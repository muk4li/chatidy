"""Import official ChatGPT conversations.json, preserving the current conversation branch."""
import io
import json
import zipfile
from pathlib import PurePosixPath
from datetime import datetime

MAX_UPLOAD = 200 * 1024 * 1024
MAX_UNCOMPRESSED = 350 * 1024 * 1024

def content_text(message):
    content = message.get("content") or {}
    if isinstance(content, str):
        return content
    if not isinstance(content, dict):
        return ""
    parts = content.get("parts")
    result = []
    if isinstance(parts, list):
        for part in parts:
            if isinstance(part, str):
                result.append(part)
            elif isinstance(part, dict):
                for key in ("text", "content", "transcript"):
                    if isinstance(part.get(key), str):
                        result.append(part[key])
                        break
                else:
                    if part.get("asset_pointer"):
                        result.append("[Anhang]")
    if not result and isinstance(content.get("text"), str):
        result.append(content["text"])
    return "\n".join(result)

def parse_chat(raw):
    if not isinstance(raw, dict) or not raw.get("id"):
        return None
    mapping = raw.get("mapping")
    if not isinstance(mapping, dict):
        return None
    current = raw.get("current_node")
    chain, seen = [], set()
    if current in mapping:
        while current in mapping and current not in seen:
            seen.add(current)
            node = mapping[current]
            if not isinstance(node, dict):
                break
            if isinstance(node.get("message"), dict):
                chain.append(node["message"])
            current = node.get("parent")
        chain.reverse()
    else:
        chain = [v["message"] for v in mapping.values()
                 if isinstance(v, dict) and isinstance(v.get("message"), dict)]
        chain.sort(key=lambda m: m.get("create_time") or 0)
    messages = []
    for i, message in enumerate(chain):
        author = message.get("author") or {}
        role = author.get("role", "unknown") if isinstance(author, dict) else "unknown"
        if role not in ("user", "assistant", "tool"):
            continue
        body = content_text(message)
        if not body.strip():
            continue
        messages.append({"id": str(message.get("id") or f"{raw['id']}:{i}"),
                         "role": role, "content": body,
                         "timestamp": message.get("create_time")})
    return {"id": str(raw["id"]), "title": str(raw.get("title") or "Ohne Titel"),
            "created": raw.get("create_time"), "updated": raw.get("update_time"),
            "project": str(raw.get("conversation_template_id") or ""),
            "archived": bool(raw.get("is_archived", False)),
            "messages": messages}

def unix_time(value):
    if isinstance(value, (int,float)):
        return value
    if isinstance(value,str):
        try:
            return datetime.fromisoformat(value.replace("Z","+00:00")).timestamp()
        except ValueError:
            return None
    return None

def parse_extractor_chat(raw):
    """Adapt structured JSON produced by chatgpt-conversation-extractor."""
    if not isinstance(raw,dict) or not raw.get("id") or not isinstance(raw.get("messages"),list):
        return None
    cid=str(raw["id"])
    messages=[]
    for index,item in enumerate(raw["messages"]):
        if not isinstance(item,dict) or not isinstance(item.get("content"),str):
            continue
        if not item["content"].strip():
            continue
        messages.append({"id":f"{cid}:extractor:{index}",
                         "role":str(item.get("role") or "unknown"),
                         "content":item["content"],
                         "timestamp":unix_time(item.get("timestamp"))})
    return {"id":cid,"title":str(raw.get("title") or "Ohne Titel"),
            "created":unix_time(raw.get("created")),
            "updated":unix_time(raw.get("updated")),
            "project":str(raw.get("project_id") or ""),
            "archived":bool(raw.get("archived",False)),
            "messages":messages}

def parse_root(root):
    if isinstance(root,dict) and isinstance(root.get("conversations"),list):
        root=root["conversations"]
    if isinstance(root,dict):
        root=[root]
    if not isinstance(root,list):
        raise ValueError("Erwartet ChatGPT-conversations.json oder Extractor-JSON.")
    parsed=[]
    for raw in root:
        if not isinstance(raw,dict):
            continue
        chat=parse_chat(raw) if "mapping" in raw else parse_extractor_chat(raw)
        if chat:
            parsed.append(chat)
    return parsed

def parse_export(data, name):
    if len(data)>MAX_UPLOAD:
        raise ValueError("Datei größer als 200 MB.")
    roots=[]
    if name.lower().endswith(".zip"):
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                entries=[x for x in archive.infolist()
                         if not x.is_dir() and PurePosixPath(x.filename).suffix.lower()==".json"]
                if len(entries)>12000 or sum(x.file_size for x in entries)>MAX_UNCOMPRESSED:
                    raise ValueError("ZIP enthält zu viele bzw. zu große JSON-Dateien.")
                named=[x for x in entries if PurePosixPath(x.filename).name=="conversations.json"]
                entries=named[:1] if named else entries
                if not entries:
                    raise ValueError("Keine ChatGPT-JSON-Dateien gefunden.")
                for item in entries:
                    if item.compress_size and item.file_size/item.compress_size>500:
                        raise ValueError("Verdächtige ZIP-Kompressionsrate.")
                    try:
                        roots.append(json.loads(archive.read(item).decode("utf-8-sig")))
                    except (ValueError,UnicodeError) as exc:
                        if len(entries)==1:
                            raise ValueError("JSON im Archiv ungültig.") from exc
        except zipfile.BadZipFile as exc:
            raise ValueError("Ungültiges ZIP-Archiv.") from exc
    elif name.lower().endswith(".json"):
        roots=[json.loads(data.decode("utf-8-sig"))]
    else:
        raise ValueError("Bitte eine .zip- oder .json-Datei wählen.")
    merged={}
    for root in roots:
        for chat in parse_root(root):
            merged[chat["id"]]=chat
    if not merged:
        raise ValueError("Keine erkennbaren ChatGPT-Konversationen gefunden.")
    return list(merged.values())
