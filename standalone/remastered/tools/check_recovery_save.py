#!/usr/bin/env python3
"""Prepare, then separately run a copied-backup load/save/reload acceptance.

No restore into the normal profile, new army, game edits or input injection.
The run command needs the exclusive native test slot; prepare never launches.
"""
import argparse
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
import subprocess
import tempfile
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
SELF = Path(__file__).resolve()
MATRIX = ROOT / 'tools/check_starting_races.py'
APP_HELPER = ROOT / 'tools/check_app.py'
NORMAL_WORLD = Path.home() / 'Library/Application Support/Dungeon Master Remastered/world'
BACKUP = ROOT / 'restore-points/before-border-menu-animation-20261016/player-units/localhost@kiwi_save.sav'
BACKUP_SHA = '9f5cf0944ea917fe20385eb51d62e3666437046cb926a04c42ded34523560c09'
NORMAL_SHA = '368992a781598c7703b64091935e081666dd9052808ee4d881ba5fa98d74fac4'
USERNAME = 'Kiwi'
SAVE_NAME = 'localhost@kiwi_save.sav'
# These retain historical values, including the backup's earned/previously
# saved capacities. No fixture stat, tool, material or position is supplied.
UNIT_FIELDS = ('name', 'Race', 'SubRace', 'HP', 'MAXHP', 'Level', 'EXP',
               'IsRoyal', 'savedx', 'savedy', 'savedz', 'weight', 'weightmax',
               'Strength', 'Agility', 'Defence', 'GoingToDie', 'Caged', 'InHole',
               'HasLeftLeg', 'HasRightLeg', 'HoldingWeapon', 'WearingShield',
               'WearingChest', 'WearingHelmet', 'WearingLegs', 'WearingBack',
               'WearingCape', 'WearingLeftArm', 'WearingRightArm', 'WearingRing',
               'WearingCrown', 'remaster_job')
ITEM_FIELDS = ('name', 'Race', 'SubRace', 'ItemType', 'weight', 'suffix',
               'Content', 'Content2', 'Content3', 'Skinned', 'HP', 'MAXHP',
               'Level', 'Strength', 'Agility', 'Defence', 'DamageType',
               'WeaponDamageMin', 'WeaponDamageMax', 'ArmourSkill',
               'Poisoned', 'PoisonContent', 'HasPersonIn', 'EggContent')


def utc():
    return datetime.now(timezone.utc).isoformat()


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def normal_hashes():
    return {str(p.relative_to(NORMAL_WORLD)): digest(p)
            for p in sorted(NORMAL_WORLD.rglob('*.sav'))} if NORMAL_WORLD.exists() else {}


def graph_summary(path):
    """Compare persisted identity by roster/content paths, never graph ID numbers.

    IDs are local to one serialization. Ordered nodes, their stable fields and
    alias paths detect lost/duplicated cargo without pretending IDs survive a
    process restart. All graph references are range checked, including those
    outside the roster projection. Raw saves remain the complete evidence.
    """
    nodes = json.loads(path.read_text())['_nodes']
    table = nodes['.opendream_graph']['Objects']

    def reference(value):
        if not isinstance(value, dict) or value.get('$type') != 'graphref':
            raise ValueError('Expected a graph reference')
        index = value.get('Id')
        if not isinstance(index, int) or isinstance(index, bool) or not 0 <= index < len(table):
            raise ValueError(f'Dangling graph reference: {index!r}')
        return index

    references = 0

    def validate(value):
        nonlocal references
        if isinstance(value, dict):
            if value.get('$type') == 'graphref':
                reference(value)
                references += 1
            for child in value.values():
                validate(child)
        elif isinstance(value, list):
            for child in value:
                validate(child)

    validate(nodes)

    def scalar(fields, key):
        value = fields.get(key)
        if value is None:
            return {'missing': True}
        if value.get('$type') != 'primitive':
            raise ValueError(f'Expected scalar {key}, got {value.get("$type")}')
        return value['Value']['Value']

    roster = table[reference(nodes['UnitList'])]['Values']
    seen = {}
    identities = []

    def atom(ref, path, keys):
        index = reference(ref)
        if index in seen:
            return {'alias': seen[index]}
        seen[index] = path
        entry = table[index]
        if not isinstance(entry.get('Type'), str):
            raise ValueError(f'Untyped roster/content node at {path}')
        fields = entry['Fields']['_nodes']
        identities.append({'path': path, 'graph_id': index, 'type': entry['Type']})
        contents = table[reference(fields['contents'])]['Values']
        return {'type': entry['Type'], 'fields': {k: scalar(fields, k) for k in keys},
                'contents': [atom(r, f'{path}/contents/{i}', ITEM_FIELDS)
                             for i, r in enumerate(contents)]}

    units = [atom(r, f'roster/{i}', UNIT_FIELDS) for i, r in enumerate(roster)]
    return {'key': scalar(nodes, 'key'), 'race': scalar(nodes, 'Race'),
            'camera': [scalar(nodes, k) for k in ('savedx', 'savedy', 'savedz')],
            'units': units, 'identities': identities, 'graph_objects': len(table),
            'validated_graph_references': references}


def comparable(summary):
    return {k: summary[k] for k in ('key', 'race', 'camera', 'units')}


def differences(expected, actual, path=''):
    if type(expected) is not type(actual):
        return [{'path': path, 'expected': expected, 'actual': actual}]
    if isinstance(expected, dict):
        result = []
        for key in sorted(expected.keys() | actual.keys()):
            if key not in expected or key not in actual:
                result.append({'path': path+'/'+key, 'expected': expected.get(key), 'actual': actual.get(key)})
            else:
                result.extend(differences(expected[key], actual[key], path+'/'+key))
        return result
    if isinstance(expected, list):
        if len(expected) != len(actual):
            return [{'path': path, 'expected_length': len(expected), 'actual_length': len(actual)}]
        return [change for i, (a, b) in enumerate(zip(expected, actual))
                for change in differences(a, b, path+'/'+str(i))]
    return [] if expected == actual else [{'path': path, 'expected': expected, 'actual': actual}]


def busy_ports():
    occupied = []
    for port in (12151, 25651):
        # The game is UDP, whereas local save/status connections use TCP.
        for family, address in ((socket.AF_INET, ('127.0.0.1', port)),
                                (socket.AF_INET6, ('::1', port))):
            with socket.socket(family, socket.SOCK_STREAM) as sock:
                sock.settimeout(0.2)
                if sock.connect_ex(address) == 0:
                    occupied.append({'port': port, 'transport': 'TCP'})
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            try:
                sock.bind(('127.0.0.1', port))
            except OSError:
                occupied.append({'port': port, 'transport': 'UDP'})
    return occupied


def prepare(args, matrix, app_helper):
    app = args.app.resolve(strict=True)
    backup = args.backup.resolve(strict=True)
    if digest(backup) != BACKUP_SHA or backup.name != SAVE_NAME:
        raise ValueError('This acceptance is restricted to the reviewed preferred three-Orc backup')
    if not next(((app)/'Contents/MacOS'/n for n in ('BannersOfTheDeep', 'LandOfLords', 'DungeonMasterRemastered') if ((app)/'Contents/MacOS'/n).is_file()), (app)/'Contents/MacOS/BannersOfTheDeep').is_file():   # LandOfLords since the rename
        raise ValueError('Expected the final packaged Remastered app')
    if any((app/'Contents/Resources/game/world').rglob('*.sav')):
        raise ValueError('Packaged mutable world contains saves that could overwrite the private seed')
    destination = args.manifest.resolve()
    if any(destination.is_relative_to(p) for p in (NORMAL_WORLD.parent, app, backup.parent)):
        raise ValueError('Preparation evidence must be outside app, original backup and normal profile')
    summary = graph_summary(backup)
    if summary['key'] != 'localhost@Kiwi' and summary['key'] != 'localhost@kiwi':
        raise ValueError(f'Unexpected original key: {summary["key"]}')
    if len(summary['units']) != 3 or any(u['type'] != '/mob/Monsters/Orc' for u in summary['units']):
        raise ValueError('Expected the original three-Orc roster')
    entries = matrix.inventory(app)
    record = {'schema': 1, 'created_utc': utc(), 'app': str(app),
              'entries': entries, 'package_sha256': matrix.canonical_digest(entries),
              'build_hashes': app_helper.build_hashes(app), 'backup': str(backup),
              'backup_sha256': digest(backup), 'backup_summary': summary,
              'username': USERNAME, 'save_name': SAVE_NAME,
              'helpers': {str(p): digest(p) for p in (SELF, MATRIX, APP_HELPER)},
              'normal_saves_at_preparation': normal_hashes(),
              'scope': 'Preparation only; no app, server, client, restore or gameplay input.'}
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    with args.manifest.open('x') as stream:
        stream.write(json.dumps(record, indent=2)+'\n')
    args.manifest.chmod(0o444)
    print(json.dumps({'prepared': str(args.manifest.resolve()), 'launched': False,
                      'package_sha256': record['package_sha256'], 'roster': 3}))


class Recovery:
    def __init__(self, args, matrix, app_helper):
        self.args, self.matrix, self.app_helper = args, matrix, app_helper
        self.frozen = json.loads(args.freeze.read_text())
        if self.frozen.get('schema') != 1 or matrix.canonical_digest(self.frozen['entries']) != self.frozen['package_sha256']:
            raise ValueError('Invalid preparation manifest')
        self.app = Path(self.frozen['app'])
        self.backup = Path(self.frozen['backup'])
        if self.frozen['backup_sha256'] != BACKUP_SHA or digest(self.backup) != BACKUP_SHA:
            raise ValueError('Wrong or changed preferred backup')
        self.out = args.output.resolve()
        if any(self.out.is_relative_to(p) for p in (NORMAL_WORLD.parent, self.app, self.backup.parent)):
            raise ValueError('Evidence must be outside app, original backup and normal profile')
        self.out.mkdir(parents=True, exist_ok=False)
        self.freeze_hash = digest(args.freeze)
        self.stop_signal = None
        self.cleanup_complete = True
        self.evidence_complete = True
        self.report = {'schema': 1, 'started_utc': utc(), 'passed': False,
                       'status': 'preflight', 'freeze': str(args.freeze.resolve()),
                       'freeze_sha256': self.freeze_hash, 'package_sha256': self.frozen['package_sha256'],
                       'backup': str(self.backup), 'backup_sha256': BACKUP_SHA,
                       'normal_saves_before': normal_hashes(), 'phases': [],
                       'scope': 'Two unchanged packaged launches loading the original copied three-Orc save. '
                                'No new army, stats/tools/material grants, gameplay/OS input or normal-profile restore. '
                                'Identity means ordered persisted roster/cargo values and distinct/alias graph topology; '
                                'numeric serialization IDs are not cross-process identities. Natural drift fails strict checks.'}
        self.work = None

    def save_report(self):
        self.matrix.atomic_json(self.out/'checks.json', self.report)

    def guard(self):
        if self.stop_signal:
            raise RuntimeError(f'Received signal {self.stop_signal}')
        if digest(self.args.freeze) != self.freeze_hash:
            raise RuntimeError('Preparation manifest changed')
        for name, expected in self.frozen['helpers'].items():
            if digest(Path(name)) != expected:
                raise RuntimeError(f'Checker dependency changed: {name}')
        if digest(self.backup) != BACKUP_SHA:
            raise RuntimeError('Read-only backup changed')
        if normal_hashes() != self.report['normal_saves_before']:
            raise RuntimeError('Normal saves changed; stop without modifying them')
        if self.matrix.inventory(self.app) != self.frozen['entries']:
            raise RuntimeError('Frozen app changed')

    def errors(self, data):
        result = {}
        for name in ('reports/launcher.log', 'reports/server.log', 'reports/client.log', 'world/ErrorLog.txt'):
            p = data/name
            found = self.app_helper.error_lines(p.read_text(errors='replace')) if p.exists() else []
            if found:
                result[name] = found
        p = data/'reports/save-request.error'
        if p.exists():
            result[str(p.relative_to(data))] = [p.read_text(errors='replace')]
        return result

    def phase(self, name, data, expected_seed):
        self.guard()
        seed_hash = digest(data/'world/units'/SAVE_NAME)
        if seed_hash != expected_seed:
            raise RuntimeError('Private input differs from the original/previous saved graph')
        if busy_ports():
            raise RuntimeError(f'Package ports occupied; no launch: {busy_ports()}')
        dest = self.out/name
        dest.mkdir()
        probe = self.work/(name+'-probe')
        probe.mkdir()
        snapshot = dest/'game.png'
        # All request-capable DM flags inherited from other fixtures are removed.
        env = {k: v for k, v in os.environ.items()
               if not k.startswith(('DM_', 'ROBUST_', 'DOTNET_', 'DYLD_'))}
        env.update(PATH='/usr/bin:/bin:/usr/sbin:/sbin', DM_STANDALONE_DATA_DIR=str(data),
                   DM_GAME_SNAPSHOT=str(snapshot), DM_NATIVE_UI_PROBE=str(probe))
        assert 'DM_TEST_RACE' not in env
        command = [str(next(((self.app)/'Contents/MacOS'/n for n in ('BannersOfTheDeep', 'LandOfLords', 'DungeonMasterRemastered') if ((self.app)/'Contents/MacOS'/n).is_file()), (self.app)/'Contents/MacOS/BannersOfTheDeep')),   # LandOfLords since the rename
                   '--username', USERNAME, '--smoke-seconds', '30']
        row = {'name': name, 'started_utc': utc(), 'command': command,
               'input_save_sha256': seed_hash,
               'private_profile': str(data), 'dm_environment': {k:v for k,v in env.items() if k.startswith('DM_')},
               'passed': False}
        self.report['phases'].append(row)
        self.save_report()
        process = None
        process_log = (dest/'process.log').open('x')
        start = time.monotonic()
        failure = None
        try:
            (data/'world/ErrorLog.txt').unlink(missing_ok=True)
            process = subprocess.Popen(command, env=env, cwd=self.work, start_new_session=True,
                                       stdout=process_log, stderr=subprocess.STDOUT)
            row['pid'] = row['owned_process_group'] = process.pid
            requested = False
            while process.poll() is None:
                if self.stop_signal or time.monotonic()-start > 240:
                    raise RuntimeError('Interrupted or exceeded 240-second phase limit')
                if snapshot.is_file() and not requested:
                    (probe/'capture-web.txt').write_text('hud')
                    requested = True
                errors = self.errors(data)
                if errors:
                    row['errors'] = errors
                    raise RuntimeError('Product error; see preserved phase logs')
                time.sleep(0.25)
            row['exit_code'] = process.returncode
            if process.returncode != 0 or self.matrix.group_alive(process.pid):
                raise RuntimeError('Launcher failed or left a private child process')
        except BaseException as error:
            failure = error
            row['exception'] = f'{type(error).__name__}: {error}'
        finally:
            if process is not None:
                try:
                    row['cleanup'] = self.matrix.stop_owned_group(process, data)
                    if not row['cleanup']['owned_group_stopped'] or row['cleanup']['ports_still_occupied']:
                        self.cleanup_complete = False
                        raise RuntimeError('Private process cleanup incomplete')
                except Exception as error:
                    self.cleanup_complete = False
                    row['cleanup_error'] = str(error)
                    failure = failure or error
            process_log.close()
            # Retain both successful and failed raw graphs BEFORE temp cleanup.
            # If copying fails, retain the entire temp directory for recovery.
            self.evidence_complete = False
            for relative in ('reports', 'world/units', 'world/players', 'world/ErrorLog.txt', 'launcher.lock'):
                source = data/relative
                target = dest/'profile'/relative
                if source.is_dir():
                    shutil.copytree(source, target)
                elif source.is_file():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, target)
            shutil.copytree(probe, dest/'native-probe')
            self.evidence_complete = True
            row['seconds'] = round(time.monotonic()-start, 2)
            row['finished_utc'] = utc()
            self.save_report()
        if failure:
            raise failure
        read = lambda p: p.read_text(errors='replace') if p.is_file() else ''
        logs = {n:read(data/'reports'/n) for n in ('launcher.log','server.log','client.log')}
        save = data/'world/units'/SAVE_NAME
        summary = graph_summary(save)
        self.matrix.atomic_json(dest/'graph-summary.json', summary)
        changed = differences(comparable(self.frozen['backup_summary']), comparable(summary))
        row.update(saved_graph_sha256=digest(save), saved_unit_count=len(summary['units']),
                   graph_differences=changed, errors=self.errors(data),
                   ack=read(data/'reports/save-request.ack').strip(),
                   panels=self.app_helper.preserve_panels(probe, dest/'native-panels'))
        row['checks'] = {
            'exact_roster_cargo_coordinates_and_fields': not changed,
            'three_living_original_orcs': len(summary['units']) == 3 and all(
                u.get('type') == '/mob/Monsters/Orc' and u['fields']['HP'] > 0 for u in summary['units']),
            'server_ready': ' -> Ready' in logs['server.log'],
            'client_in_game': 'Runlevel changed to: InGame' in logs['client.log'],
            'no_new_army_smoke_action': 'smoke test requested race' not in logs['client.log']
                                        and 'smoke test chose' not in logs['client.log'],
            'acknowledged_save': read(data/'reports/save-status').strip() == 'saved'
                                  and bool(re.fullmatch(r'[0-9A-Fa-f-]{36}', row['ack']))
                                  and 'Local host saved units before shutdown' in logs['server.log'],
            'no_save_error': not (data/'reports/save-request.error').exists(),
            'no_launcher_lock': not (data/'launcher.lock').exists(),
            'clean_logs': not row['errors'], 'framebuffer': snapshot.is_file(),
            'read_only_native_panels': row['panels']['passed'],
            'private_bootstrap_matches_package': digest(data/'client/Space Station 14.app/Contents/Resources/Robust.Client.dll')
                                                  == self.frozen['build_hashes']['native_bootstrap'],
            'only_expected_unit_save': sorted(p.name for p in (data/'world/units').glob('*.sav')) == [SAVE_NAME],
            'private_seed_is_original_or_previous_phase': seed_hash == expected_seed,
        }
        self.guard()
        row['passed'] = all(row['checks'].values())
        self.save_report()
        if not row['passed']:
            raise RuntimeError(f'{name} failed strict acceptance; no later launch')

    def run(self):
        self.save_report()
        try:
            self.guard()
            if self.report['normal_saves_before'].get('units/'+SAVE_NAME) != NORMAL_SHA:
                raise RuntimeError('Normal Kiwi baseline changed; re-review recovery context before launching')
            if busy_ports():
                raise RuntimeError(f'Package ports occupied: {busy_ports()}')
            self.work = Path(tempfile.mkdtemp(prefix='dm-recovery-private-')).resolve()
            data = self.work/'profile'
            if data.is_relative_to(NORMAL_WORLD.parent) or NORMAL_WORLD.is_relative_to(data):
                raise RuntimeError('Unsafe private profile path')
            units = data/'world/units'
            units.mkdir(parents=True)
            (data/'world/players').mkdir()
            # Explicitly skip the package's optional personal seed-save import.
            (data/'initial-saves-imported').touch()
            shutil.copy2(self.backup, units/SAVE_NAME)
            if digest(units/SAVE_NAME) != BACKUP_SHA:
                raise RuntimeError('Private seed copy differs from original backup')
            shutil.copy2(self.backup, self.out/'original-input-copy.sav')
            self.matrix.atomic_json(self.out/'original-graph-summary.json', self.frozen['backup_summary'])
            self.report.update(status='running', private_work=str(self.work))
            self.phase('load_existing', data, BACKUP_SHA)
            previous = digest(units/SAVE_NAME)
            self.report['reload_seed_sha256'] = previous
            if previous != self.report['phases'][0]['saved_graph_sha256']:
                raise RuntimeError('First private saved graph changed before reload')
            self.phase('reload_saved', data, previous)
            acknowledgments = [p['ack'] for p in self.report['phases']]
            self.report['fresh_save_acknowledgments'] = len(set(acknowledgments)) == 2
            self.report.update(status='completed', passed=self.report['fresh_save_acknowledgments'])
        except BaseException as error:
            self.report.update(status='failed', error=f'{type(error).__name__}: {error}', traceback=traceback.format_exc())
        finally:
            try:
                self.report['backup_unchanged'] = digest(self.backup) == BACKUP_SHA
                self.report['normal_saves_after'] = normal_hashes()
                self.report['normal_saves_unchanged'] = self.report['normal_saves_before'] == self.report['normal_saves_after']
                self.report['package_unchanged'] = self.matrix.inventory(self.app) == self.frozen['entries']
                self.report['helpers_unchanged'] = all(digest(Path(k)) == v for k,v in self.frozen['helpers'].items())
                self.report['passed'] = self.report['passed'] and all(self.report[k] for k in
                    ('backup_unchanged','normal_saves_unchanged','package_unchanged','helpers_unchanged'))
            except Exception as error:
                self.report.update(passed=False, final_integrity_error=str(error))
            if self.work and self.cleanup_complete and self.evidence_complete:
                try:
                    shutil.rmtree(self.work)
                    self.report['private_work_removed_after_evidence'] = True
                except Exception as error:
                    self.report.update(passed=False, private_cleanup_error=str(error),
                                       private_work_retained_for_cleanup=str(self.work))
            elif self.work:
                self.report['private_work_retained_for_incomplete_cleanup_or_preservation'] = str(self.work)
            self.report['finished_utc'] = utc()
            try:
                self.report['evidence_sha256'] = {str(p.relative_to(self.out)): digest(p)
                    for p in sorted(self.out.rglob('*')) if p.is_file() and p.name != 'checks.json'}
            except Exception as error:
                self.report.update(passed=False, evidence_hash_error=str(error))
            if not self.report['passed']:
                self.report['status'] = 'failed'
            self.save_report()
        print(json.dumps({'report': str(self.out/'checks.json'), 'passed': self.report['passed']}))
        return 0 if self.report['passed'] else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    prep = commands.add_parser('prepare', help='Hash app/backup/helpers only; does not launch')
    prep.add_argument('--app', type=Path, required=True)
    prep.add_argument('--backup', type=Path, default=BACKUP)
    prep.add_argument('--manifest', type=Path, required=True)
    run = commands.add_parser('run', help='Two private launches; requires the released native slot')
    run.add_argument('--freeze', type=Path, required=True)
    run.add_argument('--output', type=Path, required=True, help='New evidence directory; never overwritten')
    args = parser.parse_args()
    matrix = load_module('recovery_matrix', MATRIX)
    app_helper = load_module('recovery_check_app', APP_HELPER)
    if args.command == 'prepare':
        prepare(args, matrix, app_helper)
        return 0
    recovery = Recovery(args, matrix, app_helper)
    old_handlers = {sig: signal.signal(sig, lambda n, f: setattr(recovery, 'stop_signal', n))
                    for sig in (signal.SIGINT, signal.SIGTERM)}
    try:
        return recovery.run()
    finally:
        for sig, old in old_handlers.items():
            signal.signal(sig, old)


if __name__ == '__main__':
    raise SystemExit(main())
