"""Use each edition's own functions; change title layout and display activation."""
from pathlib import Path
import copy, json, sys
from display_tools import NativePatch, ui, k, find_script, expr_name, replace_function, sha

ROOT, BASE, SOURCE = map(Path, sys.argv[1:4])
report = {'release': '18.5', 'runtime_tested': False, 'assets': []}


def input_asset(edition, suffix):
    mount = 'Carnal_Instinct_UE5/Content/' + suffix
    base = BASE / 'Extracted' / edition / mount
    path = base if base.exists() else SOURCE / 'Content' / suffix
    assert path.exists(), (edition, suffix)
    return mount, path


for edition in ('Steam_current', 'NoSteam_0.7.9.16232'):
    mount, path = input_asset(edition, 'BlueprintSystems/DynamicRadialMenu/Widgets/W_MenuItem.uasset')
    patch = NativePatch(path)
    _, text, _ = patch.properties('TXT_Item')
    text_slot = patch.package['exports'][text['Slot']['value'] - 1]
    _, slot, _ = patch.properties(text_slot)
    assert slot['Content']['value'] - 1 == patch.export('TXT_Item')['index']
    patch.set(text_slot['name'], 'Padding', {'Left': -30., 'Top': 112., 'Right': -30., 'Bottom': -112.})
    patch.set(text_slot['name'], 'HorizontalAlignment', 0)
    patch.set(text_slot['name'], 'VerticalAlignment', 1)
    patch.set('TXT_Item', 'AutoWrapText', 1)
    patch.set('TXT_Item', 'WrapTextAt', 160.)
    patch.set('TXT_Item', 'TextTransformPolicy', 0)
    out = ROOT / 'Developer/V18_5/patched' / edition / mount
    data = patch.finish(out)
    report['assets'].append({'edition': edition, 'mount': mount, 'source_sha256': sha(path.read_bytes()),
                            'patched_sha256': sha(data), 'type': 'native_caption_layout',
                            'function_exports_unchanged': True, 'selection_geometry_unchanged': True,
                            'properties': patch.evidence})

    mount, path = input_asset(edition, 'NiceSettingsMenu/UI/Theme_3/WB_T3_MainMenu.uasset')
    p = ui.zen.package(path)
    e = next(e for e in p['exports'] if e['name'] == 'ExecuteUbergraph_WB_T3_MainMenu')
    _, _, _, nodes, _ = find_script(p['bytes'][e['start']:e['end']])
    nodes = copy.deepcopy(nodes)
    evidence = []
    for node in nodes:
        for expr in k.walk(node):
            if expr.op not in (0x19, 0x1a) or expr_name(expr.object, p['names']) != 'WB_T3_SettingsMenu':
                continue
            call = expr.context
            if expr_name(call, p['names']) != 'Activate' or len(call.parts) != 4 or call.parts[1].op != 0x27:
                continue
            old = call.parts[2]
            assert old.op == 0x27 or expr_name(old, p['names']) == 'CI_RU_LoadSettingsOnOpen', old.op
            call.parts[2] = k.Expr(0x28, old=old.old, old_end=old.old_end)
            evidence.append({'old_call_vm_offset': call.old, 'old_apply_argument': expr_name(old, p['names']) or 'True',
                             'new_apply_argument': 'False', 'bActivate': True})
    assert len(evidence) in (2, 3), (edition, len(evidence))
    replacement, rebase = replace_function(p, e, nodes)
    data = ui.zen.rebuild(p, replacement)
    out = ROOT / 'Developer/V18_5/patched' / edition / mount
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(data)
    q = ui.zen.package(out)
    assert p['names'] == q['names']
    for a, b in zip(p['exports'], q['exports']):
        if a['index'] not in replacement:
            assert p['bytes'][a['start']:a['end']] == data[b['start']:b['end']]
    report['assets'].append({'edition': edition, 'mount': mount, 'source_sha256': sha(path.read_bytes()),
                            'patched_sha256': sha(data), 'type': 'skip_reapplying_on_display_activation',
                            'manual_apply_and_save_component_unchanged': True, 'calls': evidence, **rebase})

(ROOT / 'Reports/V18_5_RADIAL_SETTINGS.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'patched_assets': len(report['assets']), 'runtime_tested': False}))
