"""Read actual cooked UI: normal headings, compact journal and bounded tracking."""
import os,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'ui_parity_v18_7'))
from inspect_native import ui,props
from native_edit import plain
from display_tools import FUNCTION

ROOT=Path(os.environ['CI_RU_CHECK_ROOT'])
BASE=Path(os.environ.get('CI_RU_BASE_ROOT','/workspace/project-context/carnal-instinct/v18.8'))
NAMES=['WB_T3_SubHeadline','WB_QuestScreen','WB_QuestObjectiveName','WB_QuestObjectiveDescription','WB_QuestName']
def package(name,root=ROOT):return ui.zen.package(next((root/'FinalExtracted/Steam_current').rglob(name+'.uasset')))
def values(p,name):return plain(props(p,next(e for e in p['exports'] if e['name']==name)))

class SteamFontTracking(unittest.TestCase):
    def test_settings_heading_restores_source_font_size(self):
        v=values(package('WB_T3_SubHeadline'),'T_SubHeadline')
        self.assertEqual(v['Font']['Size'],16)
        self.assertEqual(v.get('Justification',0),0)
        self.assertEqual(v['AutoWrapText'],1)

    def test_journal_body_and_objective_headers_compact(self):
        for name in ['WB_QuestObjectiveName','WB_QuestObjectiveDescription']:
            v=values(package(name),'Text_ObjectiveName')
            self.assertLessEqual(v['Font']['Size'],16,name)
            self.assertEqual(v['AutoWrapText'],1)
        p=package('WB_QuestScreen')
        for name in ['ObjectivesText','ObjectivesText_1']:
            self.assertLessEqual(values(p,name)['Font']['Size'],18,name)

    def test_tracking_icon_size_and_margin_do_not_extend_past_card(self):
        p=package('WB_QuestName');v=values(p,'Checkbox_Tracked')
        for name in ['UncheckedImage','UncheckedHoveredImage','UncheckedPressedImage','CheckedImage','CheckedHoveredImage','CheckedPressedImage']:
            self.assertEqual(v['WidgetStyle'][name]['ImageSize'],[28.,28.],name)
        self.assertEqual(v['RenderTransform']['Scale'],[1.,1.])
        self.assertGreaterEqual(values(p,'OverlaySlot_4')['Padding']['Right'],10)
        padding=values(p,'SizeBoxSlot_0')['Padding']
        host=values(package('WB_QuestScreen'),'SizeBox_249')['WidthOverride']
        self.assertLessEqual(values(p,'SizeBox_27')['WidthOverride']+padding['Left']+padding['Right'],host)

    def test_all_gameplay_functions_class_and_cdo_unchanged(self):
        for name in NAMES:
            p,old=package(name),package(name,BASE)
            for e in old['exports']:
                if e['cls']==FUNCTION or e['name'] in [name+'_C','Default__'+name+'_C']:
                    x=p['exports'][e['index']]
                    self.assertEqual(p['bytes'][x['start']:x['end']],old['bytes'][e['start']:e['end']],(name,e['name']))

if __name__=='__main__':unittest.main()
