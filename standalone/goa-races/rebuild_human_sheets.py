"""Rebuild complete male Human frames from the saved redraws, not arm/nose patches."""
from pathlib import Path
from PIL import Image,PngImagePlugin
import json,hashlib,shutil,sys
ART=Path(__file__).resolve().parent;ROOT=ART.parents[1];SAMPLE=ROOT/'Dungeon Master Sample';BUILD=ART/'human-sheet-rebuild-v6';BUILD.mkdir(exist_ok=True)
KINDS=['base','Possessed1','Possessed2','Marked','Ashen','Hellblooded','Werewolf','Zombie'];records=[]
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dmi(im,path):
 replay=Image.new('RGBA',(256,256))
 for row,f in enumerate([0,1,0,2]):replay.paste(im.crop((0,f*64,256,(f+1)*64)),(0,row*64))
 info=PngImagePlugin.PngInfo();info.add_text('Description','# BEGIN DMI\nversion = 4.0\n\twidth = 64\n\theight = 64\nstate = ""\n\tdirs = 4\n\tframes = 4\n\tdelay = 2,2,2,2\n\tmovement = 1\n# END DMI\n',zip=True);replay.save(path,format='PNG',pnginfo=info)
walkreg=json.loads((ART/'hybrids/walk-registration.json').read_text())
flat=SAMPLE/'Human Sprites';flat.mkdir(exist_ok=True)
for race in ['Human','HumanBlack']:
 for kind in KINDS:
  original=ART/'human-hand-corrections-v1/before'/race/kind/'sprites.png'
  before=Image.open(original).convert('RGBA');sheet=before.copy();frames=[]
  folder=ART/'hybrids/packed'/race/kind;output=BUILD/race/kind;output.mkdir(parents=True,exist_ok=True)
  previous=BUILD/'previous'/race/kind;previous.mkdir(parents=True,exist_ok=True)
  for name in ['sprites.png','atlas.json','movement.dmi']:
   src=folder/name
   if src.exists() and not (previous/name).exists():shutil.copy2(src,previous/name)
  for row in (range(3) if kind in ['base','Possessed1'] else [0]):
   for view in [2,3]:
    if kind in ['base','Possessed1']:src=ART/'human-hand-corrections-v5'/race/kind/f'{view}-{row}-registered.png'
    else:src=ART/'human-hand-corrections-v4'/race/kind/(('east' if view==2 else 'west')+'-registered.png')
    frame=Image.open(src).convert('RGBA');assert frame.size==(64,64) and frame.getbbox()
    # Remove the generated image's faint background halo when packing pixel-art frames.
    frame.putalpha(frame.getchannel('A').point(lambda a:255 if a>=128 else 0))
    clean=output/f'{view}-{row}-full-frame.png';frame.save(clean)
    sheet.paste(frame,(view*64,row*64));assert sheet.crop((view*64,row*64,(view+1)*64,(row+1)*64)).tobytes()==frame.tobytes()
    frames.append(dict(view=view,row=row,source=str(src.relative_to(ROOT)),sourceSha256=digest(src),packedFrame=str(clean.relative_to(ROOT)),packedSha256=digest(clean)))
  for row in range(3):
   for view in [0,1]:assert sheet.crop((view*64,row*64,(view+1)*64,(row+1)*64)).tobytes()==before.crop((view*64,row*64,(view+1)*64,(row+1)*64)).tobytes()
  sheet.save(output/'sprites.png');sheet.save(folder/'sprites.png');dmi(sheet,folder/'movement.dmi');shutil.copy2(folder/'movement.dmi',output/'movement.dmi')
  meta=dict(format='goa-human-rebuilt-sheet',race=race,sex='male',appearance=kind,image='sprites.png',revision='v6-full-redrawn-frames',frameSize=[64,64],directionOrder=['South','North','East','West'],frames=3,sequence=[0,1,0,2],frameDurationMs=200,assembly='Full registered redraw cells replace previous side-view frames; no arm/nose patch compositing.',redrawnFrames=frames)
  for dest in [folder/'atlas.json',output/'atlas.json']:dest.write_text(json.dumps(meta,indent=2))
  if kind!='base':
   anim=ART/'hybrid-animations/assets'/race/kind;overrides=anim/'full-frames-v6';overrides.mkdir(exist_ok=True)
   shutil.copy2(folder/'sprites.png',anim/'sprites.png');shutil.copy2(folder/'movement.dmi',anim/'movement.dmi');(anim/'atlas.json').write_text(json.dumps(meta,indent=2))
   override_records=[]
   for row in range(3):
    for view in [2,3]:
     name=f'{view}-{row}.png';sheet.crop((view*64,row*64,(view+1)*64,(row+1)*64)).save(overrides/name);override_records.append(dict(column=view,row=row,image='full-frames-v6/'+name))
   (anim/'frame-overrides.json').write_text(json.dumps(override_records,indent=2))
  else:
   native=ART/'hybrids/walks'/(race+'.png');saved=previous/'walk-source.png'
   if not saved.exists():shutil.copy2(native,saved)
   sheet.save(native);walkreg[race]=dict(targetMaxHeight=56,footBaseline=62,uniformScale=1,rects=[dict(column=v,row=r,source=[v*64,r*64,64,64],destination=[v*64,r*64,64,64]) for r in range(3) for v in range(4)])
  name=f'{race}-Male-{kind}-64';shutil.copy2(folder/'sprites.png',flat/(name+'.png'));shutil.copy2(folder/'movement.dmi',flat/(name+'.dmi'));flatmeta={**meta,'image':name+'.png'};(flat/(name+'.json')).write_text(json.dumps(flatmeta,indent=2))
  record=dict(race=race,appearance=kind,sha256=digest(folder/'sprites.png'),fullFrames=len(frames),sources=frames,source=str((folder/'sprites.png').relative_to(ROOT)))
  records.append(record)
(ART/'hybrids/walk-registration.json').write_text(json.dumps(walkreg,indent=2))
# Refresh registry hashes and frame bounds while keeping other races' records intact.
sys.path.insert(0,str(ART/'armory'));from body_registry import refresh_human_sources
p=ART/'armory/bodies.json';registry=json.loads(p.read_text());registry['bodies']=refresh_human_sources(registry['bodies']);p.write_text(json.dumps(registry,indent=2))
report=dict(sheets=len(records),fullRedrawnCells=sum(r['fullFrames'] for r in records),cellSize=[64,64],allInsertedCellsMatchRegisteredRedraws=True,southNorthUnchanged=True,records=records)
(BUILD/'verification.json').write_text(json.dumps(report,indent=2));(flat/'manifest.json').write_text(json.dumps(report,indent=2))
(flat/'README.md').write_text('Rebuilt male Human sheets\n\nThese 16 PNG sheets use the full saved redraw frames, not patches over the old bodies. Each PNG is 256x192 with 64x64 cells; columns South/North/East/West; rows idle/walk A/walk B. Replay 0,1,0,2 at 200ms. Normal and Possessed1 use all six approved side-view redraws; remaining variants use their two redrawn side-idle frames and retain existing walking poses. DMI and JSON companions are included. manifest.json records exact redraw sources and checks.\n')
for race in ['Human','HumanBlack']:
 sheet=Image.open(ART/'hybrids/packed'/race/'base/sprites.png');sheet.resize((1024,768),Image.Resampling.NEAREST).save(flat/(race+'-rebuilt-sheet-preview.png'))
print(json.dumps({k:v for k,v in report.items() if k!='records'}))

if '--publish' in sys.argv:
 import subprocess
 scripts=[
  'human-hand-corrections-v5/build_review.py',
  'human-hand-corrections-v5/publish_approved.py',
  'hybrid-animations/publish.py',
  'hybrids/build_gallery.py',
  'armory/build.py',
  'held-equipment-demo/build.py',
  'human-hand-corrections-v5/package.py',
  'armory/export_samples.py',
  'human-hand-corrections-v5/organize_sample.py',
  'sync_sample_collection.py',
  'human-sheet-rebuild-v6/build_index.py',
  'human-sheet-rebuild-v6/verify.py',
 ]
 for script in scripts:subprocess.run([sys.executable,str(ART/script)],cwd=ROOT,check=True)
