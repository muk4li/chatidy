"""Descriptor-relative local job storage. Never follow symlinks during cleanup.

POSIX locks are shared by workers, status inspection and deletion across server
processes. No recursive deletion or user-supplied filesystem paths are accepted.
"""
import json
import os
import re
import stat
from contextlib import contextmanager
from pathlib import Path
try:
    import fcntl
except ImportError:  # Fail closed instead of providing an unsafe deletion fallback.
    fcntl = None

ID = re.compile(r'[a-f0-9]{32}')
FILES = frozenset(('status.json', 'status.tmp', 'source.json', 'source.zip',
                   'staging.sqlite3', 'staging.sqlite3-journal', 'staging.sqlite3-wal',
                   'staging.sqlite3-shm', 'job.lock', 'deletion.json'))


def validate_id(value):
    if not isinstance(value, str) or not ID.fullmatch(value):
        raise ValueError('Ungültige Importjob-ID.')
    return value


def root_path():
    configured = os.getenv('CHATIDY_DB', 'data/chatidy.sqlite3')
    if os.name == 'nt':
        drive, tail = os.path.splitdrive(configured)
        if drive and (len(drive) != 2 or not tail.startswith(('\\', '/'))):
            raise ValueError('Keine UNC-, Geräte- oder laufwerksrelativen Importjob-Pfade erlaubt.')
    return Path(os.path.abspath(configured)).parent / 'import-jobs'


def directory(name, parent=None):
    fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
    return fd


def regular(fd):
    info = os.fstat(fd)
    if not stat.S_ISREG(info.st_mode) or info.st_nlink > 1 or info.st_uid != os.getuid():
        raise ValueError('Unsichere Importjob-Datei: nur eigene reguläre Dateien ohne Hardlinks erlaubt.')
    return info


def file_open(parent, name, flags=os.O_RDONLY):
    if name not in FILES and name != 'management.lock':
        raise ValueError('Unbekannte Importjob-Datei.')
    fd = os.open(name, flags | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600, dir_fd=parent)
    try:
        regular(fd)
        return fd
    except BaseException:
        os.close(fd)
        raise


def private_directory(fd):
    info = os.fstat(fd)
    if info.st_uid != os.getuid() or info.st_mode & 0o022:
        raise ValueError('Importjob-Verzeichnis muss dem aktuellen Benutzer gehören und schreibgeschützt für andere sein.')


@contextmanager
def root(create=False):
    if (fcntl is None or not hasattr(os, 'O_NOFOLLOW') or os.open not in os.supports_dir_fd):
        raise ValueError('Sichere Importjobs benötigen POSIX-Dateisperren und dir_fd-Unterstützung.')
    fd = directory('/')
    try:
        try:
            for component in root_path().parts[1:]:
                if create:
                    try:
                        os.mkdir(component, 0o700, dir_fd=fd)
                    except FileExistsError:
                        pass
                next_fd = directory(component, fd)
                os.close(fd)
                fd = next_fd
                info = os.fstat(fd)
                if info.st_mode & 0o022 and not info.st_mode & stat.S_ISVTX:
                    raise ValueError('Unsicheres übergeordnetes Importjob-Verzeichnis: für andere schreibbar.')
            private_directory(fd)
        except OSError as exc:
            raise ValueError('Importjob-Verzeichnis fehlt oder ist unsicher. Pfade und Symlinks prüfen.') from exc
        yield fd
    finally:
        os.close(fd)


@contextmanager
def registry(root_fd):
    try:
        fd = file_open(root_fd, 'management.lock', os.O_RDWR | os.O_CREAT)
    except OSError as exc:
        raise ValueError('Unsichere Sperrdatei im Importjob-Verzeichnis.') from exc
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        os.close(fd)


class Job:
    def __init__(self, parent, name):
        validate_id(name.removeprefix('.deleting-'))
        self.fd = directory(name, parent)
        self.name = name
        try:
            private_directory(self.fd)
        except BaseException:
            os.close(self.fd)
            raise

    def close(self):
        os.close(self.fd)

    def entries(self, ignore_missing=False):
        result = {}
        for name in os.listdir(self.fd):
            if name not in FILES:
                raise ValueError('Unbekannte Datei im Importjob. Keine Bereinigung durchgeführt.')
            try:
                fd = file_open(self.fd, name)
            except FileNotFoundError:
                if ignore_missing:
                    continue
                raise
            try:
                result[name] = regular(fd)
            finally:
                os.close(fd)
        return result

    def read(self, name):
        fd = file_open(self.fd, name)
        with os.fdopen(fd, encoding='utf-8') as source:
            if os.fstat(source.fileno()).st_size > 65536:
                raise ValueError('Importjob-Statusdatei ist zu groß.')
            return json.load(source)

    def write(self, name, value):
        if name not in ('status.json', 'deletion.json'):
            raise ValueError('Ungültige Importjob-Statusdatei.')
        # A fixed temporary file is safe because the caller holds the job lease
        # (or registry lock). Validate before truncation, including hardlinks.
        fd = file_open(self.fd, 'status.tmp', os.O_WRONLY | os.O_CREAT)
        with os.fdopen(fd, 'w', encoding='utf-8') as target:
            os.ftruncate(target.fileno(), 0)
            json.dump(value, target)
            target.flush()
            os.fsync(target.fileno())
        os.replace('status.tmp', name, src_dir_fd=self.fd, dst_dir_fd=self.fd)
        os.fsync(self.fd)

    def acquire(self):
        fd = file_open(self.fd, 'job.lock', os.O_RDWR | os.O_CREAT)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return fd
        except BlockingIOError:
            os.close(fd)
            return None
        except BaseException:
            os.close(fd)
            raise

    def sqlite_path(self):
        # Pin the directory even if an administrator renames a parent. SQLite
        # needs a filename for its journal; all allowed sidecars are preflighted.
        if not Path('/proc/self/fd').is_dir():
            raise ValueError('Import-Staging benötigt auf diesem System /proc/self/fd.')
        return f'/proc/self/fd/{self.fd}/staging.sqlite3'

# The job lifecycle uses only these filesystem primitives. Keep the POSIX
# descriptor-relative backend; select native handles explicitly on Windows.
def mkdir(parent, name):
    validate_id(name)
    os.mkdir(name, 0o700, dir_fd=parent)


def listdir(parent):
    return os.listdir(parent)


def stat_entry(parent, name):
    return os.stat(name, dir_fd=parent, follow_symlinks=False)


def rename_job(job, parent, name):
    validate_id(name.removeprefix('.deleting-'))
    os.rename(job.name, name, src_dir_fd=parent, dst_dir_fd=parent)
    job.name = name


def unlink(job, name):
    if name not in FILES:
        raise ValueError('Unbekannte Importjob-Datei.')
    os.unlink(name, dir_fd=job.fd)


def remove_job(job, parent, name):
    os.rmdir(name, dir_fd=parent)


def sync(parent):
    os.fsync(parent)


def prepare_delete(job, lease):
    return lease


def path_identity(path):
    info = path.stat()
    return info.st_dev, info.st_ino


if os.name == 'nt':
    from .windows_job_storage import (root, registry, file_open, Job, mkdir,
        listdir, stat_entry, rename_job, unlink, remove_job, sync, path_identity, prepare_delete)
