# Chatidy – Produkt-Roadmap

Stand: Nutzbarkeitsdurchlauf auf main `8e19e78` (2026-11-14). Legende: **Implementiert und getestet**,
**Teilweise implementiert**, **Offen**, **Blockiert**. Neue Funktionen dieses
Durchlaufs werden erst nach ihren Tests hochgestuft; private Exportdaten bleiben lokal.

Aktueller Fokus: Nutzbarkeit und Verständlichkeit. Passende Startkategorien und
kompakte Dokumentation sind umgesetzt (FOCUS-001). Nächster Nachweis ist der
lokale manuelle Echttest durch den Nutzer (REAL-001); dieser bleibt offen.
Weitere Import-/Storage-Härtung und neue Plattformfälle nur auf ausdrücklichen Auftrag.
Die folgenden offenen Themen sind Backlog, keine automatisch folgenden Aufträge.

## Phase 1 – Exportkompatibilität und Datenintegrität

- **Implementiert und getestet:** klassische und nummerierte offizielle
  Konversationsdateien, explizite Archivklassifizierung, gemeinsame Segment-Batches.
- **Implementiert und getestet:** Schema-4-Migration auf gesprächsbezogene
  Nachrichtenidentität; IDs/Bestandsdaten/Reihenfolge bleiben erhalten.
- **Implementiert und getestet:** schreibfreie Import-Vorschau, einmalige
  Batch-Bestätigung, automatische idempotente Fälle und getrennte nicht destruktive
  Entscheidungen für ältere bzw. abweichende/unvollständige Versionen.
- **Implementiert und getestet:** Graphprüfung, atomare Transaktionen, konservativer
  Reimport-Schutz, lokales Staging/Wiederaufnahme sowie Windows-/Linux-Backend.
  Neue Implementierung: CI 43561857600 mit Python 3.10/3.11/3.13 auf beiden Hosts.
- **Teilweise implementiert:** große Exporte (Streaming/Jobs; 200/350-MB-Limits,
  Einzelobjekte benötigen RAM; keine unbegrenzte Skalierbarkeit).
- **Teilweise implementiert:** Zusatzressourcen/Manifeste werden inventarisiert;
  ihre noch ungeprüften Schemas werden nicht als unterstützt behauptet.
- **Offen:** validierte Manifest-Gesamtzahlen, komplexe Mehrversions-/Zweigrekonstruktion
  und überlappende Gesprächs-Snapshots. Fehlende letzte Segmente sind ohne
  vertrauenswürdige Gesamtzahl nicht nachweisbar. Details: TASKS.md.

## Phase 2 – Organisation und UX

- Implementiert und getestet: Ordner, Tags, Mehrfachauswahl (geladene Ergebnisse),
  zusätzliche Drag-and-drop-Zuordnung, gespeicherte Suchansichten, Regeln, Review.
- Implementiert und getestet (Browser, synthetisch): dreigeteilte Oberfläche
  (Navigation | Chat-Liste | Leseansicht), Import auf eigener Seite, Tag-Filter in der Navigation.
- Teilweise implementiert: intelligente Sammlungen, Filter/Suche, Markdown/Code
  (FTS5, sichere Textdarstellung, abgesetzte Codeblöcke; keine umfassende Markdown-Renderpipeline).
- Offen: eigenständige Favoriten, fortgeschrittene Filter, größere Bulk-Workflows.

## Phase 3 – Lokale Intelligenz

- Teilweise implementiert: explizite Ollama-Vorschläge und deterministische Themencluster.
- Offen: semantische Suche, lokale Embeddings, erklärbare Kategorisierungsvorschläge,
  Konfidenzwerte und Feedback-Lernen. Keine autonome Klassifikation ohne Sicherheitsgrenzen.

## Phase 4 – Knowledge Management

- Teilweise implementiert: JSON-Export und lokale Import-/Export-APIs.
- Offen: verwandte Gespräche, Zusammenfassungen, Wissensgraph, Volltext-/Vektorkombination,
  Projektwissen, Medienbibliothek und Markdown-Export.

## Phase 5 – Integration

- Teilweise implementiert: unabhängiger JSON-Adapter für chatgpt-conversation-extractor.
- Offen: optionale Anbindung an instakram, chat-organizer-extension,
  chatgpt-cost-dashboard und personal-platform; keine verpflichtende Kopplung.

## Verifikationsgrenzen

Synthetische und CI-Ergebnisse sind kein Test mit dem privaten Originalexport.
Aktuellen konkreten Test-/CI-Nachweis und Einschränkungen in aktuellerStand.md lesen.
