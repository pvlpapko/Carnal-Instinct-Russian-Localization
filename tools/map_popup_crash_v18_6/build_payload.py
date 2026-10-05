"""Overlay reviewed changes into the exact failed v18.5 payload; read back all files."""
from pathlib import Path
import collections, csv, json, re, struct, sys, zlib
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'map_audit_v18_5'))
from display_tools import cf, ui, k, verify_script, FUNCTION, sha
from native_ftext import guid_base_texts

ROOT, BASE = map(Path, sys.argv[1:3])
evidence = json.loads((ROOT / 'Reports/V18_6_MAP_CAPTIONS.json').read_text())['assets']
item_report = json.loads((ROOT / 'Reports/V18_6_NATIVE_ITEM_FIX.json').read_text())
report = {'release': '18.6', 'runtime_tested': False, 'editions': {}}

def container(files, out):
    original = cf.build_directory
    cf.build_directory = lambda pairs, mount='../../../': original([(i, p) for p, i in pairs], mount)
    try:
        return cf.build_container(list(files.items()), out)
    finally:
        cf.build_directory = original

def read_rows(path):
    return list(csv.DictReader(path.open(encoding='utf-8-sig', newline=''), delimiter='\t'))

for edition in ('Steam_current', 'NoSteam_0.7.9.16232'):
    old = cf.Toc(BASE / 'Files' / edition / 'pakchunk1015-Windows_P.utoc')
    previous = {p: old.read_chunk(i) for p, i in old.files}
    files = dict(previous)
    edited = [e for e in evidence if e['edition'] == edition]
    changed = set()
    for change in edited:
        mount = change['mount']
        assert sha(previous[mount]) == change['source_sha256'], ('stale input', mount)
        data = (ROOT / 'Developer/V18_6/patched' / edition / mount).read_bytes()
        assert sha(data) == change['patched_sha256']
        files[mount] = data; changed.add(mount)
    if edition == 'Steam_current':
        mount = next(x for x in previous if x.endswith('/Essence_Tier_1_Small.uasset'))
        data = (ROOT / 'Developer/V18_6/patched' / edition / mount).read_bytes()
        assert sha(data) == item_report['patched_sha256']
        files[mount] = data; changed.add(mount)
    result = container(files, ROOT / 'Files' / edition / 'pakchunk1015-Windows_P.utoc')
    toc = cf.Toc(ROOT / 'Files' / edition / 'pakchunk1015-Windows_P.utoc')
    assert not toc.verify_meta() and sum(b[1] for b in toc.blocks) == len(toc.ub)
    assert len(toc.files) == len(previous)
    assert all(toc.read_chunk(i) == files[p] for p, i in toc.files)
    output = ROOT / 'FinalExtracted' / edition
    assert not output.exists(), 'Fresh container readback required'
    toc.extract_named(output)
    function_count = 0
    for change in edited:
        p = ui.zen.package(output / change['mount'])
        scripts = {}
        for e in p['exports']:
            if e['cls'] == FUNCTION:
                scripts[e['index']] = verify_script(p['bytes'][e['start']:e['end']])[3]
                function_count += 1
        for index, nodes in scripts.items():
            for n in nodes:
                for call in k.walk(n):
                    if call.op not in (0x46, 0x1c):
                        continue
                    target = struct.unpack('<i', call.parts[0].data)[0] - 1
                    if target not in scripts or not p['exports'][target]['name'].startswith('ExecuteUbergraph_'):
                        continue
                    arg = call.parts[1]
                    entry = struct.unpack('<i', arg.parts[0].data)[0] if arg.op == 0x1d else {0x25: 0, 0x26: 1}[arg.op]
                    assert entry in {x.old for n in scripts[target] for x in k.walk(n)}, (edition, index, entry)
    if edition == 'Steam_current':
        p = ui.zen.package(next(output.rglob('Essence_Tier_1_Small.uasset')))
        e = next(e for e in p['exports'] if e['name'].startswith('Default__'))
        records = guid_base_texts(p['bytes'][e['start']:e['end']])
        assert len(records) == 3 and all(x.namespace == 'CI_RU_Display_V18_4_Items' for x in records)
    for mount in previous.keys() - changed:
        assert files[mount] == previous[mount]
    folder = ROOT / 'Data' / edition
    loc = cf.Locres(folder / 'Game.locres'); oldloc = cf.Locres(BASE / 'Data' / edition / 'Game.locres')
    assert loc.entries[:len(oldloc.entries)] == oldloc.entries and len(loc.entries) == len(oldloc.entries) + 2
    rows = read_rows(folder / 'translation.tsv'); oldrows = read_rows(BASE / 'Data' / edition / 'translation.tsv')
    assert rows[:len(oldrows)] == oldrows and len(rows) == len(oldrows) + 2
    loc_index = {(e['namespace'], e['key'], str(e['source_hash'])): e for e in loc.entries}
    assert len(loc_index) == len(loc.entries)
    for row in rows:
        variants = [row['English'], row['English'].replace('\r\n', '\n').replace('\n', '\r\n')]
        assert int(row['SourceStringHash']) in [zlib.crc32(v.encode('utf-32-le')) & 0xffffffff for v in variants]
        assert row['Russian']
        assert collections.Counter(re.findall(r'\{[^{}]+\}', row['English'])) == collections.Counter(re.findall(r'\{[^{}]+\}', row['Russian']))
        entry = loc_index.get((row['Namespace'], row['Key'], row['SourceStringHash']))
        if entry:
            assert entry['value'].replace('\r\n', '\n') == row['Russian'].replace('\r\n', '\n')
        else:
            assert row in oldrows and 'exact FText local fallback' in row['SourceEvidence']
    assert cf.parse_pak_one(ROOT / 'Files' / edition / 'pakchunk1015-Windows_P.pak')['data'] == (folder / 'Game.locres').read_bytes()
    report['editions'][edition] = {**result, 'translation_rows': len(rows), 'locres_entries': len(loc.entries),
        'changed_packages': sorted(changed), 'strict_changed_widget_functions': function_count,
        'event_wrapper_entries': 'PASS', 'all_source_hashes_placeholders_original_rows_and_locres_entries': 'PASS',
        'all_other_packages_including_radial_settings_wide_character_and_journal': 'UNCHANGED',
        'exact_full_container_readback': 'PASS', 'native_essence_text_fields': '3/3 PASS' if edition == 'Steam_current' else 'no override'}
(ROOT / 'Reports/V18_6_VALIDATION.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(report, ensure_ascii=False, indent=2))
