# Operatives Backlog

Aktueller Fokus: Nutzbarkeit und Verständlichkeit. Weitere Import-/Storage-Härtung
und neue Plattformfälle nur mit ausdrücklichem Nutzerauftrag; bestehende Bugs beheben.

## REAL-001 – Manueller Echttest durch Nutzer
- Priorität: P0; Status: Offen – nur lokal durch den Nutzer ausführbar.
- Komponenten: Windows-11-Bedienablauf; Abhängigkeiten: EXP-001, DATA-001, IMP-001.
- [ ] Analyse, Vorschau, bestätigten Import und Stichproben mit echtem Export prüfen.
- [ ] Identischen Reimport ohne Duplikate und mit erhaltenen Zuordnungen prüfen.
- Akzeptanz: Nutzer bestätigt Ergebnis anhand der [Checkliste](docs/manueller-echttest.md);
  ausschließlich geschwärzte technische Angaben zurückmelden, keine privaten Daten.
- Tests: manueller lokaler Windows-11-Durchlauf; kein Ersatz durch synthetische CI.

## FOCUS-001 – Nutzbarkeit und Dokumentation aufräumen
- Priorität: P0; Status: Implementiert; Verifikation siehe aktuellerStand.md.
- Komponenten: DB-Startwerte, Server-Startkonfiguration, Dokumentation.
- [x] Acht passende Kategorien nur für neue Datenbanken; Bestand unverändert.
- [x] Projektbezogener Standardpfad, CHATIDY_DB und explizite Pfade vorrangig.
- [x] Kurze README, Importdetails, ausgelagerte Historie und Echttest-Checkliste.
- Akzeptanz: keine Schema-/Import-/Storage-Änderungen oder neuen Abhängigkeiten.
- Tests: neue/bestehende/leere Ordnerbestände, Pfadwahl und Serverstart; vollständige Suite.

## EXP-001 – Offizielle Segmentarchive erkennen
- Priorität: P0; Status: Abgeschlossen – implementiert und unter Linux/Windows getestet (CI 43561857600).
- Komponenten: Importer, Archivinventar, Jobvorschau. Abhängigkeiten: keine.
- [x] conversations.json und numerisch sortierte conversations-NNN.json auswählen.
- [x] Fehlende/doppelte/beschädigte erforderliche Segmente kontrolliert ablehnen.
- [x] Metadaten, DAT, HTML, Manifeste und unbekannte Extras separat inventarisieren.
- [x] Zusatzdateien weder ausführen noch ungeprüft als Chats parsen.
- Akzeptanz: ein gemeinsamer Batch für 000–007 unabhängig von ZIP-Reihenfolge.
  Interne Lücken werden erkannt; fehlende Endsegmente ohne validiertes Manifest
  bleiben eine ausdrücklich dokumentierte Grenze.
- Tests: klassische/segmentierte/Extractor-Archive, Extras, Lücken, CRC/JSON,
  Größenlimits, Mehrdeutigkeit und doppelte Konversations-IDs.

## DATA-001 – Nachrichtenidentität pro Gespräch
- Priorität: P0; Status: Abgeschlossen – implementiert und unter Linux/Windows getestet (CI 43561857600).
- Komponenten: SQLite, Migrationen, upsert, Details/Export, FTS5. Abhängigkeiten: keine.
- [x] Globale Kollisionsursache synthetisch reproduzieren.
- [x] Bestehende IDs/Metadaten/Reihenfolge verlustfrei per Migration erhalten.
- [x] Gleiche ID in verschiedenen Chats erlauben, doppelte IDs im selben Chat ablehnen.
- Akzeptanz: kein fremder Chat wird überschrieben; Einzeldatei danach Gesamt-ZIP ist idempotent.
- Tests: Migration von Schema 3, Rollback, FKs, FTS, Tags/Review/Ordner und Reimport.

## IMP-001 – Vorschau, Bestätigung und Batch-Konflikte
- Priorität: P0; Status: Abgeschlossen – implementiert, HTTP-/Browsertest und Linux-/Windows-CI erfolgreich (43561857600).
- Komponenten: Jobs, HTTP, UI. Abhängigkeiten: EXP-001, DATA-001.
- [x] Analyse/Staging von Änderungen an der Hauptbibliothek trennen.
- [x] Inventar, Gesprächszahl, Konfliktklassen, Warnungen und grobe Speicherprognose zeigen.
- [x] Eine Bestätigung pro Batch; keine globale Fehler-ignorieren-Option.
- [x] Identische/neuere vollständige Chats sicher behandeln; ältere oder abweichende
  Chats nur nach eindeutiger klassenbezogener Wahl unverändert lassen oder abbrechen.
- Akzeptanz: ohne Bestätigung kein Chatimport; atomarer Batch mit Wiederaufnahme.
- Tests: HTTP/Browser, Vorschau ohne Bibliotheksänderung, Konfliktentscheidung,
  Abbruch/Wiederaufnahme, parallele Bibliotheksänderung, Windows/Linux-CI.

## META-001 – Noch unbekannte offizielle Zusatzschemas
- Priorität: P1; Status: Offen.
- Komponenten: Manifest-/Metadata-Adapter. Abhängigkeiten: EXP-001.
- [ ] Nur mit dokumentiertem Schema zukünftige Metadaten interpretieren.
- Befund 2026-11-20: Wurzel-`export_manifest.json` mit `logical_files.<name>.shard_count`/`files[]`
  würde den Nachweis fehlender Endsegmente erlauben (Grenze aus EXP-001). Umsetzung nur auf Auftrag.
- [ ] Keine privaten Exporte in Cloud/Repo anfordern; synthetische Beispiele nutzen.
- Akzeptanz: Schema-Validierung vor Nutzung; sensible Konto-/Werbedaten nicht unnötig persistieren.
- Tests: nicht vertrauenswürdige, fehlerhafte und zukünftige Manifestversionen.

## SCALE-001 – Größere Exporte und Speicherbudgets
- Priorität: P1; Status: Teilweise implementiert.
- Komponenten: Streaming, Jobs, Limits. Abhängigkeiten: IMP-001.
- [x] Streaming von JSON-Arrays und persistente Checkpoints.
- [ ] Konfigurierbare, getestete Speicherbudgets; Begrenzung großer Einzelobjekte.
- Akzeptanz: keine stillen Limit-Erhöhungen, keine unkontrollierte Extraktion.
- Tests: synthetische große Archive, BOM/Chunks, Abbruch und Speicherverbrauch.

## UX-001 – Organisation erweitern
- Priorität: P2; Status: Teilweise implementiert.
- Komponenten: UI, Suche. Abhängigkeiten: stabile P0-Importbasis.
- [x] Ordner, Tags, Review, Regeln, Mehrfachauswahl und zusätzliche Drag-Zuordnung.
- [x] UI-Layout: Navigation | Chat-Liste | Leseansicht, Import auf eigener Seite,
  einklappbarer Ordnerbaum, Tag-Liste als Filter, Kennzahlen in der Navigation.
- [x] Codeblöcke (```) im Verlauf abgesetzt, ausschließlich als Text (kein HTML).
- [x] Einklappbare Navigationsbereiche, verstellbare Breite von Navigation und
  Leseansicht, Anzahl für Archiviert/Ohne Gruppe/Themencluster (`/api/stats` additiv).
- [x] Größere Navigationssymbole; Auf-/Zuklapp-Pfeile als gleich große CSS-Dreiecke (▶/▼).
- [ ] Favoriten, fortgeschrittene Filter, weitere Markdown-Darstellung.
- Akzeptanz: Rückwärtskompatibilität, Tastatur-/Mobile-Bedienung und kein XSS.
- Tests: API-, DOM- und echter Browsertest.

## KNOW-001 – Lokales Wissen und Integrationen
- Priorität: P3; Status: Offen.
- Komponenten: lokale Intelligenz, Exporte, optionale Adapter. Abhängigkeiten: P0/P1.
- [ ] Semantische Suche, Medienbibliothek, Wissensgraph und optionale Projektintegrationen.
- Akzeptanz: lokale Verarbeitung, erklärbare Vorschläge, keine Pflicht-Cloud.
- Tests: pro abgeschlossener Funktion; bislang keine Implementierungsbehauptung.

## AUTO-001 – Gruppenvorschläge für viele Chats (Backlog, Idee des Nutzers)
- Priorität: P3; Status: Offen – nur festgehalten, kein Umsetzungsauftrag.
- Anlass: ca. 700–800 Chats; Ollama-Vorschläge pro Chat (Titel + 6000 Zeichen) sind
  dafür zu langsam und müssen einzeln ausgelöst werden; keine große GPU vorhanden.
- Ansatz (gestuft, alles lokal über Ollama auf 127.0.0.1, keine neuen Python-Pakete):
  1. Ohne Neuentwicklung: Regeln (Titel/Inhalt/Projekt) und ChatGPT-Projekte nutzen.
  2. Embeddings aus Titel + erster Nutzerfrage (z. B. kleines Embedding-Modell), einmalig
     berechnen und lokal speichern; Nutzer ordnet wenige Beispiele je Gruppe zu, übrige
     Chats erhalten Ähnlichkeitsvorschläge mit Sicherheitswert.
  3. Optional nur unsichere Fälle per kleinem LLM (Titel + erste Frage + Gruppenliste) klassifizieren.
- Keine Volltext-Zusammenfassungen zum Einsortieren (zu teuer, kaum Mehrwert).
- Vorschläge landen im Posteingang; Übernahme nur nach Bestätigung, Sammelbestätigung je
  Gruppe mit Rückfrage. Hintergrundjob mit Fortschritt und gemessener Dauer.
- Akzeptanz: keine autonome Zuordnung, erklärbarer Vorschlag (ähnlichste Beispiele),
  bestehende Zuordnungen bleiben unverändert, Laufzeit auf Durchschnitts-Hardware gemessen.
- Tests: synthetische Embeddings/Mock-Ollama, Schwellenwerte, Bestätigung, Reimport-Stabilität.
- Abhängigkeiten: KNOW-001 (lokale Embeddings), Phase 3 der ROADMAP.

## DATA-002 – Explizite Versions-/Zweig- und Duplikatrekonstruktion
- Priorität: P1; Status: Offen.
- Komponenten: Konfliktmodell, Importer, Versionsdaten. Abhängigkeiten: DATA-001, IMP-001.
- [ ] Mehrere Snapshots derselben Gesprächs-ID im Batch nach definierter Regel behandeln.
- [ ] Legacy-Fallback-IDs und alternative Zweige ohne heuristisches Überschreiben rekonstruieren.
- Akzeptanz: keine automatische unklare Zusammenführung. Bis dahin doppelte
  Gesprächs-IDs ablehnen, Zweige ggf. vollständig unverändert lassen.
- Tests: überlappende Segment-Snapshots, widersprüchliche Inhalte, Metadaten und Rollback.

## DELIV-001 – PR und Merge der Exportkorrekturen
- Priorität: P1; Status: Abgeschlossen – PR #6 auf main gemergt (Merge-Commit `81665a8`), am 2026-11-14 nachgeprüft.
- Komponenten: GitHub/CI. Abhängigkeiten: EXP-001, DATA-001, IMP-001.
- [x] Feature-Branch und sechs erfolgreiche CI-Jobs gegen die Implementierung.
- [x] Tatsächlich erstellten PR und ggf. Merge bestätigen; keine Erfolgsaussage ohne Nachweis.
- Akzeptanz: PR gegen aktuellen main, grüne CI, geklärte Risiken, kein Force-Push.
- Tests: Commit-/Branch-Zuordnung und CI-Matrix prüfen. Manueller PR-Link:
  https://github.com/muk4li/chatidy/pull/new/feature/segmented-export-preview

## PROV-001 – Anbieterneutrale Importbasis
- Priorität: P2; Status: Implementiert (Backend); UI-Teil nach PROV-002 verschoben. Verifikation: aktuellerStand.md.
- Komponenten: Importer, Archivinventar, Migrationen, API. Abhängigkeiten: EXP-001, DATA-001, IMP-001.
- [x] Bestehende Formate (ChatGPT offiziell, Extractor) als Adapter mit ausdrücklicher Erkennung (E1/E2);
  gilt auch für die Strukturerkennung in ZIPs ohne offizielle Dateinamen.
- [x] Migration 5: `conversations.provider`, Bestand `chatgpt` (E3). Format steht weiter in `metadata.source`.
- [x] API: `/api/chats?provider=`, `/api/stats.providers` (additiv); Anbieter Teil der Reimport-Identität.
- [ ] → PROV-002: Anbieter-Badge pro Chat und Anbieterfilter in der Navigation (erst mit zweitem Anbieter sinnvoll).
- Akzeptanz: Bestandsdaten, IDs, Zuordnungen und Reimport-Verhalten unverändert; mehrdeutige Formate brechen ab.
- Tests: Migration von Schema 4, Erkennung/Mehrdeutigkeit, Reimport, API/DOM/Browser.
  Pflicht-Regressionstest: Objekt mit `messages` ohne Extractor-Merkmale (z. B. `sender` statt `role`)
  wird nicht als Extractor gelesen – weder als Einzel-JSON noch über die ZIP-Strukturerkennung.

## PROV-002 – Claude-Export importieren
- Priorität: P2; Status: Offen – geplant, kein Umsetzungsauftrag. Abhängigkeiten: PROV-001.
- Komponenten: Claude-Adapter, Archivinventar, Themencluster-Stoppwörter.
- [x] Vorab: Strukturbefund aus echtem Export (nur Schlüssel/Typen), siehe ROADMAP Phase 6.
- [ ] Zweige über `parent_message_uuid`, aktueller Zweig = spätestes Blatt, übrige Zweige in Metadaten (E10).
- [ ] Lese-/Suchtext nur aus `text`-Blöcken und `extracted_content`; Tool-/Thinking-Blöcke als Kurzzeile (E11).
- [ ] Keine URL aus Importdaten laden (E12); Nicht-Gesprächs-ZIPs mit klarer Meldung ablehnen (E13).
- [ ] Anbieter-Badge pro Chat und Anbieterfilter in der Navigation (aus PROV-001 übernommen).
- [ ] `chat_messages` → normalisiertes Modell; `human`→`user`; Text aus Textblöcken, Fallback `text` (E5).
- [ ] IDs `claude:<uuid>` (E4); Rohdaten inkl. Thinking/Tools/`extracted_content` in `metadata`.
- [ ] `projects.json`, `memories.json`, `users.json` als Metadaten inventarisieren, sensible markieren (E9).
- Akzeptanz: kein stiller Inhaltsverlust; gemischte ChatGPT-/Claude-Bibliothek; idempotenter Reimport.
- Tests: synthetische Claude-Fixtures (nur `text`, nur `content[]`, unbekannte Blocktypen, Anhänge,
  Variante mit `messages` statt `chat_messages` – auch mit zusätzlichem `id`: wird als Claude erkannt
  oder kontrolliert abgelehnt, nie als Extractor gelesen; verzweigte/unsortierte/zyklische Verläufe;
  leeres Gespräch, leerer Titel; Konto-/Memory-/Artifact-/Routinen-ZIP einzeln hochgeladen),
  gemischter Bestand, Reimport/Konflikte. Grenze: Batch-ZIPs großer Konten ungeprüft.

## CGPT-001 – Denk- und Reasoning-Nachrichten im ChatGPT-Import lesbar machen
- Priorität: P2; Status: Abgeschlossen – PR #17 gemergt; Sichtprüfung mit echtem Export durch Nutzer bestanden (2026-11-20).
- Komponenten: Leseansicht (`web/reading.js`, `web/app.js`). Abhängigkeiten: keine; passt zu E11.
- [x] `thoughts`/`reasoning_recap` als eingeklappter Block („💭 Nachgedacht für …“ mit Schritten) statt
  „[Nicht-textueller Inhalt]“; aufeinanderfolgende `thoughts` + `reasoning_recap` werden ein Block.
- [x] Nur Darstellung: gespeicherter Inhalt, Volltextsuche, Themencluster und Reimport-Identität unverändert;
  Rohdaten weiter unter „Metadaten“. Kein Neuimport nötig.
- Grenze: Kopfzeile zählt weiter gespeicherte Nachrichten (inkl. Denkknoten); der Platzhalter bleibt im
  Suchindex (eine Bereinigung bräuchte Importer-/Indexänderung und wäre ein eigener Auftrag).
- Akzeptanz: bestehende Bibliotheken ohne Neuimport korrekt dargestellt (Darstellung aus Metadaten), kein Datenverlust.
- Tests: synthetische Knoten je `content_type`, Reimport-Identität unverändert, DOM-Test.

## PROV-004 – Codex-Aufgaben aus `codex.json` (Backlog)
- Priorität: P3; Status: Offen – nur festgehalten.
- Komponenten: eigener Adapter im Sinne von E1 (Anbieter `chatgpt`, Quelle `codex`). Abhängigkeiten: PROV-001.
- [ ] `turns[]` als Gesprächsverlauf; PR-Titel/Diff-Kennzahlen als Metadaten; Dateiausschnitte nicht in die Suche.
- Akzeptanz: keine Vermischung mit normalen Chats ohne sichtbare Kennzeichnung.
- Tests: synthetische Codex-Fixtures, Reimport.

## PROV-003 – Weitere Anbieter und lokale Oberflächen (Backlog)
- Priorität: P3; Status: Offen – nur bei echtem Bedarf.
- Komponenten: zusätzliche Adapter (z. B. Open WebUI, weitere Cloud-Anbieter). Abhängigkeiten: PROV-001.
- [ ] Je Anbieter: Exportstruktur dokumentieren, Adapter + synthetische Fixtures, keine API-/DB-Zugriffe (E7).
- Nicht im Umfang: Messenger-Exporte (z. B. Instagram-DMs) – keine KI-Chats, enthalten Daten Dritter.
- Akzeptanz: Kernmodule bleiben unverändert; neuer Anbieter = neuer Adapter + Tests.
- Tests: pro Adapter; Formatänderungen bekannter Anbieter als neue Fixture-Variante.
