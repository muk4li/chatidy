# Chatidy – Service-Vertrag (Entwicklung / nicht freigegeben)

Stand: 2026-11-21. Architekturgrundlage: Centrality ADR-001, ADR-007,
ADR-008 und CE-103. Private Vertragsunterlagen werden nicht übernommen.

| Bereich | Aktuell / vorgesehen |
| --- | --- |
| Anwendung | Python Standardbibliothek + SQLite/FTS5, optionale exakt gepinnte OIDC-Abhängigkeiten |
| HTTP-Listener | lokal 127.0.0.1:8877; explizites Container-0.0.0.0 nur mit Auth und vertrautem Proxy; keine Host-Portfreigabe in Compose |
| Öffentliche Routen | `/` Landing, `/landing.css`, `/login`, `/auth/callback` |
| Geschützte Routen | `/app`, App-Assets und **alle** `/api/*` |
| Identity | authentik OIDC (Authorization Code + PKCE, RS256 ID-Token); nur explizit angelegte aktive Konten |
| Sessions | gehashte Token in zentraler SQLite-Registry; revokabel, HttpOnly/Secure/SameSite |
| Persistenz | lokale Registry mit eingeschriebenen Konten; separate private SQLite-Bibliotheken und Importjobs pro Konto |
| Bestand | explizit bestätigte Offline-Kopie mit Backup; keine erste-Login-Übernahme |
| Externe Verbindungen | kein Chatinhalts-Cloud-Transfer; OIDC-Token/JWKS nur zur fest konfigurierten Identity-Instanz; optionaler RP-Logout; Ollama lokal optional |
| Freigabe | **NEIN** – L2-Code über #52/#53 sowie Container-Vorbereitung über #57 in main integriert und synthetisch getestet ([CI 44958269781](https://github.com/muk4li/chatidy/actions/runs/44958269781)); echter Authentik-/HTTPS-/ACL-/Zwei-Konten-Abnahmelauf fehlt |

## Zwingende Gates vor öffentlichem Betrieb

1. L2-Integrationen #52 und #53 sowie DEPLOY-001 über #57 sind in main gemergt. Verbleibende
   alte Feature-PRs #39–#50 sind durch #53 ersetzt (nicht nochmals mergen).
   **Centrality-Synchronisierung bleibt als eigene spätere Aufgabe offen**;
   diese Änderung darf nicht als Centrality-Freigabe gelten.
2. Authentik eingerichtet, HTTPS-Discovery/Issuer, Client, Callback und
   feste Token-/JWKS-Endpunkte gegen tatsächlichen Provider validiert.
3. HTTPS-Reverse-Proxy und Headervertrauen (Host, Origin, Forwarding,
   X-Forwarded-*) mit negativen Tests. Keine Zugriffe ohne Sitzung, auch
   auf Importjobs, Upload, Suche, Export und Schreiboperationen.
4. Separate Kontobibliotheken und Importjobs nativ unter Windows und
   Linux auf ACL, Symlink-/Junction-Schutz, Rechte, Wiederaufnahme,
   parallele Anfragen und Lösch-/Sperrstatus prüfen.
5. Backup **und Restore** aller Registry-, Konto-, Upload-/Job-Dateien
   vollständig testen. Bestandsmigration nur bei gestopptem Server,
   nach Backup und expliziter Eigentümerzuordnung.
6. TLS, Logout, Sessionablauf/-widerruf, CSRF/Origin, Code-State-Replay,
   Rollen-Sperre, unbekanntes Konto und Zwei-Konten-Tests nachweisen.
7. Deployment-/Rollback-/Monitoring-Runbook und Freigabe durch Eigentümer.
   Vor erstem eingeladenen Benutzer zusätzlich Datenschutz/Impressum und
   Sperren/Löschen des Kontos klären.

**Bis dahin: lokal Loopback bzw. isolierter Container-Integrationstest, keine öffentliche Netzfreigabe.**

## OIDC Confidential Client (AUTH-023)

Zusätzlich zum bisherigen HTTPS-Issuer, Autorisierungs-/Token-/JWKS-Endpoint,
Client-ID und Redirect-URI muss `CHATIDY_OIDC_CLIENT_SECRET` oder alternativ
`CHATIDY_OIDC_CLIENT_SECRET_FILE` ausschließlich serverseitig verfügbar sein. Der Token-Exchange verwendet
`client_secret_basic` **und** PKCE-S256; keine browserseitigen Client-Secrets.
Der tatsächliche authentik-Provider muss mit entsprechendem Client-
Authentication-Method konfiguriert und getestet werden. Vor dieser Prüfung
bleibt öffentliche Betriebsfreigabe gesperrt.

## Mandantenfähige App-Routen (UX F-009)

`/app`, `/app/import`, `/app/inbox`, `/app/archive`, `/app/unfiled`,
`/app/topics`, `/app/folders/<interne-ordner-id>`,
`/app/smart/<interne-id>` und `/app/chats/<chat-id>` liefern
dieselbe App-Oberfläche. Der **serverseitig geprüfte Sitzungskontext**
bestimmt die jeweilige Kontobibliothek. Keine Benutzer-IDs oder Tokens
werden für Berechtigungen aus URL-Parametern akzeptiert.
Unauthentifizierte Direktaufrufe bleiben im Authentik-Modus geschützt;
fremde oder unbekannte Datensätze dürfen keine Daten preisgeben.

**Centrality-Nachpflege: OFFEN, nicht durchgeführt.**

## Container-/Proxy-Vertrag (DEPLOY-001)

Owner: Repository-Inhaber; implementierter Vorbereitungsstand, kein Live-Betrieb.
[Konfiguration, Ist-Analyse und Abnahme](docs/authentik-container-test.md) sind die
technische Quelle. Artefakte: [Dockerfile](Dockerfile), [compose.yaml](compose.yaml),
gepinntes Basisimage und unveränderte Auth-Pins in [requirements-auth.txt](requirements-auth.txt).
Linux/amd64-Build und synthetischer Compose-Smoke lokal geprüft; andere
Architekturen und echte authentik-/Caddy-Integration nicht abgenommen.

- Compose veröffentlicht keine Host-Ports. UID/GID 10001, Root-FS read-only,
  keine Capabilities/privilegierten Container/Docker-Sockets; ein internes,
  dediziertes Proxy-Netz und ein App-Egress-Netz mit stabilen Namen.
- `CHATIDY_HOST=0.0.0.0` erfordert `CHATIDY_AUTH_REQUIRED=1`, gültige HTTPS-Origin,
  vollständige OIDC-Konfiguration und `CHATIDY_TRUSTED_PROXIES`. Ohne diese Werte
  kein Serverstart. Host/Origin bleiben unabhängig von Forwarding validiert.
  Peer-IP, genaues HTTPS-Proto/Host, doppelte/unerwartete Header: siehe Runbook.
- `GET /healthz`: nur containerlokales Loopback ohne Proxyheader; minimale
  Liveness ohne Sitzung, DB-Abfragen oder Upstream-Zugriff. Nicht öffentlich routen.
  Auth-Start öffnet/migriert die Registry vor dem Listener. Fehler beenden den
  CLI-Start mit generischer Meldung/Exit 1, ohne Secrets oder private Pfade.
- `/data` als Named Volume enthält Registry, Kontobibliotheken, Importjobs und
  SQLite-Sidecars. Schema bleibt 8. Keine automatische Bestandszuordnung.
  Vollständiges gestopptes Volume plus externe Secrets/Konfiguration sichern und
  isoliert wiederherstellen; bestehende Migrations-/Rollback-Gates gelten weiter.
- `POST /logout` widerruft die Session; mit `Accept: application/json` antwortet
  er mit einem festen Navigationsziel und ablaufenden Cookies, sonst per 302.
  Die Weboberfläche navigiert danach als Browser-Seite zum Provider (kein
  Cross-Origin-Fetch). Optionaler RP-Logout über `CHATIDY_OIDC_END_SESSION` mit fester Rückkehr-Origin,
  ohne gespeicherten ID-Token. Lokaler Widerruf immer; tatsächliche globale
  Provider-Abmeldung ohne `id_token_hint` muss mit authentik geprüft werden.
- Keine automatische Discovery, Gruppenrollen, Backchannel-Abmeldung oder
  Kontoanlage; explizite Einschreibung bleibt maßgeblich. Die ältere vorgeschlagene
  JIT-Regel in ADR-007 wird nicht still umgesetzt oder zur Freigabe erklärt.

Nachweise: Python-Suite inklusive lokalem TLS-Proxy und synthetischem signierten
Callback sowie [Container-Smoke](tests/container_smoke.py); tatsächliche Ergebnisse
stehen in [aktuellerStand.md](aktuellerStand.md). Eine CI-Definition ist kein
Laufbeleg. Echte Provider-/TLS-/Backup-/Betreiber-Gates bleiben offen.
