#!/usr/bin/env python3
"""Build additive body/VFX sheets and zero-redraw ki recipes from approved poses."""
from pathlib import Path
import importlib.util
import hashlib
import json
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'Dungeon Master Sample/GOA Orc Base Animation Sprites/ki-movement-v1'
APPROVED = OUT.parent / 'curated-attacks-v1'
spec = importlib.util.spec_from_file_location('curate', Path(__file__).with_name('curate_orc_attacks.py'))
curate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(curate)
BODY = {
    'ki_charge': ('Power charge', ['Guard', 'Brace', 'Power up', 'Sustain'], [180, 180, 250, 250], [0,0,0,0]),
    'ki_blast': ('Open-palm blast', ['Guard', 'Draw back', 'Release', 'Recoil'], [140, 120, 100, 180], [0,0,0,0]),
    'ki_beam': ('Two-hand energy wave', ['Guard', 'Cup hands', 'Release', 'Sustain'], [180, 350, 160, 500], [0,0,0,0]),
    'jump': ('Jump', ['Crouch', 'Takeoff', 'Apex', 'Descent'], [180, 140, 220, 160], [0,-6,-12,-6]),
    'land': ('Landing', ['Descent', 'Contact', 'Absorb', 'Guard'], [140, 100, 140, 200], [-6,0,0,0])}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def phase(sheet, row, label, duration=140, effect=None, offset=0):
    return {'sheet': sheet, 'row': row, 'label': label, 'ms': duration,
            'effect': effect, 'rootOffsetY': offset}


def main():
    (OUT / 'frames').mkdir(exist_ok=True)
    (OUT / 'effects').mkdir(exist_ok=True)
    before = json.loads((OUT / 'approved-frame-hashes.json').read_text())
    assert before == {p.name: digest(p) for p in (APPROVED / 'frames').glob('*.png')}
    palette = curate.palette_from_original()
    recipes, records = [], []
    pr, pl = '../curated-attacks-v1/punch_right.png', '../curated-attacks-v1/punch_left.png'
    for side, sheet in [('right', pr), ('left', pl)]:
        recipes.append({'id': 'rapid_' + side, 'name': side.title() + ' fist blast', 'group': 'reuse',
                        'reusesApprovedPixels': True, 'hand': side,
                        'phases': [phase(sheet, i, label, ms, 'projectile' if i == 2 else None)
                                   for i, (label, ms) in enumerate(zip(['Guard','Windup','Release','Recover'], [100,100,100,120]))]})
    alternating = []
    for side, sheet in [('right', pr), ('left', pl)]:
        for i, label in enumerate(['Guard','Windup','Release','Recover']):
            item = phase(sheet, i, side.title() + ' · ' + label, 100, 'projectile' if i == 2 else None)
            item['hand'] = side
            alternating.append(item)
    recipes.append({'id': 'rapid_alternating', 'name': 'Alternating ki volley', 'group': 'reuse',
                    'reusesApprovedPixels': True, 'phases': alternating})
    recipes.append({'id': 'held_blast', 'name': 'Held extended-arm blast', 'group': 'reuse',
                    'reusesApprovedPixels': True, 'hand': 'right',
                    'phases': [phase(pr, 2, 'Hold extended pose', 160, 'beam') for _ in range(4)]})
    recipes.append({'id': 'standing_charge', 'name': 'Standing aura charge', 'group': 'reuse',
                    'reusesApprovedPixels': True,
                    'phases': [phase(pr, 0, 'Hold guard · aura pulse', 180, 'aura') for _ in range(4)]})
    for action, (name, labels, durations, offsets) in BODY.items():
        raw = OUT / 'drawings' / (action + '.png')
        source = curate.extract(raw)
        curate.SCALE = .205 * 1448 / Image.open(raw).width
        sheet = Image.new('RGBA', (320, 320))
        for row in range(4):
            for direction, facing in enumerate(curate.DIRECTIONS):
                shared = (action.startswith('ki_') and row == 0) or (action == 'land' and row == 3)
                frame = (Image.open(APPROVED / 'frames' / f'punch_right-{facing}-0.png').convert('RGBA')
                         if shared else curate.register(source[row, direction], palette))
                # Root translation stays separate from anatomy. Gameplay can supply its own trajectory.
                frame.save(OUT / 'frames' / f'{action}-{facing}-{row}.png')
                sheet.paste(frame, (80 * direction, 80 * row))
                a = np.asarray(frame)
                assert set(np.unique(a[:, :, 3])) <= {0,255}
                assert frame.getbbox()
                records.append({'action': action, 'direction': facing, 'phase': row,
                                'file': f'frames/{action}-{facing}-{row}.png', 'sharedGuard': shared,
                                'previewRootOffsetY': offsets[row]})
        sheet.save(OUT / (action + '.png'))
        phases = []
        for row in range(4):
            effect = ('aura' if action == 'ki_charge' and row >= 1 else
                      'projectile' if action == 'ki_blast' and row == 2 else
                      'beam' if action == 'ki_beam' and row >= 2 else None)
            phases.append(phase(action + '.png', row, labels[row], durations[row], effect, offsets[row]))
        recipes.append({'id': action, 'name': name, 'group': 'movement' if action in ['jump','land'] else 'new_ki',
                        'reusesApprovedPixels': False, 'status': 'new_drawing_review', 'hand': 'right', 'phases': phases})
    jump = next(r for r in recipes if r['id'] == 'jump')
    landing = next(r for r in recipes if r['id'] == 'land')
    recipes.append({'id':'jump_land','name':'Complete jump and landing','group':'movement',
                    'reusesApprovedPixels':False,'status':'new_drawing_review',
                    'phases':jump['phases'] + landing['phases'][1:]})
    # Pack separately drawn effects; keep them out of every body image.
    source = Image.open(OUT / 'drawings/effects.png').convert('RGBA')
    a = np.asarray(source)
    # Discard the generated low-opacity glow. Keep solid pixel clusters only.
    effect_alpha_cutoff = 200
    rows = curate.bands(a[:, :, 3] > effect_alpha_cutoff)
    assert len(rows) == 4, rows
    colors = np.array([[245,255,255], [151,245,255], [40,214,248], [25,124,230], [25,54,128]], dtype=np.int32)
    effects = {}
    columns = [0, round(source.width*.31), round(source.width*.59), source.width]
    for col, (kind, size) in enumerate([('aura',(64,80)),('projectile',(32,24)),('beam',(128,32))]):
        atlas = Image.new('RGBA', (size[0], size[1] * 4))
        crops = []
        for row, (top, bottom) in enumerate(rows):
            crop = source.crop((columns[col], top, columns[col+1], bottom))
            data = np.asarray(crop); y, x = np.where(data[:, :, 3] > effect_alpha_cutoff)
            crop = crop.crop((int(x.min()),int(y.min()),int(x.max())+1,int(y.max())+1))
            crops.append(crop)
        ratio = min((size[0]-2)/max(c.width for c in crops), (size[1]-2)/max(c.height for c in crops))
        for row, crop in enumerate(crops):
            crop = crop.resize((max(1,round(crop.width*ratio)),max(1,round(crop.height*ratio))), Image.Resampling.NEAREST)
            data = np.asarray(crop).copy(); rgb = data[:, :, :3].astype(np.int32)
            nearest = ((rgb[:, :, None]-colors[None,None])**2).sum(axis=3).argmin(axis=2)
            data[:, :, :3] = colors[nearest]; data[:, :, 3] = np.where(data[:, :, 3]>effect_alpha_cutoff,255,0)
            data[data[:,:,3]==0,:3] = 0
            x = 1 if kind == 'beam' else (size[0]-crop.width)//2
            y = size[1]-crop.height-1 if kind == 'aura' else (size[1]-crop.height)//2
            cell = Image.new('RGBA',size); cell.paste(Image.fromarray(data),(x,y))
            cell.save(OUT/'effects'/f'{kind}-{row}.png');atlas.paste(cell,(0,row*size[1]))
        atlas.save(OUT/'effects'/f'{kind}.png')
        effects[kind] = {'sheet':f'effects/{kind}.png','width':size[0],'height':size[1],'frames':4}
    contact = Image.new('RGB', (680, 970), '#444951')
    draw = ImageDraw.Draw(contact)
    for ai, (action, (name, labels, _, _)) in enumerate(BODY.items()):
        y = ai * 194
        draw.text((12, y + 5), name, fill='white')
        for row, label in enumerate(labels):
            frame = Image.open(OUT/'frames'/f'{action}-south-{row}.png').resize((160,160), Image.Resampling.NEAREST)
            contact.paste(frame, (row*170, y+20), frame)
            draw.text((row*170+12,y+179),label,fill='#d9e5cf')
    contact.save(OUT/'front-body-contact-sheet.png')
    data = {'cellSize':80,'directions':curate.DIRECTIONS,'recipes':recipes,'bodyFrames':records,'effects':effects,
            'status':'review_not_integrated','sourceHashes':{p.name:digest(p) for p in (OUT/'drawings').glob('*.png')},
            'approvedFramesUnchanged':64,'newBodyFrameCells':len(records),'effectFrameCells':12,
            'note':'Timings, effect hand anchors and root offsets are preview values, not gameplay physics.'}
    curate.annotate_appearance(data)
    (OUT/'manifest.json').write_text(json.dumps(data,indent=2)+'\n')
    (OUT/'catalog.js').write_text('window.ORC_KI_CATALOG = '+json.dumps(data)+';\n')
    assert before == {p.name:digest(p) for p in (APPROVED/'frames').glob('*.png')}
    print(f'Built {len(records)} body cells, 12 separate effect cells and {len(recipes)} animation recipes. Approved 64 cells unchanged.')


if __name__ == '__main__':
    main()
