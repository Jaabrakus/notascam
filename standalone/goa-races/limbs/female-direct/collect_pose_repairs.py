"""Prepare identity references and comparisons for unresolved pose reviews."""
import argparse
import json
from pathlib import Path
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
DIRECTIONS = ['South', 'North', 'East', 'West']


def collect(prefix):
    catalog = {j['id']: j for j in json.loads((HERE / 'all-catalog.json').read_text())}
    jobs = []
    for record in json.loads((HERE / 'all-packed.json').read_text()):
        for flag in record['flags']:
            for row in flag['badRows']:
                source = catalog[record['id']]
                jobs.append(dict(id=source['id'], race=source['race'], appearance=source['appearance'],
                                 folder=source['folder'], category=flag['category'], row=row, view=flag['view'],
                                 targetHeight=source['targetHeight'], reference=source['reference']))
    if not jobs:
        print(json.dumps(dict(jobs=0, groups=[])))
        return
    comparison = Image.new('RGB', (800, len(jobs)*144), (35,37,44))
    draw = ImageDraw.Draw(comparison)
    for index, job in enumerate(jobs):
        draw.text((4,index*144+4), f"{job['race']} {job['appearance']}\n{job['category']} row{job['row']} {job['view']}", fill='white')
        view = DIRECTIONS.index(job['view'])
        normal = Image.open(Path(job['folder'])/'normal64.png').convert('RGBA').crop((view*64,0,(view+1)*64,64))
        sheet = Image.open(Path(job['folder'])/'injuries64-v1.png').convert('RGBA')
        start = 1 if job['category']=='arms' else 4
        frames = [normal]+[sheet.crop((view*64,(start+r)*64,(view+1)*64,(start+r+1)*64)) for r in range(3)]
        for column, frame in enumerate(frames):
            frame=frame.resize((128,128),Image.Resampling.NEAREST)
            comparison.paste(frame,(280+column*128,index*144),frame)
    comparison.save(HERE / (prefix+'-comparison.png'))
    for start in range(0,len(jobs),12):
        comparison.crop((0,start*144,800,min(len(jobs),start+12)*144)).save(HERE/(prefix+'-comparison-%02d.png'%(start//12+1)))
    groups = []
    for category in ('arms','legs'):
        for view in ('North','South'):
            for row in (0,1):
                selected = [j for j in jobs if j['category']==category and j['view']==view and j['row']==row]
                for first in range(0,len(selected),4):
                    group = selected[first:first+4]
                    reference = Image.new('RGBA',(len(group)*256,256))
                    for column, job in enumerate(group):
                        v=DIRECTIONS.index(view)
                        src=Image.open(job['reference']).convert('RGBA').crop((v*256,0,(v+1)*256,256))
                        reference.paste(src,(column*256,0))
                        job['column']=column
                    path=HERE/(prefix+'-group-%02d-reference.png'%(len(groups)+1))
                    reference.save(path)
                    groups.append(dict(reference=str(path),category=category,view=view,row=row,jobs=group))
    (HERE/(prefix+'-groups.json')).write_text(json.dumps(groups,indent=2)+'\n')
    print(json.dumps(dict(jobs=len(jobs),groups=len(groups),manifest=str(HERE/(prefix+'-groups.json')),comparison=str(HERE/(prefix+'-comparison.png')))))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('prefix')
    collect(parser.parse_args().prefix)
