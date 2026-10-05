"""Regressions from the supplied HUD and NoSteam journal screenshots."""
import copy, csv, os, struct, sys, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'ui_parity_v18_7'))
from inspect_native import ui, props
from native_edit import plain
from display_tools import FUNCTION, k, find_script

ROOT = Path(os.environ['CI_RU_CHECK_ROOT'])
BASE = Path(os.environ.get('CI_RU_BASE_ROOT', '/workspace/project-context/carnal-instinct/v18.9'))
INPUT = Path('/workspace/project-context/carnal-instinct/v18.10/Developer/V18_10/inputs')
NAMESPACE = 'CI_RU_Display_Quest'

def asset(root, edition, name):
    hits = list((root / 'FinalExtracted' / edition).rglob(name + '.uasset'))
    if not hits:
        hits = list((INPUT / edition).rglob(name + '.uasset'))
    assert len(hits) == 1, (root, edition, name, hits)
    return ui.zen.package(hits[0])

def functions(p):
    return {e['index']: p['bytes'][e['start']:e['end']] for e in p['exports'] if e['cls'] == FUNCTION}

def string(x):
    assert x.op in (0x1f, 0x34)
    return x.parts[0].data[:-1 if x.op == 0x1f else -2].decode('ascii' if x.op == 0x1f else 'utf-16-le')

def switches(p):
    result = []
    for raw in functions(p).values():
        for node in find_script(raw)[3]:
            for x in k.walk(node):
                if x.op == 0x69 and x.cases and all(v.op == 0x29 and len(v.parts) == 4 and string(v.parts[3]) == NAMESPACE for _, v in x.cases):
                    result.append(x)
    return result

def rows():
    with (ROOT / 'Data/Steam_current/translation.tsv').open(encoding='utf-8-sig', newline='') as f:
        return [r for r in csv.DictReader(f, delimiter='\t') if r['Namespace'] == NAMESPACE]

class QuestDisplayTests(unittest.TestCase):
    def test_first_quest_and_optional_weapon_on_hud(self):
        expected = {'Find a way further inland to safety': 'Найти безопасный путь вглубь острова',
                    'Find a weapon amongst the wreckage': 'Найти оружие среди обломков'}
        translations = {(r['Key'], r['English']): r['Russian'] for r in rows()}
        for name, english in zip(['w_06_objective_entry', 'w_07_sub_objective'], expected):
            p = asset(ROOT, 'Steam_current', name)
            options = switches(p)
            self.assertTrue(options, f'{name}: HUD has no objective translation route')
            for switch in options:
                choices = {p['names'][struct.unpack('<II', key.parts[0].data)[0]].casefold(): value for key, value in switch.cases}
                value = choices[english.casefold()]
                self.assertEqual(string(value.parts[1]), english)
                self.assertEqual(translations[(string(value.parts[2]), english)], expected[english])

    def test_all_known_objectives_and_unknown_fallback(self):
        translations = {(r['Key'], r['English']): r['Russian'] for r in rows()}
        wanted = {r['English'].casefold(): r['Russian'] for r in rows()}
        for name, count in [('w_06_objective_entry', 1), ('w_07_sub_objective', 2)]:
            p = asset(ROOT, 'Steam_current', name)
            options = switches(p)
            self.assertEqual(len(options), count)
            for switch in options:
                actual = {p['names'][struct.unpack('<II', key.parts[0].data)[0]].casefold(): translations[(string(value.parts[2]), string(value.parts[1]))] for key, value in switch.cases}
                self.assertEqual(actual, wanted)
                self.assertEqual(switch.default.op, 0x00)  # existing localized text, including unknown future objectives

    def test_nostem_journal_text_marker_and_card_bounds(self):
        for name in ['WB_QuestObjectiveName', 'WB_QuestObjectiveDescription']:
            p = asset(ROOT, 'NoSteam_0.7.9.16232', name)
            e = next(e for e in p['exports'] if e['name'] == 'Text_ObjectiveName')
            self.assertEqual(plain(props(p, e))['Font']['Size'], 16)
        p = asset(ROOT, 'NoSteam_0.7.9.16232', 'WB_QuestName')
        def values(name): return plain(props(p, next(e for e in p['exports'] if e['name'] == name)))
        style = values('Checkbox_Tracked')['WidgetStyle']
        self.assertEqual(style['CheckedImage']['ImageSize'], [28, 28])
        self.assertEqual(values('SizeBox_27')['WidthOverride'] + values('SizeBoxSlot_0')['Padding']['Left'] + values('SizeBoxSlot_0')['Padding']['Right'], 550)

    def test_nostem_gameplay_functions_classes_and_cdos_preserved(self):
        for name in ['WB_QuestName', 'WB_QuestObjectiveName', 'WB_QuestObjectiveDescription']:
            old = asset(BASE, 'NoSteam_0.7.9.16232', name)
            new = asset(ROOT, 'NoSteam_0.7.9.16232', name)
            self.assertEqual(functions(new), functions(old))
            for a, b in zip(old['exports'], new['exports']):
                if a['name'].endswith('_C'):
                    self.assertEqual(old['bytes'][a['start']:a['end']], new['bytes'][b['start']:b['end']])

if __name__ == '__main__': unittest.main()
