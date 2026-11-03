/* Four-view carry proof. The character artwork and held equipment remain separate. */
(async()=>{
 const eq=new EquipmentEngine.Renderer(DATA);await eq.initialize();
 const cv=(w,h)=>Object.assign(document.createElement('canvas'),{width:w,height:h});
 const state={motion:'carry-walk',weapon:'weapon.arming sword',shield:true,playing:true,time:0,speed:1};
 const strips=new Map(),views=[...document.querySelectorAll('.views canvas')];
 function weaponRaster(id,view){const key=id+':'+view;if(strips.has(key))return strips.get(key);const item=eq.items.get(id),g=eq.gear(item,id==='weapon.crystal staff'?'silver':'iron',0),cell=view===1?14:6,w=g.image.width/16,im=cv(w,g.image.height),c=im.getContext('2d');c.drawImage(g.image,cell*w,0,w,im.height,0,0,w,im.height);const p=c.getImageData(0,0,w,im.height).data;let far=0,tip=[g.meta.ax,g.meta.ay-1];for(let y=0;y<im.height;y++)for(let x=0;x<w;x++)if(p[(y*w+x)*4+3]>128){const d=(x-g.meta.ax)**2+(y-g.meta.ay)**2;if(d>far){far=d;tip=[x,y];}}const r={im,meta:g.meta,axis:Math.atan2(tip[1]-g.meta.ay,tip[0]-g.meta.ax)};strips.set(key,r);return r;}
 function draw(c,view,time=state.time,opts={}){
  const s={...state,...opts},moving=s.motion.endsWith('walk'),carrying=s.motion.startsWith('carry'),phase=Math.floor((time%900)/225),frame=moving?[0,1,0,2][phase]:0,row=carrying?frame:frame,body=eq.images.get(carrying?'armedWalk':'body'),bob=carrying&&moving&&(phase===1||phase===3)?-.5:0;
  c.clearRect(0,0,c.canvas.width,c.canvas.height);c.imageSmoothingEnabled=false;c.save();c.translate((c.canvas.width-64)/2,(c.canvas.height-64)/2+bob);
  const profile=DATA.carry.views[view],grip=profile.R,shieldGrip=profile.L,farWeapon=view===1||view===3,farShield=view===1||view===2;
  const bodyLayer=()=>c.drawImage(body,view*64,row*64,64,64,0,0,64,64);
  const drawWeapon=()=>{if(!carrying||!s.weapon)return;const r=weaponRaster(s.weapon,view),angle=s.weapon==='weapon.arming sword'?Math.atan2(-1,[0,0,.08,-.08][view]):-Math.PI/2,length=s.weapon==='weapon.spear'?.82:s.weapon==='weapon.crystal staff'?.9:1.15,width=s.weapon==='weapon.spear'?.65:.95;c.save();c.translate(...grip);c.rotate(angle);c.scale(length,width);c.rotate(-r.axis);c.drawImage(r.im,-r.meta.ax,-r.meta.ay);c.restore();};
  const drawShield=()=>{if(!carrying||!s.shield)return;eq.drawGear(c,eq.items.get('shield.round'),'iron',0,profile.shieldAngle,'shield',{height:56},{anchor:shieldGrip,x:profile.shieldBias[0],y:profile.shieldBias[1],scale:1.05,stretch:1,rotation:0});};
  if(farWeapon)drawWeapon();if(farShield)drawShield();bodyLayer();if(!farWeapon)drawWeapon();if(!farShield)drawShield();
  if(carrying&&s.weapon&&!farWeapon){c.save();c.beginPath();c.arc(grip[0],grip[1],2.15,0,2*Math.PI);c.clip();bodyLayer();c.restore();}
  c.restore();return {view,sourceFrame:frame,bodyOrigin:[(c.canvas.width-64)/2,(c.canvas.height-64)/2+bob],grip:[grip[0],grip[1]+bob],shieldGrip:[shieldGrip[0],shieldGrip[1]+bob],carrying,weapon:carrying?s.weapon:null,shield:carrying&&s.shield};
 }
 function sheet(opts={},count=4){const out=cv(512,128*count),c=out.getContext('2d'),cell=cv(128,128);for(let r=0;r<count;r++)for(let v=0;v<4;v++){draw(cell.getContext('2d'),v,r*900/count,opts);c.drawImage(cell,v*128,r*128);}return out;}
 function save(filename,src){const a=document.createElement('a');a.download=filename;a.href=src;a.click();}
 document.querySelector('#motion').onchange=e=>state.motion=e.target.value;
 document.querySelector('#weapon').onchange=e=>state.weapon=e.target.value;
 document.querySelector('#shield').onchange=e=>state.shield=e.target.checked;
 document.querySelector('#speed').oninput=e=>state.speed=+e.target.value;
 document.querySelector('#play').onclick=e=>{state.playing=!state.playing;e.target.textContent=state.playing?'Pause':'Play';};
 document.querySelector('#export').onclick=()=>save('Human-Male-Remake-v2-'+state.motion+'.png',sheet().toDataURL());
 let last=performance.now();function loop(now){if(state.playing)state.time+=(now-last)*state.speed;last=now;window.carryFrame=views.map((v,i)=>draw(v.getContext('2d'),i));requestAnimationFrame(loop);}requestAnimationFrame(loop);
 window.carry={state,eq,draw,sheet,data:DATA};window.carryReady=true;
 document.querySelector('#status').textContent='Human male · 64 × 64 body cells · South / North / East / West';
})().catch(e=>{document.querySelector('#status').textContent=e.message;throw e;});
