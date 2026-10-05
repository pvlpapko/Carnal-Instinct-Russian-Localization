"""Activate Steam's modern UMG layout, retaining edition-specific gameplay code."""
import copy,json,struct,sys
from pathlib import Path
from native_edit import Edit,plain
from inspect_native import ui,cf,k,expr_name,find_script,props,is_widget
from display_tools import FUNCTION,replace_function,verify_script,sha

ROOT,BASE=map(Path,sys.argv[1:3]);ED='Steam_current';MOUNT='Carnal_Instinct_UE5/Content/'
report={'release':'18.7 TEST','runtime_tested':False,'assets':[]}

def path_for(name,edition=ED):
    a=list((BASE/'FinalExtracted'/edition).rglob(name+'.uasset'))
    if not a:a=list((ROOT/'Developer/V18_7/inputs'/edition).rglob(name+'.uasset'))
    assert len(a)==1,(name,edition,a);return a[0]

def patch(name):return Edit(path_for(name))

def copy_visual(editor,name,fields=('Font','ColorAndOpacity','Brush','BrushColor','BackgroundColor','ContentColorAndOpacity','WidgetStyle')):
    """Only named native appearance fields; resource refs remap by package/public hash."""
    ref=ui.zen.package(path_for(name,'NoSteam_0.7.9.16232'))
    def remap(v,f):
        if f['type']=='ObjectProperty':return editor.import_resource(ref,v) if v<0 else v
        if f['type']=='StructProperty' and f['struct'] not in ui.NATIVE:
            fs={x['name']:x for x in ui.fields(f['struct'])};return {key:remap(x,fs[key]) for key,x in v.items()}
        if f['type']=='ArrayProperty':return [remap(x,f['inner']) for x in v]
        return v
    for source in ref['exports']:
        if not is_widget(source):continue
        matches=[e for e in editor.exports if e['name']==source['name'] and e['cls']==source['cls']]
        if len(matches)!=1:continue
        e=matches[0];v=props(ref,source);fs={f['name']:f for f in ui.fields('/Script/UMG.'+ui.CLASS[e['cls']])}
        for field in fields:
            if field in v:editor.set(e,field,remap(plain(v[field]),fs[field]))
        if ui.CLASS[e['cls']]=='TextBlock' and 'ColorAndOpacity' not in v:
            editor.set(e,'ColorAndOpacity',{'SpecifiedColor':[1.,1.,1.,1.]})

def fixed_canvas(editor):editor.fixed_canvas()

def border_panel(editor,size_name):
    size=editor.export(size_name);s=editor.exports[plain(editor.values(size))['Slots'][0]-1]
    child=plain(editor.values(s))['Content'];tree=editor.export('WidgetTree')['index']
    # Reuse the child slot index so existing bound UserWidget instances stay intact.
    oldcls=ui.CLASS[s['cls']];v=plain(editor.values(s))
    padding=15. if size_name=='StatsSize' else 20.
    b=editor.add('CI_RU_'+size_name+'_Background','Border',tree,{'BrushColor':[0.,0.,0.,0.55],
            'Padding':{'Left':padding,'Top':0.,'Right':padding,'Bottom':0.},'Slots':[s['index']+1]})
    newslot=editor.add('CI_RU_'+size_name+'_Slot','SizeBoxSlot',size['index'],{'Parent':size['index']+1,'Content':b,
                'HorizontalAlignment':0,'VerticalAlignment':0})
    editor.set(size,'Slots',[newslot]);editor.set(editor.exports[b-1],'Slot',newslot)
    s['cls']=next(i for i,n in ui.CLASS.items() if n=='BorderSlot')
    s['template']=(cf.CityHash64('/script/umg/default__borderslot'.encode('utf-16-le'))&((1<<62)-1))|(1<<62)
    s['outer']=b-1
    editor.data[s['index']]=editor.object({'Parent':b,'Content':child,'HorizontalAlignment':0,'VerticalAlignment':0,
                            'Padding':{'Left':padding,'Top':0.,'Right':padding,'Bottom':0.}},'/Script/UMG.BorderSlot')+b'\0'*4
    editor.changed.add(s['index']);editor.values(s)

def finish(editor,name):
    mount=MOUNT+editor.p['name'].removeprefix('/Game/')+'.uasset'
    target=ROOT/'Developer/V18_7/patched'/ED/mount
    item=editor.finish(target);item.update(name=name,edition=ED,mount=mount)
    q=ui.zen.package(target);count=0
    for e in q['exports']:
        if e['cls']==FUNCTION:verify_script(q['bytes'][e['start']:e['end']]);count+=1
    item['strict_functions']=count;report['assets'].append(item)

# Character: a fixed design viewport inside ScaleBox, as in the NoSteam reference.
e=patch('WB_CharacterScreen');fixed_canvas(e)
for n in ['SizeBox_161','StatsSize']:e.set(n,'bOverride_WidthOverride',1)
e.set('HorizontalBoxSlot_3','Padding',{'Left':0.,'Top':0.,'Right':0.,'Bottom':0.})
e.set('HorizontalBoxSlot_8','Padding',{'Left':20.,'Top':0.,'Right':0.,'Bottom':0.})
e.set('HorizontalBoxSlot_8','Size',{'Value':1.,'SizeRule':0})
inner=next(s for s in e.exports if ui.CLASS.get(s['cls'])=='CanvasPanelSlot' and plain(e.values(s)).get('Content')==e.export('HorizontalBox_83')['index']+1)
layout=plain(e.values(inner))['LayoutData'];layout['Offsets'].update(Left=50.,Right=50.)
e.set(inner,'LayoutData',layout)
# Two black panel backgrounds keep the source instances and stat callbacks bound.
border_panel(e,'SizeBox_161');border_panel(e,'StatsSize');finish(e,'WB_CharacterScreen')

# Source Steam already contains both old gold controls and the modern controls.
e=patch('WB_Stats_Main');copy_visual(e,'WB_Stats_Main')
for n in ['SizeBox_7','SizeBox_10']:e.set(n,'Visibility',3)
for n in ['Level','LevelXP','CarnalInstinct','CarnalInstinctXP']:e.set(n,'Visibility',0)
for n in ['WB_T3_SubHeadline_1','WB_T3_SubHeadline_321','WB_LevelExpBar','WB_LevelExpBar_Carnal']:e.custom_visibility(n,1)
e.set('SizeBox_0','Visibility',1)
e.set('BG_Border','Visibility',1)
e.set('Text_Attributes_1','Visibility',1)
e.set('Text_Attributes','MinDesiredWidth',64.)
# Move the existing attribute points into the modern header; retain its slot index.
attrs=e.export('Box_Attributes');s=e.exports[plain(e.values(attrs))['Slot']-1]
oldparent=e.exports[plain(e.values(s))['Parent']-1];newparent=e.export('Overlay_1')
e.set(oldparent,'Slots',[x for x in plain(e.values(oldparent))['Slots'] if x!=s['index']+1])
e.set(newparent,'Slots',plain(e.values(newparent))['Slots']+[s['index']+1])
e.set(s,'Parent',newparent['index']+1);e.set(s,'Padding',{'Left':0.,'Top':0.,'Right':20.,'Bottom':0.});s['outer']=newparent['index']
# Redirect only the form caption's SetText to the existing, declared Text_Form field.
function=e.export('ExecuteUbergraph_WB_Stats_Main');nodes=find_script(e.data[function['index']])[3];changes=0
for node in nodes:
    for x in k.walk(node):
        if x.op==0x19 and x.context and expr_name(x.context,e.names)=='SetText' and x.object.op==0x19:
            assert expr_name(x.object.object,e.names)=='WB_T3_SubHeadline' and expr_name(x.object.context,e.names)=='T_SubHeadline'
            old=x.object.object
            owner=e.export('WB_Stats_Main_C')['index']+1
            raw=struct.pack('<IIIi',1,e.name('Text_Form'),0,owner)
            x.object=k.Expr(0x01,[k.Raw(raw,8)],old=old.old,old_end=old.old_end);changes+=1
assert changes==1
replacements,proof=replace_function(e.p,function,nodes)
e.data.update(replacements);e.changed.update(replacements);e.evidence.append({'form_caption_route':'Text_Form','script_rebase':proof})
finish(e,'WB_Stats_Main')

e=patch('WB_Stats_Full');copy_visual(e,'WB_Stats_Full')
e.set('SizeBox_38','Visibility',3)
for n in ['Column1','Column2']:e.set(n,'bOverride_WidthOverride',1)
e.custom_visibility('WB_T3_SubHeadline',1);finish(e,'WB_Stats_Full')
e=patch('WB_Stats_Main_Slot');copy_visual(e,'WB_Stats_Main_Slot');finish(e,'WB_Stats_Main_Slot')

e=patch('WB_WindowSwitcher');e.set('Button_crafting','Visibility',0)
# bIsEnabled and all click/hover/progression handlers retain their source bytes.
finish(e,'WB_WindowSwitcher')
e=patch('WB_UpperUIBar');finish(e,'WB_UpperUIBar')

e=patch('WB_QuestScreen');fixed_canvas(e)
row=e.export('HorizontalBox_2');slots=plain(e.values(row))['Slots'];e.class_to('HorizontalBox_2','VerticalBox')
for i in slots:
    s=e.exports[i-1];e.class_to(s['name'],'VerticalBoxSlot') if sum(x['name']==s['name'] for x in e.exports)==1 else None
    # Slot names repeat under different outer panels: select by index.
    if ui.CLASS[s['cls']]=='HorizontalBoxSlot':
        s['cls']=next(i for i,n in ui.CLASS.items() if n=='VerticalBoxSlot')
        s['template']=(cf.CityHash64('/script/umg/default__verticalboxslot'.encode('utf-16-le'))&((1<<62)-1))|(1<<62)
        e.changed.add(s['index']);e.values(s)
    e.set(s,'Padding',{'Left':0.,'Top':0.,'Right':0.,'Bottom':20.})
    e.set(s,'Size',{'Value':0.4 if i==slots[0] else 0.6,'SizeRule':1})
e.set('SizeBox_0','bOverride_WidthOverride',0);e.set('SizeBox_0','bOverride_MinDesiredWidth',0)
for n in ['ObjectivesText','ObjectivesText_1']:
    font=plain(e.values(n))['Font'];font['Size']=22.;font['LetterSpacing']=0
    e.set(n,'Font',font)
    e.set(n,'AutoWrapText',1)
# Existing modern grouped list stays in use. Only its redundant old headings disappear.
for n in ['WB_T3_SubHeadline','WB_T3_OptionSwitcher']:e.custom_visibility(n,1)
e.set('HorizontalBox_1','Visibility',1)  # Source right-click tracking route remains available.
finish(e,'WB_QuestScreen')
e=patch('WB_QuestType');finish(e,'WB_QuestType')
for name in ['WB_QuestName','WB_QuestObjectiveName','WB_QuestObjectiveDescription']:
    e=patch(name);copy_visual(e,name);finish(e,name)

# The selected quest heading uses this source class. Modernize native appearance;
# preserve its Text, T_SubHeadline member, casing and update handlers.
e=patch('WB_T3_SubHeadline')
font_source=ui.zen.package(path_for('WB_Stats_Main'))
font_export=next(x for x in font_source['exports'] if x['name']=='TextBlock_66')
font=plain(props(font_source,font_export))['Font'];font['FontObject']=e.import_resource(font_source,font['FontObject'])
font['Size']=32.;font['LetterSpacing']=0
e.set('T_SubHeadline','Font',font)
e.set('T_SubHeadline','AutoWrapText',1);e.set('T_SubHeadline','Justification',1)
for n in ['Image_180','Image_337']:e.set(n,'Visibility',1)
finish(e,'WB_T3_SubHeadline')

(ROOT/'Reports/V18_7_UI_PARITY.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'assets':len(report['assets']),'strict_functions':sum(x['strict_functions'] for x in report['assets']),
                  'changed_packages':[x['name'] for x in report['assets']]},ensure_ascii=False))
