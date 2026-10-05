"""Inventory every shipped world cell; collect display candidates without rewriting actors."""
from pathlib import Path
import collections, json, re, struct, sys, zlib
from display_tools import ui, sha

INDEX, SOURCES, OUT = map(Path, sys.argv[1:4])
entries = json.loads(INDEX.read_text())['entries']
targets = [e for e in entries if e['type'] == 'file' and e['relative_path'].endswith('.umap') and '/Maps/Shipping/' in e['relative_path']]
names = collections.defaultdict(list)
texts = []
strings = collections.defaultdict(list)
errors, acquired = [], []


def fstring(data, pos):
    if pos + 4 > len(data):
        raise ValueError('FString header out of bounds')
    size = struct.unpack_from('<i', data, pos)[0]
    pos += 4
    if not size:
        return '', pos
    width = 2 if size < 0 else 1
    length = abs(size) * width
    if not 1 <= abs(size) <= 65536 or pos + length > len(data) or data[pos + length - width:pos + length] != b'\0' * width:
        raise ValueError('invalid FString')
    return data[pos:pos + length - width].decode('utf-16-le' if size < 0 else 'utf-8'), pos + length


for target in targets:
    rel = target['relative_path']
    path = SOURCES / rel
    if not path.exists():
        errors.append({'path': rel, 'error': 'not_acquired'})
        continue
    data = path.read_bytes()
    try:
        p = ui.zen.package(path)
    except Exception as ex:
        errors.append({'path': rel, 'error': str(ex)})
        continue
    acquired.append({'path': rel, 'sha256': sha(data), 'bytes': len(data)})
    body = data[p['header'][1]:]
    for name in p['names']:
        if name.isascii() and any(c.isalpha() for c in name) and len(names[name]) < 3:
            names[name].append(rel)
    for m in re.finditer(rb'\x21\x00\x00\x00([A-F0-9]{32})\x00', body):
        key_pos = m.start()
        namespaces = []
        for pos in range(max(5, key_pos - 260), key_pos - 3):
            if body[pos - 5:pos] != b'\0' * 5:
                continue
            try:
                ns, end = fstring(body, pos)
                if end == key_pos:
                    namespaces.append(ns)
            except (ValueError, UnicodeError, struct.error):
                pass
        if len(namespaces) != 1:
            continue
        try:
            source, end = fstring(body, m.end())
        except (ValueError, UnicodeError, struct.error):
            continue
        if source:
            texts.append({'Namespace': namespaces[0], 'Key': m.group(1).decode(), 'English': source,
                          'SourceStringHash': str(zlib.crc32(source.encode('utf-32-le')) & 0xffffffff),
                          'Assets': rel.removeprefix('Content/'), 'offset': p['header'][1] + m.start()})
    # Conservative ASCII FString candidates. Retain owners/offsets for manual classification.
    for m in re.finditer(rb'[\x20-\x7e]{3,240}\x00', body):
        pos = m.start() - 4
        if pos < 0 or struct.unpack_from('<i', body, pos)[0] != len(m.group()):
            continue
        value = m.group()[:-1].decode('ascii')
        if re.fullmatch(r"[A-Za-z0-9 '’.,:!?()\[\]&/\-]+", value) and any(c.isalpha() for c in value) and len(strings[value]) < 3:
            strings[value].append({'path': rel, 'offset': p['header'][1] + pos})
    # English captions containing typographic apostrophes use UTF-16 FString.
    for m in re.finditer(rb'(?:[\x20-\x7e]\x00|[\x18\x19\x1c\x1d]\x20){3,240}\x00\x00', body):
        pos = m.start() - 4
        if pos < 0 or struct.unpack_from('<i', body, pos)[0] != -len(m.group()) // 2:
            continue
        value = m.group()[:-2].decode('utf-16-le')
        if any(c.isalpha() for c in value) and len(strings[value]) < 3:
            strings[value].append({'path': rel, 'offset': p['header'][1] + pos, 'encoding': 'utf-16-le'})

report = {'target_cells': len(targets), 'acquired_cells': len(acquired), 'errors': errors,
          'all_cells_acquired': len(acquired) == len(targets), 'files': acquired,
          'native_ftext_occurrences': texts, 'raw_fstring_candidates': dict(strings),
          'name_candidates': dict(names), 'actor_overrides_created': 0,
          'classification_required': 'Raw strings/names include technical IDs; do not translate by existence alone.'}
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'target_cells': len(targets), 'acquired': len(acquired), 'missing': len(errors),
                  'ftexts': len(texts), 'strings': len(strings), 'names': len(names)}))
