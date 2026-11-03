from pathlib import Path
import base64,json
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
def src(p):return 'data:image/png;base64,'+base64.b64encode(p.read_bytes()).decode()
def main():
 data={}
 registrations=json.loads((HERE/'walk-registration.json').read_text())
 variants=json.loads((HERE/'variant-registration.json').read_text())
 animations_file=HERE.parent/'hybrid-animations/registration.json'
 animations=json.loads(animations_file.read_text()) if animations_file.exists() else {}
 for race,label in [('Human','Human'),('HumanBlack','Human (dark)'),('Dwarves','Dwarf'),('Elf','Elf'),('Night Elf','Dark Elf'),('Orc','Orc'),('Goblins','Goblin'),('Kobold','Kobold'),('FrogMan','Frogman'),('LizardMan','Lizardman')]:
  base=HERE/'sheets/Elf-base.png' if race=='Elf' else HERE/'references'/(race+'-approved.png')
  walk=HERE/'walks'/(race+'.png')
  data[race]=dict(label=label,variants=src(HERE/'sheets'/(race+'.png')),base=src(base),walk=src(walk) if walk.exists() else None)
  if race in registrations:data[race]['walkRects']=registrations[race]['rects']
  if race in ['Human','HumanBlack']:
   approved=HERE/'packed'/race/'base/sprites.png'
   if approved.exists():
    data[race]['walk']=src(approved)
    data[race]['walkRects']=[dict(source=[v*64,r*64,64,64],destination=[v*64,r*64,64,64]) for r in range(3) for v in range(4)]

  data[race]['variantRects']=variants[race]['rects']
  data[race]['hybridWalks']={key.split('/',1)[1]:src(Path(value['path'])) for key,value in animations.items() if key.startswith(race+'/')}
 corrections=HERE.parent/'wing-corrections'
 for name in ['DemonFly','GargoyleFly']:
  data[name]=dict(label=name+' · north wings fixed',variants=None,base=None,walk=src(corrections/(name+'-north-fixed.png')),frames=2,sequence=[0,1],motion='flight')
 data['VampireFly']=dict(label='Vampire flying · approved design',variants=None,base=src(corrections/'Vampire-flight-approved-north-fixed.png'),walk=None,note='Approved flying appearance; complete flying animation pending.')
 from PIL import Image
 g=Image.open(HERE/'sheets/Gargoyle-eyes.png');s=g.height//6;stand=HERE/'references/Gargoyle-color-base.png';g.crop((0,0,g.width,s)).save(stand)
 data['Gargoyle variants']=dict(label='Gargoyle eye variants · north fixed',variants=src(HERE/'sheets/Gargoyle-eyes.png'),base=src(stand),walk=None,kinds=['Amber ground','Ice ground','Red ground','Amber flying','Ice flying','Red flying'])
 data['Gargoyle variants']['variantRects']=variants['Gargoyle-eyes']['rects']
 html=(HERE/'gallery.template.html').read_text().replace('/*DATA*/null',json.dumps(data,separators=(',',':'))).replace('/*APP*/',(HERE/'gallery.js').read_text())
 (HERE/'index.html').write_text(html)
 (ROOT/'Dungeon Master Sample/GOA Races and Hybrids.html').write_text(html)
 print('Built gallery:',len(data),'races,',sum(bool(d['walk']) for d in data.values()),'updated walk sheets.')
if __name__=='__main__':main()
