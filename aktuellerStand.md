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
3. **Extractor-Integration vervollständigen** – ausstehend.
   Metadaten, Bilder-/Anhangreferenzen, Code und weitere Inhalte verlustärmer
   erhalten, ohne Cloud-Aufrufe oder erzwungene externe Abhängigkeit.
4. **UI und Organisation ausbauen** – ausstehend.
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

## Nächster interner Arbeitsauftrag

Erweitere den optionalen Extractor-JSON-Adapter ohne dessen Parsing neu zu bauen.
Erhalte zusätzliche Metadaten, Zitate, Dateien, Bild-/Anhangreferenzen und Code
verlustärmer. Nutze nachvollziehbare additive Migrationen und Tests für bestehende
Datenbanken. Keine automatischen Downloads und keine Ausführung importierter
Inhalte. Aktualisiere Status und Folgeauftrag für UI/Organisation.
