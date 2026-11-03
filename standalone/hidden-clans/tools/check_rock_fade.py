#!/usr/bin/env python3
"""The camera near rock and what fades (world-look, 2026-10-23): the 3D view's real page code in headless Chrome on the
Mac's GPU, fed the dumped scenes (tools/worldlook_replay.py), no client and no input.

  python3 tools/check_rock_fade.py [OUT] [--only orbit,clicks] [--stills]

orbit   A villager at the foot of the mountain in scene 3 (70,38; rock from x=71 east). The camera turns twice round it
        (the page's own E-key turn), free and iso, then pans along the mountain's edge. Per frame: the eye's height, its
        distance from the point looked at, the aim height, whether rock stands between the eye and the unit, and how far
        the rock there is faded. Pass: the aim stays flat (< 0.05), the eye moves < 0.35 and its distance < 0.3 a frame
        (no snaps), and the unit is behind unfaded rock in under 8 % of the frames it is behind rock (the fade easing in).
clicks  A selected villager behind rock (scene 3, the camera over the mountain) and behind trees (scene 5, 10,48 in the
        forest). Playwright mouse clicks on the canvas, through the page's own handlers (what it sends is caught). Pass:
        a click on the unit sends it; a click on the faded rock or tree beside it goes to the ground behind; a click on
        rock or a tree away from it still picks that.
--stills  also save before/after-style stills of the ridge at four angles (free and iso) into OUT.
WORLDLOOK_HTML=<page> checks another copy of the page (as worldlook_replay.py). Exit status 1 on any failure."""
import argparse
import json
import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import worldlook_replay as W   # noqa: E402

ROOT = Path(__file__).resolve().parents[1]

UNIT = r"""(([x,y])=>{const d=window.replayData,src=d.things.find(t=>t.kind==='mine');const u=JSON.parse(JSON.stringify(src));u.ref=u.id='probe-1';u.x=x;u.y=y;u.selected=1;u.name='Probe';d.things=d.things.filter(t=>t.ref!=='probe-1');d.things.push(u);update3D(d);
 window.sends=[];send=function(a,v){sends.push([a,String(v)])};return true})"""

LOG = r"""(()=>{window.hides=(P,E)=>{const G=V3.hgt;if(!G)return false;let top=0;for(let k=0;k<G.H.length;k++)if(G.H[k]>top)top=G.H[k];const dx=E[0]-P[0],dy=E[1]-P[1],dz=E[2]-P[2],n=Math.min(300,Math.ceil(Math.hypot(dx,dz)/0.2));
  for(let s=1;s<=n;s++){const f=s/n,y=P[1]+dy*f;if(dy>0&&y>top+0.2)return false;const g=v3groundAt(P[0]+dx*f,-(P[2]+dz*f));if(g>0.5&&y<g-0.1)return true}return false};
 const L=window.orbitLog=[];const prev=v3frame;v3frame=function(ts){prev(ts);const e=V3.eye;if(!e)return;const t=[V3.cx,V3.camH,-V3.cy],u=V3.things.find(x=>x.ref==='probe-1'),ud=u&&V3.disp.get(u.key);
  const U=ud?[ud.dx,0.9,-ud.dy]:null;L.push({yaw:V3.yaw,ey:e[1],camH:V3.camH,dist:Math.hypot(e[0]-t[0],e[1]-t[1],e[2]-t[2]),hid:U?hides(U,e):null,fade:V3.fprF?V3.fprF[0]:null});if(L.length>4000)L.shift()};return true})()"""


def orbit_stats(L):
    ey = [r['ey'] for r in L]; di = [r['dist'] for r in L]; ch = [r['camH'] for r in L]
    hid = [r for r in L if r['hid']]
    return dict(frames=len(L), eye_y=[round(min(ey), 2), round(max(ey), 2)], eye_step_max=round(max(abs(ey[i + 1] - ey[i]) for i in range(len(ey) - 1)), 3),
                dist=[round(min(di), 2), round(max(di), 2)], dist_step_max=round(max(abs(di[i + 1] - di[i]) for i in range(len(di) - 1)), 3),
                aim_range=round(max(ch) - min(ch), 3), behind_rock=len(hid), behind_unfaded=sum(1 for r in hid if not (r['fade'] or 0) > 0.5))


def orbit_ok(s):
    return s['aim_range'] < 0.05 and s['eye_step_max'] < 0.35 and s['dist_step_max'] < 0.3 and s['behind_unfaded'] <= 0.08 * max(1, s['behind_rock'])


def orbit(p, base, out, stills):
    res = {}
    for iso in ('0', '1'):
        W.load(p, base + f'scene=3&cx=70&cy=38&dist=9&pitch=0.32&yaw=0&dayp=0.4&iso={iso}', settle=2200)
        p.evaluate(UNIT, [70, 38]); p.evaluate(LOG)
        if iso == '1': p.evaluate('V3.iso=true;0')
        p.wait_for_timeout(800)
        if stills:
            for name, ya in (('east', math.pi / 2), ('northeast', math.pi * 0.75), ('southeast', math.pi * 0.25), ('west', -math.pi / 2)):
                p.evaluate(f'V3.turnTo=null;V3.yaw={ya};' + ('V3.pitch=V3.ISOPITCH;' if iso == '1' else 'V3.pitch=0.32;') + 'V3.userTurn=performance.now()+1e9;0')
                p.wait_for_timeout(1600)
                p.screenshot(path=str(out / f'ridge-{name}-iso{iso}.jpg'), type='jpeg', quality=85)
        p.evaluate('window.orbitLog.length=0;V3.yaw=0;V3.keys.add("e");0')
        p.wait_for_timeout(8200)
        p.evaluate('V3.keys.delete("e");0')
        res[f'orbit-iso{iso}'] = orbit_stats(p.evaluate('window.orbitLog.slice()'))
        p.evaluate('window.orbitLog.length=0;V3.yaw=Math.PI/2;V3.userTurn=performance.now()+1e9;window.panT0=performance.now();window.panI=setInterval(()=>{const k=(performance.now()-panT0)/6000;V3.tcx=69;V3.tcy=30+16*Math.min(1,k)},16);0')
        p.wait_for_timeout(6500)
        p.evaluate('clearInterval(window.panI);0')
        s = orbit_stats(p.evaluate('window.orbitLog.slice()'))
        s.pop('behind_rock'); s.pop('behind_unfaded')   # the unit stays put while the camera pans: only the camera's moves count here
        s['behind_rock'] = 0; s['behind_unfaded'] = 0
        res[f'pan-iso{iso}'] = s
    for k, s in res.items(): s['ok'] = orbit_ok(s)
    return res


SCAN = r"""((kinds)=>{const u=V3.things.find(t=>t.ref==='probe-1'),s=v3project([u.dx,0.6,-u.dy]),K=t=>t?(v3kindAt(t.x,t.y)||{}).kind:null;const has=typeof v3fadedAt==='function';
 const pick=(x,y,faded)=>{if(!has)return v3pickTile(x,y);const f=v3fadedAt;if(!faded)v3fadedAt=()=>false;try{return v3pickTile(x,y)}finally{v3fadedAt=f}};
 let through=null,still=null;for(let r=28;r<=150&&!through;r+=6)for(let a=0;a<24;a++){const x=s[0]+Math.cos(a/24*6.283)*r,y=s[1]+Math.sin(a/24*6.283)*r*1.3;if(v3pickThing(x,y))continue;const p0=pick(x,y,false),p1=pick(x,y,true);
  if(!through&&p0&&kinds.includes(K(p0))&&p1&&!kinds.includes(K(p1)))through=[Math.round(x),Math.round(y)]}
 for(let r=160;r<=520&&!still;r+=20)for(let a=0;a<24&&!still;a++){const x=s[0]+Math.cos(a/24*6.283)*r,y=s[1]+Math.sin(a/24*6.283)*r;if(x<20||y<20||x>1420||y>880||v3pickThing(x,y))continue;const p=pick(x,y,true);if(p&&kinds.includes(K(p)))still=[Math.round(x),Math.round(y)]}
 return {unit:s.map(Math.round),through,still}})"""
CLICK_SCENES = {
    'rock': dict(url=f'scene=3&cx=70&cy=38&dist=9&pitch=0.32&yaw={math.pi / 2}&dayp=0.4&iso=0', at=[70, 38], yaw=math.pi / 2, kinds=['wall', 'block']),
    'tree': dict(url='scene=5&cx=10&cy=48&dist=9&pitch=0.42&yaw=0.6&dayp=0.4&iso=0', at=[10, 48], yaw=0.6, kinds=['tree']),
}


def clicks(p, base):
    res = {}
    for name, S in CLICK_SCENES.items():
        W.load(p, base + S['url'], settle=1800)
        p.evaluate(UNIT, S['at'])
        p.evaluate(f'V3.turnTo=null;V3.yaw={S["yaw"]};V3.userTurn=performance.now()+1e9;0')
        p.wait_for_timeout(1500)
        sc = p.evaluate(SCAN, S['kinds'])
        r = dict(points=sc)
        for what, pt in (('unit', sc['unit']), ('faded', sc['through']), ('away', sc['still'])):
            if not pt: r[what] = None; continue
            p.mouse.move(pt[0], pt[1]); p.wait_for_timeout(120)
            hover = p.evaluate('(()=>{const t=V3.hoverTile;return t?[t.x,t.y,(v3kindAt(t.x,t.y)||{}).kind]:null})()')
            p.mouse.click(pt[0], pt[1]); p.wait_for_timeout(150)
            sent = p.evaluate('(()=>{const r=sends.slice();sends.length=0;return r})()')
            clk = [v for a, v in sent if a == 'click3d']
            tile = None
            if clk:
                f = clk[0].split('|'); tile = [int(f[0]), int(f[1]), p.evaluate(f'(v3kindAt({f[0]},{f[1]})||{{}}).kind'), f[2]]
            r[what] = dict(at=pt, hover=hover, click=tile)
        r['ok'] = bool(r.get('unit') and r['unit']['click'] and r['unit']['click'][3] == 'probe-1'
                       and r.get('faded') and r['faded']['click'] and r['faded']['click'][2] not in S['kinds'] and r['faded']['hover'] and r['faded']['hover'][2] not in S['kinds']
                       and r.get('away') and r['away']['click'] and r['away']['click'][2] in S['kinds'])
        res[name] = r
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('out', nargs='?', type=Path, default=ROOT / 'reports/polish-2026-10-22/world-look/rock-fade')
    ap.add_argument('--only', default='orbit,clicks')
    ap.add_argument('--stills', action='store_true')
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    from playwright.sync_api import sync_playwright
    W.page()
    res = {}
    with W.Server() as s, sync_playwright() as pw:
        b, p, errs = W.browser(pw, 1440, 900)
        if 'orbit' in a.only: res['orbit'] = orbit(p, s.base, a.out, a.stills)
        if 'clicks' in a.only: res['clicks'] = clicks(p, s.base)
        res['errors'] = errs + p.evaluate('window.__errs||[]')
        b.close()
    ok = not res['errors'] and all(v['ok'] for part in ('orbit', 'clicks') for v in res.get(part, {}).values())
    res['ok'] = ok
    (a.out / 'check_rock_fade.json').write_text(json.dumps(res, indent=1) + '\n')
    print(json.dumps(res, indent=1))
    print('PASS' if ok else 'FAIL')
    raise SystemExit(0 if ok else 1)


if __name__ == '__main__':
    main()
