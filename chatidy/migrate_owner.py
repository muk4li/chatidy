"""Explicit, offline-only copy of single-user content to one enrolled owner library.

No implicit migration on login or startup. Never copy users, OIDC challenges,
session hashes or other accounts into the new user library.
"""
import argparse
from contextlib import closing
import os
import sqlite3
from pathlib import Path
from .db import connect
from .library_scope import account_database_path, _prepare_account_database
from .users import User

DATA_TABLES = ("folders","conversations","messages","tags","smart_folders",
               "rules","memberships","suggestions","chat_tags")


def _snapshot(db, table):
    cols = [row["name"] for row in db.execute("PRAGMA table_info("+table+")")]
    return cols, [tuple(row) for row in db.execute(
        "SELECT "+",".join('"'+x+'"' for x in cols)+" FROM "+table+" ORDER BY rowid")]


def copy_legacy(registry_path, user_id, *, confirmed=False, server_stopped=False):
    if not confirmed or not server_stopped:
        raise ValueError("Migration nur nach bestätigtem Stopp und Backup.")
    if type(user_id) is not int or user_id < 1:
        raise ValueError("Ungültiges Eigentümerkonto.")
    registry_path = Path(os.path.abspath(registry_path))
    if not registry_path.is_file():
        raise ValueError("Bestandsdatenbank fehlt.")
    target = registry_path.parent / "accounts" / str(user_id) / "chatidy.sqlite3"
    # Do not even run schema-upgrade steps on user data without an actual backup.
    backup_dir = registry_path.parent / "backups"
    backup_dir.mkdir(mode=0o700,exist_ok=True)
    if os.name != "nt" and backup_dir.stat().st_mode & 0o077:
        raise ValueError("Backup-Verzeichnis darf nicht öffentlich lesbar sein.")
    backup = backup_dir / ("chatidy-before-owner-migration-"+str(user_id)+".sqlite3")
    if backup.exists() or target.exists():
        raise ValueError("Backup/Ziel bereits vorhanden. Keine Überschreibung.")
    fd = os.open(backup,os.O_CREAT | os.O_EXCL | os.O_WRONLY,0o600)
    os.close(fd)
    try:
        with closing(sqlite3.connect(registry_path)) as old, closing(sqlite3.connect(backup)) as saved:
            old.backup(saved)
        with closing(connect(registry_path)) as registry:
            row = registry.execute(
                "SELECT id,oidc_issuer,oidc_sub,role,display_name,status "
                "FROM users WHERE id=?", (user_id,)).fetchone()
            if row is None or row["role"]!="owner" or row["status"]!="active":
                raise ValueError("Nur ein bereits eingeschriebenes aktives Eigentümerkonto.")
            user = User(row["id"],row["oidc_issuer"],row["oidc_sub"],row["role"],row["display_name"])
            # Import jobs are never moved silently; stop and handle them separately.
            jobs_dir=registry_path.parent/"import-jobs"
            if jobs_dir.exists() and any(entry.name!="management.lock" for entry in jobs_dir.iterdir()):
                raise ValueError("Bestands-Importjobs müssen zuerst administrativ geprüft werden.")
            snapshots={table:_snapshot(registry,table) for table in DATA_TABLES}
        if target.exists():
            raise ValueError("Zielbibliothek existiert bereits.")
        staging = target.with_name(".pending-owner-migration.sqlite3")
        if staging.exists():
            raise ValueError("Unvollständige ältere Migration – manuell prüfen.")
        _prepare_account_database(staging)
        try:
            with closing(connect(staging)) as account:
                with account:
                    account.execute("DELETE FROM folders")  # remove new-DB starter folders
                    for table in DATA_TABLES:
                        cols,rows=snapshots[table]
                        if rows:
                            names=",".join('"'+col+'"' for col in cols)
                            marks=",".join("?" for col in cols)
                            account.executemany("INSERT INTO "+table+"("+names+") VALUES("+marks+")",rows)
                    # Rebuild from actual messages, without non-text placeholder.
                    account.execute("DELETE FROM search_index")
                    account.execute("""INSERT INTO search_index(conversation_id,title,body)
                      SELECT c.id,c.title,COALESCE((SELECT group_concat(content,char(10))
                      FROM (SELECT content FROM messages m WHERE m.conversation_id=c.id
                      AND m.content!='[Nicht-textueller Inhalt]' ORDER BY m.position,m.rowid)),'')
                      FROM conversations c""")
                for table,(columns,rows) in snapshots.items():
                    target_columns,target_rows=_snapshot(account,table)
                    if target_columns!=columns or target_rows!=rows:
                        raise ValueError("Migrationsprüfung fehlgeschlagen: Datenvergleich.")
                if account.execute("PRAGMA foreign_key_check").fetchall():
                    raise ValueError("Migrations-Fremdschlüsselprüfung fehlgeschlagen.")
                if account.execute("PRAGMA integrity_check").fetchone()[0]!="ok":
                    raise ValueError("Migrations-Integritätsprüfung fehlgeschlagen.")
                if account.execute("SELECT count(*) FROM users").fetchone()[0]:
                    raise ValueError("Anmeldedaten dürfen nicht in Kontobibliotheken gelangen.")
            # The source database and offline backup remain untouched. Target is new.
            if target.exists():
                raise ValueError("Ziel inzwischen vorhanden, keine Überschreibung.")
            os.rename(staging,target)
        except BaseException:
            # Deliberately leave a failed staging DB for admin review; no data deleted.
            raise
        return {"conversations":len(snapshots["conversations"][1]),
                "backup_created":True,"target_created":True}
    except BaseException:
        # Even when migration fails, preserve the offline backup.
        raise


def main(argv=None):
    parser=argparse.ArgumentParser(description="Explizite Offline-Kopie der lokalen Bibliothek.")
    parser.add_argument("--db",required=True,type=Path)
    parser.add_argument("--owner-id",required=True,type=int)
    parser.add_argument("--confirm",action="store_true")
    parser.add_argument("--server-stopped",action="store_true")
    args=parser.parse_args(argv)
    try:
        result=copy_legacy(args.db,args.owner_id,confirmed=args.confirm,
                           server_stopped=args.server_stopped)
    except (ValueError,sqlite3.Error,OSError):
        print("Migration nicht abgeschlossen. Lokales Backup und Staging prüfen.")
        return 1
    print("Bibliothekskopie erstellt. Gespräche:",result["conversations"])
    return 0

if __name__=="__main__":
    raise SystemExit(main())
