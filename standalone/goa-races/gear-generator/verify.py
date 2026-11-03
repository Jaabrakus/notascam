"""Validate generated gear frames, item mappings, local gallery and archive."""
import asyncio
import json
from pathlib import Path
import zipfile
from PIL import Image
from playwright.async_api import async_playwright

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
OUT=HERE/'generated'


def read(path):return json.loads(path.read_text())


async def main():
    report=read(OUT/'generation-report.json');index=read(OUT/'index.json')
    catalog=read(HERE.parent/'armory/catalog.json');fits=read(OUT/'body-fits.json')
    assert len(index['assets'])==sum(len(item['materials']) for item in catalog['items'])==454
    assert len(index['previews'])==report['itemPreviews']==63*report['fittedPreviewBodies']
    mapping=read(OUT/'game-items.json')
    assert len(mapping['matched'])==mapping['definitions']==354 and not mapping['missing']
    assert len({row['gameId'] for row in mapping['matched']})==354
    assert len(fits)==94 and all(len(b['frames'])==b['frameCount'] for b in fits)
    assert all(b['frameCount']==1 for b in fits if b['status']=='standing_only')
    assets={(a['id'],a['material']):a for a in index['assets']}
    assert all((r['design'],r['material']) in assets for r in mapping['matched'])
    checked=0;animated=0;source_frames=0
    for row in index['assets']:
        folder=OUT/row['path'];manifest=read(folder/'manifest.json')
        for name in row['images']:
            with Image.open(folder/name) as im:
                assert im.mode=='RGBA' and im.getchannel('A').getbbox(),str(folder/name)
                assert im.getchannel('A').getextrema()[0]==0
                layer=row['images'].index(name)
                frames=[f for f in manifest['frames'] if f.get('layer',0)==layer]
                assert frames
                for frame in frames:
                    x,y,w,h=frame['rect'];assert x>=0 and y>=0 and x+w<=im.width and y+h<=im.height
                    tile=im.crop((x,y,x+w,y+h));assert bool(tile.getchannel('A').getbbox())==frame.get('visible',True)
                    if manifest['renderer']=='gear16':
                        b=tile.getchannel('A').getbbox();assert b and b[0]>0 and b[1]>0 and b[2]<w and b[3]<h
                source_frames+=len(frames);checked+=1
        if manifest['renderer']=='gear16':
            assert all(sum(f['pose']==pose for f in manifest['frames'])==16 for pose in range(manifest['sourceFrameCount']))
    for row in index['previews']:
        folder=(OUT/row['path']).parent;manifest=read(folder/'manifest.json')
        for name in ['equipped.png','equipment-layer.png']:
            with Image.open(folder/name) as im:
                assert im.width==768 and im.height%192==0
                for f in manifest['frames']:
                    x,y,w,h=f['rect'];assert (w,h)==(192,192)
                    tile=im.crop((x,y,x+w,y+h));b=tile.getchannel('A').getbbox()
                    # A hidden gear layer can be empty, but no nonempty tile may clip.
                    if b:assert b[0]>0 and b[1]>0 and b[2]<w and b[3]<h,(str(folder),f)
                    if name=='equipped.png':assert b
                if name=='equipped.png' and im.height>192:
                    assert len({im.crop((0,f*192,192,f*192+192)).tobytes() for f in range(im.height//192)})>1
                    animated+=1
                checked+=1
    for source in (OUT/'sets').glob('*/*.png'):
        with Image.open(source) as im:assert im.getchannel('A').getbbox()
        checked+=1
    starter=OUT/'deepguard-pixel-starter'
    for part in read(starter/'manifest.json')['parts']:assert (starter/part['file64']).exists()
    archive=ROOT/'Dungeon Master Sample/Generated Matching Gear.zip'
    with zipfile.ZipFile(archive) as bundle:
        assert bundle.testzip() is None
        assert all(str(path.relative_to(OUT)) in bundle.namelist() for path in OUT.rglob('*') if path.is_file() and path.name!='verification.json')
    errors=[]
    async with async_playwright() as pw:
        browser=await pw.chromium.launch(executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless=True)
        try:
            page=await browser.new_page(viewport=dict(width=1350,height=1100))
            page.on('pageerror',lambda error:errors.append(str(error)))
            await page.route('**/*',lambda route:route.continue_() if route.request.url.startswith(('file:','data:')) else route.abort())
            await page.goto((OUT/'index.html').as_uri())
            await page.wait_for_function('image?.complete && image.naturalWidth===768')
            for body in ['human','dwarf','elf','dark-elf','orc','goblin','kobold']:
                await page.select_option('#body',body)
                await page.wait_for_function('(b)=>image?.src.endsWith("/"+b+".png") && image.complete',arg=body)
            await page.select_option('#mode','item');await page.select_option('#item','weapon.halberd')
            await page.wait_for_function('image?.src.includes("weapon.halberd") && image.complete')
            await page.select_option('#assetItem','chest.plate')
            await page.select_option('#material','iron')
            await page.wait_for_function('document.getElementById("sourceSheet").complete && document.getElementById("sourceSheet").naturalWidth>0')
            assert await page.locator('#error').inner_text()==''
            assert not errors,errors
            await page.select_option('#mode','sets');await page.select_option('#body','human');await page.select_option('#set','iron')
            await page.wait_for_function('image?.src.endsWith("/iron/human.png") && image.complete')
            await page.screenshot(path=str(OUT/'gallery-preview.png'),full_page=True)
        finally:await browser.close()
    result=dict(status='passed',assetVariants=454,gameDefinitions=354,bodyFits=94,itemPreviews=len(index['previews']),walkingSheets=animated,sourceFrames=source_frames,pngFilesChecked=checked,browserErrors=errors)
    (OUT/'verification.json').write_text(json.dumps(result,indent=2))
    # Rebuild so repeat verification replaces the prior screenshot and report.
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as bundle:
        for path in OUT.rglob('*'):
            if path.is_file():bundle.write(path,path.relative_to(OUT))
    with zipfile.ZipFile(archive) as bundle:assert bundle.testzip() is None
    print(json.dumps(result),flush=True)


if __name__=='__main__':asyncio.run(main())
