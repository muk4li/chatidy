# Aktueller Stand von Chatidy

## Stand

**Stand:** 2026-11-22 · **Basis:** `main` [`6b42f842`](https://github.com/muk4li/chatidy/commit/6b42f8428fc94671fb6986220ff36c860873115c), einschließlich [PR #57](https://github.com/muk4li/chatidy/pull/57) (DEPLOY-001).

- **Implementiert auf main:** L2-/UX-Funktionen sowie explizite OIDC-Einschreibung, RS256/JWKS, PKCE, eigene Sitzungen, getrennte SQLite-/Jobbibliotheken (Schema 8), geschützte API-Routen und kontrollierte Offline-Eigentümermigration. Der lokale Loopback-Modus bleibt erhalten. Für den Container: HTTPS-Proxy-Gate, Secret-Datei, RP-Logout-Navigation, Liveness und Nicht-Root-Docker-/Compose ohne Host-Ports.
- **Tatsächliche Testbelege:** [GitHub Actions 44958269781](https://github.com/muk4li/chatidy/actions/runs/44958269781) für den `main`-Merge erfolgreich: neun Jobs einschließlich Windows/Linux-Python-Matrix, Stdlib-Läufen und synthetischem Docker-/Compose-Smoke. Die früheren lokalen 228 Tests und lokalen TLS-/Chromium-Prüfungen sind im [Runbook](docs/authentik-container-test.md) dokumentiert; kein echter VPS-/authentik-Test.
- **Nicht freigegeben:** Reale authentik-/Caddy-/Logout-/Zwei-Konten-Abnahme, Host-Dateirechte/Last, Backup samt vollständigem Restore, bestätigte Bestandsmigration und Betreiberfreigabe. Keine automatische Discovery, JIT-Einschreibung, Gruppenauthorisierung oder Backchannel-Logout. [Centrality ADR-007](https://github.com/muk4li/centrality/blob/main/docs/decisions/ADR-007-AUTHENTIK-VPS01.md) enthält weiterhin einen JIT-Vorschlag, der nicht zum implementierten Freigabemodell passt.
- **Feedback (ADR-011):** Nur als nicht dringliche Dokumentationsaufgabe vorgesehen; kein Formular und kein sicher öffentlich freigegebenes feetbackhurts-Ingest.
- **Nächster technischer Gate:** Integrationsabnahme aus [docs/authentik-container-test.md](docs/authentik-container-test.md) auf dem echten Zielsystem durch den Betreiber. Kein Deployment durch diese Doku-Synchronisierung.

## Protokoll

- 2026-11-22: Nachweis nach Merge von PR #57 und erfolgreicher `main`-CI 44958269781 in der Dokumentation konsolidiert; keine Live-Abnahme.

- 2026-11-21: DEPLOY-001 implementiert und lokal synthetisch geprüft; Runbook,
  Service-Vertrag und Container-CI ergänzt. Kein Deployment und kein Merge.
