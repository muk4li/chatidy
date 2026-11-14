"""Synthetic regressions for atomic imports into the existing SQLite schema."""
import copy
import sqlite3
import tempfile
import unittest
from pathlib import Path

from chatidy.db import assign, chat_detail, connect, create_folder, create_rule, list_chats, stats, upsert


def chat(cid, mid, text='Synthetic SQLite message'):
    return {'id': cid, 'title': 'Synthetic conversation', 'messages': [
        {'id': mid, 'role': 'user', 'content': text}]}


class ImportIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / 'synthetic.sqlite3'
        self.db = connect(self.path)
        self.original = chat('first', 'shared')
        upsert(self.db, [self.original])
        self.folder = create_folder(self.db, 'Synthetic folder')
        assign(self.db, 'first', [self.folder])
        create_rule(self.db, 'content', 'SQLite', self.folder)
        self.before = self.snapshot()

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def snapshot(self):
        tables = ('conversations', 'messages', 'memberships', 'rules', 'search_index')
        return {table: [tuple(row) for row in self.db.execute(
            f'SELECT * FROM {table} ORDER BY rowid')] for table in tables}

    def test_same_message_id_in_two_chats_keeps_independent_contents(self):
        replacement = copy.deepcopy(self.original)
        replacement['messages'].extend(chat('first', 'replacement', 'Changed synthetic text')['messages'])
        upsert(self.db, [replacement, chat('second', 'replacement', 'Independent synthetic text')])
        self.assertEqual(len(chat_detail(self.db, 'first')['messages']), 2)
        self.assertEqual(chat_detail(self.db, 'second')['messages'][0]['content'], 'Independent synthetic text')
        self.assertEqual(len(list_chats(self.db, 'Changed')), 1)
        self.assertEqual(len(list_chats(self.db, 'Independent')), 1)
        self.assertEqual(chat_detail(self.db, 'first')['folders'], [self.folder])

    def test_existing_message_cannot_be_stolen_by_same_id_in_another_chat(self):
        before = chat_detail(self.db, 'first')
        upsert(self.db, [chat('second', 'shared', 'Independent content')])
        self.assertEqual(chat_detail(self.db, 'first'), before)
        self.assertEqual(self.db.execute('SELECT count(*) FROM messages WHERE id=?', ('shared',)).fetchone()[0], 2)
        self.db.close()
        self.db = connect(self.path)
        self.assertEqual(chat_detail(self.db, 'first'), before)
        self.assertEqual(self.db.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
        self.assertEqual(self.db.execute('PRAGMA foreign_key_check').fetchall(), [])

    def test_duplicate_message_in_reimport_preserves_original(self):
        duplicate = copy.deepcopy(self.original)
        duplicate['messages'].append(dict(duplicate['messages'][0], content='Different text'))
        with self.assertRaisesRegex(ValueError, 'Doppelte Nachrichten-ID'):
            upsert(self.db, [duplicate])
        self.assertEqual(self.snapshot(), self.before)

    def test_interrupted_iterable_rolls_back(self):
        def interrupted():
            yield chat('second', 'unique')
            raise RuntimeError('Synthetic interrupted import')
        with self.assertRaises(RuntimeError):
            upsert(self.db, interrupted())
        self.assertEqual(self.snapshot(), self.before)

    def test_sql_error_rolls_back(self):
        invalid = chat('second', 'unique')
        invalid['messages'][0]['content'] = None
        with self.assertRaises(sqlite3.IntegrityError):
            upsert(self.db, [chat('third', 'third-message'), invalid])
        self.assertEqual(self.snapshot(), self.before)

    def test_large_batch_and_reimport_remain_idempotent(self):
        batch = [chat(f'synthetic-{i}', f'message-{i}') for i in range(1500)]
        self.assertEqual(upsert(self.db, batch), 1500)
        self.assertEqual(upsert(self.db, batch), 1500)
        self.assertEqual(stats(self.db)['messages'], 1501)
        self.assertEqual(self.db.execute('SELECT count(*) FROM search_index').fetchone()[0], 1501)
        self.assertEqual(chat_detail(self.db, 'first')['chat']['reviewed'], 1)
        self.assertEqual(chat_detail(self.db, 'first')['folders'], [self.folder])


if __name__ == '__main__':
    unittest.main()
