"""Read-only mapping of a verified OIDC identity to an enrolled local account.

IMPORTANT: These helpers do NOT authenticate OIDC tokens, create accounts or grant
HTTP access. Call only after verifying the identity and the active app session.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class User:
    id: int
    oidc_issuer: str
    oidc_sub: str
    role: str
    display_name: str


def enrolled_user(db, issuer, subject):
    """Return an explicitly enrolled active user, never auto-provision one.

    E-mail and display name are deliberately not accepted as identifiers.
    The identity must already be cryptographically verified by the future
    OIDC layer. An unknown or disabled identity always resolves to None.
    """
    if (not isinstance(issuer, str) or not issuer
            or issuer != issuer.strip() or not isinstance(subject, str)
            or not subject or subject != subject.strip()):
        return None
    row = db.execute(
        """SELECT id,oidc_issuer,oidc_sub,role,display_name
           FROM users WHERE oidc_issuer=? AND oidc_sub=? AND status='active'""",
        (issuer, subject)).fetchone()
    return User(**dict(row)) if row is not None else None
