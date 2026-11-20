"""SEARCH-001: full-text index without the non-text marker; migration 6 rebuilds it."""
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from chatidy import migrations
from chatidy.db import chat_detail, connect, list_chats, upsert
from chatidy.importer import NON_TEXT
from legacy_schema import legacy_upsert
from test_reading_view import thinking_export
from chatidy.importer import parse_export


class SearchIndexTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "synthetic.sqlite3"

    def tearDown(self):
        self.temp.cleanup()

    def chats(self):
        return parse_export(json.dumps(thinking_export()).encode(), "conversations.json")

    def test_marker_matches_migration_sql(self):
        self.assertIn("'" + NON_TEXT + "'", " ".join(migrations.MIGRATIONS[6]))

    def test_new_imports_do_not_index_marker(self):
        db = connect(self.path)
        try:
            upsert(db, self.chats())
            self.assertEqual(list_chats(db, "Inhalt"), [])
            self.assertEqual(len(list_chats(db, "Synthetische Antwort")), 1)
            self.assertEqual(chat_detail(db, "think-1")["messages"][1]["content"], NON_TEXT, "stored content unchanged")
        finally:
            db.close()

    def test_content_rules_ignore_non_text_marker_on_import_and_rule_creation(self):
        from chatidy.db import create_folder, create_rule
        db = connect(self.path)
        try:
            placeholder_folder = create_folder(db, "Synthetic marker")
            text_folder = create_folder(db, "Synthetic text")
            # Rules created first must not assign a chat just because of a marker.
            create_rule(db, "content", "Nicht-textueller Inhalt", placeholder_folder)
            create_rule(db, "content", "Synthetische Antwort", text_folder)
            upsert(db, self.chats())
            members = db.execute("SELECT folder_id FROM memberships WHERE conversation_id='think-1'").fetchall()
            self.assertNotIn(placeholder_folder, [row[0] for row in members])
            self.assertIn(text_folder, [row[0] for row in members])
            # A rule created later must also ignore already stored marker nodes.
            late = create_folder(db, "Synthetic late marker")
            create_rule(db, "content", "Nicht-textueller", late)
            members = db.execute("SELECT folder_id FROM memberships WHERE conversation_id='think-1'").fetchall()
            self.assertNotIn(late, [row[0] for row in members])
            self.assertEqual(chat_detail(db, "think-1")["messages"][1]["content"], NON_TEXT)
        finally:
            db.close()

    def test_migration_rebuilds_old_index_and_keeps_data(self):
        with patch("chatidy.migrations.LATEST", 5):
            db = connect(self.path)
            chats = self.chats()
            legacy_upsert(db, chats)  # old behaviour: marker is part of the indexed body
            self.assertEqual(len(list_chats(db, "Inhalt")), 1)
            before = chat_detail(db, "think-1")
            db.close()
        db = connect(self.path)
        try:
            self.assertEqual(db.execute("PRAGMA user_version").fetchone()[0], migrations.LATEST)
            self.assertEqual(list_chats(db, "Inhalt"), [])
            self.assertEqual(len(list_chats(db, "Synthetische Frage")), 1)
            self.assertEqual(len(list_chats(db, "Denken")), 1, "titles stay searchable")
            self.assertEqual(chat_detail(db, "think-1"), before)
            self.assertEqual(db.execute("SELECT count(*) FROM search_index").fetchone()[0], 1)
        finally:
            db.close()

    def test_failed_rebuild_keeps_old_index(self):
        with patch("chatidy.migrations.LATEST", 5):
            db = connect(self.path)
            legacy_upsert(db, self.chats())
            db.close()
        bad = dict(migrations.MIGRATIONS)
        bad[6] = (bad[6][0], "INVALID SQL")
        with patch("chatidy.migrations.MIGRATIONS", bad), self.assertRaises(sqlite3.OperationalError):
            connect(self.path)
        raw = sqlite3.connect(self.path)
        try:
            self.assertEqual(raw.execute("PRAGMA user_version").fetchone()[0], 5)
            self.assertEqual(raw.execute("SELECT count(*) FROM search_index").fetchone()[0], 1)
        finally:
            raw.close()


if __name__ == "__main__":
    unittest.main()
