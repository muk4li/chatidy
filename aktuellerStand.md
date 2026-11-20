## AUTH-012 – Explizite Bestandskopie (Draft)

Offline-Admin-Befehl für überprüftes Eigentümerkonto; Backup und Kopie von
Chats/Organisation ohne Login-/Sitzungsinformationen. Kein Automatismus beim
Anmelden, alte Daten bleiben erhalten. Reale Migration/Restore ungeprüft.

---

## AUTH-011 – Browser-Login und OIDC-Callback (Draft)

Einmaliger browsergebundener State mit PKCE und verifiziertem ID-Token,
Sitzung für explizit freigeschaltete Konten, Secure-Cookies und Logout.
Synthetische HTTP-Tests; Authentik-Live-/Deployment- und Migrationsgates offen.

---

## AUTH-010 – OIDC-Code-Exchange (Draft-PR)

Synthetisch getesteter Token-/JWKS-Abruf ohne offene Redirects, nur
konfigurierte HTTPS-Endpunkte. Keine HTTP-Browseranmeldung. Kein Live-IdP-
Test oder öffentlicher Server; in CI optionale gepinnte Auth-Abhängigkeiten.

---

## AUTH-009 – Serverseitiges HTTP-Gate (Draft-PR)

Opt-in-Testmodus schützt `/app`, App-Assets und alle Daten-/Import-APIs
serverseitig vor Zugriff ohne aktive Sitzung. Bei gültiger Session wird
der pro Konto isolierte DB-/Importjob-Kontext aktiviert. Keine tatsächliche
OIDC-Anmeldung und kein Deployment; lokaler Standardmodus bleibt erhalten.

---

## AUTH-008 – OIDC-State und Sessions (Draft-PR)

Schema 8 speichert browsergebundene kurzlebige Login-Challenges und
widerrufbare Sitzungen mit SHA-256-Tokenhashes. Helper sind noch nicht
in HTTP oder authentik eingebunden, keine Konto-/Chat-Zuordnung. CI und
Sicherheitstests zum isolierten Baustein; Loopback-only weiterhin Pflicht.

---

## AUTH-004 – Explizite OIDC-Kontoeinschreibung (Draft-PR)

Lokales CLI für vom Administrator vorher verifizierte OIDC-Issuer/Subjekt-
Kennungen, mit ausdrücklichem `--confirm`. Keine HTTP-Registrierung, kein
Automatismus für Eigentümerkonto oder bestehenden Chatbestand. Funktionen
unabhängig von echter authentik-Installation synthetisch testbar.

---

## AUTH-003 – OIDC-Identitätszuordnung (gestapelter Draft-PR)

Schreibfreier `enrolled_user`-Lookup für bestehende aktive Benutzer über
exakte OIDC-Issuer-/Subjektkombination. Keine Registrierung, kein HTTP-Login,
keine Tokenprüfung, keine Freigabe von Chatdaten. Abhängig von Schema 7
(AUTH-002). CI/Tests siehe PR, echter Login noch nicht möglich.

---

## AUTH-002 – Schema 7 (Draft-PR)

Additive Tabelle `users` für späteren authentik-OIDC-Bezug (`iss`+`sub`),
Rolle/Status und Anzeigenamen. Keine automatische Benutzeranlage oder
Eigentümerzuordnung. Sämtliche bisherigen Daten/API-Pfade bleiben im lokalen
Einzelnutzermodus unverändert; **nicht** für öffentlichen Betrieb geeignet.
Synthetische Migrations-/Rollbacktests ergänzt; tatsächlicher CI-Status siehe PR.

---

# Aktueller Stand von Chatidy

**Nachprüfung GitHub 2026-11-14:** Der unten als offen beschriebene Fokus-PR ist inzwischen **PR #9, gemergt**; aktueller `main`-HEAD `8fe4da20f4ca`. GitHub-Actions-Workflow „Tests“ auf diesem Commit erfolgreich. Die damalige GraphQL-Fehlermeldung bleibt als historischer Verlauf stehen. Weiterhin offen: manueller Echttest REAL-001 und die bestehenden Backlog-/Remote-Grenzen.


**Stand:** 2026-11-14 · **Basis-Commit:** `8e19e783def2045bb08798478973918ba2ec6ea7` auf `main`
**Stand:** 2026-11-14 · **Basis-Commit:** `f648669` auf `main`

- **Läuft:** Lokaler Import mit Vorschau/Batch-Bestätigung, SQLite/FTS5, Ordner,
  Tags, Regeln, Review und JSON-Export. Dreigeteilte Oberfläche (PR #11) sowie einklappbare/verstellbare
  Seitenleisten (PR #12) und größere Navigationssymbole (PR #13) gemergt. Seit PR #12: Bereiche „Ordner & Gruppen“, „Intelligente Ordner“ und
  „Tags“ einklappbar; Navigation und Leseansicht per Ziehen/Pfeiltasten verstellbar
  (Doppelklick setzt zurück, Breiten nur im Browser gespeichert); Anzahl hinter
  Archiviert, Ohne Gruppe und Themencluster. `/api/stats` liefert zusätzlich
  `archived` und `unfiled` (additiv, bestehende Felder unverändert).
  Tests lokal: 113 entdeckt, 103 bestanden, 10 native Windows-Tests übersprungen;
  Chromium-Browsertest 3/3 erfolgreich. Nur synthetische Daten. Keine Änderungen
  an Import-, Job-Storage-, Migrations- oder Schemacode.
- **PROV-004 (2026-11-20):** Codex-Aufgaben aus `codex.json` werden mit dem ChatGPT-ZIP als eigene
  Chats importiert (`codex:<id>`); nicht erkannte Datei nur Warnung. Dabei behoben: Strukturerkennung in
  ZIPs ohne offizielle Namen verlangte `id` und übersah so Claude-Gespräche (`uuid`). Tests: 151
  (10 Windows-Skips), Browser-Smoke lokal bestanden. Hinweis: Der nächste Import des vollständigen
  ChatGPT-ZIPs bringt die Codex-Aufgaben als neue Chats mit.
- **META-001 (2026-11-20):** Segmente werden gegen ein erkanntes Wurzel-`export_manifest.json`
  abgeglichen; fehlende/zusätzliche Segmente brechen ab. Unbekannte Manifeste nur Warnung.
  Tests: 145 (10 Windows-Skips). Offen: Gegenprobe mit echtem ChatGPT-Export (sollte „vollständig“ zeigen).
- **SEARCH-001 (2026-11-20):** Platzhalter nicht mehr in der Volltextsuche; Schema 6 baut den Suchindex
  einmalig neu auf (nur abgeleiteter Index). Tests: 139 (10 Windows-Skips).
- **Nachrichtenzahlen (2026-11-20):** Liste, Kopfzeile, Verlauf und Statistik zählen nur lesbare
  Nachrichten (ohne Denk-/Werkzeugknoten). Nur Abfrage/Anzeige, keine Schemaänderung.
- **PROV-002b (2026-11-20):** Anbieter-Badge, Anbieter in der Kopfzeile, Filter „Anbieter“ in der
  Navigation (ab zwei Anbietern sichtbar), intelligente Ordner mit Anbieterfilter; Claude-Werkzeug-
  und Denkblöcke als einklappbare Kurzzeile (nur Namen/Zahlen, keine Inhalte/URLs). Tests: 135
  (10 Windows-Skips), Node-Logiktest, Browser-Smoke lokal bestanden. Offen: Prüfung mit echtem Export.
- **PROV-002a (2026-11-20):** Claude-Adapter: `conversations-000.zip`/`conversations.json` importierbar,
  IDs `claude:<uuid>`, Zweigauswahl über Elternverweise (neuestes Ende), Text aus Textblöcken und
  Anhangstext, Tool-/Thinking-Rohdaten in Metadaten; Manifest und andere Kategorie-ZIPs mit Hinweis
  abgelehnt. Tests: 134 (10 Windows-Skips) inkl. HTTP-Jobablauf, nur synthetische Fixtures nach realem Schlüsselbefund.
  Offen: 002b (UI), Import des echten Exports durch den Nutzer.
- **PROV-001 (2026-11-20):** Format-Adapter mit ausdrücklicher Erkennung (Mehrdeutigkeit = Abbruch;
  Claude-ähnliche `messages`-Varianten werden nicht mehr als Extractor gelesen), Schema 5 mit
  `conversations.provider` (Bestand `chatgpt`), API-Filter und Anbieterzählung. Dabei behoben:
  Vorschau gegen noch nicht migrierte Bibliothek hätte alle Chats als „unklare Identität“ gemeldet.
  Tests: 123 (10 Windows-Skips), Browser-Smoke lokal bestanden. Noch keine UI-Änderung.
- **CGPT-001 (2026-11-20):** ChatGPT-Denkprozesse erscheinen in der Leseansicht als eingeklappter
  Block statt „[Nicht-textueller Inhalt]“. Nur Anzeige (`web/reading.js`), keine Import-, Schema- oder
  Indexänderung. Tests: Node-Logiktest (über `tests/test_reading_view.py`, ohne Node übersprungen),
  Metadaten-/Reimport-Test, HTTP-Auslieferung; Playwright-Browsertest mit Chrome in der Cloud-Session
  bestanden (synthetisch). Sichtprüfung mit echtem Export durch den Nutzer: passt (2026-11-20).
- **Offen:** REAL-001 (manueller Echttest durch
  Nutzer). META-001, SCALE-001, UX-001 (Rest), KNOW-001, AUTO-001 (Gruppenvorschläge
  für viele Chats), DATA-002 bleiben Backlog. Neu geplant (nur Doku, kein Code):
  Mehrere Chat-Anbieter inkl. Claude-Export, ROADMAP Phase 6 / PROV-001 bis PROV-003.
  Claude- und ChatGPT-Exportstruktur am 2026-11-20 anhand echter Exporte (nur Schlüssel) geprüft;
  Claude-Zweige bestätigt. Neu im Backlog: CGPT-001, PROV-004.
  Nur Loopback; kein Remote-Login (Centrality F-02). Kein manueller Windows-11-Test
  der neuen Oberfläche.
- **Nächster Schritt:** Oberfläche lokal ausprobieren und Rückmeldung geben; danach
  REAL-001 nach der [Echttest-Checkliste](docs/manueller-echttest.md).
