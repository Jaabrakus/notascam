"""Verify actual female walk playback, selected sources and exported DMI layout."""
from pathlib import Path
from PIL import Image
from playwright.sync_api import sync_playwright
import json,hashlib
HERE=Path(__file__).resolve().parent
def main():
 reg=json.loads((HERE/'registration.json').read_text());assert len(reg)==80,('incomplete coverage',len(reg))
 reports=[];errors=[]
 with sync_playwright() as p:
  browser=p.chromium.launch(executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless=True)
  try:
   page=browser.new_page(viewport=dict(width=1360,height=1050))
   page.on('pageerror',lambda e:errors.append(str(e)))
   page.route('**/*',lambda r:r.continue_() if r.request.url.startswith(('file:','data:')) else r.abort())
   page.goto((HERE/'index.html').as_uri());page.wait_for_function('window.galleryReady===true')
   races=page.locator('#race option').evaluate_all('(o)=>o.map(x=>x.value)');assert len(races)==10
   for race in races:
    page.select_option('#race',race)
    kinds=page.locator('#kind option').evaluate_all('(o)=>o.map(x=>x.value)');assert len(kinds)==8,(race,kinds)
    for kind in kinds:
     page.select_option('#kind',kind);page.wait_for_function('([r,k])=>galleryFrame.race===r&&galleryFrame.kind===k',arg=[race,kind])
     meta=page.evaluate('gallery.metadata()');assert meta['race']==race and meta['sex']=='female' and meta['appearance']==kind
     assert meta['frames']==3 and meta['sequence']==[0,1,0,2] and meta['frameSize']==[64,64]
     assert page.evaluate('gallery.current().walking') and not page.locator('#play').is_disabled()
     observed=set()
     for _ in range(18):observed.add(page.evaluate('galleryFrame.row'));page.wait_for_timeout(60)
     assert observed=={0,1,2},(race,kind,'missing playback poses',observed)
     folder=HERE/'assets'/race/kind;im=Image.open(folder/'sprites.png').convert('RGBA');assert im.size==(256,192)
     checks=[]
     for d in range(4):
      cells=[im.crop((d*64,row*64,(d+1)*64,(row+1)*64)) for row in range(3)]
      boxes=[c.getchannel('A').point(lambda a:255 if a>128 else 0).getbbox() for c in cells]
      assert all(boxes) and len({hashlib.sha256(c.tobytes()).hexdigest() for c in cells})==3,(race,kind,d,'empty or duplicate poses')
      assert all(b[0]>=1 and b[1]>=1 and b[2]<=63 and b[3]<=63 for b in boxes),(race,kind,d,'clipping')
      drift=max(b[3] for b in boxes)-min(b[3] for b in boxes);assert drift<=1,(race,kind,d,'foot drift')
      checks.append(dict(direction=d,uniqueFrames=3,footBaselineSpread=drift))
     dmi=Image.open(folder/'movement.dmi');assert dmi.size==(256,256)
     desc=dmi.info['Description'];assert '\tframes = 4' in desc and '\tdirs = 4' in desc and '\tmovement = 1' in desc
     reports.append(dict(race=race,sex='female',appearance=kind,observedRows=sorted(observed),directions=checks))
   page.select_option('#race','FrogMan');page.select_option('#kind','base');page.screenshot(path=str(HERE/'female-gallery-preview.png'),full_page=True)
   assert not errors,errors
  finally:browser.close()
 coverage=json.loads((HERE/'exports/coverage.json').read_text());assert len(coverage)==80 and all(r['status']=='generated walk draft' for r in coverage)
 assert len({r['image'] for r in coverage})==80 and all('-Female-' in r['image'] for r in coverage)
 (HERE/'playback-verification.json').write_text(json.dumps(dict(appearances=len(reports),sourceCells=960,browserErrors=errors,sheets=reports,artisticGaitApproved=False,gearFittingComplete=False),indent=2))
 print(json.dumps(dict(appearances=len(reports),sourceCells=960,browserErrors=errors)))
if __name__=='__main__':main()
