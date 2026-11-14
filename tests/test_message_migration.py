import copy
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from chatidy import migrations
from chatidy.db import connect, upsert, assign, create_folder, chat_detail, list_chats
from chatidy.organisation import apply_tags
from test_import_integrity import chat


class MessageMigrationTests(unittest.TestCase):
    def baseline(self, path):
        with patch('chatidy.migrations.LATEST', 3):
            db = connect(path)
            first = chat('old', 'original-message')
            first['messages'].append({'id':'original-answer','role':'assistant','content':'Synthetic old answer'})
            upsert(db, [first])
            folder = create_folder(db, 'Synthetic folder')
            assign(db, 'old', [folder])
            apply_tags(db, ['old'], ['synthetic'])
            before = chat_detail(db, 'old')
            db.close()
        return before

    def test_schema_three_is_migrated_without_losing_identity_or_organisation(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'synthetic.sqlite3'
            before = self.baseline(path)
            db = connect(path)
            try:
                self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0], 4)
                self.assertEqual(chat_detail(db, 'old'), before)
                key = {row['name']:row['pk'] for row in db.execute('PRAGMA table_info(messages)')}
                self.assertEqual((key['conversation_id'], key['id']), (1,2))
                upsert(db, [chat('new', 'original-message', 'Independent synthetic body')])
                self.assertEqual(chat_detail(db, 'old'), before)
                self.assertEqual(len(list_chats(db, 'SQLite')), 1)
                self.assertEqual(len(list_chats(db, 'Independent')), 1)
                self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
                self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(), [])
            finally:
                db.close()

    def test_failed_rebuild_rolls_back_data_schema_and_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'synthetic.sqlite3'
            before = self.baseline(path)
            bad = dict(migrations.MIGRATIONS)
            bad[4] = (*bad[4][:2], 'INVALID SQL')
            with patch('chatidy.migrations.MIGRATIONS', bad), self.assertRaises(sqlite3.OperationalError):
                connect(path)
            db = sqlite3.connect(path)
            try:
                self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0], 3)
                self.assertEqual(db.execute("SELECT name FROM sqlite_master WHERE name='messages_v4'").fetchall(), [])
                self.assertEqual(db.execute('SELECT count(*) FROM messages').fetchone()[0], 2)
                self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
            finally:
                db.close()
            db = connect(path)
            self.assertEqual(chat_detail(db, 'old'), before)
            db.close()
