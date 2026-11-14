"""Classify archive names without trusting metadata or manifest schemas."""
import re
from pathlib import PurePosixPath

SEGMENT = re.compile(r'^conversations-(\d{1,8})\.json$', re.I)
METADATA = frozenset(('ads.json', 'codex.json', 'conversation_asset_file_names.json',
    'library_files.json', 'sectioned_conversations.json', 'shared_conversations.json',
    'user.json', 'user_settings.json'))


def classify(archive, max_entries, max_json_bytes):
    entries = archive.infolist()
    if len(entries) > max_entries:
        raise ValueError('ZIP enthält zu viele Dateien.')
    json_entries = [x for x in entries if not x.is_dir() and x.filename.lower().endswith('.json')]
    json_bytes = sum(x.file_size for x in json_entries)
    if json_bytes > max_json_bytes:
        raise ValueError(f'ZIP-JSONs umfassen entpackt {json_bytes / 1048576:.1f} MB; Limit {max_json_bytes / 1048576:.1f} MB. Keine Gespräche übernommen.')
    if any(x.flag_bits & 1 for x in entries):
        raise ValueError('Verschlüsselte ZIP-Archive werden nicht unterstützt.')
    if len({x.filename.casefold() for x in entries}) != len(entries):
        raise ValueError('Doppelte oder mehrdeutige Dateinamen im ZIP.')
    counts = dict.fromkeys(('conversation_segment', 'metadata', 'attachment', 'html_viewer',
                           'supported_resource', 'unknown'), 0)
    classic, numbered, candidates = [], [], []
    manifests, sensitive = 0, 0
    manifest_paths = []
    roles = dict.fromkeys(('codex','advertising','account','settings','library','asset_names','shared','sectioned','root_manifest','site_manifest','other_manifest'), 0)
    role_names = {'codex.json':'codex','ads.json':'advertising','user.json':'account','user_settings.json':'settings','library_files.json':'library','conversation_asset_file_names.json':'asset_names','shared_conversations.json':'shared','sectioned_conversations.json':'sectioned'}
    for item in entries:
        if item.is_dir():
            continue
        path = PurePosixPath(item.filename.replace('\\', '/'))
        name = path.name.casefold()
        match = SEGMENT.fullmatch(name)
        if name == 'conversations.json' or match:
            counts['conversation_segment'] += 1
            (numbered if match else classic).append((path, item))
        elif name == 'export_manifest.json':
            counts['metadata'] += 1
            manifests += 1
            manifest_paths.append(path)
        elif name in METADATA:
            counts['metadata'] += 1
            roles[role_names[name]] += 1
            sensitive += name in ('user.json', 'user_settings.json', 'ads.json')
        elif path.suffix.lower() in ('.dat', '.png', '.jpg', '.jpeg', '.webp', '.mp3', '.mp4', '.pdf'):
            counts['attachment'] += 1
        elif path.suffix.lower() in ('.html', '.htm'):
            counts['html_viewer'] += 1
        elif name == 'third_party_notices.txt':
            counts['supported_resource'] += 1
        else:
            counts['unknown'] += 1
            if path.suffix.lower() == '.json':
                candidates.append(item)
    warnings = []
    if classic and numbered:
        raise ValueError('Klassische und nummerierte Konversationsdateien gleichzeitig: Auswahl mehrdeutig.')
    if len(classic) > 1:
        raise ValueError('Mehrere conversations.json im ZIP-Archiv: Auswahl mehrdeutig.')
    if numbered:
        if len({str(path.parent).casefold() for path, _ in numbered}) != 1:
            raise ValueError('Konversationssegmente aus mehreren Verzeichnissen: Auswahl mehrdeutig.')
        selected = sorted(numbered, key=lambda pair: int(SEGMENT.fullmatch(pair[0].name).group(1)))
        numbers = [int(SEGMENT.fullmatch(path.name).group(1)) for path, _ in selected]
        if numbers != list(range(len(numbers))):
            raise ValueError('Konversationssegment fehlt oder Segmentnummer ist doppelt; erwartet 0 bis N ohne Lücken.')
        selected = [item for _, item in selected]
        format_name = 'official_segments'
        warnings.append('Ohne validiertes Manifest ist ein fehlendes letztes Segment nicht nachweisbar.')
    elif classic:
        selected = [classic[0][1]]
        format_name = 'official_classic'
    else:
        selected = []
        format_name = 'structured_json_archive'
    root_folder = PurePosixPath(selected[0].filename.replace('\\','/')).parent if selected else None
    for manifest in manifest_paths:
        role = 'root_manifest' if manifest.parent == root_folder else 'site_manifest' if manifest.parent.name.casefold() == 'sites' else 'other_manifest'
        roles[role] += 1
    if manifests:
        warnings.append('Manifeste nur inventarisiert; keine Felder ungeprüft als Spezifikation verwendet.')
    if counts['metadata']:
        warnings.append('Zusätzliche JSON-Metadaten werden nicht als Gespräche importiert.')
    if counts['unknown']:
        warnings.append('Unbekannte Zusatzressourcen werden nicht ausgeführt oder extrahiert.')
    return selected, candidates, {'format': format_name, 'counts': counts, 'manifests': manifests,
        'manifests_validated': False, 'metadata_roles': roles, 'sensitive_metadata_files': sensitive, 'warnings': warnings}
