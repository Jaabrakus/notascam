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
