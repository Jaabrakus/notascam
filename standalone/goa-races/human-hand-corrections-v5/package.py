"""Synchronize canonical Human PNG/DMI sheets and sample download archives."""
from pathlib import Path
from PIL import Image,PngImagePlugin
import json,hashlib,zipfile
HERE=Path(__file__).resolve().parent;ART=HERE.parent;ROOT=ART.parents[1];SAMPLE=ROOT/'Dungeon Master Sample'
records=[]
for race in ['Human','HumanBlack']:
 for kind in ['base','Possessed1','Possessed2','Marked','Ashen','Hellblooded','Werewolf','Zombie']:
  folder=ART/'hybrids/packed'/race/kind;im=Image.open(folder/'sprites.png').convert('RGBA');assert im.size==(256,192)
  replay=Image.new('RGBA',(256,256))
  for row,frame in enumerate([0,1,0,2]):replay.paste(im.crop((0,frame*64,256,(frame+1)*64)),(0,row*64))
  info=PngImagePlugin.PngInfo();info.add_text('Description','# BEGIN DMI\nversion = 4.0\n\twidth = 64\n\theight = 64\nstate = ""\n\tdirs = 4\n\tframes = 4\n\tdelay = 2,2,2,2\n\tmovement = 1\n# END DMI\n',zip=True)
  replay.save(folder/'movement.dmi',format='PNG',pnginfo=info)
  meta=json.loads((folder/'atlas.json').read_text());meta.update(image='sprites.png',race=race,appearance=kind,frameSize=[64,64],directionOrder=['South','North','East','West'],frames=3,sequence=[0,1,0,2],frameDurationMs=200)
  meta.setdefault('revision','v6-full-redrawn-frames');(folder/'atlas.json').write_text(json.dumps(meta,indent=2))
  records.append(dict(race=race,appearance=kind,png=str(folder/'sprites.png'),dmi=str(folder/'movement.dmi'),sha256=hashlib.sha256((folder/'sprites.png').read_bytes()).hexdigest()))
readme='Male Human sprites\n\n16 male Human/HumanBlack appearances. PNG: 256x192, 64x64 cells, columns South/North/East/West; rows idle, walk A, walk B. Replay 0,1,0,2 at 200ms. movement.dmi is the same explicit 4-phase BYOND movement loop, with metadata. Normal and Possessed1 Humans use full approved side-view frames; other appearances use full redrawn side-idle frames. atlas.json identifies every sheet. Other action poses remain in the separate combat library.\n'
(ART/'hybrids/packed/MALE-HUMAN-SHEETS.md').write_text(readme)
with zipfile.ZipFile(SAMPLE/'GOA Male Human Sprites.zip','w',zipfile.ZIP_DEFLATED) as z:
 z.writestr('README.md',readme)
 for r in records:
  folder=Path(r['png']).parent
  for name in ['sprites.png','movement.dmi','atlas.json']:z.write(folder/name,Path(r['race'])/r['appearance']/name)
with zipfile.ZipFile(SAMPLE/'GOA Updated Races and Hybrids.zip','w',zipfile.ZIP_DEFLATED) as z:
 for p in (ART/'hybrids/packed').rglob('*'):
  if p.is_file():z.write(p,p.relative_to(ART/'hybrids/packed'))
# Keep the combat bundle's existing action content and include the current review/idle sources.
combat=SAMPLE/'GOA Human Combat Samples.zip';members={}
if combat.exists():
 with zipfile.ZipFile(combat) as z:members={n:z.read(n) for n in z.namelist() if not n.endswith('/')}
with zipfile.ZipFile(combat,'w',zipfile.ZIP_DEFLATED) as z:
 for n,b in members.items():
  if n not in ['index.html','GOA Human Combat Sample.html','GOA Male Human Idle Hand Redraws.html'] and not n.startswith('Human Sprites/'):z.writestr(n,b)
 z.write(SAMPLE/'GOA Human Combat Sample.html','index.html');z.write(SAMPLE/'GOA Male Human Idle Hand Redraws.html','GOA Male Human Idle Hand Redraws.html')
 for r in records:
  for name in ['sprites.png','movement.dmi','atlas.json']:z.write(Path(r['png']).parent/name,Path('Human Sprites')/r['race']/r['appearance']/name)
(HERE/'published-locations.json').write_text(json.dumps(dict(sheets=records,archives=[str(SAMPLE/n) for n in ['GOA Male Human Sprites.zip','GOA Updated Races and Hybrids.zip','GOA Human Combat Samples.zip','GOA Hybrid Walk Animations.zip']]),indent=2));print('Packaged 16 canonical Human sheets and synchronized PNG/DMI downloads.')
