# Aktueller Stand von Chatidy

Ausgangsbasis dieses Durchlaufs: main `46c9c936998bce9110d04f0e06ad99d15b44ac98`.
Alle Daten in Tests sind synthetisch. Änderungen liegen auf
`feature/import-foundation-and-organisation`; der Nutzer übernimmt den Merge.

## Graph-Korrektur – abgeschlossen

Elternketten bestimmen die Reihenfolge, nie Zeitstempel. Ein gültiger current_node
wählt genau einen Zweig. Ohne gültigen current_node wird ausschließlich ein
vollständig eindeutiger Verlauf rekonstruiert. Mehrdeutigkeit, Zyklen, fehlende
Eltern, ungültige Knoten und widersprüchliche children-Listen liefern ValueError
vor dem Schreiben. Auch inaktive Knoten werden geprüft. Fallback-Nachrichten-IDs
verwenden stabile Knotenschlüssel statt Laufpositionen. Alte Importe mit früheren
Fallback-IDs können deshalb konservativ vom Reimport-Schutz abgelehnt werden.

Extractor-Referenz: backward_traverse in Stand `33ad32f`; die Rückwärtstraversierung
wurde übernommen als Prinzip, dessen gewichtete Blattwahl ausdrücklich nicht.
SQLite-Schema und bestehender Reimport-Schutz bleiben erhalten.
Validierung: 31 Tests erfolgreich unter Python 3.12, einschließlich SQLite/FTS,
fehlerhaftem Batch, Zweigwechsel und wiederholtem Import. Python 3.10 wird durch
Syntaxprüfung mit dessen Grammatik geprüft; kein Python-3.10-Lauf behauptet.

## Vier Folgephasen in Ausführungsreihenfolge

1. **ZIP-Import und Fehlerbehandlung härten** – abgeschlossen (erste sichere Version).
   Defektes JSON, ZIP-Bombs, Verschlüsselung und unvollständige Exporte erkennen.
2. **Große Exporte effizient importieren** – abgeschlossen (begrenzter Streaming-/Jobpfad).
   Speicherverbrauch reduzieren, Fortschritt anzeigen und unterbrochene Importe
   sicher wiederaufnehmen.
3. **Extractor-Integration vervollständigen** – abgeschlossen (verlustärmerer JSON-Adapter).
   Metadaten, Bilder-/Anhangreferenzen, Code und weitere Inhalte verlustärmer
   erhalten, ohne Cloud-Aufrufe oder erzwungene externe Abhängigkeit.
4. **UI und Organisation ausbauen** – abgeschlossen (nutzbare erste Organisationsversion).
   Mehrfachauswahl, Drag-and-drop, Tags und intelligente Ordner auf stabiler Basis.

## Ergebnis Folgephase 1 – ZIP und Fehlerbehandlung

Kein stilles Überspringen defekter JSON-Dateien oder unbekannter Konversationen.
Doppelte JSON-Schlüssel/Chat-IDs, mehrdeutige conversations.json, verschlüsselte
Archive, CRC-Fehler, unzulässige Größen/Dateizahlen und hohe Kompressionsraten
werden kontrolliert abgelehnt. Keine Extraktion von Archivpfaden. Ein offizielles
conversations.json hat weiterhin Vorrang vor beiliegenden Kontometadaten.
38 Tests erfolgreich, einschließlich kleiner synthetischer ZIP-Bomb und manipulierten
Verschlüsselungsflags. Kein Test verwendet echte Nutzerdaten.

## Ergebnis Folgephase 2 – große Exporte

Upload in lokalen Dateien statt Bytes-Kopie im Server; JSON-Arrays werden
konversationsweise mit begrenztem Dekompressionsbudget gelesen. Persistentes
SQLite-Staging mit SHA-256-Quellenprüfung, Fortschrittsstatus und Fortsetzen nach
Neustart. Erst die vollständige Prüfung erlaubt einen atomaren Hauptdatenbank-
Commit. Bestehender synchroner Endpunkt bleibt kompatibel. Die Weboberfläche
speichert die letzte Job-ID lokal und zeigt Prüfphase und geprüfte Chatanzahl.
46 Tests erfolgreich, einschließlich HTTP-Jobpfad, simulierter Unterbrechung,
Commitfehler, nachträglichem JSON-Fehler, Quellenänderung und Speicherregression:
3.000 synthetische Chats (~12 MB) mit weniger als 2 MB zusätzlich gemessenem
Python-Speicher beim Streaming.
Grenzen: ein Chat/Objekt-Envelope passt in RAM; 200/350-MB-Limits bleiben. Bei Resume
wird die Quelle von vorn gelesen, Checkpoints werden verifiziert. Upload-Abbrüche
brauchen erneuten Upload. Jobdaten bleiben privat lokal bis zur manuellen Bereinigung.

## Ergebnis Folgephase 3 – optionale Extractor-Integration

Gesprächs-/Nachrichten-Zusatzdaten, Modellfelder, Zitate, Quellen und Datei-/Bild-
referenzen werden als lokale JSON-Metadaten gespeichert und im Detail/Export
sichtbar. Code bleibt unveränderter Text. Nichttextuelle Inhalte mit Referenzen
werden nicht mehr allein wegen fehlenden Textes verworfen. Fehlende Zusatzfelder
erhalten vorhandene Werte auf oberster Ebene. Keine Binärdateiextraktion, keine
Downloads und keine neue Pflichtabhängigkeit. Additive transaktionale Migration
auf Schema 1, inklusive Zukunftsversionsschutz. 51 Tests erfolgreich; Migration
bestehender Daten, Wiederöffnung, Migrations-Rollback und Metadaten-Rundlauf geprüft.
Grenzen: Binäranhänge und alle alternativen Zweige bleiben außerhalb des Adapters;
die Originalformat-Serialisierung wird nicht nachgebildet.

## Ergebnis Folgephase 4 – UI und Organisation

Mehrfachauswahl bis 500 geladener Chats mit bestätigter zusätzlicher Bulk-
Ordnerzuordnung. Native Drag-and-drop-Zuordnung einzelner/ausgewählter Chats mit
Bestätigung; Tags im Detail bearbeiten oder für die Auswahl ergänzen. Dynamische
intelligente Ordner speichern Suchtext, Tag und Ansichtsfilter; die API kann auch
Projektfilter speichern. Löschen einer Suchansicht entfernt keine Chats.
Additive Migration 2 ergänzt Tags/Suchansichten, Migration 3 die explizite
Nachrichtenposition. Diese erhält die Graphreihenfolge auch nach Datenbank-
Speicherung bei widersprüchlichen Zeitstempeln. Veraltete Suchantworten dürfen
keine neuere Ansicht mehr überschreiben. Mobile Navigation scrollt ohne
überlappende Beschriftungen und ohne horizontalen Seitenüberlauf.

Validierung: alle 55 Python-Tests erfolgreich. Echter Chromium-Browsertest prüft
Upload mit Fortschritt, Bulk-Auswahl, bestätigte Zuordnung, Tags, Drag-and-drop,
dynamische Suchordner, Metadatenanzeige ohne externe Anhang-Anfragen und mobiles
Layout. JavaScript-Syntaxprüfung und Python-3.10-Grammatikprüfung erfolgreich.
Ein Python-3.10-Lauf sowie entfernte GitHub-CI-Ergebnisse wurden nicht bestätigt.
Die GitHub-API liefert weiterhin Forbidden für PR-/CI-Abfragen.

## Abgearbeitete interne Folgeaufträge

1. Nach der Graphphase: „ZIP-/JSON-Import strikt prüfen und Teilimporte verhindern.“
   Ergebnis: Folgephase 1, Commit `516c082`, 38 Tests.
2. Danach: „Streaming, lokales Staging, Fortschritt und sichere Job-Wiederaufnahme
   ergänzen, atomaren Hauptdatenbank-Commit erhalten.“
   Ergebnis: Folgephase 2, Commit `a8d1d5e`, 46 Tests.
3. Danach: „Optionalen Extractor-Adapter erweitern, Zusatzdaten lokal erhalten und
   additive Migrationen mit Regressionstests einführen.“
   Ergebnis: Folgephase 3, Commit `af7d849`, 51 Tests.
4. Danach: „Mehrfachauswahl, bestätigtes Drag-and-drop, Tags und dynamische
   Suchordner mit API-/Browsertests implementieren.“
   Ergebnis: Folgephase 4, 55 Python-Tests und echter Browsertest erfolgreich.

Graphphase: Commit `f3dc01a`; endgültige Positionspersistenz in Folgephase 4 ergänzt.

## Abschluss und verbleibende Grenzen

Keine weitere Phase aus der beauftragten Liste ist offen; alle vier besitzen nun
eine abgegrenzte, getestete erste Version. Es werden keine neuen Phasen autonom
angehängt. Der Nutzer prüft und mergt den gemeinsamen Feature-Branch manuell.

- Keine pauschale vollständige Unterstützung aller ChatGPT-Multimodalitätsformate;
  Binäranhänge bleiben Referenzen, alternative Zweige erhalten keine Versions-UI.
- Exporte mit Objekt-Hüllen und einzelne große Chats benötigen weiterhin RAM für
  das ganze Objekt. Upload-/Entpacklimits bleiben 200/350 MB. Resume validiert die
  Quelle erneut ab Anfang; unvollständige Uploads müssen wiederholt werden.
- Lokale Jobquellen/Staging bleiben bis zur manuellen Bereinigung gespeichert.
- Bestehende Metadaten werden nur auf oberster Ebene zusammengeführt. Gleiche
  Nachrichten-IDs können neuere Textinhalte erhalten; keine Versionshistorie.
- Drag-and-drop fügt Mitgliedschaften hinzu und ist auf Touch-Geräten durch die
  Bulk-Leiste ersetzbar. Die Auswahl betrifft nur geladene Chats (maximal 500).
- Gespeicherte Suchansichten sind explizite lokale Filter, keine KI-Klassifizierung.
- Keine neue Pflichtabhängigkeit, kein öffentliches Hosting und keine echten
  Nutzerdaten in Tests/Commits. Lokale Migrationen wurden mit synthetischen
  Alt-Datenbanken geprüft; vor realen Upgrades lokale Sicherung anlegen.

Empfohlener nächster menschlicher Schritt: Branch-Diff prüfen, CI im GitHub-UI
kontrollieren und bei Zustimmung manuell mergen. Die automatische PR-Erstellung
ist abhängig vom derzeit blockierten GitHub-API-Zugriff.
