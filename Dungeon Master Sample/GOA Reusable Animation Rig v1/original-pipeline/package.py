"""Bundle the verified rig with a portable, dependency-free rebuild tool."""
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
LIB = ROOT / 'Dungeon Master Sample/GOA Sword and Shield Rig/library'
OUT = ROOT / 'Dungeon Master Sample/GOA Reusable Animation Rig v1'
report = json.loads((LIB / 'verification.json').read_text())
data = json.loads((LIB / 'library.json').read_text())
assert report['status'] == 'passed' and report['revision'] == data['revision']
assert report['clips'] == len(data['clips'])
OUT.mkdir(exist_ok=True)
shutil.copytree(LIB, OUT / 'preview', dirs_exist_ok=True)
(OUT / 'source').mkdir(exist_ok=True)
for name in ['engine.js', 'app.js', 'viewer.html', 'AI-HANDOFF.md']:
    shutil.copyfile(HERE / name, OUT / 'source' / name)
(OUT / 'original-pipeline').mkdir(exist_ok=True)
for name in ['extract.js', 'build.py', 'runtime-source.json', 'verify_export.py', 'check_ranged.js', 'check_polish.js', 'package.py']:
    shutil.copyfile(HERE / name, OUT / 'original-pipeline' / name)
(OUT / 'profiles').mkdir(exist_ok=True)
(OUT / 'profiles/elf-male.json').write_text(json.dumps({
    'name': 'Approved GOA Elf male', 'views': data['views'], 'grips': data['grips']
}, indent=2))
shutil.copyfile(LIB / 'library.json', OUT / 'source/library-base.json')
(OUT / 'rebuild.py').write_text('''"""Rebuild this package: python3 rebuild.py [profiles/your-character.json]."""
import base64, json, shutil, sys
from pathlib import Path
root=Path(__file__).resolve().parent
profile=Path(sys.argv[1]) if len(sys.argv)>1 else root/'profiles/elf-male.json'
if not profile.is_absolute(): profile=root/profile
p=json.loads(profile.read_text())
data=json.loads((root/'source/library-base.json').read_text())
assert len(p['views'])==4 and len(p['grips'])==4, 'Need S/N/E/W views and grips'
data.update(views=p['views'],grips=p['grips'])
data['character']=p['name']
images={}
for f in (root/'preview/assets').rglob('*.png'):
    images[f.relative_to(root/'preview/assets').as_posix()]='data:image/png;base64,'+base64.b64encode(f.read_bytes()).decode()
refs=[]
for v in data['views']:
    refs.extend(v['parts'].values())
    for row in v['walk']: refs.extend(row.values())
for item in data['items'].values(): refs.extend(v['image'] for v in item['views'])
refs.append(data['arrow'])
assert all(r in images for r in refs), 'Missing referenced PNG in preview/assets'
for f in ['engine.js','app.js']: shutil.copyfile(root/'source'/f,root/'preview'/f)
(root/'preview/library.json').write_text(json.dumps(data,indent=2))
data['images']=images
html=(root/'source/viewer.html').read_text().replace('/*DATA*/','const DATA='+json.dumps(data)+';')
html=html.replace('<a href="../?v=body-attack-6">Accepted sword-and-shield preview</a>', '')
html=html.replace('approved GOA Elf',p['name']).replace('Loading Elf parts','Loading character parts')
(root/'preview/index.html').write_text(html)
print('Built',p['name'],'— open preview/index.html or serve this folder.')
''')
(OUT / 'README.md').write_text('''# GOA reusable animation rig — v1

Snapshot: rig-package-16. Start with `preview/index.html`. This folder contains the current Elf rig, 97 animation clips, equipment artwork, baked PNG/JSON sheets, and editable renderer code. North spear has a longer rear shaft and thicker forward section, attached at the same grip.

## Reproduce the current result

Requires Python 3 only for rebuilding; the browser runs the preview.

```
python3 rebuild.py
python3 -m http.server 8880 --bind 127.0.0.1
```

Open http://127.0.0.1:8880/preview/. The default profile reproduces the packaged Elf. `preview/exports` contains all 97 baked sheets and timing/grip metadata. Body artwork uses native 64px coordinates; export cells are 192px with origin [64,64]. Columns are South, North, East, West.

## Adapt another character

1. Duplicate `profiles/elf-male.json` under a new name. Preserve the four-view order and the part names.
2. Add that character's transparent native-scale PNGs to `preview/assets` with unique filenames. Each view needs head, torso, pelvis, upper arms, forearms, hands, thighs, shins and feet. Complete hidden anatomy so moving a limb does not expose holes. Also supply the idle/walk images referenced by each view's `walk` rows.
3. Replace the profile's image references. Calibrate neck, waist, each shoulder/elbow/wrist, hip/knee/ankle, near-leg order, joint colors and both hand grips. Coordinates belong to the same 64px canvas as the PNGs; never measure from an enlarged screenshot.
4. Run `python3 rebuild.py profiles/your-character.json`. This rebuilds the preview, not the pre-baked exports. Existing baked sheets and verification reports still describe the original Elf until regenerated and rechecked.
5. Tune the character's action targets in `source/engine.js`. Bow/throw targets currently contain Elf-specific coordinates and corrections. Sharing the motion timing does not automatically fit every race, female or hybrid body. Calibrate one new character before expanding further.
6. Review every facing at windup, release, follow-through and recovery. Bow release is 0.90s; throw release is 0.38s. Check seams, hand contact, foot contact and layer order at native scale and slow playback. Export reviewed clips with the viewer buttons.

## Current rules worth preserving

- West is the master side bow pose. East mirrors its complete rendered animation.
- Both bow arms straighten toward relaxed rest after the shot; do not return the drawing hand to a raised shield grip.
- Front/back arrows are short end-on tips. North body occlusion is intentional.
- South throwing forearm is upright; North windup uses an outward elbow and upright forearm (reverse L).
- North held spear draws over the body, with the gripping hand on top. Shaft width/length are adjusted around the grip, so the weapon stays attached.
- Spear is vertical for North/South and horizontal for East/West. Axe/dagger use their own rotation.
- Projected limb lengths may be shorter than the physical calibration; tests must not force full side-view lengths onto foreshortened limbs.

## Contents and limits

`source` is the editable portable viewer/renderer. `profiles` supplies calibrated character anatomy. `preview` is runnable and includes assets, exports and reports. `original-pipeline` preserves extraction/build/test scripts for the original Dungeon Master repository; those scripts rely on its source paths and are not standalone commands for this package. `rebuild.py` is the standalone builder.

The archived technical verification covers all 97 clips. It does not mean every clip or deep bend is visually approved. Physics falls and projectile flight remain preview approximations; collision, damage and live game integration are separate. Only the approved Elf male is calibrated here. This package does not modify the live game.

`source/AI-HANDOFF.md` records earlier iterations; the rules above describe this final snapshot and supersede conflicting historical notes. `manifest.json` records packaged file hashes for reproducibility; regenerate it after intentional edits if you need a new snapshot.
''')
shutil.copyfile(OUT / 'README.md', OUT / 'preview/README.md')
subprocess.run([sys.executable, str(OUT / 'rebuild.py')], check=True)
(OUT / 'manifest.json').write_text(json.dumps({
    'revision': data['revision'], 'clips': len(data['clips']),
    'files': {str(p.relative_to(OUT)): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in sorted(OUT.rglob('*')) if p.is_file() and p.name != 'manifest.json'}
}, indent=2))
print(OUT)
