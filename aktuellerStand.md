# Aktueller Stand von Chatidy

**Stand:** 2026-11-14 · **Basis-Commit:** `8e19e783def2045bb08798478973918ba2ec6ea7` auf `main`

- **Läuft:** Lokaler Import mit Vorschau/Batch-Bestätigung, SQLite/FTS5, Ordner,
  Tags, Regeln, Review und JSON-Export. FOCUS-001 auf `chore/focus-usability`:
  acht Startkategorien nur für neue DBs; Standardpfad im Projektordner, beim
  Serverstart auch für bestehende Job-APIs; CHATIDY_DB bleibt vorrangig.
  Kein neues Schema, keine Änderungen an Import-/Job-Storage-/Windows-Code.
  README von 415 auf 120 Zeilen gekürzt; [Importdetails](docs/import-details.md)
  und [Durchlauf-Historie](docs/history.md) ausgelagert. Tests: 112 entdeckt,
  102 bestanden, zehn native Windows-Tests lokal übersprungen.
  Chromium-Browsertest erfolgreich (Import, Reimport, Organisation, Jobs, Mobil).
  CI-/PR-Nachweis nach Push prüfen. Nur synthetische Daten.
- **Offen:** REAL-001, manueller Echttest durch Nutzer. META-001, SCALE-001,
  UX-001, KNOW-001 und DATA-002 bleiben Backlog (TASKS.md), kein automatischer
  Folgeauftrag. Nur Loopback; kein Remote-Login (Centrality F-02).
  Kein manueller Windows-11-Test mit echtem Export erfolgt.
- **Nächster Schritt:** Diesen Nutzbarkeits-PR prüfen, danach lokal die
  [Echttest-Checkliste](docs/manueller-echttest.md) durchführen; ausschließlich
  geschwärzte technische Ergebnisse zurückmelden. Fokus auf Verständlichkeit;
  weitere Import-/Storage-Härtung nur auf ausdrücklichen Nutzerauftrag.
