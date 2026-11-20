# Aktueller Stand von Chatidy

**Nachprüfung GitHub 2026-11-14:** Der unten als offen beschriebene Fokus-PR ist inzwischen **PR #9, gemergt**; aktueller `main`-HEAD `8fe4da20f4ca`. GitHub-Actions-Workflow „Tests“ auf diesem Commit erfolgreich. Die damalige GraphQL-Fehlermeldung bleibt als historischer Verlauf stehen. Weiterhin offen: manueller Echttest REAL-001 und die bestehenden Backlog-/Remote-Grenzen.


**Stand:** 2026-11-14 · **Basis-Commit:** `8e19e783def2045bb08798478973918ba2ec6ea7` auf `main`
**Stand:** 2026-11-14 · **Basis-Commit:** `f648669` auf `main`

- **Läuft:** Lokaler Import mit Vorschau/Batch-Bestätigung, SQLite/FTS5, Ordner,
  Tags, Regeln, Review und JSON-Export. Dreigeteilte Oberfläche (PR #11) sowie einklappbare/verstellbare
  Seitenleisten (PR #12) und größere Navigationssymbole (PR #13) gemergt. Seit PR #12: Bereiche „Ordner & Gruppen“, „Intelligente Ordner“ und
  „Tags“ einklappbar; Navigation und Leseansicht per Ziehen/Pfeiltasten verstellbar
  (Doppelklick setzt zurück, Breiten nur im Browser gespeichert); Anzahl hinter
  Archiviert, Ohne Gruppe und Themencluster. `/api/stats` liefert zusätzlich
  `archived` und `unfiled` (additiv, bestehende Felder unverändert).
  Tests lokal: 113 entdeckt, 103 bestanden, 10 native Windows-Tests übersprungen;
  Chromium-Browsertest 3/3 erfolgreich. Nur synthetische Daten. Keine Änderungen
  an Import-, Job-Storage-, Migrations- oder Schemacode.
- **PROV-001 (2026-11-20):** Format-Adapter mit ausdrücklicher Erkennung (Mehrdeutigkeit = Abbruch;
  Claude-ähnliche `messages`-Varianten werden nicht mehr als Extractor gelesen), Schema 5 mit
  `conversations.provider` (Bestand `chatgpt`), API-Filter und Anbieterzählung. Dabei behoben:
  Vorschau gegen noch nicht migrierte Bibliothek hätte alle Chats als „unklare Identität“ gemeldet.
  Tests: 123 (10 Windows-Skips), Browser-Smoke lokal bestanden. Noch keine UI-Änderung.
- **CGPT-001 (2026-11-20):** ChatGPT-Denkprozesse erscheinen in der Leseansicht als eingeklappter
  Block statt „[Nicht-textueller Inhalt]“. Nur Anzeige (`web/reading.js`), keine Import-, Schema- oder
  Indexänderung. Tests: Node-Logiktest (über `tests/test_reading_view.py`, ohne Node übersprungen),
  Metadaten-/Reimport-Test, HTTP-Auslieferung; Playwright-Browsertest mit Chrome in der Cloud-Session
  bestanden (synthetisch). Sichtprüfung mit echtem Export durch den Nutzer: passt (2026-11-20).
- **Offen:** REAL-001 (manueller Echttest durch
  Nutzer). META-001, SCALE-001, UX-001 (Rest), KNOW-001, AUTO-001 (Gruppenvorschläge
  für viele Chats), DATA-002 bleiben Backlog. Neu geplant (nur Doku, kein Code):
  Mehrere Chat-Anbieter inkl. Claude-Export, ROADMAP Phase 6 / PROV-001 bis PROV-003.
  Claude- und ChatGPT-Exportstruktur am 2026-11-20 anhand echter Exporte (nur Schlüssel) geprüft;
  Claude-Zweige bestätigt. Neu im Backlog: CGPT-001, PROV-004.
  Nur Loopback; kein Remote-Login (Centrality F-02). Kein manueller Windows-11-Test
  der neuen Oberfläche.
- **Nächster Schritt:** Oberfläche lokal ausprobieren und Rückmeldung geben; danach
  REAL-001 nach der [Echttest-Checkliste](docs/manueller-echttest.md).
