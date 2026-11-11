"""Small, transactional, additive schema migrations for existing local libraries."""
MIGRATIONS = {
    1: (
        "ALTER TABLE conversations ADD COLUMN metadata TEXT NOT NULL DEFAULT '{}'",
        "ALTER TABLE messages ADD COLUMN metadata TEXT NOT NULL DEFAULT '{}'",
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
