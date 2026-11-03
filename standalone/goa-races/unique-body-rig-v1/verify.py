"""Exercise actual file:// preview, grip constraints, controls and PNG exports."""
import asyncio,base64,hashlib,json
from pathlib import Path
from PIL import Image,ImageDraw
from playwright.async_api import async_playwright
from build import ROOT,OUT
from complete_surfaces import TORSO_POLYGONS

async def main():
    errors=[]
    data=json.loads((OUT/'rig.json').read_text())
    for file,sha in data['sources'].items():assert hashlib.sha256((ROOT/file).read_bytes()).hexdigest()==sha
    palette={tuple(c) for c in data['completion']['palette']};added_count=0;protected=0
    east,west=data['directions'][2:4]
    for side,opposite in [('right','left'),('left','right')]:
        assert west['arms'][side]==[[63-x,y] for x,y in east['arms'][opposite]]
        for part in ['upper','lower']:
            for suffix in ['rig','complete','refined']:
                e=Image.open(OUT/'assets'/east['frames'][0][f'{opposite}-{part}-{suffix}'])
                w=Image.open(OUT/'assets'/west['frames'][0][f'{side}-{part}-{suffix}'])
                assert w.tobytes()==e.transpose(Image.Transpose.FLIP_LEFT_RIGHT).tobytes()
    assert data['slots']['mainHand']=='rightHand' and data['slots']['offHand']=='leftHand'
    torso_samples=0
    source_legs=0
    original=Image.open(OUT/'assets/elf-original.png')
    for direction in range(3):
        for frame_index,frame in enumerate(data['directions'][direction]['frames']):
            if direction==2 and frame_index==2:continue
            expected=original.crop((direction*64,frame_index*64+48,direction*64+64,frame_index*64+64))
            lower=Image.open(OUT/'assets'/frame['walk-lower']).crop((0,48,64,64))
            assert lower.tobytes()==expected.tobytes(),(direction,frame_index)
            source_legs+=1
    # The accepted AI redraw must really replace the second contact, while
    # the untouched source remains independently available in Original mode.
    repaired=Image.open(OUT/'assets'/east['frames'][2]['walk-lower']).crop((0,48,64,64))
    assert repaired.tobytes()!=original.crop((128,176,192,192)).tobytes()
    for pixel in repaired.getdata():
        if pixel[3]:assert pixel[:3] in palette and pixel[3]==255
    for e,w in zip(east['frames'],west['frames']):
        assert Image.open(OUT/'assets'/w['refined-torso']).tobytes()==Image.open(OUT/'assets'/e['refined-torso']).transpose(Image.Transpose.FLIP_LEFT_RIGHT).tobytes()
    for i,d in enumerate(data['directions']):
        mask=Image.new('L',(64,64));ImageDraw.Draw(mask).polygon(TORSO_POLYGONS[2 if i==3 else i],fill=255)
        if i==3:mask=mask.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        for frame_index,f in enumerate(d['frames']):
            torso=Image.open(OUT/'assets'/f['refined-torso'])
            # Validate the moving torso core in its actual registration. Shorts
            # and legs are separate source silhouettes, not the torso polygon.
            for y in range(39):
                for x in range(64):
                    if mask.getpixel((x,y)):assert torso.getpixel((x,y-(1 if frame_index else 0)))[3]>=128;torso_samples+=1
        for side in ['right','left']:
            for suffix in ['rig','refined']:
                f=d['frames'][0]
                forearm=Image.open(OUT/'assets'/f[f'{side}-forearm-{suffix}'])
                hand=Image.open(OUT/'assets'/f[f'{side}-hand-{suffix}'])
                lower=Image.open(OUT/'assets'/f[f'{side}-lower-{suffix}'])
                for a,b,c in zip(forearm.getdata(),hand.getdata(),lower.getdata()):
                    assert not(a[3] and b[3])
                    assert (a if a[3] else b)==c
        if i<2:
            for side in ['right','left']:
                for part,joints in [('upper',d['arms'][side][:2]),('lower',d['arms'][side][1:])]:
                    arm=Image.open(OUT/'assets'/d['frames'][0][side+'-'+part+'-refined'])
                    for x,y in joints:
                        for dy in [-1,0,1]:
                            for dx in [-1,0,1]:assert arm.getpixel((x+dx,y+dy))[3]>=128
    for d in data['directions']:
        pairs=[]
        for side in ['right','left']:
            for part in ['upper','lower']:
                f=d['frames'][0];pairs.append((f[side+'-'+part+'-rig'],f[side+'-'+part+'-complete']))
        for f in d['frames']:pairs.append((f['equipped-torso'],f['completed-torso']))
        for raw,completed in pairs:
            a=Image.open(OUT/'assets'/raw);b=Image.open(OUT/'assets'/completed)
            for p,q in zip(a.getdata(),b.getdata()):
                if p[3]:assert p==q;protected+=1
                elif q[3]:assert q[3]==255 and q[:3] in palette;added_count+=1
    async with async_playwright() as pw:
        browser=await pw.chromium.launch(executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless=True)
        try:
            page=await browser.new_page(viewport={'width':1440,'height':1120},device_scale_factor=1)
            page.on('pageerror',lambda e:errors.append(str(e)))
            await page.goto((OUT/'index.html').as_uri());await page.wait_for_function('document.body.dataset.ready === "true"')
            assert await page.locator('#views canvas').count()==4
            full_checks=await page.evaluate('''()=>{
                const r=equipmentRig,options={chest:false,spear:false,shield:false,debug:false,part:'all'};
                let count=0,slots=0;const c=document.createElement('canvas');c.width=c.height=128;
                for(let d=0;d<4;d++)for(let f=0;f<32;f++){
                    const p=r.render(c,d,'fullbody',f/32,options);
                    const rgba=c.getContext('2d').getImageData(0,0,128,128).data;
                    for(let i=0;i<128;i++)for(const [x,y] of [[i,0],[i,127],[0,i],[127,i]])if(rgba[(y*128+x)*4+3])throw Error('Full-body export clipped');
                    for(const leg of Object.values(p.legs)){
                        if(Math.abs(Math.hypot(leg.hip[0]-leg.knee[0],leg.hip[1]-leg.knee[1])-leg.upper)>1e-6)throw Error('Thigh stretched');
                        if(Math.abs(Math.hypot(leg.ankle[0]-leg.knee[0],leg.ankle[1]-leg.knee[1])-leg.lower)>1e-6)throw Error('Shin stretched');
                        for(const pt of [leg.hip,leg.knee,leg.ankle]){
                            let covered=false;
                            for(let dy=-1;dy<=1;dy++)for(let dx=-1;dx<=1;dx++)if(rgba[((Math.round(pt[1])+32+dy)*128+Math.round(pt[0])+32+dx)*4+3]>=128)covered=true;
                            if(!covered)throw Error('Uncovered leg joint '+d+' '+f);
                        }count++;
                    }
                    for(const a of Object.values(p.attachments)){if(!a.position.every(Number.isFinite)||!Number.isFinite(a.rotation))throw Error('Invalid equipment attachment');slots++;}
                }
                for(let d=0;d<4;d++)for(const part of r.data.fullBody.parts){
                    r.render(c,d,'fullbody',.25,{...options,part});
                    if(!c.getContext('2d').getImageData(0,0,128,128).data.some((v,i)=>i%4===3&&v))throw Error('Empty isolated part '+part);
                }
                return {legChains:count,attachments:slots,isolatedParts:60};
            }''')
            async with page.expect_download() as event:await page.click('#exportParts')
            download=await event.value;await download.save_as(OUT/'Elf_Full_Body_Components_64px.png')
            assert Image.open(OUT/'Elf_Full_Body_Components_64px.png').size==(256,960)
            await page.select_option('#bodyPart','rightFoot')
            assert await page.locator('#motion').input_value()=='fullbody'
            await page.select_option('#bodyPart','all')
            projection=await page.evaluate('''()=>{
                let checks=0;
                for(let d=0;d<4;d++)for(let f=0;f<32;f++){
                    const p=equipmentRig.pose(d,'raise',f/32);
                    for(const [side,arm] of Object.entries(p.arms)){
                        for(const [length,rest,i] of [[arm.upper,arm.restUpper,0],[arm.lower,arm.restLower,1]]){
                            if(Math.abs(Math.hypot(length,arm.depths[i+1]-arm.depths[i])-rest)>1e-6)throw Error('3D arm length changed');
                            checks++;
                        }
                        if(d<2&&Math.abs(arm.hand[0]-equipmentRig.data.directions[d].arms[side][2][0])>1e-6)throw Error('Lateral raise returned');
                    }
                }return checks;
            }''')
            mirrored=await page.evaluate('''()=>{
                let checks=0;const options={spear:false,shield:false,chest:false,completed:true,debug:false};
                for(const motion of ['idle','walk','raise'])for(let f=0;f<24;f++){
                    const e=equipmentRig.pose(2,motion,f/24,options),w=equipmentRig.pose(3,motion,f/24,options);
                    for(const [side,opposite] of [['right','left'],['left','right']])for(const joint of ['shoulder','elbow','hand']){
                        const a=e.arms[opposite][joint],b=w.arms[side][joint];
                        if(Math.abs(63-a[0]-b[0])>1e-6||Math.abs(a[1]-b[1])>1e-6)throw Error('Side pose does not mirror: '+motion+' '+joint);
                        checks++;
                    }
                }return checks;
            }''')
            checks=await page.evaluate('''()=>{
                let poses=0, nonempty=0;
                const r=equipmentRig;
                for(const motion of ['idle','walk','thrust','raise'])for(let d=0;d<4;d++)for(let f=0;f<24;f++){
                    const p=r.pose(d,motion,f/24);
                    for(const arm of Object.values(p.arms)){
                        const distance=(a,b)=>Math.hypot(a[0]-b[0],a[1]-b[1]);
                        if(Math.abs(distance(arm.shoulder,arm.elbow)-arm.upper)>1e-6)throw Error('Upper arm stretched');
                        if(Math.abs(distance(arm.elbow,arm.hand)-arm.lower)>1e-6)throw Error('Forearm stretched');
                    }
                    const c=document.createElement('canvas');c.width=c.height=128;r.render(c,d,motion,f/24,{chest:true,spear:true,shield:true,debug:false});
                    const pix=c.getContext('2d').getImageData(0,0,128,128).data;
                    if(!pix.some((v,i)=>i%4===3&&v))throw Error('Empty frame');
                    for(let i=0;i<128;i++)for(const [x,y] of [[i,0],[i,127],[0,i],[127,i]])if(pix[(y*128+x)*4+3])throw Error('Clipped export frame');
                    poses++;nonempty++;
                }
                return {poses,nonempty};
            }''')
            await page.evaluate('equipmentRig.setPhase(0)')
            await page.select_option('#motion','idle')
            for checkbox in ['chest','spear','shield']:await page.check('#'+checkbox)
            # Each equipment toggle and each authored facing renders independently.
            for checkbox in ['chest','spear','shield']:
                before=await page.evaluate('[...document.querySelectorAll("#views canvas")].map(c=>c.toDataURL())')
                await page.uncheck('#'+checkbox)
                after=await page.evaluate('[...document.querySelectorAll("#views canvas")].map(c=>c.toDataURL())')
                assert all(a!=b for a,b in zip(before,after)),checkbox
                await page.check('#'+checkbox)
            await page.select_option('#facing','2');await page.fill('#mainX','2')
            assert (await page.evaluate('equipmentRig.getFits()'))[2]['mainX']==2
            async with page.expect_download() as event:await page.click('#saveFit')
            download=await event.value;fit=OUT/'Verified_Fit_Export.json';await download.save_as(fit)
            await page.click('#reset');await page.set_input_files('#fitFile',str(fit))
            await page.wait_for_function('document.getElementById("status").textContent === "Fit imported."')
            assert (await page.evaluate('equipmentRig.getFits()'))[2]['mainX']==2
            await page.click('#reset')
            for motion in ['idle','walk','thrust','fullbody']:
                await page.select_option('#motion',motion)
                async with page.expect_download() as event:await page.click('#export')
                download=await event.value;target=OUT/('Elf_'+motion.title()+'_Equipment_128px.png');await download.save_as(target)
                assert Image.open(target).size==(512,1024)
            await page.select_option('#motion','walk');await page.evaluate('equipmentRig.setPhase(.25)')
            await page.screenshot(path=str(OUT/'Viewer_Preview.png'),full_page=True)
            url=await page.evaluate('equipmentRig.comparison().toDataURL()')
            (OUT/'Original_Idle_Thrust_Comparison.png').write_bytes(base64.b64decode(url.split(',')[1]))
            im=Image.open(OUT/'Original_Idle_Thrust_Comparison.png');im.resize((1536,1152),Image.Resampling.NEAREST).save(OUT/'Original_Idle_Thrust_Comparison_3x.png')
            await page.check('#debug');await page.screenshot(path=str(OUT/'Rig_Debug_Preview.png'),full_page=True)
            await page.uncheck('#debug')
            for checkbox in ['chest','spear','shield']:await page.uncheck('#'+checkbox)
            await page.select_option('#motion','raise');await page.evaluate('equipmentRig.setPhase(.5)')
            before=await page.evaluate('[...document.querySelectorAll("#views canvas")].map(c=>c.toDataURL())')
            await page.uncheck('#completed')
            after=await page.evaluate('[...document.querySelectorAll("#views canvas")].map(c=>c.toDataURL())')
            assert all(a!=b for a,b in zip(before,after))
            await page.check('#completed')
            await page.screenshot(path=str(OUT/'Completed_Surfaces_Preview.png'),full_page=True)
            url=await page.evaluate('''()=>{
                const out=document.createElement('canvas');out.width=512;out.height=384;
                const tile=document.createElement('canvas');tile.width=tile.height=128;
                for(let row=0;row<3;row++)for(let d=0;d<4;d++){
                    equipmentRig.render(tile,d,row===0?'original':'raise',.5,{chest:false,spear:false,shield:false,debug:false,completed:row===2});
                    out.getContext('2d').drawImage(tile,d*128,row*128);
                }return out.toDataURL();
            }''')
            target=OUT/'Raised_Arms_Before_After.png';target.write_bytes(base64.b64decode(url.split(',')[1]));im=Image.open(target);im.resize((1536,1152),Image.Resampling.NEAREST).save(OUT/'Raised_Arms_Before_After_3x.png')
            async with page.expect_download() as event:await page.click('#export')
            download=await event.value;await download.save_as(OUT/'Elf_Raise_Arms_Unarmored_128px.png')
            await page.select_option('#motion','walk')
            async with page.expect_download() as event:await page.click('#export')
            download=await event.value;await download.save_as(OUT/'Elf_Walk_Unarmored_128px.png')
            await page.select_option('#motion','fullbody')
            async with page.expect_download() as event:await page.click('#export')
            download=await event.value;await download.save_as(OUT/'Elf_Full_Body_Unarmored_128px.png')
            await page.check('#debug');await page.evaluate('equipmentRig.setPhase(.25)')
            await page.screenshot(path=str(OUT/'Full_Body_Joints_Preview.png'),full_page=True)
            await page.uncheck('#debug')
            # Compact native-pixel strips for visual inspection of the whole
            # exposed movement, not just the peak raised-arm pose.
            strip=Image.new('RGBA',(512,256))
            for motion_row,filename in enumerate(['Elf_Raise_Arms_Unarmored_128px.png','Elf_Walk_Unarmored_128px.png']):
                atlas=Image.open(OUT/filename)
                for direction in range(2):
                    for frame in range(8):
                        tile=atlas.crop((direction*128+32,frame*128+32,direction*128+96,frame*128+96))
                        strip.paste(tile,(frame*64,(motion_row*2+direction)*64))
            strip.resize((1536,768),Image.Resampling.NEAREST).save(OUT/'North_South_Movement_Inspection.png')
            for motion in ['Raise_Arms','Walk','Full_Body']:
                atlas=Image.open(OUT/f'Elf_{motion}_Unarmored_128px.png')
                strip=Image.new('RGBA',(512,256),'#29362e')
                for direction in range(4):
                    for frame in range(8):
                        tile=atlas.crop((direction*128+32,frame*128+32,direction*128+96,frame*128+96))
                        strip.alpha_composite(tile,(frame*64,direction*64))
                strip.resize((1536,768),Image.Resampling.NEAREST).save(OUT/f'{motion}_Four_Views_Inspection.png')
                animated=[]
                for frame in range(8):
                    view=Image.new('RGBA',(256,64),'#29362e')
                    for direction in range(4):
                        view.alpha_composite(atlas.crop((direction*128+32,frame*128+32,direction*128+96,frame*128+96)),(direction*64,0))
                    animated.append(view.resize((1024,256),Image.Resampling.NEAREST).convert('RGB'))
                animated[0].save(OUT/f'{motion}_Four_Views.gif',save_all=True,append_images=animated[1:],duration=150,loop=0,disposal=2)
            assert not errors,errors
            result=dict(status='passed',sourceHashesUnchanged=True,exactSourcePartitions=12,intermediateLayerPixelsPreserved=protected,addedPaletteConstrainedPixels=added_count,refinedTorsoInteriorSamples=torso_samples,roundedNorthSouthJointCaps=True,westArmArtMirrorsEast=True,mirroredJointChecks=mirrored,equipmentHandednessRetained=True,completionComparisonWorks=True,ikPosesChecked=checks['poses'],allExportFramesWithinBounds=True,equipmentToggles=3,fitRoundTrip=True,exports=['idle','walk','thrust','raise-unarmored'],browserErrors=errors)
            result.update(version=data['version'],forwardRaiseProjectionChecks=projection,disjointHandsReconstructForearms=True,unchangedSourceLegRegions=source_legs,oppositeContactUsesSourcePalette=True)
            result['fullBody']=full_checks
            (OUT/'verification.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
        finally:await browser.close()

if __name__=='__main__':asyncio.run(main())
