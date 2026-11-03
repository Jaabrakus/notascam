"""Register the low, one-handed spear jab body source in a fixed 64px space."""
from pathlib import Path
from PIL import Image
import numpy as np
import json

HERE=Path(__file__).resolve().parent/'combat/spear-short-jab'
im=Image.open(HERE/'generated.png').convert('RGBA');alpha=np.asarray(im)[:,:,3]>128
def runs(v):
    ids=np.flatnonzero(v)
    return [(int(g[0]),int(g[-1])+1) for g in np.split(ids,np.where(np.diff(ids)>1)[0]+1) if len(g)]
rows=runs(alpha.any(axis=1));assert len(rows)==4,rows
out=Image.new('RGBA',(256,192));records=[]
scale=55/max(y1-y0 for y0,y1 in rows)
for r,source_row in enumerate([0,1,3]):
    y0,y1=rows[source_row]
    cols=runs(alpha[y0:y1].any(axis=0));assert len(cols)==4,(r,cols)
    for d,(x0,x1) in enumerate(cols):
        piece=im.crop((x0,y0,x1,y1));piece=piece.resize((round(piece.width*scale),round(piece.height*scale)),Image.Resampling.NEAREST)
        assert piece.width<=62 and piece.height<=55
        out.paste(piece,(d*64+32-piece.width//2,r*64+62-piece.height))
        records.append(dict(row=r,direction=d,source=[x0,y0,x1,y1]))
west=Image.open(HERE/'west-compact.png').convert('RGBA');wa=np.asarray(west)[:,:,3]>128
west_rows=runs(wa.any(axis=1));assert len(west_rows)==3,west_rows
for r,(y0,y1) in enumerate(west_rows):
    xs=np.flatnonzero(wa[y0:y1].any(axis=0));x0,x1=int(xs[0]),int(xs[-1])+1
    piece=west.crop((x0,y0,x1,y1));piece=piece.resize((round(piece.width*55/piece.height),55),Image.Resampling.NEAREST)
    out.paste(Image.new('RGBA',(64,64)),(192,r*64));out.paste(piece,(224-piece.width//2,r*64+7))
    records.append(dict(row=r,direction=3,sourceImage='west-compact.png',source=[x0,y0,x1,y1]))
out.save(HERE/'body.png')
(HERE/'registration.json').write_text(json.dumps(dict(frameSize=[64,64],scale=scale,weaponHands=1,poses=['low-ready','small-drawback','short-jab'],excludedSourceRow=2,sourceRects=records),indent=2))
