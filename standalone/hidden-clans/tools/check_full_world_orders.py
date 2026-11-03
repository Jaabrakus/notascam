#!/usr/bin/env python3
"""Private full-world original-Human two-tree FIFO and capacity-delivery check.
All four original maps and original startup/constructors remain unchanged.
An additive read-only DM observer records live objects. Map actions use the
real client hit-test/network path; HUD actions click actual loaded WebKit DOM
controls and their original byond:// Topic route. No OS input or normal profile.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import fnmatch
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
import check_app
import check_mouse
import check_browser
import skin_layout


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


GAME_EXCLUDES = ('Cave Crawlers.json', '*.sav', 'ErrorLog.txt', 'units', 'saves')
CLIENT_EXCLUDES = ('user_data', '.DS_Store')


def tree_hashes(root, excludes=()):
    """Include resources/dependencies as well as source; mirror copy exclusions."""
    return {str(path.relative_to(root)): sha(path) for path in sorted(root.rglob('*'))
            if path.is_file() and not any(fnmatch.fnmatchcase(part, pattern)
                for part in path.relative_to(root).parts for pattern in excludes)}


def changed_files(before, after):
    return sorted(key for key in before.keys() | after.keys() if before.get(key) != after.get(key))


def frozen_integrity(result):
    """Missing evidence fails closed, including interrupted setup/compilation."""
    pairs = (('source_sha256', 'source_sha256_after'),
             ('hashes_before', 'hashes_after'),
             ('original_artifacts_before', 'original_artifacts_after'),
             ('copied_source_before', 'copied_source_after'),
             ('private_artifacts_before', 'private_artifacts_after'))
    return (all(isinstance(result.get(a), dict) and bool(result[a]) and
                isinstance(result.get(b), dict) and result[a] == result[b] for a, b in pairs)
            and 'source_changes_during_run' in result and not result['source_changes_during_run']
            and bool(result.get('compiled_full_world_sha256'))
            and result['compiled_full_world_sha256'] == result.get('compiled_full_world_sha256_after'))


def timestamp(value):
    value = re.sub(r'\.(\d+)', lambda match: '.' + (match[1] + '000000')[:6], value)
    return datetime.fromisoformat(value.replace('Z', '+00:00')).timestamp()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=12198)
    parser.add_argument('--webview-dir', '--webview', dest='webview', type=Path, default=Path('/tmp/dm-runtime-audit/full-world-orders-stage/engine/webview-webkit'))
    parser.add_argument('--server-dir', type=Path, default=RUNTIME / 'server', help='Candidate runtime/server directory; copied privately before launch.')
    parser.add_argument('--client-zip', type=Path, help='Candidate client package; defaults to server-dir/Content.Client.zip.')
    parser.add_argument('--client-assemblies-dir', type=Path, help='Replace client/shared DLL entries in the private client package with these candidates.')
    parser.add_argument('--label', default='full-world-orders')
    args = parser.parse_args()
    if not 1024 <= args.port <= 52035 or not re.fullmatch(r'[A-Za-z0-9_-]+', args.label):
        parser.error('invalid port or label')
    out = ROOT / 'tests'
    outputs = ['checks.json', 'compile.log', 'server.log', 'client.log', 'world.log', 'animation.jsonl',
               'map-clicks.jsonl', 'state.json', 'before.png', 'selected.png', 'arrived.png', 'startup.png']
    if any((out / f'{args.label}-{suffix}').exists() for suffix in outputs):
        parser.error('output label already has artifacts; choose a fresh --label to preserve existing evidence')
    result = dict(scope=__doc__, started_utc=datetime.now(timezone.utc).isoformat(), checks={}, inputs=[],
                  expected_checks=['unmodified_full_map_source','three_original_starting_humans','original_starting_axe_and_stats','two_unmodified_natural_trees','actual_map_hit_selects_original_worker','stockpile_auto_unload_via_live_hud','first_tree_real_hit_starts_chop','second_real_tree_appended_in_fifo','hud_deselect_keeps_exact_fifo','two_harvests_complete_while_deselected','other_starting_units_unchanged','first_harvest_collected_before_second_damage','all_eight_wood_conserved','all_four_seeds_remain_on_ground','no_unrelated_inventory_collected','capacity_never_exceeded','real_capacity_detours_observed','pending_task_identity_preserved','no_world_threat_interrupts_scenario','no_unexpected_native_input','private_runtime_stable','private_clients_stopped'],
                  limitations=['Internal map callbacks and native WebKit DOM clicks bypass physical OS delivery; no physical touchscreen claim.', 'A read-only additive DM observer discovers targets and records effects without changing actors, terrain or controllers.', 'The original HUD camera request repositions only the camera so both natural trees can be hit-tested.'])
    report_path = out / f'{args.label}-checks.json'
    server_log, client_log = out / f'{args.label}-server.log', out / f'{args.label}-client.log'
    client_zip = args.client_zip or args.server_dir / 'Content.Client.zip'
    paths = {'runtime': args.server_dir / 'Resources/Assemblies/OpenDreamRuntime.dll',
             'shared': args.server_dir / 'Resources/Assemblies/OpenDreamShared.dll',
             'client_zip': client_zip,
             'webview': args.webview / 'Robust.Client.WebView.dll', 'bridge': args.webview / 'libdmwebkit.dylib',
             'probe_source': Path('/tmp/dm-runtime-audit/full-world-orders-stage/mac-webview/NativeUiProbe.cs'),
             'fixture': ROOT/'tests/full_world_orders_observer.dm',
             'webview_manager_source': ROOT / 'mac-webview/MacWebViewManager.cs',
             'harness': Path(__file__),
             'star_icon': ROOT / 'game/Icons/mob.dmi',
             'native_bootstrap': RUNTIME / 'client/Space Station 14.app/Contents/Resources/Robust.Client.dll',
             'compiler': RUNTIME / 'compiler/DMCompiler.dll',
             'standard': RUNTIME / 'compiler/DMStandard/_Standard.dm',
             'dotnet': RUNTIME / 'dotnet/dotnet',
             'check_app': Path(check_app.__file__), 'check_mouse': Path(check_mouse.__file__),
             'check_browser': Path(check_browser.__file__), 'skin_layout': Path(skin_layout.__file__)}
    if args.client_assemblies_dir:
        paths.update(candidate_client=args.client_assemblies_dir / 'OpenDreamClient.dll',
                     candidate_shared=args.client_assemblies_dir / 'OpenDreamShared.dll')
    result['hashes_before'] = {key: sha(path) for key, path in paths.items()}
    manifest = tree_hashes(ROOT / 'game', GAME_EXCLUDES)
    artifact_roots = {'server': (args.server_dir, ()), 'compiler': (RUNTIME / 'compiler', ()),
                      'dotnet': (RUNTIME / 'dotnet', ()),
                      'client': (RUNTIME / 'client/Space Station 14.app/Contents/Resources', CLIENT_EXCLUDES),
                      'webview': (args.webview, ())}
    result['original_artifacts_before'] = {key: tree_hashes(path, excludes) for key, (path, excludes) in artifact_roots.items()}
    result['source_sha256'] = manifest
    server = client = None
    trace = []
    with tempfile.TemporaryDirectory(prefix='dm-full-world-orders-') as temp:
        base = Path(temp)
        world, probe, cd = base / 'world', base / 'probe', base / 'client'
        probe.mkdir()
        shutil.copytree(ROOT / 'game', world, ignore=shutil.ignore_patterns(*GAME_EXCLUDES))
        copied = {name: sha(world / name) for name in manifest}
        result['copied_source_before'] = copied
        result['checks']['unmodified_full_map_source'] = copied == manifest and len(list((world / 'Maps').glob('*.dmm'))) == 4
        shutil.copy2(paths['fixture'],world/'full_world_orders_observer.dm')
        fixture=world/'full_orders.dme'
        fixture.write_text('#include \"Cave Crawlers.dme\"\n#include \"full_world_orders_observer.dm\"\n')
        private_server = base / 'runtime-server'
        shutil.copytree(args.server_dir, private_server)
        private_compiler = base / 'compiler'
        shutil.copytree(RUNTIME / 'compiler', private_compiler)
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
                        ignore=shutil.ignore_patterns(*CLIENT_EXCLUDES))
        private_paths = {'runtime': private_server / 'Resources/Assemblies/OpenDreamRuntime.dll',
                         'shared': private_server / 'Resources/Assemblies/OpenDreamShared.dll',
                         'client_zip': private_server / 'Content.Client.zip',
                         'webview': private_webview / 'Robust.Client.WebView.dll', 'bridge': private_webview / 'libdmwebkit.dylib'}
        result['private_hashes_before'] = {key: sha(path) for key, path in private_paths.items()}
        private_artifacts = {'server': (private_server, ()), 'compiler': (private_compiler, ()),
                             'client': (cd, CLIENT_EXCLUDES), 'webview': (private_webview, ())}
        result['private_artifacts_before'] = {key: tree_hashes(path, excludes) for key, (path, excludes) in private_artifacts.items()}
        with zipfile.ZipFile(private_paths['client_zip']) as archive:
            result['mounted_assemblies'] = {name: hashlib.sha256(archive.read(next(p for p in archive.namelist() if p.endswith('/' + name) or p == name))).hexdigest()
                                            for name in ('OpenDreamClient.dll', 'OpenDreamShared.dll')}
        if result['mounted_assemblies']['OpenDreamShared.dll'] != result['private_hashes_before']['shared']:
            raise RuntimeError('Candidate client and server shared assemblies differ; stage a consistent set before running')
        dotnet = RUNTIME / 'dotnet/dotnet'
        env = dict(os.environ, DOTNET_ReadyToRun='0')
        try:
            with (out / f'{args.label}-compile.log').open('w') as log:
                subprocess.run([str(dotnet), str(private_compiler / 'DMCompiler.dll'), str(fixture)],
                               env=env, stdout=log, stderr=subprocess.STDOUT, timeout=180, check=True)
            result['compiled_full_world_sha256'] = sha(fixture.with_suffix('.json'))
            hints = base / 'layout.json'
            write_hints(world / 'skin.dmf', hints)
            env.update(RM_KEEP_2D='1', DM_SKIN_LAYOUT_HINTS=str(hints), DM_NATIVE_UI_PROBE=str(probe), DM_ANIMATION_PROBE='{Player}',
                       DM_ANIMATION_PIXEL_PROBE='1', DM_TEST_RACE='Human',
                       DM_GAME_SNAPSHOT=str(out / f'{args.label}-startup.png'),
                       DM_NATIVE_UI_TEST_TITLE='Remastered - Private Full World Orders Check',
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
                        if 'FULL_ORDERS|state|' in line:
                            observations.append(json.loads(line.split('FULL_ORDERS|state|',1)[1]))
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
                raise TimeoutError('Full-world check timed out')

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
                    '--connect', '--connect-address', f'udp://127.0.0.1:{args.port}', '--username', 'FullWorldOrders', '--self-contained',
                    '--cvar', 'web.headless=false', '--cvar', 'discord.enabled=false'], cwd=cd, env=env, stdout=cl, stderr=subprocess.STDOUT)
                until(lambda: len(hud().get('units', [])) == 3 and len(samples()) >= 15 and observed().get('actor') and not any(w.get('prompt') for w in state().get('windows', [])), 90)
                before = hud(); observation = observed()
                result['ready_utc'] = datetime.now(timezone.utc).isoformat()
                result['before'] = before; result['initial_observation'] = observation
                ready_match = re.findall(r'FULL_ORDERS\|ready\|([^\r\n]+)', (world/'ErrorLog.txt').read_text(errors='replace'))
                ready = json.loads(ready_match[-1]); result['audit'] = ready
                checks = result['checks']; actor_ref = ready['actor']; result['actor'] = actor_ref
                actor = next(u for u in before['units'] if u['ref']==actor_ref)
                initial = {u['ref']:u for u in observation['units']}
                worker = initial[actor_ref]
                checks['three_original_starting_humans'] = len(initial)==3 and all(u['type']=='/mob/Monsters/Human' for u in initial.values()) and ready['world']==[1000,1000,4]
                checks['original_starting_axe_and_stats'] = worker['capacity']==110 and worker['skill']==20 and any(i['type'].endswith('/Axes/MetalAxe') for i in worker['items'])
                if not checks['original_starting_axe_and_stats']: raise RuntimeError('Unexpected original Human starting equipment/stats; inspect audit')
                pairs = [(a,b) for a in ready['candidates'] for b in ready['candidates'] if a is not b and max(abs(a['position'][0]-b['position'][0]),abs(a['position'][1]-b['position'][1]))<=10]
                if not pairs: raise RuntimeError('No suitable reachable natural tree pair within original spawn neighborhood')
                first,second = min(pairs,key=lambda pair:pair[0]['distance']+max(abs(pair[0]['position'][0]-pair[1]['position'][0]),abs(pair[0]['position'][1]-pair[1]['position'][1])))
                targets = [first['position'],second['position']];result['targets']=targets
                checks['two_unmodified_natural_trees'] = all(t['type']=='/turf/grounds/Trees/Tree1' and t['hp']==250 for t in (first,second))
                rows = sorted(samples()[-1]['rows'],key=lambda row:(row['x'],row['y']))
                units = sorted(before['units'],key=lambda unit:(unit['x'],unit['y']))
                if len(rows)!=3: raise RuntimeError('Expected original three-Human renderer scene')
                unit_rows={u['ref']:row for u,row in zip(units,rows)}
                receipt=click_tile(actor['x'],actor['y'],'entity{'+unit_rows[actor_ref]['netEntity']+'}')
                checks['actual_map_hit_selects_original_worker']=receipt['accepted']
                if not receipt['accepted']:raise RuntimeError('Worker map hit mismatch')
                until(lambda:selected()==[actor_ref])
                snapshot('before')
                hud_action(selector='nav [data-value="work"]')
                until(lambda:hud().get('tab')=='work')
                hud_action(selector='[data-do="stockpile"][data-value="unit"]')
                until(lambda:hud().get('settlement',{}).get('stockpile',{}).get('set'))
                hud_action(selector='[data-do="stockfilter"][data-value="wood"]')
                until(lambda:hud().get('settlement',{}).get('stockpile',{}).get('filter')=='wood')
                result['stockpile']=[hud()['settlement']['stockpile'][k] for k in ('x','y','z')]
                hud_action(selector='nav [data-value="orders"]')
                until(lambda:hud().get('tab')=='orders')
                hud_action(selector='[data-do="autounload"][data-value="'+actor_ref+'"]')
                until(lambda:next(u for u in hud()['units'] if u['ref']==actor_ref)['autoUnload'])
                checks['stockpile_auto_unload_via_live_hud']=result['stockpile']==worker['position']
                camera=[round((targets[0][0]+targets[1][0])/2),round((targets[0][1]+targets[1][1])/2)]
                hud_action(command='camera',value=','.join(map(str,camera)))
                until(lambda:[hud()['x'],hud()['y']]==camera)
                time.sleep(.5)
                result['camera_positioning']=dict(route='Existing HUD camera request via native WebKit send()',position=camera)
                receipt=click_tile(*targets[0][:2],f'turf{{{targets[0][0]},{targets[0][1]},{targets[0][2]}}}')
                checks['first_tree_real_hit_starts_chop']=receipt['accepted']
                if not receipt['accepted']:raise RuntimeError('First tree rendered hit did not match intended natural turf')
                until(lambda:next(u for u in observed()['units'] if u['ref']==actor_ref)['target']==targets[0])
                hud_action(selector='#queue')
                until(lambda:hud().get('queue')==1)
                receipt=click_tile(*targets[1][:2],f'turf{{{targets[1][0]},{targets[1][1]},{targets[1][2]}}}')
                if not receipt['accepted']:raise RuntimeError('Second tree rendered hit did not match intended natural turf')
                until(lambda:len(next(u for u in observed()['units'] if u['ref']==actor_ref)['pending'])==1)
                queued=observed();worker_queued=next(u for u in queued['units'] if u['ref']==actor_ref)
                result['queued']=queued
                checks['second_real_tree_appended_in_fifo']=worker_queued['target']==targets[0] and worker_queued['pending'][0]['target']==targets[1]
                result['task_refs']=[worker_queued['active'],worker_queued['pending'][0]['ref']]
                snapshot('queued')
                hud_action(selector='#deselect')
                until(lambda:observed().get('selection')==0 and hud().get('selection')==0)
                result['deselected']=observed();result['deselected_time']=observed()['time']
                checks['hud_deselect_keeps_exact_fifo']=next(u for u in observed()['units'] if u['ref']==actor_ref)['active']==result['task_refs'][0] and next(u for u in observed()['units'] if u['ref']==actor_ref)['pending'][0]['ref']==result['task_refs'][1]
                deadline=time.monotonic()+240
                while time.monotonic()<deadline:
                    current=observed();worker_now=next(u for u in current['units'] if u['ref']==actor_ref)
                    if current['alert'] or any(u['defense'] or u['hp']<initial[u['ref']]['hp'] for u in current['units']):raise RuntimeError('Real-world threat interrupted acceptance scenario')
                    if any(u['position']!=initial[u['ref']]['position'] or u['active'] or u['pending'] for u in current['units'] if u['ref']!=actor_ref):raise RuntimeError('Unselected starting unit moved or acquired work')
                    if worker_now['blocked']:raise RuntimeError('Original worker blocked: '+worker_now['blocked'])
                    tree_rows=[t for t in current['trees'] if t['position'] in targets]
                    if len(tree_rows)==2 and all(not t['dense'] for t in tree_rows) and not worker_now['active'] and not worker_now['pending'] and not worker_now['delivery']:
                        result['after']=current;break
                    time.sleep(.1)
                else:raise TimeoutError('Original two-tree harvest/automatic-unload queue did not complete in240seconds')
                time.sleep(1);result['after']=observed();snapshot('arrived')
                (world/'full-orders-done.txt').write_text('done')
                checks['two_harvests_complete_while_deselected']=result['after']['selection']==0
                result['hud_after']=hud()
                result['observations']=observations
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
            result['private_hashes_after'] = {key: sha(path) if path.is_file() else None for key,path in private_paths.items()}
            result['checks']['private_runtime_stable'] = result['private_hashes_before'] == result['private_hashes_after']
            result['copied_source_after'] = {name: sha(world / name) if (world / name).is_file() else None for name in manifest}
            result['private_artifacts_after'] = {key: tree_hashes(path, excludes) for key, (path, excludes) in private_artifacts.items()}
            result['compiled_full_world_sha256_after'] = sha(fixture.with_suffix('.json')) if fixture.with_suffix('.json').is_file() else None
    result['source_sha256_after'] = tree_hashes(ROOT / 'game', GAME_EXCLUDES)
    result['source_changes_during_run'] = changed_files(manifest, result['source_sha256_after'])
    result['original_artifacts_after'] = {key: tree_hashes(path, excludes) for key, (path, excludes) in artifact_roots.items()}
    result['hashes_after'] = {key: sha(path) if path.is_file() else None for key,path in paths.items()}
    return finalize_orders(result,out,args.label)


def finalize_orders(result,out,label):
    checks=result['checks'];history=result.get('observations',[])
    initial={u['ref']:u for u in result.get('initial_observation',{}).get('units',[])}
    actor=result.get('actor');targets=result.get('targets',[])
    def worker(s):return next(u for u in s['units'] if u['ref']==actor)
    def key(pos):return ','.join(map(str,pos))
    def output_map(sample):
        value=sample.get('outputs')
        return value if isinstance(value,dict) else {}
    if history and initial and len(targets)==2:
        after=result.get('after',history[-1]);final=worker(after);stock=result.get('stockpile')
        active_history=[s for s in history if s['time']>=result.get('deselected_time',float('inf'))]
        checks['other_starting_units_unchanged']=all(u['position']==initial[u['ref']]['position'] and not u['active'] and not u['pending'] and not u['delivery'] for s in history for u in s['units'] if u['ref']!=actor)
        second_damage=[s for s in history if any(t['position']==targets[1] and t['hp']<250 for t in s['trees'])]
        def accounted(item):return item['container']==final['rawref'] and item['state']=='(Carrying)' or item['position']==stock and not item['state']
        checks['first_harvest_collected_before_second_damage']=bool(second_damage) and all(len(output_map(s).get(key(targets[0]),[]))==4 and all(accounted(i) for i in output_map(s)[key(targets[0])]) for s in second_damage)
        outputs=[i for group in output_map(after).values() for i in group]
        checks['all_eight_wood_conserved']=len(outputs)==8 and len({i['ref'] for i in outputs})==8 and all(i['type']=='/obj/Items/woods/wood' and i['weight']==20 and accounted(i) for i in outputs)
        checks['all_four_seeds_remain_on_ground']=len(after['seeds'])==4 and all(not i['state'] and i['container']!=final['rawref'] for i in after['seeds'])
        checks['no_unrelated_inventory_collected']=all(not s['unexpectedInventory'] for s in history)
        checks['capacity_never_exceeded']=all(worker(s)['weight']<=worker(s)['capacity'] for s in history)
        checks['real_capacity_detours_observed']=any(worker(s)['delivery'] for s in active_history)
        refs=result.get('task_refs',[])
        checks['pending_task_identity_preserved']=len(refs)==2 and any(worker(s)['active']==refs[1] and worker(s)['target']==targets[1] for s in active_history) and all(worker(s)['active'] in [None,*refs] for s in active_history)
        checks['two_harvests_complete_while_deselected']=checks.get('two_harvests_complete_while_deselected',False) and bool(active_history) and all(s['selection']==0 for s in active_history) and all(not u['active'] and not u['pending'] and not u['delivery'] for u in after['units'])
        result['world_threat_interruptions']=[s for s in history if s['alert'] or any(u['defense'] or u['hp']<initial[u['ref']]['hp'] for u in s['units'])]
        checks['no_world_threat_interrupts_scenario']=not result['world_threat_interruptions']
        result['effect_summary']=dict(samples=len(history),wood=len(outputs),deposited=sum(not i['state'] and i['position']==stock for i in outputs),carried=sum(i['container']==final['rawref'] for i in outputs),seeds=len(after['seeds']),capacity=final['capacity'],final_weight=final['weight'],starting_items=len(initial[actor]['items']),final_items=len(final['items']))
    logs={name:(out/f'{label}-{name}.log').read_text(errors='replace') for name in ('server','client','world') if (out/f'{label}-{name}.log').exists()}
    result['errors']={name:error_lines(text) for name,text in logs.items()}
    result['unexpected_native_input']=re.findall(r'native.ui.probe: (?:engine key|event)[^\r\n]*',logs.get('client',''))
    checks['no_unexpected_native_input']=not result['unexpected_native_input']
    result['missing_checks']=[key for key in result['expected_checks'] if key not in checks]
    result['frozen_integrity_passed'] = frozen_integrity(result)
    result['passed']=not result.get('error') and not result['missing_checks'] and all(checks.values()) and not any(result['errors'].values()) and result['frozen_integrity_passed']
    result['finished_utc']=datetime.now(timezone.utc).isoformat()
    (out/f'{label}-checks.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('passed','checks','missing_checks','errors','source_changes_during_run','frozen_integrity_passed')},indent=2))
    if result.get('error'):print(result['error'])
    return 0 if result['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
