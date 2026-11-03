"""Register native arm redraws without changing the surrounding approved character pixels."""
from pathlib import Path
from PIL import Image,ImageDraw
import numpy as np,json
HERE=Path(__file__).resolve().parent
entries=json.loads((HERE/'manifest.json').read_text());reports=[]
board=Image.new('RGBA',(1024,608),(20,32,38,255));draw=ImageDraw.Draw(board)
for i,e in enumerate(entries):
 f=Path(e['folder']);native=f/'redrawn.png'
 if not native.exists():continue
 gen=Image.open(native).convert('RGBA');before=Image.open(f/'before.png').convert('RGBA');after=before.copy();edits=[];reg=[]
 for k,view in enumerate([2,3]):
  g=gen.crop((round(k*gen.width/2),0,round((k+1)*gen.width/2),gen.height));a=np.array(g)[:,:,3]>128
  # Ignore isolated alpha speckles; the body is the largest connected silhouette.
  groups=[]
  for yy,xx in zip(*np.where(a)):
   if not a[yy,xx]:continue
   stack=[(int(xx),int(yy))];a[yy,xx]=False;x0=x1=int(xx);y0=y1=int(yy);n=0
   while stack:
    x,y=stack.pop();n+=1;x0=min(x0,x);x1=max(x1,x);y0=min(y0,y);y1=max(y1,y)
    for nx,ny in [(x-1,y),(x+1,y),(x,y-1),(x,y+1),(x-1,y-1),(x+1,y-1),(x-1,y+1),(x+1,y+1)]:
     if 0<=nx<g.width and 0<=ny<g.height and a[ny,nx]:a[ny,nx]=False;stack.append((nx,ny))
   if n>100:groups.append((n,(x0,y0,x1+1,y1+1)))
  box=max(groups)[1];x0,y0,x1,y1=box
  old=before.crop((view*64,0,(view+1)*64,64));ob=old.getchannel('A').point(lambda a:255 if a>128 else 0).getbbox();height=ob[3]-ob[1];scale=height/(y1-y0)
  head=g.crop((0,y0,g.width,y0+round((y1-y0)*.30))).getchannel('A').point(lambda a:255 if a>128 else 0).getbbox();oldhead=old.crop((0,ob[1],64,ob[1]+round(height*.30))).getchannel('A').point(lambda a:255 if a>128 else 0).getbbox()
  center=(head[0]+head[2])/2;oldcenter=(oldhead[0]+oldhead[2])/2
  sprite=g.crop(box).resize((round((x1-x0)*scale),height),Image.Resampling.NEAREST);aligned=Image.new('RGBA',(64,64));dx=round(oldcenter+(x0-center)*scale);aligned.paste(sprite,(dx,ob[1]))
  # Include the elbow transition as well as the fist; no walking-pose grafts.
  tailed=e['appearance'] in ['Hellblooded','Werewolf']
  arm=(23 if tailed else 19,35,34,53) if view==2 else (31,35,45 if tailed else 48,53)
  ax0,ay0,ax1,ay1=arm;after.paste(aligned.crop(arm),(view*64+ax0,ay0))
  aligned.save(f/(('east' if view==2 else 'west')+'-registered.png'))
  edits.append(dict(view=view,box=list(arm)));reg.append(dict(view=view,sourceBox=list(box),scale=scale,destination=[dx,ob[1]]))
 diff=np.any(np.array(after)!=np.array(before),axis=2);allowed=np.zeros(diff.shape,dtype=bool)
 for edit in edits:
  x0,y0,x1,y1=edit['box'];allowed[y0:y1,edit['view']*64+x0:edit['view']*64+x1]=True
 assert not np.any(diff&~allowed)
 after.save(f/'candidate.png');(f/'registration.json').write_text(json.dumps(reg,indent=2))
 cell=after.crop((128,0,256,64)).resize((256,128),Image.Resampling.NEAREST);board.alpha_composite(cell,((i%4)*256,(i//4)*152+22));draw.text(((i%4)*256+4,(i//4)*152+3),e['id'],fill='white')
 reports.append(dict(id=e['id'],edits=edits,changedPixels=int(diff.sum()),otherPixelsIdentical=True))
board.save(HERE/'redraw-review.png');(HERE/'staged-verification.json').write_text(json.dumps(reports,indent=2));print('Staged',len(reports),'of 16 redraws')
