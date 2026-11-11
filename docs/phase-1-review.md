# Phase 1: Bestandsaufnahme und erster Integritätsschritt

Geprüfter Chatidy-Ausgangspunkt: `697cb02` (main, 2026-11-11).

## Architektur und bestehende Funktionen

- Python-Standardbibliothek, SQLite/FTS5, lokaler ThreadingHTTPServer, statische Weboberfläche.
- Import (`importer.py`), Speicherung (`db.py`), Themen (`topics.py`) und Darstellung sind getrennt.
- Vorhanden: ZIP/JSON, aktive Graphzweige, Extractor-JSON-Adapter, Suche, Ordner mit Mehrfachzuordnung, Regeln, Review und explizite lokale Ollama-Vorschläge.
- HTTP bleibt an Loopback gebunden; Host-/Origin-Prüfung und textContent für importierte Inhalte sind vorhanden.
- CI definiert unittest unter Python 3.11 und 3.13. Lokal wurden Python 3.12 und 16 erfolgreiche Tests geprüft; aktuelle Actions-Ergebnisse, Issues und PRs waren wegen GitHub-API `Forbidden` nicht abrufbar.

## Behobene Datenverlustgefahr

`messages.id` ist im vorhandenen Schema global eindeutig. `INSERT OR REPLACE` konnte bei einer ID-Kollision eine Nachricht eines anderen Chats löschen und dessen FTS-Index inkonsistent zurücklassen.

Der Import lehnt doppelte IDs innerhalb eines Chats und Kollisionen mit anderen Chats jetzt mit ValueError ab. Die vorhandene Transaktion rollt den gesamten Batch zurück, einschließlich Gesprächsänderungen, Regeln und Suchindex. Ein normaler Reimport desselben Chats funktioniert weiterhin. Das Schema bleibt unverändert; eine Migration ist für diese Korrektur nicht erforderlich. Bereits früher verlorene Inhalte werden dadurch nicht rekonstruiert.

Validierung mit synthetischen Daten: bestehende Tests, kollidierende und doppelte IDs, Rollback bei unterbrochenem Iterator und SQL-Fehler, Datenbank-Wiederöffnung/Integritätsprüfung, 1.500 Chats mit wiederholtem Import. Zusätzlich HTTP-Smoke-Test: erster Import erfolgreich, zweiter kollidierender Import HTTP 400, ursprüngliche Nachricht über FTS weiter auffindbar.

## Datenschutzprüfung

Die verfolgten Dateien enthalten Quellcode, Dokumentation und synthetische Tests; keine Exportarchive oder Datenbankdateien. Die bestehenden Ignore-Regeln und Datenschutztests schützen übliche lokale Datenpfade. Kein allgemeiner Schutz vor beliebig benannten privaten Dateien oder `git add -f`; vor dem Commit ist weiterhin Inhaltsprüfung erforderlich. Dieser Schritt importiert ausschließlich synthetische Daten. Keine umfassende historische Secret-Prüfung erfolgt.

## Extractor und nächste Schritte

`muk4li/chatgpt-conversation-extractor` wurde separat unter /tmp untersucht, Stand `33ad32f18ed9d08b575106b08da8ce5263e783dd`. Seine `generate_json_data`-Ausgabe mit id, created, updated, project_id und messages passt zum vorhandenen unabhängigen JSON-Adapter. Keine neue Laufzeitabhängigkeit; keine vollständige End-to-End-Prüfung des externen Tools in diesem Schritt.

Priorisierte Restarbeiten:

1. Reimport-Schutz ist im nachfolgenden Schritt implementiert (siehe unten). Versionshistorie, explizit bestätigte Zweigwechsel und verlustfreie Metadatenaktualisierung bleiben offen.
2. Ohne gültiges current_node werden derzeit alle Graphnachrichten nach Zeit sortiert; alternative Zweige können vermischt werden. Fehlerhafte Graphverweise und Metadaten brauchen weitere Tests.
3. ZIP-Bomb-/Größenprüfungen sind vorhanden, aber Sicherheitsregressionen und Behandlung verschlüsselter/defekter Mitglieder sollten ausgebaut werden. Mehrdatei-ZIPs überspringen derzeit teilweise ungültiges JSON.
4. Upload und JSON-Verarbeitung erfolgen im Speicher; Größenlimits sind kein Streaming. Große echte Exporte wurden nicht getestet.
5. Versionierte Migrationen einführen, bevor Metadaten, Anhänge oder zusammengesetzte Nachrichten-IDs das Schema erweitern.
6. Extractor-Metadaten, Zitate und Multimodalität schrittweise verlustärmer übernehmen; derzeit werden Anhänge überwiegend als Platzhalter dargestellt. Markdown wird sicher als Text gezeigt.

Phase 1 insgesamt ist mit diesem ersten abgegrenzten Schritt noch nicht abgeschlossen.

## Folgeschritt: konservativer Reimport-Schutz

Ausgangspunkt: `916ef99` auf main. Implementiert auf einem separaten Branch;
der Merge bleibt dem Nutzer überlassen.

- Bereits gespeicherte Nachrichten-IDs müssen im Reimport vollständig enthalten sein.
  Sonst wird die gesamte Transaktion abgebrochen. Das gilt auch bei einer gleich
  großen Nachrichtenzahl mit anderen IDs und bei neueren Änderungszeitpunkten.
- Wenn ein Änderungszeitpunkt gespeichert ist, sind ältere Exporte und Exporte
  ohne Änderungszeitpunkt gesperrt. Angegebene Zeitpunkte müssen endliche
  numerische Unix-Zeitstempel sein (Extractor-ISO-Daten normalisiert der Adapter).
- Ein Schreib-Lock wird vor der ersten Datenbankabfrage reserviert, damit sich
  der zu prüfende Bestand nicht zwischen Prüfung und Aktualisierung ändern kann.
- Identische Importe und vollständige neuere Inhalte einschließlich weiterer
  Nachrichten funktionieren weiter. Ordner, Review, Regeln und Vorschläge bleiben
  erhalten. Kein neues Schema, keine Migration und keine externe Abhängigkeit.
- 25 Tests erfolgreich unter Python 3.12, einschließlich automatisiertem HTTP-Test
  für offiziellen Import, Ablehnung verkürzter/älterer Exporte, Suche und Export.
  Rollbacks werden auch nach Wiederöffnung der Datenbank geprüft. Ausgewählte
  neue Regressionstests erzeugen am ursprünglichen main erwartungsgemäß sechs
  Assertion-Fehlschläge ohne Infrastrukturfehler.
- GitHub Issues, PRs und Actions-Ergebnisse wurden erneut abgefragt, bleiben aber
  durch API `Forbidden` nicht einsehbar. Lokale Tests ersetzen keine CI-Bestätigung.

Bewusste Grenzen: Es gibt noch keinen bestätigten destruktiven Ersetzungsmodus.
Zweigwechsel und Wechsel des Importformats mit anderen Nachrichten-IDs sind
deshalb konservativ gesperrt. Fehlen auf beiden Seiten Änderungszeitpunkte,
kann das Alter nicht beurteilt werden. Inhalte derselben ID können weiterhin
ersetzt werden; das ist keine Erkennung aller Textkürzungen. Metadaten wie Titel,
Projekt und Archivstatus brauchen weiterhin eine eigene Strategie für fehlende
Felder. Historisch bereits verlorene Inhalte werden nicht wiederhergestellt.
