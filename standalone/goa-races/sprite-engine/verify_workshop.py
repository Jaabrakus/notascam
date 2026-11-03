"""Exercise real DMI intake, frame extraction, job persistence and export.

Uses only local Chrome and synthetic result fixtures; no AI calls or API keys.
Start serve.py first. Temporary fixture jobs are removed after verification.
"""
import asyncio
import base64
from io import BytesIO
import json
from pathlib import Path
import shutil
import tempfile
import urllib.error
import urllib.request
import zipfile

from PIL import Image
from playwright.async_api import async_playwright

HERE = Path(__file__).resolve().parent
URL = 'http://127.0.0.1:8876'


def request(path, body=None, token=None):
    headers = {}
    if token:
        headers['X-Sprite-Token'] = token
    if body is not None:
        headers['Content-Type'] = 'application/json'
    req = urllib.request.Request(URL + path, data=json.dumps(body).encode() if body is not None else None, headers=headers)
    with urllib.request.urlopen(req) as response:
        return json.load(response)


async def main():
    errors, job_ids = [], []
    with tempfile.TemporaryDirectory(prefix='goa-workshop-check-') as temporary:
        temporary = Path(temporary)
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless=True)
            try:
                page = await browser.new_page(viewport=dict(width=1560, height=1150), device_scale_factor=1)
                page.set_default_timeout(10000)
                page.on('pageerror', lambda error: errors.append(str(error)))
                await page.route('**/*', lambda route: route.continue_() if route.request.url.startswith(('file:', 'data:', URL)) else route.abort())
                await page.goto((HERE / 'index.html').as_uri())
                await page.wait_for_function('window.workshopReady')
                await page.click('#example')
                await page.wait_for_function('window.workshop.prepared!=null')
                dmi = await page.evaluate('({cells:workshop.prepared.cells.length,states:document.querySelector("#state").options.length,size:workshop.prepared.width})')
                assert dmi['states'] > 1 and dmi['size'] == 64, dmi
                animated = await page.locator('#state option').evaluate_all('(items)=>items.find(o=>/ [2-9] frames/.test(o.textContent))?.value')
                assert animated is not None
                await page.select_option('#state', animated)
                await page.wait_for_function('workshop.prepared.frames>1')
                await page.locator('#previewMode').select_option('frame')
                await page.click('#play')
                frames = set()
                for _ in range(14):
                    frames.add(await page.locator('#frame').input_value())
                    await page.wait_for_timeout(80)
                assert len(frames) > 1
                await page.click('#play')
                await page.locator('#gridSettings summary').click()
                await page.locator('#offset').fill('100000')
                await page.locator('#offset').dispatch_event('change')
                assert await page.locator('#prepare').is_disabled()
                await page.locator('#offset').fill('0')
                await page.locator('#offset').dispatch_event('change')
                assert await page.locator('#prepare').is_enabled()

                # Synthetic, transparent fixture: test exact cell ordering and packing.
                checks = await page.evaluate('''async()=>{
                  const E=SpriteEngine,cv=E.canvas(32,16),c=cv.getContext('2d');
                  for(let i=0;i<8;i++){c.fillStyle=`rgb(${20+i*25},${240-i*20},70)`;c.fillRect((i%4)*8,Math.floor(i/4)*8,7,7);}
                  const blob=await new Promise(r=>cv.toBlob(r));await workshop.importFile(new File([blob],'fixture.png',{type:'image/png'}));
                  for(const [id,value]of Object.entries({cellWidth:8,cellHeight:8,directions:4,frames:2,offset:0}))document.getElementById(id).value=value;
                  document.getElementById('frames').dispatchEvent(new Event('change'));
                  const normal=workshop.prepared.cells.map(c=>c.sourceCell);
                  document.getElementById('order').value='direction-major';document.getElementById('order').dispatchEvent(new Event('change'));
                  const reordered=workshop.prepared.cells.map(c=>c.sourceCell);
                  const packed=E.pack(cv,workshop.spec),p=packed.getContext('2d').getImageData(63,63,1,1).data;
                  const jpg=await new Promise(r=>cv.toBlob(r,'image/jpeg'));const jpeg=await E.inspect(new File([jpg],'fixture.jpg',{type:'image/jpeg'}));
                  return {normal,reordered,alpha:p[3],packed:[packed.width,packed.height],jpegIsPng:jpeg.src.startsWith('data:image/png;')};
                }''')
                assert checks['normal'] == list(range(8))
                assert checks['reordered'] == [0, 2, 4, 6, 1, 3, 5, 7]
                assert checks['packed'] == [256, 128] and checks['alpha'] == 0 and checks['jpegIsPng']
                async with page.expect_download() as pending:
                    await page.click('#downloadRequest')
                bundle = await pending.value
                await bundle.save_as(temporary / 'request.zip')
                with zipfile.ZipFile(temporary / 'request.zip') as archive:
                    assert archive.testzip() is None
                    assert set(archive.namelist()) == {'input-original.png', 'input-sheet.png', 'style-reference.png', 'request.json', 'request.md'}
                    offline_spec = json.loads(archive.read('request.json'))
                    assert offline_spec['output']['columns'] == 4
                    Image.open(BytesIO(archive.read('input-sheet.png'))).verify()

                await page.goto(URL)
                await page.wait_for_function('window.workshopReady')
                await page.click('#example')
                await page.wait_for_function('window.workshop.prepared!=null')
                await page.click('#prepare')
                await page.wait_for_function('workshop.job!=null')
                saved = await page.evaluate('workshop.job')
                job_ids.append(saved['id'])
                folder = Path(saved['path'])
                assert (folder / 'style-reference.png').read_bytes() == (HERE.parent / 'goa-races-lotr-v1.png').read_bytes()
                assert len(list(folder.iterdir())) == 5
                message = await page.locator('#requestMessage').input_value()
                assert saved['path'] in message and 'built-in image generation' in message
                # A local result fixture, explicitly not an AI redraw, tests detection.
                shutil.copyfile(folder / 'input-sheet.png', folder / 'result.png')
                await page.wait_for_function('workshop.packed!=null', timeout=15000)
                assert await page.locator('#export').is_enabled()
                async with page.expect_download() as pending:
                    await page.click('#export')
                exported = await pending.value
                await exported.save_as(temporary / 'sprites.zip')
                with zipfile.ZipFile(temporary / 'sprites.zip') as archive:
                    assert archive.testzip() is None
                    atlas = json.loads(archive.read('atlas.json'))
                    image = Image.open(BytesIO(archive.read('sprites.png')))
                    assert list(image.size) == atlas['size']
                    assert len(atlas['frames']) == saved['spec']['output']['columns'] * saved['spec']['output']['rows']
                    assert image.mode == 'RGBA'
                # Changing the source invalidates the old result. Reopening restores it.
                await page.select_option('#outputSize', '32')
                assert await page.locator('#export').is_disabled()
                await page.reload()
                await page.wait_for_function('window.workshopReady')
                await page.select_option('#jobHistory', saved['id'])
                await page.wait_for_function('workshop.packed!=null')
                assert await page.locator('#outputSize').input_value() == '64'
                info = request('/api/info')
                try:
                    request('/api/jobs', {})
                    raise AssertionError('Unauthenticated job mutation accepted')
                except urllib.error.HTTPError as error:
                    assert error.code == 403
                try:
                    request('/api/jobs', {'spec': {}}, info['token'])
                    raise AssertionError('Invalid job accepted')
                except urllib.error.HTTPError as error:
                    assert error.code == 400
                try:
                    request('/jobs/../../request.json')
                    raise AssertionError('Path traversal accepted')
                except urllib.error.HTTPError as error:
                    assert error.code == 404
                # Final screenshot shows actual source art, never the result fixture.
                await page.click('#example')
                await page.wait_for_function('workshop.prepared!=null && workshop.job===null')
                await page.locator('#previewMode').select_option('sheet')
                await page.screenshot(path=str(HERE / 'converter-preview.png'), full_page=True)
                assert not errors, errors
                assert not await page.evaluate('window.workshopErrors')
                summary = dict(dmi=dmi,animation_frames_previewed=len(frames),frame_order=checks,
                               offline_bundle=True,saved_jobs=True,result_detection=True,
                               png_atlas_export=True,job_reopen=True,request_validation=True,
                               browser_errors=errors,ai_calls=0)
                (HERE / 'verification.json').write_text(json.dumps(summary, indent=2))
                print(json.dumps(summary))
            finally:
                await browser.close()
                for job_id in job_ids:
                    shutil.rmtree(HERE / 'jobs' / job_id)


if __name__ == '__main__':
    asyncio.run(main())
