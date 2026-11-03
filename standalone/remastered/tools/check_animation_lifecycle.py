#!/usr/bin/env python3
"""Read real native renderer frames during scripted original-Human movement.

Private world/client/profile; never writes action.json or injects input. Can
test staged engine assemblies before installation. Animation flags/frames are
observations of actual AtomGlideSystem + renderer, never directly manipulated.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time
import zipfile

from check_mouse import ROOT, RUNTIME, stop, write_hints


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--server', type=Path, default=RUNTIME / 'server')
    parser.add_argument('--assemblies', type=Path, help='Staged client/shared DLLs to mount in a private copy of the client package.')
    parser.add_argument('--port', type=int, default=12168)
    parser.add_argument('--analyze-only', action='store_true', help='Re-evaluate the saved raw trace/report without starting a client.')
    args = parser.parse_args()
    out = ROOT / 'tests'
    if args.analyze_only:
        result = json.loads((out / 'animation-lifecycle-checks.json').read_text())
        trace = [json.loads(line) for line in (out / 'animation-lifecycle-trace.jsonl').read_text().splitlines()]
        return analyze(result, trace)
    slp, clp = out / 'animation-lifecycle-server.log', out / 'animation-lifecycle-client.log'
    paths = {'runtime': args.server / 'Resources/Assemblies/OpenDreamRuntime.dll',
             'shared': args.server / 'Resources/Assemblies/OpenDreamShared.dll',
             'client_zip': args.server / 'Content.Client.zip',
             'webview': ROOT / 'engine/webview-webkit/Robust.Client.WebView.dll',
             'fixture': out / 'animation_lifecycle_probe.dm'}
    if args.assemblies:
        paths.update(staged_client=args.assemblies / 'OpenDreamClient.dll', staged_shared=args.assemblies / 'OpenDreamShared.dll')
    result = dict(scope=__doc__, checks={}, hashes_before={k: sha(v) for k, v in paths.items()}, phases=[])
    report_path = out / 'animation-lifecycle-checks.json'
    report_path.write_text(json.dumps(result, indent=2) + '\n')
    server = client = None
    with tempfile.TemporaryDirectory(prefix='dm-animation-lifecycle-') as temp:
        base = Path(temp)
        client_zip = args.server / 'Content.Client.zip'
        if args.assemblies:
            staged_zip = base / 'Content.Client.zip'
            with zipfile.ZipFile(client_zip) as source, zipfile.ZipFile(staged_zip, 'w', compression=zipfile.ZIP_DEFLATED) as target:
                for entry in source.infolist():
                    replacement = args.assemblies / Path(entry.filename).name
                    use_staged = Path(entry.filename).name in ('OpenDreamClient.dll', 'OpenDreamShared.dll')
                    target.writestr(entry, replacement.read_bytes() if use_staged else source.read(entry))
            client_zip = staged_zip
        result['mounted_client_package_sha256'] = sha(client_zip)
        world, probe = base / 'world', base / 'probe'
        probe.mkdir()
        shutil.copytree(ROOT / 'game', world, ignore=shutil.ignore_patterns('Cave Crawlers.json', '*.dmm', '*.sav', 'units', 'saves', 'ErrorLog.txt'))
        text = (world / 'Code/World.dm').read_text(encoding='latin-1')
        start, end = text.index('\tNew()'), text.index('\nvar/Season')
        (world / 'Code/World.dm').write_text(text[:start] + '\tNew()\n\t\tlog = file("ErrorLog.txt")\n' + text[end:], encoding='latin-1')
        dme = re.sub(r'^#include .*\.dmm"\s*$', '', (world / 'Cave Crawlers.dme').read_text(encoding='latin-1'), flags=re.M)
        fixture = world / 'lifecycle.dme'
        shutil.copy2(paths['fixture'], world / 'animation_lifecycle_probe.dm')
        fixture.write_text(dme + '\n#include "animation_lifecycle_probe.dm"\n', encoding='latin-1')
        dotnet = RUNTIME / 'dotnet/dotnet'
        env = dict(os.environ, DOTNET_ReadyToRun='0')
        with (out / 'animation-lifecycle-compile.log').open('w') as log:
            subprocess.run([str(dotnet), str(RUNTIME / 'compiler/DMCompiler.dll'), str(fixture)], env=env, stdout=log, stderr=subprocess.STDOUT, timeout=60, check=True)
        cd = base / 'client'
        shutil.copytree(RUNTIME / 'client/Space Station 14.app/Contents/Resources', cd, ignore=shutil.ignore_patterns('user_data', '.DS_Store'))
        hints = base / 'layout.json'
        write_hints(world / 'skin.dmf', hints)
        env.update(DM_SKIN_LAYOUT_HINTS=str(hints), DM_NATIVE_UI_PROBE=str(probe), DM_ANIMATION_PROBE='Lifecycle ',
                   DM_NATIVE_UI_TEST_TITLE='Remastered - Animation Lifecycle Check',
                   ROBUST_MODULE_ROBUST_CLIENT_WEBVIEW=str(ROOT / 'engine/webview-webkit'))

        def world_log():
            path = world / 'ErrorLog.txt'
            return path.read_text(errors='replace') if path.exists() else ''

        try:
            with slp.open('w') as sl, clp.open('w') as cl:
                server = subprocess.Popen([str(dotnet), str(args.server / 'Robust.Server.dll'), '--data-dir', str(base / 'server-data'), '--cvar', f'opendream.json_path={fixture.with_suffix(".json")}', '--cvar', 'net.bindto=127.0.0.1', '--cvar', f'net.port={args.port}', '--cvar', f'opendream.topic_port={args.port+13500}', '--cvar', 'auth.mode=0', '--cvar', 'status.enabled=false', '--cvar', 'hub.advertise=false', '--cvar', 'game.auto_pause_empty=false'], cwd=world, env=env, stdout=sl, stderr=subprocess.STDOUT)
                deadline = time.monotonic() + 30
                while ' -> Ready' not in slp.read_text(errors='replace'):
                    if time.monotonic() > deadline: raise TimeoutError('Server did not start')
                    time.sleep(.1)
                client = subprocess.Popen([str(dotnet), str(cd / 'Robust.Client.dll'), '--mount-zip', str(client_zip), '--connect', '--connect-address', f'udp://127.0.0.1:{args.port}', '--username', 'AnimationLifecycle', '--self-contained', '--cvar', 'web.headless=false', '--cvar', 'discord.enabled=false'], cwd=cd, env=env, stdout=cl, stderr=subprocess.STDOUT)
                deadline = time.monotonic() + 90
                seen = set()
                while time.monotonic() < deadline:
                    log = world_log()
                    for phase in re.findall(r'LIFECYCLE\|phase\|([^\r\n]+)', log):
                        if phase not in seen:
                            seen.add(phase)
                            result['phases'].append(dict(name=phase, utc=datetime.now(timezone.utc).isoformat()))
                            report_path.write_text(json.dumps(result, indent=2) + '\n')
                    if 'LIFECYCLE|complete|' in log: break
                    if client.poll() is not None: raise RuntimeError('Client exited early')
                    time.sleep(.05)
                else: raise TimeoutError('Lifecycle fixture did not finish')
                time.sleep(.3)
        except Exception as error:
            result['error'] = repr(error)
        finally:
            stop(client)
            stop(server)
            (out / 'animation-lifecycle-world.log').write_text(world_log())
            if (probe / 'animation.jsonl').exists():
                shutil.copy2(probe / 'animation.jsonl', out / 'animation-lifecycle-trace.jsonl')
                trace = [json.loads(line) for line in (probe / 'animation.jsonl').read_text().splitlines()]
            else: trace = []
    result['hashes_after'] = {k: sha(v) for k, v in paths.items()}
    report_path.write_text(json.dumps(result, indent=2) + '\n')
    return analyze(result, trace)


def analyze(result, trace):
    out = ROOT / 'tests'
    slp, clp = out / 'animation-lifecycle-server.log', out / 'animation-lifecycle-client.log'
    checks = result['checks'] = {}
    checks['assemblies_stable'] = result['hashes_before'] == result['hashes_after']
    setup = re.findall(r'LIFECYCLE\|setup\|([^\r\n]+)', (out / 'animation-lifecycle-world.log').read_text())
    result['setup'] = json.loads(setup[0]) if setup else {}
    checks['real_human_chestplate_equipped'] = result['setup'].get('equipped') == 1
    result['samples'] = len(trace)
    def timestamp(value):
        # Python 3.9 accepts 3 or 6 digits; .NET emits 0-7 fractional digits.
        value = re.sub(r'\.(\d+)', lambda m: '.' + (m[1] + '000000')[:6], value)
        return datetime.fromisoformat(value.replace('Z', '+00:00')).timestamp()
    def descendants(icon):
        for child in icon['children']:
            yield child['icon']
            yield from descendants(child['icon'])
    observations = {}
    for index, phase in enumerate(result['phases']):
        start = timestamp(phase['utc']) + .6
        end = timestamp(result['phases'][index+1]['utc']) - .15 if index+1 < len(result['phases']) else float('inf')
        rows = [row for sample in trace if start <= timestamp(sample['utc']) < end for row in sample['rows'] if row['name'] == 'Lifecycle Human']
        observations[phase['name']] = rows
        if 'idle' in phase['name']:
            checks[phase['name'] + '_actual_samples'] = len(rows) >= 5
            checks[phase['name'] + '_body_stable_zero_frame'] = bool(rows) and all(r['icon']['frame'] == 0 and r['icon']['active'] is False and not r['gliding'] for r in rows)
            checks[phase['name'] + '_holds_direction_and_position'] = bool(rows) and len({(r['icon']['direction'], r['x'], r['y'], r['parent']) for r in rows}) == 1
            movement_children = [i for r in rows for i in descendants(r['icon']) if i['movement']]
            checks[phase['name'] + '_equipped_overlays_stable'] = bool(movement_children) and all(i['frame'] == 0 and i['active'] is False for i in movement_children)
    moving = [r for r in observations.get('walking', []) if r['gliding']]
    checks['real_glides_activate_walking'] = len(moving) >= 5 and all(r['icon']['active'] is True for r in moving)
    checks['moving_body_renders_multiple_frames'] = len({r['icon']['frame'] for r in moving}) >= 2
    children = [i for r in moving for i in descendants(r['icon']) if i['movement']]
    checks['moving_equipped_overlay_renders_multiple_frames'] = bool(children) and len({i['frame'] for i in children}) >= 2
    checks['moving_overlays_inherit_active'] = bool(children) and all(i['active'] is True for i in children)
    initial_ids = {i['id'] for r in observations.get('initial_idle', []) for i in descendants(r['icon']) if i['movement']}
    moving_ids = {i['id'] for i in children}
    checks['actual_renderer_overlay_instances_rebuilt'] = bool(initial_ids) and bool(moving_ids - initial_ids)
    fire = [r for sample in trace for r in sample['rows'] if r['name'] == 'Lifecycle Fire']
    checks['stationary_scenery_keeps_animating'] = len({r['icon']['frame'] for r in fire}) >= 2 and all(r['icon']['active'] is False for r in fire)
    result['movement_summary'] = dict(glide_samples=len(moving), body_frames=sorted({r['icon']['frame'] for r in moving}), child_frames=sorted({i['frame'] for i in children}), child_ids=sorted({i['id'] for i in children}))
    humans = [(sample['utc'], row) for sample in trace for row in sample['rows'] if row['name'] == 'Lifecycle Human']
    transitions = []
    for (before_time, before), (after_time, after) in zip(humans, humans[1:]):
        changed_parent = before['parent'] != after['parent']
        if changed_parent or math.dist((before['x'], before['y']), (after['x'], after['y'])) > 2:
            transitions.append(dict(kind='layer_change' if changed_parent else 'teleport', before_utc=before_time, after_utc=after_time,
                before_gliding=before['gliding'], after_gliding=after['gliding'], before_active=before['icon']['active'],
                after_active=after['icon']['active'], after_frame=after['icon']['frame']))
    result['observed_discontinuities'] = transitions
    for kind in ('teleport', 'layer_change'):
        checks[kind + '_actually_interrupts_active_glide'] = any(t['kind'] == kind and t['before_gliding'] and t['before_active'] and not t['after_gliding'] and not t['after_active'] and t['after_frame'] == 0 for t in transitions)
    result['observed_input_events'] = re.findall(r'native.ui.probe: (?:engine key|event)[^\r\n]*', clp.read_text(errors='replace'))
    result['client_errors'] = re.findall(r'\[(?:ERRO|FATL)\][^\r\n]*', clp.read_text(errors='replace'))
    result['server_errors'] = re.findall(r'\[(?:ERRO|FATL)\][^\r\n]*', slp.read_text(errors='replace'))
    result['passed'] = all(checks.values()) and not result.get('error') and not result['client_errors'] and not result['server_errors'] and not result['observed_input_events']
    report = out / 'animation-lifecycle-checks.json'
    report.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
