#!/usr/bin/env python3
"""Craft through the real client: original Carpentry prompts answered by clicking rows and Ok."""
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
    arena=ROOT/'reference/client-crafting'
    shutil.copytree(ROOT/'reference/gameplay-opendream',arena,dirs_exist_ok=True)
    world=arena/'Code/World.dm'
    world.write_text(world.read_text(encoding='latin1').replace('ParityRun()','ClientCraftRun()'),encoding='latin1')
    restart=(ROOT/'opendream/Code/Restart.dm').read_text(encoding='latin1')
    restart=restart.replace('\tvar/TRIES=0','\tX=4\n\tXX=16\n\tY=4\n\tYY=16\n\tvar/TRIES=0',1)
    restart=restart.replace('locate(rand(350,700),rand(400,750),1)','locate(10,10,1)')
    (arena/'Code/Restart.dm').write_text(restart,encoding='latin1')
    login=arena/'Code/Login.dm'
    login.write_text(login.read_text(encoding='latin1').replace('locate(rand(350,700),rand(400,750),1)','locate(10,10,1)'),encoding='latin1')
    shutil.copy2(ROOT/'reference/fixtures/client_crafting.dm',arena/'client_crafting.dm')
    fixture=arena/'client_crafting.dme'
    fixture.write_text((arena/'gameplay.dme').read_text().replace('#include "gameplay.dm"','#include "client_crafting.dm"'))
    for folder in ('units','players'):
        for path in (arena/folder).glob('*'):path.unlink()
    hints=REPORTS/'client-crafting-layout.json';write_hints(arena/'skin.dmf',hints)
    probe=REPORTS/'client-crafting-probe';probe.mkdir(exist_ok=True)
    for name in ('state.json','action.json'):(probe/name).unlink(missing_ok=True)
    env=dict(os.environ,DOTNET_ReadyToRun='0',DM_SKIN_LAYOUT_HINTS=str(hints),DM_TEST_RACE='Human',DM_NATIVE_UI_PROBE=str(probe),
             DM_GAME_SNAPSHOT=str(REPORTS/'client-crafting.png'),  # also paces the race automation
             ROBUST_MODULE_ROBUST_CLIENT_WEBVIEW=str(RUNTIME/'webview-webkit'))
    dotnet=RUNTIME/'dotnet/dotnet'
    with (REPORTS/'client-crafting-compile.log').open('w') as log:
        subprocess.run([str(dotnet),str(RUNTIME/'compiler/DMCompiler.dll'),str(fixture)],env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=120)
    report=dict(passed=False,exact_replica_verified=False,recipe='Carpentry > Craft > Wooden Door',
        input_path='Original DblClick() list prompts -> real client ListPrompt -> injected row click and Ok -> server',
        exclusions=['The workshop DblClick() is invoked server-side for the selected unit; map double-click targeting is not exercised here.',
                    'Synthetic SDL clicks, not physical input timing. A misclicked row is corrected from the highlight (see clicks).','One recipe; recipe outcomes for every workshop/race are in crafting and crafting_races parity.'])
    server=client=None
    slp=REPORTS/'client-crafting-server.log';clp=REPORTS/'client-crafting-client.log'
    def output():return slp.read_text(errors='replace')
    def wait_for(fn,description,timeout=60):
        deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            value=fn()
            if value:return value
            if client and client.poll() is not None:raise RuntimeError('Client exited: '+description)
            if 'CLIENT_CRAFT|failed' in output() or '[ERRO]' in output():raise RuntimeError('Server error: '+description)
            time.sleep(.15)
        raise RuntimeError('Timed out: '+description)
    def state():
        try:return json.loads((probe/'state.json').read_text())
        except (FileNotFoundError,json.JSONDecodeError):return {}
    def action(window,x,y):
        path=probe/'action.json'
        path.with_suffix('.pending').write_text(json.dumps(dict(window=window['id'],kind=0,x=x/window['width'],y=y/window['height'],code=0,modifiers=0)))
        path.with_suffix('.pending').replace(path)
        wait_for(lambda:not path.exists(),'native event consumed')
        time.sleep(.25)
        wait_for(lambda:state().get('pendingEvents',1)==0,'native event queue drained')
        time.sleep(.4)
    def prompt_with(item):
        for window in state().get('windows',[]):
            for listing in window.get('lists',[]):
                for entry in listing['items']:
                    if entry['text']==item and entry['rect']:return window
    def choose(item):
        window=wait_for(lambda:prompt_with(item),f'list prompt offering {item}')
        time.sleep(.5)
        window=prompt_with(item)
        row=next(e for l in window['lists'] for e in l['items'] if e['text']==item)
        listing=next(l for l in window['lists'] if any(e is row for e in l['items']))
        step=dict(item=item,title=window['title'],offered=[e['text'] for l in window['lists'] for e in l['items']],
                  window_size=[window['width'],window['height']],list_rect=listing['rect'],row_rect=row['rect'])
        # A player clicks the entry they want (the prompt pre-selects the first) and
        # corrects a misclick from the highlight; retries are recorded.
        step['clicks']=[]
        current=window
        for attempt in range(3):
            row=next(e for l in current['lists'] for e in l['items'] if e['text']==item)
            if row['selected']:break
            before=[l.get('scroll') for l in current['lists']]
            action(current,row['rect']['x']+row['rect']['width']/2,row['rect']['y']+row['rect']['height']/2)
            snapshot=state()
            current=next((w for w in snapshot.get('windows',[]) if w['id']==window['id']),current)
            step['clicks'].append(dict(row_rect=row['rect'],scroll_before=before,scroll_after=[l.get('scroll') for l in current.get('lists',[])],
                mouse=snapshot.get('mouse'),selected=[e['text'] for l in current.get('lists',[]) for e in l['items'] if e['selected']]))
        step['selected_after_click']=[e['text'] for l in current.get('lists',[]) for e in l['items'] if e['selected']]
        ok=next(b for b in current['buttons'] if b['text']=='Ok')
        action(current,ok['rect']['x']+ok['rect']['width']/2,ok['rect']['y']+ok['rect']['height']/2)
        wait_for(lambda:not any(w['id']==window['id'] for w in state().get('windows',[])),f'{item} prompt closed')
        report['steps'].append(step)
    try:
        with tempfile.TemporaryDirectory(prefix='dm-client-craft-') as data,slp.open('w') as sl,clp.open('w') as cl:
            server=subprocess.Popen([str(dotnet),str(args.server_dir/'Robust.Server.dll'),'--data-dir',data,
                '--cvar',f'opendream.json_path={fixture.with_suffix(".json")}','--cvar','opendream.topic_port=25581',
                '--cvar','net.bindto=127.0.0.1','--cvar','net.port=12131','--cvar','auth.mode=0','--cvar','status.enabled=false',
                '--cvar','hub.advertise=false','--cvar','game.auto_pause_empty=false'],env=env,stdout=sl,stderr=subprocess.STDOUT)
            wait_for(lambda:' -> Ready' in output(),'server startup',90)
            client_dir=RUNTIME/'client/Space Station 14.app/Contents/Resources'
            client=subprocess.Popen([str(dotnet),str(client_dir/'Robust.Client.dll'),'--mount-zip',str(args.server_dir/'Content.Client.zip'),
                '--connect','--connect-address','udp://127.0.0.1:12131','--username','CraftingTest','--self-contained',
                '--cvar','web.headless=false','--cvar','discord.enabled=false'],cwd=client_dir,env=env,stdout=cl,stderr=subprocess.STDOUT)
            report['steps']=[]
            wait_for(lambda:'CLIENT_CRAFT|ready|' in output(),'three Human units and a workbench',150)
            choose('Craft')
            choose('Wooden Door')
            wait_for(lambda:'CLIENT_CRAFT|result|' in output(),'crafting result')
            report['observations']=re.findall(r'CLIENT_CRAFT\|[^\r\n]*',output())
            ready=next(o for o in report['observations'] if o.startswith('CLIENT_CRAFT|ready|'))
            result=next(o for o in report['observations'] if o.startswith('CLIENT_CRAFT|result|'))
            report['passed']=(ready=='CLIENT_CRAFT|ready|selected=1|wood=1|skill=25|adjacent=1' and
                re.fullmatch(r'CLIENT_CRAFT\|result\|products=/obj/Items/Furniture/Doors/WoodenDoor:[^;]*;\|wood=0\|skill=25\.5\|unit_moved=0,0',result) is not None and
                [s['selected_after_click'] for s in report['steps']]==[['Craft'],['Wooden Door']])
    except Exception as error:report['error']=repr(error)
    finally:stop(client);stop(server)
    report['client_errors']=re.findall(r'\[(?:ERRO|FATL)\][^\r\n]*',clp.read_text(errors='replace')) if clp.exists() else []
    report['server_errors']=re.findall(r'\[(?:ERRO|FATL)\][^\r\n]*',slp.read_text(errors='replace')) if slp.exists() else []
    report['passed']=report['passed'] and not report['client_errors'] and not report['server_errors']
    (REPORTS/'client-crafting-checks.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    if not report['passed']:raise SystemExit(1)


if __name__=='__main__':main()
