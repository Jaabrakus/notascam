"""Publish independently redrawn side-idle arms for every male Human variant."""
from pathlib import Path
from PIL import Image,ImageOps,PngImagePlugin,ImageDraw
import numpy as np,json,shutil,hashlib
HERE=Path(__file__).resolve().parent;ART=HERE.parent;ROOT=ART.parents[1]
source='Built-in image_gen: independent elbow/forearm/wrist/fist redraw for each variant'
staged=json.loads((HERE/'staged-verification.json').read_text());assert len(staged)==16
stagedByID={r['id']:r for r in staged}
entries=[e for e in json.loads((HERE/'manifest.json').read_text()) if e['sex']=='male'];report=[]
for e in entries:
 p=ROOT/e['source'];backup=HERE/'before'/e['race']/e['appearance'];backup.mkdir(parents=True,exist_ok=True)
 dest=backup/'sprites.png'
 if not dest.exists():shutil.copy2(p,dest)
 before=Image.open(dest).convert('RGBA');after=before.copy();cell=before.crop((128,0,192,64));a=np.array(cell)
 record=stagedByID[e['id']];edits=record['edits']
 after=Image.open(HERE/e['race']/e['appearance']/'candidate.png').convert('RGBA')
 diff=np.any(np.array(before)!=np.array(after),axis=2);allowed=np.zeros(diff.shape,dtype=bool)
 for item in edits:
  x0,y0,x1,y1=item['box'];allowed[y0:y1,item['view']*64+x0:item['view']*64+x1]=True
 assert not np.any(diff&~allowed)
 after.save(p)
 # Keep the animation source and replay DMI in sync; preserve native sources for provenance.
 if e['appearance']!='base':
  folder=ART/'hybrid-animations/assets'/e['race']/e['appearance'];after.save(folder/'sprites.png')
  override=folder/'redrawn-idle-arms-v4';override.mkdir(exist_ok=True)
  overrides=[]
  for view in [2,3]:
   name=('east' if view==2 else 'west')+'-idle-fixed-64.png'
   after.crop((view*64,0,(view+1)*64,64)).save(override/name)
   overrides.append(dict(column=view,row=0,image='redrawn-idle-arms-v4/'+name))
  (folder/'frame-overrides.json').write_text(json.dumps(overrides,indent=2))
  meta=json.loads((folder/'atlas.json').read_text());meta['frameOverrides']=[dict(column=v,row=0,reason='Independently redrawn elbow, wrist and fist') for v in [2,3]]
  (folder/'atlas.json').write_text(json.dumps(meta,indent=2));(p.parent/'atlas.json').write_text(json.dumps(meta,indent=2))
  replay=Image.new('RGBA',(256,256))
  for r,f in enumerate([0,1,0,2]):replay.paste(after.crop((0,f*64,256,(f+1)*64)),(0,r*64))
  info=PngImagePlugin.PngInfo();info.add_text('Description','# BEGIN DMI\nversion = 4.0\n\twidth = 64\n\theight = 64\nstate = ""\n\tdirs = 4\n\tframes = 4\n\tdelay = 2,2,2,2\n\tmovement = 1\n# END DMI\n',zip=True);replay.save(folder/'movement.dmi',format='PNG',pnginfo=info)
 else:
  registrations=json.loads((ART/'hybrids/walk-registration.json').read_text())
  native=ART/'hybrids/walks'/(e['race']+'.png');saved=backup/'native-walk.png'
  assert saved.exists()
  im=Image.open(saved).convert('RGBA')
  for item in edits:
   view=item['view'];x0,y0,x1,y1=item['box']
   r=next(r for r in registrations[e['race']]['rects'] if r['row']==0 and r['column']==view)
   sx,sy,sw,sh=r['source'];tx,ty,tw,th=r['destination']
   nx0=round(sx+(view*64+x0-tx)*sw/tw);nx1=round(sx+(view*64+x1-tx)*sw/tw);ny0=round(sy+(y0-ty)*sh/th);ny1=round(sy+(y1-ty)*sh/th)
   patch=after.crop((view*64+x0,y0,view*64+x1,y1));im.paste(patch.resize((nx1-nx0,ny1-ny0),Image.Resampling.NEAREST),(nx0,ny0))
  im.save(native)

 report.append(dict(id=e['id'],changedPixels=int(diff.sum()),edits=edits,otherFramesIdentical=True,independentlyRedrawn=True))
board=Image.new('RGBA',(1024,4*280),(20,32,38,255));d=ImageDraw.Draw(board)
for i,e in enumerate(entries):
 cell=Image.open(ROOT/e['source']).crop((128,0,256,64)).resize((256,128),Image.Resampling.NEAREST);board.alpha_composite(cell,((i%4)*256,(i//4)*280+20));d.text(((i%4)*256+4,(i//4)*280+3),e['id'],fill='white')
board.save(HERE/'male-humans-after.png');(HERE/'verification.json').write_text(json.dumps(dict(corrected=report,total=len(report),femaleSheetsModified=False,source=str(source)),indent=2));print('Corrected',len(report),'male sheets; every change confined to east/west idle arm regions.')
