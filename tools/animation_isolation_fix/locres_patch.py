import struct, csv, json, hashlib, os, sys
from pathlib import Path
MAGIC=bytes.fromhex('0e147475674a03fc4a15909dc3377f1b')

def read_i32(b,p): return struct.unpack_from('<i',b,p)[0],p+4
def read_u32(b,p): return struct.unpack_from('<I',b,p)[0],p+4
def read_i64(b,p): return struct.unpack_from('<q',b,p)[0],p+8

def read_ustr(b,p):
    start=p; n,p=read_i32(b,p)
    if n==0: return '',p,(start,p)
    if n>0:
        raw=b[p:p+n]; p+=n
        if len(raw)!=n or raw[-1:]!=b'\x00': raise ValueError(('bad ansi string',start,n))
        s=raw[:-1].decode('utf-8',errors='strict')
    else:
        n2=-n; raw=b[p:p+n2*2]; p+=n2*2
        if len(raw)!=n2*2 or raw[-2:]!=b'\x00\x00': raise ValueError(('bad utf16 string',start,n))
        s=raw[:-2].decode('utf-16le',errors='strict')
    return s,p,(start,p)

def enc_ustr(s):
    if all(ord(ch)<128 for ch in s):
        raw=s.encode('utf-8')+b'\0'
        return struct.pack('<i',len(raw))+raw
    raw=s.encode('utf-16le')+b'\0\0'
    return struct.pack('<i',-(len(raw)//2))+raw

def parse(path):
    b=bytearray(Path(path).read_bytes()); p=0
    if b[:16]!=MAGIC: raise ValueError('unsupported legacy locres')
    p=16; ver=b[p]; p+=1
    if ver<1: raise ValueError(ver)
    table_off,p=read_i64(b,p)
    entries_count=None
    if ver>=2: entries_count,p=read_i32(b,p)
    ns_count,p=read_i32(b,p)
    namespaces=[]; entries=[]
    for ni in range(ns_count):
        nh=None
        if ver>=2: nh,p=read_u32(b,p)
        ns,p,_=read_ustr(b,p)
        kc,p=read_i32(b,p)
        nse={'name':ns,'hash':nh,'count':kc}
        namespaces.append(nse)
        for j in range(kc):
            kh=None
            if ver>=2: kh,p=read_u32(b,p)
            key,p,_=read_ustr(b,p)
            sh,p=read_u32(b,p)
            idx_pos=p; idx,p=read_i32(b,p)
            entries.append({'namespace':ns,'key':key,'source_hash':sh,'string_index':idx,'string_index_pos':idx_pos,'key_hash':kh,'namespace_hash':nh})
    entries_end=p
    if p>table_off: raise ValueError(('entries overlap table',p,table_off))
    p=table_off; sc,p=read_i32(b,p)
    strings=[]
    for i in range(sc):
        s,p,span=read_ustr(b,p)
        ref_pos=None; ref=None
        if ver>=2:
            ref_pos=p; ref,p=read_i32(b,p)
        strings.append({'text':s,'refcount':ref,'ref_pos':ref_pos,'span':span})
    if p!=len(b):
        raise ValueError(('trailing bytes',p,len(b)))
    if entries_count is not None and entries_count!=len(entries): raise ValueError(('entry count mismatch',entries_count,len(entries)))
    actual=[0]*len(strings)
    for e in entries:
        if not 0<=e['string_index']<len(strings): raise ValueError(('bad index',e))
        actual[e['string_index']]+=1
        e['value']=strings[e['string_index']]['text']
    if ver>=2:
        bad=[(i,s['refcount'],actual[i],s['text']) for i,s in enumerate(strings) if s['refcount']!=actual[i]]
        if bad: raise ValueError(('refcount mismatch',bad[:10],len(bad)))
    return {'bytes':b,'version':ver,'table_offset':table_off,'entries_count':entries_count,'namespace_count':ns_count,'entries':entries,'strings':strings,'entries_end':entries_end}

TECH_ENUM_PREFIXES=(
    'DynamicCombatSystem/Enumerations/',
)
TECH_ENUM_EXCLUDE={'DynamicCombatSystem/Enumerations/E_StatType.uasset'}
TECH_EXACT_ASSETS={
    'BlueprintSystems/AdvancedLocomotionV2/Enumeration/E_Gait.uasset',
    'BlueprintSystems/AdvancedLocomotionV2/Enumeration/E_MovementDirection.uasset',
    'BlueprintSystems/AdvancedLocomotionV2/Enumeration/E_Stance.uasset',
    'DynamicCombatSystem/Blueprints/AI/E_Faction.uasset',
}
TECH_SELECTIVE={
    'DynamicCombatSystem/Blueprints/AI/BP_CI_BaseAI_DLG.uasset': {'BASE AI','Base AI DLG'},
    'DynamicCombatSystem/Blueprints/AI/BP_CI_SellswordAI.uasset': {'BASE AI','Base AI DLG'},
}

def is_technical_row(r):
    assets=(r.get('Assets') or '').split(';')
    eng=r.get('English','')
    for a in assets:
        a=a.strip()
        if a in TECH_EXACT_ASSETS: return True
        if a in TECH_SELECTIVE and eng in TECH_SELECTIVE[a]: return True
        if a.startswith(TECH_ENUM_PREFIXES) and a not in TECH_ENUM_EXCLUDE: return True
    return False

def patch(locres, tsv, out_locres, out_tsv, report_path):
    st=parse(locres)
    with open(tsv,encoding='utf-8-sig',newline='') as f:
        reader=csv.DictReader(f,delimiter='\t'); rows=list(reader); fields=reader.fieldnames
    byid={(e['namespace'],e['key'],str(e['source_hash'])):e for e in st['entries']}
    text_indices={}
    for i,s in enumerate(st['strings']): text_indices.setdefault(s['text'],[]).append(i)
    changes=[]; missing=[]; mismatches=[]
    appended={}
    for r in rows:
        if not is_technical_row(r): continue
        k=(r['Namespace'],r['Key'],r['SourceStringHash'])
        e=byid.get(k)
        if not e:
            missing.append({'key':k,'english':r['English'],'asset':r['Assets'],'reason':'entry_not_found'}); continue
        if e['value']!=r['Russian']:
            mismatches.append({'key':k,'locres':e['value'],'tsv_ru':r['Russian'],'english':r['English']})
        target=r['English']
        inds=text_indices.get(target,[])
        if inds:
            new_idx=next((i for i in inds if st['strings'][i]['refcount']>0),inds[0])
        else:
            a=appended.get(target)
            if a is None:
                a={'index':len(st['strings'])+len(appended),'refcount':0}
                appended[target]=a
            new_idx=a['index']
        old_idx=e['string_index']
        if old_idx!=new_idx:
            struct.pack_into('<i',st['bytes'],e['string_index_pos'],new_idx)
            old_s=st['strings'][old_idx]
            old_s['refcount']-=1
            struct.pack_into('<i',st['bytes'],old_s['ref_pos'],old_s['refcount'])
            if new_idx < len(st['strings']):
                new_s=st['strings'][new_idx]
                new_s['refcount']+=1
                struct.pack_into('<i',st['bytes'],new_s['ref_pos'],new_s['refcount'])
            else:
                appended[target]['refcount']+=1
        changes.append({'namespace':r['Namespace'],'key':r['Key'],'source_hash':r['SourceStringHash'],'asset':r['Assets'],'english':target,'before':r['Russian'],'old_index':old_idx,'new_index':new_idx})
        r['Russian']=target
    if missing: raise RuntimeError('missing locres entries: '+json.dumps(missing[:10],ensure_ascii=False))
    if appended:
        struct.pack_into('<i',st['bytes'],st['table_offset'],len(st['strings'])+len(appended))
        for textv,a in appended.items():
            st['bytes'] += enc_ustr(textv) + struct.pack('<i',a['refcount'])
    Path(out_locres).write_bytes(st['bytes'])
    with open(out_tsv,'w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,delimiter='\t',lineterminator='\n'); w.writeheader(); w.writerows(rows)
    after=parse(out_locres)
    amap={(e['namespace'],e['key'],str(e['source_hash'])):e['value'] for e in after['entries']}
    bad=[]
    for c in changes:
        k=(c['namespace'],c['key'],c['source_hash'])
        if amap[k]!=c['english']: bad.append((k,amap[k],c['english']))
    if bad: raise RuntimeError(('postcheck failed',bad[:10]))
    report={
        'input_locres':str(locres),'input_tsv':str(tsv),'output_locres':str(out_locres),'output_tsv':str(out_tsv),
        'version':st['version'],'entries':len(st['entries']),'string_lut_entries':len(st['strings']),
        'technical_keys_restored':len(changes),'appended_lut_strings':len(appended),'mismatches_before_patch':mismatches,
        'locres_size_before':Path(locres).stat().st_size,'locres_size_after':Path(out_locres).stat().st_size,
        'sha256_before':hashlib.sha256(Path(locres).read_bytes()).hexdigest(),'sha256_after':hashlib.sha256(Path(out_locres).read_bytes()).hexdigest(),
        'changes':changes,
        'post_validation':'PASS: complete parse, entry indexes, refcounts, selected values',
    }
    Path(report_path).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return report

if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser(); ap.add_argument('locres'); ap.add_argument('tsv'); ap.add_argument('outdir'); ap.add_argument('--name',default='TECHNICAL_KEY_RESTORE.json')
    a=ap.parse_args(); od=Path(a.outdir); od.mkdir(parents=True,exist_ok=True)
    r=patch(a.locres,a.tsv,od/'Game.locres',od/'translation.tsv',od/a.name)
    print(json.dumps({k:r[k] for k in ['version','entries','string_lut_entries','technical_keys_restored','locres_size_before','locres_size_after','sha256_before','sha256_after','post_validation']},ensure_ascii=False,indent=2))
