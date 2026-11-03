"""Register generated female walks without painting or synthesizing artwork."""
from pathlib import Path
import json, hashlib
import numpy as np
from PIL import Image, PngImagePlugin

HERE=Path(__file__).resolve().parent
def runs(active):
 out=[]; start=None
 for i,v in enumerate(active):
  if v and start is None:start=i
  if not v and start is not None:out.append((start,i));start=None
 if start is not None:out.append((start,len(active)))
 return out

def main():
 jobs=json.loads((HERE/'manifest.json').read_text()); registered={}; failures=[]
 for job in jobs:
  folder=Path(job['folder']); path=folder/'corrected.png' if (folder/'corrected.png').exists() else folder/'generated.png'
  if not path.exists():continue
  try:
   im=Image.open(path).convert('RGBA'); mask=np.array(im.getchannel('A'))>128
   rows=runs(mask.sum(1)>3); assert len(rows)==3,('row count',rows)
   rects=[]
   for row,(y0,y1) in enumerate(rows):
    cols=runs(mask[y0:y1].sum(0)>3);assert len(cols)==4,('column count',row,cols)
    for d,(x0,x1) in enumerate(cols):
     ys=np.nonzero(mask[y0:y1,x0:x1].any(1))[0];top=y0+int(ys.min());bottom=y0+int(ys.max())+1
     rects.append(dict(column=d,row=row,source=[x0,top,x1-x0,bottom-top]))
   scale=min(job['targetHeight']/max(r['source'][3] for r in rects),60/max(r['source'][2] for r in rects))
   atlas=Image.new('RGBA',(256,192))
   for r in rects:
    x,y,w,h=r['source'];dw,dh=round(w*scale),round(h*scale)
    dx,dy=r['column']*64+32-dw//2,r['row']*64+62-dh
    r['destination']=[dx,dy,dw,dh]
    tile=im.crop((x,y,x+w,y+h)).resize((dw,dh),Image.Resampling.NEAREST)
    atlas.paste(tile,(dx,dy))
   for d in range(4):
    cells=[atlas.crop((d*64,f*64,(d+1)*64,(f+1)*64)) for f in range(3)]
    assert len({hashlib.sha256(c.tobytes()).hexdigest() for c in cells})==3,('duplicate poses',d)
    assert all(c.getbbox() for c in cells),('empty pose',d)
   atlas.save(folder/'sprites.png');atlas.crop((0,0,256,64)).save(folder/'standing.png')
   meta=dict(format='goa-female-walk',sex='female',race=job['race'],appearance=job['appearance'],frameSize=[64,64],directionOrder=['South','North','East','West'],frames=3,sequence=[0,1,0,2],frameDurationMs=200,status='generated walk draft',image='sprites.png',footBaseline=62,uniformScale=scale,rects=rects)
   (folder/'atlas.json').write_text(json.dumps(meta,indent=2))
   replay=Image.new('RGBA',(256,256))
   for row,f in enumerate(meta['sequence']):replay.paste(atlas.crop((0,f*64,256,(f+1)*64)),(0,row*64))
   state='Normal' if job['race'] in ['Night Elf','Orc','Kobold','Elf'] else ''
   desc=f'# BEGIN DMI\nversion = 4.0\n\twidth = 64\n\theight = 64\nstate = "{state}"\n\tdirs = 4\n\tframes = 4\n\tdelay = 2,2,2,2\n\tmovement = 1\n# END DMI\n'
   info=PngImagePlugin.PngInfo();info.add_text('Description',desc,zip=True);replay.save(folder/'movement.dmi',format='PNG',pnginfo=info)
   registered[job['id']]=dict(path=str(folder/'sprites.png'),source=str(path),frames=3,sequence=[0,1,0,2],status='generated walk draft')
  except (AssertionError,ValueError) as e:failures.append(dict(id=job['id'],error=str(e)))
 (HERE/'registration.json').write_text(json.dumps(registered,indent=2))
 (HERE/'registration-errors.json').write_text(json.dumps(failures,indent=2))
 print(json.dumps(dict(registered=len(registered),pending=len(jobs)-len(registered),errors=failures)))
if __name__=='__main__':main()
