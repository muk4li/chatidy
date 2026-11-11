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

## Funktionen

- ChatGPT-ZIP/JSON importieren; aktive Gesprächszweige aus der Export-Graphstruktur rekonstruieren.
- JSON-Ausgaben des vorhandenen `chatgpt-conversation-extractor` (einzeln oder als ZIP mit mehreren JSON-Dateien) importieren, inklusive dessen Textrepräsentation.
- Volltextsuche in Nachrichten und Titeln mit SQLite FTS5.
- Virtuelle verschachtelte Ordner und mehrere Gruppen pro Chat.
- Zuordnungen, Ordner und Review-Status bleiben bei erneutem Exportimport erhalten.
- Nachrichten-IDs müssen innerhalb und zwischen Chats eindeutig sein. Bei einer
  Kollision wird der gesamte Import zurückgerollt, statt Nachrichten eines anderen
  Chats zu überschreiben. Eine Wiederholung desselben Chats bleibt möglich.
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

Ist ein Änderungszeitpunkt gespeichert, muss der Reimport einen gültigen,
mindestens ebenso aktuellen Änderungszeitpunkt enthalten. Fehlt dieser oder ist
der Export älter, bricht der gesamte Dateiimport ab; auch vorher in diesem Import
verarbeitete Chats bleiben unverändert. Verwende dann einen aktuellen,
vollständigen Export desselben Gesprächszweigs. Ohne Änderungszeitpunkte auf
beiden Seiten ist nur die Prüfung der Nachrichten-IDs möglich. Gleiche IDs können
weiterhin aktualisierte Inhalte enthalten; eine vollständige Versionshistorie
speichert Chatidy derzeit nicht. Ein Wechsel zwischen Original- und
Extractor-Import kann wegen unterschiedlicher Nachrichten-IDs abgelehnt werden.

Identische sowie vollständige neuere Exporte bleiben importierbar. Bestehende
Gruppenzuordnungen und der Review-Status bleiben erhalten. Das Datenbankschema
wird durch diesen Schutz nicht verändert.

## Große Exporte und wiederaufnehmbare Importjobs

Die Weboberfläche lädt die Datei in einen lokalen Importjob (weiterhin maximal
200 MB Upload / 350 MB entpacktes JSON). JSON-Arrays werden pro Konversation
verarbeitet; Einzelkonversationen und `{"conversations": [...]}`-Hüllen benötigen
weiterhin Speicher für das ganze Objekt. Nach vollständiger Prüfung wird atomar
in SQLite übernommen. Der bisherige synchrone `/api/import` bleibt kompatibel.

Der Status zeigt die Prüfphase und die Zahl geprüfter Chats. Nach Browser- oder
Serverneustart kann der letzte Job mit **Import fortsetzen** weiterlaufen. Die
Quelle wird dabei ab Byte null erneut geprüft; bereits gespeicherte Checkpoints
werden verifiziert und wiederverwendet. Ein unvollständiger Upload muss erneut
hochgeladen werden. Ein Prozessabbruch während des SQLite-Commits wird durch die
Transaktion abgesichert; ein erneutes Übernehmen bleibt idempotent.

Quellen und Checkpoints liegen lokal in `import-jobs/` neben der durch `CHATIDY_DB`
ausgewählten Datenbank, standardmäßig unter `data/import-jobs/`. Sie enthalten
private Daten und bleiben bis zur manuellen lokalen Bereinigung erhalten.
Eigene Datenbankpfade sollten außerhalb des öffentlichen Checkouts liegen.
Ein einzelner Chat muss weiterhin in den Arbeitsspeicher passen; dies ist kein
unbegrenzter Import und kein Wiederaufnehmen ab der letzten Upload-Byteposition.

## Ordner und Regeln

Links in der Navigation auf **+** klicken, um einen Ordner anzulegen. Ordner können Unterordner besitzen. Zum Umbenennen oder Löschen zunächst den betreffenden Ordner öffnen und anschließend erneut **+** wählen. Im Chat auf **Gruppen bearbeiten** klicken, beliebig viele Gruppen auswählen und bestätigen.

Unter **Regeln** legst du Zuordnungen an: Wenn Titel, Chatinhalt oder Projekt einen Begriff enthält, wird der Chat dem ausgewählten Ordner hinzugefügt. Regeln gelten beim Import und werden beim Erstellen auch auf existierende Chats angewendet. Beim Entfernen einer Regel bleiben bereits erfolgte Zuordnungen erhalten.

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
Die additive Schema-Migration auf Version 1 erhält bestehende Datensätze und
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

GitHub Actions führt die Unit-Tests unter Python 3.11 und 3.13 aus.

## Bekannte Grenzen / Roadmap

- Noch nicht mit einem großen echten ChatGPT-Export end-to-end getestet.
- Der integrierte Parser importiert überwiegend Text aus dem aktiven Gesprächszweig; Multimodalität, Anhänge und Revisionen werden nicht vollständig übernommen.
- Semantische Vektorsuche, Drag-and-drop zwischen Ordnern, frei auswählbare Bulk-Aktionen und direkte Python-API-Anbindung an den Extractor stehen aus. Die derzeitigen Themencluster sind deterministisch und dienen der Sichtung.
- Es gibt keine automatische Live-Synchronisierung oder direkte Änderung von Chats auf chatgpt.com.
- Chatidy ist ein persönlicher, lokal gebundener Dienst und darf nicht öffentlich ins Internet gestellt werden.
