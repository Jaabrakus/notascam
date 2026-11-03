#!/usr/bin/env python3
"""Reproduce Smelter effects and work handoff with real units in a copied world."""
import argparse, hashlib, json, re, shutil, tempfile
from pathlib import Path
import check_combat as core
ROOT=core.ROOT

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--label',default='smelter-before');p.add_argument('--port',type=int,default=12195)
    p.add_argument('--game-overlay',type=Path);a=p.parse_args()
    if not re.fullmatch(r'[a-z0-9-]+',a.label):p.error('simple label required')
    sources=['Code/Items/CraftingStations.dm','Code/Remastered/QoL.dm','Code/Remastered/Orders.dm','Code/Remastered/SelectedActions.dm','Code/Remastered/Defense.dm','Code/Items/Item Procs.dm','Code/Ownership.dm','Cave Crawlers.dme']
    original={n:sha(ROOT/'game'/n) for n in sources}
    with tempfile.TemporaryDirectory(prefix='dm-smelter-') as directory:
        directory=Path(directory);runtime=directory/'runtime';runtime.mkdir()
        installed=core.RUNTIME
        for component in ('server','compiler'):shutil.copytree(installed/component,runtime/component)
        (runtime/'dotnet').symlink_to(installed/'dotnet',target_is_directory=True)
        core.RUNTIME=runtime
        artifacts={n:runtime/n for n in ['server/Resources/Assemblies/OpenDreamRuntime.dll','compiler/DMCompiler.dll','compiler/DMStandard/_Standard.dm']}
        runtime_before={n:sha(v) for n,v in artifacts.items()}
        arena=directory/'game';shutil.copytree(ROOT/'game',arena,ignore=shutil.ignore_patterns('Cave Crawlers.json','*.dmm','*.sav','saves','units','ErrorLog.txt'))
        if a.game_overlay:
            for name in sources:
                if (a.game_overlay/name).is_file():shutil.copy2(a.game_overlay/name,arena/name)
        tested={n:sha(arena/n) for n in sources}
        station=arena/'Code/Items/CraftingStations.dm';source=station.read_text(encoding='latin-1');start=source.index('\n\t\tSmelters\n');end=source.index('\n\t\tCampFires\n',start);section=source[start:end]
        old='input("What Action Will You Choose?", "Choose", null) in menu'
        count=section.count(old)
        if count==1:section=section.replace(old,'usr.RemasterActionChoice("What Action Will You Choose?", "Choose", menu)')
        elif count or section.count('P.RemasterActionChoice(')!=1:raise RuntimeError('Smelter prompt changed')
        station.write_text(source[:start]+section+source[end:],encoding='latin-1')
        qol=(arena/'Code/Remastered/QoL.dm').read_text(encoding='latin-1');start=qol.index('\tif(istype(mob, /Player) && !mob.Function && istype(m, /mob/WorkShops))');end=qol.index('\n\tif(',start+1);branch=qol[start:end]
        eager='RemasterLegacyHandoff()' in branch and '!istype(m, /mob/WorkShops/Smelters)' not in branch
        (arena/'smelter_config.dm').write_text(f'var/smelt_eager_handoff={int(eager)}\n')
        world=arena/'Code/World.dm';s=world.read_text(encoding='latin-1');start=s.index('\tNew()');end=s.index('\nvar/Season',start);world.write_text(s[:start]+'\tNew()\n\t\tspawn(0) SmeltRun()\n'+s[end:],encoding='latin-1')
        fixture_source=ROOT/'tests/smelter_handoff_test.dm';fixture_hash=sha(fixture_source);shutil.copy2(fixture_source,arena/'smelter_handoff_test.dm')
        dme=re.sub(r'^#include .*\.dmm"\s*$','',(arena/'Cave Crawlers.dme').read_text(encoding='latin-1'),flags=re.M)
        fixture=arena/'smelter.dme';fixture.write_text(dme+'\n#include "smelter_config.dm"\n#include "smelter_handoff_test.dm"\n',encoding='latin-1')
        passed=core.run_world(arena,fixture,a.label,90,prefix='SMELT',port=a.port)
        path=ROOT/'tests'/(a.label+'-checks.json');report=json.loads(path.read_text());report.update(original_source_sha256=original,tested_source_sha256=tested,private_runtime_sha256=runtime_before,private_runtime_stable=runtime_before=={n:sha(v) for n,v in artifacts.items()},fixture_sha256=fixture_hash,fixture_stable=fixture_hash==sha(fixture_source),workshop_click_branch=branch,prompt_replacements=count,scope=__doc__+' Only list prompt delivery adapted; tap tests call exact verified handoff+DblClick sequence without native input. Runtime/compiler private, no normal profile/app/saves.')
        report['passed']=passed and report['private_runtime_stable'] and report['fixture_stable'];path.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'passed':report['passed'],'report':str(path)},indent=2))
    return 0 if report['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
