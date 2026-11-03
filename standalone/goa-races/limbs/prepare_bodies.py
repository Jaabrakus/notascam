"""Extract canonical approved standing body references without repainting."""
from pathlib import Path
from PIL import Image
import json
HERE=Path(__file__).resolve().parent
REG=HERE.parent/'armory/bodies.json'
data=json.loads(REG.read_text())
out=[]
for b in data['bodies']:
 if b['variant']!='Base' or b['status']=='flight':continue
 im=Image.open(b['source']).convert('RGBA');sheet=Image.new('RGBA',(1024,256))
 for view in range(4):
  x,y,w,h=b['sourceRects'][0][view];l,t,r,bot=b['frameBounds'][0][view]
  cell=im.crop((x,y,x+w,y+h));scale=b['targetHeight']/b['normalization']['referenceHeight']*4
  ww,hh=round(w*scale),round(h*scale);cell=cell.resize((ww,hh),Image.Resampling.NEAREST)
  dx=round(128-(l+r)*.5*scale);dy=round(244-bot*scale)
  sheet.alpha_composite(cell,(view*256+dx,dy))
 race=b['raceKey'];path=HERE/'references'/(race+'-approved-body.png');sheet.save(path)
 out.append(dict(race=race,label=b['label'],reference=str(path),bodyId=b['id'],source=b['source'],targetHeight=b['targetHeight']))
(HERE/'body-references.json').write_text(json.dumps(out,indent=2))
print('Prepared',len(out),'canonical base references.')
