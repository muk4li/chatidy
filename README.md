# Chatidy ✳

Chatidy organisiert lokale ChatGPT- und Claude-Exporte: Python-Standardbibliothek,
SQLite/FTS5 und eine Weboberfläche unter **http://127.0.0.1:8877**.
Es verändert keine Unterhaltungen auf chatgpt.com und benötigt keinen ChatGPT-Login.

## Startseite und lokale Anwendung

`/` zeigt eine öffentliche Produkt-Landingpage und `/app` die bestehende lokale Bibliothek.
**L2 technisch integriert, öffentliche Freigabe weiterhin gesperrt:** OIDC-Login,
serverseitige Sitzungen, geschützte APIs, getrennte Bibliotheken und Jobdaten
sind implementiert und synthetisch getestet (Integration #52/#53). Im normalen
lokalen Modus bleibt Chatidy ohne Login bedienbar. Ein echter authentik-,
HTTPS-/Proxy-, Windows-ACL- und Zwei-Konten-Test sowie Backup-/Restore-
und Betreiberfreigabe stehen noch aus; daher ausschließlich Loopback-Betrieb.
Der Link „Bibliothek öffnen“ auf der Landingpage ist für den lokalen Modus gedacht.

## Schnellstart

Python 3.10+ mit SQLite/FTS5, keine zusätzlichen Python-Pakete.

**Linux:**

```bash
git clone https://github.com/muk4li/chatidy.git
cd chatidy
python -m chatidy
```

**Windows 11:** Python 3.13 von python.org installieren, Repository klonen oder
entpacken und PowerShell im Projektordner öffnen. Kein WSL oder Docker nötig.

```powershell
$env:CHATIDY_DB = Join-Path $env:LOCALAPPDATA "Chatidy\chatidy.sqlite3"
py -3.13 -m chatidy
```

Browser unter `http://127.0.0.1:8877/app` öffnen → links **Import** (öffnet sich bei leerer Bibliothek automatisch) →
**Datei auswählen** → vollständiges Export-ZIP oder
`conversations.json` auswählen → **Import-Vorschau** prüfen →
**Diesen Batch importieren** → auf **Erfolgreich** warten.
Für den ersten echten Export: [Windows-Checkliste](docs/manueller-echttest.md).
[Ausführlicher Windows-Start und Fehlerhilfe](docs/import-details.md#windows-11-nativer-schnellstart).

Ohne `CHATIDY_DB` liegt die Datenbank unter `data/chatidy.sqlite3` im
Projektordner, unabhängig vom Arbeitsverzeichnis. `CHATIDY_DB` hat Vorrang;
relative eigene Pfade bleiben relativ zum Arbeitsverzeichnis. Beim üblichen
Start im Repo-Root ändert sich kein Speicherort, es ist keine Migration nötig.
Für vorhandene Daten außerhalb des Projektordners deren bisherigen Pfad explizit
setzen; Chatidy verschiebt oder sucht diese Dateien nicht automatisch.

Die Importseite erläutert die unterstützten Formate unter **„Welchen Export kann ich auswählen?“**.
Für ChatGPT das gesamte Export-ZIP auswählen; bei Claude das ZIP der Kategorie
`conversations` (z. B. `conversations-000.zip`) oder `conversations.json`.
Konto-, Memory- und Artifact-ZIPs sind keine Gesprächsexporte.

## Funktionen

- Dreigeteilte Oberfläche: links Ansichten mit Anzahl (Alle, Posteingang, Archiviert,
  Ohne Gruppe, Themencluster), einklappbare Bereiche Ordner & Gruppen (mit Ordnerbaum),
  intelligente Ordner und Tags (Klick filtert) samt Kennzahlen; Mitte Chat-Liste als
  Tabelle; rechts Leseansicht mit aufklappbaren Bereichen und abgesetzten Codeblöcken.
  Navigation und Leseansicht per Ziehen (oder Pfeiltasten) in der Breite verstellbar,
  Doppelklick setzt zurück. Import, Vorschau und Jobverwaltung auf eigener Seite.
- Offizielle klassische und nummerierte Segment-ZIPs sowie Extractor-JSON;
  Analyse, Vorschau, Batch-Bestätigung und wiederaufnehmbare lokale Jobs.
- Volltextsuche in Titeln/Nachrichten und Inhaltsregeln ohne technische Nicht-Text-Platzhalter, Ordner mit Mehrfachzuordnung, Tags,
  Posteingang/Review, Regeln, gespeicherte Suchansichten und Themencluster.
- Mehrfachauswahl bis 500 geladene Chats; bestätigte zusätzliche Drag-Zuordnung,
  auf Touch-Geräten über die Auswahlleiste. Keine unsichtbare Gesamtauswahl.
- Rollen, Projekt-/Nachrichtenmetadaten und Code als Text; JSON-Export bis 500 Chats.
- ChatGPT-Denkprozesse (`thoughts`/`reasoning_recap`) als eingeklappter Block in der Leseansicht.
- Claude-Export: `conversations-000.zip` (bzw. `conversations.json`) importieren; die übrigen ZIPs
  des Claude-Exports enthalten keine Gespräche und werden mit Hinweis abgelehnt. Anbieter als Badge
  und Filter („Anbieter“ in der Navigation); Claude-Werkzeugaufrufe und Denkblöcke als Kurzzeile.
- ChatGPT-Codex-Aufgaben aus `codex.json` werden mit dem Export-ZIP als eigene Chats importiert
  (Kopfzeile „ChatGPT · Codex“).
- Optionale, ausdrücklich ausgelöste Ollama-Vorschläge: Titel und höchstens
  6000 Zeichen gehen an `127.0.0.1:11434`, keine autonome Zuordnung.
- Neue Datenbanken starten mit acht ChatGPT-Kategorien. Vorhandene Ordner,
  Zuordnungen und Regeln bleiben unverändert; entfernte Ordner werden nicht neu angelegt.

[Bedienung, Reimport-Regeln, Segmente, Jobs, Windows-Storage, Schema 4 bis 6](docs/import-details.md).
Dort stehen auch Ollama-Einrichtung, Extractor-Metadaten und die lokalen APIs.

## L2: getrennte Bibliotheken und optionaler Login

Die Authentik-OIDC-Integration (Authorization Code, PKCE, RS256, Confidential
Client mit serverseitigem Client-Secret), serverseitige Sessions, genaue
Issuer/Subjekt-Einschreibung, Account-Isolation sowie eine ausdrücklich
bestätigte Offline-Bestandsmigration sind im Code vorhanden. **Sie sind nicht
automatisch aktiv und noch nicht für den öffentlichen Betrieb freigegeben.**
Ein neuer Login legt weder Konten an noch übernimmt er bestehende Chats.
Details und Sicherheits-Gates: [SERVICE.md](SERVICE.md).

## URLs, Quellen, Datum und Importauswahl

- `/`: Landingpage ohne erfundene Demoansicht; Logo in `/app` führt dorthin.
- `/app`: Alle Chats; `/app/inbox`, `/app/archive`, `/app/unfiled`,
  `/app/import`, `/app/topics` sowie stabile Ordner-IDs
  (`/app/folders/<id>-<name>`, bisherige ID-Links bleiben gültig;
  bei Umbenennung wird der Slug aktualisiert), intelligente Ordner (`/app/smart/<id>`) und
  Direktlinks zu Chats (`/app/chats/<id>`). Browser-Zurück und Lesezeichen
  funktionieren; in L2 sind alle Pfade nur für die jeweilige Sitzung sichtbar.
- Quellen-Untertypen: ChatGPT, Codex, Claude und Extractor sind unabhängig
  vom Anbieterfilter kombinierbar. Claude Code wird nur separat gezeigt,
  wenn das Importformat eine **zuverlässige** explizite Kennzeichnung enthält;
  gewöhnliche Claude-Chats werden nicht automatisch zu Claude Code erklärt.
- Datumsbereich passend zur lokalen Browser-Zeitzone mit Start/Ende,
  älteste/neueste zuerst und „Ohne Datum“
  (insbesondere für Codex-Aufgaben ohne Zeitstempel).
- Mehrere ZIP-/JSON-Dateien in **einer Auswahl**, pro Datei eigener
  Uploadstatus, Importjob, Vorschau und bewusste Bestätigung. Eine
  gemeinsame atomare Bestätigung mehrerer ZIP-Dateien ist **nicht** vorgesehen;
  einzelne fehlerhafte Dateien blockieren nicht die übrigen Jobs. Das
  bestehende Größenlimit von 200 MB gilt **je Datei**.

Die gespeicherten Bibliotheksdaten bleiben auf dem Server pro Konto getrennt;
Benutzer-/Session-Tokens erscheinen nicht in URLs. Weitere Bedienhinweise:
[Importdetails](docs/import-details.md) und [UX-Abnahmeliste](docs/ux-f001-f009.md).

## Datenschutz

Alle Export-/Bibliotheksdaten bleiben lokal. Keine Cloud-API, Zugangsdaten,
Telemetrie oder automatische Übertragung an OpenAI. Importierte URLs/Bilder werden
nicht geladen, Inhalte nicht ausgeführt. **Nur Loopback; nicht öffentlich hosten.**

Die lokale Uploadkopie enthält das gesamte Archiv einschließlich etwaiger
Konto-/Werbedaten, bis du **Jobdaten löschen** bestätigst. Das entfernt weder die
Bibliothek noch den ursprünglichen Export. Aktive Jobs sind nicht löschbar;
Wiederaufnahme entfällt nach Bereinigung. Keine automatische Aufbewahrungsfrist.

Dieses Repository ist öffentlich: private Exporte, Datenbanken, Anhänge und
Secrets niemals committen. `.gitignore` deckt übliche SQLite-Dateien/Sidecars,
Archive, `import-jobs/`, `.env`, Schlüssel und Logs ab; ungewöhnliche eigene Namen
zusätzlich ausschließen oder außerhalb des Checkouts speichern. Es schützt nicht
vor `git add -f`, bereits verfolgten Dateien oder ungewöhnlich benannten Secrets.
Vor Push `git status --short` und `git diff --cached` prüfen. Nach versehentlicher
Veröffentlichung sensible Daten auch aus dem Git-Verlauf entfernen und betroffene
Zugangsdaten erneuern. Nur geheimnisfreie `.env.example`-Vorlagen versionieren;
Umgebungsvariablen für den Start im Terminal setzen.

Vor Upgrade/Sicherung Anwendung beenden (Strg+C); Datenbankordner inklusive
vorhandener `-wal`/`-shm`-Dateien und Originalexport separat außerhalb des Repos
sichern. Schema 4 benötigt gegebenenfalls zusätzlichen temporären SQLite-/WAL-Platz;
Schema 5 ergänzt nur die Spalte `provider` (bestehende Chats: `chatgpt`); Schema 6 baut nur den
Suchindex neu auf.

## Grenzen

- Noch kein manueller End-to-End-Test mit echtem Export; [REAL-001](TASKS.md#real-001--manueller-echttest-durch-nutzer)
  bleibt offen. Entwicklung und CI verwenden ausschließlich synthetische Daten.
- **200 MB Upload / 350 MB entpacktes JSON.** Einzelchats/Objekthüllen benötigen
  RAM; Speicherprognose ist keine Quota. Resume prüft ab Byte null; abgebrochene
  Uploads müssen neu hochgeladen werden. Exporte nicht in beschädigte Teilgraphen zerlegen.
- Windows-Importjobs: lokale feste NTFS-Laufwerke, keine OneDrive-Reparse-Pfade,
  Junctions, Symlinks, UNC-/Geräte-/Netzpfade, FAT/exFAT oder Alternate Data Streams.
  Keine unsicheren Fallbacks. Andere Plattformen können auf den synchronen API-Import
  beschränkt sein. Details zur lokalen Vertrauensgrenze stehen in der Importdokumentation.
- Ein fehlendes letztes Segment wird nur erkannt, wenn das Wurzel-`export_manifest.json`
  das bekannte Schema hat (aktuelle ChatGPT-Exporte); sonst bleibt es eine sichtbare Grenze.
  Doppelte Gesprächs-IDs im Batch werden abgelehnt.
- Aktiver Gesprächszweig und überwiegend Text; Anhänge/Bilder bleiben Referenzen.
  Kein vollständiger Medienbetrachter, keine Versionshistorie, keine automatische
  Zweigzusammenführung und kein Rundlaufexport im Originalformat. Unklare/verkürzte
  Reimporte werden abgelehnt; ältere/abweichende Klassen können ausdrücklich
  unverändert bleiben. Formatwechsel können unterschiedliche IDs erzeugen.
- Noch keine semantische Vektorsuche, umfassende Bulk-Bearbeitung oder direkte
  Extractor-Python-API-Anbindung; Themencluster sind deterministische Sichtungshilfen.
  Keine Live-Synchronisierung mit ChatGPT. [Roadmap](ROADMAP.md) · [Backlog](TASKS.md).

## Tests

```bash
python -m unittest discover -s tests -v
```

CI: Linux/Windows × Python 3.10/3.11/3.13. Skips sind keine bestandenen Tests.
Optional mit Node, Playwright und Chromium:

```bash
node tests/browser_smoke.cjs
```

Temporäre synthetische Daten; `CHROMIUM_PATH` überschreibt `/usr/bin/chromium`.
`KEEP_TEST_ARTIFACTS=1` erhält Testartefakte/Screenshots, sonst werden sie entfernt.
Nachweise: [aktuellerStand.md](aktuellerStand.md), frühere Durchläufe:
[Historie](docs/history.md). Entwicklungsregeln: [AGENTS.md](AGENTS.md).

### OIDC-Status

Kryptografie, Login-/Callback-/Logout-Handler, Session- und Datenisolation sind
im Quellcode integriert. Ein echter Authentik-End-to-End-Test und die übrigen
Betriebsfreigaben aus [SERVICE.md](SERVICE.md) sind noch offen. **Nicht
öffentlich bereitstellen** und keinen echten Bestand ohne Backup und
ausdrückliche Eigentümerfreigabe migrieren.
