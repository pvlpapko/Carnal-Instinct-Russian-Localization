import struct, sys

def align(v,a): return (v+a-1)//a*a

def parse_ico(path):
    b=open(path,'rb').read()
    if len(b)<6: raise ValueError('truncated icon header')
    reserved,itype,count=struct.unpack_from('<HHH',b,0)
    if (reserved,itype)!=(0,1) or not 1<=count<=256: raise ValueError('invalid icon header')
    table_end=6+count*16
    if table_end>len(b): raise ValueError('truncated icon directory')
    out=[]
    for i in range(count):
        o=6+i*16;w,h,cc,res,planes,bpp,size,dataoff=struct.unpack_from('<BBBBHHII',b,o)
        if res!=0 or size==0 or dataoff<table_end or dataoff+size>len(b): raise ValueError('invalid icon image bounds')
        out.append(dict(w=w,h=h,cc=cc,res=res,planes=planes,bpp=bpp,size=size,data=b[dataoff:dataoff+size]))
    return out

MANIFEST=b'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">\n  <assemblyIdentity version="3.0.0.0" processorArchitecture="amd64" name="DontLook.CarnalInstinct.RU.Setup" type="win32"/>\n  <description>Carnal Instinct Russian Localization - Don't Look</description>\n  <trustInfo xmlns="urn:schemas-microsoft-com:asm.v3">\n    <security><requestedPrivileges><requestedExecutionLevel level="requireAdministrator" uiAccess="false"/></requestedPrivileges></security>\n  </trustInfo>\n  <application xmlns="urn:schemas-microsoft-com:asm.v3">
    <windowsSettings>
      <dpiAware xmlns="http://schemas.microsoft.com/SMI/2005/WindowsSettings">true/pm</dpiAware>
      <dpiAwareness xmlns="http://schemas.microsoft.com/SMI/2016/WindowsSettings">PerMonitorV2, PerMonitor</dpiAwareness>
      <longPathAware xmlns="http://schemas.microsoft.com/SMI/2016/WindowsSettings">true</longPathAware>
    </windowsSettings>
  </application>
  <compatibility xmlns="urn:schemas-microsoft-com:compatibility.v1">
    <application><supportedOS Id="{8e0f7a12-bfb3-4fe8-b9a5-48fd50a15a9a}"/></application>
  </compatibility>
  <dependency><dependentAssembly><assemblyIdentity type="win32" name="Microsoft.Windows.Common-Controls" version="6.0.0.0" processorArchitecture="*" publicKeyToken="6595b64144ccf1df" language="*"/></dependentAssembly></dependency>\n</assembly>\n'''

def build_rsrc(icon_entries, base_rva):
    b=bytearray()
    def reserve(n,a=4):
        while len(b)%a:b.append(0)
        o=len(b);b.extend(b'\0'*n);return o
    def mk_dir(n):
        o=reserve(16);struct.pack_into('<IIHHHH',b,o,0,0,0,0,0,n);reserve(8*n,1);return o
    def setent(d,i,idv,target,sub):
        struct.pack_into('<II',b,d+16+i*8,idv,target|(0x80000000 if sub else 0))
    # Root: icon/group/manifest
    root=mk_dir(3); icon_type=mk_dir(len(icon_entries)); group_type=mk_dir(1); manifest_type=mk_dir(1)
    setent(root,0,3,icon_type,1);setent(root,1,14,group_type,1);setent(root,2,24,manifest_type,1)
    icon_lang=[]
    for i in range(len(icon_entries)):
        d=mk_dir(1);icon_lang.append(d);setent(icon_type,i,i+1,d,1)
    group_lang=mk_dir(1);setent(group_type,0,1,group_lang,1)
    manifest_lang=mk_dir(1);setent(manifest_type,0,1,manifest_lang,1)
    icon_de=[]
    for i,d in enumerate(icon_lang):
        de=reserve(16);icon_de.append(de);setent(d,0,1033,de,0)
    group_de=reserve(16);setent(group_lang,0,1033,group_de,0)
    manifest_de=reserve(16);setent(manifest_lang,0,1033,manifest_de,0)
    for i,e in enumerate(icon_entries):
        while len(b)%4:b.append(0)
        o=len(b);b.extend(e['data']);struct.pack_into('<IIII',b,icon_de[i],base_rva+o,len(e['data']),0,0)
    while len(b)%4:b.append(0)
    go=len(b);g=bytearray(struct.pack('<HHH',0,1,len(icon_entries)))
    for i,e in enumerate(icon_entries):g+=struct.pack('<BBBBHHIH',e['w'],e['h'],e['cc'],e['res'],e['planes'],e['bpp'],e['size'],i+1)
    b.extend(g);struct.pack_into('<IIII',b,group_de,base_rva+go,len(g),0,0)
    while len(b)%4:b.append(0)
    mo=len(b);b.extend(MANIFEST);struct.pack_into('<IIII',b,manifest_de,base_rva+mo,len(MANIFEST),65001,0)
    return bytes(b)

def patch(exe,ico,out):
    b=bytearray(open(exe,'rb').read())
    if len(b)<64 or b[:2]!=b'MZ':raise ValueError('not DOS/PE executable')
    pe=struct.unpack_from('<I',b,0x3c)[0]
    if pe+24>len(b):raise ValueError('truncated PE header')
    if b[pe:pe+4]!=b'PE\0\0':raise ValueError('not PE')
    coff=pe+4;nsec=struct.unpack_from('<H',b,coff+2)[0];optsz=struct.unpack_from('<H',b,coff+16)[0];opt=coff+20
    if opt+optsz>len(b) or optsz<136:raise ValueError('truncated PE32+ optional header')
    if struct.unpack_from('<H',b,opt)[0]!=0x20b:raise ValueError('not PE32+')
    if any(struct.unpack_from('<II',b,opt+112+2*8)):raise ValueError('executable already contains resources; use an unpatched Go build')
    sa=struct.unpack_from('<I',b,opt+32)[0];fa=struct.unpack_from('<I',b,opt+36)[0];headers=struct.unpack_from('<I',b,opt+60)[0];st=opt+optsz
    nso=st+nsec*40
    if nso+40>headers or headers>len(b):raise ValueError('no header room')
    maxe=0
    for i in range(nsec):
        o=st+i*40;vs,va,rs,rp=struct.unpack_from('<IIII',b,o+8);maxe=max(maxe,va+max(vs,rs))
    va=align(maxe,sa);rsrc=build_rsrc(parse_ico(ico),va);rp=align(len(b),fa);raw=align(len(rsrc),fa)
    if len(b)<rp:b.extend(b'\0'*(rp-len(b)))
    b.extend(rsrc);b.extend(b'\0'*(raw-len(rsrc)))
    sh=bytearray(40);sh[:8]=b'.rsrc\0\0\0';struct.pack_into('<IIIIIIHHI',sh,8,len(rsrc),va,raw,rp,0,0,0,0,0x40000040);b[nso:nso+40]=sh
    struct.pack_into('<H',b,coff+2,nsec+1);struct.pack_into('<I',b,opt+56,align(va+len(rsrc),sa));struct.pack_into('<I',b,opt+8,struct.unpack_from('<I',b,opt+8)[0]+raw);struct.pack_into('<II',b,opt+112+2*8,va,len(rsrc))
    open(out,'wb').write(b);return {'icons':len(parse_ico(ico)),'resource_size':len(rsrc),'raw_size':raw,'resource_rva':va,'sections':nsec+1,'manifest':True}

if __name__=='__main__':print(patch(sys.argv[1],sys.argv[2],sys.argv[3]))
