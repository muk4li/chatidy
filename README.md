# Chatidy ✳

Lokaler ChatGPT-Export-Organizer mit schöner Weboberfläche, SQLite, Suche, Ordnern, Regeln, Posteingang und optionaler lokaler KI-Kategorisierung.

> Chatidy bearbeitet ausschließlich lokal importierte ChatGPT-Exporte. Es verändert **keine** Unterhaltungen auf chatgpt.com.

## Schnellstart

Python 3.10+ (mit SQLite/FTS5) und sonst keine Abhängigkeiten:

```bash
git clone https://github.com/muk4li/chatidy.git
cd chatidy
python -m chatidy
```

Im Browser **http://127.0.0.1:8877** öffnen und dein offizielles ChatGPT-Export-ZIP oder `conversations.json` importieren.

## Windows 11: nativer Schnellstart

Kein WSL, Docker oder zusätzliches Python-Paket erforderlich. Die native
Windows-Implementierung ist auf echten `windows-latest`-Runnern mit Python
3.10, 3.11 und 3.13 erfolgreich geprüft. Der konkrete CI-Nachweis steht in
[aktuellerStand.md](aktuellerStand.md). Ein manueller Windows-11-Desktopdurchlauf
mit deinem echten Export bleibt davon getrennt.

1. Installiere Python 3.13 (oder 3.11) von **python.org**. Aktiviere im Installer
   den Python-Launcher bzw. **Add Python to PATH**. Prüfe in PowerShell
   `py -3.13 --version` (bei Python 3.11 entsprechend `py -3.11`).
2. Lade das Repository über GitHub **Code → Download ZIP** herunter und entpacke
   es, oder klone es mit Git. Öffne PowerShell im Projektverzeichnis: Dort müssen
   `README.md` und der Unterordner `chatidy` liegen.
3. Wähle einen lokalen Datenbankpfad außerhalb des Checkouts, von OneDrive und
   Netzlaufwerken. Auf einem normalen Windows-System ist dies ein NTFS-Laufwerk:

   ```powershell
   $env:CHATIDY_DB = Join-Path $env:LOCALAPPDATA "Chatidy\chatidy.sqlite3"
   py -3.13 -m chatidy
   ```

   Der Ordner wird angelegt. Verwende denselben Datenbankpfad bei jedem Start;
   ohne die Variable wird stattdessen `data/chatidy.sqlite3` im Projekt genutzt.
4. Öffne im Browser `http://127.0.0.1:8877`. Wähle **Datei auswählen** und deinen
   vollständigen offiziellen ChatGPT-Export als ZIP. Die Originaldatei wird nur
   gelesen; Chatidy speichert eine private lokale Kopie im Jobverzeichnis.
5. Warte auf **Import-Vorschau**, prüfe Segmente, Gesprächszahl und Warnungen
   und bestätige den gesamten Batch mit **Diesen Batch importieren**. Ältere oder
   abweichende Chats kannst du je Konfliktklasse vollständig unverändert lassen.
   Erst **Erfolgreich** bestätigt die atomare Übernahme. Prüfe danach die Anzahl
   der Chats/Nachrichten und suche nach einem bekannten Begriff.
6. Ein vollständiger Upload kann nach einem Prozessabbruch über **Fortsetzen**
   erneut geprüft und übernommen werden. Ein abgebrochener Upload muss neu
   hochgeladen werden. **Jobdaten löschen** verlangt eine Bestätigung und
   entfernt nur die Jobkopie, nicht importierte Chats oder den Originalexport.
7. Warte möglichst auf den Abschluss aktiver Jobs und beende den Server im
   PowerShell-Fenster mit **Strg+C**. Nach einem unerwarteten Abbruch bleiben
   SQLite-Transaktionen und Job-Wiederaufnahme wirksam.
8. Sichere bei beendeter Anwendung den gesamten Datenbankordner, einschließlich
   eventuell vorhandener `-wal`-/`-shm`-Dateien, und separat den ursprünglichen
   Export. Sichere private Daten außerhalb dieses öffentlichen Repositories.

Die Limits bleiben **200 MB Upload / 350 MB entpacktes JSON**. Einzelne sehr große
Konversationen benötigen weiterhin ausreichend RAM. Größere Exporte werden
kontrolliert abgelehnt; nicht willkürlich in beschädigte Teilgraphen zerlegen.

Häufige Windows-Fehler:

- **`py` nicht gefunden:** PowerShell nach der Installation neu öffnen oder
  `python --version` prüfen und `python -m chatidy` verwenden.
- **`No module named chatidy`:** In den entpackten Projektordner wechseln.
- **NTFS-/Reparse-/Junction-Fehler:** Einen echten lokalen NTFS-Ordner außerhalb
  von OneDrive, Junctions, Symlinks, UNC-, Geräte- und Netzlaufwerkspfaden wählen.
  Diese Sicherheitsprüfung nicht umgehen.
- **Zugriff verweigert / Datei wird verwendet:** Andere Chatidy-Instanzen,
  SQLite-Programme oder Editoren mit offenen Jobdateien schließen. Eine
  unterbrochene Bereinigung anschließend erneut ausdrücklich bestätigen.
- **Unsichere Berechtigungen:** Einen neuen privaten Datenordner unter
  `%LOCALAPPDATA%` verwenden. Vorhandene Daten nicht löschen oder ihre Rechte
  pauschal auf „Jeder: Vollzugriff“ erweitern.
- **Port 8877 belegt:** Eine noch laufende Chatidy-Instanz beenden. Den Server
  weiterhin ausschließlich über Loopback verwenden.

## Funktionen

- ChatGPT-ZIP/JSON importieren; aktive Gesprächszweige aus der Export-Graphstruktur rekonstruieren.
- JSON-Ausgaben des vorhandenen `chatgpt-conversation-extractor` (einzeln oder als ZIP mit mehreren JSON-Dateien) importieren, inklusive dessen Textrepräsentation.
- Volltextsuche in Nachrichten und Titeln mit SQLite FTS5.
- Virtuelle verschachtelte Ordner und mehrere Gruppen pro Chat.
- Zuordnungen, Ordner und Review-Status bleiben bei erneutem Exportimport erhalten.
- Nachrichten sind durch Gesprächs-ID und ursprüngliche Nachrichten-ID gemeinsam
  eindeutig. Gleiche IDs in verschiedenen Chats bleiben unabhängig; doppelte IDs
  innerhalb eines Chats brechen den gesamten Import mit Rollback ab.
- Intelligenter Posteingang für noch nicht geprüfte Gespräche.
- Lokale Themencluster aus gemeinsamen Titelbegriffen, Hashtags und vorhandenen Gruppen; bis zu 500 Chats pro Cluster nach Bestätigung gesammelt zuweisen.
- Regelbasierte Zuordnung anhand von Titel, Nachrichteninhalt und Projektmetadaten.
- Ollama-Kategorisierung als manuell zu bestätigender Vorschlag.
- Chatansicht mit Rollen, Nachrichten und Projektmetadaten.
- Export von bis zu 500 Gesprächen in strukturiertes JSON.
- Lokaler Webserver (127.0.0.1) ohne ChatGPT-Login und ohne Cloud-Sync.

## Sichere Wiederholungsimporte

Ein Reimport muss alle bereits gespeicherten Nachrichten-IDs des betreffenden
Chats enthalten. Verkürzte Exporte, leere Verläufe und Gesprächszweigwechsel,
bei denen gespeicherte Nachrichten entfallen würden, werden abgelehnt. Es werden
keine Zweige automatisch zusammengeführt oder Nachrichten stillschweigend gelöscht.

Für eine tatsächliche Aktualisierung muss der Reimport bei gespeichertem
Änderungszeitpunkt einen gültigen,
mindestens ebenso aktuellen Änderungszeitpunkt enthalten. Fehlt dieser oder ist
der Export älter, bricht der Dateiimport ohne ausdrücklich gewählte Batch-Regel ab. In der
Vorschau kann diese Klasse vollständig unverändert gelassen werden, während
andere sichere Chats atomar übernommen werden. Bereits verarbeitete Änderungen
werden bei einem Fehler des Batches vollständig zurückgerollt. Verwende dann einen aktuellen,
vollständigen Export desselben Gesprächszweigs. Ohne Änderungszeitpunkte auf
beiden Seiten ist nur die Prüfung der Nachrichten-IDs möglich. Geänderte Inhalte derselben IDs benötigen eine nachweislich neuere vollständige
Version. Unklare Änderungen ohne neueren Zeitstempel werden auch über die
Legacy-Importpfade abgelehnt; eine vollständige Versionshistorie gibt es nicht. Ein Wechsel zwischen Original- und
Extractor-Import kann wegen unterschiedlicher Nachrichten-IDs abgelehnt werden.

Identische sowie vollständige neuere Exporte bleiben importierbar. Bestehende
Gruppenzuordnungen und der Review-Status bleiben erhalten. Das Datenbankschema
wird durch diesen Schutz nicht verändert.

## Sichere Gesprächszweigauswahl

Ein gültiger `current_node` bestimmt ausschließlich seine Elternkette. Zeitstempel
ändern deren Reihenfolge nicht. Fehlt der aktive Knoten oder verweist er ins
Leere, wird nur ein einzelner vollständig eindeutiger Verlauf rekonstruiert.
Mehrere mögliche Zweige, Zyklen, fehlende Eltern und widersprüchliche optionale
`children`-Listen führen zu einem kontrollierten Importfehler. Auch beschädigte
inaktive Knoten werden abgelehnt. Nachrichten ohne eigene ID erhalten eine stabile
ID aus Chat- und Knotenschlüssel; ältere positional erzeugte Fallback-IDs können
daher vom konservativen Reimport-Schutz abgelehnt werden.

## Offizielle ZIP-Exporte mit nummerierten Segmenten

Unterstützt werden klassische `conversations.json` sowie zusammengehörige
`conversations-NNN.json`-Segmente. Die Nummern werden numerisch sortiert, müssen
bei 0 beginnen und lückenlos sein. Doppelte Nummern, mehrere Segmentverzeichnisse
oder ein Gemisch aus klassischer und segmentierter Variante werden als mehrdeutig
abgelehnt. Beschädigte ausgewählte Segmente brechen den ganzen Batch ab.

Das Archiv wird vor dem Parsen klassifiziert: Gesprächssegmente, zusätzliche
JSON-Metadaten, Anhänge/Binärressourcen, HTML-Darstellung, Begleitdateien und
unbekannte Ressourcen. `codex.json`, `ads.json`, Kontoeinstellungen, Bibliotheks-/
Anhangzuordnungen sowie `shared_conversations.json` und `sectioned_conversations.json`
werden nur inventarisiert. DAT und HTML werden weder extrahiert noch ausgeführt.
`export_manifest.json` und `sites/export_manifest.json` werden gezählt; ihre
ungeprüften Felder bestimmen weder Segmentzahl noch Dateipfade oder Limits.
Ein fehlendes letztes Segment ist ohne validiertes Manifest nicht nachweisbar;
die Vorschau macht diese Grenze sichtbar.

Unbekannte Zusatzdateien blockieren einen eindeutig erkannten offiziellen Export
nicht. Ohne offizielle Dateinamen können strukturell erkannte Conversation-/
Extractor-JSON-Dateien importiert werden. Gültige unbekannte JSON-Objekte werden
als Zusatzressourcen behandelt; beschädigtes JSON im mehrdeutigen Extractor-
Fallback bleibt aus Sicherheitsgründen ein Fehler. Doppelte Gesprächs-IDs im
selben Batch werden abgelehnt, statt Versionen still zusammenzuführen.

Nur ausgewählte Gespräche werden normalisiert in die Bibliothek übernommen.
Sensible Konto-/Werbedaten werden nicht zusätzlich in der Bibliothek persistiert;
die private lokale ZIP-Uploadkopie enthält bis zur bestätigten Jobbereinigung
weiterhin den ursprünglichen Archivinhalt. Es wurde kein privater Originalexport
für Entwicklung oder CI hochgeladen. Neue unbekannte Zusatzschemas gelten nicht
allein aufgrund ihres Dateinamens als unterstützt.

## Analyse, Import-Vorschau und Batch-Bestätigung

**Datei auswählen** startet in der Weboberfläche zunächst nur eine Analyse.
Die Gespräche werden lokal geprüft und gestaged, aber nicht in die Hauptbibliothek
übernommen. Auch eine bestehende Schema-3-Bibliothek wird durch den Analysepfad
nicht migriert. Die Vorschau zeigt Archivtyp, Segment-/Ressourcenzahlen, erkannte
Gespräche, Manifest-/Codex-/Kontodatenrollen, Konfliktklassen, Warnungen und eine
**grobe Speicherschätzung**. Sie ist keine Quota oder Zusage über freien Speicher;
eine Datenbankmigration kann zusätzlich temporären Platz benötigen.

Mit **Diesen Batch importieren** bestätigst du alle erkannten Gesprächssegmente
zusammen. Identische vorhandene Gespräche bleiben automatisch unverändert;
neuere vollständige Versionen und nachweislich nicht destruktive Ergänzungen
werden übernommen. Es gibt keine einzelne Nachfrage für jede Nachricht.

Für ältere Exporte bzw. fehlende erforderliche Änderungszeitpunkte und für
abweichende/unvollständige Zweige gibt es jeweils eine getrennte Klassenentscheidung:
**abbrechen** oder **diese Gespräche vollständig unverändert lassen**. Diese Wahl
gilt nur für den jeweiligen Job. Unklare Identitäten oder widersprüchliche
Nachrichten derselben Version sind nicht pauschal ignorierbar. Ein destruktiver
„trotzdem überschreiben“-Modus ist nicht implementiert.

Vor dem Commit werden alle Konflikte innerhalb einer SQLite-Schreibtransaktion
erneut gegen den aktuellen Bestand geprüft. Ist seit der Vorschau eine neue
Entscheidung erforderlich, wird erneut eine Vorschau angezeigt; kein alter
Analysebefund autorisiert ein stilles Überschreiben. Ordner, Tags, Review,
Nachrichtenreihenfolge und Metadaten bleiben erhalten. Alle übernommenen Chats
bilden eine Transaktion; ein später Fehler hinterlässt keinen halben Batch.

Nach einem Abbruch ist Staging wiederaufnehmbar. Eine bereits bestätigte,
unveränderte Quelle behält ihre Entscheidung nur in demselben Job; Änderungen
an der Quelle oder behandelte Fehler heben die Zustimmung auf. Ein neuer Job
übernimmt keine früheren Entscheidungen. Das Ergebnis zeigt die tatsächlich
übernommenen und unverändert gelassenen Gespräche.

Der neue Endpunkt `POST /api/import/analyze` erzeugt diese Vorschau;
`POST /api/import/jobs/<id>/confirm` verlangt `{"confirm":true,"policies":{}}`.
Optionale Policies sind ausschließlich `older` und `branch` mit `abort` oder
`skip`. Die bestehenden explizit mutierenden Legacy-Endpunkte `/api/import` und
`/api/import/jobs` bleiben für bisherige API-Clients kompatibel; sie umgehen
weder ID-, Reimport- noch Transaktionsschutz. Die normale Weboberfläche benutzt
immer den neuen zweistufigen Ablauf.

## Große Exporte und wiederaufnehmbare Importjobs

Die Weboberfläche lädt die Datei in einen lokalen Importjob (weiterhin maximal
200 MB Upload / 350 MB entpacktes JSON). JSON-Arrays werden pro Konversation
verarbeitet; Einzelkonversationen und `{"conversations": [...]}`-Hüllen benötigen
weiterhin Speicher für das ganze Objekt. Nach vollständiger Prüfung wird atomar
in SQLite übernommen. Der bisherige synchrone `/api/import` bleibt kompatibel.

Der Status zeigt die Prüfphase und die Zahl geprüfter Chats. Nach Browser- oder
Serverneustart kann ein Job mit **Import fortsetzen** weiterlaufen; eine wartende
Vorschau lässt sich in der Jobverwaltung wieder öffnen. Die
Quelle wird dabei ab Byte null erneut geprüft; bereits gespeicherte Checkpoints
werden verifiziert und wiederverwendet. Ein unvollständiger Upload muss erneut
hochgeladen werden. Ein Prozessabbruch während des SQLite-Commits wird durch die
Transaktion abgesichert; ein erneutes Übernehmen bleibt idempotent.

Quellen und Checkpoints liegen lokal in `import-jobs/` neben der durch `CHATIDY_DB`
ausgewählten Datenbank, standardmäßig unter `data/import-jobs/`. Ein einzelner
Chat muss weiterhin in den Arbeitsspeicher passen; dies ist kein unbegrenzter
Import und kein Wiederaufnehmen ab der letzten Upload-Byteposition.

### Importjob-Verwaltung und Datenschutz

Öffne **Lokale Importjobs verwalten** unter dem Importbereich. Die Übersicht zeigt
Anzahl gespeicherter Jobs, erfasste Dateigröße, Erstellung, Status und geprüfte
Gespräche. **Jobs aktualisieren** lädt den aktuellen Stand auch nach einem
Serverneustart. Sie umfasst alle Jobs, nicht nur den zuletzt im Browser geöffneten.

| Status | Verhalten |
| --- | --- |
| Hochgeladen | Lokal gespeichert; kann gestartet bzw. fortgesetzt werden. |
| In Prüfung / Wird übernommen | Prozessübergreifend gesperrt; Löschen und doppelter Start sind ausgeschlossen. |
| Vorschau bereit | Keine Übernahme ohne ausdrückliche Batch-Bestätigung. |
| Erfolgreich | Chats übernommen; lokale Jobkopien können bestätigt gelöscht werden. |
| Fehlgeschlagen | Fehler anzeigen; bei vollständiger Quelle ist ein erneuter Versuch möglich. |
| Unterbrochen | Keine aktive Sperre nach Prozessabbruch; vollständige Uploads sind wiederaufnehmbar. |
| Bereinigung unterbrochen | Teilweise entfernt; nur bestätigtes Abschließen der Bereinigung möglich. |
| Jobdaten gesperrt | Unsichere Dateien/Verzeichnisse; keine automatische Bereinigung, lokal prüfen. |

**Jobdaten löschen** fragt bei jedem Job ausdrücklich nach. Bei fehlgeschlagenen
oder unterbrochenen Jobs weist der Dialog darauf hin, dass die Wiederaufnahme
danach nicht mehr möglich ist. Abbrechen behält sämtliche Jobdaten. Aktive Jobs
sind auch serverseitig gegen Löschen gesperrt. Die Bestätigung entfernt nur die
lokalen Uploadkopien, Status- und Stagingdateien. Die Chatidy-Datenbank samt Suche
und die ursprüngliche Exportdatei außerhalb des Jobverzeichnisses bleiben erhalten.
Es gibt keine automatische Löschung oder Aufbewahrungsfrist.

Die Bereinigung validiert UUIDs, Verzeichnisse und eine feste Dateiliste. Sie
folgt keinen Symlinks, lehnt Hardlinks/fremde Einträge ab und löscht niemals
rekursiv beliebige Pfade. Eine atomare Umbenennung markiert die bestätigte
Löschung; nach einem Abbruch bleibt sie als erneut bestätigbare Bereinigung
sichtbar. Die leere `management.lock` bleibt zur Prozesskoordination im Stamm;
sie zählt nicht als gespeicherter Job. Dateigrößen sind logische Größen zum
Abfragezeitpunkt; gesperrte oder fremde Einträge sind darin nicht enthalten.

Benutzerdefinierte Datenbankpfade sollten außerhalb des öffentlichen Checkouts
liegen. `.gitignore` schützt nun `import-jobs/` auf jeder Verzeichnisebene sowie
die üblichen SQLite-Dateiendungen und Sidecars. Ein beliebig benannter eigener
Datenbankpfad ohne solche Endung muss zusätzlich lokal ausgeschlossen werden;
`.gitignore` schützt weiterhin nicht vor `git add -f` oder bereits verfolgten Daten.

Die Storage-Abstraktion wählt das Backend ausdrücklich nach Betriebssystem:
Unter Linux bleiben `flock`, descriptorrelative Operationen und `/proc/self/fd`
erhalten. Unter Windows verwendet sie `CreateFileW` mit Reparse-Prüfung,
über die gesamte Verarbeitung gehaltene Verzeichnishandles, private NTFS-DACLs,
`msvcrt`-Dateisperren und native atomare Statusersetzung. SQLite erhält dort einen
regulären, durch die gehaltenen Pfad-Handles geschützten Dateinamen. Vor dem Löschen wird das umbenannte Verzeichnis erneut gepinnt und seine
native Identität geprüft; Dateilöschungen erfolgen über geprüfte Windows-Handles; aktive Job-Leases und die
Registry-Sperre bleiben auf beiden Plattformen wirksam.

Windows unterstützt zunächst **lokale feste NTFS-Laufwerke**. Junctions,
Symlinks, sonstige Reparse Points, Hardlinks, UNC-/Gerätepfade, Netzlaufwerke und
für andere Benutzer schreibbare Jobdateien werden kontrolliert abgelehnt.
SYSTEM und Administratoren bleiben vertrauenswürdige Betriebssystemidentitäten.
Ein fehlender Windows-Symlink-Test wegen fehlender Berechtigung zählt nicht als
bestandener Test; Junction-Tests benötigen diese Berechtigung nicht. Die Abwehr
ersetzt keine Zugriffskontrolle gegen Programme mit demselben Benutzerkonto.
Auf anderen nicht unterstützten Plattformen bleibt der synchrone `/api/import`
verfügbar; es gibt keinen unsicheren Storage-Fallback. Keine neue Pflichtabhängigkeit
und keine Datenbankmigration sind erforderlich.

Zusätzliche lokale HTTP-Endpunkte (Host-/Origin-Prüfung bleibt aktiv):

- `GET /api/import/jobs`: Übersicht mit Anzahl und erfasster Größe.
- `GET /api/import/jobs/<id>`: bisheriger Status, ergänzt um Erstellung, Größe,
  Aktivität sowie `can_resume` und `can_delete`.
- `POST /api/import/jobs/<id>/resume` mit `{}`: bisherigen Job fortsetzen.
- `POST /api/import/jobs/<id>/delete` mit `{"confirm": true}`: explizit bestätigte
  Bereinigung. Fehlende oder nicht-boolsche Bestätigung wird abgelehnt.

## Ordner und Regeln

Links in der Navigation auf **+** klicken, um einen Ordner anzulegen. Ordner können Unterordner besitzen. Zum Umbenennen oder Löschen zunächst den betreffenden Ordner öffnen und anschließend erneut **+** wählen. Im Chat auf **Gruppen bearbeiten** klicken, beliebig viele Gruppen auswählen und bestätigen.

Unter **Regeln** legst du Zuordnungen an: Wenn Titel, Chatinhalt oder Projekt einen Begriff enthält, wird der Chat dem ausgewählten Ordner hinzugefügt. Regeln gelten beim Import und werden beim Erstellen auch auf existierende Chats angewendet. Beim Entfernen einer Regel bleiben bereits erfolgte Zuordnungen erhalten.

## Mehrfachauswahl, Tags und intelligente Ordner

- Checkboxen wählen bis zu 500 geladene Chats aus. **Zuordnen** fügt sie nach
  Bestätigung einem Zielordner hinzu; bestehende Gruppen bleiben erhalten.
- Ziehe einen Chat oder eine bestehende Auswahl auf einen Ordner. Auch diese
  zusätzliche Zuordnung verlangt eine Bestätigung. Auf Touch-Geräten dient die
  Auswahlleiste als Alternative zum nativen Browser-Drag-and-drop.
- **Tags bearbeiten** im Chat ersetzt dessen Tags nach Bestätigung im Dialog;
  **Tags hinzufügen** ergänzt Tags für die Auswahl. Tags werden normalisiert und
  können über das Auswahlfeld gefiltert werden (maximal 20 je Aktion, 60 Zeichen
  je Name). Gruppenzuordnungen, Tags und Review bleiben bei Reimports erhalten.
- **Suche speichern** legt einen intelligenten Ordner aus Textsuche, Tag und
  Bibliotheksansicht an. Er wird bei jedem Öffnen neu ausgewertet und enthält
  dadurch auch passende später importierte Chats. Die API unterstützt außerdem
  exakte Projektfilter. Das Löschen eines intelligenten Ordners löscht keine Chats.

Tags und gespeicherte Abfragen werden additiv in Schema 2 eingeführt; Schema 3
bewahrt die Nachrichtenreihenfolge ausdrücklich statt nach Datum neu zu sortieren.
Intelligente Ordner sind gespeicherte Suchabfragen, keine automatische KI-Zuordnung.
Die Auswahl umfasst geladene Ergebnisse, keine unsichtbare Gesamtauswahl.

## Optionale KI mit Ollama

Lokales Ollama installieren und das Modell laden:

```bash
ollama pull llama3.2
ollama serve
```

KI-Vorschläge werden erst nach einer gesonderten Bestätigung erzeugt. Pro Aufruf werden Titel und höchstens 6000 Zeichen Nachrichten an **127.0.0.1:11434** gesendet. Die KI entscheidet nicht autonom und bearbeitet keine ChatGPT-Inhalte.

## Optionale Extractor-Integration und erhaltene Metadaten

Der unabhängige JSON-Adapter importiert Einzeldateien, JSON-Arrays und ZIPs aus
`chatgpt-conversation-extractor`. Das externe Werkzeug wird nicht zur Pflicht:
Offizielle ChatGPT-Exporte funktionieren weiterhin direkt. Zusätzliche
Gesprächsfelder (z. B. Modelle und Projektinformationen) sowie Nachrichtenfelder
(Zitate, Quellen, Dateireferenzen und Multimodalitätsdaten) werden lokal als JSON
aufbewahrt und über Chatansicht und JSON-Export zugänglich. Fehlende Zusatzfelder
löschen bereits gespeicherte Zusatzfelder beim Reimport nicht; vorhandene Felder
werden auf oberster Ebene aktualisiert. Codeblöcke bleiben unverändert als Text.

Bild-/Anhangdaten bleiben Referenzen und Metadaten: Es werden keine Binärdateien
aus Archiven extrahiert, keine entfernten Bilder geladen und keine importierten
Inhalte ausgeführt. Dies ist noch kein vollständiger Medienbetrachter und kein
Rundlaufexport im Originalformat. Importformate können unterschiedliche IDs nutzen.
Die Metadaten-Migration (Version 1) erhält bestehende Datensätze und
bricht bei unbekannten neueren Datenbankversionen ab. Vor einem Upgrade empfiehlt
sich eine lokale Sicherung der geschlossenen Datenbank außerhalb des Repositories.

## Datenschutz

- Exportdateien und SQLite-Datenbank liegen ausschließlich lokal; Chatidy speichert unter `data/chatidy.sqlite3`.
- Optionaler Datenbankpfad: Umgebungsvariable `CHATIDY_DB`.
- Kein automatisches Senden an OpenAI, keine Zugangsdaten und keine Cloud-API.
- Die `.gitignore` blendet private Exporte und Datenbanken aus. Dennoch vor jedem Git-Commit Inhalte sorgfältig prüfen.
- **Dieses Repository ist und bleibt öffentlich.** Persönliche Exporte, lokale Datenbanken, Anhänge und Zugangsdaten gehören niemals in Git-Commits. Die Anwendung arbeitet auf diesen Daten ausschließlich lokal.
- Die `.gitignore` deckt die üblichen lokalen Speicherorte, SQLite-WAL/SHM-Dateien, Exportarchive, `.env`-Konfigurationen, Schlüsseldateien und Logs ab. Für eigene Importpfade außerhalb dieser Muster empfiehlt sich `data/` oder `imports/`.
- **Wichtig:** `.gitignore` schützt nicht vor `git add -f`, bereits versionierten Dateien oder Geheimnissen in ungewöhnlich benannten Dateien. Vor jedem Push `git status --short` und `git diff --cached --name-only` kontrollieren; bei versehentlicher Veröffentlichung müssen sensible Daten zusätzlich aus dem Git-Verlauf entfernt und Zugangsdaten erneuert werden.
- Für lokale Konfigurationen kannst du `.env` verwenden; dokumentierte, **geheimnisfreie** Vorlagen dürfen als `.env.example` versioniert werden.

## Bestehende Bausteine / Erweiterungsplan

- [chatgpt-conversation-extractor](https://github.com/muk4li/chatgpt-conversation-extractor): bewährte High-Fidelity-Konvertierung. Chatidy enthält jetzt einen **Adapter für die vom Extractor erzeugten strukturierten JSON-Dateien**. Die vollständige direkte Nutzung seiner Python-API und der erweiterten Metadaten bleibt ein späterer Schritt.
- [instakram](https://github.com/muk4li/instakram): Vorbild für lokale Ordner, Regeln und Review-Prozesse. Künftige Integration über APIs statt gemeinsamer SQLite-Datei.
- [chat-organizer-extension](https://github.com/muk4li/chat-organizer-extension): separater Organizer für den Browser. Kein direkter Live-ChatGPT-Zugriff in Chatidy.

## Tests

```bash
python -m unittest discover -s tests -v
```

GitHub Actions definiert die vollständige Unit-Testmatrix für `ubuntu-latest` und
`windows-latest` mit Python 3.10, 3.11 und 3.13. Windows-spezifische Tests laufen
ausschließlich auf einem echten Windows-Host; übersprungene Tests zählen nicht als
Windows-Verifikation.
Optionaler echter Browsertest mit installiertem Node, Playwright und Chromium:

```bash
node tests/browser_smoke.cjs
```

`CHROMIUM_PATH` kann den Browserpfad überschreiben (Standard `/usr/bin/chromium`).
Der Test startet selbst einen lokalen Server mit temporärer synthetischer
Datenbank. Für Screenshots `KEEP_TEST_ARTIFACTS=1` setzen; sonst werden die
synthetischen Testartefakte nach dem Lauf entfernt.

Den iterativen Entwicklungsstand und die Ergebnisse aller vier Folgephasen
beschreibt [aktuellerStand.md](aktuellerStand.md).

## Bekannte Grenzen / Roadmap

- Noch nicht mit einem großen echten ChatGPT-Export end-to-end getestet.
- Der integrierte Parser importiert überwiegend Text aus dem aktiven Gesprächszweig; Multimodalität, Anhänge und Revisionen werden nicht vollständig übernommen.
- Semantische Vektorsuche, umfassende Bulk-Bearbeitung und direkte Python-API-Anbindung an den Extractor stehen aus. Drag-and-drop ordnet zusätzlich zu, statt Mitgliedschaften zu verschieben. Themencluster sind deterministisch und dienen der Sichtung.
- Es gibt keine automatische Live-Synchronisierung oder direkte Änderung von Chats auf chatgpt.com.
- Chatidy ist ein persönlicher, lokal gebundener Dienst und darf nicht öffentlich ins Internet gestellt werden.

## Nachrichtenidentität und Schema 4

Schema 4 stellt die Nachrichtentabelle transaktional auf den zusammengesetzten
Schlüssel `(conversation_id, id)` um. Vorhandene IDs, Inhalte, Metadaten und
Positionen werden kopiert und erhalten; Ordner, Tags, Review und FTS5 bleiben
unverändert. Ein fehlgeschlagener Umbau rollt Daten, Schema und Versionsnummer
zurück. Bestehende Dateien vor dem Upgrade bei geschlossener Anwendung lokal
sichern. Die Änderung kann zusätzliches temporäres SQLite-/WAL-Speichervolumen
benötigen. Der private Originalexport wurde für die Entwicklung nicht untersucht.
