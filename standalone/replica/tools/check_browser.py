#!/usr/bin/env python3
"""Exercise a native embedded browser through the real client/server protocol."""
import json
import argparse
import shutil
import os
import re
from pathlib import Path
import signal
import subprocess
import tempfile
import time
from skin_layout import write_hints

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT/'runtime/macos-x64'
REPORTS = ROOT/'reports'


def stop(process):
    if process is None or process.poll() is not None:
        return
    process.send_signal(signal.SIGINT)
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--legacy', action='store_true', help='Exercise the complete original game skin')
    args = parser.parse_args()
    dotnet = RUNTIME/'dotnet/dotnet'
    fixture = ROOT/'reference/fixtures/browser.dme'
    if args.legacy:
        fixture = fixture.with_name('browser_legacy.dme')
        fixture.write_text('#include "browser_legacy.dmf"\n#include "browser.dm"\n')
        shutil.copy2(ROOT/'source/skin.dmf', fixture.with_suffix('.dmf'))
    hints = REPORTS/'browser-fixture-layout-hints.json'
    write_hints(fixture.with_suffix('.dmf'), hints)
    env = dict(os.environ, DOTNET_ReadyToRun='0', DM_WEBVIEW_TEST='1',
        DM_WEBVIEW_SNAPSHOT=str(REPORTS/'browser-test.png'),
        ROBUST_MODULE_ROBUST_CLIENT_WEBVIEW=str(RUNTIME/'webview-webkit'))
    env['DM_SKIN_LAYOUT_HINTS'] = str(hints)
    with (REPORTS/'browser-fixture-compile.log').open('w') as log:
        subprocess.run([str(dotnet), str(RUNTIME/'compiler/DMCompiler.dll'), str(fixture)],
                       env=env, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=60)
    (REPORTS/'browser-test.png').unlink(missing_ok=True)
    server = client = None
    server_path = REPORTS/'browser-test-server.log'
    client_path = REPORTS/'browser-test-client.log'
    with tempfile.TemporaryDirectory(prefix='dm-browser-check-') as temporary, server_path.open('w') as server_log, client_path.open('w') as client_log:
        try:
            command = [dotnet, RUNTIME/'server/Robust.Server.dll', '--data-dir', temporary,
                '--cvar', f'opendream.json_path={fixture.with_suffix(".json")}',
                '--cvar', 'opendream.topic_port=25568', '--cvar', 'net.bindto=127.0.0.1',
                '--cvar', 'net.port=12123', '--cvar', 'auth.mode=0', '--cvar', 'status.enabled=false',
                '--cvar', 'hub.advertise=false', '--cvar', 'game.auto_pause_empty=false']
            server = subprocess.Popen([str(v) for v in command], env=env, stdout=server_log, stderr=subprocess.STDOUT)
            deadline = time.monotonic()+60
            while server.poll() is None and time.monotonic() < deadline:
                if ' -> Ready' in server_path.read_text(errors='replace'):
                    break
                time.sleep(0.2)
            else:
                raise RuntimeError('Browser fixture server did not start')
            client_dir = RUNTIME/'client/Space Station 14.app/Contents/Resources'
            client = subprocess.Popen([str(dotnet), str(client_dir/'Robust.Client.dll'),
                '--mount-zip', str(RUNTIME/'server/Content.Client.zip'), '--connect',
                '--connect-address', 'udp://127.0.0.1:12123', '--username', 'BrowserTest',
                '--self-contained', '--cvar', 'web.headless=false', '--cvar', 'discord.enabled=false'], env=env, cwd=client_dir,
                stdout=client_log, stderr=subprocess.STDOUT)
            deadline = time.monotonic()+90
            while client.poll() is None and time.monotonic() < deadline:
                if ((REPORTS/'browser-test.png').is_file() and
                    'FOUNDATION_BROWSER|named_panel_close_received' in server_path.read_text(errors='replace')):
                    break
                time.sleep(0.25)
            client_text = client_path.read_text(errors='replace')
            server_text = server_path.read_text(errors='replace')
            frames = re.findall(r'attached title=.*? frame=\(([^)]+)\) parent=\(([^)]+)\) visible=true', client_text)
            primary = re.findall(r'panel=1 attached title=.*? frame=\(([^)]+)\) parent=\(([^)]+)\) visible=true', client_text)
            fills_remaining = False
            if primary:
                final, parent = primary[-1]
                x, y, width, height = map(float, final.split(','))
                _, _, pw, ph = map(float, parent.split(','))
                if args.legacy:
                    fills_remaining = x >= pw/2-1 and width <= pw/2+1 and y >= -1 and y+height <= ph+1
                else:
                    fills_remaining = abs(x-280) <= 1 and abs(y) <= 1 and abs(width-(pw-280)) <= 1 and abs(height-(ph-30)) <= 1
            geometry_ok = bool(frames)
            for frame, parent in frames:
                x, y, width, height = map(float, frame.split(','))
                _, _, pw, ph = map(float, parent.split(','))
                geometry_ok &= x >= -1 and y >= -1 and width > 0 and height > 0 and x+width <= pw+1 and y+height <= ph+1
            result = {
                'native_webkit_initialized': 'Native WebKit renderer initialized' in client_text,
                'unnamed_browse_routed': 'FOUNDATION BROWSER TEST' in client_text,
                'resource_image_loaded': '"loaded":true' in client_text,
                'topic_received_by_original_dm_handler': 'FOUNDATION_BROWSER|topic_received|usr_src=1' in server_text,
                'server_response_rendered': 'FOUNDATION BROWSER RESPONSE' in client_text,
                'embedded_panel_attached': 'visible=True' in client_text or 'visible=true' in client_text,
                'initially_hidden_browser_shown': bool(re.search(r'panel=1 attached[^\n]*visible=true', client_text)),
                'panel_geometry_within_window': geometry_ok,
                'nested_pane_fits_splitter': ('fitting embedded pane browserwindow' if args.legacy else 'fitting embedded pane browserpane') in client_text,
                'zero_size_child_fills_remaining_area': fills_remaining,
                'named_panel_rendered': 'FOUNDATION NAMED PANEL' in client_text,
                'byond_link_closed_named_panel': 'FOUNDATION_BROWSER|named_panel_close_received' in server_text,
                'snapshot_created': (REPORTS/'browser-test.png').is_file(),
                'browser_errors': [line for line in client_text.splitlines() if '[ERRO] mac.webview:' in line],
            }
            (REPORTS/'browser-checks.json').write_text(json.dumps(result, indent=2)+'\n')
            print(json.dumps(result, indent=2))
            if not all(value for key, value in result.items() if key != 'browser_errors') or result['browser_errors']:
                raise SystemExit(1)
        finally:
            stop(client)
            stop(server)


if __name__ == '__main__':
    main()
