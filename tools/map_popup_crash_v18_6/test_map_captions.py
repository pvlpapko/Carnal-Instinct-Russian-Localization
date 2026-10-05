"""Reported runtime omissions must resolve in both rows and every icon path."""
from pathlib import Path
import os, sys, unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'map_audit_v18_5'))
from display_tools import ui, k, find_script, expr_name

ROOT = Path(os.environ.get('CI_RU_CHECK_ROOT', '/workspace/project-context/carnal-instinct/v18.5'))

class MapCaptionRegression(unittest.TestCase):
    def test_reported_captions_in_all_display_paths(self):
        for edition in ('Steam_current', 'NoSteam_0.7.9.16232'):
            for name, count in [('WB_WorldMapPopup.uasset', 2), ('w_03_map_icon.uasset', 5)]:
                p = ui.zen.package(next((ROOT / 'FinalExtracted' / edition).rglob(name)))
                e = next(e for e in p['exports'] if e['name'].startswith('ExecuteUbergraph'))
                nodes = find_script(p['bytes'][e['start']:e['end']])[3]
                switches = [s for n in nodes for s in k.walk(n) if s.op == 0x69 and len(s.cases) > 100]
                self.assertEqual(len(switches), count)
                for switch in switches:
                    captions = {expr_name(key, p['names']).casefold(): value for key, value in switch.cases}
                    for label in ('RAQOTE', 'THE BREADBASKET', 'ANUBITE CAMP'):
                        with self.subTest(edition=edition, asset=name, switch=switch.old, caption=label):
                            self.assertTrue(label.casefold() in captions, 'missing displayed caption: ' + label)
                            self.assertEqual(captions[label.casefold()].op, 0x29)

if __name__ == '__main__':
    unittest.main()
