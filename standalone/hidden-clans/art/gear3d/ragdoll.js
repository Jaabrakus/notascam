// Ragdolls for sprite units (art/gear3d; the animation arena). A unit that falls, flies or flinches becomes a flat 2D
// doll cut from its own picture (parts.py: head, torso, two arms, two legs, each with its joint): the doll's plane
// (the picture's, when it went) moves through 3D, tipping over, flying, spinning and landing flat, while the limbs
// and head swing in it on their joints (loose pendulums with gravity along the plane, held to their pose while the
// unit lives). Seen from its back the doll shows the unit's back picture. The unit's 3D pieces (gear3d.js) ride on
// the part that holds them, and come loose as real 3D pieces that fall, bounce and settle flat. Arrows fly on an arc
// and stay in what they hit. Units are in tiles, time in seconds.
const RD={rig:null,busy:0,dolls:[],loose:[],arrows:[],shots:[],va:new Map(),cen:new Map(),fx:[],acts:[]};   /* fx: blood, sparks, dust, trails (skills.js) */
// races that don't bleed: a vampire (never), bones, stone
const RDNOBLOOD=new Set(['Vampire','Skeleton','Gargoyle']);
const RDG=7.5;   /* gravity, tiles a second a second (a unit is about a tile tall) */
const RDBACK={S:'N',N:'S',E:'W',W:'E'},RDPARTS=['head','torso','armRu','armRl','armLu','armLl','legRu','legRl','legLu','legLl'];   /* parts.py's cells, in order */
// the swinging parts, parents first (a forearm hangs from its upper arm's elbow, a shin from its thigh's knee); a hidden
// limb borrows its mirror's pixels
const RDLIMBS=['armRu','armRl','armLu','armLl','legRu','legRl','legLu','legLl','head'],RDPARENT={armRl:'armRu',armLl:'armLu',legRl:'legRu',legLl:'legLu'},
 RDMIRROR={armRu:'armLu',armRl:'armLl',armLu:'armRu',armLl:'armRl',legRu:'legLu',legRl:'legLl',legLu:'legRu',legLl:'legRl'};
function rdLoad(){if(RD.busy||performance.now()<(RD.waitTil||0))return;RD.busy=1;fetch('g3rig.json').then(r=>{if(!r.ok)throw r.status;return r.json()}).then(d=>{RD.rig=d}).catch(()=>{RD.busy=0;RD.wait=Math.min(60000,(RD.wait||2500)*2);RD.waitTil=performance.now()+RD.wait})}   /* not there yet: asked again after 5 s, then less often */
const rdV={add:(a,b)=>[a[0]+b[0],a[1]+b[1],a[2]+b[2]],sub:(a,b)=>[a[0]-b[0],a[1]-b[1],a[2]-b[2]],mul:(a,k)=>[a[0]*k,a[1]*k,a[2]*k],dot:(a,b)=>a[0]*b[0]+a[1]*b[1]+a[2]*b[2],
 cross:(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]],n:v=>{const l=Math.hypot(v[0],v[1],v[2])||1;return [v[0]/l,v[1]/l,v[2]/l]}};
// quaternions [x, y, z, w]
const rdQ={mul:(a,b)=>[a[3]*b[0]+a[0]*b[3]+a[1]*b[2]-a[2]*b[1],a[3]*b[1]-a[0]*b[2]+a[1]*b[3]+a[2]*b[0],a[3]*b[2]+a[0]*b[1]-a[1]*b[0]+a[2]*b[3],a[3]*b[3]-a[0]*b[0]-a[1]*b[1]-a[2]*b[2]],
 rot:(q,v)=>{const u=[q[0],q[1],q[2]],t=rdV.mul(rdV.cross(u,v),2);return rdV.add(rdV.add(v,rdV.mul(t,q[3])),rdV.cross(u,t))},
 axis:(ax,an)=>{const s=Math.sin(an/2);return [ax[0]*s,ax[1]*s,ax[2]*s,Math.cos(an/2)]},nrm:q=>{const l=Math.hypot(q[0],q[1],q[2],q[3])||1;return [q[0]/l,q[1]/l,q[2]/l,q[3]/l]},
 slerp:(a,b,k)=>{let d=a[0]*b[0]+a[1]*b[1]+a[2]*b[2]+a[3]*b[3];if(d<0){b=[-b[0],-b[1],-b[2],-b[3]];d=-d}if(d>0.9995)return rdQ.nrm([a[0]+(b[0]-a[0])*k,a[1]+(b[1]-a[1])*k,a[2]+(b[2]-a[2])*k,a[3]+(b[3]-a[3])*k]);const th=Math.acos(d),s=Math.sin(th),p=Math.sin((1-k)*th)/s,q=Math.sin(k*th)/s;return [a[0]*p+b[0]*q,a[1]*p+b[1]*q,a[2]*p+b[2]*q,a[3]*p+b[3]*q]}};
function rdGround(X,Z){try{return v3groundAt(X,-Z)}catch(e){return 0}}

// Where a held piece is and how it is turned right now, as gear3d.js's live path places it: {name, tier, o, X, Y, Z, s}.
function rdPose(t,slot){const L0=t.g3last,g=t.g3,A=G3.A&&G3.A[g.sheet];if(!L0||!A||!g[slot])return null;const [st,tier]=g3split(g[slot]);
 const R=L0.R,LV=L0.L,face=L0.face,V=(A.views['SNEW'[face]]||A.views.S)[L0.fi<3?L0.fi:0],loc=A.loc,k=2*L0.hw/64;
 const Nc=rdV.cross(R,LV),Vh=rdV.n([Nc[0],0,Nc[2]]),Fv=face===1?rdV.mul(Vh,-1):face===2?[R[0],0,R[2]]:face===3?[-R[0],0,-R[2]]:Vh;
 const dd=t.dir||2,Ft=rdV.n([((dd&4)?1:0)-((dd&8)?1:0),0,((dd&2)?1:0)-((dd&1)?1:0)]);const del=Math.max(-1.6,Math.min(1.6,Math.atan2(Fv[2]*Ft[0]-Fv[0]*Ft[2],Fv[0]*Ft[0]+Fv[2]*Ft[2])));
 const turn=kf=>{const a=del*kf,c=Math.cos(a),s=Math.sin(a),F=[Fv[0]*c+Fv[2]*s,0,-Fv[0]*s+Fv[2]*c];return [F,[-F[2],0,F[0]]]};
 const card=(px,py,dpx)=>{const u=1-py/64,a=L0.hw*(2*px/64-1);return [L0.LX+R[0]*a+LV[0]*L0.sh*u+Nc[0]*dpx*k,L0.yA+R[1]*a+LV[1]*L0.sh*u+Nc[1]*dpx*k,L0.LZ+R[2]*a+LV[2]*L0.sh*u+Nc[2]*dpx*k]};
 const U=[0,1,0];
 if(slot==='h'){const [F,Rt]=turn(0.3),H=V.head,sx=loc.headw/11.5,sz=loc.headd/9.5;return {name:'helmet.'+st,tier,o:card((H.l+H.r)/2,H.top+10.5*sx,1),X:rdV.mul(Rt,-1),Y:U,Z:F,s:k*(sx+sz)/2}}
 if(slot==='s'){const [F,Rt]=turn(0.6),Z=rdV.n([F[0]-Rt[0],0,F[2]-Rt[2]]),X=rdV.cross(U,Z),sc=k*(A.scale||1);const o=card(V.shield[0],V.shield[1],face===2?-6:face===1?-3:2.2);return {name:'shield.'+st,tier,o:rdV.add(o,rdV.mul(Z,1.3*sc)),X,Y:U,Z,s:sc}}
 const [F,Rt]=turn(1),a=G3.rest[st]||[0.58,0.59,0.57],Aw=rdV.n([Rt[0]*a[0]+F[0]*a[1],a[2],Rt[2]*a[0]+F[2]*a[1]]);
 const e0=st==='bow'?F:[F[0]*0.8+Rt[0]*0.6,0,F[2]*0.8+Rt[2]*0.6],ed=rdV.dot(e0,Aw),Ew=rdV.n(rdV.sub(e0,rdV.mul(Aw,ed))),Nw=rdV.cross(Aw,Ew),sc=k*(A.scale||1);
 return {name:'weapon.'+st,tier,o:card(V.hand[0],V.hand[1],face===3?-6:face===1?-2.8*(A.scale||1):2.8*(A.scale||1)),X:Aw,Y:Ew,Z:Nw,s:sc}}
function rdQuat(X,Y,Z){return g3quat(X,Y,Z)}

// A doll from a unit (its last picture, t.g3last): the parts in the plane (tiles, x along the camera's right, y up from
// the feet), the skeleton (pelvis and angle; each limb a root on the torso and a tip that swings), and the gear on it.
function rdMake(t){const L0=t.g3last;if(!L0||!RD.rig)return null;if(t.dx!=null&&t.dy!=null){L0.LX=t.dx+(t.px||0)+((t.iw||1)-1)/2;L0.LZ=-t.dy-(t.py||0)}   /* where it is drawn now: a walking or still unit's picture is kept records, not redrawn */const RR=typeof rdRigOf==='function'?rdRigOf(t):null;if(!RR)return null;const rig=RR.rig,idx=RR.idx;   /* its parts (game.js: cut from its own picture, or the arena's lineup) */
 const fl='SNEW'[L0.face]||'S',bl=RDBACK[fl],k=2*L0.hw/64,R=[L0.R[0],L0.R[1],L0.R[2]],Uy=[L0.L[0],L0.L[1],L0.L[2]],N=rdV.cross(R,Uy);
 const P=(px,py,flip)=>[(flip?32-px:px-32)*k,(64-py)*k];
 const hc=q=>q&&q.box?[(q.box[0]+q.box[2])/2,(q.box[1]+q.box[3])/2]:null;   /* the head's middle: its tip */
 const sets={};for(const [side,f0,flip] of [['f',fl,false],['b',bl,true]]){const f=rig[f0]?f0:fl,r=rig[f],o={};   /* no back picture yet (game.js): the front turned over */for(const p of RDPARTS){let q=r[p],src=q,borrow=false;
   if(q&&!q.box&&RDMIRROR[p]&&r[RDMIRROR[p]]&&r[RDMIRROR[p]].box){src=r[RDMIRROR[p]];borrow=true}   /* hidden behind the body: its mirror's pixels, drawn behind */
   if(!q||!src||!src.box)continue;const sr=src.root,st=src.tip||(p==='head'?hc(src):null);
   o[p]={box:src.box,flip,tex:RR.tex[f],cell:RDPARTS.indexOf(borrow?RDMIRROR[p]:p),borrow,rootP:sr?P(sr[0],sr[1],flip):null,rest:sr&&st?Math.atan2(P(st[0],st[1],flip)[1]-P(sr[0],sr[1],flip)[1],P(st[0],st[1],flip)[0]-P(sr[0],sr[1],flip)[0]):null}}sets[side]=o}
 const RF=rig[fl],pel=RF.torso&&RF.torso.root?P(RF.torso.root[0],RF.torso.root[1],false):[0,0.45];
 // the skeleton, from the picture it went in: each limb's joint and tip, a forearm's joint its upper arm's tip
 const limbs={};for(const p of RDLIMBS){const q=RF[p];if(!q)continue;const r=q.root,tp=q.tip||(p==='head'?hc(q):null);if(!r||!tp)continue;const root0=P(r[0],r[1],false),tip0=P(tp[0],tp[1],false);
  limbs[p]={root0,tip0,tip:[...tip0],prev:[...tip0],len:Math.hypot(tip0[0]-root0[0],tip0[1]-root0[1])||0.01,parent:RDPARENT[p]&&RF[RDPARENT[p]]?RDPARENT[p]:null,pose:null}}
 for(const s of ['f','b']){const q=sets[s].torso;if(q&&!q.rootP)q.rootP=pel}
 // a limb it lost is gone from every doll it makes after (its stump at that limb's joint)
 const stumps=[];if(t.maimed)for(const p of t.maimed){if(!RDPARENT[p]&&RF[p]&&RF[p].root)stumps.push(P(RF[p].root[0],RF[p].root[1],false));delete limbs[p];for(const s of ['f','b'])delete sets[s][p]}
 const d={t,idx,tx:t.x,ty:t.y,fl,bl,k,R,Uy,N,O:[L0.LX,L0.yA,L0.LZ],V:[0,0,0],th:0,om:0,phi:0,pom:0,pel0:[...pel],pel:[...pel],limbs,sets,muscle:1,t0:performance.now()/1000,kind:'',air:false,landed:false,done:false,gear:[],alive:false,until:0,crouch:0,phiTo:null,col:1,stumps};
 // the gear rides on its part: kept as its pose in that part's frame (plane coordinates, turned with the part)
 const PQ=t.g3p,fr=PQ&&G3.pix?g3frame(R,Uy):null;   /* the unit's pieces as pictures (gear3d.js pixel mode): drawn on the doll as they were on the unit */
 for(const [slot,part,k3] of [['w',limbs.armRl?'armRl':'armRu',0],['s',limbs.armLl?'armLl':'armLu',1],['h','head',2]]){const g=rdPose(t,slot);if(!g)continue;const a=rdAttach(d,g,part);a.slot=slot;a.wrist=0;a.aw0=Math.atan2(a.X[1],a.X[0]);
  const q=PQ&&PQ[slot];if(q&&fr){a.card={tex:q.tex[0],C:q.P.poses[0],i:fr.ix[(L0.face*16+((t.dir||2)&15))*3+k3],nf:G3.pix.facings}}d.gear.push(a)}
 for(const a of RD.arrows)if(a.unit===t&&a.state==='unit'){rdArrowOnUnit(a);a.state='doll';a.doll=d;rdAttachArrow(d,a,a.dpart)}
 return d}
// The doll's plane in the world now: a plane point (x, y) and an offset n along its face.
function rdBasis(d){const c=Math.cos(d.th),s=Math.sin(d.th);return {Ux:d.R,Uy:rdV.sub(rdV.mul(d.Uy,c),rdV.mul(d.N,s)),Nn:rdV.add(rdV.mul(d.N,c),rdV.mul(d.Uy,s))}}
function rdW(d,B,x,y,n){if(d.squash!=null&&d.squash<1){const q=d.squash;y*=q;x*=1+(1-q)*0.7}return [d.O[0]+B.Ux[0]*x+B.Uy[0]*y+B.Nn[0]*n,d.O[1]+B.Ux[1]*x+B.Uy[1]*y+B.Nn[1]*n,d.O[2]+B.Ux[2]*x+B.Uy[2]*y+B.Nn[2]*n]}
// A part's frame: its joint in the plane and how far it has turned from its rest.
function rdPartFrame(d,part){if(part==='torso'){return {root:d.pel,ang:d.phi,root0:d.pel0,abs:null}}const L=d.limbs[part];if(!L)return {root:d.pel,ang:d.phi,root0:d.pel0,abs:null};
 const rr=rdRootNow(d,L),abs=Math.atan2(L.tip[1]-rr[1],L.tip[0]-rr[0]);return {root:rr,ang:abs-Math.atan2(L.tip0[1]-L.root0[1],L.tip0[0]-L.root0[0]),root0:L.root0,abs}}
function rdRootNow(d,L){if(L.parent&&d.limbs[L.parent])return d.limbs[L.parent].tip;const c=Math.cos(d.phi),s=Math.sin(d.phi),x=L.root0[0]-d.pel0[0],y=L.root0[1]-d.pel0[1];return [d.pel[0]+x*c-y*s,d.pel[1]+x*s+y*c]}
// how far a limb has turned from its rest (a forearm's rest pose follows its upper arm)
function rdTurned(d,L){const r=rdRootNow(d,L);return Math.atan2(L.tip[1]-r[1],L.tip[0]-r[0])-Math.atan2(L.tip0[1]-L.root0[1],L.tip0[0]-L.root0[0])}
// a world pose into a part's frame (x, y in the plane from the joint, unturned; n out of it) and back
function rdAttach(d,g,part){const B=rdBasis(d),f=rdPartFrame(d,part),rel=rdV.sub(g.o,rdW(d,B,f.root[0],f.root[1],0));
 const lx=rdV.dot(rel,B.Ux),ly=rdV.dot(rel,B.Uy),ln=rdV.dot(rel,B.Nn),c=Math.cos(-f.ang),s=Math.sin(-f.ang);
 const toL=v=>{const x=rdV.dot(v,B.Ux),y=rdV.dot(v,B.Uy),n=rdV.dot(v,B.Nn);return [x*c-y*s,x*s+y*c,n]};
 return {name:g.name,tier:g.tier,s:g.s,part,p:[lx*c-ly*s,lx*s+ly*c,ln],X:toL(g.X),Y:toL(g.Y),Z:toL(g.Z)}}
function rdGearWorld(d,a){const r0=rdGearWorld0(d,a);if(!a.aim3)return r0;   /* aimed into the depth (skills.js): its own direction, a little toward the target */
 const k=a.aimK||1,X0=rdV.n(r0.X),X=rdV.n(rdV.add(rdV.mul(X0,1-k),rdV.mul(a.aim3,k))),Z=rdV.n(rdV.cross(X,Math.abs(X[1])>0.95?[1,0,0]:[0,1,0])),Y=rdV.cross(Z,X),L=rdV.dot(r0.X,r0.X)**0.5||1;
 return {o:rdV.add(r0.o,a.aimOff||[0,0,0]),X:rdV.mul(X,L),Y:rdV.mul(Y,L),Z:rdV.mul(Z,L)}}
function rdGearWorld0(d,a){const B=rdBasis(d),f=rdPartFrame(d,a.part),an=f.ang+(a.wrist||0),c=Math.cos(an),s=Math.sin(an);
 const fromL=v=>{const x=v[0]*c-v[1]*s,y=v[0]*s+v[1]*c;return rdV.add(rdV.add(rdV.mul(B.Ux,x),rdV.mul(B.Uy,y)),rdV.mul(B.Nn,v[2]))};
 const fc=Math.cos(f.ang),fs=Math.sin(f.ang),px=a.p[0]*fc-a.p[1]*fs,py=a.p[0]*fs+a.p[1]*fc,r=rdW(d,B,f.root[0],f.root[1],0);   /* the grip stays where the part holds it; the wrist turns the piece about it */
 return {o:rdV.add(r,rdV.add(rdV.add(rdV.mul(B.Ux,px),rdV.mul(B.Uy,py)),rdV.mul(B.Nn,a.p[2]))),X:fromL(a.X),Y:fromL(a.Y),Z:fromL(a.Z)}}
// Let a piece go: a free body with the part's motion now, plus a push.
function rdDrop(d,a,push){const w=rdGearWorld(d,a),q=rdQuat(rdV.n(w.X),rdV.n(w.Y),rdV.n(w.Z));const P=G3.P[a.name];let c=RD.cen.get(a.name);
 if(!c&&P){let mn=[1e9,1e9,1e9],mx=[-1e9,-1e9,-1e9];for(let i=0;i<P.v;i++)for(let j=0;j<3;j++){const v=P.pos[i*3+j]/G3.q;if(v<mn[j])mn[j]=v;if(v>mx[j])mx[j]=v}c={c:[(mn[0]+mx[0])/2,(mn[1]+mx[1])/2,(mn[2]+mx[2])/2],r:Math.max(mx[2]-mn[2],0.8)/2};RD.cen.set(a.name,c)}
 const cc=c?c.c:[0,0,0],X=rdV.add(w.o,rdQ.rot(q,rdV.mul(cc,a.s)));
 const spin=a.name.startsWith('weapon')?7:a.name.startsWith('helmet')?5:3;
 const tg=d.t&&d.t.g3dropAt&&d.t.g3dropAt[a.slot];let V=push;   /* the game said where this one comes down (Gear3D.dm RmG3Drops): thrown onto that tile */
 if(tg){const jx=(Math.random()-0.5)*0.4,jz=(Math.random()-0.5)*0.4,gy=rdGround(tg.at[0]+jx,tg.at[1]+jz),vy=2.4,Tf=(vy+Math.sqrt(vy*vy+2*RDG*Math.max(0,X[1]-gy)))/RDG;V=[(tg.at[0]+jx-X[0])/Tf,vy,(tg.at[1]+jz-X[2])/Tf]}
 RD.loose.push({aimed:!!tg,itemKey:tg?tg.key:null,tile:tg?tg.tile:null,z:tg&&V3.terrain?V3.terrain.z:null,name:a.name,tier:a.tier,s:a.s,c:cc,r:(c?c.r:0.5)*a.s+0.005,X,V,q,w:[(Math.random()-0.5)*spin,(Math.random()-0.5)*spin,(Math.random()-0.5)*spin],rest:false,flat:a.name.startsWith('helmet')?1:2,bounce:0,doll:d,part:a.part,held:a});
 d.gear.splice(d.gear.indexOf(a),1)}

// Start an animation on a unit. kind: fall, crumple, spin, shot, flying (a heavy blow), hammer (thrown a few tiles),
// throw (a dragon's: high and far), armoff, legoff, ko (out cold, then up), flinch. from: the blow's way, a world
// unit vector (from the striker toward the unit), level.
// opt.live: a launch (hammer, throw, knock-back) it lives through: it flies, lands, lies a moment and gets up where
// it came down, its weapons still in its hands. armcut and legcut: a limb taken by a blow that doesn't kill: it
// staggers and fights on without it (a leg lost, on the other one); the stump bleeds (RD.bleedOut) till bandaged.
function rdStart(t,kind,from,opt){opt=opt||{};if(!RD.rig){rdLoad();return null}
 if(typeof wkInterrupt==='function')wkInterrupt(t,from);   /* struck while carrying: it drops it (work.js) */
 // one doll a unit: struck in the middle of a move it is jolted and goes on; killed, thrown or knocked out, the move
 // stops and it falls from wherever it is
 const cur=rdLive(t);if(cur&&cur.asLies)return cur;   /* died as it lay (game.js g3hit, G3TOW.dieAsLies): nothing moves it now */
 if(t.dead&&(kind==='flinch'||opt.live))return cur;   /* dead: a blow's flinch or a knock timed before it fell (skills.js, game.js opt.knock) leaves its fall be */
 if(cur&&cur.alive&&kind==='flinch'&&cur.kind==='pose'&&typeof SK!=='undefined'&&SK.acts.some(A=>A.t===t&&!A.replaced)){cur.jolt={t:performance.now()/1000,k:-(rdV.dot(from||[0,0,1],cur.R)>=0?1:-1)*0.12};return cur}   /* rocked a little, away from the blow */
 if(cur&&!cur.done&&(cur.live||(cur.cut&&cur.alive))&&kind==='flinch')return cur;   /* knocked flying: the blow's flinch doesn't stop it */
 // down and lying (out cold, bleeding out; the owner, 10-26: the final pose holds for the bleeding and the dragging): a blow
 // jolts it where it lies and a limb comes off where it lies; a death falls as before (die-in-place: g3hit, G3TOW.dieAsLies)
 if(cur&&cur.alive&&cur.kind==='ko'&&cur.landed&&!opt.live&&typeof G3G!=='undefined'&&G3G.game){
  if(kind==='ko')return cur;
  if(kind==='flinch'){for(const L of Object.values(cur.limbs))L.prev=[L.tip[0]-0.004,L.tip[1]];return cur}
  if((kind==='armcut'||kind==='legcut')&&!cur.cut){const keep={th:cur.th,om:cur.om,phi:cur.phi,phiTo:cur.phiTo,pom:cur.pom,until:cur.until,t0:cur.t0,crouchTo:cur.crouchTo,delay:cur.delay};rdKind(cur,kind,from,opt);Object.assign(cur,keep);cur.kind='ko';cur.alive=true;cur.landed=true;return cur}
  if(cur.cut)cur.kind='maimed';   /* anything else (a death, a second limb): as a maimed doll's, its lost limb left lying (rdRetire) */
 }
 if(cur&&!cur.cut){rdStopActs(t);rdKind(cur,kind,from,opt);return cur}
 // lying wounded (a leg lost): a blow jolts it where it lies, or kills it there
 const w=RD.dolls.find(x=>x.t===t&&!x.done&&!x.ghost&&x.kind==='wounded');
 if(w){if(kind==='flinch'){for(const L of Object.values(w.limbs))L.prev=[L.tip[0]-0.004,L.tip[1]];return w}w.alive=false;if(t.bleed)t.bleed.on=false;for(const a of [...w.gear])rdDrop(w,a,[0,0.4,0]);return w}
 rdRetire(t);
 const d=rdMake(t);if(!d)return null;rdKind(d,kind,from,opt);
 // the unit's own picture goes for now (the arena brings it back for a flinch or when out cold ends)
 rdHide(t);RD.dolls.push(d);return d}
// A doll set going as a kind, from however it is now (a fresh doll, or one in the middle of a move: a unit dying of
// something acts it out first, then falls from where it is). The new falls: stiff (frozen, struck by lightning: it
// tips over like a plank, its limbs held), melt (it sinks into a puddle), heap (bones: it drops where it stands),
// liedown (old age: it sinks down and lies down slowly).
function rdKind(d,kind,from,opt){opt=opt||{};from=from||[0,0,1];const t=d.t;
 if(t.g3maim&&!opt.live&&['fall','crumple','spin','flying','hammer','throw','shot','stiff'].includes(kind)){kind=t.g3maim==='arm'?'armoff':'legoff';opt={...opt,limbAt:opt.limbAt||t.g3limbAt,limbKey:opt.limbKey||t.g3limbKey};t.g3maim=null}   /* the game took a limb with the killing blow (Gear3D.dm RmG3Limb): off it comes as it dies */d.kind=kind;d.from=from;const now=performance.now()/1000;d.t0=now;d.done=false;d.tilt=null;d.armsBehind=false;d.armsFront=null;
 if(!d.alive||kind!=='pose')for(const L of Object.values(d.limbs))L.pose=null;
 const B=rdBasis(d),toward=rdV.dot(from,B.Nn),side=rdV.dot(from,B.Ux);   /* the blow along the plane's face (toward the camera +) and across it */
 const away=toward>0?-1:1;   /* the plane tips away from the blow: + is the top going away from the camera */
 const live=!!opt.live&&(kind==='flying'||kind==='hammer'||kind==='throw');d.rigid=false;d.gentle=false;
 if(kind==='stiff'){kind='fall';d.kind='fall';d.rigid=true}   /* falls as a fall, its limbs held as they are */
 d.alive=kind==='flinch'||kind==='ko'||kind==='armcut'||kind==='legcut'||live;d.live=live;d.muscle=1;
 const kick=(k)=>{for(const L of Object.values(d.limbs)){L.prev=[L.tip[0]-side*k*(0.4+Math.random()*0.6)*0.016,L.tip[1]-k*0.3*0.016*Math.random()]}};
 if(kind==='fall'&&d.rigid){d.om=away*0.5;d.phiTo=0}
 else if(kind==='flinch'||kind==='armcut'||kind==='legcut'){const cut=kind!=='flinch';d.om=away*(cut?2.8:2.2);d.until=cut?0.9:0.7;kick(cut?2.5:1.5)}   /* a limb lost: it staggers and stays up */
 else if(kind==='ko'||kind==='crumple'){d.crouchTo=0.45;d.om=away*0.25;d.delay=0.3;d.phiTo=side*0.35;d.until=kind==='ko'?3.2:0}
 else if(kind==='liedown'){d.kind='crumple';d.crouchTo=0.55;d.om=away*0.12;d.delay=0.9;d.phiTo=side*0.2;d.gentle=true}
 else if(kind==='melt'||kind==='heap'){d.squashTo=kind==='melt'?0.12:0.3;d.squashRate=kind==='melt'?0.7:3.5;d.squash=d.squash||1;d.crouchTo=0.3;d.om=0}
 else if(kind==='fall'||kind==='shot'||kind==='armoff'||kind==='legoff'){d.om=away*(kind==='shot'?1.6:1.1);d.phiTo=side*0.6;kick(2)}
 else if(kind==='spin'){d.om=away*0.5;d.pom=(side>=0?1:-1)*8;d.phiTo=null;kick(3)}
 else if(kind==='flying'||kind==='hammer'||kind==='throw'){if(opt.at){d.O[0]=opt.at[0];d.O[2]=opt.at[1];d.O[1]=rdGround(d.O[0],d.O[2])}d.noslide=!!opt.far;   /* the game's knock-back: from the tile it was on onto the one the server put it on (game.js g3knock) */
  const far=opt.far!=null?opt.far:kind==='throw'?6:kind==='hammer'?2.6:1.2,up=kind==='throw'?3.2:kind==='hammer'?0.9:0.35;let T=Math.sqrt(8*up/RDG),vy=RDG*T/2;   /* on an arc up to `up` tiles, landing `far` tiles off */
  if(opt.at&&opt.far!=null){const dh=d.O[1]-rdGround(d.O[0]+from[0]*far,d.O[2]+from[2]*far);vy=Math.max(vy,Math.sqrt(Math.max(0,-dh)*2*RDG)+0.5);T=(vy+Math.sqrt(vy*vy+2*RDG*dh))/RDG}   /* the game's: timed to come down on the server's tile, at its height */
  d.air=true;d.V=[from[0]*far/T,vy,from[2]*far/T];d.O[1]+=0.01;d.om=away*(Math.PI/2)/T*1.05;d.pom=(Math.random()<0.5?-1:1)*(kind==='throw'?9:kind==='hammer'?5:2);d.phiTo=null;kick(kind==='throw'?9:6);if(live)d.muscle=0.45}   /* living, it flails a little */
 // the weapon and shield leave the hands as it dies (living, it keeps them; out cold, or its weapon arm cut off, the
 // weapon goes); helmets may come off
 const push=(k)=>rdV.add(rdV.mul(from,k),[0,0.6+Math.random()*0.8,0]),drops=a=>kind==='ko'?a.part.startsWith('armR'):kind==='armcut'?a.part.startsWith((opt.side||t.g3maimS)==='L'?'armL':'armR'):!d.alive;
 for(const a of [...d.gear]){if(!drops(a))continue;if(a.part==='head'&&!(t.g3dropAt&&t.g3dropAt.h)&&!(kind==='throw'||kind==='hammer'||kind==='flying'||Math.random()<0.25))continue;   /* the game dropped it: off it comes */
  rdDrop(d,a,rdV.add(d.air?rdV.mul(d.V,0.6):[0,0,0],push(a.part==='head'?1.2:0.9)))}
 if(kind==='armoff'||kind==='legoff'||kind==='armcut'||kind==='legcut'){if(!opt.limbAt&&t.g3limbAt&&(kind==='armoff'||kind==='legoff'))opt={...opt,limbAt:t.g3limbAt,limbKey:t.g3limbKey};   /* a killing move's fall (skills.js): where the game's limb lies, and its item */const S=(opt.side||t.g3maimS)==='L'?'L':'R',parts=kind.startsWith('arm')?['arm'+S+'u','arm'+S+'l']:['leg'+S+'u','leg'+S+'l'],p=parts[0];   /* the side the game took (Combats.dm LimbFling; parts.py: R is its own right) */const L=d.limbs[p];if(L){for(const q of parts.slice(1))delete d.limbs[q];
  if(d.alive){t.maimed=[...new Set([...(t.maimed||[]),...parts])];d.stumps.push([...L.root0]);t.bleed={t0:now,on:!RDNOBLOOD.has(t.g3&&t.g3.sheet)};
   if(kind==='armcut'){t.g3={...t.g3};delete t.g3[S==='L'?'s':'w'];t.g3p=undefined;t.g3kk=undefined}}   /* its weapon went with the hand */
  d.cut={part:p,parts,key:opt.limbKey||null,tile:opt.limbAt?[Math.round(opt.limbAt[0]),Math.round(-opt.limbAt[1])]:null,O:[...d.O],th:0,om:away*1.8,x:0,y:0,vx:(side>=0?-1:1)*(1.6+Math.random()*0.6),vy:3.6,ang:0,av:(Math.random()<0.5?-1:1)*12};delete d.limbs[p];
  if(opt.limbAt){const C=d.cut,T=1.06,off=[opt.limbAt[0]-d.O[0],0,opt.limbAt[1]-d.O[2]],ax=rdV.dot(off,d.R);C.vx=ax/T;C.drift=rdV.mul(rdV.sub(off,rdV.mul(d.R,ax)),1/T);C.driftT=T}   /* flown to where the game's limb lies (Gear3D.dm RmG3Limb) */
  if(d.cut.key&&typeof G3G!=='undefined'&&G3G.game)(G3G.limbs||(G3G.limbs=new Map())).set(d.cut.key,{d,tile:d.cut.tile,t0:performance.now()});   /* the animation's limb is that item's look (game.js g3rebind) */
  if(!RDNOBLOOD.has(t.g3&&t.g3.sheet)){const B2=rdBasis(d),j=rdW(d,B2,L.root0[0],L.root0[1],0.01);rdBlood(j,rdV.mul(B2.Ux,d.cut.vx*0.5),22,true)}}}
 return d}

function rdStep(d,dt){const now=performance.now()/1000,age=now-d.t0;d.age=age;if(d.frozen||d.done)return;   /* done: not again in the frame's later sub-steps */
 if(d.ghost){rdCutStep(d,dt);if(typeof G3G!=='undefined'&&G3G.game&&d.cut&&d.cut.restAt&&now-d.cut.restAt>1.5&&!d.cut.key)d.done=true;return}   /* in the game the limb lies as the game's own item there */   /* only its lost limb, lying where it fell */
 // the plane: tipping over (a rod falling about its feet), flying (on an arc), spinning in itself
 const g=RDG;
 if(d.kind==='ko'&&d.alive&&!d.air&&typeof G3G!=='undefined'&&G3G.game&&d.t&&d.t.g3ko&&d.t.dx!=null){const t=d.t,X=t.dx+(t.px||0)+((t.iw||1)-1)/2,Z=-t.dy-(t.py||0);if(X!==d.O[0]||Z!==d.O[2]){d.O=[X,t.ly?d.O[1]:rdGround(X,Z),Z];d.tx=t.x;d.ty=t.y}}   /* down and carried (the Doctor, "Carry them"): where its unit is drawn, with its ring, every frame */
 if(d.kind==='pose'){d.th=d.tilt!=null?d.tiltSign*Math.PI/2*d.tilt:0;d.om=0}
 else if(d.kind==='melt'||d.kind==='heap'){d.om=0;d.squash+=(d.squashTo-d.squash)*Math.min(1,dt*d.squashRate);if(Math.abs(d.squash-d.squashTo)<0.03)d.landed=true}   /* it sinks where it stands */   /* a move holds it upright (getting up: as far as it has come) */
 else if(d.alive&&(d.kind==='flinch'||d.kind==='armcut'||d.kind==='legcut'||d.kind==='maimed')){d.om+=(-60*d.th-16*d.om)*dt}   /* rocked by the blow, then back without rocking to and fro */
 else if(d.alive&&((d.kind==='ko'&&age>d.until)||(d.live&&d.rise!=null&&age>d.rise))){if(typeof skGetUp==='function'){skGetUp(d);return}d.om+=(-14*d.th-7*d.om)*dt;d.crouchTo=0;d.muscle=Math.min(1,d.muscle+dt*2)}   /* getting up (skills.js: a move) */
 else if(!d.landed&&!(d.delay&&age<d.delay)){const s=Math.sin(d.th)||(d.om>=0?0.02:-0.02);d.om+=(d.gentle?3:10.5)*s*dt}
 d.th+=d.om*dt;
 if(Math.abs(d.th)>=Math.PI/2&&!d.air){d.th=Math.sign(d.th)*Math.PI/2;if(Math.abs(d.om)>1.2)d.om=-d.om*0.18;else{d.om=0;d.landed=true}}
 if(d.air){d.V[1]-=g*dt;d.O=rdV.add(d.O,rdV.mul(d.V,dt));const gy=rdGround(d.O[0],d.O[2]);if(d.O[1]<=gy&&d.V[1]<0){d.O[1]=gy;d.air=false;d.V=rdV.mul([d.V[0],0,d.V[2]],0.55);d.slide=d.noslide?0:1;if(Math.abs(d.th)<Math.PI/2)d.om=Math.sign(d.th||1)*Math.max(Math.abs(d.om),3)}}
 else if(d.slide){d.O=rdV.add(d.O,rdV.mul(d.V,dt));d.V=rdV.mul(d.V,Math.max(0,1-dt*5));if(Math.hypot(d.V[0],d.V[2])<0.05)d.slide=0}
 if(d.phiTo!=null){const k=Math.min(1,Math.abs(d.th)/(Math.PI/2));d.phi+=((d.phiTo*k)-d.phi)*Math.min(1,dt*6)}else{d.phi+=d.pom*dt;d.pom*=Math.max(0,1-dt*(d.air?0.6:4))}
 // knees giving way: the pelvis sinks, the feet stay
 if(d.crouchTo!=null){const ln=p=>d.limbs[p]?d.limbs[p].len:0,leg=Math.max(ln('legRu')+ln('legRl'),ln('legLu')+ln('legLl'),0.15),want=d.pel0[1]-(d.crouchTo||0)*leg;d.pel[1]+=(want-d.pel[1])*Math.min(1,dt*7)}
 // muscle: a living unit holds its pose; a dying one lets go
 if(!d.alive&&!d.rigid)d.muscle=Math.max(0,d.muscle-dt*4);
 if(d.onStep)d.onStep(d,dt,age);   /* a death's own effects (deaths.js) */
 const gin=-g*Math.cos(d.th)*0.45,gy0=d.air?-(d.O[1]-rdGround(d.O[0],d.O[2]))/Math.max(0.1,Math.cos(d.th)):0;
 // a unit doing a move holds its pose: each joint eases straight onto its angle, parents first, with no spring left
 // in it (a spring overshoots and the chained joints set each other wobbling as a pose is held)
 if(d.rigid){if(!d.held){d.held=true;for(const L of Object.values(d.limbs)){const r=rdRootNow(d,L);L.pose=Math.atan2(L.tip[1]-r[1],L.tip[0]-r[0])}}}   /* frozen stiff: held as they were */
 if(d.kind==='pose'||d.kind==='maimed'||d.rigid){const e=1-Math.exp(-dt*30);for(const L of Object.values(d.limbs)){const r=rdRootNow(d,L);let ta;
   if(L.pose!=null)ta=L.pose;else{const a=L.parent&&d.limbs[L.parent]?rdTurned(d,d.limbs[L.parent]):d.phi;ta=Math.atan2(L.tip0[1]-L.root0[1],L.tip0[0]-L.root0[0])+a}
   const a0=Math.atan2(L.tip[1]-r[1],L.tip[0]-r[0]);let da=ta-a0;while(da>Math.PI)da-=2*Math.PI;while(da<-Math.PI)da+=2*Math.PI;const a1=a0+da*e;
   L.tip[0]=r[0]+Math.cos(a1)*L.len;L.tip[1]=r[1]+Math.sin(a1)*L.len;L.prev=[L.tip[0],L.tip[1]]}}
 else for(let it=0;it<2;it++)for(const [p,L] of Object.entries(d.limbs)){const r=rdRootNow(d,L),c=Math.cos(d.phi),s=Math.sin(d.phi),rx=L.tip0[0]-L.root0[0],ry=L.tip0[1]-L.root0[1];
  if(it===0){const dm=d.alive?0.86:0.985,vx=(L.tip[0]-L.prev[0])*dm,vy=(L.tip[1]-L.prev[1])*dm;   /* living limbs damped hard: a blow jolts them once, they don't bounce */L.prev=[...L.tip];L.tip[0]+=vx;L.tip[1]+=vy+gin*dt*dt*(p==='head'?0.6:1);
   const m=d.muscle;if(m>0){let tx,ty;if(L.pose!=null){tx=r[0]+Math.cos(L.pose)*L.len;ty=r[1]+Math.sin(L.pose)*L.len}
    else{const a=L.parent&&d.limbs[L.parent]?rdTurned(d,d.limbs[L.parent]):d.phi,ca=Math.cos(a),sa=Math.sin(a);tx=r[0]+rx*ca-ry*sa;ty=r[1]+rx*sa+ry*ca}
    const k=Math.min(1,m*dt*(L.pose!=null?22:14));L.tip[0]+=(tx-L.tip[0])*k;L.tip[1]+=(ty-L.tip[1])*k}}
  const dx=L.tip[0]-r[0],dy=L.tip[1]-r[1],dl=Math.hypot(dx,dy)||1e-6;L.tip[0]=r[0]+dx/dl*L.len;L.tip[1]=r[1]+dy/dl*L.len;
  if(Math.cos(d.th)>0.12&&L.tip[1]<gy0){L.tip[1]=gy0;L.prev[0]+=(L.tip[0]-L.prev[0])*0.5}}
 rdCutStep(d,dt);
 // a dead one darkens a little as it settles, then stops being worked out at all (its pictures kept, rdFrame)
 if(!d.alive&&d.landed){d.col=Math.max(0.82,d.col-dt*0.15);let mv=0;for(const L of Object.values(d.limbs))mv=Math.max(mv,Math.abs(L.tip[0]-L.prev[0])+Math.abs(L.tip[1]-L.prev[1]));
  d.still=mv<2e-5&&!d.slide&&!d.air&&!(d.cut&&Math.abs(d.cut.vy)>0.01)?(d.still||0)+dt:0;if(d.still>0.6&&d.col<=0.821&&(!d.onStep||age>6))d.freeze=true}   /* not while its smoke or puddle goes on */
 // out cold and getting up: what it dropped comes back to its hand
 if(d.alive&&d.kind==='ko'&&age>d.until)for(const b of RD.loose)if(b.doll===d&&!b.pick)b.pick=1;
 // launched and living: down a moment once it lands, then up
 if(d.live&&d.landed&&d.rise==null)d.rise=age+1.0;
 // a limb lost, it stands on without it (a leg lost: on the other)
 if(d.alive&&(d.kind==='armcut'||d.kind==='legcut')&&age>d.until){d.kind='maimed';if(typeof G3G!=='undefined'&&G3G.game){rdRetire(d.t);rdShow(d.t)}}   /* in the game its own picture without the limb (Combats.dm LimbLoss); the limb flies on and lies as the game's item */
 // the stump bleeds till bandaged (RDNOBLOOD never), and it bleeds out
 if(d.alive&&d.t.bleed&&d.t.bleed.on&&d.stumps.length){d.drip=(d.drip||0)-dt;if(d.drip<=0){d.drip=0.28+Math.random()*0.25;const B=rdBasis(d),c=Math.cos(d.phi),s=Math.sin(d.phi);
   for(const st of d.stumps){const x=st[0]-d.pel0[0],y=st[1]-d.pel0[1];rdBlood(rdW(d,B,d.pel[0]+x*c-y*s,d.pel[1]+x*s+y*c,0.012),[0,-0.2,0],2,false)}}
  if(now-d.t.bleed.t0>RD.bleedOut&&!(typeof G3G!=='undefined'&&G3G.game))rdBleedOut(d,now)}   /* the arena's rule: in the game the server says when it dies (BleedOut.dm) */
 // out cold ends, a flinch ends, a launch it lived through ends: the unit takes back its picture and pieces
 if(d.alive&&((d.kind==='flinch'&&age>d.until)||(d.kind==='ko'&&age>d.until+1.2&&Math.abs(d.th)<0.03)||(d.live&&d.rise!=null&&age>d.rise+1.2&&Math.abs(d.th)<0.03))){d.done=true;
  if(d.live&&!(typeof G3G!=='undefined'&&G3G.game)){const t=d.t;t.x=Math.round(d.O[0]);t.y=Math.round(-d.O[2]);t.dx=t.x;t.dy=t.y}   /* where it came down (the arena's; in the game the server has said where: move3D, g3knock3D) */
  rdBack(d.t);for(const a of RD.arrows)if(a.doll===d){rdArrowPin(a,d.t);a.doll=null}}}
// A lost limb flies on its own, then lies flat.
function rdCutStep(d,dt){if(!d.cut)return;const C=d.cut,g=RDG;if(C.driftT>0){const k=Math.min(dt,C.driftT);C.O=rdV.add(C.O,rdV.mul(C.drift,k));C.driftT-=k}if(C.vy===0&&!C.restAt)C.restAt=performance.now()/1000;C.vy-=g*dt;C.x+=C.vx*dt;C.y+=C.vy*dt;C.ang+=C.av*dt;C.th+=C.om*dt;if(Math.abs(C.th)>Math.PI/2)C.th=Math.sign(C.th)*Math.PI/2;const L0=d.sets.f[C.part];
 if(C.y<-(L0&&L0.root?L0.root[1]:0.4)+0.02){C.y=-(L0&&L0.root?L0.root[1]:0.4)+0.02;C.vy=Math.abs(C.vy)>1?-C.vy*0.25:0;C.vx*=0.6;C.av*=0.5;C.th=Math.sign(C.th||1)*Math.PI/2}}
// Bled out: it crumples where it stands, or stops where it lies; what it held falls.
function rdBleedOut(d,now){d.alive=false;d.t.bleed.on=false;d.t.dead=true;if(d.kind==='maimed'||d.kind==='pose'){d.kind='crumple';d.crouchTo=0.45;d.om=(Math.random()<0.5?-1:1)*0.25;d.delay=0.2;d.phiTo=0.2;d.t0=now}
 for(const a of [...d.gear])rdDrop(d,a,[0,0.5,0])}
RD.bleedOut=15;   /* seconds a stump bleeds before the unit dies (in the game: its own rules, till a Doctor treats it) */
// A unit back on its feet after a doll: its own picture again, or, missing a limb, a standing doll without it (its
// picture would still show the limb).
function rdBack(t){for(const d of RD.dolls)if(d.t===t&&d.done&&!d.ghost)d.handoff=2;if(t.dead)return;if(t.maimed&&t.maimed.length&&!(typeof G3G!=='undefined'&&G3G.game)){rdStand(t);return}   /* the arena's pictures still show a lost limb; the game's own picture doesn't */rdShow(t)}
// A unit drawn as its doll: only its own picture is left out (t.g3doll, the page's unit drawing), so its ring, bar and
// clicks stay; back after. (In the game the server's list is the truth: a unit no longer in it isn't put back.)
function rdHide(t){t.g3doll=true;const kd=V3.disp.get(t.key);if(kd){if(kd.rc)kd.rc.ep=null;if(kd.wc)kd.wc.ep=null}}
function rdShow(t){t.g3doll=false;if(!(typeof G3G!=='undefined'&&G3G.game)&&!V3.things.includes(t))V3.things.push(t);const kd=V3.disp.get(t.key);if(kd){if(kd.rc)kd.rc.ep=null;if(kd.wc)kd.wc.ep=null}}
function rdStand(t){const d=rdMake(t);if(!d)return null;d.kind='maimed';d.alive=true;d.muscle=1;rdHide(t);RD.dolls.push(d);return d}
// The doll a unit is now (its moves and its falls are all one doll), or null.
function rdLive(t){for(const d of RD.dolls)if(d.t===t&&!d.done&&!d.ghost)return d;return null}
// Its moves and shots stop (a new one, or a fall, takes over its doll).
function rdStopActs(t){if(typeof SK!=='undefined')for(const A of SK.acts)if(A.t===t){A.replaced=true;A.opt.loop=false;A.opt.then=null}
 RD.shots=RD.shots.filter(sh=>sh.t!==t)}
// For a new move: the doll it is now if it can act (standing, flinching, mid-move), a fresh one if it has none, or
// null if it can't act now (dead, out cold, flying, down).
function rdTake(t){const c=rdLive(t);if(!c){rdRetire(t);const d=rdMake(t);if(!d)return null;rdHide(t);RD.dolls.push(d);return d}
 if(!c.alive||c.kind==='ko'||c.live||c.air)return null;
 if(c.cut&&c.kind==='maimed'){rdRetire(t);const d=rdMake(t);if(!d)return null;RD.dolls.push(d);return d}   /* its lost limb stays lying */
 rdStopActs(t);c.th=0;c.om=0;c.tilt=null;return c}
// A unit's standing maimed doll gives way to a new one (a move, a blow); the limb it lost stays where it lies.
function rdRetire(t){for(const d of RD.dolls)if(d.t===t&&!d.done&&!d.ghost&&d.kind==='maimed'){if(d.cut)d.ghost=true;else d.done=true}}
// Bandaged: the stumps stop bleeding.
function rdBandage(t){if(t.bleed)t.bleed.on=false}

// Loose pieces: gravity, a bounce, rolling to a stop, then lying flat as they came to rest.
function rdLoose(b,dt){if(b.pick){const d=b.doll,L=d&&d.limbs[b.part];if(!L||d.done){b.gone=true;return}const B=rdBasis(d),h=rdW(d,B,L.tip[0],L.tip[1],0.02),D=rdV.sub(h,b.X),l=Math.hypot(D[0],D[1],D[2]);
  if(l<0.03){b.gone=true;if(b.held&&d.alive&&!d.done&&d.limbs[b.part])d.gear.push(b.held);return}   /* back in the hand it fell from */b.X=rdV.add(b.X,rdV.mul(D,Math.min(1,dt*9)));b.X[1]+=Math.sin(Math.min(1,b.pick)*Math.PI)*dt*0.6;b.pick+=dt;return}
 if(b.rest)return;b.V[1]-=RDG*dt;b.X=rdV.add(b.X,rdV.mul(b.V,dt));const wl=Math.hypot(b.w[0],b.w[1],b.w[2]);if(wl>1e-4)b.q=rdQ.nrm(rdQ.mul(rdQ.axis(rdV.mul(b.w,1/wl),wl*dt),b.q));
 const gy=rdGround(b.X[0],b.X[2])+b.r;if(b.X[1]<gy){b.X[1]=gy;if(b.V[1]<0){b.V[1]=-b.V[1]*0.32;b.bounce++}const k=b.aimed?0.18:0.72;b.V[0]*=k;b.V[2]*=k;b.w=rdV.mul(b.w,0.62)}   /* thrown onto its tile: it stays on it */
 // near the ground and slow: turn to lie flat (its flat side down), keeping its heading
 if(b.X[1]<gy+0.02&&Math.hypot(b.V[0],b.V[1],b.V[2])<0.5){const ax=b.flat===1?[0,1,0]:[0,0,1],cur=rdQ.rot(b.q,ax),want=cur[1]>=0||b.flat===1?[0,1,0]:[0,-1,0],c=rdV.cross(cur,want),s=Math.hypot(c[0],c[1],c[2]),an=Math.atan2(s,rdV.dot(cur,want));
  if(s>1e-4&&an>0.01){b.q=rdQ.nrm(rdQ.mul(rdQ.axis(rdV.mul(c,1/s),an*Math.min(1,dt*8)),b.q))}b.w=rdV.mul(b.w,0.8);b.V=rdV.mul(b.V,0.85);if(an<0.02&&Math.hypot(b.V[0],b.V[2])<0.02){b.rest=true;b.X[1]=gy}}}

// An arrow: nocked at o, loosed at the target point P (on an arc, about 16 tiles a second); it stays in what it hits.
// Where a shot lands on a unit: a body part's point on its standing picture (its rig box), and the doll part it then
// sticks in. part: 'head', 'chest', 'lower' (the belly), 'armL', 'armR', 'legL', 'legR'.
const RDAIM={head:['head'],chest:['torso'],lower:['torso'],armL:['armLl','armLu'],armR:['armRl','armRu'],legL:['legLu','legLl'],legR:['legRu','legRl']};
function rdAim(t,part){const L0=t.g3last,RR=RD.rig&&typeof rdRigOf==='function'?rdRigOf(t):null,rig=RR&&RR.rig;
 const opts=RDAIM[part]||RDAIM.chest,p=opts[Math.floor(Math.random()*opts.length)],mid=[L0.LX,L0.yA+L0.sh*0.55,L0.LZ];if(!rig||!L0)return {P:mid,dpart:'torso'};
 const r=rig['SNEW'[L0.face]||'S'];let q=r&&r[p];if(q&&!q.box&&RDMIRROR[p])q=r[RDMIRROR[p]];if(!q||!q.box)return {P:mid,dpart:'torso'};
 const b=q.box,jx=(Math.random()-0.5)*0.4,px=(b[0]+b[2])/2+jx*(b[2]-b[0]),py=part==='chest'?b[1]+(b[3]-b[1])*0.32:part==='lower'?b[1]+(b[3]-b[1])*0.72:(b[1]+b[3])/2+(Math.random()-0.5)*0.3*(b[3]-b[1]);
 const a=L0.hw*(2*px/64-1),u=1-py/64;return {P:[L0.LX+L0.R[0]*a+L0.L[0]*L0.sh*u,L0.yA+L0.R[1]*a+L0.L[1]*L0.sh*u,L0.LZ+L0.R[2]*a+L0.L[2]*L0.sh*u],dpart:p}}
// the game's rolls (Combat - Bows.dm RmArrowRegion; Throwing.dm RemasterThrownWound)
function rdArrowPart(){const r=1+Math.floor(Math.random()*20);return r===1?'legL':r===2?'legR':r===3?'armR':r===4?'armL':r<=6?'head':r===8?'lower':r<=10?'chest':Math.random()<0.6?'chest':'lower'}
function rdThrowPart(){return ['legL','legR','armL','armR','chest','chest'][Math.floor(Math.random()*6)]}
// A shot's way past the target: aimed a little to its side and on, to come down in the ground beyond.
function rdMissPoint(o,P){const F=rdV.n([P[0]-o[0],0,P[2]-o[2]]),S=[-F[2],0,F[0]],k=Math.random()<0.5?-1:1;return rdV.add(P,rdV.add(rdV.mul(S,k*(0.32+Math.random()*0.15)),rdV.mul(F,0.05)))}
function rdLooseArrow(o,P,target,kill,opt){const D=rdV.sub(P,o),dist=Math.hypot(D[0],D[2])||0.01,T=Math.max(0.12,dist/16);
 const V=[D[0]/T,(D[1]+0.5*RDG*T*T)/T,D[2]/T];RD.arrows.push({X:[...o],V,state:'fly',t:0,T,target,kill,P,res:(opt&&opt.res)||'hit',dpart:(opt&&opt.dpart)||'torso'})}
function rdArrowBasis(dir){const X=rdV.n(dir),up=Math.abs(X[1])>0.95?[1,0,0]:[0,1,0],Z=rdV.n(rdV.cross(X,up)),Y=rdV.cross(Z,X);return [X,Y,Z]}
function rdAttachArrow(d,a,part){part=part&&(part==='torso'||d.limbs[part])?part:'torso';const [X,Y,Z]=rdArrowBasis(a.dir);a.at=rdAttach(d,{name:'arrow',tier:'wood',s:a.s,o:a.X,X,Y,Z},part)}
// An arrow stuck in a unit standing as its own picture: kept in the picture's frame, so it goes where the unit goes
// and turns with it (the page alone: the server knows nothing of it). Facing the other way, it is on the other side.
RD.arrowStay=20;   /* seconds an arrow stays in a body before it falls out */
function rdArrowPin(a,t){const L0=t&&t.g3last;a.state='unit';a.unit=t;if(!L0)return;const O=[L0.LX,L0.yA,L0.LZ],N=rdV.cross(L0.R,L0.L),D=rdV.sub(a.X,O),dir=a.dir||[1,0,0];
 a.rel=[rdV.dot(D,L0.R),rdV.dot(D,L0.L),rdV.dot(D,N)];a.reld=[rdV.dot(dir,L0.R),rdV.dot(dir,L0.L),rdV.dot(dir,N)];a.face0=L0.face}
function rdArrowOnUnit(a){const t=a.unit,L0=t&&t.g3last;if(!a.rel||!L0)return;const O=[L0.LX,L0.yA,L0.LZ],N=rdV.cross(L0.R,L0.L),f=(a.face0^1)===L0.face?-1:1;
 const at=(r,o)=>rdV.add(o,rdV.add(rdV.add(rdV.mul(L0.R,r[0]*f),rdV.mul(L0.L,r[1])),rdV.mul(N,r[2]*f)));a.X=at(a.rel,O);a.dir=rdV.n(at(a.reld,[0,0,0]))}
// An arrow that won't stay: it glances off or falls from a shield, a loose piece now.
function rdArrowOff(a,V){const L=typeof skLen==='function'?skLen('arrow'):20,[X,Y,Z]=rdArrowBasis(a.dir||[1,0,0]);a.state='gone';
 RD.loose.push({name:'arrow',tier:'wood',s:a.s,c:[L/2,0,0],r:0.01,X:rdV.add(a.X,rdV.mul(X,L/2*a.s)),V,q:rdQuat(X,Y,Z),w:[(Math.random()-0.5)*14,(Math.random()-0.5)*14,(Math.random()-0.5)*14],rest:false,flat:2,bounce:0})}
function rdArrowStep(a,dt){if(a.state!=='fly')return;a.t+=dt;a.V[1]-=RDG*dt;a.X=rdV.add(a.X,rdV.mul(a.V,dt));a.dir=rdV.n(a.V);
 // a miss flies on past the target and sticks in the ground beyond
 if(a.res==='miss'){const gy=rdGround(a.X[0],a.X[2]);if(a.t>a.T*0.5&&a.X[1]<=gy+0.01){a.X=rdV.sub([a.X[0],gy,a.X[2]],rdV.mul(a.dir,a.s*12));a.state='ground'}return}
 if(a.t>=a.T){a.state='hit';const t=a.target;a.X=[...a.P];a.dir=rdV.n(a.V);
  const from=rdV.n([a.V[0],0,a.V[2]]);
  // blocked: it sticks in the raised shield (its doll's), and falls when the shield comes down
  if(a.res==='block'){const d=t&&RD.dolls.find(x=>x.t===t&&!x.done&&x.alive),g=d&&d.gear.find(x=>x.slot==='s');
   if(g){const w=rdGearWorld(d,g);a.X=rdV.sub(rdV.add(w.o,rdV.mul(from,-0.03)),rdV.mul(a.dir,a.s*14));a.state='doll';a.doll=d;a.shield=true;rdAttachArrow(d,a,g.part);rdDust(w.o,3);return}
   a.res='deflect'}
  // turned by its armour: sparks, and it glances off
  if(a.res==='deflect'){rdSparks(a.X,8,[0.95,0.95,1]);rdArrowOff(a,rdV.add(rdV.mul(from,-1.2),[(Math.random()-0.5)*1.5,1.4,(Math.random()-0.5)*1.5]));if(t)rdStart(t,'flinch',from);return}
  // pushed in a little, the shaft left out behind, in the part it struck
  a.X=rdV.sub(a.X,rdV.mul(a.dir,a.s*20));
  a.stuck=performance.now()/1000;
  if(t){const d=rdStart(t,a.kill?'shot':'flinch',from);if(d){a.state='doll';a.doll=d;rdAttachArrow(d,a,a.dpart)}else rdArrowPin(a,t)
   if(!RDNOBLOOD.has(t.g3&&t.g3.sheet))rdBlood(a.P,rdV.mul(from,0.4),a.kill?8:3,false)}}}

// The archer's shot, played on the archer's own sprite: it turns to its target, then its picture becomes a standing
// doll whose arms move. The bow arm comes up straight at the target; the drawing arm reaches to the string, then
// pulls back, the elbow out behind and the hand at the cheek, the string bending back to it with the arrow on it from
// that hand through the bow; it looses (the hand flies back), holds a moment and lowers. The bow is in the bow hand
// (the left), upright, its string toward the archer.
// opt: {res: 'hit' | 'block' | 'deflect' | 'miss', part: where it lands (rdAim's), rolled as the game does if not given}
function rdShoot(t,target,kill,opt){if(!t.g3last||!target||!target.g3last)return;const kd=V3.disp.get(t.key);if(kd&&kd.rc)kd.rc.ep=null;
 {const dx=target.x-t.x,dy=target.y-t.y;t.dir=Math.abs(dx)>=Math.abs(dy)?(dx>=0?4:8):(dy>=0?1:2)}   /* turned to its target, as the game turns a unit */
 RD.shots.push({t,target,kill,opt:opt||{},t0:performance.now()/1000,doll:null,loosed:false})}
// Two bones reaching a point in a doll's plane: the angles that put the forearm's end on P (the elbow out from the body).
function rdReach(d,u,l,P,tuck){const U=d.limbs[u],W=d.limbs[l];if(!U||!W)return null;const H=rdRootNow(d,U),a=U.len,c=W.len;let vx=P[0]-H[0],vy=P[1]-H[1],dd=Math.hypot(vx,vy);
 const mx=(a+c)*0.995,mn=Math.abs(a-c)+0.002;if(dd<1e-5){vx=0;vy=-1;dd=1}const k=Math.min(mx,Math.max(mn,dd))/dd;vx*=k;vy*=k;dd*=k;
 const al=Math.acos(Math.max(-1,Math.min(1,(a*a+dd*dd-c*c)/(2*a*dd)))),base=Math.atan2(vy,vx);let best=null;
 for(const kn of [1,-1]){const th=base+kn*al,K=[H[0]+Math.cos(th)*a,H[1]+Math.sin(th)*a],out=(tuck?-1:1)*Math.abs(K[0]-d.pel0[0])-0.3*K[1];if(!best||out>best.out)best={th,lo:Math.atan2(H[1]+vy-K[1],H[0]+vx-K[0]),out}}
 return [best.th,best.lo]}
const rdMixA=(a,b,k)=>{let d=b-a;while(d>Math.PI)d-=2*Math.PI;while(d<-Math.PI)d+=2*Math.PI;return a+d*k};
function rdShotDraw(sh,emit){const now=performance.now()/1000,a=now-sh.t0,t=sh.t,T0=sh.target.g3last;if(!T0)return true;
 if(!sh.doll){if(a<0.12)return false;   /* a frame or two for its turned picture */
  const d=rdTake(t);if(!d)return true;d.kind='pose';d.alive=true;d.muscle=1;
  const bw=d.gear.find(g=>g.name.startsWith('weapon.'));sh.bow=bw?{name:bw.name,tier:bw.tier,s:bw.s}:null;if(bw)d.gear.splice(d.gear.indexOf(bw),1);
  sh.doll=d;sh.a0=a;
  const tgt=[T0.LX,T0.yA+T0.sh*0.55,T0.LZ];sh.tgt=tgt;sh.sig=rdV.dot(rdV.sub(tgt,d.O),d.R)>=0?1:-1}
 const d=sh.doll,b=a-sh.a0,sg=sh.sig,L=d.limbs;
 // the aim, in the world: level at the target. The picture's arms can only reach across it, so the share of the aim
 // that runs across (k) sets the pose: across, the bow arm out straight at the target and the drawing hand pulled
 // back past the shoulder; toward or away from the eye, the bow held in front of the chest and the string drawn to it
 // which picture it shows decides the pose: side on (E, W) the arms work across the picture; its front (S) or back
 // (N) the hands meet before its chest, the bow hand out toward the target's side by how far across it is
 const F=rdV.n([sh.tgt[0]-d.O[0],0,sh.tgt[2]-d.O[2]]),across=Math.min(1,Math.abs(rdV.dot(F,d.R))*1.3),sideOn=d.fl==='E'||d.fl==='W',k=sideOn?across:0,kk=sideOn?0:across;
 const fw=a=>sg>0?a:Math.PI-a;
 // the drawing arm is the one on the camera's side (a side view hides the far one behind the body); the bow in the other
 const near=d.fl==='W'?'L':'R',far=near==='L'?'R':'L',bu='arm'+far+'u',bl='arm'+far+'l',du='arm'+near+'u',dl='arm'+near+'l';
 const q0=Math.min(1,Math.max(0,(b-0.32)/0.4)),e=q0*q0*(3-2*q0);   /* how far it has drawn */
 // face on, the hands meet in front of the chest: the bow hand a little to its own side, the string hand at it, then
 // drawn up to the cheek (toward or away from the eye, the draw runs through the picture's depth)
 const nk=L.head?L.head.root0:[d.pel0[0],d.pel0[1]+0.4],px=d.k,side=p=>L[p]?Math.sign(L[p].root0[0]-nk[0])||1:1;
 const bs=sideOn?side(bu):sg,ds=sideOn?side(du):-sg;   /* the bow hand's side and the drawing hand's */
 const chest=[nk[0]+bs*(1.5+6*kk)*px,nk[1]-(7-2*kk)*px],nockAt=[chest[0]+ds*(1+1.5*kk)*px,chest[1]-0.5*px],cheek=[nk[0]+ds*(2.5-1.5*kk)*px,nk[1]-1.5*px],flung=[nk[0]+ds*9*px,nk[1]-3*px];
 // seen from behind (its back to the eye, the target beyond) the hands stay within its outline, the elbows tucked in
 const eh=rdV.n([(V3.eye||[0,10,10])[0]-d.O[0],0,(V3.eye||[0,10,10])[2]-d.O[2]]),away=d.fl==='N';   /* its back picture */
 const put=(u,l,acrossU,acrossL,P)=>{if(!L[u]||!L[l])return;const r=rdReach(d,u,l,away?[nk[0]+(P[0]-nk[0])*0.35,P[1]]:P,away)||[acrossU,acrossL];L[u].pose=rdMixA(r[0],acrossU,k);L[l].pose=rdMixA(r[1],acrossL,k)};
 const lerp=(A,B,t)=>[A[0]+(B[0]-A[0])*t,A[1]+(B[1]-A[1])*t];
 if(b<0.9){put(bu,bl,fw(0.12),fw(0.12),chest);   /* the bow up, at the target */
  put(du,dl,fw(0.3+(Math.PI-0.65)*e),fw(0.1+0.6*e),lerp(nockAt,cheek,e))}   /* the string hand to the string, then the draw */
 else if(b<1.15){put(du,dl,fw(0.3+Math.PI-0.65),fw(Math.PI-0.15),flung)}   /* loosed: the drawing hand flies back */
 else{for(const p of [bu,bl,du,dl])if(L[p])L[p].pose=null}   /* lowered */
 const map={armLl:bl,armRl:dl};

 if((sh.opt.res==='block'||sh.opt.dodge)&&!sh.guarded&&b>=0.5&&typeof skAct==='function'){sh.guarded=true;skAct(sh.target,sh.opt.res==='block'?'block':'dodge',t,{})}   /* its shield comes up to meet the arrow, or it ducks aside */
 // its back to the eye: the bow, the hands and the arrow are in front of it, behind its body as seen (the bow back by
 // the draw too, so the drawn string stays behind it); else the bow and the bow arm are drawn over the body (side on
 // the bow arm is the far one, which would be hidden behind it)
 // (side on the bow arm is the far one, its pixels the near arm's: it stays behind the body with the bow, user)
 d.armsBehind=away&&b<1.15;d.armsFront=null;
 const B=rdBasis(d),front=rdV.dot(B.Nn,rdV.sub(V3.eye||[0,10,10],d.O))>=0;
 const off=away?rdV.dot(F,B.Nn)*(0.1+(sh.bow&&b<0.9?(1.6+16*e)*sh.bow.s:0)):sideOn?(front?1:-1)*0.02:(front?1:-1)*(0.012+0.08*Math.max(0,rdV.dot(F,eh)));   /* away: behind it; side on: in front, with the drawing arm (the bow arm tucked behind, user); facing: in front */
 const hand=p=>{const l=L[p]||L[p.replace(/l$/,'u')];return l?rdW(d,B,l.tip[0],l.tip[1],off):d.O},grip=hand(map.armLl);
 if(sh.bow){const s=sh.bow.s,drawing=b>=0.32&&b<0.9;
  // upright, facing the target; the string drawn back along the aim by the pull, the arrow on it through the bow
  const Y=rdV.n([F[0],0.04,F[2]]),X=rdV.n(rdV.sub([0,1,0],rdV.mul(Y,Y[1]))),Z=rdV.cross(X,Y),q=rdQuat(X,Y,Z);
  const pull=drawing?(1.6+16*e)*s:0,dr=Math.min(1,Math.max(0,(pull/s-1.6)/16)),dn=dr>=0.875?'1.0':dr>=0.625?'0.75':dr>=0.375?'0.5':dr>=0.125?'0.25':'';
  emit(dn?'weapon.bow@'+dn:'weapon.bow',sh.bow.tier,grip,q,s);
  if(drawing&&!away){const nock=rdV.sub(grip,rdV.mul(Y,pull)),[AX,AY,AZ]=rdArrowBasis(Y);emit('arrow','wood',nock,rdQuat(AX,AY,AZ),s)}
  if(b>=0.9&&!sh.loosed){sh.loosed=true;const res=sh.opt.res||'hit',A=rdAim(sh.target,sh.opt.part||rdArrowPart());
   rdLooseArrow(grip,res==='miss'?rdMissPoint(grip,A.P):A.P,sh.target,sh.kill&&res==='hit',{res,dpart:A.dpart});RD.arrows[RD.arrows.length-1].s=s}}   /* off from the bow */
 if(b>1.75){d.done=true;rdBack(t);return true}
 return false}

// A held piece drawn as its picture on the doll (the unit's own, from the facing it had): in the doll's plane, at the
// grip, turned with the part and the wrist; seen from the doll's back, the opposite facing's picture, mirrored.
function rdCardQuad(d,B,a,front,lift,cc){const c=a.card,C=c.C,f=rdPartFrame(d,a.part),an=f.ang+(a.wrist||0);
 const fc=Math.cos(f.ang),fs=Math.sin(f.ang),gx=f.root[0]+a.p[0]*fc-a.p[1]*fs,gy=f.root[1]+a.p[0]*fs+a.p[1]*fc;
 const s=a.s,ca=Math.cos(an),sa=Math.sin(an),flip=!front,i=flip?(c.i+c.nf/2)%c.nf:c.i,fu=C.fu||1/c.nf,n=(a.stowed?a.p[2]*(front?1:-1):Math.max(-0.03,Math.min(0.03,a.p[2])))+(front?lift:-lift);   /* slung on its back: on the side its back is */
 const corner=(cx,cy)=>{let x=(cx-C.ax)*s,y=(C.ay-cy)*s;if(flip)x=-x;return rdW(d,B,gx+x*ca-y*sa,gy+x*sa+y*ca,n)};
 let va=RD.va.get(c.tex);if(!va){va=new VA();RD.va.set(c.tex,va)}const u0=(i+0.0005)*fu,u1=(i+0.9995)*fu;
 quad(va,corner(0,C.h),corner(C.w,C.h),corner(C.w,0),corner(0,0),QN0,cc,[u0,1,u1,1,u1,0,u0,0])}
// Blood, sparks, dust: little bits flying off and falling; blood that lands stays a while as a splash on the ground.
function rdBlood(at,vel,n,big){for(let i=0;i<n;i++)RD.fx.push({k:'blood',X:[...at],V:[vel[0]+(Math.random()-0.5)*1.4,(big?1.4:0.8)+Math.random()*1.6,vel[2]+(Math.random()-0.5)*1.4],life:0.6+Math.random()*0.5,age:0,r:0.012+Math.random()*0.014})}
function rdSparks(at,n,col){for(let i=0;i<n;i++){const a=Math.random()*6.283,e=Math.random()*1.2;RD.fx.push({k:'spark',X:[...at],V:[Math.cos(a)*2.4*Math.cos(e),1.2+Math.sin(e)*2,Math.sin(a)*2.4*Math.cos(e)],life:0.18+Math.random()*0.2,age:0,r:0.008+Math.random()*0.008,col:col||[1,0.92,0.6]})}}
function rdDust(at,n){for(let i=0;i<n;i++){const a=Math.random()*6.283;RD.fx.push({k:'dust',X:[at[0],at[1]+0.02,at[2]],V:[Math.cos(a)*0.9,0.25+Math.random()*0.4,Math.sin(a)*0.9],life:0.5+Math.random()*0.4,age:0,r:0.05+Math.random()*0.05})}}
// A particle of a death's effects: colour c0 to c1 over its life, size r0 to r1, g its pull (tiles/s/s, + down, - up),
// drag slowing it; splat: the colour it leaves on the ground where it lands (drool, venom, goo), else it just goes.
function rdPart(X,V,life,r0,r1,c0,c1,g=0,drag=0,splat=null){RD.fx.push({k:'p',X:[...X],V:[...V],life,age:0,r:r0,r0,r1,c0,c1,g,drag,splat})}
// One of the game's own pixel particles (the race specials' and burning ground's atlas, art/enhance/breath64.py:
// rb-breath-dragon.png): el 'fire', 'frost', 'poison', 'holy', 'plague', 'spark', 'dust', 'acid'..., in one of its
// three looks, animating through its four frames, added on as light, fading in and out.
const RDPX=['fire','frost','poison','magma','sand','water','plague','holy','unholy','mind','acid','dust','web','spark'];
function rdPx(X,V,life,r0,r1,el,g=0,drag=0){RD.fx.push({k:'px',X:[...X],V:[...V],life,age:0,r:r0,r0,r1,el:Math.max(0,RDPX.indexOf(el)),v:Math.floor(Math.random()*3),seed:Math.random()*10,g,drag})}
function rdFxStep(dt){for(const f of RD.fx){f.age+=dt;if(f.k==='splat')continue;
  if(f.k==='px'){const q=Math.max(0,1-f.drag*dt);f.V[0]*=q;f.V[1]=(f.V[1]-f.g*dt)*q;f.V[2]*=q;f.X=rdV.add(f.X,rdV.mul(f.V,dt));f.r=f.r0+(f.r1-f.r0)*f.age/f.life;continue}
  if(f.k==='p'){const q=Math.max(0,1-f.drag*dt);f.V[0]*=q;f.V[1]=(f.V[1]-f.g*dt)*q;f.V[2]*=q;f.X=rdV.add(f.X,rdV.mul(f.V,dt));const u=f.age/f.life;f.r=f.r0+(f.r1-f.r0)*u;
   if(f.g>0){const gy=rdGround(f.X[0],f.X[2]);if(f.X[1]<gy+0.004){if(f.splat){f.k='splat';f.col=f.splat;f.X[1]=gy+0.004;f.age=0;f.life=6;f.r=f.r0*2.2}else f.age=f.life}}continue}f.V[1]-=(f.k==='dust'?0.6:RDG)*dt;if(f.k==='dust'){f.V=rdV.mul(f.V,Math.max(0,1-dt*3));f.r+=dt*0.12}
  f.X=rdV.add(f.X,rdV.mul(f.V,dt));const gy=rdGround(f.X[0],f.X[2]);if(f.X[1]<gy+0.005&&f.k!=='dust'){if(f.k==='blood'){f.k='splat';f.X[1]=gy+0.004;f.age=0;f.life=7;f.r*=1.8}else f.age=f.life}}
 RD.fx=RD.fx.filter(f=>f.age<f.life)}
function rdFxDraw(){if(!RD.fx.length&&!(typeof SK!=='undefined'&&SK.trails.length)&&!(typeof WK!=='undefined'&&WK.lines.length))return;const gl=V3.gl,L=V3.loc,va=RD.fxva||(RD.fxva=new VA()),tv=RD.trva||(RD.trva=new VA());va.length=0;tv.length=0;const R=[Math.cos(V3.yaw),0,-Math.sin(V3.yaw)],U=[0,1,0];
 const pv=RD.pxva||(RD.pxva=new VA());pv.length=0;const nowP=performance.now()/1000,ROWS=RDPX.length*3;
 for(const f of RD.fx){const k=f.age/f.life,x=f.X,r=f.r;let c;
  if(f.k==='px'){const fade=Math.min(1,Math.sin(Math.PI*k)*1.6);if(fade<=0.02)continue;const fr=Math.floor(nowP*9+f.seed*1.7)%4,u0=fr/4+0.002,u1=(fr+1)/4-0.002,row=f.el*3+f.v,v0=row/ROWS+0.0005,v1=(row+1)/ROWS-0.0005;
   quad(pv,[x[0]-R[0]*r,x[1]-r,x[2]-R[2]*r],[x[0]+R[0]*r,x[1]-r,x[2]+R[2]*r],[x[0]+R[0]*r,x[1]+r,x[2]+R[2]*r],[x[0]-R[0]*r,x[1]+r,x[2]-R[2]*r],QN0,[fade,fade,fade,1],[u0,v1,u1,v1,u1,v0,u0,v0]);continue}
  if(f.k==='splat'){const a=0.85*(1-Math.max(0,k-0.7)/0.3),sc=f.col||[0.42,0.04,0.03];c=[sc[0],sc[1],sc[2],a];quad(va,[x[0]-r,x[1],x[2]+r],[x[0]+r,x[1],x[2]+r],[x[0]+r,x[1],x[2]-r],[x[0]-r,x[1],x[2]-r],QN0,c);continue}
  if(f.k==='p'){const a=f.c0,b=f.c1;c=[a[0]+(b[0]-a[0])*k,a[1]+(b[1]-a[1])*k,a[2]+(b[2]-a[2])*k,a[3]+(b[3]-a[3])*k]}
  else c=f.k==='blood'?[0.55,0.05,0.04,0.9]:f.k==='spark'?[f.col[0],f.col[1],f.col[2],0.9*(1-k)]:[0.62,0.58,0.5,0.45*(1-k)];
  quad(va,[x[0]-R[0]*r,x[1]-r,x[2]-R[2]*r],[x[0]+R[0]*r,x[1]-r,x[2]+R[2]*r],[x[0]+R[0]*r,x[1]+r,x[2]+R[2]*r],[x[0]-R[0]*r,x[1]+r,x[2]-R[2]*r],QN0,c)}
 if(typeof skTrailsDraw==='function')skTrailsDraw(tv);
 // the pixel particles: added on, as the page adds its fire
 if(pv.length){const e=v3tex('rb-breath-dragon.png');if(e&&e.ok){gl.enable(gl.BLEND);gl.blendFunc(gl.ONE,gl.ONE);gl.depthMask(false);gl.depthFunc(gl.LEQUAL);gl.uniform1f(L.addm,1);gl.uniform1f(L.alpha,1);
   gl.bindBuffer(gl.ARRAY_BUFFER,V3.dyn);v3up(pv);v3draw(V3.dyn,pv.length/12,e);gl.uniform1f(L.addm,0);gl.depthFunc(gl.LESS);gl.blendFunc(gl.SRC_ALPHA,gl.ONE_MINUS_SRC_ALPHA);gl.depthMask(true);gl.disable(gl.BLEND)}}
 if(!va.length&&!tv.length)return;gl.enable(gl.BLEND);gl.blendFunc(gl.SRC_ALPHA,gl.ONE_MINUS_SRC_ALPHA);gl.depthMask(false);gl.uniform1f(L.soft,1);gl.uniform1f(L.alpha,1);
 // the bits round (the page's white disc), the trails plain
 if(va.length){gl.bindBuffer(gl.ARRAY_BUFFER,V3.dyn);v3up(va);v3draw(V3.dyn,va.length/12,V3.blob)}if(tv.length){gl.bindBuffer(gl.ARRAY_BUFFER,V3.dyn);v3up(tv);v3draw(V3.dyn,tv.length/12,null)}
 gl.uniform1f(L.soft,0);gl.depthMask(true);gl.disable(gl.BLEND)}

// Each frame (after the pieces, gear3d.js g3draw): step and draw the dolls, the loose pieces, the arrows, the shots.
function rdFrame(){for(const d of RD.dolls)if(d.t&&d.t.dead&&!d.out){d.out=1;const i=V3.things.indexOf(d.t);if(i>=0)V3.things.splice(i,1)}   /* the dead leave the list (their ring and bar too); in the game the server takes them */
 const now=performance.now()/1000,dt=Math.min(1/30,Math.max(0.001,now-(RD.last||now)))*(RD.slow||1);RD.last=now;if(!RD.dolls.length&&!RD.loose.length&&!RD.arrows.length&&!RD.shots.length&&!RD.fx.length&&!(typeof SK!=='undefined'&&(SK.acts.length||SK.shots.length||SK.trails.length))&&!(typeof WK!=='undefined'&&WK.props.length)&&!(typeof G3G!=='undefined'&&G3G.posed.length))return;
 if(!g3gpu())return;const gl=V3.gl,eye=V3.eye||[0,10,10];
 const emit=(name,tier,o,q,s,noShear=1)=>{const b=G3.B[name];if(!b)return;let a=G3.I.get(name);if(!a){a=new VA();G3.I.set(name,a)}a.push(o[0],o[1],o[2],s,q[0],q[1],q[2],q[3],G3.row[tier]??G3.row.iron,g3cols(tier)[0][3],noShear,0)};
 const sub=Math.max(1,Math.ceil(dt/0.008)),h=dt/sub;
 for(const d of RD.dolls)for(let i=0;i<sub;i++)rdStep(d,h);
 for(const b of RD.loose)for(let i=0;i<sub;i++)rdLoose(b,h);
 for(const a of RD.arrows)for(let i=0;i<sub;i++)rdArrowStep(a,h);
 RD.shots=RD.shots.filter(sh=>!rdShotDraw(sh,emit));
 if(typeof skStep==='function')skStep(dt,emit);   /* weapon skills (skills.js) */
 rdFxStep(dt);RD.loose=RD.loose.filter(b=>!b.gone);
 RD.dolls=RD.dolls.filter(d=>!d.done||(d.handoff>0&&d.handoff--));   /* a finished doll stays drawn two frames, till its unit's own picture is back */
 for(const a of RD.va.values())a.length=0;
 if(typeof g3poses==='function')g3poses();   /* bodies lying as their death dolls fell (game.js) */
 if(typeof wkCards==='function')wkCards();   /* work's pictures (the pixel sack, work.js) */
 for(const d of RD.dolls){if(d.cache){for(const [tex,f] of d.cache){let va=RD.va.get(tex);if(!va){va=new VA();RD.va.set(tex,va)}va.copy(f,0,f.length)}continue}
  const ghost=!!d.ghost;
  const mark=d.freeze?new Map([...RD.va].map(([k,v])=>[k,v.length])):null;
  const B=rdBasis(d),front=rdV.dot(B.Nn,rdV.sub(eye,d.O))>=0,set=front?d.sets.f:d.sets.b,lift=0.006,cc=d.tint?[d.col*d.tint[0],d.col*d.tint[1],d.col*d.tint[2],1]:[d.col,d.col,d.col,1];
  const fr=['armRu','armRl','armLu','armLl','legRu','legRl','legLu','legLl'],hid=fr.filter(p=>set[p]&&set[p].borrow),shown=fr.filter(p=>!(set[p]&&set[p].borrow)),order0=d.armsFront?[...hid.filter(p=>!d.armsFront.includes(p)),'torso',...shown.filter(p=>p.startsWith('leg')),'head',...shown.filter(p=>p.startsWith('arm')),...d.armsFront.filter(p=>hid.includes(p))]:d.armsBehind?[...shown.filter(p=>p.startsWith('arm')),...hid,'torso',...shown.filter(p=>p.startsWith('leg')),'head']:[...hid,'torso',...shown.filter(p=>p.startsWith('leg')),'head',...shown.filter(p=>p.startsWith('arm'))],   /* arms reaching out on the far side: behind the body */order=front?order0:[...order0].reverse();
  for(let k=0;k<order.length&&!ghost;k++){const p=order[k];const q=set[p];if(!q||!q.box)continue;if(RD.hide&&RD.hide.has(p))continue;   /* (checks: parts left out) */if(d.cut&&(d.cut.parts||[d.cut.part]).includes(p))continue;const f=rdPartFrame(d,p),r0=q.rootP||f.root0;
   // turn the picture's pixels about the part's own joint, and put that joint on the skeleton's
   const ang=p==='torso'?d.phi:(q.rest!=null&&f.abs!=null?f.abs-q.rest:f.ang),c=Math.cos(ang),s=Math.sin(ang),bx=q.box,u0=(q.cell*64+bx[0])/(64*RDPARTS.length),u1=(q.cell*64+bx[2])/(64*RDPARTS.length),v0=bx[1]/64,v1=bx[3]/64;
   const pt=(px,py)=>{const x0=(q.flip?32-px:px-32)*d.k-r0[0],y0=(64-py)*d.k-r0[1];return rdW(d,B,f.root[0]+x0*c-y0*s,f.root[1]+x0*s+y0*c,(lift+k*0.0012)*(front?1:-1))};
   let va=RD.va.get(q.tex);if(!va){va=new VA();RD.va.set(q.tex,va)}
   const ua=q.flip?u1:u0,ub=q.flip?u0:u1;quad(va,pt(bx[0],bx[3]),pt(bx[2],bx[3]),pt(bx[2],bx[1]),pt(bx[0],bx[1]),QN0,cc,[ua,v1,ub,v1,ub,v0,ua,v0])}
  if(d.cut){const C=d.cut,q0=set[C.part];if(q0&&q0.box){const ct=Math.cos(C.th),st=Math.sin(C.th),Uy=rdV.sub(rdV.mul(d.Uy,ct),rdV.mul(d.N,st)),c=Math.cos(C.ang),s=Math.sin(C.ang),r0=q0.rootP||[0,0];
   for(const pn of C.parts||[C.part]){const q=set[pn];if(!q||!q.box)continue;const bx=q.box;   /* the lost limb as it was, turning about its shoulder or hip */
    const pt=(px,py)=>{const x0=(q.flip?32-px:px-32)*d.k-r0[0],y0=(64-py)*d.k-r0[1],x=r0[0]+C.x+x0*c-y0*s,y=r0[1]+C.y+x0*s+y0*c;return [C.O[0]+d.R[0]*x+Uy[0]*y,C.O[1]+d.R[1]*x+Uy[1]*y+0.004,C.O[2]+d.R[2]*x+Uy[2]*y]};
    if(pn===C.part)C.mid=pt((bx[0]+bx[2])/2,(bx[1]+bx[3])/2);   /* its middle as drawn: where a click finds it (game.js g3rebind, the item's g3pc) */
    let va=RD.va.get(q.tex);if(!va){va=new VA();RD.va.set(q.tex,va)}const W=64*RDPARTS.length,u0=(q.cell*64+bx[0])/W,u1=(q.cell*64+bx[2])/W,a0=va.length;quad(va,pt(bx[0],bx[3]),pt(bx[2],bx[3]),pt(bx[2],bx[1]),pt(bx[0],bx[1]),QN0,cc,[q.flip?u1:u0,bx[3]/64,q.flip?u0:u1,bx[3]/64,q.flip?u0:u1,bx[1]/64,q.flip?u1:u0,bx[1]/64]);if(mark){const m=mark.get(q.tex)||0;(d.cutVerts||(d.cutVerts=[])).push([q.tex,a0-m,va.length-m])}}}}   /* kept: where its lost limb's pictures are in d.cache (game.js g3keepPose, P.limbVerts) */
  // while it stands its pieces are drawn as on a standing unit (laid toward the face, gear3d.js); once it tips, as they are
  // held pieces: their pictures on the doll; a piece with no picture (no pixel mode) as its 3D model
  const upright=Math.abs(d.th)<0.15&&!d.air?0:1;for(const a of ghost?[]:d.gear){if(a.card&&!a.live){rdCardQuad(d,B,a,front,a.stowed?0:a.slot==='w'&&d.fl==='N'?-0.02:0.02,[1,1,1,1]);continue}   /* its back picture: the weapon behind it */const w=rdGearWorld(d,a);emit(a.name,a.tier,w.o,rdQuat(rdV.n(w.X),rdV.n(w.Y),rdV.n(w.Z)),a.s,upright)}
  if(mark){d.cache=[];for(const [k,v] of RD.va){const from=mark.get(k)||0;if(v.length>from)d.cache.push([k,v.f.slice(from,v.length)])}d.frozen=true}}
 // loose pieces: their 3D models while they fly and roll; once still, a flat picture lying on the ground (as a dropped
 // item is drawn), so a field of dropped gear costs what a field of items does
 for(const b of RD.loose){const GP=b.rest&&G3.pix&&G3.pix.pieces[b.name]&&G3.pix.pieces[b.name].ground;if(!GP){emit(b.name,b.tier,rdV.sub(b.X,rdQ.rot(b.q,rdV.mul(b.c,b.s))),b.q,b.s);continue}
  const tex=g3ptex(b.name,b.tier,'g',b.pal),x=rdQ.rot(b.q,[1,0,0]),A=rdV.n([x[0],0,x[2]]),down=rdQ.rot(b.q,[0,0,1])[1]<0&&b.flat===2;
  let Up=rdV.cross([0,1,0],A);if(down)Up=rdV.mul(Up,-1);const gy=rdGround(b.X[0],b.X[2])+0.003,s=b.s,C=[b.X[0],gy,b.X[2]];
  const corner=(px,py)=>[C[0]+A[0]*(px-GP.ax)*s+Up[0]*(GP.ay-py)*s,gy,C[2]+A[2]*(px-GP.ax)*s+Up[2]*(GP.ay-py)*s];
  let va=RD.va.get(tex);if(!va){va=new VA();RD.va.set(tex,va)}quad(va,corner(0,GP.h),corner(GP.w,GP.h),corner(GP.w,0),corner(0,0),QN0,[1,1,1,1],[0,GP.v1,GP.u1,GP.v1,GP.u1,0,0,0])}
 const nowA=performance.now()/1000;
 for(const a of RD.arrows){if(a.state==='gone')continue;let o,X,Y,Z;
  if(a.stuck&&(a.state==='doll'||a.state==='unit')&&nowA-a.stuck>RD.arrowStay){rdArrowOff(a,[(Math.random()-0.5)*0.4,0.2,(Math.random()-0.5)*0.4]);continue}   /* worked loose: it falls out */
  if(a.state==='unit')rdArrowOnUnit(a);
  if(a.state==='doll'&&a.doll&&a.at){if(RD.dolls.includes(a.doll)){const w=rdGearWorld(a.doll,a.at);o=w.o;X=rdV.n(w.X);Y=rdV.n(w.Y);Z=rdV.n(w.Z);a.X=o;a.dir=X}
   else if(a.shield){rdArrowOff(a,[(Math.random()-0.5)*0.5,0.3,(Math.random()-0.5)*0.5]);continue}else rdArrowPin(a,a.doll.t)}
  if(!o){[X,Y,Z]=rdArrowBasis(a.dir||rdV.n(a.V));o=a.X}emit('arrow','wood',o,rdQuat(X,Y,Z),a.s||0.03)}
 // the doll parts: pictures (unlit, as the units are), drawn like the gear after the hidden-unit silhouettes
 for(const [k,a] of RD.va){if(!a.length)continue;const e=v3tex(k);if(!e||!e.ok)continue;gl.bindBuffer(gl.ARRAY_BUFFER,V3.dyn);v3up(a);v3draw(V3.dyn,a.length/12,e)}
 rdRings();rdFxDraw()}
// A living unit mid-move (a skill, a flinch, out cold) keeps the ring under its feet that the page draws for a unit
// standing as itself: the same colours, size and health band (remastered.html's unit rings).
function rdRings(){if(typeof RC_MINE==='undefined'||!V3.ring)return;const rg=RD.rg||(RD.rg=new VA());rg.length=0;
 for(const d of RD.dolls){const t=d.t;if(!d.alive||d.done||d.ghost||d.air||!(t.kind==='mine'||t.kind==='npc'||t.kind==='player'))continue;
  const rc=t.kind==='mine'?(t.selected?RC_SEL:RC_MINE):t.kind==='player'?(t.ally?RC_ALLY:t.war?RC_WAR:RC_PLAYER):t.peace?RC_PEACE:RC_FOE,r=t.kind==='mine'&&!t.selected?0.42:0.5;
  const X=(t.dx??t.x)+(t.px||0)+((t.iw||1)-1)/2,Z=-(t.dy??t.y)-(t.py||0),y=(t.ly||0)+0.03,hf=t.hp!=null?Math.max(0,Math.min(1,t.hp/100)):1;
  if(V3.hpRing!==false&&t.hp!=null&&hf<1)v3hpRing(rg,X,y,Z,r,t.kind==='mine'&&!t.selected?(hf>0.5?HPOK:hf>0.25?HPMID:HPLOW):rc,hf,hf);else rg.v(X,y,Z,r,0,1,HPRN,0,rc[0],rc[1],rc[2],rc[3])}
 if(!rg.length)return;const gl=V3.gl,L=V3.loc;gl.enable(gl.BLEND);gl.blendFunc(gl.SRC_ALPHA,gl.ONE_MINUS_SRC_ALPHA);gl.depthMask(false);gl.uniform1f(L.soft,1);
 v3drawInst(rg,4,V3.ring);gl.uniform1f(L.soft,0);gl.depthMask(true);gl.disable(gl.BLEND)}
