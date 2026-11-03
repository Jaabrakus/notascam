#!/usr/bin/env python3
"""Private native Work-control identity plus original Human wood-to-Carpentry production check.
All four original maps and original startup/constructors remain unchanged.
An additive DM observer records live objects and any explicit one-time worker/camera placement. Map actions use the
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
    parser.add_argument('--port', type=int, default=12230)
    parser.add_argument('--webview-dir', '--webview', dest='webview', type=Path, default=Path('/tmp/dm-runtime-audit/work-controls-native-stage/engine/webview-webkit'))
    parser.add_argument('--server-dir', type=Path, default=RUNTIME / 'server', help='Candidate runtime/server directory; copied privately before launch.')
    parser.add_argument('--client-zip', type=Path, help='Candidate client package; defaults to server-dir/Content.Client.zip.')
    parser.add_argument('--client-assemblies-dir', type=Path, help='Replace client/shared DLL entries in the private client package with these candidates.')
    parser.add_argument('--label', default='full-world-work')
    parser.add_argument('--candidate', type=Path, default=Path('/tmp/remastered-mining-filter-candidate/game'))
    parser.add_argument('--stage-worker', help='Optional one-time original worker/camera placement at existing grass x,y,z; recorded explicitly.', default='439,269,1')
    parser.add_argument('--html',type=Path,default=Path('/tmp/remastered-work-controls-candidate/game/Interface/remastered.html'))
    args = parser.parse_args()
    placement=None
    if args.stage_worker:
        if not re.fullmatch(r'[0-9]+,[0-9]+,[1-4]', args.stage_worker): parser.error('stage-worker requires x,y,z')
        placement=[int(n) for n in args.stage_worker.split(',')]
        if not all(1<=n<=1000 for n in placement[:2]): parser.error('placement outside original map')
    if not 1024 <= args.port <= 52035 or not re.fullmatch(r'[A-Za-z0-9_-]+', args.label):
        parser.error('invalid port or label')
    out = ROOT / 'tests'
    outputs = ['checks.json', 'compile.log', 'server.log', 'client.log', 'world.log', 'animation.jsonl',
               'map-clicks.jsonl', 'state.json', 'before.png', 'selected.png', 'arrived.png', 'startup.png']
    if any((out / f'{args.label}-{suffix}').exists() for suffix in outputs):
        parser.error('output label already has artifacts; choose a fresh --label to preserve existing evidence')
    result = dict(scope=__doc__, started_utc=datetime.now(timezone.utc).isoformat(), checks={}, inputs=[],
                  expected_checks=['unmodified_full_map_startup_source', 'three_original_starting_humans', 'original_starter_skills_tools_and_weights', 'actual_map_hit_selects_original_worker', 'role_identity_focus_survive_live_queue_status', 'role_release_dispatches_once_preserving_production', 'recipe_identity_focus_survive_live_queue_status', 'recipe_release_queues_exactly_one_attempt', 'selection_change_replaces_held_recipe', 'stale_release_cannot_queue_for_new_selection', 'three_exact_attempts_retained', 'one_original_natural_tree', 'wood_stockpile_and_auto_unload_via_live_hud', 'chop_then_build_location_move_fifo', 'deselection_preserves_harvest_and_production', 'four_woods_and_two_seeds_accounted_before_build', 'real_capacity_detours_observed', 'carpentry_uses_original_two_piece_constructor_and_one_wood', 'production_resumes_after_build_handoff', 'three_attempts_have_original_cost_output_and_skill_effects', 'all_four_woods_consumed_exactly_once', 'original_inventory_weight_retained', 'other_starting_units_unaffected', 'no_unrelated_items_collected', 'capacity_never_exceeded', 'no_world_threat_interrupts_scenario', 'no_unexpected_native_input', 'private_runtime_stable', 'private_clients_stopped'],
                  limitations=['Internal map callbacks and native WebKit DOM clicks bypass physical OS delivery; no physical touchscreen claim.', 'An additive DM observer discovers targets and records effects. Optional --stage-worker only relocates the existing worker/camera once, recorded explicitly; original terrain, stats, tools, AI and RNG remain unchanged.', 'Held actions use explicitly synthetic DOM pointer events followed by click() on the retained original node. This checks live WKWebView identity/dispatch, not trusted physical pointer delivery.'])
    report_path = out / f'{args.label}-checks.json'
    server_log, client_log = out / f'{args.label}-server.log', out / f'{args.label}-client.log'
    client_zip = args.client_zip or args.server_dir / 'Content.Client.zip'
    paths = {'runtime': args.server_dir / 'Resources/Assemblies/OpenDreamRuntime.dll',
             'shared': args.server_dir / 'Resources/Assemblies/OpenDreamShared.dll',
             'client_zip': client_zip,
             'webview': args.webview / 'Robust.Client.WebView.dll', 'bridge': args.webview / 'libdmwebkit.dylib',
             'probe_source': Path('/tmp/dm-runtime-audit/work-controls-native-stage/mac-webview/NativeUiProbe.cs'),
             'fixture': ROOT/'tests/full_world_work_observer.dm',
             'webview_manager_source': ROOT / 'mac-webview/MacWebViewManager.cs',
             'harness': Path(__file__), 'candidate_html':args.html, 'bridge_source':Path('/tmp/dm-runtime-audit/work-controls-native-stage/mac-webview/WebKitBridge.swift'),
             'star_icon': ROOT / 'game/Icons/mob.dmi', 'compiler': RUNTIME/'compiler/DMCompiler.dll'}
    if args.client_assemblies_dir:
        paths.update(candidate_client=args.client_assemblies_dir / 'OpenDreamClient.dll',
                     candidate_shared=args.client_assemblies_dir / 'OpenDreamShared.dll')
    result['hashes_before'] = {key: sha(path) for key, path in paths.items()}
    manifest = {str(path.relative_to(ROOT / 'game')): sha(path) for path in (ROOT / 'game').rglob('*')
                if path.is_file() and path.suffix.lower() in ('.dm', '.dme', '.dmm', '.dmf', '.html', '.dms')}
    result['source_sha256'] = manifest
    server = client = None
    trace = []
    with tempfile.TemporaryDirectory(prefix='dm-full-world-work-') as temp:
        base = Path(temp)
        world, probe, cd = base / 'world', base / 'probe', base / 'client'
        probe.mkdir()
        shutil.copytree(ROOT / 'game', world, ignore=shutil.ignore_patterns('Cave Crawlers.json', '*.sav', 'ErrorLog.txt', 'units', 'saves'))
        copied = {name: sha(world / name) for name in manifest}
        result['checks']['unmodified_full_map_startup_source'] = copied == manifest and len(list((world / 'Maps').glob('*.dmm'))) == 4
        overlays = ('Code/Remastered/Delivery.dm', 'Code/Remastered/Settlement.dm', 'Code/Remastered/HUD.dm', 'Interface/remastered.html')
        result['candidate_sha256'] = {name: sha(args.candidate/name) for name in overlays}
        for name in overlays: shutil.copy2(args.candidate/name, world/name)
        shutil.copy2(args.html,world/'Interface/remastered.html')
        result['work_html_sha256']=sha(args.html)
        result['compiled_source_sha256'] = {name: sha(world/name) for name in manifest}
        private_compiler=base/'compiler'
        shutil.copytree(RUNTIME/'compiler', private_compiler)
        result['compiler_files']={str(p.relative_to(private_compiler)):sha(p) for p in private_compiler.rglob('*') if p.is_file()}
        evidence=out/f'{args.label}-source'
        evidence.mkdir(exist_ok=False)
        for key in ('fixture','harness','probe_source','bridge_source','candidate_html'):
            shutil.copy2(paths[key],evidence/paths[key].name)
        for name in overlays:
            dest=evidence/'candidate'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(world/name,dest)
        result['source_evidence']=str(evidence)
        if placement: (world/'full-work-placement.json').write_text(json.dumps(placement))
        result['requested_placement']=placement
        shutil.copy2(paths['fixture'],world/'full_world_work_observer.dm')
        fixture=world/'full_work.dme'
        fixture.write_text('#include \"Cave Crawlers.dme\"\n#include \"full_world_work_observer.dm\"\n')
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
                subprocess.run([str(dotnet), str(private_compiler / 'DMCompiler.dll'), str(fixture)],
                               env=env, stdout=log, stderr=subprocess.STDOUT, timeout=180, check=True)
            result['compiled_full_world_sha256'] = sha(fixture.with_suffix('.json'))
            hints = base / 'layout.json'
            write_hints(world / 'skin.dmf', hints)
            env.update(RM_KEEP_2D='1', DM_SKIN_LAYOUT_HINTS=str(hints), DM_NATIVE_UI_PROBE=str(probe), DM_ANIMATION_PROBE='{Player}',
                       DM_ANIMATION_PIXEL_PROBE='1', DM_TEST_RACE='Human',
                       DM_GAME_SNAPSHOT=str(out / f'{args.label}-startup.png'),
                       DM_NATIVE_UI_TEST_TITLE='Remastered - Private Full World Work Check',
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
                        if 'FULL_WORK|state|' in line:
                            observations.append(json.loads(line.split('FULL_WORK|state|',1)[1]))
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

            def web_eval(code):
                payload=dict(kind=25,window=window()['id'],nonce='eval-'+str(len(result['inputs'])+1),code=code)
                result['inputs'].append(payload)
                (probe/'action.pending').write_text(json.dumps(payload));(probe/'action.pending').replace(probe/'action.json')
                def done():
                    try:return json.loads((probe/'work-eval-result.json').read_text())['nonce']==payload['nonce']
                    except (FileNotFoundError,ValueError):return False
                until(done,8)
                receipt=json.loads((probe/'work-eval-result.json').read_text());result['inputs'][-1]['receipt']=receipt
                if receipt['error']:raise RuntimeError('Native WebKit diagnostic: '+receipt['error'])
                return json.loads(receipt['value'])

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
                    '--connect', '--connect-address', f'udp://127.0.0.1:{args.port}', '--username', 'FullWorldWork', '--self-contained',
                    '--cvar', 'web.headless=false', '--cvar', 'discord.enabled=false'], cwd=cd, env=env, stdout=cl, stderr=subprocess.STDOUT)
                until(lambda: len(hud().get('units', [])) == 3 and len(samples()) >= 15 and observed().get('actor') and not any(w.get('prompt') for w in state().get('windows', [])), 90)
                before = hud(); observation = observed()
                result['ready_utc'] = datetime.now(timezone.utc).isoformat()
                result['before'] = before; result['initial_observation'] = observation
                ready_match = re.findall(r'FULL_WORK\|ready\|([^\r\n]+)', (world/'ErrorLog.txt').read_text(errors='replace'))
                ready = json.loads(ready_match[-1]); result['audit'] = ready
                checks = result['checks']; actor_ref = ready['actor']; result['actor'] = actor_ref
                actor = next(u for u in before['units'] if u['ref']==actor_ref)
                initial = {u['ref']:u for u in observation['units']}
                worker = initial[actor_ref]
                checks['three_original_starting_humans'] = len(initial)==3 and all(u['type']=='/mob/Monsters/Human' for u in initial.values()) and ready['world']==[1000,1000,4]
                checks['original_starter_skills_tools_and_weights'] = worker['capacity']==110 and worker['weight']==85 and worker['skill']==20 and worker['craftSkill']==25 and any(i['type'].endswith('/Axes/MetalAxe') and i['weight']==25 for i in worker['items'])
                if not checks['original_starter_skills_tools_and_weights']: raise RuntimeError('Unexpected original Human starting equipment/stats; inspect audit')
                if not ready['candidates']:raise RuntimeError('No reachable original natural tree in placement neighborhood')
                target=min(ready['candidates'],key=lambda t:t['distance']);result['target']=target['position']
                checks['one_original_natural_tree']=target['type']=='/turf/grounds/Trees/Tree1' and target['hp']==250
                rows=samples()[-1]['rows'];actor_rows=[row for row in rows if row['x']==actor['x'] and row['y']==actor['y']]
                if len(actor_rows)!=1:raise RuntimeError('Expected exactly one rendered original worker')
                receipt=click_tile(actor['x'],actor['y'],'entity{'+actor_rows[0]['netEntity']+'}')
                checks['actual_map_hit_selects_original_worker']=receipt['accepted']
                if not receipt['accepted']:raise RuntimeError('Worker hit mismatch')
                until(lambda:selected()==[actor_ref]);snapshot('before')
                hud_action(selector='nav [data-value="work"]');until(lambda:hud().get('tab')=='work')
                def actor_state():return next(u for u in observed()['units'] if u['ref']==actor_ref)
                def queue():return actor_state()['production']
                setup = r"""
                const p=window.__workProbe={ids:new WeakMap(),serial:0,held:null,events:[]};
                p.id=e=>{if(!e)return null;if(!p.ids.has(e))p.ids.set(e,++p.serial);return p.ids.get(e)};
                p.capture=()=>({jobs:Array.from(document.querySelectorAll('#jobs button')).map(e=>({id:p.id(e),value:e.dataset.value,disabled:e.disabled})),recipes:Array.from(document.querySelectorAll('#recipes button')).map(e=>({id:p.id(e),value:e.dataset.value,disabled:e.disabled})),workRows:Array.from(document.querySelectorAll('#workunits .workunit')).map(e=>({id:p.id(e),text:e.innerText})),focus:p.id(document.activeElement),focusId:document.activeElement.id,held:p.held?{id:p.id(p.held),connected:p.held.isConnected,current:p.held===document.querySelector(p.selector)}:null,selected:model.units.filter(u=>u.selected).map(u=>u.ref),settlement:model.settlement,events:p.events.slice()});
                document.addEventListener('click',e=>{const b=e.target.closest('button[data-do]');if(b)p.events.push({action:b.dataset.do,value:b.dataset.value,trusted:e.isTrusted})},true);
                return p.capture();
                """
                result['dom_initial']=web_eval(setup)
                def hold(selector):
                    return web_eval('const p=window.__workProbe;p.selector='+json.dumps(selector)+';p.held=document.querySelector(p.selector);if(!p.held||p.held.disabled)throw Error("Invalid hold target");p.held.scrollIntoView({block:"center"});p.held.focus({preventScroll:true});p.held.dispatchEvent(new PointerEvent("pointerdown",{bubbles:true,pointerId:1,pointerType:"touch",isPrimary:true,buttons:1}));return p.capture();')
                def inspect():return web_eval('return window.__workProbe.capture();')
                def release():return web_eval('const p=window.__workProbe;p.held.dispatchEvent(new PointerEvent("pointerup",{bubbles:true,pointerId:1,pointerType:"touch",isPrimary:true,buttons:0}));p.held.click();return p.capture();')
                def identity(a,b):return [(n['id'],n['value']) for n in a['jobs']+a['recipes']]==[(n['id'],n['value']) for n in b['jobs']+b['recipes']]
                role_before=hold('#jobs [data-value="manual"]')
                hud_action(selector='#recipes [data-value="bucket"]');until(lambda:queue()==['bucket']);time.sleep(.8)
                role_after=inspect();result['role_hold']={'before':role_before,'after':role_after}
                checks['role_identity_focus_survive_live_queue_status']=identity(role_before,role_after) and role_after['focus']==role_before['held']['id'] and role_after['held']['connected'] and role_after['settlement']!=role_before['settlement']
                release();until(lambda:actor_state()['job']=='manual');time.sleep(.8)
                role_release=inspect();result['role_release']=role_release
                checks['role_release_dispatches_once_preserving_production']=queue()==['bucket'] and sum(e['action']=='job' and e['value']=='manual' for e in role_release['events'])==1
                recipe_before=hold('#recipes [data-value="spade"]')
                hud_action(selector='#recipes [data-value="spike"]');until(lambda:queue()==['bucket','spike']);time.sleep(.8)
                recipe_after=inspect();result['recipe_hold']={'before':recipe_before,'after':recipe_after}
                checks['recipe_identity_focus_survive_live_queue_status']=identity(recipe_before,recipe_after) and recipe_after['focus']==recipe_before['held']['id'] and recipe_after['held']['connected'] and recipe_after['settlement']!=recipe_before['settlement']
                release();until(lambda:queue()==['bucket','spike','spade']);time.sleep(.5)
                recipe_release=inspect();result['recipe_release']=recipe_release
                checks['recipe_release_queues_exactly_one_attempt']=sum(e['action']=='craft' and e['value']=='spade' for e in recipe_release['events'])==1 and queue()==['bucket','spike','spade']
                stale_before=hold('#recipes [data-value="bucket"]');other_ref=next(ref for ref in initial if ref!=actor_ref)
                hud_action(selector='[data-do="select"][data-value="'+other_ref+'"]');until(lambda:selected()==[other_ref]);time.sleep(.7)
                stale_after=inspect();result['selection_hold']={'before':stale_before,'after':stale_after}
                checks['selection_change_replaces_held_recipe']=not stale_after['held']['connected'] and not stale_after['held']['current'] and not identity(stale_before,stale_after) and stale_after['focusId']=='productionHeading'
                release();time.sleep(.8);result['stale_release']=inspect()
                other=next(u for u in observed()['units'] if u['ref']==other_ref)
                checks['stale_release_cannot_queue_for_new_selection']=not other['production'] and queue()==['bucket','spike','spade'] and len(result['stale_release']['events'])==len(stale_after['events'])
                hud_action(selector='[data-do="select"][data-value="'+actor_ref+'"]');until(lambda:selected()==[actor_ref])
                checks['three_exact_attempts_retained']=queue()==['bucket','spike','spade'];result['production_before']=observed()
                if not all(checks[k] for k in ['role_identity_focus_survive_live_queue_status','recipe_identity_focus_survive_live_queue_status','selection_change_replaces_held_recipe','stale_release_cannot_queue_for_new_selection']):raise RuntimeError('Native Work-control continuity failed; preserve before evidence')
                hud_action(selector='[data-do="stockpile"][data-value="unit"]');until(lambda:hud()['settlement']['stockpile']['set'])
                hud_action(selector='[data-do="stockfilter"][data-value="wood"]');until(lambda:hud()['settlement']['stockpile']['filter']=='wood')
                result['stockpile']=[hud()['settlement']['stockpile'][k] for k in ('x','y','z')]
                hud_action(selector='[data-do="autounload"][data-value="'+actor_ref+'"]');until(lambda:next(u for u in hud()['units'] if u['ref']==actor_ref)['autoUnload'])
                checks['wood_stockpile_and_auto_unload_via_live_hud']=result['stockpile']==worker['position']
                target_pos=result['target'];receipt=click_tile(*target_pos[:2],f'turf{{{target_pos[0]},{target_pos[1]},{target_pos[2]}}}')
                if not receipt['accepted']:raise RuntimeError('Original tree rendered hit mismatch')
                until(lambda:actor_state()['target']==target_pos)
                hud_action(selector='#queue');until(lambda:hud()['queue']==1)
                build=[result['stockpile'][0]+2,result['stockpile'][1],result['stockpile'][2]];result['build_position']=build
                receipt=click_tile(*build[:2],f'turf{{{build[0]},{build[1]},{build[2]}}}')
                if not receipt['accepted']:raise RuntimeError('Original build approach tile rendered hit mismatch')
                until(lambda:len(actor_state()['pending'])==1)
                result['finite_task_refs']=[actor_state()['active'],actor_state()['pending'][0]['ref']]
                checks['chop_then_build_location_move_fifo']=actor_state()['activeKind']=='Chop' and actor_state()['pending'][0]['kind']=='Move' and actor_state()['pending'][0]['target']==build
                hud_action(selector='#deselect');until(lambda:observed()['selection']==0)
                result['deselected_time']=observed()['time']
                def safe():
                    current=observed()
                    if current['alert'] or any(u['defense'] or u['hp']<initial[u['ref']]['hp'] for u in current['units']):raise RuntimeError('World threat interrupted acceptance')
                    if any(u['position']!=initial[u['ref']]['position'] or u['active'] or u['pending'] or u['production'] for u in current['units'] if u['ref']!=actor_ref):raise RuntimeError('Other original unit acquired work or moved')
                    if actor_state()['blocked']:raise RuntimeError('Original worker blocked: '+actor_state()['blocked'])
                    return current
                deadline=time.monotonic()+210
                while time.monotonic()<deadline:
                    current=safe();m=actor_state()
                    if m['position']==build and not m['active'] and not m['pending'] and not m['delivery']:break
                    time.sleep(.1)
                else:raise TimeoutError('Original tree harvest/approach did not finish')
                result['pre_build']=safe();checks['deselection_preserves_harvest_and_production']=result['pre_build']['selection']==0 and queue()==['bucket','spike','spade']
                checks['four_woods_and_two_seeds_accounted_before_build']=len(result['pre_build']['woods'])==4 and all(w['alive'] and w['initial']['weight']==20 for w in result['pre_build']['woods']) and len(result['pre_build']['seeds'])==2 and actor_state()['weight']==105
                hud_action(selector='[data-do="select"][data-value="'+actor_ref+'"]');until(lambda:selected()==[actor_ref])
                hud_action(selector='[data-do="build"][data-value="carpentry"]')
                until(lambda:len(observed()['workshops'])==2,10);result['built']=observed();snapshot('built')
                deadline=time.monotonic()+50
                while time.monotonic()<deadline:
                    safe()
                    if not queue() and len(observed()['products'])==3:break
                    time.sleep(.1)
                else:raise TimeoutError('Original queued production did not resume and complete after build')
                time.sleep(.7);result['after']=safe();snapshot('arrived');result['hud_after']=hud()
                (world/'full-work-done.txt').write_text('done')
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
            result['private_hashes_after'] = {key: sha(path) for key,path in private_paths.items()}
            result['checks']['private_runtime_stable'] = result['private_hashes_before'] == result['private_hashes_after']
    result['candidate_changes_during_run']=[name for name,digest in result['candidate_sha256'].items() if sha(args.candidate/name)!=digest]
    result['source_changes_during_run'] = [name for name,digest in manifest.items() if sha(ROOT / 'game' / name) != digest]
    result['hashes_after'] = {key: sha(path) for key,path in paths.items()}
    return finalize_work(result,out,args.label)


def finalize_work(result,out,label):
    checks=result['checks'];history=result.get('observations',[]);actor=result.get('actor')
    initial={u['ref']:u for u in result.get('initial_observation',{}).get('units',[])}
    def worker(sample):return next(u for u in sample['units'] if u['ref']==actor)
    if history and initial:
        checks['other_starting_units_unaffected']=all(u['position']==initial[u['ref']]['position'] and u['weight']==initial[u['ref']]['weight'] and not u['active'] and not u['pending'] and not u['delivery'] and not u['production'] and u['job']=='manual' for s in history for u in s['units'] if u['ref']!=actor)
        checks['capacity_never_exceeded']=all(worker(s)['capacity']==110 and worker(s)['weight']<=110 for s in history)
        checks['no_unrelated_items_collected']=all(not s['unexpectedInventory'] for s in history)
        checks['real_capacity_detours_observed']=any(worker(s)['delivery'] for s in history)
        checks['no_world_threat_interrupts_scenario']=all(not s['alert'] and all(not u['defense'] and u['hp']>=initial[u['ref']]['hp'] for u in s['units']) for s in history)
    if result.get('after'):
        after=result['after'];m=worker(after);build=result['build_position'];pre=result['pre_build'];woods=after['woods']
        checks['carpentry_uses_original_two_piece_constructor_and_one_wood']=len(after['workshops'])==2 and sorted((w['type'],w['position']) for w in after['workshops'])==[('/mob/WorkShops/Carpentry/Left',[build[0]-1,build[1],build[2]]),('/mob/WorkShops/Carpentry/Right',build)] and worker(pre)['craftSkill']==25 and m['craftSkill']==27.5
        expected={'/obj/Items/Shafts/WoodenBucket':7,'/obj/Items/Shafts/WoodenSpade':5,'/obj/Items/Traps/Spikes/WoodenSpike':5}
        checks['three_attempts_have_original_cost_output_and_skill_effects']=len(after['products'])==3 and {p['type']:p['weight'] for p in after['products']}==expected and m['craftSkill']==25+1+3*.5 and not m['production']
        checks['all_four_woods_consumed_exactly_once']=len(woods)==4 and len({w['token'] for w in woods})==4 and all(not w['alive'] for w in woods)
        checks['production_resumes_after_build_handoff']=not m['rolePaused'] and not m['production'] and not m['paused'] and len(after['products'])==3
        checks['original_inventory_weight_retained']=m['weight']==85 and {i['token'] for i in m['items']}=={i['token'] for i in initial[actor]['items']}
        result['effect_summary']=dict(original_weight=initial[actor]['weight'],final_weight=m['weight'],capacity=m['capacity'],initial_craft_skill=initial[actor]['craftSkill'],final_craft_skill=m['craftSkill'],harvested_wood=len(woods),consumed_wood=sum(not w['alive'] for w in woods),ground_seeds=len(after['seeds']),products=after['products'],workshops=after['workshops'],production_attempts=['bucket','spike','spade'],original_chance_percent=100,capacity_detours=any(worker(s)['delivery'] for s in history))
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
