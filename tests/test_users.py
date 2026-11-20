"""AUTH-003: only pre-enrolled active users can resolve from verified iss+sub."""
import tempfile
import unittest
from pathlib import Path

from chatidy.db import connect
from chatidy.users import enrolled_user


class EnrolledUserTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = connect(Path(self.temp.name) / 'synthetic.sqlite3')

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def test_unknown_user_does_not_register_or_get_access(self):
        self.assertIsNone(enrolled_user(self.db, "https://idp.example.invalid", "subject"))
        self.assertEqual(self.db.execute("SELECT count(*) FROM users").fetchone()[0], 0)

    def test_exact_issuer_and_subject_and_active_status_required(self):
        with self.db:
            self.db.execute(
                "INSERT INTO users(oidc_issuer,oidc_sub,email,role,display_name) VALUES(?,?,?,?,?)",
                ("https://idp.example.invalid", "user-a", "shared@example.invalid", "owner", "Synthetic A"))
            self.db.execute(
                "INSERT INTO users(oidc_issuer,oidc_sub,email,status) VALUES(?,?,?,?)",
                ("https://idp.example.invalid", "user-b", "shared@example.invalid", "disabled"))
        owner = enrolled_user(self.db, "https://idp.example.invalid", "user-a")
        self.assertIsNotNone(owner)
        self.assertEqual(owner.role, "owner")
        self.assertEqual(owner.display_name, "Synthetic A")
        self.assertIsNone(enrolled_user(self.db, "https://other-idp.example.invalid", "user-a"))
        self.assertIsNone(enrolled_user(self.db, "https://idp.example.invalid", "user-b"))
        self.assertIsNone(enrolled_user(self.db, "https://idp.example.invalid", "shared@example.invalid"))
        self.assertIsNone(enrolled_user(self.db, "https://idp.example.invalid", "USER-A"))

    def test_rejects_missing_and_untrusted_identifiers(self):
        for identity in ((None, "x"), ("x", None), ("", "x"), ("x", ""),
                         (" https://idp.example.invalid", "x"),
                         ("https://idp.example.invalid", "x "),
                         (1, "x"), ("x", 1)):
            self.assertIsNone(enrolled_user(self.db, *identity))
        self.assertEqual(self.db.execute("SELECT count(*) FROM users").fetchone()[0], 0)


if __name__ == "__main__":
    unittest.main()
