import struct
IV = [0x6A09E667,0xBB67AE85,0x3C6EF372,0xA54FF53A,0x510E527F,0x9B05688C,0x1F83D9AB,0x5BE0CD19]
MSG_PERMUTATION=[2,6,3,10,7,0,4,13,1,11,12,5,9,14,15,8]
CHUNK_START=1; CHUNK_END=2; PARENT=4; ROOT=8
MASK=0xffffffff

def rotr32(x,n): return ((x>>n)|(x<<(32-n))) & MASK

def g(s,a,b,c,d,mx,my):
    s[a]=(s[a]+s[b]+mx)&MASK; s[d]=rotr32(s[d]^s[a],16)
    s[c]=(s[c]+s[d])&MASK; s[b]=rotr32(s[b]^s[c],12)
    s[a]=(s[a]+s[b]+my)&MASK; s[d]=rotr32(s[d]^s[a],8)
    s[c]=(s[c]+s[d])&MASK; s[b]=rotr32(s[b]^s[c],7)

def round_fn(s,m):
    g(s,0,4,8,12,m[0],m[1]); g(s,1,5,9,13,m[2],m[3]); g(s,2,6,10,14,m[4],m[5]); g(s,3,7,11,15,m[6],m[7])
    g(s,0,5,10,15,m[8],m[9]); g(s,1,6,11,12,m[10],m[11]); g(s,2,7,8,13,m[12],m[13]); g(s,3,4,9,14,m[14],m[15])

def compress(cv, block_words, counter, block_len, flags):
    s=list(cv)+IV[:4]+[counter & MASK,(counter>>32)&MASK,block_len,flags]
    m=list(block_words)
    for r in range(7):
        round_fn(s,m)
        if r != 6: m=[m[i] for i in MSG_PERMUTATION]
    return [(s[i]^s[i+8])&MASK for i in range(8)] + [(s[i+8]^cv[i])&MASK for i in range(8)]

def words_from_block(block):
    return list(struct.unpack('<16I', block.ljust(64,b'\0')))

class Output:
    def __init__(self,input_cv,block_words,counter,block_len,flags):
        self.input_cv=list(input_cv); self.block_words=list(block_words); self.counter=counter; self.block_len=block_len; self.flags=flags
    def chaining_value(self):
        return compress(self.input_cv,self.block_words,self.counter,self.block_len,self.flags)[:8]
    def root_output_bytes(self,n=32):
        out=bytearray(); oc=0
        while len(out)<n:
            words=compress(self.input_cv,self.block_words,oc,self.block_len,self.flags|ROOT)
            out += struct.pack('<16I',*words)
            oc += 1
        return bytes(out[:n])

def chunk_output(chunk, chunk_counter, key=IV, flags=0):
    assert len(chunk)<=1024
    if len(chunk)==0:
        blocks=[b'']
    else:
        blocks=[chunk[i:i+64] for i in range(0,len(chunk),64)]
    cv=list(key)
    for i,block in enumerate(blocks[:-1]):
        f=flags | (CHUNK_START if i==0 else 0)
        cv=compress(cv,words_from_block(block),chunk_counter,len(block),f)[:8]
    i=len(blocks)-1; block=blocks[-1]
    f=flags | CHUNK_END | (CHUNK_START if i==0 else 0)
    return Output(cv,words_from_block(block),chunk_counter,len(block),f)

def parent_output(left_cv,right_cv,key=IV,flags=0):
    return Output(key,list(left_cv)+list(right_cv),0,64,flags|PARENT)

def blake3(data:bytes,n=32):
    if not data:
        chunks=[b'']
    else:
        chunks=[data[i:i+1024] for i in range(0,len(data),1024)]
    stack=[]
    for i,ch in enumerate(chunks[:-1]):
        cv=chunk_output(ch,i).chaining_value()
        total_chunks=i+1
        while (total_chunks & 1)==0:
            left=stack.pop(); cv=parent_output(left,cv).chaining_value(); total_chunks >>= 1
        stack.append(cv)
    output=chunk_output(chunks[-1],len(chunks)-1)
    for left in reversed(stack):
        output=parent_output(left,output.chaining_value())
    return output.root_output_bytes(n)

if __name__=='__main__':
    tests=[(b'', 'af1349b9f5f9a1a6a0404dea36dcc9499bcb25c9adc112b7cc9a93cae41f3262'),(b'abc','6437b3ac38465133ffb63b75273a8db548c558465d79db03fd359c6cd5bd9d85')]
    for d,e in tests:
        h=blake3(d).hex(); print(repr(d),h,'PASS' if h==e else 'FAIL expected '+e)
