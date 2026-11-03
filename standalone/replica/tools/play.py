#!/usr/bin/env python3
"""Launch the original-code local server and its Mac OpenDream client."""
import argparse
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time
import json
import shutil
from skin_layout import write_hints

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--username', default='Kiwi')
    args = parser.parse_args()
    runtime = ROOT/'runtime/macos-x64'
    client_dir = runtime/'client/Space Station 14.app/Contents/Resources'
    dotnet = runtime/'dotnet/dotnet'
    client = client_dir/'Robust.Client.dll'
    if not client.is_file():
        raise SystemExit('The Mac client has not been staged. See FOUNDATION.md.')
    env = dict(os.environ, DOTNET_ReadyToRun='0',
               ROBUST_MODULE_ROBUST_CLIENT_WEBVIEW=str(runtime/'webview-webkit'),
               DM_LOCAL_SERVER_READY_FILE=str(ROOT/'reports/local-server-ready.txt'),
               DM_LOCAL_SERVER_PORT='12121')
    hints = ROOT/'reports/skin-layout-hints.json'
    write_hints(ROOT/'opendream/skin.dmf', hints)
    env['DM_SKIN_LAYOUT_HINTS'] = str(hints)
    # Earlier runtimes had an empty datum.Write(). Their empty files must not
    # be treated as actual armies by the original LoadUnits() procedure.
    # Preserve those empty files for diagnosis; never move a populated save.
    for save in (ROOT/'opendream/units').glob('*_save.sav'):
        try:
            contents = json.loads(save.read_text())
        except (ValueError, UnicodeError):
            continue
        if contents == {'$type': 'dir', '_nodes': {}}:
            backup = ROOT/'reports/empty-save-backups'/save.name
            backup.parent.mkdir(exist_ok=True)
            if backup.exists() and backup.read_bytes() != save.read_bytes():
                raise RuntimeError(f'Empty-save backup differs: {backup}')
            shutil.copy2(save, backup)
            save.unlink()
            print(f'Backed up an empty save left by an earlier test runtime: {backup}', flush=True)
    own_server = None
    server_log = None
    # A second launch may reuse the local server that is already running.
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
        try:
            probe.bind(('127.0.0.1', 12121))
            available = True
        except OSError:
            available = False
    try:
        if available:
            print('Starting the original Dungeon Master world. Loading can take a minute.', flush=True)
            log_path = ROOT/'reports/play-server.log'
            server_log = log_path.open('w')
            own_server = subprocess.Popen([sys.executable, str(ROOT/'tools/local_runtime.py'), 'server'],
                                          env=env, stdout=server_log, stderr=subprocess.STDOUT,
                                          start_new_session=True)
            deadline = time.monotonic()+180
            while own_server.poll() is None and time.monotonic() < deadline:
                if ' -> Ready' in log_path.read_text(errors='replace'):
                    break
                time.sleep(0.5)
            else:
                raise RuntimeError(f'Server did not start; see {log_path}')
        else:
            print('Connecting to the existing local server on port 12121.', flush=True)
        print('Opening Dungeon Master with native browser panels. Press R to choose a race.', flush=True)
        with (ROOT/'reports/play-client.log').open('w') as log:
            result = subprocess.call([str(dotnet), str(client), '--mount-zip',
                str(runtime/'server/Content.Client.zip'), '--connect', '--connect-address',
                'udp://127.0.0.1:12121', '--username', args.username, '--self-contained',
                '--cvar', 'web.headless=false', '--cvar', 'discord.enabled=false'], cwd=client_dir, env=env,
                stdout=log, stderr=subprocess.STDOUT)
        if result:
            raise RuntimeError(f'Client exited with code {result}; see reports/play-client.log')
    finally:
        if own_server is not None and own_server.poll() is None:
            # Allow the disconnect/Logout save to run before stopping this launcher’s server.
            time.sleep(2)
            os.killpg(own_server.pid, signal.SIGINT)
            try:
                own_server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(own_server.pid, signal.SIGTERM)
                own_server.wait(timeout=10)
        if server_log is not None:
            server_log.close()


if __name__ == '__main__':
    main()
