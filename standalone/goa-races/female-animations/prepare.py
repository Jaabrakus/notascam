"""Stage female appearance and walk references, without changing existing art."""
from pathlib import Path
from PIL import Image
import json,shutil
HERE=Path(__file__).resolve().parent
MALE=HERE.parent/'hybrid-animations'
BASE=HERE.parent/'hybrids/packed'
RACES=['Human','HumanBlack','Dwarves','Elf','Night Elf','Orc','Goblins','Kobold','FrogMan','LizardMan']
KINDS=['base','Possessed1','Possessed2','Marked','Ashen','Hellblooded','Werewolf','Zombie']
HEIGHTS=dict(Human=56,HumanBlack=56,Dwarves=46,Elf=59,Orc=57,Goblins=43,Kobold=45,FrogMan=54,LizardMan=54)
HEIGHTS['Night Elf']=59
FEATURES={
 'Human':'fair peach skin, dark eyes, chestnut brown hair tied back, human round ears',
 'HumanBlack':'deep warm brown skin, dark eyes, dark brown coiled hair tied back, human round ears',
 'Dwarves':'short broad sturdy dwarf body, warm tan skin, dark eyes, auburn hair in a short braid, no beard',
 'Elf':'fair skin, BLUE eyes, long golden BLOND hair, long pointed elf ears, tall slender race silhouette',
 'Night Elf':'navy BLUE skin, RED eyes, long SILVER hair, very long pointed ears, tall slender race silhouette',
 'Orc':'GREEN skin, red eyes, small ivory tusks, pointed ears, strong broad body, dark hair tied back',
 'Goblins':'small wiry dark OLIVE body, yellow eyes, long pointed ears, short dark hair',
 'Kobold':'small OCHRE OLIVE body, yellow eyes, broad swept pointed ears, keep kobold face, no human hairstyle',
 'FrogMan':'GREEN frog face, large round eyes, broad mouth, amphibian hands and feet, no human hair',
 'LizardMan':'TEAL reptile scales, yellow slit eyes, reptile snout, small head ridges, tapered reptile tail visible from north, no human hair'
}
def main():
 jobs=[]
 for race in RACES:
  base=Image.open(BASE/race/'base/sprites.png').convert('RGBA')
  for kind in KINDS:
   folder=HERE/'assets'/race/kind;folder.mkdir(parents=True,exist_ok=True)
   source=BASE/race/'base/sprites.png' if kind=='base' else MALE/'assets'/race/kind/'sprites.png'
   shutil.copyfile(source,folder/'male-motion-guide.png')
   base.crop((0,0,256,64)).save(folder/'race-reference.png')
   if kind!='base':
    im=Image.open(source);im.crop((0,0,256,64)).save(folder/'hybrid-reference.png')
   jobs.append(dict(id=race+'/Female/'+kind,race=race,sex='female',appearance=kind,features=FEATURES[race],folder=str(folder),targetHeight=HEIGHTS[race],status='pending'))
 (HERE/'manifest.json').write_text(json.dumps(jobs,indent=2));print(json.dumps(jobs))
if __name__=='__main__':main()
