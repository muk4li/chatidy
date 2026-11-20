"""F-006/F-007/F-008: source subtype and date filtering are server-side."""
import unittest
from contextlib import closing
from datetime import datetime, timezone
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
            # 2025-01-01 23:30 UTC is January 2 in UTC+01:00.
            late={"id":"late","provider":"chatgpt","title":"Late","created":
                  datetime(2025,1,1,23,30,tzinfo=timezone.utc).timestamp(),
                  "metadata":{"source":"chatgpt"},
                  "messages":[{"id":"late:m","role":"user","content":"synthetic"}]}
            upsert(db,[late])
            self.assertIn("late",ids(date_from="2025-01-02",date_to="2025-01-02",
                                     date_from_offset="-60",date_to_offset="-60"))
            self.assertNotIn("late",ids(date_from="2025-01-01",date_to="2025-01-01",
                                        date_from_offset="-60",date_to_offset="-60"))
            for options in ({"source":"injected"},{"sort":"SQL"},{"date_from":"2025-99-99"},
                            {"undated":True,"date_from":"2025-01-01"},
                            {"date_from":"2025-01-01","date_from_offset":"9999"}):
                with self.assertRaises(ValueError):list_chats(db,**options)

if __name__=="__main__":unittest.main()
