#!/usr/bin/env python3
"""Check original hashes, constructor parity and full-world OpenDream startup.

The optional --reference run uses BYOND only as an isolated test oracle. The
replacement server never loads BYOND binaries. This is not a gameplay test.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT/'reports'
FIXTURES = ROOT/'reference/fixtures'


def run_logged(command, filename, **kwargs):
    with (REPORTS/filename).open('w') as log:
        subprocess.run([str(v) for v in command], stdout=log, stderr=subprocess.STDOUT,
                       timeout=120, check=True, **kwargs)


def observations(path):
    return re.findall(r'FOUNDATION\|[^\r\n]*', path.read_text(errors='replace'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dotnet', type=Path, required=True, help='Compiler runtime')
    parser.add_argument('--compiler', type=Path, required=True)
    parser.add_argument('--server-dotnet', type=Path, required=True)
    parser.add_argument('--server', type=Path, required=True, help='Robust.Server.dll')
    parser.add_argument('--reference', action='store_true', help='Refresh reference with isolated Docker image')
    args = parser.parse_args()
    entries = json.loads((REPORTS/'source-baseline.json').read_text())
    for base in (ROOT/'source', ROOT.parent.parent):
        for entry in entries:
            path = base/entry['path']
            if hashlib.sha256(path.read_bytes()).hexdigest() != entry['sha256']:
                raise RuntimeError(f'Original source hash differs: {path}')
    if args.reference:
        prefix = ['docker', 'run', '--rm', '--network', 'none', '--memory', '1g', '--ulimit', 'core=0',
                  '--mount', f'type=bind,src={FIXTURES},dst=/game',
                  'dungeon-master-reference:516.1655']
        run_logged(prefix+['/opt/byond/bin/DreamMaker', '/game/context.dme'], 'byond-context-compile.log')
        # QEMU's 32-bit daemon teardown is unreliable on this ARM host. Stop the
        # isolated oracle after its completion marker; teardown is not a parity assertion.
        name = f'dm-foundation-oracle-{os.getpid()}'
        command = prefix[:2]+['--name', name]+prefix[2:]+[
            '/opt/byond/bin/DreamDaemon', '/game/context.dmb', '0', '-trusted', '-invisible', '-close']
        path = REPORTS/'byond-context-runtime.log'
        with path.open('w') as log:
            oracle = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
            try:
                deadline = time.monotonic()+30
                while oracle.poll() is None and time.monotonic() < deadline:
                    if 'FOUNDATION|complete' in path.read_text(errors='replace'):
                        break
                    time.sleep(0.1)
            finally:
                subprocess.run(['docker', 'stop', '-t', '1', name], stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL, timeout=10)
                oracle.wait(timeout=10)
    expected = observations(REPORTS/'byond-context-runtime.log')
    if not expected or expected[-1] != 'FOUNDATION|complete':
        raise RuntimeError('No complete BYOND context reference; run with --reference')
    run_logged([args.dotnet, args.compiler, FIXTURES/'context.dme'], 'opendream-context-compile.log')
    env = dict(os.environ, DOTNET_ReadyToRun='0')

    def server_command(game, data, port, pause):
        return [str(args.server_dotnet.resolve()), str(args.server.resolve()), '--data-dir', str(data),
                '--cvar', f'opendream.json_path={game}', '--cvar', 'net.bindto=127.0.0.1',
                '--cvar', f'opendream.topic_port={port+13450}',
                '--cvar', f'net.port={port}', '--cvar', 'net.max_connections=1',
                '--cvar', 'status.enabled=false', '--cvar', 'hub.advertise=false',
                '--cvar', 'auth.mode=0', '--cvar', f'game.auto_pause_empty={pause}']

    with tempfile.TemporaryDirectory(prefix='dm-foundation-') as temporary:
        temp = Path(temporary)
        run_logged(server_command(FIXTURES/'context.json', temp/'context', 12122, 'false'),
                   'opendream-context-runtime.log', env=env)
        actual = observations(REPORTS/'opendream-context-runtime.log')
        # Spawn ordering is checked too: this fixture has four equal-delay tasks.
        context_match = actual == expected
        log_path = REPORTS/'opendream-server-foundation.log'
        ready = False
        with log_path.open('w') as log:
            process = subprocess.Popen(server_command(ROOT/'opendream/Cave Crawlers.json',
                                       temp/'world', 12126, 'true'), env=env,
                                       stdout=log, stderr=subprocess.STDOUT)
            try:
                deadline = time.monotonic()+120
                while process.poll() is None and time.monotonic() < deadline:
                    content = log_path.read_text(errors='replace')
                    if ' -> Ready' in content:
                        ready = True
                        time.sleep(3)
                        break
                    time.sleep(0.25)
            finally:
                if process.poll() is None:
                    process.send_signal(signal.SIGINT)
                    try:
                        process.wait(timeout=15)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
        content = log_path.read_text(errors='replace')
    errors = re.findall(r'\[ERRO\][^\r\n]*', content)
    result = {'original_and_frozen_files_verified': len(entries),
              'runtime_sha256': hashlib.sha256((args.server.parent/'Resources/Assemblies/OpenDreamRuntime.dll').read_bytes()).hexdigest(),
              'context_observations': len(expected), 'constructor_context_matches_byond': context_match,
              'world_reached_ready': ready, 'world_error_count': len(errors),
              'errors': errors, 'client_session_verified': False, 'replica_verified': False}
    (REPORTS/'foundation-checks.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))
    if not context_match or not ready or errors:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
