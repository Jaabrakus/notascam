// ===== Layered rock (Breaking.dm): a rock tile is K.blocks one-unit layers of natural, faceted
// rock. Mining knocks out the bottom layer (the tile shows a recess with the rock still over
// it), then the one above, opening a two-high tunnel; a dug tile keeps K.roof layers overhead
// as a rough rock roof. Heights come from the layer counts, so they hold as you dig.
// The rock over a cut: a faceted mass from 'cut' (2 over a tunnel, 1 over a recess) up to the
// shared rock corners. A recess also gets its back walls. Returns its record for the cracks.
// A rock column on the surface as a stack of blocks, one a layer (the user, 2026-10-24: "each mountain tile a mineable
// block ... not big long blocks"). Each block's exposed sides are a band of their own that bulges out between its
// seams, so the layers read as stacked stone, never cubes; every seam point is set by its world corner and layer, so
// all the blocks that meet there share it and the rock closes up. K.gone has a bit for each block mined out (with the
// old dug notches and a tunnel's open blocks): the blocks round a hole show their sides, the one under it its top,
// the one over it its underside. Returns the rockGeo entry: c the top's corners, s its full-height sides (marks,
// cracks, ore), L[k] the faces block k shows (the exact outline of the block a click mines).
function v3stackGone(K){if(!K)return 0;let m=K.gone||0;if(K.kind==='wall'){if(K.dug===1)m|=1;if(K.dug===2)m|=2}else if(K.roof)m|=(1<<(K.ceil||2))-1;return m}
function v3stackTop(K){return !K?0:K.kind==='wall'?(K.blocks||0):K.roof?(K.ceil||2)+K.roof:0}
function v3stackHas(K,k){if(!K)return false;if(K.kind==='wall'&&!K.blocks)return true;const H=v3stackTop(K);return k>=0&&k<H&&!((v3stackGone(K)>>k)&1)}
// Whether a neighbour's block k fills its whole side: a ramp's block (its top one, carved into a slope) doesn't.
function v3stackFull(K,k){return v3stackHas(K,k)&&!(K.slope&&k===(K.slopeh?K.slopeh-1:v3stackTop(K)-1))}
// A seam point: tile corner (ci, cj) at layer seam k. Above the ground it wanders a little, and it is pulled in towards
// the blocks round it: a corner standing out (one block there) is rounded off, a seam along a straight face is chipped
// in; every block that meets there works it out the same way, so the faces close up.
function v3stackPt(T,kindAt,ci,cj,k,Y){const wx=T.x0+ci,wy=T.y0+cj;
 let n=0,ox=0,oz=0,dr=1;for(const [a,b,dx,dz] of [[ci,cj,0.5,-0.5],[ci-1,cj,-0.5,-0.5],[ci,cj-1,0.5,0.5],[ci-1,cj-1,-0.5,0.5]]){const K=kindAt(a,b),h0=v3stackHas(K,k-1),h1=v3stackHas(K,k);if(h0||h1){n++;ox+=dx;oz+=dz;if((h0&&!v3laid(K,k-1))||(h1&&!v3laid(K,k)))dr=0}}
 if(n&&dr)return [wx-0.5,Y+k,-wy+0.5];   // only laid blocks meet here: an exact corner (building rework L3)
 if(k<=0)return [wx-0.5+(MD.h(wx,wy,61)-0.5)*0.06,Y,-wy+0.5+(MD.h(wx,wy,71)-0.5)*0.06];
 const f=n===1?0.36:n===2?0.2:n===3?0.1:0;return [wx-0.5+ox/Math.max(1,n)*f+(MD.h(wx,wy,61+k)-0.5)*0.14,Y+k+(MD.h(wx,wy,81+k)-0.5)*0.22,-wy+0.5+oz/Math.max(1,n)*f+(MD.h(wx,wy,71+k)-0.5)*0.14]}
// Building rework L3 (planning/BUILDING_REWORK_PLAN_2026-10-27.md step 2): a block laid by a plan (bit k of K.lay, View3D.dm
// Remaster3DTerrain; its letter in K.mat: w wood, else stone) is drawn dressed, not as rock: stone as masonry, two courses
// a block in a running bond (the joints at the same places on every tile, so a wall's courses run on across its tiles, never
// a row of cubes), wood as three logs a block lying along the side. Its seams are exact (v3stackPt: a corner where only laid
// blocks meet), its sides and top flat (the top's middle point, which unit feet read, kept). Natural blocks, and the natural
// base under a wall built on a mountain, are drawn as before. Still tagged as rock (v3rockTag): it thins out in front of
// your units the same way.
const V3LAID={stone:[0.70,0.66,0.57,1],mortar:[0.40,0.37,0.32,1],wood:[0.50,0.34,0.20,1],bark:[0.27,0.18,0.10,1]};
function v3laid(K,k){return !!(K&&K.lay&&k>=0&&((K.lay>>k)&1))}
function v3laidWood(K,k){return v3laid(K,k)&&typeof K.mat==='string'&&K.mat.charAt(k)==='w'}
// One open side of laid block k: b0 b1 along its foot, t1 t0 along its top (as v3rockStack's sides); n its outward normal,
// out a point inside the block.
function v3laidFace(ra,b0,b1,t1,t0,n,k,wood,out,e0,e1){
 const L=(p,q,t)=>[p[0]+(q[0]-p[0])*t,p[1]+(q[1]-p[1])*t,p[2]+(q[2]-p[2])*t],B=(u,v,d)=>{const p=L(L(b0,b1,u),L(t0,t1,u),v);return d?[p[0]+n[0]*d,p[1],p[2]+n[2]*d]:p},
  side=(u0,u1,v0,v1,d,c)=>{const p=B(u0,v0,d),q=B(u1,v0,d),r=B(u1,v1,d),s=B(u0,v1,d);MD.f(ra,p,q,r,c,out);MD.f(ra,p,r,s,c,out)};
 if(wood){side(0,1,0,1,0,MD.shade(V3LAID.bark,0.85));
  for(let r=0;r<3;r++){const v=(r+0.5)/3,m=B(0.5,v,0),c=MD.shade(V3LAID.wood,0.84+MD.h(Math.round(m[0]*4),Math.round(m[2]*4)+k*7+r,41)*0.24);MD.rod(ra,B(-(e0||0),v,0),B(1+(e1||0),v,0),0.165,6,c,k*3+r)}return}   /* e0, e1: the logs run on past an outer corner or a wall's end (construction-3d) */
 side(0,1,0,1,0,MD.shade(V3LAID.mortar,0.92));
 for(let r=0;r<2;r++){const v0=r*0.5,cuts=((k*2+r)%2)?[0,0.25,0.75,1]:[0,0.5,1];
  for(let s=0;s+1<cuts.length;s++){const u0=cuts[s],u1=cuts[s+1],m=B((u0+u1)/2,v0+0.25,0),tone=0.84+MD.h(Math.round(m[0]*8),Math.round(m[2]*8)+(k*2+r)*131,43)*0.24;
   side(u0+0.022,u1-0.022,v0+0.03,v0+0.47,0.014,MD.shade(V3LAID.stone,tone))}}}
// Building rework L4-L6 (planning/BUILDING_REWORK_PLAN_2026-10-27.md step 3; the owner, 10-27: "the game recognises walls,
// towers and gateways by their shape, no designating"): what laid blocks make, worked out once a terrain (kept on it) and
// skipped when no kind has laid blocks; nothing is saved, the shape is the blocks. Ported from the arena
// (reports/gathering/staged/build-by-shape, make_arena.py recognise). A barrier is a column with 2+ laid blocks in a run (a
// mined hole breaks the run); natural rock never is one.
//  - Tower: a 3x3 ring of barriers, its middle hollow or filled, with no full row of barriers beside it.
//  - Gateway: 1-3 open tiles in a line between barriers, the wall going on past both ends, open ground on both sides;
//    side-by-side runs (a thick wall) are one gateway.
//  - Enclosures: open ground the window's edge can't reach (gateways and towers shut it); 4 to 40 tiles is a house.
//  - Wall: the other barriers, 4-connected, 3+ tiles (or any length meeting a tower or gateway); touching a house: house
//    walls (no battlements, its gateway a doorway); more than a quarter of it inside the mass: a platform (nothing added).
//    Battlements go on a wall's outer sides: towards open ground outside a yard it closes, or, closing nothing, away from
//    the nearest claim (both sides with none).
// v3shapes(T): {tag: "x,y" -> its text in the chunk signature (020 v3chunkSig: closing a yard's last gap rebuilds every
// chunk whose battlements turn), at: "x,y" -> what that tile draws (v3shapeDeco)}.
function v3layRun(K){const L=K.lay|0;let best=0,run=0;for(let k=0;k<16;k++){if((L>>k)&1){run++;if(run>best)best=run}else run=0}return best}
function v3layWoodish(K){const m=typeof K.mat==='string'?K.mat:'';let w=0,s=0;for(const c of m){if(c==='w')w++;else if(c==='s')s++}return w>s}
function v3shapes(T){if(T.rmShp)return T.rmShp;const out={tag:new Map(),at:new Map(),n:{wall:0,house:0,mass:0,tower:0,gate:0,doorway:0}};T.rmShp=out;
 if(!Array.isArray(T.kinds)||!T.kinds.some(k=>k&&k.lay))return out;
 const W=T.w,H=T.h,kindAt=(i,j)=>{if(i<0||j<0||i>=W||j>=H)return null;const c=T.tiles[j*W+i];return c?T.kinds[c-1]:null};
 const BR=new Uint8Array(W*H);for(let j=0;j<H;j++)for(let i=0;i<W;i++){const K=kindAt(i,j);if(K&&K.kind==='wall'&&K.lay&&v3layRun(K)>=2)BR[j*W+i]=1}
 const bar=(i,j)=>i>=0&&j>=0&&i<W&&j<H&&BR[j*W+i]===1,top=(i,j)=>{const K=kindAt(i,j);return K?(K.blocks||0):0},wood=(i,j)=>{const K=kindAt(i,j);return !!K&&v3layWoodish(K)};
 const open=(i,j)=>{const K=kindAt(i,j);return !!K&&!['wall','block','built','tree','void','walk','peak'].includes(K.kind)},key=(i,j)=>i+','+j,wk=(i,j)=>(T.x0+i)+','+(T.y0+j);
 const tower=new Set(),towers=[],qcol=new Set();for(const c of (Array.isArray(V3.planCells)?V3.planCells:[]))if(c&&c[4]===1)qcol.add(c[0]+','+c[1]);   /* columns still going up: no battlements till done (construction-3d) */
 for(let y=0;y+2<H;y++)for(let x=0;x+2<W;x++){let ok=true;for(let v=0;v<3&&ok;v++)for(let u=0;u<3&&ok;u++)if((!(u===1&&v===1)&&!bar(x+u,y+v))||tower.has(key(x+u,y+v)))ok=false;if(!ok)continue;
  const row=pts=>pts.every(([a,b])=>bar(a,b));
  if(row([[x-1,y],[x-1,y+1],[x-1,y+2]])||row([[x+3,y],[x+3,y+1],[x+3,y+2]])||row([[x,y-1],[x+1,y-1],[x+2,y-1]])||row([[x,y+3],[x+1,y+3],[x+2,y+3]]))continue;
  let t=0,w=0;for(let v=0;v<3;v++)for(let u=0;u<3;u++){t=Math.max(t,top(x+u,y+v));if(wood(x+u,y+v))w++;tower.add(key(x+u,y+v))}
  towers.push({x,y,top:t,wood:w>4})}
 // gateways: runs of open tiles between barriers, the wall going on past both ends; parallel runs side by side are one
 const runs=[];
 for(let j=0;j<H;j++)for(let i=0;i<W-1;i++)if(bar(i,j)&&open(i+1,j)){let L=0;while(L<4&&open(i+1+L,j))L++;if(L>=1&&L<=3&&bar(i+1+L,j)&&bar(i-1,j)&&bar(i+2+L,j))runs.push({d:'x',a0:i+1,a1:i+L,b:j})}
 for(let i=0;i<W;i++)for(let j=0;j<H-1;j++)if(bar(i,j)&&open(i,j+1)){let L=0;while(L<4&&open(i,j+1+L))L++;if(L>=1&&L<=3&&bar(i,j+1+L)&&bar(i,j-1)&&bar(i,j+2+L))runs.push({d:'y',a0:j+1,a1:j+L,b:i})}
 const gates=[],gate=new Set();
 for(const r of runs){if(r.used)continue;let b0=r.b,b1=r.b;r.used=true;
  for(let more=true;more;){more=false;for(const q of runs)if(!q.used&&q.d===r.d&&q.a0===r.a0&&q.a1===r.a1&&(q.b===b1+1||q.b===b0-1)){q.used=true;b0=Math.min(b0,q.b);b1=Math.max(b1,q.b);more=true}}
  const at=(a,b)=>r.d==='x'?[a,b]:[b,a];let s0=false,s1=false;
  for(let a=r.a0;a<=r.a1;a++){if(open(...at(a,b0-1)))s0=true;if(open(...at(a,b1+1)))s1=true}
  if(!s0||!s1)continue;   // a notch, not a way through
  const e0=at(r.a0-1,b0),e1=at(r.a1+1,b0),cells=[];for(let a=r.a0;a<=r.a1;a++)for(let b=b0;b<=b1;b++){cells.push(at(a,b));gate.add(key(...at(a,b)))}
  gates.push({d:r.d,a0:r.a0,a1:r.a1,b0,b1,e0,e1,top:Math.min(top(...e0),top(...e1)),wood:wood(...e0)&&wood(...e1),cells})}
 // enclosures: open ground the window's edge can't reach
 const reach=new Uint8Array(W*H),q=[],shut=(i,j)=>gate.has(key(i,j))||tower.has(key(i,j)),push=(i,j)=>{if(i<0||j<0||i>=W||j>=H||reach[j*W+i]||!open(i,j)||shut(i,j))return;reach[j*W+i]=1;q.push(i,j)};
 for(let i=0;i<W;i++){push(i,0);push(i,H-1)}for(let j=0;j<H;j++){push(0,j);push(W-1,j)}
 for(let h=0;h<q.length;h+=2){const i=q[h],j=q[h+1];push(i+1,j);push(i-1,j);push(i,j+1);push(i,j-1)}
 const region=new Int32Array(W*H).fill(-1),regions=[];
 for(let j=0;j<H;j++)for(let i=0;i<W;i++){if(region[j*W+i]>=0||reach[j*W+i]||!open(i,j)||shut(i,j))continue;const id=regions.length,st=[[i,j]];let n=0;region[j*W+i]=id;
  while(st.length){const [a,b]=st.pop();n++;for(const [dx,dy] of [[1,0],[-1,0],[0,1],[0,-1]]){const x=a+dx,y=b+dy;if(x<0||y<0||x>=W||y>=H||region[y*W+x]>=0||reach[y*W+x]||!open(x,y)||shut(x,y))continue;region[y*W+x]=id;st.push([x,y])}}
  regions.push({n,house:n>=4&&n<=40})}
 const inside=(i,j)=>i>=0&&j>=0&&i<W&&j<H?region[j*W+i]:-1;
 // the nearest claim's banner, for walls that close nothing
 const claims=Array.isArray(V3.claims)?V3.claims:[];
 // walls
 const seen=new Set(),comp=new Map(),D4=[[1,0],[-1,0],[0,1],[0,-1]];
 for(let j=0;j<H;j++)for(let i=0;i<W;i++){if(!bar(i,j)||tower.has(key(i,j))||seen.has(key(i,j)))continue;const st=[[i,j]],cells=[];seen.add(key(i,j));
  while(st.length){const [a,b]=st.pop();cells.push([a,b]);for(const [dx,dy] of D4){const x=a+dx,y=b+dy,k=key(x,y);if(!bar(x,y)||tower.has(k)||seen.has(k))continue;seen.add(k);st.push([x,y])}}
  const set=new Set(cells.map(([a,b])=>key(a,b)));let interior=0,w=0,house=false,court=false;
  for(const [a,b] of cells){if(wood(a,b))w++;if(D4.every(([dx,dy])=>set.has(key(a+dx,b+dy))))interior++;
   for(const [dx,dy] of D4){const r2=inside(a+dx,b+dy);if(r2>=0){if(regions[r2].house)house=true;else if(regions[r2].n>=4)court=true}}}
  const joins=cells.some(([a,b])=>D4.some(([dx,dy])=>tower.has(key(a+dx,b+dy))||gate.has(key(a+dx,b+dy))));
  if(cells.length<3&&!joins)continue;
  const kind=interior>cells.length*0.25?'mass':house?'house':'wall',going=cells.some(([p,q])=>qcol.has(wk(p,q))||D4.some(([dx,dy])=>qcol.has(wk(p+dx,q+dy))));for(const [a,b] of cells)comp.set(key(a,b),going?'going':kind);   /* going: a column of it still going up (construction-3d) */out.n[kind]++;if(kind!=='wall')continue;
  let cx=0,cy=0;for(const [a,b] of cells){cx+=T.x0+a;cy+=T.y0+b}cx/=cells.length;cy/=cells.length;
  let ban=null,bd=1e9;for(const c of claims){const d=Math.hypot(c.x-cx,c.y-cy);if(d<bd){bd=d;ban=c}}
  const wd=w*2>cells.length;
  for(const [a,b] of cells){if(going)continue;let e=0;   /* no battlements on any of a wall still going up */for(let s=0;s<4;s++){const [dx,dy]=D4[s],x=a+dx,y=b+dy;if(bar(x,y)||gate.has(key(x,y))||inside(x,y)>=0||!open(x,y))continue;
    if(court||!ban||dx*(T.x0+a-ban.x)+dy*(T.y0+b-ban.y)>0)e|=1<<s}
   if(!e)continue;out.at.set(wk(a,b),{e,wood:wd});out.tag.set(wk(a,b),'W'+e+(wd?'w':''))}}
 for(const t of towers){out.n.tower++;for(let v=0;v<3;v++)for(let u=0;u<3;u++){const c=u===0&&v===0,k=wk(t.x+u,t.y+v),o={tw:t,c};   /* drawn from its corner block (its middle may be hollow ground) */const prev=out.at.get(k);out.at.set(k,prev?Object.assign(prev,o):o);
   out.tag.set(k,'T'+(c?'c'+t.top+(t.wood?'w':''):''))}}
 for(const g of gates){g.house=g.cells.some(([a,b])=>D4.some(([dx,dy])=>{const r2=inside(a+dx,b+dy);return r2>=0&&regions[r2].house}));if(!g.house){const k0=comp.get(key(...g.e0)),k1=comp.get(key(...g.e1));if(k0==='going'||k1==='going'||(k0&&k0!=='wall'&&k1&&k1!=='wall'))continue}   /* nor a gateway beside a wall still going up */   /* a gap between two houses, not a gateway (construction-3d) */out.n[g.house?'doorway':'gate']++;
  // its open leaves swing in towards the side a yard lies on (else away from the nearest claim; else south or west)
  const at=(a,b)=>g.d==='x'?[a,b]:[b,a];let inSide=0;for(let a=g.a0;a<=g.a1;a++){if(inside(...at(a,g.b0-1))>=0)inSide=-1;if(inside(...at(a,g.b1+1))>=0)inSide=1}
  g.inSide=inSide||-1;const k=wk(...g.e0),prev=out.at.get(k)||{};prev.g=g;out.at.set(k,prev);
  out.tag.set(k,(out.tag.get(k)||'')+'G'+g.d+(g.a1-g.a0+1)+'.'+(g.b1-g.b0+1)+'.'+g.top+(g.wood?'w':'')+(g.house?'h':'')+g.inSide)}
 return out}
// A throwaway place for a tower tile's stack: its blocks keep their rockGeo record (picking, feet) but draw nothing.
const V3_SHAPE_SINK=[];function v3shapeSink(){V3_SHAPE_SINK.length=0;return V3_SHAPE_SINK}
// What a recognised tile adds over its column: battlements on a wall's outer edges, a round tower (from its corner tile), a
// gateway's lintel and gate leaves on the tile at its start. Tagged as rock (v3rockTag): it thins out in front of your
// units as the walls do.
function v3shapeDeco(g,K,S,tx,ty,X,Y,Z){const a=g(''),a0=a.length,H=v3stackTop(K),stone=V3LAID.stone,wood=V3LAID.wood;
 if(S.e){const D=[[1,0],[-1,0],[0,1],[0,-1]];for(let s=0;s<4;s++){if(!((S.e>>s)&1))continue;const [dx,dy]=D[s];
   if(S.wood)for(const f of [-0.3,0,0.3]){const cx=dx?X+dx*0.41:X+f,cz=dx?Z+f:Z-dy*0.41;MD.prism(a,cx,cz,Y+H-0.04,Y+H+0.4,0.075,0.012,5,MD.shade(wood,0.86+MD.h(tx*3+s,ty*5+f*10,47)*0.2),tx*7+ty*13+s)}
   else for(const f of [-0.23,0.23]){const cx=dx?X+dx*0.39:X+f,cz=dx?Z+f:Z-dy*0.39,hx=dx?0.1:0.15,hz=dx?0.15:0.1;boxr(a,cx-hx,cx+hx,cz-hz,cz+hz,Y+H,Y+H+0.34,MD.shade(stone,0.9+MD.h(tx*3+s,ty*5+(f>0?1:0),48)*0.16))}}}
 if(S.tw&&S.c)v3blockTower(a,X+1,Y,Z-1,tx,ty,S.tw.top,S.tw.wood);   // its middle, a tile in from the corner
 if(S.g)v3gatewayDeco(a,S.g,tx,ty,Y);
 v3rockTag(a,a0)}
// A round tower on laid blocks: a drum of radius ~1.5 up to its top block, coursed like the masonry (or of upright logs),
// a flat top at the blocks' own height (where units stand) and 14 merlons or stakes round its crown.
function v3blockTower(a,X,Y,Z,tx,ty,H,wd){const R=1.5,N=28,seed=tx*31+ty*17,base=wd?V3LAID.wood:V3LAID.stone,st=k=>MD.shade(base,k);
 MD.prism(a,X,Z,Y,Y+0.3,R*1.06,R*1.02,N,st(wd?0.7:0.8),seed);
 if(wd)MD.prism(a,X,Z,Y+0.3,Y+H,R,R,N,st(0.92),seed+1);
 else for(let c=0,n=Math.max(1,Math.round(H*2));c<n;c++){const y0=Y+0.3+(H-0.3)*c/n,y1=Y+0.3+(H-0.3)*(c+1)/n;MD.prism(a,X,Z,y0,y1,R,R,N,st(0.86+MD.h(tx,ty+c,49)*0.16),seed+2+c)}
 for(let k=0;k<N;k++){const t0=k/N*6.2832,t1=(k+1)/N*6.2832;tri(a,[X,Y+H+0.004,Z],[X+Math.cos(t0)*R,Y+H+0.004,Z+Math.sin(t0)*R],[X+Math.cos(t1)*R,Y+H+0.004,Z+Math.sin(t1)*R],[0,1,0],st(0.78))}
 for(let k=0;k<14;k++){const an=(k+0.5)/14*6.2832,cx=X+Math.cos(an)*R*0.9,cz=Z+Math.sin(an)*R*0.9;
  if(wd)MD.prism(a,cx,cz,Y+H-0.04,Y+H+0.42,0.08,0.014,5,st(0.9),seed+40+k);else boxr(a,cx-0.13,cx+0.13,cz-0.13,cz+0.13,Y+H,Y+H+0.34,st(0.94))}}
// A gateway (S.g, from v3shapes; its end tile at tx,ty): a lintel 0.42 thick across the gap at the wall top, and open gate
// leaves swung in against the posts (a house's doorway: the lintel only).
function v3gatewayDeco(a,G,tx,ty,Y){const t=Math.max(1.6,G.top),w=G.a1-G.a0+1,ox=tx-(G.d==='x'?G.e0[0]:G.e0[0]),oy=ty-G.e0[1];   /* world = local + (ox, oy) */
 const wx=i=>i+ox,wy=j=>j+oy,col=MD.shade(G.wood?V3LAID.wood:V3LAID.stone,0.9),leaf=MD.shade(V3LAID.wood,0.8);
 if(G.d==='x'){const x0=wx(G.a0)-0.5,x1=wx(G.a1)+0.5,y0=wy(G.b0)-0.5,y1=wy(G.b1)+0.5;boxr(a,x0,x1,-y1,-y0,Y+t-0.42,Y+t,col);
  if(!G.house)for(const xh of [x0+0.06,x1-0.06]){const yc=G.inSide>0?y1:y0,y2=yc+G.inSide*w/2;boxr(a,xh-0.04,xh+0.04,-Math.max(yc,y2),-Math.min(yc,y2),Y,Y+t-0.55,leaf)}}
 else{const y0=wy(G.a0)-0.5,y1=wy(G.a1)+0.5,x0=wx(G.b0)-0.5,x1=wx(G.b1)+0.5;boxr(a,x0,x1,-y1,-y0,Y+t-0.42,Y+t,col);
  if(!G.house)for(const yh of [y0+0.06,y1-0.06]){const xc=G.inSide>0?x1:x0,x2=xc+G.inSide*w/2;boxr(a,Math.min(xc,x2),Math.max(xc,x2),-yh-0.04,-yh+0.04,Y,Y+t-0.55,leaf)}}}
function v3rockStack(g,T,kindAt,i,j,X,Y,Z,K){const tx=T.x0+i,ty=T.y0+j,ra=g(''),ra0=ra.length,H=v3stackTop(K),has=k=>v3stackHas(K,k);
 const pal=K.biome==='mesa'?MD.PAL.mesa:K.biome==='ashlands'?MD.PAL.ash:K.biome==='tundra'?MD.PAL.tundraRock:K.biome==='mushroom'?MD.PAL.shroomRock:MD.PAL.rock;
 const rc0=K.biome==='mesa'?pal[(ty+Math.floor(MD.h(tx,0,6)*2))%pal.length]:pal[Math.floor(MD.h(tx,ty,6)*pal.length)%pal.length],V=K.vein&&VEIN[K.vein],rc=V?MD.mix(rc0,V.tint,0.12):rc0;
 const P=(ci,cj,k)=>v3stackPt(T,kindAt,i+ci,j+cj,k,Y),L={},gs=[];let top=-1;for(let k=H-1;k>=0;k--)if(has(k)){top=k;break}
 // the four sides: neighbour offset, corners (as the old faces ran: sw-se south, ne-nw north, se-ne east, nw-sw west), outward normal
 const SD=[[0,-1,[0,0],[1,0],[0,0,1]],[0,1,[1,1],[0,1],[0,0,-1]],[1,0,[1,0],[1,1],[1,0,0]],[-1,0,[0,1],[0,0],[-1,0,0]]];
 for(let k=0;k<H;k++){if(!has(k))continue;const out=[X,Y+k+0.5,Z],F=L[k]=[];
  // a ramp (K.slope, the way it rises): the top block's corners on its low side come down to the block's foot
  const sl=K.slope&&k===(K.slopeh?K.slopeh-1:top)?K.slope:0,low=(ci,cj)=>sl===1?cj===0:sl===2?cj===1:sl===4?ci===0:sl===8?ci===1:false,TP=(ci,cj)=>P(ci,cj,low(ci,cj)?k:k+1);
  const lk=!sl&&v3laid(K,k),wk=lk&&v3laidWood(K,k);   // laid by a plan (not carved into a ramp): dressed
  SD.forEach(([di,dj,ca,cb,n],d)=>{if(v3stackFull(kindAt(i+di,j+dj),k))return;if(sl&&low(ca[0],ca[1])&&low(cb[0],cb[1]))return;const b0=P(ca[0],ca[1],k),b1=P(cb[0],cb[1],k),t1=TP(cb[0],cb[1]),t0=TP(ca[0],ca[1]);
   if(lk){v3laidFace(ra,b0,b1,t1,t0,n,k,wk,out,wk&&!v3stackHas(kindAt(i+ca[0]-cb[0],j+ca[1]-cb[1]),k)?0.16:0,wk&&!v3stackHas(kindAt(i+cb[0]-ca[0],j+cb[1]-ca[1]),k)?0.16:0);F.push({a:b0,b:b1,c:t1,d:t0,m:[(b0[0]+b1[0]+t1[0]+t0[0])/4,(b0[1]+b1[1]+t1[1]+t0[1])/4,(b0[2]+b1[2]+t1[2]+t0[2])/4],n});if(k===0||!v3stackHas(kindAt(i+di,j+dj),0))gs[d]=gs[d]||[ca,cb];return}
   // the face's high point off its middle, at a depth of its own: rough stone, not a pillow
   const u=0.25+MD.h(tx*7+d,ty*13+k,91)*0.5,v=0.25+MD.h(tx+d*5,ty*3+k,92)*0.5,bu=0.05+MD.h(tx*3+d,ty+k*7,93)*0.16,L2=(a,b,q)=>[a[0]+(b[0]-a[0])*q,a[1]+(b[1]-a[1])*q,a[2]+(b[2]-a[2])*q],Q=L2(L2(b0,b1,u),L2(t0,t1,u),v);
   const mid=[Q[0]+n[0]*bu,Q[1],Q[2]+n[2]*bu],tone=0.62+MD.h(tx,ty*3+d,k+94)*0.26,c=MD.shade(rc,tone*(k%2?0.96:1.03));
   MD.f(ra,b0,b1,mid,MD.shade(c,0.86),out);MD.f(ra,b1,t1,mid,MD.shade(c,1.02),out);MD.f(ra,t1,t0,mid,MD.shade(c,1.14),out);MD.f(ra,t0,b0,mid,MD.shade(c,0.94),out);
   F.push({a:b0,b:b1,c:t1,d:t0,m:mid,n});if(k===0||!v3stackHas(kindAt(i+di,j+dj),0))gs[d]=gs[d]||[ca,cb]});
  // the block's top, where nothing of this column sits on it: the mountain's top has more relief and a little grass at an edge
  if(!has(k+1)){const sw=TP(0,0),se=TP(1,0),ne=TP(1,1),nw=TP(0,1),hi=k===top,cm=lk?[(sw[0]+se[0]+ne[0]+nw[0])/4,(sw[1]+se[1]+ne[1]+nw[1])/4,(sw[2]+se[2]+ne[2]+nw[2])/4]:[X+(MD.h(tx,ty,95)-0.5)*(sl?0.1:0.3),(sw[1]+se[1]+ne[1]+nw[1])/4+(sl?0.03:hi?0.04+MD.h(tx,ty,96)*0.06:0.03),Z+(MD.h(tx,ty,97)-0.5)*(sl?0.1:0.3)];
   const grass=!lk&&hi&&!sl&&T.z===1&&MD.h(tx,ty,8)<0.2&&[[0,-1],[0,1],[1,0],[-1,0]].some(([a,b])=>!v3stackHas(kindAt(i+a,j+b),k)),tc=lk?MD.shade(wk?V3LAID.wood:V3LAID.stone,1.06):grass?[0.36,0.5,0.26]:rc,lo=[X,Y+k,Z];
   [[sw,se],[se,ne],[ne,nw],[nw,sw]].forEach(([p,q],e)=>MD.f(ra,p,q,cm,MD.shade(tc,0.9+MD.h(tx+e,ty,98+k)*0.14),lo));F.top={sw,se,ne,nw,m:cm}}
  // its underside, over a block mined out under it
  if(k>0&&!has(k-1)){const sw=P(0,0,k),se=P(1,0,k),ne=P(1,1,k),nw=P(0,1,k),cm=[X,Y+k-0.04,Z],dk=MD.shade(lk?(wk?V3LAID.wood:V3LAID.stone):rc,0.5),up=[X,Y+k+1,Z];[[sw,se],[se,ne],[ne,nw],[nw,sw]].forEach(([p,q])=>MD.f(ra,p,q,cm,dk,up));F.bot={sw,se,ne,nw,m:cm}}}
 const tk=top>=0?top+1:0,c=L[top]&&L[top].top?[L[top].top.sw,L[top].top.se,L[top].top.ne,L[top].top.nw]:[P(0,0,tk),P(1,0,tk),P(1,1,tk),P(0,1,tk)];
 const s=gs.filter(Boolean).map(([ca,cb])=>[P(ca[0],ca[1],tk),P(cb[0],cb[1],tk),null]);
 const G={c,Y,rc:v3laid(K,top)?(v3laidWood(K,top)?V3LAID.wood:V3LAID.stone):rc,s,blocks:H,cut:0,L,stack:1,slope:K.slope||0};if(V&&s.length&&!K.lay)v3veinMarks(ra,G,K.vein,tx,ty);   /* no ore marks on a built column */v3rockTag(ra,ra0);return G}
function v3cutRock(g,T,kindAt,i,j,X,Y,Z,K,cut,recess){const tx=T.x0+i,ty=T.y0+j,h=0.5,ra=g(''),ra0=ra.length;
 const topOf=(a,b)=>{const n=kindAt(a,b);if(!n)return null;if(n.kind==='wall')return n.blocks?n.blocks+0.4:null;return n.roof?(n.ceil||2)+n.roof+0.4:null};
 const fb=recess?K.blocks+0.4:(K.ceil||2)+K.roof+0.4,ch=(ci,cj)=>{let s=0,n=0;for(const [di,dj] of [[0,0],[-1,0],[0,-1],[-1,-1]]){const t=topOf(ci+di,cj+dj);if(t!=null){s+=t;n++}}return (n?s/n:fb)+(MD.h(T.x0+ci,T.y0+cj,5)-0.5)*0.7+(MD.vn(T.x0+ci,T.y0+cj,3,6)-0.5)*0.8};
 const lo=(ci,cj)=>cut+(MD.h(T.x0+ci,T.y0+cj,15)-0.5)*0.16;
 const pal=K.biome==='mesa'?MD.PAL.mesa:K.biome==='ashlands'?MD.PAL.ash:K.biome==='tundra'?MD.PAL.tundraRock:K.biome==='mushroom'?MD.PAL.shroomRock:(T.z===1||T.z===3)?MD.PAL.rock:MD.PAL.cave;
 const rc0=K.biome==='mesa'?pal[(ty+Math.floor(MD.h(tx,0,6)*2))%pal.length]:pal[Math.floor(MD.h(tx,ty,6)*pal.length)%pal.length],V=K.vein&&VEIN[K.vein],rc=V?MD.mix(rc0,V.tint,0.12):rc0;
 const C=(ci,cj,x,z)=>{const b=lo(ci,cj);return [[x,Y+Math.max(ch(ci,cj),b+0.6),z],[x,Y+b,z]]};
 const [sw,bsw]=C(i,j,X-h,Z+h),[se,bse]=C(i+1,j,X+h,Z+h),[ne,bne]=C(i+1,j+1,X+h,Z-h),[nw,bnw]=C(i,j+1,X-h,Z-h);
 MD.f(ra,sw,se,ne,MD.shade(rc,0.95+MD.h(tx,ty,9)*0.12));MD.f(ra,sw,ne,nw,MD.shade(rc,0.9+MD.h(tx,ty,10)*0.12));
 const above=[X,Y+cut+4,Z],dark=MD.shade(rc,0.55);MD.f(ra,bsw,bne,bse,dark,above);MD.f(ra,bsw,bnw,bne,dark,above);
 const covers=n=>!!n&&(n.kind==='wall'||!!n.roof),out=[X,Y+cut+1,Z],gs=[];
 const side=(p0,p1,b0,b1,k)=>{const mid=[(p0[0]+p1[0])/2+(MD.h(tx,ty,k)-0.5)*0.12,(b0[1]+Math.min(p0[1],p1[1]))/2,(p0[2]+p1[2])/2+(MD.h(tx,ty,k+1)-0.5)*0.12];gs.push([p0,p1,mid]);const c=MD.shade(rc,0.72+MD.h(tx,ty,k+2)*0.18);
  MD.f(ra,b0,b1,mid,c,out);MD.f(ra,b1,p1,mid,c,out);MD.f(ra,p1,p0,mid,MD.shade(c,1.08),out);MD.f(ra,p0,b0,mid,c,out)};
 const nb=[kindAt(i,j-1),kindAt(i,j+1),kindAt(i+1,j),kindAt(i-1,j)];
 if(!covers(nb[0]))side(sw,se,bsw,bse,20);if(!covers(nb[1]))side(ne,nw,bne,bnw,24);if(!covers(nb[2]))side(se,ne,bse,bne,28);if(!covers(nb[3]))side(nw,sw,bnw,bsw,32);
 // a recess: its back walls where the neighbours are solid rock (they draw no face towards it)
 if(recess){const wc=MD.shade(rc,0.62),inn=[X,Y+0.5,Z],wall=(a,b)=>{MD.f(ra,[a[0],Y,a[2]],[b[0],Y,b[2]],[b[0],Y+cut,b[2]],wc,inn);MD.f(ra,[a[0],Y,a[2]],[b[0],Y+cut,b[2]],[a[0],Y+cut,a[2]],wc,inn)};
  const solid=n=>!!n&&n.kind==='wall';if(solid(nb[0]))wall(bsw,bse);if(solid(nb[1]))wall(bne,bnw);if(solid(nb[2]))wall(bse,bne);if(solid(nb[3]))wall(bnw,bsw)}
 const G={c:[sw,se,ne,nw],Y:Y+cut,rc,s:gs,blocks:K.blocks||K.roof||0,cut};if(V)v3veinMarks(ra,G,K.vein,tx,ty);v3rockTag(ra,ra0);return G}
// The floor block left standing when the block above it was mined first (dug 2): a low ledge of the same rock, never a
// box. Its top is four facets round a raised middle, lower where it meets an open side (a worn, rounded edge), with noise
// at the corners; its open sides bulge out round their middle like the mountain's faces. The mass from two blocks up and
// its back walls are v3cutRock's (cut 2). Returns its faces for the cracks and the outline (rockGeo's .ledge, read by
// rts-feel's rfMineMark and by v3drawWork).
function v3rockLedge(g,T,kindAt,i,j,X,Y,Z,K,top){const tx=T.x0+i,ty=T.y0+j,h=0.5,ra=g(''),ra0=ra.length;
 const pal=K.biome==='mesa'?MD.PAL.mesa:K.biome==='ashlands'?MD.PAL.ash:K.biome==='tundra'?MD.PAL.tundraRock:K.biome==='mushroom'?MD.PAL.shroomRock:(T.z===1||T.z===3)?MD.PAL.rock:MD.PAL.cave;
 const rc0=K.biome==='mesa'?pal[(ty+Math.floor(MD.h(tx,0,6)*2))%pal.length]:pal[Math.floor(MD.h(tx,ty,6)*pal.length)%pal.length],V=K.vein&&VEIN[K.vein],rc=V?MD.mix(rc0,V.tint,0.12):rc0;
 const covers=n=>!!n&&(n.kind==='wall'||!!n.roof),op=[kindAt(i,j-1),kindAt(i,j+1),kindAt(i+1,j),kindAt(i-1,j)].map(n=>!covers(n));   // open: south, north, east, west
 // a corner a little lower for each open side it is on, with noise (the shared corners of two ledges along a face agree)
 const LH=[1,0.85,0.72],ht=(ci,cj,a,b)=>Y+top*LH[(a?1:0)+(b?1:0)]+(MD.h(T.x0+ci,T.y0+cj,17)-0.5)*0.14;
 const sw=[X-h,ht(i,j,op[0],op[3]),Z+h],se=[X+h,ht(i+1,j,op[0],op[2]),Z+h],ne=[X+h,ht(i+1,j+1,op[1],op[2]),Z-h],nw=[X-h,ht(i,j+1,op[1],op[3]),Z-h];
 const mid=[X+(MD.h(tx,ty,21)-0.5)*0.2,Math.max(sw[1],se[1],ne[1],nw[1])+0.04+MD.h(tx,ty,22)*0.06,Z+(MD.h(tx,ty,23)-0.5)*0.2],below=[X,Y-2,Z];
 [[sw,se],[se,ne],[ne,nw],[nw,sw]].forEach(([a,b],q)=>MD.f(ra,a,b,mid,MD.shade(rc,0.9+MD.h(tx+q,ty,24)*0.14),below));
 const out=[X,Y+top*0.5,Z],gs=[];
 const side=(p0,p1,k,nx,nz)=>{const b0=[p0[0],Y,p0[2]],b1=[p1[0],Y,p1[2]],bu=0.07+MD.h(tx,ty,k)*0.08,tj=(MD.h(tx,ty,k+1)-0.5)*0.14,lo=Math.min(p0[1],p1[1]);
  const m=[(p0[0]+p1[0])/2+nx*bu+nz*tj,Y+(lo-Y)*(0.42+MD.h(tx,ty,k+3)*0.16),(p0[2]+p1[2])/2+nz*bu+nx*tj];gs.push([p0,p1,m]);const c=MD.shade(rc,0.72+MD.h(tx,ty,k+2)*0.18);
  MD.f(ra,b0,b1,m,c,out);MD.f(ra,b1,p1,m,MD.shade(c,0.96),out);MD.f(ra,p1,p0,m,MD.shade(c,1.1),out);MD.f(ra,p0,b0,m,MD.shade(c,0.92),out)};
 if(op[0])side(sw,se,40,0,1);if(op[1])side(ne,nw,44,0,-1);if(op[2])side(se,ne,48,1,0);if(op[3])side(nw,sw,52,-1,0);
 const G={c:[sw,se,ne,nw],Y,rc,s:gs,blocks:1,cut:0};if(V)v3veinMarks(ra,G,K.vein,tx,ty);v3rockTag(ra,ra0);return G}
// Ore: lumps of metal sticking out of the rock, most of them low on the faces where you dig.
function v3veinMarks(a,g,vein,tx,ty){const V=VEIN[vein];if(!V)return;const lump=(P,n,r,seed)=>{const s0=a.length;MD.blob(a,P[0]+n[0]*r*0.45,P[1]+n[1]*r*0.3,P[2]+n[2]*r*0.45,r,r*0.85,r,V.mark,seed,0.4);if(V.glow)for(let q=s0+3;q<a.length;q+=12){a[q]=0;a[q+1]=0;a[q+2]=0}};
 g.s.forEach((_,fi)=>{const F=v3rockFace(g,fi),H=Math.max(1,F.size),n=2+Math.floor(MD.h(tx+fi,ty,51)*3);
  for(let k=0;k<n;k++){const u=0.15+MD.h(tx*3+k,ty+fi*5,52)*0.7,v=Math.max(0.06,Math.pow(MD.h(tx+fi*7,ty*3+k,53),1.6)*Math.min(1,3/H));lump(F.P(u,v),F.n,0.08+MD.h(tx+k,ty+fi,54)*0.08,tx*13+ty*7+k+fi*3)}});
 const Ft=v3rockFace(g,null);for(let k=0;k<1+Math.floor(MD.h(tx,ty,55)*2);k++)lump(Ft.P(0.2+MD.h(tx,ty+k,56)*0.6,0.2+MD.h(tx+k,ty,57)*0.6),[0,1,0],0.1,tx+ty+k)}
