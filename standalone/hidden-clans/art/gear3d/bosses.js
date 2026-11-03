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
