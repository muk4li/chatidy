import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from chatidy.db import connect, upsert, list_chats, create_folder, change_folder, assign, create_rule, chat_detail, stats
from chatidy.importer import parse_chat, parse_export

def sample():
    return [{"id":"test-1","title":"Python und Datenbanken","create_time":1710000000,
      "update_time":1710000300,"current_node":"n2","mapping":{
       "n0":{"parent":None,"message":None},
       "n1":{"parent":"n0","message":{"id":"m1","author":{"role":"user"},
        "content":{"parts":["Ich suche SQLite Beispiele"]},"create_time":1710000000}},
       "n2":{"parent":"n1","message":{"id":"m2","author":{"role":"assistant"},
        "content":{"parts":["Hier ist deine Abfrage"]},"create_time":1710000300}},
       "side":{"parent":"n0","message":{"id":"side","author":{"role":"user"},
        "content":{"parts":["alternative branch"]},"create_time":1710000001}}}}]

class ImporterTests(unittest.TestCase):
    def test_active_branch_only(self):
        parsed=parse_chat(sample()[0])
        self.assertEqual(len(parsed["messages"]),2)
        self.assertNotIn("alternative branch","\n".join(m["content"] for m in parsed["messages"]))
    def test_zip_import(self):
        data=json.dumps(sample()).encode()
        buff=io.BytesIO()
        with zipfile.ZipFile(buff,"w") as archive: archive.writestr("nested/conversations.json",data)
        self.assertEqual(len(parse_export(buff.getvalue(),"export.zip")),1)
    def test_extractor_json_adapter(self):
        source={"id":"high-fidelity-1","title":"Extractor Export",
                "created":"2026-11-11T10:20:00Z","project_id":"project-123",
                "messages":[{"role":"user","content":"Hallo","timestamp":"2026-11-11T10:20:01Z"},
                            {"role":"assistant","content":"Antwort","timestamp":"2026-11-11T10:20:02Z"}]}
        parsed=parse_export(json.dumps(source).encode(),"extractor.json")
        self.assertEqual(parsed[0]["project"],"project-123")
        self.assertEqual(len(parsed[0]["messages"]),2)
        self.assertTrue(parsed[0]["messages"][0]["timestamp"]>0)

    def test_reject_bad_export(self):
        with self.assertRaises(ValueError):parse_export(b'{"wrong": "format"}',"conversations.json")
        with self.assertRaises(ValueError):parse_export(b"hello","export.txt")

class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.db=connect(Path(self.temp.name)/"test.sqlite3")
        self.chats=parse_export(json.dumps(sample()).encode(),"conversations.json")
        upsert(self.db,self.chats)
    def tearDown(self):
        self.db.close();self.temp.cleanup()
    def test_full_text_search(self):
        self.assertEqual(len(list_chats(self.db,"SQLite")),1)
        self.assertEqual(len(list_chats(self.db,"doesnotexist")),0)
        self.assertEqual(len(list_chats(self.db)),1)
    def test_nested_folders_and_multiple_memberships(self):
        root=create_folder(self.db,"Work")
        a=create_folder(self.db,"Python",root);b=create_folder(self.db,"Database",root)
        assign(self.db,"test-1",[a,b])
        self.assertEqual(set(chat_detail(self.db,"test-1")["folders"]),{a,b})
        self.assertEqual(len(list_chats(self.db,folder=a)),1)
        with self.assertRaises(ValueError):change_folder(self.db,root,parent_id=a)
    def test_rules_import_idempotency(self):
        folder=create_folder(self.db,"Sqlitewissen")
        create_rule(self.db,"content","sqlite",folder)
        self.assertIn(folder,chat_detail(self.db,"test-1")["folders"])
        upsert(self.db,self.chats)
        self.assertIn(folder,chat_detail(self.db,"test-1")["folders"])
        self.assertEqual(stats(self.db)["messages"],2)
    def test_reviews_stay_across_reimport(self):
        folder=create_folder(self.db,"Favorites")
        assign(self.db,"test-1",[folder])
        upsert(self.db,self.chats)
        self.assertEqual(stats(self.db)["inbox"],0)
        self.assertIn(folder,chat_detail(self.db,"test-1")["folders"])

if __name__=="__main__":
    unittest.main()
