#!/usr/bin/env python3
"""RTS feel in the real Remastered client with real AppKit input (rts-feel, overnight polish 2026-10-22).
Same temporary game copy and ZZClick.dm scenario as tools/click_audit (units on open ground, a tree, rock, a sleeping
goblin), the click-audit probe hook (screen positions) and rf_hook.js (rts-feel state). Real clicks, drags, a
double-click, keys and the wheel; measures click-to-feedback times in the real WebKit page.
  python3 tools/runlock.py --who rts-feel -- caffeinate -d -i -u python3 tools/rts_feel/real_feel.py [--tag NAME]
Writes reports/polish-2026-10-22/rts-feel/real-feel[-TAG].json and stills in real-frames[-TAG]/."""
import argparse, json, os, re, shutil, subprocess, sys, tempfile, time, urllib.parse
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
APPRT = ROOT/'Dungeon Master Remastered.app/Contents/Resources/game/runtime'
REPLICA = ROOT.parent/'replica'
sys.path.insert(0, str(REPLICA/'tools'))
from skin_layout import write_hints
CA = ROOT/'tools/click_audit'
RFT = Path(__file__).resolve().parent
TT = ROOT/'tools/trailer/breaking'
ap = argparse.ArgumentParser()
ap.add_argument('--tag', default='')
ap.add_argument('--game', type=Path, default=ROOT/'game')
ap.add_argument('--only', default='', help='minimap: the minimap camera box in Top / Iso / Chase / a horizon view; dig: the dig outline; after-build: both, a second dig and a tree; two-block: the upper block first, then the floor block; walk: smooth walking, one unit and the group; chop: the chop hitch (page frames and server ticks while ~33 units are sent to chop, then re-sent as they walk); sky: the Sky level; keys: the 2006 letter keys off the keyboard')
a = ap.parse_args()
OUT = ROOT/'reports/polish-2026-10-22/rts-feel'
FR = OUT/('real-frames' + ('-' + a.tag if a.tag else '')); FR.mkdir(parents=True, exist_ok=True)
WINREC = os.environ.get('WINREC', str(TT/'winrec')); FRAME = os.environ.get('FRAME', str(TT/'frame'))
dotnet = APPRT/'dotnet/dotnet'
work = Path(tempfile.mkdtemp(prefix='dm-rtsfeel-')); world = work/'world'; probe = work/'probe'; probe.mkdir()
import atexit; atexit.register(shutil.rmtree, work, True)   # the run's world, client and logs (~160 MB) go when it ends, --only modes too
shutil.copytree(a.game, world, ignore=shutil.ignore_patterns('Cave Crawlers.json', 'ErrorLog.txt', 'units', 'players'))
(world/'units').mkdir(); (world/'players').mkdir()
shutil.copy2(CA/'ZZClick.dm', world/'ZZClick.dm')
# the race pick became a HUD card (Onboarding.dm), which the client's DM_TEST_RACE smoke answer (a native list) can't
# click: in this test copy only, the pick answers itself from test-race.txt
ob = world/'Code/Remastered/Onboarding.dm'; obt = ob.read_text(encoding='utf-8'); kk = 'proc/RemasterChooseRace(mob/who, list/menu)\n'
if kk in obt:
    obt = obt.replace(kk, kk + '\tif(fexists("test-race.txt")) return trimtext(file2text("test-race.txt"))\n', 1)
    ks = 'proc/RemasterStory(mob/who, message, title)\n'   # and the arrival story card does not wait for Begin
    if ks in obt: obt = obt.replace(ks, ks + '\tif(fexists("test-race.txt")) return\n', 1)
    ob.write_text(obt, encoding='utf-8')
    (world/'test-race.txt').write_text('Human')
with (world/'Cave Crawlers.dme').open('a', encoding='latin-1') as f: f.write('\n#include "ZZClick.dm"\n')
if a.only == 'chop':   # the chop hitch: its scenario step and page probe (tools/rts_feel/chop/)
    shutil.copy2(RFT/'chop/ZZChop.dm', world/'ZZChop.dm')
    with (world/'Cave Crawlers.dme').open('a', encoding='latin-1') as f: f.write('#include "ZZChop.dm"\n')
if a.only == 'keys':   # the 2006 letter keys: each old command logs that it ran, and does nothing (tools/rts_feel/keys/)
    shutil.copy2(RFT/'keys/ZZKeys.dm', world/'ZZKeys.dm')
    with (world/'Cave Crawlers.dme').open('a', encoding='latin-1') as f: f.write('#include "ZZKeys.dm"\n')
if a.only == 'sky':   # the sky job: its scenario steps and page probe (tools/rts_feel/sky/)
    shutil.copy2(RFT/'sky/ZZSky.dm', world/'ZZSky.dm')
    with (world/'Cave Crawlers.dme').open('a', encoding='latin-1') as f: f.write('#include "ZZSky.dm"\n')
hud = world/'Interface/remastered.html'; h = hud.read_text(encoding='utf-8'); k = "send('ready','');"; assert h.count(k) == 1
hud.write_text(h.replace(k, (CA/'hook.js').read_text() + '\n' + (RFT/'rf_hook.js').read_text() + '\n' + ((RFT/'chop/chop_hook.js').read_text() + '\n' if a.only == 'chop' else '') + ((RFT/'sky/sky_hook.js').read_text() + '\n' if a.only == 'sky' else '') + k), encoding='utf-8')
env = dict(os.environ, DOTNET_ReadyToRun='0')
if a.only == 'chop': env['RM_TICK_PROFILE'] = '1'   # the server's slow ticks (SLOWTICK lines) and seconds, beside the page's frames
with (work/'compile.log').open('w') as out:
    subprocess.run([str(dotnet), str(REPLICA/'runtime/macos-x64/compiler/DMCompiler.dll'), str(world/'Cave Crawlers.dme')], env=env, stdout=out, stderr=subprocess.STDOUT, check=True)
hints = work/'layout.json'; write_hints(world/'skin.dmf', hints)
cd = work/'client'; shutil.copytree(APPRT/'client/Space Station 14.app/Contents/Resources', cd, ignore=shutil.ignore_patterns('user_data', '.DS_Store'))
cenv = dict(env, DM_RECORDING='1', DM_SKIN_LAYOUT_HINTS=str(hints), DM_TEST_RACE='Human', DM_NATIVE_UI_PROBE=str(probe), DM_GAME_SNAPSHOT=str(probe/'game.png'), ROBUST_MODULE_ROBUST_CLIENT_WEBVIEW=str(APPRT/'webview-webkit'))
slp = work/'server.log'; clp = work/'client.log'; elog = world/'ErrorLog.txt'
results = []
def wait(cond, t):
    d = time.monotonic() + t
    while time.monotonic() < d:
        v = cond()
        if v: return v
        time.sleep(.2)
    return None
def errlog(): return elog.read_text(errors='replace') if elog.exists() else ''
def step(s):
    (world/'click-scene.txt').write_text(s)
    return wait(lambda: f'CK|done|{s}' in errlog(), 30)
serial = [0]
def probes(tries=3):
    P = R = None
    for _ in range(tries):
        serial[0] += 1; s = str(serial[0]); step(f'probe {s}')
        def got(kind):
            for m in re.findall(rf'rm={kind}&value=([^\s&]+)', clp.read_text(errors='replace')):
                d = json.loads(urllib.parse.unquote(m))
                if d.get('serial') == s or 'error' in d: return d
        P = wait(lambda: got('ckprobe'), 15); R = wait(lambda: got('rfprobe'), 15)
        if P and R: return P, R
    return P, R
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
def drag(p0, p1, P, mods=0):
    x, y, wid = frac(p0[0], p0[1], P); x2, y2, _ = frac(p1[0], p1[1], P); act(window=wid, kind=7, x=x, y=y, x2=x2, y2=y2, button=0, code=0, modifiers=mods, text='')
def key(code, text, mods=0, pause=1.6):
    w, _ = win(); act(pause, window=w['id'], kind=4, x=0, y=0, code=code, modifiers=mods, text=text)
def skey(code, mods=0, pause=1.6):
    # a key by the SDL route (SDL scancode), for the game window: AppKit-posted keys can go to another app's prompt
    w, _ = win(); act(pause, window=w['id'], kind=1, x=0, y=0, code=code, modifiers=mods, text='')
def scroll(pt, P, dy):
    x, y, wid = frac(pt[0], pt[1], P); act(window=wid, kind=11, x=x, y=y, dy=dy, code=0, modifiers=0, text='')
def record(name, ok, detail=''):
    results.append(dict(test=name, ok=None if ok is None else bool(ok), detail=detail))
    print(('SKIP ' if ok is None else 'PASS ' if ok else 'FAIL ') + name + (' — ' + json.dumps(detail)[:400] if detail != '' else ''), flush=True)
def still(name):
    # a 1 s window recording (ScreenCaptureKit, tools/trailer/winrec.swift) and its middle frame; skipped without the tools
    if not (Path(WINREC).exists() and Path(FRAME).exists()): return
    f = work/f'{name}.mov'
    try:
        subprocess.run([WINREC, str(client.pid), '1', str(f)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
        subprocess.run([FRAME, str(f), '0.25', str(FR/f'{name}.png')], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
    except Exception as e: print('still failed', name, e)
lat = {'drawn': [], 'frames': [], 'ack': [], 'step': []}
def note_latency(R, kind):
    L = (R.get('stats') or {}).get('last') or {}
    if L.get('k') == kind and L.get('drawn'):
        lat['drawn'].append(round(L['drawn'] - L['at'])); lat['frames'].append(L.get('frames'))
    if L.get('k') == kind and L.get('acked'):
        lat['ack'].append(round(L['acked'] - L['at']))
    if L.get('k') in ('move', 'attack') and L.get('k') == kind:
        after = [t for t in R.get('steps', []) if t >= L['at']]
        if after: lat['step'].append(round(after[0] - L['at']))
    return L
server = client = None
try:
    with slp.open('w') as sl, clp.open('w') as cl:
        server = subprocess.Popen([str(dotnet), str(APPRT/'server/Robust.Server.dll'), '--data-dir', str(work/'data'), '--cvar', f'opendream.json_path={world/"Cave Crawlers.json"}',
            '--cvar', 'opendream.topic_port=25791', '--cvar', 'net.bindto=127.0.0.1', '--cvar', 'net.port=12391', '--cvar', 'auth.mode=0', '--cvar', 'status.enabled=false',
            '--cvar', 'hub.advertise=false', '--cvar', 'game.auto_pause_empty=false'], env=env, stdout=sl, stderr=subprocess.STDOUT, cwd=world)
        assert wait(lambda: ' -> Ready' in slp.read_text(errors='replace'), 300), 'server not ready'
        client = subprocess.Popen([str(dotnet), str(cd/'Robust.Client.dll'), '--mount-zip', str(APPRT/'server/Content.Client.zip'), '--connect', '--connect-address', 'udp://127.0.0.1:12391',
            '--username', 'Feel', '--self-contained', '--cvar', 'web.headless=false', '--cvar', 'discord.enabled=false'], cwd=cd, env=cenv, stdout=cl, stderr=subprocess.STDOUT)
        assert wait(lambda: (probe/'game.png').exists(), 300), 'client never reached the game'
        # the race pick (DM_TEST_RACE) gives the player units a little after the game appears
        def has_units():
            try: return '"ref":"ui-' in (probe/'hud-update.js').read_text(errors='replace') or 'ui-' in (probe/'hud-update.js').read_text(errors='replace')
            except OSError: return False
        wait(has_units, 120); time.sleep(4)
        ok = False
        for n in range(6):
            name = 'setup' if n % 2 == 0 else f'probe 0{n}'
            if step(name) and name == 'setup' and re.search(r'CK\|unit\|', errlog()): ok = True; break
            time.sleep(5)
        assert ok, 'setup failed'
        refs = re.findall(r'CK\|unit\|[^|]*\|([^\r\n|]+)', errlog())
        P = R = None
        for _ in range(40):
            time.sleep(1.5); P, R = probes()
            if P and R and all(r in P.get('units', {}) for r in refs[:3]): break
        assert P and R, 'no probe'
        # the loading cover must be gone before the first click (it lifts on an animation frame, which a window behind
        # others never gets): a key with no binding (F13) brings the window to the front
        for _ in range(30):
            if not R.get('boot'): break
            key(105, '\uf710', pause=1.0); P, R = probes()
        record('the loading cover is gone', not R.get('boot'), R.get('boot'))
        record('the page has the rts-feel module', R.get('stats') is not None, R.get('error', ''))
        time.sleep(1.5); cl0 = clp.read_text(errors='replace')
        got = {k: f'rm=rfdbl&value={k}' in cl0 for k in ('first', 'second', 'third', 'fourth')}
        record('two commands sent in one task both reach the game (no dropped clicks)', got['first'] and got['second'], got)
        record('two commands sent a task apart both reach the game', got['third'] and got['fourth'], got)
        u1, u2, u3 = refs[:3]
        cam0 = R['cam'][:2]   # the scenario's site: the forge test comes back here
        still('00-start')
        if a.only == 'minimap':
            # the minimap's camera footprint (06:01 user report: a huge wedge in Iso): real clicks on the camera buttons,
            # the horizon tilt by a test step; a still of each, cropped to the minimap
            from PIL import Image
            def mm_shot(name):
                still('mm-' + name); P2, R2 = probes(); f = FR/f'mm-{name}.png'
                if f.exists() and R2.get('mini'):
                    im = Image.open(f); sc = im.width/P2['w']; top = im.height - P2['h']*sc; x, y, w, h = R2['mini']
                    im.crop((int((x - 14)*sc), int(top + (y - 14)*sc), int((x + w + 14)*sc), int(top + (y + h + 14)*sc))).save(FR/f'mm-{name}-crop.png'); f.unlink()
                F = R2.get('foot'); fx, fy = R2['cam'][:2]
                far = max((((p[0] - fx)**2 + (p[1] - fy)**2)**0.5 for p in F), default=0) if F else None
                d = lambda p, q: ((p[0] - q[0])**2 + (p[1] - q[1])**2)**0.5
                flat = F is not None and abs(d(F[0], F[1]) - d(F[3], F[2])) < 0.05 and abs(d(F[1], F[2]) - d(F[0], F[3])) < 0.05
                record(f'minimap view box, {name}: a flat 2D rectangle round the camera', flat and far is not None and far <= 45, {'corners': F, 'farthest_tiles': far and round(far, 1), 'view': R2.get('view')})
            mm_shot('default')
            B = R.get('camBtns', {})
            click(P['units'][u1][:2], P, pause=0.8)
            for bid, name in (('camTop', 'top'), ('camTop', None), ('camIso', 'iso'), ('camIso', None), ('camChase', 'chase'), ('camChase', None)):
                P, R = probes(); B = R.get('camBtns', B)
                if bid in B: click(B[bid], P, pause=1.5)
                if name: mm_shot(name)
            step('probe horizon'); time.sleep(1.5); mm_shot('horizon')
            raise SystemExit(0)
        if a.only == 'after-build':
            # after the final build (user, 06:01 / 06:08 / 07:27): the minimap box at four angles, then a dig's marks (the
            # click's ping and the order line's mark) on the block that will break, then the one above, then a tree
            from PIL import Image
            def crop_shot(name, box=None):
                still(name); P2, R2 = probes(); f = FR/f'{name}.png'
                if f.exists():
                    im = Image.open(f); sc = im.width/P2['w']; top = im.height - P2['h']*sc
                    if box: x, y, w, h = box; im = im.crop((int(x*sc), int(top + y*sc), int((x + w)*sc), int(top + (y + h)*sc)))
                    im.convert('RGB').save(FR/f'{name}.jpg', quality=80); f.unlink()
                return P2, R2
            P, R = probes(); B = R.get('camBtns', {})
            click(P['units'][u1][:2], P, pause=0.8)
            for bid, name in (('camTop', 'top'), ('camTop', None), ('camIso', 'iso'), ('camIso', None), ('camChase', 'chase'), ('camChase', None)):
                P, R = probes(); B = R.get('camBtns', B)
                if bid in B: click(B[bid], P, pause=1.5)
                if name:
                    x, y, w, h = R['mini']; P, R = crop_shot('mm-' + name, (x - 14, y - 14, w + 28, h + 28))
                    F = R.get('foot'); d = lambda p, q: ((p[0] - q[0])**2 + (p[1] - q[1])**2)**0.5
                    record(f'minimap view box, {name}: a flat 2D rectangle', bool(F) and abs(d(F[0], F[1]) - d(F[3], F[2])) < 0.05 and abs(d(F[1], F[2]) - d(F[0], F[3])) < 0.05, {'corners': F, 'view': R.get('view')})
            step('probe horizon'); time.sleep(1.5); P, R = probes(); x, y, w, h = R['mini']; crop_shot('mm-horizon', (x - 14, y - 14, w + 28, h + 28))
            rfCam = R['cam'][:2]
            if R.get('mini') and R.get('rfm'):   # back to the start's camera and zoom
                step('probe far'); time.sleep(1.0); P, R = probes(); mx0, my0, mw, mh = R['mini']; cx, cy, rr = R['rfm']; S = 2*rr + 1
                click((mx0 + (cam0[0] - (cx - rr) + 0.5)/S*mw, my0 + ((cy + rr) - cam0[1] + 0.5)/S*mh), P, pause=2.0); P, R = probes()
            alive = [r for r in (u1, u2, u3) if r in P['units']]
            xs = [P['units'][r][0] for r in alive] or [P['w']/2]; ys = [P['units'][r][1] for r in alive] or [P['h']/2]
            drag((min(xs) - 40, min(ys) - 50), (max(xs) + 40, max(ys) + 30), P); time.sleep(0.5)
            if R.get('mini') and R.get('rfm'):   # rock and tree in the middle column, as the full run does
                P, R = probes(); mx0, my0, mw, mh = R['mini']; cx, cy, rr = R['rfm']; S = 2*rr + 1; tx, ty = cam0[0] + 6, cam0[1]
                click((mx0 + (tx - (cx - rr) + 0.5)/S*mw, my0 + ((cy + rr) - ty + 0.5)/S*mh), P, pause=2.0); P, R = probes()
            for n_, tname, kind in ((1, 'rock', 'mine'), (2, 'rock', 'mine'), (3, 'tree', 'chop')):
                P, R = probes(); tt = P['tiles'].get(tname)
                if not (tt and tt[3]): record(f'{tname} click {n_}: {kind} marks', None, 'not on screen'); continue
                click(tt[:2], P, pause=0.02); still(f'work-{n_}-{tname}-ping'); time.sleep(1.5)
                P, R = crop_shot(f'work-{n_}-{tname}-order', None)
                L = (R.get('stats') or {}).get('last') or {}
                record(f'{tname} click {n_}: {kind} ping and order mark', L.get('k') == kind and bool(L.get('drawn')), {'last': L, 'notices': R.get('notices', [])[-3:]})
                if n_ == 1:   # the first block comes out before the next click (one block an order)
                    for _ in range(20):
                        time.sleep(1.5); P, R = probes()
                        if any('Mined a block' in x or 'no good stone' in x for x in R.get('notices', [])): break
            raise SystemExit(0)
        if a.only == 'chop':
            # the chop hitch (user, 2026-10-25 08:4x): ~33 units sent to chop, then half and half re-sent as they walk; the
            # page's frame intervals with what ran in each (chop_hook.js) and the server's ticks over 100 ms side by side
            (world/'chop-scene.txt').write_text('chopsetup')
            assert wait(lambda: 'CK|chop|setup' in errlog(), 60), 'chop setup failed'
            time.sleep(8)   # the new units' pictures sent and drawn before the measurement
            key(105, '\uf710', pause=1.0)   # the window to the front (a covered window redraws slowly)
            (world/'chop-scene.txt').write_text('chopgo 1')
            def chunks():
                got = {}
                for m in re.findall(r'rm=chopres&value=([^\s&]+)', clp.read_text(errors='replace')):
                    v = urllib.parse.unquote(m); sid, i, n, body = v.split('|', 3)
                    got[int(i)] = (int(n), body)
                if got and len(got) == next(iter(got.values()))[0]: return ''.join(got[i][1] for i in sorted(got))
            body = wait(chunks, 90)
            page = json.loads(body) if body else {'error': 'no result from the page'}
            tp = world/'tick-profile.log'
            lines = tp.read_text(errors='replace').splitlines() if tp.exists() else []
            # world.time -> wall clock from the per-second lines (rt = world.timeofday, deciseconds since midnight)
            secs = [dict(kv.split('=', 1) for kv in l.split('|')[1:11] if '=' in kv) for l in lines if l.startswith('RMPROF|')]
            slow = [l for l in lines if l.startswith('SLOWTICK|')]
            e0 = page.get('epoch0')
            lt = time.localtime((e0 or 0) / 1000); mid = (e0 or 0) / 1000 - (lt.tm_hour * 3600 + lt.tm_min * 60 + lt.tm_sec)
            def wall(t):   # a world.time's wall-clock ms since the page's start, by the nearest per-second line
                best = min(secs, key=lambda d: abs(float(d.get('t', 0)) - t), default=None)
                if not best or not e0: return None
                return round((mid + float(best['rt']) / 10 + (t - float(best['t'])) / 10) * 1000 - e0)
            server_slow = [dict(ms_since_page_start=wall(float(re.search(r't=([0-9.]+)', l).group(1))), line=l[:300]) for l in slow]
            win = [d for d in secs if e0 and -5000 <= (wall(float(d.get('t', 0))) or -9e9) <= 40000]
            rep = dict(page=page, server_slow_ticks=server_slow, server_seconds=[{k: d.get(k) for k in ('t', 'rt', 'cpu', 'stalls', 'mobs')} for d in win],
                       server_lines_in_window=[l[:400] for l in lines if l.startswith('RMPROF|') and any(f"t={d.get('t')}|" in l for d in win)])
            outp = OUT/f'chop-hitch{"-" + a.tag if a.tag else ""}.json'
            outp.write_text(json.dumps(rep, indent=1))
            P0 = page if isinstance(page, dict) else {}
            record('chop: page frames over 33 ms (orders / arriving)', None if 'error' in P0 else P0.get('slowCount', 0) == 0,
                   {k: P0.get(k) for k in ('fps', 'p50', 'p95', 'p99', 'worst', 'idle', 'orders', 'arriving', 'slowCount', 'error')})
            record('chop: server ticks over 100 ms in the window', len([x for x in server_slow if x['ms_since_page_start'] is not None and -2000 <= x['ms_since_page_start'] <= 36000]) == 0, len(server_slow))
            print('wrote', outp)
            raise SystemExit(0)
        if a.only == 'sky':
            # the sky job (the user, 2026-10-25): flyers up to the Sky level, a real click on its button, a real click on
            # open sky with the flyers selected (they fly there) and with the walkers (refused), and back down
            def sky(s, tag):
                (world/'sky-scene.txt').write_text(s)
                r = wait(lambda: re.findall(rf'CK\|sky\|{re.escape(tag)}\|([^\r\n]*)', errlog()), 30)
                return r[-1] if r else None
            def skyprobe(n):
                sky(f'skyprobe {n}', f'probe {n}')
                def got():
                    for m in re.findall(r'rm=skyprobe&value=([^\s&]+)', clp.read_text(errors='replace')):
                        d = json.loads(urllib.parse.unquote(m))
                        if str(d.get('serial')) == str(n) or 'error' in d: return d
                return wait(got, 20) or {}
            def units(line):
                return [(u.split(' ')[0], tuple(map(int, u.split(' ')[1].split(',')))) for u in (line or '').split('|')[-1].split(';') if ' ' in u]
            s0 = sky('skysetup', 'setup'); time.sleep(6)
            key(105, '\uf710', pause=1.0)   # the window to the front
            S1 = skyprobe(1)
            record('sky: shut with no unit up there (no Sky button, the HUD says so)', bool(S1) and not S1.get('skyShown') and not S1.get('sky'), {k: S1.get(k) for k in ('v3z', 'sky', 'skyShown')})
            s1 = sky('skyup', 'up'); time.sleep(3)
            S2 = skyprobe(2); U = units(s1)
            record("sky: the selection's Fly higher: the flyers go up, the walkers stay, the Sky button shows",
                   all((z == 3) == (k == 'flyer') for k, (x, y, z) in U) and len(U) == 5 and S2.get('skyShown'), dict(units=U, skyShown=S2.get('skyShown')))
            if S2.get('skyBtn'): click(S2['skyBtn'], S2, pause=3)
            S3 = skyprobe(3); still('sky-01-sky-level')
            after = [s for s in S3.get('sends', []) if s[0] > (S2.get('at') or 0)]   # only what the page sent after the button's click
            record('sky: the click on the Sky button gives no order (only the level)', not [s for s in after if s[1] == 'click3d'], after)
            def settled(n):   # the camera done easing to its target before a spot is picked and clicked
                for i in range(10):
                    S = skyprobe(f'{n}{i}')   # a new probe each time (the same step twice isn't read again)
                    c = S.get('cam') or [0, 0, 9, 9]
                    if abs(c[0] - c[2]) < 0.05 and abs(c[1] - c[3]) < 0.05: return S
                    time.sleep(0.5)
                return S
            record('sky: a real click on the Sky button shows the Sky level', S3.get('v3z') == 3, {k: S3.get(k) for k in ('v3z', 'skyBtn', 'notice')})
            sky('skysel flyers', 'sel flyers'); time.sleep(1.5)
            S4 = settled(4); spot = S4.get('spot')
            if spot: click(spot[:2], S4, pause=1.5)
            still('sky-02-flyers-sent'); time.sleep(8)
            U = units(sky('skywhere 1', 'where 1'))
            fl = [(x, y, z) for k, (x, y, z) in U if k == 'flyer']
            foreign = [s for s in (skyprobe('41').get('sends') or []) if s[1] == 'click3d' and s[0] > (S4.get('at') or 0) and spot and s[2] != f'{spot[2]}|{spot[3]}||0|0']
            if foreign: print('NOTE: 3D clicks this run did not send (real input from someone at the Mac):', foreign, flush=True)
            record('sky: a real click on open sky flies the flyers there', bool(spot) and len(fl) == 3 and all(z == 3 and max(abs(x - spot[2]), abs(y - spot[3])) <= 2 for x, y, z in fl) and len(set(fl)) == 3,
                   dict(spot=spot, flyers=fl, tag=S4.get('tag')))
            sky('skysel walkers', 'sel walkers'); time.sleep(1.5)
            S5 = settled(50); spot5 = S5.get('spot')
            if spot5: click(spot5[:2], S5, pause=1.2)
            S6 = skyprobe(6); U6 = units(sky('skywhere 2', 'where 2'))
            wk = [(x, y, z) for k, (x, y, z) in U6 if k == 'walker']; wk0 = [(x, y, z) for k, (x, y, z) in U if k == 'walker']
            record("sky: walkers selected, a real click on open sky: the red can't, a notice, they stay", bool(spot5) and 'deny' in S6.get('pings', []) and wk == wk0 and any('Only flyers' in n for n in S6.get('notes', []) + [S6.get('tag', '')]),
                   dict(spot=spot5, pings=S6.get('pings'), notes=S6.get('notes'), tag=S6.get('tag'), walkers=wk))
            sky('skydown', 'down'); time.sleep(4)
            S7 = skyprobe(7); still('sky-03-back-down')
            record('sky: the flyers back down: the view on the surface, no Sky button', S7.get('v3z') == 1 and not S7.get('skyShown'), {k: S7.get(k) for k in ('v3z', 'skyShown', 'notice')})
            for lg in (clp, slp):   # kept (the run's folder goes when it ends)
                try: shutil.copy2(lg, OUT/f'sky-real{"-" + a.tag if a.tag else ""}-{lg.name}')
                except OSError: pass
            outp = OUT/f'sky-real{"-" + a.tag if a.tag else ""}.json'
            outp.write_text(json.dumps(dict(results=results, probes=[S1, S2, S3, S4, S5, S6, S7]), indent=1)); print('wrote', outp)
            raise SystemExit(0)
        if a.only == 'keys':
            # the 2006 letter keys off the keyboard (the user, 2026-10-25): real AppKit keys with the game window holding the
            # keyboard (after a click on a unit in the 3D view), then with the HUD page holding it (after a HUD button)
            key(105, '\uf710', pause=1.0)   # the window to the front
            P, R = probes()
            def prompts():
                try: st = json.loads((probe/'state.json').read_text())
                except Exception: return ['?']
                return [w.get('title') or w.get('prompt') for w in st['windows'] if w.get('prompt')]
            def mark(): return len(errlog()), len(clp.read_text(errors='replace'))
            def since(m): return errlog()[m[0]:], clp.read_text(errors='replace')[m[1]:]
            def dist(c0, c1): return round(((c1[0] - c0[0])**2 + (c1[1] - c0[1])**2)**0.5, 2)
            click(P['units'][u1][:2], P, pause=1.2); P, R = probes()
            LET = [('W', 13, 'w'), ('S', 1, 's'), ('D', 2, 'd'), ('Y', 16, 'y'), ('U', 32, 'u'), ('L', 37, 'l'), ('-', 27, '-'), ('B', 11, 'b'),
                   ('R', 15, 'r'), ('H', 4, 'h'), ('J', 38, 'j'), ('K', 40, 'k'), ('M', 46, 'm'), ('O', 31, 'o'), ('T', 17, 't'), ('V', 9, 'v'), ('=', 24, '='), ('/', 44, '/')]
            got = {}
            for name, code, text in LET:
                c0 = R['cam'][:2]; m = mark()
                key(code, text, pause=1.0); P, R = probes(); ev, cv = since(m)
                got[name] = dict(verbs=re.findall(r'CK\|verb\|(\w+)', ev), prompts=prompts(), moved=dist(c0, R['cam']), page_focus=R.get('focus'), race='rm=action&value=race' in cv)
                if got[name]['prompts']: key(53, '\x1b', pause=0.8)   # close it, so the next key reaches the game
            bad = {k: v for k, v in got.items() if v['verbs'] or v['prompts'] or v['moved'] > 0.3 or v['race'] or v['page_focus']}
            record('keys: the 2006 letters do nothing with the game window holding the keyboard (no command, no prompt, no pan)', not bad, bad or {k: v['moved'] for k, v in got.items()})
            m = mark(); key(8, 'c', pause=1.0); P, R = probes(); ev, cv = since(m); c_sent = re.findall(r'rm=stack3d&value=(\w+)', cv)
            m = mark(); key(7, 'x', pause=1.0); P, R = probes(); ev2, cv2 = since(m); x_sent = re.findall(r'rm=xray3d&value=(\w+)', cv2)
            record('keys: C cuts away and X x-rays with the game window holding the keyboard (not coordinates, not an emote)',
                   bool(c_sent) and bool(x_sent) and not re.findall(r'CK\|verb\|', ev + ev2) and not prompts(), dict(stack3d=c_sent, xray3d=x_sent, verbs=re.findall(r'CK\|verb\|(\w+)', ev + ev2), focus=R.get('focus')))
            still('keys-01-cut-xray')
            key(8, 'c', pause=0.6); key(8, 'c', pause=0.6); key(7, 'x', pause=1.0)   # back to the diorama, x-ray off
            key(0, 'a', pause=1.0); P, R = probes(); on = R.get('attackMode')
            key(53, '\x1b', pause=1.0); P, R = probes(); off = not R.get('attackMode')
            record('keys: A turns Attack mode on and Esc off with the game window holding the keyboard, as before', on and off, dict(after_A=on, after_Esc=R.get('attackMode')))
            c0 = R['cam'][:2]; key(126, '\uf700', pause=0.5); key(126, '\uf700', pause=1.2); P, R = probes()
            record('keys: the Up arrow still pans (game window)', R['cam'][1] - c0[1] > 1.5, dict(before=c0, after=R['cam'][:2]))
            btn = P.get('btn', {}).get('#deselect')
            if btn:
                click(btn, P, pause=1.0); P, R = probes(); pf = R.get('focus'); c0 = R['cam'][:2]; m = mark()
                for code, text in ((13, 'w'), (1, 's'), (2, 'd'), (15, 'r')): key(code, text, pause=0.6)
                time.sleep(0.6); P, R = probes(); ev, cv = since(m)
                record('keys: W, S, D and R do nothing with the HUD page holding the keyboard', pf and dist(c0, R['cam']) < 0.3 and 'rm=action&value=race' not in cv and not re.findall(r'CK\|verb\|', ev) and not prompts(),
                       dict(page_focus=pf, moved=dist(c0, R['cam']), race='rm=action&value=race' in cv, verbs=re.findall(r'CK\|verb\|(\w+)', ev), prompts=prompts()))
                c0 = R['cam'][:2]; key(126, '\uf700', pause=0.5); key(126, '\uf700', pause=1.2); P, R = probes()
                record('keys: the Up arrow still pans (HUD page)', R['cam'][1] - c0[1] > 1.5, dict(before=c0, after=R['cam'][:2], focus=R.get('focus')))
            else:
                record('keys: W, S, D and R do nothing with the HUD page holding the keyboard', None, 'no Deselect button found')
            still('keys-02-end')
            for lg in (clp, slp):   # kept (the run's folder goes when it ends)
                try: shutil.copy2(lg, OUT/f'keys/keys-real{"-" + a.tag if a.tag else ""}-{lg.name}')
                except OSError: pass
            outp = OUT/f'keys/keys-real{"-" + a.tag if a.tag else ""}.json'
            outp.write_text(json.dumps(dict(results=results, keys=got, game=str(a.game), at=time.strftime('%Y-%m-%d %H:%M:%S'),
                                            app_server_dll=time.strftime('%Y-%m-%d %H:%M:%S', time.localtime((APPRT/'server/Robust.Server.dll').stat().st_mtime)),
                                            app_runtime=time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(APPRT.stat().st_mtime))), indent=1)); print('wrote', outp)
            raise SystemExit(0)
        if a.only == 'walk':
            # smooth walking (user, 20:1x): a walk ordered as a click would (the page hook, no input), every frame's drawn
            # positions in the real WebKit page, and a 4 s clip of it
            for case in ('walk-one', 'walk-group'):
                step(f'probe {case}'); time.sleep(2.0)
                if Path(WINREC).exists():
                    subprocess.run([WINREC, str(client.pid), '4', str(work/f'{case}.mov')], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=40)
                    for k in range(48):   # 15 a second for 3.2 s: enough to see a walk stop and start
                        subprocess.run([FRAME, str(work/f'{case}.mov'), f'{0.3 + k/15:.3f}', str(FR/f'{case}-{k:02d}.png')], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
                time.sleep(9.5); P, R = probes()
                W = R.get('walk') or {}
                U = [u for u in (W.get('units') or {}).values() if u.get('moved')]
                ok = bool(U) and all(u['pauses'] == 0 and u['snaps'] == 0 for u in U)
                record(f'{case}: smooth all the way (no pause over 150 ms, no snap over 0.3 tile)', ok, W)
            raise SystemExit(0)
        if a.only == 'two-block':
            # two-block mining (user, 08:2x): point at the block above the floor first, then at the floor block; the
            # outline follows the pointer, the upper block comes out first (dug 2), then the floor block opens the tile
            alive = [r for r in (u1, u2, u3) if r in P['units']]
            xs = [P['units'][r][0] for r in alive] or [P['w']/2]; ys = [P['units'][r][1] for r in alive] or [P['h']/2]
            drag((min(xs) - 40, min(ys) - 50), (max(xs) + 40, max(ys) + 30), P); time.sleep(0.5)
            # (no camera move: the scenario's rock is in view from the start; the 08:56 run moved it under the panels)
            for n_, part, want in ((1, 'above', 2), (2, 'floor', None)):
                P, R = probes(); RB = R.get('rockBlocks') or {}
                pt = RB.get(part)
                if not pt: record(f'two-block {n_}: a click on the {part} block', None, {'rock': RB}); continue
                click(pt, P, pause=0.02); still(f'two-{n_}-{part}-ping'); time.sleep(0.4)
                P, R = probes(); L = (R.get('stats') or {}).get('last') or {}
                for _ in range(25):
                    time.sleep(1.2); P, R = probes(); RB = R.get('rockBlocks') or {}
                    if (want and RB.get('dug') == want) or (not want and RB.get('kind') != 'wall'): break
                still(f'two-{n_}-{part}-after')
                ok = L.get('k') == 'mine' and [L.get('x'), L.get('y')] == [RB.get('x'), RB.get('y')] and ((RB.get('dug') == want) if want else RB.get('kind') != 'wall')
                record(f'two-block {n_}: a click on the {part} block takes that block', ok, {'last': L, 'rock': RB, 'notices': R.get('notices', [])[-3:]})
            raise SystemExit(0)
        if a.only == 'dig':
            # the dig outline: the band of the block that will break, on the rock's faces (user, 06:08)
            click(P['units'][u1][:2], P, pause=0.8); step('probe far'); time.sleep(1.5); P, R = probes()
            if R.get('mini') and R.get('rfm'):
                mx0, my0, mw, mh = R['mini']; cx, cy, rr = R['rfm']; S = 2*rr + 1; tx, ty = cam0[0] + 6, cam0[1]
                click((mx0 + (tx - (cx - rr) + 0.5)/S*mw, my0 + ((cy + rr) - ty + 0.5)/S*mh), P, pause=2.0); P, R = probes()
            rk = P['tiles'].get('rock')
            if rk and rk[3]:
                click(rk[:2], P, pause=0.02); still('dig-ping'); time.sleep(0.6); P, R = probes()
                L = (R.get('stats') or {}).get('last') or {}
                record('click on rock: a mine order, its outline drawn', L.get('k') == 'mine' and bool(L.get('drawn')), {'last': L})
            else:
                record('click on rock: a mine order, its outline drawn', None, 'rock not on screen')
            raise SystemExit(0)
        # 0. a first click on open ground (nothing selected yet: no order); where it landed vs where it was aimed
        click(P['tiles']['ground2'][:2], P, pause=1.0); P, R = probes()
        record('info: a first click on open ground, where it landed (page px) vs aimed', None, {'aimed': P['tiles']['ground2'][:2], 'page_w': P['w'], 'last': R['stats'].get('last'), 'mode': R.get('mode')})
        # 1. a click on a unit: its ring turns on the next frame; the game confirms
        click(P['units'][u1][:2], P); P, R = probes()
        L = note_latency(R, 'select')
        record('info: the unit click, where it landed vs aimed', None, {'aimed': P['units'][u1][:2], 'last': L, 'mode': R.get('mode')})
        record('click on a unit: ring turns at once', R['msel'] == [u1] and L.get('k') == 'select' and L.get('drawn'), {'last': L, 'sel': R['sel'], 'msel': R['msel']})
        # 2. move orders on open ground, several times: ping on the next frame, the game's reply later
        for i, tname in enumerate(['ground', 'ground2', 'ground', 'ground2', 'ground']):
            P, R0 = probes()
            pt = P['tiles'][tname]
            click(pt[:2], P, pause=0.02 if i == 1 else 0.9)
            if i == 1: still('01-move-ping')   # recorded at once, so the ping (0.72 s) is on it
            time.sleep(0.6)
            P, R = probes(); L = note_latency(R, 'move')
            record(f'move click {i + 1}: ping drawn', L.get('k') == 'move' and L.get('drawn'), {'drawn_ms': L.get('drawn') and round(L['drawn'] - L['at']), 'frames': L.get('frames'), 'ack_ms': L.get('acked') and round(L['acked'] - L['at'])})
        # 5. box around all three (once they have stopped walking from the move tests)
        prev = None
        for _ in range(12):
            P, R = probes(); now_pos = [tuple(P['units'].get(r, [0, 0, 0, 0])[2:4]) for r in (u1, u2, u3)]
            if now_pos == prev: break
            prev = now_pos; time.sleep(1.0)
        alive = [r for r in (u1, u2, u3) if r in P['units']]
        xs = [P['units'][r][0] for r in alive] or [P['w']/2]; ys = [P['units'][r][1] for r in alive] or [P['h']/2]
        drag((min(xs) - 40, min(ys) - 50), (max(xs) + 40, max(ys) + 30), P); time.sleep(0.5)
        P, R = probes(); L = note_latency(R, 'select')
        record('box select: all three, rings at once', sorted(R['msel']) == sorted([u1, u2, u3]) and L.get('k') == 'select', {'msel': R['msel'], 'last': L})
        hv = []
        for _ in range(3):
            P, R = probes(); hv.append(R.get('hover'))
        record('hover verdict on a tree / rock with units selected (model.hover)', any(h and h.get('kind') in ('Chop', 'Mine', 'Move') for h in hv), hv)
        # 6. Ctrl+2 saves the group; select one; 2 recalls the three
        # Ctrl+2 by the SDL key route (the AppKit probe action drops modifier keys; memory: test-with-real-input)
        w0, _ = win(); act(window=w0['id'], kind=1, x=0, y=0, code=31, modifiers=0x40, text=''); P, R = probes()
        record('Ctrl+2 saves the three as group 2 (SDL key route)', len(R['groups']) >= 2 and R['groups'][1] == 3, R['groups'])
        click(P['units'][u2][:2], P); P, R = probes()
        skey(31); P, R = probes()
        record('2 recalls group 2 (game focus, SDL key route)', sorted(R['msel']) == sorted([u1, u2, u3]), R['msel'])
        # 6b. keys while the HUD page has the keyboard: Deselect (a HUD button, which takes the keyboard), then 2
        btn = P.get('btn', {}).get('#deselect')
        if btn:
            click(btn, P, pause=1.0); P, R = probes(); before = R['msel']; focus_page = R.get('focus')
            key(19, '2'); P, R = probes()
            record('2 recalls group 2 while the HUD page has the keyboard', not before and sorted(R['msel']) == sorted([u1, u2, u3]), {'after_deselect': before, 'msel': R['msel'], 'page_focus': focus_page})
        else:
            record('2 recalls group 2 while the HUD page has the keyboard', None, 'no Deselect button found')
        # 6c. the Up arrow with the game window focused (skin NORTH+REP → Remaster-3D-Key → key3d): the camera pans north
        click(P['tiles']['ground'][:2], P); P, R = probes(); y0 = R['cam'][1]
        skey(82, pause=1.0); skey(82, pause=1.0); P, R = probes(); y1 = R['cam'][1]
        record('Up arrow (game focus) pans the camera north smoothly', y1 - y0 > 1.5, {'before': y0, 'after': y1, 'focus': R.get('focus')})
        # 6d. F1: the next idle unit, selected, the camera on it
        skey(58, pause=1.5); P, R = probes()
        record('F1 selects an idle unit', len(R['msel']) == 1, {'msel': R['msel'], 'cam': R['cam']})
        # 6e. a fast double tap on 2 (game focus): the camera jumps to the group (ControlGroups.dm + RemasterCamTo)
        if R.get('mini') and R.get('rfm'):   # first look 20 tiles away (a minimap click), so a jump back shows
            mx0, my0, mw, mh = R['mini']; cx, cy, rr = R['rfm']; S = 2*rr + 1; tx, ty = R['cam'][0] + 20, R['cam'][1]
            click((mx0 + (tx - (cx - rr) + 0.5)/S*mw, my0 + ((cy + rr) - ty + 0.5)/S*mh), P, pause=2.0); P, R = probes()
        c_away = R['cam'][:2]
        key(19, '2', pause=0.12); key(19, '2', pause=1.5); P, R = probes()
        record('2 twice quickly: the camera jumps back to the group', abs(R['cam'][0] - c_away[0]) > 10, {'away': c_away, 'after': R['cam'][:2], 'msel': R['msel']})
        # 7. double-click one: all of that race on screen (all three are Human)
        click(P['units'][u3][:2], P); P, R = probes()
        click(P['units'][u3][:2], P, kind=10); P, R = probes()
        record('double-click: the same race on screen', sorted(R['msel']) == sorted([u1, u2, u3]), R['msel'])
        # 3. the sleeping goblin: a red ping and the sword pointer
        # the goblin wakes and roams, so aim at it (or any hostile) where the 3D view draws it now
        foe = next((v for k, v in P['units'].items() if len(v) > 5 and v[4] == 'npc' and v[5]), None)
        if R.get('foes'): foe = R['foes'][0]   # one the 3D view draws and a click there picks (r12: one stood inside rock)
        if foe:
            click(foe[:2], P, pause=0.5); still('02-attack'); time.sleep(0.8)
            P, R = probes(); L = note_latency(R, 'attack')
            record('click on a hostile: attack ping, sword pointer', L.get('k') == 'attack' and L.get('cur') == 'attack', {'last': L})
        # 4. rock and tree: pick and axe pointers, gather pings. They sit under the side panels from the site's camera,
        # so the camera first goes 6 tiles east (a minimap click), which puts both in the middle column
        if R.get('mini') and R.get('rfm'):
            mx0, my0, mw, mh = R['mini']; cx, cy, rr = R['rfm']; S = 2*rr + 1; tx, ty = cam0[0] + 6, cam0[1]
            click((mx0 + (tx - (cx - rr) + 0.5)/S*mw, my0 + ((cy + rr) - ty + 0.5)/S*mh), P, pause=2.0); P, R = probes()
        for tname, kind, cur in (('rock', 'mine', 'mine'), ('tree', 'chop', 'chop')):
            if P['tiles'].get(tname) and P['tiles'][tname][3]:
                click(P['tiles'][tname][:2], P, pause=0.02); still(f'03-{tname}'); time.sleep(0.8)
                P, R = probes(); L = note_latency(R, kind)
                record(f'click on {tname}: {kind} ping, {cur} pointer', L.get('k') == kind and L.get('cur') == cur, {'last': L, 'css_cursor': R.get('css_cursor')})
            else:
                record(f'click on {tname}: {kind} ping, {cur} pointer', None, 'not on screen')
        # 8. wheel: the zoom eases over several frames
        mid = (P['w']*0.5, P['h']*0.45)
        scroll(mid, P, 300); P, R = probes()
        D = [s[1] for s in R.get('dist_log', [])][-40:]
        record('wheel zoom eases over several frames', len(D) >= 5, {'values': D[-12:]})
        # 9. edge scroll: the pointer at the left edge pans west, and stops when it leaves
        btn = P.get('btn', {}).get('#deselect')   # nothing selected, so the edge click orders no one away
        if btn: click(btn, P, pause=1.0); P, R = probes()
        c0 = R['cam'][:2]
        click((2, P['h']*0.5), P, pause=2.0); P, R = probes()
        c1 = R['cam'][:2]
        click((P['w']*0.5, P['h']*0.45), P, pause=1.0); P, R = probes(); c2 = R['cam'][:2]
        time.sleep(1.0); P, R = probes(); c3 = R['cam'][:2]
        record('edge scroll: the left edge pans west, and stops off the edge', c1[0] < c0[0] - 3 and abs(c3[0] - c2[0]) < 1.5, {'before': c0, 'at_edge': c1, 'left': c2, 'later': c3, 'cam_x_last_frames': [c[2] for c in R.get('cam_log', [])][-90::6]})
        # 10. minimap: a click moves the camera there
        if R.get('mini'):
            mx0, my0, mw, mh = R['mini']; tx, ty = R['cam'][0] + 30, R['cam'][1] + 10
            if R.get('rfm'):   # the local minimap: 2R+1 tiles round its centre, north up
                cx, cy, rr = R['rfm']; S = 2*rr + 1
                px, py = mx0 + (tx - (cx - rr) + 0.5)/S*mw, my0 + ((cy + rr) - ty + 0.5)/S*mh
            else:
                px, py = mx0 + tx/R['maxx']*mw, my0 + (1 - ty/R['maxy'])*mh
            click((px, py), P, pause=2.0); P, R = probes()
            record('minimap click moves the camera there', abs(R['cam'][0] - tx) < 8 and abs(R['cam'][1] - ty) < 8, {'want': [round(tx), round(ty)], 'cam': R['cam']})
        else:
            record('minimap click moves the camera there', None, 'no minimap')
        # 10b. Attack mode by A, left by Esc, both with the game window focused (SDL keys: skin A and the new ESCAPE macro).
        # Back at the site first, so the unit click lands in the 3D view (which hands the keyboard to the game window).
        if R.get('mini') and R.get('rfm'):
            mx0, my0, mw, mh = R['mini']; cx, cy, rr = R['rfm']; S = 2*rr + 1
            click((mx0 + (cam0[0] - (cx - rr) + 0.5)/S*mw, my0 + ((cy + rr) - cam0[1] + 0.5)/S*mh), P, pause=2.0); P, R = probes()
        if P['units'].get(u2) and P['units'][u2][5]:
            click(P['units'][u2][:2], P); P, R = probes()
            skey(4); P, R = probes(); on = R.get('attackMode')
            skey(41); P, R = probes(); off = not R.get('attackMode')
            record('A enters Attack mode, Esc leaves it (game window focused)', on and off, {'after_A': on, 'after_Esc': R.get('attackMode')})
        # 10c. right-click on the minimap with a unit selected: it walks there (mapmove)
        if R.get('mini') and R.get('rfm') and R['msel']:
            mx0, my0, mw, mh = R['mini']; cx, cy, rr = R['rfm']; S = 2*rr + 1; tx, ty = R['cam'][0] - 12, R['cam'][1] + 6
            click((mx0 + (tx - (cx - rr) + 0.5)/S*mw, my0 + ((cy + rr) - ty + 0.5)/S*mh), P, kind=6, pause=1.5); P, R = probes()
            step('state m'); st = [l for l in errlog().splitlines() if 'CK|u|m|' in l and 'sel=1' in l]
            record('right-click on the minimap sends the selected unit there', any(f'goal={round(tx)},{round(ty)}' in l or 'active=Move' in l for l in st), {'want': [round(tx), round(ty)], 'units': st[-2:]})
        # 10d. right-click opens the menu; a second right-click on the same spot runs its main action
        if R.get('mini') and R.get('rfm'):   # back to the site, where the 'ground' tile is
            mx0, my0, mw, mh = R['mini']; cx, cy, rr = R['rfm']; S = 2*rr + 1
            click((mx0 + (cam0[0] - (cx - rr) + 0.5)/S*mw, my0 + ((cy + rr) - cam0[1] + 0.5)/S*mh), P, pause=2.0); P, R = probes()
        gpt = P['tiles'].get('ground')
        if gpt and gpt[3] and R['msel']:
            click(gpt[:2], P, kind=6, pause=1.0); P, R = probes(); opened = R.get('menuOpen')
            click(gpt[:2], P, kind=6, pause=1.0); P, R = probes()
            record('a second right-click on the spot runs the menu\'s main action', opened and not R.get('menuOpen') and any('Started' in n or 'Move' in n for n in R.get('notices', [])[-3:]), {'opened': opened, 'after': R.get('menuOpen'), 'notices': R.get('notices', [])[-3:]})
        # 11. a workshop far from the unit: a click sends the unit beside it and its menu (a question card) opens there
        if step('forge'):
            P, R = probes()
            if R.get('mini') and R.get('rfm'):   # back to the site by a minimap click (the camera tests moved away)
                mx0, my0, mw, mh = R['mini']; cx, cy, rr = R['rfm']; S = 2*rr + 1
                click((mx0 + (cam0[0] - (cx - rr) + 0.5)/S*mw, my0 + ((cy + rr) - cam0[1] + 0.5)/S*mh), P, pause=2.0); P, R = probes()
            fg = P['tiles'].get('forge')
            st_pts = [v for v in R.get('stations', {}).values() if 'orge' in v[4]]
            if st_pts: fg = [st_pts[0][0], st_pts[0][1], 0, True]   # aim at where the 3D view draws the bench
            if fg and fg[3]:
                click(P['units'][u1][:2], P); P, R = probes()      # just one unit selected
                click(fg[:2], P, pause=0.8); P, R = probes()
                opened = None
                for _ in range(12):
                    time.sleep(1.0); P, R = probes()
                    if R.get('ask'): opened = R.get('ask'); break
                still('10-forge')
                notes = R.get('notices', [])
                step('state f'); st = [l for l in errlog().splitlines() if 'CK|u|f|' in l][-3:]
                record('click a workshop far away: the unit walks over and its menu opens there', any('walks over' in n for n in notes) and opened, {'notices': notes[-4:], 'menu': opened, 'units': st, 'last': R['stats'].get('last')})
            else:
                record('click a workshop far away: the unit walks over and its menu opens there', None, 'forge not on screen')
        # 12. zoomed right in, a click on a person's feet or head selects them (the map's pick looked 26 px round the
        # middle of the picture only). The camera is zoomed by a test step ('probe zoom', rf_hook.js); the clicks are real.
        P, R = probes()
        # close the question card with a real click on its close button (an Esc goes nowhere while no control has the
        # keyboard, and the next click then lands on the card: r19)
        if R.get('askCancel'): click(R['askCancel'], P, pause=0.8); P, R = probes()
        if R.get('ask') or R.get('menuOpen'): key(53, '\x1b', pause=0.8); P, R = probes()
        if u1 in P['units'] and P['units'][u1][5]:
            click(P['units'][u1][:2], P, pause=0.8); step('probe zoom'); time.sleep(1.5); P, R = probes()
            B = R.get('bodies', {}).get(u1); btn = P.get('btn', {}).get('#deselect'); got = {}
            if B and btn:
                for part, pt in (('feet', (B[0], B[1] - 6)), ('head', (B[2], B[3] + 8))):
                    click(btn, P, pause=0.8); P, R = probes(); before = R['msel']
                    click(pt, P, pause=0.8); P, R = probes()
                    got[part] = {'before': before, 'after': R['msel'], 'at': pt}
                tall = B[1] - B[3]
                record("zoomed in, a click on a person's feet or head selects them", all(g['before'] == [] and g['after'] == [u1] for g in got.values()) and tall > 70, {'dist': R.get('dist'), 'tall_px': tall, **got})
            else:
                record("zoomed in, a click on a person's feet or head selects them", None, {'bodies': bool(B), 'btn': bool(btn)})
        still('09-end')
finally:
    for f in (slp, clp):
        if f.exists(): shutil.copy2(f, OUT/('real-feel-' + f.name))
    for p in (client, server):
        if p and p.poll() is None:
            p.terminate()
            try: p.wait(10)
            except subprocess.TimeoutExpired: p.kill()
txt = errlog()
errs = len(re.findall(r'Exception occurred|runtime error', txt))
record('no runtime errors in the game', errs == 0, errs)
cl = clp.read_text(errors='replace') if clp.exists() else ''
js = [l for l in cl.splitlines() if 'TypeError' in l or 'ReferenceError' in l or 'SyntaxError' in l][:5]
record('no page script errors in the client log', not js, js)
med = lambda L: sorted(L)[len(L)//2] if L else None
summary = {'drawn_ms': lat['drawn'], 'drawn_frames': lat['frames'], 'ack_ms': lat['ack'], 'first_step_ms': lat['step'], 'drawn_median_ms': med(lat['drawn']), 'ack_median_ms': med(lat['ack']), 'first_step_median_ms': med(lat['step'])}
print('latency', json.dumps(summary))
(OUT/('real-feel' + ('-' + a.tag if a.tag else '') + '.json')).write_text(json.dumps({'results': results, 'latency': summary, 'at': time.strftime('%Y-%m-%d %H:%M:%S')}, indent=1) + '\n')
shutil.copy2(clp, OUT/'real-feel-client.log') if clp.exists() else None
(OUT/'real-feel-world-ErrorLog.txt').write_text(txt[-200000:])
print(f"{sum(1 for r in results if r['ok'])}/{sum(1 for r in results if r['ok'] is not None)} passed")
