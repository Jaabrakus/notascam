#!/usr/bin/env python3
"""Full-map starting-army check with targeted internal client viewport clicks.

The unmodified copied DME/maps run original world, login and Human constructors.
Race setup uses the existing client smoke command/prompt callbacks. Selection and
orders use real ControlMap/MouseInputSystem hit-testing + network click dispatch,
not DM procedure calls. No OS pointer, focus, keyboard or mouse injection occurs.
This covers the client map callback boundary, not physical OS input delivery.
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
    parser.add_argument('--port', type=int, default=12183)
    parser.add_argument('--webview-dir', '--webview', dest='webview', type=Path, default=Path('/tmp/dm-runtime-audit/full-world-webview'))
    parser.add_argument('--server-dir', type=Path, default=RUNTIME / 'server', help='Candidate runtime/server directory; copied privately before launch.')
    parser.add_argument('--client-zip', type=Path, help='Candidate client package; defaults to server-dir/Content.Client.zip.')
    parser.add_argument('--client-assemblies-dir', type=Path, help='Replace client/shared DLL entries in the private client package with these candidates.')
    parser.add_argument('--label', default='full-world-selection')
    parser.add_argument('--reanalyze', help='Reevaluate preserved native evidence under this earlier label; no client is launched.')
    args = parser.parse_args()
    if not 1024 <= args.port <= 52035 or not re.fullmatch(r'[A-Za-z0-9_-]+', args.label):
        parser.error('invalid port or label')
    out = ROOT / 'tests'
    outputs = ['checks.json', 'compile.log', 'server.log', 'client.log', 'world.log', 'animation.jsonl',
               'map-clicks.jsonl', 'state.json', 'before.png', 'selected.png', 'arrived.png', 'startup.png']
    if any((out / f'{args.label}-{suffix}').exists() for suffix in outputs):
        parser.error('output label already has artifacts; choose a fresh --label to preserve existing evidence')
    if args.reanalyze:
        if not re.fullmatch(r'[A-Za-z0-9_-]+', args.reanalyze) or args.reanalyze == args.label:
            parser.error('use a distinct valid source label for reanalysis')
        source = out / f'{args.reanalyze}-checks.json'
        result = json.loads(source.read_text())
        result['reanalysis'] = dict(source_report=str(source), source_sha256=sha(source), analysis_harness_sha256=sha(Path(__file__)),
            reason='Completed Move status remains Arrived; completion is determined by target position and empty active/pending work, with no pause/block.')
        if result.get('error') != "TimeoutError('Selected unit did not arrive and become idle')":
            raise RuntimeError('This reanalysis only handles the preserved presentation-status mismatch')
        result['reanalysis']['original_harness_error'] = result.pop('error')
        observations = result.get('hud_history', [])
        arrival = next((sample for sample in observations if any(unit['ref'] == result['actor'] and completed(unit, result['move_target']) for unit in sample['units'])), None)
        if arrival is None:
            result['error'] = 'Preserved evidence does not establish successful arrival'
        else:
            result['arrived_utc'] = arrival['utc']
            result['after'] = result['last_hud']
            evaluate_completion(result)
        trace = [json.loads(line) for line in (out / f'{args.reanalyze}-animation.jsonl').read_text().splitlines()]
        return finalize(result, trace, out, args.label, args.reanalyze)
    result = dict(scope=__doc__, started_utc=datetime.now(timezone.utc).isoformat(), checks={}, inputs=[],
                  expected_checks=['unmodified_full_map_source', 'three_original_starting_humans', 'startup_equipment_present',
                    'initial_units_idle_unselected', 'initial_renderer_has_three_units', 'initial_highlights_absent',
                    'exact_unit_hit_accepted', 'single_internal_map_click_selects_exactly_one', 'only_selected_unit_highlighted',
                    'exact_ground_hit_accepted', 'selected_unit_reaches_clicked_ground', 'selection_stays_on_one_unit',
                    'other_two_units_never_move_or_receive_orders', 'selected_unit_returns_to_idle', 'renderer_records_actual_movement',
                    'arrived_body_stable_facing_and_frame', 'other_two_renderer_facings_stay_stable',
                    'selection_highlight_follows_arrival', 'no_world_threat_interrupts_scenario', 'no_unexpected_native_input', 'private_runtime_stable', 'private_clients_stopped'],
                  limitations=['Targeted internal viewport callback dispatch bypasses OS delivery/focus handling; it still uses the real rendered hit map and network click path.',
                    'The race smoke driver calls the original Restart command and answers the original prompt through client callbacks.',
                    'This is a copied-source full-world gameplay/renderer check, not a packaged launcher/save lifecycle test.'])
    report_path = out / f'{args.label}-checks.json'
    server_log, client_log = out / f'{args.label}-server.log', out / f'{args.label}-client.log'
    client_zip = args.client_zip or args.server_dir / 'Content.Client.zip'
    paths = {'runtime': args.server_dir / 'Resources/Assemblies/OpenDreamRuntime.dll',
             'shared': args.server_dir / 'Resources/Assemblies/OpenDreamShared.dll',
             'client_zip': client_zip,
             'webview': args.webview / 'Robust.Client.WebView.dll', 'bridge': args.webview / 'libdmwebkit.dylib',
             'probe_source': ROOT / 'mac-webview/NativeUiProbe.cs',
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
    with tempfile.TemporaryDirectory(prefix='dm-full-world-selection-') as temp:
        base = Path(temp)
        world, probe, cd = base / 'world', base / 'probe', base / 'client'
        probe.mkdir()
        shutil.copytree(ROOT / 'game', world, ignore=shutil.ignore_patterns('Cave Crawlers.json', '*.sav', 'ErrorLog.txt', 'units', 'saves'))
        copied = {name: sha(world / name) for name in manifest}
        result['checks']['unmodified_full_map_source'] = copied == manifest and len(list((world / 'Maps').glob('*.dmm'))) == 4
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
                subprocess.run([str(dotnet), str(RUNTIME / 'compiler/DMCompiler.dll'), str(world / 'Cave Crawlers.dme')],
                               env=env, stdout=log, stderr=subprocess.STDOUT, timeout=180, check=True)
            result['compiled_full_world_sha256'] = sha(world / 'Cave Crawlers.json')
            hints = base / 'layout.json'
            write_hints(world / 'skin.dmf', hints)
            env.update(RM_KEEP_2D='1', DM_SKIN_LAYOUT_HINTS=str(hints), DM_NATIVE_UI_PROBE=str(probe), DM_ANIMATION_PROBE='{Player}',
                       DM_ANIMATION_PIXEL_PROBE='1', DM_TEST_RACE='Human',
                       DM_GAME_SNAPSHOT=str(out / f'{args.label}-startup.png'),
                       DM_NATIVE_UI_TEST_TITLE='Remastered - Private Full World Selection Check',
                       ROBUST_MODULE_ROBUST_CLIENT_WEBVIEW=str(private_webview))

            def state():
                try: return json.loads((probe / 'state.json').read_text())
                except (FileNotFoundError, ValueError): return {}

            def hud():
                try:
                    code = (probe / 'hud-update.js').read_text().strip().rstrip(';')
                    return json.loads(json.loads(code[len('updateHUD('):-1]))
                except (FileNotFoundError, ValueError): return {}

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
                    '--cvar', f'opendream.json_path={world / "Cave Crawlers.json"}', '--cvar', 'net.bindto=127.0.0.1',
                    '--cvar', f'net.port={args.port}', '--cvar', f'opendream.topic_port={args.port+13500}', '--cvar', 'auth.mode=0',
                    '--cvar', 'status.enabled=false', '--cvar', 'hub.advertise=false', '--cvar', 'game.auto_pause_empty=false'],
                    cwd=world, env=env, stdout=sl, stderr=subprocess.STDOUT)
                until(lambda: ' -> Ready' in server_log.read_text(errors='replace'), 60)
                client = subprocess.Popen([str(dotnet), str(cd / 'Robust.Client.dll'), '--mount-zip', str(private_server / 'Content.Client.zip'),
                    '--connect', '--connect-address', f'udp://127.0.0.1:{args.port}', '--username', 'FullWorldSelection', '--self-contained',
                    '--cvar', 'web.headless=false', '--cvar', 'discord.enabled=false'], cwd=cd, env=env, stdout=cl, stderr=subprocess.STDOUT)
                until(lambda: len(hud().get('units', [])) == 3 and len(samples()) >= 15 and not any(w.get('prompt') for w in state().get('windows', [])), 90)
                before = hud()
                result['ready_utc'] = datetime.now(timezone.utc).isoformat()
                result['before'] = before
                units = sorted(before['units'], key=lambda unit: (unit['x'], unit['y']))
                actor = units[0]
                initial = {u['ref']: [u['x'], u['y'], u['z']] for u in units}
                result['actor'] = actor['ref']
                checks = result['checks']
                checks['three_original_starting_humans'] = all(u['race'] == 'Human' for u in units) and before['maxx'] == 1000 and before['maxy'] == 1000 and before['maxz'] == 4
                # Inventory is only exported for selected units. Equipment overlay proof comes from the renderer below.
                checks['initial_units_idle_unselected'] = not selected(before) and all(u['order'] == 'Idle' and not u['active'] and not u['pending'] for u in units)
                rows = sorted(samples()[-1]['rows'], key=lambda row: (row['x'], row['y']))
                checks['initial_renderer_has_three_units'] = len(rows) == 3
                if len(rows) != 3: raise RuntimeError('Expected exactly three renderer rows for starting army')
                unit_rows = {u['ref']: row for u, row in zip(units, rows)}
                result['renderer_units'] = unit_rows
                star_sha = result['hashes_before']['star_icon']
                def stars(row):
                    return [image for image in row.get('clientImages', []) if image['icon']['resourceSha'] == star_sha]
                checks['initial_highlights_absent'] = not any(stars(row) for row in rows)
                checks['startup_equipment_present'] = all(len(row['icon']['children']) >= 3 for row in rows)
                snapshot('before')
                receipt = click_tile(actor['x'], actor['y'], 'entity{' + unit_rows[actor['ref']]['netEntity'] + '}')
                checks['exact_unit_hit_accepted'] = receipt['accepted']
                if not receipt['accepted']: raise RuntimeError('Rendered unit hit did not match intended actor')
                until(lambda: selected() == [actor['ref']])
                result['selected'] = hud()
                checks['single_internal_map_click_selects_exactly_one'] = True
                until(lambda: sum(len(stars(row)) for row in samples()[-1]['rows']) == 1)
                selected_rows = samples()[-1]['rows']
                checks['only_selected_unit_highlighted'] = all(bool(stars(row)) == (row['uid'] == unit_rows[actor['ref']]['uid']) for row in selected_rows)
                snapshot('selected')
                target = [actor['x'], actor['y']+1, actor['z']]
                result['move_target'] = target
                result['move_started_utc'] = datetime.now(timezone.utc).isoformat()
                receipt = click_tile(target[0], target[1], f'turf{{{target[0]},{target[1]},{target[2]}}}')
                checks['exact_ground_hit_accepted'] = receipt['accepted']
                if not receipt['accepted']: raise RuntimeError('Rendered ground hit did not match intended turf')
                history = []
                deadline = time.monotonic()+20
                while time.monotonic()<deadline:
                    model = hud()
                    history.append(dict(utc=datetime.now(timezone.utc).isoformat(), units=model['units'], alert=model.get('alert'), notice=model.get('notice')))
                    result['hud_history'] = history
                    if selected(model) != [actor['ref']]: raise RuntimeError('Unexpected selection change while moving')
                    if any([u['x'],u['y'],u['z']] != initial[u['ref']] or u['active'] or u['pending'] for u in model['units'] if u['ref'] != actor['ref']):
                        raise RuntimeError('Unselected starting unit moved or acquired work')
                    current = next(u for u in model['units'] if u['ref'] == actor['ref'])
                    if current['active'] and current['active']['kind'] != 'Move': raise RuntimeError('Unexpected action kind while moving')
                    if completed(current, target): break
                    time.sleep(.1)
                else: raise TimeoutError('Selected unit did not arrive and become idle')
                result['arrived_utc'] = datetime.now(timezone.utc).isoformat()
                # Observe stationary facing after interpolation has finished.
                time.sleep(3)
                after = hud()
                history.append(dict(utc=datetime.now(timezone.utc).isoformat(), units=after['units'], alert=after.get('alert'), notice=after.get('notice')))
                result['after'] = after
                result['hud_history'] = history
                current = next(u for u in after['units'] if u['ref'] == actor['ref'])
                checks['selected_unit_reaches_clicked_ground'] = [current['x'],current['y'],current['z']] == target
                checks['selection_stays_on_one_unit'] = selected(after) == [actor['ref']]
                checks['other_two_units_never_move_or_receive_orders'] = all([u['x'],u['y'],u['z']] == initial[u['ref']] and not u['active'] and not u['pending'] for sample in history for u in sample['units'] if u['ref'] != actor['ref'])
                checks['selected_unit_returns_to_idle'] = completed(current, target)
                snapshot('arrived')
        except Exception as error:
            result['error'] = repr(error)
            if 'hud' in locals(): result['last_hud'] = hud()
            if 'state' in locals(): result['last_native_state'] = state()
        finally:
            stop(client)
            stop(server)
            result['checks']['private_clients_stopped'] = all(p is None or p.poll() is not None for p in (server, client))
            log = world / 'ErrorLog.txt'
            if log.exists(): shutil.copy2(log, out / f'{args.label}-world.log')
            for name in ('animation.jsonl', 'map-clicks.jsonl', 'state.json'):
                if (probe / name).exists(): shutil.copy2(probe / name, out / f'{args.label}-{name}')
            trace_path = probe / 'animation.jsonl'
            if trace_path.exists(): trace = [json.loads(line) for line in trace_path.read_text().splitlines() if line.endswith('}')]
            result['private_hashes_after'] = {key: sha(path) for key,path in private_paths.items()}
            result['checks']['private_runtime_stable'] = result['private_hashes_before'] == result['private_hashes_after']
    result['source_changes_during_run'] = [name for name,digest in manifest.items() if sha(ROOT / 'game' / name) != digest]
    result['hashes_after'] = {key: sha(path) for key,path in paths.items()}
    return finalize(result, trace, out, args.label, args.label)


def completed(unit, target):
    return [unit['x'], unit['y'], unit['z']] == target and not unit['active'] and not unit['pending'] and not unit['paused'] and not unit['blocked']


def evaluate_completion(result):
    checks, actor, target = result['checks'], result['actor'], result['move_target']
    current = next(unit for unit in result['after']['units'] if unit['ref'] == actor)
    initial = {unit['ref']: [unit['x'],unit['y'],unit['z']] for unit in result['before']['units']}
    checks['selected_unit_reaches_clicked_ground'] = [current['x'],current['y'],current['z']] == target
    checks['selection_stays_on_one_unit'] = all([unit['ref'] for unit in sample['units'] if unit['selected']] == [actor] for sample in result['hud_history'])
    checks['other_two_units_never_move_or_receive_orders'] = all([unit['x'],unit['y'],unit['z']] == initial[unit['ref']] and not unit['active'] and not unit['pending'] for sample in result['hud_history'] for unit in sample['units'] if unit['ref'] != actor)
    checks['selected_unit_returns_to_idle'] = completed(current, target)


def finalize(result, trace, out, label, log_label):
    checks = result['checks']
    if result.get('arrived_utc'):
        actor = result['actor']
        actor_uid = result['renderer_units'][actor]['uid']
        arrived = timestamp(result['arrived_utc'])
        moving = [row for sample in trace if timestamp(sample['utc']) >= timestamp(result['move_started_utc']) for row in sample['rows'] if row['uid'] == actor_uid and row['gliding']]
        idle = [row for sample in trace if timestamp(sample['utc']) >= arrived+.7 for row in sample['rows'] if row['uid'] == actor_uid]
        checks['renderer_records_actual_movement'] = bool(moving) and all(row['icon']['active'] for row in moving)
        checks['arrived_body_stable_facing_and_frame'] = len(idle) >= 10 and len({(row['x'],row['y'],row['parent'],row['icon']['direction'],row['icon']['frame']) for row in idle}) == 1 and all(not row['gliding'] and not row['icon']['active'] and row['icon']['frame'] == 0 for row in idle)
        checks['other_two_renderer_facings_stay_stable'] = all(len({(row['x'],row['y'],row['icon']['direction'],row['icon']['frame']) for sample in trace if timestamp(sample['utc']) >= timestamp(result['ready_utc']) for row in sample['rows'] if row['uid'] == known['uid']}) == 1 for ref,known in result['renderer_units'].items() if ref != actor)
        star_sha = result['hashes_before']['star_icon']
        checks['selection_highlight_follows_arrival'] = bool(idle) and all(sum(image['icon']['resourceSha'] == star_sha for image in row['clientImages']) == 1 for row in idle)
        result['render_summary'] = dict(total_samples=len(trace), moving_samples=len(moving), idle_samples=len(idle),
            walking_frames=sorted({row['icon']['frame'] for row in moving}), idle_directions=sorted({row['icon']['direction'] for row in idle}))
    logs = {name: path.read_text(errors='replace') for name,path in [(name,out / f'{log_label}-{name}.log') for name in ('server','client','world')] if path.exists()}
    result['errors'] = {name: error_lines(text) for name,text in logs.items()}
    result['unexpected_native_input'] = re.findall(r'native.ui.probe: (?:engine key|event)[^\r\n]*', logs.get('client',''))
    checks['no_unexpected_native_input'] = not result['unexpected_native_input']
    initial_hp = {unit['ref']: unit['hp'] for unit in result.get('before', {}).get('units', [])}
    observations = [result[key] for key in ('before', 'selected', 'after', 'last_hud') if key in result] + result.get('hud_history', [])
    result['world_threat_interruptions'] = [dict(alert=sample.get('alert'), notice=sample.get('notice'),
        units=[dict(ref=unit['ref'], hp=unit['hp'], defense=unit.get('defense')) for unit in sample.get('units', [])])
        for sample in observations if sample.get('alert') or any(unit.get('defense', {}).get('responding') or unit['hp'] < initial_hp.get(unit['ref'], unit['hp']) for unit in sample.get('units', []))]
    checks['no_world_threat_interrupts_scenario'] = bool(result.get('before')) and not result['world_threat_interruptions']
    verify_highlight_pixels(result)
    result['missing_checks'] = [key for key in result['expected_checks'] if key not in checks]
    result['finished_utc'] = datetime.now(timezone.utc).isoformat()
    result['passed'] = not result.get('error') and not result['missing_checks'] and all(checks.values()) and not any(result['errors'].values())
    (out / f'{label}-checks.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({key:result[key] for key in ('passed','checks','missing_checks','errors','source_changes_during_run')},indent=2))
    if result.get('error'): print(result['error'])
    return 0 if result['passed'] else 1


def verify_highlight_pixels(result):
    # The original mob.dmi selection marker is bright red. Compare actual map
    # framebuffer crops, not just the client.images attachment table.
    from PIL import Image
    check = 'original_selection_marker_visible_only_over_selected_unit'
    if check not in result['expected_checks']: result['expected_checks'].append(check)
    result['checks'][check] = False
    screenshots = result.get('screenshots', {})
    if 'before' not in screenshots or 'selected' not in screenshots or not result['inputs']: return
    receipt = result['inputs'][0].get('receipt', {})
    if not receipt.get('accepted'): return
    dimensions = [int(value) for value in re.findall(r'\d+', receipt['viewportSize'])]
    if len(dimensions) != 2: return
    tile_x, tile_y = receipt['width'] / (dimensions[0]/32), receipt['height'] / (dimensions[1]/32)
    actor = next(unit for unit in result['before']['units'] if unit['ref'] == result['actor'])
    images = {phase: Image.open(screenshots[phase]).convert('RGB') for phase in ('before','selected')}
    rows = []
    for unit in result['before']['units']:
        x = receipt['x'] + (unit['x']-actor['x'])*tile_x
        y = receipt['y'] - (unit['y']-actor['y'])*tile_y
        box = (round(x-tile_x/2),round(y-tile_y/2),round(x+tile_x/2),round(y+tile_y/2))
        counts = {phase: sum(r>180 and g<90 and b<90 for r,g,b in image.crop(box).getdata()) for phase,image in images.items()}
        rows.append(dict(ref=unit['ref'],box=box,**counts))
    result['selection_pixels'] = rows
    result['checks'][check] = all(row['selected']-row['before'] >= 3 if row['ref'] == actor['ref'] else row['selected'] == row['before'] for row in rows)


if __name__ == '__main__':
    raise SystemExit(main())
