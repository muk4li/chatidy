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
- Priorität: P1; Status: Teilweise implementiert (Manifest-Abgleich der Segmente).
- Komponenten: Manifest-/Metadata-Adapter. Abhängigkeiten: EXP-001.
- [ ] Nur mit dokumentiertem Schema zukünftige Metadaten interpretieren.
- [x] 2026-11-20 (Auftrag des Nutzers): Wurzel-`export_manifest.json` mit erkanntem Schema
  (`version`, genau ein `logical_files`-Eintrag nur mit Konversationsdateien, passender `shard_count`)
  wird gegen die gefundenen Segmente abgeglichen; Abweichung = Abbruch „Export unvollständig“.
  Unbekannte/fehlerhafte/mehrdeutige Manifeste bleiben Inventar mit Warnung. Grenze aus EXP-001 damit
  für aktuelle ChatGPT-Exporte geschlossen. Offen: Prüfung mit echtem Export durch den Nutzer.
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
- Priorität: P2; Status: Implementiert (002a Import, 002b UI); Prüfung mit echtem Export durch Nutzer offen. Abhängigkeiten: PROV-001.
- Komponenten: Claude-Adapter, Archivinventar, Themencluster-Stoppwörter.
- [x] Vorab: Strukturbefund aus echtem Export (nur Schlüssel/Typen), siehe ROADMAP Phase 6.
- [x] 002a: Zweige über `parent_message_uuid`, aktueller Zweig = spätestes Blatt, übrige in Metadaten (E10).
- [x] 002a: Lese-/Suchtext nur aus `text`-Blöcken und `extracted_content` (E11, Importteil).
- [x] 002b: Tool-/Thinking-Blöcke als einklappbare Kurzzeile (Werkzeugnamen, Ergebnis-/Fehlerzahl, nicht leerer
  Denktext); reine Tool-Nachrichten als Block statt Platzhalter. Keine Tool-Ein-/Ausgaben oder URLs in der Kurzzeile (E11/E12).
- [x] 002b: Anbieter-Badge pro Chat (ab zwei Anbietern), Anbieter in der Kopfzeile, Anbieterfilter in der
  Navigation; intelligente Ordner speichern den Anbieterfilter.
- [ ] Nutzer: echten `conversations-000.zip` lokal importieren und Stichproben prüfen.
- [x] 002a: `chat_messages` → normalisiertes Modell; `human`→`user`; Text aus Textblöcken, Fallback `text` (E5).
- [x] 002a: IDs `claude:<uuid>` (E4); Rohdaten inkl. Thinking/Tools/`extracted_content` in `metadata`.
- [x] 002a: Nicht-Gesprächs-ZIPs/Manifest mit Kategoriehinweis abgelehnt, nicht persistiert (E9/E13).
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
- [x] Nachtrag: Nachrichtenzahlen (Liste, Kopfzeile, Verlauf, Statistik) zählen nur lesbare Nachrichten;
  Denk-/Werkzeugknoten (`[Nicht-textueller Inhalt]`) nicht mehr. Gespeicherte Daten unverändert.
- Grenze: der Platzhalter bleibt im Suchindex (→ SEARCH-001).
- Akzeptanz: bestehende Bibliotheken ohne Neuimport korrekt dargestellt (Darstellung aus Metadaten), kein Datenverlust.
- Tests: synthetische Knoten je `content_type`, Reimport-Identität unverändert, DOM-Test.

## SEARCH-001 – Platzhalter nicht in der Volltextsuche
- Priorität: P2; Status: Implementiert. Abhängigkeiten: CGPT-001.
- [x] `[Nicht-textueller Inhalt]` wird beim Import nicht indiziert; Migration 6 baut den Index einmalig neu auf.
- Akzeptanz: Gespräche/Nachrichten/Organisation unverändert, Titel weiter durchsuchbar, Rollback bei Fehler.
- Tests: neue Importe, Migration 5→6 mit Altindex, fehlgeschlagene Migration, Konstante = SQL-Marker.
- Grenze: Regeln mit Feld „Inhalt“ prüfen weiterhin den gespeicherten Text inkl. Platzhalter.

## PROV-004 – Codex-Aufgaben aus `codex.json`
- Priorität: P3; Status: Implementiert (Auftrag 2026-11-20); Prüfung mit echtem Export durch Nutzer offen.
- Komponenten: eigener Adapter im Sinne von E1 (Anbieter `chatgpt`, Quelle `codex`). Abhängigkeiten: PROV-001.
- [x] `turns[]` als Gesprächsverlauf (Listenreihenfolge, keine Zeitstempel im Export); Text aus
  Nachrichtenteilen plus „[Pull Request] Titel“; Repo-Snapshots, Diffs, Zitate nur in Metadaten, nicht in der Suche.
- [x] `codex.json` im selben Ordner wie die Konversationsdateien wird mitimportiert, wenn jeder Eintrag
  erkannt wird; sonst Warnung und kein Import. IDs `codex:<id>`; Kopfzeile „ChatGPT · Codex“.
- Grenze: ohne Zeitstempel stehen Codex-Chats in der Datumssortierung am Ende.
- Akzeptanz: keine Vermischung mit normalen Chats ohne sichtbare Kennzeichnung.
- Tests: synthetische Codex-Fixtures, Reimport.

## PROV-003 – Weitere Anbieter und lokale Oberflächen (Backlog)
- Priorität: P3; Status: Offen – nur bei echtem Bedarf.
- Komponenten: zusätzliche Adapter (z. B. Open WebUI, weitere Cloud-Anbieter). Abhängigkeiten: PROV-001.
- [ ] Je Anbieter: Exportstruktur dokumentieren, Adapter + synthetische Fixtures, keine API-/DB-Zugriffe (E7).
- Nicht im Umfang: Messenger-Exporte (z. B. Instagram-DMs) – keine KI-Chats, enthalten Daten Dritter.
- Akzeptanz: Kernmodule bleiben unverändert; neuer Anbieter = neuer Adapter + Tests.
- Tests: pro Adapter; Formatänderungen bekannter Anbieter als neue Fixture-Variante.

## AUTH-002 – Additive Benutzeridentitätsbasis (Schema 7)
- Priorität: P1; Status: Implementierung auf Draft-Branch, CI/Review ausstehend.
- [x] `users`-Schema mit internem Schlüssel, eindeutiger OIDC-Issuer/Subjekt-
  Kombination, Anzeigeattributen, Rolle und Sperrstatus.
- [x] Keine Kontenanlage, automatische Eigentümerzuordnung, API-/Login-Änderung.
- [x] Synthetische Migration-, Reopen-, Eindeutigkeits- und Rollbacktests.
- [ ] Nach RepoPilot-Modellfreigabe Besitzmodell, Datenzugriffe und Jobs isolieren.
- Akzeptanz: alte Daten bleiben unverändert, keinerlei Remote-Freigabe.

## AUTH-003 – Explizite schreibfreie Identitätsauflösung
- Priorität: P1; Status: Implementiert auf gestapeltem Draft-Branch, CI offen.
- [x] Exakter Lookup für aktiv eingeschriebene OIDC-Identitäten (`iss` + `sub`).
- [x] Unbekannte/gesperrte Konten und E-Mail-Matches werden abgewiesen;
  insbesondere keine automatische Erstbenutzer- oder Eigentümeranlage.
- [x] Rein synthetische Isolationstests.
- [ ] Authentifizierte HTTP-Session und Benutzerisolierung sämtlicher Daten
  bleiben getrennte Folgepakete. Ohne OIDC-Verifikation ist Lookup kein Login.

## AUTH-004 – Manuelle lokale Einschreibung verifizierter OIDC-Identitäten
- Priorität: P1; Status: Gestapelter Draft-PR, CI/Review offen.
- [x] Bestätigte CLI-Einschreibung eines exakten HTTPS-Issuer/Subjekts,
  Rollen owner/member; kein öffentlicher Endpoint, keine automatische Anmeldung.
- [x] Zweites Eigentümerkonto nicht automatisch gestattet.
- [x] Keine Übernahme bestehender Chats; synthetische Regressionstests.
- [ ] Vor praktischem Einsatz IdP und Benutzerisolation vollständig prüfen.

## AUTH-008 – Einmalige OIDC-States und serverseitige Sitzungen
- Priorität: P1; Status: Gestapelter Draft-PR, CI offen.
- [x] Schema 8 für zeitlich begrenzte, browsergebundene OIDC-Challenges
  und nur als Hash gespeicherte Session-IDs.
- [x] Einmalige atomare State-Verwendung; Sperrstatus und Session-Widerruf.
- [x] Synthetische Replay-/Browserbindung-/Expiry-/Kontosperrtests.
- [ ] Echten OIDC-Code-Exchange, Cookie-Flags, CSRF-/API-Gate und vollständige
  Benutzer-/Job-Isolation in Folge-PRs integrieren; keine Live-Freigabe.

## AUTH-009 – HTTP-Sitzungsgate (Draft)
- Priorität: P1; Status: Integrations-PR offen, CI/Review notwendig.
- [x] Expliziter Auth-Testmodus: private `/app`, App-Assets und `/api/*`.
- [x] Session aus serverseitigem Speicher, danach kontospezifische DB/Jobs.
- [x] Synthetische Negativtests für fehlende/gesperrte Session, POST-Origin
  und zwei Konten mit derselben ursprünglichen Konversations-ID.
- [ ] Live-OIDC-Callback, Logout, Cookie-/CSRF-Sicherheitsreview und native
  Windows-/Job-Tests vor öffentlicher Exposition.

## AUTH-010 – Verifizierbarer Code-Exchange (Draft)
- [x] Explizite IdP-Endpunkte, HTTPS und Redirect-Verbot für OIDC-
  Token und JWKS, Größenlimits, PKCE-Verifier.
- [x] Synthetische Positiv-/Negativtests ohne Live-Zugang.
- [ ] HTTP-Login, Callback und sichere Sitzungs-Cookies integrieren;
  IdP-Livetest/Security-Review vor Deploy.

## AUTH-011 – OIDC-Login, Callback, Logout (gestapelter Draft)
- [x] PKCE, browsergebundener Einmal-State, sichere Sitzungs-Cookies,
  explizit freigeschaltete User, HTTP-Logout und synthetische Negativtests.
- [ ] Live-Provider-/Proxy-Sicherheitsprüfung, Benutzer-/Job-Isolation und
  Bestandsmigration samt Backup/Restore vor öffentlicher Freigabe.

## AUTH-012 – Explizite Offline-Bestandsmigration (Draft)
- [x] Nur aktives Owner-Konto und doppelte ausdrückliche Bestätigung.
- [x] Offline-Backup vor einer Datenänderung; keine Überschreibung des Ziels.
- [x] Copy von Chat/Organisation und FTS-Rebuild, ohne OIDC-Sessiondaten.
- [x] Synthetische Regression für Daten-/Tag-Erhalt, idempotente Verweigerung.
- [ ] Manuelle reale Bibliotheks-/Backup-Restore-Prüfung und Jobmigration offen.

## AUTH-013 – Abmelden und Kontostatus in der App (Draft)
- [x] Authentifizierter `/api/session`-Status, ohne OIDC-Kennung/Token.
- [x] UI-Abmelden per POST und Redirect zur öffentlichen Startseite.
- [x] Kontoaktionen im lokalen Standardmodus ausgeblendet.
- [x] Synthetische HTTP-Tests für Kontoanzeige und Widerruf.
- [ ] Browser- und authentik-Liveprüfung vor Remote-Freigabe.

## AUTH-014 – Negative HTTP-Mehrbenutzertests (Draft)
- [x] Serverseitige Isolationsprüfung für Detail, Suche, Ordner,
  Export, Review sowie anonyme API-Requests mit synthetischen Konten.
- [x] Fremder Gesprächs-Review erhält 404 und verändert keine Daten.
- [ ] Native Provider-/Proxy-/Backuptests und Migration bleiben Release-Gates.
