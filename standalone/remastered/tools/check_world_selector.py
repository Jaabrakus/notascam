#!/usr/bin/env python3
"""Windowless checks for the launcher's world list (planning/WORLD_SELECTOR_PLAN_2026-10-31.md).

    python3 tools/check_world_selector.py [--launch mac-app/launch.zsh] [--mac-app mac-app] [--hfs]

1. launch.zsh --prepare-only on temporary data folders and a fake app (a tiny packaged world, a fake client): world
   folders, each world's .build-id, the first world left as it was, profiles copied once, bad --world values refused.
2. mac-app/LauncherWorlds.h compiled into a small test with clang: listing, sorting, names, "your" company, folder ids.
3. --ui: mac-app/Launcher.m itself, driven with no window on screen and no input (tools/check_world_selector_ui.m):
   the list, keys, Rename, New world, Move to Trash (into a test folder), Host; pictures into --shots.
--hfs also runs the copy fallback on a small HFS+ disk image (cp -c can't clone there). Never touches the real saves:
every data folder is made here and removed after."""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPLICA = ROOT.parent/'replica'
results = []


def check(name, ok, detail=''):
    results.append(dict(name=name, ok=bool(ok), detail=detail))
    print(('PASS ' if ok else 'FAIL ') + name + (f'  ({detail})' if detail and not ok else ''))


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def tree(folder):
    """relative path -> sha256 of every file under folder."""
    folder = Path(folder)
    return {str(p.relative_to(folder)): sha(p) for p in sorted(folder.rglob('*')) if p.is_file()} if folder.exists() else {}


def fake_app(where, launch, build_id):
    """A Resources folder launch.zsh can run from: the script, the save helper, a tiny packaged world, a fake client."""
    res = Path(where)/'Resources'
    game = res/'game'
    (game/'world/Code').mkdir(parents=True)
    (game/'world/Cave Crawlers.json').write_text('{"fake": true}\n')
    (game/'world/Code/World.dm').write_text(f'packaged {build_id}\n')
    (game/'build-id').write_text(build_id + '\n')
    (game/'player-name').write_text('@login\n')
    client = game/'runtime/client/Space Station 14.app/Contents/Resources'
    client.mkdir(parents=True)
    (client/'Robust.Client.dll').write_text('fake client\n')
    shutil.copy2(launch, res/'launch.zsh')
    shutil.copy2(REPLICA/'mac-app/local_save.zsh', res/'local_save.zsh')
    return res


def set_build(res, build_id):
    (res/'game/build-id').write_text(build_id + '\n')
    (res/'game/world/Code/World.dm').write_text(f'packaged {build_id}\n')


def prepare(res, data, *args):
    status = Path(data).parent/'status'
    status.unlink(missing_ok=True)
    env = {'PATH': '/usr/bin:/bin:/usr/sbin:/sbin', 'HOME': os.environ['HOME'], 'DM_STANDALONE_DATA_DIR': str(data),
           'DM_LAUNCH_STATUS': str(status)}
    p = subprocess.run(['/bin/zsh', str(res/'launch.zsh'), '--prepare-only', *args], env=env, capture_output=True, text=True, timeout=120)
    log = (Path(data)/'reports/launcher.log').read_text() if (Path(data)/'reports/launcher.log').exists() else ''
    return p.returncode, status.read_text().strip() if status.exists() else '', log


def legacy_world(data, build_id):
    """Today's layout: world/ with the game files, saves and a profile, $data/build-id; no .build-id, no profiles/."""
    world = Path(data)/'world'
    (world/'Code').mkdir(parents=True)
    (world/'Cave Crawlers.json').write_text('{"fake": true}\n')
    (world/'Code/World.dm').write_text(f'packaged {build_id}\n')
    units = world/'units'; units.mkdir()
    (units/'remaster_world.sav').write_text('{"world": "saved"}\n')
    (units/'localhost@kiwi_save.sav').write_text('{"units": 63}\n')
    (units/'remaster_profile_localhost@kiwi.sav').write_text('{"audio": "kiwi"}\n')
    (units/'remaster_profile_localhost@friend.sav').write_text('{"audio": "friend"}\n')
    (world/'players').mkdir()
    (world/'players/localhost@kiwi_save.sav').write_text('{"player": 1}\n')
    (Path(data)/'build-id').write_text(build_id + '\n')
    client = Path(data)/'client/Space Station 14.app/Contents/Resources'
    client.mkdir(parents=True)
    (client/'Robust.Client.dll').write_text('fake client\n')
    return world


def saves(world):
    return {k: v for k, v in tree(world).items() if k.startswith(('units/', 'players/'))}


def check_launch(launch, hfs):
    with tempfile.TemporaryDirectory(prefix='botd-worlds-') as work:
        work = Path(work)
        res = fake_app(work/'app', launch, 'B1')

        # A. A fresh data folder: the first world made as before, plus its .build-id and profiles/.
        data = work/'fresh/data'
        code, status, log = prepare(res, data)
        check('fresh: prepared', code == 0 and status == 'stopped' and 'World: world' in log, f'{code} {status!r}')
        check('fresh: world has the game files', (data/'world/Cave Crawlers.json').exists() and (data/'world/Code/World.dm').read_text() == 'packaged B1\n')
        check('fresh: world .build-id', (data/'world/.build-id').read_text().strip() == 'B1')
        check('fresh: client copied, data build-id', (data/'client/Space Station 14.app/Contents/Resources/Robust.Client.dll').exists() and (data/'build-id').read_text().strip() == 'B1')
        check('fresh: profiles folder', (data/'profiles/.imported').exists() and not [p for p in (data/'profiles').iterdir() if p.name != '.imported'])
        check('fresh: no worlds/ folder', not (data/'worlds').exists())

        # B. Today's layout on the current build: nothing under world/ rewritten, profiles copied, originals kept.
        data = work/'legacy/data'
        world = legacy_world(data, 'B1')
        (world/'Code/World.dm').write_text('changed locally\n')     # a refresh would put the packaged text back
        before = tree(world)
        code, status, log = prepare(res, data)
        after = tree(world)
        check('legacy: prepared', code == 0 and status == 'stopped', f'{code} {status!r}')
        check('legacy: no game file copied (same build)', (world/'Code/World.dm').read_text() == 'changed locally\n')
        check('legacy: every file the same, only .build-id added',
              {k: v for k, v in after.items() if k != '.build-id'} == before and set(after) - set(before) == {'.build-id'})
        check('legacy: .build-id from the data folder', (world/'.build-id').read_text().strip() == 'B1')
        profiles = data/'profiles'
        check('legacy: profiles copied', sha(profiles/'remaster_profile_localhost@kiwi.sav') == before['units/remaster_profile_localhost@kiwi.sav']
              and sha(profiles/'remaster_profile_localhost@friend.sav') == before['units/remaster_profile_localhost@friend.sav'])
        check('legacy: originals still in the world', (world/'units/remaster_profile_localhost@kiwi.sav').exists())

        # G. The copy happens once: a later change in the first world's profile is not copied again.
        (world/'units/remaster_profile_localhost@kiwi.sav').write_text('{"audio": "older build"}\n')
        (profiles/'remaster_profile_localhost@kiwi.sav').write_text('{"audio": "new build"}\n')
        prepare(res, data)
        check('legacy: profiles copied once, never overwritten', (profiles/'remaster_profile_localhost@kiwi.sav').read_text() == '{"audio": "new build"}\n')

        # D. A new world: its own folder with the game files; the first world untouched.
        first = tree(world)
        code, status, log = prepare(res, data, '--world', 'worlds/20261031-0912')
        new = data/'worlds/20261031-0912'
        check('new world: prepared', code == 0 and status == 'stopped' and 'World: worlds/20261031-0912' in log, f'{code} {status!r}')
        check('new world: game files and .build-id', (new/'Cave Crawlers.json').exists() and (new/'.build-id').read_text().strip() == 'B1')
        check('new world: no saves of its own yet', not (new/'units').exists())
        check('new world: first world untouched', tree(world) == first)

        # C/E. A new build: each world refreshes when it is played; saves kept.
        (new/'units').mkdir()
        (new/'units/remaster_world.sav').write_text('{"world": "second"}\n')
        set_build(res, 'B2')
        kept_first, kept_new = saves(world), saves(new)
        prepare(res, data, '--world', 'worlds/20261031-0912')
        check('new build: played world refreshed', (new/'Code/World.dm').read_text() == 'packaged B2\n' and (new/'.build-id').read_text().strip() == 'B2')
        check('new build: its saves kept', saves(new) == kept_new)
        check('new build: other world waits', (world/'.build-id').read_text().strip() == 'B1' and (world/'Code/World.dm').read_text() == 'changed locally\n')
        prepare(res, data)
        check('new build: first world refreshed when played', (world/'Code/World.dm').read_text() == 'packaged B2\n' and (world/'.build-id').read_text().strip() == 'B2')
        check('new build: first world saves kept', saves(world) == kept_first)

        # F. Bad world folders are refused, and nothing is made for them.
        for bad in ('../x', '/tmp', 'worlds/a/b', 'worlds/..', 'worlds/', 'world2', 'worlds/a b', 'worlds/' + 'x' * 41, ''):
            listing = sorted(str(p.relative_to(data)) for p in data.rglob('*'))
            args = ['--world', bad] if bad else ['--world']
            code, status, log = prepare(res, data, *args)
            check(f'refused --world {bad!r}', code != 0 and status.startswith('error:') and
                  sorted(str(p.relative_to(data)) for p in data.rglob('*')) == listing, f'{code} {status!r}')

        # H. The plain-copy fallback where the disk can't clone (HFS+).
        if hfs:
            image = work/'hfs.dmg'; mount = work/'hfs'
            subprocess.run(['/usr/bin/hdiutil', 'create', '-size', '20m', '-fs', 'HFS+', '-volname', 'botdcheck', str(image)], check=True, capture_output=True)
            subprocess.run(['/usr/bin/hdiutil', 'attach', '-nobrowse', '-mountpoint', str(mount), str(image)], check=True, capture_output=True)
            try:
                data = mount/'data'
                code, status, log = prepare(res, data, '--world', 'worlds/hfs')
                check('HFS+: copied without clones', code == 0 and (data/'worlds/hfs/Code/World.dm').read_text() == 'packaged B2\n', f'{code} {status!r}')
            finally:
                subprocess.run(['/usr/bin/hdiutil', 'detach', str(mount)], capture_output=True)


def check_header(mac_app):
    """LauncherWorlds.h's pure functions, compiled with the launcher's own flags into a test program."""
    test = ROOT/'tools/check_world_selector_test.m'
    with tempfile.TemporaryDirectory(prefix='botd-worlds-h-') as work:
        exe = Path(work)/'worlds_test'
        build = subprocess.run(['/usr/bin/clang', '-fobjc-arc', '-mmacosx-version-min=11.0', '-Wall', '-Werror', '-I', str(mac_app),
                                '-framework', 'Foundation', str(test), '-o', str(exe)], capture_output=True, text=True)
        check('header: compiles without warnings', build.returncode == 0, build.stderr[-600:])
        if build.returncode: return
        run = subprocess.run([str(exe), work], capture_output=True, text=True, timeout=60)
        for line in run.stdout.splitlines():
            if line.startswith(('PASS ', 'FAIL ')):
                ok, _, rest = line.partition(' ')
                name, _, detail = rest.partition('  (')
                check('header: ' + name, ok == 'PASS', detail.rstrip(')'))
        check('header: test ran to the end', run.returncode == 0 and 'DONE' in run.stdout, run.stderr[-400:])


def check_ui(mac_app, shots):
    """Launcher.m's world list, run hidden: three made-up worlds, then every action; pictures of the window."""
    with tempfile.TemporaryDirectory(prefix='botd-worlds-ui-') as work:
        work = Path(work); data = work/'data'; now = time.time()
        def world(folder, info=None, meta=None, mtime=None):
            path = data/folder; path.mkdir(parents=True)
            if info is not None: (path/'world-info.json').write_text(json.dumps(info) + '\r\n')
            if meta is not None: (path/'botd-world.json').write_text(json.dumps(meta))
            if mtime and info is not None: os.utime(path/'world-info.json', (mtime, mtime))
            return path
        stamp = lambda t: time.strftime('%Y-%m-%dT%H:%M:%S%z', time.localtime(t))[:-2] + ':' + time.strftime('%z', time.localtime(t))[-2:]
        first = world('world', dict(version=1, name=' Mountains of the Hidden Temple', season='Fall', year=975, age='Age of the Burning Dragon',
                      players={'localhost@kiwi': dict(key='Kiwi', race='Dwarf', units=63)}), mtime=now - 3600)
        (first/'units').mkdir(); (first/'units/remaster_world.sav').write_text('{}')
        world('worlds/20261028-2000', dict(version=1, name='Stars of the Lost Scroll', season='Winter', year=212, age='Time of the Red Goblin',
              players={'localhost@kiwi': dict(key='Kiwi', race='Elf', units=12), 'localhost@friend': dict(key='Friend', race='Orc', units=5)}),
              dict(version=1, label='Friday nights', created=stamp(now - 9 * 86400), last_played=stamp(now - 3 * 86400)))
        world('worlds/20261019-1000', dict(version=1, name='Plains of the Ancient Dragon', season='Summer', year=640, players={}),
              dict(version=1, label='', created=stamp(now - 14 * 86400), last_played=stamp(now - 12 * 86400)))
        (data/'discord-account.json').write_text(json.dumps(dict(id='1', username='kiwi', global_name='Kiwi', game_name='Kiwi')))
        (work/'data-empty').mkdir(); (work/'trash').mkdir()
        exe = work/'bin/world_ui_test'; exe.parent.mkdir()
        build = subprocess.run(['/usr/bin/clang', '-fobjc-arc', '-mmacosx-version-min=11.0', '-I', str(mac_app), '-I', str(REPLICA/'mac-app'),
                                '-framework', 'Cocoa', str(ROOT/'tools/check_world_selector_ui.m'), '-o', str(exe)], capture_output=True, text=True)
        check('ui: compiles', build.returncode == 0, build.stderr[-800:])
        if build.returncode: return
        shutil.copy2(mac_app/'launcher-art.png' if (mac_app/'launcher-art.png').exists() else ROOT/'mac-app/launcher-art.png', exe.parent/'launcher-art.png')
        shutil.copy2(ROOT/'art/hud/src/assets/screens-races.png', exe.parent/'world-races.png')
        (exe.parent/'game').mkdir(); (exe.parent/'game/player-name').write_text('@login\n')
        shots.mkdir(parents=True, exist_ok=True)
        run = subprocess.run([str(exe), str(data), str(work/'trash'), str(shots)], capture_output=True, text=True, timeout=120)
        for line in run.stdout.splitlines():
            if line.startswith(('PASS ', 'FAIL ')):
                ok, _, rest = line.partition(' ')
                name, _, detail = rest.partition('  (')
                check('ui: ' + name, ok == 'PASS', detail.rstrip(')'))
        check('ui: test ran to the end', run.returncode == 0 and 'DONE' in run.stdout, (run.stderr or run.stdout)[-600:])


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--launch', type=Path, default=ROOT/'mac-app/launch.zsh')
    parser.add_argument('--mac-app', type=Path, default=ROOT/'mac-app')
    parser.add_argument('--hfs', action='store_true', help='also check the plain-copy fallback on an HFS+ disk image')
    parser.add_argument('--skip-header', action='store_true')
    parser.add_argument('--ui', action='store_true', help='also drive Launcher.m hidden (no window on screen, no input)')
    parser.add_argument('--shots', type=Path, default=ROOT/'tests/world-selector-shots', help='where --ui saves its pictures')
    args = parser.parse_args()
    started = time.monotonic()
    check_launch(args.launch.resolve(), args.hfs)
    if not args.skip_header: check_header(args.mac_app.resolve())
    if args.ui: check_ui(args.mac_app.resolve(), args.shots.resolve())
    failed = [r for r in results if not r['ok']]
    print(json.dumps(dict(passed=len(results) - len(failed), failed=len(failed), seconds=round(time.monotonic() - started, 1))))
    sys.exit(1 if failed else 0)


if __name__ == '__main__':
    main()
