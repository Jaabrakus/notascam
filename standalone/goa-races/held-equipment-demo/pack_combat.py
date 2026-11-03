"""Mechanically register the three complete combat pose rows; leave source intact."""
from pathlib import Path
from PIL import Image
import numpy as np
import json

HERE=Path(__file__).resolve().parent
im=Image.open(HERE/'combat/generated.png').convert('RGBA')
a=np.asarray(im)[:,:,3]>128
def runs(v):
    ids=np.flatnonzero(v)
    return [(int(g[0]),int(g[-1])+1) for g in np.split(ids,np.where(np.diff(ids)>1)[0]+1) if len(g)]
rows=runs(a.any(axis=1))[:3]
assert len(rows)==3
out=Image.new('RGBA',(256,192));rects=[]
for r,(y0,y1) in enumerate(rows):
    cols=runs(a[y0:y1].any(axis=0));assert len(cols)==4
    scale=55/(y1-y0)
    for d,(x0,x1) in enumerate(cols):
        piece=im.crop((x0,y0,x1,y1))
        piece=piece.resize((round(piece.width*scale),round(piece.height*scale)),Image.Resampling.NEAREST)
        out.paste(piece,(d*64+32-piece.width//2,r*64+62-piece.height))
        rects.append(dict(row=r,direction=d,source=[x0,y0,x1,y1]))
west=Image.open(HERE/'combat/west-right-handed.png').convert('RGBA')
wa=np.asarray(west)[:,:,3]>128
west_rows=runs(wa.any(axis=1));assert len(west_rows)==3
for r,(y0,y1) in enumerate(west_rows):
    xs=np.flatnonzero(wa[y0:y1].any(axis=0));x0,x1=int(xs[0]),int(xs[-1])+1
    piece=west.crop((x0,y0,x1,y1));scale=55/piece.height
    piece=piece.resize((round(piece.width*scale),55),Image.Resampling.NEAREST)
    out.paste(Image.new('RGBA',(64,64)),(192,r*64))
    out.paste(piece,(224-piece.width//2,r*64+7))
out.save(HERE/'combat/body.png')
(HERE/'combat/registration.json').write_text(json.dumps(dict(rows=['ready','windup','strike'],directions=['South','North','East','West'],frameSize=[64,64],sourceRects=rects,excluded='Fourth generated row reaches the image edge; it is not used.'),indent=2))
