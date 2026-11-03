#!/usr/bin/env python3
"""One native-pixel body cycle, shared attachment points, interchangeable gear."""
from pathlib import Path
import hashlib
import importlib.util
import json
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[3]
ART = ROOT / 'Dungeon Master Sample/GOA Orc Base Animation Sprites'
OUT = ART / 'thrust-foundation-v1'
spec = importlib.util.spec_from_file_location('curate', Path(__file__).with_name('curate_orc_attacks.py'))
curate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(curate)
CELL, OFFSET = 128, 24
DIRS = curate.DIRECTIONS
LABELS = ['Ready', 'Pull back', 'Short thrust', 'Recover']

def blank():
    return Image.new('RGBA', (CELL, CELL))

def hard(im):
    a = np.array(im.convert('RGBA'))
    a[:, :, 3] = np.where(a[:, :, 3] >= 128, 255, 0)
    a[a[:, :, 3] == 0, :3] = 0
    return Image.fromarray(a)

def source_frames():
    im = Image.open(OUT / 'drawings/body-source.png').convert('RGBA')
    a = np.array(im)
    a[:, :, 3] = np.where(a[:, :, 3] >= 240, 255, 0)
    a[a[:, :, 3] == 0, :3] = 0
    im = Image.fromarray(a)
    curate.SCALE = .205 * 1448 / im.width
    frames = {}
    for phase, (top, bottom) in enumerate([(0, 287), (287, 527), (527, 765), (765, 1024)]):
        for d in range(4):
            tile = im.crop((d * 384, top, (d + 1) * 384, bottom))
            frames[phase, d] = curate.register(tile.crop(tile.getbbox()), curate.palette_from_original())
    return frames

def bodies(raw):
    from orc_elbow_poke import build_bodies
    return build_bodies(OUT)

def weapon(kind, direction):
    im = Image.open(OUT / 'equipment' / (kind + '.png')).convert('RGBA')
    if kind == 'sword':
        im = im.crop((0, 0, 14, 30)); grip = (7, 24)
    else:
        grip = (4, 40)
    im = hard(im)
    if direction == 2:
        return im.transpose(Image.Transpose.ROTATE_270), (im.height - 1 - grip[1], grip[0])
    if direction == 3:
        return im.transpose(Image.Transpose.ROTATE_90), (grip[1], im.width - 1 - grip[0])
    # Fixed foreshortened directional view, reused unchanged through every phase.
    height = 16 if kind == 'sword' else 32
    grip = (grip[0], round(grip[1] * height / im.height))
    im = im.resize((im.width, height), Image.Resampling.NEAREST)
    if direction == 0:
        im = im.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
        grip = (grip[0], height - 1 - grip[1])
    return im, grip

def main():
    raw = source_frames(); body = bodies(raw)
    for d in range(4):
        ready=np.asarray(body[0,d])
        assert body[3,d].tobytes()==body[0,d].tobytes()
        for phase in range(4):
            current=np.asarray(body[phase,d])
            assert np.array_equal(current[:43],ready[:43]), ('head drift',d,phase)
            assert np.array_equal(current[58:],ready[58:]), ('leg drift',d,phase)
    for name in ['frames', 'layers', 'sheets']:
        (OUT / name).mkdir(exist_ok=True)
    # Native coordinates before the fixed 24px export padding.
    from orc_elbow_poke import HANDS
    hands = HANDS
    shield_centers = [(51,51),(27,51),(53,51),(42,51)]
    atlases = {key: Image.new('RGBA', (CELL*4, CELL*4)) for key in
               ['body', 'sword', 'spear', 'shield-rear', 'shield-front',
                'sword-rear','sword-front','spear-rear','spear-front']}
    records = []
    for phase in range(4):
        for d, direction in enumerate(DIRS):
            base = blank(); base.paste(body[phase,d], (OFFSET, OFFSET))
            x, y = (hands[d][phase][0]+OFFSET, hands[d][phase][1]+OFFSET)
            shield = hard(Image.open(OUT/'equipment'/f'{"SNEW"[d]}-shield.png'))
            shield_layer = blank(); sx, sy = shield_centers[d]
            shield_layer.alpha_composite(shield, (sx+OFFSET-shield.width//2, sy+OFFSET-shield.height//2))
            rear_shield, front_shield = (shield_layer, blank()) if d == 2 else (blank(), shield_layer)
            layers = {'body':base, 'shield-rear':rear_shield, 'shield-front':front_shield}
            for kind in ['sword','spear']:
                gear, grip = weapon(kind,d)
                gear_layer = blank(); gear_layer.alpha_composite(gear,(x-grip[0],y-grip[1]))
                # Far weapon arm passes behind the torso. Near grips cover only
                # the handle where the existing closed hand occludes equipment.
                rear, front = (gear_layer,blank()) if d in (1,3) else (blank(),gear_layer)
                if d in (0,2):
                    a = np.array(front)
                    b = np.array(base)
                    region = np.zeros(a.shape[:2],dtype=bool)
                    region[y-3:y+4,x-3:x+4] = True
                    a[region & (b[:,:,3]>0)] = 0
                    front = Image.fromarray(a)
                composed = Image.alpha_composite(rear_shield,rear)
                composed = Image.alpha_composite(composed,base)
                composed = Image.alpha_composite(composed,front)
                composed = Image.alpha_composite(composed,front_shield)
                layers[kind+'-rear'] = rear; layers[kind+'-front'] = front; layers[kind] = composed
            for name,im in layers.items():
                atlas = atlases[name];atlas.paste(im,(d*CELL,phase*CELL))
                filename = f'{name}-{direction}-{phase}.png'
                im.save(OUT/('frames' if name in ('body','sword','spear') else 'layers')/filename)
                a=np.asarray(im)
                assert set(np.unique(a[:,:,3])) <= {0,255}
                assert not (a[0,:,3].any() or a[-1,:,3].any() or a[:,0,3].any() or a[:,-1,3].any())
            records.append({'direction':direction,'phase':phase,'grip':[x,y],
                'shieldAnchor':[sx+OFFSET,sy+OFFSET],'body':f'frames/body-{direction}-{phase}.png',
                'rect':[d*CELL,phase*CELL,CELL,CELL]})
    for name,im in atlases.items():im.save(OUT/'sheets'/f'{name}.png')
    prior=json.loads((OUT/'prior-frame-hashes.json').read_text())
    assert all(hashlib.sha256((ART/p).read_bytes()).hexdigest()==h for p,h in prior.items())
    # Readable impact comparison: same phase and body across all equipment choices.
    contact=Image.new('RGB',(1000,830),'#444951');draw=ImageDraw.Draw(contact)
    for row,name in enumerate(['body','sword','spear']):
        draw.text((10,row*275+8),name.upper(),fill='white')
        for d,direction in enumerate(DIRS):
            im=atlases[name].crop((d*CELL,2*CELL,(d+1)*CELL,3*CELL)).resize((256,256),Image.Resampling.NEAREST)
            contact.paste(im,(d*250,row*275+20),im)
            draw.text((d*250+10,row*275+25),direction,fill='white')
    contact.save(OUT/'comparison.png')
    manifest={'status':'pose_review_not_game_integrated','cellSize':CELL,'bodyOffset':[OFFSET,OFFSET],
        'directions':DIRS,'labels':LABELS,'durations':[260,130,140,220],'frames':records,
        'sheets':{name:'sheets/'+name+'.png' for name in atlases},
        'equipmentLayersSeparate':True,'bodySharedAcrossEquipment':True,
        'sources':{'body':'drawings/elbow-poke.png','prompt':'prompts/elbow-poke.txt','equipment':'equipment/sources.json'},
        'checks':{'priorFramesUnchanged':len(prior),'binaryAlpha':True,'noClipping':True,'recoveryCopiesReady':True,'headAndLegsLocked':True},
        'notes':'One-handed thrust review. Fixed equipment pixels and hand sockets; no reach/hitboxes or game integration. Drawn bent-elbow and opening-elbow poses; static head, legs and guard regions copied from the prior body. Equipment follows revised grips.'}
    curate.annotate_appearance(manifest)
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (OUT/'catalog.js').write_text('window.THRUST_FOUNDATION='+json.dumps(manifest)+';\n')
    print(f'Built 16 body poses, separate equipment layers and 32 equipped comparisons; {len(prior)} prior frames unchanged.')

if __name__=='__main__':main()
