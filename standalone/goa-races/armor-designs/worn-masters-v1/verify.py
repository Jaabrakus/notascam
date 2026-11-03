"""Check actual sample-page aliases, source preservation and padded exports."""
import asyncio,hashlib,json
from pathlib import Path
from PIL import Image
from playwright.async_api import async_playwright

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]


async def main():
    records=json.loads((HERE/'masters.json').read_text())['masters']
    for m in records:
        source=HERE/m['source'];assert hashlib.sha256(source.read_bytes()).hexdigest()==m['sourceSha256']
        with Image.open(HERE/m['spriteFile']) as im:
            size=m['frameSize'];assert im.mode=='RGBA' and im.size==(size*4,size)
            assert im.getchannel('A').getextrema()[0]==0
            for f in m['frames']:
                x,y,w,h=f['rect'];b=im.crop((x,y,x+w,y+h)).getchannel('A').point(lambda a:255 if a>=128 else 0).getbbox()
                assert b and b[0]>0 and b[1]>0 and b[2]<w and b[3]<h
    staff=next(m for m in records if m['id']=='deepguard-iron-staff-idle')
    spear=next(m for m in records if m['id']=='deepguard-iron-spear-shield-idle')
    assert staff['source'].endswith('-v2.png') and spear['offhand']=='shield'
    assert staff['frameSize']==spear['frameSize']==128
    errors=[]
    async with async_playwright() as pw:
        browser=await pw.chromium.launch(executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless=True)
        try:
            page=await browser.new_page(viewport=dict(width=1450,height=1000))
            page.on('pageerror',lambda e:errors.append(str(e)))
            await page.route('**/*',lambda r:r.continue_() if r.request.url.startswith(('file:','data:')) else r.abort())
            for alias in ['Generated Matching Gear.html','New Armor Worn on Races.html','Worn Armor Masters.html']:
                path=ROOT/'Dungeon Master Sample'/alias;assert path.resolve()==HERE/'index.html'
                await page.goto(path.as_uri());await page.wait_for_function('document.getElementById("art").complete && document.getElementById("art").naturalWidth>0')
                assert await page.evaluate('document.baseURI')==HERE.as_uri()+'/'
                assert await page.locator('#set option').count()==len(records)
                assert await page.locator('#set').input_value()==spear['id']
            for m in records:
                await page.select_option('#set',m['id'])
                for mode in ['artwork','sprite']:
                    await page.select_option('#mode',mode)
                    await page.wait_for_function('Array.from(document.images).every(im=>im.complete&&im.naturalWidth>0)')
                    if mode=='sprite':assert await page.evaluate('document.getElementById("art").naturalWidth')==m['frameSize']*4
            await page.select_option('#mode','artwork');await page.select_option('#set',spear['id'])
            await page.screenshot(path=str(HERE/'preview.png'),full_page=True)
            assert not errors,errors
        finally:await browser.close()
    result=dict(status='passed',masters=len(records),directionsPerMaster=4,aliasPagesChecked=3,revisedStaffActive=True,spearShieldActive=True,paddedLongWeaponFrames=128,browserErrors=errors,scope='File, crop and UI checks. Weapon-side anatomy was reviewed visually; animation and 16 facings remain pending.')
    (HERE/'review-checks.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))


if __name__=='__main__':asyncio.run(main())
