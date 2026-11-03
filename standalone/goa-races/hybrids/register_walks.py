"""Measure actual sprite islands; the browser packs complete sprites at a fixed foot anchor."""
from pathlib import Path
from PIL import Image
import numpy as np,json
HERE=Path(__file__).resolve().parent
HEIGHTS={'Human':56,'Dwarves':46,'Night Elf':59,'Orc':57,'Goblins':43,'Kobold':45,'Elf':59,'HumanBlack':56,'FrogMan':54,'LizardMan':54}
def runs(active):
 out=[];start=None
 for i,v in enumerate(active):
  if v and start is None:start=i
  if not v and start is not None:out.append((start,i));start=None
 if start is not None:out.append((start,len(active)))
 return out
result={}
for name,height in HEIGHTS.items():
 im=Image.open(HERE/'walks'/(name+'.png'));a=np.array(im.getchannel('A'));mask=a>128;rows=runs(mask.sum(1)>3);assert len(rows)==3,(name,rows)
 rects=[]
 for row,(y0,y1) in enumerate(rows):
  cols=runs(mask[y0:y1].sum(0)>3);assert len(cols)==4,(name,row,cols)
  for d,(x0,x1) in enumerate(cols):
   ys=np.nonzero(mask[y0:y1,x0:x1].any(1))[0];top=y0+int(ys.min());bottom=y0+int(ys.max())+1
   rects.append(dict(column=d,row=row,source=[x0,top,x1-x0,bottom-top]))
 scale=height/max(r['source'][3] for r in rects)
 assert max(r['source'][2]*scale for r in rects)<62
 for r in rects:
  w,h=r['source'][2:];dw,dh=round(w*scale),round(h*scale);r['destination']=[r['column']*64+32-dw//2,r['row']*64+62-dh,dw,dh]
 result[name]=dict(targetMaxHeight=height,footBaseline=62,uniformScale=scale,rects=rects)
(HERE/'walk-registration.json').write_text(json.dumps(result,indent=2));print('Measured 84 complete frames. Foot anchor: y62; one scale per race.')
