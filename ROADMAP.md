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
- **Offen:** validierte Manifest-Gesamtzahlen, komplexe Mehrversions-/Zweigrekonstruktion
  und überlappende Gesprächs-Snapshots. Fehlende letzte Segmente sind ohne
  vertrauenswürdige Gesamtzahl nicht nachweisbar. Details: TASKS.md.

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

Status: **Offen – nur geplant, kein Umsetzungsauftrag.** Backlog: PROV-001 bis PROV-003 in TASKS.md.

Ziel: Neben ChatGPT auch Claude-Exporte (claude.ai, Settings › Privacy › Export data)
verlustfrei importieren; jeder Chat trägt sichtbar und filterbar seinen Anbieter.
Die Architektur soll außerdem auf Formatänderungen der Anbieter, weitere Cloud-Anbieter
und lokale Oberflächen (z. B. Open WebUI) reagieren können, falls Bedarf entsteht –
ohne dafür jetzt schon Adapter zu bauen.

Bekannter Claude-Export (öffentliche Beschreibungen, nicht mit echtem Export verifiziert):
ZIP mit `conversations.json`, `projects.json`, `memories.json`, `users.json`; große
Konten erhalten ein Manifest mit mehreren Batch-ZIPs. Gespräch: `uuid`, `name`,
`summary`, ISO-Zeitstempel, `chat_messages[]` mit `uuid`, `sender` (`human`/`assistant`),
`text`, `content[]`-Blöcken (u. a. `text`, `thinking`, `tool_use`, `tool_result`),
`attachments[]` (mit `extracted_content`) und `files[]` (nur Namen).

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

### Risiken und Gegenmaßnahmen

| Risiko | Gegenmaßnahme |
|---|---|
| Anbieterformate sind undokumentiert und ändern sich (z. B. `text` vs. `content[]`, Schlüsselvarianten) | E5/E6; Fixtures je Variante; Strukturabgleich mit echtem Export nur über Schlüssellisten, nie Inhalte |
| Datenverlust bei Thinking/Tools/Artifacts/Anhängen | Rohdaten in `metadata`, Platzhalter statt Verwerfen; Binäranhänge sind im Export nicht enthalten (Exportgrenze, dokumentieren) |
| Fehlerkennung eines Formats (Claude-Variante als Extractor geparst) | E2: eindeutige Erkennung, Mehrdeutigkeit = Abbruch |
| ID-Kollision zwischen Anbietern | E4 |
| Zweige im Claude-Export: vermutlich linear, nicht verifiziert | Vor Umsetzung echten Export auf Elternverweise prüfen; falls vorhanden, Graphlogik nutzen |
| Große Claude-Konten: Manifest mit mehreren Batch-ZIPs | Zunächst jedes ZIP einzeln importieren; erst nach Prüfung als unterstützt bezeichnen (vgl. SCALE-001/META-001) |
| Sensible Zusatzdaten (Memories, Konto) | E9; nicht persistieren, in Vorschau kennzeichnen |
| Große `extracted_content`-Texte belasten Speicher/Limits | bestehende Limits gelten; ggf. SCALE-001 |
| Über-Engineering für hypothetische Anbieter | Nur Claude konkret planen; weitere Adapter erst bei echtem Bedarf (PROV-003) |

## Verifikationsgrenzen

Synthetische und CI-Ergebnisse sind kein Test mit dem privaten Originalexport.
Aktuellen konkreten Test-/CI-Nachweis und Einschränkungen in aktuellerStand.md lesen.
