"""Read TOC blocks, package-store dependencies and Zen spans independently."""
from pathlib import Path
import json, struct, sys
from display_tools import cf

root = Path(sys.argv[1])
sys.path.insert(0, str(root / 'Developer/AnimationIsolationFix'))
import iostore_simple as independent
report = {'release': '18.5', 'independent_reader': 'iostore_simple with separate BLAKE3 implementation', 'editions': {}}
for edition in ('Steam_current', 'NoSteam_0.7.9.16232'):
    folder = root / 'Files' / edition
    toc, data, info = independent.validate(folder / 'pakchunk1015-Windows_P.utoc', folder / 'pakchunk1015-Windows_P.ucas', False)
    assert not info['bad_hashes'] and info['block_cover_exact']
    assert len(info['container_header_indices']) == 1
    header = independent.parse_container_header(data[info['container_header_indices'][0]])
    pids = {int.from_bytes(toc['chunk_ids'][idx][:8], 'little') for idx in toc['dir']['paths'].values()}
    assert pids == set(header['package_ids'])
    entries = {e['package_id']: e for e in header['entries']}
    exports = 0
    for path, idx in toc['dir']['paths'].items():
        raw = data[idx]; z = cf.zen_info(raw); h = z['header']
        pid = cf.package_id(z['package'])
        assert pid == int.from_bytes(toc['chunk_ids'][idx][:8], 'little')
        assert entries[pid]['imports'] == [cf.package_id(p) for p in z['imports']]
        assert (h[9] - h[8]) % 72 == 0
        for pos in range(h[8], h[9], 72):
            offset, size = struct.unpack_from('<QQ', raw, pos)
            assert h[1] + offset + size <= len(raw), (edition, path, pos)
            exports += 1
    report['editions'][edition] = {'package_ids_and_imported_dependencies': 'PASS',
        'hashes_and_physical_cover': 'PASS', 'export_serial_spans': 'PASS', 'exports': exports, 'packages': len(pids)}
(root / 'Reports/V18_5_INDEPENDENT_CONTAINER_VALIDATION.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
