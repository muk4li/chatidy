# Aktueller Stand von Chatidy

## Stand

**Stand:** 2026-11-21 · **Ausgangscommit:** `d84dc45baeb64dcfdb7ba9005b50f7eb7a8c3a32` (main)
**Branch:** `feature/authentik-container-readiness` · keine öffentliche Betriebsfreigabe.

- **Läuft:** L2-/UX-Code auf main, lokaler Einzelnutzermodus erhalten. DEPLOY-001:
  explizite HTTPS-Proxygrenze und Container-Listener, Secret-Dateialternative,
  optionaler Standard-RP-Logout mit Browsernavigation, lokaler Healthcheck,
  Startprüfung und Nicht-Root-Docker-/Compose-Vorlage ohne Host-Ports.
  Schema 8, bestehende Migrationen/Import-/Storage- und Autorisierungsregeln erhalten.
- **Geprüft:** ausschließlich synthetisch; vollständige Python-Suite mit gepinnten
  Auth-Paketen, separater Stdlib-Lauf, signierter Callback einschließlich realer
  Exchange/JWKS-Funktionen mit Transport-Fixtures und echter lokaler TLS-Proxy.
  Chromium und Container-Build/Compose-Smoke mit SQLite/FTS5, Zwei-Konten-/
  Jobisolation, bestätigter Bereinigung und Neustartpersistenz. 228 Tests mit Auth:
  218 bestanden, zehn Windows-Skips; ohne Auth-Pakete: 195 bestanden, 33 Skips
  (OIDC/TLS/Windows). Image lokal linux/amd64 gebaut (~139 MB).
  [CI 44949005054](https://github.com/muk4li/chatidy/actions/runs/44949005054)
  für Implementierungscommit `f662245`: erfolgreich, alle neun Jobs
  (Linux/Windows × 3.10/3.11/3.13, zwei Stdlib-Jobs und Container-Smoke).
  Branch gepusht; PR-Erstellung konkret mit GitHub-GraphQL `Forbidden` gescheitert.
  [PR anlegen](https://github.com/muk4li/chatidy/pull/new/feature/authentik-container-readiness).
  Kein PR-Erfolg/kein Merge behauptet, main unverändert.
- **Offen:** echte authentik-/Caddy-/Zwei-Konten-Abnahme, Zielrechte/Last,
  vollständiger Backup/Restore, bestätigte Bestandsmigration und Betreiberfreigabe.
  Keine Liveänderungen, produktiven Daten oder Änderungen an anderen Repos.
  Automatische Discovery, Gruppenrollen, JIT-Kontoanlage und Backchannel-Logout
  sind nicht implementiert; ADR-007/JIT-Widerspruch im Runbook dokumentiert.
- **Nächster Schritt:** Betreiber schließt Phase 3b ab und führt die
  [gemeinsame Abnahme](docs/authentik-container-test.md) privat durch.
  [SERVICE.md](SERVICE.md) bleibt maßgeblich; Centrality-Nachpflege separat später.

## Protokoll

- 2026-11-21: DEPLOY-001 implementiert und lokal synthetisch geprüft; Runbook,
  Service-Vertrag und Container-CI ergänzt. Kein Deployment und kein Merge.
