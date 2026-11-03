#!/usr/bin/env python3
"""Observe native classic-border visibility through a private connected client.

No injected keyboard or mouse input: the DM fixture scripts original callbacks,
waits for the real WebKit ready handshake, and inspects live client.screen.
This verifies alpha/mouse-opacity state, not a synthesized map click hit test.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time

from check_mouse import ROOT, RUNTIME, stop, write_hints


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    out = ROOT / 'tests'
    server_log = out / 'command-dock-native-server.log'
    client_log = out / 'command-dock-native-client.log'
    paths = {'runtime': RUNTIME / 'server/Resources/Assemblies/OpenDreamRuntime.dll',
             'client_zip': RUNTIME / 'server/Content.Client.zip',
             'webview': ROOT / 'engine/webview-webkit/Robust.Client.WebView.dll',
             'fixture': out / 'command_dock_probe.dm'}
    for name in ('Code/Remastered/BorderControls.dm', 'Code/Remastered/HUD.dm',
                 'Interface/remastered.html', 'Interface/border-controls.json', 'skin.dmf'):
        paths[name] = ROOT / 'game' / name
    result = dict(scope=__doc__, hashes_before={key:sha(path) for key,path in paths.items()},
                  checks={}, phases=[], screenshots=[], injected_inputs=[])
    result['limitations'] = [
        'Engine framebuffer screenshots show map/border state; macOS WebKit overlays are not captured by this hook.',
        'No synthetic clicks: native non-interactivity is verified through live alpha/mouse_opacity, not OS hit-test events.']
    server = client = None
    with tempfile.TemporaryDirectory(prefix='dm-command-dock-') as temp:
        base = Path(temp)
        world, probe = base/'world', base/'probe'
        probe.mkdir()
        shutil.copytree(ROOT/'game', world, ignore=shutil.ignore_patterns(
            'Cave Crawlers.json', '*.dmm', '*.sav', 'units', 'saves', 'ErrorLog.txt'))
        source = (world/'Code/World.dm').read_text(encoding='latin-1')
        start, end = source.index('\tNew()'), source.index('\nvar/Season')
        (world/'Code/World.dm').write_text(source[:start]+'\tNew()\n\t\tlog = file("ErrorLog.txt")\n'+source[end:],encoding='latin-1')
        dme = re.sub(r'^#include .*\.dmm"\s*$', '', (world/'Cave Crawlers.dme').read_text(encoding='latin-1'), flags=re.M)
        fixture = world/'command_dock.dme'
        shutil.copy2(paths['fixture'],world/'command_dock_probe.dm')
        fixture.write_text(dme+'\n#include "command_dock_probe.dm"\n',encoding='latin-1')
        dotnet = RUNTIME/'dotnet/dotnet'
        env = dict(os.environ,DOTNET_ReadyToRun='0')
        with (out/'command-dock-native-compile.log').open('w') as log:
            subprocess.run([str(dotnet),str(RUNTIME/'compiler/DMCompiler.dll'),str(fixture)],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=60,check=True)
        cd = base/'client'
        shutil.copytree(RUNTIME/'client/Space Station 14.app/Contents/Resources',cd,ignore=shutil.ignore_patterns('user_data','.DS_Store'))
        hints = base/'layout.json'
        write_hints(world/'skin.dmf',hints)
        env.update(DM_SKIN_LAYOUT_HINTS=str(hints),DM_NATIVE_UI_PROBE=str(probe),
                   DM_NATIVE_UI_TEST_TITLE='Remastered - Command Dock Check',
                   ROBUST_MODULE_ROBUST_CLIENT_WEBVIEW=str(ROOT/'engine/webview-webkit'))

        def world_log():
            path = world/'ErrorLog.txt'
            return path.read_text(errors='replace') if path.exists() else ''

        def until(condition, seconds):
            deadline = time.monotonic()+seconds
            while not condition():
                if time.monotonic()>deadline: raise TimeoutError('Native command dock probe timed out')
                time.sleep(.05)

        def screenshot(phase):
            filename = 'command-dock-native-'+phase+'.png'
            # Capture only this private client's viewport using its read-only
            # probe hook. The hook takes no OS input and cannot target another app.
            (probe/'capture.txt').write_text(filename)
            path = probe/filename
            until(lambda:path.exists() and path.read_bytes().endswith(b'IEND\xaeB`\x82'),5)
            shutil.copy2(path,out/filename)
            result['screenshots'].append(str(out/filename))

        try:
            with server_log.open('w') as sl, client_log.open('w') as cl:
                server = subprocess.Popen([str(dotnet),str(RUNTIME/'server/Robust.Server.dll'),'--data-dir',str(base/'server-data'),
                    '--cvar',f'opendream.json_path={fixture.with_suffix(".json")}',
                    '--cvar','net.bindto=127.0.0.1','--cvar','net.port=12175','--cvar','opendream.topic_port=25675',
                    '--cvar','auth.mode=0','--cvar','status.enabled=false','--cvar','hub.advertise=false','--cvar','game.auto_pause_empty=false'],
                    cwd=world,env=env,stdout=sl,stderr=subprocess.STDOUT)
                until(lambda:' -> Ready' in server_log.read_text(errors='replace'),30)
                client = subprocess.Popen([str(dotnet),str(cd/'Robust.Client.dll'),'--mount-zip',str(RUNTIME/'server/Content.Client.zip'),
                    '--connect','--connect-address','udp://127.0.0.1:12175','--username','CommandDockObserver','--self-contained',
                    '--cvar','web.headless=false','--cvar','discord.enabled=false'],cwd=cd,env=env,stdout=cl,stderr=subprocess.STDOUT)
                deadline = time.monotonic()+50
                while time.monotonic()<deadline:
                    for phase in re.findall(r'COMMAND_DOCK\|phase\|([^\r\n]+)',world_log()):
                        if phase not in result['phases']:
                            result['phases'].append(phase)
                            time.sleep(.35)
                            screenshot(phase)
                    if 'COMMAND_DOCK|complete|' in world_log(): break
                    if client.poll() is not None: raise RuntimeError('Private client exited early')
                    time.sleep(.05)
                else: raise TimeoutError('Fixture did not finish')
                if (probe/'state.json').exists():
                    shutil.copy2(probe/'state.json',out/'command-dock-native-state.json')
        except Exception as error:
            result['error'] = repr(error)
        finally:
            stop(client)
            stop(server)
            log = world_log()
            (out/'command-dock-native-world.log').write_text(log)
            result['checks'].update({label:status=='PASS' for status,label in re.findall(r'COMMAND_DOCK\|(PASS|FAIL)\|([^\r\n]+)',log)})
            result['checks']['fixture_completed'] = 'COMMAND_DOCK|complete|failures=0' in log
            result['checks']['no_input_instruction_file_created'] = not (probe/'action.json').exists() and not (probe/'action.pending').exists()
            result['checks']['no_world_save_created'] = not list(world.rglob('*.sav'))
            diagnostics = re.findall(r'COMMAND_DOCK\|diagnostic\|([^\r\n]+)',log)
            result['diagnostic'] = json.loads(diagnostics[0]) if diagnostics else {}
    result['hashes_after'] = {key:sha(path) for key,path in paths.items()}
    result['checks']['source_runtime_fixture_stable'] = result['hashes_before']==result['hashes_after']
    result['client_errors'] = re.findall(r'\[(?:ERRO|FATL)\][^\r\n]*',client_log.read_text(errors='replace'))
    result['server_errors'] = re.findall(r'\[(?:ERRO|FATL)\][^\r\n]*|Exception occurred[^\r\n]*|runtime error[^\r\n]*',server_log.read_text(errors='replace'))
    result['observed_input_events'] = re.findall(r'native.ui.probe: (?:engine key|event)[^\r\n]*',client_log.read_text(errors='replace'))
    result['passed'] = all(result['checks'].values()) and not result.get('error') and not result['client_errors'] and not result['server_errors']
    (out/'command-dock-native-checks.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
    return 0 if result['passed'] else 1


if __name__=='__main__':
    raise SystemExit(main())
