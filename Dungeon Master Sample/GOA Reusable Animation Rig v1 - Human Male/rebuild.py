"""Rebuild this package: python3 rebuild.py [profiles/your-character.json]."""
import base64, json, shutil, sys
from pathlib import Path
root=Path(__file__).resolve().parent
profile=Path(sys.argv[1]) if len(sys.argv)>1 else root/'profiles/human-male.json'
if not profile.is_absolute(): profile=root/profile
p=json.loads(profile.read_text())
data=json.loads((root/'source/library-base.json').read_text())
assert len(p['views'])==4 and len(p['grips'])==4, 'Need S/N/E/W views and grips'
data.update(views=p['views'],grips=p['grips'])
data['character']=p['name']
for key in ['actions','calibration']:
    if key in p: data[key]=p[key]   # character action targets read by source/engine.js
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
html=html.replace('Elf animation library',p['name']+' animation library').replace('Four-direction Elf adaptations','Four-direction '+p['name']+' adaptations')
html=html.replace('<a id="baked" href="exports/slash.png">Baked sheet</a>','<a id="baked" href="../review/keyframes.png">Review sheets</a>')
html=html.replace('<a href="README.md">Source and fitting notes</a>','<a href="../README.md">Source and fitting notes</a> <a href="../README-REVIEW.md">Creator review</a>')
(root/'preview/index.html').write_text(html)
print('Built',p['name'],'— open preview/index.html or serve this folder.')
