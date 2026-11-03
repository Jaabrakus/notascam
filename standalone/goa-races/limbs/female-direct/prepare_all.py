"""Stage all registered female identities without changing their original art."""
import json
from pathlib import Path
import sys
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import build as geometry


def main():
    jobs = json.loads((HERE.parents[1] / 'female-animations/manifest.json').read_text())
    prior_path = HERE / 'all-catalog.json'
    prior = {r['id']: r for r in json.loads(prior_path.read_text())} if prior_path.exists() else {}
    catalog = []
    for job in jobs:
        source_folder = Path(job['folder'])
        source = source_folder / 'corrected.png'
        if not source.exists():
            source = source_folder / 'generated.png'
        folder = HERE / 'all' / job['race'] / job['appearance']
        folder.mkdir(parents=True, exist_ok=True)
        record = dict(id=job['id'], race=job['race'], appearance=job['appearance'], sex='female',
                      targetHeight=job['targetHeight'], folder=str(folder), source=str(source),
                      reference=str(folder / 'reference.png'), features=job['features'],
                      sourceStatus='missing', categories={})
        for category in ('arms', 'legs'):
            # Reuse the three already completed base-female sheets.
            previous = HERE / (job['race'] + '-female-' + category + '-v1.png')
            output = previous if job['appearance'] == 'base' and previous.exists() else folder / (category + '-v1.png')
            selected = prior.get(job['id'], {}).get('categories', {}).get(category, {}).get('path')
            if selected and Path(selected).exists():
                output = Path(selected)
            record['categories'][category] = dict(path=str(output), status='generated' if output.exists() else 'pending')
        if Path(record['reference']).exists() and (folder / 'normal64.png').exists():
            record['sourceStatus'] = 'ready'
            record['source'] = prior.get(job['id'], {}).get('source', record['source'])
            catalog.append(record)
            continue
        if source.exists():
            try:
                with Image.open(source) as image:
                    image = image.convert('RGBA')
                    grid, _ = geometry.measured_grid(image, 4, 3, job['id'])
                    cells = [image.crop((x, y, x + w, y + h)) for x, y, w, h in grid[0]]
                    boxes = [cell.getchannel('A').point(lambda a: 255 if a >= 128 else 0).getbbox() for cell in cells]
                    scale = min(job['targetHeight'] * 4 / max(b[3] - b[1] for b in boxes), 240 / max(b[2] - b[0] for b in boxes))
                    reference = Image.new('RGBA', (1024, 256))
                    normal = Image.new('RGBA', (256, 64))
                    for view, (cell, box) in enumerate(zip(cells, boxes)):
                        crop = cell.crop(box)
                        large = crop.resize((round(crop.width * scale), round(crop.height * scale)), Image.Resampling.NEAREST)
                        reference.alpha_composite(large, (view * 256 + (256 - large.width) // 2, 248 - large.height))
                        small = crop.resize((round(crop.width * scale / 4), round(crop.height * scale / 4)), Image.Resampling.NEAREST)
                        normal.paste(small, (view * 64 + (64 - small.width) // 2, 62 - small.height))
                    reference.save(record['reference'])
                    normal.save(folder / 'normal64.png')
                record['sourceStatus'] = 'ready'
            except (ValueError, OSError) as error:
                record['sourceStatus'] = 'reference error: ' + str(error)
        catalog.append(record)
    (HERE / 'all-catalog.json').write_text(json.dumps(catalog, indent=2) + '\n')
    print(json.dumps({'appearances': len(catalog), 'ready': sum(r['sourceStatus'] == 'ready' for r in catalog),
                      'remainingAIsheets': sum(c['status'] == 'pending' for r in catalog for c in r['categories'].values()),
                      'unavailable': [r['id'] for r in catalog if r['sourceStatus'] != 'ready']}))


if __name__ == '__main__':
    main()
