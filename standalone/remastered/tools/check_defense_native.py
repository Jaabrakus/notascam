#!/usr/bin/env python3
"""Private staged nearby-defense and exact work-resume acceptance.
Original Human/Orc constructors and stats, actual client-driven game loop.
Mapless encounter positions/equipment and attacker retreat are explicit fixtures. Map actions use the
real client hit-test/network path; HUD actions click actual loaded WebKit DOM
controls and their original byond:// Topic route. No OS input or normal profile.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time
import zipfile

from check_mouse import ROOT, RUNTIME, stop, write_hints
from check_app import error_lines


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def timestamp(value):
    value = re.sub(r'\.(\d+)', lambda match: '.' + (match[1] + '000000')[:6], value)
    return datetime.fromisoformat(value.replace('Z', '+00:00')).timestamp()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=12198)
    parser.add_argument('--webview-dir', '--webview', dest='webview', type=Path, default=Path('/tmp/dm-runtime-audit/full-world-orders-stage/engine/webview-webkit'))
    parser.add_argument('--compiler-dir', type=Path, default=RUNTIME/'compiler')
    parser.add_argument('--server-dir', type=Path, default=RUNTIME / 'server', help='Candidate runtime/server directory; copied privately before launch.')
    parser.add_argument('--client-zip', type=Path, help='Candidate client package; defaults to server-dir/Content.Client.zip.')
    parser.add_argument('--client-assemblies-dir', type=Path, help='Replace client/shared DLL entries in the private client package with these candidates.')
    parser.add_argument('--label', default='defense-native')
    args = parser.parse_args()
    if not 1024 <= args.port <= 52035 or not re.fullmatch(r'[A-Za-z0-9_-]+', args.label):
        parser.error('invalid port or label')
    out = ROOT / 'tests'
    outputs = ['checks.json', 'compile.log', 'server.log', 'client.log', 'world.log', 'animation.jsonl',
               'map-clicks.jsonl', 'state.json', 'before.png', 'selected.png', 'arrived.png', 'startup.png']
    if any((out / f'{args.label}-{suffix}').exists() for suffix in outputs):
        parser.error('output label already has artifacts; choose a fresh --label to preserve existing evidence')
    result = dict(scope=__doc__, started_utc=datetime.now(timezone.utc).isoformat(), checks={}, inputs=[],
                  expected_checks=['original_constructor_stats_and_real_equipment','actual_map_selects_worker','real_chop_then_move_queued','actual_fired_arrow_triggers_alarm','victim_responds','diagonal_radius8_busy_worker_responds','cardinal_radius8_helper_responds','cardinal_radius9_excluded','diagonal_radius9_excluded','other_level_excluded','response_shown_in_live_hud','deselect_preserves_response_and_exact_fifo','worker_moves_to_help_while_deselected','return_phase_observed','same_chop_resumes_after_return','same_pending_move_completes','four_logs_collected_seeds_left','unaffected_bounds_controls_stay_idle','no_extra_alarm_cascade','no_unexpected_native_input','private_runtime_stable','private_clients_stopped'],
                  limitations=['Explicit staged mapless encounter, not natural full-world startup.', 'Real tool/bow/quiver/one-arrow grants use original item APIs; no actor combat/movement/capacity overrides.', 'One original BowTarget call initiates the encounter; scripted live attacker relocation to another level ends danger.', 'Map and native WebKit DOM callbacks use original input/Topic routes but bypass physical OS delivery. No physical touchscreen claim.', 'Original long world season/spawn/save scheduling is disabled only in the private fixture; original client-driven RemasterLoop and constructors run.'])
    report_path = out / f'{args.label}-checks.json'
    server_log, client_log = out / f'{args.label}-server.log', out / f'{args.label}-client.log'
    client_zip = args.client_zip or args.server_dir / 'Content.Client.zip'
    paths = {'compiler':args.compiler_dir/'DMCompiler.dll','standard':args.compiler_dir/'DMStandard/_Standard.dm','runtime': args.server_dir / 'Resources/Assemblies/OpenDreamRuntime.dll',
             'shared': args.server_dir / 'Resources/Assemblies/OpenDreamShared.dll',
             'client_zip': client_zip,
             'webview': args.webview / 'Robust.Client.WebView.dll', 'bridge': args.webview / 'libdmwebkit.dylib',
             'probe_source': Path('/tmp/dm-runtime-audit/full-world-orders-stage/mac-webview/NativeUiProbe.cs'),
             'fixture': ROOT/'tests/defense_native_probe.dm',
             'webview_manager_source': ROOT / 'mac-webview/MacWebViewManager.cs',
             'harness': Path(__file__),
             'star_icon': ROOT / 'game/Icons/mob.dmi'}
    if args.client_assemblies_dir:
        paths.update(candidate_client=args.client_assemblies_dir / 'OpenDreamClient.dll',
                     candidate_shared=args.client_assemblies_dir / 'OpenDreamShared.dll')
    result['hashes_before'] = {key: sha(path) for key, path in paths.items()}
    manifest = {str(path.relative_to(ROOT / 'game')): sha(path) for path in (ROOT / 'game').rglob('*')
                if path.is_file() and path.suffix.lower() in ('.dm', '.dme', '.dmm', '.dmf', '.html', '.dms')}
    result['source_sha256'] = manifest
    server = client = None
    trace = []
    with tempfile.TemporaryDirectory(prefix='dm-defense-native-') as temp:
        base = Path(temp)
        world, probe, cd = base / 'world', base / 'probe', base / 'client'
        probe.mkdir()
        shutil.copytree(ROOT / 'game', world, ignore=shutil.ignore_patterns('Cave Crawlers.json', '*.dmm', '*.sav', 'ErrorLog.txt', 'units', 'saves'))
        dme=(world/'Cave Crawlers.dme').read_text(encoding='latin-1')
        dme=re.sub(r'^#include .*\.dmm"\s*$', '',dme,flags=re.M)
        startup=world/'Code/World.dm'; source=startup.read_text(encoding='latin-1')
        start=source.index('\tNew()');end=source.index('\nvar/Season',start)
        startup.write_text(source[:start]+'\tNew()\n\t\tlog = file("ErrorLog.txt")\n'+source[end:],encoding='latin-1')
        shutil.copy2(paths['fixture'],world/'defense_native_probe.dm')
        fixture=world/'native_defense.dme'
        fixture.write_text(dme+'\n#include "defense_native_probe.dm"\n',encoding='latin-1')
        result['private_fixture_source']={'world_startup':sha(startup),'dme':sha(fixture),'fixture':sha(world/'defense_native_probe.dm')}
        private_server = base / 'runtime-server'
        shutil.copytree(args.server_dir, private_server)
        if args.client_assemblies_dir:
            with zipfile.ZipFile(client_zip) as source, zipfile.ZipFile(private_server / 'client-candidate.zip', 'w', compression=zipfile.ZIP_DEFLATED) as target:
                replaced = set()
                for entry in source.infolist():
                    name = Path(entry.filename).name
                    if name in ('OpenDreamClient.dll', 'OpenDreamShared.dll'):
                        target.writestr(entry, (args.client_assemblies_dir / name).read_bytes())
                        replaced.add(name)
                    else:
                        target.writestr(entry, source.read(entry))
                if replaced != {'OpenDreamClient.dll', 'OpenDreamShared.dll'}:
                    raise RuntimeError('Candidate package is missing expected client/shared assembly entries')
            (private_server / 'client-candidate.zip').replace(private_server / 'Content.Client.zip')
        elif args.client_zip:
            shutil.copy2(client_zip, private_server / 'Content.Client.zip')
        private_webview = base / 'webview'
        shutil.copytree(args.webview, private_webview)
        shutil.copytree(RUNTIME / 'client/Space Station 14.app/Contents/Resources', cd,
                        ignore=shutil.ignore_patterns('user_data', '.DS_Store'))
        private_paths = {'runtime': private_server / 'Resources/Assemblies/OpenDreamRuntime.dll',
                         'shared': private_server / 'Resources/Assemblies/OpenDreamShared.dll',
                         'client_zip': private_server / 'Content.Client.zip',
                         'webview': private_webview / 'Robust.Client.WebView.dll', 'bridge': private_webview / 'libdmwebkit.dylib'}
        result['private_hashes_before'] = {key: sha(path) for key, path in private_paths.items()}
        with zipfile.ZipFile(private_paths['client_zip']) as archive:
            result['mounted_assemblies'] = {name: hashlib.sha256(archive.read(next(p for p in archive.namelist() if p.endswith('/' + name) or p == name))).hexdigest()
                                            for name in ('OpenDreamClient.dll', 'OpenDreamShared.dll')}
        if result['mounted_assemblies']['OpenDreamShared.dll'] != result['private_hashes_before']['shared']:
            raise RuntimeError('Candidate client and server shared assemblies differ; stage a consistent set before running')
        dotnet = RUNTIME / 'dotnet/dotnet'
        env = dict(os.environ, DOTNET_ReadyToRun='0')
        try:
            with (out / f'{args.label}-compile.log').open('w') as log:
                subprocess.run([str(dotnet), str(args.compiler_dir / 'DMCompiler.dll'), str(fixture)],
                               env=env, stdout=log, stderr=subprocess.STDOUT, timeout=180, check=True)
            result['compiled_full_world_sha256'] = sha(fixture.with_suffix('.json'))
            hints = base / 'layout.json'
            write_hints(world / 'skin.dmf', hints)
            env.update(RM_KEEP_2D='1', DM_SKIN_LAYOUT_HINTS=str(hints), DM_NATIVE_UI_PROBE=str(probe), DM_ANIMATION_PROBE='Defense Worker',
                       DM_ANIMATION_PIXEL_PROBE='1', DM_TEST_RACE='Human',
                       DM_GAME_SNAPSHOT=str(out / f'{args.label}-startup.png'),
                       DM_NATIVE_UI_TEST_TITLE='Remastered - Private Staged Defense Check',
                       ROBUST_MODULE_ROBUST_CLIENT_WEBVIEW=str(private_webview))

            def state():
                try: return json.loads((probe / 'state.json').read_text())
                except (FileNotFoundError, ValueError): return {}

            def hud():
                try:
                    code = (probe / 'hud-update.js').read_text().strip().rstrip(';')
                    return json.loads(json.loads(code[len('updateHUD('):-1]))
                except (FileNotFoundError, ValueError): return {}

            observations=[]
            observer_offset=0
            observer_pending=''
            def observed():
                nonlocal observer_offset,observer_pending
                path=world/'ErrorLog.txt'
                if path.exists():
                    with path.open(errors='replace') as stream:
                        stream.seek(observer_offset);observer_pending+=stream.read();observer_offset=stream.tell()
                    lines=observer_pending.split('\n');observer_pending=lines.pop()
                    for line in lines:
                        if 'NATIVE_DEFENSE|state|' in line:
                            observations.append(json.loads(line.split('NATIVE_DEFENSE|state|',1)[1]))
                return observations[-1] if observations else {}

            def hud_action(**values):
                payload=dict(kind=15,window=window()['id'],nonce='hud-'+str(len(result['inputs'])+1));payload.update(values)
                result['inputs'].append(payload)
                (probe/'action.pending').write_text(json.dumps(payload));(probe/'action.pending').replace(probe/'action.json')
                def done():
                    try:return json.loads((probe/'hud-action-result.json').read_text())['nonce']==payload['nonce']
                    except (FileNotFoundError,ValueError):return False
                until(done,6);result['inputs'][-1]['receipt']=json.loads((probe/'hud-action-result.json').read_text())
                time.sleep(.2)

            def samples():
                path = probe / 'animation.jsonl'
                if not path.exists(): return []
                lines = path.read_text().splitlines()
                return [json.loads(line) for line in lines if line.endswith('}')]

            def until(predicate, timeout=15):
                deadline = time.monotonic() + timeout
                while time.monotonic() < deadline:
                    if predicate(): return
                    if client and client.poll() is not None: raise RuntimeError('Private client exited early')
                    if server and server.poll() is not None: raise RuntimeError('Private server exited early')
                    time.sleep(.08)
                raise TimeoutError('Staged defense check timed out')

            def window():
                return next((w for w in state()['windows'] if w.get('viewports')), None) or max(state()['windows'], key=lambda w: w['width'] * w['height'])

            def snapshot(name):
                filename = f'{args.label}-{name}.png'
                path = probe / filename
                (probe / 'capture.txt').write_text(filename)
                until(lambda: path.exists() and path.read_bytes().endswith(b'IEND\xaeB`\x82'), 6)
                shutil.copy2(path, out / filename)
                result.setdefault('screenshots', {})[name] = str(out / filename)

            def selected(model=None):
                return [unit['ref'] for unit in (model or hud()).get('units', []) if unit['selected']]

            def click_tile(x, y, expected):
                model, w = hud(), window()
                view = max(w['viewports'] or [{'rect': {'x': 0, 'y': 0, 'width': w['width'], 'height': w['height']}}], key=lambda v: v['rect']['width'] * v['rect']['height'])
                # Use actual render size; the default view may be changed by the skin.
                tiles_x, tiles_y = view['viewportSize']['width'] / 32, view['viewportSize']['height'] / 32
                payload = dict(kind=9, window=w['id'], x=.5 + (x-model['x'])/tiles_x,
                               y=.5 - (y-model['y'])/tiles_y, expected=expected, nonce=str(len(result['inputs'])+1))
                result['inputs'].append(dict(payload, utc=datetime.now(timezone.utc).isoformat()))
                (probe / 'action.pending').write_text(json.dumps(payload))
                (probe / 'action.pending').replace(probe / 'action.json')
                def ready():
                    try: return json.loads((probe / 'map-click-result.json').read_text()).get('nonce') == payload['nonce']
                    except (FileNotFoundError, ValueError): return False
                until(ready, 6)
                receipt = json.loads((probe / 'map-click-result.json').read_text())
                result['inputs'][-1]['receipt'] = receipt
                return receipt

            with server_log.open('w') as sl, client_log.open('w') as cl:
                server = subprocess.Popen([str(dotnet), str(private_server / 'Robust.Server.dll'), '--data-dir', str(base / 'server-data'),
                    '--cvar', f'opendream.json_path={fixture.with_suffix(".json")}', '--cvar', 'net.bindto=127.0.0.1',
                    '--cvar', f'net.port={args.port}', '--cvar', f'opendream.topic_port={args.port+13500}', '--cvar', 'auth.mode=0',
                    '--cvar', 'status.enabled=false', '--cvar', 'hub.advertise=false', '--cvar', 'game.auto_pause_empty=false'],
                    cwd=world, env=env, stdout=sl, stderr=subprocess.STDOUT)
                until(lambda: ' -> Ready' in server_log.read_text(errors='replace'), 60)
                client = subprocess.Popen([str(dotnet), str(cd / 'Robust.Client.dll'), '--mount-zip', str(private_server / 'Content.Client.zip'),
                    '--connect', '--connect-address', f'udp://127.0.0.1:{args.port}', '--username', 'StagedDefense', '--self-contained',
                    '--cvar', 'web.headless=false', '--cvar', 'discord.enabled=false'], cwd=cd, env=env, stdout=cl, stderr=subprocess.STDOUT)
                until(lambda:len(hud().get('units',[]))==6 and len(samples())>=8 and observed().get('units') and not any(w.get('prompt') for w in state().get('windows',[])),60)
                result['before']=hud();result['initial_observation']=observed()
                ready=json.loads(re.findall(r'NATIVE_DEFENSE\|ready\|([^\r\n]+)',(world/'ErrorLog.txt').read_text(errors='replace'))[-1]);result['audit']=ready
                checks=result['checks'];actor=next(u for u in observed()['units'] if u['name']=='Defense Worker');actor_ref=actor['ref'];result['actor']=actor_ref
                checks['original_constructor_stats_and_real_equipment']=ready['axeEquipped'] and ready['bowEquipped'] and ready['quiverEquipped'] and ready['arrowCount']==1 and actor['capacity']==110 and actor['weight']==25 and actor['skill']==20 and actor['delay']==4
                if not checks['original_constructor_stats_and_real_equipment']:raise RuntimeError('Original constructor/equipment audit mismatch')
                row=next(r for r in samples()[-1]['rows'] if r['name']=='Defense Worker')
                receipt=click_tile(24,24,'entity{'+row['netEntity']+'}')
                checks['actual_map_selects_worker']=receipt['accepted']
                if not receipt['accepted']:raise RuntimeError('Worker map hit mismatch')
                until(lambda:selected()==[actor_ref]);snapshot('selected')
                receipt=click_tile(25,24,'turf{25,24,1}')
                if not receipt['accepted']:raise RuntimeError('Tree map hit mismatch')
                until(lambda:next(u for u in observed()['units'] if u['ref']==actor_ref)['active'])
                hud_action(selector='#queue');until(lambda:hud().get('queue')==1)
                receipt=click_tile(24,20,'turf{24,20,1}')
                if not receipt['accepted']:raise RuntimeError('Queued move map hit mismatch')
                until(lambda:observed().get('phase')=='Responding')
                result['attack']=json.loads(re.findall(r'NATIVE_DEFENSE\|attack\|([^\r\n]+)',(world/'ErrorLog.txt').read_text(errors='replace'))[-1])
                attack_actor=next(u for u in result['attack']['units'] if u['ref']==actor_ref)
                result['task_refs']=[attack_actor['active'],*attack_actor['pending']]
                checks['real_chop_then_move_queued']=len(result['task_refs'])==2 and attack_actor['target']==[25,24,1] and 0<result['attack']['treeHP']<250
                until(lambda:next(u for u in hud()['units'] if u['ref']==actor_ref)['defense']['responding'])
                checks['response_shown_in_live_hud']=True;result['responding_hud']=hud();snapshot('responding')
                hud_action(selector='#deselect')
                until(lambda:observed().get('selection')==0 and hud().get('selection')==0)
                result['deselected']=observed()
                checks['deselect_preserves_response_and_exact_fifo']=result['deselected']['activeSame'] and result['deselected']['pendingSame'] and next(u for u in result['deselected']['units'] if u['ref']==actor_ref)['defense']['responding']
                deadline=time.monotonic()+120
                while time.monotonic()<deadline:
                    current=observed()
                    if 'NATIVE_DEFENSE|error|' in (world/'ErrorLog.txt').read_text(errors='replace'):raise RuntimeError('Unexpected staged actor death')
                    if any(u['blocked'] for u in current['units']):raise RuntimeError('Unexpected blocked unit')
                    if current.get('phase')=='Complete':break
                    time.sleep(.08)
                else:raise TimeoutError('Original worker failed to finish its preserved chop/collect/move within120seconds')
                result['after']=observed();result['hud_after']=hud();snapshot('arrived')
                (world/'native-defense-done.txt').write_text('done');result['observations']=observations

        except Exception as error:
            result['error'] = repr(error)
            if 'hud' in locals(): result['last_hud'] = hud()
            if 'observed' in locals(): result['last_observation']=observed();result['observations']=observations
            if 'state' in locals(): result['last_native_state'] = state()
        finally:
            stop(client)
            stop(server)
            result['checks']['private_clients_stopped'] = all(p is None or p.poll() is not None for p in (server, client))
            log = world / 'ErrorLog.txt'
            if log.exists(): shutil.copy2(log, out / f'{args.label}-world.log')
            for name in ('animation.jsonl', 'map-clicks.jsonl', 'state.json','hud-actions.jsonl'):
                if (probe / name).exists(): shutil.copy2(probe / name, out / f'{args.label}-{name}')
            trace_path = probe / 'animation.jsonl'
            if trace_path.exists(): trace = [json.loads(line) for line in trace_path.read_text().splitlines() if line.endswith('}')]
            result['private_hashes_after'] = {key: sha(path) for key,path in private_paths.items()}
            result['checks']['private_runtime_stable'] = result['private_hashes_before'] == result['private_hashes_after']
    result['source_changes_during_run'] = [name for name,digest in manifest.items() if sha(ROOT / 'game' / name) != digest]
    result['hashes_after'] = {key: sha(path) for key,path in paths.items()}
    return finalize_defense(result,out,args.label)


def finalize_defense(result,out,label):
    checks=result['checks'];history=result.get('observations',[]);initial={u['name']:u for u in result.get('initial_observation',{}).get('units',[])}
    def unit(sample,name='Defense Worker'):return next(u for u in sample['units'] if u['name']==name)
    attack=result.get('attack');after=result.get('after')
    if attack:
        checks['actual_fired_arrow_triggers_alarm']=attack['arrowCount']==0 and attack['attackTime']>0
        for key,name,expected in [('victim_responds','Attacked Human',True),('diagonal_radius8_busy_worker_responds','Defense Worker',True),('cardinal_radius8_helper_responds','Cardinal radius8',True),('cardinal_radius9_excluded','Cardinal radius9',False),('diagonal_radius9_excluded','Diagonal radius9',False),('other_level_excluded','Other level',False)]:
            u=unit(attack,name);checks[key]=bool(u['defense']['responding'])==expected and (not expected or u['caller']=='Attacked Human' and u['defenseTarget']=='Staged Orc archer')
    if history and initial and after:
        refs=result.get('task_refs',[])
        response=[s for s in history if unit(s)['defense']['state']=='Responding']
        returning=[s for s in history if unit(s)['defense']['state']=='Returning']
        checks['worker_moves_to_help_while_deselected']=any(s['selection']==0 and unit(s)['position']!=initial['Defense Worker']['position'] for s in response)
        checks['return_phase_observed']=bool(returning) and all(unit(s)['active']==refs[0] and unit(s)['pending']==refs[1:] for s in returning)
        checks['same_chop_resumes_after_return']=any(s['phase']=='Retreated' and not unit(s)['defense']['responding'] and s['treeHP']<s['attackTreeHP'] and unit(s)['active']==refs[0] for s in history)
        checks['same_pending_move_completes']=any(unit(s)['active']==refs[1] for s in history) and unit(after)['position']==[24,20,1] and not unit(after)['active'] and not unit(after)['pending'] and not unit(after)['defense']['responding']
        checks['four_logs_collected_seeds_left']=unit(after)['wood']==4 and unit(after)['weight']==105 and not after['treeDense'] and after.get('groundSeeds')==2
        controls=['Cardinal radius9','Diagonal radius9','Other level']
        checks['unaffected_bounds_controls_stay_idle']=all(unit(s,n)['position']==initial[n]['position'] and not unit(s,n)['defense']['responding'] and not unit(s,n)['active'] and not unit(s,n)['pending'] for s in history for n in controls)
        checks['no_extra_alarm_cascade']=all(not u['caller'] or u['caller']=='Attacked Human' for s in history for u in s['units'])
    logs={name:(out/f'{label}-{name}.log').read_text(errors='replace') for name in ('server','client','world') if (out/f'{label}-{name}.log').exists()}
    result['errors']={name:error_lines(text) for name,text in logs.items()}
    result['unexpected_native_input']=re.findall(r'native.ui.probe: (?:engine key|event)[^\r\n]*',logs.get('client',''))
    checks['no_unexpected_native_input']=not result['unexpected_native_input']
    result['missing_checks']=[key for key in result['expected_checks'] if key not in checks]
    result['passed']=not result.get('error') and not result['missing_checks'] and all(checks.values()) and not any(result['errors'].values())
    result['finished_utc']=datetime.now(timezone.utc).isoformat()
    (out/f'{label}-checks.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('passed','checks','missing_checks','errors','source_changes_during_run')},indent=2))
    if result.get('error'):print(result['error'])
    return 0 if result['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
