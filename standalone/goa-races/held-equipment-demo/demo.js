(async()=>{
 const engine=new EquipmentEngine.Renderer(DATA);await engine.initialize();
 const canvases=[...document.querySelectorAll('canvas')],$=id=>document.getElementById(id),actions=createActions(engine,DATA);
 let family='spear-jab';
 const weaponIDs={'spear-jab':'weapon.spear','spear-sweep':'weapon.spear',sword:'weapon.arming sword',longsword:'weapon.longsword',scimitar:'weapon.scimitar',battleaxe:'weapon.battle axe',morningstar:'weapon.morning star',hammer:'weapon.warhammer',axe:'weapon.hand axe',mace:'weapon.mace',dagger:'weapon.dagger',spear:'weapon.spear',bow:'weapon.bow',staff:'weapon.crystal staff'};
 const labels={'spear-jab':['Low ready','Small drawback','Short jab'],'one-hand-sweep':['Guard','Windup','Sweep','Recovery'],sword:['Ready','Windup','Strike'],spear:['Ready','Draw back','Thrust'],bow:['Ready','Draw','Release'],staff:['Ready','Charge','Cast']};
 // Registered 64px body cells; explicit grips for each pose and direction.
 const grips=[
  [{weapon:[23,40],shield:[41,39]},{weapon:[43,39],shield:[22,39]},{weapon:[32,42],shield:[44,39]},{weapon:[19,40],shield:[28,35]}],
  [{weapon:[19,18],shield:[41,40]},{weapon:[46,14],shield:[20,40]},{weapon:[19,17],shield:[44,40]},{weapon:[45,15],shield:[24,34]}],
  [{weapon:[16,44],shield:[43,37]},{weapon:[50,43],shield:[16,37]},{weapon:[50,46],shield:[39,36]},{weapon:[13,40],shield:[27,33]}]
 ];
 const rotations=[[-12,12,15,-15],[-55,55,-60,60],[-115,115,100,-100]];
 const basePhases=[{row:0,ms:400,label:'Ready'},{row:1,ms:240,label:'Windup'},{row:2,ms:120,label:'Strike'},{row:2,ms:120,label:'Follow-through'},{row:0,ms:260,label:'Return to ready'}];
 const sweepPhases=[400,200,140,260].map((ms,row)=>({row,ms,label:labels['one-hand-sweep'][row]}));
 const jabPhases=[{row:0,ms:450},{row:1,ms:220},{row:2,ms:240},{row:0,ms:360}].map(p=>({...p,label:labels['spear-jab'][p.row]}));
 const melee=()=>['one-hand-sweep','spear-jab'].includes(family);
const flinchLabels=['Hit','Recoil','Recover'];
 const flinchPhases=[80,100,180].map((ms,row)=>({row,ms,label:flinchLabels[row]}));
 function choosePhases(){
  if($('motion').value==='flinch')return flinchPhases;
  if(!melee())return basePhases;
  if(!$('hop').checked)return family==='spear-jab'?jabPhases:sweepPhases;
  return [
   {row:0,ms:family==='spear-jab'?400:360,label:'Ready',rootFrom:0,rootTo:0,lift:0},
   {row:1,ms:family==='spear-jab'?240:170,label:'Hop back',rootFrom:0,rootTo:-1.5,lift:2},
   {row:family==='spear-jab'?0:1,ms:family==='spear-jab'?220:150,label:'Hop forward',rootFrom:-1.5,rootTo:1.5,lift:2.2},
   {row:2,ms:family==='spear-jab'?240:140,label:labels[family][2],rootFrom:1.5,rootTo:1,lift:0},
   {row:family==='spear-jab'?0:3,ms:family==='spear-jab'?360:240,label:'Settle',rootFrom:1,rootTo:0,lift:.4}
  ];
 }
 let phases=choosePhases();
 function snapshot(time){let t=((time%phases.reduce((n,p)=>n+p.ms,0))+phases.reduce((n,p)=>n+p.ms,0))%phases.reduce((n,p)=>n+p.ms,0),index=0;while(t>=phases[index].ms)t-=phases[index++].ms;return {row:phases[index].row,index,u:t/phases[index].ms};}
 function rootFor(s,view){const p=phases[s.index],u=s.u,e=u*u*(3-2*u),forward=(p.rootFrom||0)+((p.rootTo||0)-(p.rootFrom||0))*e,height=(p.lift||0)*Math.sin(Math.PI*u),dir=[[0,1],[0,-1],[1,0],[-1,0]][view];return {x:dir[0]*forward,y:dir[1]*forward*.45-height,height,groundY:dir[1]*forward*.45};}
 let motionState={row:0,index:0,u:0};
 const state={bodyId:'human',motion:'walk',frame:0,fits:{},loadout:{weapon:{id:'weapon.arming sword',material:'iron'},shield:{id:'shield.round',material:'iron'}}};
 let playing=true,start=performance.now(),mode='hold',phase=0,pausedTime=0,hitReturn=null;
 function sync(){state.loadout.weapon.id=$('weapon').checked?weaponIDs[$('loadout').value]:null;state.loadout.shield.id=$('shield').checked&&['sword','one-hand-sweep','spear-jab'].includes(family)?'shield.round':null;}
 // Orient the real blade tip toward the facing; gear-strip yaw is not attack pitch.
 const bladeDirections=[[[0,1],[0,-1],[1,-.6],[-1,-.6]],[[0,-1],[0,1],[-.6,-1],[.6,-1]],[[0,1],[0,-1],[1,.4],[-1,.4]]];
 const bladeCache=new Map();
 function drawBlade(c,view,row,anchor){
  const key=state.loadout.weapon.id+':'+(view===1?14:6);let b=bladeCache.get(key);
  if(!b){const item=engine.items.get(state.loadout.weapon.id),g=engine.gear(item,'iron',0),m=g.meta,sw=g.image.width/16;
   const im=document.createElement('canvas');im.width=sw;im.height=g.image.height;const x=im.getContext('2d');x.drawImage(g.image,(view===1?14:6)*sw,0,sw,g.image.height,0,0,sw,g.image.height);
   const pix=x.getImageData(0,0,sw,im.height).data;let tip=[m.ax,m.ay-1],dist=0;
   for(let y=0;y<im.height;y++)for(let k=0;k<sw;k++)if(pix[(y*sw+k)*4+3]>128){const d=(k-m.ax)**2+(y-m.ay)**2;if(d>dist){dist=d;tip=[k,y];}}
   b={im,m,angle:Math.atan2(tip[1]-m.ay,tip[0]-m.ax)};bladeCache.set(key,b);
  }
  const v=bladeDirections[row][view];c.save();c.translate(...anchor);c.rotate(Math.atan2(v[1],v[0])-b.angle);c.scale(.85,.85);c.drawImage(b.im,-b.m.ax,-b.m.ay);c.restore();
 }
 function combat(c,view,row,anchors){
  if(family!=='sword')return actions.draw(c,family,view,row,!!state.loadout.weapon.id,anchors,!!state.loadout.shield.id,state.loadout.weapon.id);
  const body=document.createElement('canvas');body.width=body.height=64;const bc=body.getContext('2d');bc.drawImage(engine.images.get(DATA.combatSource),view*64,row*64,64,64,0,0,64,64);
  const rig={height:56},fit=slot=>({anchor:grips[row][view][slot],x:slot==='shield'?[ -2,2,-2,2 ][view]:0,y:0,scale:1,stretch:1,rotation:slot==='weapon'?rotations[row][view]-(view===2?25:view===3?-25:0):0});
  const far=slot=>slot==='weapon'?(view===1||view===3):(view===1||view===2);
  const item=slot=>{const selected=state.loadout[slot];if(slot==='weapon'&&selected.id){drawBlade(c,view,row,fit(slot).anchor);return;}if(selected.id)engine.drawGear(c,engine.items.get(selected.id),selected.material,0,(EquipmentEngine.angles[view]+(slot==='shield'?135:0))%360,slot,rig,fit(slot));};
  for(const slot of ['weapon','shield'])if(far(slot))item(slot);
  c.drawImage(body,0,0);
  for(const slot of ['weapon','shield'])if(!far(slot))item(slot);
  // Restore foreground fist pixels over the grip.
  for(const slot of ['weapon'])if(state.loadout[slot].id&&!far(slot)){const [x,y]=grips[row][view][slot];c.save();c.beginPath();c.arc(x,y,2.1,0,Math.PI*2);c.clip();c.drawImage(body,0,0);c.restore();}
  if(anchors)for(const slot of ['weapon','shield']){const [x,y]=grips[row][view][slot];c.strokeStyle=slot==='weapon'?'#ffcc65':'#63eaca';c.lineWidth=.6;c.beginPath();c.arc(x,y,2,0,Math.PI*2);c.stroke();}
  return {view,row,grips:grips[row][view],rotations:rotations[row][view]};
 }
 function draw(canvas,view,row,anchors=false,drawMode=mode,root=null){const c=canvas.getContext('2d');c.clearRect(0,0,128,128);c.imageSmoothingEnabled=false;if(root){c.fillStyle='rgba(0,0,0,.18)';c.beginPath();c.ellipse(64+root.x,95+root.groundY,10-root.height*.6,2.2,0,0,Math.PI*2);c.fill();}c.save();c.translate(32+(root?.x||0),32+(root?.y||0));const result=drawMode==='flinch'?actions.drawFlinch(c,view,row,state.loadout.weapon.id,!!state.loadout.shield.id,anchors):drawMode==='walk'?engine.render(c,state,{angle:EquipmentEngine.angles[view],frame:row,anchors}):combat(c,view,row,anchors);c.restore();return result;}
 function tick(now){if(playing){let elapsed=now-start;if(hitReturn&&elapsed>=360){const back=hitReturn;hitReturn=null;mode=back.mode;$('motion').value=mode;phases=choosePhases();playing=back.playing;start=now;elapsed=0;$('play').textContent=playing?'Pause':'Resume';state.frame=0;}if(mode==='attack'||mode==='flinch'){motionState=snapshot(elapsed);phase=motionState.index;state.frame=motionState.row;}else if(mode==='walk')state.frame=[0,1,0,2][Math.floor(elapsed/200)%4];else state.frame=0;}
  sync();window.demoFrames=canvases.map((c,v)=>draw(c,v,state.frame,$('anchors').checked,mode,mode==='attack'&&melee()&&$('hop').checked?rootFor(motionState,v):null));$('status').textContent=((mode==='attack'||mode==='flinch')?phases[phase].label:mode==='hold'?'Idle / holding':'Original walk')+' · pose '+state.frame+' · '+$('loadout').selectedOptions[0].textContent+' · separate equipment layers';requestAnimationFrame(tick);}
 function pause(){playing=false;pausedTime=performance.now()-start;$('play').textContent='Resume';}
 $('play').onclick=()=>{if(playing)pause();else{playing=true;start=performance.now()-pausedTime;$('play').textContent='Pause';}};
 $('loadout').onchange=()=>{hitReturn=null;const value=$('loadout').value;family=['bow','staff','spear-jab'].includes(value)?value:'one-hand-sweep';phases=choosePhases();$('hop').disabled=!melee();$('shield').disabled=!['sword','one-hand-sweep','spear-jab'].includes(family);state.frame=0;phase=0;start=performance.now();pausedTime=0;};
 $('hop').onchange=()=>{phases=choosePhases();phase=0;state.frame=0;motionState={row:0,index:0,u:0};start=performance.now();pausedTime=0;};
 $('motion').onchange=()=>{hitReturn=null;mode=$('motion').value;phases=choosePhases();phase=0;state.frame=0;start=performance.now();pausedTime=0;};
 $('step').onclick=()=>{pause();if(mode==='attack'||mode==='flinch'){phase=(phase+1)%phases.length;state.frame=phases[phase].row;motionState={row:state.frame,index:phase,u:.5};}else if(mode==='walk')state.frame=(state.frame+1)%3;};
 window.sampleSheet=()=>{sync();const out=document.createElement('canvas');out.width=512;const rows=mode==='hold'?1:['walk','flinch'].includes(mode)?3:labels[family].length;out.height=rows*128;const c=out.getContext('2d');for(let r=0;r<rows;r++)for(let v=0;v<4;v++){const cell=document.createElement('canvas');cell.width=cell.height=128;draw(cell,v,r,false,mode);c.drawImage(cell,v*128,r*128);}return out;};
 $('hit').onclick=()=>{hitReturn={mode:mode==='flinch'?'hold':mode,playing};mode='flinch';$('motion').value=mode;phases=choosePhases();phase=0;state.frame=0;start=performance.now();playing=true;$('play').textContent='Pause';};
 window.animationSheet=time=>{sync();const snap=snapshot(time),out=document.createElement('canvas');out.width=512;out.height=128;const c=out.getContext('2d');for(let v=0;v<4;v++){const cell=document.createElement('canvas');cell.width=cell.height=128;draw(cell,v,snap.row,false,mode==='flinch'?'flinch':'attack',mode!=='flinch'&&melee()&&$('hop').checked?rootFor(snap,v):null);c.drawImage(cell,v*128,0);}return out;};
 window.combatMetadata=()=>({family,weapon:weaponIDs[$('loadout').value],frameSize:[128,128],bodyOrigin:[32,32],directions:['South','North','East','West'],action:mode,bodySource:mode==='flinch'?'combat/universal-flinch/body.png':null,rows:mode==='hold'?['Idle hold']:mode==='walk'?['neutral','step-a','step-b']:mode==='flinch'?flinchLabels:labels[family],phases:mode==='hold'?[{row:0,ms:1200,label:'Idle hold'}]:phases,rootMotion:{enabled:mode==='attack'&&melee()&&$('hop').checked,forwardProjection:[[0,.45],[0,-.45],[1,0],[-1,0]],positionCurve:'smoothstep',heightCurve:'lift*sin(pi*u)',sharedBodyAndEquipment:true},grips:mode==='walk'?null:mode==='flinch'?DATA.flinchProfile.grips.map(row=>row.map(g=>({...g,weapon:state.loadout.weapon.id==='weapon.bow'?g.shield:g.weapon}))):family==='sword'?(mode==='hold'?[grips[0]]:grips):(mode==='hold'?[actions.hands[family][0]]:actions.hands[family]),weaponHands:['one-hand-sweep','spear-jab'].includes(family)?1:null,jabProfile:family==='spear-jab'?DATA.jabProfile:null,sweepVectors:family==='one-hand-sweep'?DATA.sweepProfile.vectors.map((row,r)=>row.map((v,d)=>d===3&&r===0&&weaponIDs[$('loadout').value]!=='weapon.spear'?[.4,-1]:v)):null,rotations,bladeDirections,shieldFacingOffset:135,shieldForearmOffset:[-2,2,-2,2],loadout:state.loadout});
 $('export').onclick=()=>{const a=document.createElement('a');a.download='Human-'+$('loadout').value+'-'+mode+'.png';a.href=sampleSheet().toDataURL();a.click();const m=document.createElement('a');m.download='Human-'+$('loadout').value+'-'+mode+'.json';const url=URL.createObjectURL(new Blob([JSON.stringify(combatMetadata(),null,2)],{type:'application/json'}));m.href=url;m.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
 $('shield').checked=false;
 $('shield').disabled=false;
 window.demo={engine,state,draw,grips,actions,snapshot,rootFor};window.demoReady=true;requestAnimationFrame(tick);
})().catch(e=>{document.getElementById('status').textContent=e.message;throw e;});
