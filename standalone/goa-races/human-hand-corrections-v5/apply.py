"""Publish rounded noses and focused idle-arm corrections."""
from pathlib import Path
from PIL import Image,ImageOps,PngImagePlugin,ImageDraw
import numpy as np,json,shutil,hashlib
HERE=Path(__file__).resolve().parent;ART=HERE.parent;ROOT=ART.parents[1]
source='Built-in image_gen: independent elbow/forearm/wrist/fist redraw for each variant'
staged=json.loads((HERE/'staged-verification.json').read_text());assert len(staged)==4
stagedByID={r['id']:r for r in staged}
entries=json.loads((HERE/'manifest.json').read_text());report=[]
for e in entries:
 p=ART/'hybrids/packed'/e['race']/e['appearance']/'sprites.png';backup=HERE/'before'/e['race']/e['appearance'];backup.mkdir(parents=True,exist_ok=True)
 dest=backup/'sprites.png'
 if not dest.exists():shutil.copy2(p,dest)
 before=Image.open(dest).convert('RGBA');after=before.copy();cell=before.crop((128,0,192,64));a=np.array(cell)
 record=stagedByID[e['id']];edits=record['edits']
 after=Image.open(HERE/e['race']/e['appearance']/'candidate.png').convert('RGBA')
 diff=np.any(np.array(before)!=np.array(after),axis=2);allowed=np.zeros(diff.shape,dtype=bool)
 for item in edits:
  x0,y0,x1,y1=item['box'];allowed[item['row']*64+y0:item['row']*64+y1,item['view']*64+x0:item['view']*64+x1]=True
 assert not np.any(diff&~allowed)
 after.save(p)
 # Keep the animation source and replay DMI in sync; preserve native sources for provenance.
 if e['appearance']!='base':
  folder=ART/'hybrid-animations/assets'/e['race']/e['appearance'];after.save(folder/'sprites.png')
  override=folder/'rounded-profile-v5';override.mkdir(exist_ok=True)
  overrides=[]
  for row in range(3):
   for view in [2,3]:
    name=f'{view}-{row}-fixed-64.png'
    after.crop((view*64,row*64,(view+1)*64,(row+1)*64)).save(override/name)
    overrides.append(dict(column=view,row=row,image='rounded-profile-v5/'+name))
  (folder/'frame-overrides.json').write_text(json.dumps(overrides,indent=2))
  meta=json.loads((folder/'atlas.json').read_text());meta['frameOverrides']=[dict(column=v,row=r,reason='Rounded Human nose and corrected idle arm') for r in range(3) for v in [2,3]]
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
   row=item['row'];r=next(r for r in registrations[e['race']]['rects'] if r['row']==row and r['column']==view)
   sx,sy,sw,sh=r['source'];tx,ty,tw,th=r['destination']
   nx0=round(sx+(view*64+x0-tx)*sw/tw);nx1=round(sx+(view*64+x1-tx)*sw/tw);ny0=round(sy+(row*64+y0-ty)*sh/th);ny1=round(sy+(row*64+y1-ty)*sh/th)
   patch=after.crop((view*64+x0,row*64+y0,view*64+x1,row*64+y1));im.paste(patch.resize((nx1-nx0,ny1-ny0),Image.Resampling.NEAREST),(nx0,ny0))
  im.save(native)

 report.append(dict(id=e['id'],changedPixels=int(diff.sum()),edits=edits,otherFramesIdentical=True,independentlyRedrawn=True))
(HERE/'verification.json').write_text(json.dumps(dict(corrected=report,total=len(report),femaleSheetsModified=False,source=str(source)),indent=2));print('Published',len(report),'rounded-profile and idle-arm corrections.')
