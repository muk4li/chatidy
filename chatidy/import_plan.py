"""Read-only preview and rechecked, class-scoped non-destructive batch policies."""
import json
import sqlite3
from contextlib import contextmanager, closing
from pathlib import Path
from .db import connect, upsert
from .conflicts import classify_chat
from .migrations import check_version

CLASSES = ('new', 'identical', 'newer', 'complete', 'older', 'branch', 'identity')


@contextmanager
def readonly_database(path):
    path = Path(path).absolute()
    if not path.exists():
        yield None
        return
    with closing(sqlite3.connect(path.as_uri()+'?mode=ro', uri=True)) as db:
        db.row_factory = sqlite3.Row
        check_version(db)
        db.execute('PRAGMA query_only=ON')
        yield db




def preview(path, staging, inventory):
    counts = dict.fromkeys(CLASSES, 0)
    with readonly_database(path) as db, closing(staging.execute('SELECT payload FROM chats ORDER BY sequence')) as rows:
        for row in rows:
            counts[classify_chat(db, json.loads(row[0]))] += 1
    return {'inventory': inventory, 'conversations': sum(counts.values()), 'classes': counts,
            'estimated_additional_bytes': inventory['selected_json_bytes'] * 6,
            'estimate_note': 'Grobe Schätzung für Staging, Metadaten und Index; keine Speicherzusage.',
            'can_confirm': counts['identity'] == 0,
            'warnings': [*inventory.get('warnings', []),
                'Die lokale Uploadkopie kann sensible Zusatzdateien enthalten; Jobdaten nach Bedarf bestätigt löschen.']}


def validate_policies(value):
    if not isinstance(value, dict) or set(value) - {'older', 'branch'}:
        raise ValueError('Nur getrennte Entscheidungen für ältere und abweichende/unvollständige Chats sind zulässig.')
    result = {'older':'abort', 'branch':'abort'}
    for key, choice in value.items():
        if choice not in ('abort', 'skip'):
            raise ValueError('Ungültige Konfliktentscheidung; kein globales Fehler-ignorieren erlaubt.')
        result[key] = choice
    return result


def apply(path, staging, policies):
    policies = validate_policies(policies)
    counts = dict.fromkeys(CLASSES, 0)
    with closing(connect(path)) as db, db:
        db.execute('BEGIN IMMEDIATE')
        def chosen(rows):
            for row in rows:
                chat = json.loads(row[0])
                kind = classify_chat(db, chat)  # Recheck against the locked current library.
                counts[kind] += 1
                if kind == 'identity':
                    raise ValueError('Unklare Nachrichten-/Versionsidentität. Kein automatisches Überschreiben zulässig.')
                if kind in ('older', 'branch'):
                    if policies[kind] != 'skip':
                        raise ValueError('Batch enthält ältere oder abweichende/unvollständige Chats. Vorschau erneut prüfen.')
                    continue
                if kind == 'identical':
                    continue
                yield chat
        with closing(staging.execute('SELECT payload FROM chats ORDER BY sequence')) as rows:
            imported = upsert(db, chosen(rows))
    return {'imported': imported, 'unchanged': counts['identical']+counts['older']+counts['branch'], 'classes': counts}
