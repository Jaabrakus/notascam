"""Pack the first female injury sheets; preserve source RGB and body identities."""
import html
import json
from pathlib import Path
import sys
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / 'ai-redraws'))
import build as geometry
import build_pixel_assets as packing
from pack_direct_repairs import clean

STATES = ['Normal', 'NoLeftArm', 'NoRightArm', 'NoArms', 'NoLeftLeg', 'NoRightLeg', 'NoLegs']
FEMALE = HERE.parents[1] / 'female-animations/assets'


def measured_grid(image, columns, rows, label):
    """Use the same alpha thresholds as geometry, with vectorized projections."""
    visible = np.asarray(image.getchannel('A')) >= 128
    bands = geometry.projection_bands((visible.sum(axis=1) > 5).tolist(), rows, label + ' rows')
    row_cuts = [0] + [(bands[i][1]+bands[i+1][0])//2 for i in range(rows-1)] + [image.height]
    grid = []
    for row, (top, bottom) in enumerate(bands):
        found = geometry.projection_bands((visible[top:bottom].sum(axis=0) > 2).tolist(), columns, label + f' row {row} columns')
        cuts = [0] + [(found[i][1]+found[i+1][0])//2 for i in range(columns-1)] + [image.width]
        grid.append([[cuts[col],row_cuts[row],cuts[col+1]-cuts[col],row_cuts[row+1]-row_cuts[row]] for col in range(columns)])
    return grid


def normalize(path, category, height):
    im = Image.open(path).convert('RGBA')
    rects = measured_grid(im, 4, 3, path.name)
    cells = [[im.crop((x, y, x + w, y + h)) for x, y, w, h in row] for row in rects]
    boxes = [[cell.getchannel('A').point(lambda a: 255 if a >= 128 else 0).getbbox() for cell in row] for row in cells]
    references = boxes if category == 'arms' else boxes[:2]
    full_height = max(box[3] - box[1] for row in references for box in row)
    scale = height / full_height
    output = []
    for row, bounds in zip(cells, boxes):
        views = []
        for cell, box in zip(row, bounds):
            rgba = np.asarray(cell)
            sy, sx = np.nonzero((rgba[..., 3] >= 128) & (np.indices(rgba.shape[:2])[0] < box[1] + full_height * .30))
            center = float(np.median(sx))
            yy, xx = np.mgrid[:64, :64]
            xs = np.floor((xx + .5 - 32) / scale + center).astype(int)
            ys = np.floor((yy + .5 - (62 - height)) / scale + box[1]).astype(int)
            valid = (xs >= 0) & (xs < cell.width) & (ys >= 0) & (ys < cell.height)
            frame = np.zeros((64, 64, 4), np.uint8)
            frame[valid] = rgba[ys[valid], xs[valid]]
            views.append(frame)
        output.append(views)
    return output


def main():
    records, sections = [], []
    for race, height in [('Human', 56), ('Elf', 59), ('Orc', 57)]:
        arms = normalize(HERE / (race + '-female-arms-v1.png'), 'arms', height)
        legs = normalize(HERE / (race + '-female-legs-v1.png'), 'legs', height)
        standing = Image.open(FEMALE / race / 'base/standing.png').convert('RGBA')
        normal = [np.asarray(standing.crop((v * 64, 0, v * 64 + 64, 64))) for v in range(4)]
        if race in ('Human', 'Orc'):
            arms[0][1], arms[1][1] = arms[1][1], arms[0][1]
        if race == 'Orc':
            legs[0][1], legs[1][1] = legs[1][1], legs[0][1]
        # Whole profiles are reused where the far arm is occluded. The near-arm
        # missing profile is visibly identical to the both-arm-missing profile.
        arms[0][2], arms[1][3] = normal[2].copy(), normal[3].copy()
        arms[0][3], arms[1][2] = arms[2][3].copy(), arms[2][2].copy()
        cleaned, removed = [], 0
        for row in [normal] + arms + legs:
            views = []
            for frame in row:
                result, count = clean(frame)
                removed += count
                keep = result[..., 3] > 0
                assert np.array_equal(result[keep, :3], frame[keep, :3])
                assert not result[~keep].any()
                views.append(Image.fromarray(result))
            cleaned.append(views)
        if race != 'Orc':
            for frame in cleaned[-1]:
                assert not np.asarray(frame)[58:, :, 3].any(), 'Unwanted foot pixels in NoLegs'
        png = HERE / (race + '-female-injuries64-v1.png')
        dmi = png.with_suffix('.dmi')
        packing.sheet(cleaned, png)
        packing.dmi({state: [row] for state, row in zip(STATES, cleaned)}, [0], [200], False, dmi)
        record = dict(race=race, sex='female', appearance='base', image=png.name, dmi=dmi.name,
                      frameSize=[64, 64], footBaseline=62, directions=packing.DIRECTIONS,
                      rowLabels=STATES, rows=7, columns=4, sourceRGBPreserved=True,
                      isolatedPixelsRemoved=removed, status='standing injury draft; walking injury frames not generated',
                      sourceArt=[race + '-female-arms-v1.png', race + '-female-legs-v1.png'])
        png.with_suffix('.json').write_text(json.dumps(record, indent=2) + '\n')
        records.append(record)
        rel = '../standalone/goa-races/limbs/female-direct/'
        rows = []
        for index, state in enumerate(STATES):
            rows.append('<div class="row"><b>' + state + '</b><div class="crop"><img src="' + rel + png.name + '" style="transform:translateY(-' + str(index * 128) + 'px)" alt="' + state + '"></div></div>')
        sections.append('<section><h2>' + race + ' · Female</h2><p><a href="' + rel + png.name + '">PNG sheet</a> · <a href="' + rel + dmi.name + '">DMI</a></p><p class="views">Front · Back · East · West</p>' + ''.join(rows) + '</section>')
    doc = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Female Limb Sheets — First Set</title><style>body{margin:24px;background:#1e2026;color:#eee;font:15px system-ui}h1{font-size:24px}h2{font-size:20px}a{color:#9cd3ff}p{color:#bac0cb}.sheets{display:flex;flex-wrap:wrap;gap:30px}.row{display:flex;align-items:center;gap:12px}.row>b{width:100px;font-size:13px}.crop{width:512px;height:128px;overflow:hidden;background:conic-gradient(#333 25%,#292c33 0 50%,#333 0 75%,#292c33 0);background-size:20px 20px}.crop img{display:block;width:512px;height:896px;image-rendering:pixelated}.views{margin-left:112px;width:512px;text-align:center}</style><h1>Female Limb Sheets — Human, Elf and Orc</h1><p>First female injury set. Direct AI artwork, 64×64 frames, red cut caps. Standing poses only; injury walk animations remain unfinished. The existing Orc reference includes a tail, which is retained.</p><main class="sheets">'''
    preview = HERE.parents[3] / 'Dungeon Master Sample/Female Limb Sheets - First Set.html'
    preview.write_text(doc + ''.join(sections) + '</main></html>')
    (HERE / 'manifest.json').write_text(json.dumps(records, indent=2) + '\n')
    print(json.dumps({'races': len(records), 'frames': 84, 'preview': str(preview)}))


if __name__ == '__main__':
    main()
