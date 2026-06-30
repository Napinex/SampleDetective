from __future__ import annotations

import json
import time
from pathlib import Path
from typing import List, Dict

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from data_engine import (
    load_data,
    maybe_handle_structured_question,
    build_available_answer,
    build_health_answer,
    build_tests_answer,
    recommend_reuse_or_order,
)
from rag_core import load_index, rag_answer

ROOT = Path(__file__).resolve().parent
CHAT_PATH = ROOT / "storage" / "chat_history.json"

st.set_page_config(
    page_title="Sample Detective",
    page_icon="🧩",
    layout="wide",
    initial_sidebar_state="expanded",
)

BOSCH_RED = "#E20015"
BOSCH_BLUE = "#005691"
BOSCH_LIGHT_BLUE = "#00A8E8"
BOSCH_YELLOW = "#FFD500"
BOSCH_GREEN = "#78BE20"
BOSCH_PURPLE = "#50237F"
TEXT = "#1f2937"
DARK_BG = "#f3f6fa"
PANEL_BG = "#ffffff"

st.markdown(
    f"""
    <style>
    :root {{
        --bosch-red: {BOSCH_RED};
        --bosch-blue: {BOSCH_BLUE};
        --bosch-light-blue: {BOSCH_LIGHT_BLUE};
        --bosch-yellow: {BOSCH_YELLOW};
        --bosch-green: {BOSCH_GREEN};
        --bosch-purple: {BOSCH_PURPLE};
        --dark-bg: {DARK_BG};
        --panel-bg: {PANEL_BG};
    }}
    html, body, [class*="css"] {{
        color: {TEXT} !important;
        font-family: Arial, Helvetica, sans-serif;
    }}
    .stApp {{
        background: {DARK_BG};
        color: {TEXT} !important;
    }}
    .block-container {{
        padding-top: 1.25rem;
        padding-bottom: 8.5rem;
    }}
    h1, h2, h3, h4, h5, h6, p, label, span, div, li, td, th {{
        color: {TEXT} !important;
    }}
    div[data-testid="stMarkdownContainer"] h1 a[href^="#"],
    div[data-testid="stMarkdownContainer"] h2 a[href^="#"],
    div[data-testid="stMarkdownContainer"] h3 a[href^="#"],
    div[data-testid="stMarkdownContainer"] h4 a[href^="#"],
    div[data-testid="stMarkdownContainer"] h5 a[href^="#"],
    div[data-testid="stMarkdownContainer"] h6 a[href^="#"],
    [data-testid="stHeaderActionElements"],
    .stHeadingActionElements {{
        display: none !important;
    }}
    .bosch-top-strip {{
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        height: 9px;
        z-index: 1001;
        background:
            linear-gradient(90deg,
                #8b1118 0%,
                #c4121a 12%,
                #e20015 18%,
                #8f3b97 31%,
                #25358a 46%,
                #005691 58%,
                #00a8e8 76%,
                #009a44 90%,
                #78be20 100%);
        box-shadow: 0 2px 8px rgba(31,41,55,0.12);
    }}
    .bosch-supergraphic {{
        position: relative;
        height: 14px;
        margin: -0.15rem 0 1.05rem 0;
        border-radius: 0;
        overflow: hidden;
        background:
            linear-gradient(90deg,
                #8b1118 0%,
                #c4121a 12%,
                #e20015 18%,
                #8f3b97 31%,
                #25358a 46%,
                #005691 58%,
                #00a8e8 76%,
                #009a44 90%,
                #78be20 100%);
        box-shadow: 0 6px 18px rgba(0,0,0,0.25);
    }}
    .bosch-supergraphic span {{
        position: absolute;
        top: 0;
        bottom: 0;
        opacity: 0.55;
        mix-blend-mode: screen;
    }}
    .bosch-supergraphic span:nth-child(1) {{
        left: 4%;
        width: 12%;
        background: #f01922;
        clip-path: polygon(0 0, 52% 0, 100% 50%, 52% 100%, 0 100%, 38% 50%);
    }}
    .bosch-supergraphic span:nth-child(2) {{
        left: 16%;
        width: 18%;
        background: #8f3b97;
        clip-path: polygon(0 0, 74% 0, 100% 50%, 74% 100%, 0 100%, 26% 50%);
    }}
    .bosch-supergraphic span:nth-child(3) {{
        left: 36%;
        width: 22%;
        background: #133b8f;
        clip-path: polygon(0 0, 88% 0, 100% 50%, 88% 100%, 0 100%, 8% 50%);
    }}
    .bosch-supergraphic span:nth-child(4) {{
        left: 58%;
        width: 22%;
        background: #69c4d8;
        clip-path: polygon(0 0, 74% 0, 100% 50%, 74% 100%, 0 100%, 12% 50%);
    }}
    .bosch-supergraphic span:nth-child(5) {{
        left: 82%;
        width: 14%;
        background: #a6ce64;
        clip-path: polygon(0 0, 80% 0, 100% 50%, 80% 100%, 0 100%, 20% 50%);
    }}
    .title-box {{
        background: {PANEL_BG};
        border-radius: 8px;
        padding: 1.05rem 1.25rem 1.15rem 1.25rem;
        border: 1px solid rgba(31,41,55,0.12);
        margin-bottom: 1rem;
        box-shadow: 0 8px 24px rgba(31,41,55,0.08);
    }}
    .title-box h1 {{
        color: {TEXT} !important;
        margin: 0;
        font-size: 2.35rem;
        font-weight: 800;
        letter-spacing: 0;
    }}
    .title-box p {{
        color: #4b5563 !important;
        margin: 0.35rem 0 0 0;
        font-size: 1.05rem;
        font-weight: 600;
    }}
    .kpi-card {{
        background: {PANEL_BG};
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid rgba(31,41,55,0.12);
        border-top: 5px solid {BOSCH_RED};
        box-shadow: 0 8px 22px rgba(31,41,55,0.08);
    }}
    .kpi-card h3 {{
        margin: 0;
        font-size: 1.8rem;
        color: {TEXT} !important;
    }}
    .kpi-card p {{
        margin: 0.25rem 0 0 0;
        font-weight: 600;
        color: #4b5563 !important;
    }}
    .hint {{
        background: {PANEL_BG};
        border-left: 6px solid {BOSCH_YELLOW};
        padding: 0.8rem 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
        border-top: 1px solid rgba(31,41,55,0.12);
        border-right: 1px solid rgba(31,41,55,0.12);
        border-bottom: 1px solid rgba(31,41,55,0.12);
    }}
    section[data-testid="stSidebar"] {{
        background: #ffffff;
        border-right: 1px solid rgba(31,41,55,0.12);
    }}
    .stChatMessage {{
        background: {PANEL_BG};
        border: 1px solid rgba(31,41,55,0.12);
        border-radius: 8px;
        padding: 0.5rem;
        box-shadow: 0 6px 18px rgba(31,41,55,0.06);
    }}
    .stChatMessage [data-testid="stMarkdownContainer"] * {{
        color: {TEXT} !important;
    }}
    div[data-testid="stChatInput"] {{
        position: fixed;
        left: 23rem;
        right: 5.25rem;
        bottom: 1.1rem;
        z-index: 999;
        background: #ffffff;
        border: 1px solid rgba(31,41,55,0.14);
        border-radius: 8px;
        box-shadow: 0 12px 30px rgba(31,41,55,0.16);
        padding: 0.55rem 3.25rem 0.55rem 0.55rem;
    }}
    div[data-testid="stChatInput"] > div {{
        width: 100%;
    }}
    div[data-testid="stChatInput"] textarea {{
        background: #ffffff !important;
        color: {TEXT} !important;
        border: 2px solid {BOSCH_LIGHT_BLUE} !important;
        border-radius: 8px !important;
        box-shadow: none !important;
        min-height: 2.65rem !important;
        height: 2.65rem !important;
        padding-right: 0.75rem !important;
    }}
    div[data-testid="stChatInput"] textarea::placeholder {{
        color: #6b7280 !important;
    }}
    div[data-testid="stChatInput"] button {{
        color: #ffffff !important;
        background: {BOSCH_BLUE} !important;
        border-radius: 8px !important;
        position: absolute !important;
        right: 0.65rem !important;
        top: 50% !important;
        transform: translateY(-50%) !important;
        width: 2.4rem !important;
        height: 2.4rem !important;
    }}
    @media (max-width: 900px) {{
        div[data-testid="stChatInput"] {{
            left: 1rem;
            right: 4.75rem;
        }}
    }}
    div[data-testid="stTabs"] button p {{
        color: {TEXT} !important;
    }}
    div[data-testid="stDataFrame"] {{
        background: {PANEL_BG} !important;
        border: 1px solid rgba(31,41,55,0.12);
        border-radius: 8px;
    }}
    div[data-testid="stDataFrame"] * {{
        color: #111827 !important;
    }}
    div[data-testid="stDataFrame"] input,
    div[data-testid="stDataFrame"] textarea {{
        color: #111827 !important;
        background: #ffffff !important;
    }}
    input, textarea, select {{
        background: #ffffff !important;
        color: {TEXT} !important;
        border-color: rgba(31,41,55,0.22) !important;
    }}
    input::placeholder, textarea::placeholder {{
        color: #6b7280 !important;
    }}
    div[data-baseweb="select"] * {{
        background: #ffffff !important;
        color: {TEXT} !important;
    }}
    div[data-testid="stAlert"] {{
        background: {PANEL_BG} !important;
        color: {TEXT} !important;
        border: 1px solid rgba(31,41,55,0.12);
    }}
    div[data-testid="stExpander"] {{
        background: {PANEL_BG} !important;
        color: {TEXT} !important;
        border-color: rgba(31,41,55,0.12) !important;
    }}
    div[data-testid="stMarkdownContainer"] code,
    div[data-testid="stMarkdownContainer"] code *,
    .stChatMessage [data-testid="stMarkdownContainer"] code,
    .stChatMessage [data-testid="stMarkdownContainer"] code * {{
        color: #07111d !important;
        background: #dfe8f2 !important;
        text-shadow: none !important;
    }}
    div[data-testid="stMarkdownContainer"] code,
    .stChatMessage [data-testid="stMarkdownContainer"] code {{
        border: 1px solid rgba(31,41,55,0.16);
        border-radius: 5px;
        padding: 0.08rem 0.28rem;
        font-weight: 700;
    }}
    div[data-testid="stTable"] * {{
        background: {PANEL_BG} !important;
        color: {TEXT} !important;
    }}
    button[kind="primary"] {{
        background: {BOSCH_RED} !important;
        color: white !important;
    }}
    .scroll-bottom {{
        position: fixed;
        right: 1.25rem;
        bottom: 1.1rem;
        z-index: 1000;
        width: 2.75rem;
        height: 2.75rem;
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        background: {BOSCH_BLUE};
        color: #ffffff !important;
        text-decoration: none !important;
        font-size: 1.45rem;
        font-weight: 800;
        box-shadow: 0 12px 26px rgba(0,86,145,0.28);
    }}
    .scroll-bottom:hover {{
        background: #004777;
        color: #ffffff !important;
    }}
    html {{
        scroll-behavior: smooth;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

components.html(
    """
    <script>
    (function () {
      function installCopyShortcutGuard() {
        try {
          const doc = window.parent.document;
          if (doc.__sampleDetectiveCopyShortcutGuard) return;
          doc.__sampleDetectiveCopyShortcutGuard = true;
          doc.addEventListener(
            "keydown",
            function (event) {
              const key = (event.key || "").toLowerCase();
              if ((event.ctrlKey || event.metaKey) && !event.altKey && key === "c") {
                event.stopImmediatePropagation();
              }
            },
            true
          );
        } catch (error) {
          // Component iframe may be sandboxed in some environments.
        }
      }
      installCopyShortcutGuard();
      window.setInterval(installCopyShortcutGuard, 1000);
    })();
    </script>
    """,
    height=0,
    width=0,
)


def load_chat() -> List[Dict[str, str]]:
    if "messages" in st.session_state:
        return st.session_state.messages
    if CHAT_PATH.exists():
        try:
            st.session_state.messages = json.loads(CHAT_PATH.read_text(encoding="utf-8"))
        except Exception:
            st.session_state.messages = []
    else:
        st.session_state.messages = []
    return st.session_state.messages


def save_chat(messages: List[Dict[str, str]]) -> None:
    CHAT_PATH.parent.mkdir(parents=True, exist_ok=True)
    CHAT_PATH.write_text(json.dumps(messages, ensure_ascii=False, indent=2), encoding="utf-8")


def add_message(role: str, content: str) -> None:
    messages = load_chat()
    messages.append({"role": role, "content": content})
    st.session_state.messages = messages
    save_chat(messages)


def stream_markdown(text: str, delay: float = 0.018) -> None:
    placeholder = st.empty()
    words = text.split(" ")
    rendered: List[str] = []
    for word in words:
        rendered.append(word)
        placeholder.markdown(" ".join(rendered) + " ▌")
        time.sleep(delay)
    placeholder.markdown(text)


def visible_dataframe(rows: List[Dict[str, str]]):
    df = pd.DataFrame(rows)
    return df.style.set_properties(**{
        "background-color": "#ffffff",
        "color": "#111827",
        "border-color": "#d1d5db",
    }).set_table_styles([
        {
            "selector": "th",
            "props": [
                ("background-color", "#e8eef5"),
                ("color", "#111827"),
                ("font-weight", "700"),
            ],
        },
        {
            "selector": "td",
            "props": [
                ("background-color", "#ffffff"),
                ("color", "#111827"),
            ],
        },
    ])


@st.cache_data(show_spinner=False)
def cached_data():
    return load_data()


data = cached_data()
messages = load_chat()

index = load_index(auto_build=True)
chunk_count = len(index.get("chunks", []))

QUICK_QUESTIONS = [
    "Welche Prüfmuster sind aktuell verfügbar?",
    "Zeige mir den Musterpass für 4301828993017651.",
    "Was hat 4401831543017350 schon für Tests gesehen?",
    "Welche Tests dürfen mit 0805038020400411 noch gemacht werden?",
    "Gibt es ähnliche Konfigurationen zu 4301828993017651 anhand der BOM?",
    "Worin unterscheiden sich die ähnlichen Muster zu 4301828993017651?",
    "Passt 4301800000000012 als Ersatz für 4301828993017651?",
    "Gibt es ähnliche Muster zur global_id 019DCC3C-5800-7D5E-BF60-7A8B9CDAEBFC?",
    "Welche Muster haben eine ähnliche BOM?",
    "Soll ich ein neues Muster bestellen oder ein vorhandenes wiederverwenden?",
]

with st.sidebar:
    st.markdown("## ⚙️ Einstellungen")
    model = st.text_input("Ollama-Modell", value="llama3.2:3b", help="Schnell: llama3.2:3b | stärker aber langsamer: llama3.1:8b")
    use_ollama = st.checkbox("Ollama für freie RAG-Fragen nutzen", value=True)
    structured_first = st.checkbox("CSV-/Tabellenfragen direkt beantworten", value=True)
    top_k = st.slider("Top-K Quellen für RAG", min_value=3, max_value=20, value=7, step=1)
    show_sources = st.checkbox("Quellen-Chunks anzeigen", value=False)

    st.markdown("---")
    st.markdown("## 📦 Index")
    st.write(f"**{chunk_count} Chunks** im lokalen Index")
    st.caption("Der Index durchsucht alle Dokumente und CSV-Zeilen. An das LLM gehen nur die relevantesten Chunks.")

    if st.button("🧹 Neuen Chat starten"):
        st.session_state.messages = []
        save_chat([])
        st.rerun()

    if st.button("🔄 Daten neu laden"):
        st.cache_data.clear()
        st.rerun()

st.markdown(
    """
    <div class="bosch-top-strip"></div>
    <div class="bosch-supergraphic">
        <span></span><span></span><span></span><span></span><span></span>
    </div>
    <div class="title-box">
        <h1>Sample Detective</h1>
        <p>From scattered sample data to reuse decisions.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

samples = data.get("samples", [])
available = [s for s in samples if s.get("status") == "available"]
open_high = [s for s in samples if int(s.get("high_defects_count") or 0) > 0]
good_reuse = [s for s in samples if int(s.get("reuse_score") or 0) >= 70 and s.get("status") == "available"]

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f'<div class="kpi-card"><h3>{len(samples)}</h3><p>Prüfmuster</p></div>', unsafe_allow_html=True)
with c2:
    st.markdown(f'<div class="kpi-card"><h3>{len(available)}</h3><p>verfügbar</p></div>', unsafe_allow_html=True)
with c3:
    st.markdown(f'<div class="kpi-card"><h3>{len(good_reuse)}</h3><p>gute Reuse-Kandidaten</p></div>', unsafe_allow_html=True)
with c4:
    st.markdown(f'<div class="kpi-card"><h3>{len(open_high)}</h3><p>mit High-Defect</p></div>', unsafe_allow_html=True)

st.markdown(
    """
    <div class="hint">
    <b>Schnellfragen:</b> Wähle eine Beispiel-Frage aus, wenn du eine Orientierung brauchst.
    </div>
    """,
    unsafe_allow_html=True,
)
quick_cols = st.columns([5, 1.25])
with quick_cols[0]:
    selected_quick_question = st.selectbox(
        "Beispiel-Frage auswählen",
        [""] + QUICK_QUESTIONS,
        index=0,
        label_visibility="collapsed",
    )
with quick_cols[1]:
    ask_quick_question = st.button(
        "Frage stellen",
        disabled=not selected_quick_question,
        use_container_width=True,
    )
if ask_quick_question and selected_quick_question:
    st.session_state.pending_question = selected_quick_question

tab_chat, tab_overview, tab_data = st.tabs(["💬 Chat", "📊 Simple Übersicht", "🗂️ Daten"])

with tab_overview:
    st.subheader("Simple Übersicht")
    st.markdown("Die Übersicht ist bewusst simpel gehalten: Verfügbarkeit, Health, Reuse und Defects auf einen Blick.")

    cols = ["local_id", "material_nr", "product_hierarchy_name", "status_de", "location", "availability_from", "total_usage_hours", "total_test_count", "open_defects_count", "health_score", "reuse_score"]
    st.dataframe(visible_dataframe([{c: s.get(c, "") for c in cols} for s in samples]), use_container_width=True, hide_index=True)

    st.subheader("Schnellantworten")
    b1, b2, b3 = st.columns(3)
    if b1.button("Verfügbare Muster anzeigen"):
        st.markdown(build_available_answer(data))
    if b2.button("Health Score Tabelle"):
        st.markdown(build_health_answer(data))
    if b3.button("Testarten erklären"):
        st.markdown(build_tests_answer(data, None))

with tab_data:
    st.subheader("CSV-Datenquellen")
    selected = st.selectbox("Datenquelle", list(data.keys()))
    st.dataframe(visible_dataframe(data.get(selected, [])), use_container_width=True, hide_index=True)

with tab_chat:
    st.subheader("Chat mit Kontext")
    st.caption("Der Chat bleibt im Kontext erhalten. Folgefragen wie „wo unterschiedlich?“ können sich auf vorherige Muster beziehen.")

    if not messages:
        st.info("Starte mit einer Frage. Beispiel: Welche Prüfmuster sind aktuell verfügbar?")

    for msg in messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    pending_question = st.session_state.pop("pending_question", None)
    typed_question = st.chat_input("Frage an Sample Detective stellen ...")
    question = pending_question or typed_question
    if question:
        add_message("user", question)
        with st.chat_message("user"):
            st.markdown(question)

        with st.chat_message("assistant"):
            with st.spinner("Prüfe strukturierte Daten und lokalen RAG-Index ..."):
                answer = None
                sources = []
                structured_tried = False
                if structured_first:
                    structured_tried = True
                    handled = maybe_handle_structured_question(question, data, history=load_chat())
                    if handled:
                        answer = handled["answer"]
                        sources = handled.get("sources", [])

                if answer is None:
                    result = rag_answer(
                        question=question,
                        model=model.strip() or "llama3.2:3b",
                        top_k=top_k,
                        use_ollama=use_ollama,
                        history=load_chat(),
                    )
                    answer = result["answer"]
                    sources = result.get("sources", [])
                    if result.get("error") and not structured_tried:
                        handled = maybe_handle_structured_question(question, data, history=load_chat())
                        if handled:
                            answer = handled["answer"]
                            sources = handled.get("sources", [])
                    elif result.get("error") and structured_tried:
                        handled = maybe_handle_structured_question(question, data, history=load_chat())
                        if handled:
                            answer = handled["answer"]
                            sources = handled.get("sources", [])

            stream_markdown(answer)

            if show_sources and sources:
                with st.expander("Quellen anzeigen"):
                    if isinstance(sources[0], dict):
                        for i, src in enumerate(sources, start=1):
                            st.markdown(f"**[{i}] {src.get('source')}** — Score {src.get('score', 0):.3f}")
                            st.write(src.get("text", "")[:1200])
                    else:
                        for src in sources:
                            st.write(src)

        add_message("assistant", answer)

    st.markdown('<div id="chat-bottom"></div>', unsafe_allow_html=True)

st.markdown('<a class="scroll-bottom" href="#chat-bottom" aria-label="Zur letzten Antwort">↓</a>', unsafe_allow_html=True)
