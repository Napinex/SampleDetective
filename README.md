# SampleSphere AI

**Local Second-Hand Sample Market Assistant** für Prüfmuster, BOM-Vergleich, Tests, Defects, Health Score, Reuse und Bestellprozess.

Das Projekt ist ein lokaler RAG-/LLM-Assistent mit dokumentierten Prüfmusterdaten für den Second-Hand-Sample-Market.

## Was ist neu?

- Sehr simple Streamlit-Übersicht mit Bosch-Farbwelt
- Lokaler Chat mit Verlauf: Folgefragen behalten Kontext
- Strukturierte Antworten aus CSV-Daten ohne LLM-Wartezeit
- Optionales lokales LLM über Ollama
- RAG-Index über Dokumente und CSV-Zeilen
- Mehr fachlicher Kontext:
  - Prüfmuster
  - Verfügbarkeit
  - BOM-Komponenten
  - Testkatalog
  - Testläufe
  - Defects
  - Usage Hours
  - Health Score
  - Reuse Score
  - Bestell-/Wiederverwendungsprozess

## Start unter Windows

Im Projektordner PowerShell öffnen und ausführen:

```powershell
.\run_windows.bat
```

Die Datei erstellt eine virtuelle Umgebung, installiert Pakete, baut den Index und startet die App.

Danach öffnet sich meistens automatisch:

```text
http://localhost:8501
```

## Ollama optional

Für echte lokale LLM-Antworten kannst du Ollama installieren und ein Modell laden:

```powershell
ollama pull llama3.2:3b
```

In der App ist `llama3.2:3b` voreingestellt.  
Für stärkere, aber langsamere Antworten kannst du `llama3.1:8b` nutzen.

Ohne Ollama funktioniert die App trotzdem:
- strukturierte CSV-Fragen
- Übersichten
- RAG-Fallback-Quellen

## Gute Testfragen

```text
Welche Prüfmuster sind aktuell verfügbar?
```

```text
Zeige mir den Musterpass für 4301828993017651.
```

```text
Was hat 4401831543017350 schon für Tests gesehen?
```

```text
Was sind das für Testarten?
```

```text
Welche Tests dürfen mit 0805038020400411 noch gemacht werden?
```

```text
Gibt es ähnliche Konfigurationen zu 4301828993017651 anhand der BOM?
```

```text
Wo unterscheiden sich 4301828993017651 und 4301827613015290?
```

```text
Worin unterscheiden sich die ähnlichen Muster zu 4301828993017651?
```

```text
Gibt es ähnliche Muster zur global_id 019DCC3C-5800-7D5E-BF60-7A8B9CDAEBFC?
```

```text
Passt 4301800000000012 als Ersatz für 4301828993017651?
```

```text
Soll ich ein neues Muster bestellen oder ein vorhandenes wiederverwenden?
```

## Vergleich ähnlicher Prüfmuster

Der Chat erkennt Fragen nach ähnlichen Prüfmustern und erklärt die Unterschiede strukturiert. Für konkrete Muster nutzt er `local_id` oder `global_id`.

Beispiel:

```text
Welche Prüfmuster sind ähnlich zu 4301828993017651?
```

Die Antwort enthält:

- Ausgangs-Prüfmuster mit `local_id`, `global_id` und Materialnummer
- gefundene ähnliche Prüfmuster mit Similarity Score
- gemeinsame BOM-Komponenten und gemeinsame Metadaten
- fehlende, zusätzliche oder abweichende BOM-Komponenten
- abweichende Konfiguration, Software-/Hardware-Version, Status, Standort, Lifecycle und Verfügbarkeit
- Tests, die nur eines der Muster gesehen hat
- offene Defects
- Einschätzung: `passt gut`, `bedingt passend` oder `nicht passend`

Genutzte Datenfelder:

- `samples.csv`: `local_id`, `global_id`, `material_nr`, `product_hierarchy_name`, `configuration_version`, `software_version`, `hardware_version`, `lifecycle_phase`, `availability_status`, `location`, `status`, `health_score`, `reuse_score`
- `bom_components.csv`: `material_nr`, `component`, `component_description`, `component_version`, `quantity`, `unit`, `function_group`, `criticality`, `reuse_relevance`
- `test_runs.csv`: `test_type`, `test_name`, `phase`, `result`, `usage_hours_added`, `test_bench`
- `availability.csv`: Status, Standort, Verfügbarkeit und Reservierung
- `defects.csv`: offene Defects, Severity und Reuse Impact

Wenn Felder in den Quelldaten fehlen, sagt die Antwort das explizit, z. B. `Dazu liegen in den Daten keine Informationen vor.`

Beispiel-Antwort, gekürzt:

```text
Ausgangsmuster: 4301828993017651 / global_id: ...
Ähnliches Muster: 4301800000012 / global_id: ...
Ähnlichkeit: 100 %

Gemeinsamkeiten:
- BOM: gemeinsame Hauptkomponenten
- gleiche Materialnummer

Unterschiede:
- andere Software-Version
- andere Lifecycle-/Verfügbarkeitsdaten
- Tests nur im Ausgangsmuster: PRESSURE_LEAK

Einschätzung:
bedingt passend: als Vergleichsmuster geeignet, aber nicht automatisch als direkter Ersatz.
```

## Tests

Die Vergleichsfunktion kann ohne zusätzliche Testabhängigkeit geprüft werden:

```powershell
python -m unittest tests.test_sample_comparison
```

## Daten ersetzen

Später kannst du echte Daten ersetzen durch:

- `data/records/samples.csv`
- `data/records/bom_components.csv`
- `data/records/test_runs.csv`
- `data/records/defects.csv`
- `data/records/availability.csv`
- `docs/records/*.md`

Danach Index neu bauen:

```powershell
python ingest.py
```

Oder einfach wieder:

```powershell
.\run_windows.bat
```

## Projektstruktur

```text
app.py
data_engine.py
rag_core.py
ingest.py
validate_data.py
requirements.txt
run_windows.bat
data/records/
docs/records/
storage/
```

## Hinweise

- `data_engine.py` beantwortet konkrete Tabellenfragen direkt.
- `sample_comparison.py` enthält Suche ähnlicher Prüfmuster, Mustervergleich und fachliche Ersatz-/Vergleichseinschätzung.
- `rag_core.py` baut den lokalen TF-IDF-RAG-Index.
- `app.py` enthält die Streamlit-Oberfläche und den Chatverlauf.
- Der Chatverlauf wird in `storage/chat_history.json` gespeichert.


