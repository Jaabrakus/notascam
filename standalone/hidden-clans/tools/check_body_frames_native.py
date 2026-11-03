#!/usr/bin/env python3
"""Observe original MakeBody resources through actual client glides in four directions.

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
    parser.add_argument('--port', type=int, default=12201)
    parser.add_argument('--analyze-only', action='store_true', help='Re-evaluate the saved raw trace/report without starting a client.')
    args = parser.parse_args()
    out = ROOT / 'tests'
    if args.analyze_only:
        result = json.loads((out / 'body-frames-native-checks.json').read_text())
        trace = [json.loads(line) for line in (out / 'body-frames-native-trace.jsonl').read_text().splitlines()]
        return analyze(result, trace)
    slp, clp = out / 'body-frames-native-server.log', out / 'body-frames-native-client.log'
    paths = {'runtime': args.server / 'Resources/Assemblies/OpenDreamRuntime.dll',
             'shared': args.server / 'Resources/Assemblies/OpenDreamShared.dll',
             'client_zip': args.server / 'Content.Client.zip',
             'webview': args.webview / 'Robust.Client.WebView.dll',
             'fixture': out / 'body_frames_probe.dm', 'runner': Path(__file__),
             'human': ROOT / 'game/Icons/Human.dmi', 'orc': ROOT / 'game/Icons/Orc.dmi',
             'human_black': ROOT / 'game/Icons/HumanBlack.dmi',
             'hair': ROOT / 'game/Code/Creatures/Icons/Hair.dmi', 'beard': ROOT / 'game/Code/Creatures/Icons/Beards.dmi', 'female': ROOT / 'game/Code/Creatures/Icons/Female.dmi', 'fire': ROOT / 'game/Icons/Cave.dmi', 'death': ROOT / 'game/Code/Creatures/Death.dm', 'standard': RUNTIME / 'compiler/DMStandard/_Standard.dm', 'compiler': RUNTIME / 'compiler/DMCompiler.dll'}
    reference = ROOT.parent / 'replica/reference/icon-fallback-audit/frames-final/byond/outputs'
    for body in reference.glob('*-body.dmi'):
        paths['reference_' + body.stem] = body
    if args.assemblies:
        paths.update(staged_client=args.assemblies / 'OpenDreamClient.dll', staged_shared=args.assemblies / 'OpenDreamShared.dll')
    result = dict(scope=__doc__, checks={}, hashes_before={k: sha(v) for k, v in paths.items()}, phases=[])
    report_path = out / 'body-frames-native-checks.json'
    report_path.write_text(json.dumps(result, indent=2) + '\n')
    server = client = None
    with tempfile.TemporaryDirectory(prefix='dm-body-frames-native-') as temp:
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
        shutil.copy2(paths['fixture'], world / 'body_frames_probe.dm')
        fixture.write_text(dme + '\n#include "body_frames_probe.dm"\n', encoding='latin-1')
        dotnet = RUNTIME / 'dotnet/dotnet'
        env = dict(os.environ, DOTNET_ReadyToRun='0')
        with (out / 'body-frames-native-compile.log').open('w') as log:
            subprocess.run([str(dotnet), str(RUNTIME / 'compiler/DMCompiler.dll'), str(fixture)], env=env, stdout=log, stderr=subprocess.STDOUT, timeout=60, check=True)
        (world / 'body-output').mkdir()
        result['compiled_world_sha256'] = sha(fixture.with_suffix('.json'))
        copied_sources = {str(p.relative_to(world)): sha(p) for p in sorted(world.rglob('*.dm'))}
        result['copied_dm_source_hashes'] = copied_sources
        cd = base / 'client'
        shutil.copytree(RUNTIME / 'client/Space Station 14.app/Contents/Resources', cd, ignore=shutil.ignore_patterns('user_data', '.DS_Store'))
        hints = base / 'layout.json'
        write_hints(world / 'skin.dmf', hints)
        env.update(DM_SKIN_LAYOUT_HINTS=str(hints), DM_NATIVE_UI_PROBE=str(probe), DM_ANIMATION_PROBE='BodyFrames ',
                   DM_NATIVE_UI_TEST_TITLE='Remastered - Body Frames Check',
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
                client = subprocess.Popen([str(dotnet), str(cd / 'Robust.Client.dll'), '--mount-zip', str(client_zip), '--connect', '--connect-address', f'udp://127.0.0.1:{args.port}', '--username', 'BodyFrames', '--self-contained', '--cvar', 'web.headless=false', '--cvar', 'discord.enabled=false'], cwd=cd, env=env, stdout=cl, stderr=subprocess.STDOUT)
                deadline = time.monotonic() + 90
                seen = set()
                while time.monotonic() < deadline:
                    log = world_log()
                    for phase in re.findall(r'BODYFRAMES\|phase\|([^\r\n]+)', log):
                        if phase not in seen:
                            seen.add(phase)
                            result['phases'].append(dict(name=phase, utc=datetime.now(timezone.utc).isoformat()))
                            report_path.write_text(json.dumps(result, indent=2) + '\n')
                    if 'BODYFRAMES|complete|' in log: break
                    if client.poll() is not None: raise RuntimeError('Client exited early')
                    time.sleep(.05)
                else: raise TimeoutError('Variants fixture did not finish')
                time.sleep(.3)
        except Exception as error:
            result['error'] = repr(error)
        finally:
            stop(client)
            stop(server)
            (out / 'body-frames-native-world.log').write_text(world_log())
            if (probe / 'animation.jsonl').exists():
                shutil.copy2(probe / 'animation.jsonl', out / 'body-frames-native-trace.jsonl')
                trace = [json.loads(line) for line in (probe / 'animation.jsonl').read_text().splitlines()]
            else: trace = []
            shutil.copytree(world / 'body-output', out / 'body-frames-native-outputs', dirs_exist_ok=True)
            resources = out / 'body-frames-native-resources'
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
    resources = out / 'body-frames-native-resources'
    reference = ROOT.parent / 'replica/reference/icon-fallback-audit/frames-final/byond/outputs'
    world_log = (out / 'body-frames-native-world.log').read_text(errors='replace')
    client_log = (out / 'body-frames-native-client.log').read_text(errors='replace')
    server_log = (out / 'body-frames-native-server.log').read_text(errors='replace')
    names = ['human-male','human-female','human-black-female','elf-female','dwarf-male','orc-male','orc-female']
    checks = result['checks'] = {}
    checks['assemblies_fixtures_original_art_stable'] = result.get('hashes_before') == result.get('hashes_after')
    checks['copied_world_sources_stable'] = result.get('copied_dm_sources_stable', False)
    checks['script_completed'] = 'BODYFRAMES|complete|bodies=7' in world_log
    checks['private_world_never_saved_or_injected_input'] = not result.get('private_save_files') and not result.get('injected_input_file_exists')
    found = re.findall(r'BODYFRAMES\|setup\|([^\r\n]+)', world_log)
    setup = result['setup'] = json.loads(found[0]) if found else {}
    checks['seven_original_body_constructors_and_live_human'] = {r['case'] for r in setup.get('bodies',[])} == set(names) and setup.get('live_race') == 'Human'
    expected = {name: read_states(reference/(name+'-body.dmi')) for name in names}
    human_sources = {sha(ROOT/'game/Icons'/name):read_states(ROOT/'game/Icons'/name) for name in ['Human.dmi','HumanBlack.dmi']}
    fire = [s for s in read_states(ROOT/'game/Icons/Cave.dmi') if s['name']=='Fire']
    images, resource_states = {}, {}
    for path in resources.glob('animation-resource-*.dmi'):
        key = path.stem.removeprefix('animation-resource-')
        if sha(path) != key:
            raise ValueError('Observed renderer resource hash differs from retained bytes')
        resource_states[key] = read_states(path)
        images[key] = Image.open(path).convert('RGBA')
    checks['all_seven_native_generated_resources_exact_reference'] = all(
        read_states(out/'body-frames-native-outputs'/(n+'-body.dmi')) == expected[n] for n in names)
    result['reference_hashes'] = {str(reference/(n+'-body.dmi')):sha(reference/(n+'-body.dmi')) for n in names}
    def timestamp(value):
        value = re.sub(r'\.(\d+)', lambda m: '.' + (m[1]+'000000')[:6], value)
        return datetime.fromisoformat(value.replace('Z','+00:00')).timestamp()
    def choose(states, state, active):
        choices = [s for s in states if s['name']==state] or [s for s in states if s['name']=='']
        return next((s for s in choices if bool(s['movement'])==bool(active)), choices[0] if choices else None)
    direction_map = {'South':'south','North':'north','East':'east','West':'west'}
    mismatches = []
    def exact(row, name, phase):
        icon=row['icon'];states=expected.get(name)
        if name=='Live Human': states=human_sources.get(icon.get('resourceSha'),[])
        elif name=='Fire': states=fire
        state=choose(states or [],icon['state'],icon['active'])
        direction=direction_map.get(icon['direction']) if state and state['dirs']>=4 else 'south'
        cells=[c for c in state['cells'] if c['frame']==icon['frame'] and c['direction']==direction] if state else []
        rect=icon.get('textureRect');image=images.get(icon.get('resourceSha'))
        good=bool(cells) and bool(rect) and image is not None and bool(state['movement'])==bool(icon['movement'])
        if good:
            x,y,w,h=[int(rect[k]) for k in ['x','y','width','height']]
            good=pixel_hash(image.crop((x,y,x+w,y+h)))==cells[0]['sha256']
        if not good and len(mismatches)<30:mismatches.append(dict(name=name,phase=phase,icon=icon))
        return good
    def full_cycle(rows):
        seq=[]
        for r in rows:
            f=r['icon']['frame']
            if not seq or seq[-1]!=f:seq.append(f)
        return any(seq[i:i+4]==[0,1,2,0] for i in range(max(0,len(seq)-3)))
    phases={};summaries={}
    for index,phase in enumerate(result['phases']):
        start=timestamp(phase['utc'])+.4
        end=timestamp(result['phases'][index+1]['utc'])-.1 if index+1<len(result['phases']) else float('inf')
        phases[phase['name']]=[r for sample in trace if start<=timestamp(sample['utc'])<end for r in sample['rows'] if r['icon']['loaded']]
    for phase,rows in phases.items():
        if 'idle' not in phase:continue
        for name in names+['Live Human']:
            subset=[r for r in rows if r['name']=='BodyFrames '+name]
            checks[phase+'_'+name+'_stationary_frame0'] = len(subset)>=5 and all(not r['gliding'] and not r['icon']['active'] and r['icon']['frame']==0 for r in subset) and len({(r['x'],r['y'],r['icon']['direction']) for r in subset})==1
            checks[phase+'_'+name+'_exact_source_pixels']=bool(subset) and all(exact(r,name,phase) for r in subset)
    for direction in ['east','north','west','south']:
        phase='walking_'+direction;rows=phases.get(phase,[])
        for name in names+['Live Human']:
            subset=[r for r in rows if r['name']=='BodyFrames '+name and r['gliding']]
            traversal = full_cycle(subset) if name != 'Live Human' else len({r['icon']['frame'] for r in subset}) >= 2
            suffix = '_actual_glide_full_cycle' if name != 'Live Human' else '_actual_glide_animates'
            checks[phase+'_'+name+suffix]=len(subset)>=8 and all(r['icon']['active'] and r['icon']['direction'].lower()==direction for r in subset) and traversal
            checks[phase+'_'+name+'_exact_frame_pixels']=bool(subset) and all(exact(r,name,phase) for r in subset)
            summaries[phase+'_'+name]=dict(samples=len(subset),frames=sorted({r['icon']['frame'] for r in subset}),full_cycle=full_cycle(subset))
    fires=[r for sample in trace for r in sample['rows'] if r['name']=='BodyFrames Fire' and r['icon']['loaded'] and r['icon'].get('textureRect')]
    checks['stationary_fire_keeps_ordinary_animation']=len(fires)>=30 and full_cycle(fires) and all(not r['gliding'] and not r['icon']['active'] and exact(r,'Fire','all') for r in fires)
    result['samples']=len(trace);result['phase_summary']=summaries;result['pixel_mismatches']=mismatches
    result['observed_input_events']=re.findall(r'native.ui.probe: (?:engine key|event)[^\r\n]*',client_log)
    result['client_errors']=re.findall(r'\[(?:ERRO|FATL)\][^\r\n]*',client_log)
    result['server_errors']=re.findall(r'\[(?:ERRO|FATL)\][^\r\n]*',server_log)
    result['world_errors']=re.findall(r'(?im)^.*(?:runtime error|exception|error:).*$|^\s+at [^\r\n]*',world_log)
    checks['no_observed_or_injected_input']=not result['observed_input_events'] and not result.get('injected_input_file_exists')
    checks['no_world_server_client_errors']=not result['world_errors'] and not result['server_errors'] and not result['client_errors']
    result['limits']=['Private rendering fixture; corpse step() motion is scripted solely to exercise animation.', 'No observed client animation frame or movement flag is modified.', 'Original source pixels are compared with BYOND-generated MakeBody references; this does not measure real-world game pacing.']
    result['passed']=all(checks.values()) and not result.get('error')
    (out/'body-frames-native-checks.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(passed=result['passed'],checks=len(checks),samples=len(trace),failures=[k for k,v in checks.items() if not v],error=result.get('error'),report=str(out/'body-frames-native-checks.json')),indent=2))
    for image in images.values():image.close()
    return 0 if result['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
