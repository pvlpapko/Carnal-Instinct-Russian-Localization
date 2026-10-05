import json,struct,sys,types
from pathlib import Path
ROOT=Path(__import__('os').environ.get('CI_RU_RELEASE_WORKSPACE', sys.argv[1] if len(sys.argv)>1 else str(Path(__file__).resolve().parents[3])))
sys.path.insert(0,str(ROOT/'Developer/SafeUIFix/tools'));import cityhash_pure
shim=types.ModuleType('cityhash');shim.CityHash64=cityhash_pure.CityHash64;sys.modules['cityhash']=shim
sys.path.insert(0,str(ROOT/'Developer/MapFix'));import zen
SCHEMA=json.loads(Path(__file__).with_name('native_schema.json').read_text())
CLASS={0x53e9771079198ff9:'SizeBox',0x6f37994b3fc8d22d:'TextBlock',0x4f870d939e710a92:'CanvasPanelSlot',0x78de084bde67c823:'HorizontalBoxSlot',0x4ee71527e2182c0f:'SizeBoxSlot'}
NATIVE={'/Script/CoreUObject.Vector2D':'2d','/Script/CoreUObject.Vector':'3d','/Script/CoreUObject.LinearColor':'4f','/Script/CoreUObject.Guid':'4I'}
def fields(cls):
 d=SCHEMA[cls];return d['properties']+(fields(d['super']) if d.get('super') else [])
def header(b,p):
 index=0;out=[];flags=[]
 while True:
  v=struct.unpack_from('<H',b,p)[0];p+=2;index+=v&127;n=v>>9
  out.extend(range(index,index+n));flags.extend([bool(v&128)]*n);index+=n
  if v&256:break
 zc=sum(flags);zeros=set()
 if zc:
  n=1 if zc<=8 else 2 if zc<=16 else ((zc+31)//32)*4
  bitmap=int.from_bytes(b[p:p+n],'little');p+=n;k=0
  for i,flag in zip(out,flags):
   if flag:
    if bitmap&(1<<k):zeros.add(i)
    k+=1
 return out,zeros,p

def fstr(b,p):
 n=struct.unpack_from('<i',b,p)[0];p+=4
 if not n:return '',p
 z=abs(n)*(2 if n<0 else 1);assert z<10000000 and p+z<=len(b)
 raw=b[p:p+z];s=raw[:-2].decode('utf-16-le') if n<0 else raw[:-1].decode('utf8');return s,p+z

def value(b,p,t,names):
 typ=t['type']
 if typ in ['FloatProperty','DoubleProperty','IntProperty','UInt32Property','ObjectProperty','SoftObjectProperty','WeakObjectProperty','BoolProperty','ByteProperty','EnumProperty','NameProperty','Int64Property','UInt64Property']:
  fmt={'FloatProperty':'f','DoubleProperty':'d','IntProperty':'i','UInt32Property':'I','ObjectProperty':'i','SoftObjectProperty':'i','WeakObjectProperty':'i','BoolProperty':'B','ByteProperty':'B','EnumProperty':'B','NameProperty':'2I','Int64Property':'q','UInt64Property':'Q'}[typ]
  vals=struct.unpack_from('<'+fmt,b,p);v=vals[0] if len(vals)==1 else vals
  if typ=='NameProperty':v=names[vals[0]]+('_'+str(vals[1]-1) if vals[1] else '')
  return v,p+struct.calcsize('<'+fmt)
 if typ=='StrProperty':return fstr(b,p)
 if typ=='TextProperty':
  flags,h=struct.unpack_from('<Ib',b,p);p+=5
  if h==0:
   ns,p=fstr(b,p);k,p=fstr(b,p);s,p=fstr(b,p);return {'ns':ns,'key':k,'source':s},p
  if h==11:
   ti,tn=struct.unpack_from('<II',b,p);p+=8;k,p=fstr(b,p);return {'table':names[ti],'key':k},p
  if h==-1:
   has=struct.unpack_from('<i',b,p)[0];p+=4
   if has:s,p=fstr(b,p);return {'invariant':s},p
   return {'empty':True},p
  raise ValueError(('ftext history',h,p))
 if typ=='StructProperty':
  cls=t['struct']
  if cls in NATIVE:
   fmt=NATIVE[cls];return struct.unpack_from('<'+fmt,b,p),p+struct.calcsize('<'+fmt)
  return obj(b,p,cls,names)
 if typ=='ArrayProperty':
  n=struct.unpack_from('<i',b,p)[0];p+=4;assert 0<=n<100000
  out=[]
  for _ in range(n):
   v,p=value(b,p,t['inner'],names);out.append(v)
  return out,p
 if typ=='DelegateProperty':return b[p:p+12].hex(),p+12
 raise ValueError(('unsupported',typ,t))
def obj(b,p,cls,names):
 fs=fields(cls);ids,zero,p=header(b,p);out={}
 for i in ids:
  t=fs[i];s=p
  if i in zero:v=0
  else:v,p=value(b,p,t,names)
  out[t['name']]={'value':v,'start':s,'end':p,'index':i,'zero':i in zero}
 return out,p

def describe(path):
 p=zen.package(path);out=[]
 for e in p['exports']:
  c=CLASS.get(e['cls'])
  if not c:continue
  raw=p['bytes'][e['start']:e['end']]
  try:
   v,end=obj(raw,0,'/Script/UMG.'+c,p['names']);assert raw[end:]==b'\0'*4,('trailing',raw[end:].hex());out.append({'index':e['index'],'name':e['name'],'class':c,'properties':v,'outer':e['outer']})
  except Exception as ex:out.append({'index':e['index'],'name':e['name'],'class':c,'error':str(ex),'hex':raw.hex()})
 return out
