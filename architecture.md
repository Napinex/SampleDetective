# Architektur – SampleSphere AI

## Ziel

SampleSphere AI kombiniert strukturierte Datenlogik und lokalen RAG, damit Prüfmuster-Fragen zuverlässig beantwortet werden können.

## Pipeline

1. Datenquellen:
   - CSV: Prüfmuster, BOM, Tests, Defects, Availability, Order Requests
   - Markdown: Regeln, Datenprodukte, Testdefinitionen, Musterpässe, Testberichte

2. Strukturierte Datenlogik:
   - Verfügbarkeit
   - Health Score
   - Testhistorie
   - erlaubte Tests
   - BOM-Ähnlichkeit
   - BOM-Differenzen
   - Reuse-/Bestellempfehlung

3. RAG:
   - Dokumente und CSV-Zeilen werden in Chunks zerlegt.
   - TF-IDF sucht relevante Chunks.
   - Optional bekommt Ollama die relevanten Chunks + Chat-Historie.

4. Chat:
   - Streamlit Chat UI
   - Verlauf bleibt in `storage/chat_history.json` erhalten.
   - Folgefragen nutzen die letzten Nachrichten als Kontext.

## Health Score

Berechnet aus:
- Usage Hours
- Anzahl Tests
- offene Defects
- offene High-Defects
- belastende Tests
- Status wie blocked oder maintenance

## Reuse Score

Berechnet aus:
- Health Score
- Verfügbarkeit
- Defect-Freiheit
- Testhistorie
- vorhandene Materialnummer/BOM


