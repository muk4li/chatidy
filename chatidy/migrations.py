"""Transactional schema migrations preserving existing local records."""
MIGRATIONS = {
    1: (
        "ALTER TABLE conversations ADD COLUMN metadata TEXT NOT NULL DEFAULT '{}'",
        "ALTER TABLE messages ADD COLUMN metadata TEXT NOT NULL DEFAULT '{}'",
    ),
    2: (
        "CREATE TABLE tags(id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE)",
        "CREATE TABLE chat_tags(conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE, tag_id INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE, PRIMARY KEY(conversation_id,tag_id))",
        "CREATE TABLE smart_folders(id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, query TEXT NOT NULL)",
    ),
    3: (
        "ALTER TABLE messages ADD COLUMN position INTEGER NOT NULL DEFAULT 0",
        "UPDATE messages SET position=rowid",
    ),
    4: (
        "CREATE TABLE messages_v4(id TEXT NOT NULL, conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE, role TEXT, content TEXT NOT NULL, timestamp REAL, metadata TEXT NOT NULL DEFAULT '{}', position INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(conversation_id,id))",
        "INSERT INTO messages_v4(id,conversation_id,role,content,timestamp,metadata,position) SELECT id,conversation_id,role,content,timestamp,metadata,position FROM messages",
        "DROP TABLE messages",
        "ALTER TABLE messages_v4 RENAME TO messages",
    ),
    5: (
        # Origin of a chat (E3): fixed column, not a tag. All existing chats came from ChatGPT.
        "ALTER TABLE conversations ADD COLUMN provider TEXT NOT NULL DEFAULT 'chatgpt'",
    ),
    6: (
        # Rebuild the full-text index without the non-text marker (SEARCH-001). Only the derived
        # index changes; conversations and messages stay untouched. Marker must match importer.NON_TEXT.
        "DELETE FROM search_index",
        "INSERT INTO search_index(conversation_id,title,body) "
        "SELECT c.id, c.title, COALESCE((SELECT group_concat(content, char(10)) FROM "
        "(SELECT content FROM messages m WHERE m.conversation_id=c.id "
        "AND m.content!='[Nicht-textueller Inhalt]' ORDER BY m.position, m.rowid)), '') "
        "FROM conversations c",
    ),
}
LATEST = max(MIGRATIONS)


def check_version(db):
    version = db.execute('PRAGMA user_version').fetchone()[0]
    if version > LATEST:
        raise ValueError('Datenbank stammt aus einer neueren Chatidy-Version. Bitte Anwendung aktualisieren.')
    return version


def migrate(db):
    if check_version(db) == LATEST:
        return
    with db:
        db.execute('BEGIN IMMEDIATE')
        version = check_version(db)
        for target in range(version + 1, LATEST + 1):
            for statement in MIGRATIONS[target]:
                db.execute(statement)
            db.execute(f'PRAGMA user_version={target}')
