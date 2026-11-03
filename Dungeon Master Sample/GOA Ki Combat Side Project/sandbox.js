/* World-space ki-combat prototype. Planar movement, altitude and render depth are independent. */
'use strict';
(async()=>{
 const $=id=>document.getElementById(id);
 try{
  if(!window.DBZ_DATA?.actor?.directions||!window.DbzAnimator)throw Error('Elf rig or animation maker is missing. Rebuild the side project and reload.');
  const images={},unique=new Map();for(const [key,src] of Object.entries(DBZ_DATA.images)){if(!unique.has(src))unique.set(src,[]);unique.get(src).push(key);}let count=0;
  await Promise.all([...unique].map(async([src,names])=>{const im=await new Promise((resolve,reject)=>{const im=new Image(),timer=setTimeout(()=>reject(Error('Sprite load timed out')),15000);im.onload=()=>{clearTimeout(timer);resolve(im);};im.onerror=()=>{clearTimeout(timer);reject(Error('Could not load '+names[0]));};im.src=src;});for(const n of names)images[n]=im;$('loadStatus').textContent='Loading sprites · '+(++count)+' / '+unique.size;}));
  const Animator=window.DbzAnimator,animator=new Animator(DBZ_DATA,images),clips=Animator.clips,clipMap=Object.fromEntries(clips.map(c=>[c.id,c]));
  const canvas=$('world'),ctx=canvas.getContext('2d'),W=960,H=540,DEPTH=.65,SCALE=2,BOUNDS={width:2200,height:1600};
  const input=new Set(),keys=new Set(),particles=[],projectiles=[],beams=[],impacts=[];let paused=false,last=performance.now(),lastCharge=0;
  const mobile=new Set(['idle','walk','hover','fly','charge','guard']),clamp=(n,a,b)=>Math.max(a,Math.min(b,n));
  const norm=(x,y)=>{const l=Math.hypot(x,y);return l?[x/l,y/l]:[1,0];};
  const face=(v)=>Math.abs(v[0])>Math.abs(v[1])?(v[0]>0?'E':'W'):(v[1]>0?'S':'N');
  const obstacles=[
   {id:'cedar1',type:'tree',x:860,y:860,r:23},{id:'cedar2',type:'tree',x:1240,y:690,r:23},
   {id:'cedar3',type:'tree',x:1020,y:1080,r:23},{id:'cedar4',type:'tree',x:1500,y:1000,r:23},
   {id:'cedar5',type:'tree',x:720,y:1160,r:23},{id:'cedar6',type:'tree',x:1510,y:530,r:23},
   {id:'cedar7',type:'tree',x:680,y:550,r:23},{id:'cedar8',type:'tree',x:1810,y:1200,r:23},
   {id:'cedar9',type:'tree',x:380,y:1060,r:23},{id:'cedar10',type:'tree',x:1700,y:730,r:23},
   {id:'rock1',type:'rock',x:790,y:710,r:22},{id:'rock2',type:'rock',x:1360,y:890,r:29},
   {id:'rock3',type:'rock',x:1130,y:1130,r:24},{id:'rock4',type:'rock',x:1580,y:1360,r:26}
  ];
  const state={mode:'world',time:0,x:1050,y:850,z:0,facing:'E',aim:[1,0],aimPoint:null,attackAim:[1,0],flight:false,
   energy:60,hits:0,damage:0,punchVariant:0,kickVariant:0,action:'idle',actionTime:0,eventIndex:[],comboQueued:false,message:'Explore with WASD. Aim with the pointer; nearby figures are practice targets.',
   camera:{x:1050,y:850},targets:[],projectiles,beams,particles,impacts,motionEffects:true,contactHold:null,world:BOUNDS,obstacles,lab:{id:'punch',time:0,playing:true,speed:1,loop:true}};
  function clip(id){return clipMap[id]||clipMap.idle||{id:'idle',duration:1,loop:true,events:[]};}
  function reset(){input.clear();keys.clear();projectiles.length=beams.length=particles.length=impacts.length=0;Object.assign(state,{time:0,x:1050,y:850,z:0,facing:'E',aim:[1,0],aimPoint:null,attackAim:[1,0],flight:false,energy:60,hits:0,damage:0,punchVariant:0,kickVariant:0,action:'idle',actionTime:0,eventIndex:[],comboQueued:false,contactHold:null});state.camera.x=state.x;state.camera.y=state.y;
   state.targets=[{id:'east',label:'East target',x:1170,y:850,z:0},{id:'north',label:'North target',x:980,y:610,z:0},{id:'south',label:'South target',x:1300,y:1060,z:0}].map(t=>({...t,hp:100,action:'idle',time:0,revive:0,flash:0,facing:'S'}));state.enemy=state.targets[0];state.message='Explore with WASD. Aim with the pointer; nearby figures are practice targets.';updateHud();}
  function worldToScreen(x,y,z=0){return [W/2+x-state.camera.x,H*.6+(y-state.camera.y)*DEPTH-z];}
  function screenToWorld(x,y,z=0){return [state.camera.x+x-W/2,state.camera.y+(y-H*.6+z)/DEPTH];}
  function setAim(x,y){state.aimPoint=[x,y];state.aim=norm(x-state.x,y-state.y);if(mobile.has(state.action))state.facing=face(state.aim);return state.aim;}
  function setInput(name,down=true){down?input.add(name):input.delete(name);}
  function setMotionEffects(enabled){state.motionEffects=Boolean(enabled);if($('motionEffects'))$('motionEffects').checked=state.motionEffects;if(!state.motionEffects){impacts.length=0;state.contactHold=null;}render();}
  const held=name=>input.has(name)||({left:['a','arrowleft'],right:['d','arrowright'],up:['w','arrowup'],down:['s','arrowdown'],charge:['c'],guard:['shift']}[name]||[]).some(k=>keys.has(k));
  function start(id){state.action=id;state.actionTime=0;state.eventIndex=[];state.attackAim=[...state.aim];state.contactHold=null;}
  function trigger(id){
   if(id==='reset'){reset();return true;}
   if(id==='hover'){state.flight=!state.flight;if(mobile.has(state.action))start(state.flight?'hover':'idle');state.message=state.flight?'Flight: ground position stays separate from height. WASD moves over the world.':'Landing on the world plane.';return true;}
   if(!clipMap[id])return false;
   if(id==='punch'&&['punch','punch2','combo'].includes(state.action)){state.comboQueued=true;return true;}
   if(!mobile.has(state.action)&&state.actionTime<clip(state.action).duration*.85)return false;
   if(id==='punch'&&clipMap.punch2)id=(state.punchVariant++%2)?'punch2':'punch';
   if(id==='kick'&&clipMap.kick2)id=(state.kickVariant++%2)?'kick2':'kick';
   const cost={blast:8,beam:30,dash:6}[id]||0;if(state.energy<cost){state.message='Hold C to charge more ki.';return false;}
   state.energy-=cost;state.facing=face(state.aim);start(id);return true;
  }
  function move(dx,dy){
   state.x=clamp(state.x+dx,40,BOUNDS.width-40);state.y=clamp(state.y+dy,40,BOUNDS.height-40);
   if(state.z<48)for(const o of obstacles){const x=state.x-o.x,y=state.y-o.y,d=Math.hypot(x,y),r=o.r+12;if(d<r){const n=norm(x,y);state.x=o.x+n[0]*r;state.y=o.y+n[1]*r;}}
  }
  function sparks(x,y,z,color,n=12){for(let i=0;i<n;i++){const a=i/n*Math.PI*2;particles.push({x,y,z,vx:Math.cos(a)*35,vy:Math.sin(a)*35,vz:25+(i%4)*12,life:.25+(i%3)*.08,max:.42,color,size:i%3?3:4});}}
  function hit(target,damage,kind){if(target.hp<=0)return false;target.hp=Math.max(0,target.hp-damage);target.action=target.hp?'hurt':'fall';target.time=0;target.flash=.16;state.hits++;state.damage+=damage;sparks(target.x,target.y,target.z+58,kind==='energy'?'#c5ffff':'#ffe0a0',18);if(kind==='melee'&&state.motionEffects)impacts.push({x:target.x,y:target.y,z:target.z+58,aim:[...state.attackAim],life:.12,max:.12});state.message=target.label+' · '+damage+' damage';if(!target.hp){target.revive=3;state.message=target.label+' down · recovering';}return true;}
  function palm(time,paired=false){
   const p=animator.sample(state.action,time,state.facing),r=p.arms.right.hand,l=p.arms.left.hand;
   const h=paired?[(r[0]+l[0])/2,(r[1]+l[1])/2]:r,height=state.z+58;
   return {x:state.x+(h[0]-32)*SCALE,y:state.y+((h[1]-62)*SCALE+58)/DEPTH,z:height};
  }
  function segmentDistance(ax,ay,bx,by,x,y){const dx=bx-ax,dy=by-ay,l=dx*dx+dy*dy,u=l?clamp(((x-ax)*dx+(y-ay)*dy)/l,0,1):0;return Math.hypot(x-(ax+u*dx),y-(ay+u*dy));}
  function fireEvent(ev){
   const aim=state.attackAim;
   if(['hit','melee','strike'].includes(ev.type)){
    const reach=ev.range|| (state.action.startsWith('kick')?78:64);let landed=false;
    for(const target of state.targets){const dx=target.x-state.x,dy=target.y-state.y,d=Math.hypot(dx,dy),dot=(dx*aim[0]+dy*aim[1])/(d||1);if(d<=reach&&dot>.55&&Math.abs(target.z-state.z)<28)landed=hit(target,ev.damage||8,'melee')||landed;}
    if(!landed)state.message='Step within reach and aim toward the target. Height matters too.';
    // A contact hold changes only the drawn pose. World physics, inputs and hit timers keep advancing.
    else if(state.motionEffects)state.contactHold={action:state.action,time:ev.time,until:state.time+.035};
   }
   if(['projectile','blast','release'].includes(ev.type)&&state.action==='blast'){const origin=palm(ev.time);projectiles.push({...origin,spawnOrigin:{...origin},vx:aim[0]*430,vy:aim[1]*430,life:2,damage:ev.damage||16});sparks(origin.x,origin.y,origin.z,'#b7ffff',6);}
   if(ev.type==='beam'||state.action==='beam'&&ev.type==='release'){
    const origin=palm(ev.time,true),length=780,ex=origin.x+aim[0]*length,ey=origin.y+aim[1]*length;
    beams.push({...origin,spawnOrigin:{...origin},aim:[...aim],length,life:ev.duration||.46,max:ev.duration||.46});
    for(const target of state.targets)if(Math.abs(target.z+58-origin.z)<28&&segmentDistance(origin.x,origin.y,ex,ey,target.x,target.y)<23&&(target.x-origin.x)*aim[0]+(target.y-origin.y)*aim[1]>0)hit(target,ev.damage||35,'energy');
   }
  }
  function advance(dt){
   state.time+=dt;
   for(const target of state.targets){target.time+=dt;target.flash=Math.max(0,target.flash-dt);if(target.revive>0){target.revive-=dt;if(target.revive<=0){target.hp=100;target.action='recover';target.time=0;}}else if(target.action!=='idle'&&target.time>=clip(target.action).duration){target.action='idle';target.time=0;}target.facing=face(norm(state.x-target.x,state.y-target.y));}
   if(state.mode==='world'){
    const dx=(held('right')?1:0)-(held('left')?1:0),dy=(held('down')?1:0)-(held('up')?1:0),moving=dx||dy;
    if(mobile.has(state.action)){
     if(held('charge')){if(state.action!=='charge')start('charge');state.energy=Math.min(100,state.energy+29*dt);if(state.time-lastCharge>.09){lastCharge=state.time;sparks(state.x,state.y,state.z+10,'#b0f4bf',2);}}
     else if(held('guard')){if(state.action!=='guard')start('guard');}
     else if(moving){const v=norm(dx,dy);move(v[0]*(state.flight?210:140)*dt,v[1]*(state.flight?210:140)*dt);if(state.aimPoint)state.aim=norm(state.aimPoint[0]-state.x,state.aimPoint[1]-state.y);else state.aim=v;state.facing=face(state.aim);const id=state.flight?'fly':'walk';if(state.action!==id)start(id);}
     else{const id=state.flight?'hover':'idle';if(state.action!==id)start(id);}
    }
    const prev=state.actionTime;state.actionTime+=dt;const c=clip(state.action);
    if(state.action==='dash')move(state.attackAim[0]*490*dt,state.attackAim[1]*490*dt);
    for(const [i,ev] of (c.events||[]).entries())if(ev.time>=prev-1e-7&&ev.time<=state.actionTime&&!state.eventIndex.includes(i)){state.eventIndex.push(i);fireEvent(ev);}
    if(state.actionTime>=c.duration){if(state.comboQueued&&['punch','punch2','combo'].includes(state.action)){state.comboQueued=false;start('combo');}else if(c.loop||mobile.has(state.action)){state.actionTime%=c.duration;state.eventIndex=[];}else start(state.flight?'hover':'idle');}
    state.z+=( (state.flight?72:0)-state.z)*Math.min(1,dt*9);state.energy=Math.min(100,state.energy+.7*dt);
    const follow=1-Math.exp(-dt*7);state.camera.x+=(state.x-state.camera.x)*follow;state.camera.y+=(state.y-state.camera.y)*follow;
   }
   for(let i=projectiles.length-1;i>=0;i--){const p=projectiles[i],ox=p.x,oy=p.y;p.x+=p.vx*dt;p.y+=p.vy*dt;p.life-=dt;for(const target of state.targets)if(target.hp>0&&Math.abs(p.z-(target.z+58))<28&&segmentDistance(ox,oy,p.x,p.y,target.x,target.y)<23){hit(target,p.damage,'energy');p.life=0;break;}if(p.life<=0||p.x<0||p.y<0||p.x>BOUNDS.width||p.y>BOUNDS.height)projectiles.splice(i,1);}
   for(let i=beams.length-1;i>=0;i--)if((beams[i].life-=dt)<=0)beams.splice(i,1);
   for(let i=impacts.length-1;i>=0;i--)if((impacts[i].life-=dt)<=0)impacts.splice(i,1);
   for(let i=particles.length-1;i>=0;i--){const p=particles[i];p.life-=dt;p.x+=p.vx*dt;p.y+=p.vy*dt;p.z+=p.vz*dt;if(p.life<=0)particles.splice(i,1);}
   if(state.mode==='lab'&&state.lab.playing){state.lab.time+=dt*state.lab.speed;const d=clip(state.lab.id).duration;if(state.lab.time>=d){if(state.lab.loop)state.lab.time%=d;else{state.lab.time=d;state.lab.playing=false;$('labPlay').textContent='Play';}}}
  }
  function step(dt){let left=Math.max(0,Math.min(10,Number(dt)||0));while(left>0){const h=Math.min(1/60,left);advance(h);left-=h;}render();return state;}
  function polygon(points,color){ctx.fillStyle=color;ctx.beginPath();points.forEach((p,i)=>{const s=worldToScreen(...p);i?ctx.lineTo(...s):ctx.moveTo(...s);});ctx.closePath();ctx.fill();}
  function ground(){
   ctx.fillStyle='#203a2d';ctx.fillRect(0,0,W,H);
   const [x,y]=worldToScreen(0,0);ctx.fillStyle='#3b5840';ctx.fillRect(x,y,BOUNDS.width,BOUNDS.height*DEPTH);
   const tile=80,minx=Math.floor((state.camera.x-W/2)/tile)*tile,miny=Math.floor((state.camera.y-H/(2*DEPTH))/tile)*tile;
   for(let wy=miny;wy<miny+1100;wy+=tile)for(let wx=minx;wx<minx+1200;wx+=tile){if(wx<0||wy<0||wx>BOUNDS.width||wy>BOUNDS.height)continue;const [sx,sy]=worldToScreen(wx,wy),n=Math.abs(Math.floor(wx*7+wy*11));ctx.fillStyle=n%3?'#35513b':'#405c40';ctx.fillRect(Math.round(sx),Math.round(sy),tile,tile*DEPTH);ctx.fillStyle='#6c79504f';ctx.fillRect(sx+17+n%29,sy+15,9,2);ctx.fillStyle='#243f2d';ctx.fillRect(sx+8,sy+36,4,3);}
   polygon([[160,755],[900,760],[1100,790],[1770,590],[1820,645],[1110,850],[900,820],[160,815]],'#788065');
   polygon([[1040,320],[1090,320],[1100,1420],[1040,1420]],'#737b60');
   polygon([[390,350],[520,290],[640,330],[660,420],[540,480],[405,440]],'#315a59');
   polygon([[415,360],[520,315],[615,345],[632,412],[540,451],[430,420]],'#417272');
   const [cx,cy]=worldToScreen(1050,850);ctx.strokeStyle='#b6b68a44';ctx.lineWidth=1;ctx.beginPath();ctx.ellipse(cx,cy,100,65,0,0,Math.PI*2);ctx.stroke();
  }
  function shadow(x,y,r=20,z=0){const p=worldToScreen(x,y);ctx.fillStyle='#132a2290';ctx.beginPath();ctx.ellipse(p[0],p[1]+2,r*(z? .8:1),r*.3,0,0,Math.PI*2);ctx.fill();}
  function drawObstacle(o){const [x,y]=worldToScreen(o.x,o.y);if(x<-130||x>W+130||y<-40||y>H+170)return;
   if(o.type==='tree'){ctx.fillStyle='#453c2d';ctx.fillRect(x-9,y-68,18,68);ctx.fillStyle='#766549';ctx.fillRect(x-3,y-63,5,60);for(const [dy,w,h,col] of [[-126,90,46,'#294b36'],[-101,110,46,'#315c3b'],[-80,96,38,'#3e6b42']]){ctx.fillStyle=col;ctx.fillRect(x-w/2,y+dy,w,h);ctx.fillRect(x-w/2+10,y+dy-11,w-20,20);}ctx.fillStyle='#739452';ctx.fillRect(x-30,y-116,26,5);ctx.fillRect(x+8,y-86,27,5);}
   else{ctx.fillStyle='#455451';ctx.beginPath();ctx.moveTo(x-o.r,y-8);ctx.lineTo(x-o.r+8,y-30);ctx.lineTo(x+10,y-39);ctx.lineTo(x+o.r,y-23);ctx.lineTo(x+o.r-2,y+3);ctx.lineTo(x-o.r+8,y+6);ctx.fill();ctx.fillStyle='#819087';ctx.fillRect(x-9,y-30,18,5);ctx.fillStyle='#354842';ctx.fillRect(x-12,y-5,25,7);}
  }
  function drawPoseAt(a,time,alpha=1){const [x,y]=worldToScreen(a.x,a.y,a.z);ctx.save();ctx.translate(Math.round(x-32*SCALE),Math.round(y-62*SCALE));ctx.scale(SCALE,SCALE);animator.render(ctx,a.action,time,a.facing,{alpha});ctx.restore();}
  function drawActor(a,player=false){const [x,y]=worldToScreen(a.x,a.y,a.z),hold=player&&state.motionEffects&&state.contactHold?.action===a.action&&state.time<state.contactHold.until;drawPoseAt(a,hold?state.contactHold.time:player?state.actionTime:a.time);if(!player){ctx.fillStyle='#152a23';ctx.fillRect(x-23,y-130,46,5);ctx.fillStyle=a.flash?'#fff3b0':'#e2c276';ctx.fillRect(x-22,y-129,44*a.hp/100,3);ctx.font='9px system-ui';ctx.textAlign='center';ctx.fillStyle='#e4e9d0';ctx.fillText(a.label,x,y-137);}}
  function strikeEchoes(){
   if(!state.motionEffects)return[];
   const nearContact=(clip(state.action).events||[]).some(ev=>['hit','melee','strike'].includes(ev.type)&&state.actionTime>=ev.time-.065&&state.actionTime<=ev.time+.035);
   if(!nearContact)return[];
   // Melee feet stay in world space. Earlier articulated poses provide the streak; no sideways fake motion.
   return[.055,.028].filter(delay=>state.actionTime>delay).map((delay,i)=>({y:state.y,draw:()=>drawPoseAt(state,state.actionTime-delay,i?.14:.07)}));
  }
  function drawImpact(impact){
   const [x,y]=worldToScreen(impact.x,impact.y,impact.z),dir=norm(impact.aim[0],impact.aim[1]*DEPTH),side=[-dir[1],dir[0]],age=1-impact.life/impact.max,r=5+age*12;
   const point=(forward,cross)=>[Math.round(x+dir[0]*forward+side[0]*cross),Math.round(y+dir[1]*forward+side[1]*cross)];
   ctx.save();ctx.globalAlpha=Math.max(0,1-age);ctx.lineWidth=2;ctx.strokeStyle='#e9ffdc';ctx.beginPath();ctx.moveTo(...point(-r,0));ctx.lineTo(...point(0,-r*.55));ctx.lineTo(...point(r,0));ctx.lineTo(...point(0,r*.55));ctx.closePath();ctx.stroke();ctx.strokeStyle='#fff5b8';ctx.beginPath();ctx.moveTo(...point(-r-7,0));ctx.lineTo(...point(r+8,0));ctx.moveTo(...point(-4,-r-3));ctx.lineTo(...point(4,r+3));ctx.stroke();ctx.restore();
  }
  function aura(){if(!['charge','beam'].includes(state.action))return;const [x,y]=worldToScreen(state.x,state.y,state.z);ctx.save();ctx.globalAlpha=.35;ctx.strokeStyle='#b8f8b9';ctx.lineWidth=2;ctx.beginPath();ctx.moveTo(x-26,y-3);ctx.lineTo(x-34,y-48);ctx.lineTo(x-17,y-95);ctx.lineTo(x,y-126-Math.sin(state.time*22)*4);ctx.lineTo(x+28,y-75);ctx.lineTo(x+31,y-15);ctx.stroke();ctx.restore();}
  function selectedTarget(){let best=null,score=Infinity;for(const t of state.targets){const dx=t.x-state.x,dy=t.y-state.y,d=Math.hypot(dx,dy),alignment=(dx*state.aim[0]+dy*state.aim[1])/(d||1),s=d+(1-alignment)*180;if(s<score){score=s;best=t;}}return best;}
  function drawWorld(){ctx.imageSmoothingEnabled=false;ground();
   for(const o of obstacles)shadow(o.x,o.y,o.type==='tree'?40:o.r);
   for(const t of state.targets)shadow(t.x,t.y,21,t.z);shadow(state.x,state.y,22,state.z);
   const chosen=selectedTarget();if(chosen){const [x,y]=worldToScreen(chosen.x,chosen.y);ctx.strokeStyle='#d0c590';ctx.lineWidth=1;ctx.beginPath();ctx.ellipse(x,y+2,27,12,0,0,Math.PI*2);ctx.stroke();}
   const depth=[...obstacles.map(o=>({y:o.y,draw:()=>drawObstacle(o)})),...state.targets.map(t=>({y:t.y,draw:()=>drawActor(t)})),...strikeEchoes(),{y:state.y,draw:()=>{aura();drawActor(state,true);}},...(state.motionEffects?impacts.map(p=>({y:p.y+.01,draw:()=>drawImpact(p)})):[])].sort((a,b)=>a.y-b.y);
   for(const entry of depth)entry.draw();
   for(const p of projectiles){const [x,y]=worldToScreen(p.x,p.y,p.z),v=norm(p.vx,p.vy*DEPTH);ctx.strokeStyle='#6bbeb8';ctx.lineWidth=8;ctx.beginPath();ctx.moveTo(x-v[0]*18,y-v[1]*18);ctx.lineTo(x,y);ctx.stroke();ctx.fillStyle='#b5fff5';ctx.fillRect(x-6,y-6,12,12);ctx.fillStyle='#efffe7';ctx.fillRect(x-3,y-3,6,6);}
   for(const b of beams){const a=worldToScreen(b.x,b.y,b.z),z=worldToScreen(b.x+b.aim[0]*b.length,b.y+b.aim[1]*b.length,b.z);ctx.save();ctx.globalAlpha=Math.min(1,b.life/.09);for(const [width,col] of [[20,'#45bcb9'],[12,'#a4fff0'],[4,'#f7ffe9']]){ctx.strokeStyle=col;ctx.lineWidth=width;ctx.beginPath();ctx.moveTo(...a);ctx.lineTo(...z);ctx.stroke();}ctx.restore();}
   for(const p of particles){const [x,y]=worldToScreen(p.x,p.y,p.z);ctx.globalAlpha=Math.min(1,p.life/p.max);ctx.fillStyle=p.color;ctx.fillRect(x,y,p.size,p.size);}ctx.globalAlpha=1;
   const from=worldToScreen(state.x,state.y,state.z+36),to=worldToScreen(state.x+state.aim[0]*54,state.y+state.aim[1]*54,state.z+36);ctx.strokeStyle='#d3ead57f';ctx.lineWidth=1;ctx.setLineDash([3,4]);ctx.beginPath();ctx.moveTo(...from);ctx.lineTo(...to);ctx.stroke();ctx.setLineDash([]);ctx.strokeRect(to[0]-3,to[1]-3,6,6);
   drawMinimap();
  }
  function drawMinimap(){const x=W-145,y=H-112,w=128,h=94;ctx.fillStyle='#10291ce0';ctx.fillRect(x,y,w,h);ctx.strokeStyle='#8ca77999';ctx.strokeRect(x+.5,y+.5,w,h);for(const t of state.targets){ctx.fillStyle=t.hp?'#e2bf75':'#6f7b67';ctx.fillRect(x+t.x/BOUNDS.width*w-2,y+t.y/BOUNDS.height*h-2,4,4);}ctx.fillStyle='#b5f3dc';ctx.fillRect(x+state.x/BOUNDS.width*w-3,y+state.y/BOUNDS.height*h-3,6,6);ctx.font='8px system-ui';ctx.textAlign='left';ctx.fillStyle='#c6d4bd';ctx.fillText('TRAINING GROVE',x+6,y+11);}
  const labs=[];for(const [d,name] of ['South','North','East','West'].entries()){const a=document.createElement('article');a.className='lab-view';a.innerHTML='<h3>'+name+'</h3><canvas width="128" height="128" aria-label="'+name+' animation"></canvas>';$('labViews').append(a);labs.push(a.querySelector('canvas'));}
  for(const c of clips){const o=document.createElement('option');o.value=c.id;o.textContent=c.label||c.id;$('clip').append(o);}$('clip').value=state.lab.id;
  function renderLab(){for(let d=0;d<4;d++){const c=labs[d],g=c.getContext('2d');g.clearRect(0,0,128,128);g.save();g.translate(32,32);animator.render(g,state.lab.id,state.lab.time,'SNEW'[d],{debug:$('skeleton').checked});g.restore();}const c=clip(state.lab.id);$('timeline').value=state.lab.time/c.duration*1000;$('labTime').textContent=state.lab.time.toFixed(2)+'s';$('labDuration').textContent=c.duration.toFixed(2)+'s';$('clipDescription').textContent=(c.description||c.label||c.id)+' · '+(c.events||[]).map(e=>e.type+' at '+e.time.toFixed(2)+'s').join(' · ');}
  function updateHud(){const t=selectedTarget();$('energyBar').style.width=state.energy+'%';$('energyText').textContent=Math.floor(state.energy)+' / 100 KI';$('healthBar').style.width=(t?t.hp:0)+'%';$('healthText').textContent=t?t.label+' · '+t.hp+' HP':'No target';$('stance').textContent=state.z>5?'ALT '+Math.round(state.z):'ON GROUND';$('enemyStatus').textContent=t?Math.round(Math.hypot(t.x-state.x,t.y-state.y))+' units':'—';$('hitCount').textContent=state.hits;$('actionName').textContent=clip(state.action).label||state.action;$('worldMessage').textContent=state.message;$('position').textContent=Math.round(state.x)+', '+Math.round(state.y)+' · '+state.facing;}
  function render(){state.mode==='world'?(drawWorld(),updateHud()):renderLab();}
  function setMode(mode){state.mode=mode==='lab'?'lab':'world';input.clear();keys.clear();document.querySelectorAll('.pressed').forEach(b=>b.classList.remove('pressed'));$('worldPanel').hidden=state.mode!=='world';$('labPanel').hidden=state.mode!=='lab';for(const [id,m] of [['worldTab','world'],['labTab','lab']]){$(id).classList.toggle('selected',state.mode===m);$(id).setAttribute('aria-selected',state.mode===m);}render();}
  let timingUrl=null;
  async function exportSheet(){
   const id=state.lab.id,c=clip(id),schedule=animator.timeline(id),n=schedule.times.length,a=document.createElement('canvas');a.width=768;a.height=192*n;const g=a.getContext('2d');
   for(let f=0;f<n;f++)for(let d=0;d<4;d++){g.save();g.translate(d*192+64,f*192+64);animator.render(g,id,schedule.times[f],'SNEW'[d]);g.restore();}
   const metadata={id,frames:n,cellSize:192,origin:[64,64],duration:c.duration,frameTimes:schedule.times,durationsMs:schedule.durationsMs,directions:['South','North','East','West'],renderer:'elf-rig',body:DBZ_DATA.actor.actor,bodyPixels:64,motionReference:c.motionReference,motionSource:c.motionSource,originalMotion:c.originalMotion,sourceStates:c.sourceStates,adapted:true};
   const blob=await new Promise(r=>a.toBlob(r,'image/png'));if(!blob)throw Error('PNG export failed');
   const url=URL.createObjectURL(blob),link=document.createElement('a');link.href=url;link.download='Elf_Ki_'+id+'_SNEW_192px.png';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
   if(timingUrl)URL.revokeObjectURL(timingUrl);timingUrl=URL.createObjectURL(new Blob([JSON.stringify(metadata,null,2)],{type:'application/json'}));
   $('exportTiming').href=timingUrl;$('exportTiming').download='Elf_Ki_'+id+'_timing.json';$('exportTiming').hidden=false;
   $('exportStatus').textContent='Exported '+n+' Elf rig poses × four directions · frame timing available as JSON.';
   return{...metadata,dataUrl:a.toDataURL()};
  }
  $('worldTab').onclick=()=>setMode('world');$('labTab').onclick=()=>setMode('lab');$('reset').onclick=reset;
  if($('motionEffects'))$('motionEffects').onchange=()=>setMotionEffects($('motionEffects').checked);
  $('clip').onchange=()=>{state.lab.id=$('clip').value;state.lab.time=0;renderLab();};$('labPlay').onclick=()=>{state.lab.playing=!state.lab.playing;$('labPlay').textContent=state.lab.playing?'Pause':'Play';};$('speed').onchange=()=>state.lab.speed=+$('speed').value;$('labLoop').onchange=()=>state.lab.loop=$('labLoop').checked;$('skeleton').onchange=renderLab;$('timeline').oninput=()=>{state.lab.playing=false;$('labPlay').textContent='Play';state.lab.time=+$('timeline').value/1000*clip(state.lab.id).duration;renderLab();};
  $('exportSheet').onclick=async()=>{try{$('exportSheet').disabled=true;await exportSheet();}catch(e){$('exportStatus').textContent=e.message;}finally{$('exportSheet').disabled=false;}};
  const actionKeys={j:'punch',k:'kick',l:'blast',h:'beam',q:'dash',' ':'hover',r:'reset'};
  window.addEventListener('keydown',e=>{if(state.mode!=='world'||['INPUT','SELECT','TEXTAREA'].includes(e.target.tagName))return;const k=e.key.toLowerCase();if(actionKeys[k]||['w','a','s','d','c','shift','arrowleft','arrowright','arrowup','arrowdown'].includes(k))e.preventDefault();keys.add(k);if(!e.repeat&&actionKeys[k])trigger(actionKeys[k]);});window.addEventListener('keyup',e=>keys.delete(e.key.toLowerCase()));window.addEventListener('blur',()=>{input.clear();keys.clear();document.querySelectorAll('.pressed').forEach(b=>b.classList.remove('pressed'));});
  function pointerAim(e){
   const r=canvas.getBoundingClientRect(),sx=(e.clientX-r.left)/r.width*W,sy=(e.clientY-r.top)/r.height*H;
   // A visible character is picked at its sprite, then aimed at in world space.
   // Empty-ground aiming uses the projectile's elevation plane.
   const picked=state.targets.filter(t=>t.hp>0).map(t=>({t,p:worldToScreen(t.x,t.y,t.z)})).filter(({p})=>Math.abs(sx-p[0])<28&&sy>=p[1]-120&&sy<=p[1]+5).sort((a,b)=>b.t.y-a.t.y)[0];
   if(picked)setAim(picked.t.x,picked.t.y);else setAim(...screenToWorld(sx,sy,state.z+58));
  }
  canvas.addEventListener('pointermove',e=>{if(e.pointerType!=='touch')pointerAim(e);});
  canvas.addEventListener('pointerdown',e=>{pointerAim(e);canvas.focus({preventScroll:true});});
  document.querySelectorAll('[data-action]').forEach(b=>b.onclick=()=>{trigger(b.dataset.action);canvas.focus({preventScroll:true});});document.querySelectorAll('[data-hold]').forEach(b=>{b.onpointerdown=e=>{e.preventDefault();input.add(b.dataset.hold);b.classList.add('pressed');b.setPointerCapture(e.pointerId);};const end=()=>{input.delete(b.dataset.hold);b.classList.remove('pressed');};b.onpointerup=end;b.onpointercancel=end;b.onlostpointercapture=end;});
  window.kiSandbox={state,step,trigger,reset,setMode,animator,clips,images,exportSheet,setInput,setAim,setMotionEffects,worldToScreen,screenToWorld,segmentDistance,setPaused:v=>{paused=Boolean(v);last=performance.now();},setLab:(id,time=0)=>{state.lab.id=id;state.lab.time=time;state.lab.playing=false;$('clip').value=id;$('labPlay').textContent='Play';setMode('lab');},render};
  reset();$('loadStatus').textContent='Ready · approved Elf rig · four facings';document.body.dataset.ready='true';render();function tick(now){const dt=Math.min(.05,(now-last)/1000);last=now;if(!paused)step(dt);requestAnimationFrame(tick);}requestAnimationFrame(tick);
 }catch(e){$('fatal').hidden=false;$('fatal').textContent='Could not start world test: '+e.message;$('loadStatus').textContent='Loading failed';console.error(e);}
})();
