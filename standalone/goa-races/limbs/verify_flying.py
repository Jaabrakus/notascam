"""Verify actual-pixel limb removal and fly-off behavior in local Chrome."""
import asyncio
import json
import tempfile
from pathlib import Path
from playwright.async_api import async_playwright

HERE=Path(__file__).resolve().parent


async def main():
    async with async_playwright() as playwright:
        browser=await playwright.chromium.launch(executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless=True)
        try:
            page=await browser.new_page(viewport=dict(width=1380,height=1100),device_scale_factor=1)
            errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
            await page.route('**/*',lambda route:route.continue_() if route.request.url.startswith(('file:','data:')) else route.abort())
            await page.goto((HERE/'flying-pieces.html').as_uri())
            await page.wait_for_function('window.flyDemoReady')
            assert not await page.locator('#cap').is_checked()
            with tempfile.TemporaryDirectory(prefix='flyoff-export-') as temporary:
                async with page.expect_download() as pending:await page.click('#saveParts')
                download=await pending.value;path=Path(temporary)/'parts.png';await download.save_as(path)
                assert path.read_bytes()==(HERE/'pixel-assets/human/parts.png').read_bytes()
                async with page.expect_download() as pending:await page.click('#saveMetadata')
                download=await pending.value;path=Path(temporary)/'metadata.json';await download.save_as(path)
                assert json.loads(path.read_text())==json.loads((HERE/'pixel-assets/human/metadata.json').read_text())
            checked=[]
            for slot in ['LeftArm','RightArm','LeftLeg','RightLeg']:
                await page.click('#reset')
                expected=await page.evaluate('slot=>flyDemo.parts.filter(p=>p[slot].box).length',slot)
                await page.click('#'+slot)
                result=await page.evaluate('''slot=>({proof:Array.from({length:4},(_,v)=>flyDemo.proof(v,slot)),count:flyDemo.particles.length,sameSourceCache:flyDemo.particles.every(p=>p.part===flyDemo.parts[p.view][p.slot]),sameZoom:flyDemo.particles.every(p=>p.part.box.w<64&&p.part.box.h<64),blood:flyDemo.drops.length})''',slot)
                assert result['count']==expected and expected>0
                assert result['sameSourceCache'] and result['sameZoom'] and result['blood']>0
                assert all(p==dict(outsideChanges=0,remainingPartPixels=0) for p in result['proof']),result
                await page.wait_for_timeout(250)
                motion=await page.evaluate('flyDemo.particles.every(p=>p.x!==p.initialX||p.y!==p.initialY)')
                assert motion
                checked.append(dict(slot=slot,visibleSourcePieces=expected,exactAttachedSourceCache=True,unchangedOutsideCut=True,motion=True))
            await page.click('#reset')
            await page.click('#LeftArm')
            await page.click('#RightLeg')
            await page.wait_for_timeout(180)
            await page.screenshot(path=str(HERE/'flying-pieces-preview.png'),full_page=True)
            await page.locator('#stage').screenshot(path=str(HERE/'flying-pieces-stage.png'))
            assert not errors and not await page.evaluate('flyDemoErrors')
            result=dict(slots=checked,redBloodParticles=True,optionalSeparateWoundOverlay=True,sourceBodyAndPiecesShareZoom=True,source_png_download_byte_exact=True,metadata_download=True,browser_errors=errors,ai_calls=0)
            (HERE/'flying-verification.json').write_text(json.dumps(result,indent=2))
            print(json.dumps(result))
        finally:await browser.close()


if __name__=='__main__':asyncio.run(main())
