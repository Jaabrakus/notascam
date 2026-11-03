// Built by art/gear3d/install.py from gear3d.js, ragdoll.js, skills.js, deaths.js, work.js, magicfx.js, bosses.js, game.js: edit those, then run it again.
// 3D gear on sprite units (art/gear3d): a unit drawn as its picture holds its weapon, shield and helmet as smooth 3D
// pieces (gear3d.json, meshes.py) at the picture's own fist, forearm and head (gear3d-anchors.json, anchors.py),
// turned the way the unit faces, so they turn as the camera goes round. t.g3: {sheet, w, s, h}, each "style:tier".
// A piece sits in front of or behind the flat picture by where that hand is on the body; its depth is laid along
// the look from the eye (the picture is drawn face-on, so a piece drawn the same way stays on the hand it is in).
//
// Drawn on the GPU: each piece's mesh is uploaded once (G3.B), and a unit adds one record a piece a frame (where,
// how big, turned how, which tier); the vertex shader's gear mode (G3VS) turns, places and shades it. Without
// instancing the same pieces are built in JS (g3piece), slower.
const G3={ready:false,P:{},C:new Map(),va:null,I:new Map(),B:null,pal:null,row:null,pix:null,cards:new Map(),rec:[],f:null};
// How far each kind of piece turns from the way the picture faces toward the way the unit really faces (the
// picture's four facings are 90 degrees apart): a helmet stays on the drawn face, a weapon follows the unit.
const G3TURN={w:1,s:0.6,h:0.3};
const G3WIND=[0.45,-0.12,0.88],G3STRIKE=[-0.15,0.9,-0.4];   /* an attack's wind-up (up beside the head, as drawn) and blow (right, front, up) */
// A held weapon stays in front of its glove (the fist is drawn on the picture's plane), a shield in front of its
// forearm, unless that hand is on the far side of the body: pixels out from the picture.
const G3FRONT={w:2.8,s:2.2};
// The vertex shader's gear mode (inst 5): the mesh (p, n; uv: palette column, shines) turned by the quaternion i1,
// i0.w world units a pixel, at i0.xyz; its depth from the picture laid along the line to the eye; i2: palette row,
// the tier's shine. Colour is the palette's times k: edges turning away from the eye darkened like the pictures'
// outlines; metal mirrors a sky over a darker ground and takes a glint from the sun.
const G3VS='if(inst>4.5){vec3 lp=p*i0.w,qv=i1.xyz;vec3 t1=2.0*cross(qv,lp);vec3 O=lp+i1.w*t1+cross(qv,t1);vec3 t2=2.0*cross(qv,n);N=n+i1.w*t2+cross(qv,t2);'+
 'vec3 nc=cross(iright,ilean),ev=normalize(eye-i0.xyz);float cn=max(0.3,dot(ev,nc));if(i2.z<0.5)O+=(ev/cn-nc)*dot(O,nc);P=i0.xyz+O;'+
 'vec3 V=normalize(eye-P);float nv=dot(N,V),fr=1.0-abs(nv),rim=1.0-0.62*fr*fr*fr;float h=max(dot(N,normalize(light+V)),0.0),h4=h*h*h*h,h8=h4*h4,h24=h8*h8*h8;'+
 'float m=uv.y*i2.y;vec3 R=2.0*nv*N-V;float env=mix(0.62,1.38,smoothstep(-0.35,0.85,R.y));float k=rim*mix(1.0,env,m)+m*h24*1.6*(light.y>0.0?1.0:0.3);'+
 'C=vec4(k,k,k,1.0);U=vec2(uv.x,i2.x);}else ';
// Pixel mode (gear3d-pix.json, pixelgear.py): the pieces as pixel art the way the dragons are drawn, a strip of 16
// facings each, the facing nearest the camera drawn as a picture at the fist, forearm or head.
// How far each piece turns from the way its picture faces toward the way the unit really faces. Nothing, any of them:
// the body is one of four pictures, so a weapon turned toward a diagonal or a turned camera showed another angle than
// the arm holding it (a hand axe side-on, lying flat out at the waist); held as the picture holds it, every facing and
// camera turn shows the hold that was set for the front, back and sides (the owner, 10-27: "we need to fix movement
// and looks for all angles back front all 16 angles when walking"). Was w 1, s 0.5.
const G3PIXTURN={w:0,s:0,h:0};
// A long sword's grip sat with its middle on the hand point (the fist's lower edge), so the grip and the pommel hung
// below the hand (the owner, 10-27: "the sword hilt is not on hand", "it was just the sword was to low"): its pictures
// raised this many art pixels, the grip across the fist and the guard above it. Every other weapon's hold looked right.
const G3GRIP={'weapon.longsword':3,'weapon.rune sword':3};
function g3load(){if(G3.busy)return;G3.busy=1;Promise.all([fetch('gear3d.json').then(r=>{if(!r.ok)throw r.status;return r.json()}),fetch('gear3d-anchors.json').then(r=>{if(!r.ok)throw r.status;return r.json()}),fetch('gear3d-pix.json').then(r=>r.ok?r.json():null).catch(()=>null)]).then(([d,a,px])=>{G3.pix=px;if(px)for(const n in G3GRIP){const p=px.pieces[n];if(p)for(const c of p.poses)c.ay+=G3GRIP[n]}
 const dec=b=>{const s=atob(b),u=new Uint8Array(s.length);for(let i=0;i<s.length;i++)u[i]=s.charCodeAt(i);return u};
 for(const k in d.pieces){const p=d.pieces[k];G3.P[k]={v:p.v,pos:new Int16Array(dec(p.pos).buffer),nrm:new Int8Array(dec(p.nrm).buffer),mat:dec(p.mat)}}
 G3.q=d.q;G3.T=d.tiers;G3.rest=d.rest;G3.M=d.magic||{};G3.metallic=d.metallic||[0,1,2,9,15,17];G3.A=a;G3.ready=true}).catch(e=>{G3.failed=String(e);G3.wait=Math.min(60000,(G3.wait||2500)*2);setTimeout(()=>{G3.busy=0},G3.wait)})}   /* in the game the files may still be on their way: asked again after 5 s, then less often */
// A worn piece's style and tier ("longsword:iron"); a magic piece has its own tier (meshes.MAGIC_TIER, "crystal staff").
function g3split(v){const [st,tier]=String(v).split(':');return [st,tier||(G3.M&&G3.M[st])||'iron']}
// The tier a piece's pictures were drawn in: its own, else iron, else the one it has (each piece is drawn in the
// tiers the game makes it in, smoothgear.py).
function g3pixTier(name,tier){const P=G3.pix&&G3.pix.pieces[name],ts=(P&&P.tiers)||(G3.pix&&G3.pix.tiers)||['iron'];return ts.includes(tier)?tier:ts.includes('iron')?'iron':ts[0]}
// A piece's picture for a tier (and a player's own colours, pal): its own file, or, from palette pictures (smoothgear
// --index: each pixel a material and a brightness), one coloured here the first time it is wanted, then kept.
function g3ptex(name,tier,pose,pal){const n=name.replace(/ /g,'_'),PX=G3.pix;if(!PX||!PX.index)return 'g3p-'+n+'-'+g3pixTier(name,tier)+'-'+pose+'.png';
 const pk=g3palKey(pal),key='g3c-'+n+'-'+pose+'-'+(tier||'iron')+(pk?'-'+pk:'')+'.png';if(!V3.tex.has(key))g3colour(key,'g3p-'+n+'-idx-'+pose+'.png',tier||'iron',pal);return key}
// A player's own colours: {metal, trim, paint, paint2} each a ramp's name (wearables64.RAMPS): the metal of the
// piece, its trim (gold parts), its main paint (red parts) and second paint (blue parts).
const G3PALM={metal:[0,1,2,15,17],trim:[9],paint:[7],paint2:[8]};
function g3palKey(pal){if(!pal)return '';return Object.keys(G3PALM).filter(k=>pal[k]).map(k=>k[0]+k.slice(-1)+'.'+pal[k]).join('_')}
function g3base(IX,m,ramp){const r=IX.ramps[ramp]||IX.ramps.iron,sh=IX.sh[m]||0,met=IX.met.includes(m),L=(a,b,k)=>[a[0]+(b[0]-a[0])*k,a[1]+(b[1]-a[1])*k,a[2]+(b[2]-a[2])*k];
 const kk=sh+(met?0:5);let b=kk===0?L(r[1],r[2],0.75):kk===1?L(r[2],r[3],0.5):r[Math.min(4,Math.max(0,2+sh))];if(met&&sh<0)b=L(r[1],r[2],0.35);return b}
function g3colour(key,src,tier,pal){const e={t:null,ok:false};V3.tex.set(key,e);const IX=G3.pix.index,use=IX.use[tier]||IX.use.iron,base=[];
 for(let m=0;m<32;m++){let ramp=use[m];if(pal)for(const k in G3PALM)if(pal[k]&&G3PALM[k].includes(m))ramp=pal[k];base.push(g3base(IX,m,ramp))}
 const go=img=>{const cv=document.createElement('canvas');cv.width=img.width;cv.height=img.height;const cx=cv.getContext('2d');cx.drawImage(img,0,0);const D=cx.getImageData(0,0,cv.width,cv.height),p=D.data;
  for(let i=0;i<p.length;i+=4){if(!p[i+3])continue;const m=p[i];if(m<32){const b=base[m],l=p[i+1]/100;p[i]=Math.min(255,b[0]*l);p[i+1]=Math.min(255,b[1]*l);p[i+2]=Math.min(255,b[2]*l)}
   else{const b=base[p[i+1]&31],l=p[i+2]/100*0.3;p[i]=Math.min(40,b[0]*l);p[i+1]=Math.min(40,b[1]*l);p[i+2]=Math.min(40,b[2]*l)}}   /* the outline: its neighbour, darkened */
  cx.putImageData(D,0,0);(V3.texQ||(V3.texQ=[])).push([cv,e])};
 const I=(G3.idx||(G3.idx=new Map())),c=I.get(src);if(c&&c.ok){go(c.img);return}if(c){c.wait.push(go);return}
 const img=new Image(),r={img,ok:false,wait:[go]};I.set(src,r);img.onload=()=>{r.ok=true;for(const f of r.wait)f(img)};img.src=src}
// A tier's colour (0-1) and shine for each material code (meshes.MAT).
function g3cols(tier){let c=G3.C.get(tier);if(c)return c;const T=G3.T,r=T[tier]||T.iron,f=k=>k.map(v=>v/255),mix=(a,b,k)=>a.map((v,i)=>v+(b[i]-v)*k);
 const soft=['wood','leather','bonehide','dragonhide','spidersilk','bone','dragonbone','dragonfang','fang'].includes(tier);
 const sp={iron:0.55,silver:0.8,gold:0.75,bronze:0.65,adamantium:0.75,diamond:0.95,hell:0.5,chitin:0.45,dragon:0.35,spiderfang:0.4}[tier]??(soft?0.12:0.5);
 const M=f(mix(r[1],r[2],0.75)),B=f(mix(r[2],r[3],0.5)),iron=f(T.iron[2]),ir=soft?T.iron:r;
 c=[[...M,sp],[...B,sp*1.1],soft?[...iron,0.55]:[...M,sp],[...f(T.wood[2]),0.04],[...f(mix(T.leather[1],T.leather[2],0.5)),0.06],[0.07,0.06,0.06,0],[...f(T.silk[3]),0.1],
  [...f(T.red[2]),0.08],[...f(T.blue[2]),0.08],[...f(T.gold[3]),0.75],[...f(T.horn[2]),0.18],[...f(T.feather[3]),0.05],[...f(T.plume[2]),0.03],[...f(T.wood[0]),0],[...f(T.wood[1]),0.03],
  [...f(mix(r[1],r[2],0.35)),sp*0.8],[...f(mix(T.leather[0],T.leather[1],0.6)),0.04],[...f(mix(ir[2],ir[3],0.7)),soft?0.55:sp*1.1],
  /* the magic pieces' own stuff (meshes.MAT 18-26): crystal, orb, bone, leaf, chitin, eye, dragon bone, dragon horn, ember */
  [...f(mix(T.adamantium[2],T.ice[3],0.5)),0.95],[...f(mix(T.purple[2],T.purple[3],0.5)),0.85],[...f(T.bone[2]),0.12],[...f(mix(T.green[2],T.green[3],0.5)),0.05],
  [...f(mix(T.chitin[2],T.chitin[3],0.4)),0.45],[...f(T.spidereye[3]),0.6],[...f(T.dragonbone[2]),0.12],[...f(T.dragonhorn[2]),0.18],[...f(T.ember[3]),0.0],[...f(mix(T.green[0],T.green[1],0.7)),0.04],   /* 27: Bloodwhisker's green-stained haft */
  [0.5,0.47,0.42,0.1],[0.62,0.36,0.24,0.35],[...f(mix(T.wool[1],T.wool[2],0.5)),0.03],[...f(mix(T.silver[2],T.silver[3],0.5)),0.7]];   /* 28-31 work: stone, ore, sackcloth, a fish */
 G3.C.set(tier,c);return c}
function g3slerp(a,b,k){const d=Math.max(-1,Math.min(1,a[0]*b[0]+a[1]*b[1]+a[2]*b[2]));const th=Math.acos(d);if(th<1e-3)return a;const s=Math.sin(th),p=Math.sin((1-k)*th)/s,q=Math.sin(k*th)/s;return [a[0]*p+b[0]*q,a[1]*p+b[1]*q,a[2]*p+b[2]*q]}
function g3n(v){const l=Math.hypot(v[0],v[1],v[2])||1;return [v[0]/l,v[1]/l,v[2]/l]}
// The turn taking a piece's x, y, z onto X, Y, Z (unit length, right-handed) as a quaternion [x, y, z, w].
function g3quat(X,Y,Z){const tr=X[0]+Y[1]+Z[2];let s;
 if(tr>0){s=Math.sqrt(tr+1)*2;return [(Y[2]-Z[1])/s,(Z[0]-X[2])/s,(X[1]-Y[0])/s,0.25*s]}
 if(X[0]>Y[1]&&X[0]>Z[2]){s=Math.sqrt(1+X[0]-Y[1]-Z[2])*2;return [0.25*s,(Y[0]+X[1])/s,(Z[0]+X[2])/s,(Y[2]-Z[1])/s]}
 if(Y[1]>Z[2]){s=Math.sqrt(1+Y[1]-X[0]-Z[2])*2;return [(Y[0]+X[1])/s,0.25*s,(Z[1]+Y[2])/s,(Z[0]-X[2])/s]}
 s=Math.sqrt(1+Z[2]-X[0]-Y[1])*2;return [(Z[0]+X[2])/s,(Z[1]+Y[2])/s,0.25*s,(X[1]-Y[0])/s]}
// Once a page: each mesh in a buffer (position in pixels, normal, palette column, shines) and the palette, a texel
// for each material (column) of each tier (row).
function g3gpu(){if(G3.B)return true;const gl=V3.gl;if(!gl||!V3.ix||!V3.ibuf)return false;
 const names=Object.keys(G3.T),NT=names.length,d=new Uint8Array(32*NT*4);G3.row={};
 names.forEach((tn,r)=>{G3.row[tn]=(r+0.5)/NT;const c=g3cols(tn);for(let m=0;m<c.length&&m<32;m++){const o=(r*32+m)*4;d[o]=Math.round(Math.min(1,c[m][0])*255);d[o+1]=Math.round(Math.min(1,c[m][1])*255);d[o+2]=Math.round(Math.min(1,c[m][2])*255);d[o+3]=255}});
 const t=gl.createTexture();gl.bindTexture(gl.TEXTURE_2D,t);gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL,false);gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,32,NT,0,gl.RGBA,gl.UNSIGNED_BYTE,d);
 for(const [k,v] of [[gl.TEXTURE_MIN_FILTER,gl.NEAREST],[gl.TEXTURE_MAG_FILTER,gl.NEAREST],[gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE],[gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE]])gl.texParameteri(gl.TEXTURE_2D,k,v);G3.pal=t;
 const met=new Set(G3.metallic),q=1/G3.q;G3.B={};
 for(const k in G3.P){const p=G3.P[k],f=new Float32Array(p.v*8);for(let i=0;i<p.v;i++){const o=i*8,a=i*3;f[o]=p.pos[a]*q;f[o+1]=p.pos[a+1]*q;f[o+2]=p.pos[a+2]*q;f[o+3]=p.nrm[a]/127;f[o+4]=p.nrm[a+1]/127;f[o+5]=p.nrm[a+2]/127;f[o+6]=(p.mat[i]+0.5)/32;f[o+7]=met.has(p.mat[i])?1:0}
  const b=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,b);gl.bufferData(gl.ARRAY_BUFFER,f,gl.STATIC_DRAW);G3.B[k]={buf:b,n:p.v}}
 return true}
// One piece without instancing: local x, y, z along X, Y, Z (world, unit length) from origin o, s world units a pixel;
// Sv shears a point's depth (along Nc) onto the line to the eye; lit by the sun lv with a glint toward the eye Ve.
function g3piece(out,p,cols,o,X,Y,Z,s,Nc,Sv,Ve,lv){const P=p.pos,N=p.nrm,Mt=p.mat,q=s/G3.q,n=p.v;
 const hx=lv[0]+Ve[0],hy=lv[1]+Ve[1],hz=lv[2]+Ve[2],hl=Math.hypot(hx,hy,hz)||1,Hx=hx/hl,Hy=hy/hl,Hz=hz/hl,day=lv[1]>0?1:0.3;
 for(let i=0;i<n;i++){const a=i*3,px=P[a]*q,py=P[a+1]*q,pz=P[a+2]*q;let x=X[0]*px+Y[0]*py+Z[0]*pz,y=X[1]*px+Y[1]*py+Z[1]*pz,z=X[2]*px+Y[2]*py+Z[2]*pz;
  const dn=x*Nc[0]+y*Nc[1]+z*Nc[2];x+=Sv[0]*dn;y+=Sv[1]*dn;z+=Sv[2]*dn;
  const nx0=N[a]/127,ny0=N[a+1]/127,nz0=N[a+2]/127,nx=X[0]*nx0+Y[0]*ny0+Z[0]*nz0,ny=X[1]*nx0+Y[1]*ny0+Z[1]*nz0,nz=X[2]*nx0+Y[2]*ny0+Z[2]*nz0;
  const c=cols[Mt[i]]||cols[0],sh=c[3],fr=1-Math.abs(nx*Ve[0]+ny*Ve[1]+nz*Ve[2]),fr2=fr*fr,rim=1-0.62*fr2*fr;let g=0;if(sh>0){const h=Math.max(0,nx*Hx+ny*Hy+nz*Hz),h2=h*h,h4=h2*h2,h8=h4*h4,h16=h8*h8;g=sh*h16*h8*0.75*day}
  out.v(o[0]+x,o[1]+y,o[2]+z,nx,ny,nz,0,0,Math.min(1,c[0]*rim+g),Math.min(1,c[1]*rim+g*0.97),Math.min(1,c[2]*rim+g*0.9),1)}}
// A piece for this frame: a record for the GPU, or (no instancing) its triangles.
function g3emit(cx,name,o,X,Y,Z,s,tier){if(cx.gpu){const b=G3.B[name];if(!b)return;let a=G3.I.get(name);if(!a){a=new VA();G3.I.set(name,a)}const q=g3quat(X,Y,Z);
  a.push(o[0],o[1],o[2],s,q[0],q[1],q[2],q[3],G3.row[tier]??G3.row.iron,g3cols(tier)[0][3],0,0);return}
 const p=G3.P[name];if(p)g3piece(G3.va||(G3.va=new VA()),p,g3cols(tier),o,X,Y,Z,s,cx.Nc,cx.Sv,cx.Ve,cx.lv)}
// Pixel mode's fast path (most frames, most units). What depends only on the camera is worked out once a frame
// (G3.f): the picture plane, the line to the eye, and for each picture facing and each way a unit can face, the
// facing each kind of piece shows. A unit's pieces (t.g3p, once a server update): their strips, poses and anchors.
// Per unit there is then only the arithmetic of placing its cards; nothing is made that would need collecting.
function g3frame(R,L){const f=G3.f||(G3.f={}),E=V3.eye;if(!E)return null;
 if(f.y===V3.yaw&&f.p===V3.pitch&&f.l0===L[0]&&f.l1===L[1]&&f.l2===L[2]&&f.e0===E[0]&&f.e1===E[1]&&f.e2===E[2])return f;
 f.y=V3.yaw;f.p=V3.pitch;f.l0=L[0];f.l1=L[1];f.l2=L[2];f.e0=E[0];f.e1=E[1];f.e2=E[2];
 const Nc=[R[1]*L[2]-R[2]*L[1],R[2]*L[0]-R[0]*L[2],R[0]*L[1]-R[1]*L[0]],Ve=g3n([E[0]-V3.cx,E[1]-(V3.camH||0),E[2]+V3.cy]);
 f.cn=Math.max(0.3,Ve[0]*Nc[0]+Ve[1]*Nc[1]+Ve[2]*Nc[2]);f.ve=Ve;
 const Vh=g3n([Nc[0],0,Nc[2]]),nf=G3.pix.facings,kinds=['w','s','h'];f.dR=[];f.dF=[];f.ix=[];
 for(let face=0;face<4;face++){const Fv=face===1?[-Vh[0],0,-Vh[2]]:face===2?[R[0],0,R[2]]:face===3?[-R[0],0,-R[2]]:Vh,Rv=[-Fv[2],0,Fv[0]];
  f.dR[face]=Rv[0]*Nc[0]+Rv[2]*Nc[2];f.dF[face]=Fv[0]*Nc[0]+Fv[2]*Nc[2];
  for(let dd=0;dd<16;dd++){const Ft=g3n([((dd&4)?1:0)-((dd&8)?1:0),0,((dd&2)?1:0)-((dd&1)?1:0)]);let del=dd?Math.atan2(Fv[2]*Ft[0]-Fv[0]*Ft[2],Fv[0]*Ft[0]+Fv[2]*Ft[2]):0;del=Math.max(-1.6,Math.min(1.6,del));
   for(let k=0;k<3;k++){const a=del*G3PIXTURN[kinds[k]],c=Math.cos(a),sn=Math.sin(a),F=[Fv[0]*c+Fv[2]*sn,0,-Fv[0]*sn+Fv[2]*c],Rt=[-F[2],0,F[0]];
    const ph=Math.atan2(Vh[0]*Rt[0]+Vh[2]*Rt[2],Vh[0]*F[0]+Vh[2]*F[2]);f.ix[(face*16+dd)*3+k]=((Math.round(ph/(2*Math.PI/nf))%nf)+nf)%nf}}}
 return f}
// The armed walk (hud-rework 10-27): a unit holding a weapon walks with that arm at its side (its sheet's Armed frames,
// Gear3D.dm RmG3Armed, g.armed), so in the walk frames its hand is the standing frame's, moved with the body's bob
// (anchors' armed: per facing, the two walk frames' [dx, dy], armed_walk.py). Made once a sheet.
function g3armed(A){if(A.vvArmed)return A.vvArmed;const out=[];
 for(const f of ['S','N','E','W']){const V=A.views[f],B=A.armed&&A.armed[f];if(!V||!B){out.push(V);continue}
  out.push(V.map((v,k)=>{if(!k||k>2)return v;const b=B[k-1],h0=V[0].hand,f0=V[0].fistR||h0;return Object.assign({},v,{hand:[h0[0]+b[0],h0[1]+b[1]],fistR:[f0[0]+b[0],f0[1]+b[1]]})}))}
 return A.vvArmed=out}
function g3parse(t){const g=t.g3,A=G3.A[g.sheet];if(!A)return null;const PX=G3.pix,out={A,vv:g.armed&&A.armed?g3armed(A):[A.views.S,A.views.N,A.views.E,A.views.W],w:null,s:null,h:null};
 for(const [slot,kind] of [['w','weapon'],['s','shield'],['h','helmet']]){if(!g[slot])continue;const [st,tier]=g3split(g[slot]),name=kind+'.'+st,P=PX.pieces[name];if(!P)continue;
  out[slot]={P,tex:P.poses.map((c,i)=>g3ptex(name,tier,i,g.pal)),bow:st==='bow',idx:PX.index?'g3p-'+name.replace(/ /g,'_')+'-idx-0.png':null}}   /* idx: its rest pose's palette picture (g3edge) */
 return out}
// One card: the pose's cell of a strip, its anchor at (x, y, z), s world units an art pixel.
// lean: the piece tilted about its anchor, as a shear (the tangent of the angle: its top goes sideways, the anchor stays
// on the fist); sq: its height squashed, as when it swings toward the eye (g3swing)
function g3card(tex,C,i,nf,x,y,z,s,R,L,lean,sq){lean=lean||0;sq=sq||1;const H=C.h*s*sq,by=(C.h-C.ay)*s*sq,bx=(C.ax-C.w/2)*s+lean*by;let a=G3.cards.get(tex);if(!a){a=new VA();G3.cards.set(tex,a)}
 if(G3.rec)G3.rec.push(tex,a.length);const fu=C.fu||1/nf;a.v(x-R[0]*bx-L[0]*by,y-R[1]*bx-L[1]*by,z-R[2]*bx-L[2]*by,C.w/2*s,H,lean*H,(i+0.0005)*fu,(i+0.9995)*fu,1,1,1,1)}
// A carried weapon swings with the walk (hud-rework 10-27, the owner: "the weapons in the front view needs to animate
// dynamicly with the walking cycle", "needs to be more dynamic looking"): it tilts about the fist with the stride (the
// arms swing once a stride, two tiles, as the walk frames go 1,0,2,0), out and in seen from the front or the back, its
// tip forward and back seen from the side, and it follows on a spring, so it lags the hand a little, overshoots a touch
// and settles when the walk stops. Standing, it barely breathes. The shield sways less, the other way (the other arm).
// Fighting and working keep their own poses. Returns {w: the weapon's lean, q: its squash, s: the shield's lean}.
function g3swing(t,kd,face,V,now){if(!kd||kd.t0==null)return null;
 const walking=now-kd.t0<kd.dur&&(kd.tx!==kd.fx||kd.ty!==kd.fy),busy=t.act==='attack'||t.act==='work',amp=face<2?0.16:0.34;
 let tgt=0;if(busy)tgt=0;else if(walking){const st=(kd.n||0)+(now-kd.t0)/Math.max(0.12,kd.dur);tgt=amp*Math.sin(Math.PI*(st+0.25))}   /* a quarter stride ahead: with the spring's lag it peaks mid-frame, the arm at its furthest */else tgt=0.02*Math.sin(now*2.1+(kd.off||0)*6.3);
 let S=kd.g3sw;if(!S)S=kd.g3sw={a:0,v:0,t:now};const dt=Math.min(0.05,Math.max(0,now-S.t));S.t=now;
 if(dt>0){const ac=170*(tgt-S.a)-19*S.v;S.v+=ac*dt;S.a+=S.v*dt}   /* a quick spring, a little under-damped */
 // held with its tip a little in toward the body's middle seen from the front or the back (the owner, 10-27: "the weapons
 // tips need to move towards center a little"), a little forward seen from the side; the swing goes round that
 const side=face<2?(V.hand[0]<32?-1:1):(face===2?1:-1),base=face<2?-0.17:0.07,w=Math.tan(Math.max(-0.6,Math.min(0.6,S.a+base)))*side;
 return {w,q:face<2?1-0.06*Math.min(1,Math.abs(S.a)/amp):1,s:-0.45*Math.tan(S.a)*side}}
   /* fu: a cell's share of the strip (smooth strips are padded) */
// A carried piece's inner edge in each facing, row by row: its picture's column nearest the body's middle, the right-most
// held on the left of the picture and the left-most on the right (-1: nothing in that row). Read once from its rest
// pose's palette picture, when g3colour has it.
function g3edge(src,C){const E=G3.edge||(G3.edge=new Map());let e=E.get(src);if(e)return e;const c=G3.idx&&G3.idx.get(src);if(!c||!c.ok)return null;
 const img=c.img,W=img.width,h=img.height,cv=document.createElement('canvas');cv.width=W;cv.height=h;const cx=cv.getContext('2d');cx.drawImage(img,0,0);const p=cx.getImageData(0,0,W,h).data;
 const nf=G3.pix.facings,cw=Math.round(W*(C.fu||1/nf)),L=new Int16Array(nf*h).fill(-1),R=new Int16Array(nf*h).fill(-1);
 for(let i=0;i<nf;i++)for(let y=0;y<h;y++){let lo=-1,hi=-1;for(let x=0;x<cw;x++)if(p[(y*W+i*cw+x)*4+3]){if(lo<0)lo=x;hi=x}L[i*h+y]=hi;R[i*h+y]=lo}
 e={L,R,h};E.set(src,e);return e}
// Seen from the front, a weapon leaned in toward the body's middle (g3swing) stops short of the face: across the eyes
// (the brow and 7 pixels down) its inner edge stays outside the head's outline less 1.5 px. Where the walk frame's fist
// already holds it over the face (a spear in the fist at the body's middle) it leans no further in; outward is free.
// w: the lean as g3card takes it; returns it, kept off the face.
function g3offFace(Q,C,cell,V,sc,w,sq){let E=Q.edge;if(!E){E=g3edge(Q.idx,C);if(!E)return w;Q.edge=E}
 const H=V.head,hx=V.hand[0],hy=V.hand[1],left=hx<32,h=E.h,ed=left?E.L:E.R,lim=left?H.l+1.5:H.r-1.5,o=cell*h;let m=left?1e9:-1e9;
 for(let y=Math.ceil(H.brow),y1=H.brow+7;y<=y1;y++){const up=hy-y;if(up<=0)continue;const cy=Math.round(C.ay-up/(sc*sq));if(cy<0||cy>=h)continue;const e=ed[o+cy];if(e<0)continue;
  const b=(lim-hx-((left?e+1:e)-C.ax)*sc)/up;if(left?b<m:b>m)m=b}   /* the lean that brings this row's edge to the limit */
 return left?Math.min(w,Math.max(0,m)):Math.max(w,Math.min(0,m))}
function v3gearPix(t,kd,face,fi,LX,yA,LZ,hw,sh,sway,R,L,now){const f=g3frame(R,L);if(!f)return;
 let q=t.g3p;if(q===undefined)q=t.g3p=g3parse(t);if(!q)return;
 const A=q.A,V=q.vv[face][fi<3?fi:0],loc=A.loc,k=2*hw/64,nf=G3.pix.facings,Ve=f.ve,cn=f.cn,dR=f.dR[face],dF=f.dF[face],sc=A.scale||1,ib=(face*16+((t.dir||2)&15))*3,sw=q.w||q.s?g3swing(t,kd,face,V,now):null;
 // a point of the picture (art pixels), d pixels out toward the eye
 let u,a,d,x,y,z;
 if(q.h){const H=V.head,sx=loc.headw/11.5,s=k*(sx+loc.headd/9.5)/2;u=1-(H.top+10.5*sx)/64;a=hw*((H.l+H.r)/64-1)+sway*u;d=Math.max(1,dF*loc.head[1])*k/cn;
  g3card(q.h.tex[0],q.h.P.poses[0],f.ix[ib+2],nf,LX+R[0]*a+L[0]*sh*u+Ve[0]*d,yA+R[1]*a+L[1]*sh*u+Ve[1]*d,LZ+R[2]*a+L[2]*sh*u+Ve[2]*d,s,R,L)}
 if(q.s){let dp=dR*loc.shield[0]+dF*loc.shield[1];if(face===0||face===3)dp=Math.max(dp,G3FRONT.s);else if(face===1)dp=Math.min(dp,-G3FRONT.s);   /* in front of the body on the near arm (front and west pictures); seen from behind it is held out in front, beyond the body, which hides it */u=1-V.shield[1]/64;a=hw*(2*V.shield[0]/64-1)+sway*u;d=dp*k/cn;
  g3card(q.s.tex[0],q.s.P.poses[0],f.ix[ib+1],nf,LX+R[0]*a+L[0]*sh*u+Ve[0]*d,yA+R[1]*a+L[1]*sh*u+Ve[1]*d,LZ+R[2]*a+L[2]*sh*u+Ve[2]*d,k*sc,R,L,sw?sw.s:0)}
 if(q.w&&!(t.g3hide&&t.g3hide.w)){let dp=dR*loc.hand[0]+dF*loc.hand[1];if(face===1)dp=Math.min(dp,-G3FRONT.w*sc);else if(face!==3)dp=Math.max(dp,G3FRONT.w*sc);   /* seen from its back the body hides what it holds before it */u=1-V.hand[1]/64;a=hw*(2*V.hand[0]/64-1)+sway*u;d=dp*k/cn;
  let pose=0;if(kd&&(t.act==='attack'||t.act==='work')&&!q.w.bow){const ph=((now+(kd.off||0))%0.9)/0.9;pose=ph<0.12?0:ph<0.4?1:ph<0.5?2:ph<0.68?3:ph<0.8?2:0}
  if(!q.w.P.poses[pose])pose=0;const Cw=q.w.P.poses[pose];let wl=sw&&!pose?sw.w:0;if(wl&&!face&&q.w.idx)wl=g3offFace(q.w,Cw,f.ix[ib],V,sc,wl,sw.q);
  g3card(q.w.tex[pose],Cw,f.ix[ib],nf,LX+R[0]*a+L[0]*sh*u+Ve[0]*d,yA+R[1]*a+L[1]*sh*u+Ve[1]*d,LZ+R[2]*a+L[2]*sh*u+Ve[2]*d,k*sc,R,L,wl,sw&&!pose?sw.q:1)}}
// A unit kept as still records (the page's v3rcMake) keeps its cards too, and gives them back with the rest.
function g3key(t){const g=t.g3;if(!g)return undefined;let k=t.g3kk;if(k===undefined)k=t.g3kk=(g.w||'')+'|'+(g.s||'')+'|'+(g.h||'');return k}   /* once a server update */
function g3keep(R,t){if(!R)return R;R.g3k=g3key(t);const r=G3.rec;if(!t.g3||!r||!r.length){R.g3=null;return R}
 const n=r.length/2;if(!R.g3||R.g3.length<n*12)R.g3=new Float32Array(36);R.g3n=n;R.g3t=R.g3t||[];
 for(let i=0;i<n;i++){const tex=r[i*2],a=G3.cards.get(tex),o=r[i*2+1];R.g3t[i]=tex;for(let j=0;j<12;j++)R.g3[i*12+j]=a.f[o+j]}return R}
// A walking unit's kept records slide along its step (the page's v3walkEmit): its pieces' cards go with them.
function g3shift(R,dx,dy,dz){const F=R.g3;for(let i=0;i<R.g3n;i++){F[i*12]+=dx;F[i*12+1]+=dy;F[i*12+2]+=dz}}
function g3put(R){for(let i=0;i<R.g3n;i++){const tex=R.g3t[i];let a=G3.cards.get(tex);if(!a){a=new VA();G3.cards.set(tex,a)}a.copy(R.g3,i*12,12)}}
function v3gear3d(t,kd,face,fi,LX,yA,LZ,hw,sh,sway,right,LV,lv,now){
 let L0=t.g3last;if(!L0)L0=t.g3last=(kd&&kd.g3last)||{};if(kd)kd.g3last=L0;L0.at=now;   /* kept with its display entry too (each update is a new object, game.js g3rebind); when: in view */
 if(t.g3doll)return;   /* drawn as its doll (ragdoll.js): the doll carries its pieces */L0.LX=LX;L0.yA=yA;L0.LZ=LZ;L0.hw=hw;L0.sh=sh;L0.face=face;L0.fi=fi;L0.R=right;L0.L=LV;   /* the picture as last drawn (ragdoll.js) */
 if(!G3.ready){g3load();return}if(G3.pix)return v3gearPix(t,kd,face,fi,LX,yA,LZ,hw,sh,sway,right,LV,now);const g=t.g3,A=G3.A[g.sheet];if(!A)return;
 const vn='SNEW'[face]||'S',V=(A.views[vn]||A.views.S)[fi<3?fi:0],loc=A.loc,k=2*hw/64,R=right,L=LV;
 // the picture's plane: right, lean (up), and out toward the camera; the eye's line through the unit
 const Nc=[R[1]*L[2]-R[2]*L[1],R[2]*L[0]-R[0]*L[2],R[0]*L[1]-R[1]*L[0]],E3=V3.eye||[LX,yA+5,LZ+5];
 const Ve=g3n([E3[0]-LX,E3[1]-yA-sh*0.5,E3[2]-LZ]),cn=Math.max(0.3,Ve[0]*Nc[0]+Ve[1]*Nc[1]+Ve[2]*Nc[2]),Sv=[Ve[0]/cn-Nc[0],Ve[1]/cn-Nc[1],Ve[2]/cn-Nc[2]];
 const PX=G3.pix,cx={gpu:!PX&&g3gpu(),Nc,Sv,Ve,lv};
 const card=(px,py,depth)=>{const u=1-py/64,a=hw*(2*px/64-1)+sway*u,d=depth*k/cn;return [LX+R[0]*a+L[0]*sh*u+Ve[0]*d,yA+R[1]*a+L[1]*sh*u+Ve[1]*d,LZ+R[2]*a+L[2]*sh*u+Ve[2]*d]};
 // the way the picture faces, the way the unit faces, and a turn part way between
 const Vh=g3n([Nc[0],0,Nc[2]]),Fv=face===1?[-Vh[0],0,-Vh[2]]:face===2?[R[0],0,R[2]]:face===3?[-R[0],0,-R[2]]:Vh;
 const dd=t.dir||2,Ft=g3n([((dd&4)?1:0)-((dd&8)?1:0),0,((dd&2)?1:0)-((dd&1)?1:0)]);let del=Math.atan2(Fv[2]*Ft[0]-Fv[0]*Ft[2],Fv[0]*Ft[0]+Fv[2]*Ft[2]);del=Math.max(-1.6,Math.min(1.6,del));
 const turn0=kf=>{const a=del*kf,c=Math.cos(a),s=Math.sin(a),F=[Fv[0]*c+Fv[2]*s,0,-Fv[0]*s+Fv[2]*c];return [F,[-F[2],0,F[0]]]};
 const turn=(kf,kind)=>turn0(PX?G3PIXTURN[kind]:kf);
 // a pixel piece: the facing seen from the camera (0 in front, then round toward the wearer's right), its pose's
 // cell placed with its anchor on o, s world units an art pixel, as a picture parallel to the unit's
 const card3=(name,tier,pose,F,Rt,o,s)=>{const P=PX.pieces[name];if(!P)return;const C=P.poses[pose]||P.poses[0],nf=PX.facings;
  const ph=Math.atan2(Vh[0]*Rt[0]+Vh[2]*Rt[2],Vh[0]*F[0]+Vh[2]*F[2]),i=((Math.round(ph/(2*Math.PI/nf))%nf)+nf)%nf;
  const tex=g3ptex(name,tier,P.poses[pose]?pose:0,t.g3&&t.g3.pal);
  const bx=(C.ax-C.w/2)*s,by=(C.h-C.ay)*s;let a=G3.cards.get(tex);if(!a){a=new VA();G3.cards.set(tex,a)}
  a.v(o[0]-R[0]*bx-L[0]*by,o[1]-R[1]*bx-L[1]*by,o[2]-R[2]*bx-L[2]*by,C.w/2*s,C.h*s,0,i/nf+0.0005,(i+1)/nf-0.0005,1,1,1,1)};
 const Rv=[-Fv[2],0,Fv[0]],depth=(r,f)=>(Rv[0]*r+Fv[0]*f)*Nc[0]+(Rv[2]*r+Fv[2]*f)*Nc[2];
 const U=[0,1,0];
 // the helmet: its x to the wearer's left (the meshes are the same both sides), so the turn stays right-handed
 if(g.h){const [st,tier]=g3split(g.h);const [F,Rt]=turn(G3TURN.h,'h'),H=V.head,sx=loc.headw/11.5,sz=loc.headd/9.5;
  const o=card((H.l+H.r)/2,H.top+10.5*sx,PX?Math.max(1,depth(0,loc.head[1])):depth(0,loc.head[1]));if(PX)card3('helmet.'+st,tier,0,F,Rt,o,k*(sx+sz)/2);else g3emit(cx,'helmet.'+st,o,[-Rt[0],0,-Rt[2]],U,F,k*(sx+sz)/2,tier)}
 // the shield: on the near arm (front and west pictures) in front of the forearm, on the far one behind the body
 if(g.s){const [st,tier]=g3split(g.s);const [F,Rt]=turn(G3TURN.s,'s'),Z=g3n([F[0]-Rt[0],0,F[2]-Rt[2]]),X=[U[1]*Z[2]-U[2]*Z[1],U[2]*Z[0]-U[0]*Z[2],U[0]*Z[1]-U[1]*Z[0]],sc=k*(A.scale||1);
  let d=depth(loc.shield[0],loc.shield[1]);if(face===0||face===3)d=Math.max(d,G3FRONT.s);else if(face===1)d=Math.min(d,-G3FRONT.s);
  const o=card(V.shield[0],V.shield[1],d);if(PX){card3('shield.'+st,tier,0,F,Rt,o,sc)}else{o[0]+=Z[0]*1.3*sc;o[2]+=Z[2]*1.3*sc;g3emit(cx,'shield.'+st,o,X,U,Z,sc,tier)}}
 if(g.w){const [st,tier]=g3split(g.w);const [F,Rt]=turn(G3TURN.w,'w'),rest=G3.rest[st]||[0.58,0.59,0.57];
  const atk=kd&&(t.act==='attack'||t.act==='work')&&st!=='bow',ph=atk?((now+(kd.off||0))%0.9)/0.9:0;
  if(PX){let d=depth(loc.hand[0],loc.hand[1]);if(face===1)d=Math.min(d,-G3FRONT.w*(A.scale||1));else if(face!==3)d=Math.max(d,G3FRONT.w*(A.scale||1));
   // the pixel poses through a swing: at rest, wound up, half way, the blow, half way back, at rest
   const pose=!atk?0:ph<0.12?0:ph<0.4?1:ph<0.5?2:ph<0.68?3:ph<0.8?2:0;card3('weapon.'+st,tier,pose,F,Rt,card(V.hand[0],V.hand[1],d),k*(A.scale||1));return}
  // at rest as drawn; in an attack (or at work) up beside the head, then the blow, then back
  let a=rest,ws=0;if(atk){const e=x=>x*x*(3-2*x);
   if(ph<0.4)a=g3slerp(rest,G3WIND,e(ph/0.4));else if(ph<0.65){const x=e((ph-0.4)/0.25);a=g3slerp(G3WIND,G3STRIKE,x);ws=x}else{const x=e((ph-0.65)/0.35);a=g3slerp(G3STRIKE,rest,x);ws=1-x}}
  const Aw=g3n([Rt[0]*a[0]+F[0]*a[1],a[2],Rt[2]*a[0]+F[2]*a[1]]);
  const e0=st==='bow'?F:[F[0]*0.8+Rt[0]*0.6,-1.2*ws,F[2]*0.8+Rt[2]*0.6],ed=e0[0]*Aw[0]+e0[1]*Aw[1]+e0[2]*Aw[2];let Ew=g3n([e0[0]-Aw[0]*ed,e0[1]-Aw[1]*ed,e0[2]-Aw[2]*ed]);
  const Nw=[Aw[1]*Ew[2]-Aw[2]*Ew[1],Aw[2]*Ew[0]-Aw[0]*Ew[2],Aw[0]*Ew[1]-Aw[1]*Ew[0]],sc=k*(A.scale||1);
  // in front of the glove, unless the right hand is on the far side (the west picture)
  let d=depth(loc.hand[0],loc.hand[1]);if(face===1)d=Math.min(d,-G3FRONT.w*(A.scale||1));else if(face!==3)d=Math.max(d,G3FRONT.w*(A.scale||1));
  g3emit(cx,'weapon.'+st,card(V.hand[0],V.hand[1],d),Aw,Ew,Nw,sc,tier)}}
// The pieces are drawn after the "hidden unit" silhouettes (a piece in front of its own picture is not a wall
// hiding it), depth-tested against the pictures as usual; then the lists are emptied for the next frame. Their
// colours come from the palette (a texture), so the ground's painted detail, for untextured faces, leaves them be.
function g3draw(){if(typeof bsFrame==='function')bsFrame();g3drawPieces();if(typeof mfFrame==='function')mfFrame()}   /* the world bosses first (bosses.js: plain lit triangles, before the instanced pieces) */   /* the magic pieces' effects (magicfx.js) last: lights over what is drawn */
function g3drawPieces(){const gl=V3.gl,L=V3.loc,x=V3.ix;
 if(typeof rdFrame==='function')rdFrame();   /* ragdolls, loose pieces, arrows (ragdoll.js): their pieces join the records drawn below */
 for(const [k,a] of G3.cards){if(!a.length)continue;const e=v3tex(k);if(e&&e.ok)v3drawInst(a,1,e);a.length=0}
 const a=G3.va;if(a&&a.length){gl.uniform1f(L.gon,0);gl.bindBuffer(gl.ARRAY_BUFFER,V3.dyn);v3up(a);v3draw(V3.dyn,a.length/12,null);gl.uniform1f(L.gon,V3.gtex&&V3.gtex.ok&&V3.etex&&V3.etex.ok&&V3.stex&&V3.stex.ok?1:0);a.length=0}
 if(!x||!G3.B)return;let any=false;for(const r of G3.I.values())if(r.length){any=true;break}if(!any)return;
 const U=V3.iU;gl.uniform1f(L.inst,5);gl.uniform3f(L.iright,U.r[0],U.r[1],U.r[2]);gl.uniform3f(L.ilean,U.l[0],U.l[1],U.l[2]);
 gl.activeTexture(gl.TEXTURE0);gl.bindTexture(gl.TEXTURE_2D,G3.pal);gl.uniform1i(L.t,0);gl.uniform1f(L.useTex,1);
 gl.disableVertexAttribArray(L.col);gl.vertexAttrib4f(L.col,1,1,1,1);
 for(const [k,r] of G3.I){if(!r.length)continue;const b=G3.B[k];if(!b){r.length=0;continue}
  gl.bindBuffer(gl.ARRAY_BUFFER,b.buf);gl.vertexAttribPointer(L.p,3,gl.FLOAT,false,32,0);gl.enableVertexAttribArray(L.p);gl.vertexAttribPointer(L.n,3,gl.FLOAT,false,32,12);gl.enableVertexAttribArray(L.n);gl.vertexAttribPointer(L.uv,2,gl.FLOAT,false,32,24);gl.enableVertexAttribArray(L.uv);
  gl.bindBuffer(gl.ARRAY_BUFFER,V3.ibuf);gl.bufferData(gl.ARRAY_BUFFER,r.f.subarray(0,r.length),gl.STREAM_DRAW);
  gl.vertexAttribPointer(L.i0,4,gl.FLOAT,false,48,0);gl.vertexAttribPointer(L.i1,4,gl.FLOAT,false,48,16);gl.vertexAttribPointer(L.i2,4,gl.FLOAT,false,48,32);
  for(const l of [L.i0,L.i1,L.i2]){gl.enableVertexAttribArray(l);x.vertexAttribDivisorANGLE(l,1)}
  x.drawArraysInstancedANGLE(gl.TRIANGLES,0,b.n,r.length/12);
  for(const l of [L.i0,L.i1,L.i2]){x.vertexAttribDivisorANGLE(l,0);gl.disableVertexAttribArray(l)}r.length=0}
 gl.enableVertexAttribArray(L.col);gl.uniform1f(L.inst,0)}

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

// Weapon skill animations on the sprite units (art/gear3d; the animation arena), one for each of the game's weapon
// skills (CombatSkills.dm): Sword (slash, thrust), Axe (chop), Mace (smash; a warhammer's blow can launch), Spear
// (thrust; a halberd chops), Dagger (two quick stabs), Bow (ragdoll.js rdShoot), Unarmed (jab and cross), Claw (a
// double rake), Shield (bash, block), Armour (blows glance off), Throwing (a spear, knife or axe thrown at the
// target), and Defence's parry and dodge. Each plays on the unit's own sprite as a standing doll (ragdoll.js): its
// arms, torso and weapon follow keyframes (a wind-up, the blow, the follow-through), the weapon's edge leaves a trail
// through the blow, and at the blow the target reacts: it flinches or, killed, falls as the blow decides; a defender
// blocks, parries (sparks) or dodges (a miss).
//
// Keyframe angles are in a unit's own terms: 0 straight at its target, +pi/2 up, -pi/2 down (a hanging arm), pi
// behind it. R is the weapon arm, L the other (the shield arm); u the upper arm, l the forearm; W the weapon's own
// angle (left out, it follows the forearm); lean leans the body toward the target. The rest are in the unit's own leg
// lengths, so a dwarf's stride is a dwarf's: lunge moves the body in, step puts the front foot down that far ahead of
// where it stood (left out, it goes with the lunge), back moves the back foot back, crouch sinks the hips. The feet
// stay planted (but kick: the front foot lifted that far off the ground, in leg lengths, as GOA's kick; Hidden Clans): the
// hips sink as far as the stance needs for both knees to stay bent, and shift against the lean so
// the weight stays between the feet.
const SK={defs:{
 slash:{keys:[[0],[0.16,{Ru:2.0,Rl:2.5,W:2.5,Lu:-0.9,Ll:-0.3,lean:-0.1,back:0.15,crouch:0.08}],[0.3,{Ru:0.35,Rl:0.15,W:0.1,Lu:-1.1,Ll:-0.6,lean:0.18,lunge:0.35,step:0.6,back:0.1,crouch:0.2}],
  [0.42,{Ru:-0.25,Rl:-0.4,W:-0.35,lean:0.12,lunge:0.35,step:0.6,back:0.1,crouch:0.16}],[0.72]],   /* over the shoulder, level through the target, low and forward after */hit:[0.3],trail:[0.18,0.42],death:'fall',maim:'armcut'},
 thrust:{keys:[[0],[0.18,{Ru:-2.5,Rl:0.0,W:0.06,Lu:-0.6,Ll:-0.2,lean:-0.08,back:0.25,crouch:0.12}],[0.3,{Ru:-0.1,Rl:0.0,W:0.0,lean:0.15,lunge:0.5,step:0.85,back:0.2,crouch:0.26}],[0.46,{Ru:-0.55,Rl:-0.3,W:0.1,lean:0.08,lunge:0.4,step:0.85,back:0.2,crouch:0.2}],[0.74]],hit:[0.3],trail:[0.2,0.34],death:'fall'},
 chop:{keys:[[0],[0.26,{Ru:2.6,Rl:2.9,W:2.4,lean:-0.16,back:0.2,crouch:0.06}],[0.4,{Ru:-0.4,Rl:-0.7,W:-0.9,lean:0.3,lunge:0.35,step:0.6,back:0.15,crouch:0.32}],[0.62,{Ru:-0.5,Rl:-0.8,W:-1.0,lean:0.25,lunge:0.35,step:0.6,back:0.15,crouch:0.26}],[0.92]],hit:[0.4],trail:[0.28,0.44],two:true,death:'armoff',deaths:['armoff','armoff','fall'],maim:'armcut'},
 smash:{keys:[[0],[0.24,{Ru:2.4,Rl:2.7,W:2.0,lean:-0.14,back:0.2,crouch:0.06}],[0.38,{Ru:-0.3,Rl:-0.6,W:-1.2,lean:0.3,lunge:0.35,step:0.6,back:0.15,crouch:0.34}],[0.62,{Ru:-0.4,Rl:-0.7,W:-1.25,lean:0.24,lunge:0.35,step:0.6,back:0.15,crouch:0.28}],[0.9]],hit:[0.38],trail:[0.26,0.42],dust:true,death:'flying'},
 launch:{keys:[[0],[0.34,{Ru:2.7,Rl:3.0,W:2.5,lean:-0.22,back:0.3,crouch:0.18}],[0.5,{Ru:-0.2,Rl:-0.5,W:-1.15,lean:0.36,lunge:0.45,step:0.75,back:0.25,crouch:0.4}],[0.78,{Ru:-0.3,Rl:-0.6,W:-1.2,lean:0.3,lunge:0.45,step:0.75,back:0.25,crouch:0.34}],[1.1]],hit:[0.5],trail:[0.36,0.54],two:true,dust:true,death:'hammer',always:'hammer'},
 sweep:{keys:[[0],[0.24,{Ru:1.4,Rl:2.2,W:2.6,lean:-0.12,back:0.15,crouch:0.1}],[0.4,{Ru:-0.6,Rl:-0.4,W:-0.5,lean:0.24,lunge:0.3,step:0.55,back:0.15,crouch:0.28}],[0.6,{Ru:-0.9,Rl:-0.8,W:-0.9,lean:0.18,lunge:0.3,step:0.55,back:0.15,crouch:0.24}],[0.9]],hit:[0.4],trail:[0.26,0.44],two:true,death:'spin',deaths:['spin','legoff'],maim:'legcut'},
 stab:{keys:[[0],[0.07,{Ru:-2.4,Rl:0.1,W:0.0,back:0.1,crouch:0.1}],[0.14,{Ru:-0.2,Rl:0.0,W:0.0,lean:0.12,lunge:0.25,step:0.45,back:0.1,crouch:0.16}],[0.22,{Ru:-2.4,Rl:0.1,W:0.0,lunge:0.12,step:0.45,back:0.1,crouch:0.12}],[0.3,{Ru:-0.15,Rl:0.0,W:0.0,lean:0.14,lunge:0.3,step:0.5,back:0.1,crouch:0.18}],[0.5]],hit:[0.14,0.3],trail:[0.08,0.32],death:'crumple'},
 punch:{keys:[[0],[0.08,{Lu:-0.15,Ll:0.0,lean:0.08,lunge:0.2,step:0.4,back:0.1,crouch:0.12}],[0.16,{Lu:-1.2,Ll:-0.5,lunge:0.1,step:0.4,back:0.1,crouch:0.1}],[0.25,{Ru:-0.1,Rl:0.0,lean:0.16,lunge:0.35,step:0.5,back:0.1,crouch:0.16}],[0.37,{Ru:-1.2,Rl:-0.6,lunge:0.2,step:0.5,back:0.1,crouch:0.12}],[0.56]],hit:[0.08,0.25],bare:true,death:'fall'},
 jab:{keys:[[0],[0.08,{Lu:-0.15,Ll:0.0,lean:0.08,lunge:0.2,step:0.4,back:0.1,crouch:0.12}],[0.2,{Lu:-1.2,Ll:-0.5,lunge:0.1,step:0.4,back:0.1,crouch:0.1}],[0.36]],hit:[0.08],bare:true,death:'fall'},   /* the punch's first half: the lead hand (Hidden Clans' combo) */
 cross:{keys:[[0],[0.06,{Lu:-1.2,Ll:-0.5,lean:0.04,lunge:0.1,step:0.4,back:0.1,crouch:0.12}],[0.14,{Ru:-0.1,Rl:0.0,lean:0.16,lunge:0.35,step:0.5,back:0.1,crouch:0.16}],[0.28,{Ru:-1.2,Rl:-0.6,lunge:0.2,step:0.5,back:0.1,crouch:0.12}],[0.44]],hit:[0.14],bare:true,death:'fall'},   /* its second half: the rear hand driven through */
 kick:{keys:[[0],[0.1,{Ru:-0.9,Rl:0.9,Lu:-0.9,Ll:0.9,kick:0.55,step:0.3,lean:-0.1,back:0.1,crouch:0.04}],[0.2,{Ru:-1.4,Rl:-0.6,Lu:-0.7,Ll:0.8,kick:1.4,step:0.9,lean:-0.35,back:0.15}],
  [0.3,{Ru:-1.4,Rl:-0.6,Lu:-0.7,Ll:0.8,kick:1.3,step:0.85,lean:-0.3,back:0.15}],[0.42,{Ru:-0.9,Rl:0.6,Lu:-0.9,Ll:0.8,kick:0.4,step:0.35,lean:-0.05,back:0.1}],[0.6]],   /* GOA's KickA (Hidden Clans): the knee up in a guard, then the leg out high and straight, the body leaning back */
  hit:[0.2],bare:true,death:'fall',deaths:['fall','spin']},
 claw:{keys:[[0],[0.15,{Ru:1.8,Rl:2.4,Lu:1.7,Ll:2.3,lean:-0.1,back:0.15,crouch:0.16}],[0.3,{Ru:-0.7,Rl:-1.1,Lu:-0.6,Ll:-1.0,lean:0.22,lunge:0.4,step:0.65,back:0.15,crouch:0.3}],[0.6]],hit:[0.3],bare:true,claw:true,death:'spin',maim:'armcut'},
 bash:{keys:[[0],[0.15,{Lu:-2.4,Ll:0.3,lean:-0.08,back:0.2,crouch:0.18}],[0.27,{Lu:0.0,Ll:0.0,lean:0.22,lunge:0.55,step:0.85,back:0.15,crouch:0.24}],[0.55]],hit:[0.27],shield:true,death:'flying',knock:true},
 throw:{keys:[[0],[0.26,{Ru:2.3,Rl:2.7,W:2.6,Lu:0.3,Ll:0.3,lean:-0.16,back:0.35,crouch:0.14}],[0.38,{Ru:0.5,Rl:0.3,W:0.3,Lu:-0.6,Ll:-0.4,lean:0.2,lunge:0.3,step:0.55,back:0.3,crouch:0.2}],[0.52,{Ru:-0.4,Rl:-0.6,lean:0.1,lunge:0.25,step:0.55,back:0.3,crouch:0.12}],[0.75]],release:0.38,ranged:true,death:'fall'},
 // a staff's spell (magicfx.js mfCast): raised back over the shoulder, then thrust at the target, the free hand thrown
 // forward; the staff's own pixel effect leaves its head at the thrust
 cast:{keys:[[0],[0.24,{Ru:1.9,Rl:2.4,W:1.65,Lu:0.8,Ll:1.3,lean:-0.12,back:0.2,crouch:0.06}],[0.42,{Ru:0.35,Rl:0.25,W:0.45,Lu:0.15,Ll:0.05,lean:0.15,lunge:0.2,step:0.4,back:0.15,crouch:0.12}],
  [0.62,{Ru:0.4,Rl:0.3,W:0.5,Lu:0.2,Ll:0.1,lean:0.1,lunge:0.18,step:0.4,back:0.15,crouch:0.1}],[0.95]],release:0.42,ranged:true,spell:true,death:'fall'},
 // the game's own weapon moves (WeaponSkills.dm, the user 2026-10-25: "lets do it"), played when the server says a blow
 // was one (Hits.dm "mv", game.js g3hit): each with the unit's own weapon. Their passives (a burning edge, frostbite...)
 // ride on the plain swings with their own pixel effects.
 lunge:{keys:[[0],[0.22,{Ru:-2.6,Rl:0.0,W:0.06,Lu:-0.4,Ll:-0.1,lean:-0.12,back:0.3,crouch:0.18}],[0.36,{Ru:-0.05,Rl:0.0,W:0.0,Lu:-1.3,Ll:-0.5,lean:0.3,lunge:1.0,step:1.35,back:0.25,crouch:0.4}],
  [0.6,{Ru:-0.3,Rl:-0.15,W:0.05,lean:0.22,lunge:0.9,step:1.35,back:0.25,crouch:0.34}],[0.95]],hit:[0.36],trail:[0.24,0.4],death:'fall'},   /* a long step in, the point driven home */
 heavyblow:{keys:[[0],[0.32,{Ru:2.8,Rl:3.0,W:2.7,Lu:2.6,Ll:2.9,lean:-0.2,back:0.25,crouch:0.1}],[0.46,{Ru:-0.35,Rl:-0.6,W:-0.8,Lu:-0.3,Ll:-0.5,lean:0.34,lunge:0.4,step:0.7,back:0.2,crouch:0.36}],
  [0.75,{Ru:-0.45,Rl:-0.7,W:-0.95,lean:0.28,lunge:0.4,step:0.7,back:0.2,crouch:0.3}],[1.05]],hit:[0.46],trail:[0.34,0.5],two:true,dust:true,death:'flying',maim:'armcut'},   /* both hands, high over the head and down */
 riposte:{keys:[[0],[0.1,{Ru:0.4,Rl:1.5,W:1.75,back:0.25,crouch:0.16}],[0.9,{Ru:0.5,Rl:1.6,W:1.8,lean:-0.04,back:0.28,crouch:0.2}],[1.15]],self:true},   /* its guard up and held: what strikes at it is parried and struck back */
 cleave:{keys:[[0],[0.28,{Ru:1.2,Rl:1.9,W:2.4,Lu:1.0,Ll:1.6,lean:-0.18,back:0.2,crouch:0.14}],[0.44,{Ru:-0.5,Rl:-0.3,W:-0.3,Lu:-0.6,Ll:-0.4,lean:0.3,lunge:0.35,step:0.6,back:0.15,crouch:0.32}],
  [0.66,{Ru:-1.1,Rl:-0.9,W:-1.0,Lu:-1.0,Ll:-0.8,lean:0.2,lunge:0.35,step:0.6,back:0.15,crouch:0.26}],[1.0]],hit:[0.44],trail:[0.3,0.66],two:true,death:'spin',deaths:['spin','armoff'],maim:'armcut'},   /* a wide two-handed sweep through all round the foe */
 skullcracker:{keys:[[0],[0.3,{Ru:2.9,Rl:3.1,W:2.6,Lu:1.2,Ll:1.6,lean:-0.24,back:0.3,crouch:0.3}],[0.44,{Ru:-0.2,Rl:-0.55,W:-1.3,Lu:-0.7,Ll:-0.4,lean:0.4,lunge:0.4,step:0.7,back:0.2,crouch:0.42}],
  [0.7,{Ru:-0.3,Rl:-0.65,W:-1.3,lean:0.32,lunge:0.4,step:0.7,back:0.2,crouch:0.36}],[1.0]],hit:[0.44],trail:[0.32,0.48],dust:true,death:'crumple'},   /* crouched, then up and over onto the head */
 skewer:{keys:[[0],[0.24,{Ru:-2.7,Rl:0.0,W:0.05,Lu:-1.6,Ll:-0.6,lean:-0.14,back:0.35,crouch:0.18}],[0.38,{Ru:-0.05,Rl:0.0,W:0.0,Lu:-0.5,Ll:-0.2,lean:0.28,lunge:0.8,step:1.1,back:0.3,crouch:0.34}],
  [0.62,{Ru:-0.15,Rl:0.0,W:0.02,lean:0.24,lunge:0.75,step:1.1,back:0.3,crouch:0.3}],[0.95]],hit:[0.38],trail:[0.26,0.42],two:true,death:'flying'},   /* driven through, into the one behind */
 flurry:{keys:[[0],[0.06,{Ru:-2.4,Rl:0.1,W:0.0,back:0.1,crouch:0.12}],[0.12,{Ru:-0.2,Rl:0.0,W:0.0,lean:0.14,lunge:0.25,step:0.45,back:0.1,crouch:0.18}],[0.18,{Ru:-2.3,Rl:0.1,W:0.0,lunge:0.15,step:0.45,back:0.1,crouch:0.14}],
  [0.24,{Ru:0.1,Rl:0.0,W:0.0,lean:0.16,lunge:0.3,step:0.5,back:0.1,crouch:0.2}],[0.3,{Ru:-2.4,Rl:0.1,W:0.0,lunge:0.18,step:0.5,back:0.1,crouch:0.15}],[0.36,{Ru:-0.35,Rl:0.0,W:0.0,lean:0.16,lunge:0.32,step:0.5,back:0.1,crouch:0.2}],
  [0.42,{Ru:-2.3,Rl:0.1,W:0.0,lunge:0.2,step:0.5,back:0.1,crouch:0.15}],[0.48,{Ru:-0.1,Rl:0.0,W:0.0,lean:0.18,lunge:0.35,step:0.5,back:0.1,crouch:0.22}],[0.7]],hit:[0.12,0.24,0.36,0.48],trail:[0.06,0.5],death:'crumple'},   /* four quick stabs */
 runebolt:{keys:[[0],[0.26,{Ru:1.6,Rl:2.2,W:2.2,Lu:0.6,Ll:1.0,lean:-0.1,back:0.2,crouch:0.08}],[0.44,{Ru:0.1,Rl:0.05,W:0.05,Lu:-0.4,Ll:-0.2,lean:0.14,lunge:0.25,step:0.45,back:0.15,crouch:0.14}],
  [0.7,{Ru:0.1,Rl:0.05,W:0.05,lean:0.1,lunge:0.2,step:0.45,back:0.15,crouch:0.12}],[1.0]],release:0.44,ranged:true,spell:true,death:'fall'},   /* the rune sword raised, then pointed: the bolt leaves its point */
 firewave:{keys:[[0],[0.26,{Ru:1.3,Rl:2.0,W:2.5,lean:-0.14,back:0.2,crouch:0.18}],[0.42,{Ru:-0.9,Rl:-0.6,W:-0.8,lean:0.3,lunge:0.3,step:0.6,back:0.2,crouch:0.42}],
  [0.66,{Ru:-1.2,Rl:-1.0,W:-1.1,lean:0.24,lunge:0.3,step:0.6,back:0.2,crouch:0.36}],[1.0]],hit:[0.42],trail:[0.28,0.66],death:'fall'},   /* a low wide sweep that throws the fire on */
 frozenhamstring:{keys:[[0],[0.26,{Ru:2.2,Rl:2.6,W:2.2,lean:-0.12,back:0.2,crouch:0.1}],[0.42,{Ru:-1.0,Rl:-1.2,W:-1.4,lean:0.4,lunge:0.35,step:0.65,back:0.18,crouch:0.48}],
  [0.68,{Ru:-1.1,Rl:-1.3,W:-1.5,lean:0.32,lunge:0.35,step:0.65,back:0.18,crouch:0.42}],[1.0]],hit:[0.42],trail:[0.3,0.5],two:true,death:'fall',deaths:['legoff','fall'],maim:'legcut'},   /* down low at the legs */
 calllightning:{keys:[[0],[0.3,{Ru:2.9,Rl:3.0,W:1.6,Lu:1.0,Ll:1.4,lean:-0.18,back:0.15,crouch:0.04}],[0.7,{Ru:3.0,Rl:3.05,W:1.6,Lu:1.1,Ll:1.5,lean:-0.2,back:0.15,crouch:0.04}],
  [0.86,{Ru:0.2,Rl:0.1,W:0.1,Lu:-0.4,Ll:-0.2,lean:0.16,lunge:0.25,step:0.45,back:0.15,crouch:0.14}],[1.2]],release:0.86,ranged:true,spell:true,death:'stiff'},   /* the storm spear held up to the sky, then down at the foe */
 bonespear:{keys:[[0],[0.28,{Ru:2.3,Rl:2.7,W:2.0,Lu:0.4,Ll:0.5,lean:-0.18,back:0.3,crouch:0.12}],[0.44,{Ru:0.4,Rl:0.2,W:0.4,Lu:-0.6,Ll:-0.4,lean:0.22,lunge:0.3,step:0.55,back:0.25,crouch:0.2}],
  [0.7,{Ru:0.3,Rl:0.2,W:0.35,lean:0.12,lunge:0.25,step:0.55,back:0.25,crouch:0.14}],[1.0]],release:0.44,ranged:true,spell:true,death:'fall'},   /* thrown from the staff like a spear */
 raiseskeleton:{keys:[[0],[0.4,{Ru:2.9,Rl:3.0,W:1.6,Lu:2.6,Ll:2.9,lean:-0.12,crouch:0.05}],[1.2,{Ru:2.95,Rl:3.05,W:1.6,Lu:2.7,Ll:3.0,lean:-0.14,crouch:0.05}],[1.6]],self:true,spell:true},   /* both hands raise the staff: the dead rise */
 // getting up from the ground (skGetUp): tilt is how far the body still lies (1 flat, 0 upright). It pushes up on one
 // hand with its knees drawn in, comes up to a kneel with one foot forward, then stands.
 getup:{keys:[[0,{tilt:1,crouch:0.1,Ru:-1.3,Rl:-1.3,Lu:-1.4,Ll:-1.4}],[0.35,{tilt:0.6,crouch:0.55,Ru:-2.1,Rl:-1.9,Lu:-0.8,Ll:-0.3,lean:0.3,back:0.1}],
  [0.8,{tilt:0.2,crouch:0.5,Ru:-1.7,Rl:-1.6,Lu:-0.6,Ll:-0.2,lean:0.15,step:0.35,back:0.1}],[1.25,{tilt:0,crouch:0.06,lean:0.02}],[1.5]],tilt:true},
 // the defender's side: started so the guard is up as the blow lands
 block:{keys:[[0],[0.12,{Lu:0.15,Ll:1.1,lean:-0.05,step:0,back:0.35,crouch:0.24}],[0.55,{Lu:0.15,Ll:1.1,lean:-0.08,step:0,back:0.35,crouch:0.24}],[0.8]],shield:true},
 parry:{keys:[[0],[0.12,{Ru:0.4,Rl:1.5,W:1.75,step:0,back:0.25,crouch:0.16}],[0.45,{Ru:0.5,Rl:1.6,W:1.8,step:0,back:0.25,crouch:0.16}],[0.7]]},
 dodge:{keys:[[0],[0.14,{lean:-0.4,lunge:-0.6,Ru:-1.0,Lu:-1.0,step:-0.15,back:0.9,crouch:0.2}],[0.42,{lean:-0.3,lunge:-0.55,step:-0.15,back:0.9,crouch:0.14}],[0.7]]},
},acts:[],shots:[],trails:[]};
// the weapons each skill is done with (the arena lends one when the unit holds none of them)
const SKWEAPON={slash:['arming sword','longsword','scimitar','rune sword','flame sword','void blade','soul eater'],thrust:['arming sword','longsword','scimitar','spear','rune sword','flame sword','storm spear','soul eater','bloodwhisker'],
 chop:['battle axe','hand axe','halberd','frost axe'],smash:['mace','morning star','warhammer','holy mace'],launch:['warhammer'],sweep:['halberd'],stab:['dagger'],throw:['spear','dagger','hand axe'],
 parry:['arming sword','longsword','scimitar','spear','halberd','rune sword','flame sword','void blade','storm spear','soul eater','bloodwhisker'],
 mine:['pickaxe'],chop:['hand axe','battle axe'],build:['hammer'],smith:['hammer'],fish:['fishing rod'],spearfish:['harpoon','spear'],till:['spade'],
 cast:['crystal staff','orb staff','skull staff','flame staff','nature staff','dragon staff','spider staff']};   /* the enchanted weapons (magicfx.js) do their base weapon's skills */
const SKLEND={till:'spade:wood',spearfish:'harpoon:iron',mine:'pickaxe:iron',chop:'hand axe:iron',build:'hammer:iron',smith:'hammer:iron',fish:'fishing rod:wood',cast:'crystal staff',slash:'arming sword:iron',thrust:'spear:iron',chop:'battle axe:iron',smash:'mace:iron',launch:'warhammer:iron',sweep:'halberd:iron',stab:'dagger:iron',throw:'spear:iron',parry:'arming sword:iron'};
const SKTWO=new Set(['spade','harpoon','battle axe','warhammer','halberd','spear','pickaxe','longsword','rune sword','frost axe','storm spear','bloodwhisker']);

// The unit's weapon for a skill: its own if it fits, else one lent for the skill (given back after).
function skGear(t,skill,want){const g=t.g3,need=want?[want.split(':')[0]]:SKWEAPON[skill],have=g.w?g.w.split(':')[0]:null;let lent=null;
 if(need&&!(have&&need.includes(have))){lent={w:g.w};t.g3={...g,w:want||SKLEND[skill]}}
 if((skill==='bash'||skill==='block')&&!g.s){lent=lent||{};lent.s=null;t.g3={...t.g3,s:'round:iron'}}
 if(lent){t.g3p=undefined;t.g3kk=undefined;const kd=V3.disp.get(t.key);if(kd&&kd.rc)kd.rc.ep=null}return lent}
function skFace(t,target){const dx=target.x-t.x,dy=target.y-t.y;t.dir=Math.abs(dx)>=Math.abs(dy)?(dx>=0?4:8):(dy>=0?1:2);const kd=V3.disp.get(t.key);if(kd&&kd.rc)kd.rc.ep=null}
// A melee blow needs the target in reach: the striker steps to the tile beside it, on its own side.
function skReach(t,target){if(typeof G3G!=='undefined'&&G3G.game)return;   /* in the game the server places it (a two-tile move reaches with its lunge) */const dx=target.x-t.x,dy=target.y-t.y;if(Math.max(Math.abs(dx),Math.abs(dy))<=1)return;
 if(Math.abs(dx)>=Math.abs(dy)){t.x=target.x-Math.sign(dx);t.y=target.y}else{t.x=target.x;t.y=target.y-Math.sign(dy)}t.dx=t.x;t.dy=t.y}

// Play a skill: t at target (for a defence, the striker it guards against). opt: {kill, guard: 'block'|'parry'|'dodge'|'armour'}
function skAct(t,skill,target,opt){opt=opt||{};const D=SK.defs[skill];if(!D||!t.g3last)return null;if(t.dead&&!opt.death)return null;   /* the dead act out only their death (deaths.js rdDie): a guard or swing timed before it fell (the setTimeouts below) took over the death act and stopped its fall, so it swayed till g3rebind felled it or stood (the owner, 10-28: "Death animation loop") */if(!RD.rig){rdLoad();return null}
 if(target&&target!==t){skFace(t,target);if(!D.ranged&&!['block','parry','dodge'].includes(skill))skReach(t,target)}
 if(opt.at){const dx=opt.at[0]-t.x,dy=-opt.at[2]-t.y;t.dir=Math.abs(dx)>=Math.abs(dy)?(dx>=0?4:8):(dy>=0?1:2);const kd=V3.disp.get(t.key);if(kd&&kd.rc)kd.rc.ep=null}   /* work at a spot: turned to it (work.js) */
 const lent=skGear(t,skill,opt.weapon),A={t,skill,D,target,opt,lent,t0:performance.now()/1000,doll:null,hits:0,released:false,trail:[]};
 // the defender's guard goes up so it meets the blow
 // a throw: a shield comes up as it leaves the hand
 if(target&&(opt.guard==='block'||opt.guard==='dodge')&&D.release!=null&&!D.spell){const gd=opt.guard;setTimeout(()=>{if(target.g3last&&V3.things.includes(target))skAct(target,gd,t,{})},Math.max(0,(0.12+D.release-0.3)*1000/(RD.slow||1)))}
 if(target&&opt.guard&&opt.guard!=='armour'&&D.hit){const g=opt.guard;setTimeout(()=>{if(target.g3last&&V3.things.includes(target))skAct(target,g,t,{})},Math.max(0,(0.12+D.hit[0]-0.18)*1000/(RD.slow||1)))}
 if(!opt.doll)for(const B of SK.acts.concat(SK.pending||[]))if(B.t===t&&B!==A&&!B.replaced){B.replaced=true;B.opt.loop=false;B.opt.then=null;if(B.doll&&B.doll.alive&&!B.doll.done)A.opt.doll=B.doll}   /* one move a unit: the new one takes over */
 (SK.stepping?SK.pending:SK.acts).push(A);return A}   /* started from inside a move's step (its then): joins after the step */

// The weapon slung on its back, slanting over the shoulder, the hilt up behind its head like a quiver's arrows (and,
// stowShield, the shield on its back too): riding on the body, behind it as seen from in front and side on, over it
// as seen from behind.
function skStow(d,shield){const L=d.limbs,nk=L.head?L.head.root0:[d.pel0[0],d.pel0[1]+0.4],up=nk[1]-d.pel0[1],back=d.fl==='N'?1:-1,side=d.fl==='W'?-1:1;
 for(const a of d.gear){if(a.stowed||!(a.slot==='w'||(shield&&a.slot==='s')))continue;a.stowed=true;a.part='torso';a.live=false;
  const sw=a.slot==='w',tilt=sw?side*0.65:0,ang=Math.PI/2+tilt;a.wrist=tilt;
  a.p=sw?[-side*0.18*up,up*0.55,back*0.035]:[0,up*0.42,back*0.03];a.X=[Math.cos(ang),Math.sin(ang),0];a.Y=[-Math.sin(ang),Math.cos(ang),0];a.Z=[0,0,1]}}
const skAbs=(a,sg)=>sg>0?a:Math.PI-a;
const SKZERO=new Set(['lean','lunge','crouch','step','back','shake','kick']);   /* these ease in from and out to nothing */
function skKey(D,b,name){const K=D.keys;let i=0;while(i<K.length-1&&K[i+1][0]<=b)i++;const k0=K[i],k1=K[Math.min(i+1,K.length-1)];
 let v0=k0[1]&&k0[1][name],v1=k1[1]&&k1[1][name];if(SKZERO.has(name)){if(v0==null)v0=0;if(v1==null)v1=0}
 if(k1===k0||b>=k1[0])return v0==null?null:v0;
 const f=(b-k0[0])/Math.max(1e-6,k1[0]-k0[0]),e=f*f*(3-2*f);
 if(v0==null&&v1==null)return null;if(v1==null)return f<0.6?v0:null;   /* letting go: the muscle takes it back to rest */
 if(v0==null)return e>0.05?v1:null;
 return v0+(v1-v0)*e}

// The legs: each foot planted on the ground where the stance puts it, the hips low enough that both knees stay bent
// and shifted against the lean so the weight stays between the feet, each knee bent to fit between hip and foot (two
// bones, the law of cosines): side on, the way the unit faces; face on, out over its foot. The front leg is the one on
// the target's side (side on, the one drawn).
function skLegs(A,d,b,sg,lunge,dt){const L=d.limbs,Lg=A.Lg;
 if(!A.legs){const set=d.sets.f,legs=[['legRu','legRl'],['legLu','legLl']].filter(([u,l])=>L[u]&&L[l]);
  const x=([u])=>L[u].root0[0]*sg-(set[u]&&set[u].borrow?1e-3:0);legs.sort((p,q)=>x(q)-x(p));
  A.legs=legs.map(([u,l],i)=>({u,l,front:i===0,foot0:[...L[l].tip0],hip0:[L[u].root0[0]-d.pel0[0],L[u].root0[1]-d.pel0[1]]}));A.own=A.D.keys.some(k=>k[1]&&'step' in k[1])}
 const D=A.D,step=skKey(D,b,'step')*Lg,back=skKey(D,b,'back')*Lg,crouch=(skKey(D,b,'crouch')||0)*Lg,lean=skKey(D,b,'lean')||0,end=D.keys[D.keys.length-1][0]+0.25,kick=(skKey(D,b,'kick')||0)*Lg;
 const feet=A.legs.map(g=>{const go=g.front?(A.own?step:lunge):-back;return [g.foot0[0]+sg*(go-lunge),g.foot0[1]+(g.front?kick:0)]});   /* a kick lifts the front foot */
 // how low the hips must go: each leg reaching at most most of its length (fully only as the move begins and ends)
 const on=Math.min(1,b/0.1,Math.max(0,(end-b)/0.15)),reach=1-0.07*on;let need=0;
 A.legs.forEach((g,i)=>{const U=L[g.u],W=L[g.l];if(!U||!W)return;const r=(U.len+W.len)*reach,hx=d.pel0[0]+g.hip0[0],dx=Math.min(Math.abs(feet[i][0]-hx),r*0.95);
  need=Math.max(need,d.pel0[1]+g.hip0[1]-(feet[i][1]+Math.sqrt(r*r-dx*dx)))});
 // the weight: as the body leans into the blow the hips go back, as it leans away they come forward
 const Ht=L.head?L.head.tip0[1]-d.pel0[1]:2.5*Lg,want=[d.pel0[0]-sg*0.3*Math.sin(lean)*Ht,d.pel0[1]-Math.max(crouch,need)],k=Math.min(1,dt*18);
 d.crouchTo=null;d.pel[0]+=(want[0]-d.pel[0])*k;d.pel[1]+=(want[1]-d.pel[1])*k;
 A.legs.forEach((g,i)=>{const U=L[g.u],W=L[g.l];if(!U||!W)return;const F=feet[i],H=rdRootNow(d,U),a=U.len,c=W.len;
  let vx=F[0]-H[0],vy=F[1]-H[1],dd=Math.hypot(vx,vy);const mx=(a+c)*0.999;if(dd<1e-4)return;if(dd>mx){vx*=mx/dd;vy*=mx/dd;dd=mx}
  const kn=d.fl==='E'?1:d.fl==='W'?-1:(H[0]>=d.pel[0]?1:-1);   /* side on the knee goes the way it faces; face on, out over the foot */
  const al=Math.acos(Math.max(-1,Math.min(1,(a*a+dd*dd-c*c)/(2*a*dd)))),th=Math.atan2(vy,vx)+kn*al,K=[H[0]+Math.cos(th)*a,H[1]+Math.sin(th)*a];
  U.pose=th;W.pose=Math.atan2(H[1]+vy-K[1],H[0]+vx-K[0])})}

// Where a living unit stands on the page, as its circle is drawn (game.js's downed doll follows it the same way); null for
// a dead one or one not placed yet. A move's doll keeps to it: one doll a unit is used move after move, and each started
// where the last left it, so in a fight (swing after swing while it stepped) the doll was left tiles from its circle
// (the owner, 10-31: "if a unit gets knocked back or dies it doesnt match the circle perfectly").
function skAt(t){return t&&!t.dead&&t.dx!=null?[t.dx+(t.px||0)+((t.iw||1)-1)/2,-t.dy-(t.py||0)]:null}
function skStep(dt,emit){const now=performance.now()/1000;SK.stepping=true;SK.pending=SK.pending||[];
 SK.acts=SK.acts.filter(A=>{if(A.replaced)return false;   /* another move or a fall took its doll */const t=A.t,b0=(now-A.t0)*(RD.slow||1)/(RD.slow||1);
  if(!A.doll){let d=A.opt.doll;   /* opt.doll: carry on in the doll it already has (lifting, then carrying) */
   if(d){d.kind='pose';d.alive=true;d.done=false;d.muscle=1}
   else{const cur=rdLive(t);if(!cur&&now-A.t0<0.12)return true;   /* a frame or two for its turned picture */
    d=rdTake(t);if(!d){const c=A.opt.death&&A.opt.then?rdLive(t):null;if(c)A.opt.then(c);return false}d.kind='pose';d.alive=true;d.muscle=1}   /* a death whose doll can't act (knocked flying, down): it falls as it is */   /* the doll it is already (one a unit), or a new one */
   const at0=A.opt.death||A.opt.walk||A.skill==='getup'?null:skAt(t);   /* a death, a carry (its own walk), getting up where it lay: as they were */
   if(at0)d.O=[at0[0],t.ly?d.O[1]:rdGround(at0[0],at0[1]),at0[1]];   /* a doll kept from its last move starts where the unit stands now */
   A.doll=d;A.a0=now;A.O0=[...d.O];A.at=at0;
   const tg=A.target&&A.target.g3last,at=tg?[tg.LX,0,tg.LZ]:A.opt.at;A.sg=at?(rdV.dot(rdV.sub([at[0],0,at[2]],[d.O[0],0,d.O[2]]),d.R)>=0?1:-1):1;
   if(A.D.bare)skStow(d,A.D.stowShield);   /* fists, claws, work with both hands: the weapon (and the shield) on its back */
   const w=d.gear.find(g=>g.slot==='w');A.w=w;A.two=(A.D.two||(w&&SKTWO.has(w.name.replace('weapon.',''))))&&!d.gear.some(g=>g.slot==='s');   /* with a shield on its arm, one hand only */
   const ln=p=>d.limbs[p]?d.limbs[p].len:0;A.Lg=Math.max(ln('legRu')+ln('legRl'),ln('legLu')+ln('legLl'))||0.17}   /* its leg's length: the stance's measure */
  const d=A.doll,D=A.D,b=now-A.a0,sg=A.sg,L=d.limbs;
  // the two hands: on a two-handed haft the other hand follows the weapon hand
  const arm={R:'R',L:'L'};
  for(const [key,p] of [['Ru','armRu'],['Rl','armRl'],['Lu','armLu'],['Ll','armLl']]){let v=skKey(D,b,key);if(A.two&&key[0]==='L'&&v==null){const r=skKey(D,b,'R'+key[1]);if(r!=null)v=r-0.12}if(L[p])L[p].pose=v==null?null:skAbs(v,sg)}
  // hands put on a spot of the body (deaths.js): Rhx, Rhy, Lhx, Lhy in picture pixels from the neck, x out to the
  // hand's own side (- across the body), y up; the arm bends to reach it
  // or Rfx, Rfy: forward toward what it works at (work.js), in picture pixels from the neck
  if(L.head)for(const sd of ['R','L']){const fx=skKey(D,b,sd+'fx');if(fx==null)continue;const fy=skKey(D,b,sd+'fy')||0,U=L['arm'+sd+'u'];if(!U)continue;
   const nk=rdRootNow(d,L.head),r=rdReach(d,'arm'+sd+'u','arm'+sd+'l',[nk[0]+sg*fx*d.k,nk[1]+fy*d.k]);if(r){U.pose=r[0];L['arm'+sd+'l'].pose=r[1]}}
  if(L.head)for(const sd of ['R','L']){const hx=skKey(D,b,sd+'hx');if(hx==null)continue;const hy=skKey(D,b,sd+'hy')||0,U=L['arm'+sd+'u'];if(!U)continue;
   const nk=rdRootNow(d,L.head),ss=Math.sign(U.root0[0]-L.head.root0[0])||1,r=rdReach(d,'arm'+sd+'u','arm'+sd+'l',[nk[0]+ss*hx*d.k,nk[1]+hy*d.k]);if(r){U.pose=r[0];L['arm'+sd+'l'].pose=r[1]}}
  // toward or away from the eye (its front or back picture, the target ahead in the view's depth): the move goes into
  // the depth, as the archer's does. The hands come in before its chest by how far they reach (drawn back, they stay
  // at the shoulder), the weapon points where its keys say but toward the target in 3D, and from its back the arms and
  // the blade are behind the body
  const tgw=A.target&&A.target.g3last?[A.target.g3last.LX,0,A.target.g3last.LZ]:A.opt.at?[A.opt.at[0],0,A.opt.at[2]]:null,Fw=tgw?rdV.n([tgw[0]-A.O0[0],0,tgw[2]-A.O0[2]]):rdV.mul(d.R,sg);
  const kx=d.fl==='E'||d.fl==='W'?1:Math.min(1,Math.abs(rdV.dot(Fw,d.R))*1.3),deep=1-kx;A.deep=deep;A.Fw=Fw;
  if(deep>0.05&&!['block','parry','dodge','lift','carry','hold'].includes(A.skill)&&!D.work&&L.head){const nk=L.head.root0;
   const shieldL=d.gear.some(g=>g.slot==='s');
   for(const sd of ['R','L']){if(sd==='L'&&shieldL&&!A.two&&!A.D.shield){if(deep>0.5){if(L.armLu)L.armLu.pose=null;if(L.armLl)L.armLl.pose=null}continue}   /* the shield arm keeps its shield up as it was */
    const U=L['arm'+sd+'u'],W=L['arm'+sd+'l'];if(!U||!W||U.pose==null||W.pose==null)continue;const S=rdRootNow(d,U),a=U.len,c=W.len;
    const E=[S[0]+Math.cos(U.pose)*a,S[1]+Math.sin(U.pose)*a],H=[E[0]+Math.cos(W.pose)*c,E[1]+Math.sin(W.pose)*c],ext=((H[0]-S[0])*sg)/(a+c),ss=Math.sign(S[0]-nk[0])||1;
    const P=[S[0]+(nk[0]-S[0])*Math.max(0,ext)*0.85+ss*Math.max(0,-ext)*0.25*(a+c),H[1]],r=rdReach(d,'arm'+sd+'u','arm'+sd+'l',P,d.fl==='N');
    if(r){U.pose=rdMixA(U.pose,r[0],deep);W.pose=rdMixA(W.pose,r[1],deep)}}
   d.armsBehind=d.fl==='N'&&deep>0.5}
  else d.armsBehind=false;
  const lean=(skKey(D,b,'lean')||0)+(skKey(D,b,'shake')||0)*(Math.sin(now*47)+0.5*Math.sin(now*31));let lunge=(skKey(D,b,'lunge')||0)*A.Lg;   /* shake: a shiver, a convulsion */if(D.tilt)d.phi+=(-sg*lean-d.phi)*Math.min(1,dt*8);else d.phi=-sg*lean;   /* getting up: from however it lay */
  if(D.tilt)d.tilt=skKey(D,b,'tilt')||0;   /* getting up: how far it still lies */
  if(d.jolt){const u=(now-d.jolt.t)/0.35;if(u<1){const k=d.jolt.k*Math.sin(Math.PI*Math.min(1,u*2))*(1-u);d.phi+=k;lunge-=Math.abs(k)*0.15*A.Lg}else d.jolt=null}   /* struck mid-move: a jolt, and it goes on */
  if(A.at){const a=skAt(t);if(a&&(a[0]!==A.at[0]||a[1]!==A.at[1])){const X=A.O0[0]+a[0]-A.at[0],Z=A.O0[2]+a[1]-A.at[1];A.O0=[X,t.ly?A.O0[1]:rdGround(X,Z),Z];A.at=a}}   /* the unit stepped (or was moved) mid-move: its doll goes with it */
  d.O=rdV.add(A.O0,rdV.mul(rdV.n(rdV.add(rdV.mul(d.R,sg*kx),rdV.mul(Fw,deep))),lunge));   /* the lunge toward the target, into the depth too */
  skLegs(A,d,b,sg,lunge*kx,dt);
  // the grip: the weapon slides into the fist as the move starts (the standing picture holds it a little apart) and
  // back as it ends, so the arm carries it from its hand
  if(A.w&&L[A.w.part]){const P=L[A.w.part];if(!A.g0)A.g0=[...A.w.p];const fist=[P.tip0[0]-P.root0[0],P.tip0[1]-P.root0[1],A.g0[2]],end0=D.keys[D.keys.length-1][0]+0.25;
   const f=A.looped?(A.stop?Math.min(1,Math.max(0,(end0-b)/0.15)):1):Math.min(1,b/0.12,Math.max(0,(end0-b)/0.15)),e=f*f*(3-2*f);   /* a job going round: kept in the fist */for(let i=0;i<3;i++)A.w.p[i]=A.g0[i]+(fist[i]-A.g0[i])*e}
  // the weapon's own angle
  if(A.w&&L[A.w.part]){const W=skKey(D,b,'W');if(W==null)A.w.wrist*=Math.max(0,1-dt*10);else{const f=rdPartFrame(d,A.w.part);let want=skAbs(W,sg)-(A.w.aw0+f.ang);while(want-A.w.wrist>Math.PI)want-=2*Math.PI;while(want-A.w.wrist<-Math.PI)want+=2*Math.PI;A.w.wrist+=(want-A.w.wrist)*Math.min(1,dt*30)}}
  // into the depth: the weapon's direction in 3D, its angle in the keys (forward and up) turned to point at the target
  if(A.w){if(deep>0.1){const W=skKey(D,b,'W');let ang;if(W!=null)ang=W;else{const f=rdPartFrame(d,A.w.part),fa=f.abs!=null?f.abs:0;ang=sg>0?fa:Math.PI-fa}
    const X3=rdV.n(rdV.add(rdV.mul(Fw,Math.cos(ang)),[0,Math.sin(ang),0]));A.w.aim3=X3;A.w.aimK=deep;A.w.aimOff=rdV.mul(Fw,0.05*deep);A.w.live=true}
   else if(A.w.aim3){A.w.aim3=null;A.w.live=false}}
  // the edge's trail through the blow
  if(A.w&&D.trail&&b>=D.trail[0]&&b<=D.trail[1]){const g=rdGearWorld(d,A.w),len=skLen(A.w.name)*A.w.s,X=rdV.n(g.X);A.trail.push({t:now,tip:rdV.add(g.o,rdV.mul(X,len)),mid:rdV.add(g.o,rdV.mul(X,len*0.45)),tier:A.w.tier,st:A.w.name.replace('weapon.','')});if(!SK.trails.includes(A.trail))SK.trails.push(A.trail)}
  // the blow lands
  if(D.hit)while(A.hits<D.hit.length&&b>=D.hit[A.hits]){if(D.work)wkStrike(A,emit);else skHit(A,A.hits===D.hit.length-1);A.hits++}   /* work: the tool bites (work.js) */
  // a thrown weapon leaves the hand
  if(D.release!=null&&!A.released&&b>=D.release&&D.work==='netfish'){A.released=true;wkCast(A,null)}   /* the net goes out (no tool in hand) */
  if(D.release!=null&&!A.released&&b>=D.release){A.released=true;if(A.w){const g=rdGearWorld(d,A.w);
   if(D.spell){if(typeof mfCast==='function')mfCast(A.w.name.replace('weapon.',''),g,A.w.s,A.target,A.opt.kill)}   /* the spell leaves the staff's head */
   else if(D.work)wkCast(A,g);   /* the line goes out (work.js) */
   else{d.gear.splice(d.gear.indexOf(A.w),1);skThrow(A,g)}}}
  const end=D.keys[D.keys.length-1][0]+0.25;
  if(A.opt.walk){const W=A.opt.walk;A.walked=(A.walked||0)+dt;if(A.walked<(W.until||1e9))A.O0=rdV.add(A.O0,rdV.mul(W.dir,W.speed*dt))}   /* walking as it goes (carrying) */
  if(A.opt.fx)A.opt.fx(d,dt,b,emit,A);   /* a death's or a job's own effects as it is acted out (deaths.js, work.js) */
  if(b>end&&A.opt.loop&&!A.stop){A.a0=now;A.hits=0;A.released=false;A.trail=[];A.looped=true;return true}   /* a job goes round till it is stopped */
  if(A.stop&&A.opt.then&&A.climbing){d.tilt=null;A.opt.then(d,A);return false}   /* a climb ends where it got to */
  if(b>end&&A.opt.then){d.tilt=null;A.opt.then(d,A);return false}   /* then something else from where it is (a fall) */
  if(b>end){d.done=true;d.tilt=null;if(A.opt.walk){t.x=Math.round(d.O[0]);t.y=Math.round(-d.O[2]);t.dx=t.x;t.dy=t.y}if(A.lent){if('w' in A.lent)t.g3={...t.g3,w:A.lent.w};if('s' in A.lent)t.g3={...t.g3,s:A.lent.s};if(!t.g3.w)delete t.g3.w;if(!t.g3.s)delete t.g3.s;t.g3p=undefined;t.g3kk=undefined}
   rdBack(t);return false}
  return true});
 SK.stepping=false;if(SK.pending.length){SK.acts.push(...SK.pending);SK.pending.length=0}
 // a living unit's standing doll that no move holds (its move taken over, a knock-back's flight cut short) stays where it
 // was left while the unit walks on, its circle with it (4 tiles apart in a fight arena): off its spot for 0.3 s it is let
 // go and the unit's own picture stands on its circle again (g3rebind does so only when its tile changes)
 {const held=new Set();for(const A of SK.acts)if(A.doll)held.add(A.doll);for(const A of SK.acts)held.add(A.t);
  for(const d of RD.dolls){const t=d.t;if(d.done||d.ghost||!d.alive||d.kind!=='pose'||!t||held.has(d)||held.has(t)||t.g3ko||t.g3cl||t.g3cy)continue;
   if(typeof WK!=='undefined'&&WK.carry.get(t))continue;const a=skAt(t);if(!a)continue;   /* dying (its fall to come), carried, carrying: theirs */
   if(Math.hypot(d.O[0]-a[0],d.O[2]-a[1])<0.05){d.loose=0;continue}d.loose=(d.loose||0)+dt;if(d.loose>0.3){d.done=true;rdShow(t)}}}
 SK.trails=SK.trails.filter(T=>{while(T.length&&now-T[0].t>0.2)T.shift();return T.length>0});
 SK.shots=SK.shots.filter(P=>skShotStep(P,dt,emit));
 if(typeof wkDraw==='function')wkDraw(emit)}

// The blow on the target: guarded (sparks or a miss), glancing off armour, or a hit: a flinch, or the skill's death.
function skHit(A,last){const T=A.target,d=A.doll;if(!T||!T.g3last)return;const tg=T.g3last,at=[tg.LX,tg.yA+tg.sh*0.5,tg.LZ];
 const from=rdV.n([tg.LX-A.O0[0],0,tg.LZ-A.O0[2]]),g=A.opt.guard;
 if(A.D.dust){const w=A.w&&rdGearWorld(d,A.w);rdDust(w?[w.o[0],rdGround(w.o[0],w.o[2]),w.o[2]]:at,9)}
 if(A.D.claw){for(let k=0;k<3;k++)SK.trails.push(skClawStreak(at,d,k,A.sg))}
 if(g==='dodge')return;   /* stepped out of it */
 if(g==='block'||g==='parry'){rdSparks(rdV.add(at,rdV.mul(from,-0.12)),12);return}
 if(g==='armour'){rdSparks(rdV.add(at,rdV.mul(from,-0.08)),9,[0.95,0.95,1]);rdStart(T,'flinch',from);return}
 if(!last&&!A.opt.kill){rdStart(T,'flinch',from);return}
 if(A.opt.maim&&A.D.maim){rdStart(T,A.D.maim,from);return}   /* a limb taken: it lives on without it, bleeding */
 if(A.D.always&&!A.opt.kill){rdStart(T,A.D.always,from,{live:true});return}   /* launched: it gets up where it lands */
 if(A.opt.kill){const ds=A.D.deaths,kind=(T.g3maim?(T.g3maim==='arm'?'armoff':'legoff'):null)||A.D.always||(ds?ds[Math.floor(Math.random()*ds.length)]:A.D.death)||'fall';   /* a limb the game took with the blow: off with it */const t2=rdStart(T,kind,from);if(t2&&!RDNOBLOOD.has(T.g3&&T.g3.sheet)&&!A.D.bare)rdBlood(at,rdV.mul(from,0.8),10,false);return}
 if(A.opt.knock){g3knockNow(T,A.opt.knock);return}   /* the game moved it: knocked there, alive (game.js) */
 if(A.D.knock){const t2=rdStart(T,'flinch',from);if(t2){t2.om*=1.6}return}
 rdStart(T,'flinch',from);if(!RDNOBLOOD.has(T.g3&&T.g3.sheet)&&!A.D.bare&&Math.random()<0.6)rdBlood(at,rdV.mul(from,0.5),5,false)}

// The weapon's length in pixels (the far end of its model along its haft or blade).
function skLen(name){let c=RD.cen.get('len:'+name);if(c!=null)return c;const P=G3.P[name];let mx=10;if(P)for(let i=0;i<P.v;i++)mx=Math.max(mx,P.pos[i*3]/G3.q);RD.cen.set('len:'+name,mx);return mx}

// A thrown weapon: on an arc to the target, a spear along its flight, a knife or an axe turning over; then it lands.
// It lands where the game says (Throwing.dm: a leg, an arm or the chest), is blocked by a shield, glances off armour
// or misses and comes down beyond (opt.guard 'block', 'armour', 'dodge'; opt.part a body part, else rolled).
function skThrow(A,g){const T=A.target;if(!T||!T.g3last)return;const gd=A.opt.guard,res=gd==='block'?'block':gd==='armour'?'deflect':gd==='dodge'?'miss':'hit';
 const aim=rdAim(T,A.opt.part||rdThrowPart());let P=aim.P;
 if(res==='miss'){const M=rdMissPoint(g.o,P),F=rdV.n([P[0]-g.o[0],0,P[2]-g.o[2]]);P=rdV.add(M,rdV.mul(F,0.9));P[1]=rdGround(P[0],P[2])+0.03}
 const D=rdV.sub(P,g.o),dist=Math.hypot(D[0],D[2])||0.01,time=Math.max(0.15,dist/11);
 const V=[D[0]/time,(D[1]+0.5*RDG*time*time)/time,D[2]/time],spear=A.w.name.includes('spear');
 SK.shots.push({name:A.w.name,tier:A.w.tier,s:A.w.s,X:[...g.o],V,t:0,T:time,target:T,kill:A.opt.kill&&res==='hit',res,at:P,spin:spear?0:(A.sg>0?-1:1)*18,ang:0,ax:rdV.n(rdV.cross(V,[0,1,0])),from:rdV.n([V[0],0,V[2]])})}
function skShotStep(P,dt,emit){P.t+=dt;P.V[1]-=RDG*dt;P.X=rdV.add(P.X,rdV.mul(P.V,dt));P.ang+=P.spin*dt;
 let [X,Y,Z]=rdArrowBasis(P.V);if(!P.spear){const q0=rdQuat(X,Y,Z),q=rdQ.mul(rdQ.axis(P.ax,P.ang),q0);emit(P.name,P.tier,P.X,q,P.s)}else emit(P.name,P.tier,rdV.sub(P.X,rdV.mul(X,skLen(P.name)*P.s*0.6)),rdQuat(X,Y,Z),P.s);
 if(P.t>=P.T){const T=P.target;let V=rdV.mul(P.V,-0.15);
  if(P.res==='block'||P.res==='deflect'){   /* off the shield or the armour: sparks, and it bounces back */
   const d=T&&RD.dolls.find(x=>x.t===T&&!x.done&&x.alive),sg=d&&d.gear.find(x=>x.slot==='s'),at=P.res==='block'&&sg?rdGearWorld(d,sg).o:P.X;
   rdSparks(at,10,P.res==='block'?undefined:[0.95,0.95,1]);V=rdV.add(rdV.mul(P.from,-1.4),[(Math.random()-0.5)*0.8,1.6,(Math.random()-0.5)*0.8]);if(T&&P.res==='deflect')rdStart(T,'flinch',P.from)}
  else if(P.res==='hit'&&T){rdStart(T,P.kill?'fall':'flinch',P.from);if(!RDNOBLOOD.has(T.g3&&T.g3.sheet))rdBlood(P.X,rdV.mul(P.from,0.6),P.kill?10:4,false)}
  // it drops where it struck (a miss: where it came down)
  RD.loose.push({name:P.name,tier:P.tier,s:P.s,c:[skLen(P.name)/2,0,0],r:0.02,X:[...P.X],V,q:rdQuat(X,Y,Z),w:[(Math.random()-0.5)*6,(Math.random()-0.5)*6,(Math.random()-0.5)*6],rest:false,flat:2,bounce:0});return false}
 return true}

// A claw's three streaks across the target, drawn as short trails.
function skClawStreak(at,d,k,sg){const now=performance.now()/1000,T=[],B=rdBasis(d);for(let i=0;i<5;i++){const f=i/4,x=(-0.12+f*0.24)*sg,y=0.16-f*0.26+(k-1)*0.05;
  const p=rdV.add(at,rdV.add(rdV.mul(B.Ux,x),rdV.mul(B.Uy,y)));T.push({t:now+i*0.01,tip:rdV.add(p,rdV.mul(B.Uy,0.012)),mid:rdV.sub(p,rdV.mul(B.Uy,0.012)),tier:'claw'})}return T}
// The trails as fading ribbons (ragdoll.js rdFxDraw adds them to its see-through pass).
function skTrailsDraw(va){if(typeof wkLinesDraw==='function')wkLinesDraw(va);   /* fishing lines (work.js) */
 skTrailsDraw0(va)}
function skTrailsDraw0(va){const now=performance.now()/1000;for(const T of SK.trails)for(let i=1;i<T.length;i++){const a=T[i-1],b=T[i],age=now-b.t,al=Math.max(0,0.5*(1-age/0.2));if(al<=0.01)continue;
  const m=SKTRAIL[b.st],c=m?[m[0],m[1],m[2],al*1.5]:b.tier==='hell'?[1,0.55,0.3,al]:b.tier==='gold'?[1,0.9,0.55,al]:b.tier==='claw'?[1,1,1,al*1.4]:[0.9,0.94,1,al];quad(va,a.mid,b.mid,b.tip,a.tip,QN0,c)}}
// an enchanted weapon's trail in its own colour (magicfx.js)
const SKTRAIL={'flame sword':[1,0.55,0.2],'frost axe':[0.7,0.9,1],'void blade':[0.55,0.3,0.85],'rune sword':[0.5,0.75,1],'storm spear':[0.8,0.9,1],'holy mace':[1,0.88,0.5]};

// Getting up from the ground, out cold or launched and living (ragdoll.js, when it is ready): its doll goes on as a
// move from where it lies; what it dropped comes back to its hand; a launched one is now on the tile it came down on.
function skGetUp(d){const t=d.t,now=performance.now()/1000;if(d.live){t.x=Math.round(d.O[0]);t.y=Math.round(-d.O[2]);t.dx=t.x;t.dy=t.y}
 for(const b of RD.loose)if(b.doll===d&&!b.pick)b.pick=1;
 d.tiltSign=Math.sign(d.th)||1;d.tilt=Math.min(1,Math.abs(d.th)/(Math.PI/2));d.kind='pose';d.live=false;d.crouchTo=null;d.om=0;d.landed=false;d.muscle=1;
 const ln=p=>d.limbs[p]?d.limbs[p].len:0;
 SK.acts.push({t,skill:'getup',D:SK.defs.getup,target:null,opt:{},lent:null,t0:now-1,doll:d,a0:now,O0:[...d.O],sg:d.fl==='W'?-1:1,hits:0,released:false,trail:[],w:null,two:false,
  Lg:Math.max(ln('legRu')+ln('legRl'),ln('legLu')+ln('legLl'))||0.17})}

// Deaths that aren't a blow (art/gear3d; the animation arena): each of the game's other causes of death (its
// DeathType names, RDCAUSE below) acted out on the unit's own sprite, then a fall of its own, with its own effects:
// bleeding out sways and sinks in its own blood; poison retches and drools green; starving sways and sinks; cold
// shivers hugging itself, frosts over and topples stiff; fever wipes its brow and sweats; burning flails in flames and
// falls charred and smoking; lightning throws its arms out rigid, sparking, and topples; the heart clutches its chest;
// choking (vapours, the lungs) holds its throat; goo and holy energy melt it into a puddle; a skeleton rattles and
// drops into a heap of bones; old age sits down and lies down. The acting is a move (skills.js: keys, hands on the
// body), the fall a doll kind (ragdoll.js rdKind), the effects particles (rdPart), and the body's colour a tint.
const DZ={};
// the moves (hand spots in picture pixels from the neck: x out to the hand's own side, - across the body; y up)
Object.assign(SK.defs,{
 d_sway:{keys:[[0],[0.5,{lean:0.12,crouch:0.1}],[1.0,{lean:-0.1,crouch:0.2}],[1.5,{lean:0.15,crouch:0.35}],[1.9,{lean:0.08,crouch:0.45}]]},
 d_retch:{keys:[[0],[0.3,{Rhx:-1,Rhy:-10,lean:0.3,crouch:0.12,shake:0.03}],[0.7,{Rhx:-1,Rhy:-10,Lhx:-2,Lhy:2,lean:0.45,crouch:0.2,shake:0.05}],[1.1,{Rhx:-1,Rhy:-11,Lhx:-1,Lhy:2,lean:0.5,crouch:0.3,shake:0.07}],[1.6,{Rhx:-1,Rhy:-11,lean:0.45,crouch:0.35,shake:0.08}]]},
 d_choke:{keys:[[0],[0.25,{Rhx:-1,Rhy:-1.5,Lhx:-1,Lhy:-1.5,lean:-0.12,shake:0.04}],[0.9,{Rhx:-0.5,Rhy:-1,Lhx:-0.5,Lhy:-1,lean:0.2,crouch:0.15,shake:0.07}],[1.5,{Rhx:-0.5,Rhy:-1.5,Lhx:-0.5,Lhy:-1.5,lean:0.3,crouch:0.3,shake:0.05}]]},
 d_clutch:{keys:[[0],[0.15,{Rhx:-2,Rhy:-6,lean:0.1,shake:0.05}],[0.5,{Rhx:-2,Rhy:-6,Lhx:6,Lhy:-6,lean:0.25,crouch:0.15,lunge:0.15,shake:0.02}],[1.0,{Rhx:-2,Rhy:-7,Lhx:3,Lhy:-12,lean:0.35,crouch:0.4,lunge:0.1}]]},
 d_shiver:{keys:[[0],[0.3,{Rhx:-3,Rhy:-6,Lhx:-3,Lhy:-6.5,crouch:0.1,shake:0.03}],[1.4,{Rhx:-3.5,Rhy:-6,Lhx:-3.5,Lhy:-6.5,crouch:0.18,shake:0.045}],[1.9,{Rhx:-3.5,Rhy:-6,Lhx:-3.5,Lhy:-6.5,crouch:0.18,shake:0.0}]]},
 d_fever:{keys:[[0],[0.3,{Rhx:-1,Rhy:7,lean:-0.05,crouch:0.05}],[0.9,{Rhx:-1,Rhy:7,lean:0.12,crouch:0.15}],[1.4,{Rhx:0,Rhy:4,lean:-0.12,crouch:0.3}],[1.8,{lean:0.1,crouch:0.4}]]},
 d_flail:{keys:[[0],[0.15,{Rhx:5,Rhy:8,Lhx:7,Lhy:-2,lean:-0.2,lunge:0.1,shake:0.04}],[0.3,{Rhx:7,Rhy:-2,Lhx:5,Lhy:8,lean:0.15,lunge:-0.08,shake:0.04}],[0.45,{Rhx:5,Rhy:8,Lhx:7,Lhy:-2,lean:-0.15,lunge:0.12,shake:0.04}],
  [0.6,{Rhx:7,Rhy:-2,Lhx:5,Lhy:8,lean:0.2,lunge:-0.05,shake:0.04}],[0.75,{Rhx:5,Rhy:8,Lhx:7,Lhy:-2,lean:-0.1,lunge:0.15,shake:0.04}],[0.9,{Rhx:7,Rhy:-2,Lhx:5,Lhy:8,lean:0.2,lunge:0.0,shake:0.04}],
  [1.05,{Rhx:5,Rhy:8,Lhx:7,Lhy:-2,lean:-0.15,lunge:0.12,shake:0.04}],[1.2,{Rhx:7,Rhy:-2,Lhx:5,Lhy:8,lean:0.25,lunge:0.05,crouch:0.15,shake:0.04}],[1.5,{Rhx:6,Rhy:2,Lhx:6,Lhy:2,lean:0.3,crouch:0.3,shake:0.06}]]},
 d_jolt:{keys:[[0],[0.05,{Rhx:8,Rhy:2,Lhx:8,Lhy:2,shake:0.12,lean:-0.12}],[0.55,{Rhx:8,Rhy:3,Lhx:8,Lhy:3,shake:0.12,lean:-0.12}],[0.7,{Rhx:7,Rhy:1,Lhx:7,Lhy:1,lean:-0.08}]]},
 d_twitch:{keys:[[0],[0.2,{shake:0.06,lean:0.05}],[0.7,{shake:0.09,crouch:0.15}],[1.0,{shake:0.04,crouch:0.25}]]},
 d_rattle:{keys:[[0],[0.2,{shake:0.08,crouch:0.05}],[0.8,{shake:0.1,crouch:0.1}]]},
 d_melt:{keys:[[0],[0.4,{Rhx:4,Rhy:-2,Lhx:4,Lhy:-2,shake:0.03,crouch:0.1}],[1.0,{Rhx:5,Rhy:0,Lhx:5,Lhy:0,shake:0.04,crouch:0.2}]]},
 d_sit:{keys:[[0],[0.8,{crouch:0.35,lean:0.1,Rhx:1,Rhy:-12,Lhx:1,Lhy:-12}],[1.6,{crouch:0.55,lean:0.15,Rhx:1,Rhy:-14,Lhx:1,Lhy:-14}]]},
 d_stone:{keys:[[0],[0.3,{shake:0.06,crouch:0.04}],[0.9,{shake:0.03,crouch:0.06,lean:0.04}],[1.4,{shake:0,crouch:0.06,lean:0.04}]]},
});
// the game's causes (its DeathType) to these deaths
const RDCAUSE={'Bleeding To Death':'bleed','Poison':'poison','Food Poisoning':'poison','eating it like a moron.':'poison','Starvation':'starve','Tiredness':'starve',
 'Coldness':'cold','Fever':'fever','Overheating':'fever','Burned To Death':'burn','Being Burned':'burn','lightning':'lightning','Heart Failure':'heart',
 'Massive Heart Attack':'heart','Punctured Heart':'heart','Lung Failure':'choke','Brain Damage':'brain','Melting Into Goo':'goo','being slowly melted by holy energy':'holy',
 'Crumbled into Bonemeal':'crumble','old age':'oldage','vapours':'choke','Turned To Stone':'stone'};

// A point on the doll, in picture pixels from its neck (x right in the picture, y up), lifted toward the eye by n.
function dzAt(d,dx,dy,n=0.02){const L=d.limbs.head,B=rdBasis(d),nk=L?rdRootNow(d,L):[d.pel[0],d.pel[1]+0.4];const front=rdV.dot(B.Nn,rdV.sub(V3.eye||[0,10,10],d.O))>=0?1:-1;
 return rdW(d,B,nk[0]+dx*d.k,nk[1]+dy*d.k,n*front)}
const dzR=(a,b)=>a+Math.random()*(b-a),dzBody=d=>dzAt(d,dzR(-5,5),dzR(-17,6),0.03);
// how many to start this frame at a rate a second, carried between frames
function dzN(d,key,rate,dt){d.dzAcc=d.dzAcc||{};const v=(d.dzAcc[key]||0)+rate*dt,n=Math.floor(v);d.dzAcc[key]=v-n;return n}
const dzLerp=(a,b,k)=>a.map((v,i)=>v+(b[i]-v)*k);
const GREEN=[0.45,0.75,0.2,0.9],GOO=[0.32,0.6,0.14];

// Each death: the move it acts out, the fall, the tint it ends in, its effects while acting (fx) and after (after).
const DZDEF={
 bleed:{act:'d_sway',fall:'crumple',tint:[0.92,0.86,0.86],fx(d,dt){for(let i=dzN(d,'b',5,dt);i>0;i--)rdBlood(dzBody(d),[0,-0.3,0],1,false)},
  after(d,dt,age){if(age<1.5&&dzN(d,'p',4,dt))rdPart(rdV.add(d.O,[dzR(-0.12,0.12),0.02,dzR(-0.12,0.12)]),[0,-1,0],0.5,0.03,0.03,[0.45,0.04,0.03,0.9],[0.45,0.04,0.03,0.9],6,0,[0.4,0.03,0.02])}},
 poison:{act:'d_retch',fall:'crumple',tint:[0.8,1.0,0.72],fx(d,dt,b){for(let i=dzN(d,'d',4,dt);i>0;i--)rdPart(dzAt(d,dzR(-1,1),2),[dzR(-0.05,0.05),-0.1,dzR(-0.05,0.05)],1.4,0.012,0.01,GREEN,GREEN,6,0,[0.3,0.5,0.12]);if(dzN(d,'pp',3,dt))rdPx(dzAt(d,dzR(-4,4),dzR(0,6)),[0,0.08,0],1.0,0.035,0.05,'poison',-0.05,1);
   if(b>1.05&&!d.dzSpew){d.dzSpew=true;const F=rdV.mul(d.R,d.fl==='W'?-1:1);for(let i=0;i<14;i++)rdPart(dzAt(d,0,2),rdV.add(rdV.mul(F,dzR(0.3,0.9)),[dzR(-0.3,0.3),dzR(0,0.5),dzR(-0.3,0.3)]),1.2,0.016,0.012,GREEN,GREEN,6,0,[0.3,0.5,0.12])}}},
 starve:{act:'d_sway',fall:'crumple',tint:[0.9,0.88,0.84]},
 cold:{act:'d_shiver',fall:'stiff',tint:[0.72,0.86,1.22],fx(d,dt){for(let i=dzN(d,'f',6,dt);i>0;i--){const P=rdV.add(dzBody(d),[dzR(-0.08,0.08),0,dzR(-0.08,0.08)]);rdPx(P,[0,-0.04,0],1.2,0.035,0.02,'frost',0.1,0.5)}
   if(dzN(d,'br',1.6,dt))rdPart(dzAt(d,0,3),[dzR(-0.05,0.05),0.08,dzR(-0.05,0.05)],1.0,0.015,0.05,[0.95,0.97,1,0.45],[0.95,0.97,1,0],-0.05,1)},
  after(d,dt,age){if(d.landed&&!d.dzIce){d.dzIce=true;rdSparks(d.O,14,[0.85,0.95,1])}if(age<3)for(let i=dzN(d,'f',3,dt);i>0;i--)rdPx(dzBody(d),[0,-0.03,0],1.2,0.035,0.02,'frost',0.1,0.5)}},
 fever:{act:'d_fever',fall:'crumple',tint:[1.1,0.84,0.8],fx(d,dt,b){d.tint=[1+0.12*Math.abs(Math.sin(b*5)),0.86,0.82];for(let i=dzN(d,'s',5,dt);i>0;i--)rdPart(dzAt(d,dzR(-4,4),dzR(5,9)),[dzR(-0.15,0.15),0.15,dzR(-0.15,0.15)],0.8,0.008,0.006,[0.75,0.88,1,0.9],[0.75,0.88,1,0.6],6)}},
 burn:{act:'d_flail',fall:'fall',tint:[0.3,0.25,0.22],fx(d,dt,b){dzFire(d,dt,45,8)},after(d,dt,age){if(age<2.5)dzFire(d,dt,30*(1-age/2.5),6);else if(age<6)dzSmoke(d,dt,4)}},
 lightning:{act:'d_jolt',fall:'stiff',tint:[0.36,0.33,0.33],fx(d,dt,b){if(!d.dzFlash){d.dzFlash=true;rdSparks(dzAt(d,0,10),30,[0.85,0.92,1]);rdPart(dzAt(d,0,-4),[0,0,0],0.18,0.25,0.4,[0.9,0.95,1,0.9],[0.8,0.9,1,0])}
   d.tint=b<0.12?[1.8,1.8,2]:null;if(dzN(d,'s',30,dt))rdSparks(dzBody(d),2,[0.8,0.9,1]);for(let i=dzN(d,'sp',14,dt);i>0;i--)rdPx(dzBody(d),[0,0,0],0.25,0.06,0.03,'spark')},after(d,dt,age){if(age<4)dzSmoke(d,dt,5)}},
 heart:{act:'d_clutch',fall:'fall'},
 choke:{act:'d_choke',fall:'crumple',tint:[0.86,0.86,0.94],fx(d,dt){if(dzN(d,'c',2.5,dt))for(let i=0;i<2;i++)rdPx(dzAt(d,dzR(-1,1),2),[dzR(-0.1,0.1),dzR(0.05,0.2),dzR(-0.1,0.1)],1.0,0.03,0.07,'plague',-0.1,1)}},
 brain:{act:'d_twitch',fall:'crumple'},
 goo:{act:'d_melt',fall:'melt',tint:[0.72,1.05,0.58],fx(d,dt){for(let i=dzN(d,'g',6,dt);i>0;i--)rdPart(dzBody(d),[0,-0.2,0],1,0.014,0.012,[0.4,0.7,0.18,0.95],[0.4,0.7,0.18,0.95],6,0,GOO)},after(d,dt,age){if(age<3){dzPuddle(d,dt,GOO,0.5);if(dzN(d,'ac',6,dt))rdPx(rdV.add(d.O,[dzR(-0.2,0.2),0.04,dzR(-0.2,0.2)]),[0,0.1,0],0.8,0.03,0.04,'acid',0,1)}}},
 holy:{act:'d_melt',fall:'melt',tint:[1.45,1.35,1.1],fx(d,dt,b){d.tint=dzLerp([1,1,1],[1.45,1.35,1.1],Math.min(1,b));for(let i=dzN(d,'h',8,dt);i>0;i--)rdPx(dzBody(d),[dzR(-0.03,0.03),dzR(0.2,0.35),dzR(-0.03,0.03)],1.2,0.04,0.025,'holy',-0.1,0.3)},
  after(d,dt,age){if(age<3){dzPuddle(d,dt,[0.85,0.82,0.7],0.45);for(let i=dzN(d,'h',5,dt);i>0;i--)rdPx(rdV.add(d.O,[dzR(-0.15,0.15),0.05,dzR(-0.15,0.15)]),[0,0.3,0],1.2,0.04,0.025,'holy',-0.1,0.3)}}},
 stone:{act:'d_stone',fall:'pose',tint:[0.62,0.6,0.58],fx(d,dt){for(let i=dzN(d,'st',7,dt);i>0;i--)rdPx(dzBody(d),[dzR(-0.03,0.03),dzR(0.05,0.15),dzR(-0.03,0.03)],0.9,0.035,0.06,'dust',0.05,0.6)},after(d,dt,age){if(age<0.1&&!d.dzDust){d.dzDust=true;rdDust(d.O,12)}}},   /* turned to stone (a guest who left, Guests.dm): it stiffens and greys where it stands, in a breath of stone dust, and stays standing */
 crumble:{act:'d_rattle',fall:'heap',tint:[0.95,0.93,0.86],after(d,dt,age){if(age<0.1&&!d.dzDust){d.dzDust=true;rdDust(d.O,10);for(let i=0;i<10;i++)rdPx(rdV.add(d.O,[dzR(-0.2,0.2),dzR(0.02,0.15),dzR(-0.2,0.2)]),[dzR(-0.2,0.2),dzR(0.1,0.3),dzR(-0.2,0.2)],1.0,0.05,0.08,'dust',0,1.5)}}},
 oldage:{act:'d_sit',fall:'liedown'},
};
function dzFire(d,dt,flames,smoke){for(let i=dzN(d,'fl',flames*0.45,dt);i>0;i--)rdPx(dzBody(d),[dzR(-0.06,0.06),dzR(0.35,0.6),dzR(-0.06,0.06)],dzR(0.45,0.7),0.07,0.045,'fire',-0.2,1.2);   /* the game's own fire pixels */
 for(let i=dzN(d,'em',flames*0.15,dt);i>0;i--)rdPart(dzBody(d),[dzR(-0.1,0.1),dzR(0.5,0.9),dzR(-0.1,0.1)],dzR(0.6,1.0),0.008,0.004,[1,0.75,0.3,1],[1,0.3,0.05,0],-0.1,0.5);dzSmoke(d,dt,smoke)}
function dzSmoke(d,dt,n){for(let i=dzN(d,'sm',n,dt);i>0;i--)rdPart(rdV.add(dzBody(d),[0,0.05,0]),[dzR(-0.08,0.08),0.35,dzR(-0.08,0.08)],1.6,0.03,0.12,[0.3,0.28,0.26,0.55],[0.35,0.34,0.33,0],-0.05,0.8)}
function dzPuddle(d,dt,col,r){for(let i=dzN(d,'pu',10,dt);i>0;i--){const a=Math.random()*6.283,q=Math.sqrt(Math.random())*r*Math.min(1,(d.age||0)+0.3);rdPart(rdV.add(d.O,[Math.cos(a)*q,0.01,Math.sin(a)*q]),[0,-1,0],0.3,0.035,0.035,[...col,0.9],[...col,0.9],8,0,col)}}

// The unit dies of cause (the game's DeathType, or one of DZDEF's names): it acts it out, then falls; from: the way it
// falls (away from that), else to a side.
function rdDie(t,cause,from){const key=DZDEF[cause]?cause:RDCAUSE[cause]||'starve',Z=DZDEF[key];if(!t||!t.g3last)return null;
 from=from||(()=>{const a=Math.random()*6.283;return [Math.cos(a),0,Math.sin(a)]})();
 const tint0=[1,1,1],A=skAct(t,Z.act,null,{death:true,fx(d,dt,b){if(Z.tint&&!['fever','lightning','holy'].includes(key))d.tint=dzLerp(tint0,Z.tint,Math.min(1,b/1.4));if(Z.fx)Z.fx(d,dt,b)},
  then(d){d.alive=false;rdKind(d,Z.fall,from);if(Z.tint)d.tint=Z.tint;d.onStep=Z.after||null;if(t.bleed)t.bleed.on=false;t.dead=true}});
 return A}

// Work on the sprite units (art/gear3d; the animation arena), with the real tool in hand (3D pieces like the weapons):
// mining (the pick swung down into the rock, chips and dust flying), chopping (the axe driven into the trunk, wood
// chips), smithing (the hammer on the anvil, sparks), building (knelt, hammering at the ground), fishing (the line
// cast out, the float bobbing, a bite, the fish reeled in on its line) and carrying (lifted from the ground in front,
// held before it in both hands, walked with, dropped if it is struck). Each job goes round till it is stopped (the
// skills' moves, skills.js, looped); its effects are the game's own pixels (rdPx) and chips (rdPart). Units in tiles.
const WK={props:[],lines:[],carry:new Map(),cards:[]};
// The sack is the game's own pixel sack (Icons/Remastered/Sack.dmi, the full one: g3sack.png, its size in pixels), a
// picture facing the eye; a barrel is a big one, half the unit's height.
const WKSACK={tex:'g3sack.png',w:10,h:14},WKBIG={barrel:2.1,log:1.15};
const wkR=(a,b)=>a+Math.random()*(b-a);
Object.assign(SK.defs,{
 mine:{keys:[[0],[0.35,{Ru:2.5,Rl:2.8,W:2.3,lean:-0.15,back:0.15,crouch:0.05}],[0.55,{Ru:-0.45,Rl:-0.7,W:-0.95,lean:0.35,crouch:0.22,lunge:0.15,step:0.35,back:0.15}],
  [0.8,{Ru:-0.55,Rl:-0.8,W:-1.0,lean:0.3,crouch:0.2,lunge:0.15,step:0.35,back:0.15}],[1.15]],hit:[0.55],two:true,work:'mine'},
 woodchop:{keys:[[0],[0.3,{Ru:1.2,Rl:1.8,W:2.6,lean:-0.12,back:0.15}],[0.5,{Ru:-0.1,Rl:0.1,W:0.05,lean:0.25,lunge:0.08,step:0.25,back:0.15,crouch:0.1}],
  [0.75,{Ru:-0.3,Rl:-0.2,W:-0.3,lean:0.2,crouch:0.1,step:0.25,back:0.15}],[1.05]],hit:[0.5],two:true,work:'chop'},
 smith:{keys:[[0,{Lu:-0.5,Ll:-0.1}],[0.25,{Ru:1.4,Rl:2.3,W:2.0,Lu:-0.5,Ll:-0.1,lean:-0.05}],[0.4,{Ru:-0.4,Rl:-0.5,W:-0.9,Lu:-0.5,Ll:-0.1,lean:0.12,crouch:0.05}],
  [0.6,{Ru:-0.3,Rl:-0.4,W:-0.8,Lu:-0.5,Ll:-0.1}],[0.7]],hit:[0.4],work:'smith'},
 build:{keys:[[0,{crouch:0.45,lean:0.3,Lu:-0.9,Ll:-0.9}],[0.2,{Ru:0.8,Rl:1.6,W:1.4,crouch:0.45,lean:0.3,Lu:-0.9,Ll:-0.9}],[0.35,{Ru:-0.9,Rl:-1.1,W:-1.4,crouch:0.48,lean:0.4,Lu:-0.9,Ll:-0.9}],
  [0.55,{Ru:-0.8,Rl:-1.0,W:-1.3,crouch:0.45,lean:0.35,Lu:-0.9,Ll:-0.9}],[0.65,{crouch:0.45,lean:0.3,Lu:-0.9,Ll:-0.9}]],hit:[0.35],work:'build'},
 // cast (0.4 back, 0.6 out), wait, a bite (2.6), the strike (2.8), reel in (3.1-3.6)
 fish:{keys:[[0],[0.4,{Ru:2.2,Rl:2.6,W:2.4,lean:-0.1,back:0.1}],[0.6,{Ru:0.4,Rl:0.3,W:0.5,lean:0.12,step:0.2,back:0.1}],[2.6,{Ru:0.3,Rl:0.2,W:0.45,lean:0.08,step:0.2,back:0.1}],
  [2.8,{Ru:0.25,Rl:0.15,W:0.35,lean:0.1,step:0.2,back:0.1}],[3.1,{Ru:1.3,Rl:1.8,W:1.6,lean:-0.12,back:0.1}],[3.6,{Ru:0.6,Rl:1.0,W:1.2,back:0.05}],[4.1]],release:0.6,work:'fish'},
 // spear fishing (the game's harpoon): raised, the point down, driven into the water ahead, held, then pulled up
 // with the fish on it
 spearfish:{keys:[[0],[0.4,{Ru:1.5,Rl:2.0,W:-1.3,lean:-0.05,back:0.1}],[0.58,{Ru:-0.75,Rl:-0.95,W:-1.3,lean:0.4,crouch:0.22,lunge:0.1,step:0.35,back:0.15}],
  [0.95,{Ru:-0.75,Rl:-0.95,W:-1.3,lean:0.38,crouch:0.22,lunge:0.1,step:0.35,back:0.15}],[1.35,{Ru:0.7,Rl:1.2,W:1.1,lean:-0.08,back:0.1}],[2.0,{Ru:0.7,Rl:1.2,W:1.1,back:0.1}],[2.3]],
  hit:[0.58],two:true,work:'spearfish'},
 // net fishing: the net swung back in both hands, thrown out to open over the water, left to sink, then hauled in
 // hand over hand
 netfish:{keys:[[0,{Rhx:-1,Rhy:-11,Lhx:-1,Lhy:-11}],[0.25,{Ru:-1.9,Rl:-1.6,Lu:-1.8,Ll:-1.5,lean:0.35,crouch:0.35,back:0.35}],[0.45,{Ru:2.3,Rl:2.6,Lu:2.2,Ll:2.5,lean:-0.3,crouch:0.15,back:0.3}],
  [0.62,{Ru:0.2,Rl:0.1,Lu:0.15,Ll:0.05,lean:0.45,crouch:0.25,lunge:0.25,step:0.55,back:0.2}],   /* the whole body into the throw: wound down low and back, up and over, lunging through */
  [2.3,{Ru:-0.3,Rl:-0.1,Lu:-0.35,Ll:-0.15,lean:0.15,step:0.3,back:0.15}],[2.6,{Ru:0.4,Rl:1.4,Lu:-0.4,Ll:-0.2,lean:-0.15,back:0.25,step:0.1}],[2.9,{Ru:-0.4,Rl:-0.2,Lu:0.4,Ll:1.4,lean:-0.18,back:0.25,step:0.1}],
  [3.2,{Ru:0.4,Rl:1.4,Lu:-0.4,Ll:-0.2,lean:-0.15,back:0.25,step:0.1}],[3.5,{Ru:-0.4,Rl:-0.2,Lu:0.4,Ll:1.4,lean:-0.15,back:0.2}],[3.9,{Rhx:-1,Rhy:-12,Lhx:-1,Lhy:-12}],[4.3]],release:0.62,bare:true,stowShield:true,work:'netfish'},
 // foraging (the game's wild herbs, Doctor.dm, and the farmer's steps, FoodRoles.dm): picking from a plant at chest
 // height, a hand in among the leaves, then to the bag at its hip; picking from the ground, knelt; tilling with the
 // spade (driven in with a foot, the earth levered up and thrown); planting seeds (knelt, a hole poked, a seed in, the
 // earth pressed down); harvesting (bent, a handful gathered and cut with the free hand's knife, then bundled)
 pick:{keys:[[0],[0.35,{Rfx:13,Rfy:-9,Lfx:5,Lfy:-12,lean:0.25,step:0.35,back:0.05,crouch:0.06}],[0.55,{Rfx:14,Rfy:-8,Lfx:5,Lfy:-12,lean:0.28,step:0.35,back:0.05,crouch:0.06}],[0.75,{Rfx:13,Rfy:-10,Lfx:5,Lfy:-12,lean:0.25,step:0.35,back:0.05,crouch:0.06}],
  [1.1,{Rfx:-2,Rfy:-16,lean:0.0,crouch:0.02}],[1.35]],hit:[0.6],bare:true,work:'pick'},
 gather:{keys:[[0],[0.45,{Rfx:9,Rfy:-27,Lfx:4,Lfy:-20,lean:0.6,crouch:0.55,step:0.3,back:0.25}],[0.7,{Rfx:10,Rfy:-28,Lfx:4,Lfy:-20,lean:0.6,crouch:0.55,step:0.3,back:0.25}],
  [0.95,{Rfx:9,Rfy:-26,Lfx:4,Lfy:-20,lean:0.6,crouch:0.55,step:0.3,back:0.25}],[1.3,{Rfx:-2,Rfy:-17,lean:0.15,crouch:0.2}],[1.6]],hit:[0.75],bare:true,stowShield:true,work:'gather'},
 till:{keys:[[0],[0.3,{Ru:-0.6,Rl:-0.9,W:-1.45,Lu:-0.2,Ll:0.4,lean:0.1,step:0.3,back:0.1,crouch:0.05}],[0.5,{Ru:-0.9,Rl:-1.0,W:-1.5,Lu:-0.5,Ll:0.1,lean:0.25,step:0.3,back:0.1,crouch:0.18}],
  [0.85,{Ru:-0.2,Rl:0.3,W:-0.9,Lu:0.1,Ll:0.8,lean:-0.15,step:0.3,back:0.15,crouch:0.1}],[1.05,{Ru:0.4,Rl:0.8,W:-0.4,Lu:0.4,Ll:1.0,lean:0.1,step:0.25,back:0.1}],[1.35]],hit:[0.5,0.95],two:true,work:'till'},
 plant:{keys:[[0],[0.4,{Rfx:8,Rfy:-27,Lfx:3,Lfy:-18,lean:0.55,crouch:0.6,step:0.3,back:0.25}],[0.6,{Rfx:8,Rfy:-29,Lfx:3,Lfy:-18,lean:0.6,crouch:0.6,step:0.3,back:0.25}],
  [0.85,{Rfx:8,Rfy:-27,Lfx:9,Lfy:-27,lean:0.6,crouch:0.6,step:0.3,back:0.25}],[1.05,{Rfx:8,Rfy:-29,Lfx:9,Lfy:-29,lean:0.6,crouch:0.6,step:0.3,back:0.25}],[1.4,{crouch:0.1}],[1.7]],hit:[0.6,1.05],bare:true,stowShield:true,work:'plant'},
 harvest:{keys:[[0],[0.35,{Rfx:11,Rfy:-14,Lfx:10,Lfy:-16,lean:0.45,crouch:0.35,step:0.35,back:0.2}],[0.55,{Rfx:11,Rfy:-15,Lfx:5,Lfy:-12,lean:0.48,crouch:0.37,step:0.35,back:0.2}],
  [0.75,{Rfx:11,Rfy:-14,Lfx:11,Lfy:-15,lean:0.45,crouch:0.35,step:0.35,back:0.2}],[1.1,{Rfx:3,Rfy:-10,Lfx:3,Lfy:-10,lean:0.05,crouch:0.05}],[1.4]],hit:[0.55],bare:true,stowShield:true,work:'harvest'},
 // climbing with the climbing gear (Mountains.dm): hand over hand up the face, the knees coming up in turn, on the
 // rope from a piton above; one cycle is one reach of each hand
 climb:{keys:[[0,{Rhx:1,Rhy:8,Lhx:2,Lhy:-4,crouch:0.16,step:0.22,back:-0.12}],[0.35,{Rhx:2,Rhy:-4,Lhx:1,Lhy:8,crouch:0.04,step:-0.08,back:0.16}],[0.7,{Rhx:1,Rhy:8,Lhx:2,Lhy:-4,crouch:0.16,step:0.22,back:-0.12}]],bare:true,stowShield:true,work:'climb'},
 // carrying: bent forward to lift it (the hands down to the ground in front), up, then held before it; the feet
 // stepping as it walks (wkCarry sets it going)
 lift:{keys:[[0],[0.3,{Rhx:1,Rhy:-22,Lhx:1,Lhy:-22,lean:0.6,crouch:0.45}],[0.55,{Rhx:0,Rhy:-20,Lhx:0,Lhy:-20,lean:0.55,crouch:0.45}],[0.9,{Rhx:-1,Rhy:-9,Lhx:-1,Lhy:-9,lean:0.05,crouch:0.05}],[1.0,{Rhx:-1,Rhy:-9,Lhx:-1,Lhy:-9}]]},
 carry:{keys:[[0,{Rhx:-1,Rhy:-9,Lhx:-1,Lhy:-9,step:0.25,back:0.1,crouch:0.04}],[0.3,{Rhx:-1,Rhy:-9.5,Lhx:-1,Lhy:-9.5,step:-0.1,back:-0.25,crouch:0.06}],
  [0.6,{Rhx:-1,Rhy:-9,Lhx:-1,Lhy:-9,step:0.25,back:0.1,crouch:0.04}]]},
 hold:{keys:[[0,{Rhx:-1,Rhy:-9,Lhx:-1,Lhy:-9,crouch:0.03}],[0.8,{Rhx:-1,Rhy:-9,Lhx:-1,Lhy:-9,crouch:0.03}]]},
});
SKWEAPON.woodchop=['hand axe','battle axe'];SKLEND.woodchop='hand axe:iron';SK.defs.carry.bare=SK.defs.lift.bare=SK.defs.hold.bare=true;SK.defs.carry.stowShield=SK.defs.lift.stowShield=SK.defs.hold.stowShield=true;   /* the tools set down to carry (Jobs.dm: heavy pieces) */

// A tool's head where it bites: its far end.
function wkTip(A){const d=A.doll,g=rdGearWorld(d,A.w),X=rdV.n(g.X);return rdV.add(g.o,rdV.mul(X,skLen(A.w.name)*A.w.s*0.92))}
// The tool bites: what flies off it.
function wkStrike(A){const w=A.D.work;if(['pick','gather','plant','harvest'].includes(w)){wkForage(A);return}if(!A.w)return;const P=wkTip(A),U=[0,1,0];
 if(w==='till'){const chips=(n,col,sp)=>{for(let i=0;i<n;i++)rdPart(P,[wkR(-sp,sp),wkR(0.4,1.2),wkR(-sp,sp)],wkR(0.4,0.7),0.014,0.012,[...col,1],[...col,1],6)};chips(10,[0.36,0.25,0.15],0.7);for(let i=0;i<3;i++)rdPx(P,[wkR(-0.2,0.2),wkR(0.05,0.2),wkR(-0.2,0.2)],0.7,0.05,0.09,'dust',0,1.5);return}
 if(w==='spearfish'){for(let i=0;i<12;i++)rdPx(P,[wkR(-0.4,0.4),wkR(0.5,1.1),wkR(-0.4,0.4)],0.55,0.04,0.03,'water',3);A.caught=A.opt.catch!=null?A.opt.catch:Math.random()<0.65;return}
 const chips=(n,col,sp)=>{for(let i=0;i<n;i++)rdPart(P,[wkR(-sp,sp),wkR(0.4,1.4),wkR(-sp,sp)],wkR(0.4,0.7),0.012,0.01,[...col,1],[...col,1],6)};
 if(w==='mine'){chips(9,[0.45,0.42,0.38],0.9);for(let i=0;i<3;i++)rdPx(P,[wkR(-0.2,0.2),wkR(0.1,0.3),wkR(-0.2,0.2)],0.7,0.05,0.09,'dust',0,1.5);if(Math.random()<0.4)rdSparks(P,5)}
 else if(w==='chop'){chips(7,[0.78,0.6,0.36],0.8);chips(3,[0.42,0.28,0.16],0.6);rdPx(P,[0,0.1,0],0.6,0.04,0.07,'dust',0,1.5)}
 else if(w==='smith'){rdSparks(P,12,[1,0.8,0.35]);for(let i=0;i<4;i++)rdPx(P,[wkR(-0.4,0.4),wkR(0.2,0.6),wkR(-0.4,0.4)],0.35,0.05,0.02,'spark',2)}
 else if(w==='build'){chips(5,[0.72,0.56,0.34],0.6);for(let i=0;i<3;i++)rdPx(P,[wkR(-0.2,0.2),wkR(0.05,0.2),wkR(-0.2,0.2)],0.7,0.05,0.09,'dust',0,1.5)}}

// The line goes out: the float flies from the rod's tip to the water ahead (opt.at, or two tiles on).
function wkCast(A){if(A.D.work==='netfish'){wkNetCast(A);return}const d=A.doll,tip=wkTip(A),F=rdV.n([...(A.opt.at?[A.opt.at[0]-d.O[0],0,A.opt.at[2]-d.O[2]]:[d.R[0]*A.sg,0,d.R[2]*A.sg])]);
 const P=A.opt.water||rdV.add([d.O[0],0,d.O[2]],rdV.mul(F,2.2));P[1]=rdGround(P[0],P[2])+0.02;A.float={P,from:tip,t0:performance.now()/1000}}
// Fishing as it goes: the line from the rod's tip to the float (or the fish), the float bobbing, the bite, the catch.
function wkFish(d,dt,b,emit,A){if(!A.w||!A.float)return;const tip=wkTip(A),F=A.float,now=performance.now()/1000;let at,fish=null;
 if(b<0.9){const u=Math.max(0,Math.min(1,(b-0.6)/0.3));at=rdV.add(rdV.add(F.from,rdV.mul(rdV.sub(F.P,F.from),u)),[0,Math.sin(Math.PI*u)*0.5,0])}   /* flying out */
 else if(b<2.6)at=rdV.add(F.P,[0,Math.sin(now*3.1)*0.012,0]);   /* waiting */
 else if(b<3.1){at=rdV.add(F.P,[0,-0.03-Math.abs(Math.sin(now*14))*0.03,0]);if(!F.bit){F.bit=true;for(let i=0;i<8;i++)rdPx(F.P,[wkR(-0.3,0.3),wkR(0.4,0.8),wkR(-0.3,0.3)],0.5,0.04,0.03,'water',3)}}   /* a bite */
 else if(b<3.6){const u=(b-3.1)/0.5;at=rdV.add(rdV.add(F.P,rdV.mul(rdV.sub(tip,F.P),u)),[0,Math.sin(Math.PI*u)*0.6,0]);fish=at}   /* reeled in */
 else{fish=rdV.add(tip,[0,-0.12,0]);at=fish}
 if(b>=0.6){WK.lines.push([tip,at]);if(!fish)WK.lines.push({float:at})}
 if(fish&&b<3.9){const q=rdQuat(...rdArrowBasis(rdV.n([Math.cos(now*18)*0.4,-1,Math.sin(now*18)*0.4])));emit('load.fish','iron',fish,q,d.k*1.5)}}

// Foraging: what comes away in the hand (a berry, a leaf, a seed going in, a stalk cut), as the game's pieces.
function wkForage(A){const d=A.doll,L=d.limbs,B=rdBasis(d),h=L.armRl?rdW(d,B,L.armRl.tip[0],L.armRl.tip[1],0.05):d.O,w=A.D.work;
 const bits=(n,col,sp,up)=>{for(let i=0;i<n;i++)rdPart(h,[wkR(-sp,sp),wkR(0,up),wkR(-sp,sp)],wkR(0.4,0.8),0.012,0.009,[...col,1],[...col,1],6)};
 if(w==='pick'){bits(4,[0.25,0.55,0.18],0.4,0.6);A.held={col:[0.75,0.1,0.15]}}
 else if(w==='gather'){bits(3,[0.3,0.25,0.15],0.3,0.4);for(let i=0;i<2;i++)rdPx(h,[0,0.1,0],0.6,0.04,0.07,'dust',0,1.5);A.held={col:[0.8,0.25,0.18]}}
 else if(w==='plant'){if(A.hits===0)bits(5,[0.36,0.25,0.15],0.3,0.5);else rdPx(h,[0,0.05,0],0.6,0.04,0.07,'dust',0,1.5)}
 else if(w==='harvest'){bits(6,[0.85,0.7,0.3],0.5,0.8);A.held={col:[0.85,0.7,0.3]}}}
// While foraging: the berry, mushroom or sheaf in its hand on the way to the bag.
function wkForageFx(d,dt,b,emit,A){if(!A.held)return;const D=A.D,last=D.keys[D.keys.length-1][0];if(b<D.hit[0]||b>last-0.2){if(b<D.hit[0])A.held=null;return}
 const L=d.limbs,B=rdBasis(d),h=L.armRl?rdW(d,B,L.armRl.tip[0],L.armRl.tip[1],0.06):d.O;const r=D.work==='harvest'?0.03:0.018;rdPart(h,[0,0,0],0.04,r,r,[...A.held.col,1],[...A.held.col,1])}   /* (a sheaf: bigger) */
// Spear fishing as it goes: the fish on the harpoon's point once pulled up (when it caught one).
function wkSpear(d,dt,b,emit,A){if(!A.w||!A.caught||b<1.0||b>2.15)return;const tip=wkTip(A),now=performance.now()/1000,g=rdGearWorld(d,A.w),X=rdV.n(g.X);
 const at=rdV.sub(tip,rdV.mul(X,4*A.w.s)),q=rdQuat(...rdArrowBasis(rdV.n(rdV.add(rdV.cross(X,[0,1,0]),[0,Math.sin(now*20)*0.4,0]))));emit('load.fish','iron',at,q,d.k*1.5)}
// The net: bundled in the hands, thrown out opening into a ring of cord over the water, sinking, then hauled back in,
// closing round what it caught.
const WKN=12,WKNR=0.34;
function wkNetCast(A){const d=A.doll,F=A.opt.at?rdV.n([A.opt.at[0]-d.O[0],0,A.opt.at[2]-d.O[2]]):[d.R[0]*A.sg,0,d.R[2]*A.sg],P=A.opt.water||rdV.add([d.O[0],0,d.O[2]],rdV.mul(F,0.95));   /* close in, a tile out */
 P[1]=rdGround(P[0],P[2])+0.01;A.net={P,F,caught:A.opt.catch!=null?A.opt.catch:Math.random()<0.7}}
function wkHands(d){const L=d.limbs,B=rdBasis(d),front=rdV.dot(B.Nn,rdV.sub(V3.eye||[0,10,10],d.O))>=0,n=(front?1:-1)*0.05,h=p=>L[p]?rdW(d,B,L[p].tip[0],L[p].tip[1],n):null,a=h('armRl'),c=h('armLl');
 return a&&c?rdV.mul(rdV.add(a,c),0.5):a||c||d.O}
function wkNet(d,dt,b,emit,A){const hands=wkHands(d),N=A.net;
 if(!N||b<0.62){emit('load.net','iron',rdV.add(hands,[0,-0.02,0]),[0,0,0,1],d.k);return}   /* bundled in its hands */
 let C,R,sink=0,closed=0;
 if(b<1.05){const u=(b-0.62)/0.43;C=rdV.add(rdV.add(hands,rdV.mul(rdV.sub(N.P,hands),u)),[0,Math.sin(Math.PI*u)*0.45,0]);R=0.06+WKNR*u}   /* flying out, opening */
 else if(b<2.4){C=N.P;R=WKNR;sink=Math.min(1,(b-1.05)/0.6);if(!N.splash){N.splash=true;for(let i=0;i<16;i++){const a=i/16*6.283;rdPx(rdV.add(N.P,[Math.cos(a)*WKNR,0,Math.sin(a)*WKNR]),[Math.cos(a)*0.2,wkR(0.3,0.6),Math.sin(a)*0.2],0.5,0.035,0.025,'water',3)}}}   /* on the water, sinking */
 else if(b<3.6){const u=(b-2.4)/1.2;C=rdV.add(N.P,rdV.mul(rdV.sub([hands[0],N.P[1],hands[2]],N.P),u*0.85));R=WKNR*(1-0.75*u);sink=1-u;closed=u}   /* hauled in, closing */
 else{const at=rdV.add([d.O[0],0,d.O[2]],rdV.mul(N.F,0.35));at[1]=rdGround(at[0],at[2]);emit('load.net','iron',rdV.add(at,[0,0.04,0]),[0,0,0,1],d.k);
  if(N.caught)for(let k=0;k<3;k++)emit('load.fish','iron',rdV.add(at,[Math.cos(k*2.1)*0.08,0.03,Math.sin(k*2.1)*0.08]),rdQ.axis([0,1,0],k*2.1),d.k*1.3);return}   /* on the ground at its feet, the catch on it */
 const y=C[1]-0.015*sink,pts=[];for(let i=0;i<WKN;i++){const a=i/WKN*6.283;pts.push([C[0]+Math.cos(a)*R,y+(closed?0.08*closed:0),C[2]+Math.sin(a)*R])}
 const mid=[C[0],y-0.02*sink+(closed?0.04*closed:0),C[2]];
 for(let i=0;i<WKN;i++){WK.lines.push([pts[i],pts[(i+1)%WKN]]);WK.lines.push([mid,pts[i]]);const q=rdV.mul(rdV.add(mid,pts[i]),0.5),r=rdV.mul(rdV.add(mid,pts[(i+1)%WKN]),0.5);WK.lines.push([q,r])}   /* its rim, spokes and a ring of mesh */
 if(b>=1.05)WK.lines.push([hands,pts[0]]);   /* the line back to its hands */
 if(N.caught&&b>2.4)for(let k=0;k<3;k++)emit('load.fish','iron',[mid[0]+Math.cos(b*9+k*2.1)*R*0.4,mid[1]+0.02,mid[2]+Math.sin(b*9+k*2.1)*R*0.4],rdQ.axis([0,1,0],b*6+k),d.k*1.3)}
// Climbing: t goes up (or down) the face of the rock at `at` (a cliff, height tiles high) in dur seconds, facing it,
// hand over hand, then over the lip onto the top (coming down: the same, backwards). In the game the climb's progress
// comes from the server (View3D.dm D["climb"]); here it runs on the clock. The rope hangs from a piton at the top of the
// face, pitons are driven in up it, and the coil is on its shoulder before and after. o (the game, game.js): base, the
// foot of the face; prog(), how far it has got (0-1, the server's); rope false for a race that climbs bare-handed;
// face, lip, top: how far from the foot toward the rock the face is, the top piton, and where it ends (a game block's).
function wkClimb(t,at,height,dur,up,o){o=o||{};const A=skAct(t,'climb',null,{loop:true,at,fx:(d,dt,b,emit,A2)=>{const C=A2.cl||(A2.cl={t0:performance.now()/1000,base:o.base?[...o.base]:[...A2.O0]});
   const u=o.prog?Math.max(0,Math.min(1,o.prog())):Math.min(1,(performance.now()/1000-C.t0)/dur),q=up?u:1-u,F=rdV.n([at[0]-C.base[0],0,at[2]-C.base[2]]),gy=rdGround(C.base[0],C.base[2]);
   const rise=Math.min(1,q/0.85),lip=Math.max(0,(q-0.85)/0.15),toFace=(o.face??0.82)*(1-lip)+(o.top??1.15)*lip;   /* up the face, then over the lip onto the top */
   A2.O0=[C.base[0]+F[0]*toFace,gy+height*rise+(lip>0?0.02:0),C.base[2]+F[2]*toFace];
   const top=[C.base[0]+F[0]*(o.lip??0.55),gy+height,C.base[2]+F[2]*(o.lip??0.55)],L=d.limbs,B=rdBasis(d),hn=p=>L[p]?rdW(d,B,L[p].tip[0],L[p].tip[1],0.02):A2.O0;
   if(o.rope!==false){WK.lines.push([top,hn('armRl')]);WK.lines.push([hn('armRl'),rdV.add(A2.O0,[0,-0.08,0])]);   /* the rope: from the piton to its hand, down past it */
    const X=rdV.mul(F,-1),Y=[0,1,0],q0=rdQuat(X,Y,rdV.cross(X,Y));emit('load.piton','iron',top,q0,d.k);
    for(let k=1;k<4;k++){const y=gy+height*k/4;if(y<A2.O0[1]+0.3)emit('load.piton','iron',[top[0],y,top[2]],q0,d.k)}}   /* driven in as it climbs */
   if(u>=1&&!A2.stop){A2.stop=true;A2.opt.then=(d2)=>{t.g3dir=0;if(up&&!o.prog){t.x=Math.round(at[0]);t.y=Math.round(-at[2]);t.dx=t.x;t.dy=t.y;t.ly=height}d2.done=true;rdBack(t)}}}});
 if(A){A.climbing=true;wkShowBack(t)}return A}
// A climber is always seen from behind: turned to the face if that is its back picture, else the way most away from
// the eye (v3face picks the picture from the unit's way and the camera).
function wkShowBack(t){if(typeof v3face!=='function'||v3face(t)===1){t.g3dir=t.dir;return}const sy=Math.sin(V3.yaw||0),cy=Math.cos(V3.yaw||0);let best=1,bv=-9;
 for(const d of [1,2,4,8,5,6,9,10]){const fx=(d&4?1:0)-(d&8?1:0),fz=(d&2?1:0)-(d&1?1:0),v=(fx*-sy+fz*-cy)/Math.hypot(fx,fz);if(v>bv){bv=v;best=d}}
 t.dir=t.g3dir=best;const kd=V3.disp.get(t.key);if(kd&&kd.rc)kd.rc.ep=null}   /* g3dir: kept over the game's updates (game.js g3adopt) */
// Carrying: what is held, between the hands, in front of it (behind it, hidden, from its back).
function wkCard(P,d,lift){const C=WKSACK,eye=V3.eye||[0,10,10],D=rdV.n([eye[0]-P[0],0,eye[2]-P[2]]),R=rdV.n(rdV.cross([0,1,0],D)),s=d.k*1.3,hw=C.w/2*s,h=C.h*s,y0=P[1]-(lift||0)*h;
 WK.cards.push([C.tex,rdV.add([P[0],y0,P[2]],rdV.add(rdV.mul(R,-hw),rdV.mul(D,0.02))),rdV.add([P[0],y0,P[2]],rdV.add(rdV.mul(R,hw),rdV.mul(D,0.02))),h])}
// (called by ragdoll.js once it has cleared its pictures this frame)
function wkCards(){for(const [tex,a,b,h] of WK.cards){let va=RD.va.get(tex);if(!va){va=new VA();RD.va.set(tex,va)}quad(va,a,b,rdV.add(b,[0,h,0]),rdV.add(a,[0,h,0]),QN0,[1,1,1,1],[0,1,1,1,1,0,0,0])}WK.cards.length=0}
function wkLoad(d,emit,kind){const L=d.limbs,B=rdBasis(d),front=rdV.dot(B.Nn,rdV.sub(V3.eye||[0,10,10],d.O))>=0,n=(d.fl==='N'?-1:1)*(front?1:-1)*0.06;
 const hand=p=>L[p]?rdW(d,B,L[p].tip[0],L[p].tip[1],n):null,a=hand('armRl'),c=hand('armLl');if(!a&&!c)return null;const m=a&&c?rdV.mul(rdV.add(a,c),0.5):a||c;
 const t=d.t,dir=t.dir||2,Fw=rdV.n([((dir&4)?1:0)-((dir&8)?1:0),0,((dir&2)?1:0)-((dir&1)?1:0)]),across=rdV.n(rdV.cross([0,1,0],Fw));
 const X=kind==='log'?across:kind==='barrel'?[0,1,0]:across,Y=kind==='barrel'?Fw:[0,1,0],Z=rdV.cross(X,Y);
 if(kind==='sack'){const at=rdV.add(m,[0,-0.02,0]);wkCard(at,d,0.45);return at}   /* the pixel sack, held by its middle */
 const at=rdV.add(m,[0,kind==='log'?0.02:kind==='barrel'?-0.02:0.03,0]);emit('load.'+kind,'iron',at,rdQuat(X,Y,Z),d.k*(WKBIG[kind]||1));return at}
// t lifts a load lying on the ground in front of it (a sack, a barrel, a log, a stone, ore), then holds it, walking
// steps tiles ahead if asked; struck while carrying, it drops it.
function wkCarry(t,kind,steps){const bare=d=>{if(!d.wkBare){d.wkBare=true;skStow(d,true)}};   /* both hands on the load: its weapon and shield on its back */
 const hold=(d)=>skAct(t,'hold',null,{loop:true,doll:d,fx:(d2,dt,b,emit,A2)=>{bare(d2);WK.carry.set(t,{A:A2,d:d2,kind,at:wkLoad(d2,emit,kind)})}});
 const lift=skAct(t,'lift',null,{fx:(d,dt,b,emit)=>{bare(d);const C=WK.carry.get(t);if(C)C.d=d;if(b>0.45){if(C)C.at=wkLoad(d,emit,kind)}else wkGround(d,emit,kind)},
  then:(d)=>{if(!steps){hold(d);return}const dir=t.dir||2,Fw=rdV.n([((dir&4)?1:0)-((dir&8)?1:0),0,((dir&2)?1:0)-((dir&1)?1:0)]),until=steps/1.1;
   skAct(t,'carry',null,{loop:true,doll:d,walk:{dir:Fw,speed:1.1,until},fx:(d2,dt,b,emit,A2)=>{bare(d2);WK.carry.set(t,{A:A2,d:d2,kind,at:wkLoad(d2,emit,kind)});
     if(A2.walked>=until&&!A2.stop){A2.stop=true;t.x=Math.round(d2.O[0]);t.y=Math.round(-d2.O[2]);t.dx=t.x;t.dy=t.y;A2.opt.then=hold}}})}});
 WK.carry.set(t,{A:lift,kind});return lift}
function wkGround(d,emit,kind){const t=d.t,dir=t.dir||2,Fw=rdV.n([((dir&4)?1:0)-((dir&8)?1:0),0,((dir&2)?1:0)-((dir&1)?1:0)]),P=rdV.add([d.O[0],0,d.O[2]],rdV.mul(Fw,0.32));
 P[1]=rdGround(P[0],P[2]);if(kind==='sack'){wkCard(P,d,0);return}const big=WKBIG[kind]||1;P[1]+=(kind==='barrel'?6:3)*d.k*big;
 const X=kind==='barrel'?[0,1,0]:rdV.n(rdV.cross([0,1,0],Fw)),Y=kind==='barrel'?Fw:[0,1,0];emit('load.'+kind,'iron',P,rdQuat(X,Y,rdV.cross(X,Y)),d.k*big)}
// Struck or killed while carrying: the load drops and rolls.
function wkInterrupt(t,from){const C=WK.carry.get(t);if(!C)return;WK.carry.delete(t);for(const A of SK.acts)if(A.t===t){A.stop=true;A.opt.loop=false;A.opt.then=null;if(A.doll)A.doll.done=true}
 SK.acts=SK.acts.filter(A=>A.t!==t);if(!C.at)return;
 if(C.kind==='sack'){const P=[C.at[0]+(from?from[0]*0.15:0),0,C.at[2]+(from?from[2]*0.15:0)];P[1]=rdGround(P[0],P[2]);WK.dropped=(WK.dropped||[]).concat([{P,d:C.d}]);return}
 RD.loose.push({name:'load.'+C.kind,tier:'iron',s:((C.d&&C.d.k)||0.0156)*(WKBIG[C.kind]||1),c:[0,0,0],r:0.06,X:[...C.at],V:rdV.add(rdV.mul(from||[0,0,1],0.6),[0,0.8,0]),q:[0,0,0,1],w:[wkR(-4,4),wkR(-4,4),wkR(-4,4)],rest:false,flat:2,bounce:0})}
// A job going round: the unit works at a spot (at, in the world) till wkStop.
function wkStart(t,job,at,opt){if(job==='chop')job='woodchop';   /* felling: not the axe's fighting chop (skills.js) */if(!SK.defs[job])return null;return skAct(t,job,null,Object.assign({loop:true,at,fx:job==='fish'?wkFish:job==='spearfish'?wkSpear:job==='netfish'?wkNet:['pick','gather','plant','harvest'].includes(job)?wkForageFx:null},opt||{}))}
function wkStop(t){const C=WK.carry.get(t);if(C){wkInterrupt(t,[0,0,0]);const b=RD.loose[RD.loose.length-1];if(b&&C.at){b.V=[0,0.2,0];b.w=[0,0,0]}rdBack(t);return}   /* set down where it stands */
 for(const A of SK.acts)if(A.t===t)A.stop=true}
// Something to work at, for the arena (in the game: the real rock, tree, anvil): name 'rock', 'trunk', 'anvil'.
function wkProp(name,X,Z,turn,scale){const y=rdGround(X,Z);WK.props.push({name:'prop.'+name,P:[X,y,Z],q:rdQ.axis([0,1,0],turn||0),s:0.0156*(scale||1)})}
// Each frame: the props, the fishing lines (gathered this frame, drawn with the trails), the floats.
function wkDraw(emit){for(const p of WK.props)emit(p.name,'iron',p.P,p.q,p.s);for(const s of WK.dropped||[])if(s.d)wkCard(s.P,s.d,0)}
function wkLinesDraw(va){const eye=V3.eye||[0,10,10];for(const l of WK.lines){if(l.float){const P=l.float,R=rdV.n(rdV.cross([0,1,0],rdV.sub(eye,P))),r=0.018;
   quad(va,rdV.sub(P,rdV.mul(R,r)),rdV.add(P,rdV.mul(R,r)),rdV.add(rdV.add(P,rdV.mul(R,r)),[0,r*1.6,0]),rdV.add(rdV.sub(P,rdV.mul(R,r)),[0,r*1.6,0]),QN0,[0.85,0.15,0.1,1]);continue}
  const [a,b]=l,D=rdV.n(rdV.sub(eye,a)),S=rdV.mul(rdV.n(rdV.cross(rdV.sub(b,a),D)),0.0025);quad(va,rdV.sub(a,S),rdV.add(a,S),rdV.add(b,S),rdV.sub(b,S),QN0,[0.92,0.92,0.88,0.85])}
 WK.lines.length=0}

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

// World bosses (the user, 2026-10-25): a mountain guardian built of the mountains' own rock and an ent of the forest's
// own trees, like Shadow of the Colossus's: they never attack. They walk, and they shake off whoever climbs them, so
// climbers die by the fall and by the traps on the way up to the weak points they must strike (glowing crystals on the
// guardian, sap knots on the ent). Each is built once from the 3D world's own pieces (the page's MD: boulders and
// clumps, tapered limbs, roots, the rock, leaf and bark colours), one part to a bone; posed each frame by its skeleton
// and drawn as lit triangles in the world's light. Sizes in tiles.
const BS={kinds:{},list:[],va:null};
// The skeleton: bone, parent, where its joint sits on the parent's (tiles, at scale 1). Limbs hang down their bone (-y).
const BSBONES=[['pelvis',null,[0,4.2,0]],['chest','pelvis',[0,0.5,0]],['head','chest',[0,2.7,0.15]],
 ['uarmL','chest',[-2.15,2.1,0]],['farmL','uarmL',[0,-2.2,0]],['handL','farmL',[0,-2.0,0]],
 ['uarmR','chest',[2.15,2.1,0]],['farmR','uarmR',[0,-2.2,0]],['handR','farmR',[0,-2.0,0]],
 ['thighL','pelvis',[-1.0,-0.2,0]],['shinL','thighL',[0,-2.0,0]],['footL','shinL',[0,-1.9,0]],
 ['thighR','pelvis',[1.0,-0.2,0]],['shinR','thighR',[0,-2.0,0]],['footR','shinR',[0,-1.9,0]]];
const BSI={};BSBONES.forEach((b,i)=>BSI[b[0]]=i);

// --- building them from the world's own assets ------------------------------------------------------------------
// Mountain rock blocks: the terrain's own builder (v3rockStack), given a little made-up grid of tiles (cells: [i, j,
// blocks, vein]), so each part is real mountain blocks, faces between them closed up, grass on a top edge, ore veins
// on the faces. Then centred, scaled (sx, sy, sz) and placed (ox, oy, oz) in the bone's frame; flip: hung down the bone.
function bsXform(src,dst,sx,sy,sz,ox,oy,oz,flip,cx,cy,cz){for(let v=0;v<src.length;v+=12){let x=(src[v]-cx)*sx,y=(src[v+1]-cy)*sy,z=(src[v+2]-cz)*sz,nx=src[v+3]/sx,ny=src[v+4]/sy,nz=src[v+5]/sz;
  if(flip){y=-y;z=-z;ny=-ny;nz=-nz}const l=Math.hypot(nx,ny,nz)||1;dst.push(x+ox,y+oy,z+oz,nx/l,ny/l,nz/l,0,0,src[v+8],src[v+9],src[v+10],1)}}   /* alpha 1: none of the terrain's own effects (rock tag, tree sway) */
function bsBox(a,f){let x0=1e9,y0=1e9,z0=1e9,x1=-1e9,y1=-1e9,z1=-1e9;for(let v=0;v<a.length;v+=12){if(f&&!f(a,v))continue;x0=Math.min(x0,a[v]);x1=Math.max(x1,a[v]);y0=Math.min(y0,a[v+1]);y1=Math.max(y1,a[v+1]);z0=Math.min(z0,a[v+2]);z1=Math.max(z1,a[v+2])}return [x0,y0,z0,x1,y1,z1]}
function bsRocks(dst,cells,seed,sx,sy,sz,ox,oy,oz,flip){const src=[],warm=BS.warm,T={x0:seed*7,y0:seed*13,z:1},map=new Map();for(const [i,j,n,vein] of cells)map.set(i+','+j,{kind:'wall',blocks:n,biome:'',vein:vein||null});
 const kindAt=(i,j)=>map.get(i+','+j)||null;for(const [i,j] of cells)v3rockStack(()=>src,T,kindAt,i,j,T.x0+i,0,-(T.y0+j),kindAt(i,j));
 if(warm)for(let v=0;v<src.length;v+=12){const lit=src[v+8]>0.8&&src[v+9]>0.4&&src[v+10]<0.4;if(lit)continue;src[v+8]=Math.min(1,src[v+8]*warm[0]);src[v+9]=Math.min(1,src[v+9]*warm[1]);src[v+10]=Math.min(1,src[v+10]*warm[2])}   /* the guardian's warm stone (not its lava) */
 const B=bsBox(src);bsXform(src,dst,sx,sy,sz,ox,oy,oz,false,(B[0]+B[3])/2,flip?B[4]:B[1],(B[2]+B[5])/2)}   /* hung: its top at the joint, down the bone */
// Trees: the world's own (MD.bigTree: oak, pine, birch), a slice of one by height (the trunk, the roots, the crown),
// centred on its trunk and scaled into the bone; flip: hung down the bone (a branch arm's crown is its hand).
function bsTree(dst,kind,seed,y0,y1,sx,sy,sz,ox,oy,oz,flip,top){const src=[];MD.bigTree(src,0,0,0,{state:'',biome:''},seed,seed*3+1,kind);
 const tri=[];for(let v=0;v<src.length;v+=36){const cy=(src[v+1]+src[v+13]+src[v+25])/3;if(cy>=y0&&cy<y1)for(let k=0;k<36;k++)tri.push(src[v+k])}
 const B=bsBox(tri),base=top?B[4]:Math.max(B[1],y0);bsXform(tri,dst,sx,sy,sz,ox,oy,oz,flip,0,base,0)}
const BSCRYS=[0.6,0.95,1,1],BSSAP=[1,0.72,0.25,1];
function bsGlow(dst,x,y,z,r,c,seed){for(let k=0;k<6;k++){const a=k*1.05+seed;MD.gem(dst,x+Math.cos(a)*r*0.45,y+(k%3)*r*0.22,z+Math.sin(a)*r*0.45,r*(0.32+(k%2)*0.18),c)}}

// The guardian, as close as can be to the stone golem the user picked (2026-10-25, a D&D miniature on Sketchfab, used
// as a look only): squat and wide, smooth rounded sandstone blocks fitted together, carved spirals (a ram's-horn pair on
// the round chest plate, more on the shoulders, the thighs and the back), a small block head under a heavy brow set
// low in a collar of stones, huge shoulders standing above it, arms hanging to the ground on block fists, short pillar
// legs. The spirals that glow are its weak points.
const BSSAND=[0.84,0.71,0.53],BSGROOVE=[0.43,0.34,0.25,1],BSRUNE=[1,0.68,0.28,1];
// A rounded block: a box (half sizes hx, hy, hz) with its edges rounded off by r, a little uneven, flat-shaded facets.
function bsRB(dst,cx,cy,cz,hx,hy,hz,r,c,seed,jit=0.035){const N=3,h=[hx,hy,hz],pt=(a)=>{const q=[a[0]*hx,a[1]*hy,a[2]*hz],o=[0,0,0];let dl=0;
  for(let k=0;k<3;k++){const m=h[k]-r;o[k]=Math.max(-m,Math.min(m,q[k]));dl+=(q[k]-o[k])**2}dl=Math.sqrt(dl)||1;
  const j=1+(MD.h(Math.round(a[0]*7)+seed,Math.round(a[1]*7)*13+Math.round(a[2]*7)*29,3)-0.5)*2*jit;return [cx+(o[0]+(q[0]-o[0])/dl*r)*j,cy+(o[1]+(q[1]-o[1])/dl*r)*j,cz+(o[2]+(q[2]-o[2])/dl*r)*j]};
 const out=[cx,cy,cz];for(let ax=0;ax<3;ax++)for(const sg of [-1,1]){const u=(ax+1)%3,v=(ax+2)%3,tone=MD.shade(c,0.94+MD.h(seed,ax*2+(sg>0?1:0),5)*0.12);
  for(let i=0;i<N;i++)for(let j=0;j<N;j++){const g=(ii,jj)=>{const a=[0,0,0];a[ax]=sg;a[u]=-1+2*ii/N;a[v]=-1+2*jj/N;return pt(a)};const p00=g(i,j),p10=g(i+1,j),p11=g(i+1,j+1),p01=g(i,j+1);
   MD.f(dst,p00,p10,p11,tone,out);MD.f(dst,p00,p11,p01,tone,out)}}}
// A spiral line on a face: carved (dark), or glowing (a weak point). n: the face's outward axis (x, y or z sign).
function bsSpiral(dst,cx,cy,cz,R,turns,sd,glow,face){const pts=[];for(let k=0;k<=22;k++){const u=k/22,a=u*turns*6.2832+sd,r=R*(0.12+0.88*u),c=Math.cos(a)*r,s=Math.sin(a)*r;
  pts.push(face==='x'?[cx,cy+s,cz+c]:face==='-z'?[cx-c,cy+s,cz]:[cx+c,cy+s,cz])}
 for(let k=0;k+1<pts.length;k++)MD.limb(dst,pts[k],pts[k+1],glow?0.045:0.035,glow?0.04:0.03,4,glow?BSRUNE:BSGROOVE,950+k)}
function bsBuildGuardian(){const P={},S=[],part=n=>P[n]||(P[n]=[]),sand=k=>MD.shade(BSSAND,0.93+((k*37)%13)/100),rb=(n,cx,cy,cz,hx,hy,hz,r,k)=>bsRB(part(n),cx,cy,cz,hx,hy,hz,r,sand(k),k);
 // the chest: a round plate in the middle, blocks round it, a collar of stones round the head, the back
 rb('chest',0,1.55,0.42,1.25,1.2,0.62,0.42,1);rb('chest',-1.25,1.25,0.25,0.62,0.85,0.7,0.3,2);rb('chest',1.25,1.25,0.25,0.62,0.85,0.7,0.3,3);
 rb('chest',0,0.38,0.32,0.95,0.42,0.68,0.25,4);rb('chest',-0.95,0.35,0.2,0.48,0.4,0.6,0.22,5);rb('chest',0.95,0.35,0.2,0.48,0.4,0.6,0.22,6);
 rb('chest',0,1.6,-0.55,1.55,1.45,0.7,0.4,7);rb('chest',-1.1,0.8,-0.5,0.6,0.7,0.6,0.25,8);rb('chest',1.1,0.8,-0.5,0.6,0.7,0.6,0.25,9);
 rb('chest',-0.85,2.75,0.2,0.55,0.42,0.62,0.26,10);rb('chest',0.85,2.75,0.2,0.55,0.42,0.62,0.26,11);rb('chest',0,2.95,-0.35,0.85,0.38,0.55,0.25,12);rb('chest',-0.35,3.05,0.45,0.32,0.28,0.3,0.15,13);rb('chest',0.4,3.1,0.4,0.3,0.25,0.3,0.14,14);
 // the shoulders: great rounded masses standing above the head
 for(const sx of [-1,1]){rb('chest',sx*2.15,2.55,0.05,0.95,0.82,0.95,0.42,20+sx);rb('chest',sx*2.0,3.3,0.0,0.68,0.42,0.7,0.26,22+sx);rb('chest',sx*2.75,2.4,-0.1,0.42,0.6,0.62,0.22,24+sx);
  bsSpiral(part('chest'),sx*2.15,2.55,1.02,0.42,1.7,sx>0?2.2:0.4,false)}
 bsSpiral(part('chest'),-0.52,1.62,1.06,0.46,1.8,0.3,true);bsSpiral(part('chest'),0.52,1.62,1.06,0.46,1.8,3.4,true);   /* the ram's horns on its chest: weak points */
 MD.limb(part('chest'),[0,2.05,1.04],[0,1.05,1.06],0.07,0.05,4,BSGROOVE,960);MD.limb(part('chest'),[-0.45,1.05,1.05],[0.45,1.05,1.05],0.05,0.05,4,BSGROOVE,961);
 bsSpiral(part('chest'),0,1.7,-1.27,0.55,1.9,1.0,true,'-z');S.push({name:'core',bone:'chest',at:[0,1.7,-1.4],weak:true});
 S.push({name:'horns',bone:'chest',at:[0,1.6,1.2],weak:true});
 // the hips and the head
 rb('pelvis',0,0,0.05,1.35,0.5,0.78,0.3,30);rb('pelvis',-0.95,-0.1,0,0.55,0.45,0.6,0.22,31);rb('pelvis',0.95,-0.1,0,0.55,0.45,0.6,0.22,32);
 rb('head',0,0.42,0,0.55,0.45,0.5,0.18,40);rb('head',0,0.78,0.22,0.62,0.17,0.38,0.1,41);rb('head',0,0.3,0.42,0.16,0.22,0.12,0.06,42);
 for(const x of [-0.22,0.22])MD.blob(part('head'),x,0.55,0.5,0.12,0.04,0.03,[0.2,0.13,0.08,1],43,0.04);   /* deep-set eyes under the brow */
 S.push({name:'crown',bone:'head',at:[0,1.0,0]});
 // arms to the ground, block fists; short pillar legs
 for(const s of ['L','R']){const sx=s==='L'?-1:1,k=s==='L'?50:70;
  rb('uarm'+s,0,-0.55,0,0.78,0.62,0.74,0.3,k);rb('uarm'+s,0,-1.45,0.02,0.7,0.55,0.68,0.26,k+1);
  rb('farm'+s,0,-0.95,0.05,0.92,1.0,0.86,0.36,k+2);bsSpiral(part('farm'+s),sx*0.93,-0.95,0.05,0.38,1.6,k,false,'x');
  rb('hand'+s,0,-0.52,0.12,0.92,0.5,0.95,0.3,k+3);for(let q=0;q<3;q++)rb('hand'+s,-0.5+q*0.5,-0.9,0.55,0.22,0.2,0.26,0.1,k+4+q);
  rb('thigh'+s,0,-0.5,0,0.82,0.55,0.82,0.3,k+8);bsSpiral(part('thigh'+s),0,-0.5,0.83,0.3,1.5,k,false);
  rb('shin'+s,0,-0.45,0.02,0.78,0.5,0.78,0.28,k+9);rb('foot'+s,0,-0.2,0.25,0.88,0.26,1.0,0.16,k+10);
  S.push({name:'calf'+s,bone:'shin'+s,at:[0,-0.5,-0.82]},{name:'thigh'+s,bone:'thigh'+s,at:[0,-0.5,-0.86]},{name:'fist'+s,bone:'hand'+s,at:[0,-0.1,0.2]})}
 S.push({name:'back',bone:'chest',at:[0,0.9,-1.3]},{name:'shoulder',bone:'chest',at:[-2.1,3.75,0]});
 // its build: squat, hips low, shoulders wide and high, the head low in its collar; it stands hunched, arms to the ground
 const off={pelvis:[0,2.25,0],chest:[0,0.32,0],head:[0,2.55,0.55],uarmL:[-2.35,2.55,0.1],uarmR:[2.35,2.55,0.1],farmL:[0,-1.95,0],farmR:[0,-1.95,0],handL:[0,-1.9,0],handR:[0,-1.9,0],
  thighL:[-0.95,-0.2,0],thighR:[0.95,-0.2,0],shinL:[0,-1.05,0],shinR:[0,-1.05,0],footL:[0,-0.95,0],footR:[0,-0.95,0]};
 const rest={chest:[0.16,0,0],head:[-0.12,0,0],uarmL:[0.2,0,-0.06],uarmR:[0.2,0,0.06],farmL:[-0.1,0,0],farmR:[-0.1,0,0]};
 return {P,S,H:6.1,off,rest,scale:1.6,route:['calfL','thighL','back','core','shoulder','crown']}}

function bsBuildEnt(){const P={},S=[],part=n=>P[n]||(P[n]=[]);
 // an oak for its body (the trunk) and its head (the crown); oak boughs for its arms, hung from the shoulders, small oak
 // crowns its hands; oak trunks for its legs, the roots its feet
 bsTree(part('chest'),'oak',31,0.25,1.9,4.2,1.65,4.2,0,0,0);bsTree(part('head'),'oak',31,1.9,99,1.25,1.15,1.25,0,-0.4,0);
 bsTree(part('pelvis'),'oak',32,0.2,1.2,4.6,1.0,4.6,0,-0.6,0);
 for(const s of ['L','R']){const k=s==='L'?40:50;
  bsTree(part('uarm'+s),'oak',k+1,0.2,1.2,2.9,2.2,2.9,0,0.2,0,true);bsTree(part('farm'+s),'oak',k+6,0.9,1.9,2.4,2.0,2.4,0,0.05,0,true);bsTree(part('hand'+s),'oak',k+2,1.9,99,0.55,0.5,0.55,0,0.1,0,true);
  bsTree(part('thigh'+s),'oak',k+3,0.6,1.9,2.6,1.55,2.6,0,0.05,0,true);bsTree(part('shin'+s),'oak',k+4,0.25,1.2,2.4,2.1,2.4,0,0.05,0,true);bsTree(part('foot'+s),'oak',k+5,-1,0.3,2.4,1.6,2.4,0,0.3,0.15,false,true);
  S.push({name:'calf'+s,bone:'shin'+s,at:[0,-1.0,-0.55]},{name:'thigh'+s,bone:'thigh'+s,at:[0,-0.9,-0.6]})}
 for(const x of [-0.3,0.3])MD.blob(part('chest'),x,2.05,0.85,0.13,0.1,0.07,BSSAP,24,0.05);   /* its eyes: sap glowing in the bark */
 bsGlow(part('chest'),0,1.4,-0.9,0.42,BSSAP,4);S.push({name:'core',bone:'chest',at:[0,1.45,-1.05],weak:true});
 bsGlow(part('head'),0,2.4,0,0.4,BSSAP,5);S.push({name:'crown',bone:'head',at:[0,2.5,0],weak:true});
 bsGlow(part('farmR'),0,-1.0,0.32,0.26,BSSAP,6);S.push({name:'band',bone:'farmR',at:[0,-1.0,0.45],weak:true});
 S.push({name:'back',bone:'chest',at:[0,0.9,-0.95]},{name:'shoulder',bone:'chest',at:[-1.4,2.5,-0.2]});
 return {P,S,H:11,route:['calfL','thighL','back','core','shoulder','crown']}}

// The stone golem the user made in Blender (Stone_Golem.blend; art/gear3d/golem/export_golem.py bakes its occlusion into
// vertex colours and decimates it: boss-golem.json): its 64 stones put on the skeleton by their names, each bone's
// joint where the stones meet (shoulder, elbow, wrist, hip, knee, ankle). Until it is in, the guardian is built here.
BS.assets={};
function bsAsset(name,url){const a=BS.assets[name];if(a!==undefined)return a;BS.assets[name]=null;
 fetch(url).then(r=>{if(!r.ok)throw r.status;return r.json()}).then(d=>{BS.assets[name]=d;delete BS.kinds.guardian}).catch(()=>{BS.assets[name]=false;BS.wait=Math.min(60000,(BS.wait||2500)*2);setTimeout(()=>{if(BS.assets[name]===false)delete BS.assets[name]},BS.wait)});return null}   /* not there yet (the game sends it with the first golem): asked again, less and less often */
const BSGOLEMBONE=[[/^Head\b/,'head'],[/^(Pelvis|Hip [LR])\b/,'pelvis'],[/^Upper arm ([LR])/,'uarm'],[/^(Elbow|Forearm) ([LR])/,'farm'],[/^Hand ([LR])/,'hand'],[/^Leg ([LR]) . Upper thigh/,'thigh'],
 [/^(Knee|Leg) ([LR])/,'shin'],[/^Foot ([LR])/,'foot'],[/./,'chest']];
// joints in the model's own units (cm; Blender: x right, y back, z up)
const BSGOLEMJ={pelvis:[0,0.14,1.94],chest:[0,0.15,2.3],head:[0,-0.9,3.85],uarmL:[-2.25,0.05,4.2],farmL:[-2.5,0.05,2.95],handL:[-2.9,-0.15,1.35],thighL:[-1.0,0.05,2.0],shinL:[-1.12,-0.1,1.15],footL:[-1.15,-0.1,0.5]};
const BSLIME=[0.87,0.8,0.68];
function bsBuildGolem(G){const dec=(b,T)=>{const s=atob(b),u=new Uint8Array(s.length);for(let i=0;i<s.length;i++)u[i]=s.charCodeAt(i);return new T(u.buffer)};
 const J=n=>{if(BSGOLEMJ[n])return BSGOLEMJ[n];const m=n.match(/^(.*)R$/);if(m&&BSGOLEMJ[m[1]+'L']){const q=BSGOLEMJ[m[1]+'L'];return [-q[0],q[1],q[2]]}return [0,0,0]};
 const pg=(q)=>[q[0],q[2],-q[1]];   /* the model's axes to the page's: y up, +z its front */
 const P={},S=[],box={};
 for(const p of G.parts){let bone='chest';for(const [re,b] of BSGOLEMBONE){const m=p.name.match(re);if(m){const side=(m.slice(1).find(x=>x==='L'||x==='R'))||'';bone=b+(b==='chest'||b==='pelvis'||b==='head'?'':side);break}}
  const pos=dec(p.pos,Int16Array),nrm=dec(p.nrm,Int8Array),ao=dec(p.ao,Uint8Array),j=pg(J(bone)),out=P[bone]||(P[bone]=[]),tone=0.95+((p.name.length*37)%11)/100;
  const bx=box[p.name]=[1e9,1e9,1e9,-1e9,-1e9,-1e9];
  for(let i=0;i<p.n;i++){const q=pg([pos[i*3]/1000,pos[i*3+1]/1000,pos[i*3+2]/1000]),n=pg([nrm[i*3]/127,nrm[i*3+1]/127,nrm[i*3+2]/127]),k=(0.42+0.58*ao[i]/255)*tone;
   for(let c=0;c<3;c++){bx[c]=Math.min(bx[c],q[c]);bx[c+3]=Math.max(bx[c+3],q[c])}
   out.push(q[0]-j[0],q[1]-j[1],q[2]-j[2],n[0],n[1],n[2],0,0,Math.min(1,BSLIME[0]*k),Math.min(1,BSLIME[1]*k),Math.min(1,BSLIME[2]*k),1)}}
 // a spot on a stone's back (or top, or front), in its bone's frame
 const spot=(name,stone,bone,face,weak)=>{const b=box[Object.keys(box).find(k=>k.startsWith(stone))];if(!b)return;const j=pg(J(bone)),c=[(b[0]+b[3])/2,(b[1]+b[4])/2,(b[2]+b[5])/2];
  const at=face==='back'?[c[0],c[1],b[2]-0.05]:face==='top'?[c[0],b[4]+0.05,c[2]]:[c[0],c[1],b[5]+0.05];S.push({name,bone,at:[at[0]-j[0],at[1]-j[1],at[2]-j[2]],weak:!!weak})};
 spot('calfL','Leg L • Short shin','shinL','back');spot('calfR','Leg R • Short shin','shinR','back');spot('thighL','Leg L • Upper thigh','thighL','back');spot('thighR','Leg R • Upper thigh','thighR','back');
 spot('back','Back L • Hip spiral wedge','chest','back');spot('core','Back • Broad double-volute','chest','back',true);spot('shoulder','Shoulder L • Rear mass','chest','top');
 spot('crown','Crown L • Upper arch wedge','chest','top',true);spot('band','Forearm R • Outer spiral','farmR','front',true);spot('horns','Chest L • Large volute','chest','front',true);
 // handholds (the user: little rocks to hold on to): knobs of rock on its back, legs, shoulders and arms. A climber who
 // has reached one and grips it (fast enough, or told to hold on) is not shaken off; between them it is tested.
 const hold=(name,stone,bone,face,dy=0)=>{const before=S.length;spot(name,stone,bone,face);const q=S[before];if(!q)return;q.hold=true;q.at[1]+=dy;
  const k=MD.shade(MD.PAL.rock[1],0.62),o=P[bone]||(P[bone]=[]),tmp=[];MD.blob(tmp,q.at[0],q.at[1],q.at[2]+(face==='back'?-0.06:face==='top'?0:0.06),0.17,0.11,0.13,k,name.length*7,0.2);
  for(let v=0;v<tmp.length;v+=12)o.push(...tmp.slice(v,v+11),1)};
 hold('heelL','Foot L • Heel','footL','back');hold('h_calfL','Leg L • Short shin','shinL','back');hold('h_thighL','Leg L • Upper thigh','thighL','back',-0.25);hold('h_hipL','Hip L • Flanking','pelvis','back');
 hold('h_back','Back L • Hip spiral wedge','chest','back',0.2);hold('h_core','Back • Broad double-volute','chest','back',0.55);hold('h_upback','Back • Top transverse crown','chest','back');
 hold('h_shoulder','Shoulder L • Rear mass','chest','top');hold('h_crown','Crown L • Upper arch wedge','chest','top');hold('h_uarmR','Upper arm R • Hanging block','uarmR','back');hold('h_farmR','Forearm R • Massive gauntlet','farmR','back');
 const off={};for(const [n,par] of BSBONES){if(!par){off[n]=pg(J(n));continue}const a=pg(J(n)),b=pg(J(par));off[n]=[a[0]-b[0],a[1]-b[1],a[2]-b[2]]}
 const rest={chest:[0.08,0,0],uarmL:[0.06,0,0],uarmR:[0.06,0,0]};
 return {P,S,H:6.1,off,rest,scale:1.65,foot:2,route:['heelL','h_calfL','h_thighL','h_hipL','h_back','h_core','h_upback','h_shoulder','h_crown'],asset:true}}   /* foot: 2 x 2 tiles each (its foot stones, about 1.2 x 1.4 cm, at 1.65 tiles a cm) */

function bsKind(kind){let K=BS.kinds[kind];if(K)return K;if(typeof MD==='undefined'||!MD.blob)return null;
 const G=kind==='guardian'?bsAsset('golem','boss-golem.json'):null;K=kind==='ent'?bsBuildEnt():G?bsBuildGolem(G):bsBuildGuardian();
 for(const n in K.P)K.P[n]=new Float32Array(K.P[n]);K.spots={};for(const s of K.S)K.spots[s.name]=s;return BS.kinds[kind]=K}

// --- posing ----------------------------------------------------------------------------------------------------------
// 3x3 rotations, row-major: yaw about y, pitch about x, roll about z
const bsM=(a,b)=>{const o=new Array(9);for(let i=0;i<3;i++)for(let j=0;j<3;j++)o[i*3+j]=a[i*3]*b[j]+a[i*3+1]*b[3+j]+a[i*3+2]*b[6+j];return o};
const bsRx=t=>{const c=Math.cos(t),s=Math.sin(t);return [1,0,0,0,c,-s,0,s,c]},bsRy=t=>{const c=Math.cos(t),s=Math.sin(t);return [c,0,s,0,1,0,-s,0,c]},bsRz=t=>{const c=Math.cos(t),s=Math.sin(t);return [c,-s,0,s,c,0,0,0,1]};
const bsMv=(m,v)=>[m[0]*v[0]+m[1]*v[1]+m[2]*v[2],m[3]*v[0]+m[4]*v[1]+m[5]*v[2],m[6]*v[0]+m[7]*v[1]+m[8]*v[2]];
// The bones' angles now: [pitch, yaw, roll] each, and the body's bob, from what it is doing.
function bsPose(B,now){const t=now-B.t0,A={},set=(n,p,y=0,r=0)=>{A[n]=[p,y,r]},K=bsKind(B.kind),hip=(K&&K.off&&K.off.pelvis?K.off.pelvis[1]:4.2);let bob=0;   /* hip: its own hips' height (a fall kneels and lies by it) */
 if(B.mode==='walk'||B.mode==='shake'||B.mode==='idle'){const ph=(now-B.w0)*2*Math.PI/B.stride,w=B.mode==='walk'?1:0,s=Math.sin(ph),c=Math.cos(ph);
  set('thighL',-0.38*s*w,0,0);set('thighR',0.38*s*w,0,0);set('shinL',Math.max(0,c)*0.55*w,0,0);set('shinR',Math.max(0,-c)*0.55*w,0,0);
  set('footL',-0.15*s*w);set('footR',0.15*s*w);set('uarmL',0.28*s*w,0,-0.08);set('uarmR',-0.28*s*w,0,0.08);set('farmL',-0.25-0.1*w);set('farmR',-0.25-0.1*w);
  set('pelvis',0,0.06*s*w,0.03*s*w);set('chest',0.06,-0.08*s*w,-0.04*s*w);set('head',0,0.05*s*w,0);bob=Math.abs(s)*0.22*w-0.1*w;
  const br=Math.sin(now*0.9)*0.025;A.chest[0]+=br;A.head[0]-=br}
 if(B.mode==='shake'){const k=Math.min(1,t/0.6)*Math.max(0,1-(t-2.9)/0.7),f=now*4.2;   /* slow heaves (the user: too much, slower) */
  A.chest=[A.chest[0]+Math.sin(f*0.7)*0.06*k,A.chest[1]+Math.sin(f)*0.11*k,A.chest[2]+Math.sin(f*1.3)*0.08*k];A.pelvis=[0,Math.sin(f*0.9)*0.04*k,Math.sin(f*1.1)*0.035*k];
  A.head=[Math.sin(f*1.2)*0.08*k,Math.sin(f*0.9)*0.1*k,0];set('uarmL',Math.sin(f*0.8)*0.35*k,0,-0.25*k);set('uarmR',-Math.sin(f*0.75)*0.35*k,0,0.25*k);set('farmL',-0.4*k);set('farmR',-0.4*k);
  bob+=Math.abs(Math.sin(f*0.5))*0.12*k;if(t>3.6)bsMode(B,B.after||'idle')}
 // the slam (the user: an attack of its own, both fists overhand): both fists raised slowly over its head while the
 // tiles they will strike are marked (1.9 s: time to run), brought down together, then held on the ground, bent over,
 // slow to rise (to 5.6 s, up by 7.2 s): the moment to run in, or climb its arms
 if(B.mode==='slam'){if(!A.chest)A.chest=[0,0,0];const e=x=>x*x*(3-2*x),cl=x=>Math.max(0,Math.min(1,x)),wind=e(cl(t/BSSLAM.wind)),strike=e(cl((t-BSSLAM.wind)/(BSSLAM.hit-BSSLAM.wind))),rise=e(cl((t-BSSLAM.hold)/(BSSLAM.up-BSSLAM.hold)));
  const arm=((-2.75*wind)*(1-strike)-1.3*strike)*(1-rise),inward=0.72*Math.min(1,wind*2)*(1-rise),lean=((-0.2*wind)*(1-strike)+0.6*strike)*(1-rise);   /* a hanging arm swings forward at minus: overhead -2.75, down in front -1.3 (the chest leant 0.6); turned in 0.72 so the fists meet */
  set('uarmL',arm,0,inward);set('uarmR',arm,0,-inward);set('farmL',-0.55*wind*(1-strike)*(1-rise));set('farmR',-0.55*wind*(1-strike)*(1-rise));
  A.chest[0]+=lean;set('head',(-0.3*wind*(1-strike)+0.25*strike)*(1-rise));
  const kn=strike*(1-rise);set('thighL',-0.45*kn,0,-0.05*kn);set('thighR',-0.45*kn,0,0.05*kn);set('shinL',0.75*kn);set('shinR',0.75*kn);set('footL',-0.25*kn);set('footR',-0.25*kn);
  bob-=0.2*hip*kn;if(t>=BSSLAM.hit&&!B.struck){B.struck=true}
  if(t>BSSLAM.up)bsMode(B,B.after||'idle')}
 if(B.mode==='fall'){const u=Math.min(1,t/3.2),e=u*u*(3-2*u),k1=Math.min(1,t/1.2);   /* it kneels, then pitches forward and lies: the mountain it becomes */
  set('thighL',-1.2*k1,0,-0.1);set('thighR',-1.0*k1,0,0.1);set('shinL',2.0*k1);set('shinR',1.8*k1);set('footL',-0.6*k1);set('footR',-0.6*k1);
  set('pelvis',1.25*e,0,0.05*e);set('chest',0.35*e,0.1*e,0);set('head',0.4*e,0.2*e,0);set('uarmL',-1.3*e,0,-0.35*e);set('uarmR',-1.4*e,0,0.3*e);set('farmL',-0.3*e);set('farmR',-0.4*e);
  bob=-0.62*hip*k1-0.24*hip*e}
 if(B.mode==='raise'){const u=B.mtn?B.mtn.u||0:0;set('thighL',-1.2,0,-0.1);set('thighR',-1.0,0,0.1);set('shinL',2.0);set('shinR',1.8);set('footL',-0.6);set('footR',-0.6);
  set('pelvis',1.25,0,0.05);set('chest',0.35,0.1,0);set('head',0.4,0.2,0);set('uarmL',-1.3,0,-0.35);set('uarmR',-1.4,0,0.3);set('farmL',-0.3);set('farmR',-0.4);bob=-0.86*hip-u*hip*1.1}   /* its stones sink into the mountain */
 return {A,bob}}
function bsMode(B,mode){B.mode=mode;B.t0=performance.now()/1000;if(mode==='walk'&&!B.w0)B.w0=B.t0;if(mode==='shake')for(const c of B.riders)c.beat=null;   /* each shake tests every climber again */
 if(mode==='slam'){B.struck=B.strikeDone=false;B.zone=bsSlamTiles(B)}else if(mode!=='slam')B.zone=null}
// Each bone's place and turn in the world: rotation R (3x3), position P.
function bsBones(B,now){const {A,bob}=bsPose(B,now),K=bsKind(B.kind),s=B.scale,W=[],RO=K.rest||{};
 const g=rdGround(B.x,B.z);for(let i=0;i<BSBONES.length;i++){const n=BSBONES[i][0],par=BSBONES[i][1],off=(K.off&&K.off[n])||BSBONES[i][2],a0=A[n]||[0,0,0],r0=RO[n]||[0,0,0],a=[a0[0]+r0[0],a0[1]+r0[1],a0[2]+r0[2]],   /* its own build and stance (K.off, K.rest) */L=bsM(bsRy(a[1]),bsM(bsRx(a[0]),bsRz(a[2])));
  if(!par){const R=bsM(bsRy(B.yaw),L);W.push({R,P:[B.x,g+off[1]*s+bob*s-(B.sink||0)*4*s,B.z]});continue}   /* sink: rising out of the rock (the game's golems, bsBeast) */
  const p=W[BSI[par]],o=bsMv(p.R,[off[0]*s,off[1]*s,off[2]*s]);W.push({R:bsM(p.R,L),P:[p.P[0]+o[0],p.P[1]+o[1],p.P[2]+o[2]]})}
 bsGround(B,K,W,s);B.W=W;return W}
// Its feet on the ground (the owner, 10-26: "stones feet are not on the ground it hovers"): placed by its hips, its feet
// stood where its legs put them, off the ground when a knee bent or the ground under a foot lay lower than under its
// middle. While it stands, walks, heaves or slams, the whole golem goes down or up so its lower foot stone rests on the
// ground under it (the stones' box corners, as turned: K.fbox, from its foot bones' own stones). Not while it rises out
// of the rock (sink) or falls.
function bsGround(B,K,W,s){if(!K||!K.asset||!K.P||(B.sink||0)>0||!['idle','walk','shake','slam'].includes(B.mode))return;
 if(!K.fbox){K.fbox={};for(const f of ['footL','footR']){const V=K.P[f];if(!V||!V.length)continue;const b=[1e9,1e9,1e9,-1e9,-1e9,-1e9];for(let i=0;i<V.length;i+=12)for(let c=0;c<3;c++){b[c]=Math.min(b[c],V[i+c]);b[c+3]=Math.max(b[c+3],V[i+c])}K.fbox[f]=b}}
 let dy=1e9;for(const f of ['footL','footR']){const w=W[BSI[f]],b=K.fbox[f];if(!w||!b)continue;let lo=1e9,lx=w.P[0],lz=w.P[2];
  for(const x of [b[0],b[3]])for(const y of [b[1],b[4]])for(const z of [b[2],b[5]]){const o=bsMv(w.R,[x*s,y*s,z*s]),py=w.P[1]+o[1];if(py<lo){lo=py;lx=w.P[0]+o[0];lz=w.P[2]+o[2]}}
  dy=Math.min(dy,lo-rdGround(lx,lz))}
 if(dy<1e8&&Math.abs(dy)>0.002)for(const w of W)w.P[1]-=dy}
// A spot on it (a ledge, a weak point) in the world now.
function bsSpot(B,name){const K=bsKind(B.kind),S=K&&K.spots[name];if(!S||!B.W)return null;const w=B.W[BSI[S.bone]],o=bsMv(w.R,[S.at[0]*B.scale,S.at[1]*B.scale,S.at[2]*B.scale]);return [w.P[0]+o[0],w.P[1]+o[1],w.P[2]+o[2]]}

// --- walking about, shaking climbers off ---------------------------------------------------------------------------
// Its death raises a mountain (the user, 2026-10-25): it falls and lies, then the world's own mountain blocks (v3rockStack,
// as every mountain is built) rise out of the ground where it lay, highest at its middle, and its stones sink into them;
// whoever stands there is carried up onto the tops. In the game the server makes the tiles rock (the page then draws
// them as ever, units on the tops); here the arena shows it.
function bsRaise(B){const cx=Math.round(B.x),cy=Math.round(-B.z),R=Math.round(3*(B.scale||1)),cells=[];
 for(let dy=-R;dy<=R;dy++)for(let dx=-R;dx<=R;dx++){const d=Math.hypot(dx,dy)+(MD.h(cx+dx,cy+dy,5)-0.5)*1.3;if(d>R+0.4)continue;
  cells.push([dx,dy,Math.max(1,Math.min(5,Math.round(5.2-d*4.2/R+(MD.h(cx+dx,cy+dy,6)-0.5)*1.2)))])}
 const src=[],T={x0:cx,y0:cy,z:1},map=new Map();for(const [i,j,n] of cells)map.set(i+','+j,{kind:'wall',blocks:n,biome:''});const kindAt=(i,j)=>map.get(i+','+j)||null;
 for(const [i,j] of cells)v3rockStack(()=>src,T,kindAt,i,j,cx+i,rdGround(cx+i,-(cy+j)),-(cy+j),kindAt(i,j));
 for(let v=11;v<src.length;v+=12)src[v]=1;   /* none of the terrain's own effects (the rock tag) */
 const top=new Map();for(const [i,j,n] of cells)top.set((cx+i)+','+(cy+j),n);
 B.mtn={F:new Float32Array(src),top,H:Math.max(...cells.map(c=>c[2])),t0:performance.now()/1000,cells:cells.length,dust:0}}
const bsEase=u=>u*u*(3-2*u);
function bsStep(B,dt,now){if(B.auto)bsAuto(B,now);if(B.W){bsFeetStep(B,now);bsTrample(B,now)}if(B.mode==='fall'&&now-B.t0>3.4&&!B.mtn&&!B.game){bsRaise(B);bsMode(B,'raise')}   /* in the game the server raises the world's own blocks (Golems.dm) */
 if(B.mtn){const M=B.mtn,u=Math.min(1,(now-M.t0)/2.6),e=bsEase(u);M.u=u;
  // whoever stands on its ground rides up onto the tops (the arena: their drawn height; the game: the server's tops)
  for(const t of V3.things){if(!(t.kind==='mine'||t.kind==='npc'||t.kind==='player'||t.kind==='animal'))continue;const h=M.top.get(Math.round(t.dx??t.x)+','+Math.round(t.dy??t.y));if(h==null)continue;
   if(t.g3mBase==null)t.g3mBase=t.ly||0;t.ly=t.g3mBase+h*e+(e>0?0.02:0);const kd=V3.disp.get(t.key);if(kd&&kd.rc)kd.rc.ep=null}
  if(u<1&&Math.random()<dt*14&&typeof rdDust==='function'){const a=Math.random()*6.283,r=(M.cells**0.5)*0.55;rdDust([B.x+Math.cos(a)*r,rdGround(B.x,B.z),B.z+Math.sin(a)*r],10)}   /* dust off the rising rock */
  return}
 if(B.mode==='walk'&&!B.game){const v=B.speed;B.x+=Math.sin(B.yaw)*v*dt;B.z+=Math.cos(B.yaw)*v*dt;
  if(B.goal){const dx=B.goal[0]-B.x,dz=B.goal[1]-B.z,want=Math.atan2(dx,dz);let d=want-B.yaw;while(d>Math.PI)d-=2*Math.PI;while(d<-Math.PI)d+=2*Math.PI;B.yaw+=Math.max(-0.25*dt,Math.min(0.25*dt,d));if(Math.hypot(dx,dz)<1)B.goal=null}
  }
 // climbers ride the spot they hold. A shake tests their grip: each heave a check, Strength and Defence against its
 // heave (BSGRIP), and the slam a harder one; one who fails is thrown off and lands alive (a hammer launch): the fall,
 // and what is below, is what kills. The arena's units have a Strength and Defence by race (BSARENASTAT); the game's own.
 for(const c of B.riders){if(c.off)continue;bsClimbStep(B,c,dt,now);if(B.mode!=='shake')continue;const t=now-B.t0;if(c.holding)continue;   /* gripping a handhold: not shaken off */
  const test=(need,why)=>{const st=bsStat(c.t),ok=Math.random()<Math.max(0.05,Math.min(0.96,(st[0]+st[1])/need));bsSay(c.t,ok?'Holds on':why,ok);if(ok)return;
   c.off=true;const A=c.A;if(A){A.replaced=true;A.opt.loop=false}c.t.g3dir=0;const away=rdV.n([c.at[0]-B.x,0,c.at[2]-B.z]);rdStart(c.t,'hammer',rdV.add(away,[0,0.5,0]),{live:true})};
  const beat=Math.floor((t-0.4)/0.9);if(t>0.4&&t<2.6&&beat!==c.beat){c.beat=beat;test(BSGRIP.heave,'Shaken off!')}
  }
 if(B.mode==='slam'&&B.struck&&!B.strikeDone){B.strikeDone=true;bsStrike(B)}
 B.riders=B.riders.filter(c=>!c.off)}
const BSGRIP={heave:110,slam:170};
const BSSLAM={wind:1.9,hit:2.15,hold:5.6,up:7.2};   /* seconds: fists up (the tiles marked), down, held, risen */
// Where its fists will come down: posed at the moment they strike, the tiles round both fists. Marked from the start of
// its wind-up (red, pulsing) so units can run; struck at BSSLAM.hit.
function bsSlamTiles(B){const keep=B.W,t0=B.t0;bsBones(B,t0+BSSLAM.hit+0.05);const out=new Map(),r=1.4*(B.scale||1)/1.65+0.6;
 for(const f of ['handL','handR']){const w=B.W[BSI[f]];if(!w)continue;const cx=w.P[0],cz=w.P[2];for(let x=Math.floor(cx-r);x<=Math.ceil(cx+r);x++)for(let y=Math.floor(-cz-r);y<=Math.ceil(-cz+r);y++)if(Math.hypot(x-cx,-y-cz)<=r)out.set(x+','+y,[x,y])}
 B.W=keep;return [...out.values()]}
function bsStrike(B){const s=B.scale||1;let mx=0,mz=0;for(const f of ['handL','handR']){const w=B.W&&B.W[BSI[f]];if(w){mx+=w.P[0]/2;mz+=w.P[2]/2}}
 if(typeof rdDust==='function'){rdDust([mx,rdGround(mx,mz),mz],50);for(const [x,y] of B.zone||[])if(Math.random()<0.35)rdDust([x,rdGround(x,-y),-y],6)}
 if(B.game)return;   /* the game's own: the server throws them and breaks what is there (Golems.dm RmGolemStrike) */
 const on=new Set((B.zone||[]).map(q=>q[0]+','+q[1]));
 for(const n of bsNear(B,[mx,0,mz],6*s)){const tx=Math.round(n.t.dx??n.t.x),ty=Math.round(n.t.dy??n.t.y),inside=on.has(tx+','+ty);
  let next=inside;if(!inside)for(const [ax,ay] of [[1,0],[-1,0],[0,1],[0,-1]])if(on.has((tx+ax)+','+(ty+ay)))next=true;if(!next)continue;
  rdStart(n.t,inside?'throw':'flying',rdV.add(n.from,[0,inside?0.7:0.35,0]),{live:true});bsSay(n.t,inside?'Critical!':'Knocked back',false)}
 for(const c of B.riders)if(!c.off&&Math.random()>Math.min(0.96,bsStat(c.t).reduce((a,b)=>a+b,0)/BSGRIP.slam)){c.off=true;if(c.A){c.A.replaced=true;c.A.opt.loop=false}c.t.g3dir=0;rdStart(c.t,'hammer',[0,0.5,0],{live:true});bsSay(c.t,'Thrown off!',false)}   /* Strength + Defence for a sure hold: a heave, the slam */
 const fx=Math.sin(B.yaw),fy=-Math.cos(B.yaw);bsBreak(B,(B.zone||[]).map(([x,y])=>[x,y,x-mx+fx,y+mz+fy]))}   /* what the fists come down on breaks, thrown out from where they land */
// What it breaks (the user, 2026-10-25: "have the strike fist destroy buildings or things in its way also when it walks
// have it break trees"): on the tiles its fists come down on, walls burst (stone blocks, or splinters from timber, as a
// siege breach), trees fall away from the blow, and furniture, doors and stations smash; walking, the trees its legs
// push through fall away from it and what its feet come down on breaks. list: [x, y, dx, dy], the way each is struck.
// In the game the server changes those tiles and things, and the page's own terrain effects (v3terrainFx) play them; the
// arena changes its own terrain so the same effects play.
function bsBreak(B,list){if(window.G3GAME||!list.length)return 0;const T=V3.terrain;if(!T||!Array.isArray(T.tiles)||!Array.isArray(T.kinds))return 0;
 const K=T.kinds;let g=K.findIndex(k=>k.kind==='floor'&&/grass/.test(k.state||''))+1;if(!g)g=K.findIndex(k=>k.kind==='floor')+1;
 const tiles=T.tiles.slice(),dir=new Map(),hit=new Set();let n=0;
 for(const [x,y,dx,dy] of list){hit.add(x+','+y);const i=x-T.x0,j=y-T.y0;if(!g||i<0||j<0||i>=T.w||j>=T.h)continue;const c=tiles[j*T.w+i],k=c?K[c-1]:null;
  if(k&&(k.kind==='tree'||k.kind==='built')){tiles[j*T.w+i]=g;dir.set(x+','+y,[dx,dy]);n++}}
 const now=performance.now(),gone=V3.things.filter(t=>(t.kind==='item'||t.kind==='station')&&hit.has(t.x+','+t.y));
 if(n){const m0=(V3.bfx||[]).length,L=V3.lastLayers||{};v3applyTerrain({terrain:{...T,tiles},upper:L.upper,below:L.below,above:L.above,z:T.z});
  for(const f of (V3.bfx||[]).slice(m0)){const d=dir.get(f.x+','+f.y);if(d&&f.type==='fell'){f.dx=d[0];f.dy=d[1]}}}   /* a tree falls the way it was pushed */
 if(gone.length){V3.things=V3.things.filter(t=>!gone.includes(t));V3.bfx=V3.bfx||[];
  for(const t of gone)V3.bfx.push({type:'burst',x:t.x,y:t.y,t:now,col:t.mat==='stone'?[0.5,0.48,0.44,1]:t.mat==='iron'?[0.42,0.42,0.45,1]:[0.45,0.3,0.16,1],level:0,dx:0,dy:0,top:t.m3==='door'?1.6:0.7})}
 return n+gone.length}
// Walking: the trees its legs and hanging arms push through (round each foot, between them, round a low hand).
function bsTrample(B,now){if(B.game||B.mode!=='walk'||!B.W||now<(B.trampleAt||0))return;B.trampleAt=now+0.15;const T=V3.terrain;if(!T||!Array.isArray(T.tiles))return;
 const s=B.scale||1,fx=Math.sin(B.yaw),fy=-Math.cos(B.yaw),pts=[];for(const f of ['footL','footR','handL','handR']){const w=B.W[BSI[f]];if(w&&(f[0]==='f'||w.P[1]-rdGround(w.P[0],w.P[2])<3*s/1.65))pts.push([w.P[0],-w.P[2],f[0]==='f'?0.8*s:0.55*s])}
 if(pts.length>=2)pts.push([(pts[0][0]+pts[1][0])/2,(pts[0][1]+pts[1][1])/2,0.8*s]);const list=[],seen=new Set();
 for(const [px,py,r] of pts)for(let x=Math.floor(px-r);x<=Math.ceil(px+r);x++)for(let y=Math.floor(py-r);y<=Math.ceil(py+r);y++){if(Math.hypot(x-px,y-py)>r||seen.has(x+','+y))continue;seen.add(x+','+y);
  const i=x-T.x0,j=y-T.y0;if(i<0||j<0||i>=T.w||j>=T.h)continue;const c=T.tiles[j*T.w+i],k=c?T.kinds[c-1]:null;if(k&&k.kind==='tree'){const ox=x-B.x,oy=y+B.z,l=Math.hypot(ox,oy)||1;list.push([x,y,ox/l+fx*1.5,oy/l+fy*1.5])}}   /* pushed on ahead and out to its side */
 if(list.length)bsBreak(B,list)}
const BSARENASTAT={Dwarves:[70,60],Orc:[65,45],Human:[45,45],'Night Elf':[35,40],Goblins:[20,25],Kobold:[18,20],LizardMan:[50,40],Skeleton:[30,30],Vampire:[55,40],Demon:[75,55],FrogMan:[30,30],Gargoyle:[60,70],DevourerZombie:[40,30]};
function bsStat(t){if(t.str!=null)return [t.str,t.def||0];const r=BSARENASTAT[t.g3&&t.g3.sheet]||[40,40];return r}
function bsSay(t,txt,good){try{if(typeof v3floatOn!=='function'||!V3.floats)return;V3.floats.push({cls:good?'dmg parry':'dmg stagger',txt,x:t.x,y:t.y,key:v3floatOn(t.x,t.y),t:performance.now(),dx:0,life:1300})}catch(e){}}
// Who stands near a point on the ground (not riding it), and the way from the point to them.
function bsNear(B,P,r){const out=[];for(const t of V3.things){if(!t.g3last||t.dead||t.g3doll||B.riders.some(c=>c.t===t&&!c.off))continue;if(!(t.kind==='mine'||t.kind==='npc'||t.kind==='player'))continue;
  const dx=(t.dx??t.x)-P[0],dz=-(t.dy??t.y)-P[2],d=Math.hypot(dx,dz);if(d<=r)out.push({t,d,from:rdV.n([dx||0.01,0,dz])})}return out}
// Climbing it: up the route hold to hold at its own pace (BSCLIMB: holds a second, by race; the game's from its
// climbing), resting a moment on each hold it reaches (gripping: safe), and gripping on till told to go on when the
// player has it hold on (bsHoldOn). c.i: the hold it last reached; c.u: how far to the next.
const BSCLIMB={Kobold:0.75,Goblins:0.7,'Night Elf':0.6,Human:0.5,LizardMan:0.55,Orc:0.45,Skeleton:0.5,Vampire:0.6,Demon:0.45,Dwarves:0.35,FrogMan:0.6,Gargoyle:0.3};
function bsClimbStep(B,c,dt,now){const K=bsKind(B.kind),R=c.route||K.route;if(c.i==null){c.i=Math.max(0,R.indexOf(c.spot));c.u=0;c.rest=now+0.6}
 const at=i=>bsSpot(B,R[Math.min(i,R.length-1)]);if(c.gripTill&&now<c.gripTill){c.holding=true;c.at=at(c.i);return}
 if(now<(c.rest||0)||c.i>=R.length-1){c.holding=c.u===0;c.at=at(c.i);return}
 c.holding=false;c.u+=dt*(BSCLIMB[c.t.g3&&c.t.g3.sheet]||0.5);if(c.u>=1){c.i++;c.u=0;c.rest=now+0.7;c.holding=true}   /* reached the next hold: grips it a moment */
 const a=at(c.i),b=at(c.i+1);if(a&&b)c.at=[a[0]+(b[0]-a[0])*c.u,a[1]+(b[1]-a[1])*c.u,a[2]+(b[2]-a[2])*c.u];else c.at=a}
// The player has its climbers hold on (a right-click on the golem in the game): each grips the nearest hold (the one it
// is on or the next, whichever is closer) and stays gripping till told to climb on.
function bsHoldOn(B,on=true){for(const c of B.riders){if(c.off)continue;if(on){if(c.u>0.5){c.i++;c.u=0}c.u=0;c.gripTill=Infinity;bsSay(c.t,'Holds on',true)}else{c.gripTill=0;c.rest=0}}}
// t climbs onto B (seen from behind, hand over hand, as climbing gear's climb), from a spot of its route.
function bsRide(B,t,spot,grip){if(!t.g3last)return null;const c={t,spot,grip,at:bsSpot(B,spot)};B.riders.push(c);
 c.A=skAct(t,'climb',null,{loop:true,fx:(d,dt,b,emit,A2)=>{if(c.at)A2.O0=[c.at[0],c.at[1]-0.5,c.at[2]]}});if(c.A){c.A.climbing=true;wkShowBack(t)}return c}
// Its feet (the user, 2026-10-25): the tiles each foot stands on, from its foot stones' own size at its scale (the golem:
// 2 x 2 a foot). Only the feet hold ground: units walk between its legs and under its body. In the game the server keeps
// those tiles taken as the feet move (and a unit under a foot as it comes down is pushed off).
// Timed by foot (the user: "so we can time the left and right foot and which tiles"): in a stride each foot is planted,
// then lifts and swings, then comes down; a planted foot holds its tiles, a lifted one none. Each footfall is kept
// (B.steps: which foot, when, the tiles it came down on), for the game to take those tiles at that moment and push off
// whoever stands there. bsGait: each foot's phase now: 'down' or 'up' (and how far through the swing).
function bsGait(B,now){if(B.mode!=='walk')return {L:'down',R:'down'};const c=Math.cos((now-B.w0)*2*Math.PI/B.stride);return {L:c>0.25?'up':'down',R:-c>0.25?'up':'down'}}
function bsFootAt(B,f){const K=bsKind(B.kind),n=K&&K.foot||2,w=B.W&&B.W[BSI['foot'+f]];if(!w)return [];const x0=Math.round(w.P[0]-n/2+0.5),y0=Math.round(-w.P[2]-n/2+0.5),out=[];
 for(let i=0;i<n;i++)for(let j=0;j<n;j++)out.push([x0+i,y0+j]);return out}
function bsFootTiles(B){const out=[];for(const f of ['L','R'])if((B.gait||{})[f]!=='up')for(const t of bsFootAt(B,f))out.push([t[0],t[1],f]);return out}
function bsFeetStep(B,now){const g=bsGait(B,now),was=B.gait||{L:'down',R:'down'};B.gait=g;B.steps=B.steps||[];
 for(const f of ['L','R'])if(was[f]==='up'&&g[f]==='down'){const tiles=bsFootAt(B,f);B.steps.push({foot:f,at:+now.toFixed(2),tiles});if(B.steps.length>40)B.steps.shift();
  const w=B.W&&B.W[BSI['foot'+f]];if(!w)continue;const P=[w.P[0],rdGround(w.P[0],w.P[2]),w.P[2]];if(typeof rdDust==='function')rdDust(P,16);   /* its footfall: dust where it lands */
  if(B.game)continue;   /* the server knocks them aside (Golems.dm) */
  for(const n of bsNear(B,P,(K0(B).foot||2)*0.5+1.4)){rdStart(n.t,'flying',rdV.add(n.from,[0,0.3,0]),{live:true});bsSay(n.t,'Knocked back',false)}   /* too close to where it came down: knocked back, alive */
  const fx=Math.sin(B.yaw),fy=-Math.cos(B.yaw);bsBreak(B,tiles.map(([x,y])=>[x,y,fx,fy]))}}   /* what its foot comes down on breaks */
const K0=B=>bsKind(B.kind)||{};
// How often it moves (the user, 2026-10-25): it stands a while (rest, seconds), then walks a stretch (tiles) and stands
// again. The arena runs it quick to watch; the game's are minutes (the server's timer).
const BSPACE={guardian:{rest:[6,10],walk:[6,10]},ent:{rest:[6,10],walk:[5,8]}};
function bsAuto(B,now){const P=BSPACE[B.kind]||BSPACE.guardian;if(B.mode!=='idle'&&B.mode!=='walk'&&B.mode!=='slam')return;
 if(B.mode==='walk'&&!B.goal){bsMode(B,'idle');B.next=now+P.rest[0]+Math.random()*(P.rest[1]-P.rest[0]);return}
 if(B.mode==='slam')return;if(B.mode==='idle'){if(B.next==null)B.next=now+P.rest[0];if(now<B.next)return;
  const ahead=bsNear(B,[B.x+Math.sin(B.yaw)*3*(B.scale||1),0,B.z+Math.cos(B.yaw)*3*(B.scale||1)],4*(B.scale||1));if(ahead.length&&Math.random()<0.6){bsMode(B,'slam');B.next=now+BSSLAM.up+P.rest[0];return}const d=P.walk[0]+Math.random()*(P.walk[1]-P.walk[0]),a=B.yaw+(Math.random()-0.5)*1.6;
  B.goal=[B.x+Math.sin(a)*d,B.z+Math.cos(a)*d];bsMode(B,'walk')}}
function bsSpawn(kind,x,z,yaw){const K=bsKind(kind);if(!K)return null;const B={kind,x,z,yaw:yaw||0,scale:K.scale||1,mode:'idle',t0:performance.now()/1000,w0:performance.now()/1000,stride:kind==='ent'?3.0:2.6,speed:kind==='ent'?0.5:0.6,riders:[],goal:null,auto:false};BS.list.push(B);return B}

// --- in the game (Golems.dm) -------------------------------------------------------------------------------------------
// A stone golem is one of the game's great beasts (Beasts.dm). The page's beast drawing (remastered.html v3drawBeast)
// hands it here each frame with where it is drawn, and the server says what it is doing (anim: idle, walk, shake, slam,
// fall; at: seconds into it; zone: the tiles its fists will strike); it turns slowly to the way the server faces it. It
// is drawn with the arena's (bsFrame) and goes when the page stops handing it over (out of view, or felled and the
// mountain risen). The server knocks people aside, throws them and breaks what it breaks: here it only plays. Returns
// the height of its top (the page's health bar), or 0 to draw its plain picture while the page has no bosses.
BS.game=new Map();
function bsBeast(t,X,gy,Z,kd,walking,shadows){const G=t.beast;if(!bsKind('guardian'))return 0;const now=performance.now()/1000;
 const d=t.dir||2,fx=(d&4?1:0)-(d&8?1:0),fz=(d&2?1:0)-(d&1?1:0),want=fx||fz?Math.atan2(fx,fz):null;
 let B=BS.game.get(t.key);if(!B){B=bsSpawn('guardian',X,Z,want??0);B.game=true;BS.game.set(t.key,B)}
 const dt=Math.min(0.1,now-(B.seen||now));B.seen=now;B.x=X;B.z=Z;
 if(want!=null&&!G.dead){let dd=want-B.yaw;while(dd>Math.PI)dd-=2*Math.PI;while(dd<-Math.PI)dd+=2*Math.PI;B.yaw+=Math.max(-1.6*dt,Math.min(1.6*dt,dd))}
 const rise=G.anim==='rise';if(rise){if(B.riseT0==null)B.riseT0=now-(G.at||0);B.sink=Math.max(0,1-(now-B.riseT0)/3);if(B.sink>0&&Math.random()<0.3&&typeof rdDust==='function')rdDust([X+(Math.random()-0.5)*4,gy,Z+(Math.random()-0.5)*3],8)}else{B.sink=0;B.riseT0=null}   /* standing up out of the gap it leaves in the mountain (Golems.dm RmGolemRise) */
 const m=G.dead?'fall':rise?'idle':G.anim==='idle'&&walking?'walk':(G.anim||'idle');
 if(m!==B.mode){bsMode(B,m);if(G.at!=null&&m!=='walk')B.t0=now-Math.min(G.at,60)}   /* in step with the server: its slam lands when the server's does */
 if(m==='slam'&&G.zone)B.zone=G.zone.map(q=>[q[0],q[1]]);
 const r=2.2*(B.scale||1)/1.65,sy=gy+0.012;for(const k of [1,0.8,0.6,0.4]){const a2=r*k,b2=r*k*0.7;quad(shadows,[X-a2,sy,Z+b2],[X+a2,sy,Z+b2],[X+a2,sy,Z-b2],[X-a2,sy,Z-b2],[0,0,0],[0,0,0,1],[0,1,1,1,1,0,0,0])}   /* its shadow, wide and soft */
 return gy+(m==='fall'?2.2:6.4)*(B.scale||1)/1.65}

// --- drawing ---------------------------------------------------------------------------------------------------------
function bsFrame(){if(BS.game.size){const now=performance.now()/1000;for(const [k,B] of BS.game)if(now-B.seen>1){BS.game.delete(k);const i=BS.list.indexOf(B);if(i>=0)BS.list.splice(i,1)}}   /* no longer handed over */
 if(!BS.list.length||!V3.gl)return;const gl=V3.gl,L=V3.loc,now=performance.now()/1000,dt=Math.min(0.05,now-(BS.last||now));BS.last=now;
 const a=BS.va||(BS.va=new VA());a.length=0;
 for(const B of BS.list){const K=bsKind(B.kind);if(!K)continue;bsStep(B,dt,now);
  if(B.mtn){const M=B.mtn,F=M.F,off=-(M.H+0.6)*(1-bsEase(M.u||0));for(let v=0;v<F.length;v+=12)a.v(F[v],F[v+1]+off,F[v+2],F[v+3],F[v+4],F[v+5],0,0,F[v+8],F[v+9],F[v+10],1);if((M.u||0)>=1)continue}
  const W=bsBones(B,now),s=B.scale;
  if(B.zone&&B.mode==='slam'&&now-B.t0<BSSLAM.hit+0.6){const pu=0.55+0.45*Math.sin(now*9),c=[0.95,0.18*pu,0.12*pu];for(const [tx,ty] of B.zone){const y=rdGround(tx,-ty)+0.035,h=0.47,X=tx,Z=-ty;
    a.v(X-h,y,Z-h,0,1,0,0,0,...c,1);a.v(X+h,y,Z-h,0,1,0,0,0,...c,1);a.v(X+h,y,Z+h,0,1,0,0,0,...c,1);a.v(X-h,y,Z-h,0,1,0,0,0,...c,1);a.v(X+h,y,Z+h,0,1,0,0,0,...c,1);a.v(X-h,y,Z+h,0,1,0,0,0,...c,1)}}   /* where its fists will fall: run */
  if(B.showFeet&&B.mode!=='fall'&&B.mode!=='raise')for(const [tx,ty] of bsFootTiles(B)){const y=rdGround(tx,-ty)+0.03,h=0.47,c=[0.95,0.78,0.35],bar=(x0,z0,x1,z1)=>{a.v(x0,y,z0,0,1,0,0,0,...c,1);a.v(x1,y,z0,0,1,0,0,0,...c,1);a.v(x1,y,z1,0,1,0,0,0,...c,1);a.v(x0,y,z0,0,1,0,0,0,...c,1);a.v(x1,y,z1,0,1,0,0,0,...c,1);a.v(x0,y,z1,0,1,0,0,0,...c,1)};
   const X=tx,Z=-ty,w=0.05;bar(X-h,Z-h,X+h,Z-h+w);bar(X-h,Z+h-w,X+h,Z+h);bar(X-h,Z-h,X-h+w,Z+h);bar(X+h-w,Z-h,X+h,Z+h)}   /* the tiles its feet hold: squares, as the game marks a tile */
  for(let i=0;i<BSBONES.length;i++){const F=K.P[BSBONES[i][0]];if(!F)continue;const {R,P}=W[i],m=R;
   for(let v=0;v<F.length;v+=12){const x=F[v]*s,y=F[v+1]*s,z=F[v+2]*s,nx=F[v+3],ny=F[v+4],nz=F[v+5];
    a.v(P[0]+m[0]*x+m[1]*y+m[2]*z,P[1]+m[3]*x+m[4]*y+m[5]*z,P[2]+m[6]*x+m[7]*y+m[8]*z,m[0]*nx+m[1]*ny+m[2]*nz,m[3]*nx+m[4]*ny+m[5]*nz,m[6]*nx+m[7]*ny+m[8]*nz,0,0,F[v+8],F[v+9],F[v+10],F[v+11])}}}
 if(!a.length)return;gl.uniform1f(L.gon,0);gl.bindBuffer(gl.ARRAY_BUFFER,V3.dyn);v3up(a);v3draw(V3.dyn,a.length/12,null);
 gl.uniform1f(L.gon,V3.gtex&&V3.gtex.ok&&V3.etex&&V3.etex.ok&&V3.stex&&V3.stex.ok?1:0)}

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
// Bare hands (Hidden Clans, the owner 11-01: "the punch and kick should be the same attack or combos itself"): each fighter's
// blows go jab, cross, kick, and again; a pause of 4.5 s without a blow starts the string over (blows come every 1-3 s).
const G3COMBO=['jab','cross','kick'],g3comboAt=new Map();
function g3combo(t){const k=t.ref||t.id||t.name,now=performance.now(),c=g3comboAt.get(k);const i=c&&now-c.at<4500?(c.i+1)%G3COMBO.length:0;g3comboAt.set(k,{i,at:now});
 if(g3comboAt.size>400)for(const [key,v] of g3comboAt)if(now-v.at>10000)g3comboAt.delete(key);   /* the fighters gone quiet */
 return G3COMBO[i]}
// The move its weapon swings (skills.js), its own weapon in hand.
function g3move(t,kill){const w=t.g3&&t.g3.w?t.g3.w.split(':')[0]:'',has=s=>SKWEAPON[s]&&SKWEAPON[s].includes(w);if(t.g3&&t.g3.s&&Math.random()<(kill?0.1:0.15))return 'bash';   /* now and then its shield in the foe's face */
 if(!w)return g3combo(t);   /* bare hands: GOA's punch and kick as one string (Hidden Clans) */if(SKWEAPON.cast.includes(w))return 'cast';if(w==='warhammer')return kill&&Math.random()<0.5?'launch':'smash';
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

