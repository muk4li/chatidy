"""AUTH-008: single-use browser-bound OIDC state and revocable local sessions."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from chatidy import auth_state

from chatidy.db import connect
from chatidy.users import enrolled_user
from chatidy.auth_state import (create_challenge, consume_challenge, issue_session,
                                 session_user, revoke_session)


class AuthStateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = connect(Path(self.temp.name) / "synthetic.sqlite3")
        with self.db:
            self.db.execute("INSERT INTO users(oidc_issuer,oidc_sub) VALUES(?,?)",
                            ("https://idp.example.invalid", "synthetic-subject"))
        self.user = enrolled_user(self.db, "https://idp.example.invalid", "synthetic-subject")
        self.state = "s" * 48
        self.browser = "b" * 48
        self.nonce = "n" * 48
        self.verifier = "v" * 64

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def test_challenge_is_bound_to_browser_and_single_use(self):
        create_challenge(self.db, state=self.state, browser_binding=self.browser,
                         nonce=self.nonce, code_verifier=self.verifier, now=100)
        row = self.db.execute("SELECT * FROM oidc_pending").fetchone()
        self.assertNotIn(self.state, dict(row).values())
        self.assertNotIn(self.browser, dict(row).values())
        self.assertIsNone(consume_challenge(self.db, state=self.state,
                                            browser_binding="x"*48, now=101))
        self.assertEqual(consume_challenge(self.db, state=self.state,
                         browser_binding=self.browser, now=101),
                         {"nonce":self.nonce,"code_verifier":self.verifier})
        self.assertIsNone(consume_challenge(self.db, state=self.state,
                                           browser_binding=self.browser, now=102))

    def test_expired_challenge_rejected(self):
        create_challenge(self.db, state=self.state,browser_binding=self.browser,
                         nonce=self.nonce,code_verifier=self.verifier,now=10)
        self.assertIsNone(consume_challenge(self.db,state=self.state,
                                            browser_binding=self.browser,now=611))

    def test_pending_login_limit_fails_closed_and_preserves_inflight_challenges(self):
        with patch.object(auth_state, "MAX_PENDING_CHALLENGES", 2):
            for index in range(2):
                create_challenge(self.db, state=str(index) * 48,
                                 browser_binding="b" * 48, nonce=self.nonce,
                                 code_verifier=self.verifier, now=100)
            with self.assertRaisesRegex(ValueError, "Zu viele"):
                create_challenge(self.db, state="z" * 48,
                                 browser_binding="c" * 48, nonce=self.nonce,
                                 code_verifier=self.verifier, now=101)
            self.assertEqual(self.db.execute("SELECT count(*) FROM oidc_pending").fetchone()[0], 2)
            self.assertEqual(consume_challenge(self.db, state="0"*48,
                             browser_binding="b"*48, now=102),
                             {"nonce":self.nonce,"code_verifier":self.verifier})
            create_challenge(self.db, state="z" * 48,
                             browser_binding="c" * 48, nonce=self.nonce,
                             code_verifier=self.verifier, now=103)
            self.assertEqual(self.db.execute("SELECT count(*) FROM oidc_pending").fetchone()[0], 2)
            # Once both remaining challenges expire, an attempt can proceed.
            create_challenge(self.db, state="n"*48, browser_binding="d"*48,
                             nonce=self.nonce, code_verifier=self.verifier, now=800)
            self.assertEqual(self.db.execute("SELECT count(*) FROM oidc_pending").fetchone()[0], 1)

    def test_session_lookup_revocation_expiry_and_disabled_account(self):
        token = issue_session(self.db, self.user, now=100)
        self.assertEqual(session_user(self.db, token, now=101).id,self.user.id)
        self.assertNotIn(token, [x[0] for x in self.db.execute("SELECT token_hash FROM auth_sessions")])
        self.assertIsNone(session_user(self.db, "not-a-real-token", now=101))
        with self.db:
            self.db.execute("UPDATE users SET status='disabled' WHERE id=?", (self.user.id,))
        self.assertIsNone(session_user(self.db, token, now=101))
        with self.assertRaisesRegex(ValueError,"nicht freigeschaltet"):
            issue_session(self.db,self.user,now=102)
        with self.db:
            self.db.execute("UPDATE users SET status='active' WHERE id=?", (self.user.id,))
        self.assertIsNone(session_user(self.db, token, now=100+12*3600))
        revoke_session(self.db, token)
        self.assertIsNone(session_user(self.db,token,now=101))

    def test_no_unknown_user_or_unverified_identity_claim(self):
        from chatidy.users import User
        with self.assertRaises(ValueError):
            issue_session(self.db, User(999,"https://idp.example.invalid","other","owner","synthetic"),now=100)


if __name__=="__main__":
    unittest.main()
