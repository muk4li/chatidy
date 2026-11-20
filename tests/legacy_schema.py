"""Write chats the way pre-provider Chatidy versions did (schema 3/4, no provider column).

Migration tests build old libraries with this helper, because the current upsert
writes columns that older schemas do not have.
"""
import json


def legacy_upsert(db, chats):
    with db:
        for chat in chats:
            cid = chat["id"]
            db.execute("INSERT INTO conversations(id,title,created,updated,project,archived,metadata) "
                       "VALUES(?,?,?,?,?,?,?)",
                       (cid, chat["title"], chat.get("created"), chat.get("updated"), chat.get("project") or "",
                        int(chat.get("archived", False)), json.dumps(chat.get("metadata", {}), ensure_ascii=False)))
            db.executemany("INSERT INTO messages(id,conversation_id,role,content,timestamp,metadata,position) "
                           "VALUES(?,?,?,?,?,?,?)",
                           [(m["id"], cid, m["role"], m["content"], m.get("timestamp"),
                             json.dumps(m.get("metadata", {}), ensure_ascii=False), index)
                            for index, m in enumerate(chat["messages"])])
            db.execute("INSERT INTO search_index(conversation_id,title,body) VALUES(?,?,?)",
                       (cid, chat["title"], "\n".join(m["content"] for m in chat["messages"])))
