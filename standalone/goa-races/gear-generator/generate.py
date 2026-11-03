"""Generate the full shared gear pack and body-fit previews from existing art.

No AI/API calls. Original source sprites and gameplay definitions are read-only.
Only shared assets are stored per material; fit metadata covers all registered bodies.
"""
import argparse
import asyncio
import base64
import hashlib
from io import BytesIO
import json
from pathlib import Path
import shutil
import zipfile

from PIL import Image, ImageDraw
from playwright.async_api import async_playwright

HERE=Path(__file__).resolve().parent
RACES=HERE.parent
ROOT=HERE.parents[2]
CATALOG=RACES/'armory/catalog.json'
GAME=ROOT/'standalone/remastered/art/enhance/catalogue.json'
BASES=['human','dwarf','elf','dark-elf','orc','goblin','kobold']


def slug(value):
    import re
    return re.sub(r'[^a-zA-Z0-9._-]+','_',value)


def png(path,value):
    raw=base64.b64decode(value.split(',',1)[1]);im=Image.open(BytesIO(raw))
    if im.mode!='RGBA' or im.getchannel('A').getextrema()[0]!=0:
        raise ValueError('Missing transparency: '+str(path))
    if not im.getchannel('A').getbbox():raise ValueError('Empty image: '+str(path))
    path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)


def dump(path,value):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,indent=2))


def overview(output):
    materials=['iron','leather','gold','dragonbone','hell','chitin','dragonhide','blue']
    out=Image.new('RGB',(980,1150),(17,24,30));draw=ImageDraw.Draw(out)
    for col,body in enumerate(BASES):draw.text((col*138+20,8),body,fill='white')
    for row,material in enumerate(materials):
        top=28+row*140;draw.text((8,top),material,fill='#bed5de')
        for col,body in enumerate(BASES):
            source=output/'sets'/material/(body+'.png')
            if not source.exists():continue
            with Image.open(source) as sheet:
                sprite=sheet.convert('RGBA').crop((64,64,128,128)).resize((112,112),Image.Resampling.NEAREST)
                out.paste(sprite,(col*138+20,top+20),sprite)
    out.save(output/'overview.png')


def frame_crop(path):
    # Compute preview bounds at export time, so file:// galleries never need
    # canvas pixel reads (which browsers block for locally loaded images).
    boxes=[]
    with Image.open(path) as image:
        alpha=image.getchannel('A')
        for y in range(0,image.height,192):
            for x in range(0,image.width,192):
                box=alpha.crop((x,y,x+192,y+192)).getbbox()
                if box:boxes.append(box)
    x0=min(b[0] for b in boxes);y0=min(b[1] for b in boxes)
    x1=max(b[2] for b in boxes);y1=max(b[3] for b in boxes)
    size=min(192,max(96,((max(x1-x0,y1-y0)+19)//8)*8))
    return [max(0,min(192-size,(x0+x1-size)//2)),max(0,min(192-size,(y0+y1-size)//2)),size]


def game_mapping(catalog):
    designs={i['id']:i for i in catalog['items']};rows=json.loads(GAME.read_text())['items'];matched=[];missing=[]
    for row in rows:
        parts=row['id'].split('.')
        if row['id']=='legs.boots':key='feet.boots';material='original'
        elif parts[0]=='magic':key='weapon.'+parts[1];material=designs.get(key,{}).get('referenceMaterial','iron')
        else:key='.'.join(parts[:2]);material=parts[2] if len(parts)>2 else row.get('tier')
        design=designs.get(key)
        if not design or material not in design['materials']:
            missing.append(dict(gameId=row['id'],requestedDesign=key,material=material));continue
        matched.append(dict(gameId=row['id'],name=row['name'],design=key,material=material,slot=design['slot'],hands=row.get('hands',1),raceRules=row.get('who',{}),source='standalone/remastered/art/enhance/catalogue.json'))
    return dict(definitions=len(rows),matched=matched,missing=missing,scope='Generated gameplay equipment catalogue; old original item aliases are retained in the game source and are not enumerated as new item definitions here.')


def sets(catalog):
    items={i['id']:i for i in catalog['items']};materials=sorted({m for i in catalog['items'] for m in i['materials']});result=[]
    for mat in materials:
        loadout={slot:{'id':'','material':''} for slot in ['weapon','shield','head','chest','arms','legs','feet']}
        for slot,choices in {'weapon':['weapon.arming sword','weapon.longsword','weapon.dagger'], 'shield':['shield.round','shield.buckler'], 'head':['helmet.nasal','helmet.kettle'], 'chest':['chest.plate','chest.leather','chest.robe'], 'arms':['arms.plate','arms.leather'], 'legs':['legs.plate','legs.leather','legs.cloth']}.items():
            item=next((items[k] for k in choices if k in items and mat in items[k]['materials']),None)
            if item:loadout[slot]={'id':item['id'],'material':mat}
        if any(v['id'] for v in loadout.values()):
            loadout['feet']={'id':'feet.boots','material':'original'}
            result.append(dict(id=slug(mat),material=mat,loadout=loadout,notes='Only compatible material recipes are equipped; absent slots stay empty. Boots use their actual original leather artwork.'))
    return result


async def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=HERE/'generated')
    parser.add_argument('--all-bodies',action='store_true',help='Bake reference-material item previews for all bodies instead of the seven main fitting templates.')
    parser.add_argument('--resume',action='store_true')
    args=parser.parse_args();output=args.output.resolve()
    if ROOT not in output.parents:raise ValueError('Keep generated outputs within the project.')
    if shutil.disk_usage(ROOT).free<2*1024**3:raise RuntimeError('Less than 2 GB free; no files generated.')
    output.mkdir(parents=True,exist_ok=True)
    catalog=json.loads(CATALOG.read_text());mapping=game_mapping(catalog)
    digest=hashlib.sha256()
    for source in [CATALOG,RACES/'armory/bodies.json',RACES/'armory/equipment.js',RACES/'armory/index.html',HERE/'batch-runtime.js']:
        digest.update(source.read_bytes())
    build_key=digest.hexdigest()
    def cached(folder):
        path=folder/'manifest.json'
        if not args.resume or not path.exists():return None
        manifest=json.loads(path.read_text())
        if manifest.get('buildKey')!=build_key:return None
        images=[row['name'] for row in manifest.get('images',[])] or ['equipped.png','equipment-layer.png']
        return manifest if all((folder/name).exists() for name in images) else None
    if mapping['missing']:raise RuntimeError('Gameplay designs missing art: '+json.dumps(mapping['missing']))
    dump(output/'game-items.json',mapping);matching_sets=sets(catalog);dump(output/'material-sets.json',matching_sets)
    records=[];preview_records=[];errors=[]
    async with async_playwright() as playwright:
        browser=await playwright.chromium.launch(executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless=True)
        try:
            page=await browser.new_page(viewport=dict(width=1500,height=1000));page.on('pageerror',lambda e:errors.append(str(e)))
            await page.route('**/*',lambda r:r.continue_() if r.request.url.startswith(('file:','data:')) else r.abort())
            await page.goto((RACES/'armory/index.html').as_uri());await page.wait_for_function('window.Armory?.ready && Armory.frame()!=null')
            await page.add_script_tag(path=str(HERE/'batch-runtime.js'))
            fits=await page.evaluate('GearBatch.bodyFits()');dump(output/'body-fits.json',fits)
            ids=[b['id'] for b in fits] if args.all_bodies else BASES
            for index,item in enumerate(catalog['items']):
                for material in item['materials']:
                    key=slug(item['id'])+'/'+slug(material);folder=output/'assets'/key
                    manifest=cached(folder)
                    if manifest:
                        pass
                    else:
                        value=await page.evaluate('([id,m])=>GearBatch.asset(id,m)',[item['id'],material])
                        for image in value['images']:png(folder/image['name'],image['png'])
                        manifest=value['manifest'];manifest['buildKey']=build_key;manifest['images']=[{k:v for k,v in i.items() if k!='png'} for i in value['images']]
                        dump(folder/'manifest.json',manifest)
                    records.append(dict(id=item['id'],label=item['label'],slot=item['slot'],material=material,path='assets/'+key,images=[i['name'] for i in manifest['images']]))
                material=item.get('referenceMaterial') or ('iron' if 'iron' in item['materials'] else item['materials'][0])
                for body in ids:
                    folder=output/'fitted'/body/slug(item['id'])
                    if not cached(folder):
                        value=await page.evaluate('([id,m,b])=>GearBatch.fitted(id,m,b)',[item['id'],material,body])
                        value['manifest']['buildKey']=build_key
                        png(folder/'equipped.png',value['png']);png(folder/'equipment-layer.png',value['layer']);dump(folder/'manifest.json',value['manifest'])
                    preview_records.append(dict(id=item['id'],label=item['label'],slot=item['slot'],body=body,material=material,path='fitted/'+body+'/'+slug(item['id'])+'/equipped.png'))
                print(f"{index+1}/{len(catalog['items'])}: {item['label']} / {len(item['materials'])} materials",flush=True)
            sets_key=output/'sets/build-key.json'
            cached_sets=args.resume and sets_key.exists() and json.loads(sets_key.read_text()).get('key')==build_key
            for group in matching_sets:
                for body in BASES:
                    target=output/'sets'/group['id']/(body+'.png')
                    if not (cached_sets and target.exists()):png(target,await page.evaluate('([b,s])=>GearBatch.setPreview(b,s)',[body,group['loadout']]))
            dump(sets_key,dict(key=build_key))
            if errors:raise RuntimeError('Browser errors: '+str(errors))
        finally:await browser.close()
    # Include the separately authored starter design; it is not advertised as a full animation.
    deepguard=RACES/'armor-designs/deepguard-iron/pixel-fit-v2/pieces'
    if deepguard.exists():
        destination=output/'deepguard-pixel-starter';destination.mkdir(exist_ok=True)
        for source in (deepguard/'64px').glob('*.png'):shutil.copyfile(source,destination/source.name)
        starter=json.loads((deepguard/'manifest.json').read_text())
        starter['status']='standing-only visible-surface draft'
        for part in starter['parts']:
            part['file64']=Path(part['file64']).name
            part.pop('fileFull',None)
        dump(destination/'manifest.json',starter)
    overview(output)
    report=dict(status='complete',sourceArt='existing game art decoded and fitted through the shared renderer; this batch does not AI-redraw shapes',designs=len(catalog['items']),designMaterialVariants=len(records),gameDefinitions=mapping['definitions'],unmappedGameDefinitions=mapping['missing'],bodyFits=len(fits),fittedPreviewBodies=len(ids),itemPreviews=len(preview_records),materialSets=len(matching_sets),browserErrors=errors,bodyAnimationCoverage={s:sum(b['status']==s for b in fits) for s in ['walk','flight','standing_only']},missingArtwork=['Dedicated glove and cloak designs in the modern drawable catalog','Complete injury/limb-loss states for the new race artwork','Walk/attack states for standing-only hybrid designs','Hidden surfaces and movement poses for the new Deepguard pixel starter pieces'],catalogSha256=hashlib.sha256(CATALOG.read_bytes()).hexdigest())
    for preview in preview_records:preview['crop']=frame_crop(output/preview['path'])
    for group in matching_sets:group['crops']={body:frame_crop(output/'sets'/group['id']/(body+'.png')) for body in BASES}
    dump(output/'material-sets.json',matching_sets)
    dump(output/'generation-report.json',report);dump(output/'index.json',dict(assets=records,previews=preview_records))
    data=dict(report=report,records=records,previews=preview_records,sets=matching_sets)
    (output/'index.html').write_text((HERE/'gallery.template.html').read_text().replace('/*DATA*/null',json.dumps(data,separators=(',',':'))))
    (output/'README.md').write_text('# Generated matching equipment pack\n\nAll 354 generated gameplay equipment definitions map to source-backed shared assets. The pack exports every supported drawable design/material combination once, plus fitted item-layer and equipped previews for seven main GOA body templates and socket metadata for all registered bodies. Material-set previews combine compatible source recipes without replacing missing slots with unrelated art.\n\nThis is a deterministic source-art export, not an AI redesign of the whole catalog or proof that every fit is production-ready. Standing-only variants remain standing. Full hybrid movement, limb-loss states and clean hidden Deepguard surfaces are still pending. Original source/game files are unchanged. All canonical gear poses available in the source are exported; fitted previews show the real body movement with the neutral hold, not newly created attack animations.\n\nRun generate.py --resume to regenerate skipped/missing artifacts. Use --all-bodies to bake every reference-material design onto all registered bodies; fit metadata already covers them without those duplicate PNGs.\n')
    sample=ROOT/'Dungeon Master Sample'
    link=sample/'Generated Matching Gear.html'
    if not link.exists():link.symlink_to(__import__('os').path.relpath(output/'index.html',sample))
    archive=sample/'Generated Matching Gear.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as bundle:
        for path in output.rglob('*'):
            if path.is_file():bundle.write(path,path.relative_to(output))
    print(json.dumps(report),flush=True)
    print('Saved '+str(archive),flush=True)


if __name__=='__main__':asyncio.run(main())
