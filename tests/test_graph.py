"""Synthetic graph fixtures: no branch guessing, no truncation on corruption."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from chatidy.db import connect, upsert, chat_detail, list_chats
from chatidy.importer import parse_chat, parse_export


def graph():
    return {'id': 'synthetic-graph', 'current_node': 'answer', 'mapping': {
        'root': {'parent': None, 'message': None},
        'question': {'parent': 'root', 'message': {'author': {'role': 'user'},
            'content': {'parts': ['Synthetic question']}, 'create_time': 99}},
        'answer': {'parent': 'question', 'message': {'id': 'answer-message',
            'author': {'role': 'assistant'}, 'content': {'parts': ['Synthetic answer']}, 'create_time': 1}}}}


class GraphTests(unittest.TestCase):
    def test_active_branch_order_is_parent_order_not_time_order(self):
        raw = graph()
        raw['mapping']['alternative'] = copy.deepcopy(raw['mapping']['answer'])
        raw['mapping']['alternative']['message'].update(id='alternative-id', content={'parts': ['Wrong branch']})
        for _ in range(3):
            messages = parse_chat(raw)['messages']
            self.assertEqual([m['content'] for m in messages], ['Synthetic question', 'Synthetic answer'])
            self.assertEqual(messages[0]['id'], 'synthetic-graph:node:question')

    def test_missing_invalid_or_unhashable_current_reconstructs_only_unique_path(self):
        for current in (None, 'missing', [], {}):
            raw = graph()
            raw['current_node'] = current
            self.assertEqual(len(parse_chat(raw)['messages']), 2)

    def test_multiple_leaves_never_guessed(self):
        for current in (None, 'missing'):
            raw = graph()
            raw['current_node'] = current
            raw['mapping']['other'] = {'parent': 'question', 'message': None}
            with self.assertRaisesRegex(ValueError, 'Mehrdeutiger'):
                parse_chat(raw)

    def test_broken_structures_are_controlled_errors(self):
        mutations = [
            lambda r: r['mapping']['answer'].update(parent='missing'),
            lambda r: r['mapping']['root'].update(parent='answer'),
            lambda r: r['mapping']['answer'].update(parent=[]),
            lambda r: r['mapping'].update(answer=[]),
            lambda r: r['mapping']['answer'].update(message='invalid'),
            lambda r: r['mapping']['root'].update(children=['missing']),
            lambda r: r['mapping']['root'].update(children=[]),
            lambda r: r['mapping'].update(disconnected={'parent': None}),
            lambda r: r.update(mapping={}),
        ]
        for mutation in mutations:
            raw = graph()
            mutation(raw)
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                parse_chat(raw)

    def test_equal_times_empty_nodes_and_children(self):
        raw = graph()
        raw['mapping']['question']['message']['create_time'] = 1
        raw['mapping']['empty'] = {'parent': 'answer', 'message': {'content': {'parts': []}}}
        raw['current_node'] = 'empty'
        for key, node in raw['mapping'].items():
            node['children'] = [k for k, n in raw['mapping'].items() if n.get('parent') == key]
        self.assertEqual([m['content'] for m in parse_chat(raw)['messages']],
                         ['Synthetic question', 'Synthetic answer'])

    def test_database_reimport_and_failed_batch_preserve_fts(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = connect(Path(tmp) / 'synthetic.sqlite3')
            try:
                raw = graph()
                upsert(db, parse_export(json.dumps([raw]).encode(), 'synthetic.json'))
                before = chat_detail(db, raw['id'])
                upsert(db, parse_export(json.dumps([raw]).encode(), 'synthetic.json'))
                self.assertEqual(chat_detail(db, raw['id']), before)
                broken = graph()
                broken['mapping']['answer']['parent'] = 'missing'
                with self.assertRaisesRegex(ValueError, 'Elternknoten'):
                    upsert(db, parse_export(json.dumps([raw, broken]).encode(), 'synthetic.json'))
                alternative = graph()
                alternative['mapping']['other'] = {'parent': 'question', 'message': {
                    'id': 'other-message', 'author': {'role': 'assistant'}, 'content': {'parts': ['Other']}}}
                alternative['current_node'] = 'other'
                with self.assertRaisesRegex(ValueError, 'nicht alle gespeicherten'):
                    upsert(db, [parse_chat(alternative)])
                self.assertEqual(chat_detail(db, raw['id']), before)
                self.assertEqual(len(list_chats(db, 'Synthetic answer')), 1)
                self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
            finally:
                db.close()
