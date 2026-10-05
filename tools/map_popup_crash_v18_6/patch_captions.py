"""Complete the union of known captions at display boundaries, for each edition."""
from pathlib import Path
import copy, csv, hashlib, json, re, sys, zlib
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'map_audit_v18_5'))
from display_tools import cf, ui, k, find_script, expr_name, replace_function, sha
from cityhash_pure import CityHash64

def key_hash(value):
    if not value:
        return 0
    number = CityHash64(value.encode('utf-16-le'))
    return ((number & 0xffffffff) + (number >> 32) * 23) & 0xffffffff

ROOT, BASE, SCAN = map(Path, sys.argv[1:4])
scan = json.loads(SCAN.read_text())
observed = set(scan['raw_fstring_candidates'])
explicit = json.loads(Path(__file__).with_name('captions.json').read_text())
report = {'release': '18.6', 'runtime_tested': False, 'source_map_cells_audited': scan['acquired_cells'],
          'gameplay_actor_quest_save_identifiers_changed': False, 'assets': [], 'editions': {}}

def unstring(expr):
    assert expr.op in (0x1f, 0x34)
    return expr.parts[0].data[:-1].decode('ascii') if expr.op == 0x1f else expr.parts[0].data[:-2].decode('utf-16-le')

def copy_value(expr):
    result = copy.deepcopy(expr)
    for x in k.walk(result):
        x.old = x.old_end = None
    return result

for edition in ('Steam_current', 'NoSteam_0.7.9.16232'):
    folder = ROOT / 'Data' / edition
    rows = list(csv.DictReader((BASE / 'Data' / edition / 'translation.tsv').open(encoding='utf-8-sig', newline=''), delimiter='\t'))
    columns = list(rows[0])
    loc = cf.Locres(BASE / 'Data' / edition / 'Game.locres')
    loc_index = {(e['namespace'], e['key'], str(e['source_hash'])): e for e in loc.entries}
    popup = next((BASE / 'FinalExtracted' / edition).rglob('WB_WorldMapPopup.uasset'))
    p = ui.zen.package(popup)
    e = next(e for e in p['exports'] if e['name'].startswith('ExecuteUbergraph'))
    nodes = find_script(p['bytes'][e['start']:e['end']])[3]
    pool = {}
    for n in nodes:
        for s in k.walk(n):
            if s.op == 0x69:
                for key, value in s.cases:
                    assert value.op == 0x29
                    label = expr_name(key, p['names'])
                    pool.setdefault(label.casefold(), (label, value))
    baseline_caption_count = len(pool)
    missing_translation = []
    additional = []
    # Existing source identities stay intact, including captions whose quest-list
    # records were omitted by the previous display dictionary.
    for row in rows:
        label = row['English']
        relevant = any(x in row['Assets'] for x in ('WorldMap/', 'Minimap/', 'Scalable_Map/', 'dmap_system/', 'dqst_system/common/quest_list'))
        if (label not in observed and not relevant) or not label.strip() or len(label) > 85 or '\n' in label:
            continue
        if label.startswith('{Z}:') or label == 'Text Info hovered icon.':
            continue  # Logging/placeholder strings are not map captions.
        folded = label.casefold()
        if folded in pool:
            continue
        identity = row['Namespace'], row['Key'], row['SourceStringHash']
        assert identity in loc_index, identity
        assert key_hash(row['Namespace']) == int(row['NamespaceHash'])
        assert key_hash(row['Key']) == int(row['KeyHash'])
        value = k.text(label, row['Key'], row['Namespace'])
        pool[folded] = (label, value)
        additional.append({'English': label, 'Russian': row['Russian'], 'identity': identity, 'source': row['Assets']})
    new_rows = []
    for item in explicit:
        label, russian = item['English'], item['Russian']
        namespace = 'CI_RU_Display_MapCaptions_V18_6'
        key = hashlib.md5(('MapCaption:' + label).encode()).hexdigest().upper()
        source_hash = zlib.crc32(label.encode('utf-32-le')) & 0xffffffff
        entry = {'namespace': namespace, 'key': key, 'source_hash': source_hash,
                 'namespace_hash': key_hash(namespace), 'key_hash': key_hash(key), 'value': russian}
        assert (namespace, key, str(source_hash)) not in loc_index
        loc.entries.append(entry)
        row = dict(zip(columns, [namespace, key, str(source_hash), str(entry['namespace_hash']), str(entry['key_hash']),
                                label, russian, item['evidence'] + '; display-only FText, English and source hash retained',
                                'RPG_InventorySystem/UI/WorldMap/WB_WorldMapPopup.uasset;DLG_Tree/dmap_system/widgets/w_03_map_icon.uasset']))
        new_rows.append(row)
        pool[label.casefold()] = (label, k.text(label, key, namespace))
        additional.append({'English': label, 'Russian': russian, 'identity': [namespace, key, str(source_hash)], 'source': item['evidence']})
    loc.write(folder / 'Game.locres')
    with (folder / 'translation.tsv').open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, columns, delimiter='\t'); writer.writeheader(); writer.writerows(rows + new_rows)
    cf.build_pak_one((folder / 'Game.locres').read_bytes(), 'Carnal_Instinct_UE5/Content/Localization/Game/en/Game.locres',
                     ROOT / 'Files' / edition / 'pakchunk1015-Windows_P.pak')
    for label in ('The Breadbasket', 'Raqote', 'Anubite Camp'):
        assert label.casefold() in pool
    for name, count in [('WB_WorldMapPopup.uasset', 2), ('w_03_map_icon.uasset', 5)]:
        path = next((BASE / 'FinalExtracted' / edition).rglob(name))
        mount = path.relative_to(BASE / 'FinalExtracted' / edition).as_posix()
        p = ui.zen.package(path)
        e = next(e for e in p['exports'] if e['name'].startswith('ExecuteUbergraph'))
        nodes = copy.deepcopy(find_script(p['bytes'][e['start']:e['end']])[3])
        appended = []
        lookup = {s.casefold(): i for i, s in enumerate(p['names'])}
        evidence = []
        for n in nodes:
            for switch in k.walk(n):
                if switch.op != 0x69 or len(switch.cases) < 100:
                    continue
                originals = [(expr_name(key, p['names']), value) for key, value in switch.cases]
                assert all(label and value.op == 0x29 for label, value in originals)
                present = {label.casefold() for label, value in originals}
                added = []
                for folded, (label, value) in sorted(pool.items()):
                    if folded in present:
                        continue
                    if folded not in lookup:
                        lookup[folded] = len(p['names']) + len(appended); appended.append(label)
                    switch.cases.append((k.name(lookup[folded]), copy_value(value)))
                    added.append(label)
                evidence.append({'old_switch_vm': switch.old, 'old_cases': len(originals),
                                 'new_cases': len(switch.cases), 'added_captions': added})
        assert len(evidence) == count
        replacements, rebase = replace_function(p, e, nodes)
        data = ui.zen.rebuild(p, replacements, appended)
        out = ROOT / 'Developer/V18_6/patched' / edition / mount
        out.parent.mkdir(parents=True, exist_ok=True); out.write_bytes(data)
        q = ui.zen.package(out)
        assert q['names'][:len(p['names'])] == p['names']
        assert cf.zen_info(data)['imports'] == cf.zen_info(p['bytes'])['imports']
        for old, new in zip(p['exports'], q['exports']):
            assert all(old[x] == new[x] for x in ('name', 'cls', 'outer', 'super', 'template', 'flags'))
            if old['index'] not in replacements:
                assert p['bytes'][old['start']:old['end']] == data[new['start']:new['end']]
        report['assets'].append({'edition': edition, 'mount': mount, 'source_sha256': sha(p['bytes']),
                                'patched_sha256': sha(data), 'evidence': evidence, **rebase})
    report['editions'][edition] = {'previous_popup_captions': baseline_caption_count, 'unified_caption_pool': len(pool),
                                  'added_captions': additional, 'new_localization_rows': len(new_rows),
                                  'source_map_raw_labels_missing_from_dictionary': sorted(x for x in observed if re.fullmatch(r'[A-Za-z][A-Za-z \'’\-]+', x) and ' ' in x and x.casefold() not in pool)}
    assert not report['editions'][edition]['source_map_raw_labels_missing_from_dictionary']
(ROOT / 'Reports/V18_6_MAP_CAPTIONS.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({ed: {k: v for k, v in data.items() if k != 'added_captions'} for ed, data in report['editions'].items()}, ensure_ascii=False, indent=2))
