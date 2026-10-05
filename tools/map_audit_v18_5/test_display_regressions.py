"""Regression evidence uses the cooked UI consumed by the game."""
from pathlib import Path
import os, struct, unittest
from display_tools import NativePatch, find_script, expr_name, k, ui

ROOT = Path(os.environ.get('CI_RU_CHECK_ROOT', '/workspace/project-context/carnal-instinct/v18.4'))
RADIAL = 'BlueprintSystems/DynamicRadialMenu/Widgets/W_MenuItem.uasset'


class DisplayRegressions(unittest.TestCase):
    def test_caption_below_icon_without_resizing_hit_region(self):
        p = NativePatch(next((ROOT / 'Extracted/NoSteam_0.7.9.16232').rglob('W_MenuItem.uasset')))
        _, text, _ = p.properties('TXT_Item')
        slot = p.package['exports'][text['Slot']['value'] - 1]
        _, props, _ = p.properties(slot)
        padding = props.get('Padding', {}).get('value', {})
        top = padding.get('Top', {}).get('value', 0)
        bottom = padding.get('Bottom', {}).get('value', 0)
        self.assertGreaterEqual(top, 110, 'caption must clear a 100px icon')
        self.assertEqual(top + bottom, 0, 'caption must not grow selection/layout height')
        self.assertEqual(props['VerticalAlignment']['value'], 1)
        self.assertTrue(text.get('AutoWrapText', {}).get('value'))
        _, area, _ = p.properties('SizeBox_0')
        self.assertEqual(area['WidthOverride']['value'], 100)
        self.assertEqual(area['HeightOverride']['value'], 100)

    def test_settings_open_does_not_reapply_saved_settings(self):
        path = next((ROOT / 'Extracted/NoSteam_0.7.9.16232').rglob('WB_T3_MainMenu.uasset'))
        p = ui.zen.package(path)
        e = next(e for e in p['exports'] if e['name'] == 'ExecuteUbergraph_WB_T3_MainMenu')
        _, _, _, nodes, _ = find_script(p['bytes'][e['start']:e['end']])
        calls = [x for node in nodes for x in k.walk(node) if expr_name(x, p['names']) == 'Activate']
        settings_calls = [x for x in calls if len(x.parts) == 4 and x.parts[1].op == 0x27]
        self.assertGreaterEqual(len(settings_calls), 2)
        self.assertTrue(all(x.parts[2].op == 0x28 for x in settings_calls), 'opening Settings must be view-only')

    def test_minimap_label_apostrophe_alias_is_present(self):
        path = next((ROOT / 'Extracted/NoSteam_0.7.9.16232').rglob('WB_WorldMapPopup.uasset'))
        p = ui.zen.package(path)
        e = next(e for e in p['exports'] if e['name'] == 'ExecuteUbergraph_WB_WorldMapPopup')
        _, _, _, nodes, _ = find_script(p['bytes'][e['start']:e['end']])
        switches = [x for node in nodes for x in k.walk(node) if x.op == 0x69 and len(x.cases) > 800]
        self.assertEqual(len(switches), 2)
        for switch in switches:
            aliases = {expr_name(key, p['names']): value for key, value in switch.cases}
            for label in ["Tal'Senet", 'Tal’Senet']:
                self.assertTrue(label in aliases, 'missing displayed label alias: ' + label)
                self.assertEqual(aliases[label].op, 0x29)


if __name__ == '__main__':
    unittest.main()
