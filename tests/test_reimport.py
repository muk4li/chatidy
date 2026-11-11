"""Conservative reimport policy, using only synthetic conversations."""
import copy
import json
import os
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from chatidy.db import assign, chat_detail, connect, create_folder, create_rule, list_chats, upsert
from chatidy.importer import parse_export
from chatidy.server import Handler


def sample():
    return {'id': 'synthetic', 'title': 'Synthetic title', 'created': 10, 'updated': 20,
            'project': 'synthetic-project', 'archived': True, 'messages': [
                {'id': 'first', 'role': 'user', 'content': 'Synthetic SQLite', 'timestamp': 11},
                {'id': 'second', 'role': 'assistant', 'content': 'Synthetic answer', 'timestamp': 12}]}


class ReimportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / 'synthetic.sqlite3'
        self.db = connect(self.path)
        self.original = sample()
        upsert(self.db, [self.original])
        self.folder = create_folder(self.db, 'Synthetic folder')
        assign(self.db, 'synthetic', [self.folder])
        create_rule(self.db, 'content', 'SQLite', self.folder)
        with self.db:
            self.db.execute("INSERT INTO suggestions VALUES(?,?,?)",
                            ('synthetic', self.folder, 'Synthetic suggestion'))
        self.before = self.snapshot()

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def snapshot(self):
        tables = ('conversations', 'messages', 'search_index', 'memberships', 'folders', 'rules', 'suggestions')
        return {table: [tuple(row) for row in self.db.execute(f'SELECT * FROM {table} ORDER BY rowid')]
                for table in tables}

    def rejected(self, incoming, error):
        new_chat = {'id': 'new', 'title': 'Synthetic new chat', 'messages': [
            {'id': 'new-message', 'role': 'user', 'content': 'Synthetic rollback token'}]}
        with self.assertRaisesRegex(ValueError, error):
            upsert(self.db, [new_chat, incoming])
        self.assertEqual(self.snapshot(), self.before)
        self.assertEqual(list_chats(self.db, 'rollback'), [])
        self.db.close()
        self.db = connect(self.path)
        self.assertEqual(self.snapshot(), self.before)
        self.assertEqual(self.db.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
        self.assertEqual(self.db.execute('PRAGMA foreign_key_check').fetchall(), [])

    def test_truncated_empty_and_different_branch_are_rejected(self):
        for messages in (self.original['messages'][:1], [], [
                self.original['messages'][0],
                {'id': 'alternative', 'role': 'assistant', 'content': 'Synthetic alternative'}]):
            with self.subTest(messages=messages):
                incoming = copy.deepcopy(self.original)
                incoming.update(messages=messages, updated=30)
                self.rejected(incoming, 'nicht alle gespeicherten Nachrichten')

    def test_older_complete_export_cannot_replace_content_or_metadata(self):
        incoming = copy.deepcopy(self.original)
        incoming.update(updated=19, title='Synthetic old title', project='', archived=False)
        incoming['messages'][0]['content'] = 'Synthetic stale content'
        self.rejected(incoming, 'älter')

    def test_missing_freshness_date_is_rejected_when_stored_date_known(self):
        incoming = copy.deepcopy(self.original)
        del incoming['updated']
        self.rejected(incoming, 'keinen Änderungszeitpunkt')

    def test_invalid_freshness_dates_are_rejected(self):
        for value in ('invalid', float('nan'), float('inf'), -float('inf'), True, [], {}):
            with self.subTest(value=value):
                incoming = copy.deepcopy(self.original)
                incoming['updated'] = value
                self.rejected(incoming, 'Ungültiger Änderungszeitpunkt')

    def test_identical_reimport_is_idempotent(self):
        self.assertEqual(upsert(self.db, [copy.deepcopy(self.original)]), 1)
        self.assertEqual(self.snapshot(), self.before)

    def test_newer_complete_export_updates_content_and_adds_messages(self):
        incoming = copy.deepcopy(self.original)
        incoming.update(updated=30, title='Synthetic newer title')
        incoming['messages'][1]['content'] = 'Synthetic revised answer'
        incoming['messages'].append({'id': 'third', 'role': 'user', 'content': 'Synthetic extension'})
        self.assertEqual(upsert(self.db, [incoming]), 1)
        detail = chat_detail(self.db, 'synthetic')
        self.assertEqual(len(detail['messages']), 3)
        self.assertEqual(detail['chat']['updated'], 30)
        self.assertEqual(detail['chat']['reviewed'], 1)
        self.assertEqual(detail['folders'], [self.folder])
        self.assertEqual(len(detail['suggestions']), 1)
        self.assertEqual(len(list_chats(self.db, 'revised')), 1)
        self.assertEqual(list_chats(self.db, 'Synthetic answer'), [])
        self.assertEqual(upsert(self.db, [incoming]), 1)
        self.assertEqual(len(chat_detail(self.db, 'synthetic')['messages']), 3)

    def test_missing_dates_on_both_sides_still_allow_reimport(self):
        incoming = {'id': 'undated', 'title': 'Synthetic undated', 'messages': [
            {'id': 'undated-message', 'role': 'user', 'content': 'Synthetic text'}]}
        self.assertEqual(upsert(self.db, [incoming]), 1)
        self.assertEqual(upsert(self.db, [incoming]), 1)

    def test_extractor_adapter_truncated_reimport_is_rejected(self):
        raw = {'id': 'extractor', 'messages': [
            {'role': 'user', 'content': 'Synthetic question'},
            {'role': 'assistant', 'content': 'Synthetic answer'}]}
        upsert(self.db, parse_export(json.dumps(raw).encode(), 'synthetic.json'))
        before = self.snapshot()
        raw['messages'].pop()
        with self.assertRaisesRegex(ValueError, 'nicht alle gespeicherten Nachrichten'):
            upsert(self.db, parse_export(json.dumps(raw).encode(), 'synthetic.json'))
        self.assertEqual(self.snapshot(), before)

    def test_http_official_export_rejection_keeps_search_and_export_intact(self):
        def official(messages, updated):
            return {'id': 'http-synthetic', 'title': 'Synthetic HTTP', 'update_time': updated,
                    'current_node': str(len(messages) - 1), 'mapping': {
                        str(i): {'parent': str(i-1) if i else None,
                                 'message': {'id': f'http-{i}', 'author': {'role': 'user'},
                                             'content': {'parts': [text]}}}
                        for i, text in enumerate(messages)}}

        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        port = server.server_address[1]
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        with patch.dict(os.environ, CHATIDY_DB=str(self.path), CHATIDY_PORT=str(port)):
            thread.start()
            try:
                def request(path, data=None):
                    req = urllib.request.Request(f'http://127.0.0.1:{port}{path}',
                        data=json.dumps(data).encode() if data is not None else None,
                        headers={'X-Filename': 'conversations.json'})
                    with urllib.request.urlopen(req, timeout=5) as response:
                        return json.load(response)

                complete = official(['Synthetic HTTP question', 'Synthetic preserved answer'], 20)
                self.assertEqual(request('/api/import', [complete]), {'imported': 1})
                before = self.snapshot()
                for rejected in (official(['Synthetic HTTP question'], 30),
                                 official(['Synthetic HTTP question', 'Synthetic stale answer'], 19)):
                    with self.assertRaises(urllib.error.HTTPError) as caught:
                        request('/api/import', [rejected])
                    self.assertEqual(caught.exception.code, 400)
                    with caught.exception as response:
                        self.assertIn('Import abgebrochen', json.load(response)['error'])
                    self.assertEqual(self.snapshot(), before)
                self.assertEqual(request('/api/chats?q=preserved')[0]['id'], 'http-synthetic')
                exported = request('/api/export', {'ids': ['http-synthetic']})['exported']
                self.assertEqual(len(exported), 1)
                self.assertEqual(len(exported[0]['messages']), 2)
            finally:
                server.shutdown()
                thread.join(timeout=5)
                server.server_close()


if __name__ == '__main__':
    unittest.main()
