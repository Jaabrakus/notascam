"""Register the native redraw; pack 64px frames and a self-contained carry review."""
from pathlib import Path
from PIL import Image
import base64,json,hashlib
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def uri(p):return 'data:image/png;base64,'+base64.b64encode(p.read_bytes()).decode()
source=Image.open(HERE/'Human-Male-Remake-v2-generated.png').convert('RGBA');sw,sh=source.size
# Identify the 16 character silhouettes rather than assuming perfectly even AI margins.
a=np.array(source)[:,:,3]>128;components=[]
for yy,xx in zip(*np.where(a)):
 if not a[yy,xx]:continue
 stack=[(int(xx),int(yy))];a[yy,xx]=False;x0=x1=int(xx);y0=y1=int(yy);n=0
 while stack:
  x,y=stack.pop();n+=1;x0=min(x0,x);x1=max(x1,x);y0=min(y0,y);y1=max(y1,y)
  for nx,ny in [(x-1,y),(x+1,y),(x,y-1),(x,y+1),(x-1,y-1),(x+1,y-1),(x-1,y+1),(x+1,y+1)]:
   if 0<=nx<sw and 0<=ny<sh and a[ny,nx]:a[ny,nx]=False;stack.append((nx,ny))
 if n>1000:components.append(dict(box=[x0,y0,x1+1,y1+1],pixels=n))
if len(components)!=16:raise ValueError(('Expected 16 complete silhouettes',len(components)))
components.sort(key=lambda c:c['box'][1]);records=[]
for row in range(4):
 group=sorted(components[row*4:row*4+4],key=lambda c:c['box'][0])
 for view,component in enumerate(group):
  x0,y0,x1,y1=component['box'];rect=[x0,y0,x1,y1]
  records.append(dict(row=row,view=view,rect=rect,box=[0,0,x1-x0,y1-y0],pixels=component['pixels']))
scale=56/max(r['box'][3]-r['box'][1] for r in records)
scale=min(scale,56/max(r['box'][2]-r['box'][0] for r in records))
atlas=Image.new('RGBA',(256,256))
for r in records:
 cell=source.crop(r['rect']);x0,y0,x1,y1=r['box'];head=cell.crop((0,y0,cell.width,y0+max(1,round((y1-y0)*.29))))
 hbox=head.getchannel('A').point(lambda a:255 if a>128 else 0).getbbox();center=(hbox[0]+hbox[2])/2
 sprite=cell.crop(r['box']);size=(round((x1-x0)*scale),round((y1-y0)*scale));sprite=sprite.resize(size,Image.Resampling.NEAREST)
 dx=round(32+(x0-center)*scale);dy=62-size[1]
 if dx<0 or dx+size[0]>64 or dy<0:raise ValueError(('registration clip',r))
 atlas.alpha_composite(sprite,(r['view']*64+dx,r['row']*64+dy));r.update(headCenter=center,destination=[dx,dy,*size])
atlas.save(HERE/'Human-Male-Remake-v2-all.png')
atlas.crop((0,0,256,192)).save(HERE/'Human-Male-Remake-v2-idle-walk.png')
atlas.crop((0,192,256,256)).save(HERE/'Human-Male-Remake-v2-carry.png')
(HERE/'registration.json').write_text(json.dumps(dict(scale=scale,sourceSize=source.size,views=records),indent=2))
# Keep the carry upper body intact; reuse this redraw's own walking legs below the shorts.
cut=50;armed=Image.new('RGBA',(256,192))
for row in range(3):
 for view in range(4):
  master=atlas.crop((view*64,192,view*64+64,256))
  if row:
   master.paste((0,0,0,0),(0,cut,64,64));master.alpha_composite(atlas.crop((view*64,row*64+cut,view*64+64,row*64+64)),(0,cut))
  armed.paste(master,(view*64,row*64))
armed.save(HERE/'Human-Male-Remake-v2-armed-walk.png')
meta=dict(race='Human',sex='male',appearance='base',version=2,frameSize=[64,64],directionOrder=['South','North','East','West'],rows=['idle','walk-contact-A','walk-contact-B','carry'],sequence=[0,1,0,2],frameDurationMs=225,packing='one fixed scale; head-centered, common foot baseline',bodyImage='Human-Male-Remake-v2-all.png',armedWalkImage='Human-Male-Remake-v2-armed-walk.png',armedWalkUpperBodyCut=cut,status='redraw preview; combat actions and race retargeting pending',nativeSha256=hashlib.sha256((HERE/'Human-Male-Remake-v2-generated.png').read_bytes()).hexdigest())
(HERE/'atlas.json').write_text(json.dumps(meta,indent=2))
cat=json.loads((HERE.parent/'armory/catalog.json').read_text());cat['items']=[i for i in cat['items'] if i['id'] in ['weapon.arming sword','weapon.spear','weapon.crystal staff','shield.round']]
paths={i['strips'][0] for i in cat['items']};images={p:uri(ROOT/p) for p in paths};images.update(body=uri(HERE/'Human-Male-Remake-v2-idle-walk.png'),armedWalk=uri(HERE/'Human-Male-Remake-v2-armed-walk.png'))
profile=json.loads((HERE/'carry-profile.json').read_text())
data=dict(catalog=cat,bodies=[],images=images,gear=json.loads((ROOT/'standalone/remastered/game/Interface/gear3d/gear3d-pix.json').read_text()),carry=profile,carryTemplate=json.loads((HERE.parent/'universal-animation/carry-template/template.json').read_text()))
page=(HERE/'template.html').read_text().replace('/*ORIGINAL*/',uri(HERE/'Human-Male-Base-original.png')).replace('/*DATA*/null',json.dumps(data)).replace('/*EQUIPMENT*/',(HERE.parent/'armory/equipment.js').read_text()).replace('/*MAPPER*/',(HERE.parent/'universal-animation/carry-pose.js').read_text()).replace('/*APP*/',(HERE/'carry.js').read_text())
(HERE/'index.html').write_text(page);(ROOT/'Dungeon Master Sample/GOA Human Remake v2.html').write_text(page)
print(json.dumps(dict(native=source.size,bodyAtlas=atlas.size,frames=16,scale=scale)))
