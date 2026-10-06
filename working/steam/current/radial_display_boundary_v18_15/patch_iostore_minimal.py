from pathlib import Path
import sys, json, hashlib
ROOT=Path(sys.argv[1]); BASE=Path(sys.argv[2])
sys.path.insert(0,str(ROOT/'Developer/SafeUIFix/tools'))
import ci_formats as cf
T='Carnal_Instinct_UE5/Content/BlueprintSystems/DynamicRadialMenu/Widgets/W_MenuItem.uasset'
report={'release':'18.15','method':'minimal_single_chunk_patch','target':T,'editions':{}}
for ed in ['Steam_current','NoSteam_0.7.9.16232']:
    base_utoc=BASE/'Files'/ed/'pakchunk1015-Windows_P.utoc'
    base_ucas=base_utoc.with_suffix('.ucas')
    out_utoc=ROOT/'Files'/ed/'pakchunk1015-Windows_P.utoc'
    out_ucas=out_utoc.with_suffix('.ucas')
    old=cf.Toc(base_utoc)
    idx=dict(old.files)[T]
    old_chunk=old.read_chunk(idx)
    new_chunk=(ROOT/'Developer/V18_15_RadialDisplay/patched'/ed/T).read_bytes()
    off,old_len=old.ol[idx]
    assert len(old_chunk)==old_len
    block_i=off//old.block_size
    block_off,cs,us,method=old.blocks[block_i]
    assert method==0 and cs==us==old.block_size
    assert off==block_off and len(new_chunk)<=old.block_size
    old_ucas=bytearray(base_ucas.read_bytes())
    assert old_ucas[off+old_len:block_off+old.block_size] == b'\0'*(old.block_size-old_len)
    new_ucas=bytearray(old_ucas)
    new_ucas[off:off+len(new_chunk)] = new_chunk
    new_ucas[off+len(new_chunk):block_off+old.block_size] = b'\0'*(old.block_size-len(new_chunk))
    out_ucas.write_bytes(new_ucas)
    old_utoc=bytearray(base_utoc.read_bytes())
    new_utoc=bytearray(old_utoc)
    ol_pos=old.header_size + 12*old.n + 10*idx
    new_utoc[ol_pos:ol_pos+10] = cf.write_offset_len(off,len(new_chunk))
    meta_base=len(old_utoc)-old.n*24
    meta_pos=meta_base+idx*24
    new_hash=cf.blake3(new_chunk).digest()[:20]
    new_utoc[meta_pos:meta_pos+20]=new_hash
    out_utoc.write_bytes(new_utoc)
    toc=cf.Toc(out_utoc)
    assert toc.ol[idx]==(off,len(new_chunk))
    assert toc.read_chunk(idx)==new_chunk
    assert toc.meta[idx][:20]==new_hash
    old_files=dict(old.files); new_files=dict(toc.files)
    assert old_files==new_files
    for path,j in old.files:
        if path==T: continue
        assert toc.read_chunk(new_files[path])==old.read_chunk(j), path
    changed_ucas=[i for i,(a,b) in enumerate(zip(base_ucas.read_bytes(),out_ucas.read_bytes())) if a!=b]
    assert changed_ucas and min(changed_ucas)>=off and max(changed_ucas)<off+old.block_size
    allowed=set(range(ol_pos,ol_pos+10))|set(range(meta_pos,meta_pos+20))
    changed_utoc={i for i,(a,b) in enumerate(zip(base_utoc.read_bytes(),out_utoc.read_bytes())) if a!=b}
    assert changed_utoc <= allowed and changed_utoc
    report['editions'][ed]={
      'chunk_index':idx,'offset':off,'old_length':old_len,'new_length':len(new_chunk),
      'old_chunk_sha256':hashlib.sha256(old_chunk).hexdigest(),
      'new_chunk_sha256':hashlib.sha256(new_chunk).hexdigest(),
      'new_chunk_blake3_160':new_hash.hex(),
      'utoc_sha256':hashlib.sha256(out_utoc.read_bytes()).hexdigest(),
      'ucas_sha256':hashlib.sha256(out_ucas.read_bytes()).hexdigest(),
      'other_named_chunks_exact_readback':'PASS',
      'utoc_changes_limited_to_offset_length_and_meta':'PASS',
      'ucas_changes_limited_to_target_physical_block':'PASS'
    }
(ROOT/'Reports/V18_15_IOSTORE_MINIMAL_PATCH.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
