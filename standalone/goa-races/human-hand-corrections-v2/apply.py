"""Mirror each male Human west forearm/hand into the east idle cell; retain other pixels."""
from pathlib import Path
from PIL import Image,ImageOps,PngImagePlugin,ImageDraw
import numpy as np,json,shutil,hashlib
HERE=Path(__file__).resolve().parent;ART=HERE.parent;ROOT=ART.parents[1]
source='Each variant’s original west-facing idle arm and hand'
entries=[e for e in json.loads((HERE/'manifest.json').read_text()) if e['sex']=='male'];report=[]
for e in entries:
 p=ROOT/e['source'];backup=HERE/'before'/e['race']/e['appearance'];backup.mkdir(parents=True,exist_ok=True)
 dest=backup/'sprites.png'
 if not dest.exists():shutil.copy2(p,dest)
 before=Image.open(dest).convert('RGBA');after=before.copy();cell=before.crop((128,0,192,64));a=np.array(cell)
 left=19
 if e['appearance']=='Hellblooded':left=24 if e['race']=='Human' else 25
 if e['appearance']=='Werewolf':left=25
 box=(left,40,34 if e['appearance'] in ['Hellblooded','Werewolf'] else 33,53)
 mirrored=ImageOps.mirror(before.crop((192,0,256,64)))
 patch=mirrored.crop(box)
 after.paste(patch,(128+box[0],box[1]))
 diff=np.any(np.array(before)!=np.array(after),axis=2);ys,xs=np.where(diff)
 assert len(xs)>0
 assert xs.min()>=128+box[0] and xs.max()<128+box[2] and ys.min()>=box[1] and ys.max()<box[3]
 after.save(p)
 # Keep the animation source and replay DMI in sync; preserve native sources for provenance.
 if e['appearance']!='base':
  folder=ART/'hybrid-animations/assets'/e['race']/e['appearance'];after.save(folder/'sprites.png')
  override=folder/'east-idle-hand-v1';override.mkdir(exist_ok=True);after.crop((128,0,192,64)).save(override/'east-idle-fixed-64.png')
  (folder/'frame-overrides.json').write_text(json.dumps([dict(column=2,row=0,image='east-idle-hand-v1/east-idle-fixed-64.png')],indent=2))
  meta=json.loads((folder/'atlas.json').read_text());meta['frameOverrides']=[dict(column=2,row=0,reason='West idle forearm/hand mirrored into east idle')];(folder/'atlas.json').write_text(json.dumps(meta,indent=2))
  replay=Image.new('RGBA',(256,256))
  for r,f in enumerate([0,1,0,2]):replay.paste(after.crop((0,f*64,256,(f+1)*64)),(0,r*64))
  info=PngImagePlugin.PngInfo();info.add_text('Description','# BEGIN DMI\nversion = 4.0\n\twidth = 64\n\theight = 64\nstate = ""\n\tdirs = 4\n\tframes = 4\n\tdelay = 2,2,2,2\n\tmovement = 1\n# END DMI\n',zip=True);replay.save(folder/'movement.dmi',format='PNG',pnginfo=info)
 else:
  registrations=json.loads((ART/'hybrids/walk-registration.json').read_text());r=next(r for r in registrations[e['race']]['rects'] if r['row']==0 and r['column']==2)
  native=ART/'hybrids/walks'/(e['race']+'.png');saved=backup/'native-walk.png'
  if not saved.exists():shutil.copy2(native,saved)
  im=Image.open(saved).convert('RGBA');sx,sy,sw,sh=r['source'];tx,ty,tw,th=r['destination'];x0,y0,x1,y1=box
  nx0=round(sx+(128+x0-tx)*sw/tw);nx1=round(sx+(128+x1-tx)*sw/tw);ny0=round(sy+(y0-ty)*sh/th);ny1=round(sy+(y1-ty)*sh/th)
  im.paste(patch.resize((nx1-nx0,ny1-ny0),Image.Resampling.NEAREST),(nx0,ny0));im.save(native)
 report.append(dict(id=e['id'],changedPixels=int(diff.sum()),changedRegion=[128+box[0],box[1],128+box[2],box[3]],otherFramesIdentical=True))
board=Image.new('RGBA',(1024,4*280),(20,32,38,255));d=ImageDraw.Draw(board)
for i,e in enumerate(entries):
 cell=Image.open(ROOT/e['source']).crop((128,0,192,64)).resize((256,256),Image.Resampling.NEAREST);board.alpha_composite(cell,((i%4)*256,(i//4)*280+20));d.text(((i%4)*256+4,(i//4)*280+3),e['id'],fill='white')
board.save(HERE/'male-humans-after.png');(HERE/'verification.json').write_text(json.dumps(dict(corrected=report,total=len(report),femaleSheetsModified=False,source=str(source)),indent=2));print('Corrected',len(report),'male sheets; every change confined to the east-idle hand region.')
