"""Actual cooked journal header: centered, underlined, source handlers retained."""
import os,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'ui_parity_v18_7'))
from inspect_native import ui,props
from native_edit import plain
from display_tools import FUNCTION

ROOT=Path(os.environ['CI_RU_CHECK_ROOT'])
BASE=Path(os.environ.get('CI_RU_BASE_ROOT','/workspace/project-context/carnal-instinct/v18.7'))
def package(root):return ui.zen.package(next((root/'FinalExtracted/Steam_current').rglob('WB_QuestScreen.uasset')))

class JournalTitle(unittest.TestCase):
    def test_selected_title_centered_and_underlined(self):
        p=package(ROOT)
        title=next(e for e in p['exports'] if e['name']=='WB_T3_SubHeadline_746')
        slot=next(e for e in p['exports'] if ui.CLASS.get(e['cls'])=='VerticalBoxSlot' and plain(props(p,e)).get('Content')==title['index']+1)
        self.assertEqual(plain(props(p,slot)).get('HorizontalAlignment'),2)
        self.assertTrue(any(e['name']=='CI_RU_QuestTitleUnderline' for e in p['exports']))

    def test_journal_functions_and_gameplay_class_cdo_unchanged(self):
        p,old=package(ROOT),package(BASE)
        for e in old['exports']:
            if e['cls']==FUNCTION or e['name'] in ['WB_QuestScreen_C','Default__WB_QuestScreen_C']:
                x=p['exports'][e['index']]
                self.assertEqual(p['bytes'][x['start']:x['end']],old['bytes'][e['start']:e['end']],e['name'])

if __name__=='__main__':unittest.main()
