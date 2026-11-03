"""Read existing body registries without mutating their source assets."""
from pathlib import Path
import hashlib,json
from functools import lru_cache
from PIL import Image
HERE=Path(__file__).resolve().parent
RACES=HERE.parent
RACE_MAP={'Human':'human','HumanBlack':'human-dark','Dwarves':'dwarf','Elf':'elf','Night Elf':'dark-elf','Orc':'orc','Goblins':'goblin','Kobold':'kobold','Vampire':'vampire','VampireFly':'vampire-flying','Demon':'demon','DemonFly':'demon-flying','Gargoyle':'gargoyle','GargoyleFly':'gargoyle-flying','FrogMan':'frogman','LizardMan':'lizardman','DevourerZombie':'devourer-zombie','Skeleton':'skeleton'}
HEIGHTS={'human':56,'human-dark':56,'dwarf':46,'elf':59,'dark-elf':59,'orc':57,'goblin':43,'kobold':45,'frogman':52,'lizardman':56}


@lru_cache(maxsize=200)
def source_image(path):
    return Image.open(path).convert('RGBA')


def read_bodies():
    male=json.loads((HERE/'body-registry-snapshot.json').read_text())['bodies']
    result=[]
    for body in male:
        body=dict(body,sex='male',appearance=body['variant'],race=body['baseId'].replace('-flying',''))
        body['motion']=body['animation']['kind']
        body['frames']=len(body['sourceRects'])
        result.append(body)
    for entry in json.loads((HERE/'female-registry-snapshot.json').read_text())['entries']:
        base=RACE_MAP[entry['race']];path=RACES/entry['walk']['image']
        meta=json.loads((RACES/entry['walk']['metadata']).read_text())
        im=source_image(str(path));n=meta['frames'];rects=[];bounds=[]
        assert im.size==(256,64*n),(entry['id'],im.size)
        for f in range(n):
            rr=[];bb=[]
            for v in range(4):
                rect=[64*v,64*f,64,64];rr.append(rect)
                box=im.crop((64*v,64*f,64*v+64,64*f+64)).getchannel('A').point(lambda a:255 if a>=128 else 0).getbbox()
                assert box,(entry['id'],f,v)
                bb.append(list(box))
            rects.append(rr);bounds.append(bb)
        appearance=entry['appearance']
        result.append(dict(id=base+'-female'+('' if appearance.lower()=='base' else '-'+appearance.lower()),
            baseId=base+'-female',race=base,raceKey=entry['race'],sex='female',appearance=appearance,
            variant=appearance,label=base.replace('-',' ').title()+' · Female'+('' if appearance.lower()=='base' else ' · '+appearance),
            status='walk',motion='walk',frames=n,source=str(path),sourceSha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            sourceRects=rects,frameBounds=bounds,targetHeight=HEIGHTS[base],
            animation=dict(kind='walk',sequence=meta['sequence'],delaysMs=[meta['frameDurationMs']]*len(meta['sequence']))))
    assert len({b['id'] for b in result})==len(result)
    return result


def normalize(body):
    im=source_image(body['source'])
    # Keep one scale for the entire animation so the body never grows per step.
    maximum=max(box[3]-box[1] for frame in body['frameBounds'] for box in frame)
    scale=body['targetHeight']/maximum
    # Wide wings and special silhouettes stay within the existing 64px body space.
    widest=max(box[2]-box[0] for frame in body['frameBounds'] for box in frame)
    scale=min(scale,60/widest)
    atlas=Image.new('RGBA',(256,64*body['frames']))
    for f,frame in enumerate(body['sourceRects']):
        for v,(rect,box) in enumerate(zip(frame,body['frameBounds'][f])):
            x,y,w,h=rect
            source_cell=im.crop((x,y,x+w,y+h));cx=(box[0]+box[2])/2
            cell=Image.new('RGBA',(w,h));cell.paste(source_cell.crop(tuple(box)),(box[0],box[1]))
            tile=cell.transform((64,64),Image.Transform.AFFINE,(1/scale,0,cx-32/scale,0,1/scale,box[3]-61/scale),resample=Image.Resampling.NEAREST)
            atlas.paste(tile,(64*v,64*f))
    return atlas

