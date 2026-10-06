#!/usr/bin/env python3
from pathlib import Path
import csv,sys,unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'Developer/SafeUIFix/tools')); import ci_formats as cf
KEYS={'2658420B4FD907B4111E3493B20DE1D4':'Canopic Capture','73D7C99F4BFC15F37038A78A260A26D8':'Fishing','61A1BF914358BC1944053EAC831C41BB':"Korvoth's Sceptre",'FFD8476A472BA585601FF8B43AD324B0':'Masturbate','4ACBBA2B411E9ED180EAE98189BA072D':'Shade Sight','86304DA1490FFECCD302FE9B9B15D119':'Summon Aadi','D7A77ABE4ABEE67D22AE9FA9D8D06220':'Torch'}
ED=['Steam_current','NoSteam_0.7.9.16232']
class TestRadialActionFix(unittest.TestCase):
 def test_runtime_ids_are_original_english(self):
  for ed in ED:
   d={e['key']:e['value'] for e in cf.Locres(ROOT/'Data'/ed/'Game.locres').entries if e['namespace']=='' and e['key'] in KEYS}; self.assertEqual(d,KEYS)
 def test_pak_exactly_embeds_data_locres(self):
  for ed in ED: self.assertEqual(cf.parse_pak_one(ROOT/'Files'/ed/'pakchunk1015-Windows_P.pak')['data'],(ROOT/'Data'/ed/'Game.locres').read_bytes())
 def test_only_target_rows_are_technicalized(self):
  for ed in ED:
   with (ROOT/'Data'/ed/'translation.tsv').open(encoding='utf-8-sig',newline='') as f: rows=list(csv.DictReader(f,delimiter='\t'))
   t={r['Key']:r for r in rows if r['Namespace']=='' and r['Key'] in KEYS and r['Assets']=='BlueprintSystems/DynamicRadialMenu/Tables/DT_Menu.uasset'}
   self.assertEqual(set(t),set(KEYS)); self.assertTrue(all(t[k]['Russian']==v for k,v in KEYS.items()))
if __name__=='__main__':unittest.main()
