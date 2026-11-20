"""Server-side, one-time OIDC challenge and revocable session primitives.

NOT an HTTP login or an OIDC token verifier. Only the future callback handler
may consume a pending challenge after matching a browser-bound cookie, and only
a verified, enrolled user may be passed to issue_session.
"""
import hashlib
import secrets
import time

from .users import User

CHALLENGE_SECONDS = 600
SESSION_SECONDS = 12 * 60 * 60


def _digest(value):
    if not isinstance(value, str) or len(value) < 32 or len(value) > 512:
        raise ValueError("Ungültiges Sitzungstoken.")
    return hashlib.sha256(value.encode("ascii")).hexdigest()


def create_challenge(db, *, state, browser_binding, nonce, code_verifier, now=None):
    at = time.time() if now is None else now
    if not isinstance(nonce, str) or len(nonce) < 32 or not isinstance(code_verifier, str) or len(code_verifier) < 32:
        raise ValueError("Ungültige OIDC-Challenge.")
    with db:
        db.execute("DELETE FROM oidc_pending WHERE expires_at <= ?", (at,))
        db.execute("""INSERT INTO oidc_pending(state_hash,browser_hash,nonce,code_verifier,expires_at)
                      VALUES(?,?,?,?,?)""",
                   (_digest(state), _digest(browser_binding), nonce, code_verifier, at + CHALLENGE_SECONDS))


def consume_challenge(db, *, state, browser_binding, now=None):
    at = time.time() if now is None else now
    state_hash = _digest(state)
    browser_hash = _digest(browser_binding)
    with db:
        db.execute("BEGIN IMMEDIATE")
        record = db.execute("""SELECT browser_hash,nonce,code_verifier,expires_at
                                FROM oidc_pending WHERE state_hash=?""", (state_hash,)).fetchone()
        if record is None or record["browser_hash"] != browser_hash or record["expires_at"] <= at:
            return None
        db.execute("DELETE FROM oidc_pending WHERE state_hash=?", (state_hash,))
        return {"nonce": record["nonce"], "code_verifier": record["code_verifier"]}


def issue_session(db, user, *, now=None):
    """Must only be called after OIDC signature verification and enrollment."""
    if not isinstance(user, User) or type(user.id) is not int or user.id <= 0:
        raise ValueError("Ungültiger Konto-Kontext.")
    at = time.time() if now is None else now
    record = db.execute("SELECT 1 FROM users WHERE id=? AND oidc_issuer=? AND oidc_sub=? AND status='active'",
                        (user.id, user.oidc_issuer, user.oidc_sub)).fetchone()
    if record is None:
        raise ValueError("Konto nicht freigeschaltet.")
    token = secrets.token_urlsafe(48)
    with db:
        db.execute("DELETE FROM auth_sessions WHERE expires_at <= ?", (at,))
        db.execute("INSERT INTO auth_sessions(token_hash,user_id,created_at,expires_at) VALUES(?,?,?,?)",
                   (_digest(token), user.id, at, at + SESSION_SECONDS))
    return token


def session_user(db, token, *, now=None):
    try:
        token_hash = _digest(token)
    except (ValueError, UnicodeError):
        return None
    at = time.time() if now is None else now
    record = db.execute(
        """SELECT u.id,u.oidc_issuer,u.oidc_sub,u.role,u.display_name
           FROM auth_sessions s JOIN users u ON u.id=s.user_id
           WHERE s.token_hash=? AND s.expires_at>? AND u.status='active'""",
        (token_hash, at)).fetchone()
    return User(**dict(record)) if record is not None else None


def revoke_session(db, token):
    try:
        token_hash = _digest(token)
    except (ValueError, UnicodeError):
        return
    with db:
        db.execute("DELETE FROM auth_sessions WHERE token_hash=?", (token_hash,))
