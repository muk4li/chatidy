import io
import json
import os
import tempfile
import tracemalloc
import threading
import time
import urllib.request
from http.server import ThreadingHTTPServer
from chatidy.server import Handler
import unittest
from pathlib import Path
from unittest.mock import patch
from chatidy import jobs
from chatidy.db import connect, stats
from chatidy.importer import iter_export
from chatidy.streaming import json_values
from chatidy.importer import unique_object, invalid_constant


def payload(count=205):
    return json.dumps([{'id': f'synthetic-{i}', 'messages': [
        {'role': 'user', 'content': f'Synthetic body {i}'}]} for i in range(count)]).encode()


class JobTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp.name) / 'synthetic.sqlite3'
        self.env = patch.dict(os.environ, CHATIDY_DB=str(self.db_path))
        self.env.start()
        connect(self.db_path).close()

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def create(self, body=None):
        data = payload() if body is None else body
        return jobs.create(io.BytesIO(data), len(data), 'synthetic.json')

    def count(self):
        db = connect(self.db_path)
        try:
            return stats(db)['chats']
        finally:
            db.close()

    def test_interrupted_staging_resumes_without_partial_library(self):
        job = self.create()
        original = jobs.iter_export
        def interrupted(*args):
            for i, chat in enumerate(original(*args)):
                if i == 105:
                    raise KeyboardInterrupt('Synthetic termination')
                yield chat
        with patch('chatidy.jobs.iter_export', interrupted), self.assertRaises(KeyboardInterrupt):
            jobs.run(job)
        self.assertEqual(jobs.status(job)['validated'], 100)
        self.assertEqual(self.count(), 0)
        jobs.run(job)
        self.assertEqual(jobs.status(job)['state'], 'done')
        self.assertEqual(self.count(), 205)
        jobs.run(job)
        self.assertEqual(self.count(), 205)

    def test_late_json_error_never_changes_library(self):
        job = self.create(payload()[:-1] + b',null]')
        jobs.run(job)
        self.assertEqual(jobs.status(job)['state'], 'error')
        self.assertEqual(self.count(), 0)

    def test_commit_failure_can_resume(self):
        job = self.create()
        with patch('chatidy.jobs.upsert', side_effect=RuntimeError('Synthetic crash')):
            jobs.run(job)
        self.assertEqual(jobs.status(job)['state'], 'error')
        self.assertEqual(self.count(), 0)
        jobs.run(job)
        self.assertEqual(self.count(), 205)

    def test_changed_source_and_invalid_job_paths_rejected(self):
        job = self.create()
        (jobs.job_path(job) / 'source.json').write_bytes(payload(1))
        jobs.run(job)
        self.assertIn('verändert', jobs.status(job)['error'])
        self.assertEqual(self.count(), 0)
        with self.assertRaises(ValueError):
            jobs.status('../../source')

    def test_incomplete_upload_does_not_leave_resumable_source(self):
        with self.assertRaisesRegex(ValueError, 'unvollständig'):
            jobs.create(io.BytesIO(b'['), 50, 'synthetic.json')
        root = self.db_path.parent / 'import-jobs'
        self.assertEqual(list(root.iterdir()), [])

    def test_streamed_json_chunk_boundaries_bom_and_envelope(self):
        decoder = json.JSONDecoder(object_pairs_hook=unique_object, parse_constant=invalid_constant)
        for raw in (b'\xef\xbb\xbf[{"id":"synthetic"}]', b'{"conversations":[{"id":"synthetic"}]}'):
            self.assertEqual(len(list(json_values(io.BytesIO(raw), [1000], decoder, chunk_size=1))), 1)
        for raw in (b'[{}] trailing', b'[{},]', b'[{', b'[{}]null'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                list(json_values(io.BytesIO(raw), [1000], decoder, chunk_size=1))

    def test_http_upload_status_and_resume(self):
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        port = server.server_address[1]
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        with patch.dict(os.environ, CHATIDY_PORT=str(port)):
            thread.start()
            try:
                def request(path, body=None):
                    req = urllib.request.Request(f'http://127.0.0.1:{port}'+path,
                        data=body, headers={'X-Filename': 'synthetic.json'})
                    with urllib.request.urlopen(req, timeout=5) as response:
                        return json.load(response)
                job = request('/api/import/jobs', payload(3))['id']
                for _ in range(100):
                    state = request('/api/import/jobs/'+job)
                    if state['state'] in ('done', 'error'):
                        break
                    time.sleep(.02)
                self.assertEqual(state['state'], 'done', state)
                self.assertEqual(state['imported'], 3)
                self.assertNotIn('sha256', state)
                request('/api/import/jobs/'+job+'/resume', b'{}')
                self.assertEqual(self.count(), 3)
            finally:
                server.shutdown()
                thread.join(timeout=5)
                server.server_close()

    def test_array_memory_is_bounded_by_conversation_not_export(self):
        data = json.dumps([{'id': f'synthetic-{i}', 'messages': [
            {'role': 'user', 'content': 'S' * 4000}]} for i in range(3000)]).encode()
        source = io.BytesIO(data)
        tracemalloc.start()
        try:
            self.assertEqual(sum(1 for _ in iter_export(source, 'synthetic.json')), 3000)
            _, peak = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()
        self.assertLess(peak, 2 * 1024 * 1024)
