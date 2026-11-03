#!/usr/bin/env python3
"""Deterministic local pixel-art relighting. This is not an AI redraw.

Only visible RGB inside metadata-declared cells is eligible. Geometry, alpha,
hidden RGB, empty cells, trailing padding and decoded Description stay exact.
No image resizing, filtering, smoothing, texture generation or external calls.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, PngImagePlugin

from validate_dmi import load_asset, validate_paths

VERSION = 'local-native-relight-1.0'
DEFAULT_SETTINGS = {'strength': 1.0}


def _distance(mask):
    """Bounded chessboard distance, with no wrapped neighbors or raster blur."""
    inner = np.pad(mask, 1)
    depth = mask.astype(np.float32)
    for _ in range(11):
        inner = np.pad(inner[1:-1, 1:-1] & inner[:-2, 1:-1]
                       & inner[2:, 1:-1] & inner[1:-1, :-2]
                       & inner[1:-1, 2:] & inner[:-2, :-2]
                       & inner[:-2, 2:] & inner[2:, :-2]
                       & inner[2:, 2:], 1)
        if not inner.any():
            break
        depth += inner[1:-1, 1:-1]
    return depth


def enhance_cell(cell, strength=1.0):
    """Stepped form lighting over the original colors, never moved pixels."""
    visible = cell[:, :, 3] > 0
    if not visible.any():
        return cell.copy()
    rgb = cell[:, :, :3].astype(np.float32)
    peak = rgb.max(axis=2)
    luminance = rgb @ np.array([.2126, .7152, .0722], dtype=np.float32)
    # Dark lines subdivide the form. Relative threshold keeps dark skin eligible.
    median = float(np.median(peak[visible]))
    lines = peak <= max(12.0, median * .22)
    form = visible & ~lines
    depth = _distance(form if form.any() else visible)
    height = np.sqrt(depth)
    gy, gx = np.gradient(height)
    normal_length = np.sqrt(gx * gx + gy * gy + .85 ** 2)
    lit = (.48 * gx + .62 * gy + .85 * .62) / normal_length
    # Four broad light steps create readable facets without adding tiny texture.
    light = np.select([lit < .30, lit < .53, lit < .74],
                      [-.115, -.035, .035], default=.085).astype(np.float32)
    # Very bright materials gain shadow definition with restrained highlights.
    light = np.where((light > 0) & (peak > 210), light * .50, light)
    # Keep dark faces legible and saturated materials within their original hues.
    light = np.where((light < 0) & (luminance < 42), light * .50, light)
    delta = rgb * (light * strength)[:, :, None]
    # Use highlight headroom rather than clipping bright red/green/white channels.
    delta = np.where(delta > 0, np.minimum(delta, (255 - rgb) * .45), delta)
    result = np.rint(rgb + delta).clip(0, 255).astype(np.uint8)
    eligible = form
    # Rare, high-contrast marks (eyes, mouth, clasps) stay exactly as drawn.
    colors, inverse, counts = np.unique(cell[visible, :3], axis=0,
                                        return_inverse=True, return_counts=True)
    rare = np.zeros(visible.shape, dtype=bool)
    rare[visible] = counts[inverse] <= max(1, int(visible.sum() * .004))
    eligible &= ~(rare & (np.abs(luminance - np.median(luminance[visible])) > 38))
    out = cell.copy()
    out[eligible, :3] = result[eligible]
    # Tiny glyphs and nearly black cells still receive a modest tonal treatment;
    # pure black stays black unless the entire occupied cell is black.
    if np.array_equal(out, cell):
        safe = visible & (peak > 0)
        if safe.any():
            offset = np.where(rgb > 0, np.where(rgb > 225, -1, 1), 0)
            out[safe, :3] = np.clip(rgb + offset, 0, 255).astype(np.uint8)[safe]
        else:
            out[visible, :3] = 1
    return out


def enhance_file(sourcePath, outPath, settings=None):
    """Write and validate one native candidate; return compact auditable result."""
    source, output = Path(sourcePath).resolve(), Path(outPath).resolve()
    if source == output:
        raise ValueError('Refusing to overwrite source')
    if 'standalone/remastered/game/Icons/Remastered' in str(output):
        raise ValueError('Refusing output inside canonical native source tree')
    cfg = dict(DEFAULT_SETTINGS)
    cfg.update(settings or {})
    if set(cfg) != {'strength'} or not 0 < float(cfg['strength']) <= 1.5:
        raise ValueError('Only strength in (0, 1.5] is supported')
    data = source.read_bytes()
    source_hash = hashlib.sha256(data).hexdigest()
    engine_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    key = hashlib.sha256(json.dumps([source_hash, VERSION, engine_hash, cfg],
                                    sort_keys=True).encode()).hexdigest()
    sidecar = Path(str(output) + '.local.json')
    if output.exists() and sidecar.exists():
        previous = json.loads(sidecar.read_text())
        if previous.get('cache_key') == key and previous.get('output_sha256') == hashlib.sha256(output.read_bytes()).hexdigest():
            previous['cache_hit'] = True
            return previous
    asset = load_asset(data, str(source))
    sheet = np.asarray(asset.image).copy()
    width, height = asset.metadata.width, asset.metadata.height
    columns = asset.image.width // width
    occupied = changed = 0
    for index in range(asset.metadata.used_cells):
        x, y = index % columns * width, index // columns * height
        cell = sheet[y:y + height, x:x + width]
        if not (cell[:, :, 3] > 0).any():
            continue
        occupied += 1
        result = enhance_cell(cell, float(cfg['strength']))
        changed += int(not np.array_equal(cell, result))
        cell[:] = result
    output.parent.mkdir(parents=True, exist_ok=True)
    info = PngImagePlugin.PngInfo()
    info.add_text('Description', asset.description, zip=True)
    temporary = output.with_name(output.name + '.working.png')
    Image.fromarray(sheet).save(temporary, format='PNG', pnginfo=info)
    validation = validate_paths(source, temporary, require_enhanced=occupied > 0)
    if not validation['passed']:
        temporary.unlink(missing_ok=True)
        raise ValueError('Validation rejected candidate: ' + str(validation['failures']))
    if hashlib.sha256(source.read_bytes()).hexdigest() != source_hash:
        temporary.unlink(missing_ok=True)
        raise ValueError('Source changed during enhancement')
    temporary.replace(output)
    result = {
        'classification': ('local_pixel_art_enhancement_not_ai_redraw' if occupied
                           else 'empty_preserved'),
        'version': VERSION, 'settings': cfg, 'cache_key': key, 'cache_hit': False,
        'engine_sha256': engine_hash, 'source_sha256': source_hash,
        'source_path': str(source), 'output_path': str(output),
        'output_sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
        'passed': True, 'size': list(asset.image.size),
        'frame_size': [width, height], 'used_cells': asset.metadata.used_cells,
        'occupied_cells': occupied, 'changed_cells': changed,
        'visible_rgb_changed': validation['pixels']['visible_rgb_changed'],
        'source_visible_pixels': validation['pixels']['source_visible_pixels'],
        'alpha_changed': validation['pixels']['alpha_changed'],
        'transparent_rgb_changed': validation['pixels']['transparent_rgb_changed'],
        'padding_rgb_changed': validation['padding']['rgb_changed'],
        'description_equal': True, 'ordered_states_equal': True,
        'source_unchanged': True,
    }
    sidecar.write_text(json.dumps(result, indent=2) + '\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--strength', type=float, default=1.0)
    args = parser.parse_args()
    print(json.dumps(enhance_file(args.source, args.output, {'strength': args.strength})))
