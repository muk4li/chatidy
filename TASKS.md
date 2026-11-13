# Operatives Backlog

## EXP-001 – Offizielle Segmentarchive erkennen
- Priorität: P0; Status: Teilweise implementiert (lokale Regressionen erfolgreich; aktuelle Windows-CI ausstehend).
- Komponenten: Importer, Archivinventar, Jobvorschau. Abhängigkeiten: keine.
- [x] conversations.json und numerisch sortierte conversations-NNN.json auswählen.
- [x] Fehlende/doppelte/beschädigte erforderliche Segmente kontrolliert ablehnen.
- [x] Metadaten, DAT, HTML, Manifeste und unbekannte Extras separat inventarisieren.
- [x] Zusatzdateien weder ausführen noch ungeprüft als Chats parsen.
- Akzeptanz: ein gemeinsamer Batch für 000–007 unabhängig von ZIP-Reihenfolge.
- Tests: klassische/segmentierte/Extractor-Archive, Extras, Lücken, CRC/JSON,
  Größenlimits, Mehrdeutigkeit und doppelte Konversations-IDs.

## DATA-001 – Nachrichtenidentität pro Gespräch
- Priorität: P0; Status: Teilweise implementiert (Code und lokale Regressionen erfolgreich; aktuelle Windows-CI ausstehend).
- Komponenten: SQLite, Migrationen, upsert, Details/Export, FTS5. Abhängigkeiten: keine.
- [x] Globale Kollisionsursache synthetisch reproduzieren.
- [x] Bestehende IDs/Metadaten/Reihenfolge verlustfrei per Migration erhalten.
- [x] Gleiche ID in verschiedenen Chats erlauben, doppelte IDs im selben Chat ablehnen.
- Akzeptanz: kein fremder Chat wird überschrieben; Einzeldatei danach Gesamt-ZIP ist idempotent.
- Tests: Migration von Schema 3, Rollback, FKs, FTS, Tags/Review/Ordner und Reimport.

## IMP-001 – Vorschau, Bestätigung und Batch-Konflikte
- Priorität: P0; Status: Offen.
- Komponenten: Jobs, HTTP, UI. Abhängigkeiten: EXP-001, DATA-001.
- [ ] Analyse/Staging von Änderungen an der Hauptbibliothek trennen.
- [ ] Inventar, Gesprächszahl, Konfliktklassen, Warnungen und grobe Speicherprognose zeigen.
- [ ] Eine Bestätigung pro Batch; keine globale Fehler-ignorieren-Option.
- [ ] Identische/neuere vollständige Chats sicher behandeln; ältere oder abweichende
  Chats nur nach eindeutiger klassenbezogener Wahl unverändert lassen oder abbrechen.
- Akzeptanz: ohne Bestätigung kein Chatimport; atomarer Batch mit Wiederaufnahme.
- Tests: HTTP/Browser, Vorschau ohne Bibliotheksänderung, Konfliktentscheidung,
  Abbruch/Wiederaufnahme, parallele Bibliotheksänderung, Windows/Linux-CI.

## META-001 – Noch unbekannte offizielle Zusatzschemas
- Priorität: P1; Status: Offen.
- Komponenten: Manifest-/Metadata-Adapter. Abhängigkeiten: EXP-001.
- [ ] Nur mit dokumentiertem Schema zukünftige Metadaten interpretieren.
- [ ] Keine privaten Exporte in Cloud/Repo anfordern; synthetische Beispiele nutzen.
- Akzeptanz: Schema-Validierung vor Nutzung; sensible Konto-/Werbedaten nicht unnötig persistieren.
- Tests: nicht vertrauenswürdige, fehlerhafte und zukünftige Manifestversionen.

## SCALE-001 – Größere Exporte und Speicherbudgets
- Priorität: P1; Status: Teilweise implementiert.
- Komponenten: Streaming, Jobs, Limits. Abhängigkeiten: IMP-001.
- [x] Streaming von JSON-Arrays und persistente Checkpoints.
- [ ] Konfigurierbare, getestete Speicherbudgets; Begrenzung großer Einzelobjekte.
- Akzeptanz: keine stillen Limit-Erhöhungen, keine unkontrollierte Extraktion.
- Tests: synthetische große Archive, BOM/Chunks, Abbruch und Speicherverbrauch.

## UX-001 – Organisation erweitern
- Priorität: P2; Status: Teilweise implementiert.
- Komponenten: UI, Suche. Abhängigkeiten: stabile P0-Importbasis.
- [x] Ordner, Tags, Review, Regeln, Mehrfachauswahl und zusätzliche Drag-Zuordnung.
- [ ] Favoriten, fortgeschrittene Filter, sichere Markdown-/Code-Darstellung.
- Akzeptanz: Rückwärtskompatibilität, Tastatur-/Mobile-Bedienung und kein XSS.
- Tests: API-, DOM- und echter Browsertest.

## KNOW-001 – Lokales Wissen und Integrationen
- Priorität: P3; Status: Offen.
- Komponenten: lokale Intelligenz, Exporte, optionale Adapter. Abhängigkeiten: P0/P1.
- [ ] Semantische Suche, Medienbibliothek, Wissensgraph und optionale Projektintegrationen.
- Akzeptanz: lokale Verarbeitung, erklärbare Vorschläge, keine Pflicht-Cloud.
- Tests: pro abgeschlossener Funktion; bislang keine Implementierungsbehauptung.
