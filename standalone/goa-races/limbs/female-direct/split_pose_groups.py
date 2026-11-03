"""Split native corrective atlases into complete-pose review overrides.

This performs layout extraction only. Acceptance is a separate visual decision;
pack_all.py ignores every override until its metadata says visualReview=accepted.
"""
import argparse
import json
from pathlib import Path
from PIL import Image
from pack import geometry


def split(metadata_path):
    metadata_path = Path(metadata_path)
    group = json.loads(metadata_path.read_text())
    source = Path(group['path'])
    image = Image.open(source).convert('RGBA')
    rectangles, segmentation = geometry.measured_grid(image, len(group['jobs']), 1, source.name)
    for job, rectangle in zip(group['jobs'], rectangles[0]):
        folder = Path(job['folder']) / 'overrides'
        folder.mkdir(exist_ok=True)
        destination = folder / f"{job['category']}-row{job['row']}-{job['view']}.png"
        if destination.with_suffix('.json').exists():
            existing = json.loads(destination.with_suffix('.json').read_text())
            if existing.get('visualReview') == 'accepted':
                continue
        x, y, width, height = rectangle
        image.crop((x, y, x + width, y + height)).save(destination)
        record = dict(job, source=str(source), sourceRect=rectangle, segmentation=segmentation,
                      prompt=group['prompt'], method='native corrective complete pose; layout extraction only',
                      visualReview='pending')
        destination.with_suffix('.json').write_text(json.dumps(record, indent=2) + '\n')
        destination.with_suffix('.prompt.txt').write_text(group['prompt'])
        print(destination)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('metadata', nargs='+', type=Path)
    for path in parser.parse_args().metadata:
        split(path)
