"""The normal official ZIP workflow, run on Linux AND native Windows CI."""
import io
import json
import os
import tempfile
import threading
import time
import unittest
import urllib.request
import zipfile
from pathlib import Path
from http.server import ThreadingHTTPServer
from unittest.mock import patch
from chatidy.server import Handler
from chatidy.db import connect


class ZipJobHttpTests(unittest.TestCase):
    def test_official_zip_progress_cleanup_and_original_integrity(self):
        export = [{'id': 'synthetic-zip', 'title': 'Synthetic ZIP', 'current_node': 'a',
                   'mapping': {'q': {'parent': None, 'message': {'id': 'synthetic-q',
                       'author': {'role': 'user'}, 'content': {'parts': ['Synthetic SQLite question']}}},
                       'a': {'parent': 'q', 'message': {'id': 'synthetic-a',
                       'author': {'role': 'assistant'}, 'content': {'parts': ['Synthetic answer']}}}}}]
        content = io.BytesIO()
        with zipfile.ZipFile(content, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr('conversations.json', json.dumps(export))
        with tempfile.TemporaryDirectory(prefix='chatidy-zip-') as tmp:
            original = Path(tmp)/'original.zip'
            original.write_bytes(content.getvalue())
            database = Path(tmp)/'library.sqlite3'
            server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
            port = server.server_address[1]
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            with patch.dict(os.environ, CHATIDY_DB=str(database), CHATIDY_PORT=str(port)):
                thread.start()
                try:
                    def request(path, body=None):
                        req = urllib.request.Request(f'http://127.0.0.1:{port}'+path, data=body,
                            headers={'X-Filename': 'synthetic.zip'})
                        with urllib.request.urlopen(req, timeout=10) as response:
                            return json.load(response)
                    job = request('/api/import/jobs', original.read_bytes())['id']
                    deadline = time.monotonic()+20
                    while time.monotonic() < deadline:
                        value = request('/api/import/jobs/'+job)
                        if value['state'] in ('done', 'error') and not value['active']:
                            break
                        time.sleep(.05)
                    self.assertEqual(value['state'], 'done', value)
                    self.assertEqual(value['validated'], 1)
                    self.assertEqual(request('/api/stats')['messages'], 2)
                    self.assertEqual(len(request('/api/chats?q=SQLite')), 1)
                    request('/api/import/jobs/'+job+'/delete', b'{"confirm":true}')
                    self.assertEqual(request('/api/import/jobs')['count'], 0)
                    self.assertEqual(request('/api/stats')['messages'], 2)
                    self.assertEqual(original.read_bytes(), content.getvalue())
                    db = connect(database)
                    try:
                        self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
                        self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(), [])
                    finally:
                        db.close()
                finally:
                    server.shutdown()
                    thread.join(timeout=5)
                    server.server_close()
