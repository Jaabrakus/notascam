"""Register body-only action sheets and the independently reusable arrow."""
from pathlib import Path
from PIL import Image
import numpy as np
import json
HERE=Path(__file__).resolve().parent/'combat'
def runs(v):
    ids=np.flatnonzero(v)
    return [(int(g[0]),int(g[-1])+1) for g in np.split(ids,np.where(np.diff(ids)>1)[0]+1) if len(g)]
for kind in ['spear','bow','staff']:
    im=Image.open(HERE/kind/'generated.png').convert('RGBA');a=np.asarray(im)[:,:,3]>128
    rows=runs(a.any(axis=1));assert len(rows)==3,(kind,rows)
    out=Image.new('RGBA',(256,192));rects=[]
    for r,(y0,y1) in enumerate(rows):
        cols=runs(a[y0:y1].any(axis=0));assert len(cols)==4,(kind,r,cols)
        scale=55/(y1-y0)
        for d,(x0,x1) in enumerate(cols):
            piece=im.crop((x0,y0,x1,y1));piece=piece.resize((round(piece.width*scale),55),Image.Resampling.NEAREST)
            out.paste(piece,(d*64+32-piece.width//2,r*64+7));rects.append([x0,y0,x1,y1])
    correction=HERE/kind/'north-south-correction.png'
    if correction.exists():
        fixed=Image.open(correction).convert('RGBA');fa=np.asarray(fixed)[:,:,3]>128
        fr=runs(fa.any(axis=1));assert len(fr)==3,(kind,fr)
        for r,(y0,y1) in enumerate(fr):
            fc=runs(fa[y0:y1].any(axis=0));assert len(fc)==2,(kind,r,fc)
            for d,(x0,x1) in enumerate(fc):
                piece=fixed.crop((x0,y0,x1,y1));scale=55/piece.height
                piece=piece.resize((round(piece.width*scale),55),Image.Resampling.NEAREST)
                out.paste(Image.new('RGBA',(64,64)),(d*64,r*64))
                out.paste(piece,(d*64+32-piece.width//2,r*64+7))
    out.save(HERE/kind/'body.png');(HERE/kind/'registration.json').write_text(json.dumps(dict(sourceRects=rects,cellSize=[64,64],northSouthCorrection=correction.exists()),indent=2))
arrow=Image.open(HERE/'arrow-generated.png').convert('RGBA');a=np.asarray(arrow)[:,:,3]>128
ys,xs=np.where(a);arrow=arrow.crop((int(xs.min()),int(ys.min()),int(xs.max())+1,int(ys.max())+1));arrow.thumbnail((32,8),Image.Resampling.NEAREST);arrow.save(HERE/'arrow.png')
