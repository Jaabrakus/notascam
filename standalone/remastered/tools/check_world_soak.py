#!/usr/bin/env python3
"""Accept a frozen full world in isolation; requires explicit --launch.

Copies all game/maps and server/compiler/dotnet files, retains tested sources and
logs, and uses the corrected check_combat.run_world without a player or client.
Do not launch until the lead releases simulation capacity and freezes sources.
"""
import argparse
import ast
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import socket
import subprocess
import sys
import time
import traceback
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SELF = Path(__file__).resolve()
HELPER = ROOT / 'tools/check_combat.py'
NORMAL = Path.home() / 'Library/Application Support/Dungeon Master Remastered/world/units'
PREFIX = 'WORLD_SOAK'
IGNORED = ('Cave Crawlers.json', '*.sav', 'ErrorLog.txt', 'units', 'players', 'saves', '__pycache__')


def utc():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def hashes(folder):
    return {str(p.relative_to(folder)): sha(p) for p in sorted(folder.rglob('*')) if p.is_file()}


def unchanged(folder, expected):
    try:
        return all((folder / name).is_file() and sha(folder / name) == value for name, value in expected.items())
    except OSError:
        return False


def normal_saves():
    return hashes(NORMAL) if NORMAL.exists() else {}


def write_json(path, value):
    temporary = path.with_name(path.name + '.partial')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    os.replace(temporary, path)


def corrected_helper(source):
    """Require both reviewed fail-closed conditions in run_world's conjunction."""
    function = next(n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == 'run_world')
    result = next(n.value for n in ast.walk(function) if isinstance(n, ast.Assign)
                  and any(isinstance(t, ast.Name) and t.id == 'result' for t in n.targets))
    fields = {k.arg: k.value for k in result.keywords}
    passed = fields['passed']
    terms = [ast.dump(term, include_attributes=False) for term in passed.values] if isinstance(passed, ast.BoolOp) and isinstance(passed.op, ast.And) else []
    for expression in ('not timed_out', 'server.returncode == 0'):
        if ast.dump(ast.parse(expression, mode='eval').body, include_attributes=False) not in terms:
            raise ValueError('Install the reviewed clean-exit check_combat.py before this run')
    if not {'timed_out', 'server_exit_code'} <= fields.keys():
        raise ValueError('Corrected helper must record timeout and server exit status')


def port_busy(port):
    with socket.socket() as connection:
        connection.settimeout(0.2)
        if connection.connect_ex(('127.0.0.1', port)) == 0:
            return True
    # The game transport binds UDP; the topic endpoint uses TCP.
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as datagram:
        try:
            datagram.bind(('127.0.0.1', port))
        except OSError:
            return True
    return False


def group_alive(pgid):
    try:
        os.killpg(pgid, 0)
        return True
    except ProcessLookupError:
        return False


def stop_group(process):
    actions = []
    for sig, grace in ((signal.SIGINT, 15), (signal.SIGTERM, 10), (signal.SIGKILL, 5)):
        if not group_alive(process.pid):
            break
        try:
            os.killpg(process.pid, sig)
            actions.append(signal.Signals(sig).name)
        except ProcessLookupError:
            break
        deadline = time.monotonic() + grace
        while group_alive(process.pid) and time.monotonic() < deadline:
            process.poll()
            time.sleep(0.2)
    process.wait(timeout=10)
    return {'signals': actions, 'owned_group_stopped': not group_alive(process.pid)}


def observer(ticks):
    return f'''proc/RemasterWorldAcceptance()
\tvar/start = world.time
\twhile(world.time - start < {ticks})
\t\tvar/population = 0
\t\tfor(var/mob/Monsters/M in world) population++
\t\tworld.log << "{PREFIX}|sample|tick=[world.time-start]|population=[population]|season=[Season]|night=[night]"
\t\tsleep(min(600, {ticks} - (world.time-start)))
\tworld.log << "{PREFIX}|elapsed|ticks=[world.time-start]|target={ticks}"
\tworld.log << "{PREFIX}|complete|failures=0"
\tshutdown()
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT / 'game', help='Frozen complete game directory')
    parser.add_argument('--runtime', type=Path, default=ROOT.parent / 'replica/runtime/macos-x64')
    parser.add_argument('--output', type=Path, default=ROOT / 'tests')
    parser.add_argument('--label', required=True)
    parser.add_argument('--ticks', type=int, required=True)
    parser.add_argument('--port', type=int, required=True)
    parser.add_argument('--timeout', type=float, required=True, help='Server deadline in seconds, after compilation')
    parser.add_argument('--launch', action='store_true', help='Explicitly launch only after the lead releases capacity')
    args = parser.parse_args()
    if not args.launch:
        parser.error('Preparation only: --launch is required after the lead releases simulation capacity')
    if not re.fullmatch(r'[A-Za-z0-9_-]+', args.label) or args.ticks <= 0 or args.timeout <= 0 or not 1024 <= args.port <= 52035:
        parser.error('Use a simple unique label, positive ticks/timeout, and port 1024..52035')
    args.source = args.source.resolve(strict=True)
    args.runtime = args.runtime.resolve(strict=True)
    args.output = args.output.resolve()
    if args.output.is_relative_to(args.source) or args.output.is_relative_to(args.runtime):
        parser.error('Output must be outside source and runtime directories')
    helper_source = HELPER.read_text()
    corrected_helper(helper_source)
    if any(port_busy(port) for port in (args.port, args.port + 13500)):
        parser.error('Chosen server/topic port is already in use; unrelated processes will not be stopped')
    folder = args.output / f'{args.label}-world-soak'
    folder.mkdir(parents=True, exist_ok=False)
    (folder / 'tests').mkdir()
    (folder / 'tools').mkdir()
    (folder / 'tmp').mkdir()
    arena, runtime = folder / 'world', folder / 'runtime'
    report_path = folder / 'acceptance.json'
    report = {'started_utc': utc(), 'passed': False, 'status': 'copying', 'ticks': args.ticks,
              'port': args.port, 'topic_port': args.port + 13500, 'timeout': args.timeout,
              'server_exit_code': None, 'timed_out': None,
              'source': str(args.source), 'runtime_source': str(args.runtime),
              'normal_saves_before': normal_saves(), 'source_manifest': str(folder / 'manifest.json'),
              'scope': 'Original full maps and startup with a read-only timed observer and shutdown. '
                       'No connected players/clients, normal profile, modified unit stats, or physical input. '
                       'A bounded autonomous-world check, not multiplayer/save-reload or exhaustive gameplay parity.'}
    write_json(report_path, report)
    interrupted = []
    handlers = {sig: signal.signal(sig, lambda number, frame: interrupted.append(number))
                for sig in (signal.SIGINT, signal.SIGTERM)}
    process = awake = None
    manifest = None
    try:
        shutil.copytree(args.source, arena, ignore=shutil.ignore_patterns(*IGNORED))
        source_hashes = hashes(arena)
        if not unchanged(args.source, source_hashes):
            raise RuntimeError('Source changed while it was copied')
        runtime.mkdir()
        for component in ('server', 'compiler', 'dotnet'):
            shutil.copytree(args.runtime / component, runtime / component)
        runtime_hashes = hashes(runtime)
        if not unchanged(args.runtime, runtime_hashes):
            raise RuntimeError('Runtime changed while it was copied')
        world_file = arena / 'Code/World.dm'
        original = world_file.read_bytes()
        marker = b'\t\tCallSave()'
        if original.count(marker) != 1:
            raise RuntimeError('Original startup shape changed; review observer insertion')
        if (arena / 'world_acceptance.dm').exists() or (arena / 'world_acceptance.dme').exists():
            raise RuntimeError('Observer filenames already exist in game source')
        world_file.write_bytes(original.replace(marker, marker + b'\n\t\tspawn() RemasterWorldAcceptance()'))
        (arena / 'world_acceptance.dm').write_text(observer(args.ticks))
        fixture = arena / 'world_acceptance.dme'
        fixture.write_bytes((arena / 'Cave Crawlers.dme').read_bytes() + b'\n#include "world_acceptance.dm"\n')
        tested_hashes = hashes(arena)
        archive = folder / 'tested-source.zip'
        with zipfile.ZipFile(archive, 'x', zipfile.ZIP_DEFLATED) as zipped:
            for name in sorted(tested_hashes):
                zipped.write(arena / name, name)
        copied_helper = folder / 'tools/check_combat.py'
        copied_helper.write_text(helper_source)
        worker = folder / 'run_private.py'
        worker.write_text('from pathlib import Path\nimport sys\nroot=Path(__file__).resolve().parent\n'
                          'sys.path.insert(0,str(root/"tools"))\nimport check_combat as core\n'
                          'core.ROOT=root\ncore.RUNTIME=root/"runtime"\n'
                          f'passed=core.run_world(root/"world",root/"world/world_acceptance.dme",{args.label!r},{args.timeout!r},prefix={PREFIX!r},port={args.port})\n'
                          'raise SystemExit(0 if passed else 1)\n')
        manifest = {'created_utc': utc(), 'source': str(args.source), 'source_sha256': source_hashes,
                    'tested_source_sha256': tested_hashes, 'runtime_source': str(args.runtime),
                    'runtime_sha256': runtime_hashes, 'fixture_sha256': sha(arena / 'world_acceptance.dm'),
                    'archive_sha256': sha(archive), 'helper_sha256': sha(copied_helper),
                    'runner_sha256': sha(SELF), 'private_worker_sha256': sha(worker),
                    'observer_only_startup_change': True, 'excluded_mutable_names': IGNORED}
        write_json(folder / 'manifest.json', manifest)
        (folder / 'manifest.json').chmod(0o444)
        archive.chmod(0o444)
        report['manifest_sha256'] = sha(folder / 'manifest.json')
        if interrupted:
            raise InterruptedError('Interrupted before launch')
        if sha(HELPER) != manifest['helper_sha256']:
            raise RuntimeError('Acceptance helper changed during preparation')
        if any(port_busy(port) for port in (args.port, args.port + 13500)):
            raise RuntimeError('Chosen port became occupied during preparation; nothing launched')
        env = {k: v for k, v in os.environ.items() if not k.startswith('DM_')}
        env.update(TMPDIR=str(folder / 'tmp'), DOTNET_CLI_HOME=str(folder / 'tmp/dotnet-home'),
                   DOTNET_CLI_TELEMETRY_OPTOUT='1', DOTNET_SKIP_FIRST_TIME_EXPERIENCE='1')
        if Path('/usr/bin/caffeinate').exists():
            awake = subprocess.Popen(['/usr/bin/caffeinate', '-i', '-t', str(int(args.timeout + 360))])
        with (folder / 'worker.log').open('w') as log:
            process = subprocess.Popen([sys.executable, str(worker)], env=env, cwd=folder,
                                       stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            report.update(status='running', worker_pid=process.pid, owned_process_group=process.pid,
                          launched_utc=utc())
            write_json(report_path, report)
            deadline = time.monotonic() + args.timeout + 330
            next_progress = 0
            while process.poll() is None:
                if interrupted:
                    raise InterruptedError(f'Interrupted by signal {interrupted[-1]}')
                if time.monotonic() >= deadline:
                    report['supervisor_timed_out'] = True
                    raise TimeoutError('Compilation/server/cleanup exceeded supervisor deadline')
                if time.monotonic() >= next_progress:
                    report['updated_utc'] = utc()
                    world_log = arena / 'ErrorLog.txt'
                    text = world_log.read_text(errors='replace') if world_log.exists() else ''
                    samples = re.findall(r'WORLD_SOAK\|sample\|[^\r\n]*', text)
                    report['latest_sample'] = samples[-1] if samples else None
                    write_json(report_path, report)
                    next_progress = time.monotonic() + 15
                time.sleep(0.5)
        report['worker_exit_code'] = process.returncode
        if group_alive(process.pid):
            raise RuntimeError('Worker left child processes; stopping only its owned process group')
        helper_report = folder / f'tests/{args.label}-checks.json'
        checks = json.loads(helper_report.read_text()) if helper_report.exists() else {}
        observations = checks.get('observations', [])
        elapsed = [int(m[1]) for item in observations
                   if (m := re.fullmatch(r'WORLD_SOAK\|elapsed\|ticks=([0-9]+)\|target=' + str(args.ticks), item))]
        report.update(helper_report=str(helper_report), server_exit_code=checks.get('server_exit_code'),
                      timed_out=checks.get('timed_out'), elapsed_ticks=elapsed,
                      exact_completion=f'{PREFIX}|complete|failures=0' in observations)
        report['passed'] = (process.returncode == 0 and checks.get('passed') is True
                            and checks.get('server_exit_code') == 0 and checks.get('timed_out') is False
                            and report['exact_completion'] and bool(elapsed) and min(elapsed) >= args.ticks)
        report['status'] = 'completed' if report['passed'] else 'failed'
    except BaseException as error:
        report.update(status='interrupted' if interrupted else 'failed', passed=False,
                      error=f'{type(error).__name__}: {error}', traceback=traceback.format_exc())
    finally:
        if process is not None:
            try:
                report['cleanup'] = stop_group(process)
                report['worker_exit_code'] = process.returncode
                if not report['cleanup']['owned_group_stopped']:
                    report['passed'] = False
            except Exception as error:
                report.update(passed=False, cleanup_error=str(error))
        if awake is not None:
            try:
                awake.terminate()
                try:
                    awake.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    awake.kill()
                    awake.wait(timeout=5)
            except Exception as error:
                report.update(passed=False, awake_cleanup_error=str(error))
        try:
            report['normal_saves_after'] = normal_saves()
            report['normal_saves_unchanged'] = report['normal_saves_before'] == report['normal_saves_after']
            if manifest:
                report['integrity'] = {
                    'source_origin': unchanged(args.source, manifest['source_sha256']),
                    'runtime_origin': unchanged(args.runtime, manifest['runtime_sha256']),
                    'tested_source': unchanged(arena, manifest['tested_source_sha256']),
                    'runtime_copy': hashes(runtime) == manifest['runtime_sha256'],
                    'helper_copy': sha(folder / 'tools/check_combat.py') == manifest['helper_sha256'],
                    'helper_origin': sha(HELPER) == manifest['helper_sha256'],
                    'runner': sha(SELF) == manifest['runner_sha256'],
                    'manifest': sha(folder / 'manifest.json') == report['manifest_sha256'],
                    'archive': sha(folder / 'tested-source.zip') == manifest['archive_sha256'],
                    'worker': sha(folder / 'run_private.py') == manifest['private_worker_sha256'],
                }
                report['passed'] = report['passed'] and all(report['integrity'].values())
            else:
                report['passed'] = False
            report['passed'] = report['passed'] and report['normal_saves_unchanged'] and not interrupted
            report['evidence_sha256'] = {str(p.relative_to(folder)): sha(p) for p in sorted(folder.rglob('*'))
                                         if p.is_file() and p != report_path and not p.is_relative_to(runtime)
                                         and not p.is_relative_to(arena) and not p.is_relative_to(folder / 'tmp')}
            world_log = arena / 'ErrorLog.txt'
            if world_log.exists():
                report['world_error_log'] = {'path': str(world_log), 'sha256': sha(world_log)}
            compiled = arena / 'world_acceptance.json'
            if compiled.exists():
                report['compiled_world'] = {'path': str(compiled), 'sha256': sha(compiled)}
        except Exception as error:
            report.update(passed=False, verification_error=f'{type(error).__name__}: {error}',
                          verification_traceback=traceback.format_exc())
        if interrupted:
            report['passed'] = False
        if not report['passed'] and report['status'] == 'completed':
            report['status'] = 'failed'
        report['finished_utc'] = utc()
        report['evidence_directory'] = str(folder)
        try:
            write_json(report_path, report)
        finally:
            for sig, handler in handlers.items():
                signal.signal(sig, handler)
        print(json.dumps({'passed': report['passed'], 'status': report['status'], 'report': str(report_path)}))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
