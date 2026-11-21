"""Fixed-endpoint OIDC authorization-code exchange (no browser/session handlers).

HTTPS endpoints come from trusted application configuration, never from requests
or JWT headers. HTTP redirects are rejected; no access or refresh token stored.
"""
import json
from pathlib import Path
from .runtime_config import https_origin
import base64
import urllib.error
import urllib.parse
import urllib.request
from .oidc import OIDCError, OIDCSettings, verify_id_token

MAX_RESPONSE = 65536

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, url):
        return None


def exchange_code(settings, code, code_verifier, *, trusted_jwks, opener=None):
    settings.validate()
    if (not isinstance(code, str) or not code or len(code) > 4096
            or not isinstance(code_verifier, str) or not 43 <= len(code_verifier) <= 128):
        raise OIDCError("OIDC-Code oder PKCE-Verifier ungültig.")
    if not isinstance(settings.client_secret, str) or not settings.client_secret.strip():
        raise OIDCError("OIDC Confidential-Client-Secret fehlt.")
    # OAuth 2.0 section 2.3.1: form-encode credentials before HTTP Basic.
    # Never put the secret in a URL, form body, exception or log.
    encoded_id = urllib.parse.quote(settings.client_id, safe="")
    encoded_secret = urllib.parse.quote(settings.client_secret, safe="")
    credential = base64.b64encode(
        (encoded_id + ":" + encoded_secret).encode("utf-8")).decode("ascii")
    payload = urllib.parse.urlencode({
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": settings.redirect_uri,
        "code_verifier": code_verifier,
    }).encode("ascii")
    request = urllib.request.Request(
        settings.token_endpoint, data=payload, method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded",
                 "Accept": "application/json",
                 "Authorization": "Basic " + credential})
    transport = opener if opener is not None else urllib.request.build_opener(NoRedirect)
    try:
        with transport.open(request, timeout=12) as response:
            if response.status != 200:
                raise OIDCError("OIDC-Tokenantwort ungültig.")
            raw = response.read(MAX_RESPONSE + 1)
            if len(raw) > MAX_RESPONSE:
                raise OIDCError("OIDC-Tokenantwort zu groß.")
            answer = json.loads(raw)
        if not isinstance(answer, dict) or not isinstance(answer.get("id_token"), str):
            raise OIDCError("OIDC-ID-Token fehlt.")
        return answer["id_token"]
    except (OSError, urllib.error.URLError, json.JSONDecodeError,
            UnicodeDecodeError, ValueError, TypeError) as exc:
        raise OIDCError("OIDC-Code konnte nicht ausgetauscht werden.") from None


def configured_settings(environment):
    """Validate explicit standard OIDC endpoints; no provider-specific paths."""
    names = ("CHATIDY_OIDC_ISSUER", "CHATIDY_OIDC_AUTHORIZE",
             "CHATIDY_OIDC_TOKEN", "CHATIDY_OIDC_JWKS", "CHATIDY_OIDC_CLIENT_ID")
    if any(not environment.get(name) for name in names):
        raise OIDCError("OIDC-Konfiguration unvollständig.")
    origin = https_origin(environment.get("CHATIDY_PUBLIC_ORIGIN", ""))
    secret = environment.get("CHATIDY_OIDC_CLIENT_SECRET", "")
    secret_file = environment.get("CHATIDY_OIDC_CLIENT_SECRET_FILE", "")
    if secret and secret_file:
        raise OIDCError("Client-Secret entweder direkt oder als Datei konfigurieren.")
    if secret_file:
        try:
            with Path(secret_file).open("rb") as source:
                raw = source.read(8193)
            if len(raw) > 8192:
                raise ValueError
            secret = raw.decode("utf-8").rstrip("\r\n")
        except (OSError, ValueError, UnicodeError):
            raise OIDCError("OIDC-Client-Secret-Datei nicht lesbar oder ungültig.") from None
    if not secret or not secret.strip():
        raise OIDCError("OIDC-Client-Secret fehlt.")
    return OIDCSettings(*(environment[key] for key in names), origin + "/auth/callback",
                        client_secret=secret,
                        end_session_endpoint=environment.get("CHATIDY_OIDC_END_SESSION", "")).validate()


def load_trusted_jwks(settings, *, opener=None):
    """Retrieve keys only from fixed HTTPS JWKS URI and reject redirects."""
    settings.validate()
    request = urllib.request.Request(settings.jwks_uri,
                                     headers={"Accept": "application/json"})
    transport = opener if opener is not None else urllib.request.build_opener(NoRedirect)
    try:
        with transport.open(request, timeout=12) as response:
            if response.status != 200:
                raise OIDCError("OIDC-JWKS ungültig.")
            data = response.read(MAX_RESPONSE + 1)
            if len(data) > MAX_RESPONSE:
                raise OIDCError("OIDC-JWKS zu groß.")
        jwks = json.loads(data)
        if not isinstance(jwks, dict) or not isinstance(jwks.get("keys"), list):
            raise OIDCError("OIDC-JWKS ungültig.")
        return jwks
    except (OSError, urllib.error.URLError, ValueError,
            UnicodeError, TypeError) as exc:
        raise OIDCError("OIDC-Schlüssel konnten nicht geladen werden.") from None


def identity_from_code(settings, *, code, verifier, nonce, token_opener=None, jwks_opener=None):
    token = exchange_code(settings, code, verifier, trusted_jwks=None,
                          opener=token_opener)
    jwks = load_trusted_jwks(settings, opener=jwks_opener)
    return verify_id_token(token, jwks, issuer=settings.issuer,
                           audience=settings.client_id, nonce=nonce)
