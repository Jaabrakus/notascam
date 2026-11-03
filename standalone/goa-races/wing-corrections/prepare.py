from pathlib import Path
from PIL import Image
import json
HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
entries=[]
for name,job in [('DemonFly','20261029-214909-d377bfdd'),('GargoyleFly','20261029-214909-5b3b707d')]:
 path=ROOT/'sprite-engine/jobs'/job/'result.png';im=Image.open(path);w,h=im.width/4,im.height/2
 for frame in range(2):
  out=HERE/(name+'-north-'+str(frame)+'-input.png');im.crop((round(w),round(frame*h),round(2*w),round((frame+1)*h))).save(out)
  entries.append(dict(name=name,frame=frame,path=str(out),sheet=str(path),columns=4,rows=2))
path=ROOT/'hybrids/sheets/Gargoyle-eyes.png';im=Image.open(path);w,h=im.width/4,im.height/6
for row in range(3,6):
 out=HERE/('Gargoyle-eyes-north-'+str(row)+'-input.png');im.crop((round(w),round(row*h),round(2*w),round((row+1)*h))).save(out)
 entries.append(dict(name='Gargoyle-eyes',frame=row,path=str(out),sheet=str(path),columns=4,rows=6))
(HERE/'inputs.json').write_text(json.dumps(entries,indent=2))
print('Prepared seven north-only cells; all other cells will be retained.')
