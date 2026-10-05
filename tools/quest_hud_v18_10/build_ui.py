"""Display-only objective translation and native NoSteam journal refinements."""
import copy, csv, json, struct, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'ui_parity_v18_7'))
from native_edit import Edit, plain
from inspect_native import ui, cf
from display_tools import FUNCTION, k, find_script, expr_name, replace_function, verify_script, sha

ROOT, BASE = map(Path, sys.argv[1:3])
report = {'release': '18.10', 'runtime_tested': False, 'assets': [], 'nosteam_missing_sources': ['WB_QuestScreen', 'w_06_objective_entry', 'w_07_sub_objective']}
with (ROOT / 'Data/Steam_current/translation.tsv').open(encoding='utf-8-sig', newline='') as f:
    records = [r for r in csv.DictReader(f, delimiter='\t') if r['Namespace'] == 'CI_RU_Display_Quest']
pool = {}
for row in records:
    key = row['English'].casefold()
    if key in pool:
        assert pool[key]['Russian'] == row['Russian']
    else:
        pool[key] = row

def clear(x):
    for node in k.walk(x): node.old = node.old_end = None
    return x

for name in ['w_06_objective_entry', 'w_07_sub_objective']:
    source = next((ROOT / 'Developer/V18_10/inputs/Steam_current').rglob(name + '.uasset'))
    p = ui.zen.package(source)
    export = next(e for e in p['exports'] if e['name'].startswith('ExecuteUbergraph_'))
    nodes = copy.deepcopy(find_script(p['bytes'][export['start']:export['end']])[3])
    calls = [x for n in nodes for x in k.walk(n) if x.op in (0x1b, 0x45) and expr_name(x, p['names']) == 'get_line_localization']
    assert len(calls) == 1
    index = calls[0].parts[2]
    assert index.op == 0x42 and expr_name(index.parts[1], p['names']) == ('objective_data' if name.startswith('w_06') else 'sub_objective_data')
    appended = []
    name_ids = {value.casefold(): i for i, value in enumerate(p['names'])}
    for row in pool.values():
        folded = row['English'].casefold()
        if folded not in name_ids:
            name_ids[folded] = len(p['names']) + len(appended)
            appended.append(row['English'])
    changed = []
    def replace(x):
        if x.op == 0x00 and expr_name(x, p['names']) == 'CallFunc_get_line_localization_line_text':
            switch = k.Expr(0x69, old=x.old, old_end=x.old_end,
                index=clear(copy.deepcopy(index)), default=clear(copy.deepcopy(x)),
                cases=[(k.name(name_ids[row['English'].casefold()]), k.text(row['English'], row['Key'], row['Namespace'])) for row in pool.values()])
            changed.append(x.old)
            return switch
        if x.op in (0x12, 0x19, 0x1a):
            x.object = replace(x.object); x.context = replace(x.context)
        elif x.op == 0x69:
            x.index = replace(x.index); x.cases = [(replace(a), replace(b)) for a, b in x.cases]; x.default = replace(x.default)
        else:
            x.parts = [replace(a) if isinstance(a, k.Expr) else a for a in x.parts]
        return x
    for i, node in enumerate(nodes):
        # The localization call still writes its original output variable.
        if any(x is calls[0] for x in k.walk(node)): continue
        nodes[i] = replace(node)
    assert len(changed) == (1 if name.startswith('w_06') else 2), (name, changed)
    replacements, proof = replace_function(p, export, nodes)
    data = ui.zen.rebuild(p, replacements, appended)
    mount = 'Carnal_Instinct_UE5/Content/' + p['name'].removeprefix('/Game/') + '.uasset'
    target = ROOT / 'Developer/V18_10/patched/Steam_current' / mount
    target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(data)
    q = ui.zen.package(target)
    assert cf.zen_info(data)['imports'] == cf.zen_info(p['bytes'])['imports']
    assert q['names'][:len(p['names'])] == p['names']
    for a, b in zip(p['exports'], q['exports']):
        assert all(a[key] == b[key] for key in ['name', 'cls', 'outer', 'super', 'template', 'flags'])
        if a['index'] not in replacements: assert p['bytes'][a['start']:a['end']] == data[b['start']:b['end']]
        if b['cls'] == FUNCTION: verify_script(data[b['start']:b['end']])
    report['assets'].append({'name': name, 'edition': 'Steam_current', 'mount': mount, 'source_sha256': sha(p['bytes']),
        'patched_sha256': sha(data), 'type': 'objective_display_only', 'translated_name_cases': len(pool), 'display_reads': changed,
        'unknown_objective_fallback': 'original localization output', 'localization_audio_state_and_counters_preserved': True,
        'imports_and_class_cdo_unchanged': True, **proof})

for name in ['WB_QuestObjectiveName', 'WB_QuestObjectiveDescription', 'WB_QuestName']:
    source = next((BASE / 'FinalExtracted/NoSteam_0.7.9.16232').rglob(name + '.uasset'))
    e = Edit(source)
    if name != 'WB_QuestName':
        font = plain(e.values('Text_ObjectiveName'))['Font']; font['Size'] = 16.; font['LetterSpacing'] = 0
        e.set('Text_ObjectiveName', 'Font', font)
        if name == 'WB_QuestObjectiveName':
            e.set('SizeBox_63', 'WidthOverride', 24.); e.set('SizeBox_63', 'HeightOverride', 24.)
    else:
        style = plain(e.values('Checkbox_Tracked'))['WidgetStyle']
        for key in ['UncheckedImage', 'UncheckedHoveredImage', 'UncheckedPressedImage', 'CheckedImage', 'CheckedHoveredImage', 'CheckedPressedImage']:
            brush = style.setdefault(key, copy.deepcopy(style['CheckedImage']) if key.startswith('Checked') else {'DrawAs': 0})
            brush['ImageSize'] = [28., 28.]
        e.set('Checkbox_Tracked', 'WidgetStyle', style)
        e.set('Checkbox_Tracked', 'RenderTransform', {'Scale': [1., 1.]})
        slot = next(x for x in e.exports if ui.CLASS.get(x['cls']) == 'OverlaySlot' and plain(e.values(x)).get('Content') == e.export('Checkbox_Tracked')['index'] + 1)
        padding = plain(e.values(slot))['Padding']; padding['Right'] = 10.; e.set(slot, 'Padding', padding)
        padding = plain(e.values('SizeBoxSlot_0'))['Padding']; padding['Right'] = 10.; e.set('SizeBoxSlot_0', 'Padding', padding)
        e.set('SizeBox_27', 'WidthOverride', 530.)
    mount = 'Carnal_Instinct_UE5/Content/' + e.p['name'].removeprefix('/Game/') + '.uasset'
    item = e.finish(ROOT / 'Developer/V18_10/patched/NoSteam_0.7.9.16232' / mount)
    item.update(name=name, edition='NoSteam_0.7.9.16232', mount=mount, type='native_journal_typography_tracking')
    report['assets'].append(item)

(ROOT / 'Reports/V18_10_UI.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'assets': len(report['assets']), 'objective_cases': len(pool), 'nosteam_source_pending': report['nosteam_missing_sources']}))
