"""Verify every universal clip and bake every four-direction body preview."""
from pathlib import Path
from playwright.sync_api import sync_playwright
from PIL import Image
import json,base64,hashlib,zipfile
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];exports=HERE/'exports';exports.mkdir(exist_ok=True)
library=json.loads((HERE/'clips.json').read_text());source=json.loads((HERE/'source-clips.json').read_text())
assert len(source['defs'])==57 and len(library['clips'])==99
for name,definition in source['defs'].items():assert library['clips'][name]['keys']==definition['keys'],name
assert all(a['resolved'] for a in library['arenaAliases'])
coverage=[]
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless=True)
 page=browser.new_page(viewport=dict(width=1400,height=1100));errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto((HERE/'index.html').as_uri());page.wait_for_function('window.universalReady===true')
 page.uncheck('#bones');page.select_option('#weapon','')
 checks=page.evaluate('''()=>{const e=universal.engine;let n=0;for(const clip of Object.values(universal.data.clips))for(let i=0;i<13;i++)for(let v=0;v<4;v++){const pose=e.sample(clip.id,clip.duration*i/12,v);for(const bone of Object.values(pose.bones))for(const key of ['root','tip'])if(bone[key].some(x=>!Number.isFinite(x)))throw Error(clip.id+' invalid joint');n++;}return n;}''')
 # A real mapping edit changes the wrist and survives JSON serialization.
 point=page.evaluate('universal.engine.rig.views[0].armRl.tip');box=page.locator('#map').bounding_box();x=box['x']+(point[0]+32)/128*box['width'];y=box['y']+(point[1]+32)/128*box['height']
 page.mouse.move(x,y);page.mouse.down();page.mouse.move(x+5,y+3,steps=3);page.mouse.up()
 assert page.evaluate('universal.engine.rig.views[0].armRl.tip')!=point
 page.click('#resetmap');assert page.evaluate('universal.engine.rig.views[0].armRl.tip')==point
 for index,(name,clip) in enumerate(library['clips'].items()):
  count=max(6,int(np.ceil(clip['duration']*12))+1)
  data=base64.b64decode(page.evaluate('([id,n])=>bakeClip(id,n).toDataURL().split(",")[1]',[name,count]));folder=exports/name;folder.mkdir(exist_ok=True);dest=folder/'Human-mapping-preview.png';dest.write_bytes(data);im=Image.open(dest).convert('RGBA');assert im.size==(768,192*count),(name,im.size)
  unique=set();clipped=[]
  for r in range(count):
   for d in range(4):
    cell=im.crop((d*192,r*192,(d+1)*192,(r+1)*192));b=cell.getbbox();assert b,(name,r,d,'empty')
    if b[0]==0 or b[1]==0 or b[2]==192 or b[3]==192:clipped.append([r,d])
    unique.add(hashlib.sha256(cell.tobytes()).hexdigest())
  assert not clipped,(name,'clipping',clipped)
  meta=dict(clip=name,clipData=clip,rig='human-calibration',frameSize=[192,192],bodyOrigin=[64,64],directions=['South','North','East','West'],frames=count,times=[clip['duration']*r/(count-1) for r in range(count)],bodyOnly=True,status='mapping preview; artistic review pending')
  (folder/'atlas.json').write_text(json.dumps(meta,indent=2));(folder/'clip.json').write_text(json.dumps(clip,indent=2))
  coverage.append(dict(id=name,frames=count,directions=4,cells=count*4,uniqueRenderedCells=len(unique),path=str(dest.relative_to(HERE)),status=meta['status']))
  if index%20==0:print(json.dumps(dict(baked=index+1,total=len(library['clips']))),flush=True)
 # Playback, multiple facings and source-backed category selectors.
 page.select_option('#clip','mine');page.wait_for_timeout(120);assert page.evaluate('universalFrame.every(f=>f.clip==="mine")')
 page.select_option('#weapon','weapon.spear');page.check('#bones');page.select_option('#clip','universal_flinch');page.wait_for_timeout(120)
 assert not errors,errors
 page.screenshot(path=str(HERE/'preview.png'),full_page=True);page.locator('#map').screenshot(path=str(HERE/'limb-map.png'))
 browser.close()
report=dict(clips=len(coverage),sourceKeyed=57,arenaVariants=len(library['arenaAliases']),unresolvedAliases=0,finitePoseSamples=checks,totalSpriteCells=sum(c['cells'] for c in coverage),browserErrors=errors,rigMappingEditable=True,productionArtApproved=False,liveGameIntegrated=False)
(HERE/'coverage.json').write_text(json.dumps(coverage,indent=2));(HERE/'verification.json').write_text(json.dumps(report,indent=2))
with zipfile.ZipFile(ROOT/'Dungeon Master Sample/GOA Universal Animation Library.zip','w',zipfile.ZIP_DEFLATED) as z:
 for name in ['clips.json','source-clips.json','human-rig.json','coverage.json','verification.json','README.md','engine.js']:
  z.write(HERE/name,name)
 for base in [HERE/'exports',HERE/'assets']:
  for f in base.rglob('*'):
   if f.is_file():z.write(f,f.relative_to(HERE))
print(json.dumps(report),flush=True)
