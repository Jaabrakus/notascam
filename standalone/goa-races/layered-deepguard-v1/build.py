"""Build shared Deepguard standing layers for three anatomical fit profiles."""
from pathlib import Path
from PIL import Image, ImageDraw
import base64, hashlib, json, shutil
import importlib.util
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PARTS = HERE.parent/'armor-designs/deepguard-iron/pixel-fit-v2/pieces/64px'
SOURCE_MANIFEST=json.loads((PARTS.parent/'manifest.json').read_text())
DEST = ROOT/'Dungeon Master Sample/Layered Deepguard Fitting'
DIRECTIONS = ['South','North','East','West']
SLOTS = {'helmet':['helmet'],'chest':['chest'],'shoulders':['shoulder-left','shoulder-right'],
    'bracers':['bracer-left','bracer-right'],'belt':['belt'],'waist':['waist-mail-cloth'],
    'greaves':['greave-left','greave-right'],'boots':['boot-left','boot-right']}
PROFILES = {
 'human':dict(label='Human · standard build',body='Human',family='standard',
    y=[5,29,42,44,52,56,61],headY=[[5,27],[5,28],[4,26],[4,26]],headWidth=1.04,torsoWidth=1,lowerWidth=1,armWidth=1,armY=[29,40,44],armSpread=0),
 'dwarf':dict(label='Dwarf · stocky build',body='Dwarves',family='stocky',
    y=[14,35,44,46,54,57,61],headY=[[14,32],[14,34],[14,32],[14,32]],headWidth=1.0,torsoWidth=1.12,lowerWidth=1,armWidth=1.05,armY=[35,44,47],armSpread=1),
 'goblin':dict(label='Goblin · small build',body='Goblins',family='small',
    y=[17,38,46,48,54,57,61],headY=[[17,33],[17,36],[17,33],[17,33]],headWidth=.85,torsoWidth=.82,lowerWidth=.80,armWidth=.80,armY=[38,45,49],armSpread=0),
}
SOURCE_Y=[5,28,39,42,50,55,61]


def normalize_bodies():
    spec=importlib.util.spec_from_file_location('master_build',HERE.parent/'armor-designs/worn-masters-v1/build.py')
    helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    for name,height in [('Human',56),('Dwarves',46),('Goblins',43)]:
        im=Image.open(HERE.parent/'hybrids/references'/(name+'-approved.png')).convert('RGBA')
        cuts=helper.columns(im);boxes=[];atlas=Image.new('RGBA',(256,64))
        for v in range(4):
            a,b=cuts[v:v+2]
            box=im.getchannel('A').crop((a,0,b,im.height)).point(lambda a:255 if a>=128 else 0).getbbox()
            boxes.append((a+box[0],box[1],a+box[2],box[3]))
        scale=height/max(b[3]-b[1] for b in boxes)
        for v,b in enumerate(boxes):
            isolated=Image.new('RGBA',im.size)
            isolated.paste(im.crop((cuts[v],0,cuts[v+1],im.height)),(cuts[v],0))
            cx=(b[0]+b[2])/2
            tile=isolated.transform((64,64),Image.Transform.AFFINE,(1/scale,0,cx-32/scale,0,1/scale,b[3]-61/scale),resample=Image.Resampling.NEAREST)
            atlas.paste(tile,(v*64,0))
        atlas.save(HERE/(name+'-base.png'))


def interpolate(value, old, new):
    index=next((i for i in range(len(old)-1) if value < old[i+1]),len(old)-2)
    return new[index]+(value-old[index])*(new[index+1]-new[index])/(old[index+1]-old[index])


def warp(tile, part, view, profile):
    # Map every existing pixel through the same anatomical anchors within a slot.
    # Outlines and material shading come from the approved source, not repainted shapes.
    if part=='helmet':
        ys=[5,28]; yd=profile['headY'][view]; sx=profile['headWidth']; shift=0
    elif part.startswith(('shoulder','bracer')):
        ys=[28,37,41]; yd=profile['armY']; sx=profile['armWidth']
        side='left' if part.endswith('left') else 'right'
        screen=-1 if (side=='right')==(view==0) else 1
        if view>=2:screen=-1 if view==2 else 1
        shift=screen*profile['armSpread']
    else:
        ys=SOURCE_Y; yd=profile['y']; sx=profile['lowerWidth'] if part.startswith(('boot','greave')) else profile['torsoWidth'];shift=0
    result=Image.new('RGBA',(64,64)); src=tile.load(); dst=result.load()
    bounds=SOURCE_MANIFEST['sourceBodyBounds'][view]
    source_center=(bounds[0]+bounds[2])/2
    source_scale=SOURCE_MANIFEST['sourceScale']
    for y in range(64):
        sy=interpolate(y+.5,yd,ys)
        iy=int(bounds[3]+(sy-61)/source_scale)
        for x in range(64):
            source_x=32+(x+.5-32-shift)/sx
            ix=int(source_center+(source_x-32)/source_scale)
            if bounds[0]<=ix<bounds[2] and bounds[1]<=iy<bounds[3]:
                color=src[ix,iy]
                # Extracted pieces can retain pale source-body edge pixels.
                # Exclude those from equipment so the wearer's own skin shows.
                r,g,b,a=color
                if r>225 and g>155 and b>110 and r>g>b:continue
                dst[x,y]=color
    return result


def dataurl(path):
    return 'data:image/png;base64,'+base64.b64encode(path.read_bytes()).decode()


def main():
    normalize_bodies()
    DEST.mkdir(exist_ok=True,parents=True)
    preview=Image.new('RGB',(1024,3*300),(25,27,31));draw=ImageDraw.Draw(preview)
    metadata=dict(version=2,frameSize=64,directionOrder=DIRECTIONS,slots=SLOTS,profiles=[],sourceHashes={},fullSourceHashes={},
        fitMethod='Full-resolution source pieces sampled once to each anatomical profile; independent helmet/arm/torso/leg fitting and slot-dependent boot coverage.',
        limits='Standing four-direction fitting prototype. Female-specific fits, hybrid anatomy exceptions, walking, attacks and sixteen directions are not authored here.')
    for part in sum(SLOTS.values(),[]):
        metadata['sourceHashes'][part]=hashlib.sha256((PARTS/(part+'.png')).read_bytes()).hexdigest()
        metadata['fullSourceHashes'][part]=hashlib.sha256((PARTS.parent/'full-resolution'/(part+'.png')).read_bytes()).hexdigest()
    for row,(key,p) in enumerate(PROFILES.items()):
        folder=DEST/key;folder.mkdir(exist_ok=True)
        base=Image.open(HERE/(p['body']+'-base.png')).convert('RGBA')
        base.save(folder/'base.png');layers={}
        boot_mask=Image.new('RGBA',(256,64))
        for v in range(4):
            mask=Image.new('RGBA',(64,64));ImageDraw.Draw(mask).rectangle((0,p['y'][5],63,63),fill=(255,255,255,255))
            boot_mask.paste(mask,(v*64,0))
        boot_mask.save(folder/'boots-coverage.png')
        for slot,parts in SLOTS.items():
            layer=Image.new('RGBA',(256,64))
            for v in range(4):
                fitted=Image.new('RGBA',(64,64))
                for part in parts:
                    source=Image.open(PARTS.parent/'full-resolution'/(part+'.png')).convert('RGBA')
                    fitted.alpha_composite(warp(source,part,v,p))
                layer.paste(fitted,(v*64,0))
            layer.save(folder/(slot+'.png'));layers[slot]=key+'/'+slot+'.png'
        composed=base.copy()
        composed.paste((0,0,0,0),(0,0,256,64),boot_mask.getchannel('A'))
        # Torso first; arms in front; helmet last, leaving base ears untouched outside it.
        order=['boots','greaves','waist','chest','belt','shoulders','bracers','helmet']
        for slot in order:composed.alpha_composite(Image.open(folder/(slot+'.png')))
        composed.save(folder/'equipped.png')
        for v,direction in enumerate(DIRECTIONS):
            composed.crop((v*64,0,v*64+64,64)).save(folder/('Deepguard_'+key+'_'+direction+'_64px.png'))
        large=composed.resize((1024,256),Image.Resampling.NEAREST)
        preview.paste(large,(0,row*300+28),large)
        draw.text((14,row*300+8),p['label'],fill='white')
        metadata['profiles'].append(dict(id=key,**p,base=key+'/base.png',layers=layers,
            layerOrder=order,equipped=key+'/equipped.png',
            coverage={'boots':key+'/boots-coverage.png'},
            baseSource='standalone/goa-races/hybrids/references/'+p['body']+'-approved.png'))
    preview.save(DEST/'Fitting_Preview_4x.png')
    (DEST/'manifest.json').write_text(json.dumps(metadata,indent=2))
    (DEST/'README.md').write_text('# Layered Deepguard fitting prototype\n\nOne approved Deepguard design, fitted onto three existing body shapes: human/standard, dwarf/stocky and goblin/small. The same twelve extracted pieces are grouped into eight independently switchable equipment slots. No new armor design is generated per race.\n\nEach profile contains a transparent 256×64 base sheet, eight matching equipment sheets and a composed sheet plus four individual 64×64 equipped frames. Source pixels use nearest-neighbor anatomical fitting; source artwork is preserved. Body ears stay visible outside the helmet. The viewer allows slot toggling and per-facing pixel offsets; adjusted sheets and recipes can be exported.\n\nThe fit belongs to body shape, not crafting origin or sex. A hybrid or female body can reuse a profile when its anatomy matches; different proportions and horns/wings require a reviewed exception. Those variants are not demonstrated or validated here.\n\nStanding South, North, East and West only. Hidden equipment surfaces, walking, holding poses, attacks and sixteen facings still require authored work. This does not establish universal fit for every body.\n\nRebuild with: python3 standalone/goa-races/layered-deepguard-v1/build.py\n')
    embedded=dict(metadata)
    embedded['reference']=dataurl(PARTS.parent/'reassembled-64px.png')
    embedded['images']={}
    for p in metadata['profiles']:
        for path in [p['base'],*p['layers'].values(),*p['coverage'].values()]:embedded['images'][path]=dataurl(DEST/path)
    template=HERE/'viewer.template.html'
    if template.exists():(DEST/'index.html').write_text(template.read_text().replace('/*DATA*/null',json.dumps(embedded)))
    print(json.dumps(dict(folder=str(DEST),profiles=3,slots=8,directions=4)))


if __name__=='__main__':main()

