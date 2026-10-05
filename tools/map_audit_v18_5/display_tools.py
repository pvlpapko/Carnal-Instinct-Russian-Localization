"""Strict display-only native edits and validated Kismet readback."""
from pathlib import Path
import hashlib, importlib.util, json, os, struct, sys

_spec = importlib.util.spec_from_file_location('ci_kismet_v18_5', Path(__file__).with_name('kismet.py'))
k = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = k
_spec.loader.exec_module(k)

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'ui_translation_v18_4'))
import ui_properties as ui
import ci_formats as cf

ui.SCHEMA.update(json.loads(Path(__file__).with_name('native_schema.json').read_text()))
ui.CLASS[0x715ce0fd72983d24] = 'OverlaySlot'
FUNCTION = 0x574f27aec05072d0


def sha(data):
    return hashlib.sha256(data).hexdigest()


def header(items):
    out = bytearray()
    cursor = count = 0
    for position, (index, zero) in enumerate(items):
        skip = index - cursor
        assert skip >= 0
        while skip > 127:
            out += struct.pack('<H', 127)
            cursor += 127
            skip -= 127
        out += struct.pack('<H', skip | (128 if zero else 0) | 512 |
                           (256 if position == len(items) - 1 else 0))
        cursor = index + 1
        count += zero
    if count:
        size = 1 if count <= 8 else 2 if count <= 16 else ((count + 31) // 32) * 4
        out += ((1 << count) - 1).to_bytes(size, 'little')
    return bytes(out) if items else b'\x00\x01'


def encode(value, field):
    typ = field['type']
    formats = {'BoolProperty': 'B', 'ByteProperty': 'B', 'EnumProperty': 'B', 'FloatProperty': 'f', 'IntProperty': 'i'}
    if typ in formats:
        return struct.pack('<' + formats[typ], value)
    assert typ == 'StructProperty', field
    cls = field['struct']
    if cls in ui.NATIVE:
        return struct.pack('<' + ui.NATIVE[cls], *value)
    fields = ui.fields(cls)
    items = [(i, False, encode(value[f['name']], f)) for i, f in enumerate(fields) if f['name'] in value]
    assert len(items) == len(value), (cls, value)
    return header([(i, z) for i, z, _ in items]) + b''.join(v for _, _, v in items)


class NativePatch:
    def __init__(self, path):
        self.path = Path(path)
        self.package = ui.zen.package(path)
        self.changed = {}
        self.evidence = []

    def export(self, name):
        matches = [e for e in self.package['exports'] if e['name'] == name]
        assert len(matches) == 1, (self.path, name)
        return matches[0]

    def properties(self, export):
        e = self.export(export) if isinstance(export, str) else export
        raw = self.changed.get(e['index'], self.package['bytes'][e['start']:e['end']])
        cls = '/Script/UMG.' + ui.CLASS[e['cls']]
        props, end = ui.obj(raw, 0, cls, self.package['names'])
        assert raw[end:] == b'\0' * 4, (e['name'], raw[end:].hex())
        return raw, props, cls

    def set(self, export, field, value):
        e = self.export(export)
        raw, props, cls = self.properties(e)
        fs = ui.fields(cls)
        index = next(i for i, f in enumerate(fs) if f['name'] == field)
        old = props.get(field, {}).get('value', 'native default')
        if old == value:
            return
        items = [(v['index'], v['zero'], raw[v['start']:v['end']]) for name, v in props.items() if name != field]
        items.append((index, False, encode(value, fs[index])))
        items.sort()
        self.changed[e['index']] = header([(i, z) for i, z, _ in items]) + b''.join(v for _, _, v in items) + b'\0' * 4
        self.properties(e)
        self.evidence.append({'export': export, 'property': field, 'old': old, 'new': value})

    def finish(self, path):
        p = self.package
        result = ui.zen.rebuild(p, self.changed)
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(result)
        q = ui.zen.package(path)
        assert p['names'] == q['names']
        assert cf.zen_info(p['bytes'])['imports'] == cf.zen_info(result)['imports']
        for old, new in zip(p['exports'], q['exports']):
            assert all(old[key] == new[key] for key in ('name', 'cls', 'outer', 'super', 'template', 'flags'))
            if old['index'] not in self.changed:
                assert p['bytes'][old['start']:old['end']] == result[new['start']:new['end']]
        return result


def find_script(raw):
    matches = []
    for pos in range(len(raw) - 20):
        memory, disk = struct.unpack_from('<II', raw, pos)
        if not disk or pos + 8 + disk + 12 != len(raw):
            continue
        try:
            reader = k.Reader(raw[pos + 8:pos + 8 + disk])
            nodes = reader.all()
            code, actual_memory, _ = k.serialize(nodes)
            assert reader.m == memory == actual_memory
            assert code == raw[pos + 8:pos + 8 + disk]
            matches.append((pos, memory, disk, nodes, reader))
        except (ValueError, AssertionError, EOFError, IndexError, struct.error, UnicodeError):
            pass
    assert len(matches) == 1, ('strict script match', len(matches), len(raw))
    return matches[0]


def pointer_name(raw, names):
    count = struct.unpack_from('<I', raw.data)[0]
    return names[struct.unpack_from('<I', raw.data, 4)[0] & 0x3fffffff] if count else None


def expr_name(expr, names):
    if expr.op in (0x00, 0x01, 0x02, 0x48):
        return pointer_name(expr.parts[0], names)
    if expr.op in (0x21, 0x1b, 0x45):
        return names[struct.unpack_from('<I', expr.parts[0].data)[0] & 0x3fffffff]


def verify_script(raw):
    pos, memory, disk, nodes, reader = find_script(raw)
    expressions = [x for node in nodes for x in k.walk(node)]
    boundaries = {x.old for x in expressions} | {x.old_end for x in expressions} | {memory}
    assert all(t.old in boundaries for t in reader.targets)
    return pos, memory, disk, nodes, reader


def rebase_latent(nodes, function_name, mapping, names):
    """Latent Linkage is a VM address stored as an int, not a jump opcode."""
    count = 0
    for node in nodes:
        for expr in k.walk(node):
            if expr.op != 0x2f or len(expr.parts) < 6:
                continue
            values = expr.parts[2:]
            if not any(isinstance(x, k.Expr) and expr_name(x, names) == function_name for x in values):
                continue
            linkage = values[0]
            if isinstance(linkage, k.Expr) and linkage.op == 0x5b:
                assert linkage.parts[0].old in mapping, ('latent offset missing', function_name)
                # EX_SkipOffsetConst is already handled by the serializer.
                continue
            assert isinstance(linkage, k.Expr) and linkage.op in (0x1d, 0x25, 0x26), ('latent linkage', function_name)
            old = struct.unpack('<i', linkage.parts[0].data)[0] if linkage.op == 0x1d else (0 if linkage.op == 0x25 else 1)
            if old < 0:
                continue
            assert old in mapping, ('latent address missing', function_name, old)
            new = mapping[old]
            if new != old:
                assert linkage.op == 0x1d, 'cannot resize compact Linkage after computing map'
                linkage.parts[0].data = struct.pack('<i', new)
                count += 1
    return count


def replace_function(package, export, nodes):
    raw = package['bytes'][export['start']:export['end']]
    pos, old_memory, old_disk, old_nodes, _ = find_script(raw)
    code, memory, mapping = k.serialize(nodes)
    latent_count = rebase_latent(nodes, export['name'], mapping, package['names'])
    code, memory, second_mapping = k.serialize(nodes)
    assert mapping == second_mapping
    result = raw[:pos] + struct.pack('<II', memory, len(code)) + code + raw[-12:]
    verify_script(result)
    replacements = {export['index']: result}
    wrapper_count = 0
    entry_targets = []
    for wrapper in package['exports']:
        if wrapper['cls'] != FUNCTION or wrapper['index'] == export['index']:
            continue
        wr = package['bytes'][wrapper['start']:wrapper['end']]
        wpos, wmemory, wdisk, wn, _ = find_script(wr)
        changed = False
        for node in wn:
            for expr in k.walk(node):
                if expr.op not in (0x1c, 0x46) or struct.unpack('<i', expr.parts[0].data)[0] != export['index'] + 1:
                    continue
                arg = expr.parts[1]
                assert arg.op in (0x1d, 0x25, 0x26), (wrapper['name'], arg.op)
                old = struct.unpack('<i', arg.parts[0].data)[0] if arg.op == 0x1d else (0 if arg.op == 0x25 else 1)
                assert old in mapping, ('wrapper entry missing', wrapper['name'], old)
                entry_targets.append({'wrapper': wrapper['name'], 'old': old, 'new': mapping[old]})
                if old != mapping[old]:
                    assert arg.op == 0x1d
                    arg.parts[0].data = struct.pack('<i', mapping[old])
                    changed = True
        if changed:
            wc, wm, _ = k.serialize(wn)
            assert wm == wmemory and len(wc) == wdisk
            assert wr[-8:] == b'\0' * 8, 'unsupported fast-call trailer needs explicit rebase'
            patched = wr[:wpos + 8] + wc + wr[-12:]
            verify_script(patched)
            replacements[wrapper['index']] = patched
            wrapper_count += 1
    return replacements, {'old_memory': old_memory, 'new_memory': memory, 'old_disk': old_disk,
                          'new_disk': len(code), 'latent_linkages_rebased': latent_count,
                          'wrappers_rebased': wrapper_count, 'wrapper_entries': entry_targets}
