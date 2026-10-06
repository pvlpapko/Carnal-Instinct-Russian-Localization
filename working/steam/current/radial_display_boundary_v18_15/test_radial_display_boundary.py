from pathlib import Path
import csv, hashlib, json, struct, sys, tempfile
ROOT=Path(sys.argv[1]); BASE=Path(sys.argv[2])
sys.path.insert(0,str(ROOT/'Developer/SafeUIFix/tools'))
import ci_formats as cf
sys.path.insert(0,str(ROOT/'tools/map_audit_v18_5'))
import display_tools as d
T='Carnal_Instinct_UE5/Content/BlueprintSystems/DynamicRadialMenu/Widgets/W_MenuItem.uasset'
ALIASES=[
 ('Canopic Capture','5EC37C4D8083528EEA2DA50B6E342D44',1009922021,'Захват канопой'),
 ('Fishing','79CEA8FF2BA190BBB1BDB045610C272C',2680376353,'Рыбалка'),
 ("Korvoth's Sceptre",'252B52243AB3DA58F770F48C2CAD76C9',406990083,'Скипетр Корвота'),
 ('Masturbate','84CA42CB806912F44A5FD87EA66D79E6',2284028336,'Мастурбировать'),
 ('Summon Aadi','8F9100DF142AD9B12A2DD786B3C1521A',1824976582,'Призвать Аади'),
 ('Torch','DCC578ACD71A7BF2C0E96DE641CC4656',1261106821,'Факел'),
 ('Shade Sight','D9F46D7344B1F6CCD7C81D89A0B3CCFE',2468818620,'Зрение тени')]
tech_keys={
 'Canopic Capture':'2658420B4FD907B4111E3493B20DE1D4','Fishing':'73D7C99F4BFC15F37038A78A260A26D8',
 "Korvoth's Sceptre":'61A1BF914358BC1944053EAC831C41BB','Masturbate':'FFD8476A472BA585601FF8B43AD324B0',
 'Summon Aadi':'86304DA1490FFECCD302FE9B9B15D119','Torch':'D7A77ABE4ABEE67D22AE9FA9D8D06220','Shade Sight':'4ACBBA2B411E9ED180EAE98189BA072D'}
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ftext_tuple(x):
 assert x.op==0x29 and x.parts[0].data==b'\x01'
 vals=[]
 for s in x.parts[1:4]:
  raw=s.parts[0].data; vals.append(raw[:-1].decode('ascii') if s.op==0x1f else raw[:-2].decode('utf-16-le'))
 return tuple(vals)
report={'release':'18.15','runtime_tested':False,'tests':{},'editions':{}}
for ed in ['Steam_current','NoSteam_0.7.9.16232']:
 old=cf.Toc(BASE/'Files'/ed/'pakchunk1015-Windows_P.utoc'); new=cf.Toc(ROOT/'Files'/ed/'pakchunk1015-Windows_P.utoc')
 oi=dict(old.files)[T]; ni=dict(new.files)[T]
 old_chunk=old.read_chunk(oi); new_chunk=new.read_chunk(ni)
 with tempfile.TemporaryDirectory() as td:
  a=Path(td)/'old.uasset'; b=Path(td)/'new.uasset'; a.write_bytes(old_chunk); b.write_bytes(new_chunk)
  p=d.ui.zen.package(a); q=d.ui.zen.package(b)
  assert len(p['exports'])==len(q['exports'])==64
  set_idx=next(e['index'] for e in p['exports'] if e['name']=='SetItemText')
  for pe,qe in zip(p['exports'],q['exports']):
   assert all(pe[k]==qe[k] for k in ['name','cls','outer','super','template','flags'])
   if pe['index']!=set_idx:
    assert p['bytes'][pe['start']:pe['end']]==q['bytes'][qe['start']:qe['end']],(ed,pe['name'])
  se=q['exports'][set_idx]
  _,mem,disk,nodes,_=d.find_script(q['bytes'][se['start']:se['end']])
  switches=[x for n in nodes for x in d.k.walk(n) if x.op==0x69]
  assert len(switches)==1
  sw=switches[0]; assert len(sw.cases)==7
  got=[]
  for ck,cv in sw.cases:
   idx=struct.unpack_from('<I',ck.parts[0].data)[0]&0x3fffffff
   got.append((q['names'][idx],)+ftext_tuple(cv))
  exp=[(src,src,key,'CI_RU_Display_RadialAudit') for src,key,_,_ in ALIASES]
  assert got==exp,(ed,got)
  assert sw.default.op==0x42 and d.pointer_name(sw.default.parts[0],q['names']).startswith('DisplayName_')
  if ed.startswith('NoSteam'):
   assert q['names'][len(p['names']):]==[x[0] for x in ALIASES]
  else:
   assert q['names']==p['names']
 loc=cf.Locres(ROOT/'Data'/ed/'Game.locres')
 ix={(e['namespace'],e['key'],e['source_hash']):e for e in loc.entries}
 alias_values={}
 for src,key,sh,ru in ALIASES:
  assert ix[('CI_RU_Display_RadialAudit',key,sh)]['value']==ru
  alias_values[src]=ru
 rows=list(csv.DictReader((ROOT/'Data'/ed/'translation.tsv').open(encoding='utf-8-sig',newline=''),delimiter='\t'))
 bykey={(r['Namespace'],r['Key'],int(r['SourceStringHash'])):r for r in rows}
 for src,_,sh,_ in ALIASES:
  r=bykey[('',tech_keys[src],sh)]
  assert r['English']==src and r['Russian']==src and 'technical runtime action ID' in r['SourceEvidence']
 assert (ROOT/'Data'/ed/'Game.locres').read_bytes()==(BASE/'Data'/ed/'Game.locres').read_bytes()
 assert (ROOT/'Files'/ed/'pakchunk1015-Windows_P.pak').read_bytes()==(BASE/'Files'/ed/'pakchunk1015-Windows_P.pak').read_bytes()
 report['editions'][ed]={'set_item_text_memory':mem,'set_item_text_disk':disk,'display_cases':alias_values,'technical_runtime_ids':'7/7 English','other_W_MenuItem_exports':'byte-identical','locres_vs_v18_14':'byte-identical','pak_vs_v18_14':'byte-identical','utoc_sha256':sha(ROOT/'Files'/ed/'pakchunk1015-Windows_P.utoc'),'ucas_sha256':sha(ROOT/'Files'/ed/'pakchunk1015-Windows_P.ucas'),'pak_sha256':sha(ROOT/'Files'/ed/'pakchunk1015-Windows_P.pak')}
installer=(ROOT/'Installer/CarnalInstinct_RU_Setup.exe').read_bytes()
trusted=json.loads((ROOT/'Developer/Installer_Source/trusted_hashes.json').read_text(encoding='utf-8'))
embedded={}
for ed in ['Steam_current','NoSteam_0.7.9.16232']:
 for ext in ['pak','utoc','ucas']:
  name=f'pakchunk1015-Windows_P.{ext}'; path=ROOT/'Files'/ed/name; data=path.read_bytes(); h=hashlib.sha256(data).hexdigest()
  assert h in trusted[name],(ed,name,h)
  assert installer.find(data)>=0,(ed,name,'not embedded')
  embedded[f'{ed}/{name}']=h
assert 'Русификатор 18.15'.encode('utf-8') in installer
report['tests']={'kismet_display_boundary':'PASS','technical_ids_english':'PASS','display_aliases_russian':'PASS','only_SetItemText_export_changed_inside_W_MenuItem':'PASS','locres_and_pak_unchanged_v18_14':'PASS','installer_payloads_embedded':'6/6 PASS','installer_trusted_hashes':'6/6 PASS','installer_version_string':'18.15 PASS'}
report['installer_sha256']=hashlib.sha256(installer).hexdigest(); report['embedded_payloads']=embedded
(ROOT/'Reports/V18_15_VALIDATION.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
