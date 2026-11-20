"""Pure routing contract for a future authenticated Chatidy server.

This module does NOT enforce HTTP access. Handler integration must occur in
the dedicated OIDC/security PR, with verified sessions and negative tests.
"""
from urllib.parse import unquote, urlsplit


def private_route(url):
    """True for every existing user-data/API namespace and the library UI."""
    if not isinstance(url, str):
        raise ValueError("Ungültiger URL-Pfad.")
    path = unquote(urlsplit(url).path)
    return (path == "/app" or path.startswith("/app/")
            or path == "/api" or path.startswith("/api/"))


def public_route(url):
    """Allowlist only; unknown and future URLs are NOT auto-public."""
    if not isinstance(url, str):
        raise ValueError("Ungültiger URL-Pfad.")
    path = unquote(urlsplit(url).path)
    return path in ("/", "/landing.css", "/login", "/auth/callback")


def is_allowed_without_login(url):
    """Future HTTP access decision must fail closed for unknown routes."""
    return public_route(url) and not private_route(url)
