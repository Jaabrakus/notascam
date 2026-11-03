// ===== Combat feel (world-look). A blow or shot landing (v3hits: when its number shows): the struck unit's picture
// flashes for a moment, and a short burst flies off it, its colour by what was hit (blood, bone chips for skeletons,
// dark ichor for zombies), with a spark star; a parry or block gives sparks only. A unit leaving the view fades out
// (a killed one darkens and sinks) instead of vanishing. Audio can sound the same moments: rmSfx.at('impact'|'fall').
const V3BLOOD={skeleton:[0.86,0.83,0.74],zombie:[0.27,0.3,0.14],vampire:[0.42,0.02,0.05],frogman:[0.36,0.5,0.16],lizardman:[0.5,0.08,0.05]};
function v3impact(h,now){const t=V3.things.find(o=>o.x===h.x&&o.y===h.y&&!o.ly&&(o.kind==='mine'||o.kind==='npc'||o.kind==='player'||o.kind==='animal'));if(!t&&h.k!=='wall'&&h.k!=='wreck')return;
 const spark=h.k==='parry'||h.k==='block'||h.k==='guard',col=t&&t.beast?[0.5,0.05,0.04]:(t&&V3BLOOD[t.model])||[0.55,0.05,0.04],big=h.k==='kill'||h.n>=30||h.k==='crush'||h.k==='cleave';
 V3.fx=V3.fx||[];V3.fx.push({type:'puff',x:h.x,y:h.y,ax:h.ax,ay:h.ay,t:now,col,spark,big,kill:h.k==='kill',seed:(h.x*31+h.y*17+Math.floor(now))%9973,wall:h.k==='wall'||h.k==='wreck'});
 try{window.rmSfx&&rmSfx.at('impact',h.x,h.y,{k:h.k,w:h.w,spark})}catch(e){}}
function v3puff(a,gw,f,now,sb){const age=(now-f.t)/1000,life=f.big?0.6:0.45;if(age>life)return false;if(f.wall)return false;const [X,,Z]=v3world({dx:f.x,dy:f.y}),[AX,,AZ]=v3world({dx:f.ax,dy:f.ay}),Y0=v3groundAt(f.x,f.y),Y=Y0+0.62;
 let ux=X-AX,uz=Z-AZ;const l=Math.hypot(ux,uz);if(l<0.01){ux=Math.sin(V3.yaw);uz=Math.cos(V3.yaw)}else{ux/=l;uz/=l}const p=age/life,g=9.8;
 // the star: four short rays of added light at the point of the blow, gone in a tenth of a second or so
 if(age<0.13){const k=1-age/0.13,r=(f.spark?0.42:0.3)*(0.6+0.4*k),c=f.spark?[1*k,0.85*k,0.45*k,1]:[0.95*k,0.85*k,0.75*k,1],cx=X-ux*0.28,cz=Z-uz*0.28,cy=Y+0.05,R=[Math.cos(V3.yaw),0,-Math.sin(V3.yaw)];
  for(let q=0;q<4;q++){const an=q*0.785+f.seed,ca=Math.cos(an),sa=Math.sin(an),dx=R[0]*ca*r,dz=R[2]*ca*r,dy=sa*r,wx=-R[0]*sa*0.03,wz=-R[2]*sa*0.03,wy=ca*0.03;quad(gw,[cx-dx-wx,cy-dy-wy,cz-dz-wz],[cx+dx-wx,cy+dy-wy,cz+dz-wz],[cx+dx+wx,cy+dy+wy,cz+dz+wz],[cx-dx+wx,cy-dy+wy,cz-dz+wz],QN0,c)}}
 // sparks off a parried or blocked blow: bright flecks thrown back toward the striker
 if(f.spark){for(let q=0;q<7;q++){const an=(MD.h(f.seed,q,1)-0.5)*2.2,sp=2+MD.h(f.seed,q,2)*2.2,up=1+MD.h(f.seed,q,3)*1.6,dx=-ux*Math.cos(an)+uz*Math.sin(an),dz=-uz*Math.cos(an)-ux*Math.sin(an),x=X-ux*0.3+dx*sp*age,z=Z-uz*0.3+dz*sp*age,y=Y+up*age-0.5*g*age*age,k=Math.max(0,1-p*1.4);if(k<=0||y<Y0)continue;
   MD.blob(gw,x,y,z,0.025,0.025,0.025,[1.4*k,1.1*k,0.5*k,1],q,0.05)}return true}
 // droplets (or chips) thrown off the far side, falling; a big blow throws more, a kill leaves a splash on the ground
 const n=f.big?8:5;for(let q=0;q<n;q++){const an=(MD.h(f.seed,q,4)-0.5)*2.4,sp=0.8+MD.h(f.seed,q,5)*1.6,up=0.6+MD.h(f.seed,q,6)*1.8,dx=ux*Math.cos(an)-uz*Math.sin(an),dz=uz*Math.cos(an)+ux*Math.sin(an);let y=Y+up*age-0.5*g*age*age;const x=X+dx*sp*age,z=Z+dz*sp*age;if(y<Y0+0.03)y=Y0+0.03;
  const r=(0.034+MD.h(f.seed,q,7)*0.03)*(1-p*0.5),s=0.8+MD.h(f.seed,q,8)*0.4,c=f.col,rx=Math.cos(V3.yaw)*r,rz=-Math.sin(V3.yaw)*r;
  quad(sb,[x-rx,y-r,z-rz],[x+rx,y-r,z+rz],[x+rx,y+r,z+rz],[x-rx,y+r,z-rz],QN0,[Math.min(1,c[0]*s),Math.min(1,c[1]*s),Math.min(1,c[2]*s),1])}
 if(f.kill||f.big){const s=Math.min(1,age/0.18)*(f.kill?0.36:0.22),al=p>0.6?1-(p-0.6)/0.4:1,cx=X+ux*0.15,cz=Z+uz*0.15,y=Y0+0.014,c=MD.shade(f.col,0.62);qb(sb,cx-s,y,cz+s*0.8,cx+s,y,cz+s*0.8,cx+s,y,cz-s*0.8,cx-s,y,cz-s*0.8,0,0,0,[c[0],c[1],c[2],0.85*al])}
 return true}
// Footsteps on loose ground (sand, desert, dirt tracks, tilled earth, snow) kick up a small soft puff of it.
function v3stepDust(x,y){const tx=Math.round(x),ty=Math.round(y),K=v3kindAt(tx,ty);if(!K||K.kind!=='floor'&&K.kind!=='farm')return;const st=String(K.state||''),snow=st.includes('snow');
 if(!(snow||st.includes('desert')||st.includes('sand')||st.includes('dirt')||st.includes('farm')||K.kind==='farm'||K.road==='dirt'||K.biome==='mesa'||K.biome==='ashlands'))return;if((V3.fx||[]).length>160)return;
 const c=snow?[0.95,0.97,1]:MD.groundColor(K);(V3.fx||(V3.fx=[])).push({type:'dust',x,y,t:performance.now(),col:[Math.min(1,c[0]*0.7+0.36),Math.min(1,c[1]*0.7+0.33),Math.min(1,c[2]*0.7+0.3)],seed:(tx*31+ty*17+((performance.now()/97)|0))%997})}
function v3dust(sb,f,now){const age=(now-f.t)/1000,life=0.8;if(age>life)return false;const p=age/life,[X,,Z]=v3world({dx:f.x,dy:f.y}),Y=v3groundAt(Math.round(f.x),Math.round(f.y)),cp=Math.cos(V3.pitch),sp=Math.sin(V3.pitch),rx=Math.cos(V3.yaw),rz=-Math.sin(V3.yaw),ux=-Math.sin(V3.yaw)*sp,uy=cp,uz=-Math.cos(V3.yaw)*sp;
 for(let k=0;k<4;k++){const an=MD.h(f.seed,k,1)*6.283,d=0.06+p*(0.2+MD.h(f.seed,k,2)*0.14),x=X+Math.cos(an)*d,z=Z+Math.sin(an)*d,y=Y+0.1+p*0.24,r=0.13+p*0.22,al=0.8*Math.pow(1-p,1.6)*Math.min(1,p*8);
  quad(sb,[x-rx*r-ux*r,y-uy*r,z-rz*r-uz*r],[x+rx*r-ux*r,y-uy*r,z+rz*r-uz*r],[x+rx*r+ux*r,y+uy*r,z+rz*r+uz*r],[x-rx*r+ux*r,y+uy*r,z-rz*r+uz*r],QN0,[f.col[0],f.col[1],f.col[2],al])}return true}
// a unit leaving the view: its last picture, drawn by v3combatFx as it fades
function v3ghost(kd){if(!kd||!kd.gtk||!V3.on)return;const key=Math.round(kd.tx)+','+Math.round(kd.ty),ka=V3.kills&&V3.kills.get(key),dead=ka!=null&&performance.now()-ka<2500;
 (V3.ghosts||(V3.ghosts=[])).push({tk:kd.gtk,u0:kd.gu0,u1:kd.gu1,hw:kd.ghw,sh:kd.gsh,y:kd.gy,x:kd.dx,z:-kd.dy,t0:performance.now(),dead});if(V3.ghosts.length>80)V3.ghosts.shift();
 if(dead)try{window.rmSfx&&rmSfx.at('fall',Math.round(kd.tx),Math.round(kd.ty))}catch(e){}}
function v3combatFx(right,ts,flashG){const gl=V3.gl,L=V3.loc,now=performance.now();
 if(V3.impacts&&V3.impacts.length)V3.impacts=V3.impacts.filter(h=>{if(h.t>now)return true;if(now-h.t<500)v3impact(h,now);return false});
 if(V3.flash&&V3.flash.size>40)for(const [k,t] of V3.flash)if(now-t>1000)V3.flash.delete(k);if(V3.kills&&V3.kills.size>40)for(const [k,t] of V3.kills)if(now-t>3000)V3.kills.delete(k);
 // the flash: the struck picture again in warm white over itself
 let any=false;for(const a of flashG.values())if(a.length){any=true;break}
 if(any){gl.enable(gl.BLEND);gl.blendFunc(gl.SRC_ALPHA,gl.ONE_MINUS_SRC_ALPHA);gl.depthMask(false);gl.depthFunc(gl.LEQUAL);gl.uniform4f(L.tint,1,0.97,0.9,0.62);
  for(const [k,a] of flashG){const e=a.length?v3tex(k):null;if(!e||!e.ok)continue;gl.bindBuffer(gl.ARRAY_BUFFER,V3.dyn);v3up(a);v3draw(V3.dyn,a.length/12,e)}gl.uniform4f(L.tint,0,0,0,0);gl.depthFunc(gl.LESS);gl.depthMask(true);gl.disable(gl.BLEND)}
 // fading pictures of units that left; a killed one darkens, slumps and sinks
 const G=V3.ghosts;if(!G||!G.length)return;const by=V3.ghostG||(V3.ghostG=new Map());for(const a of by.values())a.length=0;
 V3.ghosts=G.filter(g=>{const dur=g.dead?0.9:0.35,p=(now-g.t0)/1000/dur;if(p>=1)return false;const al=g.dead?1-p*p:1-p,sink=g.dead?p*p*0.45:0,hgt=g.sh*(g.dead?1-0.45*p:1),y=g.y-sink,c=g.dead?[1-0.45*p,0.82-0.5*p,0.8-0.5*p,al]:[1,1,1,al];
  let a=by.get(g.tk);if(!a){a=new VA();by.set(g.tk,a)}quad(a,[g.x-right[0]*g.hw,y,g.z-right[2]*g.hw],[g.x+right[0]*g.hw,y,g.z+right[2]*g.hw],[g.x+right[0]*g.hw,y+hgt,g.z+right[2]*g.hw],[g.x-right[0]*g.hw,y+hgt,g.z-right[2]*g.hw],QN0,c,[g.u0,1,g.u1,1,g.u1,0,g.u0,0]);return true});
 gl.enable(gl.BLEND);gl.blendFunc(gl.SRC_ALPHA,gl.ONE_MINUS_SRC_ALPHA);gl.depthMask(false);gl.uniform1f(L.soft,1);
 for(const [k,a] of by){const e=a.length?v3tex(k):null;if(!e||!e.ok)continue;gl.bindBuffer(gl.ARRAY_BUFFER,V3.dyn);v3up(a);v3draw(V3.dyn,a.length/12,e)}
 gl.uniform1f(L.soft,0);gl.depthMask(true);gl.disable(gl.BLEND)}
// A unit in water stands lower (Swim.dm): to the chest in deep water, swum; a little in shallows and fords, waded.
function v3swimY(x,y){const K=v3kindAt(x,y);return K&&K.kind==='water'&&!K.lift?(K.deep?-0.36:-0.08):0}
function v3kindAt(x,y){const T=V3.terrain;if(!T)return null;const i=x-T.x0,j=y-T.y0;if(i<0||j<0||i>=T.w||j>=T.h)return null;const c=T.tiles[j*T.w+i];return c?T.kinds[c-1]:null}
// Build-mode ghost: tiles a drag covers (walls: outline, floors: filled).
function v3paintTiles(a,b,kind){const out=[];const x0=Math.min(a.x,b.x),x1=Math.max(a.x,b.x),y0=Math.min(a.y,b.y),y1=Math.max(a.y,b.y);if((x1-x0+1)*(y1-y0+1)>600)return out;for(let y=y0;y<=y1;y++)for(let x=x0;x<=x1;x++){if(kind==='wall'&&x!==x0&&x!==x1&&y!==y0&&y!==y1)continue;out.push({x,y})}return out}
function v3ghostOk(t,kind){const K=v3kindAt(t.x,t.y);if(!K)return 'bad';if(kind==='dig')return K.kind==='wall'?'ok':'bad';if(kind==='bridge')return ['water','lava','hole','void'].includes(K.kind)||String(K.state||'').includes('chasm')?(V3.hasSel?'ok':'warn'):'bad';if(['wall','built','tree','water','lava','block','void','hole'].includes(K.kind))return 'bad';if(kind==='floor'&&K.kind==='bfloor')return 'bad';return V3.hasSel?'ok':'warn'}
// GPU unit drawing (2026-10-24, the user: "3D world look: GPU unit drawing"): a unit's picture, cast and contact shadows and
// ring are one 12-number record each (a VA row: i0, i1, the colour), and the vertex shader builds the corners (inst: 1 a
// picture, 2 a cast shadow, 3 a flat quad, 4 a ring's arc), so a frame no longer builds and uploads six vertices for each.
// V3.iU: this frame's camera right and lean, and the cast shadows' directions.
// A unit's records as they were written this frame (its picture, silhouette, shadows, rings, bar), with what they were
// worked out from, so an unchanged unit is given them again (v3rcEmit) instead of worked out every frame.
// Kept in the unit's own buffer (kd.rc.F: picture, silhouette, cast and contact shadows, up to four ring records), so
// keeping thousands of them makes no garbage.
function v3rcMake(t,kd,ep,tk,w,IG,sil,castG,contact,rings,rs0,BL,bs0,key){key=key||'rc';const R=kd[key]||(kd[key]={F:new Float32Array(96),bar:[]}),F=R.F;let o=0;const put=(a,from,n)=>{for(let i=0;i<n;i++)F[o+i]=a.f[from+i];o+=n};
 R.vI=null;R.ep=ep;R.ob=t;R.og=V3.sceneGen;R.fb=tk!==((t.texd&&t.texd[v3face(t)])||t.tex||'');R.t0=kd.t0;R.x=t.x;R.y=t.y;R.dir=t.dir;R.sel=t.selected;R.hp=t.hp;R.act=t.act;R.ly=t.ly;R.dx=t.dx;R.dy=t.dy;R.kind=t.kind;R.tex=t.tex;R.tint=t.tint;R.color=t.color;R.peace=t.peace;R.ally=t.ally;R.war=t.war;R.fly=t.fly;R.sc=t.sc;R.iw=t.iw;R.ih=t.ih;R.px=t.px;R.py=t.py;R.el=t.el;R.wf=t.wf;R.tk=tk;R.top=t.top3d;
 const pa=IG.get(tk);put(pa,pa.length-12,12);R.ns=0;if(t.kind==='mine'&&!t.g3doll){const sa=sil.get(tk);put(sa,sa.length-12,12);R.ns=12}R.nc=0;if(w&1){const ca=castG.get(tk);put(ca,ca.length-12,12);R.nc=12}
 R.nt=0;if(w&2){put(contact,contact.length-12,12);R.nt=12}const nr=rings.length-rs0;if(nr>F.length-o){R.ep=null;return R}R.nr=nr;put(rings,rs0,nr);   /* more rings than it holds: not kept */R.bar.length=0;for(let i=bs0;i<BL.length;i++)R.bar.push(BL[i]);return R}
// A unit the picture path draws (none of the sorts the frame's loop sends elsewhere), so its kept records can be given again
// before the sorting. Fields the server sets: worked out once for each thing object, that is once a scene.
function v3plain(t){return t.vap==null&&!t.flame&&!t.cauldron&&!t.rune&&!t.crop&&!t.banner&&!t.siege&&!t.food&&t.vomit==null&&!t.clinic&&!t.optable&&!t.tavern&&!t.graveyard&&!t.grave&&!t.trace&&!t.m3&&!t.fishspot&&!t.stall&&!t.mouth&&!t.hellgate&&!t.vent&&!t.caveexit&&t.cap==null&&t.ko==null&&t.kind!=='decal'&&t.kind!=='body'&&!t.beast?1:0}   /* a unit with a 3D model is drawn as a model only when models are on (then it has no kept records) */
// A walking unit's kept step (kd.wc, v3rcMake): its records moved to where the whole path would draw them this frame, and
// given (false once the step is over: the whole path then). The same sums as the frame's loop: the glide's position, the
// step's bob and sway, the height eased to the tile's, the walk frame (two a tile); shadows, rings and the bar follow.
function v3walkEmit(t,kd,W,ts,IG,sil,castG,contact,rings,BL,iadd){const nowS=ts/1000;if(!(nowS-kd.t0<kd.dur&&(kd.tx!==kd.fx||kd.ty!==kd.fy)))return false;
 const fa=V3.flash&&V3.flash.size?V3.flash.get(t.x+','+t.y):null;if(fa!=null&&ts<fa+120)return false;
 const X=t.dx+(t.px||0)+((t.iw||1)-1)/2,Z=-t.dy-(t.py||0),ph=(nowS-kd.t0)/Math.max(0.12,kd.dur),bob=Math.abs(Math.sin(ph*Math.PI*2))*0.07,sway=Math.sin(ph*Math.PI*2)*0.05;
 const gf=kd.dur>0&&kd.t0!=null?Math.min(1,Math.max(0,(nowS-kd.t0)/kd.dur)):1;kd.base=kd.bFrom+(W.bto-kd.bFrom)*gf;const y0=kd.base+bob,nf=W.nf;
 let fi=0;if(nf>=2){const seq=nf>=3?[1,0,2,0]:[1,0];fi=seq[Math.floor(((kd.n||0)+ph)*2)%seq.length]}const u0=fi/nf+0.0005,u1=(fi+1)/nf-0.0005,F=W.F;
 F[0]=X;F[1]=y0;F[2]=Z;F[5]=sway;F[6]=u0;F[7]=u1;let o=12;if(W.ns){F[o]=X;F[o+1]=y0;F[o+2]=Z;F[o+5]=sway;F[o+6]=u0;F[o+7]=u1;o+=12}
 if(W.nc){F[o]=X;F[o+2]=Z;F[o+6]=u0;F[o+7]=u1;o+=12}if(W.nt){F[o]=X;F[o+2]=Z;o+=12}for(let i=0;i<W.nr;i+=12){F[o+i]=X;F[o+i+2]=Z}
 if(W.g3)g3shift(W,X-W.bx,y0-W.by,Z-W.bz);const B=W.bar;if(B.length){B[0]+=X-W.bx;B[1]+=y0-W.by;B[2]+=Z-W.bz}t.top3d=W.top+y0-W.by;W.bx=X;W.bz=Z;W.by=y0;W.top=t.top3d;kd.gu0=u0;kd.gu1=u1;kd.gy=y0;
 v3rcEmit(W,IG,sil,castG,contact,rings,BL,iadd);
 // its 3D gear made again for this frame's walk frame and swing (gear3d.js g3swing), with the size and the camera's axes
 // its whole drawing last gave it: slid along with the rest it stayed where the hand was as the step began, off the hand
 // as the walk frames changed, and never swung (the owner, 10-27: "how come the weapons does not sway or wiggle", "fix
 // the weapon placement for all the angles"). Only the gear: the unit's picture and shadows stay its kept records.
 if(W.g3){const L0=t.g3last||kd.g3last;if(L0&&L0.R&&window.v3gear3d){G3.rec.length=0;v3gear3d(t,kd,v3face(t),fi,X,y0,Z,L0.hw,L0.sh,sway,L0.R,L0.L,null,nowS)}else g3put(W)}return true}
// The camera's view as six planes (x, y, z, d; a point is inside each where x X + y Y + z Z + d >= 0), from its matrix.
function v3planes(m,P){P=P||new Float64Array(24);const r=(k,a,b,c,d)=>{const l=Math.hypot(a,b,c)||1;P[k]=a/l;P[k+1]=b/l;P[k+2]=c/l;P[k+3]=d/l};
 r(0,m[3]+m[0],m[7]+m[4],m[11]+m[8],m[15]+m[12]);r(4,m[3]-m[0],m[7]-m[4],m[11]-m[8],m[15]-m[12]);r(8,m[3]+m[1],m[7]+m[5],m[11]+m[9],m[15]+m[13]);
 r(12,m[3]-m[1],m[7]-m[5],m[11]-m[9],m[15]-m[13]);r(16,m[3]+m[2],m[7]+m[6],m[11]+m[10],m[15]+m[14]);r(20,m[3]-m[2],m[7]-m[6],m[11]-m[10],m[15]-m[14]);return P}
// A plain unit wholly outside the view: its picture, shadows, rings and bar lie in a ball round it, and the ball is
// outside one of the planes. Never one whose look steps on by itself frame by frame (a flyer easing its height, a health
// trail running down), so none comes back into view behind time.
function v3culled(t){const P=V3.frPl,kd=t._k;if(!P||!kd||t.fly||t.climb||t.drunk||(kd.alt||0)>0.001||(kd.lift||0)>0.001)return false;
 if(t.hp!=null&&kd.hpLag!=null&&kd.hpLag!==Math.max(0,Math.min(1,t.hp/100)))return false;
 const X=t.dx+(t.px||0)+((t.iw||1)-1)/2,Y=(t.ly||0)+0.8,Z=-t.dy-(t.py||0),r=1.6+2.6*Math.max(t.iw||1,t.ih||1)*(t.sc||1);
 for(let i=0;i<24;i+=4)if(P[i]*X+P[i+1]*Y+P[i+2]*Z+P[i+3]<-r)return true;return false}
function v3rcEmit(R,IG,sil,castG,contact,rings,BL,iadd){const F=R.F;let o=0;   /* its sheet's buffers kept with it until one is let go (V3.vaGen) */
 if(R.vg!==(V3.vaGen||0)||R.vI!==IG){R.vg=V3.vaGen||0;R.vI=IG;R.va=iadd(IG,R.tk);R.vs=R.ns?iadd(sil,R.tk):null;R.vc=R.nc?iadd(castG,R.tk):null}
 R.va.copy(F,o,12);o=12;if(R.ns){R.vs.copy(F,o,12);o+=12}if(R.nc){R.vc.copy(F,o,12);o+=12}if(R.nt){contact.copy(F,o,12);o+=12}if(R.nr)rings.copy(F,o,R.nr);for(const v of R.bar)BL.push(v)}
function v3drawInst(a,mode,tex){const n=a.length/12;if(!n)return;const gl=V3.gl,L=V3.loc,x=V3.ix,U=V3.iU;
 if(!x){const v=v3instTris(a,mode);gl.bindBuffer(gl.ARRAY_BUFFER,V3.dyn);v3up(v);v3draw(V3.dyn,v.length/12,tex);return}
 gl.uniform1f(L.inst,mode);gl.uniform3f(L.iright,U.r[0],U.r[1],U.r[2]);gl.uniform3f(L.ilean,U.l[0],U.l[1],U.l[2]);gl.uniform4f(L.ishadow,U.s[0],U.s[1],U.s[2],U.s[3]);
 gl.disableVertexAttribArray(L.p);gl.disableVertexAttribArray(L.n);gl.disableVertexAttribArray(L.uv);gl.disableVertexAttribArray(L.col);
 gl.bindBuffer(gl.ARRAY_BUFFER,mode===4?V3.ia:V3.iq);gl.vertexAttribPointer(L.ic,2,gl.FLOAT,false,8,0);gl.enableVertexAttribArray(L.ic);
 gl.bindBuffer(gl.ARRAY_BUFFER,V3.ibuf);gl.bufferData(gl.ARRAY_BUFFER,a.f.subarray(0,a.length),gl.STREAM_DRAW);
 gl.vertexAttribPointer(L.i0,4,gl.FLOAT,false,48,0);gl.vertexAttribPointer(L.i1,4,gl.FLOAT,false,48,16);gl.vertexAttribPointer(L.i2,4,gl.FLOAT,false,48,32);
 for(const l of [L.i0,L.i1,L.i2]){gl.enableVertexAttribArray(l);x.vertexAttribDivisorANGLE(l,1)}
 const e=tex&&tex.ok?tex:null;if(e){gl.activeTexture(gl.TEXTURE0);gl.bindTexture(gl.TEXTURE_2D,e.t);gl.uniform1i(L.t,0);gl.uniform1f(L.useTex,1)}else gl.uniform1f(L.useTex,0);
 const a2c=v3tpx(e);x.drawArraysInstancedANGLE(gl.TRIANGLES,0,mode===4?120:6,n);if(a2c)gl.disable(gl.SAMPLE_ALPHA_TO_COVERAGE);
 for(const l of [L.i0,L.i1,L.i2]){x.vertexAttribDivisorANGLE(l,0);gl.disableVertexAttribArray(l)}gl.disableVertexAttribArray(L.ic);
 gl.enableVertexAttribArray(L.p);gl.enableVertexAttribArray(L.n);gl.enableVertexAttribArray(L.uv);gl.enableVertexAttribArray(L.col);gl.uniform1f(L.inst,0)}
// The same corners in JS (a WebGL1 without instancing): the records spread into triangles, as the vertex shader does.
function v3instTris(a,mode){const U=V3.iU,o=(V3.ivx||(V3.ivx=new VA())).reset(),f=a.f,R=U.r,Lv=U.l,S=U.s,C=[-1,0,1,0,1,1,-1,0,1,1,-1,1];
 for(let i=0;i<a.length;i+=12){const x=f[i],y=f[i+1],z=f[i+2],w=f[i+3],b0=f[i+4],b1=f[i+5],b2=f[i+6],b3=f[i+7],r=f[i+8],g=f[i+9],b=f[i+10],al=f[i+11];
  if(mode===4){const cy=R[0],sy=-R[2],RR=w/Math.cos(Math.PI/40);for(let s=0;s<b2;s++)for(let k=0;k<3;k++){let dx=0,dz=0;if(k){const an=(b0+(b1-b0)*(s+(k>1?1:0))/b2+0.5)*6.2832,sn=Math.sin(an),co=Math.cos(an);dx=RR*(sn*cy-co*sy);dz=RR*(-sn*sy-co*cy)}o.v(x+dx,y,z+dz,0,0,0,dx*0.5/w+0.5,dz*0.5/w+0.5,r,g,b,al)}continue}
  for(let c=0;c<12;c+=2){const cx=C[c],cv=C[c+1];if(mode===1){const d=cx*w+cv*b1;o.v(x+R[0]*d+Lv[0]*cv*b0,y+Lv[1]*cv*b0,z+R[2]*d+Lv[2]*cv*b0,0,0,0,cx<0?b2:b3,1-cv,r,g,b,al)}
   else if(mode===2)o.v(x+S[0]*w*cx+S[2]*b0*cv,y,z+S[1]*w*cx+S[3]*b0*cv,0,0,0,cx<0?b2:b3,1-cv,r,g,b,al);else o.v(x+cx*w,y,z+(1-2*cv)*b0,0,0,0,(cx+1)/2,1-cv,r,g,b,al)}}
 return o}
function v3draw(buf,count,tex,fallback){const gl=V3.gl,L=V3.loc;gl.bindBuffer(gl.ARRAY_BUFFER,buf);const st=48;
 gl.vertexAttribPointer(L.p,3,gl.FLOAT,false,st,0);gl.enableVertexAttribArray(L.p);gl.vertexAttribPointer(L.n,3,gl.FLOAT,false,st,12);gl.enableVertexAttribArray(L.n);
 gl.vertexAttribPointer(L.uv,2,gl.FLOAT,false,st,24);gl.enableVertexAttribArray(L.uv);gl.vertexAttribPointer(L.col,4,gl.FLOAT,false,st,32);gl.enableVertexAttribArray(L.col);
 const e=tex&&tex.ok?tex:null;if(e){gl.activeTexture(gl.TEXTURE0);gl.bindTexture(gl.TEXTURE_2D,e.t);gl.uniform1i(L.t,0);gl.uniform1f(L.useTex,1)}else gl.uniform1f(L.useTex,0);
 // A picture still loading shows its kind's colour, never a white flash.
 const tinted=tex&&!e&&fallback;if(tinted)gl.uniform4f(L.tint,fallback[0],fallback[1],fallback[2],1);
 const a2c=v3tpx(e);gl.drawArrays(gl.TRIANGLES,0,count);if(a2c)gl.disable(gl.SAMPLE_ALPHA_TO_COVERAGE);if(tinted)gl.uniform4f(L.tint,0,0,0,0)}
// A pixel-art picture (v3texUpload's px) drawn smooth but defined (the shader's txp): its size to the shader, and drawn
// unblended, its outline's soft edge as coverage (the view is multisampled), so the silhouette is smooth too and still
// sorts by depth. Returns whether coverage was turned on, for the caller to turn off after its draw.
function v3tpx(e){const gl=V3.gl,L=V3.loc;if(!e||!e.px){gl.uniform3f(L.tpx,1,1,0);return false}const c=!gl.isEnabled(gl.BLEND);gl.uniform3f(L.tpx,e.px[0],e.px[1],c?2:1);if(c)gl.enable(gl.SAMPLE_ALPHA_TO_COVERAGE);return c}
// Where the sun is (a unit vector towards it): up in the east at daybreak, highest (about 58 degrees) in the south
// at noon, down in the west at dusk, from how far through the day it is (View3D.dm). At night, the moon, fixed.
// Time of day as light. Day: the sun's colour and strength and the sky's fill, golden when the sun is low; night: a
// moonlit blue grade (nk) with the moon's weak light. Day's end and night's start both come to the same twilight, so
// the game's night flag switches with no jump, and the sun and moon are both faint there, so their swap doesn't show.
// The season tints green ground and leaves (seas: autumn, winter, spring), eased in when it changes.
function v3grade(){const dp=V3.dayp==null?0.62:V3.dayp,e=Math.sin(Math.PI*Math.max(0,Math.min(1,dp))),ss=(a,b,x)=>{const t=Math.max(0,Math.min(1,(x-a)/(b-a)));return t*t*(3-2*t)},M=(a,b,t)=>[a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t,a[2]+(b[2]-a[2])*t];
 const T={sunc:[0.55,0.38,0.3],skyc:[0.86,0.88,1.02],unl:[1.0,0.95,0.92],nk:0.55,fog:[0.28,0.28,0.42],zen:[0.12,0.15,0.36],amb:0.96,dirk:0.12};   /* twilight: the blue hour */let D,f;
 if(!V3.night){const w=1-ss(0.1,0.62,e),k=0.55+0.45*ss(0.05,0.5,e);D={sunc:M([1.04,1.02,0.97],[1.3,0.92,0.62],w).map(v=>v*k),skyc:M([0.98,1.0,1.04],[0.84,0.85,0.98],w),unl:M([1,1,1],[1.06,0.97,0.88],w),nk:0,fog:M([0.55,0.68,0.78],[0.8,0.63,0.52],w),zen:M([0.27,0.47,0.8],[0.26,0.33,0.6],w),amb:1,dirk:k};f=ss(0,0.24,e)}
 else{D={sunc:[0.6,0.7,0.98],skyc:[0.88,0.92,1.02],unl:[1.04,1.04,1.06],nk:1,fog:[0.05,0.075,0.15],zen:[0.015,0.025,0.075],amb:0.9,dirk:0.5};f=ss(0,0.2,e)}
 const G={};for(const k in T)G[k]=typeof T[k]==='number'?T[k]+(D[k]-T[k])*f:M(T[k],D[k],f);
 const sn=String(V3.seasonOverride||(typeof model!=='undefined'&&model&&model.season)||'').toLowerCase(),want=sn==='fall'||sn==='autumn'?[0.5,0,0]:sn==='winter'?[0,0.4,0]:sn==='spring'?[0,0,0.6]:[0,0,0];
 const S=V3.seas||(V3.seas=want.slice()),now=performance.now(),dt=Math.min(0.1,(now-(V3.seasAt||now))/1000);V3.seasAt=now;for(let i=0;i<3;i++)S[i]+=(want[i]-S[i])*Math.min(1,dt*0.4);G.seas=S;return G}
function M3mix(a,b,t){return [a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t,a[2]+(b[2]-a[2])*t]}
function v3sunDir(){if(V3.night){const dp=V3.dayp==null?0.5:Math.max(0,Math.min(1,V3.dayp)),el=(16+36*Math.sin(Math.PI*dp))*Math.PI/180,th=Math.PI*dp;return [Math.cos(th)*Math.cos(el),Math.sin(el),Math.sin(th)*Math.cos(el)]}const dp=V3.dayp==null?0.62:V3.dayp,el=(14+44*Math.sin(Math.PI*dp))*Math.PI/180,th=Math.PI*dp;return [Math.cos(th)*Math.cos(el),Math.sin(el),Math.sin(th)*Math.cos(el)]}
// One mesh into the sun's shadow map (the shadow program is in use).
function v3drawShadow(buf,count,tex){const gl=V3.gl,L=V3.loc,S=V3.sh;gl.bindBuffer(gl.ARRAY_BUFFER,buf);const st=48;
 gl.vertexAttribPointer(L.p,3,gl.FLOAT,false,st,0);gl.enableVertexAttribArray(L.p);gl.vertexAttribPointer(L.uv,2,gl.FLOAT,false,st,24);gl.enableVertexAttribArray(L.uv);gl.vertexAttribPointer(L.col,4,gl.FLOAT,false,st,32);gl.enableVertexAttribArray(L.col);if(L.n>=0)gl.disableVertexAttribArray(L.n);   /* the shadow pass reads no normal: left on, it could point at a let-go buffer and every shadow draw failed */
 const e=tex&&tex.ok?tex:null;if(e){gl.activeTexture(gl.TEXTURE0);gl.bindTexture(gl.TEXTURE_2D,e.t);gl.uniform1i(S.t,0);gl.uniform1f(S.useTex,1)}else gl.uniform1f(S.useTex,0);gl.drawArrays(gl.TRIANGLES,0,count)}
// A short word drawn on a canvas as a texture, cached by its text: the knocked-out "Zzz", captives' countdowns.
// Blood pools (BloodPools.dm; the owner, 10-29: "one big pool if blood tiles are adjencent", the look from a mock-up: "Keep
// splat detail", "Thinner, patchier"): a block's pool drawn as one crisp picture laid on the ground, 32 px a tile, made
// again at most every 1.5 s while its blood changes (two a frame at most): a patchy surface where blood is heavy, its shape
// a field of the tiles' splats round each point (the blocks round it too, so a pool runs on across blocks without a seam),
// and each tile's last two splats on it. A picture reaches a tile past its block where no block of blood is; every tile is
// drawn by one picture only, so none fight. One splat alone stays a small puddle.
const V3POOL_MID=[[169,0,0],[151,0,0],[187,0,0]],V3POOL_DARK=[[134,0,0],[151,0,0],[120,0,0]],V3POOL_RIM=[50,4,2];
function v3poolNz(x,y,s){let h=Math.imul(x,73856093)^Math.imul(y,19349663)^Math.imul(s,83492791);h=Math.imul(h^(h>>>13),1274126177);return ((h^(h>>>16))>>>0)%1000/1000}
function v3poolImg(f){if(!f)return null;const M=V3.poolImgs||(V3.poolImgs=new Map());let im=M.get(f);if(!im){im=new Image();im.onload=()=>{V3.poolImgN=(V3.poolImgN||0)+1};im.src=f;M.set(f,im)}return im.complete&&im.naturalWidth?im:null}
function v3poolBlocks(){if(V3.poolOf!==V3.things){V3.poolOf=V3.things;const B=V3.poolByBlock=new Map();for(const o of V3.things)if(o.pool&&o.pool.length>2)B.set(Math.floor((o.pool[0]-1)/8)+','+Math.floor((o.pool[1]-1)/8),o)}return V3.poolByBlock}
function v3poolMake(t,B){
 const P=t.pool,x0=P[0],y0=P[1],bx=Math.floor((x0-1)/8),by=Math.floor((y0-1)/8),GW=14,gx0=x0-3,gy0=y0-3,W=new Float32Array(GW*GW),own=[];
 for(let i=-1;i<=1;i++)for(let j=-1;j<=1;j++){const q=B.get((bx+i)+','+(by+j));if(!q)continue;const Q=q.pool;for(let k=2;k<Q.length;k++){const c=Q[k],ix=Q[0]+c[0]-gx0,iy=Q[1]+c[1]-gy0;if(ix>=0&&iy>=0&&ix<GW&&iy<GW)W[iy*GW+ix]=0.2+Math.min(c[2],12)*0.075;if(q===t)own.push(c)}}   /* each tile with blood a soft blob, stronger the more splats */
 const E=V3.poolE||(V3.poolE=(()=>{const e=new Float32Array(80);for(let s=0;s<16;s++)for(let k=0;k<5;k++){const r=(s+0.5)/16-0.5-(k-2);e[s*5+k]=Math.exp(-r*r/0.33)}return e})());   /* a blob's reach along one axis, by blood pixel in the tile and tile apart */
 const ours=(tx,ty)=>{const qb=Math.floor((tx-1)/8),rb=Math.floor((ty-1)/8);return (qb===bx&&rb===by)||!B.has(qb+','+rb)};
 const S=320,cv=document.createElement('canvas');cv.width=cv.height=S;const g=cv.getContext('2d'),img=g.createImageData(S,S),d=img.data,clip=new Path2D();
 for(let j=0;j<10;j++){const ty=y0+8-j;for(let i=0;i<10;i++){const tx=x0-1+i;if(!ours(tx,ty))continue;clip.rect(i*32,j*32,32,32);
  for(let sy=0;sy<16;sy++){const vy=15-sy;for(let sx=0;sx<16;sx++){let f=0;for(let ky=0;ky<5;ky++){const ey=E[vy*5+ky];if(ey<0.002)continue;const row=(ty+ky-2-gy0)*GW+tx-2-gx0;for(let kx=0;kx<5;kx++){const w=W[row+kx];if(w)f+=w*E[sx*5+kx]*ey}}
   if(f<0.3)continue;const wx=tx*16+sx,wy=ty*16+vy;f+=(v3poolNz(wx,wy,1)-0.5)*0.35+(v3poolNz(Math.floor(wx/5),Math.floor(wy/5),2)-0.5)*0.45;if(f<0.95)continue;   /* patchy: only where blood is heavy, ragged */
   const r=v3poolNz(wx,wy,3),c=f<1.03?V3POOL_RIM:(f>1.5&&r<0.7?V3POOL_DARK:V3POOL_MID)[Math.floor(r*3)%3];
   const px=i*32+sx*2,py=j*32+sy*2;for(let yy=0;yy<2;yy++){let o=((py+yy)*S+px)*4;for(let xx=0;xx<2;xx++,o+=4){d[o]=c[0];d[o+1]=c[1];d[o+2]=c[2];d[o+3]=255}}}}}}
 g.putImageData(img,0,0);g.imageSmoothingEnabled=false;g.save();g.clip(clip);let miss=0;
 for(const c of own){const tx=x0+c[0],ty=y0+c[1],i=tx-x0+1,j=y0+8-ty;for(let k=3;k<=4;k++){const ti=c[k];if(ti==null||ti<0)continue;const im=v3poolImg(t.pt&&t.pt[ti]);if(!im){miss++;continue}g.drawImage(im,i*32+Math.round((v3poolNz(tx,ty,10+k)-0.5)*8),j*32+Math.round((v3poolNz(tx,ty,20+k)-0.5)*8),32,32)}}   /* the tile's last two splats, as they fell */
 g.restore();
 const gl=V3.gl,tex=gl.createTexture();gl.bindTexture(gl.TEXTURE_2D,tex);gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL,false);gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL,true);gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,gl.RGBA,gl.UNSIGNED_BYTE,cv);gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL,false);
 gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.LINEAR);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.NEAREST);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);
 return {e:{t:tex,ok:true},miss}}
function v3poolDraw(t,add){const P=t.pool;if(!Array.isArray(P)||P.length<3||!V3.gl)return;const B=v3poolBlocks(),bx=Math.floor((P[0]-1)/8),by=Math.floor((P[1]-1)/8),key='rm:pool:'+t.id,now=performance.now();
 let sig=t.pv+'|'+(V3.poolImgN||0);for(let i=-1;i<=1;i++)for(let j=-1;j<=1;j++)if(i||j){const q=B.get((bx+i)+','+(by+j));sig+=','+(q?q.pv:'-')}
 const PT=V3.poolTex||(V3.poolTex=new Map());let r=PT.get(key);if(now-(V3.poolBT||0)>8){V3.poolBT=now;V3.poolBudget=0}
 if((!r||r.sig!==sig)&&(!r||now-r.at>1500)&&V3.poolBudget<2){V3.poolBudget++;const m=v3poolMake(t,B);if(r&&r.e&&r.e.t)V3.gl.deleteTexture(r.e.t);r={e:m.e,at:now,sig:m.miss?sig+'|miss':sig,seen:now};PT.set(key,r);V3.tex.set(key,m.e)}
 if(!r)return;r.seen=now;const x0=P[0]-1,y0=P[1]-1,a=[];quad(a,[x0-0.5,0.02,-y0+0.5],[x0+9.5,0.02,-y0+0.5],[x0+9.5,0.02,-y0-9.5],[x0-0.5,0.02,-y0-9.5],[0,1,0],[1,1,1,1],[0,1,1,1,1,0,0,0]);add(key,a);
 if(now-(V3.poolGC||0)>5000){V3.poolGC=now;for(const [k,o] of PT)if(now-o.seen>10000){if(o.e&&o.e.t)V3.gl.deleteTexture(o.e.t);V3.tex.delete(k);PT.delete(k)}}}   /* pictures of pools gone or out of view a while */
// Ships (naval, Ships.dm): a hull of planks on the water, bobbing and rolling a little, drawn from the same beams and
// blobs as the siege engines. A rowboat: a short open boat with two oars a side. A longship: long and low, a dragon prow,
// shields in its owner's colour along the sides, a square striped sail and oars sweeping while it moves. A cog: broad
// and high, a castle at the stern, a tall mast and a big sail in its owner's colour. Those aboard sit along the deck.
function v3shipDraw(a,e){const kind=e.siege,big=kind==='cog',lng=kind==='longship',t=performance.now()/1000;
 const d=e.dir||2,fx=(d&4?1:0)-(d&8?1:0),fz=(d&2?1:0)-(d&1?1:0),L=Math.hypot(fx,fz)||1,ux=fx/L||0,uz=fz/L||(fx?0:1),px=-uz,pz=ux;
 const [X,,Z]=v3world(e),W=v3groundAt(e.x,e.y)-0.12,bob=Math.sin(t*1.4+e.x*0.7+e.y*0.3)*0.035,roll=Math.sin(t*1.1+e.y)*0.05;
 if(e.dx!=null&&(Math.abs(e.dx-e.x)>0.02||Math.abs(e.dy-e.y)>0.02))e._mvAt=t;const moving=!!e._mvAt&&t-e._mvAt<0.6,beam=v3beam4.bind(null,a);
 const len=lng?1.55:big?1.25:0.72,wid=lng?0.36:big?0.52:0.3,hi=lng?0.3:big?0.55:0.24,draft=big?0.16:0.1;
 const at=(u,v,h)=>[X+ux*u+px*v,W+bob+h+roll*v,Z+uz*u+pz*v];
 const hull=[0.42,0.27,0.14,1],plank=[0.5,0.33,0.17,1],dark=[0.25,0.16,0.08,1],sailC=e.sail?v3hexCol(e.sail):[0.82,0.76,0.6,1],cloth=[0.86,0.82,0.7,1];
 // the hull: sides curving in to the prow and stern, a few strakes each side, the deck between them
 const N=8,side=[];for(let i=0;i<=N;i++){const u=-len+2*len*i/N,s=Math.sqrt(Math.max(0,1-Math.pow(u/len,2)))*0.92+0.08;side.push([u,wid*s])}
 for(const sg of [-1,1])for(let i=0;i<N;i++){const [u0,w0]=side[i],[u1,w1]=side[i+1];
  for(let k=0;k<3;k++){const h0=-draft+(hi+draft)*k/3,h1=-draft+(hi+draft)*(k+1)/3,f0=0.55+0.45*(k+1)/3,f1=0.55+0.45*k/3,c=k%2?hull:plank;
   quad(a,at(u0,sg*w0*f1,h0),at(u1,sg*w1*f1,h0),at(u1,sg*w1*f0,h1),at(u0,sg*w0*f0,h1),[0,1,0],c);quad(a,at(u1,sg*w1*f1,h0),at(u0,sg*w0*f1,h0),at(u0,sg*w0*f0,h1),at(u1,sg*w1*f0,h1),[0,1,0],c)}
  beam(at(u0,sg*w0,hi),at(u1,sg*w1,hi),0.022,dark)}   // the gunwale
 for(let i=0;i<N;i++){const [u0,w0]=side[i],[u1,w1]=side[i+1],h=hi*0.55;quad(a,at(u0,-w0*0.85,h),at(u1,-w1*0.85,h),at(u1,w1*0.85,h),at(u0,w0*0.85,h),[0,1,0],i%2?plank:[0.55,0.37,0.2,1])}
 // prow and stern posts; a longship's prow a dragon's neck and head
 beam(at(len-0.02,0,hi),at(len+(lng?0.18:0.06),0,hi+(lng?0.42:0.12)),0.035,dark);beam(at(-len+0.02,0,hi),at(-len-(lng?0.14:0.05),0,hi+(lng?0.32:0.1)),0.035,dark);
 if(lng){const hd=at(len+0.24,0,hi+0.47);MD.blob(a,hd[0],hd[1],hd[2],0.07,0.05,0.07,[0.2,0.14,0.07,1],e.x,0.05)}
 // a cog's castle at the stern
 if(big){for(const v of [-1,1])quad(a,at(-len*0.95,v*wid*0.7,hi),at(-len*0.45,v*wid*0.8,hi),at(-len*0.45,v*wid*0.8,hi+0.28),at(-len*0.95,v*wid*0.7,hi+0.28),[0,1,0],hull);
  quad(a,at(-len*0.95,-wid*0.7,hi+0.28),at(-len*0.45,-wid*0.8,hi+0.28),at(-len*0.45,wid*0.8,hi+0.28),at(-len*0.95,wid*0.7,hi+0.28),[0,1,0],plank)}
 // shields along a longship's sides, in its owner's colour and wood
 if(lng)for(const sg of [-1,1])for(let i=1;i<N;i++){const [u,w]=side[i],p=at(u,sg*(w+0.015),hi*0.82);MD.blob(a,p[0],p[1],p[2],0.06,0.06,0.06,i%2?sailC:[0.62,0.5,0.32,1],i*3+sg,0.02)}
 // oars: two a side on a rowboat, five a side on a longship, sweeping while it moves
 if(!big){const n=lng?5:2,sw=moving?Math.sin(t*(lng?5:6))*0.25:0;for(const sg of [-1,1])for(let i=0;i<n;i++){const u=-len*0.55+len*1.1*(i+0.5)/n,w=side[Math.round((u+len)/(2*len)*N)][1];
  beam(at(u,sg*w,hi),at(u+sw*0.6,sg*(w+0.45),-0.02+Math.abs(sw)*0.1),0.012,[0.55,0.42,0.25,1])}}
 // mast and sail: a square sail, striped on a longship; furled on a rowboat
 if(lng||big){const mh=big?2.0:1.45,yd=big?0.62:0.5,sl=moving?0.12:0.04;beam(at(0.05,0,hi*0.5),at(0.05,0,hi+mh),0.03,dark);beam(at(0.05,-yd,hi+mh-0.08),at(0.05,yd,hi+mh-0.08),0.022,dark);
  const rows=big?4:5;for(let r=0;r<rows;r++){const h0=hi+mh-0.1-(mh-0.35)*r/rows,h1=hi+mh-0.1-(mh-0.35)*(r+1)/rows,b0=sl*Math.sin(Math.PI*r/rows),b1=sl*Math.sin(Math.PI*(r+1)/rows),c=lng?(r%2?cloth:sailC):(r%2?sailC:v3shade4(sailC,0.88));
   quad(a,at(0.1+b0,-yd,h0),at(0.1+b0,yd,h0),at(0.1+b1,yd,h1),at(0.1+b1,-yd,h1),[0,1,0],c);quad(a,at(0.1+b1,-yd,h1),at(0.1+b1,yd,h1),at(0.1+b0,yd,h0),at(0.1+b0,-yd,h0),[0,1,0],c)}}
 // those aboard, sitting along the deck
 const n=Math.min(e.aboard||0,lng?12:big?10:4);for(let i=0;i<n;i++){const row=lng?Math.floor(i/2):big?Math.floor(i/2):Math.floor(i/2),u=-len*0.6+len*1.2*(row+0.5)/Math.max(1,Math.ceil(n/2)),v=(i%2?1:-1)*wid*0.42,p=at(u,v,hi*0.55),c=(e.crew&&e.crew[i])?v3hexCol(e.crew[i]):[0.7,0.55,0.42,1];
  MD.blob(a,p[0],p[1]+0.12,p[2],0.07,0.11,0.07,c,i*7+e.x,0.05);MD.blob(a,p[0],p[1]+0.27,p[2],0.055,0.055,0.055,[0.82,0.66,0.52,1],i*5+e.y,0.04)}
 // the wake: two pale lines spreading behind it while it moves
 if(moving)for(const sg of [-1,1]){const p0=at(-len,sg*wid*0.5,0.015),p1=at(-len-0.9,sg*(wid+0.45),0.015);beam(p0,p1,0.03,[0.82,0.9,0.95,0.9])}}
function v3hexCol(h){const n=parseInt(String(h).replace('#',''),16);return isNaN(n)?[0.8,0.75,0.6,1]:[(n>>16&255)/255,(n>>8&255)/255,(n&255)/255,1]}
function v3shade4(c,f){return [c[0]*f,c[1]*f,c[2]*f,c[3]]}
function v3beam4(a,p0,p1,w,c){const dx=p1[0]-p0[0],dz=p1[2]-p0[2],hl=Math.hypot(dx,dz)||1,nx=-dz/hl*w,nz=dx/hl*w;
 quad(a,[p0[0]-nx,p0[1],p0[2]-nz],[p0[0]+nx,p0[1],p0[2]+nz],[p1[0]+nx,p1[1],p1[2]+nz],[p1[0]-nx,p1[1],p1[2]-nz],[0,1,0],c);quad(a,[p1[0]-nx,p1[1],p1[2]-nz],[p1[0]+nx,p1[1],p1[2]+nz],[p0[0]+nx,p0[1],p0[2]+nz],[p0[0]-nx,p0[1],p0[2]-nz],[0,1,0],c);
 quad(a,[p0[0],p0[1]-w,p0[2]],[p0[0],p0[1]+w,p0[2]],[p1[0],p1[1]+w,p1[2]],[p1[0],p1[1]-w,p1[2]],[0,1,0],c);quad(a,[p1[0],p1[1]-w,p1[2]],[p1[0],p1[1]+w,p1[2]],[p0[0],p0[1]+w,p0[2]],[p0[0],p0[1]-w,p0[2]],[0,1,0],c)}
const V3SHIPK=new Set(['rowboat','longship','cog']);
function v3word(txt,col){if(!V3.wfl&&document.fonts){V3.wfl=1;document.fonts.load('bold 19px HudText').then(()=>{for(const [k,e] of V3.tex)if(k.startsWith('rm:w:')){if(e.t)V3.gl.deleteTexture(e.t);V3.tex.delete(k)}}).catch(()=>{})}   /* the HUD's lettering arrives with the page: words drawn before it are drawn again */
 const key='rm:w:'+col+':'+txt;if(!V3.tex.has(key)){const c=document.createElement('canvas'),F='bold 19px HudText,Georgia,serif',m=c.getContext('2d');m.font=F;const w=Math.max(128,Math.ceil(m.measureText(txt).width)+12);c.width=w;c.height=32;const x=c.getContext('2d');x.font=F;x.textAlign='center';x.textBaseline='middle';x.lineWidth=4;x.strokeStyle='rgba(0,0,0,.85)';x.strokeText(txt,w/2,16);x.fillStyle=col;x.fillText(txt,w/2,16);const e=v3texFromCanvas(c);e.wk=w/128;V3.tex.set(key,e)}return key}   /* a long word ("Bleeding out 59", "Bound, straining") widens its picture, and its quad with it (wk), instead of losing both ends */
function v3world(t){return [t.dx,0,-t.dy]}
// Which of the unit's S/N/E/W sprites faces the camera (BYOND dirs: 1 N, 2 S, 4 E, 8 W).
// Your nearest units on the ground (the selected first), nearest first: the same order as sorting them all (ties keep
// the list's order), the first 16 picked in one pass (the rock fade takes 8, skipping any off the screen); sorting
// thousands every frame cost about 1 ms at 8,000.
function v3nearest8(){const K=16,B=V3.near8||(V3.near8=[]);B.length=0;const cx=V3.cx,cy=V3.cy;for(const t of v3cat('mine',t=>t.kind==='mine')){if(t.kind!=='mine'||t.dx==null||(t.ly&&(t.ly<0||t.fly)))continue;const pen=t.selected?0:1e4;   /* yours up on the rock or a wall-walk too (t.ly over 0): the rock in front of them thins as for those on the ground (own units are never hidden) */if(B.length===K&&pen+Math.max(Math.abs(t.dx-cx),Math.abs(t.dy-cy))>=B[K-1][1])continue;if(!v3visible(t))continue;const d=pen+Math.hypot(t.dx-cx,t.dy-cy);
 if(B.length===K&&d>=B[K-1][1])continue;let i=B.length<K?B.length:K-1;if(B.length<K)B.push(null);while(i>0&&B[i-1][1]>d){B[i]=B[i-1];i--}B[i]=[t,d]}return B}
function v3face(t){const d=t.dir||2;const fx=(d&4?1:0)-(d&8?1:0),fz=(d&2?1:0)-(d&1?1:0);if(!fx&&!fz)return 0;const sy=Math.sin(V3.yaw),cy=Math.cos(V3.yaw);const along=fx*-sy+fz*-cy,side=fx*cy+fz*-sy;if(Math.abs(along)>=Math.abs(side))return along<0?0:1;return side>0?2:3}   /* plain numbers: it runs for every unit every frame */
// Huge beasts (dragons, spiders; Beasts.dm): an atlas per animation and facing (the pack's angles: 000 seen from
// behind, 090 facing right), the facing nearest how the camera sees the unit, frames by time. Standing it is a
// bent card - upright above its ground point, lying on the ground toward the camera below it (the packs are drawn
// from high up, so what is below the ground point is nearer, not lower); flying, the same card lifted into the air.
// It casts its own wide shadow. Returns the height of its top (for the health bar), or 0 while its pictures
// are still on their way (the old sprite is drawn instead).
const V3BEAST_FACINGS=['000','045','090','135','180','225','270','315'];
function v3drawBeast(t,X,gy,Z,kd,nowS,walking,add,shadows,air){const B=t.beast;if(B.kind==='golem')return typeof bsBeast==='function'?bsBeast(t,X,gy,Z,kd,walking,shadows):0;   /* a stone golem: its model (Golems.dm, bosses.js) */let anim=B.anim,M=B.meta,once=-1;air=air||0;
 // Take-off plays once as it leaves the ground; coming down it flies until it is near the ground, then lands.
 if(kd){if(B.fly&&!kd.upAt&&B.takeoff)kd.upAt=nowS;if(!B.fly)kd.upAt=0;if(!B.fly&&air<0.6&&kd.wasUp&&B.land){kd.downAt=nowS;kd.wasUp=0}if(B.fly)kd.wasUp=1}
 const rising=kd&&kd.upAt&&B.takeoff&&nowS-kd.upAt<B.takeoff[0]/B.takeoff[6],landing=kd&&kd.downAt&&B.land&&nowS-kd.downAt<B.land[0]/B.land[6];
 if(rising){anim='takeoff';M=B.takeoff;once=nowS-kd.upAt}else if(landing){anim='land';M=B.land;once=nowS-kd.downAt}
 else if(!B.fly&&air>=0.6&&B.air){anim='fly';M=B.air}
 else if(walking&&anim==='idle'&&B.walk){anim='walk';M=B.walk}
 // Its F breath (Specials.dm): it breathes, turned to the spot, while the stream runs.
 const spB=!B.dead&&B.brm?(V3.fx||[]).find(f=>f.type==='special'&&f.sp==='breath'&&f.sx===t.x&&f.sy===t.y&&performance.now()-f.t<1100):null;
 if(spB){anim=B.fly&&B.fbrm?'flybreathe':'breathe';M=anim==='flybreathe'?B.fbrm:B.brm;once=-1}
 // A dead beast (Beasts.dm RmBeastCorpse3D): its death played once from when it fell, then held as it lies.
 if(B.dead){anim='death';M=B.meta;if(kd&&kd.deadSeen==null)kd.deadSeen=nowS;once=(B.since||0)+(kd?nowS-kd.deadSeen:99)}
 if(!M)return 0;
 // Fighting, it stays on its own tile, turned to its foe (Beasts.dm tx/ty): the server has it bite and breathe
 // from where its head is drawn (RmJawStrike), so nothing slides it about.
 let wx,wz;{const d=t.dir||2;wx=(d&4?1:0)-(d&8?1:0);wz=(d&2?1:0)-(d&1?1:0)}
 if(kd&&B.tx!=null&&!B.dead){const dx=B.tx-X,dz=-B.ty-Z,dist=Math.hypot(dx,dz);if(dist>0.01){kd.bdx=dx/dist;kd.bdz=dz/dist;wx=kd.bdx;wz=kd.bdz}}
 if(spB){const dx=spB.tx-X,dz=-spB.ty-Z,dd=Math.hypot(dx,dz)||1;wx=dx/dd;wz=dz/dd}
 const rx=Math.cos(V3.yaw),rz=-Math.sin(V3.yaw),ax=-Math.sin(V3.yaw),az=-Math.cos(V3.yaw);
 // chained down (Taming.dm): every few seconds it strains against its chains, shaking
 if(B.bound&&!B.dead){const ph=(nowS+(t.x*7+t.y)%5)%3.2;if(ph<0.7){const j=Math.sin(nowS*34)*0.06*(B.size||1)*(1-ph/0.7);X+=j*rx;Z+=j*rz}}
 const ang=(Math.atan2(wx*rx+wz*rz,wx*ax+wz*az)*180/Math.PI+360)%360,fi=Math.round(ang/45)%8,base='rb-'+B.kind+'-'+B.variant+'-'+anim+'-';
 let file=base+V3BEAST_FACINGS[fi]+'.png';const e=v3tex(file);
 v3tex(base+V3BEAST_FACINGS[(fi+1)%8]+'.png');v3tex(base+V3BEAST_FACINGS[(fi+7)%8]+'.png');   // the facings it may turn to next
 // Never the old sprite: until a picture has arrived, the last one drawn (or, the first time, just its shadow).
 if(!(e&&e.ok)){if(kd&&kd.bFile){file=kd.bFile;M=kd.bM;once=-1}else{const r0=1.2*(B.size||1),sy0=gy+0.012;for(const k of [1,0.7,0.4]){const a2=r0*k,b2=r0*k*0.6;quad(shadows,[X-a2,sy0,Z+b2],[X+a2,sy0,Z+b2],[X+a2,sy0,Z-b2],[X-a2,sy0,Z-b2],[0,0,0],[0,0,0,1],[0,1,1,1,1,0,0,0])}return gy+air+3}}
 else if(kd){kd.bFile=file;kd.bM=M}
 const[n,cols,w,h,px,py,fps]=M,rows=Math.ceil(n/cols),fr=once>=0?Math.min(n-1,Math.floor(once*fps)):Math.floor(nowS*fps+(kd&&kd.off||0)*n)%n,col=fr%cols,row=Math.floor(fr/cols);
 const s=(B.size||1)/(B.ppt||64),u0=col/cols+0.0002,u1=(col+1)/cols-0.0002,v0=row/rows+0.0002,v1=(row+1)/rows-0.0002,vp=(row+py/h)/rows;
 const L=-px*s,R=(w-px)*s,up=py*s,down=(h-py)*s,c=[1,1,1,1],a=[],P=(x,y,b)=>[X+rx*x-ax*b,y,Z+rz*x-az*b];let top;
 {const y=gy+0.03+air;top=y+up;quad(a,P(L,y,0),P(R,y,0),P(R,top,0),P(L,top,0),[0,0,0],c,[u0,vp,u1,vp,u1,v0,u0,v0]);
  quad(a,P(L,y,down),P(R,y,down),P(R,y,0),P(L,y,0),[0,1,0],c,[u0,v1,u1,v1,u1,vp,u0,vp])}
 add(file,a);
 // its upright part laid on the ground away from the sun, as units' are; a flyer's falls further off the higher it flies
 {const CS=V3.cast;if(CS&&CS.on&&!B.dead&&anim!=='death'){let ca=CS.g.get(file);if(!ca){ca=new VA();CS.g.set(file,ca)}const g0=gy+0.02,Ls=up*CS.len,ox=CS.sx*air*CS.len,oz=CS.sz*air*CS.len,x0=X+CS.px*L+ox,z0=Z+CS.pz*L+oz,x1=X+CS.px*R+ox,z1=Z+CS.pz*R+oz;
  quad(ca,[x0,g0,z0],[x1,g0,z1],[x1+CS.sx*Ls,g0,z1+CS.sz*Ls],[x0+CS.sx*Ls,g0,z0+CS.sz*Ls],QN0,QBLK,[u0,vp,u1,vp,u1,v0,u0,v0])}}
 {const mm=B.mouths&&B.mouths[anim];if(kd&&mm){const nf=Math.max(1,Math.floor(mm.length/16)),mi=(fi*nf+Math.min(fr,nf-1))*2,mx=mm[mi],my=mm[mi+1],y0=gy+0.03+air;kd.mouthPt=my<=py?P((mx-px)*s,y0+(py-my)*s,0):P((mx-px)*s,y0,(my-py)*s);if(air<0.6){const gp=v3groundUnder(kd.mouthPt,gy+0.45);if(gp)kd.mouthPt=gp}kd.mouthAt=nowS}}
 if(kd&&B.breath&&B.tx!=null&&/breathe/.test(anim)){const jm=kd.mouthPt&&nowS-kd.mouthAt<0.2?kd.mouthPt:[X+(kd.bdx||0)*(B.jaw||1),gy+air+(B.mouth||1),Z+(kd.bdz||0)*(B.jaw||1)];
  V3.breaths.push({m:jm,t:[B.tx,gy+(air<0.6?0.45:0.6),-B.ty],el:B.breath,seed:(t.x*7+t.y)|0})}
 const r=Math.max(0.6,(R-L)*0.26)/(1+air*0.04),sy=gy+0.012;
 for(const k of [1,0.84,0.68,0.52,0.36]){const a2=r*k,b2=r*k*0.6;quad(shadows,[X-a2,sy,Z+b2],[X+a2,sy,Z+b2],[X+a2,sy,Z-b2],[X-a2,sy,Z-b2],[0,0,0],[0,0,0,1],[0,1,1,1,1,0,0,0])}
 return top}
function v3kick(){if(V3.rafPending)return;V3.rafPending=true;requestAnimationFrame(t=>{V3.rafPending=false;v3frame(t)})}
// Mountain cut-away (Buildings.dm halls): with the camera on a tile that has rock overhead (inside a mountain),
// the terrain round it is cut down to the tunnel's ceiling so the halls and tunnels show, like a cut-away model.
// The fragment shader discards terrain above the ceiling on whole tiles within a radius; the radius grows to 8
// tiles and back, so the cut opens tile by tile from the middle and closes again. It reaches on toward the camera
// (a capsule), so the rock between the eye and the hall is cut too. Geometry stays whole (shadows, picking,
// rockGeo); faceted caps close the tops of the cut rock and walls, and the standing rock beside the cut shows its
// section. Returns their vertices.
// Where the middle of the view meets a floor at height fl: the camera aims a little above the ground (V3.camH, eased; on
// rock 0.6 of its top), so the floor in the middle of the screen can lie beyond V3.cx, V3.cy.
function v3mcutLook(fl){const E=V3.eye,tY=V3.camH!=null?V3.camH:v3groundAt(V3.cx,V3.cy)*0.6;
 if(!E||E[1]-tY<0.05||tY<=fl)return [V3.cx,V3.cy];const s=Math.min(4,(E[1]-fl)/(E[1]-tY)),x=E[0]+(V3.cx-E[0])*s,z=E[2]+(-V3.cy-E[2])*s;return [x,-z]}
function v3mountainCut(L,dt){const inK=K=>!!(K&&K.roof&&K.kind!=='wall');
 // The cut follows your units (the user, 2026-10-24, the whole mountain mineable now: "cut at the unit's height"; "when
 // digging in mountains the clicker hits the top"): round a selected unit of yours walled in by rock (in a tunnel or a
 // hall, down a pit, or up on the mountain in a hollow it dug), the rock is cut down to just over its head, two blocks
 // over its feet, so it and the blocks round it show and take the click (a cut rock's top is the block cut through); with
 // none of yours walled in the mountain stands whole. Walled in: a tunnel's roof over it, or 6 of its 8 neighbours (or 12 of the 16 tiles two out) rock standing over
 // 2.4 above its feet (a plain mountain edge or an inside corner has 5 or fewer, 11 or fewer).
 const pit=(fx,fy,f)=>{const tall=(x,y)=>{const K=v3kindAt(x,y);return !!K&&(K.kind==='wall'||K.kind==='block'||inK(K))&&v3peakTop(x,y)>f+2.4};let r1=0,r2=0;
  for(let dy=-2;dy<=2;dy++)for(let dx=-2;dx<=2;dx++){if(!dx&&!dy)continue;if(!tall(fx+dx,fy+dy))continue;if(Math.abs(dx)<2&&Math.abs(dy)<2)r1++;else r2++}return r1>=6||r2>=12};
 let U=null,UF=0,bd=1e9;if(V3.z!==3)for(const t of v3cat('mine',t=>t.kind==='mine')){if(t.kind!=='mine'||!t.selected||t.dx==null||t.ly<0)continue;const K=v3kindAt(t.x,t.y),f=t.ly>0?t.ly:((V3.rampH&&V3.rampH.get(t.x+','+t.y))||0);
  const over=t.ly>0&&!!K&&K.kind==='wall'&&!!K.blocks&&Array.from({length:Math.max(0,v3stackTop(K)-Math.round(f))},(_,q)=>Math.round(f)+q).some(q=>v3stackHas(K,q));   /* inside the mountain, under rock of its own column (Gather.dm) */
  if(!((!t.ly&&inK(K))||over||(K&&(t.ly>0||K.kind!=='wall'&&K.kind!=='block')&&pit(t.x,t.y,f))))continue;const d=Math.hypot(t.dx-V3.cx,t.dy-V3.cy);if(d<bd){bd=d;U=t;UF=f}}
 const inMt=!!U;
 if(inMt){V3.mcFloor=UF;const lx=U.dx,ly=U.dy;V3.mcX=V3.mcX==null||!V3.mcR?lx:V3.mcX+(lx-V3.mcX)*Math.min(1,dt*8);V3.mcY=V3.mcY==null||!V3.mcR?ly:V3.mcY+(ly-V3.mcY)*Math.min(1,dt*8);const UK=v3kindAt(U.x,U.y),top=UF+(model&&model.gather?2.88:UK&&v3stackHas(UK,Math.round(UF)+1)?0.25:1.88);V3.mcTop=V3.mcTop==null||!V3.mcR?top:V3.mcTop+(top-V3.mcTop)*Math.min(1,dt*6)}   // just over its head (in a one-block room, a low slab a quarter block up: its floor shows at any tilt); with Gather on, over
   // its reach, three blocks up, so the blocks it can mine stand solid round it (the fade shows it, rts-feel outlines them); eases as it moves
 if(V3.planCut!=null){V3.mcX=V3.cx;V3.mcY=V3.cy;V3.mcTop=V3.planCut;V3.mcR=V3.planR||26}else{V3.mcR=(V3.mcR||0)+((inMt?8:0)-(V3.mcR||0))*Math.min(1,dt*4);if(V3.mcR<0.05)V3.mcR=0}   // Plan mode cuts the whole view at its level (pm module)
 if(!V3.mcR){gl3off(L);return null}
 // Round the camera's focus the rock is cut down to the ceiling, and on toward the camera the whole way (a trench, no
 // slope: the user wants nothing left standing between the eye and the hall), however far out the camera is.
 const R=V3.mcR,Y=V3.mcTop,Lc=Math.min(24,Math.max(8,V3.dist*Math.cos(V3.pitch)))*R/8;V3.mcDir=[Math.sin(V3.yaw)*Lc,Math.cos(V3.yaw)*Lc];V3.mcSlope=0;if(V3.planCut!=null)V3.mcDir=[0,0];
 V3.gl.uniform4f(L.mcut,V3.mcX,-V3.mcY,R,Y);V3.gl.uniform2f(L.mcdir,V3.mcDir[0],V3.mcDir[1]);V3.gl.uniform1f(L.mcslope,V3.mcSlope);
 const a=[],T=V3.terrain;if(!T)return a;
 const ex=Math.abs(V3.mcDir[0])+R,ey=Math.abs(V3.mcDir[1])+R,sec=[0.33,0.31,0.29,1],rmp=(x,y)=>(V3.rampH&&V3.rampH.get(x+','+y))||0;
 // How high each tile stands (rock to its top, a tunnel's roof from its ceiling up) and how high it shows in the cut.
 const solid=(x,y,K)=>K.kind==='wall'||K.kind==='block'?v3peakTop(x,y):K.kind==='built'?V3.STOREY:inK(K)?v3peakTop(x,y):0,
  from=(x,y,K)=>inK(K)?rmp(x,y)+(K.ceil||2):0,shown=(x,y,K)=>{const t=solid(x,y,K);return v3mcutTile(x,y)?Math.min(t,v3mcutLim(x,y)):t};
 // Whole tiles are cut (the shader cuts by tile too). A cap closes each cut tile of rock, roof or wall at its cut, and
 // where a cut tile meets rock standing higher the rock's section is drawn, so nothing looks hollow.
 for(let ty=Math.floor(V3.mcY-ey);ty<=Math.ceil(V3.mcY+ey);ty++)for(let tx=Math.floor(V3.mcX-ex);tx<=Math.ceil(V3.mcX+ex);tx++){
  if(!v3mcutTile(tx,ty))continue;const K=v3kindAt(tx,ty);if(!K)continue;const X=tx,Z=-ty,h=0.5,lim=v3mcutLim(tx,ty),tA=solid(tx,ty,K),fA=from(tx,ty,K);
  const capped=tA>lim+0.02&&(K.kind==='wall'||K.kind==='block'||K.kind==='built'||(inK(K)&&lim>fA));
  if(capped){
   // the section through rock (dark, faceted: four corners a little apart) or through a built wall (its stone)
   const rock=K.kind!=='built',c=rock?[0.3,0.28,0.26,1]:[0.5,0.48,0.45,1],y=k=>lim-0.012-MD.h(tx*2+k,ty,170)*0.035;
   const sw=[X-h,y(0),Z+h],se=[X+h,y(1),Z+h],ne=[X+h,y(2),Z-h],nw=[X-h,y(3),Z-h];
   tri(a,sw,se,ne,[0,1,0],MD.shade(c,0.92+MD.h(tx,ty,171)*0.16));tri(a,sw,ne,nw,[0,1,0],MD.shade(c,0.86+MD.h(tx,ty,172)*0.16))}
  const base=capped?lim-0.012:inK(K)?Math.max(fA,lim):null;if(base==null)continue;
  for(const [dx,dy] of [[1,0],[-1,0],[0,1],[0,-1]]){const nx=tx+dx,ny=ty+dy,N=v3kindAt(nx,ny);if(!N||!(N.kind==='wall'||N.kind==='block'||inK(N)))continue;
   const t1=shown(nx,ny,N),y0=Math.max(base,from(nx,ny,N));if(!(t1>y0+0.05))continue;
   const mx=X+dx*h,mz=Z-dy*h,ux=dy?h:0,uz=dx?h:0,c=MD.shade(sec,0.85+MD.h(nx,ny,173)*0.2);
   quad(a,[mx-ux,y0,mz-uz],[mx+ux,y0,mz+uz],[mx+ux,t1,mz+uz],[mx-ux,t1,mz-uz],[-dx,0,dy],c)}}
 return a}
// A tile inside the cut (the shader, the caps, the section walls and picking all go by this), and how low it is cut.
function v3mcutTile(tx,ty){return V3.mcR>0.5&&v3mcutDist(tx,ty)<=V3.mcR-0.6}
function v3mcutLim(tx,ty){const D=V3.mcDir||[0,0],dx=tx-V3.mcX,dz=-ty+V3.mcY,ll=D[0]*D[0]+D[1]*D[1],t=ll?Math.max(0,Math.min(1,(dx*D[0]+dz*D[1])/ll)):0;return V3.mcTop+Math.max(0,t*Math.sqrt(ll)-V3.mcR*0.5)*(V3.mcSlope||0)}
// Upper storeys over the view: near the floor point in the middle of the screen, a building's upper storey (V3.upper
// and its roofs) is cut away by whole tiles, there and on toward the camera, so its ground floor shows; the rest of it
// stays. It eases in and out like the mountain cut. Walls and their parapets are in the ground mesh and stay whole.
function v3upperCut(L,dt){const U=V3.upperTiles;let near=false,lx=0,ly=0;
 if(U&&U.size&&V3.z===1){[lx,ly]=v3mcutLook(0);const fx=Math.round(lx),fy=Math.round(ly);for(let dy=-3;dy<=3&&!near;dy++)for(let dx=-3;dx<=3;dx++)if(U.has((fx+dx)+','+(fy+dy))){near=true;break}}
 V3.ucR=(V3.ucR||0)+((near?6:0)-(V3.ucR||0))*Math.min(1,dt*4);if(V3.ucR<0.05){V3.ucR=0;return false}
 if(near||V3.ucX==null){V3.ucX=lx;V3.ucY=ly}
 const R=V3.ucR,Lc=Math.min(24,Math.max(8,V3.dist*Math.cos(V3.pitch)))*R/6;
 V3.gl.uniform4f(L.mcut,V3.ucX,-V3.ucY,R,V3.STOREY-0.05);V3.gl.uniform2f(L.mcdir,Math.sin(V3.yaw)*Lc,Math.cos(V3.yaw)*Lc);V3.gl.uniform1f(L.mcslope,0);return true}
function gl3off(L){V3.gl.uniform4f(L.mcut,0,0,0,0)}
// How far a tile is from the cut's capsule (its axis from the focus toward the camera).
function v3mcutDist(tx,ty){const D=V3.mcDir||[0,0],dx=tx-V3.mcX,dz=-ty+V3.mcY,ll=D[0]*D[0]+D[1]*D[1],t=ll?Math.max(0,Math.min(1,(dx*D[0]+dz*D[1])/ll)):0;return Math.hypot(dx-D[0]*t,dz-D[1]*t)}
// Rock fade (the camera near rock): rock geometry carries vertex alpha 0.94 (v3rockTag), and the shader thins it to a
// dither over your units and the point looked at, like trees, wherever v3rockHides finds rock between them and the eye.
function v3isRock(x,y){const K=v3kindAt(x,y);return !!K&&(K.kind==='wall'||K.kind==='block'||K.kind==='carve')}
// How high the rock stands on a tile: its top (v3groundAt), or over a tunnel or hall dug into a mountain, its roof.
function v3rockTopAt(x,y){const K=v3kindAt(x,y);return K&&K.roof&&K.kind!=='wall'?(K.ceil||2)+K.roof+0.4:v3groundAt(x,y)}
// The highest point of the rock as drawn on a tile (its faceted top's highest corner, V3.rockGeo), else v3rockTopAt.
function v3rockPeak(x,y){const G=V3.rockGeo&&V3.rockGeo.get(x+','+y);if(G&&G.c){let m=-1e9;for(const p of G.c)if(p[1]>m)m=p[1];return m}return v3rockTopAt(x,y)}
function v3rockTag(a,st){const f=a instanceof VA?a.f:a,n=a.length;for(let v=st+11;v<n;v+=12)f[v]=0.94}
// Does rock stand between a point (world x, y, z) and the eye? Steps along the line every 0.3 tiles until it is above the
// highest rock in view (and the roofs over tunnels: G.mx); a step under a rock tile's top (v3rockTopAt, with a little
// margin for the facets' jitter) is hidden.
function v3rockHides(px,py,pz,E){const G=V3.hgt;if(!G)return false;let top=G.mx;if(top==null){top=0;for(let k=0;k<G.H.length;k++)if(G.H[k]>top)top=G.H[k];const T=V3.terrain;if(T&&Array.isArray(T.kinds))for(const K of T.kinds)if(K&&K.roof&&K.kind!=='wall')top=Math.max(top,(K.ceil||2)+K.roof+0.4);G.mx=top}if(top<0.5)return false;
 const dx=E[0]-px,dy=E[1]-py,dz=E[2]-pz,n=Math.min(300,Math.ceil(Math.hypot(dx,dz)/0.3));
 for(let s=1;s<=n;s++){const f=s/n,y=py+dy*f;if(dy>0&&y>top+0.2)return false;const g=v3rockTopAt(Math.round(px+dx*f),Math.round(-(pz+dz*f)));if(g>0.5&&y<g+0.15)return true}return false}
// Is the rock or tree (kind 'rock' / 'tree') at this world point faded away at this point of the screen (CSS px)? Where
// the dither has taken about half of it (inside a fade slot's circle, in front of what the slot is over; a tree also close
// to the eye), it can't be clicked or hovered: picking (v3pickTile) passes through it to what is behind.
function v3fadedAt(mx,my,px,py,pz,kind){const F=V3.fpF,R=V3.fprF,m=V3.vp,c=$('world3d'),tree=kind==='tree';if(!F||!m||!c||!c.clientWidth)return false;
 if(tree&&V3.fnearV>0&&V3.eye&&Math.hypot(px-V3.eye[0],py-V3.eye[1],pz-V3.eye[2])<V3.fnearV*0.85)return true;
 const sx=mx/c.clientWidth*c.width,sy=c.height-my/c.clientHeight*c.height,z=px*m[2]+py*m[6]+pz*m[10]+m[14],w=px*m[3]+py*m[7]+pz*m[11]+m[15];if(w<=0)return false;const d=z/w*0.5+0.5;
 for(let i=0;i<(tree?12:13);i++){const r=F[i*4+2],k=tree?1:R?R[i]:0;if(k<0.5||r<=0||d>=F[i*4+3])continue;const ux=(sx-F[i*4])/r,uy=(sy-F[i*4+1])/r*0.7;if(ux*ux+uy*uy<0.6)return true}return false}
function v3frame(ts){V3.lastFrameAt=performance.now();v3kick();if(!V3.on){v3floatsTick();return}const gl=V3.gl,c=$('world3d');const dpr=Math.min(2,window.devicePixelRatio||1);
 // The buffer at the screen's own pixels (hud-rework 10-27, the owner: "less blurry ... if we are zoomed out a little",
 // "i want it look clean and detailed from zoom out to zoom in"). The page is CSS-zoomed for the HUD, so clientWidth is
 // in zoomed units and clientWidth*dpr was 1/zoom of the pixels the canvas covers: at a full screen's Auto HUD size (1.27
 // on a 1920x1200 screen) the scene was drawn at 79% and stretched (soft), at 0.8 at 125% (GPU spent for nothing). Full
 // screen at its own pixels held 60 fps (16.7-18 ms frames, 10-27); a governor that stepped it down on late frames only
 // softened the picture, those being mostly the window's compositing, not the 3D (fps60, 10-27). Picking and the
 // screen-space effects scale with the buffer (c.width/c.clientWidth, W and H).
 V3.px=dpr*(parseFloat(document.documentElement.style.zoom)||1);
 const W=Math.max(1,Math.floor(c.clientWidth*V3.px)),H=Math.max(1,Math.floor(c.clientHeight*V3.px));if(c.width!==W||c.height!==H){c.width=W;c.height=H}
 if(!W||!H)return;   // not laid out yet (loading, a hidden pane): nothing to draw, and the camera can't be inverted
 const dt=Math.min(0.1,(ts-(V3.lt||ts))/1000);V3.lt=ts;
 if(V3.cine){const C=V3.cine,k=Math.min(1,dt*1.2);V3.turnTo=null;V3.yaw+=dt*(C.spin||0);V3.dist+=((C.dist||V3.dist)-V3.dist)*k;V3.pitch+=((C.pitch??V3.pitch)-V3.pitch)*k}
 if(V3.keys.has('q')){V3.turnTo=null;V3.yaw-=dt*1.6;V3.userTurn=performance.now()}if(V3.keys.has('e')){V3.turnTo=null;V3.yaw+=dt*1.6;V3.userTurn=performance.now()}
 // Iso viewpoints are soft magnets: let go within ~10 degrees of a diagonal (or near the iso tilt) and the
 // camera settles the rest of the way; anywhere else it stays where you left it.
 if(v3isoOn()&&!V3.drag&&V3.turnTo==null&&!V3.keys.has('q')&&!V3.keys.has('e')&&performance.now()-(V3.userTurn||0)>350){const q=Math.PI/2,sy=Math.round((V3.yaw-q/2)/q)*q+q/2,k=Math.min(1,dt*5);if(Math.abs(sy-V3.yaw)<0.17)V3.yaw+=(sy-V3.yaw)*k;if(Math.abs(V3.ISOPITCH-V3.pitch)<0.12)V3.pitch+=(V3.ISOPITCH-V3.pitch)*k}
 if(V3.turnTo!=null){const d=V3.turnTo-V3.yaw;if(Math.abs(d)<0.01){V3.yaw=V3.turnTo;V3.turnTo=null}else V3.yaw+=d*Math.min(1,dt*10)}
 V3.cx+=(V3.tcx-V3.cx)*Math.min(1,dt*8);V3.cy+=(V3.tcy-V3.cy)*Math.min(1,dt*8);
 // a deferred terrain (v3terrainShift) is built once the camera has settled, or sooner if the view nears the built edge
 {const tw=performance.now();if(Math.abs(V3.tcx-(V3.ptx??V3.tcx))+Math.abs(V3.tcy-(V3.pty??V3.tcy))>0.001)V3.camMovedAt=ts;V3.ptx=V3.tcx;V3.pty=V3.tcy;if(V3.lvHold)v3levelWarm(8);else if(V3.pendTerr){const pm=V3.pendTerr,warm=v3chunksWarm(pm.terrain,4)&&v3layerWarm(pm.upper||null,V3.STOREY,Math.max(1,4-(performance.now()-tw)),V3.upperL||(V3.upperL={}))&&(pm.z!==3||v3layerWarm(pm.below||null,-v3skyGap(),Math.max(1,4-(performance.now()-tw)),V3.belowL||(V3.belowL={})));if(pm.warmAt?warm||performance.now()-pm.warmAt>250:ts-(V3.camMovedAt||0)>300&&warm||!v3inMargin(V3.terrain)){V3.pendTerr=null;v3applyTerrain(pm)}}v3bgWork(4-(performance.now()-tw))}   /* what is left of 4 ms after the chunks; none in a frame that applied a terrain */
 {const now=ts/1000,G=V3.gMove||(V3.gMove=new Set()),D=V3.gDirty;
  // Glide at the unit's own pace: each step takes as long as the time since its last step (like the map's glide).
  // Looked at only when it may have changed (30k units): every unit after a scene (new objects), those a moves push moved
  // (V3.gDirty), then each frame only the ones still gliding (V3.gMove). t._k: its entry, for the rest of the frame.
  // Steps play one after another from a short queue (owner 10-29: "a freeze and then a speed up on orders"; in the real app
  // the moves reach the page unevenly, gaps of 0.6-2 s, reports/polish-night-1026/gather-hitch): a new tile waits its turn
  // and is walked at the unit's own pace (its steps' lengths, averaged), by how many tiles behind the unit is drawn: a
  // little slower one behind, so the next is usually in by then, faster the further behind (up to 2.5x), so a late batch
  // is walked off quickly. Put where the server has it only on a real jump (a leap, a shadowstep: farther than walking
  // explains since the last moves came, up to 2.5 s) or 15+ tiles behind (owner 10-29: units teleported when they fell
  // behind; any 4 tiles behind used to put them there, which a late batch passed: reports/polish-night-1026/glide-catchup).
  // A step's length is the server's own (game time) over V3.rate, the pace the server keeps (027 v3rateFrom): a server
  // running at 60% of real time has its units walk at 60%, steadily (reports/polish-night-1026/server-pace).
  const tl=(ax,ay,bx,by)=>Math.max(Math.abs(ax-bx),Math.abs(ay-by));
  const seg=(k,t0)=>{const s=k.q.shift(),L=Math.max(1,tl(k.dx,k.dy,s[0],s[1]));let b=L,px=s[0],py=s[1];for(const e of k.q){b+=tl(px,py,e[0],e[1]);px=e[0];py=e[1]}k.fx=k.dx;k.fy=k.dy;k.tx=s[0];k.ty=s[1];k.dur=Math.max(0.12,Math.min(1.5*L,(k.g||s[2])*L*(b<=1?1.05:b<=2?0.92:Math.max(0.4,2.2/b))));k.t0=t0};
  const chk=t=>{let k=V3.disp.get(t.key);
  if(!k){k={dx:t.x,dy:t.y,fx:t.x,fy:t.y,tx:t.x,ty:t.y,t0:now,dur:0.3,last:now,born:now,off:Math.random()};V3.disp.set(t.key,k)}if(t._k!==k)v3hid(t,'_k',k);
  const q=k.q,qx=q&&q.length?q[q.length-1][0]:k.tx,qy=q&&q.length?q[q.length-1][1]:k.ty;
  if(qx!==t.x||qy!==t.y){const g=t.gap>0?Math.max(0.12,Math.min(1.5,t.gap/1000/(V3.rate||1))):Math.max(0.12,Math.min(0.7,now-k.last)),J=tl(qx,qy,t.x,t.y);if(J>3&&J>Math.min(2.5,now-(V3.gAt??now))/(k.g||g)+2||tl(k.dx,k.dy,t.x,t.y)>15){k.q=null;k.dx=k.fx=k.tx=t.x;k.dy=k.fy=k.ty=t.y;k.dur=0.001;k.t0=now}else{k.g=k.g?k.g*0.6+g*0.4:g;(k.q||(k.q=[])).push([t.x,t.y,g]);if(now-k.t0>=k.dur)seg(k,now)}k.last=now;k.n=(k.n||0)+1}G.add(t)};
  if(V3.gAll){V3.gAll=0;G.clear();if(D)D.clear();for(const t of V3.things)chk(t);V3.gAt=now}else if(D&&D.size){for(const t of D)chk(t);D.clear();V3.gAt=now}   /* V3.gAt: when the last moves came */
  for(const t of G){const k=t._k;let p=Math.min(1,(now-k.t0)/k.dur);if(p>=1&&k.q&&k.q.length){k.dx=k.tx;k.dy=k.ty;seg(k,Math.max(k.t0+k.dur,now-0.05));p=Math.min(1,(now-k.t0)/k.dur)}k.dx=k.fx+(k.tx-k.fx)*p;k.dy=k.fy+(k.ty-k.fy)*p;t.dx=k.dx;t.dy=k.dy;if(p>=1&&!(k.q&&k.q.length))G.delete(t)}}   /* the next queued tile straight on from the last one's end */
 v3chase(dt);if(!V3.sizeAt||ts-V3.sizeAt>700){V3.sizeAt=ts;v3sizeCheck()}
 // Low views look at chest height. The aim height follows the ground the focus stands on, never rock beside it (a cliff
 // next to the focus lifted the whole camera): a locked unit's own footing while it is at the focus, else the open ground
 // in the 5x5 tiles round the focus; only well inside a mountain (little open ground round it) 0.6 of the rock's top, as
 // before. Inside a mountain cut, the hall's floor. It eases, so a real change of level (a ramp up onto a wall) glides.
 const low=1-Math.max(0,Math.min(1,(V3.pitch-0.25)/0.6));let gA=0,gW=0,nW=0;if(!(V3.mcR>0.5&&V3.mcFloor!=null)){const fx=Math.round(V3.cx),fy=Math.round(V3.cy);for(let dy=-2;dy<=2;dy++)for(let dx=-2;dx<=2;dx++){const g=v3groundAt(fx+dx,fy+dy);gA+=g;if(!v3isRock(fx+dx,fy+dy)){gW+=g;nW++}}gA/=25}
 // Locked on a flyer (v3chase): aim at it up in the air (its rock top plus its height), so it stays in view however high.
 const LT=V3.lockT,LD=LT&&LT.key&&V3.disp.get(LT.key),flyAim=LD&&(LD.alt||0)>0.3?(LD.lift||0)+(LD.alt||0):null;
 const foot=LT&&LT.dx!=null&&flyAim==null&&Math.hypot(LT.dx-V3.cx,LT.dy-V3.cy)<1.6?(LT.ly||0)+((V3.rampH&&V3.rampH.get(LT.x+','+LT.y))||0):null,wk=Math.min(1,nW/6),gS=foot!=null?foot:gA*0.6*(1-wk)+(nW?gW/nW:0)*wk;
 const aimH=flyAim!=null?Math.max(flyAim,gS+low):V3.mcR>0.5&&V3.mcFloor!=null?V3.mcFloor+low:gS+low*1.0;V3.camH=V3.camH==null?aimH:V3.camH+(aimH-V3.camH)*Math.min(1,dt*2.5);const tgt=[V3.cx,V3.camH,-V3.cy];const cp=Math.cos(V3.pitch),sp=Math.sin(V3.pitch);const iso=v3isoOn(),fov=iso?V3.ISOFOV:0.8,ed=iso?V3.dist*Math.tan(0.4)/Math.tan(fov/2):V3.dist;const eye=[tgt[0]+Math.sin(V3.yaw)*cp*ed,tgt[1]+sp*ed,tgt[2]+Math.cos(V3.yaw)*cp*ed];
 // The eye keeps above the rock round it: a floor from the rock tops (tunnel roofs too) in the 5x5 tiles round the eye,
 // each tapering off over the two tiles beyond it, so it changes smoothly as the eye moves (turning beside a ridge no
 // longer bumps), and eased the same up and down. It never snaps, only when the view jumps. Rock right at the eye fades.
 {const ex=eye[0],ey=-eye[2],ix=Math.round(ex),iy=Math.round(ey);let fl=0;for(let dy=-2;dy<=2;dy++)for(let dx=-2;dx<=2;dx++){const g=v3rockPeak(ix+dx,iy+dy);if(g<=0.05)continue;const d=(Math.max(Math.abs(ex-ix-dx),Math.abs(ey-iy-dy))-0.5)/2,w=d<=0?1:d>=1?0:1-d*d*(3-2*d);if(g*w>fl)fl=g*w}
  const want=fl+0.7,c=V3.eyeG,jump=V3.eyeAx==null||Math.abs(V3.eyeAx-V3.cx)+Math.abs(V3.eyeAy-V3.cy)>3;V3.eyeAx=V3.cx;V3.eyeAy=V3.cy;V3.eyeG=c==null||jump?want:c+(want-c)*Math.min(1,dt*5);if(eye[1]<V3.eyeG)eye[1]=V3.eyeG}
 // Rock between the camera and what it looks at no longer pulls the camera in (it came in at once and eased back out, so
 // it pumped as you moved): that rock fades instead, the way trees do (the rock fade below, v3rockHides, and the shader).
 V3.eye=eye;
 const proj=M4.persp(fov,W/H,iso?Math.max(0.3,ed*0.2):0.3,600+ed),view=M4.look(eye,tgt,[0,1,0]);const vp=M4.mul(proj,view);V3.vp=vp;V3.frPl=v3planes(vp,V3.frPl);V3.inv=M4.inv(vp);v3floatsTick();   /* the damage numbers with this frame's camera (drawn first, they lagged a frame behind a zoom or turn) */
 gl.viewport(0,0,W,H);const under=V3.z===2||V3.z===4,sky=V3.z===3;const G=V3.G=v3grade(),fog=under?[0.07,0.055,0.045]:sky?M3mix([0.72,0.83,0.95],G.fog,0.35):G.fog;
 if(V3.lift){V3.liftT=Math.min(1,(V3.liftT||0)+dt/0.7);const e=1-Math.pow(1-V3.liftT,3);V3.curLift=V3.lift*(1-e);if(V3.liftT>=1){V3.lift=0;V3.curLift=0}}else V3.curLift=0;const fade=V3.lift?0.35+0.65*Math.min(1,V3.liftT||0):1;gl.clearColor(fog[0],fog[1],fog[2],1);gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);gl.enable(gl.DEPTH_TEST);gl.disable(gl.BLEND);
 const L=V3.loc;gl.uniformMatrix4fv(L.mvp,false,vp);gl.uniform3fv(L.eye,eye);const lv=v3sunDir(),ll=1;gl.uniform1f(L.fill,under?0:V3.night?0.22-0.12*Math.max(0,Math.min(1,(G.nk-0.55)/0.45)):0.22*(1-Math.min(1,Math.max(0,(lv[1]-0.25)/0.55))));gl.uniform3f(L.light,lv[0]/ll,lv[1]/ll,lv[2]/ll);gl.uniform3f(L.lightf,lv[0],lv[1],lv[2]);gl.uniform1f(L.tm,(ts/1000)%600);gl.uniform1f(L.tmv,(ts/1000)%600);gl.uniform1f(L.gfl,V3.curLift||0);gl.uniform1f(L.clk,(V3.z===1||V3.z===3)&&!V3.night&&!V3.noClouds&&!V3.lite?0.32*Math.min(1,G.dirk*1.4):0);gl.uniform3fv(L.fogc,fog);{const fn=under?V3.dist*1.1:Math.min(380,V3.dist*(iso?0.7:4)+(iso?0:40)+low*55),ff=under?V3.dist*2.8:Math.min(560,Math.max(fn+60,V3.dist*(iso?11:9)+(iso?60:160)+low*250));gl.uniform1f(L.fogn,fn+ed-V3.dist);gl.uniform1f(L.fogf,ff+ed-V3.dist)}gl.uniform1f(L.amb,V3.amb=(under?0.78:sky?1.05*G.amb:G.amb)*fade);gl.uniform3fv(L.sunc,under?[1,0.95,0.86]:G.sunc);gl.uniform3fv(L.skyc,under?[1,0.97,0.92]:G.skyc);gl.uniform3fv(L.unl,under?[1,0.97,0.93]:G.unl);gl.uniform3fv(L.seas,under?[0,0,0]:G.seas);gl.uniform1f(L.gon,V3.gtex&&V3.gtex.ok&&V3.etex&&V3.etex.ok&&V3.stex&&V3.stex.ok?1:0);gl.uniform2f(L.gorg,Math.floor(tgt[0]/16)*16,Math.floor(tgt[2]/16)*16);gl.uniform1f(L.night,under?2:G.nk);v3fogFrame(L,dt,under);v3fireLights(tgt,under);gl.uniform1f(L.lift,V3.curLift);gl.uniform1f(L.alpha,1);gl.uniform4f(L.tint,0,0,0,0);
 // The sun's shadows (by day, on the surface and the sky layer): the terrain drawn from the sun into the shadow map,
 // its centre kept on the map's texel grid so edges don't crawl as the camera moves.
 {const sun=[lv[0]/ll,lv[1]/ll,lv[2]/ll];let lvp=null;
  if(V3.sh&&(V3.z===1||V3.z===3)&&!V3.lite){   /* V3.lite (a measuring switch): no sun-shadow pass, clouds, foam, glows, ambience or vignette */const R=Math.max(18,Math.min(80,V3.dist*1.5+10)),D=R+50,tx=2*R/V3.SHADOW,c0=[tgt[0],0,tgt[2]],at=c=>M4.look([c[0]+sun[0]*D,c[1]+sun[1]*D,c[2]+sun[2]*D],c,[0,1,0]);
   let Vl=at(c0);const ax=[Vl[0],Vl[4],Vl[8]],ay=[Vl[1],Vl[5],Vl[9]],px=c0[0]*ax[0]+c0[2]*ax[2],py=c0[0]*ay[0]+c0[2]*ay[2],dx=Math.round(px/tx)*tx-px,dy=Math.round(py/tx)*tx-py;
   Vl=at([c0[0]+ax[0]*dx+ay[0]*dy,ax[1]*dx+ay[1]*dy,c0[2]+ax[2]*dx+ay[2]*dy]);const n=1,f=D+R+30;lvp=M4.mul([1/R,0,0,0,0,1/R,0,0,0,0,-2/(f-n),0,0,0,-(f+n)/(f-n),1],Vl);
   // redrawn only when what it shows changed: the sun, the snapped centre, the terrain, the layer's lift, a texture loaded
   // (it was a 2048x2048 pass over all the terrain every frame)
   const S=V3.sh,skey=lvp.map(v=>Math.round(v*1e5)).join(',')+'|'+(V3.curLift||0)+'|'+(V3.tmeshGen||0)+'|'+V3.tmesh.reduce((n,m)=>n+(m.tex&&(v3tex(m.tex)||{}).ok?1:0),0);
   if(skey!==V3.shKey){V3.shKey=skey;gl.bindFramebuffer(gl.FRAMEBUFFER,S.fb);gl.viewport(0,0,V3.SHADOW,V3.SHADOW);gl.clearColor(1,1,1,1);gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);gl.useProgram(S.pr);gl.uniformMatrix4fv(S.lmvp,false,lvp);gl.uniform1f(S.lift,V3.curLift||0);
   for(const m of V3.tmesh)v3drawShadow(m.buf,m.count,m.tex?v3tex(m.tex):null);
   gl.bindFramebuffer(gl.FRAMEBUFFER,null)}gl.viewport(0,0,W,H);gl.useProgram(V3.pr);gl.activeTexture(gl.TEXTURE4);gl.bindTexture(gl.TEXTURE_2D,S.tx);gl.activeTexture(gl.TEXTURE0)}
  gl.uniform1f(L.son,lvp?1:0);if(lvp)gl.uniformMatrix4fv(L.lvp,false,lvp);
  // the sky behind everything
  const K=V3.skyp;if(K&&!under){gl.useProgram(K.pr);gl.disable(gl.DEPTH_TEST);gl.depthMask(false);gl.uniformMatrix4fv(K.inv,false,V3.inv);gl.uniform3fv(K.eye,eye);gl.uniform3fv(K.sun,sun);gl.uniform3fv(K.hz,fog);
   gl.uniform3fv(K.zen,V3.z===3?M3mix([0.36,0.56,0.9],G.zen,0.35):G.zen);gl.uniform1f(K.night,G.nk);gl.uniform1f(K.time,ts/1000);gl.bindBuffer(gl.ARRAY_BUFFER,K.buf);gl.vertexAttribPointer(K.p,2,gl.FLOAT,false,8,0);gl.enableVertexAttribArray(K.p);for(const a of [L.n,L.uv,L.col])if(a>=0&&a!==K.p)gl.disableVertexAttribArray(a);gl.drawArrays(gl.TRIANGLES,0,3);   /* only its own input on: a terrain buffer let go since the last frame (a level change) left the others pointing at nothing, and the sky was not drawn that frame (WebGL: no buffer bound to an enabled attribute); v3draw turns them on again */
   gl.depthMask(true);gl.enable(gl.DEPTH_TEST);gl.useProgram(V3.pr)}}
 // Trees and rock thin out over your units (the selected first, then those nearest the middle; up to 8) and over the
 // workshops and stations nearest the middle (up to 4); trees also right in front of the camera when zoomed in close.
 // Rock only where it really stands between the eye and that unit (v3rockHides), and also over the point looked at
 // (slot 12), each eased in and out (fpr, per slot): a mountain top in front of a flyer never opens.
 {const F=V3.fpF&&V3.fpF.length===52?V3.fpF:(V3.fpF=new Float32Array(52)),R=V3.fprF||(V3.fprF=new Float32Array(13)),pj=v=>{const m=vp,x=v[0]*m[0]+v[1]*m[4]+v[2]*m[8]+m[12],y=v[0]*m[1]+v[1]*m[5]+v[2]*m[9]+m[13],z=v[0]*m[2]+v[1]*m[6]+v[2]*m[10]+m[14],w=v[0]*m[3]+v[1]*m[7]+v[2]*m[11]+m[15];return w>0?[(x/w*0.5+0.5)*W,(y/w*0.5+0.5)*H,z/w*0.5+0.5]:null};let n=0;
  F.fill(0);R.fill(0);const surf=V3.z===1||V3.z===3,RW=V3.fprW||(V3.fprW=new Map()),RN=V3.fprN||(V3.fprN=new Map()),k7=Math.min(1,dt*10),rw=(key,on)=>{const w0=RW.get(key)||0,w=w0+((on?1:0)-w0)*k7;if(w>0.01)RN.set(key,w);return w>0.01?w:0},
   hid=(x,y,z)=>v3rockHides(x,y+0.3,z,eye)||v3rockHides(x,y+0.9,z,eye)||v3rockHides(x,y+1.5,z,eye);
  if(surf)for(const [t] of v3nearest8()){if(n>=8)break;const kd=V3.disp.get(t.key),gy=t.ly>0?t.ly:kd&&(kd.alt||0)>0.3?(kd.lift||0)+kd.alt:v3groundAt(t.dx,t.dy),p0=pj([t.dx,gy+0.55,-t.dy]),p1=pj([t.dx,gy+1.55,-t.dy]);if(!p0||!p1)continue;F.set([p0[0],p0[1],Math.max(14,Math.hypot(p1[0]-p0[0],p1[1]-p0[1])*1.25),p0[2]],n*4);R[n]=rw(t.key,hid(t.dx,gy,-t.dy));n++}
  // and over the workshops and stations nearest the middle (up to 4), wider: a building under a canopy stays in sight
  if(surf){let m=0;for(const [t] of v3cat('station',t=>t.kind==='station').filter(t=>t.dx!=null&&!t.ly&&Math.abs(t.dx-V3.cx)<18&&Math.abs(t.dy-V3.cy)<14).map(t=>[t,Math.hypot(t.dx-V3.cx,t.dy-V3.cy)]).sort((p,q)=>p[1]-q[1])){if(m>=4)break;const gy=v3groundAt(t.dx,t.dy),p0=pj([t.dx,gy+0.45,-t.dy]),p1=pj([t.dx,gy+1.45,-t.dy]);if(!p0||!p1)continue;F.set([p0[0],p0[1],Math.max(20,Math.hypot(p1[0]-p0[0],p1[1]-p0[1])*1.7),p0[2]],(8+m)*4);R[8+m]=rw(t.key,hid(t.dx,gy,-t.dy));m++}}
  // the point looked at (slot 12, rock only), when it is open ground: not over a mountain (the aim is inside its top) nor
  // in a hall (the mountain cut opens those)
  if(surf&&!(V3.mcR>0.5)){const fx=Math.round(V3.cx),fy=Math.round(V3.cy),on=!(v3isRock(fx,fy)&&tgt[1]<v3groundAt(fx,fy)+0.1)&&(v3rockHides(tgt[0],tgt[1],tgt[2],eye)||v3rockHides(tgt[0],tgt[1]-0.6,tgt[2],eye)),w=rw('@focus',on);
   if(w>0){const p0=pj(tgt),p1=pj([tgt[0]+Math.cos(V3.yaw)*1.8,tgt[1],tgt[2]-Math.sin(V3.yaw)*1.8]);if(p0&&p1){F[48]=p0[0];F[49]=p0[1];F[50]=Math.max(30,Math.hypot(p1[0]-p0[0],p1[1]-p0[1]));F[51]=p0[2];R[12]=w}}}
  RW.clear();V3.fprW=RN;V3.fprN=RW;
  gl.uniform4fv(L.fp,F.s48||(F.s48=F.subarray(0,48)));{const RP=V3.rpF||(V3.rpF=new Float32Array(24)),RQ=V3.rpW||(V3.rpW=new Float32Array(6));let q=0;for(let i=0;i<13&&q<6;i++)if(R[i]>0&&F[i*4+2]>0){for(let k=0;k<4;k++)RP[q*4+k]=F[i*4+k];RQ[q++]=R[i]}gl.uniform4fv(L.rp,RP);gl.uniform1fv(L.rpw,RQ);gl.uniform1i(L.rpn,q)}gl.uniform1f(L.fnear,V3.fnearV=V3.dist<10?Math.max(0.5,Math.hypot(eye[0]-tgt[0],eye[1]-tgt[1],eye[2]-tgt[2])-V3.dist*0.6):0)}
 const cutting=V3.mode==='cut'&&V3.z!==3;gl.uniform4f(L.cut,tgt[0],tgt[2],Math.sin(V3.yaw),Math.cos(V3.yaw));
 gl.uniform1f(L.cutMode,cutting?2:0);for(const m of V3.below||[]){v3draw(m.buf,m.count,m.tex?v3tex(m.tex):null,m.color)}gl.uniform1f(L.cutMode,cutting?1:0);
 const mcap=v3mountainCut(L,dt);for(const m of V3.tmesh){const tex=m.tex?v3tex(m.tex):null;v3draw(m.buf,m.count,tex,m.color)}gl.uniform1f(L.cutMode,0);gl.uniform4f(L.mcut,0,0,0,0);
 if(mcap&&mcap.length){gl.bindBuffer(gl.ARRAY_BUFFER,V3.dyn);v3up(mcap);v3draw(V3.dyn,mcap.length/12,null,[1,1,1])}
 {const fl=V3.z===3?(V3.curLift||0)-v3skyGap():null;if(fl!=null)gl.uniform1f(L.lift,fl);   /* up on the Sky level, the surface's far land and horizon under it (world-look 2026-10-25) */
 gl.uniform2f(L.fogout,0,1);for(const m of V3.far||[])v3draw(m.buf,m.count,null,[1,1,1]);
 gl.uniform2f(L.fogout,0,0);gl.uniform1f(L.faron,0);if(V3.z===1||V3.z===3){const H=v3horizon(tgt[0],tgt[2]);if(H)v3draw(H.buf,H.count,null,[1,1,1])}gl.uniform2f(L.fogout,0,1);gl.uniform1f(L.faron,V3.farFogOn?1:0);if(fl!=null)gl.uniform1f(L.lift,V3.curLift||0)}
 // Far-off figures: your units beyond the detailed area and what they can see, a simple body and head. (The gold arrow
 // over each of your own went, the user 2026-10-25: "the arrows are to much"; the focus button and a double click in the
 // Company list find them.) Built when the list or the ground under them changes, into their own buffer, not each frame.
 if(V3.z===1&&V3.farUnits&&V3.farUnits.length&&V3.dyn){gl.uniform1f(L.fogon,0);let FF=V3.farFig;if(!FF||FF.gl!==gl)FF=V3.farFig={gl,buf:gl.createBuffer(),n:0};
  if(FF.of!==V3.farUnits||FF.hg!==V3.hgt||FF.fh!==V3.farH||FF.tg!==V3.terrGen){FF.of=V3.farUnits;FF.hg=V3.hgt;FF.fh=V3.farH;FF.tg=V3.terrGen;FF.builds=(FF.builds||0)+1;
   const a=[],C={m:[0.3,0.75,0.35,1],p:[0.35,0.55,0.95,1],a:[0.62,0.46,0.3,1],n:[0.85,0.25,0.2,1]};
   for(const u of V3.farUnits){const x=u[0],z=-u[1],c=C[u[2]]||C.n,y=v3groundAt(u[0],u[1]);const animal=u[2]==='a';
    if(animal){box(a,x,z,y,y+0.45,0.28,c);box(a,x+0.25,z,y+0.3,y+0.62,0.13,MD.shade(c,1.1))}else{box(a,x,z,y,y+0.75,0.18,c);box(a,x,z,y+0.75,y+1.05,0.14,MD.shade(c,1.15))}}
   FF.a=V3.farFigCheck?a:null;gl.bindBuffer(gl.ARRAY_BUFFER,FF.buf);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(a),gl.STATIC_DRAW);FF.n=a.length/12}
  v3draw(FF.buf,FF.n,null,[1,1,1]);gl.uniform1f(L.fogon,V3.fogLive?1:0)}
 const selTiles=v3cat('mine',t=>t.kind==='mine').filter(t=>t.selected).map(t=>t.x+','+t.y);
 const lifted=V3.mode==='cut'||V3.dist<11||V3.mcR>0.5||selTiles.some(k=>V3.upperTiles&&V3.upperTiles.has(k));
 if(!lifted){const uc=v3upperCut(L,dt);for(const m of V3.upper||[])v3draw(m.buf,m.count,m.tex?v3tex(m.tex):null,m.color);for(const r of V3.roofsUp||[])v3draw(r.buf,r.count,null);if(uc)gl3off(L)}else V3.ucR=0
 // Roofs: while playing, every roof on screen is see-through, so the insides of houses show; zoomed far out (an
 // overview) they turn solid; right in close they're gone. Each fades rather than pops.
 if(V3.mode!=='cut'){const ra=V3.roofA||(V3.roofA=new Map()),Lc=V3.loc,d=V3.dist,want=d<12?0.2*Math.max(0,(d-9)/3):d<24?0.2:d<30?0.2+0.8*(d-24)/6:1;
  for(const r of V3.roofs||[]){const cur=ra.has(r.key)?ra.get(r.key):want,a=cur+(want-cur)*Math.min(1,dt*7);ra.set(r.key,a);if(a<0.03)continue;
   if(a>0.985){v3draw(r.buf,r.count,null);continue}gl.enable(gl.BLEND);gl.blendFunc(gl.SRC_ALPHA,gl.ONE_MINUS_SRC_ALPHA);gl.depthMask(false);gl.uniform1f(Lc.alpha,a);v3draw(r.buf,r.count,null);gl.uniform1f(Lc.alpha,1);gl.depthMask(true);gl.disable(gl.BLEND)}}
 {const ga=[];const col={ok:[0.35,0.9,0.45,1],warn:[0.95,0.8,0.3,1],bad:[0.95,0.3,0.25,1],plan:[0.4,0.75,1,1]};
  const piece=(x,y,c,kind)=>{const X=x,Z=-y;if(kind==='workshop'){boxr(ga,X-1.45,X+0.45,Z-0.45,Z+0.45,0,0.9,c);return}if(kind==='floor'||kind==='bridge')boxr(ga,X-0.48,X+0.48,Z-0.48,Z+0.48,0,0.06,c);else if(kind==='dig')boxr(ga,X-0.5,X+0.5,Z-0.5,Z+0.5,0,1.45,c);else boxr(ga,X-0.2,X+0.2,Z-0.5,Z+0.5,0,V3.STOREY,c)};
  // Planned pieces (construction tasks) show as their own picture, see-through: plain while being built, amber while
  // waiting for material, grey while nobody is assigned. Walls stand up as a box wearing it; the rest lie flat.
  const tg=new Map(),tint={working:[1,1,1,1],waiting:[1,0.78,0.38,1],unassigned:[0.62,0.62,0.62,1]};
  for(const b of V3.blueprints||[]){if(!b.tex||b.kind==='dig'){piece(b.x,b.y,col.plan,b.kind);continue}const c=tint[b.state]||tint.working,X=b.x,Z=-b.y,gy=v3groundAt(b.x,b.y);let a=tg.get(b.tex);if(!a){a=[];tg.set(b.tex,a)}
   if(b.kind==='wall')boxr(a,X-0.5,X+0.5,Z-0.5,Z+0.5,gy,gy+V3.STOREY,c);else quad(a,[X-0.5,gy+0.04,Z+0.5],[X+0.5,gy+0.04,Z+0.5],[X+0.5,gy+0.04,Z-0.5],[X-0.5,gy+0.04,Z-0.5],[0,1,0],c,[0,1,1,1,1,0,0,0])}
  if(V3.shop&&V3.hoverTile){const t=V3.hoverTile;const c=col[v3shopOk(t)];if(V3.shop.two)piece(t.x,t.y,c,'workshop');else boxr(ga,t.x-0.45,t.x+0.45,-t.y-0.45,-t.y+0.45,0,0.7,c)}
  else if(V3.build&&V3.hoverTile){const tiles=V3.paint?v3paintTiles(V3.paint,V3.hoverTile,V3.build.kind):[V3.hoverTile];for(const t of tiles)piece(t.x,t.y,col[v3ghostOk(t,V3.build.kind)],V3.build.kind)}
  if(window.jbGhosts)try{jbGhosts(ga)}catch(e){}   // work zones outlined on the ground, and a zone being dragged (job board)
  if(ga.length){gl.enable(gl.BLEND);gl.blendFunc(gl.SRC_ALPHA,gl.ONE_MINUS_SRC_ALPHA);gl.depthMask(false);gl.uniform1f(L.alpha,0.42);gl.bindBuffer(gl.ARRAY_BUFFER,V3.dyn);v3up(ga);v3draw(V3.dyn,ga.length/12,null);gl.uniform1f(L.alpha,1);gl.depthMask(true);gl.disable(gl.BLEND)}
  if(tg.size){gl.enable(gl.BLEND);gl.blendFunc(gl.SRC_ALPHA,gl.ONE_MINUS_SRC_ALPHA);gl.depthMask(false);gl.uniform1f(L.alpha,0.55);for(const [k,a] of tg){gl.bindBuffer(gl.ARRAY_BUFFER,V3.dyn);v3up(a);v3draw(V3.dyn,a.length/12,v3tex(k))}gl.uniform1f(L.alpha,1);gl.depthMask(true);gl.disable(gl.BLEND)}}
 // billboards
 const right=[Math.cos(V3.yaw),0,-Math.sin(V3.yaw)];const groups=V3.vaG||(V3.vaG=new Map());if(groups.size>300)for(const [k,a] of groups)if(!a.length)groups.delete(k);for(const a of groups.values())a.length=0;const add=(k,arr)=>{let a=groups.get(k);if(!a){a=new VA();groups.set(k,a)}a.addArr(arr)};
 const IG=V3.vaI||(V3.vaI=new Map());if(IG.size>300)for(const [k,a] of IG)if(!a.length){IG.delete(k);V3.vaGen=(V3.vaGen||0)+1}for(const a of IG.values())a.length=0;const iadd=(M,k)=>{let a=M.get(k);if(!a){a=new VA();M.set(k,a)}return a};   /* the pictures as records, by sheet (v3drawInst) */
 V3.breaths=[];   // dragons' breath this frame (v3drawBeast), drawn with the models
 const VS=V3.vaS||(V3.vaS={bars:new VA(),rings:new VA(),shadows:new VA(),contact:new VA(),sil:new Map(),castG:new Map(),castB:new Map()}),bars=VS.bars.reset(),rings=VS.rings.reset(),shadows=VS.shadows.reset(),contact=VS.contact.reset(),sil=VS.sil,castG=VS.castG,castB=VS.castB,BL=(V3.barL||(V3.barL=[])),flashG=VS.flashG||(VS.flashG=new Map()),fxg=new Map(),vapours=[],flames=[],cauldrons=[],runes=[],crops=[],banners=[],sieges=[],objs=[],fishspots=[],stalls=[],foods=[],vomits=[],clinics=[],optables=[],taverns=[],graveyards=[],graves=[],traces=[],mouths=[],exits=[],vents=[],gates=[];
 const byRef=V3.byRef||(V3.byRef=new Map());if(V3.byRefOf!==V3.things){V3.byRefOf=V3.things;byRef.clear();for(const o of V3.things)if(o.ref)byRef.set(o.ref,o)}   /* once a scene */
 // Units' pictures laid on the ground away from the sun (or the moon) as their shadows, Diablo-like: the shadow's foot
 // runs across the light, its length from the sun's height. Not underground, where only the contact shadow shows.
 for(const [k,a] of sil)if(a.length)a.length=0;else if(sil.size>200){sil.delete(k);V3.vaGen=(V3.vaGen||0)+1}for(const [k,a] of castG)if(a.length)a.length=0;else if(castG.size>200){castG.delete(k);V3.vaGen=(V3.vaGen||0)+1}for(const [k,a] of castB)if(a.length)a.length=0;else if(castB.size>200)castB.delete(k);for(const [k,a] of flashG)if(a.length)a.length=0;else if(flashG.size>60)flashG.delete(k);
 BL.length=0;{const q=Math.max(0,Math.min(1,(V3.pitch-0.9)/0.32)),k=0.72*q*q*(3-2*q),sp=Math.sin(V3.pitch),cp=Math.cos(V3.pitch),lx=-Math.sin(V3.yaw)*sp*k,ly=1+(cp-1)*k,lz=-Math.cos(V3.yaw)*sp*k,l=Math.hypot(lx,ly,lz)||1;V3.lean=[lx/l,ly/l,lz/l]}
 const castOn=(V3.z===1||V3.z===3)&&!under;let csx=-lv[0],csz=-lv[2];const chz=Math.hypot(csx,csz)||1;csx/=chz;csz/=chz;const clen=Math.max(0.3,Math.min(1.45,chz/Math.max(0.2,lv[1])));let cpx=-csz,cpz=csx;if(cpx*right[0]+cpz*right[2]<0){cpx=-cpx;cpz=-cpz}V3.cast={on:castOn,sx:csx,sz:csz,len:clen,px:cpx,pz:cpz,g:castB};   /* for v3drawBeast (its shadows are triangles) */V3.iU={r:right,l:V3.lean,s:[cpx,cpz,csx,csz]};const rcEp=V3.yaw+','+V3.pitch+','+clen+','+castOn+','+V3.models+','+V3.unitModels+','+V3.hpRing+','+!!V3.hpOff+','+(V3.terrGen||0)+','+(V3.tmeshGen||0)+','+V3.z+','+under;   /* a hit's flash no longer in it: each new hit threw away every unit's kept records (the owner 10-28: big-battle lag); a unit flashing now draws afresh (below) */   /* the cached records' frame key (v3rcMake) */
 for(const t of V3.things){if(t.pool){v3poolDraw(t,add);continue}if(!v3visible(t))continue;if(t._pl===undefined)v3hid(t,'_pl',v3plain(t));   /* once a scene: a plain unit */
  if(t._pl&&V3.cull!==false&&v3culled(t))continue;   /* wholly outside the view: nothing of it can show */
  if(t._pl){const kd=t._k,R=kd&&kd.rc,fz=V3.flash&&V3.flash.size?V3.flash.get(t.x+','+t.y):null;if(R&&!(fz!=null&&ts>=fz-16&&ts<fz+120)&&R.ob===t&&R.og===V3.sceneGen&&R.ep===rcEp&&R.t0===kd.t0&&R.x===t.x&&R.y===t.y&&R.dir===t.dir&&R.sel===t.selected&&R.ly===t.ly&&R.dx===t.dx&&R.dy===t.dy&&R.px===t.px&&R.py===t.py&&!R.fb&&!t.climb&&!t.drunk){v3rcEmit(R,IG,sil,castG,contact,rings,BL,iadd);if(R.g3)g3put(R);t.top3d=R.top;continue}
   const Wc=kd&&kd.wc;if(Wc&&Wc.ob===t&&Wc.og===V3.sceneGen&&Wc.ep===rcEp&&Wc.t0===kd.t0&&Wc.n===kd.n&&Wc.x===t.x&&Wc.y===t.y&&Wc.dir===t.dir&&Wc.sel===t.selected&&Wc.ly===t.ly&&Wc.px===t.px&&Wc.py===t.py&&!Wc.fb&&!t.climb&&!t.drunk&&v3walkEmit(t,kd,Wc,ts,IG,sil,castG,contact,rings,BL,iadd))continue}   /* walking a step: this step's records moved along it. Above, standing: the same object, checked in this scene, standing as it was: what moves between scenes compared, the rest can't have changed */
  if(t.vap!=null){vapours.push(t);continue}if(t.flame){flames.push(t);continue}if(t.cauldron&&V3.models){cauldrons.push(t);continue}if(t.rune&&V3.models){runes.push(t);continue}if(t.crop&&V3.models){crops.push(t);continue}if(t.banner){banners.push(t);continue}if(t.siege){sieges.push(t);continue}if(t.food&&V3.models){foods.push(t);continue}if(t.vomit!=null&&V3.models){vomits.push(t);continue}if(t.clinic&&V3.models){clinics.push(t);continue}if(t.optable&&V3.models){optables.push(t);continue}if(t.tavern&&V3.models){taverns.push(t);continue}if(t.graveyard&&V3.models){graveyards.push(t);continue}if(t.grave&&V3.models){graves.push(t);continue}if(t.trace&&V3.models){traces.push(t);continue}if(t.m3&&V3.models){objs.push(t);continue}if(t.fishspot){fishspots.push(t);continue}if(t.stall&&V3.models){stalls.push(t);continue}if(t.mouth){mouths.push(t);continue}if(t.hellgate){gates.push(t);continue}if(t.vent){vents.push(t);continue}if(t.caveexit){exits.push(t);continue}let X=t.g3ring?t.g3ring[0]:t.dx,Z=t.g3ring?t.g3ring[1]:-t.dy;   /* v3world(t) without a new array */const sc=t.model&&V3.unitModels?1:(t.sc||1),iw=(t.iw||1)*sc,ih=(t.ih||1)*sc;
  // Where the map draws it: pixel offsets, and pictures bigger than a tile grow up and to the right from their tile.
  X+=(t.px||0)+((t.iw||1)-1)/2;Z-=(t.py||0);
  // up or down a cliff face (Mountains.dm): against the rock between it and its foot, rising (or coming down) with the climb
  // up the face to the rock's drawn top, then over the lip onto it (coming down: the same, backwards)
  let climbY=0;if(t.climb){const [p,H,rx,ry,up,fx,fy]=t.climb,top=v3peakTop(rx,ry)||H,q=up?p:1-p,m=Math.max(0,(q-0.85)/0.15),f=0.62*(1-m);X=rx+(fx-rx)*f;Z=-(ry+(fy-ry)*f);climbY=top*Math.min(1,q/0.85)}
  // A captive on a rope to its captor, and "Bound" over it (Captives.dm).
  if(t.cap!=null&&t.dx!=null){const L=t.lead&&byRef.get(t.lead),gy=v3groundAt(t.dx,t.dy);if(L&&L.dx!=null){const ra=[];MD.rod(ra,[X,gy+0.45,Z],[L.dx,v3groundAt(L.dx,L.dy)+0.5,-L.dy],0.018,4,[0.55,0.4,0.22,1],7);add('',ra)}
   else if(t.tieTo){const [SX,,SZ]=v3world({dx:t.tieTo[0],dy:t.tieTo[1]}),ra=[];MD.rod(ra,[X,gy+0.42,Z],[SX,v3groundAt(t.tieTo[0],t.tieTo[1])+0.38,SZ],0.018,4,[0.55,0.4,0.22,1],7);add('',ra)}   /* tied to a stake, tree or pillar */
   const ck=v3word(String(t.cap),'#f2d27a'),cy=gy+1.25,cw=1.1*(V3.tex.get(ck).wk||1),ch=0.24,ca=[];quad(ca,[X-right[0]*cw/2,cy,Z-right[2]*cw/2],[X+right[0]*cw/2,cy,Z+right[2]*cw/2],[X+right[0]*cw/2,cy+ch,Z+right[2]*cw/2],[X-right[0]*cw/2,cy+ch,Z-right[2]*cw/2],[0,0,0],[1,1,1,1],[0,1,1,1,1,0,0,0]);add(ck,ca)}
  // Knocked out (Subdue.dm): lying on its side, a "Zzz" bobbing over it and the seconds until it wakes.
  if(t.ko!=null&&!t.beast&&t.dx!=null){const gy=(t.ly||v3groundAt(t.dx,t.dy))+0.03,h=0.5*(t.sc||1),w=0.5*(t.iw||1),a=[],fu=t.texd&&t.wf?1/t.wf:1;
   quad(a,[X-h,gy,Z+w],[X-h,gy,Z-w],[X+h,gy,Z-w],[X+h,gy,Z+w],[0,1,0],[1,1,1,1],[0,1,fu,1,fu,0,0,0]);if(!t.g3doll){const tk=(t.texd&&t.texd[v3face(t)])||t.tex||'',e=tk?v3tex(tk):null;if(e&&e.ok)add(tk,a)}   /* drawn as its doll lying out cold (gear3d.js): the Zzz only */
   const b=Math.sin(ts/350+X*3)*0.06,zk=v3word(t.dying?'Bleeding out '+t.ko:t.ko>0?'Zzz '+t.ko:'Zzz',t.dying?'#ff8a7a':'#d8d0ff'),zy=gy+0.5+b,zw=0.9*(V3.tex.get(zk).wk||1),zh=0.22,za=[];quad(za,[X-right[0]*zw/2,zy,Z-right[2]*zw/2],[X+right[0]*zw/2,zy,Z+right[2]*zw/2],[X+right[0]*zw/2,zy+zh,Z+right[2]*zw/2],[X-right[0]*zw/2,zy+zh,Z-right[2]*zw/2],[0,0,0],[1,1,1,1],[0,1,1,1,1,0,0,0]);add(zk,za);continue}
  if((t.kind==='decal'||t.kind==='body')&&!t.beast){if(t.g3doll)continue;   /* lying as its death doll fell (gear3d.js g3poses) */const w=iw/2,d=ih/2,zc=Z-(ih-1)/2,a=[];const c=t.tint?[...hexrgb(t.tint),1]:t.tex?[1,1,1,1]:[...hexrgb(t.color||'#888888'),1];
   const fu=t.texd&&t.wf?1/t.wf:1;/* a body lies on the ground under it: on a mountain top or a carved step that is well above 0, and a body drawn at 0 was inside the rock; and a little over the decals, or the blood it lies in hid it (2026-10-23) */const by=t.kind==='body'?(t.ly||v3groundAt(t.x,t.y))+0.045:(t.ly||0)+0.025;quad(a,[X-w,by,zc+d],[X+w,by,zc+d],[X+w,by,zc-d],[X-w,by,zc-d],[0,1,0],c,[0,1,fu,1,fu,0,0,0]);{let tk=(t.texd&&t.texd[v3face(t)])||t.tex||'';const k=V3.disp.get(t.key),e=tk?v3tex(tk):null;if(tk&&!(e&&e.ok)){if(k&&k.tex)tk=k.tex;else continue}else if(k&&tk)k.tex=tk;add(tk,a)}continue}
  const kd=t._k,nowS=ts/1000;   /* its glide entry (the glide pass above) */
  // A unit that has not changed since its last frame (standing, the same tile, facing, selection, health,
  // action, kind, picture and side, nothing animating, the camera's turn and tilt, the sun and the terrain the same): its records again, with
  // none of the work below (GPU unit drawing: only units that changed are worked out; v3rcMake).
  {const R=kd&&kd.rc;if(R&&R.ep===rcEp&&R.t0===kd.t0&&R.x===t.x&&R.y===t.y&&R.dir===t.dir&&R.sel===t.selected&&R.hp===t.hp&&R.act===t.act&&R.ly===t.ly&&R.dx===t.dx&&R.dy===t.dy&&R.kind===t.kind&&R.tex===t.tex&&R.tint===t.tint&&R.color===t.color&&R.peace===t.peace&&R.ally===t.ally&&R.war===t.war&&R.fly===t.fly&&R.sc===t.sc&&R.iw===t.iw&&R.ih===t.ih&&R.px===t.px&&R.py===t.py&&R.el===t.el&&R.wf===t.wf&&!t.g3doll&&R.g3k===(window.g3key?g3key(t):undefined)&&!t.climb&&!t.drunk&&!t.beast&&R.tk===((t.texd&&t.texd[v3face(t)])||t.tex||'')){R.ob=t;R.og=V3.sceneGen;v3rcEmit(R,IG,sil,castG,contact,rings,BL,iadd);if(R.g3)g3put(R);t.top3d=R.top;continue}}   /* by its fields: every server update brings new objects */
  const rs0=rings.length,bs0=BL.length;let rcW=0;   /* where this unit's rings and bar start; rcW: 1 a cast shadow, 2 a contact shadow */
  // New arrivals grow in over a third of a second instead of popping up.
  const grow=kd&&kd.born!=null?Math.min(1,(nowS-kd.born)/0.35):1,ge=1-Math.pow(1-grow,3);
  // Walking: a step bob and a little sway, one cycle per tile like the map's glide.
  const walking=kd&&(t.kind==='mine'||t.kind==='npc'||t.kind==='player'||t.kind==='animal')&&nowS-kd.t0<kd.dur&&(kd.tx!==kd.fx||kd.ty!==kd.fy);const ph=walking?(nowS-kd.t0)/Math.max(0.12,kd.dur):0;
  const bob=walking?Math.abs(Math.sin(ph*Math.PI*2))*0.07:0,sway=(walking?Math.sin(ph*Math.PI*2)*0.05:0)+(t.drunk?Math.sin(nowS*2.3+(t.x||0)*1.7)*Math.min(0.25,t.drunk/240):0);
  // Flying (Flying.dm): it rises to its height (t.fly, in tiles) and comes down to land, a big climb taking a few
  // seconds; it comes low to fight; small flyers bob as they flap.
  const flyTo=t.fly?(t.act==='attack'?Math.min(t.fly,t.beast?3:1.5):t.fly):0;if(kd){const a0=kd.alt||0;kd.alt=a0+(flyTo-a0)*Math.min(1,dt*(flyTo>a0?0.9:1.4))}
  const air=kd?kd.alt||0:flyTo,flap=air>0.15&&!t.beast?Math.sin(nowS*9+(kd&&kd.off||0)*6)*0.07:0;
  // Over rock a flyer keeps its height above the rock top (it was drawn inside the mountain), eased over ridges.
  const liftTo=t.fly&&!t.ly?Math.max(0,v3groundAt(t.dx,t.dy)):0;if(kd){const l0=kd.lift||0;kd.lift=l0+(liftTo-l0)*Math.min(1,dt*(liftTo>l0?4:2))}const lift=kd?kd.lift||0:liftTo;
  const size=(t.kind==='item'?0.55:t.kind==='station'?1.3:t.el?0.68:1.05)*(0.55+0.45*ge);const hw=size*iw/2;const rampY=t.ly||t.climb?0:(V3.rampH&&V3.rampH.get(t.x+','+t.y)||0)+(t.fly||!V3UNITK.has(t.kind)?0:v3swimY(t.x,t.y)),baseTo=(t.climb?climbY:(t.ly||0))+rampY;if(kd&&!t.climb){const tk=t.x+','+t.y+','+(t.ly?1:0);if(kd.bTile!==tk){kd.bFrom=kd.base==null?baseTo:kd.base;kd.bTile=tk}const gf=kd.dur>0&&kd.t0!=null?Math.min(1,Math.max(0,(nowS-kd.t0)/kd.dur)):1;kd.base=kd.bFrom+(baseTo-kd.bFrom)*gf}   /* up or down a block (a ramp, a hop): the height follows the step's glide, never a jump */const y0=(kd&&!t.climb&&kd.base!=null?kd.base:baseTo)+(t.kind==='item'?0.02:0)+bob+lift;const sh=size*ih*(t.el?1/Math.cos(Math.min(1.15,Math.max(0,V3.pitch))):1);
  if(t.ly>V3.STOREY+0.5)rings.v(X,0.02,Z,0.32,0,1,HPRN,0,0,0,0,1)   /* a whole ring: an arc record (v3drawInst 4) */
  if(V3.models&&t.kind==='item'&&!t.ly){if(t.g3doll)continue;   /* a dead unit's piece lying where it landed is its look (gear3d.js) */let tk=t.tex||'';const e=tk?v3tex(tk):null;if(tk&&e&&e.ok){let ua=groups.get('');if(!ua){ua=new VA();groups.set('',ua)}v3card(add,ua,t,X,v3groundAt(t.x,t.y),Z,tk);continue}}
  const md=V3.models&&V3.unitModels&&t.model?v3model(t.model):null;let beastTop=0,gen='',gfx=0;   /* gen: the picture's sheet when it took the plain picture path */
  if(md){let ma=groups.get('');if(!ma){ma=new VA();groups.set('',ma)}v3drawModel(ma,md,t,X,y0-bob,Z,kd,nowS,walking)}
  else if(t.beast&&(beastTop=v3drawBeast(t,X,y0-bob,Z,kd,nowS,walking,add,shadows,air))){}
  else{const c=t.tint?v3rgba(t.tint):t.tex?QWHITE:v3rgba(t.color||'#888888');
  let tk=(t.texd&&t.texd[v3face(t)])||t.tex||'',nf=t.texd&&t.texd[v3face(t)]?(t.wf||1):1;{const k=kd,e=tk?v3tex(tk):null;if(tk&&!(e&&e.ok)){if(k&&k.tex){tk=k.tex;nf=k.texn||1}else continue}else if(k&&tk){k.tex=tk;k.texn=nf}}
  // A unit's picture is a strip of frames (View3D.dm Remaster3DStrip): standing, two walk frames, then an
  // attack's wind-up and strike. Walking steps through them, two per tile; fighting or working swings,
  // the sprite leaning back, then into the blow (a lean alone when it has no swing frames).
  let fi=0,lunge=0;
  if(walking&&nf>=2){const seq=nf>=3?[1,0,2,0]:[1,0];fi=seq[Math.floor(((kd.n||0)+ph)*2)%seq.length]}
  else if(kd&&(t.act==='attack'||t.act==='work')){const p=((nowS+(kd.off||0))%0.9)/0.9;if(nf>=5)fi=p<0.4?3:p<0.65?4:0;lunge=p<0.4?-0.04:p<0.65?0.14:0}
  const fd=t.dir||2,LX=X+((fd&4?1:0)-(fd&8?1:0))*lunge,LZ=Z-((fd&1?1:0)-(fd&2?1:0))*lunge,u0=fi/nf+0.0005,u1=(fi+1)/nf-0.0005;
  // Looked at steeply (the Top camera) the picture leans back with the camera (V3.lean), its top tipping away, so it
  // reads from above instead of edge-on; the iso and Chase views keep it upright.
  const yA=y0+air+flap,LV=V3.lean||[0,1,0],vx=LV[0],vy=LV[1],vz=LV[2];if(kd){kd.lvx=vx;kd.lvy=vy;kd.lvz=vz}
  // the picture as one record, its corners built by the vertex shader (v3drawInst 1); the corners in JS only for a flash
  // or an effect (Qf), drawn as triangles
  const Qf=()=>[[LX-right[0]*hw,yA,LZ-right[2]*hw],[LX+right[0]*hw,yA,LZ+right[2]*hw],[LX+right[0]*(hw+sway)+vx*sh,yA+vy*sh,LZ+right[2]*(hw+sway)+vz*sh],[LX-right[0]*(hw-sway)+vx*sh,yA+vy*sh,LZ-right[2]*(hw-sway)+vz*sh]];
  if(!t.g3doll)iadd(IG,tk).v(LX,yA,LZ,hw,sh,sway,u0,u1,c[0],c[1],c[2],c[3]);if(t.g3&&window.v3gear3d){G3.rec.length=0;v3gear3d(t,kd,v3face(t),fi,LX,yA,LZ,hw,sh,sway,right,LV,lv,nowS)}   /* its 3D gear (gear3d.js) */
  if(kd&&(t.kind==='mine'||t.kind==='npc'||t.kind==='player'||t.kind==='animal')){kd.gtk=tk;kd.gu0=u0;kd.gu1=u1;kd.ghw=hw;kd.gsh=sh;kd.gy=yA-air-flap;const fa=V3.flash&&V3.flash.get(t.x+','+t.y);if(fa!=null&&!t.g3doll&&ts>=fa-16&&ts<fa+120){let fq=flashG.get(tk);if(!fq){fq=new VA();flashG.set(tk,fq)}const Q=Qf();quad(fq,Q[0],Q[1],Q[2],Q[3],QN0,QBLK,[u0,1,u1,1,u1,0,u0,0])}}if(t.kind==='mine'&&!t.g3doll)iadd(sil,tk).v(LX,yA,LZ,hw,sh,sway,u0,u1,c[0],c[1],c[2],c[3])
  if(castOn&&!t.ly&&!t.climb&&!t.g3doll&&air<0.2&&(t.kind==='mine'||t.kind==='npc'||t.kind==='player'||t.kind==='animal')){const gy=v3groundAt(t.x,t.y)+rampY+0.016,Ls=sh*clen*(0.55+0.45*ge);
   iadd(castG,tk).v(LX,gy,LZ,hw,Ls,0,u0,u1,0,0,0,1);rcW|=1}   /* from its foot across the light, Ls long (v3drawInst 2) */
  // A magic item's effect (glow, sparks, flame): an atlas per facing, a row per effect frame, its columns the
  // picture's frames; added as light over the same quad, a new effect frame every 0.14 s.
  const fk=t.fxd&&nf===t.wf?t.fxd[v3face(t)]:null,fe=fk?v3tex(fk):null;gen=tk;gfx=fk?1:0;
  if(walking&&kd&&kd.n!==kd.dustN&&!t.ly&&!air){kd.dustN=kd.n;v3stepDust(kd.fx,kd.fy)}
  if(fe&&fe.ok){const r=Math.floor(nowS/0.14+(kd?kd.off||0:0)*4)%4,b=[];quad(b,...Qf(),[0,0,0],[1,1,1,1],[u0,(r+1)/4,u1,(r+1)/4,u1,r/4,u0,r/4]);let fa=fxg.get(fk);if(!fa){fa=[];fxg.set(fk,fa)}fa.push(...b)}}
  // A soft contact shadow right under the feet (one quad, a radial fade), so a unit always stands on the ground.
  if(!t.ly&&!beastTop&&V3UNITK.has(t.kind)){const gy=v3groundAt(t.x,t.y)+rampY+0.012,k=Math.min(1.8,sc||1)*(t.el?0.7:1)/(1+air*0.25),a=0.36*k,b=0.25*k;contact.v(X,gy,Z,a,b,0,0,0,0,0,0,1);rcW|=2}   /* a flat quad a by b (v3drawInst 3) */
  if(t.kind==='mine'||t.kind==='npc'||t.kind==='player'){/* the selected get the bright gold ring; your others a faint thin one (a crowd no longer reads as rings); others' rings say friend or foe, a little softer */const rc=t.kind==='mine'?(t.selected?RC_SEL:RC_MINE):t.kind==='player'?(t.ally?RC_ALLY:t.war?RC_WAR:RC_PLAYER):t.peace?RC_PEACE:RC_FOE;const r=t.kind==='mine'&&!t.selected?0.42:0.5,ry=(t.ly||0)+lift+0.03;
   // health and the pale trail of a blow just taken; with Settings › Health on the ring (the default) it is drawn on the
   // ring under the unit, and only the selected keep the bar over their heads too (and beasts and units up on the walls)
   const hf=t.hp!=null?Math.max(0,Math.min(1,t.hp/100)):1;if(t.hp!=null&&kd){if(kd.hpLag==null||hf>=kd.hpLag){kd.hpLag=hf;kd.hpPrev=hf}else{if(kd.hpPrev!==hf){kd.hpDrop=ts;kd.hpPrev=hf}if(ts-kd.hpDrop>260)kd.hpLag=Math.max(hf,kd.hpLag-dt*0.9)}}
   const hl=kd&&kd.hpLag!=null?kd.hpLag:hf,hpR=V3.hpRing!==false&&t.hp!=null&&!t.ly&&!beastTop;
   if(!t.ly){if(hpR&&(hf<1||hl>hf))v3hpRing(rings,X,ry,Z,r,t.kind==='mine'&&!t.selected?(hf>0.5?HPOK:hf>0.25?HPMID:HPLOW):rc,hf,hl);else rings.v(X,ry,Z,r,0,1,HPRN,0,rc[0],rc[1],rc[2],rc[3])}
   t.top3d=beastTop||y0+air+flap+sh;
   // the health bar: where it goes and what it shows; drawn last, in screen pixels (v3bars)
   if(t.hp!=null&&!V3.hpOff&&!hpR&&(t.selected||t.hp<100||t.kind!=='mine')){const f=hf;   /* on the ring: no bars, the selected included (the user, 10-25) */
    const lk=!beastTop&&kd&&kd.lvy!=null;BL.push(X+(lk?kd.lvx*sh*0.84:0),beastTop?beastTop+0.05:y0+air+flap+sh*0.84*(lk?kd.lvy:1),Z+(lk?kd.lvz*sh*0.84:0),f,kd?kd.hpLag:f,t.kind==='mine'||t.kind==='player'?1:0,beastTop?1:0,t.selected?1:0)}}
  // kept for the next frames when nothing about it is moving or changing (v3rcEmit gives the same records back)
  if(kd){const fa=V3.flash&&V3.flash.get(t.x+','+t.y),still=t.act!=='attack'&&t.act!=='work'&&!flyTo&&!air&&!lift&&!t.drunk&&ge===1&&!t.climb&&!gfx&&!(t.hp!=null&&kd.hpLag!=null&&kd.hpLag!==Math.max(0,Math.min(1,t.hp/100)))&&!(fa!=null&&ts<fa+120);
   !t.g3doll&&!(t.g3&&window.v3gear3d&&!G3.pix)&&gen&&!walking&&still&&(kd.base==null||kd.base===baseTo)?(window.g3keep?g3keep(v3rcMake(t,kd,rcEp,gen,rcW,IG,sil,castG,contact,rings,rs0,BL,bs0),t):v3rcMake(t,kd,rcEp,gen,rcW,IG,sil,castG,contact,rings,rs0,BL,bs0)):(kd.rc&&(kd.rc.ep=null));
   // walking a step with nothing else changing: this step's records kept, and moved along it in the frames after (v3walkEmit)
   if(gen&&walking&&still&&t._pl&&!t.climb&&!t.g3doll&&!(t.g3&&window.v3gear3d&&!G3.pix)){const Wc=v3rcMake(t,kd,rcEp,gen,rcW,IG,sil,castG,contact,rings,rs0,BL,bs0,'wc');if(window.g3keep)g3keep(Wc,t);if(Wc.ep){Wc.n=kd.n;Wc.nf=kd.texn||1;Wc.bto=baseTo;Wc.bx=X;Wc.bz=Z;Wc.by=y0}}else if(kd.wc)kd.wc.ep=null}}
 if(castOn&&(castG.size||castB.size)){gl.enable(gl.BLEND);gl.blendFunc(gl.SRC_ALPHA,gl.ONE_MINUS_SRC_ALPHA);gl.depthMask(false);gl.uniform4f(L.tint,0.03,0.035,0.06,(V3.night?0.3:0.34)*G.dirk);
  for(const [k,a] of castG){const e=a.length?v3tex(k):null;if(!e||!e.ok)continue;v3drawInst(a,2,e)}for(const [k,a] of castB){const e=a.length?v3tex(k):null;if(!e||!e.ok)continue;gl.bindBuffer(gl.ARRAY_BUFFER,V3.dyn);v3up(a);v3draw(V3.dyn,a.length/12,e)}gl.uniform4f(L.tint,0,0,0,0);gl.depthMask(true);gl.disable(gl.BLEND)}
 if(contact.length&&V3.soft){gl.enable(gl.BLEND);gl.blendFunc(gl.SRC_ALPHA,gl.ONE_MINUS_SRC_ALPHA);gl.depthMask(false);gl.uniform1f(L.soft,1);gl.uniform1f(L.alpha,under||V3.night?0.5:0.42);v3drawInst(contact,3,V3.soft);gl.uniform1f(L.alpha,1);gl.uniform1f(L.soft,0);gl.depthMask(true);gl.disable(gl.BLEND)}
 if(shadows.length){gl.enable(gl.BLEND);gl.blendFunc(gl.SRC_ALPHA,gl.ONE_MINUS_SRC_ALPHA);gl.depthMask(false);gl.uniform1f(L.alpha,0.075);gl.bindBuffer(gl.ARRAY_BUFFER,V3.dyn);v3up(shadows);v3draw(V3.dyn,shadows.length/12,V3.blob);gl.uniform1f(L.alpha,1);gl.depthMask(true);gl.disable(gl.BLEND)}
 for(const [k,a] of groups){if(!a.length)continue;gl.bindBuffer(gl.ARRAY_BUFFER,V3.dyn);v3up(a);v3draw(V3.dyn,a.length/12,k?v3tex(k):null)}
 for(const [k,a] of IG){if(!a.length)continue;const e=v3tex(k);if(e&&e.ok)v3drawInst(a,1,e)}   /* the pictures, a draw a sheet */
 v3combatFx(right,ts,flashG);
 v3breathFx(fxg,right,ts/1000);
 if(fxg.size){gl.enable(gl.BLEND);gl.blendFunc(gl.ONE,gl.ONE);gl.depthMask(false);gl.depthFunc(gl.LEQUAL);gl.uniform1f(L.addm,1);
  for(const [k,a] of fxg){gl.bindBuffer(gl.ARRAY_BUFFER,V3.dyn);v3up(a);v3draw(V3.dyn,a.length/12,v3tex(k))}
  gl.uniform1f(L.addm,0);gl.depthFunc(gl.LESS);gl.depthMask(true);gl.blendFunc(gl.SRC_ALPHA,gl.ONE_MINUS_SRC_ALPHA);gl.disable(gl.BLEND)}
 if(bars.length){gl.bindBuffer(gl.ARRAY_BUFFER,V3.dyn);v3up(bars);v3draw(V3.dyn,bars.length/12,null)}
 if(rings.length){gl.enable(gl.BLEND);gl.blendFunc(gl.SRC_ALPHA,gl.ONE_MINUS_SRC_ALPHA);gl.depthMask(false);gl.uniform1f(L.soft,1);v3drawInst(rings,4,V3.ring);gl.uniform1f(L.soft,0);gl.depthMask(true);gl.disable(gl.BLEND)}
 // Orders of the selected units: each target tile is outlined on the ground, and a line runs
 // from the unit through its targets in queue order (all selected units at once).
 {const hl=[];const Q=v3queues();
  // on the ground, not at sea level: the outline sits at its tile's height (a rock's top for digging), and a long leg
  // is cut into half-tile pieces that each follow the ground, so hills no longer swallow the line
  const gy=(x,z)=>typeof rfY==='function'?rfY(Math.round(x),Math.round(-z)):v3groundAt(Math.round(x),Math.round(-z))+0.035;
  const strip=(x0,z0,x1,z1,w,c,Yf,A)=>{const dx=x1-x0,dz=z1-z0,l=Math.hypot(dx,dz)||1,nx=-dz/l*w,nz=dx/l*w,n=Yf!=null?1:Math.max(1,Math.ceil(l/0.5));for(let i=0;i<n;i++){const a=i/n,b=(i+1)/n,ax=x0+dx*a,az=z0+dz*a,bx=x0+dx*b,bz=z0+dz*b,ya=Yf!=null?Yf:gy(ax,az),yb=Yf!=null?Yf:gy(bx,bz);quad(A||hl,[ax+nx,ya,az+nz],[bx+nx,yb,bz+nz],[bx-nx,yb,bz-nz],[ax-nx,ya,az-nz],[0,1,0],c)}};
  // the lines (StarCraft-style, the user 10-25: v3lineGroups): faded in and out, all of them while Shift is held, and one
  // from a big group's middle instead of one each; the target squares (the placement grid) fade with them, each unit's
  // own square even in a merged group (the user, 10-25); the dig outlines are drawn as before
  const ln=[],LG=v3lineGroups(Q,performance.now());V3.lineA=LG.alpha;   // v3marks fades the queue numbers by it
  for(const q of Q){let px=q.from?q.from[0]:null,pz=q.from?q.from[1]:null;const la=LG.alpha.get(q.unit)||0,own=la>0&&!LG.merged.has(q.unit);
   for(const t of q.list){const X=t.x,Z=-t.y,h=0.47,c=t.color,Y=gy(X,Z);let dug=null;try{dug=typeof rfQueueDig==='function'?v3digCached(hl,t,c,px,pz):null}catch(err){dug=null}   // a dig: the block that will break on the rock's face, not a square on its top (rts-feel)
    if(!dug&&la>0){const cs=[c[0],c[1],c[2],la];strip(X-h,Z+h,X+h,Z+h,0.045,cs,Y,ln);strip(X+h,Z+h,X+h,Z-h,0.045,cs,Y,ln);strip(X+h,Z-h,X-h,Z-h,0.045,cs,Y,ln);strip(X-h,Z-h,X-h,Z+h,0.045,cs,Y,ln)}
    const ex=dug?dug[0]:X,ez=dug?dug[1]:Z;if(own&&px!=null)strip(px,pz,ex,ez,0.025,[c[0]*0.8,c[1]*0.8,c[2]*0.8,la],null,ln);px=ex;pz=ez}}
  for(const g of LG.lines){const c=g.c;for(let i=1;i<g.pts.length;i++)strip(g.pts[i-1][0],g.pts[i-1][1],g.pts[i][0],g.pts[i][1],0.06,[c[0]*0.85,c[1]*0.85,c[2]*0.85,g.a],null,ln)}
  if(hl.length){gl.bindBuffer(gl.ARRAY_BUFFER,V3.dyn);v3up(hl);v3draw(V3.dyn,hl.length/12,null)}
  const fb=typeof FM!=='undefined'&&FM.blend&&FM.blend.length?FM.blend:null;   // the formation slots' squares (fmDraw), fading the same way
  if(ln.length||fb){gl.enable(gl.BLEND);gl.blendFunc(gl.SRC_ALPHA,gl.ONE_MINUS_SRC_ALPHA);gl.depthMask(false);gl.bindBuffer(gl.ARRAY_BUFFER,V3.dyn);if(ln.length){v3up(ln);v3draw(V3.dyn,ln.length/12,null)}if(fb){v3up(fb);v3draw(V3.dyn,fb.length/12,null)}gl.depthMask(true);gl.disable(gl.BLEND)}}
 // Your units hidden behind walls or trees show as a green silhouette.
 if(sil.size){gl.enable(gl.BLEND);gl.blendFunc(gl.SRC_ALPHA,gl.ONE_MINUS_SRC_ALPHA);gl.depthFunc(gl.GREATER);gl.depthMask(false);gl.uniform4f(L.tint,0.45,0.95,0.45,0.55);
  for(const [k,a] of sil){if(!a.length)continue;v3drawInst(a,1,k?v3tex(k):null)}
  gl.uniform4f(L.tint,0,0,0,0);gl.depthFunc(gl.LESS);gl.depthMask(true);gl.disable(gl.BLEND)}if(window.g3draw)g3draw();
 if(V3.above&&V3.above.length&&V3.xray){gl.enable(gl.BLEND);gl.blendFunc(gl.SRC_ALPHA,gl.ONE_MINUS_SRC_ALPHA);gl.depthMask(false);gl.uniform1f(L.alpha,0.22);for(const m of V3.above)v3draw(m.buf,m.count,m.tex?v3tex(m.tex):null,m.color);gl.uniform1f(L.alpha,1);gl.depthMask(true);gl.disable(gl.BLEND)}
 // Cauldron: an iron pot on three legs, its surface the brew's colour, bubbling when
 // hot, flames under it while lit.
 if(cauldrons.length){const a=[],tt=ts/1000,iron=[0.2,0.2,0.23,1],rim=[0.32,0.32,0.36,1];for(const c of cauldrons){const [X,,Z]=v3world(c),Y=v3groundAt(c.x,c.y),C=c.cauldron||{};
   for(let k=0;k<3;k++){const an=k*2.094+0.5;boxr(a,X+Math.cos(an)*0.28-0.04,X+Math.cos(an)*0.28+0.04,Z+Math.sin(an)*0.28-0.04,Z+Math.sin(an)*0.28+0.04,Y,Y+0.28,iron)}
   MD.blob(a,X,Y+0.36,Z,0.4,0.22,0.4,iron,c.x*7+c.y,0.04);
   const R=0.33,top=Y+0.62,n=16;for(let k=0;k<n;k++){const a0=k/n*6.283,a1=(k+1)/n*6.283,m=(a0+a1)/2;boxr(a,X+Math.cos(m)*R-0.035,X+Math.cos(m)*R+0.035,Z+Math.sin(m)*R-0.035,Z+Math.sin(m)*R+0.035,top-0.03,top+0.03,rim);
    if(C.color&&C.fill>0){const lc=hexrgb(C.color),ly=top-0.01+0.02*Math.min(1,C.fill);tri(a,[X,ly,Z],[X+Math.cos(a1)*R*0.92,ly,Z+Math.sin(a1)*R*0.92],[X+Math.cos(a0)*R*0.92,ly,Z+Math.sin(a0)*R*0.92],[0,0,0],[lc[0],lc[1],lc[2],1])}}
   if(C.color&&C.temp>=80)for(let k=0;k<4;k++){const ph=(tt*1.6+k*0.27+c.x*0.13)%1,lc=hexrgb(C.color);MD.blob(a,X+(MD.h(c.x,c.y,k)-0.5)*0.4,top-0.05+ph*0.18,Z+(MD.h(c.x,c.y,k+3)-0.5)*0.4,0.05+ph*0.04,0.05,0.05+ph*0.04,[Math.min(1,lc[0]*1.3),Math.min(1,lc[1]*1.3),Math.min(1,lc[2]*1.3),1],k,0.1)}
   if(C.lit)for(let k=0;k<3;k++){const sd=k*11+c.x,h=0.22+0.08*Math.sin(tt*9+sd),ox=(k-1)*0.12;MD.cone(a,X+ox,Z+0.02,Y,Y+h,0.08,5,[1,0.42,0.08,1],sd,false);MD.cone(a,X+ox,Z,Y,Y+h*0.6,0.05,4,[1,0.9,0.4,1],sd+1,false)}}
  gl.bindBuffer(gl.ARRAY_BUFFER,V3.dyn);v3up(a);v3draw(V3.dyn,a.length/12,null)}
 // Realms: each claim's border as a coloured strip on the ground, and its banner on a pole.
 {const a=(V3.vaO||(V3.vaO=new VA())).reset(),tt=ts/1000;for(const c of arr(V3.claims)){const col=[...hexrgb(c.color),1],r=c.r,s=0.08;
   for(let d=-r;d<=r;d++)for(const [ex,ey,ax] of [[c.x+d,c.y-r,0],[c.x+d,c.y+r,0],[c.x-r,c.y+d,1],[c.x+r,c.y+d,1]]){const [X,,Z]=v3world({dx:ex,dy:ey}),Y=v3groundAt(ex,ey)+0.04,h=0.5;
    if(ax)quad(a,[X-s,Y,Z+h],[X+s,Y,Z+h],[X+s,Y,Z-h],[X-s,Y,Z-h],[0,0,0],col);else quad(a,[X-h,Y,Z+s],[X+h,Y,Z+s],[X+h,Y,Z-s],[X-h,Y,Z-s],[0,0,0],col)}}
  for(const b of banners){const [X,,Z]=v3world(b),Y=v3groundAt(b.x,b.y),col=[...hexrgb(b.banner||'#e0bb73'),1],w=0.06*Math.sin(tt*3+b.x);boxr(a,X-0.03,X+0.03,Z-0.03,Z+0.03,Y,Y+1.5,[0.35,0.25,0.12,1]);
   const p0=[X+0.03,Y+1.45,Z],p1=[X+0.6,Y+1.42+w,Z+w],p2=[X+0.6,Y+1.0+w,Z+w],p3=[X+0.03,Y+1.02,Z];quad(a,p0,p1,p2,p3,[0,0,0],col);quad(a,p3,p2,p1,p0,[0,0,0],col);MD.blob(a,X,Y+1.52,Z,0.05,0.05,0.05,[0.85,0.7,0.3,1],b.x,0.05);
   if(b.siege){const f=Math.min(1,b.siege/100),pu=0.75+0.25*Math.sin(tt*6);boxr(a,X-0.5,X+0.5,Z-0.04,Z+0.04,Y+1.78,Y+1.9,[0.08,0.05,0.04,1]);boxr(a,X-0.48,X-0.48+0.96*f,Z-0.05,Z+0.05,Y+1.8,Y+1.88,[0.9*pu,0.2,0.15,1]);
    const r=2.5,n=24;for(let k=0;k<n;k+=2){const a0=k/n*6.283,a1=(k+1)/n*6.283;quad(a,[X+Math.cos(a0)*r,Y+0.04,Z+Math.sin(a0)*r],[X+Math.cos(a1)*r,Y+0.04,Z+Math.sin(a1)*r],[X+Math.cos(a1)*(r-0.08),Y+0.04,Z+Math.sin(a1)*(r-0.08)],[X+Math.cos(a0)*(r-0.08),Y+0.04,Z+Math.sin(a0)*(r-0.08)],[0,1,0],[0.9*pu,0.2,0.15,1])}}}
  // Siege engines: a battering ram (a capped log slung under a roof on wheels) and a
  // catapult (a throwing arm on a wheeled frame); each swings when it strikes.
  for(const e of sieges){if(V3SHIPK.has(e.siege)){try{v3shipDraw(a,e)}catch(err){if(!V3.shipErr){V3.shipErr=1;console.error(err)}}continue}   /* ships (Ships.dm); a fault drawing one never stops the frame */const [X,,Z]=v3world(e),Y=v3groundAt(e.x,e.y),d=e.dir||2,fx=(d&4?1:0)-(d&8?1:0),fz=(d&2?1:0)-(d&1?1:0),L=Math.hypot(fx,fz)||1,ux=fx/L||0,uz=fz/L||(fx?0:1),px=-uz,pz=ux;
   const wood=[0.48,0.32,0.17,1],dark=[0.3,0.2,0.1,1],iron=[0.42,0.43,0.46,1],since=(performance.now()-((V3.siegeAnim||{})[e.x+','+e.y]||-1e9))/1000;
   const at=(u,v,h)=>[X+ux*u+px*v,Y+h,Z+uz*u+pz*v];
   const beam=(p0,p1,w,c)=>{const dx=p1[0]-p0[0],dz=p1[2]-p0[2],hl=Math.hypot(dx,dz)||1,nx=-dz/hl*w,nz=dx/hl*w;
    quad(a,[p0[0]-nx,p0[1],p0[2]-nz],[p0[0]+nx,p0[1],p0[2]+nz],[p1[0]+nx,p1[1],p1[2]+nz],[p1[0]-nx,p1[1],p1[2]-nz],[0,1,0],c);quad(a,[p1[0]-nx,p1[1],p1[2]-nz],[p1[0]+nx,p1[1],p1[2]+nz],[p0[0]+nx,p0[1],p0[2]+nz],[p0[0]-nx,p0[1],p0[2]-nz],[0,1,0],c);
    quad(a,[p0[0],p0[1]-w,p0[2]],[p0[0],p0[1]+w,p0[2]],[p1[0],p1[1]+w,p1[2]],[p1[0],p1[1]-w,p1[2]],[0,1,0],c);quad(a,[p1[0],p1[1]-w,p1[2]],[p1[0],p1[1]+w,p1[2]],[p0[0],p0[1]+w,p0[2]],[p0[0],p0[1]-w,p0[2]],[0,1,0],c)};
   for(const [u,v] of [[-0.42,-0.36],[-0.42,0.36],[0.42,-0.36],[0.42,0.36]]){const w=at(u,v,0.14);MD.blob(a,w[0],w[1],w[2],0.14,0.14,0.14,dark,u*7+v,0.05)}
   beam(at(-0.5,-0.3,0.26),at(0.5,-0.3,0.26),0.05,wood);beam(at(-0.5,0.3,0.26),at(0.5,0.3,0.26),0.05,wood);beam(at(-0.5,-0.3,0.26),at(-0.5,0.3,0.26),0.05,wood);beam(at(0.5,-0.3,0.26),at(0.5,0.3,0.26),0.05,wood);
   if(e.siege==='ram'){const sw=since<0.6?Math.sin(since/0.6*Math.PI)*0.45:0;
    for(const v of [-0.3,0.3]){beam(at(-0.45,v,0.26),at(0,v,1.05),0.035,wood);beam(at(0.45,v,0.26),at(0,v,1.05),0.035,wood)}
    beam(at(0,-0.3,1.05),at(0,0.3,1.05),0.04,wood);
    quad(a,at(-0.55,-0.36,0.75),at(0.55,-0.36,0.75),at(0.55,0,1.12),at(-0.55,0,1.12),[0,1,0],[0.36,0.28,0.18,1]);quad(a,at(-0.55,0.36,0.75),at(-0.55,0,1.12),at(0.55,0,1.12),at(0.55,0.36,0.75),[0,1,0],[0.33,0.25,0.16,1]);
    beam(at(0.05+sw,-0.18,1.04),at(0.05+sw,-0.18,0.62),0.012,dark);beam(at(-0.25+sw,0.18,1.04),at(-0.25+sw,0.18,0.62),0.012,dark);
    beam(at(-0.7+sw,0,0.6),at(0.62+sw,0,0.6),0.09,[0.42,0.27,0.13,1]);const hd=at(0.7+sw,0,0.6);MD.blob(a,hd[0],hd[1],hd[2],0.15,0.15,0.15,iron,e.x,0.08)}
   else if(e.siege==='ballista'){// a great crossbow on a post: the string drawn back and a bolt laid on it; loosed, it is wound back over a second
    const shot=since<1.2,pull=shot?Math.min(1,since/1.2)*0.45:0.45;beam(at(0,0,0.26),at(0,0,0.72),0.05,wood);beam(at(-0.55,0,0.76),at(0.62,0,0.76),0.05,wood);
    for(const v of [-1,1]){beam(at(0.5,0,0.76),at(0.3,v*0.6,0.8),0.035,dark);beam(at(0.3,v*0.6,0.8),at(0.5-pull,0,0.79),0.008,[0.85,0.82,0.75,1])}
    if(!shot){beam(at(0.05,0,0.82),at(0.95,0,0.82),0.022,wood);const tip=at(0.98,0,0.82);MD.blob(a,tip[0],tip[1],tip[2],0.04,0.04,0.04,iron,e.x,0.05)}}
   else{// catapult arm: rests back, flings forward when it fires
    const fire=since<0.25?since/0.25:since<1.4?1-(since-0.25)/1.15:0,ang=-0.75+fire*2.0,pv=at(-0.05,0,0.75),len=1.15;
    for(const v of [-0.26,0.26]){beam(at(-0.3,v,0.26),at(-0.05,v,0.8),0.035,wood);beam(at(0.2,v,0.26),at(-0.05,v,0.8),0.035,wood)}
    beam(at(-0.05,-0.28,0.78),at(-0.05,0.28,0.78),0.035,wood);
    const arm=[pv[0]-ux*Math.cos(ang)*len,pv[1]+Math.sin(ang)*len,pv[2]-uz*Math.cos(ang)*len];beam(pv,arm,0.045,[0.42,0.27,0.13,1]);
    MD.blob(a,arm[0],arm[1],arm[2],0.13,0.07,0.13,dark,e.y,0.05);if(since>2)MD.blob(a,arm[0],arm[1]+0.1,arm[2],0.12,0.11,0.12,[0.5,0.47,0.43,1],e.x,0.4);
    const cw=at(0.25,0,0.55+fire*0.25);MD.blob(a,cw[0],cw[1],cw[2],0.16,0.16,0.16,iron,e.x+3,0.1)}
   if(e.selected&&e.siege==='ballista'){const R=e.srange||12,ry=Y+0.05,n=72,c=[1,0.78,0.3,0.9];for(let k=0;k<n;k+=2){const a0=k/n*6.283,a1=(k+1)/n*6.283;quad(a,[X+Math.cos(a0)*R,ry,Z+Math.sin(a0)*R],[X+Math.cos(a1)*R,ry,Z+Math.sin(a1)*R],[X+Math.cos(a1)*(R-0.08),ry,Z+Math.sin(a1)*(R-0.08)],[X+Math.cos(a0)*(R-0.08),ry,Z+Math.sin(a0)*(R-0.08)],[0,1,0],c)}
    if(e.starget){const [TX,,TZ]=v3world({dx:e.starget[0],dy:e.starget[1]}),dx=TX-X,dz=TZ-Z,l=Math.hypot(dx,dz)||1,nx=-dz/l*0.05,nz=dx/l*0.05,steps=Math.floor(l/0.5);for(let k=0;k<steps;k+=2){const q0=k/steps,q1=(k+1)/steps,p0=[X+dx*q0,ry,Z+dz*q0],p1=[X+dx*q1,ry,Z+dz*q1];quad(a,[p0[0]-nx,ry,p0[2]-nz],[p0[0]+nx,ry,p0[2]+nz],[p1[0]+nx,ry,p1[2]+nz],[p1[0]-nx,ry,p1[2]-nz],[0,1,0],[1,0.45,0.2,1])}
     const tr=0.5,tY=v3groundAt(e.starget[0],e.starget[1])+0.06;for(let k=0;k<16;k++){const a0=k/16*6.283,a1=(k+1)/16*6.283;quad(a,[TX+Math.cos(a0)*tr,tY,TZ+Math.sin(a0)*tr],[TX+Math.cos(a1)*tr,tY,TZ+Math.sin(a1)*tr],[TX+Math.cos(a1)*(tr-0.07),tY,TZ+Math.sin(a1)*(tr-0.07)],[TX+Math.cos(a0)*(tr-0.07),tY,TZ+Math.sin(a0)*(tr-0.07)],[0,1,0],[1,0.45,0.2,1])}}}
   if(e.selected){const r=0.7,ry=Y+0.04;quad(a,[X-r,ry,Z+r],[X+r,ry,Z+r],[X+r,ry,Z-r],[X-r,ry,Z-r],[0,1,0],[0.95,0.82,0.3,0.35])}
   if(e.siegeHp!=null){const f=Math.max(0,Math.min(1,e.siegeHp/100)),by=Y+1.45;boxr(a,X-0.45,X+0.45,Z-0.05,Z+0.05,by,by+0.12,[0.08,0.05,0.04,1]);boxr(a,X-0.43,X-0.43+0.86*f,Z-0.06,Z+0.06,by+0.02,by+0.1,f>0.5?[0.55,0.8,0.35,1]:[0.85,0.3,0.2,1])}
   if(e.burning){const tt2=performance.now()/1000;for(let k=0;k<7;k++){const ph=tt2*3+k*1.7,u=(MD.h(e.x,k,21)-0.5)*0.9,v=(MD.h(e.y,k,22)-0.5)*0.6,rise=(ph%1),q=at(u,v,0.35+rise*0.9),sz=0.16*(1-rise)+0.04;MD.blob(a,q[0],q[1],q[2],sz,sz*1.4,sz,rise<0.4?[1,0.85,0.3,1]:[0.95,0.4,0.12,1],k+e.x,0.2)}}}
  // Objects that never move are built once and then copied each frame (building every bed, table and station each frame
  // added up in a furnished village); turning machines, fires and gate doors are built every frame.
  {const OC=V3.objCache||(V3.objCache=new Map()),gen=V3.terrGen||0,fn=V3.frameNo=(V3.frameNo||0)+1;for(const t of objs){let [X,,Z]=v3world(t);const Y=t.ly||v3groundAt(t.x,t.y),m=t.m3||'';
   if(!(a instanceof VA)||m==='station:campfire'||m==='waterwheel'||m==='windmill'||m==='bellows'||m==='dynamo'||m.startsWith('axle')||m.startsWith('lift')||(m==='door'&&V3.walkTiles&&V3.walkTiles.has(t.x+','+t.y))){v3obj(a,t,X,Y,Z);continue}
   if(t._os==null)t._os=JSON.stringify(t);const k=t.key||(t.x+','+t.y+m);let E=OC.get(k);if(E&&E.os===t._os&&E.X===X&&E.Y===Y&&E.Z===Z&&E.gen===gen){a.addArr(E.f);E.fn=fn;continue}
   const s0=a.length;v3obj(a,t,X,Y,Z);OC.set(k,{os:t._os,X,Y,Z,gen,fn,f:a.f.slice(s0,a.length)})}
   if(OC.size>objs.length+200)for(const [k,E] of OC)if(E.fn!==fn)OC.delete(k)}
  if(V3.models)v3drawLiquids(a);
  // Fishing spots: rings spreading on the water and now and then a fish breaking the surface.
  {const tt=performance.now()/1000;for(const f of fishspots){const [X,,Z]=v3world(f),Y=v3groundAt(f.x,f.y)-0.1,col={shallow:[0.85,0.95,1],river:[0.75,0.9,1],deep:[0.6,0.8,1],swamp:[0.75,0.95,0.7],cave:[0.7,0.8,0.95]}[f.fishspot]||[0.85,0.95,1];
   for(let k=0;k<3;k++){const ph=((tt*0.6+k/3+MD.h(f.x,f.y,61))%1),R=0.08+ph*0.42,fd=1-ph,n=14;for(let q=0;q<n;q+=2){const a0=q/n*6.283,a1=(q+1)/n*6.283;quad(a,[X+Math.cos(a0)*R,Y+0.02,Z+Math.sin(a0)*R],[X+Math.cos(a1)*R,Y+0.02,Z+Math.sin(a1)*R],[X+Math.cos(a1)*(R+0.035),Y+0.02,Z+Math.sin(a1)*(R+0.035)],[X+Math.cos(a0)*(R+0.035),Y+0.02,Z+Math.sin(a0)*(R+0.035)],[0,1,0],[col[0]*fd+0.2*(1-fd),col[1]*fd+0.4*(1-fd),col[2]*fd+0.6*(1-fd),1])}}
   for(let k=0;k<3;k++)MD.blob(a,X+(MD.h(f.x,k,62)-0.5)*0.4,Y+0.03+0.02*Math.sin(tt*5+k),Z+(MD.h(f.y,k,63)-0.5)*0.4,0.03,0.02,0.03,[0.95,0.98,1,1],k,0.1);
   const jp=(tt*0.25+MD.h(f.x,f.y,64))%1;if(jp<0.12){const q=jp/0.12,hx=X-0.25+q*0.5;MD.blob(a,hx,Y+Math.sin(q*Math.PI)*0.45,Z,0.1,0.05,0.04,[0.6,0.66,0.7,1],f.x,0.1)}}}
  v3drawAim(a);      // aiming a race special: its shape follows the pointer
  v3drawBonds(a);    // great beasts in chains (Taming.dm)
  v3drawWebbed(a);   // units held fast in a web
  v3drawCarriedEggs(a);   // eggs carried off from a nest (Taming.dm)
  v3drawPartRing(a); // the part of a great beast under the pointer
  if(typeof rfDraw==='function')try{rfDraw(a)}catch(err){if(!V3.rfErr){V3.rfErr=1;console.error(err)}}if(typeof pmDraw==='function')try{pmDraw(a)}catch(err){if(!V3.pmErr){V3.pmErr=1;console.error(err)}}   // order pings, target flashes, the ring under the pointer (rts-feel)
  // Walls under siege: a bar shows what is left of each.
  for(const w of arr(V3.siegeWalls)){const [X,,Z]=v3world({dx:w.x,dy:w.y}),Y=v3groundAt(w.x,w.y)+1.95,f=Math.max(0,Math.min(1,w.p/100));
   boxr(a,X-0.45,X+0.45,Z-0.05,Z+0.05,Y,Y+0.12,[0.08,0.05,0.04,1]);boxr(a,X-0.43,X-0.43+0.86*f,Z-0.06,Z+0.06,Y+0.02,Y+0.1,f>0.5?[0.85,0.62,0.25,1]:[0.85,0.25,0.18,1])}
  // Cave mouths: a dark ramp sloping down under a rough arch of rock; a flag shows the danger.
  for(const m of mouths){const [X,,Z]=v3world(m),Y=v3groundAt(m.x,m.y),rock=[0.42,0.4,0.38,1],dark=[0.04,0.03,0.03,1],dirt=[0.3,0.22,0.14,1];
   quad(a,[X-0.45,Y+0.02,Z+0.5],[X+0.45,Y+0.02,Z+0.5],[X+0.4,Y-0.5,Z-0.45],[X-0.4,Y-0.5,Z-0.45],[0,0,0],dirt);
   quad(a,[X-0.42,Y-0.5,Z-0.44],[X+0.42,Y-0.5,Z-0.44],[X+0.42,Y+0.85,Z-0.44],[X-0.42,Y+0.85,Z-0.44],[0,0,0],dark);
   MD.blob(a,X-0.5,Y+0.45,Z-0.2,0.18,0.55,0.3,rock,m.x,0.25);MD.blob(a,X+0.5,Y+0.45,Z-0.2,0.18,0.55,0.3,rock,m.y,0.25);MD.blob(a,X,Y+1.0,Z-0.25,0.65,0.22,0.32,MD.shade(rock,0.9),m.x+m.y,0.25);
   const fc=m.mouth>=3?[0.85,0.15,0.12,1]:m.mouth===2?[0.95,0.6,0.15,1]:[0.35,0.8,0.3,1];boxr(a,X+0.55,X+0.58,Z+0.3,Z+0.33,Y,Y+1.1,[0.35,0.25,0.12,1]);quad(a,[X+0.58,Y+1.08,Z+0.31],[X+0.92,Y+1.0,Z+0.31],[X+0.92,Y+0.82,Z+0.31],[X+0.58,Y+0.86,Z+0.31],[0,0,0],fc);quad(a,[X+0.58,Y+0.86,Z+0.31],[X+0.92,Y+0.82,Z+0.31],[X+0.92,Y+1.0,Z+0.31],[X+0.58,Y+1.08,Z+0.31],[0,0,0],fc);
   // Lairs (Instances.dm): a dragon's has scorched ground and bones before the mouth; a spider's is webbed over.
   if(m.lair==='dragon'){MD.blob(a,X,Y+0.02,Z+0.7,0.95,0.03,0.55,[0.1,0.08,0.07,1],m.x,0.3);for(let k=0;k<4;k++)MD.blob(a,X-0.6+k*0.4,Y+0.06,Z+0.8+(k%2)*0.25,0.13,0.06,0.05,[0.9,0.88,0.8,1],k,0.1)}
   else if(m.lair==='spider'){const w=[0.93,0.93,0.97,1];for(let k=0;k<5;k++){const x0=X-0.4+k*0.2;quad(a,[x0,Y+0.84,Z-0.42],[x0+0.025,Y+0.84,Z-0.42],[X+0.025,Y+0.08,Z-0.40],[X,Y+0.08,Z-0.40],[0,0,0],w)}quad(a,[X-0.42,Y+0.5,Z-0.41],[X+0.42,Y+0.5,Z-0.41],[X+0.42,Y+0.53,Z-0.41],[X-0.42,Y+0.53,Z-0.41],[0,0,0],w)}}
  // Ember vents: a black crack in the ash glowing orange, a little smoke of sparks.
  for(const v of vents){const [X,,Z]=v3world(v),Y=v3groundAt(v.x,v.y),g=0.6+0.4*Math.sin(ts/300+v.x);MD.blob(a,X,Y+0.03,Z,0.36,0.05,0.24,[0.08,0.06,0.06,1],v.x,0.3);MD.blob(a,X,Y+0.06,Z,0.2*g+0.08,0.04,0.12,[1,0.45*g+0.2,0.08,1],v.y,0.2);for(let k=0;k<3;k++){const t=((ts/900)+k/3+v.x*0.1)%1;MD.blob(a,X+(MD.h(v.x,k,3)-0.5)*0.3,Y+0.1+t*0.9,Z,0.03,0.03,0.03,[1,0.7-0.4*t,0.2,1],k,0.1)}}
  // Stairs up inside a cave: rough stone steps climbing to a pale light.
  for(const e of exits){const [X,,Z]=v3world(e),Y=v3groundAt(e.x,e.y),st=[0.5,0.48,0.45,1];for(let q=0;q<4;q++)boxr(a,X-0.35,X+0.35,Z-0.4+q*0.2,Z-0.2+q*0.2,Y,Y+0.15+q*0.15,MD.shade(st,0.85+q*0.06));
   quad(a,[X-0.3,Y+0.6,Z+0.4],[X+0.3,Y+0.6,Z+0.4],[X+0.3,Y+1.6,Z+0.4],[X-0.3,Y+1.6,Z+0.4],[0,0,0],[0.85,0.85,0.7,1])}
  if(a.length){gl.bindBuffer(gl.ARRAY_BUFFER,V3.dyn);v3up(a);v3draw(V3.dyn,a.length/12,null);a.length=0}
  v3hellgates(gates,ts,gl,L);
  v3drawFx(ts);
  v3drawWork(ts);
  // Market stalls: a wooden counter on four posts under a striped awning in the realm's colour.
  for(const s of stalls){const [X,,Z]=v3world(s),Y=v3groundAt(s.x,s.y),wood=[0.5,0.34,0.18,1],dark=[0.36,0.24,0.12,1],col=[...hexrgb(s.stall),1],pale=[0.92,0.88,0.78,1];
   boxr(a,X-0.42,X+0.42,Z-0.22,Z+0.22,Y+0.42,Y+0.5,wood);boxr(a,X-0.4,X+0.4,Z-0.2,Z+0.2,Y,Y+0.42,dark);
   for(const [px,pz] of [[-0.42,-0.3],[0.38,-0.3],[-0.42,0.26],[0.38,0.26]])boxr(a,X+px,X+px+0.04,Z+pz,Z+pz+0.04,Y,Y+1.1,wood);
   for(let q=0;q<6;q++){const x0=X-0.48+q*0.16,x1=x0+0.16,c=q%2?pale:col;quad(a,[x0,Y+1.18,Z-0.36],[x1,Y+1.18,Z-0.36],[x1,Y+1.04,Z+0.34],[x0,Y+1.04,Z+0.34],[0,0,0],c);quad(a,[x0,Y+1.04,Z+0.34],[x1,Y+1.04,Z+0.34],[x1,Y+1.18,Z-0.36],[x0,Y+1.18,Z-0.36],[0,0,0],c)}
   MD.blob(a,X-0.2,Y+0.56,Z,0.08,0.06,0.08,[0.85,0.2,0.15,1],s.x,0.1);MD.blob(a,X+0.05,Y+0.56,Z+0.05,0.08,0.06,0.08,[0.45,0.18,0.5,1],s.y,0.1);boxr(a,X+0.2,X+0.32,Z-0.06,Z+0.06,Y+0.5,Y+0.6,[0.6,0.6,0.64,1])}
  // Food pots (FoodSupply.dm): an iron pot on a ring of hearth stones over a wood fire when lit, the stew rising with what it
  // holds and steaming when hot. Food stalls: a counter under a green awning with the food laid out and crates in front.
  // Food your villagers fell sick from or found poisoned shows sickly green.
  {const SC={CookedMeat:[0.48,0.28,0.13],Stew:[0.52,0.4,0.22],Tomato:[0.72,0.18,0.1],Grape:[0.38,0.14,0.4],RawMeat:[0.66,0.26,0.26],Fungus:[0.56,0.5,0.4],Cheese:[0.9,0.78,0.38]},sc=s=>SC[s]||[0.6,0.45,0.25],tt=ts/1000;
  for(const f of foods){const F=f.food||{},[X,,Z]=v3world(f),Y=v3groundAt(f.x,f.y),warn=F.warn>0,items=arr(F.items),fill=F.max?Math.min(1,F.n/F.max):0;
   if(F.kind==='pot'){const iron=[0.18,0.18,0.2,1],rim=[0.3,0.3,0.33,1],stone=[0.45,0.43,0.4,1];
    for(let k=0;k<7;k++){const an=k/7*6.283;MD.blob(a,X+Math.cos(an)*0.4,Y+0.05,Z+Math.sin(an)*0.4,0.1,0.07,0.09,MD.shade(stone,0.85+MD.h(f.x,f.y,k)*0.3),f.x+k,0.2)}
    if(F.lit)for(let k=0;k<3;k++){const sd=k*7+f.y,h=0.2+0.07*Math.sin(tt*8+sd),ox=(k-1)*0.1;MD.cone(a,X+ox,Z,Y+0.02,Y+h,0.07,5,[1,0.45,0.1,1],sd,false);MD.cone(a,X+ox,Z,Y+0.02,Y+h*0.6,0.04,4,[1,0.85,0.35,1],sd+1,false)}
    for(let k=0;k<3;k++){const an=k*2.094+0.3;boxr(a,X+Math.cos(an)*0.3-0.03,X+Math.cos(an)*0.3+0.03,Z+Math.sin(an)*0.3-0.03,Z+Math.sin(an)*0.3+0.03,Y,Y+0.3,iron)}
    MD.blob(a,X,Y+0.42,Z,0.38,0.25,0.38,iron,f.x*5+f.y,0.04);
    const R=0.31,top=Y+0.62,n=16;let lc=[0,0,0];if(items.length){for(const s of items){const c=sc(s);lc=[lc[0]+c[0],lc[1]+c[1],lc[2]+c[2]]}lc=lc.map(x=>x/items.length)}if(warn)lc=[lc[0]*0.4+0.27,lc[1]*0.4+0.42,lc[2]*0.4+0.1];
    for(let k=0;k<n;k++){const a0=k/n*6.283,a1=(k+1)/n*6.283,m=(a0+a1)/2;boxr(a,X+Math.cos(m)*R-0.035,X+Math.cos(m)*R+0.035,Z+Math.sin(m)*R-0.035,Z+Math.sin(m)*R+0.035,top-0.03,top+0.03,rim);
     if(fill>0){const ly=top-0.16+0.15*fill;tri(a,[X,ly,Z],[X+Math.cos(a1)*R*0.93,ly,Z+Math.sin(a1)*R*0.93],[X+Math.cos(a0)*R*0.93,ly,Z+Math.sin(a0)*R*0.93],[0,0,0],[lc[0],lc[1],lc[2],1])}}
    if(fill>0)for(let k=0;k<Math.min(5,items.length);k++){const c=sc(items[k]);MD.blob(a,X+(MD.h(f.x,f.y,k)-0.5)*0.36,top-0.13+0.15*fill,Z+(MD.h(f.x,f.y,k+5)-0.5)*0.36,0.05,0.03,0.05,[c[0]*0.9,c[1]*0.9,c[2]*0.9,1],k,0.2)}
    boxr(a,X+0.12,X+0.16,Z-0.02,Z+0.02,top-0.1,top+0.32,[0.42,0.28,0.14,1]);
    if((F.temp||0)>=60&&fill>0)for(let k=0;k<4;k++){const ph=(tt*0.5+k*0.25+f.x*0.07)%1;MD.blob(a,X+(MD.h(f.x,k,1)-0.5)*0.3+ph*0.1,top+0.05+ph*0.7,Z+(MD.h(f.y,k,2)-0.5)*0.3,0.06+ph*0.08,0.05+ph*0.06,0.06+ph*0.08,warn?[0.75,0.95,0.55,1]:[0.92,0.92,0.9,1],k,0.1)}}
   else{const wood=[0.5,0.34,0.18,1],dark=[0.34,0.22,0.11,1],col=[...hexrgb(F.col||'#c8a060'),1],green=warn?[0.55,0.75,0.25,1]:[0.36,0.55,0.25,1],pale=[0.92,0.88,0.76,1];
    boxr(a,X-0.44,X+0.44,Z-0.24,Z+0.24,Y+0.44,Y+0.52,wood);boxr(a,X-0.42,X+0.42,Z-0.22,Z+0.22,Y,Y+0.44,dark);boxr(a,X-0.44,X+0.44,Z+0.22,Z+0.25,Y+0.36,Y+0.44,col);
    for(const [px,pz] of [[-0.44,-0.32],[0.4,-0.32],[-0.44,0.28],[0.4,0.28]])boxr(a,X+px,X+px+0.04,Z+pz,Z+pz+0.04,Y,Y+1.15,wood);
    for(let q=0;q<6;q++){const x0=X-0.5+q*0.1667,x1=x0+0.1667,c=q%2?pale:green;quad(a,[x0,Y+1.22,Z-0.38],[x1,Y+1.22,Z-0.38],[x1,Y+1.08,Z+0.36],[x0,Y+1.08,Z+0.36],[0,0,0],c);quad(a,[x0,Y+1.08,Z+0.36],[x1,Y+1.08,Z+0.36],[x1,Y+1.22,Z-0.38],[x0,Y+1.22,Z-0.38],[0,0,0],c)}
    for(let k=0;k<items.length;k++){const c=sc(items[k]),cx=X-0.34+(k%6)*0.136,cz=Z-0.1+Math.floor(k/6)*0.18;if(items[k]==='RawMeat'||items[k]==='CookedMeat')boxr(a,cx-0.05,cx+0.05,cz-0.04,cz+0.04,Y+0.52,Y+0.58,[...c,1]);else MD.blob(a,cx,Y+0.57,cz,0.05,0.045,0.05,[...c,1],k+f.x,0.15)}
    for(const dx of [-0.28,0.22]){boxr(a,X+dx-0.11,X+dx+0.11,Z+0.3,Z+0.48,Y,Y+0.16,[0.58,0.42,0.24,1]);if(fill>0.2&&items.length)MD.blob(a,X+dx,Y+0.18,Z+0.39,0.08,0.04,0.06,[...sc(items[items.length-1]),1],f.x+dx*10,0.2)}}}}
  // Green vomit (FoodSupply.dm): a puddle of bile with lumps in it; while fresh, the splash still falling.
  for(const v of vomits){const d=v.dir||2,[X0,,Z0]=v3world(v),X=X0+(d&4?0.3:d&8?-0.3:0),Z=Z0-(d&1?0.3:d&2?-0.3:0),Y=v3groundAt(v.x,v.y)+0.02,g=[0.46,0.74,0.18,1],dk=[0.3,0.52,0.11,1];
   for(let k=0;k<6;k++){const r=0.08+MD.h(v.x,k,3)*0.1;MD.blob(a,X+(MD.h(v.x,v.y,k)-0.5)*0.5,Y,Z+(MD.h(v.x,v.y,k+9)-0.5)*0.5,r,0.012,r*0.8,k%2?g:dk,v.x+k,0.3)}
   for(let k=0;k<4;k++)MD.blob(a,X+(MD.h(v.y,k,5)-0.5)*0.4,Y+0.02,Z+(MD.h(v.x,k,7)-0.5)*0.4,0.03,0.02,0.03,[0.62,0.52,0.24,1],k,0.3);
   if(v.vomit<1.5){const p=v.vomit/1.5;for(let k=0;k<5;k++)MD.blob(a,X+(MD.h(k,v.x,1)-0.5)*0.2,Y+0.6*(1-p)+0.05,Z+(MD.h(k,v.y,2)-0.5)*0.2,0.04,0.05,0.04,g,k,0.2)}}
  // Doctor's stalls (Doctor.dm): a counter under a white awning, herb bundles hanging from the beam, jars of
  // remedies on the counter (green poultices, blue tonics, purple purges) and a mortar.
  for(const s of clinics){const K=s.clinic||{},[X,,Z]=v3world(s),Y=v3groundAt(s.x,s.y),wood=[0.46,0.32,0.17,1],dark=[0.3,0.2,0.1,1],cloth=[0.93,0.92,0.86,1],col=[...hexrgb(K.col||'#c8a060'),1];
   boxr(a,X-0.44,X+0.44,Z-0.24,Z+0.24,Y+0.44,Y+0.52,wood);boxr(a,X-0.42,X+0.42,Z-0.22,Z+0.22,Y,Y+0.44,dark);boxr(a,X-0.44,X+0.44,Z+0.22,Z+0.25,Y+0.36,Y+0.44,col);
   for(const [px,pz] of [[-0.44,-0.32],[0.4,-0.32],[-0.44,0.28],[0.4,0.28]])boxr(a,X+px,X+px+0.04,Z+pz,Z+pz+0.04,Y,Y+1.15,wood);
   quad(a,[X-0.5,Y+1.2,Z-0.38],[X+0.5,Y+1.2,Z-0.38],[X+0.5,Y+1.06,Z+0.36],[X-0.5,Y+1.06,Z+0.36],[0,0,0],cloth);quad(a,[X-0.5,Y+1.06,Z+0.36],[X+0.5,Y+1.06,Z+0.36],[X+0.5,Y+1.2,Z-0.38],[X-0.5,Y+1.2,Z-0.38],[0,0,0],cloth);
   boxr(a,X-0.42,X+0.42,Z+0.3,Z+0.32,Y+1.0,Y+1.04,wood);
   for(let k=0;k<Math.min(6,(K.herbs||0)+1);k++){const hx=X-0.34+k*0.14,c=k%3===0?[0.45,0.7,0.35,1]:k%3===1?[0.85,0.85,0.6,1]:[0.62,0.45,0.75,1];boxr(a,hx-0.005,hx+0.005,Z+0.3,Z+0.31,Y+0.86,Y+1.0,[0.5,0.42,0.3,1]);MD.blob(a,hx,Y+0.82,Z+0.31,0.045,0.08,0.035,c,k+s.x,0.25)}
   const jars=[['poultice',[0.3,0.62,0.3,1]],['tonic',[0.3,0.5,0.85,1]],['purge',[0.6,0.35,0.75,1]]];let j=0;
   for(const [id,c] of jars)for(let q=0;q<Math.min(3,K[id]||0);q++){const jx=X-0.32+j*0.1;boxr(a,jx-0.03,jx+0.03,Z-0.08,Z-0.02,Y+0.52,Y+0.62,c);boxr(a,jx-0.015,jx+0.015,Z-0.065,Z-0.035,Y+0.62,Y+0.66,[0.55,0.4,0.25,1]);j++}
   MD.blob(a,X+0.28,Y+0.56,Z+0.05,0.07,0.05,0.07,[0.55,0.55,0.58,1],s.y,0.1);boxr(a,X+0.27,X+0.3,Z+0.02,Z+0.05,Y+0.56,Y+0.68,[0.42,0.3,0.18,1])}
  // Operating tables (Surgery.dm): a wooden table with a white sheet and pillow, a tray of steel tools on a stand,
  // a bucket, and a lamp on a pole that burns while someone lies on it.
  for(const s of optables){const O=s.optable||{},[X,,Z]=v3world(s),Y=v3groundAt(s.x,s.y),wood=[0.42,0.3,0.17,1],dark=[0.28,0.19,0.1,1],sheet=[0.9,0.9,0.86,1],steel=[0.7,0.72,0.76,1];
   for(const [px,pz] of [[-0.4,-0.2],[0.35,-0.2],[-0.4,0.15],[0.35,0.15]])boxr(a,X+px,X+px+0.05,Z+pz,Z+pz+0.05,Y,Y+0.46,dark);
   boxr(a,X-0.42,X+0.42,Z-0.23,Z+0.23,Y+0.46,Y+0.52,wood);boxr(a,X-0.4,X+0.26,Z-0.21,Z+0.21,Y+0.52,Y+0.545,sheet);boxr(a,X+0.26,X+0.4,Z-0.15,Z+0.15,Y+0.52,Y+0.6,sheet);
   if(O.busy)boxr(a,X-0.12,X+0.08,Z-0.08,Z+0.07,Y+0.546,Y+0.549,[0.55,0.1,0.08,1]);
   boxr(a,X-0.3,X-0.27,Z+0.33,Z+0.36,Y,Y+0.62,dark);boxr(a,X-0.44,X-0.12,Z+0.26,Z+0.44,Y+0.62,Y+0.64,steel);for(let k=0;k<3;k++)boxr(a,X-0.4+k*0.1,X-0.38+k*0.1,Z+0.29,Z+0.41,Y+0.64,Y+0.655,[0.86,0.87,0.9,1]);
   MD.prism(a,X+0.3,Z+0.36,Y,Y+0.22,0.08,0.1,8,[0.45,0.32,0.18,1],s.x+s.y);
   boxr(a,X+0.44,X+0.47,Z-0.33,Z-0.3,Y,Y+1.2,dark);MD.blob(a,X+0.455,Y+1.24,Z-0.315,0.06,0.07,0.06,O.busy?[1,0.86,0.45,1]:[0.55,0.5,0.4,1],s.x,0.1)}
  // Taverns (Tavern.dm): a counter with mugs on it (as many as it has wine for), two barrels with taps behind it,
  // and a sign on a post in the realm's colour.
  for(const s of taverns){const T=s.tavern||{},[X,,Z]=v3world(s),Y=v3groundAt(s.x,s.y),wood=[0.52,0.35,0.18,1],dark=[0.3,0.2,0.1,1],hoop=[0.24,0.24,0.27,1],col=[...hexrgb(T.col||'#c8a060'),1];
   boxr(a,X-0.46,X+0.46,Z-0.18,Z+0.2,Y+0.5,Y+0.58,wood);boxr(a,X-0.44,X+0.44,Z-0.16,Z+0.18,Y,Y+0.5,dark);
   for(const bx of [-0.24,0.2]){const bz=Z-0.34;MD.rod(a,[X+bx-0.17,Y+0.18,bz],[X+bx+0.17,Y+0.18,bz],0.16,10,wood,s.x*3+bx*10);for(const hx of [-0.11,0.11])MD.rod(a,[X+bx+hx-0.015,Y+0.18,bz],[X+bx+hx+0.015,Y+0.18,bz],0.168,10,hoop,1);boxr(a,X+bx-0.015,X+bx+0.015,bz+0.15,bz+0.2,Y+0.12,Y+0.16,[0.62,0.62,0.64,1])}
   const mugs=Math.min(6,Math.ceil((T.drink||0)/7));for(let k=0;k<mugs;k++){const mx=X-0.36+k*0.14;MD.prism(a,mx,Z+0.05,Y+0.58,Y+0.7,0.04,0.045,6,[0.62,0.48,0.3,1],k+s.y);boxr(a,mx-0.03,mx+0.03,Z+0.04,Z+0.06,Y+0.69,Y+0.705,[0.5,0.14,0.24,1])}
   boxr(a,X+0.47,X+0.51,Z+0.2,Z+0.24,Y,Y+1.3,dark);boxr(a,X+0.28,X+0.51,Z+0.205,Z+0.235,Y+1.26,Y+1.29,dark);boxr(a,X+0.29,X+0.45,Z+0.2,Z+0.24,Y+1.0,Y+1.22,col);MD.prism(a,X+0.37,Z+0.18,Y+1.05,Y+1.15,0.03,0.035,6,[0.85,0.75,0.4,1],s.x)}
  // Graveyards (Graves.dm): a stone cross on a plinth with moss at its foot and a ring of low stones round the plot.
  for(const s of graveyards){const [X,,Z]=v3world(s),Y=v3groundAt(s.x,s.y),st=[0.56,0.55,0.53,1],dk=[0.4,0.39,0.38,1];
   boxr(a,X-0.26,X+0.26,Z-0.16,Z+0.16,Y,Y+0.12,dk);boxr(a,X-0.06,X+0.06,Z-0.05,Z+0.05,Y+0.12,Y+1.2,st);boxr(a,X-0.26,X+0.26,Z-0.05,Z+0.05,Y+0.82,Y+0.94,st);
   MD.blob(a,X-0.16,Y+0.13,Z+0.1,0.1,0.04,0.06,[0.33,0.45,0.24,1],s.x,0.3);
   for(let k=0;k<10;k++){const an=k/10*6.283;MD.blob(a,X+Math.cos(an)*0.46,Y+0.04,Z+Math.sin(an)*0.46,0.07,0.05,0.06,MD.shade(st,0.8+MD.h(s.x,s.y,k)*0.3),s.y+k,0.25)}}
  // Graves (the original Bury): a mound of earth with a headstone.
  for(const g of graves){const [X,,Z]=v3world(g),Y=v3groundAt(g.x,g.y),st=[0.58,0.57,0.55,1];MD.blob(a,X,Y+0.02,Z+0.06,0.22,0.1,0.36,[0.36,0.27,0.17,1],g.x*3+g.y,0.15);boxr(a,X-0.14,X+0.14,Z-0.38,Z-0.31,Y,Y+0.4,st);MD.blob(a,X,Y+0.4,Z-0.345,0.14,0.06,0.035,st,g.y,0.05)}
  // Footprints (Forensics.dm): three prints the size of the feet that left them, fading into the ground over 15 minutes.
  {const FS={Orc:1.25,Dwarf:1.05,Human:1,Elf:0.9,Goblin:0.75,Kobold:0.7,Ratman:0.7,Gargoyle:1.3,Demon:1.3,Lizardman:1.1,Frogman:0.95};
  for(const f of traces){const [X,,Z]=v3world(f),Y=v3groundAt(f.x,f.y)+0.015,age=Math.min(1,(f.age||0)/15),d=f.dir||2,sz=FS[f.trace]||1,c=MD.mix([0.17,0.12,0.07,1],[0.38,0.32,0.22,1],age);
   const fx=d&4?1:d&8?-1:0,fz=d&1?-1:d&2?1:0,len=Math.hypot(fx,fz)||1,ux=fx/len,uz=(fx||fz)?fz/len:1,px=-uz,pz=ux;
   for(let k=0;k<3;k++){const along=(k-1)*0.28,side=(k%2?1:-1)*0.07,cx=X+ux*along+px*side,cz=Z+uz*along+pz*side,w=0.045*sz,l=0.085*sz;
    quad(a,[cx-px*w-ux*l,Y,cz-pz*w-uz*l],[cx+px*w-ux*l,Y,cz+pz*w-uz*l],[cx+px*w+ux*l,Y,cz+pz*w+uz*l],[cx-px*w+ux*l,Y,cz-pz*w+uz*l],[0,1,0],c)}}}
  // An item held (UseOn.dm): a green ring round each thing it can be used on, breathing.
  {const UO=model&&model.useon;if(UO)for(const g of arr(UO.targets)){const X=g.x,Z=-g.y,Y=v3groundAt(g.x,g.y)+0.05,R=0.5+0.05*Math.sin(ts/200),n=24;
   for(let k=0;k<n;k++){const a0=k/n*6.283,a1=(k+0.6)/n*6.283;quad(a,[X+Math.cos(a0)*R,Y,Z+Math.sin(a0)*R],[X+Math.cos(a1)*R,Y,Z+Math.sin(a1)*R],[X+Math.cos(a1)*(R+0.08),Y,Z+Math.sin(a1)*(R+0.08)],[X+Math.cos(a0)*(R+0.08),Y,Z+Math.sin(a0)*(R+0.08)],[0,1,0],[0.45,0.95,0.35,1])}}}
  // Glimmering limbs (Surgery.dm): sparks circling the unit. A brawl (Tavern.dm): a dust cloud round its feet and stars over it.
  for(const u of v3cat('glow',u=>u.glow||u.brawl)){if(!(u.glow||u.brawl)||u.dx==null||!v3visible(u))continue;const [X,,Z]=v3world(u),Y=v3groundAt(u.x,u.y);
   if(u.glow)for(let k=0;k<3;k++){const an=ts/700+k*2.094+u.x,ph=((ts/1100)+k/3)%1;MD.gem(a,X+Math.cos(an)*0.28,Y+0.35+ph*0.6,Z+Math.sin(an)*0.28,0.03,[0.62,0.95,1,1])}
   if(u.brawl){for(let k=0;k<5;k++){const an=ts/260+k*1.257,r=0.32+0.06*Math.sin(ts/150+k);MD.blob(a,X+Math.cos(an)*r,Y+0.12+0.08*Math.sin(ts/120+k*2),Z+Math.sin(an)*r,0.09,0.07,0.09,[0.72,0.64,0.5,1],k+u.y,0.3)}
    const top=(u.top3d||Y+1.1)+0.15;for(let k=0;k<3;k++){const an=-ts/400+k*2.094;MD.gem(a,X+Math.cos(an)*0.18,top,Z+Math.sin(an)*0.18,0.045,[1,0.9,0.3,1])}}}
  // Sick villagers (Ailments.dm): a pale cough cloud at the mouth now and then.
  for(const u of v3cat('ill',u=>u.ill)){if(!u.ill||u.dx==null||!v3visible(u))continue;const ph=((ts/900)+u.x*0.37)%1;if(!u.cough&&ph>0.35)continue;const [X,,Z]=v3world(u),Y=v3groundAt(u.x,u.y)+0.95,p=u.cough?((ts/600)%1):ph/0.35;
   for(let k=0;k<3;k++)MD.blob(a,X+0.12+p*0.25+k*0.05,Y+p*0.18+k*0.03,Z+0.05,0.04+p*0.05,0.035+p*0.04,0.04+p*0.05,u.ill>=3?[0.7,0.8,0.5,1]:[0.85,0.9,0.78,1],k+u.x,0.2)}
  v3foodTags(foods.concat(clinics,taverns,V3.things.filter(t=>(t.qboard||t.qkeeper)&&v3visible(t))));if(typeof questPins3D==='function')questPins3D();if(typeof guidePin3D==='function')guidePin3D();v3sayTags();v3useOnBanner();
  if(a.length){gl.bindBuffer(gl.ARRAY_BUFFER,V3.dyn);v3up(a);v3draw(V3.dyn,a.length/12,null)}}
 // Crops: tomato bushes and grape vines grow through five stages; ripe ones show fruit.
 if(crops.length){const a=[],leaf=[0.25,0.55,0.2,1],stem=[0.35,0.25,0.12,1];for(const c of crops){const [X,,Z]=v3world(c),Y=v3groundAt(c.x,c.y),C=c.crop||{},s=Math.max(1,Math.min(5,C.stage||1))/5;
   if(C.type==='athelas'||C.type==='feverfew'||C.type==='thistle'){const th=C.type==='thistle',lf=th?[0.42,0.55,0.42,1]:C.type==='athelas'?[0.18,0.5,0.22,1]:[0.35,0.6,0.25,1],fl=th?[0.62,0.3,0.7,1]:C.type==='athelas'?[0.97,0.97,0.94,1]:[0.98,0.95,0.7,1];
    for(let k=0;k<5;k++){const an=k*1.26+c.x*0.7;MD.blob(a,X+Math.cos(an)*0.17,Y+(th?0.22:0.12),Z+Math.sin(an)*0.17,th?0.1:0.15,th?0.2:0.07,th?0.1:0.15,MD.shade(lf,0.85+MD.h(c.x,k,8)*0.3),c.x+k,th?0.45:0.2)}
    for(let k=0;k<(C.n||0)*2;k++){const an=k*2.1+c.y;const r=0.08+MD.h(c.y,k,9)*0.14;MD.blob(a,X+Math.cos(an)*r,Y+(th?0.46:0.23)+MD.h(c.x,k,2)*0.08,Z+Math.sin(an)*r,0.05,th?0.06:0.028,0.05,fl,k,0.15);if(C.type==='feverfew')MD.blob(a,X+Math.cos(an)*r,Y+0.26+MD.h(c.x,k,2)*0.08,Z+Math.sin(an)*r,0.018,0.018,0.018,[0.95,0.75,0.15,1],k,0.1)}}
   else if(C.type==='grape'){boxr(a,X-0.3,X-0.26,Z-0.02,Z+0.02,Y,Y+0.75,stem);boxr(a,X+0.26,X+0.3,Z-0.02,Z+0.02,Y,Y+0.75,stem);boxr(a,X-0.3,X+0.3,Z-0.015,Z+0.015,Y+0.7,Y+0.73,stem);
    MD.blob(a,X,Y+0.25+0.3*s,Z,0.18+0.14*s,0.12+0.2*s,0.12,MD.shade(leaf,0.9+MD.h(c.x,c.y,3)*0.2),c.x*5+c.y,0.25);
    if(C.ripe)for(let k=0;k<4;k++)MD.blob(a,X-0.18+k*0.12,Y+0.32+MD.h(c.x+k,c.y,4)*0.2,Z+0.1,0.05,0.07,0.05,[0.45,0.18,0.5,1],k,0.1)}
   else{boxr(a,X-0.02,X+0.02,Z-0.02,Z+0.02,Y,Y+0.15+0.25*s,stem);MD.blob(a,X,Y+0.1+0.28*s,Z,0.12+0.2*s,0.1+0.18*s,0.12+0.2*s,MD.shade(leaf,0.9+MD.h(c.x,c.y,5)*0.2),c.x*3+c.y,0.3);
    if(C.ripe)for(let k=0;k<5;k++){const an=k*1.26+c.x;MD.blob(a,X+Math.cos(an)*0.2*s,Y+0.12+0.25*s+MD.h(c.x,k,6)*0.1,Z+Math.sin(an)*0.2*s,0.05,0.05,0.05,[0.85,0.15,0.1,1],k,0.1)}}}
  gl.bindBuffer(gl.ARRAY_BUFFER,V3.dyn);v3up(a);v3draw(V3.dyn,a.length/12,null)}
 // Rune circuits: glowing violet lines linking the pieces (bright while the circuit has
 // mana), crystals, doors, traps, plates, levers, lamps and bells.
 if(runes.length){const a=[],g=[],tt=ts/1000,stone=[0.45,0.43,0.46,1],dark=[0.22,0.21,0.24,1],wood=[0.45,0.31,0.18,1];
  for(const r of runes){const R=r.rune||{},[X,,Z]=v3world(r),Y=v3groundAt(r.x,r.y),pw=R.pow?0.75+0.25*Math.sin(tt*3+r.x*0.7+r.y*0.5):0.3,gc=R.pow?[0.62*pw,0.45*pw,1*pw,1]:[0.24,0.2,0.32,1];
   const strip=(dx,dz)=>{const w=0.05,y=Y+0.025;if(dx)quad(g,[X,y,Z-w],[X+dx*0.5,y,Z-w],[X+dx*0.5,y,Z+w],[X,y,Z+w],[0,0,0],gc);else quad(g,[X-w,y,Z],[X+w,y,Z],[X+w,y,Z+dz*0.5],[X-w,y,Z+dz*0.5],[0,0,0],gc)};
   const L=R.link||0;if(L&1)strip(0,-1);if(L&2)strip(0,1);if(L&4)strip(1,0);if(L&8)strip(-1,0);
   for(let k=0;k<8;k++){const a0=k/8*6.283,a1=(k+1)/8*6.283,rr=0.16,y=Y+0.027;quad(g,[X+Math.cos(a0)*rr,y,Z+Math.sin(a0)*rr],[X+Math.cos(a1)*rr,y,Z+Math.sin(a1)*rr],[X+Math.cos(a1)*(rr-0.04),y,Z+Math.sin(a1)*(rr-0.04)],[X+Math.cos(a0)*(rr-0.04),y,Z+Math.sin(a0)*(rr-0.04)],[0,0,0],gc)}
   switch(R.id){
    case 'crystal':{const c=Math.min(1,(R.charge||0)/100),bob=Math.sin(tt*1.5+r.x)*0.05,cy=Y+0.75+bob,sp=tt*0.8,col=[0.35+0.4*c,0.25+0.4*c,0.7+0.3*c,1];boxr(a,X-0.14,X+0.14,Z-0.14,Z+0.14,Y,Y+0.18,stone);
     const P=[[0,0.32,0],[0,-0.32,0]],ring=[];for(let k=0;k<4;k++){const an=sp+k*1.571;ring.push([Math.cos(an)*0.16,0,Math.sin(an)*0.16])}
     for(let k=0;k<4;k++){const q0=ring[k],q1=ring[(k+1)%4];for(const tip of P){const v=(p)=>[X+p[0],cy+p[1],Z+p[2]];if(tip[1]>0)tri(g,v(q0),v(q1),v(tip),[0,0,0],[col[0]*(0.85+k*0.05),col[1]*(0.85+k*0.05),col[2],1]);else tri(g,v(q1),v(q0),v(tip),[0,0,0],[col[0]*0.7,col[1]*0.7,col[2]*0.8,1])}}break}
    case 'runedoor':{const sink=R.open?-1.35:0;boxr(a,X-0.46,X+0.46,Z-0.12,Z+0.12,Y+sink,Y+1.45+sink,stone);
     if(!R.open)for(let k=0;k<8;k++){const a0=k/8*6.283,a1=(k+1)/8*6.283,rr=0.2,cy=Y+0.8,z=Z+0.125;quad(g,[X+Math.cos(a0)*rr,cy+Math.sin(a0)*rr,z],[X+Math.cos(a1)*rr,cy+Math.sin(a1)*rr,z],[X+Math.cos(a1)*(rr-0.05),cy+Math.sin(a1)*(rr-0.05),z],[X+Math.cos(a0)*(rr-0.05),cy+Math.sin(a0)*(rr-0.05),z],[0,0,0],gc)}break}
    case 'firejet':boxr(a,X-0.25,X+0.25,Z-0.25,Z+0.25,Y,Y+0.22,stone);boxr(a,X-0.15,X+0.15,Z-0.15,Z+0.15,Y+0.22,Y+0.25,dark);break;
    case 'spikes':{boxr(a,X-0.42,X+0.42,Z-0.42,Z+0.42,Y,Y+0.06,dark);const h=R.up?0.55:0.07;for(let i=0;i<3;i++)for(let j=0;j<3;j++)MD.cone(a,X-0.27+i*0.27,Z-0.27+j*0.27,Y+0.06,Y+0.06+h,0.05,4,[0.78,0.78,0.82,1],i*3+j,false);break}
    case 'plate':boxr(a,X-0.36,X+0.36,Z-0.36,Z+0.36,Y,Y+0.06,stone);for(const [x0,x1,z0,z1] of [[-0.36,0.36,-0.36,-0.32],[-0.36,0.36,0.32,0.36],[-0.36,-0.32,-0.36,0.36],[0.32,0.36,-0.36,0.36]])quad(g,[X+x0,Y+0.065,Z+z1],[X+x1,Y+0.065,Z+z1],[X+x1,Y+0.065,Z+z0],[X+x0,Y+0.065,Z+z0],[0,0,0],gc);break;
    case 'lever':{boxr(a,X-0.14,X+0.14,Z-0.1,Z+0.1,Y,Y+0.18,dark);const s=R.on?1:-1,tx=X+s*0.28,ty=Y+0.62;for(let k=0;k<6;k++){const f0=k/6,f1=(k+1)/6;boxr(a,X+(tx-X)*f0-0.03,X+(tx-X)*f0+0.03,Z-0.03,Z+0.03,Y+0.18+(ty-Y-0.18)*f0,Y+0.18+(ty-Y-0.18)*f1,wood)}MD.blob(a,tx,ty,Z,0.07,0.07,0.07,[0.8,0.22,0.18,1],r.x,0.1);break}
    case 'lamp':boxr(a,X-0.12,X+0.12,Z-0.12,Z+0.12,Y,Y+0.06,dark);boxr(a,X-0.045,X+0.045,Z-0.045,Z+0.045,Y,Y+0.86,dark);   /* a lamp: base, post, an iron cage round a glass globe, a cap; the globe is pale glass unlit and warm light when its circuit has mana */
      for(const [cx,cz] of [[-0.13,-0.13],[0.13,-0.13],[-0.13,0.13],[0.13,0.13]])boxr(a,X+cx-0.015,X+cx+0.015,Z+cz-0.015,Z+cz+0.015,Y+0.86,Y+1.18,dark);boxr(a,X-0.15,X+0.15,Z-0.15,Z+0.15,Y+0.84,Y+0.88,dark);
      MD.blob(g,X,Y+1.02,Z,0.12,0.13,0.12,R.pow?[1,0.9,0.6,1]:[0.62,0.64,0.72,1],r.y,0.05);MD.cone(a,X,Z,Y+1.18,Y+1.34,0.19,6,dark,r.x,false);break;
    case 'bell':boxr(a,X-0.36,X-0.3,Z-0.04,Z+0.04,Y,Y+1.1,wood);boxr(a,X+0.3,X+0.36,Z-0.04,Z+0.04,Y,Y+1.1,wood);boxr(a,X-0.36,X+0.36,Z-0.05,Z+0.05,Y+1.06,Y+1.14,wood);MD.cone(a,X,Z,Y+0.6,Y+1.04,0.2,8,[0.8,0.64,0.26,1],r.x,false);break
    // Gates (Gates.dm). A portcullis: a grating of timber and iron across the gap. Under a wall walk's gate (v3gateArch)
    // it hangs in that gate's slot (a stone arch: the outer slot, fitting the arch; a timber gatehouse: between its
    // posts) and goes up into the masonry, its teeth showing, never above 2.2 (the walk is at V3.STOREY); with no walk
    // over it, it has its own posts and lintel. r.dir: 4 the walls east and west, 1 north and south.
    case 'portcullis':{const T3=V3.terrain,arch=!!(T3&&V3.walkTiles&&V3.walkTiles.has(r.x+','+r.y)),G=arch?v3gateGeom((p,q)=>v3kindAt(T3.x0+p,T3.y0+q),r.x-T3.x0,r.y-T3.y0,r.x,r.y):null;
     const ew=G?G.ew:(r.dir===4||r.dir===8),bx=(u0,u1,v0,v1,y0,y1,c)=>{const U0=Math.min(u0,u1),U1=Math.max(u0,u1),V0=Math.min(v0,v1),V1=Math.max(v0,v1);if(ew)boxr(a,X+U0,X+U1,Z+V0,Z+V1,y0,y1,c);else boxr(a,X+V0,X+V1,Z+U0,Z+U1,y0,y1,c)};
     const stoneArch=G&&!G.wood,vc=stoneArch?(G.outerPos||1)*0.355:0,half=stoneArch?0.36:G?0.3:0.4,cap=G?2.2:1.95,
      opTop=u=>stoneArch?1.3+Math.sqrt(Math.max(0,0.16-u*u)):G?1.5:1.85,tim=[0.33,0.23,0.14,1],irn=[0.36,0.36,0.4,1];
     const PC=(dx,dy)=>runes.some(t=>t.rune&&t.rune.id==='portcullis'&&t.x===r.x+dx&&t.y===r.y+dy),nLo=!G&&(ew?PC(-1,0):PC(0,1)),nHi=!G&&(ew?PC(1,0):PC(0,-1));   // pieces beside it in a wide gap
     if(!G){if(!nLo)bx(-0.5,-0.4,-0.12,0.12,Y,Y+2.0,dark);if(!nHi)bx(0.4,0.5,-0.12,0.12,Y,Y+2.0,dark);bx(-0.5,0.5,-0.12,0.12,Y+1.88,Y+2.02,dark)}
     for(let k=0;k<5;k++){const u=-half+0.06+k*(half*2-0.12)/4,t=opTop(u),b0=R.open?t-0.2:0,b1=R.open?Math.min(cap,t-0.2+t):t;
      bx(u-0.025,u+0.025,vc-0.02,vc+0.02,Y+b0+0.08,Y+b1,tim);bx(u-0.015,u+0.015,vc-0.015,vc+0.015,Y+b0,Y+b0+0.08,irn)}
     for(let k=0;k<4;k++){const yr=0.3+k*0.38,y=(R.open?opTop(0)-0.2:0)+yr;if(y>cap-0.05)break;
      const w=stoneArch&&y>1.3?Math.sqrt(Math.max(0,0.16-(y-1.3)*(y-1.3)))-0.02:half;if(!R.open&&w<=0.05)continue;bx(nLo?-0.5:-Math.min(w,half),nHi?0.5:Math.min(w,half),vc-0.025,vc+0.025,Y+y,Y+y+0.045,k%2?tim:irn)}break}
    // A drawbridge: the pieces touching side by side are one bridge across the moat (as wide as its gateway, as long
    // as the moat is wide). Its bank row (r.dir: the hinge side) draws it: hinge posts at its outer edges and chains;
    // down, the chains run to the far end (the terrain lays the deck); up, the whole deck stands on end at the hinge.
    case 'drawbridge':{const d=r.dir||4,hx=d===4?1:d===8?-1:0,hz=d===2?1:d===1?-1:0,px=-hz,pz=hx,DB=new Set();for(const t of runes)if(t.rune&&t.rune.id==='drawbridge')DB.add(t.x+','+t.y);
     const has=(x,y)=>DB.has(x+','+y);if(has(r.x+hx,r.y-hz))break;let L=1;while(L<6&&has(r.x-hx*L,r.y+hz*L))L++;
     const sA=has(r.x+px,r.y-pz),sB=has(r.x-px,r.y+pz),wA=sA?0.5:0.45,wB=sB?0.5:0.45,ex=X+hx*0.5,ez=Z+hz*0.5,tim=[0.42,0.29,0.17,1],chain=[0.3,0.3,0.32,1],PH=R.open?1.45:Math.max(1.45,L+0.35);
     const rect=(h0,h1,u0,u1,y0,y1,c)=>{const xs=[ex-hx*h0+px*u0,ex-hx*h1+px*u1],zs=[ez-hz*h0+pz*u0,ez-hz*h1+pz*u1];boxr(a,Math.min(...xs),Math.max(...xs),Math.min(...zs),Math.max(...zs),y0,y1,c)};
     const tops=[];for(const [s,on] of [[1,!sA],[-1,!sB]])if(on){const x=ex+px*0.46*s,z=ez+pz*0.46*s;boxr(a,x-0.06,x+0.06,z-0.06,z+0.06,Y-0.2,Y+PH,dark);tops.push([[x,Y+PH-0.05,z],s])}
     if(R.open){for(const [t,s] of tops)MD.rod(a,t,[X-hx*(L-0.55)+px*0.42*s,Y+0.12,Z-hz*(L-0.55)+pz*0.42*s],0.015,3,chain,r.x+s)}
     else{const H=L*0.98;rect(0,0.12,-wB,wA,Y,Y+H,tim);for(let y=0.25;y<H-0.1;y+=0.33)rect(-0.01,0.13,-wB-0.01,wA+0.01,Y+y,Y+y+0.04,dark);
      for(const [t,s] of tops)MD.rod(a,t,[ex-hx*0.12+px*0.42*s,Y+H-0.02,ez-hz*0.12+pz*0.42*s],0.015,3,chain,r.y+s)}break}}}
  for(let i=3;i<g.length;i+=12){g[i]=0;g[i+1]=0;g[i+2]=0}
  if(a.length){gl.bindBuffer(gl.ARRAY_BUFFER,V3.dyn);v3up(a);v3draw(V3.dyn,a.length/12,null)}
  if(g.length){gl.bindBuffer(gl.ARRAY_BUFFER,V3.dyn);v3up(g);v3draw(V3.dyn,g.length/12,null)}}
 // Fire: flickering low-poly flames, orange outside, yellow inside.
 const fireTex=flames.length?v3tex('rb-breath-dragon.png'):null,fireFx=!!(fireTex&&fireTex.ok);   // asked for only when something burns: the server sends it then (Beasts.dm RmSendFireFx)
  V3.flameTiles=fireFx?flames:[];   // with the fire particles loaded, flames are drawn by v3breathFx
  if(flames.length){const a=[],tt=ts/1000;for(const f of flames){const [X,,Z]=v3world(f),Y=v3groundAt(f.x,f.y);if(fireFx){quad(a,[X-0.42,Y+0.02,Z+0.42],[X+0.42,Y+0.02,Z+0.42],[X+0.42,Y+0.02,Z-0.42],[X-0.42,Y+0.02,Z-0.42],[0,0,0],[0.42,0.15,0.05,1]);continue}
   for(let k=0;k<3;k++){const sd=f.x*7+f.y*13+k*31,ox=(MD.h(f.x,f.y,k)-0.5)*0.55,oz=(MD.h(f.x,f.y,k+5)-0.5)*0.55,h=0.55+0.3*Math.sin(tt*9+sd)+0.25*MD.h(f.x,f.y,k+3);
    const lean=Math.sin(tt*5+sd)*0.08;MD.cone(a,X+ox+lean,Z+oz,Y,Y+h,0.19,5,[1,0.36,0.06,1],sd,false);MD.cone(a,X+ox+lean*0.6,Z+oz-0.06,Y,Y+h*0.8,0.13,5,[1,0.72,0.18,1],sd+1,false);MD.cone(a,X+ox+lean*0.3,Z+oz-0.12,Y,Y+h*0.5,0.08,4,[1,0.96,0.6,1],sd+2,false)}
   quad(a,[X-0.42,Y+0.02,Z+0.42],[X+0.42,Y+0.02,Z+0.42],[X+0.42,Y+0.02,Z-0.42],[X-0.42,Y+0.02,Z-0.42],[0,0,0],[0.42,0.15,0.05,1])}
  for(let i=3;i<a.length;i+=12){a[i]=0;a[i+1]=0;a[i+2]=0}
  gl.bindBuffer(gl.ARRAY_BUFFER,V3.dyn);v3up(a);v3draw(V3.dyn,a.length/12,null)}
 // Vapours: soft see-through puffs in the gas's colour, thicker where there's more, drifting.
 // Vapours and smoke: soft puffs that drift up and fade (a texture made here, v3smokeTex), see-through and
 // unlit, in place of the old solid blobs; dark smoke rises off whatever burns.
 if(vapours.length||flames.length){const S=v3smokeTex(),a=[],tt=ts/1000,cp=Math.cos(V3.pitch),sp=Math.sin(V3.pitch),up=[-Math.sin(V3.yaw)*sp,cp,-Math.cos(V3.yaw)*sp];
  const puff=(x,y,z,r,c,f,al)=>{if(al<=0.01)return;const u0=f/4+0.004,u1=(f+1)/4-0.004,rx=right[0]*r,rz=right[2]*r,ux=up[0]*r,uy=up[1]*r,uz=up[2]*r;
   quad(a,[x-rx-ux,y-uy,z-rz-uz],[x+rx-ux,y-uy,z+rz-uz],[x+rx+ux,y+uy,z+rz+uz],[x-rx+ux,y+uy,z-rz+uz],[0,0,0],[c[0],c[1],c[2],Math.min(0.9,al)],[u0,1,u1,1,u1,0,u0,0])};
  // How much gas there is: the cloud's alpha (Vapours.dm RemasterAirShow: 70 at a trace, 30 more per unit of gas, to 230).
  // A trace is barely there and a thick cloud clearly one (a trace drew at 0.2, so many thin tiles stacked into a haze).
  // Puffs thin out close to the eye and over your units and stations (the fp slots, as trees and rock do), so gas never
  // fills the screen or hides your own people. A body's rot is a smell, not a fog: one thin wisp off the body, and flies;
  // plague (miasma, from a brew) is a cloud like the others.
  const E=V3.eye,FP=V3.fpF,m=vp,clear=(x,y,z,rad=1.8)=>{let k=1;const d=Math.hypot(x-E[0],y-E[1],z-E[2]);if(d<4)k*=Math.max(0,(d-1.2)/2.8);
   if(FP){const w=x*m[3]+y*m[7]+z*m[11]+m[15];if(w>0){const sx=((x*m[0]+y*m[4]+z*m[8]+m[12])/w*0.5+0.5)*W,sy=((x*m[1]+y*m[5]+z*m[9]+m[13])/w*0.5+0.5)*H,sz=(x*m[2]+y*m[6]+z*m[10]+m[14])/w*0.5+0.5;
    for(let i=0;i<12;i++){const r=FP[i*4+2];if(r<=0||sz>=FP[i*4+3])continue;const dd=Math.hypot(sx-FP[i*4],(sy-FP[i*4+1])*0.7)/(r*rad);if(dd<1)k*=0.12+0.88*dd*dd}}}return k};
  let flies=0;
  for(const v of vapours){const [X,,Z]=v3world(v),Y=v3groundAt(v.x,v.y),q=v.vap||80,s=Math.max(0,Math.min(1,(q-78)/140)),g=hexrgb(v.tint||'#909098'),c=[g[0]*0.7+0.3,g[1]*0.7+0.3,g[2]*0.7+0.3];
   if(String(v.tint||'').toLowerCase()==='#7f8f4c'){const pk=0.75*Math.min(1,0.45+s*2);   // a body's rot (Vapours.dm "rot": it stays on the body's tile)
    // a small green mist over the body, as easy to see as a poison cloud but one tile, and a couple of flies; it clears
    // only right over a unit (it is one tile: wider, it vanished between people)
    for(let k=0;k<7;k++){const ph=(tt*(0.07+MD.h(v.x,v.y,k+9)*0.05)+k/7)%1,an=v.x*3+v.y*5+k*2.4+tt*0.15,rr=0.1+0.25*MD.h(v.x,v.y,k+2),x=X+Math.cos(an)*rr,y=Y+0.15+ph*0.9,z=Z+Math.sin(an)*rr;
     puff(x,y,z,0.5+ph*0.4,[0.62,0.86,0.4],(k+v.x+v.y)%4,pk*Math.sin(ph*Math.PI)*clear(x,y,z,0.45))}
    if(s>0.05&&flies<40)for(let k=0;k<2;k++,flies++){const an=tt*(2.6+k*0.9)+MD.h(v.x,v.y,k+31)*6.3,rr=0.18+0.12*Math.sin(tt*1.7+k),x=X+Math.cos(an)*rr,y=Y+0.3+0.12*Math.sin(tt*3.1+k*2),z=Z+Math.sin(an*1.3)*rr;
     puff(x,y,z,0.07,[0.05,0.05,0.04],0,Math.min(1,s*4)*(Math.hypot(x-E[0],y-E[1],z-E[2])<1.5?0:1))}
    continue}
   const peak=0.6*Math.pow(s,0.75),n=q>150?7:5;if(peak<0.03)continue;
   for(let k=0;k<n;k++){const ph=(tt*(0.08+MD.h(v.x,v.y,k+9)*0.06)+k/n)%1,an=v.x*3+v.y*5+k*2.4+tt*0.15,rr=0.12+0.3*MD.h(v.x,v.y,k+2),x=X+Math.cos(an)*rr,y=Y+0.3+ph*1.0,z=Z+Math.sin(an)*rr;
    puff(x,y,z,0.45+q/600+ph*0.35,c,(k+v.x+v.y)%4,peak*Math.sin(ph*Math.PI)*clear(x,y,z))}}
  for(const t of flames){const [X,,Z]=v3world(t),Y=v3groundAt(t.x,t.y),sd=t.x*7+t.y*13;
   for(let k=0;k<3;k++){const ph=(tt*0.22+k/3+MD.h(sd,k,81)*0.2)%1,dr=Math.sin(tt*0.5+sd+k)*0.25*ph;
    puff(X+dr,Y+0.8+ph*1.8,Z+dr*0.5,0.3+ph*0.55,[0.3,0.29,0.28],(k+sd)%4,0.45*Math.sin(ph*Math.PI)*(1-ph*0.4))}}
  if(S&&a.length){gl.enable(gl.BLEND);gl.blendFunc(gl.SRC_ALPHA,gl.ONE_MINUS_SRC_ALPHA);gl.depthMask(false);gl.uniform1f(L.soft,1);
   gl.bindBuffer(gl.ARRAY_BUFFER,V3.dyn);v3up(a);v3draw(V3.dyn,a.length/12,S);
   gl.uniform1f(L.soft,0);gl.depthMask(true);gl.disable(gl.BLEND)}}
 if(!V3.lite){v3drawFoam(ts);v3clouds(ts);v3fireFx(ts);v3ambient(ts)}v3bars(vp,W,H);v3hover();v3marks()}
// Ambient life over the land, a few dozen at a time round the view (world-look): snow falling in winter, leaves
// drifting down from trees in autumn, fireflies over grass and trees on summer and spring nights. Soft round dots (the
// contact shadow's radial texture), fireflies added as light. Nothing underground or in a cutaway.
function v3ambient(ts){const gl=V3.gl,L=V3.loc,under=V3.z===2||V3.z===4,sn=String(V3.seasonOverride||(typeof model!=='undefined'&&model&&model.season)||'').toLowerCase();
 const kind=under||!V3.soft||V3.mode==='cut'?'':sn==='winter'?'snow':(sn==='fall'||sn==='autumn')?'leaf':V3.night&&(sn==='summer'||sn==='spring')?'fly':'';
 const P=V3.ambP||(V3.ambP=[]),now=ts/1000,dt=Math.min(0.1,Math.max(0,now-(V3.ambT||now)));V3.ambT=now;if(!kind){P.length=0;return}
 if(P.kind!==kind){P.length=0;P.kind=kind}
 const R=Math.max(7,Math.min(30,V3.dist*1.15)),cx=V3.cx,cy=V3.cy,want=kind==='snow'?Math.round(R*9):kind==='leaf'?Math.round(R*1.6):Math.round(R*2.2),rnd=Math.random;
 for(let tries=0;P.length<want&&tries<want*3;tries++){const x=cx+(rnd()*2-1)*R,y=cy+(rnd()*2-1)*R*0.8,K=v3kindAt(Math.round(x),Math.round(y));
  if(kind==='leaf'){if(!K||K.kind!=='tree')continue;P.push({x:x+(rnd()-0.5)*0.6,y:y+(rnd()-0.5)*0.6,h:1.2+rnd()*0.8,vx:(rnd()-0.5)*0.3,ph:rnd()*6.3,life:0,col:[[0.78,0.46,0.12],[0.84,0.62,0.16],[0.62,0.26,0.08],[0.7,0.55,0.2]][Math.floor(rnd()*4)]});continue}
  if(kind==='fly'){if(!K||!(K.kind==='tree'||(K.kind==='floor'&&String(K.state||'').includes('grass'))||K.kind==='floor'&&!K.state))continue;P.push({x,y,h:0.25+rnd()*1.1,ph:rnd()*6.3,life:0,end:5+rnd()*6,sx:(rnd()-0.5)*0.4,sy:(rnd()-0.5)*0.4});continue}
  P.push({x,y,h:2+rnd()*4.5,ph:rnd()*6.3,life:0,vy:0.55+rnd()*0.4})}
 const cp=Math.cos(V3.pitch),sp=Math.sin(V3.pitch),rt=[Math.cos(V3.yaw),0,-Math.sin(V3.yaw)],up=[-Math.sin(V3.yaw)*sp,cp,-Math.cos(V3.yaw)*sp],a=(V3.ambV||(V3.ambV=new VA())).reset();
 const dot=(X,Y,Z,r,c)=>{quad(a,[X-rt[0]*r-up[0]*r,Y-up[1]*r,Z-rt[2]*r-up[2]*r],[X+rt[0]*r-up[0]*r,Y-up[1]*r,Z+rt[2]*r-up[2]*r],[X+rt[0]*r+up[0]*r,Y+up[1]*r,Z+rt[2]*r+up[2]*r],[X-rt[0]*r+up[0]*r,Y+up[1]*r,Z-rt[2]*r+up[2]*r],QN0,c)};
 for(let i=P.length-1;i>=0;i--){const p=P[i];p.life+=dt;const g=v3groundAt(p.x,p.y);let gone=Math.abs(p.x-cx)>R*1.2||Math.abs(p.y-cy)>R;
  if(kind==='snow'){p.h-=p.vy*dt;p.x+=Math.sin(now*0.7+p.ph)*0.15*dt+0.08*dt;if(p.h<=0)gone=true;else dot(p.x,g+p.h,-p.y,0.05,[1,1,1,Math.min(1,p.life*2)])}
  else if(kind==='leaf'){if(p.h>0.03){p.h=Math.max(0.03,p.h-0.32*dt);p.x+=(p.vx+Math.sin(now*2.1+p.ph)*0.35)*dt;p.y+=Math.cos(now*1.7+p.ph)*0.2*dt}else if(p.life>18)gone=true;const c=p.col;dot(p.x,g+p.h,-p.y,0.045,[c[0],c[1],c[2],Math.min(1,p.life*3)*(p.h<=0.03?Math.max(0,1-(p.life-12)/6):1)])}
  else{if(p.life>p.end)gone=true;p.x+=(p.sx+Math.sin(now*0.9+p.ph)*0.25)*dt;p.y+=(p.sy+Math.cos(now*0.8+p.ph*1.3)*0.25)*dt;const b=(0.3+0.7*Math.max(0,Math.sin(now*2.2+p.ph*3))**2)*Math.min(1,p.life,p.end-p.life);dot(p.x,g+p.h+Math.sin(now*1.3+p.ph)*0.12,-p.y,0.11,[0.8,1,0.35,Math.min(1,b*1.2)])}
  if(gone)P.splice(i,1)}
 if(!a.length)return;gl.enable(gl.BLEND);gl.depthMask(false);gl.bindBuffer(gl.ARRAY_BUFFER,V3.dyn);v3up(a);
 if(kind==='fly'){gl.blendFunc(gl.SRC_ALPHA,gl.ONE);gl.uniform1f(L.addm,1);gl.uniform1f(L.soft,1);v3draw(V3.dyn,a.length/12,V3.soft);gl.uniform1f(L.addm,0)}
 else{gl.blendFunc(gl.SRC_ALPHA,gl.ONE_MINUS_SRC_ALPHA);gl.uniform1f(L.soft,1);v3draw(V3.dyn,a.length/12,V3.soft)}
 gl.uniform1f(L.soft,0);gl.blendFunc(gl.SRC_ALPHA,gl.ONE_MINUS_SRC_ALPHA);gl.depthMask(true);gl.disable(gl.BLEND)}
// The shore's foam: a thin pale line where the water meets each bank (worked out with the terrain), a fainter wider
// band round it, both breathing slowly along the shore.
function v3drawFoam(ts){const S=V3.foamSegs;if(!S||!S.length||V3.z===2||V3.z===4)return;const gl=V3.gl,L=V3.loc,t=ts/1000,a=(V3.foamV||(V3.foamV=new VA())).reset(),cx=V3.cx,cy=V3.cy,R=Math.max(20,V3.dist*2.2);
 for(let i=0;i<S.length;i+=5){const x0=S[i],z0=S[i+1],x1=S[i+2],z1=S[i+3],y=S[i+4]+0.006;if(Math.abs(x0-cx)>R||Math.abs(-z0-cy)>R)continue;let nx=-(z1-z0),nz=x1-x0;const l=Math.hypot(nx,nz)||1;nx/=l;nz/=l;
  const p=0.6+0.4*Math.sin(t*1.5+(x0+z0)*2.1),q=0.6+0.4*Math.sin(t*1.5+(x1+z1)*2.1);
  for(let b=0;b<2;b++){const w=b?0.035:0.1,al=b?0.42:0.16,c=b?0.95:0.86,c2=c*1.02,ap=al*p,aq=al*q,ax=nx*w,az=nz*w;   /* a faint wide band, then the bright line */
   a.v(x0-ax,y,z0-az,0,0,0,0,0,c,c,c2,ap);a.v(x1-ax,y,z1-az,0,0,0,0,0,c,c,c2,aq);a.v(x1+ax,y,z1+az,0,0,0,0,0,c,c,c2,aq);a.v(x0-ax,y,z0-az,0,0,0,0,0,c,c,c2,ap);a.v(x1+ax,y,z1+az,0,0,0,0,0,c,c,c2,aq);a.v(x0+ax,y,z0+az,0,0,0,0,0,c,c,c2,ap)}}
 if(!a.length)return;gl.enable(gl.BLEND);gl.blendFunc(gl.SRC_ALPHA,gl.ONE_MINUS_SRC_ALPHA);gl.depthMask(false);gl.uniform1f(L.soft,1);gl.bindBuffer(gl.ARRAY_BUFFER,V3.dyn);v3up(a);v3draw(V3.dyn,a.length/12,null);gl.uniform1f(L.soft,0);gl.depthMask(true);gl.disable(gl.BLEND)}
// Clouds (the owner, 10-27: "on zoom out 60 we should be able to see cloud wisp"): far out over the surface, thin wisps
// high over the land, drawn from the same drifting pattern as the cloud shadows (the shader, alpha 0.88), fading in from
// zoom 30 to their fullest at 55 and up, never over the caves; fainter on a clear day, faint and grey at night.
function v3clouds(ts){if(!(V3.z===1||V3.z===3)||V3.noClouds)return;const f=Math.min(1,Math.max(0,(V3.dist-30)/25));if(f<=0)return;
 const gl=V3.gl,L=V3.loc,a=(V3.cloudV||(V3.cloudV=new VA())).reset(),cx=V3.cx,cy=V3.cy,R=Math.max(60,V3.dist*2.6),N=12,y=(V3.curLift||0)+14+(V3.z===3&&V3.SKYH?V3.SKYH:0),k=f*f*(3-2*f)*0.62,th=V3.night?0.45:1;
 for(let j=0;j<N;j++)for(let i=0;i<N;i++){const x0=cx-R+2*R*i/N,x1=cx-R+2*R*(i+1)/N,z0=-(cy-R+2*R*j/N),z1=-(cy-R+2*R*(j+1)/N);
  a.v(x0,y,z0,0,1,0,0,0,k,th,1,0.88);a.v(x1,y,z0,0,1,0,0,0,k,th,1,0.88);a.v(x1,y,z1,0,1,0,0,0,k,th,1,0.88);a.v(x0,y,z0,0,1,0,0,0,k,th,1,0.88);a.v(x1,y,z1,0,1,0,0,0,k,th,1,0.88);a.v(x0,y,z1,0,1,0,0,0,k,th,1,0.88)}
 gl.enable(gl.BLEND);gl.blendFunc(gl.SRC_ALPHA,gl.ONE_MINUS_SRC_ALPHA);gl.depthMask(false);gl.uniform1f(L.soft,1);gl.bindBuffer(gl.ARRAY_BUFFER,V3.dyn);v3up(a);v3draw(V3.dyn,a.length/12,null);gl.uniform1f(L.soft,0);gl.depthMask(true);gl.disable(gl.BLEND)}
// Fires glow (world-look): a flickering halo of added light over each campfire, forge and burning tile near the view,
// and embers rising off it and winking out; stronger at night and underground, where the fire is the light.
function v3fireFx(ts){const gl=V3.gl,L=V3.loc,now=ts/1000,dk=V3.z===2||V3.z===4?1:Math.min(1,V3.G?V3.G.nk:V3.night?1:0),dark=dk>0.5,g=(V3.fireV||(V3.fireV=new VA())).reset();if(!V3.soft)return;
 const cp=Math.cos(V3.pitch),sp=Math.sin(V3.pitch),rt=[Math.cos(V3.yaw),0,-Math.sin(V3.yaw)],up=[-Math.sin(V3.yaw)*sp,cp,-Math.cos(V3.yaw)*sp];
 const dot=(X,Y,Z,r,c)=>{quad(g,[X-rt[0]*r-up[0]*r,Y-up[1]*r,Z-rt[2]*r-up[2]*r],[X+rt[0]*r-up[0]*r,Y-up[1]*r,Z+rt[2]*r-up[2]*r],[X+rt[0]*r+up[0]*r,Y+up[1]*r,Z+rt[2]*r+up[2]*r],[X-rt[0]*r+up[0]*r,Y+up[1]*r,Z-rt[2]*r+up[2]*r],QN0,c)};
 let n=0;for(const t of V3.things){const m=t.m3||'';let h=0,s=0;if(m==='station:campfire'){h=0.32;s=1}else if(/^station:(forge|smelter|melter)/.test(m)&&t.half!=='R'){h=0.82;s=0.7}else if(t.flame){h=0.45;s=1.2}else continue;
  if(!v3visible(t)||Math.abs(t.x-V3.cx)>28||Math.abs(t.y-V3.cy)>22||n++>40)continue;const [X,,Z]=v3world(t),Y=(t.ly||v3groundAt(t.x,t.y))+h,seed=t.x*31+t.y*17,fl=0.82+0.18*Math.sin(now*11+seed)*Math.sin(now*7.3+seed*0.7),k=(0.22+0.33*dk)*s*fl;
  const E=V3.eye,ex=E[0]-X,ey=E[1]-Y,ez=E[2]-Z,el=Math.hypot(ex,ey,ez)||1,R=(0.65+0.35*dk)*s,mv=Math.min(el*0.5,R*1.6),hx=X+ex/el*mv,hy=Y+ey/el*mv,hz=Z+ez/el*mv;
  dot(hx,hy,hz,R,[1,0.52,0.18,k*0.75]);dot(hx,hy+0.04,hz,0.3*s,[1,0.8,0.45,Math.min(1,k*1.3)]);
  for(let e=0;e<(dark?6:3);e++){const ph=(now*(0.55+MD.h(seed,e,3)*0.4)+MD.h(seed,e,4))%1,dr=Math.sin(now*1.7+e*2.1+seed)*0.12*ph,b=(1-ph)*(0.6+0.4*dk)*(0.5+0.5*Math.sin(now*17+e*5));
   dot(X+(MD.h(seed,e,5)-0.5)*0.3+dr,Y+0.05+ph*1.3*s,Z+(MD.h(seed,e,6)-0.5)*0.3,0.03,[1,0.55,0.14,Math.min(1,b*1.3)])}}
 if(!g.length)return;gl.enable(gl.BLEND);gl.blendFunc(gl.SRC_ALPHA,gl.ONE);gl.depthMask(false);gl.uniform1f(L.addm,1);gl.uniform1f(L.soft,1);gl.bindBuffer(gl.ARRAY_BUFFER,V3.dyn);v3up(g);v3draw(V3.dyn,g.length/12,V3.soft);
 gl.uniform1f(L.soft,0);gl.uniform1f(L.addm,0);gl.blendFunc(gl.SRC_ALPHA,gl.ONE_MINUS_SRC_ALPHA);gl.depthMask(true);gl.disable(gl.BLEND)}
// The 2D program (screen pixels, a colour per corner) for the bars and the vignette.
function v3ui(){const gl=V3.gl;let U=V3.ui;
 if(U===undefined){const sh=(ty,src)=>{const s=gl.createShader(ty);gl.shaderSource(s,src);gl.compileShader(s);if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))console.error(gl.getShaderInfoLog(s));return s};const pr=gl.createProgram();
  gl.attachShader(pr,sh(gl.VERTEX_SHADER,'attribute vec2 p;attribute vec4 c;uniform vec2 res;varying vec4 vc;void main(){vc=c;gl_Position=vec4(p.x/res.x*2.0-1.0,1.0-p.y/res.y*2.0,0.0,1.0);}'));
  gl.attachShader(pr,sh(gl.FRAGMENT_SHADER,'precision mediump float;varying vec4 vc;void main(){gl_FragColor=vc;}'));gl.linkProgram(pr);
  U=V3.ui=gl.getProgramParameter(pr,gl.LINK_STATUS)?{pr,p:gl.getAttribLocation(pr,'p'),c:gl.getAttribLocation(pr,'c'),res:gl.getUniformLocation(pr,'res'),buf:gl.createBuffer(),f:new Float32Array(36*8*64)}:null}
 return U}
// (No screen-edge vignette since 2026-10-25: the user wants light from the sun and sky only, no darkening that
// goes with the camera.)
// Health bars, drawn last in screen pixels so they stay crisp at any zoom and are never hidden by the world: a dark
// frame, the health in the side's colour with a lighter top, quarter ticks, and the chunk just lost shown pale while
// it drains (StarCraft-like). One small 2D program; V3.barL holds 8 numbers a bar from the unit loop.
// A health ring: the ring's own texture drawn as wedges round the unit, filled clockwise from the side nearest the
// camera (the far side is behind the unit) to its health in the ring's colour, then the pale trail of the last blow,
// the rest dark. Your units that are not selected show green, amber or red, like the bars did. Each part is an arc
// record (v3drawInst 4: q from 0 to 1 round from the near side, clockwise on screen, in 40ths of a turn), its wedges
// laid by the vertex shader.
const RC_SEL=[1,0.85,0.32,1],RC_MINE=[0.5,0.9,0.45,0.3],RC_ALLY=[0.3,0.88,0.78,0.7],RC_WAR=[0.95,0.3,0.25,0.8],RC_PLAYER=[0.4,0.6,1,0.6],RC_PEACE=[0.95,0.8,0.35,0.6],RC_FOE=[0.95,0.35,0.3,0.8];   /* the rings' colours (never change them) */
const HPRN=40,HPDARK=[0.06,0.05,0.04,0.62],HPTRAIL=[1,0.9,0.66,0.95],HPOK=[0.36,0.84,0.3,0.9],HPMID=[0.98,0.74,0.2,0.9],HPLOW=[0.94,0.27,0.2,0.9];
function v3hpRing(a,X,y,Z,r,c,f,lag){
 const span=(q0,q1,col)=>{if(q1>q0)a.v(X,y,Z,r,q0,q1,Math.max(1,Math.ceil((q1-q0)*HPRN)),0,col[0],col[1],col[2],col[3])};
 span(0,f,c);span(f,Math.max(f,lag),HPTRAIL);span(Math.max(f,lag),1,HPDARK)}
function v3bars(vp,W,H){const B=V3.barL;if(!B||!B.length)return;const gl=V3.gl,U=v3ui();
 if(!U)return;const m=vp,dpr=W/Math.max(1,$('world3d').clientWidth),zs=Math.max(0.85,Math.min(1.3,Math.sqrt(12/Math.max(4,V3.dist)))),bh=Math.max(3,Math.round(5*dpr)),bd=Math.max(1,Math.round(dpr)),tk=Math.max(1,Math.round(dpr*0.75));
 let n=0,F=U.f,r=0,g=0,b=0,a=0;const V=(x,y)=>{F[n++]=x;F[n++]=y;F[n++]=r;F[n++]=g;F[n++]=b;F[n++]=a},R=(x0,y0,x1,y1,r1,g1,b1,a1)=>{if(x1<=x0||y1<=y0)return;if(n+36>F.length){const G=new Float32Array(F.length*2);G.set(F);F=U.f=G}r=r1;g=g1;b=b1;a=a1;V(x0,y0);V(x1,y0);V(x1,y1);V(x0,y0);V(x1,y1);V(x0,y1)};
 for(let i=0;i<B.length;i+=8){const X=B[i],Y=B[i+1],Z=B[i+2],f=B[i+3],lag=B[i+4],own=B[i+5],big=B[i+6];const cx=X*m[0]+Y*m[4]+Z*m[8]+m[12],cy=X*m[1]+Y*m[5]+Z*m[9]+m[13],cw=X*m[3]+Y*m[7]+Z*m[11]+m[15];if(cw<=0.01)continue;
  const sx=(cx/cw*0.5+0.5)*W,sy=(0.5-cy/cw*0.5)*H;if(sx<-60||sx>W+60||sy<-20||sy>H+40)continue;const bw=Math.round((big?56:34)*dpr*zs),x0=Math.round(sx-bw/2),y0=Math.round(sy-bh-dpr),fw=Math.round(bw*f),lw=Math.round(bw*lag);
  const c=own?(f>0.5?[0.36,0.84,0.3]:f>0.25?[0.98,0.74,0.2]:[0.94,0.27,0.2]):[0.9,0.22,0.17];
  R(x0-bd,y0-bd,x0+bw+bd,y0+bh+bd,0.03,0.025,0.02,0.86);R(x0,y0,x0+bw,y0+bh,0.2,0.06,0.05,0.92);if(lw>fw)R(x0+fw,y0,x0+lw,y0+bh,0.98,0.88,0.62,0.95);
  R(x0,y0,x0+fw,y0+bh,c[0],c[1],c[2],1);R(x0,y0,x0+fw,y0+Math.max(1,Math.round(bh*0.4)),Math.min(1,c[0]+0.22),Math.min(1,c[1]+0.2),Math.min(1,c[2]+0.18),1);
  if(bw>=24)for(let q=1;q<4;q++){const tx=x0+Math.round(bw*q/4);R(tx,y0,tx+tk,y0+bh,0,0,0,0.38)}}
 if(!n)return;gl.useProgram(U.pr);gl.disable(gl.DEPTH_TEST);gl.enable(gl.BLEND);gl.blendFunc(gl.SRC_ALPHA,gl.ONE_MINUS_SRC_ALPHA);gl.uniform2f(U.res,W,H);gl.bindBuffer(gl.ARRAY_BUFFER,U.buf);gl.bufferData(gl.ARRAY_BUFFER,U.f.subarray(0,n),gl.STREAM_DRAW);
 gl.vertexAttribPointer(U.p,2,gl.FLOAT,false,24,0);gl.enableVertexAttribArray(U.p);gl.vertexAttribPointer(U.c,4,gl.FLOAT,false,24,8);gl.enableVertexAttribArray(U.c);gl.drawArrays(gl.TRIANGLES,0,n/6);
 gl.disable(gl.BLEND);gl.enable(gl.DEPTH_TEST);gl.useProgram(V3.pr)}
// Queues of the selected units: [{unit, from:[x,z], list:[{x,y,n,color,kind}]}], numbered in order.
function v3queues(){if(!V3.on)return [];const by=new Map();if(model&&model.patrol){const pts=arr(model.patrol.points).filter(p=>p[2]===V3.z);if(pts.length)by.set('patrol-draft',pts.map((p,i)=>({x:p[0],y:p[1],z:p[2],kind:'patrol',index:i+1,unit:'patrol-draft'})))}for(const t of arr(model&&model.targets)){if(t.z!==V3.z)continue;const k=t.unit||'';if(!by.has(k))by.set(k,[]);by.get(k).push(t)}
 const col=k=>/patrol/i.test(k||'')?[0.75,0.55,1,1]:/chop|mine|dig|gather|pick/i.test(k||'')?[0.95,0.7,0.25,1]:/attack|fight|kill/i.test(k||'')?[0.95,0.3,0.25,1]:/build|craft|use|interact/i.test(k||'')?[0.45,0.7,1,1]:[0.45,0.9,0.45,1];
 const out=[],RB=V3.byRefOf===V3.things?V3.byRef:null;for(const [u,L] of by){L.sort((a,b)=>(a.index||0)-(b.index||0));const me=RB?RB.get(u):V3.things.find(t=>t.ref===u);out.push({unit:u,from:me&&me.dx!=null?[me.dx,-me.dy]:null,list:L.map((t,i)=>({x:t.x,y:t.y,n:i+1,kind:t.kind,color:col(t.kind)}))})}return out}
// The queue number sits on its highlighted tile, and fades with it and the line (V3.lineA, the frame's v3lineGroups).
function v3marks(){const box=$('marks3d');const T=[],A=[];for(const q of v3queues())if(q.list.length>1){const a=V3.lineA?V3.lineA.get(q.unit)||0:1;if(a>0)for(const t of q.list){T.push(t);A.push(a)}}   /* numbers only for a real queue: a single order needs no "1" */while(box.childElementCount<T.length){const e=document.createElement('span');box.append(e)}
 [...box.children].forEach((e,i)=>{const t=T[i];const s=t&&v3project([t.x,0.05,-t.y]);if(!s){e.hidden=true;return}e.hidden=false;const label=String(t.n);if(e.textContent!==label)e.textContent=label;e.title=t.kind||'';e.style.transform='translate('+Math.round(s[0]-8)+'px,'+Math.round(s[1]-9)+'px)';const o=A[i]<1?A[i].toFixed(2):'';if(e.style.opacity!==o)e.style.opacity=o})}
// Food pots and stalls: how much food each holds, over it (FoodSupply.dm).
function v3foodTags(L){const box=$('food3d');if(!box)return;while(box.childElementCount<L.length)box.append(document.createElement('span'));
 [...box.children].forEach((e,i)=>{const t=L[i],F=t&&(t.food||t.clinic&&{kind:'clinic'}||t.tavern&&{kind:'tavern',n:t.tavern.drink}||t.qboard&&{kind:'qboard'}||t.qkeeper&&{kind:'qkeeper'});if(!F){e.hidden=true;return}const [X,,Z]=v3world(t),s=v3project([X,v3groundAt(t.x,t.y)+(F.kind==='pot'?1.0:F.kind==='qkeeper'?2.3:1.45),Z]);if(!s){e.hidden=true;return}e.hidden=false;
  const label=t.qkeeper?(t.qkeeper.m?t.qkeeper.m+' ':'')+t.qkeeper.n+' \u00b7 '+t.qkeeper.j:t.qboard?(t.qboard.m?t.qboard.m+' ':'')+'Notice board \u00b7 '+(t.qboard.n||0)+' notice'+(t.qboard.n===1?'':'s'):t.tavern?'Tavern · '+(t.tavern.drink||0)+' cup'+(t.tavern.drink===1?'':'s')+' of wine':t.clinic?'Doctor’s stall · '+((t.clinic.poultice||0)+(t.clinic.tonic||0)+(t.clinic.purge||0))+' remedies':(F.kind==='pot'?'Food pot ':'Food stall ')+F.n+'/'+F.max+(F.warn?(F.warn>1?' · poisoned':' · suspect'):'');if(e.textContent!==label)e.textContent=label;const cl=t.qkeeper?(t.qkeeper.m?'qmark':''):t.qboard?(t.qboard.m?'qmark':''):F.warn?'warn':F.n?'':'empty';if(e.className!==cl)e.className=cl;e.style.transform='translate('+Math.round(s[0])+'px,'+Math.round(s[1])+'px) translate(-50%,-100%)'})}
// An item held (UseOn.dm): the banner says what to click; its bag slot is marked.
function v3useOnBanner(){const U=model&&model.useon,b=$('useon3d'),k=U?U.hint+'|'+U.ref:'';if(!b||b.dataset.k===k)return;b.dataset.k=k;
 document.querySelectorAll('.bagheld').forEach(x=>x.classList.remove('bagheld'));if(!U){b.hidden=true;return}
 b.hidden=false;text(b,U.hint+(arr(U.targets).length?'':' (none in reach)')+' · right-click or Esc to let it go');document.querySelectorAll('[data-bag="'+U.ref+'"]').forEach(x=>x.classList.add('bagheld'))}
// Speech bubbles (Speech.dm): what a unit just said, over its head for a few seconds.
function v3sayTags(){const box=$('say3d');if(!box)return;const L=V3.things.filter(t=>t.say&&t.dx!=null&&v3visible(t));while(box.childElementCount<L.length)box.append(document.createElement('span'));
 [...box.children].forEach((e,i)=>{const t=L[i];if(!t){e.hidden=true;return}const [X,,Z]=v3world(t),s=v3project([X,(t.top3d||v3groundAt(t.x,t.y)+1.1)+0.3,Z]);if(!s){e.hidden=true;return}e.hidden=false;if(e.textContent!==t.say)e.textContent=t.say;e.style.transform='translate('+Math.round(s[0])+'px,'+Math.round(s[1])+'px) translate(-50%,-100%)'})}
// The point at height yh that the camera sees through P: a grounded beast's picture stands up as a card, so a mouth
// drawn high on it is seen over the ground behind it; its breath leaves from there, along the ground, not from the air.
function v3groundUnder(P,yh){const s=v3project(P);if(!s||!V3.inv)return null;const c=$('world3d'),nx=s[0]/c.clientWidth*2-1,ny=1-s[1]/c.clientHeight*2,m=V3.inv;
 const un=(x,y,z)=>{const X=x*m[0]+y*m[4]+z*m[8]+m[12],Y=x*m[1]+y*m[5]+z*m[9]+m[13],Z=x*m[2]+y*m[6]+z*m[10]+m[14],W=x*m[3]+y*m[7]+z*m[11]+m[15];return [X/W,Y/W,Z/W]};
 const a=un(nx,ny,-1),b=un(nx,ny,1),dy=b[1]-a[1];if(Math.abs(dy)<1e-6)return null;const k=(yh-a[1])/dy;return k<0?null:[a[0]+(b[0]-a[0])*k,yh,a[2]+(b[2]-a[2])*k]}
function v3project(P){const m=V3.vp;if(!m)return null;   /* before the first 3D frame (a click or hover over the loading cover) */const x=P[0]*m[0]+P[1]*m[4]+P[2]*m[8]+m[12],y=P[0]*m[1]+P[1]*m[5]+P[2]*m[9]+m[13],w=P[0]*m[3]+P[1]*m[7]+P[2]*m[11]+m[15];if(w<=0)return null;const c=$('world3d');return [(x/w*0.5+0.5)*c.clientWidth,(1-(y/w*0.5+0.5))*c.clientHeight]}
function v3target(mx,my){const t=v3pickThing(mx,my);const tile=t?{x:t.x,y:t.y}:v3pickTile(mx,my);return tile?tile.x+'|'+tile.y+'|'+(t?(t.ref||t.id||''):'')+(!t&&tile.up?'|0|1':''):null}   /* '|0|1': the top of a wall or a peak, as the click sends it, so the verdict is for what a click does (rts-feel) */
// Right-click menu: the map's right-click choices for what is under the mouse.
function gameFocus(){if(!overlayHost)return;try{window.webkit.messageHandlers.dmOverlay.postMessage({focus:'game'})}catch(e){}}
// World map: explored chunks as 4x4 colour cells, your units, the stockpile and the camera.
let worldMapKey='';
function renderWorldMap(m){const W=m.worldMap,box=$('worldmap');const open=!!W&&overlayHost;if(box.hidden===open){box.hidden=!open;queueRegions()}if(!W)return;
 const key=JSON.stringify([W.z,W.chunks.length,W.units,W.stockpile,W.x,W.y,W.quests,W.pick]);if(key===worldMapKey)return;worldMapKey=key;
 // Fit the view to what has been explored (plus your units and the camera), at least 64 tiles across.
 let x0=W.x-12,x1=W.x+12,y0=W.y-9,y1=W.y+9;for(const [cx,cy] of W.chunks){x0=Math.min(x0,cx*16);x1=Math.max(x1,cx*16+16);y0=Math.min(y0,cy*16);y1=Math.max(y1,cy*16+16)}for(const [x,y] of W.units){x0=Math.min(x0,x);x1=Math.max(x1,x);y0=Math.min(y0,y);y1=Math.max(y1,y)}for(const q of arr(W.quests)){x0=Math.min(x0,q.x-(q.r||0));x1=Math.max(x1,q.x+(q.r||0));y0=Math.min(y0,q.y-(q.r||0));y1=Math.max(y1,q.y+(q.r||0))}
 let span=Math.max(64,x1-x0,y1-y0)*1.15;const mx=(x0+x1)/2,my=(y0+y1)/2;x0=mx-span/2;y0=my-span/2;W.view={x0,y0,span};
 const c=$('wmCanvas'),g=c.getContext('2d'),k=c.width/span;const PX=x=>(x-x0)*k,PY=y=>c.height-(y-y0)*k;
 g.fillStyle='#07090a';g.fillRect(0,0,c.width,c.height);
 for(const [cx,cy,cells] of W.chunks)for(let n=0;n<16;n++){const col=cells[n];if(!col)continue;const i=n%4,j=Math.floor(n/4);const x=cx*16+i*4,y=cy*16+j*4;g.fillStyle=col;g.fillRect(Math.floor(PX(x)),Math.floor(PY(y+4)),Math.ceil(4*k)+1,Math.ceil(4*k)+1)}
 g.strokeStyle='rgba(242,210,122,.25)';g.lineWidth=1;for(const [cx,cy,cells] of W.chunks)if(cells.some(Boolean))g.strokeRect(PX(cx*16),PY(cy*16+16),16*k,16*k);
 g.fillStyle='#ffdf88';for(const [x,y] of W.units){g.beginPath();g.arc(PX(x+0.5),PY(y+0.5),Math.max(3,k*0.6),0,Math.PI*2);g.fill()}
 if(W.stockpile){g.strokeStyle='#f2d27a';g.lineWidth=2;g.strokeRect(PX(W.stockpile[0])-6,PY(W.stockpile[1])-6,12,12)}
 g.strokeStyle='#ffffff';g.lineWidth=1.5;g.strokeRect(PX(W.x-12),PY(W.y+9),25*k,19*k);
 drawPings(g,x=>PX(x+0.5),y=>PY(y+0.5),W.z,2.5);if(typeof questMapMarks==='function')questMapMarks(g,PX,PY,k,W);
 text($('wmHint'),W.pick?(W.pick==='thing'?'Creatures are picked in the world, where your people see them, not on the map.':'Picking for your notice: click the spot (explored land only).'):'Explored land only · '+Math.round(span)+' tiles across · click a spot to move the camera there.');
 const L=$('wmLayers');if(!L.childElementCount)[[1,'Surface'],[2,'Caves'],[3,'Sky'],[4,'Depths']].forEach(([z,l])=>{const b=document.createElement('button');b.textContent=l;b.dataset.z=z;b.addEventListener('click',()=>{send('worldmaplayer',String(z));worldMapKey=''});L.append(b)});
 L.querySelectorAll('button').forEach(b=>{b.setAttribute('aria-pressed',String(+b.dataset.z===W.z));if(+b.dataset.z===3)b.hidden=!(model&&model.sky)&&W.z!==3})}   /* the Sky: earned (Flying.dm) */
// Settings: kept in this browser (per computer).
// HUD size "Auto": the HUD was laid out for a 1440x900 window; it shrinks on smaller
// windows and grows on bigger ones (0.6x to 1.6x), measured with the zoom cleared so a
// previous scale does not feed back into the next.
// Mouse positions in the HUD's own (zoomed) pixels. With Settings → HUD size the page is zoomed; some engines
// report clientX/Y and element rects in unzoomed window pixels (this app's WebKit view, the Claude browser),
// others (standard CSS zoom) in zoomed ones. hudK() is the factor between the two: 1 where nothing is needed.
function hudK(){const z=+document.documentElement.style.zoom||1;if(z===1)return 1;const w=document.documentElement.getBoundingClientRect().width;return w?z*w/innerWidth:1}
// Mouse positions: clientX/Y and elementFromPoint are in window pixels in every engine here (this app's WebKit,
// Chromium), so the HUD's layout pixels are the window ones divided by the zoom; element rects are in layout pixels
// in WebKit (hudK() converts them where an engine differs). Measured 2026-10-22 in WebKit and Chromium.
function hudKC(){return +document.documentElement.style.zoom||1}
function mx(e){return e.clientX/hudKC()}
function my(e){return e.clientY/hudKC()}
// Auto shrinks the HUD for a small window but never blows it up past its own size (the owner, 10-27, full screen on a
// 1920x1200 screen at 1.33: "the hud on full screen looks to big no? it looks like stretch"): a bigger window shows more
// of the world instead, and the pixel-drawn frames, buttons and portraits stay at whole pixels. A larger HUD is still
// one pick away in Settings → HUD size.
function autoHudScale(){document.documentElement.style.zoom='';const s=Math.min(innerWidth/1440,innerHeight/900);return Math.round(Math.max(0.6,Math.min(1,s))*100)/100}
let hudScaleTimer=null;addEventListener('resize',()=>{clearTimeout(hudScaleTimer);hudScaleTimer=setTimeout(applySettings,150)});   // Auto re-fits; every size refreshes --sw/--sh
function applySettings(){let st={};try{st=JSON.parse(localStorage.getItem('rmSettings')||'{}')}catch(e){}const pref=(st.scale==null||st.scale==='auto')?'auto':String(st.scale);/* a chosen size never makes the HUD's room smaller than 1260x720, where every panel fits (Large and Extra large ran the
   top bar off the window and the action bar over the unit card in a 1280x720 window) (hud-craft) */
const want=+pref||1,cap=Math.max(0.6,Math.floor(Math.min(innerWidth/1260,innerHeight/720)*100)/100);const sc=pref==='auto'?autoHudScale():Math.min(want,cap);{const se=$('setScale');if(se){se.dataset.tip=pref!=='auto'&&want>cap?'HUD size\nThis size doesn\u2019t fit the window: showing the largest that does.':'';se.removeAttribute('title')}}document.documentElement.style.zoom=sc===1?'':String(sc);document.body.classList.toggle('hc-small',sc<0.76);/* WebKit's 9 px text floor makes labels relatively wider at small scales (hud-craft) */requestAnimationFrame(queueRegions);
// viewport units ignore the zoom; the stylesheet uses these instead (the window's size in zoomed pixels)
document.documentElement.style.setProperty('--sw',(innerWidth/sc)+'px');document.documentElement.style.setProperty('--sh',(innerHeight/sc)+'px');document.body.classList.toggle('cb',!!st.cb);$('setScale').value=pref;$('setCB').checked=!!st.cb;const look=st.look||(st.sprites?'flat':'hd2d');$('setLook').value=look;V3.unitModels=look==='models';$('setXP').checked=!!st.xp;window.rmXPDrops=!!st.xp;$('setHp').value=st.hp==='bars'||st.hp==='off'?st.hp:'ring';V3.hpRing=st.hp!=='bars'&&st.hp!=='off';V3.hpOff=st.hp==='off';if(V3.models===(look==='flat')){V3.models=look!=='flat';if(V3.terrain&&V3.gl)v3buildTerrain(V3.terrain)}queueRegions()}
function saveSettings(){const st={scale:$('setScale').value==='auto'?'auto':+$('setScale').value,cb:$('setCB').checked,look:$('setLook').value,xp:$('setXP').checked,hp:$('setHp').value};try{localStorage.setItem('rmSettings',JSON.stringify(st))}catch(e){}applySettings();try{if(typeof window.rmPersistNow==='function')window.rmPersistNow()}catch(e){}}
$('btnSettings').addEventListener('click',()=>{$('settings').hidden=!$('settings').hidden;queueRegions()});
$('setClose').addEventListener('click',()=>{$('settings').hidden=true;queueRegions()});
$('setScale').addEventListener('change',saveSettings);$('setCB').addEventListener('change',saveSettings);$('setLook').addEventListener('change',saveSettings);$('setXP').addEventListener('change',saveSettings);$('setHp').addEventListener('change',saveSettings);$('setDiff').addEventListener('change',e=>send('difficulty',e.target.value));$('setFog').addEventListener('change',e=>send('fogofwar',e.target.checked?'1':'0'));
setTimeout(applySettings,0);
$('btnMap').addEventListener('click',()=>send('worldmap',model&&model.worldMap?'0':'1'));
// One window at a time (hud-craft, from playtest): a page, the Log, Settings or the world map. Whichever opens closes
// the others, so they never pile up over each other or the Company list; Map and Settings light their menu button while open.
{const B=document.body,st=$('settings'),wm=$('worldmap');let was={page:false,log:false,set:false,map:false};
 const closeExcept=k=>{if(k!=='page'&&B.classList.contains('panel-open'))B.classList.remove('panel-open');
  if(k!=='set'&&!st.hidden)st.hidden=true;
  if(k!=='map'&&!wm.hidden&&model&&model.worldMap)send('worldmap','0')};
 const sync=()=>{const now={page:B.classList.contains('panel-open'),log:B.classList.contains('logopen'),set:!st.hidden,map:!wm.hidden};
  for(const k of ['page','log','set','map'])if(now[k]&&!was[k]){was=now;closeExcept(k);break}
  was={page:B.classList.contains('panel-open'),log:B.classList.contains('logopen'),set:!st.hidden,map:!wm.hidden};
  $('btnSettings').setAttribute('aria-pressed',String(was.set));$('btnMap').setAttribute('aria-pressed',String(was.map))};
 const mo=new MutationObserver(sync);mo.observe(B,{attributes:true,attributeFilter:['class']});mo.observe(st,{attributes:true,attributeFilter:['hidden']});mo.observe(wm,{attributes:true,attributeFilter:['hidden']});
 setTimeout(()=>B.classList.add('hc-anim'),2000)}
// Top-centre notices (hud-craft): camera lock, war, Paused, the fight alert, food, placing and use-on banners stack in one
// column under the top bar, below the menu's frame where they would reach it, instead of landing on each other or on the
// frames. Framed ones (the fight alert) keep 6 px for the frame drawn outside their box. Runs after each HUD update.
function hcStackNotices(){if(!overlayHost)return;const k=hudK(),W=innerWidth/hudKC();
 const shown=el=>el&&!el.hidden&&getComputedStyle(el).display!=='none',box=el=>{const r=el.getBoundingClientRect();return {l:r.left/k,r:r.right/k,b:r.bottom/k,w:r.width/k,h:r.height/k}};
 const tb=$('topbar'),nv=document.querySelector('nav');let y=shown(tb)?box(tb).b+12:12;const N=shown(nv)?box(nv):null;
 for(const id of ['lockbar','warbar','pausebanner','attack','foodalert','build3d','useon3d','hoverbar']){/* the hover line last: it comes and goes with the pointer, so it must not push the others */const el=$(id);if(!shown(el))continue;const b=box(el),fr=id==='attack'||id==='foodalert'?6:0;
  if(N&&W/2+b.w/2+fr>N.l-8)y=Math.max(y,N.b+12);const top=Math.round(y+fr)+'px';if(el.style.top!==top)el.style.top=top;
  if(id==='attack'){const x=$('attackx');if(shown(x)){if(x.style.top!==top)x.style.top=top;const l=Math.round(W/2+b.w/2+16)+'px';if(x.style.left!==l)x.style.left=l}}y+=b.h+fr*2+6}
 /* a centred card (an ask card: a craft list, the race pick; a workshop's use card) starts below the stack instead of
    covering its last notices, 16 px clear so the frames don't touch; its height is capped so it still ends above the
    action bar (hud-craft). The arrival story's side note is not one: it sits under the guide (placeRoster) */
 for(const a of [$('askcard'),$('usecard')]){if(a&&!a.classList.contains('story')){const st=a.style;if(shown(a)){const free=y+16,top0=box(a).b-box(a).h;if(st.top||top0<free){const want=Math.max(free,0)+'px';if(st.top!==want){st.top=want;st.transform='translate(-50%,0)';st.maxHeight='calc(var(--sh,100vh) - '+(free+100)+'px)'}}}if(!shown(a)||y<=(shown(tb)?box(tb).b+12:12)+1){if(st.top){st.top='';st.transform='';st.maxHeight=''}}}}}
// N faces the camera north (as the N key does); Top looks steeply down (about 70 degrees: straight down, the units'
// upright sprites are seen edge-on and vanish) until pressed again or the camera is turned.
$('camNorth').addEventListener('click',()=>{if(!V3.on)return;v3iso(false);V3.turnTo=null;V3.yaw=0;V3.pitch=Math.max(V3.pitch,0.9);toast('Camera faces north.')});
$('camTop').addEventListener('click',()=>{if(!V3.on)return;V3.top=!V3.top;if(V3.top){V3.topPitch=V3.pitch;v3iso(false);V3.pitch=1.22}else V3.pitch=V3.topPitch||0.9;$('camTop').setAttribute('aria-pressed',String(V3.top))});
$('wmClose').addEventListener('click',()=>send('worldmap','0'));
// The pointer in the canvas box's own units: the app's WebKit measures the box unzoomed (pointer / hudKC, as mx() does),
// a browser measures it at the HUD's zoom (pointer as it is); s, the box's scale over its layout size and the zoom, is
// 1/hudKC in the first and 1 in the second (quest maker Q3's play-test: map clicks landed off in the browser pane).
$('wmCanvas').addEventListener('click',e=>{const W=model&&model.worldMap;if(!W)return;const C=e.currentTarget,r=C.getBoundingClientRect(),s=r.width/(C.offsetWidth||r.width)/hudKC();const V=W.view||{x0:0,y0:0,span:W.maxx};const x=Math.round(V.x0+(e.clientX*s-r.left)/r.width*V.span),y=Math.round(V.y0+(1-(e.clientY*s-r.top)/r.height)*V.span);if(W.pick){send('quest','pickat|'+x+'|'+y+'|'+W.z);send('worldmap','0');return}send('camera',x+','+y);send('worldmap','0')});
// A great beast's parts in the right-click menu (Beasts.dm parts): laid out as they are on its body seen from above, head
// at the top, each with a bar for how whole it is; the part under the pointer is lit.
const V3PART_AT={dragon:{'left foreleg':[0,0],'head':[1,0],'right foreleg':[2,0],'left wing':[0,1],'right wing':[2,1],'left hind leg':[0,2],'right hind leg':[2,2]},
 spider:{'left foreleg':[0,0],'head':[1,0],'right foreleg':[2,0],'left second leg':[0,1],'right second leg':[2,1],'left third leg':[0,2],'right third leg':[2,2],'left hind leg':[0,3],'right hind leg':[2,3]}};
function v3partShort(n){return n==='head'?'Head':(n.startsWith('left')?'L ':'R ')+n.replace(/^(left|right) /,'').replace('foreleg','fore').replace(' leg','').replace('second','2nd').replace('third','3rd')}
function v3partGrid(G){const d=document.createElement('div');d.className='m3grid';const at=V3PART_AT[G.kind]||{};
 G.parts.forEach((p,i)=>{const b=document.createElement('button'),hp=p.hp==null?100:p.hp,pos=G.fly?[p.n.startsWith('left')?0:2,0]:at[p.n]||[i%3,Math.floor(i/3)];
  b.setAttribute('role','menuitem');b.style.gridColumn=pos[0]+1;b.style.gridRow=pos[1]+1;if(p.n===G.here)b.classList.add('here');
  b.title='Attack its '+p.n+(p.hp!=null?' ('+hp+'%)':'');b.setAttribute('aria-label',b.title);
  b.innerHTML='<span>'+esc(v3partShort(p.n))+'</span><i style="width:calc((100% - 10px)*'+(hp/100)+');background:'+(hp>60?'#6fbf4a':hp>30?'#d9a43a':'#d0503c')+'"></i>';
  b.addEventListener('click',()=>{send('attackpart',G.id+'|'+p.n);v3menuClose();gameFocus()});d.append(b)});return d}
// The workshop's Interact card ("Use / open"): its options grouped as its menus group them, a Find box when
// there are many; a choice is made by the selected unit (UseCard.dm).
// A question with answers (AskCard.dm), instead of the native "Choose" window: the question as the heading, a big
// button per answer, Cancel apart; Find when there are many; Esc cancels.
// The original's Title Case question reads as a plain one; a list of things to make asks what to make.
function askHeading(t,rest){if(t!=='What Action Will You Choose?')return t;return rest.length>6&&!rest.some(([l])=>/^(Craft|Destroy|Attack|Pick Up|Drop)$/.test(l))?'What will you make?':'What will you do?'}
function renderAskCard(m){const c=$('askcard');if(!c)return;const A=m.ask;if(!A){if(!c.hidden){c.hidden=true;c.dataset.k='';queueRegions()}return}
 const key=A.kind==='company'?companyKey(A,m):String(A.id);if(c.dataset.k===key&&!c.hidden)return;if(c.hidden&&window.rmAskDone&&rmAskDone.id===key&&performance.now()-rmAskDone.at<3000)return;   /* answered here a moment ago: a send from before the game had the answer still carries it, so the card came back (polish-start 10-26); one still asked after 3 s shows again */
 c.dataset.k=key;
 c.classList.toggle('race',A.kind==='race');c.classList.toggle('story',A.kind==='story');c.classList.toggle('group',A.kind==='group');c.classList.toggle('company',A.kind==='company');if(A.kind==='company'){renderCompanyAsk(c,A,m);return}if(A.kind==='race'||A.kind==='story'){renderOnboardAsk(c,A);return}
 const opts=arr(A.options).map((l,i)=>[String(l),i+1]),cancel=opts.find(([l])=>l==='Cancel'),rest=opts.filter(([l])=>l!=='Cancel');
 const who=arr(m.units).filter(u=>u.selected);const sub=(A.title&&A.title!=='Choose'?A.title:'')+(who.length===1?(A.title&&A.title!=='Choose'?' · ':'')+'for '+ownName(who[0].name):'');
 let h='<div class="ic-head"><span class="ic-kind">?</span><div class="ic-name"><b>'+esc(askHeading(A.message||A.title||'Choose',rest))+'</b>'+(sub?'<small>'+esc(sub)+'</small>':'')+'</div>'+(cancel?'':'<button class="ic-x" data-ask="cancel" title="Close (Esc)">×</button>')+'</div>';
 if(rest.length>10)h+='<input class="uc-q" type="search" placeholder="Find…" aria-label="Find">';
 h+='<div class="uc-body"><div class="uc-sec"><div class="uc-opts'+(rest.length<=4?' one':'')+'">'+rest.map(([l,i])=>'<button data-ask="'+i+'" title="'+esc(icSpaced(l))+'">'+esc(icSpaced(l))+'</button>').join('')+'</div></div></div>';
 if(cancel)h+='<div class="ask-foot"><button data-ask="'+cancel[1]+'" class="ask-cancel" title="Cancel (Esc)">Cancel</button></div>';
 c.innerHTML=h;c.hidden=false;queueRegions();const q=c.querySelector('.uc-q');if(q)q.focus()}
document.addEventListener('click',e=>{const b=e.target.closest('#askcard [data-ask]');if(!b)return;const c=$('askcard'),id=c.dataset.k,v=b.dataset.ask;window.rmAskDone={id:id,at:performance.now()};if(v==='cancel')send('askcancel',id.split('|')[0]);else{send('askanswer',id.split('|')[0]+'|'+v);window.rmAskAnsweredAt=performance.now();const sc=$('startcard');if(sc)sc.hidden=true}c.hidden=true;queueRegions();gameFocus()});
document.addEventListener('keydown',e=>{const c=$('askcard');if(e.key==='Escape'&&c&&!c.hidden){send('askcancel',c.dataset.k);window.rmAskDone={id:c.dataset.k,at:performance.now()};c.hidden=true;queueRegions()}});
document.addEventListener('input',e=>{const q=e.target.closest&&e.target.closest('#askcard .uc-q');if(!q)return;const t=q.value.trim().toLowerCase();$('askcard').querySelectorAll('.uc-opts button').forEach(b=>{b.hidden=!!t&&!b.textContent.toLowerCase().includes(t)})});
// The log: everything the bottom-right panel showed (messages, and the fight lines the game prints), kept here for the
// session; Village > Log > Messages shows it (hud-craft: it was the menu's Log card, merged into the village log).
const logHist=[];let logSerial=0;
function logPush(t,k){t=String(t);if(k!=='fight'&&/attack|\bhits?\b|strikes|bleed|wound|\bkill|\bdies\b|\bdied\b|slain|knocked out|fight|raid|hostile/i.test(t))k='fight';  // fight news counts as a fight line
 logHist.push({t,k,at:Date.now()});logSerial++;if(logHist.length>400)logHist.shift();hcMsgView()}
// Village > Log > Messages: newest first, each line with its time; fight lines carry the log's red stripe. Redrawn only
// when a line comes in (or a repeat counts up), and only while that view is showing.
let hcMsgKey='';
function hcMsgView(){if(typeof cbQueue==='function')cbQueue();const v=$('villageLog'),box=$('vlogList');if(!v||!box||v.hidden)return;{const c=document.querySelector('#vlogFilters [data-k=msg] b');if(c)text(c,logHist.length)}
 if(vlogFilter==='fight'){if(model)villageLogView(model);return}  // Fights holds the fight lines too (its key only changes when one comes in)
 if(vlogFilter!=='msg'){const c=document.querySelector('#vlogFilters [data-k=fight] b');if(c&&model)text(c,arr(model.villageLog).filter(vlogIsFight).length+logHist.filter(e=>e.k==='fight').length);return}text($('vlogHint'),'Every message and fight line of this session, newest first.');const last=logHist[logHist.length-1];const key=logSerial+'|'+(last?last.t:'');if(key===hcMsgKey&&box.dataset.view==='msg')return;hcMsgKey=key;box.dataset.view='msg';vlogKey='';
 const hm=t=>{const d=new Date(t);return String(d.getHours()).padStart(2,'0')+':'+String(d.getMinutes()).padStart(2,'0')};
 box.innerHTML=logHist.length?logHist.slice().reverse().map(e=>'<button class="ventry k-'+(e.k==='fight'?'fight':e.k==='note'?'note':'msg')+'" disabled><span>'+esc(tidyLine(e.t))+'</span><small>'+hm(e.at)+(e.k==='fight'?' · fight':'')+'</small></button>').join(''):'<p class="hint">No messages yet. What your people say and every fight line land here, with the time.</p>'}
// Anything that opened the old Log (the old layout's footer button) opens Village > Log > Messages.
function hcOpenMessages(){vlogFilter='msg';vlogKey='';hcMsgKey='';send('villageview','log');if(overlayHost){document.body.classList.add('panel-open');queueRegions()}}
document.addEventListener('click',e=>{if(e.target.closest('[data-hudlog]'))hcOpenMessages()});
