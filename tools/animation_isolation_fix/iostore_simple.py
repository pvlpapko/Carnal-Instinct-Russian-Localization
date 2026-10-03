from pathlib import Path
import struct, json, hashlib, sys
from blake3_pure import blake3

INVALID=0xffffffff

def u24le(b): return b[0] | (b[1]<<8) | (b[2]<<16)
def u40be(b): return int.from_bytes(b,'big')
def u40le(b): return int.from_bytes(b,'little')

def fstring_read(data, pos):
    (n,)=struct.unpack_from('<i',data,pos); pos+=4
    if n==0: return '',pos
    if n>0:
        raw=data[pos:pos+n]; pos+=n
        if raw and raw[-1]==0: raw=raw[:-1]
        return raw.decode('utf-8','surrogateescape'),pos
    count=-n; raw=data[pos:pos+count*2]; pos+=count*2
    if raw[-2:]==b'\0\0': raw=raw[:-2]
    return raw.decode('utf-16le','surrogatepass'),pos

def fstring_write(s):
    try:
        b=s.encode('ascii')+b'\0'
        return struct.pack('<i',len(b))+b
    except UnicodeEncodeError:
        b=s.encode('utf-16le')+b'\0\0'
        return struct.pack('<i',-(len(b)//2))+b

def parse_dir_index(data):
    p=0; mount,p=fstring_read(data,p)
    (nd,)=struct.unpack_from('<i',data,p);p+=4
    dirs=[]
    for i in range(nd):
        dirs.append(struct.unpack_from('<4I',data,p));p+=16
    (nf,)=struct.unpack_from('<i',data,p);p+=4
    files=[]
    for i in range(nf):
        files.append(struct.unpack_from('<3I',data,p));p+=12
    (ns,)=struct.unpack_from('<i',data,p);p+=4
    strings=[]
    for i in range(ns):
        s,p=fstring_read(data,p); strings.append(s)
    if p!=len(data):
        raise ValueError(f'dir index trailing {len(data)-p} bytes at {p}/{len(data)}')
    paths={}
    visited_dirs=set(); visited_files=set()
    def name(idx): return '' if idx==INVALID else strings[idx]
    def walk_dir(di,parent):
        if di==INVALID:return
        if di>=len(dirs): raise ValueError(('bad dir',di))
        if di in visited_dirs: raise ValueError(('dir cycle',di))
        visited_dirs.add(di)
        ni,child,sib,firstfile=dirs[di]
        dn=name(ni)
        here=parent
        if di!=0 and dn: here=(parent.rstrip('/')+'/'+dn).lstrip('/')
        fi=firstfile
        while fi!=INVALID:
            if fi>=len(files): raise ValueError(('bad file',fi))
            if fi in visited_files: raise ValueError(('file cycle',fi))
            visited_files.add(fi)
            fni,nxt,user=files[fi]
            fp=(here.rstrip('/')+'/'+name(fni)).lstrip('/')
            paths[fp]=user
            fi=nxt
        ci=child
        while ci!=INVALID:
            if ci>=len(dirs): raise ValueError(('bad child',ci))
            next_sib=dirs[ci][2]
            walk_dir(ci,here)
            ci=next_sib
    if dirs: walk_dir(0,'')
    return {'mount':mount,'dirs':dirs,'files':files,'strings':strings,'paths':paths,'visited_dirs':len(visited_dirs),'visited_files':len(visited_files)}

def parse_utoc(path):
    b=Path(path).read_bytes()
    if len(b)<144: raise ValueError('short utoc')
    if b[:16]!=b'-==--==--==--==-': raise ValueError('magic')
    version=b[16]
    hs, n, m, cbes, method_count, method_len, block_size, dir_size, partition_count = struct.unpack_from('<9I',b,0x14)
    container_id=struct.unpack_from('<Q',b,0x38)[0]
    guid=b[0x40:0x50]; flags=b[0x50]
    perfect=struct.unpack_from('<I',b,0x54)[0]
    partition_size=struct.unpack_from('<Q',b,0x58)[0]
    no_perfect=struct.unpack_from('<I',b,0x60)[0]
    p=hs
    chunk_ids=[b[p+i*12:p+(i+1)*12] for i in range(n)];p+=n*12
    offs=[]
    for i in range(n):
        x=b[p+i*10:p+(i+1)*10]
        offs.append((u40be(x[:5]),u40be(x[5:])))
    p+=n*10
    if perfect: p += perfect*4
    if no_perfect: p += no_perfect*4
    blocks=[]
    for i in range(m):
        x=b[p+i*cbes:p+(i+1)*cbes]
        blocks.append((u40le(x[:5]),u24le(x[5:8]),u24le(x[8:11]),x[11]))
    p+=m*cbes
    methods=[]
    for i in range(method_count):
        raw=b[p:p+method_len];p+=method_len
        methods.append(raw.split(b'\0',1)[0].decode('ascii'))
    if flags & 2: raise NotImplementedError('signed')
    dirraw=b[p:p+dir_size];p+=dir_size
    di=parse_dir_index(dirraw) if dir_size else None
    metas=[]
    for i in range(n):
        x=b[p:p+24];p+=24
        metas.append((x[:20],x[20],x[21:24]))
    if p!=len(b): raise ValueError(f'utoc trailing {len(b)-p} bytes')
    return {'raw':b,'version':version,'header_size':hs,'n':n,'m':m,'cbes':cbes,'method_count':method_count,'method_len':method_len,'block_size':block_size,'dir_size':dir_size,'partition_count':partition_count,'container_id':container_id,'guid':guid,'flags':flags,'perfect':perfect,'partition_size':partition_size,'no_perfect':no_perfect,'chunk_ids':chunk_ids,'offs':offs,'blocks':blocks,'methods':methods,'dirraw':dirraw,'dir':di,'metas':metas,'header_raw':b[:hs]}

def extract_chunk(toc, ucas:bytes, idx):
    voff,length=toc['offs'][idx]
    if length==0:return b''
    bs=toc['block_size']; start=voff//bs
    out=bytearray(); remain=length
    bi=start
    while remain>0:
        poff,csize,usize,method=toc['blocks'][bi]
        if method!=0: raise NotImplementedError(('compression',method))
        raw=ucas[poff:poff+csize]
        if len(raw)!=csize: raise ValueError(('short ucas block',bi))
        if csize!=usize: raise ValueError(('compressed but method0',bi,csize,usize))
        take=min(remain,usize); out+=raw[:take]; remain-=take; bi+=1
    if len(out)!=length: raise AssertionError
    return bytes(out)

def validate(toc_path,ucas_path,verbose=True):
    toc=parse_utoc(toc_path); ucas=Path(ucas_path).read_bytes()
    bad=[]
    datas=[]
    for i in range(toc['n']):
        d=extract_chunk(toc,ucas,i); datas.append(d)
        h=blake3(d,32)[:20]
        if h!=toc['metas'][i][0]: bad.append((i,h.hex(),toc['metas'][i][0].hex(),len(d)))
    end=max((o+c for o,c,_,_ in toc['blocks']),default=0)
    info={'chunks':toc['n'],'blocks':toc['m'],'paths':len(toc['dir']['paths']) if toc['dir'] else 0,'mount':toc['dir']['mount'] if toc['dir'] else None,'bad_hashes':bad,'ucas_size':len(ucas),'physical_end':end,'block_cover_exact':end==len(ucas),'container_header_indices':[i for i,c in enumerate(toc['chunk_ids']) if c[-1]==6]}
    if verbose: print(json.dumps(info,indent=2))
    return toc,datas,info

def parse_container_header(d):
    p=0
    magic,version=struct.unpack_from('<II',d,p);p+=8
    cid=struct.unpack_from('<Q',d,p)[0];p+=8
    n=struct.unpack_from('<I',d,p)[0];p+=4
    pids=list(struct.unpack_from('<'+'Q'*n,d,p)) if n else []; p+=8*n
    store_len=struct.unpack_from('<I',d,p)[0];p+=4
    store=d[p:p+store_len]; p+=store_len
    entries=[]
    for i in range(n):
        imp_count,imp_rel,shader_count,shader_rel=struct.unpack_from('<IIII',store,i*16)
        deps=[]
        if imp_count:
            start=i*16+imp_rel
            deps=list(struct.unpack_from('<'+'Q'*imp_count,store,start))
        entries.append({'package_id':pids[i],'imports':deps,'shader_count':shader_count,'shader_rel':shader_rel})
    tail=d[p:]
    return {'magic':magic,'version':version,'container_id':cid,'package_count':n,'package_ids':pids,'store_len':store_len,'entries':entries,'tail':tail,'parsed_prefix_end':p}

if __name__=='__main__':
    toc,datas,info=validate(sys.argv[1],sys.argv[2])
    for i in info['container_header_indices']:
        h=parse_container_header(datas[i]); print('HEADER',i,{k:h[k] for k in ['magic','version','container_id','package_count','store_len']},'tail',len(h['tail']),h['tail'][:32].hex())
    if toc['dir']:
        print('first paths:')
        for x in list(toc['dir']['paths'].items())[:20]: print(x)
