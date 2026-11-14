# Aktueller Stand von Chatidy

**Nachprüfung GitHub 2026-11-14:** Der unten als offen beschriebene Fokus-PR ist inzwischen **PR #9, gemergt**; aktueller `main`-HEAD `8fe4da20f4ca`. GitHub-Actions-Workflow „Tests“ auf diesem Commit erfolgreich. Die damalige GraphQL-Fehlermeldung bleibt als historischer Verlauf stehen. Weiterhin offen: manueller Echttest REAL-001 und die bestehenden Backlog-/Remote-Grenzen.


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
  [CI für Implementierungscommit 5d3ce49](https://github.com/muk4li/chatidy/actions/runs/43595514082)
  prüft Linux/Windows × Python 3.10/3.11/3.13. Nur synthetische Daten.
- **Offen:** PR-Erstellung konkret versucht, GitHub-GraphQL-API liefert `Forbidden`.
  Branch gepusht, kein Merge. [PR anlegen](https://github.com/muk4li/chatidy/pull/new/chore/focus-usability).
  REAL-001, manueller Echttest durch Nutzer. META-001, SCALE-001,
  UX-001, KNOW-001 und DATA-002 bleiben Backlog (TASKS.md), kein automatischer
  Folgeauftrag. Nur Loopback; kein Remote-Login (Centrality F-02).
  Kein manueller Windows-11-Test mit echtem Export erfolgt.
- **Nächster Schritt:** Diesen Nutzbarkeits-PR prüfen, danach lokal die
  [Echttest-Checkliste](docs/manueller-echttest.md) durchführen; ausschließlich
  geschwärzte technische Ergebnisse zurückmelden. Fokus auf Verständlichkeit;
  weitere Import-/Storage-Härtung nur auf ausdrücklichen Nutzerauftrag.
