"""F-009: application deep links are private and resolve to the same SPA."""
import os
import tempfile
import threading
import unittest
import urllib.request
import urllib.error
from http.server import ThreadingHTTPServer
from unittest.mock import patch
from chatidy.server import Handler

class DeepLinkTests(unittest.TestCase):
    def test_deep_links_are_same_app_in_local_mode(self):
        with tempfile.TemporaryDirectory() as td:
            with patch.dict(os.environ,CHATIDY_DB=td+"/test.sqlite3",CHATIDY_AUTH_REQUIRED="0",CHATIDY_PUBLIC_ORIGIN=""):
                server=ThreadingHTTPServer(("127.0.0.1",0),Handler)
                os.environ["CHATIDY_PORT"]=str(server.server_address[1])
                thread=threading.Thread(target=server.serve_forever,daemon=True)
                thread.start()
                try:
                    url="http://127.0.0.1:"+str(server.server_address[1])
                    with urllib.request.urlopen(url+"/app") as response:
                        main=response.read()
                    for path in ("/app/import","/app/inbox","/app/archive","/app/folders/12","/app/chats/codex%3Atask","/app/smart/4"):
                        with self.subTest(path=path):
                            with urllib.request.urlopen(url+path) as response:
                                self.assertEqual(response.status,200)
                                self.assertEqual(response.read(),main)
                finally:
                    server.shutdown()
                    thread.join(timeout=5)
                    server.server_close()

if __name__=="__main__":unittest.main()
