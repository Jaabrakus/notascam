#!/usr/bin/env python3
"""Full world + real client: log every move/turn of a fresh, idle player army."""
import argparse
import json
import os
from pathlib import Path
import re
import tempfile
import time
from check_browser import stop
from skin_layout import write_hints
import subprocess

ROOT=Path(__file__).resolve().parents[1]
RUNTIME=ROOT/'runtime/macos-x64'
REPORTS=ROOT/'reports'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--server-dir',type=Path,default=RUNTIME/'server')
    parser.add_argument('--world',type=Path,default=ROOT/'reference/idle-world')
    parser.add_argument('--race',default='Human')
    args=parser.parse_args()
    world=args.world.resolve()
    hints=REPORTS/'idle-world-layout.json';write_hints(world/'skin.dmf',hints)
    env=dict(os.environ,DOTNET_ReadyToRun='0',DM_SKIN_LAYOUT_HINTS=str(hints),DM_TEST_RACE=args.race,
             DM_GAME_SNAPSHOT=str(REPORTS/'idle-world.png'),ROBUST_MODULE_ROBUST_CLIENT_WEBVIEW=str(RUNTIME/'webview-webkit'))
    dotnet=RUNTIME/'dotnet/dotnet'
    slp=REPORTS/'idle-world-server.log';clp=REPORTS/'idle-world-client.log'
    server=client=None
    report=dict(race=args.race,passed=False)
    try:
        with tempfile.TemporaryDirectory(prefix='dm-idle-world-') as data,slp.open('w') as sl,clp.open('w') as cl:
            server=subprocess.Popen([str(dotnet),str(args.server_dir/'Robust.Server.dll'),'--data-dir',data,
                '--cvar',f'opendream.json_path={world/"Cave Crawlers.json"}','--cvar','opendream.topic_port=25583',
                '--cvar','net.bindto=127.0.0.1','--cvar','net.port=12133','--cvar','auth.mode=0','--cvar','status.enabled=false',
                '--cvar','hub.advertise=false','--cvar','game.auto_pause_empty=false'],env=env,stdout=sl,stderr=subprocess.STDOUT,cwd=world)
            deadline=time.monotonic()+240
            while ' -> Ready' not in slp.read_text(errors='replace'):
                if time.monotonic()>deadline or server.poll() is not None:raise RuntimeError('server did not start')
                time.sleep(.5)
            client_dir=RUNTIME/'client/Space Station 14.app/Contents/Resources'
            client=subprocess.Popen([str(dotnet),str(client_dir/'Robust.Client.dll'),'--mount-zip',str(args.server_dir/'Content.Client.zip'),
                '--connect','--connect-address','udp://127.0.0.1:12133','--username','IdleTest','--self-contained',
                '--cvar','web.headless=false','--cvar','discord.enabled=false'],cwd=client_dir,env=env,stdout=cl,stderr=subprocess.STDOUT)
            deadline=time.monotonic()+300
            while 'IDLE_PROBE|done' not in slp.read_text(errors='replace'):
                if time.monotonic()>deadline:raise RuntimeError('probe did not finish')
                if client.poll() is not None:raise RuntimeError('client exited')
                time.sleep(1)
    except Exception as error:report['error']=repr(error)
    finally:stop(client);stop(server)
    text=slp.read_text(errors='replace')
    report['observations']=re.findall(r'IDLE_PROBE\|[^\r\n]*',text)
    report['runtime_errors']=len(re.findall(r'\[ERRO\]',text))
    done=[o for o in report['observations'] if o.startswith('IDLE_PROBE|done|')]
    report['passed']=done==['IDLE_PROBE|done|changes=0']
    (REPORTS/'idle-world-checks.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    if not report['passed']:raise SystemExit(1)


if __name__=='__main__':main()
