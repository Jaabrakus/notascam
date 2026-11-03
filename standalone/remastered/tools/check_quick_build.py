#!/usr/bin/env python3
"""Original-unit quick build retains interrupted work and production-only continuation."""
import argparse,contextlib,hashlib,io,json,re,shutil,tempfile
from pathlib import Path
import check_combat as harness
BASE=Path(__file__).resolve().parents[1]
harness.ROOT=BASE
if (BASE/'runtime/server').exists():harness.RUNTIME=BASE/'runtime'
p=argparse.ArgumentParser();p.add_argument('--label',required=True);p.add_argument('--port',type=int,default=12211);a=p.parse_args()
with tempfile.TemporaryDirectory(prefix='dm-quick-build-') as temp:
    world=Path(temp)/'world';shutil.copytree(BASE/'game',world)
    dme=re.sub(r'^#include .*\.dmm"\s*$','',(world/'Cave Crawlers.dme').read_text(encoding='latin-1'),flags=re.M)
    f=world/'Code/World.dm';s=f.read_text(encoding='latin-1');start=s.index('\tNew()');end=s.index('\nvar/Season',start)
    f.write_text(s[:start]+'\tNew()\n\t\tspawn(0) QuickBuildRun()\n'+s[end:],encoding='latin-1')
    shutil.copy2(BASE/'tests/quick_build_test.dm',world/'quick_build_test.dm')
    fixture=world/'quick_build.dme';fixture.write_text(dme+'\n#include "quick_build_test.dm"\n',encoding='latin-1')
    with contextlib.redirect_stdout(io.StringIO()):ok=harness.run_world(world,fixture,a.label,120,prefix='QUICKBUILD',port=a.port)
    models=BASE/'tests'/f'{a.label}-models';models.mkdir(exist_ok=True)
    for model in world.glob('quickbuild-model-*.json'):shutil.copy2(model,models/model.name)
    report=BASE/'tests'/f'{a.label}-checks.json';r=json.loads(report.read_text())
    r['sources']={str(f.relative_to(BASE)):hashlib.sha256(f.read_bytes()).hexdigest() for f in [BASE/'game/Code/Remastered/HUD.dm',BASE/'game/Code/Remastered/Settlement.dm',BASE/'tests/quick_build_test.dm']}
    r['scope']='Original Human/Orc constructors, original wood pickup, CreateCarpentry/Fire construction and production effects. Fixture provides wood, owned task/role configuration and explicit invalid HP/GoingToDie/stale-roster states; no skill/capacity/RNG changes. Private grass arena, no connected native client.'
    report.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps(dict(passed=ok,checks=sum('|PASS|' in x or '|FAIL|' in x for x in r['observations']),failures=[x for x in r['observations'] if '|FAIL|' in x],errors=r['errors'],report=str(report)),indent=2))
    raise SystemExit(0 if ok else 1)
