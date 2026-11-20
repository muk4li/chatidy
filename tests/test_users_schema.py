"""AUTH-002: schema 7 is additive and never claims ownership of legacy chats."""
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from chatidy import migrations
from chatidy.db import connect, upsert, create_folder, assign, chat_detail
from chatidy.organisation import apply_tags


class UsersSchemaTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "synthetic-users.sqlite3"

    def tearDown(self):
        self.tmp.cleanup()

    def seed_version_six(self):
        with patch.object(migrations, "LATEST", 6):
            db = connect(self.path)
            upsert(db, [{"id": "synthetic-chat", "title": "Synthetic title",
                         "messages": [{"id": "synthetic-message", "role": "user",
                                       "content": "Synthetic answer"}]}])
            folder = create_folder(db, "Synthetic folder")
            assign(db, "synthetic-chat", [folder])
            apply_tags(db, ["synthetic-chat"], ["synthetic"])
            before = chat_detail(db, "synthetic-chat")
            db.close()
        return before

    def test_migration_adds_empty_users_and_preserves_data(self):
        before = self.seed_version_six()
        db = connect(self.path)
        try:
            self.assertEqual(db.execute("PRAGMA user_version").fetchone()[0], 7)
            self.assertEqual(db.execute("SELECT count(*) FROM users").fetchone()[0], 0)
            self.assertEqual(chat_detail(db, "synthetic-chat"), before)
            self.assertEqual(db.execute("PRAGMA foreign_key_check").fetchall(), [])
            self.assertEqual(db.execute("PRAGMA integrity_check").fetchone()[0], "ok")
        finally:
            db.close()

    def test_oidc_identity_is_issuer_plus_subject_not_email(self):
        db = connect(self.path)
        try:
            with db:
                db.execute("INSERT INTO users(oidc_issuer,oidc_sub,email,role) VALUES(?,?,?,?)",
                           ("https://synthetic.example/idp", "subject-1", "same@example.invalid", "owner"))
                db.execute("INSERT INTO users(oidc_issuer,oidc_sub,email) VALUES(?,?,?)",
                           ("https://synthetic.example/idp", "subject-2", "same@example.invalid"))
                db.execute("INSERT INTO users(oidc_issuer,oidc_sub,email) VALUES(?,?,?)",
                           ("https://synthetic.example/other", "subject-1", "same@example.invalid"))
            self.assertEqual(db.execute("SELECT count(*) FROM users").fetchone()[0], 3)
            with self.assertRaises(sqlite3.IntegrityError):
                with db:
                    db.execute("INSERT INTO users(oidc_issuer,oidc_sub) VALUES(?,?)",
                               ("https://synthetic.example/idp", "subject-1"))
            with self.assertRaises(sqlite3.IntegrityError):
                with db:
                    db.execute("INSERT INTO users(oidc_issuer,oidc_sub,status) VALUES(?,?,?)",
                               ("https://synthetic.example/idp", "subject-4", "unknown"))
        finally:
            db.close()

    def test_reopen_does_not_create_users_or_change_version(self):
        db = connect(self.path)
        db.close()
        db = connect(self.path)
        try:
            self.assertEqual(db.execute("SELECT count(*) FROM users").fetchone()[0], 0)
            self.assertEqual(db.execute("PRAGMA user_version").fetchone()[0], 7)
        finally:
            db.close()

    def test_migration_failure_preserves_version_six_and_all_data(self):
        before = self.seed_version_six()
        bad = dict(migrations.MIGRATIONS)
        bad[7] = (bad[7][0], "INVALID SQL")
        with patch.object(migrations, "MIGRATIONS", bad), self.assertRaises(sqlite3.OperationalError):
            connect(self.path)
        raw = sqlite3.connect(self.path)
        try:
            self.assertEqual(raw.execute("PRAGMA user_version").fetchone()[0], 6)
            self.assertEqual(raw.execute("SELECT name FROM sqlite_master WHERE name='users'").fetchall(), [])
        finally:
            raw.close()
        db = connect(self.path)
        try:
            self.assertEqual(chat_detail(db, "synthetic-chat"), before)
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
