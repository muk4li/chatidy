"""Native Windows storage: local NTFS, private ACLs, pinned non-reparse paths.

No POSIX emulation, WSL or /proc fallback. All ancestors remain pinned while a
job uses normal SQLite filenames. Lifecycle operations share byte-range locks.
"""
import errno
import json
import msvcrt
import os
import time
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from . import windows_handles as win
from .job_storage import FILES, validate_id, root_path


class PinnedDirectory:
    def __init__(self, path, parents=()):
        self.path = Path(path)
        self.parents = []
        self.handle = None
        try:
            for handle in parents:
                self.parents.append(win.duplicate(handle))
            self.handle = win.open_handle(self.path, 0x80 | 1, share=win.SHARE_PIN, directory=True)
        except BaseException:
            self.close()
            raise

    def close(self):
        if self.handle is not None:
            win.Close(self.handle)
            self.handle = None
        for handle in self.parents:
            win.Close(handle)
        self.parents = []

    def deletion_handle(self):
        # Upgrade without ever acting on an unverified replacement object. The
        # registry lock excludes other Chatidy lookups during this short gap.
        previous = win.identity(self.handle)
        win.Close(self.handle)
        self.handle = None
        handle = win.open_handle(self.path, win.DELETE | 0x80 | 1,
                                 share=win.SHARE_PIN, directory=True)
        try:
            if win.identity(handle) != previous:
                raise ValueError('Importjob-Verzeichnis wurde ersetzt. Vorgang abgebrochen.')
        except BaseException:
            win.Close(handle)
            raise
        self.handle = handle


def _create_directory(path):
    with win.private_attributes() as attributes:
        win.checked(win.CreateDirectory(str(path), win.c.byref(attributes)))


@contextmanager
def root(create=False):
    target = root_path()
    win.validate_volume(target)
    pins = []
    try:
        path = Path(target.anchor)
        pins.append(win.open_handle(path, 0x80 | 1, share=win.SHARE_PIN, directory=True))
        for component in target.parts[1:]:
            path = path / component
            try:
                handle = win.open_handle(path, 0x80 | 1, share=win.SHARE_PIN, directory=True)
            except FileNotFoundError:
                if not create:
                    raise
                try:
                    _create_directory(path)
                except FileExistsError:
                    pass
                handle = win.open_handle(path, 0x80 | 1, share=win.SHARE_PIN, directory=True)
            pins.append(handle)
        win.check_acl(pins[-1])
        guard = PinnedDirectory(target, pins)
        try:
            yield guard
        finally:
            guard.close()
    except OSError as exc:
        raise ValueError('Windows-Importjob-Pfad nicht verfügbar. NTFS, Berechtigungen und offene Dateihandles prüfen.') from exc
    finally:
        for handle in pins:
            win.Close(handle)


def _filename(parent, name):
    if name not in FILES and name != 'management.lock':
        raise ValueError('Unbekannte Importjob-Datei.')
    return parent.path / name


def file_open(parent, name, flags=os.O_RDONLY):
    path = _filename(parent, name)
    access = 0x80000000
    if flags & os.O_RDWR:
        access |= 0x40000000
    elif flags & os.O_WRONLY:
        access = 0x40000000
    disposition = win.OPEN_EXISTING
    if flags & os.O_CREAT:
        disposition = win.CREATE_NEW if flags & os.O_EXCL else win.OPEN_ALWAYS
    handle = win.open_handle(path, access, disposition=disposition)
    try:
        win.check_acl(handle)
        descriptor = msvcrt.open_osfhandle(handle, (flags & (os.O_WRONLY | os.O_RDWR)) | os.O_BINARY | os.O_NOINHERIT)
    except BaseException:
        win.Close(handle)
        raise
    # open_osfhandle now owns the native handle; os.close releases it.
    return descriptor


def _lock(fd, blocking=False):
    # LockFile regions may extend beyond EOF; keep the empty coordination file.
    while True:
        os.lseek(fd, 0, os.SEEK_SET)
        try:
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            return True
        except OSError as exc:
            if exc.errno not in (errno.EACCES, errno.EAGAIN, errno.EDEADLK):
                raise
            if not blocking:
                return False
            time.sleep(.02)


@contextmanager
def registry(parent):
    fd = file_open(parent, 'management.lock', os.O_RDWR | os.O_CREAT)
    try:
        _lock(fd, blocking=True)
        yield
    finally:
        os.close(fd)


def mkdir(parent, name):
    validate_id(name)
    _create_directory(parent.path / name)


def listdir(parent):
    return os.listdir(parent.path)


def _entry(handle):
    info = win.information(handle)
    return SimpleNamespace(st_dev=info.volume, st_ino=(info.index_high << 32) | info.index_low,
                           st_size=(info.size_high << 32) | info.size_low, st_nlink=info.links)


def path_identity(path):
    handle = win.open_handle(path, 0x80)
    try:
        info = _entry(handle)
        return info.st_dev, info.st_ino
    finally:
        win.Close(handle)


def stat_entry(parent, name):
    if name not in FILES:
        validate_id(name.removeprefix('.deleting-'))
        handle = win.open_handle(parent.path / name, 0x80, directory=True)
        try:
            return _entry(handle)
        finally:
            win.Close(handle)
    fd = file_open(parent, name)
    try:
        return _entry(msvcrt.get_osfhandle(fd))
    finally:
        os.close(fd)


class Job:
    def __init__(self, parent, name):
        validate_id(name.removeprefix('.deleting-'))
        self.name = name
        self.fd = PinnedDirectory(parent.path / name, [*parent.parents, parent.handle])
        try:
            win.check_acl(self.fd.handle)
        except BaseException:
            self.close()
            raise

    def close(self):
        self.fd.close()

    def entries(self, ignore_missing=False):
        entries = {}
        for name in listdir(self.fd):
            if name not in FILES:
                raise ValueError('Unbekannte Datei im Importjob. Keine Bereinigung durchgeführt.')
            try:
                fd = file_open(self.fd, name)
            except FileNotFoundError:
                if ignore_missing:
                    continue
                raise
            try:
                entries[name] = _entry(msvcrt.get_osfhandle(fd))
            finally:
                os.close(fd)
        return entries

    def read(self, name):
        fd = file_open(self.fd, name)
        with os.fdopen(fd, encoding='utf-8') as source:
            if os.fstat(source.fileno()).st_size > 65536:
                raise ValueError('Importjob-Statusdatei ist zu groß.')
            return json.load(source)

    def write(self, name, value):
        if name not in ('status.json', 'deletion.json'):
            raise ValueError('Ungültige Importjob-Statusdatei.')
        fd = file_open(self.fd, 'status.tmp', os.O_WRONLY | os.O_CREAT)
        with os.fdopen(fd, 'w', encoding='utf-8') as target:
            os.ftruncate(target.fileno(), 0)
            json.dump(value, target)
            target.flush()
            os.fsync(target.fileno())
        # The source and destination directory cannot move. Readers use
        # FILE_SHARE_DELETE; MoveFileEx replaces a complete status atomically.
        try:
            destination = file_open(self.fd, name)
        except FileNotFoundError:
            pass
        else:
            os.close(destination)
        win.checked(win.MoveFile(str(self.fd.path / 'status.tmp'), str(self.fd.path / name), 1 | 8))

    def acquire(self):
        fd = file_open(self.fd, 'job.lock', os.O_RDWR | os.O_CREAT)
        try:
            if _lock(fd):
                return fd
            os.close(fd)
            return None
        except BaseException:
            os.close(fd)
            raise

    def sqlite_path(self):
        # Native SQLite opens its regular filename. Private ACLs and pinned
        # ancestors protect it; the process-wide job lease protects sidecars.
        return str(self.fd.path / 'staging.sqlite3')


def prepare_delete(job, lease):
    # Windows directory renames can fail while a child file is open, including
    # the lock file. The caller already proved no worker owns the lease and
    # holds the registry lock for the ENTIRE cleanup, so releasing this cleanup
    # lease cannot let a worker start. Keep all ancestor pins intact.
    os.close(lease)
    return None


def rename_job(job, parent, name):
    validate_id(name.removeprefix('.deleting-'))
    # MoveFileEx is the documented Win32 directory rename operation. Temporarily
    # release only this leaf pin (the entire ancestor chain stays pinned and the
    # registry/job locks remain held). No contents are removed until the renamed
    # directory is re-pinned and its native file identity has been verified.
    previous = win.identity(job.fd.handle)
    win.Close(job.fd.handle)
    job.fd.handle = None
    target = parent.path / name
    win.checked(win.MoveFile(str(job.fd.path), str(target), 8))
    job.fd.path, job.name = target, name
    job.fd.handle = win.open_handle(target, 0x80 | 1, share=win.SHARE_PIN, directory=True)
    if win.identity(job.fd.handle) != previous:
        raise ValueError('Importjob-Verzeichnis wurde beim Umbenennen ersetzt. Keine Dateien gelöscht.')


def unlink(job, name):
    path = _filename(job.fd, name)
    handle = win.open_handle(path, win.DELETE | 0x80)
    try:
        win.check_acl(handle)
        win.mark_delete(handle)
    finally:
        win.Close(handle)


def remove_job(job, parent, name):
    if job.name != name:
        raise ValueError('Ungültiges Bereinigungsziel.')
    # A resumed cleanup has a read pin; a newly renamed cleanup already holds
    # DELETE access. Upgrade again only in the former case.
    job.fd.deletion_handle()
    win.mark_delete(job.fd.handle)
    job.close()  # NTFS removes the now-empty directory on final handle close.


def sync(parent):
    # Windows has no POSIX directory fsync. Status files use FlushFileBuffers via
    # os.fsync + MOVEFILE_WRITE_THROUGH; SQLite supplies its own journal sync.
    pass
