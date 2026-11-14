# Chatidy – Produkt-Roadmap

Stand: Ausgangspunkt main `c7702a6`. Legende: **Implementiert und getestet**,
**Teilweise implementiert**, **Offen**, **Blockiert**. Neue Funktionen dieses
Durchlaufs werden erst nach ihren Tests hochgestuft; private Exportdaten bleiben lokal.

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
- Teilweise implementiert: intelligente Sammlungen, Filter/Suche, Markdown/Code
  (FTS5 und sichere Textdarstellung; keine umfassende Markdown-Renderpipeline).
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
