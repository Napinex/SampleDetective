# Ausgewählte Datenprodukte: Wiederverwendung und Bestellprozess

## Datenprodukt 1: Reuse Recommendation Engine
Die Reuse Recommendation Engine bewertet, ob ein vorhandenes Prüfmuster erneut genutzt werden kann.
Sie nutzt Health Score, Reuse Score, Verfügbarkeit, Defects, Usage Hours, Testhistorie, Konfigurationsstand und BOM-Ähnlichkeit.

Typische Entscheidungslogik:
- Health Score >= 70: guter Kandidat
- Reuse Score >= 70: fachliche Prüfung sinnvoll
- keine offenen High-Severity-Defects
- Muster ist verfügbar oder rechtzeitig verfügbar
- BOM-Ähnlichkeit zum Zielmuster hoch genug
- gewünschter Test ist nach Regeln noch erlaubt

## Datenprodukt 2: Automatischer Musterbestell-Assistent
Der automatische Musterbestell-Assistent prüft vor einer Neubestellung:
1. Gibt es ein vorhandenes Muster mit gleicher Materialnummer?
2. Gibt es ein ähnliches Muster mit hoher BOM-Ähnlichkeit?
3. Ist das Muster verfügbar?
4. Sind offene Defects vorhanden?
5. Darf der gewünschte Test noch durchgeführt werden?
6. Ist Reuse wirtschaftlich sinnvoller als Neubestellung?

Wenn kein geeignetes Muster gefunden wird, empfiehlt der Assistent eine Neubestellung.



