"""Verify original templates, exact head pixels, shared silhouettes and UI exports."""
import asyncio,hashlib,json,sys
from pathlib import Path
from PIL import Image
from playwright.async_api import async_playwright
from exact_templates import SOURCES
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
DEST=ROOT/'Dungeon Master Sample/Shared Body Rigs'


async def main():
    data=json.loads((DEST/'manifest.json').read_text())
    templates={t['id']:t for t in data['templates']}
    assert len(templates)==6 and len(data['actors'])==174
    for key,guide,filename in SOURCES:
        template=templates[key];reference=HERE/'references'/filename
        assert hashlib.sha256(reference.read_bytes()).hexdigest()==template['artworkSha256']
        assert (DEST/template['sourceArtwork']).read_bytes()==reference.read_bytes()
        expected=Image.open(reference).convert('RGBA').resize((256,192),Image.Resampling.NEAREST)
        assert expected.tobytes()==Image.open(DEST/template['sourceAtlas']).tobytes()
        core=Image.open(DEST/template['core']);assert core.size==(256,192)
        assert hashlib.sha256(core.getchannel('A').tobytes()).hexdigest()==template['coreAlphaSha256']
    head_count=0
    baseline=HERE/'polish-v2'
    old_heads=json.loads((baseline/'original-head-hashes.json').read_text())
    old_cores=json.loads((baseline/'body-core-hashes.json').read_text())
    for t in data['templates']:assert hashlib.sha256((DEST/t['core']).read_bytes()).hexdigest()==old_cores[t['id']]
    for actor in data['actors']:
        folder=DEST/'Characters'/actor['id'];body=Image.open(DEST/actor['body'])
        master=Image.open(DEST/templates[actor['template']]['core'])
        assert body.getchannel('A').tobytes()==master.getchannel('A').tobytes()
        original=Image.open(folder/'Unmodified_Head_Pixels_64px.png')
        assert hashlib.sha256((folder/'Unmodified_Head_Pixels_64px.png').read_bytes()).hexdigest()==old_heads[actor['id']]
        markings=Image.open(DEST/actor['markings'])
        skin=Image.open(DEST/templates[actor['template']]['skinMask'])
        assert markings.size==body.size
        for mark,allowed in zip(markings.getchannel('A').getdata(),skin.getchannel('A').getdata()):assert not mark or allowed>=128
        heads=Image.open(DEST/actor['head']);features=Image.open(DEST/actor['features'])
        composed=Image.open(DEST/actor['composite'])
        assert heads.size==composed.size==(512,384)
        assert hashlib.sha256((DEST/actor['donor']).read_bytes()).hexdigest()==actor['donorSha256']
        for f in range(3):
            for v in range(4):
                placed=actor['placements'][f][v];ff=placed['sourceFrame'];dx,dy=placed['offset']
                tile=heads.crop((v*128,f*128,v*128+128,f*128+128))
                raw=original.crop((v*64,ff*64,v*64+64,ff*64+64))
                assert tile.crop((32+dx,32+dy,96+dx,96+dy)).tobytes()==raw.tobytes(),(actor['id'],f,v)
                assert tile.getchannel('A').getbbox()
                expected=features.crop((v*128,f*128,v*128+128,f*128+128))
                expected.alpha_composite(body.crop((v*64,f*64,v*64+64,f*64+64)),(32,32));expected.alpha_composite(markings.crop((v*64,f*64,v*64+64,f*64+64)),(32,32));expected.alpha_composite(tile)
                assert expected.tobytes()==composed.crop((v*128,f*128,v*128+128,f*128+128)).tobytes()
                head_count+=1
    orc=next(a for a in data['actors'] if a['id']=='orc');dwarf=next(a for a in data['actors'] if a['id']=='dwarf')
    assert orc['template']==dwarf['template']=='stocky-male' and dwarf['displayScale']<orc['displayScale']
    assert data['summary']['hybridAppearances']==146
    for key in ['human-marked','human-ashen','orc-female-marked','lizardman-female-ashen']:
        assert next(a for a in data['actors'] if a['id']==key)['hybridDetails']['markPixels']>0
    assert len(data['hybridSheets'])==11
    for s in data['hybridSheets']:assert (DEST/s['file']).exists()
    if '--files-only' in sys.argv:
        result=dict(status='passed',scope='File and exact-pixel checks only; browser controls not checked in this run.',originalTemplates=6,bodyAssignments=174,femaleVariants=80,hybridAppearances=146,hybridFamilySheets=11,exactHeadPlacements=head_count,allBodySilhouettesMatchTheirMaster=True,originalUserArtworkPreserved=True,headsAndBodyCoresUnchangedSincePolish=True,identityMarksClippedToSkin=True,orcDwarfShareStocky=True)
        (DEST/'file-verification.json').write_text(json.dumps(result,indent=2));print(json.dumps(result));return
    errors=[]
    async with async_playwright() as pw:
        browser=await pw.chromium.launch(executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless=True)
        try:
            page=await browser.new_page(viewport=dict(width=1440,height=1100));page.on('pageerror',lambda e:errors.append(str(e)))
            await page.goto((ROOT/'Dungeon Master Sample/Layered Deepguard Fitting/index.html').as_uri())
            await page.wait_for_function('document.body.dataset.ready==="true"')
            assert page.url==(DEST/'index.html').as_uri()
            assert await page.evaluate('sharedRigs.data.templates.length')==6
            assert await page.locator('#character').input_value()=='elf'
            await page.select_option('#forms','all')
            assert await page.locator('#character option').count()==174
            await page.select_option('#sex','female')
            assert await page.locator('#character option').count()==80
            await page.select_option('#sex','all')
            await page.click('#showHybrids')
            assert await page.locator('#character option').count()==146
            await page.select_option('#forms','all')
            # Decode and render every supplied body/head combination in-browser.
            checked=await page.evaluate('''async()=>{
                let n=0;
                for(const actor of sharedRigs.data.actors){
                    await sharedRigs.select(actor.id);
                    const canvases=[...document.querySelectorAll('#views canvas')];
                    if(canvases.length!==4)throw Error('Missing directions');
                    for(const c of canvases){
                        const p=c.getContext('2d').getImageData(0,0,128,128).data;
                        if(!p.some((x,i)=>i%4===3&&x>0))throw Error('Empty character '+actor.id);
                    }
                    n++;
                }
                return n;
            }''')
            assert checked==174
            await page.evaluate('sharedRigs.select("human-ashen")')
            await page.select_option('#mode','markings')
            assert await page.evaluate('Array.from(document.querySelector("#views canvas").getContext("2d").getImageData(0,0,128,128).data).some((x,i)=>i%4===3&&x>0)')
            await page.evaluate('sharedRigs.select("elf")')
            await page.select_option('#mode','neutral')
            neutral=await page.evaluate('document.querySelector("#views canvas").toDataURL()')
            await page.select_option('#mode','composed')
            assert await page.evaluate('document.querySelector("#views canvas").toDataURL()')!=neutral
            await page.click('#play')
            await page.wait_for_function('document.getElementById("frame").value!=="0"')
            await page.click('#play')
            await page.evaluate('document.getElementById("frame").value="0"');await page.locator('#frame').dispatch_event('input')
            await page.locator('section details summary').first.click()
            await page.select_option('#facing','0');await page.select_option('#mode','head')
            before=await page.evaluate('document.querySelector("#views canvas").toDataURL()')
            await page.fill('#dx','2')
            assert await page.evaluate('document.querySelector("#views canvas").toDataURL()')!=before
            async with page.expect_download() as export:await page.click('#exportAtlas')
            download=await export.value;exported=HERE/'verified-character-atlas.png';await download.save_as(exported)
            assert Image.open(exported).size==(512,384)
            async with page.expect_download() as export:await page.click('#exportCore')
            download=await export.value;exported_core=HERE/'verified-original-body-core.png';await download.save_as(exported_core)
            assert exported_core.read_bytes()==(DEST/templates['standard-male']['core']).read_bytes()
            async with page.expect_download() as export:await page.click('#exportRecipe')
            download=await export.value;recipe=HERE/'verified-head-attachments.json';await download.save_as(recipe)
            assert json.loads(recipe.read_text())['offsets']['elf']['0']['x']==2
            await page.click('#reset');await page.set_input_files('#importRecipe',str(recipe))
            await page.wait_for_function('document.getElementById("message").textContent==="Head attachment recipe loaded."')
            assert await page.locator('#dx').input_value()=='2'
            await page.click('#reset');await page.select_option('#mode','composed')
            await page.locator('section details summary').first.click()
            await page.select_option('#forms','base')
            await page.wait_for_function('document.body.dataset.ready==="true" && document.getElementById("name").textContent.includes("Elf")')
            await page.screenshot(path=str(DEST/'Viewer_Preview.png'),full_page=True)
            assert not errors,errors
        finally:await browser.close()
    result=dict(status='passed',originalTemplates=6,bodyAssignments=174,femaleVariants=80,
        exactHeadPlacements=head_count,allBodySilhouettesMatchTheirMaster=True,
        originalUserArtworkPreserved=True,headScaling=False,headRedraws=0,orcDwarfShareStocky=True,hybridAppearances=146,hybridFamilySheets=11,headsAndBodyCoresUnchangedSincePolish=True,identityMarksClippedToSkin=True,
        browserCharactersChecked=checked,walkPreview=True,exports=True,recipes=True,browserErrors=errors,
        scope='Pixel preservation, shared body geometry and viewer behavior; extraction boundaries remain subject to visual review. Armor is not rebuilt.')
    (DEST/'verification.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))


if __name__=='__main__':asyncio.run(main())

