"""Read real cooked UI: sizing, visible modern sections and retained handlers."""
import os, unittest
from pathlib import Path
from inspect_native import ui, props

ROOT = Path(os.environ.get('CI_RU_CHECK_ROOT', '/workspace/project-context/carnal-instinct/v18.6'))
ED = ROOT / 'FinalExtracted/Steam_current'

def package(name):
    paths = list(ED.rglob(name + '.uasset'))
    assert len(paths) == 1, name
    return ui.zen.package(paths[0])

def widget(p, name):
    e = next(x for x in p['exports'] if x['name'] == name)
    return e, props(p, e)

class SteamLayout(unittest.TestCase):
    def test_character_widths_are_enabled(self):
        p = package('WB_CharacterScreen')
        for name, width in [('SizeBox_161', 600), ('StatsSize', 1198)]:
            _, v = widget(p, name)
            self.assertEqual(v.get('bOverride_WidthOverride', {}).get('value', 0), 1, name)
            self.assertEqual(v['WidthOverride']['value'], width)

    def test_character_canvas_scales_as_fixed_1920_by_1080(self):
        p = package('WB_CharacterScreen')
        self.assertTrue(any((v.get('WidthOverride', {}).get('value'), v.get('HeightOverride', {}).get('value')) == (1920,1080)
                            for e in p['exports'] if ui.CLASS.get(e['cls']) == 'SizeBox' for v in [props(p,e)]))

    def test_modern_character_sections_visible(self):
        p = package('WB_Stats_Main')
        for name in ['SizeBox_7', 'SizeBox_10', 'Level', 'LevelXP', 'CarnalInstinct', 'CarnalInstinctXP']:
            _, v = widget(p,name)
            self.assertNotIn(v.get('Visibility', {}).get('value', 0), [1,2], name)
        p = package('WB_Stats_Full')
        self.assertEqual(widget(p,'SizeBox_38')[1]['Visibility']['value'], 3)
        for name in ['Column1','Column2']:
            self.assertEqual(widget(p,name)[1]['bOverride_WidthOverride']['value'],1)

    def test_crafting_visible_immediately_after_lore(self):
        p = package('WB_WindowSwitcher')
        e,v=widget(p,'Button_crafting')
        self.assertEqual(v.get('Visibility',{}).get('value',0),0)
        _,row=widget(p,'HorizontalBox')
        def contains(ref,name):
            x=p['exports'][ref-1]
            if x['name']==name:return True
            if x['cls'] not in ui.CLASS:return False
            q=props(p,x)
            return any(contains(props(p,p['exports'][s-1])['Content']['value'],name) for s in q.get('Slots',{}).get('value',[]))
        order=row['Slots']['value']
        lore=next(i for i,s in enumerate(order) if contains(props(p,p['exports'][s-1])['Content']['value'],'Button_Lore'))
        craft=next(i for i,s in enumerate(order) if contains(props(p,p['exports'][s-1])['Content']['value'],'Button_crafting'))
        self.assertEqual(craft,lore+1)

    def test_journal_objectives_above_description_with_full_width(self):
        p=package('WB_QuestScreen')
        e,v=widget(p,'HorizontalBox_2')
        self.assertEqual(ui.CLASS[e['cls']],'VerticalBox')
        contents=[props(p,p['exports'][i-1])['Content']['value'] for i in v['Slots']['value']]
        self.assertEqual([p['exports'][i-1]['name'] for i in contents],['SizeBox_0','QuestObjectives_1'])
        self.assertEqual(widget(p,'SizeBox_0')[1]['bOverride_WidthOverride']['value'],0)

    def test_journal_body_has_white_condensed_font_and_wrapping(self):
        for name in ['WB_QuestObjectiveName','WB_QuestObjectiveDescription']:
            p=package(name);_,v=widget(p,'Text_ObjectiveName')
            font=v['Font']['value']
            self.assertEqual(font['TypefaceFontName']['value'],'FF_BarlowCondensed-Regular')
            self.assertEqual(list(v['ColorAndOpacity']['value']['SpecifiedColor']['value']),[1,1,1,1])
            self.assertEqual(v['AutoWrapText']['value'],1)

if __name__=='__main__':unittest.main()
