"""Apply approved hybrid appearances to actual AI-drawn injured bodies.

Reuse changes palettes and preserves the approved head/hair/markings. The body
silhouette comes from the AI injury artwork, not a cutout of an intact pose.
Only body PNG/DMI sheets are exported; there are no detached-piece exports.
"""
import json
from pathlib import Path
import sys
from collections import deque
import numpy as np
from PIL import Image, ImageFilter

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import build_pixel_assets as packing
import pixel_cutter
from build_hybrid_injuries import ai_cells, VARIANTS

WEIGHTS = np.array([.2126, .7152, .0722])


def luminance(rgb):
    return rgb @ WEIGHTS


def neck_row(image, height):
    top = 61 - height
    first, last = round(top + height * .30), round(top + height * .56)
    candidates = []
    for y in range(max(0, first), min(63, last)):
        xs = np.nonzero(image[y, :, 3] >= 128)[0]
        if len(xs):
            candidates.append((int(xs.max() - xs.min()), y))
    if not candidates:
        return round(top + height * .43)
    narrowest = min(width for width, y in candidates)
    return round(np.median([y for width, y in candidates if width <= narrowest + 1]))


def body_component(frame):
    visible = frame[..., 3] >= 128
    visited = np.zeros((64, 64), bool)
    components = []
    for y, x in zip(*np.nonzero(visible)):
        if visited[y, x]:
            continue
        points, pending = [], deque([(int(y), int(x))])
        visited[y, x] = True
        while pending:
            yy, xx = pending.popleft()
            points.append((yy, xx))
            for dy, dx in [(dy, dx) for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dy or dx]:
                ny, nx = yy + dy, xx + dx
                if 0 <= ny < 64 and 0 <= nx < 64 and visible[ny, nx] and not visited[ny, nx]:
                    visited[ny, nx] = True
                    pending.append((ny, nx))
        components.append(points)
    output = np.zeros_like(frame)
    if components:
        for y, x in max(components, key=len):
            output[y, x] = frame[y, x]
    return output


def hair_layer(approved, body, neck):
    rgb = approved[..., :3].astype(float)
    maximum, minimum = rgb.max(axis=2), rgb.min(axis=2)
    yy, xx = np.mgrid[:64, :64]
    region = (yy >= neck) & (yy < min(neck + body['targetHeight'] * .28, 49))
    race = body['raceKey']
    if race == 'Elf':
        # Gold hair is yellower than peach skin; do not restore skin or feet.
        selected = (rgb[..., 0] > 70) & (rgb[..., 1] > rgb[..., 2] * 1.5 + 12) & (rgb[..., 1] > rgb[..., 0] * .62)
    elif race == 'Night Elf':
        # Silver hair is brighter than Ashen skin and the black shorts.
        selected = (maximum > 110) & (maximum - minimum < 38)
    else:
        return np.zeros((64, 64), bool)
    return selected & region & (approved[..., 3] >= 128)


def skin_sample(rgba, height):
    y0 = round(61 - height + height * .46)
    y1 = round(61 - height + height * .66)
    sample = rgba[y0:y1, 28:36]
    colors = sample[..., :3][(sample[..., 3] >= 128) & (sample[..., :3].max(axis=2) > 35)]
    if len(colors) < 4:
        raise ValueError('Not enough visible torso pixels for palette reuse')
    order = colors[np.argsort(luminance(colors))]
    return np.array([np.median(chunk, axis=0) for chunk in np.array_split(order, min(12, len(order)))], dtype=np.uint8)


def texture(injured, approved, body, normal_base):
    output = injured.copy()
    rgb = output[..., :3].astype(float)
    alpha = output[..., 3] >= 128
    source_palette = skin_sample(normal_base, body['targetHeight'])
    target_palette = skin_sample(approved, body['targetHeight'])
    source_mean = max(float(luminance(source_palette).mean()), 1)
    target_mean = float(luminance(target_palette).mean())
    maximum, minimum = rgb.max(axis=2), rgb.min(axis=2)
    # Keep the native black outline, black shorts and red wound pixels.
    blood = (rgb[..., 0] > rgb[..., 1] * 4 + 20) & (rgb[..., 0] > rgb[..., 2] * 4 + 20)
    clothes = (maximum - minimum < 18) & (maximum < 90)
    skin = alpha & (maximum > 35) & ~blood & ~clothes
    wanted = luminance(rgb) * target_mean / source_mean
    index = np.abs(wanted[..., None] - luminance(target_palette)[None, None, :]).argmin(axis=2)
    output[skin, :3] = target_palette[index[skin]]
    output[..., 3] = np.where(alpha, 255, 0)
    output[~alpha] = 0
    # Copy the approved head, ears, horns and eyes as one identity layer.
    neck = neck_row(approved, body['targetHeight']) + 1
    output[:neck] = approved[:neck]
    # Long hair remains an independent visual feature of the approved identity.
    hair = hair_layer(approved, body, neck)
    output[hair] = approved[hair]
    yy, xx = np.mgrid[:64, :64]
    actual_body = (yy >= neck) & (output[..., 3] >= 128) & (approved[..., 3] >= 128)
    r, g, b = (approved[..., channel].astype(float) for channel in range(3))
    if body['variant'] == 'Marked':
        markings = (r > g * 1.4 + 12) & (r > b * 1.4 + 12) & (r > 80)
    elif body['variant'] == 'Ashen':
        markings = (r > 90) & (r > g * 1.4) & (g > b * 1.3 + 5)
    elif body['variant'] == 'Zombie':
        markings = (r > g * 1.25 + 5) & (g > b * 1.1) & (r < 150)
    else:
        markings = np.zeros((64, 64), bool)
    output[actual_body & markings] = approved[actual_body & markings]
    return output


def orient_pair(frame, category, row, view, height):
    """Fix obvious model left/right swaps in front/back views before reuse."""
    if row == 2 or view > 1:
        return frame
    top = 61 - height
    if category == 'arms':
        visible = frame[round(top + height * .43):round(61 - height * .19), :, 3] >= 128
    else:
        visible = frame[round(61 - height * .18):, :, 3] >= 128
    left, right = visible[:, :32].sum(), visible[:, 32:].sum()
    left_should_have_more = (row == 0) == (view == 0)
    if left != right and ((left > right) != left_should_have_more):
        return frame[:, ::-1].copy()
    return frame


def add_tail(image, approved, normal_base, body, view):
    if body['variant'] not in ('Hellblooded', 'Werewolf'):
        return image
    # Preserve visible appendage art outside the ordinary body silhouette.
    base_alpha = Image.fromarray((normal_base[..., 3] >= 128).astype(np.uint8) * 255)
    expanded = np.asarray(base_alpha) > 0
    yy, xx = np.mgrid[:64, :64]
    hip = round(61 - body['targetHeight'] * .30)
    tail = (approved[..., 3] >= 128) & ~expanded & (yy >= hip)
    # The tail is behind the body: retain existing injured-body pixels on top.
    visible = tail & (image[..., 3] < 128)
    image[visible] = approved[visible]
    return image


def fit_geometry(frame, source_normal, target_normal, base, body):
    """Fit shared injured-body art to the approved family's body dimensions."""
    source_height, target_height = base['targetHeight'], body['targetHeight']
    source_neck, target_neck = neck_row(frame, source_height), neck_row(target_normal, target_height)
    def torso_width(image, height):
        y0, y1 = round(61 - height * .55), round(61 - height * .32)
        visible = image[y0:y1, :, 3] >= 128
        xs = np.nonzero(visible)[1]
        return max(int(xs.max() - xs.min() + 1), 1) if len(xs) else 1
    scale_x = np.clip(torso_width(target_normal, target_height) / torso_width(source_normal, source_height), .70, 1.40)
    scale_y = (61 - target_neck) / max(61 - source_neck, 1)
    yy, xx = np.mgrid[:64, :64]
    sx = np.floor(32 + (xx + .5 - 32) / scale_x).astype(int)
    sy = np.floor(source_neck + (yy + .5 - target_neck) / scale_y).astype(int)
    inside = (sx >= 0) & (sx < 64) & (sy >= 0) & (sy < 64)
    output = np.zeros_like(frame)
    output[inside] = frame[sy[inside], sx[inside]]
    return output


def build():
    bodies = json.loads((HERE.parents[1] / 'armory' / 'bodies.json').read_text())['bodies']
    by_id = {b['id']: b for b in bodies}
    destination = HERE / 'hybrid-reuse'
    destination.mkdir(exist_ok=True)
    records, pending, cache = [], [], {}
    for body in bodies:
        if body['variant'] not in VARIANTS and not (body['variant'] == 'Base' and body['status'] != 'flight'):
            continue
        geometry_id = ('human-werewolf' if body['variant'] == 'Werewolf' else
                       'human-hellblooded' if body['variant'] == 'Hellblooded' else body['baseId'])
        base = by_id[geometry_id]
        try:
            if geometry_id not in cache:
                arms, arm_path = ai_cells(base, 'arms')
                legs, leg_path = ai_cells(base, 'legs')
                arms = [[body_component(frame) for frame in row] for row in arms]
                legs = [[body_component(frame) for frame in row] for row in legs]
                cache[geometry_id] = arms, legs, [arm_path, leg_path]
            arms, legs, sources = cache[geometry_id]
        except (ValueError, FileNotFoundError) as error:
            pending.append(dict(id=body['id'], reason=str(error)))
            continue
        approved = [np.asarray(cell) for cell in pixel_cutter.render_body(body)[0]]
        base_normal = [np.asarray(cell) for cell in pixel_cutter.render_body(base)[0]]
        fitted_base = [fit_geometry(normal, normal, approved[view], base, body) for view, normal in enumerate(base_normal)]
        arm_states, leg_states = [], []
        for category, frames, output in [('arms', arms, arm_states), ('legs', legs, leg_states)]:
            for row in range(3):
                views = []
                for view in range(4):
                    if category == 'arms' and ((row == 0 and view == 2) or (row == 1 and view == 3)):
                        views.append(approved[view].copy())
                        continue
                    frame = orient_pair(frames[row][view], category, row, view, base['targetHeight'])
                    if category == 'arms' and view > 1:
                        frame = frames[2][view]
                    if body['id'] == 'human-hellblooded' or body['variant'] == 'Base':
                        # This identity was redrawn as one complete connected body.
                        # Do not splice its head or tail back onto the new torso.
                        frame = frame.copy()
                    else:
                        frame = fit_geometry(frame, base_normal[view], approved[view], base, body)
                        frame = texture(frame, approved[view], body, fitted_base[view])
                        if body['variant'] != 'Hellblooded':
                            frame = add_tail(frame, approved[view], fitted_base[view], body, view)
                    views.append(frame)
                output.append(views)
        # Rebuild the two front/back single-arm states from verified both-arm
        # and both-arm-missing upper bodies. Some AI drafts removed both arms
        # in a nominal single-arm back view; mirroring cannot repair that.
        for view in (0, 1):
            upper_start = neck_row(arm_states[2][view], body['targetHeight']) + 1
            upper_end = round(61 - body['targetHeight'] * .20)
            for row in (0, 1):
                frame = arm_states[2][view].copy()
                restore_left = (row == 0) == (view == 0)
                span = slice(0, 32) if restore_left else slice(32, 64)
                frame[upper_start:upper_end, span] = leg_states[0][view][upper_start:upper_end, span]
                arm_states[row][view] = frame
        groups = {}
        for bits, name in packing.STATES:
            arm_bits, leg_bits = bits[:2], bits[2:]
            arm_row = {'10': 0, '01': 1, '11': 2}.get(arm_bits)
            leg_row = {'10': 0, '01': 1, '11': 2}.get(leg_bits)
            views = []
            for view in range(4):
                if arm_row is None and leg_row is None:
                    frame = approved[view].copy()
                elif arm_row is None:
                    frame = leg_states[leg_row][view].copy()
                elif leg_row is None:
                    frame = arm_states[arm_row][view].copy()
                else:
                    # The black shorts hide the seam between two registered states.
                    seam = round(61 - body['targetHeight'] * .20)
                    frame = arm_states[arm_row][view].copy()
                    frame[seam:] = leg_states[leg_row][view][seam:]
                    if body['variant'] != 'Hellblooded':
                        frame = add_tail(frame, approved[view], fitted_base[view], body, view)
                frame = body_component(frame)
                visible = frame[..., 3] >= 128
                frame[..., 3] = np.where(visible, 255, 0)
                frame[~visible] = 0
                views.append(Image.fromarray(frame))
            groups[name] = [views]
        folder = destination / body['id']
        folder.mkdir(exist_ok=True)
        packing.sheet([state[0] for state in groups.values()], folder / 'injuries.png')
        packing.dmi(groups, [0], [200], False, folder / 'injuries.dmi')
        record = dict(id=body['id'], race=body['raceKey'], label=body['label'], variant=body['variant'],
                      path=str(folder / 'injuries.png'), dmi=str(folder / 'injuries.dmi'),
                      appearanceSource=body['source'], injurySources=sources,
                      method='actual AI-drawn injured-body art, reused palette and approved identity layers; mixed states assembled at shorts',
                      newlyAIGenerated=(geometry_id == body['id']), detachedPiecesGenerated=False,
                      columns=4, rows=len(groups), frameSize=[64, 64], rowLabels=list(groups),
                      directionOrder=packing.DIRECTIONS, animation='standing pose only',
                      pixelCleanup='8-connected body only; isolated fragments removed; zero RGBA outside silhouette; binary alpha',
                      status='reuse draft; neck/shorts seams, profile laterality and tail attachment need visual review')
        (folder / 'provenance.json').write_text(json.dumps(record, indent=2) + '\n')
        records.append(record)
    (destination / 'manifest.json').write_text(json.dumps(records, indent=2) + '\n')
    (destination / 'pending.json').write_text(json.dumps(pending, indent=2) + '\n')
    print(json.dumps({'bodies': len(records), 'hybrids': sum(r['variant'] in VARIANTS for r in records), 'pending': len(pending), 'detachedPieces': 0}))


if __name__ == '__main__':
    raise SystemExit('Retired: the user rejected this compositing method. Use direct edits of approved sprite art; do not regenerate this batch.')
