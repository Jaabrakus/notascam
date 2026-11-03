#!/usr/bin/env python3
"""Original Human/Orc backend mining filter, delivery, roles and persistence checks.

Copies source/compiler/runtime privately; never modifies the game or normal saves.
Uses actual original movement and item methods, with headless order/role ticks.
No natural mining RNG or native input is claimed by this focused backend suite.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import tempfile
import check_combat as c

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate',type=Path,default=Path('/tmp/remastered-mining-filter-candidate/game'))
    parser.add_argument('--baseline',action='store_true')
    parser.add_argument('--label',default='mining-filter')
    parser.add_argument('--port',type=int,default=12230)
    args=parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_-]+',args.label) or not 1024<=args.port<=52035:parser.error('invalid label or port')
    root=c.ROOT;game=root/'game';out=root/'tests'
    if any((out/f'{args.label}-{s}').exists() for s in ('checks.json','compile.log','server.log','world.log')):parser.error('Choose a fresh label to preserve evidence')
    fixture_source=out/'mining_filter_test.dm'
    candidate_files=('Code/Remastered/Delivery.dm','Code/Remastered/Settlement.dm','Code/Remastered/HUD.dm','Interface/remastered.html')
    sources={str(p.relative_to(game)):sha(p) for p in game.rglob('*') if p.is_file() and p.suffix.lower() in ('.dm','.dme','.dmf','.html')}
    runtime=c.RUNTIME
    result=dict(scope=__doc__,started_utc=datetime.now(timezone.utc).isoformat(),baseline=args.baseline,canonical_source_sha256=sources,fixture_sha256=sha(fixture_source),harness_sha256=sha(Path(__file__)))
    with tempfile.TemporaryDirectory(prefix='dm-mining-filter-') as work:
        base=Path(work);arena=base/'world';private_runtime=base/'runtime'
        shutil.copytree(game,arena,ignore=shutil.ignore_patterns('Cave Crawlers.json','*.dmm','*.sav','ErrorLog.txt','units','saves'))
        if not args.baseline:
            result['candidate_source_sha256']={name:sha(args.candidate/name) for name in candidate_files}
            for name in candidate_files:shutil.copy2(args.candidate/name,arena/name)
        result['tested_source_sha256']={name:sha(arena/name) for name in sources}
        shutil.copytree(runtime/'compiler',private_runtime/'compiler')
        shutil.copytree(runtime/'server',private_runtime/'server',ignore=shutil.ignore_patterns('Content.Client.zip'))
        (private_runtime/'dotnet').symlink_to(runtime/'dotnet',target_is_directory=True)
        paths=dict(runtime=private_runtime/'server/Resources/Assemblies/OpenDreamRuntime.dll',shared=private_runtime/'server/Resources/Assemblies/OpenDreamShared.dll',compiler=private_runtime/'compiler/DMCompiler.dll',standard=private_runtime/'compiler/DMStandard/_Standard.dm')
        result['private_hashes_before']={key:sha(p) for key,p in paths.items()}
        startup=arena/'Code/World.dm';text=startup.read_text(encoding='latin-1');start=text.index('\tNew()');end=text.index('\nvar/Season',start)
        startup.write_text(text[:start]+'\tNew()\n\t\tlog = file("ErrorLog.txt")\n\t\tspawn(0) MiningFilterRun()\n'+text[end:],encoding='latin-1')
        dme=re.sub(r'^#include .*\.dmm"\s*$', '',(arena/'Cave Crawlers.dme').read_text(encoding='latin-1'),flags=re.M)
        shutil.copy2(fixture_source,arena/'mining_filter_test.dm')
        fixture=arena/'mining_filter.dme';fixture.write_text(dme+'\n#include "mining_filter_test.dm"\n',encoding='latin-1')
        c.RUNTIME=private_runtime
        try:
            passed=c.run_world(arena,fixture,args.label,150,prefix='MINING_FILTER',port=args.port)
            observed=json.loads((out/f'{args.label}-checks.json').read_text())
            result.update(observed)
            result['checks']={line.split('|')[2]:line.split('|')[1]=='PASS' for line in observed['observations'] if '|PASS|' in line or '|FAIL|' in line}
            result['compiled_sha256']=sha(fixture.with_suffix('.json'))
        except Exception as error:
            passed=False;result['error']=repr(error)
        finally:c.RUNTIME=runtime
        if (arena/'mining-filter-test.sav').exists():
            save=out/f'{args.label}-settings.sav';shutil.copy2(arena/'mining-filter-test.sav',save);result['save_sha256']=sha(save)
        result['private_hashes_after']={key:sha(p) for key,p in paths.items()}
        result['private_runtime_stable']=result['private_hashes_before']==result['private_hashes_after']
        result['private_game_changes_during_run']=[name for name,digest in result['tested_source_sha256'].items() if name!='Code/World.dm' and sha(arena/name)!=digest]
    result['source_changes_during_run']=[name for name,digest in sources.items() if sha(game/name)!=digest]
    result['fixture_stable']=sha(fixture_source)==result['fixture_sha256']
    result['harness_stable']=sha(Path(__file__))==result['harness_sha256']
    result['passed']=passed and result['private_runtime_stable'] and not result['private_game_changes_during_run'] and result['fixture_stable'] and result['harness_stable']
    result['finished_utc']=datetime.now(timezone.utc).isoformat()
    (out/f'{args.label}-checks.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(report=str(out/f'{args.label}-checks.json'),passed=result['passed'],checks=len(result.get('checks',{})),failed=[k for k,v in result.get('checks',{}).items() if not v],error=result.get('error')),indent=2))
    return 0 if result['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
