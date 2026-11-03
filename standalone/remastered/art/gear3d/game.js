// The animations in the game (planning/ANIMATIONS_INTO_GAME.md). Three things the arena doesn't need:
// - each unit's doll is cut from its own picture as it wears it, by its race's part map (parts.py --races), read back
//   from the unit's own texture once a look (g3cut);
// - the game sends every unit afresh each update (View3D.dm), but the moves and dolls hold their unit: a unit in the
//   middle of one keeps its object, the update's fields put on it (g3rebind), still flagged as drawn by its doll
//   (ragdoll.js rdHide); the body a death doll lies over stays in the list (clicks, the carry menu) with its own
//   picture left out, and once the doll has settled its last pose is the body's look for as long as it lies (g3poses);
// - the server's blows and deaths (Hits.dm, the page's v3hits) play as moves: the striker's swing with its own weapon,
//   the guard, the flinch or the fall, a death of something else acted out (g3hit).
const G3G={cur:new Map(),gone:new Map(),at:new Map(),cuts:new Map(),maps:new Map(),dead:[],killAt:new Map(),n:0,max:40,game:!!window.G3GAME,poses:new Map(),posed:[],swingAt:new Map(),knocked:new Set(),knockAt:new Map(),bodySeen:new Map()};
const G3KEEP=new Set(['key','g3last','maimed','bleed','dead','g3hide','g3doll','g3dir','g3wk','g3cl','g3cs','g3ko','g3cy','g3cyd','g3maim','g3maimS','g3limbAt','g3limbKey','g3dropAt']);
const G3LOST=[['armRu','armRl'],['armLu','armLl'],['legRu','legRl'],['legLu','legLl']];   /* the server's bits (Gear3D.dm): right arm, left arm, right leg, left leg */

// --- the part maps and the cut -------------------------------------------------------------------------------------
// A race's map for one facing, decoded once: codes (0-9 the parts in RDPARTS order, 10 the torso from its own pixels,
// 11 nothing, 255 unknown), where the body shows under the arms, and the joints.
function g3map(sheet,f,sleeved){const k=sheet+'|'+f+(sleeved?'|s':'');let M=G3G.maps.get(k);if(M)return M;const R=RD.rig&&RD.rig.sheets&&RD.rig.sheets[sheet],m=R&&R[f];if(!m)return null;
 const dec=(s,fn)=>{const out=new Uint8Array(4096);let i=0;const re=/([A-L.YN])(\d+)/g;let r;while((r=re.exec(s))){const v=fn(r[1]);for(let n=+r[2];n>0&&i<4096;n--)out[i++]=v}return out};
 M={codes:dec(sleeved&&m.labs?m.labs:m.lab,c=>c==='.'?255:c.charCodeAt(0)-65),fill:dec(m.fill,c=>c==='Y'?1:0),j:m.j};G3G.maps.set(k,M);return M}
// The standing frame of a unit's picture (its strip's first 64 px), read back from its texture: null until loaded.
function g3pixels(file){const e=file&&V3.tex.get(file);if(!e||!e.ok||!e.t)return null;const gl=V3.gl;if(!gl)return null;
 const fb=G3G.fb||(G3G.fb=gl.createFramebuffer()),prev=gl.getParameter(gl.FRAMEBUFFER_BINDING);gl.bindFramebuffer(gl.FRAMEBUFFER,fb);
 gl.framebufferTexture2D(gl.FRAMEBUFFER,gl.COLOR_ATTACHMENT0,gl.TEXTURE_2D,e.t,0);let px=null;
 if(gl.checkFramebufferStatus(gl.FRAMEBUFFER)===gl.FRAMEBUFFER_COMPLETE){px=new Uint8Array(16384);gl.readPixels(0,0,64,64,gl.RGBA,gl.UNSIGNED_BYTE,px)}
 gl.framebufferTexture2D(gl.FRAMEBUFFER,gl.COLOR_ATTACHMENT0,gl.TEXTURE_2D,null,0);gl.bindFramebuffer(gl.FRAMEBUFFER,prev);return px}
// One facing cut: each opaque pixel to its part by the map, the ones it doesn't know to the part they touch (a flood,
// parts.py's way); where an arm lay over the body, the torso gets the body's own pixels from along that row (an even
// step first, so mail and bands run on). Ten 64 px cells side by side, as parts.py writes them.
function g3cutFacing(px,M){const lab=new Uint8Array(4096).fill(255),q=[];
 for(let i=0;i<4096;i++){if(!px[i*4+3])continue;const c=M.codes[i];if(c!==255){lab[i]=c;if(c!==11)q.push(i)}}
 for(let h=0;h<q.length;h++){const i=q[h],x=i&63,y=i>>6,c=lab[i]===10?1:lab[i];
  for(const n of [x>0?i-1:-1,x<63?i+1:-1,y>0?i-64:-1,y<63?i+64:-1])if(n>=0&&lab[n]===255&&px[n*4+3]){lab[n]=c;q.push(n)}}
 const cv=document.createElement('canvas');cv.width=640;cv.height=64;const cx=cv.getContext('2d'),D=cx.createImageData(640,64),o=D.data,bx=RDPARTS.map(()=>null);
 const put=(p,x,y,s)=>{const d=(y*640+p*64+x)*4;o[d]=px[s];o[d+1]=px[s+1];o[d+2]=px[s+2];o[d+3]=px[s+3];const b=bx[p];if(!b)bx[p]=[x,y,x+1,y+1];else{if(x<b[0])b[0]=x;if(y<b[1])b[1]=y;if(x+1>b[2])b[2]=x+1;if(y+1>b[3])b[3]=y+1}};
 const torsoNear=(x,y)=>{for(const dy of [0,-1,1,-2,2]){const yy=y+dy;if(yy<0||yy>63)continue;for(let k=1;k<12;k++)for(const s of [k%2?0:1,k%2?1:0])if(s){for(const xx of [x-k,x+k])if(xx>=0&&xx<64&&lab[yy*64+xx]===1)return (yy*64+xx)*4}}
  for(const dy of [0,-1,1,-2,2]){const yy=y+dy;if(yy<0||yy>63)continue;for(let k=1;k<16;k++)for(const xx of [x-k,x+k])if(xx>=0&&xx<64&&lab[yy*64+xx]===1)return (yy*64+xx)*4}return -1};
 for(let i=0;i<4096;i++){const l=lab[i];if(l===255||l===11)continue;const x=i&63,y=i>>6;
  if(l<10)put(l,x,y,i*4);
  if((l===10||(l>=2&&l<=5&&M.fill[i]))){const s=torsoNear(x,y);if(s>=0)put(1,x,y,s)}}
 cx.putImageData(D,0,0);const rig={};
 for(let p=0;p<RDPARTS.length;p++){const name=RDPARTS[p],j=M.j[name]||{};rig[name]={box:bx[p],root:j.root||null,tip:j.tip||null}}
 if(!rig.torso.root&&rig.torso.box)rig.torso.root=[(rig.torso.box[0]+rig.torso.box[2])/2,rig.torso.box[3]];
 return {rig,cv}}
// A unit's doll parts for each facing, cut from its own pictures (t.texd: S, N, E, W) by its race's map, kept for its
// look (the most recent 48 looks, none a doll still uses). The page loads a facing's picture only once the unit is seen
// that way: the others are cut when they are in (asked for now); a doll without its back picture shows its front
// turned over (rdMake). Null until the facing it is seen from is cut.
function g3cut(t){if(!t.g3||!t.texd||t.texd.length<4)return null;const sl=!!t.g3.arms,key=t.g3.sheet+(sl?'|s|':'|')+t.texd.join('|');   /* arms: in arm armour (Gear3D.dm) */let out=G3G.cuts.get(key);
 if(out){G3G.cuts.delete(key);G3G.cuts.set(key,out)}
 else{if(G3G.cuts.size>=48){const used=new Set(RD.dolls.map(d=>d.idx));for(const P of G3G.poses.values())used.add(P.idx);   /* a body's kept pose draws with its cut */for(const [k,v] of G3G.cuts){if(G3G.cuts.size<48)break;if(used.has(k))continue;
   for(const f in v.tex){const e=V3.tex.get(v.tex[f]);if(e&&e.t&&V3.gl)V3.gl.deleteTexture(e.t);V3.tex.delete(v.tex[f])}G3G.cuts.delete(k)}}
  out={idx:key,rig:{},tex:{}};G3G.cuts.set(key,out)}
 for(let fi=0;fi<4;fi++){const f='SNEW'[fi];if(out.rig[f])continue;const M=g3map(t.g3.sheet,f,sl);if(!M)continue;const px=g3pixels(t.texd[fi]);if(!px){if(typeof v3tex==='function')v3tex(t.texd[fi]);continue}
  const r=g3cutFacing(px,M),tk='g3k-'+(++G3G.n)+'-'+f+'.png',e={t:null,ok:false};V3.tex.set(tk,e);if(typeof v3texUpload==='function')v3texUpload(r.cv,e);else (V3.texQ||(V3.texQ=[])).push([r.cv,e]);out.rig[f]=r.rig;out.tex[f]=tk}
 return out.rig['SNEW'[(t.g3last&&t.g3last.face)||0]]?out:null}
// The parts a doll is made of: the arena's lineup cut ahead (parts.py), or, with the races' maps, the unit's own picture cut.
function rdRigOf(t){const R=RD.rig;if(!R)return null;if(R.sheets)return g3cut(t);
 const idx=String(t.ref||'').replace(/^g3/,'').replace(/_c\d+$/,''),rig=R[idx];if(!rig)return null;return {idx,rig,tex:{S:'g3r-'+idx+'-S.png',N:'g3r-'+idx+'-N.png',E:'g3r-'+idx+'-E.png',W:'g3r-'+idx+'-W.png'}}}

// --- each update ---------------------------------------------------------------------------------------------------
// The update's fields onto the unit's own object (the server's, all of them; the page's own kept).
function g3adopt(o,t){for(const k in o)if(!(k in t)&&!G3KEEP.has(k))delete o[k];Object.assign(o,t);o.g3p=undefined;o.g3kk=undefined;if(o.g3dir)o.dir=o.g3dir}   /* a climber stays turned to show its back */
// Limbs the server says it has lost: gone from every doll it makes (rdMake), with the page's own.
function g3lost(t){const b=t.g3&&t.g3.lost;if(!b)return;const m=new Set(t.maimed||[]);for(let k=0;k<4;k++)if(b&(1<<k))for(const p of G3LOST[k])m.add(p);t.maimed=[...m]}
// A unit at work (t.g3wk) that the moves push says stepped off its doll's tile (remastered.html move3D, every tick):
// its work ends and its own picture walks on now, by g3rebind's rule below, not when the next scene comes (hud-controls,
// 10-26: with Shift-queued gathering the doll kept swinging at the old tree while its ring walked on to the next).
function g3stepped(){if(typeof RD==='undefined'||!RD.dolls.length)return;for(const d of RD.dolls){if(d.done||d.ghost||!d.alive)continue;const t=d.t;
 if(t&&t.g3wk&&t.g3doll&&!t.dead&&!t.g3cl&&!t.g3cy&&!t.g3ko&&(d.tx!==t.x||d.ty!==t.y)){rdStopActs(t);d.done=true;rdShow(t)}}}
function g3rebind(){if(typeof RD==='undefined'){for(const t of V3.things){if(!t.g3)continue;const kd=V3.disp.get(t.key);if(kd&&kd.g3last&&!t.g3last)t.g3last=kd.g3last}return}
 if(!RD.rig)rdLoad();if(typeof mfLoad==='function'&&typeof MF!=='undefined'&&!MF.meta)mfLoad();
 if(!G3G.wrap&&typeof v3ghost==='function'){G3G.wrap=1;const g0=v3ghost;window.v3ghost=function(kd){if(kd&&kd.g3dead)return;return g0(kd)}}   /* a death doll, not the page's fading picture */
 if(!G3G.wrapMv&&typeof window.move3D==='function'){G3G.wrapMv=1;const m0=window.move3D;window.move3D=function(raw){m0(raw);try{g3stepped()}catch(e){console.error(e)}}}   /* a working unit stepping on leaves its doll at once (g3stepped) */
 const now=performance.now(),keep=new Map(),hold=t=>{if(t&&t.key!=null)keep.set(t.key,t)};
 for(const d of RD.dolls)hold(d.t);for(const s of RD.shots){hold(s.t);hold(s.target)}
 if(typeof SK!=='undefined')for(const A of SK.acts.concat(SK.pending||[])){hold(A.t);hold(A.target)}
 const live=new Set();for(const d of RD.dolls)if(!d.done&&!d.ghost&&d.t)live.add(d.t.key);
 const bodies=new Map();for(const D of G3G.dead)if(!D.over&&!D.handed)bodies.set(D.tile,D);
 const cur=new Map(),at=new Map(),out=[],seen=new Map(),posed=[];
 for(let t of V3.things){const o=keep.get(t.key);if(o&&o!==t){g3adopt(o,t);t=o}
  const kn=G3G.knockAt.get(t.key);if(kn&&t.x===kn.ox&&t.y===kn.oy&&now-kn.at<2500){t.x=kn.x;t.y=kn.y}   /* a scene listed before it was thrown (Spread.dm): the server has it where it threw it (g3knock3D) */
  if(t.g3){const kd=V3.disp.get(t.key);if(kd&&kd.g3last&&!t.g3last)t.g3last=kd.g3last;g3lost(t);cur.set(t.key,t);at.set(t.x+','+t.y,t);if(!window.G3NODOLLS&&(t.climb||t.g3cl||t.g3.work||t.g3wk))g3jobs(t);if(!window.G3NODOLLS)g3state(t)}
  else if(t.m3==='door'&&t.mat==='stone'){const r=G3.ready?1:0;if(t.g3s!==r){t.g3s=r;t._os=null}}   /* its look (g3stoneDoor) once the meshes are in: a new key for the page's kept geometry */
  if(t.g3doll&&!live.has(t.key)&&!rdLive(t))t.g3doll=false;   /* its doll gone some other way */
  if(t.g3doll&&!t.dead&&!t.g3cl&&!t.g3cy&&!t.g3ko){const d=RD.dolls.find(x=>x.t===t&&!x.done&&!x.ghost&&x.alive);if(d&&(d.tx!==t.x||d.ty!==t.y)){rdStopActs(t);if(d.cut)d.ghost=true;else d.done=true;rdShow(t)}}
  if(t.g3ko&&!t.dead){const d=RD.dolls.find(x=>x.t===t&&!x.done&&!x.ghost&&!x.air);if(d&&(d.tx!==t.x||d.ty!==t.y)){const X=d.O[0]+t.x-d.tx,Z=d.O[2]-(t.y-d.ty);d.O=[X,rdGround(X,Z),Z];d.tx=t.x;d.ty=t.y}}   /* down and moved by the server (carried to the Doctor's table, "Carry them", dragged: Surgery.dm, TargetActions.dm): its doll goes with it, a tile at a time */   /* it stepped on: its move ends, its own picture walks (never a doll left behind) */
  if(t.body&&!G3G.bodySeen.has(t.key)){G3G.bodySeen.set(t.key,now);if(G3G.bodySeen.size>4000)G3G.bodySeen.clear()}   /* when each body first came (g3dying's before) */
  if(t.body){const D=bodies.get(t.x+','+t.y);if(G3G.poses.has(t.key)){t.g3doll=true;posed.push(t)}else if(D&&!D.before.has(t.key)){t.g3doll=true;if(!seen.has(D))seen.set(D,t)}}   /* under its death doll (not a body that lay there before), or lying as its doll did: its own picture left out, clicked all the same */
  out.push(t)}
 for(const [k,t] of G3G.cur)if(!cur.has(k))G3G.gone.set(k,{t,at:now});
 for(const [k,g] of G3G.gone)if(now-g.at>2500||cur.has(k))G3G.gone.delete(k);
 for(const [k,v] of G3G.knockAt)if(now-v.at>2500)G3G.knockAt.delete(k);
 // a doll still upright whose unit has left the scene (the owner 10-28: "still some bodys are left standing"; a big
 // fight's hits reach the page 160 at a time, so a death can come without its hit): with a body on its tile it died
 // there and falls as any death does (g3dying); else it went out of view, and its doll goes with it
 {const bodyAt=new Set();for(const o of out)if(o.body)bodyAt.add(o.x+','+o.y);
  for(const d of RD.dolls){const T=d.t;if(d.done||d.ghost||!d.alive||!T||cur.has(T.key))continue;const g=G3G.gone.get(T.key);if(g&&now-g.at<1500)continue;if(G3G.dead.some(D=>D.T===T&&!D.over))continue;
   if(!T.dead&&bodyAt.has(T.x+','+T.y))g3dying(T,T.x+','+T.y,null);else{rdStopActs(T);d.done=true}}}
 G3G.cur=cur;G3G.at=at;V3.things=out;G3G.posed=posed;for(const b of posed){const P=G3G.poses.get(b.key);b.g3pc=[P.cx+(b.dx??b.x)-P.x0,P.cz-((b.dy??b.y)-P.y0)]}   /* clicked where it lies (remastered.html v3pickThing) */
 // a death doll falls whatever else happens (a blow that never lands, a move that took over: never left standing); once
 // it has settled, its last pose is the body's look (the user, 2026-10-25: "let that be their final pose or what they
 // look like dont revert to the other one"): kept by the body's key and drawn where the body is (g3poses), the body
 // still the one to click (loot, carry, bury); with no body (bones, nothing left) it lies a minute
 const dm=new Map();for(const x of RD.dolls)if(!x.done&&!x.ghost&&!dm.has(x.t))dm.set(x.t,x);   /* each unit's doll, looked up once: a big fight's deaths each searched every doll */
 for(const D of G3G.dead){if(D.over)continue;const d=dm.get(D.T);
  if(d&&d.alive&&now-D.t0>(D.grace||1500))rdStart(D.T,'fall',D.from||null);
  if(d&&!d.alive&&!D.fell)D.fell=now;if(seen.has(D))D.body=seen.get(D);
  if(d&&D.fell&&now-D.fell>5000&&!d.frozen)d.freeze=true;   /* settled or not, it holds still now (its pictures kept, ragdoll.js rdFrame) */
  if(D.body&&d&&d.frozen&&d.cache){g3keepPose(D.body,d);D.over=D.handed=true;d.done=true;continue}
  if(D.body&&!d&&now-D.t0>1500){D.over=D.handed=true;continue}   /* (its death act takes its doll a frame or two after it starts: not handed to its body meanwhile) */   /* its doll gone some other way: the body as the server draws it */
  if(now-D.t0>60000){D.over=true;if(d)d.done=true}}
 G3G.dead=G3G.dead.filter(D=>!D.over);if(G3G.dead.length>400)for(const D of G3G.dead.splice(0,G3G.dead.length-400)){const d=dm.get(D.T);if(d&&d.alive)rdStart(D.T,'fall',D.from||null)}   /* the last 400 deaths at once (was 40: in a big fight older ones were let go still standing, the owner 10-28); past that the oldest fall as they go */
 // what fell from a dead unit lies on the ground as the game's own item: the 3D piece goes once it has come to rest
 // a piece the game said where it comes down lies there as that item's look (its own picture left out) till it is taken
 if(G3G.game){let items=null;for(const b of RD.loose){
   if(b.itemKey){if(!items){items=new Map();for(const t of V3.things)if(t.kind==='item')items.set(t.key,t)}const it=items.get(b.itemKey),T=V3.terrain;
    if(it){if(b.tile&&(it.x!==b.tile[0]||it.y!==b.tile[1])){b.gone=true;continue}it.g3doll=true;it.g3pc=[b.X[0],b.X[2]];b.seenAt=now}   /* clicked where the piece lies */
    else if(T&&T.z===b.z&&b.tile&&b.tile[0]>=T.x0&&b.tile[1]>=T.y0&&b.tile[0]<T.x0+T.w&&b.tile[1]<T.y0+T.h&&now-(b.seenAt||now)>2500)b.gone=true;   /* taken: the piece goes with it */
    if(b.seenAt==null)b.seenAt=now;continue}
   if(b.rest&&!b.restAt)b.restAt=now;if(b.restAt&&now-b.restAt>1500&&!(b.doll&&!b.doll.done&&b.doll.alive&&b.doll.kind==='ko'))b.gone=true}}   /* out cold: what it dropped lies there till it gets up and takes it back */
 // a limb cut off (Gear3D.dm RmG3Limb names its item; ragdoll.js rdKind): the animation's own limb is that item's look, in
 // the air and where it lies (its own picture left out), till it is taken, moved or rots; after a death the body's kept
 // pose holds it (the owner, 10-26: "we want the animations limbs")
 if(G3G.game&&G3G.limbs&&G3G.limbs.size){const items=new Map();for(const t of V3.things)if(t.kind==='item')items.set(t.key,t);const T=V3.terrain;
  for(const [k,L] of G3G.limbs){const d=L.d;if(d.done&&!d.frozen){G3G.limbs.delete(k);continue}   /* its doll gone some other way: the item as the server draws it */
   const it=items.get(k);
   if(it){if(L.tile&&(it.x!==L.tile[0]||it.y!==L.tile[1])&&now-L.t0>3000){if(d.ghost)d.done=true;else g3poseLimbGone(k);G3G.limbs.delete(k);continue}it.g3doll=true;L.seenAt=now;if(d.cut&&d.cut.mid)it.g3pc=[d.cut.mid[0],d.cut.mid[2]]}   /* moved: taken up and put down; clicked where the limb lies */
   else if(L.seenAt!=null&&T&&L.tile&&L.tile[0]>=T.x0&&L.tile[1]>=T.y0&&L.tile[0]<T.x0+T.w&&L.tile[1]<T.y0+T.h&&now-L.seenAt>2500){if(d.ghost)d.done=true;else g3poseLimbGone(k);G3G.limbs.delete(k)}}   /* taken, or rotted */
  if(G3G.limbs.size>80)for(const [k,L] of G3G.limbs){if(G3G.limbs.size<=80)break;if(L.d.ghost)L.d.done=true;G3G.limbs.delete(k)}}}

// --- a body's last pose ----------------------------------------------------------------------------------------------
// A settled death doll's pictures (d.cache: its parts in the world, as drawn) become its body's look, kept by the body's
// key through the server's refreshes, scene rebuilds and level changes, and moved with the body when it is dragged
// (capture-rope's "Drag body"). The most recent 150 are kept (each holds its look's cut, g3cut); an older one, or a body
// seen first after a relog, lies as its own picture.
function g3keepPose(b,d){const c=[],lv=d.cutVerts&&d.cutVerts.length?d.cutVerts.map(r=>[...r]):null;let sx=0,sz=0,n=0;for(const [tex,f] of d.cache){c.push([tex,f.slice()]);const r=lv&&lv.filter(r=>r[0]===tex);for(let i=0;i<f.length;i+=12){if(r&&r.some(r=>i>=r[1]&&i<r[2]))continue;sx+=f[i];sz+=f[i+2];n++}}   /* its middle: the body's, its lost limb left out */
 const x=b.dx??b.x,y=b.dy??b.y,P={cache:c,moved:c,idx:d.idx,x0:x,y0:y,g0:rdGround(x,-y),cx:n?sx/n:x,cz:n?sz/n:-y,ox:0,oz:0,limbVerts:lv,limbKey:lv&&d.cut?d.cut.key:null};   /* its lost limb's pictures: they stay where they lie when it is pulled (g3towPose) */
 G3G.poses.delete(b.key);G3G.poses.set(b.key,P);while(G3G.poses.size>150)G3G.poses.delete(G3G.poses.keys().next().value);
 b.g3doll=true;if(!G3G.posed.includes(b))G3G.posed.push(b);b.g3pc=[P.cx,P.cz]}
// Its lost limb's item taken, moved or rotted (g3rebind's limb registry): its pictures in the body's kept pose are folded
// to a point, so nothing of it is drawn there (where it is now, the item draws itself).
function g3poseLimbGone(k){for(const P of G3G.poses.values()){if(!k||P.limbKey!==k||!P.limbVerts)continue;P.limbKey=null;
 for(const A of new Set([P.cache,P.moved]))for(const [tex,f] of A)for(const r of P.limbVerts)if(r[0]===tex)for(let i=r[1];i<r[2];i+=12){f[i]=f[r[1]];f[i+1]=f[r[1]+1];f[i+2]=f[r[1]+2]}
 P.qa=null}}   /* a pull's next frame redraws from the folded pictures */
// Each frame (ragdoll.js rdFrame, with the dolls' pictures): the kept poses where their bodies are now.
function g3poses(){if(typeof g3tows==='function')g3tows();   /* pulled along (g3tows) */for(const b of G3G.posed){const P=G3G.poses.get(b.key);if(!P||G3G.tows&&G3G.tows.has(b.key)||(typeof v3visible==='function'&&!v3visible(b)))continue;
  const x=b.dx??b.x,y=b.dy??b.y,ox=x-P.x0,oz=-(y-P.y0);
  if(ox!==P.ox||oz!==P.oz){const oy=ox||oz?rdGround(x,-y)-P.g0:0;P.ox=ox;P.oz=oz;P.moved=!ox&&!oz?P.cache:P.cache.map(([tex,f])=>{const g=f.slice();for(let i=0;i<g.length;i+=12){g[i]+=ox;g[i+1]+=oy;g[i+2]+=oz}return [tex,g]})}   /* dragged: moved along with it */
  for(const [tex,f] of P.moved){let va=RD.va.get(tex);if(!va){va=new VA();RD.va.set(tex,va)}va.copy(f,0,f.length)}}}

// --- the server's blows and deaths ---------------------------------------------------------------------------------
// The unit on a tile: in this update, else one the update took away (it died).
function g3at(x,y){const t=G3G.at.get(x+','+y);if(t)return t;let best=null;for(const g of G3G.gone.values())if(g.t.x===x&&g.t.y===y&&(!best||g.at>best.at))best=g;return best?best.t:null}
const g3seen=t=>{if(!t||!t.g3last||t.g3last.at==null)return false;const r=(V3.dist||20)*1.4+10;return Math.abs((t.dx??t.x)-(V3.cx??t.x))<r&&Math.abs((t.dy??t.y)-(V3.cy??t.y))<r};   /* drawn once, and near the camera: kept and walking records (a still or walking unit) don't run the gear code each frame */
const g3busy=()=>RD.dolls.filter(d=>!d.done&&!d.ghost&&d.alive).length>=G3G.max;   /* a lost limb lying is not a doll playing */
// The move its weapon swings (skills.js), its own weapon in hand.
function g3move(t,kill){const w=t.g3&&t.g3.w?t.g3.w.split(':')[0]:'',has=s=>SKWEAPON[s]&&SKWEAPON[s].includes(w);if(t.g3&&t.g3.s&&Math.random()<(kill?0.1:0.15))return 'bash';   /* now and then its shield in the foe's face */
 if(!w)return 'punch';if(SKWEAPON.cast.includes(w))return 'cast';if(w==='warhammer')return kill&&Math.random()<0.5?'launch':'smash';
 if(w==='halberd')return Math.random()<0.5?'sweep':'chop';if(has('slash')&&has('thrust'))return Math.random()<0.7?'slash':'thrust';
 for(const s of ['slash','thrust','chop','smash','stab'])if(has(s))return s;return 'smash'}
// Its guard against a blow (skills.js opt.guard), from what the server says the blow did.
function g3guard(k,T,n){if(k==='hit'&&n!=null&&n<=1&&T.g3&&(T.g3.arms||T.g3.h))return 'armour';   /* the blow did nothing through its armour: it glances off */if(k==='miss')return 'dodge';if(k==='block')return T.g3&&T.g3.s?'block':'parry';if(k==='parry'||k==='guard')return T.g3&&T.g3.w?'parry':'dodge';return undefined}
const g3from=(h)=>{const dx=h.x-h.ax,dz=-(h.y-h.ay),l=Math.hypot(dx,dz)||1;return [dx/l,0,dz/l]};
// A dead unit's doll keeps its place as its body (g3rebind), and the page's fading picture of it gives way.
function g3dying(T,tile,from){T.dead=true;const kd=V3.disp.get(T.key);if(kd)kd.g3dead=1;
 if(V3.ghosts)V3.ghosts=V3.ghosts.filter(g=>!(Math.abs(g.x-(T.dx??T.x))<0.6&&Math.abs(g.z+(T.dy??T.y))<0.6&&performance.now()-g.t0<1500));
 const D={tile,T,from,t0:performance.now(),body:null,over:false,before:new Set(V3.things.filter(o=>o.body&&o.x+','+o.y===tile&&G3G.bodySeen.has(o.key)&&performance.now()-G3G.bodySeen.get(o.key)>2500).map(o=>o.key))};G3G.dead.push(D);return D}   /* before: bodies that lay there before. Its own body can come in a scene before its death does (Death.dm MakeBody, then the hit): seen under 2.5 s ago it is this one's, which its doll lies over, else the corpse showed and the doll stood up and fell again (the owner, 10-28: "Death animation loop") */
// Each new hit (the page's v3hits, once each). Sets h.g3late (ms till the doll's blow lands, for the number and flash),
// h.g3shot (the doll looses the arrow or throws: not the page's own projectile) and h.g3swing (not the page's swing).
function g3hit(h){if(window.G3NODOLLS||typeof RD==='undefined'||typeof SK==='undefined')return;if(!RD.rig){rdLoad();return}   /* G3NODOLLS (Gear3D.dm rm_g3_dolls 0): no dolls at all */
 const tile=h.x+','+h.y,noDeath=!!window.G3NODEATHS;   /* Gear3D.dm rm_g3_doll_deaths 0: deaths as the page drew them before */
 if(noDeath&&(h.k==='die'||h.k==='kill'))return;
 if(h.k==='crit'||h.k==='save'||h.k==='flank'||h.k==='rear'||h.k==='turned'||h.k==='charge'||h.k==='rout'||h.k==='cover'||/^m-?\d$/.test(h.k))return;   /* words over it only (CombatSkills.dm, Wounds.dm, Facing.dm): no swing */
 if(h.k==='die'){if(G3G.killAt.has(tile)&&performance.now()-G3G.killAt.get(tile)<2500)return;const T=g3at(h.x,h.y);if(!T||!g3seen(T)||T.dead)return;
  const from=h.ax!==h.x||h.ay!==h.y?g3from(h):null;g3dying(T,tile,from).grace=4500;   /* it acts its death out first */
  if(T.g3ko){const d=typeof G3TOW!=='undefined'&&G3TOW.dieAsLies?rdLive(T):null;if(d&&!d.air){d.alive=false;d.rigid=true;d.held=false;d.asLies=true;T.g3ko=0}else rdStart(T,'fall',from);return}   /* dying where it lies out cold or dying (BleedOut.dm): it stays down as it lies, only dead now (the owner: the final animation frame is the final pose) */
  if(RDCAUSE[h.p]||DZDEF[h.p])rdDie(T,h.p,from);else rdStart(T,g3dieKind(h.p),from);return}
 if(h.k==='drop'){const p=String(h.p||'').split('|'),T=g3at(h.x,h.y);if(!T||!T.g3)return;const slot=p[1],tg={at:[+p[2],-(+p[3])],tile:[+p[2],+p[3]],key:p[4]};   /* where a dying unit's piece comes down (Gear3D.dm RmG3Drops) */
  (T.g3dropAt=T.g3dropAt||{})[slot]=tg;
  for(const b of RD.loose)if(b.doll&&b.doll.t===T&&b.held&&b.held.slot===slot&&!b.itemKey){b.itemKey=tg.key;b.tile=tg.tile;b.z=V3.terrain?V3.terrain.z:null;   /* already falling: steered onto its tile */
   if(!b.rest){const gy=rdGround(tg.at[0],tg.at[1]),vy=Math.max(0.6,b.V[1]),Tf=(vy+Math.sqrt(vy*vy+2*RDG*Math.max(0,b.X[1]-gy)))/RDG;b.V=[(tg.at[0]-b.X[0])/Tf,vy,(tg.at[1]-b.X[2])/Tf];b.aimed=true}}
  return}
 if(h.k==='limb'){const p=String(h.p||'').split('|'),T=g3at(h.x,h.y);if(!T||!T.g3||!g3seen(T))return;const part=/arm/i.test(p[1]||'')?'arm':'leg',side=/left/i.test(p[1]||'')?'L':'R',limbKey=p[4]||null,at=[+p[2],-(+p[3])];   /* a limb flung off (Gear3D.dm RmG3Limb): where the game's lies */
  if(T.dead||G3G.dead.some(D=>D.T===T&&!D.over)){T.g3maim=part;T.g3maimS=side;T.g3limbAt=at;T.g3limbKey=limbKey;return}   /* the killing blow took it: its fall takes it off (ragdoll.js rdKind) */
  const go=()=>{if(!T.dead)rdStart(T,part==='arm'?'armcut':'legcut',null,{limbAt:at,side,limbKey})};const w=(G3G.swingAt.get(T.key)||0)-performance.now();if(w>0)setTimeout(go,w);else go();return}
 if(h.k==='stagger'&&typeof h.p==='string'&&h.p.startsWith('knock|')){if(G3G.knocked.has(h.id))return;   /* played as it happened (g3knock3D) */const p=h.p.split('|'),dx=+p[1],dy=+p[2],n=+p[3],T=g3at(h.x,h.y);if(!T||!T.g3||!g3seen(T)||T.dead)return;   /* knocked back, alive (Hits.dm RmKnockBack, Golems.dm): from its old tile onto the new */
  const K={kind:p[4]||'flying',from:rdV.n([dx,0,-dy]),at:[h.x-dx*n,-(h.y-dy*n)],far:n*Math.hypot(dx,dy)},A=SK.acts.find(a=>a.target===T&&!a.replaced&&!a.hits&&a.D.hit);
  if(A){A.opt.knock=K;return}g3knockNow(T,K);return}   /* the blow that knocks it is still coming: it knocks it as it lands */
 const T=g3at(h.x,h.y);if(!T||!T.g3||!g3seen(T)||T.dead)return;   /* nothing more for the dead: their fall is theirs */
 const kill=h.k==='kill';if(kill){G3G.killAt.set(tile,performance.now());if(G3G.killAt.size>200)G3G.killAt.clear()}
 const mv=h.mv&&SK.defs[h.mv]?h.mv:null;   /* one of the game's weapon moves (Hits.dm "mv", WeaponSkills.dm) */
 if(mv&&SK.defs[mv].self){const U=g3at(h.ax,h.ay);if(U&&U.g3&&g3seen(U)&&!U.dead&&!SK.acts.some(A=>A.t===U&&A.skill===mv&&!A.replaced))skAct(U,mv,null,{});return}   /* a guard held, the dead raised: on itself */
 if(mv){const S=g3at(h.ax,h.ay);if(S&&SK.acts.some(A=>A.t===S&&A.skill===mv&&!A.replaced&&performance.now()/1000-A.t0<1.2))return}   /* its other blows (four stabs, a cleave's foes, a bolt's spark): one move */
 if(!mv&&(['bleed','burn','venom','chill','shock','drain','smite','astral','webbed','echo','wall','wreck'].includes(h.k)||(typeof h.k==='string'&&h.k[0]==='+')))return;   /* ticks and effects: no swing */
 if(!kill&&g3busy())return;
 const S=(h.ax!==h.x||h.ay!==h.y)?g3at(h.ax,h.ay):null,guard=kill?undefined:g3guard(h.k,T,h.n);
 if(kill){g3dying(T,tile,g3from(h));const L=T.g3ko&&typeof G3TOW!=='undefined'&&G3TOW.dieAsLies?rdLive(T):null;if(L&&!L.air){L.alive=false;L.rigid=true;L.held=false;L.asLies=true;T.g3ko=0}else{const d=rdTake(T);if(d){d.kind='pose';d.alive=true;d.muscle=1}}}   /* finished as it lay (Falls.dm's Lethal finisher): it keeps its pose; the striker's swing still plays */   /* it stands till the blow lands (g3rebind fells it if that blow never comes) */
 if(S&&S.g3&&g3seen(S)&&!S.dead){const w=S.g3.w||'',st=w.split(':')[0];
  const part=G3PT[h.pt],res=h.pt==='block'?'block':h.pt==='deflect'?'deflect':h.k==='miss'?'miss':'hit';   /* where the game says it struck (Combat - Bows.dm, Throwing.dm: Hits.dm "pt") */
  if(h.p==='arrow'&&st==='bow'){rdShoot(S,T,kill,{guard,part,res});h.g3shot=true;h.g3late=600+Math.hypot(h.x-h.ax,h.y-h.ay)*60;if(kill){const fr=g3from(h);setTimeout(()=>{const d=rdLive(T);if(d&&d.alive)rdStart(T,'fall',fr)},h.g3late+300)}return}
  if(h.p==='javelin'||h.p==='axe'){if(skAct(S,'throw',T,{kill,guard,part,weapon:h.p==='javelin'?'spear:iron':'hand axe:iron'})){h.g3shot=true;h.g3late=700+Math.hypot(h.x-h.ax,h.y-h.ay)*70;if(kill){const fr=g3from(h);setTimeout(()=>{const d=rdLive(T);if(d&&d.alive)rdStart(T,'fall',fr)},h.g3late+300)}}else if(kill)rdStart(T,g3death(h,S),g3from(h));return}   /* a kill by a throw falls all the same, as an arrow's does (the owner 10-28: dead left standing) */
  if(!h.p){const A=skAct(S,mv||g3move(S,kill),T,{kill,guard,weapon:w||undefined});if(A){h.g3swing=true;h.g3late=Math.round(((A.D.hit?A.D.hit[0]:0.3)+0.12)*1000/(RD.slow||1));G3G.swingAt.set(T.key,performance.now()+h.g3late);if(G3G.swingAt.size>300)G3G.swingAt.clear();
    if(kill){const fr=g3from(h);setTimeout(()=>{const d=rdLive(T);if(d&&d.alive)rdStart(T,'fall',fr)},h.g3late+120)}}   /* the swing taken over by its next one: it falls all the same */
   else if(kill)rdStart(T,g3death(h,S),g3from(h));return}}
 if(kill)rdStart(T,g3death(h,S),g3from(h));else if(!h.p&&!guard)rdStart(T,'flinch',g3from(h))}
// The game's body parts (CombatSkills.dm RmArrowRegion, Throwing.dm) as the page's (ragdoll.js rdAim).
const G3PT={LeftLeg:'legL',RightLeg:'legR',LeftArm:'armL',RightArm:'armR',Head:'head',LowerBody:'lower',UpperBody:'chest',Chest:'chest'};
// Knocked back by the game (it moved the unit): the doll launched from the tile it was on onto the one it is on now, and up.
function g3knockNow(T,K){const d=rdStart(T,K.kind,K.from,{live:true,at:K.at,far:K.far});if(d){d.tx=T.x;d.ty=T.y}return d}   /* its tile now, the server's: a doll it already had (a move) kept its old one, and g3rebind ends a doll whose unit has gone on from it */
// Thrown by a golem (Golems.dm RmGolemShowThrow): told the moment the server threw it, ahead of its new tile (move3D)
// and of the HUD's record of the blow (g3hit, which then leaves it), so the doll flies from the tile it stood on onto
// the one the server put it on, and its picture never jumps or slides there first. A row: its ref, its tile now, the
// way it went, tiles (0: pinned where it stood: up and down on the spot), the launch, the hit's id.
window.knock3D=function(raw){try{const L=JSON.parse(typeof raw==='string'?raw:JSON.stringify(raw));if(Array.isArray(L))for(const r of L)g3knock3D(r)}catch(e){console.error(e)}};
function g3knock3D(r){if(window.G3NODOLLS||typeof RD==='undefined'||!Array.isArray(r))return;const [ref,x,y,dx,dy,n,kind,id]=r;if(G3G.knocked.has(id))return;
 G3G.knocked.add(id);if(G3G.knocked.size>300)G3G.knocked=new Set([...G3G.knocked].slice(-150));
 const T=G3G.cur.get(ref);if(!T)return;const ox=x-dx*n,oy=y-dy*n;G3G.knockAt.set(T.key,{x,y,ox,oy,at:performance.now()});
 if(G3G.at.get(T.x+','+T.y)===T)G3G.at.delete(T.x+','+T.y);G3G.at.set(x+','+y,T);T.x=x;T.y=y;   /* where the server has it (its move3D says so next) */
 if(!RD.rig){rdLoad();return}if(!T.g3||T.dead||!g3seen(T))return;
 g3knockNow(T,{kind:kind||'flying',from:rdV.n([dx,0,-dy]),at:[ox,-oy],far:n*Math.hypot(dx,dy)})}
// A kill with no doll to strike it (a monster, a beast, one out of view): the fall its weapon gives (Hits.dm's classes);
// a dragon's flings it. A death the server names (Death.dm DeathType): its fall, a weapon move's own (WeaponSkills.dm).
function g3death(h,S){if(S&&S.beast&&S.beast.kind==='dragon')return 'throw';const w=h.w||'',r=Math.random();
 if(w==='axe')return r<0.4?'armoff':r<0.6?'legoff':'fall';if(w==='mace')return r<0.5?'flying':'hammer';if(w==='claws')return 'spin';if(w==='dagger')return 'crumple';if(w==='bow')return 'shot';if(w==='spear')return r<0.3?'flying':'fall';return 'fall'}
const G3DIES={'Smashed Head':'crumple','a blow to the head':'crumple','Head Mutalation':'crumple','Smashed':'flying','Sacrificed To Death':'crumple','Suicide':'crumple',
 'being shot in the lungs with arrows':'shot','being shot in the heart with an arrow':'shot','crashing to the ground':'fall'};
function g3dieKind(c){c=String(c||'');if(G3DIES[c])return G3DIES[c];const m=c.match(/^an? (.+)$/),D=m&&SK.defs[m[1].replace(/ /g,'')];
 if(D){const ds=D.deaths;return D.always||(ds?ds[Math.floor(Math.random()*ds.length)]:D.death)||'fall'}return 'fall'}
// The server's word on a unit, played on its doll: out cold (D["ko"]: down till it wakes), a bandaged stump (Stumps.dm:
// it stops bleeding), a load carried in (Jobs.dm: held before it as it walks, the doll going where the unit goes).
function g3state(t){
 if(t.ko!=null&&!t.g3ko&&!t.dead&&g3seen(t)&&!g3busy()){const dy=t.dying&&typeof G3TOW!=='undefined'&&G3TOW.dying,d=rdStart(t,dy?'fall':'ko',dy?g3blowFrom(t):null);if(d){if(dy)g3downDying(d);d.until=1e9;t.g3ko=1}}   /* down dying: the death fall, bleeding (g3downDying) */
 else if(t.ko==null&&t.g3ko){t.g3ko=0;const d=rdLive(t);if(d&&d.kind==='ko')d.until=d.age||0}   /* awake: it gets up */
 if(t.g3.band&&t.bleed&&t.bleed.on)rdBandage(t);
 g3carry(t)}
function g3carry(t){const k=t.g3.carry;
 if(!k||t.dead||t.ko!=null){if(t.g3cy){t.g3cy=0;if(typeof WK!=='undefined')WK.carry.delete(t);const d=rdLive(t);if(d&&d.alive&&d.kind==='pose'){rdStopActs(t);d.done=true;rdShow(t)}}return}
 if(t.g3cy===k&&t.g3cyd===t.dir&&rdLive(t))return;
 if(t.g3cy){const d=rdLive(t);if(d&&d.kind==='pose'){rdStopActs(t);d.done=true}}   /* turned, or another load: a fresh doll facing its way */
 if(!g3seen(t)||g3busy()||typeof wkLoad!=='function')return;t.g3cy=k;t.g3cyd=t.dir;
 skAct(t,'carry',null,{loop:true,fx:(d,dt,b,emit,A)=>{if(!d.wkBare){d.wkBare=true;skStow(d,true)}const x=(t.dx??t.x)+(t.px||0),z=-(t.dy??t.y)-(t.py||0);A.O0=[x,rdGround(x,z),z];WK.carry.set(t,{A,d,kind:k,at:wkLoad(d,emit,k)})}})}

// --- work and climbing -------------------------------------------------------------------------------------------
// As the server says (Gear3D.dm D["g3"].work: the job and the tile it works; View3D.dm D["climb"]): a unit in view at it
// plays the move with its tool in hand (work.js) till it stops; a climb is always seen from behind (wkShowBack), at the
// server's pace: its progress eased between updates, with a rope and pitons only for climbing gear (g3.cg).
const G3JOB={mine:'mine',chop:'woodchop',smith:'smith',build:'build',fish:'fish',spearfish:'spearfish',netfish:'netfish',pick:'pick',gather:'gather',till:'till',plant:'plant',harvest:'harvest'};
function g3jobs(t){const c=t.climb,now=performance.now()/1000;
 if(c&&Array.isArray(c)){
  if(!t.g3cl){if(t.g3wk){t.g3wk='';wkStop(t)}if(!g3seen(t)||g3busy())return;
   const up=!!c[4],foot=[c[5],0,-c[6]],H=(typeof v3peakTop==='function'&&v3peakTop(c[2],c[3]))||c[1]||2;foot[1]=rdGround(foot[0],foot[2]);t.g3cs={p:c[0],at:now,rate:1/Math.max(1.5,2+(c[1]||2))};
   const A=wkClimb(t,[c[2],0,-c[3]],H,5,up,{base:foot,face:0.38,lip:0.5,top:1,rope:!!t.g3.cg,prog:()=>{const S=t.g3cs;return S?S.p+(performance.now()/1000-S.at)*S.rate:1}});if(A)t.g3cl=1;return}
  const S=t.g3cs;if(S&&c[0]!==S.p){const dt=now-S.at;if(dt>0.05&&c[0]>S.p)S.rate=Math.min(1.5,(c[0]-S.p)/dt);S.p=c[0];S.at=now}return}
 if(t.g3cl){t.g3cl=0;t.g3cs=null;t.g3dir=0;wkStop(t);return}
 const w=t.g3.work,key=w?w.join(','):'';if(key===(t.g3wk||''))return;
 if(t.g3wk){t.g3wk='';wkStop(t)}
 if(!w||!g3seen(t)||g3busy())return;const job=G3JOB[w[0]];if(!job||!SK.defs[job])return;
 {const A=wkStart(t,job,[w[1],0,-w[2]]);if(A){t.g3wk=key;const f0=A.opt.fx;A.opt.fx=(d,dt,b,emit,A2)=>{if(t.dx!=null&&t.dy!=null){const x=t.dx+(t.px||0)+((t.iw||1)-1)/2,z=-t.dy-(t.py||0);A2.O0=[x,t.ly?A2.O0[1]:rdGround(x,z),z]}if(f0)f0(d,dt,b,emit,A2)}}}}   /* it works where it is drawn: on along the step it was finishing when the job came, on the ground there (as g3carry); up on a mountain at the height it was made at (hud-controls, 10-26) */

// --- the stone door --------------------------------------------------------------------------------------------------
// A stone door is the climbing stone's rock (meshes.py prop.cliff), exactly as the arena's cliff stands: no frame, the
// rough rock with its ledges at its own size (about 2 tiles tall, wider than the doorway, so it covers it whole); slid
// aside into the wall when open. Drawn into the page's object geometry (v3obj, kept per object) once the meshes are in; until
// then the page's own stone door.
function g3stoneDoor(a,t,X,Y,Z,rot,B,stone){const P=G3.ready&&G3.P['prop.cliff'];if(!P)return false;
 let bb=G3G.cliff;if(!bb){const p=P.pos;bb=[1e9,1e9,1e9,-1e9,-1e9,-1e9];for(let i=0;i<P.v*3;i+=3)for(let k=0;k<3;k++){bb[k]=Math.min(bb[k],p[i+k]);bb[k+3]=Math.max(bb[k+3],p[i+k])}G3G.cliff=bb}
 const W=rot?[0,0,1]:[1,0,0],T=rot?[1,0,0]:[0,0,-1],   /* turned, never mirrored (the faces keep their winding) */sc=0.0156/G3.q,sw=sc,sh=sc,st=sc,cols=g3cols('iron');   /* the arena's scale (work.js wkProp: a mesh pixel 1/64 tile; positions are G3.q finer) */
 const slide=t.open?-0.9:0,cx=(bb[0]+bb[3])/2,cz=(bb[2]+bb[5])/2,o=[X+W[0]*slide,Y+0.02,Z+W[2]*slide],p=P.pos,n=P.nrm,m=P.mat;
 // mesh x (into the rock) across the doorway, y up, z along it
 for(let i=0;i<P.v;i++){const j=i*3,u=(p[j+2]-cz)*sw,v=(p[j]-cx)*st,y=(p[j+1]-bb[1])*sh,nu=n[j+2]/127,nv=n[j]/127,ny=n[j+1]/127,c=cols[m[i]]||cols[0];
  a.v(o[0]+W[0]*u+T[0]*v,o[1]+y,o[2]+W[2]*u+T[2]*v,W[0]*nu+T[0]*nv,ny,W[2]*nu+T[2]*nv,0,0,c[0],c[1],c[2],1)}
 return true}

// --- towed: a body dragged, a downed unit carried --------------------------------------------------------------------
// The user (2026-10-26): "i wonder can the draging the body can it be like drag ragdoll? versus a teleport?", then "we
// drag them how it looks at its end state like we dont reset the asset to fit us". The server moves a dragged body
// (BodyDrag.dm) and a carried downed unit (TargetActions.dm, Surgery.dm) a tile at a time behind whoever pulls it, and
// the page drew it hopping there. Now, once it moves while it lies there, it is pulled along as it lies: a body as its
// kept pose (how its death left it), a downed unit as its out-cold doll, never remade or straightened. It follows on a
// rope behind the puller as the puller is drawn and turns with the pull round a corner. When the pulling stops (the
// puller stands, lets go, goes down or away, the level changes) it settles onto the tile the server has it on, and
// lies there turned as it came to rest. The one thing that slides: a body being pulled; a unit walking never eases off
// its tile. G3TOW.on false: as before.
const G3TOW={on:true,dieAsLies:true,dying:true,rope:0.95,pull:2.6,reach:1.75,still:1000};   /* on: pulled as it lies; dieAsLies: one dying where it lies keeps its pose (g3hit); dying: down dying falls as a death falls and bleeds (g3state); rope: puller's middle to its middle (tiles); pull: its fastest (tiles a second); reach: how far a puller may be from the tile; still: ms a puller stands before it lets it settle */
G3G.tows=new Map();   /* the towed thing's key -> {t, P (a body's kept pose) or d (a downed unit's doll), towerKey, Q (its middle: world x, z), h (the pull's way), a0, tx, ty, movedAt, settled} */
const g3n2=v=>{const l=Math.hypot(v[0],v[1])||1;return [v[0]/l,v[1]/l]};
// Who pulls it: of the units near its tile, the one where a puller would be (ahead of it, the way it moved).
function g3towPick(t,ox,oy){const px=t.x+(t.x-ox),py=t.y+(t.y-oy);let best=null,bs=1e9;
 for(const u of G3G.cur.values()){if(u===t||u.dead||u.g3ko||u.body)continue;const ux=u.dx??u.x,uy=u.dy??u.y;
  if(Math.max(Math.abs(ux-t.x),Math.abs(uy-t.y))>G3TOW.reach)continue;const s=Math.hypot(ux-px,uy-py);if(s<bs){bs=s;best=u}}return best}
// From where it lies (c: its middle, world x, z).
function g3towStart(t,ox,oy,c,P,d){const tw=g3towPick(t,ox,oy),T=tw?[tw.dx??tw.x,-(tw.dy??tw.y)]:[ox,-oy],h=g3n2([c[0]-T[0],c[1]-T[1]]);
 const W={t,P:P||null,d:d||null,towerKey:tw?tw.key:null,tp:tw?T:null,Q:[c[0],c[1]],h,a0:Math.atan2(h[1],h[0]),ad:0,tx:t.x,ty:t.y,movedAt:performance.now(),settled:0,last:performance.now()};
 if(d){d.tow=W;d.air=false;d.V=[0,0,0]}G3G.tows.set(t.key,W)}
// A kept pose's pictures where it is drawn now, as its own: a pull starts from there.
function g3towBake(P){if(P.ox||P.oz){P.cache=P.moved;P.cx+=P.ox;P.cz+=P.oz;P.x0+=P.ox;P.y0-=P.oz;P.ox=0;P.oz=0}P.g0=rdGround(P.cx,P.cz)}
// Each frame (g3poses): bodies and downed units the server moved start being pulled; the pulled follow their puller,
// are drawn where they are, and settle once nobody pulls.
function g3tows(){if(window.G3NODOLLS||typeof RD==='undefined')return;const now=performance.now();if(G3TOW.ring!==false)g3rings();if(G3TOW.dying)g3bleedDying(now);if(!G3TOW.on)return;
 for(const b of G3G.posed){if(G3G.tows.has(b.key))continue;const P=G3G.poses.get(b.key);if(!P)continue;
  if(P.tx==null){P.tx=Math.round(P.x0);P.ty=Math.round(P.y0)}
  if(b.x!==P.tx||b.y!==P.ty){g3towBake(P);P.moved=P.cache;g3towStart(b,P.tx,P.ty,[P.cx,P.cz],P,null)}}
 for(const d of RD.dolls){const t=d.t;if(d.tow||d.done||d.ghost||!d.alive||d.kind!=='ko'||d.air||!t||!t.g3ko||t.dead)continue;
  if(!d.towSeen){d.towSeen=[t.x,t.y];continue}const ox=d.towSeen[0],oy=d.towSeen[1];if(t.x===ox&&t.y===oy)continue;
  const B=rdBasis(d),p=rdW(d,B,d.pel[0],d.pel[1],0),moved=d.tx===t.x&&d.ty===t.y;   /* a scene may have moved its doll the tile already (g3rebind): from where it lay before that */
  if(moved){d.O=[d.O[0]-(t.x-ox),d.O[1],d.O[2]+(t.y-oy)];p[0]-=t.x-ox;p[2]+=t.y-oy}
  g3towStart(t,ox,oy,[p[0],p[2]],null,d)}
 for(const [k,W] of G3G.tows){const d=W.d,dt=Math.min(0.05,(now-W.last)/1000);W.last=now;
  if(!d){const b=G3G.posed.find(x=>x.key===k);if(b)W.t=b}const t=W.t;   /* a body comes as a new object with each scene: by its key */
  if(d?(d.done||t.dead||!t.g3ko):(!G3G.posed.includes(t)||G3G.poses.get(k)!==W.P)){g3towDone(k,W);continue}   /* taken up, buried, woken, dead: its own way now */
  if(t.x!==W.tx||t.y!==W.ty){const tw=g3towPick(t,W.tx,W.ty);if(tw)W.towerKey=tw.key;W.tx=t.x;W.ty=t.y;W.movedAt=now;W.settled=0}   /* a step on the server */
  let tw=W.towerKey!=null?G3G.cur.get(W.towerKey):null;if(tw&&(tw.dead||tw.g3ko||Math.max(Math.abs((tw.dx??tw.x)-t.x),Math.abs((tw.dy??tw.y)-t.y))>G3TOW.reach))tw=null;
  if(tw){const T=[tw.dx??tw.x,-(tw.dy??tw.y)];if(!W.tp||Math.hypot(T[0]-W.tp[0],T[1]-W.tp[1])>0.004)W.movedAt=now;W.tp=T}
  tw=tw&&now-W.movedAt<G3TOW.still?tw:null;   /* pulled while its puller moves; standing a second, it lets it settle */
  // its middle: on the rope behind the puller (taken up at a pull's pace, never snapped: a body hears of its step up to
  // half a second late), kept near the tile the server has it on; nobody pulling, eased onto that tile
  const C=[t.x,-t.y];let Q=W.Q;
  if(tw){const T=W.tp,vx=Q[0]-T[0],vz=Q[1]-T[1],L=Math.hypot(vx,vz);
   if(L>G3TOW.rope){const gx=T[0]+vx/L*G3TOW.rope-Q[0],gz=T[1]+vz/L*G3TOW.rope-Q[1],gl=Math.hypot(gx,gz),m=Math.min(gl,G3TOW.pull*dt)/(gl||1);Q=[Q[0]+gx*m,Q[1]+gz*m]}
   if(L>0.05){const k=Math.min(1,dt*4);W.h=g3n2([W.h[0]+(vx/L-W.h[0])*k,W.h[1]+(vz/L-W.h[1])*k])}
   const b=Math.min(1,dt*0.8);Q=[Q[0]+(C[0]-Q[0])*b,Q[1]+(C[1]-Q[1])*b]}
  else{const k=Math.min(1,dt*3);Q=[Q[0]+(C[0]-Q[0])*k,Q[1]+(C[1]-Q[1])*k]}
  const moved=Math.hypot(Q[0]-W.Q[0],Q[1]-W.Q[1]);W.Q=Q;
  // turned with the pull, as it lies: its look kept, only its way round the up axis
  let a=Math.atan2(W.h[1],W.h[0])-W.a0;while(a>Math.PI)a-=2*Math.PI;while(a<-Math.PI)a+=2*Math.PI;const da=a-W.ad;W.ad=a;
  if(W.P)g3towPose(W);else g3towDoll(W,da);
  W.settled=!tw&&Math.hypot(C[0]-Q[0],C[1]-Q[1])<0.03&&moved<0.002?W.settled+dt:0;
  if(W.settled>0.4)g3towDone(k,W)}}   /* at rest on its tile, lying as it came to rest */
// The pull over: a body keeps where and how it was drawn as its kept pose on its tile; a doll goes on as it lies.
function g3towDone(k,W){G3G.tows.delete(k);const t=W.t,d=W.d,Q=W.Q;
 if(W.P){const P=W.P;P.cache=P.moved;P.cx=Q[0];P.cz=Q[1];P.x0=t.x;P.y0=t.y;P.tx=t.x;P.ty=t.y;P.ox=0;P.oz=0;P.g0=rdGround(Q[0],Q[1]);P.a=0;P.qa=null}
 else if(!d.done){d.tow=null;d.tx=t.x;d.ty=t.y;d.towSeen=[t.x,t.y]}}
// A body: its kept pose's pictures turned about its middle and moved to where it is pulled to, drawn this frame. A cut
// limb that is an item on the ground (P.limbVerts: [tex, from, to] float ranges of P.cache) stays where it lies.
function g3towPose(W){const P=W.P,Q=W.Q,a=W.ad;
 if(P.a!==a||!P.qa||P.qa[0]!==Q[0]||P.qa[1]!==Q[1]){const c=Math.cos(a),s=Math.sin(a),oy=rdGround(Q[0],Q[1])-P.g0;P.a=a;P.qa=[Q[0],Q[1]];
  P.moved=P.cache.map(([tex,f])=>{const g=f.slice(),lv=P.limbVerts&&P.limbVerts.filter(r=>r[0]===tex);for(let i=0;i<g.length;i+=12){if(lv&&lv.some(r=>i>=r[1]&&i<r[2]))continue;const x=g[i]-P.cx,z=g[i+2]-P.cz,nx=g[i+3],nz=g[i+5];
   g[i]=Q[0]+x*c-z*s;g[i+1]+=oy;g[i+2]=Q[1]+x*s+z*c;g[i+3]=nx*c-nz*s;g[i+5]=nx*s+nz*c}return [tex,g]})}
 for(const [tex,f] of P.moved){let va=RD.va.get(tex);if(!va){va=new VA();RD.va.set(tex,va)}va.copy(f,0,f.length)}}
// A downed unit: its out-cold doll turned by the pull's turn, its middle where it is pulled to; its limbs as they lie.
function g3towDoll(W,da){const d=W.d,t=W.t;
 if(da){const c=Math.cos(da),s=Math.sin(da),r=v=>[v[0]*c-v[2]*s,v[1],v[0]*s+v[2]*c];d.R=r(d.R);d.Uy=r(d.Uy);d.N=r(d.N)}
 const p=rdW(d,rdBasis(d),d.pel[0],d.pel[1],0),gy=rdGround(W.Q[0],W.Q[1])-rdGround(p[0],p[2]);
 d.O=[d.O[0]+W.Q[0]-p[0],d.O[1]+gy,d.O[2]+W.Q[1]-p[2]];d.tx=t.x;d.ty=t.y}
// --- down dying ------------------------------------------------------------------------------------------------------
// Falls (the owner: "any unit brought down falls dying, with the death fall and blood, and has 60 s to be saved"): the
// server sends a unit down dying as D["dying"] beside its seconds (View3D.dm). It falls as a death falls, limp, and lies
// bleeding, a pool spreading under it, the page's "Bleeding out" words over it (no Zzz). That fall's last frame is its
// pose while it bleeds, is carried or dragged, saved or dies (the owner's rule). Saved, it gets up from there as from a
// knock-out (g3state). A knock-out from a Non-lethal blow slumps as before. G3TOW.dying false: it slumps as a knock-out.
function g3downDying(d){d.alive=true;d.kind='ko';d.muscle=0.12;d.until=1e9;d.dying=1;g3fallTurn(d,d.t)}   /* rdKind's fall, but alive: it can be saved */
function g3bleedDying(now){for(const d of RD.dolls){if(!d.dying||d.done||!d.alive)continue;const t=d.t;if(!t||t.dead||!t.dying){d.dying=0;continue}   /* saved, or dead: no more */g3fallTurnStep(d);   /* away from the blow as it falls */
 if(!d.landed||RDNOBLOOD.has(t.g3&&t.g3.sheet))continue;const p=rdW(d,rdBasis(d),d.pel[0],d.pel[1],0);
 if(d.dying===1){d.dying=2;d.dripAt=now;rdBlood(p,[0,-0.4,0],24,true)}   /* where it fell: a pool */
 else if(now-d.dripAt>1800){d.dripAt=now;rdBlood(p,[0,-0.2,0],4,true)}}}   /* and it goes on bleeding */
// --- falling away from the blow ---------------------------------------------------------------------------------------
// The user (2026-10-26): "make down-dying units fall away from the blow that dropped them". The last blow on each unit
// (where it came from: the page's hit records, g3hit) is kept a few seconds; a unit going down dying falls from it, as a
// death falls, and turns as it goes, so that it comes to lie with its head away from the striker; with no blow known
// (an old wound bled it out), a way of its own. Its limbs still fall as they will. That fall's last frame stays its pose.
G3G.blows=new Map();   /* a unit's key -> {from: the blow's way (world x, 0, z), at} */
{const g0=g3hit;g3hit=function(h){try{if(h&&h.k!=='die'&&(h.ax!==h.x||h.ay!==h.y)){const T=g3at(h.x,h.y);if(T&&T.key!=null){G3G.blows.delete(T.key);G3G.blows.set(T.key,{from:g3from(h),at:performance.now()});if(G3G.blows.size>300)G3G.blows.delete(G3G.blows.keys().next().value)}}}catch(e){}return g0(h)}}
function g3blowFrom(t){const b=t&&G3G.blows.get(t.key);return b&&performance.now()-b.at<5000?b.from:null}
// Where its head will lie (the fall tips it one way: Uy turned flat), and the turn that puts it away from the blow.
function g3fallTurn(d,t){const f=g3blowFrom(t),s=Math.sign(d.om)||1,H0=Math.atan2(-s*d.N[2],-s*d.N[0]),T=f?Math.atan2(f[2],f[0]):H0+(Math.random()*2-1)*Math.PI;
 let a=T-H0;while(a>Math.PI)a-=2*Math.PI;while(a<-Math.PI)a+=2*Math.PI;d.turnTo=a;d.turned=0;d.phiTo=0}   /* no twist in its plane: the turn alone sets its way */
// Each frame while it falls: turned as far as it has tipped, all the way once it lies.
function g3fallTurnStep(d){if(d.turnTo==null)return;const want=d.landed?d.turnTo:d.turnTo*Math.min(1,Math.abs(d.th)/(Math.PI/2)),da=want-d.turned;
 if(da){const c=Math.cos(da),s=Math.sin(da),r=v=>[v[0]*c-v[2]*s,v[1],v[0]*s+v[2]*c];d.R=r(d.R);d.Uy=r(d.Uy);d.N=r(d.N);d.turned=want}if(d.landed)d.turnTo=null}
// --- a downed unit's ring round its body --------------------------------------------------------------------------------
// The owner (10-26): "the circle was still in the center of the tile versus circling that piece of thing on the ground".
// A unit lying as its doll (out cold, down dying, carried) has its ring, bar, words and click spot where its body lies (its
// hips), not on its tile: the page draws them at t.g3ring (remastered.html), set here each frame; going down, they go
// with the fall, and back up, they come back to it. G3TOW.ring false: on its tile, as before.
function g3rings(){const seen=new Set();
 for(const d of RD.dolls){const t=d.t;if(!t||d.done||d.ghost||!d.alive||d.kind!=='ko'||t.dead||t.dx==null)continue;
  const p=rdW(d,rdBasis(d),d.pel[0],d.pel[1],0),k=d.tow?1:Math.min(1,Math.abs(d.th)/(Math.PI/2)),X=t.dx+(p[0]-t.dx)*k,Z=-t.dy+(p[2]+t.dy)*k;
  t.g3ring=[X,Z];t.g3pc=[X,Z];seen.add(t)}
 for(const t of G3G.ringed||[])if(!seen.has(t)){delete t.g3ring;delete t.g3pc}
 G3G.ringed=seen}
