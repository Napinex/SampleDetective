from __future__ import annotations

import csv
import math
import re
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional

import sample_comparison as sample_compare

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data" / "records"
SAMPLE_KEY = "local_id"


def read_csv_dict(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def to_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(float(str(value).replace(",", ".")))
    except Exception:
        return default


def to_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(str(value).replace(",", "."))
    except Exception:
        return default


def sample_identifier(row: Dict[str, str]) -> str:
    return row.get(SAMPLE_KEY) or row.get("sample_id", "")


def load_data() -> Dict[str, List[Dict[str, str]]]:
    data = {
        "samples": read_csv_dict(DATA_DIR / "samples.csv"),
        "availability": read_csv_dict(DATA_DIR / "availability.csv"),
        "bom": read_csv_dict(DATA_DIR / "bom_components.csv"),
        "test_catalog": read_csv_dict(DATA_DIR / "test_catalog.csv"),
        "test_runs": read_csv_dict(DATA_DIR / "test_runs.csv"),
        "defects": read_csv_dict(DATA_DIR / "defects.csv"),
        "order_requests": read_csv_dict(DATA_DIR / "order_requests.csv"),
    }
    enrich_comparison_metadata(data)
    recalculate_scores(data)
    return data


def enrich_comparison_metadata(data: Dict[str, List[Dict[str, str]]]) -> None:
    """Ergänzt fehlende synthetische Vergleichsfelder ohne die CSV-Struktur zu erzwingen."""
    material_defaults = {
        "4897.B4T.0S3": ("HW_3.2", "brake_family=ESP10_CP;pressure_sensor=S1;valve_block=VB-A"),
        "4897.B4T.0NM": ("HW_3.1", "brake_family=ESP10_TE;pressure_sensor=S2;valve_block=VB-B"),
        "4897.B4T.0RG": ("HW_2.9", "brake_family=ESP10_TE;pressure_sensor=S1;valve_block=VB-C"),
        "4897.B4T.0N4": ("HW_2.8", "brake_family=ESP10_CB;pressure_sensor=S3;valve_block=VB-D"),
        "4897.B4T.0PR": ("HW_3.2", "brake_family=ESP10_CB;pressure_sensor=S1;valve_block=VB-A"),
        "4897.B4T.0RJ": ("HW_3.1", "brake_family=ESP10_CB;pressure_sensor=S2;valve_block=VB-B"),
    }
    availability_by_sample = {sample_identifier(row): row for row in data.get("availability", [])}
    tests_by_sample: Dict[str, List[Dict[str, str]]] = {}
    for test in data.get("test_runs", []):
        tests_by_sample.setdefault(sample_identifier(test), []).append(test)

    for sample in data.get("samples", []):
        sample_id = sample_identifier(sample)
        material = sample.get("material_nr", "")
        hardware_version, config_parameters = material_defaults.get(
            material,
            ("HW_unbekannt", "Dazu liegen in den Daten keine Informationen vor."),
        )
        if not sample.get("hardware_version"):
            sample["hardware_version"] = hardware_version
        if not sample.get("configuration_parameters"):
            sample["configuration_parameters"] = config_parameters

        status = sample.get("status", "").lower()
        if not sample.get("lifecycle_phase"):
            if status == "blocked":
                sample["lifecycle_phase"] = "EOL"
            elif status in {"available", "reserved"}:
                sample["lifecycle_phase"] = "MOL"
            elif status == "in_test":
                sample["lifecycle_phase"] = "MOL-Test"
            else:
                sample["lifecycle_phase"] = "Dazu liegen in den Daten keine Informationen vor."

        availability = availability_by_sample.get(sample_id, {})
        if not sample.get("availability_status"):
            sample["availability_status"] = availability.get("status_de") or availability.get("status") or sample.get("status_de") or sample.get("status", "")

        tests = tests_by_sample.get(sample_id, [])
        completed = sorted({t.get("test_type", "") for t in tests if t.get("test_type") and t.get("result", "").lower() in {"passed", "warning", "failed"}})
        failed = sorted({t.get("test_type", "") for t in tests if t.get("test_type") and t.get("result", "").lower() == "failed"})
        sample["completed_tests"] = ";".join(completed) if completed else "keine dokumentierten abgeschlossenen Tests"
        sample["failed_tests"] = ";".join(failed) if failed else "keine dokumentierten fehlgeschlagenen Tests"
        sample["planned_tests"] = "Dazu liegen in den Daten keine Informationen vor."

    for row in data.get("bom", []):
        component = row.get("component", "")
        if not row.get("component_id"):
            row["component_id"] = component
        if not row.get("component_name"):
            row["component_name"] = row.get("component_description", "")
        if not row.get("component_version"):
            suffix = component[-4:] if component else "UNKNOWN"
            row["component_version"] = f"CV-{suffix}"


def recalculate_scores(data: Dict[str, List[Dict[str, str]]]) -> None:
    """Rechnet Health Score und Reuse Score aus den aktuellen CSV-Daten neu."""
    tests_by_sample: Dict[str, List[Dict[str, str]]] = {}
    defects_by_sample: Dict[str, List[Dict[str, str]]] = {}
    for t in data.get("test_runs", []):
        tests_by_sample.setdefault(sample_identifier(t), []).append(t)
    for d in data.get("defects", []):
        defects_by_sample.setdefault(sample_identifier(d), []).append(d)

    heavy_tests = {"DURABILITY", "FIELD_DRIVE", "THERMAL_FADE", "CORROSION"}

    for s in data.get("samples", []):
        sample_id = sample_identifier(s)
        tests = tests_by_sample.get(sample_id, [])
        defects = defects_by_sample.get(sample_id, [])

        usage_hours = sum(to_int(t.get("usage_hours_added")) for t in tests)
        if usage_hours == 0:
            usage_hours = to_int(s.get("total_usage_hours"))

        open_defects = [d for d in defects if str(d.get("status", "")).lower() == "open"]
        high_open = [d for d in open_defects if str(d.get("severity", "")).lower() == "high"]
        heavy_count = sum(1 for t in tests if t.get("test_type") in heavy_tests)

        health = 100
        health -= usage_hours * 0.10
        health -= len(tests) * 1.5
        health -= len(high_open) * 22
        health -= max(0, len(open_defects) - len(high_open)) * 8
        health -= heavy_count * 3

        status = str(s.get("status", "")).lower()
        if status == "blocked":
            health -= 20
        if status == "maintenance":
            health -= 10

        health = int(max(0, min(100, round(health))))

        reuse_score = health * 0.62
        if status == "available":
            reuse_score += 18
        if len(open_defects) == 0:
            reuse_score += 10
        if len(tests) >= 2:
            reuse_score += 6
        if s.get("material_nr"):
            reuse_score += 4
        reuse_score = int(max(0, min(100, round(reuse_score))))

        s["total_usage_hours"] = str(usage_hours)
        s["total_test_count"] = str(len(tests))
        s["open_defects_count"] = str(len(open_defects))
        s["high_defects_count"] = str(len(high_open))
        s["health_score"] = str(health)
        s["reuse_score"] = str(reuse_score)


def extract_entities(question: str, history: Optional[List[Dict[str, str]]] = None) -> Dict[str, List[str]]:
    text = question or ""
    if history:
        last = history[-8:]
        text += "\n" + "\n".join(m.get("content", "") for m in last)

    sample_ids = re.findall(
        r"\b(?:\d{16}|SMP-\d{4}-\d{3}|PM-\d{3,}|[0-9A-F]{8}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{12})\b",
        text,
        flags=re.IGNORECASE,
    )
    sample_ids = [s.upper() for s in sample_ids]

    material_ids = re.findall(r"\b\d{4,5}\.B4T\.0[A-Z0-9]{2,3}\b", text, flags=re.IGNORECASE)
    material_ids = [m.upper().replace("44897.", "4897.") for m in material_ids]

    test_types = []
    for key in ["FUNC_CHECK", "PRESSURE_LEAK", "ABS_CTRL", "THERMAL_FADE", "DURABILITY", "NVH_NOISE", "FIELD_DRIVE", "REGRESSION_SW", "CORROSION", "FINAL_VALID"]:
        if key.lower() in text.lower():
            test_types.append(key)
    # German aliases
    aliases = {
        "thermal": "THERMAL_FADE",
        "dauerlauf": "DURABILITY",
        "endurance": "DURABILITY",
        "feld": "FIELD_DRIVE",
        "fahrzeug": "FIELD_DRIVE",
        "druck": "PRESSURE_LEAK",
        "leckage": "PRESSURE_LEAK",
        "abs": "ABS_CTRL",
        "geräusch": "NVH_NOISE",
        "noise": "NVH_NOISE",
        "korrosion": "CORROSION",
        "final": "FINAL_VALID",
        "software": "REGRESSION_SW",
    }
    for word, ttype in aliases.items():
        if word in text.lower() and ttype not in test_types:
            test_types.append(ttype)

    # Keep order but remove duplicates
    def dedup(xs: List[str]) -> List[str]:
        out = []
        for x in xs:
            if x not in out:
                out.append(x)
        return out

    return {"sample_ids": dedup(sample_ids), "material_ids": dedup(material_ids), "test_types": dedup(test_types)}


def get_sample(data: Dict[str, List[Dict[str, str]]], sample_id: str) -> Optional[Dict[str, str]]:
    return sample_compare.get_sample_by_identifier(data, sample_id)


def tests_for_sample(data: Dict[str, List[Dict[str, str]]], sample_id: str) -> List[Dict[str, str]]:
    return [t for t in data.get("test_runs", []) if sample_identifier(t).upper() == sample_id.upper()]


def defects_for_sample(data: Dict[str, List[Dict[str, str]]], sample_id: str, only_open: bool = False) -> List[Dict[str, str]]:
    rows = [d for d in data.get("defects", []) if sample_identifier(d).upper() == sample_id.upper()]
    if only_open:
        rows = [d for d in rows if d.get("status", "").lower() == "open"]
    return rows


def components_for_material(data: Dict[str, List[Dict[str, str]]], material_nr: str) -> List[Dict[str, str]]:
    m = material_nr.strip().upper().replace("44897.", "4897.")
    return [b for b in data.get("bom", []) if b.get("material_nr", "").upper() == m]


def component_set(data: Dict[str, List[Dict[str, str]]], material_nr: str) -> set:
    return {str(b.get("component", "")).strip() for b in components_for_material(data, material_nr) if b.get("component")}


def bom_similarity(data: Dict[str, List[Dict[str, str]]], mat_a: str, mat_b: str) -> float:
    a = component_set(data, mat_a)
    b = component_set(data, mat_b)
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def bom_diff(data: Dict[str, List[Dict[str, str]]], mat_a: str, mat_b: str) -> Dict[str, Any]:
    a_rows = components_for_material(data, mat_a)
    b_rows = components_for_material(data, mat_b)
    a = {r.get("component"): r for r in a_rows}
    b = {r.get("component"): r for r in b_rows}
    only_a = [a[c] for c in sorted(set(a) - set(b))]
    only_b = [b[c] for c in sorted(set(b) - set(a))]
    common = sorted(set(a) & set(b))
    critical_a = [x for x in only_a if x.get("criticality") == "high"]
    critical_b = [x for x in only_b if x.get("criticality") == "high"]
    return {
        "material_a": mat_a,
        "material_b": mat_b,
        "similarity": bom_similarity(data, mat_a, mat_b),
        "common_count": len(common),
        "only_a": only_a,
        "only_b": only_b,
        "critical_differences": critical_a + critical_b,
    }


def similar_samples(data: Dict[str, List[Dict[str, str]]], sample_id_or_material: str, limit: int = 6) -> List[Dict[str, Any]]:
    sample = get_sample(data, sample_id_or_material)
    if sample:
        try:
            return [
                {
                    "local_id": item["local_id"],
                    "global_id": item["global_id"],
                    "material_nr": item["material_nr"],
                    "status": item["status"],
                    "location": item["location"],
                    "health_score": item["health_score"],
                    "reuse_score": item["reuse_score"],
                    "bom_similarity": item["bom_similarity"],
                    "similarity_percent": item["similarity_percent"],
                    "fit": item["fit"],
                    "reason": item["reason"],
                }
                for item in sample_compare.find_similar_samples(data, sample_identifier(sample), top_k=limit)
            ]
        except ValueError:
            pass

    target_material = sample.get("material_nr") if sample else sample_id_or_material
    target_sample_id = sample_identifier(sample) if sample else None

    out = []
    for s in data.get("samples", []):
        if target_sample_id and sample_identifier(s) == target_sample_id:
            continue
        sim = bom_similarity(data, target_material, s.get("material_nr", ""))
        out.append({
            "local_id": sample_identifier(s),
            "material_nr": s.get("material_nr"),
            "status": s.get("status_de") or s.get("status"),
            "location": s.get("location"),
            "health_score": to_int(s.get("health_score")),
            "reuse_score": to_int(s.get("reuse_score")),
            "bom_similarity": round(sim, 3),
            "product": s.get("product_hierarchy_name"),
        })
    out.sort(key=lambda x: (x["bom_similarity"], x["reuse_score"], x["health_score"]), reverse=True)
    return out[:limit]


def allowed_tests(data: Dict[str, List[Dict[str, str]]], sample_id: str) -> List[Dict[str, Any]]:
    s = get_sample(data, sample_id)
    if not s:
        return []

    existing = tests_for_sample(data, sample_id)
    existing_types = {t.get("test_type") for t in existing if t.get("result") == "passed"}
    open_defects = defects_for_sample(data, sample_id, only_open=True)
    high_open = [d for d in open_defects if d.get("severity", "").lower() == "high"]
    health = to_int(s.get("health_score"))
    usage = to_int(s.get("total_usage_hours"))
    status = s.get("status", "").lower()

    results = []
    for t in data.get("test_catalog", []):
        ttype = t.get("test_type", "")
        min_health = to_int(t.get("min_health_required"))
        max_usage = to_int(t.get("max_usage_hours"), 999999)
        repeat = str(t.get("repeat_allowed", "")).lower()

        blockers = []
        if status == "blocked":
            blockers.append("Muster ist gesperrt")
        if high_open:
            blockers.append("offener High-Defect")
        if health < min_health:
            blockers.append(f"Health Score {health} < Mindestwert {min_health}")
        if usage > max_usage:
            blockers.append(f"Usage Hours {usage} > Grenzwert {max_usage}")
        if ttype in existing_types and repeat == "no":
            blockers.append("Test bereits bestanden und nicht wiederholbar")
        if ttype in existing_types and repeat == "limited" and usage > max_usage * 0.75:
            blockers.append("Wiederholung nur eingeschränkt erlaubt, Usage bereits hoch")

        allowed = len(blockers) == 0
        results.append({
            "test_type": ttype,
            "test_name": t.get("test_name"),
            "allowed": "ja" if allowed else "nein",
            "reason": "freigegeben nach aktuellen Prüfregeln" if allowed else "; ".join(blockers),
            "min_health_required": min_health,
            "sample_health": health,
            "sample_usage_hours": usage,
            "phase": t.get("phase")
        })
    return results


def recommend_reuse_or_order(data: Dict[str, List[Dict[str, str]]], material_nr: Optional[str] = None, test_type: Optional[str] = None) -> Dict[str, Any]:
    if not material_nr:
        # Use the most common material among available samples as fallback.
        available = [s for s in data.get("samples", []) if s.get("status") == "available"]
        material_nr = available[0].get("material_nr") if available else (data.get("samples", [{}])[0].get("material_nr", ""))

    candidates = []
    for s in data.get("samples", []):
        sim = bom_similarity(data, material_nr, s.get("material_nr", ""))
        if sim <= 0:
            continue
        status_bonus = 1 if s.get("status") == "available" else 0
        high_def = to_int(s.get("high_defects_count"))
        health = to_int(s.get("health_score"))
        reuse = to_int(s.get("reuse_score"))

        test_ok = True
        test_reason = ""
        if test_type:
            allowed = allowed_tests(data, sample_identifier(s))
            hit = next((a for a in allowed if a.get("test_type") == test_type), None)
            test_ok = bool(hit and hit.get("allowed") == "ja")
            test_reason = hit.get("reason") if hit else "Testtyp nicht gefunden"

        decision_score = sim * 50 + reuse * 0.35 + health * 0.15 + status_bonus * 12 - high_def * 30
        if not test_ok:
            decision_score -= 25
        candidates.append({
            "local_id": sample_identifier(s),
            "material_nr": s.get("material_nr"),
            "status": s.get("status_de") or s.get("status"),
            "location": s.get("location"),
            "availability_from": s.get("availability_from"),
            "health_score": health,
            "reuse_score": reuse,
            "bom_similarity": round(sim, 3),
            "test_ok": "ja" if test_ok else "nein",
            "test_reason": test_reason,
            "decision_score": round(decision_score, 1),
        })

    candidates.sort(key=lambda x: x["decision_score"], reverse=True)
    best = candidates[0] if candidates else None

    if best and best["decision_score"] >= 70 and best["test_ok"] == "ja":
        decision = "Wiederverwendung empfohlen"
    elif best and best["decision_score"] >= 55:
        decision = "Fachliche Prüfung vor Wiederverwendung empfohlen"
    else:
        decision = "Neubestellung wahrscheinlich sinnvoll"

    return {
        "requested_material_nr": material_nr,
        "requested_test_type": test_type or "nicht angegeben",
        "decision": decision,
        "best_candidate": best,
        "candidates": candidates[:8],
    }


def markdown_table(rows: List[Dict[str, Any]], columns: List[str], headers: Optional[List[str]] = None, max_rows: int = 20) -> str:
    if not rows:
        return "_Keine passenden Daten gefunden._"
    headers = headers or columns
    clipped = rows[:max_rows]
    lines = []
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join(["---"] * len(columns)) + " |")
    for r in clipped:
        vals = []
        for c in columns:
            v = r.get(c, "")
            vals.append(str(v).replace("\n", " ")[:120])
        lines.append("| " + " | ".join(vals) + " |")
    if len(rows) > max_rows:
        lines.append(f"\n_Weitere {len(rows)-max_rows} Zeilen ausgeblendet._")
    return "\n".join(lines)


def build_available_answer(data: Dict[str, List[Dict[str, str]]]) -> str:
    rows = [s for s in data.get("samples", []) if s.get("status") == "available"]
    rows.sort(key=lambda x: (to_int(x.get("reuse_score")), to_int(x.get("health_score"))), reverse=True)
    intro = f"Laut aktuellem Datenbestand sind **{len(rows)} Prüfmuster verfügbar**."
    table = markdown_table(rows, ["local_id", "material_nr", "product_hierarchy_name", "location", "availability_from", "health_score", "reuse_score", "open_defects_count"],
                           ["Muster", "Material", "Produkt", "Standort", "Verfügbar ab", "Health", "Reuse", "Offene Defects"])
    return intro + "\n\n" + table + "\n\nQuelle: `samples.csv`, `availability.csv`."


def build_health_answer(data: Dict[str, List[Dict[str, str]]]) -> str:
    rows = list(data.get("samples", []))
    rows.sort(key=lambda x: to_int(x.get("health_score")), reverse=True)
    table = markdown_table(rows, ["local_id", "status_de", "material_nr", "total_usage_hours", "total_test_count", "open_defects_count", "high_defects_count", "health_score", "reuse_score"],
                           ["Muster", "Status", "Material", "Usage h", "Tests", "Defects offen", "High offen", "Health", "Reuse"])
    return "Hier ist die Health-Score-Übersicht. Die Scores werden aus Tests, Defects und Usage Hours berechnet.\n\n" + table + "\n\nQuelle: `samples.csv`, `test_runs.csv`, `defects.csv`, Health-Regel aus `02_health_score_definition.md`."


def build_sample_pass_answer(data: Dict[str, List[Dict[str, str]]], sample_id: str) -> str:
    s = get_sample(data, sample_id)
    if not s:
        return f"Ich finde kein Prüfmuster `{sample_id}` im Datenbestand."

    tests = tests_for_sample(data, sample_id)
    defs = defects_for_sample(data, sample_id)
    lines = [
        f"## Digitaler Musterpass für {sample_id}",
        f"- **Materialnummer:** {s.get('material_nr')}",
        f"- **Produkt:** {s.get('product_hierarchy_name')}",
        f"- **Status:** {s.get('status_de')} / Standort: {s.get('location')}",
        f"- **Verfügbarkeit:** ab {s.get('availability_from')} bis {s.get('availability_until')}",
        f"- **Usage Hours:** {s.get('total_usage_hours')}",
        f"- **Health Score:** {s.get('health_score')}",
        f"- **Reuse Score:** {s.get('reuse_score')}",
        f"- **Offene Defects:** {s.get('open_defects_count')} davon High: {s.get('high_defects_count')}",
        "",
        "### Testhistorie",
        markdown_table(tests, ["test_id", "test_name", "start_date", "end_date", "result", "usage_hours_added", "test_bench"],
                       ["Test-ID", "Test", "Start", "Ende", "Ergebnis", "+h", "Prüfstand"], max_rows=10),
        "",
        "### Defects",
        markdown_table(defs, ["defect_id", "severity", "status", "defect_type", "impact_on_reuse", "action"],
                       ["Defect", "Severity", "Status", "Typ", "Reuse Impact", "Maßnahme"], max_rows=10),
        "",
        "Quelle: `samples.csv`, `test_runs.csv`, `defects.csv`, `sample_pass_*.md`."
    ]
    return "\n".join(lines)


def build_tests_answer(data: Dict[str, List[Dict[str, str]]], sample_id: Optional[str] = None) -> str:
    if sample_id:
        tests = tests_for_sample(data, sample_id)
        return f"## Testhistorie für {sample_id}\n\n" + markdown_table(tests, ["test_id", "test_type", "test_name", "phase", "start_date", "end_date", "result", "usage_hours_added", "temperature_max_c", "brake_cycles"],
                            ["Test-ID", "Typ", "Name", "Phase", "Start", "Ende", "Ergebnis", "+h", "Temp °C", "Zyklen"], max_rows=20) + "\n\nQuelle: `test_runs.csv`."
    return "## Testarten im Testkatalog\n\n" + markdown_table(data.get("test_catalog", []), ["test_type", "test_name", "phase", "description", "min_health_required", "max_usage_hours", "repeat_allowed"],
                           ["Typ", "Name", "Phase", "Beschreibung", "Min Health", "Max Usage h", "Wiederholung"], max_rows=20) + "\n\nQuelle: `test_catalog.csv`, `04_test_rules_allowed_tests.md`."


def build_allowed_tests_answer(data: Dict[str, List[Dict[str, str]]], sample_id: str) -> str:
    rows = allowed_tests(data, sample_id)
    if not rows:
        return f"Ich finde kein Prüfmuster `{sample_id}` im Datenbestand."

    allowed_rows = [r for r in rows if r.get("allowed") == "ja"]
    blocked_rows = [r for r in rows if r.get("allowed") != "ja"]

    lines = [
        f"## Welche Tests dürfen mit {sample_id} noch gemacht werden?",
        "",
        "### Noch erlaubt",
        markdown_table(
            allowed_rows,
            ["test_type", "test_name", "phase", "reason", "sample_health", "sample_usage_hours"],
            ["Typ", "Test", "Phase", "Grund", "Health", "Usage h"],
            max_rows=20,
        ),
        "",
        "### Nicht erlaubt / blockiert",
        markdown_table(
            blocked_rows,
            ["test_type", "test_name", "reason", "sample_health", "sample_usage_hours"],
            ["Typ", "Test", "Grund", "Health", "Usage h"],
            max_rows=20,
        ),
        "",
        "Quelle: `test_catalog.csv`, `samples.csv`, `defects.csv`, `04_test_rules_allowed_tests.md`.",
    ]
    return "\n".join(lines)


def build_similar_answer(data: Dict[str, List[Dict[str, str]]], target: str) -> str:
    if get_sample(data, target):
        return sample_compare.explain_sample_differences(data, target, top_k=5)

    sims = similar_samples(data, target, limit=8)
    title = f"## Ähnliche Prüfmuster / Konfigurationen zu {target}"
    table = markdown_table(sims, ["local_id", "material_nr", "status", "location", "health_score", "reuse_score", "bom_similarity"],
                           ["Muster", "Material", "Status", "Standort", "Health", "Reuse", "BOM-Ähnlichkeit"], max_rows=8)
    return title + "\n\n" + table + "\n\nBewertung: >= 0,95 nahezu identisch, 0,85–0,94 ähnlich mit technischer Prüfung, < 0,70 eher kein direkter Reuse.\n\nQuelle: `bom_components.csv`, `03_bom_similarity_rules.md`."


def build_diff_answer(data: Dict[str, List[Dict[str, str]]], a: str, b: str) -> str:
    sa = get_sample(data, a)
    sb = get_sample(data, b)
    if sa and sb:
        try:
            comparison = sample_compare.compare_samples(data, a, b)
            return sample_compare.format_comparison_markdown(comparison)
        except ValueError as exc:
            return str(exc)

    mat_a = sa.get("material_nr") if sa else a
    mat_b = sb.get("material_nr") if sb else b
    diff = bom_diff(data, mat_a, mat_b)

    only_a = diff["only_a"][:8]
    only_b = diff["only_b"][:8]
    lines = [
        f"## BOM-Vergleich: {a} ↔ {b}",
        f"- Material A: `{mat_a}`",
        f"- Material B: `{mat_b}`",
        f"- BOM-Ähnlichkeit: **{diff['similarity']:.3f}**",
        f"- Gemeinsame Komponenten: {diff['common_count']}",
        f"- Kritische Unterschiede: {len(diff['critical_differences'])}",
        "",
        "### Nur in A / Ziel vorhanden",
        markdown_table(only_a, ["item", "component", "component_description", "function_group", "criticality"],
                       ["Item", "Komponente", "Beschreibung", "Gruppe", "Kritikalität"], max_rows=8),
        "",
        "### Nur in B / Kandidat vorhanden",
        markdown_table(only_b, ["item", "component", "component_description", "function_group", "criticality"],
                       ["Item", "Komponente", "Beschreibung", "Gruppe", "Kritikalität"], max_rows=8),
        "",
        "Quelle: `bom_components.csv`, `03_bom_similarity_rules.md`."
    ]
    return "\n".join(lines)


def build_defects_answer(data: Dict[str, List[Dict[str, str]]], sample_id: Optional[str] = None) -> str:
    rows = defects_for_sample(data, sample_id) if sample_id else data.get("defects", [])
    rows = sorted(rows, key=lambda x: (x.get("status") != "open", x.get("severity") != "High"))
    title = f"## Defects für {sample_id}" if sample_id else "## Defects aller Prüfmuster"
    return title + "\n\n" + markdown_table(rows, ["defect_id", "local_id", "severity", "status", "defect_type", "impact_on_reuse", "related_test_id", "action"],
                           ["Defect", "Muster", "Severity", "Status", "Typ", "Reuse Impact", "Test", "Maßnahme"], max_rows=20) + "\n\nQuelle: `defects.csv`."


def build_order_answer(data: Dict[str, List[Dict[str, str]]], material: Optional[str], test_type: Optional[str]) -> str:
    rec = recommend_reuse_or_order(data, material, test_type)
    lines = [
        "## Bestell-/Reuse-Entscheidung",
        f"- Angefragte Materialnummer: `{rec['requested_material_nr']}`",
        f"- Angefragter Test: `{rec['requested_test_type']}`",
        f"- Empfehlung: **{rec['decision']}**",
        "",
    ]
    if rec["best_candidate"]:
        b = rec["best_candidate"]
        lines.extend([
            "### Bester Kandidat",
            f"- Muster: **{b['local_id']}**",
            f"- Material: {b['material_nr']}",
            f"- Status: {b['status']} ab {b['availability_from']}",
            f"- BOM-Ähnlichkeit: {b['bom_similarity']}",
            f"- Health Score: {b['health_score']}, Reuse Score: {b['reuse_score']}",
            f"- Test erlaubt: {b['test_ok']} ({b['test_reason']})",
            "",
        ])
    lines.append("### Top-Kandidaten")
    lines.append(markdown_table(rec["candidates"], ["local_id", "material_nr", "status", "availability_from", "health_score", "reuse_score", "bom_similarity", "test_ok", "decision_score"],
                                ["Muster", "Material", "Status", "Verfügbar ab", "Health", "Reuse", "BOM Sim", "Test OK", "Score"], max_rows=8))
    lines.append("\nQuelle: `samples.csv`, `availability.csv`, `bom_components.csv`, `test_catalog.csv`, `defects.csv`, `07_ordering_process.md`.")
    return "\n".join(lines)


def maybe_handle_structured_question(question: str, data: Dict[str, List[Dict[str, str]]], history: Optional[List[Dict[str, str]]] = None) -> Optional[Dict[str, Any]]:
    q = (question or "").lower()
    entities = extract_entities(question, history)
    sample_ids = entities["sample_ids"]
    material_ids = entities["material_ids"]
    test_types = entities["test_types"]
    sample_id = sample_ids[0] if sample_ids else None
    material = material_ids[0] if material_ids else None
    test_type = test_types[0] if test_types else None

    # 1) Difference first, because follow-up questions like "wo unterschiedlich?" rely on history.
    if any(w in q for w in ["unterschied", "unterschiedlich", "unterscheiden", "diff", "anders", "passt das ähnliche", "passt das aehnliche", "passt der kandidat", "ersatz", "vergleichsmuster"]):
        ids = sample_ids
        mats = material_ids
        if len(ids) >= 2:
            return {"answer": build_diff_answer(data, ids[0], ids[1]), "sources": ["bom_components.csv"]}
        if len(mats) >= 2:
            return {"answer": build_diff_answer(data, mats[0], mats[1]), "sources": ["bom_components.csv"]}
        if len(ids) == 1:
            sims = similar_samples(data, ids[0], limit=1)
            if sims:
                return {"answer": build_diff_answer(data, ids[0], sims[0]["local_id"]), "sources": ["bom_components.csv"]}
        return {"answer": "Für einen Unterschiedsvergleich brauche ich zwei Muster oder zwei Materialnummern, z. B. `4301828993017651 und 4301827613015290`.", "sources": []}

    # 2) Order / reuse questions.
    if any(w in q for w in ["bestellen", "bestell", "neubestellung", "order", "reuse", "wiederverwendung", "wiederverwenden"]):
        return {"answer": build_order_answer(data, material, test_type), "sources": ["samples.csv", "availability.csv", "bom_components.csv", "test_catalog.csv"]}

    # 3) Similarity / BOM / configuration.
    if any(w in q for w in ["ähnlich", "aehnlich", "similar", "bom", "config", "konfiguration"]):
        if len(sample_ids) >= 2 and any(w in q for w in ["warum", "wieso", "weshalb", "passt", "ersatz", "vergleich"]):
            return {"answer": build_diff_answer(data, sample_ids[0], sample_ids[1]), "sources": ["samples.csv", "bom_components.csv", "test_runs.csv", "defects.csv"]}
        target = sample_id or material
        if target:
            return {"answer": build_similar_answer(data, target), "sources": ["bom_components.csv"]}
        if "bom" in q and any(w in q for w in ["welche", "liste", "zeigen", "zeige"]):
            return {"answer": sample_compare.similar_bom_overview(data), "sources": ["samples.csv", "bom_components.csv"]}
        return {"answer": "Bitte nenne eine Muster-ID oder Materialnummer, z. B. `4301828993017651` oder `4897.B4T.0S3`.", "sources": []}

    # 4) Allowed tests.
    if sample_id and any(w in q for w in ["dürfen", "duerfen", "darf", "noch gemacht", "noch machen", "machen darf", "machen dürfen", "machen duerfen", "erlaubt", "freigegeben"]):
        return {"answer": build_allowed_tests_answer(data, sample_id), "sources": ["test_catalog.csv", "samples.csv", "defects.csv"]}

    # 5) Specific test history / test catalog.
    if any(w in q for w in ["testarten", "was sind das für test", "was sind das fuer test", "testkatalog"]):
        return {"answer": build_tests_answer(data, None), "sources": ["test_catalog.csv"]}

    if sample_id and any(w in q for w in ["tests gesehen", "testhistorie", "welche tests", "gelaufen", "durchgeführt", "durchgefuehrt"]):
        return {"answer": build_tests_answer(data, sample_id), "sources": ["test_runs.csv"]}

    # 6) Defects.
    if any(w in q for w in ["defect", "fehler", "auffälligkeit", "auffaelligkeit", "mängel", "maengel"]):
        return {"answer": build_defects_answer(data, sample_id), "sources": ["defects.csv"]}

    # 7) Health Score.
    if "health" in q or "score" in q or "zustand" in q:
        return {"answer": build_health_answer(data), "sources": ["samples.csv", "test_runs.csv", "defects.csv"]}

    # 8) Availability.
    if any(w in q for w in ["verfügbar", "verfuegbar", "available", "fügbarkeit", "verfügbarkeit"]):
        return {"answer": build_available_answer(data), "sources": ["samples.csv", "availability.csv"]}

    # 9) Sample pass.
    if sample_id and any(w in q for w in ["musterpass", "details", "übersicht", "uebersicht", "zeige", "status"]):
        return {"answer": build_sample_pass_answer(data, sample_id), "sources": ["samples.csv", "test_runs.csv", "defects.csv"]}

    return None
