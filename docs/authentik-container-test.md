# Kontrollierter OIDC-/Container-Test

Stand: 2026-11-21. Vorbereitung, **keine öffentliche Betriebsfreigabe**.
Dieses App-Runbook verändert weder authentik noch DNS, Caddy oder einen VPS.
Verantwortlich für den späteren Integrationstest ist der Betreiber.

## Bestandsaufnahme und tatsächliche Lücken

Ausgangsstand: Chatidy main `d84dc45baeb64dcfdb7ba9005b50f7eb7a8c3a32`.
Architektur gelesen auf Centrality main `eb7e5faf34f3aaf66109cdbafab2e49418e8e0f9`;
keine privaten Architekturunterlagen werden hier übernommen.

| Bereich | Implementiert / synthetisch geprüft | Weiterhin nicht nachgewiesen |
| --- | --- | --- |
| OIDC | Code + PKCE-S256, State/Nonce mit Browserbindung, einmaliger Verbrauch; RS256/JWKS, iss/aud/exp/iat/nonce, azp bei mehreren Audiences; feste HTTPS-Endpunkte, keine Redirects bei Token-/JWKS-Abruf | echter Provider, dessen Discovery-Daten, Key-Rotation und externe Proxy-Positivliste |
| Konten | explizite Einschreibung über issuer + sub; aktive Konten, keine automatische Registrierung oder Bestandszuordnung | Freischaltung/Identitätsnachweis des realen Eigentümers; native Windows-Kontorechte |
| Sessions | gehashte serverseitige Sessions, Secure/HttpOnly/SameSite-Lax-Hostcookies, 12 Stunden, Widerruf und Kontosperre; lokaler Logout | globale IdP-Abmeldung mit echtem Provider; kein Backchannel-/Frontchannel-Logout implementiert |
| Daten | separate Konto-SQLite-Dateien/Jobs, ContextVar pro Anfrage/Worker, Schema 8; transaktionale Migrationen und explizite Offline-Eigentümerkopie | vollständiger Betreiber-Backup-/Restore-Lauf und reale Bestandsmigration |
| HTTP | Host-/Origin-/POST-CSRF-Prüfung, Session vor privaten APIs/Assets; exakte unmittelbare Proxy-Vertrauensgrenze | realer Caddy-Headervertrag, externes HTTPS und Ressourcen-/Lastgrenzen |
| Container | digestgepinntes Python, vorhandene exakt gepinnte Auth-Pakete, Nicht-Root, schreibgeschütztes Root-FS, Datenvolume, Liveness | kein Produktionsdeploy, keine Image-Sicherheitsfreigabe oder ARM-Laufprüfung |

**Priorität vor dem Integrationstest:** (1) verifizierte Providerwerte und lokale
Testkonfiguration, (2) privater Proxy-/Netz-/Volume-Vertrag, (3) synthetischer
Containerlauf, (4) echte Login-/Logout-/Zwei-Konten-Abnahme, (5) Backup/Restore
und ausdrückliche Freigabe. Schritte 1/2 mit echten Werten und 4/5 sind Betreiberarbeit.

## Konfiguration

Die Werte kommen aus der nicht versionierten Betreiberkonfiguration; keine
festen authentik-Pfade im Python-Code. `.env.example` enthält nur Platzhalter.
Compose liest `.env`/`--env-file`; ein direkter Python-Start lädt **keine** `.env`.

| Variable | Vertrag |
| --- | --- |
| `CHATIDY_AUTH_REQUIRED` | `0` lokal (Default), `1` für OIDC; andere Werte verhindern den Start |
| `CHATIDY_HOST` | `127.0.0.1` Default; `0.0.0.0` nur mit Auth und expliziter Proxy-Vertrauensliste |
| `CHATIDY_PORT` | 1–65535, Default 8877; Compose intern fest 8877, ohne Host-Portmapping |
| `CHATIDY_DB` | Registry; Compose `/data/registry.sqlite3`, nicht die Datenbank eines beliebigen Kontos |
| `CHATIDY_PUBLIC_ORIGIN` | genaue HTTPS-Origin ohne Credentials, Query, Fragment oder Unterpfad; spätere Ziel-Origin `https://chatidy.htbui.de` |
| `CHATIDY_TRUSTED_PROXIES` | kommaseparierte IPs/CIDRs des **unmittelbaren** Proxys; bevorzugt einzelne feste IP, kein `/0`; keine Client-IP aus XFF |
| `CHATIDY_OIDC_ISSUER` | exakter `issuer` aus verifizierten Discovery-Metadaten, einschließlich abschließendem Slash falls vorhanden |
| `CHATIDY_OIDC_AUTHORIZE` | `authorization_endpoint` aus denselben Metadaten |
| `CHATIDY_OIDC_TOKEN` | `token_endpoint` |
| `CHATIDY_OIDC_JWKS` | `jwks_uri` |
| `CHATIDY_OIDC_CLIENT_ID` | eigener Confidential Client dieser App |
| `CHATIDY_OIDC_CLIENT_SECRET` | optional für direkten Python-Start; ausschließlich serverseitig injizieren |
| `CHATIDY_OIDC_CLIENT_SECRET_FILE` | Alternative zur Secret-Variable, UTF-8-Datei bis 8192 Bytes; finale CR/LF werden entfernt; beide Quellen gleichzeitig sind ein Fehler |
| `CHATIDY_OIDC_END_SESSION` | optionaler HTTPS-`end_session_endpoint`; Compose verlangt ihn zur Vorbereitung der Logout-Abnahme |

Autorisierungs-, Token-, JWKS- und Logout-Endpunkte müssen dieselbe konfigurierte
IdP-Authority verwenden (auch Port); dies bleibt eine bewusste bestehende
Vertrauensgrenze. Provider mit verteilten Endpunkten sind nicht abgenommen.
Discovery erfolgt **nicht automatisch**: Betreiber verifiziert die HTTPS-Metadaten
(zukünftiger Provider `https://auth.htbui.de`) und überträgt die Standardfelder.
Scopes: `openid profile email`; `client_secret_basic` plus PKCE-S256, RS256.
Rollen/Freischaltung kommen aus der lokalen Einschreibung, **nicht** aus einem
ungeprüften Gruppen-Claim. Kein automatisches Just-in-Time-Enrolment.

Callback exakt `${CHATIDY_PUBLIC_ORIGIN}/auth/callback`, Logout-Rückkehr exakt
`${CHATIDY_PUBLIC_ORIGIN}/`, ohne Wildcards. RP-Logout sendet `client_id` und die
feste `post_logout_redirect_uri`, **kein** `id_token_hint`, weil Chatidy keine
Provider-Tokens aufbewahrt. Unterstützt der IdP das nicht oder verlangt eine
Bestätigung, muss der Betreiber das klären. Ohne Endpunkt erfolgt nur lokale
Abmeldung. Der lokale Sessionwiderruf erfolgt auch bei fehlender IdP-Konfiguration.
Andere Chatidy-Sitzungen werden durch diesen Logout nicht automatisch widerrufen.
Die Weboberfläche fordert den lokalen POST mit `Accept: application/json` an;
die Antwort löscht Cookies und liefert das feste Navigationsziel. Erst danach
navigiert der Browser zum IdP. Ein Fetch folgt keinem Cross-Origin-Logoutredirect.
Bisherige POST-Clients erhalten weiterhin 302.

## Proxy-Vertrag

Bei gesetzter Vertrauensliste müssen **alle App-Anfragen** vom dort eingetragenen
unmittelbaren TCP-Peer kommen und folgende Header genau einmal enthalten:

- `Host`: unveränderte Authority der öffentlichen Origin.
- `X-Forwarded-Proto: https`.
- `X-Forwarded-Host`: exakt dieselbe öffentliche Authority.

Proxy muss diese beiden Forwarding-Header überschreiben, nicht Clientwerte
anhängen. `X-Forwarded-For` ist optional und wird für Berechtigungen ignoriert.
Doppelte Host-/Origin-/Forwarding-Header, Proto-/Host-Ketten, `Forwarded` und
andere `X-Forwarded-*` werden abgelehnt. Ohne Vertrauensliste werden Forwarding-
Header generell abgelehnt. Ein passender Host oder ein gefälschtes XFF allein
gewährt keinen Zugang. POST verlangt zusätzlich die exakte HTTPS-Origin.

Nur ein explizites, internes App↔Proxy-Netz verwenden; kein pauschal vertrautes
Docker-Defaultnetz. Das App-Egress-Netz dient ausschließlich den nötigen OIDC-
Abrufen; Compose implementiert **keine** domainbasierte Egress-Firewall. Diese
ist bei Bedarf Betreiberaufgabe. In diesem Repo gibt es keinen Caddy-Deploy.

`GET /healthz` antwortet nur bei Loopback-Peer, lokalem Host und ohne Forwarding
mit `{"status":"ok"}`. Er ist nicht für öffentliche Proxy-Routen gedacht und
zeigt weder Konfiguration noch Konten. Liveness beweist weder Datenintegrität
noch IdP-Erreichbarkeit; Registry wird beim Auth-Serverstart geöffnet/migriert.

## Reproduzierbarer lokaler Test ohne echte Zugangsdaten

Voraussetzung: Linux-Docker/Compose, Python 3.10+ für das Testskript.
Keine Produktionsvolumes und keine Host-Portbindungen. Vor späteren neuen
Host-Portbindungen erst freie Ports und Netzgrenzen read-only prüfen.

```bash
docker build -t chatidy:auth-integration-v1 .
python tests/container_smoke.py
```

Der Test erzeugt zufällig benannte **synthetische** Volumes/Netze, startet nur
die App, prüft Auth/SQLite/FTS5/Zwei-Konten-/Jobisolation und Neustartpersistenz
und entfernt ausschließlich seine eigenen Testressourcen. Er verwendet keine
externen OIDC-Anmeldungen und ersetzt keinen echten TLS-/authentik-Test.
Zusätzlich testet unittest einen echten lokalen TLS-Proxy mit temporärem
synthetischem Zertifikat und aktiver Zertifikatsprüfung sowie den vollständigen
Code-Exchange/JWKS/Signatur/Session-Pfad mit transportseitigen Fixtures.

Basis: Python `3.13.11-slim-bookworm` mit unveränderlichem Index-Digest im
Dockerfile; Auth-Abhängigkeiten unverändert aus `requirements-auth.txt`.
Build-Kontext ist eine Allowlist für Quellcode, Webdateien und Anforderungen:
keine Exporte, Datenbanken, `.git`, `.env` oder Tests im Image. Digest und
Paketpins bei Updates bewusst prüfen und die gesamte CI erneut ausführen;
ein erfolgreicher Build ist kein Schwachstellenscan.

Cloud-/Unternehmensproxy mit eigener CA: optional ein **geprüftes** CA-Bundle
nur für den Build einhängen, ohne TLS-Prüfung abzuschalten:

```bash
docker build --secret id=build_ca,src=/etc/ssl/certs/ca-certificates.crt \
  -t chatidy:auth-integration-v1 .
```

Das Bundle bleibt ein temporärer BuildKit-Mount und wird nicht ins Image
übernommen. Der Laufzeit-Container verwendet den normalen öffentlichen CA-Store.

## Späterer privater Integrationstest durch den Betreiber

1. Gewünschten Commit/Image festhalten, synthetisches Testkonto verwenden.
   Noch keine Bestandsmigration und keine öffentliche Freigabe.
2. `.env.example` in einen privaten Ordner **außerhalb des Checkouts** kopieren.
   Dort nur benötigte Werte pflegen; Secret als separate private Datei sichern.
   Secret muss für Container-UID 10001 lesbar sein. Compose-Dateisecrets sind
   Read-only-Bindmounts; `uid/gid/mode` werden dabei nicht zuverlässig umgesetzt.
   Besitzer/Lesbarkeit kontrolliert einrichten, keine pauschale Rechteerweiterung.
3. Dediziertes internes Proxy-Netz, tatsächliche Proxy-IP, Egress und Namen lokal
   prüfen/festlegen. `CHATIDY_PROXY_NETWORK`, `CHATIDY_EGRESS_NETWORK`,
   `CHATIDY_DATA_VOLUME` sind explizite stabile Namen. Kein bestehendes Netz ersetzen.
4. `docker compose --env-file /privater/pfad/review.env config --quiet` ausführen.
   Keine ungeschwärzte Konfigurationsausgabe teilen. Es gibt kein gemeinsames
   `env_file` im Service und keine Weitergabe anderer Host-Secrets.
5. Nach Betreiberfreigabe privat starten:
   `docker compose --env-file /privater/pfad/review.env up -d --build`.
   Named Volume `/data`: Registry, `accounts/<interne-id>/chatidy.sqlite3`,
   Konto-Importjobs und Sidecars zusammen erhalten. Neue Volumes sind für UID
   10001 vorbereitet; fremde/bestehende Volumes nicht automatisch umberechtigen.
6. Identität `issuer` + `sub` aus administrativ verifizierter Quelle einschreiben:
   `docker compose --env-file /privater/pfad/review.env exec chatidy python -m chatidy.enroll --issuer '<exakter issuer>' --subject '<verifiziertes sub>' --role owner --confirm`.
   Das legt keine Bestandszuordnung an. Im Zweifel nicht anhand der E-Mail raten.
7. Abnahme unten ausführen. Danach privat stoppen mit `docker compose ... down`;
   **kein `down --volumes`** für Betreiber-/Nutzerdaten. Kein automatischer Restart
   des Services in dieser Testvorlage; Neustart nur kontrolliert ausführen.

Image läuft als UID/GID 10001, ohne Capabilities, ohne Docker-Socket, ohne
privilegierten Modus; Root-FS read-only, `/tmp` begrenzt, `/data` persistent.
Limits (512 MiB RAM, 1 CPU, 128 Prozesse) sind **Testwerte**, keine Abnahme großer
Exporte. Die bisherigen 200/350-MB-Importlimits und Einzelobjekt-RAM-Grenzen gelten.
Ollama wird im Container nicht automatisch erreichbar gemacht.

## Gemeinsame End-to-End-Abnahme / verbleibende Betreiberaktionen

- [ ] authentik Phase 3b: reale Discovery, RS256-Signaturkey, Confidential Client,
  PKCE-S256, Scopes, Callback und Logout-Rückkehr exakt eingerichtet; Application
  nur für freigegebene Alltagskonten. Keine offene Selbstregistrierung.
- [ ] Öffentliche IdP-Positivliste für Discovery/Autorisierung/Token/JWKS und
  Provider-Logout geprüft; Admin- und unbekannte Pfade extern negativ testen.
  Konkreter Logout-Flow ist Providerkonfiguration, kein fest kodierter App-Pfad.
- [ ] Tatsächliche Caddy-Peer-IP und Header belegen; direkte Containerzugriffe,
  falscher Host/Origin, gefälschte/multiple Forwarding-Header und fehlende Sitzung
  müssen scheitern. Browser-HTTPS mit gültigem Zertifikat verifizieren.
- [ ] Login → Callback → eigene Bibliothek → Suche/Import/Export; kein Token in
  URL nach Callback, Browser-Storage oder Logs; Cookies Secure/HttpOnly/Host-only.
- [ ] Falscher/abgelaufener State, fehlende Browserbindung, Replay, Nonce-/Issuer-/
  Audience-/Signaturfehler verhindern den Login. Providerausfall bleibt geschlossen.
- [ ] Zwei explizit eingeschriebene Testkonten: fremde Chats, Ordner, Tags,
  Suchansichten, Regeln, Exporte, Jobs und Jobaktionen nicht zugänglich.
  Nicht eingeschriebene/gesperrte Konten bleiben gesperrt.
- [ ] Sessionablauf und lokale Sperre/Widerruf; Logout beendet lokale Sitzung
  **und** nachweislich gewünschte Provider-Sitzung. Erneuter Login darf keine
  unerwartete automatische Wiederanmeldung ergeben. Andere Browser-Sitzungen prüfen.
- [ ] Containerneustart, private Verzeichnis-/Dateirechte auf Zielplattform,
  gleichzeitige Jobs, Uploadgrenzen, Speicherplatz, RAM/CPU und Betriebslogs prüfen.
- [ ] Gestopptes vollständiges `/data`-Volume inklusive Registry, Kontobibliotheken,
  Importdateien und SQLite-Sidecars sichern; zusätzlich Secret und Konfiguration
  verschlüsselt außerhalb des Hosts sichern. Isolierter Restore, Integrity/FK/FTS,
  Hashvergleich und unabhängige Entschlüsselung nachweisen. Restore enthält ggf.
  Sessions; vor Wiederfreigabe bewusst widerrufen/ablaufen lassen.
- [ ] Bestandsmigration **separat** planen: Server gestoppt, verifiziertes Backup,
  explizit bestätigtes Eigentümerkonto und vorhandene Importjobs administrativ
  geprüft. `python -m chatidy.migrate_owner --help` beschreibt den vorhandenen
  Offline-Kopierpfad. Weder Start noch Login führen diese Kopie automatisch aus.
- [ ] Rollback: altes geprüftes Image **und** passende Sicherung vor Migration
  bereitstellen. Nie ein älteres Programm auf eine neuere DB-Version zwingen.
- [ ] Monitoring, Dependency-/Image-Updates, Notfallwiderruf und Datenschutz vor
  Dritten klären. Erst danach ausdrückliche Betreiberfreigabe; Centrality-Abgleich
  ist eine spätere eigene Aufgabe, nicht in diesem Durchlauf erledigt.

## Architekturabgleich

ADR-007 nennt im vorgeschlagenen Schnittstellenabschnitt noch Just-in-Time-
Benutzeranlage. ADR-008 und der bestehende App-Code verlangen dagegen explizite
Freischaltung. Dieser Durchlauf erhält die sicherere bestehende Einschreibung;
der Widerspruch bleibt für den Eigentümer zur Dokumentationsklärung offen.
Gruppen-Claims und automatische Discovery sind kein implementierter
Freischaltungsmechanismus. Ein späterer Providerwechsel braucht bestätigte neue
Identitätszuordnung, keinen automatischen E-Mail-Abgleich.
