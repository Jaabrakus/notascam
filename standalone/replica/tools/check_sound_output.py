#!/usr/bin/env python3
"""Real client: `src << 'P1.wav'` must play the sound and print nothing (BYOND)."""
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

def main():
    fixture=ROOT/'reference/fixtures/sound_output'
    hints=fixture/'layout.json';write_hints(fixture/'skin.dmf',hints)
    shot=REPORTS/'sound-output.png';shot.unlink(missing_ok=True)
    env=dict(os.environ,DOTNET_ReadyToRun='0',DM_SKIN_LAYOUT_HINTS=str(hints),DM_GAME_SNAPSHOT=str(shot),
             ROBUST_MODULE_ROBUST_CLIENT_WEBVIEW=str(RUNTIME/'webview-webkit'))
    dotnet=RUNTIME/'dotnet/dotnet';server_dir=RUNTIME/'server'
    subprocess.run([str(dotnet),str(RUNTIME/'compiler/DMCompiler.dll'),str(fixture/'sound_output.dme')],env=env,check=True,stdout=subprocess.DEVNULL)
    slp=REPORTS/'sound-output-server.log';clp=REPORTS/'sound-output-client.log'
    server=client=None
    try:
        with tempfile.TemporaryDirectory(prefix='dm-sound-') as data,slp.open('w') as sl,clp.open('w') as cl:
            server=subprocess.Popen([str(dotnet),str(server_dir/'Robust.Server.dll'),'--data-dir',data,
                '--cvar',f'opendream.json_path={fixture/"sound_output.json"}','--cvar','opendream.topic_port=25587',
                '--cvar','net.bindto=127.0.0.1','--cvar','net.port=12137','--cvar','auth.mode=0','--cvar','status.enabled=false',
                '--cvar','hub.advertise=false','--cvar','game.auto_pause_empty=false'],env=env,stdout=sl,stderr=subprocess.STDOUT)
            while ' -> Ready' not in slp.read_text(errors='replace'):time.sleep(.3)
            client_dir=RUNTIME/'client/Space Station 14.app/Contents/Resources'
            client=subprocess.Popen([str(dotnet),str(client_dir/'Robust.Client.dll'),'--mount-zip',str(server_dir/'Content.Client.zip'),
                '--connect','--connect-address','udp://127.0.0.1:12137','--username','SoundTest','--self-contained',
                '--cvar','web.headless=false','--cvar','discord.enabled=false'],cwd=client_dir,env=env,stdout=cl,stderr=subprocess.STDOUT)
            deadline=time.monotonic()+120
            while not shot.exists() and time.monotonic()<deadline:time.sleep(.5)
            time.sleep(1)
    finally:stop(client);stop(server)
    errors=re.findall(r'\[(?:ERRO|FATL)\][^\r\n]*',slp.read_text(errors='replace')+clp.read_text(errors='replace'))
    print('snapshot',shot.exists(),'sent','SOUND|sent' in slp.read_text(errors='replace'),'errors',errors[:5])
    print('\n'.join(l for l in clp.read_text(errors='replace').splitlines() if re.search(r'(?i)sound|audio|wav',l))[:2000])

if __name__=='__main__':main()
