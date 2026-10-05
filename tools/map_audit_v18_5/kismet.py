from dataclasses import dataclass, field
import struct

@dataclass
class Raw:
    data: bytes
    memory: int
@dataclass
class Target:
    old: int
@dataclass
class Expr:
    op:int
    parts:list=field(default_factory=list)
    old:int|None=None
    old_end:int|None=None
    object:object=None
    context:object=None
    pointer:object=None
    cases:list=field(default_factory=list)
    index:object=None
    default:object=None
    target:object=None
    def children(self):
        if self.op==0x69:
            return [self.index]+[x for kv in self.cases for x in kv]+[self.default]
        if self.op in (0x19,0x1a): return [self.object,self.context]
        return [x for x in self.parts if isinstance(x,Expr)]

def walk(e):
    yield e
    for c in e.children():yield from walk(c)

class Reader:
    def __init__(self,data):self.data=data;self.p=0;self.m=0;self.targets=[]
    def raw(self,n,memory=None):
        if self.p+n>len(self.data):raise EOFError((self.p,n,len(self.data)))
        x=Raw(self.data[self.p:self.p+n], n if memory is None else memory)
        self.p+=n;self.m+=x.memory;return x
    def u8(self):return self.raw(1).data[0]
    def uint(self,n):return int.from_bytes(self.raw(n).data,'little')
    def i32raw(self):return self.raw(4,8)
    def fname(self):return self.raw(8,12)
    def pointer(self):
        start=self.p;before=self.m
        count=self.uint(4)
        if count>64:raise ValueError(('field path count',start,count))
        self.raw(8*count+4)
        disk=self.data[start:self.p]
        self.m=before+8
        return Raw(disk,8)
    def target(self):
        t=Target(self.uint(4));self.targets.append(t);return t
    def expr(self):
        old=self.m;op=self.u8();e=Expr(op,old=old)
        # variables
        if op in (0x00,0x01,0x02,0x48,0x6c): e.parts=[self.pointer()]
        elif op in (0x0b,0x16,0x17,0x25,0x26,0x27,0x28,0x2a,0x2d,0x30,0x32,0x3a,0x3c,0x3e,0x40,0x4d,0x50,0x53,0x5a,0x5e,0x66): pass
        elif op==0x04: e.parts=[self.expr()]
        elif op==0x06: e.parts=[self.target()]
        elif op==0x07: e.parts=[self.target(),self.expr()]
        elif op==0x0f: e.parts=[self.pointer(),self.expr(),self.expr()]
        elif op==0x11:e.parts=[self.pointer(),self.raw(1)]
        elif op in (0x14,0x43,0x44,0x5c,0x5f,0x60,0x62):e.parts=[self.expr(),self.expr()]
        elif op in (0x19,0x1a):
            e.object=self.expr();skip=self.uint(4);e.pointer=self.pointer();cstart=self.m;e.context=self.expr()
            if self.m-cstart!=skip:raise ValueError(('context skip',old,skip,self.m-cstart))
        elif op in (0x1b,0x45):
            e.parts=[self.fname()]
            while True:
                x=self.expr();e.parts.append(x)
                if x.op==0x16:break
        elif op in (0x1c,0x46,0x68):
            e.parts=[self.i32raw()]
            while True:
                x=self.expr();e.parts.append(x)
                if x.op==0x16:break
        elif op in (0x1d,0x1e):e.parts=[self.raw(4)]
        elif op in (0x24,0x2c):e.parts=[self.raw(1)]
        elif op in (0x35,0x36,0x37):e.parts=[self.raw(8)]
        elif op==0x38:e.parts=[self.raw(1),self.expr()]
        elif op==0x20:e.parts=[self.i32raw()]
        elif op in (0x13,0x2e,0x52,0x54,0x55):e.parts=[self.i32raw(),self.expr()]
        elif op==0x21:e.parts=[self.fname()]
        elif op in (0x1f,0x34):
            start=self.p;before=self.m;unit=1 if op==0x1f else 2
            while True:
                x=self.raw(unit)
                if x.data==b'\0'*unit:break
            e.parts=[Raw(self.data[start:self.p],self.m-before)]
        elif op==0x29:
            kind=self.u8();e.parts=[Raw(bytes([kind]),1)]
            if kind==1:e.parts += [self.expr(),self.expr(),self.expr()]
            elif kind in (2,3):e.parts += [self.expr()]
            elif kind==4:e.parts += [self.i32raw(),self.expr(),self.expr()]
            elif kind!=0:raise ValueError(('text kind',kind,old))
        elif op==0x31:
            e.parts=[self.expr()]
            while True:
                x=self.expr();e.parts.append(x)
                if x.op==0x32:break
        elif op==0x2f:
            e.parts=[self.i32raw(),self.raw(4)]
            while True:
                x=self.expr();e.parts.append(x)
                if x.op==0x30:break
        elif op==0x42:e.parts=[self.pointer(),self.expr()]
        elif op==0x4c:e.parts=[self.target()]
        elif op==0x4e:e.parts=[self.expr()]
        elif op in (0x4f,0x51):e.parts=[self.expr()]
        elif op==0x5b:e.parts=[self.target()]
        elif op==0x61:e.parts=[self.fname(),self.expr(),self.expr()]
        elif op==0x64:e.parts=[self.pointer(),self.expr()]
        elif op==0x69:
            count=self.uint(2);end=self.target();e.index=self.expr()
            for _ in range(count):
                k=self.expr();nxt=self.target();v=self.expr();e.cases.append((k,v))
                if nxt.old!=self.m:raise ValueError(('switch next',old,nxt.old,self.m))
            e.default=self.expr()
            if end.old!=self.m:raise ValueError(('switch end',old,end.old,self.m))
        else:raise ValueError(f'unsupported opcode {op:#x} disk={self.p-1} memory={old}')
        e.old_end=self.m;return e
    def all(self):
        out=[]
        while self.p<len(self.data):out.append(self.expr())
        if not out or out[-1].op!=0x53:raise ValueError('script no EndOfScript')
        return out

def memory_size(x):
    if isinstance(x,Raw):return x.memory
    if isinstance(x,Target):return 4
    if x.op==0x69:
        return 1+2+4+memory_size(x.index)+sum(memory_size(k)+4+memory_size(v) for k,v in x.cases)+memory_size(x.default)
    if x.op in (0x19,0x1a):return 1+memory_size(x.object)+4+8+memory_size(x.context)
    return 1+sum(memory_size(p) for p in x.parts)

class Writer:
    def __init__(self,mapping=None):self.out=bytearray();self.m=0;self.mapping={} if mapping is None else mapping;self.record=mapping is None
    def raw(self,x):self.out.extend(x.data);self.m+=x.memory
    def uint(self,v,n):self.raw(Raw(int(v).to_bytes(n,'little'),n))
    def target(self,t):
        if self.record:self.uint(0,4)
        else:
            if t.old not in self.mapping:raise KeyError(('target missing',t.old,sorted(self.mapping)[-20:]))
            self.uint(self.mapping[t.old],4)
    def emit(self,e):
        if isinstance(e,Raw):self.raw(e);return
        if isinstance(e,Target):self.target(e);return
        if self.record and e.old is not None:self.mapping[e.old]=self.m
        self.uint(e.op,1)
        if e.op==0x69:
            self.uint(len(e.cases),2)
            # Switch end offset is the absolute VM/iCode address immediately after default.
            end = self.m + 4 + memory_size(e.index) + sum(memory_size(k)+4+memory_size(v) for k,v in e.cases) + memory_size(e.default)
            self.uint(end,4)
            self.emit(e.index)
            for k,v in e.cases:
                self.emit(k)
                # next offset is immediately after v; writer first pass can know by size, second writes absolute memory addr
                if self.record:self.uint(0,4)
                else:self.uint(self.m+4+memory_size(v),4)
                self.emit(v)
            self.emit(e.default)
        elif e.op in (0x19,0x1a):
            self.emit(e.object);self.uint(memory_size(e.context),4);self.emit(e.pointer);self.emit(e.context)
        else:
            for p in e.parts:self.emit(p)
        if self.record and e.old_end is not None:self.mapping[e.old_end]=self.m

def serialize(nodes):
    a=Writer()
    for n in nodes:a.emit(n)
    b=Writer(a.mapping)
    for n in nodes:b.emit(n)
    if b.m!=a.m:raise AssertionError((a.m,b.m))
    return bytes(b.out),b.m,a.mapping

def string(value):
    ascii=value.isascii();enc='ascii' if ascii else 'utf-16-le';raw=value.encode(enc)+(b'\0' if ascii else b'\0\0')
    return Expr(0x1f if ascii else 0x34,[Raw(raw,len(raw))])
def text(source,key,namespace):return Expr(0x29,[Raw(b'\x01',1),string(source),string(key),string(namespace)])
def name(index):return Expr(0x21,[Raw(struct.pack('<II',index,0),12)])
def instance_var(pointer_raw):return Expr(0x01,[pointer_raw])
def callmath(import_index,params):return Expr(0x68,[Raw(struct.pack('<i',-(import_index+1)),8),*params,Expr(0x16)])
