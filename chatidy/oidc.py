"""OIDC protocol primitives, not an HTTP login or a session implementation.

The OPTIONAL pinned auth dependencies are only required when using this module.
No token or credentials are logged or stored. Callers must keep authorization
state/nonce/code verifier in a server-side, single-use, expiring state record.
"""
import base64
import hashlib
import hmac
import json
import secrets
from urllib.parse import urlencode, urlsplit
from dataclasses import dataclass

import jwt


class OIDCError(ValueError):
    """Safe, generic failure without exposing credentials."""


def _https_url(url):
    if not isinstance(url, str) or not url.startswith("https://"):
        raise OIDCError("OIDC-Konfiguration benötigt HTTPS.")
    parsed = urlsplit(url)
    if not parsed.hostname or parsed.username or parsed.password or parsed.fragment:
        raise OIDCError("Ungültiger OIDC-Endpunkt.")
    return parsed


@dataclass(frozen=True)
class OIDCSettings:
    issuer: str
    authorization_endpoint: str
    token_endpoint: str
    jwks_uri: str
    client_id: str
    redirect_uri: str

    def validate(self):
        issuer = _https_url(self.issuer)
        if not self.client_id or not self.client_id.strip():
            raise OIDCError("OIDC-Client-ID fehlt.")
        for name in ("authorization_endpoint", "token_endpoint", "jwks_uri"):
            endpoint = _https_url(getattr(self, name))
            if endpoint.hostname != issuer.hostname or endpoint.port != issuer.port:
                raise OIDCError("OIDC-Endpunkt außerhalb des konfigurierten Identity-Providers.")
        _https_url(self.redirect_uri)
        return self


def new_login_challenge():
    """Unpredictable state, nonce and RFC7636 verifier; store only server-side."""
    return (secrets.token_urlsafe(32), secrets.token_urlsafe(32),
            secrets.token_urlsafe(48))


def authorization_url(settings, state, nonce, verifier):
    settings.validate()
    if not all(isinstance(x, str) and len(x) >= 32 for x in (state, nonce, verifier)):
        raise OIDCError("OIDC-Zustandsdaten fehlen.")
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest()).rstrip(b"=").decode("ascii")
    return settings.authorization_endpoint + ("&" if "?" in settings.authorization_endpoint else "?") + urlencode({
        "client_id": settings.client_id, "redirect_uri": settings.redirect_uri,
        "response_type": "code", "scope": "openid profile email", "state": state,
        "nonce": nonce, "code_challenge": challenge, "code_challenge_method": "S256"
    })


def verify_id_token(raw_token, trusted_jwks, *, issuer, audience, nonce):
    """Verify an RS256 ID token against trusted fixed-provider JWKS.

    JWKS must come from a configured HTTPS endpoint, never from JWT header URLs.
    No PyJWKClient and no network request based on an untrusted 'kid'.
    """
    if not isinstance(raw_token, str) or len(raw_token) > 16384:
        raise OIDCError("OIDC-ID-Token ungültig.")
    if not isinstance(trusted_jwks, dict) or not isinstance(trusted_jwks.get("keys"), list) or len(trusted_jwks["keys"]) > 32:
        raise OIDCError("OIDC-Schlüsselliste ungültig.")
    try:
        header = jwt.get_unverified_header(raw_token)
        if header.get("alg") != "RS256":
            raise OIDCError("OIDC-Signaturalgorithmus nicht erlaubt.")
        kid = header.get("kid")
        if not isinstance(kid, str) or not 0 < len(kid) <= 128:
            raise OIDCError("OIDC-Key-ID ungültig.")
        keys = [key for key in trusted_jwks["keys"] if isinstance(key, dict)
                and key.get("kid") == kid and key.get("kty") == "RSA"
                and key.get("use", "sig") == "sig"
                and key.get("alg", "RS256") == "RS256"]
        if len(keys) != 1:
            raise OIDCError("OIDC-Signaturschlüssel nicht eindeutig.")
        key = jwt.PyJWK.from_dict(keys[0], algorithm="RS256").key
        claims = jwt.decode(raw_token, key, algorithms=["RS256"],
                            audience=audience, issuer=issuer, leeway=30,
                            options={"require": ["iss", "sub", "aud", "exp", "iat", "nonce"]})
        if not isinstance(claims.get("sub"), str) or not claims["sub"]:
            raise OIDCError("OIDC-Subjekt fehlt.")
        if not isinstance(nonce, str) or not hmac.compare_digest(str(claims["nonce"]), nonce):
            raise OIDCError("OIDC-Nonce ungültig.")
        if isinstance(claims.get("aud"), list) and len(claims["aud"]) > 1 and claims.get("azp") != audience:
            raise OIDCError("OIDC-autorisierte Partei ungültig.")
        return {"issuer": claims["iss"], "subject": claims["sub"]}
    except (jwt.PyJWTError, ValueError, TypeError, KeyError, UnicodeError) as exc:
        raise OIDCError("OIDC-ID-Token konnte nicht verifiziert werden.") from None
