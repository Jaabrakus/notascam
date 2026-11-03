#!/usr/bin/env python3
import argparse,hashlib,json,shutil,sys,re,tempfile,contextlib,io
from pathlib import Path
BASE=Path(__file__).resolve().parents[1]
import check_combat as harness
harness.ROOT=BASE
if (BASE/'runtime/server').exists():harness.RUNTIME=BASE/'runtime'
p=argparse.ArgumentParser();p.add_argument('--label',required=True);p.add_argument('--port',type=int,default=12204);a=p.parse_args()
with tempfile.TemporaryDirectory(prefix='dm-idle-audit-')as temp:
 world=Path(temp)/'world';shutil.copytree(BASE/'game',world)
 dme=re.sub(r'^#include .*\.dmm"\s*$','',(world/'Cave Crawlers.dme').read_text(encoding='latin-1'),flags=re.M)
 f=world/'Code/World.dm';s=f.read_text(encoding='latin-1');start=s.index('\tNew()');end=s.index('\nvar/Season',start);f.write_text(s[:start]+'\tNew()\n\t\tspawn(0) SelectRejectRun()\n'+s[end:],encoding='latin-1')
 shutil.copy2(BASE/'tests/selection_rejection_probe.dm',world/'selection_rejection_probe.dm');fixture=world/'selection_rejection_probe.dme';fixture.write_text(dme+'\n#include "selection_rejection_probe.dm"\n',encoding='latin-1')
 with contextlib.redirect_stdout(io.StringIO()):ok=harness.run_world(world,fixture,a.label,180,prefix='SELECT_REJECT',port=a.port)
 for model in world.glob('idle-model-*.json'):shutil.copy2(model,BASE/'tests'/model.name)
 rpath=BASE/'tests'/f'{a.label}-checks.json';r=json.loads(rpath.read_text());r['sources']={str(f.relative_to(BASE)):hashlib.sha256(f.read_bytes()).hexdigest()for f in [BASE/'game/Code/Remastered/QoL.dm',BASE/'tests/selection_rejection_probe.dm']};rpath.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(passed=ok,checks=sum('|PASS|'in x or '|FAIL|'in x for x in r['observations']),failures=[x for x in r['observations']if'|FAIL|'in x],errors=r['errors'],report=str(rpath)),indent=2));raise SystemExit(0 if ok else 1)
