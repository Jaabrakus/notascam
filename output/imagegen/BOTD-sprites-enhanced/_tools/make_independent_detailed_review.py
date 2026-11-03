from pathlib import Path
from PIL import Image
import json
BASE=Path(__file__).resolve().parents[1]/'detailed-artwork'
plan=json.loads((BASE/'production-plan.json').read_text())
folder=BASE/'reports/independent-previews';folder.mkdir(parents=True,exist_ok=True)
for family in ['adamantium','bone','chitin','dragon','wood','hell','iron','silver','gold']:
    rp=BASE/'reports'/(family+'.json')
    if not rp.exists():continue
    report=json.loads(rp.read_text());pages=report.get('pages',[])
    for chunk in range(0,len(pages),2):
        group=pages[chunk:chunk+2];canvas=Image.new('RGB',(1500,850*len(group)),(35,40,48))
        for row,page in enumerate(group):
            native=Image.open(page['source_reference']).convert('RGB');art=Image.open(page.get('output',page.get('target',page.get('path')))).convert('RGB')
            native.thumbnail((480,820),Image.Resampling.NEAREST);art.thumbnail((1010,820),Image.Resampling.LANCZOS)
            canvas.paste(native,(0,row*850));canvas.paste(art,(490,row*850))
        path=folder/f'{family}-pages-{group[0]["page"]:02d}-{group[-1]["page"]:02d}.png';canvas.save(path)
        print(path)
