#!/usr/bin/env python3
"""Put the rts-feel hooks and module into a copy of remastered.html (or the real one), by exact-match replacement.
Idempotent: hooks already present are skipped; the module (between its marker comments) is replaced.
  python3 tools/rts_feel/patch_hooks.py PAGE MODULE.js"""
import sys
from pathlib import Path

HOOKS = [
    # the instant answer to a 3D click, just before it is sent (rfClick returns true when it handled it)
    ("if(!tile)return;if(!t&&tile.roof&&",
     "if(!tile)return;{let rfh=false;try{rfh=typeof rfClick==='function'&&rfClick(e,t,tile)}catch(err){console.error(err)}if(rfh)return}if(!t&&tile.roof&&"),
    ("if(refs.length){send('boxrefs',",
     "if(refs.length){try{if(typeof rfBoxFx==='function')rfBoxFx(refs,e.shiftKey)}catch(err){console.error(err)}send('boxrefs',"),
    ("c.addEventListener('dblclick',e=>{if(!V3.on||V3.build||V3.shop)return;",
     "c.addEventListener('dblclick',e=>{if(!V3.on||V3.build||V3.shop)return;{let rfh=false;try{rfh=typeof rfDbl==='function'&&rfDbl(e)}catch(err){console.error(err)}if(rfh)return}"),
    # a drag box that caught none of yours: a shaky click stays a click; a real box keeps the selection
    ("const a=v3pickTile(d.x,d.y),b=v3pickTile(mx(e),my(e));if(a&&b)send('box3d'",
     "{let rfh=false;try{rfh=typeof rfEmptyBox==='function'&&rfEmptyBox(e,d)}catch(err){console.error(err)}if(rfh)return}const a=v3pickTile(d.x,d.y),b=v3pickTile(mx(e),my(e));if(a&&b)send('box3d'"),
    # right-click: an order when the player chose RTS-style right-click (Settings), else the menu as before
    ("if(V3.aim){send('specialcancel','');return}v3menuOpen(mx(e),my(e));return}",
     "if(V3.aim){send('specialcancel','');return}{let rfh=false;try{rfh=typeof rfRightClick==='function'&&rfRightClick(e)}catch(err){console.error(err)}if(rfh)return}v3menuOpen(mx(e),my(e));return}"),
    ("  v3drawPartRing(a); // the part of a great beast under the pointer\n",
     "  v3drawPartRing(a); // the part of a great beast under the pointer\n"
     "  if(typeof rfDraw==='function')try{rfDraw(a)}catch(err){if(!V3.rfErr){V3.rfErr=1;console.error(err)}}   // order pings, target flashes, the ring under the pointer (rts-feel)\n"),
    # the order queue's target outlines (the main script): a dig's is the block that will break, on the rock face
    ('   for(const t of q.list){const X=t.x,Z=-t.y,h=0.47,c=t.color,Y=gy(X,Z);strip(X-h,Z+h,X+h,Z+h,0.045,c,Y);strip(X+h,Z+h,X+h,Z-h,0.045,c,Y);strip(X+h,Z-h,X-h,Z-h,0.045,c,Y);strip(X-h,Z-h,X-h,Z+h,0.045,c,Y);\n    if(px!=null)strip(px,pz,X,Z,0.025,[c[0]*0.8,c[1]*0.8,c[2]*0.8,1]);px=X;pz=Z}}',
     "   for(const t of q.list){const X=t.x,Z=-t.y,h=0.47,c=t.color,Y=gy(X,Z);let dug=null;try{dug=typeof rfQueueDig==='function'?rfQueueDig(hl,t,c,px,pz):null}catch(err){dug=null}   // a dig: the block that will break on the rock's face, not a square on its top (rts-feel)\n    if(!dug){strip(X-h,Z+h,X+h,Z+h,0.045,c,Y);strip(X+h,Z+h,X+h,Z-h,0.045,c,Y);strip(X+h,Z-h,X-h,Z-h,0.045,c,Y);strip(X-h,Z-h,X-h,Z+h,0.045,c,Y)}\n    const ex=dug?dug[0]:X,ez=dug?dug[1]:Z;if(px!=null)strip(px,pz,ex,ez,0.025,[c[0]*0.8,c[1]*0.8,c[2]*0.8,1]);px=ex;pz=ez}}"),
    # two-block mining (rts-feel 2026-10-23, world-look told on the board): the crack rows say which block is worked
    ("for(const w of arr(m.work)){const [x,y,dmg,blows,dx,dy,broken,roof]=w,key=x+','+y,p=old.get(key),e={x,y,dmg,blows,dx,dy,broken,roof};",
     "for(const w of arr(m.work)){const [x,y,dmg,blows,dx,dy,broken,roof,lvl]=w,key=x+','+y,p=old.get(key),e={x,y,dmg,blows,dx,dy,broken,roof,lvl};"),
    ("const lvl=g.blocks?(g.cut?1:0):-1,st=g.blocks?Math.min(9,Math.max(0,Math.floor((e.dmg-lvl*50)/5))):stage;",
     "const K0=v3kindAt(e.x,e.y),half=K0&&K0.dug?1:0,one=!!g.stack&&e.lvl>=2,lvl=g.blocks?(e.lvl===0||e.lvl===1||one?e.lvl:(g.cut?1:0)):-1,st=g.blocks?(one?Math.min(9,Math.floor(e.dmg/10)):Math.min(9,Math.max(0,Math.floor((e.dmg-half*50)/5)))):stage,gc=g.stack&&lvl>=0&&g.L&&g.L[lvl]&&g.L[lvl].length?((g.crk=g.crk||{})[lvl]||(g.crk[lvl]={Y:g.Y+lvl,c:g.c,cut:lvl,blocks:g.blocks,s:g.L[lvl].map(f=>[f.d,f.c,f.m])})):g;"),
    # dug 2 (the block above out first) draws as the full column until world-look's recess for it
    ("if(K.kind==='wall'&&K.blocks&&K.dug&&!fill&&V3.models){const G=v3cutRock(g,T,kindAt,i,j,X,Y,Z,K,1,true);",
     "if(K.kind==='wall'&&K.blocks&&K.dug===1&&!fill&&V3.models){const G=v3cutRock(g,T,kindAt,i,j,X,Y,Z,K,1,true);"),
    ("else if(a.kind==='wall'&&b.kind==='wall'&&!a.dug&&b.dug){V3.bfx.push({type:'burst',x,y,t:now,col:hexrgb(a.color||'#777777',1),geo:V3.rockGeo&&V3.rockGeo.get(x+','+y),level:0,",
     "else if(a.kind==='wall'&&b.kind==='wall'&&!a.dug&&b.dug){V3.bfx.push({type:'burst',x,y,t:now,col:hexrgb(a.color||'#777777',1),geo:V3.rockGeo&&V3.rockGeo.get(x+','+y),level:b.dug===2?1:0,"),
    # dug 2: the mass from two blocks up over a standing floor block (world-look's v3rockLedge since 09:20), as a recess in the rock (user, 08:58:
    # "the top block still visible stays if the top one is mined first")
    ("if(K.kind==='wall'&&K.blocks&&K.dug===1&&!fill&&V3.models){const G=v3cutRock(g,T,kindAt,i,j,X,Y,Z,K,1,true);if(yo===0)V3.rockGeo.set(tx+','+ty,G)}",
     "if(K.kind==='wall'&&K.blocks&&K.dug===1&&!fill&&V3.models){const G=v3cutRock(g,T,kindAt,i,j,X,Y,Z,K,1,true);if(yo===0)V3.rockGeo.set(tx+','+ty,G)}\n  else if(K.kind==='wall'&&K.blocks&&K.dug===2&&!fill&&V3.models&&typeof v3rockLedge==='function'){const G=v3cutRock(g,T,kindAt,i,j,X,Y,Z,K,2,true);try{G.ledge=v3rockLedge(g,T,kindAt,i,j,X,Y,Z,K,1)}catch(err){console.error(err)}if(yo===0)V3.rockGeo.set(tx+','+ty,G)}   // the block above the floor block out first (rts-feel)"),
    ("for(const [key,e] of V3.work){if(e.broken||e.dmg<=0||e.roof)continue;const g=V3.rockGeo.get(key);if(!g)continue;",
     "for(const [key,e] of V3.work){if(e.broken||e.dmg<=0||e.roof)continue;const g0=V3.rockGeo.get(key);if(!g0)continue;const g=g0.ledge&&e.lvl!==1?g0.ledge:g0;"),
    # smooth walking (rts-feel 2026-10-23): a tile's glide lasts the unit's real step (move3D's 5th field, kept as t.gap by my
    # block), not the time since the page last saw it move, which jittered with the pushes
    ("else{k.fx=k.dx;k.fy=k.dy;k.tx=t.x;k.ty=t.y;k.dur=Math.max(0.12,Math.min(0.7,now-k.last))}",
     "else{k.fx=k.dx;k.fy=k.dy;k.tx=t.x;k.ty=t.y;k.dur=t.gap>0?Math.max(0.12,Math.min(1.5,t.gap/1000)):Math.max(0.12,Math.min(0.7,now-k.last))}"),
]
START = '<script>\n/* RTS feel (overnight polish 2026-10-22, rts-feel)'
END_TAG = '</script>\n'


def patch(html, module):
    for old, new in HOOKS:
        if new in html:
            continue
        n = html.count(old)
        if n != 1:
            raise SystemExit(f'hook anchor found {n} times: {old[:60]!r}')
        html = html.replace(old, new)
    if START in html:
        i = html.index(START)
        j = html.index(END_TAG, i) + len(END_TAG)
        html = html[:i] + module + html[j:]
    else:
        # before the page's last script (the one that asks for the first model: nothing after it ever runs)
        k = '<script>\n// The browser requests its first model only after every script'
        if html.count(k) != 1:
            raise SystemExit('the ready script was not found once')
        html = html.replace(k, module + k)
    return html


if __name__ == '__main__':
    page, mod = Path(sys.argv[1]), Path(sys.argv[2])
    module = mod.read_text(encoding='utf-8')
    if not module.endswith('\n'):
        module += '\n'
    assert module.startswith(START), 'module must start with its marker'
    page.write_text(patch(page.read_text(encoding='utf-8'), module), encoding='utf-8')
    print('patched', page)
