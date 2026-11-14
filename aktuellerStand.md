# Aktueller Stand von Chatidy

## Durchlauf – offizielle segmentierte Exporte und Datenintegrität

Ausgangscommit: `c7702a670cad54bfe8265bdd49f6dad322ece2ef` auf main.
Branch: `feature/segmented-export-preview`. Die öffentliche PR-Liste enthielt
beim Prüfen keine offenen PRs; der vorherige main-CI-Lauf 43520240796 war erfolgreich.

### Umgesetzt und lokal geprüft

- Schema 4 kopiert Nachrichten auf `(conversation_id,id)`; ursprüngliche IDs,
  Positionen, Metadaten, Ordner, Tags, Review und FTS bleiben erhalten. Gleiche IDs
  in verschiedenen Chats sind unabhängig; doppelte IDs im selben Chat bleiben
  Fehler. Der Schema-3-Umbau und ein absichtlich fehlgeschlagener Umbau sind geprüft.
- Archivklassifizierung vor dem Parsen: klassische und nummerierte Segmente,
  Metadatenrollen, Anhänge, HTML, Begleitdateien und unbekannte Ressourcen.
  000–007 werden numerisch und gemeinsam verarbeitet, selbst bei umgekehrter
  ZIP-Reihenfolge. Interne Lücken, doppelte Nummern, defekte Pflichtsegmente und
  mehrdeutige Dateivarianten brechen den Import ab.
- Eine vollständig synthetische Form mit 18 JSON-Dateien, 227 DAT-Ressourcen,
  HTML und Begleittext ist getestet. Kontodaten, Werbung, Codex, Bibliotheks-/
  Assetzuordnungen und beide Manifestrollen werden nicht als Chats interpretiert.
  Kein privater Originalexport oder dessen Inhalte/IDs wurde angefordert oder verwendet.
- Neue Weboberfläche: Analyse → Vorschau → eine Batch-Bestätigung. Vorher keine
  Gesprächsübernahme oder Migration durch den Analysepfad. Inventar, Gesprächszahl,
  Konflikte, Warnungen und grobe Speicherprognose sind sichtbar. Identisches bleibt
  unverändert; sichere neuere Versionen/Ergänzungen werden automatisch behandelt.
- Ältere und abweichende/unvollständige Chats können je klar definierter Klasse
  ausdrücklich vollständig unverändert bleiben. Unklare Identitäten sind nicht
  ignorierbar. Entscheidungen bleiben auf denselben Job und Quellenhash begrenzt.
- Beim Commit erneute Konfliktprüfung unter Schreibsperre; bei geänderter Bibliothek
  ggf. neue Vorschau. Atomicität und Wiederaufnahme bleiben erhalten. Die gemeinsame
  Identitätsprüfung schützt auch die kompatiblen explizit mutierenden Legacy-APIs.

### Tatsächlich geprüfter Stand

105 Tests entdeckt: 95 erfolgreich ausgeführt und zehn native Windows-Tests hier
übersprungen. Echter Chromium-Browsertest erfolgreich: Vorschau ohne Datenübernahme,
Einzeldatei danach Gesamt-ZIP, Reimport, klassenbezogener älterer Batch, unveränderte
Bestandsdaten sowie bisherige Jobverwaltung/Organisation und mobile Ansicht.
Die Bestätigung wird erst nach Ende der aktiven Analyse angezeigt, sodass eine
späte Statusabfrage keine bereits gewählten Klassenentscheidungen zurücksetzt.

[CI 43561857600](https://github.com/muk4li/chatidy/actions/runs/43561857600) bestätigt
Implementierungscommit `fd62bc4` mit sechs erfolgreichen Jobs:

| Host | Python 3.10 | Python 3.11 | Python 3.13 |
| --- | --- | --- | --- |
| ubuntu-latest | erfolgreich | erfolgreich | erfolgreich |
| windows-latest | erfolgreich | erfolgreich | erfolgreich |

Alle neuen generischen Export-/Migrations-/Vorschautests laufen damit auch nativ
auf Windows. Ein manueller Windows-11-Test mit dem privaten Originalexport wurde
nicht durchgeführt. Ausgangsbestand und Features sind getrennt von diesem Nachweis.

Commits: Planung `4f4d681`, Identität `7682250`, Layout `607f3ce`, Vorschau/Batch
`fd62bc4`. Ein nachfolgender UI-/Dokumentationsabschluss ändert nicht die geprüfte
Python-Implementierung. Dateiliste/Inhalte und gängige Secret-Muster vor jedem
Commit geprüft, ausschließlich synthetische Daten. Python-3.10-Grammatik und
JavaScript-Syntax zusätzlich geprüft.

PR-Erstellung wurde konkret versucht; die API antwortet weiter mit Forbidden.
Kein PR-/Merge-Erfolg wird behauptet. Der Branch ist gepusht, main bleibt
unverändert. ROADMAP.md und TASKS.md markieren EXP-001/DATA-001/IMP-001 anhand
obenstehender Akzeptanz und CI als implementiert/getestet; DELIV-001 bleibt blockiert.

### Grenzen und Backlog

Manifeste und zusätzliche JSON-Schemas bleiben absichtlich ungeprüft und werden
nur inventarisiert. Ein fehlendes letztes Segment ist ohne vertrauenswürdig
validierte Gesamtzahl nicht erkennbar. Im mehrdeutigen Extractor-ZIP-Fallback bleibt
beschädigtes JSON ein Fehler. Doppelte Gesprächs-IDs in einem Batch werden nicht
still dedupliziert oder zusammengeführt. Es gibt keinen destruktiven Ersetzungsmodus.
Die private Uploadkopie enthält bis zur bestätigten Bereinigung weiterhin das ganze
Archiv; die Bibliothek erhält nur ausgewählte Gesprächsdaten. DAT bleibt Inventar/
Referenz, ohne Medienextraktion. Speicherprognose ist grob, keine Quota.

Upload-/JSON-Limits bleiben 200/350 MB; ein großes Einzelobjekt benötigt RAM.
Kein automatisches Hochsetzen aufgrund der komprimierten Archivgröße. Native
Windows-NTFS- und Linux-Sicherheitsgrenzen bleiben erhalten. Der private echte
Export und ein manueller Windows-11-Durchlauf mit ihm wurden nicht geprüft.

ROADMAP.md enthält die fünf Produktphasen, AGENTS.md praktische Entwicklungsregeln,
TASKS.md die P0-Arbeitspakete mit Akzeptanz/Tests und die offenen P1–P3-Themen.
META-001, SCALE-001 und DATA-002 bleiben ausdrücklich offen/teilweise: Schemas,
Speicherbudgets und komplexe Versions-/Zweigrekonstruktion sind nicht als fertig markiert.

---


## Neuester Durchlauf – P0: native Windows-Importjobs

Ausgangscommit: `80f420d360f801f59f2db3e9eab5d2e10f0bbdc6` auf main.
Feature-Branch: `feature/native-windows-import-jobs`.

### Implementierte Lösung und Sicherheit

Der Job-Lebenszyklus verwendet eine kleine Storage-Schnittstelle. Linux behält
flock, descriptorrelative Operationen und /proc/self/fd. Das neue native Windows-
Backend verwendet ausschließlich die Python-Standardbibliothek und Win32-APIs:

- CreateFileW öffnet Reparse Points selbst. Junctions, Symlinks, Hardlinks und
  fremde Dateitypen werden vor Verarbeitung/Bereinigung abgelehnt.
- Handles aller Pfadkomponenten bleiben während des Jobs offen und verweigern
  FILE_SHARE_DELETE. Die Jobpfade können deshalb während Streaming und nativer
  SQLite-Nutzung nicht umbenannt/ausgetauscht werden.
- Geschützte DACLs beschränken neue Dateien/Ordner auf den Benutzer und SYSTEM.
  Bestehende breite Schreibrechte werden abgelehnt, nicht pauschal repariert.
- msvcrt-Bytebereichssperren koordinieren Verwaltung und Jobs prozessübergreifend.
  Die Bereinigung prüft zuerst, dass kein Worker aktiv ist. Danach darf die eigene
  Cleanup-Lease unter der durchgehend gehaltenen Registry-Sperre geschlossen
  werden, damit Windows die Lockdatei nicht als Rename-Hindernis behandelt.
- MoveFileEx ersetzt gespülte Statusdateien atomar. Vor der Entfernung von Daten
  wird das umbenannte Jobverzeichnis erneut gepinnt und seine native Identität
  geprüft. Dateilöschungen erfolgen über geprüfte Handles. Originalexport,
  Hauptdatenbank und Sidecars bleiben geschützt; Löschung verlangt Bestätigung.
- HTTP-Verbindungen und Staging-Cursor werden deterministisch geschlossen. Die CI
  hat außerdem ein Statuslese-Rennen sichtbar gemacht: eine bereits geöffnete,
  inzwischen atomar ersetzte Datei mit Linkzahl 0 ist kein Hardlink. Mehrere Links
  bleiben abgelehnt. Hierfür existiert ein Regressionstest.

Keine neue Schema-Migration, keine externen Pflichtpakete und kein WSL/Docker.
Graph-, ZIP-, Streaming-, Reimport- und Transaktionsschutz bleiben erhalten.

### Tatsächlich verifiziert

[CI-Lauf 43517257301](https://github.com/muk4li/chatidy/actions/runs/43517257301)
prüft Implementierungscommit `f66248b` einschließlich serialisierter Windows-Statuspublikation.
Alle sechs Jobs dieses Implementierungslaufs wurden auf der öffentlichen Actions-Seite als erfolgreich bestätigt:

| Host | Python 3.10 | Python 3.11 | Python 3.13 |
| --- | --- | --- | --- |
| ubuntu-latest | erfolgreich | erfolgreich | erfolgreich |
| windows-latest | erfolgreich | erfolgreich | erfolgreich |

Die native Windows-Suite enthält zusätzlich Junction-/Reparse-Abwehr, ACL-Prüfung,
Bytebereichssperren, parallele Jobs, echte Prozessabbrüche/Wiederaufnahme, offene
Dateihandles und SQLite-WAL. Der plattformübergreifende HTTP-Test führt einen
normalen offiziellen ZIP-Import mit Fortschritt und bestätigter Bereinigung aus
und prüft SQLite/FTS5 sowie den unveränderten Originalexport. POSIX-spezifische
Mechanismentests laufen weiterhin unter Linux. Ein Windows-Symlink-Test darf bei
fehlendem Privileg ausdrücklich übersprungen werden; die Junction-Tests werden
nicht aus diesem Grund übersprungen.

Lokal unter Linux: 84 entdeckte Tests, 74 erfolgreich ausgeführt und zehn native
Windows-Tests ausdrücklich übersprungen. Chromium-Browsertest für den vollständigen
bestehenden Import-/Organisations-/Jobverwaltungsablauf erfolgreich, einschließlich
mobilen Layouts. Python-3.10-Grammatik und gestagte Dateien auf private Daten/
gängige Secret-Muster geprüft. Sämtliche Daten sind synthetisch.

Windows ist damit nativ auf echten Windows-CI-Runnern verifiziert. Ein manueller
Windows-11-Desktopdurchlauf mit dem echten Export des Nutzers wurde nicht ausgeführt.
Die Wiederholung der CI hat zusätzlich ein sporadisches Windows-Status-Schreibrennen
aufgedeckt. Windows-Workerstatus und Statusleser werden nun kurz über die Registry-
Sperre serialisiert, ohne die Importverarbeitung zu serialisieren. Auch diese
Korrektur ist im oben verlinkten vollständigen nativen CI-Lauf erfolgreich geprüft.
Frühere fehlgeschlagene CI-Läufe wurden diagnostiziert und korrigiert;
Fehlerannotationen stellen synthetische Tracebacks auch ohne API-Logzugriff bereit.

### Windows-11-Schnellstart und Grenzen

Python 3.13 installieren, Projekt lokal entpacken und PowerShell dort öffnen:

```powershell
$env:CHATIDY_DB = Join-Path $env:LOCALAPPDATA "Chatidy\chatidy.sqlite3"
py -3.13 -m chatidy
```

Dann Browser auf http://127.0.0.1:8877, vollständiges Export-ZIP auswählen und bis
Erfolgreich warten. Jobdaten nur bestätigt bereinigen. Vor einer Sicherung die
Anwendung mit Strg+C beenden und Datenbankordner inklusive vorhandener Sidecars
sowie den Originalexport separat sichern. Vollständige Anleitung/Fehlerhilfe: README.

Zunächst lokale feste NTFS-Laufwerke: keine UNC-/Netzlaufwerke, FAT/exFAT,
OneDrive-Reparse-Pfade, Junctions oder Alternate Data Streams. Keine unsicheren
Fallbacks. Windows bietet kein POSIX-Verzeichnis-fsync; gespülte Dateien,
Write-through und SQLite-Journaling sichern Prozessabbrüche, sind aber keine
Garantie gegen jedes Hardwareversagen. Programme mit denselben Benutzerrechten,
SYSTEM und Administratoren bleiben Teil der lokalen Vertrauensgrenze. Die Limits
bleiben 200 MB Upload / 350 MB entpacktes JSON; einzelne große Objekte benötigen RAM.

### Lieferung und nächster Schritt

Die Änderungen sind auf dem Feature-Branch gepusht. GitHub-API-Aufrufe zur PR-
Erstellung liefern weiterhin Forbidden; die öffentliche Actions-Seite erlaubt
hingegen die CI-Prüfung. Ein PR und Merge dürfen nicht als erledigt gelten, solange
sie nicht tatsächlich bestätigt sind. main wurde in diesem Durchlauf nicht verändert.
Nächster sinnvoller Schritt: Branch per PR prüfen/mergen und den ersten echten
Windows-11-Import lokal nach der README durchführen, ohne private Exporte hochzuladen.

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
