/* Runtime keyframes retargeted onto the approved Elf, preserving fixed bone lengths. */
const V={add:(a,b)=>a.map((x,i)=>x+b[i]),sub:(a,b)=>a.map((x,i)=>x-b[i]),len:a=>Math.hypot(...a),mix:(a,b,u)=>a.map((x,i)=>x+(b[i]-x)*u),clamp:(x,a,b)=>Math.max(a,Math.min(b,x)),smooth:x=>(x=V.clamp(x,0,1),x*x*(3-2*x))};
function turn(p,pivot,angle,offset=[0,0]){const [x,y]=V.sub(p,pivot),c=Math.cos(angle),s=Math.sin(angle);return [pivot[0]+offset[0]+x*c-y*s,pivot[1]+offset[1]+x*s+y*c];}
function ik(root,target,a,b,bend){const v=V.sub(target,root),dist=V.clamp(V.len(v),Math.abs(a-b)+.001,a+b-.001),th=Math.atan2(v[1],v[0]),al=Math.acos(V.clamp((a*a+dist*dist-b*b)/(2*a*dist),-1,1));return [V.add(root,[Math.cos(th+bend*al)*a,Math.sin(th+bend*al)*a]),V.add(root,[Math.cos(th)*dist,Math.sin(th)*dist])];}
class ElfAnimator{
 constructor(data,images){this.data=data;this.images=images;}
 scalar(clip,time,name,rest=0){const keys=clip.keys||[[0]];let i=0;while(i<keys.length-1&&keys[i+1][0]<=time)i++;const a=keys[i],b=keys[Math.min(i+1,keys.length-1)],u=V.smooth((time-a[0])/(b[0]-a[0]||1));return (a[1]?.[name]??rest)+((b[1]?.[name]??rest)-(a[1]?.[name]??rest))*u;}
 sample(id,time,d,equipment){const clip=this.data.clips[id];time=V.clamp(time,0,clip.duration);equipment=equipment||clip.equipment;
  // Side archery uses one approved pose; East is an exact reflection of West.
  if(clip.mode==='bow'&&d===2){const p=this.sample(id,time,3,equipment),mirror=v=>[64-v[0],v[1]];p.d=2;p.mirroredFrom=3;
   for(const a of Object.values(p.arms))for(const k of ['shoulder','elbow','hand'])a[k]=mirror(a[k]);
   for(const a of Object.values(p.legs))for(const k of ['hip','knee','ankle','target'])a[k]=mirror(a[k]);
   for(const q of Object.values(p.parts)){q.root=mirror(q.root);q.tip=mirror(q.tip);}
   p.waist=mirror(p.waist);p.neck=mirror(p.neck);return p;}
  if(clip.sequence){let t=time;for(let i=0;i<clip.sequence.length;i++){const cid=clip.sequence[i],c=this.data.clips[cid];if(t<=c.duration||i===clip.sequence.length-1){const p=this.sample(cid,Math.min(t,c.duration),d,equipment);if(i&&c.physics){const prev=this.data.clips[clip.sequence[i-1]],base=this.sample(prev.id,prev.duration,d,equipment);p.parts=base.parts;p.arms=base.arms;p.legs=base.legs;p.waist=base.waist;p.neck=base.neck;}p.requestedClip=id;return p;}t-=c.duration;}}
  const bodyDirection=clip.mode==='bow'&&d>=2?(d===2?1:0):d,view=this.data.views[bodyDirection],def=clip.definition||{},val=(k,r=0)=>this.scalar(clip,time,k,r),has=k=>(clip.keys||[]).some(a=>a[1]&&k in a[1]),side=d===3?-1:1,front=d===0?1:-1,near=d===3?'left':'right';
  const leadSide=view.leadLeg||(d<2?'right':Object.entries(view.legs).sort((a,b)=>(b[1][0][0]-a[1][0][0])*side)[0][0]);
  const lengths=Object.values(view.legs).map(([h,k,a])=>V.len(V.sub(k,h))+V.len(V.sub(a,k))),L=Math.max(...lengths),u=time/clip.duration;
  let lean=val('lean')+val('shake')*(Math.sin(time*47)+.5*Math.sin(time*31)),crouch=V.clamp(val('crouch'),0,.4)*L,forward=(val('lunge')+val('rootForward'))*L,hop=val('hop')*L,fall=0,squash=1,spin=0,hidden=[];
  if(clip.physics){const k=clip.physics,w=V.smooth(u*1.7);if(['flinch','armcut','legcut'].includes(k)){lean=-.18*Math.sin(Math.PI*u)*Math.exp(-u);forward=-2*Math.sin(Math.PI*u);}else if(['melt','heap'].includes(k)){squash=1-(k==='melt'?.82:.6)*V.smooth(u);crouch=2*V.smooth(u);}else{fall=w*Math.PI/2;if(k==='spin')spin=Math.sin(Math.PI*u)*.8;if(['throw','flying','hammer'].includes(k)){hop=Math.sin(Math.PI*u)*(k==='throw'?14:8);forward=-Math.sin(Math.PI*u/2)*9;}}if(['armoff','armcut'].includes(k))hidden.push('rightUpperArm','rightForearm','rightHand');if(['legoff','legcut'].includes(k))hidden.push('rightThigh','rightShin','rightFoot');}
  if(id==='getup')fall=(1-V.smooth(u))*Math.PI/2;
  const walking=clip.mode==='walk',drawn=clip.mode==='walk'||clip.mode==='idle'||clip.mode==='fallback';
  let frame=walking?[1,0,2,0][Math.floor(time/.2)%4]:0;
  if(clip.mode==='fallback'){const phase=time/.9;lean=phase<.4?-.06:phase<.65?.14:0;forward=phase<.4?-.6:phase<.65?2:0;}
  const root=[d<2?0:side*forward,(d<2?front*forward*.35:0)-hop],angle=V.clamp(lean,-.65,.65)*(d<2?(d===0?1:-1):side)+spin;
  // Match skLegs: feet move by step/back in world space; do not add lunge twice.
  // The front leg is selected by hip position toward the target, not camera depth.
  const footTargets={};let counter=d<2?0:-Math.sin(angle)*(49-view.neck[1]+14)*.3;
  let lo=-Infinity,hi=Infinity;
  for(const [name,[h,k,a]] of Object.entries(view.legs)){
   const lead=name===leadSide,step=V.clamp(val(lead?'step':'back'),-1.4,1.4)*L*(lead?1:-1),target=V.add(a,[0,-hop]);
   if(d<2)target[1]+=front*step*.3;else target[0]+=side*step;
   const plant=clip.events?.hit?.[0]??clip.duration*.35;
   if(lead)target[1]-=Math.sin(Math.PI*V.clamp(time/plant,0,1))*Math.min(1.5,Math.abs(step)*.35);
   if(clip.physics){target[0]+=root[0];target[1]+=root[1]+hop;}
   footTargets[name]=target;const reach=(V.len(V.sub(k,h))+V.len(V.sub(a,k)))*.96;
   lo=Math.max(lo,target[0]-root[0]-h[0]-reach*.95);hi=Math.min(hi,target[0]-root[0]-h[0]+reach*.95);
  }
  if(lo<=hi)counter=V.clamp(counter,lo,hi);
  for(const [name,[h,k,a]] of Object.entries(view.legs)){
   const reach=(V.len(V.sub(k,h))+V.len(V.sub(a,k)))*.98,dx=footTargets[name][0]-h[0]-root[0]-counter;
   const need=footTargets[name][1]-Math.sqrt(Math.max(.01,reach*reach-dx*dx))-h[1]-root[1];
   if(!drawn)crouch=Math.max(crouch,need);
  }
  const pelvisOffset=V.add(root,[counter,crouch+(walking&&frame?-1:0)]),waist=V.add(view.waist,pelvisOffset),tp=p=>turn(p,view.waist,angle,pelvisOffset),neck=tp(view.neck);
  const result={bodyDirection,parts:{},arms:{},legs:{},root,waist,neck,angle,fall,squash,hidden,clip:id,requestedClip:id,time,d,equipment,sourceFrame:frame,drawnBody:drawn,weaponAngle:0};
  const rigid=(name,srcRoot,srcTip,toRoot,toTip)=>{const ps=view.partSource?.[name];result.parts[name]={srcRoot:ps?ps[0]:srcRoot,srcTip:ps?ps[1]:srcTip,root:toRoot,tip:toTip,foreshortened:ps?.[2]==='fit'};};
  rigid('pelvis',view.waist,V.add(view.waist,[0,1]),waist,V.add(waist,[0,1]));
  rigid('torso',view.waist,view.neck,waist,neck);
  rigid('head',view.neck,V.add(view.neck,[0,-10]),neck,turn(V.add(view.neck,[0,-10]),view.neck,angle*.3,V.sub(neck,view.neck)));
  for(const [name,joints] of Object.entries(view.legs)){const [h,k,a]=joints,A=V.len(V.sub(k,h)),B=V.len(V.sub(a,k)),hip=V.add(h,pelvisOffset),target=footTargets[name];
   const bend=d===2?-1:d===3?1:hip[0]<32?1:-1,[knee,ankle]=ik(hip,target,A,B,bend);
   rigid(name+'Thigh',h,k,hip,knee);rigid(name+'Shin',k,a,knee,ankle);rigid(name+'Foot',a,V.add(a,[0,1]),ankle,V.add(ankle,[0,1]));result.legs[name]={hip,knee,ankle,target,upperLength:A,lowerLength:B};
  }
  if(has('W')){const w=val('W',Math.PI/2),vx=d<2?(d===0?1:-1)*Math.cos(w)*.7:side*Math.cos(w),vy=-Math.sin(w);result.weaponAngle=Math.atan2(vx,-vy);}else result.weaponAngle=({'0':-10,'1':10,'2':14,'3':-14}[d])*Math.PI/180+angle;
  if(clip.mode==='fallback')result.weaponAngle=(time/.9<.4?-45:time/.9<.65?105:14)*Math.PI/180*(d===3||d===1?-1:1);
  const twoHanded=!!def.two&&!equipment.shield&&equipment.weapon!=='none';
  const supportOffset=[-Math.sin(result.weaponAngle)*4,Math.cos(result.weaponAngle)*4];
  for(const [name,sd] of [['right','R'],['left','L']]){const [s,e,h]=view.arms[name],A=V.len(V.sub(e,s)),B=V.len(V.sub(h,e)),shoulder=tp(s),guard=this.data.grips[d][name],armed=equipment.weapon!=='none'||equipment.shield,base=armed?guard:h;
   let target=tp(base),bend=d===2?1:d===3?-1:s[0]<32?1:-1;
   if(has(sd+'u')||has(sd+'l')){const rest=ik(s,base,A,B,bend),a0=Math.atan2(-(rest[0][1]-s[1]),(rest[0][0]-s[0])*side),a1=Math.atan2(-(rest[1][1]-rest[0][1]),(rest[1][0]-rest[0][0])*side),ua=val(sd+'u',a0),la=val(sd+'l',a1);
    const project=(a,len)=>d<2?[(32-s[0])*Math.max(0,Math.cos(a))*.32+Math.sign(s[0]-32)*Math.min(0,Math.cos(a))*len*.18,-Math.sin(a)*len+front*Math.cos(a)*len*.2]:[side*Math.cos(a)*len,-Math.sin(a)*len];
    const q=V.add(project(ua,A),project(la,B)),restQ=V.add(project(a0,A),project(a1,B));
    // Projected front/back rest angles do not reconstruct the actual drawn guard.
    // Fade that projection error out whenever the arm track returns to rest.
    const activity={keys:clip.keys.map(k=>[k[0],{weight:k[1]&&(sd+'u' in k[1]||sd+'l' in k[1])?1:0}])},weight=this.scalar(activity,time,'weight');
    target=V.add(V.add(shoulder,q),V.sub(tp(base),V.add(shoulder,restQ)).map(x=>x*(1-weight)));
   }
   if(has(sd+'hx')||has(sd+'fx')){const fx=has(sd+'fx')?val(sd+'fx'):null,scale=L/9,own=Math.sign(s[0]-32)||1;
    target=V.add(neck,[fx==null?own*val(sd+'hx')*scale:d<2?own*1.5:side*fx*scale,-val(sd+(fx==null?'hy':'fy'))*scale+(fx!=null&&d<2?front*fx*.28:0)]);
   }
   if(name==='left'&&equipment.shield&&!def.shield&&!def.bare)target=tp(guard);
   if(walking&&!armed){const swing=Math.sin(time/.8*Math.PI*2+(name==='left'?Math.PI:0))*2;target=V.add(tp(h),[d<2?0:side*swing,d<2?swing*.5:0]);}
   if(clip.mode==='fallback'&&name==='right'){const p=time/.9;target=tp(p<.4?V.add(s,[d===3?4:-4,-4]):p<.65?V.add(s,[d<2?4:side*12,8]):guard);}
   if(clip.id.startsWith('throw')&&d<2&&name==='right'){
    // Frontal throws stay outside the anatomical right shoulder, not across the chest.
    const out=d===0?-1:1,poses=[[0,guard],[.26,V.add(s,[out*5,-5])],[.38,V.add(s,[out*3,1])],[.52,V.add(s,[out,7])],[.75,guard]];
    let k=0;while(k<poses.length-1&&poses[k+1][0]<=time)k++;const a=poses[k],b=poses[Math.min(k+1,poses.length-1)];target=tp(V.mix(a[1],b[1],V.smooth((time-a[0])/(b[0]-a[0]||1))));
   }
   if(twoHanded&&name==='right'){
    const [ls,le,lh]=view.arms.left,leftCenter=V.sub(tp(ls),supportOffset),leftReach=V.len(V.sub(le,ls))+V.len(V.sub(lh,le))-.02;
    const clampTo=(p,c,r)=>{const v=V.sub(p,c),n=V.len(v);return n>r?V.add(c,v.map(x=>x*r/n)):p;};
    for(let i=0;i<24;i++){target=clampTo(target,leftCenter,leftReach);target=clampTo(target,shoulder,A+B-.02);}
   }
   if(twoHanded&&name==='left'&&result.arms.right)target=V.add(result.arms.right.hand,supportOffset);
   const projection=d<2&&clip.id.startsWith('throw')&&name==='right'?1-.48*V.smooth((time-.26)/.12)*(1-V.smooth((time-.52)/.23)):1,[elbow,hand]=ik(shoulder,target,A*projection,B*projection,bend);rigid(name+'UpperArm',s,e,shoulder,elbow);rigid(name+'Forearm',e,h,elbow,hand);const wristRoll=Math.atan2(hand[1]-elbow[1],hand[0]-elbow[0])-Math.atan2(h[1]-e[1],h[0]-e[0]);rigid(name+'Hand',h,V.add(h,[0,1]),hand,turn(V.add(h,[0,1]),h,wristRoll,V.sub(hand,h)));result.arms[name]={shoulder,elbow,hand,upperLength:A,lowerLength:B,projectedUpperLength:A*projection,projectedLowerLength:B*projection};if(projection!==1){result.parts[name+'UpperArm'].foreshortened=true;result.parts[name+'Forearm'].foreshortened=true;}
  }
  if(d===0&&clip.id.startsWith('throw')){
   const a=result.arms.right,w=V.smooth(time/.26)*(1-V.smooth((time-.52)/.23));
   // An upright forearm follows the spear instead of rolling across the chest.
   const hand=V.mix(a.hand,[a.shoulder[0]-3,a.shoulder[1]-4],w),elbow=V.mix(a.elbow,V.add(hand,[0,6]),w);
   this.projectArm(result,'right',elbow,hand);
  }
  if(clip.mode==='bow'){this.bowPose(result,clip,time,view,tp,rigid);if(d>=2){const hn=this.data.views[d].neck;result.parts.head.srcRoot=hn;result.parts.head.srcTip=V.add(hn,[0,-10]);result.parts.head.sourceDirection=d;}}
  if(d===1&&clip.id.startsWith('throw')){
   const a=result.arms.right,w=V.smooth(time/.18)*(1-V.smooth((time-.28)/.16)),
    elbow=[a.shoulder[0]+6,a.shoulder[1]],hand=[elbow[0],elbow[1]-7];
   this.projectArm(result,'right',V.mix(a.elbow,elbow,w),V.mix(a.hand,hand,w));
  }
  if(d===1&&clip.id.startsWith('throw')){
   // Keep the fist seated on the shaft during windup; turn the wrist only on release.
   const hand=result.arms.right.hand,q=result.parts.rightHand,release=clip.events.release,
    flick=V.smooth((time-release)/.09)*(1-V.smooth((time-.55)/.2)),roll=-Math.PI*.32*flick;
   q.root=hand;q.tip=V.add(hand,[-Math.sin(roll),Math.cos(roll)]);
  }
  result.supportGrip=twoHanded?V.add(result.arms.right.hand,supportOffset):null;
  // Spear projects vertically in front/back views and horizontally in side views.
  if(clip.id.startsWith('throw')&&equipment.weapon==='spear')result.weaponAngle=(d===0?Math.PI:d===1?0:d===2?Math.PI/2:-Math.PI/2);
  result.released=def.ranged&&!def.spell&&!def.work&&def.release!=null&&time>=def.release;
  return result;
 }
 projectArm(p,side,elbow,hand){const a=p.arms[side];a.elbow=elbow;a.hand=hand;a.projectedUpperLength=V.len(V.sub(elbow,a.shoulder));a.projectedLowerLength=V.len(V.sub(hand,elbow));
  for(const [part,root,tip] of [['UpperArm',a.shoulder,elbow],['Forearm',elbow,hand]]){const q=p.parts[side+part];q.root=root;q.tip=tip;q.foreshortened=true;}
  const q=p.parts[side+'Hand'];q.root=hand;q.tip=V.add(hand,[0,1]);
 }
 bowPose(p,clip,time,view,tp,rigid){
  const shot=clip.id==='bow_shot',raise=shot?(time<1.15?V.smooth(time/.32):1-V.smooth((time-1.15)/.6)):0,draw=shot?V.smooth((time-.32)/.4):0;
  const targets=this.data.poseTargets?.bow?.[p.d]||[{bow:[38,32],nock:[32,32],cheek:[28,29],flung:[26,28]},
   {bow:[26,31],nock:[31,31],cheek:[36,30],flung:[38,29]},
   {bow:[54,28],nock:[45,28],cheek:[36,27],flung:[32,26]},
   {bow:[9,28],nock:[18,28],cheek:[27,27],flung:[29,28]}][p.d];
  const pulling=time<.9?V.mix(targets.nock,targets.cheek,draw):V.mix(targets.cheek,targets.flung,V.smooth((time-.9)/.14));
  const bowSide=p.d>=2?'right':'left',drawSide=p.d>=2?'left':'right';
  for(const [side,to] of [[bowSide,targets.bow],[drawSide,pulling]]){const [s,e,h]=view.arms[side],a=V.len(V.sub(e,s)),b=V.len(V.sub(h,e)),shoulder=tp(s),rest=p.d===3||side===drawSide?h:this.data.grips[p.bodyDirection][side],target=tp(V.mix(rest,to,raise)),bend=side===drawSide&&p.d>=2?(p.d===2?-1:1):p.d===2?1:p.d===3?-1:s[0]<32?1:-1,projection=p.d<2?1-raise*(side===bowSide?.48:.22):p.d===3&&side===drawSide?1-raise+raise*Math.min(1,(V.len(V.sub(target,shoulder))+.002)/(a+b)):1,[elbow,hand]=ik(shoulder,target,a*projection,b*projection,bend);
   rigid(side+'UpperArm',s,e,shoulder,elbow);rigid(side+'Forearm',e,h,elbow,hand);rigid(side+'Hand',h,V.add(h,[0,1]),hand,V.add(hand,[0,1]));p.arms[side]={shoulder,elbow,hand,upperLength:a,lowerLength:b,projectedUpperLength:a*projection,projectedLowerLength:b*projection};if(projection!==1){p.parts[side+'UpperArm'].foreshortened=true;p.parts[side+'Forearm'].foreshortened=true;}
  }
  if(p.d===3){const a=p.arms.left,reach=Math.min(a.lowerLength*.9,Math.max(2,(a.shoulder[0]-a.hand[0])*.55)),levelElbow=[a.hand[0]+reach,a.hand[1]];this.projectArm(p,'left',V.mix(a.elbow,levelElbow,raise),a.hand);}
  if(p.d===3&&shot&&time>1.15)for(const side of ['left','right']){const a=p.arms[side],[s,e,h]=view.arms[side],recovery=V.smooth((time-1.15)/.6),hand=tp(V.mix(side==='left'?targets.flung:targets.bow,h,recovery)),straight=V.mix(a.shoulder,hand,a.upperLength/(a.upperLength+a.lowerLength)),blend=V.smooth((time-1.15)/.1);this.projectArm(p,side,V.mix(a.elbow,straight,blend),hand);}
  p.bow={bowSide,drawSide,arrowPresentation:p.d<2?'tip':'shaft',raise,draw,nocked:shot&&time>=.32&&time<.9,released:shot&&time>=.9,phase:!shot?'ready':time<.32?'raise':time<.72?'draw':time<.9?'aim':time<1.15?'release':'recover'};
 }
 pixelLine(ctx,a,b,color){let x=Math.round(a[0]),y=Math.round(a[1]),ex=Math.round(b[0]),ey=Math.round(b[1]),dx=Math.abs(ex-x),dy=-Math.abs(ey-y),sx=x<ex?1:-1,sy=y<ey?1:-1,e=dx+dy;ctx.fillStyle=color;for(let n=0;n<200;n++){ctx.fillRect(x,y,1,1);if(x===ex&&y===ey)break;const q=2*e;if(q>=dy){e+=dy;x+=sx;}if(q<=dx){e+=dx;y+=sy;}}}
 bowArt(ctx,p){
  const v=this.data.items.bow.views[2],im=this.images[v.image],g=p.arms[p.bow.bowSide].hand,flip=p.d===3?-1:1,scale=p.d<2?.65:1,grip=v.grip;
  // Separate the existing limb artwork from its baked straight string at render time.
  if(!this.bowLimbs){const c=document.createElement('canvas');c.width=im.width;c.height=im.height;const x=c.getContext('2d'),w=im.width,h=im.height;
   x.save();x.beginPath();x.moveTo(0,0);x.lineTo(w,0);x.lineTo(w,h);x.lineTo(0,h);x.lineTo(0,h-3);x.lineTo(w*.28+2,h-3);x.lineTo(w*.06+2,3);x.lineTo(0,3);x.closePath();x.clip();x.drawImage(im,0,0);x.restore();this.bowLimbs=c;}
  const at=pt=>[g[0]+flip*scale*(pt[0]-grip[0]),g[1]+pt[1]-grip[1]],upper=at([1,2]),lower=at([im.width*.28,im.height-2]);
  const rest=V.mix(upper,lower,.5),nock=p.bow.nocked?p.arms[p.bow.drawSide].hand:rest;
  this.pixelLine(ctx,upper,nock,'#b9a787');this.pixelLine(ctx,nock,lower,'#b9a787');
  ctx.save();ctx.translate(...g);ctx.scale(flip*scale,1);ctx.drawImage(this.bowLimbs,-grip[0],-grip[1]);ctx.restore();
  if(p.bow.nocked){if(p.d<2)this.arrowTip(ctx,g,[0,p.d===0?1:-1]);else this.arrow(ctx,nock,[flip,0],24);}
 }
 arrowTip(ctx,origin,axis){const im=this.images[this.data.arrow];ctx.save();ctx.translate(...origin);ctx.rotate(Math.atan2(axis[1],axis[0]));ctx.drawImage(im,im.width-6,0,6,im.height,0,-1,4,3);ctx.restore();}
 arrow(ctx,origin,axis,length=24){const im=this.images[this.data.arrow];ctx.save();ctx.translate(...origin);ctx.rotate(Math.atan2(axis[1],axis[0]));ctx.drawImage(im,0,-2,length,4);ctx.restore();}
 projectile(ctx,id,time,d,p){const clip=this.data.clips[id],bow=!!p.bow,release=clip.events?.release;if(typeof release!=='number'||time<release||(!bow&&!p.released))return;
  const elapsed=time-release,flight=.38;if(elapsed>=flight)return;const start=this.sample(id,release-1e-6,d,p.equipment),origin=bow?start.arms[start.bow.bowSide].hand:start.arms.right.hand;
  const direction=d===0?[0,1]:d===1?[0,-1]:d===2?[1,0]:[-1,0],distance=elapsed*70,position=V.add(origin,direction.map(x=>x*distance));if(d>=2)position[1]+=elapsed*elapsed*8;
  ctx.save();ctx.globalAlpha=1-V.smooth((elapsed-.24)/.14);
  if(bow){if(d<2)this.arrowTip(ctx,position,direction);else this.arrow(ctx,position,direction,24);}
  else{const base=p.equipment.weapon==='spear'?(d===0?Math.PI:d===1?0:d===2?Math.PI/2:-Math.PI/2):Math.atan2(direction[0],-direction[1]),spin=p.equipment.weapon==='hand_axe'?elapsed*12:p.equipment.weapon==='dagger'?elapsed*7:0;if(d<2){ctx.translate(...position);if(d===1&&p.equipment.weapon==='spear')this.gear(ctx,p.equipment.weapon,d,[0,0],base+spin,[.5,.72]);else{ctx.scale(.7,.55);this.gear(ctx,p.equipment.weapon,d,[0,0],base+spin);}}else this.gear(ctx,p.equipment.weapon,d,position,base+spin*(d===3?-1:1));}
  ctx.restore();
 }
 part(ctx,name,p){if(p.hidden.includes(name))return;const q=p.parts[name],image=this.images[this.data.views[q.sourceDirection??p.bodyDirection??p.d].parts[name]];if(!q||!image)return;const angle=Math.atan2(q.tip[1]-q.root[1],q.tip[0]-q.root[0])-Math.atan2(q.srcTip[1]-q.srcRoot[1],q.srcTip[0]-q.srcRoot[0]);ctx.save();ctx.translate(...q.root);ctx.rotate(angle);if(q.foreshortened){const axis=Math.atan2(q.srcTip[1]-q.srcRoot[1],q.srcTip[0]-q.srcRoot[0]),ratio=V.len(V.sub(q.tip,q.root))/V.len(V.sub(q.srcTip,q.srcRoot));ctx.rotate(axis);ctx.scale(ratio,1);ctx.rotate(-axis);}ctx.drawImage(image,-q.srcRoot[0],-q.srcRoot[1]);ctx.restore();}
 gear(ctx,id,d,hand,angle,projection=[1,1]){const item=this.data.items[id];if(!item)return;const v=item.views[d];ctx.save();ctx.translate(...hand);ctx.rotate(angle);const im=this.images[v.image];if(id==='spear'&&d===1&&projection[0]===.5){const y=v.grip[1];ctx.drawImage(im,0,0,im.width,y,-v.grip[0]*.7,-y*.72,im.width*.7,y*.72);ctx.drawImage(im,0,y,im.width,im.height-y,-v.grip[0]*.5,0,im.width*.5,(im.height-y)*1.1);}else{ctx.scale(...projection);ctx.drawImage(im,-v.grip[0],-v.grip[1]);}ctx.restore();}
 render(ctx,id,time,d,options={}){const clip=this.data.clips[id],equipment={...clip.equipment,...options.equipment},p=this.sample(id,time,d,equipment),view=this.data.views[p.bodyDirection??d];if(p.mirroredFrom===3){const canvas=document.createElement('canvas');canvas.width=canvas.height=192;this.render(canvas.getContext('2d'),id,time,3,options);ctx.clearRect(0,0,192,192);ctx.save();ctx.imageSmoothingEnabled=false;ctx.translate(192,0);ctx.scale(-1,1);ctx.drawImage(canvas,0,0);ctx.restore();return p;}ctx.clearRect(0,0,192,192);ctx.imageSmoothingEnabled=false;ctx.save();ctx.translate(64,64);
  if(p.fall){ctx.translate(32,60);if(d<2)ctx.scale(1,Math.max(.15,Math.cos(p.fall)));else ctx.rotate((d===3?-1:1)*p.fall);ctx.translate(-32,-60);}if(p.squash!==1){ctx.translate(32,60);ctx.scale(1+(1-p.squash)*.2,p.squash);ctx.translate(-32,-60);}
  const cap=(name,xy)=>{const rgba=view.jointColors?.[name];if(!rgba)return;ctx.fillStyle=`rgb(${rgba[0]},${rgba[1]},${rgba[2]})`;ctx.fillRect(Math.round(xy[0])-1,Math.round(xy[1])-1,3,3);};
  const arm=side=>{if(!p.hidden.includes(side+'UpperArm')){const a=p.arms[side];cap(side+'Elbow',a.elbow);cap(side+'Wrist',a.hand);}for(const suffix of (d===1?['Forearm','UpperArm','Hand']:['UpperArm','Forearm','Hand']))this.part(ctx,side+suffix,p);};
  const shield=()=>{if(options.showEquipment!==false&&equipment.shield&&!p.hidden.includes('leftHand'))this.gear(ctx,'shield',d,p.arms.left.hand,0);};
  const weapon=()=>{if(options.showEquipment!==false&&equipment.weapon!=='none'&&!p.bow&&!p.released&&!p.hidden.includes('rightHand')){this.gear(ctx,equipment.weapon,d,p.arms.right.hand,p.weaponAngle,d===1&&clip.id.startsWith('throw')&&equipment.weapon==='spear'?[.5,.72]:[1,1]);this.part(ctx,'rightHand',p);}};
  if(p.bow&&d===2){arm('left');arm('right');if(options.showEquipment!==false)this.bowArt(ctx,p);this.part(ctx,'rightHand',p);this.part(ctx,'leftHand',p);}
  else if(p.bow&&d===3){arm('left');}
  else if(p.bow&&d===1){arm('right');arm('left');if(options.showEquipment!==false)this.bowArt(ctx,p);}
  else if(d===1){if(equipment.weapon==='sword'){weapon();arm('right');}else{arm('right');if(!(clip.id.startsWith('throw')&&equipment.weapon==='spear'))weapon();}shield();arm('left');}else if(d===2){arm('left');shield();}else if(d===3){arm('right');weapon();}
  if(d===1&&options.showEquipment!==false)this.projectile(ctx,id,time,d,p);
  if(p.drawnBody){const row=view.walk[p.sourceFrame];ctx.save();ctx.translate(...p.root);ctx.drawImage(this.images[row['refined-torso']],0,0);ctx.drawImage(this.images[row['render-head']],0,0);ctx.restore();}
  else{for(const side of [view.nearLeg==='right'?'left':'right',view.nearLeg]){if(!p.hidden.includes(side+'Thigh')){cap(side+'Knee',p.legs[side].knee);cap(side+'Ankle',p.legs[side].ankle);}for(const suffix of ['Thigh','Shin','Foot'])this.part(ctx,side+suffix,p);}this.part(ctx,'pelvis',p);this.part(ctx,'torso',p);this.part(ctx,'head',p);}
  if(p.bow&&d>=2){if(d===3){arm('left');arm('right');}}else if(d===0){arm('left');shield();arm('right');weapon();}else if(d===2){arm('right');weapon();}else if(d===3){arm('left');shield();}
  if(d===1&&clip.id.startsWith('throw')&&equipment.weapon==='spear')weapon();
  if(p.bow&&(d===0||d===3)&&options.showEquipment!==false){this.bowArt(ctx,p);this.part(ctx,'leftHand',p);this.part(ctx,'rightHand',p);}
  if(d!==1&&options.showEquipment!==false)this.projectile(ctx,id,time,d,p);
  if(options.debug){ctx.lineWidth=.6;for(const [side,a] of Object.entries(p.arms)){ctx.strokeStyle=side==='right'?'#ffd268':'#7af1cf';ctx.beginPath();ctx.moveTo(...a.shoulder);ctx.lineTo(...a.elbow);ctx.lineTo(...a.hand);ctx.stroke();}ctx.strokeStyle='#a6bfff';for(const a of Object.values(p.legs)){ctx.beginPath();ctx.moveTo(...a.hip);ctx.lineTo(...a.knee);ctx.lineTo(...a.ankle);ctx.stroke();}ctx.beginPath();ctx.moveTo(...p.waist);ctx.lineTo(...p.neck);ctx.stroke();}
  ctx.restore();return p;
 }
 times(id){const clip=this.data.clips[id],out=new Set([0,clip.duration]);for(let t=0;t<clip.duration;t+=1/12)out.add(+t.toFixed(6));const add=(c,offset=0)=>{for(const k of c.keys||[])out.add(+(k[0]+offset).toFixed(6));for(const event of Object.values(c.events||{}))for(const t of Array.isArray(event)?event:[event])out.add(+(t+offset).toFixed(6));if(c.sequence){let o=offset;for(const id of c.sequence){add(this.data.clips[id],o);o+=this.data.clips[id].duration;}}};add(clip);return [...out].filter(t=>t<=clip.duration).sort((a,b)=>a-b);}
 atlas(id){const times=this.times(id),canvas=document.createElement('canvas');canvas.width=768;canvas.height=times.length*192;const ctx=canvas.getContext('2d'),cell=document.createElement('canvas');cell.width=cell.height=192;const c=cell.getContext('2d');const frames=[];times.forEach((t,f)=>{const row=[];for(let d=0;d<4;d++){row.push(this.render(c,id,t,d));ctx.drawImage(cell,d*192,f*192);}frames.push(row);});return {canvas,metadata:{id,cellSize:192,bodyPixels:64,origin:[64,64],directions:['South','North','East','West'],times,duration:this.data.clips[id].duration,events:this.data.clips[id].events,clip:this.data.clips[id],frames}};}
}
