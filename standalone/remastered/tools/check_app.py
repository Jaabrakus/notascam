#!/usr/bin/env python3
"""Launch the packaged Remastered app twice (new army + save, then reload) with a
temporary save folder; record a game screenshot and any errors."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
ERROR_LINE = re.compile(r'^.*(?:\[(?:ERRO|FATL)\]|Exception occurred:|runtime error).*$', re.IGNORECASE | re.MULTILINE)
# Original Restart choices and starting counts; rare unlocks are not injected.
STARTING_ARMIES = {
    'Human': 3, 'Dwarf': 3, 'Elf': 3, 'Orc': 3, 'Goblin': 3,
    'Lizardman': 3, 'Frogman': 3, 'Kobold': 5, 'Ratman': 5,
    'Svartalfar': 1, 'Spider': 1, 'Dragon': 1, 'Devourer': 1,
}


def error_lines(log):
    # OpenDream redirects game exceptions to world/ErrorLog.txt, using a
    # different prefix from BYOND's "runtime error". Check both formats.
    return ERROR_LINE.findall(log)


def build_hashes(app):
    game = app/'Contents/Resources/game'
    files = {
        'game': game/'world/Cave Crawlers.json',
        'runtime': game/'runtime/server/Resources/Assemblies/OpenDreamRuntime.dll',
        'client': game/'runtime/server/Content.Client.zip',
        'native_bootstrap': game/'runtime/client/Space Station 14.app/Contents/Resources/Robust.Client.dll',
        'hud': game/'world/Interface/remastered.html',
        'webview': game/'runtime/webview-webkit/Robust.Client.WebView.dll',
        'native_bridge': game/'runtime/webview-webkit/libdmwebkit.dylib',
        'launcher': app/'Contents/Resources/launch.zsh',
        'save_helper': app/'Contents/Resources/local_save.zsh',
    }
    return {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in files.items()}


def run_phase(command, env, work, snapshot, probe=None):
    """Request read-only WebKit snapshots after the game framebuffer is ready.

    Native WebKit panels are absent from the engine's screenshot. The optional
    private probe writes only capture-web.txt: no input/action requests.
    """
    with subprocess.Popen(command, env=env, cwd=work) as process:
        deadline = time.monotonic() + 300
        requested = False
        while process.poll() is None:
            if probe is not None and not requested and snapshot.is_file():
                (probe/'capture-web.txt').write_text('hud')
                requested = True
            if time.monotonic() >= deadline:
                process.kill()
                process.wait()
                raise subprocess.TimeoutExpired(command, 300)
            time.sleep(0.25)
        return process.returncode


def preserve_panels(probe, destination):
    """Keep native panel pixels separate from gameplay/input acceptance."""
    destination.mkdir(parents=True, exist_ok=True)
    manifest = probe/'hud-panels.json'
    rows = json.loads(manifest.read_text()) if manifest.is_file() else []
    if manifest.is_file():
        shutil.copy2(manifest, destination/manifest.name)
    panels = []
    for row in rows:
        filename = row.get('file', '')
        if not re.fullmatch(r'hud-panel-[0-9]+\.png', filename):
            raise ValueError(f'Unexpected native snapshot name: {filename!r}')
        path = probe/filename
        pixels = path.read_bytes() if path.is_file() else b''
        width, height = struct.unpack('>II', pixels[16:24]) if len(pixels) >= 24 and pixels[:8] == b'\x89PNG\r\n\x1a\n' else (0, 0)
        if pixels:
            shutil.copy2(path, destination/filename)
        panels.append(dict(panel=row.get('panel'), url=row.get('url'),
                           file=str(destination/filename), width=width, height=height,
                           sha256=hashlib.sha256(pixels).hexdigest() if pixels else '',
                           valid_png=width > 0 and height > 0))
    no_actions = not any(probe.glob('action*'))
    return dict(panels=panels, manifest=str(destination/manifest.name),
                no_action_requests=no_actions,
                passed=bool(panels) and no_actions and all(p['valid_png'] for p in panels),
                scope='Read-only native WebKit panel capture; visual inspection is separate. No physical input claim.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app', type=Path, default=ROOT/'Banners of the Deep.app')   # the real folder; the old names are hidden shortcuts to it
    parser.add_argument('--race', choices=STARTING_ARMIES, default='Human')
    parser.add_argument('--label', default='app', help='Separate report, log and screenshot prefix.')
    parser.add_argument('--native-panels', action='store_true', help='Also preserve read-only native WebKit panel snapshots for visual review.')
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_-]+', args.label):
        parser.error('label must contain only letters, digits, underscores and hyphens')
    out = ROOT/'tests'; out.mkdir(exist_ok=True)
    result = dict(app=str(args.app), started_utc=datetime.now(timezone.utc).isoformat(),
                  build_hashes=build_hashes(args.app), race=args.race,
                  expected_starting_units=STARTING_ARMIES[args.race], phases={})
    result['helper_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    result['native_panels_requested'] = args.native_panels
    expected_type = '/mob/Monsters/' + ('Spider/Queen' if args.race == 'Spider' else args.race)
    normal_data = Path.home()/'Library/Application Support/Dungeon Master Remastered'
    def normal_save_hashes():
        # every world's saves (world/units, and worlds/<id>/units since the world list of 10-31) and the shared profiles
        folders = [normal_data/'world/units', normal_data/'profiles', *sorted((normal_data/'worlds').glob('*/units'))]
        return {str(p.relative_to(normal_data)): hashlib.sha256(p.read_bytes()).hexdigest()
                for d in folders if d.exists() for p in sorted(d.rglob('*.sav'))}
    result['normal_saves_before'] = normal_save_hashes()
    current = {
        'game': ROOT/'game/Cave Crawlers.json',
        'hud': ROOT/'game/Interface/remastered.html',
        'webview': ROOT/'engine/webview-webkit/Robust.Client.WebView.dll',
        'native_bridge': ROOT/'engine/webview-webkit/libdmwebkit.dylib',
        # build_app.py overlays Remastered's clock runtime after copying Classic.
        'runtime': ROOT/'engine/server/OpenDreamRuntime.dll',
        'client': ROOT/'engine/client/Content.Client.zip',    # the shared client with Remastered's title screen (tools/make_client_brand.py)
        'native_bootstrap': ROOT.parent/'replica/runtime/macos-x64/client/Space Station 14.app/Contents/Resources/Robust.Client.dll',
        'launcher': ROOT/'mac-app/launch.zsh',
        'save_helper': ROOT.parent/'replica/mac-app/local_save.zsh',
    }
    result['matches_current_build'] = {
        name: hashlib.sha256(path.read_bytes()).hexdigest() == result['build_hashes'][name]
        for name, path in current.items()
    }
    with tempfile.TemporaryDirectory(prefix='dm-remastered-app-') as work:
        work = Path(work); data = work/'profile'
        exe = next(((args.app)/'Contents/MacOS'/n for n in ('BannersOfTheDeep', 'LandOfLords', 'DungeonMasterRemastered') if ((args.app)/'Contents/MacOS'/n).is_file()), (args.app)/'Contents/MacOS/BannersOfTheDeep')   # LandOfLords since the rename
        for phase, seconds in (('new_army', 45), ('reload', 30)):
            # Each phase gets its own complete log; retain it before the
            # disposable profile is removed, including full DM stack traces.
            errorlog = data/'world/ErrorLog.txt'
            errorlog.unlink(missing_ok=True)
            env = dict({k:v for k,v in os.environ.items() if not k.startswith('DM_')}, PATH='/usr/bin:/bin:/usr/sbin:/sbin', DM_STANDALONE_DATA_DIR=str(data),
                       DM_GAME_SNAPSHOT=str(out/f'{args.label}-{phase}.png'))
            if phase == 'new_army': env['DM_TEST_RACE'] = args.race
            snapshot = out/f'{args.label}-{phase}.png'
            snapshot.unlink(missing_ok=True)
            probe = work/f'{phase}-native-probe' if args.native_panels else None
            if probe is not None:
                probe.mkdir()
                env['DM_NATIVE_UI_PROBE'] = str(probe)
            started = time.monotonic()
            code = run_phase([str(exe), '--username', 'RemasterCheck', '--smoke-seconds', str(seconds)], env, work, snapshot, probe)
            bootstrap = data/'client/Space Station 14.app/Contents/Resources/Robust.Client.dll'
            bootstrap_hash = hashlib.sha256(bootstrap.read_bytes()).hexdigest() if bootstrap.is_file() else ''
            # on Apple silicon the launcher lays the arm64 client over the copy (launch.zsh, client-arch)
            client_arch = (data/'client-arch').read_text().strip() if (data/'client-arch').is_file() else 'x86_64'
            arm64_bootstrap = args.app/'Contents/Resources/game/runtime/client-arm64/Robust.Client.dll'
            expected_bootstrap = (hashlib.sha256(arm64_bootstrap.read_bytes()).hexdigest() if client_arch == 'arm64' and arm64_bootstrap.is_file()
                                  else result['build_hashes']['native_bootstrap'])
            logs = {name: (data/'reports'/name).read_text(errors='replace') for name in ('launcher.log', 'server.log', 'client.log') if (data/'reports'/name).exists()}
            world_log = errorlog.read_text(errors='replace') if errorlog.exists() else ''
            log_files = {}
            for name, contents in dict(logs, world=world_log).items():
                path = out/f'{args.label}-{phase}-{name}'
                if name == 'world': path = path.with_suffix('.log')
                path.write_text(contents)
                log_files[name] = str(path)
            save = data/'world/units/localhost@remastercheck_save.sav'
            units = 0
            unit_summary = []
            if save.exists():
                nodes = json.loads(save.read_text())['_nodes']; table = nodes['.opendream_graph']['Objects']
                unit_refs = table[nodes['UnitList']['Id']]['Values']
                units = len(unit_refs)
                for ref in unit_refs:
                    unit = table[ref['Id']]
                    fields = unit['Fields']['_nodes']
                    unit_summary.append(dict(type=unit['Type'],
                        race=fields.get('Race', {}).get('Value', {}).get('Value'),
                        hp=fields.get('HP', {}).get('Value', {}).get('Value')))
            status_path = data/'reports/save-status'
            ack_path = data/'reports/save-request.ack'
            acknowledgment = ack_path.read_text().strip() if ack_path.exists() else ''
            result['phases'][phase] = dict(exit_code=code, seconds=round(time.monotonic() - started, 1),
                server_ready=' -> Ready' in logs.get('server.log', ''), client_in_game='Runlevel changed to: InGame' in logs.get('client.log', ''),
                saved_units=units, saved_unit_summary=unit_summary,
                saved_types_match=units > 0 and all(u['type'] == expected_type for u in unit_summary),
                saved_units_alive=units > 0 and all(isinstance(u['hp'], (int, float)) and u['hp'] > 0 for u in unit_summary),
                race_prompt_chosen=phase == 'reload' or f'smoke test chose {args.race} through the race prompt' in logs.get('client.log', ''),
                snapshot=(out/f'{args.label}-{phase}.png').exists(),
                logs=log_files,
                save_status=status_path.read_text().strip() if status_path.exists() else '',
                save_acknowledgment=acknowledgment,
                acknowledged_flush='Local host saved units before shutdown' in logs.get('server.log', ''),
                no_save_error=not (data/'reports/save-request.error').exists(),
                launcher_lock_removed=not (data/'launcher.lock').exists(),
                copied_bootstrap_sha256=bootstrap_hash, client_arch=client_arch,
                copied_bootstrap_matches_package=bootstrap_hash == expected_bootstrap,
                errors={k: error_lines(v) for k, v in logs.items()},
                game_runtime_errors=error_lines(world_log))
            if probe is not None:
                result['phases'][phase]['native_panels'] = preserve_panels(probe, out/f'{args.label}-{phase}-native-panels')
    result['finished_utc'] = datetime.now(timezone.utc).isoformat()
    result['normal_saves_unchanged'] = result['normal_saves_before'] == normal_save_hashes()
    acknowledgments = [p['save_acknowledgment'] for p in result['phases'].values()]
    result['fresh_save_acknowledgments'] = len(set(acknowledgments)) == 2 and all(re.fullmatch(r'[0-9A-Fa-f-]{36}', ack) for ack in acknowledgments)
    result['build_stable'] = result['build_hashes'] == build_hashes(args.app)
    result['passed'] = result['normal_saves_unchanged'] and result['fresh_save_acknowledgments'] and result['build_stable'] and all(result['matches_current_build'].values()) and all(p['exit_code'] == 0 and p['server_ready'] and p['client_in_game'] and p['saved_units'] == STARTING_ARMIES[args.race] and p['saved_types_match'] and p['saved_units_alive'] and p['race_prompt_chosen']
                           and p['save_status'] == 'saved' and p['acknowledged_flush'] and p['no_save_error'] and p['launcher_lock_removed'] and p['copied_bootstrap_matches_package']
                           and p['snapshot'] and (not args.native_panels or p['native_panels']['passed'])
                           and not any(p['errors'].values()) and not p['game_runtime_errors'] for p in result['phases'].values())
    (out/f'{args.label}-checks.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    if not result['passed']: raise SystemExit(1)


if __name__ == '__main__':
    main()
