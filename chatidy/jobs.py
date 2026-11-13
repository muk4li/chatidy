"""Durable import lifecycle and explicitly confirmed, confined job cleanup."""
import hashlib
import json
import math
import os
import sqlite3
import threading
import time
import uuid
from pathlib import Path
from .db import connect, upsert
from .importer import MAX_UPLOAD, iter_export
from . import job_storage as storage

STATES = frozenset(('uploading', 'uploaded', 'validating', 'committing', 'done', 'error', 'interrupted'))


def database_path():
    return Path(os.path.abspath(os.getenv('CHATIDY_DB', 'data/chatidy.sqlite3')))


def job_path(job_id):
    return storage.root_path() / storage.validate_id(job_id)


def _read(job, job_id):
    value = job.read('status.json')
    if (not isinstance(value, dict) or value.get('id') != job_id or value.get('state') not in STATES
            or value.get('suffix') not in ('.json', '.zip')
            or not isinstance(value.get('validated'), int) or value['validated'] < 0
            or not isinstance(value.get('created'), (int, float))
            or not math.isfinite(value['created'])
            or not isinstance(value.get('total_bytes'), int)
            or not 0 < value['total_bytes'] <= MAX_UPLOAD):
        raise ValueError('Ungültiger Importjob-Status.')
    return value


def _inspect(job, job_id, deleting=False):
    lease = job.acquire() if not deleting else None
    active = lease is None and not deleting
    if lease is not None:
        os.close(lease)
    entries = job.entries(ignore_missing=active)
    if deleting or 'deletion.json' in entries:
        try:
            value = job.read('deletion.json')
            if (not isinstance(value, dict) or value.get('id') != job_id
                    or not isinstance(value.get('created'), (int, float))
                    or not math.isfinite(value['created'])
                    or not isinstance(value.get('validated'), int) or value['validated'] < 0):
                raise ValueError('Ungültige Bereinigungsmarkierung.')
        except (FileNotFoundError, ValueError, UnicodeError):
            value = {'id': job_id, 'created': 0, 'validated': 0}
        value = {**value, 'state': 'cleanup_pending', 'active': active,
                 'can_resume': False, 'can_delete': not active}
    else:
        try:
            value = _read(job, job_id)
        except (FileNotFoundError, ValueError, UnicodeError):
            # A damaged status does not authorize resume, but an explicit delete
            # is safe after the same full filesystem preflight as every cleanup.
            value = {'id': job_id, 'state': 'error', 'created': 0, 'validated': 0,
                     'error': 'Jobstatus beschädigt oder unvollständig. Neu hochladen oder Jobdaten bestätigt löschen.'}
        if not active and value['state'] in ('uploading', 'validating', 'committing'):
            value['state'] = 'interrupted'
        value.update(active=active, can_delete=not active,
                     can_resume=not active and value['state'] != 'done'
                     and isinstance(value.get('sha256'), str)
                     and len(value['sha256']) == 64 and 'source'+value['suffix'] in entries)
    value['storage_bytes'] = sum(entry.st_size for entry in entries.values())
    return value


def _open(root_fd, job_id):
    try:
        return storage.Job(root_fd, job_id), False
    except FileNotFoundError:
        return storage.Job(root_fd, '.deleting-'+job_id), True


def status(job_id):
    storage.validate_id(job_id)
    try:
        with storage.root() as root_fd, storage.registry(root_fd):
            job, deleting = _open(root_fd, job_id)
            try:
                return _inspect(job, job_id, deleting)
            finally:
                job.close()
    except (OSError, json.JSONDecodeError, UnicodeError) as exc:
        raise ValueError('Importjob fehlt, ist beschädigt oder enthält unsichere Dateien.') from exc


def public_status(job_id):
    value = status(job_id)
    return {key: value.get(key) for key in ('id', 'state', 'validated', 'total_bytes', 'imported',
            'error', 'created', 'storage_bytes', 'active', 'can_resume', 'can_delete')}


def listing():
    if not storage.root_path().exists() and not storage.root_path().is_symlink():
        return {'jobs': [], 'count': 0, 'storage_bytes': 0, 'ignored_entries': 0}
    results, ignored = [], 0
    with storage.root() as root_fd, storage.registry(root_fd):
        for name in sorted(storage.listdir(root_fd)):
            if name == 'management.lock':
                continue
            job_id = name.removeprefix('.deleting-')
            if not storage.ID.fullmatch(job_id):
                ignored += 1
                continue
            job = None
            try:
                job = storage.Job(root_fd, name)
                value = _inspect(job, job_id, name.startswith('.deleting-'))
                results.append({key: value.get(key) for key in ('id', 'state', 'validated', 'total_bytes',
                    'imported', 'error', 'created', 'storage_bytes', 'active', 'can_resume', 'can_delete')})
            except (OSError, ValueError, UnicodeError):
                results.append({'id': job_id, 'state': 'blocked', 'can_resume': False,
                                'can_delete': False, 'storage_bytes': 0,
                                'error': 'Unsichere oder beschädigte Jobdaten. Lokal prüfen; keine automatische Bereinigung.'})
            finally:
                if job:
                    job.close()
    results.sort(key=lambda item: item.get('created') or 0, reverse=True)
    return {'jobs': results, 'count': len(results),
            'storage_bytes': sum(item['storage_bytes'] for item in results), 'ignored_entries': ignored}


def _lease(job_id):
    storage.validate_id(job_id)
    try:
        with storage.root() as root_fd, storage.registry(root_fd):
            job, deleting = _open(root_fd, job_id)
            lease = None
            try:
                if deleting:
                    raise ValueError('Bereinigung unterbrochen. Löschung erneut bestätigen; Import nicht mehr fortsetzbar.')
                entries = job.entries(ignore_missing=True)
                if 'deletion.json' in entries:
                    raise ValueError('Bereinigung unterbrochen. Löschung erneut bestätigen.')
                lease = job.acquire()
                if lease is None:
                    raise ValueError('Importjob ist aktiv. Bitte Verarbeitung abwarten.')
                _read(job, job_id)
                return job, lease
            except BaseException:
                if lease is not None:
                    os.close(lease)
                job.close()
                raise
    except OSError as exc:
        raise ValueError('Importjob fehlt oder enthält unsichere Dateien.') from exc


def create(source, size, name):
    if not 0 < size <= MAX_UPLOAD:
        raise ValueError('Ungültige Dateigröße (maximal 200 MB).')
    suffix = Path(name).suffix.lower()
    if suffix not in ('.json', '.zip'):
        raise ValueError('Bitte eine .zip- oder .json-Datei wählen.')
    job_id = uuid.uuid4().hex
    with storage.root(create=True) as root_fd, storage.registry(root_fd):
        storage.mkdir(root_fd, job_id)
        job = storage.Job(root_fd, job_id)
        lease = job.acquire()
        state = {'id': job_id, 'state': 'uploading', 'validated': 0, 'total_bytes': size,
                 'sha256': None, 'suffix': suffix, 'created': time.time(), 'error': None}
        try:
            job.write('status.json', state)
        except BaseException:
            os.close(lease)
            job.close()
            raise
    try:
        digest = hashlib.sha256()
        fd = storage.file_open(job.fd, 'source'+suffix, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
        with os.fdopen(fd, 'wb') as output:
            remaining = size
            while remaining:
                chunk = source.read(min(65536, remaining))
                if not chunk:
                    raise ValueError('Upload unvollständig. Bitte Datei erneut auswählen.')
                remaining -= len(chunk)
                digest.update(chunk)
                output.write(chunk)
            output.flush()
            os.fsync(output.fileno())
        state.update(state='uploaded', sha256=digest.hexdigest())
        job.write('status.json', state)
    except Exception:
        state.update(state='error', error='Upload unvollständig. Bitte Datei erneut auswählen; Jobdaten können bestätigt gelöscht werden.')
        job.write('status.json', state)
        raise ValueError(state['error']) from None
    finally:
        os.close(lease)
        job.close()
    return job_id


def _run(job, job_id):
    state = _read(job, job_id)
    if state['state'] == 'done':
        return
    if not isinstance(state.get('sha256'), str) or len(state['sha256']) != 64:
        raise ValueError('Upload unvollständig. Bitte Datei erneut auswählen.')
    staging = None
    try:
        job.entries()
        # Create/validate the database itself before SQLite opens its filename.
        fd = storage.file_open(job.fd, 'staging.sqlite3', os.O_RDWR | os.O_CREAT)
        os.close(fd)
        staging = sqlite3.connect(job.sqlite_path())
        staging.execute('CREATE TABLE IF NOT EXISTS chats(sequence INTEGER PRIMARY KEY, id TEXT UNIQUE, payload TEXT)')
        state.update(state='validating', error=None)
        job.write('status.json', state)
        fd = storage.file_open(job.fd, 'source'+state['suffix'])
        with os.fdopen(fd, 'rb') as source:
            digest = hashlib.sha256()
            while chunk := source.read(65536):
                digest.update(chunk)
            if digest.hexdigest() != state['sha256']:
                raise ValueError('Lokale Quelldatei wurde verändert. Bitte neu hochladen.')
            source.seek(0)
            count = 0
            for count, chat in enumerate(iter_export(source, 'source'+state['suffix']), 1):
                payload = json.dumps(chat, ensure_ascii=False)
                previous = staging.execute('SELECT payload FROM chats WHERE sequence=?', (count,)).fetchone()
                if previous:
                    if previous[0] != payload:
                        raise ValueError('Staging stimmt nicht mit der Quelle überein. Bitte neu hochladen.')
                else:
                    staging.execute('INSERT INTO chats VALUES(?,?,?)', (count, chat['id'], payload))
                if count % 100 == 0:
                    staging.commit()
                    state['validated'] = count
                    job.write('status.json', state)
            staging.commit()
        if staging.execute('SELECT count(*) FROM chats').fetchone()[0] != count:
            raise ValueError('Staging unvollständig oder inkonsistent. Bitte neu hochladen.')
        state.update(state='committing', validated=count)
        job.write('status.json', state)
        db = connect(database_path())
        try:
            imported = upsert(db, (json.loads(row[0]) for row in
                                  staging.execute('SELECT payload FROM chats ORDER BY sequence')))
        finally:
            db.close()
        state.update(state='done', imported=imported)
        job.write('status.json', state)
    except Exception as exc:
        if staging:
            staging.rollback()
        state.update(state='error', error=str(exc) if isinstance(exc, ValueError)
                     else 'Import fehlgeschlagen. Lokalen Speicher prüfen und Import fortsetzen.')
        job.write('status.json', state)
    finally:
        if staging:
            staging.close()


def run(job_id):
    job, lease = _lease(job_id)
    try:
        _run(job, job_id)
    finally:
        os.close(lease)
        job.close()


def start(job_id):
    # Acquire before scheduling, closing the start/delete race across processes.
    try:
        job, lease = _lease(job_id)
    except ValueError:
        if public_status(job_id).get('active'):
            return  # Compatible idempotent resume while a worker is already active.
        raise
    try:
        state = _read(job, job_id)
    except BaseException:
        os.close(lease)
        job.close()
        raise
    if state['state'] == 'done':
        os.close(lease)
        job.close()
        return

    if not isinstance(state.get('sha256'), str) or len(state['sha256']) != 64:
        os.close(lease)
        job.close()
        raise ValueError('Upload unvollständig. Bitte Datei erneut auswählen.')

    def worker():
        try:
            _run(job, job_id)
        finally:
            os.close(lease)
            job.close()
    thread = threading.Thread(target=worker, daemon=True)
    try:
        thread.start()
    except BaseException:
        os.close(lease)
        job.close()
        raise
    return thread


def delete(job_id, confirmed=False):
    """Delete only a confirmed, inactive job. Interrupted deletion is retryable.

    The registry lock serializes namespace changes. A tombstone directory records
    deletion intent before any data is removed. No path recursion or symlink
    traversal is used, and unknown files/hardlinks block the entire operation.
    """
    storage.validate_id(job_id)
    if confirmed is not True:
        raise ValueError('Löschen der lokalen Jobdaten muss ausdrücklich bestätigt werden.')
    try:
        with storage.root() as root_fd, storage.registry(root_fd):
            job, deleting = _open(root_fd, job_id)
            lease = None
            try:
                lease = job.acquire()
                if lease is None:
                    raise ValueError('Aktiver Importjob kann nicht gelöscht werden.')
                entries = job.entries()  # Full preflight before any removal.
                protected = set()
                for path in (database_path(), Path(str(database_path())+'-wal'), Path(str(database_path())+'-shm'), Path(str(database_path())+'-journal')):
                    try:
                        protected.add(storage.path_identity(path))
                    except FileNotFoundError:
                        pass
                if any((info.st_dev, info.st_ino) in protected for info in entries.values()):
                    raise ValueError('Jobdatei gehört zur Chatidy-Datenbank. Bereinigung verweigert.')
                if not deleting:
                    try:
                        value = _read(job, job_id)
                    except (FileNotFoundError, ValueError, UnicodeError):
                        value = {'id': job_id, 'created': 0, 'validated': 0}
                    tombstone = '.deleting-'+job_id
                    try:
                        storage.stat_entry(root_fd, tombstone)
                    except FileNotFoundError:
                        pass
                    else:
                        raise ValueError('Mehrdeutige Bereinigungsdaten. Lokal prüfen.')
                    job.write('deletion.json', {key: value[key] for key in ('id', 'created', 'validated')})
                    storage.rename_job(job, root_fd, tombstone)
                    storage.sync(root_fd)
                else:
                    tombstone = job.name
                # Keep recovery markers until the end. On failure the tombstone
                # stays visible as cleanup_pending and requires another confirm.
                entries = job.entries()
                order = sorted(set(entries) - {'status.json', 'deletion.json', 'job.lock'})
                order += [name for name in ('status.json', 'deletion.json', 'job.lock') if name in entries]
                for name in order:
                    now = storage.stat_entry(job.fd, name)
                    before = entries[name]
                    if (now.st_dev, now.st_ino) != (before.st_dev, before.st_ino):
                        raise ValueError('Jobdateien wurden während der Bereinigung verändert. Vorgang abgebrochen.')
                    if name == 'job.lock':
                        # The registry lock and tombstone prevent new workers.
                        # Windows cannot remove a directory with a delete-pending
                        # open lock file, so release its lease at the very end.
                        os.close(lease)
                        lease = None
                    storage.unlink(job, name)
                storage.sync(job.fd)
                storage.remove_job(job, root_fd, tombstone)
                storage.sync(root_fd)
            finally:
                if lease is not None:
                    os.close(lease)
                job.close()
    except OSError as exc:
        raise ValueError('Bereinigung nicht vollständig. Jobdaten lokal prüfen und Löschung erneut bestätigen.') from exc
    return {'deleted': job_id}
