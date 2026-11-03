"""Six fixed body masters with unchanged original race/hybrid heads."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageChops
import base64,hashlib,importlib.util,json,math,shutil
from heads import extract,tint
import exact_templates
import hybrid_details
import previews
from functools import lru_cache
from copy import deepcopy
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
DEST=ROOT/'Dungeon Master Sample/Shared Body Rigs'
DONORS=ROOT/'Dungeon Master Sample/Deepguard Armor Framework'
DIRECTIONS=['South','North','East','West']
HEIGHTS={'standard-male':35,'standard-female':36,'stocky-male':34,'stocky-female':34,'small-male':24,'small-female':25}
BASE_HEIGHTS={'standard':59,'stocky':57,'small':43}
GROUPS={'dwarf':'stocky','orc':'stocky','demon':'stocky','gargoyle':'stocky','frogman':'stocky','devourer-zombie':'stocky','goblin':'small','kobold':'small'}
SPECIES_HEIGHT={'human':56,'human-dark':56,'dwarf':46,'elf':59,'dark-elf':59,'orc':57,'goblin':43,'kobold':45,'vampire':56,'demon':57,'gargoyle':57,'frogman':52,'lizardman':56,'devourer-zombie':56,'skeleton':56}


@lru_cache(maxsize=1)
def changed_donors():
    # Some source sheets were updated by other art work after the armory registry.
    # Re-measure their actual gutters rather than preserving stale/clipped cells.
    import sys
    sys.path.insert(0,str(HERE.parent/'deepguard-framework-v2'))
    import registry as body_registry
    import rig as fit_rig
    spec=importlib.util.spec_from_file_location('source_grid',HERE.parent/'armory/body_registry.py')
    grid_module=importlib.util.module_from_spec(spec);spec.loader.exec_module(grid_module)
    old_spec=importlib.util.spec_from_file_location('old_fit',HERE.parent/'layered-deepguard-v1/build.py')
    old_fit=importlib.util.module_from_spec(old_spec);old_spec.loader.exec_module(old_fit)
    result={}
    for body in body_registry.read_bodies():
        if body['sex']!='male':continue
        path=Path(body['source']);digest=hashlib.sha256(path.read_bytes()).hexdigest()
        if digest==body['sourceSha256']:continue
        directory=HERE/'preserved-updated-sources';directory.mkdir(exist_ok=True)
        saved=directory/(digest[:12]+'.png')
        if not saved.exists():shutil.copyfile(path,saved)
        source=Image.open(saved).convert('RGBA');grid,_=grid_module.measured_grid(str(saved),body['layout']['columns'],body['layout']['rows'])
        body=deepcopy(body);body['source']=str(saved);body['sourceRects']=grid[body['layout']['row']:body['layout']['row']+body['frames']]
        body['frameBounds']=[]
        for row in body['sourceRects']:
            bounds=[]
            for x,y,w,h in row:
                bounds.append(list(source.crop((x,y,x+w,y+h)).getchannel('A').point(lambda a:255 if a>=128 else 0).getbbox()))
            body['frameBounds'].append(bounds)
        atlas=body_registry.normalize(body);profile=fit_rig.fit_profile(body,old_fit.PROFILES)
        rigs=[[fit_rig.measure(atlas.crop((v*64,f*64,v*64+64,f*64+64)),profile,v,f) for v in range(4)] for f in range(body['frames'])]
        result[body['id']]=(atlas,rigs,str(path),digest)
    return result


def encoded(path):
    return 'data:image/png;base64,'+base64.b64encode(path.read_bytes()).decode()


def prepare_templates():
    spec=importlib.util.spec_from_file_location('body_registry',HERE.parent/'armory/body_registry.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    records={};directory=DEST/'Body Templates';directory.mkdir(parents=True,exist_ok=True)
    for entry in json.loads((HERE/'generation-inputs.json').read_text()):
        key=entry['id'];folder=directory/key;folder.mkdir(exist_ok=True)
        original=folder/'Body_Master_Artwork.png'
        if not original.exists():shutil.copyfile(entry['source'],original)
        (folder/'Generation_Prompt.md').write_text(entry['prompt'])
        source=Image.open(original).convert('RGBA')
        grid,_=module.measured_grid(str(original),4,3)
        boxes=[]
        for row in grid:
            bb=[]
            for x,y,w,h in row:
                a=source.crop((x,y,x+w,y+h)).getchannel('A').point(lambda a:255 if a>=128 else 0).getbbox()
                assert a
                bb.append([x+a[0],y+a[1],x+a[2],y+a[3]])
            boxes.append(bb)
        scale=HEIGHTS[key]/max(b[3]-b[1] for row in boxes for b in row)
        atlas=Image.new('RGBA',(256,192));rig=[]
        for f,row in enumerate(boxes):
            joints=[]
            for v,box in enumerate(row):
                x,y,w,h=grid[f][v]
                isolated=Image.new('RGBA',source.size);isolated.paste(source.crop(tuple(box)),(box[0],box[1]))
                cx=(box[0]+box[2])/2
                tile=isolated.transform((64,64),Image.Transform.AFFINE,(1/scale,0,cx-32/scale,0,1/scale,box[3]-61/scale),resample=Image.Resampling.NEAREST)
                # Remove low-alpha extraction fringe; original artwork stays untouched.
                tile.putalpha(tile.getchannel('A').point(lambda a:255 if a>=128 else 0))
                b=tile.getchannel('A').getbbox();assert b and b[0]>0 and b[1]>0 and b[2]<64 and b[3]<64
                probe=tile.getchannel('A').crop((24,b[1],40,min(64,b[1]+4))).getbbox()
                neckx=24+(probe[0]+probe[2])/2 if probe else 32
                neck=[round(neckx),b[1]+1]
                atlas.paste(tile,(v*64,f*64))
                tile.save(folder/(DIRECTIONS[v]+'_Pose_'+str(f)+'_64px.png'))
                joints.append(dict(neck=neck,feet=[32,61],bounds=list(b)))
            rig.append(joints)
        atlas.save(folder/'Body_Core_Atlas_64px.png')
        rec=dict(id=key,build=key.rsplit('-',1)[0],sex=key.rsplit('-',1)[1],reference=entry['guide'],
            core='Body Templates/'+key+'/Body_Core_Atlas_64px.png',frames=3,frameSize=64,logicalBodySpace=64,
            directionOrder=DIRECTIONS,sequence=[0,1,0,2],rig=rig,coreAlphaSha256=hashlib.sha256(atlas.getchannel('A').tobytes()).hexdigest(),
            artworkSha256=hashlib.sha256(original.read_bytes()).hexdigest(),
            sourceArtwork='Body Templates/'+key+'/Body_Master_Artwork.png')
        (folder/'rig.json').write_text(json.dumps(rec,indent=2));records[key]=rec
    return records


def main():
    DEST.mkdir(exist_ok=True,parents=True);donors=json.loads((DONORS/'manifest.json').read_text())['profiles'];templates=exact_templates.prepare(HERE,DEST,donors)
    images={};actors=[];thumbs={};head_proofs=[]
    for t in templates.values():
        for path in [t['core'],t['neutral'],t['sourceAtlas']]:images[path]=encoded(DEST/path)
    target=DEST/'Characters';target.mkdir(exist_ok=True)
    for record in donors:
        key=record['id'];folder=target/key;folder.mkdir(exist_ok=True)
        donor_path=DONORS/record['base'];saved=folder/'Original_Donor_Atlas.png'
        record=deepcopy(record)
        own_template=next((t for t in templates.values() if t['reference']==key),None)
        replacement=changed_donors().get(key)
        if own_template:
            shutil.copyfile(DEST/own_template['sourceAtlas'],saved)
        elif replacement:
            corrected,record['rigs'],original_path,original_hash=replacement
            corrected.save(saved)
            record['sourceCropRepair']=dict(source=original_path,sha256=original_hash,method='Re-measured current source rectangles; source art unchanged.')
        elif not saved.exists():shutil.copyfile(donor_path,saved)
        donor=Image.open(saved).convert('RGBA')
        body_palette=hybrid_details.palette(donor,record)
        build=GROUPS.get(record['race'],'standard');tid=build+'-'+record['sex'];template=templates[tid]
        core=Image.open(DEST/template['core']).convert('RGBA')
        skin_mask=Image.open(DEST/template['skinMask']).convert('RGBA')
        body_atlas=Image.new('RGBA',(256,192));heads=Image.new('RGBA',(512,384));features=Image.new('RGBA',(512,384))
        whole=Image.new('RGBA',(512,384));placements=[];raw_heads=Image.new('RGBA',donor.size)
        identity_marks=Image.new('RGBA',(256,192));mark_counts=[]
        for f in range(3):
            ff=f%record['frames'];row=[]
            for v in range(4):
                source=donor.crop((v*64,ff*64,v*64+64,ff*64+64))
                head,extra,info=extract(source,record,ff,v)
                raw_heads.paste(head,(v*64,ff*64))
                bcore=core.crop((v*64,f*64,v*64+64,f*64+64))
                mask=skin_mask.crop((v*64,f*64,v*64+64,f*64+64))
                colored=bcore.copy() if key==template['reference'] else exact_templates.tint(bcore,body_palette['mid'],mask,template['sourceTones'][0][0])
                body_atlas.paste(colored,(v*64,f*64))
                marking_mask=mask.copy()
                marking_mask.putalpha(ImageChops.multiply(mask.getchannel('A'),bcore.getchannel('A').point(lambda a:255 if a>=128 else 0)))
                marks,mark_count=hybrid_details.markings(source,head,record,ff,v,template['rig'][f][v]['bodyJoints'],marking_mask,body_palette['mid'])
                identity_marks.paste(marks,(v*64,f*64));mark_counts.append(mark_count)
                neck=template['rig'][f][v]['neck'];dx=neck[0]-info['neck'][0];dy=neck[1]-info['neck'][1]
                placed_head=Image.new('RGBA',(128,128));placed_extra=Image.new('RGBA',(128,128))
                placed_head.paste(head,(32+dx,32+dy));placed_extra.paste(extra,(32+dx,32+dy))
                assert placed_head.getchannel('A').getbbox(),(key,f,v,info)
                result=placed_extra.copy();result.alpha_composite(colored,(32,32));result.alpha_composite(marks,(32,32));result.alpha_composite(placed_head)
                whole.paste(result,(v*128,f*128));heads.paste(placed_head,(v*128,f*128));features.paste(placed_extra,(v*128,f*128))
                # Exact color/alpha check: head extraction and placement never resample pixels.
                recovered=placed_head.crop((32+dx,32+dy,96+dx,96+dy))
                assert recovered.tobytes()==head.tobytes(),(key,f,v,'head changed')
                assert colored.getchannel('A').tobytes()==bcore.getchannel('A').tobytes(),(key,'body silhouette changed')
                row.append(dict(sourceFrame=ff,direction=DIRECTIONS[v],offset=[dx,dy],sourceHead=info,
                    sourceHeadPixels=sum(a>0 for a in head.getchannel('A').getdata())))
            placements.append(row)
        for image,name in [(body_atlas,'Shared_Body_64px.png'),(heads,'Original_Head_Layer_128px.png'),
            (features,'Features_Behind_Body_128px.png'),(whole,'Standardized_Character_128px.png'),
            (raw_heads,'Unmodified_Head_Pixels_64px.png'),(identity_marks,'Hybrid_Identity_Marks_64px.png')]:image.save(folder/name)
        for v,d in enumerate(DIRECTIONS):whole.crop((v*128,0,v*128+128,128)).save(folder/(d+'_Idle_128px.png'))
        rect=whole.crop((16,12,112,112));rect.save(folder/'Preview.png')
        files=dict(body='Characters/'+key+'/Shared_Body_64px.png',head='Characters/'+key+'/Original_Head_Layer_128px.png',
            features='Characters/'+key+'/Features_Behind_Body_128px.png',composite='Characters/'+key+'/Standardized_Character_128px.png',markings='Characters/'+key+'/Hybrid_Identity_Marks_64px.png')
        for path in files.values():images[path]=encoded(DEST/path)
        images['Characters/'+key+'/Original_Donor_Atlas.png']=encoded(saved)
        thumbs[key]=encoded(folder/'Preview.png')
        display_scale=SPECIES_HEIGHT[record['race']]/BASE_HEIGHTS[build]
        actor=dict(id=key,label=record['label'],race=record['race'],sex=record['sex'],appearance=record['appearance'],
            template=tid,build=build,displayScale=round(display_scale,5),frames=3,sequence=[0,1,0,2],directionOrder=DIRECTIONS,
            frameSize=128,bodySpace=64,bodyOrigin=[32,32],feet=[64,93],**files,placements=placements,
            donor='Characters/'+key+'/Original_Donor_Atlas.png',donorSha256=hashlib.sha256(saved.read_bytes()).hexdigest(),
            headMethod='Exact extracted RGBA pixels, integer translation only. Head size, color and features are unchanged.',
            bodyPalette=body_palette,hybridDetails=dict(appearance=record['appearance'],markPixels=sum(mark_counts),method='Original donor identity markings attached by body segment and clipped to the fixed skin mask.'),
            status='Standardized body / original-head assembly draft')
        (folder/'manifest.json').write_text(json.dumps(actor,indent=2));actors.append(actor)
        head_proofs.append(dict(id=key,frames=12,headPixelsUnchanged=True,bodyAlphaMatchesTemplate=True))
    summary=dict(templates=len(templates),builds=3,characters=len(actors),female=sum(a['sex']=='female' for a in actors),
        headAttachmentsChecked=len(actors)*12,bodyPoses=72,displayPresets=['Standard','Small','Large stocky','Small stocky'],
        originalHeadsRedrawn=0,equipmentRefitted=False,templateSource='Original approved sprite pixels; exact male/female Elf and Orc references provided by user',polishVersion=2,hybridAppearances=sum(a['appearance'].lower()!='base' for a in actors),bodiesWithIdentityMarks=sum(a['hybridDetails']['markPixels']>0 for a in actors))
    manifest=dict(version=1,summary=summary,templates=list(templates.values()),actors=actors,
        directions=DIRECTIONS,sequence=[0,1,0,2],notes=['Elf standard. Orc stocky. Goblin small. Male and female masters for each build. Dwarf is the stocky rig displayed smaller.','Body cores are immutable within a rig. Only skin colors and identity layers vary. Original source heads are retained.','Equipment authoring targets these six fixed body sheets. Existing armor auto-fits are retired. Helmets still need per-head clearance.'])
    manifest['hybridSheets']=previews.build(DEST,actors)
    (DEST/'manifest.json').write_text(json.dumps(manifest,indent=2))
    (DEST/'head-preservation.json').write_text(json.dumps(dict(summary=summary,checks=head_proofs),indent=2))
    for tag,items in [('Male',[a for a in actors if a['sex']=='male' and a['appearance'].lower()=='base']),
        ('Female',[a for a in actors if a['sex']=='female' and a['appearance'].lower()=='base'])]:
        contact=Image.new('RGB',(1024,math.ceil(len(items)/4)*210),(24,29,35));draw=ImageDraw.Draw(contact)
        for i,a in enumerate(items):
            x=i%4*256;y=i//4*210
            im=Image.open(DEST/'Characters'/a['id']/'Preview.png').resize((192,200),Image.Resampling.NEAREST)
            contact.paste(im,(x+30,y+13),im);draw.text((x+5,y+3),a['label'][:36],fill='white')
        contact.save(DEST/(tag+'_Shared_Bodies_Contact.png'))
    if (HERE/'viewer.template.html').exists():
        embedded=dict(manifest,images=images,thumbs=thumbs)
        (DEST/'index.html').write_text((HERE/'viewer.template.html').read_text().replace('/*DATA*/null',json.dumps(embedded,separators=(',',':'))))
    (DEST/'README.md').write_text('# Three shared builds, six body masters\n\n'+json.dumps(summary,indent=2)+'\n\nStandard uses Elf proportions; stocky uses Orc proportions; small uses Goblin proportions. Each has a male and female sheet with three poses and four directions. Dwarves use the stocky rig at a smaller whole-character display scale.\n\nAll existing race/hybrid heads are extracted as unchanged RGBA pixels and attached by integer translation. No head scaling, repainting or regeneration is used. Original donor atlases and hashes are included. Longer hair and wings/tails are identity layers. Extraction boundaries still need visual review.\n\nEach body silhouette is identical to its master: only palette tint varies. Equipment must be authored once for each of the six fixed masters; no per-race armor stretching is performed. Helmets require head-specific clearance.\n\nBody cores are 64×64 logical frames. Composites use padded 128×128 frames with a 64px body at (32,32), protecting large heads and horns. These sheets are not live-game integrated. Injury states, attacks, sixteen facings and the new fixed-rig armor sheets remain pending.\n')
    # Retire the rejected automatic fitter while keeping every old asset available.
    for legacy in [ROOT/'Dungeon Master Sample/Layered Deepguard Fitting',DONORS]:
        page=legacy/'index.html'
        archive=legacy/'Archived Automatic Fitter.html'
        if page.exists() and not archive.exists():shutil.copyfile(page,archive)
        page.write_text('<!doctype html><meta charset="utf-8"><meta http-equiv="refresh" content="0;url=../Shared%20Body%20Rigs/index.html"><title>Shared Body Rigs</title><a href="../Shared%20Body%20Rigs/index.html">Open shared bodies and original heads</a>')
    print(json.dumps(dict(folder=str(DEST),summary=summary)))


if __name__=='__main__':main()

