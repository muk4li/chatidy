"""Explicit host-only enrollment of an OIDC identity; no API or first-login signup.

Run only on an administratively controlled local host after the identity
provider has confirmed the issuer and subject. This does not attach any chats.
"""
import argparse
import sqlite3
import sys
from contextlib import closing
from pathlib import Path

from .db import DEFAULT_DATABASE, connect
from .users import enrolled_user


def enroll(db, issuer, subject, role, *, confirmed=False):
    if confirmed is not True:
        raise ValueError("Explizite Bestätigung erforderlich.")
    if (not isinstance(issuer, str) or not issuer.startswith("https://")
            or issuer != issuer.strip() or any(char.isspace() for char in issuer)
            or not isinstance(subject, str) or not subject
            or subject != subject.strip() or any(char.isspace() for char in subject)
            or role not in ("owner", "member")):
        raise ValueError("Ungültige OIDC-Identität oder Rolle.")
    with db:
        if role == "owner" and db.execute("SELECT 1 FROM users WHERE role='owner'").fetchone():
            raise ValueError("Eigentümerkonto bereits vorhanden. Keine automatische Neuverknüpfung.")
        try:
            result = db.execute(
                "INSERT INTO users(oidc_issuer,oidc_sub,role) VALUES(?,?,?)",
                (issuer, subject, role))
        except sqlite3.IntegrityError as exc:
            raise ValueError("Identität bereits eingetragen oder ungültig.") from exc
        return result.lastrowid


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Lokale OIDC-Kontoeinschreibung; ordnet KEINE Bestandschats zu.")
    parser.add_argument("--db", type=Path, default=None, help="Pfad zur zentralen Chatidy-Datenbank")
    parser.add_argument("--issuer", required=True, help="Exakter HTTPS-OIDC-Issuer aus verifizierter Provider-Konfiguration")
    parser.add_argument("--subject", required=True, help="Exaktes OIDC-sub aus administrativ verifizierter Quelle")
    parser.add_argument("--role", choices=("owner", "member"), required=True)
    parser.add_argument("--confirm", action="store_true", help="Explizite Einschreibung bestätigen")
    args = parser.parse_args(argv)
    if not args.confirm:
        parser.error("Ohne --confirm wird kein Benutzer angelegt.")
    try:
        # Import DB path is never inferred from arbitrary browser input.
        with closing(connect(args.db)) as db:
            uid = enroll(db, args.issuer, args.subject, args.role, confirmed=True)
    except (ValueError, sqlite3.Error) as exc:
        # Avoid echoing identity strings or database record contents.
        print("Kontoeinschreibung fehlgeschlagen. Daten und Berechtigungen lokal prüfen.",
              file=sys.stderr)
        return 1
    print(f"Lokale Benutzer-ID {uid} angelegt. Bestehende Chats wurden NICHT zugeordnet.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
