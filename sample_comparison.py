from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

SAMPLE_LOOKUP_FIELDS = ("local_id", "global_id", "sample_order", "leepa_id", "mes_id")


def to_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(float(str(value).replace(",", ".")))
    except Exception:
        return default


def sample_identifier(row: Optional[Dict[str, str]]) -> str:
    if not row:
        return ""
    return row.get("local_id") or row.get("sample_id", "")


def normalize_identifier(value: str) -> str:
    return (value or "").strip().upper().replace("44897.", "4897.")


def get_sample_by_identifier(data: Dict[str, List[Dict[str, str]]], identifier: str) -> Optional[Dict[str, str]]:
    needle = normalize_identifier(identifier)
    if not needle:
        return None

    for sample in data.get("samples", []):
        for field in SAMPLE_LOOKUP_FIELDS:
            if normalize_identifier(sample.get(field, "")) == needle:
                return sample
    return None


def tests_for_sample(data: Dict[str, List[Dict[str, str]]], sample_id: str) -> List[Dict[str, str]]:
    needle = normalize_identifier(sample_id)
    return [row for row in data.get("test_runs", []) if normalize_identifier(sample_identifier(row)) == needle]


def defects_for_sample(data: Dict[str, List[Dict[str, str]]], sample_id: str) -> List[Dict[str, str]]:
    needle = normalize_identifier(sample_id)
    return [row for row in data.get("defects", []) if normalize_identifier(sample_identifier(row)) == needle]


def availability_for_sample(data: Dict[str, List[Dict[str, str]]], sample_id: str) -> Optional[Dict[str, str]]:
    needle = normalize_identifier(sample_id)
    for row in data.get("availability", []):
        if normalize_identifier(sample_identifier(row)) == needle:
            return row
    return None


def components_for_material(data: Dict[str, List[Dict[str, str]]], material_nr: str) -> List[Dict[str, str]]:
    material = normalize_identifier(material_nr)
    return [row for row in data.get("bom", []) if normalize_identifier(row.get("material_nr", "")) == material]


def component_key(row: Dict[str, str]) -> str:
    return (row.get("component") or "").strip()


def component_label(row: Dict[str, str]) -> str:
    component = row.get("component", "")
    description = row.get("component_description", "")
    group = row.get("function_group", "")
    if description and component:
        return f"{description} ({component}, {group})"
    return component or description or "unbekannte Komponente"


def component_map(data: Dict[str, List[Dict[str, str]]], material_nr: str) -> Dict[str, Dict[str, str]]:
    return {component_key(row): row for row in components_for_material(data, material_nr) if component_key(row)}


def bom_similarity(data: Dict[str, List[Dict[str, str]]], mat_a: str, mat_b: str) -> float:
    a = set(component_map(data, mat_a))
    b = set(component_map(data, mat_b))
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _different_component_attributes(a: Dict[str, str], b: Dict[str, str]) -> Dict[str, Tuple[str, str]]:
    fields = ("component_description", "quantity", "unit", "function_group", "criticality", "reuse_relevance", "component_version")
    diffs: Dict[str, Tuple[str, str]] = {}
    for field in fields:
        av = a.get(field, "")
        bv = b.get(field, "")
        if av != bv:
            diffs[field] = (av, bv)
    return diffs


def compare_bom(data: Dict[str, List[Dict[str, str]]], mat_a: str, mat_b: str) -> Dict[str, Any]:
    a_map = component_map(data, mat_a)
    b_map = component_map(data, mat_b)
    a_keys = set(a_map)
    b_keys = set(b_map)
    common_keys = sorted(a_keys & b_keys)

    changed_common = []
    for key in common_keys:
        diffs = _different_component_attributes(a_map[key], b_map[key])
        if diffs:
            changed_common.append({"component": key, "base": a_map[key], "candidate": b_map[key], "differences": diffs})

    only_base = [a_map[key] for key in sorted(a_keys - b_keys)]
    only_candidate = [b_map[key] for key in sorted(b_keys - a_keys)]
    critical_differences = [
        row for row in only_base + only_candidate
        if row.get("criticality", "").lower() == "high"
    ]

    missing = []
    if not a_map:
        missing.append(f"Zur BOM von `{mat_a}` liegen keine Komponenten vor.")
    if not b_map:
        missing.append(f"Zur BOM von `{mat_b}` liegen keine Komponenten vor.")
    if a_map and b_map and not any("component_version" in row for row in list(a_map.values()) + list(b_map.values())):
        missing.append("Zu Komponenten-Versionen liegen in der BOM keine Informationen vor.")

    return {
        "material_a": mat_a,
        "material_b": mat_b,
        "similarity": bom_similarity(data, mat_a, mat_b),
        "common": [a_map[key] for key in common_keys],
        "only_base": only_base,
        "only_candidate": only_candidate,
        "changed_common": changed_common,
        "critical_differences": critical_differences,
        "missing_information": missing,
    }


def _compare_fields(base: Dict[str, str], candidate: Dict[str, str], fields: List[Tuple[str, str]]) -> Dict[str, Any]:
    same = []
    different = []
    missing = []
    for field, label in fields:
        left = base.get(field, "")
        right = candidate.get(field, "")
        if left and right:
            if left == right:
                same.append({"field": field, "label": label, "value": left})
            else:
                different.append({"field": field, "label": label, "base": left, "candidate": right})
        else:
            missing.append({"field": field, "label": label})
    return {"same": same, "different": different, "missing": missing}


def _test_sets(tests: List[Dict[str, str]]) -> Dict[str, set]:
    completed = {row.get("test_type", "") for row in tests if row.get("test_type") and row.get("result", "").lower() in {"passed", "warning", "failed"}}
    failed = {row.get("test_type", "") for row in tests if row.get("test_type") and row.get("result", "").lower() == "failed"}
    warning = {row.get("test_type", "") for row in tests if row.get("test_type") and row.get("result", "").lower() == "warning"}
    return {"completed": completed, "failed": failed, "warning": warning}


def compare_test_history(base_tests: List[Dict[str, str]], candidate_tests: List[Dict[str, str]]) -> Dict[str, Any]:
    base = _test_sets(base_tests)
    candidate = _test_sets(candidate_tests)
    missing = []
    if not base_tests:
        missing.append("Zum Ausgangsmuster liegen keine Testläufe vor.")
    if not candidate_tests:
        missing.append("Zum Kandidaten liegen keine Testläufe vor.")
    missing.append("Geplante Tests werden in den vorhandenen Daten nicht separat gepflegt.")

    return {
        "common_completed": sorted(base["completed"] & candidate["completed"]),
        "only_base_completed": sorted(base["completed"] - candidate["completed"]),
        "only_candidate_completed": sorted(candidate["completed"] - base["completed"]),
        "base_failed": sorted(base["failed"]),
        "candidate_failed": sorted(candidate["failed"]),
        "base_warning": sorted(base["warning"]),
        "candidate_warning": sorted(candidate["warning"]),
        "missing_information": missing,
    }


def _status_value(sample: Dict[str, str]) -> str:
    return sample.get("status_de") or sample.get("status") or "unbekannt"


def _assessment(comparison: Dict[str, Any]) -> Dict[str, str]:
    bom = comparison["bom"]
    config = comparison["configuration"]
    metadata = comparison["metadata"]
    candidate = comparison["candidate"]
    defects = comparison["defects"]

    score = bom["similarity"] * 100
    reasons = []

    if bom["critical_differences"]:
        score -= 18
        reasons.append("kritische BOM-Unterschiede vorhanden")
    if bom["changed_common"]:
        score -= 8
        reasons.append("gemeinsame Komponenten haben abweichende Attribute")
    if any(item["field"] == "software_version" for item in config["different"]):
        score -= 8
        reasons.append("Software-Version weicht ab")
    if any(item["field"] == "hardware_version" for item in config["different"]):
        score -= 6
        reasons.append("Hardware-Version weicht ab")
    if any(item["field"] == "lifecycle_phase" for item in metadata["different"]):
        score -= 5
        reasons.append("Lifecycle-Phase unterscheidet sich")
    if candidate.get("status", "").lower() not in {"available", "verfügbar"}:
        score -= 12
        reasons.append("Kandidat ist nicht frei verfügbar")
    if defects["candidate_high_open"] > 0:
        score -= 20
        reasons.append("Kandidat hat offene High-Defects")
    elif defects["candidate_open"] > 0:
        score -= 6
        reasons.append("Kandidat hat offene Defects")

    score = max(0, min(100, round(score)))
    if score >= 85:
        label = "passt gut"
    elif score >= 60:
        label = "bedingt passend"
    else:
        label = "nicht passend"

    if not reasons:
        reasons.append("hohe BOM-Übereinstimmung und keine harten Ausschlusskriterien in den vorhandenen Daten")

    direct_replacement = (
        label == "passt gut"
        and bom["similarity"] >= 0.95
        and not bom["critical_differences"]
        and not any(item["field"] in {"software_version", "hardware_version", "configuration_version"} for item in config["different"])
        and candidate.get("status", "").lower() == "available"
        and defects["candidate_high_open"] == 0
    )
    replacement_text = "als Ersatz grundsätzlich geeignet" if direct_replacement else "eher als Vergleichsmuster, nicht automatisch als direkter Ersatz"

    return {
        "label": label,
        "score": str(score),
        "replacement_text": replacement_text,
        "reason": "; ".join(reasons),
    }


def compare_samples(data: Dict[str, List[Dict[str, str]]], base_identifier: str, candidate_identifier: str) -> Dict[str, Any]:
    base = get_sample_by_identifier(data, base_identifier)
    candidate = get_sample_by_identifier(data, candidate_identifier)
    if not base:
        raise ValueError(f"Ich finde kein Ausgangs-Prüfmuster `{base_identifier}` im Datenbestand.")
    if not candidate:
        raise ValueError(f"Ich finde kein Kandidaten-Prüfmuster `{candidate_identifier}` im Datenbestand.")

    base_id = sample_identifier(base)
    candidate_id = sample_identifier(candidate)
    base_availability = availability_for_sample(data, base_id) or {}
    candidate_availability = availability_for_sample(data, candidate_id) or {}

    config_fields = [
        ("product_hierarchy_name", "Produkt-/Bremssystem-Familie"),
        ("configuration_version", "Konfiguration"),
        ("software_version", "Software-Version"),
        ("hardware_version", "Hardware-Version"),
        ("configuration_parameters", "Konfigurationsparameter"),
    ]
    metadata_fields = [
        ("status_de", "Status"),
        ("location", "Standort"),
        ("lifecycle_phase", "Lifecycle-Phase"),
        ("availability_status", "Verfügbarkeitsstatus"),
        ("availability_from", "Verfügbar ab"),
        ("availability_until", "Verfügbar bis"),
    ]

    comparison: Dict[str, Any] = {
        "base": base,
        "candidate": candidate,
        "base_availability": base_availability,
        "candidate_availability": candidate_availability,
        "bom": compare_bom(data, base.get("material_nr", ""), candidate.get("material_nr", "")),
        "configuration": _compare_fields(base, candidate, config_fields),
        "metadata": _compare_fields(base, candidate, metadata_fields),
        "tests": compare_test_history(tests_for_sample(data, base_id), tests_for_sample(data, candidate_id)),
        "defects": {
            "base_open": sum(1 for row in defects_for_sample(data, base_id) if row.get("status", "").lower() == "open"),
            "candidate_open": sum(1 for row in defects_for_sample(data, candidate_id) if row.get("status", "").lower() == "open"),
            "base_high_open": sum(1 for row in defects_for_sample(data, base_id) if row.get("status", "").lower() == "open" and row.get("severity", "").lower() == "high"),
            "candidate_high_open": sum(1 for row in defects_for_sample(data, candidate_id) if row.get("status", "").lower() == "open" and row.get("severity", "").lower() == "high"),
        },
    }
    comparison["assessment"] = _assessment(comparison)
    return comparison


def find_similar_samples(data: Dict[str, List[Dict[str, str]]], sample_id: str, top_k: int = 5) -> List[Dict[str, Any]]:
    base = get_sample_by_identifier(data, sample_id)
    if not base:
        raise ValueError(f"Ich finde kein Prüfmuster `{sample_id}` im Datenbestand.")

    base_id = sample_identifier(base)
    candidates = []
    for sample in data.get("samples", []):
        candidate_id = sample_identifier(sample)
        if candidate_id == base_id:
            continue
        comparison = compare_samples(data, base_id, candidate_id)
        assessment = comparison["assessment"]
        candidates.append({
            "local_id": candidate_id,
            "global_id": sample.get("global_id", ""),
            "material_nr": sample.get("material_nr", ""),
            "status": _status_value(sample),
            "location": sample.get("location", ""),
            "health_score": to_int(sample.get("health_score")),
            "reuse_score": to_int(sample.get("reuse_score")),
            "bom_similarity": round(comparison["bom"]["similarity"], 3),
            "similarity_percent": round(comparison["bom"]["similarity"] * 100),
            "fit": assessment["label"],
            "fit_score": to_int(assessment["score"]),
            "reason": assessment["reason"],
            "comparison": comparison,
        })

    candidates.sort(key=lambda row: (row["bom_similarity"], row["fit_score"], row["reuse_score"], row["health_score"]), reverse=True)
    return candidates[:top_k]


def _format_list(values: List[str], empty: str = "keine") -> str:
    values = [value for value in values if value]
    if not values:
        return empty
    return ", ".join(values[:8]) + (f" (+{len(values) - 8} weitere)" if len(values) > 8 else "")


def _format_component_list(rows: List[Dict[str, str]], empty: str = "keine") -> str:
    if not rows:
        return empty
    return "; ".join(component_label(row) for row in rows[:6]) + (f"; +{len(rows) - 6} weitere" if len(rows) > 6 else "")


def _format_differences(rows: List[Dict[str, Any]]) -> str:
    if not rows:
        return "keine"
    parts = []
    for row in rows[:8]:
        parts.append(f"{row['label']}: `{row['base']}` vs. `{row['candidate']}`")
    return "; ".join(parts)


def _format_missing(messages: List[Any]) -> str:
    text = []
    for item in messages:
        if isinstance(item, dict):
            text.append(f"Zu `{item.get('label')}` liegen in mindestens einem Muster keine Informationen vor.")
        elif item:
            text.append(str(item))
    return "\n".join(f"- {line}" for line in text)


def format_comparison_markdown(comparison: Dict[str, Any], include_heading: bool = True) -> str:
    base = comparison["base"]
    candidate = comparison["candidate"]
    bom = comparison["bom"]
    config = comparison["configuration"]
    metadata = comparison["metadata"]
    tests = comparison["tests"]
    defects = comparison["defects"]
    assessment = comparison["assessment"]

    heading = [
        f"## Vergleich: {sample_identifier(base)} <-> {sample_identifier(candidate)}",
        "",
    ] if include_heading else []

    missing_messages: List[Any] = []
    missing_messages.extend(bom["missing_information"])
    missing_messages.extend(config["missing"])
    missing_messages.extend(metadata["missing"])
    missing_messages.extend(tests["missing_information"])

    lines = heading + [
        f"**Ausgangsmuster:** {sample_identifier(base)} / global_id: `{base.get('global_id', 'nicht vorhanden')}`",
        f"**Ähnliches Muster:** {sample_identifier(candidate)} / global_id: `{candidate.get('global_id', 'nicht vorhanden')}`",
        f"**Ähnlichkeit:** {round(bom['similarity'] * 100)} %",
        "",
        "### Gemeinsamkeiten",
        f"- BOM: {len(bom['common'])} gemeinsame Komponenten; Beispiele: {_format_component_list(bom['common'])}",
        f"- Konfiguration/Metadaten: {_format_list([item['label'] for item in config['same'] + metadata['same']])}",
        f"- Testhistorie: {_format_list(tests['common_completed'])}",
        "",
        "### Unterschiede",
        f"- Nur im Ausgangsmuster: {_format_component_list(bom['only_base'])}",
        f"- Nur im ähnlichen Muster: {_format_component_list(bom['only_candidate'])}",
        f"- Abweichende gemeinsame BOM-Komponenten: {len(bom['changed_common'])}",
        f"- Abweichende Konfiguration: {_format_differences(config['different'])}",
        f"- Abweichende Status-/Lifecycle-/Verfügbarkeitsdaten: {_format_differences(metadata['different'])}",
        f"- Tests nur im Ausgangsmuster: {_format_list(tests['only_base_completed'])}",
        f"- Tests nur im ähnlichen Muster: {_format_list(tests['only_candidate_completed'])}",
        f"- Offene Defects: Ausgangsmuster {defects['base_open']} (High: {defects['base_high_open']}), Kandidat {defects['candidate_open']} (High: {defects['candidate_high_open']})",
        "",
        "### Einschätzung",
        f"**{assessment['label']}** ({assessment['score']} Punkte): {assessment['replacement_text']}.",
        f"Begründung: {assessment['reason']}.",
    ]

    if missing_messages:
        lines.extend(["", "### Fehlende Daten", _format_missing(missing_messages)])

    lines.append("")
    lines.append("Quelle: `samples.csv`, `availability.csv`, `bom_components.csv`, `test_runs.csv`, `defects.csv`.")
    return "\n".join(lines)


def explain_sample_differences(data: Dict[str, List[Dict[str, str]]], base_identifier: str, top_k: int = 5) -> str:
    base = get_sample_by_identifier(data, base_identifier)
    if not base:
        return f"Ich finde kein Prüfmuster `{base_identifier}` im Datenbestand."

    similar = find_similar_samples(data, sample_identifier(base), top_k=top_k)
    if not similar:
        return f"Zu `{base_identifier}` finde ich keine ähnlichen Prüfmuster mit verwertbarer BOM."

    lines = [
        f"## Ähnliche Prüfmuster mit erklärtem Unterschied zu {sample_identifier(base)}",
        "",
        f"Ausgangsmuster: **{sample_identifier(base)}** / global_id: `{base.get('global_id', 'nicht vorhanden')}` / Material: `{base.get('material_nr', '')}`",
        "",
        "| Muster | global_id | Material | Similarity | Einschätzung | Status |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for item in similar:
        lines.append(
            f"| {item['local_id']} | `{item['global_id']}` | {item['material_nr']} | {item['similarity_percent']} % | {item['fit']} | {item['status']} |"
        )

    for item in similar[:3]:
        lines.extend(["", format_comparison_markdown(item["comparison"], include_heading=True)])

    return "\n".join(lines)


def similar_bom_overview(data: Dict[str, List[Dict[str, str]]], top_k: int = 8) -> str:
    rows = []
    samples = data.get("samples", [])
    for left_index, base in enumerate(samples):
        for candidate in samples[left_index + 1:]:
            comparison = compare_samples(data, sample_identifier(base), sample_identifier(candidate))
            similarity = comparison["bom"]["similarity"]
            if similarity <= 0:
                continue
            rows.append({
                "base": sample_identifier(base),
                "candidate": sample_identifier(candidate),
                "base_material": base.get("material_nr", ""),
                "candidate_material": candidate.get("material_nr", ""),
                "similarity": round(similarity * 100),
                "fit": comparison["assessment"]["label"],
            })

    rows.sort(key=lambda row: row["similarity"], reverse=True)
    lines = [
        "## Prüfmuster mit ähnlicher BOM",
        "",
        "Ohne Ausgangsmuster liste ich die stärksten BOM-Paare im Datenbestand. Für eine Ersatzentscheidung ist danach ein Einzelvergleich sinnvoll.",
        "",
        "| Muster A | Muster B | Material A | Material B | BOM-Ähnlichkeit | Einschätzung |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows[:top_k]:
        lines.append(f"| {row['base']} | {row['candidate']} | {row['base_material']} | {row['candidate_material']} | {row['similarity']} % | {row['fit']} |")
    lines.append("")
    lines.append("Quelle: `samples.csv`, `bom_components.csv`.")
    return "\n".join(lines)
