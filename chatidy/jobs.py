"""Local durable import staging; only the final transaction changes the library."""
import hashlib
import json
import os
import re
import sqlite3
import threading
import time
import uuid
from pathlib import Path
from .db import connect, upsert
from .importer import MAX_UPLOAD, iter_export

_active = set()
_lock = threading.Lock()


def database_path():
    return Path(os.getenv('CHATIDY_DB', 'data/chatidy.sqlite3')).resolve()


def job_path(job_id):
    if not re.fullmatch(r'[a-f0-9]{32}', job_id):
        raise ValueError('Ungültige Importjob-ID.')
    return database_path().parent / 'import-jobs' / job_id


def save(path, status):
    temporary = path / 'status.tmp'
    with temporary.open('w', encoding='utf-8') as output:
        json.dump(status, output)
        output.flush()
        os.fsync(output.fileno())
    os.chmod(temporary, 0o600)
    temporary.replace(path / 'status.json')


def status(job_id):
    try:
        return json.loads((job_path(job_id) / 'status.json').read_text())
    except FileNotFoundError as exc:
        raise ValueError('Importjob nicht gefunden.') from exc


def create(source, size, name):
    if not 0 < size <= MAX_UPLOAD:
        raise ValueError('Ungültige Dateigröße (maximal 200 MB).')
    suffix = Path(name).suffix.lower()
    if suffix not in ('.json', '.zip'):
        raise ValueError('Bitte eine .zip- oder .json-Datei wählen.')
    job_id = uuid.uuid4().hex
    path = job_path(job_id)
    path.mkdir(mode=0o700, parents=True)
    digest = hashlib.sha256()
    try:
        with (path / ('source' + suffix)).open('xb') as output:
            os.chmod(output.name, 0o600)
            remaining = size
            while remaining:
                chunk = source.read(min(65536, remaining))
                if not chunk:
                    raise ValueError('Upload unvollständig. Bitte Datei erneut auswählen.')
                remaining -= len(chunk)
                digest.update(chunk)
                output.write(chunk)
        save(path, {'id': job_id, 'state': 'uploaded', 'validated': 0,
                    'total_bytes': size, 'sha256': digest.hexdigest(), 'suffix': suffix,
                    'created': time.time(), 'error': None})
    except Exception:
        # An incomplete upload has no resumable status and is not used again.
        (path / ('source' + suffix)).unlink(missing_ok=True)
        path.rmdir()
        raise
    return job_id


def run(job_id):
    """Repeatable after termination, including a crash during final commit.

    Checkpoints avoid rewriting staged chats. On resume, source validation starts
    at byte zero and checks existing checkpoints before proceeding. SQLite rolls
    back an interrupted main transaction; a commit/status crash is idempotent.
    """
    path = job_path(job_id)
    state = status(job_id)
    if state['state'] == 'done':
        return
    staging = sqlite3.connect(path / 'staging.sqlite3')
    try:
        staging.execute('CREATE TABLE IF NOT EXISTS chats(sequence INTEGER PRIMARY KEY, id TEXT UNIQUE, payload TEXT)')
        state.update(state='validating', error=None)
        save(path, state)
        source_path = path / ('source' + state['suffix'])
        with source_path.open('rb') as source:
            digest = hashlib.sha256()
            while chunk := source.read(65536):
                digest.update(chunk)
            if digest.hexdigest() != state['sha256']:
                raise ValueError('Lokale Quelldatei wurde verändert. Bitte neu hochladen.')
            source.seek(0)
            count = 0
            for count, chat in enumerate(iter_export(source, source_path.name), 1):
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
                    save(path, state)
            staging.commit()
        if staging.execute('SELECT count(*) FROM chats').fetchone()[0] != count:
            raise ValueError('Staging unvollständig oder inkonsistent. Bitte neu hochladen.')
        state.update(state='committing', validated=count)
        save(path, state)
        db = connect(database_path())
        try:
            imported = upsert(db, (json.loads(row[0]) for row in
                                  staging.execute('SELECT payload FROM chats ORDER BY sequence')))
        finally:
            db.close()
        state.update(state='done', imported=imported)
        save(path, state)
    except Exception as exc:
        staging.rollback()
        state.update(state='error', error=str(exc) if isinstance(exc, ValueError)
                     else 'Import fehlgeschlagen. Lokalen Speicher prüfen und Import fortsetzen.')
        save(path, state)
    finally:
        staging.close()


def start(job_id):
    path = str(job_path(job_id))
    status(job_id)
    with _lock:
        if path in _active:
            return
        _active.add(path)

    def worker():
        try:
            run(job_id)
        finally:
            with _lock:
                _active.discard(path)
    threading.Thread(target=worker, daemon=True).start()


def public_status(job_id):
    value = status(job_id)
    return {key: value.get(key) for key in ('id', 'state', 'validated', 'total_bytes', 'imported', 'error')}
