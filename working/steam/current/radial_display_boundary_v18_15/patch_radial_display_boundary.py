from pathlib import Path
import copy, hashlib, json, struct, sys, tempfile

ROOT = Path(sys.argv[1]).resolve()
BASE = Path(sys.argv[2]).resolve()

sys.path.insert(0, str(ROOT / 'tools' / 'map_audit_v18_5'))
import display_tools as d
cf = d.cf

TARGET = 'Carnal_Instinct_UE5/Content/BlueprintSystems/DynamicRadialMenu/Widgets/W_MenuItem.uasset'
ALIASES = [
    ('Canopic Capture', '5EC37C4D8083528EEA2DA50B6E342D44', 1009922021, 'Захват канопой'),
    ('Fishing', '79CEA8FF2BA190BBB1BDB045610C272C', 2680376353, 'Рыбалка'),
    ("Korvoth's Sceptre", '252B52243AB3DA58F770F48C2CAD76C9', 406990083, 'Скипетр Корвота'),
    ('Masturbate', '84CA42CB806912F44A5FD87EA66D79E6', 2284028336, 'Мастурбировать'),
    ('Summon Aadi', '8F9100DF142AD9B12A2DD786B3C1521A', 1824976582, 'Призвать Аади'),
    ('Torch', 'DCC578ACD71A7BF2C0E96DE641CC4656', 1261106821, 'Факел'),
    ('Shade Sight', 'D9F46D7344B1F6CCD7C81D89A0B3CCFE', 2468818620, 'Зрение тени'),
]

def sha(b):
    return hashlib.sha256(b).hexdigest()

def callmath_imports(package, function_name):
    e = next(x for x in package['exports'] if x['name'] == function_name)
    _, _, _, nodes, _ = d.find_script(package['bytes'][e['start']:e['end']])
    out = set()
    for node in nodes:
        for x in d.k.walk(node):
            if x.op == 0x68:
                v = struct.unpack('<i', x.parts[0].data)[0]
                out.add(-v - 1)
    return out

def ftext_parts(expr):
    assert expr.op == 0x29 and expr.parts[0].data == b'\x01'
    vals = []
    for x in expr.parts[1:4]:
        assert x.op in (0x1f, 0x34)
        raw = x.parts[0].data
        vals.append(raw[:-1].decode('ascii') if x.op == 0x1f else raw[:-2].decode('utf-16-le'))
    return tuple(vals)

def patch_asset(data, edition, out_path):
    with tempfile.TemporaryDirectory() as td:
        src = Path(td) / 'W_MenuItem.uasset'
        src.write_bytes(data)
        p = d.ui.zen.package(src)
        seen = callmath_imports(p, 'CheckForSubitems') | callmath_imports(p, 'SetSubmenuIndicator')
        assert 147 in seen and 63 in seen, (edition, seen)

        e = next(x for x in p['exports'] if x['name'] == 'SetItemText')
        old_export = p['bytes'][e['start']:e['end']]
        _, old_mem, old_disk, nodes, _ = d.find_script(old_export)
        nodes = copy.deepcopy(nodes)

        set_calls = [x for n in nodes for x in d.k.walk(n) if x.op == 0x1b and d.expr_name(x, p['names']) == 'SetText']
        assert len(set_calls) == 1, (edition, len(set_calls))
        set_call = set_calls[0]
        assert len(set_call.parts) == 3
        display = set_call.parts[1]
        assert display.op == 0x42
        assert d.pointer_name(display.parts[0], p['names']).startswith('DisplayName_')
        original_display = copy.deepcopy(display)

        appended = []
        name_index = {}
        for name, _, _, _ in ALIASES:
            if name in p['names']:
                name_index[name] = p['names'].index(name)
            else:
                name_index[name] = len(p['names']) + len(appended)
                appended.append(name)

        to_string = d.k.callmath(147, [copy.deepcopy(original_display)])
        to_name = d.k.callmath(63, [to_string])
        cases = []
        for name, key, _, _ in ALIASES:
            cases.append((d.k.name(name_index[name]), d.k.text(name, key, 'CI_RU_Display_RadialAudit')))
        set_call.parts[1] = d.k.Expr(0x69, index=to_name, cases=cases, default=copy.deepcopy(original_display))

        replacements, rebase = d.replace_function(p, e, nodes)
        result = d.ui.zen.rebuild(p, replacements, appended)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(result)

        q = d.ui.zen.package(out_path)
        assert q['names'][:len(p['names'])] == p['names']
        assert q['names'][len(p['names']):] == appended
        qe = next(x for x in q['exports'] if x['name'] == 'SetItemText')
        _, new_mem, new_disk, qnodes, _ = d.find_script(q['bytes'][qe['start']:qe['end']])
        switches = [x for n in qnodes for x in d.k.walk(n) if x.op == 0x69]
        assert len(switches) == 1 and len(switches[0].cases) == 7
        sw = switches[0]
        assert sw.index.op == 0x68
        cases_readback = []
        for ck, cv in sw.cases:
            assert ck.op == 0x21 and cv.op == 0x29
            ni = struct.unpack_from('<I', ck.parts[0].data)[0] & 0x3fffffff
            cases_readback.append((q['names'][ni],) + ftext_parts(cv))
        expected = [(n, n, k, 'CI_RU_Display_RadialAudit') for n, k, _, _ in ALIASES]
        assert cases_readback == expected, (edition, cases_readback)
        assert sw.default.op == 0x42 and d.pointer_name(sw.default.parts[0], q['names']).startswith('DisplayName_')

        for a, b in zip(p['exports'], q['exports']):
            if a['index'] not in replacements:
                assert p['bytes'][a['start']:a['end']] == result[b['start']:b['end']], (edition, a['name'])

        return {
            'source_sha256': sha(data),
            'patched_sha256': sha(result),
            'source_bytes': len(data),
            'patched_bytes': len(result),
            'old_name_count': len(p['names']),
            'new_name_count': len(q['names']),
            'appended_names': appended,
            'set_item_text_old_memory': old_mem,
            'set_item_text_new_memory': new_mem,
            'set_item_text_old_disk': old_disk,
            'set_item_text_new_disk': new_disk,
            'rebase': rebase,
            'cases': [n for n, _, _, _ in ALIASES],
            'other_exports_byte_identical': True,
        }

def build_container(files, out_utoc):
    original = cf.build_directory
    cf.build_directory = lambda pairs, mount='../../../': original([(i, p) for p, i in pairs], mount)
    try:
        return cf.build_container(list(files.items()), out_utoc)
    finally:
        cf.build_directory = original

report = {
    'release': '18.15',
    'task': 'radial_display_boundary',
    'runtime_tested': False,
    'design': 'English runtime DisplayName retained; Russian FText injected only at W_MenuItem.SetItemText display boundary.',
    'editions': {},
}

for edition in ('Steam_current', 'NoSteam_0.7.9.16232'):
    old = cf.Toc(BASE / 'Files' / edition / 'pakchunk1015-Windows_P.utoc')
    assert not old.verify_meta()
    previous = {p: old.read_chunk(i) for p, i in old.files}
    assert TARGET in previous, (edition, TARGET)

    patched_path = ROOT / 'Developer' / 'V18_15_RadialDisplay' / 'patched' / edition / TARGET
    evidence = patch_asset(previous[TARGET], edition, patched_path)
    files = dict(previous)
    files[TARGET] = patched_path.read_bytes()

    out_utoc = ROOT / 'Files' / edition / 'pakchunk1015-Windows_P.utoc'
    build = build_container(files, out_utoc)
    toc = cf.Toc(out_utoc)
    assert not toc.verify_meta(), (edition, toc.verify_meta())
    assert len(toc.files) == len(files)
    readback = {p: toc.read_chunk(i) for p, i in toc.files}
    assert readback == files
    changed = [p for p in files if files[p] != previous[p]]
    assert changed == [TARGET], (edition, changed)

    loc = cf.Locres(ROOT / 'Data' / edition / 'Game.locres')
    indexed = {(e['namespace'], e['key'], e['source_hash']): e for e in loc.entries}
    alias_values = {}
    for source, key, source_hash, russian in ALIASES:
        a = indexed[('CI_RU_Display_RadialAudit', key, source_hash)]
        assert a['value'] == russian
        alias_values[source] = a['value']
    technical = {}
    for source, _, source_hash, _ in ALIASES:
        matches = [e for e in loc.entries if e['source_hash'] == source_hash and e['value'] == source]
        assert matches, (edition, source, source_hash)
        technical[source] = source

    report['editions'][edition] = {
        'target': TARGET,
        'patch': evidence,
        'container': build,
        'package_count': len(files),
        'utoc_sha256': sha(out_utoc.read_bytes()),
        'ucas_sha256': sha(out_utoc.with_suffix('.ucas').read_bytes()),
        'pak_sha256': sha((ROOT / 'Files' / edition / 'pakchunk1015-Windows_P.pak').read_bytes()),
        'container_meta_hashes': 'PASS',
        'container_exact_chunk_readback': 'PASS',
        'only_changed_package': TARGET,
        'technical_runtime_ids': technical,
        'display_aliases': alias_values,
    }

out = ROOT / 'Reports' / 'V18_15_RADIAL_DISPLAY_BOUNDARY.json'
out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps(report, ensure_ascii=False, indent=2))
