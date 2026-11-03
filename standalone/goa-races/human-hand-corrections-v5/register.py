"""Stage rounded side-profile noses and integrated idle arm redraws."""
from pathlib import Path
from PIL import Image,ImageDraw
import numpy as np,json
HERE=Path(__file__).resolve().parent;entries=json.loads((HERE/'manifest.json').read_text());reports=[]
proof=Image.new('RGBA',(1024,4*192),(20,32,38,255));draw=ImageDraw.Draw(proof)
for index,e in enumerate(entries):
 f=Path(e['folder']);native=f/'redrawn.png'
 if not native.exists():continue
 gen=Image.open(native).convert('RGBA');before=Image.open(f/'before.png').convert('RGBA');after=before.copy();a=np.array(gen)[:,:,3]>128;h,w=a.shape;groups=[]
 for yy,xx in zip(*np.where(a)):
  if not a[yy,xx]:continue
  stack=[(int(xx),int(yy))];a[yy,xx]=False;x0=x1=int(xx);y0=y1=int(yy);n=0
  while stack:
   x,y=stack.pop();n+=1;x0=min(x0,x);x1=max(x1,x);y0=min(y0,y);y1=max(y1,y)
   for nx,ny in [(x-1,y),(x+1,y),(x,y-1),(x,y+1),(x-1,y-1),(x+1,y-1),(x-1,y+1),(x+1,y+1)]:
    if 0<=nx<w and 0<=ny<h and a[ny,nx]:a[ny,nx]=False;stack.append((nx,ny))
  if n>500:groups.append((n,(x0,y0,x1+1,y1+1)))
 groups=sorted(sorted(groups,reverse=True)[:6],key=lambda q:q[1][1]);assert len(groups)==6,(e['id'],len(groups));edits=[];registration=[]
 for row in range(3):
  for k,(_,box) in enumerate(sorted(groups[row*2:row*2+2],key=lambda q:q[1][0])):
   view=k+2;x0,y0,x1,y1=box;old=before.crop((view*64,row*64,(view+1)*64,(row+1)*64));ob=old.getchannel('A').point(lambda a:255 if a>128 else 0).getbbox();height=ob[3]-ob[1];scale=height/(y1-y0)
   head=gen.crop((x0,y0,x1,y0+round((y1-y0)*.27))).getchannel('A').point(lambda a:255 if a>128 else 0).getbbox();oh=old.crop((0,ob[1],64,ob[1]+round(height*.27))).getchannel('A').point(lambda a:255 if a>128 else 0).getbbox()
   center=x0+(head[0]+head[2])/2;oldcenter=(oh[0]+oh[2])/2;dx=round(oldcenter+(x0-center)*scale)
   sprite=gen.crop(box).resize((round((x1-x0)*scale),height),Image.Resampling.NEAREST);aligned=Image.new('RGBA',(64,64));aligned.paste(sprite,(dx,ob[1]));aligned.save(f/f'{view}-{row}-registered.png')
   nose=(41,ob[1]+12,51,ob[1]+27) if view==2 else (13,ob[1]+12,24,ob[1]+27)
   regions=[('nose',nose)]
   if row==0:regions.append(('arm',(18,31,34,54) if view==2 else (30,31,49,54)))
   for kind,region in regions:
    ax0,ay0,ax1,ay1=region;after.paste(aligned.crop(region),(view*64+ax0,row*64+ay0));edits.append(dict(view=view,row=row,kind=kind,box=list(region)))
   registration.append(dict(view=view,row=row,sourceBox=list(box),scale=scale,destination=[dx,ob[1]]))
 diff=np.any(np.array(before)!=np.array(after),axis=2);allowed=np.zeros(diff.shape,dtype=bool)
 for edit in edits:
  x0,y0,x1,y1=edit['box'];allowed[edit['row']*64+y0:edit['row']*64+y1,edit['view']*64+x0:edit['view']*64+x1]=True
 assert not np.any(diff&~allowed)
 after.save(f/'candidate.png');(f/'registration.json').write_text(json.dumps(registration,indent=2));reports.append(dict(id=e['id'],edits=edits,changedPixels=int(diff.sum()),otherPixelsIdentical=True))
 for col,im in enumerate([before,after]):
  pair=im.crop((128,0,256,64)).resize((384,192),Image.Resampling.NEAREST);proof.alpha_composite(pair,(col*512+64,index*192));draw.text((col*512+4,index*192+4),e['id']+(' · previous' if col==0 else ' · corrected'),fill='white')
proof.save(HERE/'comparison.png');(HERE/'staged-verification.json').write_text(json.dumps(reports,indent=2));print('Staged',len(reports),'of 4 focused corrections')
