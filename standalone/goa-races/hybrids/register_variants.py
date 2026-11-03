"""Measure complete hybrid characters instead of assuming equal source rows.

Only records source rectangles and destination registration. Original artwork
is unchanged; Canvas performs the normal atlas packing in the viewer.
"""
from pathlib import Path
import json
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
HEIGHTS = {'Human': 56, 'HumanBlack': 56, 'Dwarves': 46, 'Elf': 59,
           'Night Elf': 59, 'Orc': 57, 'Goblins': 43, 'Kobold': 45,
           'FrogMan': 54, 'LizardMan': 54, 'Gargoyle-eyes': 52}


def runs(active):
    result, start = [], None
    for index, occupied in enumerate(active):
        if occupied and start is None:
            start = index
        if not occupied and start is not None:
            result.append((start, index))
            start = None
    if start is not None:
        result.append((start, len(active)))
    return result


def main():
    result = {}
    for name, target_height in HEIGHTS.items():
        image = Image.open(HERE / 'sheets' / (name + '.png'))
        mask = np.asarray(image.getchannel('A')) > 128
        rows = runs(mask.sum(1) > 3)
        expected = 6 if name == 'Gargoyle-eyes' else 7
        assert len(rows) == expected, (name, rows)
        rects = []
        for row, (top, bottom) in enumerate(rows):
            columns = runs(mask[top:bottom].sum(0) > 3)
            assert len(columns) == 4, (name, row, columns)
            for direction, (left, right) in enumerate(columns):
                ys = np.nonzero(mask[top:bottom, left:right].any(1))[0]
                y0, y1 = top + int(ys.min()), top + int(ys.max()) + 1
                rects.append(dict(row=row, column=direction,
                                  source=[left, y0, right-left, y1-y0]))
        scale = min(target_height / max(r['source'][3] for r in rects[:4]),
                    60 / max(r['source'][3] for r in rects),
                    60 / max(r['source'][2] for r in rects))
        for rect in rects:
            width, height = [max(1, round(v * scale)) for v in rect['source'][2:]]
            rect['destination'] = [rect['column']*64 + 32-width//2,
                                   rect['row']*64 + 62-height, width, height]
        result[name] = dict(rows=expected, uniformScale=scale,
                            footBaseline=62, rects=rects,
                            sourceBorderContact=any(r['source'][1]+r['source'][3] == image.height for r in rects))
    (HERE / 'variant-registration.json').write_text(json.dumps(result, indent=2))
    print('Measured', sum(len(v['rects']) for v in result.values()),
          'complete variant views; foot baseline y62.')


if __name__ == '__main__':
    main()
