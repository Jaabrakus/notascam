from pathlib import Path
import sys,json
from PIL import Image
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'full-states'))
from prepare import inspect
SOURCE=HERE.parents[1]/'remastered/game/Icons/Remastered/Races64'
RACES={'Human':'Human','HumanBlack':'HumanBlack','Dwarves':'Dwarf','Night Elf':'Night Elf','Orc':'Orc','Goblins':'Goblin','Kobold':'Kobold','FrogMan':'FrogMan','LizardMan':'LizardMan'}
KINDS=['Possessed1','Possessed2','Marked','Ashen','Hellblooded','Werewolf','Zombie']
entries=[]
for source,label in RACES.items():
 ref=Image.new('RGBA',(1024,256))
 if source in ['HumanBlack','FrogMan','LizardMan']:
  im=Image.open(HERE.parent/'sprite-engine/converted'/source/'sprites.png')
  for d in range(4):ref.paste(im.crop((d*64,0,d*64+64,64)).resize((256,256),Image.Resampling.NEAREST),(d*256,0))
 else:
  for d,dir in enumerate(['south','north','east','west']):
   im=Image.open(HERE.parent/'all-races/sprites'/f'{label}-{dir}.png').convert('RGBA')
   ref.alpha_composite(im, (d*256+(256-im.width)//2,250-im.height))
 ref.save(HERE/'references'/f'{source}-approved.png')
 contact=Image.new('RGBA',(256,448))
 for row,kind in enumerate(KINDS):
  path=SOURCE/f'{source}-{kind}.dmi';meta=inspect(path);im=Image.open(path)
  state=next(s for s in meta['states'] if s['dirs']==4 and s['name'] in ('','Normal'))
  for d in range(4):
   index=state['offset']+d;x=index%meta['columns']*64;y=index//meta['columns']*64
   contact.paste(im.crop((x,y,x+64,y+64)),(d*64,row*64))
 contact.save(HERE/'references'/f'{source}-source-variants.png')
 entries.append(dict(race=source,label=label,reference=str(HERE/'references'/f'{source}-approved.png'),source=str(HERE/'references'/f'{source}-source-variants.png'),rows=KINDS))
(HERE/'manifest.json').write_text(json.dumps(entries,indent=2))
print('Prepared 9 updated body references and 63 source variant designs (252 views).')
