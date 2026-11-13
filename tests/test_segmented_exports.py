"""Synthetic 2026-shaped archives. No private export schema/content is assumed."""
import copy
import io
import json
import tempfile
import unittest
from pathlib import Path
from chatidy.importer import parse_export, inspect_export
from chatidy.db import connect, upsert, chat_detail, list_chats, assign, create_folder
from chatidy.organisation import apply_tags
from test_archives import archive


def conversation(index):
    return {'id': f'synthetic-{index}', 'title': f'Synthetic chat {index}', 'update_time': 20,
            'current_node': 'message', 'mapping': {'message': {'parent': None, 'message': {
                'id': 'shared-official-message', 'author': {'role': 'user'},
                'content': {'parts': [f'Synthetic SQLite content {index}']}}}}}


def segmented(extras=True):
    files = [(f'conversations-{i:03d}.json', json.dumps([conversation(i)])) for i in reversed(range(8))]
    if extras:
        files += [(name, '{not-a-conversation-schema') for name in (
            'ads.json', 'codex.json', 'conversation_asset_file_names.json', 'library_files.json',
            'sectioned_conversations.json', 'shared_conversations.json', 'user.json',
            'user_settings.json', 'export_manifest.json', 'sites/export_manifest.json', 'future.json')]
        files += [('file-synthetic.dat', b'\x00\xff'), ('file_synthetic.dat', b'\x01'),
                  ('index.html', '<script>Never execute</script>'),
                  ('THIRD_PARTY_NOTICES.txt', 'Synthetic notice'), ('future.resource', b'\x00')]
    return files


class SegmentedExportTests(unittest.TestCase):
    def test_numeric_order_and_inventory_without_parsing_extras(self):
        data = archive(segmented())
        chats = parse_export(data, 'synthetic.zip')
        self.assertEqual([c['id'] for c in chats], [f'synthetic-{i}' for i in range(8)])
        inventory = inspect_export(io.BytesIO(data), 'synthetic.zip')
        self.assertEqual(inventory['format'], 'official_segments')
        self.assertEqual(inventory['segment_count'], 8)
        self.assertEqual(inventory['counts']['metadata'], 10)
        self.assertEqual(inventory['counts']['attachment'], 2)
        self.assertEqual(inventory['counts']['html_viewer'], 1)
        self.assertEqual(inventory['counts']['unknown'], 2)
        self.assertEqual(inventory['manifests'], 2)
        self.assertFalse(inventory['manifests_validated'])
        self.assertEqual(inventory['sensitive_metadata_files'], 3)

    def test_reported_archive_shape_is_supported_without_metadata_schema_claims(self):
        files = [(name, body) for name,body in segmented() if name not in
                 ('future.json','future.resource','file-synthetic.dat','file_synthetic.dat')]
        files += [(f'file-synthetic-{i:04d}.dat', b'Synthetic binary') for i in range(227)]
        data = archive(files)
        inventory = inspect_export(io.BytesIO(data), 'synthetic.zip')
        self.assertEqual(inventory['counts']['conversation_segment'], 8)
        self.assertEqual(inventory['counts']['metadata'], 10)
        self.assertEqual(inventory['counts']['attachment'], 227)
        self.assertEqual(inventory['counts']['html_viewer'], 1)
        self.assertEqual(len(parse_export(data, 'synthetic.zip')), 8)

    def test_missing_duplicate_or_corrupt_segments_are_fatal(self):
        files = segmented(False)
        cases = [[pair for pair in files if '003' not in pair[0]],
                 files + [('conversations-3.json', json.dumps([conversation(9)]))],
                 [('conversations-000.json','[{'), *files[:-1]],
                 files + [('conversations.json', json.dumps([conversation(9)]))]]
        for case in cases:
            with self.subTest(), self.assertRaises(ValueError):
                parse_export(archive(case), 'synthetic.zip')

    def test_duplicate_conversation_ids_are_not_merged(self):
        with self.assertRaisesRegex(ValueError, 'Doppelte Konversations-ID'):
            parse_export(archive([('conversations-000.json', json.dumps([conversation(0)])),
                                  ('conversations-001.json', json.dumps([conversation(0)]))]), 'synthetic.zip')

    def test_classic_and_extractor_with_valid_unknown_metadata(self):
        for name, raw in (('conversations.json', [conversation(0)]),
                          ('synthetic-title.json', {'id':'extractor','messages':[{'role':'user','content':'Synthetic'}]})):
            data = archive([(name, json.dumps(raw)), ('future.json','{"future": true}'), ('file-synthetic.dat', b'')])
            self.assertEqual(len(parse_export(data, 'synthetic.zip')), 1)

    def test_single_segment_then_full_archive_and_reimport_preserve_organisation(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = connect(Path(tmp)/'synthetic.sqlite3')
            try:
                upsert(db, parse_export(json.dumps([conversation(0)]).encode(), 'conversations-000.json'))
                folder = create_folder(db, 'Synthetic folder')
                assign(db, 'synthetic-0', [folder])
                apply_tags(db, ['synthetic-0'], ['synthetic'])
                before = chat_detail(db, 'synthetic-0')
                for _ in range(2):
                    upsert(db, parse_export(archive(segmented()), 'synthetic.zip'))
                    self.assertEqual(chat_detail(db, 'synthetic-0'), before)
                    self.assertEqual(len(list_chats(db, 'SQLite')), 8)
                self.assertEqual(db.execute('SELECT count(*) FROM messages').fetchone()[0], 8)
                self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
                self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(), [])
            finally:
                db.close()
