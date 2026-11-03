"""Reuse AI injury silhouettes on approved hybrid art; export body sheets only.

This is mechanical reuse, not a new AI generation for every palette variant.
Source pixels outside the removed limb masks and small wound caps are preserved.
"""
import json
from pathlib import Path
import sys
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import build as review_geometry
import build_pixel_assets as packing
import pixel_cutter
import wound_pixels

VARIANTS = {'Possessed1', 'Possessed2', 'Marked', 'Ashen', 'Hellblooded', 'Werewolf', 'Zombie'}
SLOTS = packing.SLOTS


def ai_cells(body, category, override_path=None):
    path = Path(override_path) if override_path else HERE / 'raw' / (body['id'] + '-' + category + '-v1.png')
    with Image.open(path) as source:
        source = source.convert('RGBA')
        rects, _ = review_geometry.measured_grid(source, 4, 3, path.name)
        cells = [[source.crop((x, y, x + w, y + h)) for x, y, w, h in row] for row in rects]
        bounds = [[cell.getchannel('A').point(lambda a: 255 if a >= 128 else 0).getbbox() for cell in row] for row in cells]
        # Single-leg rows still contain a foot; use them to establish full height.
        reference_rows = bounds if category == 'arms' else bounds[:2]
        height = max(b[3] - b[1] for row in reference_rows for b in row)
        scale = body['targetHeight'] / height
        output = []
        for row, boxes in zip(cells, bounds):
            outrow = []
            for cell, box in zip(row, boxes):
                pixels = np.asarray(cell)
                ys, xs = np.nonzero((pixels[..., 3] >= 128) & (np.indices(pixels.shape[:2])[0] < box[1] + height * .30))
                head_center = float(np.median(xs))
                yy, xx = np.mgrid[:64, :64]
                sx = np.floor((xx + .5 - 32) / scale + head_center).astype(int)
                sy = np.floor((yy + .5 - (61 - body['targetHeight'])) / scale + box[1]).astype(int)
                inside = (sx >= 0) & (sx < cell.width) & (sy >= 0) & (sy < cell.height)
                normalized = np.zeros((64, 64, 4), np.uint8)
                normalized[inside] = pixels[sy[inside], sx[inside]]
                outrow.append(normalized)
            output.append(outrow)
    return output, str(path)


def shared_masks(base):
    normal = pixel_cutter.render_body(base)[0]
    arms, arm_path = ai_cells(base, 'arms')
    legs, leg_path = ai_cells(base, 'legs')
    yy, xx = np.mgrid[:64, :64]
    top = 61 - base['targetHeight']
    arm_zone = (yy >= top + base['targetHeight'] * .40) & (yy < 61 - base['targetHeight'] * .16)
    leg_zone = yy >= top + base['targetHeight'] * .78
    result = []
    for view in range(4):
        visible = np.asarray(normal[view])[..., 3] >= 128
        # Both-limb states avoid inheriting a model's accidental left/right swap.
        missing_arms = visible & (arms[2][view][..., 3] < 128) & arm_zone
        missing_legs = visible & (legs[2][view][..., 3] < 128) & leg_zone
        # Never erode the central chest while borrowing another drawing's outline.
        missing_arms &= (xx < 32 - base['targetHeight'] * .115) | (xx > 32 + base['targetHeight'] * .115)
        if view == 0:
            left_arm, right_arm = missing_arms & (xx >= 32), missing_arms & (xx < 32)
            left_leg, right_leg = missing_legs & (xx >= 32), missing_legs & (xx < 32)
        elif view == 1:
            left_arm, right_arm = missing_arms & (xx < 32), missing_arms & (xx >= 32)
            left_leg, right_leg = missing_legs & (xx < 32), missing_legs & (xx >= 32)
        else:
            # A side view primarily shows the near arm; do not invent far-side art.
            empty = np.zeros((64, 64), bool)
            left_arm, right_arm = (empty, missing_arms) if view == 2 else (missing_arms, empty)
            # Borrow the existing calibrated anatomical ownership of visible legs.
            original_split = pixel_cutter.split_frame(normal[view], base, 0, view)
            left_leg = missing_legs & (np.asarray(original_split['masks']['LeftLeg']) > 0)
            right_leg = missing_legs & (np.asarray(original_split['masks']['RightLeg']) > 0)
        result.append(dict(zip(SLOTS, [left_arm, right_arm, left_leg, right_leg])))
    return result, [arm_path, leg_path]


def make_split(cell, body, base, masks, view):
    rgba = np.asarray(cell)
    yy, xx = np.mgrid[:64, :64]
    scale = body['targetHeight'] / base['targetHeight']
    sx = np.clip(np.floor(32 + (xx - 32) / scale).astype(int), 0, 63)
    sy = np.clip(np.floor(61 + (yy - 61) / scale).astype(int), 0, 63)
    assigned = np.zeros((64, 64), bool)
    protected_hair = pixel_cutter._protected_hair(rgba, body)
    split = {'parts': {}, 'masks': {}}
    for slot in SLOTS:
        mask = masks[view][slot][sy, sx] & (rgba[..., 3] > 0) & ~assigned
        if slot.endswith('Arm'):
            mask &= ~protected_hair
        assigned |= mask
        part = np.zeros_like(rgba)
        part[mask] = rgba[mask]
        split['parts'][slot] = Image.fromarray(part, 'RGBA')
        split['masks'][slot] = Image.fromarray(mask.astype(np.uint8) * 255, 'L')
    core = rgba.copy()
    core[assigned] = 0
    split['core'] = Image.fromarray(core, 'RGBA')
    return split


def build(only=None):
    bodies = json.loads((HERE.parents[1] / 'armory' / 'bodies.json').read_text())['bodies']
    by_id = {b['id']: b for b in bodies}
    cache, records, pending = {}, [], []
    destination = HERE / 'hybrid-bodies'
    destination.mkdir(exist_ok=True)
    for body in bodies:
        if body['variant'] not in VARIANTS or (only and body['baseId'] != only):
            continue
        # A distinct werewolf silhouette is available for the Human family.
        geometry_id = 'human-werewolf' if body['id'] == 'human-werewolf' else body['baseId']
        base = by_id[geometry_id]
        try:
            if geometry_id not in cache:
                cache[geometry_id] = shared_masks(base)
            masks, sources = cache[geometry_id]
        except (FileNotFoundError, ValueError) as error:
            pending.append({'id': body['id'], 'reason': str(error)})
            continue
        cells = pixel_cutter.render_body(body)[0]
        splits = [make_split(cell, body, base, masks, view) for view, cell in enumerate(cells)]
        caps = [wound_pixels.wound_overlays(cell, split, body, 0, view) for view, (cell, split) in enumerate(zip(cells, splits))]
        groups = {}
        for bits, name in packing.STATES:
            row = []
            for view, (cell, split) in enumerate(zip(cells, splits)):
                result = packing.without(cell, split, bits)
                permitted = Image.new('L', (64, 64))
                from PIL import ImageChops
                for index, slot in enumerate(SLOTS):
                    if bits[index] == '1':
                        permitted = ImageChops.lighter(permitted, split['masks'][slot])
                        permitted = ImageChops.lighter(permitted, packing.support(caps[view][slot]))
                        result = packing.overlay_at_support(result, caps[view][slot])
                restored = result.copy()
                restored.paste(cell, (0, 0), permitted)
                assert restored.tobytes() == cell.tobytes(), 'Unexpected changes outside injury masks'
                row.append(result)
            groups[name] = [row]
        folder = destination / body['id']
        folder.mkdir(exist_ok=True)
        packing.sheet([frames[0] for frames in groups.values()], folder / 'injuries.png')
        packing.dmi(groups, [0], [200], False, folder / 'injuries.dmi')
        record = dict(id=body['id'], race=body['raceKey'], label=body['label'], variant=body['variant'],
                      path=str(folder / 'injuries.png'), dmi=str(folder / 'injuries.dmi'),
                      source=body['source'], geometrySources=sources,
                      generator='reuse of approved AI character pixels and shared AI injury silhouettes; mechanical masking and source-palette wound caps',
                      newlyAIGenerated=False, detachedPiecesGenerated=False,
                      columns=4, rows=len(groups), frameSize=[64, 64], rowLabels=list(groups),
                      directionOrder=packing.DIRECTIONS, outsideInjuryPixelsPreserved=True,
                      animation='standing pose only; no new walk cycle generated',
                      status='reuse draft; anatomical seams, profile overlap and tail clearance require visual review')
        (folder / 'provenance.json').write_text(json.dumps(record, indent=2) + '\n')
        records.append(record)
    (destination / 'manifest.json').write_text(json.dumps(records, indent=2) + '\n')
    (destination / 'pending.json').write_text(json.dumps(pending, indent=2) + '\n')
    print(json.dumps({'hybridBodies': len(records), 'pending': len(pending), 'detachedPieceFiles': 0, 'statesPerBody': len(packing.STATES)}))


if __name__ == '__main__':
    raise SystemExit('Retired cut-mask prototype. Use direct AI repairs; ai_cells remains available for frame extraction only.')
