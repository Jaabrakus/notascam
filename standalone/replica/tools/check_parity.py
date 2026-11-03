#!/usr/bin/env python3
"""Run the same bounded fixture in isolated BYOND and replacement runtimes."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT/'reports'
FIXTURES = ROOT/'reference/fixtures'


def logged(command, path, **kwargs):
    with path.open('w') as log:
        subprocess.run([str(x) for x in command], stdout=log, stderr=subprocess.STDOUT,
                       timeout=120, check=True, **kwargs)


def observations(path):
    return re.findall(r'PARITY\|[^\r\n]*', path.read_text(errors='replace'))


def run_server(command, path, env):
    with path.open('w') as log:
        process = subprocess.Popen([str(x) for x in command], stdout=log, stderr=subprocess.STDOUT, env=env)
        try:
            deadline = time.monotonic()+90
            while process.poll() is None and time.monotonic()<deadline:
                output = path.read_text(errors='replace')
                if '[ERRO]' in output or '[FATL]' in output:
                    break
                if 'PARITY|complete' in output:
                    try: process.wait(timeout=10)
                    except subprocess.TimeoutExpired: pass
                    break
                time.sleep(.1)
        finally:
            if process.poll() is None:
                process.send_signal(signal.SIGINT)
                try: process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('fixture')
    parser.add_argument('--reference', action='store_true')
    parser.add_argument('--reference-only', action='store_true')
    parser.add_argument('--reload', action='store_true', help='Also compare a second process using the saved file')
    parser.add_argument('--supervised', action='store_true', help='Allow explicit world.Reboot() in the fixture')
    parser.add_argument('--server-dir', type=Path)
    parser.add_argument('--fixture-dir', type=Path, default=FIXTURES)
    parser.add_argument('--reference-dir', type=Path)
    parser.add_argument('--reference-timeout', type=float, default=45, help='seconds to wait for the emulated BYOND run')
    args = parser.parse_args()
    name = args.fixture
    fixtures = args.fixture_dir.resolve()
    if not re.fullmatch(r'[a-z_]+', name):
        parser.error('Use a fixture basename')
    env = dict(os.environ, DOTNET_ReadyToRun='0')
    runtime = ROOT/'runtime/macos-x64'
    expected_path = REPORTS/f'byond-{name}-runtime.log'
    if args.reference or args.reference_only:
        reference_dir = (args.reference_dir or fixtures).resolve()
        prefix = ['docker', 'run', '--rm', '--network', 'none', '--memory', '1g', '--ulimit', 'core=0',
                  '--mount', f'type=bind,src={reference_dir},dst=/game']
        image = 'dungeon-master-reference:516.1655'
        logged(prefix+[image, '/opt/byond/bin/DreamMaker', f'/game/{name}.dme'],
               REPORTS/f'byond-{name}-compile.log')
        container = f'dm-parity-{name}-{os.getpid()}'
        with expected_path.open('w') as log:
            process = subprocess.Popen(prefix+['--name', container, image,
                '/opt/byond/bin/DreamDaemon', f'/game/{name}.dmb', '0', '-trusted', '-invisible', '-close'],
                stdout=log, stderr=subprocess.STDOUT)
            try:
                deadline = time.monotonic()+args.reference_timeout
                while process.poll() is None and time.monotonic()<deadline:
                    if 'PARITY|complete' in expected_path.read_text(errors='replace'):
                        break
                    time.sleep(.1)
            finally:
                subprocess.run(['docker', 'stop', '-t', '1', container], stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL, timeout=10)
                process.wait(timeout=10)
    if 'runtime error:' in expected_path.read_text(errors='replace'):
        raise RuntimeError('Reference fixture produced runtime errors; inspect its log')
    expected = observations(expected_path)
    if not expected or expected[-1] != 'PARITY|complete':
        raise RuntimeError('Reference did not complete; inspect its log')
    if args.reload and (args.reference or args.reference_only):
        subprocess.run([sys.executable, __file__, name+'_reload', '--reference-only',
                        '--fixture-dir', str(fixtures), '--reference-dir', str(args.reference_dir or fixtures)], check=True)
    if args.reference_only:
        print('\n'.join(expected))
        return
    logged([runtime/'dotnet/dotnet', runtime/'compiler/DMCompiler.dll', fixtures/f'{name}.dme'],
           REPORTS/f'opendream-{name}-compile.log', env=env)
    actual_path = REPORTS/f'opendream-{name}-runtime.log'
    with tempfile.TemporaryDirectory(prefix='dm-parity-') as data:
        command = [runtime/'dotnet/dotnet', (args.server_dir or runtime/'server')/'Robust.Server.dll', '--data-dir', data,
                '--cvar', f'opendream.json_path={fixtures/name}.json',
                '--cvar', 'opendream.topic_port=25569',
                '--cvar', 'net.bindto=127.0.0.1', '--cvar', 'net.port=12124',
                '--cvar', 'status.enabled=false', '--cvar', 'hub.advertise=false',
                '--cvar', 'auth.mode=0', '--cvar', 'game.auto_pause_empty=false']
        if args.supervised:
            command = [sys.executable, ROOT/'tools/server_supervisor.py', '--', *command]
        run_server(command, actual_path, env=env)
    actual = observations(actual_path)
    result = {'fixture': name, 'matches': expected == actual, 'expected': expected, 'actual': actual,
              'runtime_sha256': hashlib.sha256(((args.server_dir or runtime/'server')/'Resources/Assemblies/OpenDreamRuntime.dll').read_bytes()).hexdigest(),
              'fixture_sha256': hashlib.sha256((fixtures/f'{name}.dm').read_bytes()).hexdigest() if (fixtures/f'{name}.dm').exists() else None,
              'reference_log_sha256': hashlib.sha256(expected_path.read_bytes()).hexdigest(),
              'reference_version': 'BYOND 516.1655',
              'errors': re.findall(r'\[(?:ERRO|FATL)\][^\r\n]*', actual_path.read_text(errors='replace'))}
    (REPORTS/f'{name}-parity.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))
    if not result['matches'] or result['errors']:
        raise SystemExit(1)
    if args.reload:
        subprocess.run([sys.executable, __file__, name+'_reload', '--fixture-dir', str(fixtures),
                        '--server-dir', str(args.server_dir or runtime/'server')], check=True)


if __name__ == '__main__':
    main()
