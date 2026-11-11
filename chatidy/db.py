"""SQLite persistence, multi-folder assignments, rules, reviews and full-text indexing."""
import os
import math
import json
from .migrations import check_version, migrate
import sqlite3
from pathlib import Path

DEFAULT_CATEGORIES = ["Tech & KI", "Programmieren", "Gaming", "Memes & Humor",
                      "Musik", "Wissen & Bildung", "Favoriten", "Fitness & Sport",
                      "Design & Kunst", "Lifestyle", "Inspiration", "Rezepte",
                      "Anime", "Filme und Serien"]

def connect(path=None):
    path = Path(path or os.getenv("CHATIDY_DB", "data/chatidy.sqlite3"))
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=20)
    db.row_factory = sqlite3.Row
    try:
        check_version(db)
    except Exception:
        db.close()
        raise
    db.execute("PRAGMA foreign_keys=ON")
    db.execute("PRAGMA busy_timeout=20000")
    db.execute("PRAGMA journal_mode=WAL")
    db.executescript("""
      CREATE TABLE IF NOT EXISTS conversations(
        id TEXT PRIMARY KEY, title TEXT NOT NULL, created REAL, updated REAL,
        project TEXT DEFAULT '', archived INTEGER DEFAULT 0, reviewed INTEGER DEFAULT 0
      );
      CREATE TABLE IF NOT EXISTS messages(
        id TEXT PRIMARY KEY, conversation_id TEXT NOT NULL
        REFERENCES conversations(id) ON DELETE CASCADE,
        role TEXT, content TEXT NOT NULL, timestamp REAL
      );
      CREATE TABLE IF NOT EXISTS folders(
        id INTEGER PRIMARY KEY, name TEXT NOT NULL,
        parent_id INTEGER REFERENCES folders(id) ON DELETE CASCADE
      );
      CREATE UNIQUE INDEX IF NOT EXISTS folders_root ON folders(name) WHERE parent_id IS NULL;
      CREATE UNIQUE INDEX IF NOT EXISTS folders_child ON folders(parent_id,name) WHERE parent_id IS NOT NULL;
      CREATE TABLE IF NOT EXISTS memberships(
        conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
        folder_id INTEGER NOT NULL REFERENCES folders(id) ON DELETE CASCADE,
        origin TEXT NOT NULL DEFAULT 'manual',
        PRIMARY KEY(conversation_id,folder_id)
      );
      CREATE TABLE IF NOT EXISTS rules(
        id INTEGER PRIMARY KEY, field TEXT NOT NULL, needle TEXT NOT NULL,
        folder_id INTEGER NOT NULL REFERENCES folders(id) ON DELETE CASCADE,
        enabled INTEGER NOT NULL DEFAULT 1
      );
      CREATE TABLE IF NOT EXISTS suggestions(
        conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
        folder_id INTEGER NOT NULL REFERENCES folders(id) ON DELETE CASCADE,
        reason TEXT, PRIMARY KEY(conversation_id,folder_id)
      );
      CREATE VIRTUAL TABLE IF NOT EXISTS search_index USING fts5(
        conversation_id UNINDEXED, title, body, tokenize='unicode61'
      );
    """)
    try:
        migrate(db)
    except Exception:
        db.close()
        raise
    for name in ("ChatGPT", "Projekte", "Wissen", "Privat", "Favoriten"):
        db.execute("INSERT OR IGNORE INTO folders(name,parent_id) VALUES(?,NULL)", (name,))
    group = db.execute("SELECT id FROM folders WHERE name='Wissen' AND parent_id IS NULL").fetchone()[0]
    for name in DEFAULT_CATEGORIES:
        db.execute("INSERT OR IGNORE INTO folders(name,parent_id) VALUES(?,?)", (name, group))
    db.commit()
    return db

def list_folders(db):
    return [dict(row) for row in db.execute("""
      SELECT f.*, (SELECT COUNT(*) FROM memberships x WHERE x.folder_id=f.id) AS item_count
      FROM folders f ORDER BY f.name COLLATE NOCASE, f.id
    """)]

def validate_folder(db, folder_id):
    if db.execute("SELECT 1 FROM folders WHERE id=?", (folder_id,)).fetchone() is None:
        raise ValueError("Ordner existiert nicht.")

def create_folder(db, name, parent_id=None):
    name = str(name).strip()
    if not name or len(name) > 100 or "/" in name or "\\" in name:
        raise ValueError("Ungültiger Ordnername.")
    if parent_id is not None:
        validate_folder(db, parent_id)
    try:
        with db:
            cur = db.execute("INSERT INTO folders(name,parent_id) VALUES(?,?)", (name,parent_id))
        return cur.lastrowid
    except sqlite3.IntegrityError as exc:
        raise ValueError("Ordnername bereits vorhanden.") from exc

def change_folder(db, folder_id, name=None, parent_id=...):
    validate_folder(db, folder_id)
    row = db.execute("SELECT * FROM folders WHERE id=?", (folder_id,)).fetchone()
    name = row["name"] if name is None else str(name).strip()
    if not name or len(name)>100 or "/" in name or "\\" in name:
        raise ValueError("Ungültiger Ordnername.")
    parent_id = row["parent_id"] if parent_id is ... else parent_id
    current = parent_id
    while current is not None:
        if current == folder_id:
            raise ValueError("Zirkuläre Ordnerhierarchie nicht erlaubt.")
        parent = db.execute("SELECT parent_id FROM folders WHERE id=?", (current,)).fetchone()
        if parent is None:
            raise ValueError("Zielordner fehlt.")
        current = parent[0]
    try:
        with db:
            db.execute("UPDATE folders SET name=?,parent_id=? WHERE id=?", (name,parent_id,folder_id))
    except sqlite3.IntegrityError as exc:
        raise ValueError("Ordnername bereits vorhanden.") from exc

def apply_rules(db, chat_id):
    chat = db.execute("SELECT * FROM conversations WHERE id=?", (chat_id,)).fetchone()
    if not chat:
        return
    body = "\n".join(row[0] for row in db.execute(
        "SELECT content FROM messages WHERE conversation_id=?", (chat_id,)))
    fields = {"title": chat["title"] or "", "project": chat["project"] or "",
              "content": body}
    for rule in db.execute("SELECT * FROM rules WHERE enabled=1"):
        if rule["needle"].casefold() in fields[rule["field"]].casefold():
            db.execute("""INSERT OR IGNORE INTO memberships(conversation_id,folder_id,origin)
                          VALUES(?,?,'rule')""", (chat_id,rule["folder_id"]))

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


def upsert(db, chats):
    count = 0
    with db:
        # Reimport validation and writes must observe the same database state.
        # Reserve the writer before reading, including when the first chat exists.
        if not db.in_transaction:
            db.execute("BEGIN IMMEDIATE")
        for chat in chats:
            cid = chat["id"]
            messages = [(m["id"],cid,m["role"],m["content"],m.get("timestamp"))
                        for m in chat["messages"]]
            ids = {message[0] for message in messages}
            if len(ids) != len(messages):
                raise ValueError("Doppelte Nachrichten-ID innerhalb eines Chats. Import abgebrochen.")
            updated = _import_timestamp(chat.get("updated"))
            existing = db.execute("SELECT updated,metadata FROM conversations WHERE id=?", (cid,)).fetchone()
            old_messages = {row["id"]: row["metadata"] for row in db.execute(
                "SELECT id,metadata FROM messages WHERE conversation_id=?", (cid,))}
            for index, message in enumerate(chat["messages"]):
                metadata = json.loads(old_messages.get(message["id"], '{}'))
                metadata.update(message.get("metadata", {}))
                messages[index] = messages[index] + (json.dumps(metadata, ensure_ascii=False), index)
            metadata = json.loads(existing["metadata"]) if existing else {}
            metadata.update(chat.get("metadata", {}))
            if existing:
                previous = _import_timestamp(existing["updated"])
                if previous is not None and (updated is None or updated < previous):
                    raise ValueError("Reimport ist älter oder hat keinen Änderungszeitpunkt. "
                                     "Bitte einen aktuellen vollständigen Export verwenden. Import abgebrochen.")
                stored_ids = set(old_messages)
                if not stored_ids.issubset(ids):
                    raise ValueError("Reimport enthält nicht alle gespeicherten Nachrichten. "
                                     "Bitte einen vollständigen Export desselben Gesprächszweigs verwenden. "
                                     "Import abgebrochen.")
            db.execute("""
              INSERT INTO conversations(id,title,created,updated,project,archived,metadata)
              VALUES(?,?,?,?,?,?,?)
              ON CONFLICT(id) DO UPDATE SET title=excluded.title,
              created=excluded.created,updated=excluded.updated,
              project=excluded.project,archived=excluded.archived,metadata=excluded.metadata
            """, (cid, chat["title"],chat.get("created"),updated,
                  chat.get("project") or "",int(chat.get("archived",False)),json.dumps(metadata, ensure_ascii=False)))
            db.execute("DELETE FROM messages WHERE conversation_id=?", (cid,))
            # Message IDs are globally unique in the existing schema. REPLACE
            # would silently delete another conversation's message on collision.
            if any(db.execute("SELECT 1 FROM messages WHERE id=?", (mid,)).fetchone()
                   for mid in ids):
                raise ValueError("Nachrichten-ID bereits in einem anderen Chat vorhanden. Import abgebrochen.")
            db.executemany("""INSERT INTO messages
                           (id,conversation_id,role,content,timestamp,metadata,position)
                           VALUES(?,?,?,?,?,?,?)""",messages)
            db.execute("DELETE FROM search_index WHERE conversation_id=?", (cid,))
            db.execute("INSERT INTO search_index(conversation_id,title,body) VALUES(?,?,?)",
                       (cid,chat["title"],"\n".join(m["content"] for m in chat["messages"])))
            apply_rules(db,cid)
            count+=1
    return count

def list_chats(db, q="", folder=None, mode="all", limit=250, offset=0, tag=None, project=None):
    sql="""SELECT c.*, (SELECT COUNT(*) FROM messages m WHERE m.conversation_id=c.id)
             AS message_count,
             (SELECT COUNT(*) FROM memberships g WHERE g.conversation_id=c.id) AS groups_count
             FROM conversations c WHERE 1=1"""
    args=[]
    if q.strip():
        sql+=" AND EXISTS(SELECT 1 FROM search_index s WHERE s.conversation_id=c.id AND search_index MATCH ?)"
        # Quote user text as a literal phrase, escaping FTS query syntax.
        args.append('"'+q.strip().replace('"','""')+'"')
    if folder is not None:
        sql+=" AND EXISTS(SELECT 1 FROM memberships g WHERE g.conversation_id=c.id AND g.folder_id=?)"
        args.append(folder)
    if tag:
        sql+=" AND EXISTS(SELECT 1 FROM chat_tags ct JOIN tags t ON t.id=ct.tag_id WHERE ct.conversation_id=c.id AND t.name=?)"
        args.append(str(tag).strip().casefold())
    if project:
        sql+=" AND c.project=?"
        args.append(project)
    if mode=="inbox":
        sql+=" AND c.reviewed=0"
    elif mode=="archived":
        sql+=" AND c.archived=1"
    elif mode=="unfiled":
        sql+=" AND NOT EXISTS(SELECT 1 FROM memberships g WHERE g.conversation_id=c.id)"
    sql+=" ORDER BY COALESCE(c.updated,c.created,0) DESC,c.id LIMIT ? OFFSET ?"
    args.extend([min(max(int(limit),1),500),max(int(offset),0)])
    return [dict(x) for x in db.execute(sql,args)]

def chat_detail(db, chat_id):
    row = db.execute("SELECT * FROM conversations WHERE id=?", (chat_id,)).fetchone()
    if row is None:
        return None
    chat = dict(row)
    chat["metadata"] = json.loads(chat["metadata"])
    messages = []
    for message in db.execute("SELECT role,content,timestamp,metadata FROM messages WHERE conversation_id=? ORDER BY position,rowid", (chat_id,)):
        item = dict(message)
        item["metadata"] = json.loads(item["metadata"])
        messages.append(item)
    return {"chat":chat,
            "tags":[r[0] for r in db.execute("SELECT t.name FROM tags t JOIN chat_tags ct ON t.id=ct.tag_id WHERE ct.conversation_id=? ORDER BY t.name", (chat_id,))],
            "messages":messages,
            "folders":[x[0] for x in db.execute(
                "SELECT folder_id FROM memberships WHERE conversation_id=?",(chat_id,))],
            "suggestions":[dict(x) for x in db.execute(
                "SELECT folder_id,reason FROM suggestions WHERE conversation_id=?",(chat_id,))]}

def assign(db, chat_id, folder_ids):
    if not isinstance(folder_ids,list) or len(folder_ids)>100:
        raise ValueError("Ungültige Gruppenauswahl.")
    if not db.execute("SELECT 1 FROM conversations WHERE id=?",(chat_id,)).fetchone():
        raise ValueError("Chat nicht gefunden.")
    ids=set(int(fid) for fid in folder_ids)
    for fid in ids:
        validate_folder(db,fid)
    with db:
        db.execute("DELETE FROM memberships WHERE conversation_id=?",(chat_id,))
        db.executemany("""INSERT INTO memberships(conversation_id,folder_id,origin)
                          VALUES(?,?,'manual')""",[(chat_id,fid) for fid in ids])
        db.execute("UPDATE conversations SET reviewed=1 WHERE id=?",(chat_id,))
        db.execute("DELETE FROM suggestions WHERE conversation_id=?",(chat_id,))

def create_rule(db,field,needle,folder_id):
    if field not in ("title","content","project") or not isinstance(needle,str) or not needle.strip() or len(needle)>200:
        raise ValueError("Ungültige Regel.")
    validate_folder(db,int(folder_id))
    with db:
        cur=db.execute("INSERT INTO rules(field,needle,folder_id) VALUES(?,?,?)",
                       (field,needle.strip(),int(folder_id)))
        for row in db.execute("SELECT id FROM conversations"):
            apply_rules(db,row[0])
    return cur.lastrowid

def stats(db):
    return {"chats":db.execute("SELECT COUNT(*) FROM conversations").fetchone()[0],
            "messages":db.execute("SELECT COUNT(*) FROM messages").fetchone()[0],
            "folders":db.execute("SELECT COUNT(*) FROM folders").fetchone()[0],
            "inbox":db.execute("SELECT COUNT(*) FROM conversations WHERE reviewed=0").fetchone()[0]}
