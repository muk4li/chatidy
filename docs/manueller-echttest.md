# Manueller Echttest unter Windows 11

Diesen Test führt der Nutzer ausschließlich lokal durch. Export, Datenbank und
Screenshots mit privaten Inhalten bleiben auf seinem Rechner. Hier nichts hochladen.

1. Python 3.13 und den zu prüfenden Chatidy-Stand bereitstellen. Commit notieren
   (`git rev-parse HEAD`, falls mit Git installiert). Anwendung zunächst beenden.
   Vorhandene Bibliothek inklusive vorhandener WAL/SHM-Dateien separat sichern.
2. PowerShell im Projektordner öffnen. Einen neuen Test-Datenbankpfad auf einem
   lokalen festen NTFS-Laufwerk **außerhalb des Repos und von OneDrive** wählen:

   ```powershell
   $env:CHATIDY_DB = Join-Path $env:LOCALAPPDATA "Chatidy-Echttest\chatidy.sqlite3"
   py -3.13 -m chatidy
   ```

   Für einen frischen Test einen noch nicht benutzten Ordnernamen verwenden,
   keine vorhandene Datenbank löschen. Bei jedem Neustart denselben Pfad setzen.
3. `http://127.0.0.1:8877` öffnen. Vollständiges offizielles Export-ZIP über
   **Datei auswählen** analysieren. Originalexport unverändert aufbewahren.
4. In der Vorschau prüfen: erkannter Archivtyp, Segmentzahl und Reihenfolge
   (falls segmentiert), Gesprächszahl, Ressourcenzahlen, Konfliktklassen,
   Warnungen und grobe Speicherprognose. Bei frischer DB sollten die Gespräche
   neu sein; die Bibliothek sollte vor Bestätigung noch leer bleiben.
   Warnungen zu ungeprüften Manifesten/Anhangreferenzen sind bekannte Grenzen.
   Bei unerwarteten Zahlen oder unklarer Identität nicht bestätigen, nur die
   unten genannten technischen Angaben notieren. Fehlende letzte Segmente können
   ohne validiertes Manifest nicht sicher erkannt werden.
5. Bei plausibler Vorschau **Diesen Batch importieren** bestätigen und bis
   **Erfolgreich** warten. Ergebniszahlen notieren; bei Fehler keine Dateien
   manuell im Jobverzeichnis ändern oder Schutzprüfungen umgehen.
6. Stichproben lokal prüfen:
   - Gesamtzahl der Chats mit Vorschau/Ergebnis vergleichen (nicht nur sichtbare
     Liste; diese ist begrenzt). Abweichungen notieren.
   - Nach einem bekannten Begriff suchen: erscheint das erwartete Gespräch?
   - Einen langen Chat öffnen: Anfang, Ende und Reihenfolge plausibel?
   - Einen Chat mit Code prüfen: Text und Einrückung erhalten? Code wird als
     sicherer Text angezeigt, umfassendes Markdown-Rendering ist nicht zugesagt.
   - Einen Chat mit Bild/Anhang prüfen: Referenz/Metadaten bzw. Platzhalter vorhanden?
     Binäranzeige und Extraktion sind noch nicht unterstützt; keine externen Abrufe erwarten.
7. Optional einen Testordner zuweisen, Tag setzen und Review-Status ändern.
   **Dasselbe unveränderte ZIP erneut** analysieren. Alle Gespräche sollten als
   identisch gelten. Nach Bestätigung: keine zusätzlichen Chats/Nachrichten,
   bisherige Zuordnungen/Tags/Review und Suche unverändert. Zahlen vergleichen.
8. Optional erfolgreiche **Jobdaten löschen**, ausdrücklich bestätigen und prüfen:
   Chats/Suche und Originalexport sind weiter vorhanden. Nur lokale Upload-/
   Stagingkopien verschwinden. Keine automatische Löschung erwarten.
9. Anwendung mit Strg+C beenden. Private Testdaten lokal aufbewahren oder selbst
   verwalten; keine Datenbank oder Exporte in Git aufnehmen.

## Rückmeldung ohne private Inhalte

- Chatidy-Commit/Version, Windows-Version, Python-Version (`py -3.13 --version`).
- Testschritt und Ergebnis (bestanden/fehlgeschlagen), erwartete vs. angezeigte
  **Anzahlen** von Segmenten, Chats, Konfliktklassen und importierten/unveränderten Chats.
- Warnungsklassen und technische Fehlermeldung als Text, vorher prüfen und
  persönliche Pfade/Benutzernamen/IDs/Inhalte durch `[entfernt]` ersetzen.
- Ob frische oder bestehende Test-DB, ZIP oder JSON, ungefähre Dateigröße,
  lokales NTFS und ob ein Neustart nötig war. Keine genauen privaten Dateinamen.
- Nicht senden: Export, DB, Chattexte/-titel, Suchbegriffe, echte IDs,
  Anhänge, Zugangsdaten oder ungeschwärzte Screenshots/Logs.

Ohne lokalen Durchlauf bleibt [REAL-001](../TASKS.md#real-001--manueller-echttest-durch-nutzer)
offen; grüne synthetische Tests ersetzen diesen Nachweis nicht.
