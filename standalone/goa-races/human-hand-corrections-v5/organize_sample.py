"""Snapshot current published GOA sprite assets into the user's sample folder."""
from pathlib import Path
import json,hashlib,collections
HERE=Path(__file__).resolve().parent;ART=HERE.parent;ROOT=ART.parents[1];OUT=ROOT/'Dungeon Master Sample/Sprites';OUT.mkdir(exist_ok=True);records=[];missing=[]
def copy(src,dst,group):
 src=Path(src);dest=OUT/dst
 if not src.is_file():missing.append(str(src));return
 data=src.read_bytes();dest.parent.mkdir(parents=True,exist_ok=True)
 if not dest.exists() or dest.read_bytes()!=data:dest.write_bytes(data)
 records.append(dict(group=group,path=str(dest.relative_to(OUT)),source=str(src.relative_to(ROOT)) if src.is_relative_to(ROOT) else str(src),bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
for folder in sorted((ART/'hybrids/packed').glob('*/*')):
 if not (folder/'sprites.png').exists():continue
 race,kind=folder.relative_to(ART/'hybrids/packed').parts
 for name in ['sprites.png','movement.dmi','atlas.json']:
  if (folder/name).exists():copy(folder/name,Path('Male')/race/kind/name,'Male')
# Additional races already have their own packed converted sheets; canonical corrected entries win.
for folder in sorted((ART/'sprite-engine/converted').iterdir()):
 if not folder.is_dir() or not (folder/'sprites.png').exists() or (OUT/'Male'/folder.name/'base/sprites.png').exists():continue
 for name in ['sprites.png','movement.dmi','atlas.json']:
  if (folder/name).exists():copy(folder/name,Path('Male')/folder.name/'base'/name,'Male')
females=json.loads((ART/'female-sprite-registry.json').read_text())
for e in females['entries']:
 target=Path('Female')/e['race']/e['appearance']
 for key,name in [('image','sprites.png'),('dmi','movement.dmi'),('metadata','atlas.json')]:copy(ART/e['walk'][key],target/name,'Female')
 for key in ['image','dmi','metadata']:
  src=ART/e['injuries'][key];copy(src,Path('Limbs/Female')/e['race']/e['appearance']/src.name,'Limbs')
 normal=(ART/e['injuries']['image']).parent/'normal64.png'
 if normal.exists():copy(normal,Path('Limbs/Female')/e['race']/e['appearance']/normal.name,'Limbs')
for src in (ART/'limbs/pixel-assets').rglob('*'):
 if src.is_file() and src.suffix in ['.png','.dmi','.json'] and not src.name.startswith(('reference','proof')):copy(src,Path('Limbs/Male')/src.relative_to(ART/'limbs/pixel-assets'),'Limbs')
combat=ART/'held-equipment-demo/combat'
for src in combat.iterdir():
 if src.is_file() and (src.name.startswith('Human-') and src.suffix in ['.png','.json'] or src.suffix=='.gif' or src.name in ['arrow.png','arrow-directions-64.png']):copy(src,Path('Combat/Human')/src.name,'Combat')
for family in ['spear-short-jab','spear-one-hand-sweep','bow','staff','universal-flinch']:
 for src in (combat/family).iterdir():
  if src.is_file() and (src.name in ['body.png','rig.json','atlas.json'] or src.suffix=='.gif'):copy(src,Path('Combat/Human')/family/src.name,'Combat')
for src in (ART/'held-equipment-demo/idle-holds').iterdir():
 if src.is_file() and src.suffix in ['.png','.json'] and src.name not in ['verification.json','gallery-preview.png']:copy(src,Path('Combat/Idle Holds')/src.name,'Combat')
u=ART/'universal-animation'
for src in (u/'exports').rglob('*'):
 if src.is_file():copy(src,Path('Animations/Universal')/src.relative_to(u/'exports'),'Animations')
for name in ['engine.js','clips.json','human-rig.json','README.md','verification.json']:copy(u/name,Path('Animations/Universal')/name,'Animations')
for src in (u/'assets').iterdir():
 if src.is_file():copy(src,Path('Animations/Universal/assets')/src.name,'Animations')
cat=json.loads((ART/'armory/catalog.json').read_text());copy(ART/'armory/equipment.js',Path('Equipment/equipment.js'),'Equipment');pathmap={}
def equipment_path(src):
 if src.is_relative_to(ROOT):return src.relative_to(ROOT)
 goa=Path('/Users/kiwimango/Downloads/GOA Source')
 if src.is_relative_to(goa):return Path('external/GOA Source')/src.relative_to(goa)
 return Path('external')/hashlib.sha256(str(src.parent).encode()).hexdigest()[:10]/src.name

for name in cat['sources']:
 src=Path(name);src=src if src.is_absolute() else ROOT/src
 dest=equipment_path(src);pathmap[name]=str(dest);copy(src,Path('Equipment')/dest,'Equipment')
for item in cat['items']:
 for name in item.get('strips',[]):
  src=Path(name);src=src if src.is_absolute() else ROOT/src;dest=equipment_path(src);pathmap[name]=str(dest);dst=Path('Equipment')/dest
  if not any(r['path']==str(dst) for r in records):copy(src,dst,'Equipment')
def rewrite(value):
 if isinstance(value,str):return pathmap.get(value,value)
 if isinstance(value,list):return [rewrite(v) for v in value]
 if isinstance(value,dict):return {k:rewrite(v) for k,v in value.items()}
 return value
catalog_data=json.dumps(rewrite(cat),indent=2).encode();(OUT/'Equipment/catalog.json').write_bytes(catalog_data)
records.append(dict(group='Equipment',path='Equipment/catalog.json',source='standalone/goa-races/armory/catalog.json',bytes=len(catalog_data),sha256=hashlib.sha256(catalog_data).hexdigest(),transformation='Portable paths for bundled equipment textures'))
copy(ROOT/'standalone/remastered/game/Interface/gear3d/gear3d-pix.json',Path('Equipment/gear3d-pix.json'),'Equipment')
# Directly identify the current equipped samples without moving their working sources.
for src in (ART/'armory/equipped-samples').rglob('*'):
 if src.is_file() and src.suffix in ['.png','.json']:copy(src,Path('Equipped')/src.relative_to(ART/'armory/equipped-samples'),'Equipped')
counts=dict(collections.Counter(r['group'] for r in records));summary=dict(files=len(records),counts=counts,bytes=sum(r['bytes'] for r in records),missingSources=missing,sourceArtRepainted=False,existingAnimationPixelsChanged=False)
(OUT/'manifest.json').write_text(json.dumps(dict(summary=summary,files=records),indent=2))
(OUT/'README.md').write_text('''# Dungeon Master sample sprites

Current published sprite sheets are organized here for easy use. Working files stay in standalone/goa-races; earlier redraw experiments are kept there as history and are excluded from this folder.

- **Male/** — race / appearance / sprites.png, atlas.json and movement.dmi where available. Human and HumanBlack include the current corrected sheets.
- **Female/** — all 80 female race/appearance walking sheets and metadata.
- **Combat/** — the existing Human attack, weapon, casting, flinch and idle-hold assets. These retain their current artwork.
- **Animations/Universal/** — existing 99 shared clip previews and rig metadata. These are mapping previews; they still require artistic review and retargeting for each body.
- **Equipment/** — existing directional gear textures, armor layers and catalog.
- **Equipped/** — exported previews with the shared equipment loadout.
- **Limbs/** — snapshots of the existing male and female limb/injury sprite work. The separate limb pipeline remains the working source.

PNG body cells are 64x64. Read each atlas.json for its direction order, state availability and timing; flight, injury and combat sheets use their own layouts. A sheet being organized here does not mark draft animation or game integration as complete.

Preview pages, armor galleries and ZIP downloads remain one folder above, in Dungeon Master Sample. Worn Armor and Idle Poses is also already there. manifest.json maps every copied file back to its working source and records a SHA-256 hash. Existing animations were copied without repainting or changing their pixels.
''')
(ART/'SPRITE-LOCATIONS.md').write_text('''# Current sprite locations

The organized sample copy is **Dungeon Master Sample/Sprites/**. Its README and manifest identify every asset and working source.

Working race/variant sheets: hybrids/packed/ (male) and female-animations/assets/ (female). Human corrections are published to those locations. Hybrid movement sources remain in hybrid-animations/assets/. Existing actions are in held-equipment-demo/combat/; universal clips and previews in universal-animation/. Equipment is in armory/. Limb/injury work stays in limbs/ and is managed separately. Armor and gear design sources retain their existing folders.

Use the current sheets and sample exports, not numbered human-hand-corrections or human-remake experiments. Those retain source artwork and history.
''')
print(json.dumps(summary))
if missing:raise SystemExit('Some source files are missing; inspect manifest.json')
