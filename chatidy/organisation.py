"""Validated local tags and dynamic saved queries, independent of presentation."""
import json


def label(value, maximum=100):
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > maximum:
        raise ValueError('Ungültiger Name oder zu langes Suchfeld.')
    value = value.strip()
    if any(ord(c) < 32 for c in value):
        raise ValueError('Steuerzeichen im Namen sind nicht erlaubt.')
    return value


def tag_names(values):
    if not isinstance(values, list) or len(values) > 20:
        raise ValueError('Maximal 20 Tags pro Aktion.')
    return sorted({label(value, 60).casefold() for value in values})


def chat_ids(db, values):
    if not isinstance(values, list) or not 1 <= len(values) <= 500:
        raise ValueError('Bitte 1 bis 500 Chats auswählen.')
    if any(not isinstance(cid, str) or not cid for cid in values):
        raise ValueError('Ungültige Chat-ID.')
    ids = set(values)
    for cid in ids:
        if not db.execute('SELECT 1 FROM conversations WHERE id=?', (cid,)).fetchone():
            raise ValueError('Chat nicht gefunden.')
    return ids


def apply_tags(db, ids, names, replace=False):
    names = tag_names(names)
    with db:
        ids = chat_ids(db, ids)
        for cid in ids:
            if replace:
                db.execute('DELETE FROM chat_tags WHERE conversation_id=?', (cid,))
            for name in names:
                db.execute('INSERT OR IGNORE INTO tags(name) VALUES(?)', (name,))
                tag_id = db.execute('SELECT id FROM tags WHERE name=?', (name,)).fetchone()[0]
                db.execute('INSERT OR IGNORE INTO chat_tags VALUES(?,?)', (cid, tag_id))
    return len(ids)


def tags(db):
    return [dict(row) for row in db.execute('''SELECT t.id,t.name,count(ct.conversation_id) AS count
        FROM tags t JOIN chat_tags ct ON ct.tag_id=t.id GROUP BY t.id ORDER BY t.name''')]


def validated_query(value):
    if not isinstance(value, dict) or set(value) - {'q', 'tag', 'mode', 'project'}:
        raise ValueError('Ungültige intelligente Ordnerabfrage.')
    result = {'mode': value.get('mode', 'all')}
    if result['mode'] not in ('all', 'inbox', 'archived', 'unfiled'):
        raise ValueError('Ungültiger Ansichtsfilter.')
    for key, maximum in (('q', 500), ('tag', 60), ('project', 200)):
        if key in value:
            if not isinstance(value[key], str):
                raise ValueError('Ungültiges Suchfeld.')
            result[key] = label(value[key], maximum) if value[key].strip() else ''
    return result


def create_smart_folder(db, name, query):
    name = label(name)
    query = validated_query(query)
    if db.execute('SELECT 1 FROM smart_folders WHERE name=?', (name,)).fetchone():
        raise ValueError('Intelligenter Ordnername bereits vorhanden.')
    with db:
        return db.execute('INSERT INTO smart_folders(name,query) VALUES(?,?)',
                          (name, json.dumps(query))).lastrowid


def smart_folders(db):
    return [{**dict(row), 'query': json.loads(row['query'])} for row in
            db.execute('SELECT * FROM smart_folders ORDER BY name')]


def smart_query(db, folder_id):
    row = db.execute('SELECT query FROM smart_folders WHERE id=?', (folder_id,)).fetchone()
    if not row:
        raise ValueError('Intelligenter Ordner nicht gefunden.')
    return validated_query(json.loads(row['query']))


def delete_smart_folder(db, folder_id):
    smart_query(db, folder_id)
    with db:
        db.execute('DELETE FROM smart_folders WHERE id=?', (folder_id,))
