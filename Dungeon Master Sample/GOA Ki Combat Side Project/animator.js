/* Approved Elf pixels articulated by our animation maker. New DBZ-inspired choreography.
 * Targets are normalized by each limb's own length. No source files are edited.
 * Four authored views; extreme side-leg poses still use inferred source surfaces.
 */
(function(global){
'use strict';
const TAU=Math.PI*2,clamp=(x,a,b)=>Math.max(a,Math.min(b,x));
const add=(a,b)=>[a[0]+b[0],a[1]+b[1]],sub=(a,b)=>[a[0]-b[0],a[1]-b[1]],mul=(a,s)=>[a[0]*s,a[1]*s];
const dist=(a,b)=>Math.hypot(a[0]-b[0],a[1]-b[1]),mix=(a,b,t)=>a+(b-a)*t;
function rotate(p,o,a){const x=p[0]-o[0],y=p[1]-o[1],c=Math.cos(a),s=Math.sin(a);return[o[0]+x*c-y*s,o[1]+x*s+y*c];}
function ik(root,target,a,b,bend){const delta=sub(target,root),d=clamp(Math.hypot(...delta),Math.abs(a-b)+.001,a+b-.001),theta=Math.atan2(delta[1],delta[0]),phi=Math.acos(clamp((a*a+d*d-b*b)/(2*a*d),-1,1));return[add(root,[Math.cos(theta+bend*phi)*a,Math.sin(theta+bend*phi)*a]),add(root,[Math.cos(theta)*d,Math.sin(theta)*d])];}
const CLIPS=[
 {id:'idle',label:'Fighting stance',duration:1.2,loop:true,events:[]},
 {id:'walk',label:'Combat step',duration:.7,loop:true,events:[]},
 {id:'dash',label:'Burst dash',duration:.34,loop:false,events:[]},
 {id:'punch',label:'Snap jab',duration:.32,loop:false,events:[{time:.11,type:'hit',damage:8,range:72}],description:'Quick lead-hand snap from a compact guard, with a short torso coil and planted rear foot.'},
 {id:'punch2',label:'Driving cross',duration:.46,loop:false,events:[{time:.16,type:'hit',damage:11,range:84}],description:'Rear-hand power strike with hip rotation, a deep forward drive and a distinct recoil.'},
 {id:'combo',label:'Meteor rush',duration:1.18,loop:false,events:[{time:.10,type:'hit',damage:6,range:76},{time:.28,type:'hit',damage:9,range:84},{time:.55,type:'hit',damage:12,range:94},{time:.86,type:'hit',damage:16,range:112}],description:'New continuous jab–cross–rising kick–airborne finisher choreography; momentum carries between strikes.'},
 {id:'kick',label:'Rising thrust kick',duration:.52,loop:false,events:[{time:.22,type:'hit',damage:14,range:100}],description:'A tight raised-knee chamber snaps into a forward thrust, with a counterlean and planted support foot.'},
 {id:'kick2',label:'Aerial sweep kick',duration:.68,loop:false,events:[{time:.30,type:'hit',damage:18,range:112}],description:'Crouch, spring upward, rotate through an airborne sweeping kick, tuck and land.'},
 {id:'charge',label:'Energy charge',duration:1,loop:true,events:[]},
 {id:'blast',label:'Palm blast',duration:.65,loop:false,events:[{time:.28,type:'projectile',damage:16}]},
 {id:'beam',label:'Two-palm beam',duration:1.4,loop:false,events:[{time:.64,type:'beam',damage:35,duration:.46}]},
 {id:'hover',label:'Hover',duration:1.1,loop:true,events:[]},
 {id:'fly',label:'Forward flight',duration:.8,loop:true,events:[]},
 {id:'hurt',label:'Hit reaction',duration:.4,loop:false,events:[]},
 {id:'guard',label:'Raised guard',duration:.85,loop:true,events:[]},
 {id:'fall',label:'Knockdown',duration:.8,loop:false,events:[]},
 {id:'recover',label:'Get up',duration:.8,loop:false,events:[]}
].map(c=>({...c,renderer:'elf-rig',adapted:true,originalMotion:true,motionVersion:'dbz-1',motionSource:['punch','punch2','kick','kick2','combo'].includes(c.id)?'original-dbz-choreography':'animation-maker',motionReference:['punch','punch2','kick','kick2','combo'].includes(c.id)?'Original DBZ-inspired choreography':'Animation maker keyframes',sourceStates:[],eventTiming:'Impact and release events follow the newly authored action keyframes.'}));
const DEFAULT={lean:0,crouch:.35,rootF:0,rootY:0,Rf:.5,Ry:.2,Lf:.5,Ly:.2,nearStep:0,farStep:0,nearLift:0,farLift:0,kick:0,kickUp:0,kickLeft:0,flight:0,head:0,handR:0,handL:0,hipTilt:0,frontFold:0,footLock:0};
const KEYS={
 // These curves are newly authored for the side project. They are not copies of
 // the original GOA two-frame attacks or the earlier Elf test's .4s motions.
 // f/y are hand targets normalized to each limb's real length. Forward-facing
 // guards fold across the chest, and support feet stay at their ground anchors.
 punch:[[0,{}],
  [.04,{Rf:.18,Ry:.12,Lf:.34,Ly:-.28,lean:-.16,crouch:1.05,rootF:-.8,hipTilt:-.06,frontFold:1,footLock:1}],
  [.08,{Rf:.32,Ry:-.1,Lf:.34,Ly:-.28,lean:-.09,crouch:.8,rootF:-.3,hipTilt:-.03,frontFold:1,footLock:1}],
  [.11,{Rf:.985,Ry:-.17,Lf:.3,Ly:-.27,lean:.27,crouch:1.25,rootF:1.7,nearStep:1.4,hipTilt:.08,frontFold:1,footLock:1}],
  [.145,{Rf:.985,Ry:-.17,Lf:.3,Ly:-.27,lean:.27,crouch:1.25,rootF:1.7,nearStep:1.4,hipTilt:.08,frontFold:1,footLock:1}],
  [.20,{Rf:.37,Ry:-.05,Lf:.32,Ly:-.25,lean:.07,crouch:.8,rootF:.5,nearStep:.6,hipTilt:.03,frontFold:1,footLock:1}],
  [.32,{}]],
 punch2:[[0,{}],
  [.07,{Lf:-.12,Ly:.22,Rf:.36,Ry:-.24,lean:-.23,crouch:1.7,rootF:-1.3,nearStep:1.2,farStep:-1.2,hipTilt:-.14,frontFold:1,footLock:1}],
  [.115,{Lf:.15,Ly:.02,Rf:.38,Ry:-.25,lean:-.06,crouch:1.45,rootF:-.1,nearStep:1.4,farStep:-1,hipTilt:-.03,frontFold:1,footLock:1}],
  [.16,{Lf:.98,Ly:-.17,Rf:.33,Ry:-.27,lean:.43,crouch:2,rootF:2.4,nearStep:2,farStep:-.4,hipTilt:.18,frontFold:1,footLock:1}],
  [.205,{Lf:.98,Ly:-.17,Rf:.33,Ry:-.27,lean:.43,crouch:2,rootF:2.4,nearStep:2,farStep:-.4,hipTilt:.18,frontFold:1,footLock:1}],
  [.29,{Lf:.3,Ly:-.05,Rf:.35,Ry:-.2,lean:.16,crouch:1.4,rootF:.8,nearStep:1.1,hipTilt:.06,frontFold:1,footLock:1}],
  [.46,{}]],
 kick:[[0,{}],
  [.08,{kick:.08,kickUp:-.68,Rf:.37,Ry:-.2,Lf:.38,Ly:-.25,lean:-.08,crouch:1.35,hipTilt:-.05,frontFold:1,footLock:1}],
  [.155,{kick:.16,kickUp:-.76,Rf:.35,Ry:-.12,Lf:.4,Ly:-.3,lean:-.23,crouch:.8,rootF:.35,hipTilt:-.1,frontFold:1,footLock:1}],
  [.22,{kick:.82,kickUp:-.55,Rf:.23,Ry:.08,Lf:.4,Ly:-.25,lean:-.48,crouch:1,rootF:.5,hipTilt:-.15,frontFold:1,footLock:1}],
  [.265,{kick:.82,kickUp:-.55,Rf:.23,Ry:.08,Lf:.4,Ly:-.25,lean:-.48,crouch:1,rootF:.5,hipTilt:-.15,frontFold:1,footLock:1}],
  [.35,{kick:.15,kickUp:-.68,Rf:.37,Ry:-.16,Lf:.38,Ly:-.25,lean:-.19,crouch:.7,hipTilt:-.07,frontFold:1,footLock:1}],
  [.43,{kick:.1,kickUp:.4,Rf:.4,Ry:.05,Lf:.4,Ly:-.1,lean:-.04,crouch:1.2,frontFold:.5,footLock:1}],
  [.52,{}]],
 kick2:[[0,{kickLeft:1}],
  [.075,{kickLeft:1,Rf:.22,Ry:.5,Lf:.22,Ly:.5,crouch:2.8,lean:.18,hipTilt:.14,frontFold:1,footLock:1}],
  [.15,{kickLeft:1,kick:.14,kickUp:-.65,rootY:-3,Rf:.28,Ry:-.18,Lf:.2,Ly:-.3,crouch:.4,lean:-.18,hipTilt:-.18,nearLift:3,farLift:2,frontFold:1}],
  [.23,{kickLeft:1,kick:.35,kickUp:-.75,rootY:-7.5,rootF:1.1,Rf:-.12,Ry:.3,Lf:.5,Ly:-.15,crouch:.1,lean:-.43,hipTilt:-.26,nearLift:4.5,nearStep:-1.3,frontFold:1}],
  [.30,{kickLeft:1,kick:.95,kickUp:-.28,rootY:-8,rootF:2,Rf:-.3,Ry:.38,Lf:.35,Ly:-.2,crouch:.1,lean:-.62,hipTilt:-.3,nearLift:4.2,nearStep:-1.7,frontFold:1}],
  [.35,{kickLeft:1,kick:.9,kickUp:.13,rootY:-7,rootF:2.1,Rf:-.1,Ry:.2,Lf:.4,Ly:-.2,crouch:.1,lean:-.42,hipTilt:.12,nearLift:3.7,nearStep:-1.6,frontFold:1}],
  [.44,{kickLeft:1,kick:.25,kickUp:-.55,rootY:-4,Rf:.35,Ry:-.2,Lf:.35,Ly:-.2,lean:.12,hipTilt:.14,nearLift:2,frontFold:1}],
  [.54,{kickLeft:1,crouch:2.4,lean:.14,Rf:.25,Ry:.1,Lf:.25,Ly:.1,frontFold:1,footLock:1}],
  [.68,{kickLeft:1}]],
 // A continuous rush: no repeated return to idle between its four contacts.
 combo:[[0,{}],
  [.045,{Rf:.18,Ry:.06,Lf:.35,Ly:-.25,lean:-.13,crouch:1.2,frontFold:1,footLock:1}],
  [.10,{Rf:.98,Ry:-.17,Lf:.34,Ly:-.27,lean:.25,crouch:1.2,rootF:1.4,nearStep:1.1,hipTilt:.08,frontFold:1,footLock:1}],
  [.16,{Rf:.3,Ry:-.25,Lf:-.1,Ly:.15,lean:-.12,crouch:1.8,rootF:.4,hipTilt:-.12,frontFold:1,footLock:1}],
  [.28,{Lf:.98,Ly:-.18,Rf:.34,Ry:-.25,lean:.42,crouch:2.1,rootF:2.3,nearStep:2,farStep:-.4,hipTilt:.18,frontFold:1,footLock:1}],
  [.34,{Lf:.35,Ly:-.2,Rf:.35,Ry:-.2,lean:.12,crouch:1.5,rootF:.8,hipTilt:.03,frontFold:1,footLock:1}],
  [.43,{kick:.14,kickUp:-.73,lean:-.21,crouch:1,rootF:.4,Rf:.35,Ry:-.15,Lf:.4,Ly:-.26,hipTilt:-.1,frontFold:1,footLock:1}],
  [.55,{kick:.84,kickUp:-.51,lean:-.45,crouch:1,rootF:.5,Rf:.25,Ry:.08,Lf:.4,Ly:-.24,hipTilt:-.14,frontFold:1,footLock:1}],
  [.64,{kick:.05,kickUp:.5,crouch:2.8,lean:.14,Rf:.22,Ry:.35,Lf:.22,Ly:.35,frontFold:1,footLock:1}],
  [.72,{kickLeft:1,kick:.15,kickUp:-.65,rootY:-3,crouch:.2,lean:-.2,hipTilt:-.15,nearLift:3,Rf:.25,Ry:-.2,Lf:.3,Ly:-.2,frontFold:1}],
  [.86,{kickLeft:1,kick:.95,kickUp:-.25,rootY:-8,rootF:2,Rf:-.28,Ry:.35,Lf:.35,Ly:-.2,crouch:.1,lean:-.6,hipTilt:-.28,nearLift:4.2,nearStep:-1.7,frontFold:1}],
  [.91,{kickLeft:1,kick:.88,kickUp:.12,rootY:-7,rootF:2,Rf:-.08,Ry:.18,Lf:.4,Ly:-.2,lean:-.4,hipTilt:.12,nearLift:3.8,nearStep:-1.5,frontFold:1}],
  [1.01,{kickLeft:1,kick:.2,kickUp:-.5,rootY:-3.5,lean:.12,hipTilt:.1,nearLift:2,Rf:.35,Ry:-.2,Lf:.35,Ly:-.2,frontFold:1}],
  [1.09,{crouch:2.3,lean:.14,Rf:.25,Ry:.12,Lf:.25,Ly:.12,frontFold:1,footLock:1}],
  [1.18,{}]],
 blast:[[0,{}],[.14,{Rf:-.1,Ry:.2,lean:-.1,Lf:.35,Ly:-.1}],[.28,{Rf:.98,Ry:-.04,Lf:.35,Ly:.05,lean:.12,nearStep:2,crouch:.8}],[.4,{Rf:.95,Ry:-.02,Lf:.4,Ly:.1,lean:.1,nearStep:2}],[.65,{}]],
 beam:[[0,{}],[.22,{Rf:-.3,Ry:.7,Lf:-.15,Ly:.75,crouch:1.1,lean:-.15,nearStep:-1,farStep:-1}],[.52,{Rf:-.3,Ry:.7,Lf:-.15,Ly:.75,crouch:1.4,lean:-.17,nearStep:-1,farStep:-1}],[.64,{Rf:.98,Ry:.06,Lf:.95,Ly:.1,crouch:1.6,lean:.21,nearStep:3.5,farStep:-1.5}],[1.07,{Rf:.97,Ry:.07,Lf:.95,Ly:.1,crouch:1.5,lean:.19,nearStep:3.5,farStep:-1.5}],[1.4,{}]],
 hurt:[[0,{}],[.07,{lean:-.23,Rf:.1,Ry:.45,Lf:.1,Ly:.45,crouch:1.2,rootF:-1.3}],[.18,{lean:-.16,Rf:.2,Ry:.3,Lf:.2,Ly:.3,crouch:1,rootF:-1}],[.4,{}]],
 dash:[[0,{}],[.06,{lean:.7,Rf:-.3,Ry:.6,Lf:.3,Ly:.1,nearStep:2.5,farStep:-2,crouch:1.5,rootY:-1}],[.24,{lean:.75,Rf:-.3,Ry:.55,Lf:.3,Ly:.1,nearStep:3,farStep:-2,crouch:1.2,rootY:-1}],[.34,{}]]
};
function keyPose(action,t){const keys=KEYS[action];if(!keys)return{...DEFAULT};let i=0;while(i<keys.length-1&&keys[i+1][0]<=t)i++;const a=keys[i],b=keys[Math.min(i+1,keys.length-1)],f=clamp((t-a[0])/(b[0]-a[0]||1),0,1),s=f*f*(3-2*f),p={};for(const k of Object.keys(DEFAULT))p[k]=mix(a[1][k]??DEFAULT[k],b[1][k]??DEFAULT[k],s);return p;}
function bone(a,b,sourceA,sourceB){return{root:a,tip:b,sourceRoot:sourceA,sourceTip:sourceB};}
class DbzAnimator {
 static clips=CLIPS;
 constructor(data,images){this.renderer='elf-rig';this.data=data;this.actor=data.actor;this.images=images;this.palette=new Map();if(!this.actor?.directions?.length)throw Error('Missing approved GOA actor rig');}
 timeline(id){
  const clip=CLIPS.find(c=>c.id===id)||CLIPS[0],duration=clip.duration;
  // Stable 20fps baking, including exact gameplay/key-pose times, not GOA bitmap cells.
  const ms=new Set([0]);for(let t=50;t<Math.round(duration*1000);t+=50)ms.add(t);
  for(const ev of clip.events)ms.add(Math.round(ev.time*1000));
  for(const [time]of KEYS[clip.id]||[])if(time<duration)ms.add(Math.round(time*1000));
  const timesMs=[...ms].sort((a,b)=>a-b),times=timesMs.map(t=>t/1000),durationsMs=timesMs.map((t,i)=>(timesMs[i+1]??Math.round(duration*1000))-t);
  return{times,durationsMs,renderer:'elf-rig',sampleRate:20};
 }
 sample(action,time,facing='E'){
  const clip=CLIPS.find(c=>c.id===action)||CLIPS[0],d=typeof facing==='number'?clamp(Math.floor(facing),0,3):Math.max(0,'SNEW'.indexOf(String(facing)[0].toUpperCase())),F='SNEW'[d],spec=this.actor.directions[d],rig=spec.fullBody;
  const raw=Number.isFinite(time)?Math.max(0,time):0,t=clip.loop?raw%clip.duration:Math.min(raw,clip.duration),phase=t/clip.duration,side=d===3?-1:1,depth=d===0?1:-1,p=keyPose(clip.id,t);
  if(clip.id==='idle'){p.crouch=.35+.25*Math.sin(phase*TAU);p.Ry+=.025*Math.sin(phase*TAU);}
  if(clip.id==='walk'){const q=Math.sin(phase*TAU);p.nearStep=q*2.7;p.farStep=-q*2.7;p.nearLift=Math.max(0,Math.cos(phase*TAU))*1.1;p.farLift=Math.max(0,-Math.cos(phase*TAU))*1.1;p.crouch=.55+.25*Math.cos(phase*TAU*2);p.lean=.06;}
  if(clip.id==='guard'){p.Rf=.35;p.Ry=-.3;p.Lf=.35;p.Ly=-.27;p.crouch=.9;p.lean=-.05;}
  if(clip.id==='charge'){p.Rf=.08;p.Ry=.68;p.Lf=.08;p.Ly=.65;p.crouch=1.1+.15*Math.sin(phase*TAU*6);p.lean=-.06;p.nearStep=1.1;p.farStep=-1.1;}
  if(clip.id==='hover'){p.rootY=-2+Math.sin(phase*TAU)*.7;p.crouch=.2;p.nearLift=3.4;p.farLift=2.6;p.nearStep=1.2;p.farStep=-1.5;p.Rf=.25;p.Ry=.45;p.Lf=.25;p.Ly=.45;p.lean=.02;}
  if(clip.id==='fly'){p.rootY=-1+Math.sin(phase*TAU)*.3;p.lean=1.02;p.flight=1;p.Rf=.82;p.Ry=-.4;p.Lf=.7;p.Ly=-.35;p.nearStep=-3.2;p.farStep=-2.5;p.nearLift=3;p.farLift=2.4;p.crouch=.3;}
  let fall=0;if(clip.id==='fall'||clip.id==='recover'){const u=clip.id==='fall'?phase:1-phase,q=clamp(u*1.5,0,1);fall=q*q*(3-2*q);p.crouch=1.2*fall;p.Rf=.1;p.Ry=.65;p.Lf=.1;p.Ly=.65;p.lean=-.1*fall;}
  const forward=f=>d<2?[0,depth*f*.32]:[side*f,0],root=add(forward(p.rootF),[0,p.rootY]),delta=add(root,[0,p.crouch]);
  const pelvis=add(rig.waist,delta),torsoAngle=(d<2?(d===0?1:-1)*.24:side)*p.lean,hipAngle=(d<2?(d===0?1:-1)*.45:side)*p.hipTilt;
  const hipPoint=xy=>add(rotate(xy,rig.waist,hipAngle),delta);
  const torsoPoint=xy=>add(rotate(xy,rig.waist,torsoAngle),delta),headAngle=torsoAngle*.35,neck=torsoPoint(rig.neck),bones={},arms={},legs={};
  bones.pelvis=bone(pelvis,hipPoint(add(rig.waist,[0,7])),rig.waist,add(rig.waist,[0,7]));
  bones.torso=bone(pelvis,torsoPoint(rig.neck),rig.waist,rig.neck);
  bones.head=bone(neck,add(neck,[-Math.sin(headAngle)*-12,-Math.cos(headAngle)*12]),rig.neck,add(rig.neck,[0,-12]));
  for(const sd of ['right','left']){
   const s=sd==='right'?'R':'L',[S,E,H]=spec.arms[sd],shoulder=torsoPoint(S),a=dist(S,E),b=dist(E,H),reach=a+b;
   let f=p[s+'f'],y=p[s+'y'],target;
   if(d<2){const toward=rig.waist[0]-S[0],spread=Math.sign(S[0]-rig.waist[0])||1;const folded=toward*(.68+Math.max(0,f)*.25),open=toward*Math.max(0,f)*.65+spread*Math.max(0,-f)*reach*.25;target=add(shoulder,[mix(open,folded,p.frontFold),y*reach+depth*Math.max(0,f)*reach*.25]);}
   else target=add(shoulder,[side*f*reach,y*reach]);
   let bend=d===2?1:d===3?-1:S[0]<32?1:-1;
   const [elbow,hand]=ik(shoulder,target,a,b,bend);
   bones[sd+'UpperArm']=bone(shoulder,elbow,S,E);bones[sd+'Forearm']=bone(elbow,hand,E,H);
   // The complete hand stays attached at its authored wrist; no stretched glove.
   const handAngle=(clip.id==='punch'||clip.id==='punch2'||(clip.id==='combo'&&t<.4)||clip.id==='blast'||clip.id==='beam')?(d<2?0:side*.15):0;
   bones[sd+'Hand']=bone(hand,add(hand,[Math.sin(handAngle),-Math.cos(handAngle)]),H,add(H,[0,-1]));
   arms[sd]={shoulder,elbow,wrist:hand,hand,upperLength:a,forearmLength:b,target};
  }
  for(const sd of ['right','left']){
   const [H,K,A]=rig.legs[sd],near=sd===rig.nearLeg,a=dist(H,K),b=dist(K,A),hip=hipPoint(H),step=p[near?'nearStep':'farStep'],lift=p[near?'nearLift':'farLift'];
   let target=add(add(A,mul(root,1-p.footLock)),add(forward(step),[0,-lift]));
   const kicking=sd===(p.kickLeft>.5?'left':'right')&&p.kick>0;
   if(kicking){const k=p.kick;if(d<2)target=add(hip,[Math.sign(H[0]-rig.waist[0])*k*(a+b)*.13,p.kickUp*(a+b)+depth*k*(a+b)*.2]);else target=add(hip,[side*k*(a+b),p.kickUp*(a+b)]);}
   // Knees bend toward the facing; front views preserve anatomical spread.
   const bend=d===2?(kicking?1:-1):d===3?(kicking?-1:1):H[0]<32?-1:1,[knee,ankle]=ik(hip,target,a,b,bend);
   bones[sd+'Thigh']=bone(hip,knee,H,K);bones[sd+'Shin']=bone(knee,ankle,K,A);
   let footAngle=kicking&&p.kick>.3?(d<2?0:-side*.5):p.flight?-side*.25:0;
   bones[sd+'Foot']=bone(ankle,add(ankle,[Math.cos(footAngle),Math.sin(footAngle)]),A,add(A,[1,0]));
   legs[sd]={hip,knee,ankle,upperLength:a,lowerLength:b,target,planted:!kicking&&p.footLock>.99};
  }
  const wholeAngle=fall*(d===3?1:-1)*Math.PI/2,center=[32,59],whole=p=>rotate(p,center,wholeAngle);
  if(fall){for(const b of Object.values(bones)){b.root=whole(b.root);b.tip=whole(b.tip);}for(const a of Object.values(arms))for(const key of ['shoulder','elbow','wrist','hand','target'])a[key]=whole(a[key]);for(const leg of Object.values(legs))for(const key of ['hip','knee','ankle','target'])leg[key]=whole(leg[key]);}
  return {action:clip.id,time:t,duration:clip.duration,facing:F,view:d,renderer:'elf-rig',motionSource:clip.motionSource,originalMotion:true,motionVersion:clip.motionVersion,motionReference:clip.motionReference,sourceStates:clip.sourceStates,adapted:true,nativePixels:64,bodyPixels:64,kickingSide:p.kick>0?(p.kickLeft>.5?'left':'right'):null,root,torsoAngle,hipAngle,headAngle,fall,wholeAngle,bodyParameters:p,bones,arms,legs,events:clip.events,complete:!clip.loop&&raw>=clip.duration};
 }
 skin(view){
  if(this.palette.has(view))return this.palette.get(view);
  const image=this.images[this.actor.directions[view].fullBody.parts.rightUpperArm];let color='#e6ad7e';
  if(image&&typeof document!=='undefined'){try{const canvas=document.createElement('canvas');canvas.width=canvas.height=64;const c=canvas.getContext('2d',{willReadFrequently:true});c.drawImage(image,0,0);const a=c.getImageData(0,0,64,64).data,skin=[];for(let i=0;i<a.length;i+=4)if(a[i+3]>128&&a[i]>a[i+1]*1.08&&a[i+1]>a[i+2]*1.08&&a[i+2]>40)skin.push([a[i],a[i+1],a[i+2]]);if(skin.length){skin.sort((a,b)=>a[0]-b[0]);color='rgb('+skin[Math.floor(skin.length*.45)].join(',')+')';}}catch(_){} }
  this.palette.set(view,color);return color;
 }
 part(ctx,name,state){const source=this.actor.directions[state.view].fullBody.parts[name],im=this.images[source],b=state.bones[name];if(!im||!b)return;const a=Math.atan2(b.tip[1]-b.root[1],b.tip[0]-b.root[0])-Math.atan2(b.sourceTip[1]-b.sourceRoot[1],b.sourceTip[0]-b.sourceRoot[0]);ctx.save();ctx.translate(...b.root);ctx.rotate(a);ctx.drawImage(im,-b.sourceRoot[0],-b.sourceRoot[1]);ctx.restore();}
 chain(ctx,sd,kind,state){const arm=kind==='arm',j=arm?state.arms[sd]:state.legs[sd],pts=arm?[j.shoulder,j.elbow,j.wrist]:[j.hip,j.knee,j.ankle];ctx.fillStyle=this.skin(state.view);for(const p of pts){const x=Math.round(p[0]),y=Math.round(p[1]);ctx.fillRect(x-1,y,3,1);ctx.fillRect(x,y-1,1,3);}for(const suffix of arm?['UpperArm','Forearm','Hand']:['Thigh','Shin','Foot'])this.part(ctx,sd+suffix,state);}
 render(ctx,action,time,facing='E',options={}){
  const state=this.sample(action,time,facing),spec=this.actor.directions[state.view],near=spec.fullBody.nearLeg,far=near==='right'?'left':'right';ctx.save();ctx.imageSmoothingEnabled=false;
  if(options.alpha!=null)ctx.globalAlpha*=options.alpha;
  // Rear-facing arms are correctly hidden by the torso/head; side far arm is behind.
  if(state.view===1){this.chain(ctx,'right','arm',state);this.chain(ctx,'left','arm',state);}else if(state.view>=2)this.chain(ctx,far,'arm',state);
  const frontKick=state.view===0&&state.kickingSide;
  for(const sd of [far,near])if(sd!==frontKick)this.chain(ctx,sd,'leg',state);this.part(ctx,'pelvis',state);this.part(ctx,'torso',state);
  // A forward kick approaches the camera in South and recedes behind the body in North.
  if(frontKick)this.chain(ctx,frontKick,'leg',state);
  if(state.view===0)this.chain(ctx,far,'arm',state);
  if(state.view!==1)this.chain(ctx,near,'arm',state);
  this.part(ctx,'head',state);
  // Punch/blast fists must remain readable when raised across the cheek.
  if(state.view!==1)for(const sd of ['right','left'])if(state.arms[sd].hand[1]<state.bones.torso.root[1]-9&&state.arms[sd].hand[0]*(state.view===3?-1:1)>state.bones.head.root[0]*(state.view===3?-1:1))this.part(ctx,sd+'Hand',state);
  if(options.debug){ctx.save();ctx.lineWidth=.6;for(const [name,b] of Object.entries(state.bones)){ctx.strokeStyle=name.startsWith('right')?'#ffcd68':name.startsWith('left')?'#ff91c4':'#79dafa';ctx.beginPath();ctx.moveTo(...b.root);ctx.lineTo(...b.tip);ctx.stroke();ctx.fillStyle=ctx.strokeStyle;ctx.fillRect(b.tip[0]-.6,b.tip[1]-.6,1.2,1.2);}ctx.restore();}
  ctx.restore();return state;
 }
}
global.DbzAnimator=DbzAnimator;
})(typeof window==='undefined'?globalThis:window);
