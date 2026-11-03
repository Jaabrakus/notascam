"""Export real equipped PNG/metadata examples for every registered body."""
import asyncio
import base64
import json
from pathlib import Path
import zipfile

from playwright.async_api import async_playwright

HERE = Path(__file__).resolve().parent
SAMPLE = HERE.parents[2] / 'Dungeon Master Sample'


async def main():
    output = HERE / 'equipped-samples'
    output.mkdir(exist_ok=True)
    report = []
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless=True)
        try:
            page = await browser.new_page(viewport=dict(width=1560, height=1150))
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            await page.goto((HERE / 'index.html').as_uri())
            await page.wait_for_function('window.Armory?.ready && Armory.frame()!=null')
            bodies = await page.evaluate('Armory.bodies.map(b=>({id:b.id,status:b.status,label:b.label}))')
            for body in bodies:
                await page.select_option('#body', body['id'])
                await page.select_option('#motion', 'idle' if body['status']=='standing_only' else 'walk')
                value = await page.evaluate('''()=>{
                  const out=Armory.exportAtlas();
                  return {png:out.canvas.toDataURL(),bare:out.bare.toDataURL(),manifest:out.manifest,preset:Armory.snapshot()};
                }''')
                folder = output / body['id']
                folder.mkdir(exist_ok=True)
                for key, filename in [('png','sprites.png'),('bare','body64.png')]:
                    (folder / filename).write_bytes(base64.b64decode(value[key].split(',',1)[1]))
                (folder/'atlas.json').write_text(json.dumps(value['manifest'],indent=2))
                (folder/'loadout.json').write_text(json.dumps(value['preset'],indent=2))
                report.append(dict(body=body['id'],frames=len(value['manifest']['frames']),status=body['status']))
            # A compact visual sample of the shared soldier loadout on varied bodies.
            preview = await page.evaluate('''()=>{
              const ids=['human','dwarf','elf','dark-elf','orc','goblin','kobold','vampire','human-hellblooded','dark-elf-ashen','orc-marked','kobold-werewolf'];
              const canvas=document.createElement('canvas');canvas.width=1024;canvas.height=768;
              const c=canvas.getContext('2d');c.fillStyle='#142125';c.fillRect(0,0,1024,768);
              for(let i=0;i<ids.length;i++){
                const b=Armory.bodies.find(b=>b.id===ids[i]);if(!b)continue;
                const x=i%4*256,y=Math.floor(i/4)*256;
                c.save();c.translate(x+128-32*3,y+216-61*3);c.scale(3,3);
                Armory.render(c,{bodyId:b.id,angle:0,frame:0});c.restore();
                c.fillStyle='#ddcca7';c.font='13px system-ui';c.textAlign='center';c.fillText(b.label,x+128,y+244);
              }return canvas.toDataURL();
            }''')
            (HERE/'equipped-races-preview.png').write_bytes(base64.b64decode(preview.split(',',1)[1]))
            (SAMPLE/'GOA Equipped Races Preview.png').write_bytes(base64.b64decode(preview.split(',',1)[1]))
            assert not errors, errors
        finally:
            await browser.close()
    (output/'README.md').write_text('# Shared soldier loadout samples\n\nEach registered race/variant has equipped sprite PNGs, bare 64px body PNGs, an atlas manifest, and a reusable loadout/fit preset. Walking/flying bodies include their available frames; standing hybrids include only their actual standing views. These are visual fit drafts, not completed injury or hybrid animation sets. Use the armory to change weapons, materials and race-specific fits.\n')
    archive=SAMPLE/'GOA Universal Equipped Sprites.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as bundle:
        for path in output.rglob('*'):
            if path.is_file():bundle.write(path,path.relative_to(output))
    (HERE/'equipped-samples.json').write_text(json.dumps(dict(bodies=report,totalFrames=sum(r['frames'] for r in report)),indent=2))
    print(json.dumps(dict(bodies=len(report),frames=sum(r['frames'] for r in report),archive=str(archive))))


if __name__=='__main__':
    asyncio.run(main())
