"""Import official ChatGPT conversations.json, preserving the current conversation branch."""
import io
import json
import zipfile
import zlib
from pathlib import PurePosixPath
from datetime import datetime
from .graph import selected_branch

MAX_UPLOAD = 200 * 1024 * 1024
MAX_UNCOMPRESSED = 350 * 1024 * 1024
MAX_ENTRIES = 12000

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
    chain = selected_branch(raw.get("mapping"), raw.get("current_node"))
    messages = []
    for node_id, message in chain:
        author = message.get("author") or {}
        role = author.get("role", "unknown") if isinstance(author, dict) else "unknown"
        if role not in ("user", "assistant", "tool"):
            continue
        body = content_text(message)
        if not body.strip():
            continue
        messages.append({"id": str(message.get("id") or f"{raw['id']}:node:{node_id}"),
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
    if not isinstance(root,list) or not root:
        raise ValueError("Erwartet ChatGPT-conversations.json oder Extractor-JSON.")
    parsed=[]
    for raw in root:
        if not isinstance(raw,dict):
            raise ValueError("Ungültige Konversation im Export.")
        chat=parse_chat(raw) if "mapping" in raw else parse_extractor_chat(raw)
        if not chat:
            raise ValueError("Unvollständige oder unbekannte Konversation im Export.")
        parsed.append(chat)
    return parsed

def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Doppelte JSON-Schlüssel im Export.")
        result[key] = value
    return result


def invalid_constant(value):
    raise ValueError("Ungültige JSON-Zahl im Export.")


def decode_json(data):
    try:
        return json.loads(data.decode("utf-8-sig"), object_pairs_hook=unique_object,
                          parse_constant=invalid_constant)
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise ValueError("Ungültiges oder unvollständiges JSON im Export.") from exc


def parse_export(data, name):
    if len(data)>MAX_UPLOAD:
        raise ValueError("Datei größer als 200 MB.")
    roots=[]
    if name.lower().endswith(".zip"):
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                entries=[x for x in archive.infolist()
                         if not x.is_dir() and PurePosixPath(x.filename).suffix.lower()==".json"]
                if len(archive.infolist())>MAX_ENTRIES or sum(x.file_size for x in entries)>MAX_UNCOMPRESSED:
                    raise ValueError("ZIP enthält zu viele bzw. zu große JSON-Dateien.")
                if any(x.flag_bits & 1 for x in archive.infolist()):
                    raise ValueError("Verschlüsselte ZIP-Archive werden nicht unterstützt.")
                if len({x.filename for x in entries}) != len(entries):
                    raise ValueError("Doppelte JSON-Dateinamen im ZIP-Archiv.")
                named=[x for x in entries if PurePosixPath(x.filename).name=="conversations.json"]
                if len(named)>1:
                    raise ValueError("Mehrere conversations.json im ZIP-Archiv: Auswahl mehrdeutig.")
                entries=named if named else entries
                if not entries:
                    raise ValueError("Keine ChatGPT-JSON-Dateien gefunden.")
                for item in entries:
                    if (item.file_size and not item.compress_size) or (item.compress_size and item.file_size/item.compress_size>500):
                        raise ValueError("Verdächtige ZIP-Kompressionsrate.")
                    try:
                        with archive.open(item) as member:
                            payload = member.read(MAX_UNCOMPRESSED + 1)
                        if len(payload) > MAX_UNCOMPRESSED:
                            raise ValueError("Entpacktes JSON überschreitet das Größenlimit.")
                        roots.append(decode_json(payload))
                    except (ValueError,UnicodeError) as exc:
                        raise ValueError("JSON im Archiv ungültig oder unvollständig.") from exc
        except (zipfile.BadZipFile, zlib.error, RuntimeError, NotImplementedError, EOFError) as exc:
            raise ValueError("Ungültiges ZIP-Archiv.") from exc
    elif name.lower().endswith(".json"):
        roots=[decode_json(data)]
    else:
        raise ValueError("Bitte eine .zip- oder .json-Datei wählen.")
    merged={}
    for root in roots:
        for chat in parse_root(root):
            if chat["id"] in merged:
                raise ValueError("Doppelte Konversations-ID im Export. Import abgebrochen.")
            merged[chat["id"]]=chat
    if not merged:
        raise ValueError("Keine erkennbaren ChatGPT-Konversationen gefunden.")
    return list(merged.values())
