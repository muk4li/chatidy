"""F-006/F-007/F-008: source subtype and date filtering are server-side."""
import unittest
from contextlib import closing
from chatidy.db import connect, list_chats, upsert

class SourceDateTests(unittest.TestCase):
    def test_independent_source_and_date_filters(self):
        with closing(connect(":memory:")) as db:
            samples=[
                {"id":"normal","provider":"chatgpt","title":"ChatGPT","created":1704067200,
                 "metadata":{"source":"chatgpt"}},
                {"id":"codex:task","provider":"chatgpt","title":"Codex","created":None,
                 "metadata":{"source":"codex"}},
                {"id":"claude:one","provider":"claude","title":"Claude","created":1735689600,
                 "metadata":{"source":"claude"}}]
            for item in samples:
                item["messages"]=[{"id":item["id"]+":m","role":"user","content":"synthetic"}]
            upsert(db,samples)
            ids=lambda **kw: {x["id"] for x in list_chats(db,**kw)}
            self.assertEqual(ids(source="codex"),{"codex:task"})
            self.assertEqual(ids(source="codex",provider="chatgpt"),{"codex:task"})
            self.assertEqual(ids(provider="claude"),{"claude:one"})
            self.assertEqual(ids(undated=True),{"codex:task"})
            self.assertEqual(ids(date_from="2025-01-01",date_to="2025-01-01"),{"claude:one"})
            self.assertEqual(ids(date_to="2024-01-01"),{"normal"})
            self.assertEqual([x["id"] for x in list_chats(db,sort="oldest")][0],"codex:task")
            for options in ({"source":"injected"},{"sort":"SQL"},{"date_from":"2025-99-99"},
                            {"undated":True,"date_from":"2025-01-01"}):
                with self.assertRaises(ValueError):list_chats(db,**options)

if __name__=="__main__":unittest.main()
