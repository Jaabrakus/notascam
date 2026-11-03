"""Extract complete native both-arm-loss poses as review-only overrides."""
import argparse
import json
from pathlib import Path
from PIL import Image
from pack import measured_grid, packing


def split(path):
    path=Path(path)
    metadata=json.loads(path.with_suffix('.json').read_text())
    image=Image.open(path).convert('RGBA')
    grid=measured_grid(image,4,len(metadata['jobs']),path.name)
    for job, rectangles in zip(metadata['jobs'],grid):
        folder=Path(job['folder'])/'overrides'
        folder.mkdir(exist_ok=True)
        for direction, rectangle in zip(packing.DIRECTIONS,rectangles):
            output=folder/('arms-row2-'+direction+'.png')
            x,y,w,h=rectangle
            image.crop((x,y,x+w,y+h)).save(output)
            record=dict(id=job['id'],category='arms',row=2,view=direction,
                        reference=metadata['reference'],source=str(path),sourceRect=rectangle,
                        nativeOutput=metadata['nativeOutput'],prompt=metadata['prompt'],
                        method='native complete both-arm-loss pose; layout extraction only',visualReview='pending')
            output.with_suffix('.json').write_text(json.dumps(record,indent=2)+'\n')
            output.with_suffix('.prompt.txt').write_text(metadata['prompt'])
    print(path)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('paths',nargs='+',type=Path)
    for path in parser.parse_args().paths:
        split(path)
