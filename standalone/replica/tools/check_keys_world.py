#!/usr/bin/env python3
"""Full game + real client: physical-route (AppKit) arrow keys and typing in Rename."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time
from check_browser import stop
from skin_layout import write_hints

ROOT=Path(__file__).resolve().parents[1]
RUNTIME=ROOT/'runtime/macos-x64'
REPORTS=ROOT/'reports'
NUMPAD_FUNCTION=0x200000|0x800000  # NSEvent .numericPad | .function, as macOS sets for arrows
ARROWS={'up':(126,''),'down':(125,''),'left':(123,''),'right':(124,'')}
LETTERS={'a':0,'s':1,'d':2,'f':3,'h':4,'g':5,'z':6,'x':7,'c':8,'v':9,'b':11,'q':12,'w':13,'e':14,'r':15,'y':16,'t':17,
         'o':31,'u':32,'i':34,'p':35,'l':37,'j':38,'k':40,'n':45,'m':46}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--server-dir',type=Path,default=RUNTIME/'server')
    parser.add_argument('--world',type=Path,default=ROOT/'reference/keys-world')
    args=parser.parse_args()
    world=args.world.resolve()
    (world/'keys-rename.txt').unlink(missing_ok=True)
    hints=REPORTS/'keys-world-layout.json';write_hints(world/'skin.dmf',hints)
    probe=REPORTS/'keys-probe';probe.mkdir(exist_ok=True)
    for name in ('state.json','action.json'):(probe/name).unlink(missing_ok=True)
    env=dict(os.environ,DOTNET_ReadyToRun='0',DM_SKIN_LAYOUT_HINTS=str(hints),DM_TEST_RACE='Orc',DM_NATIVE_UI_PROBE=str(probe),
             DM_GAME_SNAPSHOT=str(REPORTS/'keys-world.png'),ROBUST_MODULE_ROBUST_CLIENT_WEBVIEW=str(RUNTIME/'webview-webkit'))
    dotnet=RUNTIME/'dotnet/dotnet'
    slp=REPORTS/'keys-world-server.log';clp=REPORTS/'keys-world-client.log'
    errorlog=world/'ErrorLog.txt';errorlog.unlink(missing_ok=True)
    report=dict(passed=False,input_route='AppKit NSEvents posted to the game window (first-responder routing), not SDL injection',steps=[])
    server=client=None
    def observations():return re.findall(r'KEYS\|[^\r\n]*',errorlog.read_text(errors='replace')) if errorlog.exists() else []
    def state():
        try:return json.loads((probe/'state.json').read_text())
        except (FileNotFoundError,json.JSONDecodeError):return {}
    def wait_for(fn,description,timeout=60):
        deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            value=fn()
            if value:return value
            if client and client.poll() is not None:raise RuntimeError('Client exited: '+description)
            time.sleep(.2)
        raise RuntimeError('Timed out: '+description)
    def act(window,**action):
        path=probe/'action.json'
        payload=dict(window=window['id'],x=0,y=0,code=0,modifiers=0,text='');payload.update(action)
        path.with_suffix('.pending').write_text(json.dumps(payload))
        path.with_suffix('.pending').replace(path)
        wait_for(lambda:not path.exists(),'action consumed')
        time.sleep(.6)
    def main_window():return next(w for w in state()['windows'] if not w['prompt'] and w.get('viewports'))
    def step(name,before):
        current=main_window()
        report['steps'].append(dict(name=name,responder=current.get('responder'),new_observations=observations()[before:]))
    def arrows(window,keys):
        for key in keys:
            code,text=ARROWS[key];act(window,kind=4,code=code,text=text,modifiers=NUMPAD_FUNCTION);time.sleep(.3)
    try:
        with tempfile.TemporaryDirectory(prefix='dm-keys-') as data,slp.open('w') as sl,clp.open('w') as cl:
            server=subprocess.Popen([str(dotnet),str(args.server_dir/'Robust.Server.dll'),'--data-dir',data,
                '--cvar',f'opendream.json_path={world/"Cave Crawlers.json"}','--cvar','opendream.topic_port=25589',
                '--cvar','net.bindto=127.0.0.1','--cvar','net.port=12139','--cvar','auth.mode=0','--cvar','status.enabled=false',
                '--cvar','hub.advertise=false','--cvar','game.auto_pause_empty=false'],env=env,stdout=sl,stderr=subprocess.STDOUT,cwd=world)
            wait_for(lambda:' -> Ready' in slp.read_text(errors='replace'),'server startup',240)
            client_dir=RUNTIME/'client/Space Station 14.app/Contents/Resources'
            client=subprocess.Popen([str(dotnet),str(client_dir/'Robust.Client.dll'),'--mount-zip',str(args.server_dir/'Content.Client.zip'),
                '--connect','--connect-address','udp://127.0.0.1:12139','--username','KeysTest','--self-contained',
                '--cvar','web.headless=false','--cvar','discord.enabled=false'],cwd=client_dir,env=env,stdout=cl,stderr=subprocess.STDOUT)
            wait_for(lambda:any(o.startswith('KEYS|ready') for o in observations()),'army and observer ready',240)
            time.sleep(2)
            window=main_window()
            report['initial_responder']=window.get('responder')
            view=max(window['viewports'],key=lambda v:v['rect']['width']*v['rect']['height'])['rect']
            mx=(view['x']+view['width']*0.25)/window['width'];my=(view['y']+view['height']*0.25)/window['height']
            before=len(observations())
            act(window,kind=5,x=mx,y=my)
            arrows(window,['up','up','right','right'])
            step('map_click_then_arrows',before)
            browser=[s for s in window.get('scrolls',[])]
            before=len(observations())
            act(window,kind=5,x=0.75,y=0.25)   # inside the right-hand browser panel
            step('click_browser_panel',before)
            before=len(observations())
            act(window,kind=5,x=mx,y=my)
            arrows(window,['down','left'])
            step('back_to_map_then_arrows',before)
            (world/'keys-rename.txt').write_text('go')
            prompt=wait_for(lambda:next((w for w in state().get('windows',[]) if w['title']=='Rename'),None),'Rename prompt')
            time.sleep(1)
            report['rename_prompt_responder']=prompt.get('responder')
            report['rename_prompt_text_box']=next((w for w in state().get('windows',[]) if w['title']=='Rename'),{}).get('lineEdits')
            before=len(observations())
            for letter in 'grok':
                act(prompt,kind=4,code=LETTERS[letter],text=letter)
            act(prompt,kind=4,code=36,text='\r')
            wait_for(lambda:any(o.startswith('KEYS|renamed|') for o in observations()),'rename result',30)
            report['steps'].append(dict(name='type_grok_return',new_observations=observations()[before:]))
    except Exception as error:report['error']=repr(error)
    finally:stop(client);stop(server)
    obs=observations();report['observations']=obs
    moves=lambda name:[o for s in report['steps'] if s['name']==name for o in s['new_observations'] if o.startswith('KEYS|move|')]
    renamed=next((o for o in obs if o.startswith('KEYS|renamed|')),'')
    report['checks']=dict(arrows_after_map_click=len(moves('map_click_then_arrows'))==4,
                          arrows_after_browser_then_map=len(moves('back_to_map_then_arrows'))==2,
                          typed_name_reached_rename=renamed.endswith('Grok'))
    report['passed']=all(report['checks'].values()) and 'error' not in report
    (REPORTS/'keys-world-checks.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    if not report['passed']:raise SystemExit(1)


if __name__=='__main__':main()
