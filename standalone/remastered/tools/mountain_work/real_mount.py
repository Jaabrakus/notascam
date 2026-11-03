#!/usr/bin/env python3
"""Ramps, the Gather switch and mining a whole mountain, in the real Remastered client with real AppKit input (2026-10-24).
A temporary game copy with tools/mountain_work/ZZMountWork.dm (a rock massif with peaks beside the company) and the page
hook mw_hook.js (screen positions). Real clicks, a right-click menu, the G key and the Gather button:
  1. Gather is off at the start; a click on a tree or rock face walks there.
  2. G turns it on (one press, one change); a click on the rock face mines it.
  3. A ramp carved from the right-click menu, dug out; a click on its slope walks onto it; a click on the top climbs.
  4. From the top, a click on the next peak digs that column down a block.
  5. From below, a click on the top block of a face mines on up to it; then a block of the column behind.
  6. A click on the Gather button turns it off.
  python3 tools/runlock.py --who ramps-gather -- caffeinate -d -i -u python3 tools/mountain_work/real_mount.py [--tag T] [--game DIR] [--only ramp]
Writes reports/mountain-work/real-mount[-TAG].json and stills in reports/mountain-work/frames[-TAG]/."""
import argparse, json, os, re, shutil, subprocess, sys, tempfile, time, urllib.parse
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
APPRT = ROOT/'Land of Lords.app/Contents/Resources/game/runtime'
REPLICA = ROOT.parent/'replica'
sys.path.insert(0, str(REPLICA/'tools'))
from skin_layout import write_hints
HERE = Path(__file__).resolve().parent
TT = ROOT/'tools/trailer/breaking'
ap = argparse.ArgumentParser()
ap.add_argument('--tag', default='')
ap.add_argument('--game', type=Path, default=ROOT/'game')
ap.add_argument('--play', type=float, default=0, help='minutes: no checks, ordinary work, a window for a player to try the mountain, then close')
ap.add_argument('--only', default='', help='ramp: only the ramp (the carve, a click on its slope, a click on the top), for a before/after; hollow; inside: walking in a corridor in the mountain; plan: Plan mode; sky: mountain heights step 2 (Surface and Sky views)')
a = ap.parse_args()
OUT = ROOT/'reports/mountain-work'
FR = OUT/('frames' + ('-' + a.tag if a.tag else '')); FR.mkdir(parents=True, exist_ok=True)
WINREC = os.environ.get('WINREC', str(TT/'winrec')); FRAME = os.environ.get('FRAME', str(TT/'frame'))
dotnet = APPRT/'dotnet/dotnet'
work = Path(tempfile.mkdtemp(prefix='dm-mount-')); world = work/'world'; probe = work/'probe'; probe.mkdir()
shutil.copytree(a.game, world, ignore=shutil.ignore_patterns('Cave Crawlers.json', 'ErrorLog.txt', 'units', 'players', 'backup'))
(world/'units').mkdir(); (world/'players').mkdir()
shutil.copy2(HERE/'ZZMountWork.dm', world/'ZZMountWork.dm')
# the race pick is a HUD card (Onboarding.dm); in this copy only, it answers itself from test-race.txt (as rts-feel's run does)
ob = world/'Code/Remastered/Onboarding.dm'; obt = ob.read_text(encoding='utf-8'); kk = 'proc/RemasterChooseRace(mob/who, list/menu)\n'
if kk in obt:
    obt = obt.replace(kk, kk + '\tif(fexists("test-race.txt")) return trimtext(file2text("test-race.txt"))\n', 1)
    ks = 'proc/RemasterStory(mob/who, message, title)\n'
    if ks in obt: obt = obt.replace(ks, ks + '\tif(fexists("test-race.txt")) return\n', 1)
    ob.write_text(obt, encoding='utf-8')
    (world/'test-race.txt').write_text('Human')
stub = ''
if not (world/'Code/Remastered/Gather.dm').exists():   # an older game (--game): the vars the scenario reads, as they were (gathering always on)
    (world/'ZZStub.dm').write_text('Player/var/remaster_gather = 1\nturf/var/tmp/remaster_top_hp = 0\nturf/var/remaster_topcut = 0\nturf/var/remaster_holes = 0\n'); stub = '#include "ZZStub.dm"\n'
with (world/'Cave Crawlers.dme').open('a', encoding='latin-1') as f: f.write('\n' + stub + '#include "ZZMountWork.dm"\n')
hud = world/'Interface/remastered.html'; h = hud.read_text(encoding='utf-8'); k = "send('ready','');"; assert h.count(k) == 1
hud.write_text(h.replace(k, (HERE/'mw_hook.js').read_text() + '\n' + k), encoding='utf-8')
env = dict(os.environ, DOTNET_ReadyToRun='0')
with (work/'compile.log').open('w') as out:
    subprocess.run([str(dotnet), str(REPLICA/'runtime/macos-x64/compiler/DMCompiler.dll'), str(world/'Cave Crawlers.dme')], env=env, stdout=out, stderr=subprocess.STDOUT, check=True)
hints = work/'layout.json'; write_hints(world/'skin.dmf', hints)
cd = work/'client'; shutil.copytree(APPRT/'client/Space Station 14.app/Contents/Resources', cd, ignore=shutil.ignore_patterns('user_data', '.DS_Store'))
cenv = dict(env, DM_RECORDING='1', DM_SKIN_LAYOUT_HINTS=str(hints), DM_TEST_RACE='Human', DM_NATIVE_UI_PROBE=str(probe), DM_GAME_SNAPSHOT=str(probe/'game.png'), ROBUST_MODULE_ROBUST_CLIENT_WEBVIEW=str(APPRT/'webview-webkit'))
slp = work/'server.log'; clp = work/'client.log'; elog = world/'ErrorLog.txt'
results = []
def wait(cond, t, every=.2):
    d = time.monotonic() + t
    while time.monotonic() < d:
        v = cond()
        if v: return v
        time.sleep(every)
    return None
def errlog(): return elog.read_text(errors='replace') if elog.exists() else ''
def step(s):
    serial[0] += 1; s = f'{s} #{serial[0]}'   # every step new (the scenario skips a repeat), its done line ours
    (world/'mw-scene.txt').write_text(s)
    return wait(lambda: f'MW|done|{s}\n' in errlog() or errlog().endswith(f'MW|done|{s}'), 30)
serial = [0]
def probes(tries=3, need=('face0',)):
    """The page's answer; asked again (up to ~20 s) while the points needed aren't drawn yet (a level change rebuilds the view)."""
    for _ in range(10):
        P = probe1(tries)
        if P and not P.get('error') and all(k in P.get('pts', {}) for k in need): return P
        time.sleep(2)
    return P
def probe1(tries=3):
    for _ in range(tries):
        serial[0] += 1; s = str(serial[0]); step(f'probe {s}')
        def got():
            for m in re.findall(r'rm=mwprobe&value=([^\s&]+)', clp.read_text(errors='replace')):
                d = json.loads(urllib.parse.unquote(m))
                if d.get('serial') == s or 'error' in d: return d
        P = wait(got, 15)
        if P: return P
    return None
def state(tag):
    serial[0] += 1; tag = f'{tag}-{serial[0]}'   # a step the scenario hasn't seen yet (it ignores a repeat)
    step(f'state {tag}')
    lines = [l for l in errlog().splitlines() if l.startswith(('MW|unit|', 'MW|tile|', 'MW|state|'))]
    # the last block written for this tag
    found = [j for j, l in enumerate(lines) if l.startswith(f'MW|state|{tag}|')]
    if not found: return {'units': {}, 'tiles': {}, 'head': None}   # the step never ran (the game stalled or closed): no state
    i = found[-1]
    S = {'units': {}, 'tiles': {}, 'head': lines[i]}
    for l in lines[i + 1:]:
        if l.startswith('MW|state|'): break
        f = l.split('|')
        if f[1] == 'unit': S['units'][f[2]] = dict(x.split('=', 1) for x in f[3:] if '=' in x)
        if f[1] == 'tile': S['tiles'][f[2]] = dict([('at', f[3])] + [x.split('=', 1) for x in f[4:] if '=' in x])
    return S
def win():
    st = json.loads((probe/'state.json').read_text()); w = ([w for w in st['windows'] if w.get('viewports')] or [max(st['windows'], key=lambda w: w['width'] * w['height'])])[0]
    m = re.findall(r'panel\d+ hidden=false top-left=\((\d+),(\d+)\)\)? size=(\d+)x(\d+)', w['responder'])
    return w, tuple(map(int, m[0])) if m else (0, 0, w['width'], w['height'])
def frac(px, py, P):
    w, (ox, oy, pw, ph) = win()
    return (ox + px*pw/P['w'])/w['width'], (oy + py*ph/P['h'])/w['height'], w['id']
def act(pause=1.6, **x):
    (probe/'action.pending').write_text(json.dumps(x)); (probe/'action.pending').replace(probe/'action.json')
    wait(lambda: not (probe/'action.json').exists(), 10); time.sleep(pause)
def click(pt, P, kind=5, pause=1.6):
    x, y, wid = frac(pt[0], pt[1], P); act(pause, window=wid, kind=kind, x=x, y=y, code=0, modifiers=0, text='')
def drag(pa, pb, P, pause=1.6):
    x, y, wid = frac(pa[0], pa[1], P); x2, y2, _ = frac(pb[0], pb[1], P); act(pause, window=wid, kind=7, x=x, y=y, x2=x2, y2=y2, button=0, code=0, modifiers=0, text='')
def key(code, text, mods=0, pause=1.6):
    w, _ = win(); act(pause, window=w['id'], kind=4, x=0, y=0, code=code, modifiers=mods, text=text)
def record(name, ok, detail=''):
    results.append(dict(test=name, ok=None if ok is None else bool(ok), detail=detail))
    print(('SKIP ' if ok is None else 'PASS ' if ok else 'FAIL ') + name + (' — ' + json.dumps(detail)[:500] if detail != '' else ''), flush=True)
def still(name):
    if not (Path(WINREC).exists() and Path(FRAME).exists()): return
    f = work/f'{name}.mov'
    try:
        subprocess.run([WINREC, str(client.pid), '1', str(f)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
        subprocess.run([FRAME, str(f), '0.25', str(FR/f'{name}.png')], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
    except Exception as e: print('still failed', name, e)
def unit(S, ref): return next((u for u in S['units'].values() if u.get('ref') == ref), {})
def select(ref, idx, P):
    """A real click on the unit; the scenario's select step if that missed (the test is the orders, not selecting)."""
    if ref in P['units']:
        click(P['units'][ref][:2], P, pause=1.0)
    S = state('sel')
    if unit(S, ref).get('sel') != '1': step(f'select {idx}'); time.sleep(0.8)
    return unit(state('sel2'), ref).get('sel') == '1'
server = client = None
try:
    with slp.open('w') as sl, clp.open('w') as cl:
        server = subprocess.Popen([str(dotnet), str(APPRT/'server/Robust.Server.dll'), '--data-dir', str(work/'data'), '--cvar', f'opendream.json_path={world/"Cave Crawlers.json"}',
            '--cvar', 'opendream.topic_port=25843', '--cvar', 'net.bindto=127.0.0.1', '--cvar', 'net.port=12443', '--cvar', 'auth.mode=0', '--cvar', 'status.enabled=false',
            '--cvar', 'hub.advertise=false', '--cvar', 'game.auto_pause_empty=false'], env=env, stdout=sl, stderr=subprocess.STDOUT, cwd=world)
        assert wait(lambda: ' -> Ready' in slp.read_text(errors='replace'), 300), 'server not ready'
        client = subprocess.Popen([str(dotnet), str(cd/'Robust.Client.dll'), '--mount-zip', str(APPRT/'server/Content.Client.zip'), '--connect', '--connect-address', 'udp://127.0.0.1:12443',
            '--username', 'Mount', '--self-contained', '--cvar', 'web.headless=false', '--cvar', 'discord.enabled=false'], cwd=cd, env=cenv, stdout=cl, stderr=subprocess.STDOUT)
        assert wait(lambda: (probe/'game.png').exists(), 300), 'client never reached the game'
        def has_units():
            try: return 'ui-' in (probe/'hud-update.js').read_text(errors='replace')
            except OSError: return False
        wait(has_units, 120); time.sleep(4)
        ok = False
        for n in range(6):
            if step('setup') and re.search(r'MW\|ref\|', errlog()): ok = True; break
            time.sleep(5)
        assert ok, 'setup failed'
        refs = re.findall(r'MW\|ref\|[^|]*\|([^\r\n|]+)', errlog())
        u1, u2 = refs[0], refs[1]
        P = None
        for _ in range(40):
            time.sleep(1.5); P = probes()
            if P and not P.get('error') and u1 in P.get('units', {}) and u2 in P.get('units', {}): break
        assert P and not P.get('error'), f'no probe {P}'
        for _ in range(30):
            if not P.get('boot'): break
            key(105, '', pause=1.0); P = probes()   # F13 (no binding): brings the window to the front so the cover lifts
        record('the loading cover is gone', not P.get('boot'))
        still('00-start')
        if a.play:
            step('slow'); step('inside'); print('PLAY: the window is yours for', a.play, 'minutes (close it to end sooner)', flush=True)
            wait(lambda: client.poll() is not None, a.play * 60, every=2)
            raise SystemExit(0)
        has_switch = bool(P.get('btn'))
        if a.only != 'ramp':
            # 1. Gather off at the start: clicks on a tree and on the rock face walk there
            record('Gather is off at the start, and the button says so', has_switch and P['gather'] is False and P['btn']['pressed'] == 'false' and P['btn']['text'] == 'Gather off', P.get('btn'))
            select(u1, 1, P); P = probes()
            click(P['pts']['tree'][:2], P); S = state('tree-off'); U1 = unit(S, u1)
            record('Gather off: a click on a tree walks there (no Chop)', U1.get('active') in ('Move', '-') and 'Chop' not in U1.get('status', '') and 'Chop' not in U1.get('queued', ''), U1)
            P = probes(); click(P['pts']['face0'][:2], P); S = state('rock-off'); U1 = unit(S, u1)
            record('Gather off: a click on the rock face walks there (no Mine)', U1.get('active') in ('Move', '-') and 'Mine' not in U1.get('status', ''), {'unit': U1, 'face0': S['tiles'].get('face0')})
            # 2. G turns it on: one press, one change
            key(5, 'g', pause=1.5); P = probes()
            record('G turns Gather on (one press, one change), and the button lights', P['gather'] is True and P['btn']['pressed'] == 'true' and P['btn']['text'] == 'Gather on', P.get('btn'))
            still('01-gather-on')
            click(P['pts']['face0'][:2], P, pause=1.0); S = state('rock-on'); U1 = unit(S, u1); L = probes().get('last') or {}
            record('Gather on: a click on the rock face mines it', U1.get('active') == 'Mine' or any(w in U1.get('status', '') for w in ('Mine', 'Gathered')) or S['tiles']['face0'].get('dense') == '0', {'unit': U1, 'face0': S['tiles']['face0']})
            record('the page\'s instant answer after G is a dig, not a move (no stale verdict)', L.get('k') == 'mine', L)
            time.sleep(4); step('stopall')
        if a.only == 'hollow':
            # digging in up on the mountain (user: "when digging in mountains the clicker hits the top of the mountain"): a unit in
            # a hollow two blocks deep; the rock round it is cut to just over its reach, and a click on the wall's block 3 mines that block
            step('hollow'); time.sleep(3); P = probes(need=('wallb3',))
            if not P.get('gather'): key(5, 'g', pause=1.5); P = probes(need=('wallb3',))   # Gather on (an earlier section may have turned it on)
            for _ in range(6):
                if (P.get('cut') or [0])[0] > 4: break
                time.sleep(1); P = probes(need=('wallb3',))
            record('round a unit in a hollow the rock is cut to just over its head (two over its feet)', (P.get('cut') or [0])[0] > 4 and abs((P.get('cut') or [0, 0])[1] - 3.88) < 0.3, P.get('cut'))
            still('h1-hollow-cut')
            click(P['pts']['wallb3'][:2], P, pause=1.0); S = state('hollowclick'); U3 = unit(S, refs[2])
            record('a click on the wall block in reach mines that block, not the mountain top', U3.get('active') == 'Mine' and U3.get('block') == '3' or S['tiles']['wall'].get('holes', '0') != '0', {'unit': U3, 'wall': S['tiles']['wall'], 'last': probes(need=()).get('last'), 'gather': P.get('gather')})
            exc = [l for l in errlog().splitlines() if 'runtime error' in l.lower() or 'Exception occurred' in l]
            record('no runtime errors in the game log', not exc, exc[:6])
            raise SystemExit(0)
        if a.only == 'plan':
            # Plan mode (the user, 2026-10-25: "we make a plan and then they set it in motion"): the dock's Plan button, a
            # drag over the corridor's south wall on level 3, Queue it; the selected unit (on Manual) takes it up and digs
            # the three blocks by itself
            step('inside'); time.sleep(3); P = probes(need=('planA', 'planB')); pl = P.get('plan') or {}
            record('the dock has a Plan button', bool(pl.get('btn')), pl)
            click(pl['btn'], P, pause=1.2); P = probes(need=('planA', 'planB')); pl = P.get('plan') or {}
            record("Plan mode opens on the selected unit's level (3)", pl.get('on') and pl.get('level') == 3, pl)
            still('p1-plan-mode')
            drag(P['pts']['planA'][:2], P['pts']['planB'][:2], P); P = probes(need=()); pl = P.get('plan') or {}
            record('a drag over the wall marks its three blocks on level 3', pl.get('marks') == 3, pl)
            still('p2-marked')
            if pl.get('queue'): click(pl['queue'], P, pause=1.5)
            got = wait(lambda: len((probes(need=()).get('plan') or {}).get('rows') or []) > 0, 25, every=2)
            P = probes(need=()); pl = P.get('plan') or {}
            record('Queue it: the game has the dig plan on the job board', bool(got), pl.get('rows'))
            dugs = lambda S: [S['tiles'][t].get('holes', '0') != '0' or S['tiles'][t].get('dense') == '0' for t in ('pw1', 'pw2', 'pw3')]
            dug = wait(lambda: all(dugs(state('pd'))), 90, every=3)
            S = state('pdone'); still('p3-dug')
            record('the selected unit digs the plan by itself, block by block', bool(dug), {'tiles': {t: S['tiles'][t] for t in ('pw1', 'pw2', 'pw3')}, 'unit': unit(S, refs[2]), 'rows': (probes(need=()).get('plan') or {}).get('rows')})
            def reopen():   # Plan mode off and on again: it opens on the selected unit's level
                P = probes(need=()); pl = P.get('plan') or {}
                if pl.get('on') and pl.get('done'): click(pl['done'], P, pause=1.0)
                P = probes(need=()); pl = P.get('plan') or {}
                if pl.get('btn'): click(pl['btn'], P, pause=1.2)
                return probes(need=())
            # Building (stage 3): the Build tool, a drag of three blocks on open grass at level 0, one more stacked on the
            # middle one at level 1, Queue it; the selected unit fetches stone from the stockpile and lays all four
            step('buildsetup'); time.sleep(2)
            P = reopen(); pl = P.get('plan') or {}
            record('Plan mode opens again on the ground unit\'s level (0)', pl.get('on') and pl.get('level') == 0, pl)
            if pl.get('build'): click(pl['build'], P, pause=0.8)
            P = probes(need=('buildA', 'buildB'))
            drag(P['pts']['buildA'][:2], P['pts']['buildB'][:2], P); P = probes(need=()); pl = P.get('plan') or {}
            m0 = pl.get('marks')
            if pl.get('up'): click(pl['up'], P, pause=1.0)
            P = probes(need=('build2',)); click(P['pts']['build2'][:2], P, pause=1.0); P = probes(need=()); pl = P.get('plan') or {}
            record('Build: a drag marks three blocks on open ground; on level 1 a click stacks a fourth', pl.get('tool') == 'build' and m0 == 3 and pl.get('marks') == 4 and pl.get('level') == 1, {'first': m0, 'plan': pl})
            still('b1-build-marked')
            if pl.get('queue'): click(pl['queue'], P, pause=1.5)
            got = wait(lambda: any(str(r[0]).startswith('Build') for r in ((probes(need=()).get('plan') or {}).get('rows') or [])), 25, every=2)
            record('Queue it: the game has the build plan on the job board', bool(got), (probes(need=()).get('plan') or {}).get('rows'))
            hts = lambda S: [S['tiles'].get(t, {}).get('blocks') if S['tiles'].get(t, {}).get('dense') == '1' else '0' for t in ('bw1', 'bw2', 'bw3')]
            built = wait(lambda: hts(state('bd')) == ['1', '2', '1'], 150, every=4)
            S = state('bdone'); still('b2-built')
            record('the selected unit fetches stone and lays the four blocks by itself', bool(built), {'tiles': {t: S['tiles'].get(t) for t in ('bw1', 'bw2', 'bw3')}, 'unit': unit(S, refs[0])})
            # The way up: the six-high face's two top blocks (levels 4 and 5) marked from the ground, nobody up there; the
            # worker cuts steps up the rock by itself (Plans.dm RmPlanAccess) and digs them
            step('upsetup'); time.sleep(2)
            P = reopen(); pl = P.get('plan') or {}
            if pl.get('dig'): click(pl['dig'], P, pause=0.8)
            for _ in range(4):
                P = probes(need=()); pl = P.get('plan') or {}
                if pl.get('up'): click(pl['up'], P, pause=0.8)
            P = probes(need=('tall4',)); click(P['pts']['tall4'][:2], P, pause=1.0)
            P = probes(need=()); pl = P.get('plan') or {}
            if pl.get('up'): click(pl['up'], P, pause=0.8)
            P = probes(need=('tall5',)); click(P['pts']['tall5'][:2], P, pause=1.0); P = probes(need=()); pl = P.get('plan') or {}
            record('the face\'s top two blocks marked on levels 4 and 5, out of reach from the ground', pl.get('marks') == 2 and pl.get('level') == 5, pl)
            still('u1-marked')
            if pl.get('queue'): click(pl['queue'], P, pause=1.5)
            upd = wait(lambda: (lambda S: S['tiles'].get('face1', {}).get('blocks') == '4' and int(S['tiles'].get('ramps', {}).get('n', '0')) > 0)(state('ud')), 300, every=5)
            S = state('udone'); still('u2-way-up')
            record('the worker cuts its own way up (carved ramps) and digs both', bool(upd), {'face': S['tiles'].get('face1'), 'ramps': S['tiles'].get('ramps'), 'unit': unit(S, refs[1] if len(refs) > 1 else refs[0]), 'rows': (probes(need=()).get('plan') or {}).get('rows')})
            exc = [l for l in errlog().splitlines() if 'runtime error' in l.lower() or 'Exception occurred' in l]
            record('no runtime errors in the game log', not exc, exc[:6])
            raise SystemExit(0)
        if a.only == 'sky':
            # Mountain heights step 2 (planning/MOUNTAIN_HEIGHTS.md, plan B), on a game with heights_step2.py, world-look's
            # patch_sky_height.py and rts-feel's sky scripts: an ordinary mountain's top is the Surface's. The Surface view
            # draws it on the rock; the Sky view has it below, under the sky plane; from the Sky view a walker can't be sent
            # there (open sky for walkers: only flyers go), and back to the Surface
            step('skysetup'); time.sleep(3); P = probes(need=('skytopS',)); still('s1-surface')
            S = state('sky0'); MU = unit(S, refs[0])
            record('a unit on an ordinary mountain top is on the Surface view (layer 1) at its height; no peak floors in the upper layer', P.get('vz') == 1 and MU.get('feet') not in (None, '0') and (P.get('tris') or {}).get('upper', 1) == 0, {'vz': P.get('vz'), 'unit': MU, 'ys': P.get('ys', {}).get(refs[0]), 'tris': P.get('tris'), 'upperTiles': P.get('upperTiles')})
            sky = next((r for n, r in (P.get('layers') or []) if n == 'Sky'), None)
            if sky: click(sky, P, pause=2.0)
            for _ in range(8):
                P = probes(need=('skytop',))
                if P.get('vz') == 3: break
                time.sleep(1)
            time.sleep(1.5); P = probes(need=('skytop',))    # the unit eases to its height (world-look: read a second after the scene)
            still('s2-sky')
            y = (P.get('ys') or {}).get(refs[0]) or [None, None, None]
            feet = int(MU.get('feet') or 0)
            ly_ok = isinstance(y[0], (int, float)) and abs(y[0] - (feet - 10)) < 0.01
            base_ok = isinstance(y[1], (int, float)) and abs(y[1] - (feet - 10)) < 0.6
            record('the Sky view (a real click on Sky): sky height 10, the surface below at -10, the unit on the ordinary top under the sky plane at its feet - 10', P.get('vz') == 3 and P.get('skyh') == 10 and str(P.get('belowZk') or '').endswith('|-10') and ly_ok and base_ok, {'vz': P.get('vz'), 'skyh': P.get('skyh'), 'belowZk': P.get('belowZk'), 'ys(ly,base,feet)': y, 'tris': P.get('tris'), 'lvLast': P.get('lvLast')})
            if 'skytop' in (P.get('pts') or {}): click(P['pts']['skytop'][:2], P, pause=2.5)
            S = state('sky1'); MG = unit(S, refs[1] if len(refs) > 1 else refs[0])
            record('from the Sky view a walker clicked onto the ordinary top stays: open sky, only flyers go', MG.get('active') in ('-', None) and MG.get('at', '').endswith(',1'), {'walker': MG, 'notice': S['head'], 'last': P.get('last')})
            surf = next((r for n, r in (P.get('layers') or []) if n == 'Surface'), None)
            if surf: click(surf, P, pause=2.0)
            for _ in range(8):
                P = probes(need=())
                if P.get('vz') == 1: break
                time.sleep(1)
            still('s3-back')
            record('back to the Surface view (a real click on Surface)', P.get('vz') == 1, {'vz': P.get('vz')})
            exc = [l for l in errlog().splitlines() if 'runtime error' in l.lower() or 'Exception occurred' in l]
            record('no runtime errors in the game log', not exc, exc[:6])
            raise SystemExit(0)
        if a.only == 'inside':
            # walking inside the mountain (user: "it defaults to all movement at the top of the mountain stack"): a unit in a
            # corridor dug at block 3, Gather off; a click on the corridor's floor further along walks it there, at that height
            step('inside'); time.sleep(3); P = probes(need=('inside',))
            if P.get('gather'): key(5, 'g', pause=1.5); P = probes(need=('inside',))
            for _ in range(6):
                if (P.get('cut') or [0])[0] > 4: break
                time.sleep(1); P = probes(need=('inside',))
            record('round the unit in a one-block corridor the rock is cut to a low slab over its feet', (P.get('cut') or [0])[0] > 4 and abs((P.get('cut') or [0, 0])[1] - 3.3) < 0.3, P.get('cut'))
            still('i1-inside')
            S0 = state('inside0'); C = S0['tiles']['corridor']['at']
            click(P['pts']['inside'][:2], P, pause=1.0); L = probes(need=()).get('last') or {}
            got = wait(lambda: unit(state('iw'), refs[2]).get('at', '') == C + ',3', 45, every=1.5)
            U3 = unit(state('inside1'), refs[2]); still('i2-walked')
            record('a click on the corridor floor walks the unit there, inside the mountain at that height', bool(got) and U3.get('feet') == '3', {'unit': U3, 'last': L, 'corridor': C})
            key(5, 'g', pause=1.5); time.sleep(2); P = probes(need=('wall4',)); still('i3-outlines')
            record('Gather on inside: the cut goes over its reach (three blocks up)', (P.get('cut') or [0, 0])[1] > 5.5, P.get('cut'))
            click(P['pts']['wall4'][:2], P, pause=1.0); L = probes(need=()).get('last') or {}
            mined = wait(lambda: (lambda t: t.get('holes', '0') != '0' or t.get('topcut', '0') != '0')(state('nw')['tiles']['nearwall']), 40, every=1.5)
            S = state('inside2'); still('i4-mined-over')
            record('Gather on inside: a click on the wall over its level mines a block there (in reach)', bool(mined), {'wall': S['tiles']['nearwall'], 'unit': unit(S, refs[2]), 'last': L})
            exc = [l for l in errlog().splitlines() if 'runtime error' in l.lower() or 'Exception occurred' in l]
            record('no runtime errors in the game log', not exc, exc[:6])
            raise SystemExit(0)
        # 3. a one-tile ramp: right-click a one-block rock, "Carve into a ramp"; up it onto the block behind
        select(u1, 1, P); P = probes()
        click(P['pts']['rampstart'][:2], P, kind=6, pause=1.2); P = probes()
        menu = P.get('menu') or []
        carve = next((b for b in menu if 'Carve into a ramp' in b[0]), None)
        record('the right-click menu on a one-block rock offers "Carve into a ramp"', bool(carve), [m[0] for m in menu])
        if carve: click(carve[1], P, pause=1.5)
        built = wait(lambda: state('dig')['tiles']['ramp'].get('slope', '0') != '0', 90, every=2)
        S = state('ramp'); step('stopall'); step('clearitems'); time.sleep(1.5); P = probes(); still('02-ramp')
        record('the block is carved into a ramp, rising away from the carver', bool(built) and S['tiles']['ramp'].get('slope') == '1', S['tiles']['ramp'])
        record('the 3D view has it as a ramp (its slope sent to the page)', (P['kinds'].get('rampblk') or [0]*7)[6] == 1, P['kinds'].get('rampblk'))
        step('camera 0 2'); time.sleep(2.5); P = probes(need=('top',))
        record('the top behind the ramp is on screen for the click', bool(P['pts'].get('top') and P['pts']['top'][2]), P['pts'].get('top'))
        click(P['pts']['top'][:2], P, pause=0.8); S = state('topclick'); U1 = unit(S, u1)
        record('a click on the top behind the ramp: up the ramp to it', U1.get('active') in ('Climb', 'Move') or U1.get('at', '').endswith(',3'), U1)
        T0 = S['tiles']['top']['at']
        # while it climbs: one figure for each of yours, no fading ghost copy of it (the ramp "rebuilt" the unit, two showed)
        G = []
        for _ in range(12):
            Q = probes(need=());
            if Q and not Q.get('error'): G.append((Q.get('ghosts', 0), Q.get('mine', 0)))
            if unit(state('w1b'), u1).get('at', '') == T0 + ',3': break
        for _ in range(3):
            Q = probes(need=())
            if Q and not Q.get('error'): G.append((Q.get('ghosts', 0), Q.get('mine', 0)))
        record('up the ramp it stays one unit: no ghost copy, no rebuild', bool(G) and max(g for g, _ in G) == 0 and min(m for _, m in G) == max(m for _, m in G), G)
        up = wait(lambda: unit(state('w2'), u1).get('at', '') == T0 + ',3', 60, every=1.5)
        U1 = unit(state('ontop'), u1); time.sleep(1); still('03-up-the-ramp')
        record('the unit walks up the ramp onto the block', bool(up), U1)
        if a.only != 'ramp':
            # 4. up there with Gather on: a click on the next column digs it down a block; then a hop down to the ground
            try:
                P = probes(need=('dig',)); S0 = state('dig0'); h0 = int(S0['tiles']['dig']['blocks'])
                click(P['pts']['dig'][:2], P, pause=0.8); S = state('digclick'); U1 = unit(S, u1)
                record('Gather on, up top: a click on the next column is a Dig down order', U1.get('active') == 'Dig down', {'unit': U1, 'hover': P.get('hover')})
                dug = wait(lambda: int(state('w3')['tiles']['dig']['blocks']) < h0, 60, every=1.5)
                S = state('dug'); still('04-dug-down')
                record('the column is a block lower', bool(dug), {'before': h0, 'dig': S['tiles']['dig'], 'unit': unit(S, u1)})
                P = probes(need=('ground',)); click(P['pts']['ground'][:2], P, pause=0.8)
                down = wait(lambda: unit(state('w3b'), u1).get('at', '').endswith(',1'), 60, every=1.5)
                U1 = unit(state('hopped'), u1); still('05-hopped-down')
                record('a click on the ground: it hops down off the one-block top', bool(down), U1)
            except Exception as e:
                record('up top: dig down, hop down (the section ran)', False, repr(e))
            # 5. one block only, three up from the feet: a six-block face; from the ground block 2 leaves a hole, block 3 is out of reach
            try:
                step('stopall'); step('camera 0 0'); time.sleep(2.5); P = probes(need=('face1b2',)); select(u2, 2, P); P = probes(need=('face1b2',))
                click(P['pts']['face1b2'][:2], P, pause=0.8); S = state('faceclick'); U2 = unit(S, u2)
                record('a click on block 2 of a tall face is a Mine order for that block', U2.get('block') == '2' or S['tiles']['face1'].get('holes') == '4', {'unit': U2, 'face1': S['tiles']['face1']})
                holed = wait(lambda: state('w4')['tiles']['face1'].get('holes') == '4', 60, every=1.5)
                S = state('facehole'); still('06-face-hole')
                record('only that block comes out: a hole, rock below and above it', bool(holed) and S['tiles']['face1'].get('dense') == '1' and S['tiles']['face1'].get('blocks') == '6', {'face1': S['tiles']['face1'], 'unit': unit(S, u2)})
                wait(lambda: unit(state('w5'), u2).get('active') == '-', 30, every=1.5); P = probes(need=('face1b3',))
                click(P['pts']['face1b3'][:2], P, pause=1.2); S = state('reach'); U2 = unit(S, u2); P2 = probes()
                record('block 3 from the ground is out of reach: no order, and the game says so', U2.get('active') == '-' and S['tiles']['face1'].get('holes') == '4' and 'reach' in S['head'].lower(), {'unit': U2, 'head': S['head'][:200], 'hover': P2.get('hover')})
            except Exception as e:
                record('one block at a time on the face (the section ran)', False, repr(e))
            # 6. a click on the Gather button turns it off
            P = probes()
            if P.get('btn') and P['btn'].get('at'): click(P['btn']['at'], P, pause=1.2)
            P = probes()
            record('a click on the Gather button turns it off', P['gather'] is False and P['btn']['text'] == 'Gather off', P.get('btn'))
        exc = [l for l in errlog().splitlines() if 'runtime error' in l.lower() or 'Exception occurred' in l]
        record('no runtime errors in the game log', not exc, exc[:6])
finally:
    for p in (client, server):
        if p and p.poll() is None:
            p.terminate()
            try: p.wait(10)
            except Exception: p.kill()
    rep = OUT/('real-mount' + ('-' + a.tag if a.tag else '') + '.json')
    rep.write_text(json.dumps({'results': results, 'work': str(work)}, indent=1))
    try: shutil.copy2(elog, OUT/('world-log' + ('-' + a.tag if a.tag else '') + '.txt'))
    except Exception: pass
    print('wrote', rep, '|', sum(1 for r in results if r['ok']), 'pass', sum(1 for r in results if r['ok'] is False), 'fail')
