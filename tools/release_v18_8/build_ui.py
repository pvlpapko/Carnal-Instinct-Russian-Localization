"""Small native-only journal refinement over the user-tested 18.7 payload."""
from pathlib import Path
import json,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'ui_parity_v18_7'))
from native_edit import Edit,plain
from inspect_native import ui

ROOT,BASE=map(Path,sys.argv[1:3])
source=next((BASE/'FinalExtracted/Steam_current').rglob('WB_QuestScreen.uasset'))
e=Edit(source);tree=e.export('WidgetTree')['index'];panel=e.export('VerticalBox_1')
title=e.export('WB_T3_SubHeadline_746')
slot=next(s for s in e.exports if ui.CLASS.get(s['cls'])=='VerticalBoxSlot' and plain(e.values(s)).get('Content')==title['index']+1)
e.set(slot,'HorizontalAlignment',2)
box=e.add('CI_RU_QuestTitleUnderline','SizeBox',tree,{'HeightOverride':2.,'bOverride_HeightOverride':1})
line=e.add('CI_RU_QuestTitleLine','Border',tree,{'BrushColor':[0.7,0.7,0.7,0.65],
    'Brush':{'DrawAs':1,'TintColor':{'SpecifiedColor':[1.,1.,1.,1.]}}})
bs=e.add('CI_RU_QuestTitleLineSlot','SizeBoxSlot',box-1,{'Parent':box,'Content':line,'HorizontalAlignment':0,'VerticalAlignment':0})
vs=e.add('CI_RU_QuestTitleUnderlineSlot','VerticalBoxSlot',panel['index'],{'Parent':panel['index']+1,'Content':box,
    'HorizontalAlignment':0,'Padding':{'Left':0.,'Top':0.,'Right':0.,'Bottom':20.}})
e.set(e.exports[box-1],'Slots',[bs]);e.set(e.exports[box-1],'Slot',vs);e.set(e.exports[line-1],'Slot',bs)
slots=plain(e.values(panel))['Slots'];assert slots[0]==slot['index']+1
e.set(panel,'Slots',[slots[0],vs]+slots[1:])
mount='Carnal_Instinct_UE5/Content/'+e.p['name'].removeprefix('/Game/')+'.uasset'
out=ROOT/'Developer/V18_8/patched/Steam_current'/mount
item=e.finish(out);item.update(name='WB_QuestScreen',edition='Steam_current',mount=mount)
(ROOT/'Reports/V18_8_UI.json').write_text(json.dumps({'release':'18.8','assets':[item],'runtime_tested':False},ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'changed_packages':1,'changed_gameplay_functions':0,'new_native_exports':4}))
