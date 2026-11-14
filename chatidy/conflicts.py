"""Conversation-scoped identity checks shared by all import paths."""
import json
import math


def _import_timestamp(value):
    """Accept finite Unix timestamps; missing dates cannot prove freshness."""
    if value is None:
        return None
    try:
        timestamp = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("Ungültiger Änderungszeitpunkt. Import abgebrochen.") from exc
    if isinstance(value, bool) or not math.isfinite(timestamp):
        raise ValueError("Ungültiger Änderungszeitpunkt. Import abgebrochen.")
    return timestamp



def classify_chat(db, chat):
    messages = chat['messages']
    ids = [m['id'] for m in messages]
    if len(ids) != len(set(ids)) or any(not isinstance(mid, str) or not mid for mid in ids):
        raise ValueError('Doppelte oder ungültige Nachrichten-ID innerhalb eines Chats.')
    updated = _import_timestamp(chat.get('updated'))
    existing = db.execute('SELECT * FROM conversations WHERE id=?', (chat['id'],)).fetchone() if db else None
    if existing is None:
        return 'new'
    existing = dict(existing)
    old_time = _import_timestamp(existing.get('updated'))
    if old_time is not None and (updated is None or updated < old_time):
        return 'older'
    stored = [dict(row) for row in db.execute('SELECT * FROM messages WHERE conversation_id=? ORDER BY rowid', (chat['id'],))]
    stored.sort(key=lambda row: row.get('position', 0))
    old_ids = [m['id'] for m in stored]
    if not set(old_ids).issubset(ids):
        return 'branch'
    if old_time is not None and updated is not None and updated > old_time:
        return 'newer'
    old_by_id = {m['id']: m for m in stored}
    additions = len(messages) > len(stored)
    if [mid for mid in ids if mid in old_by_id] != old_ids:
        return 'identity'
    for incoming in messages:
        previous = old_by_id.get(incoming['id'])
        if previous is None:
            continue
        for key in ('role', 'content', 'timestamp'):
            if previous.get(key) != incoming.get(key):
                return 'identity'
        old_meta = json.loads(previous.get('metadata', '{}'))
        for key, value in incoming.get('metadata', {}).items():
            if key in old_meta and old_meta[key] != value:
                return 'identity'
            additions |= key not in old_meta
    for key, default in (('title', ''), ('created', None), ('project', ''), ('archived', False)):
        if existing.get(key) != chat.get(key, default):
            return 'identity'
    old_meta = json.loads(existing.get('metadata', '{}'))
    for key, value in chat.get('metadata', {}).items():
        if key in old_meta and old_meta[key] != value:
            return 'identity'
        additions |= key not in old_meta
    additions |= old_time != updated
    return 'complete' if additions else 'identical'
