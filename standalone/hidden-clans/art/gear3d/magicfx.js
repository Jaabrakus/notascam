// The magic weapons' own 2D pixel effects on the 3D pieces (art/gear3d; the animation arena): each staff and
// enchanted weapon a unit holds (meshes.MAGIC) shows the effect the 2D one has (wearables64.magic_layers: glow
// rings, sparkles, pixel flames, wisps, runes, frost, bolts, smoke, venom), its frames cut round the weapon held
// straight up (fxsheet.py) and laid along the 3D piece as it turns and swings, its pixels the piece's own size.
// Added on, as the game adds its effect sheet over a unit (light: colour times opacity), with hard pixels.
const MF={meta:null,busy:0,va:new Map(),spells:[],hits:[],last:0};
function mfLoad(){if(MF.busy||performance.now()<(MF.waitTil||0))return;MF.busy=1;fetch('g3fx.json').then(r=>{if(!r.ok)throw r.status;return r.json()}).then(d=>{MF.meta=d}).catch(()=>{MF.busy=0;MF.wait=Math.min(60000,(MF.wait||2500)*2);MF.waitTil=performance.now()+MF.wait})}
const mfV={add:(a,b)=>[a[0]+b[0],a[1]+b[1],a[2]+b[2]],sub:(a,b)=>[a[0]-b[0],a[1]-b[1],a[2]-b[2]],mul:(a,k)=>[a[0]*k,a[1]*k,a[2]*k],dot:(a,b)=>a[0]*b[0]+a[1]*b[1]+a[2]*b[2],
 cross:(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]],n:v=>{const l=Math.hypot(v[0],v[1],v[2])||1;return [v[0]/l,v[1]/l,v[2]/l]}};

// Each magic piece held right now: its style and its frame in the world (o the top of its grip, X up the piece,
// Y toward its edge or head; s tiles a pixel). Standing units (gear3d.js's pose) and units moving as dolls.
function mfHeld(){const out=[],M=MF.meta;
 for(const t of V3.things){const w=t.g3&&t.g3.w;if(!w||t.g3doll)continue;   /* drawn as its doll: its effect goes with the doll's weapon (below), not left at its standing pose */const st=String(w).split(':')[0];if(!M[st])continue;
  const g=typeof rdPose==='function'&&rdPose(t,'w');if(g)out.push({key:String(t.key||t.ref),st,o:g.o,X:mfV.n(g.X),Y:mfV.n(g.Y),s:g.s})}
 if(typeof RD!=='undefined')for(const d of RD.dolls){const a=d.gear.find(g=>g.slot==='w');if(!a)continue;const st=a.name.replace('weapon.','');if(!M[st])continue;
  const w=rdGearWorld(d,a);out.push({key:String(d.t.key||d.t.ref),st,o:w.o,X:mfV.n(w.X),Y:mfV.n(w.Y),s:a.s})}
 return out}

// Each frame (last, gear3d.js g3draw): each held piece's effect frame, a quad along the piece. Its across is the
// piece's edge side as the eye sees it (so a curved blade's glow follows its curve), square to the piece.
function mfFrame(){if(typeof V3==='undefined'||!V3.gl)return;if(!MF.meta){mfLoad();return}
 const now=performance.now()/1000,dt=Math.min(1/20,Math.max(0.001,now-(MF.last||now)));MF.last=now;
 const held=mfHeld();if(!held.length&&!MF.spells.length&&!MF.hits.length)return;const eye=V3.eye||[0,10,10];
 for(const a of MF.va.values())a.length=0;
 mfSpells(dt,now,eye);
 for(const h of held){const C=MF.meta[h.st],tex='g3fx-'+h.st.replace(/ /g,'_')+'.png';
  const D=mfV.n(mfV.sub(eye,h.o));let W=mfV.sub(h.Y,mfV.mul(D,mfV.dot(h.Y,D)));W=mfV.sub(W,mfV.mul(h.X,mfV.dot(W,h.X)));
  if(Math.hypot(W[0],W[1],W[2])<0.25){const c=mfV.n(mfV.cross(h.X,D));W=mfV.dot(c,h.Y)<0?mfV.mul(c,-1):c}W=mfV.n(W);
  let k=0;for(let i=0;i<h.key.length;i++)k+=h.key.charCodeAt(i);const f=(Math.floor(now/C.dt)+k)%C.frames,u0=f/C.frames,u1=(f+1)/C.frames;
  const P=(x,y)=>mfV.add(h.o,mfV.add(mfV.mul(h.X,(C.oy-y)*h.s),mfV.mul(W,(x-C.ox)*h.s)));
  let va=MF.va.get(tex);if(!va){va=new VA();MF.va.set(tex,va)}
  quad(va,P(0,C.h),P(C.w,C.h),P(C.w,0),P(0,0),QN0,[1,1,1,1],[u0,1,u1,1,u1,0,u0,0])}
 const gl=V3.gl,L=V3.loc;gl.enable(gl.BLEND);gl.blendFunc(gl.ONE,gl.ONE);gl.depthMask(false);gl.depthFunc(gl.LEQUAL);gl.uniform1f(L.addm,1);gl.uniform1f(L.alpha,1);
 for(const [k,a] of MF.va){if(!a.length)continue;const e=v3tex(k);if(!e||!e.ok)continue;gl.bindBuffer(gl.ARRAY_BUFFER,V3.dyn);v3up(a);v3draw(V3.dyn,a.length/12,e)}
 gl.uniform1f(L.addm,0);gl.depthFunc(gl.LESS);gl.blendFunc(gl.SRC_ALPHA,gl.ONE_MINUS_SRC_ALPHA);gl.depthMask(true);gl.disable(gl.BLEND)}

// A staff's spell: its own effect frames leave the staff's head (skills.js cast) and fly at the target on a low arc,
// a few fading copies behind, then burst on it bigger and fade; the target flinches, or, killed, falls as that
// spell kills (frost and death crumple, a dragon's knocks back, an orb's spins).
const MFKILL={'crystal staff':'crumple','skull staff':'crumple','dragon staff':'flying','orb staff':'spin','spider staff':'crumple'};
function mfCast(st,g,s,target,kill){const C=MF.meta&&MF.meta[st];if(!C||!target||!target.g3last)return;const X=mfV.n(g.X),head=mfV.add(g.o,mfV.mul(X,(C.oy-C.h/2)*s));
 const tg=target.g3last,P1=[tg.LX,tg.yA+tg.sh*0.5,tg.LZ],T=Math.max(0.2,Math.hypot(P1[0]-head[0],P1[2]-head[2])/8);MF.spells.push({st,P0:head,P1,t:0,T,s,target,kill,trail:[]})}
function mfSprite(st,P,s,k,lum,f,eye){const C=MF.meta[st],tex='g3fx-'+st.replace(/ /g,'_')+'.png',D=mfV.n(mfV.sub(eye,P)),R=mfV.n(mfV.cross([0,1,0],D)),U=mfV.cross(D,R);
 const hw=C.w/2*s*k,hh=C.h/2*s*k,u0=f/C.frames,u1=(f+1)/C.frames,a=mfV.mul(R,hw),b=mfV.mul(U,hh);let va=MF.va.get(tex);if(!va){va=new VA();MF.va.set(tex,va)}
 quad(va,mfV.sub(mfV.sub(P,a),b),mfV.sub(mfV.add(P,a),b),mfV.add(mfV.add(P,a),b),mfV.add(mfV.sub(P,a),b),QN0,[lum,lum,lum,1],[u0,1,u1,1,u1,0,u0,0])}
function mfSpells(dt,now,eye){
 MF.spells=MF.spells.filter(S=>{S.t+=dt;const u=Math.min(1,S.t/S.T),P=mfV.add(mfV.add(S.P0,mfV.mul(mfV.sub(S.P1,S.P0),u)),[0,Math.sin(Math.PI*u)*0.15,0]),C=MF.meta[S.st],f=Math.floor(now/C.dt)%C.frames;
  S.trail.unshift(P);if(S.trail.length>4)S.trail.length=4;S.trail.forEach((q,i)=>mfSprite(S.st,q,S.s,1.15-i*0.15,i?0.55-i*0.12:1,(f+i)%C.frames,eye));
  if(u<1)return true;const T=S.target,from=mfV.n([S.P1[0]-S.P0[0],0,S.P1[2]-S.P0[2]]);
  if(T&&T.g3last&&typeof rdStart==='function')rdStart(T,S.kill?(MFKILL[S.st]||'fall'):'flinch',from);
  MF.hits.push({st:S.st,P:S.P1,t:0,T:0.4,s:S.s});return false});
 MF.hits=MF.hits.filter(H=>{H.t+=dt;const u=H.t/H.T,C=MF.meta[H.st];if(u>=1)return false;mfSprite(H.st,H.P,H.s,1.8+0.8*u,1-u,Math.floor(H.t/C.dt)%C.frames,eye);return true})}
