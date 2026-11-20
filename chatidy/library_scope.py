"""Trusted per-account storage context; NOT an authentication mechanism."""
from contextlib import contextmanager
from contextvars import ContextVar
import os
from pathlib import Path

from .users import User

_CURRENT = ContextVar("chatidy_account_database", default=None)

def scoped_database():
    return _CURRENT.get()

def account_database_path(user, registry_path):
    if not isinstance(user, User) or type(user.id) is not int or user.id <= 0:
        raise ValueError("Ungültiger interner Benutzerkontext.")
    if not isinstance(registry_path, (str, os.PathLike)):
        raise ValueError("Ungültiger Registry-Pfad.")
    root = Path(os.path.abspath(registry_path)).parent
    return root / "accounts" / str(user.id) / "chatidy.sqlite3"

@contextmanager
def account_library(user, registry_path):
    """Only use with a previously verified/enrolled User on the server."""
    target = account_database_path(user, registry_path)
    token = _CURRENT.set(target)
    try:
        yield target
    finally:
        _CURRENT.reset(token)
