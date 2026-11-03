#!/usr/bin/env python3
"""Exercise real prompt layout and SDL mouse/key dispatch, without saves."""
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
    report=dict(passed=False,client_package_sha256=hashlib.sha256((args.server_dir/'Content.Client.zip').read_bytes()).hexdigest(),
        webview_sha256=hashlib.sha256((RUNTIME/'webview-webkit/Robust.Client.WebView.dll').read_bytes()).hexdigest(),
        input_path='Injected SDL event -> client input/UI -> original DMF macro -> server',
        exact_replica_verified=False,exclusions=['Synthetic SDL events, not a human physical-input or BYOND timing comparison.',
            'Bounded prompt and macro fixture; full-world gameplay and exact original font metrics remain open.'])
    probe=REPORTS/'native-ui-probe'
    probe.mkdir(exist_ok=True)
    for name in ('state.json','action.json'):(probe/name).unlink(missing_ok=True)
    for path in probe.glob('prompt-*.png'):path.unlink()
    source=(ROOT/'source/Code/Restart.dm').read_text(encoding='latin1')
    orc=re.search(r'if\("Orc"\) alert\(src,"(.*?)"\)',source).group(1).replace('[WorldName]','the test world')
    messages=[('Orc introduction',orc),('Three choices','Choose a response.'),
              ('Long message',' '.join(['The entire message must remain reachable while every response button stays visible.']*100)),
              ('Literal text','Literal [color=red]brackets[/color], <b>tags</b> and a second line.\nEnd of message.')]
    def dm(s):return '"'+s.replace('\\','\\\\').replace('"','\\"').replace('[','\\[').replace('\n','\\n')+'"'
    fixture=ROOT/'reference/fixtures/native_ui'
    fixture.mkdir(exist_ok=True)
    shutil.copy2(ROOT/'opendream/skin.dmf',fixture/'skin.dmf')
    (fixture/'native_ui.dme').write_text('#include "skin.dmf"\n#include "native_ui.dm"\n')
    code='''world
    name = "Native UI verification"
    maxx = 30
    maxy = 30
    maxz = 1
    fps = 10
mob
    Login()
        loc = locate(15,15,1)
        sleep(5)
'''
    for title,message in messages:
        buttons=', "First", "Second", "Third"' if title=='Three choices' else ', "Ok"'
        code+='        world.log << "NATIVE_UI|'+title+'|[alert(src, '+dm(message)+', '+dm(title)+buttons+')]"\n'
    code+='''        var/race = input(src, "Select a race", "Race list", "Orc") as null|anything in list("Human", "Orc", "Dwarf")
        world.log << "NATIVE_UI|Race list|[race]"
        var/text = input(src, "Keep this value", "Text entry", "kept") as text
        world.log << "NATIVE_UI|Text entry|[text]"
        var/number = input(src, "Keep this number", "Number entry", 42) as num
        world.log << "NATIVE_UI|Number entry|[number]"
        world.log << "NATIVE_UI|ready"
    Move(NewLoc, Dir)
        . = ..()
        world.log << "NATIVE_UI|move|[Dir]|[x],[y],[z]"
    verb/Quick(N as num, Mode as text)
        world.log << "NATIVE_UI|quick|[N]|[Mode]"
'''
    (fixture/'native_ui.dm').write_text(code)
    hints=fixture/'layout.json';write_hints(fixture/'skin.dmf',hints)
    env=dict(os.environ,DOTNET_ReadyToRun='0',DM_NATIVE_UI_PROBE=str(probe),DM_SKIN_LAYOUT_HINTS=str(hints),
        ROBUST_MODULE_ROBUST_CLIENT_WEBVIEW=str(RUNTIME/'webview-webkit'))
    dotnet=RUNTIME/'dotnet/dotnet'
    with (REPORTS/'native-ui-compile.log').open('w') as log:
        subprocess.run([str(dotnet),str(RUNTIME/'compiler/DMCompiler.dll'),str(fixture/'native_ui.dme')],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
    server=client=None
    slp=REPORTS/'native-ui-server.log';clp=REPORTS/'native-ui-client.log'
    def wait_for(fn,description,timeout=25):
        deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            value=fn()
            if value:return value
            if client and client.poll() is not None:raise RuntimeError('Client exited: '+description)
            time.sleep(.15)
        raise RuntimeError('Timed out: '+description)
    def state():
        try:return json.loads((probe/'state.json').read_text())['windows']
        except (FileNotFoundError,json.JSONDecodeError):return []
    def action(window,kind=0,x=0,y=0,code=0,modifiers=0):
        if kind==0:x,y=x/window['width'],y/window['height']
        path=probe/'action.json'
        path.with_suffix('.pending').write_text(json.dumps(dict(window=window['id'],kind=kind,x=x,y=y,code=code,modifiers=modifiers)))
        path.with_suffix('.pending').replace(path)
        wait_for(lambda:not path.exists(),'native event consumed')
        time.sleep(.25)  # State is published before the action is queued.
        wait_for(lambda:json.loads((probe/'state.json').read_text()).get('pendingEvents',0)==0,'native event queue drained')
        time.sleep(.4)
    def click(window,button):
        rect=next(b['rect'] for b in window['buttons'] if b['text']==button)
        action(window,x=rect['x']+rect['width']/2,y=rect['y']+rect['height']/2)
    def output():return slp.read_text(errors='replace')
    def fits(rect,window):return rect['x']>=0 and rect['y']>=0 and rect['width']>0 and rect['height']>0 and rect['x']+rect['width']<=window['width']+1 and rect['y']+rect['height']<=window['height']+1
    try:
        with tempfile.TemporaryDirectory(prefix='dm-native-ui-') as data,slp.open('w') as sl,clp.open('w') as cl:
            server=subprocess.Popen([str(dotnet),str(args.server_dir/'Robust.Server.dll'),'--data-dir',data,
                '--cvar',f'opendream.json_path={fixture/"native_ui.json"}','--cvar','opendream.topic_port=25579',
                '--cvar','net.bindto=127.0.0.1','--cvar','net.port=12130','--cvar','auth.mode=0',
                '--cvar','status.enabled=false','--cvar','hub.advertise=false','--cvar','game.auto_pause_empty=false'],env=env,stdout=sl,stderr=subprocess.STDOUT)
            wait_for(lambda:' -> Ready' in output(),'server startup',60)
            client_dir=RUNTIME/'client/Space Station 14.app/Contents/Resources'
            client=subprocess.Popen([str(dotnet),str(client_dir/'Robust.Client.dll'),'--mount-zip',str(args.server_dir/'Content.Client.zip'),
                '--connect','--connect-address','udp://127.0.0.1:12130','--username','NativeUiTest','--self-contained',
                '--cvar','web.headless=false','--cvar','discord.enabled=false'],cwd=client_dir,env=env,stdout=cl,stderr=subprocess.STDOUT)
            report['dialogs']=[]
            for title,message in messages+[('Race list',None),('Text entry',None),('Number entry',None)]:
                window=wait_for(lambda:next((w for w in state() if w['title']==title and w['buttons']),None),title,60)
                # Let measurement and painting settle before retaining bounds.
                time.sleep(.5)
                window=next(w for w in state() if w['title']==title)
                entry=dict(title=title,window=window,
                    bounded=window['width']/window['scale']<=520 and window['height']/window['scale']<=650,
                    buttons_visible=all(fits(b['rect'],window) for b in window['buttons']))
                if message is not None:entry['literal_text_preserved']=any(m['text']==message for m in window['messages'])
                if title=='Orc introduction':entry['wrapped']=window['messages'][0]['rect']['height']/window['scale']>30
                if title=='Long message':entry['scrollable']=window['messages'][0]['rect']['height']>window['scrolls'][0]['rect']['height']
                report['dialogs'].append(entry)
                click(window,'Third' if title=='Three choices' else 'Ok')
                wait_for(lambda:'NATIVE_UI|'+title+'|' in output(),'response from '+title)
                expected={'Three choices':'Third','Race list':'Orc','Text entry':'kept','Number entry':'42'}.get(title,'Ok')
                entry['correct_response']=f'NATIVE_UI|{title}|{expected}' in output()
            wait_for(lambda:'NATIVE_UI|ready' in output(),'prompt completion')
            main=next(w for w in state() if not w['prompt'] and w['width']>500)
            action(main,x=100,y=100)
            report['movement']=[]
            # SDL scancodes: up, right, down, left.
            for key,direction in [(82,1),(79,4),(81,2),(80,8),(75,5),(78,6),(77,10),(74,9)]:
                before=output().count('NATIVE_UI|move|')
                action(main,kind=1,code=key)
                wait_for(lambda:output().count('NATIVE_UI|move|')>before,'movement key '+str(key))
                report['movement'].append(dict(key=key,expected_direction=direction,events=re.findall(r'NATIVE_UI\|move\|[^\r\n]*',output())[before:]))
            time.sleep(.5)
            stopped=output().count('NATIVE_UI|move|')
            time.sleep(.7)
            report['movement_stops_after_release']=output().count('NATIVE_UI|move|')==stopped
            report['groups']=[]
            for number in range(1,10):
                for mode,mods in [('Select',0x100),('Set',0x100|0x40),('Add',0x100|1)]:
                    action(main,kind=1,code=29+number,modifiers=mods)
                    expected=f'NATIVE_UI|quick|{number}|{mode}'
                    wait_for(lambda:expected in output(),f'group {number} {mode}')
                    report['groups'].append(expected)
            report['resizes']=[]
            for width,height in [(420,450),(900,600),(1280,720)]:
                action(main,kind=2,x=width,y=height)
                current=wait_for(lambda:next((w for w in state() if w['id']==main['id'] and w['width']==width and w['height']==height),None),'window resize')
                info=next((b for b in current['buttons'] if b['text']=='Info'),None)
                if info and fits(info['rect'],current):click(current,'Info')
                time.sleep(.5)
                report['resizes'].append(dict(width=width,height=height,completed=True))
            report['observations']=re.findall(r'NATIVE_UI\|[^\r\n]*',output())
            report['passed']=report['movement_stops_after_release'] and len(report['groups'])==27 and all(d['bounded'] and d['buttons_visible'] and d['correct_response'] and d.get('literal_text_preserved',True) and d.get('wrapped',True) and d.get('scrollable',True) for d in report['dialogs']) and all(
                any(f'|move|{m["expected_direction"]}|' in event for event in m['events']) for m in report['movement'])
    except Exception as error:report['error']=repr(error)
    finally:stop(client);stop(server)
    report['client_errors']=re.findall(r'\[(?:ERRO|FATL)\][^\r\n]*',clp.read_text(errors='replace')) if clp.exists() else []
    report['server_errors']=re.findall(r'\[(?:ERRO|FATL)\][^\r\n]*',slp.read_text(errors='replace')) if slp.exists() else []
    report['passed']=report['passed'] and not report['client_errors'] and not report['server_errors']
    (REPORTS/'native-ui-checks.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    if not report['passed']:raise SystemExit(1)

if __name__=='__main__':main()
