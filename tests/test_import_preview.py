import copy
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from chatidy import jobs, import_plan
from chatidy.db import connect, upsert, chat_detail, list_chats
from test_archives import archive
from test_segmented_exports import conversation, segmented


class ImportPreviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name)/'library.sqlite3'
        self.env = patch.dict(os.environ, CHATIDY_DB=str(self.path))
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def analyze(self, data=None, name='synthetic.zip'):
        data = archive(segmented()) if data is None else data
        job = jobs.create(io.BytesIO(data), len(data), name, confirmation_required=True)
        jobs.run(job)
        self.assertEqual(jobs.status(job)['state'], 'awaiting_confirmation', jobs.public_status(job))
        return job

    def commit(self, job, policies=None):
        thread = jobs.confirm(job, True, policies)
        thread.join(timeout=10)
        self.assertFalse(thread.is_alive())
        return jobs.public_status(job)

    def seed(self, raw):
        from chatidy.importer import parse_export
        db = connect(self.path)
        try:
            upsert(db, parse_export(json.dumps(raw).encode(), 'synthetic.json'))
        finally:
            db.close()

    def test_analysis_never_creates_library_and_confirmation_is_required(self):
        job = self.analyze()
        self.assertFalse(self.path.exists())
        plan = jobs.public_status(job)['preview']
        self.assertEqual(plan['conversations'], 8)
        self.assertEqual(plan['classes']['new'], 8)
        self.assertEqual(plan['inventory']['segment_count'], 8)
        self.assertGreater(plan['estimated_additional_bytes'], 0)
        for confirm in (False, 'true', 1):
            with self.assertRaises(ValueError):
                jobs.confirm(job, confirm)
        self.assertFalse(self.path.exists())
        result = self.commit(job)
        self.assertEqual(result['state'], 'done')
        self.assertEqual(result['imported'], 8)
        db = connect(self.path)
        self.assertEqual(len(list_chats(db, 'SQLite')), 8)
        self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(), [])
        db.close()

    def test_preview_does_not_upgrade_existing_schema_three_library(self):
        from chatidy.importer import parse_export
        import sqlite3
        with patch('chatidy.migrations.LATEST', 3):
            db = connect(self.path)
            upsert(db, parse_export(json.dumps([conversation(0)]).encode(), 'synthetic.json'))
            db.close()
        before = self.path.read_bytes()
        job = self.analyze()
        db = sqlite3.connect(self.path)
        self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0], 3)
        db.close()
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(self.commit(job)['state'], 'done')
        db = connect(self.path)
        self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0], 4)
        self.assertEqual(len(list_chats(db)), 8)
        db.close()

    def test_single_segment_then_archive_and_full_reimport_are_idempotent(self):
        self.seed([conversation(0)])
        job = self.analyze()
        self.assertEqual(jobs.public_status(job)['preview']['classes']['identical'], 1)
        self.assertEqual(self.commit(job)['result']['unchanged'], 1)
        other = self.analyze()
        self.assertEqual(jobs.status(other)['approval'], None)
        self.assertEqual(jobs.public_status(other)['preview']['classes']['identical'], 8)
        result = self.commit(other)
        self.assertEqual(result['imported'], 0)
        self.assertEqual(result['result']['unchanged'], 8)

    def test_batch_policies_are_class_scoped_and_never_overwrite(self):
        old = conversation(0)
        branch = conversation(1)
        branch['mapping']['answer'] = {'parent':'message','message':{'id':'extra','author':{'role':'assistant'},'content':{'parts':['Synthetic retained answer']}}}
        branch['current_node'] = 'answer'
        self.seed([old, branch])
        incoming_old = copy.deepcopy(old)
        incoming_old['update_time'] = 10
        incoming_branch = conversation(1)
        incoming_branch['update_time'] = 30
        data = json.dumps([incoming_old, incoming_branch, conversation(2)]).encode()
        job = self.analyze(data, 'synthetic.json')
        kinds = jobs.public_status(job)['preview']['classes']
        self.assertEqual((kinds['older'], kinds['branch'], kinds['new']), (1, 1, 1))
        for policies in ({'older':'skip'}, {'identity':'skip'}, {'older':'ignore'}, {'all':'skip'}):
            with self.assertRaises(ValueError):
                jobs.confirm(job, True, policies)
        result = self.commit(job, {'older':'skip','branch':'skip'})
        self.assertEqual(result['state'], 'done')
        self.assertEqual(result['result']['unchanged'], 2)
        db = connect(self.path)
        self.assertEqual(len(chat_detail(db, 'synthetic-1')['messages']), 2)
        self.assertEqual(chat_detail(db, 'synthetic-0')['chat']['updated'], 20)
        db.close()

    def test_unclear_same_version_content_is_not_overwritable(self):
        self.seed([conversation(0)])
        changed = conversation(0)
        changed['mapping']['message']['message']['content']['parts'] = ['Synthetic conflicting body']
        job = self.analyze(json.dumps([changed]).encode(), 'synthetic.json')
        self.assertEqual(jobs.public_status(job)['preview']['classes']['identity'], 1)
        with self.assertRaises(ValueError):
            jobs.confirm(job, True, {})
        db = connect(self.path)
        self.assertEqual(len(list_chats(db, 'SQLite')), 1)
        self.assertEqual(list_chats(db, 'conflicting'), [])
        db.close()

    def test_legacy_import_path_also_rejects_unclear_same_version_changes(self):
        self.seed([conversation(0)])
        changed = conversation(0)
        changed['mapping']['message']['message']['content']['parts'] = ['Synthetic ambiguous body']
        from chatidy.importer import parse_export
        db = connect(self.path)
        try:
            with self.assertRaisesRegex(ValueError, 'Unklare'):
                upsert(db, parse_export(json.dumps([changed]).encode(), 'synthetic.json'))
            self.assertEqual(len(list_chats(db, 'SQLite')), 1)
            self.assertEqual(list_chats(db, 'ambiguous'), [])
        finally:
            db.close()

    def test_library_change_after_preview_requires_a_new_decision(self):
        job = self.analyze(json.dumps([conversation(0), conversation(1)]).encode(), 'synthetic.json')
        existing = conversation(1)
        existing['update_time'] = 99
        self.seed([existing])
        value = self.commit(job)
        self.assertEqual(value['state'], 'awaiting_confirmation')
        self.assertIsNone(jobs.status(job)['approval'])
        db = connect(self.path)
        self.assertEqual(len(list_chats(db)), 1)
        db.close()
        result = self.commit(job, {'older':'skip'})
        self.assertEqual(result['state'], 'done')
        self.assertEqual(result['result']['unchanged'], 1)

    def test_interrupted_staging_and_commit_can_resume_without_implicit_initial_consent(self):
        data = json.dumps([conversation(i) for i in range(120)]).encode()
        job = jobs.create(io.BytesIO(data), len(data), 'synthetic.json', confirmation_required=True)
        original = jobs.iter_export
        def interrupted(*args):
            for i, chat in enumerate(original(*args)):
                if i == 105:
                    raise KeyboardInterrupt('Synthetic termination')
                yield chat
        with patch('chatidy.jobs.iter_export', interrupted), self.assertRaises(KeyboardInterrupt):
            jobs.run(job)
        self.assertFalse(self.path.exists())
        jobs.run(job)
        self.assertEqual(jobs.status(job)['state'], 'awaiting_confirmation')
        self.assertFalse(self.path.exists())
        self.assertEqual(self.commit(job)['imported'], 120)

    def test_newer_complete_version_is_classified_and_imported(self):
        self.seed([conversation(0)])
        changed = conversation(0)
        changed['update_time'] = 30
        changed['mapping']['message']['message']['content']['parts'] = ['Synthetic newer content']
        job = self.analyze(json.dumps([changed]).encode(), 'synthetic.json')
        self.assertEqual(jobs.public_status(job)['preview']['classes']['newer'], 1)
        self.assertEqual(self.commit(job)['state'], 'done')
        db = connect(self.path)
        self.assertEqual(len(list_chats(db, 'newer')), 1)
        self.assertEqual(list_chats(db, 'SQLite'), [])
        db.close()

    def test_required_segment_error_does_not_touch_existing_library(self):
        self.seed([conversation(0)])
        files = segmented(False)
        files[-2] = (files[-2][0], '[broken')
        data = archive(files)
        job = jobs.create(io.BytesIO(data), len(data), 'synthetic.zip', confirmation_required=True)
        jobs.run(job)
        self.assertEqual(jobs.public_status(job)['state'], 'error')
        db = connect(self.path)
        self.assertEqual([c['id'] for c in list_chats(db)], ['synthetic-0'])
        self.assertEqual(len(list_chats(db, 'SQLite')), 1)
        db.close()

    def test_changed_source_invalidates_approval_before_main_write(self):
        job = self.analyze()
        (jobs.job_path(job)/'source.zip').write_bytes(archive(segmented(False)))
        result = self.commit(job)
        self.assertEqual(result['state'], 'error')
        self.assertIn('verändert', result['error'])
        self.assertFalse(self.path.exists())
        self.assertIsNone(jobs.status(job)['approval'])

    def test_rechecked_transaction_rolls_back_on_late_conflict(self):
        self.seed([conversation(1)])
        import sqlite3
        staging = sqlite3.connect(':memory:')
        staging.execute('CREATE TABLE chats(sequence INTEGER PRIMARY KEY,payload TEXT)')
        old = conversation(1)
        old['update_time'] = 10
        from chatidy.importer import parse_export
        normalized = parse_export(json.dumps([conversation(0), old]).encode(), 'synthetic.json')
        staging.executemany('INSERT INTO chats VALUES(?,?)', [(i,json.dumps(chat)) for i,chat in enumerate(normalized)])
        staging.commit()
        with self.assertRaises(ValueError):
            import_plan.apply(self.path, staging, {})
        staging.close()
        db = connect(self.path)
        self.assertEqual([c['id'] for c in list_chats(db)], ['synthetic-1'])
        self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
        db.close()
