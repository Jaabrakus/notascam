#!/usr/bin/env python3
"""Orders out over open sky on the Sky level, the page's half (rts-feel, 2026-10-25; the server's: apply_sky.py).
  v3pickTile0  on the Sky level, a pick that hits no block is the open-sky tile under the pointer (the level's own plane,
               y 0, where the page draws it): marked sky
  rfPredict    open sky: a move with a flyer selected, nothing without one
  rfClick      open sky with no flyer selected: the red "can't" at once (as when the game's verdict says no one can)
  rfDraw1      the hover square on open sky while only flyers are selected (no grid: just the tile under the pointer)
  the level row and the world map's layers: the Sky button only while the HUD model says sky (a unit of yours up there)
  rfSkyGrid    the Sky level's open sky as a faint grid while only flyers are selected (the user: "Faint grid with flyers")
Exact-match edits, idempotent.
    python3 tools/rts_feel/sky/apply_sky_page.py <remastered.html>"""
import os, sys, tempfile
from pathlib import Path

EDITS = [
(""" const X=a[0]+(b[0]-a[0])*k,Z=a[2]+(b[2]-a[2])*k;return {x:Math.round(X),y:Math.round(-Z)}}""",
 """ const X=a[0]+(b[0]-a[0])*k,Z=a[2]+(b[2]-a[2])*k,rx=Math.round(X),ry=Math.round(-Z);if(V3.z===3){const K=v3kindAt(rx,ry);if(!K||K.kind==='void')return {x:rx,y:ry,sky:true}}   /* open sky on the Sky level: flyers fly there, walkers can't (Flying.dm RmOpenSky; rts-feel) */return {x:rx,y:ry}}"""),
("""function rfSelected(){return arr(model&&model.units).some(u=>u.selected)}""",
 """function rfSelected(){return arr(model&&model.units).some(u=>u.selected)}
// Your selected units in the air (the 3D view's fly height, View3D.dm): any of them, or all of them.
function rfSelFly(all){const S=V3.things.filter(t=>t.kind==='mine'&&t.selected);return S.length>0&&(all?S.every(t=>t.fly):S.some(t=>t.fly))}
// The Sky level's open sky as a faint grid while only flyers are selected (the user, 2026-10-25: "Faint grid with flyers"):
// where they can go. Only the loaded window, as long thin strips along the tile edges (one per run of open sky, not four a
// tile), none round a peak's block; it fades in and out with the selection.
function rfSkyGrid(a,now){const want=V3.z===3&&rfSelFly(true)?1:0,dt=Math.min(0.1,Math.max(0,(now-(RF.sgT||now))/1000));RF.sgT=now;RF.sgA=(RF.sgA||0)+(want-(RF.sgA||0))*Math.min(1,dt*6);if(RF.sgA<0.01)return;
 const T=V3.terrain;if(!T||!Array.isArray(T.tiles)||T.z!==3)return;const open=(x,y)=>{const i=x-T.x0,j=y-T.y0;if(i<0||j<0||i>=T.w||j>=T.h)return false;const c=T.tiles[j*T.w+i],K=c?T.kinds[c-1]:null;return !K||K.kind==='void'};
 const c=[0.86,0.93,1,0.16*RF.sgA],w=0.018,Y=0.015;
 for(let y=T.y0-1;y<T.y0+T.h;y++){let s=null;for(let x=T.x0;x<=T.x0+T.w;x++){const on=x<T.x0+T.w&&(open(x,y)||open(x,y+1));if(on&&s===null)s=x;else if(!on&&s!==null){const Z=-(y+0.5);quad(a,[s-0.5,Y,Z-w],[x-0.5,Y,Z-w],[x-0.5,Y,Z+w],[s-0.5,Y,Z+w],[0,0,0],c);s=null}}}   // the edges between rows y and y+1
 for(let x=T.x0-1;x<T.x0+T.w;x++){let s=null;for(let y=T.y0;y<=T.y0+T.h;y++){const on=y<T.y0+T.h&&(open(x,y)||open(x+1,y));if(on&&s===null)s=y;else if(!on&&s!==null){const X=x+0.5;quad(a,[X-w,Y,-(s-0.5)],[X+w,Y,-(s-0.5)],[X+w,Y,-(y-0.5)],[X-w,Y,-(y-0.5)],[0,0,0],c);s=null}}}}   // between columns x and x+1"""),
(""" try{rfGatherLines(a)}catch(e){V3.reach=null}
""", """ try{rfGatherLines(a)}catch(e){V3.reach=null}
 try{rfSkyGrid(a,now)}catch(e){}   // the Sky level's open sky while only flyers are selected
"""),
(""" if(t&&t.fishspot&&rfGather())return 'fish';   // a fishing spot: the selected fish it from the shore (QoL.dm, Fishing.dm)
""", """ if(t&&t.fishspot&&rfGather())return 'fish';   // a fishing spot: the selected fish it from the shore (QoL.dm, Fishing.dm)
 if(tile.sky&&!t)return rfSelFly()?'move':null;   // open sky (Sky level): the flyers fly there, the walkers stay (Orders.dm); none fly: no one can
"""),
("""if(!k){const hv=model&&model.hover;if(rfSelected()&&hv&&hv.x===tile.x&&hv.y===tile.y&&hv.bad&&!hv.ok&&!model.mode&&!V3.build&&!V3.shop){""",
 """if(!k){const hv=model&&model.hover;if(rfSelected()&&(hv&&hv.x===tile.x&&hv.y===tile.y&&hv.bad&&!hv.ok||tile.sky&&!t)&&!model.mode&&!V3.build&&!V3.shop){"""),
("""if(!done)rfSquare(a,T.x,rfY(T.x,T.y),-T.y,0.49+pu*0.5,0.035,rfLit(RF_COL[H.k],1.15))}}
 else if(RF.cur&&!RF.over)rfCursor(null)}""",
 """if(!done)rfSquare(a,T.x,rfY(T.x,T.y),-T.y,0.49+pu*0.5,0.035,rfLit(RF_COL[H.k],1.15))}
  else if(H&&H.tile&&!H.t&&H.tile.sky&&H.k==='move'&&rfSelFly(true))rfSquare(a,H.tile.x,rfY(H.tile.x,H.tile.y),-H.tile.y,0.49+pu*0.5,0.035,rfLit(RF_COL.move,1.15))}   // open sky with only flyers selected: the tile they would fly to
 else if(RF.cur&&!RF.over)rfCursor(null)}"""),
("""$('layers').querySelectorAll('button').forEach(b=>b.classList.toggle('active',Number(b.dataset.value)===m.z));""",
 """$('layers').querySelectorAll('button').forEach(b=>{b.classList.toggle('active',Number(b.dataset.value)===m.z);if(Number(b.dataset.value)===3)b.hidden=!m.sky&&m.z!==3});   /* the Sky: only once one of your units is up there (Flying.dm RmSkyOpen) */"""),
("""L.querySelectorAll('button').forEach(b=>b.setAttribute('aria-pressed',String(+b.dataset.z===W.z)))}""",
 """L.querySelectorAll('button').forEach(b=>{b.setAttribute('aria-pressed',String(+b.dataset.z===W.z));if(+b.dataset.z===3)b.hidden=!(model&&model.sky)&&W.z!==3})}   /* the Sky: earned (Flying.dm) */"""),
]


def main(page):
    p = Path(page)
    t = p.read_text(encoding='utf-8')
    done = 0
    for old, new in EDITS:
        if new in t: continue
        if t.count(old) != 1: sys.exit(f'{p}: no unique match for:\n{old[:160]}')
        t = t.replace(old, new); done += 1
    if done:
        fd, tmp = tempfile.mkstemp(dir=p.parent, prefix='.sky-'); os.write(fd, t.encode('utf-8')); os.close(fd)
        os.chmod(tmp, p.stat().st_mode); os.replace(tmp, p)
    print(f'{p}: {done} edit(s)' if done else f'{p}: already applied')


if __name__ == '__main__':
    main(sys.argv[1])
