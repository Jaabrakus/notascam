// ===== 3D models: low-poly, flat-shaded, painted vertex colours (RuneScape-like) =====
// Everything is built from the tile's world position, so a tree or rock looks
// the same every time you see it, and neighbouring tiles share corner heights.
const MD={
 h(x,y,s=0){let n=(x*374761393+y*668265263+s*2147483647)|0;n=(n^(n>>>13))*1274126177|0;n^=n>>>16;return (n>>>0)/4294967296},
 // Smooth value noise for large, soft colour patches.
 vn(x,y,sc,sd=0){const fx=x/sc,fy=y/sc,ix=Math.floor(fx),iy=Math.floor(fy),tx=fx-ix,ty=fy-iy,sx=tx*tx*(3-2*tx),sy=ty*ty*(3-2*ty);const a=MD.h(ix,iy,sd),b=MD.h(ix+1,iy,sd),c=MD.h(ix,iy+1,sd),d=MD.h(ix+1,iy+1,sd);return a+(b-a)*sx+(c-a)*sy+(a-b-c+d)*sx*sy},
 n3(a,b,c){const ux=b[0]-a[0],uy=b[1]-a[1],uz=b[2]-a[2],vx=c[0]-a[0],vy=c[1]-a[1],vz=c[2]-a[2];let x=uy*vz-uz*vy,y=uz*vx-ux*vz,z=ux*vy-uy*vx;const l=Math.hypot(x,y,z)||1;return [x/l,y/l,z/l]},
 // A face lit as a flat facet; its normal points away from 'out' (a point inside the shape).
 f(a,p0,p1,p2,c,out){const ux=p1[0]-p0[0],uy=p1[1]-p0[1],uz=p1[2]-p0[2],vx=p2[0]-p0[0],vy=p2[1]-p0[1],vz=p2[2]-p0[2];let x=uy*vz-uz*vy,y=uz*vx-ux*vz,z=ux*vy-uy*vx;const l=Math.sqrt(x*x+y*y+z*z)||1;x/=l;y/=l;z/=l;
  if(out){const cx=(p0[0]+p1[0]+p2[0])/3-out[0],cy=(p0[1]+p1[1]+p2[1])/3-out[1],cz=(p0[2]+p1[2]+p2[2])/3-out[2];if(x*cx+y*cy+z*cz<0){x=-x;y=-y;z=-z}}else if(y<0){x=-x;y=-y;z=-z}
  const r=c[0],g=c[1],b=c[2],al=c[3];if(a instanceof VA){a.v(p0[0],p0[1],p0[2],x,y,z,0,0,r,g,b,al);a.v(p1[0],p1[1],p1[2],x,y,z,0,0,r,g,b,al);a.v(p2[0],p2[1],p2[2],x,y,z,0,0,r,g,b,al);return}a.push(p0[0],p0[1],p0[2],x,y,z,0,0,r,g,b,al,p1[0],p1[1],p1[2],x,y,z,0,0,r,g,b,al,p2[0],p2[1],p2[2],x,y,z,0,0,r,g,b,al)},
 // MD.f on three corners held in a flat array (offsets A, B, C), lit away from (ox,oy,oz): no temporary arrays.
 fw(a,W,A,B,C,r,g,b,al,ox,oy,oz){const ux=W[B]-W[A],uy=W[B+1]-W[A+1],uz=W[B+2]-W[A+2],vx=W[C]-W[A],vy=W[C+1]-W[A+1],vz=W[C+2]-W[A+2];let x=uy*vz-uz*vy,y=uz*vx-ux*vz,z=ux*vy-uy*vx;const l=Math.sqrt(x*x+y*y+z*z)||1;x/=l;y/=l;z/=l;
  if(x*((W[A]+W[B]+W[C])/3-ox)+y*((W[A+1]+W[B+1]+W[C+1])/3-oy)+z*((W[A+2]+W[B+2]+W[C+2])/3-oz)<0){x=-x;y=-y;z=-z}
  if(a instanceof VA){a.v(W[A],W[A+1],W[A+2],x,y,z,0,0,r,g,b,al);a.v(W[B],W[B+1],W[B+2],x,y,z,0,0,r,g,b,al);a.v(W[C],W[C+1],W[C+2],x,y,z,0,0,r,g,b,al);return}a.push(W[A],W[A+1],W[A+2],x,y,z,0,0,r,g,b,al,W[B],W[B+1],W[B+2],x,y,z,0,0,r,g,b,al,W[C],W[C+1],W[C+2],x,y,z,0,0,r,g,b,al)},
 shade(c,k){return [Math.min(1,c[0]*k),Math.min(1,c[1]*k),Math.min(1,c[2]*k),c[3]===undefined?1:c[3]]},
 mix(a,b,t){return [a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t,a[2]+(b[2]-a[2])*t,1]},
 // A tapered prism (trunks, stalks, cactus): n sides from r0 at y0 to r1 at y1.
 prism(a,x,z,y0,y1,r0,r1,n,c,seed,lean=0){const out=[x,(y0+y1)/2,z];const off=MD.h(seed,7)*6.28;for(let k=0;k<n;k++){const t0=off+k/n*6.2832,t1=off+(k+1)/n*6.2832;const b0=[x+Math.cos(t0)*r0,y0,z+Math.sin(t0)*r0],b1=[x+Math.cos(t1)*r0,y0,z+Math.sin(t1)*r0],u0=[x+lean+Math.cos(t0)*r1,y1,z+Math.sin(t0)*r1],u1=[x+lean+Math.cos(t1)*r1,y1,z+Math.sin(t1)*r1];const cc=MD.shade(c,0.9+MD.h(seed,k)*0.2);MD.f(a,b0,b1,u1,cc,out);MD.f(a,b0,u1,u0,cc,out)}},
 // A faceted blob (leaves, bushes, boulders): an octahedron split once and jittered.
 blob(a,cx,cy,cz,rx,ry,rz,c,seed,jit=0.22){const T=MD.BT||MD.blobTopo(),P=T.P,Wp=T.W,I=T.I,np=P.length/3,nt=I.length/3,c0=c[0],c1=c[1],c2=c[2],c3=c[3]===undefined?1:c[3];
  for(let i=0;i<np;i++){const j=1+(MD.h(seed,i)-0.5)*2*jit;Wp[i*3]=cx+P[i*3]*rx*j;Wp[i*3+1]=cy+P[i*3+1]*ry*j;Wp[i*3+2]=cz+P[i*3+2]*rz*j}
  for(let i=0;i<nt;i++){const A=I[i*3]*3,B=I[i*3+1]*3,C=I[i*3+2]*3,yy=(Wp[A+1]+Wp[B+1]+Wp[C+1])/3-cy,k=0.82+0.3*(yy/ry*0.5+0.5)+(MD.h(seed,i+50)-0.5)*0.12;MD.fw(a,Wp,A,B,C,Math.min(1,c0*k),Math.min(1,c1*k),Math.min(1,c2*k),c3,cx,cy,cz)}},
 // The blob's shape (an octahedron split once): its unit corners and faces, worked out once.
 blobTopo(){const V=[[1,0,0],[-1,0,0],[0,1,0],[0,-1,0],[0,0,1],[0,0,-1]];const F=[[0,2,4],[4,2,1],[1,2,5],[5,2,0],[4,3,0],[1,3,4],[5,3,1],[0,3,5]];
  const mid=new Map();const pts=V.map(v=>v.slice());const m=(i,j)=>{const k=i<j?i+'_'+j:j+'_'+i;if(mid.has(k))return mid.get(k);const p=[(pts[i][0]+pts[j][0])/2,(pts[i][1]+pts[j][1])/2,(pts[i][2]+pts[j][2])/2];const l=Math.hypot(...p);pts.push(p.map(v=>v/l));mid.set(k,pts.length-1);return pts.length-1};
  const tris=[];for(const [x,y,z] of F){const ab=m(x,y),bc=m(y,z),ca=m(z,x);tris.push([x,ab,ca],[ab,y,bc],[ca,bc,z],[ab,bc,ca])}
  return MD.BT={P:new Float64Array(pts.flat()),I:new Uint8Array(tris.flat()),W:new Float64Array(pts.length*3)}},
 // A leaf clump: an icosahedron, jittered and shaded lighter on top (rounder than a blob for fewer faces).
 ICO:(()=>{const t=(1+Math.sqrt(5))/2,V=[[-1,t,0],[1,t,0],[-1,-t,0],[1,-t,0],[0,-1,t],[0,1,t],[0,-1,-t],[0,1,-t],[t,0,-1],[t,0,1],[-t,0,-1],[-t,0,1]].map(v=>{const l=Math.hypot(...v);return v.map(q=>q/l)});
  return {V,F:[[0,11,5],[0,5,1],[0,1,7],[0,7,10],[0,10,11],[1,5,9],[5,11,4],[11,10,2],[10,7,6],[7,1,8],[3,9,4],[3,4,2],[3,2,6],[3,6,8],[3,8,9],[4,9,5],[2,4,11],[6,2,10],[8,6,7],[9,8,1]]}})(),
 clump(a,cx,cy,cz,rx,ry,rz,c,seed,jit=0.22){const {V,F}=MD.ICO,W=V.map((p,i)=>{const j=1+(MD.h(seed,i)-0.5)*2*jit;return [cx+p[0]*rx*j,cy+p[1]*ry*j,cz+p[2]*rz*j]}),out=[cx,cy,cz];
  F.forEach((t,i)=>{const yy=(W[t[0]][1]+W[t[1]][1]+W[t[2]][1])/3-cy,k=0.82+0.3*(yy/ry*0.5+0.5)+(MD.h(seed,i+50)-0.5)*0.12;MD.f(a,W[t[0]],W[t[1]],W[t[2]],MD.shade(c,k),out)})},
 // A small four-faced bead (berries, twig ends).
 gem(a,x,y,z,r,c){const P=[[x,y+r,z],[x+r*0.94,y-r*0.33,z],[x-r*0.47,y-r*0.33,z+r*0.82],[x-r*0.47,y-r*0.33,z-r*0.82]],o=[x,y,z];MD.f(a,P[0],P[1],P[2],c,o);MD.f(a,P[0],P[2],P[3],c,o);MD.f(a,P[0],P[3],P[1],c,o);MD.f(a,P[1],P[3],P[2],c,o)},
 // A round log of n sides between two points, capped at both ends (cabins, rails).
 rod(a,p0,p1,r,n,c,seed){const d=[p1[0]-p0[0],p1[1]-p0[1],p1[2]-p0[2]],L=Math.hypot(...d)||1,u=d.map(v=>v/L),ref=Math.abs(u[1])<0.9?[0,1,0]:[1,0,0];let v1=[u[1]*ref[2]-u[2]*ref[1],u[2]*ref[0]-u[0]*ref[2],u[0]*ref[1]-u[1]*ref[0]];const l1=Math.hypot(...v1);v1=v1.map(x=>x/l1);const v2=[u[1]*v1[2]-u[2]*v1[1],u[2]*v1[0]-u[0]*v1[2],u[0]*v1[1]-u[1]*v1[0]];
  const out=[(p0[0]+p1[0])/2,(p0[1]+p1[1])/2,(p0[2]+p1[2])/2],P=(p,t)=>[p[0]+(v1[0]*Math.cos(t)+v2[0]*Math.sin(t))*r,p[1]+(v1[1]*Math.cos(t)+v2[1]*Math.sin(t))*r,p[2]+(v1[2]*Math.cos(t)+v2[2]*Math.sin(t))*r];
  for(let k=0;k<n;k++){const t0=k/n*6.2832,t1=(k+1)/n*6.2832,cc=MD.shade(c,0.88+MD.h(seed,k)*0.2);MD.f(a,P(p0,t0),P(p1,t0),P(p1,t1),cc,out);MD.f(a,P(p0,t0),P(p1,t1),P(p0,t1),cc,out)}
  const ce=MD.shade(c,1.18);for(const p of [p0,p1])for(let k=0;k<n;k++){const t0=k/n*6.2832,t1=(k+1)/n*6.2832;MD.f(a,p,P(p,t0),P(p,t1),ce,out)}},
 // A cone of n sides (pine tiers, roofs).
 cone(a,x,z,y0,y1,r,n,c,seed,snow){const out=[x,y0+(y1-y0)*0.3,z];const off=MD.h(seed,3)*6.28;const top=[x,y1,z];for(let k=0;k<n;k++){const t0=off+k/n*6.2832,t1=off+(k+1)/n*6.2832;const j0=1+(MD.h(seed,k)-0.5)*0.25,j1=1+(MD.h(seed,(k+1)%n)-0.5)*0.25;const b0=[x+Math.cos(t0)*r*j0,y0,z+Math.sin(t0)*r*j0],b1=[x+Math.cos(t1)*r*j1,y0,z+Math.sin(t1)*r*j1];MD.f(a,b0,b1,top,MD.shade(c,0.85+MD.h(seed,k+9)*0.25),out);if(snow){const s0=MD.mix(b0,top,0.3),s1=MD.mix(b1,top,0.3);MD.f(a,[s0[0],s0[1]+0.01,s0[2]],[s1[0],s1[1]+0.01,s1[2]],[top[0],top[1]+0.01,top[2]],[0.92,0.95,0.98,1],out)}}},
 PAL:{leaf:[[0.3,0.47,0.22],[0.36,0.52,0.24],[0.25,0.41,0.2],[0.4,0.53,0.26]],pine:[[0.14,0.3,0.2],[0.18,0.35,0.22]],bark:[0.4,0.27,0.15],rock:[[0.46,0.44,0.4],[0.52,0.48,0.42],[0.4,0.38,0.36]],cave:[[0.34,0.32,0.34],[0.4,0.37,0.38]],mesa:[[0.66,0.36,0.22],[0.74,0.45,0.27],[0.58,0.3,0.2],[0.8,0.55,0.34]],ash:[[0.2,0.19,0.2],[0.26,0.24,0.24],[0.16,0.15,0.17]],tundraRock:[[0.62,0.66,0.72],[0.7,0.74,0.8]],shroomRock:[[0.3,0.26,0.36],[0.36,0.3,0.42]]},
 tree(a,X,Y,Z,K,tx,ty){const st=K.state||'',seed=tx*31+ty*17;const r=MD.h(tx,ty,1),jx=(MD.h(tx,ty,2)-0.5)*0.22,jz=(MD.h(tx,ty,3)-0.5)*0.22;const x=X+jx,z=Z+jz;const big=0.85+r*0.35;
  if(K.biome==='mushroom'){const caps=[[0.72,0.28,0.55],[0.35,0.62,0.78],[0.85,0.55,0.25]],c=caps[Math.floor(r*3)%3];MD.prism(a,x,z,Y,Y+1.1*big,0.12,0.09,7,[0.86,0.82,0.74],seed);MD.blob(a,x,Y+1.15*big,z,0.62*big,0.22*big,0.62*big,c,seed,0.12);
   for(let k=0;k<5;k++){const ang=k*1.26+r;MD.blob(a,x+Math.cos(ang)*0.38*big,Y+1.08*big,z+Math.sin(ang)*0.38*big,0.05,0.04,0.05,[1,0.95,0.8],seed+k,0.1)}if(r>0.5)MD.blob(a,x+0.3,Y+0.25,z+0.1,0.18,0.1,0.18,c,seed+9,0.15);return}
  if(K.biome==='jungle'&&!st.includes('bamboo')){MD.prism(a,x,z,Y,Y+1.5*big,0.11,0.07,6,[0.36,0.25,0.14],seed);const dark=[0.12,0.4,0.14],mid=[0.18,0.5,0.18];
   MD.blob(a,x,Y+1.6*big,z,0.72*big,0.38*big,0.72*big,dark,seed);for(let k=0;k<4;k++){const ang=MD.h(seed,k+30)*6.28;MD.blob(a,x+Math.cos(ang)*0.42*big,Y+(1.38+MD.h(seed,k)*0.3)*big,z+Math.sin(ang)*0.42*big,0.38*big,0.24*big,0.38*big,MD.shade(mid,0.9+MD.h(seed,k+1)*0.2),seed+k*7)}
   for(let k=0;k<3;k++){const ang=MD.h(seed,k+50)*6.28,vx=x+Math.cos(ang)*0.5*big,vz=z+Math.sin(ang)*0.5*big;MD.prism(a,vx,vz,Y+0.5*big,Y+1.4*big,0.02,0.02,4,[0.2,0.45,0.15],seed+k+60)}return}
  if(st.includes('cactus')){const g=[0.32,0.55,0.26];MD.prism(a,x,z,Y,Y+1.1*big,0.13,0.11,7,g,seed);if(r>0.35){MD.prism(a,x+0.13,z,Y+0.45,Y+0.5,0.06,0.06,5,g,seed+1);MD.prism(a,x+0.22,z,Y+0.48,Y+0.85,0.06,0.05,5,g,seed+2)}if(r<0.7){MD.prism(a,x-0.13,z,Y+0.6,Y+0.65,0.06,0.06,5,g,seed+3);MD.prism(a,x-0.21,z,Y+0.62,Y+0.95,0.055,0.05,5,g,seed+4)}return}
  if(st.includes('bamboo')){for(let k=0;k<4;k++){const ax=x+(MD.h(seed,k)-0.5)*0.5,az=z+(MD.h(seed,k+4)-0.5)*0.5,hh=1.2+MD.h(seed,k+8)*0.9;MD.prism(a,ax,az,Y,Y+hh,0.04,0.035,5,[0.5,0.62,0.28],seed+k,(MD.h(seed,k+12)-0.5)*0.15);MD.blob(a,ax,Y+hh,az,0.18,0.08,0.18,[0.34,0.58,0.24],seed+k+20,0.4)}return}
  const pine=st.includes('snow')||st.includes('pine')||(K.kind==='tree'&&r>0.62&&!st.includes('dead'));const snow=st.includes('snow');
  MD.prism(a,x,z,Y,Y+(pine?0.45:0.7)*big,0.1,0.07,6,MD.PAL.bark,seed);
  if(st.includes('dead')){MD.prism(a,x,z,Y+0.6,Y+1.2,0.06,0.03,5,MD.PAL.bark,seed+1,0.15);return}
  if(pine){const c=MD.PAL.pine[Math.floor(r*2)%2];const tiers=r>0.8?4:3;for(let t=0;t<tiers;t++){const y0=Y+0.4*big+t*0.42*big,rad=(0.46-t*0.1)*big;MD.cone(a,x,z,y0,y0+0.72*big,rad,7,c,seed+t*5,snow)}return}
  const c=MD.PAL.leaf[Math.floor(r*4)%4];const n=2+Math.floor(MD.h(tx,ty,4)*2);
  MD.blob(a,x,Y+1.0*big,z,0.52*big,0.42*big,0.52*big,c,seed);
  for(let k=0;k<n;k++){const ang=MD.h(seed,k+30)*6.28;MD.blob(a,x+Math.cos(ang)*0.28*big,Y+(0.82+MD.h(seed,k+40)*0.35)*big,z+Math.sin(ang)*0.28*big,0.32*big,0.28*big,0.32*big,MD.shade(c,0.92+MD.h(seed,k)*0.16),seed+k*11)}},
 // Trees stand well above the walls and the units (a unit is about 1 high): oaks about 4.5, pines about 6, each kind
 // modelled at its own height (MD.bigTree). Bamboo, cactus and giant mushrooms keep the small model stretched 1.9x up
 // and 1.3x across (v3cane copies the bamboo). Every tree vertex is marked (colour alpha 0.97) so the shader can thin
 // trees out over your units and right in front of the camera.
 tallTree(a,X,Y,Z,K,tx,ty){const s0=a.length,kind=MD.treeKind(K,tx,ty);if(kind)MD.bigTree(a,X,Y,Z,K,tx,ty,kind);
  else{MD.tree(a,X,Y,Z,K,tx,ty);const sy=1.9,sw=1.3;for(let v=s0;v<a.length;v+=12){a[v]=X+(a[v]-X)*sw;a[v+1]=Y+(a[v+1]-Y)*sy;a[v+2]=Z+(a[v+2]-Z)*sw;let nx=a[v+3]/sw,ny=a[v+4]/sy,nz=a[v+5]/sw;const l=Math.hypot(nx,ny,nz)||1;a[v+3]=nx/l;a[v+4]=ny/l;a[v+5]=nz/l}}
  for(let v=s0+11;v<a.length;v+=12)a[v]=0.97},
 // Which full-size tree a tile grows: the sprite's own kind where it has one, else a steady mix by place.
 treeKind(K,tx,ty){const st=K.state||'',r=MD.h(tx,ty,1),w=MD.h(tx,ty,13);if(K.biome==='mushroom'||st.includes('bamboo')||st.includes('cactus'))return '';
  if(st.includes('dead')||K.biome==='ashlands')return 'dead';if(st==='snowtree')return 'bare';if(st.includes('pine'))return 'pine';if(st.includes('snow')||K.biome==='tundra')return w<0.25?'bare':'pine';
  if(K.biome==='jungle')return 'jungle';return r>0.62?'pine':r>0.47?'birch':'oak'},
 // How tall it stands (clicks on the crown pick its tile).
 treeTop(K,tx,ty){const k=MD.treeKind(K,tx,ty);return ({oak:4.4,pine:6,birch:4.5,jungle:5.1,dead:3.4,bare:3.6}[k]||2.9)*(k?0.84+MD.h(tx,ty,5)*0.34:1)},
 // A tapered limb of n sides from p0 (radius r0) to p1 (r1), capped at a thick end: trunks, branches, roots, vines.
 limb(a,p0,p1,r0,r1,n,c,seed){const d=[p1[0]-p0[0],p1[1]-p0[1],p1[2]-p0[2]],L=Math.hypot(...d)||1,u=d.map(v=>v/L),ref=Math.abs(u[1])<0.9?[0,1,0]:[1,0,0];
  let v1=[u[1]*ref[2]-u[2]*ref[1],u[2]*ref[0]-u[0]*ref[2],u[0]*ref[1]-u[1]*ref[0]];const l1=Math.hypot(...v1);v1=v1.map(q=>q/l1);const v2=[u[1]*v1[2]-u[2]*v1[1],u[2]*v1[0]-u[0]*v1[2],u[0]*v1[1]-u[1]*v1[0]];
  const off=MD.h(seed,7)*6.2832,P=(p,r,t)=>{const cs=Math.cos(t)*r,sn=Math.sin(t)*r;return [p[0]+v1[0]*cs+v2[0]*sn,p[1]+v1[1]*cs+v2[1]*sn,p[2]+v1[2]*cs+v2[2]*sn]},out=[(p0[0]+p1[0])/2,(p0[1]+p1[1])/2,(p0[2]+p1[2])/2];
  for(let k=0;k<n;k++){const t0=off+k/n*6.2832,t1=off+(k+1)/n*6.2832,cc=MD.shade(c,0.88+MD.h(seed,k)*0.2),a0=P(p0,r0,t0),a1=P(p0,r0,t1),b0=P(p1,r1,t0),b1=P(p1,r1,t1);MD.f(a,a0,b0,b1,cc,out);MD.f(a,a0,b1,a1,cc,out);if(r1>0.04)MD.f(a,p1,b0,b1,MD.shade(c,1.08),out)}},
 // Roots flaring from a trunk's foot into the ground.
 roots(a,x,z,Y,r,n,len,c,seed,rot){for(let k=0;k<n;k++){const an=rot+(k+MD.h(seed,k+40)*0.5)/n*6.2832,cs=Math.cos(an),sn=Math.sin(an),l=len*(0.75+MD.h(seed,k+45)*0.5);MD.limb(a,[x+cs*r*0.45,Y+len*0.55,z+sn*r*0.45],[x+cs*(r+l),Y-0.04,z+sn*(r+l)],r*0.55,r*0.12,3,MD.shade(c,0.92),seed+k+50)}},
 // A pine tier: a star of drooping branch tips round a cone (closed underneath if asked); snow on its upper part when cold.
 skirt(a,x,z,y0,y1,r,n,c,seed,snow,under){const off=MD.h(seed,3)*6.2832,top=[x,y1,z],hub=[x,y0+(y1-y0)*0.28,z],pts=[],m=2*n;
  for(let k=0;k<m;k++){const t=off+k/m*6.2832,o=k%2===0,rr=r*(o?1+(MD.h(seed,k)-0.5)*0.22:0.6),yy=y0+(o?-0.1:0.1)*r;pts.push([x+Math.cos(t)*rr,yy,z+Math.sin(t)*rr])}
  for(let k=0;k<m;k++){const p0=pts[k],p1=pts[(k+1)%m];MD.f(a,p0,p1,top,MD.shade(c,0.84+MD.h(seed,k+9)*0.26),hub);if(under)MD.f(a,p1,p0,hub,MD.shade(c,0.6),top)}
  if(snow){const sp=pts.map(p=>[x+(p[0]-x)*0.72,y0+(y1-y0)*0.3+(p[1]-y0)*0.7+0.03,z+(p[2]-z)*0.72]),st=[x,y1+0.03,z];for(let k=0;k<m;k++)MD.f(a,sp[k],sp[(k+1)%m],st,[0.92,0.95,0.98,1],hub)}},
 // The full-size trees. Size (0.84-1.18), turn and a lean of a few degrees vary per tile; the oak keeps the sprite's
 // broad round crown with its red-brown flecks (apples on a good tree), the winter tree its spread of bare branches.
 bigTree(a,X,Y,Z,K,tx,ty,kind){const s0=a.length,st=K.state||'',seed=tx*31+ty*17,x=X+(MD.h(tx,ty,2)-0.5)*0.22,z=Z+(MD.h(tx,ty,3)-0.5)*0.22,s=0.84+MD.h(tx,ty,5)*0.34,rot=MD.h(tx,ty,4)*6.2832;
  const J=(k,m)=>(MD.h(seed,k)-0.5)*m*s,lerp=(p,q,t)=>[p[0]+(q[0]-p[0])*t,p[1]+(q[1]-p[1])*t,p[2]+(q[2]-p[2])*t],B=[x,Y-0.05,z],snow=st.includes('snow')||K.biome==='tundra';
  if(kind==='oak'){const bark=[0.36,0.25,0.15],leaf=MD.shade(MD.PAL.leaf[Math.floor(MD.h(tx,ty,9)*4)%4],1.12),k1=[x+J(61,0.14),Y+1.0*s,z+J(62,0.14)],k2=[x+J(63,0.22),Y+1.85*s,z+J(64,0.22)],cy=Y+2.85*s,fr=st==='goodtree';
   MD.roots(a,x,z,Y,0.2*s,5,0.38*s,bark,seed,rot);MD.limb(a,B,k1,0.21*s,0.17*s,6,bark,seed);MD.limb(a,k1,k2,0.17*s,0.12*s,6,bark,seed+1);
   // a big round crown: a core, a low ring of clumps on the branches, a smaller ring above and a cap
   MD.clump(a,k2[0],cy+0.3*s,k2[2],0.85*s,0.78*s,0.85*s,MD.shade(leaf,0.84),seed+200,0.2);
   const n=5+(MD.h(seed,65)<0.4?1:0);for(let k=0;k<n;k++){const an=rot+k/n*6.2832+(MD.h(seed,k+70)-0.5)*0.6,cs=Math.cos(an),sn=Math.sin(an),rr=(0.62+MD.h(seed,k+80)*0.2)*s,p=[k2[0]+cs*rr,cy-0.2*s+MD.h(seed,k+90)*0.3*s,k2[2]+sn*rr],rx=(0.54+MD.h(seed,k+110)*0.14)*s,ry=(0.46+MD.h(seed,k+120)*0.1)*s;
    MD.limb(a,lerp(k1,k2,0.55+MD.h(seed,k+95)*0.45),[k2[0]+cs*rr*0.8,p[1]-0.25*s,k2[2]+sn*rr*0.8],0.075*s,0.03*s,4,bark,seed+k+100);
    MD.clump(a,p[0],p[1],p[2],rx,ry,rx,MD.shade(leaf,0.86+MD.h(seed,k+140)*0.18),seed+k*13+300,0.26);
    // the sprite's red-brown flecks (apples on a good tree): twig ends and fruit showing through the leaves
    for(let f=0;f<(fr?2:1);f++){const e=(MD.h(seed,k*3+f+170)-0.3)*0.9,da=(MD.h(seed,k*3+f+180)-0.5)*1.2,ce=Math.cos(e);MD.gem(a,p[0]+Math.cos(an+da)*rx*ce,p[1]+Math.sin(e)*ry,p[2]+Math.sin(an+da)*rx*ce,0.08*s,fr?[0.78,0.16,0.1]:[0.42,0.2,0.12])}}
   const nu=3;for(let k=0;k<nu;k++){const an=rot+0.5+k/nu*6.2832,rr=(0.4+MD.h(seed,k+150)*0.12)*s;MD.clump(a,k2[0]+Math.cos(an)*rr,cy+(0.55+MD.h(seed,k+155)*0.15)*s,k2[2]+Math.sin(an)*rr,0.5*s,0.42*s,0.5*s,MD.shade(leaf,1.0+MD.h(seed,k+160)*0.12),seed+k*17+400,0.26)}
   MD.clump(a,k2[0]+J(171,0.2),cy+0.98*s,k2[2]+J(172,0.2),0.4*s,0.32*s,0.4*s,MD.shade(leaf,1.14),seed+450,0.26)}
  else if(kind==='pine'){const bark=[0.32,0.21,0.13],c=MD.shade(MD.PAL.pine[Math.floor(MD.h(tx,ty,9)*2)%2],0.92+MD.h(tx,ty,10)*0.16),n=5+(MD.h(seed,67)<0.5?1:0);
   MD.roots(a,x,z,Y,0.14*s,4,0.26*s,bark,seed,rot);MD.limb(a,B,[x,Y+3.5*s,z],0.15*s,0.06*s,6,bark,seed);
   for(let t=0;t<n;t++){const q=t/(n-1),y0=Y+(0.95+q*3.75)*s,y1=t===n-1?Y+6*s:y0+(1.45-0.1*t)*s;MD.skirt(a,x,z,y0,y1,(1.12-0.8*q)*s,7,MD.shade(c,0.94+0.04*t),seed+t*5,snow,t===0)}}
  else if(kind==='birch'){const bark=[0.87,0.85,0.8],dark=[0.17,0.15,0.14],leaf=MD.shade([0.5,0.63,0.27],0.92+MD.h(tx,ty,9)*0.14),k1=[x+J(61,0.2),Y+1.7*s,z+J(62,0.2)],k2=[x+J(63,0.32),Y+3.4*s,z+J(64,0.32)];
   // a slender pale trunk with a bend, ringed with dark marks (pieces of one limb share its sides, so no seams)
   const seg=(p,q,r0,r1,sd)=>{const cuts=[0,0.2,0.235,0.42,0.45,0.66,0.7,0.88,0.91,1];for(let k=0;k<cuts.length-1;k++)MD.limb(a,lerp(p,q,cuts[k]),lerp(p,q,cuts[k+1]),r0+(r1-r0)*cuts[k],r0+(r1-r0)*cuts[k+1],6,k%2?dark:bark,sd)};
   seg(B,k1,0.12*s,0.095*s,seed);seg(k1,k2,0.095*s,0.05*s,seed+1);
   for(let k=0;k<3;k++){const an=rot+k*2.1,f=lerp(k1,k2,0.2+k*0.25);MD.limb(a,f,[f[0]+Math.cos(an)*0.5*s,f[1]+0.55*s,f[2]+Math.sin(an)*0.5*s],0.04*s,0.015*s,4,[0.3,0.27,0.24],seed+k+80)}
   for(let k=0;k<6;k++){const q=k/5,an=rot+k*2.4,f=lerp(k1,k2,0.15+q*0.85),w=1-Math.abs(q-0.45),rr=(0.22+w*0.18)*s,rx=(0.36+w*0.2)*s;MD.clump(a,f[0]+Math.cos(an)*rr,f[1]+0.25*s,f[2]+Math.sin(an)*rr,rx,0.4*s,rx,MD.shade(leaf,0.88+q*0.18+MD.h(seed,k+140)*0.08),seed+k*13+300,0.26)}
   MD.clump(a,k2[0],k2[1]+0.55*s,k2[2],0.32*s,0.42*s,0.32*s,MD.shade(leaf,1.08),seed+390,0.24)}
  else if(kind==='dead'){const bark=K.biome==='ashlands'?[0.17,0.15,0.14]:[0.41,0.36,0.31],k1=[x+J(61,0.3),Y+1.2*s,z+J(62,0.3)],k2=[x+J(63,0.5),Y+2.3*s,z+J(64,0.5)];
   MD.roots(a,x,z,Y,0.18*s,4,0.36*s,bark,seed,rot);MD.limb(a,B,k1,0.19*s,0.14*s,6,bark,seed);MD.limb(a,k1,k2,0.14*s,0.06*s,6,bark,seed+1);
   const n=3+Math.floor(MD.h(seed,65)*2);for(let k=0;k<n;k++){const an=rot+k/n*6.2832+(MD.h(seed,k+70)-0.5)*0.9,cs=Math.cos(an),sn=Math.sin(an),f=lerp(k1,k2,0.1+MD.h(seed,k+75)*0.75),L=(0.75+MD.h(seed,k+76)*0.5)*s;
    const m=[f[0]+cs*L*0.45+J(k+77,0.2),f[1]+L*0.35,f[2]+sn*L*0.45+J(k+78,0.2)],e=[f[0]+cs*L*0.8,f[1]+L*0.75+J(k+79,0.3),f[2]+sn*L*0.8],tw=an+(MD.h(seed,k+81)<0.5?0.9:-0.9);
    MD.limb(a,f,m,0.065*s,0.045*s,4,bark,seed+k+100);MD.limb(a,m,e,0.045*s,0.012*s,4,bark,seed+k+110);MD.limb(a,m,[m[0]+Math.cos(tw)*0.35*s,m[1]+0.32*s,m[2]+Math.sin(tw)*0.35*s],0.028*s,0.008*s,4,bark,seed+k+120)}}
  else if(kind==='bare'){const bark=[0.36,0.25,0.15],wh=[0.93,0.95,0.98,1],k1=[x+J(61,0.14),Y+0.95*s,z+J(62,0.14)],k2=[x+J(63,0.2),Y+1.75*s,z+J(64,0.2)];
   MD.roots(a,x,z,Y,0.2*s,5,0.36*s,bark,seed,rot);MD.limb(a,B,k1,0.21*s,0.17*s,6,bark,seed);MD.limb(a,k1,k2,0.17*s,0.1*s,6,bark,seed+1);
   const n=6+Math.floor(MD.h(seed,65)*2);for(let k=0;k<n;k++){const an=rot+k/n*6.2832+(MD.h(seed,k+70)-0.5)*0.5,cs=Math.cos(an),sn=Math.sin(an),f=lerp(k1,k2,0.5+MD.h(seed,k+75)*0.5),L=(1.35+MD.h(seed,k+76)*0.45)*s;
    const m=[f[0]+cs*L*0.5,f[1]+L*0.42,f[2]+sn*L*0.5],e=[f[0]+cs*L,f[1]+L*0.85,f[2]+sn*L];MD.limb(a,f,m,0.095*s,0.06*s,4,bark,seed+k+100);MD.limb(a,m,e,0.06*s,0.015*s,4,bark,seed+k+110);
    for(let w=0;w<3;w++){const tw=an+(w-1)*0.75,b=lerp(m,e,0.15+0.3*w);MD.limb(a,b,[b[0]+Math.cos(tw)*0.5*s,b[1]+0.45*s,b[2]+Math.sin(tw)*0.5*s],0.032*s,0.006*s,4,bark,seed+k*3+w+120)}
    if(snow){MD.limb(a,[f[0],f[1]+0.04*s,f[2]],[m[0],m[1]+0.03*s,m[2]],0.08*s,0.05*s,4,wh,seed+k+100);MD.clump(a,m[0],m[1]+0.045*s,m[2],0.065*s,0.04*s,0.065*s,wh,seed+k+150,0.2)}}}
  else if(kind==='jungle'){const bark=[0.42,0.33,0.22],dark=[0.1,0.35,0.13],mid=[0.17,0.46,0.17],T=[x+J(63,0.25),Y+4.1*s,z+J(64,0.25)];
   // buttress roots: thin fins out from the foot
   for(let k=0;k<5;k++){const an=rot+k/5*6.2832+(MD.h(seed,k+40)-0.5)*0.5,cs=Math.cos(an),sn=Math.sin(an),px=-sn*0.03*s,pz=cs*0.03*s,b=[x+cs*0.1*s,Y-0.02,z+sn*0.1*s],e=[x+cs*0.65*s,Y-0.02,z+sn*0.65*s],t=[x+cs*0.12*s,Y+1.05*s,z+sn*0.12*s],c=MD.shade(bark,0.88+MD.h(seed,k+45)*0.16);
    for(const g of [1,-1]){const o=[(b[0]+e[0]+t[0])/3-px*g,(b[1]+e[1]+t[1])/3,(b[2]+e[2]+t[2])/3-pz*g];MD.f(a,[b[0]+px*g,b[1],b[2]+pz*g],[e[0]+px*g,e[1],e[2]+pz*g],[t[0]+px*g,t[1],t[2]+pz*g],c,o)}}
   MD.limb(a,B,T,0.2*s,0.1*s,6,bark,seed);MD.clump(a,x+(T[0]-x)*0.55+0.18*s,Y+2.3*s,z+(T[2]-z)*0.55,0.2*s,0.16*s,0.2*s,mid,seed+220,0.25);
   for(let k=0;k<5;k++){const an=rot+k/5*6.2832+(MD.h(seed,k+70)-0.5)*0.5,cs=Math.cos(an),sn=Math.sin(an),rr=(0.8+MD.h(seed,k+80)*0.25)*s,p=[T[0]+cs*rr,T[1]-0.05*s+J(k+90,0.3),T[2]+sn*rr],rx=(0.58+MD.h(seed,k+110)*0.15)*s;
    MD.limb(a,lerp(B,T,0.85),[p[0]-cs*0.2*s,p[1]-0.1*s,p[2]-sn*0.2*s],0.07*s,0.035*s,4,bark,seed+k+100);MD.clump(a,p[0],p[1],p[2],rx,0.32*s,rx,MD.shade(mid,0.85+MD.h(seed,k+140)*0.25),seed+k*13+300,0.22);
    // vines hanging off the canopy's edge
    if(k<4){const v=[p[0]+cs*0.3*s,p[1]-0.2*s,p[2]+sn*0.3*s];MD.limb(a,v,[v[0]+J(k+150,0.15),v[1]-(1.0+MD.h(seed,k+151)*0.9)*s,v[2]+J(k+152,0.15)],0.022*s,0.012*s,4,[0.22,0.43,0.16],seed+k+160)}}
   MD.clump(a,T[0],T[1]+0.3*s,T[2],1.0*s,0.42*s,1.0*s,dark,seed+200,0.2);MD.clump(a,T[0]+J(201,0.4),T[1]+0.62*s,T[2]+J(202,0.4),0.55*s,0.3*s,0.55*s,MD.shade(mid,1.1),seed+210,0.22)}
  // the lean: a shear about the foot
  const la=MD.h(tx,ty,6)*6.2832,ln=(kind==='pine'?0.012:0.022)+MD.h(tx,ty,7)*0.045,lx=Math.cos(la)*ln,lz=Math.sin(la)*ln;for(let v=s0;v<a.length;v+=12){const up=Math.max(0,a[v+1]-Y);a[v]+=up*lx;a[v+2]+=up*lz}},
 // One colour per ground corner, shared by every tile that touches it (no seams).
 groundCorner(T,kindAt,ci,cj,own,liquid){const q=liquid?own:(MD.ground(T,kindAt,ci,cj)||own);const wx=T.x0+ci,wy=T.y0+cj;const big=liquid?0.5:MD.vn(wx,wy,7,3),v=0.86+big*0.2+MD.h(wx,wy,11)*0.08,warm=liquid?0:(MD.vn(wx,wy,11,4)-0.5)*0.08;return [q[0]*v+warm,q[1]*v+warm*0.5,q[2]*v,1]},
 // Ground corner colour: the average of the four tiles around the corner, so colours blend (land only: water's colour
 // in a bank's corners turned its grass to earth, a band of cobbles along every shore).
 ground(T,kindAt,i,j){let r=0,g=0,b=0,n=0;for(const [di,dj] of [[0,0],[-1,0],[0,-1],[-1,-1]]){const K=kindAt(i+di,j+dj);if(!K||K.kind==='wall'||K.kind==='block'||K.kind==='void'||K.kind==='water'||K.kind==='lava')continue;const c=MD.groundColor(K);r+=c[0];g+=c[1];b+=c[2];n++}return n?[r/n,g/n,b/n]:null},
 groundColor(K){const st=K.state||'';if(K.hoard)return [0.5,0.37,0.12];if(K.road)return K.road==='stone'?[0.4,0.38,0.35]:[0.47,0.37,0.24];if(K.biome&&K.kind!=='water'&&K.kind!=='lava'){const B={jungle:[0.16,0.33,0.12],mesa:[0.78,0.47,0.28],tundra:[0.74,0.8,0.86],ashlands:[0.22,0.2,0.2],mushroom:[0.27,0.2,0.33]}[K.biome];if(B)return B}if(K.kind==='tree')return [0.31,0.41,0.22];if(K.kind==='water')return [0.15,0.24,0.36];if(K.kind==='lava')return [0.85,0.35,0.1];if(st.includes('snow'))return [0.86,0.89,0.92];if(st.includes('desert')||st.includes('sand'))return [0.82,0.72,0.48];if(st.includes('cave')||st.includes('cellar'))return [0.36,0.33,0.32];if(st.includes('farm'))return [0.42,0.3,0.18];if(st.includes('marsh')||st.includes('swamp'))return [0.3,0.38,0.24];if(st.includes('grass'))return [0.36,0.45,0.25];const c=hexrgb(K.color,1);return [c[0]*0.85,c[1]*0.85,c[2]*0.85]}
};

