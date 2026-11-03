"""Register the one-handed body art; keep the two-handed experiment separate."""
from pathlib import Path
from PIL import Image
import numpy as np
import json

HERE=Path(__file__).resolve().parent/'combat/spear-one-hand-sweep'
im=Image.open(HERE/'generated.png').convert('RGBA');alpha=np.asarray(im)[:,:,3]>128
def runs(v):
    ids=np.flatnonzero(v)
    return [(int(g[0]),int(g[-1])+1) for g in np.split(ids,np.where(np.diff(ids)>1)[0]+1) if len(g)]
rows=runs(alpha.any(axis=1));assert len(rows)==4,rows
out=Image.new('RGBA',(256,256));records=[]
scale=55/max(y1-y0 for y0,y1 in rows)
for r,(y0,y1) in enumerate(rows):
    cols=runs(alpha[y0:y1].any(axis=0));assert len(cols)==4,(r,cols)
    for d,(x0,x1) in enumerate(cols):
        piece=im.crop((x0,y0,x1,y1));piece=piece.resize((round(piece.width*scale),round(piece.height*scale)),Image.Resampling.NEAREST)
        assert piece.width<=62 and piece.height<=55
        out.paste(piece,(d*64+32-piece.width//2,r*64+62-piece.height))
        records.append(dict(row=r,direction=d,source=[x0,y0,x1,y1]))
out.save(HERE/'body.png')
(HERE/'registration.json').write_text(json.dumps(dict(frameSize=[64,64],scale=scale,weaponHands=1,poses=['guard','windup','sweep','recovery'],sourceRects=records),indent=2))
