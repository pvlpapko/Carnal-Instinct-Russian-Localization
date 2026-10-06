#!/usr/bin/env python3
from pathlib import Path
import hashlib, sys
BASE=Path(sys.argv[1]).resolve(); NEW=Path(sys.argv[2]).resolve()
sys.path.insert(0,str(NEW/'Developer/SafeUIFix/tools'))
import ci_formats as cf
TARGET='Carnal_Instinct_UE5/Content/NiceSettingsMenu/UI/Theme_3/WB_T3_MainMenu.uasset'
EXPECTED={
 'Steam_current':'0af9bdf9d0d9b067b0361e4ebde83b1dbe8d7e506e99587ef1c199c6015f8cd9',
 'NoSteam_0.7.9.16232':'904527b59be85c28b0ba449111719dfeda8e6581833e1ae49ba1434814e7391e',
}
sha=lambda b: hashlib.sha256(b).hexdigest()
for ed,exp in EXPECTED.items():
    a=cf.Toc(BASE/'Files'/ed/'pakchunk1015-Windows_P.utoc'); b=cf.Toc(NEW/'Files'/ed/'pakchunk1015-Windows_P.utoc')
    assert dict(a.files)==dict(b.files)
    changed=[]
    amap=dict(a.files); bmap=dict(b.files)
    for path,i in a.files:
        if a.read_chunk(i)!=b.read_chunk(bmap[path]): changed.append(path)
    assert changed==[TARGET],(ed,changed)
    assert sha(b.read_chunk(bmap[TARGET]))==exp and not b.verify_meta()
    assert (BASE/'Files'/ed/'pakchunk1015-Windows_P.pak').read_bytes()==(NEW/'Files'/ed/'pakchunk1015-Windows_P.pak').read_bytes()
    assert (BASE/'Data'/ed/'Game.locres').read_bytes()==(NEW/'Data'/ed/'Game.locres').read_bytes()
print('PASS')
