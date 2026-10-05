"""Fix the complete three FText records; every other item byte is preserved."""
from pathlib import Path
import json, struct, sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'map_audit_v18_5'))
from display_tools import ui, cf, sha
from native_ftext import guid_base_texts, read_base, replace_namespace

ROOT, SOURCE = map(Path, sys.argv[1:3])
source = next(SOURCE.rglob('Essence_Tier_1_Small.uasset'))
p = ui.zen.package(source)
namespace = 'CI_RU_Display_V18_4_Items'
changed = {}; evidence = []
keys = {'7161373344630149D4AE198A780FAC9B', 'A5DAC0B440486F2FF22295AB9517C97B', '444A551D4C5C423C08DF8F86C652F88E'}
for export in p['exports']:
    if not export['name'].startswith('Default__'):
        continue
    original = p['bytes'][export['start']:export['end']]
    records = [r for r in guid_base_texts(original) if r.key in keys and not r.namespace]
    assert len(records) == 3 and {r.key for r in records} == keys
    raw = original
    for record in reversed(records):
        value = replace_namespace(original, record, namespace, cf.fstring_write)
        raw = raw[:record.start] + value + raw[record.end:]
    written = guid_base_texts(raw)
    assert len(written) == len(records)
    # Compare every byte outside the three exact typed text records.
    before_segments = []; after_segments = []; old_cursor = new_cursor = 0
    for old, new in zip(records, written):
        assert (old.flags, old.key, old.source) == (new.flags, new.key, new.source)
        assert new.namespace == namespace
        before_segments.append(original[old_cursor:old.start]); after_segments.append(raw[new_cursor:new.start])
        old_cursor, new_cursor = old.end, new.end
        evidence.append({'key': old.key, 'original_text_start': old.start,
                         'original_empty_namespace_count': struct.unpack_from('<i', original, old.namespace_start)[0],
                         'original_namespace_serialized_bytes': old.namespace_end - old.namespace_start,
                         'written_namespace_count': struct.unpack_from('<i', raw, new.namespace_start)[0],
                         'new_native_text_start': new.start})
    before_segments.append(original[old_cursor:]); after_segments.append(raw[new_cursor:])
    assert before_segments == after_segments
    changed[export['index']] = raw
out = ROOT / 'Developer/V18_6/patched/Steam_current/Carnal_Instinct_UE5' / source.relative_to(SOURCE)
out.parent.mkdir(parents=True, exist_ok=True)
data = ui.zen.rebuild(p, changed); out.write_bytes(data)
q = ui.zen.package(out)
assert p['names'] == q['names']
assert cf.zen_info(data)['imports'] == cf.zen_info(p['bytes'])['imports']
for old, new in zip(p['exports'], q['exports']):
    assert all(old[k] == new[k] for k in ('name', 'cls', 'outer', 'super', 'template', 'flags'))
    if old['index'] not in changed:
        assert p['bytes'][old['start']:old['end']] == data[new['start']:new['end']]
    else:
        assert len(guid_base_texts(data[new['start']:new['end']])) == 3
report = {'release': '18.6', 'source_sha256': sha(p['bytes']), 'patched_sha256': sha(data),
          'source_bytes': len(p['bytes']), 'patched_bytes': len(data), 'fields': evidence,
          'root_cause': 'v18.4 substring replacement matched inside a 5-byte empty FString, leaving count byte 0x01; new count became 0x1a01=6657.',
          'other_class_and_item_bytes': 'UNCHANGED', 'complete_native_ftext_bounded_readback': '3/3 PASS',
          'runtime_tested': False}
(ROOT / 'Reports/V18_6_NATIVE_ITEM_FIX.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
