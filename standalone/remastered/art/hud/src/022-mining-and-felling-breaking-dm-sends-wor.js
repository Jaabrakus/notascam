// ===== Mining and felling (Breaking.dm sends "work": x, y, damage %, blows, dx, dy, broken) =====
// Rock being mined cracks in ten stages (like Minecraft) and throws chips at every blow,
// then bursts into tumbling chunks and dust. A tree being chopped leaves the terrain mesh
// and is drawn on its own, so it shakes at each blow; when it goes it falls away from its
// feller, bounces, and breaks into logs. Bamboo canes topple one by one and split.
// Metal veins: natural rock that holds ore is tinted and streaked with its metal.
const VEIN={iron:{tint:[0.62,0.4,0.3],mark:[0.86,0.55,0.36,1]},silver:{tint:[0.66,0.68,0.74],mark:[0.93,0.95,1,1]},gold:{tint:[0.74,0.6,0.3],mark:[1,0.84,0.26,1]},adamantium:{tint:[0.3,0.55,0.52],mark:[0.4,1,0.86,1],glow:1}};
// A point on a rock face, from (u,v) in 0..1, and the face's outward normal. Top: the
// four corners. Side: the top edge p0-p1 down to the ground, bulging to its mid point
// exactly as the rock is drawn (four triangles round the mid point).
function v3rockFace(g,side){if(side==null){const [sw,se,ne,nw]=g.c,L=(a,b,t)=>[a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t,a[2]+(b[2]-a[2])*t];const n=MD.n3(sw,se,nw);const up=n[1]<0?n.map(v=>-v):n;return {P:(u,v)=>L(L(sw,se,u),L(nw,ne,u),v),n:up,size:1}}
 const [p0,p1,mid]=g.s[side],b0=[p0[0],g.Y,p0[2]],b1=[p1[0],g.Y,p1[2]],L=(a,b,t)=>[a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t,a[2]+(b[2]-a[2])*t],Q=(u,v)=>L(L(b0,b1,u),L(p0,p1,u),v);
 const cx=(g.c[0][0]+g.c[2][0])/2,cz=(g.c[0][2]+g.c[2][2])/2;let nx=-(p1[2]-p0[2]),nz=p1[0]-p0[0];const l=Math.hypot(nx,nz)||1;nx/=l;nz/=l;if(nx*((p0[0]+p1[0])/2-cx)+nz*((p0[2]+p1[2])/2-cz)<0){nx=-nx;nz=-nz}
 const P=mid?(u,v)=>{const du=u-0.5,dv=v-0.5,s=2*Math.max(Math.abs(du),Math.abs(dv));if(s<1e-4)return mid.slice();const E=Q(0.5+du/s,0.5+dv/s);return [mid[0]+(E[0]-mid[0])*s,mid[1]+(E[1]-mid[1])*s,mid[2]+(E[2]-mid[2])*s]}:Q;
 return {P,n:[nx,0,nz],size:Math.max(1,Math.min(p0[1],p1[1])-g.Y)}}
// Wandering lines on a face: n paths of k steps, in face (u,v), from a seed.
function v3facePaths(n,k,step,seed){const out=[];for(let p=0;p<n;p++){let u=0.15+MD.h(seed,p,1)*0.7,v=0.15+MD.h(seed,p,2)*0.7,a=MD.h(seed,p,3)*6.283;const pts=[[u,v]];
  for(let s=0;s<k;s++){a+=(MD.h(seed+s,p,4)-0.5)*1.6;u=Math.min(0.98,Math.max(0.02,u+Math.cos(a)*step));v=Math.min(0.98,Math.max(0.02,v+Math.sin(a)*step));pts.push([u,v])}out.push(pts)}return out}
// A flat strip along a path on a face, lifted off it a little; both sides, so it shows from anywhere.
function v3strip(a,F,path,upto,w,c,lift,lit){const n=lit?F.n:[0,0,0];let left=upto;for(let s=0;s+1<path.length&&left>0;s++,left--){
  const A=F.P(path[s][0],path[s][1]),B=F.P(path[s+1][0],path[s+1][1]),d=[B[0]-A[0],B[1]-A[1],B[2]-A[2]];let x=F.n[1]*d[2]-F.n[2]*d[1],y=F.n[2]*d[0]-F.n[0]*d[2],z=F.n[0]*d[1]-F.n[1]*d[0];const l=Math.hypot(x,y,z)||1;x=x/l*w;y=y/l*w;z=z/l*w;
  const o=[F.n[0]*lift,F.n[1]*lift,F.n[2]*lift],p=(P,sg)=>[P[0]+o[0]+x*sg,P[1]+o[1]+y*sg,P[2]+o[2]+z*sg];
  quad(a,p(A,-1),p(A,1),p(B,1),p(B,-1),n,c);quad(a,p(B,-1),p(B,1),p(A,1),p(A,-1),n,c)}}
// Cracks for damage stage 0..9: they grow along their paths as the stage rises.
function v3crackGeo(g,stage,tx,ty,lvl=-1){const a=[],faces=lvl>=0?g.s.map((_,i)=>i):[null,...g.s.map((_,i)=>i)],dark=[0.07,0.06,0.06,1];
 faces.forEach((side,fi)=>{let F=v3rockFace(g,side);if(lvl>=0){const R=F,H=Math.max(1,R.size),v0=Math.min(0.9,(lvl-(g.cut||0))/H),v1=Math.min(1,v0+1/H);F={P:(u,v)=>R.P(u,v0+v*(v1-v0)),n:R.n,size:1}}const seed=tx*977+ty*389+fi*53,paths=v3facePaths(side==null?3:4,7,side==null?0.11:0.08,seed);const total=paths.length*7,show=Math.round(total*(stage+1)/10);let left=show;
  for(const path of paths){const n=Math.min(7,left);if(n<=0)break;v3strip(a,F,path,n,0.022,dark,0.035,false);left-=n}});return a}
function v3work(m){const old=V3.work||new Map(),now=performance.now(),W=new Map(),T=m.terrain||V3.terrain;V3.bfx=V3.bfx||[];V3.shake=V3.shake||new Map();
 const kindOf=(x,y)=>{if(!T)return null;const i=x-T.x0,j=y-T.y0;if(i<0||j<0||i>=T.w||j>=T.h)return null;const c=T.tiles[j*T.w+i];return c?T.kinds[c-1]:null};
 for(const w of arr(m.work)){const [x,y,dmg,blows,dx,dy,broken,roof,lvl]=w,key=x+','+y,p=old.get(key),e={x,y,dmg,blows,dx,dy,broken,roof,lvl};W.set(key,e);if(broken)continue;
  const n=Math.min(4,blows-(p?p.blows:blows-1));if(n<=0)continue;const K=kindOf(x,y);if(!K)continue;
  for(let k=0;k<n;k++)V3.bfx.push({type:K.kind==='tree'?'leaf':'chip',x,y,dx,dy,t:now+k*150,seed:blows*7+k,K,geo:V3.rockGeo&&V3.rockGeo.get(key),roof:roof?(K.ceil||2):0});
  if(K.kind==='tree')V3.shake.set(key,{t:now+(n-1)*150,dx,dy})}
 V3.work=W;if(V3.crack)for(const k of [...V3.crack.keys()])if(!W.has(k))V3.crack.delete(k);
 const trees=new Set();if(V3.models)for(const [key,e] of W){if(e.broken)continue;const K=kindOf(e.x,e.y);if(K&&K.kind==='tree')trees.add(key)}
 const prev=V3.workTrees||new Set(),changed=trees.size!==prev.size||[...trees].some(k=>!prev.has(k));V3.workTrees=trees;if(changed)V3.workVer=(V3.workVer||0)+1;
 if(changed){if(V3.treeGeo)for(const k of [...V3.treeGeo.keys()])if(!trees.has(k))V3.treeGeo.delete(k)}
 if((changed||V3.recut)&&!m.terrain&&V3.terrain&&m.z===V3.z)v3buildTerrain(V3.terrain);V3.recut=false}
// Rotate geometry (12 floats a vertex) about base point B by ang round axis k; lift raises it.
function v3rot(src,B,k,ang,lift){const out=new Float32Array(src.length),c=Math.cos(ang),s=Math.sin(ang),[kx,ky,kz]=k;
 const R=(x,y,z)=>{const d=kx*x+ky*y+kz*z;return [x*c+(ky*z-kz*y)*s+kx*d*(1-c),y*c+(kz*x-kx*z)*s+ky*d*(1-c),z*c+(kx*y-ky*x)*s+kz*d*(1-c)]};
 for(let i=0;i<src.length;i+=12){const p=R(src[i]-B[0],src[i+1]-B[1],src[i+2]-B[2]),n=R(src[i+3],src[i+4],src[i+5]);out[i]=p[0]+B[0];out[i+1]=p[1]+B[1]+lift;out[i+2]=p[2]+B[2];out[i+3]=n[0];out[i+4]=n[1];out[i+5]=n[2];for(let j=6;j<12;j++)out[i+j]=src[i+j]}return out}
// The way a tree falls (world X/Z): away from whoever cut it, else a steady random way.
function v3fallDir(f){let x=f.dx||0,z=-(f.dy||0);const l=Math.hypot(x,z);if(l<0.01){const a=MD.h(f.x,f.y,5)*6.283;return [Math.cos(a),Math.sin(a)]}return [x/l,z/l]}
// One bamboo cane as the tree model draws it (MD.tree, stretched like MD.tallTree).
function v3cane(K,tx,ty,k){const X=tx,Y=0,Z=-ty,seed=tx*31+ty*17,x=X+(MD.h(tx,ty,2)-0.5)*0.22,z=Z+(MD.h(tx,ty,3)-0.5)*0.22,a=[];const ax=x+(MD.h(seed,k)-0.5)*0.5,az=z+(MD.h(seed,k+4)-0.5)*0.5,hh=1.2+MD.h(seed,k+8)*0.9;
 MD.prism(a,ax,az,Y,Y+hh,0.04,0.035,5,[0.5,0.62,0.28],seed+k,(MD.h(seed,k+12)-0.5)*0.15);MD.blob(a,ax,Y+hh,az,0.18,0.08,0.18,[0.34,0.58,0.24],seed+k+20,0.4);
 for(let v=0;v<a.length;v+=12){a[v]=X+(a[v]-X)*1.3;a[v+1]=Y+(a[v+1]-Y)*1.9;a[v+2]=Z+(a[v+2]-Z)*1.3}return {g:new Float32Array(a),B:[X+(ax-X)*1.3,Y,Z+(az-Z)*1.3],h:hh*1.9}}
function v3drawWork(ts){if(!V3.on)return;const gl=V3.gl,L=V3.loc,now=performance.now(),lit=[],dust=[],geos=[];
 const draw=g=>{if(!g.length)return;gl.bindBuffer(gl.ARRAY_BUFFER,V3.dyn);v3up(g);v3draw(V3.dyn,g.length/12,null)};
 // cracks on worked rock
 if(V3.work&&V3.rockGeo){V3.crack=V3.crack||new Map();for(const [key,e] of V3.work){if(e.broken||e.dmg<=0||e.roof)continue;const g0=V3.rockGeo.get(key);if(!g0)continue;const g=g0.ledge&&e.lvl!==1?g0.ledge:g0;const stage=Math.min(9,Math.floor(e.dmg/10));
  const K0=v3kindAt(e.x,e.y),half=K0&&K0.dug?1:0,one=!!g.stack&&e.lvl>=2,lvl=g.blocks?(e.lvl===0||e.lvl===1||one?e.lvl:(g.cut?1:0)):-1,st=g.blocks?(one?Math.min(9,Math.floor(e.dmg/10)):Math.min(9,Math.max(0,Math.floor((e.dmg-half*50)/5)))):stage,gc=g.stack&&lvl>=0&&g.L&&g.L[lvl]&&g.L[lvl].length?((g.crk=g.crk||{})[lvl]||(g.crk[lvl]={Y:g.Y+lvl,c:g.c,cut:lvl,blocks:g.blocks,s:g.L[lvl].map(f=>[f.d,f.c,f.m])})):g;    // a block an order: the bottom one, then on a notch the one above
  let c=V3.crack.get(key);if(!c||c.stage!==st||c.lvl!==lvl||c.g!==g){c={stage:st,lvl,g,a:new Float32Array(v3crackGeo(gc,st,e.x,e.y,lvl))}   /* on stacked rock: that block's own faces (Gather.dm) */;V3.crack.set(key,c)}geos.push(c.a)}}
 // trees being chopped, shaking at each blow
 if(V3.workTrees&&V3.workTrees.size&&V3.models&&V3.terrain){V3.treeGeo=V3.treeGeo||new Map();for(const key of V3.workTrees){const [x,y]=key.split(',').map(Number);let g=V3.treeGeo.get(key);
  if(!g){const K=v3kindAt(x,y);if(!K||K.kind!=='tree')continue;const a=[];MD.tallTree(a,x,0,-y,K,x,y);g={a:new Float32Array(a),B:[x,0,-y]};V3.treeGeo.set(key,g)}
  const s=V3.shake&&V3.shake.get(key),age=s?(now-s.t)/1000:9;if(age<0||age>1.2){geos.push(g.a);continue}
  const d=v3fallDir({x,y,dx:s.dx,dy:s.dy}),amp=0.09*Math.exp(-age*3.2)*Math.sin(age*24);geos.push(v3rot(g.a,g.B,[d[1],0,-d[0]],amp,0))}}
 // effects
 V3.bfx=(V3.bfx||[]).filter(f=>v3breakFx(f,now,lit,dust,geos));
 for(const g of geos)draw(g);draw(lit);
 // dust: soft and see-through, drawn in a few strengths
 if(dust.length){gl.enable(gl.BLEND);gl.blendFunc(gl.SRC_ALPHA,gl.ONE_MINUS_SRC_ALPHA);gl.depthMask(false);
  for(let b=1;b<=4;b++){const a=[];for(const d of dust)if(Math.ceil(d.al*4)===b)MD.blob(a,d.x,d.y,d.z,d.r,d.r*0.7,d.r,d.c,d.s,0.3);if(a.length){for(let i=3;i<a.length;i+=12){a[i]=0;a[i+1]=0;a[i+2]=0}gl.uniform1f(L.alpha,b/4*0.55);draw(a)}}
  gl.uniform1f(L.alpha,1);gl.depthMask(true);gl.disable(gl.BLEND)}}
// A little cube that flies, falls and bounces once; p carries its state between frames.
function v3cube(a,p,now,g,col,fade,round){const dt=Math.min(0.05,(now-(p.last||now))/1000);p.last=now;p.vy-=g*dt;p.x+=p.vx*dt;p.y+=p.vy*dt;p.z+=p.vz*dt;
 if(p.y<p.floor){p.y=p.floor;if(p.vy<-1.2){p.vy=-p.vy*0.3;p.vx*=0.5;p.vz*=0.5}else{p.vy=0;p.vx*=0.85;p.vz*=0.85}}
 const r=p.r*fade;if(r<0.004)return;if(round)MD.blob(a,p.x,p.y+r*0.8,p.z,r,r*0.8,r,col,p.s||1,0.35);else boxr(a,p.x-r,p.x+r,p.z-r,p.z+r,p.y,p.y+2*r,col)}
function v3breakFx(f,now,a,dust,geos){const age=(now-f.t)/1000;if(age<0)return true;const [X,,Z]=v3world({dx:f.x,dy:f.y});
 // a blow on rock: chips fly back towards the miner, with a puff of grit
 if(f.type==='chip'){if(age>0.9)return false;const col=f.geo?f.geo.rc:hexrgb(f.K&&f.K.color||'#777777',1),d=v3fallDir(f);
  if(!f.p&&f.roof){f.p=[];for(let k=0;k<4;k++)f.p.push({x:X+(MD.h(f.seed,k,1)-0.5)*0.6,y:f.roof-0.08,z:Z+(MD.h(f.seed,k,2)-0.5)*0.6,vx:(MD.h(f.seed,k,3)-0.5)*0.6,vy:-0.5,vz:(MD.h(f.seed,k,4)-0.5)*0.6,r:0.025+MD.h(f.seed,k,5)*0.03,floor:0.01})}
  if(!f.p){f.p=[];const lv=f.geo&&f.geo.blocks?f.geo.Y:0;for(let k=0;k<5;k++){const sp=1.2+MD.h(f.seed,k,1)*1.6,sd=(MD.h(f.seed,k,2)-0.5)*2.2;f.p.push({x:X-d[0]*0.5,y:lv+0.35+MD.h(f.seed,k,3)*0.5,z:Z-d[1]*0.5,vx:-d[0]*sp-d[1]*sd,vy:1.8+MD.h(f.seed,k,4)*2,vz:-d[1]*sp+d[0]*sd,r:0.025+MD.h(f.seed,k,5)*0.035,floor:0.01})}}
  for(const p of f.p)v3cube(a,p,now,12,MD.shade(col,0.8+MD.h(f.seed,p.r*99,6)*0.35),age>0.6?(0.9-age)/0.3:1);
  if(age<0.45)dust.push({x:X-d[0]*0.55,y:0.5+age*0.4,z:Z-d[1]*0.55,r:0.12+age*0.5,c:[0.7,0.66,0.6,1],al:1-age/0.45,s:f.seed});return true}
 // a blow on a tree: wood chips off the trunk, leaves drifting down from the crown
 if(f.type==='leaf'){if(age>1.8)return false;const d=v3fallDir(f),bam=/bamboo/.test(f.K&&f.K.state||''),leaf=bam?[0.4,0.62,0.26,1]:[0.3,0.52,0.22,1];
  if(!f.p){f.p=[];for(let k=0;k<3;k++){const sd=(MD.h(f.seed,k,2)-0.5)*1.6;f.p.push({x:X-d[0]*0.15,y:0.5,z:Z-d[1]*0.15,vx:-d[0]*1.4-d[1]*sd,vy:1.5+MD.h(f.seed,k,4),vz:-d[1]*1.4+d[0]*sd,r:0.02+MD.h(f.seed,k,5)*0.02,floor:0.01})}}
  for(const p of f.p)v3cube(a,p,now,12,[0.78,0.62,0.4,1],age>0.7?Math.max(0,(1-age)/0.3):1);
  for(let k=0;k<5;k++){const sx=(MD.h(f.seed,k,7)-0.5)*1.4,sz=(MD.h(f.seed,k,8)-0.5)*1.4,y=Math.max(0.03,(bam?2.6:f.K&&MD.treeKind(f.K,f.x,f.y)?3.1:2.1)+MD.h(f.seed,k,9)*0.6-age*1.3),sw=Math.sin(age*5+k)*0.18;
   MD.blob(a,X+sx+sw,y,Z+sz+Math.cos(age*4+k)*0.12,0.07,0.015,0.05,MD.shade(leaf,0.85+MD.h(k,f.seed,3)*0.3),f.seed+k,0.2)}return true}
 // rock broken: the block bursts into cubes that tumble out and bounce, in a cloud of dust
 if(f.type==='burst'){if(age>1.8)return false;const col=f.geo?f.geo.rc:f.col||[0.5,0.48,0.44],top=f.geo?Math.min(2.6,(f.geo.c[0][1]+f.geo.c[1][1]+f.geo.c[2][1]+f.geo.c[3][1])/4):(f.top||1);
  // a layer: rough chunks from its slab of rock
  const blk=f.geo&&f.geo.blocks?(f.level!=null?f.level:1):-1,base=f.geo?f.geo.Y-(f.geo.cut||0):0;
  if(!f.p){f.p=[];const n=blk>=0?18:(f.big?42:26);for(let k=0;k<n;k++){const ox=(MD.h(f.x,f.y,k*3)-0.5)*0.9,oz=(MD.h(f.y,f.x,k*3+1)-0.5)*0.9,oy=blk>=0?base+blk+0.15+MD.h(f.x+k,f.y,7)*0.7:0.1+MD.h(f.x+k,f.y,7)*top,sp=1+MD.h(k,f.x,8)*2.2,l=Math.hypot(ox,oz)||1;
    f.p.push({x:X+ox,y:oy,z:Z+oz,vx:ox/l*sp,vy:1.2+MD.h(f.y,k,9)*2.6,vz:oz/l*sp,r:blk>=0?0.08+MD.h(k,f.y,10)*0.1:0.05+MD.h(k,f.y,10)*0.07,floor:0.01,k:0.7+MD.h(f.x,k,11)*0.45,s:f.x*7+k})}}
  const fade=age>1.3?(1.8-age)/0.5:1;for(const p of f.p)v3cube(a,p,now,14,MD.shade(col,p.k),fade,blk>=0);
  if(age<1.2)for(let k=0;k<4;k++){const an=k*1.57+f.x,rr=0.3+age*0.9;dust.push({x:X+Math.cos(an)*age*0.6,y:0.3+age*0.5+k*0.12,z:Z+Math.sin(an)*age*0.6,r:rr,c:[0.66,0.62,0.56,1],al:(1-age/1.2)*0.9,s:f.x+k})}return true}
 // a cave-in: rock crashes down into the tunnel in a cloud of dust
 if(f.type==='collapse'){if(age>1.8)return false;if(!f.p){f.p=[];for(let k=0;k<16;k++)f.p.push({x:X+(MD.h(f.x,k,1)-0.5)*0.9,y:2.4+MD.h(f.y,k,2)*1.8,z:Z+(MD.h(f.y,k,3)-0.5)*0.9,vx:(MD.h(f.x,k,4)-0.5)*0.8,vy:-1-MD.h(f.y,k,5)*2,vz:(MD.h(f.x,k,6)-0.5)*0.8,r:0.08+MD.h(k,f.x,7)*0.12,floor:0.01,s:f.x*5+k})}
  const fade=age>1.3?(1.8-age)/0.5:1;for(const p of f.p)v3cube(a,p,now,14,MD.shade(f.col,0.75+MD.h(p.s,1,8)*0.4),fade,true);
  if(age<1.4)for(let k=0;k<4;k++)dust.push({x:X+Math.cos(k*1.6)*age*0.5,y:0.4+age*0.6+k*0.15,z:Z+Math.sin(k*1.6)*age*0.5,r:0.45+age*0.9,c:[0.6,0.57,0.52,1],al:(1-age/1.4)*0.9,s:f.y+k});return true}
 // a tree felled: it falls away from its feller, bounces, lies a moment and breaks into logs
 if(f.type==='fell'){const K=f.K||{},st=K.state||'',d=v3fallDir(f),axis=[d[1],0,-d[0]];
  if(/bamboo/.test(st)){if(age>3)return false;f.canes=f.canes||[0,1,2,3].map(k=>v3cane(K,f.x,f.y,k));
   f.canes.forEach((c,k)=>{const t=age-k*0.14;if(t<0){geos.push(c.g);return}const sp=(MD.h(f.x,f.y,k+40)-0.5)*0.7,dd=[d[0]*Math.cos(sp)-d[1]*Math.sin(sp),d[0]*Math.sin(sp)+d[1]*Math.cos(sp)],ax=[dd[1],0,-dd[0]];
    const T1=0.75,th=t<T1?Math.PI/2*(t/T1)**2:Math.PI/2-0.08*Math.abs(Math.sin((t-T1)*9))*Math.exp(-(t-T1)*5);
    if(t<1.5){geos.push(v3rot(c.g,c.B,ax,th,0.04*Math.sin(th)));return}
    // split into three lengths that roll apart, then sink away
    const q=Math.min(1,(t-1.5)/0.4),sink=Math.max(0,t-2.3)*0.5,y=0.05-sink;for(let s=0;s<3;s++){const r0=c.h*(s/3+0.02),r1=c.h*((s+1)/3-0.02),off=(s-1)*0.12*q,px=-dd[1]*off,pz=dd[0]*off;
     MD.rod(a,[c.B[0]+dd[0]*r0+px,y,c.B[2]+dd[1]*r0+pz],[c.B[0]+dd[0]*r1+px,y,c.B[2]+dd[1]*r1+pz],0.045,5,[0.52,0.62,0.3,1],f.x+k*3+s)}});
   if(age>0.75&&age<1.6)dust.push({x:X+d[0]*1.6,y:0.15,z:Z+d[1]*1.6,r:0.3+(age-0.75)*0.6,c:[0.6,0.66,0.45,1],al:(1.6-age)/0.85*0.7,s:f.x});return true}
  if(age>3.4)return false;if(!f.g){const g=[];MD.tallTree(g,X,0,Z,K,f.x,f.y);f.g=new Float32Array(g)}
  const T1=1.05,landed=age>=T1,th=!landed?Math.PI/2*(age/T1)**2:Math.PI/2-0.13*Math.abs(Math.sin((age-T1)*8))*Math.exp(-(age-T1)*4.5),cactus=/cactus/.test(st),pine=/pine|snow|fir/.test(st);
  if(age<2.3)geos.push(v3rot(f.g,[X,0,Z],axis,th,0.12*Math.sin(th)));
  // the crown hits the ground: leaves and dust
  if(landed&&age<2.1){const t=age-T1,tl=MD.treeKind(K,f.x,f.y)?MD.treeTop(K,f.x,f.y)*0.72:2.1,tip=[X+d[0]*tl,0,Z+d[1]*tl],leaf=cactus?[0.32,0.55,0.26,1]:pine?[0.16,0.36,0.22,1]:[0.3,0.52,0.22,1];
   for(let k=0;k<10;k++){const an=k*0.63+f.x,sp=0.6+MD.h(f.x,k,4)*1.2;MD.blob(a,tip[0]+Math.cos(an)*sp*t,Math.max(0.03,0.3+t*1.5-3.5*t*t),tip[2]+Math.sin(an)*sp*t,0.06,0.02,0.05,MD.shade(leaf,0.8+MD.h(k,f.y,2)*0.4),f.x+k,0.2)}
   if(t<0.9)dust.push({x:tip[0],y:0.25+t*0.3,z:tip[2],r:0.4+t*0.8,c:[0.62,0.6,0.52,1],al:(1-t/0.9)*0.8,s:f.y})}
  // logs (or cactus chunks) where it lay, rolling apart a little, then sinking away
  if(age>=2.3){const q=Math.min(1,(age-2.3)/0.35),sink=Math.max(0,age-2.9)*0.6;
   if(cactus){for(let s=0;s<3;s++){const r=0.5+s*0.55,c=[X+d[0]*r+(s-1)*0.1*q*-d[1],0.12-sink,Z+d[1]*r+(s-1)*0.1*q*d[0]];MD.blob(a,c[0],c[1],c[2],0.16,0.13,0.16,[0.32,0.55,0.26,1],f.x+s,0.25)}}
   else{const big=!!MD.treeKind(K,f.x,f.y),nl=big?4:3,lr=big?0.15:0.1;for(let s=0;s<nl;s++){const r0=0.15+s*0.6,r1=r0+0.52,off=(s-1.5)*0.16*q,px=-d[1]*off,pz=d[0]*off,y=lr+0.01-sink;MD.rod(a,[X+d[0]*r0+px,y,Z+d[1]*r0+pz],[X+d[0]*r1+px,y,Z+d[1]*r1+pz],lr,7,MD.PAL.bark.concat(1),f.x+s)}}}
  return true}
 return false}
// Steps or a ramp carved up a mountain (Mountains.dm): K.carve = [k, n, dir, top layers, ramp].
// The floor of tile k rises along dir from top*(k-1)/n to top*k/n; the rock either side stands
// as the walls of the cut, and the head tile is the stairs onto the peak.
function v3carveRock(g,T,kindAt,i,j,X,Y,Z,K){const [k,n,dir,top,ramp]=K.carve,Ht=top+0.4,h0=Ht*(k-1)/n,h1=Ht*k/n,tx=T.x0+i,ty=T.y0+j,h=0.5,ra=g('');
 const pal=K.biome==='mesa'?MD.PAL.mesa:K.biome==='ashlands'?MD.PAL.ash:K.biome==='tundra'?MD.PAL.tundraRock:T.z===1?MD.PAL.rock:MD.PAL.cave,rc=pal[Math.floor(MD.h(tx,ty,6)*pal.length)%pal.length];
 const ux=dir&4?1:dir&8?-1:0,uz=dir&1?-1:dir&2?1:0,vx=-uz,vz=ux,P=(a,c,y)=>[X+ux*a+vx*c,Y+y,Z+uz*a+vz*c];
 const tread=MD.shade(rc,1.18),riser=MD.shade(rc,0.82),side=MD.shade(rc,0.74),up=[0,1,0],back=[-ux,0,-uz];if(Y===0&&V3.rampH)V3.rampH.set(tx+','+ty,(h0+h1)/2);
 const sides=(a0,a1,y0,y1)=>{for(const c of [-h,h])quad(ra,P(a0,c,0),P(a1,c,0),P(a1,c,y1),P(a0,c,y0),[vx*Math.sign(c),0,vz*Math.sign(c)],side)};
 if(ramp){quad(ra,P(-h,-h,h0),P(h,-h,h1),P(h,h,h1),P(-h,h,h0),MD.n3(P(-h,-h,h0),P(h,-h,h1),P(-h,h,h0))[1]<0?MD.n3(P(-h,h,h0),P(h,-h,h1),P(-h,-h,h0)):MD.n3(P(-h,-h,h0),P(h,-h,h1),P(-h,h,h0)),tread);sides(-h,h,h0,h1);if(h0>0.01)quad(ra,P(-h,-h,0),P(-h,h,0),P(-h,h,h0),P(-h,-h,h0),back,riser)}
 else{const S=2;for(let s=0;s<S;s++){const a0=-h+s/S,a1=a0+1/S,hs=h0+(h1-h0)*(s+1)/S;quad(ra,P(a0,-h,hs),P(a1,-h,hs),P(a1,h,hs),P(a0,h,hs),up,MD.shade(tread,0.96+MD.h(tx+s,ty,7)*0.08));quad(ra,P(a0,-h,0),P(a0,h,0),P(a0,h,hs),P(a0,-h,hs),back,riser);sides(a0,a1,hs,hs)}}}
// Height of the rock top under a unit up on the sky layer: a mountain, a carved run's head, a tunnel's roof.
function v3peakTop(x,y){const K=v3kindAt(x,y);if(!K)return 0;
 // the rock top as drawn (its corners carry noise): the middle, or a little under the highest edge so feet stay clear
 const G=(K.kind==='wall'||K.roof)&&V3.rockGeo&&V3.rockGeo.get(x+','+y);if(G&&G.c&&G.slope&&!(K.slopeh&&K.slopeh<v3stackTop(K)))return (G.c[0][1]+G.c[1][1]+G.c[2][1]+G.c[3][1])/4+0.03;   /* a ramp: half way up its slope */if(G&&G.stack){let tk=-1;for(const q in G.L)if(G.L[q].top)tk=Math.max(tk,+q);const F=tk>=0&&G.L[tk].top;if(F)return F.m[1]+0.02}   /* stacked rock: on its top block's top as drawn, feet never in the stone */if(G&&G.c){const [sw,se,ne,nw]=G.c,m=(sw[1]+ne[1])/2,e=Math.max((sw[1]+se[1])/2,(se[1]+ne[1])/2,(ne[1]+nw[1])/2,(nw[1]+sw[1])/2)-0.15;return Math.max(m,e)+0.03}
if(K.kind==='wall'&&K.blocks)return K.blocks+0.42;if(K.roof&&K.kind!=='wall')return (K.ceil||2)+K.roof+0.42;if(K.kind==='carve'&&K.carve&&K.carve[0]===K.carve[1])return K.carve[3]+0.42;if(K.state&&String(K.state).startsWith('lift')){let h=0;for(const [a,b] of [[1,0],[-1,0],[0,1],[0,-1]]){const n=v3kindAt(x+a,y+b);if(n&&!String(n.state||'').startsWith('lift'))h=Math.max(h,v3peakTop(x+a,y+b))}return h}return 0}
// Where a unit up on a mountain stands at height f (blocks): on block f-1's top as drawn, a dug-out floor inside the
// mountain or its top (Gather.dm "one block, everywhere"); f unknown or no block drawn there: the top (v3peakTop).
function v3feetY(x,y,f){if(f==null)return v3peakTop(x,y);const G=V3.rockGeo&&V3.rockGeo.get(x+','+y);if(G&&G.stack&&G.L){let tk=-1;for(const q in G.L)if(G.L[q].top)tk=Math.max(tk,+q);const F=tk!==f-1&&G.L[f-1]&&G.L[f-1].top;if(F)return F.m[1]+0.02}return v3peakTop(x,y)}
// Hellgates: a ring of black obsidian spikes on scorched ground around a floating
// rift of hellfire that always turns to face you, a red glow on the ground and
// embers rising out of it. A gate in Hell (back up to the surface) burns paler.
function v3hellgates(gates,ts,gl,L){if(!gates.length)return;
 const lit=[],fire=[],glow=[],t=ts/1000,tc=[Math.sin(V3.yaw),0,Math.cos(V3.yaw)],rt=[Math.cos(V3.yaw),0,-Math.sin(V3.yaw)];
 const draw=arr=>{if(!arr.length)return;gl.bindBuffer(gl.ARRAY_BUFFER,V3.dyn);v3up(arr);v3draw(V3.dyn,arr.length/12,null)};
 const flat=arr=>{for(let i=3;i<arr.length;i+=12){arr[i]=0;arr[i+1]=0;arr[i+2]=0}};
 // an ellipse standing at C facing the camera (off: nudged toward it), its edge jagged and turning
 const disc=(arr,C,rx,ry,off,col,n,spin,jag,seed)=>{const c0=[C[0]+tc[0]*off,C[1],C[2]+tc[2]*off];
  const P=k=>{const an=k/n*6.2832+spin,j=1+(MD.h(seed,k%n,7)-0.5)*jag;return [c0[0]+rt[0]*Math.cos(an)*rx*j,C[1]+Math.sin(an)*ry*j,c0[2]+rt[2]*Math.cos(an)*rx*j]};
  for(let k=0;k<n;k++){const p0=P(k),p1=P(k+1);tri(arr,c0,p0,p1,[0,0,0],col);tri(arr,c0,p1,p0,[0,0,0],col)}};
 const K=1.55;  // a landmark: about one and a half tiles across
 for(const q of gates){const [X,,Z]=v3world(q),Y=v3groundAt(q.x,q.y),up=q.hellgate==='up',s=q.x*7+q.y*13,pulse=0.93+0.07*Math.sin(t*3.1+s);
  MD.blob(lit,X,Y+0.02,Z,1.05*K,0.04,1.05*K,[0.14,0.06,0.05,1],s,0.35);
  for(let k=0;k<7;k++){const an=k/7*6.2832+MD.h(q.x,q.y,k)*0.4,r=(0.8+MD.h(q.y,q.x,k)*0.14)*K,hh=(0.75+MD.h(q.x,k,q.y)*0.85)*K;
   MD.cone(lit,X+Math.cos(an)*r,Z+Math.sin(an)*r,Y,Y+hh,(0.14+MD.h(k,q.x,1)*0.06)*K,5,[0.09,0.07,0.1,1],s+k,false);
   MD.blob(fire,X+Math.cos(an)*r*0.84,Y+0.07,Z+Math.sin(an)*r*0.84,0.08*K,0.05,0.08*K,[1,0.3+0.25*Math.sin(t*3+k),0.06,1],s+k,0.2)}
  const C=[X,Y+(1.1+0.05*Math.sin(t*1.7+s))*K,Z];
  const cols=up?[[0.6,0.22,0.06,1],[0.98,0.58,0.16,1],[1,0.86,0.5,1],[1,0.98,0.88,1]]:[[0.07,0.0,0.02,1],[0.78,0.08,0.04,1],[1,0.4,0.07,1],[1,0.84,0.38,1]];
  disc(fire,C,0.52*K*pulse,0.74*K*pulse,0,cols[0],18,t*0.6,0.35,s);
  disc(fire,C,0.4*K*pulse,0.58*K*pulse,0.02,cols[1],16,-t*0.9,0.4,s+1);
  disc(fire,C,0.26*K,0.39*K,0.04,cols[2],14,t*1.5,0.45,s+2);
  disc(fire,C,0.11*K,0.17*K,0.06,cols[3],10,-t*2.2,0.3,s+3);
  for(let k=0;k<9;k++){const life=((t*0.45)+k/9+MD.h(q.x,q.y,k))%1,ex=((MD.h(q.x,k,2)-0.5)*0.8+Math.sin(t*2+k)*0.08)*K,sz=(0.05*(1-life)+0.012)*K;
   MD.blob(fire,C[0]+rt[0]*ex+tc[0]*0.12,C[1]-0.35*K+life*1.7*K,C[2]+rt[2]*ex+tc[2]*0.12,sz,sz,sz,[1,0.6-0.45*life,0.08,1],k,0.1)}
  disc(glow,C,0.9*K*pulse,1.12*K*pulse,-0.03,up?[1,0.7,0.35,1]:[1,0.42,0.12,1],20,t*0.3,0.25,s+4);
  for(let k=0;k<20;k++){const a0=k/20*6.2832,a1=(k+1)/20*6.2832,R=1.35*K*pulse;
   tri(glow,[X,Y+0.05,Z],[X+Math.cos(a0)*R,Y+0.05,Z+Math.sin(a0)*R],[X+Math.cos(a1)*R,Y+0.05,Z+Math.sin(a1)*R],[0,0,0],up?[0.9,0.5,0.2,1]:[0.9,0.12,0.04,1]);
   tri(glow,[X,Y+0.05,Z],[X+Math.cos(a1)*R,Y+0.05,Z+Math.sin(a1)*R],[X+Math.cos(a0)*R,Y+0.05,Z+Math.sin(a0)*R],[0,0,0],up?[0.9,0.5,0.2,1]:[0.9,0.12,0.04,1])}}
 draw(lit);
 // the fire is unlit and keeps its full brightness at night
 flat(fire);gl.uniform1f(L.amb,1);draw(fire);
 // the halo and the ground glow add light on top
 flat(glow);gl.enable(gl.BLEND);gl.blendFunc(gl.SRC_ALPHA,gl.ONE);gl.depthMask(false);gl.uniform1f(L.alpha,0.2+0.06*Math.sin(t*2.3));gl.uniform1f(L.addm,1);draw(glow);gl.uniform1f(L.addm,0);
 gl.uniform1f(L.alpha,1);gl.depthMask(true);gl.blendFunc(gl.SRC_ALPHA,gl.ONE_MINUS_SRC_ALPHA);gl.disable(gl.BLEND);gl.uniform1f(L.amb,V3.amb==null?1:V3.amb)}
function v3drawFx(ts){if(!V3.fx||!V3.fx.length)return;const gl=V3.gl,now=performance.now(),a=(V3.fxA||(V3.fxA=new VA())).reset(),gw=(V3.fxG||(V3.fxG=new VA())).reset(),sb=(V3.fxS||(V3.fxS=new VA())).reset();
 V3.fx=V3.fx.filter(f=>{
  if(f.type==='special')return v3drawSpecial(a,f,now);
  if(f.type==='puff')return v3puff(a,gw,f,now,sb);
  if(f.type==='dust')return v3dust(sb,f,now);
  // shots: arrows, javelins, throwing axes and rocks arc from the shooter to the target
  if(f.type==='proj'){const s=(now-f.t)/f.dur,stay=f.miss&&(f.p==='arrow'||f.p==='javelin')?0.9:0;if(s>1+stay*1000/f.dur)return false;
   const [AX,,AZ]=v3world({dx:f.ax,dy:f.ay}),[BX0,,BZ0]=v3world({dx:f.x,dy:f.y}),ddx=BX0-AX,ddz=BZ0-AZ,l=Math.hypot(ddx,ddz)||1,ux=ddx/l,uz=ddz/l;
   const over=f.miss?0.7+MD.h(f.seed,1,5)*0.6:0,side=f.miss?(MD.h(f.seed,2,6)-0.5)*0.9:0,BX=BX0+ux*over-uz*side,BZ=BZ0+uz*over+ux*side;
   const YA=v3groundAt(f.ax,f.ay)+(f.p==='boulder'?1.9:0.85),YB=f.miss?v3groundAt(f.x,f.y)+0.05:v3groundAt(f.x,f.y)+0.6,H=f.p==='bolt'?0.05:{arrow:0.18,javelin:0.26,axe:0.2,rock:0.3,boulder:0.38}[f.p]*l+0.3;
   const at=t=>{t=Math.min(1,t);return [AX+(BX-AX)*t,YA+(YB-YA)*t+4*H*t*(1-t),AZ+(BZ-AZ)*t]};
   const line=(p0,p1,w,c)=>{const dx=p1[0]-p0[0],dz=p1[2]-p0[2],hl=Math.hypot(dx,dz)||1,nx=-dz/hl*w,nz=dx/hl*w;
    quad(a,[p0[0]-nx,p0[1],p0[2]-nz],[p0[0]+nx,p0[1],p0[2]+nz],[p1[0]+nx,p1[1],p1[2]+nz],[p1[0]-nx,p1[1],p1[2]-nz],[0,0,0],c);quad(a,[p1[0]-nx,p1[1],p1[2]-nz],[p1[0]+nx,p1[1],p1[2]+nz],[p0[0]+nx,p0[1],p0[2]+nz],[p0[0]-nx,p0[1],p0[2]-nz],[0,0,0],c);
    quad(a,[p0[0],p0[1]-w,p0[2]],[p0[0],p0[1]+w,p0[2]],[p1[0],p1[1]+w,p1[2]],[p1[0],p1[1]-w,p1[2]],[0,0,0],c);quad(a,[p1[0],p1[1]-w,p1[2]],[p1[0],p1[1]+w,p1[2]],[p0[0],p0[1]+w,p0[2]],[p0[0],p0[1]-w,p0[2]],[0,0,0],c)};
   const st=Math.min(1,s),P=at(st),Q=st<1?at(st+0.03):P,R=st<1?P:at(0.97);let tx=Q[0]-R[0]+(st<1?0:0),ty=Q[1]-R[1],tz=Q[2]-R[2];if(st>=1){const P2=at(0.97);tx=P[0]-P2[0];ty=P[1]-P2[1];tz=P[2]-P2[2]}const tl=Math.hypot(tx,ty,tz)||1;tx/=tl;ty/=tl;tz/=tl;
   const back=k=>[P[0]-tx*k,P[1]-ty*k,P[2]-tz*k];
   // a faint streak behind a shot in flight (added light), so its path reads
   if(st<1&&f.p!=='boulder'&&f.p!=='rock'&&f.p!=='axe'){const E=V3.eye,L2=f.p==='bolt'?2.2:1.5,T0=back(f.p==='javelin'?1.1:0.5),T1=back(L2+0.5),vx=T0[0]-E[0],vy=T0[1]-E[1],vz=T0[2]-E[2];let wx=ty*vz-tz*vy,wy=tz*vx-tx*vz,wz=tx*vy-ty*vx;const wl=Math.hypot(wx,wy,wz)||1,ww=0.035/wl;wx*=ww;wy*=ww;wz*=ww;const k0=[0.34,0.32,0.28,1],k1=[0,0,0,1];quad4(gw,[T0[0]-wx,T0[1]-wy,T0[2]-wz],[T0[0]+wx,T0[1]+wy,T0[2]+wz],[T1[0],T1[1],T1[2]],[T1[0],T1[1],T1[2]],QN0,k0,k0,k1,k1)}
   if(f.p==='arrow'){line(back(0.6),P,0.024,[0.42,0.3,0.18,1]);MD.blob(a,P[0],P[1],P[2],0.03,0.03,0.03,[0.75,0.77,0.8,1],f.seed,0.1);line(back(0.6),back(0.44),0.055,[0.95,0.93,0.88,1])}
   else if(f.p==='javelin'){line(back(1.1),P,0.034,[0.45,0.32,0.18,1]);line(back(0.16),P,0.055,[0.78,0.8,0.84,1])}
   else if(f.p==='axe'){const sp=(now-f.t)*0.022,c=Math.cos(sp),sn=Math.sin(sp),hx=ux*c,hz=uz*c,hy=sn;const E0=[P[0]-hx*0.22,P[1]-hy*0.22,P[2]-hz*0.22],E1=[P[0]+hx*0.22,P[1]+hy*0.22,P[2]+hz*0.22];line(E0,E1,0.02,[0.5,0.35,0.2,1]);MD.blob(a,E1[0],E1[1],E1[2],0.09,0.09,0.09,[0.78,0.8,0.84,1],f.seed,0.15)}
   else if(f.p==='bolt'){line(back(1.3),P,0.04,[0.38,0.27,0.15,1]);line(back(0.2),P,0.07,[0.72,0.74,0.78,1]);line(back(1.3),back(1.05),0.11,[0.85,0.82,0.75,1])}   // a ballista's (Siege.dm)
   else if(f.p==='boulder')MD.blob(a,P[0],P[1],P[2],0.24,0.21,0.24,[0.5,0.47,0.43,1],f.seed,0.4);
   else MD.blob(a,P[0],P[1],P[2],0.11,0.09,0.11,[0.55,0.52,0.48,1],f.seed,0.35);
   return true}
  // weapon strikes: each class has its own stroke over the target
  if(f.type==='swing'){const age=(now-f.t)/1000,life=f.w==='mace'?0.45:0.32;if(age>life)return false;const p=age/life,[X,,Z]=v3world({dx:f.x,dy:f.y}),[AX,,AZ]=v3world({dx:f.ax,dy:f.ay}),Y=v3groundAt(f.x,f.y)+0.7;
   const dx=X-AX,dz=Z-AZ,l=Math.hypot(dx,dz)||1,ux=dx/l,uz=dz/l,px=-uz,pz=ux,fade=1-p;
   const strip=(x0,y0,z0,x1,y1,z1,w,c)=>{const nx=px*w,nz=pz*w;quad(a,[x0-nx,y0,z0-nz],[x0+nx,y0,z0+nz],[x1+nx,y1,z1+nz],[x1-nx,y1,z1-nz],[0,0,0],c);quad(a,[x1-nx,y1,z1-nz],[x1+nx,y1,z1+nz],[x0+nx,y0,z0+nz],[x0-nx,y0,z0-nz],[0,0,0],c)};
   const arc=(r,w,c,span)=>{const n=7,s0=-span/2+p*0.6;for(let k=0;k<n;k++){const a0=s0+span*k/n,a1=s0+span*(k+1)/n;const P=t=>[X-ux*0.15+Math.cos(t)*px*r+Math.sin(t)*ux*r*0.4,Y+0.35-Math.sin(t+0.6)*0.45,Z-uz*0.15+Math.cos(t)*pz*r+Math.sin(t)*uz*r*0.4];const q0=P(a0),q1=P(a1);strip(q0[0],q0[1],q0[2],q1[0],q1[1],q1[2],w,c)}};
   if(f.w==='sword')arc(0.55,0.03,[0.92,0.94,1,1],2.4*fade+0.4);
   else if(f.w==='axe')arc(0.6,0.06,[1,0.55,0.4,1],2.0*fade+0.4);
   else if(f.w==='parry'){for(let k=0;k<6;k++){const an=k*1.05+p*2;MD.blob(a,X-ux*0.3+Math.cos(an)*0.25*p,Y+0.3+Math.sin(an)*0.25*p,Z-uz*0.3,0.03,0.03,0.03,[1,0.95,0.6,1],k,0.1)}strip(X-ux*0.3-px*0.3,Y+0.6,Z-uz*0.3-pz*0.3,X-ux*0.3+px*0.3,Y+0.1,Z-uz*0.3+pz*0.3,0.025,[0.8,0.85,0.95,1])}
   else if(f.w==='mace'){const r=0.15+p*0.75,n=12;for(let k=0;k<n;k++){const a0=k/n*6.283,a1=(k+1)/n*6.283;quad(a,[X+Math.cos(a0)*r,Y-0.62,Z+Math.sin(a0)*r],[X+Math.cos(a1)*r,Y-0.62,Z+Math.sin(a1)*r],[X+Math.cos(a1)*(r+0.08),Y-0.62,Z+Math.sin(a1)*(r+0.08)],[X+Math.cos(a0)*(r+0.08),Y-0.62,Z+Math.sin(a0)*(r+0.08)],[0,0,0],[0.85,0.8,0.7,1])}for(let k=0;k<4;k++)MD.blob(a,X+(MD.h(f.x,k,3)-0.5)*0.6*p,Y-0.5+p*0.5-p*p*0.6,Z+(MD.h(f.y,k,4)-0.5)*0.6*p,0.05,0.05,0.05,[0.55,0.5,0.45,1],k,0.2)}
   else if(f.w==='spear'){const reach=Math.min(l,2.2),k0=0.3+p*0.5;strip(AX+ux*k0*reach*0.4,Y,AZ+uz*k0*reach*0.4,AX+ux*(k0*reach+0.6),Y,AZ+uz*(k0*reach+0.6),0.02,[0.95,0.9,0.75,1])}
   else if(f.w==='dagger'){for(let k=0;k<2;k++){const o=(k-0.5)*0.25,c=[0.95,0.95,1,1];strip(X-ux*0.2-px*0.25,Y+0.3+o,Z-uz*0.2-pz*0.25,X-ux*0.2+px*0.25,Y+0.1+o,Z-uz*0.2+pz*0.25,0.015,c)}}
   else if(f.w==='claws'){for(let k=-1;k<=1;k++)strip(X-ux*0.2+px*0.12*k,Y+0.5,Z-uz*0.2+pz*0.12*k,X-ux*0.2+px*(0.12*k+0.1),Y-0.1,Z-uz*0.2+pz*(0.12*k+0.1),0.02,[0.9,0.25,0.2,1])}
   else MD.blob(a,X-ux*0.3,Y+0.2,Z-uz*0.3,0.12+p*0.2,0.12+p*0.2,0.12+p*0.2,[0.95,0.9,0.8,1],f.x,0.3);
   return true}const age=(now-f.t)/1000,[X,,Z]=v3world({dx:f.x,dy:f.y}),Y0=v3groundAt(f.x,f.y);
  if(f.type==='rock'){if(age>1.1)return false;const g=9.8;
   for(let k=0;k<9;k++){const an=k*0.7+f.x*1.3,sp=0.9+MD.h(f.x+k,f.y,8)*1.4,up=2.2+MD.h(f.x,f.y+k,9)*1.8,t=age;
    const px=X+Math.cos(an)*sp*t,pz=Z+Math.sin(an)*sp*t,py=Math.max(Y0+0.05,Y0+0.5+up*t-0.5*g*t*t),r=0.07+MD.h(k,f.x,10)*0.08;
    MD.blob(a,px,py,pz,r,r*0.8,r,MD.shade(f.col,0.75+MD.h(k,f.y,11)*0.4),k+f.x,0.3)}
   const d=Math.min(1,age/1.1),dr=0.35+d*0.6;MD.blob(a,X,Y0+0.25+d*0.3,Z,dr,dr*0.55,dr,[0.62,0.58,0.52,1],f.x+f.y,0.35);return true}
  // tree: rotate from upright to lying flat around its base, then sink and fade
  if(age>2.2)return false;const fall=Math.min(1,age/1.1),ang=fall*fall*Math.PI/2,sink=Math.max(0,age-1.5)*0.6,ca=Math.cos(ang),sa=Math.sin(ang),dx=Math.cos(f.dir),dz=Math.sin(f.dir);
  const P=(u,h,w)=>{const along=h*sa,up=h*ca;return [X+dx*along+u*(-dz)+w*dx*0,Y0+up-sink,Z+dz*along+u*dx]};
  const trunk=[0.4,0.27,0.14,1],leaf=f.pine?[0.16,0.42,0.22,1]:[0.25,0.55,0.2,1];
  for(const [u0,u1] of [[-0.07,0.07]]){quad(a,P(u0,0,0),P(u1,0,0),P(u1,1.1,0),P(u0,1.1,0),[0,0,0],trunk);quad(a,P(u1,0,0),P(u0,0,0),P(u0,1.1,0),P(u1,1.1,0),[0,0,0],trunk)}
  // the canopy as solid lumps along the trunk, so it reads from any side
  const layers=f.pine?[[0.95,0.42],[1.3,0.34],[1.62,0.25],[1.88,0.15]]:[[1.15,0.42],[1.45,0.5]];for(const [h,r] of layers){const c=P(0,h,0);MD.blob(a,c[0],c[1],c[2],r,r,r,MD.shade(leaf,0.85+h*0.08),f.x+h*10,0.22)}
  if(fall>=1&&age<1.6)for(let k=0;k<6;k++){const t=age-1.1,an=k*1.05+f.y,tip=P(0,1.4,0);MD.blob(a,tip[0]+Math.cos(an)*t*1.2,Math.max(Y0+0.04,tip[1]+t*1.2-4*t*t),tip[2]+Math.sin(an)*t*1.2,0.06,0.04,0.06,leaf,k,0.2)}
  return true});
 if(a.length){gl.bindBuffer(gl.ARRAY_BUFFER,V3.dyn);v3up(a);v3draw(V3.dyn,a.length/12,null)}
 if(sb.length&&V3.soft){const L=V3.loc;gl.enable(gl.BLEND);gl.blendFunc(gl.SRC_ALPHA,gl.ONE_MINUS_SRC_ALPHA);gl.depthMask(false);gl.uniform1f(L.soft,1);gl.bindBuffer(gl.ARRAY_BUFFER,V3.dyn);v3up(sb);v3draw(V3.dyn,sb.length/12,V3.soft);gl.uniform1f(L.soft,0);gl.depthMask(true);gl.disable(gl.BLEND)}
 if(gw.length){const L=V3.loc;gl.enable(gl.BLEND);gl.blendFunc(gl.ONE,gl.ONE);gl.depthMask(false);gl.uniform1f(L.addm,1);gl.bindBuffer(gl.ARRAY_BUFFER,V3.dyn);v3up(gw);v3draw(V3.dyn,gw.length/12,null);gl.uniform1f(L.addm,0);gl.depthMask(true);gl.blendFunc(gl.SRC_ALPHA,gl.ONE_MINUS_SRC_ALPHA);gl.disable(gl.BLEND)}}
