"""AUTH-004: manual enrollment cannot silently claim legacy data or owner role."""
import sqlite3
import tempfile
import unittest
from pathlib import Path

from chatidy.db import connect, upsert, chat_detail
from chatidy.enroll import enroll, main
from chatidy.users import enrolled_user


class EnrollmentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "synthetic.sqlite3"
        self.db = connect(self.path)
        upsert(self.db, [{"id": "synthetic", "title": "Synthetic data",
                          "messages": [{"id": "one", "role": "user",
                                        "content": "Synthetic secret-free chat"}]}])
        self.before = chat_detail(self.db, "synthetic")

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def test_explicit_owner_enrollment_preserves_legacy_content(self):
        issuer = "https://auth.example.invalid/application/o/test/"
        self.assertIsNone(enrolled_user(self.db, issuer, "synthetic-owner"))
        with self.assertRaisesRegex(ValueError, "Bestätigung"):
            enroll(self.db, issuer, "synthetic-owner", "owner")
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM users").fetchone()[0], 0)
        uid = enroll(self.db, issuer, "synthetic-owner", "owner", confirmed=True)
        self.assertEqual(enrolled_user(self.db, issuer, "synthetic-owner").id, uid)
        self.assertEqual(chat_detail(self.db, "synthetic"), self.before)
        # No newly introduced owner field exists on existing conversations.
        self.assertNotIn("user_id", self.before["chat"])

    def test_first_unknown_user_cannot_be_auto_enrolled_or_own(self):
        issuer = "https://auth.example.invalid/application/o/test/"
        enroll(self.db, issuer, "initial-owner", "owner", confirmed=True)
        with self.assertRaisesRegex(ValueError, "Eigentümerkonto"):
            enroll(self.db, issuer, "second-owner", "owner", confirmed=True)
        with self.assertRaisesRegex(ValueError, "bereits eingetragen"):
            enroll(self.db, issuer, "initial-owner", "member", confirmed=True)
        self.assertIsNone(enrolled_user(self.db, issuer, "stranger"))
        self.assertEqual(self.db.execute("SELECT count(*) FROM users").fetchone()[0], 1)

    def test_member_enrollment_is_separate_and_no_email_is_accepted(self):
        issuer = "https://auth.example.invalid/application/o/test/"
        enroll(self.db, issuer, "member-1", "member", confirmed=True)
        self.assertEqual(enrolled_user(self.db, issuer, "member-1").role, "member")
        for badissuer, badsub in (("http://unsafe.invalid", "x"), ("https://auth.invalid", ""),
                                  (" https://auth.invalid", "x"), ("https://auth.invalid", "space here")):
            with self.assertRaisesRegex(ValueError, "Ungültige"):
                enroll(self.db, badissuer, badsub, "member", confirmed=True)
        self.assertEqual(chat_detail(self.db, "synthetic"), self.before)

    def test_cli_requires_explicit_confirmation(self):
        with self.assertRaises(SystemExit) as caught:
            main(["--db", str(self.path), "--issuer", "https://auth.invalid",
                  "--subject", "synthetic", "--role", "owner"])
        self.assertEqual(caught.exception.code, 2)
        self.assertEqual(self.db.execute("SELECT count(*) FROM users").fetchone()[0], 0)


if __name__ == "__main__":
    unittest.main()
