#!/usr/bin/env python3
"""Connect two native clients, reboot the world, and verify automatic recovery."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
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
    arena=ROOT/'reference/lifecycle'
    shutil.copytree(ROOT/'reference/gameplay-opendream',arena,dirs_exist_ok=True)
    world=arena/'Code/World.dm'
    world.write_text(world.read_text(encoding='latin1').replace('ParityRun()','ClientParityRun()'),encoding='latin1')
    restart=(ROOT/'opendream/Code/Restart.dm').read_text(encoding='latin1')
    restart=restart.replace('\tvar/TRIES=0','\tX=4\n\tXX=16\n\tY=4\n\tYY=16\n\tvar/TRIES=0',1)
    restart=restart.replace('locate(rand(350,700),rand(400,750),1)','locate(10,10,1)')
    (arena/'Code/Restart.dm').write_text(restart,encoding='latin1')
    login=arena/'Code/Login.dm'
    login.write_text(login.read_text(encoding='latin1').replace('locate(rand(350,700),rand(400,750),1)',
                                                            'locate(10,10,1)'),encoding='latin1')
    shutil.copy2(ROOT/'reference/fixtures/lifecycle.dm',arena/'lifecycle.dm')
    fixture=arena/'lifecycle.dme'
    fixture.write_text((arena/'gameplay.dme').read_text().replace('#include "gameplay.dm"','#include "lifecycle.dm"'))
    (arena/'lifecycle-ready.txt').unlink(missing_ok=True)
    for folder in ('units','players'):
        for path in (arena/folder).glob('*'):path.unlink()
    ready=REPORTS/'lifecycle-server-ready.txt'
    ready.unlink(missing_ok=True)
    hints=REPORTS/'lifecycle-layout.json';write_hints(arena/'skin.dmf',hints)
    env=dict(os.environ,DOTNET_ReadyToRun='0',DM_SKIN_LAYOUT_HINTS=str(hints),
             ROBUST_MODULE_ROBUST_CLIENT_WEBVIEW=str(RUNTIME/'webview-webkit'),
             DM_LOCAL_SERVER_READY_FILE=str(ready),DM_LOCAL_SERVER_PORT='12127')
    dotnet=RUNTIME/'dotnet/dotnet'
    with (REPORTS/'lifecycle-compile.log').open('w') as log:
        subprocess.run([str(dotnet),str(RUNTIME/'compiler/DMCompiler.dll'),str(fixture)],
                       env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=90)
    clients=[];logs=[];server=None
    server_path=REPORTS/'lifecycle-server.log'
    result={}
    with tempfile.TemporaryDirectory(prefix='dm-lifecycle-') as data,server_path.open('w') as sl:
        try:
            command=[sys.executable,ROOT/'tools/server_supervisor.py','--ready-file',ready,'--',
                dotnet,args.server_dir/'Robust.Server.dll','--data-dir',data,
                '--cvar',f'opendream.json_path={fixture.with_suffix(".json")}',
                '--cvar','opendream.topic_port=25572','--cvar','net.bindto=127.0.0.1',
                '--cvar','net.port=12127','--cvar','net.max_connections=16','--cvar','auth.mode=0',
                '--cvar','status.enabled=false','--cvar','hub.advertise=false','--cvar','game.auto_pause_empty=false']
            server=subprocess.Popen([str(x) for x in command],env=env,stdout=sl,stderr=subprocess.STDOUT)
            deadline=time.monotonic()+60
            while time.monotonic()<deadline and server.poll() is None:
                if ready.exists():break
                time.sleep(.2)
            else:raise RuntimeError('Lifecycle server did not reach Ready')
            client_dir=RUNTIME/'client/Space Station 14.app/Contents/Resources'
            for name in ('FidelityAlpha','FidelityBeta'):
                log=(REPORTS/f'lifecycle-{name}.log').open('w');logs.append(log)
                snapshot=REPORTS/f'lifecycle-{name}.png';snapshot.unlink(missing_ok=True)
                client_env=dict(env,DM_TEST_RACE='Human',DM_GAME_SNAPSHOT=str(snapshot))
                clients.append(subprocess.Popen([str(dotnet),str(client_dir/'Robust.Client.dll'),
                    '--mount-zip',str(args.server_dir/'Content.Client.zip'),'--connect',
                    '--connect-address','udp://127.0.0.1:12127','--username',name,
                    '--self-contained','--cvar','web.headless=false', '--cvar', 'discord.enabled=false'],env=client_env,cwd=client_dir,
                    stdout=log,stderr=subprocess.STDOUT))
            deadline=time.monotonic()+180
            while time.monotonic()<deadline and server.poll() is None:
                output=server_path.read_text(errors='replace')
                if 'LIFECYCLE|failed' in output or '[ERRO]' in output or 'LIFECYCLE|complete' in output:break
                time.sleep(.25)
            output=server_path.read_text(errors='replace')
            observed=re.findall(r'LIFECYCLE\|[^\r\n]*',output)
            expected=['LIFECYCLE|connected|distinct=1|alpha_units=3|beta_units=3|alpha_selected=1|beta_selected=1|shared_units=0',
                      'LIFECYCLE|reboot_requested',
                      'LIFECYCLE|restored|alpha|units=3|owners=3|placed=3|selected=0|hp=111',
                      'LIFECYCLE|restored|beta|units=3|owners=3|placed=3|selected=0|hp=222',
                      'LIFECYCLE|complete']
            errors=re.findall(r'\[(?:ERRO|FATL)\][^\r\n]*',output)
            reconnects={name:'reconnecting to the rebooted local world' in (REPORTS/f'lifecycle-{name}.log').read_text(errors='replace')
                        for name in ('FidelityAlpha','FidelityBeta')}
            client_errors={name:re.findall(r'\[(?:ERRO|FATL)\][^\r\n]*',(REPORTS/f'lifecycle-{name}.log').read_text(errors='replace'))
                           for name in ('FidelityAlpha','FidelityBeta')}
            result=dict(passed=observed==expected and not errors and all(reconnects.values()) and not any(client_errors.values()),observations=observed,
                        expected=expected,server_errors=errors,automatic_reconnections=reconnects,
                        client_errors=client_errors,
                        runtime_sha256=hashlib.sha256((args.server_dir/'Resources/Assemblies/OpenDreamRuntime.dll').read_bytes()).hexdigest(),
                        substitutions=['Bounded grass arena; no world event loops','Original MultiKeyAllowed setting enabled for two same-computer clients',
                                       'Race chosen through real prompt with opt-in test automation'],
                        exclusions=['Does not compare multiplayer combat, chat or latency to an original two-client session.'])
        finally:
            for client in clients:stop(client)
            stop(server)
            for log in logs:log.close()
    (REPORTS/'lifecycle-checks.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
    if not result['passed']:raise SystemExit(1)

if __name__=='__main__':main()
