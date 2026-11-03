"""Refine S/N arm ownership using native joints and the original source palette.
Preserves originals and stores their references so reruns do not accumulate changes.
Usage: python3 refine_front_back_arms.py PACKAGE
"""
import json,sys,math
from pathlib import Path
from PIL import Image
root=Path(sys.argv[1]).resolve();pp=root/'profiles/character.json';p=json.loads(pp.read_text());assets=root/'preview/assets';rp=root/'arm-cut-review.json'
report=json.loads(rp.read_text()) if rp.exists() else {'originalParts':{},'changes':[]}
report['changes']=[]
for d in [0,1]:
 v=p['views'][d]
 for side in ['right','left']:
  key=f'{d}-{side}';names=[side+s for s in ['UpperArm','Forearm','Hand']]
  originals=report['originalParts'].setdefault(key,{n:v['parts'][n] for n in names})
  whole=Image.new('RGBA',(64,64))
  for n in names:whole.alpha_composite(Image.open(assets/originals[n]).convert('RGBA'))
  shoulder,elbow,wrist=v['arms'][side];ey=round(elbow[1]);wy=round(wrist[1])
  # Reuse only colors already present in the limb; no guessed new palette.
  samples=[(x,y,whole.getpixel((x,y))) for y in range(64) for x in range(64) if whole.getpixel((x,y))[3] and sum(whole.getpixel((x,y))[:3])>140]
  if not samples:raise ValueError('No usable limb palette: '+key)
  parts={n:Image.new('RGBA',(64,64)) for n in names}
  for y in range(64):
   for x in range(64):
    color=whole.getpixel((x,y))
    if not color[3]:continue
    if y<=ey:parts[names[0]].putpixel((x,y),color)
    if ey-1<=y<wy:parts[names[1]].putpixel((x,y),color)
    if y>=wy:parts[names[2]].putpixel((x,y),color)
  for name,center,radius in [(names[0],shoulder,2.0),(names[0],elbow,2.0),(names[1],elbow,2.0)]:
   im=parts[name]
   for y in range(max(0,math.floor(center[1]-radius)),min(64,math.ceil(center[1]+radius)+1)):
    for x in range(max(0,math.floor(center[0]-radius)),min(64,math.ceil(center[0]+radius)+1)):
     if math.hypot(x-center[0],y-center[1])<=radius and not im.getpixel((x,y))[3]:
      color=min(samples,key=lambda s:(s[0]-x)**2+(s[1]-y)**2)[2];im.putpixel((x,y),color)
  # Cut edges inside overlapping joints must not retain their original dark outline.
  # Keep long outer arm contours; soften only the joint ends where layers connect.
  for name,center,radius in [(names[0],shoulder,3.0),(names[0],elbow,2.3),(names[1],elbow,2.3),(names[1],wrist,1.8),(names[2],wrist,1.8)]:
   im=parts[name]
   for y in range(max(0,math.floor(center[1]-radius)),min(64,math.ceil(center[1]+radius)+1)):
    for x in range(max(0,math.floor(center[0]-radius)),min(64,math.ceil(center[0]+radius)+1)):
     old=im.getpixel((x,y))
     if old[3] and sum(old[:3])<140 and math.hypot(x-center[0],y-center[1])<=radius:
      im.putpixel((x,y),min(samples,key=lambda s:(s[0]-x)**2+(s[1]-y)**2)[2])
  for n,im in parts.items():
   assert im.getbbox(),n
   file=f'arm-clean-{d}-{n}.png';im.save(assets/file);v['parts'][n]=file
  assert parts[names[1]].crop((0,wy,64,64)).getbbox() is None
  assert parts[names[2]].crop((0,0,64,wy)).getbbox() is None
  report['changes'].append({'view':v['name'],'side':side,'wristRow':wy,'elbowOverlap':'two source rows plus rounded backing','handForearmPixelOverlap':False})
pp.write_text(json.dumps(p,indent=2));rp.write_text(json.dumps(report,indent=2));print('Refined four front/back arms; original assets preserved.')
