# Entwicklungsprüfung

Chatidy benötigt Python 3.10 oder neuer mit SQLite/FTS5 und keine zusätzlichen Python-Pakete.

Die vorhandene Testsuite lässt sich im Repository-Verzeichnis ausführen:

```bash
python -m unittest discover -s tests -v
```

Die Anwendung startet mit `python -m chatidy` als lokaler Dienst.
