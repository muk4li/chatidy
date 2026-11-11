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
- Volltextsuche in Nachrichten und Titeln mit SQLite FTS5.
- Virtuelle verschachtelte Ordner und mehrere Gruppen pro Chat.
- Zuordnungen, Ordner und Review-Status bleiben bei erneutem Exportimport erhalten.
- Intelligenter Posteingang für noch nicht geprüfte Gespräche.
- Regelbasierte Zuordnung anhand von Titel, Nachrichteninhalt und Projektmetadaten.
- Ollama-Kategorisierung als manuell zu bestätigender Vorschlag.
- Chatansicht mit Rollen, Nachrichten und Projektmetadaten.
- Export von bis zu 500 Gesprächen in strukturiertes JSON.
- Lokaler Webserver (127.0.0.1) ohne ChatGPT-Login und ohne Cloud-Sync.

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

## Datenschutz

- Exportdateien und SQLite-Datenbank liegen ausschließlich lokal; Chatidy speichert unter `data/chatidy.sqlite3`.
- Optionaler Datenbankpfad: Umgebungsvariable `CHATIDY_DB`.
- Kein automatisches Senden an OpenAI, keine Zugangsdaten und keine Cloud-API.
- Die `.gitignore` blendet private Exporte und Datenbanken aus. Dennoch vor jedem Git-Commit Inhalte sorgfältig prüfen.
- **Achtung: Dieses Repository wurde beim Start als öffentlich erkannt. Bitte auf Private stellen, wenn du später persönlichen Code oder vertrauliche Informationen speichern möchtest.**

## Bestehende Bausteine / Erweiterungsplan

- [chatgpt-conversation-extractor](https://github.com/muk4li/chatgpt-conversation-extractor): bewährte High-Fidelity-Konvertierung. Chatidy verwendet aktuell einen eigenen fokussierten JSON-Importer. Ein Adapter zum vollständigen Extractor ist **noch nicht implementiert** und für komplexe Exportvarianten geplant.
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
- Semantische Suche, Themencluster, Massenzuordnung, Umzug in Ordner per Drag-and-drop und eine vollständige Extractor-Adapter-Anbindung stehen aus.
- Es gibt keine automatische Live-Synchronisierung oder direkte Änderung von Chats auf chatgpt.com.
- Chatidy ist ein persönlicher, lokal gebundener Dienst und darf nicht öffentlich ins Internet gestellt werden.