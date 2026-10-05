"""Regression from the actual startup-failing v18.5 item export."""
from pathlib import Path
import os, sys, unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'map_audit_v18_5'))
from display_tools import ui
from native_ftext import read_base

ROOT = Path(os.environ.get('CI_RU_CHECK_ROOT', '/workspace/project-context/carnal-instinct/v18.5'))

class NativeItemRegression(unittest.TestCase):
    def test_essence_namespace_is_a_valid_complete_fstring(self):
        path = next((ROOT / 'FinalExtracted/Steam_current').rglob('Essence_Tier_1_Small.uasset'))
        p = ui.zen.package(path)
        export = next(e for e in p['exports'] if e['name'] == 'Default__Essence_Tier_1_Small_C')
        raw = p['bytes'][export['start']:export['end']]
        record = read_base(raw, 10)
        self.assertEqual(record.namespace, 'CI_RU_Display_V18_4_Items')
        self.assertEqual(record.source, 'Weak Essence Fragment')
        self.assertEqual(record.key, '7161373344630149D4AE198A780FAC9B')

if __name__ == '__main__':
    unittest.main()
