from pathlib import Path
import argparse,hashlib,json,re,shutil,tempfile
import check_combat as runner
B=Path(__file__).resolve().parents[1];runner.ROOT=B;runner.RUNTIME=B/'runtime' if (B/'runtime/server').exists() else B.parent/'replica/runtime/macos-x64'
p=argparse.ArgumentParser();p.add_argument('--label',required=True);p.add_argument('--candidate',action='store_true');p.add_argument('--port',type=int,default=12208);a=p.parse_args();source=B/'game';fixture_source=B/'tests/work_selection.dm';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
with tempfile.TemporaryDirectory(prefix='dm-work-selection-')as temp:
 world=Path(temp)/'world';shutil.copytree(source,world);s=(world/'Code/World.dm').read_text(encoding='latin-1');start,end=s.index('\tNew()'),s.index('\nvar/Season');(world/'Code/World.dm').write_text(s[:start]+'\tNew()\n\t\tspawn(0) AuditRun()\n'+s[end:],encoding='latin-1');dme=re.sub(r'^#include .*\.dmm"\s*$','',(world/'Cave Crawlers.dme').read_text(encoding='latin-1'),flags=re.M);fixture=world/'work_selection.dme';fixture.write_text(dme+'\n#include "work_selection.dm"\n',encoding='latin-1');shutil.copy2(fixture_source,world/'work_selection.dm')
 runner.run_world(world,fixture,a.label,45,prefix='WORKINTENT',port=a.port)
 for f in world.glob('work-*-model.json'):shutil.copy2(f,B/'tests'/f.name)
 report=B/'tests'/(a.label+'-checks.json');r=json.loads(report.read_text());r['fixture_sha256']=sha(fixture_source);r['source_sha256']={str(f.relative_to(source)):sha(f)for f in source.rglob('*')if f.is_file()};r['scope']='Private real Human/Orc direct Work receipt audit. Receipt predicate gates unchanged original handlers exactly as production Topic. Native receipt separately required. No normal save/input.';report.write_text(json.dumps(r,indent=2)+'\n')

raise SystemExit(0 if r['passed'] else 1)
