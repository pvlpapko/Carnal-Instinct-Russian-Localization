"""Rebuild EXE from the release Files folders. Python 3 + Go 1.23 required.

The newest Steam version supplies both Steam and newer NoSteam. No duplicated
newer-NoSteam payload folder is created, including during future updates.
"""
from pathlib import Path
import argparse,hashlib,json,os,re,shutil,subprocess
from add_resources import patch

HERE=Path(__file__).resolve().parent

def version(path):
    # Steam is rolling: runtime payload lives in a stable Steam_current folder.
    return (1,) if path.name == 'Steam_current' else ()

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--files',type=Path,default=HERE.parent.parent/'Files');parser.add_argument('--icon',type=Path,default=HERE.parent.parent/'Branding'/'ci_ru.ico');parser.add_argument('--go',default=os.environ.get('CI_RU_GO','go'));parser.add_argument('--output',type=Path,default=HERE.parent.parent/'Installer'/'CarnalInstinct_RU_Setup.exe');args=parser.parse_args()
    candidates=[p for p in args.files.iterdir() if p.is_dir() and version(p)]
    if not candidates:raise SystemExit('No Steam_current folder found')
    steam=max(candidates,key=version);legacy=args.files/'NoSteam_0.7.9.16232'
    names=['pakchunk1015-Windows_P.'+x for x in ['pak','utoc','ucas']]
    inputs=[(p,n,(p/n).read_bytes()) for p in [steam,legacy] for n in names]
    if any(not data for _,_,data in inputs):raise SystemExit('Empty payload file')
    stage=HERE/'payload'
    if stage.exists():shutil.rmtree(stage)
    for folder,n,data in inputs:
        out=stage/folder.name;out.mkdir(exist_ok=True,parents=True);(out/n).write_bytes(data)
    trusted=HERE/'trusted_hashes.json';known=json.loads(trusted.read_text(encoding='utf-8'))
    for _,n,data in inputs:
        digest=hashlib.sha256(data).hexdigest();values=known.setdefault(n,[])
        if digest not in values:values.append(digest)
    trusted.write_text(json.dumps(known,indent=2)+'\n',encoding='utf-8')
    env=os.environ.copy();env.update(GOOS='windows',GOARCH='amd64',CGO_ENABLED='0',GOTOOLCHAIN='local',GOPROXY='off')
    subprocess.run([args.go,'test','-buildvcs=false','-count=1','-c','-o',str(HERE/'core-tests.exe'),'core.go','core_test.go','no_backup_test.go'],env=env,cwd=HERE,check=True)
    raw=HERE/'CarnalInstinct_RU_Setup_raw.exe'
    flags='-H windowsgui -s -w -X main.steamPayloadEditionID='+steam.name
    subprocess.run([args.go,'build','-buildvcs=false','-trimpath','-ldflags='+flags,'-o',str(raw),'.'],env=env,cwd=HERE,check=True)
    args.output.parent.mkdir(parents=True,exist_ok=True);result=patch(raw,args.icon,args.output)
    raw.unlink();(HERE/'core-tests.exe').unlink()
    print(json.dumps({'installer':str(args.output),'steam_source':steam.name,'newer_nosteam_source':steam.name,'sha256':hashlib.sha256(args.output.read_bytes()).hexdigest(),'resources':result},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
