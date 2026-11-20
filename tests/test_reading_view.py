import json
import os
import shutil
import subprocess
import tempfile
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from chatidy.conflicts import classify_chat
from chatidy.db import chat_detail, connect, upsert
from chatidy.importer import parse_export
from chatidy.server import Handler

ROOT = Path(__file__).resolve().parents[1]


def thinking_export():
    def node(nid, parent, role, content):
        return {"id": nid, "parent": parent, "message": None if role is None else
                {"id": "m-"+nid, "author": {"role": role}, "content": content, "create_time": 1710000000}}
    mapping = {
        "client-created-root": {"id": "client-created-root", "parent": None, "message": None},
        "u": node("u", "client-created-root", "user", {"content_type": "text", "parts": ["Synthetische Frage"]}),
        "t": node("t", "u", "assistant", {"content_type": "thoughts", "thoughts": [
            {"summary": "Synthetischer Plan", "content": "Schritt eins", "chunks": [], "finished": True}],
            "source_analysis_msg_id": "x"}),
        "r": node("r", "t", "assistant", {"content_type": "reasoning_recap", "content": "Nachgedacht für 3s"}),
        "a": node("a", "r", "assistant", {"content_type": "text", "parts": ["Synthetische Antwort"]}),
    }
    return [{"id": "think-1", "title": "Denken", "create_time": 1710000000, "update_time": 1710000100,
             "current_node": "a", "mapping": mapping}]


class ReadingViewTests(unittest.TestCase):
    def test_reading_view_logic_with_node(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("Node.js nicht installiert; reine JS-Logik nicht geprüft.")
        result = subprocess.run([node, str(ROOT/"tests"/"reading_view.test.cjs")],
                                capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_thinking_messages_keep_raw_metadata_and_stored_content(self):
        # Display is derived from metadata; stored content and reimport identity stay unchanged.
        with tempfile.TemporaryDirectory() as tmp:
            db = connect(Path(tmp)/"t.sqlite3")
            try:
                chats = parse_export(json.dumps(thinking_export()).encode(), "conversations.json")
                upsert(db, chats)
                messages = chat_detail(db, "think-1")["messages"]
                self.assertEqual([m["content"] for m in messages],
                                 ["Synthetische Frage", "[Nicht-textueller Inhalt]",
                                  "[Nicht-textueller Inhalt]", "Synthetische Antwort"])
                self.assertEqual(messages[1]["metadata"]["content"]["content_type"], "thoughts")
                self.assertEqual(messages[1]["metadata"]["content"]["thoughts"][0]["summary"], "Synthetischer Plan")
                self.assertEqual(messages[2]["metadata"]["content"]["content"], "Nachgedacht für 3s")
                again = parse_export(json.dumps(thinking_export()).encode(), "conversations.json")[0]
                self.assertEqual(classify_chat(db, again), "identical")
            finally:
                db.close()

    def test_reading_script_is_served_before_app(self):
        html = (ROOT/"web"/"index.html").read_text(encoding="utf-8")
        self.assertLess(html.index('src="/reading.js"'), html.index('src="/app.js"'))
        with tempfile.TemporaryDirectory() as tmp:
            server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
            port = server.server_address[1]
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            with patch.dict(os.environ, CHATIDY_DB=str(Path(tmp)/"l.sqlite3"), CHATIDY_PORT=str(port)):
                thread.start()
                try:
                    with urllib.request.urlopen(f"http://127.0.0.1:{port}/reading.js", timeout=10) as response:
                        self.assertIn("javascript", response.headers["Content-Type"])
                        self.assertIn(b"function readingItems", response.read())
                finally:
                    server.shutdown()
                    server.server_close()


if __name__ == "__main__":
    unittest.main()
