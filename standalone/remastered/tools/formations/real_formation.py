#!/usr/bin/env python3
"""Group moves in the real Remastered client with real AppKit input (formations, 2026-10-23). A temporary game copy
(game/ as it is now) with tools/formations/ZZForm.dm: six of yours of mixed races in a 3 x 2 block on open ground,
then a forest to the east. Real input: a box drag round the six, a click on open ground ten tiles away, then a click in
the forest. Stills at each stage; the slot markers and every unit's position read from the real WebKit page
(the click audit's hook plus tools/formations/fm_hook.js).
  python3 tools/runlock.py --who formations -- caffeinate -d -i -u python3 tools/formations/real_formation.py
Writes reports/formations/real-formation.json and stills in reports/formations/real-frames/."""
import argparse, json, os, re, shutil, subprocess, sys, tempfile, time, urllib.parse
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
APPRT = ROOT/'Dungeon Master Remastered.app/Contents/Resources/game/runtime'
REPLICA = ROOT.parent/'replica'
sys.path.insert(0, str(REPLICA/'tools'))
from skin_layout import write_hints
CA = ROOT/'tools/click_audit'
FT = Path(__file__).resolve().parent
TT = ROOT/'tools/trailer/breaking'
ap = argparse.ArgumentParser()
ap.add_argument('--game', type=Path, default=ROOT/'game')
ap.add_argument('--only', default='', help='new: only drag to face, groups, the attack box and A + click (short); play: the scene, then the window is yours')
a = ap.parse_args()
OUT = ROOT/'reports/formations'
FR = OUT/'real-frames'; FR.mkdir(parents=True, exist_ok=True)
WINREC = os.environ.get('WINREC', str(TT/'winrec')); FRAME = os.environ.get('FRAME', str(TT/'frame'))
dotnet = APPRT/'dotnet/dotnet'
work = Path(tempfile.mkdtemp(prefix='dm-formations-')); world = work/'world'; probe = work/'probe'; probe.mkdir()
shutil.copytree(a.game, world, ignore=shutil.ignore_patterns('Cave Crawlers.json', 'ErrorLog.txt', 'units', 'players'))
(world/'units').mkdir(); (world/'players').mkdir()
shutil.copy2(FT/'ZZForm.dm', world/'ZZForm.dm')
# the race pick is a HUD card (Onboarding.dm): in this test copy only, it answers itself, and the story card doesn't wait
ob = world/'Code/Remastered/Onboarding.dm'; obt = ob.read_text(encoding='utf-8'); kk = 'proc/RemasterChooseRace(mob/who, list/menu)\n'
if kk in obt:
    obt = obt.replace(kk, kk + '\tif(fexists("test-race.txt")) return trimtext(file2text("test-race.txt"))\n', 1)
    ks = 'proc/RemasterStory(mob/who, message, title)\n'
    if ks in obt: obt = obt.replace(ks, ks + '\tif(fexists("test-race.txt")) return\n', 1)
    ob.write_text(obt, encoding='utf-8')
    (world/'test-race.txt').write_text('Human')
with (world/'Cave Crawlers.dme').open('a', encoding='latin-1') as f: f.write('\n#include "ZZForm.dm"\n')
hud = world/'Interface/remastered.html'; h = hud.read_text(encoding='utf-8'); k = "send('ready','');"; assert h.count(k) == 1
assert 'Formations (2026-10-23, formations)' in h, 'the page has no formations block (tools/formations/patch_page.py)'
# this copy only: the boot cover lifts without waiting for an animation frame (WebKit gives none to a covered window)
raf = "requestAnimationFrame(()=>requestAnimationFrame(()=>{c.classList.add('off');setTimeout(()=>c.remove(),900)}))"
if raf in h: h = h.replace(raf, "c.classList.add('off');c.remove()", 1)
hud.write_text(h.replace(k, (CA/'hook.js').read_text() + '\n' + (FT/'fm_hook.js').read_text() + '\n' + k), encoding='utf-8')
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
        time.sleep(.2)
    return None
def errlog(): return elog.read_text(errors='replace') if elog.exists() else ''
def step(s):
    (world/'click-scene.txt').write_text(s)
    done = re.compile(rf'^CK\|done\|{re.escape(s)}\s*$', re.M)      # the whole line ("state kit" is not "state kit2")
    return wait(lambda: done.search(errlog()), 30)
serial = [0]
def probes(tries=3, name=None):
    P = R = None
    for _ in range(tries):
        serial[0] += 1; s = name or str(serial[0]); step(f'probe {s}')
        def got(kind):
            for m in re.findall(rf'rm={kind}&value=([^\s&]+)', clp.read_text(errors='replace')):
                d = json.loads(urllib.parse.unquote(m))
                if d.get('serial') == s or 'error' in d: return d
        P = wait(lambda: got('ckprobe'), 15); R = wait(lambda: got('fmprobe'), 15)
        if P and R: return P, R
        name = None
    return P, R
def win():
    st = json.loads((probe/'state.json').read_text()); w = ([w for w in st['windows'] if w.get('viewports')] or [max(st['windows'], key=lambda w: w['width'] * w['height'])])[0]
    m = re.findall(r'panel\d+ hidden=false top-left=\((\d+),(\d+)\)\)? size=(\d+)x(\d+)', w['responder'])
    return w, tuple(map(int, m[0])) if m else (0, 0, w['width'], w['height'])
def frac(px, py, P):
    w, (ox, oy, pw, ph) = win()
    return (ox + px*pw/P['w'])/w['width'], (oy + py*ph/P['h'])/w['height'], w['id']
def front():
    # a covered client window draws about one frame in 0.6 s (memory: covered-window-boot-cover): bring it forward
    if client: subprocess.run(['osascript', '-e', f'tell application "System Events" to set frontmost of (first process whose unix id is {client.pid}) to true'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20)
def act(pause=1.6, **x):
    (probe/'action.pending').write_text(json.dumps(x)); (probe/'action.pending').replace(probe/'action.json')
    wait(lambda: not (probe/'action.json').exists(), 10); time.sleep(pause)
def click(pt, P, kind=5, pause=1.6):
    x, y, wid = frac(pt[0], pt[1], P); act(pause, window=wid, kind=kind, x=x, y=y, code=0, modifiers=0, text='')
def drag(p0, p1, P, mods=0, pause=1.6):
    x, y, wid = frac(p0[0], p0[1], P); x2, y2, _ = frac(p1[0], p1[1], P); act(pause, window=wid, kind=7, x=x, y=y, x2=x2, y2=y2, button=0, code=0, modifiers=mods, text='')
def key(code, text, mods=0, pause=1.6):
    w, _ = win(); act(pause, window=w['id'], kind=4, x=0, y=0, code=code, modifiers=mods, text=text)
def skey(code, mods=0, pause=1.6):
    # a key by the SDL route (SDL scancode), for the game window, as rts-feel's real_feel does for Ctrl+digit
    w, _ = win(); act(pause, window=w['id'], kind=1, x=0, y=0, code=code, modifiers=mods, text='')
def rclick(pt, P, pause=1.6):
    click(pt, P, kind=6, pause=pause)
def gstate(tag):
    # the groups (n:count), how many are selected and the selection's group (ZZForm.dm "state")
    step(f'state {tag}')
    m = None
    for l in errlog().splitlines():
        x = re.search(rf'CK\|g\|{re.escape(tag)}\|([^|]*)\|sel=(\d+)\|selgroup=(\d+)', l)
        if x: m = x
    return {'groups': m.group(1), 'sel': m.group(2), 'selgroup': m.group(3)} if m else {}
def record(name, ok, detail=''):
    results.append(dict(test=name, ok=None if ok is None else bool(ok), detail=detail))
    print(('SKIP ' if ok is None else 'PASS ' if ok else 'FAIL ') + name + (' — ' + json.dumps(detail)[:400] if detail != '' else ''), flush=True)
def still(name, at=0.25):
    # a 1 s window recording (ScreenCaptureKit, tools/trailer/winrec.swift) and one frame of it
    if not (Path(WINREC).exists() and Path(FRAME).exists()):
        print('no window recorder (WINREC/FRAME)', flush=True); return
    front()
    f = work/f'{name}.mov'
    try:
        subprocess.run([WINREC, str(client.pid), '1', str(f)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
        subprocess.run([FRAME, str(f), str(at), str(FR/f'{name}.png')], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
        p = FR/f'{name}.png'
        if p.exists():
            from PIL import Image
            Image.open(p).convert('RGB').save(FR/f'{name}.jpg', quality=82); p.unlink()
    except Exception as e: print('still failed', name, e)
def state(tag):
    step(f'state {tag}')
    rows = {}
    for l in errlog().splitlines():
        m = re.search(rf'CK\|u\|{re.escape(tag)}\|(.*)', l)
        if m:
            d = dict(x.split('=', 1) for x in m.group(1).split('|')[1:] if '=' in x); rows[d['ref']] = d
    return rows
def go(label, target, cam, expect=None):
    """A real click on `target` with the six selected; stills while they go; their state once there."""
    step(f'look {cam}'); time.sleep(1.2)
    P, R = probes(name=f'fmcam-{cam}'); time.sleep(1.0); P, R = probes()
    front(); time.sleep(0.5); P, R = probes()
    T = P['tiles'].get(target)
    record(f'{label}: the target is on screen and clickable', T and T[3], T)
    if not (T and T[3]): return None
    before = {u[0]: (u[1], u[2]) for u in R['units']}
    click(T[:2], P, pause=0.15)
    still(f'{label}-1-click', 0.2)
    P, R = probes()
    fm = R.get('fm') or {}
    sets = fm.get('sets', [])
    record(f'{label}: a marker on each of the six slots', sets and sets[-1]['n'] == 6, [(s['n'], s['pred'], s['kind']) for s in sets])
    record(f"{label}: the game's slots came back (the page's prediction confirmed or corrected)", fm.get('confirmed', 0) >= 1 and sets and not sets[-1]['pred'], {'predicted': fm.get('predicted'), 'confirmed': fm.get('confirmed'), 'push': (fm.get('lastPush') or {}).get('s')})
    record(f"{label}: how many predicted markers the game moved (0: the page's guess was exact)", True, fm.get('lastCheck'))
    M = R.get('markAt') or []
    L = R.get('last') or {}
    hit = [m for m in M if abs(m[0] - (L.get('at') or -1)) < 1]
    record(f'{label}: the markers are drawn within 100 ms of the click', hit and hit[-1][1] - hit[-1][0] < 100, {'click_to_markers_ms': hit and round(hit[-1][1] - hit[-1][0]), 'drawn_ms': L.get('drawn') and round(L['drawn'] - L['at'])})
    slots = {e[0]: (e[1], e[2]) for e in (sets[-1]['s'] if sets else [])}
    time.sleep(0.8); still(f'{label}-2-walking', 0.5)
    rows = None
    for _ in range(30):
        time.sleep(1.0); rows = state(f'{label}{_}')
        if rows and all(r['active'] == '-' for r in rows.values()): break
    still(f'{label}-3-arrived', 0.5)
    rows = rows or {}
    at = {r: tuple(map(int, d['at'].split(','))) for r, d in rows.items() if r in slots}
    record(f'{label}: all six arrived on distinct tiles', len(at) == 6 and len(set(at.values())) == 6 and all(d['active'] == '-' for d in rows.values()), {r: (d['at'], d['status']) for r, d in rows.items()})
    record(f'{label}: each stands on the slot its marker showed', all(at.get(r) == tuple(s) for r, s in slots.items()), {'slots': slots, 'at': at})
    tx, ty = TILE[target]
    record(f'{label}: one of them stands on the clicked tile (the group is anchored on the click, not round it)', (tx, ty) in set(at.values()), {'clicked': (tx, ty), 'at': sorted(at.values())})
    if expect is not None:
        role = {r: d.get('role') for r, d in rows.items()}
        record(f'{label}: they stand in the chosen formation, each on a square of its role', set(at.values()) == set(expect) and all(expect.get(at[r]) == role.get(r) for r in at), {'expected': sorted(expect.items()), 'at': sorted((at[r], role.get(r)) for r in at)})
    P, R = probes()
    left = sum(s['n'] for s in (R.get('fm') or {}).get('sets', []))
    record(f'{label}: the markers faded once they were there', left == 0, left)
    return at
TILE = {}
V = [(-1, 1, 'front'), (0, 1, 'front'), (1, 1, 'front'), (-1, -1, 'ranged'), (1, -1, 'ranged'), (0, -1, 'mage')]
def own_layout():
    # Army › Formations with real clicks: the Army button, + New, each brush and its squares (swords front, bows behind
    # them left and right, the mage behind in the middle), Use this formation, then close the panel
    front(); P, R = probes()
    b = (R.get('btn') or {}).get('army')
    record('own formation: the Army button is on screen', bool(b), R.get('btn'))
    if not b: return False
    click(b, P, pause=1.2); P, R = probes()
    n = (R.get('btn') or {}).get('new')
    record('own formation: the editor offers + New', bool(n), R.get('btn'))
    if not n: return False
    click(n, P, pause=1.0)
    P, R = probes(name='fmscroll1'); time.sleep(0.5); P, R = probes()
    # calibrate: paint one square, see which one took, and correct the rest by that many squares (the side panel is
    # zoomed, so a page position can land a square off on screen)
    B = R.get('btn') or {}
    pitch = B.get('pitch') or [24, 24]
    off = [0, 0]
    c = B.get('cells', {}).get('-1,1')
    if c:
        click(c, P, pause=0.6); P, R = probes(); B = R.get('btn') or {}
        got = [tuple(map(int, k.split(','))) for k, r in B.get('painted', [])]
        if got and got[0] != (-1, 1):
            off = [got[0][0] - (-1), got[0][1] - 1]          # squares right, squares up
        if B.get('clear'): click(B['clear'], P, pause=0.6); P, R = probes()
    record('own formation: the click offset in the side panel (calibrated)', True, {'squares_off': off, 'pitch': pitch})
    for x, y, r in V:
        # fresh positions before every click (the panel can move as the editor redraws)
        B = R.get('btn') or {}
        if B.get('brush', {}).get(r): click(B['brush'][r], P, pause=0.5); P, R = probes(); B = R.get('btn') or {}
        c = B.get('cells', {}).get(f'{x},{y}')
        if c: click((c[0] - off[0] * pitch[0], c[1] + off[1] * pitch[0]), P, pause=0.5); P, R = probes()
    time.sleep(1.0); P, R = probes()
    u = (R.get('btn') or {}).get('use')
    if u: click(u, P, pause=1.2)
    P, R = probes()
    grid = sorted(tuple(c) for c in (R.get('grid') or []))
    record('own formation: the game keeps the six squares with their roles and uses it', grid == sorted(V) and R.get('formation') == 'custom', {'grid': grid, 'formation': R.get('formation')})
    still('own-0-editor', 0.5)
    c = (R.get('btn') or {}).get('close')
    if c: click(c, P, pause=1.0)
    return grid == sorted(V)
def arrived(tag, tries=30):
    rows = None
    for k in range(tries):
        time.sleep(1.0); rows = state(f'{tag}{k}')
        if rows and all(r['active'] == '-' for r in rows.values()): break
    return rows or {}
def new_run(sx, sy):
    # 1. drag to face: a real click on mid1, then a real drag from it two tiles north: five abreast facing north, one behind
    step('look mid1'); time.sleep(1.0); P, R = probes(name='fmcam-mid1'); time.sleep(1.0); front(); P, R = probes()
    A, B = P['tiles'].get('mid1'), P['tiles'].get('face2')
    record('face: both ends of the drag on screen', A and B and A[3] and B[3], [A, B])
    if A and B:
        # the user's way: click to move, then a drag from the same spot right after
        click(A[:2], P, pause=0.3)
        drag(A[:2], B[:2], P, pause=0.3)
        still('new-1-face', 0.3)
        rows = arrived('face')
        tx, ty = sx - 6, sy + 1
        want = {(tx + d, ty) for d in (-2, -1, 0, 1, 2)} | {(tx, ty - 1)}
        at = {tuple(map(int, d['at'].split(','))) for d in rows.values()}
        record('face: click, then drag north from the spot: they line up five abreast facing north, one behind, on the pressed tile', at == want, {'want': sorted(want), 'at': sorted(at)})
        still('new-2-faced', 0.5)
    # 2. Ctrl+2 right after the drag (the keyboard is back with the game): the six are group 2, a card in the Company list
    refs6 = [r for r in re.findall(r'CK\|unit\|[^|]*\|([^\r\n|]+)', errlog())][:6]
    front(); skey(31, mods=0x40); time.sleep(0.6); P, R = probes(); B = R.get('btn') or {}
    g = gstate('g2key')
    record('Ctrl+2 right after the drag to face saves the six as group 2 (the keys reach the game again)', g.get('groups') == '2:6' and g.get('selgroup') == '2', g)
    record("the Company list shows group 2's card, the six folded into it", '2' in (B.get('cards') or {}) and not any(r in (B.get('rows') or {}) for r in refs6), {'cards': B.get('cards'), 'text': B.get('cardText'), 'rows': list((B.get('rows') or {}).keys())})
    still('new-2a-group-card', 0.4)
    # 3. right-click the card: Ungroup; right-click a row: Group the selected: a card again (group 1)
    if (B.get('cards') or {}).get('2'):
        rclick(B['cards']['2'], P, pause=0.9); P, R = probes(); B = R.get('btn') or {}
        M = {m[0]: m[1:] for m in (B.get('menu') or []) if len(m) == 3}
        record('right-click on the card: Select, Add, Ungroup', list(M) == ['Select group 2', 'Add group 2 to the selection', 'Ungroup'], list(M))
        still('new-2b-card-menu', 0.3)
        if M.get('Ungroup'): click(M['Ungroup'], P, pause=1.0); P, R = probes(); B = R.get('btn') or {}
    g = gstate('ungrouped')
    record('Ungroup: no group left, the six back in the Company list', g.get('groups') == '' and sum(1 for r in refs6 if r in (B.get('rows') or {})) == 6, {'g': g, 'rows': len(B.get('rows') or {})})
    row = (B.get('rows') or {}).get(refs6[0]) if refs6 else None
    if row:
        rclick(row, P, pause=0.9); P, R = probes(); B = R.get('btn') or {}
        M = {m[0]: m[1:] for m in (B.get('menu') or []) if len(m) == 3}
        still('new-2c-row-menu', 0.3)
        k = next((t for t in M if t.startswith('Group the selected')), None)
        record('right-click on a row: Group the selected (6)', k == 'Group the selected (6)', list(M))
        if k: click(M[k], P, pause=1.0); P, R = probes(); B = R.get('btn') or {}
    g = gstate('regrouped')
    record('Group: the six are group 1, its card in the Company list', g.get('groups') == '1:6' and '1' in (B.get('cards') or {}), {'g': g, 'cards': B.get('cards'), 'text': B.get('cardText')})
    still('new-2d-card-again', 0.4)
    # 4. the band card's Orders tab, Line: group 1's own formation; a click on open ground: a straight line
    B = R.get('btn') or {}
    if B.get('orders'): click(B['orders'], P, pause=0.8); P, R = probes(); B = R.get('btn') or {}
    if B.get('line'): click(B['line'], P, pause=1.0)
    P, R = probes()
    record("group: with group 1 selected, Line is group 1's own formation (the band card and its card say so)", R.get('formation') == 'line' and R.get('formationGroup') == 1 and 'Control group 1' in (R.get('groupNote') or '') and any('line' in t for t in ((R.get('btn') or {}).get('cardText') or [])), {'formation': R.get('formation'), 'group': R.get('formationGroup'), 'note': R.get('groupNote'), 'card': (R.get('btn') or {}).get('cardText')})
    T = P['tiles'].get('ground')
    if T and T[3]:
        click(T[:2], P, pause=0.3)
        rows = arrived('grp')
        at = {tuple(map(int, d['at'].split(','))) for d in rows.values()}
        c = (sx - 1, sy + 2)    # a line across the way they went (a diagonal when they went that way), through the clicked tile
        straight = len(at) == 6 and c in at and all((a[0] - c[0]) * (b[1] - c[1]) == (a[1] - c[1]) * (b[0] - c[0]) for a in at for b in at)
        record("group: group 1's move is a straight line of six through the clicked tile", straight, sorted(at))
        still('new-3-group-line', 0.5)
    # 5. a click on one of them (just it), then a Ctrl-click on another in the world: the whole group again
    P, R = probes()
    U = [r for r in refs6 if r in P.get('units', {}) and 0 < P['units'][r][0] < P['w'] and 0 < P['units'][r][1] < P['h']]
    if len(U) >= 2:
        click(P['units'][U[0]][:2], P, pause=0.9)
        g1 = gstate('one')
        p = P['units'][U[1]][:2]
        drag(p, p, P, mods=1 << 18, pause=1.0)     # Ctrl held, pressed and let go on the spot: a Ctrl-click
        for k in range(8):                          # the injected press takes a moment to arrive
            g2 = gstate(f'ctrlclick{k}')
            if g2.get('sel') == '6': break
            time.sleep(0.6)
        record('a click selects just one; a Ctrl-click on another of group 1 in the world selects the whole group', g1.get('sel') == '1' and g2.get('sel') == '6' and g2.get('selgroup') == '1', {'one': g1, 'ctrl': g2})
        still('new-3b-ctrl-click-group', 0.4)
    # 6. a click on the group card opens it; an archer's row in it: just that one, its quiver's arrows on its bag slot
    P, R = probes(); B = R.get('btn') or {}
    c1 = (B.get('cards') or {}).get('1')
    if c1:
        click(c1, P, pause=0.9); P, R = probes(); B = R.get('btn') or {}
        inside = [r for r in refs6 if r in (B.get('rows') or {})]
        record('a click on the group card selects them and opens it: its six rows', len(inside) == 6, {'rows': list((B.get('rows') or {}).keys()), 'text': B.get('cardText')})
        still('new-3c-card-open', 0.3)
        kit = state('kit2')
        arch = [r for r, d in kit.items() if d.get('holds') == 'Bow']
        if arch and arch[0] in (B.get('rows') or {}):
            click(B['rows'][arch[0]], P, pause=1.0); P, R = probes(); B = R.get('btn') or {}
            n = state('kit3').get(arch[0], {}).get('arrows')
            record("an archer's quiver shows its arrows on its bag slot", (B.get('quiver') or []) == [n], {'badge': B.get('quiver'), 'arrows': n})
            still('new-3d-quiver', 0.3)
        P, R = probes(); B = R.get('btn') or {}
        if (B.get('cards') or {}).get('1'): click(B['cards']['1'], P, pause=0.9)    # the six again for the attack
    # 7. each group's supplies on the left: group 1's card shows its arrows (both quivers); a click selects the six and
    # opens its combined bag
    P, R = probes(); B = R.get('btn') or {}
    sc = (B.get('sup') or {}).get('1')
    arrows = sum(int(d.get('arrows', '0')) for d in state('kit4').values())
    record("Supplies on the left: group 1's card shows its arrows (the two quivers together)", sc is not None and any(('\u27b6' + str(arrows)) in t for t in (B.get('supText') or [])), {'text': B.get('supText'), 'arrows': arrows})
    if sc:
        click(sc, P, pause=1.0); P, R = probes(); B = R.get('btn') or {}
        g = gstate('supplies')
        record("a click on it selects the group and opens its combined bag", (B.get('supBag') or 0) >= 1 and g.get('sel') == '6', {'items': B.get('supBag'), 'g': g})
        still('new-3e-supplies', 0.3)
    # 3. Attack (the HUD's button), then a real drag over the four sleeping foes: all four taken, shared out
    step('look mid2'); time.sleep(1.0); P, R = probes(name='fmcam-mid2'); time.sleep(0.8)
    arrows0 = {r: int(d.get('arrows', '0')) for r, d in state('kit').items() if d.get('holds') == 'Bow'}   # before the foes are there
    step('foes 1'); time.sleep(1.5); front(); P, R = probes()
    foes = re.findall(r'CK\|foe\|(\[0x[0-9a-f]+\])\|(\w+)\|[^|]*\|(foe\d)', errlog())
    spot = {f: P['tiles'].get(k) for f, w, k in foes}      # where each foe's tile is on screen (the probe's own units are only yours)
    seen = [f for f, w, k in foes if spot[f] and spot[f][3] and 0 < spot[f][0] < P['w'] and 0 < spot[f][1] < P['h']]
    fp = [spot[f][:2] for f in seen]
    foes = [(f, w) for f, w, k in foes]
    record('archers: the two bow units hold real bows with arrows (six each)', len(arrows0) == 2 and all(v == 6 for v in arrows0.values()), arrows0)
    record('attack: the foes are on screen (three at least)', len(fp) >= 3, fp)
    b = (R.get('btn') or {}).get('attack') or P.get('btn', {}).get('#btnAttack')
    if len(fp) >= 3 and b:
        click(b, P, pause=0.8); P, R = probes()
        x0, x1 = min(p[0] for p in fp) - 45, max(p[0] for p in fp) + 45; y0, y1 = min(p[1] for p in fp) - 55, max(p[1] for p in fp) + 35
        drag((x0, y0), (x1, y1), P)
        still('new-4-attack-box', 0.4)
        time.sleep(0.8); rows = state('abox')
        tg = [d.get('atk') for d in rows.values()]
        record('attack box: all six go for the foes in the box, spread over them (not all on one)', tg and all(t in dict(foes) for t in tg) and len(set(tg)) >= min(3, len(fp)), tg)
        # the user: "if a unit is ranged and click on a unit it will not attack": the archers shoot (from within 5 tiles)
        shot = {}
        for k in range(12):
            time.sleep(1.0); rows = state(f'shoot{k}')
            shot = {r: arrows0[r] - int(rows[r].get('arrows', '0')) for r in arrows0 if r in rows}
            if shot and all(v >= 1 for v in shot.values()): break
        record('archers in the attack box shoot their arrows at their foes', shot and all(v >= 1 for v in shot.values()), {'shot': shot, 'status': [rows[r].get('status') for r in arrows0 if r in rows]})
        still('new-4b-archers-shoot', 0.4)
        # 4. Attack, then a click (no drag) on an enemy archer: all six on the two archers, not the swordsmen
        step('foes 2'); time.sleep(1.5); front(); P, R = probes()
        last = errlog().rsplit('CK|foeset|2', 1)[-1]
        foes = [(f, w) for f, w, k in re.findall(r'CK\|foe\|(\[0x[0-9a-f]+\])\|(\w+)\|[^|]*\|(foe\d)', last)]
        spot = {f: P['tiles'].get(k) for f, k in re.findall(r'CK\|foe\|(\[0x[0-9a-f]+\])\|\w+\|[^|]*\|(foe\d)', last)}
        arch = [f for f, w in foes if w == 'Bow' and spot.get(f) and spot[f][3] and 0 < spot[f][0] < P['w'] and 0 < spot[f][1] < P['h']]
        b = (R.get('btn') or {}).get('attack') or P.get('btn', {}).get('#btnAttack')
        if arch and b:
            click(b, P, pause=0.8); P, R = probes()
            click((spot[arch[0]][0], spot[arch[0]][1] - 14), P, pause=0.8)    # on its body, a little above its feet
            still('new-5-attack-alike', 0.4)
            time.sleep(0.8); rows = state('alike')
            tg = [d.get('atk') for d in rows.values()]
            bows = {f for f, w in foes if w == 'Bow'}
            held = re.findall(r'CK\|f\|alike\|([^|]+)\|(\w*)\|(\w+)', errlog())
            record('A + a click on an enemy archer: all six go for the enemy archers (both), none for the swordsmen', tg and all(t in bows for t in tg) and len(set(tg)) == 2, {'targets': tg, 'foes then (ref, holds, kind)': held})
server = client = None
try:
    with slp.open('w') as sl, clp.open('w') as cl:
        server = subprocess.Popen([str(dotnet), str(APPRT/'server/Robust.Server.dll'), '--data-dir', str(work/'data'), '--cvar', f'opendream.json_path={world/"Cave Crawlers.json"}',
            '--cvar', 'opendream.topic_port=25793', '--cvar', 'net.bindto=127.0.0.1', '--cvar', 'net.port=12393', '--cvar', 'auth.mode=0', '--cvar', 'status.enabled=false',
            '--cvar', 'hub.advertise=false', '--cvar', 'game.auto_pause_empty=false'], env=env, stdout=sl, stderr=subprocess.STDOUT, cwd=world)
        assert wait(lambda: ' -> Ready' in slp.read_text(errors='replace'), 300), 'server not ready'
        client = subprocess.Popen([str(dotnet), str(cd/'Robust.Client.dll'), '--mount-zip', str(APPRT/'server/Content.Client.zip'), '--connect', '--connect-address', 'udp://127.0.0.1:12393',
            '--username', 'Former', '--self-contained', '--cvar', 'web.headless=false', '--cvar', 'discord.enabled=false'], cwd=cd, env=cenv, stdout=cl, stderr=subprocess.STDOUT)
        assert wait(lambda: (probe/'game.png').exists(), 300), 'client never reached the game'
        def has_units():
            try: return 'ui-' in (probe/'hud-update.js').read_text(errors='replace')
            except OSError: return False
        wait(has_units, 120); time.sleep(4)
        ok = False
        for n in range(6):
            if step('setup') and re.search(r'CK\|unit\|', errlog()): ok = True; break
            time.sleep(5)
        assert ok, 'setup failed'
        refs = re.findall(r'CK\|unit\|[^|]*\|([^\r\n|]+)', errlog())
        sx, sy = map(int, re.search(r'CK\|site\|(\d+),(\d+)', errlog()).groups())
        TILE.update(ground=(sx - 1, sy + 2), forest=(sx + 11, sy), ground3=(sx - 3, sy - 2))
        P = R = None
        for _ in range(40):
            time.sleep(1.5); P, R = probes()
            if P and R and sum(1 for r in refs if r in P.get('units', {})) >= 6: break
        assert P and R, 'no probe'
        for _ in range(30):
            if not R.get('boot'): break
            front(); key(105, '', pause=1.0); P, R = probes()
        record('the loading cover is gone', not R.get('boot'), R.get('boot'))
        record('the page has the formations block', (R.get('fm') is not None), R.get('error', ''))
        # select the six with a real box drag round them
        P, R = probes(name='fmcam-mid1'); time.sleep(1.2); P, R = probes()
        A, B = P['tiles'].get('boxa'), P['tiles'].get('boxb')
        front()
        if A and B:
            drag(A[:2], B[:2], P)
        P, R = probes()
        sel = [u for u in R['units'] if u[3]]
        if len(sel) != 6:
            key(0, 'a', mods=1 << 18)   # Ctrl+A: every unit (the scene has only these six)
            P, R = probes(); sel = [u for u in R['units'] if u[3]]
        record('six selected (a real box drag round them)', len(sel) == 6, [u[0] for u in sel])
        still('0-selected')
        if a.only == 'play':
            # a sandbox for the user to try it themselves: the six (selected), four sleeping foes; nothing is clicked for
            # them. It ends when the game window is closed (or after 20 minutes).
            step('foes'); front()
            print('PLAY: the game window is yours; close it to end', flush=True)
            end = time.monotonic() + 1200
            while client.poll() is None and time.monotonic() < end: time.sleep(2)
        elif a.only == 'new':
            new_run(sx, sy)
        else:
            start = {u[0]: (u[1], u[2]) for u in R['units']}
            at1 = go('open', 'ground', 'mid1')
            if at1:
                # across open ground the group keeps its own 3 x 2 shape: everyone moved by the same step
                moves = {(at1[r][0] - start[r][0], at1[r][1] - start[r][1]) for r in at1 if r in start}
                record('open: the group kept its own shape (everyone moved the same way)', len(moves) == 1, sorted(moves))
            at2 = go('forest', 'forest', 'mid2')
            if own_layout():
                # west: forward (-1, 0), right (0, 1): a square dx,dy stands at (x - dy, y + dx); the layout's 0,0 is empty, so
                # its square nearest the clicked tile (front 0,1) goes on it: every square moves by (0, -1) first
                tx, ty = TILE['ground3']
                go('own', 'ground3', 'mid1', expect={(tx - (dy - 1), ty + dx): r for dx, dy, r in V})
finally:
    for f in (slp, clp):
        if f.exists(): shutil.copy2(f, OUT/('real-formation-' + f.name))
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
(OUT/'real-formation.json').write_text(json.dumps({'results': results, 'at': time.strftime('%Y-%m-%d %H:%M:%S')}, indent=1) + '\n')
(OUT/'real-formation-world-ErrorLog.txt').write_text(txt[-200000:])
print(f"{sum(1 for r in results if r['ok'])}/{sum(1 for r in results if r['ok'] is not None)} passed")
shutil.rmtree(work, ignore_errors=True)
