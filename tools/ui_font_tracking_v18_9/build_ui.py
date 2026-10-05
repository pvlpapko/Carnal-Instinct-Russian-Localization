"""Native-only Steam heading, journal text and tracking geometry correction."""
from pathlib import Path
import copy,json,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'ui_parity_v18_7'))
from native_edit import Edit,plain

ROOT,BASE=map(Path,sys.argv[1:3]);report={'release':'18.9','runtime_tested':False,'assets':[]}
def edit(name):return Edit(next((BASE/'FinalExtracted/Steam_current').rglob(name+'.uasset')))
def font(e,name,size):
    value=plain(e.values(name))['Font'];value['Size']=float(size);value['LetterSpacing']=0
    e.set(name,'Font',value)
def finish(e,name):
    mount='Carnal_Instinct_UE5/Content/'+e.p['name'].removeprefix('/Game/')+'.uasset'
    item=e.finish(ROOT/'Developer/V18_9/patched/Steam_current'/mount)
    item.update(name=name,edition='Steam_current',mount=mount);report['assets'].append(item)

# Restore the source heading size for every settings category using this class.
e=edit('WB_T3_SubHeadline');font(e,'T_SubHeadline',16)
e.set('T_SubHeadline','Justification',0);finish(e,'WB_T3_SubHeadline')

e=edit('WB_QuestScreen')
for name in ['ObjectivesText','ObjectivesText_1']:font(e,name,18)
finish(e,'WB_QuestScreen')
for name in ['WB_QuestObjectiveName','WB_QuestObjectiveDescription']:
    e=edit(name);font(e,'Text_ObjectiveName',16)
    if name=='WB_QuestObjectiveName':
        e.set('SizeBox_63','WidthOverride',24.);e.set('SizeBox_63','HeightOverride',24.)
    finish(e,name)

e=edit('WB_QuestName');value=plain(e.values('Checkbox_Tracked'))
style=value['WidgetStyle'];checked=style['CheckedImage']
for name in ['UncheckedImage','UncheckedHoveredImage','UncheckedPressedImage','CheckedImage','CheckedHoveredImage','CheckedPressedImage']:
    brush=style.setdefault(name,copy.deepcopy(checked) if name.startswith('Checked') else {'DrawAs':0})
    brush['ImageSize']=[28.,28.]
e.set('Checkbox_Tracked','WidgetStyle',style)
transform=value['RenderTransform'];transform['Scale']=[1.,1.]
e.set('Checkbox_Tracked','RenderTransform',transform)
# Keep the tracking overlay inside the row; the source negative margin clipped it.
padding=plain(e.values('OverlaySlot_4'))['Padding'];padding['Right']=10.
e.set('OverlaySlot_4','Padding',padding)
padding=plain(e.values('SizeBoxSlot_0'))['Padding'];padding['Right']=10.
e.set('SizeBoxSlot_0','Padding',padding)
# 530 + two 10px margins = the journal's 550px list; source width was 550 + padding.
e.set('SizeBox_27','WidthOverride',530.)
finish(e,'WB_QuestName')

(ROOT/'Reports/V18_9_UI.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'changed_packages':len(report['assets']),'gameplay_code_changes':0}))
