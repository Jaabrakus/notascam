"""Verify source preservation, independent layers and browser fitting/export controls."""
import asyncio, hashlib, json
from pathlib import Path
from PIL import Image, ImageChops
from playwright.async_api import async_playwright
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
DEST=ROOT/'Dungeon Master Sample/Layered Deepguard Fitting'


async def main():
    data=json.loads((DEST/'manifest.json').read_text())
    for part,digest in data['sourceHashes'].items():
        path=HERE.parent/'armor-designs/deepguard-iron/pixel-fit-v2/pieces/64px'/(part+'.png')
        assert hashlib.sha256(path.read_bytes()).hexdigest()==digest
    for part,digest in data['fullSourceHashes'].items():
        path=HERE.parent/'armor-designs/deepguard-iron/pixel-fit-v2/pieces/full-resolution'/(part+'.png')
        assert hashlib.sha256(path.read_bytes()).hexdigest()==digest
    for p in data['profiles']:
        base=Image.open(DEST/p['base']).convert('RGBA');composed=base.copy()
        assert base.size==(256,64)
        for slot,mask in p.get('coverage',{}).items():
            composed.paste((0,0,0,0),(0,0,256,64),Image.open(DEST/mask).getchannel('A'))
        for slot in p['layerOrder']:
            layer=Image.open(DEST/p['layers'][slot]).convert('RGBA')
            assert layer.size==(256,64) and layer.getchannel('A').getextrema()[0]==0
            assert layer.getchannel('A').getbbox()
            for v in range(4):
                bounds=layer.crop((v*64,0,v*64+64,64)).getchannel('A').point(lambda a:255 if a>=128 else 0).getbbox()
                assert not bounds or (bounds[0]>0 and bounds[1]>0 and bounds[2]<64 and bounds[3]<64)
            composed.alpha_composite(layer)
        assert composed.tobytes()==Image.open(DEST/p['equipped']).tobytes()
        assert ImageChops.difference(composed,base).getbbox()
        for v,d in enumerate(data['directionOrder']):
            frame=Image.open(DEST/p['id']/('Deepguard_'+p['id']+'_'+d+'_64px.png'))
            assert frame.tobytes()==composed.crop((v*64,0,v*64+64,64)).tobytes()
        helmet=Image.open(DEST/p['layers']['helmet'])
        for v in [0,2,3]:
            eyes=[]
            for y in range(16,34):
                for x in range(20,44):
                    c=base.getpixel((v*64+x,y))
                    bright=(c[0]>125 and c[1]>115 and c[2]<80) if p['id']=='goblin' else min(c[:3])>180
                    if c[3]>128 and bright:eyes.append((x,y))
            visible=sum(helmet.getpixel((v*64+x,y))[3]<128 for x,y in eyes)
            assert eyes and visible/len(eyes)>=.85,(p['id'],v,visible,len(eyes))
    errors=[]
    async with async_playwright() as pw:
        browser=await pw.chromium.launch(executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless=True)
        try:
            page=await browser.new_page(viewport=dict(width=1440,height=1100))
            page.on('pageerror',lambda e:errors.append(str(e)))
            await page.goto((ROOT/'Dungeon Master Sample/Generated Matching Gear.html').as_uri())
            await page.get_by_role('link',name='Open the layered Deepguard fitting demo — human, dwarf and goblin').click()
            await page.wait_for_function('document.body.dataset.ready==="true"')
            assert await page.locator('#body option').count()==3
            assert await page.locator('#slots input').count()==8
            for p in data['profiles']:
                await page.select_option('#body',p['id'])
                before=await page.evaluate('document.querySelector("#views canvas").toDataURL()')
                await page.click('#none')
                bare=await page.evaluate('document.querySelector("#views canvas").toDataURL()')
                assert bare!=before
                assert await page.locator('#slots input:checked').count()==0
                await page.click('#all')
                assert await page.evaluate('document.querySelector("#views canvas").toDataURL()')==before
            await page.select_option('#body','human')
            await page.locator('details summary').click()
            await page.select_option('#adjustSlot','helmet')
            await page.select_option('#adjustFacing','0')
            before=await page.evaluate('Array.from(document.querySelectorAll("#views canvas"),c=>c.toDataURL())')
            await page.fill('#dx','2')
            after=await page.evaluate('Array.from(document.querySelectorAll("#views canvas"),c=>c.toDataURL())')
            assert after[0]!=before[0] and after[1:]==before[1:]
            async with page.expect_download() as export:
                await page.click('#downloadSheet')
            downloaded=await export.value
            exported=HERE/'verification-export.png'
            await downloaded.save_as(exported)
            assert Image.open(exported).size==(256,64)
            async with page.expect_download() as export:
                await page.click('#downloadFit')
            recipe=await export.value
            saved=HERE/'verification-recipe.json'
            await recipe.save_as(saved)
            assert json.loads(saved.read_text())['offsets']['human']['helmet'][0]['x']==2
            await page.click('#reset')
            assert await page.locator('#dx').input_value()=='0'
            await page.set_input_files('#importFit',str(saved))
            await page.wait_for_function('document.getElementById("message").textContent==="Fitting recipe loaded."')
            assert await page.locator('#dx').input_value()=='2'
            await page.reload()
            await page.wait_for_function('document.body.dataset.ready==="true"')
            assert await page.evaluate('fittingDemo.recipe().offsets.human.helmet[0].x')==2
            await page.locator('details summary').click()
            await page.click('#reset')
            await page.locator('details summary').click()
            await page.select_option('#comparison','base')
            await page.select_option('#comparison','equipped')
            await page.screenshot(path=str(DEST/'Viewer_Preview.png'),full_page=True)
            assert not errors, errors
        finally:
            await browser.close()
    result=dict(status='passed',profiles=3,slots=8,directions=4,exportedFrames=12,
        sourceHashesUnchanged=True,compositionMatchesLayers=True,bodyOnlyToggle=True,eyeOpeningsClear=True,layerEdgesClear=True,
        perFacingAdjustments=True,pngExport=True,recipeRoundTrip=True,persistence=True,browserErrors=errors,
        scope='Standing fitting demo only; visual fit remains subject to art review.')
    (DEST/'verification.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result))


if __name__=='__main__':asyncio.run(main())

