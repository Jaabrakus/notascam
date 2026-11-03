#!/usr/bin/env python3
"""Technical cutouts and two original-height exports FROM detailed artwork.

No generation, RGB repaint, creative filtering, or modification to large plates.
Automatic crop proposals remain subject to the worker's visual review.
"""
import argparse
from collections import deque, Counter
import hashlib
import json
from pathlib import Path
import re

import numpy as np
from PIL import Image, ImageDraw

from extract_existing_sprite import extract
from export_sprite_height import export_height
from validate_dmi import load_asset

BASE = Path(__file__).resolve().parents[1]
REPO = BASE.parents[2]
ART = BASE / 'detailed-artwork'
VERSION = 'detailed-original-height-1.0'


def components(alpha):
    seen = np.zeros(alpha.shape, bool)
    result = []
    height, width = alpha.shape
    for y, x in zip(*np.nonzero(alpha)):
        if seen[y, x]:
            continue
        seen[y, x] = True
        todo = deque([(y, x)])
        xs, ys = [], []
        while todo:
            py, px = todo.popleft()
            xs.append(px); ys.append(py)
            for dy, dx in ((-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)):
                ny, nx = py + dy, px + dx
                if 0 <= ny < height and 0 <= nx < width and alpha[ny,nx] and not seen[ny,nx]:
                    seen[ny,nx] = True; todo.append((ny,nx))
        result.append({'area': len(xs), 'box': [int(min(xs)),int(min(ys)),int(max(xs)+1),int(max(ys)+1)],
                       'center': [float(np.mean(xs)),float(np.mean(ys))]})
    return result


def propose_page(page, family, export_root):
    """Propose first-facing boxes using retained components, area-weighted rows."""
    source = ART / page['path']
    with Image.open(source) as image:
        width, height = image.size
    band_box = (int(width*.26), int(height*.035), int(width*.49), height)
    band_path = export_root / '_layout' / family / ('page-%02d-band.png' % page['page'])
    if not band_path.exists():
        extract(source, band_box, band_path)
    band = np.asarray(Image.open(band_path).convert('RGBA'))[4:-4,4:-4]
    comp = components(band[:,:,3] > 0)
    eligible = []
    for c in comp:
        c = dict(c)
        c['box'] = [c['box'][0]+band_box[0],c['box'][1]+band_box[1],
                    c['box'][2]+band_box[0],c['box'][3]+band_box[1]]
        c['center'] = [c['center'][0]+band_box[0],c['center'][1]+band_box[1]]
        if .30*width <= c['center'][0] <= .455*width and c['area'] >= 2:
            eligible.append(c)
    count = len(page['states'])
    major = [c for c in eligible if c['area'] >= max(15, width*height*.000015)]
    if len(major) < count:
        raise ValueError('Insufficient components for page rows: '+str(source))
    centers = np.linspace(height*.11, height*.92, count)
    for _ in range(30):
        assignments = [int(np.argmin(np.abs(centers-c['center'][1]))) for c in major]
        new = centers.copy()
        for i in range(count):
            group = [c for c,k in zip(major,assignments) if k==i]
            if group:
                new[i] = np.average([c['center'][1] for c in group],weights=[c['area'] for c in group])
        if np.max(np.abs(new-centers)) < .05:
            break
        centers = new
    centers.sort()
    boxes = {}
    details = {}
    for i, index in enumerate(page['state_indices']):
        low = 0 if i == 0 else (centers[i-1]+centers[i])/2
        high = height if i == count-1 else (centers[i]+centers[i+1])/2
        group = [c for c in eligible if low <= c['center'][1] < high]
        if not group:
            raise ValueError('No component for '+page['states'][i])
        main = max(group, key=lambda c:c['area'])
        pitch = min(centers[i]-centers[i-1] if i else height/count,
                    centers[i+1]-centers[i] if i+1<count else height/count)
        selected = []
        mb = main['box']
        for c in group:
            cb = c['box']
            dx = max(mb[0]-cb[2],cb[0]-mb[2],0)
            dy = max(mb[1]-cb[3],cb[1]-mb[3],0)
            if dx <= width*.035 and dy <= pitch*.18:
                selected.append(c)
        box = [max(band_box[0],min(c['box'][0] for c in selected)-2),
               max(0,min(c['box'][1] for c in selected)-2),
               min(band_box[2],max(c['box'][2] for c in selected)+2),
               min(height,max(c['box'][3] for c in selected)+2)]
        boxes[index] = box
        details[index] = {'row_center': float(centers[i]), 'selected_components': selected,
                          'rule': 'Area-weighted Y clusters; largest body plus nearby detached components'}
    return boxes, details


def occupied_reference(asset, state):
    w,h=asset.metadata.width,asset.metadata.height
    columns=asset.image.width//w
    for offset in range(state.directions*state.frames):
        cell=state.start_cell+offset
        x,y=(cell%columns)*w,(cell//columns)*h
        if asset.image.crop((x,y,x+w,y+h)).getchannel('A').getbbox():
            return cell
    raise ValueError('State has no occupied native facing: '+state.name)


def export_one(source, box, cutout, output, native, cell):
    if not cutout.exists():
        audit=extract(source,box,cutout)
    else:
        audit=json.loads(cutout.with_suffix('.cutout.json').read_text())
        if audit['crop_box'] != list(box):
            raise ValueError('Existing cutout crop differs; use a new output root')
    if not output.exists():
        try:
            report=export_height(cutout,output,native_source=native,cell_index=cell)
        except ValueError as error:
            if 'Resizing lost sparse top/bottom pixels' not in str(error):
                raise
            report=export_height(cutout,output,native_source=native,cell_index=cell,method='lanczos')
    else:
        report=output.with_suffix('.export.json')
    info=json.loads(Path(report).read_text())
    image=Image.open(output).convert('RGBA');bbox=image.getchannel('A').getbbox()
    ref=info['native_reference']
    if bbox[3]-bbox[1] != ref['visible_height'] or bbox[3] != ref['bottom_baseline_exclusive']:
        raise ValueError('Native height or baseline mismatch')
    return {'path':str(output),'report':str(report),'sha256':hashlib.sha256(output.read_bytes()).hexdigest(),
            'size':list(image.size),'alpha_bbox':list(bbox),'visible_height':bbox[3]-bbox[1],
            'baseline_exclusive':bbox[3],'native_reference':ref,'resample':info['output']['resample'],
            'visible_height_exact':True,'baseline_exact':True,'drop_in_overlay':False},audit


def export_family(family, output_root=None, overrides=None):
    """Export family; overrides maps integer or string native state index to box.

    Output status is pending_visual_review until the worker checks its contact
    montages. Each worker owns only its assigned family report and outputs.
    """
    root=Path(output_root) if output_root else ART/'exports'
    manifest=json.loads((ART/'manifest.json').read_text())
    pages=[x for x in manifest['gear_pages'] if x['family']==family]
    if not pages:
        raise ValueError('Unknown detailed family: '+family)
    overrides={int(k):v for k,v in (overrides or {}).items()}
    native_root=REPO/'standalone/remastered/game/Icons/Remastered'
    inventory_path=native_root/'Gear'/(family+'.dmi')
    player_path=native_root/'Gear64/Human'/(family+'.dmi')
    inventory=load_asset(inventory_path.read_bytes(),str(inventory_path))
    player=load_asset(player_path.read_bytes(),str(player_path))
    used_names=Counter();results=[]
    report={'version':VERSION,'family':family,'classification':'game_height_exports_from_detailed_artwork',
            'status':'in_progress','new_artwork_generated':False,'source_large_plates_unchanged':True,
            'drop_in_overlay':False,'states':results}
    report_path=root/'reports'/(family+'.json');report_path.parent.mkdir(parents=True,exist_ok=True)
    for page in pages:
        required=[i for i in page['state_indices'] if i not in overrides]
        boxes,details=propose_page(page,family,root) if required else ({},{})
        for index,name in zip(page['state_indices'],page['states']):
            state=inventory.metadata.states[index]
            if json.loads(state.name) != name:
                raise ValueError('Inventory ordered state name mismatch')
            occurrence=used_names[name];used_names[name]+=1
            matches=[s for s in player.metadata.states if json.loads(s.name)==name]
            if len(matches)<=occurrence:
                raise ValueError('Missing player state '+name)
            pstate=matches[occurrence]
            inv_cell=occupied_reference(inventory,state);player_cell=occupied_reference(player,pstate)
            slug='%03d-'%index+re.sub(r'[^A-Za-z0-9._-]+','_',name)
            cutout=root/'source-cutouts'/family/(slug+'.png')
            box=overrides.get(index,boxes.get(index))
            source=ART/page['path']
            inv,audit=export_one(source,box,cutout,root/'game-height/inventory'/family/(slug+'.png'),inventory_path,inv_cell)
            worn,_=export_one(source,box,cutout,root/'game-height/player'/family/(slug+'.png'),player_path,player_cell)
            src=np.asarray(Image.open(source).convert('RGBA').crop(box))
            rgba=np.asarray(Image.open(cutout).convert('RGBA'))[4:-4,4:-4]
            keep=rgba[:,:,3]>0
            exact=bool(np.array_equal(src[keep,:3],rgba[keep,:3]))
            if not exact:
                raise ValueError('Source RGB changed in cutout')
            results.append({'state_index':index,'state_name':name,'same_name_occurrence':occurrence,
                            'source_plate':str(source),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
                            'crop_box':list(box),'crop_method':'explicit_review_override' if index in overrides else 'automatic_proposal',
                            'crop_detection':details.get(index),'source_cutout':str(cutout),
                            'extraction':audit,'source_resolution_retained_rgb_exact':exact,
                            'inventory':inv,'player':worn,'visual_review':'pending'})
            report_path.write_text(json.dumps(report,indent=2)+'\n')
    report['status']='exported_pending_visual_review';report['state_count']=len(results)
    report['cutout_count']=len(results);report['height_export_count']=len(results)*2
    report_path.write_text(json.dumps(report,indent=2)+'\n')
    # Native-size inventory and worn designs, displayed at 3x on a gray backdrop.
    cols=6;tilew,tileh=210,250;rows=(len(results)+cols-1)//cols
    preview=Image.new('RGB',(cols*tilew,rows*tileh),(165,165,165));draw=ImageDraw.Draw(preview)
    for i,r in enumerate(results):
        x,y=(i%cols)*tilew,(i//cols)*tileh
        draw.text((x+4,y+3),str(r['state_index'])+' '+r['state_name'][:28],fill='black')
        for k,key in enumerate(['inventory','player']):
            im=Image.open(r[key]['path']).convert('RGBA');bbox=im.getchannel('A').getbbox();im=im.crop(bbox)
            im=im.resize((im.width*3,im.height*3),Image.Resampling.NEAREST)
            preview.paste(im,(x+4+k*100,y+25),im)
    pp=root/'review'/(family+'-native3x.png');pp.parent.mkdir(parents=True,exist_ok=True);preview.save(pp)
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--family',required=True)
    parser.add_argument('--output-root',type=Path)
    parser.add_argument('--overrides',type=Path,help='JSON mapping native inventory state indices to explicit xyxy boxes')
    args=parser.parse_args()
    overrides=json.loads(args.overrides.read_text()) if args.overrides else None
    r=export_family(args.family,args.output_root,overrides)
    print(json.dumps({'family':r['family'],'status':r['status'],'states':r['state_count']}))
