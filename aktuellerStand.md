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

1. **ZIP-Import und Fehlerbehandlung härten** – ausstehend.
   Defektes JSON, ZIP-Bombs, Verschlüsselung und unvollständige Exporte erkennen.
2. **Große Exporte effizient importieren** – ausstehend.
   Speicherverbrauch reduzieren, Fortschritt anzeigen und unterbrochene Importe
   sicher wiederaufnehmen.
3. **Extractor-Integration vervollständigen** – ausstehend.
   Metadaten, Bilder-/Anhangreferenzen, Code und weitere Inhalte verlustärmer
   erhalten, ohne Cloud-Aufrufe oder erzwungene externe Abhängigkeit.
4. **UI und Organisation ausbauen** – ausstehend.
   Mehrfachauswahl, Drag-and-drop, Tags und intelligente Ordner auf stabiler Basis.

## Nächster interner Arbeitsauftrag

Härte ZIP/JSON in einer separaten Iteration. Kein stilles Überspringen defekter
Konversationen, keine Teilimporte, keine Archivextraktion auf Dateipfade. Prüfe
Größen-, Kompressions- und Verschlüsselungsgrenzen mit synthetischen Tests,
führe die gesamte Suite aus und ergänze hier Ergebnisse und nächsten Auftrag.
