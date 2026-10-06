#!/usr/bin/env python3
from pathlib import Path
import hashlib, shutil, sys
BASE=Path(sys.argv[1]).resolve(); OUT=Path(sys.argv[2]).resolve()
if OUT.exists(): shutil.rmtree(OUT)
shutil.copytree(BASE,OUT)
sys.path.insert(0,str(OUT/'Developer/SafeUIFix/tools'))
import ci_formats as cf
TARGET='Carnal_Instinct_UE5/Content/NiceSettingsMenu/UI/Theme_3/WB_T3_MainMenu.uasset'
SPEC={
 'Steam_current':('a66fc5e85b5bd36d9b916267222f6fc5a1e5252fdd47469d3734f3059626ecbd','0af9bdf9d0d9b067b0361e4ebde83b1dbe8d7e506e99587ef1c199c6015f8cd9',42002),
 'NoSteam_0.7.9.16232':('5323ba5256552942804688c3fdc108551365527afd9ca2b2a4387052d637ddd3','904527b59be85c28b0ba449111719dfeda8e6581833e1ae49ba1434814e7391e',39499),
}
sha=lambda b: hashlib.sha256(b).hexdigest()
for ed,(old_sha,new_sha,asset_off) in SPEC.items():
    utoc=OUT/'Files'/ed/'pakchunk1015-Windows_P.utoc'; ucas=utoc.with_suffix('.ucas')
    toc=cf.Toc(utoc); idx=dict(toc.files)[TARGET]; old=toc.read_chunk(idx)
    assert sha(old)==old_sha
    b=bytearray(old); assert b[asset_off]==0x28; b[asset_off]=0x27; new=bytes(b)
    assert sha(new)==new_sha
    raw=bytearray(ucas.read_bytes()); pos=raw.find(old)
    assert pos>=0 and raw.find(old,pos+1)<0
    raw[pos:pos+len(old)]=new; ucas.write_bytes(raw)
    raw_toc=bytearray(utoc.read_bytes()); meta_base=len(raw_toc)-toc.n*24; meta_pos=meta_base+idx*24
    h=cf.blake3(new).digest()[:20]; raw_toc[meta_pos:meta_pos+20]=h; utoc.write_bytes(raw_toc)
    check=cf.Toc(utoc); assert check.read_chunk(idx)==new and check.meta[idx][:20]==h and not check.verify_meta()
    print(ed,new_sha)
