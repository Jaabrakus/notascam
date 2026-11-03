"""Verify the local armory against its actual bodies, recipes and exported pixels.

Uses a temporary Chrome profile and local files only. No AI calls or game writes.
Run after build.py has produced index.html.
"""
import asyncio
import base64
from io import BytesIO
import json
from pathlib import Path
import tempfile
import sys
import zipfile

from PIL import Image
from playwright.async_api import async_playwright

HERE = Path(__file__).resolve().parent
SLOTS = ['weapon', 'shield', 'head', 'chest', 'arms', 'legs', 'feet']


def source_boundary_report(bodies):
    """Boundary contact is an art-review signal, not proof of a clipped sprite."""
    images, warnings = {}, []
    for body in bodies:
        source = body['source']
        if source not in images:
            images[source] = Image.open(source).convert('RGBA')
        image = images[source]
        for frame, row in enumerate(body['sourceRects']):
            for view, rect in enumerate(row):
                x, y, width, height = rect
                # Source rectangles can have fractional pixel boundaries.
                tile = image.crop((round(x), round(y), round(x + width), round(y + height)))
                alpha = tile.getchannel('A').point(lambda value: 255 if value >= 160 else 0)
                w, h = tile.size
                edges = dict(top=alpha.crop((0, 0, w, 1)), bottom=alpha.crop((0, h - 1, w, h)),
                             left=alpha.crop((0, 0, 1, h)), right=alpha.crop((w - 1, 0, w, h)))
                touching = {edge: sum(bool(pixel) for pixel in pixels.getdata()) for edge, pixels in edges.items()}
                touching = {edge: count for edge, count in touching.items() if count > 2}
                if touching:
                    warnings.append(dict(body=body['id'], frame=frame, view=view, edges=touching))
    return warnings


async def settle(page):
    await page.evaluate('new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))')


async def export_pixels(page):
    return await page.evaluate('''async()=>{
      const out=await Armory.exportAtlas();
      const cv=out.canvas;
      if(!cv || typeof cv.toDataURL!=='function') throw new Error('exportAtlas must return {canvas,manifest}');
      return {png:cv.toDataURL(),manifest:out.manifest};
    }''')


def decode_export(value):
    image = Image.open(BytesIO(base64.b64decode(value['png'].split(',', 1)[1]))).convert('RGBA')
    assert image.getchannel('A').getextrema()[0] == 0, 'Export lost transparency'
    assert image.getchannel('A').getbbox(), 'Export contains no sprites'
    return image


async def main():
    catalog = json.loads((HERE / 'catalog.json').read_text())
    bodies = json.loads((HERE / 'bodies.json').read_text())['bodies']
    source_warnings = source_boundary_report(bodies)
    errors, blocked = [], []
    with tempfile.TemporaryDirectory(prefix='goa-armory-check-') as temporary:
        temporary = Path(temporary)
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(
                executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless=True)
            try:
                page = await browser.new_page(viewport=dict(width=1600, height=1150), device_scale_factor=1)
                page.set_default_timeout(15000)
                page.on('pageerror', lambda error: errors.append(str(error)))

                async def route(request):
                    if request.request.url.startswith(('file:', 'data:')):
                        await request.continue_()
                    else:
                        blocked.append(request.request.url)
                        await request.abort()

                await page.route('**/*', route)
                await page.goto((HERE / 'index.html').as_uri())
                await page.wait_for_function('window.Armory?.ready===true && Armory.frame()!=null')
                assert await page.locator('#body option').count() == len(bodies)
                human = next(body for body in bodies if body['raceKey'] == 'Human' and body['variant'] == 'Base')
                dwarf = next(body for body in bodies if body['raceKey'] == 'Dwarves' and body['variant'] == 'Base')
                standing = next(body for body in bodies if body['status'] == 'standing_only')
                await page.select_option('#body', human['id'])
                await page.select_option('#motion', 'idle')
                await settle(page)
                initial = await export_pixels(page)
                initial_image = decode_export(initial)
                initial_loadout = await page.evaluate('JSON.parse(JSON.stringify(Armory.state.loadout))')
                await page.screenshot(path=str(HERE / 'armory-preview.png'), full_page=True)
                await page.select_option('#body', dwarf['id'])
                await settle(page)
                await page.screenshot(path=str(HERE / 'dwarf-equipped.png'), full_page=True)
                await page.select_option('#body', human['id'])
                for slot in SLOTS:
                    await page.select_option('#' + slot, '')
                await page.select_option('#weapon', 'goa.sword')
                await page.select_option('#chest', 'goa.chest')
                await settle(page)
                await page.locator('#strip').screenshot(path=str(HERE / 'goa-sword-fitted.png'))
                await page.locator('#stage').screenshot(path=str(HERE / 'goa-armor-equipped.png'))
                goa_adaptation = await page.evaluate('Armory.catalog.items.find(i=>i.id==="goa.sword").fitAdaptation||null')
                await page.select_option('#body', human['id'])
                print('Initial screenshots saved.', flush=True)

                # Every design/material recipe must execute the real renderer.
                combinations = await page.evaluate('''async()=>{
                  const checked=[];
                  const slots=['weapon','shield','head','chest','arms','legs','feet'];
                  function clearSlots(){for(const slot of slots){const control=document.getElementById(slot);const empty=[...control.options].find(o=>o.value===''||o.value==='none');if(!empty)throw new Error('Missing None option for '+slot);control.value=empty.value;control.dispatchEvent(new Event('change'));}}
                  clearSlots();
                  const bare=await Armory.exportAtlas(),base=bare.canvas.getContext('2d').getImageData(0,0,bare.canvas.width,bare.canvas.height).data;
                  for(const item of Armory.catalog.items){
                    clearSlots();
                    const select=document.getElementById(item.slot);
                    if(!select)throw new Error('Missing slot control '+item.slot);
                    select.value=item.id;select.dispatchEvent(new Event('change'));
                    for(const material of item.materials){
                      const control=document.getElementById('material-'+item.slot);
                      if(!control)throw new Error('Missing material control '+item.slot);
                      control.value=material;control.dispatchEvent(new Event('change'));
                      await new Promise(resolve=>requestAnimationFrame(resolve));
                      const result=await Armory.exportAtlas();
                      if(!result.canvas.width||!result.canvas.height)throw new Error('Empty atlas '+item.id+' '+material);
                      const pixels=result.canvas.getContext('2d').getImageData(0,0,result.canvas.width,result.canvas.height).data;
                      let difference=pixels.length!==base.length;
                      for(let i=0;!difference&&i<pixels.length;i++)difference=pixels[i]!==base[i];
                      if(!difference)throw new Error('Equipment made no pixel change: '+item.id+' / '+material);
                      checked.push([item.id,material]);
                    }
                  }
                  return checked;
                }''')
                expected_count = sum(len(item['materials']) for item in catalog['items'])
                assert len(combinations) == expected_count
                assert len({item for item, _material in combinations}) == len(catalog['items'])

                # Body/hybrid options must render as their actual registered status.
                body_results = []
                for body in bodies:
                    await page.select_option('#body', body['id'])
                    await settle(page)
                    frame = await page.evaluate('Armory.frame()')
                    assert frame['bodyId'] == body['id'], frame
                    assert frame['bodyStatus'] == body['status'], frame
                    if body['status'] == 'standing_only':
                        assert frame['bodyFrame'] == 0, frame
                    body_results.append(body['id'])

                await page.select_option('#body', human['id'])
                cells, views = set(), set()
                for cell in range(16):
                    await page.locator('#angle').fill(str(round(cell * 22.5)))
                    await page.locator('#angle').dispatch_event('input')
                    await settle(page)
                    frame = await page.evaluate('Armory.frame()')
                    assert frame['gearCell'] == cell, frame
                    cells.add(frame['gearCell']);views.add(frame['bodyView'])
                assert len(cells) == 16 and len(views) == 4

                await page.locator('#angle').fill('0')
                await page.locator('#angle').dispatch_event('input')
                await page.select_option('#motion', 'walk')
                seen_frames = set()
                for _ in range(25):
                    seen_frames.add((await page.evaluate('Armory.frame()'))['bodyFrame'])
                    await page.wait_for_timeout(55)
                assert len(seen_frames) >= 3, seen_frames
                await page.select_option('#body', standing['id'])
                if await page.locator('#motion option[value="walk"]').is_enabled():
                    await page.select_option('#motion', 'walk')
                await settle(page)
                for _ in range(5):
                    assert (await page.evaluate('Armory.frame()'))['bodyFrame'] == 0
                    await page.wait_for_timeout(90)

                # Fit changes must alter the exported sprite, not only stage handles.
                await page.select_option('#body', human['id'])
                await page.select_option('#motion', 'idle')
                for slot, selection in initial_loadout.items():
                    if slot in SLOTS:
                        await page.select_option('#' + slot, selection['id'])
                        if selection['id']:
                            await page.select_option('#material-' + slot, selection['material'])
                await page.select_option('#weapon', 'weapon.longsword')
                await settle(page)
                before = await export_pixels(page)
                before_fits = await page.evaluate('JSON.stringify(Armory.state.fits)')
                await page.select_option('#fitSlot', 'weapon')
                await page.locator('#fitX').fill('4')
                await page.locator('#fitX').dispatch_event('change')
                await settle(page)
                after = await export_pixels(page)
                assert before['png'] != after['png'], 'Attachment adjustment did not affect exported pixels'
                assert before_fits != await page.evaluate('JSON.stringify(Armory.state.fits)')
                decode_export(after)

                # A parent's fit carries to its hybrids, and a saved preset restores it.
                hybrid = next(body for body in bodies if body['baseId'] == human['id'] and body['variant'] == 'Marked')
                await page.select_option('#body', hybrid['id'])
                await settle(page)
                assert (await page.evaluate('Armory.frame()'))['fit']['weapon']['x'] == 4
                await page.select_option('#body', human['id'])
                await settle(page)
                saved_snapshot = await page.evaluate('Armory.snapshot()')
                async with page.expect_download() as pending:
                    await page.click('#savePreset')
                preset_download = await pending.value
                await preset_download.save_as(temporary / 'preset.json')
                await page.select_option('#body', dwarf['id'])
                await page.locator('#presetFile').set_input_files(str(temporary / 'preset.json'))
                await page.wait_for_function('id=>Armory.state.bodyId===id', arg=human['id'])
                await settle(page)
                assert await page.evaluate('Armory.snapshot()') == saved_snapshot

                async with page.expect_download() as pending:
                    await page.click('#exportSprites')
                downloaded = await pending.value
                await downloaded.save_as(temporary / 'sprites.zip')
                with zipfile.ZipFile(temporary / 'sprites.zip') as archive:
                    assert archive.testzip() is None
                    assert {'sprites.png', 'atlas.json', 'loadout.json'} <= set(archive.namelist())
                    manifest = json.loads(archive.read('atlas.json'))
                    loadout = json.loads(archive.read('loadout.json'))
                    image = Image.open(BytesIO(archive.read('sprites.png'))).convert('RGBA')
                    assert image.getchannel('A').getextrema()[0] == 0
                    assert image.getchannel('A').getbbox()
                    assert manifest and loadout
                    cell_width, cell_height = manifest['frameSize']
                    assert cell_width >= 128 and cell_height >= 128
                    assert image.width % cell_width == 0 and image.height % cell_height == 0
                    assert manifest['clipping']['measured'] and not manifest['clipping']['clipped']
                    assert loadout['fits'] == manifest['fits'] and loadout['bodyId'] == manifest['bodyId']

                await page.select_option('#body', human['id'])
                await page.evaluate('fits=>{Armory.state.fits=JSON.parse(fits)}', before_fits)
                await page.locator('#fitSlot').dispatch_event('change')
                await settle(page)
                await page.screenshot(path=str(HERE / 'armory-preview.png'), full_page=True)
                await page.select_option('#body', dwarf['id'])
                await settle(page)
                await page.screenshot(path=str(HERE / 'dwarf-equipped.png'), full_page=True)
                assert not errors, errors
                assert not blocked, blocked
                summary = dict(designs_checked=len(catalog['items']), material_recipes_checked=len(combinations),
                               body_options_checked=len(body_results), gear_angles_checked=sorted(cells),
                               cardinal_views_checked=sorted(views), walk_frames_seen=sorted(seen_frames),
                               standing_hybrids_do_not_fake_walk=True, fitted_export_changes_pixels=True,
                               base_fit_inherited_by_hybrid=True, preset_round_trip=True,
                               goa_held_direction_adaptation=goa_adaptation,
                               png_zip_export=True, export_frame_size=manifest['frameSize'], initial_atlas_size=list(initial_image.size),
                               source_boundary_review_notes=source_warnings,
                               browser_errors=errors, external_requests=blocked)
                (HERE / 'verification.json').write_text(json.dumps(summary, indent=2))
                print(json.dumps({key: value for key, value in summary.items() if key != 'source_boundary_review_notes'}))
                print('Source boundary review notes:', len(source_warnings))
            finally:
                await browser.close()


async def detail_portraits():
    """Capture the ears/horns/tails fitting cases for visual calibration."""
    bodies = json.loads((HERE / 'bodies.json').read_text())['bodies']
    cases = [
        ('elf-front', next(b for b in bodies if b['raceKey'] == 'Elf' and b['variant'] == 'Base'), 0),
        ('elf-side', next(b for b in bodies if b['raceKey'] == 'Elf' and b['variant'] == 'Base'), 90),
        ('dark-elf-side', next(b for b in bodies if b['raceKey'] == 'Night Elf' and b['variant'] == 'Base'), 90),
        ('dark-elf-hellblooded-side', next(b for b in bodies if b['raceKey'] == 'Night Elf' and b['variant'] == 'Hellblooded'), 90),
        ('goblin-front', next(b for b in bodies if b['raceKey'] == 'Goblins' and b['variant'] == 'Base'), 0),
    ]
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless=True)
        try:
            page = await browser.new_page(viewport=dict(width=1600, height=1150))
            await page.goto((HERE / 'index.html').as_uri())
            await page.wait_for_function('window.Armory?.ready===true && Armory.frame()!=null')
            for name, body, angle in cases:
                await page.select_option('#body', body['id'])
                await page.locator('#angle').fill(str(angle))
                await page.locator('#angle').dispatch_event('input')
                await settle(page)
                await page.locator('#stage').screenshot(path=str(HERE / (name + '.png')))
                frame = await page.evaluate('Armory.frame()')
                print(json.dumps(dict(case=name, headWidth=frame['rig']['headWidth'], head=frame['rig']['head'], body=body['id'])))
            await page.select_option('#body', 'human')
            await page.select_option('#motion', 'walk')
            observed = {}
            for _ in range(25):
                frame = await page.evaluate('Armory.frame()')
                observed[frame['bodyFrame']] = dict(weapon=frame['rig']['weapon'], shield=frame['rig']['shield'])
                await page.wait_for_timeout(55)
            assert len(observed) == 3, observed
            print(json.dumps(dict(walk_registration=observed)))
            await page.select_option('#motion', 'idle')
            await page.select_option('#weapon', 'weapon.spear')
            await page.select_option('#fitSlot', 'weapon')
            for control, value in [('fitY', '64'), ('fitScale', '2'), ('fitRotation', '180')]:
                await page.locator('#' + control).fill(value)
                await page.locator('#' + control).dispatch_event('input')
            await settle(page)
            stress = await page.evaluate('''()=>{
              const out=Armory.exportAtlas(),[w,h]=out.manifest.frameSize,c=out.canvas.getContext('2d');let edgePixels=0;
              for(let row=0;row<out.canvas.height/h;row++)for(let col=0;col<out.canvas.width/w;col++){
                const p=c.getImageData(col*w,row*h,w,h).data;
                for(let x=0;x<w;x++)edgePixels+=p[x*4+3]>110||p[((h-1)*w+x)*4+3]>110;
                for(let y=0;y<h;y++)edgePixels+=p[(y*w)*4+3]>110||p[(y*w+w-1)*4+3]>110;
              }
              return {frameSize:[w,h],edgePixels,clipping:out.manifest.clipping};
            }''')
            print(json.dumps(dict(long_weapon_fit_stress=stress)))
            assert stress['edgePixels'] == 0, 'A supported long-weapon fitting clips at exported frame edges'
            for control, value in [('fitX', '64'), ('fitWidth', '1.8'), ('fitRotation', '0')]:
                await page.locator('#' + control).fill(value)
                await page.locator('#' + control).dispatch_event('input')
            await page.select_option('#motion', 'gear-poses')
            await page.wait_for_function('Armory.frame().pose===3')
            horizontal = await page.evaluate('''()=>{
              const out=Armory.exportAtlas(),[w,h]=out.manifest.frameSize,c=out.canvas.getContext('2d');let edgePixels=0;
              for(let col=0;col<4;col++){const p=c.getImageData(col*w,0,w,h).data;
                for(let x=0;x<w;x++)edgePixels+=p[x*4+3]>110||p[((h-1)*w+x)*4+3]>110;
                for(let y=0;y<h;y++)edgePixels+=p[(y*w)*4+3]>110||p[(y*w+w-1)*4+3]>110;}
              return {frameSize:[w,h],edgePixels,pose:out.manifest.weaponPose,clipping:out.manifest.clipping};
            }''')
            print(json.dumps(dict(horizontal_spear_stress=horizontal)))
            assert horizontal['edgePixels'] == 0, 'Horizontal long-weapon fitting clips at exported frame edges'
        finally:
            await browser.close()


if __name__ == '__main__':
    asyncio.run(detail_portraits() if '--portraits' in sys.argv else main())
