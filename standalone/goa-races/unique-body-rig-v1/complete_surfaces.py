"""Register AI completion art to the approved Elf; retain source pixels exactly.

This is asset preparation, not runtime generation. Only previously transparent
pixels inside authored anatomy masks receive generated, source-palette colors.
"""
from pathlib import Path
from functools import lru_cache
from PIL import Image,ImageDraw
import numpy as np

HERE=Path(__file__).resolve().parent
ART=HERE/'hidden-surfaces-v2/Elf_Completed_Components_AI.png'
TORSO_POLYGONS=[
 [(29,24),(35,24),(41,28),(40,32),(38,36),(38,42),(25,42),(25,36),(22,30),(23,28)],
 [(29,24),(35,24),(42,29),(39,34),(38,42),(25,42),(25,36),(22,30),(24,28)],
 [(32,24),(36,24),(40,28),(41,34),(39,42),(29,42),(28,32),(29,28)],
 [(27,24),(31,24),(35,28),(36,32),(35,42),(24,42),(23,34),(24,28)]
]
BODY_BOXES=[(22,24,43,62),(22,24,43,62),(27,24,42,62),(22,24,37,62)]

def lab(rgb):
    c=np.asarray(rgb,dtype=float)/255
    c=np.where(c<=.04045,c/12.92,((c+.055)/1.055)**2.4)
    r,g,b=c[...,0],c[...,1],c[...,2]
    xyz=np.stack((.4124564*r+.3575761*g+.1804375*b,.2126729*r+.7151522*g+.0721750*b,.0193339*r+.1191920*g+.9503041*b),axis=-1)
    xyz/=np.array([.95047,1,1.08883])
    f=np.where(xyz>(6/29)**3,np.cbrt(xyz),xyz/(3*(6/29)**2)+4/29)
    return np.stack((116*f[...,1]-16,500*(f[...,0]-f[...,1]),200*(f[...,1]-f[...,2])),axis=-1)

def component(im):
    """Ignore transparent gutters and isolated generation specks."""
    a=np.array(im.getchannel('A'))>=128;seen=set();largest=[]
    for y,x in zip(*np.nonzero(a)):
        if (x,y) in seen:continue
        seen.add((x,y));stack=[(x,y)];part=[]
        while stack:
            u,v=stack.pop();part.append((u,v))
            for nx,ny in [(u-1,v),(u+1,v),(u,v-1),(u,v+1)]:
                if 0<=nx<im.width and 0<=ny<im.height and a[ny,nx] and (nx,ny) not in seen:
                    seen.add((nx,ny));stack.append((nx,ny))
        if len(part)>len(largest):largest=part
    assert largest,'Missing generated component'
    x0=min(p[0] for p in largest);y0=min(p[1] for p in largest)
    x1=max(p[0] for p in largest)+1;y1=max(p[1] for p in largest)+1
    out=Image.new('RGBA',(x1-x0,y1-y0))
    for x,y in largest:out.putpixel((x-x0,y-y0),im.getpixel((x,y))[:3]+(255,))
    return out

def segment_distance(x,y,a,b):
    dx,dy=b[0]-a[0],b[1]-a[1]
    t=max(0,min(1,((x-a[0])*dx+(y-a[1])*dy)/max(1,dx*dx+dy*dy)))
    return ((x-a[0]-t*dx)**2+(y-a[1]-t*dy)**2)**.5

class Completion:
    def __init__(self,original):
        self.art=Image.open(ART).convert('RGBA')
        # Exact colors from visible source skin/outline regions; no generated
        # palette entries enter the output. Shorts and hair are never recolored.
        colors=set()
        for d in range(4):
            for y in range(27,42):
                for x in range(18,46):
                    r,g,b,a=original.getpixel((d*64+x,y))
                    if a>=128 and ((r>g*1.09 and g>b*1.08 and b>45) or max(r,g,b)<65):colors.add((r,g,b))
        self.palette=np.array(sorted(colors),dtype=np.uint8)
        assert len(self.palette)>10
        self.palette_lab=lab(self.palette)
        assert np.isfinite(self.palette_lab).all()
        self.stats=[]

    @lru_cache(maxsize=16384)
    def color(self,rgb):
        idx=np.argmin(np.sum((self.palette_lab-lab(rgb))**2,axis=1))
        return tuple(int(x) for x in self.palette[idx])+(255,)

    def cell(self,d,row):
        w,h=self.art.size
        return component(self.art.crop((round(d*w/4),round(row*h/3),round((d+1)*w/4),round((row+1)*h/3))))

    def sample(self,im,x,y):
        x=max(0,min(im.width-1,int(x)));y=max(0,min(im.height-1,int(y)))
        if not im.getpixel((x,y))[3]:
            candidates=[u for u in range(im.width) if im.getpixel((u,y))[3]]
            if candidates:x=min(candidates,key=lambda u:abs(u-x))
            else:
                points=[(u,v) for v in range(im.height) for u in range(im.width) if im.getpixel((u,v))[3]]
                x,y=min(points,key=lambda p:(p[0]-x)**2+(p[1]-y)**2)
        return self.color(im.getpixel((x,y))[:3])

    def add_only(self,raw,patch,mask,label):
        out=raw.copy();added=Image.new('RGBA',raw.size);count=0
        for y in range(raw.height):
            for x in range(raw.width):
                if not raw.getpixel((x,y))[3] and mask.getpixel((x,y)):
                    c=patch.getpixel((x,y));assert c[3]==255
                    out.putpixel((x,y),c);added.putpixel((x,y),c);count+=1
                if raw.getpixel((x,y))[3]:assert out.getpixel((x,y))==raw.getpixel((x,y))
        self.stats.append(dict(layer=label,addedPixels=count,visibleSourcePixelsUnchanged=True))
        return out,added

    def torso(self,raw,d):
        gen=self.cell(d,0);box=BODY_BOXES[d];w,h=box[2]-box[0],box[3]-box[1]
        patch=Image.new('RGBA',(64,64));mask=Image.new('L',(64,64));ImageDraw.Draw(mask).polygon(TORSO_POLYGONS[d],fill=255)
        for y in range(64):
            for x in range(64):
                if mask.getpixel((x,y)):
                    patch.putpixel((x,y),self.sample(gen,(x-box[0])*gen.width/w,(y-box[1])*gen.height/h))
        return self.add_only(raw,patch,mask,f'{d}/torso')

    def arms(self,raw_upper,raw_lower,d,side,joints):
        gen=self.cell(d,1 if side=='right' else 2)
        shoulder,elbow,hand=joints
        start=shoulder[1]-3;end=hand[1]+4
        patch=Image.new('RGBA',(64,64));fullmask=Image.new('L',(64,64))
        for y in range(max(0,start),min(64,end+1)):
            a,b=(shoulder,elbow) if y<elbow[1] else (elbow,hand)
            t=max(0,min(1,(y-a[1])/max(1,b[1]-a[1])))
            cx=a[0]+t*(b[0]-a[0])
            for x in range(64):
                if min(segment_distance(x,y,shoulder,elbow),segment_distance(x,y,elbow,hand))<=2.8:
                    fullmask.putpixel((x,y),255)
                    patch.putpixel((x,y),self.sample(gen,(x-cx+3)*gen.width/6,(y-start)*gen.height/max(1,end-start)))
        result=[]
        for name,raw in [('upper',raw_upper),('lower',raw_lower)]:
            mask=fullmask.copy()
            for y in range(64):
                if (name=='upper' and y>elbow[1]+2) or (name=='lower' and y<elbow[1]-2):
                    ImageDraw.Draw(mask).line((0,y,63,y),fill=0)
            result.append(self.add_only(raw,patch,mask,f'{d}/{side}-{name}'))
        return result
