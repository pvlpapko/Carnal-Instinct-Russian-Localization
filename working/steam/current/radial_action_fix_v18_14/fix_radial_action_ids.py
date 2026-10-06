#!/usr/bin/env python3
"""Restore DynamicRadialMenu action DisplayName FText identities used as runtime string IDs."""
from pathlib import Path
import json, sys, hashlib
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'Developer/SafeUIFix/tools'))
import ci_formats as cf

TECHNICAL = {
    '2658420B4FD907B4111E3493B20DE1D4': ('Canopic Capture', 1009922021),
    '73D7C99F4BFC15F37038A78A260A26D8': ('Fishing', 2680376353),
    '61A1BF914358BC1944053EAC831C41BB': ("Korvoth's Sceptre", 406990083),
    'FFD8476A472BA585601FF8B43AD324B0': ('Masturbate', 2284028336),
    '4ACBBA2B411E9ED180EAE98189BA072D': ('Shade Sight', 2468818620),
    '86304DA1490FFECCD302FE9B9B15D119': ('Summon Aadi', 1824976582),
    'D7A77ABE4ABEE67D22AE9FA9D8D06220': ('Torch', 1261106821),
}
EDITIONS=['Steam_current','NoSteam_0.7.9.16232']
ASSET='BlueprintSystems/DynamicRadialMenu/Tables/DT_Menu.uasset'
INTERNAL='Carnal_Instinct_UE5/Content/Localization/Game/en/Game.locres'
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def fix(ed):
    d=ROOT/'Data'/ed; lp=d/'Game.locres'; tp=d/'translation.tsv'; before=sha(lp)
    loc=cf.Locres(lp); found={}
    for e in loc.entries:
        if e['namespace']=='' and e['key'] in TECHNICAL:
            en,sh=TECHNICAL[e['key']]; assert e['source_hash']==sh
            found[e['key']]={'before':e['value'],'after':en,'source_hash':sh}; e['value']=en
    assert set(found)==set(TECHNICAL); loc.write(lp)
    raw=tp.read_bytes(); bom=b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b''; text=raw[len(bom):].decode('utf-8')
    out=[]; n=0
    for line in text.splitlines(keepends=True):
        ending='\r\n' if line.endswith('\r\n') else ('\n' if line.endswith('\n') else '')
        body=line[:-len(ending)] if ending else line; parts=body.split('\t')
        if len(parts)==9 and parts[0]=='' and parts[1] in TECHNICAL and parts[8]==ASSET:
            en,sh=TECHNICAL[parts[1]]; assert parts[5]==en and int(parts[2])==sh
            parts[6]=en; parts[7]='technical runtime action ID; original English preserved (v18.14)'
            body='\t'.join(parts); n+=1
        out.append(body+ending)
    assert n==7; tp.write_bytes(bom+''.join(out).encode('utf-8'))
    pak=ROOT/'Files'/ed/'pakchunk1015-Windows_P.pak'; cf.build_pak_one(lp.read_bytes(),INTERNAL,pak)
    assert cf.parse_pak_one(pak)['data']==lp.read_bytes()
    return {'edition':ed,'locres_before_sha256':before,'locres_after_sha256':sha(lp),'translation_tsv_sha256':sha(tp),'pak_sha256':sha(pak),'restored':found}
def main():
    r={'release':'18.14','fix':'radial exact-string action identifiers','editions':[fix(e) for e in EDITIONS]}
    (ROOT/'Reports/V18_14_RADIAL_ACTION_FIX.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
if __name__=='__main__': main()
