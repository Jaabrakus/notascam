"""Package actual approved sprite pixels as limbs and 16 injury combinations.

Default: Human preview only. Use --all only after the cut geometry is reviewed.
Pure pixel-cut assets remain unchanged. Optional tiny wound overlays are separate.
"""
import argparse
import hashlib
import importlib
import json
from pathlib import Path
import sys

from PIL import Image, ImageChops, PngImagePlugin

HERE = Path(__file__).resolve().parent
REGISTRY = HERE.parent / 'armory/bodies.json'
SLOTS = ['LeftArm', 'RightArm', 'LeftLeg', 'RightLeg']
DIRECTIONS = ['South', 'North', 'East', 'West']
# Exact canonical Surgery.dm rm_limb_states mapping; 1 means missing.
STATES = [('0000','Normal'),('1000','NoLeftArm'),('0100','NoRightArm'),('0010','NoLeftLeg'),
          ('0001','NoRightLeg'),('1100','NoArms'),('0011','NoLegs'),
          ('1001','NoRightLegNoLeftArm'),('0110','NoLeftLegNoRightArm'),
          ('0101','NoRightArmNoRightLeg'),('1010','NoLeftArmNoLeftLeg'),
          ('0111','NoLegsNoRightArm'),('1011','NoLegsNoLeftArm'),
          ('1101','NoArmsNoRightLeg'),('1110','NoArmsNoLeftLeg'),('1111','None')]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def support(image):
    return image.getchannel('A').point(lambda value: 255 if value else 0)


def changed_pixels(left, right):
    return sum(a != b for a, b in zip(left.getdata(), right.getdata()))


def validate_partition(original, cut):
    if original.mode != 'RGBA' or original.size != (64, 64):
        raise ValueError('The body renderer must return RGBA64 cells.')
    layers = [('core', cut['core'])] + [(slot, cut['parts'][slot]) for slot in SLOTS]
    coverage = Image.new('L', (64,64))
    # Preserve invisible RGB values too; source PNGs may retain color under alpha0.
    rebuilt = cut['core'].copy()
    for name, layer in layers:
        if layer.mode != 'RGBA' or layer.size != original.size:
            raise ValueError('All limb layers must retain their aligned64px RGBA cells: ' + name)
        visible = support(layer)
        if ImageChops.multiply(coverage, visible).getbbox():
            raise ValueError('Overlapping source pixel assignments: ' + name)
        coverage = ImageChops.lighter(coverage, visible)
        rebuilt.paste(layer, (0,0), visible)
    if rebuilt.tobytes() != original.tobytes():
        raise ValueError('Source pixel reconstruction failed: ' + str(changed_pixels(rebuilt, original)) + ' changed pixels.')
    return dict(exactRGBAReconstruction=True, overlappingPixels=0,
                sourceVisiblePixels=sum(value > 0 for value in original.getchannel('A').getdata()))


def without(original, cut, bits):
    missing = Image.new('L', original.size)
    for index, slot in enumerate(SLOTS):
        if bits[index] == '1':
            # The actual part pixels define removal, never an enlarged rectangle.
            missing = ImageChops.lighter(missing, support(cut['parts'][slot]))
    image = original.copy()
    image.paste((0,0,0,0), (0,0,64,64), missing)
    # Restore source pixels in the removed area: everything must reconstruct exactly.
    restored = image.copy()
    restored.paste(original, (0,0), missing)
    if restored.tobytes() != original.tobytes():
        raise ValueError('An injury state changed pixels outside its missing-limb masks.')
    return image


def sheet(rows, output):
    image = Image.new('RGBA', (256, len(rows)*64))
    for row, cells in enumerate(rows):
        if len(cells) != 4:
            raise ValueError('Each atlas row must contain S,N,E,W.')
        for view, cell in enumerate(cells):
            # Paste exact bytes; alpha compositing would change partial-alpha pixels.
            image.paste(cell, (view*64,row*64))
    image.save(output)
    return image


def description(states, sequence, delays, moving):
    lines = ['# BEGIN DMI','version = 4.0','\twidth = 64','\theight = 64']
    for name in states:
        lines += ['state = '+json.dumps(name), '\tdirs = 4', '\tframes = '+str(len(sequence)),
                  '\tdelay = '+','.join(f'{delay/100:g}' for delay in delays),
                  '\tmovement = '+str(int(moving)), '\tloop = 0', '\trewind = 0']
    lines += ['# END DMI','']
    return '\n'.join(lines)


def dmi(groups, sequence, delays, moving, output):
    rows = [frames[index] for frames in groups.values() for index in sequence]
    image = Image.new('RGBA',(256,len(rows)*64))
    for row,cells in enumerate(rows):
        for view,cell in enumerate(cells):
            image.paste(cell,(view*64,row*64))
    info = PngImagePlugin.PngInfo()
    info.add_text('Description', description(groups,sequence,delays,moving))
    image.save(output,format='PNG',pnginfo=info)
    # Ensure the DMI wrapper retained both pixels and original state names.
    with Image.open(output) as saved:
        if saved.tobytes()!=image.tobytes() or saved.info.get('Description')!=description(groups,sequence,delays,moving):
            raise ValueError('DMI serialization changed atlas pixels or state metadata.')


def rectangles(rows):
    return [[[view*64,row*64,64,64] for view in range(4)] for row in range(rows)]


def overlay_at_support(base, overlay):
    """Composite only actual overlay pixels, preserving alpha0 RGB elsewhere."""
    result=base.copy()
    result.paste(Image.alpha_composite(base,overlay),(0,0),support(overlay))
    return result


def wound_exports(body, frames, cuts, injury_groups, folder, sequence, delays, moving, wounds):
    caps=[];cap_counts=[]
    race=str(body.get('raceKey','')).lower().replace(' ','')
    no_blood=race.startswith('gargoyle') or race=='skeleton' or body.get('material') in ('stone','bone')
    for frame,cells in enumerate(frames):
        row=[]
        for view,original in enumerate(cells):
            overlays=wounds.wound_overlays(original,cuts[frame][view],body,frame,view)
            for slot in SLOTS:
                overlay=overlays[slot]
                if overlay.mode!='RGBA' or overlay.size!=(64,64):raise ValueError('Wound overlays must be aligned64px RGBA layers.')
                count=sum(value>0 for value in overlay.getchannel('A').getdata())
                palette=getattr(wounds,'PALETTE',None)
                if palette is not None and any(pixel not in palette for pixel in overlay.getdata() if pixel[3]):raise ValueError('Wound overlay uses a color outside its declared source palette.')
                if count>4:raise ValueError('Wound cap exceeds the4-pixel budget: '+body['id']+' '+slot)
                if no_blood and count:raise ValueError('Stone and Skeleton bodies must not receive blood caps.')
                if not support(cuts[frame][view]['parts'][slot]).getbbox() and count:raise ValueError('An invisible limb received an invented wound cap.')
                cap_counts.append(dict(frame=frame,direction=DIRECTIONS[view],slot=slot,pixels=count))
            row.append(overlays)
        caps.append(row)
    cap_groups={slot:[[caps[frame][view][slot] for view in range(4)] for frame in range(len(frames))] for slot in SLOTS}
    sheet([row for group in cap_groups.values() for row in group],folder/'wound-caps.png')
    dmi(cap_groups,sequence,delays,moving,folder/'wound-caps.dmi')
    bloody={};checked=0
    for bits,name in STATES:
        state=[]
        for frame,cells in enumerate(frames):
            row=[]
            for view,original in enumerate(cells):
                base=injury_groups[name][frame][view]
                image=base.copy();cap_mask=Image.new('L',(64,64));allowed=Image.new('L',(64,64))
                for index,slot in enumerate(SLOTS):
                    if bits[index]=='1':
                        cap=caps[frame][view][slot];image=overlay_at_support(image,cap)
                        cap_mask=ImageChops.lighter(cap_mask,support(cap))
                        allowed=ImageChops.lighter(allowed,support(cuts[frame][view]['parts'][slot]))
                allowed=ImageChops.lighter(allowed,cap_mask)
                restored=image.copy();restored.paste(original,(0,0),allowed)
                if restored.tobytes()!=original.tobytes():raise ValueError('Blood-state pixels changed outside removed limb and cap masks.')
                restored=image.copy();restored.paste(base,(0,0),cap_mask)
                if restored.tobytes()!=base.tobytes():raise ValueError('Wound composition changed the pure injury outside its cap pixels.')
                row.append(image);checked+=1
            state.append(row)
        bloody[name]=state
    sheet([row for group in bloody.values() for row in group],folder/'injuries-with-blood.png')
    dmi(bloody,sequence,delays,moving,folder/'injuries-with-blood.dmi')
    return dict(enabled=True,separateOverlay=True,capPixelBudget=4,noBloodMaterial=no_blood,
                capPixels=sum(item['pixels'] for item in cap_counts),capCounts=cap_counts,
                injuryViewsChecked=checked,outsideCapAndRemovedMaskChangedPixels=0,
                outsideCapVsPureInjuryChangedPixels=0,
                sourcePaletteOnly=True,qualityFlags=list(getattr(wounds,'QUALITY_FLAGS',())),
                method='wound_pixels.wound_overlays; alpha support restricted composition')


def pack_body(body, cutter, destination, wounds=None):
    source=Path(body['source']); before=sha(source)
    frames=cutter.render_body(body)
    if len(frames)!=len(body['sourceRects']) or not frames:
        raise ValueError('Rendered frame count does not match body source rectangles.')
    folder=destination/body['id'];folder.mkdir(parents=True,exist_ok=True)
    cuts=[];proof=[];flags=set(body.get('qualityFlags',[]));methods=set()
    for frame_index,cells in enumerate(frames):
        if len(cells)!=4:raise ValueError('Body renderer omitted a cardinal view.')
        row=[]
        for view,cell in enumerate(cells):
            cut=cutter.split_frame(cell,body,frame_index,view)
            entry=validate_partition(cell,cut)
            entry.update(frame=frame_index,direction=DIRECTIONS[view],
                         visiblePartPixels={slot:sum(value>0 for value in cut['parts'][slot].getchannel('A').getdata()) for slot in SLOTS})
            proof.append(entry);row.append(cut);methods.add(cut.get('method','unspecified'))
            flags.update(cut.get('qualityFlags',[]))
        cuts.append(row)
    normal=sheet(frames,folder/'normal.png')
    sheet([[cuts[f][v]['core'] for v in range(4)] for f in range(len(frames))],folder/'core.png')
    part_rows=[[cuts[f][v]['parts'][slot] for v in range(4)] for slot in SLOTS for f in range(len(frames))]
    sheet(part_rows,folder/'parts.png')
    mask_rows=[]
    for slot in SLOTS:
        for frame_index in range(len(frames)):
            mask_rows.append([Image.merge('RGBA',(Image.new('L',(64,64),255),)*3+(support(cuts[frame_index][view]['parts'][slot]),)) for view in range(4)])
    sheet(mask_rows,folder/'part-masks.png')
    injury_groups={}
    for bits,name in STATES:
        injury_groups[name]=[[without(frames[f][v],cuts[f][v],bits) for v in range(4)] for f in range(len(frames))]
    injury_rows=[row for frames_for_state in injury_groups.values() for row in frames_for_state]
    sheet(injury_rows,folder/'injuries.png')
    animation=body['animation'];sequence=animation.get('sequence',list(range(len(frames))))
    delays=animation.get('delaysMs',[200]*len(sequence))
    if any(type(index)is not int or not 0<=index<len(frames) for index in sequence) or len(delays)!=len(sequence):
        raise ValueError('Invalid body animation sequence or timing.')
    moving=animation.get('kind') in ('walk','flight')
    dmi(injury_groups,sequence,delays,moving,folder/'injuries.dmi')
    dmi({slot:[[cuts[f][v]['parts'][slot] for v in range(4)] for f in range(len(frames))] for slot in SLOTS},sequence,delays,moving,folder/'parts.dmi')
    dmi({'Normal':frames},sequence,delays,moving,folder/'normal.dmi')
    wound_report=wound_exports(body,frames,cuts,injury_groups,folder,sequence,delays,moving,wounds) if wounds else dict(enabled=False)
    if sha(source)!=before:raise ValueError('The original body source changed during packaging.')
    summary=dict(id=body['id'],label=body['label'],raceKey=body['raceKey'],variant=body['variant'],
                 source=str(source),sourceSha256=before,renderedBodySha256=sha(folder/'normal.png'),
                 frameCount=len(frames),directions=DIRECTIONS,states=len(STATES),
                 exactRGBAReconstruction=True,overlappingPixels=0,outsideMaskChangedPixels=0,
                 injuryViewsChecked=len(STATES)*len(frames)*4,
                 woundCaps=wound_report,
                 inventedFarSidePixels=0,geometryStatus='draft cut masks; anatomical review required',
                 methods=sorted(methods),qualityFlags=sorted(flags),proof=proof)
    (folder/'proof.json').write_text(json.dumps(summary,indent=2))
    state_metadata=[dict(bits=bits,name=name,missing=[slot for index,slot in enumerate(SLOTS) if bits[index]=='1']) for bits,name in STATES]
    metadata=dict(format='goa-source-pixel-limbs',version=1,bodyId=body['id'],frameSize=[64,64],directionOrder=DIRECTIONS,
                  source=body,states=state_metadata,slots=SLOTS,animation=dict(animation,encodedDMISequence=sequence,encodedDMIFrames=len(sequence),delaysDeciseconds=[value/100 for value in delays]),
                  atlases=dict(normal=dict(image='normal.png',rows=len(frames)),parts=dict(image='parts.png',rows=len(part_rows),rowOrder='slot then source frame'),injury=dict(image='injuries.png',rows=len(injury_rows),rowOrder='canonical state then source frame')),
                  normalState='Normal',stateNameBinding='Canonical Surgery.dm rm_limb_states names; renderer callers must use Normal for the intact body.',
                  reconstruction=dict(exactRGBA=True,overlapPixels=0,outsideMaskChangedPixels=0),
                  wounds=wound_report,
                  existingGameBinding=dict(physics='LimbFling and RmG3Limb already implement flying body pieces; this export adds no physics',
                                           limbStates='Code/Remastered/Surgery.dm rm_limb_states',
                                           status='asset export only; not integrated into live body registration'),
                  status='actual source-pixel cutouts; geometry is a review draft, not anatomy approval')
    if wounds:
        metadata['atlases']['woundCaps']=dict(image='wound-caps.png',rows=len(part_rows),rowOrder='slot then source frame',dmi='wound-caps.dmi')
        metadata['atlases']['injuryWithBlood']=dict(image='injuries-with-blood.png',rows=len(injury_rows),rowOrder='canonical state then source frame',dmi='injuries-with-blood.dmi')
    (folder/'metadata.json').write_text(json.dumps(metadata,indent=2))
    common=dict(race=body['label'],columns=4,directionOrder=DIRECTIONS,status='actual-pixel-cutout draft',
                provenance='Actual approved body64 pixels, unchanged colors and alpha; no AI redraw or invented hidden limb.',
                reconstruction=metadata['reconstruction'])
    manifest=[dict(common,id=body['id']+'-parts',category='detached',label=body['label']+' · original-pixel limbs',path=str((folder/'parts.png').resolve()),rows=len(part_rows),rowLabels=[slot+':frame'+str(f) for slot in SLOTS for f in range(len(frames))],sourceRects=rectangles(len(part_rows))),
              dict(common,id=body['id']+'-injury',category='injury',label=body['label']+' · limb-loss states',path=str((folder/'injuries.png').resolve()),rows=len(injury_rows),rowLabels=[name+':frame'+str(f) for _,name in STATES for f in range(len(frames))],sourceRects=rectangles(len(injury_rows)))]
    if wounds:
        manifest.append(dict(common,id=body['id']+'-injury-blood',category='injury',label=body['label']+(' · limb-loss states (bloodless material)' if wound_report['noBloodMaterial'] else ' · limb-loss states with small source-palette blood caps'),path=str((folder/'injuries-with-blood.png').resolve()),rows=len(injury_rows),rowLabels=[name+':frame'+str(f) for _,name in STATES for f in range(len(frames))],sourceRects=rectangles(len(injury_rows)),wounds=wound_report,
                             provenance='Actual approved body64 pixel cutouts; only separate4px source-palette wound caps are added. Stone and Skeleton remain bloodless.'))
    return manifest,summary


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    group=parser.add_mutually_exclusive_group()
    group.add_argument('--only',default=None,help='Comma-separated body IDs; default: human')
    group.add_argument('--all',action='store_true',help='Export all registered bodies after reviewing the Human cut geometry')
    parser.add_argument('--registry',type=Path,default=REGISTRY)
    parser.add_argument('--output',type=Path,default=HERE/'pixel-assets')
    parser.add_argument('--no-wounds',action='store_true',help='Export pure source-pixel cutouts only, even if wound_pixels.py is available')
    args=parser.parse_args()
    registry=json.loads(args.registry.read_text());bodies=registry['bodies']
    if not args.all:
        selected=set((args.only or 'human').split(','));known={body['id'] for body in bodies}
        if selected-known:raise ValueError('Unknown body IDs: '+','.join(sorted(selected-known)))
        bodies=[body for body in bodies if body['id'] in selected]
    cutter=importlib.import_module('pixel_cutter')
    wounds=None
    if not args.no_wounds:
        try:wounds=importlib.import_module('wound_pixels')
        except ModuleNotFoundError as error:
            if error.name!='wound_pixels':raise
    args.output.mkdir(parents=True,exist_ok=True);manifest=[];reports=[]
    for body in bodies:
        entries,report=pack_body(body,cutter,args.output,wounds=wounds);manifest.extend(entries);reports.append(report)
        print('Packed '+body['id']+': '+str(report['injuryViewsChecked'])+' injury views; exact pixel reconstruction',flush=True)
    (args.output/'manifest.json').write_text(json.dumps(manifest,indent=2))
    summary=dict(bodies=len(reports),bodyIds=[report['id'] for report in reports],
                 injuryViewsChecked=sum(report['injuryViewsChecked'] for report in reports),
                 exactRGBAReconstruction=True,overlappingPixels=0,outsideMaskChangedPixels=0,
                 geometryApproval=False,animationsEncoded=True,woundCaps=bool(wounds),
                 outsideCapAndRemovedMaskChangedPixels=0,reports=reports)
    (args.output/'verification.json').write_text(json.dumps(summary,indent=2))
    temporary=HERE/'manifest.pixel-tmp.json';temporary.write_text(json.dumps(manifest,indent=2));temporary.replace(HERE/'manifest.json')
    print(json.dumps({key:value for key,value in summary.items() if key!='reports'}))


if __name__=='__main__':main()
