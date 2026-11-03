"""Import the remaining original Dungeon Master races through the converter UI."""
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parents[2] / 'standalone/remastered/game/Icons/Remastered/Races64'
RACES = ['HumanBlack', 'Vampire', 'VampireFly', 'Demon', 'DemonFly',
         'Gargoyle', 'GargoyleFly', 'FrogMan', 'LizardMan', 'DevourerZombie', 'Skeleton']
URL = 'http://127.0.0.1:8876/'


async def main():
    saved = []
    previous = json.loads((HERE / 'remaining-races-jobs.json').read_text()) if (HERE / 'remaining-races-jobs.json').exists() else []
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless=True)
        try:
            page = await browser.new_page(viewport=dict(width=1560, height=1100))
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            await page.route('**/*', lambda route: route.continue_() if route.request.url.startswith((URL, 'data:')) else route.abort())
            await page.goto(URL)
            await page.wait_for_function('window.workshopReady')
            for race in RACES:
                existing = next((j for j in previous if j['race'] == race and j['cells'] >= 4), None)
                if existing:
                    saved.append(existing)
                    continue
                source = SOURCE / (race + '.dmi')
                if not source.is_file():
                    raise FileNotFoundError(source)
                await page.locator('#inputFile').set_input_files(str(source))
                await page.wait_for_function('race => workshop.spec?.source.filename === race+".dmi" && workshop.job===null', arg=race)
                walking = await page.locator('#state option').evaluate_all('(options)=>options.find(o=>o.textContent.startsWith("Walk ·"))?.value')
                if walking is not None:
                    await page.select_option('#state', walking)
                await page.locator('#name').fill(race + ' · original for redraw')
                await page.locator('#name').dispatch_event('change')
                await page.locator('#notes').fill('Preserve this race’s own anatomy, distinctive features and colors. Adapt its art style to the approved GOA reference. Keep every supplied pose and direction; preserve wings for flying forms.')
                await page.locator('#notes').dispatch_event('change')
                await page.click('#prepare')
                await page.wait_for_function('workshop.job!=null')
                job = await page.evaluate('workshop.job')
                saved.append(dict(race=race, id=job['id'], path=job['path'],
                                  source=str(source), cells=len(job['spec']['source']['cells']),
                                  url=URL+'?job='+job['id']))
                print(f"Loaded {race}: {saved[-1]['cells']} original cells", flush=True)
            await page.goto(saved[3]['url'])
            await page.wait_for_function('window.workshopReady && workshop.job!=null')
            assert await page.locator('#name').input_value() == 'Demon · original for redraw'
            assert await page.locator('#jobHistory option').count() >= 12
            assert not errors, errors
            await page.screenshot(path=str(HERE / 'remaining-races-loaded.png'), full_page=True)
            (HERE / 'remaining-races-jobs.json').write_text(json.dumps(saved, indent=2))
            print(json.dumps(dict(jobs=len(saved), open=saved[3]['url'], browser_errors=errors)))
        finally:
            await browser.close()


if __name__ == '__main__':
    asyncio.run(main())
