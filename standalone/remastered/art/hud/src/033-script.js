/* Formations (2026-10-23, formations): the order queue's square on every unit's slot when a group is sent somewhere
   (a move or an attack-move), drawn on the click's next frame and faded as each unit gets there.
   - At the click the page works out the slots itself (fmPredict: the same shape and hand-out as the game's
     RemasterGroupForm in Formations.dm, on the 3D view's own map), so the markers show at once.
   - The game then sends the real slots (rmSlots3D, a moment later); a marker that differs glides to its real tile.
   - Green for a move, red for an attack-move (the user prefers the square to an arrow, 10:0x). A Shift-queued leg
     keeps the earlier leg's markers; any other order for a unit takes its marker away.
   It wraps rts-feel's rfClick (the instant answer to a click) and rfDraw (its per-frame drawing) rather than editing
   them: the original runs first, unchanged. Source: tools/formations/fm_module.js, put in the page by
   tools/formations/patch_page.py (before the page's last script, which asks for the first model). */
'use strict';
const FM={sets:[],cost:null,lastPush:null,predicted:0,confirmed:0};
const FM_WALK=new Set(['floor','bfloor','bridge']);
const FM_COL={move:[0.45,0.9,0.45,1],attack:[0.95,0.3,0.25,1]};   // v3queues' colours
const fmEase=q=>{q=Math.max(0,Math.min(1,q));return 1-(1-q)*(1-q)*(1-q)};
function fmSel(){return V3.things.filter(t=>t.kind==='mine'&&t.selected&&!t.ly&&t.x!=null&&t.ref)}
function fmSnap(fx,fy,four){const ax=Math.abs(fx),ay=Math.abs(fy);if(four)return ax>=ay?[fx>=0?1:-1,0]:[0,fy>=0?1:-1];if(ax>ay*2.414)return [fx>=0?1:-1,0];if(ay>ax*2.414)return [0,fy>=0?1:-1];return [fx>=0?1:-1,fy>=0?1:-1]}
// How many abreast a shape's rows are (Formations.dm RemasterShapePer).
function fmShapePer(shape,n,width){let per;if(shape==='line'){const rows=Math.floor((n+11)/12);per=Math.floor((n+rows-1)/rows)}else if(shape==='column')per=n<=8?1:(n<=24?2:3);else per=Math.max(1,Math.floor(Math.sqrt(n)+0.999));
 if(width>0&&shape!=='column')per=Math.max(1,Math.min(n,Math.round(width)));return per}   /* a drag set the front row's width */
function fmShape(shape,n,tx,ty,fx,fy,width){const S=fmSnap(fx,fy,shape==='box'),sx=S[0],sy=S[1],ax=-sy,ay=sx,per=fmShapePer(shape,n,width);
 const rowsAll=Math.floor((n+per-1)/per),P=[];for(let i=0;i<n;i++){const r=Math.floor(i/per),c=i%per,count=r===rowsAll-1?n-r*per:per,off=c-Math.floor((count-1)/2),back=shape==='box'?r-Math.floor((rowsAll-1)/2):r;P.push([tx+ax*off-sx*back,ty+ay*off-sy*back,null])}return P}
// The player's own formation (Formations.dm RemasterCustomPoints): squares [dx,dy,role] round the clicked tile, forward
// up; each role's squares for its units, then the rest ("any" first); the square nearest the clicked tile goes on it.
const FM_ROLES=['front','ranged','mage','any'];
// L in order of k1 (then k2), smallest first, equal keys in the order they came; in place (Formations.dm RmSortBy, the
// same order: n log n, where the selection sorts were n squared).
function fmSortBy(L,k1,k2){const idx=L.map((_,i)=>i);idx.sort((a,b)=>(k1[a]-k1[b])||(k2?(k2[a]-k2[b]):0)||(a-b));const was=L.slice();for(let i=0;i<L.length;i++)L[i]=was[idx[i]];return L}
// Do A-B and C-D cross, not just touch (Formations.dm RmSegCross)?
function fmSegCross(ax,ay,bx,by,cx,cy,dx,dy){const d1=(dx-cx)*(ay-cy)-(dy-cy)*(ax-cx),d2=(dx-cx)*(by-cy)-(dy-cy)*(bx-cx),d3=(bx-ax)*(cy-ay)-(by-ay)*(cx-ax),d4=(bx-ax)*(dy-ay)-(by-ay)*(dx-ax);return ((d1>0&&d2<0)||(d1<0&&d2>0))&&((d3>0&&d4<0)||(d3<0&&d4>0))}
function fmCellKey(c){return Math.max(Math.abs(c[0]),Math.abs(c[1]))*1000+(c[0]*c[0]+c[1]*c[1])*10-c[1]}
function fmCustomPoints(grid,counts,n,tx,ty,fx,fy){let pool=grid.map(c=>[c[0],c[1],FM_ROLES.includes(c[2])?c[2]:'any']);if(!pool.length)return [];
 fmSortBy(pool,pool.map(fmCellKey));
 const cells=[];for(const r of ['mage','ranged','front']){let want=counts[r]||0;for(const C of pool.slice()){if(want<=0||cells.length>=n)break;if(C[2]!==r)continue;cells.push(C);pool.splice(pool.indexOf(C),1);want--}}
 for(let pass=1;pass<=2;pass++)for(const C of pool.slice()){if(cells.length>=n)break;if(pass===1&&C[2]!=='any')continue;cells.push(C);pool.splice(pool.indexOf(C),1)}
 let near=null;for(const C of cells)if(!near||fmCellKey(C)<fmCellKey(near))near=C;if(near&&(near[0]||near[1])){const ox=near[0],oy=near[1];for(const C of cells){C[0]-=ox;C[1]-=oy}}
 let x0=Infinity,x1=-Infinity,y0=Infinity;for(const c of cells){x0=Math.min(x0,c[0]);x1=Math.max(x1,c[0]);y0=Math.min(y0,c[1])}const w=Math.max(1,x1-x0+1);
 for(let i=0;cells.length<n;i++)cells.push([x0+i%w,y0-1-Math.floor(i/w),'any']);
 fmSortBy(cells,cells.map(c=>-c[1]),cells.map(c=>-c[0]));
 const F=fmSnap(fx,fy,true),rx=F[1],ry=-F[0];return cells.map(c=>[tx+c[0]*rx+c[1]*F[0],ty+c[0]*ry+c[1]*F[1],c[2]])}
// Front first (along the facing), then right to left (Formations.dm RemasterGeoOrder), in place.
function fmGeoOrder(L,pos,ox,oy,fx,fy){const P=L.map(pos);return fmSortBy(L,P.map(p=>-Math.floor((p[0]-ox)*fx+(p[1]-oy)*fy+0.5)),P.map(p=>(p[0]-ox)*-fy+(p[1]-oy)*fx))}
function fmMine(m){const L=arr(m&&m.formations),i=(m&&m.formationMine||1)-1,F=L[i];return F&&arr(F.cells).length?arr(F.cells):null}
function fmRoleOf(ref){const u=arr(model&&model.units).find(x=>x.ref===ref);return u&&u.frole||'any'}
function fmCompact(A){const n=A.length;if(n<2)return true;let x0=1e9,x1=-1e9,y0=1e9,y1=-1e9;for(const a of A){x0=Math.min(x0,a.x);x1=Math.max(x1,a.x);y0=Math.min(y0,a.y);y1=Math.max(y1,a.y)}const w=x1-x0+1,h=y1-y0+1,limit=Math.max(2,Math.floor(Math.sqrt(n))+1);return Math.max(w,h)<=2*limit+1&&w*h<=3*n+3}
// The slots the game will give the selected units for a group move to (tx, ty): [{ref,x,y}] (RemasterGroupForm's
// rules: the group's own shape when it is close together, else a block or the chosen shape, facing the way it goes;
// open tiles only, reachable from the target's open side; slid back from a wall; no two routes crossing).
function fmPredict(tx,ty,units,shapeName,face){const n=units.length;if(n<2)return null;let cx=0,cy=0;for(const u of units){cx+=u.x;cy+=u.y}cx/=n;cy/=n;
 let fx=tx-cx,fy=ty-cy;const fl=Math.hypot(fx,fy);if(fl<1.5){fx=0;fy=1}else{fx/=fl;fy/=fl}
 let shape=shapeName,width=0;if(face&&(face.fx||face.fy)){const l=Math.hypot(face.fx,face.fy);fx=face.fx/l;fy=face.fy/l;width=face.width||0;if(!['line','column','box','custom'].includes(shape))shape=width>=n?'line':'box'}const grid=fmMine(model);if(shape==='custom'&&!grid)shape='';if(!['line','column','box','custom'].includes(shape))shape=fmCompact(units)?'keep':'box';
 const roleOf=new Map(units.map(u=>[u,u.role||fmRoleOf(u.ref)]));
 let points;if(shape==='custom'){const counts={};for(const u of units){const r=roleOf.get(u);counts[r]=(counts[r]||0)+1}points=fmCustomPoints(grid,counts,n,tx,ty,fx,fy)}else if(shape==='keep'){let mid=null,md=Infinity;for(const u of units){const d=((u.x-cx)**2+(u.y-cy)**2)*10000-u.y*100+u.x;if(d<md){md=d;mid=u}}const vx=tx-mid.x,vy=ty-mid.y;points=units.map(u=>[u.x+vx,u.y+vy,u])}   /* anchored on the click: the one nearest the middle stands on it (Formations.dm) */else points=fmShape(shape,n,tx,ty,fx,fy,width);
 const mine=new Set(units.map(u=>u.x+','+u.y)),busy=new Set();for(const t of V3.things){if(t.ly||t.x==null)continue;if(t.kind==='item')continue;if(t.kind==='mine'&&t.selected)continue;busy.add(t.x+','+t.y)}
 const open=(x,y)=>{const K=v3kindAt(x,y);return !!K&&FM_WALK.has(K.kind)},free=(x,y)=>open(x,y)&&!busy.has(x+','+y);
 let ext=0;for(const p of points)ext=Math.max(ext,Math.abs(p[0]-tx),Math.abs(p[1]-ty));const R=Math.min(14,ext+4);
 let seed=null;if(free(tx,ty))seed=[tx,ty];else{let bd=Infinity;for(let x=tx-R;x<=tx+R;x++)for(let y=ty-R;y<=ty+R;y++){if(!free(x,y))continue;const d=Math.max(Math.abs(x-tx),Math.abs(y-ty))*100+Math.abs(x-cx)+Math.abs(y-cy);if(d<bd){bd=d;seed=[x,y]}}}
 if(!seed)return null;const reach=new Set([seed[0]+','+seed[1]]),stack=[seed];
 while(stack.length){const c=stack.pop();for(const [dx,dy] of [[0,1],[0,-1],[1,0],[-1,0],[1,1],[-1,1],[1,-1],[-1,-1]]){const x=c[0]+dx,y=c[1]+dy,k=x+','+y;if(reach.has(k)||Math.max(Math.abs(x-tx),Math.abs(y-ty))>R)continue;if(!open(x,y)||busy.has(k)&&!mine.has(k))continue;reach.add(k);stack.push([x,y])}}
 const places=new Set();for(const k of reach){if(!busy.has(k))places.add(k)}if(!places.size)return null;
 const back=fmSnap(fx,fy);let sx=0,sy=0,bestFit=-1;for(let k=0;k<=3;k++){let fit=0;for(const p of points)if(places.has((p[0]-back[0]*k)+','+(p[1]-back[1]*k)))fit++;if(fit>bestFit){bestFit=fit;sx=-back[0]*k;sy=-back[1]*k}if(fit>=n)break}
 const mx=tx+sx,my=ty+sy,ordered=points.slice(),key=p=>Math.max(Math.abs(p[0]+sx-mx),Math.abs(p[1]+sy-my));
 fmSortBy(ordered,ordered.map(key));
 const tiles=[],owner=[];for(const p of ordered){const px=p[0]+sx,py=p[1]+sy;let best=null,bd=Infinity;const sc=(x,y)=>(x-px)**2+(y-py)**2+0.1*Math.max(Math.abs(x-mx),Math.abs(y-my));
  const rx=Math.round(px),ry=Math.round(py);for(let x=rx-2;x<=rx+2;x++)for(let y=ry-2;y<=ry+2;y++){if(!places.has(x+','+y))continue;const d=sc(x,y);if(d<bd){bd=d;best=[x,y]}}
  if(!best)for(const k of places){const [x,y]=k.split(',').map(Number),d=sc(x,y);if(d<bd){bd=d;best=[x,y]}}if(!best)break;places.delete(best[0]+','+best[1]);tiles.push(best);owner.push(p[2])}
 const assign=new Map(),keyOf=new Map();if(shape==='keep'){for(let i=0;i<tiles.length;i++)if(owner[i])assign.set(owner[i],tiles[i])}
 else if(shape==='custom'){const posU=u=>[u.x,u.y],posT=i=>tiles[i];let freeT=tiles.map((_,i)=>i),left=units.slice();
  for(const r of ['mage','ranged','front','fill']){const U=left.filter(u=>r==='fill'||roleOf.get(u)===r);let I=freeT.filter(i=>r==='fill'?owner[i]==='any':owner[i]===r);if(r==='fill')I=I.concat(freeT.filter(i=>!I.includes(i)));
   fmGeoOrder(U,posU,cx,cy,fx,fy);if(r!=='fill')fmGeoOrder(I,posT,mx,my,fx,fy);for(let q=0;q<U.length&&q<I.length;q++){assign.set(U[q],tiles[I[q]]);keyOf.set(U[q],r);left=left.filter(x=>x!==U[q]);freeT=freeT.filter(x=>x!==I[q])}}}
 else{const SF=fmSnap(fx,fy,shape==='box'),ax=-SF[1],ay=SF[0],L=units.slice(),kf=u=>(u.x-cx)*SF[0]+(u.y-cy)*SF[1],ka=u=>(u.x-cx)*ax+(u.y-cy)*ay;   /* along the shape's own rows (Formations.dm) */
  fmSortBy(L,L.map(u=>-kf(u)),L.map(ka));
  const shapeTiles=[];for(const p of points){const i=ordered.indexOf(p);if(i>=0&&i<tiles.length)shapeTiles.push(tiles[i])}
  /* row by row: each row of slots the next units, front first, each the slot across from it (Formations.dm) */const per=fmShapePer(shape,n,width),m=Math.min(L.length,shapeTiles.length);
  for(let i0=0;i0<m;i0+=per){const RU=L.slice(i0,Math.min(i0+per,m)),RT=shapeTiles.slice(i0,Math.min(i0+per,m));fmSortBy(RU,RU.map(ka));fmSortBy(RT,RT.map(t=>(t[0]-mx)*ax+(t[1]-my)*ay));for(let q=0;q<RU.length;q++)assign.set(RU[q],RT[q])}}
 // no two routes cross (Formations.dm RemasterUncross): every pair up to 60 units; more, none (they walk through their own)
 const who=[...assign.keys()],nw=who.length,dist=(u,t)=>Math.hypot(t[0]-u.x,t[1]-u.y),S=who.map(u=>assign.get(u)),K=who.map(u=>keyOf.get(u)),cell=nw>60?new Map():null;
 if(nw<=60){
 if(cell)S.forEach((t,i)=>{const k=t[0]+','+t[1];if(!cell.has(k))cell.set(k,[]);cell.get(k).push(i)});
 for(let pass=0;pass<6;pass++){let sw=false;for(let a=0;a<nw;a++){const cand=[];if(!cell){for(let b=a+1;b<nw;b++)cand.push(b)}else{const [x,y]=S[a];for(let dx=-2;dx<=2;dx++)for(let dy=-2;dy<=2;dy++){const L=cell.get((x+dx)+','+(y+dy));if(L)for(const b of L)if(b>a)cand.push(b)}cand.sort((p,q)=>p-q)}
  for(const b of cand){if(K[a]!==K[b])continue;const TA=S[a],TB=S[b],now=dist(who[a],TA)+dist(who[b],TB),then=dist(who[a],TB)+dist(who[b],TA);if(then<now-0.01||(then<now+0.01&&fmSegCross(who[a].x,who[a].y,TA[0],TA[1],who[b].x,who[b].y,TB[0],TB[1]))){S[a]=TB;S[b]=TA;if(cell){const LA=cell.get(TA[0]+','+TA[1]),LB=cell.get(TB[0]+','+TB[1]);LA[LA.indexOf(a)]=b;LB[LB.indexOf(b)]=a}sw=true}}}if(!sw)break}
 who.forEach((u,i)=>assign.set(u,S[i]))}
 return {fx,fy,s:who.map(u=>({ref:u.ref,x:assign.get(u)[0],y:assign.get(u)[1]}))}}
// A new order for these units: their markers in older sets go (a Shift-queued leg keeps them).
function fmDrop(refs){const R=new Set(refs);for(const S of FM.sets)S.s=S.s.filter(e=>!R.has(e.ref)||e.arr);FM.sets=FM.sets.filter(S=>S.s.length)}
function fmClick(e,t,tile){const L=RF.last,k=L&&L.k;if(!k||k==='select'||k==='deny'||k==='use')return;const sel=fmSel(),queued=!!(e&&e.shiftKey||model&&model.queue);if(!queued)fmDrop(sel.map(u=>u.ref));
 if(!((k==='move'||k==='attack')&&!t)||sel.length<2||tile.up)return;const t0=performance.now(),P=fmPredict(tile.x,tile.y,sel,model&&model.formation);FM.cost=performance.now()-t0;if(!P)return;
 const now=performance.now();if(k==='move'&&!queued)FM.lastMove={x:tile.x,y:tile.y,at:now};FM.sets.push({id:null,pred:true,kind:k==='attack'?'attack':'move',at:now,q:queued,fx:P.fx,fy:P.fy,z:V3.z,s:P.s.map(s=>({ref:s.ref,x:s.x,y:s.y,px:s.x,py:s.y,t0:now,born:now,arr:0}))});FM.predicted++;if(FM.sets.length>8)FM.sets.shift()}
// The game's slots for a group (Formations.dm RemasterSlotsPush): {id, kind, f:[fx,fy], q, s:[[ref,x,y,z],...]}.
window.rmSlots3D=function(raw){try{const D=JSON.parse(typeof raw==='string'?raw:JSON.stringify(raw));if(!D||!Array.isArray(D.s))return;FM.lastPush=D;const now=performance.now(),refs=D.s.map(r=>r[0]);
 let S=FM.sets.find(x=>x.id===D.id);if(!S)S=FM.sets.find(x=>x.pred&&x.kind===D.kind&&now-x.at<3000&&x.s.some(e=>refs.includes(e.ref)));
 if(!D.q){const R=new Set(refs);for(const O of FM.sets)if(O!==S)O.s=O.s.filter(e=>!R.has(e.ref)||e.arr)}
 if(!S){S={id:D.id,pred:false,kind:D.kind,at:now,q:!!D.q,s:[]};FM.sets.push(S)}const was=S.pred;S.id=D.id;S.pred=false;if(Array.isArray(D.f)){S.fx=D.f[0];S.fy=D.f[1]}
 const old=new Map(S.s.map(e=>[e.ref,e]));let moved=0,added=0;S.s=D.s.map(r=>{const e=old.get(r[0]);if(e){if(e.x!==r[1]||e.y!==r[2]){const p=fmPos(e,now);e.px=p[0];e.py=p[1];e.t0=now;e.x=r[1];e.y=r[2];moved++}e.z=r[3];return e}added++;return {ref:r[0],x:r[1],y:r[2],z:r[3],px:r[1],py:r[2],t0:now,born:now,arr:0}});
 if(was)FM.lastCheck={n:D.s.length,moved,added,dropped:Math.max(0,old.size-(D.s.length-added))};
 FM.sets=FM.sets.filter(x=>x.s.length);FM.confirmed++}catch(err){console.error(err)}};
function fmPos(e,now){const k=fmEase((now-e.t0)/160);return [e.px+(e.x-e.px)*k,e.py+(e.y-e.py)*k]}
// Each frame (with rts-feel's pings): a square on each slot; it drops in when shown and shrinks away once its unit
// stands there (or after 40 s). It fades out with the order lines (V3LINE_HOLD/V3LINE_FADE, the user 10-25: "the placement
// grid ... fade away as well"), and Shift shows it again while its unit is still on the way. Drawn blended: into FM.blend,
// which the main script's order pass draws (a frame behind; the frame's own geometry here has no alpha).
function fmDraw(a){const now=performance.now(),B=FM.blend||(FM.blend=[]);B.length=0;if(!FM.sets.length)return;const by=new Map();for(const t of V3.things)if(t.ref)by.set(t.ref,t);
 const sh=typeof v3lineShift!=='undefined'&&v3lineShift,LH=typeof V3LINE_HOLD!=='undefined'?V3LINE_HOLD:250,LF=typeof V3LINE_FADE!=='undefined'?V3LINE_FADE:1500;
 for(const S of FM.sets){const c=FM_COL[S.kind]||FM_COL.move;
  for(const e of S.s){const u=by.get(e.ref);if(!e.arr&&u&&u.x===e.x&&u.y===e.y)e.arr=now;if(!e.arr&&(!u||now-e.born>40000))e.arr=now;if(e.z!=null&&e.z!==V3.z)continue;
   const age=now-e.born,la=sh&&!e.arr?1:age<LH?1:Math.max(0,1-(age-LH)/(LF-LH));if(la<=0)continue;
   const fade=e.arr?Math.min(1,(now-e.arr)/450):0;if(fade>=1)continue;const pop=Math.min(1,(now-e.born)/200),p=fmPos(e,now),X=p[0],Z=-p[1],Y=(typeof rfY==='function'?rfY(Math.round(p[0]),Math.round(p[1])):v3groundAt(Math.round(p[0]),Math.round(p[1]))+0.05)+0.006;
   // the order queue's own square (the main script's v3queues outline: edges 0.47 from the middle, 0.09 wide), so a slot
   // looks like any other order's target: it drops in from a little larger and shrinks away once its unit stands there
   const k=(1.12-0.12*fmEase(pop))*(1-fade*0.4),h=0.515*k,w=0.09*k,cc=rfLit(c,(S.pred?0.95:1)+fade*0.5);cc[3]=la;
   rfSquare(B,X,Y,Z,h,w,cc)}
  S.s=S.s.filter(e=>!e.arr||now-e.arr<450)}
 FM.sets=FM.sets.filter(S=>S.s.length)}
if(typeof rfClick==='function'){const rfClick0=rfClick;rfClick=function(e,t,tile){
 if(t&&t.kind==='mine'&&t.ref&&(e.ctrlKey||e.metaKey)&&!V3.build&&!V3.shop&&fmGroupOf(t.ref)){fmCtrlPick(t,e.shiftKey);return true}   // Ctrl-click on a grouped unit: its group (below)
 const r=rfClick0.apply(this,arguments);if(!r)try{fmClick(e,t,tile)}catch(err){console.error(err)}return r}}
function fmHasSlot(x,y){for(const S of FM.sets)for(const e of S.s)if(!e.arr&&e.x===x&&e.y===y&&(e.z==null||e.z===V3.z))return true;return false}
// The order queue's outlines (the main script's v3queues loop) ask rfQueueDig whether a target's mark is drawn elsewhere
// (a dig's is on the rock face): a group move's slot has its marker, so it gets no square; the line still ends there.
if(typeof rfQueueDig==='function'){const rfQueueDig0=rfQueueDig;rfQueueDig=function(hl,t){const r=rfQueueDig0.apply(this,arguments);if(r)return r;try{if(t&&/^move$/i.test(t.kind||'')&&fmHasSlot(t.x,t.y))return [t.x,-t.y]}catch(err){}return r}}
if(typeof rfDraw==='function'){const rfDraw0=rfDraw;rfDraw=function(a){rfDraw0(a);try{fmAtkDraw(a);fmFaceDraw(a)}catch(err){if(!FM.errA){FM.errA=1;console.error(err)}}try{const t0=performance.now();fmDraw(a);const c=performance.now()-t0;FM.costDraw=FM.costDraw==null?c:FM.costDraw*0.95+c*0.05}catch(err){if(!FM.err){FM.err=1;console.error(err)}}}}
// Army › Formations: your own formations (hud-craft's Army page calls fmArmyEditor(el, model) on every HUD update while
// that tab is open; el is #armyFormEditor). Up to four, each with a name. Pick a brush (Front, Ranged, Mage, Any) and
// click squares to paint them; a click with the same brush, or Erase, clears one. In a move each of your people takes a
// square of its role by what it holds then: a melee weapon or claws the front ones, a bow the ranged ones, a caster
// (its own gift or a weapon with mana) the mage ones; anyone else, and those left over, the rest. The gold square is
// the tile you click; the top is the front, the way they march. Sent as formationsave / formationuse / formationdel
// (Formations.dm; squares split by "/": BYOND splits a command's params on ";"), kept in the player's save.
const FMA={list:null,cur:0,brush:'front',at:0,timer:0,R:5,F:4,B:6};
const FMA_RL={front:['Front','hcg-sword','⚔','those with a melee weapon or claws'],ranged:['Ranged','hcg-fmr','➶','those with a bow'],mage:['Mage','hcg-spark','✦','those who cast: their own gift or a weapon with mana'],any:['Any','','','whoever is left']};
function fmaFromModel(m){return arr(m&&m.formations).map(F=>({name:String(F.name||''),cells:new Map(arr(F.cells).map(c=>[c[0]+','+c[1],FM_ROLES.includes(c[2])?c[2]:'any']))}))}
function fmaSave(i){clearTimeout(FMA.timer);FMA.at=performance.now();FMA.timer=setTimeout(()=>{FMA.timer=0;const F=FMA.list[i];if(!F)return;const name=F.name.replace(/[|;\/<>&=]/g,'').slice(0,24);
 send('formationsave',(i+1)+'|'+name+'|'+[...F.cells].map(([k,r])=>k+','+r).join('/'))},300)}
function fmaStyle(){if(document.getElementById('fmaStyle'))return;const st=document.createElement('style');st.id='fmaStyle';st.textContent=
 /* text at 11.25 px at least: WebKit draws none under 9 px on screen, and the HUD is at 0.8 at 1280x720 (STYLE.md) */
 'body.overlay .fma{margin:4px 0 6px;padding:10px 12px 12px;background:rgba(0,0,0,.22);border:1px solid color-mix(in srgb,var(--mband,#5d4a2a) 80%,transparent);border-radius:3px}'+
 'body.overlay .fma-h b{display:block;font:15px/1.2 var(--mfont,Georgia),HudText,Georgia,serif;color:var(--macc,#e0b85a)}'+
 'body.overlay .fma-h small{display:block;margin-top:2px;font-size:11.25px;line-height:1.35;color:color-mix(in srgb,var(--mink,#e8dcb8) 82%,transparent)}'+
 'body.overlay .fma-row{display:flex;flex-wrap:wrap;align-items:center;gap:5px;margin-top:8px}'+
 'body.overlay .fma-row>span{min-width:44px;font-size:11.25px;color:color-mix(in srgb,var(--mink,#e8dcb8) 75%,transparent)}'+
 'body.overlay .fma-row button{min-height:24px!important;padding:0 9px!important;font-size:11.25px}'+
 'body.overlay .fma-row input{flex:1 1 120px;min-width:0;height:24px;box-sizing:border-box;padding:0 8px;font:11.25px HudText,Georgia,serif;color:var(--mink,#e8dcb8);background:rgba(0,0,0,.4);border:1px solid color-mix(in srgb,var(--mband,#5d4a2a) 90%,transparent);border-radius:2px}'+
 'body.overlay .fma-row input:focus{outline:2px solid var(--macc,#e0b85a);outline-offset:0}'+
 'body.overlay .fma-row button .fmsw{display:inline-block;width:10px;height:10px;margin-right:5px;vertical-align:-1px;background:var(--rc);border:1px solid rgba(0,0,0,.5)}'+
 'body.overlay .fma-board{display:grid;justify-content:center;margin:10px 0 6px;row-gap:3px}'+
 'body.overlay .fma-edge{font-size:11.25px;letter-spacing:.06em;text-transform:uppercase;text-align:center;color:color-mix(in srgb,var(--mink,#e8dcb8) 70%,transparent)}'+
 'body.overlay .fma-grid{display:grid;grid-template-columns:repeat(var(--c),22px);grid-auto-rows:22px;gap:2px}'+
 'body.overlay .fma-grid button{all:unset;box-sizing:border-box;width:22px;height:22px;display:grid;place-items:center;cursor:pointer;color:#14110c;'+
  'background:rgba(0,0,0,.32);border:1px solid color-mix(in srgb,var(--mband,#5d4a2a) 85%,transparent)}'+
 'body.overlay .fma-grid button:hover{border-color:var(--macc,#e0b85a)}'+
 'body.overlay .fma-grid button:focus-visible{outline:2px solid var(--macc,#e0b85a);outline-offset:1px}'+
 'body.overlay .fma-grid button.on{background:var(--rc);border-color:color-mix(in srgb,var(--rc) 60%,#fff)}'+
 'body.overlay .fma-grid button.anchor{box-shadow:inset 0 0 0 2px var(--macc,#e0b85a)}'+
 'body.overlay .fma-grid button.anchor:not(.on){background:color-mix(in srgb,var(--macc,#e0b85a) 22%,rgba(0,0,0,.32))}'+
 'body.overlay .fma-grid b.hcg{width:12px!important;height:12px!important;margin:0!important;color:#14110c}'+
 'body.overlay .hcg-fmr{--ico:var(--hci-arrow);transform:rotate(-90deg)}'+
 'body.overlay .fma{--r-front:#d9a441;--r-ranged:#79b85a;--r-mage:#a884e0;--r-any:#9aa4ae}'+
 'body.overlay.cb .fma{--r-front:#e69f00;--r-ranged:#56b4e9;--r-mage:#cc79a7;--r-any:#a8a29a}'+
 'body.overlay .fma-sum{margin-top:6px;font-size:11.25px;line-height:1.35;font-variant-numeric:lining-nums tabular-nums;color:color-mix(in srgb,var(--mink,#e8dcb8) 80%,transparent)}';
 document.head.appendChild(st)}
function fmArmyEditor(el,m){fmaStyle();const now=performance.now();
 if(!FMA.list||(!FMA.timer&&now-FMA.at>1500)){const L=fmaFromModel(m),same=FMA.list&&JSON.stringify(FMA.list.map(F=>[F.name,[...F.cells]]))===JSON.stringify(L.map(F=>[F.name,[...F.cells]]));if(!same){FMA.list=L;el.dataset.fmKey=''}}
 if(FMA.cur>=FMA.list.length)FMA.cur=Math.max(0,FMA.list.length-1);
 const inUse=m&&m.formation==='custom'?(m.formationMine||1)-1:-1,sel=fmSel(),F=FMA.list[FMA.cur],focus=el.contains(document.activeElement)&&document.activeElement.tagName==='INPUT';
 const key=JSON.stringify([FMA.list.map(F=>[F.name,[...F.cells]]),FMA.cur,FMA.brush,inUse,sel.map(u=>fmRoleOf(u.ref))]);if(el.dataset.fmKey===key||focus)return;el.dataset.fmKey=key;
 const rc=r=>'--rc:var(--r-'+r+')',icon=r=>FMA_RL[r][1]?'<b class="hcg '+FMA_RL[r][1]+'">'+FMA_RL[r][2]+'</b>':'';
 let html='<div class="fma"><div class="fma-h"><b>Your own formations</b><small>Build your own: pick a brush and click the squares where your people should stand. Each takes a square of its role by what it holds: Front for a melee weapon, Ranged for a bow, Mage for a caster; Any squares take whoever is left. The gold square is the tile you click (left empty, the nearest square goes there); the top is the front.</small></div>';
 html+='<div class="fma-row" role="group" aria-label="Your formations"><span>Yours</span>'+FMA.list.map((G,i)=>'<button type="button" data-fma="pick" data-i="'+i+'" aria-pressed="'+(i===FMA.cur)+'" title="'+esc((G.name||'Formation '+(i+1))+'\n'+G.cells.size+' squares'+(i===inUse?' · in use':'')+'\nClick: edit it')+'">'+esc(G.name||'Formation '+(i+1))+(i===inUse?' ✓':'')+'</button>').join('')+(FMA.list.length<4?'<button type="button" data-fma="new" title="New formation\nUp to four of your own.">+ New</button>':'')+'</div>';
 if(!F){el.innerHTML=html+'<div class="fma-sum">No formations yet. “+ New” starts one.</div></div>';fmaWire(el);return}
 html+='<div class="fma-row"><span>Name</span><input type="text" maxlength="24" data-fma="name" value="'+esc(F.name)+'" aria-label="Formation name"></div>';
 html+='<div class="fma-row" role="group" aria-label="Brush"><span>Paint</span>'+['front','ranged','mage','any'].map(r=>'<button type="button" data-fma="brush" data-r="'+r+'" aria-pressed="'+(FMA.brush===r)+'" style="'+rc(r)+'" title="'+esc(FMA_RL[r][0]+'\nSquares for '+FMA_RL[r][3]+'.')+'"><i class="fmsw"></i>'+FMA_RL[r][0]+'</button>').join('')+'<button type="button" data-fma="brush" data-r="erase" aria-pressed="'+(FMA.brush==='erase')+'" title="Erase\nClick squares to clear them.">Erase</button></div>';
 const cols=FMA.R*2+1;let cells='';for(let y=FMA.F;y>=-FMA.B;y--)for(let x=-FMA.R;x<=FMA.R;x++){const k=x+','+y,r=F.cells.get(k),anc=x===0&&y===0;
  cells+='<button type="button" data-fmc="'+k+'" class="'+(r?'on':'')+(anc?' anchor':'')+'"'+(r?' data-r="'+r+'" style="'+rc(r)+'"':'')+' aria-pressed="'+!!r+'" aria-label="'+esc((r?FMA_RL[r][0]+' square':'Empty square')+(anc?', the tile you click':''))+'" title="'+esc((anc?'The tile you click':'A square '+(y>0?y+' ahead':y<0?(-y)+' behind':'beside')+(x?', '+Math.abs(x)+(x>0?' right':' left'):''))+(r?'\n'+FMA_RL[r][0]+': '+FMA_RL[r][3]:'')+'\nClick: '+(FMA.brush==='erase'||r===FMA.brush?'clear it':'paint it '+FMA_RL[FMA.brush][0]))+'">'+(r?icon(r):'')+'</button>'}
 html+='<div class="fma-board"><div class="fma-edge">Front</div><div class="fma-grid" style="--c:'+cols+'">'+cells+'</div><div class="fma-edge">Back</div></div>';
 const cnt={front:0,ranged:0,mage:0,any:0},have={front:0,ranged:0,mage:0,any:0};for(const r of F.cells.values())cnt[r]++;for(const u of sel)have[fmRoleOf(u.ref)]++;
 const list=o=>['front','ranged','mage','any'].filter(r=>o[r]).map(r=>o[r]+' '+FMA_RL[r][0].toLowerCase()).join(', ')||'none';
 html+='<div class="fma-sum">'+F.cells.size+' square'+(F.cells.size===1?'':'s')+': '+list(cnt)+(sel.length?' · selected: '+list(have):'')+'</div>';
 html+='<div class="fma-row"><button type="button" data-fma="use" aria-pressed="'+(FMA.cur===inUse)+'"'+(F.cells.size?'':' disabled')+' title="'+esc('Use this formation\nEvery group move you give next lines up like this.')+'">Use this formation</button>'+
  '<button type="button" data-fma="band"'+(sel.length>1?'':' disabled')+' title="'+esc('From my band\nCopy how the selected stand now (north at the top), each square painted by what they hold.'+(sel.length>1?'':'\nSelect two or more first.'))+'">From my band</button>'+
  '<button type="button" data-fma="clear"'+(F.cells.size?'':' disabled')+' title="Clear\nTake every square away.">Clear</button>'+
  '<button type="button" data-fma="del" title="Delete\nRemove this formation.">Delete</button></div>'+(m&&m.formationGroup?'<div class="fma-sum">The selection is control group '+m.formationGroup+': choosing a formation here gives group '+m.formationGroup+' its own.</div>':'')+'</div>';
 el.innerHTML=html;fmaWire(el)}
function fmaWire(el){if(el.dataset.fmWired)return;el.dataset.fmWired='1';
 el.addEventListener('input',e=>{const n=e.target.closest('[data-fma=name]');if(!n||!FMA.list[FMA.cur])return;FMA.list[FMA.cur].name=n.value.slice(0,24);const c=el.querySelector('[data-fma=pick][data-i="'+FMA.cur+'"]');if(c)c.textContent=FMA.list[FMA.cur].name||'Formation '+(FMA.cur+1);FMA.at=performance.now()});
 el.addEventListener('change',e=>{const n=e.target.closest('[data-fma=name]');if(!n||!FMA.list[FMA.cur])return;FMA.list[FMA.cur].name=n.value.slice(0,24);fmaSave(FMA.cur)});
 el.addEventListener('click',e=>{const c=e.target.closest('[data-fmc]'),b=e.target.closest('button[data-fma]');if(!c&&!b)return;const F=FMA.list[FMA.cur];
  if(c){if(!F)return;const k=c.dataset.fmc,r=F.cells.get(k);if(FMA.brush==='erase'||r===FMA.brush)F.cells.delete(k);else if(F.cells.size<60||r)F.cells.set(k,FMA.brush);fmaSave(FMA.cur)}
  else{const a=b.dataset.fma;
   if(a==='pick')FMA.cur=+b.dataset.i;
   else if(a==='brush')FMA.brush=b.dataset.r;
   else if(a==='new'){if(FMA.list.length>=4)return;FMA.list.push({name:'Formation '+(FMA.list.length+1),cells:new Map()});FMA.cur=FMA.list.length-1;fmaSave(FMA.cur)}
   else if(a==='clear'&&F){F.cells.clear();fmaSave(FMA.cur)}
   else if(a==='del'&&F){FMA.list.splice(FMA.cur,1);FMA.at=performance.now();send('formationdel',String(FMA.cur+1));FMA.cur=Math.max(0,FMA.cur-1)}
   else if(a==='use'&&F){FMA.at=performance.now();clearTimeout(FMA.timer);if(FMA.timer){FMA.timer=0;const name=F.name.replace(/[|;\/<>&=]/g,'').slice(0,24);send('formationsave',(FMA.cur+1)+'|'+name+'|'+[...F.cells].map(([k,r])=>k+','+r).join('/'))}send('formationuse',String(FMA.cur+1))}
   else if(a==='band'&&F){const U=fmSel();if(U.length<2)return;let cx=0,cy=0;for(const u of U){cx+=u.x;cy+=u.y}cx/=U.length;cy/=U.length;
    let mid=null,md=Infinity;for(const u of U){const d=((u.x-cx)**2+(u.y-cy)**2)*10000-u.y*100+u.x;if(d<md){md=d;mid=u}}
    F.cells=new Map();for(const u of U){const x=u.x-mid.x,y=u.y-mid.y;if(Math.abs(x)<=FMA.R&&y<=FMA.F&&y>=-FMA.B)F.cells.set(x+','+y,fmRoleOf(u.ref))}fmaSave(FMA.cur)}
   else return}
  e.preventDefault();e.stopPropagation();el.dataset.fmKey='';fmArmyEditor(el,model)})}
window.fmArmyEditor=fmArmyEditor;
// Attack box (the user, 12:4x): Attack (A), then a drag over the map, as a box selects your own: it takes every foe it
// touches. While you drag, the box is red, each foe in it is ringed red, and the pointer is a red box; let go and they
// flash and the selected units share them out (Formations.dm RemasterAttackBox: the fewest-attacked, nearest first;
// archers and casters spread wider; on to the next when one falls, until the box is empty). A click without a drag in
// Attack mode still goes for the one foe clicked (or attack-moves to the ground).
function fmFoe(t){return t.dx!=null&&!t.ly&&(t.kind==='npc'&&!t.peace||t.kind==='player'&&t.war)&&(typeof v3visible!=='function'||v3visible(t))}
function fmBoxFoes(x0,y0,x1,y1){const c=$('world3d'),r=c.getBoundingClientRect(),l=Math.min(x0,x1)-r.left,h=Math.max(x0,x1)-r.left,tp=Math.min(y0,y1)-r.top,b=Math.max(y0,y1)-r.top,L=V3.lean||[0,1,0];
 return V3.things.filter(fmFoe).filter(u=>{const g=v3groundAt(u.dx,u.dy),H=(u.ih||1)*(u.sc||1)*0.9*(u.beast?(u.beast.size||1):1),A=v3project([u.dx,g+0.08,-u.dy]),B=v3project([u.dx+L[0]*H,g+0.08+L[1]*H,-u.dy+L[2]*H]);if(!A||!B)return false;
  /* the picture's axis on screen against the box (Liang-Barsky clip, as rts-feel's own box) */let t0=0,t1=1;const dx=B[0]-A[0],dy=B[1]-A[1];
  for(const [pp,qq] of [[-dx,A[0]-l],[dx,h-A[0]],[-dy,A[1]-tp],[dy,b-A[1]]]){if(pp===0){if(qq<0)return false}else{const k=qq/pp;if(pp<0){if(k>t1)return false;if(k>t0)t0=k}else{if(k<t0)return false;if(k<t1)t1=k}}}return t0<=t1})}
function fmAtkCursor(){if(FM.atkCur)return FM.atkCur;try{const c=document.createElement('canvas');c.width=c.height=32;const g=c.getContext('2d');g.lineCap='square';
 const br=(w,col)=>{g.strokeStyle=col;g.lineWidth=w;g.beginPath();for(const [x,y,sx,sy] of [[4,4,1,1],[28,4,-1,1],[4,28,1,-1],[28,28,-1,-1]]){g.moveTo(x,y+sy*8);g.lineTo(x,y);g.lineTo(x+sx*8,y)}g.stroke()};
 br(5,'#2a0806');br(2.4,'#ff5a45');g.fillStyle='#2a0806';g.fillRect(13.5,13.5,5,5);g.fillStyle='#ff5a45';g.fillRect(14.5,14.5,3,3);
 FM.atkCur='url('+c.toDataURL()+') 16 16, crosshair'}catch(e){FM.atkCur='crosshair'}return FM.atkCur}
addEventListener('mousemove',e=>{const d=V3.drag;if(!d||d.b!==0||!d.box||!d.moved||!V3.on||!(model&&model.attackMode)){if(FM.atkBox){FM.atkBox=null;if(typeof RF!=='undefined')RF.cur=''}return}
 FM.atkBox=[d.x,d.y,mx(e),my(e)];const c=$('world3d');if(c)c.style.cursor=fmAtkCursor()});
addEventListener('mouseup',e=>{const d=V3.drag;if(!d||d.b!==0||!d.box||!d.moved||!V3.on||!(model&&model.attackMode))return;
 {const z=hudKC();if(Math.abs(mx(e)-d.x)*z<16&&Math.abs(my(e)-d.y)*z<16){FM.atkBox=null;return}}   // a small slip is a click (as rts-feel's own box)
 const F=fmBoxFoes(d.x,d.y,mx(e),my(e));FM.atkBox=null;V3.drag=null;$('box3d').hidden=true;if(typeof RF!=='undefined')RF.cur='';e.stopImmediatePropagation();fmGameFocus();
 const now=performance.now();FM.lastBox={n:F.length,ids:F.map(t=>t.id||t.ref),at:now};
 if(!F.length){if(typeof toast==='function')toast('No foes in the box. Drag over them, or click one.');try{if(typeof rfSfx==='function')rfSfx('deny')}catch(err){}return}
 for(const t of F)if(typeof RF!=='undefined')RF.flashes.push({key:t.key,k:'attack',at:now});
 send('attackbox',F.map(t=>t.id||t.ref).join(','));try{if(window.rmSfx&&rmSfx.order)rmSfx.order('attack',{x:F[0].x,y:F[0].y})}catch(err){}},true);
function fmAtkDraw(a){const on=!!(model&&model.attackMode);if(on!==FM.atk){FM.atk=on;document.body.classList.toggle('fm-atk',on)}if(!FM.atkBox)return;
 const B=FM.atkBox,c=[1,0.33,0.24,1];for(const t of fmBoxFoes(B[0],B[1],B[2],B[3])){const X=t.dx,Z=-t.dy,Y=v3groundAt(Math.round(t.dx),Math.round(t.dy))+0.03,R=0.42*(t.beast?(t.beast.size||1):1);rfRing(a,X,Y,Z,R,0.06,c,24)}}
{const st=document.createElement('style');st.textContent='body.fm-atk #box3d{border-color:#ff5a45;background:rgba(255,90,69,.14)}body.fm-atk.cb #box3d{border-color:#d55e00;background:rgba(213,94,0,.14)}';document.head.appendChild(st)}
// Drag to face (the user, 13:1x and 13:5x): with two or more selected, click to move, then press on that spot again within
// 1.5 s and drag; or in one go, press on open ground with Cmd (on a Mac) or Ctrl and the left button, or the right button
// when Settings → right-click gives orders, and drag before letting go. The pressed tile is where
// they go, the drag's direction is the way they face, its length how wide the front row is (one tile of drag: three
// abreast, then two more a tile). The squares where each will stand follow the pointer; letting go gives the order
// (formmove, Formations.dm RemasterFormMove). A drag of under half a tile is the plain click or right-click it was.
function fmFaceStart(e){if(!V3.on||e.target!==$('world3d')||!model||model.attackMode||model.mode||V3.build||V3.shop||V3.aim||model.useon)return false;
 // on a Mac, Ctrl with the left button arrives as the right button (the system's right-click): that counts as Ctrl too
 const ctrl=(e.button===0&&(e.ctrlKey||e.metaKey))||(e.button===2&&e.ctrlKey),right=e.button===2&&typeof RF!=='undefined'&&RF.rclick;
 const sel=fmSel();if(sel.length<2)return false;const t=v3pickThing(mx(e),my(e));if(t)return false;const tile=v3pickTile(mx(e),my(e));if(!tile||tile.up||tile.roof)return false;
 // the user's way (13:5x): click to move, then press on that spot again within 1.5 s and drag: the order just given turns
 const L=FM.lastMove,again=e.button===0&&!e.shiftKey&&!ctrl&&L&&performance.now()-L.at<1500&&Math.max(Math.abs(tile.x-L.x),Math.abs(tile.y-L.y))<=1;
 if(!ctrl&&!right&&!again)return false;const at=again?L:tile;
 const K=v3kindAt(at.x,at.y);if(!K||!FM_WALK.has(K.kind))return false;FM.face={x:at.x,y:at.y,sx:mx(e),sy:my(e),btn:e.button,on:false,shift:!!e.shiftKey,P:null,again:!!again};return true}
function fmFaceAt(e){const F=FM.face,tile=v3pickTile(mx(e),my(e));if(!tile)return;const dx=tile.x-F.x,dy=tile.y-F.y,len=Math.max(Math.abs(dx),Math.abs(dy));
 if(!F.on&&Math.hypot(mx(e)-F.sx,my(e)-F.sy)*hudKC()<14)return;if(!len){F.P=null;F.fx=F.fy=0;return}F.on=true;
 const sel=fmSel();F.fx=dx;F.fy=dy;F.width=Math.min(sel.length,1+2*len);F.P=fmPredict(F.x,F.y,sel,model&&model.formation,{fx:dx,fy:dy,width:F.width})}
addEventListener('mousedown',e=>{FM.face=null;try{fmFaceStart(e)}catch(err){FM.face=null}},true);
addEventListener('mousemove',e=>{const F=FM.face;if(!F)return;if(!V3.drag){FM.face=null;return}try{fmFaceAt(e)}catch(err){}
 e.stopImmediatePropagation();const b=$('box3d');if(b)b.hidden=true;if(V3.drag)V3.drag.moved=false},true);   /* from the first move: no camera pan, no selection box */
addEventListener('mouseup',e=>{const F=FM.face;FM.face=null;if(!F||!F.on||e.button!==F.btn)return;FM.faceEnd=performance.now();e.stopImmediatePropagation();fmGameFocus();V3.drag=null;const b=$('box3d');if(b)b.hidden=true;
 if(!F.P||!(F.fx||F.fy))return;const sel=fmSel(),queued=F.shift||!!(model&&model.queue),now=performance.now();if(!queued)fmDrop(sel.map(u=>u.ref));
 FM.sets.push({id:null,pred:true,kind:'move',at:now,q:queued,fx:F.P.fx,fy:F.P.fy,z:V3.z,s:F.P.s.map(s=>({ref:s.ref,x:s.x,y:s.y,px:s.x,py:s.y,t0:now,born:now,arr:0}))});FM.predicted++;
 if(typeof RF!=='undefined'){RF.pings.push({x:F.x,y:F.y,k:'move',at:now});RF.last={at:now,fr:RF.fr,k:'move',x:F.x,y:F.y,drawn:0,shift:queued}}
 send('formmove',F.x+'|'+F.y+'|'+F.fx+'|'+F.fy+'|'+F.width+'|'+(queued?'1':'0'));FM.lastFace={x:F.x,y:F.y,fx:F.fx,fy:F.fy,width:F.width,n:F.P.s.length};
 try{if(window.rmSfx&&rmSfx.order)rmSfx.order('move',{x:F.x,y:F.y,queued})}catch(err){}},true);
// stop the right-click menu after a right-drag to face
addEventListener('contextmenu',e=>{if(FM.faceEnd&&performance.now()-FM.faceEnd<400){e.preventDefault();e.stopImmediatePropagation()}},true);
function fmFaceDraw(a){const F=FM.face;if(!F||!F.on||!F.P)return;const c=[0.62,0.95,0.6,1];for(const e of F.P.s){const X=e.x,Z=-e.y,Y=(typeof rfY==='function'?rfY(e.x,e.y):v3groundAt(e.x,e.y)+0.05)+0.006;rfSquare(a,X,Y,Z,0.47,0.07,c)}}
// After a drag of ours the keyboard goes back to the game, as the 3D view's own mouseup does after any click on the map
// (ours stops that event): without it Ctrl+2 and the other keys stayed with the page after a drag to face (real run, 15:1x).
function fmGameFocus(){setTimeout(()=>{try{if($('menu3d').hidden&&typeof gameFocus==='function')gameFocus()}catch(e){}},0)}
// Groups in the Company list (the user, 2026-10-23: "select units, right-click a unit in the Company list on the right and
// say Group, and that will be a group card we click and can expand"; "Ctrl+G to group up as well"; "Ctrl-click units on
// the screen and it will highlight all units in the group, and other groups"). A card per group above the Company rows:
// its number, how many, its own formation, their faces and health. Click: select them all (Shift, Ctrl or Cmd: add them);
// double-click: the camera there; the arrow: show their rows; right-click: select, add, ungroup. Grouped units' own rows
// fold into their card. Right-click a row: Group the selected (with it), select its group, take it out. Ctrl-click (Cmd)
// on a grouped unit in the world: its whole group; on one of another group then: that group too. Ctrl+G: group the
// selected. The game's side: Formations.dm RemasterGroupCommand ("fmgroup"); the groups are its numbered control groups.
const FMG={open:new Set(),items:[]};
try{for(const n of JSON.parse(localStorage.getItem('fm-gopen')||'[]'))FMG.open.add(+n)}catch(e){}
function fmGroups(){return arr(model&&model.controlGroups&&model.controlGroups.groups).filter(g=>g.count>0&&arr(g.refs).length)}
function fmGroupOf(ref){for(const g of fmGroups())if(arr(g.refs).includes(ref))return g.number;return 0}
function fmSelRefs(){return arr(model&&model.units).filter(u=>u.selected).map(u=>u.ref)}
// the selection is whole groups and nothing else (so a Ctrl-click on another group adds that one)
function fmSelIsGroups(){const S=fmSelRefs(),G=fmGroups();if(!S.length)return false;
 return S.every(r=>G.some(g=>arr(g.refs).includes(r)))&&G.every(g=>{const R=arr(g.refs),n=R.filter(r=>S.includes(r)).length;return n===0||n===R.length})}
function fmGroupPick(n,add){const g=fmGroups().find(x=>x.number===n);if(!g)return false;const refs=arr(g.refs);
 send('fmgroup','select|'+n+'|'+(add?'1':'0'));FM.lastGroupPick={n,add:!!add,at:performance.now()};
 try{if(typeof rfBoxFx==='function')rfBoxFx(refs,add);else if(typeof rfOptSelect==='function')rfOptSelect(refs,add?'add':'only');if(typeof rfSfx==='function')rfSfx('group-recall')}catch(e){}return true}   // the rings at once
// Ctrl-click (Cmd-click) on one of yours: its group when it has one, else (as before) all of its people on screen. A
// double-click still selects all of its people on screen, grouped or not.
function fmCtrlPick(t,add){const n=t&&t.ref?fmGroupOf(t.ref):0;if(!n)return typeof rfSelectAlike==='function'?rfSelectAlike(t,add):false;return fmGroupPick(n,add||fmSelIsGroups())}
// on a Mac a Ctrl-click arrives as the right button with Ctrl held: on one of yours it is that Ctrl-click, not the menu
addEventListener('mousedown',e=>{FM.cpick=null;if(e.button!==2||!e.ctrlKey||!V3.on||e.target!==$('world3d')||V3.build||V3.shop)return;const t=v3pickThing(mx(e),my(e));if(t&&t.kind==='mine'&&t.ref)FM.cpick={t,x:mx(e),y:my(e)}},true);
addEventListener('mouseup',e=>{const C=FM.cpick;FM.cpick=null;if(!C||e.button!==2||Math.hypot(mx(e)-C.x,my(e)-C.y)*hudKC()>6)return;e.stopImmediatePropagation();V3.drag=null;FM.faceEnd=performance.now();
 try{fmCtrlPick(C.t,e.shiftKey)}catch(err){console.error(err)}fmGameFocus()},true);
function fmGroupRender(){const roster=$('roster'),list=$('rosterList');if(!roster||!list||!model)return;let box=$('fmGroups');
 if(!box){box=document.createElement('div');box.id='fmGroups';box.setAttribute('role','list');box.setAttribute('aria-label','Groups');roster.insertBefore(box,list);fmGroupWire(box)}
 const G=fmGroups(),U=new Map(arr(model.units).map(u=>[u.ref,u])),inG=new Set();for(const g of G)for(const r of arr(g.refs))inG.add(r);
 for(const b of list.children){const h=!!(b.dataset&&inG.has(b.dataset.value));if(b.classList.contains('fm-ing')!==h)b.classList.toggle('fm-ing',h)}
 const hp=u=>Math.max(0,Math.min(100,Math.round(pct(u.hp,u.maxhp)||0)));
 const key=JSON.stringify([[...FMG.open].sort(),G.map(g=>[g.number,g.formation||'',arr(g.refs).map(r=>{const u=U.get(r)||{};return [r,u.name,!!u.selected,u.portrait,hp(u),unitStatus(u),!!u.combat]})])]);
 if(box.dataset.k===key)return;box.dataset.k=key;
 box.innerHTML=G.map(g=>{const M=arr(g.refs).map(r=>U.get(r)).filter(Boolean),all=M.length&&M.every(u=>u.selected),part=!all&&M.some(u=>u.selected),open=FMG.open.has(g.number),avg=M.length?Math.round(M.reduce((a,u)=>a+hp(u),0)/M.length):0,fight=M.some(u=>u.combat);
  const faces=M.slice(0,5).map(u=>'<img alt="" src="'+esc(u.portrait||'')+'">').join('')+(M.length>5?'<i>+'+(M.length-5)+'</i>':'');
  const tip='Group '+g.number+' · '+M.length+' unit'+(M.length===1?'':'s')+(g.formation?' · formation: '+g.formation:'')+'\n'+M.slice(0,8).map(u=>ownName(u.name)).join(', ')+(M.length>8?'…':'')+'\nClick: select them all and show who is in it (or press '+g.number+'). Shift-, Ctrl- or Cmd-click: add them to the selection.\nDouble-click: go there. The arrow: show or hide who is in it. Right-click: ungroup.';
  const rows=open?'<div class="fmg-m">'+M.map(u=>'<button type="button" class="member'+(u.selected?' sel':'')+(u.combat?' fighting':'')+'" data-do="select" data-value="'+esc(u.ref)+'" title="'+esc(ownName(u.name)+' · '+u.race+' · Lv '+u.level+'\n'+unitStatus(u)+'\nRight-click: take out of group '+g.number)+'"><img alt="" src="'+esc(u.portrait||'')+'"><div><div class="nm">'+esc(ownName(u.name))+'</div><div class="st">'+hcStatusHTML(unitStatus(u))+'</div><div class="hpbar"><span style="width:'+hp(u)+'%"></span></div></div></button>').join('')+'</div>':'';
  return '<div class="fmg'+(all?' sel':part?' part':'')+(open?' open':'')+(fight?' fighting':'')+'" role="listitem" data-fmg="'+g.number+'"><div class="fmg-h">'+
   '<button type="button" class="fmg-tw" data-fmgt="'+g.number+'" aria-expanded="'+open+'" title="'+(open?'Hide':'Show')+' who is in group '+g.number+'">'+(open?'▾':'▸')+'</button>'+
   '<button type="button" class="fmg-b" data-fmgs="'+g.number+'" title="'+esc(tip)+'"><span class="fmg-n"><b>Group '+g.number+'</b><small>'+M.length+(g.formation?' · '+esc(g.formation):'')+'</small></span><span class="fmg-f">'+faces+'</span><span class="hpbar"><span style="width:'+avg+'%"></span></span></button></div>'+rows+'</div>'}).join('');
 if(typeof queueRegions==='function')queueRegions()}
function fmGroupWire(box){
 box.addEventListener('click',e=>{const t=e.target.closest('[data-fmgt]');if(t){const n=+t.dataset.fmgt;if(FMG.open.has(n))FMG.open.delete(n);else FMG.open.add(n);try{localStorage.setItem('fm-gopen',JSON.stringify([...FMG.open]))}catch(_){}box.dataset.k='';fmGroupRender();return}
  // a click on a card selects the group and opens it to show who is in it (the user tried just that, 16:2x); the arrow closes it
  const b=e.target.closest('[data-fmgs]');if(b){const n=+b.dataset.fmgs;fmGroupPick(n,e.shiftKey||e.ctrlKey||e.metaKey);if(!FMG.open.has(n)){FMG.open.add(n);try{localStorage.setItem('fm-gopen',JSON.stringify([...FMG.open]))}catch(_){}box.dataset.k='';fmGroupRender()}fmGameFocus()}});
 box.addEventListener('dblclick',e=>{if(e.target.closest('[data-fmgs]')&&typeof rfJumpToSelection==='function')setTimeout(()=>{try{rfJumpToSelection()}catch(_){}},60)})}
function fmMenuClose(){const m=$('fmGroupMenu');if(m&&!m.hidden){m.hidden=true;if(typeof queueRegions==='function')queueRegions()}}
function fmMenuOpen(x,y,items){let m=$('fmGroupMenu');
 if(!m){m=document.createElement('div');m.id='fmGroupMenu';m.setAttribute('role','menu');m.hidden=true;document.body.append(m);
  m.addEventListener('click',e=>{const b=e.target.closest('button[data-fmm]');if(!b||b.disabled)return;const it=FMG.items[+b.dataset.fmm];fmMenuClose();try{if(it&&it.run)it.run()}catch(err){console.error(err)}fmGameFocus()})}
 FMG.items=items;m.innerHTML=items.map((it,i)=>'<button type="button" role="menuitem" data-fmm="'+i+'" title="'+esc(it.label+(it.tip?'\n'+it.tip:''))+'">'+esc(it.label)+'</button>').join('');m.hidden=false;
 const W=innerWidth/hudKC(),H=innerHeight/hudKC(),r=m.getBoundingClientRect(),w=r.width/hudKC(),h=r.height/hudKC();m.style.left=Math.max(4,Math.min(x,W-w-4))+'px';m.style.top=Math.max(4,Math.min(y,H-h-4))+'px';
 if(typeof queueRegions==='function')queueRegions();const f=m.querySelector('button');if(f)f.focus({preventScroll:true})}
addEventListener('contextmenu',e=>{const el=e.target.closest&&e.target.closest('#roster .member[data-do=select],#fmGroups [data-fmgs]');if(!el||e.ctrlKey)return;e.preventDefault();e.stopImmediatePropagation();
 if(el.dataset.fmgs){const n=+el.dataset.fmgs;fmMenuOpen(mx(e),my(e),[
   {label:'Select group '+n,tip:'All of group '+n+' selected (or press '+n+').',run:()=>fmGroupPick(n,false)},
   {label:'Add group '+n+' to the selection',tip:'With the units already selected (or Ctrl-click one of them).',run:()=>fmGroupPick(n,true)},
   {label:'Ungroup',tip:'Group '+n+' ends; its units go back to the Company list.',run:()=>send('fmgroup','ungroup|'+n)}]);return}
 const ref=el.dataset.value,n=fmGroupOf(ref),S=fmSelRefs(),inSel=S.includes(ref),cnt=S.length+(inSel?0:1),items=[];
 items.push({label:inSel?'Group the selected ('+cnt+')':S.length?'Group with the selected ('+cnt+')':'Group',tip:(inSel?'The selected units':S.length?'The selected units and this one':'This one')+' become a group of their own: a card at the top of the Company list to click and open. Ctrl+G does this too.',run:()=>{send('fmgroup','make|'+ref);try{if(typeof rfSfx==='function')rfSfx('group-set')}catch(_){}}});
 if(n){items.push({label:'Select group '+n,tip:'All of group '+n+' selected.',run:()=>fmGroupPick(n,false)});items.push({label:'Take out of group '+n,tip:'It goes back to the Company list; the rest stay group '+n+'.',run:()=>send('fmgroup','out|'+ref)})}
 fmMenuOpen(mx(e),my(e),items)},true);
addEventListener('mousedown',e=>{const m=$('fmGroupMenu');if(m&&!m.hidden&&!m.contains(e.target))fmMenuClose()},true);
addEventListener('keydown',e=>{if(e.key==='Escape'){fmMenuClose();return}
 if(e.code!=='KeyG'||!e.ctrlKey||e.metaKey||e.altKey||e.repeat||(e.target&&e.target.closest&&e.target.closest('input,select,textarea,[contenteditable]')))return;e.preventDefault();e.stopImmediatePropagation();
 if(!fmSelRefs().length){if(typeof toast==='function')toast('Select units first, then Ctrl+G makes them a group.');try{if(typeof rfSfx==='function')rfSfx('deny')}catch(_){}return}
 send('fmgroup','make|');try{if(typeof rfSfx==='function')rfSfx('group-set')}catch(_){}},true);
// The arrows in a unit's bag at a glance (the user, 16:3x: "the arrows in the bag of the unit"): a slot of their own just
// after their quiver in the bag bar: an arrow's picture and how many (red at none); its tip lists each kind.
function fmQuiverBadges(){const seen=new Set();
 for(const u of arr(model&&model.units))if(u.selected)for(const i of arr(u.items))if(i.arrows!=null){
  const b=document.querySelector('.bagbar .bagslot[data-bag="'+CSS.escape(i.ref)+'"]');if(!b)continue;seen.add(i.ref);
  let s=b.nextElementSibling;if(!s||!s.classList.contains('fmarrowslot')||s.dataset.q!==i.ref){s=document.createElement('span');s.className='bagslot fmarrowslot';s.dataset.q=i.ref;s.setAttribute('role','img');b.after(s)}
  const n=Number(i.arrows)||0,K=arr(i.arrowKinds),icon=(K.find(k=>k[2])||[])[2]||'',key=JSON.stringify([n,K]);
  if(s.dataset.k!==key){s.dataset.k=key;s.innerHTML=(icon?'<img alt="" src="'+esc(icon)+'">':'<b>➶</b>')+'<i class="bagcount'+(n?'':' none')+'">'+n+'</i>';
   const what=K.length?K.map(k=>itemLabel(k[0])+(k[1]>1?' ×'+k[1]:'')).join(', '):'none';
   s.title=(n?n+' arrow'+(n===1?'':'s'):'No arrows')+' in the '+itemLabel(i.name||'quiver')+(n?'\n'+what:'\nWith none, a bow can’t shoot: it fights with a blade or its fists.');s.setAttribute('aria-label',(n||'No')+' arrows')}
  if(/Arrows \d+/.test(b.title))b.title=b.title.replace(/Arrows \d+/,'Arrows '+n)}
 document.querySelectorAll('.bagbar .fmarrowslot').forEach(s=>{if(!seen.has(s.dataset.q)||!s.previousElementSibling||s.previousElementSibling.dataset.bag!==s.dataset.q)s.remove()})}
// Each group's supplies on the left (the user, 16:4x: "small group cards on the left that tell us the resources of each
// group; we look in the bag"): a small card per group under the top bar: its arrows, food, potions and bandages (the
// arrows red when it has archers and none left, the food when it has none). Click: select the group and open its
// combined bag (what its members carry, the same things together, who has how many in each one's tip); the arrow closes it.
const FMS={open:new Set()};try{for(const n of JSON.parse(localStorage.getItem('fm-sopen')||'[]'))FMS.open.add(+n)}catch(e){}
// The selection's own card at the top (the user, 10-24: "if we have a group highlighted we should have a card on the left
// similar to group cards where we can see the shared resources maybe health"): with two or more of yours selected, their
// health together, who is wounded, bleeding, hungry or tired, the same supplies and their combined bag (the game's
// model.selSupply, one pass over the selection, Formations.dm). A selection that is just one group shows on that
// group's card instead (highlighted). Every card shows its health too.
function fmSupplyRender(){let box=$('fmSupplies');const G=fmGroups().filter(g=>g.supply),SEL=model&&model.selSupply&&model.selSupply.supply?model.selSupply:null,selCard=SEL&&!SEL.group;
 if(!box){box=document.createElement('aside');box.id='fmSupplies';box.className='ovonly';box.setAttribute('aria-label','Supplies');document.body.append(box);
  const keep=()=>{try{localStorage.setItem('fm-sopen',JSON.stringify([...FMS.open]))}catch(_){}box.dataset.k='';fmSupplyRender()};
  box.addEventListener('click',e=>{const t=e.target.closest('[data-fmst]');if(t){const n=+t.dataset.fmst;if(FMS.open.has(n))FMS.open.delete(n);else FMS.open.add(n);keep();return}
   const h=e.target.closest('[data-fmss]');if(!h)return;const n=+h.dataset.fmss;
   if(n===0){if(FMS.open.has(0))FMS.open.delete(0);else FMS.open.add(0);keep();fmGameFocus();return}   // the selection's card: it is selected already, a click shows or hides its bag
   fmGroupPick(n,e.shiftKey||e.ctrlKey||e.metaKey);if(!FMS.open.has(n)){FMS.open.add(n);keep()}fmGameFocus()});
  box.addEventListener('dblclick',e=>{if(e.target.closest('[data-fmss]')&&typeof rfJumpToSelection==='function')setTimeout(()=>{try{rfJumpToSelection()}catch(_){}},60)})}
 const S=new Set(fmSelRefs()),key=JSON.stringify([[...FMS.open].sort(),selCard?[SEL.supply,SEL.bag]:0,G.map(g=>[g.number,g.count,g.supply,g.bag,arr(g.refs).every(r=>S.has(r))])]);
 if(box.dataset.k!==key){box.dataset.k=key;
  const pip=(gl,n,label,bad)=>'<span class="fms-p'+(bad?' low':'')+'" title="'+esc(n+' '+label+(bad?'\n'+bad:''))+'"><b class="hcg hcg-'+gl[0]+'">'+gl[1]+'</b>'+n+'</span>';   /* the HUD's own glyphs (hud-craft) */
  const card=(id,title,count,s,B,open,sel,tip)=>{s=s||{};B=arr(B);
   const med=[[s.bandages,'bandage'],[s.remedies,'remedy','remedies'],[s.potions,'potion']].filter(x=>x[0]).map(x=>x[0]+' '+(x[0]===1?x[1]:(x[2]||x[1]+'s'))).join(', ');
   const row=pip(['arrow','➶'],s.arrows||0,'arrows',(s.archers&&!s.arrows)?s.archers+' with a bow and no arrows: they fight with a blade or fists':'')+(s.throws?pip(['spark','✦'],s.throws,'to throw (javelins, axes, rocks)'):'')+pip(['cross','✚'],s.medical||0,'medical supplies'+(med?': '+med:''),!s.medical?'Nothing to treat a wound or a stump with':'')+pip(['bowl','❦'],s.food||0,'food',!s.food?'No food: they go hungry away from home':'');
   const hp=s.maxhp?Math.max(0,Math.min(100,Math.round(100*s.hp/s.maxhp))):null;
   const st=[[s.hurt,'wounded','Below half health'],[s.bleeding,'bleeding','Losing blood: a stump or a deep wound to treat'],[s.hungry,'hungry','Hunger 20 or less'],[s.tired,'tired','Rest 20 or less']].filter(x=>x[0]);
   const health=hp==null?'':'<span class="fms-hp" title="'+esc('Health '+s.hp+' of '+s.maxhp+' ('+hp+'%)'+(s.fighting?'\n'+s.fighting+' fighting':''))+'"><span style="width:'+hp+'%"></span></span>'+(st.length?'<span class="fms-st">'+st.map(x=>'<span class="'+(x[1]==='hungry'||x[1]==='tired'?'warn':'bad')+'" title="'+esc(x[2])+'">'+x[0]+' '+x[1]+'</span>').join('')+'</span>':'');
   const bag=open?'<div class="fms-bag">'+(B.length?B.map(it=>'<span class="bagslot fms-i" title="'+esc(itemLabel(it[0])+' ×'+it[1]+(it[3]?'\n'+it[3]:''))+'">'+(it[2]?'<img alt="" src="'+esc(it[2])+'">':'<b>'+esc(itemLabel(it[0]).slice(0,3))+'</b>')+(it[1]>1?'<i class="bagcount">'+it[1]+'</i>':'')+'</span>').join(''):'<small>They carry nothing.</small>')+'</div>':'';
   return '<div class="fms'+(sel?' sel':'')+(open?' open':'')+(id===0?' fms-sel':'')+'" data-fmsg="'+id+'"><div class="fms-h"><button type="button" class="fms-tw" data-fmst="'+id+'" aria-expanded="'+open+'" title="'+(open?'Hide':'Show')+' the bag">'+(open?'▾':'▸')+'</button>'+
    '<button type="button" class="fms-b" data-fmss="'+id+'" title="'+esc(tip)+'"><span class="fms-n"><b>'+esc(title)+'</b><small>'+count+'</small></span>'+health+'<span class="fms-r">'+row+'</span></button></div>'+bag+'</div>'};
  let html='';
  if(selCard){const s=SEL.supply;html+=card(0,'Selected',s.n,s,SEL.bag,FMS.open.has(0),true,'The '+s.n+' selected together: their health, supplies and bag.\nClick: look in their bag (or hide it).')}
  html+=G.map(g=>card(g.number,'Group '+g.number,g.count,g.supply,g.bag,FMS.open.has(g.number),arr(g.refs).length&&arr(g.refs).every(r=>S.has(r)),'Group '+g.number+' · '+g.count+(g.formation?' · '+g.formation:'')+'\nClick: select them and look in their bag. Double-click: go there.')).join('');
  box.innerHTML=html?'<h4 title="What your people carry and how they are, the selected and each group.\nClick a group: select it and look in its bag.">Supplies</h4>'+html:'';
  box.hidden=!html}
 if(!fmSupplyPlace.q){fmSupplyPlace.q=1;requestAnimationFrame(()=>{fmSupplyPlace.q=0;fmSupplyPlace()})}}   // placed in the next frame, not inside the HUD update (hud-craft, 10-25)
// under the top bar (and the goal card when it shows), above the unit card
function fmSupplyPlace(){const el=$('fmSupplies');if(!el||el.hidden)return;const k=hudKC();let top=8,bottom=innerHeight/k-8;
 for(const id of ['topbar','goaltrack']){const e=$(id);if(e&&e.getClientRects().length&&getComputedStyle(e).display!=='none'){const b=e.getBoundingClientRect();if(b.height>0&&b.left/k<240)top=Math.max(top,b.bottom/k+8)}}
 const hf=$('heroframe');if(hf&&hf.getClientRects().length){const b=hf.getBoundingClientRect();if(b.height>0&&b.left/k<240)bottom=b.top/k-8}
 const t=Math.round(top)+'px',mh=Math.max(60,Math.round(bottom-top))+'px';if(el.style.top!==t)el.style.top=t;if(el.style.maxHeight!==mh)el.style.maxHeight=mh}
addEventListener('resize',()=>requestAnimationFrame(fmSupplyPlace));
{const u0=window.updateHUD;if(typeof u0==='function')window.updateHUD=function(raw){u0(raw);try{fmGroupRender()}catch(e){console.error(e)}try{fmQuiverBadges()}catch(e){console.error(e)}try{fmSupplyRender()}catch(e){console.error(e)}}}
{const st=document.createElement('style');st.textContent='#fmGroups{margin:0 0 3px}#fmGroups:empty{display:none}#rosterList .member.fm-ing{display:none}'+
 '#roster .fmg{border:1px solid #5d4a2a;border-radius:4px;margin:0 0 4px;background:rgba(0,0,0,.22)}#roster .fmg.sel{border-color:#f2d27a;box-shadow:0 0 6px rgba(242,210,122,.35)}#roster .fmg.part{border-color:rgba(242,210,122,.55)}#roster .fmg.fighting{border-color:#a5443a}'+
 '#roster .fmg-h{display:flex;align-items:stretch}#roster .fmg-tw{flex:0 0 24px;min-height:0!important;padding:0!important;border:0!important;border-right:1px solid rgba(242,210,122,.18)!important;border-radius:0!important;background:none!important;box-shadow:none!important;color:#f2d27a;font-size:16px;line-height:1;cursor:pointer}#roster .fmg-tw:hover{background:rgba(242,210,122,.12)!important}'+
 '#roster .fmg-b{flex:1 1 auto;min-width:0;display:grid;grid-template-columns:auto minmax(0,1fr);gap:3px 5px;align-items:center;padding:4px 5px 4px 1px!important;min-height:0!important;border:0!important;background:none!important;box-shadow:none!important;text-align:left}'+
 '#roster .fmg-n{grid-column:1/-1;display:flex;gap:5px;align-items:baseline;min-width:0;white-space:nowrap;overflow:hidden}#roster .fmg-n b{font:600 12px HudText,Georgia,serif;color:#f2d27a}#roster .fmg-n small{font-size:11.25px;color:var(--muted);overflow:hidden;text-overflow:ellipsis}'+
 '#roster .fmg-f{display:flex;gap:1px;align-items:center}#roster .fmg-f img{width:16px;height:18px;object-fit:contain;image-rendering:pixelated;background:#141a16;border:1px solid #5d4a2a;border-radius:2px}#roster .fmg-f i{font-size:11.25px;font-style:normal;color:var(--muted);margin-left:2px}'+
 '#roster .fmg-b .hpbar{grid-column:2;display:block;height:4px;background:#2a0f0c;border-radius:2px;overflow:hidden}#roster .fmg-b .hpbar span{display:block;height:100%;background:linear-gradient(#7fd06a,#3f8f34)}'+
 '#roster .fmg-m{padding:0 3px 1px 10px}#roster .fmg-m .member{margin-bottom:2px}'+
 'body.overlay[data-mat] #roster .fmg{border-radius:0;border:2px solid #000;background:rgba(0,0,0,.35);box-shadow:inset 0 0 0 1px var(--mband)}body.overlay[data-mat] #roster .fmg.sel{box-shadow:inset 0 0 0 2px var(--macc)}body.overlay[data-mat] #roster .fmg.part{box-shadow:inset 0 0 0 1px var(--macc)}'+
 '.bagslot.fmarrowslot{display:inline-flex;align-items:center;justify-content:center;box-sizing:border-box;cursor:default;vertical-align:top}.fmarrowslot img{max-width:100%;max-height:100%;image-rendering:pixelated}.fmarrowslot b{color:#e8dcc0;font-size:15px;font-weight:400}.fmarrowslot .bagcount{font-size:11.25px;line-height:12px}.fmarrowslot .bagcount.none{color:#ff8a76}'+
 '#fmSupplies{position:fixed;left:6px;top:120px;width:184px;overflow:auto;padding:4px;z-index:3;background:linear-gradient(180deg,var(--pane),var(--pane2));border:1px solid var(--trim);box-shadow:0 0 0 1px #000,inset 0 0 0 1px var(--trimdark),0 6px 18px rgba(0,0,0,.55);border-radius:4px}#fmSupplies[hidden]{display:none}'+
 '#fmSupplies h4{margin:2px 4px 4px;font:12px HudText,Georgia,serif;color:#f2d27a}#fmSupplies .fms{border:1px solid #5d4a2a;border-radius:4px;margin:0 0 4px;background:rgba(0,0,0,.22)}#fmSupplies .fms.sel{border-color:#f2d27a;box-shadow:0 0 6px rgba(242,210,122,.35)}'+
 '#fmSupplies .fms-h{display:flex;align-items:stretch}#fmSupplies .fms-tw{flex:0 0 24px;min-height:0!important;padding:0!important;border:0!important;border-right:1px solid rgba(242,210,122,.18)!important;border-radius:0!important;background:none!important;box-shadow:none!important;color:#f2d27a;font-size:16px;line-height:1}#fmSupplies .fms-tw:hover{background:rgba(242,210,122,.12)!important}'+
 '#fmSupplies .fms-b{flex:1 1 auto;min-width:0;display:flex;flex-direction:column;gap:3px;align-items:stretch;padding:4px 5px!important;min-height:0!important;border:0!important;background:none!important;box-shadow:none!important;text-align:left}'+
 '#fmSupplies .fms-n{display:flex;gap:6px;align-items:baseline}#fmSupplies .fms-n b{font:600 12px HudText,Georgia,serif;color:#f2d27a}#fmSupplies .fms-n small{font-size:11.25px;color:var(--muted)}'+
 '#fmSupplies .fms-r{display:flex;gap:8px;flex-wrap:wrap}#fmSupplies .fms-p{font-size:11.25px;color:#e8dcc0;white-space:nowrap}#fmSupplies .fms-p{display:inline-flex;align-items:center;gap:2px}#fmSupplies .fms-p .hcg{color:#cdb27a;font-weight:400}#fmSupplies .fms-p.low,#fmSupplies .fms-p.low .hcg{color:#ff8a76}'+
 '#fmSupplies .fms-hp{display:block;height:5px;background:#2a0f0c;border-radius:2px;overflow:hidden}#fmSupplies .fms-hp span{display:block;height:100%;background:linear-gradient(#7fd06a,#3f8f34)}body.cb #fmSupplies .fms-hp span{background:linear-gradient(#5aa6e8,#2a5f9a)}'+
 '#fmSupplies .fms-st{display:flex;flex-wrap:wrap;gap:2px 7px}#fmSupplies .fms-st span{font-size:11.25px;white-space:nowrap}#fmSupplies .fms-st .bad{color:#ff8a76}#fmSupplies .fms-st .warn{color:#ffcf6e}#fmSupplies .fms-sel .fms-n b{color:#fff1c8}'+
 '#fmSupplies .fms-bag{display:flex;flex-wrap:wrap;gap:3px;padding:2px 5px 6px 6px}#fmSupplies .fms-i{position:relative;display:inline-flex;align-items:center;justify-content:center;box-sizing:border-box;width:30px;height:30px;padding:1px;background:#141a16;border:1px solid #5d4a2a;border-radius:3px;cursor:default}#fmSupplies .fms-i .bagcount{position:absolute;right:1px;bottom:0;font:bold 11.25px/12px HudText,Georgia,serif;font-style:normal;color:#fff;text-shadow:0 0 2px #000,0 0 2px #000}#fmSupplies .fms-i img{max-width:100%;max-height:100%;image-rendering:pixelated}#fmSupplies .fms-i b{font-size:11.25px;font-weight:400;color:#e8dcc0}#fmSupplies .fms-bag small{font-size:11.25px;color:var(--muted)}'+
 'body.overlay[data-mat] #fmSupplies .fms{border-radius:0;border:2px solid #000;background:rgba(0,0,0,.35);box-shadow:inset 0 0 0 1px var(--mband)}body.overlay[data-mat] #fmSupplies .fms.sel{box-shadow:inset 0 0 0 2px var(--macc)}'+
 '#fmGroupMenu{position:fixed;z-index:60;min-width:190px;padding:4px;display:flex;flex-direction:column;gap:2px;background:linear-gradient(180deg,var(--pane),var(--pane2));border:1px solid var(--trim);box-shadow:0 0 0 1px #000,0 6px 18px rgba(0,0,0,.55);border-radius:4px}#fmGroupMenu[hidden]{display:none}#fmGroupMenu button{text-align:left;font-size:12px;padding:5px 9px;min-height:0}';document.head.appendChild(st)}
// For probes and tests.
window.fmStats=function(){return {sets:FM.sets.map(S=>({id:S.id,pred:S.pred,kind:S.kind,fx:S.fx,fy:S.fy,n:S.s.length,s:S.s.map(e=>[e.ref,e.x,e.y,!!e.arr])})),predicted:FM.predicted,confirmed:FM.confirmed,costPredictMs:FM.cost,costDrawMs:FM.costDraw,lastPush:FM.lastPush,lastCheck:FM.lastCheck||null,lastBox:FM.lastBox||null,atkBox:FM.atkBox||null,face:FM.face?{x:FM.face.x,y:FM.face.y,on:FM.face.on,width:FM.face.width,n:FM.face.P&&FM.face.P.s.length}:null,lastFace:FM.lastFace||null,groupPick:FM.lastGroupPick||null,groups:fmGroups().map(g=>[g.number,arr(g.refs).length]),cards:document.querySelectorAll('#fmGroups .fmg').length}};
