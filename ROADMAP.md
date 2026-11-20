# Chatidy – Produkt-Roadmap

Stand: Nutzbarkeitsdurchlauf auf main `8e19e78` (2026-11-14). Legende: **Implementiert und getestet**,
**Teilweise implementiert**, **Offen**, **Blockiert**. Neue Funktionen dieses
Durchlaufs werden erst nach ihren Tests hochgestuft; private Exportdaten bleiben lokal.

Aktueller Fokus: Nutzbarkeit und Verständlichkeit. Passende Startkategorien und
kompakte Dokumentation sind umgesetzt (FOCUS-001). Nächster Nachweis ist der
lokale manuelle Echttest durch den Nutzer (REAL-001); dieser bleibt offen.
Weitere Import-/Storage-Härtung und neue Plattformfälle nur auf ausdrücklichen Auftrag.
Die folgenden offenen Themen sind Backlog, keine automatisch folgenden Aufträge.

## Phase 1 – Exportkompatibilität und Datenintegrität

- **Implementiert und getestet:** klassische und nummerierte offizielle
  Konversationsdateien, explizite Archivklassifizierung, gemeinsame Segment-Batches.
- **Implementiert und getestet:** Schema-4-Migration auf gesprächsbezogene
  Nachrichtenidentität; IDs/Bestandsdaten/Reihenfolge bleiben erhalten.
- **Implementiert und getestet:** schreibfreie Import-Vorschau, einmalige
  Batch-Bestätigung, automatische idempotente Fälle und getrennte nicht destruktive
  Entscheidungen für ältere bzw. abweichende/unvollständige Versionen.
- **Implementiert und getestet:** Graphprüfung, atomare Transaktionen, konservativer
  Reimport-Schutz, lokales Staging/Wiederaufnahme sowie Windows-/Linux-Backend.
  Neue Implementierung: CI 43561857600 mit Python 3.10/3.11/3.13 auf beiden Hosts.
- **Teilweise implementiert:** große Exporte (Streaming/Jobs; 200/350-MB-Limits,
  Einzelobjekte benötigen RAM; keine unbegrenzte Skalierbarkeit).
- **Teilweise implementiert:** Zusatzressourcen/Manifeste werden inventarisiert;
  ihre noch ungeprüften Schemas werden nicht als unterstützt behauptet.
- **Implementiert und getestet (synthetisch):** Abgleich der Konversationsdateien mit dem
  Wurzel-`export_manifest.json`, sofern dessen Schema erkannt wird (META-001); fehlende
  Endsegmente werden dann erkannt. Unbekannte Manifeste bleiben nur inventarisiert.
- **Offen:** komplexe Mehrversions-/Zweigrekonstruktion und überlappende
  Gesprächs-Snapshots. Details: TASKS.md.

## Phase 2 – Organisation und UX

- Implementiert und getestet: Ordner, Tags, Mehrfachauswahl (geladene Ergebnisse),
  zusätzliche Drag-and-drop-Zuordnung, gespeicherte Suchansichten, Regeln, Review.
- Implementiert und getestet (Browser, synthetisch): dreigeteilte Oberfläche
  (Navigation | Chat-Liste | Leseansicht), Import auf eigener Seite, Tag-Filter in der Navigation,
  einklappbare Bereiche, verstellbare Seitenleisten, Zähler für alle Ansichten.
- Teilweise implementiert: intelligente Sammlungen, Filter/Suche, Markdown/Code
  (FTS5, sichere Textdarstellung, abgesetzte Codeblöcke; keine umfassende Markdown-Renderpipeline).
- Offen: eigenständige Favoriten, fortgeschrittene Filter, größere Bulk-Workflows.

## Phase 3 – Lokale Intelligenz

- Teilweise implementiert: explizite Ollama-Vorschläge und deterministische Themencluster.
- Offen: semantische Suche, lokale Embeddings, erklärbare Kategorisierungsvorschläge,
  Konfidenzwerte und Feedback-Lernen. Keine autonome Klassifikation ohne Sicherheitsgrenzen.
  Konkreter Backlog-Ansatz für viele Chats (Embeddings + Beispiele, LLM nur für unsichere Fälle): AUTO-001.

## Phase 4 – Knowledge Management

- Teilweise implementiert: JSON-Export und lokale Import-/Export-APIs.
- Offen: verwandte Gespräche, Zusammenfassungen, Wissensgraph, Volltext-/Vektorkombination,
  Projektwissen, Medienbibliothek und Markdown-Export.

## Phase 5 – Integration

- Teilweise implementiert: unabhängiger JSON-Adapter für chatgpt-conversation-extractor.
- Offen: optionale Anbindung an instakram, chat-organizer-extension,
  chatgpt-cost-dashboard und personal-platform; keine verpflichtende Kopplung.

## Phase 6 – Mehrere Chat-Anbieter (geplant)

Status: **Teilweise implementiert** – PROV-001 und PROV-002 (Claude-Import inkl. UI) umgesetzt, Prüfung mit
echtem Claude-Export durch den Nutzer offen; PROV-004 (Codex) umgesetzt; PROV-003 Backlog. Details: TASKS.md.

Ziel: Neben ChatGPT auch Claude-Exporte (claude.ai, Settings › Privacy › Export data)
verlustfrei importieren; jeder Chat trägt sichtbar und filterbar seinen Anbieter.
Die Architektur soll außerdem auf Formatänderungen der Anbieter, weitere Cloud-Anbieter
und lokale Oberflächen (z. B. Open WebUI) reagieren können, falls Bedarf entsteht –
ohne dafür jetzt schon Adapter zu bauen.

Claude-Export – Strukturbefund (2026-11-20, ein echtes kleines Konto, lokal nur
Schlüssel/Typen ausgewertet, keine Inhalte; ältere öffentliche Beschreibungen waren teils falsch):

- **Lieferung:** Manifest-JSON (`version`, `total_files`, `data_files[]` mit `category`,
  `batch_index`, `part`, `filename`, `export_url`) plus ein ZIP **pro Kategorie**, nicht pro
  Gesprächssegment. Beobachtet: Gespräche, Konto (`users.json`, `login_history.json`),
  Memory (eine JSON je Konto), Artifacts (`artifacts/<id>/artifact.json`, `comments.json`,
  Markdown) und Claude-Code-Routinen (`routines.json`, `routine_runs.json`).
  Kein `projects.json`, kein separates `memories.json` in diesem Export.
  Dateinamen: `manifest-<id>.json` und `<kategorie>-NNN.zip` mit den Kategorien
  `conversations`, `light_metadata` (Konto/Login), `memories`, `frames` (Artifacts) und
  `claude_code_cloud` (Routinen). Große Konten erhalten vermutlich `conversations-001.zip` usw.
- **Gespräche** nur in einem ZIP: `conversations.json` (Array). Gespräch: `uuid`, `name`
  (kann leer sein), `summary`, `created_at`/`updated_at` (ISO), `account.uuid`,
  `chat_messages[]`. Kein Modell- und kein Projektfeld.
- **Nachricht:** `uuid`, `sender` (`human`/`assistant`), `text` (Zusammenfassung, kann leer
  sein), `content[]`, `created_at`/`updated_at`, `parent_message_uuid` (immer vorhanden),
  `attachments[]` (`file_name` oft leer, `file_type`, `file_size`, `extracted_content`),
  `files[]` (nur `file_name`/`file_uuid`, keine Binärdaten im Export).
- **`content[]`-Blocktypen:** `tool_use`, `tool_result`, `thinking` (meist leer, `thinking_hidden`),
  `text` (mit `citations[]` inkl. URLs), `document`, `injected_prompt_block`. Tool-Ergebnisse
  enthalten verschachtelte Blöcke (`text`, `knowledge`, `image`, `local_resource`) sowie
  Favicon-/Icon-URLs. Tool-Daten machen den Großteil der Dateigröße aus.
- **Zweige existieren:** mindestens ein Gespräch, dessen Elternverweise nicht der
  Listenreihenfolge folgen. Ein Feld für den aktuellen Zweig (wie `current_node` bei ChatGPT)
  gibt es nicht.

ChatGPT-Export – Strukturbefund (2026-11-20, aktueller echter Export vom 2026-11-11, nur Schlüssel/Typen):

- 8 Segmente `conversations-000…007.json` (wird bereits unterstützt). Knoten im `mapping` haben
  nur noch `id`, `message`, `parent` – **kein `children` mehr**; Wurzelknoten teils unter dem
  Schlüssel `client-created-root`. `graph.py` behandelt `children` bereits als optional (geprüft).
- Rollen im Export nur `user`/`assistant`. `content_type`: `text`, `multimodal_text`
  (Bild-, Audio-, Transkriptteile), `thoughts` und `reasoning_recap` – zusammen gut ein Viertel aller
  Nachrichten. Diese erscheinen heute in der Leseansicht als Platzhalter „[Nicht-textueller Inhalt]“
  (Rohdaten bleiben in `metadata`). Siehe CGPT-001.
- `codex.json` enthält Codex-Aufgaben als eigene Verläufe (`turns[]` mit Nutzer-/Assistentenrolle,
  PR-Titel, Diff-Kennzahlen, Dateiausschnitten). Heute nur als Metadaten inventarisiert. Siehe PROV-004.
- `export_manifest.json` (Wurzel) hat jetzt ein lesbares Schema: `logical_files.<name>.files[]`,
  `sharded`, `shard_count`, `export_files[].size_bytes`. Damit wäre ein fehlendes letztes Segment
  nachweisbar (bisherige Grenze in EXP-001). Siehe META-001.
- Nachrichtenmetadaten sind sehr umfangreich (`content_references` mit Widgets, Orten, Bildern,
  vielen URLs). Werden mitgespeichert; E12 gilt auch hier.
- `.dat`-Anhänge sind teils Office-Dateien (intern ZIP). Werden weiterhin nur gezählt.

### Lösungsentscheidungen

- **E1 – Ein Adapter pro Exportformat.** Jedes Format (ChatGPT offiziell, Extractor,
  Claude, später weitere) erkennt seine Struktur und liefert das bestehende normalisierte
  Chat-Modell. Konfliktprüfung, Jobs, Staging, FTS5, Organisation und UI arbeiten nur mit
  diesem Modell und bleiben anbieterneutral. Bewusst einfach: feste Adapterliste im Code,
  kein Plugin-Loader, keine neuen Abhängigkeiten.
- **E2 – Erkennung über Struktur, eindeutig oder Abbruch.** Formate werden an ihren
  Schlüsseln erkannt (z. B. `mapping`, `chat_messages`), nicht am Dateinamen – beide
  Anbieter liefern `conversations.json`. Passt kein oder mehr als ein Adapter, bricht der
  Import mit verständlicher Meldung ab; der heutige „sonst Extractor“-Fallback wird dafür
  durch eine ausdrückliche Extractor-Erkennung ersetzt.
- **E3 – Herkunft als feste Spalte `provider`.** Versionierte Migration fügt
  `conversations.provider` hinzu (Bestand: `chatgpt`). Kein Tag, weil Tags umbenannt oder
  gelöscht werden können. Exportformat und Adapterversion zusätzlich in `metadata.source`.
- **E4 – Konversations-IDs mit Anbieterpräfix für neue Anbieter.** Neue Anbieter
  speichern `<provider>:<original-id>`; bestehende ChatGPT-IDs bleiben unverändert
  (keine ID-Migration). Original-ID bleibt in den Metadaten erhalten.
- **E5 – Rohdaten vollständig bewahren.** Wie beim ChatGPT-Import landen Gesprächs- und
  Nachrichtenrohdaten in `metadata`. Anzeige-/Suchtext entsteht aus den Textblöcken;
  Thinking, Tool-Aufrufe, Artifacts und Anhangstexte gehen nicht verloren. Unbekannte
  Blocktypen erscheinen als Platzhalter mit Typname, werden nie stillschweigend verworfen.
- **E6 – Formatänderungen: bewahren statt raten.** Unbekannte Felder werden gespeichert,
  aber nicht interpretiert. Fehlen Pflichtfelder eines Adapters, zeigt die Vorschau den
  Fehler, statt teilweise zu importieren. Jede bekannte Formatvariante erhält eine
  synthetische Test-Fixture.
- **E7 – Lokale Anbieter nur über Dateiexport.** Open WebUI o. Ä. würden über ihren
  JSON-Export als weiterer Adapter angebunden – kein Zugriff auf fremde Datenbanken oder
  APIs, keine Netzwerkverbindung (local-first). Baumartige Verläufe nutzen die vorhandene
  Graph-/Zweiglogik.
- **E8 – Oberfläche ist nicht ableitbar.** Weder ChatGPT- noch Claude-Exporte enthalten,
  ob ein Chat im Web, in der Desktop- oder Mobil-App geführt wurde. Pflichtfeld ist daher
  nur der Anbieter; die Oberfläche kann bei Bedarf manuell per Tag gepflegt werden.
- **E9 – Zusatzdateien nur inventarisieren.** `projects.json`, `memories.json` und
  `users.json` werden als Metadaten erkannt, nicht als Chats importiert; `memories.json`
  und `users.json` gelten als sensibel. Projekte erst zuordnen, wenn der Export eine
  Gespräch-Projekt-Verknüpfung enthält (derzeit nicht).

- **E10 – Claude-Zweige über Elternverweise.** Nachrichten bilden über
  `parent_message_uuid` einen Baum (Wurzel: Elternverweis zeigt auf keine Nachricht des Chats).
  Mangels Feld für den aktuellen Zweig gilt das Blatt mit dem spätesten `created_at` als
  aktueller Zweig; vorhandene Graphprüfung wiederverwenden. Nachrichten anderer Zweige
  gehen nicht verloren, sondern bleiben in den Gesprächsmetadaten (anders als heute beim
  ChatGPT-`mapping`). Zyklen oder mehrere gleich späte Blätter: Abbruch statt Raten.
- **E11 – Lesetext getrennt von Tooldaten.** Leseansicht und Volltextsuche nutzen nur
  `text`-Blöcke (Fallback: Feld `text`) und `extracted_content` von Anhängen. `tool_use`/
  `tool_result`/`thinking` erscheinen als einklappbare Kurzzeile (Typ, Toolname), Rohdaten in
  `metadata`. Sonst würden Suche und Themencluster von Tool-Ausgaben dominiert.
- **E12 – URLs aus Exporten nie laden.** Zitate, Favicons und Integrations-Icons bleiben
  Text; die UI erzeugt aus importierten URLs keine Bilder oder automatischen Abrufe.
- **E13 – Nur das Gesprächs-ZIP importieren.** Chatidy erkennt das ZIP mit
  `conversations.json`; Konto-, Login-, Memory-, Artifact- und Routinen-ZIPs werden nicht als
  Chats gelesen. Separat hochgeladen ergeben sie eine verständliche Meldung („enthält keine
  Gespräche, Kategorie: …“, erkennbar am Präfix `<kategorie>-NNN.zip` und am Inhalt). Manifest nur zum Erkennen/Zuordnen, nie Links aufrufen.
  Artifacts sind ein möglicher späterer Import (eigene Aufgabe, kein Teil von PROV-002).

### Risiken und Gegenmaßnahmen

| Risiko | Gegenmaßnahme |
|---|---|
| Anbieterformate sind undokumentiert und ändern sich (z. B. `text` vs. `content[]`, Schlüsselvarianten) | E5/E6; Fixtures je Variante; Strukturabgleich mit echtem Export nur über Schlüssellisten, nie Inhalte |
| Datenverlust bei Thinking/Tools/Artifacts/Anhängen | Rohdaten in `metadata`, Platzhalter statt Verwerfen; Binäranhänge sind im Export nicht enthalten (Exportgrenze, dokumentieren) |
| Fehlerkennung eines Formats: Claude-Varianten mit `messages` statt `chat_messages` landen im heutigen Extractor-Fallback (alles ohne `mapping`). Derzeit bricht der Import nur ab, weil Claude `uuid` statt `id` nutzt – ein zufälliger Schutz. Hätte eine Variante `id`, würde sie still falsch gelesen: `sender` ignoriert (Rolle `unknown`), `content[]`-Blöcke und Feld `text` nicht übernommen, Nachrichten verworfen | E2: positive Merkmale je Format (Extractor: `id` + `messages[].role`; Claude: `uuid` + `sender`), genau ein Treffer oder Abbruch; gilt auch für die Strukturerkennung in ZIPs ohne offizielle Dateinamen; Regressionstest in PROV-001/PROV-002 |
| ID-Kollision zwischen Anbietern | E4 |
| Zweige im Claude-Export (bestätigt), ohne Kennzeichnung des aktuellen Zweigs | E10; Fixtures für verzweigte, unsortierte und zyklische Verläufe |
| Große Konten: Gespräche auf mehrere `part`-ZIPs verteilt (bisher nicht beobachtet) | Jedes Teil-ZIP einzeln importierbar; doppelte Gesprächs-IDs über Teile hinweg prüfen; erst nach Nachweis als unterstützt bezeichnen (vgl. SCALE-001/META-001) |
| Sensible Zusatzdaten: Name, E-Mail, Login-Historie mit IP-Adressen, Memory | E9/E13; nie persistieren, in Vorschau als sensibel kennzeichnen, Upload-Kopie per „Jobdaten löschen“ entfernbar |
| Tool-Daten blähen Exporte auf (beobachtet: mehrere hundert KB je Gespräch) – bei viel Agenten-Nutzung wird das 350-MB-Limit früher erreicht als bei ChatGPT | bestehende Limits gelten, Meldung nennt das Limit; Größe je Gespräch in der Vorschau zeigen; ggf. SCALE-001 |
| Importierte URLs (Zitate, Favicons) könnten beim Anzeigen geladen werden | E12; DOM-Test ohne `img`/`src` aus Importdaten |
| Messenger-Exporte (z. B. Instagram-DMs) sehen chatähnlich aus | Bewusst nicht im Umfang: keine KI-Chats, enthalten Nachrichten Dritter (siehe PROV-003) |
| Über-Engineering für hypothetische Anbieter | Nur Claude konkret planen; weitere Adapter erst bei echtem Bedarf (PROV-003) |

## Verifikationsgrenzen

Synthetische und CI-Ergebnisse sind kein Test mit dem privaten Originalexport.
Aktuellen konkreten Test-/CI-Nachweis und Einschränkungen in aktuellerStand.md lesen.

- **UX-002 (Feature-Branch, noch nicht gemergt):** kleine, einklappbare
  Import-Hilfe für ChatGPT, Claude und Extractor in der bestehenden UI.
  Keine Änderung an Erkennung oder Datenbank.
