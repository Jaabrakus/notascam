"""Publish the Deepguard layered fitter for all available male/female bodies."""
from pathlib import Path
import base64,hashlib,importlib.util,json,math,shutil
from functools import lru_cache
from PIL import Image,ImageDraw
from registry import read_bodies,normalize
from rig import fit_profile,measure,attachment,transform,LABELS
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
DEST=ROOT/'Dungeon Master Sample/Deepguard Armor Framework'
OLD=HERE.parent/'layered-deepguard-v1'
spec=importlib.util.spec_from_file_location('prototype',OLD/'build.py')
prototype=importlib.util.module_from_spec(spec);spec.loader.exec_module(prototype)
SLOTS=prototype.SLOTS
ORDER=['boots','greaves','waist','chest','belt','shoulders','bracers','helmet']
NUDGE=[dict(x=0,y=0),dict(x=0,y=0),dict(x=0,y=-2),dict(x=0,y=-2)]
SOURCES={part:Image.open(prototype.PARTS.parent/'full-resolution'/(part+'.png')).convert('RGBA') for part in sum(SLOTS.values(),[])}


@lru_cache(maxsize=80)
def template_parts(encoded):
    profile=json.loads(encoded)
    return {(v,part):prototype.warp(source,part,v,profile) for v in range(4) for part,source in SOURCES.items()}


def png_url(path):
    return 'data:image/png;base64,'+base64.b64encode(path.read_bytes()).decode()


def compose(base,layers,masks,frame,view,offset):
    tile=base.crop((64*view,64*frame,64*view+64,64*frame+64))
    for mask in masks.values():
        tile.paste((0,0,0,0),(0,0,64,64),mask.crop((64*view,64*frame,64*view+64,64*frame+64)).getchannel('A'))
    for slot in ORDER:
        layer=layers[slot].crop((64*view,64*frame,64*view+64,64*frame+64))
        translated=Image.new('RGBA',(64,64));translated.paste(layer,(offset['x'],offset['y']))
        tile.alpha_composite(translated)
    return tile


def main():
    DEST.mkdir(parents=True,exist_ok=True);(DEST/'bodies').mkdir(exist_ok=True)
    bodies=read_bodies();profiles=[];images={};thumbs={};source_hashes={};clip_flags=[]
    for index,body in enumerate(bodies):
        key=body['id'];folder=DEST/'bodies'/key;folder.mkdir(parents=True,exist_ok=True)
        base=normalize(body);base.save(folder/'Base_Body.png')
        p=fit_profile(body,prototype.PROFILES);parts=template_parts(json.dumps(p,sort_keys=True))
        layers={slot:Image.new('RGBA',base.size) for slot in SLOTS}
        masks={'boots':Image.new('RGBA',base.size)}
        rigs=[];part_anchors=[];clipped=[];posed_features=[]
        for f in range(body['frames']):
            rigs.append([measure(base.crop((64*v,64*f,64*v+64,64*f+64)),p,v,f) for v in range(4)])
        for f in range(body['frames']):
            anchors=[]
            for v in range(4):
                current=rigs[f][v];reference=rigs[0][v];commands=[]
                for slot,partnames in SLOTS.items():
                    fitted=Image.new('RGBA',(64,64))
                    for part in partnames:
                        source=parts[(v,part)]
                        dx,dy,angle,pivot=attachment(part,reference,current)
                        posed=transform(source,dx,dy,angle,pivot)
                        fitted.alpha_composite(posed)
                        commands.append(dict(part=part,translation=[round(dx,2),round(dy,2)],rotation=round(angle,2),pivot=pivot))
                    b=fitted.getchannel('A').point(lambda a:255 if a>=128 else 0).getbbox()
                    if b and (b[0]==0 or b[1]==0 or b[2]==64 or b[3]==64):
                        clipped.append(dict(slot=slot,frame=f,direction=prototype.DIRECTIONS[v]))
                    # A one-pixel transparent gutter is reserved for safe export.
                    fitted.paste((0,0,0,0),(0,0,64,1));fitted.paste((0,0,0,0),(0,63,64,64))
                    fitted.paste((0,0,0,0),(0,0,1,64));fitted.paste((0,0,0,0),(63,0,64,64))
                    layers[slot].paste(fitted,(v*64,f*64))
                mask=Image.new('RGBA',(64,64));draw=ImageDraw.Draw(mask)
                for foot in current['feet'].values():
                    x,y=foot;draw.rectangle((max(1,round(x)-7),max(1,round(y)-6),min(62,round(x)+7),62),fill=(255,255,255,255))
                masks['boots'].paste(mask,(v*64,f*64))
                anchors.append(commands)
            part_anchors.append(anchors)
        composed=Image.new('RGBA',base.size)
        for f in range(body['frames']):
            for v in range(4):
                tile=compose(base,layers,masks,f,v,NUDGE[v])
                composed.paste(tile,(v*64,f*64))
                if f==0:tile.save(folder/('Deepguard_'+key+'_'+prototype.DIRECTIONS[v]+'_64px.png'))
        composed.save(folder/'Deepguard_Equipped_Atlas.png')
        for slot,atlas in layers.items():atlas.save(folder/(slot+'.png'))
        for slot,atlas in masks.items():atlas.save(folder/(slot+'-coverage.png'))
        files=dict(base='bodies/'+key+'/Base_Body.png',
            layers={slot:'bodies/'+key+'/'+slot+'.png' for slot in SLOTS},
            coverage={slot:'bodies/'+key+'/'+slot+'-coverage.png' for slot in masks})
        for path in [files['base'],*files['layers'].values(),*files['coverage'].values()]:images[path]=png_url(DEST/path)
        thumb=Image.new('RGBA',(128,64));thumb.paste(composed.crop((0,0,64,64)),(0,0));thumb.paste(composed.crop((128,0,192,64)),(64,0));thumb.save(folder/'Preview_Front_and_East.png')
        thumbs[key]=png_url(folder/'Preview_Front_and_East.png')
        source_path=Path(body['source']);relative=str(source_path.relative_to(ROOT)) if source_path.is_relative_to(ROOT) else str(source_path)
        digest=hashlib.sha256(source_path.read_bytes()).hexdigest();source_hashes[relative]=digest
        motion=body['motion'];sequence=body['animation']['sequence'] if body['frames']>1 else [0]
        if body['frames']>1:
            gif=[]
            for f in sequence:
                strip=composed.crop((0,f*64,256,f*64+64)).resize((768,192),Image.Resampling.NEAREST)
                bg=Image.new('RGB',strip.size,(24,29,35));bg.paste(strip,(0,0),strip);gif.append(bg)
            gif[0].save(folder/'Motion_Preview.gif',save_all=True,append_images=gif[1:],duration=200,loop=0)
        label=LABELS.get(body['race'],body['race'].title())+' · '+body['sex'].title()
        if body['appearance'].lower()!='base':label+=' · '+body['appearance']
        if '-flying' in body['baseId']:label+=' · Flight form'
        record=dict(id=key,label=label,race=body['race'],sex=body['sex'],appearance=body['appearance'],
            family=p['family'],fitParent=body['baseId'],frames=body['frames'],motion=motion,sequence=sequence,
            delaysMs=body['animation'].get('delaysMs',[200]*len(sequence)),frameSize=64,directionOrder=prototype.DIRECTIONS,
            layerOrder=ORDER,fitDefaults=NUDGE,**files,
            equipped='bodies/'+key+'/Deepguard_Equipped_Atlas.png',
            source=relative,sourceSha256=digest,rigs=rigs,attachments=part_anchors,
            review=dict(status='draft fit',frameEdgeExceptions=clipped,
                notes=['Existing body frames only. Armor attachments follow measured pose features; complex anatomy and motion need art review.']))
        (folder/'manifest.json').write_text(json.dumps(record,indent=2))
        profiles.append(record)
        clip_flags.extend(dict(body=key,**flag) for flag in clipped)
        if (index+1)%20==0:print('Built',index+1,'of',len(bodies),flush=True)
    summary=dict(bodies=len(profiles),male=sum(p['sex']=='male' for p in profiles),female=sum(p['sex']=='female' for p in profiles),
        raceForms=len({p['fitParent'] for p in profiles if p['sex']=='male'}),races=len({p['race'] for p in profiles}),
        walking=sum(p['motion']=='walk' for p in profiles),flight=sum(p['motion']=='flight' for p in profiles),
        standingOnly=sum(p['frames']==1 for p in profiles),equipmentSlots=len(SLOTS),directions=4,
        equippedFrames=sum(p['frames']*4 for p in profiles))
    source_parts={part:hashlib.sha256((prototype.PARTS.parent/'full-resolution'/(part+'.png')).read_bytes()).hexdigest() for part in SOURCES}
    manifest=dict(version=2,armor='deepguard-iron',summary=summary,directionOrder=prototype.DIRECTIONS,
        slots=list(SLOTS),profiles=profiles,sourceHashes=source_hashes,equipmentSourceHashes=source_parts,
        clippingExceptions=clip_flags,frameSize=64,
        limits='Fitting drafts for existing source bodies. Female bodies exist for ten races. No new missing motion, attacks, injury variants or sixteen facings are invented.')
    (DEST/'manifest.json').write_text(json.dumps(manifest,indent=2))
    # Contact pages keep the complete registry reviewable without hundreds of browser canvases.
    for group,entries in [('Base_Male',[p for p in profiles if p['sex']=='male' and p['appearance'].lower()=='base']),
        ('Base_Female',[p for p in profiles if p['sex']=='female' and p['appearance'].lower()=='base'])]:
        contact=Image.new('RGB',(1152,math.ceil(len(entries)/4)*160),(25,29,35));draw=ImageDraw.Draw(contact)
        for i,pf in enumerate(entries):
            x=(i%4)*288;y=(i//4)*160
            pic=Image.open(DEST/'bodies'/pf['id']/'Preview_Front_and_East.png').resize((256,128),Image.Resampling.NEAREST)
            contact.paste(pic,(x+8,y+25),pic);draw.text((x+8,y+5),pf['label'][:40],fill='white')
        contact.save(DEST/(group+'_Contact.png'))
    embedded=dict(manifest,images=images,thumbs=thumbs,reference=png_url(prototype.PARTS.parent/'reassembled-64px.png'))
    (DEST/'index.html').write_text((HERE/'viewer.template.html').read_text().replace('/*DATA*/null',json.dumps(embedded,separators=(',',':'))))
    (DEST/'README.md').write_text('# Deepguard armor framework\n\n'+json.dumps(summary,indent=2)+'\n\nEvery body has named source, independent armor layers, coverage masks, equipped atlas, four standing direction PNGs, pose attachments and a manifest. Existing motion has an animated preview. The viewer supports filtering, whole-outfit and per-piece offsets for every supplied frame, PNG/recipe export and source/equipped comparisons. East and West default to Y=-2, as requested.\n\nFits are drafts for review. Shared profiles follow anatomy rather than sex or crafting origin; per-body/per-frame exceptions can be saved. Motion uses supplied body frames and separate head, torso, hand and foot attachments. Missing motion is not synthesized. Female sources currently cover ten races. New attack art, injury-aware gear, hidden surfaces and sixteen facings remain pending.\n\nRegistry snapshots and source hashes record the exact inputs. The source registries and artwork are unchanged.\n')
    legacy=ROOT/'Dungeon Master Sample/Layered Deepguard Fitting'
    if (legacy/'index.html').exists() and not (legacy/'Three Body Prototype.html').exists():shutil.copyfile(legacy/'index.html',legacy/'Three Body Prototype.html')
    legacy.mkdir(exist_ok=True)
    (legacy/'index.html').write_text('<!doctype html><meta charset="utf-8"><meta http-equiv="refresh" content="0;url=../Deepguard%20Armor%20Framework/index.html"><title>Deepguard Armor Framework</title><a href="../Deepguard%20Armor%20Framework/index.html">Open the complete armor framework</a>')
    print(json.dumps(dict(folder=str(DEST),summary=summary,edgeExceptions=len(clip_flags))),flush=True)


if __name__=='__main__':main()

