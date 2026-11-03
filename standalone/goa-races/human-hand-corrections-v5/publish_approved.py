"""Publish only the four Human sheets explicitly approved after the v5 review."""
from pathlib import Path
from PIL import Image
import json,hashlib,zipfile
HERE=Path(__file__).resolve().parent;ART=HERE.parent;ROOT=ART.parents[1];SAMPLE=ROOT/'Dungeon Master Sample';OUT=SAMPLE/'Approved Sprites';OUT.mkdir(exist_ok=True)
entries=json.loads((HERE/'manifest.json').read_text());records=[]
for e in entries:
 source=ART/'hybrids/packed'/e['race']/e['appearance'];target=OUT/'Male'/e['race']/e['appearance'];target.mkdir(parents=True,exist_ok=True)
 assert Image.open(source/'sprites.png').convert('RGBA').tobytes()==Image.open(ART/'human-sheet-rebuild-v6'/e['race']/e['appearance']/'sprites.png').convert('RGBA').tobytes()
 for name in ['sprites.png','movement.dmi','atlas.json']:
  data=(source/name).read_bytes();(target/name).write_bytes(data)
  records.append(dict(race=e['race'],sex='male',appearance=e['appearance'],path=str((target/name).relative_to(OUT)),source=str((source/name).relative_to(ROOT)),sha256=hashlib.sha256(data).hexdigest()))
manifest=dict(approval='User approved the rounded-profile and corrected idle-arm Human revision, then requested final approved sheets in Dungeon Master Sample.',revision='v6-full-redrawn-frames',sheets=4,bodyFrameSize=[64,64],directions=['South','North','East','West'],poseRows=['idle','walk A','walk B'],movementLoop=[0,1,0,2],frameDurationMs=200,files=records)
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2))
(OUT/'README.md').write_text('''# Approved sprites

These are the four male Human sheets approved after the rounded-nose and idle-arm review:

- Male/Human/base
- Male/Human/Possessed1
- Male/HumanBlack/base
- Male/HumanBlack/Possessed1

Each folder contains sprites.png (256x192; 64x64 cells), movement.dmi and atlas.json. Columns are South, North, East, West. Rows are idle, walk A, walk B; replay 0,1,0,2 at 200ms. The DMI contains that four-phase movement loop. These files match the corrected working sheets exactly; manifest.json records the source paths and hashes.

The other current race sheets, equipment and animation work remain in ../Sprites/. That broader collection includes drafts. Earlier rejected Human redraws are not included here. Live game integration is a separate step.
''')
with zipfile.ZipFile(SAMPLE/'Approved Human Sprites.zip','w',zipfile.ZIP_DEFLATED) as z:
 for p in OUT.rglob('*'):
  if p.is_file():z.write(p,p.relative_to(OUT))
print('Published 4 approved Human sheets, 12 sprite/metadata files, and Approved Human Sprites.zip.')
