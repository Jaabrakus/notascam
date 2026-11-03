"""Publish complete worn masters without distorting individual armor pieces."""
from pathlib import Path
import base64,hashlib,json,os
from io import BytesIO
from PIL import Image,ImageDraw

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
HEIGHTS={'human':56,'dwarf':46,'elf':59,'dark-elf':59,'orc':57,'goblin':43,'kobold':45}
KINDS={'human':['leather'],'dwarf':['gold','adamantium','leather'],'elf':['diamond','leather','wood'],'dark-elf':['leather','silver','spidersilk'],'goblin':['bonehide','chitin','leather'],'kobold':['dragon','dragonhide','leather'],'orc':['bone','dragonbone','hell','leather']}


def url(image):
    b=BytesIO();image.save(b,format='PNG');return 'data:image/png;base64,'+base64.b64encode(b.getvalue()).decode()


def columns(image):
    alpha=image.getchannel('A');busy=[]
    for x in range(image.width):
        if sum(v>=128 for v in alpha.crop((x,0,x+1,image.height)).getdata())>=4:busy.append(x)
    groups=[]
    for x in busy:
        if not groups or x-groups[-1][-1]>5:groups.append([x])
        else:groups[-1].append(x)
    groups=[g for g in groups if len(g)>image.width*.03]
    if len(groups)!=4:raise ValueError('Master must have four isolated complete figures, got '+str([(g[0],g[-1]) for g in groups]))
    return [0]+[(a[-1]+1+b[0])//2 for a,b in zip(groups,groups[1:])]+[image.width]


def main():
    candidates=[dict(id='deepguard-iron',race='human',label='Deepguard Iron — approved reference',source='../deepguard-iron/pixel-fit-v2/deepguard-pixel-v2.png',status='approved reference'),dict(id='deepguard-iron-armed',race='human',label='Deepguard Iron — sword and shield',source='deepguard-iron-armed.png',status='new worn master'),dict(id='deepguard-iron-spear-shield-idle',race='human',label='Deepguard Iron — spear and shield idle',source='deepguard-iron-spear-shield-idle-v2.png',status='revised side grips and shield',frameSize=128,pose='idle',holdingHand='right',offhand='shield'),dict(id='deepguard-iron-staff-idle',race='human',label='Deepguard Iron — staff idle',source='deepguard-iron-staff-idle-v2.png',status='revised right-hand side grips',frameSize=128,pose='idle',holdingHand='right',offhand='empty')]
    for race,kinds in KINDS.items():
        for kind in kinds:candidates.append(dict(id=race+'-'+kind,race=race,label=race.replace('-',' ').title()+' '+kind.title(),source=race+'-'+kind+'.png',status='new worn master'))
    records=[]
    for spec in candidates:
        path=HERE/spec['source']
        if not path.exists():continue
        im=Image.open(path).convert('RGBA');cuts=columns(im);boxes=[];feet=[]
        alpha=im.getchannel('A').point(lambda a:255 if a>=128 else 0)
        for v in range(4):
            box=alpha.crop((cuts[v],0,cuts[v+1],im.height)).getbbox()
            if not box:raise ValueError('Empty view '+spec['id'])
            b=[box[0]+cuts[v],box[1],box[2]+cuts[v],box[3]];boxes.append(b)
            fy=round(b[3]-(b[3]-b[1])*.14);fb=alpha.crop((b[0],fy,b[2],b[3])).getbbox()
            feet.append(((b[0]+fb[0]+b[0]+fb[2])/2,b[3]))
        half_span=max(max(cx-b[0],b[2]-cx) for b,(cx,_) in zip(boxes,feet))
        size=spec.get('frameSize',64);padding=(size-64)//2
        if size==128:
            core_heights=[]
            for b,(cx,bottom) in zip(boxes,feet):
                spread=max(8,round((b[3]-b[1])*.075));probe=alpha.crop((max(b[0],round(cx)-spread),b[1],min(b[2],round(cx)+spread),b[3])).getbbox()
                core_heights.append(bottom-(b[1]+probe[1]))
            scale=HEIGHTS[spec['race']]/max(core_heights)
        else:scale=min(HEIGHTS[spec['race']]/max(b[3]-b[1] for b in boxes),29/half_span)
        atlas=Image.new('RGBA',(size*4,size));frames=[]
        for v,(b,(cx,bottom)) in enumerate(zip(boxes,feet)):
            isolated=Image.new('RGBA',im.size)
            isolated.paste(im.crop((cuts[v],0,cuts[v+1],im.height)),(cuts[v],0))
            tile=isolated.transform((size,size),Image.Transform.AFFINE,(1/scale,0,cx-(32+padding)/scale,0,1/scale,bottom-(61+padding)/scale),resample=Image.Resampling.NEAREST)
            atlas.alpha_composite(tile,(v*size,0));bounds=tile.getchannel('A').point(lambda a:255 if a>=128 else 0).getbbox()
            assert bounds and bounds[0]>0 and bounds[1]>0 and bounds[2]<size and bounds[3]<size,(spec['id'],v,bounds)
            frames.append(dict(direction=['South','North','East','West'][v],sourceBounds=b,sourceFeet=[cx,bottom],rect=[v*size,0,size,size],bodyOrigin=[padding,padding],feet=[32+padding,61+padding]))
        folder=HERE/('sprites'+str(size));folder.mkdir(exist_ok=True);atlas.save(folder/(spec['id']+'.png'))
        record=dict(spec,frameSize=size,bodySpace=64,spriteFile=str((folder/(spec['id']+'.png')).relative_to(HERE)),sourceSize=list(im.size),sourceSha256=hashlib.sha256(path.read_bytes()).hexdigest(),scale=scale,frames=frames,artwork='data:image/png;base64,'+base64.b64encode(path.read_bytes()).decode(),sprite=url(atlas),limits='Complete standing character master; reusable overlays, motion and 16-direction views are not yet derived.')
        records.append(record)
    metadata=[{k:v for k,v in r.items() if k not in ['artwork','sprite']} for r in records]
    (HERE/'masters.json').write_text(json.dumps(dict(masters=metadata),indent=2))
    data=dict(masters=records,default='deepguard-iron-spear-shield-idle' if any(r['id']=='deepguard-iron-spear-shield-idle' for r in records) else 'deepguard-iron-armed')
    html=(HERE/'gallery.template.html').read_text().replace('__ASSET_ROOT__',json.dumps(HERE.as_uri()+'/')).replace('/*DATA*/null',json.dumps(data,separators=(',',':')))
    (HERE/'index.html').write_text(html)
    prompts=sorted(HERE.glob('*-PROMPT.md'));(HERE/'PROMPTS.md').write_text('# Worn master prompts\n\nBuilt-in imagegen; source artwork and new masters are preserved.\n\n'+'\n\n'.join('## '+p.name+'\n\n'+p.read_text() for p in prompts))
    sample=ROOT/'Dungeon Master Sample'
    old=ROOT/'standalone/goa-races/armor-designs/racial-redraws-v1/worn.html'
    archive=sample/'Experimental Gear Fitting.html'
    if not archive.exists():archive.symlink_to(os.path.relpath(old,sample))
    for name in ['Generated Matching Gear.html','New Armor Worn on Races.html','Worn Armor Masters.html']:
        dest=sample/name
        if dest.is_symlink():
            if dest.resolve() not in [old,HERE/'index.html']:continue
            dest.unlink()
        if not dest.exists():dest.symlink_to(os.path.relpath(HERE/'index.html',sample))
    (HERE/'verification.json').write_text(json.dumps(dict(masters=len(records),directions=4,sourceArtPreserved=True,method='Each complete character uses one uniform scale, with feet registered at (32,61). Individual armor pieces are not rescaled.',overlaysDerived=False,facings16Complete=False),indent=2))
    print(json.dumps(dict(masters=len(records),gallery=str(sample/'Worn Armor Masters.html'))))


if __name__=='__main__':main()
