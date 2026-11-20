# L2-Audit: gestapelte Pull Requests #25–#38 nach `main`

## Warum dieser Integrations-PR nötig ist

GitHub meldete #30–#32 und #35–#38 als **merged**, aber ihr Ziel war ein Feature-Branch statt `main`. Ein grüner oder geschlossener PR bedeutet nicht automatisch, dass sein Code im Standardbranch liegt. #52 ist ausdrücklich von dem geprüften `main`-Commit `99498d69a1034ba31a5163b1e248492353bda912` abgezweigt und zielt direkt zurück auf `main`.

| Ursprungs-PR | Ursprüngliches Ziel | Integration in #52 |
| --- | --- | --- |
| #25 Landing | `main` | Bereits auf `main`; unverändert behalten |
| #26 Inhaltsregeln | `main` | Bereits auf `main`; NON_TEXT-Fix im integrierten `db.py` ausdrücklich bewahrt |
| #27 Multi-Provider-Importhilfe | `main` | Bereits auf `main`; neue `web/index.html` und `web/style.css` nicht überschrieben |
| #28 L2a-Plan | `main` | Bereits auf `main` |
| #29 Benutzer-Schema 7 | `main` | Bereits auf `main`; Schema 7 im zusammengeführten Migrationsmodul erhalten |
| #30 Identitätslookup | Feature-Branch #29 | `chatidy/users.py`, `tests/test_users.py` |
| #31 Manuelle Einschreibung | Feature-Branch #30 | `chatidy/enroll.py`, `tests/test_enrollment.py` |
| #32 Konto- und Job-Speicher | Feature-Branch #31 | `chatidy/library_scope.py`, Änderungen an `db.py`, `job_storage.py`, `jobs.py`, `tests/test_account_library.py` |
| #33 Routenvertrag | `main` | Bereits auf `main`; `access_policy.py` und seine Tests vorhanden |
| #34 RS256/PKCE | `main` | Bereits auf `main`; `oidc.py`, Pins, CI und Tests vorhanden |
| **#35 Login-Zustand / Schema 8** | Feature-Branch #31 | **`chatidy/auth_state.py`, Schema 8 in `chatidy/migrations.py`, `tests/test_auth_state.py` und `tests/test_users_schema.py` integriert** |
| #36 HTTP-Session-Gate | Feature-Branch #35 | `chatidy/server.py` und begleitende Speicheränderungen; **`tests/test_http_auth_gate.py`** |
| #37 OIDC-Austausch | Feature-Branch #36 | `chatidy/oidc_exchange.py`, OIDC-Tests und bereits vorhandene #34-Abhängigkeiten |
| #38 Login/Callback/Logout | Feature-Branch #37 | `chatidy/server.py`, `tests/test_oidc_http.py`, **`tests/test_optional_auth.py`** |

## Überprüfung gegen den ursprünglichen #38-Feature-Branch

Die ursprüngliche #38-Tree-Ansicht wurde dateiweise mit #52 verglichen:
- Der Integrationsbranch enthält die Auth-Python-Dateien einschließlich `auth_state.py`, `enroll.py`, `library_scope.py`, `oidc_exchange.py`, `users.py`, `server.py`, `migrations.py` und der jeweiligen Tests.
- Zwei beim ersten Integrationscommit fehlende Tests aus #36/#38 (`test_http_auth_gate.py`, `test_optional_auth.py`) wurden im folgenden Korrekturcommit ergänzt.
- `db.py` weicht **absichtlich** vom älteren #38-Stand ab, um die bereits auf `main` gemergte Inhaltsregel-Korrektur aus #26 zu erhalten.
- `web/index.html`, `web/style.css` und `tests/test_search_index.py` behalten ihre neueren `main`-Fassungen (#26/#27); älterer PR-Code darf sie nicht zurücksetzen.
- Die bisherigen Root-Dokumentationsdateien (`README.md`, `ROADMAP.md`, `TASKS.md`, `aktuellerStand.md`) wurden **nicht** mit alten Branch-Versionen überschrieben. Die historische und technische Integrationsbilanz steht in diesem neuen Dokument. Eine redaktionelle Zusammenführung der Roadmap-/Statusangaben bleibt eine eigene Review-Aufgabe.

**Grenze dieses Audits:** Ein Dateivergleich, positive synthetische CI-Tests und GitHub-Mergeability sind keine vollständige Sicherheitsfreigabe für echten OIDC-/Proxy-Betrieb.

## Konservative Reihenfolge für die verantwortliche Person

1. **Nichts weiter aus dem gestapelten PR-Stack mergen.** Insbesondere #39–#50 nicht in alte Feature-Bases mergen.
2. **Vor einem echten lokalen Update Chatidy stoppen.** Eine vollständige lokale Kopie der bestehenden SQLite-Datei und der Importjob-Daten an einen Ort außerhalb des Repositories erstellen; bei benutzerdefiniertem `CHATIDY_DB` dessen tatsächlichen Daten- und Job-Pfad verwenden. Keine Tokens, Geheimnisse oder persönlichen Exporte in Issues/PRs hochladen.
3. Prüfen, dass #52 als Ziel `main` ausweist, der Diff nur die vorgesehenen Auth-Dateien und Tests ergänzt und die **aktuelle** CI für den letzten Head-Commit komplett grün ist. Vergangene rote CI-Runs betreffen den bereits korrigierten Ausgangscommit.
4. #52 zunächst als Draft überprüfen und erst nach ausdrücklicher Zustimmung gegen `main` mergen. **Kein Deploy.**
5. Lokal `git switch main`, `git pull --ff-only origin main` und `python -m chatidy` im **normalen lokalen Modus**. `CHATIDY_AUTH_REQUIRED` nicht setzen und keinen echten Benutzer einschreiben.
6. Landing `/`, Bibliothek `/app`, bestehende Chats, Suche, Tags, Ordner, Anbieter-Filter, Importhilfe und Jobansicht prüfen; Import mit echten Daten ist für diesen Smoke-Test nicht erforderlich.
7. Erst nach erfolgreichem Smoke-Test den **nächsten eigenständigen Integrations-PR für #39–#50 gegen `main`** vorbereiten, auf gleichem Sicherheitsniveau testen und Review-/Merge-Reihenfolge dokumentieren.

## Betriebs- und Freigabegrenzen

- Keine automatische Benutzereinschreibung, Eigentümerzuordnung oder Bestandsmigration.
- `CHATIDY_AUTH_REQUIRED` bleibt opt-in; normaler localhost-Modus muss erhalten bleiben.
- Kein öffentlicher Reverse Proxy / keine Live-Authentik-Freigabe allein aufgrund dieses Integrations-PRs.
- Echtes Authentik, HTTPS, Cookie-/Host-/Origin- und Datei-/ACL-Grenzen (insbesondere Windows), Backup-Restore und ausdrücklich freigegebene Bestandsmigration bleiben gesonderte Freigabeschritte.
