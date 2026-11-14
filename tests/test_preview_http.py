import json
import os
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from chatidy.server import Handler
from test_archives import archive
from test_segmented_exports import segmented


class PreviewHttpTests(unittest.TestCase):
    def test_segmented_zip_requires_one_batch_confirmation_and_preserves_reimports(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'library.sqlite3'
            server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            port = server.server_address[1]
            with patch.dict(os.environ, CHATIDY_DB=str(path), CHATIDY_PORT=str(port)):
                thread.start()
                try:
                    def request(route, data=None):
                        req = urllib.request.Request(f'http://127.0.0.1:{port}'+route, data=data,
                            headers={'X-Filename':'synthetic.zip'})
                        with urllib.request.urlopen(req, timeout=10) as response:
                            return json.load(response)
                    def wait(job, state):
                        deadline = time.monotonic()+20
                        while time.monotonic() < deadline:
                            value = request('/api/import/jobs/'+job)
                            if value['state']==state and not value['active']:
                                return value
                            if value['state']=='error':
                                self.fail(value['error'])
                            time.sleep(.02)
                        self.fail('Synthetic job did not reach '+state)
                    for iteration in range(2):
                        job = request('/api/import/analyze', archive(segmented()))['id']
                        plan = wait(job, 'awaiting_confirmation')['preview']
                        self.assertEqual(plan['inventory']['segment_count'], 8)
                        if not iteration:
                            self.assertFalse(path.exists(), 'analysis must not create the main library')
                        with self.assertRaises(urllib.error.HTTPError) as caught:
                            request('/api/import/jobs/'+job+'/confirm', b'{"confirm":false}')
                        self.assertEqual(caught.exception.code, 400)
                        caught.exception.close()
                        request('/api/import/jobs/'+job+'/confirm', b'{"confirm":true,"policies":{}}')
                        result = wait(job, 'done')
                        self.assertEqual(result['imported'], 8 if not iteration else 0)
                        self.assertEqual(request('/api/stats')['chats'], 8)
                        self.assertEqual(request('/api/stats')['messages'], 8)
                        self.assertEqual(len(request('/api/chats?q=SQLite')), 8)
                        request('/api/import/jobs/'+job+'/delete', b'{"confirm":true}')
                    self.assertEqual(request('/api/stats')['messages'], 8)
                finally:
                    server.shutdown()
                    thread.join(timeout=5)
                    server.server_close()
