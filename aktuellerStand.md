# Aktueller Stand von Chatidy

## Neuester Durchlauf – P0: native Windows-Importjobs

Ausgangscommit: `80f420d360f801f59f2db3e9eab5d2e10f0bbdc6` auf main.
Feature-Branch: `feature/native-windows-import-jobs`.

### Ursache und Änderung

Die bisherige Jobverwaltung verwendete ausschließlich flock/O_NOFOLLOW/dir_fd,
POSIX-Benutzerrechte und /proc/self/fd. Das verhinderte den normalen Jobimport auf
Windows. Der Job-Lebenszyklus verwendet nun plattformneutrale Storage-Operationen.
Linux behält sein descriptorrelatives Backend. Windows nutzt ein explizites
NTFS-Backend mit typisierten Win32-Aufrufen über ctypes (Standardbibliothek):

- CreateFileW öffnet Reparse Points selbst; Junctions/Symlinks werden abgelehnt.
- Gehaltene Handles aller Pfadkomponenten verhindern deren Austausch während
  Streaming/Staging. Windows-SQLite arbeitet dadurch mit normalen Dateipfaden.
- Geschützte DACLs für neue Dateien/Ordner; bestehende breite Schreibrechte,
  Hardlinks und unzulässige Dateitypen werden abgelehnt, nicht still repariert.
- Prozessübergreifende msvcrt-Bytebereichssperren koordinieren Jobs und Verwaltung.
- Statusdateien werden gespült und über MoveFileEx atomar ersetzt. Verzeichnis-
  Umbenennungen und Löschungen verwenden geprüfte Handles und Identitätskontrollen.
- Die Job-Lease wird erst am Ende der bestätigten Bereinigung unter weiterhin
  gehaltener Registry-Sperre geschlossen, damit keine delete-pending Lockdatei
  die Entfernung des Windows-Verzeichnisses blockiert.
- Keine Schemaänderung, kein WSL/Docker und keine neue externe Pflichtabhängigkeit.

### Validierung – ehrlicher Zwischenstand vor Windows-CI

Linux: 82 entdeckte Tests, davon 73 erfolgreich ausgeführt und neun echte
Windows-Tests explizit übersprungen. Der neue plattformübergreifende HTTP-Test
prüft offiziellen ZIP-Upload, Fortschritt, SQLite/FTS5, bestätigte Bereinigung
und unveränderten Originalexport. Bestehende Linux-Regressionen bleiben erhalten.
Windows-Matrix für Python 3.10/3.11/3.13 ist angelegt. Native Tests prüfen
Junctions, Reparse Points, ACLs, Windows-Pfade, Bytebereichssperren, offene Dateien,
SQLite-WAL und Schutz der Original-/Hauptdatenbank. Generische Prozessabbruch-,
Parallelitäts- und Wiederaufnahme-Tests laufen ebenfalls in dieser Matrix.
POSIX-spezifische Mechanismentests sind unter Windows gezielt durch native Tests
ergänzt; fehlende Symlink-Berechtigung kann dort einen einzelnen Test überspringen.

Windows ist erst nach erfolgreicher echter Windows-CI als verifiziert zu bezeichnen.
Dieser Zwischenstand behauptet noch keinen solchen Erfolg. Im ersten echten Lauf
43514922424 waren Linux-Jobs erfolgreich, Windows-Jobs jedoch fehlgeschlagen.
CI-Fehlerannotationen ergänzen nun die unveränderte vollständige Suite, damit
synthetische Tracebacks ohne Zugriff auf angemeldete Rohlogs untersucht werden können.
Der Folgelauf identifizierte Fehler beim Windows-Verzeichnis-Rename und offene
SQLite-Verbindungen/Cursor. Die Korrektur nutzt MoveFileEx mit erneuter Pinning-/
Identitätsprüfung vor dem Löschen sowie deterministisches Schließen aller
HTTP-Verbindungen und des Staging-Cursors. Diese Korrektur braucht erneut echte CI. Im nächsten Lauf wurde zusätzlich die
eigene offene Lockdatei als Windows-Rename-Hindernis isoliert: nach bewiesener
Inaktivität wird sie unter weiterhin durchgehend gehaltener Registry-Sperre vor
dem Rename geschlossen. Ein Statuslese-Rennen bei atomarer Ersetzung erhält
einen Regressionstest; bereits geöffnete, inzwischen unbenannte Dateien mit
Linkzahl 0 sind keine Hardlinks. Mehrere Links bleiben gesperrt. Die öffentliche
GitHub-Actions-Webseite ist lesbar, obwohl die API bisher Forbidden lieferte;
nach dem Push wird damit der konkrete Lauf überprüft, soweit verfügbar.

### Bekannte Grenzen und Windows-Schnellstart

Zunächst lokale feste NTFS-Laufwerke, keine UNC-/Netzlaufwerke, FAT/exFAT,
OneDrive-Reparse-Pfade oder Junctions. Sicherheitsablehnungen werden nicht durch
schwächere Fallbacks umgangen. Windows bietet kein POSIX-Verzeichnis-fsync;
Status-Write-through und SQLite-Journaling sichern Prozessabbrüche, sind aber
keine pauschale Garantie gegen jedes Speicher-/Hardwareversagen. Programme mit
denselben Benutzerrechten sowie SYSTEM/Administratoren bleiben Teil der lokalen
Vertrauensgrenze. Upload-/Entpacklimits bleiben 200/350 MB.

README enthält den vollständigen Windows-11-Schnellstart. Kurz: Python installieren,
Projekt lokal entpacken, in PowerShell im Projektverzeichnis ausführen:

```powershell
$env:CHATIDY_DB = Join-Path $env:LOCALAPPDATA "Chatidy\chatidy.sqlite3"
py -3.13 -m chatidy
```

Dann Browser auf http://127.0.0.1:8877, vollständiges Export-ZIP auswählen,
Fortschritt bis Erfolgreich prüfen. Jobdaten nur bestätigt bereinigen und bei
beendeter Anwendung Datenbankordner inklusive Sidecars und Originalexport sichern.

---

## Historie – Importjob-Datenschutz


## Neuester Durchlauf – sichere Importjob-Verwaltung

Tatsächlich geprüfter main-Ausgangspunkt: `0ecabfb44ea4d68e5cd5251f65c2cffefbb43444`.
Feature-Branch: `feature/import-job-lifecycle`.
Die vorherigen vier Folgephasen sind inzwischen über PR #3 in main integriert.

### Ergebnis

- Prozessübergreifende Job-Sperren, synchron vor dem Workerstart erworben. Aktive
  Jobs sind nicht löschbar und können nicht doppelt gestartet werden. Nach einem
  Prozessabbruch werden alte Prüf-/Commitzustände als unterbrochen angezeigt.
- Alle gespeicherten Jobs sind über Übersicht/API erreichbar: Status, Erstellung,
  geprüfte Gespräche, logische Dateigröße, Fortsetzen und bestätigtes Löschen.
- Bestätigte Bereinigung über feste Dateiliste und descriptorrelative Operationen;
  keine Pfadrekursion, keine Symlinkverfolgung, keine Hardlinks oder fremden Dateien.
  Datenbank-/Sidecar-Inodes sind ausdrücklich geschützt. Elternpfade werden auf
  Symlinks und unsichere Schreibrechte geprüft.
- Unterbrochene Löschung bleibt in einem markierten Jobverzeichnis sichtbar;
  erneute Bestätigung schließt sie ab. Keine unbemerkte Entfernung wiederaufnehmbarer
  Jobs. Auch beschädigte Statusdaten können nach Dateiprüfung bestätigt bereinigt
  werden; unsichere Dateistrukturen bleiben gesperrt.
- Unvollständige Uploads bleiben als fehlgeschlagen und nicht wiederaufnehmbar
  sichtbar, statt unbeobachtete Quellenreste zu hinterlassen. Kein automatischer
  Löschlauf und keine automatische Entfernung der Bibliothek oder Originalexporte.
- `import-jobs/` wird auch unter benutzerdefinierten Datenbankpfaden auf beliebiger
  Verzeichnisebene ignoriert. Eigene beliebige Datenbanknamen müssen zusätzlich
  lokal ausgeschlossen oder außerhalb des Checkouts gespeichert werden.

### Validierung und Sicherheitsprüfung

72 Python-Tests erfolgreich, einschließlich realer Prozessabbrüche während der
Prüfung und nach dem Hauptdatenbank-Commit, Wiederaufnahme, paralleler Jobs,
aktiver Löschsperren, HTTP-Bestätigung, manipulierter IDs/Verzeichnisse, Symlinks,
Hardlinks, unterbrochener Bereinigung sowie unveränderter SQLite-/FTS5-Daten.
Echter Chromium-Browsertest erfolgreich: Übersicht, Größen, abgebrochene und
bestätigte Löschdialoge, aktive Sperre, Prozessabbruch/Fortsetzen und mobile Ansicht;
bestehende Import-/Organisationsfunktionen bleiben Bestandteil dieses Tests.
Alle Testdaten sind synthetisch. Keine neue Schema-Migration. JavaScript-Syntax
und Python-3.10-Grammatik werden vor dem Commit geprüft; kein Python-3.10-Lauf
wird behauptet. Änderungen werden vor dem Commit auf private Daten geprüft.

### Grenzen und nächster sinnvoller Schritt

Die sichere Verwaltung setzt derzeit lokale POSIX-Sperren/dir_fd sowie Linux-
/proc/self/fd für Staging voraus. Auf nicht unterstützten Plattformen wird
abgelehnt, statt unsicher zurückzufallen; der synchrone Import bleibt nutzbar.
Statusabfragen zeigen logische Dateigrößen, keine Dateisystem-Quoten. Unbekannte
oder gesperrte Einträge sind nicht in der erfassten Größe enthalten. Keine
Aufbewahrungsfrist, kein automatischer Hintergrund-Löschlauf. Sperren sind keine
Zugriffskontrolle gegen Programme mit denselben Betriebssystemrechten.

Nächster sinnvoller Entwicklungsschritt: konfigurierbare Speicherbudgets und
Speicherhinweise für Importjobs, weiterhin ohne automatische destruktive Löschung.
PR-/CI- und Merge-Status werden im Abschlussbericht anhand des tatsächlichen
GitHub-Zugriffs dokumentiert; ein erfolgreicher lokaler Test ersetzt keine CI.

---

## Historie der vorherigen Entwicklungsphasen


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
