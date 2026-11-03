#!/usr/bin/env python3
"""Run the original-unit finite dispatch boundary fixture in an isolated copied world."""
import argparse, hashlib, json, re, shutil, tempfile
from pathlib import Path
import check_combat as runner

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def source_hashes(root):
    return {str(p.relative_to(root)):sha(p) for p in root.rglob('*') if p.is_file() and p.suffix in ('.dm','.dme','.html','.dmf')}
def main():
    root=Path(__file__).resolve().parents[1]
    runtime=root/"runtime" if (root/"runtime/server").exists() else root.parent/"replica/runtime/macos-x64"
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--game',type=Path,default=root/'game')
    ap.add_argument('--runtime',type=Path,default=runtime)
    ap.add_argument('--fixture',type=Path,default=root/'tests/order_eligibility.dm')
    ap.add_argument('--report-dir',type=Path,default=root/'tests')
    ap.add_argument('--label',required=True)
    ap.add_argument('--port',type=int,default=12255)
    a=ap.parse_args()
    if not re.fullmatch('[a-z0-9-]+',a.label): ap.error('label must use lowercase letters, numbers and hyphens')
    if not 1024<=a.port<=52035: ap.error('invalid port')
    if not (a.game/'Cave Crawlers.dme').is_file() or not a.fixture.is_file(): ap.error('missing source or fixture')
    a.report_dir.mkdir(parents=True,exist_ok=True)
    destination=a.report_dir/(a.label+'-checks.json')
    if destination.exists(): ap.error('use a fresh label to preserve evidence')
    before=source_hashes(a.game);fixture_hash=sha(a.fixture)
    artifacts={p:sha(a.runtime/p) for p in ['compiler/DMCompiler.dll','compiler/DMStandard/_Standard.dm','server/Resources/Assemblies/OpenDreamRuntime.dll','server/Resources/Assemblies/OpenDreamShared.dll']}
    with tempfile.TemporaryDirectory(prefix='dm-order-lifetime-') as temp:
        base=Path(temp);world=base/'world';(base/'tests').mkdir()
        shutil.copytree(a.game,world,ignore=shutil.ignore_patterns('Cave Crawlers.json','*.dmm','*.sav','units','saves','ErrorLog.txt'))
        f=world/'Code/World.dm';s=f.read_text(encoding='latin1');start,end=s.index('\tNew()'),s.index('\nvar/Season')
        f.write_text(s[:start]+'\tNew()\n\t\tspawn(0) EligibilityRun()\n'+s[end:],encoding='latin1')
        dme=re.sub(r'^#include .*\.dmm"\s*$','',(world/'Cave Crawlers.dme').read_text(encoding='latin1'),flags=re.M)
        fixture=world/'order_eligibility.dme';fixture.write_text(dme+'\n#include "order_eligibility.dm"\n',encoding='latin1');shutil.copy2(a.fixture,world/'order_eligibility.dm')
        runner.ROOT=base;runner.RUNTIME=a.runtime
        passed=runner.run_world(world,fixture,a.label,45,prefix='ELIGIBILITY',port=a.port)
        r=json.loads((base/'tests'/destination.name).read_text())
        r.update(source_sha256=before,fixture_sha256=fixture_hash,artifacts=artifacts,
                 source_stable=before==source_hashes(a.game),fixture_stable=fixture_hash==sha(a.fixture),
                 artifacts_stable=artifacts=={p:sha(a.runtime/p) for p in artifacts},
                 scope='Original Human/Orc pairs; controlled actor lifetime/availability state after actual HUD normalization and before finite dispatch. No native/physical input or normal saves.')
        r['passed']=passed and r['source_stable'] and r['fixture_stable'] and r['artifacts_stable']
        for p in (base/'tests').iterdir(): shutil.copy2(p,a.report_dir/p.name)
        shutil.copy2(a.fixture,a.report_dir/(a.label+'-fixture.dm'))
        destination.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({'passed':r['passed'],'assertions':sum('|PASS|' in x or '|FAIL|' in x for x in r['observations']),'failed':sum('|FAIL|' in x for x in r['observations']),'report':str(destination)},indent=2))
    return 0 if r['passed'] else 1
if __name__=='__main__': raise SystemExit(main())
