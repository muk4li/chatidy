# Chatidy ✳

Chatidy organisiert lokale ChatGPT-Exporte: Python-Standardbibliothek,
SQLite/FTS5 und eine Weboberfläche unter **http://127.0.0.1:8877**.
Es verändert keine Unterhaltungen auf chatgpt.com und benötigt keinen ChatGPT-Login.

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

Browser öffnen → links **Import** (öffnet sich bei leerer Bibliothek automatisch) →
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

## Funktionen

- Dreigeteilte Oberfläche: links Ansichten mit Anzahl (Alle, Posteingang, Archiviert,
  Ohne Gruppe, Themencluster), einklappbare Bereiche Ordner & Gruppen (mit Ordnerbaum),
  intelligente Ordner und Tags (Klick filtert) samt Kennzahlen; Mitte Chat-Liste als
  Tabelle; rechts Leseansicht mit aufklappbaren Bereichen und abgesetzten Codeblöcken.
  Navigation und Leseansicht per Ziehen (oder Pfeiltasten) in der Breite verstellbar,
  Doppelklick setzt zurück. Import, Vorschau und Jobverwaltung auf eigener Seite.
- Offizielle klassische und nummerierte Segment-ZIPs sowie Extractor-JSON;
  Analyse, Vorschau, Batch-Bestätigung und wiederaufnehmbare lokale Jobs.
- Volltextsuche in Titeln/Nachrichten, Ordner mit Mehrfachzuordnung, Tags,
  Posteingang/Review, Regeln, gespeicherte Suchansichten und Themencluster.
- Mehrfachauswahl bis 500 geladene Chats; bestätigte zusätzliche Drag-Zuordnung,
  auf Touch-Geräten über die Auswahlleiste. Keine unsichtbare Gesamtauswahl.
- Rollen, Projekt-/Nachrichtenmetadaten und Code als Text; JSON-Export bis 500 Chats.
- Optionale, ausdrücklich ausgelöste Ollama-Vorschläge: Titel und höchstens
  6000 Zeichen gehen an `127.0.0.1:11434`, keine autonome Zuordnung.
- Neue Datenbanken starten mit acht ChatGPT-Kategorien. Vorhandene Ordner,
  Zuordnungen und Regeln bleiben unverändert; entfernte Ordner werden nicht neu angelegt.

[Bedienung, Reimport-Regeln, Segmente, Jobs, Windows-Storage und Schema 4](docs/import-details.md).
Dort stehen auch Ollama-Einrichtung, Extractor-Metadaten und die lokalen APIs.

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
sichern. Schema 4 benötigt gegebenenfalls zusätzlichen temporären SQLite-/WAL-Platz.

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
- Manifestschemas sind ungeprüft: ein fehlendes letztes Segment ist ohne validierte
  Gesamtzahl nicht erkennbar. Doppelte Gesprächs-IDs im Batch werden abgelehnt.
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
