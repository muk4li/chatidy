"""Strict branch selection independent of text rendering and storage."""


def selected_branch(mapping, current=None):
    """Return (node ID, message) pairs in parent order, never merge branches.

    Parent links are authoritative. Optional children lists must agree with them.
    All nodes are validated, including inactive branches; corrupted exports must
    not be accepted as apparently complete conversation snapshots.
    """
    if not isinstance(mapping, dict) or not mapping:
        raise ValueError('Ungültiger Gesprächsgraph: mapping fehlt oder ist leer.')
    children = {key: set() for key in mapping}
    for key, node in mapping.items():
        if not isinstance(key, str) or not isinstance(node, dict):
            raise ValueError('Ungültiger Gesprächsgraph: Knotenstruktur.')
        if node.get('message') is not None and not isinstance(node['message'], dict):
            raise ValueError('Ungültiger Gesprächsgraph: Nachrichtenstruktur.')
        parent = node.get('parent')
        if parent is not None:
            if not isinstance(parent, str) or parent not in mapping:
                raise ValueError('Ungültiger Gesprächsgraph: Elternknoten fehlt.')
            children[parent].add(key)
    for key, node in mapping.items():
        if 'children' in node:
            refs = node['children']
            if (not isinstance(refs, list) or any(not isinstance(x, str) for x in refs)
                    or len(set(refs)) != len(refs) or set(refs) != children[key]):
                raise ValueError('Ungültiger Gesprächsgraph: children-Referenzen widersprechen parent.')
    done = set()
    for key in mapping:
        trail = set()
        cursor = key
        while cursor is not None and cursor not in done:
            if cursor in trail:
                raise ValueError('Ungültiger Gesprächsgraph: Zyklus erkannt.')
            trail.add(cursor)
            cursor = mapping[cursor].get('parent')
        done.update(trail)
    if sum(node.get('parent') is None for node in mapping.values()) != 1:
        raise ValueError('Mehrdeutiger Gesprächsgraph: keine eindeutige Wurzel.')
    if not isinstance(current, str) or current not in mapping:
        leaves = [key for key in mapping if not children[key]]
        if len(leaves) != 1:
            raise ValueError('Mehrdeutiger Gesprächsgraph: current_node fehlt oder ist ungültig; '
                             'mehrere Gesprächszweige vorhanden.')
        current = leaves[0]
    branch = []
    while current is not None:
        node = mapping[current]
        if node.get('message') is not None:
            branch.append((current, node['message']))
        current = node.get('parent')
    branch.reverse()
    return branch
