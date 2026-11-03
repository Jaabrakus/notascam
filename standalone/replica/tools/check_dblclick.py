#!/usr/bin/env python3
"""Real client map clicks: Dream Seeker double-click pairing (same atom/button, 500 ms)."""
import argparse
import hashlib
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
    fixture=ROOT/'reference/fixtures/dblclick'
    shutil.copy2(ROOT/'opendream/skin.dmf',fixture/'skin.dmf')
    shutil.copy2(ROOT/'opendream/Icons/Cave.dmi',fixture/'Cave.dmi')
    (fixture/'dblclick.dme').write_text('#include "skin.dmf"\n#include "dblclick.dm"\n')
    hints=fixture/'layout.json';write_hints(fixture/'skin.dmf',hints)
    probe=REPORTS/'dblclick-probe';probe.mkdir(exist_ok=True)
    for name in ('state.json','action.json'):(probe/name).unlink(missing_ok=True)
    env=dict(os.environ,DOTNET_ReadyToRun='0',DM_NATIVE_UI_PROBE=str(probe),DM_SKIN_LAYOUT_HINTS=str(hints),
             ROBUST_MODULE_ROBUST_CLIENT_WEBVIEW=str(RUNTIME/'webview-webkit'))
    dotnet=RUNTIME/'dotnet/dotnet'
    with (REPORTS/'dblclick-compile.log').open('w') as log:
        subprocess.run([str(dotnet),str(RUNTIME/'compiler/DMCompiler.dll'),str(fixture/'dblclick.dme')],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
    report=dict(passed=False,exact_replica_verified=False,
        runtime_sha256=hashlib.sha256((args.server_dir/'Resources/Assemblies/OpenDreamRuntime.dll').read_bytes()).hexdigest(),
        expected_rule='Windows/Dream Seeker: second click on the same atom and button within 500 ms is a double-click (Click, DblClick, Click); a third click starts a new pair.',
        exclusions=['Synthetic SDL clicks 100 ms apart (fast) or ~1 s apart (slow); not physical input timing.',
                    'Clicks are released on the map control of the original skin; popup menus and right clicks are not exercised.',
                    'Each scenario is preceded by a click-free activation of the game window, so activation cannot consume or relocate a click.'])
    server=client=None
    slp=REPORTS/'dblclick-server.log';clp=REPORTS/'dblclick-client.log'
    def output():return slp.read_text(errors='replace')
    def events():return re.findall(r'DBL\|(?:click|dblclick)\|[^\r\n]*',output())
    def state():
        try:return json.loads((probe/'state.json').read_text())
        except (FileNotFoundError,json.JSONDecodeError):return {}
    def wait_for(fn,description,timeout=60):
        deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            value=fn()
            if value:return value
            if client and client.poll() is not None:raise RuntimeError('Client exited: '+description)
            time.sleep(.15)
        raise RuntimeError('Timed out: '+description)
    def clicks(window,x,y,count,pauses=0,x2=None,y2=None):
        action=dict(window=window['id'],kind=3,x=x/window['width'],y=y/window['height'],code=count,modifiers=pauses)
        if x2 is not None:action.update(x2=x2/window['width'],y2=y2/window['height'])
        path=probe/'action.json'
        path.with_suffix('.pending').write_text(json.dumps(action));path.with_suffix('.pending').replace(path)
        wait_for(lambda:not path.exists(),'clicks consumed')
        time.sleep(.25)
        wait_for(lambda:state().get('pendingEvents',1)==0,'clicks dispatched')
        time.sleep(1.5)  # longer than the pairing window, so scenarios stay independent
    try:
        with tempfile.TemporaryDirectory(prefix='dm-dblclick-') as data,slp.open('w') as sl,clp.open('w') as cl:
            server=subprocess.Popen([str(dotnet),str(args.server_dir/'Robust.Server.dll'),'--data-dir',data,
                '--cvar',f'opendream.json_path={fixture/"dblclick.json"}','--cvar','opendream.topic_port=25585',
                '--cvar','net.bindto=127.0.0.1','--cvar','net.port=12135','--cvar','auth.mode=0',
                '--cvar','status.enabled=false','--cvar','hub.advertise=false','--cvar','game.auto_pause_empty=false'],env=env,stdout=sl,stderr=subprocess.STDOUT)
            wait_for(lambda:' -> Ready' in output(),'server startup',60)
            client_dir=RUNTIME/'client/Space Station 14.app/Contents/Resources'
            client=subprocess.Popen([str(dotnet),str(client_dir/'Robust.Client.dll'),'--mount-zip',str(args.server_dir/'Content.Client.zip'),
                '--connect','--connect-address','udp://127.0.0.1:12135','--username','DoubleClickTest','--self-contained',
                '--cvar','web.headless=false','--cvar','discord.enabled=false'],cwd=client_dir,env=env,stdout=cl,stderr=subprocess.STDOUT)
            wait_for(lambda:'DBL|ready' in output(),'login')
            main=wait_for(lambda:next((w for w in state().get('windows',[]) if not w['prompt'] and w.get('viewports')),None),'map viewport')
            time.sleep(2)
            main=next(w for w in state()['windows'] if w['id']==main['id'])
            view=max(main['viewports'],key=lambda v:v['rect']['width']*v['rect']['height'])['rect']
            tile=min(view['width'],view['height'])/19
            cx,cy=view['x']+view['width']/2,view['y']+view['height']/2
            report['viewport']=view
            scenarios=[('fast_double',dict(count=2),['click|13,13','dblclick|13,13','click|13,13']),
                       ('slow_pair',dict(count=2,pauses=9),['click|13,13','click|13,13']),
                       ('moved_pair',dict(count=2,x2=cx+tile,y2=cy),['click|13,13','click|14,13']),
                       ('triple',dict(count=3),['click|13,13','dblclick|13,13','click|13,13','click|13,13'])]
            report['scenarios']=[]
            for name,options,expected in scenarios:
                # Activating a window that lost focus can consume a click or report
                # the real pointer; activate first (no clicks), then click.
                clicks(main,cx,cy,0)
                before=len(events())
                clicks(main,cx,cy,**options)
                actual=[e[len('DBL|'):] for e in events()[before:]]
                report['scenarios'].append(dict(name=name,expected=expected,actual=actual,matches=actual==expected))
            report['passed']=all(s['matches'] for s in report['scenarios'])
    except Exception as error:report['error']=repr(error)
    finally:stop(client);stop(server)
    report['client_errors']=re.findall(r'\[(?:ERRO|FATL)\][^\r\n]*',clp.read_text(errors='replace')) if clp.exists() else []
    report['server_errors']=re.findall(r'\[(?:ERRO|FATL)\][^\r\n]*',slp.read_text(errors='replace')) if slp.exists() else []
    report['passed']=report['passed'] and not report['client_errors'] and not report['server_errors']
    (REPORTS/'dblclick-checks.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    if not report['passed']:raise SystemExit(1)


if __name__=='__main__':main()
