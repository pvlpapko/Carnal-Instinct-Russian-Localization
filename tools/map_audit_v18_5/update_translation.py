"""Apply reviewed rows by exact namespace/key/original source hash."""
from pathlib import Path
import collections, csv, json, re, sys, zlib
from display_tools import cf

ROOT, BASE, SCAN = map(Path, sys.argv[1:4])
changes = json.loads(Path(__file__).with_name('editorial_changes.json').read_text())
scan = json.loads(SCAN.read_text())
assert scan['all_cells_acquired'] and not scan['errors']
report = {'release': '18.5', 'runtime_tested': False, 'editions': {}, 'changes': changes,
          'map_source_domain': 'Current Steam source cells; shared captions checked against both edition tables. NoSteam progression cells not independently acquired.',
          'morphology_candidates_manually_reviewed': 30,
          'linguistic_review_limit': 'Full-table automated checks and targeted manual source-context review; not a claim of a complete human line-by-line proofread.'}


def identity(row):
    return row['Namespace'], row['Key'], row['SourceStringHash']


for edition in ('Steam_current', 'NoSteam_0.7.9.16232'):
    folder = ROOT / 'Data' / edition
    original = BASE / 'Data' / edition
    with (original / 'translation.tsv').open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream, delimiter='\t')
        rows, fields = list(reader), reader.fieldnames
    indexed = {identity(r): r for r in rows}
    assert len(indexed) == len(rows)
    loc = cf.Locres(original / 'Game.locres')
    loc_index = {(r['namespace'], r['key'], str(r['source_hash'])): r for r in loc.entries}
    old_identities = [(e['namespace'], e['key'], e['source_hash'], e['namespace_hash'], e['key_hash']) for e in loc.entries]
    applied = []
    for change in changes:
        if change['edition'] != edition:
            continue
        key = change['namespace'], change['key'], change['source_hash']
        row = indexed[key]
        assert row['Russian'] == change['old'] and row['English'] == change['english']
        assert key in loc_index, 'Fallback literal needs a separate typed display-property edit'
        for expression in (r'\{[^{}]+\}', r'</?[A-Za-z][^>]*>'):
            assert collections.Counter(re.findall(expression, row['Russian'])) == collections.Counter(re.findall(expression, change['new']))
        assert row['Russian'].count('\n') == change['new'].count('\n')
        row['Russian'] = change['new']
        loc_index[key]['value'] = change['new']
        applied.append(change)
    folder.mkdir(parents=True, exist_ok=True)
    loc.write(folder / 'Game.locres')
    with (folder / 'translation.tsv').open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, delimiter='\t', lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
    new = cf.Locres(folder / 'Game.locres')
    assert old_identities == [(e['namespace'], e['key'], e['source_hash'], e['namespace_hash'], e['key_hash']) for e in new.entries]
    missing = []
    for text in scan['native_ftext_occurrences']:
        entry = loc_index.get(identity(text))
        if entry is None or not entry['value']:
            missing.append(text)
    assert not missing
    pak = ROOT / 'Files' / edition / 'pakchunk1015-Windows_P.pak'
    cf.build_pak_one((folder / 'Game.locres').read_bytes(), 'Carnal_Instinct_UE5/Content/Localization/Game/en/Game.locres', pak)
    assert cf.parse_pak_one(pak)['data'] == (folder / 'Game.locres').read_bytes()
    report['editions'][edition] = {'rows': len(rows), 'editorial_changes': len(applied),
                                  'source_cells_audited': scan['acquired_cells'],
                                  'native_map_ftext_occurrences': len(scan['native_ftext_occurrences']),
                                  'unique_native_map_ftext_identities': len({identity(t) for t in scan['native_ftext_occurrences']}),
                                  'missing_native_map_localization_identities': 0,
                                  'original_identities_hashes_placeholders_tags_newlines': 'PASS'}
(ROOT / 'Reports/V18_5_TRANSLATION_MAP_AUDIT.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(report['editions']))
