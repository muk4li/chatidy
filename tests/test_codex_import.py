"""PROV-004: ChatGPT Codex tasks from codex.json (synthetic, modelled on the real key structure)."""
import io
import json
import tempfile
import unittest
from pathlib import Path

from chatidy.conflicts import classify_chat
from chatidy.db import chat_detail, connect, list_chats, upsert
from chatidy.importer import NON_TEXT, inspect_export, parse_export
from test_archives import archive
from test_segmented_exports import conversation


def text(value):
    return {"content_type": "text", "text": value}


def task(tid="task-1", title="Synthetic Codex task"):
    return {"id": tid, "title": title, "archived": False, "turns": [
        {"id": tid + "-u1", "role": "user", "previous_turn_id": None, "turn_status": "completed",
         "input_items": [{"type": "message", "role": "user", "content": [text("Synthetic fix request")]}]},
        {"id": tid + "-a1", "role": "assistant", "turn_status": "completed", "branch": "synthetic-branch",
         "output_items": [
             {"type": "message", "role": "assistant", "content": [
                 text("Synthetic summary"), {"content_type": "repo_file_citation", "path": "a.py",
                                             "line_range_start": 1, "line_range_end": 2}]},
             {"type": "partial_repo_snapshot", "files": [{"path": "a.py", "line_range_contents": [
                 {"content": ["secret_line = 1"], "line_range_start": 1, "line_range_end": 1}]}]},
             {"type": "pr", "pr_title": "Synthetic PR title", "pr_message": "Synthetic PR body"},
             {"type": "output_diff", "lines_added": 3, "lines_removed": 1, "files_modified": 1}]},
        {"id": tid + "-a2", "role": "assistant", "output_items": [{"type": "follow_up_diff"}]}]}


class CodexTests(unittest.TestCase):
    def test_parse_codex_json(self):
        chat = parse_export(json.dumps([task()]).encode(), "codex.json")[0]
        self.assertEqual((chat["id"], chat["provider"], chat["metadata"]["source"]), ("codex:task-1", "chatgpt", "codex"))
        self.assertEqual(chat["metadata"]["original_id"], "task-1")
        self.assertNotIn("turns", chat["metadata"])
        self.assertEqual([(m["role"], m["content"]) for m in chat["messages"]], [
            ("user", "Synthetic fix request"),
            ("assistant", "Synthetic summary\n\n[Pull Request] Synthetic PR title"),
            ("assistant", NON_TEXT)])
        self.assertNotIn("secret_line", chat["messages"][1]["content"])
        self.assertEqual(chat["messages"][1]["metadata"]["output_items"][3]["lines_added"], 3)

    def test_duplicate_turn_ids_abort(self):
        broken = task()
        broken["turns"][1]["id"] = broken["turns"][0]["id"]
        with self.assertRaisesRegex(ValueError, "Doppelte Turn-ID"):
            parse_export(json.dumps([broken]).encode(), "codex.json")

    def segmented_with(self, codex_name="codex.json", codex_body=None):
        files = [(f"conversations-{i:03d}.json", json.dumps([conversation(i)])) for i in range(2)]
        files.append((codex_name, json.dumps([task("t1"), task("t2")]) if codex_body is None else codex_body))
        return archive(files)

    def test_zip_imports_codex_next_to_conversations(self):
        data = self.segmented_with()
        inventory = inspect_export(io.BytesIO(data), "synthetic.zip")
        self.assertEqual((inventory["segment_count"], inventory["codex_conversations"]), (2, 2))
        self.assertEqual(inventory["metadata_roles"]["codex"], 1)
        ids = [c["id"] for c in parse_export(data, "synthetic.zip")]
        self.assertEqual(ids, ["synthetic-0", "synthetic-1", "codex:t1", "codex:t2"])

    def test_unrecognized_or_misplaced_codex_is_not_imported(self):
        for name, body in (("codex.json", "{broken"), ("codex.json", json.dumps({"tasks": []})),
                           ("codex.json", json.dumps([{"id": "x", "turns": [{"no_role": 1}]}])),
                           ("other/codex.json", None)):
            with self.subTest(name=name, body=(body or "")[:20]):
                data = self.segmented_with(name, body)
                inventory = inspect_export(io.BytesIO(data), "synthetic.zip")
                self.assertEqual(inventory["codex_conversations"], 0)
                self.assertEqual(len(parse_export(data, "synthetic.zip")), 2)
                if name == "codex.json":
                    self.assertIn("codex.json nicht als Codex-Aufgaben erkannt; wird nicht importiert.", inventory["warnings"])

    def test_library_reimport_and_header_marker(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = connect(Path(tmp) / "synthetic.sqlite3")
            try:
                data = self.segmented_with()
                upsert(db, parse_export(data, "synthetic.zip"))
                self.assertEqual(len(list_chats(db, provider="chatgpt")), 4)
                self.assertEqual(len(list_chats(db, "Synthetic PR title")), 2)
                self.assertEqual(list_chats(db, "secret_line"), [])
                self.assertEqual(chat_detail(db, "codex:t1")["chat"]["metadata"]["source"], "codex")
                for chat in parse_export(data, "synthetic.zip"):
                    self.assertEqual(classify_chat(db, chat), "identical")
            finally:
                db.close()


class StructureFallbackTests(unittest.TestCase):
    def test_claude_conversations_under_unofficial_name_are_recognized(self):
        claude = {"uuid": "c1", "name": "Synthetic", "chat_messages": [
            {"uuid": "m1", "sender": "human", "text": "Synthetic", "content": []}]}
        chats = parse_export(archive([("data/export-part.json", json.dumps([claude]))]), "synthetic.zip")
        self.assertEqual([c["id"] for c in chats], ["claude:c1"])


if __name__ == "__main__":
    unittest.main()
