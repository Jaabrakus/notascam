#!/usr/bin/env python3
"""Watch three duels in the real client (run through tools/runlock.py): the packaged app's own engine, client and WebKit
HUD on a temporary copy of game/ with tests/pace_watch_probe.dm (two humans with iron swords, two in full metal armour,
two bare-fisted, from two realms at war, side by side). Nothing is clicked: the window comes to the front and stays
open for you to watch; it closes by itself after 12 minutes, or when you close it. HUD stills at 30 s and 90 s go to
reports/polish-2026-10-22/stump-care/watch/, and how each fight ended is printed.

  python3 tools/runlock.py --who stump-care -- caffeinate -d -i python3 tools/watch_pace_real.py
"""
import json, os, re, shutil, subprocess, sys, tempfile, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APPRT = ROOT/'Dungeon Master Remastered.app/Contents/Resources/game/runtime'
REPLICA = ROOT.parent/'replica'
sys.path.insert(0, str(REPLICA/'tools'))
from skin_layout import write_hints  # noqa: E402
OUT = ROOT/'reports/polish-2026-10-22/stump-care/watch'
OUT.mkdir(parents=True, exist_ok=True)
WATCH = int(os.environ.get('PW_SECONDS', '720'))


def main():
    work = Path(tempfile.mkdtemp(prefix='dm-pace-watch-'))
    world, probe = work/'world', work/'probe'
    probe.mkdir()
    shutil.copytree(ROOT/'game', world, ignore=shutil.ignore_patterns('Cave Crawlers.json', '*.dmm', '*.sav', 'ErrorLog.txt', 'units', 'saves', 'players', 'backup'))
    dme = re.sub(r'^#include .*\.dmm"\s*$', '', (world/'Cave Crawlers.dme').read_text(encoding='latin-1'), flags=re.M)
    src = (world/'Code/World.dm').read_text(encoding='latin-1')
    a, b = src.index('\tNew()'), src.index('\nvar/Season')
    (world/'Code/World.dm').write_text(src[:a] + '\tNew()\n\t\tlog = file("ErrorLog.txt")\n' + src[b:], encoding='latin-1')
    shutil.copy2(ROOT/'tests/pace_watch_probe.dm', world/'pace_watch_probe.dm')
    fixture = world/'pace_watch.dme'
    fixture.write_text(dme + '\n#include "pace_watch_probe.dm"\n', encoding='latin-1')
    hud = world/'Interface/remastered.html'
    h = hud.read_text(encoding='utf-8')
    # the boot cover goes at once (its rAF removal stalls while the window is covered), as hud_real.py does
    hud.write_text(h.replace("requestAnimationFrame(()=>requestAnimationFrame(()=>{c.classList.add('off');setTimeout(()=>c.remove(),900)}))", "c.classList.add('off');c.remove()"), encoding='utf-8')
    dotnet = APPRT/'dotnet/dotnet'
    env = dict(os.environ, DOTNET_ReadyToRun='0')
    with (OUT/'compile.log').open('w') as out:
        subprocess.run([str(dotnet), str(REPLICA/'runtime/macos-x64/compiler/DMCompiler.dll'), str(fixture)], env=env, stdout=out, stderr=subprocess.STDOUT, check=True, timeout=180)
    hints = work/'layout.json'
    write_hints(world/'skin.dmf', hints)
    cd = work/'client'
    shutil.copytree(APPRT/'client/Space Station 14.app/Contents/Resources', cd, ignore=shutil.ignore_patterns('user_data', '.DS_Store'))
    cenv = dict(env, DM_SKIN_LAYOUT_HINTS=str(hints), DM_NATIVE_UI_PROBE=str(probe), DM_GAME_SNAPSHOT=str(probe/'game.png'),
                ROBUST_MODULE_ROBUST_CLIENT_WEBVIEW=str(APPRT/'webview-webkit'))
    slp, clp, elog = OUT/'server.log', OUT/'client.log', world/'ErrorLog.txt'
    log = lambda: elog.read_text(errors='replace') if elog.exists() else ''

    def front():
        subprocess.run(['osascript', '-e', f'tell application "System Events" to set frontmost of (first process whose unix id is {client.pid}) to true'],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def capture(name):
        front()
        time.sleep(1.0)
        prefix = 'watch-' + name
        (probe/'capture-web.txt').write_text(prefix)
        end = time.monotonic() + 15
        while time.monotonic() < end and not (probe/f'{prefix}-panels.json').exists(): time.sleep(.25)
        time.sleep(1.5)
        if (probe/f'{prefix}-panels.json').exists():
            for row in json.loads((probe/f'{prefix}-panels.json').read_text()):
                f = probe/row['file']
                if f.exists(): shutil.copy2(f, OUT/row['file'])

    server = client = None
    try:
        with slp.open('w') as sl, clp.open('w') as cl:
            server = subprocess.Popen([str(dotnet), str(APPRT/'server/Robust.Server.dll'), '--data-dir', str(work/'data'), '--cvar', f'opendream.json_path={fixture.with_suffix(".json")}',
                '--cvar', 'opendream.topic_port=25951', '--cvar', 'net.bindto=127.0.0.1', '--cvar', 'net.port=12451', '--cvar', 'auth.mode=0', '--cvar', 'status.enabled=false',
                '--cvar', 'hub.advertise=false', '--cvar', 'game.auto_pause_empty=false'], env=env, stdout=sl, stderr=subprocess.STDOUT, cwd=world)
            end = time.monotonic() + 120
            while time.monotonic() < end and ' -> Ready' not in slp.read_text(errors='replace'): time.sleep(.5)
            client = subprocess.Popen([str(dotnet), str(cd/'Robust.Client.dll'), '--mount-zip', str(APPRT/'server/Content.Client.zip'), '--connect', '--connect-address', 'udp://127.0.0.1:12451',
                '--username', 'DuelWatch', '--self-contained', '--cvar', 'web.headless=false', '--cvar', 'discord.enabled=false'], cwd=cd, env=cenv, stdout=cl, stderr=subprocess.STDOUT)
            end = time.monotonic() + 150
            while time.monotonic() < end and 'PW|started' not in log(): time.sleep(.5)
            print('fights started' if 'PW|started' in log() else 'the scene did not start', flush=True)
            front()
            t0, shots, seen = time.monotonic(), {30: 'early', 90: 'later'}, set()
            while client.poll() is None and time.monotonic() - t0 < WATCH:
                for line in re.findall(r'PW\|ended\|([^\r\n]+)', log()):
                    if line not in seen:
                        seen.add(line)
                        print('ended:', line, flush=True)
                for s, n in list(shots.items()):
                    if time.monotonic() - t0 >= s:
                        capture(n)
                        del shots[s]
                time.sleep(1)
    finally:
        for p in (client, server):
            if p and p.poll() is None:
                p.terminate()
                try: p.wait(10)
                except subprocess.TimeoutExpired: p.kill()
    (OUT/'world.log').write_text(log())
    errs = re.findall(r'^.*(?:\[(?:ERRO|FATL)\]|Exception occurred|runtime error).*$', slp.read_text(errors='replace') + '\n' + log(), flags=re.M | re.I)
    print('fights:', re.findall(r'PW\|ended\|([^\r\n]+)', log()) or 'none ended', '| errors:', errs[:5] or 'none', flush=True)
    shutil.rmtree(work, ignore_errors=True)


if __name__ == '__main__':
    main()
