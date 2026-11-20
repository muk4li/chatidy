"""PROV-001: explicit format detection, provider column and filters (synthetic data only)."""
import io
import json
import sqlite3
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from chatidy import migrations
from chatidy.conflicts import classify_chat
from chatidy.db import chat_detail, connect, list_chats, stats, upsert
from chatidy.importer import detect_format, parse_export
from legacy_schema import legacy_upsert

CHATGPT = {"id": "g1", "title": "Synthetic graph", "update_time": 10, "current_node": "n1", "mapping": {
    "n0": {"parent": None, "message": None},
    "n1": {"parent": "n0", "message": {"id": "m1", "author": {"role": "user"},
                                      "content": {"parts": ["Synthetic graph text"]}}}}}
EXTRACTOR = {"id": "e1", "title": "Synthetic extractor",
             "messages": [{"role": "user", "content": "Synthetic extractor text"}]}
# Claude-like variant with `messages` + `id` but `sender` instead of `role` (ROADMAP risk E2).
CLAUDE_LIKE = {"id": "c1", "uuid": "c1", "name": "Synthetic claude-like",
               "messages": [{"uuid": "x", "sender": "human", "text": "Synthetic"}]}


def as_zip(name, payload):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(name, json.dumps(payload))
    return buffer.getvalue()


class DetectionTests(unittest.TestCase):
    def test_known_formats_are_recognized(self):
        self.assertEqual(detect_format(CHATGPT), "chatgpt")
        self.assertEqual(detect_format(EXTRACTOR), "extractor")
        self.assertEqual(detect_format({"id": "e", "messages": []}), "extractor")
        self.assertIsNone(detect_format(CLAUDE_LIKE))
        self.assertIsNone(detect_format(["not", "a", "dict"]))

    def test_ambiguous_object_aborts(self):
        with self.assertRaisesRegex(ValueError, "Mehrdeutiges Exportformat"):
            detect_format({**CHATGPT, "messages": [{"role": "user", "content": "x"}]})

    def test_claude_like_messages_variant_is_never_read_as_extractor(self):
        # Mandatory regression test (TASKS PROV-001): single JSON and ZIP structure fallback.
        with self.assertRaisesRegex(ValueError, "unbekannte Konversation"):
            parse_export(json.dumps([CLAUDE_LIKE]).encode(), "conversations.json")
        with self.assertRaisesRegex(ValueError, "Keine erkennbaren Konversationsdateien"):
            parse_export(as_zip("data/synthetic.json", [CLAUDE_LIKE]), "export.zip")
        mixed = [EXTRACTOR, {"id": "e2", "messages": [{"role": "user"}, {"sender": "human"}]}]
        with self.assertRaisesRegex(ValueError, "unbekannte Konversation"):
            parse_export(json.dumps(mixed).encode(), "conversations.json")

    def test_parsed_chats_carry_provider(self):
        parsed = parse_export(json.dumps([CHATGPT, EXTRACTOR]).encode(), "conversations.json")
        self.assertEqual([c["provider"] for c in parsed], ["chatgpt", "chatgpt"])


class ProviderStorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "synthetic.sqlite3"

    def tearDown(self):
        self.temp.cleanup()

    def test_schema_four_library_migrates_existing_chats_to_chatgpt(self):
        with patch("chatidy.migrations.LATEST", 4):
            db = connect(self.path)
            legacy_upsert(db, parse_export(json.dumps([CHATGPT]).encode(), "conversations.json"))
            db.close()
        db = connect(self.path)
        try:
            self.assertEqual(db.execute("PRAGMA user_version").fetchone()[0], migrations.LATEST)
            self.assertEqual(chat_detail(db, "g1")["chat"]["provider"], "chatgpt")
            again = parse_export(json.dumps([CHATGPT]).encode(), "conversations.json")[0]
            self.assertEqual(classify_chat(db, again), "identical")
        finally:
            db.close()

    def test_failed_migration_keeps_schema_four(self):
        with patch("chatidy.migrations.LATEST", 4):
            connect(self.path).close()
        bad = dict(migrations.MIGRATIONS)
        bad[5] = ("INVALID SQL",)
        with patch("chatidy.migrations.MIGRATIONS", bad), self.assertRaises(sqlite3.OperationalError):
            connect(self.path)
        raw = sqlite3.connect(self.path)
        try:
            self.assertEqual(raw.execute("PRAGMA user_version").fetchone()[0], 4)
            columns = {row[1] for row in raw.execute("PRAGMA table_info(conversations)")}
            self.assertNotIn("provider", columns)
        finally:
            raw.close()

    def test_provider_is_stored_filtered_counted_and_part_of_identity(self):
        db = connect(self.path)
        try:
            chats = parse_export(json.dumps([CHATGPT]).encode(), "conversations.json")
            other = {"id": "x:1", "provider": "other", "title": "Synthetic other", "updated": 5,
                     "messages": [{"id": "o1", "role": "user", "content": "Synthetic other text"}]}
            upsert(db, chats + [other])
            self.assertEqual([c["id"] for c in list_chats(db, provider="chatgpt")], ["g1"])
            self.assertEqual([c["id"] for c in list_chats(db, provider="other")], ["x:1"])
            self.assertEqual(len(list_chats(db)), 2)
            self.assertEqual(stats(db)["providers"], {"chatgpt": 1, "other": 1})
            self.assertEqual(classify_chat(db, {**other, "provider": "chatgpt"}), "identity")
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
