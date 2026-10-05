"""Reported runtime omissions must resolve in both rows and every icon path."""
from pathlib import Path
import os, sys, unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'map_audit_v18_5'))
from display_tools import cf, ui, k, find_script, expr_name
import zlib

ROOT = Path(os.environ.get('CI_RU_CHECK_ROOT', '/workspace/project-context/carnal-instinct/v18.5'))

class MapCaptionRegression(unittest.TestCase):
    def test_every_known_caption_resolves_to_a_shipped_localization(self):
        for edition in ('Steam_current', 'NoSteam_0.7.9.16232'):
            loc = cf.Locres(ROOT / 'Data' / edition / 'Game.locres')
            entries = {(e['namespace'], e['key'], e['source_hash']): e for e in loc.entries}
            for name in ('WB_WorldMapPopup.uasset', 'w_03_map_icon.uasset'):
                p = ui.zen.package(next((ROOT / 'FinalExtracted' / edition).rglob(name)))
                e = next(e for e in p['exports'] if e['name'].startswith('ExecuteUbergraph'))
                nodes = find_script(p['bytes'][e['start']:e['end']])[3]
                switches = [s for n in nodes for s in k.walk(n) if s.op == 0x69 and len(s.cases) > 100]
                self.assertTrue(all(len(s.cases) >= 899 for s in switches))
                for s in switches:
                    for key, text in s.cases:
                        label = expr_name(key, p['names'])
                        def string(expr):
                            return expr.parts[0].data[:-1].decode('ascii') if expr.op == 0x1f else expr.parts[0].data[:-2].decode('utf-16-le')
                        source, key, namespace = map(string, text.parts[1:])
                        entry = entries.get((namespace, key, zlib.crc32(source.encode('utf-32-le')) & 0xffffffff))
                        self.assertTrue(entry and entry['value'], f'{edition} {name} untranslated caption {label}')

    def test_reported_captions_in_all_display_paths(self):
        for edition in ('Steam_current', 'NoSteam_0.7.9.16232'):
            loc = cf.Locres(ROOT / 'Data' / edition / 'Game.locres')
            entries = {(e['namespace'], e['key'], e['source_hash']): e['value'] for e in loc.entries}
            for name, count in [('WB_WorldMapPopup.uasset', 2), ('w_03_map_icon.uasset', 5)]:
                p = ui.zen.package(next((ROOT / 'FinalExtracted' / edition).rglob(name)))
                e = next(e for e in p['exports'] if e['name'].startswith('ExecuteUbergraph'))
                nodes = find_script(p['bytes'][e['start']:e['end']])[3]
                switches = [s for n in nodes for s in k.walk(n) if s.op == 0x69 and len(s.cases) > 100]
                self.assertEqual(len(switches), count)
                for switch in switches:
                    captions = {expr_name(key, p['names']).casefold(): value for key, value in switch.cases}
                    for label, russian in [('RAQOTE', 'Ракоте'), ('THE BREADBASKET', 'Житница'), ('ANUBITE CAMP', 'Лагерь анубитов')]:
                        with self.subTest(edition=edition, asset=name, switch=switch.old, caption=label):
                            self.assertTrue(label.casefold() in captions, 'missing displayed caption: ' + label)
                            self.assertEqual(captions[label.casefold()].op, 0x29)
                            text = captions[label.casefold()]
                            def string(expr):
                                return expr.parts[0].data[:-1].decode('ascii') if expr.op == 0x1f else expr.parts[0].data[:-2].decode('utf-16-le')
                            source, key, namespace = map(string, text.parts[1:])
                            self.assertEqual(entries.get((namespace, key, zlib.crc32(source.encode('utf-32-le')) & 0xffffffff)), russian)

if __name__ == '__main__':
    unittest.main()
