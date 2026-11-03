#!/usr/bin/env python3
"""Remove border-connected charcoal-blue background, retaining source RGB.

This is technical alpha masking, not generation, painting or color correction.
Explicit source rectangles are required and original sheets are never changed.
"""
import argparse
from collections import deque
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image

VERSION = 'existing-pixels-cutout-1.2'


def _flood(candidate):
    height, width = candidate.shape
    seen = np.zeros(candidate.shape, dtype=bool)
    todo = deque()
    for y, x in [(0, x) for x in range(width)] + [(height-1, x) for x in range(width)] + [(y, 0) for y in range(height)] + [(y, width-1) for y in range(height)]:
        if candidate[y, x] and not seen[y, x]:
            seen[y, x] = True
            todo.append((y, x))
    while todo:
        y, x = todo.popleft()
        for ny, nx in ((y-1, x), (y+1, x), (y, x-1), (y, x+1)):
            if 0 <= ny < height and 0 <= nx < width and candidate[ny, nx] and not seen[ny, nx]:
                seen[ny, nx] = True
                todo.append((ny, nx))
    return seen


def extract(input_sheet, crop_box, out_png):
    """Write an alpha-only source-resolution cutout and JSON audit.

    crop_box is explicit (left, top, right, bottom), right/bottom exclusive.
    A passed RGB check establishes literal pixel retention, not segmentation
    correctness. Warnings require visual review; ambiguous closed holes remain.
    """
    source, output = Path(input_sheet).resolve(), Path(out_png).resolve()
    report_path = output.with_suffix('.cutout.json')
    if source == output or output.exists() or report_path.exists():
        raise ValueError('Refusing to overwrite source or existing cutout/report')
    if output.suffix.lower() != '.png':
        raise ValueError('Cutout output must be PNG')
    box = tuple(int(x) for x in crop_box)
    if len(box) != 4:
        raise ValueError('Four explicit crop coordinates required')
    raw = source.read_bytes()
    with Image.open(source) as original:
        if not (0 <= box[0] < box[2] <= original.width and 0 <= box[1] < box[3] <= original.height):
            raise ValueError('Invalid or out-of-image crop')
        cropped = original.convert('RGBA').crop(box)
    pixels = np.asarray(cropped).copy()
    rgb = pixels[:, :, :3].astype(np.float32)
    red, green, blue = rgb.transpose(2, 0, 1)
    # The sheet's backdrop and ground shadow are a narrow blue-gray cone.
    # Saturated blue race/material colors and neutral black outlines are excluded.
    cone = ((blue - red >= 3) & (green >= red - 1) & (blue - green >= 1)
            & (red >= blue * .20) & (blue - red <= 32) & (red >= 4))
    edge = np.zeros(red.shape, dtype=bool)
    edge[0] = edge[-1] = True
    edge[:, 0] = edge[:, -1] = True
    samples = rgb[cone & edge]
    if len(samples) < max(8, int(edge.sum() * .08)):
        raise ValueError('Ambiguous crop: insufficient border charcoal-blue background samples')
    ceiling = float(np.quantile(samples.max(axis=1), .95)) + 12
    # Opaque near-black ink is protected even when it has a slight blue cast.
    # Its exact semantic boundary cannot be recovered from the flattened sheet.
    protected_black = rgb.max(axis=2) <= 18
    candidate = cone & (blue <= ceiling) & ~protected_black
    background = _flood(candidate)
    if background.sum() < pixels.shape[0] * pixels.shape[1] * .02:
        raise ValueError('Ambiguous segmentation: too little connected background')
    original_alpha = pixels[:, :, 3].copy()
    pixels[background, 3] = 0
    retained = pixels[:, :, 3] > 0
    if not retained.any():
        raise ValueError('Segmentation removed all visible artwork')
    unresolved = candidate & ~background & (original_alpha > 0)
    # Never erase enclosed candidate-colored regions: they may be material.
    warnings = []
    if unresolved.any():
        warnings.append('Enclosed background-colored pixels retained; inspect holes/materials')
    if (retained & edge).any():
        warnings.append('Retained pixels touch crop border; verify crop does not clip artwork')
    if (retained & cone & (blue > ceiling)).any():
        warnings.append('Blue-gray material above background brightness retained')
    unpadded = Image.fromarray(pixels)
    # A clear perimeter is technical packaging for the existing height exporter.
    # No source coordinate is moved relative to another; new pixels are alpha0.
    result = Image.new('RGBA', (unpadded.width + 8, unpadded.height + 8), (0, 0, 0, 0))
    result.paste(unpadded, (4, 4))
    report = {
        'version': VERSION, 'classification': 'existing_art_alpha_only_cutout',
        'status': 'source_resolution_cutout_pending_visual_review',
        'input_sheet': str(source), 'source_sha256': hashlib.sha256(raw).hexdigest(),
        'crop_box': list(box), 'size': list(result.size),
        'source_crop_size': list(unpadded.size), 'transparent_padding': 4,
        'padded_source_offset': [4, 4],
        'unpadded_alpha_bbox': list(unpadded.getchannel('A').getbbox()),
        'alpha_bbox': list(result.getchannel('A').getbbox()),
        'retained_pixels': int(retained.sum()), 'background_pixels_removed': int(background.sum()),
        'enclosed_candidate_pixels_retained': int(unresolved.sum()),
        'retained_rgb_exact': bool(np.array_equal(pixels[retained, :3], np.asarray(cropped)[retained, :3])),
        'all_rgb_exact_including_hidden': bool(np.array_equal(pixels[:, :, :3], np.asarray(cropped)[:, :, :3])),
        'retained_alpha_exact': bool(np.array_equal(pixels[retained, 3], original_alpha[retained])),
        'mask_rules': {'connectivity': 4, 'selection': 'Only border-connected charcoal-blue cone',
                       'blue_minus_red_min': 3, 'blue_minus_red_max': 32,
                       'green_at_least_red_minus': 1, 'blue_minus_green_min': 1,
                       'red_at_least_blue_fraction': .20, 'red_minimum': 4,
                       'blue_ceiling': ceiling, 'border_background_sample_count': len(samples),
                       'protected_black_maximum_channel': 18,
                       'enclosed_candidates': 'Retain and warn; never automatically erase'},
        'operations': ['Explicit rectangle crop', 'Set alpha=0 only on background flood mask',
                       'Add four transparent pixels around crop for export packaging'],
        'generated': False, 'repainted': False, 'color_filters': False, 'resized': False,
        'near_black_ink_removed': int((background & protected_black).sum()),
        'engine_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'warnings': warnings,
        'limitations': ['Conservative chroma segmentation requires visual outline/feet/hole review',
                        'A pass proves RGB retention, not correct semantic segmentation'],
    }
    if hashlib.sha256(source.read_bytes()).hexdigest() != report['source_sha256']:
        raise ValueError('Source changed during processing')
    output.parent.mkdir(parents=True, exist_ok=True)
    result.save(output, 'PNG')
    report['output_path'] = str(output)
    report['output_sha256'] = hashlib.sha256(output.read_bytes()).hexdigest()
    report_path.write_text(json.dumps(report, indent=2) + '\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--crop', required=True, help='left,top,right,bottom exclusive')
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(extract(args.source, tuple(map(int, args.crop.split(','))), args.output)))
