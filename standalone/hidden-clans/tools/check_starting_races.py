#!/usr/bin/env python3
"""Freeze a package, then serially accept all 13 original starting races.

Preparation never launches the app. `run` requires a separately created freeze
manifest and an exclusive native test slot. Each race uses check_app.py's fresh
private profile, original race prompt, save/reload checks and native snapshots.
"""
import argparse
import contextlib
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import signal
import socket
import stat
import subprocess
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
SELF = Path(__file__).resolve()
HELPER = ROOT / 'tools/check_app.py'
OUT = ROOT / 'tests'
NORMAL = Path.home() / 'Library/Application Support/Dungeon Master Remastered/world/units'
PORTS = (12151, 25651)


def utc():
    return datetime.now(timezone.utc).isoformat()


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def canonical_digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def inventory(folder):
    """Hash every package file, plus directory modes and literal symlink targets.

    Never traverse symlinks, and reject links escaping the frozen package: an
    external mutable runtime cannot be accepted as a self-contained package.
    """
    result = {}
    for current, dirs, files in os.walk(folder, followlinks=False):
        for name in sorted(dirs + files):
            path = Path(current) / name
            info = path.lstat()
            row = {'mode': stat.S_IMODE(info.st_mode)}
            if path.is_symlink():
                target = path.resolve(strict=True)
                if not target.is_relative_to(folder):
                    raise ValueError(f'Package symlink escapes app: {path} -> {target}')
                row.update(kind='symlink', target=os.readlink(path))
            elif path.is_dir():
                row['kind'] = 'directory'
            elif path.is_file():
                row.update(kind='file', bytes=info.st_size, sha256=digest(path))
            else:
                raise ValueError(f'Unsupported package entry: {path}')
            result[str(path.relative_to(folder))] = row
    if not result:
        raise ValueError(f'Empty or missing app: {folder}')
    return result


def normal_saves():
    return {str(p.relative_to(NORMAL)): digest(p) for p in sorted(NORMAL.rglob('*.sav'))} if NORMAL.exists() else {}


def atomic_json(path, value):
    temporary = path.with_name(path.name + '.partial')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    os.replace(temporary, path)


def load_helper():
    spec = importlib.util.spec_from_file_location('starting_races_check_app', HELPER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def occupied_ports():
    occupied = []
    for port in PORTS:
        for family, address in ((socket.AF_INET, ('127.0.0.1', port)), (socket.AF_INET6, ('::1', port))):
            with socket.socket(family, socket.SOCK_STREAM) as connection:
                connection.settimeout(0.2)
                if connection.connect_ex(address) == 0:
                    occupied.append(port)
                    break
    return occupied


def group_alive(pgid):
    try:
        os.killpg(pgid, 0)
        return True
    except ProcessLookupError:
        return False


def stop_owned_group(process, profile):
    """Gracefully stop the private launcher, then only its own process group.

    A distinct session prevents signals reaching this runner, the normal app or
    another test. Prefer the private zsh launcher so its acknowledged save and
    child shutdown traps can run before terminating any lingering Cocoa alert.
    """
    actions = []
    pidfile = profile / 'launcher.lock/pid'
    if pidfile.is_file():
        try:
            launcher_pid = int(pidfile.read_text().strip())
            if os.getpgid(launcher_pid) == process.pid:
                os.kill(launcher_pid, signal.SIGTERM)
                actions.append({'signal': 'TERM private launcher', 'pid': launcher_pid})
        except (ValueError, ProcessLookupError):
            pass
    if actions:
        deadline = time.monotonic() + 25
        while group_alive(process.pid) and time.monotonic() < deadline:
            process.poll()
            time.sleep(0.2)
    if group_alive(process.pid):
        try:
            os.killpg(process.pid, signal.SIGTERM)
            actions.append({'signal': 'TERM owned group', 'pgid': process.pid})
        except ProcessLookupError:
            pass
        deadline = time.monotonic() + 10
        while group_alive(process.pid) and time.monotonic() < deadline:
            process.poll()
            time.sleep(0.2)
    if group_alive(process.pid):
        try:
            os.killpg(process.pid, signal.SIGKILL)
            actions.append({'signal': 'KILL owned group', 'pgid': process.pid})
        except ProcessLookupError:
            pass
    process.wait(timeout=10)
    deadline = time.monotonic() + 5
    while group_alive(process.pid) and time.monotonic() < deadline:
        time.sleep(0.2)
    return {'actions': actions, 'owned_group_stopped': not group_alive(process.pid),
            'ports_still_occupied': occupied_ports()}


class AcceptanceStopped(RuntimeError):
    pass


class Matrix:
    def __init__(self, args, frozen, helper):
        self.args, self.frozen, self.helper = args, frozen, helper
        self.freeze_hash = digest(args.freeze)
        self.report_path = OUT / f'{args.label}-matrix.json'
        self.events_path = OUT / f'{args.label}-events.jsonl'
        self.stop_signal = None
        self.current = None
        self.report = {
            'schema': 1, 'started_utc': utc(), 'status': 'preflight', 'passed': False,
            'app': frozen['app'], 'freeze_manifest': str(args.freeze),
            'freeze_sha256': self.freeze_hash, 'package_sha256': frozen['package_sha256'],
            'helper_sha256': frozen['helper_sha256'], 'runner_sha256': digest(SELF),
            'race_order': list(helper.STARTING_ARMIES), 'expected_races': len(helper.STARTING_ARMIES),
            'normal_saves_before': normal_saves(), 'races': [],
            'scope': 'Serial original race-prompt/new-army/save/reload acceptance in private profiles. '
                     'Read-only game and WebKit snapshots; no OS input or physical mobile-input claim. '
                     'Panel presence is checked automatically; pixel/visual review remains separate.',
        }

    def save(self, event, **fields):
        self.report['updated_utc'] = utc()
        self.report['completed_races'] = sum(r['status'] == 'passed' for r in self.report['races'])
        atomic_json(self.report_path, self.report)
        with self.events_path.open('a') as stream:
            stream.write(json.dumps({'utc': utc(), 'event': event, **fields}) + '\n')

    def guard(self):
        if self.stop_signal:
            raise AcceptanceStopped(f'Received signal {self.stop_signal}')
        if digest(self.args.freeze) != self.freeze_hash:
            raise AcceptanceStopped('Freeze manifest changed')
        if digest(HELPER) != self.frozen['helper_sha256'] or digest(SELF) != self.frozen['runner_sha256']:
            raise AcceptanceStopped('Acceptance helper or runner changed after freeze')
        if normal_saves() != self.report['normal_saves_before']:
            raise AcceptanceStopped('Normal save hashes changed; matrix stopped without writing them')
        current = inventory(Path(self.frozen['app']))
        if current != self.frozen['entries']:
            changed = sorted(k for k in current.keys() | self.frozen['entries'].keys()
                             if current.get(k) != self.frozen['entries'].get(k))
            raise AcceptanceStopped(f'Frozen app changed: {changed[:12]}')

    def preserve_phase(self, work, phase):
        """Retain raw private saves before helper postconditions/temp cleanup.

        A clean process exit can still fail unit-count, acknowledgment or panel
        assertions later in check_app.main. Always retain each phase so those
        failures have the same original graphs/logs as an immediate exception.
        """
        destination = OUT / f'{self.current["label"]}-{phase}-profile-evidence'
        destination.mkdir(exist_ok=False)
        for relative in ('profile/reports', 'profile/world/units', 'profile/world/ErrorLog.txt',
                         'profile/launcher.lock', f'{phase}-native-probe'):
            source = work / relative
            target = destination / relative
            if source.is_dir():
                shutil.copytree(source, target)
            elif source.is_file():
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
        atomic_json(destination / 'evidence-manifest.json', {
            str(p.relative_to(destination)): digest(p) for p in sorted(destination.rglob('*')) if p.is_file()})
        return str(destination)

    def product_errors(self, profile):
        problems = {}
        for name in ('reports/launcher.log', 'reports/server.log', 'reports/client.log', 'world/ErrorLog.txt'):
            path = profile / name
            errors = self.helper.error_lines(path.read_text(errors='replace')) if path.exists() else []
            if errors:
                problems[name] = errors
        error = profile / 'reports/save-request.error'
        if error.exists():
            problems['reports/save-request.error'] = [error.read_text(errors='replace')]
        return problems

    def run_phase(self, command, env, work, snapshot, probe=None):
        """Drop-in launch monitor for the otherwise unchanged check_app helper."""
        phase = 'new_army' if env.get('DM_TEST_RACE') else 'reload'
        profile = Path(env['DM_STANDALONE_DATA_DIR'])
        if not profile.resolve().is_relative_to(work.resolve()) or profile.resolve() == NORMAL.parent.parent:
            raise AcceptanceStopped('Expected a disposable test profile')
        self.guard()
        busy = occupied_ports()
        if busy:
            raise AcceptanceStopped(f'Package test ports already in use: {busy}')
        state = {'phase': phase, 'started_utc': utc(), 'status': 'running',
                 'profile': str(profile), 'snapshot': str(snapshot), 'command': command,
                 'frozen_package_verified_before': True,
                 'native_panel_capture_requested': False}
        self.current['phase_monitor'].append(state)
        self.save('phase_started', race=self.current['race'], phase=phase)
        process = None
        failure = None
        started = time.monotonic()
        try:
            process = subprocess.Popen(command, env=env, cwd=work, start_new_session=True)
            state['pid'] = state['owned_process_group'] = process.pid
            next_scan = 0
            while process.poll() is None:
                if self.stop_signal:
                    raise AcceptanceStopped(f'Received signal {self.stop_signal}')
                now = time.monotonic()
                if now - started >= 300:
                    raise AcceptanceStopped(f'{phase} exceeded the helper\'s 300-second deadline')
                if probe is not None and not state['native_panel_capture_requested'] and snapshot.is_file():
                    (probe / 'capture-web.txt').write_text('hud')
                    state['native_panel_capture_requested'] = True
                if now >= next_scan:
                    problems = self.product_errors(profile)
                    if problems:
                        state['product_errors'] = problems
                        raise AcceptanceStopped(f'Product error during {phase}; see retained phase logs')
                    next_scan = now + 1
                time.sleep(0.25)
            state['exit_code'] = process.returncode
            problems = self.product_errors(profile)
            if problems:
                state['product_errors'] = problems
                raise AcceptanceStopped(f'Product error at {phase} shutdown; see retained phase logs')
            if process.returncode:
                raise AcceptanceStopped(f'{phase} exited with code {process.returncode}')
            if group_alive(process.pid):
                raise AcceptanceStopped(f'{phase} launcher exited but left private child processes')
            self.guard()
            state['frozen_package_verified_after'] = True
            state['status'] = 'finished'
            return process.returncode
        except BaseException as error:
            failure = error
            state.update(status='failed', error=f'{type(error).__name__}: {error}')
            raise
        finally:
            cleanup_error = None
            if process is not None:
                try:
                    state['cleanup'] = stop_owned_group(process, profile)
                    if not state['cleanup']['owned_group_stopped'] or state['cleanup']['ports_still_occupied']:
                        cleanup_error = AcceptanceStopped('Private phase cleanup incomplete; matrix will not continue')
                except Exception as error:
                    state['cleanup'] = {'error': f'{type(error).__name__}: {error}'}
                    cleanup_error = error
            if cleanup_error:
                state.update(status='failed', cleanup_error=str(cleanup_error))
            state['finished_utc'] = utc()
            state['seconds'] = round(time.monotonic() - started, 1)
            state['private_evidence'] = self.preserve_phase(work, phase)
            self.save('phase_finished', race=self.current['race'], phase=phase, status=state['status'])
            if cleanup_error and failure is None:
                raise cleanup_error

    def run(self):
        self.save('matrix_preflight')
        try:
            self.guard()
            if len(self.helper.STARTING_ARMIES) != 13:
                raise AcceptanceStopped('Expected the original thirteen starting races')
            self.report['status'] = 'running'
            self.helper.run_phase = self.run_phase
            for index, race in enumerate(self.helper.STARTING_ARMIES, 1):
                self.guard()
                label = f'{self.args.label}-{index:02d}-{race.lower()}'
                row = {'race': race, 'label': label, 'status': 'running', 'started_utc': utc(),
                       'expected_starting_units': self.helper.STARTING_ARMIES[race], 'phase_monitor': []}
                self.current = row
                self.report['races'].append(row)
                self.save('race_started', race=race, index=index)
                print(f'[{index}/13] {race}: original new army, save and reload', flush=True)
                original_argv = sys.argv
                log_path = OUT / f'{label}-runner.log'
                code = 0
                try:
                    sys.argv = [str(HELPER), '--app', self.frozen['app'], '--race', race,
                                '--label', label, '--native-panels']
                    with log_path.open('x') as log, contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
                        try:
                            self.helper.main()
                        except SystemExit as error:
                            code = error.code or 0
                finally:
                    sys.argv = original_argv
                checks_path = OUT / f'{label}-checks.json'
                row['helper_report'] = str(checks_path)
                checks = json.loads(checks_path.read_text()) if checks_path.exists() else {}
                self.guard()
                row.update(finished_utc=utc(), helper_exit_code=code,
                           helper_report_sha256=digest(checks_path) if checks_path.exists() else None,
                           native_panel_directories={p: v.get('native_panels', {}).get('manifest')
                                                     for p, v in checks.get('phases', {}).items()})
                if code or not checks.get('passed'):
                    row['status'] = 'failed'
                    raise AcceptanceStopped(f'{race} acceptance failed; remaining races were not launched')
                row['status'] = 'passed'
                self.save('race_passed', race=race, index=index)
                print(f'[{index}/13] {race}: PASS', flush=True)
            self.guard()
            self.report.update(status='completed', passed=True)
        except BaseException as error:
            self.report.update(status='stopped' if self.stop_signal else 'failed',
                               error=f'{type(error).__name__}: {error}', traceback=traceback.format_exc())
            if self.current and self.current['status'] == 'running':
                self.current.update(status='failed', finished_utc=utc(), error=str(error))
            print(self.report['error'], file=sys.stderr, flush=True)
        finally:
            self.report['finished_utc'] = utc()
            self.report['normal_saves_after'] = normal_saves()
            self.report['normal_saves_unchanged'] = self.report['normal_saves_before'] == self.report['normal_saves_after']
            try:
                self.report['frozen_package_unchanged'] = inventory(Path(self.frozen['app'])) == self.frozen['entries']
            except Exception as error:
                self.report['frozen_package_unchanged'] = False
                self.report['final_package_check_error'] = str(error)
            self.report['passed'] = self.report['passed'] and self.report['normal_saves_unchanged'] and self.report['frozen_package_unchanged']
            if not self.report['passed'] and self.report['status'] == 'completed':
                self.report['status'] = 'failed'
            self.report['unlaunched_races'] = [race for race in self.helper.STARTING_ARMIES
                                             if race not in {r['race'] for r in self.report['races']}]
            self.report['evidence_sha256'] = {
                str(p): digest(p) for entry in sorted(OUT.glob(f'{self.args.label}-*'))
                for p in ([entry] if entry.is_file() else sorted(entry.rglob('*')))
                if p.is_file() and p not in (self.report_path, self.events_path)}
            self.save('matrix_finished', status=self.report['status'], passed=self.report['passed'])
        return 0 if self.report['passed'] else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    freeze = commands.add_parser('freeze', help='Hash the final app and helpers; does not launch anything')
    freeze.add_argument('--app', type=Path, required=True)
    freeze.add_argument('--manifest', type=Path, required=True)
    run = commands.add_parser('run', help='Launch all thirteen races serially after the native slot is released')
    run.add_argument('--freeze', type=Path, required=True)
    run.add_argument('--label', required=True, help='Unique report prefix; existing evidence is never overwritten')
    args = parser.parse_args()
    if args.command == 'freeze':
        app = args.app.resolve(strict=True)
        if not next(((app)/'Contents/MacOS'/n for n in ('BannersOfTheDeep', 'LandOfLords', 'DungeonMasterRemastered') if ((app)/'Contents/MacOS'/n).is_file()), (app)/'Contents/MacOS/BannersOfTheDeep').is_file():   # LandOfLords since the rename
            parser.error('app must be the packaged Dungeon Master Remastered app')
        entries = inventory(app)
        record = {'schema': 1, 'created_utc': utc(), 'app': str(app), 'entries': entries,
                  'package_sha256': canonical_digest(entries), 'helper': str(HELPER),
                  'helper_sha256': digest(HELPER), 'runner': str(SELF), 'runner_sha256': digest(SELF),
                  'race_order': list(load_helper().STARTING_ARMIES),
                  'scope': 'Read-only package freeze. No app launched; run requires a released exclusive native slot.'}
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        with args.manifest.open('x') as stream:
            stream.write(json.dumps(record, indent=2) + '\n')
        args.manifest.chmod(0o444)
        print(json.dumps({'manifest': str(args.manifest.resolve()), 'package_sha256': record['package_sha256'],
                          'entries': len(entries), 'launched': False}))
        return 0
    if not re.fullmatch(r'[A-Za-z0-9_-]+', args.label):
        parser.error('label must contain only letters, digits, underscores and hyphens')
    args.freeze = args.freeze.resolve(strict=True)
    frozen = json.loads(args.freeze.read_text())
    if frozen.get('schema') != 1 or canonical_digest(frozen['entries']) != frozen['package_sha256']:
        parser.error('invalid freeze manifest')
    OUT.mkdir(exist_ok=True)
    if any(OUT.glob(f'{args.label}-*')):
        parser.error('label has existing evidence; choose a new label')
    matrix = Matrix(args, frozen, load_helper())
    handlers = {}
    for sig in (signal.SIGINT, signal.SIGTERM):
        handlers[sig] = signal.signal(sig, lambda number, frame: setattr(matrix, 'stop_signal', number))
    try:
        return matrix.run()
    finally:
        for sig, handler in handlers.items():
            signal.signal(sig, handler)


if __name__ == '__main__':
    raise SystemExit(main())
