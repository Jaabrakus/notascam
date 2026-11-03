"""Check local limb preview/export with transparent fixtures and available real art.

No AI calls. Uses installed Playwright, Pillow and local Google Chrome.
"""
import asyncio
import base64
from io import BytesIO
import json
from pathlib import Path
import tempfile
import sys

from PIL import Image, ImageDraw
from playwright.async_api import async_playwright

import build

HERE = Path(__file__).resolve().parent


def fixture(directory):
    # Odd source dimensions exercise fractional source-cell boundaries.
    image = Image.new('RGBA', (101, 53))
    draw = ImageDraw.Draw(image)
    colors = []
    for row in range(2):
        for col in range(4):
            color = (30 + col * 45, 40 + row * 100, 180 - col * 25, [255, 192, 128, 64][col])
            colors.append(color)
            x0, y0 = int(col * 101 / 4) + 3, int(row * 53 / 2) + 3
            x1, y1 = int((col + 1) * 101 / 4) - 4, int((row + 1) * 53 / 2) - 4
            draw.rectangle((x0, y0, x1, y1), fill=color)
    image.save(directory / 'fixture.png')
    assets = [dict(id='human-detached', race='Human', category='detached', label='Arm and leg fixture', path='fixture.png', columns=4, rows=2, rowLabels=['LeftArm', 'RightArm'], directionOrder=['South', 'North', 'East', 'West'], status='draft'),
              dict(id='elf-injury', race='Elf', category='injury', label='Missing limb fixture', path='fixture.png', columns=4, rows=2, rowLabels=['NoLeftArm', 'NoRightArm'], directionOrder=['South', 'North', 'East', 'West'], status='draft')]
    for asset in assets:
        asset['sourceRects'] = [[[col * 101 / 4, row * 53 / 2, 101 / 4, 53 / 2] for col in range(4)] for row in range(2)]
    uneven = Image.new('RGBA', (104, 130))
    draw = ImageDraw.Draw(uneven)
    for row, (top, bottom) in enumerate([(5, 22), (40, 66), (95, 120)]):
        for col in range(4):
            draw.rectangle((col * 26 + 5, top, col * 26 + 20, bottom), fill=[(220, 30, 50, 255), (30, 220, 50, 255), (30, 50, 220, 255)][row])
    uneven.save(directory / 'uneven.png')
    assets.append(dict(id='measured-injury', race='Measured', category='injury', label='Unequal spacing / ignored row', path='uneven.png', columns=4, rows=2, sourceGridRows=3, selectedRows=[0, 2], rowLabels=['KeepFirst', 'KeepThird'], directionOrder=['South', 'North', 'East', 'West'], status='draft'))
    manifest = directory / 'manifest.json'
    manifest.write_text(json.dumps(assets))
    page = directory / 'fixture.html'
    page.write_text(build.render(manifest))
    empty = directory / 'empty.html'
    empty.write_text(build.render(directory / 'missing-manifest.json'))
    return page, empty, colors


async def main():
    with tempfile.TemporaryDirectory(prefix='goa-limb-check-') as temporary:
        directory = Path(temporary)
        fixture_page, empty_page, colors = fixture(directory)
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless=True)
            try:
                page = await browser.new_page(viewport=dict(width=1380, height=1000), device_scale_factor=1)
                page.set_default_timeout(10000)
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                await page.route('**/*', lambda route: route.continue_() if route.request.url.startswith(('file:', 'data:')) else route.abort())
                await page.goto(empty_page.as_uri())
                await page.wait_for_function('window.limbGalleryReady')
                assert await page.locator('#empty').is_visible()
                assert await page.locator('#exportPng').is_disabled()
                await page.goto(fixture_page.as_uri())
                await page.wait_for_function('window.limbGalleryReady && window.limbGallerySelection!=null')
                dimensions = await page.evaluate('({native:[document.querySelector("#native").getBoundingClientRect().width,document.querySelector("#native").getBoundingClientRect().height],large:[document.querySelector("#large").getBoundingClientRect().width,document.querySelector("#large").getBoundingClientRect().height]})')
                assert dimensions == dict(native=[256, 64], large=[1024, 256]), dimensions
                pixels = await page.evaluate('''async()=>{const atlas=await limbGallery.atlas(limbGallery.selected),context=atlas.getContext('2d');return Array.from({length:8},(_,i)=>Array.from(context.getImageData((i%4)*64+32,Math.floor(i/4)*64+32,1,1).data));}''')
                for actual, expected in zip(pixels, colors):
                    assert all(abs(a - b) <= 3 for a, b in zip(actual, expected)), (actual, expected)
                raw = await page.evaluate('ASSETS[0].src')
                assert base64.b64decode(raw.split(',', 1)[1]) == (directory / 'fixture.png').read_bytes()
                await page.locator('#native').click(position=dict(x=32, y=32))
                assert (await page.evaluate('window.limbGalleryPixel'))['direction'] == 'South'
                await page.select_option('#row', '1')
                await page.wait_for_function('limbGallerySelection.label==="RightArm"')
                assert 'Animation states pending' in await page.locator('#status').text_content()
                async with page.expect_download() as pending:
                    await page.click('#exportPng')
                downloaded = await pending.value
                await downloaded.save_as(directory / 'export.png')
                with Image.open(directory / 'export.png') as image:
                    assert image.size == (256, 128) and image.mode == 'RGBA'
                    assert image.getchannel('A').getextrema() == (0, 255)
                async with page.expect_download() as pending:
                    await page.click('#exportJson')
                downloaded = await pending.value
                await downloaded.save_as(directory / 'export.json')
                metadata = json.loads((directory / 'export.json').read_text())
                assert metadata['animation'] is False and len(metadata['frames']) == 8
                assert metadata['frames'][4] == dict(state='RightArm', direction='South', rect=[0, 64, 64, 64])
                await page.select_option('#race', 'Elf')
                await page.wait_for_function('limbGallerySelection.id==="elf-injury"')
                assert await page.locator('#row').input_value() == '0'
                assert 'NoLeftArm' in await page.locator('#status').text_content()
                await page.select_option('#race', 'Measured')
                await page.wait_for_function('limbGallerySelection.id==="measured-injury"')
                measured = await page.evaluate('''async()=>{const asset=limbGallery.selected,atlas=await limbGallery.atlas(asset),c=atlas.getContext('2d');return {meta:limbGallery.metadata(),pixels:[Array.from(c.getImageData(32,32,1,1).data),Array.from(c.getImageData(32,96,1,1).data)]};}''')
                assert measured['pixels'] == [[220, 30, 50, 255], [30, 50, 220, 255]], measured
                assert measured['meta']['selectedRows'] == [0, 2]
                assert measured['meta']['sourceGridRows'] == 3
                assert measured['meta']['segmentation']['equalCellsAssumed'] is False
                assert measured['meta']['sourceRects'][0][0][3] != measured['meta']['sourceRects'][1][0][3]
                assert not await page.evaluate('window.limbGalleryErrors')
                actual_count = 0
                manifest = HERE / 'manifest.json'
                if manifest.exists():
                    real = directory / 'actual.html'
                    real.write_text(build.render(manifest))
                    await page.goto(real.as_uri())
                    await page.wait_for_function('window.limbGalleryReady')
                    assets = await page.evaluate('ASSETS.map(({id,race,rows,columns})=>({id,race,rows,columns}))')
                    for asset in assets:
                        await page.select_option('#race', asset['race'])
                        await page.select_option('#asset', asset['id'])
                        await page.wait_for_function('id=>limbGallerySelection.id===id', arg=asset['id'])
                        value = await page.evaluate('''async()=>{const a=await limbGallery.atlas(limbGallery.selected);return {width:a.width,height:a.height,frames:limbGallery.metadata().frames.length,alpha:a.getContext('2d').getImageData(0,0,a.width,a.height).data.filter((_,i)=>i%4===3).some(v=>v<255)};}''')
                        assert value['width'] == asset['columns'] * 64 and value['height'] == asset['rows'] * 64
                        assert value['frames'] == asset['columns'] * asset['rows']
                        assert value['alpha'], asset['id']
                        actual_count += 1
                    await page.screenshot(path=str(HERE / 'limb-gallery-preview.png'), full_page=True)
                    assert not await page.evaluate('window.limbGalleryErrors')
                assert not errors, errors
                result = dict(fractional_cell_packing=True, explicit_source_rects=True, unequal_source_spacing=True, ignored_source_rows=True, common_asset_scale=True, direction_order=True, alpha_preserved=True, source_bytes_unchanged=True, native_preview_size=dimensions['native'], enlarged_preview_size=dimensions['large'], png_export=True, metadata_export=True, pixel_inspection=True, static_rows_not_animated=True, race_selection=True, empty_manifest=True, real_assets_checked=actual_count, browser_errors=errors, ai_calls=0)
                (HERE / 'verification.json').write_text(json.dumps(result, indent=2))
                print(json.dumps(result))
            finally:
                await browser.close()


async def real_only():
    """Minimal recheck after a source-pixel mask calibration change."""
    manifest=json.loads((HERE/'manifest.json').read_text())
    with tempfile.TemporaryDirectory(prefix='limb-real-check-') as temporary:
        async with async_playwright() as playwright:
            browser=await playwright.chromium.launch(executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless=True)
            try:
                page=await browser.new_page(viewport=dict(width=1380,height=1000),device_scale_factor=1)
                errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
                await page.route('**/*',lambda route:route.continue_() if route.request.url.startswith(('file:','data:')) else route.abort())
                await page.goto((HERE/'index.html').as_uri())
                await page.wait_for_function('window.limbGalleryReady')
                for asset in manifest:
                    await page.select_option('#race',asset['race'])
                    await page.select_option('#asset',asset['id'])
                    await page.wait_for_function('id=>limbGallerySelection.id===id',arg=asset['id'])
                    value=await page.evaluate('({frames:limbGallery.metadata().frames.length,animation:limbGallery.metadata().animation})')
                    assert value==dict(frames=asset['rows']*4,animation=False)
                    async with page.expect_download() as pending:await page.click('#exportPng')
                    result=await pending.value;destination=Path(temporary)/(asset['id']+'.png')
                    await result.save_as(destination)
                    assert destination.read_bytes()==Path(asset['path']).read_bytes(), 'Already64px source atlas bytes changed during browser export'
                injury=next((asset for asset in manifest if asset['id'].endswith('-injury-blood')),None) or next((asset for asset in manifest if asset['category']=='injury'),None)
                if injury:
                    await page.select_option('#asset',injury['id'])
                    await page.wait_for_function('id=>limbGallerySelection.id===id',arg=injury['id'])
                    index=injury['rowLabels'].index('NoArms:frame0')
                    await page.select_option('#row',str(index))
                    await page.wait_for_function('limbGallerySelection.label==="NoArms:frame0"')
                await page.screenshot(path=str(HERE/'limb-gallery-preview.png'),full_page=True)
                assert not errors and not await page.evaluate('window.limbGalleryErrors')
                value=dict(real_assets_checked=len(manifest),source_png_downloads_byte_exact=True,browser_errors=errors,ai_calls=0)
                (HERE/'real-verification.json').write_text(json.dumps(value,indent=2));print(json.dumps(value))
            finally:await browser.close()


if __name__ == '__main__':
    asyncio.run(real_only() if '--real-only' in sys.argv else main())
