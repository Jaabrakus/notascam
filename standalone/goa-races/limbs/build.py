"""Package the limb review/export viewer without changing any sprite pixels."""
import argparse
import base64
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def projection_bands(active, expected, label):
    """Find separated objects; refuse ambiguous layouts instead of clipping art."""
    bands, start = [], None
    for index, occupied in enumerate(active + [False]):
        if occupied and start is None:
            start = index
        if not occupied and start is not None:
            if index - start >= 3:
                bands.append([start, index])
            start = None
    if len(bands) != expected:
        raise ValueError(f'{label}: detected {len(bands)} occupied bands, expected {expected}; provide explicit sourceRects to segment this image.')
    return bands


def measured_grid(image, columns, rows, label):
    alpha = image.getchannel('A')
    row_active = [sum(value >= 128 for value in alpha.crop((0, y, image.width, y + 1)).getdata()) > 5
                  for y in range(image.height)]
    bands = projection_bands(row_active, rows, label + ' rows')
    row_cuts = [0] + [(bands[i][1] + bands[i + 1][0]) // 2 for i in range(rows - 1)] + [image.height]
    grid = []
    for row, (top, bottom) in enumerate(bands):
        active = [sum(value >= 128 for value in alpha.crop((x, top, x + 1, bottom)).getdata()) > 2
                  for x in range(image.width)]
        columns_found = projection_bands(active, columns, label + f' row {row} columns')
        cuts = [0] + [(columns_found[i][1] + columns_found[i + 1][0]) // 2 for i in range(columns - 1)] + [image.width]
        grid.append([[cuts[col], row_cuts[row], cuts[col + 1] - cuts[col], row_cuts[row + 1] - row_cuts[row]] for col in range(columns)])
    return grid, dict(method='alpha128 projection bands and midpoint separators', rowBands=bands,
                      equalCellsAssumed=False)


def source_rectangles(entry, source):
    from PIL import Image
    image = Image.open(source).convert('RGBA')
    source_rows = entry.get('sourceGridRows', entry['rows'])
    if type(source_rows) is not int or not 1 <= source_rows <= 64:
        raise ValueError('sourceGridRows must be an integer from 1 to 64.')
    selected = entry.get('selectedRows', list(range(entry['rows'])))
    if not isinstance(selected, list) or len(selected) != entry['rows'] or any(type(row) is not int or not 0 <= row < source_rows for row in selected) or len(set(selected)) != len(selected):
        raise ValueError('selectedRows must name one distinct valid source row per output row.')
    grid = entry.get('sourceRects')
    if grid is None:
        grid, segmentation = measured_grid(image, entry['columns'], source_rows, entry['id'])
        grid = [grid[row] for row in selected]
    else:
        if not isinstance(grid, list):
            raise ValueError('sourceRects must be a list of rows.')
        if len(grid) == source_rows:
            grid = [grid[row] for row in selected]
        elif len(grid) != entry['rows']:
            raise ValueError('sourceRects must describe either all source rows or the selected output rows.')
        segmentation = dict(method='explicit source rectangles', equalCellsAssumed=False)
    for row in grid:
        if not isinstance(row, list) or len(row) != entry['columns']:
            raise ValueError('Every sourceRects row must contain four view rectangles.')
        for rect in row:
            if not isinstance(rect, list) or len(rect) != 4 or any(type(value) not in (int, float) or not math.isfinite(value) for value in rect):
                raise ValueError('Source rectangles must contain numeric [x,y,width,height].')
            x, y, width, height = rect
            if min(x, y) < 0 or min(width, height) <= 0 or x + width > image.width or y + height > image.height:
                raise ValueError('Source rectangle exceeds image bounds.')
    return dict(sourceRects=grid, sourceGridRows=source_rows, selectedRows=selected,
                sourceSize=list(image.size), segmentation=segmentation,
                packing=dict(method='common source-pixel scale, centered full cells; no independent frame stretching',
                             scale=64 / max(max(rect[2], rect[3]) for row in grid for rect in row)))


def load_assets(manifest):
    if not manifest.exists():
        return []
    entries = json.loads(manifest.read_text())
    if not isinstance(entries, list):
        raise ValueError('The limb manifest must contain a list of assets.')
    assets, ids = [], set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError('Every manifest entry must be an object.')
        for field in ['id', 'race', 'category', 'label', 'path']:
            if not isinstance(entry.get(field), str) or not entry[field]:
                raise ValueError('Missing or invalid asset ' + field)
        if entry['id'] in ids:
            raise ValueError('Duplicate asset id: ' + entry['id'])
        ids.add(entry['id'])
        if entry['category'] not in ('detached', 'injury'):
            raise ValueError('Category must be detached or injury.')
        if type(entry.get('columns')) is not int or entry['columns'] != 4:
            raise ValueError('Each asset must contain four direction columns.')
        if type(entry.get('rows')) is not int or not 1 <= entry['rows'] <= 64:
            raise ValueError('Each asset must contain 1–64 rows.')
        if not isinstance(entry.get('rowLabels'), list) or len(entry['rowLabels']) != entry['rows'] or not all(isinstance(v, str) for v in entry['rowLabels']):
            raise ValueError('Every row must have one row label.')
        if entry.get('directionOrder') != ['South', 'North', 'East', 'West']:
            raise ValueError('Direction order must be South, North, East, West.')
        source = Path(entry['path'])
        if not source.is_absolute():
            source = manifest.parent / source
            if not source.exists():
                source = ROOT / entry['path']
        raw = source.read_bytes()
        if not raw.startswith(b'\x89PNG\r\n\x1a\n'):
            raise ValueError('Expected a PNG source: ' + str(source))
        assets.append(dict(entry, **source_rectangles(entry, source), sourcePath=str(source.resolve()), src='data:image/png;base64,' + base64.b64encode(raw).decode()))
    return assets


def render(manifest):
    data = json.dumps(load_assets(manifest), separators=(',', ':')).replace('<', '\\u003c')
    return (HERE / 'gallery.template.html').read_text().replace('/*DATA*/null', data).replace('/*APP*/', (HERE / 'gallery.js').read_text())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, default=HERE / 'manifest.json')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    output = args.output or HERE / 'index.html'
    html = render(args.manifest)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html)
    if args.output is None:
        (ROOT / 'Dungeon Master Sample/GOA Limbs and Injuries.html').write_text(html)
    print('Built ' + str(output) + ': ' + str(len(load_assets(args.manifest))) + ' source assets')


if __name__ == '__main__':
    main()
