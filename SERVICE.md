# Chatidy – Service-Vertrag (Entwicklung / nicht freigegeben)

Stand: 2026-11-20. Architekturgrundlage: Centrality ADR-001, ADR-007,
ADR-008 und CE-103. Private Vertragsunterlagen werden nicht übernommen.

| Bereich | Aktuell / vorgesehen |
| --- | --- |
| Anwendung | Python Standardbibliothek + SQLite/FTS5, optionale exakt gepinnte OIDC-Abhängigkeiten |
| Lokaler HTTP-Listener | 127.0.0.1:8877 (änderbarer Port), niemals globaler Bind |
| Öffentliche Routen | `/` Landing, `/landing.css`, `/login`, `/auth/callback` |
| Geschützte Routen | `/app`, App-Assets und **alle** `/api/*` |
| Identity | authentik OIDC (Authorization Code + PKCE, RS256 ID-Token); nur explizit angelegte aktive Konten |
| Sessions | gehashte Token in zentraler SQLite-Registry; revokabel, HttpOnly/Secure/SameSite |
| Persistenz | lokale Registry mit eingeschriebenen Konten; separate private SQLite-Bibliotheken und Importjobs pro Konto |
| Bestand | explizit bestätigte Offline-Kopie mit Backup; keine erste-Login-Übernahme |
| Externe Verbindungen | kein Chatinhalts-Cloud-Transfer; OIDC-Token/JWKS nur zur fest konfigurierten Identity-Instanz; Ollama lokal optional |
| Freigabe | **NEIN** – L2-Code über #52/#53 integriert und synthetisch getestet; echter Authentik-/HTTPS-/ACL-/Zwei-Konten-Abnahmelauf fehlt |

## Zwingende Gates vor öffentlichem Betrieb

1. L2-Integrationen #52 und #53 sind in main gemergt. Verbleibende
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

**Bis dahin: local-first nur Loopback, keine öffentliche Netzfreigabe.**

## OIDC Confidential Client (AUTH-023)

Zusätzlich zum bisherigen HTTPS-Issuer, Autorisierungs-/Token-/JWKS-Endpoint,
Client-ID und Redirect-URI muss `CHATIDY_OIDC_CLIENT_SECRET` ausschließlich
serverseitig verfügbar sein. Der Token-Exchange verwendet
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
