#!/usr/bin/env python3
"""Current-source regression entry point. Scope/report each isolated fixture separately."""
from pathlib import Path
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
import argparse,hashlib,json,re,subprocess
root=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description='Run isolated current-source gameplay regressions; no normal save or native input.')
parser.add_argument('--label',required=True)
parser.add_argument('--port-base',type=int,default=12510)
parser.add_argument('--workers',type=int,choices=(1,2,3),default=2)
a=parser.parse_args()
if not re.fullmatch(r'[a-z0-9-]{1,50}',a.label): parser.error('label requires1-50 lowercase letters, digits or hyphens')
if not 1024<=a.port_base<=51000: parser.error('port-base must be1024-51000, reserving topic ports')
if list((root/'tests').glob(a.label+'-*-checks.json')) or (root/'tests'/(a.label+'-regressions.json')).exists(): parser.error('label already has evidence; choose another')
runtime=root/'runtime' if (root/'runtime/server').exists() else root.parent/'replica/runtime/macos-x64'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def hashes():
    result={str(p.relative_to(root/'game')):sha(p) for p in sorted((root/'game').rglob('*')) if p.is_file() and p.suffix.lower() in ('.dm','.dme','.dmf','.dmm','.html')}
    for rel in ('server/Resources/Assemblies/OpenDreamRuntime.dll','server/Resources/Assemblies/OpenDreamShared.dll','server/Content.Client.zip','compiler/DMCompiler.dll','compiler/DMStandard/_Standard.dm'):
        result['runtime/'+rel]=sha(runtime/rel)
    return result
jobs=[('idle','check_idle.py',[]),('smelter','check_smelter_handoff.py',[]),('mining','check_mining_filter.py',['--candidate',str(root/'game')]),('guard','check_guard_context.py',[]),('curated','check_curated_actions.py',[]),('manual','check_manual_handoff.py',[]),('carpentry','check_build_handoff.py',[]),('masonry','check_masonary_handoff.py',[]),('terrain-build','check_build_handoff.py',['--terrain']),('terrain-life','check_terrain_lifetime.py',[]),('delivery','check_delivery_commit.py',[]),('orders','check_easy_orders.py',[]),('defense','check_defense.py',[]),('inventory','check_ui_references.py',[]),('magic','check_magic_target.py',[]),('groups','check_control_groups.py',[])]
jobs += [('selection','check_selection_rejection.py',[]),('cooking','check_cooking_handoff.py',['--game-overlay',str(root/'game')]),('cooking-group','check_cooking_handoff.py',['--game-overlay',str(root/'game'),'--group']),('altars','check_altar_handoff.py',['--game-overlay',str(root/'game')]),('altar-edges','check_altar_handoff.py',['--game-overlay',str(root/'game'),'--edges']),('production-pause','check_production_pause.py',[]),('work-lifetime','check_work_lifetime.py',[]),('production-defense','check_production_defense.py',[]),('quick-build','check_quick_build.py',[])]
jobs += [('melter','check_melter_handoff.py',[]),('melter-groups','check_melter_groups.py',[]),('dragon','check_dragon_defense.py',[]),('work-selection','check_work_selection.py',[]),('selection-intent','check_selection_intent.py',[])]
jobs += [('combat-recursion','check_combat_recursion.py',[])]
jobs += [('pause-projection','check_pause_projection.py',[]),('carried-modal','check_ordinary_inventory.py',[]),('equipment-pickup','check_equipment_pickup.py',[])]
jobs += [('forge','check_forge_handoff.py',[]),('forge-effects','check_forge_effects.py',[]),('forge-groups','check_forge_groups.py',[]),('forge-soul','check_forge_soul_edges.py',[])]
jobs += [('order-eligibility','check_order_eligibility.py',[])]
jobs += [('elemental-defense','check_elemental_defense.py',[]),('holy-defense','check_holy_defense.py',[]),('holy-walls','check_holy_walls.py',[]),('projectile-defense','check_projectile_defense.py',[])]
jobs += [('poison','check_poison_handoff.py',[]),('poison-effects','check_poison_effects.py',[]),('gem','check_gem_handoff.py',[]),('gem-effects','check_gem_effects.py',[])]
jobs += [('fire-projectile','check_fire_projectile.py',[])]
jobs += [('potion','check_potion_handoff.py',[]),('potion-effects','check_potion_effects.py',[]),('vampire-defense','check_vampire_defense.py',[])]
jobs += [('bone','check_bone_handoff.py',[]),('bone-effects','check_bone_effects.py',[]),('werewolf-defense','check_werewolf_defense.py',[])]
jobs += [('leather','check_leather_handoff.py',[]),('leather-effects','check_leather_effects.py',[])]
started=datetime.now(timezone.utc).isoformat();before=hashes()
def run(job):
    i,(label,tool,args)=job;label=a.label+'-'+label
    cmd=['python3',str(root/'tools'/tool),'--label',label,'--port',str(a.port_base+i),*args]
    log=root/f'tests/{label}-runner.log'
    with log.open('w') as f:
        try:code=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,timeout=360).returncode
        except subprocess.TimeoutExpired:code=124
    report=root/f'tests/{label}-checks.json'
    data=json.loads(report.read_text()) if report.exists() else {}
    record=dict(label=label,exit_code=code,passed=code==0 and data.get('passed') is True,checks=sum('|PASS|' in str(v) or '|FAIL|' in str(v) for v in data.get('observations',[])),report=str(report),report_sha256=sha(report) if report.exists() else None)
    print(json.dumps(record),flush=True);return record
with ThreadPoolExecutor(max_workers=a.workers) as pool:records=list(pool.map(run,enumerate(jobs)))
after=hashes();result=dict(started_utc=started,finished_utc=datetime.now(timezone.utc).isoformat(),before=before,after=after,sources_and_artifacts_stable=before==after,reports=records,passed=before==after and all(v['passed'] for v in records))
(root/'tests'/(a.label+'-regressions.json')).write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(passed=result['passed'],checks=sum(v['checks'] for v in records))),flush=True)
raise SystemExit(0 if result['passed'] else 1)
