"""Reproduce Steam v18.3 objective display-boundary payload from v18.2 workspace.
Requires current Steam source assets downloaded as basename.uasset.bin and v18.2 workspace.
"""
from pathlib import Path
import sys, json, struct, shutil, importlib.util, types
ROOT=Path('/mnt/data')
BASE=ROOT/'v18_2_work'
OUT=ROOT/'v18_3_repro'
if OUT.exists(): shutil.rmtree(OUT)
OUT.mkdir()
spec=importlib.util.spec_from_file_location('cityhash_pure',BASE/'Developer/SafeUIFix/tools/cityhash_pure.py')
ch=importlib.util.module_from_spec(spec); spec.loader.exec_module(ch)
shim=types.ModuleType('cityhash'); shim.CityHash64=ch.CityHash64; sys.modules['cityhash']=shim
sys.path.insert(0,str(BASE/'Developer/SafeUIFix/tools')); import ci_formats as cf
sys.path.insert(0,str(BASE/'Developer/MapFix')); import zen
Q3='Carnal_Instinct_UE5/Content/DLG_Tree/dqst_system/common/quest_objectives.uasset'
OBJ_NAME='Carnal_Instinct_UE5/Content/RPG_InventorySystem/UI/Quests/WB_QuestObjectiveName.uasset'
OBJ_DESC='Carnal_Instinct_UE5/Content/RPG_InventorySystem/UI/Quests/WB_QuestObjectiveDescription.uasset'
bt=cf.Toc(BASE/'Files/Steam_current/pakchunk1015-Windows_P.utoc',BASE/'Files/Steam_current/pakchunk1015-Windows_P.ucas')
files={m:bt.read_chunk(i) for m,i in bt.files}; assert len(files)==23
rep=json.load(open(BASE/'Reports/V15_QUEST_DISPLAY_PATCH.json',encoding='utf-8'))
full=next(x for x in rep['assets'] if x['mount']==Q3)
ev=[x for x in full['evidence'] if x['row'].startswith('q_HellKitchen')]; assert len(ev)==12
p=zen.package(ROOT/'quest_objectives.uasset.bin'); ex=p['exports'][0]; raw=bytearray(p['bytes'][ex['start']:ex['end']]); names=p['names']
new=[]
for x in ev:
 if x['russian'] not in names and x['russian'] not in new:new.append(x['russian'])
idx={n:len(names)+i for i,n in enumerate(new)}
for x in ev:
 old,num=struct.unpack_from('<II',raw,x['offset']); assert num==0 and names[old]==x['english']
 struct.pack_into('<II',raw,x['offset'], names.index(x['russian']) if x['russian'] in names else idx[x['russian']],0)
q3=zen.rebuild(p,{0:bytes(raw)},new_names=new); qp=OUT/'quest_objectives_HellKitchen_only.uasset'; qp.write_bytes(q3)
assert zen.package(qp)['header'][1]==60905 and zen.package(qp)['header'][1]<65536
name=BASE/'Developer/QuestFix/WB_QuestObjectiveName.uasset'; desc=BASE/'Developer/QuestFix/WB_QuestObjectiveDescription.uasset'
for src,pat in [(ROOT/'WB_QuestObjectiveName.uasset.bin',name),(ROOT/'WB_QuestObjectiveDescription.uasset.bin',desc)]:
 a=cf.zen_info(src.read_bytes()); b=cf.zen_info(pat.read_bytes()); assert a['package']==b['package'] and a['imports']==b['imports']
files[OBJ_NAME]=name.read_bytes(); files[OBJ_DESC]=desc.read_bytes(); files[Q3]=q3; assert len(files)==26
manifest={'base_packages':23,'final_packages':26,'added':[OBJ_NAME,OBJ_DESC,Q3],'q3_refs':12,'q3_header':60905,
          'full_crashing_q3_refs':531,'full_crashing_q3_header':124533,
          'name_source_sha256':'5d0eaba6b987539d923cb58004ca98581002ca2b2dde72fd3ab366c62206510f',
          'desc_source_sha256':'9e14810d7bb9857e4d6ee7eb2147fea72f16715daaf4181b9cf5405043ec6476'}
(OUT/'V18_3_REPRO_INPUTS.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(manifest,ensure_ascii=False,indent=2))
