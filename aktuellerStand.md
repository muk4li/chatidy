# Aktueller Stand von Chatidy – 2026-11-20

## In `main` integriert

- PR #52: Wiederherstellung der zuvor in Feature-Branches gemergten
  L2-Bausteine #30–#38, auf Basis der bereits integrierten #25–#29/#33/#34.
- PR #53: weitere L2-Bausteine #39–#50 (mit #49 als Ersatz für den
  überlappenden signierten Callback-Test aus #45).
- Implementiert: explizite OIDC-Benutzereinschreibung, Schema 7/8,
  serverseitige Login-Challenges und Sessions, kontoabhängige SQLite- und
  Importjob-Daten, private Routen, Authentik-Confidential-Client-Code,
  Offline-Eigentümermigration mit Bestätigung, signierte Testtokens.
- Der normale Loopback-Einzelnutzermodus funktioniert weiterhin. Der Nutzer
  hat die bestehende Oberfläche nach #52 lokal erfolgreich ausprobiert.
- GitHub-Actions für den Merge von #53 war erfolgreich; die L2-Codebasis
  wurde aber **nicht** mit echtem Authentik oder live im Internet abgenommen.

## Laufende Änderung – ein gemeinsamer UX-Branch

F-001 bis F-009 sowie eine Dokumentationskorrektur werden zusammen geprüft.
Siehe [UX-Akzeptanz](docs/ux-f001-f009.md). **Das ist noch kein Merge und
noch keine Abnahme:** CI und Nutzerprüfung müssen abgeschlossen sein.

## Offene Betriebsfreigabe

- Echter authentik-OIDC-Login, Callback, Sessionablauf und Logout.
- HTTPS-Reverse-Proxy und Header-/Origin-/CSRF-Sicherheitsprüfung.
- Windows-/Linux-Rechte, isolierte Jobs, Mehrbenutzer-Negativtests in
  einer realitätsnahen Testumgebung.
- Vollständiges Backup und Restore; erst dann bestätigte Zuweisung des
  bestehenden Chatbestands an das Eigentümerkonto.
- Betreiber-Runbook, Freigabeentscheidung und Datenschutzpflichten.
- **Centrality später aktualisieren – NICHT ausgeführt und nicht Teil des
  aktuellen Chatidy-PRs.**

Weiterhin nur Loopback; keine öffentliche Bereitstellung und keine
automatische Bestandsmigration. [SERVICE.md](SERVICE.md) beschreibt
die Gates. Ältere Status-Snapshots sind in [docs/history.md](docs/history.md)
und der Git-Historie nachvollziehbar.
