"""Build a separate female gallery and distinctly named game sprite exports."""
from pathlib import Path
from PIL import Image,ImageDraw
import json,base64,shutil,zipfile,hashlib
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
ART=HERE.parent/'hybrids'
def src(p):return 'data:image/png;base64,'+base64.b64encode(p.read_bytes()).decode()
def slug(s):return s.replace(' ','-')
def main():
 jobs=json.loads((HERE/'manifest.json').read_text());reg=json.loads((HERE/'registration.json').read_text());data={};coverage=[]
 out=HERE/'exports';out.mkdir(exist_ok=True)
 for race in dict.fromkeys(j['race'] for j in jobs):
  members=[j for j in jobs if j['race']==race and j['id'] in reg]
  base=next((j for j in members if j['appearance']=='base'),None)
  if not base:continue
  hybrids=[j for j in members if j['appearance']!='base'];standing=Image.new('RGBA',(256,max(1,len(hybrids))*64))
  for row,j in enumerate(hybrids):standing.paste(Image.open(Path(j['folder'])/'standing.png'),(0,row*64))
  combined=HERE/'assets'/race/'female-hybrid-standing.png';standing.save(combined)
  data[race]=dict(label={'Dwarves':'Dwarf','Night Elf':'Dark Elf','Goblins':'Goblin','HumanBlack':'Human (dark)'}.get(race,race)+' · Female',variants=src(combined) if hybrids else None,kinds=[j['appearance'] for j in hybrids],base=src(Path(base['folder'])/'standing.png'),walk=src(Path(base['folder'])/'sprites.png'),hybridWalks={j['appearance']:src(Path(j['folder'])/'sprites.png') for j in hybrids})
 for j in jobs:
  ready=j['id'] in reg;record=dict(id=j['id'],race=j['race'],sex='female',appearance=j['appearance'],status='generated walk draft' if ready else 'pending')
  if ready:
   folder=out/slug(j['race'])/j['appearance'];folder.mkdir(parents=True,exist_ok=True);source=Path(j['folder']);name=slug(j['race'])+'-Female-'+j['appearance']+'-walk'
   for old,new in [('sprites.png',name+'-64.png'),('movement.dmi',name+'-64.dmi'),('standing.png',name+'-standing-64.png'),('atlas.json',name+'.json'),('prompt.txt',name+'-prompt.txt'),('generation.json',name+'-generation.json'),('correction-prompt.txt',name+'-correction-prompt.txt'),('correction-generation.json',name+'-correction-generation.json')]:
    if (source/old).exists():shutil.copyfile(source/old,folder/new)
   for pattern in ['*-correction-prompt.txt','*-correction-generation.json']:
    for extra in source.glob(pattern):shutil.copyfile(extra,folder/(name+'-'+extra.name))
   meta=json.loads((folder/(name+'.json')).read_text());meta['image']=name+'-64.png';(folder/(name+'.json')).write_text(json.dumps(meta,indent=2))
   record['image']=str((folder/(name+'-64.png')).relative_to(out));record['sha256']=hashlib.sha256((folder/(name+'-64.png')).read_bytes()).hexdigest()
  coverage.append(record)
 assert len({r['sha256'] for r in coverage if 'sha256' in r})==len(reg)
 (out/'coverage.json').write_text(json.dumps(coverage,indent=2))
 (out/'README.md').write_text('Female GOA walk drafts. PNG cells64x64; columns South/North/East/West; three pose rows; replay0,1,0,2 at200ms. The DMI stores the four-phase replay. Every file identifies race, Female and appearance. See coverage.json for available sheets. Generated with built-in image_gen; prompts/provenance included. Artwork needs visual gait/identity review before game integration. Attacks, sleep and limb loss are outside this export.\n')
 template=(ART/'gallery.template.html').read_text().replace('Updated GOA races & hybrids','Female GOA races & hybrids').replace('Updated GOA races and hybrids','Female GOA races and hybrids').replace('Approved body designs, new variant appearances, and the missing base-race walk cycles.','Female race designs, hybrid appearances and four-direction walk drafts.')
 start=template.index('<footer>');end=template.index('</footer>',start)
 template=template[:start]+'<footer>Female walk drafts in64px cells. Choose a race and appearance to inspect all four directions. Attacks, sleep and limb loss are handled separately. No live game assets are replaced.'+template[end:]
 app=(ART/'gallery.js').read_text().replace("format:'goa-updated-atlas'", "format:'goa-female-atlas',sex:'female'")
 app=app.replace("if(name==='Elf')","if(false)")
 html=template.replace('/*DATA*/null',json.dumps(data,separators=(',',':'))).replace('/*APP*/',app)
 (HERE/'index.html').write_text(html);(ROOT/'Dungeon Master Sample/GOA Female Races and Hybrids.html').write_text(html)
 target=ROOT/'Dungeon Master Sample/GOA Female Walk Animations.zip'
 with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
  for p in out.rglob('*'):
   if p.is_file():z.write(p,p.relative_to(out))
 print(json.dumps(dict(ready=len(reg),total=len(jobs),gallery=str(HERE/'index.html'),archive=str(target))))
if __name__=='__main__':main()
