"""Schema-directed UMG editing. Existing gameplay exports and indices stay stable."""
import copy, struct
from pathlib import Path
from inspect_native import ui, cf, props, is_widget
from display_tools import header, sha

def plain(v):
    if isinstance(v,dict):
        if 'value' in v and 'index' in v:return plain(v['value'])
        return {k:plain(x) for k,x in v.items()}
    if isinstance(v,(list,tuple)):return [plain(x) for x in v]
    return v

def imports(p):
    h=p['header'];b=p['bytes']
    hashes=list(struct.unpack('<'+'Q'*((h[7]-h[6])//8),b[h[6]:h[7]]))
    mapping=list(struct.unpack('<'+'Q'*((h[8]-h[7])//8),b[h[7]:h[8]]))
    return hashes,mapping,cf.zen_info(b)['imports']

def resource(p,ref):
    hashes,mapping,names=imports(p);ident=mapping[-ref-1]
    if ident>>62==1:return ('script',ident)
    assert ident>>62==2
    return ('package',names[(ident>>32)&0x3fffffff],hashes[ident&0xffffffff])

class Edit:
    def __init__(self,path):
        self.p=ui.zen.package(path);self.exports=copy.deepcopy(self.p['exports'])
        self.data={e['index']:self.p['bytes'][e['start']:e['end']] for e in self.exports}
        self.names=list(self.p['names']);self.hashes,self.import_map,self.packages=imports(self.p)
        self.evidence=[];self.changed=set()

    def export(self,name):
        es=[e for e in self.exports if e['name']==name];assert len(es)==1,(name,len(es));return es[0]

    def name(self,name):
        if name not in self.names:self.names.append(name)
        return self.names.index(name)

    def import_resource(self,source,ref):
        r=resource(source,ref)
        if r[0]=='script':ident=r[1]
        else:
            _,pkg,ph=r
            if pkg not in self.packages:self.packages.append(pkg)
            if ph not in self.hashes:self.hashes.append(ph)
            ident=(2<<62)|(self.packages.index(pkg)<<32)|self.hashes.index(ph)
        if ident not in self.import_map:self.import_map.append(ident)
        return -(self.import_map.index(ident)+1)

    def encode(self,v,f):
        t=f['type'];formats={'BoolProperty':'B','ByteProperty':'B','EnumProperty':'B','FloatProperty':'f',
                            'DoubleProperty':'d','IntProperty':'i','ObjectProperty':'i','UInt32Property':'I'}
        if t in formats:return struct.pack('<'+formats[t],v)
        if t=='NameProperty':return struct.pack('<II',self.name(v),0)
        if t=='ArrayProperty':return struct.pack('<i',len(v))+b''.join(self.encode(x,f['inner']) for x in v)
        if t=='StructProperty':
            if f['struct'] in ui.NATIVE:return struct.pack('<'+ui.NATIVE[f['struct']],*v)
            return self.object(v,f['struct'])
        raise ValueError(f)

    def object(self,v,cls):
        fs=ui.fields(cls);items=[(i,self.encode(v[f['name']],f)) for i,f in enumerate(fs) if f['name'] in v]
        assert len(items)==len(v),(cls,v.keys())
        return header([(i,False) for i,_ in items])+b''.join(b for _,b in items)

    def values(self,e):
        if isinstance(e,str):e=self.export(e)
        raw=self.data[e['index']];v,end=ui.obj(raw,0,'/Script/UMG.'+ui.CLASS[e['cls']],self.names)
        assert raw[end:]==b'\0'*4,(e['name'],raw[end:].hex())
        return v

    def set_raw(self,e,key,raw,zero=False):
        if isinstance(e,str):e=self.export(e)
        v=self.values(e);fs=ui.fields('/Script/UMG.'+ui.CLASS[e['cls']])
        idx=next(i for i,f in enumerate(fs) if f['name']==key)
        original=self.data[e['index']]
        items=[(x['index'],x['zero'],original[x['start']:x['end']]) for k,x in v.items() if k!=key]+[(idx,zero,raw)]
        items.sort();self.data[e['index']]=header([(i,z) for i,z,_ in items])+b''.join(b for _,_,b in items)+b'\0'*4
        self.changed.add(e['index']);self.values(e)

    def set(self,e,key,value):
        if isinstance(e,str):e=self.export(e)
        v=self.values(e);old=plain(v.get(key,{}))
        if old==value:return
        f=next(x for x in ui.fields('/Script/UMG.'+ui.CLASS[e['cls']]) if x['name']==key)
        self.set_raw(e,key,self.encode(value,f));self.evidence.append({'export':e['name'],'field':key,'old':old,'new':value})

    def custom_visibility(self,name,value):
        """Bound the inherited Slot against its native parent before adding Visibility.

        Infer the inherited field offset only when the full typed native suffix
        ends exactly at the UObject trailer and Slot matches the parent graph.
        Custom fields and their raw FText records are never reserialized.
        """
        e=self.export(name);raw=self.data[e['index']]
        ids,zero,end=ui.header(raw,0)
        slots=[s for s in self.exports if s['cls'] in ui.CLASS and ui.CLASS[s['cls']].endswith('Slot')
               and plain(self.values(s)).get('Content')==e['index']+1]
        assert len(slots)==1,(name,'native parent',len(slots))
        ref=slots[0]['index']+1
        fs=ui.fields('/Script/UMG.UserWidget')
        slotidx=next(i for i,f in enumerate(fs) if f['name']=='Slot')
        visidx=next(i for i,f in enumerate(fs) if f['name']=='Visibility')
        candidates=[];positions=[i for i in range(end,len(raw)-7) if raw[i:i+4]==struct.pack('<i',ref)]
        for start in positions:
            for j,fieldidx in enumerate(ids):
                offset=fieldidx-slotidx
                if offset<0 or fieldidx in zero:continue
                cursor=start;records=[]
                try:
                    for index in ids[j:]:
                        f=fs[index-offset];assert index-offset>=slotidx
                        before=cursor
                        if index not in zero:_,cursor=ui.value(raw,cursor,f,self.names)
                        records.append((index,index in zero,raw[before:cursor]))
                    assert cursor==len(raw)-4 and raw[-4:]==b'\0'*4
                    candidates.append((j,start,offset,records))
                except (AssertionError,IndexError,KeyError,ValueError,struct.error):pass
        assert len(candidates)==1,(name,'bounded native suffix',len(candidates))
        j,start,offset,records=candidates[0];idx=visidx+offset
        if any(i==idx and not z and v==bytes([value]) for i,z,v in records):return
        records=[x for x in records if x[0]!=idx]+[(idx,False,bytes([value]))];records.sort()
        allids=[(i,i in zero) for i in ids[:j]]+[(i,z) for i,z,_ in records]
        self.data[e['index']]=header(allids)+raw[end:start]+b''.join(v for _,_,v in records)+b'\0'*4
        check=ui.header(self.data[e['index']],0);assert check[0]==[i for i,_ in allids]
        self.changed.add(e['index']);self.evidence.append({'export':name,'inherited_slot_index':ids[j],'visibility_index':idx,'visibility':value,'slot_ref':ref,'typed_native_suffix':'PASS'})

    def add(self,name,cls,outer,values):
        ident=next(i for i,n in ui.CLASS.items() if n==cls)
        path='/script/umg/default__'+cls.lower()
        template=(cf.CityHash64(path.encode('utf-16-le'))&((1<<62)-1))|(1<<62)
        i=len(self.exports)
        self.exports.append({'index':i,'name':name,'outer':outer,'cls':ident,'super':(1<<64)-1,'template':template,'flags':8})
        self.data[i]=self.object(values,'/Script/UMG.'+cls)+b'\0'*4;self.name(name);self.changed.add(i);self.values(self.exports[i])
        return i+1

    def class_to(self,name,cls):
        e=self.export(name);old=ui.CLASS[e['cls']]
        assert ui.fields('/Script/UMG.'+old)==ui.fields('/Script/UMG.'+cls),(old,cls)
        e['cls']=next(i for i,n in ui.CLASS.items() if n==cls)
        e['template']=(cf.CityHash64(('/script/umg/default__'+cls.lower()).encode('utf-16-le'))&((1<<62)-1))|(1<<62)
        self.changed.add(e['index']);self.values(e)
        self.evidence.append({'export':name,'old_class':old,'new_class':cls})

    def fixed_canvas(self):
        tree=self.export('WidgetTree')['index'];scale=self.export('ScaleBox_0')
        ss=self.exports[plain(self.values(scale))['Slots'][0]-1]
        old=plain(self.values(ss))['Content'];old_widget=self.exports[old-1]
        size=self.add('CI_RU_ViewportSize','SizeBox',tree,{'WidthOverride':1920.,'HeightOverride':1080.,
                'bOverride_WidthOverride':1,'bOverride_HeightOverride':1,'Slot':ss['index']+1})
        slot=self.add('CI_RU_ViewportSlot','SizeBoxSlot',size-1,{'Parent':size,'Content':old,'HorizontalAlignment':0,'VerticalAlignment':0})
        self.set(self.exports[size-1],'Slots',[slot]);self.set(ss,'Content',size);self.set(old_widget,'Slot',slot)

    def finish(self,path):
        p=self.p;h=p['header'];b=p['bytes'];nold=len(p['exports']);n=len(self.exports)
        assert h[10]-h[9]==16*nold and h[11]-h[10]==20*nold
        name_batch=ui.zen.append_name_batch(b,p['names'],self.names[len(p['names']):])
        pieces=[b[:52]+name_batch+b[p['name_end']:h[6]],struct.pack('<'+'Q'*len(self.hashes),*self.hashes),
                struct.pack('<'+'Q'*len(self.import_map),*self.import_map)]
        exportmap=bytearray();output=bytearray()
        for e in self.exports:
            if e['index']<nold:
                entry=bytearray(b[e['entry']:e['entry']+72])
            else:
                entry=bytearray(72);struct.pack_into('<II',entry,16,self.name(e['name']),0)
            data=self.data[e['index']]
            struct.pack_into('<QQ',entry,0,len(output),len(data))
            struct.pack_into('<QQQQ',entry,24,e['outer'],e['cls'],e['super'],e['template'])
            struct.pack_into('<I',entry,64,e['flags']);exportmap+=entry;output+=data
        pieces.append(bytes(exportmap))
        bundles=b[h[9]:h[10]]+b''.join(struct.pack('<II',i,c) for i in range(nold,n) for c in (0,1))
        pieces.append(bundles)
        oldentries=list(struct.unpack('<'+'i'*((h[12]-h[11])//4),b[h[11]:h[12]]));entries=[];depheaders=[]
        for e in self.exports:
            if e['index']<nold:
                first,*counts=struct.unpack_from('<i4I',b,h[10]+20*e['index']);old=oldentries[first:first+sum(counts)] if sum(counts) else []
                groups=[];pos=0
                for count in counts:groups.append(old[pos:pos+count]);pos+=count
                # New visual objects must exist before any old template serializes them.
                groups[2]+=list(range(nold+1,n+1))
            else:
                groups=[[e['outer']+1] if e['outer']>>62==0 else [],[],list(range(1,n+1)),[]]
            depheaders.append((len(entries),*[len(g) for g in groups]));entries.extend(x for g in groups for x in g)
        pieces.append(b''.join(struct.pack('<i4I',*x) for x in depheaders))
        pieces.append(struct.pack('<'+'i'*len(entries),*entries))
        oldnames,oldend=ui.zen.names_at(b,h[12]);nums=b[oldend:oldend+4*len(oldnames)]
        pkg_batch=ui.zen.append_name_batch(b[h[12]-52:],oldnames,self.packages[len(oldnames):])
        pieces.append(pkg_batch+nums+b'\0'*4*(len(self.packages)-len(oldnames)))
        cursor=len(pieces[0]);nh=list(h)
        for i,part in enumerate(pieces[1:],6):nh[i]=cursor;cursor+=len(part)
        nh[1]=cursor
        out=bytearray(b''.join(pieces));struct.pack_into('<13I',out,0,*nh);out+=output+b[h[1]+max(e['serial']+e['size'] for e in p['exports']):]
        path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(out)
        q=ui.zen.package(path)
        assert len(q['exports'])==n and q['names'][:len(p['names'])]==p['names']
        for e in q['exports']:
            assert q['bytes'][e['start']:e['end']]==self.data[e['index']]
            if is_widget(e):props(q,e)
            if e['index']<nold and e['index'] not in self.changed:
                o=p['exports'][e['index']];assert b[o['start']:o['end']]==q['bytes'][e['start']:e['end']]
        return {'source_sha256':sha(b),'patched_sha256':sha(bytes(out)),'source_header':h[1],'patched_header':nh[1],
                'source_exports':nold,'patched_exports':n,'changed_exports':sorted(self.changed),'evidence':self.evidence}
