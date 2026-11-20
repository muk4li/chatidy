from contextlib import contextmanager
from contextvars import ContextVar
import os
from pathlib import Path
import stat

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

def _prepare_account_database(target):
    """Provision a private account directory and DB without following symlinks.

    POSIX enforces owner-only bits. Windows account ACL/junction policy still
    requires a separate native security review before any remote deployment.
    """
    for directory in (target.parent.parent, target.parent):
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        info = directory.lstat()
        if not stat.S_ISDIR(info.st_mode):
            raise ValueError("Konto-Speicherpfad ist kein reguläres Verzeichnis.")
        if os.name != "nt" and (info.st_uid != os.getuid() or info.st_mode & 0o077):
            raise ValueError("Konto-Verzeichnis muss privat und im Besitz des Prozesses sein.")
    flags = os.O_CREAT | os.O_EXCL | os.O_RDWR
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(target, flags, 0o600)
    except FileExistsError:
        pass
    else:
        os.close(fd)
    info = target.lstat()
    if not stat.S_ISREG(info.st_mode):
        raise ValueError("Konto-Datenbank ist keine reguläre Datei.")
    if os.name != "nt" and (info.st_uid != os.getuid() or info.st_nlink != 1 or info.st_mode & 0o077):
        raise ValueError("Konto-Datenbank muss eine private reguläre Datei sein.")

@contextmanager
def account_library(user, registry_path):
    """Only use after verifying an explicitly enrolled active identity."""
    target = account_database_path(user, registry_path)
    _prepare_account_database(target)
    token = _CURRENT.set(target)
    try:
        yield target
    finally:
        _CURRENT.reset(token)
