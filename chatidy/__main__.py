import sys
import sqlite3
from .server import main

if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, sqlite3.Error):
        # Never echo secret values, private paths or request data in startup errors.
        print("Chatidy-Start fehlgeschlagen: Listener, Datenrechte und Auth-/Proxy-Konfiguration prüfen.", file=sys.stderr)
        sys.exit(1)
