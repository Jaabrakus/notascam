"""Check each action family, four directions, toggles and sprite export bounds."""
from pathlib import Path
from playwright.sync_api import sync_playwright
from PIL import Image
import base64,json,hashlib,zipfile
HERE=Path(__file__).resolve().parent
reports=[]
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless=True)
 page=browser.new_page(viewport=dict(width=1200,height=800));errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto((HERE/'index.html').as_uri());page.wait_for_function('window.demoReady===true')
 for family in ['spear-jab','spear-sweep','sword','longsword','scimitar','axe','battleaxe','mace','morningstar','hammer','dagger','bow','staff']:
  page.select_option('#loadout',family);page.select_option('#motion','attack')
  seen=set()
  for _ in range(29):
   seen.add(page.evaluate('demo.state.frame'));page.wait_for_timeout(50)
  expected=set(range(3 if family in ['spear-jab','bow','staff'] else 4));assert seen==expected,(family,seen)
  page.click('#play');page.click('#step');page.wait_for_timeout(40);assert page.locator('#play').inner_text()=='Resume'
  sheet=base64.b64decode(page.evaluate('sampleSheet().toDataURL().split(",")[1]'))
  dest=HERE/'combat'/('Human-'+family+'-actions.png');dest.write_bytes(sheet)
  meta=page.evaluate('combatMetadata()');assert meta['frameSize']==[128,128]
  if meta['family'] in ['one-hand-sweep','spear-jab']:
   assert meta['weaponHands']==1 and len(meta['grips'])==(3 if family=='spear-jab' else 4)
   assert all('support' not in g and 'shield' in g for row in meta['grips'] for g in row)
   page.check('#shield');page.wait_for_timeout(40);assert page.evaluate('demo.state.loadout.shield.id')=='shield.round'
   page.uncheck('#shield')
  (dest.with_suffix('.json')).write_text(json.dumps(meta,indent=2))
  body=Image.open(HERE/'combat'/('body.png' if meta['family']=='sword' else ('spear-one-hand-sweep' if meta['family']=='one-hand-sweep' else 'spear-short-jab' if meta['family']=='spear-jab' else meta['family'])+'/body.png'))
  for r,row in enumerate(meta['grips']):
   for d,grip in enumerate(row):
    x,y=grip['weapon'];assert body.getpixel((d*64+x,r*64+y))[3]>128,(family,r,d,'grip off body')
  if family=='spear-jab':
   profile=meta['jabProfile'];assert profile['lengthProjection'][0]<.5 and profile['lengthProjection'][1]<.5 and profile['shaftWidthRatio']==.65
   for d in range(4):
    points=[row[d]['weapon'] for row in profile['grips']]
    assert max(((x-a)**2+(y-b)**2)**.5 for x,y in points for a,b in points)<=profile['maxGripTravel']
   root=page.evaluate('demo.rootFor({index:1,u:.5},2)');assert 0<root['height']<=2.2
   assert meta['rootMotion']['sharedBodyAndEquipment']
  im=Image.open(dest);row_count=len(meta['rows']);assert im.size==(512,row_count*128);hashes=set()
  for r in range(row_count):
   for d in range(4):
    cell=im.crop((d*128,r*128,(d+1)*128,(r+1)*128));box=cell.getbbox();assert box and box[0]>0 and box[1]>0 and box[2]<128 and box[3]<128,(family,r,d,'clipping');hashes.add(hashlib.sha256(cell.tobytes()).hexdigest())
  assert len(hashes)==row_count*4,(family,'duplicate cells')
  page.uncheck('#weapon');page.wait_for_timeout(40);assert page.evaluate('demo.state.loadout.weapon.id') is None;page.check('#weapon')
  page.select_option('#motion','hold');page.wait_for_timeout(40);assert page.evaluate('demo.state.frame')==0
  page.screenshot(path=str(HERE/'combat'/(family+'-preview.png')))
  reports.append(dict(weapon=family,observedRows=sorted(seen),uniqueCells=len(hashes),clippedCells=0))
  if family in ['spear-jab','spear-sweep','sword','hammer','bow','staff']:
   frames=[];duration=sum(p['ms'] for p in meta['phases']);step=80
   for time in range(0,duration,step):
    raw=base64.b64decode(page.evaluate('t=>animationSheet(t).toDataURL().split(",")[1]',time))
    from io import BytesIO
    strip=Image.open(BytesIO(raw)).resize((1024,256),Image.Resampling.NEAREST);bg=Image.new('RGB',strip.size,'#20343b');bg.paste(strip,mask=strip.getchannel('A'));frames.append(bg)
   frames[0].save(HERE/'combat'/(family+'-loop.gif'),save_all=True,append_images=frames[1:],duration=step,loop=0)
  page.select_option('#motion','attack');page.click('#play')
 flinch_reports=[]
 page.select_option('#motion','flinch')
 for weapon in ['spear-jab','sword','hammer','bow','staff']:
  page.select_option('#loadout',weapon);page.wait_for_timeout(100)
  if page.locator('#play').inner_text()=='Resume':page.click('#play')
  seen=set()
  for _ in range(14):seen.add(page.evaluate('demo.state.frame'));page.wait_for_timeout(40)
  assert seen=={0,1,2},(weapon,'flinch playback',seen)
  meta=page.evaluate('combatMetadata()');assert meta['action']=='flinch' and len(meta['rows'])==3
  page.click('#play')
  data=base64.b64decode(page.evaluate('sampleSheet().toDataURL().split(",")[1]'))
  (HERE/'combat'/('Human-'+weapon+'-flinch.png')).write_bytes(data)
  (HERE/'combat'/('Human-'+weapon+'-flinch.json')).write_text(json.dumps(meta,indent=2))
  if weapon=='spear-jab':
   from io import BytesIO
   frames=[]
   for time in range(0,360,40):
    raw=base64.b64decode(page.evaluate('t=>animationSheet(t).toDataURL().split(",")[1]',time));strip=Image.open(BytesIO(raw)).resize((1024,256),Image.Resampling.NEAREST);bg=Image.new('RGB',strip.size,'#20343b');bg.paste(strip,mask=strip.getchannel('A'));frames.append(bg)
   frames[0].save(HERE/'combat/universal-flinch/flinch-loop.gif',save_all=True,append_images=frames[1:],duration=40,loop=0)
  flinch_reports.append(weapon)
 page.select_option('#motion','hold');page.click('#hit');page.wait_for_timeout(40);assert page.locator('#motion').input_value()=='flinch';page.wait_for_timeout(500);assert page.locator('#motion').input_value()=='hold'
 assert not errors,errors
 browser.close()
for family in ['bow']:
 registration=json.loads((HERE/'combat'/family/'registration.json').read_text());assert registration['northSouthCorrection']
arrow=Image.open(HERE/'combat/arrow.png').convert('RGBA');arrows=Image.new('RGBA',(256,64))
for d,angle in enumerate([-90,90,0,180]):
 piece=arrow.rotate(angle,expand=True,resample=Image.Resampling.NEAREST);arrows.paste(piece,(d*64+32-piece.width//2,32-piece.height//2))
arrows.save(HERE/'combat/arrow-directions-64.png')
(HERE/'combat/verification.json').write_text(json.dumps(dict(variants=reports,browserErrors=errors,northSouthCorrected=True,universalFlinchWeapons=flinch_reports),indent=2))
root=HERE.parents[2]
with zipfile.ZipFile(root/'Dungeon Master Sample/GOA Human Combat Samples.zip','w',zipfile.ZIP_DEFLATED) as z:
 for f in (HERE/'combat').rglob('*'):
  if f.relative_to(HERE/'combat').parts[0] in ['spear-sweep','spear'] or f.name.startswith('Human-spear-actions'):continue
  if f.is_file() and (f.name.endswith('-actions.png') or f.name.endswith('-actions.json') or f.name.endswith('-flinch.png') or f.name.endswith('-flinch.json') or f.name in ['body.png','arrow.png','arrow-directions-64.png','prompt.txt','west-prompt.txt','north-south-prompt.txt','generation.json','west-generation.json','registration.json','rig.json']):z.write(f,f.relative_to(HERE))
 z.write(HERE/'README.md','README.md')
 z.write(HERE/'EQUIPMENT_RULES.md','EQUIPMENT_RULES.md')
print(json.dumps(dict(variants=len(reports),uniqueCells=sum(r['uniqueCells'] for r in reports),browserErrors=errors)))
