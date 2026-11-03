#!/usr/bin/env python3
"""Verify original Deer and generated sword idle/walk variants in the actual native renderer.

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
import sys
from PIL import Image
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "replica/tools"))
from check_generated_icons import read_states, pixel_hash

from check_mouse import ROOT, RUNTIME, stop, write_hints


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--server', type=Path, default=RUNTIME / 'server')
    parser.add_argument('--assemblies', type=Path, help='Staged client/shared DLLs to mount in a private copy of the client package.')
    parser.add_argument('--webview', type=Path, default=ROOT / 'engine/webview-webkit')
    parser.add_argument('--port', type=int, default=12182)
    parser.add_argument('--analyze-only', action='store_true', help='Re-evaluate the saved raw trace/report without starting a client.')
    args = parser.parse_args()
    out = ROOT / 'tests'
    if args.analyze_only:
        result = json.loads((out / 'dmi-variants-native-checks.json').read_text())
        trace = [json.loads(line) for line in (out / 'dmi-variants-native-trace.jsonl').read_text().splitlines()]
        return analyze(result, trace)
    slp, clp = out / 'dmi-variants-native-server.log', out / 'dmi-variants-native-client.log'
    paths = {'runtime': args.server / 'Resources/Assemblies/OpenDreamRuntime.dll',
             'shared': args.server / 'Resources/Assemblies/OpenDreamShared.dll',
             'client_zip': args.server / 'Content.Client.zip',
             'webview': args.webview / 'Robust.Client.WebView.dll',
             'fixture': out / 'dmi_variants_probe.dm', 'runner': Path(__file__),
             'deer': ROOT / 'game/Icons/Animal.dmi', 'human': ROOT / 'game/Icons/Human.dmi',
             'human_black': ROOT / 'game/Icons/HumanBlack.dmi',
             'sword': ROOT / 'game/Code/Items/Icons/DemonicItems.dmi', 'fire': ROOT / 'game/Icons/Cave.dmi'}
    if args.assemblies:
        paths.update(staged_client=args.assemblies / 'OpenDreamClient.dll', staged_shared=args.assemblies / 'OpenDreamShared.dll')
    result = dict(scope=__doc__, checks={}, hashes_before={k: sha(v) for k, v in paths.items()}, phases=[])
    report_path = out / 'dmi-variants-native-checks.json'
    report_path.write_text(json.dumps(result, indent=2) + '\n')
    server = client = None
    with tempfile.TemporaryDirectory(prefix='dm-dmi-variants-native-') as temp:
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
        fixture = world / 'variants.dme'
        shutil.copy2(paths['fixture'], world / 'dmi_variants_probe.dm')
        fixture.write_text(dme + '\n#include "dmi_variants_probe.dm"\n', encoding='latin-1')
        dotnet = RUNTIME / 'dotnet/dotnet'
        env = dict(os.environ, DOTNET_ReadyToRun='0')
        with (out / 'dmi-variants-native-compile.log').open('w') as log:
            subprocess.run([str(dotnet), str(RUNTIME / 'compiler/DMCompiler.dll'), str(fixture)], env=env, stdout=log, stderr=subprocess.STDOUT, timeout=60, check=True)
        result['compiled_world_sha256'] = sha(fixture.with_suffix('.json'))
        copied_sources = {str(p.relative_to(world)): sha(p) for p in sorted(world.rglob('*.dm'))}
        result['copied_dm_source_hashes'] = copied_sources
        cd = base / 'client'
        shutil.copytree(RUNTIME / 'client/Space Station 14.app/Contents/Resources', cd, ignore=shutil.ignore_patterns('user_data', '.DS_Store'))
        hints = base / 'layout.json'
        write_hints(world / 'skin.dmf', hints)
        env.update(DM_SKIN_LAYOUT_HINTS=str(hints), DM_NATIVE_UI_PROBE=str(probe), DM_ANIMATION_PROBE='Variants ',
                   DM_NATIVE_UI_TEST_TITLE='Remastered - Animation Variants Check',
                   ROBUST_MODULE_ROBUST_CLIENT_WEBVIEW=str(args.webview), DM_ANIMATION_PIXEL_PROBE='1')

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
                client = subprocess.Popen([str(dotnet), str(cd / 'Robust.Client.dll'), '--mount-zip', str(client_zip), '--connect', '--connect-address', f'udp://127.0.0.1:{args.port}', '--username', 'DmiVariants', '--self-contained', '--cvar', 'web.headless=false', '--cvar', 'discord.enabled=false'], cwd=cd, env=env, stdout=cl, stderr=subprocess.STDOUT)
                deadline = time.monotonic() + 90
                seen = set()
                while time.monotonic() < deadline:
                    log = world_log()
                    for phase in re.findall(r'VARIANTS\|phase\|([^\r\n]+)', log):
                        if phase not in seen:
                            seen.add(phase)
                            result['phases'].append(dict(name=phase, utc=datetime.now(timezone.utc).isoformat()))
                            report_path.write_text(json.dumps(result, indent=2) + '\n')
                    if 'VARIANTS|complete|' in log: break
                    if client.poll() is not None: raise RuntimeError('Client exited early')
                    time.sleep(.05)
                else: raise TimeoutError('Variants fixture did not finish')
                time.sleep(.3)
        except Exception as error:
            result['error'] = repr(error)
        finally:
            stop(client)
            stop(server)
            (out / 'dmi-variants-native-world.log').write_text(world_log())
            if (probe / 'animation.jsonl').exists():
                shutil.copy2(probe / 'animation.jsonl', out / 'dmi-variants-native-trace.jsonl')
                trace = [json.loads(line) for line in (probe / 'animation.jsonl').read_text().splitlines()]
            else: trace = []
            resources = out / 'dmi-variants-native-resources'
            resources.mkdir(exist_ok=True)
            for resource in probe.glob('animation-resource-*.dmi'):
                shutil.copy2(resource, resources / resource.name)
            result['injected_input_file_exists'] = (probe / 'action.json').exists()
            result['private_save_files'] = [str(p.relative_to(world)) for p in world.rglob('*.sav')]
            result['copied_dm_sources_stable'] = copied_sources == {str(p.relative_to(world)): sha(p) for p in sorted(world.rglob('*.dm'))}
    result['hashes_after'] = {k: sha(v) for k, v in paths.items()}
    report_path.write_text(json.dumps(result, indent=2) + '\n')
    return analyze(result, trace)


def analyze(result, trace):
    out = ROOT / 'tests'
    resources = out / 'dmi-variants-native-resources'
    world_log = (out / 'dmi-variants-native-world.log').read_text(errors='replace')
    client_log = (out / 'dmi-variants-native-client.log').read_text(errors='replace')
    server_log = (out / 'dmi-variants-native-server.log').read_text(errors='replace')
    checks = result['checks'] = {}
    checks['assemblies_fixtures_original_art_stable'] = result['hashes_before'] == result['hashes_after']
    checks['compiled_private_world_sources_stable'] = result.get('copied_dm_sources_stable', False)
    setup = re.findall(r'VARIANTS\|setup\|([^\r\n]+)', world_log)
    result['setup'] = json.loads(setup[0]) if setup else {}
    checks['real_deer_and_human_original_constructors'] = result['setup'].get('deer') == 'Deer' and result['setup'].get('human') == 'Human'
    checks['real_hell_forged_sword_equipped'] = result['setup'].get('sword_equipped') == 1
    checks['script_completed'] = 'VARIANTS|complete|' in world_log
    checks['private_fixture_never_saved_or_injected_input'] = not result.get('private_save_files') and not result.get('injected_input_file_exists')
    result['samples'] = len(trace)
    def timestamp(value):
        value = re.sub(r'\.(\d+)', lambda m: '.' + (m[1] + '000000')[:6], value)
        return datetime.fromisoformat(value.replace('Z', '+00:00')).timestamp()
    def descendants(icon):
        for child in icon['children']:
            yield child['icon']
            yield from descendants(child['icon'])
    originals = {}
    human_states = {sha(ROOT/'game/Icons'/name): read_states(ROOT/'game/Icons'/name)
                    for name in ('Human.dmi','HumanBlack.dmi')}
    for name, path, state in [('deer','Icons/Animal.dmi',''), ('human','Icons/Human.dmi',''),
                              ('sword','Code/Items/Icons/DemonicItems.dmi','Sword'), ('fire','Icons/Cave.dmi','Fire')]:
        originals[name] = [s for s in read_states(ROOT / 'game' / path) if s['name'] == state]
    resource_states = {}
    images = {}
    for path in resources.glob('animation-resource-*.dmi'):
        resource_hash = path.stem.removeprefix('animation-resource-')
        if sha(path) != resource_hash: raise ValueError('Trace resource hash mismatch')
        resource_states[resource_hash] = read_states(path)
        images[resource_hash] = Image.open(path).convert('RGBA')
    def state_signature(state):
        return state['movement'], state['dirs'], state['frames'], state['cells']
    def is_sword(icon):
        states = resource_states.get(icon.get('resourceSha'), [])
        return len(states) == 2 and [state_signature(s) for s in states] == [state_signature(s) for s in originals['sword']]
    direction_map = {'South':'south','North':'north','East':'east','West':'west',
                     'Southeast':'east','Southwest':'west','Northeast':'east','Northwest':'west'}
    mismatches = []
    def exact(icon, name, moving, phase):
        states = originals[name]
        if name == 'human':
            source_states = human_states.get(icon.get('resourceSha'), [])
            states = [s for s in source_states if s['name'] == icon['state']] or [s for s in source_states if s['name'] == '']
            if not states: return False
        state = next((s for s in states if bool(s['movement']) == moving), states[0])
        direction = direction_map.get(icon['direction'].replace(' ', ''), '') if state['dirs'] >= 4 else 'south'
        cells = [c for c in state['cells'] if c['direction'] == direction and c['frame'] == icon['frame']]
        rect = icon.get('textureRect')
        good = bool(cells) and bool(rect) and icon.get('resourceSha') in images
        if good:
            image = images[icon['resourceSha']]
            x,y,w,h = [int(rect[k]) for k in ('x','y','width','height')]
            good = pixel_hash(image.crop((x,y,x+w,y+h))) == cells[0]['sha256'] and bool(icon['movement']) == bool(state['movement'])
        if not good and len(mismatches) < 20:
            mismatches.append(dict(name=name, phase=phase, moving=moving, icon=icon))
        return good
    phases = {}
    for index, phase in enumerate(result['phases']):
        start = timestamp(phase['utc']) + .6
        end = timestamp(result['phases'][index+1]['utc']) - .15 if index+1 < len(result['phases']) else float('inf')
        rows = [r for sample in trace if start <= timestamp(sample['utc']) < end for r in sample['rows']]
        phases[phase['name']] = rows
        if 'idle' not in phase['name']: continue
        for name in ('deer','human'):
            bodies = [r for r in rows if r['name'] == 'Variants ' + name.title()]
            checks[f'{phase["name"]}_{name}_enough_actual_samples'] = len(bodies) >= 5
            checks[f'{phase["name"]}_{name}_stationary_facing_position'] = bool(bodies) and all(not r['gliding'] and not r['icon']['active'] and r['icon']['frame'] == 0 for r in bodies) and len({(r['icon']['direction'],r['x'],r['y']) for r in bodies}) == 1
            checks[f'{phase["name"]}_{name}_original_idle_pixels'] = bool(bodies) and all(exact(r['icon'],name,False,phase['name']) for r in bodies)
        swords = [i for r in rows if r['name'] == 'Variants Human' for i in descendants(r['icon']) if is_sword(i)]
        checks[phase['name'] + '_generated_sword_both_variants_survive'] = len(swords) >= 5
        checks[phase['name'] + '_sword_idle_art_keeps_ordinary_animation'] = bool(swords) and len({i['frame'] for i in swords}) >= 2 and all(not i['active'] and exact(i,'sword',False,phase['name']) for i in swords)
    walking = {}
    for phase in ('walking_east','walking_northwest'):
        rows = phases.get(phase, [])
        for name in ('deer','human'):
            bodies = [r for r in rows if r['name'] == 'Variants ' + name.title() and r['gliding']]
            walking[phase+'_'+name] = dict(samples=len(bodies), frames=sorted({r['icon']['frame'] for r in bodies}))
            checks[phase+'_'+name+'_actual_glides_animate_correct_variant'] = len(bodies) >= 3 and len({r['icon']['frame'] for r in bodies}) >= 2 and all(r['icon']['active'] and exact(r['icon'],name,True,phase) for r in bodies)
        swords = [i for r in rows if r['name'] == 'Variants Human' and r['gliding'] for i in descendants(r['icon']) if is_sword(i)]
        checks[phase+'_generated_sword_walks_with_parent'] = len(swords) >= 3 and len({i['frame'] for i in swords}) >= 2 and all(i['active'] and exact(i,'sword',True,phase) for i in swords)
    initial_ids = {i['id'] for r in phases.get('initial_idle',[]) if r['name']=='Variants Human' for i in descendants(r['icon']) if is_sword(i)}
    moved_ids = {i['id'] for r in phases.get('walking_east',[]) if r['name']=='Variants Human' and r['gliding'] for i in descendants(r['icon']) if is_sword(i)}
    checks['real_sword_overlay_rebuilt_during_glide_inherits_parent_state'] = bool(initial_ids) and bool(moved_ids - initial_ids)
    fire = [r for sample in trace for r in sample['rows'] if r['name']=='Variants Fire' and r['icon']['loaded']]
    checks['ordinary_fire_keeps_original_looping_pixels'] = len({r['icon']['frame'] for r in fire}) >= 2 and all(not r['icon']['active'] and exact(r['icon'],'fire',False,'all') for r in fire)
    result['movement_summary'] = walking
    result['pixel_mismatches'] = mismatches
    result['observed_input_events'] = re.findall(r'native.ui.probe: (?:engine key|event)[^\r\n]*', client_log)
    result['client_errors'] = re.findall(r'\[(?:ERRO|FATL)\][^\r\n]*', client_log)
    result['server_errors'] = re.findall(r'\[(?:ERRO|FATL)\][^\r\n]*', server_log)
    result['world_errors'] = re.findall(r'(?im)^.*(?:runtime error|exception|error:).*$|^\s+at [^\r\n]*', world_log)
    checks['no_observed_input'] = not result['observed_input_events']
    checks['no_world_server_or_client_errors'] = not result['world_errors'] and not result['server_errors'] and not result['client_errors']
    result['passed'] = all(checks.values()) and not result.get('error')
    (out / 'dmi-variants-native-checks.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k != 'pixel_mismatches'},indent=2))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())

