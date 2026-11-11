"""Import official ChatGPT conversations.json, preserving the current conversation branch."""
import io
import json
import zipfile
from pathlib import PurePosixPath

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

def parse_export(data, name):
    if len(data) > MAX_UPLOAD:
        raise ValueError("Datei größer als 200 MB.")
    if name.lower().endswith(".zip"):
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                matches = [item for item in archive.infolist()
                           if not item.is_dir() and PurePosixPath(item.filename).name == "conversations.json"]
                if not matches:
                    raise ValueError("Keine conversations.json gefunden.")
                item = matches[0]
                if item.file_size > MAX_UNCOMPRESSED:
                    raise ValueError("Entpackte JSON ist zu groß.")
                if item.compress_size and item.file_size / item.compress_size > 500:
                    raise ValueError("Verdächtige ZIP-Kompressionsrate.")
                data = archive.read(item)
        except zipfile.BadZipFile as exc:
            raise ValueError("Ungültiges ZIP-Archiv.") from exc
    elif not name.lower().endswith(".json"):
        raise ValueError("Bitte eine .zip- oder .json-Datei wählen.")
    root = json.loads(data.decode("utf-8-sig"))
    if not isinstance(root, list):
        raise ValueError("conversations.json muss eine Liste enthalten.")
    parsed = []
    for raw in root:
        chat = parse_chat(raw)
        if chat:
            parsed.append(chat)
    return parsed
