"""Fit native equipment designs on actual standing race bodies for visual review."""
import asyncio,base64,json,os
from pathlib import Path
from io import BytesIO
from PIL import Image,ImageDraw
from playwright.async_api import async_playwright
import build

HERE=Path(__file__).resolve().parent
RACES=HERE.parents[1]
ROOT=HERE.parents[3]
IDS=['human','dwarf','elf','dark-elf','orc','goblin','kobold']
RUNTIME=HERE/'worn-runtime-v2.js'


def encoded(path):return 'data:image/png;base64,'+base64.b64encode(path.read_bytes()).decode()
def png(path,data):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(base64.b64decode(data.split(',',1)[1]))


async def main():
    catalog=json.loads((HERE/'catalog.json').read_text())
    approved=RACES/'armor-designs/deepguard-iron/pixel-fit-v2/pieces'
    manifest=json.loads((approved/'manifest.json').read_text())
    master=dict(id='deepguard-iron-approved',label='Deepguard Iron — approved design',registeredMaster=True,fitBody='human',crafting=dict(onlyRace=None),sha256=__import__('hashlib').sha256((approved/'manifest.json').read_bytes()).hexdigest(),parts=[p['id'] for p in manifest['parts'] if p['id']!='body-reference'],frames=[])
    catalog['sheets'].append(master)
    kits=[s for s in catalog['sheets'] if s.get('registeredMaster') or (s['crafting'] and s['crafting']['onlyRace'] in IDS)]
    groups=dict(helmets=[],weapons=[],shields=[],chests=[])
    for s in catalog['sheets']:
        for part in s['parts']:
            entry=dict(value=s['id']+'::'+part,label=part.replace('weapon.','').replace('shield.','').replace('helmet.','').replace('ornate.','Ornate ').replace('chest.','').replace('robe.','Robe: ').replace('.',' ').title())
            if s['id'] in ['custom-helmets','ornate-helmets','dragon-helmets']:
                if s['id']=='ornate-helmets':entry['label']='Gem-set '+entry['label']
                groups['helmets'].append(entry)
            elif s['id'] in ['melee-weapons','polearms-tools','magic-staves','enchanted-weapons']:groups['weapons'].append(entry)
            elif s['id']=='custom-shields':groups['shields'].append(entry)
            elif s['id'] in ['robe-colors','special-robes','ornate-armor-finishes'] or (s['id']=='armor-styles' and part.startswith(('chest.','goa.chest'))):groups['chests'].append(entry)
    data=dict(catalog=catalog,images={},bodies=[],kitIds=[s['id'] for s in kits],groups=groups)
    for s in catalog['sheets']:
        for f in s['frames']:
            if f.get('visible') and f.get('file'):data['images'][s['id']+':'+f['part']+':'+str(['South','North','East','West'].index(f['direction']))]=encoded(HERE/f['file'])
    def image_url(image):
        b=BytesIO();image.save(b,format='PNG');return 'data:image/png;base64,'+base64.b64encode(b.getvalue()).decode()
    for part in master['parts']:
        with Image.open(approved/'64px'/(part+'.png')) as im:
            for view in range(4):
                data['images'][master['id']+':'+part+':'+str(view)]=image_url(im.crop((view*64,0,view*64+64,64)))
                master['frames'].append(dict(part=part,direction=['South','North','East','West'][view]))
    reference=Image.new('RGBA',(512,128))
    with Image.open(approved/'reassembled-64px.png') as original:
        for v in range(4):reference.alpha_composite(original.crop((v*64,0,v*64+64,64)),(v*128+32,32))
    reference.save(HERE/'deepguard-approved-reference.png');data['approvedReference']=image_url(reference)
    errors=[];fits={}
    async with async_playwright() as pw:
        browser=await pw.chromium.launch(executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless=True)
        try:
            page=await browser.new_page(viewport=dict(width=1300,height=1100));page.on('pageerror',lambda e:errors.append(str(e)))
            await page.route('**/*',lambda r:r.continue_() if r.request.url.startswith(('file:','data:')) else r.abort())
            await page.goto((RACES/'armory/index.html').as_uri());await page.wait_for_function('Armory?.ready && Armory.frame()!=null')
            data['bodies']=await page.evaluate('ids=>ids.map(id=>{const E=Armory.engine,b=E.bodies.get(id);return{id,label:b.label,views:[0,1,2,3].map(v=>{const f=E.bodyFrame(id,v,0),rig=E.rig(id,v,0);return{rig,png:f.image.toDataURL(),features:E.headFeatures(f,rig).toDataURL()};})};})',IDS)
            data['masterWidths']=[v['rig']['width'] for v in data['bodies'][0]['views']]
            for b in data['bodies']:
                for v,f in enumerate(b['views']):
                    data['images']['body:'+b['id']+':'+str(v)]=f.pop('png');data['images']['features:'+b['id']+':'+str(v)]=f.pop('features')
            await page.evaluate('data=>window.WORN_DATA=data',data);await page.add_script_tag(path=str(RUNTIME));await page.evaluate('NativeWorn.init()')
            for s in kits:
                body=s['crafting']['onlyRace'] or s.get('fitBody','human');value=await page.evaluate('([b,s])=>{const r=NativeWorn.render(b,s);return{png:r.canvas.toDataURL(),parts:Object.fromEntries(Object.entries(r.layers).map(([k,v])=>[k,v.toDataURL()])),placements:r.placements};}',[body,s['id']])
                if s.get('registeredMaster'):assert all(f['rect']==[0,0,64,64] for f in value['placements']),'Approved Human geometry changed'
                folder=HERE/'worn'/s['id'];png(folder/'equipped.png',value['png'])
                for part,image in value['parts'].items():png(folder/(part+'.png'),image)
                metadata=dict(sourceSha256=s['sha256'],bodyId=body,file=str((folder/'equipped.png').relative_to(HERE)),frameSize=[128,128],bodyOrigin=[32,32],bodySpace=[64,64],status='preliminary standing fit; review anatomy and depth before use',placements=value['placements'],animations='no new walk/attack poses authored')
                (folder/'manifest.json').write_text(json.dumps(metadata,indent=2));fits[s['id']]=metadata
            # Verify each shared leather master also renders on all seven body sizes.
            cross=await page.evaluate('ids=>{let count=0;for(const body of ids)for(const set of WORN_DATA.kitIds.filter(id=>id.endsWith("-leather"))){const r=NativeWorn.render(body,set);if(r.placements.length!==WORN_DATA.catalog.sheets.find(s=>s.id===set).frames.length)throw Error("Missing placement "+body+"/"+set);count++;}return count;}',IDS)
            overview=Image.new('RGB',(7*144,340),(17,24,30));draw=ImageDraw.Draw(overview)
            for col,body in enumerate(IDS):
                for row,bare in enumerate([True,False]):
                    url=await page.evaluate('([b,set,bare])=>NativeWorn.render(b,set,{bare}).canvas.toDataURL()',[body,body+'-leather',bare])
                    im=Image.open(BytesIO(base64.b64decode(url.split(',',1)[1]))).convert('RGBA').crop((24,24,104,104)).resize((144,144),Image.Resampling.NEAREST)
                    overview.paste(im,(col*144,22+row*150),im)
                draw.text((col*144+6,4),body,fill='white')
            overview.save(HERE/'leather-worn-overview.png')
            # The approved master keeps one registration for every layer. Race
            # previews use a shared horizontal/vertical body-family transform.
            master_overview=Image.new('RGB',(7*144,190),(17,24,30));md=ImageDraw.Draw(master_overview)
            for col,body in enumerate(IDS):
                url=await page.evaluate('b=>NativeWorn.render(b,"deepguard-iron-approved").canvas.toDataURL()',body)
                png(HERE/'worn/deepguard-iron-approved'/('on-'+body+'.png'),url)
                im=Image.open(BytesIO(base64.b64decode(url.split(',',1)[1]))).convert('RGBA').crop((24,24,104,104)).resize((144,144),Image.Resampling.NEAREST)
                master_overview.paste(im,(col*144,24),im);md.text((col*144+5,5),body,fill='white')
            master_overview.save(HERE/'deepguard-worn-races.png')
            comparison=Image.new('RGB',(640,362),(17,24,30));cd=ImageDraw.Draw(comparison)
            sources=[reference,Image.open(HERE/'worn/deepguard-iron-approved/equipped.png').convert('RGBA')]
            for row,source in enumerate(sources):
                cd.text((8,row*180+3),['Approved Deepguard design','Same registered armor on the actual Human body'][row],fill='white')
                for view in range(4):
                    sprite=source.crop((view*128+24,24,view*128+104,104)).resize((160,160),Image.Resampling.NEAREST)
                    comparison.paste(sprite,(view*160,row*180+22),sprite)
            comparison.save(HERE/'deepguard-reference-vs-worn.png')
            loadouts=[
                dict(label='Deepguard Iron',body='human',kit='deepguard-iron-approved',options=dict(weapon='melee-weapons::weapon.arming sword',shield='custom-shields::shield.round')),
                dict(label='Winged helm',body='human',kit='deepguard-iron-approved',options=dict(helmet='custom-helmets::helmet.winged',weapon='melee-weapons::weapon.longsword',shield='custom-shields::shield.heater')),
                dict(label='Dwarf gold',body='dwarf',kit='dwarf-gold',options=dict(weapon='melee-weapons::weapon.warhammer',shield='custom-shields::shield.buckler')),
                dict(label='Elf leather',body='elf',kit='elf-leather',options=dict(weapon='polearms-tools::weapon.bow')),
                dict(label='Orc bone',body='orc',kit='orc-bone',options=dict(weapon='melee-weapons::weapon.battle axe',shield='custom-shields::shield.tower')),
                dict(label='Dragonhide',body='kobold',kit='kobold-dragonhide',options=dict(weapon='polearms-tools::weapon.spear')),
                dict(label='Gem-set iron',body='human',kit='deepguard-iron-approved',options=dict(helmet='ornate-helmets::ornate.helmet.nasal',chest='ornate-armor-finishes::human.iron.gold-trim.ruby',weapon='enchanted-weapons::weapon.flame sword')),
                dict(label='Blue robes',body='human',kit='human-leather',options=dict(helmet='none',chest='robe-colors::robe.blue',weapon='magic-staves::weapon.crystal staff')),
            ]
            data['loadouts']=loadouts
            board=Image.new('RGB',(820,len(loadouts)*150),(17,24,30));bd=ImageDraw.Draw(board)
            for row,loadout in enumerate(loadouts):
                value=await page.evaluate('x=>NativeWorn.render(x.body,x.kit,x.options).canvas.toDataURL()',loadout)
                png(HERE/'worn/loadouts'/(str(row)+'.png'),value)
                source=Image.open(BytesIO(base64.b64decode(value.split(',',1)[1]))).convert('RGBA');bd.text((5,row*150+8),loadout['label'],fill='white')
                for view in range(4):
                    sprite=source.crop((view*128+16,16,view*128+112,112)).resize((144,144),Image.Resampling.NEAREST)
                    board.paste(sprite,(220+view*148,row*150+3),sprite)
            board.save(HERE/'loadouts-worn-overview.png')
            html=(HERE/'worn.template.html').read_text().replace('__ASSET_ROOT__',json.dumps(HERE.as_uri()+'/')).replace('/*DATA*/null',json.dumps(data,separators=(',',':'))).replace('/*RUNTIME*/',RUNTIME.read_text())
            (HERE/'worn.html').write_text(html)
            await page.goto((HERE/'worn.html').as_uri());await page.wait_for_function('window.wornReady===true')
            await page.select_option('#set','orc-leather');await page.select_option('#body','goblin');await page.select_option('#set','deepguard-iron-approved');await page.select_option('#body','human')
            for field,value in loadouts[0]['options'].items():await page.select_option('#'+field,value)
            assert not errors,errors
            await page.screenshot(path=str(HERE/'worn-gallery.png'),full_page=True)
        finally:await browser.close()
    (HERE/'fit-results.json').write_text(json.dumps(fits,indent=2))
    (HERE/'worn-verification.json').write_text(json.dumps(dict(status='passed composition checks; standing fit workshop',nativeKits=len(kits),selectableGear={k:len(v) for k,v in groups.items()},baseBodies=7,sharedLeatherCombinations=cross,approvedDeepguardMaster=dict(referenceGeometryPreservedOnHuman=True,bodyOrigin=[32,32],source='deepguard-iron/pixel-fit-v2/pieces/64px',otherRaceFits='shared body-family scale; manual fit review remains'),directions=4,browserErrors=errors),indent=2))
    sample=ROOT/'Dungeon Master Sample';link=sample/'New Armor Worn on Races.html'
    if not link.exists():link.symlink_to(os.path.relpath(HERE/'worn.html',sample))
    old_export=ROOT/'standalone/goa-races/gear-generator/generated/index.html'
    archive_link=sample/'Generated Matching Gear Source Export.html'
    if not archive_link.exists():archive_link.symlink_to(os.path.relpath(old_export,sample))
    current=sample/'Generated Matching Gear.html'
    if current.is_symlink() and current.resolve() in [old_export,HERE/'worn.html']:
        current.unlink();current.symlink_to(os.path.relpath(HERE/'worn.html',sample))
    build.build();print(json.dumps(dict(kits=len(kits),crossRaceLeatherPreviews=cross,viewer=str(link))),flush=True)


if __name__=='__main__':asyncio.run(main())
