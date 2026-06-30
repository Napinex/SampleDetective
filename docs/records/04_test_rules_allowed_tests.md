# Regeln: Welche Tests dürfen noch gemacht werden?

Ein Test darf nur empfohlen werden, wenn:
- das Muster nicht gesperrt ist
- kein offener High-Severity-Defect vorliegt
- der Health Score über dem Mindestwert des Tests liegt
- die Usage Hours unter dem testbezogenen Grenzwert liegen
- die BOM und der Software-/Konfigurationsstand dokumentiert sind
- der Test nicht durch die Historie ausgeschlossen ist

Belastende Tests:
- Dauerlauf / Endurance
- Field Drive / Fahrzeugtest
- Thermal-Fade-Test
- Korrosionstest

Diese Tests senken den Health Score stärker und dürfen bei alten oder beschädigten Mustern nicht mehr empfohlen werden.



