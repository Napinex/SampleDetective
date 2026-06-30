from __future__ import annotations

import csv
import json
import pickle
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

import requests
from sklearn.exceptions import NotFittedError
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

ROOT = Path(__file__).resolve().parent
DOCS_DIR = ROOT / "docs"
DATA_DIR = ROOT / "data"
STORAGE_DIR = ROOT / "storage"
INDEX_PATH = STORAGE_DIR / "rag_index.pkl"


def _read_text_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="latin-1", errors="ignore")
    except Exception:
        return ""


def chunk_text(text: str, chunk_size: int = 1200, overlap: int = 180) -> List[str]:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end].strip())
        if end >= len(text):
            break
        start = max(0, end - overlap)
    return [c for c in chunks if c]


def load_documents_as_chunks() -> List[Dict[str, Any]]:
    chunks: List[Dict[str, Any]] = []

    for path in sorted(DOCS_DIR.rglob("*")):
        if path.is_file() and path.suffix.lower() in {".md", ".txt", ".csv"}:
            text = _read_text_file(path)
            for i, chunk in enumerate(chunk_text(text)):
                chunks.append({
                    "source": str(path.relative_to(ROOT)),
                    "chunk_id": f"{path.name}#{i+1}",
                    "text": chunk,
                    "kind": "document",
                })

    # CSV rows are converted into readable factual chunks.
    for path in sorted(DATA_DIR.rglob("*.csv")):
        try:
            with path.open("r", encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f)
                for i, row in enumerate(reader, start=1):
                    parts = [f"{k}: {v}" for k, v in row.items() if v not in (None, "")]
                    text = f"CSV data row from {path.name}. " + "; ".join(parts)
                    chunks.append({
                        "source": str(path.relative_to(ROOT)),
                        "chunk_id": f"{path.name}#row-{i}",
                        "text": text,
                        "kind": "csv_row",
                    })
        except Exception:
            continue

    return chunks


def build_index(chunks: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    chunks = chunks if chunks is not None else load_documents_as_chunks()
    chunks = [c for c in chunks if c.get("text", "").strip()]
    if not chunks:
        chunks = [{
            "source": "empty",
            "chunk_id": "empty#1",
            "text": "Keine Dokumente gefunden. Bitte Daten in docs/ oder data/ ablegen und ingest.py erneut ausführen.",
            "kind": "system",
        }]

    texts = [c["text"] for c in chunks]
    vectorizer = TfidfVectorizer(lowercase=True, ngram_range=(1, 2), max_features=40000)
    matrix = vectorizer.fit_transform(texts)

    index = {"chunks": chunks, "vectorizer": vectorizer, "matrix": matrix}
    with INDEX_PATH.open("wb") as f:
        pickle.dump(index, f)
    return index


def load_index(auto_build: bool = True) -> Dict[str, Any]:
    if INDEX_PATH.exists():
        try:
            with INDEX_PATH.open("rb") as f:
                index = pickle.load(f)
            # Verify fitted vectorizer
            if index.get("chunks"):
                index["vectorizer"].transform(["health score prüfmuster"])
            return index
        except Exception:
            if not auto_build:
                raise
    if auto_build:
        return build_index()
    return {"chunks": [], "vectorizer": TfidfVectorizer(), "matrix": None}


def retrieve(query: str, index: Dict[str, Any], top_k: int = 6) -> List[Dict[str, Any]]:
    chunks = index.get("chunks", [])
    if not chunks:
        return []

    texts = [c.get("text", "") for c in chunks if c.get("text", "").strip()]
    if not texts:
        return []

    vectorizer = index.get("vectorizer")
    matrix = index.get("matrix")

    try:
        q = vectorizer.transform([query])
    except (NotFittedError, AttributeError, ValueError):
        vectorizer = TfidfVectorizer(lowercase=True, ngram_range=(1, 2), max_features=40000)
        matrix = vectorizer.fit_transform(texts)
        index["vectorizer"] = vectorizer
        index["matrix"] = matrix
        q = vectorizer.transform([query])

    scores = cosine_similarity(q, matrix).flatten()
    ranked = scores.argsort()[::-1][: max(1, min(top_k, len(chunks)))]

    results: List[Dict[str, Any]] = []
    for i in ranked:
        item = dict(chunks[int(i)])
        item["score"] = float(scores[int(i)])
        results.append(item)
    return results


def format_sources(chunks: List[Dict[str, Any]]) -> str:
    if not chunks:
        return "Keine Quellen gefunden."
    lines = []
    for i, c in enumerate(chunks, start=1):
        text = c.get("text", "")
        snippet = text[:650] + ("..." if len(text) > 650 else "")
        lines.append(f"[{i}] {c.get('source')} — Score {c.get('score', 0):.3f}\n{snippet}")
    return "\n\n".join(lines)


def format_ollama_error(error: str) -> str:
    text = error or "unbekannter Fehler"
    lower = text.lower()
    if "cuda" in lower or "ptx" in lower or "unsupported toolchain" in lower:
        return (
            "Ollama konnte wegen eines lokalen CUDA-/GPU-Problems nicht antworten "
            "(PTX wurde mit einer nicht unterstützten Toolchain kompiliert). "
            "Die strukturierten CSV-Antworten funktionieren weiterhin ohne Ollama. "
            "Für freie RAG-Fragen kannst du in der Sidebar `Ollama für freie RAG-Fragen nutzen` deaktivieren "
            "oder Ollama/den GPU-Treiber aktualisieren."
        )
    if "timed out" in lower or "timeout" in lower:
        return "Ollama hat zu lange gebraucht. Die App zeigt deshalb nur lokale Quellen."
    if "connection" in lower or "refused" in lower:
        return "Ollama ist lokal nicht erreichbar. Starte Ollama oder deaktiviere die Ollama-Option in der Sidebar."
    return f"Ollama konnte nicht antworten: {text[:300]}"


def call_ollama(prompt: str, model: str = "llama3.2:3b", timeout: int = 180) -> Tuple[bool, str]:
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.2,
                    "num_ctx": 4096,
                },
            },
            timeout=timeout,
        )
        if response.status_code != 200:
            return False, f"Ollama Fehler {response.status_code}: {response.text[:500]}"
        data = response.json()
        return True, data.get("response", "").strip()
    except Exception as exc:
        return False, str(exc)


def build_llm_prompt(question: str, retrieved: List[Dict[str, Any]], history: Optional[List[Dict[str, str]]] = None) -> str:
    context = "\n\n".join(
        f"Quelle {i}: {c.get('source')}\n{c.get('text')}"
        for i, c in enumerate(retrieved, start=1)
    )
    hist = ""
    if history:
        recent = history[-8:]
        hist = "\n".join(f"{m.get('role')}: {m.get('content')[:900]}" for m in recent)

    return f"""Du bist SampleSphere AI, ein lokaler Assistent für Prüfmuster, Second-Hand-Sample-Market, BOM-Vergleich, Tests, Defects, Health Score, Reuse und Bestellprozess.

Regeln:
- Antworte auf Deutsch.
- Nutze nur die bereitgestellten Quellen und Daten.
- Wenn eine konkrete Information fehlt, sage das klar.
- Für konkrete IDs, Tests, Defects und Health Scores nenne die Quelle.
- Sei übersichtlich: kurze Erklärung, dann Tabelle oder Bulletpoints.
- Nutze vorherigen Chat-Kontext für Folgefragen.

Bisheriger Chat-Kontext:
{hist}

Lokale Quellen:
{context}

Frage:
{question}

Antwort:"""


def rag_answer(question: str, model: str = "llama3.2:3b", top_k: int = 6, use_ollama: bool = True, history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
    index = load_index(auto_build=True)
    chunks = retrieve(question, index, top_k=top_k)

    if use_ollama:
        prompt = build_llm_prompt(question, chunks, history)
        ok, answer = call_ollama(prompt, model=model, timeout=180)
        if ok and answer:
            return {"answer": answer, "sources": chunks, "used_ollama": True, "error": None}
        fallback = (
            "Ich konnte keine lokale LLM-Antwort erzeugen.\n\n"
            f"**Hinweis:** {format_ollama_error(answer)}\n\n"
            "Ich zeige stattdessen die relevantesten lokalen Quellen:\n\n"
            + format_sources(chunks)
        )
        return {"answer": fallback, "sources": chunks, "used_ollama": False, "error": answer}

    return {"answer": "Extraktive RAG-Quellen:\n\n" + format_sources(chunks), "sources": chunks, "used_ollama": False, "error": None}
