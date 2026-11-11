import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from chatidy.db import connect, upsert, chat_detail
from chatidy.importer import parse_export
from chatidy.migrations import migrate, LATEST


class MetadataTests(unittest.TestCase):
    def test_extractor_fields_and_nontext_references_survive_round_trip(self):
        raw = {'id': 'synthetic-meta', 'model': 'synthetic-model', 'project_id': 'synthetic-project',
               'custom_instructions': {'text': 'Synthetic'}, 'messages': [
                   {'id': 'synthetic-code', 'role': 'assistant', 'content': '```python\nprint("synthetic")\n```',
                    'model_slug': 'synthetic-model', 'citations': [{'url': 'https://example.invalid/source'}],
                    'files': [{'name': 'synthetic.txt', 'id': 'synthetic-file'}]},
                   {'role': 'user', 'content': '', 'files': [{'name': 'synthetic.png'}]}]}
        with tempfile.TemporaryDirectory() as tmp:
            db = connect(Path(tmp)/'synthetic.sqlite3')
            try:
                parsed = parse_export(json.dumps(raw).encode(), 'synthetic.json')
                upsert(db, parsed)
                detail = chat_detail(db, raw['id'])
                self.assertEqual(detail['chat']['metadata']['model'], raw['model'])
                self.assertEqual(detail['messages'][0]['content'], raw['messages'][0]['content'])
                self.assertEqual(detail['messages'][0]['metadata']['citations'], raw['messages'][0]['citations'])
                self.assertEqual(len(detail['messages']), 2)
                self.assertIn('synthetic.png', json.dumps(detail))
                del raw['model']
                del raw['messages'][0]['citations']
                upsert(db, parse_export(json.dumps(raw).encode(), 'synthetic.json'))
                detail = chat_detail(db, raw['id'])
                self.assertEqual(detail['chat']['metadata']['model'], 'synthetic-model')
                self.assertTrue(detail['messages'][0]['metadata']['citations'])
            finally:
                db.close()

    def test_official_multimodal_parts_and_metadata_remain_local_json(self):
        raw = {'id': 'synthetic-image', 'current_node': 'image', 'mapping': {
            'image': {'parent': None, 'message': {'id': 'synthetic-image-message',
                'author': {'role': 'user'}, 'content': {'content_type': 'multimodal_text',
                'parts': [{'asset_pointer': 'file-service://synthetic-reference'}]},
                'metadata': {'attachments': [{'name': 'synthetic.png'}]}}}}}
        parsed = parse_export(json.dumps(raw).encode(), 'synthetic.json')[0]
        self.assertIn('[Anhang]', parsed['messages'][0]['content'])
        self.assertEqual(parsed['messages'][0]['metadata']['content'], raw['mapping']['image']['message']['content'])

    def test_existing_schema_migrates_without_losing_rows_and_reopens(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'synthetic.sqlite3'
            old = sqlite3.connect(path)
            old.executescript('''CREATE TABLE conversations(id TEXT PRIMARY KEY,title TEXT NOT NULL,
                created REAL,updated REAL,project TEXT DEFAULT '',archived INTEGER DEFAULT 0,reviewed INTEGER DEFAULT 0);
                CREATE TABLE messages(id TEXT PRIMARY KEY,conversation_id TEXT NOT NULL REFERENCES conversations(id),
                role TEXT,content TEXT NOT NULL,timestamp REAL);
                INSERT INTO conversations(id,title,reviewed) VALUES('old','Synthetic old',1);
                INSERT INTO messages VALUES('old-message','old','user','Synthetic old text',1);''')
            old.close()
            for _ in range(2):
                db = connect(path)
                try:
                    self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0], LATEST)
                    self.assertEqual(chat_detail(db, 'old')['chat']['reviewed'], 1)
                    self.assertEqual(chat_detail(db, 'old')['messages'][0]['metadata'], {})
                    self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
                finally:
                    db.close()

    def test_migration_failure_rolls_back_schema_and_version(self):
        db = sqlite3.connect(':memory:')
        try:
            db.executescript('CREATE TABLE conversations(id TEXT);CREATE TABLE messages(id TEXT);')
            with patch('chatidy.migrations.LATEST', 1), patch('chatidy.migrations.MIGRATIONS', {1: (
                    "ALTER TABLE conversations ADD COLUMN metadata TEXT", 'INVALID SQL')}):
                with self.assertRaises(sqlite3.OperationalError):
                    migrate(db)
            self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0], 0)
            self.assertEqual([r[1] for r in db.execute('PRAGMA table_info(conversations)')], ['id'])
        finally:
            db.close()

    def test_future_database_is_rejected_before_schema_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'synthetic.sqlite3'
            db = sqlite3.connect(path)
            db.execute('PRAGMA user_version=999')
            db.close()
            with self.assertRaisesRegex(ValueError, 'neueren Chatidy'):
                connect(path)
            db = sqlite3.connect(path)
            self.assertEqual(db.execute('SELECT name FROM sqlite_master').fetchall(), [])
            db.close()
