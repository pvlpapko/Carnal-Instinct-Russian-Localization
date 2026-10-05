"""Extend existing display switches with observed spellings, preserving gameplay IDs."""
from pathlib import Path
import copy, json, re, sys
from display_tools import ui, cf, k, find_script, expr_name, replace_function, sha

ROOT, BASE, SOURCE, SCAN = map(Path, sys.argv[1:5])
scan = json.loads(SCAN.read_text())
assert scan['all_cells_acquired'] and not scan['errors']
observed = set(scan['name_candidates']) | set(scan['raw_fstring_candidates'])
observed.update(["Tal'Senet", 'Tal’Senet'])  # Supplied screenshot: campfire region caption.
for path in SOURCE.rglob('*.uasset'):
    if any(x in path.as_posix() for x in ('/WorldMap/', '/Minimap/', '/dqst_system/common/', '/dmap_system/common/')):
        observed.update(ui.zen.package(path)['names'])


def normalized(value):
    value = value.translate(str.maketrans({'’': "'", '‘': "'", '-': "'", '‑': "'", '–': "'"}))
    return re.sub(r'\s+', '', value).casefold()


def clear_positions(expr):
    for x in k.walk(expr):
        x.old = x.old_end = None
    return expr


report = {'release': '18.5', 'runtime_tested': False, 'source_cells_checked': scan['acquired_cells'],
          'internal_actor_quest_and_save_names_changed': False, 'assets': []}
for edition in ('Steam_current', 'NoSteam_0.7.9.16232'):
    for suffix in ('RPG_InventorySystem/UI/WorldMap/WB_WorldMapPopup.uasset',
                   'DLG_Tree/dmap_system/widgets/w_03_map_icon.uasset'):
        mount = 'Carnal_Instinct_UE5/Content/' + suffix
        baseline = BASE / 'VerifiedExtracted' / edition / mount
        path = baseline if baseline.exists() else SOURCE / 'Content' / suffix
        assert path.exists(), path
        p = ui.zen.package(path)
        e = next(e for e in p['exports'] if e['name'].startswith('ExecuteUbergraph_'))
        _, _, _, nodes, _ = find_script(p['bytes'][e['start']:e['end']])
        nodes = copy.deepcopy(nodes)
        appended = []
        name_lookup = {s.casefold(): i for i, s in enumerate(p['names'])}
        evidence = []
        switches = []
        for node in nodes:
            for switch in k.walk(node):
                if switch.op != 0x69 or len(switch.cases) < 400:
                    continue
                originals = [(expr_name(key, p['names']), value) for key, value in switch.cases]
                if not all(name and value.op == 0x29 for name, value in originals):
                    continue
                switches.append(switch)
                exact = {name.casefold() for name, value in originals}
                pool = {}
                for name, value in originals:
                    pool.setdefault(normalized(name), (name, value))
                added = []
                for label in sorted(observed):
                    if label.casefold() in exact or len(label) > 200 or normalized(label) not in pool:
                        continue
                    canonical, value = pool[normalized(label)]
                    folded = label.casefold()
                    if folded not in name_lookup:
                        name_lookup[folded] = len(p['names']) + len(appended)
                        appended.append(label)
                    key = k.name(name_lookup[folded])
                    new_value = clear_positions(copy.deepcopy(value))
                    switch.cases.append((key, new_value))
                    exact.add(folded)
                    added.append({'input': label, 'canonical': canonical})
                evidence.append({'old_switch_vm': switch.old, 'old_cases': len(originals),
                                 'new_cases': len(switch.cases), 'aliases': added})
        assert switches, (edition, mount, 'no existing display switch')
        assert all(any(x['input'] == "Tal'Senet" for x in ev['aliases']) for ev in evidence), (edition, mount)
        repairs = {}
        if suffix.endswith('w_03_map_icon.uasset'):
            # v18.4 has OnMouseLeave pointing into the caption switch's string data.
            # The unique final handler clears the hover TextBlock and returns.
            clear_handlers = []
            for node in nodes:
                node_names = [expr_name(x, p['names'] + appended) for x in k.walk(node)]
                if node.op == 0x19 and set(x for x in node_names if x) == {'parent_widget', 'text_hover', 'SetText'}:
                    clear_handlers.append(node.old)
            assert len(clear_handlers) == 1 and clear_handlers[0] == 144117, clear_handlers
            repairs['OnMouseLeave'] = (139894, clear_handlers[0])
        replacements, rebase = replace_function(p, e, nodes, repairs)
        data = ui.zen.rebuild(p, replacements, appended)
        out = ROOT / 'Developer/V18_5/patched' / edition / mount
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(data)
        q = ui.zen.package(out)
        assert q['names'][:len(p['names'])] == p['names']
        assert cf.zen_info(data)['imports'] == cf.zen_info(p['bytes'])['imports']
        for a, b in zip(p['exports'], q['exports']):
            assert all(a[key] == b[key] for key in ('name', 'cls', 'outer', 'super', 'template', 'flags'))
            if a['index'] not in replacements:
                assert p['bytes'][a['start']:a['end']] == data[b['start']:b['end']]
        report['assets'].append({'edition': edition, 'mount': mount, 'source_sha256': sha(path.read_bytes()),
                                'patched_sha256': sha(data), 'appended_input_names': appended,
                                'evidence': evidence, **rebase})

(ROOT / 'Reports/V18_5_MAP_DISPLAY_ALIASES.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'assets': len(report['assets']), 'aliases_per_switch':
                  [[len(e['aliases']) for e in a['evidence']] for a in report['assets']]}))
