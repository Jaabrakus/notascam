"""Mechanical extraction of mixed-loss references and canonical source coverage."""
from pathlib import Path
from PIL import Image
import re,json
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
SOURCE=ROOT/'standalone/remastered/game/Icons/Remastered/Races64'
BASES=['Human','HumanBlack','Dwarves','Night Elf','Orc','Goblins','Kobold','FrogMan','LizardMan','Demon','DevourerZombie','Skeleton','Gargoyle','Vampire','Elf']
ELIGIBLE=['Human','HumanBlack','Dwarves','Night Elf','Orc','Goblins','Kobold','FrogMan','LizardMan','Elf']
KINDS=['Possessed1','Possessed2','Marked','Ashen','Hellblooded','Werewolf','Zombie']
MIXED={'mixedA':['NoRightLegNoLeftArm','NoLeftLegNoRightArm','NoRightArmNoRightLeg','NoLeftArmNoLeftLeg'],
       'mixedB':['NoLegsNoRightArm','NoLegsNoLeftArm','NoArmsNoRightLeg','NoArmsNoLeftLeg']}
CANON=['Normal','NoLeftArm','NoRightArm','NoLeftLeg','NoRightLeg','NoArms','NoLegs']+MIXED['mixedA']+MIXED['mixedB']+['None']

def limbs(name):
 if name in ('Normal',''):return frozenset()
 if name=='None':return frozenset(['LeftArm','RightArm','LeftLeg','RightLeg'])
 out=[]
 for match in re.findall(r'LeftArm|RightArm|LeftLeg|RightLeg|Arms|Legs',name):out+=['LeftArm','RightArm'] if match=='Arms' else ['LeftLeg','RightLeg'] if match=='Legs' else [match]
 return frozenset(out)

def read(p):
 im=Image.open(p);text=im.info['Description'];offset=0;states=[]
 for b in re.split(r'(?=^state\s*=)',text,flags=re.M)[1:]:
  name=re.search(r'^state\s*=\s*"(.*?)"',b,re.M)[1]
  def n(k,v):
   m=re.search(r'^\s*'+k+r'\s*=\s*(\d+)',b,re.M);return int(m[1]) if m else v
  dirs,frames=n('dirs',1),n('frames',1);states.append(dict(name=name,offset=offset,dirs=dirs,frames=frames));offset+=dirs*frames
 return im.convert('RGBA'),states

def lookup(states,wanted):
 exact=next((s for s in states if s['name']==wanted and s['dirs']==4),None)
 if exact:return exact
 return next((s for s in states if s['dirs']==4 and s['name'] not in ['Armed','Normal Armed','Sneak','Tail'] and limbs(s['name'])==limbs(wanted)),None)

def frame(im,state,d):
 i=state['offset']+d;x=i%(im.width//64)*64;y=i//(im.width//64)*64
 return im.crop((x,y,x+64,y+64))

coverage=[];guide_holes=[]
for race in BASES:
 source='Human' if race=='Elf' else race
 im,states=read(SOURCE/(source+'.dmi'))
 for group,wanted in MIXED.items():
  sheet=Image.new('RGBA',(256,256));mapping=[]
  for row,name in enumerate(wanted):
   state=lookup(states,name)
   if state:
    for d in range(4):sheet.paste(frame(im,state,d),(d*64,row*64))
   else:guide_holes.append(dict(race=race,group=group,row=row,state=name))
   mapping.append(dict(requested=name,sourceState=state['name'] if state else None,offset=state['offset'] if state else None))
  sheet.save(HERE/(race+'-'+group+'-source.png'))
  (HERE/(race+'-'+group+'-source.json')).write_text(json.dumps(dict(race=race,sourceAlias=source,rows=mapping,missingRows=[r for r in mapping if r['sourceState'] is None]),indent=2))
for race in BASES:
 for kind in [None]+(KINDS if race in ELIGIBLE else []):
  source='Human' if race=='Elf' else race
  name=race+('-'+kind if kind else '');source_name=source+('-'+kind if kind else '')
  path=SOURCE/(source_name+'.dmi');im,states=read(path)
  mapped={key:lookup(states,key) for key in CANON}
  coverage.append(dict(name=name,race=race,kind=kind,source=str(path),sourceAlias='Human pose data only; new Elf identity must come from approved artwork' if race=='Elf' else None,
    canonicalStates={key:(dict(name=s['name'],dirs=s['dirs'],frames=s['frames'],offset=s['offset']) if s else None) for key,s in mapped.items()},
    missingCanonicalStates=[key for key,s in mapped.items() if not s],
    duplicateSourceNames=[n for n in set(s['name'] for s in states) if sum(s['name']==n for s in states)>1]))
summary=dict(baseRaces=len(BASES),hybridVariants=len(coverage)-len(BASES),registryEntries=len(coverage),canonicalStateCount=len(CANON),
  guideHoles=guide_holes,entries=coverage)
(HERE/'canonical-source-coverage.json').write_text(json.dumps(summary,indent=2))
print(json.dumps(dict(entries=len(coverage),guideHoles=guide_holes,entriesWithMissing=[dict(name=c['name'],missing=c['missingCanonicalStates']) for c in coverage if c['missingCanonicalStates']])))
