"""AUTH-012: explicit migration with fake chat data and zero OIDC/session leak."""
import tempfile
import unittest
from pathlib import Path
from contextlib import closing
from chatidy.db import connect,upsert,create_folder,assign,chat_detail
from chatidy.organisation import apply_tags
from chatidy.migrate_owner import copy_legacy
from chatidy.library_scope import account_database_path
from chatidy.users import User

class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory()
        self.source=Path(self.t.name)/"legacy.sqlite3"
        with closing(connect(self.source)) as db:
            with db:
                db.execute("INSERT INTO users(oidc_issuer,oidc_sub,role) VALUES(?,?,?)",
                           ("https://synthetic.invalid","owner","owner"))
            upsert(db,[{"id":"synthetic-chat","title":"Synthetic title",
                        "messages":[{"id":"m","role":"user","content":"Synthetic body"}]}])
            fid=create_folder(db,"Synthetic custom folder")
            assign(db,"synthetic-chat",[fid])
            apply_tags(db,["synthetic-chat"],["synthetic-tag"])
            self.original=chat_detail(db,"synthetic-chat")
    def tearDown(self):self.t.cleanup()

    def test_explicit_confirmation_and_owner_required(self):
        with self.assertRaises(ValueError):
            copy_legacy(self.source,1)
        with self.assertRaises(ValueError):
            copy_legacy(self.source,999,confirmed=True,server_stopped=True)
        self.assertFalse((Path(self.t.name)/"accounts"/"999"/"chatidy.sqlite3").exists())

    def test_backup_preserve_identity_isolation_and_idempotent_refusal(self):
        result=copy_legacy(self.source,1,confirmed=True,server_stopped=True)
        self.assertEqual(result["conversations"],1)
        target=Path(self.t.name)/"accounts"/"1"/"chatidy.sqlite3"
        backup=Path(self.t.name)/"backups"/"chatidy-before-owner-migration-1.sqlite3"
        self.assertTrue(target.exists())
        self.assertTrue(backup.exists())
        with closing(connect(target)) as account:
            self.assertEqual(chat_detail(account,"synthetic-chat"),self.original)
            self.assertEqual(account.execute("SELECT count(*) FROM users").fetchone()[0],0)
            self.assertEqual(account.execute("SELECT count(*) FROM auth_sessions").fetchone()[0],0)
        with closing(connect(self.source)) as legacy:
            self.assertEqual(chat_detail(legacy,"synthetic-chat"),self.original)
        with self.assertRaises(ValueError):
            copy_legacy(self.source,1,confirmed=True,server_stopped=True)

    def test_member_cannot_receive_legacy_data(self):
        with closing(connect(self.source)) as db:
            with db:
                db.execute("INSERT INTO users(oidc_issuer,oidc_sub,role) VALUES(?,?,?)",
                           ("https://synthetic.invalid","member","member"))
        with self.assertRaises(ValueError):
            copy_legacy(self.source,2,confirmed=True,server_stopped=True)

if __name__=="__main__":unittest.main()
