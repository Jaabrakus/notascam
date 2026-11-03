#!/usr/bin/env python3
"""Demonstrate deterministic skin palette replacement without redrawing pixels.

The pose source is a generated review draft, not a registered game atlas.
Only green skin RGB values change. Alpha, placement, outlines, eyes, teeth and
shorts remain untouched. Donor palettes do not transfer horns, markings or tails.
"""
import hashlib
import json
import shutil
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[3]
LIBRARY = ROOT / 'Dungeon Master Sample/GOA Drawn Animation Library'
SOURCE = LIBRARY / 'Male/Orc/body-only-generated-draft-v2.png'
DONORS = ROOT / 'Dungeon Master Sample/Sprites/Male/Orc'
OUT = LIBRARY / 'Male/Orc/skin-swap-test-v2'
WEIGHTS = np.array([.2126, .7152, .0722])


def luminance(rgb):
    return sum(rgb[..., channel].astype(float)*weight for channel,weight in enumerate(WEIGHTS))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def palette(variant):
    # Fixed torso sampling region of the actual South-facing donor sprite.
    with Image.open(DONORS / variant / 'sprites.png') as image:
        pixels = np.array(image.convert('RGBA'))[28:40, 25:39].reshape(-1, 4)
    rgb = pixels[:, :3].astype(int)
    r, g, b = rgb.T
    if variant == 'Ashen':
        selected = (rgb.max(1)-rgb.min(1)<35) & (rgb.max(1)>25) & (rgb.max(1)<125)
    else:
        selected = (r>3*g) & (r>3*b) & (r>45)
    colors = np.unique(rgb[selected & (pixels[:, 3]>=128)], axis=0)
    if len(colors)<6:
        raise ValueError('Insufficient donor skin colors: '+variant)
    lum = luminance(colors)
    return np.array([colors[np.abs(lum-value).argmin()] for value in
                     np.quantile(lum, [.03,.20,.40,.60,.80,.98])], dtype=np.uint8)


def main():
    if OUT.exists():
        raise SystemExit('Review output already exists; preserve it or choose a versioned output.')
    before = digest(SOURCE)
    with Image.open(SOURCE) as image:
        original = np.array(image.convert('RGBA'))
    rgb = original[..., :3].astype(int)
    r, g, b = rgb.transpose(2,0,1)
    skin = (g-r>=6) & (g-b>=9) & (g>25) & (original[..., 3]>0)
    if not skin.any():
        raise ValueError('No green skin found')
    source_lum = luminance(rgb)
    assert np.isfinite(source_lum).all()
    levels = np.quantile(source_lum[skin], [.03,.20,.40,.60,.80,.98])
    indices = np.abs(source_lum[skin,None]-levels).argmin(1)
    OUT.mkdir(parents=True)
    shutil.copyfile(SOURCE, OUT / 'original.png')
    reports = []
    outputs = [('Original green', original)]
    for variant, label in [('Ashen','Ashen grey - palette only'), ('Hellblooded','Hellblooded red - palette only')]:
        shades = palette(variant)
        output = original.copy()
        output[skin,:3] = shades[indices]
        changed = np.any(output!=original,axis=2)
        assert np.array_equal(output[...,3],original[...,3]), 'Alpha changed'
        assert np.array_equal(output[~skin],original[~skin]), 'Non-skin pixels changed'
        assert not np.any(changed & ~skin)
        assert changed.any()
        path = OUT / (variant.lower()+'-palette.png')
        Image.fromarray(output).save(path)
        with Image.open(path) as image:
            assert np.array_equal(np.array(image),output)
        reports.append(dict(variant=variant,output=path.name,sourcePalette=shades.tolist(),
                            changedPixels=int(changed.sum()),alphaIdentical=True,
                            nonSkinPixelsIdentical=True,dimensionsIdentical=True,
                            sourceRGBtoTargetRGBIsDeterministic=True))
        outputs.append((label,output))
    # Copy the existing first pose row for a compact comparison, with no scaling.
    height = (original.shape[0]+3)//4
    comparison = Image.new('RGBA',(original.shape[1],(height+30)*len(outputs)),(68,73,82,255))
    draw = ImageDraw.Draw(comparison)
    for row,(label,output) in enumerate(outputs):
        y=row*(height+30)
        draw.text((12,y+8),label,fill='white')
        comparison.alpha_composite(Image.fromarray(output[:height]),(0,y+30))
    comparison.save(OUT/'comparison.png')
    assert digest(SOURCE)==before
    report=dict(status='palette_swap_test_passed',source=str(SOURCE.relative_to(ROOT)),
                sourceSha256=before,sourceUnchanged=True,sourceIsProductionAtlas=False,
                skinPixels=int(skin.sum()),variants=reports,
                limits=['Palette replacement only; no horns, scars, markings or tail transfer.',
                        'The pose image remains an unregistered generated draft.',
                        'Existing source alpha is preserved, including any pre-existing soft edges.',
                        'No resizing, filtering, geometry changes or image generation.'])
    (OUT/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    (OUT/'README.md').write_text('''# Orc skin-swap test

The same body-only Orc pose pixels are recolored using grey and red skin palettes
sampled from the existing Ashen and Hellblooded Orc art. Only selected green skin
RGB pixels change; alpha and every pixel outside the skin mask are identical.
Eyes, tusks, shorts, outlines and pose geometry are preserved. This is a palette
demonstration, not a finished recreation of either hybrid appearance: horns,
markings and tails require additional parts.

Open comparison.png for the first pose in all four directions. The individual
PNGs retain all sixteen poses. verification.json records the pixel comparisons.
The input is a generated drawing draft; recoloring does not make it a registered
native game atlas. No smoothing or resizing was applied.
''')
    print(json.dumps(dict(status=report['status'],variants=reports,output=str(OUT))))


if __name__=='__main__':
    main()
