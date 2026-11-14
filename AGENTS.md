# Verbindlicher Entwicklungsablauf

- Vor Änderungen `git status`, `git fetch origin main` und den tatsächlichen
  Ausgangscommit prüfen; bestehende Nutzeränderungen erhalten. Bestehenden Code,
  Tests und Migrationen lesen, bevor neue Mechanismen gebaut werden.
- Bestehenden Checkout verwenden; Cloud-Tasks sind isoliert. Kein Worktree ohne
  ausdrücklichen Auftrag. Auf einem Feature-Branch in kleinen vollständigen
  Arbeitspaketen arbeiten. Keine unnötigen Pflichtabhängigkeiten hinzufügen.
- Ausschließlich synthetische Testdaten. Private Exporte, personenbezogene Inhalte,
  private IDs/Dateinamen, Datenbanken, Jobdateien und Secrets niemals committen
  oder pushen. Vor jedem Commit gestagte Dateiliste UND Inhalte prüfen.
- Local-first: keine Cloud-Dienste für Chatinhalte, kein automatisches Laden
  importierter URLs, Server weiterhin nur an Loopback binden.
- Datenbankänderungen versioniert und transaktional migrieren. Bestehende Daten
  erhalten; keine destruktive Bereinigung/Überschreibung ohne ausdrückliche
  Bestätigung. Reimport-, Graph-, Archiv- und Dateisystemschutz nicht umgehen.
- Für jede wesentliche Änderung Regressionstests ergänzen; vollständige Suite
  `python -m unittest discover -s tests -v` ausführen. HTTP-/Browsertests bei
  Workflowänderungen. Windows 11 nativ und Linux berücksichtigen; CI-Matrix
  Python 3.10/3.11/3.13 erhalten. Skips von bestandenen Tests unterscheiden.
- Keine Testergebnisse oder Plattformkompatibilität behaupten, die nicht
  tatsächlich verifiziert sind. CI für den jeweiligen Commit vor Merge prüfen.
- Vor Push erneut main prüfen. Kein Force-Push, kein Überschreiben fremder
  Änderungen. PR gegen main; Merge nur bei grüner CI und geklärten Risiken.
  Blockierte API-/PR-Aktionen offen dokumentieren, nicht als erledigt darstellen.
- README, aktuellerStand.md, ROADMAP.md und TASKS.md nach jedem abgeschlossenen
  Schritt aktualisieren. Bericht: Ausgangscommit, Änderung, Tests, Datenschutz,
  Commit/Push/PR/CI/Merge und verbleibende Grenzen. Geplantes nicht als fertig markieren.

# Übergreifende Architektur

- [Centrality](https://github.com/muk4li/centrality) besitzt die Gesamtarchitektur,
  die globale Reihenfolge und die Verträge zwischen den Repositories. Bei Änderungen
  mit Wirkung auf andere Repos (Hub-Anbindung, Remote-Auth, Netzwerkbindung, Packaging,
  Deployment) zuerst dessen `docs/START-HERE.md`, `DECISIONS.md` und `CURRENT-STATE.md`
  lesen. Code, Tests und die Regeln dieser Datei bleiben für Chatidy maßgeblich.
- Ist Centrality nicht erreichbar, die Lücke melden und keine grenzverändernden
  Entscheidungen treffen. Keine privaten Centrality-Inhalte in dieses öffentliche
  Repository kopieren.
