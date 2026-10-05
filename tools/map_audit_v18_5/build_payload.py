"""Merge only reviewed display assets into authoritative v18.4 containers."""
from pathlib import Path
import csv, collections, json, re, struct, sys, zlib
from display_tools import cf, ui, k, verify_script, FUNCTION, sha

ROOT, BASE, SOURCE = map(Path, sys.argv[1:4])
report = {'release': '18.5', 'runtime_tested': False, 'editions': {}}
evidence = sum([json.loads((ROOT / 'Reports' / name).read_text())['assets'] for name in
                ('V18_5_RADIAL_SETTINGS.json', 'V18_5_MAP_DISPLAY_ALIASES.json')], [])


def container(files, out):
    original = cf.build_directory
    cf.build_directory = lambda pairs, mount='../../../': original([(i, p) for p, i in pairs], mount)
    try:
        return cf.build_container(list(files.items()), out)
    finally:
        cf.build_directory = original


def loc_identity(e):
    return tuple(e[x] for x in ('namespace', 'key', 'source_hash', 'namespace_hash', 'key_hash'))


for edition in ('Steam_current', 'NoSteam_0.7.9.16232'):
    old = cf.Toc(BASE / 'Files' / edition / 'pakchunk1015-Windows_P.utoc')
    previous = {p: old.read_chunk(i) for p, i in old.files}
    files = dict(previous)
    edited = [e for e in evidence if e['edition'] == edition]
    assert len(edited) == 4
    for change in edited:
        mount = change['mount']
        source = previous.get(mount)
        if source is None:
            assert edition == 'Steam_current'
            source = (SOURCE / mount.removeprefix('Carnal_Instinct_UE5/')).read_bytes()
        assert sha(source) == change['source_sha256'], ('stale input cache', edition, mount)
        patched = (ROOT / 'Developer/V18_5/patched' / edition / mount).read_bytes()
        assert sha(patched) == change['patched_sha256']
        files[mount] = patched
    result = container(files, ROOT / 'Files' / edition / 'pakchunk1015-Windows_P.utoc')
    toc = cf.Toc(ROOT / 'Files' / edition / 'pakchunk1015-Windows_P.utoc')
    assert not toc.verify_meta() and sum(b[1] for b in toc.blocks) == len(toc.ub)
    assert len(toc.files) == len(files)
    assert all(toc.read_chunk(i) == files[p] for p, i in toc.files)
    # Fresh game-consumed readback. Never trust copied Extracted caches.
    output = ROOT / 'FinalExtracted' / edition
    assert not output.exists(), 'Use a fresh readback directory'
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
            for node in nodes:
                for call in k.walk(node):
                    if call.op not in (0x46, 0x1c):
                        continue
                    target = struct.unpack('<i', call.parts[0].data)[0] - 1
                    if target not in scripts or not p['exports'][target]['name'].startswith('ExecuteUbergraph_'):
                        continue
                    arg = call.parts[1]
                    entry = struct.unpack('<i', arg.parts[0].data)[0] if arg.op == 0x1d else {0x25: 0, 0x26: 1}[arg.op]
                    starts = {x.old for n in scripts[target] for x in k.walk(n)}
                    assert entry in starts, (edition, change['mount'], p['exports'][index]['name'], entry)
    folder = ROOT / 'Data' / edition
    loc = cf.Locres(folder / 'Game.locres')
    baseline_loc = cf.Locres(BASE / 'Data' / edition / 'Game.locres')
    assert list(map(loc_identity, loc.entries)) == list(map(loc_identity, baseline_loc.entries))
    indexed = {(e['namespace'], e['key'], str(e['source_hash'])): e for e in loc.entries}
    assert len(indexed) == len(loc.entries)
    rows = list(csv.DictReader((folder / 'translation.tsv').open(encoding='utf-8-sig', newline=''), delimiter='\t'))
    original_rows = list(csv.DictReader((BASE / 'Data' / edition / 'translation.tsv').open(encoding='utf-8-sig', newline=''), delimiter='\t'))
    assert len(rows) == len(original_rows)
    for row, before in zip(rows, original_rows):
        assert {a: v for a, v in row.items() if a != 'Russian'} == {a: v for a, v in before.items() if a != 'Russian'}
        assert row['Russian']
        variants = [row['English'], row['English'].replace('\r\n', '\n').replace('\n', '\r\n')]
        assert int(row['SourceStringHash']) in [zlib.crc32(s.encode('utf-32-le')) & 0xffffffff for s in variants]
        for expr in (r'\{[^{}]+\}', r'</?[A-Za-z][^>]*>'):
            assert collections.Counter(re.findall(expr, before['Russian'])) == collections.Counter(re.findall(expr, row['Russian']))
        assert before['Russian'].count('\n') == row['Russian'].count('\n')
        assert collections.Counter(re.findall(r'\{[^{}]+\}', row['English'])) == collections.Counter(re.findall(r'\{[^{}]+\}', row['Russian']))
        e = indexed.get((row['Namespace'], row['Key'], row['SourceStringHash']))
        if e:
            assert e['value'].replace('\r\n', '\n') == row['Russian'].replace('\r\n', '\n')
        else:
            assert 'exact FText local fallback' in row['SourceEvidence'] and row == before
    assert cf.parse_pak_one(ROOT / 'Files' / edition / 'pakchunk1015-Windows_P.pak')['data'] == (folder / 'Game.locres').read_bytes()
    # Existing wide character/journal assets must be retained byte-for-byte.
    for mount, data in previous.items():
        if mount not in {e['mount'] for e in edited}:
            assert files[mount] == data
    report['editions'][edition] = {**result, 'translation_rows': len(rows), 'locres_entries': len(loc.entries),
        'reviewed_display_assets': 4, 'strict_function_roundtrip_and_control_checks': function_count,
        'event_wrapper_entries': 'PASS', 'baseline_input_hashes': 'PASS', 'container_exact_readback_and_hashes': 'PASS',
        'localization_identities_source_hashes_placeholders_tags_newlines': 'PASS',
        'other_baseline_packages_including_wide_character_and_journal': 'UNCHANGED'}
(ROOT / 'Reports/V18_5_VALIDATION.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(report, ensure_ascii=False, indent=2))
