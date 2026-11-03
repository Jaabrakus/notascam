/* Universal body clips use anatomical bones. A skin supplies pixels and joint calibration. */
class UniversalAnimator {
 constructor(data,equipment){this.data=data;this.rig=structuredClone(data.rig);this.eq=equipment;this.gearCache=new Map();}
 scalar(clip,time,name,rest=0){const k=clip.keys||[[0]],last=k.length-1;let i=0;while(i<last&&k[i+1][0]<=time)i++;const a=k[i],b=k[Math.min(i+1,last)],v0=a[1]?.[name]??rest,v1=b[1]?.[name]??rest;if(a===b)return v0;const f=Math.max(0,Math.min(1,(time-a[0])/(b[0]-a[0]||1))),e=f*f*(3-2*f);return v0+(v1-v0)*e;}
 resolve(id,time){let clip=this.data.clips[id];if(!clip)throw Error('Unknown clip '+id);if(clip.sequence){for(const next of clip.sequence){const d=this.data.clips[next].duration;if(time<d)return this.resolve(next,time);time-=d;}return this.resolve(clip.sequence.at(-1),this.data.clips[clip.sequence.at(-1)].duration);}return {clip,time};}
 sample(id,time,view){const resolved=this.resolve(id,time),clip=resolved.clip,t=resolved.time,bones=structuredClone(this.rig.views[view]),hold=this.rig.holdProfiles?.[clip.holdProfile],side=view===3?-1:1,front=view===0?1:-1,legLength=Math.max(...['R','L'].map(sd=>['u','l'].reduce((n,end)=>{const b=bones['leg'+sd+end];return n+Math.hypot(b.tip[0]-b.root[0],b.tip[1]-b.root[1]);},0))),pixelScale=this.rig.handTargetScale??legLength/9;
  if(hold?.rigOverrides?.[view])Object.assign(bones,hold.rigOverrides[view]);
  const val=(name,rest=0)=>this.scalar(clip,t,name,rest),has=name=>(clip.keys||[]).some(k=>k[1]&&name in k[1]);
  let lean=val('lean'),crouch=val('crouch')*legLength,move=(val('lunge')+val('rootForward'))*legLength,lift=val('hop')*legLength,fall=0,squash=1,spin=0,hidden=[];
  const duration=clip.duration,u=Math.max(0,Math.min(1,t/duration)),smooth=x=>{x=Math.max(0,Math.min(1,x));return x*x*(3-2*x);};
  if(clip.physics){const kind=clip.physics;if(kind==='flinch'||kind==='armcut'||kind==='legcut'){lean=-.2*Math.sin(Math.PI*u)*Math.exp(-2*u);move=-2*Math.sin(Math.PI*u);}
   else if(kind==='melt'||kind==='heap'){squash=1-(kind==='melt'?.85:.65)*smooth(u);crouch=3*smooth(u);}
   else{fall=smooth(u*1.7)*Math.PI/2;crouch=['crumple','ko','liedown'].includes(kind)?4*smooth(u*2):0;if(kind==='spin')spin=Math.sin(Math.PI*u)*1.1;if(['flying','hammer','throw'].includes(kind)){lift=Math.sin(Math.PI*u)*(kind==='throw'?16:kind==='hammer'?10:6);move=-Math.sin(Math.PI*u/2)*(kind==='throw'?16:9);}}
   if(kind==='armoff'||kind==='armcut')hidden=['armRu','armRl'];if(kind==='legoff'||kind==='legcut')hidden=['legRu','legRl'];
  }
  if(hold&&clip.procedural)crouch+=(1-Math.cos(t/clip.duration*Math.PI*4))*.025*legLength;
  const root=[view<2?0:side*move,(view<2?front*move*.35:0)-lift],pel=[32+root[0],52+crouch+root[1]],rot=(view<2?0:side*lean)+spin;
  const rotate=(p,o,a)=>{const x=p[0]-o[0],y=p[1]-o[1];return [x*Math.cos(a)-y*Math.sin(a),x*Math.sin(a)+y*Math.cos(a)];};
  const torso=p=>{const q=rotate(p,[32,52],rot);return [pel[0]+q[0],pel[1]+q[1]];},result={};
  for(const name of ['torso','head']){const q=bones[name];result[name]={root:torso(q.root),tip:torso(q.tip),sourceRoot:q.root,sourceTip:q.tip};}
  const unit=(a,len,rest,center=0)=>{if(a==null){const q=rotate(rest,[0,0],rot);return q;}return view<2?[Math.max(0,Math.cos(a))*center*.5+Math.sign(rest[0]||1)*Math.max(0,-Math.cos(a))*len*.18,front*Math.cos(a)*len*.3-Math.sin(a)*len]:[side*Math.cos(a)*len,-Math.sin(a)*len];};
  const ik=(hip,target,a,b,bend)=>{let dx=target[0]-hip[0],dy=target[1]-hip[1],dist=Math.hypot(dx,dy)||.01;dist=Math.max(Math.abs(a-b)+.01,Math.min(a+b-.01,dist));const ang=Math.atan2(dy,dx),alpha=Math.acos(Math.max(-1,Math.min(1,(a*a+dist*dist-b*b)/(2*a*dist))));const mid=[hip[0]+Math.cos(ang+bend*alpha)*a,hip[1]+Math.sin(ang+bend*alpha)*a];return [mid,[hip[0]+Math.cos(ang)*dist,hip[1]+Math.sin(ang)*dist]];};
  for(const sd of ['R','L']){const up='arm'+sd+'u',lo='arm'+sd+'l',a=bones[up],b=bones[lo],root0=torso(a.root),lenA=Math.hypot(a.tip[0]-a.root[0],a.tip[1]-a.root[1]),lenB=Math.hypot(b.tip[0]-b.root[0],b.tip[1]-b.root[1]);let ua=has(sd+'u')?val(sd+'u',-1.3):null,la=has(sd+'l')?val(sd+'l',-1.3):null;
   if(clip.procedural){const phase=t/clip.duration*Math.PI*2+(sd==='L'?Math.PI:0);ua=-Math.PI/2+Math.sin(phase)*(clip.procedural==='run'?.65:.35);la=ua+.15;}
   let v=unit(ua,lenA,[a.tip[0]-a.root[0],a.tip[1]-a.root[1]],32-root0[0]),elbow=[root0[0]+v[0],root0[1]+v[1]];v=unit(la,lenB,[b.tip[0]-b.root[0],b.tip[1]-b.root[1]],32-elbow[0]);let hand=[elbow[0]+v[0],elbow[1]+v[1]];
   if(has(sd+'hx')||has(sd+'fx')){const n=torso(bones.head.root),own=Math.sign(a.root[0]-32)||1,fx=has(sd+'fx')?val(sd+'fx'):null,x=fx==null?own*val(sd+'hx')*pixelScale:view<2?own*1.5:side*fx*pixelScale,y=-(fx==null?val(sd+'hy'):val(sd+'fy'))*pixelScale+(fx!=null&&view<2?front*fx*.28:0);[elbow,hand]=ik(root0,[n[0]+x,n[1]+y],lenA,lenB,view===3?1:-1);}
   if(hold){const target=torso(hold.views[view][sd]);[elbow,hand]=ik(root0,target,lenA,lenB,hold.views[view]['bend'+sd]);}
   result[up]={root:root0,tip:elbow,sourceRoot:a.root,sourceTip:a.tip};result[lo]={root:elbow,tip:hand,sourceRoot:b.root,sourceTip:b.tip};
  }
  for(const sd of ['R','L']){const up='leg'+sd+'u',lo='leg'+sd+'l',a=bones[up],b=bones[lo],hip=torso(a.root),lenA=Math.hypot(a.tip[0]-a.root[0],a.tip[1]-a.root[1]),lenB=Math.hypot(b.tip[0]-b.root[0],b.tip[1]-b.root[1]),near=(view===3?sd==='L':sd==='R'),step=val(near?'step':'back')*legLength*(near?1:-1);let foot=[...b.tip];
   if(view<2)foot[1]+=front*step*.3;else foot[0]+=side*step;
   if(clip.procedural){const ph=t/clip.duration*Math.PI*2+(sd==='L'?Math.PI:0),stride=Math.sin(ph)*(clip.procedural==='run'?5:3);if(view<2)foot[1]+=front*stride*.4;else foot[0]+=side*stride;foot[1]-=Math.max(0,Math.cos(ph))*(clip.procedural==='run'?2.2:1.2);}
   foot[0]+=root[0];foot[1]+=root[1];const [knee,end]=ik(hip,foot,lenA,lenB,view===3?1:view===2?-1:sd==='R'?-1:1);result[up]={root:hip,tip:knee,sourceRoot:a.root,sourceTip:a.tip};result[lo]={root:knee,tip:end,sourceRoot:b.root,sourceTip:b.tip};
  }
  let weaponAngle=has('W')?val('W'):-.35;return {bones:result,skinKey:hold?.skin,holdProfile:hold?.id,root,lean,fall,squash,hidden,weaponAngle,clip:clip.id,time:t,view};
 }
 part(c,name,pose,view){const p=pose.bones[name],src=this.rig.parts.indexOf(name);if(!p||pose.hidden.includes(name))return;const a=Math.atan2(p.tip[1]-p.root[1],p.tip[0]-p.root[0])-Math.atan2(p.sourceTip[1]-p.sourceRoot[1],p.sourceTip[0]-p.sourceRoot[0]);c.save();c.translate(...p.root);c.rotate(a);const old=Math.hypot(p.sourceTip[0]-p.sourceRoot[0],p.sourceTip[1]-p.sourceRoot[1]),now=Math.hypot(p.tip[0]-p.root[0],p.tip[1]-p.root[1]);if(name!=='head'&&name!=='torso'&&old)c.scale(1,Math.max(.35,Math.min(1.5,now/old)));c.drawImage(this.eq.images.get(pose.skinKey||'skin'),src*64,view*64,64,64,-p.sourceRoot[0],-p.sourceRoot[1],64,64);c.restore();}
 gear(c,id,view,grip,vector,length=.9){if(!id)return;const key=id+':'+view;let g=this.gearCache.get(key);if(!g){const item=this.eq.items.get(id),material=id==='weapon.crystal staff'?'silver':id==='weapon.bow'?'wood':'iron',r=this.eq.gear(item,material,0),cell=view===1?14:6,w=r.image.width/16,im=document.createElement('canvas');im.width=w;im.height=r.image.height;const cx=im.getContext('2d');cx.drawImage(r.image,cell*w,0,w,r.image.height,0,0,w,r.image.height);const pix=cx.getImageData(0,0,w,im.height).data,m=r.meta;let far=0,tip=[m.ax,m.ay-1];for(let y=0;y<im.height;y++)for(let x=0;x<w;x++)if(pix[(y*w+x)*4+3]>128){const d=(x-m.ax)**2+(y-m.ay)**2;if(d>far){far=d;tip=[x,y];}}g={im,m,axis:Math.atan2(tip[1]-m.ay,tip[0]-m.ax)};this.gearCache.set(key,g);}
  c.save();c.translate(...grip);c.rotate(Math.atan2(vector[1],vector[0]));c.scale(length,id==='weapon.spear'?.55:.9);c.rotate(-g.axis);c.drawImage(g.im,-g.m.ax,-g.m.ay);c.restore();
 }
 render(c,id,time,view,{bones=false,weapon='weapon.spear',shield=false}={}){const pose=this.sample(id,time,view);c.clearRect(0,0,c.canvas.width,c.canvas.height);c.imageSmoothingEnabled=false;c.save();c.translate((c.canvas.width-64)/2,(c.canvas.height-64)/2);if(pose.fall){c.translate(32,61);if(view<2)c.scale(1,Math.max(.08,Math.cos(pose.fall)));else c.rotate((view===3?-1:1)*pose.fall);c.translate(-32,-61);}if(pose.squash!==1){c.translate(32,61);c.scale(1+(1-pose.squash)*.25,pose.squash);c.translate(-32,-61);}
  const bow=weapon==='weapon.bow',farWeapon=bow?(view===1||view===2):(view===1||view===3),grip=pose.bones[bow?'armLl':'armRl'].tip,angle=pose.weaponAngle;let vector=view<2?[.08,(view===0?1:-1)*Math.cos(angle)*.35-Math.sin(angle)]:[(view===3?-1:1)*Math.cos(angle),-Math.sin(angle)];
  if(weapon==='weapon.spear'&&view>=2){const authored=this.data.clips[pose.clip]?.weaponViewDirections?.[view];if(authored)vector=authored;else if(['idle','walk','run','hold','universal_flinch','anticipation_hop'].includes(pose.clip))vector=[view===2?1:-1,-.35];}
  if(pose.holdProfile){const profile=this.rig.holdProfiles[pose.holdProfile],directions=profile.weaponDirections[weapon]||profile.weaponDirections.default;vector=directions[view];}
  const drawWeapon=()=>{if(pose.hidden.includes(bow?'armLl':'armRl'))return;let v=vector,len=weapon==='weapon.spear'?(view<2?.38:.82):.9;if(weapon==='weapon.crystal staff')v=[0,-1];if(bow)v=view<2?[1,0]:[0,-1];this.gear(c,weapon,view,grip,v,len);};
  const drawShield=()=>{if(!shield||pose.hidden.includes('armLl'))return;const profile=pose.holdProfile?this.rig.holdProfiles[pose.holdProfile]:null,bias=profile?.shieldBias?.[view]||[0,0];this.eq.drawGear(c,this.eq.items.get('shield.round'),'iron',0,profile?.shieldAngles?.[view]??(([0,180,90,270][view]+135)%360),'shield',{height:56},{anchor:pose.bones.armLl.tip,x:bias[0],y:bias[1],scale:1,stretch:1,rotation:0});};
  const farSide=view===3?'R':'L',nearSide=farSide==='R'?'L':'R';
  if(farWeapon)drawWeapon();if(view===1||view===2)drawShield();
  if(view===1)for(const p of ['armRu','armRl','armLu','armLl'])this.part(c,p,pose,view);else for(const p of ['arm'+farSide+'u','arm'+farSide+'l'])this.part(c,p,pose,view);
  for(const p of ['legLu','legLl','legRu','legRl','torso','head'])this.part(c,p,pose,view);
  if(view!==1)for(const p of ['arm'+nearSide+'u','arm'+nearSide+'l'])this.part(c,p,pose,view);
  if(!farWeapon)drawWeapon();if(view===2&&(pose.holdProfile||(weapon==='weapon.spear'&&vector[1]===-1)))this.part(c,'head',pose,view);if(view===0||view===3)drawShield();
  // Restore the original hand pixels above the grip, using the forearm's same transform.
  if(weapon&&!farWeapon){c.save();c.beginPath();c.arc(...grip,2.1,0,Math.PI*2);c.clip();this.part(c,bow?'armLl':'armRl',pose,view);c.restore();}
  if(bones)for(const [name,p] of Object.entries(pose.bones)){c.strokeStyle=name.startsWith('armR')?'#f4c362':name.startsWith('armL')?'#67e3d2':'#aa9bea';c.lineWidth=.6;c.beginPath();c.moveTo(...p.root);c.lineTo(...p.tip);c.stroke();c.fillStyle=c.strokeStyle;c.beginPath();c.arc(...p.tip,1,0,Math.PI*2);c.fill();}
  c.restore();pose.weaponDirection=vector;return pose;
 }
}
