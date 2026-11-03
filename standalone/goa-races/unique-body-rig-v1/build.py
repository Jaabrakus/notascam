"""Build an isolated original-Elf equipment/arm-rig proof. Never edits source art."""
from pathlib import Path
from PIL import Image, ImageDraw
import base64, hashlib, json, shutil
from complete_surfaces import Completion, ART
from refine_cutouts import repair_torso,source_arm,clean_islands,walk_body
from full_body import prepare as prepare_full_body

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = ROOT / 'Dungeon Master Sample/Unique Body Equipment Rig'
REF = ROOT / 'standalone/goa-races/shared-body-rigs-v1/references/Elf_male_User_Approved.png'
HEAD = ROOT / 'Dungeon Master Sample/Shared Body Rigs/Body Templates/standard-male/Source_Heads_64px.png'
CHEST = ROOT / 'standalone/goa-races/armor-designs/deepguard-iron/pixel-fit-v2/pieces/64px/chest.png'
GEAR = ROOT / 'standalone/goa-races/armor-designs/racial-redraws-v1/parts'
WALK_REPAIR = HERE / 'walk-repair-v6/Elf_East_Opposite_Contact_AI.png'
DIRS = ['South', 'North', 'East', 'West']

# Authored in the original Elf's 64px coordinate space. Anatomical right/left.
ARMS = [
    {'right': [[23,29],[21,37],[20,44]], 'left': [[40,29],[42,37],[43,44]]},
    {'right': [[40,29],[42,37],[43,44]], 'left': [[23,29],[21,37],[20,44]]},
    {'right': [[29,29],[30,37],[30,44]], 'left': [[36,30],[38,34],[38,39]]},
    {'right': [[26,30],[24,34],[24,39]], 'left': [[34,29],[34,37],[34,44]]},
]
REGIONS = [
    {'right':[(16,29),(24,28),(25,36),(24,49),(15,49)], 'left':[(39,28),(46,29),(49,49),(39,49),(39,36)]},
    {'right':[(39,28),(46,29),(49,49),(39,49),(39,36)], 'left':[(16,29),(24,28),(25,36),(24,49),(15,49)]},
    {'right':[(26,28),(33,29),(34,49),(26,49)], 'left':[(37,29),(42,30),(42,41),(36,41)]},
    {'right':[(21,29),(26,29),(27,41),(21,41)], 'left':[(30,28),(37,29),(38,49),(29,49)]},
]

def save(im, name, images):
    file=OUT/'assets'/name;file.parent.mkdir(parents=True,exist_ok=True);im.save(file)
    images[name]='data:image/png;base64,'+base64.b64encode(file.read_bytes()).decode()
    return name

def main():
    OUT.mkdir(parents=True,exist_ok=True);images={};sources={}
    for p in [REF,HEAD,CHEST,ART,WALK_REPAIR,GEAR/'polearms-tools/weapon.spear/South.png',GEAR/'custom-shields/shield.round/South.png',GEAR/'custom-shields/shield.round/North.png']:
        sources[str(p.relative_to(ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest()
    shutil.copyfile(REF,OUT/'Original_Elf_Reference.png')
    original=Image.open(REF).convert('RGBA').resize((256,192),Image.Resampling.NEAREST)
    completion=Completion(original)
    # Only the missing opposite-contact legs are taken from this redraw.
    # Native head, hair, torso, arms and shorts remain the approved source.
    corrected_legs=Image.open(WALK_REPAIR).convert('RGBA').crop((385,910,984,1195)).resize((25,13),Image.Resampling.NEAREST)
    for y in range(corrected_legs.height):
        for x in range(corrected_legs.width):
            r,g,b,a=corrected_legs.getpixel((x,y))
            corrected_legs.putpixel((x,y),completion.color((r,g,b)) if a>=128 else (0,0,0,0))
    corrected_legs=clean_islands(corrected_legs)
    leg_layer=Image.new('RGBA',(64,64));leg_layer.paste(corrected_legs,(22,48))
    save(leg_layer,'east/opposite-contact-legs-64.png',images)
    heads=Image.open(HEAD).convert('RGBA');chests=Image.open(CHEST).convert('RGBA')
    save(original,'elf-original.png',images)
    records=[];partitions=0
    for d,name in enumerate(DIRS):
        frames=[]
        for frame in range(3):
            rect=(d*64,frame*64,d*64+64,frame*64+64)
            raw=original.crop(rect);head=heads.crop(rect)
            # Partition exact pixels. Head pixels take precedence over limb masks.
            layers={key:Image.new('RGBA',(64,64)) for key in ['head','torso','right-upper','right-lower','left-upper','left-lower']}
            masks={}
            for side,poly in REGIONS[d].items():
                mask=Image.new('L',(64,64));ImageDraw.Draw(mask).polygon(poly,fill=255);masks[side]=mask
            for y in range(64):
                for x in range(64):
                    pixel=raw.getpixel((x,y))
                    key='torso'
                    if head.getpixel((x,y))[3]:key='head'
                    else:
                        for side in ['right','left']:
                            if masks[side].getpixel((x,y)):
                                key=side+('-upper' if y<ARMS[d][side][1][1] else '-lower');break
                    layers[key].putpixel((x,y),pixel)
            # Copy partitions without blending: exact reconstruction including alpha.
            restored=Image.new('RGBA',(64,64))
            for layer in layers.values():
                for y in range(64):
                    for x in range(64):
                        if layer.getpixel((x,y))[3]:restored.putpixel((x,y),layer.getpixel((x,y)))
            assert restored.tobytes()==raw.tobytes(), (name,frame)
            partitions+=1
            frames.append({key:save(im,f'{name.lower()}/{frame}-{key}.png',images) for key,im in layers.items()})
            if frame==0:
                # Keep the disjoint source partition for verification; give the
                # articulated pieces a three-pixel shared elbow overlap.
                for side in ['right','left']:
                    upper=layers[side+'-upper'].copy();lower=layers[side+'-lower'].copy()
                    elbow=ARMS[d][side][1]
                    for y in range(max(0,elbow[1]-3),min(64,elbow[1]+4)):
                        for x in range(64):
                            if masks[side].getpixel((x,y)) and not head.getpixel((x,y))[3]:
                                upper.putpixel((x,y),raw.getpixel((x,y)));lower.putpixel((x,y),raw.getpixel((x,y)))
                    frames[0][side+'-upper-rig']=save(upper,f'{name.lower()}/{side}-upper-overlap.png',images)
                    frames[0][side+'-lower-rig']=save(lower,f'{name.lower()}/{side}-lower-overlap.png',images)
        # Equipped arms are articulated from the idle drawing. Keep its torso
        # above the hips so a walk-frame arm cannot survive as a second arm.
        idle_torso=Image.open(OUT/'assets'/frames[0]['torso']).convert('RGBA')
        raw_idle=original.crop((d*64,0,d*64+64,64))
        for shoulder,_,_ in ARMS[d].values():
            for y in range(max(0,shoulder[1]-3),min(64,shoulder[1]+4)):
                for x in range(max(0,shoulder[0]-3),min(64,shoulder[0]+4)):
                    if (x-shoulder[0])**2+(y-shoulder[1])**2<=10:
                        idle_torso.putpixel((x,y),raw_idle.getpixel((x,y)))
        for side in ['right','left']:
            upper=Image.open(OUT/'assets'/frames[0][side+'-upper-rig']).convert('RGBA')
            lower=Image.open(OUT/'assets'/frames[0][side+'-lower-rig']).convert('RGBA')
            completed=completion.arms(upper,lower,d,side,ARMS[d][side])
            for part,(im,added) in zip(['upper','lower'],completed):
                frames[0][side+'-'+part+'-complete']=save(im,f'{name.lower()}/{side}-{part}-completed.png',images)
                save(added,f'{name.lower()}/{side}-{part}-added-pixels.png',images)
        torso_complete,added=completion.torso(idle_torso,d)
        save(added,f'{name.lower()}/torso-added-pixels.png',images)
        for frame in range(3):
            equipped=idle_torso.copy()
            completed=torso_complete.copy()
            walking=Image.open(OUT/'assets'/frames[frame]['torso']).convert('RGBA')
            if frame:
                for y in range(44,64):
                    for x in range(64):
                        pixel=walking.getpixel((x,y))
                        if y<48 and ((d==2 and x<27) or (d==3 and x>36)):pixel=(0,0,0,0)
                        equipped.putpixel((x,y),pixel)
                        completed.putpixel((x,y),pixel)
            frames[frame]['equipped-torso']=save(equipped,f'{name.lower()}/{frame}-equipped-torso.png',images)
            frames[frame]['completed-torso']=save(completed,f'{name.lower()}/{frame}-completed-torso.png',images)
        chest=chests.crop((d*64,0,d*64+64,64));chest=chest.crop(chest.getbbox())
        # One authored Elf fit per facing; no per-race or automatic body warping.
        size=(18,12) if d<2 else (10,12)
        chest=chest.resize(size,Image.Resampling.NEAREST)
        chest_origin=[[23,28],[23,29],[31,28],[23,28]][d]
        chestfile=save(chest,f'{name.lower()}/deepguard-chest.png',images)
        shield_source='North' if d in [1,2] else 'South'
        shield=Image.open(GEAR/f'custom-shields/shield.round/{shield_source}.png').convert('RGBA')
        shield=shield.crop(shield.getbbox()).resize((6 if d==2 else 20,22),Image.Resampling.NEAREST)
        shieldfile=save(shield,f'{name.lower()}/round-shield.png',images)
        records.append(dict(name=name,frames=frames,arms=ARMS[d],chest=dict(image=chestfile,origin=chest_origin),shield=dict(image=shieldfile,grip=[shield.width//2,10]),nearArm='left' if d==3 else 'right'))
    # One side-arm master. Reflection swaps near/far anatomical arms; equipment
    # slots remain right=main hand and left=off hand. Original West layers stay
    # on disk and Original mode still uses the untouched source sheet.
    east,west=records[2],records[3]
    west['sourceArms']=west['arms']
    west['arms']={side:[[63-x,y] for x,y in east['arms'][opposite]] for side,opposite in [('right','left'),('left','right')]}
    west['armMirror']={'source':'East','axisX':31.5,'sideMap':{'right':'left','left':'right'}}
    for side,opposite in [('right','left'),('left','right')]:
        for part in ['upper','lower']:
            for suffix in ['rig','complete']:
                key=f'{side}-{part}-{suffix}';source_key=f'{opposite}-{part}-{suffix}'
                mirrored=Image.open(OUT/'assets'/east['frames'][0][source_key]).transpose(Image.Transpose.FLIP_LEFT_RIGHT)
                west['frames'][0][key]=save(mirrored,f'west/mirrored-east-{side}-{part}-{suffix}.png',images)
    refinements=[]
    for d,record in enumerate(records):
        name=record['name'].lower()
        for frame in record['frames']:
            for key,newkey in [('completed-torso','refined-torso'),('head','render-head')]:
                src=Image.open(OUT/'assets'/frame[key]).convert('RGBA')
                im=repair_torso(src,d,completion) if key=='completed-torso' else clean_islands(src)
                path=frame[key].replace('.png','-refined.png')
                frame[newkey]=save(im,path,images)
                refinements.append({'file':path,'changedPixels':sum(a!=b for a,b in zip(src.getdata(),im.getdata()))})
        for side in ['right','left']:
            for part in ['upper','lower']:
                key=f'{side}-{part}-complete';src=Image.open(OUT/'assets'/record['frames'][0][key]).convert('RGBA')
                im=source_arm(src,part,record['arms'][side]) if d<2 else src
                path=f'{name}/{side}-{part}-refined.png'
                record['frames'][0][f'{side}-{part}-refined']=save(im,path,images)
                refinements.append({'file':path,'changedPixels':sum(a!=b for a,b in zip(src.getdata(),im.getdata()))})
    # Rebuild walking from the intact source pelvis/leg layer, not a fixed
    # horizontal slice through the shorts and old arm masks.
    for d,record in enumerate(records[:3]):
        upper=Image.open(OUT/'assets'/record['frames'][0]['refined-torso']).convert('RGBA')
        for i,frame in enumerate(record['frames']):
            raw=original.crop((d*64,i*64,d*64+64,i*64+64))
            if d==2 and i==2:
                raw.paste(leg_layer.crop((0,48,64,64)),(0,48))
            body,lower,mask=walk_body(upper,raw,d,i)
            frame['refined-torso']=save(body,f'{record["name"].lower()}/{i}-anatomical-walk-body.png',images)
            frame['walk-lower']=save(lower,f'{record["name"].lower()}/{i}-original-pelvis-legs.png',images)
            frame['walk-lower-mask']=save(mask,f'{record["name"].lower()}/{i}-pelvis-leg-mask.png',images)
    # Share the whole side body (including the waist transition) so the west
    # abdomen cannot retain a different generated patch or detached arm shadow.
    for i,frame in enumerate(records[3]['frames']):
        east_body=Image.open(OUT/'assets'/records[2]['frames'][i]['refined-torso'])
        frame['refined-torso']=save(east_body.transpose(Image.Transpose.FLIP_LEFT_RIGHT),f'west/{i}-mirrored-east-body.png',images)
        for key in ['walk-lower','walk-lower-mask']:
            im=Image.open(OUT/'assets'/records[2]['frames'][i][key]).transpose(Image.Transpose.FLIP_LEFT_RIGHT)
            frame[key]=save(im,f'west/{i}-mirrored-{key}.png',images)
    records[3]['bodyMirror']={'source':'East','axisX':31.5,'includes':'torso, shorts and original walk legs; original west head retained'}
    # Separate hands from forearms so end-on arm projection never squashes the
    # fist or changes the equipment grip. These partitions exactly reconstruct
    # the existing lower-arm layer at rest.
    for record in records:
        for side in ['right','left']:
            cut=record['arms'][side][2][1]-2
            for suffix in ['rig','refined']:
                src=Image.open(OUT/'assets'/record['frames'][0][f'{side}-lower-{suffix}']).convert('RGBA')
                forearm=src.copy();hand=src.copy()
                for y in range(64):
                    for x in range(64):
                        if y>=cut:forearm.putpixel((x,y),(0,0,0,0))
                        else:hand.putpixel((x,y),(0,0,0,0))
                for name,im in [('forearm',forearm),('hand',hand)]:
                    record['frames'][0][f'{side}-{name}-{suffix}']=save(im,f'{record["name"].lower()}/{side}-{name}-{suffix}.png',images)
    spear=Image.open(GEAR/'polearms-tools/weapon.spear/South.png').convert('RGBA');spear=spear.crop(spear.getbbox()).resize((9,64),Image.Resampling.NEAREST)
    spearfile=save(spear,'spear.png',images)
    full_body=prepare_full_body(records,OUT,images,save)
    data=dict(version=7,actor='Approved GOA Elf · male',frameSize=64,canvasSize=128,directions=records,images=images,fullBody=full_body,
              raiseMotion={'action':'forward arm raise','maxPitchDegrees':115,'projection':'One sagittal-plane lift viewed from four cardinal directions. Front/back limb length is foreshortened; hands remain separate unscaled attachments.'},
              walkMotion={'frames':[0,1,0,2],'sideContacts':['near leg forward','far leg forward'],'oppositeContact':{'source':str(WALK_REPAIR.relative_to(ROOT)),'crop':[385,910,984,1195],'nativeSize':[25,13],'origin':[22,48],'palette':'exact approved source palette'},'mirror':'West reflects each completed East frame; never mirror a frame to fake the next temporal step.'},
              refinement={'method':'Original north/south arm and hand pixels restored from completed source cutouts, elbow overlap reduced to three rows, west side body mirrored from east to correct abdomen. Original sheets retained.','layers':refinements},
              sourceDecision='User selected approved GOA-style sprites intended for the finished game.',
              completion=dict(method='AI-generated hidden surfaces, registered to authored masks and remapped to exact source colors in CIELAB. Original visible layer pixels retained.',palette=completion.palette.tolist(),layers=completion.stats),
              spear=dict(image=spearfile,grip=[4,42]),sources=sources,
              skeleton={'root':None,**{part:parent or 'root' for part,parent in full_body['parents'].items()}},
              slots=full_body['slots'],
              limitations=['Walk mode retains the repaired drawn walk; Full-body joint test articulates all fifteen components through a small motion range, not a finished skeletal walk cycle.', 'Four authored facings; no synthesized 16-direction art.', 'Hidden surfaces are inferred artwork; source lighting rotates with the limb and extreme poses need replacement art and visual review.', 'Only Elf male has an authored full-body profile. Other races, females and hybrids retain their originals and need fit profiles.', 'Fifteen equipment attachment slots are defined; only chest, spear and shield have fitted render artwork in this proof.'])
    (OUT/'rig.json').write_text(json.dumps({k:v for k,v in data.items() if k!='images'},indent=2))
    template=(HERE/'viewer.html').read_text();runtime=(HERE/'runtime.js').read_text()
    (OUT/'index.html').write_text(template.replace('/*__DATA__*/','window.RIG_DATA='+json.dumps(data)+';').replace('/*__RUNTIME__*/',runtime))
    (OUT/'README.md').write_text('''# Original-body equipment rig proof

Version 7: original Elf male, four facings, fifteen separate body parts. Full-body joint test now articulates the thighs, shins and feet independently, with a head pivot, torso and pelvis layers, existing arm chains and equipment anchors. Inspect part isolates any component; Export 15 parts PNG saves registered 64px cells. Walk mode retains the repaired drawn animation as a comparison. The joint test deliberately uses small movements: this is not a finished skeletal walk or approval for deep knee bends. The far side leg and tiny joint caps are inferred from adjacent original artwork. Only Elf male is fitted so far; female, race and hybrid appearances are not converted. Helmet, shoulder, bracer, glove, waist, greave and boot anchors are defined, but only chest, spear and shield have equipped artwork. Original source sheets remain untouched.

All twelve source cells reconstruct exactly from the retained source partitions. Equip Deepguard chest armor, a spear and a round shield independently.

The arm rig uses shoulder → elbow → hand chains with two-bone inverse kinematics. The weapon grip follows the actual solved hand endpoint. Chest armor follows the torso. Legs and heads retain the supplied three-frame pixel animation. Idle, walk and a procedural spear-thrust study are available. This is a mixed sprite/bone proof, not a finished fully skeletal character.

The approved GOA Elf is the user-selected final-game art source. Version 2 adds AI-drawn hidden torso and joint surfaces only inside authored masks, remapped to the original source palette using CIELAB distance. Visible source pixels in each layer remain unchanged. Toggle Completed surfaces to compare against the original cutout. Raise arms tests the exposed torso without armor. The thrust and side-view partitions still need visual review before more races are added. Armor is an authored Elf fit, not a universal fit. No original race or hybrid art is replaced.

Version 3 uses East as the shared side-arm master. West arm artwork and joints are mirrored from East, swapping near/right to near/left and far/left to far/right. Heads, bodies and original source sheets are retained. The spear remains in the anatomical right hand and shield in the left; equipped poses therefore need not be whole-character mirror images. Reflection also mirrors the arms' baked shading.

Version 4 repairs north/south shoulder and elbow cuts with rounded complete limb ends, cleans detached pixel scraps, and repairs exposed torso contours. Rear-view arms render behind the back and hair. The original sheet and intermediate unmodified cutouts remain available; the final render layers deliberately replace malformed cut-edge pixels, so exact-source preservation applies to the retained originals, not every repaired edge.

Version 5 restores north/south source arm and hand artwork: the v4 capsule repaint made them too tubular. Elbow overlap is now three rows. The west body is mirrored from the east body, including the waist and walking legs; its approved head remains separate. Raise-arms now starts from relaxed hands in the front/back views. The default view is the actual idle stance, with Raise arms retained as a joint test.

Version 6 changes Raise arms to one forward raise with shared pitch across all four facings. Front/back arms project shorter as they point toward/away from the viewer; side views retain their full projected length. Hands are separate pieces and stay unscaled at the weapon grip. This uses pixel-snapped cutout projection, not newly drawn end-on anatomy. Further visual cleanup may require replacement end-on pose art. Walking now selects intact shorts and legs instead of reusing the arm partition below a horizontal cut. The source East contacts both read as the near leg leading, so the second contact uses a targeted AI leg redraw registered below the original shorts and remapped to source colors. West mirrors each completed East frame, not one step into the next. Free arms swing opposite the side-view leading leg. Original mode remains untouched.

Export PNG produces a 4-direction, 8-frame sheet with 128px cells and shared registration. Export fit JSON saves calibrated equipment offsets; Import fit JSON restores them. Rig debug exposes grip points and bones. Original mode displays the unmodified source sprites.

Build: `python3 standalone/goa-races/unique-body-rig-v1/build.py`

Architecture for expansion: keep unique race bodies; share bone names, slots and clip timing; author fitting profiles only where anatomy differs. Separate visual fit from race crafting restrictions. Bake approved poses to atlases for large crowds. Existing consolidated-body and automatic-fit experiments remain available in their own folders.
''')
    (OUT/'source-verification.json').write_text(json.dumps(dict(status='passed',exactSourcePartitions=partitions,sourceHashes=sources),indent=2))
    print(json.dumps(dict(output=str(OUT),exactSourcePartitions=partitions,assets=len(images))))

if __name__=='__main__':main()
