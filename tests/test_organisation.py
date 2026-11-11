import json
import tempfile
import unittest
from pathlib import Path
from chatidy.db import connect, upsert, list_chats, chat_detail
from chatidy.organisation import apply_tags, create_smart_folder, delete_smart_folder, smart_query, tags


class OrganisationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name)/'synthetic.sqlite3'
        self.db = connect(self.path)
        self.one = {'id': 'one', 'title': 'Synthetic Python', 'messages': [
            {'id': 'one-message', 'role': 'user', 'content': 'Synthetic SQLite'}]}
        upsert(self.db, [self.one])

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def test_bulk_tags_normalized_idempotent_and_preserved_on_reimport(self):
        self.assertEqual(apply_tags(self.db, ['one', 'one'], ['Python', 'PYTHON', 'WISSEN']), 1)
        apply_tags(self.db, ['one'], ['python'])
        self.assertEqual(chat_detail(self.db, 'one')['tags'], ['python', 'wissen'])
        self.assertEqual(len(list_chats(self.db, tag='PYTHON')), 1)
        upsert(self.db, [self.one])
        self.assertEqual(chat_detail(self.db, 'one')['tags'], ['python', 'wissen'])
        apply_tags(self.db, ['one'], ['new'], replace=True)
        self.assertEqual(chat_detail(self.db, 'one')['tags'], ['new'])
        self.assertEqual([t['name'] for t in tags(self.db)], ['new'])

    def test_invalid_batch_is_atomic(self):
        for ids, names in ((['one', 'missing'], ['new']), (['one'], ['']),
                           (['one'], ['x'] * 21), ('one', ['new']), (['one'], ['bad\x00tag'])):
            with self.subTest(ids=ids, names=names), self.assertRaises(ValueError):
                apply_tags(self.db, ids, names)
        self.assertEqual(chat_detail(self.db, 'one')['tags'], [])
        self.assertEqual(tags(self.db), [])

    def test_smart_folder_dynamic_results_persist_and_delete_safely(self):
        folder = create_smart_folder(self.db, 'Synthetic saved query', {'q': 'SQLite', 'mode': 'inbox'})
        query = smart_query(self.db, folder)
        self.assertEqual(len(list_chats(self.db, **query)), 1)
        other = {'id': 'two', 'title': 'Synthetic second', 'messages': [
            {'id': 'two-message', 'role': 'user', 'content': 'Synthetic SQLite second'}]}
        upsert(self.db, [other])
        self.assertEqual(len(list_chats(self.db, **query)), 2)
        self.db.close()
        self.db = connect(self.path)
        self.assertEqual(smart_query(self.db, folder), query)
        delete_smart_folder(self.db, folder)
        self.assertEqual(len(list_chats(self.db)), 2)
        self.assertEqual(self.db.execute('PRAGMA foreign_key_check').fetchall(), [])

    def test_smart_query_validation(self):
        for query in ({'sql': 'DROP TABLE conversations'}, {'q': []}, {'mode': 'invalid'}):
            with self.subTest(query=query), self.assertRaises(ValueError):
                create_smart_folder(self.db, 'Synthetic', query)
