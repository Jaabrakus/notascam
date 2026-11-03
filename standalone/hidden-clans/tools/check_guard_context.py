#!/usr/bin/env python3
"""Exercise original Guard effects across real modal yield-time changes."""
import argparse, hashlib, json, re, shutil, tempfile
from pathlib import Path
from check_combat import ROOT,RUNTIME,run_world

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--game-dir',type=Path,default=ROOT/'game');p.add_argument('--label',default='guard-context-before');p.add_argument('--port',type=int,default=12195);p.add_argument('--owners-only',action='store_true');a=p.parse_args()
    if not re.fullmatch(r'[a-z0-9-]+',a.label):p.error('Use a simple label')
    game=a.game_dir.resolve();names=['Cave Crawlers.dme','Code/Creatures/Monster AI.dm','Code/Remastered/SelectedActions.dm','Code/Remastered/Actions.dm','Code/Remastered/Orders.dm','Code/Remastered/Delivery.dm','Code/Remastered/Settlement.dm','Code/Remastered/Defense.dm','Code/Remastered/ControlGroups.dm','Code/Remastered/QoL.dm','Code/Ownership.dm'];paths={n:game/n for n in names};paths['fixture']=ROOT/'tests/guard_context_audit.dm';paths['runtime']=RUNTIME/'server/Resources/Assemblies/OpenDreamRuntime.dll'
    before={k:sha(v)for k,v in paths.items()}
    with tempfile.TemporaryDirectory(prefix='dm-guard-audit-')as temp:
        arena=Path(temp)/'world';shutil.copytree(game,arena,ignore=shutil.ignore_patterns('Cave Crawlers.json','*.dmm','*.sav','units','saves','ErrorLog.txt'))
        source=arena/'Code/Creatures/Monster AI.dm';s=source.read_text(encoding='latin-1')
        original='input("Set a Owner to friendly for selected units, input including parentheses if adding a NPC Owner.","Add Friendly","{NPC Alliance}") as text|null'
        if original in s:s=s.replace(original,'GuardAuditFriendly()',1);source.write_text(s,encoding='latin-1')
        dme=re.sub(r'^#include .*\.dmm"\s*$','',(arena/'Cave Crawlers.dme').read_text(encoding='latin-1'),flags=re.M)
        w=arena/'Code/World.dm';s=w.read_text(encoding='latin-1');start,end=s.index('\tNew()'),s.index('\nvar/Season');w.write_text(s[:start]+'\tNew()\n\t\tspawn(0) '+('GuardAuditOwnersOnly' if a.owners_only else 'GuardAuditRun')+'()\n'+s[end:],encoding='latin-1')
        shutil.copy2(paths['fixture'],arena/'guard_context_audit.dm');fixture=arena/'guard.dme';fixture.write_text(dme+'\n#include "guard_context_audit.dm"\n',encoding='latin-1')
        passed=run_world(arena,fixture,a.label,90,prefix='GUARD_AUDIT',port=a.port)
        report_path=ROOT/'tests'/(a.label+'-checks.json');report=json.loads(report_path.read_text());report['hashes_before']=before;report['hashes_after']={k:sha(v)for k,v in paths.items()};report['source_runtime_fixture_stable']=report['hashes_before']==report['hashes_after'];report['scope']=__doc__+' Real Human/Orc constructors and original Guard body; only modal delivery is scripted in a private copy. No app/input/save.';report['passed']=passed and report['source_runtime_fixture_stable'];report_path.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(passed=report['passed'],stable=report['source_runtime_fixture_stable'],report=str(report_path)),indent=2))
    return 0 if report['passed']else 1
if __name__=='__main__':raise SystemExit(main())
