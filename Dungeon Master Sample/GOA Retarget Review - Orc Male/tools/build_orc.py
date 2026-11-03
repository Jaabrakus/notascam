#!/usr/bin/env python3
"""Build the Orc review package from the pack Orc sheet, using the same pipeline as the approved Human.

    python3 build_orc.py            (from anywhere; paths are absolute to the Dungeon-Master-master repository)

Steps, in order:
 1. Stage inputs: pack sheet Sprites/Male/Orc/base/sprites.png, staged fine zones and joints for Orc.
 2. Zone fix (Orc only, recorded in zone-fix.json): the staged side-view zones label the top of the near arm
    (deltoid down to the elbow, about 8 rows) as chest, so the cut side arm would start at the elbow. On the idle
    East/West cells, chest pixels on the arm's side of its front contour, from two rows under the torso top down to
    the arm zone, become "shoulder" of that arm. Walk frames are left as staged. fine.png keeps its original copy.
 3. standalone/goa-races/character-retarget/retarget.py into a fresh folder (refuses to overwrite).
 4. source/engine.js = the approved Human renderer (source pivots, lead leg, North draw orders as approved 10-31)
    plus tools/patch_engine.py: a profile flag (bowSideBody) that draws the side-view bow on the body's own
    East/West drawing instead of the South body with a side head.
 5. recut_by_zones.py: joints from the staged skeleton (inputs/Orc.json); arms, legs and the side torso recut from
    the Orc's own zones with original pixels only. Guard grips = the draft's.
 6. Bow targets: front/back fitted by arm reach around the neck (the pipeline's shoulder-width fit puts a broad
    body's bow hand off the canvas); West on the West body (East = its reflection).
 7. Rebuild, then replace the previous Orc folder (the old one goes to the Trash).
"""
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import time

import numpy as np
from PIL import Image

ROOT = '/Users/kiwimango/Downloads/Dungeon-Master-master'
SAMPLE = os.path.join(ROOT, 'Dungeon Master Sample')
STAGED = os.path.join(ROOT, 'standalone/remastered/reports/goa-sprite-test/staged')
PIPE = os.path.join(ROOT, 'standalone/goa-races/character-retarget')
APPROVED_HUMAN = os.path.join(SAMPLE, 'GOA Retarget Review - Human Male')
OUT = os.path.join(SAMPLE, 'GOA Retarget Review - Orc Male')
WORK = os.path.dirname(os.path.abspath(__file__))
INPUTS = os.path.join(WORK, 'orc-inputs')
ELF_REACH = 15.32
BOW_SIDE_BODY = False   # True: East/West archery drawn on the side body (gated renderer patch); False: approved construction
ELF_NECK_S = [32, 25]
ELF_BOW = [dict(bow=[38, 32], nock=[32, 32], cheek=[28, 29], flung=[26, 28]),
           dict(bow=[26, 31], nock=[31, 31], cheek=[36, 30], flung=[38, 29]),
           dict(bow=[54, 28], nock=[45, 28], cheek=[36, 27], flung=[32, 26]),
           dict(bow=[9, 28], nock=[18, 28], cheek=[27, 27], flung=[29, 28])]


def stage_inputs():
    if os.path.isdir(INPUTS):
        shutil.rmtree(INPUTS)
    os.makedirs(INPUTS)
    shutil.copyfile(os.path.join(SAMPLE, 'Sprites/Male/Orc/base/sprites.png'), os.path.join(INPUTS, 'sprites.png'))
    for f in ('fine.png', 'fine.json'):
        shutil.copyfile(os.path.join(STAGED, 'rig/finezones/Orc', f), os.path.join(INPUTS, f))
    shutil.copyfile(os.path.join(STAGED, 'rig/Orc.json'), os.path.join(INPUTS, 'Orc.json'))
    shutil.copyfile(os.path.join(INPUTS, 'fine.png'), os.path.join(INPUTS, 'fine-staged-original.png'))


def fix_side_shoulders():
    names = json.load(open(os.path.join(INPUTS, 'fine.json')))['zones']
    zim = Image.open(os.path.join(INPUTS, 'fine.png'))
    pal = zim.getpalette()
    z = np.array(zim.convert('P') if zim.mode != 'P' else zim)
    idx = {n: i for i, n in enumerate(names)}
    torso = [idx['neck'], idx['chest'], idx['belly']]
    record = []
    for d, side in [(2, 'R'), (3, 'L')]:   # idle East: near arm = right; idle West: near arm = left
        c = z[0:64, d * 64:(d + 1) * 64]
        arm = np.isin(c, [idx[f'{p} {side}'] for p in ('shoulder', 'upper arm', 'forearm', 'hand')])
        rows = np.nonzero(arm.any(1))[0]
        arm_top = int(rows.min())
        top3 = arm[arm_top:arm_top + 3]
        xs = np.nonzero(top3.any(0))[0]
        body = np.isin(c, torso)
        body_cols = np.nonzero(body.any(0))[0]
        arm_low = xs.mean() < (body_cols.min() + body_cols.max()) / 2   # arm on the low-x side of the body
        edge = int(xs.max()) if arm_low else int(xs.min())
        torso_top = int(np.nonzero(np.isin(c, [idx['chest']]).any(1))[0].min())
        changed = 0
        for y in range(torso_top + 2, arm_top):
            for x in range(64):
                if c[y, x] == idx['chest'] and ((x <= edge) if arm_low else (x >= edge)):
                    c[y, x] = idx[f'shoulder {side}']
                    changed += 1
        z[0:64, d * 64:(d + 1) * 64] = c
        record.append({'cell': 'EW'[d - 2] + '0', 'arm': side, 'rows': [torso_top + 2, arm_top - 1],
                       'frontEdgeX': edge, 'pixelsRelabelled': changed,
                       'rule': 'chest pixels on the arm side of its front edge -> shoulder ' + side})
    out = Image.fromarray(z.astype(np.uint8))
    out = out.convert('P') if out.mode != 'P' else out
    out.putpalette(pal)
    out.save(os.path.join(INPUTS, 'fine.png'))
    return record


def fit_bow(profile):
    """Elf bow targets moved to this body's South neck and scaled by its arm reach."""
    views = profile['views']
    reach = lambda chain: sum(math.dist(a, b) for a, b in zip(chain, chain[1:]))
    out = []
    for d in range(4):
        bd = 0 if d >= 2 else d                    # the bow side views are drawn with the South body
        v = views[bd]
        k = sum(reach(c) for c in v['arms'].values()) / 2 / ELF_REACH
        n = v['neck']
        out.append({key: [int(round(n[0] + (p[0] - ELF_NECK_S[0]) * k)), int(round(n[1] + (p[1] - ELF_NECK_S[1]) * k))]
                    for key, p in ELF_BOW[d].items()})
    return out


def fit_side_bow(profile):
    """West bow targets on the West body itself: the far (right) arm holds the bow forward, the near (left) arm
    draws to the jaw. East is the engine's reflection of West, so its targets are the mirror."""
    v = profile['views'][3]
    reach = lambda chain: sum(math.dist(a, b) for a, b in zip(chain, chain[1:]))
    fs, rf = v['arms']['right'][0], reach(v['arms']['right'])
    ns, rn = v['arms']['left'][0], reach(v['arms']['left'])
    bow = [fs[0] - .90 * rf, fs[1] - .08 * rf]        # bow arm forward at shoulder height, almost straight
    nock = [bow[0] + .45 * rf, bow[1] + .5]           # the string at rest
    cheek = [ns[0] - .55 * rn, ns[1] - .10 * rn]      # the drawing hand at the back of the jaw
    flung = [ns[0] - .42 * rn, ns[1] - .20 * rn]      # and a little back and up after the release
    west = {k: [round(pt[0], 2), round(pt[1], 2)] for k, pt in (('bow', bow), ('nock', nock), ('cheek', cheek), ('flung', flung))}
    east = {k: [round(64 - pt[0], 2), pt[1]] for k, pt in west.items()}
    return east, west


def run(cmd, cwd=None):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if r.returncode:
        sys.exit(r.stdout[-3000:] + r.stderr[-3000:])
    return r.stdout


def main():
    stage_inputs()
    zone_fix = fix_side_shoulders()
    tmp_out = OUT + ' (building)'
    if os.path.exists(tmp_out):
        sys.exit('leftover build folder: ' + tmp_out)
    run([sys.executable, os.path.join(PIPE, 'retarget.py'), '--inputs', INPUTS, '--race', 'Orc',
         '--name', 'GOA Orc male', '--output', tmp_out], cwd=ROOT)
    # renderer = the approved Human renderer + the profile-gated side-body bow (tools/patch_engine.py)
    shutil.copyfile(os.path.join(APPROVED_HUMAN, 'source/engine.js'), os.path.join(tmp_out, 'source/engine.js'))
    run([sys.executable, os.path.join(WORK, 'patch_engine.py'), os.path.join(tmp_out, 'source/engine.js')])
    # the package's rebuild.py copies only views/grips/poseTargets into preview/library.json; pass the flag too
    rb = os.path.join(tmp_out, 'rebuild.py')
    text = open(rb).read()
    anchor = "data.update(views=p['views'],grips=p['grips'],poseTargets=p['poseTargets'])"
    if text.count(anchor) != 1:
        sys.exit('rebuild.py anchor not found: ' + anchor)
    open(rb, 'w').write(text.replace(anchor, anchor[:-1] + ",bowSideBody=bool(p.get('bowSideBody')),frontLegsSquash=bool(p.get('frontLegsSquash')),sideHeadOnTop=bool(p.get('sideHeadOnTop')),closePinholes=bool(p.get('closePinholes')),frontHeadOnTop=p.get('frontHeadOnTop') or False,armPose=p.get('armPose'))"))
    run([sys.executable, os.path.join(tmp_out, 'rebuild.py')])
    # Orc limbs and torso recut from the Orc's own zones, original pixels only (replaces the Human arm repair)
    run([sys.executable, os.path.join(WORK, 'recut_by_zones.py'), tmp_out, INPUTS])
    pp = os.path.join(tmp_out, 'profiles/character.json')
    p = json.load(open(pp))
    # guard hands: the grips calibrated for this body in the Orc sword-and-shield draft (its idle hold keeps the
    # arms almost as drawn and raises the fist only a little). The draft's coordinates are in the staged-zone
    # space, two rows below this sheet (zoneRowShift).
    draft = json.load(open(os.path.join(SAMPLE, 'GOA Orc Sword and Shield Draft/rig.json')))['frames']['idle'][0]
    # With the staged skeleton's joints the engine's two-bone IK lands on the draft's own hold pose (elbow within
    # a pixel of the draft's), so the draft's grips are used as they are in every view.
    p['grips'] = []
    for d, fr in enumerate(draft):
        dy = p['zoneRowShift'].get('SNEW'[d] + '0', 0)
        p['grips'].append({'right': [round(fr['swordGrip'][0], 2), round(fr['swordGrip'][1] + dy, 2)],
                           'left': [round(fr['shieldGrip'][0], 2), round(fr['shieldGrip'][1] + dy, 2)]})
    p['keepGrips'] = True
    # Side-view archery as on the approved Elf and Human: the front body with the real East/West head turned to
    # aim. Now that every head piece carries its whole jaw, that head sits on the front torso without the front
    # jaw and tusks showing under it (the "frankenstein turn" the owner rejected). BOW_SIDE_BODY switches to the
    # alternative drawn on the side body itself (tools/patch_engine.py); it is off.
    if BOW_SIDE_BODY:
        front = fit_bow(p)
        east, west = fit_side_bow(p)
        p['poseTargets']['bow'] = [front[0], front[1], east, west]
    else:
        p['poseTargets']['bow'] = fit_bow(p)
    p['bowSideBody'] = BOW_SIDE_BODY
    p['frontLegsSquash'] = True    # front/back legs shorten along the hip-ankle line instead of buckling sideways
    p['sideHeadOnTop'] = True      # East/West: the head over the near arm, so a forward arm passes under the jaw
    p['closePinholes'] = True      # fill enclosed one-pixel seams where separately rotated pieces meet
    p['frontHeadOnTop'] = 4        # South: the head over an arm raised more than 4 px above the neck (wind-ups)
    # front/back views: a raised hand moves outward by half a pixel per pixel of rise, so a wind-up goes up beside this
    # wide head instead of over the face (the shared clip angles pull raised hands toward the head's middle)
    p['armPose'] = [{'spread': 0.5}, {'spread': 0.5}, None, None]
    p['calibration'] = ('joints from the staged Orc skeleton (inputs/Orc.json, 2 rows up); pieces from the Orc own '
                        'zones (tools/recut_by_zones.py); guard grips from the Orc sword-and-shield draft; front/back '
                        'bow targets = Elf targets around the South neck scaled by arm reach; side bow on the side '
                        'body (bowSideBody); renderer = approved Human renderer 2026-10-31 + tools/patch_engine.py')
    json.dump(p, open(pp, 'w'), indent=2)
    json.dump({'status': 'applied', 'source': 'staged rig/finezones/Orc/fine.png',
               'original': 'inputs/fine-staged-original.png', 'changes': zone_fix},
              open(os.path.join(tmp_out, 'zone-fix.json'), 'w'), indent=2)
    os.makedirs(os.path.join(tmp_out, 'tools'), exist_ok=True)
    shutil.copyfile(os.path.abspath(__file__), os.path.join(tmp_out, 'tools/build_orc.py'))
    shutil.copyfile(os.path.join(WORK, 'recut_by_zones.py'), os.path.join(tmp_out, 'tools/recut_by_zones.py'))
    shutil.copyfile(os.path.join(WORK, 'patch_engine.py'), os.path.join(tmp_out, 'tools/patch_engine.py'))
    shutil.copytree(INPUTS, os.path.join(tmp_out, 'inputs'))      # sheet, fixed zones, staged original zones
    run([sys.executable, os.path.join(tmp_out, 'rebuild.py')])
    # keep hand-written review material from the previous build
    if os.path.isdir(OUT):
        for keep in ('README.md', 'README-CLAUDE.md', 'review'):
            src = os.path.join(OUT, keep)
            if os.path.exists(src) and keep != 'README.md':
                dst = os.path.join(tmp_out, keep)
                (shutil.copytree if os.path.isdir(src) else shutil.copyfile)(src, dst)
        if os.path.exists(os.path.join(OUT, 'README-CLAUDE.md')):
            shutil.copyfile(os.path.join(OUT, 'README.md'), os.path.join(tmp_out, 'README.md'))
        trash = os.path.expanduser('~/.Trash/GOA Retarget Review - Orc Male ' + time.strftime('%H%M%S'))
        shutil.move(OUT, trash)
    os.rename(tmp_out, OUT)
    man = {}
    for base, _, files in os.walk(OUT):
        for f in files:
            full = os.path.join(base, f)
            if f != 'manifest.json':
                man[os.path.relpath(full, OUT)] = hashlib.sha256(open(full, 'rb').read()).hexdigest()
    json.dump(dict(sorted(man.items())), open(os.path.join(OUT, 'manifest.json'), 'w'), indent=2)
    print(json.dumps({'output': OUT, 'zoneFix': zone_fix, 'bow': p['poseTargets']['bow']}, indent=1))


if __name__ == '__main__':
    main()
