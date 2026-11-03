#!/usr/bin/env python3
"""Private real-unit altar callback audit; prompt replies scripted, no native input."""
import argparse,hashlib,json,re,shutil,sys,tempfile,zipfile
from pathlib import Path
GAME_ROOT=Path(__file__).resolve().parents[1]
STAGE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(GAME_ROOT/'tools'))
import check_combat as core
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--label',default='before');p.add_argument('--port',type=int,default=12238);p.add_argument('--game-overlay',type=Path,default=GAME_ROOT/'game');p.add_argument('--edges',action='store_true');a=p.parse_args()
 if not re.fullmatch(r'[a-z0-9-]+',a.label):p.error('simple label required')
 if any(f for f in (STAGE/'tests').glob(a.label+'-*')if not f.name.endswith('-runner.log')):p.error('existing evidence; choose fresh label')
 names=['Code/Items/CraftingStations.dm','Code/Remastered/QoL.dm','Code/Remastered/Orders.dm','Code/Remastered/Actions.dm','Code/Remastered/Defense.dm','Code/Items/Item Procs.dm','Code/Items/Food.dm','Code/Creatures/Death.dm','Code/Ownership.dm','Code/Mobs.dm','Cave Crawlers.dme']
 original={n:sha(GAME_ROOT/'game'/n)for n in names}
 for name in names:
  dest=STAGE/'source-before'/name
  if not dest.exists():dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(GAME_ROOT/'game'/name,dest)
 with tempfile.TemporaryDirectory(prefix='dm-altar-audit-')as tmp:
  tmp=Path(tmp);runtime=tmp/'runtime';runtime.mkdir();installed=core.RUNTIME
  for component in ('server','compiler'):shutil.copytree(installed/component,runtime/component)
  (runtime/'dotnet').symlink_to(installed/'dotnet',target_is_directory=True)
  core.RUNTIME=runtime;core.ROOT=STAGE
  artifacts={n:runtime/n for n in ['server/Resources/Assemblies/OpenDreamRuntime.dll','server/Resources/Assemblies/OpenDreamShared.dll','compiler/DMCompiler.dll','compiler/DMStandard/_Standard.dm']}
  runtime_before={n:sha(v)for n,v in artifacts.items()}
  arena=tmp/'game';shutil.copytree(GAME_ROOT/'game',arena,ignore=shutil.ignore_patterns('Cave Crawlers.json','*.dmm','*.sav','saves','units','ErrorLog.txt'))
  if a.game_overlay:
   for name in names:
    if(a.game_overlay/name).is_file():shutil.copy2(a.game_overlay/name,arena/name)
  tested={n:sha(arena/n)for n in names}
  station=arena/'Code/Items/CraftingStations.dm';source=station.read_text(encoding='latin-1');start=source.index('\n\t\t\tGoodAltar\n');end=source.index('\n\t\t\tFire\n',start);section=source[start:end]
  old='input("What Action Will You Choose?", "Choose", null) in menu';count=section.count(old)
  if count not in (0,2):raise RuntimeError('Altar prompt structure changed')
  section=section.replace(old,'usr.RemasterActionChoice("What Action Will You Choose?", "Choose", menu)')
  station.write_text(source[:start]+section+source[end:],encoding='latin-1')
  qol=(arena/'Code/Remastered/QoL.dm').read_text(encoding='latin-1');start=qol.index('\tif(istype(mob, /Player) && !mob.Function && istype(m, /mob/WorkShops))');end=qol.index('\n\tif(',start+1);branch=qol[start:end]
  if 'RemasterButton(m)' not in branch or 'RemasterLegacyHandoff()' not in branch:raise RuntimeError('Workshop dispatch changed')
  condition=next(line for line in branch.splitlines() if 'mob:RemasterLegacyHandoff()' in line)
  eager='!istype(m, /mob/WorkShops/CampFires/GoodAltar)' not in condition
  expected='var/remaster_cooking_fire = istype(m, /mob/WorkShops/CampFires)'
  if expected not in branch:raise RuntimeError('Review altar tap exclusion expression')
  (arena/'altar_config.dm').write_text(f'var/altar_eager={int(eager)}\n')
  entry='AltarEdgeRun' if a.edges else 'AltarRun'
  world=arena/'Code/World.dm';s=world.read_text(encoding='latin-1');start=s.index('\tNew()');end=s.index('\nvar/Season',start);world.write_text(s[:start]+f'\tNew()\n\t\tspawn(0) {entry}()\n'+s[end:],encoding='latin-1')
  fixture_source=STAGE/'tests/altar_handoff_test.dm';fixture_hash=sha(fixture_source);shutil.copy2(fixture_source,arena/fixture_source.name)
  extra=''
  if a.edges:
   shutil.copy2(STAGE/'tests/altar_edge_test.dm',arena/'altar_edge_test.dm');extra='#include "altar_edge_test.dm"\n'
  dme=re.sub(r'^#include .*\.dmm"\s*$','',(arena/'Cave Crawlers.dme').read_text(encoding='latin-1'),flags=re.M);fixture=arena/'altar.dme';fixture.write_text(dme+'\n#include "altar_config.dm"\n#include "altar_handoff_test.dm"\n'+extra,encoding='latin-1')
  with zipfile.ZipFile(STAGE/'tests'/(a.label+'-source.zip'),'w',compression=zipfile.ZIP_DEFLATED) as z:
   for f in arena.rglob('*.dm'):z.write(f,f.relative_to(arena))
   z.write(fixture,fixture.name)
  passed=core.run_world(arena,fixture,a.label,100,prefix='ALTAR',port=a.port)
  path=STAGE/'tests'/(a.label+'-checks.json');report=json.loads(path.read_text());report.update(original_source_sha256=original,tested_source_sha256=tested,private_runtime_sha256=runtime_before,private_runtime_stable=runtime_before=={n:sha(v)for n,v in artifacts.items()},fixture_sha256=fixture_hash,fixture_stable=fixture_hash==sha(fixture_source),workshop_click_branch=branch,prompt_replacements=count,source_changes_during_run=[n for n,v in original.items()if sha(GAME_ROOT/'game'/n)!=v],scope=__doc__+' Actual Human/Orc capacities/stats retained; real flask pickup, natural no-axe blocked Chop plus pending Move. Altar points/contents supplied for original eligibility; no RNG or capacity boosts; specific HP0/GoingToDie/profile/ownership/eligibility mutations deliberately test rejection. Single-tap runs verified handoff+DblClick sequence, not native client input. Only private long-world initialization disabled; original callbacks remain. All sources/server/compiler copied; no normal profile/app/saves.')
  report['edge_fixture_sha256']=sha(STAGE/'tests/altar_edge_test.dm') if a.edges else None
  report['checker_sha256']=sha(Path(__file__))
  report['caught_exceptions']=[x for x in report['observations'] if '|caught|' in x]
  report['passed']=passed and report['private_runtime_stable']and report['fixture_stable'];report['assertion_counts']={'passed':sum('|PASS|'in x for x in report['observations']),'failed':sum('|FAIL|'in x for x in report['observations'])};path.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'passed':report['passed'],'report':str(path),'counts':report['assertion_counts']},indent=2))
 return 0 if report['passed']else 1
if __name__=='__main__':raise SystemExit(main())
