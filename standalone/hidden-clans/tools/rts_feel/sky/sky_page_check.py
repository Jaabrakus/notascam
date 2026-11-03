#!/usr/bin/env python3
"""Open sky on the Sky level, the page (rts-feel, 2026-10-25; tools/rts_feel/sky/apply_sky_page.py), in a real WKWebView
(the app's engine) with world-look's replay (tools/worldlook_replay.py: the real page fed a real scene, no client): the
Sky level of tests/worldlook-replay/lv-scenes.json (scene 3: mountain-top floors, open sky round them) with five of your
units selected, three of them flying. Over a grid of points on the screen, then at one point over open sky:
  - the pick there is the open-sky tile (sky), a mountain-top floor isn't;
  - flyers selected: a click predicts a move, sends the 3D click for that tile and pings a move;
  - only walkers selected: nothing predicted, the red "can't" ping at once, the click still goes to the game (it says why);
  - only flyers selected: the hover square drawn on that tile at the sky's height; walkers too: none.
Today's page and the patched one side by side (today's: no sky pick, a move predicted for walkers too).
    python3 tools/rts_feel/sky/sky_page_check.py [--page game/Interface/remastered.html] [--wkpan PATH]"""
import argparse, functools, http.server, json, shutil, subprocess, sys, tempfile, threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'tools'))
import worldlook_replay as W

ap = argparse.ArgumentParser()
ap.add_argument('--page', type=Path, default=ROOT/'game/Interface/remastered.html')
ap.add_argument('--wkpan', default='')
a = ap.parse_args()

BODY = r"""
for(let i=0;i<200&&!window.replayReady;i++)await new Promise(r=>setTimeout(r,100));await new Promise(r=>setTimeout(r,1500));
window.requestAnimationFrame=()=>0;let ts=performance.now();const frames=n=>{for(let k=0;k<n;k++){ts+=16.7;v3frame(ts)}};
const sent=[];send=function(x,v){sent.push([x,String(v)])};
const SC=await (await fetch('lv-scenes.json')).json(),m=JSON.parse(JSON.stringify(SC['3']));
const mine=m.things.filter(t=>t.kind==='mine');mine.forEach((t,i)=>{t.selected=i<5?1:0;if(i<3)t.fly=2;else delete t.fly});
model={units:mine.map(t=>({ref:t.ref,selected:!!t.selected})),hover:null,gather:0};
update3D(JSON.stringify(m));V3.dist=22;V3.pitch=0.85;V3.yaw=0.3;V3.turnTo=null;V3.userTurn=1e12;V3.cx=V3.tcx=m.cx;V3.cy=V3.tcy=m.cy;frames(30);
const c=$('world3d'),K=typeof hudKC==='function'?hudKC():1,W=c.clientWidth,H=c.clientHeight;
const grid={sky:0,other:0,none:0};let skyPt=null,floorPt=null,best=1e9;
for(let x=60;x<W-60;x+=40)for(let y=60;y<H-60;y+=40){const r=v3pickTile(x,y);if(!r){grid.none++;continue}if(r.sky){grid.sky++;const d=Math.abs(x-W/2)+Math.abs(y-H/2);if(d<best&&!v3pickThing(x,y)){best=d;skyPt=[x,y,r]}}else{grid.other++;const Kd=v3kindAt(r.x,r.y);if(!floorPt&&Kd&&Kd.kind!=='void')floorPt=[x,y,r,Kd.kind]}}
const out={z:V3.z,grid,errs:[]};
const pt=skyPt||[W/2,H/2,v3pickTile(W/2,H/2)];out.at=[pt[0],pt[1],pt[2]];out.kind=(v3kindAt(pt[2].x,pt[2].y)||{kind:null}).kind;out.floor=floorPt?[floorPt[2],floorPt[3]]:null;
const sel=V3.things.filter(t=>t.kind==='mine'&&t.selected),setFly=list=>{sel.forEach((t,i)=>{t.fly=list[i]?2:undefined})};
const click=(x,y)=>{const o={clientX:x*K,clientY:y*K,button:0,bubbles:true};c.dispatchEvent(new MouseEvent('mousedown',o));c.dispatchEvent(new MouseEvent('mouseup',o))};
const tryCase=(name,fly)=>{setFly(fly);sent.length=0;RF.pings.length=0;const r=v3pickTile(pt[0],pt[1]);const k=rfPredict(null,r);click(pt[0],pt[1]);
 const cl=sent.filter(s=>s[0]==='click3d').map(s=>s[1]);const pg=RF.pings.map(p=>p.k);
 // the hover square: what rfDraw1 draws for the pointer there
 const sq=[];const o=rfSquare;rfSquare=function(a,X,Y,Z){sq.push([+X.toFixed(2),+Y.toFixed(2),+Z.toFixed(2)]);return o.apply(this,arguments)};
 RF.over=true;RF.mouse={x:pt[0],y:pt[1]};RF.moved=true;RF.pings.length=0;RF.pend.length=0;try{rfDraw1([],performance.now())}catch(e){out.errs.push(name+': '+e)}rfSquare=o;RF.over=false;
 out[name]={predict:k,sent:cl,pings:pg,square:sq}};
tryCase('flyers and walkers',[1,1,1,0,0]);tryCase('only walkers',[0,0,0,0,0]);tryCase('only flyers',[1,1,1,1,1]);
// the faint grid (part 4): strips with only flyers selected, none with walkers or nothing once it has faded; its cost at the widest window
if(typeof rfSkyGrid==='function'){const now0=performance.now();let fr=0;const run=n=>{let len=0;for(let i=0;i<n;i++){const A=[];rfSkyGrid(A,now0+(fr++)*16.7);len=A.length}return len};
 RF.sgA=0;RF.sgT=0;setFly([1,1,1,1,1]);out.gridFlyers=run(40);setFly([0,0,0,0,0]);out.gridWalkers=run(60);setFly([1,1,1,1,1]);run(40);sel.forEach(s=>s.selected=false);out.gridNothing=run(60);sel.forEach(s=>s.selected=true);
 const T0=V3.terrain,big={x0:T0.x0-30,y0:T0.y0-25,w:101,h:81,z:3,tiles:new Array(101*81).fill(0),kinds:T0.kinds};const pk=T0.tiles.find(c=>c&&T0.kinds[c-1].kind!=='void')||1;for(let j=30;j<40;j++)for(let i=40;i<52;i++)big.tiles[j*101+i]=pk;
 V3.terrain=big;setFly([1,1,1,1,1]);run(40);let len=0;const t0=performance.now();for(let i=0;i<200;i++){const A=[];rfSkyGrid(A,now0+(fr++)*16.7);len=A.length}const tot=performance.now()-t0;V3.terrain=T0;
 out.gridCost={tiles:101*81,floats:len,frames:200,mean:+(tot/200).toFixed(3)}}   // 200 frames timed together: WebKit's clock is 1 ms coarse
// zoom: the wheel's far end stays 60 in every level view, flyers selected or not (the user: "the oringal zoom out was fine")
try{const zoomMax=sc=>{const M=JSON.parse(JSON.stringify(SC[sc]));update3D(JSON.stringify(M));frames(10);const r=[];for(const fl of [1,0]){V3.things.forEach(t=>{if(t.kind==='mine'){t.selected=true;t.fly=fl?2:undefined}});RF.zoomTo=null;for(let i=0;i<30;i++)c.dispatchEvent(new WheelEvent('wheel',{deltaY:500,deltaMode:0,bubbles:true,cancelable:true}));r.push([V3.z,fl?'flyers':'walkers',RF.zoomTo==null?null:+RF.zoomTo.toFixed(2)])}RF.zoomTo=null;return r};   /* the wheel's target (RF.zoomTo, clamped 6-60): the camera eases to it in the page's own frame loop */out.zoom=zoomMax('1').concat(zoomMax('3'))}catch(e){out.errs.push('zoom: '+e)}
// the level row: the Sky button only while the model says the Sky is yours (part 3)
try{const HM=await (await fetch('hud-model.json')).json();const lv=s=>{const M=JSON.parse(JSON.stringify(HM));M.maxz=4;M.z=1;M.sky=s;updateHUD(M);return [...$('layers').querySelectorAll('button')].map(b=>[b.textContent,!!b.hidden])};out.levelsShut=lv(0);out.levelsOpen=lv(1)}catch(e){out.errs.push('levels: '+e)}
out.errs=out.errs.concat(window.__errs||[]);return JSON.stringify(out);
"""


def main():
    work = Path(tempfile.mkdtemp(prefix='rf-sky-'))
    try:
        site = work/'site'; site.mkdir()
        for f in W.OUT.iterdir():
            if f.name not in ('replay.html',): (site/f.name).symlink_to(f)
        for name, src in (('today', ROOT/'game/Interface/remastered.html'), ('patched', a.page)):
            html = Path(src).read_text(encoding='utf-8')
            if name == 'patched' and a.page == ROOT/'game/Interface/remastered.html':
                p = work/'patched.html'; p.write_text(html, encoding='utf-8')
                subprocess.run([sys.executable, str(ROOT/'tools/rts_feel/sky/apply_sky_page.py'), str(p)], check=True, capture_output=True)
                html = p.read_text(encoding='utf-8')
            html = html.replace("function send(action,value){window.location.href=", "function send(action,value){return;window.location.href=", 1)
            i = html.index('<head>') + len('<head>')
            (site/f'{name}.html').write_text(html[:i] + '<script>window.__errs=[];addEventListener("error",e=>__errs.push(e.message+" @"+e.lineno));' + W.REPLAY + '</script>' + html[i:], encoding='utf-8')
        shutil.copy2(ROOT/'tests/work-human-model.json', site/'hud-model.json')
        (work/'body.js').write_text(BODY)
        wk = a.wkpan
        if not wk:
            wk = str(work/'wkpan'); subprocess.run(['swiftc', '-O', str(ROOT/'tools/worldlook_wkpan.swift'), '-o', wk], check=True)
        handler = functools.partial(type('Q', (http.server.SimpleHTTPRequestHandler,), {'log_message': lambda *x: None}), directory=str(site))
        srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler); port = srv.server_address[1]
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        res = {}
        for name in ('today', 'patched'):
            p = subprocess.run([wk, f'http://127.0.0.1:{port}/{name}.html?clean=1&scene=1&cx=42&cy=32&dist=22&pitch=0.85&yaw=0.3', '1440', '900', str(work/'body.js'), str(work/f'{name}.png'), '120'],
                               capture_output=True, text=True, timeout=200)
            line = next((l for l in p.stdout.splitlines() if l.startswith('PROBE ')), '')
            if not line[6:].startswith('{'): sys.exit(f'{name}: no result\n' + p.stdout[-1500:] + p.stderr[-500:])
            res[name] = json.loads(line[6:])
            shutil.copy2(work/f'{name}.png', ROOT/f'reports/polish-2026-10-22/rts-feel/sky/sky-page-{name}.png') if (ROOT/'reports/polish-2026-10-22/rts-feel/sky').exists() else None
        srv.shutdown()
        for name, r in res.items():
            print(f'== {name}: level {r["z"]}, grid {r["grid"]}, at {r["at"][:2]} tile {r["at"][2]} kind {r["kind"]}, a floor: {r["floor"]}')
            for k in ('flyers and walkers', 'only walkers', 'only flyers'):
                print(f'   {k}: {r[k]}')
            print(f'   levels, shut: {r.get("levelsShut")}; open: {r.get("levelsOpen")}')
            print(f'   zoom: {r.get("zoom")}')
            print(f'   grid: flyers {r.get("gridFlyers")} floats, walkers {r.get("gridWalkers")}, nothing {r.get("gridNothing")}; cost {r.get("gridCost")}')
            if r['errs']: print('   errors', r['errs'][:4])
        P = res['patched']; t = P['at'][2]; tile = f"{t['x']}|{t['y']}"
        checks = [
            ('the pick over open sky is the open-sky tile', bool(t.get('sky')) and P['kind'] in (None, 'void') and P['grid']['sky'] > 0),
            ('a mountain-top floor is no sky pick', not P['floor'] or not P['floor'][0].get('sky')),
            ('flyers selected: a move, the 3D click for that tile, a move ping', P['flyers and walkers']['predict'] == 'move' and any(s.startswith(tile + '|') for s in P['flyers and walkers']['sent']) and 'move' in P['flyers and walkers']['pings']),
            ('only walkers: nothing predicted, the red "can\'t" at once, the click still sent', P['only walkers']['predict'] is None and 'deny' in P['only walkers']['pings'] and any(s.startswith(tile + '|') for s in P['only walkers']['sent'])),
            ('only flyers: the hover square on that tile at the sky\'s height', any(abs(q[0] - t['x']) < 0.01 and abs(q[2] + t['y']) < 0.01 and abs(q[1]) < 0.2 for q in P['only flyers']['square'])),
            ('walkers among them: no hover square', not P['flyers and walkers']['square']),
            ('the level row: no Sky button while the Sky is shut', ['Sky', True] in P.get('levelsShut', []) and ['Surface', False] in P.get('levelsShut', [])),
            ('the level row: the Sky button once it is open', ['Sky', False] in P.get('levelsOpen', [])),
            ('the faint grid: drawn with only flyers selected on the Sky level', (P.get('gridFlyers') or 0) > 0),
            ('the faint grid: gone (faded) with walkers or nothing selected', P.get('gridWalkers') == 0 and P.get('gridNothing') == 0),
            ('the faint grid: under 0.5 ms a frame at the widest window (101x81 tiles; 200 frames timed together)', (P.get('gridCost') or {}).get('mean', 99) < 0.5),
            ('zoom: the far end is 60 on the Surface and the Sky view, flyers selected or not', len(P.get('zoom') or []) == 4 and all(59.9 <= z[2] <= 60.01 for z in P['zoom']) and {z[0] for z in P['zoom']} == {1, 3}),
            ('no page errors', not P['errs']),
        ]
        for name, ok in checks: print(('PASS ' if ok else 'FAIL ') + name)
        sys.exit(0 if all(ok for _, ok in checks) else 1)
    finally:
        shutil.rmtree(work, ignore_errors=True)


main()
