#!/usr/bin/env python3
"""Full Remastered game + real client: run every Actions-tab row and check effects/errors."""
import json, os, re, shutil, subprocess, sys, tempfile, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
REPLICA = ROOT.parent/'replica'; RUNTIME = REPLICA/'runtime/macos-x64'
sys.path.insert(0, str(REPLICA/'tools'))
from check_browser import stop  # noqa: E402
from skin_layout import write_hints  # noqa: E402

def client_copy():
    target = ROOT/'tests/client'
    if not target.exists():
        shutil.copytree(RUNTIME/'client', target, ignore=shutil.ignore_patterns('user_data', '.DS_Store'))
    return target/'Space Station 14.app/Contents/Resources'


def main():
    world = ROOT/'tests/actions-world'
    (world/'ErrorLog.txt').unlink(missing_ok=True)
    hints = ROOT/'tests/actions-layout.json'; write_hints(world/'skin.dmf', hints)
    env = dict(os.environ, DOTNET_ReadyToRun='0', DM_SKIN_LAYOUT_HINTS=str(hints), DM_TEST_RACE='Dwarf',
               DM_GAME_SNAPSHOT=str(ROOT/'tests/actions.png'), ROBUST_MODULE_ROBUST_CLIENT_WEBVIEW=str(RUNTIME/'webview-webkit'))
    dotnet = RUNTIME/'dotnet/dotnet'; slp = ROOT/'tests/actions-server.log'; clp = ROOT/'tests/actions-client.log'
    server = client = None
    try:
        with tempfile.TemporaryDirectory(prefix='dm-actions-') as data, slp.open('w') as sl, clp.open('w') as cl:
            server = subprocess.Popen([str(dotnet), str(RUNTIME/'server/Robust.Server.dll'), '--data-dir', data,
                '--cvar', f'opendream.json_path={world/"Cave Crawlers.json"}', '--cvar', 'opendream.topic_port=25653',
                '--cvar', f'log.path={ROOT/"tests/engine-logs"}', '--cvar', 'net.bindto=127.0.0.1', '--cvar', 'net.port=12153', '--cvar', 'auth.mode=0', '--cvar', 'status.enabled=false',
                '--cvar', 'hub.advertise=false', '--cvar', 'game.auto_pause_empty=false'], env=env, stdout=sl, stderr=subprocess.STDOUT, cwd=world)
            while ' -> Ready' not in slp.read_text(errors='replace'): time.sleep(.5)
            cd = client_copy()
            client = subprocess.Popen([str(dotnet), str(cd/'Robust.Client.dll'), '--mount-zip', str(RUNTIME/'server/Content.Client.zip'),
                '--connect', '--connect-address', 'udp://127.0.0.1:12153', '--username', 'ActionsTest', '--self-contained',
                '--cvar', 'web.headless=false', '--cvar', 'discord.enabled=false'], cwd=cd, env=env, stdout=cl, stderr=subprocess.STDOUT)
            el = world/'ErrorLog.txt'; deadline = time.monotonic() + 420
            while time.monotonic() < deadline and not (el.exists() and 'ACT|done' in el.read_text(errors='replace')): time.sleep(1)
    finally:
        stop(client); stop(server)
    log = (world/'ErrorLog.txt').read_text(errors='replace') if (world/'ErrorLog.txt').exists() else ''
    result = dict(observations=re.findall(r'ACT\|[^\r\n]*', log), runtime_errors=re.findall(r'runtime error[^\r\n]*(?:\n[^\r\n]*){0,3}', log),
                  server_errors=re.findall(r'\[(?:ERRO|FATL)\][^\r\n]*', slp.read_text(errors='replace')),
                  client_errors=re.findall(r'\[(?:ERRO|FATL)\][^\r\n]*', clp.read_text(errors='replace')))
    (ROOT/'tests/actions-checks.json').write_text(json.dumps(result, indent=2) + '\n')
    print('\n'.join(result['observations'])); print('runtime errors:', len(result['runtime_errors']))
    for e in result['runtime_errors'][:8]: print(' ', e.replace('\n', ' | ')[:300])
    print('server errors:', result['server_errors'][:3]); print('client errors:', result['client_errors'][:3])

if __name__ == '__main__': main()
