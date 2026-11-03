<script>
/* RTS feel (overnight polish 2026-10-22, rts-feel): every input is answered on the next frame, before the server.
   - A click that orders the selected units drops a ping where the order lands (green move, red attack, amber dig and
     chop, blue pick up and use, violet patrol) and flashes its target; a Shift-queued order draws its waypoint line now.
   - What a click would act on gets a ring under it, and the pointer turns into a sword, pick, axe or hand.
   - Selection rings change at once (click, Shift-click, box); double-click, Ctrl- or Cmd-click on one of yours selects
     every one of that race on screen.
   - Digits run the control groups while the HUD page has the keyboard (the game window's skin.dmf macros cover the
     rest): a digit recalls, Ctrl+digit saves, Shift+digit adds, a second tap jumps the camera there. Backspace goes
     to the last alert.
   - Camera: edge scroll, held-key panning (the arrow keys also when the game window has the keyboard), eased wheel
     zoom, Z to the selection, and a local minimap (about 160 tiles round the camera) to press or drag; right-click on
     it sends the selected units there (in Attack mode a click there attack-moves).
   Sounds go to the audio module when it is there (audio.js): rmSfx.order(kind,{x,y,queued}) for each order, the moment
   it is clicked, and rmSfx(name) for select, group-set, group-recall and deny. */
'use strict';
const RF={camSent:[],pings:[],flashes:[],pend:[],hv:null,hvAt:0,mouse:null,over:false,moved:true,cur:'',keys:new Set(),zoomTo:null,edgeAt:0,inWin:false,tap:{n:0,at:0},jump:null,opt:null,hudAt:0,last:null,lat:[],latFr:[],ack:[],panV:0,lt:0,fr:0};
const RF_COL={move:[0.42,0.95,0.48,1],attack:[1,0.3,0.22,1],capture:[0.82,0.6,1,1],patrol:[0.75,0.55,1,1],mine:[1,0.72,0.26,1],chop:[1,0.72,0.26,1],pick:[0.5,0.85,1,1],use:[0.5,0.78,1,1],select:[1,0.88,0.42,1],fish:[0.45,0.86,1,1]};
// The game's own verdict for the spot under the pointer (HoverCheck.dm) by its order kind.
const RF_HV={'Attack':'attack','Knock out':'attack','Capture':'capture','Tame':'capture','Mine':'mine','Chop':'chop','Pick up':'pick','Move':'move','Fish':'fish','Dig down':'mine'};
// The Gather switch (Gather.dm): on, a click on rock mines, on a tree chops, on a fishing spot fishes; off, they walk.
// A menu order (work3d / walk3d) says which while its instant answer is drawn (RF.force).
function rfGather(){return RF.force?RF.force==='on':!!(model&&model.gather)}
function rfOnTop(){return arr(model&&model.units).some(u=>u.selected&&u.z===3)}
function rfSfx(n,o){try{if(typeof window.rmSfx==='function')window.rmSfx(n,o||{})}catch(e){}}
function rfOrderSfx(k,x,y,queued){try{const S=window.rmSfx;if(S&&typeof S.order==='function')S.order({capture:'attack',pick:'gather',fish:'gather'}[k]||k,{x,y,queued:!!queued})}catch(e){}}
function rfSelected(){return arr(model&&model.units).some(u=>u.selected)}
function rfEase(q){q=Math.max(0,Math.min(1,q));return 1-(1-q)*(1-q)*(1-q)}
function rfLit(c,k){return [Math.min(1,c[0]*k),Math.min(1,c[1]*k),Math.min(1,c[2]*k),1]}
// What a left click on thing t or tile would do now: the choices client/Click and RemasterMapOrder (QoL.dm) make,
// with the game's verdict for that spot when it has one.
function rfPredict(t,tile){if(!tile||!V3.on||V3.shop||V3.build||V3.aim||!model||model.useon||model.mode)return null;
 if(model.patrol)return 'patrol';
 if(model.attackMode&&rfSelected())return t&&t.kind==='mine'?null:'attack';   // Attack mode: the next click picks a foe or an attack-move spot
 if(t&&t.kind==='mine')return 'select';
 if(!rfSelected())return t&&t.kind==='station'?'use':null;
 if(t&&t.kind==='station')return 'use';
 if(t&&t.fishspot&&rfGather())return 'fish';   // a fishing spot: the selected fish it from the shore (QoL.dm, Fishing.dm)
 const hv=model.hover;if(!RF.force&&hv&&hv.x===tile.x&&hv.y===tile.y&&(hv.on==='thing')===!!t&&(hv.g==null||!!hv.g===!!model.gather)){if(hv.bad&&!hv.ok)return null;const k=RF_HV[hv.kind];if(k){if(hv.kind==='Dig down')tile.top=true;return k}}   /* nobody can (someone else's, no stairs, nothing there): no order */
 if(t){if(t.kind==='npc'&&!t.peace||t.kind==='player'&&t.war||t.kind==='animal'&&!t.ko)return 'attack';if(t.kind==='item'&&!t.m3)return 'pick'}   // an animal: walk up and hunt it (the menu's Hunt / attack; the game's verdict says Attack)
 if(tile.far)return 'move';   /* rock that isn't a green block (in reach): a click walks there (v3pickTile) */
 const G=rfGather();if(tile.roof)return G?'mine':'move';
 const K=v3kindAt(tile.x,tile.y);if(K&&K.slope)return 'move';   /* a ramp is a way: walk it (mine it from the menu) */if(G&&tile.up&&tile.peak&&rfOnTop()){tile.top=true;return 'mine'}   /* units up on a mountain dig its top down (Gather.dm) */
 if(K&&K.kind==='tree')return G?'chop':'move';if(K&&K.kind==='wall')return G?'mine':'move';return 'move'}   /* a ridge top too: nobody selected can get up there, so the game digs its face (View3D.dm Remaster3DTarget) */
// The verb for the pointer's tag while the game's verdict is on its way (v3hover): what a click there would do.
function rfLocalVerb(t){const H=RF.hv;if(!H||!rfSelected()||H.t!==(t||null))return null;if(!t&&H.tile&&H.tile.far)return 'Walk there · only the green blocks are in reach';return {attack:H.t&&H.t.kind==='animal'?'Hunt':'Attack',capture:'Capture',mine:'Mine',chop:'Chop',pick:'Pick up',patrol:'Patrol point',use:'Open',fish:'Fish'}[H.k]||null}
function rfY(x,y,up){const K=v3kindAt(x,y);if(up)return K&&(K.kind==='wall'||K.roof)&&typeof v3peakTop==='function'?v3peakTop(x,y)+0.04:V3.STOREY+0.44;   /* on a mountain: the top of the block there */if(K&&K.kind==='wall'){/* on the rock's top as drawn: a tall rock hid an outline drawn 1.2 up (r12) */let pk=typeof v3peakTop==='function'?v3peakTop(x,y):0;if(pk>0.3&&typeof v3mcutTile==='function'&&v3mcutTile(x,y))pk=Math.min(pk,v3mcutLim(x,y));return Math.max(pk>0.3?pk:1.2,v3groundAt(x,y))+0.04}return v3groundAt(x,y)+0.05}
function rfThingY(t){return (t.ly||0)+(t.ly?0:v3groundAt(t.dx,t.dy))+0.05}
function rfRing(a,X,Y,Z,r,w,c,n){n=n||28;for(let k=0;k<n;k++){const a0=k/n*6.283,a1=(k+1)/n*6.283,c0=Math.cos(a0),s0=Math.sin(a0),c1=Math.cos(a1),s1=Math.sin(a1),q=r-w;quad(a,[X+c0*r,Y,Z+s0*r],[X+c1*r,Y,Z+s1*r],[X+c1*q,Y,Z+s1*q],[X+c0*q,Y,Z+s0*q],[0,0,0],c)}}
function rfSquare(a,X,Y,Z,h,w,c){const e=(x0,z0,x1,z1,x2,z2,x3,z3)=>quad(a,[x0,Y,z0],[x1,Y,z1],[x2,Y,z2],[x3,Y,z3],[0,0,0],c);
 e(X-h,Z+h,X+h,Z+h,X+h-w,Z+h-w,X-h+w,Z+h-w);e(X+h,Z+h,X+h,Z-h,X+h-w,Z-h+w,X+h-w,Z+h-w);e(X+h,Z-h,X-h,Z-h,X-h+w,Z-h+w,X+h-w,Z-h+w);e(X-h,Z-h,X-h,Z+h,X-h+w,Z+h-w,X-h+w,Z-h+w)}
// A line over the ground (following its height), for waypoints not yet confirmed by the game.
// The tile a work click really works (the game's Remaster3DTarget): the game's verdict for the hovered tile names it
// (tx, ty: a ridge top becomes the face block below it); before the verdict arrives, a ridge top means the face block
// towards the nearest selected unit, as the game's RemasterRockFaceToward picks it.
function rfWorkTile(t,tile,k){if(t||!tile)return tile;const hv=model&&model.hover;if(hv&&hv.x===tile.x&&hv.y===tile.y&&hv.on==='tile'&&hv.tx!=null)return {x:hv.tx,y:hv.ty};if(k==='mine'&&tile.up&&!tile.top)return rfFaceToward(tile.x,tile.y);return tile}
function rfFaceToward(x,y){const S=V3.things.filter(t=>t.kind==='mine'&&t.selected&&t.dx!=null);if(!S.length)return {x,y};let u=S[0];for(const t of S)if(Math.hypot(t.x-x,t.y-y)<Math.hypot(u.x-x,u.y-y))u=t;
 const rock=(i,j)=>{const K=v3kindAt(i,j);return !!K&&(K.kind==='wall'||K.kind==='block')},open=(i,j)=>{const K=v3kindAt(i,j);return !!K&&!['wall','block','built','tree','void'].includes(K.kind)};
 let cx=x,cy=y;for(let n=0;n<8&&rock(cx,cy);n++){for(let i=-1;i<=1;i++)for(let j=-1;j<=1;j++)if((i||j)&&open(cx+i,cy+j))return {x:cx,y:cy};const sx=Math.sign(u.x-cx),sy=Math.sign(u.y-cy);if(!sx&&!sy)break;cx+=sx;cy+=sy}return {x,y}}
// The block a dig will break, outlined on the rock's faces as its cracks are drawn (v3drawWork / v3crackGeo): blocks go
// bottom first, then on a notch the one above, on the faces towards the camera; pointed higher up the face (blk 2 and up),
// the band from the lowest block left up to that one, which all break (Gather.dm). A face turned away (or edge-on) gets a
// small arrow on the ground in front of it instead. False when the 3D view has no rock faces for the tile.
// On the surface's stacked rock (v3rockStack) the outline is block blk's own faces, the ones towards the camera, and its
// top where it shows; 'top' outlines the column's top block from above (a Dig down).
function rfStackMark(a,g,x,y,c,w,blk){const K=v3kindAt(x,y);if(!K)return false;let k=blk;
 if(blk==='top'){k=-1;for(const q in g.L)k=Math.max(k,+q)}else if(blk==null)k=K.kind==='wall'?(K.dug===1?1:0):(K.ceil||2);
 const F=g.L[k];if(!F)return false;const z=[0,0,0],fw=[-Math.sin(V3.yaw),-Math.cos(V3.yaw)],o=0.04,ring=(pts,m,n)=>{for(let e=0;e<pts.length;e++){const p=pts[e],q=pts[(e+1)%pts.length],t=Math.min(0.45,w/0.5),
   lift=P=>[P[0]+n[0]*o,P[1]+n[1]*o,P[2]+n[2]*o],pi=[p[0]+(m[0]-p[0])*t,p[1]+(m[1]-p[1])*t,p[2]+(m[2]-p[2])*t],qi=[q[0]+(m[0]-q[0])*t,q[1]+(m[1]-q[1])*t,q[2]+(m[2]-q[2])*t];quad(a,lift(p),lift(q),lift(qi),lift(pi),z,c)}};
 let shown=0;if(blk!=='top')for(const f of F)if(f.n[0]*fw[0]+f.n[2]*fw[1]<-0.05){shown++;ring([f.a,f.b,f.c,f.d],f.m,f.n)}
 if(F.top){shown++;ring([F.top.sw,F.top.se,F.top.ne,F.top.nw],F.top.m,[0,1,0])}
 return shown>0}
function rfMineMark(a,x,y,c,w,blk){let g=V3.rockGeo&&V3.rockGeo.get(x+','+y);if(g&&g.stack)return rfStackMark(a,g,x,y,c,w,blk);if(blk==='top')return false;if(g&&g.ledge&&!(blk>=1))g=g.ledge;if(!g||!Array.isArray(g.s)||!g.s.length||typeof v3rockFace!=='function')return false;
 const lvl=g.blocks?(blk===0||blk===1?blk:blk>=2?Math.max(g.cut||0,rfAutoBlock(x,y)):g.cut&&!rfIsWall(x,y)?g.cut:rfAutoBlock(x,y)):-1,hi=blk>=2?blk:lvl,z=[0,0,0],fw=[-Math.sin(V3.yaw),-Math.cos(V3.yaw)];let shown=0;
 for(let i=0;i<g.s.length;i++){const R=v3rockFace(g,i),H=Math.max(1,R.size),v0=lvl>=0?Math.min(0.9,Math.max(0,(lvl-(g.cut||0))/H)):0,v1=lvl>=0?Math.min(1,Math.max(v0+0.5/H,(hi+1-(g.cut||0))/H)):1,n=R.n,o=0.035,
   P=(u,v)=>{const q=R.P(u,v0+v*(v1-v0));return [q[0]+n[0]*o,q[1]+n[1]*o,q[2]+n[2]*o]},du=Math.min(0.2,w),dv=Math.min(0.3,w/Math.max(0.2,(v1-v0)*H));
  if(n[0]*fw[0]+n[2]*fw[1]<-0.05){shown++;   /* a face towards the camera: its outline (one seen edge-on drew a thin line up the rock's corner) */
   quad(a,P(0,0),P(1,0),P(1,dv),P(0,dv),z,c);quad(a,P(0,1-dv),P(1,1-dv),P(1,1),P(0,1),z,c);quad(a,P(0,0),P(du,0),P(du,1),P(0,1),z,c);quad(a,P(1-du,0),P(1,0),P(1,1),P(1-du,1),z,c);continue}
  const b=R.P(0.5,0),px=-n[2],pz=n[0],at=(d,s)=>{const X=b[0]+n[0]*d+px*s,Z=b[2]+n[2]*d+pz*s;return [X,v3groundAt(X,-Z)+0.045,Z]};tri(a,at(0.14,0),at(0.5,-0.17),at(0.5,0.17),z,c)}
 return true}
// The order queue's outline of a dig (the main script's order lines, v3frame): the block that will break, on the rock's
// faces (rfMineMark), and where the line to it ends: the foot of the face nearest the line's start (world X, Z). Null for
// anything else, or rock the 3D view has no faces for: the old square is drawn then.
function rfQueueDig(a,t,c,px,pz){if(!/mine|dig/i.test(t.kind||'')||/roof/i.test(t.kind||'')&&t.blk==null)return null;const g0=V3.rockGeo&&V3.rockGeo.get(t.x+','+t.y),g=g0&&g0.ledge?g0.ledge:g0;if(!g||!Array.isArray(g.s)||!g.s.length&&!g.stack)return null;
 if(!rfMineMark(a,t.x,t.y,c,0.045,/dig down/i.test(t.kind||'')?'top':t.blk))return null;if(!g.s.length)return [t.x,-t.y];let best=null,bd=1e9;for(let i=0;i<g.s.length;i++){const R=v3rockFace(g,i),b=R.P(0.5,0),f=[b[0]+R.n[0]*0.45,b[2]+R.n[2]*0.45],d=px==null?i:Math.hypot(f[0]-px,f[1]-pz);if(d<bd){bd=d;best=f}}return best}
// Which block of a rock column the pointer is on (0 the floor block, 1 the one above, 2 and up higher on the face, where
// a click mines on up to it: Gather.dm): where the pointer's ray enters the tile's column, from the rock's base (a block
// is one unit tall); of the two outside blocks, one already out gives the other. On a tunnel's roof, the roof block.
// Null for anything else (a ridge top, no rock faces): the game then takes the floor block first. The game gets it with the click and the hover (6th field; View3D.dm Remaster3DBlock).
function rfPointBlock(x,y,sx,sy){if(V3.reach&&sx!=null&&typeof v3pickTile==='function'){const C=RF.ghostAt;let q;if(C&&C.sx===sx&&C.sy===sy&&C.fr===RF.fr)q=C.q;else{q=v3pickTile(sx,sy);RF.ghostAt={sx,sy,fr:RF.fr,q}}if(q&&q.ghost&&q.x===x&&q.y===y)return q.blk}   /* cut away or faded, in reach: the block picked */
 const K=v3kindAt(x,y),g=V3.rockGeo&&V3.rockGeo.get(x+','+y),roof=!!(K&&K.roof&&K.kind!=='wall');if(!K||!roof&&(K.kind!=='wall'||!K.blocks)||!g||!V3.inv||sx==null)return null;
 const c=$('world3d'),nx=sx/c.clientWidth*2-1,ny=1-sy/c.clientHeight*2,m=V3.inv,un=(X,Y,Z)=>{const a=X*m[0]+Y*m[4]+Z*m[8]+m[12],b=X*m[1]+Y*m[5]+Z*m[9]+m[13],d=X*m[2]+Y*m[6]+Z*m[10]+m[14],w=X*m[3]+Y*m[7]+Z*m[11]+m[15];return [a/w,b/w,d/w]};
 const A=un(nx,ny,-1),B=un(nx,ny,1);let t0=0,t1=1;for(const [i,lo,hi] of [[0,x-0.5,x+0.5],[2,-y-0.5,-y+0.5]]){const d=B[i]-A[i];if(Math.abs(d)<1e-9){if(A[i]<lo||A[i]>hi)return null;continue}let u=(lo-A[i])/d,v=(hi-A[i])/d;if(u>v)[u,v]=[v,u];t0=Math.max(t0,u);t1=Math.min(t1,v)}
 if(t0>t1)return null;const yIn=A[1]+(B[1]-A[1])*t0,base=g.Y-(g.cut||0);let b=Math.max(0,Math.floor(yIn-base));
 if(g.stack){const n=Math.max(4,Math.ceil((t1-t0)*Math.hypot(B[0]-A[0],B[1]-A[1],B[2]-A[2])/0.04)),H=typeof v3stackTop==='function'?v3stackTop(K):K.blocks,lim=typeof v3mcutTile==='function'&&v3mcutTile(x,y)?v3mcutLim(x,y):1e9;for(let s2=0;s2<=n;s2++){const t=t0+(t1-t0)*s2/n,yy=A[1]+(B[1]-A[1])*t;if(yy>lim)continue;const k=Math.floor(yy-g.Y);if(k>=0&&k<H&&v3stackHas(K,k))return k}return null}   /* above the cutaway nothing shows: the first block under it */
 if(roof){const c0=K.ceil||2;return Math.min(Math.max(b,c0),c0+K.roof-1)}b=Math.min(b,K.blocks-1);if(b<=1){if(K.dug===1)return 1;if(K.dug===2)return 0}return b}
function rfIsWall(x,y){const K=v3kindAt(x,y);return !!K&&K.kind==='wall'}
// A 3D click or hover on a rock column carries the block the pointer is on, as a 6th field (View3D.dm Remaster3DBlock):
// from the pointer over the 3D view, or, for an order picked from the right-click menu, where that menu was opened.
function rfWithBlock(a,v){if(a==='mineroof'&&V3.on){const p=String(v).split('|'),pt=RF.over||!RF.menuAt?RF.mouse:RF.menuAt,b=p.length===3&&pt?rfPointBlock(+p[0],+p[1],pt.x,pt.y):null;if(b!=null)p.push(String(b));return p.join('|')}
 if((a!=='click3d'&&a!=='hover3d'&&a!=='work3d'&&a!=='walk3d')||!V3.on)return v;const p=String(v).split('|');
 // up on a mountain, a dug-out floor inside it (v3pickTile lvl): the height it is at, as the 6th field (View3D.dm, Gather.dm)
 if(p.length===5&&p[4]==='1'&&!(p[2]||'')){const pt=RF.over||!RF.menuAt?RF.mouse:RF.menuAt,q=pt&&typeof v3pickTile==='function'?v3pickTile(pt.x,pt.y):null;if(q&&q.lvl&&q.x===+p[0]&&q.y===+p[1])p.push(String(q.lvl));return p.join('|')}
 if(p.length<2||(p[2]||'')||p[4]==='1'||p.length>=6)return v;
 const pt=RF.over||!RF.menuAt?RF.mouse:RF.menuAt,b=pt?rfPointBlock(+p[0],+p[1],pt.x,pt.y):null;if(b==null)return v;while(p.length<5)p.push('0');p.push(String(b));return p.join('|')}
// A click on rock that isn't one of the green blocks in reach (v3pickTile's far): sent as a walk there (HUD.dm walk3d).
function rfFarClick(v){if(!V3.on||!V3.reach)return false;const p=String(v).split('|');if(p.length<2||(p[2]||''))return false;const pt=RF.over||!RF.menuAt?RF.mouse:RF.menuAt,q=pt?v3pickTile(pt.x,pt.y):null;return !!(q&&q.far&&q.x===+p[0]&&q.y===+p[1])}
// The block a dig takes when nobody chose one: the floor block unless it is out.
function rfAutoBlock(x,y){const K=v3kindAt(x,y);return K&&K.dug===1?1:0}
function rfLine(a,x0,y0,x1,y1,w,c,dash){const l=Math.hypot(x1-x0,y1-y0);if(l<0.05)return;const n=Math.max(1,Math.ceil(l/0.45)),nx=-(y1-y0)/l*w,nz=-(x1-x0)/l*w;
 for(let i=0;i<n;i++){if(dash&&i%2)continue;const f0=i/n,f1=(i+1)/n,ax=x0+(x1-x0)*f0,ay=y0+(y1-y0)*f0,bx=x0+(x1-x0)*f1,by=y0+(y1-y0)*f1,ha=v3groundAt(Math.round(ax),Math.round(ay))+0.06,hb=v3groundAt(Math.round(bx),Math.round(by))+0.06;
  quad(a,[ax+nx,ha,-ay+nz],[bx+nx,hb,-by+nz],[bx-nx,hb,-by-nz],[ax-nx,ha,-ay-nz],[0,0,0],c)}}
// The instant answer to a click on the 3D view (v3wire's mouseup calls it just before it sends the click). Returns
// true when it handled the click itself (Ctrl/Cmd-click on one of yours: all of that race on screen).
function rfClick(e,t,tile){const now=performance.now();RF.fxAt=now;
 if(t&&t.kind==='mine'&&(e.ctrlKey||e.metaKey)&&!V3.build&&!V3.shop){rfSelectAlike(t,e.shiftKey);return true}
 const k=rfPredict(t,tile);rfCursor(k);RF.last={at:now,fr:RF.fr,k,x:tile.x,y:tile.y,sx:e.clientX!=null?Math.round(mx(e)):null,sy:e.clientY!=null?Math.round(my(e)):null,thing:t?t.key:null,cur:RF.cur,drawn:0,shift:!!e.shiftKey};
 if(!k){const hv=model&&model.hover;if(rfSelected()&&hv&&hv.x===tile.x&&hv.y===tile.y&&hv.bad&&!hv.ok&&!model.mode&&!V3.build&&!V3.shop){RF.pings.push({x:tile.x,y:tile.y,k:'deny',at:now,up:!!tile.up});rfSfx('deny')}return false}   // the game said no one can: a small red cross
 if(k==='select'){rfOptSelect([t.ref],e.shiftKey||model.multi?'toggle':'only');RF.flashes.push({key:t.key,k,at:now});rfSfx('select');return false}
 const W=rfWorkTile(t,tile,k),blk=k==='mine'&&!t&&!tile.up&&W.x===tile.x&&W.y===tile.y&&e.clientX!=null?rfPointBlock(tile.x,tile.y,mx(e),my(e)):null;if(k!=='use')RF.pings.push({x:tile.x,y:tile.y,k,at:now,up:!!tile.up,lvl:tile.lvl||0,thing:!!t,tx:W.x,ty:W.y,blk,top:!!tile.top});if(t&&t.key&&k!=='move')RF.flashes.push({key:t.key,k,at:now});
 if((e.shiftKey||model&&model.queue)&&k!=='use')RF.pend.push({x:W.x,y:W.y,k,at:now,blk,top:!!tile.top});
 if(RF.pings.length>12)RF.pings.shift();if(k!=='use')rfOrderSfx(k,tile.x,tile.y,e.shiftKey);return false}
// Right-click as in StarCraft, when chosen in Settings: with units selected, a right-click on ground, a foe, rock, a
// tree or an item gives the same order a left-click would; on one of yours, a workshop or with Alt/Ctrl held it opens
// the menu as before. Off by default (the game's right-click is the menu).
function rfRightOrders(){try{return localStorage.getItem('rm-rclick')==='orders'}catch(e){return false}}
function rfRightClick(e){if(model&&model.attackMode&&!e.altKey&&!e.ctrlKey&&!e.metaKey&&!(RF.last&&performance.now()-RF.last.at<500)){send('attackmode','');return true}   /* A, then a right-click: leaves attack mode (StarCraft), as it lets an aim or a held item go */
 if(!RF.rclick||e.altKey||e.ctrlKey||e.metaKey||!V3.on||!rfSelected())return false;const t=v3pickThing(mx(e),my(e)),tile=t?{x:t.x,y:t.y}:v3pickTile(mx(e),my(e));if(!tile||t&&t.kind==='mine')return false;
 const k=rfPredict(t,tile);if(!['move','attack','capture','mine','chop','pick','patrol','fish'].includes(k))return false;rfClick(e,t,tile);
 if(!t&&tile.roof&&rfGather())send('mineroof',tile.x+'|'+tile.y+'|'+(e.shiftKey?'1':'0'));else send('click3d',tile.x+'|'+tile.y+'|'+(t?(t.ref||t.id||''):'')+'|'+(e.shiftKey?'1':'0')+'|'+(tile.up?'1':'0'));return true}
// Orders chosen from the right-click menu (anything that sends a 3D click without going through rfClick) get the
// same instant answer. And no command is lost: a command is a navigation (byond://), and WebKit drops the first of two
// navigations made in the same task (measured in the game: of send(a);send(b) only b arrived), so a second command in
// the same task waits for the next one.
if(typeof send==='function'){const send0=send,Q=[];let busy=false;const flush=()=>{const n=Q.shift();if(!n){busy=false;return}send0(n[0],n[1]);setTimeout(flush,0)};
 send=function(a,v){try{if(a==='click3d'&&rfFarClick(v))a='walk3d'}catch(e){}try{v=rfWithBlock(a,v)}catch(e){}
 try{if(a==='camera'){const p=String(v).split(',');RF.camSent.push([+p[0],+p[1],performance.now()]);if(RF.camSent.length>60)RF.camSent.shift()}}catch(e){}try{if((a==='click3d'||a==='mineroof'||a==='work3d'||a==='walk3d')&&V3.on&&performance.now()-(RF.fxAt||0)>8){const p=String(v).split('|'),x=+p[0],y=+p[1],c3=a!=='mineroof';
  if(isFinite(x)&&isFinite(y)){const t=c3&&p[2]?V3.things.find(o=>(o.ref||o.id)===p[2])||null:null,K=v3kindAt(x,y);RF.force=a==='work3d'?'on':a==='walk3d'?'off':null;try{rfClick({shiftKey:(a==='mineroof'?p[2]:p[3])==='1'},t,{x,y,up:c3&&p[4]==='1',peak:c3&&p[4]==='1'&&!!(K&&K.kind==='wall'&&K.blocks),roof:a==='mineroof',lvl:c3&&p[4]==='1'&&p[5]?+p[5]:0})}finally{RF.force=null}}}}catch(e){console.error(e)}if(busy){Q.push([a,v]);return}busy=true;send0(a,v);setTimeout(flush,0)}}
// A drag box that caught none of yours. A short one (under 16 screen px each way) was a click with a shaky hand: it does
// what that click would have. A bigger one leaves the selection as it was, as in StarCraft (it used to clear it).
function rfEmptyBox(e,d){const z=hudKC(),w=Math.abs(mx(e)-d.x)*z,h=Math.abs(my(e)-d.y)*z;
 if(w<16&&h<16){const t=v3pickThing(d.x,d.y),tile=t?{x:t.x,y:t.y}:v3pickTile(d.x,d.y);if(!tile)return true;const ev={shiftKey:e.shiftKey,ctrlKey:e.ctrlKey,metaKey:e.metaKey,clientX:d.x*z,clientY:d.y*z};
  if(rfClick(ev,t,tile))return true;if(!t&&tile.roof&&rfSelected()&&rfGather())send('mineroof',tile.x+'|'+tile.y+'|'+(e.shiftKey?'1':'0'));else send('click3d',tile.x+'|'+tile.y+'|'+(t?(t.ref||t.id||''):'')+'|'+(e.shiftKey?'1':'0')+'|'+(tile.up?'1':'0'));return true}
 return rfSelected()}
// With the right-click menu (the default): a second right-click on the same spot while its menu is open runs the menu's
// main action (the highlighted one), so a quick double right-click attacks, moves or gathers, as a StarCraft player
// expects; anywhere else it opens a new menu as before.
if(typeof v3menuOpen==='function'){const open0=v3menuOpen;v3menuOpen=function(x,y){RF.menuAt={x,y};const r=open0(x,y);try{const m=$('menu3d'),b=m&&!m.hidden&&m.querySelector('.ic-act.primary');if(b&&!m.querySelector('.rf-again')){const h=document.createElement('div');h.className='rf-again';h.style.cssText='margin:6px 2px 0;font-size:11px;color:var(--muted,#a59d88);text-align:right';h.textContent='Right-click again: '+(b.querySelector('span')||b).textContent;m.append(h)}}catch(e){}return r}}
addEventListener('mousedown',e=>{if(e.button!==2||e.target!==$('world3d')||$('menu3d').hidden||!RF.menuAt||Math.hypot(mx(e)-RF.menuAt.x,my(e)-RF.menuAt.y)*hudKC()>14)return;const b=$('menu3d').querySelector('.ic-act.primary');if(!b)return;e.preventDefault();e.stopPropagation();RF.menuAt=null;b.click()},true);
// A box drawn round some of yours: their rings turn at once.
function rfBoxFx(refs,add){rfOptSelect(refs,add?'add':'only');const now=performance.now();for(const r of refs)RF.flashes.push({key:r,k:'select',at:now});RF.last={at:now,fr:RF.fr,k:'select',drawn:0};rfSfx('select')}
// Every one of yours of t's race that is drawn on screen (as the map's double-click does for its view).
function rfSelectAlike(t,add){const U=arr(model&&model.units),race=(U.find(u=>u.ref===t.ref)||{}).race;if(!race)return false;const c=$('world3d'),W=c.clientWidth,H=c.clientHeight;
 const refs=V3.things.filter(u=>u.kind==='mine'&&u.ref&&u.dx!=null&&v3visible(u)&&(U.find(x=>x.ref===u.ref)||{}).race===race).filter(u=>{const p=v3project([u.dx,0.55+v3groundAt(u.dx,u.dy),-u.dy]);return p&&p[0]>=0&&p[0]<=W&&p[1]>=0&&p[1]<=H}).map(u=>u.ref);
 if(!refs.length)return false;send('boxrefs',refs.join(',')+'|'+(add?'1':'0'));rfBoxFx(refs,add);return true}
// A click anywhere on a person's body picks them: the map's pick looks 26 px round the middle of the picture, so zoomed in
// close a click on the feet or the head (a picture 150 px tall) was a move order. When that finds nobody (or only a
// workshop further off), the nearest person whose picture, foot to head, passes the click; overlapping, the one in front.
if(typeof v3pickThing==='function'){const pk0=v3pickThing;v3pickThing=function(mx,my){const r0=pk0(mx,my);if(r0&&r0.kind!=='station')return r0;let best=null,bd=1e9,front=-1;
 const L=V3.lean||[0,1,0];for(const t of V3.things){if(t.dx==null||t.ly||t.nopick||t.beast||!['mine','npc','animal','player'].includes(t.kind)||!v3visible(t))continue;
  const g=v3groundAt(t.dx,t.dy),H=(t.ih||1)*(t.model&&V3.unitModels?1:(t.sc||1))*0.9,a=v3project([t.dx,g+0.08,-t.dy]),b=v3project([t.dx+L[0]*H,g+0.08+L[1]*H,-t.dy+L[2]*H]);if(!a||!b)continue;
  const vx=b[0]-a[0],vy=b[1]-a[1],ll=vx*vx+vy*vy,q=ll?Math.max(0,Math.min(1,((mx-a[0])*vx+(my-a[1])*vy)/ll)):0,d=Math.hypot(mx-a[0]-q*vx,my-a[1]-q*vy),r=Math.max(12,Math.min(30,Math.sqrt(ll)*0.18));
  if(d>=r)continue;if(d<r*0.6?a[1]>front:(front<0&&d<bd)){best=t;bd=d;if(d<r*0.6)front=a[1]}}
 return best||r0}}
// Box select takes yours whose body, foot to head, the box touches (it took only the middle of the picture, so a box
// round the feet of a crowd, zoomed in, caught nobody).
if(typeof v3boxRefs==='function')v3boxRefs=function(x0,y0,x1,y1){const c=$('world3d'),r=c.getBoundingClientRect(),l=Math.min(x0,x1)-r.left,h=Math.max(x0,x1)-r.left,tp=Math.min(y0,y1)-r.top,b=Math.max(y0,y1)-r.top,L=V3.lean||[0,1,0];
 return V3.things.filter(u=>u.kind==='mine'&&u.ref&&u.dx!=null&&v3visible(u)).filter(u=>{const g=v3groundAt(u.dx,u.dy),H=(u.ih||1)*(u.model&&V3.unitModels?1:(u.sc||1))*0.9;
  const A=v3project([u.dx,g+0.08,-u.dy]),B=v3project([u.dx+L[0]*H,g+0.08+L[1]*H,-u.dy+L[2]*H]);if(!A||!B)return false;
  /* the picture's axis on screen against the box (Liang-Barsky clip) */let t0=0,t1=1;const dx=B[0]-A[0],dy=B[1]-A[1];
  for(const [pp,qq] of [[-dx,A[0]-l],[dx,h-A[0]],[-dy,A[1]-tp],[dy,b-A[1]]]){if(pp===0){if(qq<0)return false}else{const k=qq/pp;if(pp<0){if(k>t1)return false;if(k>t0)t0=k}else{if(k<t0)return false;if(k<t1)t1=k}}}return t0<=t1}).map(u=>u.ref)};
// The top bar's idle count is a button for the next idle unit (as StarCraft II's idle-worker button; F1 does the same).
{const b=$('tbIdle'),r=b&&b.parentElement;if(r){r.title='Idle units (F1)\nClick: select the next idle unit and take the camera to them.';r.style.cursor='pointer';r.setAttribute('role','button');r.tabIndex=-1;
 r.addEventListener('click',e=>{if(e.button!==0)return;e.preventDefault();send('idle','')})}}
// The one-unit card's portrait: a click takes the camera to them (as Z does).
document.addEventListener('click',e=>{const p=e.target&&e.target.closest&&e.target.closest('.hf .pw');if(!p||e.button!==0)return;rfJumpToSelection()});
document.addEventListener('mouseover',e=>{const p=e.target&&e.target.closest&&e.target.closest('.hf .pw');if(p&&!p.title){p.title='Go to them (Z)\nClick: the camera goes to them.';p.style.cursor='pointer'}});
// Double-click on one of yours: the same, on screen; anything else keeps the map's double-click (Actions.dm).
function rfDbl(e){if(!V3.on||V3.build||V3.shop)return false;const t=v3pickThing(mx(e),my(e));return !!(t&&t.kind==='mine'&&rfSelectAlike(t,e.shiftKey))}
// The Company list and a group's faces: pointing at one rings that unit in 3D; a double-click takes the camera to it.
document.addEventListener('mouseover',e=>{const b=e.target.closest&&e.target.closest('button[data-do="select"]');RF.hoverRef=b?b.dataset.value:null},{passive:true});
document.addEventListener('dblclick',e=>{const b=e.target.closest&&e.target.closest('button[data-do="select"]');if(!b||!V3.on)return;const t=V3.things.find(o=>o.ref===b.dataset.value),m=arr(model&&model.units).find(x=>x.ref===b.dataset.value);
 if(t&&t.dx!=null)rfLookAt(t.dx,t.dy);else if(m&&m.z===V3.z)rfLookAt(m.x,m.y)});
// Faces with a modifier, as in StarCraft's selection panel: Shift-click adds or removes that unit; Ctrl/Cmd-click keeps
// only that unit's people from the selection (all of them in the Company list when that people isn't selected).
function rfFace(b,shift){const U=arr(model&&model.units),me=U.find(u=>u.ref===b.dataset.value);if(!me)return false;let refs;
 if(shift){const sel=new Set(U.filter(u=>u.selected).map(u=>u.ref));if(sel.has(me.ref))sel.delete(me.ref);else sel.add(me.ref);refs=[...sel]}
 else{refs=U.filter(u=>u.selected&&u.race===me.race).map(u=>u.ref);if(!refs.length)refs=U.filter(u=>u.race===me.race&&u.z===me.z).map(u=>u.ref)}
 if(!refs.length){send('action','clear');rfOptSelect([],'only');return true}send('selectmany',refs.join('|'));rfOptSelect(refs,'only');rfSfx('select');return true}
addEventListener('click',e=>{const b=e.target.closest&&e.target.closest('button[data-do="select"]');if(!b||!(e.shiftKey||e.ctrlKey||e.metaKey))return;if(rfFace(b,e.shiftKey)){e.preventDefault();e.stopImmediatePropagation()}},true);
// on a Mac a Ctrl-click is a context click (no click event): the same there
addEventListener('contextmenu',e=>{const b=e.target.closest&&e.target.closest('button[data-do="select"]');if(!b||!e.ctrlKey)return;e.preventDefault();e.stopImmediatePropagation();rfFace(b,false)},true);
// Selection drawn ahead of the game: kept until the next HUD update says what was really selected.
function rfOptSelect(refs,mode){RF.opt={refs:new Set(refs),mode,at:performance.now()};RF.tap={n:0,at:0};rfApplyOpt();try{const n=V3.things.filter(t=>t.kind==='mine'&&t.selected).length,a=$('tbSel'),b=$('deselectLabel');if(a)text(a,n);if(b)text(b,'Deselect ('+n+')')}catch(e){}}   // the counters too, until the game's reply sets them
// Control groups at a glance (StarCraft's group tabs): a chip per saved group just above the command bar, with its
// number and size; a click recalls it, a second click (or the digit twice) takes the camera there.
function rfGroupBar(){const host=document.querySelector('.taskmode');if(!host||!model)return;let bar=$('rfGroups');
 if(!bar){bar=document.createElement('div');bar.id='rfGroups';bar.setAttribute('role','group');bar.setAttribute('aria-label','Control groups');bar.style.cssText='position:absolute;left:0;right:0;bottom:100%;margin-bottom:6px;display:flex;justify-content:center;gap:4px;pointer-events:none;z-index:3';if(getComputedStyle(host).position==='static')host.style.position='relative';host.prepend(bar);
  bar.addEventListener('click',e=>{const b=e.target.closest('button[data-rfg]');if(!b)return;const n=+b.dataset.rfg,now=performance.now(),dbl=RF.tap.n===n&&now-RF.tap.at<400;RF.tap={n,at:now};send('controlgroup',n+'|Select|');rfSfx('group-recall');if(dbl)RF.jump={at:now}})}
 const G=arr(model.controlGroups&&model.controlGroups.groups).filter(g=>g.count>0),key=JSON.stringify(G.map(g=>[g.number,g.count,g.names]))+'|'+RF.tap.n;if(bar.dataset.k===key)return;bar.dataset.k=key;bar.replaceChildren();
 for(const g of G){const b=document.createElement('button'),on=RF.tap.n===g.number,names=arr(g.names).map(x=>String(x).replace(/^\{[^}]*\}\s*/,''));b.dataset.rfg=g.number;
  b.style.cssText='pointer-events:auto;min-height:0;min-width:36px;padding:2px 8px;font:600 12px/1.25 -apple-system,sans-serif;border:1px solid '+(on?'var(--gold,#e0bb73)':'rgba(224,187,115,.35)')+';border-radius:5px;background:linear-gradient(#2c2519,#16120b);color:#e8dcc0;box-shadow:0 1px 3px rgba(0,0,0,.65)'+(on?',0 0 6px rgba(242,210,122,.45)':'');
  b.innerHTML='<b style="color:var(--gold,#e0bb73)">'+g.number+'</b> <span style="opacity:.85">\u00d7'+g.count+'</span>';b.title='Group '+g.number+' ('+g.number+')\n'+names.slice(0,6).join(', ')+(names.length>6?'\u2026':'')+'\nClick or press '+g.number+' to select them; twice to go there. Ctrl+'+g.number+' saves the selection as this group, Shift+'+g.number+' adds to it.';b.setAttribute('aria-label','Group '+g.number+', '+g.count+' unit'+(g.count===1?'':'s'));bar.append(b)}}
function rfApplyOpt(){const O=RF.opt;if(!O)return;O.flip=O.flip||new Map();for(const t of V3.things){if(t.kind!=='mine'||!t.ref)continue;const hit=O.refs.has(t.ref);if(O.mode==='only')t.selected=hit?1:0;else if(hit){if(O.mode==='add')t.selected=1;else{if(!O.flip.has(t.ref))O.flip.set(t.ref,t.selected?0:1);t.selected=O.flip.get(t.ref)}}}}
function rfDrawn(L,now){L.drawn=now;L.frames=RF.fr-L.fr;RF.lat.push(Math.round(now-L.at));RF.latFr.push(L.frames);if(RF.lat.length>40){RF.lat.shift();RF.latFr.shift()}}
function rfSyncSel(){if(!model||!Array.isArray(model.units))return;const S=new Map(model.units.map(u=>[u.ref,u.selected?1:0]));for(const t of V3.things)if(t.kind==='mine'&&t.ref&&S.has(t.ref))t.selected=S.get(t.ref)}
if(typeof window.updateHUD==='function'){const hud=window.updateHUD;window.updateHUD=function(raw){hud(raw);try{const now=performance.now();RF.hudAt=now;RF.opt=null;rfSyncSel();
  const L=RF.last;if(L&&!L.acked&&now-L.at<3000&&model){const T=arr(model.targets);if(L.k==='select'||T.some(q=>q.x===L.x&&q.y===L.y)){L.acked=now;RF.ack.push(Math.round(now-L.at));if(RF.ack.length>40)RF.ack.shift()}}
  if(RF.pend.length){const T=arr(model.targets);RF.pend=RF.pend.filter(p=>now-p.at<3000&&!T.some(q=>q.x===p.x&&q.y===p.y))}
  if(RF.jump&&now-RF.jump.at<2000){RF.jump=null;rfJumpToSelection()}   /* the game's answer to a double tap: 2 s, as a busy game can take a second */rfGroupBar()}catch(e){console.error(e)}}}
// The page takes the game's camera spot from each 3D update once a pan is a second old. A busy game can answer late with a
// scene built round an older pan spot, and a fast edge scroll then jumped back ~14 tiles and forward again (real client
// r15). A spot that is one of our own earlier pan positions (not the last one sent) is such an echo: the camera stays.
function rfStaleCam(x,y){const L=RF.camSent,now=performance.now();if(L.length<2)return false;const last=L[L.length-1],near=s=>Math.abs(x-s[0])<0.6&&Math.abs(y-s[1])<0.6;if(now-last[2]>8000||near(last))return false;return L.slice(0,-1).some(s=>now-s[2]<8000&&near(s))}
if(typeof window.update3D==='function'){const u3=window.update3D;window.update3D=function(raw){const px=V3.tcx,py=V3.tcy;u3(raw);try{if((V3.tcx!==px||V3.tcy!==py)&&rfStaleCam(V3.tcx,V3.tcy)){V3.tcx=px;V3.tcy=py}}catch(e){console.error(e)}try{if(RF.opt&&performance.now()-RF.opt.at<1500)rfApplyOpt();else if(RF.hudAt)rfSyncSel()}catch(e){console.error(e)}}}
// Each move3D row carries the unit's last step length in ms (5th field, View3D.dm Remaster3DMovesPush); the frame loop's
// glide lasts that long (a hook), so a walk is one even glide instead of waiting at each tile and rushing to the next.
if(typeof window.move3D==='function'){const mv0=window.move3D;window.move3D=function(raw){mv0(raw);try{const L=JSON.parse(typeof raw==='string'?raw:JSON.stringify(raw));if(!Array.isArray(L))return;const by=new Map();for(const r of L)if(r.length>4)by.set(r[0],r[4]);if(!by.size)return;for(const t of V3.things){const g=by.get(t.ref||t.id);if(g!=null)t.gap=g}}catch(e){}}}
// Drawn with the 3D view's objects each frame (v3frame calls it): pings, target flashes, waypoints not yet confirmed,
// and the ring under whatever a click would act on.
function rfDraw(a){const now=performance.now();RF.fr++;try{rfDraw1(a,now)}finally{const c=performance.now()-now;RF.costDraw=RF.costDraw==null?c:RF.costDraw*0.95+c*0.05}}
// The level a unit of yours stands at, in blocks: up on a mountain its feet (Gather.dm), else 0.
function rfFeet(u){return u.ly>0?(u.feet!=null?u.feet:Math.round(u.ly)):0}
// The blocks your selected units can mine from where they stand (the user, 2026-10-24: "outline only blocks in reach"):
// those of the tiles round each one and its own, from two under its feet to two over them (Gather.dm RM_REACH_*), as
// "x,y,k" keys. Kept for the frame in V3.reach, so picking (v3pickTile) can take one cut away or faded at the pointer.
function rfReach(){const out=new Set();if(!V3.on||V3.z!==1||!rfGather())return out;
 for(const u of V3.things){if(u.kind!=='mine'||!u.selected||u.dx==null)continue;const ux=Math.round(u.dx),uy=Math.round(u.dy),f=rfFeet(u);
  for(let dy=-1;dy<=1;dy++)for(let dx=-1;dx<=1;dx++){const x=ux+dx,y=uy+dy,K=v3kindAt(x,y);if(!K||!(K.kind==='wall'&&K.blocks||K.roof))continue;
   for(let k=Math.max(0,f-2);k<=f+2;k++)if(v3stackHas(K,k))out.add(x+','+y+','+k)}
  if(out.size>400)break}
 return out}
// A block's whole outline (its 12 edges), drawn just inside it as thin strips turned to the eye: hidden in solid rock,
// it shows where the rock is faded at the pointer or cut away over a unit inside the mountain.
function rfBlockBox(a,x,y,k,c,w){const T=V3.terrain,g=V3.rockGeo&&V3.rockGeo.get(x+','+y);if(!T||!g||!g.stack)return false;
 const kindAt=(i,j)=>{if(i<0||j<0||i>=T.w||j>=T.h)return null;const q=T.tiles[j*T.w+i];return q?T.kinds[q-1]:null},E=V3.eye||[0,40,0],Z0=[0,0,0],i=x-T.x0,j=y-T.y0,Y=g.Y||0,P=(ci,cj,kk)=>v3stackPt(T,kindAt,i+ci,j+cj,kk,Y);
 const edge=(p,q)=>{const d0=q[0]-p[0],d1=q[1]-p[1],d2=q[2]-p[2],v0=E[0]-p[0],v1=E[1]-p[1],v2=E[2]-p[2];let s0=d1*v2-d2*v1,s1=d2*v0-d0*v2,s2=d0*v1-d1*v0;const f=w/(Math.hypot(s0,s1,s2)||1);s0*=f;s1*=f;s2*=f;
  quad(a,[p[0]-s0,p[1]-s1,p[2]-s2],[q[0]-s0,q[1]-s1,q[2]-s2],[q[0]+s0,q[1]+s1,q[2]+s2],[p[0]+s0,p[1]+s1,p[2]+s2],Z0,c)};
 const m=[x,Y+k+0.5,-y],ins=p=>[p[0]+(m[0]-p[0])*0.035,p[1]+(m[1]-p[1])*0.035,p[2]+(m[2]-p[2])*0.035],b=[P(0,0,k),P(1,0,k),P(1,1,k),P(0,1,k)].map(ins),t=[P(0,0,k+1),P(1,0,k+1),P(1,1,k+1),P(0,1,k+1)].map(ins);
 for(let e=0;e<4;e++){edge(b[e],b[(e+1)%4]);edge(t[e],t[(e+1)%4]);edge(b[e],t[e])}return true}
// Gather mode: the blocks in reach of your selected units outlined in green (the user, 2026-10-24: "outline the blocks in
// green so we can see what we are mining"; "green during the fade so they can see which blocks are all around them";
// "outline only blocks in reach"): each one's faces you see solid get their outline on the face (rfStackMark), and its
// whole outline shows through the fade and over the cutaway. The one under the pointer is drawn in gold over it (rfDraw1).
function rfGatherLines(a){const R=rfReach();V3.reach=R.size?R:null;if(!R.size||!V3.rockGeo)return;const c=[0.36,0.92,0.42,1],w=0.011;
 for(const key of R){const [x,y,k]=key.split(',').map(Number),g=V3.rockGeo.get(x+','+y);if(!g||!g.stack)continue;const cut=typeof v3mcutTile==='function'&&v3mcutTile(x,y)?v3mcutLim(x,y):1e9;
  if(k<cut&&g.L&&g.L[k])rfStackMark(a,g,x,y,c,w,k);rfBlockBox(a,x,y,k,c,w)}}
// A unit of yours inside the mountain (in a tunnel, or up on it under rock of its own column), selected: a light ring at
// its feet and a marker over its head, and the floors at its level round it lit (the user: "light the floors and the unit
// inside"), so a dug-out level reads through the cutaway, Gather on or off.
function rfInsideLight(a){if(!V3.on||V3.z!==1)return;let n=0;const fill=[0.5,0.46,0.35,1],edge=[0.96,0.88,0.6,1],ring=[1,0.95,0.72,1],rt=[Math.cos(V3.yaw),0,-Math.sin(V3.yaw)],Z0=[0,0,0];
 for(const u of V3.things){if(u.kind!=='mine'||!u.selected||u.dx==null||u.ly<0)continue;const ux=Math.round(u.dx),uy=Math.round(u.dy),K=v3kindAt(ux,uy),f=rfFeet(u);
  const inside=u.ly>0?!!K&&(K.kind==='wall'&&!!K.blocks||!!K.roof)&&Array.from({length:Math.max(0,v3stackTop(K)-f)},(_,q)=>f+q).some(q=>v3stackHas(K,q)):!!K&&!!K.roof&&K.kind!=='wall';if(!inside)continue;
  for(let dy=-3;dy<=3;dy++)for(let dx=-3;dx<=3;dx++){const x=ux+dx,y=uy+dy,N=v3kindAt(x,y);if(!N)continue;
   const floor=f>0?(N.kind==='wall'&&!!N.blocks||!!N.roof)&&v3stackHas(N,f-1)&&!v3stackHas(N,f):!!N.roof&&N.kind!=='wall'&&!v3stackHas(N,0);if(!floor)continue;
   const Y=(f>0?v3feetY(x,y,f):v3groundAt(x,y))+0.025,X=x,Z=-y,h=0.42;quad(a,[X-h,Y,Z+h],[X+h,Y,Z+h],[X+h,Y,Z-h],[X-h,Y,Z-h],Z0,fill);rfSquare(a,X,Y+0.005,Z,0.47,0.035,edge);if(++n>160)return}
  const Y=rfThingY(u)+0.02,X=u.dx,Z=-u.dy;rfRing(a,X,Y,Z,0.44,0.06,ring,32);const hY=Y+1.3,d=0.13;quad(a,[X,hY+0.2,Z],[X+rt[0]*d,hY,Z+rt[2]*d],[X,hY-0.2,Z],[X-rt[0]*d,hY,Z-rt[2]*d],Z0,ring)}}
function rfDraw1(a,now){
 try{rfGatherLines(a)}catch(e){V3.reach=null}
 try{rfInsideLight(a)}catch(e){}
 if(RF.pings.length)RF.pings=RF.pings.filter(p=>!p.drawn||now-p.drawn<720);if(RF.flashes.length)RF.flashes=RF.flashes.filter(f=>!f.drawn||now-f.drawn<660);   // animations run from their first drawn frame: a slow frame never swallows one
 for(const p of RF.pings){if(!p.drawn){p.drawn=now;const L=RF.last;if(L&&!L.drawn&&L.at===p.at)rfDrawn(L,now)}const age=(now-p.drawn)/1000,c=RF_COL[p.k]||RF_COL.move,X=p.x,Z=-p.y,Y=p.lvl&&typeof v3feetY==='function'?v3feetY(p.x,p.y,p.lvl)+0.04:rfY(p.x,p.y,p.up);   /* a dug-out floor inside the mountain: on it (Gather.dm) */
  if(p.k==='deny'){if(age<0.45){const s=0.26*(1-rfEase(age/0.45)*0.5),w=0.045,cr=[0.85,0.22,0.18,1];for(const [ux,uz] of [[1,1],[1,-1]]){const L=s*0.7071;quad(a,[X-ux*L-uz*w,Y+0.01,Z-uz*L+ux*w],[X+ux*L-uz*w,Y+0.01,Z+uz*L+ux*w],[X+ux*L+uz*w,Y+0.01,Z+uz*L-ux*w],[X-ux*L+uz*w,Y+0.01,Z-uz*L-ux*w],[0,0,0],cr)}}continue}
  if((p.k==='mine'||p.k==='chop')&&!p.thing){const q=rfEase(age/0.24),h=0.5+0.4*(1-q),w=0.075*(age>0.45?Math.max(0.2,1-(age-0.45)/0.27):1),tx=p.tx!=null?p.tx:p.x,ty=p.ty!=null?p.ty:p.y;let done=false;if(p.k==='mine')try{done=rfMineMark(a,tx,ty,rfLit(c,1.3-0.3*q),w*0.9,p.top?'top':p.blk)}catch(e){done=false}if(!done)rfSquare(a,tx,rfY(tx,ty),-ty,h,w,rfLit(c,1.3-0.3*q))}
  else{for(const d of [0,0.11]){const q=(age-d)/0.46;if(q<0||q>1)continue;const r=1.0-0.74*rfEase(q),w=0.09*(1-q*0.55);rfRing(a,X,Y,Z,r,w,rfLit(c,1.3-0.3*q))}
   if((p.k==='move'||p.k==='patrol')&&age<0.46){const q=rfEase(age/0.46),r=1.12-0.78*q,s=0.13*(1-q*0.4),cc=rfLit(c,1.35-0.3*q);for(let i=0;i<4;i++){const an=0.785+i*1.571,ux=Math.cos(an),uz=Math.sin(an),px=-uz,pz=ux;tri(a,[X+ux*r,Y+0.012,Z+uz*r],[X+ux*(r+s)+px*s*0.8,Y+0.012,Z+uz*(r+s)+pz*s*0.8],[X+ux*(r+s)-px*s*0.8,Y+0.012,Z+uz*(r+s)-pz*s*0.8],[0,0,0],cc)}}   // four chevrons riding the ring in to the spot
   if(p.k==='attack'&&age<0.5){const s=0.32*(1-rfEase(age/0.5)*0.4),w=0.05,cr=rfLit(c,1.25);for(const [ux,uz] of [[1,1],[1,-1]]){const L=s*0.7071;quad(a,[X-ux*L-uz*w,Y+0.01,Z-uz*L+ux*w],[X+ux*L-uz*w,Y+0.01,Z+uz*L+ux*w],[X+ux*L+uz*w,Y+0.01,Z+uz*L-ux*w],[X-ux*L+uz*w,Y+0.01,Z-uz*L-ux*w],[0,0,0],cr)}}}
}
 for(const f of RF.flashes){if(!f.drawn){f.drawn=now;const L=RF.last;if(L&&!L.drawn&&L.k==='select'&&Math.abs(L.at-f.at)<2)rfDrawn(L,now)}const age=(now-f.drawn)/1000;if(Math.floor(age/0.11)%2)continue;const t=V3.things.find(x=>x.key===f.key);if(!t||t.dx==null)continue;const c=RF_COL[f.k]||RF_COL.select,big=t.beast?0.5*(t.beast.size||1):0;
  rfRing(a,t.dx,rfThingY(t)+0.01,-t.dy,0.62+big+0.06*(1-age/0.66),0.075,rfLit(c,1.35),30);}
 if(RF.pend.length){const T=arr(model&&model.targets),sel=V3.things.filter(t=>t.kind==='mine'&&t.selected&&t.dx!=null);
  for(const u of sel){let px=u.dx,py=u.dy,best=-1;for(const q of T)if(q.unit===u.ref&&q.z===V3.z&&(q.index||0)>=best){best=q.index||0;px=q.x;py=q.y}
   for(const p of RF.pend){if(now-p.at>3000)continue;const c=RF_COL[p.k]||RF_COL.move,l=Math.hypot(p.x-px,p.y-py);let ex=p.x,ey=p.y;if(p.k==='mine'&&l>0.6)for(let f=0.5;f<Math.min(2,l);f+=0.1){ex=p.x-(p.x-px)/l*f;ey=p.y-(p.y-py)/l*f;const K=v3kindAt(Math.round(ex),Math.round(ey));if(!K||(K.kind!=='wall'&&K.kind!=='block'))break}   /* a dig's line stops at the foot of the face, not up the rock */
   rfLine(a,px,py,ex,ey,0.035,[c[0]*0.85,c[1]*0.85,c[2]*0.85,1],true);{let done=false;if(p.k==='mine')try{done=rfMineMark(a,p.x,p.y,c,0.045,p.top?'top':p.blk)}catch(e){done=false}if(!done)rfSquare(a,p.x,rfY(p.x,p.y),-p.y,0.47,0.045,c)}px=p.x;py=p.y}}}
 // the unit whose face (Company list, a group's faces) the pointer is on
 if(RF.hoverRef){const t=V3.things.find(x=>x.ref===RF.hoverRef);if(t&&t.dx!=null)rfRing(a,t.dx,rfThingY(t)+0.014,-t.dy,0.6+0.04*Math.sin(now/1000*8),0.05,[1,1,1,1],30)}
 // while a box is drawn: rings under the ones it will select
 {const d=V3.drag;if(d&&d.box&&d.moved&&RF.mouse&&V3.on){if(now-(RF.boxAt||0)>70){RF.boxAt=now;RF.boxRefs=new Set(v3boxRefs(d.x,d.y,RF.mouse.x,RF.mouse.y))}for(const t of V3.things)if(t.kind==='mine'&&t.dx!=null&&RF.boxRefs.has(t.ref))rfRing(a,t.dx,rfThingY(t)+0.012,-t.dy,0.57,0.045,[1,0.97,0.82,1],30)}else if(RF.boxRefs)RF.boxRefs=null}
 if(RF.over&&RF.mouse&&!V3.drag&&$('menu3d').hidden){if(RF.moved||now-RF.hvAt>150){RF.moved=false;RF.hvAt=now;const t=v3pickThing(RF.mouse.x,RF.mouse.y),tile=t?{x:t.x,y:t.y}:v3pickTile(RF.mouse.x,RF.mouse.y);RF.hv={t,tile,k:rfPredict(t,tile)};RF.hv.work=rfWorkTile(t,tile,RF.hv.k);rfCursor(RF.hv.k)}
  const H=RF.hv,pu=0.03*Math.sin(now/1000*7);
  if(H&&H.t&&H.t.dx!=null&&!(H.t.kind==='mine'&&H.t.selected)){const t=H.t,c=t.kind==='mine'?[1,0.97,0.82,1]:H.k==='attack'||t.kind==='npc'&&!t.peace||t.war?[1,0.36,0.28,1]:t.kind==='player'&&t.ally?[0.4,0.95,0.85,1]:t.kind==='animal'?[1,0.86,0.45,1]:[0.55,0.85,1,1],big=t.beast?0.5*(t.beast.size||1):0;rfRing(a,t.dx,rfThingY(t)+0.012,-t.dy,0.56+big+pu,0.04,c,30)}
  else if(H&&H.tile&&!H.t&&(H.k==='mine'||H.k==='chop')){const T=H.k==='mine'&&model&&model.hover&&model.hover.tx!=null&&model.hover.x===H.tile.x&&model.hover.y===H.tile.y?{x:model.hover.tx,y:model.hover.ty}:H.work||H.tile;let done=false;if(H.k==='mine'&&H.tile.top)try{done=rfMineMark(a,T.x,T.y,rfLit(RF_COL.mine,1.15),0.04,'top')}catch(e){done=false}else if(H.k==='mine')try{const hv=model&&model.hover,same=T.x===H.tile.x&&T.y===H.tile.y,b=same&&!H.tile.up&&RF.mouse?rfPointBlock(T.x,T.y,RF.mouse.x,RF.mouse.y):null,bb=b!=null?b:hv&&hv.blk!=null&&hv.x===H.tile.x&&hv.y===H.tile.y?hv.blk:null,gold=[1,0.84,0.3,1];
     /* the block a click takes, in gold over the green: thick on its faces, and its whole outline (cut away or faded too) */done=rfMineMark(a,T.x,T.y,gold,0.075,bb);if(bb!=null&&rfBlockBox(a,T.x,T.y,bb,gold,0.026))done=true}catch(e){done=false}if(!done)rfSquare(a,T.x,rfY(T.x,T.y),-T.y,0.49+pu*0.5,0.035,rfLit(RF_COL[H.k],1.15))}}
 else if(RF.cur&&!RF.over)rfCursor(null)}
// Pointers: a gilded arrow, and a sword, pick, axe or hand over what a click would attack, dig, chop or take.
// Drawn once on a canvas at 1x and 2x (for Retina) and used through -webkit-image-set.
const RF_CUR={};
function rfCursorArt(){const hot={base:[2,2],attack:[3,3],mine:[8,7],chop:[3,10],hand:[11,2]};
 const draw=(g,k)=>{const ink='#2a1d0c',gold='#e8c477';g.lineJoin='round';g.lineCap='round';
  const shape=(path,fill,stroke,lw)=>{g.beginPath();path();g.shadowColor='rgba(0,0,0,.55)';g.shadowBlur=1.5;g.shadowOffsetX=0.8;g.shadowOffsetY=1;g.lineWidth=lw;g.strokeStyle=stroke;g.stroke();g.shadowColor='transparent';g.fillStyle=fill;g.fill()};
  if(k==='base'){const P=()=>{g.moveTo(2,2);g.lineTo(2,24);g.lineTo(7.6,18.8);g.lineTo(11.6,27.6);g.lineTo(15.6,25.8);g.lineTo(11.8,17.2);g.lineTo(19.6,17.2);g.closePath()};shape(P,'#1c160d',ink,3.2);g.beginPath();P();g.lineWidth=1.5;g.strokeStyle=gold;g.stroke();g.beginPath();g.moveTo(4,6.5);g.lineTo(4,18.5);g.lineTo(7.5,15.4);g.lineWidth=1;g.strokeStyle='rgba(255,236,190,.45)';g.stroke()}
  if(k==='attack'){g.save();g.translate(3,3);g.rotate(Math.PI/4);const B=()=>{g.moveTo(0,0);g.lineTo(4,-2.3);g.lineTo(23,-2.3);g.lineTo(23,2.3);g.lineTo(4,2.3);g.closePath()};shape(B,'#eef0f4','#4a0d0a',2.4);g.beginPath();g.moveTo(3,0);g.lineTo(22,0);g.lineWidth=0.9;g.strokeStyle='rgba(150,30,25,.75)';g.stroke();
   shape(()=>{g.rect(22.5,-7,3,14)},'#d9a640',ink,2);shape(()=>{g.rect(25.5,-1.6,7,3.2)},'#6b3b1c',ink,2);shape(()=>{g.arc(34.6,0,2.6,0,7)},'#d9a640',ink,2);g.restore()}
  if(k==='mine'){shape(()=>{g.moveTo(27.5,28.5);g.lineTo(11.6,8.4);g.lineTo(9.6,10.4);g.lineTo(25.5,30.5);g.closePath()},'#8a5a2b',ink,2.2);
   shape(()=>{g.moveTo(2.5,17.5);g.quadraticCurveTo(4.5,2.5,19.5,1.5);g.quadraticCurveTo(9,8.5,2.5,17.5);g.closePath()},'#c9ccd2','#20232a',2.4);g.beginPath();g.moveTo(5,13.5);g.quadraticCurveTo(6.5,4.5,16,3.2);g.lineWidth=0.9;g.strokeStyle='rgba(255,255,255,.7)';g.stroke();
   shape(()=>{g.arc(10.6,9.4,1.6,0,7)},'#6b6f78','#20232a',1.2)}
  if(k==='chop'){shape(()=>{g.moveTo(26,29);g.lineTo(13.4,7.6);g.lineTo(11,9);g.lineTo(23.6,30.4);g.closePath()},'#8a5a2b',ink,2.2);
   shape(()=>{g.moveTo(14.5,6.5);g.lineTo(7,2.2);g.quadraticCurveTo(1.2,9.5,4.2,17.5);g.lineTo(15.5,11.8);g.closePath()},'#c9ccd2','#20232a',2.4);g.beginPath();g.moveTo(6.4,3.6);g.quadraticCurveTo(2.6,9.6,4.9,15.6);g.lineWidth=1;g.strokeStyle='rgba(255,255,255,.8)';g.stroke()}
  if(k==='hand'){const R=(x,y,w,h,r)=>()=>{g.moveTo(x+r,y);g.arcTo(x+w,y,x+w,y+h,r);g.arcTo(x+w,y+h,x,y+h,r);g.arcTo(x,y+h,x,y,r);g.arcTo(x,y,x+w,y,r);g.closePath()};
   const parts=[R(9,1,5.4,17,2.7),R(14,9,4.6,11,2.3),R(18.2,10,4.4,10.5,2.2),R(22.2,12,4,9.5,2),R(7.5,15,19,14.5,5)],thumb=()=>{g.save();g.translate(7.4,19);g.rotate(-0.7);g.moveTo(5,0);g.ellipse(0,0,5,2.6,0,0,7);g.restore()};
   g.beginPath();for(const p of parts)p();thumb();g.shadowColor='rgba(0,0,0,.55)';g.shadowBlur=1.5;g.shadowOffsetX=0.8;g.shadowOffsetY=1;g.lineWidth=2.6;g.strokeStyle=ink;g.stroke();g.shadowColor='transparent';g.fillStyle='#f3e3c3';for(const p of parts){g.beginPath();p();g.fill()}g.beginPath();thumb();g.fill();
   g.beginPath();g.moveTo(14.2,15);g.lineTo(14.2,19);g.moveTo(18.2,15.5);g.lineTo(18.2,20);g.moveTo(22.3,16);g.lineTo(22.3,20.5);g.lineWidth=0.9;g.strokeStyle='rgba(42,29,12,.55)';g.stroke()}};
 for(const k of Object.keys(hot)){const url=s=>{const c=document.createElement('canvas');c.width=c.height=32*s;const g=c.getContext('2d');g.scale(s,s);draw(g,k);return c.toDataURL('image/png')};try{const u1=url(1),u2=url(2),[hx,hy]=hot[k],fb=k==='base'?'default':k==='hand'?'pointer':'crosshair';RF_CUR[k]=['-webkit-image-set(url('+u1+') 1x, url('+u2+') 2x) '+hx+' '+hy+', '+fb,'url('+u1+') '+hx+' '+hy+', '+fb]}catch(e){}}}
function rfCursor(k){const c=$('world3d');if(!c)return;const key={attack:'attack',capture:'hand',mine:'mine',chop:'chop',pick:'hand',use:'hand',fish:'hand'}[k]||'base';if(RF.cur===key)return;RF.cur=key;const v=RF_CUR[key];if(!v){c.style.cursor='';return}c.style.cursor=v[1];c.style.cursor=v[0];if(!c.style.cursor)c.style.cursor=v[1]}
// The camera: the selection's middle (a control group's second tap).
function rfJumpToSelection(){const S=V3.things.filter(t=>t.kind==='mine'&&t.selected&&t.dx!=null);if(!S.length){/* out of the loaded view (or another level): the game's own Z takes the camera there */if(arr(model&&model.units).some(u=>u.selected))send('action','goto');return}let x=0,y=0;for(const t of S){x+=t.dx;y+=t.dy}x/=S.length;y/=S.length;rfLookAt(x,y)}
function rfLookAt(x,y){if(!V3.on)return;const far=Math.hypot(x-V3.cx,y-V3.cy)>30;V3.tcx=x;V3.tcy=y;if(far){V3.cx=x;V3.cy=y}V3.panAt=performance.now();v3panSend(true)}
// Held keys and the window's edges pan the camera smoothly, faster when zoomed out; the wheel zooms with easing.
const RF_PAN={arrowup:[0,1],w:[0,1],arrowdown:[0,-1],s:[0,-1],arrowleft:[-1,0],arrowright:[1,0],d:[1,0]};
function rfEdgeOn(){try{return localStorage.getItem('rm-edgescroll')!=='0'}catch(e){return true}}
function rfScrollSpeed(){try{return +localStorage.getItem('rm-scrollspeed')||1}catch(e){return 1}}
function rfEdge(ts){if(!RF.edgeOk||!RF.inWin||V3.drag||!RF.mouse||document.hidden)return [0,0];const still=performance.now()-(RF.moveAt||0);if(still>6000||still>4000&&!document.hasFocus())return [0,0];   /* a pointer left resting at an edge stops scrolling after 6 s (4 s when the window is not focused) */const W=innerWidth,H=innerHeight,x=RF.cx,y=RF.cy,m=4;if(x<0||y<0||x>=W||y>=H)return [0,0];   /* the window shrank under a still pointer: it is outside now */const ex=x<=m?-1:x>=W-1-m?1:0,ey=y<=m?1:y>=H-1-m?-1:0;if(!ex&&!ey){RF.edgeAt=0;return [0,0]}if(!RF.edgeAt)RF.edgeAt=ts;return ts-RF.edgeAt>110?[ex,ey]:[0,0]}
function rfTick(ts){requestAnimationFrame(rfTick);const dt=Math.min(0.1,(ts-(RF.lt||ts))/1000);RF.lt=ts;if(!V3.on||!V3.gl)return;
 if(ts-RFM.at>(RFM.held||RFM.pings.length?33:120)&&rfMiniOn())try{const t0=performance.now();rfMiniDraw();const c=performance.now()-t0;RF.costMini=RF.costMini==null?c:RF.costMini*0.9+c*0.1}catch(e){RFM.at=ts;console.error(e)}
 if(RF.zoomTo!=null){if(V3.cine)RF.zoomTo=null;else{const d=RF.zoomTo-V3.dist;if(Math.abs(d)<0.02){V3.dist=RF.zoomTo;RF.zoomTo=null;clearTimeout(V3.sizeT);V3.sizeT=setTimeout(v3sizeCheck,200)}else V3.dist+=d*Math.min(1,dt*14)}}
 let px=0,py=0;for(const k of RF.keys){const v=RF_PAN[k];if(v){px+=v[0];py+=v[1]}}const E=rfEdge(ts);px+=E[0];py+=E[1];
 if(px||py){const l=Math.hypot(px,py),ux=px/l,uy=py/l;RF.panV=Math.min(1,RF.panV+dt*5);const sp=(5+V3.dist*1.15)*(RF.speed||1)*(0.35+0.65*RF.panV)*dt,f=[-Math.sin(V3.yaw),Math.cos(V3.yaw)],r=[Math.cos(V3.yaw),Math.sin(V3.yaw)];
  let x=V3.tcx+(ux*r[0]+uy*f[0])*sp,y=V3.tcy+(ux*r[1]+uy*f[1])*sp;if(model&&model.maxx){x=Math.max(1,Math.min(model.maxx,x));y=Math.max(1,Math.min(model.maxy,y))}V3.tcx=x;V3.tcy=y;V3.panAt=performance.now();v3panSend(false)}
 else if(RF.panV){RF.panV=0;v3panSend(true)}}
addEventListener('wheel',e=>{if(!V3.on||e.target!==$('world3d')||e.ctrlKey)return;e.preventDefault();e.stopPropagation();const px=e.deltaMode===1?e.deltaY*16:e.deltaMode===2?e.deltaY*400:e.deltaY,f=Math.exp(Math.max(-0.5,Math.min(0.5,px*0.0016)));RF.zoomTo=Math.max(6,Math.min(60,(RF.zoomTo??V3.dist)*f))},{capture:true,passive:false});
addEventListener('mousemove',e=>{RF.mouse={x:mx(e),y:my(e)};RF.cx=e.clientX;RF.cy=e.clientY;RF.over=e.target===$('world3d');RF.moved=true;RF.inWin=true;RF.moveAt=performance.now()},{passive:true});
document.addEventListener('mouseout',e=>{if(!e.relatedTarget){RF.inWin=false;RF.over=false;RF.edgeAt=0}});
document.addEventListener('visibilitychange',()=>{if(document.hidden){RF.inWin=false;RF.keys.clear()}});
addEventListener('resize',()=>{RF.inWin=false;RF.edgeAt=0});   // a resized window has no pointer inside it until it moves (playtest r8: a shrunk window scrolled off for ever)
addEventListener('keydown',e=>{if(!V3.on||e.metaKey||e.ctrlKey||e.altKey)return;const k=(e.key||'').toLowerCase();if(!RF_PAN[k])return;if(e.target&&e.target.closest&&e.target.closest('input,select,textarea,#minimap'))return;e.preventDefault();e.stopImmediatePropagation();RF.keys.add(k)},true);
addEventListener('keyup',e=>{const k=(e.key||'').toLowerCase();if(RF.keys.delete(k)&&!RF.keys.size)v3panSend(true)},true);
// Escape in Attack mode (A, then a click) leaves the mode and keeps the selection, as in StarCraft
addEventListener('keydown',e=>{if(e.key!=='Escape'||!model||!model.attackMode||e.target&&e.target.closest&&e.target.closest('input,select,textarea'))return;e.preventDefault();e.stopImmediatePropagation();send('attackmode','')},true);
// Esc closes the open window first (Settings, the world map, a page such as Village or Build), and deselects only when
// none is open, as most games do (hud-craft 04:55). Cards, menus, a held item and an aim keep their own Esc.
addEventListener('keydown',e=>{if(e.key!=='Escape'||e.target&&e.target.closest&&e.target.closest('input,select,textarea'))return;if((typeof V3!=='undefined'&&V3.aim)||(model&&model.useon)||['askcard','usecard','menu3d','loghist','nearcard'].some(id=>$(id)&&!$(id).hidden))return;
 const b=$('settings')&&!$('settings').hidden?$('setClose'):$('worldmap')&&!$('worldmap').hidden?$('wmClose'):document.body.classList.contains('panel-open')?$('panelClose'):null;if(!b)return;e.preventDefault();e.stopImmediatePropagation();b.click()},true);
addEventListener('blur',()=>RF.keys.clear());
// The arrow keys while the game window has the keyboard (skin.dmf NORTH+REP ... call Remaster-3D-Key, Attack.dm):
// each press or repeat is a camera-relative step, eased like every pan, sized to the zoom.
const RF_DIR={north:[0,1],south:[0,-1],east:[1,0],west:[-1,0],northeast:[1,1],northwest:[-1,1],southeast:[1,-1],southwest:[-1,-1]};
function rfStep(d){if(!V3.on)return;const st=Math.max(1.5,V3.dist*0.12)*(RF.speed||1),l=Math.hypot(d[0],d[1]),ux=d[0]/l,uy=d[1]/l,f=[-Math.sin(V3.yaw),Math.cos(V3.yaw)],r=[Math.cos(V3.yaw),Math.sin(V3.yaw)];
 let x=V3.tcx+(ux*r[0]+uy*f[0])*st,y=V3.tcy+(ux*r[1]+uy*f[1])*st;if(model&&model.maxx){x=Math.max(1,Math.min(model.maxx,x));y=Math.max(1,Math.min(model.maxy,y))}V3.tcx=x;V3.tcy=y;V3.panAt=performance.now();v3panSend(false)}
if(typeof window.key3d==='function'){const k3=window.key3d;window.key3d=function(k){const d=RF_DIR[String(k)];if(d){rfStep(d);return}if(String(k)==='escape'){document.body.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',code:'Escape',bubbles:true,cancelable:true}));return}return k3(k)}}   // Esc with the game window focused: the page's own Escape handling
// A jump the game made (Z, a control group's second tap, the last alert): the 3D camera goes there now (Attack.dm RemasterCamTo).
window.rfCamTo=function(v){const p=String(v).split(',').map(Number);if(p.length===2&&isFinite(p[0])&&isFinite(p[1]))rfLookAt(p[0],p[1])};
// Control groups, Z, Ctrl+Z, F1, P, R, comma/period and the alert jump, while the HUD page has the keyboard (the game window's skin.dmf
// macros do the same when it has the keyboard).
addEventListener('keydown',e=>{if(e.target&&e.target.closest&&e.target.closest('input,select,textarea,[contenteditable]'))return;
 if(e.key==='Backspace'&&!e.metaKey&&!e.ctrlKey&&!e.altKey){e.preventDefault();if(model&&model.alert)send('attack','');else toast('No one is under attack.');return}
 if((e.key==='z'||e.key==='Z')&&!e.metaKey&&!e.ctrlKey&&!e.altKey&&V3.on){e.preventDefault();rfJumpToSelection();return}
 if((e.key==='z'||e.key==='Z')&&(e.ctrlKey||e.metaKey)&&!e.shiftKey&&!e.altKey){e.preventDefault();send('undo','');return}   // Ctrl+Z (or Cmd+Z): undo the last plan or order, as the game window's macro does
 if(e.key==='F1'&&!e.metaKey&&!e.ctrlKey&&!e.altKey){e.preventDefault();send('idle','');return}   // F1: the next idle unit
 if(!e.metaKey&&!e.ctrlKey&&!e.altKey){const a={p:'stop',',':'zup','.':'zdown',r:'race'}[e.key];if(a==='race'&&((model&&model.ask)||['askcard','usecard','menu3d'].some(id=>$(id)&&!$(id).hidden)))return;if(a){e.preventDefault();send('action',a);return}}   // P stops; , and . take the camera up or down a level; R: Choose your people / start again (the game window's keys)
 const m=/^Digit([1-9])$/.exec(e.code||'');if(!m||e.metaKey||e.altKey||e.repeat)return;e.preventDefault();const n=+m[1];
 if(e.ctrlKey||e.shiftKey){const tok=currentSelectionToken();if(!tok){toast('Select units first, then '+(e.ctrlKey?'Ctrl':'Shift')+'+'+n+' saves them as group '+n+'.');rfSfx('deny');return}send('controlgroup',n+'|'+(e.ctrlKey?'Set':'Add')+'|'+tok);rfSfx('group-set');return}
 const now=performance.now(),dbl=RF.tap.n===n&&now-RF.tap.at<350;RF.tap={n,at:now};send('controlgroup',n+'|Select|');rfSfx('group-recall');if(dbl){if(RF.hudAt>now-1500&&RF.hudAt<now)rfJumpToSelection();RF.jump={at:now}}});
// The minimap in 3D is local: about 160 tiles round the camera (the whole world, 1000 tiles, made the explored land a
// few pixels), north up, from the 3D view's own data: the far view's 4-tile cells and the loaded tiles. Your units,
// others, orders and recent events on it; the camera's view drawn as its real footprint on the ground. Press and drag
// moves the camera; the map stays put while you drag. The world map (Map) still shows everything.
const RFM={R:80,cx:null,cy:null,bg:null,key:'',held:false,at:0,pings:[]};
function rfMiniOn(){return !!(V3.on&&V3.gl&&model&&V3.terrain)}
function rfMiniCentre(){if(RFM.held&&RFM.cx!=null)return;const x=Math.round(V3.cx),y=Math.round(V3.cy);if(RFM.cx==null||Math.abs(x-RFM.cx)>RFM.R*0.45||Math.abs(y-RFM.cy)>RFM.R*0.45||V3.z!==RFM.z){RFM.cx=x;RFM.cy=y;RFM.z=V3.z}}
function rfMiniBg(c){const T=V3.terrain,F=V3.z===1?V3.farData:null,key=[RFM.cx,RFM.cy,RFM.z,c.width].join(',');if(RFM.bg&&RFM.key===key&&RFM.T===T&&RFM.F===F)return RFM.bg;
 const W=c.width,S=2*RFM.R+1,k=W/S,b=RFM.bg&&RFM.bg.width===W?RFM.bg:document.createElement('canvas');b.width=b.height=W;const g=b.getContext('2d');g.fillStyle='#16130d';g.fillRect(0,0,W,W);
 const x0=RFM.cx-RFM.R,y1=RFM.cy+RFM.R,px=x=>(x-x0)*k,py=y=>(y1-y)*k,hid=(x,y)=>(((x>>2)+(y>>2))&1)?'#1d1a13':'#221e16';
 if(Array.isArray(F))for(const f of F){const cells=f[2]||[],sm=typeof f[3]==='string'?f[3]:'1111111111111111',ox=f[0]*16+1,oy=f[1]*16+1;for(let j=0;j<4;j++)for(let i=0;i<4;i++){const tx=ox+i*4,ty=oy+j*4;if(tx+4<x0||tx>x0+S||ty+4<y1-S||ty>y1)continue;const v=cells[j*4+i];g.fillStyle=sm[j*4+i]!=='1'?hid(tx,ty):v?mapLift(v):'#2a2a22';g.fillRect(px(tx)-0.5,py(ty+3)-0.5,4*k+1,4*k+1)}}
 if(T&&Array.isArray(T.tiles)){const Sn=V3.seen;for(let j=0;j<T.h;j++)for(let i=0;i<T.w;i++){const v=T.tiles[j*T.w+i];if(!v)continue;const tx=T.x0+i,ty=T.y0+j;if(tx<x0||tx>x0+S||ty<y1-S||ty>y1)continue;const K=T.kinds[v-1];let col=K&&K.color||'#556655';
   if(Sn){const si=tx-Sn.x0,sj=ty-Sn.y0;if(si>=0&&sj>=0&&si<Sn.w&&sj<Sn.h&&Sn.s[sj*Sn.w+si]!=='1'){g.fillStyle=hid(tx,ty);g.fillRect(px(tx)-0.5,py(ty)-0.5,k+1,k+1);continue}}
   if(K&&(K.kind==='wall'||K.kind==='block'))col='#6b665c';else if(K&&K.kind==='built')col='#9a8f7a';else if(K&&K.kind==='tree')col='#2f5a2a';g.fillStyle=mapLift(col);g.fillRect(px(tx)-0.5,py(ty)-0.5,k+1,k+1)}}
 RFM.bg=b;RFM.key=key;RFM.T=T;RFM.F=F;return b}
// The ground point the camera sees through a spot on the screen (the view's footprint corners).
function rfGroundAt(sx,sy){if(!V3.inv)return null;const c=$('world3d'),nx=sx/c.clientWidth*2-1,ny=1-sy/c.clientHeight*2,m=V3.inv,un=(x,y,z)=>{const X=x*m[0]+y*m[4]+z*m[8]+m[12],Y=x*m[1]+y*m[5]+z*m[9]+m[13],Z=x*m[2]+y*m[6]+z*m[10]+m[14],W=x*m[3]+y*m[7]+z*m[11]+m[15];return [X/W,Y/W,Z/W]};
 const a=un(nx,ny,-1),b=un(nx,ny,1),dy=b[1]-a[1];if(Math.abs(dy)<1e-6)return null;const t=-a[1]/dy;if(t<0)return null;return [a[0]+(b[0]-a[0])*t,-(a[2]+(b[2]-a[2])*t)]}
// The camera's view box on the minimap: a flat 2D rectangle (the user, 06:16: "the highlight box is 3d when it needs to
// be in 2d"), not the view's perspective footprint. Centred on the camera's focus, as wide as the ground the screen
// spans through its middle, the screen's proportions, turned with the camera. Corners: far left, far right, near
// right, near left.
function rfMiniFootprint(){const v=$('world3d');if(!v||!V3.on)return null;const w=v.clientWidth,h=v.clientHeight;if(!w||!h)return null;
 const L=rfGroundAt(0,h/2),Rt=rfGroundAt(w,h/2);let W=L&&Rt?Math.hypot(Rt[0]-L[0],Rt[1]-L[1]):V3.dist*1.2;W=Math.max(4,Math.min(W,RFM.R*1.2));
 const H=W*h/w,r=[Math.cos(V3.yaw),Math.sin(V3.yaw)],f=[-Math.sin(V3.yaw),Math.cos(V3.yaw)],cx=V3.cx,cy=V3.cy,P=(a,b)=>[cx+r[0]*a+f[0]*b,cy+r[1]*a+f[1]*b];
 return [P(-W/2,H/2),P(W/2,H/2),P(W/2,-H/2),P(-W/2,-H/2)]}
function rfMiniDraw(){const c=$('minimap');if(!c)return;rfMiniCentre();const g=c.getContext('2d'),W=c.width,S=2*RFM.R+1,k=W/S,x0=RFM.cx-RFM.R,y1=RFM.cy+RFM.R,px=x=>(x-x0+0.5)*k,py=y=>(y1-y+0.5)*k;
 g.drawImage(rfMiniBg(c),0,0);
 // the camera's view: a flat rectangle outline, as StarCraft draws it (rfMiniFootprint), clipped to the round map
 {const F=rfMiniFootprint();if(F){g.save();g.beginPath();g.arc(W/2,W/2,W/2-1,0,7);g.clip();g.beginPath();F.forEach(([x,y],i)=>i?g.lineTo(px(x),py(y)):g.moveTo(px(x),py(y)));g.closePath();
  g.fillStyle='rgba(242,210,122,.05)';g.fill();g.lineWidth=3;g.strokeStyle='rgba(0,0,0,.7)';g.stroke();g.lineWidth=1.4;g.strokeStyle='#f2d27a';g.stroke();g.restore()}}
 // orders, then everyone (yours on top), then recent events
 for(const t of arr(model.targets))if(t.z===V3.z){g.strokeStyle='#ffb27d';g.lineWidth=1.5;g.beginPath();g.arc(px(t.x),py(t.y),3.5,0,7);g.stroke()}
 const dot=(x,y,r,fill)=>{g.fillStyle='#000';g.fillRect(px(x)-r-1,py(y)-r-1,2*r+2,2*r+2);g.fillStyle=fill;g.fillRect(px(x)-r,py(y)-r,2*r,2*r)};
 for(const t of V3.things){if(t.ly||t.dx==null||!['npc','player','animal'].includes(t.kind)||!v3visible(t))continue;dot(t.dx,t.dy,1.5,t.kind==='animal'?'#d8c08a':t.kind==='player'?(t.ally?'#5fe0cf':t.war?'#ff5a45':'#7fa6ff'):t.peace?'#e8c060':'#ff5a45')}
 for(const t of V3.things)if(t.kind==='mine'&&t.dx!=null&&!t.ly)dot(t.dx,t.dy,2,t.selected?'#ffd34a':'#9ff0a8');
 drawPings(g,px,py,V3.z,0.7);
 {const now=performance.now();RFM.pings=RFM.pings.filter(p=>now-p.at<700);for(const p of RFM.pings){const q=(now-p.at)/700;g.globalAlpha=1-q;g.strokeStyle=p.k==='attack'?'#ff5a45':'#6af27a';g.lineWidth=2;g.beginPath();g.arc(px(p.x),py(p.y),3+12*(1-q),0,7);g.stroke();g.globalAlpha=1}}   // a minimap order: a green ring closing on the spot
 g.font='bold 11px -apple-system,sans-serif';g.textAlign='center';g.lineWidth=3;g.strokeStyle='#000';g.strokeText('N',W/2,14);g.fillStyle='#f2d27a';g.fillText('N',W/2,14);g.textAlign='start';RFM.at=performance.now()}
if(typeof renderMap==='function'){const base=renderMap;renderMap=function(){if(rfMiniOn())try{rfMiniDraw();return}catch(e){console.error(e)}base()}}
// Minimap pointer: the spot under it; press and drag moves the camera there. Captured before the map's own handler,
// which maps the whole world.
// The HUD's zoom (hudKC) puts element rects and pointer positions in the same pixels on some engines and not on
// others; the press itself (it is on the map) says which: the reading that lands inside the map's rect.
function rfMiniTile(e,start){const c=$('minimap'),r=c.getBoundingClientRect(),S=2*RFM.R+1,z=hudKC()||1;if(start){const X=e.clientX,Y=e.clientY;RFM.scale=X>=r.left-1&&X<=r.right+1&&Y>=r.top-1&&Y<=r.bottom+1?1:1/z}
 const k=RFM.scale||1/z,fx=Math.max(0,Math.min(1,(e.clientX*k-r.left)/r.width)),fy=Math.max(0,Math.min(1,(e.clientY*k-r.top)/r.height));return [RFM.cx-RFM.R+fx*S-0.5,RFM.cy+RFM.R-fy*S+0.5]}
{const mm=$('minimap');if(mm){const go=(e,now,start)=>{const p=rfMiniTile(e,start);if(!p)return;let [x,y]=p;if(model&&model.maxx){x=Math.max(1,Math.min(model.maxx,x));y=Math.max(1,Math.min(model.maxy,y))}V3.tcx=x;V3.tcy=y;V3.panAt=performance.now();v3panSend(now)};
 const order=(e,k)=>{const p=rfMiniTile(e,true);if(!p)return;const x=Math.round(p[0]),y=Math.round(p[1]),now=performance.now();send('mapmove',x+'|'+y+'|'+(e.shiftKey?'1':'0'));RFM.pings.push({x,y,at:now,k});RF.pings.push({x,y,k,at:now,up:false,thing:false});rfOrderSfx(k,x,y,e.shiftKey);rfMiniDraw()};
 addEventListener('pointerdown',e=>{if(e.target!==mm||e.button!==0||!rfMiniOn())return;e.stopPropagation();if(model&&model.attackMode&&rfSelected()){RFM.swallow=true;order(e,'attack');return}RFM.held=true;try{mm.setPointerCapture(e.pointerId)}catch(_){}go(e,false,true);rfMiniDraw()},true);
 addEventListener('pointermove',e=>{if(!RFM.held||!(e.buttons&1))return;e.stopPropagation();go(e,false)},true);
 addEventListener('pointerup',e=>{if(RFM.swallow){RFM.swallow=false;e.stopPropagation();return}if(!RFM.held){if(e.target===mm&&rfMiniOn())e.stopPropagation();return}RFM.held=false;e.stopPropagation();go(e,true)},true);   // the map's own handler (whole world, any button) never runs while this one is on
 addEventListener('pointercancel',()=>{RFM.held=false},true);
 // right-click with units selected: they go there, however far (HUD.dm mapmove → Orders.dm RemasterMapMove), as in StarCraft
 addEventListener('contextmenu',e=>{if(e.target!==mm||!rfMiniOn()||!rfSelected())return;e.preventDefault();e.stopPropagation();order(e,model&&model.attackMode?'attack':'move')},true);
 mm.setAttribute('aria-label','Map of the land round the camera. Press or drag to move the camera; right-click to send the selected units there.');mm.title='The land round the camera\nPress or drag to move the camera there; right-click to send the selected units there. Map shows the whole world.'}}
// Settings: edge scrolling can be turned off; right-click can give orders instead of opening the menu.
{const s=$('settings'),hint=s&&s.querySelector('p.hint:last-of-type');if(s&&!$('setEdge')){const l=document.createElement('label');l.innerHTML='<input type="checkbox" id="setEdge"> Scroll the camera when the pointer touches the window’s edge';(hint||$('setClose')).before(l);const cb=$('setEdge');cb.checked=rfEdgeOn();cb.addEventListener('change',()=>{try{localStorage.setItem('rm-edgescroll',cb.checked?'1':'0')}catch(_){}RF.edgeOk=cb.checked})}
 if(s&&!$('setScroll')){const l=document.createElement('label');l.innerHTML='Camera scroll speed (edge and keys) <select id="setScroll"><option value="0.6">Slow</option><option value="1">Normal</option><option value="1.6">Fast</option></select>';(hint||$('setClose')).before(l);const sel=$('setScroll');sel.value=String(rfScrollSpeed());if(!sel.value)sel.value='1';sel.addEventListener('change',()=>{try{localStorage.setItem('rm-scrollspeed',sel.value)}catch(_){}RF.speed=+sel.value||1})}
 if(s&&!$('setRclick')){const l=document.createElement('label');l.innerHTML='Right-click <select id="setRclick"><option value="menu">opens the menu of choices</option><option value="orders">gives orders, like StarCraft (Alt+right-click: menu)</option></select>';(hint||$('setClose')).before(l);const sel=$('setRclick');sel.value=rfRightOrders()?'orders':'menu';sel.addEventListener('change',()=>{try{localStorage.setItem('rm-rclick',sel.value)}catch(_){}RF.rclick=sel.value==='orders'})}}
RF.edgeOk=rfEdgeOn();RF.rclick=rfRightOrders();RF.speed=rfScrollSpeed();rfCursorArt();requestAnimationFrame(rfTick);
addEventListener('rm-prefs-restored',()=>{RF.edgeOk=rfEdgeOn();RF.rclick=rfRightOrders();RF.speed=rfScrollSpeed();const a=$('setEdge'),b=$('setRclick'),c=$('setScroll');if(a)a.checked=RF.edgeOk;if(b)b.value=RF.rclick?'orders':'menu';if(c)c.value=String(RF.speed)});   // settings saved in the profile (audio.js PERSIST)
// For probes and tests: click-to-feedback times in ms (drawn: the next frame with the ping; ack: the game's reply).
window.rfStats=function(){const med=L=>{if(!L.length)return null;const s=[...L].sort((a,b)=>a-b);return s[s.length>>1]};return {drawn:RF.lat.slice(),frames:RF.latFr.slice(),ack:RF.ack.slice(),drawnMedian:med(RF.lat),ackMedian:med(RF.ack),last:RF.last,pings:RF.pings.length,cursor:RF.cur,costDrawMs:RF.costDraw,costMiniMs:RF.costMini}};
</script>
