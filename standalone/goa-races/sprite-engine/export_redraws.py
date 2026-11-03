"""Pack the generated redraw grids through the converter's real export library."""
import asyncio
import base64
import json
from pathlib import Path
import zipfile
from playwright.async_api import async_playwright

HERE = Path(__file__).resolve().parent


async def main():
    jobs = json.loads((HERE / 'remaining-races-jobs.json').read_text())
    report = []
    output = HERE / 'converted'
    output.mkdir(exist_ok=True)
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless=True)
        try:
            page = await browser.new_page(viewport=dict(width=1560, height=1150))
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            for job in jobs:
                await page.goto(job['url'])
                await page.wait_for_function('window.workshopReady && workshop.packed!=null')
                data = await page.evaluate('({png:workshop.packed.toDataURL(),atlas:SpriteEngine.manifest(workshop.spec),size:[workshop.packed.width,workshop.packed.height]})')
                folder = output / job['race']
                folder.mkdir(exist_ok=True)
                (folder / 'sprites.png').write_bytes(base64.b64decode(data['png'].split(',',1)[1]))
                (folder / 'atlas.json').write_text(json.dumps(data['atlas'],indent=2))
                report.append(dict(race=job['race'],frames=len(data['atlas']['frames']),size=data['size'],url=job['url']))
                print('Packed '+job['race'],flush=True)
            await page.goto(jobs[3]['url'])
            await page.wait_for_function('window.workshopReady && workshop.packed!=null')
            await page.screenshot(path=str(HERE / 'converted-preview.png'),full_page=True)
            assert not errors, errors
        finally:
            await browser.close()
    (output/'README.md').write_text('# GOA redraw drafts\n\nGenerated with the built-in image generation tool against the approved GOA race reference. Each race has a transparent 64-pixel-cell PNG atlas and frame metadata. Full-resolution results and prompts remain in the saved jobs and redraw-provenance.json.\n\nThese are generated animation drafts. Review frame-to-frame scale, gait, feet, and overlay registration before game integration. Grid and file checks do not establish animation quality. The approved first Vampire look was retained with its unintended ground wings removed.\n')
    (HERE/'redraw-verification.json').write_text(json.dumps(dict(races=report,total_frames=sum(r['frames'] for r in report),browser_errors=errors),indent=2))
    archive=HERE.parents[2]/'Dungeon Master Sample/GOA Remaining Races Redrawn.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as bundle:
        for path in output.rglob('*'):
            if path.is_file(): bundle.write(path,path.relative_to(output))
    print(str(archive))


if __name__=='__main__':
    asyncio.run(main())
