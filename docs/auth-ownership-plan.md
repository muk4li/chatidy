# L2a – Entwurf für Benutzeridentität und Datenzuordnung

Status: **Entwurf, keine Implementierung / keine Auth-Freigabe** (2026-11-20).
Quelle der Architektur: Centrality ADR-007 und ADR-008. RepoPilot bleibt Pilot;
dessen L1 ist nach aktuellem Stand noch kein implementierter, freigegebener Vertrag.

## Bestehender Chatidy-Stand

- SQLite-Schema 6, Single-User. `conversations.provider` ist die **Quelle**
  (ChatGPT/Claude), kein Besitzer.
- `conversations.id` ist aktuell global eindeutig; Nachrichten-Identität
  `(conversation_id,id)`; Organisation referenziert globale Gesprächs- und
  Ordnerkennungen.
- `folders`, `tags`, `rules`, `smart_folders`, `suggestions`,
  `memberships`, `chat_tags`, FTS-Index, Importjobs und Einstellungen
  haben heute keinen Benutzerkontext.
- Der lokale Webserver und `/api/*` haben keine Anmeldung. Host-/Origin-Prüfung
  und Loopback sind **kein** Remote-Authentisierungsschutz.

## Angestrebte Invarianten (noch nicht umgesetzt)

1. `users` enthält eine interne, stabile ID und die eindeutig kombinierte
   OIDC-Identität `(oidc_issuer, oidc_sub)`. Anzeige-E-Mail/-Name sind keine
   Berechtigungsmerkmale; keine App-Passwörter.
2. Jeder Datenzugriff wird serverseitig an eine **verifizierte Sitzung**
   und deren interne Benutzer-ID gebunden. Kein vom Client übermitteltes
   `user_id` als Berechtigungsnachweis.
3. Jede persönliche Ressource (Gespräche, Nachrichten, Tags, Ordner,
   Regeln, gespeicherte Suchen, Importjobs und Vorschläge) ist genau einem
   Benutzer zugeordnet. Kein Cross-User-Suchen, Importieren, Exportieren,
   Bearbeiten oder Job-Fortsetzen/-Löschen. Fremde IDs werden abgewiesen.
4. Ursprüngliche Anbieter-/Konversations-IDs dürfen bei mehreren Konten
   vorkommen. Identität/Reimport-Schutz müssen im jeweiligen Benutzerkontext
   prüfen, ohne bestehende Original-IDs und Inhalte zu verändern.
5. Öffentlich sind nur Landingpage und Auth-Einstieg; `/app` und
   sämtliche sensiblen `/api/*`-Routen sind vor Exposition serverseitig
   gesperrt. Für lokale Entwicklung bleibt Loopback ohne Login vorerst bestehen.
6. Ein vorhandener Single-User-Bestand wird **niemals** beim ersten Login
   automatisch übernommen. Zuordnung ausschließlich über gesonderten,
   ausdrücklich bestätigten, transaktionalen Migrationsschritt mit geprüftem
   Rollback/Backup und erhaltenen Zuordnungen.
7. Importjob-Staging und `CHATIDY_DB` bleiben lokal und geschützt;
   keine willkürliche globale Vorbelegung des Besitzers. Keine öffentlichen
   Daten-Schnittstellen vor Auth-/Isolationstests.

## Vorschlag für kleine Folgepakete (vor Umsetzung gegen RepoPilot abgleichen)

- **L2b – technische Identitätsbasis:** abgestimmte `users`-Tabelle mit
  `UNIQUE(oidc_issuer,oidc_sub)`; gesonderte, getestete additive Migration
  ohne automatischen Eigentümer und ohne Änderung vorhandener Fachschlüssel.
  Vorher klären, wie bestehende unzugeordnete Bibliotheken dargestellt werden.
- **L2c – Benutzerbezogene Fachidentitäten:** globale IDs in den heutigen
  Relationen untersuchen; pro Benutzer eindeutige Konversations-/Ordner-/Tag-
  Schlüssel oder gesonderte interne Schlüssel wählen. Besonders FTS5,
  SQLite-FKs, Klassifizierung, Import-Transaktionen und Job-Wiederaufnahme
  mit synthetischen Zwei-Benutzer-Fällen prüfen. Keine stillen FK-Umbauten.
- **L2d – Zugriffsschutz/OIDC:** Authentik Authorization Code + PKCE, Session,
  Logout, serverseitige Kontrolle aller API-/Job-Routen; erst nach akzeptiertem
  RepoPilot-Pilot und konkreter OIDC-Schnittstelle.
- **L2e – Bestandsmigration/Freigabe:** explizite Zuweisung an Eigentümerkonto,
  Regression/Negativtests, Backup/Restore und Exposition-Gates aus Centrality.

## Offene Architekturfragen (Entscheidung vor Schemaänderung)

- Werden benutzerbezogene Schlüssel über zusammengesetzte PKs oder zusätzliche
  interne IDs realisiert? Das beeinflusst Nachrichten, Mitgliedschaften, FTS5,
  Jobs und alle API-Antworten.
- Wie wird eine vorhandene Bibliothek ohne Besitzer bis zur ausdrücklichen
  Migration technisch lesbar gehalten, ohne sie einem angemeldeten Fremdkonto
  zugänglich zu machen?
- Wie werden Importjob-Verzeichnisse und Staging-Daten benutzerbezogen
  isoliert und migriert, ohne die bestehenden NTFS-/POSIX-Sicherheitsgrenzen
  zu schwächen?
- Welche Schnittstelle liefert der RepoPilot-Pilot tatsächlich für den Login?
  Chatidy übernimmt Integrationsregeln, aber kein gemeinsames Framework.

## Abnahmekriterien für diesen Entwurf

- Kein Code, keine Datenbankmigration, keine neuen Abhängigkeiten, kein Deploy.
- Abhängigkeiten/Offenpunkte nachvollziehbar; DESIGN ist nicht DONE.
- Nach RepoPilot-Pilot und ausdrücklichem Review in konkrete kleine
  Implementierungspakete zerlegen.

## Implementierungsvariante im Review – je Konto eigene SQLite-Datei

**Noch keine akzeptierte Architekturentscheidung.** Ein getrennter Draft-PR
[AUTH-005 / #32](https://github.com/muk4li/chatidy/pull/32) erprobt
eine alternative Isolation: Die globale lokale Datenbank verwaltet in
Schema 7 nur ausdrücklich eingeschriebene OIDC-Konten; jedes Konto
hat zusätzlich eine eigene, vom Server anhand der vertrauenswürdigen
internen ID bestimmte SQLite-Bibliothek und Importjob-Wurzel.

Vorteile: Bestehende Konversations-IDs und SQLite-Fremdschlüssel bleiben
innerhalb der Bibliotheken unverändert; zwei Konten können dieselbe
Original-Chat-ID haben. Die historische lokale Bibliothek wird nicht
automatisch einem Konto zugeordnet.

Zu prüfen vor Freigabe: sichere Windows-/POSIX-Dateizugriffe und Backups
aller Kontobibliotheken, Importjob-Kontext in Worker-Threads, die
Entscheidung zwischen physischer Datenbanktrennung und
`user_id`/zusammengesetzten Schlüsseln in einer Datenbank sowie die
vollständige serverseitige API-Berechtigung. **Die physische Trennung
allein ist keine Authentifizierung.** Ohne echte OIDC-Session und
geschützte HTTP-Routen bleibt Chatidy nur lokal verwendbar.
