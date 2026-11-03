#!/usr/bin/env python3
"""Select existing drawn poses, reuse pixels, and pack a reproducible review set."""
from pathlib import Path
import hashlib
import json
import numpy as np
from PIL import Image, ImageDraw, ImageOps

ROOT = Path(__file__).resolve().parents[3]
ART = ROOT / 'Dungeon Master Sample/GOA Orc Base Animation Sprites'
SOURCE = ART / 'new-drawn-attacks'
OUT = ART / 'curated-attacks-v1'
DIRECTIONS = ['south', 'north', 'east', 'west']
ACTIONS = ['punch_right', 'punch_left', 'kick_right', 'kick_left']
FILES = {'pr': 'punch-right-draft-v2.png', 'pl': 'punch-left-draft-v2.png',
         'kr': 'kick-right-draft-v2.png'}
CELL = 80
SCALE = .205


def bands(mask):
    rows = np.where(mask.sum(axis=1) > 15)[0]
    return [(int(g[0]), int(g[-1]) + 1)
            for g in np.split(rows, np.where(np.diff(rows) > 1)[0] + 1)]


def extract(path):
    image = Image.open(path).convert('RGBA')
    data = np.asarray(image)
    row_bands = bands(data[:, :, 3] > 128)
    assert len(row_bands) == 4, (path, row_bands)
    frames = {}
    for row, (top, bottom) in enumerate(row_bands):
        for direction in range(4):
            left, right = direction * image.width // 4, (direction + 1) * image.width // 4
            region = image.crop((left, top, right, bottom))
            alpha = np.asarray(region)[:, :, 3] > 128
            ys, xs = np.where(alpha)
            box = (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)
            frames[row, direction] = region.crop(box)
    return frames


def palette_from_original():
    source = np.asarray(Image.open(ART / 'references/original-game-orc.png').convert('RGBA'))
    colors = np.unique(source[source[:, :, 3] > 128, :3], axis=0)
    targets = np.array([[10, 14, 9], [29, 43, 19], [48, 66, 29], [65, 87, 36],
                        [82, 110, 45], [102, 134, 57], [121, 151, 70],
                        [22, 22, 22], [39, 40, 38], [59, 60, 56], [78, 78, 70],
                        [126, 0, 0], [205, 0, 0], [255, 15, 0],
                        [191, 191, 164], [239, 239, 214]], dtype=np.int32)
    distances = ((targets[:, None] - colors.astype(np.int32)[None]) ** 2).sum(axis=2)
    return colors[distances.argmin(axis=1)]


def annotate_appearance(manifest):
    path = ART / 'attack-appearance.json'
    if not path.exists():
        return
    appearance = json.loads(path.read_text())
    manifest['appearance'] = appearance
    if 'palette' in manifest:
        for color in appearance['skinRamp']:
            if color not in manifest['palette']:
                manifest['palette'].append(color)
    if 'paletteFromOriginalSource' in manifest.get('checks', {}):
        manifest['checks']['paletteFromOriginalSource'] = False
        manifest['checks']['paletteUsesUserAttackReference'] = True


def register(frame, palette):
    # One fixed scale across all frames: no stretching arms or legs.
    width, height = [max(1, round(v * SCALE)) for v in frame.size]
    small = np.asarray(frame.resize((width, height), Image.Resampling.NEAREST)).copy()
    rgb = small[:, :, :3].astype(np.int32)
    nearest = ((rgb[:, :, None] - palette.astype(np.int32)[None, None]) ** 2).sum(axis=3).argmin(axis=2)
    small[:, :, :3] = palette[nearest]
    # Apply the shared attack appearance from the original drawing, before its
    # green shading is lost to nearest-palette quantization. Fixed thresholds
    # across frames prevent per-frame brightness shifts. No filtering or geometry
    # changes: each source pixel selects one reference color.
    appearance_path = ART / 'attack-appearance.json'
    if appearance_path.exists():
        appearance = json.loads(appearance_path.read_text())
        skin = ((rgb[:, :, 1] > rgb[:, :, 0] * 1.15)
                & (rgb[:, :, 1] > rgb[:, :, 2] * 1.2)
                & (rgb[:, :, 1] > 55))
        levels = np.searchsorted(appearance['sourceGreenThresholds'], rgb[:, :, 1], side='right')
        ramp = np.asarray(appearance['skinRamp'], dtype=np.uint8)
        small[skin, :3] = ramp[levels[skin]]
    small[:, :, 3] = np.where(small[:, :, 3] >= 128, 255, 0)
    small[small[:, :, 3] == 0, :3] = 0
    # Head position anchors horizontal alignment; an extended fist must not move the body.
    mask = np.asarray(frame)[:, :, 3] >= 128
    head_x = np.where(mask[:min(80, frame.height)])[1]
    anchor = (float(head_x.min()) + float(head_x.max())) / 2 * SCALE
    x, y = round(CELL // 2 - anchor), 68 - height
    assert x >= 0 and y >= 0 and x + width <= CELL and y + height <= CELL, (x, y, width, height)
    canvas = Image.new('RGBA', (CELL, CELL))
    canvas.paste(Image.fromarray(small), (x, y))
    return canvas


def choose(action, phase, direction, source):
    if phase == 0:
        return source['pr'][0, direction].copy(), 'pr', 0, direction, False
    if action == 'punch_right':
        key, facing, mirror = 'pr', direction, False
    elif action == 'punch_left':
        key, facing, mirror = ('pr', direction, True) if direction == 1 else ('pl', direction, False)
    elif action == 'kick_right':
        key, facing, mirror = 'kr', direction, False
    else:
        # Reflect the opposite facing for profiles so anatomical near/far limbs swap.
        key, facing, mirror = 'kr', [0, 1, 3, 2][direction], True
    frame = source[key][phase, facing].copy()
    if mirror:
        frame = ImageOps.mirror(frame)
    return frame, key, phase, facing, mirror


def main():
    OUT.mkdir(exist_ok=True)
    (OUT / 'frames').mkdir(exist_ok=True)
    (OUT / 'selected-source-poses').mkdir(exist_ok=True)
    sources = {key: extract(SOURCE / name) for key, name in FILES.items()}
    palette = palette_from_original()
    records, checks = [], []
    atlas = Image.new('RGBA', (CELL * 4, CELL * 4 * len(ACTIONS)))
    guards = {}
    for ai, action in enumerate(ACTIONS):
        sheet = Image.new('RGBA', (CELL * 4, CELL * 4))
        for phase in range(4):
            for di, direction in enumerate(DIRECTIONS):
                raw, source_key, source_phase, source_direction, mirror = choose(action, phase, di, sources)
                name = f'{action}-{direction}-{phase}'
                raw.save(OUT / 'selected-source-poses' / f'{name}.png')
                frame = register(raw, palette)
                if phase == 0:
                    guards.setdefault(di, frame.tobytes())
                    assert guards[di] == frame.tobytes()
                frame.save(OUT / 'frames' / f'{name}.png')
                sheet.paste(frame, (di * CELL, phase * CELL))
                arr = np.asarray(frame)
                assert set(np.unique(arr[:, :, 3])) <= {0, 255}
                assert frame.getbbox() is not None
                checks.append(name)
                records.append({'id': name, 'action': action, 'direction': direction, 'phase': phase,
                                'file': f'frames/{name}.png', 'source': FILES[source_key],
                                'sourcePhase': source_phase, 'sourceDirection': DIRECTIONS[source_direction],
                                'mirror': mirror, 'atlasRect': [di * CELL, (ai * 4 + phase) * CELL, CELL, CELL]})
        sheet.save(OUT / f'{action}.png')
        atlas.paste(sheet, (0, ai * 4 * CELL))
    atlas.save(OUT / 'orc-attacks.png')
    # Contact sheet: four attacks, each shown as a four-frame strip in every direction.
    preview = Image.new('RGB', (1400, 1560), '#444951')
    draw = ImageDraw.Draw(preview)
    for ai, action in enumerate(ACTIONS):
        y = ai * 390
        draw.text((12, y + 8), action.replace('_', ' ').upper(), fill='white')
        for di, direction in enumerate(DIRECTIONS):
            x = di * 350 + 8
            draw.text((x, y + 32), direction.upper(), fill='#d5dfca')
            for phase in range(4):
                frame = Image.open(OUT / 'frames' / f'{action}-{direction}-{phase}.png')
                # 2x2 phases, integer enlargement only.
                preview.paste(frame.resize((160, 160), Image.Resampling.NEAREST),
                              (x + phase % 2 * 170, y + 48 + phase // 2 * 166),
                              frame.resize((160, 160), Image.Resampling.NEAREST))
    preview.save(OUT / 'contact-sheet.png')
    manifest = {'status': 'curated_native_size_review', 'originalMaster': '../references/original-game-orc.png',
                'note': 'Derived from generated drawings; not pixel-identical to the original Orc. Anatomy still needs review.',
                'cellSize': CELL, 'directions': DIRECTIONS, 'actions': ACTIONS,
                'phases': ['guard', 'windup_or_chamber', 'impact', 'recovery'],
                'previewDurationsMs': [160, 120, 100, 160], 'scale': SCALE,
                'palette': palette.tolist(), 'filter': 'nearest', 'alpha': 'binary',
                'equipmentIncluded': False, 'frames': records,
                'sources': {name: hashlib.sha256((SOURCE / name).read_bytes()).hexdigest() for name in FILES.values()},
                'checks': {'frames': len(checks), 'sharedGuardsIdentical': True, 'noClipping': True,
                           'binaryAlpha': True, 'paletteFromOriginalSource': True}}
    annotate_appearance(manifest)
    (OUT / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(f'Wrote {len(records)} frames, 4 action sheets, atlas and review contact sheet to {OUT}')


if __name__ == '__main__':
    main()
