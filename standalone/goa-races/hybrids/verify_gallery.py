"""Test actual playback and export the gallery's 64-pixel atlases. No AI calls."""
import asyncio,base64,json,hashlib,zipfile
from pathlib import Path
from io import BytesIO
from PIL import Image,PngImagePlugin
from playwright.async_api import async_playwright
HERE=Path(__file__).resolve().parent

async def main():
 output=HERE/'packed';output.mkdir(exist_ok=True);report=[];errors=[]
 async with async_playwright() as p:
  browser=await p.chromium.launch(executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless=True)
  try:
   page=await browser.new_page(viewport=dict(width=1380,height=1050));page.on('pageerror',lambda e:errors.append(str(e)))
   await page.route('**/*',lambda r:r.continue_() if r.request.url.startswith(('file:','data:')) else r.abort())
   await page.goto((HERE/'index.html').as_uri());await page.wait_for_function('window.galleryReady===true')
   races=await page.locator('#race option').evaluate_all('(o)=>o.map(x=>x.value)')
   for name in races:
    await page.select_option('#race',name)
    kinds=await page.locator('#kind option').evaluate_all('(o)=>o.map(x=>x.value)')
    for kind in kinds:
     if not await page.locator('#kind').is_disabled():await page.select_option('#kind',kind)
     await page.wait_for_function('([r,k])=>galleryFrame.race===r&&galleryFrame.kind===k',arg=[name,kind])
     data=await page.evaluate('({png:gallery.current().atlas.toDataURL(),meta:gallery.metadata(),animated:gallery.current().walking})')
     folder=output/name/kind;folder.mkdir(parents=True,exist_ok=True)
     raw=base64.b64decode(data['png'].split(',',1)[1]);(folder/'sprites.png').write_bytes(raw);(folder/'atlas.json').write_text(json.dumps(data['meta'],indent=2))
     im=Image.open(BytesIO(raw));assert im.width==256 and im.height==data['meta']['frames']*64
     checks=[]
     for d in range(4):
      cells=[im.crop((d*64,f*64,(d+1)*64,(f+1)*64)) for f in range(data['meta']['frames'])]
      boxes=[c.getchannel('A').point(lambda a:255 if a>128 else 0).getbbox() for c in cells]
      assert all(boxes),(name,kind,d,'empty frame')
      checks.append(dict(direction=d,uniqueFrames=len({hashlib.sha256(c.tobytes()).hexdigest() for c in cells}),footBaselineSpread=max(b[3] for b in boxes)-min(b[3] for b in boxes)))
     if kind!='base' and data['animated']:
      assert all(c['uniqueFrames']==3 for c in checks),(name,kind,'missing distinct hybrid poses')
      assert all(c['footBaselineSpread']<=1 for c in checks),(name,kind,'hybrid foot drift')
     if data['animated']:
      observed=set()
      for _ in range(18):observed.add((await page.evaluate('galleryFrame'))['row']);await page.wait_for_timeout(60)
      assert observed==set(range(data['meta']['frames'])),(name,observed)
      assert all(c['uniqueFrames']>1 for c in checks),(name,'repeated standing images')
      sequence=data['meta']['sequence'];atlas=Image.new('RGBA',(256,64*len(sequence)))
      for y,frame in enumerate(sequence):atlas.paste(im.crop((0,frame*64,256,(frame+1)*64)),(0,y*64))
      state='Normal' if name in ['Night Elf','Orc','Kobold','Elf'] else ''
      desc='# BEGIN DMI\nversion = 4.0\n\twidth = 64\n\theight = 64\nstate = "'+state+'"\n\tdirs = 4\n\tframes = '+str(len(sequence))+'\n\tdelay = '+','.join(['2']*len(sequence))+'\n\tmovement = '+('0' if name.endswith('Fly') else '1')+'\n# END DMI\n'
      info=PngImagePlugin.PngInfo();info.add_text('Description',desc,zip=True);atlas.save(folder/'movement.dmi',format='PNG',pnginfo=info)
      assert Image.open(folder/'movement.dmi').info['Description']==desc
     else:assert await page.locator('#play').is_disabled()
     report.append(dict(race=name,appearance=kind,frames=data['meta']['frames'],animated=data['animated'],directions=checks))
   await page.select_option('#race','DemonFly');await page.screenshot(path=str(HERE/'gallery-preview.png'),full_page=True)
   await page.select_option('#race','Human');await page.select_option('#kind','Marked')
   await page.wait_for_function('galleryFrame.race==="Human" && galleryFrame.kind==="Marked"')
   await page.locator('#stage').screenshot(path=str(HERE/'marked-human-fixed.png'))
   assert not errors,errors
  finally:await browser.close()
 (HERE/'playback-verification.json').write_text(json.dumps(dict(appearances=len(report),animated_sheets=sum(r['animated'] for r in report),sheets=report,browser_errors=errors,limb_loss_complete=False),indent=2))
 (output/'README.md').write_text('Updated GOA appearances and movement drafts. PNG cells are64x64. Movement DMI uses explicit replay phases and200ms frame timing. Consult atlas.json for movement availability. Static appearances contain only their standing design. Female bodies, armed movement and sleep are outside this export; limb loss is handled separately. Generated movement requires visual gait and identity review before game integration. The rejected full Human atlas is excluded.\n')
 target=HERE.parents[2]/'Dungeon Master Sample/GOA Updated Races and Hybrids.zip'
 with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
  for path in output.rglob('*'):
   if path.is_file():z.write(path,path.relative_to(output))
 print(json.dumps(dict(appearances=len(report),animated_sheets=sum(r['animated'] for r in report),errors=errors,archive=str(target))))

if __name__=='__main__':asyncio.run(main())
