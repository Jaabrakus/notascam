#!/usr/bin/env python3
"""Plan mode on the real HUD page in headless Chrome (ramps-gather, 2026-10-25): a scene with a block mountain
(tests/lairs-replay/lairs-3d-10.json), trusted mouse moves and clicks from Playwright, no server: commands are recorded.

Checks: the dock's Plan button opens it (the bar, the card, the level cut); the cursor sits on the block under the
pointer on the level looked at; a drag marks the blocks of a box on that level; Clear marks a column from the level up;
a right-click unmarks; Queue it sends planadd with the blocks; the game's queued blocks (the 3D update's plan) are read
back; the game's keys (arrows, PageUp) move the cursor and the level; Esc leaves; no script errors.

  python3 tools/plan_mode/headless_plan.py [--html PAGE] [--shots DIR]"""
import argparse
import json
import tempfile
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = Path(__file__).resolve().parents[2]
ap = argparse.ArgumentParser()
ap.add_argument('--html', type=Path, default=BASE/'game/Interface/remastered.html')
ap.add_argument('--scene', type=Path, default=BASE/'tests/lairs-replay/lairs-3d-10.json')
ap.add_argument('--shots', type=Path, default=BASE/'reports/plan-mode/headless')
a = ap.parse_args()
scene = json.loads(a.scene.read_text())
results, errors = {}, []

def check(name, ok, detail=None):
    results[name] = {'ok': bool(ok), 'detail': detail}
    print(('PASS ' if ok else 'FAIL ') + name + ('' if detail is None else '  ' + json.dumps(detail)[:300]), flush=True)

with tempfile.TemporaryDirectory(prefix='pm-headless-') as tmp, sync_playwright() as pw:
    page_file = Path(tmp)/'remastered.html'
    page_file.write_text(a.html.read_text(encoding='utf-8').replace('window.location.href=', 'window.testLastURL='), encoding='utf-8')
    browser = pw.chromium.launch(executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless=True,
                                 args=['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'])
    page = browser.new_page(viewport=dict(width=1280, height=720))
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.on('console', lambda c: errors.append(c.text[:300]) if c.type == 'error' and 'Failed to load resource' not in c.text else None)
    page.goto(page_file.as_uri() + '?overlay', wait_until='domcontentloaded')
    page.evaluate("""()=>{window.__sent=[];window.send=function(a,v){window.__sent.push([a,String(v==null?'':v)])}}""")
    model = json.loads((BASE/'tests/idle-model-available.json').read_text())
    model.update(view3d=1, targets=[], hover=None, maxx=400, maxy=400, plans=[])
    page.evaluate('m=>updateHUD(m)', model)
    page.evaluate('()=>v3set(true)')
    page.evaluate('s=>update3D(s)', scene)
    frames = lambda n=4: page.evaluate('n=>new Promise(r=>{let k=0;const f=()=>{if(++k>=n)r();else requestAnimationFrame(f)};requestAnimationFrame(f)})', n)
    page.wait_for_timeout(1200); frames()
    # a column of the mountain at least 4 high with blocks beside it, near the middle: the camera on it
    spot = page.evaluate("""()=>{const T=V3.terrain;let best=null,bd=1e9;for(let j=0;j<T.h;j++)for(let i=0;i<T.w;i++){const x=T.x0+i,y=T.y0+j,K=v3kindAt(x,y);if(!K||K.kind!=='wall'||!(K.blocks>=4))continue;
       let ok=true;for(let dx=-1;dx<=2&&ok;dx++)for(let dy=-1;dy<=1;dy++){const N=v3kindAt(x+dx,y+dy);if(!N||N.kind!=='wall'||!(N.blocks>=3))ok=false}if(!ok)continue;const d=Math.hypot(x-V3.cx,y-V3.cy);if(d<bd){bd=d;best=[x,y,K.blocks]}}return best}""")
    check('the scene has a block mountain', bool(spot), spot)
    x, y, top = spot
    page.evaluate("""([x,y])=>{if(typeof v3iso==='function')v3iso(false);V3.dist=14;V3.pitch=0.95;V3.yaw=0;V3.turnTo=null;V3.cx=V3.tcx=x;V3.cy=V3.tcy=y;V3.panAt=performance.now()}""", [x, y])
    page.wait_for_timeout(800); frames()
    zoom = page.evaluate('hudKC()')
    a.shots.mkdir(parents=True, exist_ok=True)
    # 1. the dock's Plan button
    has_btn = page.evaluate("()=>!!document.getElementById('btnPlan')")
    check('the dock has a Plan button beside Gather', has_btn)
    page.click('#btnPlan'); frames()
    st = page.evaluate("()=>({on:PM.on,bar:!document.getElementById('pmBar').hidden,card:!document.getElementById('pmCard').hidden,cut:V3.planCut,level:PM.level})")
    check('Plan mode opens: the bar, the card, the whole view cut at its level', st['on'] and st['bar'] and st['card'] and abs((st['cut'] or 0) - (st['level'] + 0.4)) < 1e-6, st)
    page.evaluate('()=>{PM.level=2;document.getElementById("pmLvl").textContent="Level 2"}'); frames(3)
    L = 2
    def scr(tx, ty, h):
        p = page.evaluate('([x,y,h])=>v3project([x,h,-y])', [tx, ty, h])
        return (p[0]*zoom, p[1]*zoom) if p else None
    # 2. the cursor: on the block under the pointer, on this level
    p = scr(x, y, L + 0.4)
    page.mouse.move(*p); frames(2)
    cur = page.evaluate('()=>[PM.cx,PM.cy]')
    check('the cursor sits on the block under the pointer, on the level looked at', cur == [x, y], {'cursor': cur, 'want': [x, y]})
    page.screenshot(path=str(a.shots/'1-plan-mode.png'))
    # 3. a drag: a box of blocks on this level
    p2 = scr(x + 2, y + 1, L + 0.4)
    page.mouse.move(*p); page.mouse.down(); page.mouse.move(*p2, steps=6); frames(2)
    tagd = page.evaluate("()=>document.getElementById('pmTag').textContent")
    page.mouse.up(); frames(2)
    marks = page.evaluate('()=>[...PM.marks.keys()]')
    want = page.evaluate("""([x,y,L])=>{let n=0;for(let i=x;i<=x+2;i++)for(let j=y;j<=y+1;j++){const K=v3kindAt(i,j);if(K&&v3stackHas(K,L))n++}return n}""", [x, y, L])
    check('a drag marks the blocks of a box on that level', len(marks) == want and all(m.endswith(f',{L}') for m in marks), {'marks': len(marks), 'want': want, 'tag': tagd})
    page.screenshot(path=str(a.shots/'2-box-marked.png'))
    # 4. a right-click unmarks
    page.mouse.click(*scr(x + 1, y, L + 0.4), button='right'); frames(2)
    after = page.evaluate('()=>PM.marks.size')
    check('a right-click on a mark unmarks it', after == len(marks) - 1, {'before': len(marks), 'after': after})
    # 5. Clear: a click marks the column from this level up
    page.click('#pmBar [data-pmtool="clear"]'); frames(1)
    cx_, cy_ = x - 1, y
    page.mouse.click(*scr(cx_, cy_, L + 0.4)); frames(2)
    col = page.evaluate("([x,y])=>[...PM.marks.keys()].filter(k=>k.startsWith(x+','+y+',')).length", [cx_, cy_])
    colh = page.evaluate("([x,y,L])=>{const K=v3kindAt(x,y);let n=0;for(let k=L;k<v3stackTop(K);k++)if(v3stackHas(K,k))n++;return n}", [cx_, cy_, L])
    check('Clear marks the column from this level up', col == colh and col > 0, {'marked': col, 'column': colh})
    # 6. Queue it: planadd with the blocks
    n_before = page.evaluate('()=>PM.marks.size')
    page.click('#pmQueue'); frames(1)
    sent = [s for s in page.evaluate('()=>window.__sent') if s[0] == 'planadd']
    cells = sent[-1][1].split('|', 1)[1].split('/') if sent else []
    check('Queue it sends the blocks as a dig plan (planadd)', bool(sent) and len(cells) == n_before and page.evaluate('()=>PM.marks.size') == 0, {'sent': len(sent), 'cells': len(cells), 'marked': n_before})
    # 7. the game's answer: the queued blocks come back in the 3D update and are drawn
    sc2 = json.loads(json.dumps(scene)); sc2['plan'] = [[int(c.split(',')[0]), int(c.split(',')[1]), int(c.split(',')[2]), 1] for c in cells]
    sc2.pop('terrain', None)
    page.evaluate('s=>update3D(s)', sc2); frames(3)
    q = page.evaluate('()=>PM.qset?PM.qset.size:0')
    check('the queued blocks are read back from the 3D update', q == len(cells), {'qset': q, 'cells': len(cells)})
    page.screenshot(path=str(a.shots/'3-queued.png'))
    # 8. Build: on open ground at level 0 a drag marks blocks to lay, on level 1 a click stacks one on a mark, a click
    # in the air is refused; Queue it sends them as a build plan; the game's queued build blocks are read back
    fl = page.evaluate("""([cx,cy])=>{let best=null,bd=1e9;for(let y=cy-25;y<=cy+25;y++)for(let x=cx-25;x<=cx+25;x++){let ok=true;for(let i=0;i<4&&ok;i++)for(const yy of [y,y+1]){const K=v3kindAt(x+i,yy);if(!K||K.kind!=='floor'||K.roof)ok=false}
       if(!ok)continue;const d=Math.hypot(x-cx,y-cy);if(d<bd){bd=d;best=[x,y]}}return best}""", [x, y])
    check('the scene has open ground for building', bool(fl), fl)
    bx, by = fl
    page.evaluate("""([x,y])=>{V3.cx=V3.tcx=x;V3.cy=V3.tcy=y;V3.panAt=performance.now()}""", [bx, by])
    page.evaluate("()=>{PM.level=0;document.getElementById('pmLvl').textContent='Level 0'}"); page.wait_for_timeout(600); frames(3)
    page.click('#pmBar [data-pmtool="build"]'); page.click('#pmBar [data-pmshape="line"]'); frames(1)
    b1, b2 = scr(bx, by, 0), scr(bx + 3, by, 0)
    page.mouse.move(*b1); page.mouse.down(); page.mouse.move(*b2, steps=6); frames(2); page.mouse.up(); frames(2)
    bm = page.evaluate("()=>[...PM.marks].filter(([k,m])=>m.b).map(([k])=>k)")
    check('Build: a drag on open ground marks blocks to lay on level 0', len(bm) == 4 and all(k.endswith(',0') for k in bm), bm)
    page.evaluate("()=>{PM.level=1;document.getElementById('pmLvl').textContent='Level 1'}"); frames(2)
    page.mouse.click(*scr(bx + 1, by, 1)); frames(2)
    up = page.evaluate("k=>!!(PM.marks.get(k)&&PM.marks.get(k).b)", f'{bx + 1},{by},1')
    n0 = page.evaluate('()=>PM.marks.size')
    page.mouse.click(*scr(bx + 1, by + 1, 1)); frames(2)    # open air: open floor beside the row, nothing under it
    air = page.evaluate("()=>({n:PM.marks.size,tag:document.getElementById('pmTag').textContent})")
    check('Build: a block stacks on a mark under it, never in the air', up and air['n'] == n0 and 'nothing to build on' in air['tag'], {'stacked': up, 'air': air})
    page.screenshot(path=str(a.shots/'4-build-marked.png'))
    nb = page.evaluate('()=>PM.marks.size')
    page.click('#pmQueue'); frames(1)
    sentb = [s for s in page.evaluate('()=>window.__sent') if s[0] == 'planadd' and s[1].endswith(('|build', '|build|stone'))]   # L1 (10-27): stone plans send |build|stone
    bcells = sentb[-1][1].split('|')[1].split('/') if sentb else []
    check('Queue it sends the build marks as a build plan', len(bcells) == nb == 5, {'sent': len(sentb), 'cells': len(bcells), 'marked': nb})
    sc3 = json.loads(json.dumps(scene)); sc3.pop('terrain', None)
    sc3['plan'] = [[int(c.split(',')[0]), int(c.split(',')[1]), int(c.split(',')[2]), 1, 1] for c in bcells]
    page.evaluate('s=>update3D(s)', sc3); frames(3)
    qb = page.evaluate("""cells=>cells.filter(c=>PM.qset&&PM.qset.get(c)===1).length""", bcells)
    check('the queued build blocks are read back and drawn as blocks to build', qb == len(bcells), {'read': qb, 'cells': len(bcells)})
    page.screenshot(path=str(a.shots/'5-build-queued.png'))
    page.click('#pmBar [data-pmtool="dig"]'); page.click('#pmBar [data-pmshape="box"]'); frames(1)
    # 9. the game's keys: arrows move the cursor (turned to the camera), PageUp the level, Esc leaves
    c0 = page.evaluate('()=>[PM.cx,PM.cy,PM.level]')
    page.evaluate("()=>{key3d('north');key3d('northeast')}"); frames(1)
    c1 = page.evaluate('()=>[PM.cx,PM.cy,PM.level]')
    check('arrows move the cursor, PageUp takes it up a level', c1[2] == c0[2] + 1 and (c1[0], c1[1]) != (c0[0], c0[1]), {'before': c0, 'after': c1})
    page.evaluate("()=>key3d('escape')"); frames(2)
    off = page.evaluate("()=>({on:PM.on,cut:V3.planCut,bar:document.getElementById('pmBar').hidden})")
    check('Esc leaves Plan mode: the cut goes', not off['on'] and off['cut'] is None and off['bar'], off)
    check('no script errors', not errors, errors[:5])
    browser.close()
bad = [k for k, v in results.items() if not v['ok']]
print('PASSED' if not bad else 'FAILED: ' + ', '.join(bad))
