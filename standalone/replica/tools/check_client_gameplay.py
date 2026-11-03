#!/usr/bin/env python3
"""Exercise real login, race prompt, SaveUnits, server restart and LoadUnits."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time
from check_browser import stop
from skin_layout import write_hints

ROOT=Path(__file__).resolve().parents[1]
RUNTIME=ROOT/'runtime/macos-x64'
REPORTS=ROOT/'reports'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--server-dir',type=Path,default=RUNTIME/'server')
    args=parser.parse_args()
    arena=ROOT/'reference/client-gameplay'
    shutil.copytree(ROOT/'reference/gameplay-opendream',arena,dirs_exist_ok=True)
    world=arena/'Code/World.dm'
    world.write_text(world.read_text(encoding='latin1').replace('ParityRun()', 'ClientParityRun()'),encoding='latin1')
    restart=(ROOT/'opendream/Code/Restart.dm').read_text(encoding='latin1')
    restart=restart.replace('\tvar/TRIES=0','\tX=4\n\tXX=16\n\tY=4\n\tYY=16\n\tvar/TRIES=0',1)
    restart=restart.replace('locate(rand(350,700),rand(400,750),1)', 'locate(10,10,1)')
    (arena/'Code/Restart.dm').write_text(restart,encoding='latin1')
    login=arena/'Code/Login.dm'
    login.write_text(login.read_text(encoding='latin1').replace('locate(rand(350,700),rand(400,750),1)',
                                                            'locate(10,10,1)'),encoding='latin1')
    shutil.copy2(ROOT/'reference/fixtures/client_gameplay.dm',arena/'client_gameplay.dm')
    dme=(arena/'gameplay.dme').read_text().replace('#include "gameplay.dm"','#include "client_gameplay.dm"')
    fixture=arena/'client_gameplay.dme'
    fixture.write_text(dme)
    (arena/'client-reload-ready.txt').unlink(missing_ok=True)
    for folder in ('units','players'):
        for path in (arena/folder).glob('*'): path.unlink()
    hints=REPORTS/'client-gameplay-layout.json'
    write_hints(arena/'skin.dmf',hints)
    env=dict(os.environ,DOTNET_ReadyToRun='0',DM_SKIN_LAYOUT_HINTS=str(hints),
             ROBUST_MODULE_ROBUST_CLIENT_WEBVIEW=str(RUNTIME/'webview-webkit'))
    dotnet=RUNTIME/'dotnet/dotnet'
    with (REPORTS/'client-gameplay-compile.log').open('w') as log:
        subprocess.run([str(dotnet),str(RUNTIME/'compiler/DMCompiler.dll'),str(fixture)],
                       env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=90)
    results={}
    for phase in ('save','reload'):
        snapshot=REPORTS/f'client-gameplay-{phase}.png'
        snapshot.unlink(missing_ok=True)
        session_env=dict(env,DM_GAME_SNAPSHOT=str(snapshot))
        if phase=='save': session_env['DM_TEST_RACE']='Human'
        server=client=None
        server_path=REPORTS/f'client-gameplay-{phase}-server.log'
        client_path=REPORTS/f'client-gameplay-{phase}-client.log'
        with tempfile.TemporaryDirectory(prefix='dm-client-parity-') as data, server_path.open('w') as sl, client_path.open('w') as cl:
            try:
                server=subprocess.Popen([str(dotnet),str(args.server_dir/'Robust.Server.dll'),'--data-dir',data,
                    '--cvar',f'opendream.json_path={fixture.with_suffix(".json")}',
                    '--cvar','opendream.topic_port=25570','--cvar','net.bindto=127.0.0.1',
                    '--cvar','net.port=12125','--cvar','auth.mode=0','--cvar','status.enabled=false',
                    '--cvar','hub.advertise=false','--cvar','game.auto_pause_empty=false'],
                    env=session_env,stdout=sl,stderr=subprocess.STDOUT)
                deadline=time.monotonic()+60
                while time.monotonic()<deadline and server.poll() is None:
                    if ' -> Ready' in server_path.read_text(errors='replace'): break
                    time.sleep(.2)
                else: raise RuntimeError('Client gameplay server did not start')
                client_dir=RUNTIME/'client/Space Station 14.app/Contents/Resources'
                client=subprocess.Popen([str(dotnet),str(client_dir/'Robust.Client.dll'),
                    '--mount-zip',str(args.server_dir/'Content.Client.zip'),'--connect',
                    '--connect-address','udp://127.0.0.1:12125','--username','FidelitySave',
                    '--self-contained','--cvar','web.headless=false', '--cvar', 'discord.enabled=false'],env=session_env,cwd=client_dir,
                    stdout=cl,stderr=subprocess.STDOUT)
                deadline=time.monotonic()+100
                while time.monotonic()<deadline and client.poll() is None:
                    output=server_path.read_text(errors='replace')
                    if 'CLIENT_PARITY|failed' in output or '[ERRO]' in output: break
                    if ('CLIENT_PARITY|' in output and snapshot.exists() and
                        f'game framebuffer captured to {snapshot}' in client_path.read_text(errors='replace')): break
                    time.sleep(.25)
                output=server_path.read_text(errors='replace')
                client_output=client_path.read_text(errors='replace')
                results[phase]={'observations':re.findall(r'CLIENT_PARITY\|[^\r\n]*',output),
                    'server_errors':re.findall(r'\[(?:ERRO|FATL)\][^\r\n]*',output),
                    'invalid_macros':re.findall(r'Invalid keybind[^\r\n]*',client_output),
                    'race_prompt_used':'smoke test chose Human through the race prompt' in client_output,
                    'snapshot':snapshot.exists() and snapshot.read_bytes().endswith(bytes.fromhex('0000000049454e44ae426082'))}
            finally:
                stop(client)
                time.sleep(.5)
                stop(server)
        if results[phase]['server_errors'] or not results[phase]['observations'] or any(
                'CLIENT_PARITY|failed' in line for line in results[phase]['observations']): break
    expected='CLIENT_PARITY|reloaded|units=3|owners=3|placed=3|selected=0|equipped=9|hp=123|client=1|icons=3'
    results['passed']=expected in results.get('reload',{}).get('observations',[]) and all(
        not results[p]['server_errors'] and not results[p]['invalid_macros'] and results[p]['snapshot'] for p in ('save','reload'))
    (REPORTS/'client-gameplay-checks.json').write_text(json.dumps(results,indent=2)+'\n')
    print(json.dumps(results,indent=2))
    if not results['passed']: raise SystemExit(1)


if __name__=='__main__': main()
