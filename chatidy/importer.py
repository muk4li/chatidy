"""Import official ChatGPT conversations.json, preserving the current conversation branch."""
import io
import json
import zipfile
import zlib
from pathlib import PurePosixPath
from datetime import datetime
from .graph import selected_branch
from .export_layout import classify
from .streaming import json_values

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
        if role not in ("user", "assistant", "tool", "system", "developer"):
            continue
        body = content_text(message)
        if not body.strip() and isinstance(message.get("metadata"), dict) and message["metadata"].get("attachments"):
            body = "[Anhang ohne Text]"
        if not body.strip() and isinstance(message.get("content"), dict):
            content = message["content"]
            if content.get("content_type") not in (None, "text"):
                body = "[Nicht-textueller Inhalt]"
        if not body.strip():
            continue
        messages.append({"id": str(message.get("id") or f"{raw['id']}:node:{node_id}"),
                         "role": role, "content": body,
                         "timestamp": message.get("create_time"),
                         "metadata": {"source": "chatgpt", "node_id": node_id, **message}})
    return {"id": str(raw["id"]), "title": str(raw.get("title") or "Ohne Titel"),
            "created": raw.get("create_time"), "updated": raw.get("update_time"),
            "project": str(raw.get("conversation_template_id") or ""),
            "archived": bool(raw.get("is_archived", False)),
            "metadata": {"source": "chatgpt", **{k:v for k,v in raw.items() if k != "mapping"}},
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
        if not isinstance(item,dict):
            raise ValueError("Ungültige Extractor-Nachricht.")
        body = item.get("content", "")
        if not isinstance(body, str):
            body = content_text(item)
        if not body.strip() and any(item.get(k) for k in ("files", "images", "attachments", "citations")):
            body = "[Anhang oder Quelle ohne Text]"
        if not body.strip():
            continue
        messages.append({"id":str(item.get("id") or f"{cid}:extractor:{index}"),
                         "role":str(item.get("role") or "unknown"),
                         "content":body,
                         "timestamp":unix_time(item.get("timestamp")),
                         "metadata":{"source":"extractor", **item}})
    return {"id":cid,"title":str(raw.get("title") or "Ohne Titel"),
            "created":unix_time(raw.get("created")),
            "updated":unix_time(raw.get("updated")),
            "project":str(raw.get("project_id") or ""),
            "archived":bool(raw.get("archived",False)),
            "metadata":{"source":"extractor", **{k:v for k,v in raw.items() if k != "messages"}},
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


def archive_layout(archive):
    selected, candidates, inventory = classify(archive, MAX_ENTRIES, MAX_UNCOMPRESSED)
    if not selected:
        # No official filenames: recognize structured conversation JSON by
        # shape, not by assuming every JSON resource is a conversation. Invalid
        # JSON in this ambiguous fallback remains an error, never a silent skip.
        decoder = json.JSONDecoder(object_pairs_hook=unique_object, parse_constant=invalid_constant)
        for item in candidates:
            check_compression(item)
            with archive.open(item) as source:
                values = json_values(source, [MAX_UNCOMPRESSED], decoder)
                try:
                    root = next(values)
                    roots = root.get('conversations') if isinstance(root, dict) and 'conversations' in root else [root]
                    recognized = isinstance(roots, list) and bool(roots) and all(
                        isinstance(raw, dict) and raw.get('id') and
                        (isinstance(raw.get('mapping'), dict) or isinstance(raw.get('messages'), list))
                        for raw in roots)
                finally:
                    values.close()
                if recognized:
                    selected.append(item)
        inventory['counts']['conversation_segment'] = len(selected)
        inventory['counts']['unknown'] -= len(selected)
    if not selected:
        raise ValueError('Keine erkennbaren Konversationsdateien im Archiv.')
    for item in selected:
        check_compression(item)
    inventory.update(segment_count=len(selected),
                     segments=[PurePosixPath(x.filename.replace('\\','/')).name[:160] for x in selected[:20]],
                     selected_json_bytes=sum(x.file_size for x in selected))
    return selected, inventory


def check_compression(item):
    if (item.file_size and not item.compress_size) or (item.compress_size and item.file_size/item.compress_size > 500):
        raise ValueError('Verdächtige ZIP-Kompressionsrate.')


def archive_entries(archive):
    return archive_layout(archive)[0]


def inspect_export(source, name):
    source.seek(0, 2)
    size = source.tell()
    if size > MAX_UPLOAD:
        raise ValueError('Datei größer als 200 MB.')
    source.seek(0)
    if name.lower().endswith('.zip'):
        try:
            with zipfile.ZipFile(source) as archive:
                _, inventory = archive_layout(archive)
        except (zipfile.BadZipFile, zlib.error, RuntimeError, NotImplementedError, EOFError) as exc:
            raise ValueError('Ungültiges ZIP-Archiv.') from exc
    elif name.lower().endswith('.json'):
        inventory = {'format':'single_json', 'segment_count':1, 'selected_json_bytes':size,
                     'counts':{'conversation_segment':1}, 'warnings':[], 'manifests_validated':False}
    else:
        raise ValueError('Bitte eine .zip- oder .json-Datei wählen.')
    inventory['archive_bytes'] = size
    return inventory


def iter_export(source, name):
    """Yield normalized chats from a seekable binary stream without array buffering.

    Consumers must stage or transact the entire iterator: a late error invalidates
    the whole export. JSON metadata envelopes still require one object in memory.
    """
    source.seek(0, 2)
    if source.tell() > MAX_UPLOAD:
        raise ValueError("Datei größer als 200 MB.")
    source.seek(0)
    budget = [MAX_UNCOMPRESSED]
    decoder = json.JSONDecoder(object_pairs_hook=unique_object, parse_constant=invalid_constant)
    seen = set()

    def chats(member):
        for root in json_values(member, budget, decoder):
            for chat in parse_root(root):
                if chat["id"] in seen:
                    raise ValueError("Doppelte Konversations-ID im Export. Import abgebrochen.")
                seen.add(chat["id"])
                yield chat

    if name.lower().endswith(".zip"):
        try:
            with zipfile.ZipFile(source) as archive:
                for item in archive_entries(archive):
                    with archive.open(item) as member:
                        yield from chats(member)
        except (zipfile.BadZipFile, zlib.error, RuntimeError, NotImplementedError, EOFError) as exc:
            raise ValueError("Ungültiges ZIP-Archiv.") from exc
    elif name.lower().endswith(".json"):
        yield from chats(source)
    else:
        raise ValueError("Bitte eine .zip- oder .json-Datei wählen.")
    if not seen:
        raise ValueError("Keine erkennbaren ChatGPT-Konversationen gefunden.")


def parse_export(data, name):
    return list(iter_export(io.BytesIO(data), name))
