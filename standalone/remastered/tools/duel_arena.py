#!/usr/bin/env python3
"""The duel arena (hud-craft, 10-25; the user: "build a new test arena for the arena dueling combat"): a walled arena
to watch duels in the real client, in 3D, with the game's current combat. The packaged app's own engine, client and
WebKit HUD on a temporary copy of game/ with tests/duel_arena_probe.dm: a sand floor inside a stone wall, your fighter
on the west side, the other realm's on the east, at war. The HUD's question cards ask who fights (each fighter's
people, weapon and armour), then after each duel: the same again, swap sides, new picks, a random pair, or stop. Each
duel's end is printed and shown in the game ("Duel 2: yours won after 74 s (...)"). The window stays until you close
it (or Stop, or --minutes). Your saves are not touched (a copy of game/ without players/ or units/).

  python3 tools/runlock.py --who duel-arena --kind input -- caffeinate -d -i python3 tools/duel_arena.py
      [--a "Human|Sword|Metal"] [--b "Orc|Axe|Leather"]   the first pair (people|weapon|armour); no cards for it
      [--auto N]                                          N duels of that pair with no cards at all, then stop
      [--stills 20,60]                                    HUD and 3D stills that many seconds after the first duel starts
      [--minutes 120]                                     close after that long
      [--compile-only]                                    build the arena and stop
Weapons: Fists, Sword, Axe, Mace, Spear, Dagger, Bow. Armour: None, Leather, Bone, Metal, Metal and shield.
Stills and logs: reports/duel-arena/."""
import argparse, json, os, re, shutil, subprocess, sys, tempfile, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APPRT = ROOT/'Dungeon Master Remastered.app/Contents/Resources/game/runtime'
REPLICA = ROOT.parent/'replica'
sys.path.insert(0, str(REPLICA/'tools'))
from skin_layout import write_hints  # noqa: E402
OUT = ROOT/'reports/duel-arena'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--a', default='')
    ap.add_argument('--b', default='')
    ap.add_argument('--auto', type=int, default=0)
    ap.add_argument('--stills', default='')
    ap.add_argument('--minutes', type=float, default=120)
    ap.add_argument('--compile-only', action='store_true')
    a = ap.parse_args()
    if a.auto and not (a.a and a.b): sys.exit('--auto needs --a and --b')
    OUT.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix='dm-duel-arena-'))
    world, probe = work/'world', work/'probe'
    probe.mkdir()
    shutil.copytree(ROOT/'game', world, ignore=shutil.ignore_patterns('Cave Crawlers.json', '*.dmm', '*.sav', 'ErrorLog.txt', 'units', 'saves', 'players', 'backup'))
    dme = re.sub(r'^#include .*\.dmm"\s*$', '', (world/'Cave Crawlers.dme').read_text(encoding='latin-1'), flags=re.M)
    src = (world/'Code/World.dm').read_text(encoding='latin-1')
    i, j = src.index('\tNew()'), src.index('\nvar/Season')
    (world/'Code/World.dm').write_text(src[:i] + '\tNew()\n\t\tlog = file("ErrorLog.txt")\n' + src[j:], encoding='latin-1')
    shutil.copy2(ROOT/'tests/duel_arena_probe.dm', world/'duel_arena_probe.dm')
    fixture = world/'duel_arena.dme'
    fixture.write_text(dme + '\n#include "duel_arena_probe.dm"\n', encoding='latin-1')
    if a.a and a.b:
        (world/'duel-arena.txt').write_text(f'A={a.a}\nB={a.b}\n' + (f'AUTO={a.auto}\n' if a.auto else ''))
    hud = world/'Interface/remastered.html'
    h = hud.read_text(encoding='utf-8')
    # the boot cover goes at once (its rAF removal stalls while the window is covered), as hud_real.py does
    hud.write_text(h.replace("requestAnimationFrame(()=>requestAnimationFrame(()=>{c.classList.add('off');setTimeout(()=>c.remove(),900)}))", "c.classList.add('off');c.remove()"), encoding='utf-8')
    dotnet = APPRT/'dotnet/dotnet'
    env = dict(os.environ, DOTNET_ReadyToRun='0')
    print('compiling the arena...', flush=True)
    with (OUT/'compile.log').open('w') as out:
        r = subprocess.run([str(dotnet), str(REPLICA/'runtime/macos-x64/compiler/DMCompiler.dll'), str(fixture)], env=env, stdout=out, stderr=subprocess.STDOUT, timeout=240)
    if r.returncode or not fixture.with_suffix('.json').exists():
        print('the arena did not compile:', '\n'.join(re.findall(r'^Error.*$', (OUT/'compile.log').read_text(errors='replace'), flags=re.M)[:5])); sys.exit(1)
    if a.compile_only:
        print('compiled:', re.findall(r'Compilation [^\r\n]*', (OUT/'compile.log').read_text(errors='replace'))[-1:]); shutil.rmtree(work, ignore_errors=True); return
    hints = work/'layout.json'
    write_hints(world/'skin.dmf', hints)
    cd = work/'client'
    shutil.copytree(APPRT/'client/Space Station 14.app/Contents/Resources', cd, ignore=shutil.ignore_patterns('user_data', '.DS_Store'))
    cenv = dict(env, DM_SKIN_LAYOUT_HINTS=str(hints), DM_NATIVE_UI_PROBE=str(probe), DM_GAME_SNAPSHOT=str(probe/'game.png'),
                ROBUST_MODULE_ROBUST_CLIENT_WEBVIEW=str(APPRT/'webview-webkit'))
    slp, clp, elog = OUT/'server.log', OUT/'client.log', world/'ErrorLog.txt'
    log = lambda: elog.read_text(errors='replace') if elog.exists() else ''
    server = client = None

    def front():
        subprocess.run(['osascript', '-e', f'tell application "System Events" to set frontmost of (first process whose unix id is {client.pid}) to true'],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def still(name):   # the page as the window shows it (the HUD and the 3D view, which the page draws), as watch_pace_real.py
        front(); time.sleep(1.0)
        prefix = 'duel-' + name
        (probe/'capture-web.txt').write_text(prefix)
        end = time.monotonic() + 15
        while time.monotonic() < end and not (probe/f'{prefix}-panels.json').exists(): time.sleep(.25)
        time.sleep(1.5)
        got = []
        if (probe/f'{prefix}-panels.json').exists():
            for row in json.loads((probe/f'{prefix}-panels.json').read_text()):
                f = probe/row['file']
                if f.exists(): shutil.copy2(f, OUT/row['file']); got.append(row['file'])
        print('still:', ', '.join(got) or 'none', flush=True)

    stills = sorted(int(s) for s in a.stills.split(',') if s.strip())
    try:
        with slp.open('w') as sl, clp.open('w') as cl:
            server = subprocess.Popen([str(dotnet), str(APPRT/'server/Robust.Server.dll'), '--data-dir', str(work/'data'), '--cvar', f'opendream.json_path={fixture.with_suffix(".json")}',
                '--cvar', 'opendream.topic_port=25961', '--cvar', 'net.bindto=127.0.0.1', '--cvar', 'net.port=12461', '--cvar', 'auth.mode=0', '--cvar', 'status.enabled=false',
                '--cvar', 'hub.advertise=false', '--cvar', 'game.auto_pause_empty=false'], env=env, stdout=sl, stderr=subprocess.STDOUT, cwd=world)
            end = time.monotonic() + 180
            while time.monotonic() < end and ' -> Ready' not in slp.read_text(errors='replace'): time.sleep(.5)
            client = subprocess.Popen([str(dotnet), str(cd/'Robust.Client.dll'), '--mount-zip', str(APPRT/'server/Content.Client.zip'), '--connect', '--connect-address', 'udp://127.0.0.1:12461',
                '--username', 'DuelArena', '--self-contained', '--cvar', 'web.headless=false', '--cvar', 'discord.enabled=false'], cwd=cd, env=cenv, stdout=cl, stderr=subprocess.STDOUT)
            print('opening the arena window...', flush=True)
            t_open = time.monotonic(); fronted = False; t_first = None; seen = set()
            while client.poll() is None and time.monotonic() - t_open < a.minutes * 60:
                if not fronted and (probe/'game.png').exists(): front(); fronted = True
                for kind, rest in re.findall(r'DA\|(started|ended|stopped)\|?([^\r\n]*)', log()):
                    key = kind + rest
                    if key in seen: continue
                    seen.add(key)
                    if kind == 'started':
                        n, sa, sb = (rest.split('|') + ['', '', ''])[:3]
                        print(f'duel {n}: {sa} against {sb}', flush=True)
                        if t_first is None: t_first = time.monotonic()
                    elif kind == 'ended':
                        f = rest.split('|')
                        print(f'  duel {f[0]}: {f[1]} after {f[2]} s; yours {f[3]} health {f[4]} limbs lost {f[5]}; theirs {f[6]} health {f[7]} limbs lost {f[8]}', flush=True)
                    else:
                        print('stopped', flush=True)
                if t_first is not None:
                    while stills and time.monotonic() - t_first >= stills[0]: still(f'{stills.pop(0)}s')
                if 'DA|stopped' in log() and a.auto and not stills: break
                time.sleep(1)
    finally:
        for p in (client, server):
            if p and p.poll() is None:
                p.terminate()
                try: p.wait(10)
                except subprocess.TimeoutExpired: p.kill()
    (OUT/'world.log').write_text(log())
    errs = re.findall(r'^.*(?:\[(?:ERRO|FATL)\]|Exception occurred|runtime error).*$', slp.read_text(errors='replace') + '\n' + log(), flags=re.M | re.I)
    js = [l for l in clp.read_text(errors='replace').splitlines() if 'TypeError' in l or 'ReferenceError' in l or 'SyntaxError' in l][:3]
    print('duels ended:', len(re.findall(r'DA\|ended', log())), '| server errors:', errs[:5] or 'none', '| page errors:', js or 'none', flush=True)
    shutil.rmtree(work, ignore_errors=True)


if __name__ == '__main__':
    main()
