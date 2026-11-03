#!/usr/bin/env python3
"""RTS-feel checks in headless Chrome (rts-feel, overnight polish 2026-10-22): the real HUD page (?overlay) with a
real 3D scene (a lairs replay scene from tests/lairs-dump-arena) and a HUD model whose units are that scene's units.
Trusted mouse/keyboard events from Playwright, no server: commands are recorded instead of sent.

Checks: a click on the ground with units selected draws a move ping on the next frame (click-to-pixels latency),
a click on a hostile flashes it and pings red, the pointer shows a sword over the hostile and a pick over rock,
a click on one of yours turns its ring at once, a box selects (optimistic rings), double-click selects the same
race on screen, digits send the control-group commands (Ctrl sets, Shift adds, a double tap jumps the camera),
the wheel zooms with easing, the window's edge scrolls, the minimap drags the camera, and no script errors.

  python3 tools/rts_feel/headless_feel.py [--html game/Interface/remastered.html] [--shots DIR]
Writes reports/polish-2026-10-22/rts-feel/headless-feel.json."""
import argparse
import json
import tempfile
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = Path(__file__).resolve().parents[2]
OUT = BASE/'reports/polish-2026-10-22/rts-feel'

ap = argparse.ArgumentParser()
ap.add_argument('--html', type=Path, default=BASE/'game/Interface/remastered.html')
ap.add_argument('--scene', type=Path, default=BASE/'tests/lairs-dump-arena/lairs-3d-12.json')
ap.add_argument('--shots', type=Path, default=None)
ap.add_argument('--out', type=Path, default=OUT/'headless-feel.json')
a = ap.parse_args()

scene = json.loads(a.scene.read_text())
cx, cy = scene['cx'], scene['cy']
T = scene['terrain']
kinds = T['kinds']
def kind_at(x, y):
    i, j = x - T['x0'], y - T['y0']
    if 0 <= i < T['w'] and 0 <= j < T['h']:
        v = T['tiles'][j*T['w'] + i]
        return kinds[v - 1]['kind'] if v else None
# a rock tile and open floor tiles near the middle
def nearest(pred):
    best = None
    for j in range(T['h']):
        for i in range(T['w']):
            x, y = T['x0'] + i, T['y0'] + j
            if pred(x, y):
                d = abs(x - cx) + abs(y - cy)
                if best is None or d < best[0]: best = (d, x, y)
    return best and best[1:]
floor = lambda x, y: kind_at(x, y) in ('floor', 'bfloor')
rock = nearest(lambda x, y: kind_at(x, y) == 'wall')
# our three units side by side, an orc to the east, a loose item to the south-west
things = [t for t in scene['things'] if t['kind'] not in ('mine', 'npc', 'animal')]
spots = []
for dx in range(-6, 7):
    for dy in range(-6, 7):
        x, y = cx + dx, cy + dy
        if floor(x, y) and all(floor(x + k, y) for k in range(-1, 2)): spots.append((abs(dx) + abs(dy), x, y))
spots.sort()
_, ux, uy = spots[0]
mine = []
for k, (x, y) in enumerate([(ux - 1, uy), (ux, uy), (ux + 1, uy)]):
    mine.append({'kind': 'mine', 'x': x, 'y': y, 'name': ['Mason', 'Weaver', 'Smith'][k], 'dir': 2, 'act': 'idle', 'model': 'dwarf', 'ref': f'ui-test-{k}', 'tex': '', 'selected': 0, 'hp': 100})
orc = next(((x, y) for d, x, y in spots if abs(x - ux) >= 3 and abs(y - uy) <= 1), (ux + 3, uy))
npc = {'kind': 'npc', 'x': orc[0], 'y': orc[1], 'name': 'Orc raider', 'dir': 8, 'act': 'idle', 'id': '[0x3000001]', 'tex': '', 'hp': 100}
ground = next(((x, y) for d, x, y in spots if abs(y - uy) >= 3), (ux, uy - 3))
scene['things'] = mine + [npc] + things
model = json.loads((BASE/'tests/idle-model-available.json').read_text())
tpl = model['units'][0]
races = ['Dwarf', 'Dwarf', 'Human']
model['units'] = [dict(tpl, ref=m['ref'], name=m['name'], x=m['x'], y=m['y'], z=scene['z'], race=races[k], selected=False) for k, m in enumerate(mine)]
model['controlGroups'] = {'selection': '', 'selectedCount': 0, 'setReason': 'Select units first.', 'addReason': '', 'groups': [{'number': n, 'count': 0, 'names': [], 'reason': ''} for n in range(1, 10)]}
model['view3d'] = 1
model['targets'] = []
model['hover'] = None
model['maxx'], model['maxy'] = 200, 200

results = {}
errors = []
import os
if os.environ.get('RF_DUMP'):   # the scene and model for tools/rts_feel/wk_feel.sh (the same check in a real WKWebView)
    Path(os.environ['RF_DUMP']).write_text('window.RFT_SCENE=' + json.dumps(scene) + ';window.RFT_MODEL=' + json.dumps(model) + ';window.RFT_U=' + json.dumps([ux, uy, ground, [npc['x'], npc['y']]]) + ';')
    raise SystemExit(0)
def check(name, ok, detail=None):
    results[name] = {'ok': None if ok is None else bool(ok), 'detail': detail}
    print(('SKIP ' if ok is None else 'PASS ' if ok else 'FAIL ') + name + ('' if detail is None else '  ' + json.dumps(detail)[:300]), flush=True)

with tempfile.TemporaryDirectory(prefix='rf-headless-') as tmp, sync_playwright() as pw:
    page_file = Path(tmp)/'remastered.html'
    page_file.write_text(a.html.read_text(encoding='utf-8').replace('window.location.href=', 'window.testLastURL='), encoding='utf-8')
    browser = pw.chromium.launch(executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless=True,
                                 args=['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'])
    page = browser.new_page(viewport=dict(width=1280, height=720))
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.on('console', lambda c: errors.append(c.text[:300]) if c.type == 'error' and 'Failed to load resource' not in c.text else None)
    page.goto(page_file.as_uri() + '?overlay', wait_until='domcontentloaded')
    page.evaluate("""()=>{window.__sent=[];window.send=function(a,v){window.__sent.push([a,String(v==null?'':v),performance.now()])}}""")
    page.evaluate('m=>updateHUD(m)', model)
    page.evaluate('()=>v3set(true)')
    page.evaluate('s=>update3D(s)', scene)
    page.evaluate("""()=>{if(typeof v3iso==='function')v3iso(false);V3.dist=14;V3.pitch=0.75;V3.yaw=0;V3.turnTo=null;V3.cx=V3.tcx=%d;V3.cy=V3.tcy=%d;V3.panAt=performance.now()}""" % (ux, uy))
    page.wait_for_timeout(1500)
    # a few drawn frames with this camera, so projections use it (frames are slow when the machine is loaded)
    page.evaluate('()=>new Promise(r=>{let n=0;const f=()=>{if(++n>=4)r();else requestAnimationFrame(f)};requestAnimationFrame(f)})')
    zoom = page.evaluate('hudKC()')
    def scr(x, y, h=0.05):
        p = page.evaluate('([x,y,h])=>{const p=v3project([x,v3groundAt(x,y)+h,-y]);return p}', [x, y, h])
        return (p[0]*zoom, p[1]*zoom) if p else None
    def free(pt):
        return page.evaluate('([x,y])=>document.elementFromPoint(x,y)===$("world3d")', list(pt))
    def shot(name):
        if a.shots:
            a.shots.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(a.shots/f'{name}.png'))
    def sent(since=0):
        return [s for s in page.evaluate('()=>window.__sent') if s[2] >= since]
    def now(): return page.evaluate('()=>performance.now()')
    def frame_ms():
        return page.evaluate('()=>new Promise(r=>{const t=[];const f=x=>{t.push(x);if(t.length<6)requestAnimationFrame(f);else r(Math.round((t[5]-t[0])/5))};requestAnimationFrame(f)})')
    print('camera after setup', page.evaluate('()=>({cx:V3.cx,cy:V3.cy,tcx:V3.tcx,tcy:V3.tcy,dist:V3.dist,yaw:V3.yaw,pitch:V3.pitch,iso:V3.iso,mouse:RF.mouse,inWin:RF.inWin,keys:[...RF.keys],zoomTo:RF.zoomTo,frame:frameTime})'.replace('frameTime','(V3.lastFrameAt||0)')), 'unit', (ux, uy), flush=True)
    shot('00-start')
    # 1. select one unit by clicking it: its ring turns gold at once, before any reply
    u = mine[1]
    pu = scr(u['x'], u['y'], 0.55)
    check('unit on screen and clickable', pu and free(pu), pu)
    t0 = now()
    page.mouse.click(*pu)
    page.wait_for_timeout(60)
    frame_ms()
    sel = page.evaluate("()=>V3.things.filter(t=>t.kind==='mine'&&t.selected).map(t=>t.ref)")
    S = sent(t0)
    check('click on a unit sends click3d', any(s[0] == 'click3d' for s in S), S[-1:] if S else None)
    check('its ring turns at once (optimistic selection)', sel == [u['ref']], sel)
    st = page.evaluate('rfStats()')
    check('select flash drawn on the first frame after the click', st['frames'] and st['frames'][-1] <= 1, {'frames': st['frames'], 'ms': st['drawn']})
    # the game confirms: the HUD model says so
    for x in model['units']: x['selected'] = x['ref'] == u['ref']
    model['controlGroups']['selection'] = 'ui-sel-1'
    page.evaluate('m=>updateHUD(m)', model)
    # 2. click open ground: a move ping on the next frame
    g = scr(*ground)
    check('ground on screen', g and free(g), g)
    page.mouse.move(*g)
    page.wait_for_timeout(250)
    cur_ground = page.evaluate('()=>RF.cur')
    shot('01-before-move')
    t0 = now()
    page.mouse.click(*g)
    page.wait_for_timeout(16)
    shot('02-move-ping')
    page.wait_for_timeout(80)
    st = page.evaluate('rfStats()')
    S = sent(t0)
    check('move click sends click3d with the tile', any(s[0] == 'click3d' and s[1].startswith(f'{ground[0]}|{ground[1]}|') for s in S), [s[:2] for s in S])
    check('move ping drawn on the first frame after the click', st['last'] and st['last']['k'] == 'move' and st['frames'] and st['frames'][-1] <= 1, {'frames': st['frames'], 'ms': st['drawn'], 'frame_ms': frame_ms()})
    check('pointer over open ground is the gilded arrow', cur_ground == 'base', cur_ground)
    page.wait_for_timeout(700); frame_ms()
    check('ping gone after its 0.72 s', page.evaluate('()=>RF.pings.length') == 0)
    # 3. hover a hostile: sword pointer and a red ring; click: red ping + target flash
    po = scr(npc['x'], npc['y'], 0.55)
    page.mouse.move(*po)
    page.wait_for_timeout(250)
    cur = page.evaluate("()=>({k:RF.cur,css:$('world3d').style.cursor.slice(0,40),hv:RF.hv&&RF.hv.k})")
    check('sword pointer over a hostile', cur['k'] == 'attack' and 'url(' in cur['css'], cur)
    shot('03-hover-hostile')
    t0 = now()
    page.mouse.click(*po)
    page.wait_for_timeout(50)
    st = page.evaluate('rfStats()')
    fl = page.evaluate('()=>RF.flashes.map(f=>f.k+":"+f.key)')
    check('attack click: red ping and the target flashes', st['last']['k'] == 'attack' and any(f.startswith('attack:') for f in fl), {'last': st['last'], 'flashes': fl})
    shot('04-attack-ping')
    # 4. rock: pick pointer
    if rock:
        page.evaluate('([x,y])=>{V3.cx=V3.tcx=x;V3.cy=V3.tcy=y;V3.pitch=1.2;V3.panAt=performance.now()}', list(rock))
        page.wait_for_timeout(600)
        pr = scr(rock[0], rock[1], 0.1)
        if pr and 0 < pr[0] < 1280 and 0 < pr[1] < 720 and free(pr):
            page.mouse.move(*pr)
            page.wait_for_timeout(250)
            check('pick pointer over rock', page.evaluate('()=>RF.cur') == 'mine', page.evaluate('()=>RF.hv&&{k:RF.hv.k,tile:RF.hv.tile}'))
            frame_ms()
            tag = page.evaluate("()=>{const t=$('tag3d');return t&&!t.hidden?t.textContent:null}")
            check('the pointer tag says Mine at once (no verdict from the game yet)', tag and 'Mine' in tag, tag)
            shot('04b-hover-rock')
            # the block a dig will break, on the rock's faces (bottom block first), not the rock's top (user, 06:08)
            mk = page.evaluate('''([x,y])=>{if(typeof rfMineMark!=='function')return null;const g=V3.rockGeo.get(x+','+y),top=v3peakTop(x,y),res={};
              for(const yaw of [0,Math.PI/2,Math.PI,-Math.PI/2]){const y0=V3.yaw;V3.yaw=yaw;const a=[],ok=rfMineMark(a,x,y,[1,0.8,0.3,1],0.04);V3.yaw=y0;let lo=1e9,hi=-1e9;for(let i=1;i<a.length;i+=12){lo=Math.min(lo,a[i]);hi=Math.max(hi,a[i])}
               res[yaw.toFixed(2)]={ok,verts:a.length/12,extra:(a.length/12)%24,lo:+lo.toFixed(2),hi:+hi.toFixed(2)}}return {sides:g&&g.s.length,blocks:g&&g.blocks,cut:g&&g.cut,top:+top.toFixed(2),res}}''', list(rock))
            if mk is None:
                check('the dig outline is the block that breaks, on the rock faces, with a ground arrow for faces turned away', None, 'page without rfMineMark')
            else:
                R4 = list(mk['res'].values())
                check('the dig outline is the block that breaks, on the rock faces, with a ground arrow for faces turned away',
                      all(r['ok'] and r['hi'] < mk['top'] - 0.5 for r in R4) and any(r['extra'] for r in R4), mk)
            # the order queue's mark for a dig (what stays after the click's ping): the same band, and its line ends at the foot
            qd = page.evaluate('''([x,y])=>{if(typeof rfQueueDig!=='function')return null;const a=[],e=rfQueueDig(a,{x,y,kind:'Mine'},[1,0.7,0.25,1],x+3,-(y-3)),k=e&&v3kindAt(Math.round(e[0]),Math.round(-e[1]));let hi=-1e9;for(let i=1;i<a.length;i+=12)hi=Math.max(hi,a[i]);
              return {end:e,endKind:k&&k.kind,hi:+hi.toFixed(2),top:+v3peakTop(x,y).toFixed(2),move:rfQueueDig([],{x,y,kind:'Move'},[1,1,1,1],null,null)}}''', list(rock))
            if qd is None:
                check("the order line's mark for a dig is the block that breaks, and the line ends at the face's foot", None, 'page without rfQueueDig')
            else:
                check("the order line's mark for a dig is the block that breaks, and the line ends at the face's foot",
                      qd['end'] is not None and qd['endKind'] not in ('wall', 'block') and qd['hi'] < qd['top'] - 0.5 and qd['move'] is None, qd)
            # two-block mining: the block under the pointer on the face (floor block / the one above / higher up = the
            # upper one), its outline, and the field the click and the hover carry
            setup = page.evaluate('''([x,y])=>{if(typeof rfPointBlock!=='function')return null;const g=V3.rockGeo.get(x+','+y);let best=null;
              for(const yaw of [0,Math.PI/2,Math.PI,-Math.PI/2]){const fw=[-Math.sin(yaw),-Math.cos(yaw)];for(let i=0;i<g.s.length;i++){const R=v3rockFace(g,i);if(!best&&R.n[0]*fw[0]+R.n[2]*fw[1]<-0.3)best={yaw,i}}}
              if(!best)return {skip:1};RF.saveCam=[V3.yaw,V3.pitch,V3.dist,V3.cx,V3.cy];V3.yaw=best.yaw;V3.turnTo=null;V3.pitch=0.62;V3.dist=11;const f=[-Math.sin(best.yaw),Math.cos(best.yaw)];V3.cx=V3.tcx=x-f[0]*2.5;V3.cy=V3.tcy=y-f[1]*2.5;V3.panAt=performance.now();return best}''', list(rock))
            if setup is None or setup.get('skip'):
                check('two-block mining: the pointer picks the floor block or the one above, and the click says which', None, setup and 'no face towards the camera' or 'page without rfPointBlock')
            else:
                page.wait_for_timeout(500)
                page.evaluate('()=>new Promise(r=>{let n=0;const f=()=>{if(++n>=4)r();else requestAnimationFrame(f)};requestAnimationFrame(f)})')
                tb = page.evaluate('''([x,y,i])=>{const g=V3.rockGeo.get(x+','+y),R=v3rockFace(g,i),H=Math.max(1,R.size),at=h=>v3project(R.P(0.5,Math.min(0.97,h/H)));
                  const res={};for(const [k,h] of [['floor',0.5],['above',1.5],['high',Math.min(H-0.3,4)]]){const p=at(h);res[k]=p?rfPointBlock(x,y,p[0],p[1]):'off'}
                  const p1=at(1.5);RF.over=true;RF.mouse={x:p1[0],y:p1[1]};res.click=rfWithBlock('click3d',x+'|'+y+'||0|0');res.hover=rfWithBlock('hover3d',x+'|'+y+'|');res.ridge=rfWithBlock('click3d',x+'|'+y+'||0|1');
                  const hi=b=>{const a=[];rfMineMark(a,x,y,[1,1,1,1],0.04,b);let lo=1e9,hh=-1e9;for(let j=0;j<a.length;j+=12){lo=Math.min(lo,a[j+1]);hh=Math.max(hh,a[j+1])}return [+lo.toFixed(2),+hh.toFixed(2)]};res.band0=hi(0);res.band1=hi(1);res.base=+(g.Y-(g.cut||0)).toFixed(2);return res}''', [rock[0], rock[1], setup['i']])
                check('two-block mining: the pointer picks the floor block or the one above, and the click says which',
                      tb['floor'] == 0 and tb['above'] == 1 and tb['high'] == 1 and tb['click'].endswith('|0|0|1') and tb['hover'].endswith('||0|0|1') and tb['ridge'].endswith('|0|1')
                      and tb['band0'][1] < tb['base'] + 1.2 and tb['base'] + 1.8 < tb['band1'][1] < tb['base'] + 2.2, tb)   # (the ground arrows sit at the foot)
                page.evaluate('()=>{const c=RF.saveCam;if(c){[V3.yaw,V3.pitch,V3.dist]=c;V3.cx=V3.tcx=c[3];V3.cy=V3.tcy=c[4];V3.panAt=performance.now()}RF.over=false}')
            hy = page.evaluate('([x,y])=>[rfY(x,y),v3mcutTile(x,y)?Math.min(v3peakTop(x,y),v3mcutLim(x,y)):v3peakTop(x,y),v3groundAt(x,y)]', list(rock))
            check('the dig outline sits on the rock top as drawn', abs(hy[0] - max(hy[1] if hy[1] > 0.3 else 1.2, hy[2]) - 0.04) < 0.01, hy)
        else:
            check('pick pointer over rock', None, 'rock off screen ' + str(pr))
        page.evaluate('([x,y])=>{V3.cx=V3.tcx=x;V3.cy=V3.tcy=y;V3.pitch=0.75;V3.panAt=performance.now()}', [ux, uy])
        page.wait_for_timeout(600)
    # 5. shift-queued order: a waypoint line drawn before the game answers
    page.evaluate('()=>new Promise(r=>{let n=0;const f=()=>{if(++n>=4)r();else requestAnimationFrame(f)};requestAnimationFrame(f)})')   # frames with this camera
    g2 = scr(ground[0] + 2, ground[1])
    page.keyboard.down('Shift')
    page.mouse.click(*g2)
    page.keyboard.up('Shift')
    page.wait_for_timeout(50)
    check('Shift-click queues a pending waypoint', page.evaluate('()=>RF.pend.length') == 1 and any(s[0] == 'click3d' and s[1].endswith('|1|0') for s in sent(t0)), page.evaluate('()=>RF.pend'))
    shot('05-queued')
    model['targets'] = [{'x': ground[0] + 2, 'y': ground[1], 'z': scene['z'], 'kind': 'Move', 'unit': u['ref'], 'index': 1}]
    page.evaluate('m=>updateHUD(m)', model)
    check('pending waypoint dropped once the game shows it', page.evaluate('()=>RF.pend.length') == 0)
    model['targets'] = []
    # 5b. right-click: the menu by default; with Settings → Right-click → orders, an order (Alt+right-click: the menu)
    page.mouse.click(*g, button='right'); page.wait_for_timeout(80)
    menu_default = page.evaluate("()=>!$('menu3d').hidden")
    page.keyboard.press('Escape')
    page.evaluate("()=>{const s=$('setRclick');s.value='orders';s.dispatchEvent(new Event('change'))}")
    t0 = now(); page.mouse.click(*g, button='right'); page.wait_for_timeout(80)
    S = [s[:2] for s in sent(t0)]
    menu_after = page.evaluate("()=>!$('menu3d').hidden")
    page.keyboard.down('Alt'); page.mouse.click(*g, button='right'); page.keyboard.up('Alt'); page.wait_for_timeout(80)
    menu_alt = page.evaluate("()=>!$('menu3d').hidden")
    page.keyboard.press('Escape')
    # (menu mode) a second right-click on the same spot runs the menu's main action
    page.evaluate("()=>{const s=$('setRclick');s.value='menu';s.dispatchEvent(new Event('change'))}")
    page.mouse.click(*g, button='right'); page.wait_for_timeout(80)
    main = page.evaluate("()=>{const b=$('menu3d').querySelector('.ic-act.primary');return b&&b.textContent}")
    t1 = now(); page.mouse.click(*g, button='right'); page.wait_for_timeout(80)
    S2 = [x[:2] for x in sent(t1) if x[0] != 'camera']
    check('menu mode: a second right-click on the spot runs the menu\'s main action', main and S2 and not page.evaluate("()=>!$('menu3d').hidden"), {'main': main, 'sent': S2})
    page.evaluate("()=>{const s=$('setRclick');s.value='menu';s.dispatchEvent(new Event('change'))}")
    check('right-click: menu by default; RTS setting gives the order; Alt+right-click still the menu', menu_default and any(x[0] == 'click3d' for x in S) and not menu_after and menu_alt, {'default_menu': menu_default, 'sent': S, 'menu_after': menu_after, 'alt_menu': menu_alt})
    # 5c. an empty drag box: a shaky click (10 px) is the move it meant; a big empty box keeps the selection
    gx, gy = scr(*ground)
    t0 = now()
    page.mouse.move(gx, gy); page.mouse.down(); page.mouse.move(gx + 9, gy + 4, steps=3); page.mouse.up(); page.wait_for_timeout(40)
    S1 = [s[:2] for s in sent(t0)]
    t0 = now()
    page.mouse.move(gx - 120, gy - 20); page.mouse.down(); page.mouse.move(gx - 20, gy + 40, steps=5); page.mouse.up(); page.wait_for_timeout(40)
    S2 = [s[:2] for s in sent(t0)]
    check('a shaky click (small drag) still orders; a big empty box keeps the selection', any(x[0] == 'click3d' for x in S1) and not any(x[0] in ('box3d', 'boxrefs') for x in S1 + S2), {'shaky': S1, 'empty_box': S2})
    # 6. box select all three: rings at once, boxrefs sent
    a0 = scr(mine[0]['x'] - 1, mine[0]['y'] + 1, 0.0)
    a1 = scr(mine[2]['x'] + 1, mine[2]['y'] - 1, 0.0)
    t0 = now()
    page.mouse.move(*a0); page.mouse.down(); page.mouse.move((a0[0] + a1[0])/2, (a0[1] + a1[1])/2, steps=4); page.mouse.move(*a1, steps=4); page.mouse.up()
    page.wait_for_timeout(40)
    sel = page.evaluate("()=>V3.things.filter(t=>t.kind==='mine'&&t.selected).map(t=>t.ref).sort()")
    S = [s for s in sent(t0) if s[0] == 'boxrefs']
    check('box select sends boxrefs and rings turn at once', S and sorted(sel) == sorted(m['ref'] for m in mine), {'sel': sel, 'sent': [s[:2] for s in S]})
    for x in model['units']: x['selected'] = True
    page.evaluate('m=>updateHUD(m)', model)
    # 7. double-click a dwarf: both dwarves on screen (not the human)
    p0 = scr(mine[0]['x'], mine[0]['y'], 0.55)
    t0 = now()
    page.mouse.dblclick(*p0)
    page.wait_for_timeout(60)
    S = [s for s in sent(t0) if s[0] == 'boxrefs']
    check('double-click selects that race on screen', S and set(S[-1][1].split('|')[0].split(',')) == {mine[0]['ref'], mine[1]['ref']}, [s[:2] for s in S])
    # 8. Ctrl-click: the same
    t0 = now()
    page.keyboard.down('Control'); page.mouse.click(*p0); page.keyboard.up('Control')
    page.wait_for_timeout(40)
    S = [s for s in sent(t0)]
    check('Ctrl-click selects that race on screen (no click3d)', any(s[0] == 'boxrefs' for s in S) and not any(s[0] == 'click3d' for s in S), [s[:2] for s in S])
    # 8b. faces with a modifier (Company list): Shift-click removes one from the selection, Ctrl-click keeps that people
    rows = page.evaluate("()=>Object.fromEntries([...document.querySelectorAll('#rosterList button[data-do=select]')].map(b=>{const r=b.getBoundingClientRect();return [b.dataset.value,[r.x+r.width/2,r.y+r.height/2,r.width>0]]}))")
    if rows.get(mine[2]['ref'], [0, 0, False])[2]:
        t0 = now()
        page.keyboard.down('Shift'); page.mouse.click(*rows[mine[2]['ref']][:2]); page.keyboard.up('Shift')
        page.keyboard.down('Control'); page.mouse.click(*rows[mine[0]['ref']][:2]); page.keyboard.up('Control')
        page.wait_for_timeout(40)
        S = [s[:2] for s in sent(t0) if s[0] in ('selectmany', 'select')]
        check('Shift-click a face removes it; Ctrl-click keeps that people', S == [['selectmany', mine[0]['ref'] + '|' + mine[1]['ref']], ['selectmany', mine[0]['ref'] + '|' + mine[1]['ref']]], S)
    else:
        check('Shift-click a face removes it; Ctrl-click keeps that people', None, 'Company list not shown')
    # 9. control groups from the page's keyboard
    page.evaluate('()=>document.activeElement&&document.activeElement.blur()')
    t0 = now()
    page.keyboard.press('Control+2')
    page.keyboard.press('Shift+3')
    page.wait_for_timeout(30)
    page.keyboard.press('2')
    page.wait_for_timeout(120)
    page.keyboard.press('2')
    page.wait_for_timeout(30)
    S = [s[:2] for s in sent(t0) if s[0] == 'controlgroup']
    check('Ctrl+2 saves, Shift+3 adds, 2 recalls', S[:3] == [['controlgroup', '2|Set|ui-sel-1'], ['controlgroup', '3|Add|ui-sel-1'], ['controlgroup', '2|Select|']], S)
    page.evaluate('m=>updateHUD(m)', model)
    page.wait_for_timeout(200)
    c = page.evaluate('()=>[V3.tcx,V3.tcy]')
    check('double tap jumps the camera to the group', abs(c[0] - ux) < 0.6 and abs(c[1] - uy) < 0.6, c)
    # 9b. the group bar: a chip per saved group; a click recalls it
    model['controlGroups']['groups'][1].update(count=3, names=['{Newcomer} Mason', 'Weaver', 'Smith'])
    model['controlGroups']['groups'][4].update(count=1, names=['Smith'])
    page.evaluate('m=>updateHUD(m)', model)
    chips = page.evaluate("()=>[...document.querySelectorAll('#rfGroups button')].map(b=>{const r=b.getBoundingClientRect();return [b.textContent,b.title.split('\\n')[1],r.x+r.width/2,r.y+r.height/2]})")
    t0 = now()
    if chips: page.mouse.click(chips[0][2], chips[0][3]); page.wait_for_timeout(40)
    S = [s[:2] for s in sent(t0) if s[0] == 'controlgroup']
    shot('05b-groupbar')
    check('group bar shows saved groups; a click recalls', [c[0] for c in chips] == ['2 \u00d73', '5 \u00d71'] and S == [['controlgroup', '2|Select|']], {'chips': [c[:2] for c in chips], 'sent': S})
    # 10. wheel: eased zoom
    page.mouse.move(*g)
    d0 = page.evaluate('()=>V3.dist')
    page.mouse.wheel(0, 300)
    page.wait_for_timeout(34)
    d1 = page.evaluate('()=>V3.dist')
    page.wait_for_timeout(500)
    d2 = page.evaluate('()=>V3.dist')
    check('wheel zooms out (easing itself: real app, headless frames are 250 ms)', d0 < d2 and d2 > d0 * 1.4, [round(d0, 2), round(d1, 2), round(d2, 2)])
    # 11. edge scroll to the east
    x0 = page.evaluate('()=>V3.tcx')
    page.mouse.move(1279, 360)
    frame_ms(); frame_ms()
    x1 = page.evaluate('()=>V3.tcx')
    page.mouse.move(640, 360)
    page.wait_for_timeout(200)
    x2 = page.evaluate('()=>V3.tcx')
    check('edge scroll moves the camera east and stops when the pointer leaves the edge', x1 - x0 > 2 and abs(x2 - x1) < 0.6, [round(x0, 2), round(x1, 2), round(x2, 2)])
    # the window shrinks under a pointer resting at its right edge (no mouse-out comes): no endless scroll (playtest r8)
    page.mouse.move(1279, 360); frame_ms(); page.set_viewport_size(dict(width=1024, height=640)); page.wait_for_timeout(200)
    xa = page.evaluate('()=>V3.tcx'); frame_ms(); frame_ms(); xb = page.evaluate('()=>V3.tcx')
    page.set_viewport_size(dict(width=1280, height=720)); page.mouse.move(640, 360); page.wait_for_timeout(300)
    check('a window shrunk under the pointer does not keep scrolling', abs(xb - xa) < 0.6, [round(xa, 2), round(xb, 2)])
    # 12. held arrow key pans smoothly
    y0 = page.evaluate('()=>V3.tcy')
    page.keyboard.down('ArrowUp'); frame_ms(); frame_ms(); dbg = page.evaluate("()=>({keys:[...RF.keys],active:document.activeElement&&(document.activeElement.id||document.activeElement.tagName),panV:RF.panV,on:V3.on,gl:!!V3.gl,lt:RF.lt,now:performance.now(),edge:rfEdge(performance.now()),pan:[...RF.keys].map(k=>RF_PAN[k]),tcy:V3.tcy,zoomTo:RF.zoomTo,cine:!!V3.cine})"); page.keyboard.up('ArrowUp')
    y1 = page.evaluate('()=>V3.tcy')
    check('held Up arrow pans north', y1 - y0 > 2, [round(y0, 2), round(y1, 2), dbg])
    # 13. minimap (local, round the camera): press at its right side, drag to its top: the camera follows
    mm = page.evaluate("()=>{const r=$('minimap').getBoundingClientRect();return r.width?[r.left,r.top,r.width,r.height]:null}")
    if mm:
        page.wait_for_timeout(300)
        st0 = page.evaluate('()=>({cx:RFM.cx,cy:RFM.cy,R:RFM.R})')
        S = 2*st0['R'] + 1
        page.mouse.move(mm[0] + mm[2]*0.75, mm[1] + mm[3]*0.5); page.mouse.down(); page.wait_for_timeout(100)
        c1 = page.evaluate('()=>[V3.tcx,V3.tcy]')
        page.mouse.move(mm[0] + mm[2]*0.5, mm[1] + mm[3]*0.25, steps=5); page.wait_for_timeout(100)
        c2 = page.evaluate('()=>[V3.tcx,V3.tcy]')
        page.mouse.up(); page.wait_for_timeout(100)
        want1 = st0['cx'] - st0['R'] + 0.75*S - 0.5
        want2 = st0['cy'] + st0['R'] - 0.25*S + 0.5
        shot('06-minimap')
        ok = abs(c1[0] - want1) < 3 and abs(c2[1] - want2) < 3
        check('local minimap: press and drag move the camera there', ok if ok else None, {'centre': st0, 'press': c1, 'want_x': round(want1, 1), 'drag': c2, 'want_y': round(want2, 1), 'note': 'Chrome CSS zoom maps pointer/rect differently from WebKit; the real app decides'})
        t0 = now(); page.mouse.click(mm[0] + mm[2]*0.5, mm[1] + mm[3]*0.5, button='right'); page.wait_for_timeout(40)
        S = [x[:2] for x in sent(t0) if x[0] == 'mapmove']
        check('right-click on the minimap sends the selected units there', len(S) == 1 and S[0][1].endswith('|0'), S)
        model['attackMode'] = 1; page.evaluate('m=>updateHUD(m)', model); cam0 = page.evaluate('()=>[V3.tcx,V3.tcy]')
        t0 = now(); page.mouse.click(mm[0] + mm[2]*0.4, mm[1] + mm[3]*0.4); page.wait_for_timeout(40)
        S = [x[:2] for x in sent(t0) if x[0] in ('mapmove', 'camera')]
        model['attackMode'] = 0; page.evaluate('m=>updateHUD(m)', model)
        check('Attack mode: a click on the minimap attack-moves there (camera stays)', [x[0] for x in S] == ['mapmove'] and page.evaluate('()=>[V3.tcx,V3.tcy]') == cam0, S)
        check('minimap no longer sends world-scaled camera spots', not any(s[0] == 'camera' and int(s[1].split(',')[0]) > 400 for s in sent(0)), [s[:2] for s in sent(0) if s[0] == 'camera'][-3:])
    # 14. arrows while the game window has the keyboard (Remaster-3D-Key → key3d), a game jump (rfCamTo), Z
    c0 = page.evaluate('()=>[V3.tcx,V3.tcy]')
    page.evaluate("()=>{key3d('north');key3d('north');key3d('east')}")
    c1 = page.evaluate('()=>[V3.tcx,V3.tcy]')
    check('key3d arrows step the camera north and east', c1[1] - c0[1] > 2 and c1[0] - c0[0] > 1, [c0, c1])
    model['attackMode'] = 1; page.evaluate('m=>updateHUD(m)', model); t0 = now()
    page.evaluate("()=>key3d('escape')"); page.wait_for_timeout(30)
    S = [s[:2] for s in sent(t0) if s[0] != 'camera']   # (a camera send from the arrow steps above may land here)
    model['attackMode'] = 0; page.evaluate('m=>updateHUD(m)', model)
    check('Esc from the game window (key3d escape) leaves Attack mode, keeps the selection', S == [['attackmode', '']], S)
    # A, then a right-click on the map: attack mode ends, no menu (StarCraft cancels targeting with a right-click)
    page.wait_for_timeout(550)
    model['attackMode'] = 1; page.evaluate('m=>updateHUD(m)', model)
    gp = next((q for q in ((640, 330), (560, 300), (720, 300), (640, 250)) if free(q) and page.evaluate('([x,y])=>{const t=v3pickThing(x/hudKC(),y/hudKC());return !t}', list(q))), None)
    if gp:
        t0 = now(); page.mouse.click(gp[0], gp[1], button='right'); page.wait_for_timeout(60)
        S = [s[:2] for s in sent(t0) if s[0] not in ('camera', 'hover3d')]
        menu = page.evaluate("()=>!!($('menu3d')&&!$('menu3d').hidden)")
        check('A, then a right-click: attack mode ends and no menu opens', S == [['attackmode', '']] and not menu, {'sent': S, 'menu': menu})
        page.evaluate('()=>typeof v3menuClose==="function"&&v3menuClose()')
    else:
        check('A, then a right-click: attack mode ends and no menu opens', None, 'ground off screen')
    model['attackMode'] = 0; page.evaluate('m=>updateHUD(m)', model)
    # R from the HUD page: Choose your people / start again, as the game window's R (not while a card asks something)
    page.evaluate('()=>document.activeElement&&document.activeElement.blur()'); t0 = now()
    page.keyboard.press('r'); page.wait_for_timeout(40)
    S1 = [x[:2] for x in sent(t0) if x[0] == 'action']
    model['ask'] = {'title': 'Start over', 'q': 'Start again?'}; page.evaluate('m=>updateHUD(m)', model); t0 = now()
    page.keyboard.press('r'); page.wait_for_timeout(40)
    S2 = [x[:2] for x in sent(t0) if x[0] == 'action']
    model['ask'] = None; page.evaluate('m=>updateHUD(m)', model)
    check('R from the HUD page sends Choose your people (not over a question card)', S1 == [['action', 'race']] and S2 == [], {'free': S1, 'card': S2})
    # a late 3D update built round one of our earlier pan spots doesn't drag the camera back (real client r15)
    # (the test stubs send(), so the two pan spots the game was sent are recorded as the page's send wrapper does)
    page.evaluate('([a,b,c,d])=>{const t=performance.now();RF.camSent.push([a,b,t-400],[c,d,t-100])}', [ux + 14, uy, ux, uy])
    page.evaluate('([x,y])=>{V3.tcx=x+0.2;V3.tcy=y;V3.panAt=performance.now()-1500}', [ux, uy])
    stale = page.evaluate('s=>{update3D(Object.assign({},s,{cx:s.cx_t+14,cy:s.cy_t}));return [V3.tcx,V3.tcy]}', dict(scene, cx_t=ux, cy_t=uy))
    page.evaluate('()=>{V3.panAt=performance.now()-1500}')
    moved = page.evaluate('s=>{update3D(Object.assign({},s,{cx:s.cx_t-9,cy:s.cy_t+3}));return [V3.tcx,V3.tcy]}', dict(scene, cx_t=ux, cy_t=uy))
    check('a late scene round an older pan spot keeps the camera; a real game move still moves it', abs(stale[0] - (ux + 0.2)) < 0.01 and moved == [ux - 9, uy + 3], {'stale': stale, 'moved': moved, 'want_stay': ux + 0.2})
    page.evaluate("()=>rfCamTo('%d,%d')" % (ux, uy))
    # the minimap's camera footprint stays a compact trapezoid when the camera tilts to the horizon (user, 06:01: a huge wedge)
    page.evaluate('([x,y])=>{if(typeof v3iso==="function")v3iso(false);V3.top=false;V3.pitch=0.24;V3.dist=24;V3.cx=V3.tcx=x;V3.cy=V3.tcy=y;V3.panAt=performance.now()}', [ux, uy])
    page.wait_for_timeout(400)
    page.evaluate('()=>new Promise(r=>{let n=0;const f=()=>{if(++n>=4)r();else requestAnimationFrame(f)};requestAnimationFrame(f)})')
    fp = page.evaluate('()=>{const F=rfMiniFootprint(),d=(a,b)=>Math.hypot(a[0]-b[0],a[1]-b[1]);return F&&{F,far:Math.max(...F.map(p=>Math.hypot(p[0]-V3.cx,p[1]-V3.cy))),w:[d(F[0],F[1]),d(F[3],F[2])],h:[d(F[1],F[2]),d(F[0],F[3])]}}')
    check('minimap view box at the horizon: a flat rectangle (equal opposite sides), compact', fp and abs(fp['w'][0] - fp['w'][1]) < 0.01 and abs(fp['h'][0] - fp['h'][1]) < 0.01 and fp['far'] <= 40, fp)
    page.evaluate('()=>{V3.pitch=0.75;V3.panAt=performance.now()}')
    # Esc closes the open window first (Settings, a page), and deselects only when none is open
    page.evaluate('()=>{$("btnSettings").click()}'); page.wait_for_timeout(60)
    page.evaluate('()=>document.activeElement&&document.activeElement.blur()'); t0 = now()
    page.keyboard.press('Escape'); page.wait_for_timeout(60)
    e_set = {'open_after': page.evaluate('()=>!$("settings").hidden'), 'sent': [x[:2] for x in sent(t0) if x[0] == 'action']}
    page.evaluate("()=>{const b=document.querySelector('nav [data-do=tab][data-value=village]')||document.querySelector('[data-do=tab][data-value=village]');b&&b.click()}"); page.wait_for_timeout(80)
    was_open = page.evaluate('()=>document.body.classList.contains("panel-open")')
    page.evaluate('()=>document.activeElement&&document.activeElement.blur()'); t0 = now()
    page.keyboard.press('Escape'); page.wait_for_timeout(60)
    e_pan = {'was_open': was_open, 'open_after': page.evaluate('()=>document.body.classList.contains("panel-open")'), 'sent': [x[:2] for x in sent(t0) if x[0] == 'action']}
    t0 = now(); page.keyboard.press('Escape'); page.wait_for_timeout(60)
    e_none = [x[:2] for x in sent(t0) if x[0] == 'action']
    check('Esc closes Settings / an open page first; with none open it deselects', not e_set['open_after'] and not e_set['sent'] and (not was_open or (not e_pan['open_after'] and not e_pan['sent'])) and ['action', 'clear'] in e_none, {'settings': e_set, 'page': e_pan, 'none': e_none})
    # work targets: the tile a click really works. The game's verdict names it (tx, ty: a ridge top becomes the face block
    # below it); before it, a ridge top deep in the rock means the face towards the nearest selected unit; a fishing spot
    # is fished, not picked up
    wt = page.evaluate('''([ux,uy])=>{if(typeof rfWorkTile!=='function')return null;const T=V3.terrain,K=(x,y)=>v3kindAt(x,y),rock=(x,y)=>{const k=K(x,y);return !!k&&(k.kind==='wall'||k.kind==='block')};
       let deep=null;for(let j=0;j<T.h&&!deep;j++)for(let i=0;i<T.w&&!deep;i++){const x=T.x0+i,y=T.y0+j;if(!rock(x,y))continue;let all=true;for(let a=-1;a<=1;a++)for(let b=-1;b<=1;b++)if(!rock(x+a,y+b))all=false;if(all)deep={x,y}}
       const sel=V3.things.filter(t=>t.kind==='mine').map(t=>t.selected);V3.things.forEach(t=>{if(t.kind==='mine')t.selected=1});
       const pred=deep?rfWorkTile(null,{x:deep.x,y:deep.y,up:true},'mine'):null,openNear=p=>{for(let a=-1;a<=1;a++)for(let b=-1;b<=1;b++)if((a||b)&&K(p.x+a,p.y+b)&&!['wall','block','built','tree','void'].includes(K(p.x+a,p.y+b).kind))return true;return false};
       const hv0=model.hover;model.hover={x:5,y:6,on:'tile',kind:'Mine',text:'Mine',ok:1,bad:0,tx:7,ty:8};const fromVerdict=rfWorkTile(null,{x:5,y:6,up:true},'mine');model.hover=hv0;
       const fish=rfPredict({kind:'decal',fishspot:'shallow',x:ux,y:uy,dx:ux,dy:uy},{x:ux,y:uy});
       V3.things.filter(t=>t.kind==='mine').forEach((t,i)=>t.selected=sel[i]);
       return {deep,pred,predIsFace:!!pred&&rock(pred.x,pred.y)&&openNear(pred),fromVerdict,fish}}''', [ux, uy])
    if wt is None:
        check('work targets: the verdict tile, a ridge top means its face, a fishing spot is fished', None, 'page without rfWorkTile')
    else:
        check('work targets: the verdict tile, a ridge top means its face, a fishing spot is fished',
              wt['fromVerdict'] == {'x': 7, 'y': 8} and wt['fish'] == 'fish' and (wt['deep'] is None or wt['predIsFace']), wt)
    # the top bar's idle count: a click selects the next idle unit
    ib = page.evaluate("()=>{const r=$('tbIdle').parentElement.getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2]}")
    t0 = now(); page.mouse.click(ib[0], ib[1]); page.wait_for_timeout(40)
    S = [x[:2] for x in sent(t0) if x[0] not in ('camera', 'hover3d', 'view3dsize')]
    check("a click on the top bar's idle count selects the next idle unit", S == [['idle', '']], S)
    # Esc with an item held: only the held item is let go (the selection stays)
    model['useon'] = {'item': 'Poultice', 'ref': 'it9', 'unit': mine[0]['ref'], 'hint': 'Poultice: click a wounded unit', 'targets': []}
    page.evaluate('m=>updateHUD(m)', model); page.evaluate('()=>document.activeElement&&document.activeElement.blur()'); t0 = now()
    page.keyboard.press('Escape'); page.wait_for_timeout(60)
    S = [x[:2] for x in sent(t0) if x[0] != 'camera']
    model['useon'] = None; page.evaluate('m=>updateHUD(m)', model)
    check('Esc with an item held lets it go and keeps the selection', ['useoncancel', ''] in S and not any(x[0] == 'action' and x[1] == 'clear' for x in S), S)
    # zoomed in close, a click on a person's feet or head picks them (the map's pick looked 26 px round the middle only)
    page.evaluate('([x,y])=>{V3.dist=5;V3.cx=V3.tcx=x;V3.cy=V3.tcy=y;V3.panAt=performance.now()}', [ux, uy])
    page.wait_for_timeout(500)
    page.evaluate('()=>new Promise(r=>{let n=0;const f=()=>{if(++n>=4)r();else requestAnimationFrame(f)};requestAnimationFrame(f)})')
    bp = page.evaluate("""()=>{const t=V3.things.find(t=>t.ref==='ui-test-1'),g=v3groundAt(t.dx,t.dy),f=v3project([t.dx,g+0.05,-t.dy]),h=v3project([t.dx,g+0.95,-t.dy]),
      q=v3project([t.dx+0.5,g+0.05,-t.dy-1.6]),pick=(x,y)=>{const p=v3pickThing(x,y);return p?p.ref||p.id||p.kind:null};
      return {tall:Math.round(f[1]-h[1]),feet:pick(f[0],f[1]-8),head:pick(h[0],h[1]+8),ground:pick(q[0],q[1])}}""")
    check('zoomed in, a click on the feet or the head picks the person', bp['feet'] == 'ui-test-1' and bp['head'] == 'ui-test-1' and bp['ground'] is None, bp)
    bx = page.evaluate("""()=>{const c=$('world3d').getBoundingClientRect(),P=r=>{const t=V3.things.find(t=>t.ref===r),g=v3groundAt(t.dx,t.dy);return v3project([t.dx,g+0.05,-t.dy])},a=P('ui-test-0'),b=P('ui-test-2');
      return {feet:v3boxRefs(c.left+a[0]-20,c.top+a[1]-14,c.left+b[0]+20,c.top+b[1]+10).sort(),below:v3boxRefs(c.left+a[0]-20,c.top+a[1]+40,c.left+b[0]+20,c.top+b[1]+90)}}""")
    check('zoomed in, a box round the feet takes the people (not one below them)', bx['feet'] == ['ui-test-0', 'ui-test-1', 'ui-test-2'] and bx['below'] == [], bx)
    page.evaluate('()=>{V3.dist=14;V3.panAt=performance.now()}')
    page.evaluate("()=>rfCamTo('%d,%d')" % (ux + 5, uy + 4))
    check('rfCamTo moves the camera at once', page.evaluate('()=>[V3.tcx,V3.tcy]') == [ux + 5, uy + 4])
    page.evaluate('()=>document.activeElement&&document.activeElement.blur()'); page.keyboard.press('z'); page.wait_for_timeout(50)
    c = page.evaluate('()=>[V3.tcx,V3.tcy]')
    check('Z centres the camera on the selection', abs(c[0] - ux) < 1.5 and abs(c[1] - uy) < 1.5, c)
    # one selected: a click on the card's portrait takes the camera to them
    for k, u in enumerate(model['units']): u['selected'] = k == 1
    page.evaluate('m=>updateHUD(m)', model); page.wait_for_timeout(150)
    page.evaluate("()=>rfCamTo('%d,%d')" % (ux + 9, uy - 6))
    pw = page.evaluate("()=>{const p=document.querySelector('.hf .pw');if(!p)return null;const r=p.getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2]}")
    if pw:
        page.mouse.click(pw[0], pw[1]); page.wait_for_timeout(80)   # the card's rect is in page px already
        c = page.evaluate('()=>[V3.tcx,V3.tcy]')
        check("a click on the one-unit card's portrait takes the camera to them", abs(c[0] - ux) < 1 and abs(c[1] - uy) < 1, {'cam': c, 'unit': [ux, uy]})
    else:
        check("a click on the one-unit card's portrait takes the camera to them", False, 'no portrait')
    page.wait_for_timeout(300)
    browser.close()
check('no script errors', not errors, errors[:6])
passed = all(r['ok'] for r in results.values() if r['ok'] is not None)
a.out.parent.mkdir(parents=True, exist_ok=True)
a.out.write_text(json.dumps({'passed': passed, 'checks': results, 'errors': errors[:10], 'at': time.strftime('%Y-%m-%d %H:%M:%S')}, indent=1) + '\n')
print('PASSED' if passed else 'FAILED')
raise SystemExit(0 if passed else 1)
