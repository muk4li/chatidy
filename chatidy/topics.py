"""Local deterministic topic exploration from ChatGPT titles and message text.

Topic views do not permanently assign categories. They show explicit token matches.
"""
import re
from collections import defaultdict
from .db import list_folders

TOKEN=re.compile(r"(?u)\b[a-zäöüß][a-zäöüß0-9_+#.-]{3,}\b",re.I)
HASHTAG=re.compile(r"(?u)#[\wäöüß]{2,}",re.I)
STOP={"this","that","with","have","from","there","what","which","where","when",
      "will","would","could","should","about","your","their","they","them","then",
      "just","some","also","only","into","hello","thanks","please","oder","aber",
      "dann","wenn","dass","weil","auch","schon","noch","hier","dort","einer",
      "einem","eine","einen","eines","etwas","dieser","diese","dieses","euch",
      "deine","deinen","deiner","meine","meinen","meiner","nicht","mehr","sehr",
      "werden","wurde","wurden","kannst","können","möchte","machen","haben",
      "eine","sich","über","unter","nach","beim","fürs","durch","wieder","bitte",
      "hallo","danke","chatgpt","assistant","user","https","http","www","com"}

def topics(db,limit=60):
    index=defaultdict(set)
    titles={}
    for row in db.execute("SELECT id,title FROM conversations"):
        cid,title=row["id"],row["title"] or ""
        titles[cid]=title
        for token in set(x.casefold() for x in TOKEN.findall(title)):
            if token not in STOP and len(token)>3:index[("title",token)].add(cid)
        for tag in set(x.casefold() for x in HASHTAG.findall(title)):
            index[("hashtag",tag)].add(cid)
    # Scan a bounded message prefix per chat to avoid enormous processing overhead.
    for row in db.execute("""SELECT conversation_id,substr(content,1,3500) AS snippet
                             FROM messages WHERE role='user'
                             ORDER BY conversation_id,timestamp"""):
        cid=row["conversation_id"]
        for tag in set(x.casefold() for x in HASHTAG.findall(row["snippet"] or "")):
            index[("hashtag",tag)].add(cid)
    for row in db.execute("""SELECT f.id,f.name,m.conversation_id FROM memberships m
                             JOIN folders f ON f.id=m.folder_id"""):
        index[("group",str(row["id"])+"|"+row["name"])].add(row["conversation_id"])
    result=[]
    for (kind,term),ids in index.items():
        minimum=2 if kind in ("group","hashtag") else 3
        if len(ids)<minimum:continue
        result.append({"type":kind,"label":term.split("|",1)[-1],
                       "count":len(ids),"conversation_ids":sorted(ids)[:500],
                       "examples":[titles.get(cid,"Ohne Titel") for cid in sorted(ids)[:4]]})
    result.sort(key=lambda x:(-x["count"],x["type"],x["label"]))
    return result[:min(limit,100)]
