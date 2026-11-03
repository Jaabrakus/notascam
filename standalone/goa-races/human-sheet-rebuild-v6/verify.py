from pathlib import Path
from PIL import Image
import json,hashlib,zipfile
import numpy as np
ART=Path(__file__).resolve().parents[1];ROOT=ART.parents[1];S=ROOT/'Dungeon Master Sample';B=ART/'human-sheet-rebuild-v6';report=json.loads((B/'verification.json').read_text());registry=json.loads((ART/'armory/bodies.json').read_text());bindings={b['id']:b for b in registry['bodies']};checked=0;full=0;archive_checks=0
for r in report['records']:
 race,kind=r['race'],r['appearance'];source=ROOT/r['source'];raw=source.read_bytes();im=Image.open(source).convert('RGBA');assert im.size==(256,192)
 for f in r['sources']:
  expected=Image.open(ROOT/f['packedFrame']).convert('RGBA');actual=im.crop((f['view']*64,f['row']*64,(f['view']+1)*64,(f['row']+1)*64));assert actual.tobytes()==expected.tobytes(),(race,kind,f['row'],f['view']);full+=1
 for dest in [S/'Sprites/Male'/race/kind/'sprites.png',S/'Human Sprites'/f'{race}-Male-{kind}-64.png']:
  assert dest.read_bytes()==raw,str(dest)
 if kind in ['base','Possessed1']:
  assert (S/'Approved Sprites/Male'/race/kind/'sprites.png').read_bytes()==raw
  old=Image.open(ART/'human-hand-corrections-v5'/race/kind/'candidate.png').convert('RGBA');edits=next(e for e in json.loads((ART/'human-hand-corrections-v5/staged-verification.json').read_text()) if e['id']==race+'/'+kind)['edits'];mask=np.zeros((192,256),dtype=bool)
  for e in edits:
   x0,y0,x1,y1=e['box'];mask[e['row']*64+y0:e['row']*64+y1,e['view']*64+x0:e['view']*64+x1]=True
  assert np.any(np.any(np.array(old)!=np.array(im),axis=2)&~mask),(race,kind,'still patch-only')
 movement=Image.open(source.parent/'movement.dmi').convert('RGBA')
 for row,pose in enumerate([0,1,0,2]):assert movement.crop((0,row*64,256,(row+1)*64)).tobytes()==im.crop((0,pose*64,256,(pose+1)*64)).tobytes()
 packs=[('GOA Male Human Sprites.zip',f'{race}/{kind}/sprites.png'),('GOA Updated Races and Hybrids.zip',f'{race}/{kind}/sprites.png'),('GOA Human Combat Samples.zip',f'Human Sprites/{race}/{kind}/sprites.png'),('All Sprites.zip',f'Male/{race}/{kind}/sprites.png')]
 if kind in ['base','Possessed1']:packs.append(('Approved Human Sprites.zip',f'Male/{race}/{kind}/sprites.png'))
 if kind!='base':
  anim=ART/'hybrid-animations/assets'/race/kind;assert (anim/'sprites.png').read_bytes()==raw
  packs.append(('GOA Hybrid Walk Animations.zip',f'{race}/{kind}/{race}-{kind}-walk-64.png'))
 else:assert (ART/'hybrids/walks'/(race+'.png')).read_bytes()==raw
 for archive,name in packs:
  with zipfile.ZipFile(S/archive) as z:assert z.read(name)==raw,(archive,name);archive_checks+=1
 id=('human' if race=='Human' else 'human-dark')+('' if kind=='base' else '-'+kind.lower());b=bindings[id];assert Path(b['source'])==source and b['sourceSha256']==hashlib.sha256(raw).hexdigest()
 equipped=ART/'armory/equipped-samples'/id/'body64.png';assert (S/'Sprites/Equipped'/id/'body64.png').read_bytes()==equipped.read_bytes()
 checked+=1
result=dict(sheets=checked,fullFramesMatched=full,archivesMatched=archive_checks,patchOnlyAssemblyRejected=True,flatSampleCopiesMatch=True,dmiLoopsMatch=True,armoryBindingsMatch=True)
(B/'publish-verification.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
