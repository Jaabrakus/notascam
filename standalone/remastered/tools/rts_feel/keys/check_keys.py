#!/usr/bin/env python3
"""The 2006 letter keys off the keyboard, checked with no game window (rts-feel, 2026-10-25; apply_keys.py and
apply_keys_page.py). --game is the patched copy; today's game/ runs beside it.
  The skin: every macro name once (a duplicate stops the client loading the interface); none of the 2006 letters; C and
    X go to the page; every key Remaster-3D-Key passes is one Attack.dm lets through.
  The action list (Actions.dm) and the border controls (border-controls.json): no command shows a key that's gone.
  The page, in a real WKWebView (the app's engine) with world-look's replay (a real scene, no client):
    W, S and D held: the camera doesn't move, nothing sent; the arrows still pan;
    R: nothing sent (today: Choose your people); P still stops, A still turns Attack mode on;
    C and X from the game window (key3d): the cutaway and the x-ray, as the page's own C and X.
    python3 tools/rts_feel/keys/check_keys.py --game <patched game folder> [--wkpan PATH]"""
import argparse, collections, functools, http.server, json, re, shutil, subprocess, sys, tempfile, threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'tools'))
import worldlook_replay as W

GONE = ['W', 'S', 'D', 'Y', 'U', 'L', '-', 'R', 'H', 'J', 'K', 'M', 'O', 'T', 'V', '=', '/']   # B: the Build bar's key since 10-26 (the owner: "Yes, B and T"; T went with Tend; hud-controls)

BODY = r"""
for(let i=0;i<200&&!window.replayReady;i++)await new Promise(r=>setTimeout(r,100));await new Promise(r=>setTimeout(r,1500));
window.requestAnimationFrame=()=>0;let ts=performance.now();
const sent=[];send=function(x,v){sent.push(x+':'+String(v))};
const SC=await (await fetch('lv-scenes.json')).json(),m=JSON.parse(JSON.stringify(SC['1']));
model={units:[],hover:null,gather:0,maxx:1000,maxy:1000};
update3D(JSON.stringify(m));V3.dist=22;V3.pitch=0.85;V3.yaw=0.3;V3.turnTo=null;V3.userTurn=1e12;V3.cx=V3.tcx=m.cx;V3.cy=V3.tcy=m.cy;
RF.edgeOk=false;RF.inWin=false;for(let i=0;i<10;i++){ts+=16.7;v3frame(ts)}
const out={errs:[],gl:!!V3.gl,on:!!V3.on};
const tick=n=>{for(let i=0;i<n;i++){ts+=16.7;rfTick(ts)}};
const ev=(type,key,code)=>document.body.dispatchEvent(new KeyboardEvent(type,{key,code,bubbles:true,cancelable:true}));
const at=()=>[V3.tcx,V3.tcy];
const hold=(key,code)=>{const a=at();sent.length=0;ev('keydown',key,code);tick(30);ev('keyup',key,code);tick(2);const b=at();return {moved:+Math.hypot(b[0]-a[0],b[1]-a[1]).toFixed(2),sent:sent.slice()}};
const press=(key,code)=>{sent.length=0;ev('keydown',key,code);ev('keyup',key,code);return sent.slice()};
const game=k=>{sent.length=0;try{window.key3d(k)}catch(e){out.errs.push('key3d '+k+': '+e)}return sent.slice()};
try{
 out.w=hold('w','KeyW');out.s=hold('s','KeyS');out.d=hold('d','KeyD');out.up=hold('ArrowUp','ArrowUp');out.right=hold('ArrowRight','ArrowRight');
 out.r=press('r','KeyR');out.p=press('p','KeyP');out.a=press('a','KeyA');
 out.c_page=press('c','KeyC');out.c_game=game('c');out.x_page=press('x','KeyX');out.x_game=game('x');out.x_after=V3.xray;
 out.n_game=game('n');out.esc_game=game('escape');
}catch(e){out.errs.push(String(e))}
out.errs=out.errs.concat(window.__errs||[]);return JSON.stringify(out);
"""


def skin_macros(text):
    block = text[text.index('macro "macro"'):text.index('menu "menu"')]
    return re.findall(r'\tname = "((?:[^"\\]|\\.)*)"\n\t\tcommand = "((?:[^"\\]|\\.)*)"', block)


def static(game):
    res = []
    macros = skin_macros((game/'skin.dmf').read_text(encoding='latin-1'))
    names = collections.Counter(n for n, _ in macros)
    cmd = dict(macros)
    res.append((f'the skin: every macro name once ({len(macros)} macros)', all(v == 1 for v in names.values())))
    res.append(('the skin: none of the 2006 letters (' + ' '.join(GONE) + ')', not [k for k in GONE if k in cmd]))
    res.append(('the skin: C and X go to the page (cutaway, x-ray)', cmd.get('C') == 'Remaster-3D-Key \\"c\\"' and cmd.get('X') == 'Remaster-3D-Key \\"x\\"'))
    res.append(('the skin: A is attack, as before', cmd.get('A') == 'Remaster-Attack'))
    res.append(('the skin: B goes to the page (the Build bar)', cmd.get('B') == 'Remaster-3D-Key \\"b\\"'))
    att = (game/'Code/Remastered/Attack.dm').read_text(encoding='latin-1')
    allowed = re.search(r'if\(client && \(k in list\(([^)]*)\)\)\) src << output\(k, "mapwindow.hud:key3d"\)', att)
    allowed = set(re.findall(r'"([^"]+)"', allowed.group(1))) if allowed else set()
    passed = {re.match(r'Remaster-3D-Key \\"([^\\]+)\\"', c).group(1) for _, c in macros if c.startswith('Remaster-3D-Key')}
    res.append((f'the skin: every key it passes to the page gets through ({", ".join(sorted(passed))})', bool(passed) and passed <= allowed))
    act = (game/'Code/Remastered/Actions.dm').read_text(encoding='latin-1')
    keys = re.findall(r'list\("(\w+)", "[^"]*", "([^"]+)", [01],', act)
    bad = [(i, k) for i, k in keys if k in GONE + ['C', 'X'] or (i == 'warp' and k == 'G')]
    res.append((f'the action list: no command shows a key that is gone (keys left: {", ".join(k for _, k in keys)})', not bad))
    bc = json.loads((game/'Interface/border-controls.json').read_text(encoding='utf-8'))
    bad = [(c['id'], c['key']) for c in bc if c.get('key') in GONE + ['C'] or (c['id'] == 'warp' and c.get('key') == 'G')]
    res.append(('the border controls: no command shows a key that is gone', not bad))
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--game', type=Path, required=True)
    ap.add_argument('--wkpan', default='')
    a = ap.parse_args()
    checks = static(a.game)
    base = static(ROOT/'game')
    work = Path(tempfile.mkdtemp(prefix='rf-keys-'))
    try:
        site = work/'site'; site.mkdir()
        for f in W.OUT.iterdir():
            if f.name not in ('replay.html',): (site/f.name).symlink_to(f)
        for name, src in (('today', ROOT/'game/Interface/remastered.html'), ('patched', a.game/'Interface/remastered.html')):
            html = Path(src).read_text(encoding='utf-8')
            html = html.replace("function send(action,value){window.location.href=", "function send(action,value){return;window.location.href=", 1)
            i = html.index('<head>') + len('<head>')
            (site/f'{name}.html').write_text(html[:i] + '<script>window.__errs=[];addEventListener("error",e=>__errs.push(e.message+" @"+e.lineno));' + W.REPLAY + '</script>' + html[i:], encoding='utf-8')
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
        srv.shutdown()
        for name, r in res.items():
            print(f'== {name}: ' + json.dumps(r))
        print('== the skin and the lists, today: ' + '; '.join(('ok ' if ok else 'NO ') + n.split(' (')[0] for n, ok in base))
        P = res['patched']
        stack = lambda s: any(x.startswith('stack3d:') for x in s)
        xray = lambda s: any(x.startswith('xray3d:') for x in s)
        checks += [
            ('the page runs in 3D (WebGL on)', P['on'] and P['gl']),
            ('W, S and D held: the camera stays, nothing sent', all(P[k]['moved'] == 0 and not P[k]['sent'] for k in ('w', 's', 'd'))),
            ('the arrows still pan', P['up']['moved'] > 1 and P['right']['moved'] > 1),
            ('R: nothing sent', not P['r']),
            ('P still stops', 'action:stop' in P['p']),
            ('A still turns Attack mode on', 'attackmode:' in P['a']),
            ('C from the game window: the cutaway, as the page\'s C', stack(P['c_page']) and stack(P['c_game'])),
            ('X from the game window: the x-ray, as the page\'s X', xray(P['x_page']) and xray(P['x_game'])),
            ('no page errors', not P['errs']),
        ]
        for name, ok in checks: print(('PASS ' if ok else 'FAIL ') + name)
        sys.exit(0 if all(ok for _, ok in checks) else 1)
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == '__main__':
    main()
