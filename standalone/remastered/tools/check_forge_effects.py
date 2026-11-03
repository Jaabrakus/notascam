#!/usr/bin/env python3
"""Real Human/Orc Forge callback tests; scripted prompt delivery, no native client."""
import argparse,hashlib,json,re,shutil,sys,tempfile,zipfile
from pathlib import Path
STAGE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(STAGE/'tools'))
import check_combat as core
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--label',required=True);p.add_argument('--candidate',action='store_true',help='Compatibility flag; current game is the default');p.add_argument('--baseline',type=Path);p.add_argument('--port',type=int,default=12251);a=p.parse_args()
 if not re.fullmatch(r'[a-z0-9-]+',a.label):p.error('simple label required')
 if(STAGE/'tests'/(a.label+'-checks.json')).exists():p.error('evidence exists; choose fresh label')
 names=['Code/Items/CraftingStations.dm','Code/Remastered/QoL.dm']
 candidate_hashes={n:sha(STAGE/'game'/n)for n in names}
 artifacts=['server/Resources/Assemblies/OpenDreamRuntime.dll','server/Resources/Assemblies/OpenDreamShared.dll','compiler/DMCompiler.dll','compiler/DMStandard/_Standard.dm']
 runtime=STAGE/'runtime' if (STAGE/'runtime/server').exists() else STAGE.parent/'replica/runtime/macos-x64';runtime_hashes={n:sha(runtime/n)for n in artifacts};core.ROOT=STAGE;core.RUNTIME=runtime
 fixture_source=STAGE/'tests/forge_effects_test.dm';fixture_hash=sha(fixture_source)
 with tempfile.TemporaryDirectory(prefix='dm-forge-audit-')as tmp:
  arena=Path(tmp)/'game';shutil.copytree(STAGE/'game',arena,ignore=shutil.ignore_patterns('Cave Crawlers.json','*.dmm','*.sav','ErrorLog.txt','saves','units'))
  if a.baseline:
   for n in names:shutil.copy2(a.baseline/n,arena/n)
  source_hashes={str(f.relative_to(arena)):sha(f)for f in arena.rglob('*.dm')}
  station=arena/'Code/Items/CraftingStations.dm';s=station.read_text(encoding='latin-1');start=s.index('\n\t\tForge\n');end=s.index('\n\t\tPotionStation\n',start);section=s[start:end]
  section,count=re.subn(r'input\("What Action Will You Choose\?", "Choose", null\) in (menu2?)',lambda m:'usr.RemasterActionChoice("What Action Will You Choose?", "Choose", '+m[1]+')',section)
  section,amounts=re.subn(r'input\("Amount\?"\)as null\|num',lambda m:'usr:RemasterForgeAmount()',section)
  if(count,amounts)not in((2,2),(0,0)):raise RuntimeError('Original Forge prompt shape changed')
  section,rolls=re.subn(r'prob\((M\.MetalCraftingSkill(?:\*4)?)\)',r'ForgeRoll(\1)',section)
  if rolls!=110:raise RuntimeError('Unexpected Forge RNG count')
  station.write_text(s[:start]+section+s[end:],encoding='latin-1')
  qol=(arena/'Code/Remastered/QoL.dm').read_text(encoding='latin-1');start=qol.index('\tif(istype(mob, /Player) && !mob.Function && istype(m, /mob/WorkShops))');end=qol.index('\n\tif(',start+1);branch=qol[start:end]
  if'RemasterButton(m)'not in branch:raise RuntimeError('Original workshop callback route changed')
  condition=next(line for line in branch.splitlines()if'mob:RemasterLegacyHandoff()'in line)
  eager='!istype(m, /mob/WorkShops/Forge)'not in condition
  (arena/'forge_config.dm').write_text(f'var/forge_eager={int(eager)}\n')
  w=arena/'Code/World.dm';s=w.read_text(encoding='latin-1');start=s.index('\tNew()');end=s.index('\nvar/Season',start);w.write_text(s[:start]+'\tNew()\n\t\tspawn(0) ForgeRun()\n'+s[end:],encoding='latin-1')
  shutil.copy2(fixture_source,arena/fixture_source.name)
  dme=re.sub(r'^#include .*\.dmm"\s*$','',(arena/'Cave Crawlers.dme').read_text(encoding='latin-1'),flags=re.M)
  fixture=arena/'forge.dme';fixture.write_text(dme+'\n#include "forge_config.dm"\n#include "forge_effects_test.dm"\n',encoding='latin-1')
  with zipfile.ZipFile(STAGE/'tests'/(a.label+'-source.zip'),'w',compression=zipfile.ZIP_DEFLATED)as z:
   for f in arena.rglob('*.dm'):z.write(f,f.relative_to(arena))
   z.write(fixture,fixture.name)
  passed=core.run_world(arena,fixture,a.label,180,prefix='FORGE',port=a.port)
 report_path=STAGE/'tests'/(a.label+'-checks.json');d=json.loads(report_path.read_text())
 d.update(source_sha256=source_hashes,candidate_stable=candidate_hashes=={n:sha(STAGE/'game'/n)for n in names},runtime_sha256_before=runtime_hashes,runtime_stable=runtime_hashes=={n:sha(runtime/n)for n in artifacts},fixture_sha256=fixture_hash,fixture_stable=fixture_hash==sha(fixture_source),checker_sha256=sha(Path(__file__)),prompt_replacements=count,amount_replacements=amounts,test_only_rng_call_adapters=rolls,workshop_click_branch=branch,caught_exceptions=[x for x in d['observations']if'|caught|'in x],scope=__doc__+' Actual constructors, capacity, skills, item weights, pickup/equip/drop unchanged; each test-only deterministic RNG selector is separately recorded. Natural missing-axe Chop plus pending Move holds work through prompt yields without changing CanWalk. Initial items/station placement and deliberate invalid actor/profile/ownership flags are disclosed test setup. Tap controls replay the source-verified eager handoff+DblClick sequence, not native mouse input. No normal app/profile/save or full-world launch.')
 d['counts']={'passed':sum('|PASS|'in x for x in d['observations']),'failed':sum('|FAIL|'in x for x in d['observations'])};d['passed']=passed and d['candidate_stable']and d['runtime_stable']and d['fixture_stable']and not d['caught_exceptions'];report_path.write_text(json.dumps(d,indent=2)+'\n');print(json.dumps({'passed':d['passed'],'counts':d['counts'],'report':str(report_path)},indent=2));return 0 if d['passed']else 1
if __name__=='__main__':raise SystemExit(main())
