"""Exercise the isolated local preview with a temporary headless browser profile."""
import asyncio
import json
from pathlib import Path

from playwright.async_api import async_playwright

HERE = Path(__file__).resolve().parent


async def main():
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless=True)
        try:
            page = await browser.new_page(viewport=dict(width=1380, height=1150), device_scale_factor=1)
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            await page.route('**/*', lambda route: route.continue_() if route.request.url.startswith(('file:', 'data:')) else route.abort())
            await page.goto((HERE / 'index.html').as_uri())
            await page.wait_for_function('window.previewReady===true && window.previewFrame!=null')
            await page.screenshot(path=str(HERE / 'fitting-preview.png'), full_page=True)
            await page.select_option('#race', 'base_m1.dmi')
            await page.select_option('#armor', 'goa')
            await page.screenshot(path=str(HERE / 'original-goa-fitting.png'), full_page=True)
            cells = []
            for index in range(16):
                await page.locator('#angle').fill(str(round(index * 22.5)))
                await page.wait_for_function('index => window.previewFrame.gearCell===index', arg=index)
                cells.append(await page.evaluate('window.previewFrame.gearCell'))
            assert len(set(cells)) == 16
            piece_count = 0
            for control in ['weapon', 'shield', 'helmet']:
                for value in await page.locator('#' + control + ' option').evaluate_all('(options)=>options.map(o=>o.value)'):
                    await page.select_option('#' + control, value)
                    await page.evaluate('new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))')
                    piece_count += bool(value) and not value.startswith('goa.')
            assert piece_count == 43
            for value in ['0', '1', '2', '3', '4', '5', 'base_m1.dmi', 'base_m2.dmi', 'base_m3.dmi']:
                await page.select_option('#race', value)
                await page.evaluate('new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))')
            await page.select_option('#weapon', 'weapon.longsword')
            await page.select_option('#shield', 'shield.round')
            await page.select_option('#helmet', 'helmet.nasal')
            await page.select_option('#race', '0')
            await page.select_option('#armor', 'none')
            await page.locator('#angle').fill('0')
            await page.locator('#attack').check()
            poses = set()
            for _ in range(50):
                poses.add((await page.evaluate('window.previewFrame'))['pose'])
                await page.wait_for_timeout(30)
            assert poses == {0, 1, 2, 3}, poses
            await page.locator('#attack').uncheck()
            await page.wait_for_timeout(50)
            await page.goto((HERE / 'goa-held-sword.html').as_uri())
            await page.wait_for_function('window.previewReady===true && window.previewFrame?.goaSword===true')
            assert await page.locator('#race').input_value() == 'base_m1.dmi'
            assert await page.locator('#shield').input_value() == ''
            assert await page.locator('#helmet').input_value() == ''
            assert await page.locator('#gearBadge').text_content() == 'GOA sword: 4 directions'
            await page.locator('#stage').screenshot(path=str(HERE / 'goa-held-sword.png'))
            await page.locator('#walk').check()
            first = await page.locator('#stage').evaluate('(c)=>c.toDataURL()')
            await page.wait_for_timeout(250)
            second = await page.locator('#stage').evaluate('(c)=>c.toDataURL()')
            assert first != second, 'GOA walking body/sword frames did not advance'
            await page.locator('#attack').check()
            await page.wait_for_function("window.previewFrame.bodyState==='w-attack'")
            await page.locator('#stage').screenshot(path=str(HERE / 'goa-sword-attack.png'))
            assert not errors, errors
            assert not await page.evaluate('window.previewErrors')
            result = dict(gear_angles=cells, gear_pieces_checked=piece_count, body_options_checked=9,
                          attack_poses_checked=sorted(poses), goa_held_sword=True, goa_body_walking=True,
                          goa_body_attack=True, browser_errors=errors)
            (HERE / 'verification.json').write_text(json.dumps(result, indent=2))
            print(json.dumps(result))
        finally:
            await browser.close()


if __name__ == '__main__':
    asyncio.run(main())
