from PIL import Image
def load(path):
    im=Image.open(path); desc=im.info.get('Description',''); im=im.convert('RGBA')
    w=h=32; states=[]; cur=None
    for line in desc.splitlines():
        s=line.strip()
        if s.startswith('width ='): w=int(s.split('=')[1])
        elif s.startswith('height ='): h=int(s.split('=')[1])
        elif s.startswith('state ='):
            cur={'name':s.split('=',1)[1].strip().strip('"'),'dirs':1,'frames':1}; states.append(cur)
        elif cur and s.startswith('dirs ='): cur['dirs']=int(s.split('=')[1])
        elif cur and s.startswith('frames ='): cur['frames']=int(s.split('=')[1])
    cols=im.width//w; idx=0; out={}
    for st in states:
        n=st['dirs']*st['frames']; icons=[]
        for i in range(idx,idx+n):
            x=(i%cols)*w; y=(i//cols)*h; icons.append(im.crop((x,y,x+w,y+h)))
        idx+=n
        # BYOND order: frame-major, dirs S,N,E,W
        out.setdefault(st['name'],{'dirs':st['dirs'],'frames':st['frames'],'icons':icons})
    return out
def frame(st,d,f=0):
    order={'S':0,'N':1,'E':2,'W':3}
    return st['icons'][f*st['dirs']+(order[d] if st['dirs']>1 else 0)]
