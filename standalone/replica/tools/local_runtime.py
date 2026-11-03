#!/usr/bin/env python3
"""Local Mac foundation commands; no BYOND installation is required."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
from prepare_standard import main as prepare_standard
from server_supervisor import supervise

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('compile', 'check', 'server'))
    parser.add_argument('--reference', action='store_true')
    args = parser.parse_args()
    runtime = ROOT/'runtime/macos-x64'
    dotnet = runtime/'dotnet/dotnet'
    compiler = runtime/'compiler/DMCompiler.dll'
    server = runtime/'server/Robust.Server.dll'
    for path in (dotnet, compiler, server):
        if not path.is_file():
            raise SystemExit(f'Missing local runtime dependency: {path}. See FOUNDATION.md.')
    env = dict(os.environ, DOTNET_ReadyToRun='0')
    if args.action == 'compile':
        prepare_standard()
        command = [sys.executable, ROOT/'tools/prepare_opendream.py',
                   '--dotnet', dotnet, '--compiler', compiler]
    elif args.action == 'check':
        command = [sys.executable, ROOT/'tools/check_foundation.py', '--dotnet', dotnet,
                   '--compiler', compiler, '--server-dotnet', dotnet, '--server', server]
        if args.reference:
            command.append('--reference')
    else:
        print('Starting the original-code server on localhost:12121. Stop with Control-C.', flush=True)
        command = [dotnet, server, '--data-dir', ROOT/'runtime/server-data',
                   '--cvar', f'opendream.json_path={ROOT / "opendream/Cave Crawlers.json"}',
                   '--cvar', 'net.bindto=127.0.0.1', '--cvar', 'net.port=12121',
                   '--cvar', 'net.max_connections=16', '--cvar', 'status.enabled=false',
                   '--cvar', 'hub.advertise=false', '--cvar', 'auth.mode=0',
                   '--cvar', 'game.auto_pause_empty=true']
    if args.action == 'server':
        raise SystemExit(supervise(command, env, ROOT/'reports/local-server-ready.txt'))
    raise SystemExit(subprocess.call([str(v) for v in command], env=env))


if __name__ == '__main__':
    main()
