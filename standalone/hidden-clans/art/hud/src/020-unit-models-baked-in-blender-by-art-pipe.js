// ===== Unit models (baked in Blender by art/pipeline/export_units.py) =====
// Loaded the first time a race appears; until then (or if loading fails) the unit stays a sprite.
const MDL=new Map();
// Material tiers: the colour metal parts and armour take (RuneScape-style colour language).
const TIER={wood:[0.55,0.38,0.22],bone:[0.86,0.82,0.7],leather:[0.46,0.31,0.19],iron:[0.56,0.56,0.6],silver:[0.84,0.86,0.9],gold:[0.93,0.76,0.3],adamantium:[0.3,0.62,0.48],diamond:[0.72,0.9,1],chitin:[0.42,0.3,0.46],hell:[0.58,0.12,0.1]};
function v3model(name){let m=MDL.get(name);if(m)return m.ready?m:null;m={ready:false};MDL.set(name,m);
 const dec=b=>{const s=atob(b),u=new Uint8Array(s.length);for(let i=0;i<s.length;i++)u[i]=s.charCodeAt(i);return u};
 fetch('model-'+name+'.json').then(r=>{if(!r.ok)throw new Error(r.status);return r.json()}).then(d=>{const anims={};for(const k in d.anims){const A=d.anims[k];anims[k]={fps:A.fps,frames:A.frames.map(f=>new Int16Array(dec(f).buffer))}}
  for(const k in d.anims)anims[k].joints=d.anims[k].joints||null;const cb=dec(d.colors),cols=[];for(let i=0;i<d.tris;i++)cols.push([cb[i*3]/255,cb[i*3+1]/255,cb[i*3+2]/255,1]);const parts=d.parts?dec(d.parts):null;const gear={};for(const g in (d.gear||{})){const G=d.gear[g];const gc=dec(G.col),cl=[];for(let i=0;i<G.tris;i++)cl.push([gc[i*3]/255,gc[i*3+1]/255,gc[i*3+2]/255,1]);gear[g]={joint:G.joint,tris:G.tris,pos:new Int16Array(dec(G.pos).buffer),mat:dec(G.mat),cols:cl}}Object.assign(m,{ready:true,tris:d.tris,q:d.q||8000,anims,cols,parts,gear})}).catch(()=>{m.failed=true});return null}
// Draw one unit: blend two frames of its animation, turn it to face its way, add its triangles to 'out'.
function v3drawModel(out,md,t,X,Y,Z,kd,now,walking){const act=t.act==='attack'?'attack':t.act==='work'?'work':walking?'walk':'idle';const A=md.anims[act]||md.anims.idle;const n=A.frames.length;
 const ph=now*A.fps+MD.h(String(t.key).length,(t.x*7+t.y)|0,9)*n;const i0=Math.floor(ph)%n,i1=(i0+1)%n,f=ph-Math.floor(ph);const F0=A.frames[i0],F1=A.frames[i1];
 let dx=0,dz=0;if(walking&&kd){dx=kd.tx-kd.fx;dz=-(kd.ty-kd.fy)}if(!dx&&!dz){const d=t.dir||2;dx=((d&4)?1:0)-((d&8)?1:0);dz=((d&2)?1:0)-((d&1)?1:0)}
 const want=Math.atan2(dx,dz);if(kd){if(kd.face==null)kd.face=want;let df=want-kd.face;while(df>Math.PI)df-=2*Math.PI;while(df<-Math.PI)df+=2*Math.PI;kd.face+=df*0.22}const th=kd&&kd.face!=null?kd.face:want;
 const cs=Math.cos(th),sn=Math.sin(th),sc=1.15/md.q,ctr=[X,Y+0.45,Z];
 // Armour recolours its body parts: 2 torso (chest), 5 legs, 3/6 right arm and hand, 4/7 left.
 const G=t.gear||{};const tc=k=>TIER[k]||null;const over={2:tc(G.c),5:tc(G.l),3:tc(G.ar),6:tc(G.ar),4:tc(G.al),7:tc(G.al)};
 for(let j=0;j<md.tris;j++){const P=[];for(let v=0;v<3;v++){const o=(j*3+v)*3;const x=(F0[o]+(F1[o]-F0[o])*f)*sc,y=(F0[o+1]+(F1[o+1]-F0[o+1])*f)*sc,z=(F0[o+2]+(F1[o+2]-F0[o+2])*f)*sc;P.push([X+x*cs+z*sn,Y+y,Z-x*sn+z*cs])}
  if(P[0][0]===P[1][0]&&P[0][1]===P[1][1]&&P[0][2]===P[1][2])continue;const pc=md.parts&&over[md.parts[j]];MD.f(out,P[0],P[1],P[2],pc?[pc[0],pc[1],pc[2],1]:md.cols[j],ctr)}
 // Held and worn gear follows its joint through the animation.
 if(!md.gear||!A.joints)return;const pieces=[];const w=(G.w||'').split(':');if(w[0]&&md.gear[w[0]])pieces.push([w[0],w[1]]);if(G.bow&&md.gear.bow)pieces.push(['bow',G.bow]);if(G.s&&md.gear.shield)pieces.push(['shield',G.s]);if(G.h&&md.gear.helmet)pieces.push(['helmet',G.h]);
 for(const [name,tier] of pieces){const g=md.gear[name];const J0=A.joints[i0][g.joint],J1=A.joints[i1][g.joint];if(!J0||!J1)continue;const M=J0.map((v,k)=>v+(J1[k]-v)*f);const metal=TIER[tier]||TIER.iron;const gs=1/md.q;
  for(let j=0;j<g.tris;j++){const P=[];for(let v=0;v<3;v++){const o=(j*3+v)*3;const lx=g.pos[o]*gs,ly=g.pos[o+1]*gs,lz=g.pos[o+2]*gs;
    const x=(M[0]*lx+M[1]*ly+M[2]*lz+M[3])*1.15,y=(M[4]*lx+M[5]*ly+M[6]*lz+M[7])*1.15,z=(M[8]*lx+M[9]*ly+M[10]*lz+M[11])*1.15;P.push([X+x*cs+z*sn,Y+y,Z-x*sn+z*cs])}
   const mc=g.mat[j];const c=mc===0?[metal[0],metal[1],metal[2],1]:mc===4?[metal[0]+(1-metal[0])*0.45,metal[1]+(1-metal[1])*0.45,metal[2]+(1-metal[2])*0.45,1]:mc===1&&tier==='wood'?[TIER.wood[0],TIER.wood[1],TIER.wood[2],1]:g.cols[j];MD.f(out,P[0],P[1],P[2],c,ctr)}}}
// Mountain top height from rock depth (tiles to open ground): above a wall's walk at the edge (~2.4),
// ~7 ten tiles in, ~11 at most.
function MH(d){return 3.4+2.2*Math.sqrt(Math.max(0,Math.min(d,30)-1))}
// The main terrain in 8x8-tile chunks on the world's grid. A chunk's geometry is rebuilt only when something it is built
// from changed: its tiles and the three round it (kind, rock depth, sight, wall walks, trees being worked,
// portcullises); then the chunks are joined into one buffer per texture. A block mined, a tree felled or a wall built
// rebuilds a chunk or a few instead of the whole view (10-30 ms before), and a shifted view only the chunks at its edge.
function v3depthField(T){const n=T.w*T.h,depth=new Int16Array(n),q=[];for(let j=0;j<T.h;j++)for(let i=0;i<T.w;i++){const c=T.tiles[j*T.w+i],k=c?T.kinds[c-1]:null;if(!k||k.kind!=='wall'){depth[j*T.w+i]=0;q.push(i,j)}else depth[j*T.w+i]=999}
 for(let h=0;h<q.length;h+=2){const i=q[h],j=q[h+1],d=depth[j*T.w+i];for(let s=0;s<4;s++){const x=i+(s===0?1:s===1?-1:0),y=j+(s===2?1:s===3?-1:0);if(x<0||y<0||x>=T.w||y>=T.h)continue;const m=y*T.w+x;if(depth[m]>d+1){depth[m]=d+1;q.push(x,y)}}}return depth}
// A terrain's chunk plan: kinds as stable ids, rock depth, sight, wall walks, worked trees, portcullises, chunk range.
function v3chunkCtx(T){const CS=8,KI=V3.kindIds||(V3.kindIds=new Map()),kid=T.kinds.map(k=>{const s=JSON.stringify(k);let n=KI.get(s);if(n==null){n=KI.size+1;KI.set(s,n)}return n});
 return {T,CS,BD:3,kid,depth:v3depthField(T),shp:T.z===1?v3shapes(T):null,seen:typeof T.seen==='string'&&T.seen.length===T.w*T.h?T.seen:null,wt:V3.workTrees||new Set(),walk:V3.walkTiles||new Set(),wf:V3.walkFace||new Map(),
  pc:new Set((V3.things||[]).filter(t=>t.rune&&t.rune.id==='portcullis').map(t=>t.x+','+t.y)),cx0:Math.floor(T.x0/CS),cx1:Math.floor((T.x0+T.w-1)/CS),cy0:Math.floor(T.y0/CS),cy1:Math.floor((T.y0+T.h-1)/CS)}}
// One chunk's range in the window and its signature: everything its geometry is built from.
function v3chunkSig(X,cx,cy){const T=X.T,CS=X.CS,BD=X.BD,i0=Math.max(0,cx*CS-T.x0),i1=Math.min(T.w,(cx+1)*CS-T.x0),j0=Math.max(0,cy*CS-T.y0),j1=Math.min(T.h,(cy+1)*CS-T.y0);
 let sig=(T.x0+i0)+','+(T.x0+i1)+','+(T.y0+j0)+','+(T.y0+j1)+'|';   /* the world tiles it covers: the same chunk in a shifted view is reused */
 for(let y=cy*CS-BD;y<(cy+1)*CS+BD;y++)for(let x=cx*CS-BD;x<(cx+1)*CS+BD;x++){const li=x-T.x0,lj=y-T.y0;if(li<0||lj<0||li>=T.w||lj>=T.h){sig+='~';continue}const n=lj*T.w+li,c=T.tiles[n],k=x+','+y;
  sig+=(c?X.kid[c-1]:0)+'.'+X.depth[n]+(X.seen?X.seen[n]:'')+(X.walk.has(k)?'w'+(X.wf.get(k)||''):'')+(X.wt.has(k)?'t':'')+(X.pc.has(k)?'p':'')+(X.shp?(X.shp.tag.get(k)||''):'')+' '}
 return {sig,i0,i1,j0,j1}}
// Builds one chunk (v3meshes over its range); its side lists are taken from the globals v3meshes fills.
function v3chunkBuild(X,b){V3.torchList=[];V3.hoardList=[];V3.rampH=new Map();V3.rockGeo=new Map();V3.waterList=[];V3.waterSet=new Set();V3.foamSegs=[];
 const G=b.i1>b.i0&&b.j1>b.j0?v3meshes(X.T,0,null,false,{i0:b.i0,i1:b.i1,j0:b.j0,j1:b.j1,depth:X.depth}):new Map(),geo=[];for(const [k,a] of G)if(a.length)geo.push([k,new Float32Array(a)]);
 return {sig:b.sig,v:(V3.chunkVer=(V3.chunkVer||0)+1),geo,torch:V3.torchList,hoard:V3.hoardList,water:V3.waterList,foam:V3.foamSegs,ramp:[...V3.rampH],rock:[...V3.rockGeo],wset:[...V3.waterSet]}}
// While a terrain waits (V3.pendTerr), its stale chunks are built a few ms a frame, so applying it is mostly a join.
function v3chunksWarm(T,ms){if(!T||!Array.isArray(T.tiles)||!V3.models||!V3.tchunks||V3.tchunksZ!==T.z+'|'+(V3.walkKnown?1:0))return true;const t0=performance.now(),C=V3.tchunks;
 let X=V3.warmCtx;if(!X||X.T!==T){X=V3.warmCtx=v3chunkCtx(T);X.list=[];for(let cy=X.cy0;cy<=X.cy1;cy++)for(let cx=X.cx0;cx<=X.cx1;cx++)X.list.push([cx+','+cy,v3chunkSig(X,cx,cy)])}
 const S=[V3.torchList,V3.hoardList,V3.rampH,V3.rockGeo,V3.waterList,V3.waterSet,V3.foamSegs];let done=true;
 for(const [key,b] of X.list){const E=C.get(key);if(E&&E.sig===b.sig)continue;if(performance.now()-t0>ms){done=false;break}C.set(key,v3chunkBuild(X,b));V3.tchunkWarmed=1}
 [V3.torchList,V3.hoardList,V3.rampH,V3.rockGeo,V3.waterList,V3.waterSet,V3.foamSegs]=S;return done}
function v3meshesChunked(T,old){const gl=V3.gl;if(!T||!Array.isArray(T.tiles)||!Array.isArray(T.kinds)||!V3.models){V3.tgroups=null;V3.tchunkLive=null;return v3meshes(T,0,old)}   /* v3meshes deletes old's buffers: the groups are gone */
 const zk=T.z+'|'+(V3.walkKnown?1:0);if(V3.tchunksZ!==zk||!V3.tchunks){V3.tchunks=new Map();V3.tchunksZ=zk;V3.tchunkLive=null}const C=V3.tchunks,live=new Set(),X=v3chunkCtx(T);
 const torch=[],hoard=[],water=[],foam=[],ramp=new Map(),rock=new Map(),wset=new Set();let built=0;
 for(let cy=X.cy0;cy<=X.cy1;cy++)for(let cx=X.cx0;cx<=X.cx1;cx++){const key=cx+','+cy;live.add(key);const b=v3chunkSig(X,cx,cy);
  let E=C.get(key);if(!E||E.sig!==b.sig){built++;E=v3chunkBuild(X,b);C.set(key,E)}
  for(const p of E.torch)torch.push(p);for(const p of E.hoard)hoard.push(p);for(const p of E.water)water.push(p);for(const v of E.foam)foam.push(v);for(const [k,v] of E.ramp)ramp.set(k,v);for(const [k,v] of E.rock)rock.set(k,v);for(const k of E.wset)wset.add(k)}
 // chunks that left the view are kept until they are 4 chunks (32 tiles) behind, so panning back reuses them
 for(const k of [...C.keys()])if(!live.has(k)){const q=k.indexOf(','),a=+k.slice(0,q),b=+k.slice(q+1);if(a<X.cx0-4||a>X.cx1+4||b<X.cy0-4||b>X.cy1+4)C.delete(k)}
 const liveSig=[...live].join(';');if(!built&&!V3.tchunkWarmed&&old&&old.length&&V3.tchunkLive===liveSig){V3.chunkBuilt=0;return old}V3.tchunkLive=liveSig;V3.tchunkWarmed=0;   /* chunks built while it waited are joined too */   /* nothing changed: keep the joined buffers */
 V3.torchList=torch;V3.hoardList=hoard;V3.waterList=water;V3.foamSegs=foam;V3.rampH=ramp;V3.rockGeo=rock;V3.waterSet=wset;V3.chunkBuilt=built;
 // join the chunks in groups of 2x2 (16x16 tiles), one buffer per texture per group: a change re-uploads only its group
 // (zoomed right out, one joined buffer of the whole view was ~16 MB copied and uploaded for every felled tree)
 const GS=2,G=new Map();   /* 2x2 chunks: a pan step re-joins only the groups at the edges (4x4 re-joined most of the view, up to 117 ms) */for(const k of live){const [cx,cy]=k.split(',').map(Number),gk=Math.floor(cx/GS)+','+Math.floor(cy/GS);let L=G.get(gk);if(!L){L=[];G.set(gk,L)}L.push(k)}
 const TG=V3.tgroups||(V3.tgroups=new Map()),out=[],keep=new Set();
 for(const [gk,keys] of G){const gsig=keys.map(k=>k+':'+C.get(k).v).join(';');let R=TG.get(gk);
  if(!R||R.gsig!==gsig){const len=new Map();for(const k of keys)for(const [tx,f] of C.get(k).geo)len.set(tx,(len.get(tx)||0)+f.length);
   const oldBy=new Map((R?R.meshes:[]).map(m=>[m.tex,m])),meshes=[];
   for(const [tx,n] of len){const F=new Float32Array(n);let o=0;for(const k of keys)for(const [tt,f] of C.get(k).geo)if(tt===tx){F.set(f,o);o+=f.length}
    const m=oldBy.get(tx);let buf;if(m){buf=m.buf;oldBy.delete(tx)}else buf=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,buf);gl.bufferData(gl.ARRAY_BUFFER,F,gl.STATIC_DRAW);
    const kind=T.kinds.find(x=>x.tex===tx);meshes.push({buf,count:n/12,tex:tx,color:kind?hexrgb(kind.color):[1,1,1]})}
   for(const m of oldBy.values())gl.deleteBuffer(m.buf);R={gsig,meshes};TG.set(gk,R)}
  keep.add(gk);for(const m of R.meshes){out.push(m)}}
 for(const [gk,R] of TG)if(!keep.has(gk)){for(const m of R.meshes)gl.deleteBuffer(m.buf);TG.delete(gk)}
 {const own=new Set(out.map(m=>m.buf));for(const m of old||[])if(!own.has(m.buf))gl.deleteBuffer(m.buf)}   /* buffers from a build outside the groups */
 const kindAt=(i,j)=>{if(i<0||j<0||i>=T.w||j>=T.h)return null;const c=T.tiles[j*T.w+i];return c?T.kinds[c-1]:null};v3roofs(T,kindAt,0);return out}
// The layers round the camera's level in chunks too, joined 2x2 like the ground (world-look 2026-10-25): the layer above
// the surface (V3.upper: mountain tops, wall walks, upper storeys; zoomed right out over mountains ~4,000 tiles rebuilt
// whole on every pan step, 23-28 ms of the 40-49 ms a step took) and the surface under the Sky level (V3.below at z 3,
// 40-75 ms of each change of level up there). A step builds only the chunks at the window's edges. S is a layer's store
// ({C chunks, G groups, zk, wx its warming}), yo its height. What the layer above adds to the ground's lists (torches,
// ramps, rock, water) is left out, as the ground's build always replaced it; with sides (the surface under the Sky
// level) it is added to them, as a whole build of it did.
function v3layerChunkBuild(T,X,b,yo){V3.torchList=[];V3.hoardList=[];V3.rampH=new Map();V3.rockGeo=new Map();V3.waterList=[];V3.waterSet=new Set();V3.foamSegs=[];
 const G=b.i1>b.i0&&b.j1>b.j0?v3meshes(T,yo,null,false,{i0:b.i0,i1:b.i1,j0:b.j0,j1:b.j1,depth:X.depth}):new Map(),geo=[];for(const [k,a] of G)if(a.length)geo.push([k,new Float32Array(a)]);
 return {sig:b.sig,v:(V3.chunkVer=(V3.chunkVer||0)+1),geo,torch:V3.torchList,hoard:V3.hoardList,water:V3.waterList,foam:V3.foamSegs,ramp:[...V3.rampH],rock:[...V3.rockGeo],wset:[...V3.waterSet]}}
// While a land waits (V3.pendTerr, V3.lvHold), a layer's stale chunks are built a few ms a frame (as v3chunksWarm); zk:
// the key the land will be put in with (by default as now).
function v3layerWarm(T,yo,ms,S,zk){if(!T||!Array.isArray(T.tiles)||!Array.isArray(T.kinds)||!V3.models||!S)return true;zk=(zk||T.z+'|'+(V3.walkKnown?1:0))+(yo?'|'+yo:'');if(S.zk!==zk||!S.C){S.C=new Map();S.zk=zk;S.G=null}const t0=performance.now(),C=S.C;
 let X=S.wx;if(!X||X.T!==T){X=S.wx=v3chunkCtx(T);X.list=[];for(let cy=X.cy0;cy<=X.cy1;cy++)for(let cx=X.cx0;cx<=X.cx1;cx++)X.list.push([cx+','+cy,v3chunkSig(X,cx,cy)])}
 const SV=[V3.torchList,V3.hoardList,V3.rampH,V3.rockGeo,V3.waterList,V3.waterSet,V3.foamSegs];let done=true;
 for(const [key,b] of X.list){const E=C.get(key);if(E&&E.sig===b.sig)continue;if(performance.now()-t0>ms){done=false;break}C.set(key,v3layerChunkBuild(T,X,b,yo))}
 [V3.torchList,V3.hoardList,V3.rampH,V3.rockGeo,V3.waterList,V3.waterSet,V3.foamSegs]=SV;return done}
function v3layerChunked(T,yo,old,S,sides){const gl=V3.gl;if(!T||!Array.isArray(T.tiles)||!Array.isArray(T.kinds)||!V3.models){S.G=null;S.C=null;S.zk=null;return v3meshes(T,yo,old,false)}   /* v3meshes deletes old's buffers: the groups are gone */
 const zk=T.z+'|'+(V3.walkKnown?1:0)+(yo?'|'+yo:'');if(S.zk!==zk||!S.C){S.C=new Map();S.zk=zk;S.G=null}const C=S.C,live=new Set(),X=v3chunkCtx(T);let built=0;
 const SV=[V3.torchList,V3.hoardList,V3.rampH,V3.rockGeo,V3.waterList,V3.waterSet,V3.foamSegs];
 for(let cy=X.cy0;cy<=X.cy1;cy++)for(let cx=X.cx0;cx<=X.cx1;cx++){const key=cx+','+cy;live.add(key);const b=v3chunkSig(X,cx,cy);let E=C.get(key);if(E&&E.sig===b.sig)continue;built++;C.set(key,v3layerChunkBuild(T,X,b,yo))}
 [V3.torchList,V3.hoardList,V3.rampH,V3.rockGeo,V3.waterList,V3.waterSet,V3.foamSegs]=SV;S.built=built;
 for(const k of [...C.keys()])if(!live.has(k)){const q=k.indexOf(','),a=+k.slice(0,q),b=+k.slice(q+1);if(a<X.cx0-4||a>X.cx1+4||b<X.cy0-4||b>X.cy1+4)C.delete(k)}
 const G=new Map();for(const k of live){const q=k.indexOf(','),gk=Math.floor(+k.slice(0,q)/2)+','+Math.floor(+k.slice(q+1)/2);let L=G.get(gk);if(!L){L=[];G.set(gk,L)}L.push(k)}
 const TG=S.G||(S.G=new Map()),out=[],keep=new Set();
 for(const [gk,keys] of G){const gsig=keys.map(k=>k+':'+C.get(k).v).join(';');let R=TG.get(gk);
  if(!R||R.gsig!==gsig){const len=new Map();for(const k of keys)for(const [tx,f] of C.get(k).geo)len.set(tx,(len.get(tx)||0)+f.length);
   const oldBy=new Map((R?R.meshes:[]).map(m=>[m.tex,m])),meshes=[];
   for(const [tx,n] of len){const F=new Float32Array(n);let o=0;for(const k of keys)for(const [tt,f] of C.get(k).geo)if(tt===tx){F.set(f,o);o+=f.length}
    const m=oldBy.get(tx);let buf;if(m){buf=m.buf;oldBy.delete(tx)}else buf=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,buf);gl.bufferData(gl.ARRAY_BUFFER,F,gl.STATIC_DRAW);
    const kind=T.kinds.find(x=>x.tex===tx);meshes.push({buf,count:n/12,tex:tx,color:kind?hexrgb(kind.color):[1,1,1]})}
   for(const m of oldBy.values())gl.deleteBuffer(m.buf);R={gsig,meshes};TG.set(gk,R)}
  keep.add(gk);for(const m of R.meshes)out.push(m)}
 for(const [gk,R] of TG)if(!keep.has(gk)){for(const m of R.meshes)gl.deleteBuffer(m.buf);TG.delete(gk)}
 {const own=new Set(out.map(m=>m.buf));for(const m of old||[])if(!own.has(m.buf))gl.deleteBuffer(m.buf)}   /* buffers from a whole build */
 if(sides)for(const k of live){const E=C.get(k);for(const p of E.torch)V3.torchList.push(p);for(const p of E.hoard)V3.hoardList.push(p);for(const p of E.water)V3.waterList.push(p);for(const p of E.foam)V3.foamSegs.push(p);for(const [a,b] of E.ramp)V3.rampH.set(a,b);for(const [a,b] of E.rock)V3.rockGeo.set(a,b);for(const a of E.wset)V3.waterSet.add(a)}
 if(yo===0||yo===V3.STOREY)v3roofs(T,(i,j)=>{if(i<0||j<0||i>=T.w||j>=T.h)return null;const c=T.tiles[j*T.w+i];return c?T.kinds[c-1]:null},yo);return out}
function v3buildTerrain(T){{const nm=v3meshesChunked(T,V3.tmesh);if(nm!==V3.tmesh)V3.tmeshGen=(V3.tmeshGen||0)+1;V3.tmesh=nm}v3heights(T);{const B=V3.farBuiltFor,ws=V3.waterSet?[...V3.waterSet].join(';'):'';const wet=ws!==V3.farWetSig;V3.farWetSig=ws;if(wet||!B||!T||Math.abs(B.x0-T.x0)>=8||Math.abs(B.y0-T.y0)>=8||B.w!==T.w||B.h!==T.h)v3buildFar()}
 // the land beyond takes the loaded ground's average colour, a little dimmer (unexplored)
 if(T&&Array.isArray(T.tiles)){const cnt=new Map();for(const c of T.tiles){const K=c?T.kinds[c-1]:null;if(!K||['wall','block','void','built','hole','water','lava','tree'].includes(K.kind))continue;cnt.set(c,(cnt.get(c)||0)+1)}let best=0,bc=0;for(const [c,n] of cnt)if(n>best){best=n;bc=c}if(bc){const q=MD.groundColor(T.kinds[bc-1]),st=T.kinds[bc-1].state||'';const v=[q[0]*0.95,q[1]*0.95,q[2]*0.95,1];V3.groundGrass=st.includes('grass')||st==='';if(!V3.groundAvg||v.some((x,i)=>Math.abs(x-V3.groundAvg[i])>0.02)){V3.groundAvg=v;if(V3.hor){V3.hor.stale=true;V3.horJob=null}   /* rebuilt in the new colour while the old one stays drawn */}}}}
// Water's edge on the surface: v3cornerMask gives the corners of tile (i,j) that a neighbour matching f shares, as
// bits (1: i,j  2: i+1,j  4: i+1,j+1  8: i,j+1). A land tile dips at the corners it shares with water into a bank,
// and the water's surface reaches under it, so the shore runs where the water meets the slope, not along tile edges.
// Ground darkens a little where it meets rock and walls (each corner by the solid tiles round it), so they
// stand on it instead of sitting on top of it. Worked out once, when the terrain is built.
function v3ao(kindAt,ci,cj,c,liquid){if(liquid)return c;let s=0;for(let q=0;q<4;q++){const K=kindAt(ci-(q&1),cj-(q>>1));if(!K)continue;const k=K.kind;if(k==='wall'||k==='block'||k==='built')s+=1}
 if(!s)return c;const f=Math.max(0.6,1-0.17*s);c[0]*=f;c[1]*=f;c[2]*=f;return c}
// A tuft of grass: a few thin tapered blades leaning out from a point, lighter toward the tips (they were faceted
// lumps, which up close read as green stones).
function v3tuft(a,x,y,z,c,seed){const n=5+Math.floor(MD.h(seed,0,9)*4);for(let k=0;k<n;k++){const an=MD.h(seed,k,1)*6.283,r=0.02+MD.h(seed,k,2)*0.06,bx=x+Math.cos(an)*r,bz=z+Math.sin(an)*r,h=0.11+MD.h(seed,k,3)*0.11,lean=0.03+MD.h(seed,k,4)*0.05,lx=Math.cos(an)*lean,lz=Math.sin(an)*lean,px=-Math.sin(an)*0.022,pz=Math.cos(an)*0.022,s=0.95+MD.h(seed,k,5)*0.4;
 tri(a,[bx-px,y,bz-pz],[bx+px,y,bz+pz],[bx+lx,y+h,bz+lz],[0,1,0],[Math.min(1,c[0]*s),Math.min(1,c[1]*s*1.05),Math.min(1,c[2]*s),1])}}
function v3isWater(K){return !!K&&(K.kind==='water'||K.kind==='bridge'&&(K.under||'water')==='water')}
// water at the valley floor (not a mountain lake up in its rock, Water.dm): what a bank slopes down to
function v3lowWater(K){return v3isWater(K)&&!K.lift}
function v3cornerMask(T,i,j,f){const w=(p,q)=>{if(p<0||q<0||p>=T.w||q>=T.h)return false;const c=T.tiles[q*T.w+p];return f(c?T.kinds[c-1]:null)};const a=w(i-1,j-1),b=w(i,j-1),c=w(i+1,j-1),d=w(i-1,j),e=w(i+1,j),f2=w(i-1,j+1),g=w(i,j+1),k=w(i+1,j+1);return (a||b||d?1:0)|(b||c||e?2:0)|(e||k||g?4:0)|(d||f2||g?8:0)}
function v3shore(T,K,i,j){return (T.z===1||T.z===3)&&!!K&&K.kind==='floor'&&!K.road&&!K.hoard?v3cornerMask(T,i,j,v3lowWater):0}
const SHORE_DIP=0.24;
// A river runs (View3D.dm sends each river and ford tile's dir): its flow at each corner of tile i,j in tiles a second,
// the mean of the four tiles round that corner, so it eases off by the banks and into the sea; null where nothing runs.
const V3_FLOWV={1:[0,-1],2:[0,1],4:[1,0],8:[-1,0],5:[0.7071,-0.7071],9:[-0.7071,-0.7071],6:[0.7071,0.7071],10:[-0.7071,0.7071]},V3_RUN=0.7;
function v3flowCorners(kindAt,i,j){let any=false;for(let b=-1;b<=1&&!any;b++)for(let a=-1;a<=1;a++){const n=kindAt(i+a,j+b);if(n&&n.flow){any=true;break}}if(!any)return null;
 const F=[];for(const [ci,cj] of [[i-1,j-1],[i,j-1],[i,j],[i-1,j]]){let x=0,z=0;for(const [a,b] of [[0,0],[1,0],[0,1],[1,1]]){const n=kindAt(ci+a,cj+b),v=n&&n.flow&&V3_FLOWV[n.flow];if(v){x+=v[0];z+=v[1]}}F.push(x*V3_RUN/4,z*V3_RUN/4)}return F}
// how far a bank's corner dips, varied by place so the shore wobbles instead of running in straight cuts
function v3dip(wx,wy){return SHORE_DIP*(0.62+0.76*MD.h(wx,wy,77))}
// how far corner c (0-3, as v3cornerMask's bits) of tile i,j sinks: by the share of water round it (its four tiles, the
// twelve beyond at a quarter), so a bank slopes in by how much water it faces and a diagonal river gets a diagonal
// waterline, not the tile grid's stair-steps (the owner, 10-27: "river tiles on the side needs work"); 0 where no water touches
// The rock under the surface (the layer below, drawn solid): its top just under the ground, but lower under water and
// under every bank beside it, which dips down to the water (v3cdip) and showed that rock's stone through it as a band
// of cobbles along each shore
function v3fillTop(tx,ty){const S=V3.waterSet;if(!S)return 4.94;if(S.has(tx+','+ty))return 4.4;for(let b=-1;b<=1;b++)for(let a=-1;a<=1;a++)if(S.has((tx+a)+','+(ty+b)))return 4.35;return 4.94}
function v3cdip(T,i,j,c){const ci=i-(c===0||c===3?1:0),cj=j-(c<2?1:0);let w=0,r=0;
 for(let b=-1;b<=2;b++)for(let a=-1;a<=2;a++){const p=ci+a,q=cj+b;if(p<0||q<0||p>=T.w||q>=T.h)continue;const k=T.tiles[q*T.w+p];if(!v3lowWater(k?T.kinds[k-1]:null))continue;if(a>=0&&a<=1&&b>=0&&b<=1)w++;else r++}
 return w?SHORE_DIP*2*Math.min(1,(w+0.25*r)/7)*(0.8+0.4*MD.h(T.x0+ci+1,T.y0+cj+1,77)):0}
// Ground height under each tile of the detailed area (mountain tops rise with rock
// depth, as v3meshes builds them), so the camera never dips into a hillside.
function v3heights(T){V3.hgt=null;
 // a dragon's lair underground: its gold is heaped up, so everything stands on top of the heaps (v3hoard)
 if(T&&Array.isArray(T.tiles)&&Array.isArray(T.kinds)&&(T.z===2||T.z===4)&&T.kinds.some(K=>K&&K.hoard)){const n=T.w*T.h,H=new Float32Array(n);for(let k=0;k<n;k++){const c=T.tiles[k],K=c?T.kinds[c-1]:null;H[k]=K&&K.hoard?[0,0.07,0.42,0.72][K.hoard]:0}V3.hgt={x0:T.x0,y0:T.y0,w:T.w,h:T.h,H};return}
 if(!T||!Array.isArray(T.tiles)||!(T.z===1||T.z===3))return;const n=T.w*T.h,d=new Int16Array(n),q=[];
 for(let k=0;k<n;k++){const c=T.tiles[k],K=c?T.kinds[c-1]:null;if(!K||K.kind!=='wall'){d[k]=0;q.push(k)}else d[k]=999}
 for(let h=0;h<q.length;h++){const k=q[h],i=k%T.w,j=(k/T.w)|0;for(const [a,b] of [[1,0],[-1,0],[0,1],[0,-1]]){const x=i+a,y=j+b;if(x<0||y<0||x>=T.w||y>=T.h)continue;const m=y*T.w+x;if(d[m]>d[k]+1){d[m]=d[k]+1;q.push(m)}}}
 const H=new Float32Array(n);for(let k=0;k<n;k++){const c=T.tiles[k],K=c?T.kinds[c-1]:null;H[k]=K&&K.kind==='wall'&&K.blocks?K.blocks+0.4:K&&K.kind==='carve'&&K.carve?(K.carve[3]+0.4)*(K.carve[0]-0.5)/K.carve[1]:d[k]?MH(d[k]):0;
  if(K&&K.lift)H[k]=K.lift;   // a mountain lake, up in its rock
  const sm=K&&K.kind==='floor'?v3shore(T,K,k%T.w,(k/T.w)|0):0;if(sm){const x=T.x0+k%T.w,y=T.y0+((k/T.w)|0);H[k]-=(v3cdip(T,k%T.w,(k/T.w)|0,0)+v3cdip(T,k%T.w,(k/T.w)|0,2))/2}}
 if(T.z===3&&V3.SKYH)for(let k=0;k<n;k++){const c=T.tiles[k],K=c?T.kinds[c-1]:null;if(K&&K.kind!=='wall')H[k]=v3skyY(T,K,0)}   /* layer 3's tiles at their heights (plan B) */
 V3.hgt={x0:T.x0,y0:T.y0,w:T.w,h:T.h,H}}
function v3groundAt(x,y){const G=V3.hgt;if(G){const i=Math.round(x)-G.x0,j=Math.round(y)-G.y0;if(i>=0&&j>=0&&i<G.w&&j<G.h)return G.H[j*G.w+i]}const F=V3.farH;if(F){const i=Math.floor((x-F.x0)/4),j=Math.floor((y-F.y0)/4);if(i>=0&&j>=0&&i<F.w&&j<F.h)return F.H[j*F.w+i]}return 0}
// The far view: explored land out to ~160 tiles as 4x4-tile cells (the world
// map's own colours). Rock cells rise with their depth into the range, like the
// near mountains, with snow on the highest; forests get a few pines. Cells the
// detailed area covers sink under it so the two meet without a seam.
const FARK={'#655e4a':'rock','#25442c':'tree','#31586a':'water','#a35032':'lava'};
// World-map colours -> the 3D ground palette (MD.groundColor), so far land matches near land.
const FARC={'#314c35':[0.27,0.43,0.19],'#25442c':[0.27,0.43,0.19],'#9c8757':[0.82,0.72,0.48],'#a2b8bb':[0.86,0.89,0.92],'#64616b':[0.36,0.33,0.32],'#31586a':[0.2,0.4,0.55],'#a35032':[0.85,0.35,0.1],'#7a6448':[0.42,0.3,0.18],'#8a6a44':[0.5,0.34,0.2]};
// It is built a few ms a frame (v3bgWork) while the last one stays drawn, then swapped in: at once it took 8-14 ms, on
// nearly every terrain step of a pan (the near water moves with the window). With none drawn yet, or now, at once.
function v3buildFar(now){V3.farJob=null;const J=v3farJob();J.next();if(now||!(V3.far&&V3.far.length)||V3.z!==1&&V3.z!==3||!Array.isArray(V3.farData)||!V3.farData.length){while(!J.next().done);}else V3.farJob=J}
function* v3farJob(){const gl=V3.gl,F=V3.farData,T=V3.terrain,W=V3.waterSet,night=V3.night,camx=V3.cx,camy=V3.cy;V3.farBuiltFor=T?{x0:T.x0,y0:T.y0,w:T.w,h:T.h}:null;yield;   /* what it is built from, taken when it is asked for */
 const swap=(far,farH)=>{(V3.far||[]).forEach(m=>gl.deleteBuffer(m.buf));V3.far=far;V3.farH=farH};if(!gl||!Array.isArray(F)||!F.length||V3.z!==1&&V3.z!==3){swap([],null);return}   /* on the Sky level too: the surface's, drawn under it */
 let cx0=1e9,cy0=1e9,cx1=-1e9,cy1=-1e9;for(const c of F){cx0=Math.min(cx0,c[0]);cy0=Math.min(cy0,c[1]);cx1=Math.max(cx1,c[0]);cy1=Math.max(cy1,c[1])}
 const w=(cx1-cx0+1)*4,h=(cy1-cy0+1)*4,col=new Array(w*h).fill(''),seen=new Uint8Array(w*h);for(const c of F){const cells=c[2]||[],sm=typeof c[3]==='string'?c[3]:'1111111111111111';for(let j=0;j<4;j++)for(let i=0;i<4;i++){const v=cells[j*4+i],k=((c[1]-cy0)*4+j)*w+(c[0]-cx0)*4+i;if(v)col[k]=v;seen[k]=sm[j*4+i]==='1'?1:0}}
 const x0=cx0*16+1,y0=cy0*16+1;yield;// tile at the lower-left corner of cell (0,0)
 // A mountain's middle is never in sight, so it is never explored. Unknown cells
 // that open ground can't reach without crossing rock are inside a range: rock.
 {const open=new Uint8Array(w*h),q=[];for(let k=0;k<w*h;k++)if(col[k]&&FARK[col[k]]!=='rock'){open[k]=1;q.push(k)}
  for(let a=0;a<q.length;a++){const k=q[a],i=k%w,j=(k/w)|0;for(const [u,v] of [[1,0],[-1,0],[0,1],[0,-1]]){const x=i+u,y=j+v;if(x<0||y<0||x>=w||y>=h)continue;const m=y*w+x;if(!open[m]&&!col[m]){open[m]=1;q.push(m)}}}
  for(let k=0;k<w*h;k++)if(!col[k]&&!open[k]){const i=k%w,j=(k/w)|0;let rock=0;for(const [u,v] of [[1,0],[-1,0],[0,1],[0,-1]]){const x=i+u,y=j+v;if(x>=0&&y>=0&&x<w&&y<h&&(FARK[col[y*w+x]]==='rock'||(!col[y*w+x]&&!open[y*w+x])))rock++}if(rock)col[k]='#655e4a'}}
 yield;const d=new Int16Array(w*h),q=[];for(let k=0;k<w*h;k++){if(FARK[col[k]]!=='rock'){d[k]=0;q.push(k)}else d[k]=999}
 for(let a=0;a<q.length;a++){const k=q[a],i=k%w,j=(k/w)|0;for(const [u,v] of [[1,0],[-1,0],[0,1],[0,-1]]){const x=i+u,y=j+v;if(x<0||y<0||x>=w||y>=h)continue;const m=y*w+x;if(d[m]>d[k]+1){d[m]=d[k]+1;q.push(m)}}}
 yield;const inNear=(i,j)=>{if(!T)return false;const tx=x0+i*4,ty=y0+j*4;return tx+3>=T.x0&&tx<=T.x0+T.w-1&&ty+3>=T.y0&&ty<=T.y0+T.h-1};
 // under nearby water the far land dips, so the pond's basin isn't covered
 const farWet=(i,j)=>{if(!W||!W.size)return false;const tx=x0+i*4,ty=y0+j*4;for(let b=0;b<4;b++)for(let a=0;a<4;a++)if(W.has((tx+a)+','+(ty+b)))return true;return false};
 const Hc=new Float32Array(w*h);for(let k=0;k<w*h;k++){const kind=FARK[col[k]],i=k%w,j=(k/w)|0;Hc[k]=inNear(i,j)?(farWet(i,j)?-0.7:-0.08):kind==='rock'?MH(d[k]*4-2):kind==='water'?-0.12:-0.02}
 const farH={x0,y0,w,h,H:Hc};yield;
 // corner heights: the mean of the known cells that share the corner
 const corner=(i,j)=>{let s=0,n=0;for(const [a,b] of [[i-1,j-1],[i,j-1],[i-1,j],[i,j]]){if(a<0||b<0||a>=w||b>=h||!col[b*w+a])continue;s+=Hc[b*w+a];n++}return n?s/n:0};
 const C=new Float32Array((w+1)*(h+1));for(let j=0;j<=h;j++)for(let i=0;i<=w;i++)C[j*(w+1)+i]=corner(i,j);yield;
 const HZ=night?[0.12,0.13,0.18]:[0.6,0.68,0.74],fz=!!(V3.fog&&V3.fog.z===1&&!V3.farFogOff);const haze=(k,c)=>seen[k]||fz?c:[c[0]*0.7+HZ[0]*0.3,c[1]*0.7+HZ[1]*0.3,c[2]*0.7+HZ[2]*0.3];
 const tint=(k,y,wx,wy)=>{const v=0.88+MD.vn(wx,wy,7,3)*0.2,kind=FARK[col[k]];if(kind==='rock'){if(y>6.6)return haze(k,[0.93,0.94,0.97]);const s=(0.78+Math.min(0.3,y*0.025))*v;return haze(k,[0.47*s,0.43*s,0.36*s])}const c=FARC[col[k]]||hexrgb(col[k]);return haze(k,[c[0]*v,c[1]*v,c[2]*v])};
 const a=(V3.farV||(V3.farV=new VA())).reset();for(let j=0;j<h;j++)for(let i=0;i<w;i++){if(!i)yield;const k=j*w+i;if(!col[k]||Hc[k]===-0.08)continue;
  // cell corners in world space (x east, y up, z = -tile y)
  const X0=x0+i*4-0.5,X1=X0+4,Z0=-(y0+j*4-0.5),Z1=Z0-4;const p00=[X0,C[j*(w+1)+i],Z0],p10=[X1,C[j*(w+1)+i+1],Z0],p11=[X1,C[(j+1)*(w+1)+i+1],Z1],p01=[X0,C[(j+1)*(w+1)+i],Z1];
  const nx=(p00[1]-p10[1])/4,nz=(p01[1]-p00[1])/4,nl=Math.hypot(nx,1,nz),n=[nx/nl,1/nl,-nz/nl];
  quad4(a,p00,p10,p11,p01,n,tint(k,p00[1],p00[0],-p00[2]),tint(k,p10[1],p10[0],-p10[2]),tint(k,p11[1],p11[0],-p11[2]),tint(k,p01[1],p01[0],-p01[2]));
  if(FARK[col[k]]==='tree'&&Math.hypot(x0+i*4+1.5-camx,y0+j*4+1.5-camy)>26){const wx=x0+i*4,wy=y0+j*4;for(let t=0;t<6;t++){const px=X0+0.5+MD.h(wx,wy,t)*3,pz=Z0-0.5-MD.h(wx,wy,t+7)*3,py=Hc[k],pine=MD.h(wx,wy,t+11)<0.5,th=(pine?4.8:3.6)+MD.h(wx,wy,t+3)*1.2,r=(pine?0.95:1.1)+MD.h(wx,wy,t+5)*0.3,sh=0.75+MD.h(wx,wy,t+9)*0.35;
   const g=haze(k,pine?[0.11*sh,0.3*sh,0.17*sh]:[0.2*sh,0.42*sh,0.16*sh]).concat(1),top=[px,py+th,pz];
   if(pine){const B=[[px-r,py,pz-r],[px+r,py,pz-r],[px+r,py,pz+r],[px-r,py,pz+r]];for(let e=0;e<4;e++){const b0=B[e],b1=B[(e+1)%4];const m=[(b0[0]+b1[0])/2-px,0.6,(b0[2]+b1[2])/2-pz],ml=Math.hypot(...m);tri(a,b0,b1,top,[m[0]/ml,m[1]/ml,m[2]/ml],[g[0]*(0.85+e*0.06),g[1]*(0.85+e*0.06),g[2],1])}}
   else{const cy=py+th*0.75,ring=[[px-r,cy,pz],[px,cy,pz-r],[px+r,cy,pz],[px,cy,pz+r]],up=[px,cy+r*0.9,pz],dn=[px,py+th*0.3,pz];for(let e=0;e<4;e++){const b0=ring[e],b1=ring[(e+1)%4];for(const tip of [up,dn]){const m=[(b0[0]+b1[0])/2-px,tip===up?0.7:-0.4,(b0[2]+b1[2])/2-pz],ml=Math.hypot(...m);const f=tip===up?1:0.7;if(tip===up)tri(a,b0,b1,tip,[m[0]/ml,m[1]/ml,m[2]/ml],[g[0]*f,g[1]*f,g[2]*f,1]);else tri(a,b1,b0,tip,[m[0]/ml,m[1]/ml,m[2]/ml],[g[0]*f,g[1]*f,g[2]*f,1])}}}}}}
 if(!a.length){swap([],farH);return}const buf=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,buf);gl.bufferData(gl.ARRAY_BUFFER,a.f.subarray(0,a.length),gl.STATIC_DRAW);swap([{buf,count:a.length/12}],farH)}
function v3meshes(T,yo,old,fill,opt){const gl=V3.gl;if(yo===0&&!fill&&!opt){V3.torchList=[];V3.hoardList=[];V3.rampH=new Map();V3.rockGeo=new Map()}if(!T||!Array.isArray(T.tiles)||!Array.isArray(T.kinds)){(old||[]).forEach(m=>gl.deleteBuffer(m.buf));return []}if(yo===0&&T&&!opt){V3.waterList=[];V3.waterSet=new Set();V3.foamSegs=[]}const oldList=old||[];const out=[];const groups=new Map();
 // Rock depth: distance from each wall tile to open ground, so mountains rise to a peak.
 const depth=opt&&opt.depth?opt.depth:new Int16Array(T.w*T.h);if(!(opt&&opt.depth)){const q=[];for(let j=0;j<T.h;j++)for(let i=0;i<T.w;i++){const c=T.tiles[j*T.w+i];const k=c?T.kinds[c-1]:null;if(!k||k.kind!=='wall'){depth[j*T.w+i]=0;q.push(i,j)}else depth[j*T.w+i]=999}
  for(let h=0;h<q.length;h+=2){const i=q[h],j=q[h+1],d=depth[j*T.w+i];[[1,0],[-1,0],[0,1],[0,-1]].forEach(([a,b])=>{const x=i+a,y=j+b;if(x<0||y<0||x>=T.w||y>=T.h)return;const n=y*T.w+x;if(depth[n]>d+1){depth[n]=d+1;q.push(x,y)}})}}let touch=null;const g=k=>{let a=groups.get(k);if(!a){a=[];groups.set(k,a)}if(touch&&!touch.has(a))touch.set(a,a.length);return a};
 // Tiles the map can't see (behind trees and walls) are drawn dark, like the map's black.
 const seen=typeof T.seen==='string'&&T.seen.length===T.w*T.h?T.seen:null;const dimDone=()=>{if(!touch)return;const f=touch.dark?0.04:0.3;for(const [a,st] of touch)for(let v=st;v<a.length;v+=12){a[v+8]*=f;a[v+9]*=f;a[v+10]*=f*1.15}touch=null};
 const kindAt=(i,j)=>{if(i<0||j<0||i>=T.w||j>=T.h)return null;const c=T.tiles[j*T.w+i];return c?T.kinds[c-1]:null};
 const I0=opt?opt.i0:0,I1=opt?opt.i1:T.w,J0=opt?opt.j0:0,J1=opt?opt.j1:T.h;
 for(let j=J0;j<J1;j++)for(let i=I0;i<I1;i++){dimDone();const K=kindAt(i,j);if(!K||K.kind==='walk'||K.kind==='peak')continue;
  if(yo===0&&K.kind!=='built'&&V3.walkTiles&&V3.walkTiles.has((T.x0+i)+','+(T.y0+j)))v3gateArch(g(''),T,kindAt,i,j);if(seen&&seen[j*T.w+i]!=='1'&&!(K.kind==='wall'&&(T.z===1||T.z===3))){touch=new Map();touch.dark=seen[j*T.w+i]==='0'}const tx=T.x0+i,ty=T.y0+j,X=tx,Z=-ty,h=0.5;const W=[1,1,1,1];const Y=v3skyY(T,K,yo)+(K.lift&&T.z===1?K.lift:0);if(K.roof&&!fill&&K.kind!=='wall'&&V3.models){const G=T.z===1?v3rockStack(g,T,kindAt,i,j,X,Y,Z,K):v3cutRock(g,T,kindAt,i,j,X,Y,Z,K,K.ceil||2,false);if(yo===0)V3.rockGeo.set(tx+','+ty,G)}if(K.kind==='carve'&&K.carve&&!fill)v3carveRock(g,T,kindAt,i,j,X,Y,Z,K);
  if(K.kind==='hole'){quad(g(''),[X-h,Y-0.03,Z+h],[X+h,Y-0.03,Z+h],[X+h,Y-0.03,Z-h],[X-h,Y-0.03,Z-h],[0,1,0],[0.02,0.02,0.02,1]);box(g(''),X-0.18,Z,Y-0.6,Y+0.25,0.03,[0.45,0.3,0.15,1]);box(g(''),X+0.18,Z,Y-0.6,Y+0.25,0.03,[0.45,0.3,0.15,1]);continue}
  if(K.kind==='stairsup'||K.kind==='stairsdown'||K.kind==='ramp'){if(K.state&&String(K.state).startsWith('lift'))continue;   // a lift (Lifts.dm): its models draw it
   const up=K.kind!=='stairsdown',st=[0.56,0.42,0.3,1];if(!up&&yo>0)continue;
   // Up stairs beside a wall with a walk rise towards that wall (a ramp onto it); others rise to the north.
   // In a corner touching two walls, the wall is the one the run lies along (ramp/stairs neighbours tell which).
   let dx=0,dz=-1;if(up&&V3.walkTiles){const kq=(p,q)=>{const k=kindAt(p,q);return k&&!String(k.state||'').startsWith('lift')?k.kind:''},rq=(p,q)=>kq(p,q)==='stairsup'||kq(p,q)==='ramp',ax0=rq(i-1,j)||rq(i+1,j),az0=rq(i,j-1)||rq(i,j+1);
    const cand=ax0&&!az0?[[0,1],[0,-1]]:az0&&!ax0?[[1,0],[-1,0]]:[[0,1],[1,0],[0,-1],[-1,0]];for(const [a1,b1] of cand)if(V3.walkTiles.has((tx+a1)+','+(ty+b1))){dx=a1;dz=-b1;break}}
   if(!up)quad(g(''),[X-h,Y-0.02,Z+h],[X+h,Y-0.02,Z+h],[X+h,Y-0.02,Z-h],[X-h,Y-0.02,Z-h],[0,1,0],[0.05,0.04,0.03,1]);
   const hug=up&&V3.walkTiles&&(dx||dz!==-1||V3.walkTiles.has(tx+','+(ty+1))),R=V3.STOREY/5,sc=MD.shade(st,0.8);
   if(K.kind==='ramp'&&!hug){quad(g(''),[X-h,Y+0.03,Z+h],[X+h,Y+0.03,Z+h],[X+h,Y+0.03,Z-h],[X-h,Y+0.03,Z-h],[0,1,0],[0.6,0.57,0.52,0.99]);continue}
   if(hug){// a stone ramp joined to the wall, rising along it; stairs in a row along the wall make one long slope
    // The run: ramp tiles and stairs in a row along the wall. It rises towards the stairs (its head, where units
    // step onto the walk); a run without stairs at either end rises towards +x / north.
    const ax=dz?1:0,az=dx?1:0,kk=(p,q)=>{const k=kindAt(p,q);return k&&!String(k.state||'').startsWith('lift')?k.kind:''},isR=(p,q)=>kk(p,q)==='stairsup'||kk(p,q)==='ramp';let back=0,fwd=0;
    while(back<8&&isR(i-ax*(back+1),j-az*(back+1)))back++;while(fwd<8&&isR(i+ax*(fwd+1),j+az*(fwd+1)))fwd++;
    const L=back+fwd+1,rev=kk(i-ax*back,j-az*back)==='stairsup'&&kk(i+ax*fwd,j+az*fwd)!=='stairsup',pos=rev?fwd:back;
    const wk=kindAt(i+dx,j-dz),wood=!!wk&&(!!wk.wood||(wk.state||'').includes('wood')),y0=Y+V3.STOREY*pos/L,y1=Y+V3.STOREY*(pos+1)/L,c=[0.6,0.57,0.52,0.99],c0=[0.47,0.33,0.21,1];if(V3.rampH)V3.rampH.set(tx+','+ty,(y0+y1)/2-Y);
    // the ramp covers the tile; its top slopes from y0 to y1 in the rising direction
    const xa=X-h,xb=X+h,za=Z-h,zb=Z+h,f=(x,z)=>ax?(rev?(xb-x)/(xb-xa):(x-xa)/(xb-xa)):(rev?(z-za)/(zb-za):(zb-z)/(zb-za)),top=(x,z)=>y0+(y1-y0)*f(x,z);
    if(wood){
     // A timber ramp up a timber wall: a smooth slope of planks with cleats across, boarded down its open side (away
     // from the wall) to the ground, a hand rail on a post above that side.
     const a=g(''),gx=ax?(top(xb,Z)-top(xa,Z)):0,gz=ax?0:(top(X,zb)-top(X,za)),nl=Math.hypot(gx,1,gz),nrm=[-gx/nl,1/nl,-gz/nl];
     for(let q=0;q<5;q++){const u0=q/5+0.003,u1=(q+1)/5-0.003,c=MD.shade(c0,0.92+MD.h(tx*5+q,ty,71)*0.16);
      if(ax){const x0=xa+u0,x1=xa+u1;quad(a,[x0,top(x0,Z)+0.02,zb],[x1,top(x1,Z)+0.02,zb],[x1,top(x1,Z)+0.02,za],[x0,top(x0,Z)+0.02,za],nrm,c)}
      else{const z0=za+u0,z1=za+u1;quad(a,[xa,top(X,z1)+0.02,z1],[xb,top(X,z1)+0.02,z1],[xb,top(X,z0)+0.02,z0],[xa,top(X,z0)+0.02,z0],nrm,c)}}
     quad(a,[xa,Y,zb],[xb,Y,zb],[xb,Y,za],[xa,Y,za],[0,1,0],MD.shade(c0,0.45));
     for(const u of [0.25,0.75]){const cc=MD.shade(c0,0.7);if(ax){const x=xa+u;MD.rod(a,[x,top(x,Z)+0.045,za+0.04],[x,top(x,Z)+0.045,zb-0.04],0.025,4,cc,tx+u*8)}
      else{const z=za+u;MD.rod(a,[xa+0.04,top(X,z)+0.045,z],[xb-0.04,top(X,z)+0.045,z],0.025,4,cc,ty+u*8)}}
     // the open side, boarded: four upright boards to a tile, each cut to the slope
     const e=dx?X-dx*h:Z-dz*h;for(let q=0;q<4;q++){const u0=q/4,u1=(q+1)/4,c=MD.shade(c0,0.66+MD.h(tx*3+q,ty,73)*0.14);
      if(ax){const x0=xa+u0,x1=xa+u1;if(dz<0)quad(a,[x0,Y,e],[x1,Y,e],[x1,top(x1,Z),e],[x0,top(x0,Z),e],[0,0,1],c);else quad(a,[x1,Y,e],[x0,Y,e],[x0,top(x0,Z),e],[x1,top(x1,Z),e],[0,0,-1],c)}
      else{const z0=za+u0,z1=za+u1;if(dx<0)quad(a,[e,Y,z1],[e,Y,z0],[e,top(X,z0),z0],[e,top(X,z1),z1],[1,0,0],c);else quad(a,[e,Y,z0],[e,Y,z1],[e,top(X,z1),z1],[e,top(X,z0),z0],[-1,0,0],c)}}
     // the high end, where nothing carries on beyond it: boarded too
     const hiX=ax?(rev?xa:xb):X,hiZ=ax?Z:(rev?zb:za),nx=ax?(rev?-1:1):0,nz=ax?0:(rev?1:-1),beyond=kindAt(i+nx,j-nz);
     if(!beyond||!['built','wall','ramp','stairsup'].includes(beyond.kind)){const ty1=top(hiX,hiZ),c=MD.shade(c0,0.6);
      if(ax){if(nx>0)quad(a,[hiX,Y,zb],[hiX,Y,za],[hiX,ty1,za],[hiX,ty1,zb],[1,0,0],c);else quad(a,[hiX,Y,za],[hiX,Y,zb],[hiX,ty1,zb],[hiX,ty1,za],[-1,0,0],c)}
      else{if(nz<0)quad(a,[xb,Y,hiZ],[xa,Y,hiZ],[xa,ty1,hiZ],[xb,ty1,hiZ],[0,0,-1],c);else quad(a,[xa,Y,hiZ],[xb,Y,hiZ],[xb,ty1,hiZ],[xa,ty1,hiZ],[0,0,1],c)}}
     const rc=MD.shade(c0,0.55),re=dx?X-dx*(h-0.06):Z-dz*(h-0.06),p0=ax?[xa,top(xa,Z)+0.5,re]:[re,top(X,za)+0.5,za],p1=ax?[xb,top(xb,Z)+0.5,re]:[re,top(X,zb)+0.5,zb];
     MD.rod(a,p0,p1,0.032,5,rc,tx*5+ty);const mx=ax?X:re,mz=ax?re:Z;MD.prism(a,mx,mz,Y,top(mx,mz)+0.52,0.05,0.045,5,rc,tx*7+ty);
     continue}
    // Solid stone steps, four to a tile, rising along the run; a stepped parapet on the open side (away from the wall).
    const n=4;for(let st=0;st<n;st++){const u0=st/n,u1=(st+1)/n,hy=y0+(y1-y0)*u1;let bx0,bx1,bz0,bz1;
     if(ax){bz0=za;bz1=zb;if(rev){bx0=xb-(xb-xa)*u1;bx1=xb-(xb-xa)*u0}else{bx0=xa+(xb-xa)*u0;bx1=xa+(xb-xa)*u1}}
     else{bx0=xa;bx1=xb;if(rev){bz0=za+(zb-za)*u0;bz1=za+(zb-za)*u1}else{bz0=zb-(zb-za)*u1;bz1=zb-(zb-za)*u0}}
     boxr(g(''),bx0,bx1,bz0,bz1,Y,hy,MD.shade(c,0.9+((st+pos*n)%2)*0.05));
     if(dx){const e=X-dx*h,i0=e+dx*0.13;boxr(g(''),Math.min(e,i0),Math.max(e,i0),bz0,bz1,hy,hy+0.4,MD.shade(c,0.86))}
     else{const e=Z-dz*h,i0=e+dz*0.13;boxr(g(''),bx0,bx1,Math.min(e,i0),Math.max(e,i0),hy,hy+0.4,MD.shade(c,0.86))}}
    continue}
   for(let k=0;k<5;k++){const f0=-h+k*0.2,f1=f0+0.2,y0=up?Y:Y-R*(k+1),y1=up?Y+R*(k+1):Y-R*k,c=MD.shade(st,0.9+MD.h(tx,ty,k)*0.15);if(dx)boxr(g(''),X+Math.min(dx*f0,dx*f1),X+Math.max(dx*f0,dx*f1),Z-0.42,Z+0.42,y0,y1,c);else boxr(g(''),X-0.42,X+0.42,Z+Math.min(dz*f0,dz*f1),Z+Math.max(dz*f0,dz*f1),y0,y1,c)}continue}
  if(K.kind==='built'&&V3.models){const H=V3.STOREY,solid=n=>{const q=kindAt(n[0],n[1]);return q&&(q.kind==='built'||q.kind==='wall')};
   const N=solid([i,j+1]),S=solid([i,j-1]),E=solid([i+1,j]),Wt=solid([i-1,j]);const a=g('');
   const st=K.state||'',wood=K.wood||st.includes('wood')||st.includes('log'),bone=st.includes('bone'),base=wood?[0.47,0.33,0.21]:bone?[0.85,0.82,0.72]:[0.6,0.57,0.52];
   // A wall beside built floor belongs to a room (a house); any other wall stands in the open (a defence).
   const walk=yo===0&&!!(V3.walkTiles&&V3.walkTiles.has(tx+','+ty));let room=false;if(V3.walkKnown&&yo===0)room=!walk;else for(let di=-1;di<=1;di++)for(let dj=-1;dj<=1;dj++){const q=kindAt(i+di,j+dj);if(q&&(q.kind==='bfloor'||q.kind==='stairsup'||q.kind==='stairsdown'))room=true}
   const runs=[];if(N)runs.push([0,-1]);if(S)runs.push([0,1]);if(E)runs.push([1,0]);if(Wt)runs.push([-1,0]);
   const straight=runs.length===2&&runs[0][0]===-runs[1][0]&&runs[0][1]===-runs[1][1];
   // Under a tower the round wall leaves the block's corners open: those show the ground around, not a wall's footprint.
   if(v3towerAt(kindAt,i,j)){const gc=c=>MD.groundCorner(T,kindAt,c[0],c[1],[0.36,0.45,0.25],false);quad4(a,[X-h,Y,Z+h],[X+h,Y,Z+h],[X+h,Y,Z-h],[X-h,Y,Z-h],[0,1,0],gc([i,j]),gc([i+1,j]),gc([i+1,j+1]),gc([i,j+1]))}
   else quad(a,[X-h,Y,Z+h],[X+h,Y,Z+h],[X+h,Y,Z-h],[X-h,Y,Z-h],[0,1,0],MD.shade(base,0.55));
   // Race walls (Buildings.dm lairs and race buildings): spider silk, Devourer flesh, elven carved wood, tribal bamboo.
   // Each tile is one block up to the storey (a room's wall) or to the walk (walkable top at exactly Y+STOREY), its
   // open faces dressed by race; faces between wall tiles are culled, so rows side by side merge into one wide wall.
   const race=st.includes('silk')?'silk':st.includes('devourer')?'flesh':st.includes('elf')?'elf':st.includes('tribal')?'tribal':null;
   if(race){
    const HW=V3.STOREY,isW=(p,q)=>{const k=kindAt(p,q);return !!k&&(k.kind==='built'||k.kind==='wall')},ramp=(p,q)=>{const k=kindAt(p,q);return !!k&&(k.kind==='stairsup'||k.kind==='ramp')};
    const R4={2:[i,j-1],1:[i,j+1],4:[i+1,j],8:[i-1,j]},sides=[isW(i,j-1)?0:1,isW(i,j+1)?0:1,isW(i+1,j)?0:1,isW(i-1,j)?0:1],open=[2,1,4,8].filter((bt,k)=>sides[k]&&!ramp(...R4[bt]));
    const face=V3.walkFace&&V3.walkFace.get(tx+','+ty)||0,outer=bt=>!face||!!(face&bt),pt=(bt,u,d)=>bt===2?[X+u,Z+h+d]:bt===1?[X+u,Z-h-d]:bt===4?[X+h+d,Z+u]:[X-h-d,Z+u];
    const band=(bt,d,y0,y1,c)=>{const p=pt(bt,-h,0),q=pt(bt,h,d);boxr(a,Math.min(p[0],q[0]),Math.max(p[0],q[0]),Math.min(p[1],q[1]),Math.max(p[1],q[1]),y0,y1,c)};
    const RB={silk:[0.86,0.85,0.8],flesh:[0.52,0.17,0.2],elf:[0.76,0.74,0.66],tribal:[0.62,0.6,0.36]}[race],c=k=>MD.shade(RB,k),top=walk?HW:H,sd=tx*31+ty*17;
    boxr(a,X-h,X+h,Z-h,Z+h,Y,Y+top,c(0.88+MD.h(tx,ty,140)*0.08),sides);
    for(const bt of open){const out=walk&&outer(bt);
     if(race==='silk'){
      // silk strands criss-crossing the face; a soft roll of silk along the top (higher on a walk's outer edge)
      for(let q=0;q<3;q++){const y0=Y+0.1+q*top*0.28,y1=Math.min(Y+top-0.05,y0+top*0.3),p0=pt(bt,-h,0.012),p1=pt(bt,h,0.012);MD.rod(a,[p0[0],y0,p0[1]],[p1[0],y1,p1[1]],0.01,3,c(1.1),sd+q);MD.rod(a,[p0[0],y1,p0[1]],[p1[0],y0,p1[1]],0.01,3,c(1.1),sd+q+7)}
      {const [x,z]=pt(bt,0,-0.07),ns=bt===2||bt===1;MD.blob(a,x,Y+top+(out?0.08:0.01),z,ns?0.5:0.11,out?0.14:0.05,ns?0.11:0.5,c(1.04),sd+bt,0.12)}}
     else if(race==='flesh'){
      // swellings and dark veins on the face; bone spikes along a walk's outer edge, a fleshy lip elsewhere
      for(let q=0;q<2;q++){const u=(MD.h(q,sd+bt,141)-0.5)*0.5,y=Y+0.3+MD.h(q,sd+bt,142)*(top-0.6),[x,z]=pt(bt,u,-0.02);MD.blob(a,x,y,z,0.16,0.2,0.16,c(1.05+MD.h(q,sd,143)*0.15),sd+q+bt,0.3)}
      for(let q=0;q<2;q++){const u=-0.3+q*0.6,p0=pt(bt,u,0.01),p1=pt(bt,u+(MD.h(q,sd+bt,144)-0.5)*0.3,0.01);MD.rod(a,[p0[0],Y+0.05,p0[1]],[p1[0],Y+top-0.1,p1[1]],0.018,4,[0.3,0.07,0.14,1],sd+q)}
      if(out)for(let q=0;q<3;q++){const [x,z]=pt(bt,-h+0.17+q*0.33,-0.08);MD.cone(a,x,z,Y+top,Y+top+0.4,0.06,5,[0.88,0.84,0.72,1],sd+q+bt)}
      else{const [x,z]=pt(bt,0,-0.1);MD.blob(a,x,Y+top+0.02,z,0.3,0.06,0.3,c(0.95),sd+bt,0.25)}}
     else if(race==='elf'){
      // pale carved wood: silver bands at sill and cornice, slender ribs rising to leaf tips (taller on a walk's
      // outer edge, with a rail between them)
      band(bt,0.03,Y+0.22,Y+0.3,[0.82,0.84,0.86,1]);band(bt,0.03,Y+top-0.12,Y+top,[0.82,0.84,0.86,1]);
      const tips=[];for(let q=0;q<2;q++){const [x,z]=pt(bt,-h/2+q*h,0.03),hh=top+(out?0.5:0.14);MD.prism(a,x,z,Y,Y+hh,0.05,0.032,6,c(1.1),sd+q+bt);MD.blob(a,x,Y+hh+0.08,z,0.05,0.12,0.05,[0.6,0.72,0.55,1],sd+q+bt,0.1);tips.push([x,Y+hh-0.08,z])}
      if(out)MD.rod(a,tips[0],tips[1],0.022,5,[0.82,0.84,0.86,1],sd+bt)}
     else{
      // tribal: bamboo poles over woven matting, bound with two cords; on a walk the poles rise into a fence
      for(let q=0;q<5;q++){const [x,z]=pt(bt,-h+0.1+q*0.2,0.03),hh=top+(out?0.38:0.04)+MD.h(q,sd+bt,145)*0.08;MD.prism(a,x,z,Y,Y+hh,0.045,0.042,6,c(1+MD.h(q,sd+bt,146)*0.15),sd+q+bt)}
      for(const y of [Y+top*0.3,Y+top*0.75]){const p0=pt(bt,-h,0.08),p1=pt(bt,h,0.08);MD.rod(a,[p0[0],y,p0[1]],[p1[0],y,p1[1]],0.016,4,[0.4,0.28,0.16,1],sd)}}}
    continue}
   // Carved stone (Moria): a stone wall inside a mountain (beside a tunnel under rock) or underground is
   // dressed rock up to the ceiling: a plinth, two half-pilasters framing a sunk panel on each open face,
   // a studded band under the ceiling, and now and then a torch (it lights the hall). No windows, no walk.
   const under=T.z===2||T.z===4||[[0,1],[0,-1],[1,0],[-1,0]].some(([di,dj])=>{const n=kindAt(i+di,j+dj);return !!n&&n.kind!=='wall'&&n.kind!=='built'&&!!n.roof});
   if(!wood&&!bone&&!race&&under){
    let ceil=0;for(const [di,dj] of [[0,1],[0,-1],[1,0],[-1,0]]){const n=kindAt(i+di,j+dj);if(n&&n.roof)ceil=Math.max(ceil,n.ceil||2)}
    const top=ceil||1.45,isW=(p,q)=>{const k=kindAt(p,q);return !!k&&(k.kind==='built'||k.kind==='wall')},sides=[isW(i,j-1)?0:1,isW(i,j+1)?0:1,isW(i+1,j)?0:1,isW(i-1,j)?0:1];
    const s=[0.55,0.54,0.5,0.99],S=k=>MD.shade(s,k*(0.94+MD.h(tx,ty,160)*0.08)),pt=(bt,u,d)=>bt===2?[X+u,Z+h+d]:bt===1?[X+u,Z-h-d]:bt===4?[X+h+d,Z+u]:[X-h-d,Z+u];
    const slab=(bt,u0,u1,d0,d1,y0,y1,c)=>{const p=pt(bt,u0,d0),q=pt(bt,u1,d1);boxr(a,Math.min(p[0],q[0]),Math.max(p[0],q[0]),Math.min(p[1],q[1]),Math.max(p[1],q[1]),y0,y1,c)};
    boxr(a,X-h,X+h,Z-h,Z+h,Y,Y+top,S(0.86),sides);
    for(const [k,bt] of [[0,2],[1,1],[2,4],[3,8]]){if(!sides[k])continue;
     slab(bt,-h,h,0,0.04,Y,Y+0.18,S(0.72));slab(bt,-h,h,0,0.035,Y+top-0.3,Y+top-0.2,S(1.02));
     for(let q=0;q<4;q++){const u=-0.36+q*0.24;slab(bt,u,u+0.1,0.035,0.06,Y+top-0.29,Y+top-0.21,S(1.12))}
     for(const u of [-0.42,0.32])slab(bt,u,u+0.1,0,0.06,Y+0.18,Y+top-0.3,S(0.98));
     slab(bt,-0.32,0.32,-0.01,0.004,Y+0.3,Y+top-0.42,S(0.78));
     if(MD.h(tx,ty,161+bt)<0.22){const [x,z]=pt(bt,0,0.1),y=Y+top*0.62;slab(bt,-0.03,0.03,0,0.12,y-0.12,y,[0.2,0.18,0.17,1]);MD.blob(a,x,y+0.06,z,0.05,0.08,0.05,[1,0.62,0.22,1],tx*5+ty+bt,0.3);if(V3.torchList)V3.torchList.push([x,y+0.1,z])}}
    continue}
   if(wood&&walk){
    // Timber rampart (a wood wall with a walk): each tile is a solid block of timber up to the walk, so rows built side
    // by side merge into one wide wall under one plank deck, as the stone walls do. Pointed logs line the outer faces and
    // stand above the deck as a breastwork; other open faces are boarded, with a hand rail along the deck's edge.
    // Outer faces come from the server (walk faces: N is -Z, S +Z, E +X, W -X); not known yet: every open face.
    const HW=V3.STOREY,face=V3.walkFace&&V3.walkFace.get(tx+','+ty)||0,isW=(p,q)=>{const k=kindAt(p,q);return !!k&&(k.kind==='built'||k.kind==='wall')};
    const ramp=(p,q)=>{const k=kindAt(p,q);return !!k&&(k.kind==='stairsup'||k.kind==='ramp')},R4={2:[i,j-1],1:[i,j+1],4:[i+1,j],8:[i-1,j]};
    const sides=[isW(i,j-1)?0:1,isW(i,j+1)?0:1,isW(i+1,j)?0:1,isW(i-1,j)?0:1],open=[2,1,4,8].filter((bt,k)=>sides[k]),outer=bt=>!face||!!(face&bt);
    // a point on face bt: u along it, d out from it (negative: inside the wall)
    const pt=(bt,u,d)=>bt===2?[X+u,Z+h+d]:bt===1?[X+u,Z-h-d]:bt===4?[X+h+d,Z+u]:[X-h-d,Z+u];
    const slab=(bt,u0,u1,d0,d1,y0,y1,c)=>{const p=pt(bt,u0,d0),q=pt(bt,u1,d1);boxr(a,Math.min(p[0],q[0]),Math.max(p[0],q[0]),Math.min(p[1],q[1]),Math.max(p[1],q[1]),y0,y1,c)};
    boxr(a,X-h,X+h,Z-h,Z+h,Y,Y+HW-0.06,MD.shade(base,0.6),sides);
    const along=runs.some(([dx])=>dx)||!runs.length;
    for(let p=0;p<5;p++){const u0=-h+p*0.2+0.004,u1=u0+0.192,c=MD.shade(base,0.92+MD.h(tx*3+p,ty,51)*0.16);if(along)boxr(a,X+u0,X+u1,Z-h,Z+h,Y+HW-0.06,Y+HW,c);else boxr(a,X-h,X+h,Z+u0,Z+u1,Y+HW-0.06,Y+HW,c)}
    for(const bt of open){
     if(ramp(...R4[bt]))continue;
     if(outer(bt)){
      // the breastwork: six pointed logs to a tile, set into the outer face, bound by a rail on the inside
      for(let q=0;q<6;q++){const u=-h+0.083+q*0.167,[x,z]=pt(bt,u,-0.075),hh=HW+0.42+MD.h(tx*7+q,ty*3,bt)*0.16,c=MD.shade(base,0.78+MD.h(tx+q,ty,bt+9)*0.3);
       MD.prism(a,x,z,Y,Y+hh,0.088,0.082,6,c,tx*31+ty*17+q+bt);MD.cone(a,x,z,Y+hh,Y+hh+0.2,0.084,6,MD.shade(c,1.08),tx*13+ty+q+bt)}
      const r0=pt(bt,-h,-0.18),r1=pt(bt,h,-0.18);MD.rod(a,[r0[0],Y+HW+0.3,r0[1]],[r1[0],Y+HW+0.3,r1[1]],0.035,5,MD.shade(base,0.55),tx+ty+bt)}
     else{
      // boarding: planks across the face, an upright at the middle carrying the hand rail
      for(let q=0;q<6;q++){const y0=Y+0.04+q*0.37;slab(bt,-h,h,0,0.025,y0,y0+0.34,MD.shade(base,0.74+MD.h(tx*5+q,ty,bt)*0.16))}
      const [px,pz]=pt(bt,0,-0.05);MD.prism(a,px,pz,Y,Y+HW+0.46,0.055,0.05,5,MD.shade(base,0.6),tx*9+ty+bt);
      const r0=pt(bt,-h,-0.05),r1=pt(bt,h,-0.05);MD.rod(a,[r0[0],Y+HW+0.42,r0[1]],[r1[0],Y+HW+0.42,r1[1]],0.032,5,MD.shade(base,0.7),tx*3+ty+bt)}}
    continue}
   if(wood&&!room){
    // Palisade: pointed logs along each run and one at the centre, a rail binding them.
    const log=(x,z,k)=>{const hh=1.5+MD.h(tx*7+k,ty*3,k)*0.32,c=MD.shade(base,0.8+MD.h(tx+k,ty,k+9)*0.32);MD.prism(a,x,z,Y,Y+hh,0.088,0.082,6,c,tx*31+ty*17+k);MD.cone(a,x,z,Y+hh,Y+hh+0.22,0.084,6,MD.shade(c,1.08),tx*13+ty+k)};
    log(X,Z,0);let k=1;for(const [dx,dz] of runs){for(let q=1;q<=3;q++){const f=q/3*h*0.98;log(X+dx*f,Z+dz*f,k++)}MD.rod(a,[X,Y+1.05,Z],[X+dx*h,Y+1.05,Z+dz*h],0.03,5,MD.shade(base,0.6),tx+ty+k)}
    continue}
   if(wood){
    // Log cabin: round logs stacked along each run, crossing and sticking out at the corners.
    const over=straight?0:0.13;for(const [dx,dz] of runs){const off=dx?0:0.085;for(let q=0;q<14;q++){const y=Y+0.09+off+q*0.17;if(y>Y+H)break;const c=MD.shade(base,0.82+MD.h(tx*3+q,ty*5+dx+dz*2,q)*0.3);MD.rod(a,[X-dx*over,y,Z-dz*over],[X+dx*h,y,Z+dz*h],0.088,6,c,tx*11+ty*7+q)}}
    if(!runs.length)for(let q=0;q<9;q++){const y=Y+0.09+q*0.17;MD.rod(a,[X-0.3,y,Z],[X+0.3,y,Z],0.088,6,MD.shade(base,0.85+MD.h(tx,ty,q)*0.2),tx+q)}
    continue}
   if(!room&&!bone){
    // Fortress wall (Helm's Deep). Each wall tile is a solid block of coursed stone up to its walk (upper-storey
    // height), so rows built side by side merge into one wide wall with one walkway across it. Each edge facing open
    // ground gets a parapet: crenellated on the outer face, a low lip on the inner; none between wall tiles. Thin
    // walls (one tile wide) get round towers at corners, junctions, ends and lone pieces; wide walls do not.
    const HW=V3.STOREY,sb=[0.6,0.57,0.52,0.99],stone=k=>MD.shade(sb,k);   // alpha 0.99: cut-stone texture (shader)
    const isW=(p,q)=>{const k=kindAt(p,q);return !!k&&(k.kind==='built'||k.kind==='wall')},open=(p,q)=>!isW(p,q)&&!(V3.walkTiles&&V3.walkTiles.has((T.x0+p)+','+(T.y0+q))),ramp=(p,q)=>{const k=kindAt(p,q);return !!k&&(k.kind==='stairsup'||k.kind==='ramp')};
    // A tower (the build menu's Tower: a solid 3x3 block of wall that no other solid 3x3 block overlaps; a wide
    // wall's blocks overlap each other, so it stays wall). The centre tile draws the round tower, the rest nothing.
    // Corners, ends and junctions of thin walls get no tower of their own.
    const inTower=v3towerAt(kindAt,i,j);
    if(inTower){if(!inTower[0]&&!inTower[1])v3tower(a,X,Y,Z,tx,ty);continue}
    const face=V3.walkFace&&V3.walkFace.get(tx+','+ty)||0;
    const oS=open(i,j-1),oN=open(i,j+1),oE=open(i+1,j),oW=open(i-1,j),sides=[isW(i,j-1)?0:1,isW(i,j+1)?0:1,isW(i+1,j)?0:1,isW(i-1,j)?0:1];
    const tone=0.92+MD.h(tx,ty,21)*0.16,st=k=>stone(k*tone),R4={2:[i,j-1],1:[i,j+1],4:[i+1,j],8:[i-1,j]};
    // Open faces (not where a ramp is cut into the wall), and bands just outside one: S is +Z, N -Z, E +X, W -X.
    const E=[[oS,2],[oN,1],[oE,4],[oW,8]].filter(([o,bt])=>o&&!ramp(...R4[bt])).map(([o,bt])=>bt),outer=bt=>!face||!!(face&bt);
    const strip=(bt,d0,d1)=>bt===2?[X-h,X+h,Z+h+d0,Z+h+d1]:bt===1?[X-h,X+h,Z-h-d1,Z-h-d0]:bt===4?[X+h+d0,X+h+d1,Z-h,Z+h]:[X-h-d1,X-h-d0,Z-h,Z+h];
    const band=(bt,d0,d1,y0,y1,c)=>{const q=strip(bt,d0,d1);boxr(a,q[0],q[1],q[2],q[3],y0,y1,c)};
    const piece=(bt,u0,u1,d0,d1,y0,y1,c)=>{const q=strip(bt,d0,d1);if(bt===2||bt===1)boxr(a,X+u0,X+u1,q[2],q[3],y0,y1,c);else boxr(a,q[0],q[1],Z+u0,Z+u1,y0,y1,c)};
    // the wall: a darker plinth stepping out (a batter), the coursed body, a string course, a corbelled
    // ledge under the parapet; now and then a buttress on the outer face of a straight run
    boxr(a,X-h,X+h,Z-h,Z+h,Y,Y+0.55,st(0.72),sides);boxr(a,X-h,X+h,Z-h,Z+h,Y+0.55,Y+HW,st(0.86),sides);
    for(const bt of E){band(bt,0,0.1,Y,Y+0.48,st(0.68));band(bt,0,0.045,Y+HW*0.55,Y+HW*0.55+0.07,st(0.97));
     band(bt,0,0.085,Y+HW-0.15,Y+HW-0.03,st(0.98));if(outer(bt))for(let m=0;m<4;m++){const u=-h+0.08+m*0.25;piece(bt,u,u+0.09,0,0.065,Y+HW-0.27,Y+HW-0.15,st(0.9))}
     if(straight&&outer(bt)&&MD.h(tx,ty,33)<0.3){piece(bt,-0.17,0.17,0,0.16,Y,Y+HW*0.72,st(0.8));piece(bt,-0.15,0.15,0,0.1,Y+HW*0.72,Y+HW*0.78,st(0.92))}}
    // parapets: the outer face crenellated (a breastwork, two chunky merlons with coping), the inner a low lip
    const P=[[oS,2,[X-h,X+h,Z+h-0.13,Z+h]],[oN,1,[X-h,X+h,Z-h,Z-h+0.13]],[oE,4,[X+h-0.13,X+h,Z-h,Z+h]],[oW,8,[X-h,X-h+0.13,Z-h,Z+h]]];
    for(const [o,bit,e] of P){if(!o||ramp(...R4[bit]))continue;const ot=outer(bit),ax=e[1]-e[0]>0.5;boxr(a,e[0],e[1],e[2],e[3],Y+HW,Y+HW+(ot?0.24:0.13),st(0.88));
     if(ot){for(let m=0;m<1;m++){const f0=-0.22,f1=0.22,c=st(0.9+MD.h(tx+m,ty,bit)*0.1);if(ax){boxr(a,X+f0,X+f1,e[2],e[3],Y+HW+0.24,Y+HW+0.56,c);boxr(a,X+f0-0.015,X+f1+0.015,e[2]-0.015,e[3]+0.015,Y+HW+0.56,Y+HW+0.61,st(0.98))}else{boxr(a,e[0],e[1],Z+f0,Z+f1,Y+HW+0.24,Y+HW+0.56,c);boxr(a,e[0]-0.015,e[1]+0.015,Z+f0-0.015,Z+f1+0.015,Y+HW+0.56,Y+HW+0.61,st(0.98))}}}
     else if(MD.h(tx,ty,77+bit)<0.12){const cx=(e[0]+e[1])/2,cz=(e[2]+e[3])/2,bx=X+(cx-X)*0.8,bz=Z+(cz-Z)*0.8;MD.prism(a,bx,bz,Y+HW,Y+HW+0.42,0.03,0.025,5,[0.15,0.13,0.12,1],tx+ty);MD.prism(a,bx,bz,Y+HW+0.42,Y+HW+0.52,0.06,0.09,7,[0.2,0.18,0.16,1],tx*3+ty);MD.blob(a,bx,Y+HW+0.58,bz,0.06,0.08,0.06,[1,0.62,0.22,1],tx*5+ty,0.3);if(V3.torchList)V3.torchList.push([bx,Y+HW+0.62,bz])}}
    // Corners and ends of thin walls stay square; round towers come from the build menu's Tower (a 3x3 block).
    continue}
   // A room's stone (or bone) wall: a solid block of cut stone up to the storey, a cornice along the top, and a
   // narrow window now and then on faces that look out. Walls of upper storeys stack on it the same way.
   {const sb=bone?[0.85,0.82,0.72,1]:[0.58,0.55,0.5,0.99],isW2=(p,q)=>{const k=kindAt(p,q);return !!k&&(k.kind==='built'||k.kind==='wall')};
    const sides=[isW2(i,j-1)?0:1,isW2(i,j+1)?0:1,isW2(i+1,j)?0:1,isW2(i-1,j)?0:1];
    boxr(a,X-h,X+h,Z-h,Z+h,Y,Y+H-0.14,MD.shade(sb,0.86+MD.h(tx,ty,3)*0.06),sides);
    boxr(a,X-h-0.04,X+h+0.04,Z-h-0.04,Z+h+0.04,Y+H-0.14,Y+H,MD.shade(sb,0.97));
    const win=[0.08,0.07,0.08,1],wy0=Y+H*0.42,wy1=Y+H*0.66;
    if(sides[0]&&MD.h(tx,ty,11)<0.55)quad(a,[X-0.07,wy0,Z+h+0.006],[X+0.07,wy0,Z+h+0.006],[X+0.07,wy1,Z+h+0.006],[X-0.07,wy1,Z+h+0.006],[0,0,1],win);
    if(sides[1]&&MD.h(tx,ty,12)<0.55)quad(a,[X+0.07,wy0,Z-h-0.006],[X-0.07,wy0,Z-h-0.006],[X-0.07,wy1,Z-h-0.006],[X+0.07,wy1,Z-h-0.006],[0,0,-1],win);
    if(sides[2]&&MD.h(tx,ty,13)<0.55)quad(a,[X+h+0.006,wy0,Z+0.07],[X+h+0.006,wy0,Z-0.07],[X+h+0.006,wy1,Z-0.07],[X+h+0.006,wy1,Z+0.07],[1,0,0],win);
    if(sides[3]&&MD.h(tx,ty,14)<0.55)quad(a,[X-h-0.006,wy0,Z-0.07],[X-h-0.006,wy0,Z+0.07],[X-h-0.006,wy1,Z+0.07],[X-h-0.006,wy1,Z-0.07],[-1,0,0],win);
    continue}}
  if(K.kind==='built'){const H=V3.STOREY,t=0.15,a=g(K.tex||''),solid=n=>{const q=kindAt(n[0],n[1]);return q&&(q.kind==='built'||q.kind==='wall')};
   const N=solid([i,j+1]),S=solid([i,j-1]),E=solid([i+1,j]),Wt=solid([i-1,j]);
   boxr(a,X-t-0.02,X+t+0.02,Z-t-0.02,Z+t+0.02,Y,Y+H+0.08,W);
   if(N)boxr(a,X-t,X+t,Z-h,Z,Y,Y+H,W,[0,0,1,1]);if(S)boxr(a,X-t,X+t,Z,Z+h,Y,Y+H,W,[0,0,1,1]);if(E)boxr(a,X,X+h,Z-t,Z+t,Y,Y+H,W,[1,1,0,0]);if(Wt)boxr(a,X-h,X,Z-t,Z+t,Y,Y+H,W,[1,1,0,0]);
   quad(g(''),[X-h,Y,Z+h],[X+h,Y,Z+h],[X+h,Y,Z-h],[X-h,Y,Z-h],[0,1,0],[0.3,0.28,0.22,1]);continue}
  if(K.kind==='farm'){const a=g(''),soil=[0.33,0.22,0.13,1];quad(a,[X-h,Y+0.01,Z+h],[X+h,Y+0.01,Z+h],[X+h,Y+0.01,Z-h],[X-h,Y+0.01,Z-h],[0,1,0],MD.shade(soil,0.85+MD.h(tx,ty,7)*0.2));
   for(let q=0;q<4;q++){const x0=X-h+0.06+q*0.25,x1=x0+0.13;boxr(a,x0,x1,Z-h+0.04,Z+h-0.04,Y+0.01,Y+0.06,MD.shade(soil,1.15+MD.h(tx+q,ty,9)*0.15))}continue}
  if(K.kind==='bfloor'&&V3.models){const st=K.state||'',wood=K.wood||st.includes('wood'),c=wood?[0.55,0.4,0.25]:hexrgb(K.color,0.95);const a=g('');
   // Silk floor (a spider's lair, Buildings.dm): a pale sheet of silk over the ground, strands across it, a few tufts.
   if(st.includes('silk')){const s=[0.84,0.83,0.78,1],sd=tx*29+ty*13;quad(a,[X-h,Y+0.025,Z+h],[X+h,Y+0.025,Z+h],[X+h,Y+0.025,Z-h],[X-h,Y+0.025,Z-h],[0,1,0],MD.shade(s,0.92+MD.h(tx,ty,150)*0.06));
    for(let q=0;q<4;q++){const a0=MD.h(q,sd,151)*6.283,a1=a0+2.2+MD.h(q,sd,152)*1.6;MD.rod(a,[X+Math.cos(a0)*0.5,Y+0.04,Z+Math.sin(a0)*0.5],[X+Math.cos(a1)*0.5,Y+0.04,Z+Math.sin(a1)*0.5],0.008,3,MD.shade(s,1.12),sd+q)}
    for(let q=0;q<2;q++){const u=(MD.h(q,sd,153)-0.5)*0.7,v=(MD.h(q,sd,154)-0.5)*0.7;MD.blob(a,X+u,Y+0.05,Z+v,0.09,0.035,0.09,MD.shade(s,1.05),sd+q,0.3)}continue}
   // Flesh floor (a Devourer's hive): a dark membrane with swellings and a vein or two.
   if(st.includes('devourer')){const f=[0.42,0.12,0.15,1],sd=tx*23+ty*11;quad(a,[X-h,Y+0.025,Z+h],[X+h,Y+0.025,Z+h],[X+h,Y+0.025,Z-h],[X-h,Y+0.025,Z-h],[0,1,0],MD.shade(f,0.9+MD.h(tx,ty,155)*0.12));
    for(let q=0;q<2;q++){const u=(MD.h(q,sd,156)-0.5)*0.6,v=(MD.h(q,sd,157)-0.5)*0.6;MD.blob(a,X+u,Y+0.04,Z+v,0.14,0.05,0.12,MD.shade(f,1.2),sd+q,0.3)}
    {const a0=MD.h(0,sd,158)*6.283;MD.rod(a,[X+Math.cos(a0)*0.5,Y+0.035,Z+Math.sin(a0)*0.5],[X-Math.cos(a0)*0.5,Y+0.035,Z-Math.sin(a0)*0.5],0.014,4,[0.25,0.05,0.1,1],sd)}continue}
   // Carved flagstones (Moria): a stone floor inside a mountain or underground is laid in big dressed
   // flags with bevelled joints, a diamond inlay now and then.
   if(!wood&&(T.z===2||T.z===4||K.roof)){const sd=tx*13+ty*7,f=[0.5,0.49,0.46,0.99],k=0.86+MD.h(tx,ty,162)*0.16+((tx+ty)%2?0.04:0),e=0.035;
    quad(a,[X-h,Y+0.02,Z+h],[X+h,Y+0.02,Z+h],[X+h,Y+0.02,Z-h],[X-h,Y+0.02,Z-h],[0,1,0],MD.shade(f,0.5));
    quad(a,[X-h+e,Y+0.035,Z+h-e],[X+h-e,Y+0.035,Z+h-e],[X+h-e,Y+0.035,Z-h+e],[X-h+e,Y+0.035,Z-h+e],[0,1,0],MD.shade(f,k));
    if(MD.h(tx,ty,163)<0.12){const r=0.14;quad(a,[X,Y+0.038,Z+r],[X+r,Y+0.038,Z],[X,Y+0.038,Z-r],[X-r,Y+0.038,Z],[0,1,0],MD.shade(f,1.18))}continue}
   if(wood){for(let q=0;q<4;q++){const z0=Z+h-q*0.25,z1=z0-0.25;quad(a,[X-h,Y+0.03,z0],[X+h,Y+0.03,z0],[X+h,Y+0.03,z1+0.012],[X-h,Y+0.03,z1+0.012],[0,1,0],MD.shade(c,0.85+MD.h(tx,ty*4+q,60)*0.25))}quad(a,[X-h,Y+0.02,Z+h],[X+h,Y+0.02,Z+h],[X+h,Y+0.02,Z-h],[X-h,Y+0.02,Z-h],[0,1,0],MD.shade(c,0.5))}
   else{for(let q=0;q<4;q++){const ox=(q%2)*0.5,oz=Math.floor(q/2)*0.5;quad(a,[X-h+ox+0.01,Y+0.03,Z+h-oz-0.01],[X-h+ox+0.49,Y+0.03,Z+h-oz-0.01],[X-h+ox+0.49,Y+0.03,Z+h-oz-0.49],[X-h+ox+0.01,Y+0.03,Z+h-oz-0.49],[0,1,0],MD.shade(c,0.85+MD.h(tx*2+q,ty,61)*0.25))}quad(a,[X-h,Y+0.02,Z+h],[X+h,Y+0.02,Z+h],[X+h,Y+0.02,Z-h],[X-h,Y+0.02,Z-h],[0,1,0],MD.shade(c,0.45))}continue}
  if(K.kind==='bfloor'){quad(g(K.tex||''),[X-h,Y+0.03,Z+h],[X+h,Y+0.03,Z+h],[X+h,Y+0.03,Z-h],[X-h,Y+0.03,Z-h],[0,1,0],W,[0,1,1,1,1,0,0,0]);continue}
  if(K.kind==='wall'&&K.blocks&&T.z===1&&!fill&&V3.models){const S=K.lay&&yo===0?v3shapes(T).at.get(tx+','+ty):null,G=v3rockStack(S&&S.tw?v3shapeSink:g,T,kindAt,i,j,X,Y,Z,K);if(S)v3shapeDeco(g,K,S,tx,ty,X,Y,Z);if(yo===0)V3.rockGeo.set(tx+','+ty,G)}   // the surface's rock: a stack of blocks (Gather.dm)
  else if(K.kind==='wall'&&K.blocks&&K.dug===1&&!fill&&V3.models){const G=v3cutRock(g,T,kindAt,i,j,X,Y,Z,K,1,true);if(yo===0)V3.rockGeo.set(tx+','+ty,G)}
  else if(K.kind==='wall'&&K.blocks&&K.dug===2&&!fill&&V3.models&&typeof v3rockLedge==='function'){const G=v3cutRock(g,T,kindAt,i,j,X,Y,Z,K,2,true);try{G.ledge=v3rockLedge(g,T,kindAt,i,j,X,Y,Z,K,1)}catch(err){console.error(err)}if(yo===0)V3.rockGeo.set(tx+','+ty,G)}   // the block above the floor block out first (rts-feel)
  else if(K.kind==='wall'||K.kind==='block'){const dd=Math.min(depth[j*T.w+i],30);const top=K.kind!=='wall'?0.55:fill?v3fillTop(tx,ty):K.blocks?K.blocks+0.55:(T.z===1||T.z===3)?MH(dd)+0.15:1.35;const isW=(a,b)=>{const n=kindAt(a,b);if(!n||n.kind!=='wall')return false;if(fill||!(T.z===1||T.z===3)||K.blocks)return true;return Math.min(depth[b*T.w+a],12)>=dd};
   if(V3.models&&!fill&&K.kind==='wall'){
    // Rock: one faceted mass. Corner heights are shared with the neighbouring rock tiles.
    const topOf=(a,b)=>{const n=kindAt(a,b);if(n&&n.roof&&n.kind!=='wall')return (n.ceil||2)+n.roof+0.4;if(!n||n.kind!=='wall')return null;if(n.blocks)return n.blocks+0.4;const d=Math.min(depth[b*T.w+a],30);return (T.z===1||T.z===3)?MH(d):1.35};
    const ch=(ci,cj)=>{let sum=0,n=0;for(const [di,dj] of [[0,0],[-1,0],[0,-1],[-1,-1]]){const t=topOf(ci+di,cj+dj);if(t!=null){sum+=t;n++}}const base=n?sum/n:top;return base+(MD.h(T.x0+ci,T.y0+cj,5)-0.5)*0.7+(MD.vn(T.x0+ci,T.y0+cj,3,6)-0.5)*0.8};
    const pal=K.biome==='mesa'?MD.PAL.mesa:K.biome==='ashlands'?MD.PAL.ash:K.biome==='tundra'?MD.PAL.tundraRock:K.biome==='mushroom'?MD.PAL.shroomRock:(T.z===1||T.z===3)?MD.PAL.rock:MD.PAL.cave;const rc=K.biome==='mesa'?pal[(ty+Math.floor(MD.h(tx,0,6)*2))%pal.length]:pal[Math.floor(MD.h(tx,ty,6)*pal.length)%pal.length];
    const sw=[X-h,Y+ch(i,j),Z+h],se=[X+h,Y+ch(i+1,j),Z+h],ne=[X+h,Y+ch(i+1,j+1),Z-h],nw=[X-h,Y+ch(i,j+1),Z-h];const ra=g(''),ra0=ra.length;
    const grass=(T.z===1)&&dd<=1&&MD.h(tx,ty,8)<0.2;const vc=K.vein&&VEIN[K.vein],rv=vc?MD.mix(rc,vc.tint,0.12):rc,tc=grass?[0.36,0.5,0.26]:rv;
    MD.f(ra,sw,se,ne,MD.shade(tc,0.95+MD.h(tx,ty,9)*0.12));MD.f(ra,sw,ne,nw,MD.shade(tc,0.9+MD.h(tx,ty,10)*0.12));
    const out=[X,Y+top*0.4,Z],gs=[];const side=(p0,p1,k)=>{const b0=[p0[0],Y,p0[2]],b1=[p1[0],Y,p1[2]];const mid=[(p0[0]+p1[0])/2+(MD.h(tx,ty,k)-0.5)*0.12,Y+Math.min(p0[1]-Y,p1[1]-Y)*0.5,(p0[2]+p1[2])/2+(MD.h(tx,ty,k+1)-0.5)*0.12];gs.push([p0,p1,mid]);const c=MD.shade(rv,0.72+MD.h(tx,ty,k+2)*0.18);MD.f(ra,b0,b1,mid,c,out);MD.f(ra,b1,p1,mid,c,out);MD.f(ra,p1,p0,mid,MD.shade(c,1.08),out);MD.f(ra,p0,b0,mid,c,out)};
    if(!isW(i,j-1))side(sw,se,20);if(!isW(i,j+1))side(ne,nw,24);if(!isW(i+1,j))side(se,ne,28);if(!isW(i-1,j))side(nw,sw,32);
    if(yo===0){const G={c:[sw,se,ne,nw],Y,rc:rv,s:gs,blocks:K.blocks||0,cut:0};V3.rockGeo.set(tx+','+ty,G);if(vc)v3veinMarks(ra,G,K.vein,tx,ty)}v3rockTag(ra,ra0)}
   else{box(g(K.tex||''),X,Z,Y,Y+top,h,W,[!isW(i,j-1),!isW(i,j+1),!isW(i+1,j),!isW(i-1,j)]);
    if(yo===0&&!fill){const c=[[X-h,Y+top,Z+h],[X+h,Y+top,Z+h],[X+h,Y+top,Z-h],[X-h,Y+top,Z-h]],sd=[];if(!isW(i,j-1))sd.push([c[0],c[1],null]);if(!isW(i,j+1))sd.push([c[2],c[3],null]);if(!isW(i+1,j))sd.push([c[1],c[2],null]);if(!isW(i-1,j))sd.push([c[3],c[0],null]);const G={c,Y,rc:hexrgb(K.color||'#777777',1),s:sd};V3.rockGeo.set(tx+','+ty,G);if(K.vein)v3veinMarks(g(''),G,K.vein,tx,ty)}}}
  else if(K.kind==='tree'&&V3.models){const gc=c=>MD.groundCorner(T,kindAt,c[0],c[1],[0.23,0.38,0.17],false);quad4(g(''),[X-h,Y,Z+h],[X+h,Y,Z+h],[X+h,Y,Z-h],[X-h,Y,Z-h],[0,1,0],gc([i,j]),gc([i+1,j]),gc([i+1,j+1]),gc([i,j+1]));if(!(yo===0&&!fill&&V3.workTrees&&V3.workTrees.has(tx+','+ty)))MD.tallTree(g(''),X,Y,Z,K,tx,ty)}
  else if(K.kind==='tree'){const tc=hexrgb(K.color,0.9);quad(g(''),[X-h,Y,Z+h],[X+h,Y,Z+h],[X+h,Y,Z-h],[X-h,Y,Z-h],[0,1,0],[0.22,0.36,0.18,1]);
   box(g(''),X,Z,Y,Y+0.75,0.09,[0.36,0.24,0.14,1]);const C=[tc[0]*0.6,tc[1]*0.85,tc[2]*0.5,1];
   [[0.45,1.05,0.42],[0.85,1.5,0.32]].forEach(([b,t,r])=>{const pk=[X,Y+t+0.15,Z];const q=[[X-r,Y+b,Z+r],[X+r,Y+b,Z+r],[X+r,Y+b,Z-r],[X-r,Y+b,Z-r]];for(let k=0;k<4;k++){const a1=q[k],a2=q[(k+1)%4];const nx=(a1[0]+a2[0])/2-X,nz=(a1[2]+a2[2])/2-Z;tri(g(''),a1,a2,pk,[nx*2,0.6,nz*2],C)}})}
  else if(V3.models&&(K.kind==='floor'||K.kind==='water'||K.kind==='lava'||K.kind==='bridge')){
   if(K.roof&&K.lay&&T.z===1&&!fill&&yo===0){const G=v3rockStack(g,T,kindAt,i,j,X,Y,Z,K);V3.rockGeo.set(tx+','+ty,G)}   // a room's ceiling laid over it (the layered builder, phase 3): its blocks as the walls' (dressed, an underside over the room), stood on above
   // Painted ground: corner colours blend with the neighbours; water and lava sit lower. A bridge lies over its
   // water, lava or chasm (K.under).
   const liquid=K.kind!=='floor',U=K.kind==='bridge'?(K.under||'water'):K.kind,own=MD.groundColor(K.kind==='bridge'?{kind:U,state:''}:K);
   if(U==='chasm'){quad(g(''),[X-h,Y-0.03,Z+h],[X+h,Y-0.03,Z+h],[X+h,Y-0.03,Z-h],[X-h,Y-0.03,Z-h],[0,1,0],[0.02,0.02,0.02,1]);v3bridge(g(''),kindAt,i,j,X,Y,Z,K,U);continue}
   const gc=(ci,cj)=>v3ao(kindAt,ci,cj,MD.groundCorner(T,kindAt,ci,cj,own,liquid),liquid);let sm=0;
   if(liquid){
    // Water and lava lie in a basin: a dark bed, earth banks where land meets it, and a
    // moving surface drawn every frame (v3drawLiquids).
    const deep=U==='water'?0.42:0.2,yb=Y-deep,dk=c=>[c[0]*0.45,c[1]*0.5,c[2]*0.55,1];
    quad4(g(''),[X-h,yb,Z+h],[X+h,yb,Z+h],[X+h,yb,Z-h],[X-h,yb,Z-h],[0,1,0],dk(gc(i,j)),dk(gc(i+1,j)),dk(gc(i+1,j+1)),dk(gc(i,j+1)));
    const bank=K.lift?[0.44,0.42,0.39,0.99]:U==='water'?[0.36,0.29,0.2,1]:[0.25,0.2,0.18,1];   // up in the rock: stone, not earth
    for(const [di,dj,x0,z0,x1,z1] of [[1,0,X+h,Z+h,X+h,Z-h],[-1,0,X-h,Z-h,X-h,Z+h],[0,1,X+h,Z-h,X-h,Z-h],[0,-1,X-h,Z+h,X+h,Z+h]]){const nk=kindAt(i+di,j+dj);if(!nk||nk.kind==='water'||nk.kind==='lava'||nk.kind==='void'||nk.kind==='bridge')continue;const bt=U==='water'&&yo===0&&v3shore(T,nk,i+di,j+dj)?Y-SHORE_DIP*0.62-0.01:Y+0.01;quad(g(''),[x0,bt,z0],[x1,bt,z1],[x1,yb,z1],[x0,yb,z0],[0,1,0],bank);quad(g(''),[x1,bt,z1],[x0,bt,z0],[x0,yb,z0],[x1,yb,z1],[0,1,0],bank)}
    // A mountain lake or its river (K.lift blocks up, Water.dm) beside anything lower: a stone face down from its lip,
    // and where the lower side is water, a waterfall pouring over it (v3drawLiquids draws it moving)
    if(K.lift&&U==='water'&&yo===0)for(const [di,dj,x0,z0,x1,z1] of [[1,0,X+h,Z+h,X+h,Z-h],[-1,0,X-h,Z-h,X-h,Z+h],[0,1,X+h,Z-h,X-h,Z-h],[0,-1,X-h,Z+h,X+h,Z+h]]){const nk=kindAt(i+di,j+dj);if(!nk||nk.kind==='wall'||nk.kind==='block'||(v3isWater(nk)&&(nk.lift||0)>=K.lift))continue;
     const wet=v3isWater(nk),nY=Y-K.lift+(wet?nk.lift||0:0),lo=nY-(wet?0.45:0.05),hi=Y-0.13,st=[0.44,0.42,0.39,0.99];quad(g(''),[x0,hi,z0],[x1,hi,z1],[x1,lo,z1],[x0,lo,z0],[di,0,-dj],st);quad(g(''),[x1,hi,z1],[x0,hi,z0],[x0,lo,z0],[x1,lo,z1],[-di,0,dj],st);
     if(wet&&V3.waterList)V3.waterList.push([x0,z0,Y-0.12,tx,ty,3,nY-0.12,x1,z1,di,-dj])}
    if(yo===0&&V3.waterList){V3.waterList.push([X,Z,Y,tx,ty,U==='lava'?1:String(K.kind==='bridge'?'':K.state||'').includes('swamp')?2:0,v3cornerMask(T,i,j,n=>!v3isWater(n)),0,U==='water'?v3flowCorners(kindAt,i,j):null]);V3.waterSet.add(tx+','+ty)}
    if(K.kind==='bridge')v3bridge(g(''),kindAt,i,j,X,Y,Z,K,U)}
   else if(yo===0&&(sm=v3shore(T,K,i,j))){const d0=v3cdip(T,i,j,0),d1=v3cdip(T,i,j,1),d2=v3cdip(T,i,j,2),d3=v3cdip(T,i,j,3),wet=(c,b)=>sm&b?[c[0]*0.6,c[1]*0.7,c[2]*0.58,1]:c;
    // a bank down into the water (v3cornerMask); wet and darker where it goes under, in its own hue (grass stays grass,
    // not a band of earth stepping along the shore: the owner, 10-27, "river tiles on the side needs work")
    quad4(g(''),[X-h,Y-(sm&1?d0:0),Z+h],[X+h,Y-(sm&2?d1:0),Z+h],[X+h,Y-(sm&4?d2:0),Z-h],[X-h,Y-(sm&8?d3:0),Z-h],[0,1,0],wet(gc(i,j),1),wet(gc(i+1,j),2),wet(gc(i+1,j+1),4),wet(gc(i,j+1),8));
    // where the water's surface cuts this slope (its two triangles, as quad4 splits them): the shore's foam line (v3drawFoam)
    if(V3.foamSegs){const L0=Y-0.12,c=[[X-h,Y-(sm&1?d0:0),Z+h],[X+h,Y-(sm&2?d1:0),Z+h],[X+h,Y-(sm&4?d2:0),Z-h],[X-h,Y-(sm&8?d3:0),Z-h]];for(const tr of [[0,1,2],[0,2,3]]){const pt=[];for(let e=0;e<3;e++){const A=c[tr[e]],B=c[tr[(e+1)%3]],da=A[1]-L0,db=B[1]-L0;if((da<0)!==(db<0)){const s=da/(da-db);pt.push(A[0]+(B[0]-A[0])*s,A[2]+(B[2]-A[2])*s)}}if(pt.length===4)V3.foamSegs.push(pt[0],pt[1],pt[2],pt[3],L0)}}
    if(V3.waterList){const sw=[[1,0],[-1,0],[0,1],[0,-1]].some(([a,b])=>{const n=kindAt(i+a,j+b);return n&&n.kind==='water'&&String(n.state||'').includes('swamp')});V3.waterList.push([X,Z,Y,tx,ty,sw?2:0,15,1,v3flowCorners(kindAt,i,j)])}}
   else quad4(g(''),[X-h,Y,Z+h],[X+h,Y,Z+h],[X+h,Y,Z-h],[X-h,Y,Z-h],[0,1,0],gc(i,j),gc(i+1,j),gc(i+1,j+1),gc(i,j+1));
   if(K.hoard){v3hoard(g(''),X,Y,Z,K,kindAt,i,j);continue}
   if(K.road){v3road(g(''),kindAt,i,j,X,Y,Z,K);continue}
   // A little grass or a pebble here and there.
   if(!liquid&&!sm){const st=K.state||'';const r=MD.h(tx,ty,12);if((st.includes('grass')||st==='')&&r<0.26)v3tuft(g(''),X+(MD.h(tx,ty,13)-0.5)*0.6,Y,Z+(MD.h(tx,ty,14)-0.5)*0.6,own,tx*7+ty);else if(r>0.95)MD.blob(g(''),X+(MD.h(tx,ty,15)-0.5)*0.6,Y+0.03,Z+(MD.h(tx,ty,16)-0.5)*0.6,0.07,0.05,0.07,[0.5,0.48,0.45,1],tx+ty*7,0.3)}}
  else{const y=Y+(K.kind==='water'?-0.14:K.kind==='lava'?-0.06:0);quad(g(K.tex||''),[X-h,y,Z+h],[X+h,y,Z+h],[X+h,y,Z-h],[X-h,y,Z-h],[0,1,0],W,[0,1,1,1,1,0,0,0])}}
 dimDone();if(opt)return groups;   // a chunk (v3meshesChunked): its geometry by texture, no buffers or roofs
 // untextured fallback colours: groups keyed '' use vertex colour; textured groups fall back to the kind colour until loaded
 for(const [k,a] of groups){const buf=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,buf);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(a),gl.STATIC_DRAW);const kind=T.kinds.find(x=>x.tex===k);out.push({buf,count:a.length/12,tex:k,color:kind?hexrgb(kind.color):[1,1,1]})}
 if((yo===0||yo===V3.STOREY)&&!fill)v3roofs(T,kindAt,yo);oldList.forEach(m=>gl.deleteBuffer(m.buf));return out}
// A built bridge: a deck at ground height spanning towards the land (or more bridge) on either side. Timber (wood,
// tribal, bone, silk): planks across two stringers on posts, a rail along each side that faces the drop. Stone:
// a slab on a pier, a low parapet along each side that faces the drop.
function v3bridge(a,kindAt,i,j,X,Y,Z,K,U){const st=K.state||'',stone=st==='bridge'||st.includes('lava'),h=0.5;
 const drop=(p,q)=>{const n=kindAt(p,q);return !n||['water','lava','hole','void'].includes(n.kind)||String(n.state||'').includes('chasm')};
 const dS=drop(i,j-1),dN=drop(i,j+1),dE=drop(i+1,j),dW=drop(i-1,j),lx=(!dE)+(!dW),lz=(!dN)+(!dS),alongX=lx>=lz;
 const sides=[[dS,2],[dN,1],[dE,4],[dW,8]].filter(([d,bt])=>d&&(alongX?bt<4:bt>2)).map(([d,bt])=>bt);
 const seg=(bt,d0,d1,y0,y1,c)=>bt===2?boxr(a,X-h,X+h,Z+h-d1,Z+h-d0,y0,y1,c):bt===1?boxr(a,X-h,X+h,Z-h+d0,Z-h+d1,y0,y1,c):bt===4?boxr(a,X+h-d1,X+h-d0,Z-h,Z+h,y0,y1,c):boxr(a,X-h+d0,X-h+d1,Z-h,Z+h,y0,y1,c);
 const tx=X,ty=-Z,pier=U==='chasm'?2.5:0.7;
 if(stone){const c=[0.58,0.55,0.5,0.99];boxr(a,X-h,X+h,Z-h,Z+h,Y-0.22,Y+0.07,MD.shade(c,0.9+MD.h(tx,ty,41)*0.08));
  if(alongX)boxr(a,X-0.22,X+0.22,Z-h,Z+h,Y-pier,Y-0.22,MD.shade(c,0.75));else boxr(a,X-h,X+h,Z-0.22,Z+0.22,Y-pier,Y-0.22,MD.shade(c,0.75));
  for(const bt of sides){seg(bt,0,0.13,Y+0.07,Y+0.4,MD.shade(c,0.86));seg(bt,-0.015,0.145,Y+0.4,Y+0.45,MD.shade(c,0.98))}
  return}
 const base=st.includes('bone')?[0.85,0.82,0.72,1]:st.includes('silk')?[0.88,0.88,0.9,1]:st.includes('tribal')?[0.56,0.45,0.27,1]:[0.5,0.36,0.22,1];
 for(let p=0;p<6;p++){const u0=-h+p/6+0.006,u1=-h+(p+1)/6-0.006,c=MD.shade(base,0.85+MD.h(tx*6+p,ty,43)*0.25);if(alongX)boxr(a,X+u0,X+u1,Z-h+0.02,Z+h-0.02,Y+0.03,Y+0.09,c);else boxr(a,X-h+0.02,X+h-0.02,Z+u0,Z+u1,Y+0.03,Y+0.09,c)}
 const sc=MD.shade(base,0.62);for(const o of [-0.36,0.36]){if(alongX)boxr(a,X-h,X+h,Z+o-0.05,Z+o+0.05,Y-0.12,Y+0.03,sc);else boxr(a,X+o-0.05,X+o+0.05,Z-h,Z+h,Y-0.12,Y+0.03,sc);
  const px=alongX?X:X+o,pz=alongX?Z+o:Z;MD.prism(a,px,pz,Y-pier,Y-0.12,0.06,0.06,6,MD.shade(base,0.5),tx*3+ty+o*10)}
 for(const bt of sides){const r0=bt===2?[X-h,Z+h-0.06]:bt===1?[X-h,Z-h+0.06]:bt===4?[X+h-0.06,Z+h]:[X-h+0.06,Z+h],r1=bt===2?[X+h,Z+h-0.06]:bt===1?[X+h,Z-h+0.06]:bt===4?[X+h-0.06,Z-h]:[X-h+0.06,Z-h];
  MD.rod(a,[r0[0],Y+0.48,r0[1]],[r1[0],Y+0.48,r1[1]],0.03,5,sc,tx+ty+bt);const m=[(r0[0]+r1[0])/2,(r0[1]+r1[1])/2];MD.prism(a,m[0],m[1],Y+0.03,Y+0.5,0.045,0.04,5,sc,tx*5+ty+bt)}}
// A road (Roads.dm): the way runs towards the neighbouring road tiles. Cobbles: rows of setts across the way, each row
// set half a sett over from the last, and a kerb of long stones wherever the road meets the verge. Dirt track: a band
// of packed earth along the way (a little narrower than the tile, so the grass runs up to it), two wheel ruts, pebbles.
// Rail track (Carts.dm, turf remaster_road "rail"): wooden sleepers and two iron rails, a half-tile run toward each
// railed neighbour, so straights, corners and junctions join (it joins rail only; roads may run up to it).
function v3rail(a,kindAt,i,j,X,Y,Z,K){const rl=(p,q)=>{const n=kindAt(p,q);return !!n&&n.road==='rail'},tx=X,ty=-Z,wood=[0.38,0.27,0.17,1],iron=[0.42,0.42,0.45,1];
 let D=[[0,1,rl(i,j-1)],[0,-1,rl(i,j+1)],[1,0,rl(i+1,j)],[-1,0,rl(i-1,j)]].filter(d=>d[2]);if(!D.length)D=[[1,0],[-1,0]];if(D.length===1)D.push([-D[0][0],-D[0][1]]);
 for(const [dx,dz] of D){const px=-dz,pz=dx;
  for(const t of [0.07,0.32]){const cx=X+dx*t,cz=Z+dz*t,c=MD.shade(wood,0.85+MD.h(tx*3+dx,ty*3+dz,180+t*10)*0.25);if(dx)boxr(a,cx-0.045,cx+0.045,cz-0.25,cz+0.25,Y,Y+0.045,c);else boxr(a,cx-0.25,cx+0.25,cz-0.045,cz+0.045,Y,Y+0.045,c)}
  for(const s of [-0.17,0.17])MD.rod(a,[X+px*s,Y+0.07,Z+pz*s],[X+dx*0.5+px*s,Y+0.07,Z+dz*0.5+pz*s],0.018,4,iron,tx+ty)}}
// A dragon's lair floor (Instances.dm, remaster_hoard 1-3): heaped gold coins, low mounds rising toward the
// beast's bed, loose coins on top catching the light, now and then a gem or a goblet.
function v3hoard(a,X,Y,Z,K,kindAt,i,j){const L=K.hoard,sx=Math.round(X*3),sz=Math.round(Z*3);
 // faceted heaps, built like the mountains: each corner's height is shared with the tiles round it (so the gold runs
 // on in slopes and ridges from tile to tile), each tile rises to its own peak, and every face is shaded on its own
 const lv=(di,dj)=>{const n=kindAt(i+di,j+dj);return n&&n.hoard?n.hoard:0},jit=(x,z,k)=>MD.h(Math.round(x*2),Math.round(z*2),k);
 const HT=[0,0.06,0.42,0.72],corner=(cx,cy)=>{const xs=cx?[0,1]:[-1,0],ys=cy?[0,1]:[-1,0];let s=0;for(const a1 of xs)for(const b1 of ys)s+=HT[lv(a1,b1)];const PX=X+(cx?0.5:-0.5),PZ=Z+(cy?-0.5:0.5);return [PX,Y+s/4+jit(PX,PZ,3)*0.04,PZ]};
 const c00=corner(0,0),c10=corner(1,0),c11=corner(1,1),c01=corner(0,1),C=[X+(MD.h(sx,sz,5)-0.5)*0.3,Y+HT[L]+MD.h(sx,sz,7)*0.05*L,Z+(MD.h(sx,sz,6)-0.5)*0.3];
 if(V3.hoardList&&L>=3&&(sx+sz)%7===0)V3.hoardList.push([X,Y+1.1,Z]);
 const face=(p,q,k)=>{const u=[p[0]-C[0],p[1]-C[1],p[2]-C[2]],v=[q[0]-C[0],q[1]-C[1],q[2]-C[2]];let n=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]];const l=Math.hypot(n[0],n[1],n[2])||1;n=n.map(c=>c/l);if(n[1]<0)n=n.map(c=>-c);
  const s=(L>=2?0.78:0.55)+MD.h(sx,sz,40+k)*0.18;quad(a,C,p,q,q,n,[0.86*s,0.62*s,0.16*s,1])};
 face(c00,c10,0);face(c10,c11,1);face(c11,c01,2);face(c01,c00,3);
 // coins lying on the slopes, a few catching the light, now and then a gem or a goblet
 const hAt=(u,v)=>{const bx=(u+0.5),bz=(v+0.5),edge=(c00[1]*(1-bx)+c10[1]*bx)*(1-bz)+(c01[1]*(1-bx)+c11[1]*bx)*bz,w=1-Math.max(Math.abs(u),Math.abs(v))*2;return edge*(1-w)+C[1]*w};
 for(let k=0;k<(L>=2?6+L*4:4);k++){const u=(MD.h(sx,sz,30+k)-0.5)*0.9,v=(MD.h(sx,sz,60+k)-0.5)*0.9,yy=hAt(u,v)+0.015,s=0.055,t=(MD.h(sx,sz,90+k)-0.5)*0.05,c=MD.h(sx,sz,120+k)<0.12?[0.98,0.88,0.55,1]:[0.85,0.64,0.2,1],cx=X+u,cz=Z-v;
  quad(a,[cx-s,yy+t,cz+s],[cx+s,yy-t,cz+s],[cx+s,yy-t,cz-s],[cx-s,yy+t,cz-s],[0,1,0],c)}
 const r=MD.h(sx,sz,150),gy=C[1]-0.04;if(r<0.08)MD.blob(a,C[0]+0.08,gy,C[2],0.05,0.05,0.05,[0.85,0.1,0.15,1],sx,0.1);else if(r<0.13)MD.blob(a,C[0]-0.08,gy,C[2],0.05,0.05,0.05,[0.1,0.75,0.35,1],sz,0.1);else if(r<0.16)boxr(a,C[0]-0.04,C[0]+0.04,C[2]-0.04,C[2]+0.04,gy,gy+0.16,[0.92,0.72,0.2,1])}
function v3road(a,kindAt,i,j,X,Y,Z,K){if(K.road==='rail'){v3rail(a,kindAt,i,j,X,Y,Z,K);return}const h=0.5,tx=X,ty=-Z,rd=(p,q)=>{const n=kindAt(p,q);return !!n&&!!n.road};
 const rS=rd(i,j-1),rN=rd(i,j+1),rE=rd(i+1,j),rW=rd(i-1,j),lx=rE+rW,lz=rN+rS,alongX=lx>=lz;
 if(K.road==='stone'){const base=[0.5,0.48,0.45,1];
  for(let r=0;r<4;r++){const v0=-h+r*0.25+0.015,v1=v0+0.22,off=(r+(alongX?tx:ty))%2?0.165:0;
   for(let k=-1;k<3;k++){let u0=-h+off+k*0.333+0.015,u1=u0+0.303;u0=Math.max(u0,-h+0.015);u1=Math.min(u1,h-0.015);if(u1-u0<0.06)continue;
    const c=MD.shade(base,0.78+MD.h(tx*4+k,ty*4+r,57)*0.3),y1=Y+0.035+MD.h(tx+k,ty+r,58)*0.03;
    if(alongX)boxr(a,X+v0,X+v1,Z+u0,Z+u1,Y,y1,c);else boxr(a,X+u0,X+u1,Z+v0,Z+v1,Y,y1,c)}}
  // kerbs along the sides that meet the verge
  const kc=MD.shade(base,0.9);for(const [o,bt] of [[rS,2],[rN,1],[rE,4],[rW,8]]){if(o)continue;const n=kindAt(...{2:[i,j-1],1:[i,j+1],4:[i+1,j],8:[i-1,j]}[bt]);if(n&&(n.kind==='built'||n.kind==='wall'))continue;
   for(let q=0;q<4;q++){const u0=-h+q*0.25+0.01,u1=u0+0.23,c=MD.shade(kc,0.88+MD.h(tx*3+q,ty,bt)*0.18);
    if(bt===2)boxr(a,X+u0,X+u1,Z+h-0.09,Z+h,Y,Y+0.085,c);else if(bt===1)boxr(a,X+u0,X+u1,Z-h,Z-h+0.09,Y,Y+0.085,c);else if(bt===4)boxr(a,X+h-0.09,X+h,Z+u0,Z+u1,Y,Y+0.085,c);else boxr(a,X-h,X-h+0.09,Z+u0,Z+u1,Y,Y+0.085,c)}}
  return}
 // the track: a band of earth along each way the road runs (both at a corner or a crossing), ruts along it
 const dirt=[0.6,0.45,0.27],verge=[0.47,0.43,0.24],band=(ax,neg,pos,w,y,col)=>{const c0=MD.shade(col,0.92+MD.h(tx,ty,61)*0.12),c1=MD.shade(col,0.92+MD.h(tx+1,ty,61)*0.12);
  if(ax)quad4(a,[X-neg,Y+y,Z+w],[X+pos,Y+y,Z+w],[X+pos,Y+y,Z-w],[X-neg,Y+y,Z-w],[0,1,0],c0,c1,c1,c0);
  else quad4(a,[X-w,Y+y,Z+neg],[X+w,Y+y,Z+neg],[X+w,Y+y,Z-pos],[X-w,Y+y,Z-pos],[0,1,0],c0,c0,c1,c1)};
 const ways=[];if(lx||!lz)ways.push(1);if(lz)ways.push(0);
 for(const ax of ways){const end=(o,e)=>o?h:e,neg=ax?(!lx?h:end(rW,0.36)):end(rS,0.36),pos=ax?(!lx?h:end(rE,0.36)):end(rN,0.36);
  // a worn verge first, then the packed earth on it
  band(ax,ax?(!lx?h:end(rW,0.46)):end(rS,0.46),ax?(!lx?h:end(rE,0.46)):end(rN,0.46),0.46,0.006,verge);band(ax,neg,pos,0.36,0.01,dirt);
  const rc=MD.shade(dirt,0.6);for(const o of [-0.19,0.19]){if(ax)quad(a,[X-neg,Y+0.012,Z+o+0.035],[X+pos,Y+0.012,Z+o+0.035],[X+pos,Y+0.012,Z+o-0.035],[X-neg,Y+0.012,Z+o-0.035],[0,1,0],rc);
   else quad(a,[X+o-0.035,Y+0.012,Z+neg],[X+o+0.035,Y+0.012,Z+neg],[X+o+0.035,Y+0.012,Z-pos],[X+o-0.035,Y+0.012,Z-pos],[0,1,0],rc)}}
 for(let k=0;k<2;k++)if(MD.h(tx,ty,62+k)<0.5)MD.blob(a,X+(MD.h(tx,ty,63+k)-0.5)*0.6,Y+0.02,Z+(MD.h(tx,ty,65+k)-0.5)*0.6,0.035,0.025,0.035,[0.52,0.5,0.46,1],tx*3+ty+k,0.3)}
// Doors decide which huts are houses (v3roofs), and things arrive after the terrain in an update: build the ground
// floor's roofs again when the doors change.
function v3roofsForDoors(){const T=V3.terrain;if(!T||!Array.isArray(T.tiles)||!V3.gl)return;
 const sig=(V3.things||[]).filter(t=>String(t.m3||'').startsWith('door')).map(t=>t.x+','+t.y).sort().join(';');if(sig===V3.roofDoors)return;
 v3roofs(T,(i,j)=>{if(i<0||j<0||i>=T.w||j>=T.h)return null;const c=T.tiles[j*T.w+i];return c?T.kinds[c-1]:null},0)}
// Automatic roofs: a room is a patch of built floor fully closed in by walls.
function v3roofs(T,kindAt,yo=0){const gl=V3.gl;const slot=yo?'roofsUp':'roofs';(V3[slot]||[]).forEach(r=>gl.deleteBuffer(r.buf));V3[slot]=[];if(T.z===2||T.z===4)return;   // caves and depths: the rock is the roof
 const seen=new Uint8Array(T.w*T.h);const covered=yo?new Set():(V3.upperTiles||new Set());yo=v3skyY(T,null,yo);
 const inside=k=>k&&(k.kind==='bfloor'||k.kind==='stairsup'||k.kind==='stairsdown');
 // Second pass, huts: a small room of plain ground with a way in (a door, or an open doorway: a one-tile gap in a
 // wall line) is a house too (WallWalks.dm RemasterWallIsHouse, up to 40 tiles). Doors and doorways stop the flood; a
 // flood that runs past 40 tiles marks its ground open (leak), so the open country is looked at once. The server's
 // verdict shows in the walls: a hut's walls have no walks.
 const doorList=(V3.things||[]).filter(t=>String(t.m3||'').startsWith('door')),doors=new Set(doorList.map(t=>(t.x-T.x0)+','+(t.y-T.y0)));
 if(!yo)V3.roofDoors=doorList.map(t=>t.x+','+t.y).sort().join(';');
 const seen2=new Uint8Array(T.w*T.h),leak=new Uint8Array(T.w*T.h),roofed=new Set(),HUT=40;
 const solidAt=(p,q)=>{const n=kindAt(p,q);return !!n&&['built','wall','block','tree'].includes(n.kind)},doorway=(x,y)=>!solidAt(x,y)&&((solidAt(x-1,y)&&solidAt(x+1,y)&&!solidAt(x,y-1)&&!solidAt(x,y+1))||(solidAt(x,y-1)&&solidAt(x,y+1)&&!solidAt(x-1,y)&&!solidAt(x+1,y)));   // a gap in a wall line, open both ways (a notch between a wall and a stair's step is no way in: phase 3)
 for(const hut of yo?[false]:[false,true])for(let j=0;j<T.h;j++)for(let i=0;i<T.w;i++){const K=kindAt(i,j),sn=hut?seen2:seen;
  if(!K||sn[j*T.w+i]||(hut?(K.kind!=='floor'||doors.has(i+','+j)||doorway(i,j)||leak[j*T.w+i]):K.kind!=='bfloor'))continue;
  const inn=hut?(n,x,y)=>!!n&&(n.kind==='floor'||inside(n))&&!doors.has(x+','+y)&&!doorway(x,y):n=>inside(n);
  const comp=[],q=[[i,j]];sn[j*T.w+i]=1;let walls=0,open=0,lk=false;const gaps=new Set();
  while(q.length&&!lk){const [a,b]=q.pop();comp.push([a,b]);if(hut&&comp.length>HUT){lk=true;break}
   [[1,0],[-1,0],[0,1],[0,-1]].forEach(([dx,dy])=>{const x=a+dx,y=b+dy,n=kindAt(x,y);if(!n){open+=99;if(hut)lk=true;return}if(inn(n,x,y)){if(hut&&leak[y*T.w+x]){lk=true;return}if(!sn[y*T.w+x]){sn[y*T.w+x]=1;q.push([x,y])}}else if(n.kind==='built'||n.kind==='wall')walls++;else if(!gaps.has(x+','+y)){gaps.add(x+','+y);open++}})}
  if(hut&&lk){for(const [a,b] of comp.concat(q))leak[b*T.w+a]=1;continue}
  if(hut&&comp.length<4)continue;   // a hut is at least four tiles (WallWalks.dm REMASTER_HUT_MIN)
  if(Array.isArray(V3.planCells)&&V3.planCells.length){const qc=new Set();for(const c of V3.planCells)if(c&&c[4]===1)qc.add(c[0]+','+c[1]);if(qc.size&&comp.some(([a,b])=>[[1,0],[-1,0],[0,1],[0,-1],[1,1],[1,-1],[-1,1],[-1,-1]].some(([dx,dy])=>qc.has((T.x0+a+dx)+','+(T.y0+b+dy)))))continue}   // its walls still going up: no roof yet (construction-3d)
  if(hut){const wk=V3.walkTiles,around=[[1,0],[-1,0],[0,1],[0,-1],[1,1],[1,-1],[-1,1],[-1,-1]];
   const way=comp.some(([a,b])=>[[1,0],[-1,0],[0,1],[0,-1]].some(([dx,dy])=>doors.has((a+dx)+','+(b+dy))||doorway(a+dx,b+dy)));
   if(open>2||!way||comp.some(([a,b])=>roofed.has(a+','+b))||(wk&&comp.some(([a,b])=>around.some(([dx,dy])=>wk.has((T.x0+a+dx)+','+(T.y0+b+dy))))))continue;
   // the roof also covers the doorways in its walls
   comp.forEach(([a,b])=>[[1,0],[-1,0],[0,1],[0,-1]].forEach(([dx,dy])=>{const x=a+dx,y=b+dy;if(doorway(x,y)||doors.has(x+','+y))gaps.add(x+','+y)}))}
  // A room: built floor walled in, allowing a doorway or two.
  if(comp.length>400||comp.length<2||open>Math.max(2,Math.floor(walls*0.12)))continue;
  const inC=new Set(comp.map(([a,b])=>a+','+b)),arr=[],tiles=new Set(comp.map(([a,b])=>(T.x0+a)+','+(T.y0+b)));
  if(comp.some(([a,b])=>covered.has((T.x0+a)+','+(T.y0+b))))continue; // an upper floor sits on this room
  let ceilTop=0;if(comp.some(([a,b])=>{const k=kindAt(a,b);if(k&&k.roof>0&&k.lay)ceilTop=Math.max(ceilTop,(k.ceil||2)+k.roof);return k&&k.roof>0&&!k.lay}))continue;   // inside a mountain: the rock is its roof (a built storey's floor over the room is not: the layered builder, phase 3)
  // The roof covers the room, its doorways and the walls round it. A rectangle gets a gable roof (the ridge along its
  // long side, the ends closed by gables of the walls' own timber or stone); any other shape a hipped roof (every
  // side sloping, hips at outside corners, valleys at inside ones). Thatch over timber walls, slate over stone. The
  // eaves reach out over the walls.
  const solid=(x,y)=>{const n=kindAt(x,y);return !!n&&(n.kind==='built'||n.kind==='wall')},fp=new Set(inC);let wood=0,stone=0,lt=0;const races={};
  gaps.forEach(k=>{const [x,y]=k.split(',').map(Number);if((solid(x-1,y)&&solid(x+1,y))||(solid(x,y-1)&&solid(x,y+1)))fp.add(k)});   // doorways in the wall line
  comp.forEach(([a,b])=>{for(let dx=-1;dx<=1;dx++)for(let dy=-1;dy<=1;dy++){const n=kindAt(a+dx,b+dy);if(n&&(n.kind==='built'||(n.kind==='wall'&&n.lay))){fp.add((a+dx)+','+(b+dy));if(n.lay){lt=Math.max(lt,n.blocks||0);if(v3layWoodish(n))wood++;else stone++;continue}const st=n.state||'';if(n.wood||st.includes('wood')||st.includes('log'))wood++;else stone++;const rk=st.includes('silk')?'silk':st.includes('devourer')?'flesh':st.includes('elf')?'elf':st.includes('tribal')?'tribal':null;if(rk)races[rk]=(races[rk]||0)+1}}});
  let a0=1e9,a1=-1e9,b0=1e9,b1=-1e9;fp.forEach(k=>{const [a,b]=k.split(',').map(Number);a0=Math.min(a0,a);a1=Math.max(a1,a);b0=Math.min(b0,b);b1=Math.max(b1,b)});
  if(ceilTop&&lt<=ceilTop)continue;   // no storey over its top floor: that floor is its roof, flat, stood on
  // a grid of quarter tiles over the footprint; its points (tile corners, edge middles, centres) carry the roof
  const GW=(a1-a0+1)*2,GH=(b1-b0+1)*2,qin=(k,l)=>k>>0===k&&k>=0&&l>=0&&k<GW&&l<GH&&fp.has((a0+(k>>1))+','+(b0+(l>>1)));
  const rect=fp.size===(a1-a0+1)*(b1-b0+1),alongA=(a1-a0)>=(b1-b0),thatch=wood>=stone;
  // how far in from the edge each point lies (chessboard steps of half a tile): a hipped roof rises with it
  const D=new Float32Array((GW+1)*(GH+1)).fill(-1),fr=[];
  for(let l=0;l<=GH;l++)for(let k=0;k<=GW;k++)if(!(qin(k-1,l-1)&&qin(k,l-1)&&qin(k-1,l)&&qin(k,l))){D[l*(GW+1)+k]=0;fr.push(k,l)}
  for(let f=0;f<fr.length;f+=2){const k=fr[f],l=fr[f+1],d=D[l*(GW+1)+k];for(let dk=-1;dk<=1;dk++)for(let dl=-1;dl<=1;dl++){const k2=k+dk,l2=l+dl;if(k2<0||l2<0||k2>GW||l2>GH)continue;const id=l2*(GW+1)+k2;if(D[id]<0){D[id]=d+0.5;fr.push(k2,l2)}}}
  const dAt=(k,l)=>rect?(alongA?Math.min(l,GH-l):Math.min(k,GW-k))*0.5:D[l*(GW+1)+k];
  let dmax=0.5;for(let l=0;l<=GH;l++)for(let k=0;k<=GW;k++)dmax=Math.max(dmax,dAt(k,l));
  const pitch=Math.min(thatch?0.85:0.7,2.4/dmax),base=yo+(lt||V3.STOREY)+0.06,ov=0.22,rmain=Object.keys(races).sort((p,q)=>races[q]-races[p])[0],RRC={silk:[0.86,0.85,0.8,1],flesh:[0.5,0.15,0.19,1],elf:[0.44,0.56,0.4,1],tribal:[0.72,0.63,0.37,1]},rcR=rmain&&races[rmain]*2>=wood+stone?RRC[rmain]:null,rc=rcR||(thatch?[0.66,0.52,0.28,1]:[0.32,0.34,0.39,1]);
  const P=(k,l)=>{const d=dAt(k,l),L=qin(k-1,l-1)||qin(k-1,l),R=qin(k,l-1)||qin(k,l),S=qin(k-1,l-1)||qin(k,l-1),N=qin(k-1,l)||qin(k,l);
   const ox=(L&&!R?1:0)-(R&&!L?1:0),oy=(S&&!N?1:0)-(N&&!S?1:0);
   return [T.x0+a0-0.5+k/2+ox*ov,base+pitch*d-(d===0&&(ox||oy)?pitch*ov:0),-(T.y0+b0-0.5+l/2+oy*ov)]};
  const nrm=(p,q2,r)=>{const u=[q2[0]-p[0],q2[1]-p[1],q2[2]-p[2]],v=[r[0]-p[0],r[1]-p[1],r[2]-p[2]];let n=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]];if(n[1]<0)n=n.map(x=>-x);const m=Math.hypot(...n)||1;return n.map(x=>x/m)};
  for(let l=0;l<GH;l++)for(let k=0;k<GW;k++){if(!qin(k,l))continue;const p0=P(k,l),p1=P(k+1,l),p2=P(k+1,l+1),p3=P(k,l+1);
   // courses of thatch or slate run along the slope's contour; split each quarter along its hip or valley
   const dd=(dAt(k,l)+dAt(k+1,l)+dAt(k+1,l+1)+dAt(k,l+1))/4,c=MD.shade(rc,(dd<0.3?0.74:0.84)+((Math.floor(dd*4))%2)*0.1+MD.h(T.x0+a0+k,T.y0+b0+l,88)*0.08);
   if(Math.abs(p0[1]-p2[1])>=Math.abs(p1[1]-p3[1])){tri(arr,p0,p1,p2,nrm(p0,p1,p2),c);tri(arr,p0,p2,p3,nrm(p0,p2,p3),c)}else{tri(arr,p1,p2,p3,nrm(p1,p2,p3),c);tri(arr,p1,p3,p0,nrm(p1,p3,p0),c)}
   // the roof's thickness along its edges
   const ec=MD.shade(rc,0.55),edge=(A,B,n)=>quad(arr,A,B,[B[0],B[1]-0.1,B[2]],[A[0],A[1]-0.1,A[2]],n,ec);
   if(!qin(k,l-1))edge(p0,p1,[0,0,1]);if(!qin(k,l+1))edge(p3,p2,[0,0,-1]);if(!qin(k-1,l))edge(p0,p3,[-1,0,0]);if(!qin(k+1,l))edge(p1,p2,[1,0,0])}
  if(rect){
   // gable ends (of the walls' timber boards or stone), a ridge roll along the top
   const gc=rcR?MD.shade(rcR,0.8):thatch?[0.47,0.33,0.21,1]:[0.58,0.55,0.5,0.99],half=(alongA?GH:GW)/4,ridge=base+pitch*half;
   for(const end of [0,1]){const along=alongA?b1-b0+1:a1-a0+1;
    for(let q=0;q<along*4;q++){const u0=q/4,u1=(q+1)/4,t0=base+pitch*Math.min(u0,along-u0)-0.05,t1=base+pitch*Math.min(u1,along-u1)-0.05,c=MD.shade(gc,0.8+MD.h(q,end,90)*(thatch?0.18:0.06));
     if(alongA){const x=T.x0+(end?a1+0.5:a0-0.5),z0=-(T.y0+b0-0.5+u0),z1=-(T.y0+b0-0.5+u1);quad(arr,[x,base-0.1,z0],[x,base-0.1,z1],[x,t1,z1],[x,t0,z0],[end?1:-1,0,0],c)}
     else{const z=-(T.y0+(end?b1+0.5:b0-0.5)),x0=T.x0+a0-0.5+u0,x1=T.x0+a0-0.5+u1;quad(arr,[x0,base-0.1,z],[x1,base-0.1,z],[x1,t1,z],[x0,t0,z],[0,0,end?-1:1],c)}}}
   const rr=MD.shade(rc,thatch?0.7:0.6),r0=alongA?[T.x0+a0-0.5-ov,ridge+0.03,-(T.y0+b0-0.5+half)]:[T.x0+a0-0.5+half,ridge+0.03,-(T.y0+b0-0.5-ov)],r1=alongA?[T.x0+a1+0.5+ov,ridge+0.03,r0[2]]:[r0[0],ridge+0.03,-(T.y0+b1+0.5+ov)];
   MD.rod(arr,r0,r1,thatch?0.09:0.06,6,rr,a0+b0)}
  const buf=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,buf);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(arr),gl.STATIC_DRAW);comp.forEach(([a,b])=>roofed.add(a+','+b));V3[slot].push({buf,count:arr.length/12,tiles,area:new Set([...fp].map(k=>{const [a,b]=k.split(',').map(Number);return (T.x0+a)+','+(T.y0+b)})),key:yo+':'+(T.x0+i)+','+(T.y0+j)})}}
// Rock and tree animations: compare the new terrain with the last one. A rock tile
// that opened up crumbles into tumbling chunks and dust; a tree that is gone tips
// over on its base and crashes down. Only the same layer, only near the camera.
function v3terrainFx(A,B){if(!A||!B||A.z!==B.z||!V3.on)return;V3.fx=V3.fx||[];const now=performance.now();let n=0;
 const kindOf=(T,x,y)=>{const i=x-T.x0,j=y-T.y0;if(i<0||j<0||i>=T.w||j>=T.h)return undefined;const c=T.tiles[j*T.w+i];return c?T.kinds[c-1]:null};
 for(let j=0;j<B.h&&n<24;j++)for(let i=0;i<B.w&&n<24;i++){const x=B.x0+i,y=B.y0+j,a=kindOf(A,x,y);if(a===undefined||!a)continue;const c=B.tiles[j*B.w+i],b=c?B.kinds[c-1]:null;if(!b)continue;
  const wasRock=a.kind==='wall'||a.kind==='block',nowOpen=!['wall','block','built','tree','void'].includes(b.kind);
  const w=V3.work&&V3.work.get(x+','+y);V3.bfx=V3.bfx||[];
  if(a.roof&&a.kind!=='wall'&&b.kind!=='wall'&&(b.roof||0)<a.roof){V3.bfx.push({type:'burst',x,y,t:now,col:hexrgb(a.color||'#777777',1),geo:V3.rockGeo&&V3.rockGeo.get(x+','+y),level:a.ceil||2,dx:0,dy:0});n++}
  // a block laid by a plan (construction-3d): dust settles round its foot, not a rockfall
  else if(b.kind==='wall'&&b.lay&&(a.kind!=='wall'||(b.lay&~(a.lay||0)))){const c=typeof v3layWoodish==='function'&&v3layWoodish(b)?[0.62,0.5,0.36]:[0.74,0.71,0.66];for(let q=0;q<6;q++){const an=q*1.047+(x*7+y)%3;V3.fx.push({type:'dust',x:x+Math.cos(an)*0.5,y:y+Math.sin(an)*0.5,t:now+q*25,col:c,seed:(x*31+y*17+q)%997})}n++}
  else if(b.kind==='wall'&&!['wall','block','built','void','tree'].includes(a.kind)){V3.bfx.push({type:'collapse',x,y,t:now,col:hexrgb(b.color||'#777777',1)});n++}
  else if(a.kind==='wall'&&b.kind==='wall'&&!a.dug&&b.dug){V3.bfx.push({type:'burst',x,y,t:now,col:hexrgb(a.color||'#777777',1),geo:V3.rockGeo&&V3.rockGeo.get(x+','+y),level:b.dug===2?1:0,dx:w?w.dx:0,dy:w?w.dy:0});n++}
  else if(wasRock&&nowOpen){const gg=V3.rockGeo&&V3.rockGeo.get(x+','+y);V3.bfx.push({type:'burst',x,y,t:now,col:hexrgb(a.color||'#777777',1),geo:gg,level:gg&&gg.cut?1:0,dx:w?w.dx:0,dy:w?w.dy:0});n++}
  else if(a.kind==='tree'&&b.kind!=='tree'){V3.bfx.push({type:'fell',x,y,t:now,K:a,dx:w?w.dx:0,dy:w?w.dy:0});n++}
  // a built wall breached (a siege engine, Siege.dm RemasterSiegeBreak): the whole wall's height bursts into stone blocks, or splinters from a timber wall
  else if(a.kind==='built'&&nowOpen){V3.bfx.push({type:'burst',x,y,t:now,col:a.wood?[0.45,0.3,0.16,1]:hexrgb(a.color||'#8a847a',1),level:0,dx:0,dy:0,top:2.2,big:1});n++}
  // a wall or building piece finished: a ring of dust settles round its foot (and audio can sound it)
  else if((b.kind==='built'||b.kind==='bfloor')&&a.kind!==b.kind&&a.kind!=='built'){const c=b.wood?[0.62,0.5,0.36]:[0.72,0.7,0.66];for(let q=0;q<6;q++){const an=q*1.047+(x*7+y)%3;V3.fx.push({type:'dust',x:x+Math.cos(an)*0.45,y:y+Math.sin(an)*0.45,t:now+q*25,col:c,seed:(x*31+y*17+q)%997})}n++;try{window.rmSfx&&rmSfx.at('built',x,y,{kind:b.kind})}catch(e){}}}}
