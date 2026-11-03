"""Stage the approved hybrid designs and existing motion guides. No limb-loss work."""
from pathlib import Path
from PIL import Image
import json,shutil
HERE=Path(__file__).resolve().parent
ART=HERE.parent/'hybrids'
RACES=['Human','HumanBlack','Dwarves','Elf','Night Elf','Orc','Goblins','Kobold','FrogMan','LizardMan']
KINDS=['Possessed1','Possessed2','Marked','Ashen','Hellblooded','Werewolf','Zombie']

def main():
 registrations=json.loads((ART/'walk-registration.json').read_text());jobs=[]
 for race in RACES:
  info=registrations[race];source=Image.open(ART/'walks'/(race+'.png')).convert('RGBA');guide=Image.new('RGBA',(256,192))
  for rect in info['rects']:
   x,y,w,h=rect['source'];dx,dy,dw,dh=rect['destination'];guide.paste(source.crop((x,y,x+w,y+h)).resize((dw,dh),Image.Resampling.NEAREST),(dx,dy))
  for kind in KINDS:
   folder=HERE/'assets'/race/kind;folder.mkdir(parents=True,exist_ok=True)
   reference=ART/'packed'/race/kind/'sprites.png';assert Image.open(reference).size==(256,64)
   shutil.copyfile(reference,folder/'approved-design.png');guide.save(folder/'motion-guide.png')
   target=Image.open(reference).getchannel('A').point(lambda a:255 if a>128 else 0)
   heights=[]
   for d in range(4):
    box=target.crop((d*64,0,d*64+64,64)).getbbox();heights.append(box[3]-box[1])
   jobs.append(dict(id=race+'/'+kind,race=race,appearance=kind,folder=str(folder),reference=str(folder/'approved-design.png'),motionGuide=str(folder/'motion-guide.png'),targetHeight=max(heights),status='pending'))
 (HERE/'manifest.json').write_text(json.dumps(jobs,indent=2))
 print(json.dumps(jobs))
if __name__=='__main__':main()
