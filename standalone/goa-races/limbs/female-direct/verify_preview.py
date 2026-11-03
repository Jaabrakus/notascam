"""Check every female injury preview against its actual exported PNG."""
from pathlib import Path
import base64,json
from playwright.sync_api import sync_playwright
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
records=json.loads((HERE/'all-packed.json').read_text())
assert len(records)==80 and not any(j['flags'] for j in records)
errors=[]
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless=True)
 try:
  page=browser.new_page(viewport=dict(width=1050,height=1350))
  page.on('pageerror',lambda e:errors.append(str(e)))
  page.route('**/*',lambda r:r.continue_() if r.request.url.startswith(('file:','data:')) else r.abort())
  page.goto((ROOT/'Dungeon Master Sample/All Female Limb Sheets.html').as_uri())
  assert page.locator('#pick option').count()==80
  for i,record in enumerate(records):
   page.select_option('#pick',str(i))
   page.locator('#sheet').evaluate('(im)=>im.decode()')
   assert page.locator('#sheet').is_visible()
   assert page.locator('#sheet').evaluate('(im)=>im.naturalWidth===256&&im.naturalHeight===448')
   assert page.locator('#issues').inner_text()==''
   src=page.locator('#sheet').get_attribute('src')
   assert base64.b64decode(src.split(',',1)[1])==Path(record['image']).read_bytes(),record['id']
  page.select_option('#pick','31')
  page.locator('#sheet').evaluate('(im)=>im.decode()')
  page.screenshot(path=str(HERE/'all-female-preview.png'),full_page=True)
  assert not errors,errors
 finally:browser.close()
report=dict(appearances=80,frameSize=[64,64],rows=7,columns=4,allImagesMatchExports=True,browserErrors=errors)
(HERE/'preview-verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
