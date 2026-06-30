# RAG-Definition im System

RAG steht für Retrieval-Augmented Generation. Die App durchsucht zuerst lokale Datenquellen und Dokumente.
Danach bekommt das lokale LLM nur die relevantesten Quellen-Chunks und die Frage.

Im System werden zwei Arten von Wissen kombiniert:
1. Strukturierte Daten: CSV-Tabellen zu Samples, BOM, Tests, Defects, Availability
2. Dokumentenwissen: Markdown-Regeln, Datenproduktbeschreibungen, Testdefinitionen und Musterpässe

Für konkrete Datenfragen nutzt die App zuerst die strukturierte Datenlogik.
Für Erklärfragen nutzt sie zusätzlich den lokalen RAG-Index und optional Ollama.



