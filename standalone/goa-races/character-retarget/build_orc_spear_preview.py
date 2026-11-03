#!/usr/bin/env python3
"""Reproducibly pack the equipped short-thrust drawing for review."""
from pathlib import Path
import hashlib
import importlib.util
import json
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[3]
ART = ROOT / 'Dungeon Master Sample/GOA Orc Base Animation Sprites'
OUT = ART / 'spear-shield-v1'
spec = importlib.util.spec_from_file_location('curate', Path(__file__).with_name('curate_orc_attacks.py'))
curate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(curate)

def main():
    source = OUT / 'drawings/equipped-thrust.png'
    raw = curate.extract(source)
    curate.CELL = 96
    curate.SCALE = .205 * 1448 / Image.open(source).width
    palette = np.concatenate([curate.palette_from_original(), np.array([
        [61, 32, 12], [98, 54, 20], [142, 83, 31], [180, 116, 53],
        [91, 92, 94], [145, 147, 150], [191, 194, 198], [225, 227, 229]
    ], dtype=np.uint8)])
    (OUT / 'frames').mkdir(exist_ok=True)
    sheet = Image.new('RGBA', (384, 384))
    contact = Image.new('RGB', (1200, 1260), '#444951')
    draw = ImageDraw.Draw(contact)
    labels = ['Ready', 'Small pullback', 'Short jab', 'Recover']
    frames = []
    for d, direction in enumerate(curate.DIRECTIONS):
        draw.text((d * 300 + 12, 8), direction.upper(), fill='white')
        guard = None
        for phase in range(4):
            frame = guard.copy() if phase == 3 else curate.register(raw[phase, d], palette)
            if phase == 0:
                guard = frame.copy()
            name = f'spear_short_thrust-{direction}-{phase}.png'
            frame.save(OUT / 'frames' / name)
            sheet.paste(frame, (d * 96, phase * 96))
            pixels = np.asarray(frame)
            assert set(np.unique(pixels[:, :, 3])) <= {0, 255}
            assert frame.getbbox()
            assert not (pixels[0, :, 3].any() or pixels[-1, :, 3].any() or pixels[:, 0, 3].any() or pixels[:, -1, 3].any())
            preview = frame.resize((288, 288), Image.Resampling.NEAREST)
            contact.paste(preview, (d * 300 + 5, phase * 310 + 25), preview)
            draw.text((d * 300 + 12, phase * 310 + 315), labels[phase], fill='white')
            frames.append({'direction': direction, 'phase': phase, 'file': 'frames/' + name,
                           'atlasRect': [d * 96, phase * 96, 96, 96], 'copiedReady': phase == 3})
    sheet.save(OUT / 'spear_short_thrust.png')
    contact.save(OUT / 'contact-sheet.png')
    prior = json.loads((OUT / 'prior-frame-hashes.json').read_text())
    assert all(hashlib.sha256((ART / p).read_bytes()).hexdigest() == h for p, h in prior.items())
    manifest = {
        'status': 'equipped_drawing_review_not_game_integrated', 'cellSize': 96,
        'directions': curate.DIRECTIONS, 'frames': frames, 'palette': palette.tolist(),
        'equipmentIncluded': True, 'separateEquipmentLayers': False,
        'note': 'Equipped visual review. Body and equipment are combined in this drawing; it is not the reusable equipment-layer export. Other weapon families are pending this pose review.',
        'source': 'drawings/equipped-thrust.png',
        'sourceSha256': hashlib.sha256(source.read_bytes()).hexdigest(),
        'recipes': [{'id': 'spear_short_thrust', 'name': 'Short spear jab + shield',
                     'sheet': 'spear_short_thrust.png', 'revision': 'equipped-v1',
                     'labels': labels, 'durations': [280, 120, 140, 220], 'previewTravel': [0, 0, 0, 0]}],
        'checks': {'prior208FramesUnchanged': len(prior) == 208, 'binaryAlpha': True,
                   'noClipping': True, 'recoveryCopiesReady': True}}
    curate.annotate_appearance(manifest)
    (OUT / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    (OUT / 'catalog.js').write_text('window.ORC_SPECIALS=' + json.dumps(manifest) + ';\n')
    print('Packed 16 equipped review cells; prior 208 body frames unchanged.')

if __name__ == '__main__':
    main()
