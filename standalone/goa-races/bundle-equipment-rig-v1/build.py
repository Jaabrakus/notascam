"""Sword/shield animation using the approved Elf rig; optional Orc draft."""
from pathlib import Path
import base64,hashlib,json,math,sys,shutil
import numpy as np
from PIL import Image,ImageDraw

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
BUNDLE=ROOT/'standalone/remastered/reports/goa-sprite-test/goa-zones-bundle'
OUT=ROOT/'Dungeon Master Sample/GOA Sword and Shield Rig'
GEAR=ROOT/'standalone/goa-races/armor-designs/racial-redraws-v1/parts'
sys.path.insert(0,str(BUNDLE/'tools'))
from pose import scale2x
from body_motion import pose as pose_body,point as transform_point
from one_handed import CLIP,REFERENCE,load_weapons,swing_pose,weapon_orientation,root_offset

FACINGS='SNEW';SIZE=128;OFFSET=32
GROUPS={'R':[(10,11),(12,),(13,)],'L':[(14,15),(16,),(17,)]}
GRIPS={'S':{'R':[16,39],'L':[48,40]},'N':{'R':[48,39],'L':[16,40]},
       'E':{'R':[38,42],'L':[40,39]},'W':{'R':[18,36],'L':[26,42]}}

def length(a,b):return float(np.linalg.norm(np.asarray(b)-a))
def angle(a,b):return math.atan2(b[1]-a[1],b[0]-a[0])
def matrix(a,b,c,d):
    t=angle(c,d)-angle(a,b);co,si=math.cos(t),math.sin(t)
    m=np.array([[co,-si,0],[si,co,0],[0,0,1.]])
    m[:2,2]=np.asarray(c)-m[:2,:2]@np.asarray(a)
    return m
def translate(delta):
    m=np.eye(3);m[:2,2]=delta;return m
def warp(image,m):
    # Use the bundle's pixel-art edge-preserving scale filter, then inverse-map
    # once to native pixels. No repeated rotate/resize of already posed art.
    up=scale2x(scale2x(image));yy,xx=np.mgrid[0:SIZE,0:SIZE]
    dx,dy=xx.ravel()-OFFSET,yy.ravel()-OFFSET;inv=np.linalg.inv(m)
    sx=inv[0,0]*dx+inv[0,1]*dy+inv[0,2];sy=inv[1,0]*dx+inv[1,1]*dy+inv[1,2]
    assert np.isfinite(sx).all() and np.isfinite(sy).all()
    x=np.floor(sx*4+2).astype(int);y=np.floor(sy*4+2).astype(int)
    ok=(x>=0)&(x<256)&(y>=0)&(y<256);out=np.zeros((SIZE*SIZE,4),np.uint8)
    out[ok]=up[y[ok],x[ok]];return Image.fromarray(out.reshape(SIZE,SIZE,4))
def solve(shoulder,target,upper,lower,bend):
    delta=np.asarray(target)-shoulder;distance=float(np.linalg.norm(delta))
    direction=math.atan2(delta[1],delta[0]);reach=max(abs(upper-lower)+.001,min(distance,upper+lower-.001))
    theta=math.acos(np.clip((upper*upper+reach*reach-lower*lower)/(2*upper*reach),-1,1))
    elbow=np.asarray(shoulder)+[math.cos(direction+bend*theta)*upper,math.sin(direction+bend*theta)*upper]
    wrist=np.asarray(shoulder)+[math.cos(direction)*reach,math.sin(direction)*reach]
    return elbow,wrist
def item_layer(image,grip,target,rotation=0,axis_scale=1):
    if rotation or axis_scale!=1:
        registered=Image.new('RGBA',(64,64));registered.alpha_composite(image,(32-grip[0],32-grip[1]))
        end=[target[0]+math.sin(rotation),target[1]-math.cos(rotation)]
        transform=matrix([32,32],[32,31],target,end)
        transform[:2,1]*=axis_scale;transform[:2,2]=np.asarray(target)-transform[:2,:2]@np.array([32,32])
        return warp(np.asarray(registered),transform)
    out=Image.new('RGBA',(SIZE,SIZE));out.alpha_composite(image,(round(target[0]+OFFSET-grip[0]),round(target[1]+OFFSET-grip[1])));return out

def main():
    global OUT
    actor='Orc' if '--orc-draft' in sys.argv else 'Elf'
    if actor=='Orc':OUT=ROOT/'Dungeon Master Sample/GOA Orc Sword and Shield Draft'
    OUT.mkdir(parents=True,exist_ok=True);(OUT/'assets').mkdir(exist_ok=True)
    elf_dir=ROOT/'Dungeon Master Sample/Unique Body Equipment Rig'
    elf=None
    if actor=='Elf':
        rig_path=elf_dir/'rig.json';elf=json.loads(rig_path.read_text())
        body_path=elf_dir/'assets/elf-original.png';body=np.asarray(Image.open(body_path).convert('RGBA'))
        sources=[rig_path,body_path]
    else:
        body_path=BUNDLE/'limb-zones/Orc/body.png';zone_path=BUNDLE/'fine-zones/Orc/fine.png';rig_path=BUNDLE/'skeleton/Orc.json'
        body=np.asarray(Image.open(body_path).convert('RGBA'));zones=np.asarray(Image.open(zone_path));rig=json.loads(rig_path.read_text())
        sources=[body_path,zone_path,rig_path]
    embedded={};metadata=[];exports={}
    grips=({'S':{'R':[19,37],'L':[44,39]},'N':{'R':[44,37],'L':[24,33]},'E':{'R':[43,36],'L':[39,38]},'W':{'R':[18,32],'L':[23,37]}} if elf else GRIPS)
    def save(im,name):
        path=OUT/'assets'/name;path.parent.mkdir(parents=True,exist_ok=True);im.save(path)
        embedded[name]='data:image/png;base64,'+base64.b64encode(path.read_bytes()).decode();return name
    def cell(array,d,f):return array[f*64:(f+1)*64,d*64:(d+1)*64].copy()
    refs={};gear={};body_parts={}
    for d,F in enumerate(FACINGS):
        refs[F]={}
        if elf:
            body_parts[F]={}
            for key,file in elf['directions'][d]['fullBody']['parts'].items():
                if 'Arm' in key or 'Hand' in key:continue
                path=elf_dir/'assets'/file;sources.append(path)
                body_parts[F][key]=np.asarray(Image.open(path).convert('RGBA'))
        for side in 'RL':
            if elf:
                frame=0;side_name='right' if side=='R' else 'left';spec=elf['directions'][d]
                shoulder,elbow,wrist=[np.asarray(pt,float) for pt in spec['arms'][side_name]];grip=wrist.copy()
                paths=[elf_dir/'assets'/spec['frames'][0][side_name+'-'+part+'-refined'] for part in ['upper','forearm','hand']]
                sources.extend(paths);layers=[np.asarray(Image.open(p).convert('RGBA')) for p in paths]
            else:
                frame=1 if (F,side) in [('E','L'),('W','R')] else 0
                art=cell(body,d,frame);z=cell(zones,d,frame);j=rig['cells'][F+str(frame)]['joints']
                shoulder=np.array(j['shoulder'+side]);elbow=np.array(j['elbow'+side]);wrist=np.array(j['wrist'+side])
                yy,xx=np.nonzero(z==(13 if side=='R' else 17));grip=np.array([xx.mean(),yy.mean()])
                layers=[np.where(np.isin(z,group)[...,None],art,0).astype(np.uint8) for group in GROUPS[side]]
            refs[F][side]={'frame':frame,'shoulder':shoulder,'elbow':elbow,'wrist':wrist,'grip':grip,'layers':layers}
            for part,layer in zip(['upper-arm','forearm','hand'],layers):save(Image.fromarray(layer),f'sources/{F}-{side}-{part}.png')
        sword_path=GEAR/f'melee-weapons/weapon.arming_sword/{["South","North","East","West"][d]}.png'
        shield_path=GEAR/f'custom-shields/shield.round/{"North" if F in "NE" else "South"}.png'
        sources.extend([sword_path,shield_path])
        sword=Image.open(sword_path).convert('RGBA').resize((14 if d<2 else 8,30),Image.Resampling.NEAREST)
        shield=Image.open(shield_path).convert('RGBA').resize((18 if F=='E' else 22,24),Image.Resampling.NEAREST)
        gear[F]={'sword':sword,'shield':shield,'swordGrip':[sword.width//2,24],'shieldGrip':[shield.width//2,12]}
        save(sword,f'gear/{F}-sword.png');save(shield,f'gear/{F}-shield.png')

    sources.extend([REFERENCE,REFERENCE.with_suffix('.png')])
    shutil.copyfile(REFERENCE.with_suffix('.png'),OUT/'Human_Attack_Reference.png')
    catalog,weapon_art=load_weapons(GEAR,save,sources)
    export_files={}
    for motion in ['idle','walk','attack']:
        atlas=Image.new('RGBA',(4*SIZE,8*SIZE));animation=[];frames=[]
        for f in range(8):
            phase=f/8;source_frame=[0,1,0,2][f//2] if motion=='walk' else 0
            row=[];review=Image.new('RGBA',(4*SIZE,SIZE),'#26362d')
            for d,F in enumerate(FACINGS):
                if elf:
                    spec=elf['directions'][d]['frames'][source_frame]
                    paths=[elf_dir/'assets'/spec[k] for k in ['refined-torso','render-head']];sources.extend(paths)
                    static_image=Image.open(paths[0]).convert('RGBA');static_image.alpha_composite(Image.open(paths[1]).convert('RGBA'))
                    static=np.asarray(static_image).copy();removed=np.zeros((64,64),bool)
                else:
                    original=cell(body,d,source_frame);z=cell(zones,d,source_frame);j=rig['cells'][F+str(source_frame)]['joints']
                    static=original.copy();static[np.isin(z,list(range(10,18)))]=0
                    removed=np.isin(z,list(range(10,18)))
                # Recover visible torso pixels from neighboring authored walk
                # cells only inside the original silhouette and removed arms.
                for other in ([] if elf else range(3)):
                    candidate=cell(body,d,other);cz=cell(zones,d,other)
                    valid=removed&np.isin(cz,[6,7,8,9])&(static[:,:,3]==0)
                    static[valid]=candidate[valid]
                root_shift=root_offset(F,f) if motion=='attack' else np.zeros(2,dtype=int)
                static_layer=Image.new('RGBA',(SIZE,SIZE));static_layer.alpha_composite(Image.fromarray(static),(OFFSET+int(root_shift[0]),OFFSET+int(root_shift[1])))
                body_state=None;body_transform=translate(root_shift);posed_parts={}
                if elf and motion=='attack':
                    articulated,body_transform,body_state,posed_parts=pose_body(F,f,elf['directions'][d]['fullBody'],body_parts[F],root_shift,warp,matrix,solve)
                    if body_state['active']:static_layer=articulated
                arm_layers={};states={};hand_layers={};attack_pitch=0.
                for side in 'RL':
                    ref=refs[F][side]
                    # The held upper body follows the original chest/neck bob;
                    # walking legs remain exactly the approved drawn frames.
                    if elf:shift=np.array([0,-1 if source_frame else 0])
                    else:
                        idle_neck=rig['cells'][F+'0']['joints']['neck']
                        shift=np.array([j['neck'][0]-idle_neck[0],j['neck'][1]-idle_neck[1]])
                    shift=shift+root_shift
                    shoulder=transform_point(body_transform,ref['shoulder']) if body_state else ref['shoulder']+shift
                    desired=np.asarray(grips[F][side],float)+shift
                    if motion!='attack':desired[1]+=math.sin(phase*math.tau)*(.4 if motion=='idle' else .7)
                    if motion=='attack' and side=='R':
                        reach=length(ref['shoulder'],ref['elbow'])+length(ref['elbow'],ref['wrist'])
                        desired,attack_pitch=swing_pose(F,f,shoulder,reach,desired)
                    if body_state:desired=transform_point(body_transform,desired-root_shift)
                    offset=ref['grip']-ref['wrist'];target=desired-offset
                    bend=1 if F=='E' else -1 if F=='W' else (1 if shoulder[0]<32 else -1)
                    elbow,wrist=solve(shoulder,target,length(ref['shoulder'],ref['elbow']),length(ref['elbow'],ref['wrist']),bend)
                    transforms=[matrix(ref['shoulder'],ref['elbow'],shoulder,elbow),matrix(ref['elbow'],ref['wrist'],elbow,wrist),translate(wrist-ref['wrist'])]
                    if motion=='attack' and side=='R':
                        roll=attack_pitch*.5*(1 if F=='E' else -1) if F in 'EW' else math.sin(attack_pitch)*(.22 if F=='S' else -.22)
                        grip_target=wrist+offset
                        transforms[2]=matrix(ref['grip'],ref['grip']+[0,-1],grip_target,grip_target+[math.sin(roll),-math.cos(roll)])
                    parts=[warp(im,m) for im,m in zip(ref['layers'],transforms)]
                    arm=Image.new('RGBA',(SIZE,SIZE))
                    # Existing skin samples back the small elbow/wrist seam;
                    # retain the source limb artwork above these hidden caps.
                    px=np.concatenate([a.reshape(-1,4) for a in ref['layers']]);skin=px[(px[:,3]>=128)&((px[:,0]>px[:,1]) if elf else (px[:,1]>px[:,0]))&(px[:,1]>px[:,2])]
                    assert len(skin),'Missing source skin for joint caps'
                    color=tuple(int(v) for v in skin[len(skin)//2])
                    draw=ImageDraw.Draw(arm)
                    for x,y in [shoulder,elbow,wrist]:draw.ellipse((round(x)+OFFSET-1,round(y)+OFFSET-1,round(x)+OFFSET+1,round(y)+OFFSET+1),fill=color)
                    for part in parts:arm.alpha_composite(part)
                    arm_layers[side]=arm;hand_layers[side]=parts[2]
                    actual=wrist+offset
                    states[side]={'sourceFrame':ref['frame'],'shoulder':shoulder.tolist(),'elbow':elbow.tolist(),'wrist':wrist.tolist(),'grip':actual.tolist(),'upperLength':length(ref['shoulder'],ref['elbow']),'forearmLength':length(ref['elbow'],ref['wrist'])}
                sword_angle,axis_scale=weapon_orientation(F,attack_pitch)
                if body_state:sword_angle+=body_state['torsoAngle']
                sword=item_layer(gear[F]['sword'],gear[F]['swordGrip'],states['R']['grip'],sword_angle,axis_scale)
                shield=item_layer(gear[F]['shield'],gear[F]['shieldGrip'],states['L']['grip'])
                # Sword shaft sits under the right fist; shield outer face covers
                # the left fist. Rear views show the authored shield straps.
                layers={'body':static_layer,'rightArm':arm_layers['R'],'leftArm':arm_layers['L'],'sword':sword,'shield':shield,'rightHand':hand_layers['R']}
                order={'S':['body','rightArm','leftArm','sword','rightHand','shield'],
                       'N':['rightArm','sword','rightHand','leftArm','shield','body'],
                       'E':['leftArm','shield','body','rightArm','sword','rightHand'],
                       'W':['rightArm','sword','rightHand','body','leftArm','shield']}[F]
                if motion=='attack' and F=='S':order=['body','leftArm','shield','rightArm','sword','rightHand']
                final=Image.new('RGBA',(SIZE,SIZE))
                for key in order:final.alpha_composite(layers[key])
                prefix=f'{motion}/{f}-{F}';files={key:save(im,prefix+'-'+key+'.png') for key,im in layers.items()}
                weapons={'sword':files['sword']}
                for ident in catalog:
                    if ident=='sword':continue
                    im,grip=weapon_art[ident][F]
                    weapons[ident]=save(item_layer(im,grip,states['R']['grip'],sword_angle,axis_scale),f'{motion}/{f}-{F}-{ident}.png')
                if body_state:
                    body_state['parts']={key:save(im,prefix+'-body-'+key+'.png') for key,im in posed_parts.items()}
                frame_record={'bodyRig':body_state,'facing':F,'sourceFrame':source_frame,'rootOffset':root_shift.tolist(),'layers':files,'weapons':weapons,'order':order,'arms':states,'swordGrip':states['R']['grip'],'shieldGrip':states['L']['grip'],'swordAngle':sword_angle,'weaponAxisScale':axis_scale,'phase':CLIP['phases'][f] if motion=='attack' else motion,'strike':motion=='attack' and f==4}
                row.append(frame_record);atlas.alpha_composite(final,(d*SIZE,f*SIZE));review.alpha_composite(final,(d*SIZE,0))
                metadata.append({'motion':motion,'frame':f,**frame_record})
            frames.append(row);animation.append(review.resize((1024,256),Image.Resampling.NEAREST).convert('RGB'))
        atlas.save(OUT/f'{actor}_Sword_Shield_{motion.title()}_128px.png')
        native=Image.new('RGBA',(256,512));fits_native=True
        for f in range(8):
            for d in range(4):
                tile=atlas.crop((d*SIZE,f*SIZE,(d+1)*SIZE,(f+1)*SIZE));bbox=tile.getbbox()
                fits_native &= bool(bbox and bbox[0]>=32 and bbox[1]>=32 and bbox[2]<=96 and bbox[3]<=96)
                if motion!='attack':assert fits_native,('64px export overflow',motion,f,F,bbox)
                native.paste(tile.crop((32,32,96,96)),(d*64,f*64))
        if fits_native:native.save(OUT/f'{actor}_Sword_Shield_{motion.title()}_64px.png')
        animation[0].save(OUT/f'{actor}_Sword_Shield_{motion.title()}.gif',save_all=True,append_images=animation[1:],duration=CLIP['frameDurationsMs'] if motion=='attack' else 150,loop=0,disposal=2)
        # Native-body crop with eight phases, four facing rows for honest review.
        contact=Image.new('RGBA',(8*96,4*96),'#26362d')
        for f in range(8):
            for d in range(4):contact.alpha_composite(atlas.crop((d*SIZE+16,f*SIZE+8,d*SIZE+112,f*SIZE+104)),(f*96,d*96))
        contact.resize((1536,768),Image.Resampling.NEAREST).save(OUT/f'{motion.title()}_Inspection.png')
        exports[motion]=frames
    # Bake the same character/hand poses with each weapon. Padding is retained
    # for attacks whose tip extends outside the original 64px body cell.
    for motion,frames in exports.items():
        export_files[motion]={}
        for ident,profile in catalog.items():
            atlas=Image.new('RGBA',(512,1024));native=Image.new('RGBA',(256,512));fits=True
            for f,row in enumerate(frames):
                for d,record in enumerate(row):
                    tile=Image.new('RGBA',(128,128))
                    for key in record['order']:
                        file=record['weapons'][ident] if key=='sword' else record['layers'][key]
                        tile.alpha_composite(Image.open(OUT/'assets'/file).convert('RGBA'))
                    box=tile.getbbox();assert box and box[0]>0 and box[1]>0 and box[2]<128 and box[3]<128
                    fits &= box[0]>=32 and box[1]>=32 and box[2]<=96 and box[3]<=96
                    atlas.paste(tile,(d*128,f*128));native.paste(tile.crop((32,32,96,96)),(d*64,f*64))
            stem=f'{actor}_{profile["slug"]}_Shield_{motion.title()}'
            atlas.save(OUT/(stem+'_128px.png'))
            if fits:native.save(OUT/(stem+'_64px.png'))
            export_files[motion][ident]={'png':stem+('_64px.png' if fits else '_128px.png'),'cellSize':64 if fits else 128,'origin':[0,0] if fits else [32,32],'paddedPng':stem+'_128px.png'}
    data={'actor':actor,'version':4,'baseRig':str(rig_path.relative_to(ROOT)),'cellSize':128,'bodyPixels':64,'nativeExports':{'cellSize':64,'columns':['South','North','East','West'],'rows':8,'renderCrop':[32,32,96,96],'frameMs':150},'weapons':catalog,'attackClip':CLIP,'exports':export_files,'directions':['South','North','East','West'],'frameMs':150,'frames':exports,'images':embedded,
          'sources':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
          'notes':(['User selected the approved Elf v7 rig as animation template.','Uses its existing completed arm cutouts, joints, head and torso layers.','Preserves the existing repaired drawn Elf walk; only the held arm targets are changed.'] if elf else ['Tuned GOA bundle Orc body, fine zones and skeleton.','Far arm uses visible authored walk-frame artwork when idle occludes it.'])+['Right-hand arming sword; left-hand round shield.','Existing approved equipment art reused. Source art and rig remain unchanged.']}
    (OUT/'rig.json').write_text(json.dumps({k:v for k,v in data.items() if k!='images'},indent=2))
    template=(HERE/'viewer.html').read_text()
    if elf:template=template.replace('Orc','Elf').replace('GOA zone bundle / tuned Elf rig','Approved GOA Elf / existing body rig').replace('The original body, zone maps, skeleton and equipment sources are preserved.','The approved Elf body, completed arm pieces, joints and equipment sources are preserved.')
    fallback='data:image/gif;base64,'+base64.b64encode((OUT/f'{actor}_Sword_Shield_Attack.gif').read_bytes()).decode()
    (OUT/'index.html').write_text(template.replace('/*DATA*/','const DATA='+json.dumps(data)+';').replace('__FALLBACK_GIF__',fallback))
    (OUT/'README.md').write_text('''# GOA Orc sword and shield hold

Uses the supplied goa-zones-bundle tuned Orc body, fine zones and per-frame skeleton. No source bundle files or live-game assets are changed.

Idle hold and guarded walk: four facings, eight frames, native 64px transparent exports (256x512 sheets) plus padded 128px exports. All equipment fits inside the native cell; build checks prevent accidental cropping. Columns South/North/East/West, rows animation frames, 150ms per frame. Sword stays in anatomical right hand, shield in left. Side-view idle far arms are extracted from authored walk frames where visible. Held arms follow the source neck movement while the drawn walking legs stay intact. Small seam caps use existing Orc skin colors. Torso backing uses visible torso pixels from neighboring source frames; this is a limited hold, not an unrestricted pose generator.

Separate render layers, exact source hashes, grips and joint positions are in rig.json and assets/. The viewer can hide either item and show grips. Existing approved arming-sword and round-shield designs are reused, with shield front/back art selected by facing.

Build: `python3 standalone/goa-races/bundle-equipment-rig-v1/build.py`

Scope: Orc hold and guarded walk only. No attacks, universal race conversion, fitted armor set or live-game integration is claimed.
''')
    print(json.dumps({'output':str(OUT),'frames':len(metadata),'sources':len(data['sources'])}))
    if elf:
        (OUT/'README.md').write_text('''# Approved Elf sword and shield animations

The approved GOA Elf and its existing v7 rig are the animation template, as selected by the user. The former Orc experiment is kept separately in GOA Orc Sword and Shield Draft.

Idle hold and guarded walk, four facings, eight frames, 150ms per frame. Native 64px sheets are 256x512; padded 128px sheets are 512x1024. Columns South, North, East, West. Sword in anatomical right hand, shield in left. Shield front/back art and draw order follow facing; the sword sits beneath the gripping fist.

Uses the current Elf's completed upper arms, forearms, hands, original head, repaired torso and drawn walking legs. This does not replace them with Orc data or the experimental skeletal legs. The body preparation and original source files are not modified. Equipment is the existing arming sword and round shield, registered at the solved grips.

Source hashes, arm joints, grips, frame timing, draw order and separate PNG layers are in rig.json and assets/. The bundle's Scale2x helper is reused for pixel rotation; the skeletal profile is the Elf's.

Build: `python3 standalone/goa-races/bundle-equipment-rig-v1/build.py`

Version 3 retargets Human-sword-actions.json onto the Elf: raised windup, anticipation hop, cross-body sweep and recovery. Its authored per-facing grips and sweep vectors drive the weapon arm, with fixed Elf limb lengths. All body/equipment layers receive the same small pixel-snapped root movement. The shield follows the chest while keeping its approved guard target and North occlusion. Version 4 adds small-range articulated Elf torso/pelvis/head and two-bone legs. The ankles follow the root while the hips shift and knees flex. Shoulders and hand targets inherit the torso transform; the head counter-rotates. Hold endpoints retain the approved assembled body. The side far leg uses the existing inferred cutout, so this is an Elf body-motion preview, not finished rigging for all races. South attack order puts the weapon and gripping hand above the shield.

Frame durations are 360/85/85/150/70/70/160/80ms (1060ms total), splitting the Human reference phases across eight export frames. Strike is frame 4 (zero-based), after 680ms for the default sword. The same motion drives sword, hand axe, mace, warhammer, scimitar, dagger, GOA sword, rune sword and flame sword; each has its own measured grip and duration multiplier. Front/back use the Human lateral blade sweep at full length.

The approved North shield stays ahead of the character, occluded by the body. Attack sheets use padding where weapon tips leave the native body cell; rig.json exports provides the cell size and origin for each clip/item. No image is cropped to force it into 64px. Attack once returns to the held pose. The strike event is metadata for game integration, not live damage logic.

Scope: Elf one-handed swing, idle and guarded walk. Other races, thrusts, ranged/two-handed motion families and live-game replacement are not included.
''')

if __name__=='__main__':main()
