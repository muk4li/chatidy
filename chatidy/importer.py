"""Import chat exports through explicit per-format adapters into one normalized chat model.

Each adapter recognizes its format by positive structural markers. Exactly one adapter
must match a conversation object; no match or several matches abort the import.
"""
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
# Stored content of messages without readable text (thinking, tool-only turns, other types).
# The raw message stays in metadata; counts and the search index skip this marker.
NON_TEXT = "[Nicht-textueller Inhalt]"

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
                body = NON_TEXT
        if not body.strip():
            continue
        messages.append({"id": str(message.get("id") or f"{raw['id']}:node:{node_id}"),
                         "role": role, "content": body,
                         "timestamp": message.get("create_time"),
                         "metadata": {"source": "chatgpt", "node_id": node_id, **message}})
    return {"id": str(raw["id"]), "provider": "chatgpt", "title": str(raw.get("title") or "Ohne Titel"),
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
    return {"id":cid,"provider":"chatgpt","title":str(raw.get("title") or "Ohne Titel"),
            "created":unix_time(raw.get("created")),
            "updated":unix_time(raw.get("updated")),
            "project":str(raw.get("project_id") or ""),
            "archived":bool(raw.get("archived",False)),
            "metadata":{"source":"extractor", **{k:v for k,v in raw.items() if k != "messages"}},
            "messages":messages}

CLAUDE_ROLES = {"human": "user", "assistant": "assistant"}


def claude_messages_key(raw):
    """Claude exports use `chat_messages`; a `messages` variant is accepted only with `sender`."""
    for key in ("chat_messages", "messages"):
        items = raw.get(key)
        if isinstance(items, list) and all(isinstance(item, dict) and "sender" in item for item in items):
            if key == "chat_messages" or items:
                return key
    return None


def claude_text(message):
    """Reading/search text (E11): text blocks, fallback `text`, plus attachment text."""
    blocks = message.get("content")
    parts = []
    if isinstance(blocks, list):
        parts = [block["text"] for block in blocks
                 if isinstance(block, dict) and block.get("type") == "text"
                 and isinstance(block.get("text"), str) and block["text"].strip()]
    if not parts and isinstance(message.get("text"), str) and message["text"].strip():
        parts = [message["text"]]
    for attachment in message.get("attachments") or []:
        if isinstance(attachment, dict) and isinstance(attachment.get("extracted_content"), str) \
                and attachment["extracted_content"].strip():
            name = attachment.get("file_name") if isinstance(attachment.get("file_name"), str) else ""
            parts.append(f"[Anhang{': ' + name if name else ''}]\n" + attachment["extracted_content"])
    return "\n\n".join(parts)


def claude_branch(cid, items):
    """Select the current branch (E10): parent links form a tree; the latest leaf wins.

    Roots are messages whose parent is not part of the conversation. Messages without
    any parent field keep list order. Cycles or equally recent leaves abort.
    """
    by_id = {}
    for index, item in enumerate(items):
        mid = str(item.get("uuid") or f"{cid}:claude:{index}")
        if mid in by_id:
            raise ValueError("Doppelte Nachrichten-ID innerhalb eines Claude-Gesprächs. Import abgebrochen.")
        by_id[mid] = item
    if not any("parent_message_uuid" in item for item in items):
        return list(by_id.items()), []
    parent = {mid: item.get("parent_message_uuid") for mid, item in by_id.items()}
    parent = {mid: (p if isinstance(p, str) and p in by_id else None) for mid, p in parent.items()}
    for start in by_id:
        seen, cursor = set(), start
        while cursor is not None:
            if cursor in seen:
                raise ValueError("Ungültiger Claude-Gesprächsverlauf: Zyklus erkannt. Import abgebrochen.")
            seen.add(cursor)
            cursor = parent[cursor]
    has_child = {p for p in parent.values() if p is not None}
    leaves = [mid for mid in by_id if mid not in has_child]
    stamp = lambda mid: unix_time(by_id[mid].get("created_at"))
    if len(leaves) > 1:
        if any(stamp(mid) is None for mid in leaves):
            raise ValueError("Mehrdeutiger Claude-Gesprächszweig: Zeitstempel fehlt. Import abgebrochen.")
        latest = max(stamp(mid) for mid in leaves)
        leaves = [mid for mid in leaves if stamp(mid) == latest]
        if len(leaves) > 1:
            raise ValueError("Mehrdeutiger Claude-Gesprächszweig: mehrere gleich neue Enden. Import abgebrochen.")
    chain, cursor = [], leaves[0]
    while cursor is not None:
        chain.append(cursor)
        cursor = parent[cursor]
    chain.reverse()
    selected = set(chain)
    return [(mid, by_id[mid]) for mid in chain], [by_id[mid] for mid in by_id if mid not in selected]


def parse_claude_chat(raw):
    """Adapt one conversation from the official Claude export (conversations.json)."""
    key = claude_messages_key(raw)
    if not raw.get("uuid") or key is None:
        return None
    cid = "claude:" + str(raw["uuid"])
    branch, inactive = claude_branch(cid, raw[key])
    messages = []
    for mid, item in branch:
        sender = str(item.get("sender") or "unknown")
        body = claude_text(item) or NON_TEXT
        messages.append({"id": mid, "role": CLAUDE_ROLES.get(sender, sender), "content": body,
                         "timestamp": unix_time(item.get("created_at")),
                         "metadata": {"source": "claude", **item}})
    metadata = {"source": "claude", "original_id": str(raw["uuid"]),
                **{k: v for k, v in raw.items() if k != key}}
    if inactive:
        metadata["inactive_branch_messages"] = inactive
    return {"id": cid, "provider": "claude", "title": str(raw.get("name") or "Ohne Titel"),
            "created": unix_time(raw.get("created_at")), "updated": unix_time(raw.get("updated_at")),
            "project": "", "archived": False, "metadata": metadata, "messages": messages}


def codex_text(items, kinds):
    parts = []
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict) or item.get("type") not in kinds:
            continue
        if item.get("type") == "pr" and isinstance(item.get("pr_title"), str) and item["pr_title"].strip():
            parts.append("[Pull Request] " + item["pr_title"])
            continue
        for block in item.get("content") if isinstance(item.get("content"), list) else []:
            if isinstance(block, dict) and block.get("content_type") == "text" \
                    and isinstance(block.get("text"), str) and block["text"].strip():
                parts.append(block["text"])
    return "\n\n".join(parts)


def parse_codex_chat(raw):
    """Adapt one ChatGPT Codex task from codex.json (PROV-004). Turns keep list order;
    the export has no timestamps. Repository snapshots and diffs stay in metadata."""
    if not raw.get("id") or not isinstance(raw.get("turns"), list):
        return None
    cid = "codex:" + str(raw["id"])
    messages, seen = [], set()
    for index, turn in enumerate(raw["turns"]):
        mid = str(turn.get("id") or f"{cid}:turn:{index}")
        if mid in seen:
            raise ValueError("Doppelte Turn-ID innerhalb einer Codex-Aufgabe. Import abgebrochen.")
        seen.add(mid)
        role = str(turn.get("role") or "unknown")
        if role == "user":
            body = codex_text(turn.get("input_items"), {"message"})
        else:
            body = codex_text(turn.get("output_items"), {"message", "pr"})
        messages.append({"id": mid, "role": role, "content": body or NON_TEXT, "timestamp": None,
                         "metadata": {"source": "codex", **turn}})
    return {"id": cid, "provider": "chatgpt", "title": str(raw.get("title") or "Ohne Titel"),
            "created": None, "updated": None, "project": "", "archived": bool(raw.get("archived", False)),
            "metadata": {"source": "codex", "original_id": str(raw["id"]),
                         **{k: v for k, v in raw.items() if k != "turns"}},
            "messages": messages}


def is_codex(raw):
    """ChatGPT Codex task (codex.json): `id` plus `turns[]` whose entries carry `role`."""
    turns = raw.get("turns")
    return ("id" in raw and isinstance(turns, list)
            and all(isinstance(turn, dict) and "role" in turn for turn in turns))


def is_claude(raw):
    """Official Claude export: `uuid` plus `chat_messages[]` whose entries carry `sender`."""
    return "uuid" in raw and claude_messages_key(raw) is not None


def is_chatgpt(raw):
    """Official ChatGPT export: conversation graph in `mapping`."""
    return "mapping" in raw


def is_extractor(raw):
    """chatgpt-conversation-extractor: `id` plus a message list whose entries carry `role`."""
    messages = raw.get("messages")
    return ("id" in raw and isinstance(messages, list)
            and all(isinstance(item, dict) and "role" in item for item in messages))


# Fixed adapter list (E1): name, recognizer, parser. New formats are added here.
ADAPTERS = (
    ("chatgpt", is_chatgpt, parse_chat),
    ("extractor", is_extractor, parse_extractor_chat),
    ("claude", is_claude, parse_claude_chat),
    ("codex", is_codex, parse_codex_chat),
)


def detect_format(raw):
    """Return the single matching adapter name, None for no match; several matches abort (E2)."""
    if not isinstance(raw, dict):
        return None
    matches = [name for name, recognize, _ in ADAPTERS if recognize(raw)]
    if len(matches) > 1:
        raise ValueError("Mehrdeutiges Exportformat: Konversation passt zu mehreren Formaten. Import abgebrochen.")
    return matches[0] if matches else None


def parse_root(root):
    if isinstance(root,dict) and "data_files" in root and "total_files" in root:
        raise ValueError("Das ist das Claude-Export-Manifest, es enthält keine Gespräche. "
                         "Bitte die Datei conversations-NNN.zip importieren.")
    if isinstance(root,dict) and isinstance(root.get("conversations"),list):
        root=root["conversations"]
    if isinstance(root,dict):
        root=[root]
    if not isinstance(root,list) or not root:
        raise ValueError("Erwartet conversations.json von ChatGPT oder Claude oder Extractor-JSON.")
    parsed=[]
    for raw in root:
        if not isinstance(raw,dict):
            raise ValueError("Ungültige Konversation im Export.")
        name=detect_format(raw)
        parser=next((parse for adapter, _, parse in ADAPTERS if adapter==name), None)
        chat=parser(raw) if parser else None
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
                        isinstance(raw, dict) and detect_format(raw) is not None for raw in roots)
                finally:
                    values.close()
                if recognized:
                    selected.append(item)
        inventory['counts']['conversation_segment'] = len(selected)
        inventory['counts']['unknown'] -= len(selected)
    if not selected:
        raise ValueError('Keine erkennbaren Konversationsdateien im Archiv.' + claude_category_hint(archive))
    for item in selected:
        check_compression(item)
    inventory.update(segment_count=len(selected),
                     segments=[PurePosixPath(x.filename.replace('\\','/')).name[:160] for x in selected[:20]],
                     codex_conversations=0)
    codex = codex_entry(archive, selected, inventory)
    if codex is not None:
        selected.append(codex)
    inventory['selected_json_bytes'] = sum(x.file_size for x in selected)
    return selected, inventory


def codex_entry(archive, selected, inventory):
    """PROV-004: codex.json next to the conversation files is imported when every entry is a
    recognizable Codex task. Otherwise it stays inventory-only, with a visible warning."""
    root = PurePosixPath(selected[0].filename.replace('\\', '/')).parent
    items = [x for x in archive.infolist() if not x.is_dir()
             and PurePosixPath(x.filename.replace('\\', '/')).name.casefold() == 'codex.json'
             and PurePosixPath(x.filename.replace('\\', '/')).parent == root]
    if len(items) != 1:
        return None
    item = items[0]
    check_compression(item)
    decoder = json.JSONDecoder(object_pairs_hook=unique_object, parse_constant=invalid_constant)
    count, recognized = 0, True
    try:
        with archive.open(item) as source:
            # json_values streams top-level array elements one by one.
            for value in json_values(source, [MAX_UNCOMPRESSED], decoder):
                if not isinstance(value, dict) or detect_format(value) != 'codex':
                    recognized = False
                    break
                count += 1
    except (ValueError, UnicodeError, RecursionError):
        recognized = False
    if recognized:
        inventory['codex_conversations'] = count
        return item if count else None
    inventory['warnings'].append('codex.json nicht als Codex-Aufgaben erkannt; wird nicht importiert.')
    return None


CLAUDE_CATEGORY_FILES = (
    ({'users.json', 'login_history.json'}, 'Konto- und Login-Daten (light_metadata)'),
    ({'routines.json', 'routine_runs.json'}, 'Claude-Code-Routinen (claude_code_cloud)'),
    ({'artifact.json', 'artifact_comments.json'}, 'Artifacts (frames)'),
)


def claude_category_hint(archive):
    """E13: explain which Claude export category was uploaded instead of conversations."""
    names = {PurePosixPath(x.filename.replace('\\', '/')).name.casefold() for x in archive.infolist()}
    for markers, label in CLAUDE_CATEGORY_FILES:
        if names & markers:
            return (f' Erkannt: Claude-Export, Kategorie {label}. Gespräche enthält nur '
                    'die Datei conversations-NNN.zip.')
    return ''


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
        raise ValueError("Keine erkennbaren Konversationen gefunden.")


def parse_export(data, name):
    return list(iter_export(io.BytesIO(data), name))
