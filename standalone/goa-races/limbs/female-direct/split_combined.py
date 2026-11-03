"""Extract complete native atlas rows; do not edit body artwork."""
import argparse
import json
from pathlib import Path
from PIL import Image
from pack import measured_grid


def split(path):
    path = Path(path)
    image = Image.open(path).convert('RGBA')
    rectangles = measured_grid(image, 4, 6, path.name)
    cut = rectangles[3][0][1]
    source = json.loads(path.with_suffix('.json').read_text())
    for category, box, rows in [('arms',(0,0,image.width,cut),[0,1,2]),('legs',(0,cut,image.width,image.height),[3,4,5])]:
        output = path.parent / (category+'-v1.png')
        image.crop(box).save(output)
        metadata = dict(source, category=category, sourceRect=box, sourceRows=rows,
                        method='native six-state female edit; complete-row extraction only')
        output.with_suffix('.json').write_text(json.dumps(metadata,indent=2)+'\n')
        output.with_suffix('.prompt.txt').write_text(source['prompt'])
    print(path.parent)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('paths',nargs='+',type=Path)
    for path in parser.parse_args().paths:
        split(path)
