# BOM-Ähnlichkeit und Konfigurationsvergleich

Die BOM-Ähnlichkeit wird über die Komponentenlisten zweier Materialnummern berechnet.
Im System wird dafür eine Jaccard-Ähnlichkeit genutzt:

BOM Similarity = gemeinsame Komponenten / alle unterschiedlichen Komponenten

Eine hohe Ähnlichkeit bedeutet, dass viele Bauteile identisch sind. Unterschiede bei kritischen Komponenten
wie Housing, Sealing, Sensorics oder Hydraulics müssen besonders geprüft werden.

Bewertung:
- >= 0,95: nahezu identisch, sehr guter Reuse-Kandidat
- 0,85 bis 0,94: ähnlich, technische Prüfung notwendig
- 0,70 bis 0,84: teilweise ähnlich, Einsatzfall kritisch prüfen
- < 0,70: eher keine direkte Wiederverwendung

Wichtige BOM-Fragen:
- Welche Komponenten fehlen im Kandidaten?
- Welche Komponenten sind zusätzlich vorhanden?
- Betreffen Unterschiede kritische Funktionsgruppen?
- Passt die Konfiguration zum geplanten Test?



