# Aktueller Stand von Chatidy

**Stand:** 2026-11-14 · **Basis-Commit:** `8fe4da2` auf `main` (Branch `feat/ui-three-pane`)

- **Läuft:** Lokaler Import mit Vorschau/Batch-Bestätigung, SQLite/FTS5, Ordner,
  Tags, Regeln, Review und JSON-Export (FOCUS-001 mit PR #9 gemergt). Neu auf diesem
  Branch: dreigeteilte Oberfläche (Navigation | Chat-Liste | Leseansicht), Import
  und Jobverwaltung auf eigener Seite, einklappbarer Ordnerbaum, Tag-Filter in der
  Navigation, abgesetzte Codeblöcke (nur Text). Behoben: eine veraltete
  Importstatus-Abfrage konnte die ID eines neu gestarteten Imports löschen.
  Browsertest korrigiert (asynchrone `waitForFunction`-Bedingungen warteten nicht).
  Tests lokal: 112 entdeckt, 102 bestanden, 10 native Windows-Tests übersprungen;
  Chromium-Browsertest 12/12 erfolgreich. Nur synthetische Daten. Keine Änderungen an
  Import-, Job-Storage-, Datenbank- oder Servercode.
- **Offen:** PR-Review und CI für diesen Branch. REAL-001 (manueller Echttest durch
  Nutzer). META-001, SCALE-001, UX-001 (Rest), KNOW-001, DATA-002 bleiben Backlog.
  Nur Loopback; kein Remote-Login (Centrality F-02). Kein manueller Windows-11-Test
  der neuen Oberfläche.
- **Nächster Schritt:** Oberfläche lokal ausprobieren und Rückmeldung geben; danach
  REAL-001 nach der [Echttest-Checkliste](docs/manueller-echttest.md).
