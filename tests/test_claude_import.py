"""PROV-002a: Claude export adapter (synthetic fixtures modelled on the real key structure)."""
import io
import json
import os
import tempfile
import threading
import time
import unittest
import urllib.request
import zipfile
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from chatidy.conflicts import classify_chat
from chatidy.db import chat_detail, connect, list_chats, stats, upsert
from chatidy.importer import inspect_export, parse_export
from chatidy.server import Handler

ROOT_PARENT = "00000000-0000-4000-8000-000000000000"


def message(uuid, sender, parent=ROOT_PARENT, text="", content=None, created="2026-11-01T10:00:00Z", **extra):
    return {"uuid": uuid, "sender": sender, "text": text, "content": content if content is not None else
            ([{"type": "text", "text": text}] if text else []), "created_at": created,
            "updated_at": created, "parent_message_uuid": parent, "attachments": [], "files": [], **extra}


def conversation(uuid="conv-1", messages=None, name="Synthetic Claude chat", updated="2026-11-01T10:05:00Z"):
    if messages is None:
        messages = [message("q1", "human", text="Synthetic question"),
                    message("a1", "assistant", parent="q1", text="Synthetic answer", created="2026-11-01T10:01:00Z")]
    return {"uuid": uuid, "name": name, "summary": "", "created_at": "2026-11-01T10:00:00Z",
            "updated_at": updated, "account": {"uuid": "synthetic-account"}, "chat_messages": messages}


def parse(conversations, name="conversations.json"):
    return parse_export(json.dumps(conversations).encode(), name)


def zip_bytes(files):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for path, payload in files.items():
            archive.writestr(path, json.dumps(payload))
    return buffer.getvalue()


class ClaudeParsingTests(unittest.TestCase):
    def test_basic_mapping(self):
        chat = parse([conversation()])[0]
        self.assertEqual(chat["id"], "claude:conv-1")
        self.assertEqual(chat["provider"], "claude")
        self.assertEqual(chat["title"], "Synthetic Claude chat")
        self.assertEqual(chat["metadata"]["original_id"], "conv-1")
        self.assertNotIn("chat_messages", chat["metadata"])
        self.assertEqual([(m["id"], m["role"], m["content"]) for m in chat["messages"]],
                         [("q1", "user", "Synthetic question"), ("a1", "assistant", "Synthetic answer")])
        self.assertIsInstance(chat["created"], float)
        self.assertGreater(chat["updated"], chat["created"])

    def test_text_comes_from_text_blocks_and_tool_data_is_kept_raw(self):
        blocks = [{"type": "thinking", "thinking": "", "thinking_hidden": True},
                  {"type": "tool_use", "name": "synthetic_tool", "input": {"query": "synthetic"}},
                  {"type": "tool_result", "content": [{"type": "text", "text": "Synthetic tool output"}]},
                  {"type": "text", "text": "Part one", "citations": [{"details": {"url": "https://example.invalid/x"}}]},
                  {"type": "future_block_type", "payload": 1},
                  {"type": "text", "text": "Part two"}]
        msgs = [message("q1", "human", text="Q"),
                message("a1", "assistant", parent="q1", text="summary field", content=blocks, created="2026-11-01T10:01:00Z")]
        answer = parse([conversation(messages=msgs)])[0]["messages"][1]
        self.assertEqual(answer["content"], "Part one\n\nPart two")
        self.assertNotIn("Synthetic tool output", answer["content"])
        self.assertEqual([b["type"] for b in answer["metadata"]["content"]],
                         ["thinking", "tool_use", "tool_result", "text", "future_block_type", "text"])

    def test_fallback_text_field_placeholder_and_attachments(self):
        msgs = [message("q1", "human", text="Only text field", content=[],
                        attachments=[{"file_name": "", "file_type": "txt", "file_size": 3, "extracted_content": "Pasted synthetic"},
                                     {"file_name": "notes.txt", "extracted_content": "Named synthetic"}],
                        files=[{"file_name": "image.png", "file_uuid": "f1"}]),
                message("a1", "assistant", parent="q1", content=[{"type": "tool_use", "name": "x", "input": {}}],
                        created="2026-11-01T10:01:00Z")]
        chat = parse([conversation(messages=msgs)])[0]
        self.assertEqual(chat["messages"][0]["content"],
                         "Only text field\n\n[Anhang]\nPasted synthetic\n\n[Anhang: notes.txt]\nNamed synthetic")
        self.assertEqual(chat["messages"][0]["metadata"]["files"][0]["file_name"], "image.png")
        self.assertEqual(chat["messages"][1]["content"], "[Nicht-textueller Inhalt]")

    def test_branches_latest_leaf_wins_and_inactive_branch_is_kept(self):
        msgs = [message("a2", "assistant", parent="q2", text="Answer to edit", created="2026-11-01T10:04:00Z"),
                message("q1", "human", text="Question"),
                message("a1", "assistant", parent="q1", text="First answer", created="2026-11-01T10:01:00Z"),
                message("q2", "human", parent="a1", text="Old follow-up", created="2026-11-01T10:02:00Z"),
                message("q2b", "human", parent="a1", text="Edited follow-up", created="2026-11-01T10:03:00Z"),
                message("a2b", "assistant", parent="q2b", text="Newest answer", created="2026-11-01T10:06:00Z")]
        chat = parse([conversation(messages=msgs)])[0]
        self.assertEqual([m["id"] for m in chat["messages"]], ["q1", "a1", "q2b", "a2b"])
        self.assertEqual(sorted(m["uuid"] for m in chat["metadata"]["inactive_branch_messages"]), ["a2", "q2"])

    def test_messages_without_parent_fields_keep_list_order(self):
        msgs = [{k: v for k, v in message(i, s, text=i).items() if k != "parent_message_uuid"}
                for i, s in (("q1", "human"), ("a1", "assistant"))]
        self.assertEqual([m["id"] for m in parse([conversation(messages=msgs)])[0]["messages"]], ["q1", "a1"])

    def test_ambiguous_or_broken_graphs_abort(self):
        cycle = [message("q1", "human", parent="a1", text="x"), message("a1", "assistant", parent="q1", text="y")]
        tie = [message("q1", "human", text="x"),
               message("a1", "assistant", parent="q1", text="y", created="2026-11-01T10:01:00Z"),
               message("a2", "assistant", parent="q1", text="z", created="2026-11-01T10:01:00Z")]
        duplicate = [message("q1", "human", text="x"), message("q1", "assistant", parent="q1", text="y")]
        for msgs, pattern in ((cycle, "Zyklus"), (tie, "gleich neue"), (duplicate, "Doppelte Nachrichten-ID")):
            with self.subTest(pattern=pattern), self.assertRaisesRegex(ValueError, pattern):
                parse([conversation(messages=msgs)])

    def test_empty_conversation_and_empty_title(self):
        chat = parse([conversation(messages=[], name="")])[0]
        self.assertEqual((chat["title"], chat["messages"]), ("Ohne Titel", []))

    def test_manifest_and_other_category_zips_explain_themselves(self):
        manifest = {"version": "1.0", "total_files": 5, "data_files": [{"category": "conversations"}]}
        with self.assertRaisesRegex(ValueError, "Claude-Export-Manifest"):
            parse(manifest, "manifest.json")
        cases = {"Konto- und Login-Daten": {"users.json": [{"uuid": "u"}], "login_history.json": {"login_events": []}},
                 "Claude-Code-Routinen": {"x/routines.json": {"claude_code_cloud": []}},
                 "Artifacts": {"artifacts/a/artifact.json": {"id": "a", "kind": "page"}}}
        for label, files in cases.items():
            with self.subTest(label=label), self.assertRaisesRegex(ValueError, label + r".*conversations-NNN\.zip"):
                parse_export(zip_bytes(files), "export.zip")


class ClaudeLibraryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = connect(Path(self.temp.name) / "synthetic.sqlite3")

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def test_zip_import_mixed_library_and_idempotent_reimport(self):
        archive = zip_bytes({"conversations.json": [conversation()]})
        self.assertEqual(inspect_export(io.BytesIO(archive), "conversations-000.zip")["format"], "official_classic")
        chatgpt = {"id": "g1", "title": "Synthetic ChatGPT", "update_time": 1, "current_node": "n1", "mapping": {
            "n0": {"parent": None, "message": None},
            "n1": {"parent": "n0", "message": {"id": "m1", "author": {"role": "user"}, "content": {"parts": ["Hi"]}}}}}
        upsert(self.db, parse_export(archive, "conversations-000.zip") + parse([chatgpt]))
        self.assertEqual(stats(self.db)["providers"], {"chatgpt": 1, "claude": 1})
        self.assertEqual([c["id"] for c in list_chats(self.db, provider="claude")], ["claude:conv-1"])
        self.assertEqual(len(list_chats(self.db, "Synthetic answer")), 1)
        detail = chat_detail(self.db, "claude:conv-1")
        self.assertEqual(detail["chat"]["provider"], "claude")
        self.assertEqual(detail["messages"][1]["metadata"]["sender"], "assistant")
        again = parse_export(archive, "conversations-000.zip")[0]
        self.assertEqual(classify_chat(self.db, again), "identical")

    def test_continued_conversation_is_complete_and_branch_switch_is_reported(self):
        upsert(self.db, parse([conversation()]))
        longer = conversation(updated="2026-11-02T10:00:00Z", messages=conversation()["chat_messages"] + [
            message("q2", "human", parent="a1", text="More", created="2026-11-02T09:00:00Z")])
        self.assertEqual(classify_chat(self.db, parse([longer])[0]), "newer")
        switched = conversation(updated="2026-11-02T10:00:00Z", messages=[
            message("q1", "human", text="Synthetic question"),
            message("a1", "assistant", parent="q1", text="Synthetic answer", created="2026-11-01T10:01:00Z"),
            message("a1b", "assistant", parent="q1", text="Regenerated", created="2026-11-02T09:00:00Z")])
        self.assertEqual(classify_chat(self.db, parse([switched])[0]), "branch")


class ClaudeHttpJobTests(unittest.TestCase):
    def test_preview_confirm_and_category_hint_through_import_jobs(self):
        with tempfile.TemporaryDirectory() as tmp:
            server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
            port = server.server_address[1]
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            with patch.dict(os.environ, CHATIDY_DB=str(Path(tmp)/"library.sqlite3"), CHATIDY_PORT=str(port)):
                thread.start()
                try:
                    def request(route, data=None):
                        req = urllib.request.Request(f"http://127.0.0.1:{port}"+route, data=data,
                                                     headers={"X-Filename": "conversations-000.zip"})
                        with urllib.request.urlopen(req, timeout=10) as response:
                            return json.load(response)

                    def wait(job, states):
                        deadline = time.monotonic() + 20
                        while time.monotonic() < deadline:
                            value = request("/api/import/jobs/"+job)
                            if value["state"] in states and not value["active"]:
                                return value
                            time.sleep(.02)
                        self.fail("job did not finish")

                    job = request("/api/import/analyze", zip_bytes({"conversations.json": [conversation()]}))["id"]
                    plan = wait(job, {"awaiting_confirmation"})["preview"]
                    self.assertEqual((plan["conversations"], plan["classes"]["new"]), (1, 1))
                    request("/api/import/jobs/"+job+"/confirm", b'{"confirm":true,"policies":{}}')
                    self.assertEqual(wait(job, {"done"})["imported"], 1)
                    self.assertEqual([c["id"] for c in request("/api/chats?provider=claude")], ["claude:conv-1"])
                    self.assertEqual(request("/api/stats")["providers"], {"claude": 1})
                    other = request("/api/import/analyze", zip_bytes({"users.json": [{"uuid": "u"}]}))["id"]
                    failed = wait(other, {"error"})
                    self.assertIn("Konto- und Login-Daten", failed["error"])
                    self.assertEqual(request("/api/stats")["chats"], 1)
                finally:
                    server.shutdown()
                    thread.join(timeout=5)
                    server.server_close()


if __name__ == "__main__":
    unittest.main()
