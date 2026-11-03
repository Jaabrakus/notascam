"""Register separated source sprites into real cells without changing their pixels."""
from pathlib import Path
from PIL import Image
import numpy as np,json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent
INPUTS=[('DemonFly',ROOT/'sprite-engine/jobs/20261029-214909-d377bfdd/result.png',2),('GargoyleFly',ROOT/'sprite-engine/jobs/20261029-214909-5b3b707d/result.png',2),('Gargoyle-eyes',ROOT/'hybrids/sheets/Gargoyle-eyes.png',6)]
records=[]
for name,path,rows in INPUTS:
 im=Image.open(path).convert('RGBA');a=np.array(im.getchannel('A'));parts=[]
 for row in range(rows):
  y0,y1=round(row*im.height/rows),round((row+1)*im.height/rows);mask=a[y0:y1]>128;active=mask.sum(0)>3;runs=[];start=None
  for x,v in enumerate(active):
   if v and start is None:start=x
   if not v and start is not None:runs.append((start,x));start=None
  if start is not None:runs.append((start,len(active)))
  assert len(runs)==4,(name,row,runs)
  for direction,(x0,x1) in enumerate(runs):
   ys=np.nonzero(mask[:,x0:x1].any(1))[0];rect=(max(0,x0-2),max(y0,y0+int(ys.min())-2),min(im.width,x1+2),min(y1,y0+int(ys.max())+3));parts.append((row,direction,rect))
 size=max(max(rect[2]-rect[0],rect[3]-rect[1]) for _,_,rect in parts)+16
 out=Image.new('RGBA',(size*4,size*rows))
 for row,d,rect in parts:
  tile=im.crop(rect);out.paste(tile,(size*d+(size-tile.width)//2,size*row+size-8-tile.height))
 out.save(HERE/(name+'-registered.png'))
 editrows=list(range(rows)) if rows==2 else [3,4,5]
 north=Image.new('RGBA',(size,size*len(editrows)))
 for i,row in enumerate(editrows):north.paste(out.crop((size,row*size,size*2,(row+1)*size)),(0,i*size))
 north.save(HERE/(name+'-north-input.png'))
 records.append(dict(name=name,original=str(path),registered=str(HERE/(name+'-registered.png')),northInput=str(HERE/(name+'-north-input.png')),rows=rows,size=size,editRows=editrows,sourceRects=[list(rect) for _,_,rect in parts]))
(HERE/'registration.json').write_text(json.dumps(records,indent=2));print('Registered complete wings into cells; no manual pixel painting.')
