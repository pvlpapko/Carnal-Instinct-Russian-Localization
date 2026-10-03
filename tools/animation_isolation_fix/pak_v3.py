import struct, hashlib, sys
from pathlib import Path
MAGIC=0x5A6F12E1
VERSION=3
MOUNT='../../../'
PATH='Carnal_Instinct_UE5/Content/Localization/Game/en/Game.locres'

def fstr_ascii(s):
    raw=s.encode('utf-8')+b'\0'
    return struct.pack('<i',len(raw))+raw

def entry(offset,size,sha1):
    return struct.pack('<qqqI',offset,size,size,0)+sha1+b'\0'+struct.pack('<I',0)

def build(locres,out):
    data=Path(locres).read_bytes(); h=hashlib.sha1(data).digest(); e=entry(0,len(data),h)
    payload=e+data
    index=fstr_ascii(MOUNT)+struct.pack('<i',1)+fstr_ascii(PATH)+e
    index_off=len(payload); index_hash=hashlib.sha1(index).digest()
    footer=struct.pack('<IIqq',MAGIC,VERSION,index_off,len(index))+index_hash
    blob=payload+index+footer
    Path(out).write_bytes(blob)
    return {'size':len(blob),'data_size':len(data),'index_offset':index_off,'index_size':len(index),'data_sha1':h.hex(),'index_sha1':index_hash.hex(),'sha256':hashlib.sha256(blob).hexdigest()}

def read_fstr(b,p):
    n=struct.unpack_from('<i',b,p)[0]; p+=4
    assert n>0
    raw=b[p:p+n]; p+=n
    assert raw[-1]==0
    return raw[:-1].decode(),p

def parse(path):
    b=Path(path).read_bytes(); footer=b[-44:]
    magic,ver,ioff,isz=struct.unpack_from('<IIqq',footer,0); ih=footer[24:44]
    assert magic==MAGIC and ver==VERSION
    assert hashlib.sha1(b[ioff:ioff+isz]).digest()==ih
    idx=b[ioff:ioff+isz]; p=0; mount,p=read_fstr(idx,p); n=struct.unpack_from('<i',idx,p)[0]; p+=4
    files=[]
    for _ in range(n):
        name,p=read_fstr(idx,p)
        off,size,usize,method=struct.unpack_from('<qqqI',idx,p); p+=28
        h=idx[p:p+20];p+=20; enc=idx[p];p+=1; block=struct.unpack_from('<I',idx,p)[0];p+=4
        files.append((name,off,size,usize,method,h,enc,block))
    assert p==len(idx)
    for name,off,size,usize,method,h,enc,block in files:
        q=off; x=struct.unpack_from('<qqqI',b,q);q+=28; hh=b[q:q+20];q+=20; ee=b[q];q+=1; bs=struct.unpack_from('<I',b,q)[0];q+=4
        assert x==(off,size,usize,method) and hh==h and ee==enc and bs==block
        data=b[q:q+size]
        assert hashlib.sha1(data).digest()==h
    return {'mount':mount,'count':n,'files':[{'name':x[0],'offset':x[1],'size':x[2],'sha1':x[5].hex()} for x in files], 'index_offset':ioff,'index_size':isz,'sha256':hashlib.sha256(b).hexdigest()}

if __name__=='__main__':
    if sys.argv[1]=='build': print(build(sys.argv[2],sys.argv[3]))
    elif sys.argv[1]=='parse': print(parse(sys.argv[2]))
