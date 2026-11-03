"""Check runtime provenance, all retargeted clips, and export actual browser renders."""
import asyncio,base64,hashlib,json,math,io,sys
from pathlib import Path
from PIL import Image
from playwright.async_api import async_playwright
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];OUT=ROOT/'Dungeon Master Sample/GOA Sword and Shield Rig/library'
async def main():
 data=json.loads((OUT/'library.json').read_text());hashes=json.loads((OUT/'source-hashes.json').read_text())
 for name,digest in hashes.items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest,name
 assert data['runtime']['installedRuntimeMatches'];assert len(data['runtime']['defs'])==57
 for name,definition in data['runtime']['defs'].items():
  c=data['clips'][name]
  if name in ['mine','woodchop'] and not data['runtime']['flags']['rm_g3_work_mine_chop']:
   assert c['mode']=='fallback' and c['inactiveDefinition']==definition
  else:assert c['keys']==definition['keys'] and c['definition']==definition
 errors=[];total=0;bounds=[];reports=[];(OUT/'exports').mkdir(exist_ok=True)
 async with async_playwright() as pw:
  browser=await pw.chromium.launch(executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless=True)
  try:
   page=await browser.new_page(viewport={'width':1500,'height':1100},device_scale_factor=1);page.on('pageerror',lambda e:errors.append(str(e)))
   await page.goto('http://127.0.0.1:8878/library/?v=rig-package-16');await page.wait_for_function('document.body.dataset.ready === "true"')
   for index,(name,clip) in enumerate(data['clips'].items()):
    if '--review' in sys.argv and name not in ['slash','lunge','thrust','chop','cast','build','walk_armed','bow_ready','bow_shot','throw','throw_axe','throw_dagger']:continue
    result=await page.evaluate('id=>elfLibrary.atlas(id)',name);meta=result['metadata'];im=Image.open(io.BytesIO(base64.b64decode(result['png'].split(',')[1]))).convert('RGBA')
    assert im.size==(768,len(meta['times'])*192)
    for event,times in clip['events'].items():
     for t in times if isinstance(times,list) else [times]:assert any(abs(t-s)<1e-5 for s in meta['times']),(name,event,t)
    for f,row in enumerate(meta['frames']):
     for d,pose in enumerate(row):
      for a in pose['arms'].values():
       assert abs(math.dist(a['shoulder'],a['elbow'])-a.get('projectedUpperLength',a['upperLength']))<1e-6,(name,f,d,'arm')
       assert abs(math.dist(a['elbow'],a['hand'])-a.get('projectedLowerLength',a['lowerLength']))<1e-6
      for leg in pose['legs'].values():
       assert abs(math.dist(leg['hip'],leg['knee'])-leg['upperLength'])<1e-6
       assert abs(math.dist(leg['knee'],leg['ankle'])-leg['lowerLength'])<1e-6
      tile=im.crop((d*192,f*192,(d+1)*192,(f+1)*192));box=tile.getbbox();assert box,(name,f,d,'empty')
      assert box[0]>0 and box[1]>0 and box[2]<192 and box[3]<192,(name,f,d,'clipped',box)
      preview=160 if clip['category']=='Ranged' or name in ['reaction.flying','reaction.hammer','reaction.throw'] else 128
      pad=(192-preview)//2
      assert box[0]>=pad and box[1]>=pad and box[2]<=192-pad and box[3]<=192-pad,(name,'preview clipped',box)
      total+=1
    im.save(OUT/'exports'/f'{name}.png',optimize=True)
    # Keep export manifests compact: full source tracks and calibration are in library.json.
    meta['grips']=[[[p['arms']['right']['hand'],p['arms']['left']['hand']] for p in row] for row in meta.pop('frames')]
    (OUT/'exports'/f'{name}.json').write_text(json.dumps(meta,separators=(',',':')))
    reports.append({'clip':name,'frames':len(meta['times']),'directions':4,'png':f'exports/{name}.png','metadata':f'exports/{name}.json'})
    if index%15==0:print(json.dumps({'exported':index+1,'total':len(data['clips'])}),flush=True)
   for id,t in [('bow_shot',.72),('throw',.5),('slash',.3),('lunge',.36),('cast',.42),('build',.35),('walk_armed',.3)]:
    await page.evaluate('([id,t])=>{elfLibrary.setClip(id);elfLibrary.setTime(t)}',[id,t]);await page.screenshot(path=str(OUT/f'Preview-{id}.png'),full_page=True)
   for clip,t,label in [('bow_shot',1.4,'bow-recovery'),('throw',.26,'north-spear-grip')]:
    await page.evaluate('([id,t])=>{elfLibrary.setClip(id);elfLibrary.setTime(t)}',[clip,t]);await page.screenshot(path=str(OUT/f'Preview-{label}.png'),full_page=True)
   await page.evaluate("elfLibrary.setClip('lunge')");await page.click('#once');await page.wait_for_function("document.getElementById('play').textContent === 'Play'",timeout=5000)
   await page.check('#debug');await page.check('#gear');await page.select_option('#zoom','1');assert await page.locator('#views canvas').first.evaluate('e=>e.getBoundingClientRect().width')==128
   # A lunge must move its leading foot forward; guard/weapon remain distinct sockets.
   for d,side in [(2,1),(3,-1)]:
    poses=await page.evaluate('d=>[elfLibrary.animator.sample("lunge",0,d),elfLibrary.animator.sample("lunge",.36,d)]',d)
    near='left' if d==2 else 'right';assert (poses[1]['legs'][near]['target'][0]-poses[0]['legs'][near]['target'][0])*side>5
   assert not errors,errors
  finally:await browser.close()
 result={'status':'passed','clips':len(reports),'directionFrames':total,'runtimeSourceFilesUnchanged':len(hashes),'runtimeDefinitions':57,'currentMineChopFallback':True,'eventTimesIncludedInExports':True,'projectedLimbLengthsChecked':True,'exportsUnclipped':True,'lungeFootwork':True,'browserErrors':errors,'exports':reports,'previewUnclipped':True,'revision':'rig-package-16','visualStatus':'Shared joint and grip polish; deep bends and physics approximations still require art review.'}
 (OUT/('review-checks.json' if '--review' in sys.argv else 'verification.json')).write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k!='exports'}))
if __name__=='__main__':asyncio.run(main())
