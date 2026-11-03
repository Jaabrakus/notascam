#!/usr/bin/env python3
"""Slot markers for group moves, in headless Chrome (formations, 2026-10-23): the real HUD page (?overlay) with a real 3D
scene (tests/lairs-dump-arena) and six of your units side by side, selected. Trusted mouse clicks from Playwright, no
server: commands are recorded, and the game's answer (rmSlots3D, then the units' steps as move3D) is played back.

Checks: a click on open ground puts a marker on every unit's slot on the first frame after it (before the game says
anything), the slots are distinct open tiles in the group's shape; the game's slots replace them (a marker that
differs glides over); each marker fades as its unit gets there; Shift keeps the earlier leg's markers; a click on a
foe or with one unit makes none; attack-move markers are red; no script errors; the drawing costs well under a ms.

  python3 tools/formations/headless_slots.py [--html PAGE] [--before PAGE_WITHOUT_BLOCK] [--shots DIR]
With --before, the same click is shot on that page too and a side-by-side image is written (before | after)."""
import argparse
import json
import tempfile
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = Path(__file__).resolve().parents[2]
OUT = BASE/'reports/formations'
ap = argparse.ArgumentParser()
ap.add_argument('--html', type=Path, default=BASE/'game/Interface/remastered.html')
ap.add_argument('--before', type=Path, default=None)
ap.add_argument('--scene', type=Path, default=BASE/'tests/lairs-dump-arena/lairs-3d-12.json')
ap.add_argument('--shots', type=Path, default=OUT/'headless')
ap.add_argument('--out', type=Path, default=OUT/'headless-slots.json')
a = ap.parse_args()

scene0 = json.loads(a.scene.read_text())
T = scene0['terrain']
kinds = T['kinds']
def kind_at(x, y):
    i, j = x - T['x0'], y - T['y0']
    if 0 <= i < T['w'] and 0 <= j < T['h']:
        v = T['tiles'][j*T['w'] + i]
        return kinds[v - 1]['kind'] if v else None
floor = lambda x, y: kind_at(x, y) in ('floor', 'bfloor')
def state_at(x, y):
    i, j = x - T['x0'], y - T['y0']
    if 0 <= i < T['w'] and 0 <= j < T['h']:
        v = T['tiles'][j*T['w'] + i]
        return kinds[v - 1].get('state') if v else None
grass = lambda x, y: floor(x, y) and state_at(x, y) == 'grass'   # open ground, not a wall-walk or a hall floor
others = [t for t in scene0['things'] if t['kind'] not in ('mine', 'npc', 'animal')]
taken = {(t['x'], t['y']) for t in others}
# a 3x2 block of open floor for the group, and open floor 7-9 tiles away for the click
def block_ok(x, y, w=3, h=2, pad=1):
    return all(grass(x + i, y + j) and (x + i, y + j) not in taken for i in range(-pad, w + pad) for j in range(-pad, h + pad))
cx, cy = scene0['cx'], scene0['cy']
def find_spot(html):
    # where to stand and where to click: open grass at ground height (the scene's wall-walks are 'grass' up on the
    # walls), asked of the page itself after it has built the scene
    with tempfile.TemporaryDirectory(prefix='fm-spot-') as tmp, sync_playwright() as pw:
        page_file = Path(tmp)/'remastered.html'
        page_file.write_text(html.read_text(encoding='utf-8').replace('window.location.href=', 'window.testLastURL='), encoding='utf-8')
        browser = pw.chromium.launch(executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless=True, args=['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'])
        page = browser.new_page(viewport=dict(width=1280, height=720))
        page.goto(page_file.as_uri() + '?overlay', wait_until='domcontentloaded')
        page.evaluate("()=>{window.send=function(){}}")
        sc = json.loads(json.dumps(scene0)); sc['things'] = others
        m0 = json.loads((BASE/'tests/idle-model-available.json').read_text()); m0.update(units=[], view3d=1, targets=[], hover=None, maxx=200, maxy=200)
        page.evaluate('m=>updateHUD(m)', m0)
        page.evaluate('()=>v3set(true)')
        page.evaluate('s=>update3D(s)', sc)
        page.wait_for_timeout(800)
        r = page.evaluate('''([cx,cy,taken])=>{const T=new Set(taken.map(t=>t[0]+','+t[1]));const ok=(x,y)=>{const K=v3kindAt(x,y);return K&&K.kind==='floor'&&!T.has(x+','+y)&&Math.abs(v3groundAt(x,y))<0.25};
          const blk=(x,y,w,h,p)=>{for(let i=-p;i<w+p;i++)for(let j=-p;j<h+p;j++)if(!ok(x+i,y+j))return false;return true};let best=null;
          for(let dy=-14;dy<=14;dy++)for(let dx=-14;dx<=14;dx++){const x=cx+dx,y=cy+dy;if(!blk(x,y,3,2,1))continue;
           for(const [gx,gy] of [[x+8,y+5],[x-8,y+5],[x+8,y-5],[x-8,y-5],[x+1,y+8],[x+1,y-8]]){if(!blk(gx-2,gy-1,5,4,0))continue;let clear=true;for(let k=0;k<=24&&clear;k++){const px=Math.round(x+1+(gx-x-1)*k/24),py=Math.round(y+(gy-y)*k/24);for(const [ox,oy] of [[0,0],[-1,0],[1,0],[0,1]])if(!ok(px+ox,py+oy))clear=false}if(!clear)continue;const d=Math.abs(dx)+Math.abs(dy);if(!best||d<best[0])best=[d,x,y,gx,gy]}}return best}''', [cx, cy, [[t['x'], t['y']] for t in others]])
        browser.close()
        return r
best = find_spot(a.html)
assert best, 'no open block at ground height in the scene'
_, ux, uy, gx, gy = best
names = ['Mason', 'Weaver', 'Smith', 'Tanner', 'Cook', 'Scout']
models = ['dwarf', 'dwarf', 'human', 'orc', 'goblin', 'human']
mine = [{'kind': 'mine', 'x': ux + k % 3, 'y': uy + k // 3, 'name': names[k], 'dir': 2, 'act': 'idle', 'model': models[k], 'ref': f'ui-fm-{k}', 'tex': '', 'selected': 1, 'hp': 100} for k in range(6)]
npc = {'kind': 'npc', 'x': ux + 4, 'y': uy - 2, 'name': 'Orc raider', 'dir': 8, 'act': 'idle', 'id': '[0x3000001]', 'tex': '', 'hp': 100}
model = json.loads((BASE/'tests/idle-model-available.json').read_text())
tpl = model['units'][0]
model['units'] = [dict(tpl, ref=m['ref'], name=m['name'], x=m['x'], y=m['y'], z=scene0['z'], race='Dwarf', selected=True) for m in mine]
model['controlGroups'] = {'selection': 'ui-fm', 'selectedCount': 6, 'setReason': '', 'addReason': '', 'groups': [{'number': n, 'count': 0, 'names': [], 'reason': ''} for n in range(1, 10)]}
model.update(view3d=1, targets=[], hover=None, maxx=200, maxy=200, formation='keep', selection=6)

def run(html, label, shots, results, errors, full=True):
    scene = json.loads(json.dumps(scene0))
    scene['things'] = [dict(m) for m in mine] + [npc] + others
    def check(name, ok, detail=None):
        results[name] = {'ok': None if ok is None else bool(ok), 'detail': detail}
        print(f'[{label}] ' + ('SKIP ' if ok is None else 'PASS ' if ok else 'FAIL ') + name + ('' if detail is None else '  ' + json.dumps(detail)[:300]), flush=True)
    with tempfile.TemporaryDirectory(prefix='fm-headless-') as tmp, sync_playwright() as pw:
        page_file = Path(tmp)/'remastered.html'
        page_file.write_text(html.read_text(encoding='utf-8').replace('window.location.href=', 'window.testLastURL='), encoding='utf-8')
        browser = pw.chromium.launch(executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless=True,
                                     args=['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'])
        page = browser.new_page(viewport=dict(width=1280, height=720))
        page.on('pageerror', lambda e: errors.append(f'[{label}] {e}'))
        page.on('console', lambda c: errors.append(f'[{label}] ' + c.text[:300]) if c.type == 'error' and 'Failed to load resource' not in c.text else None)
        page.goto(page_file.as_uri() + '?overlay', wait_until='domcontentloaded')
        page.evaluate("""()=>{window.__sent=[];window.send=function(a,v){window.__sent.push([a,String(v==null?'':v),performance.now()])}}""")
        page.evaluate('m=>updateHUD(m)', model)
        page.evaluate('()=>v3set(true)')
        page.evaluate('s=>update3D(s)', scene)
        mx, my = (ux + 1 + gx) / 2, (uy + gy) / 2
        page.evaluate("""([x,y])=>{if(typeof v3iso==='function')v3iso(false);V3.dist=16;V3.pitch=0.95;V3.yaw=0;V3.turnTo=null;V3.cx=V3.tcx=x;V3.cy=V3.tcy=y;V3.panAt=performance.now()}""", [mx, my])
        page.wait_for_timeout(1500)
        page.evaluate('()=>new Promise(r=>{let n=0;const f=()=>{if(++n>=4)r();else requestAnimationFrame(f)};requestAnimationFrame(f)})')
        page.evaluate('''([ux,uy,gx,gy])=>{const a=v3project([ux,0,-uy]),b=v3project([gx,0,-gy]);if(a&&b&&a[1]<b[1]){V3.yaw=Math.PI}}''', [ux + 1, uy, gx, gy])
        page.wait_for_timeout(600)
        page.evaluate('()=>new Promise(r=>{let n=0;const f=()=>{if(++n>=4)r();else requestAnimationFrame(f)};requestAnimationFrame(f)})')
        zoom = page.evaluate('hudKC()')
        def scr(x, y, h=0.05):
            p = page.evaluate('([x,y,h])=>v3project([x,v3groundAt(x,y)+h,-y])', [x, y, h])
            return (p[0]*zoom, p[1]*zoom) if p else None
        def frames(n=3):
            page.evaluate('n=>new Promise(r=>{let k=0;const f=()=>{if(++k>=n)r();else requestAnimationFrame(f)};requestAnimationFrame(f)})', n)
        def shot(name):
            shots.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(shots/f'{label}-{name}.png'))
        has = page.evaluate("()=>typeof fmStats==='function'")
        check('formations block present', has if label == 'after' else not has)
        shot('0-start')
        pts = [scr(m['x'], m['y'], 0.6) for m in mine] + [scr(m['x'], m['y']) for m in mine] + [scr(gx + dx, gy + dy) for dx in (-2, 2) for dy in (-2, 2)]
        pts = [p for p in pts if p]
        if pts and 'crop' not in CROP:
            x0, x1 = min(p[0] for p in pts), max(p[0] for p in pts); y0, y1 = min(p[1] for p in pts), max(p[1] for p in pts)
            CROP['crop'] = (max(0, int(x0 - 120)), max(0, int(y0 - 90)), min(1280, int(x1 + 120)), min(720, int(y1 + 70)))
        g = scr(gx, gy)
        check('target on screen', g is not None and 0 < g[0] < 1280 and 0 < g[1] < 720, g)
        # 1. a click on open ground with six selected
        page.mouse.move(*g)
        page.wait_for_timeout(250)
        t0 = page.evaluate('()=>performance.now()')
        page.mouse.click(*g)
        frames(2)
        shot('1-click')
        S = [s for s in page.evaluate('()=>window.__sent') if s[2] >= t0]
        check('the click sends click3d', any(s[0] == 'click3d' and s[1].startswith(f'{gx}|{gy}|') for s in S), [s[:2] for s in S])
        if not any(s[0] == 'click3d' for s in S):   # say why before the checks that need it fail
            print('no click3d; at the click:', page.evaluate(f"()=>{{const t=v3pickTile({g[0]}/hudKC(),{g[1]}/hudKC());const K=t&&v3kindAt(t.x,t.y);return {{tile:t,kind:K&&K.kind,sel:fmSel().length,last:typeof RF!=='undefined'&&RF.last,mode:model&&model.mode,gather:model&&model.gather}}}}"), flush=True)
        if not has:
            # what the game shows a moment later: the HUD model's target squares and lines
            page.wait_for_timeout(400)
            page.evaluate('m=>updateHUD(m)', dict(model, targets=[{'x': gx - 1 + k % 3, 'y': gy + k // 3, 'z': scene0['z'], 'kind': 'Move', 'unit': m['ref'], 'index': 0} for k, m in enumerate(mine)]))
            frames(3)
            shot('2-model')
            browser.close()
            return
        st = page.evaluate('fmStats()')
        P = st['sets'][-1] if st['sets'] else None
        tiles = [tuple(e[1:3]) for e in P['s']] if P else []
        check('a marker for every unit on the first frame after the click (predicted)', P and P['pred'] and P['n'] == 6, P)
        check('the slots are distinct open tiles', len(set(tiles)) == 6 and all(floor(x, y) for x, y in tiles), tiles)
        dx, dy = gx - (ux + 1), gy - (uy + 1)
        exp = {(m['x'] + dx, m['y'] + dy) for m in mine}
        check("'keep': the group's own 3x2 shape, moved over", set(tiles) == exp, {'got': sorted(tiles), 'expected': sorted(exp)})
        drawn = page.evaluate("()=>{const a=[];fmDraw(a);return a.length}")
        check('markers drawn', drawn > 0, drawn)
        check('prediction cost under 5 ms', st['costPredictMs'] is not None and st['costPredictMs'] < 5, st['costPredictMs'])
        if page.evaluate("()=>typeof fmRealPoints==='function'"):   # the war band's formations (Formations.dm RemasterRealPoints)
            for shp in ('line', 'column', 'wedge', 'square', 'skirmish'):
                R = page.evaluate("([x,y,s])=>{const P=fmPredict(x,y,fmSel(),s);return P&&P.s.map(e=>[e.x,e.y])}", [gx, gy, shp])
                ok = bool(R) and len(R) == 6 and len({tuple(t) for t in R}) == 6 and all(floor(x, y) for x, y in R) and [gx, gy] in R
                check(f"'{shp}': predicted, a slot each, distinct open tiles, one on the clicked tile", ok, R)
        # 2. the game's slots: one differs by a tile, so its marker glides there
        real = [[e[0], e[1], e[2], scene0['z']] for e in P['s']]
        real[0][1] += 0
        moved_ref = real[5][0]
        real[5][2] += 1
        page.evaluate('d=>rmSlots3D(JSON.stringify(d))', {'id': 7, 'kind': 'move', 'q': 0, 'f': [P['fx'], P['fy']], 's': real})
        page.wait_for_timeout(60)
        # and the HUD model's targets (the order queue's squares and lines) a moment later, as the game sends them
        page.evaluate('m=>updateHUD(m)', dict(model, targets=[{'x': e[1], 'y': e[2], 'z': scene0['z'], 'kind': 'Move', 'unit': e[0], 'index': 0} for e in real]))
        frames(2)
        st = page.evaluate('fmStats()')
        S1 = st['sets'][-1]
        sq = page.evaluate("L=>L.map(e=>typeof rfQueueDig==='function'?rfQueueDig([],{x:e[1],y:e[2],kind:'Move'},[1,1,1,1],0,0):null)", real)
        check("the order queue's square on a slot gives way to its marker (the line still runs there)", all(q and abs(q[0] - e[1]) < 1e-6 and abs(q[1] + e[2]) < 1e-6 for q, e in zip(sq, real)), sq)
        check("the game's slots replace the prediction (same set, confirmed)", len(st['sets']) == 1 and not S1['pred'] and S1['id'] == 7 and any(e[0] == moved_ref and e[2] == real[5][2] for e in S1['s']), S1)
        page.wait_for_timeout(250)
        frames(3)
        shot('2-confirmed')
        # 3. half of them get there: their markers fade; the rest stay
        for e in real[:3]:
            page.evaluate('m=>move3D(JSON.stringify(m))', [[e[0], e[1], e[2], 2]])
        frames(2)
        page.wait_for_timeout(200)
        frames(2)
        shot('3-arriving')
        page.wait_for_timeout(450)
        frames(3)
        st = page.evaluate('fmStats()')
        left = st['sets'][-1]['s'] if st['sets'] else []
        check('a marker fades once its unit stands on it (the other three stay)', len(left) == 3 and all(not x[3] for x in left), left)
        if full:
            # 4. Shift-queued second leg: the first leg's markers stay, a second set is added
            busy = {(m['x'], m['y']) for m in mine} | {(e[1], e[2]) for e in real} | taken
            def spot(skip):
                for r in range(2, 7):
                    for ddx in range(-r, r + 1):
                        for ddy in (-r, r):
                            x, y = gx + ddx, gy + ddy
                            if (x, y) in busy or (x, y) in skip or not floor(x, y): continue
                            p = scr(x, y)
                            if p and 60 < p[0] < 1220 and 60 < p[1] < 600: return (x, y), p
                return None, None
            t2, g2 = spot(set()); t3, g3 = spot({t2}); t4, g4 = spot({t2, t3})
            check('follow-up click points on screen', all(p and 0 < p[0] < 1280 and 0 < p[1] < 720 for p in (g2, g3, g4)), [g2, g3, g4])
            page.wait_for_timeout(450)
            if g2:
                page.keyboard.down('Shift'); page.mouse.click(*g2); page.keyboard.up('Shift')
                frames(1)
                st = page.evaluate('fmStats()')
                check('Shift-click keeps the first leg and adds the second', len(st['sets']) == 2, [(s['n'], s['pred']) for s in st['sets']])
                shot('4-queued')
            # 5. a plain new click: old markers go, one new set
            page.wait_for_timeout(450)
            page.mouse.click(*g3)
            frames(1)
            st = page.evaluate('fmStats()')
            check('a new order replaces the old markers', len(st['sets']) == 1 and st['sets'][0]['n'] == 6, [(s['n'], s['pred']) for s in st['sets']])
            # 6. attack-move: red markers
            page.evaluate("()=>{model.attackMode=1}")
            page.wait_for_timeout(450)
            # open ground with nobody drawn over it: the units walked in step 5, and a click on one of ours is a select
            seen = {t2, t3}
            while g4 and page.evaluate(f"()=>{{const t=v3pickThing({g4[0]}/hudKC(),{g4[1]}/hudKC());return !!(t&&t.kind==='mine')}}"):
                seen.add(t4); t4, g4 = spot(seen)
            page.mouse.click(*g4)
            frames(1)
            st = page.evaluate('fmStats()')
            check('attack-move markers (red)', st['sets'] and st['sets'][-1]['kind'] == 'attack' and st['sets'][-1]['n'] == 6, [(s['kind'], s['n']) for s in st['sets']])
            shot('5-attack-move')
            page.evaluate("()=>{model.attackMode=0}")
            # 7. a click on a foe: no slot markers
            page.evaluate("()=>{FM.sets=[]}")
            po = scr(npc['x'], npc['y'], 0.55)
            page.mouse.click(*po)
            frames(1)
            st = page.evaluate('fmStats()')
            check('a click on a foe makes no slot markers', not st['sets'], st['sets'])
            # 8. one unit selected: no slot markers
            page.evaluate("()=>{for(const t of V3.things)if(t.kind==='mine')t.selected=t.ref==='ui-fm-0'?1:0;FM.sets=[]}")
            page.mouse.click(*scr(gx + (1 if gx > ux else -1), gy + (2 if gy > uy else -2)))
            frames(1)
            st = page.evaluate('fmStats()')
            check('one unit: no slot markers', not st['sets'], st['sets'])
            # 9. cost of drawing 50 markers
            ms = page.evaluate("""()=>{FM.sets=[{id:1,pred:false,kind:'move',at:performance.now(),fx:1,fy:0,s:[]}];const now=performance.now();for(let i=0;i<50;i++)FM.sets[0].s.push({ref:'x'+i,x:%d+i%%10,y:%d+Math.floor(i/10),px:0,py:0,t0:now-1000,born:now-1000,arr:0});
              const t0=performance.now();for(let k=0;k<20;k++){const a=[];fmDraw(a)}return (performance.now()-t0)/20}""" % (gx - 5, gy - 2))
            check('drawing 50 markers costs under 1 ms a frame', ms < 1, round(ms, 3))
            # 9b. Attack (A), then a box over the raider: it is taken (attackbox), the box is red while dragging, the raider
            # ringed, the pointer a red box; a box over nothing sends nothing; a small slip is still a click
            page.evaluate("()=>{FM.sets=[];for(const t of V3.things)if(t.kind==='mine')t.selected=1;model.attackMode=1}")
            po = scr(npc['x'], npc['y'], 0.3)
            a0 = (po[0] - 70, po[1] - 70); a1 = (po[0] + 70, po[1] + 50)
            t0 = page.evaluate('()=>performance.now()')
            page.mouse.move(*a0); page.mouse.down()
            page.mouse.move((a0[0] + a1[0]) / 2, (a0[1] + a1[1]) / 2, steps=4); page.mouse.move(*a1, steps=4)
            frames(2)
            mid = page.evaluate("()=>{const b=document.getElementById('box3d'),c=getComputedStyle(b);return {shown:!b.hidden,red:document.body.classList.contains('fm-atk'),border:c.borderTopColor,cursor:String($('world3d').style.cursor).slice(0,24),box:!!FM.atkBox,rings:(()=>{const a=[];fmAtkDraw(a);return a.length})()}}")
            shot('8-attack-box-drag')
            page.mouse.up()
            page.wait_for_timeout(150)
            S = [x[:2] for x in page.evaluate('()=>window.__sent') if x[2] >= t0]
            check('Attack mode, a drag over a foe: the box is red, the foe ringed, the pointer a red box', mid['shown'] and mid['red'] and 'url(' in mid['cursor'] and mid['rings'] > 0 and mid['border'].startswith('rgb(255, 90, 69'), mid)
            check('let go: the foe in the box is sent (attackbox) and nothing is box-selected', any(x[0] == 'attackbox' and npc['id'] in x[1] for x in S) and not any(x[0] in ('boxrefs', 'box3d') for x in S), S)
            # a box over empty ground
            page.evaluate("()=>{model.attackMode=1}")
            e0 = scr(gx + 2, gy + 2); e1 = scr(gx + 4, gy + 3)
            t0 = page.evaluate('()=>performance.now()')
            page.mouse.move(*e0); page.mouse.down(); page.mouse.move(*e1, steps=5); page.mouse.up()
            page.wait_for_timeout(150)
            S = [x[:2] for x in page.evaluate('()=>window.__sent') if x[2] >= t0]
            check('a box over no foe sends nothing (and says so)', not any(x[0] in ('attackbox', 'boxrefs', 'box3d') for x in S) and page.evaluate("()=>(FM.lastBox||{}).n")==0, S)
            # a slip of a few pixels on the raider is a click on it
            page.evaluate("()=>{model.attackMode=1}")
            t0 = page.evaluate('()=>performance.now()')
            pr = scr(npc['x'], npc['y'], 0.55)
            page.mouse.move(*pr); page.mouse.down(); page.mouse.move(pr[0] + 8, pr[1] + 3, steps=3); page.mouse.up()
            page.wait_for_timeout(150)
            S = [x[:2] for x in page.evaluate('()=>window.__sent') if x[2] >= t0]
            check('a small slip is still a click (on the foe: click3d with its id)', any(x[0] == 'click3d' for x in S) and not any(x[0] == 'attackbox' for x in S), S)
            page.evaluate("()=>{model.attackMode=0}")
            # 9c. drag to face: Ctrl + a left-drag from open ground, two tiles: they face that way, five abreast
            page.evaluate("()=>{FM.sets=[];FM.face=null;for(const t of V3.things)if(t.kind==='mine')t.selected=1;model.attackMode=0}")
            busy |= {(m['x'] + 0, m['y']) for m in mine}
            fx0, fy0 = None, None
            for ddx in range(-6, 7):
                for ddy in range(-6, 4):
                    x, y = gx + ddx, gy + ddy
                    if fx0 is None and all((x, y + k) not in busy and floor(x, y + k) for k in range(0, 3)) and (x, y) not in busy and scr(x, y) and scr(x, y + 2):
                        p0, p1 = scr(x, y), scr(x, y + 2)
                        if 60 < p0[0] < 1220 and 60 < p0[1] < 600 and 60 < p1[0] < 1220 and 60 < p1[1] < 600:
                            fx0, fy0 = x, y
            f0 = scr(fx0, fy0); f1 = scr(fx0, fy0 + 2)
            t0 = page.evaluate('()=>performance.now()')
            page.keyboard.down('Control'); page.mouse.move(*f0); page.mouse.down()
            page.mouse.move((f0[0] + f1[0]) / 2, (f0[1] + f1[1]) / 2, steps=4); page.mouse.move(*f1, steps=4)
            frames(2)
            st = page.evaluate('fmStats()')
            shot('9-face-drag')
            page.evaluate("()=>{window.__gf=0;window.gameFocus=function(){window.__gf++}}")   # the keyboard back to the game after the drag
            page.mouse.up(); page.keyboard.up('Control')
            page.wait_for_timeout(150)
            check('after a drag to face the keyboard goes back to the game (so Ctrl+2 and the other keys reach it)', page.evaluate('()=>window.__gf') >= 1, page.evaluate('()=>window.__gf'))
            S = [x[:2] for x in page.evaluate('()=>window.__sent') if x[2] >= t0]
            check('drag to face: while dragging, the squares where each will stand follow the pointer (six, five abreast)', st['face'] and st['face']['on'] and st['face']['width'] == 5 and st['face']['n'] == 6, st['face'])
            check('let go: formmove with the tile, the facing and the width, and no box select', any(x[0] == 'formmove' and x[1] == f'{fx0}|{fy0}|0|2|5|0' for x in S) and not any(x[0] in ('boxrefs', 'box3d', 'click3d') for x in S), S)
            st = page.evaluate('fmStats()')
            check('and its squares stay on the slots (predicted at once)', st['sets'] and st['sets'][-1]['n'] == 6 and st['sets'][-1]['pred'], [(x['n'], x['pred']) for x in st['sets']])
            # 9d. the user's way: click to move, then press on that spot again and drag: the order just given turns
            page.wait_for_timeout(300)
            t0 = page.evaluate('()=>performance.now()')
            page.mouse.click(*f0)
            page.wait_for_timeout(250)
            page.mouse.move(*f0); page.mouse.down()
            page.mouse.move((f0[0] + f1[0]) / 2, (f0[1] + f1[1]) / 2, steps=4); page.mouse.move(*f1, steps=4)
            frames(2)
            st = page.evaluate('fmStats()')
            page.mouse.up()
            page.wait_for_timeout(150)
            S = [x[:2] for x in page.evaluate('()=>window.__sent') if x[2] >= t0]
            check('click to move, then drag from that spot: the drag turns the order just given (formmove on the clicked tile)', [x[0] for x in S if x[0] in ('click3d', 'formmove', 'boxrefs', 'box3d')] == ['click3d', 'formmove'] and any(x[0] == 'formmove' and x[1] == f'{fx0}|{fy0}|0|2|5|0' for x in S), {'sent': S, 'face': st['face']})
            # the band card says when the selection is a control group with its own formation
            page.evaluate('m=>updateHUD(m)', dict(model, formationGroup=2, formation='line'))
            page.wait_for_timeout(200)
            note = page.evaluate("()=>{const e=document.querySelector('#heroframe [data-pane=orders] .hfnote');return e&&e.textContent}")
            check("band card: 'Control group 2 keeps its own formation' when the selection is group 2", note and 'Control group 2' in note, note)
            page.evaluate('m=>updateHUD(m)', dict(model, formationGroup=0))
            # 10. Army › Formations: your own formations (hud-craft's host calls fmArmyEditor while the tab is open)
            roles = ['front', 'ranged', 'front', 'ranged', 'front', 'mage']      # what each of the six holds
            mu = [dict(u, frole=roles[k]) for k, u in enumerate(model['units'])]
            page.evaluate("()=>{FM.sets=[];for(const t of V3.things)if(t.kind==='mine')t.selected=1}")
            page.click('nav [data-value=army]')    # the menu's Army button opens the side panel, then the game says tab army
            page.evaluate('m=>updateHUD(m)', dict(model, units=mu, tab='army', formations=[], formationMine=1, formationGrid=[]))
            page.wait_for_timeout(400)
            ed = page.evaluate("()=>{const e=document.getElementById('armyFormEditor');return e&&{hidden:e.hidden,text:e.textContent.slice(0,400),nw:!!e.querySelector('[data-fma=new]')}}")
            check('Army › Formations: "Your own formations", empty, with + New', ed and not ed['hidden'] and 'No formations yet' in ed['text'] and ed['nw'], ed)
            shot('6-editor-empty')
            sent0 = lambda t: [x[:2] for x in page.evaluate('()=>window.__sent') if x[2] >= t]
            t0 = page.evaluate('()=>performance.now()')
            page.click('#armyFormEditor [data-fma=new]')
            ed = page.evaluate("()=>{const e=document.getElementById('armyFormEditor');return {cells:e.querySelectorAll('[data-fmc]').length,anchor:!!e.querySelector('.anchor'),brushes:[...e.querySelectorAll('[data-fma=brush]')].map(b=>b.dataset.r+':'+b.getAttribute('aria-pressed')),name:(e.querySelector('[data-fma=name]')||{}).value}}")
            check('+ New: a grid of squares (the clicked tile marked), the Front brush first, named Formation 1', ed['cells'] == 121 and ed['anchor'] and ed['brushes'][0] == 'front:true' and ed['name'] == 'Formation 1', ed)
            # three fighters in front, two archers behind left and right, the mage behind in the middle
            layout = [(-1, 1, 'front'), (0, 1, 'front'), (1, 1, 'front'), (-1, -1, 'ranged'), (1, -1, 'ranged'), (0, -1, 'mage')]
            for x, y, r in layout:
                page.click(f'#armyFormEditor [data-fma=brush][data-r={r}]')
                page.click(f'#armyFormEditor [data-fmc="{x},{y}"]')
            page.fill('#armyFormEditor [data-fma=name]', 'Archers back')
            page.dispatch_event('#armyFormEditor [data-fma=name]', 'change')
            page.wait_for_timeout(500)
            S = [x for x in sent0(t0) if x[0] == 'formationsave']
            want = '1|Archers back|' + '/'.join(f'{x},{y},{r}' for x, y, r in layout)
            check('painting squares with each brush and naming it saves the formation (formationsave, roles and name)', S and S[-1][1] == want, S[-3:])
            painted = page.evaluate("()=>[...document.querySelectorAll('#armyFormEditor .on')].map(e=>[e.dataset.fmc,getComputedStyle(e).backgroundColor,!!e.querySelector('b.hcg')])")
            check('painted squares take their role colour and mark (Front, Ranged, Mage)', len(painted) == 6 and len({p[1] for p in painted}) == 3 and all(p[2] for p in painted), painted)
            shot('7-editor-roles')
            t0 = page.evaluate('()=>performance.now()')
            page.click('#armyFormEditor [data-fma=use]')
            page.wait_for_timeout(200)
            check('"Use this formation" sends formationuse 1', ['formationuse', '1'] in sent0(t0), sent0(t0))
            # the game takes it: a group move then puts each on a square of its own role, turned to face the way they go
            F1 = {'name': 'Archers back', 'cells': [list(c) for c in layout]}
            page.evaluate('m=>updateHUD(m)', dict(model, units=mu, tab='units', formation='custom', formations=[F1], formationMine=1, formationGrid=F1['cells']))
            page.wait_for_timeout(300)
            P2 = page.evaluate("([tx,ty])=>{const U=V3.things.filter(t=>t.kind==='mine').map(t=>({ref:t.ref,x:t.x,y:t.y}));return fmPredict(tx,ty,U,'custom')}", [gx, gy])
            cxu = sum(m['x'] for m in mine) / 6; cyu = sum(m['y'] for m in mine) / 6
            fx, fy = gx - cxu, gy - cyu; ax, ay = abs(fx), abs(fy)
            F = (1 if fx >= 0 else -1, 0) if ax >= ay else (0, 1 if fy >= 0 else -1)
            R2 = (F[1], -F[0])
            # (0,0) is empty: the square nearest it, front 0,1, goes on the clicked tile
            where = {(gx + x * R2[0] + (y - 1) * F[0], gy + x * R2[1] + (y - 1) * F[1]): r for x, y, r in layout}
            role_of = {m['ref']: roles[k] for k, m in enumerate(mine)}
            got = {(e['x'], e['y']): role_of[e['ref']] for e in P2['s']} if P2 else {}
            check("then each goes to a square of its own role, turned to face the way they go, one on the clicked tile", got == where and (gx, gy) in got, {'got': sorted(got.items()), 'expected': sorted(where.items()), 'facing': F})
            # 11. Groups in the Company list (the user, 2026-10-23): a card per group (click, open, right-click), Group from a
            # row's right-click, Ctrl+G, Ctrl-click on a grouped unit in the world (its group; another group's: added)
            page.evaluate("()=>{const c=$('panelClose');if(c&&c.offsetParent)c.click()}")
            R = [m['ref'] for m in mine]
            cg = {'selection': 'ui-fm', 'selectedCount': 1, 'setReason': '', 'addReason': '', 'groups': [
                {'number': 1, 'count': 3, 'names': names[:3], 'reason': '', 'refs': R[:3], 'formation': 'line'},
                {'number': 2, 'count': 2, 'names': names[3:5], 'reason': '', 'refs': R[3:5], 'formation': ''}] +
                [{'number': n, 'count': 0, 'names': [], 'reason': '', 'refs': [], 'formation': ''} for n in range(3, 10)]}
            def hud(sel):
                mu6 = [dict(u, selected=(u['ref'] in sel)) for u in model['units']]
                page.evaluate("s=>{for(const t of V3.things)if(t.kind==='mine')t.selected=s.includes(t.ref)?1:0;FM.sets=[];if(typeof RF!=='undefined')RF.opt=null}", sel)
                page.evaluate('m=>updateHUD(m)', dict(model, units=mu6, controlGroups=cg, selection=len(sel), formation='keep', formationGroup=0))
                page.wait_for_timeout(200)
            hud([R[5]])
            info = page.evaluate("""()=>({cards:[...document.querySelectorAll('#fmGroups .fmg')].map(c=>({n:c.dataset.fmg,text:c.textContent.replace(/\\s+/g,' ').trim(),faces:c.querySelectorAll('.fmg-f img').length,vis:c.getBoundingClientRect().height>0})),
              rows:[...document.querySelectorAll('#rosterList .member')].map(b=>[b.dataset.value,getComputedStyle(b).display!=='none'])})""")
            check('Company list: a card per group (number, how many, formation, faces), above the rows', [c['n'] for c in info['cards']] == ['1', '2'] and 'Group 1' in info['cards'][0]['text'] and 'line' in info['cards'][0]['text'] and info['cards'][0]['faces'] == 3 and all(c['vis'] for c in info['cards']), info['cards'])
            check("grouped units' own rows fold into their card (only the sixth, ungrouped, shows)", [r for r, v in info['rows'] if v] == [R[5]], info['rows'])
            shot('11-group-cards')
            def sent_since(t0):
                return [x[:2] for x in page.evaluate('()=>window.__sent') if x[2] >= t0]
            t0 = page.evaluate('()=>performance.now()')
            page.click('#fmGroups [data-fmgs="1"]')
            page.wait_for_timeout(120)
            S = sent_since(t0)
            rows1 = page.evaluate("""()=>[...document.querySelectorAll('#fmGroups [data-fmg="1"] .fmg-m .member')].map(b=>b.dataset.value)""")
            check('a click on a card selects that group (fmgroup select) and opens it: its three rows', ['fmgroup', 'select|1|0'] in S and rows1 == R[:3], {'sent': S, 'rows': rows1})
            def rows_of(n):
                return page.evaluate("n=>{const c=[...document.querySelectorAll('#fmGroups .fmg')].find(x=>x.dataset.fmg===String(n));return c?c.querySelectorAll('.fmg-m .member').length:0}", n)
            page.click('#fmGroups [data-fmgt="1"]'); page.wait_for_timeout(120); shut = rows_of(1)
            page.click('#fmGroups [data-fmgt="1"]'); page.wait_for_timeout(120); again = rows_of(1)
            check('its arrow closes it, and opens it again', shut == 0 and again == 3, [shut, again])
            shot('11-group-open')
            t0 = page.evaluate('()=>performance.now()')
            page.click('#rosterList .member[data-value="' + R[5] + '"]', button='right')
            page.wait_for_timeout(150)
            menu = page.evaluate("()=>{const m=document.getElementById('fmGroupMenu');return m&&!m.hidden?[...m.querySelectorAll('button')].map(b=>b.textContent):null}")
            check('right-click on a row in the Company list: a menu with Group the selected', bool(menu) and menu[0].startswith('Group the selected'), menu)
            shot('11-row-menu')
            if menu:
                page.click('#fmGroupMenu button[data-fmm="0"]')
                page.wait_for_timeout(120)
            S = sent_since(t0)
            check('Group sends fmgroup make with that row', ['fmgroup', 'make|' + R[5]] in S, S)
            t0 = page.evaluate('()=>performance.now()')
            page.click('#fmGroups [data-fmgs="2"]', button='right')
            page.wait_for_timeout(150)
            menu = page.evaluate("()=>{const m=document.getElementById('fmGroupMenu');return m&&!m.hidden?[...m.querySelectorAll('button')].map(b=>b.textContent):null}")
            check('right-click on a card: Select, Add to the selection, Ungroup', menu == ['Select group 2', 'Add group 2 to the selection', 'Ungroup'], menu)
            if menu:
                page.click('#fmGroupMenu button[data-fmm="2"]')
                page.wait_for_timeout(120)
            S = sent_since(t0)
            check('Ungroup sends fmgroup ungroup', ['fmgroup', 'ungroup|2'] in S, S)
            t0 = page.evaluate('()=>performance.now()')
            page.mouse.move(640, 40)
            page.keyboard.press('Control+g')
            page.wait_for_timeout(120)
            S = sent_since(t0)
            check('Ctrl+G groups the selected (fmgroup make)', ['fmgroup', 'make|'] in S, S)
            def body(ref):    # where that unit stands now (earlier steps walked them), half-way up its picture
                p = page.evaluate("r=>{const t=V3.things.find(u=>u.ref===r);if(!t)return null;const x=t.dx!=null?t.dx:t.x,y=t.dy!=null?t.dy:t.y;return v3project([x,v3groundAt(Math.round(x),Math.round(y))+0.6,-y])}", ref)
                return (p[0]*zoom, p[1]*zoom) if p else None
            p1, p4 = body(R[1]), body(R[4])
            t0 = page.evaluate('()=>performance.now()')
            page.keyboard.down('Control'); page.mouse.click(*p1); page.keyboard.up('Control')
            page.wait_for_timeout(150)
            S = sent_since(t0)
            ring = page.evaluate("()=>V3.things.filter(t=>t.kind==='mine'&&t.selected).map(t=>t.ref).sort()")
            check('Ctrl-click on a grouped unit in the world selects its group (the rings at once)', ['fmgroup', 'select|1|0'] in S and ring == sorted(R[:3]), {'sent': S, 'ringed': ring})
            hud(R[:3])
            t0 = page.evaluate('()=>performance.now()')
            page.keyboard.down('Control'); page.mouse.click(*p4, button='right'); page.keyboard.up('Control')   # a Mac's Ctrl-click: the right button with Ctrl
            page.wait_for_timeout(150)
            S = sent_since(t0)
            m3 = page.evaluate("()=>{const m=document.getElementById('menu3d');return !!(m&&!m.hidden)}")
            check("then Ctrl-click (a Mac's: the right button with Ctrl) on one of group 2 adds that group, no right-click card", ['fmgroup', 'select|2|1'] in S and not m3, {'sent': S, 'menu3d': m3})
            shot('11-ctrl-click-groups')
            # 12. the arrows in a unit's bag at a glance: a slot of their own after the quiver (how many, each kind in its tip)
            q = {'ref': 'ui-fm-q', 'name': 'Leather Quiver', 'state': '(Equipped)', 'icon': '', 'info': 'Arrows 4 · Weight 5', 'arrows': 4, 'arrowKinds': [['Metal Arrow', 3, ''], ['Silver Arrow', 1, '']]}
            one = [dict(u, selected=(k == 1), items=([q] if k == 1 else [])) for k, u in enumerate(model['units'])]
            page.evaluate('m=>updateHUD(m)', dict(model, units=one, controlGroups=cg, selection=1))
            page.wait_for_timeout(200)
            qb = page.evaluate("""()=>{const b=document.querySelector('.bagbar .bagslot[data-bag="ui-fm-q"]');const s=b&&b.nextElementSibling;return s&&s.classList.contains('fmarrowslot')?{n:s.querySelector('.bagcount').textContent,tip:s.title,red:s.querySelector('.bagcount').classList.contains('none')}:null}""")
            page.evaluate('m=>updateHUD(m)', dict(model, units=[dict(u, items=[dict(q, arrows=0, arrowKinds=[], info='Arrows 0 · Weight 5')] if u.get('selected') else []) for u in one], controlGroups=cg, selection=1))
            page.wait_for_timeout(200)
            q0 = page.evaluate("""()=>{const s=document.querySelector('.bagbar .fmarrowslot');return s?[s.querySelector('.bagcount').textContent,s.querySelector('.bagcount').classList.contains('none'),s.title.split('\\n')[0]]:null}""")
            check("the arrows in the unit's bag: a slot after the quiver, 4, each kind in its tip; at none, 0 in red", qb and qb['n'] == '4' and '4 arrows' in qb['tip'] and 'Metal Arrow ×3' in qb['tip'] and not qb['red'] and q0 and q0[0] == '0' and q0[1], {'four': qb, 'none': q0})
            shot('12-quiver')
            # 13. each group's supplies on the left: arrows, food, potions, bandages (red when archers have no arrows, no
            # food); a click selects the group and opens its combined bag (who has how many in each tip)
            cg2 = json.loads(json.dumps(cg))
            cg2['groups'][0].update(supply={'arrows': 12, 'throws': 2, 'medical': 3, 'food': 3, 'potions': 1, 'bandages': 2, 'remedies': 0, 'archers': 2}, bag=[['Metal Arrow', 12, '', 'Weaver 6 · Tanner 6'], ['Bread', 3, '', 'Mason 2 · Smith 1'], ['Leather Bandage', 2, '', 'Smith 2']])
            cg2['groups'][1].update(supply={'arrows': 0, 'throws': 0, 'medical': 0, 'food': 0, 'potions': 0, 'bandages': 0, 'remedies': 0, 'archers': 1}, bag=[])
            page.evaluate('m=>updateHUD(m)', dict(model, units=[dict(u, selected=(k == 5), items=[]) for k, u in enumerate(model['units'])], controlGroups=cg2, selection=1))
            page.wait_for_timeout(250)
            sp = page.evaluate("""()=>{const b=document.getElementById('fmSupplies');if(!b||b.hidden)return null;const r=b.getBoundingClientRect(),h=document.getElementById('heroframe').getBoundingClientRect();
              return {cards:[...b.querySelectorAll('.fms')].map(c=>({n:c.dataset.fmsg,pips:[...c.querySelectorAll('.fms-p')].map(p=>[p.textContent,p.classList.contains('low')])})),left:r.left,above:r.bottom<=h.top+1,w:r.width}}""")
            check('Supplies on the left: a small card per group: arrows, things to throw (when it has some), medical, food; red where archers have no arrows, nothing medical, no food', sp and [c['n'] for c in sp['cards']] == ['1', '2'] and [p[0][1:] for p in sp['cards'][0]['pips']] == ['12', '2', '3', '3'] and [p[1] for p in sp['cards'][1]['pips']] == [True, True, True] and not any(p[1] for p in sp['cards'][0]['pips']) and sp['left'] < 40 and sp['above'], sp)
            t0 = page.evaluate('()=>performance.now()')
            page.click('#fmSupplies [data-fmss="1"]')
            page.wait_for_timeout(200)
            S = sent_since(t0)
            bag = page.evaluate("()=>[...document.querySelectorAll('#fmSupplies .fms[data-fmsg=\"1\"] .fms-i')].map(e=>[e.textContent,e.title.split('\\n')[1]||''])")
            check("a click on a group's supplies selects it and opens its combined bag (who has how many in each tip)", ['fmgroup', 'select|1|0'] in S and len(bag) == 3 and bag[0][1] == 'Weaver 6 · Tanner 6', {'sent': S, 'bag': bag})
            shot('13-supplies')
            # 14. the selection's own card on top (two or more selected, not just one group): health together, who is
            # wounded, bleeding, hungry or tired, the supplies; a click shows its bag (it is selected already); a selection
            # that is one group shows on that group's card instead
            sel = {'supply': {'arrows': 6, 'throws': 0, 'medical': 1, 'food': 2, 'bandages': 1, 'remedies': 0, 'potions': 0, 'archers': 1,
                   'n': 4, 'hp': 410, 'maxhp': 600, 'hurt': 2, 'bleeding': 1, 'hungry': 1, 'tired': 0, 'fighting': 1},
                   'bag': [['Metal Arrow', 6, '', 'Weaver 6'], ['Bread', 2, '', 'Mason 1 · Scout 1']], 'group': 0}
            four = [dict(u, selected=(k in (0, 1, 3, 5)), items=[]) for k, u in enumerate(model['units'])]
            page.evaluate('m=>updateHUD(m)', dict(model, units=four, controlGroups=cg2, selection=4, selSupply=sel))
            page.wait_for_timeout(250)
            sc = page.evaluate("""()=>{const c=document.querySelector('#fmSupplies .fms');if(!c)return null;const h=c.querySelector('.fms-hp span');
              return {first:c.dataset.fmsg,title:c.querySelector('.fms-n b').textContent,hp:h&&h.style.width,st:[...c.querySelectorAll('.fms-st span')].map(x=>x.textContent),pips:[...c.querySelectorAll('.fms-p')].map(p=>p.textContent.slice(1)),cards:document.querySelectorAll('#fmSupplies .fms').length}}""")
            check('the selection gets its own card on top: health together (68%), wounded, bleeding, hungry, and its supplies', sc and sc['first'] == '0' and sc['title'] == 'Selected' and sc['hp'] == '68%' and sc['st'] == ['2 wounded', '1 bleeding', '1 hungry'] and sc['pips'] == ['6', '1', '2'] and sc['cards'] == 3, sc)
            t0 = page.evaluate('()=>performance.now()')
            page.click('#fmSupplies [data-fmss="0"]')
            page.wait_for_timeout(200)
            S = sent_since(t0)
            sb = page.evaluate("()=>document.querySelectorAll('#fmSupplies .fms[data-fmsg=\"0\"] .fms-i').length")
            check("a click on it shows their bag and selects nothing new", sb == 2 and not any(x[0] == 'fmgroup' for x in S), {'bag': sb, 'sent': S})
            shot('14-selection-card')
            g1 = [dict(u, selected=(k < 3), items=[]) for k, u in enumerate(model['units'])]
            page.evaluate('m=>updateHUD(m)', dict(model, units=g1, controlGroups=cg2, selection=3, selSupply=dict(sel, group=1)))
            page.wait_for_timeout(250)
            sg = page.evaluate("()=>({first:(document.querySelector('#fmSupplies .fms')||{dataset:{}}).dataset.fmsg,sel:[...document.querySelectorAll('#fmSupplies .fms.sel')].map(c=>c.dataset.fmsg)})")
            check("a selection that is just group 1 shows on group 1's card (highlighted), no card of its own", sg['first'] == '1' and sg['sel'] == ['1'], sg)
            hud([R[5]])
            t0 = page.evaluate('()=>performance.now()')
            page.mouse.dblclick(*body(R[1]))
            page.wait_for_timeout(200)
            S = sent_since(t0)
            check('a double-click on a grouped unit still selects all of its people on screen (not its group)', any(x[0] == 'boxrefs' for x in S) and not any(x[0] == 'fmgroup' for x in S), S)
        browser.close()

CROP = {}
results, errors = {'after': {}, 'before': {}}, []
run(a.html, 'after', a.shots, results['after'], errors)
if a.before:
    run(a.before, 'before', a.shots, results['before'], errors, full=False)
ok_after = all(v['ok'] is not False for v in results['after'].values())
results['errors'] = errors
results['passed'] = ok_after and not errors
a.out.parent.mkdir(parents=True, exist_ok=True)
a.out.write_text(json.dumps(results, indent=1))
if a.before:
    from PIL import Image, ImageDraw
    pairs = [('1-click', '1-click', 'At the click (first frame)'), ('2-model', '2-confirmed', 'A moment later (the game answered)')]
    tiles = []
    for b, f, cap in pairs:
        B = Image.open(a.shots/f'before-{b}.png').convert('RGB'); F = Image.open(a.shots/f'after-{f}.png').convert('RGB')
        w, h = B.size
        crop = CROP.get('crop', (w//2 - 330, h//2 - 220, w//2 + 330, h//2 + 200))
        B, F = B.crop(crop), F.crop(crop)
        row = Image.new('RGB', (B.width*2 + 12, B.height + 30), (24, 22, 20))
        row.paste(B, (0, 30)); row.paste(F, (B.width + 12, 30))
        d = ImageDraw.Draw(row)
        d.text((8, 8), 'Before: ' + cap, fill=(235, 225, 200)); d.text((B.width + 20, 8), 'After: ' + cap, fill=(235, 225, 200))
        tiles.append(row)
    img = Image.new('RGB', (tiles[0].width, sum(t.height for t in tiles) + 8*(len(tiles) - 1)), (24, 22, 20))
    y = 0
    for t in tiles:
        img.paste(t, (0, y)); y += t.height + 8
    img.save(OUT/'slot-markers-headless-before-after.jpg', quality=88)
    print('wrote', OUT/'slot-markers-headless-before-after.jpg')
for e in errors[:8]: print('ERROR', e)
print('PASSED' if results['passed'] else 'FAILED')
raise SystemExit(0 if results['passed'] else 1)
