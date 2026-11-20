"""AUTH-005: account-specific DB and job-root isolation (synthetic only)."""
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from contextlib import closing
from unittest.mock import patch

from chatidy.db import connect, chat_detail, upsert
from chatidy.users import User
from chatidy.library_scope import account_library, account_database_path, scoped_database
from chatidy.job_storage import root_path
from chatidy import jobs


def user(number):
    return User(number, "https://idp.example.invalid", "subject-" + str(number), "member", "Synthetic")


class AccountLibraryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.registry = Path(self.tmp.name) / "registry.sqlite3"
    def tearDown(self):
        self.tmp.cleanup()

    def test_two_accounts_same_external_chat_id_stay_separate(self):
        with patch.dict(os.environ, CHATIDY_DB=str(self.registry)):
            with closing(connect()) as db:
                self.assertEqual(db.execute("SELECT count(*) FROM conversations").fetchone()[0], 0)
            for n in (1, 2):
                with account_library(user(n), self.registry) as path:
                    self.assertEqual(scoped_database(), path)
                    self.assertEqual(root_path(), path.parent / "import-jobs")
                    with closing(connect()) as db:
                        upsert(db, [{"id":"same","title":"Synthetic "+str(n),
                            "messages":[{"id":"same-message","role":"user","content":"Account "+str(n)}]}])
            for n in (1, 2):
                with account_library(user(n), self.registry):
                    with closing(connect()) as db:
                        self.assertEqual(chat_detail(db, "same")["chat"]["title"], "Synthetic "+str(n))
            with closing(connect()) as db:
                self.assertIsNone(chat_detail(db, "same"))
        self.assertIsNone(scoped_database())

    def test_bad_identity_cannot_select_arbitrary_paths(self):
        for bad in (None, "1", 0, -1, True):
            with self.assertRaises(ValueError):
                account_database_path(bad, self.registry)
        self.assertEqual(account_database_path(user(1), self.registry),
                         self.registry.parent / "accounts" / "1" / "chatidy.sqlite3")

    def test_job_worker_inherits_account_context(self):
        payload = json.dumps([{"id":"synthetic","title":"Synthetic upload",
                               "messages":[{"role":"user","content":"Synthetic body"}]}]).encode()
        with patch.dict(os.environ, CHATIDY_DB=str(self.registry)):
            with account_library(user(1), self.registry):
                job_id = jobs.create(io.BytesIO(payload), len(payload), "synthetic.json")
                worker = jobs.start(job_id)
                worker.join(timeout=15)
                self.assertFalse(worker.is_alive())
                self.assertEqual(jobs.status(job_id)["state"], "done")
                with closing(connect()) as db:
                    self.assertIsNotNone(chat_detail(db, "synthetic"))
            with account_library(user(2), self.registry):
                self.assertEqual(jobs.listing()["count"], 0)
                with closing(connect()) as db:
                    self.assertIsNone(chat_detail(db, "synthetic"))

if __name__ == "__main__":
    unittest.main()
