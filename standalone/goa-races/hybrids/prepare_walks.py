from pathlib import Path
import sys
from PIL import Image
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'full-states'))
from prepare import inspect
SOURCE=HERE.parents[1]/'remastered/game/Icons/Remastered/Races64'
for name in ['Human','Dwarves','Night Elf','Orc','Goblins','Kobold']:
 p=SOURCE/(name+'.dmi');meta=inspect(p);im=Image.open(p)
 state=next(s for s in meta['states'] if s['dirs']==4 and s['frames']>=3 and s['name'] in ('','Normal'))
 sheet=Image.new('RGBA',(256,192))
 for f in range(3):
  for d in range(4):
   i=state['offset']+f*4+d;x=i%meta['columns']*64;y=i//meta['columns']*64
   sheet.paste(im.crop((x,y,x+64,y+64)),(d*64,f*64))
 sheet.save(HERE/'references'/(name+'-walk-poses.png'))
print('Prepared six original walk pose guides.')
