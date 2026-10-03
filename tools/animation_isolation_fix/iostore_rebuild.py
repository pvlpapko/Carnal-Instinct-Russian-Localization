from pathlib import Path
import struct, os, json, hashlib, sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from iostore_simple import parse_utoc, extract_chunk, parse_container_header, parse_dir_index, fstring_write
from blake3_pure import blake3
INVALID=0xffffffff

class DNode:
    __slots__=('name','dirs','files','idx')
    def __init__(self,name=''):
        self.name=name; self.dirs={}; self.files=[]; self.idx=None

def build_dir_index(path_to_chunk, mount='../../../'):
    root=DNode('')
    for path,chunk_idx in sorted(path_to_chunk.items()):
        parts=path.replace('\\','/').strip('/').split('/')
        node=root
        for part in parts[:-1]:
            node=node.dirs.setdefault(part,DNode(part))
        node.files.append((parts[-1],chunk_idx))
    strings=[]; smap={}
    def sidx(s):
        if s not in smap:
            smap[s]=len(strings); strings.append(s)
        return smap[s]
    dirs=[]; files=[]
    def alloc_dir(node):
        node.idx=len(dirs); dirs.append([INVALID,INVALID,INVALID,INVALID])
        for child in sorted(node.dirs.values(), key=lambda x:x.name.lower()): alloc_dir(child)
    alloc_dir(root)
    def fill(node):
        ni=INVALID if node is root else sidx(node.name)
        children=sorted(node.dirs.values(),key=lambda x:x.name.lower())
        first_child=children[0].idx if children else INVALID
        first_file=INVALID
        prev_file=None
        for fname,user in sorted(node.files,key=lambda x:x[0].lower()):
            idx=len(files); files.append([sidx(fname),INVALID,user])
            if prev_file is None: first_file=idx
            else: files[prev_file][1]=idx
            prev_file=idx
        dirs[node.idx]=[ni,first_child,dirs[node.idx][2],first_file]
        for j,ch in enumerate(children):
            if j+1<len(children): dirs[ch.idx][2]=children[j+1].idx
            fill(ch)
    fill(root)
    out=bytearray(fstring_write(mount))
    out+=struct.pack('<i',len(dirs))
    for e in dirs: out+=struct.pack('<4I',*e)
    out+=struct.pack('<i',len(files))
    for e in files: out+=struct.pack('<3I',*e)
    out+=struct.pack('<i',len(strings))
    for s in strings: out+=fstring_write(s)
    p=parse_dir_index(bytes(out))
    if p['paths'] != dict(path_to_chunk):
        if set(p['paths'].items()) != set(path_to_chunk.items()):
            raise ValueError('directory index roundtrip mismatch')
    return bytes(out)

def build_container_header(orig_header_data, selected_package_ids, extra_entries=None):
    h=parse_container_header(orig_header_data)
    byid={e['package_id']:e for e in h['entries']}
    if extra_entries: byid.update(extra_entries)
    missing=[x for x in selected_package_ids if x not in byid]
    if missing: raise ValueError('missing store entries '+','.join(hex(x) for x in missing))
    pids=sorted(selected_package_ids)
    store=bytearray(len(pids)*16)
    for i,pid in enumerate(pids):
        deps=byid[pid]['imports']
        rel=(len(store)-i*16) if deps else 0
        struct.pack_into('<IIII',store,i*16,len(deps),rel,0,0)
        if deps: store+=struct.pack('<'+'Q'*len(deps),*deps)
    out=bytearray(struct.pack('<IIQI',0x496f436e,h['version'],h['container_id'],len(pids)))
    if pids: out+=struct.pack('<'+'Q'*len(pids),*pids)
    out+=struct.pack('<I',len(store))+store
    out+=struct.pack('<5I',0,0,0,0,0)+b'\0'
    out+=bytes((-len(out))%16)
    nh=parse_container_header(bytes(out))
    if nh['package_ids']!=pids or nh['package_count']!=len(pids): raise AssertionError
    return bytes(out)

def pack_u24le(x): return bytes((x&255,(x>>8)&255,(x>>16)&255))
def pack_u40le(x): return x.to_bytes(5,'little')
def pack_u40be(x): return x.to_bytes(5,'big')

def write_iostore(orig_utoc, orig_ucas, selected_paths, out_utoc, out_ucas, extra_store_entries=None):
    toc=parse_utoc(orig_utoc); ucas=Path(orig_ucas).read_bytes()
    old_datas=[extract_chunk(toc,ucas,i) for i in range(toc['n'])]
    header_old_idx=[i for i,c in enumerate(toc['chunk_ids']) if c[-1]==6]
    if len(header_old_idx)!=1: raise ValueError('expected one container header')
    header_old_idx=header_old_idx[0]
    path_to_old=toc['dir']['paths']
    missing=[p for p in selected_paths if p not in path_to_old]
    if missing: raise ValueError('missing paths '+repr(missing[:5]))
    selected_old=set(path_to_old[p] for p in selected_paths)
    selected_pids={int.from_bytes(toc['chunk_ids'][i][:8],'little') for i in selected_old}
    new_header=build_container_header(old_datas[header_old_idx], selected_pids, extra_store_entries)
    old_order=[i for i in range(toc['n']) if i in selected_old or i==header_old_idx]
    new_chunk_ids=[]; new_datas=[]; old_to_new={}
    for oldi in old_order:
        newi=len(new_datas); old_to_new[oldi]=newi
        new_chunk_ids.append(toc['chunk_ids'][oldi])
        new_datas.append(new_header if oldi==header_old_idx else old_datas[oldi])
    new_path_map={p:old_to_new[path_to_old[p]] for p in selected_paths}
    dirraw=build_dir_index(new_path_map,toc['dir']['mount'])
    bs=toc['block_size']; phys=0; blocks=[]; offs=[]; outdata=bytearray()
    for d in new_datas:
        start_block=len(blocks)
        offs.append((start_block*bs,len(d)))
        pos=0
        while pos<len(d):
            blk=d[pos:pos+bs]
            outdata+=blk
            blocks.append((phys,len(blk),len(blk),0))
            phys+=len(blk); pos+=len(blk)
    hdr=bytearray(toc['header_raw'])
    struct.pack_into('<I',hdr,0x18,len(new_datas))
    struct.pack_into('<I',hdr,0x1c,len(blocks))
    struct.pack_into('<I',hdr,0x30,len(dirraw))
    struct.pack_into('<I',hdr,0x54,0)
    struct.pack_into('<I',hdr,0x60,0)
    body=bytearray(hdr)
    for c in new_chunk_ids: body+=c
    for o,l in offs: body+=pack_u40be(o)+pack_u40be(l)
    for po,cs,us,method in blocks: body+=pack_u40le(po)+pack_u24le(cs)+pack_u24le(us)+bytes([method])
    body+=dirraw
    for d in new_datas: body+=blake3(d,32)[:20]+b'\0\0\0\0'
    Path(out_ucas).write_bytes(outdata); Path(out_utoc).write_bytes(body)
    from iostore_simple import validate
    nt,nd,info=validate(out_utoc,out_ucas,False)
    if info['bad_hashes'] or not info['block_cover_exact'] or info['paths']!=len(selected_paths): raise AssertionError(info)
    nhi=[i for i,c in enumerate(nt['chunk_ids']) if c[-1]==6][0]
    nh=parse_container_header(nd[nhi])
    dirpids={int.from_bytes(nt['chunk_ids'][idx][:8],'little') for idx in nt['dir']['paths'].values()}
    if set(nh['package_ids'])!=dirpids: raise AssertionError(('header pids mismatch',len(nh['package_ids']),len(dirpids)))
    report={
      'selected_path_count':len(selected_paths),'toc_entry_count':nt['n'],'compression_block_count':nt['m'],
      'directory_file_count':len(nt['dir']['paths']),'container_package_count':nh['package_count'],
      'all_chunk_hashes_valid':not info['bad_hashes'],'ucas_physical_cover_exact':info['block_cover_exact'],
      'utoc_sha256':hashlib.sha256(Path(out_utoc).read_bytes()).hexdigest(),
      'ucas_sha256':hashlib.sha256(Path(out_ucas).read_bytes()).hexdigest(),
      'removed_path_count':len(path_to_old)-len(selected_paths),
      'removed_paths':sorted(set(path_to_old)-set(selected_paths)),
      'retained_paths':sorted(selected_paths),
    }
    return report

if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('utoc');ap.add_argument('ucas');ap.add_argument('paths_json');ap.add_argument('out_utoc');ap.add_argument('out_ucas')
    a=ap.parse_args(); paths=json.load(open(a.paths_json))
    print(json.dumps(write_iostore(a.utoc,a.ucas,paths,a.out_utoc,a.out_ucas),indent=2))
