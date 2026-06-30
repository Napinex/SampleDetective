# Health Score Definition für Prüfmuster

Der Health Score beschreibt den technischen Zustand eines Prüfmusters auf einer Skala von 0 bis 100.
Ein hoher Wert bedeutet, dass das Muster voraussichtlich noch gut nutzbar ist.

Berechnungslogik:
Health Score = 100
- 0,10 Punkte je Usage Hour
- 1,5 Punkte je bereits gelaufenem Test
- 22 Punkte je offenem High-Defect
- 8 Punkte je offenem Medium/Low-Defect
- zusätzliche Abzüge für belastende Tests wie Dauerlauf, Feldtest, Thermal-Fade oder Korrosion

Interpretation:
- 85 bis 100: sehr guter Zustand
- 70 bis 84: wiederverwendbar, fachliche Prüfung empfohlen
- 55 bis 69: eingeschränkt nutzbar, Risiko prüfen
- unter 55: eher nicht wiederverwenden
- unter 40: nur noch für nicht-kritische Analysen oder EOL-Dokumentation

Der Health Score ersetzt keine Freigabe, sondern dient als Entscheidungsunterstützung.



