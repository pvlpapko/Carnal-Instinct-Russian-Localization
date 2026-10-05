"""Overlay UI into verified 18.7; independently read every final package back."""
from pathlib import Path
import json,struct,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'ui_parity_v18_7'))
from inspect_native import ui,cf,props,is_widget
from native_edit import plain
from display_tools import sha,FUNCTION,verify_script,k

ROOT,BASE=map(Path,sys.argv[1:3])
changes=json.loads((ROOT/'Reports/V18_8_UI.json').read_text())['assets']
result={'release':'18.8','runtime_tested':False,'editions':{}}

def graph(p):
    es=p['exports'];n=len(es);b=p['bytes'];h=p['header']
    assert h[10]-h[9]==n*16 and h[11]-h[10]==n*20
    commands=[struct.unpack_from('<II',b,o) for o in range(h[9],h[10],8)]
    assert sorted(commands)==[(i,c) for i in range(n) for c in (0,1)]
    entries=struct.unpack('<'+'i'*((h[12]-h[11])//4),b[h[11]:h[12]])
    arcs={x:set() for x in commands}
    for i in range(n):arcs[(i,0)].add((i,1))
    ni=(h[8]-h[7])//8
    for i in range(n):
        first,*counts=struct.unpack_from('<i4I',b,h[10]+i*20)
        assert not sum(counts) or 0<=first and first+sum(counts)<=len(entries)
        cursor=first
        for g,count in enumerate(counts):
            for ref in entries[cursor:cursor+count]:
                assert ref and -ni<=ref<=n,(i,ref)
                if ref>0:arcs[(ref-1,g%2)].add((i,g//2))
            cursor+=count
    degrees={x:0 for x in arcs}
    for targets in arcs.values():
        for x in targets:degrees[x]+=1
    ready=[x for x,degree in degrees.items() if not degree];seen=0
    while ready:
        x=ready.pop();seen+=1
        for t in arcs[x]:
            degrees[t]-=1
            if degrees[t]==0:ready.append(t)
    assert seen==len(arcs),('create/serialize dependency cycle',p['name'],[x for x,d in degrees.items() if d][:8])
    native={e['index']+1:plain(props(p,e)) for e in es if is_widget(e)}
    for ref,v in native.items():
        for slot in v.get('Slots',[]):
            assert slot in native
            s=native[slot];assert s['Parent']==ref and es[slot-1]['outer']==ref-1,(es[ref-1]['name'],'parent',slot)
            child=s.get('Content',0)
            if child in native:assert native[child]['Slot']==slot,(es[child-1]['name'],'child slot',slot,native[child].get('Slot'))
    return {'native_objects':len(native),'export_create_serialize_commands':len(commands),
            'native_panel_slot_reciprocity':'PASS','dependency_indices_and_acyclic_order':'PASS'}

for edition in ['Steam_current','NoSteam_0.7.9.16232']:
    old=cf.Toc(BASE/'Files'/edition/'pakchunk1015-Windows_P.utoc');previous={p:old.read_chunk(i) for p,i in old.files};files=dict(previous)
    for edit in changes if edition=='Steam_current' else []:
        mount=edit['mount'];data=(ROOT/'Developer/V18_8/patched'/edition/mount).read_bytes()
        assert sha(data)==edit['patched_sha256']
        if mount in previous:assert sha(previous[mount])==edit['source_sha256']
        files[mount]=data
    if edition=='Steam_current':
        original=cf.build_directory
        cf.build_directory=lambda pairs,mount='../../../':original([(i,p) for p,i in pairs],mount)
        try:cf.build_container(list(files.items()),ROOT/'Files'/edition/'pakchunk1015-Windows_P.utoc')
        finally:cf.build_directory=original
    else:
        for ext in ['pak','utoc','ucas']:assert (ROOT/'Files'/edition/('pakchunk1015-Windows_P.'+ext)).read_bytes()==(BASE/'Files'/edition/('pakchunk1015-Windows_P.'+ext)).read_bytes()
    toc=cf.Toc(ROOT/'Files'/edition/'pakchunk1015-Windows_P.utoc');assert not toc.verify_meta()
    assert {p:toc.read_chunk(i) for p,i in toc.files}==files
    out=ROOT/'FinalExtracted'/edition;assert not out.exists(),'fresh container extraction required';toc.extract_named(out)
    proofs={};functions=0
    if edition=='Steam_current':
        for edit in changes:
            p=ui.zen.package(out/edit['mount']);proofs[edit['name']]=graph(p);scripts={}
            for e in p['exports']:
                if e['cls']==FUNCTION:scripts[e['index']]=verify_script(p['bytes'][e['start']:e['end']])[3];functions+=1
            for nodes in scripts.values():
                for node in nodes:
                    for x in k.walk(node):
                        if x.op not in (0x1c,0x46):continue
                        target=struct.unpack('<i',x.parts[0].data)[0]-1
                        if target not in scripts or not p['exports'][target]['name'].startswith('ExecuteUbergraph_'):continue
                        arg=x.parts[1];entry=struct.unpack('<i',arg.parts[0].data)[0] if arg.op==0x1d else {0x25:0,0x26:1}[arg.op]
                        assert entry in {y.old for node in scripts[target] for y in k.walk(node)},(p['name'],entry)
    assert all(files[p]==v for p,v in previous.items() if not any(e['mount']==p for e in changes) or edition!='Steam_current')
    assert (ROOT/'Files'/edition/'pakchunk1015-Windows_P.pak').read_bytes()==(BASE/'Files'/edition/'pakchunk1015-Windows_P.pak').read_bytes()
    for name in ['Game.locres','translation.tsv']:assert (ROOT/'Data'/edition/name).read_bytes()==(BASE/'Data'/edition/name).read_bytes()
    result['editions'][edition]={'packages':len(files),'new_packages':sorted(files.keys()-previous.keys()),
        'strict_widget_functions':functions,'all_event_entries':'PASS','graphs':proofs,
        'exact_full_container_readback':'PASS','translations_essence_map_radial_settings_retained':'PASS',
        'nosteam_payload_identical_to_18_7':edition!='Steam_current'}
(ROOT/'Reports/V18_8_VALIDATION.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False,indent=2))
