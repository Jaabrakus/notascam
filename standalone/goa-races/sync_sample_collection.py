from pathlib import Path,PurePosixPath
import json,hashlib,zipfile,collections,html
root=Path(__file__).resolve().parents[2];sample=root/'Dungeon Master Sample';out=sample/'Sprites'
m=json.loads((out/'manifest.json').read_text());records={r['path']:r for r in m['files']}
def add(data,dest,source,group):
 p=out/dest;p.parent.mkdir(parents=True,exist_ok=True)
 if not p.exists() or p.read_bytes()!=data:p.write_bytes(data)
 records[str(dest)]=dict(group=group,path=str(dest),source=source,bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
for source in (sample/'Worn Armor and Idle Poses').rglob('*'):
 if source.is_file():add(source.read_bytes(),Path('Armor/Worn')/source.relative_to(sample/'Worn Armor and Idle Poses'),str(source.relative_to(root)),'Armor')
for archive,groupdir in [('Generated Matching Gear.zip','Matching Gear'),('Deepguard Armor Pieces.zip','Armor/Deepguard Components'),('Deepguard Pixel Armor Pieces.zip','Armor/Deepguard Pixel Components')]:
 with zipfile.ZipFile(sample/archive) as z:
  for info in z.infolist():
   path=PurePosixPath(info.filename)
   if info.is_dir():continue
   if path.is_absolute() or '..' in path.parts or '__MACOSX' in path.parts or info.filename.endswith('.DS_Store'):continue
   add(z.read(info),Path(groupdir)/Path(*path.parts),str((sample/archive).relative_to(root))+'::'+info.filename,groupdir.split('/')[0])
for name in ['all-wearables.png','inventory.json']:
 source=root/'standalone/goa-races/wardrobe'/name
 add(source.read_bytes(),Path('Equipment/Inventory')/name,str(source.relative_to(root)),'Equipment')
for source in sample.glob('*.png'):
 if any(word in source.name.lower() for word in ['armor','gear']):add(source.read_bytes(),Path('Armor/Reference Sheets')/source.name,str(source.relative_to(root)),'Armor')
allfiles=sorted(records.values(),key=lambda r:r['path']);counts=dict(collections.Counter(r['group'] for r in allfiles));m['files']=allfiles;m['summary']=dict(files=len(allfiles),counts=counts,bytes=sum(r['bytes'] for r in allfiles),missingSources=[],existingAnimationPixelsChanged=False)
(out/'manifest.json').write_text(json.dumps(m,indent=2))
readme=(out/'README.md').read_text();readme+='\n## Complete sample collection\n\nArmor/ now includes the published worn armor and component sets. Matching Gear/ contains the published matching-gear pack with its original folder structure. Equipment/Inventory includes the wearable item sheet and index. Open ../All Sprites.html to search every file, or download ../All Sprites.zip.\n'
(out/'README.md').write_text(readme)
rows=''.join('<tr data-search="'+html.escape((r['group']+' '+r['path']).lower(),quote=True)+'"><td>'+html.escape(r['group'])+'</td><td><a href="Sprites/'+html.escape(r['path'],quote=True)+'">'+html.escape(r['path'])+'</a></td></tr>' for r in allfiles)
page='''<!doctype html><html lang="en"><meta charset="utf-8"><title>All Dungeon Master sample sprites</title><style>body{background:#14232a;color:#eaf1f3;font:15px system-ui;margin:24px}main{max-width:1200px;margin:auto}h1{font-size:26px}p{color:#bdd0d6;line-height:1.5}a{color:#8de1d0}input{padding:12px;width:100%;box-sizing:border-box;background:#20343b;color:white;border:1px solid #54737d;border-radius:6px;margin:16px 0}table{width:100%;border-collapse:collapse}td,th{padding:8px;text-align:left;border-bottom:1px solid #29414a}td:first-child{width:120px}tr[hidden]{display:none}</style><main><h1>All sample sprites</h1><p>Male and female races, combat, animations, limbs, equipment, worn armor and matching gear. The current sprite files are together in the <strong>Sprites</strong> folder. Some animation and limb sets retain their draft status; see their metadata.</p><p><a href="All Sprites.zip">Download the complete sprite collection</a> · <a href="Sprites/README.md">Folder guide</a> · <a href="Sprites/manifest.json">Asset manifest</a></p><input id="filter" type="search" placeholder="Find a race, weapon, animation or filename" aria-label="Search sprites"><p id="count">'''+str(len(allfiles))+''' files</p><table><thead><tr><th>Set</th><th>File</th></tr></thead><tbody>'''+rows+'''</tbody></table></main><script>const rows=[...document.querySelectorAll('tbody tr')];document.getElementById('filter').addEventListener('input',e=>{const q=e.target.value.toLowerCase().trim();let n=0;for(const r of rows){r.hidden=!r.dataset.search.includes(q);if(!r.hidden)n++;}document.getElementById('count').textContent=n+' files';});</script></html>'''
(sample/'All Sprites.html').write_text(page)
# Include the complete physical Sprites folder; no dependencies on the working directories.
with zipfile.ZipFile(sample/'All Sprites.zip','w',zipfile.ZIP_DEFLATED) as z:
 for p in out.rglob('*'):
  if p.is_file():z.write(p,p.relative_to(out))
# Verify copied data and the ZIP contents against the manifest.
with zipfile.ZipFile(sample/'All Sprites.zip') as z:
 for r in allfiles:
  assert hashlib.sha256((out/r['path']).read_bytes()).hexdigest()==r['sha256'],r['path']
  assert hashlib.sha256(z.read(r['path'])).hexdigest()==r['sha256'],r['path']
print(json.dumps(m['summary']))
