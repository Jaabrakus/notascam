"""Package native AI north-view edits; preserve all other registered cells byte-for-byte."""
from pathlib import Path
from PIL import Image
import json,shutil
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent
records=json.loads((HERE/'registration.json').read_text());report=[]
def bbox(im):return im.getchannel('A').point(lambda a:255 if a>128 else 0).getbbox()
for item in records:
 name=item['name'];old=Image.open(item['registered']).convert('RGBA');out=old.copy();size=item['size'];native=Image.open(HERE/(name+'-north-output.png')).convert('RGBA');rows=item['editRows']
 for j,row in enumerate(rows):
  oldcell=old.crop((size,row*size,size*2,(row+1)*size));target=bbox(oldcell)
  candidate=native.crop((0,round(j*native.height/len(rows)),native.width,round((j+1)*native.height/len(rows))));region=bbox(candidate)
  cell=Image.new('RGBA',(size,size));cell.paste(candidate.crop(region).resize((target[2]-target[0],target[3]-target[1]),Image.Resampling.NEAREST),target[:2]);out.paste(cell,(size,row*size))
 count=0
 for row in range(item['rows']):
  for d in range(4):
   if d==1 and row in rows:continue
   box=(d*size,row*size,(d+1)*size,(row+1)*size)
   assert old.crop(box).tobytes()==out.crop(box).tobytes();count+=1
 output=HERE/(name+'-north-fixed.png');out.save(output)
 active=Path(item['original']);backup=active.with_name(active.stem+'-before-north-fix.png')
 if not backup.exists():shutil.copyfile(active,backup)
 shutil.copyfile(output,active)
 sample=ROOT.parents[1]/'Dungeon Master Sample';shutil.copyfile(output,sample/(name+' - North Wings Fixed.png'))
 report.append(dict(name=name,changed_rows=rows,unchanged_cells_verified=count,changed_direction='North',source_registration=item['sourceRects'],output=str(output)))
(HERE/'verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
