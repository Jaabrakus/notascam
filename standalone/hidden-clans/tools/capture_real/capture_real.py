#!/usr/bin/env python3
"""Capture with rope in the real Remastered client, with real AppKit input (capture-rope, 2026-10-23).
Same temporary game copy and ZZClick.dm scenario as tools/click_audit (its "setup" and "probe" steps), plus ZZCapture.dm
(a leather rope carried by the first unit, a goblin knocked out beside it) and cap_hook.js (card buttons on screen).
Real clicks: select the unit, click the knocked-out goblin (Capture: it is tied with the rope), select the captive and
open its card's Interact tab (bound, rope, loyalty, "May break free"), Win over, Enslave, then right-click the slave.
  python3 tools/runlock.py --who capture-rope -- caffeinate -d -i -u python3 tools/capture_real/capture_real.py
Writes reports/polish-2026-10-22/capture-rope/real-capture.json and stills in real-frames/.
SHORT=1: a short run to watch or screen-record (no stills, shorter pauses): capture, the rope on the body, a line,
the cage and Take out, Stake here, tie to a tree, a rising; the card checks, Enslave, the Leatherworks and the
break-free are left out."""
import json, os, re, shutil, subprocess, sys, tempfile, time, urllib.parse
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
APPRT = ROOT/'Dungeon Master Remastered.app/Contents/Resources/game/runtime'
REPLICA = ROOT.parent/'replica'
sys.path.insert(0, str(REPLICA/'tools'))
from skin_layout import write_hints
CA = ROOT/'tools/click_audit'
HERE = Path(__file__).resolve().parent
TT = ROOT/'tools/trailer/breaking'
OUT = ROOT/'reports/polish-2026-10-22/capture-rope'
FR = OUT/'real-frames'; FR.mkdir(parents=True, exist_ok=True)
WINREC = os.environ.get('WINREC', str(TT/'winrec')); FRAME = os.environ.get('FRAME', str(TT/'frame'))
SHORT = os.environ.get('SHORT') == '1'
PAUSE = 0.9 if SHORT else 1.6
dotnet = APPRT/'dotnet/dotnet'
work = Path(tempfile.mkdtemp(prefix='dm-capture-')); world = work/'world'; probe = work/'probe'; probe.mkdir()
shutil.copytree(ROOT/'game', world, ignore=shutil.ignore_patterns('Cave Crawlers.json', 'ErrorLog.txt', 'units', 'players'))
(world/'units').mkdir(); (world/'players').mkdir()
shutil.copy2(CA/'ZZClick.dm', world/'ZZClick.dm')
shutil.copy2(HERE/'ZZCapture.dm', world/'ZZCapture.dm')
# the race pick is a HUD card the client's DM_TEST_RACE answer can't click: in this copy it answers itself (as real_feel.py)
ob = world/'Code/Remastered/Onboarding.dm'; obt = ob.read_text(encoding='utf-8'); kk = 'proc/RemasterChooseRace(mob/who, list/menu)\n'
if kk in obt:
    obt = obt.replace(kk, kk + '\tif(fexists("test-race.txt")) return trimtext(file2text("test-race.txt"))\n', 1)
    ks = 'proc/RemasterStory(mob/who, message, title)\n'
    if ks in obt: obt = obt.replace(ks, ks + '\tif(fexists("test-race.txt")) return\n', 1)
    ob.write_text(obt, encoding='utf-8')
    (world/'test-race.txt').write_text('Human')
with (world/'Cave Crawlers.dme').open('a', encoding='latin-1') as f: f.write('\n#include "ZZClick.dm"\n#include "ZZCapture.dm"\n')
hud = world/'Interface/remastered.html'; h = hud.read_text(encoding='utf-8'); k = "send('ready','');"; assert h.count(k) == 1
hud.write_text(h.replace(k, (CA/'hook.js').read_text() + '\n' + (HERE/'cap_hook.js').read_text() + '\n' + k), encoding='utf-8')
env = dict(os.environ, DOTNET_ReadyToRun='0')
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
        time.sleep(.25)
    return None
def errlog(): return elog.read_text(errors='replace') if elog.exists() else ''
def step(s):
    (world/'click-scene.txt').write_text(s)
    return wait(lambda: f'CK|done|{s}' in errlog(), 30)
def cstep(s):
    # each step carries a serial, so a repeated step is run again and its own done line waited for (an older
    # "CAP|done|caplines" in the log made the run read the state from before the step)
    serial[0] += 1; tag = f'{s} #{serial[0]}'
    (world/'cap-scene.txt').write_text(tag)
    return wait(lambda: f'CAP|done|{tag}' in errlog(), 30)
serial = [0]
def probes(tries=3):
    P = C = None
    for _ in range(tries):
        serial[0] += 1; s = str(serial[0]); step(f'probe {s}')
        def got(kind):
            for m in re.findall(rf'rm={kind}&value=([^\s&]+)', clp.read_text(errors='replace')):
                d = json.loads(urllib.parse.unquote(m))
                if d.get('serial') == s or 'error' in d: return d
        P, C = wait(lambda: got('ckprobe'), 15), wait(lambda: got('cpprobe'), 15)
        if P and C: return P, C
    return P or {}, C or {}
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
def click(pt, P, kind=5, pause=None):
    pause = PAUSE if pause is None else pause
    x, y, wid = frac(pt[0], pt[1], P); act(pause, window=wid, kind=kind, x=x, y=y, code=0, modifiers=0, text='')
def key(code, text, mods=0, pause=None):
    pause = PAUSE if pause is None else pause
    w, _ = win(); act(pause, window=w['id'], kind=4, x=0, y=0, code=code, modifiers=mods, text=text)
def record(name, ok, detail=''):
    results.append(dict(test=name, ok=bool(ok), detail=detail))
    print(('PASS ' if ok else 'FAIL ') + name + (' — ' + json.dumps(detail, ensure_ascii=False)[:400] if detail != '' else ''), flush=True)
def still(name):
    if SHORT or not (Path(WINREC).exists() and Path(FRAME).exists()): return
    f = work/f'{name}.mov'
    try:
        key(105, '\uf710', pause=0.6)   # F13 (no binding) brings the window to the front: a covered window barely redraws
        subprocess.run([WINREC, str(client.pid), '1', str(f)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
        subprocess.run([FRAME, str(f), '0.5', str(FR/f'{name}.png')], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
    except Exception as e: print('still failed', name, e)
def kvs(s):
    """key=value pieces of a CAP| line; pieces without "=" (a notice with | in it) are left out."""
    out = {}
    for kv in (s or '').split('|'):
        if '=' in kv:
            k2, v = kv.split('=', 1); out[k2] = v
    return out
def state(tag):
    cstep(f'capstate {tag}'); m = re.findall(rf'CAP\|state\|{tag}\|([^\r\n]*)', errlog())
    return kvs(m[-1]) if m else {}
def poll_state(tag, cond, t=40):
    st = {}
    for i in range(int(t / 2)):
        st = state(f'{tag}{i}')
        if cond(st): return st
        time.sleep(1.2)
    return st


def zoom(name, pt, P, rx=170, ry=130, k=3):
    """The still `name` cropped round a page point (where the captive is) and enlarged, as <name>-zoom.png."""
    if SHORT: return
    try:
        from PIL import Image
        im = Image.open(FR/f'{name}.png'); fx, fy, _ = frac(pt[0], pt[1], P); X, Y = fx*im.width, fy*im.height
        box = (int(max(0, X - rx)), int(max(0, Y - ry)), int(min(im.width, X + rx)), int(min(im.height, Y + ry)))
        c = im.crop(box); c.resize((c.width*k, c.height*k), Image.NEAREST).save(FR/f'{name}-zoom.png')
    except Exception as e: print('zoom failed', name, e)

server = client = None
def start(tag):
    """The server and the client on the temporary world (again after a restart: the same world folder, so its saves)."""
    global server, client, slp, clp
    slp = work/f'server{tag}.log'; clp = work/f'client{tag}.log'
    (probe/'game.png').unlink(missing_ok=True)
    server = subprocess.Popen([str(dotnet), str(APPRT/'server/Robust.Server.dll'), '--data-dir', str(work/f'data{tag}'), '--cvar', f'opendream.json_path={world/"Cave Crawlers.json"}',
        '--cvar', 'opendream.topic_port=25791', '--cvar', 'net.bindto=127.0.0.1', '--cvar', 'net.port=12391', '--cvar', 'auth.mode=0', '--cvar', 'status.enabled=false',
        '--cvar', 'hub.advertise=false', '--cvar', 'game.auto_pause_empty=false'], env=env, stdout=slp.open('w'), stderr=subprocess.STDOUT, cwd=world)
    assert wait(lambda: ' -> Ready' in slp.read_text(errors='replace'), 300), 'server not ready'
    client = subprocess.Popen([str(dotnet), str(cd/'Robust.Client.dll'), '--mount-zip', str(APPRT/'server/Content.Client.zip'), '--connect', '--connect-address', 'udp://127.0.0.1:12391',
        '--username', 'Captor', '--self-contained', '--cvar', 'web.headless=false', '--cvar', 'discord.enabled=false'], cwd=cd, env=cenv, stdout=clp.open('w'), stderr=subprocess.STDOUT)
    assert wait(lambda: (probe/'game.png').exists(), 300), 'client never reached the game'
    time.sleep(6)
def stop():
    for p in (client, server):
        if p and p.poll() is None:
            p.terminate()
            try: p.wait(10)
            except subprocess.TimeoutExpired: p.kill()
def front(P, C):
    for _ in range(40):
        if P.get('units') and C and not C.get('boot'): break
        key(105, '\uf710', pause=1.0); P, C = probes()
    return P, C
def select(ref):
    P, C = probes()
    for _ in range(3):
        if ref in P.get('units', {}): click(P['units'][ref][:2], P)
        P, C = probes()
        if C.get('selected') == [ref]: break
    return P, C

try:
    start('')
    ok = False
    for _ in range(6):
        if step('setup') and re.search(r'CK\|unit\|', errlog()): ok = True; break
        time.sleep(5)
    assert ok, 'setup failed'
    assert cstep('capsetup'), 'capsetup failed'
    g = re.findall(r'CAP\|goblin\|([^|]+)\|(\d+),(\d+)\|unit=([^\r\n|]+)', errlog())[-1]
    gid, u1 = g[0], g[3]
    P = C = {}
    for _ in range(40):
        time.sleep(1.5); P, C = probes()
        if P and u1 in P.get('units', {}) and gid in C.get('things', {}): break
    P, C = front(P, C)
    record('the unit and the knocked-out goblin are on screen', u1 in P.get('units', {}) and gid in C.get('things', {}), {'units': list(P.get('units', {}))[:6], 'boot': C.get('boot')})
    still('00-start')
    # 1. select the unit carrying the rope (a real click on it)
    for _ in range(3):
        click(P['units'][u1][:2], P); P, C = probes()
        if C.get('selected') == [u1]: break
    record('a click selects the unit with the rope', C.get('selected') == [u1], C.get('selected'))
    # 2. a click on the knocked-out goblin: Capture; the unit walks over and ties it with the rope; it stays out cold
    click(C['things'][gid][:2], C)
    st = poll_state('cap', lambda s: s.get('state') == 'bound', 40)
    record('a click on the knocked-out goblin ties it with the rope, and it stays out cold', st.get('state') == 'bound' and st.get('mine') == '1' and 'Leather Rope' in st.get('rope', '') and st.get('ko') == '1',
           {k: st.get(k) for k in ('state', 'rope', 'lead', 'ko', 'status', 'notice')})
    cref = st.get('ref')
    cstep('capaside'); time.sleep(2); P, C = probes(); still('01-bound-out-cold')
    if cref in P.get('units', {}): zoom('01-bound-out-cold', P['units'][cref][:2], P)
    record('in 3D the rope is on its picture', 'Rope64' in st.get('layers', '') and ':leather/' in st.get('layers', ''), st.get('layers'))
    # out cold, it can't be won over: its card's Win over is greyed out (a real click selects it, a real click on the tab)
    if not SHORT: P, C = select(cref)
    if not SHORT and C.get('tab') and C.get('heroTab') != 'interact': click(C['tab'], C); P, C = probes()
    if not SHORT: record('out cold, Win over is greyed out on its card', 'win' in C.get('capOff', []) and 'enslave' not in C.get('capOff', []), {'off': C.get('capOff'), 'text': C.get('text', '')[:120]})
    still('01c-card-out-cold')
    # 3. it comes to: up, roped, and on the leash, beside its leader
    cstep('capwake'); time.sleep(4)
    P, C = probes(); still('01b-bound-awake'); P, C = probes()
    if cref in P.get('units', {}): zoom('01b-bound-awake', P['units'][cref][:2], P)
    st = state('awake'); record('awake, still bound and led', st.get('state') == 'bound' and st.get('ko') == '0' and st.get('lead') not in ('-', None), {k: st.get(k) for k in ('state', 'ko', 'lead')})
    record('bound: no weapon in its bag (laid on the ground or taken by the captor), not picked up again', st.get('armed') == '0', {k: st.get(k) for k in ('armed', 'notice')})
    # 4. select the captive (a real click) and open its card's Interact tab (a real click on the tab)
    P, C = select(cref)
    record('a click selects the captive', C.get('selected') == [cref], C.get('selected'))
    if C.get('tab') and C.get('heroTab') != 'interact': click(C['tab'], C); P, C = probes()
    txt = C.get('text', '')
    record('its Interact tab shows bound, the rope, loyalty and the escape risk', all(w in txt for w in ('Leather Rope', 'Loyalty', 'May break free')) and set(C.get('cap', {})) >= {'win', 'enslave', 'release', 'line', 'post', 'cage'},
           {'text': txt[:200], 'buttons': list(C.get('cap', {}))})
    still('02-card')
    # 5. a line: two more captives on the leader's rope, then (a real right-click on one, with another selected) roped behind it
    cstep('capline'); time.sleep(2)
    ln = re.findall(r'CAP\|line\|([^|]+)\|', errlog())
    if len(ln) >= 2 and not SHORT:
        g2, g3 = ln[-2], ln[-1]
        cstep('capapart'); time.sleep(1.5)
        P, C = select(g3)
        P, C = probes()
        if g2 in P.get('units', {}): click(P['units'][g2][:2], P, kind=6)
        P, C = probes()
        rope_btn = next((k for k in C.get('menuBtns', {}) if k.startswith('Rope ') and 'behind' in k), None)
        record('right-click on a captive, another selected: "Rope … behind them"', bool(rope_btn), list(C.get('menuBtns', {})))
        if rope_btn: click(C['menuBtns'][rope_btn], C)
        time.sleep(1.5); cstep('caplines')
        links = {m[0]: kvs(m[1]) for m in re.findall(r'CAP\|link\|([^|]+)\|([^\r\n]*)', errlog())}
        record('Goblin Three is roped behind Goblin Two', links.get('Goblin Three', {}).get('lead') == 'Goblin Two', links)
        key(53, '\x1b', pause=0.8)
        P, C = probes(); still('03-line')
        if cref in P.get('units', {}): zoom('03-line', P['units'][cref][:2], P, rx=260, ry=150)
    # 6. a cage: the first captive selected, a real right-click on an empty cage: "Put … in this cage"
    cstep('capcage'); time.sleep(2)
    cg = re.findall(r'CAP\|cage\|(\[[^\]]+\])\|', errlog())
    P, C = select(cref)
    P, C = probes()
    cpt = C.get('things', {}).get(cg[-1]) if cg else None
    if cpt: click(cpt[:2], C, kind=6)
    P, C = probes()
    put = next((k for k in C.get('menuBtns', {}) if k.startswith('Put ') and 'cage' in k), None)
    record('right-click on a cage, a captive selected: "Put … in this cage"', bool(put), list(C.get('menuBtns', {})))
    if put: click(C['menuBtns'][put], C)
    st = poll_state('cage', lambda s: s.get('odds') == '0' and 'cage' in s.get('notice', '').lower() or s.get('state') != 'bound', 20)
    cstep('caplines'); links = {m[0]: kvs(m[1]) for m in re.findall(r'CAP\|link\|([^|]+)\|([^\r\n]*)', errlog())}
    caged = any(v.get('caged') == '1' for v in links.values())
    record('the captive is shut in the cage', caged, {'notice': st.get('notice', '')[:160], 'links': links})
    record('caged: still no weapon on them', st.get('armed') == '0', st.get('armed'))
    record('in the cage the rope comes off them, back to the one who put them in', 'rope back' in st.get('notice', '') and st.get('rope') in ('', '-', None), {'notice': st.get('notice', '')[:200], 'rope': st.get('rope')})
    key(53, '\x1b', pause=0.8)
    P, C = probes(); still('04-caged')
    if cpt: zoom('04-caged', cpt[:2], C, rx=200, ry=150)
    th = C.get('things', {}); ct = th.get(cg[-1]) if cg else None; ut = th.get(cref)
    record("in 3D: the cage's own model, made tall, with the captive standing in it on its tile", bool(ct and ut and ct[5] == 'cage' and ct[6] == 1 and ut[2:4] == ct[2:4]), {'cage': ct, 'captive': ut})
    # 6b. Take out (a real click on its card's button): the one with the rope lets them out and ties them up beside it
    P, C = select(cref)
    if C.get('tab') and C.get('heroTab') != 'interact': click(C['tab'], C); P, C = probes()
    if C.get('cap', {}).get('uncage'): click(C['cap']['uncage'], C)
    st = poll_state('out', lambda s: s.get('rope') not in ('', '-', None), 20)
    cstep('caplines'); links = {m[0]: kvs(m[1]) for m in re.findall(r'CAP\|link\|([^|]+)\|([^\r\n]*)', errlog())}
    cxy = re.findall(r'CAP\|cage\|\[[^\]]+\]\|(\d+,\d+)', errlog())
    record('Take out: one of yours with the rope lets them out and ties them up beside the cage', links.get('Goblin Scout', {}).get('caged') == '0' and st.get('rope') not in ('', '-', None) and bool(cxy) and st.get('at') not in ('-', None, cxy[-1]), {'notice': st.get('notice', '')[:200], 'rope': st.get('rope'), 'at': st.get('at'), 'cage': cxy[-1] if cxy else None, 'buttons': list(C.get('cap', {}))})
    key(53, '\x1b', pause=0.8)
    # 6c. Stake here (a real click on its card's button): one of yours with a log of wood cuts a stake, drives it in
    # beside them and ties them to it
    cstep('capwood')
    P, C = select(cref)
    if C.get('tab') and C.get('heroTab') != 'interact': click(C['tab'], C); P, C = probes()
    if C.get('cap', {}).get('stake'): click(C['cap']['stake'], C)
    st = poll_state('stake', lambda s: s.get('kind') == 'stake', 30)
    P, C = probes()
    record('Stake here: a stake cut from a log, driven into the ground beside them, tied to it (the card says so)', st.get('kind') == 'stake' and st.get('tied') == '1' and 'stake' in C.get('text', '').lower(),
           {'notice': st.get('notice', '')[:200], 'kind': st.get('kind'), 'card': C.get('text', '')[:100], 'buttons': list(C.get('cap', {}))})
    key(53, '\x1b', pause=0.8)
    P, C = probes(); still('04d-staked')
    ut = C.get('things', {}).get(cref)
    if ut: zoom('04d-staked', ut[:2], C, rx=200, ry=150)
    # 6d. Tied to anything: the captive selected, a real right-click on a tree a few tiles off, "Tie … to this"
    cstep('captree'); time.sleep(2)
    P, C = select(cref)
    P, C = probes()
    tp = P.get('tiles', {}).get('captree')
    if tp: click(tp[:2], P, kind=6)
    P, C = probes()
    tie = next((k for k in C.get('menuBtns', {}) if k.startswith('Tie ') and k.endswith(' to this')), None)
    if tie: click(C['menuBtns'][tie], C)
    st = poll_state('tree', lambda s: s.get('kind') == 'tree', 40)
    record('right-click on a tree, a captive selected: "Tie … to this"; they are taken to it and tied to it', bool(tie) and st.get('kind') == 'tree' and st.get('tied') == '1',
           {'menu': list(C.get('menuBtns', {})), 'notice': st.get('notice', '')[:200], 'kind': st.get('kind')})
    key(53, '\x1b', pause=0.8)
    P, C = probes(); still('04e-tree')
    ut = C.get('things', {}).get(cref)
    if ut: zoom('04e-tree', ut[:2], C, rx=220, ry=160)
    if not SHORT:
        # 7. Enslave Goblin Two (a real click on its card's Enslave): watched, since the run of 10:16 stopped answering there
        if len(ln) >= 2:
            P, C = select(ln[-2])
            if C.get('tab') and C.get('heroTab') != 'interact': click(C['tab'], C); P, C = probes()
            if C.get('cap', {}).get('enslave'): click(C['cap']['enslave'], C)
            time.sleep(2)
            ok_step = cstep('caplines')
            if not ok_step: record('the game still answers after Enslave', False, errlog()[-1500:])
            links = {m[0]: kvs(m[1]) for m in re.findall(r'CAP\|link\|([^|]+)\|([^\r\n]*)', errlog())}
            P, C = probes()
            record('Enslave from the card: a slave, the card down to Win over and Release', ok_step and set(C.get('cap', {})) == {'win', 'release'}, {'buttons': list(C.get('cap', {})), 'text': C.get('text', '')[:120]})
            still('05-slave')
        # 8. Rope at the Leatherworks through its own card: right-click it, Use / open, Leather Rope
        cstep('capshop'); time.sleep(2)
        sh = re.findall(r'CAP\|shop\|[^|]+\|unit=([^\r\n|]+)', errlog())
        u1 = sh[-1] if sh else u1
        P, C = select(u1)
        P, C = probes()
        shop = P.get('tiles', {}).get('forge')
        if shop: click(shop[:2], P, kind=6)
        P, C = probes()
        if C.get('menuBtns', {}).get('Use / open'): click(C['menuBtns']['Use / open'], C); time.sleep(1.5)
        P, C = probes()
        record('the Leatherworks card lists Leather Rope and Silk Rope', set(C.get('ucOpts', [])) >= {'Leather Rope', 'Silk Rope'}, {'usecard': C.get('usecard'), 'ropes': C.get('ucOpts'), 'menu': list(C.get('menuBtns', {}))})
        still('06-leatherworks-card')
        if C.get('rope'): click(C['rope'], C)
        it = {}
        for i in range(15):
            time.sleep(2); cstep(f'capitems c{i}')
            m = re.findall(rf'CAP\|items\|c{i}\|([^\r\n]*)', errlog())
            it = kvs(m[-1]) if m else {}
            if int(it.get('lying', 0) or 0) + int(it.get('carried', 0) or 0) > 0: break
        record('choosing Leather Rope: the unit walks over and makes a rope from its skin', int(it.get('lying', 0) or 0) + int(it.get('carried', 0) or 0) > 0 and it.get('skins') == '0', it)
        # 9. A captive tied with plant rope and left alone breaks free (its tries at the rope come every 0.2 s here)
        cstep('capweak')
        w_ = re.findall(r'CAP\|weak\|free=([^\r\n]*)', errlog())
        wd = kvs('free=' + w_[-1]) if w_ else {}
        P, C = probes(); still('08-broke-free')
        record('left alone in plant rope, it breaks free, back to its side, and runs; the log says so', wd.get('free') == '1' and wd.get('mine') == '0' and wd.get('logged') == '1', wd)
    # 10. Five slaves with nobody watching them rise up (the revolt roll every 0.1 s here)
    cstep('caprevolt')
    r_ = re.findall(r'CAP\|revolt\|([^\r\n]*)', errlog())
    rd = kvs(r_[-1]) if r_ else {}
    P, C = probes(); still('09-revolt'); time.sleep(8); P, C = probes(); still('09b-revolt-later')
    record('five unguarded slaves rise up; the log says so', int(rd.get('rose', 0) or 0) >= 1 and rd.get('logged') == '1', rd)
    rs = wait(lambda: re.findall(r'CAP\|rising\|([^\r\n]*)', errlog()), 30)
    rs = kvs(rs[-1]) if rs else {}
    record('the risers take up their spears from the ground, strike at one of yours, then run', int(rs.get('armed', 0) or 0) >= 3 and int(rs.get('struck', 0) or 0) >= 1 and int(rs.get('ran', 0) or 0) >= 1, rs)
except Exception as ex:
    record('the run went through', False, repr(ex))
finally:
    stop()
txt = errlog(); (OUT/'real-world-ErrorLog.txt').write_text(txt[-20000:])
errs = re.findall(r'(?:Exception occurred|runtime error)[^\r\n]*', txt)
record('no runtime errors in the game', not errs, errs[:3])
json.dump(results, open(OUT/'real-capture.json', 'w'), indent=1, ensure_ascii=False)
print(f"{sum(r['ok'] for r in results)}/{len(results)} passed")
shutil.rmtree(work, ignore_errors=True)
