"""Publish distinctly named hybrid walk assets and an honest coverage manifest."""
from pathlib import Path
import json,shutil,zipfile,hashlib
from PIL import Image,ImageDraw
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
def slug(s):return s.replace(' ','-')
def main():
 jobs=json.loads((HERE/'manifest.json').read_text())
 registered=json.loads((HERE/'registration.json').read_text())
 out=HERE/'exports';out.mkdir(exist_ok=True)
 coverage=[]
 for job in jobs:
  ready=job['id'] in registered
  record=dict(race=job['race'],appearance=job['appearance'],id=job['id'],status='generated walk draft' if ready else 'pending')
  if ready:
   source=Path(job['folder']);name=slug(job['race'])+'-'+job['appearance']+'-walk'
   folder=out/slug(job['race'])/job['appearance'];folder.mkdir(parents=True,exist_ok=True)
   for old,new in [('sprites.png',name+'-64.png'),('movement.dmi',name+'-64.dmi'),('atlas.json',name+'.json'),('prompt.txt',name+'-prompt.txt'),('generation.json',name+'-generation.json')]:
    if (source/old).exists():shutil.copyfile(source/old,folder/new)
   for pattern in ['*-prompt.txt','*-generation.json']:
    for p in source.glob(pattern):shutil.copyfile(p,folder/(name+'-'+p.name))
   meta=json.loads((folder/(name+'.json')).read_text());meta['image']=name+'-64.png'
   (folder/(name+'.json')).write_text(json.dumps(meta,indent=2))
   record['image']=str((folder/(name+'-64.png')).relative_to(out))
   record['sha256']=hashlib.sha256((folder/(name+'-64.png')).read_bytes()).hexdigest()
  coverage.append(record)
 assert len({r['sha256'] for r in coverage if 'sha256' in r})==len(registered),'Duplicate artwork across named hybrids'
 for race in dict.fromkeys(j['race'] for j in jobs):
  members=[j for j in jobs if j['race']==race and j['id'] in registered]
  standing=Image.new('RGBA',(256,len(members)*64))
  review=Image.new('RGB',(528,len(members)*404),(21,33,39));draw=ImageDraw.Draw(review)
  for row,j in enumerate(members):
   im=Image.open(Path(j['folder'])/'sprites.png').convert('RGBA')
   standing.paste(im.crop((0,0,256,64)),(0,row*64))
   draw.text((8,row*404+4),race+' / '+j['appearance'],fill='white')
   tile=im.resize((512,384),Image.Resampling.NEAREST);review.paste(tile,(8,row*404+20),tile)
  standing.save(out/slug(race)/(slug(race)+'-hybrids-standing-64.png'))
  review.save(out/slug(race)/(slug(race)+'-hybrids-labeled-review.png'))
 (out/'coverage.json').write_text(json.dumps(coverage,indent=2))
 (out/'README.md').write_text('Hybrid walk drafts, generated with the built-in image generation tool from approved four-view designs. Each PNG has 64x64 cells, columns South/North/East/West and three pose rows. Replay 0,1,0,2 at 200ms. DMI files contain this explicit four-phase movement loop. Race and appearance names are retained in every filename. See coverage.json for pending assets. These drafts require visual gait and identity review before game integration. Female bodies, attacks, sleep and limb-loss states are outside this export; limb loss is handled separately. Prompts and generation provenance accompany each sheet.\n')
 target=ROOT/'Dungeon Master Sample/GOA Hybrid Walk Animations.zip'
 with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
  for p in out.rglob('*'):
   if p.is_file():z.write(p,p.relative_to(out))
 print(json.dumps(dict(ready=len(registered),total=len(jobs),archive=str(target))))
if __name__=='__main__':main()
