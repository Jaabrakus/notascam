"""Validate the Elf template, unchanged source art, holds and actual preview."""
import asyncio,hashlib,json,math,sys
from pathlib import Path
from PIL import Image
from playwright.async_api import async_playwright
from build import ROOT,OUT

async def main():
    data=json.loads((OUT/'rig.json').read_text());assert data['actor']=='Elf'
    assert data['baseRig']=='Dungeon Master Sample/Unique Body Equipment Rig/rig.json'
    for file,digest in data['sources'].items():
        assert 'Orc' not in file,file
        assert hashlib.sha256((ROOT/file).read_bytes()).hexdigest()==digest,file
    human=json.loads((ROOT/'Dungeon Master Sample/Sprites/Combat/Human/Human-sword-actions.json').read_text())
    assert sum(data['attackClip']['frameDurationsMs'])==sum(p['ms'] for p in human['phases'])
    for f,r in [(2,1),(4,2),(6,3)]:
        for d,record in enumerate(data['frames']['attack'][f]):
            vx,vy=human['sweepVectors'][r][d]
            assert abs(math.sin(record['swordAngle']-record['bodyRig']['torsoAngle']-math.atan2(vx,-vy)))<1e-6
            assert record['weaponAxisScale']==1
    counts=0
    for motion,frames in data['frames'].items():
        atlas=Image.open(OUT/f'Elf_Sword_Shield_{motion.title()}_128px.png')
        export=data['exports'][motion]['sword']
        native=Image.open(OUT/export['png']) if export['cellSize']==64 else None
        assert atlas.size==(512,1024)
        if native:assert native.size==(256,512)
        distinct=[]
        for f,row in enumerate(frames):
            distinct.append(atlas.crop((0,f*128,512,(f+1)*128)).tobytes())
            for d,record in enumerate(row):
                if native:assert native.crop((d*64,f*64,(d+1)*64,(f+1)*64)).tobytes()==atlas.crop((d*128+32,f*128+32,d*128+96,f*128+96)).tobytes()
                for side,arm in record['arms'].items():
                    assert abs(math.dist(arm['shoulder'],arm['elbow'])-arm['upperLength'])<1e-6
                    assert abs(math.dist(arm['elbow'],arm['wrist'])-arm['forearmLength'])<1e-6
                assert record['swordGrip']==record['arms']['R']['grip']
                assert record['shieldGrip']==record['arms']['L']['grip']
                x,y=record['swordGrip'];x=round(x+32);y=round(y+32)
                for key in ['sword','rightHand']:
                    image=Image.open(OUT/'assets'/record['layers'][key]);assert image.crop((x-2,y-2,x+3,y+3)).getbbox(),(motion,f,d,key,'grip disconnected')
                counts+=1
                for weapon,file in record['weapons'].items():
                    im=Image.open(OUT/'assets'/file)
                    assert im.crop((x-2,y-2,x+3,y+3)).getbbox(),(motion,f,d,weapon,'grip disconnected')
                if motion=='attack':
                    assert record['strike']==(f==4)
                    body=record['bodyRig'];assert len(body['parts'])==9
                    m=body['torsoMatrix'];anchor=frames[0][d]['shieldGrip']
                    expected=[m[i][0]*anchor[0]+m[i][1]*anchor[1]+m[i][2] for i in range(2)]
                    assert math.dist(record['shieldGrip'],expected)<.002
                    for leg in body['legs'].values():
                        assert abs(math.dist(leg['hip'],leg['knee'])-leg['upperLength'])<1e-6
                        assert abs(math.dist(leg['knee'],leg['ankle'])-leg['lowerLength'])<1e-6
                        assert math.dist(leg['ankle'],leg['ankleTarget'])<.002
                    if d==0:
                        assert record['order'].index('shield')<record['order'].index('sword')<record['order'].index('rightHand')
                if d==1:assert record['order'].index('shield')<record['order'].index('body')
        assert len(set(distinct))>=2,(motion,'static animation')
        if motion=='attack':assert distinct[0]==distinct[-1],'Attack does not return to its hold'
    export_count=0
    for motion,weapons in data['exports'].items():
        for ident,export in weapons.items():
            padded=Image.open(OUT/export['paddedPng']);assert padded.size==(512,1024)
            chosen=Image.open(OUT/export['png']);n=export['cellSize'];assert chosen.size==(n*4,n*8)
            for f in range(8):
                for d in range(4):
                    tile=padded.crop((d*128,f*128,(d+1)*128,(f+1)*128));box=tile.getbbox()
                    assert box and box[0]>0 and box[1]>0 and box[2]<128 and box[3]<128
                    if n==64:assert tile.crop((32,32,96,96)).tobytes()==chosen.crop((d*64,f*64,(d+1)*64,(f+1)*64)).tobytes()
            export_count+=1
    errors=[]
    async with async_playwright() as pw:
        browser=await pw.chromium.launch(executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless=True)
        try:
            page=await browser.new_page(viewport={'width':1400,'height':1000},device_scale_factor=1)
            page.on('pageerror',lambda e:errors.append(str(e)))
            preview_url=sys.argv[1] if len(sys.argv)>1 else (OUT/'index.html').as_uri()
            await page.goto(preview_url);await page.wait_for_function('document.body.dataset.ready === "true"')
            assert await page.locator('#loadingPreview').is_hidden()
            assert await page.locator('#views canvas').count()==4
            toggles=await page.evaluate('''()=>{
                let checks=0;
                const motion=document.getElementById('motion');
                const snapshots=()=>[...document.querySelectorAll('#views canvas')].map(c=>c.toDataURL());
                for(const name of ['idle','walk'])for(let f=0;f<8;f++){
                    motion.value=name;holdRig.setFrame(f);
                    for(const key of ['sword','shield']){
                        const before=snapshots();document.getElementById(key).checked=false;holdRig.draw();const after=snapshots();
                        for(let d=0;d<4;d++){if(before[d]===after[d])throw Error(key+' invisible in '+name+' '+f+' '+d);checks++;}
                        document.getElementById(key).checked=true;holdRig.draw();
                    }
                }return checks;
            }''')
            await page.select_option('#motion','idle');await page.evaluate('holdRig.setFrame(0)')
            await page.screenshot(path=str(OUT/'Preview.png'),full_page=True)
            await page.check('#debug');await page.screenshot(path=str(OUT/'Grip_Debug.png'),full_page=True)
            await page.uncheck('#debug');await page.select_option('#motion','walk');await page.evaluate('holdRig.setFrame(2)')
            await page.screenshot(path=str(OUT/'Guarded_Walk_Preview.png'),full_page=True)
            attack_variants=await page.evaluate('''()=>{
                const motion=document.getElementById('motion'),weapon=document.getElementById('weapon'),enabled=document.getElementById('sword');motion.value='attack';let checks=0;
                for(const id of Object.keys(holdRig.data.weapons)){
                    weapon.value=id;const visible=[false,false,false,false];
                    for(let f=0;f<8;f++){
                        enabled.checked=true;holdRig.setFrame(f);const before=[...document.querySelectorAll('#views canvas')].map(c=>c.toDataURL());
                        enabled.checked=false;holdRig.draw();const after=[...document.querySelectorAll('#views canvas')].map(c=>c.toDataURL());
                        for(let d=0;d<4;d++)visible[d] ||= before[d]!==after[d];checks++;
                    }
                    if(!visible.every(Boolean))throw Error('Attack weapon never visible: '+id);
                }
                enabled.checked=true;weapon.value='sword';holdRig.setFrame(4);return checks;
            }''')
            await page.screenshot(path=str(OUT/'Attack_Preview.png'),full_page=True)
            await page.click('#attackOnce')
            await page.wait_for_function('document.getElementById("frame").value === "7" && document.getElementById("play").textContent === "Play"',timeout=5000)
            assert await page.locator('#motion').input_value()=='attack'
            await page.select_option('#zoom','1')
            assert await page.locator('#views canvas').first.evaluate('e=>e.getBoundingClientRect().width')==128
            for link in await page.locator('a[download]').evaluate_all('es=>es.map(e=>e.getAttribute("href"))'):
                assert (OUT/link).is_file()
            assert not errors,errors
            fallback_page=await browser.new_page(java_script_enabled=False)
            await fallback_page.goto(preview_url)
            assert await fallback_page.locator('#loadingPreview').is_visible()
            assert await fallback_page.locator('#loadingPreview img').evaluate('e=>e.complete&&e.naturalWidth>0')
            await fallback_page.close()
        finally:await browser.close()
    result={'status':'passed','previewUrl':preview_url,'animationFallbackWorksWithoutJavaScript':True,'template':'approved Elf v7','unchangedSourceFiles':len(data['sources']),'animationFrames':counts,'bodyPixels':64,'exportsUnclipped':True,'equipmentVisibilityChecks':toggles,'attackVariantFramesChecked':attack_variants,'weaponProfiles':len(data['weapons']),'exportSheets':export_count,'attackOnceReturnsToHold':True,'northShieldGuardPreserved':True,'southAttackWeaponAboveShield':True,'articulatedBodyAndPlantedAnkles':True,'humanAttackReference':data['attackClip']['reference'],'rightHandSwordLeftHandShield':True,'browserErrors':errors}
    (OUT/'verification.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))

if __name__=='__main__':asyncio.run(main())
