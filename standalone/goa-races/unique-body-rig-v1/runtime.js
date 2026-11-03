/* A small sprite/arm rig, independent of a game engine. No network dependencies. */
(() => {
  'use strict';
  const data = window.RIG_DATA, $ = id => document.getElementById(id);
  const images = {}, canvases = [], keys = ['chestX','chestY','mainX','mainY','offX','offY'];
  const blankFits = () => Array.from({length:4}, () => Object.fromEntries(keys.map(k=>[k,0])));
  let fits = blankFits(), playing = true, phase = 0, start = performance.now();
  const settings = () => ({chest:$('chest').checked,spear:$('spear').checked,shield:$('shield').checked,debug:$('debug').checked,completed:$('completed').checked});
  const dist = (a,b) => Math.hypot(a[0]-b[0],a[1]-b[1]);
  const angle = (a,b) => Math.atan2(b[1]-a[1],b[0]-a[0]);
  const add = (a,b) => [a[0]+b[0],a[1]+b[1]];
  const targets={
    hold:[{right:[19,37],left:[44,39]},{right:[44,37],left:[19,39]},{right:[40,36],left:[35,39]}]
  };
  function facingTargets(kind,d){
    const source=targets[kind][d===3?2:d];
    if(d===3)return {right:[63-source.left[0],source.left[1]],left:[63-source.right[0],source.right[1]]};
    return {right:source.right.slice(),left:source.left.slice()};
  }
  // Reach-limited two-bone IK. Items use the solved endpoint, never the unclamped target.
  function solve(shoulder, target, upper, lower, bend) {
    let delta=[target[0]-shoulder[0],target[1]-shoulder[1]], distance=Math.hypot(...delta);
    if(distance<1e-8){delta=[0,1];distance=1;}
    const reach=Math.max(Math.abs(upper-lower)+.001, Math.min(distance,upper+lower-.001));
    const direction=Math.atan2(delta[1],delta[0]);
    const a=Math.acos(Math.max(-1,Math.min(1,(upper*upper+reach*reach-lower*lower)/(2*upper*reach))));
    const elbow=add(shoulder,[Math.cos(direction+bend*a)*upper,Math.sin(direction+bend*a)*upper]);
    return {shoulder,elbow,hand:add(shoulder,[Math.cos(direction)*reach,Math.sin(direction)*reach]),upper,lower};
  }
  function projectedArm(d,side,pitch,bob=0){
      const src=data.directions[d].arms[side],points=[add(src[0],[0,bob])],depths=[0];
      for(let i=0;i<2;i++){
        const dx=src[i+1][0]-src[i][0],dy=src[i+1][1]-src[i][1];
        let projected,depth=0;
        if(d<2){projected=[dx,dy*Math.cos(pitch)];depth=dy*Math.sin(pitch)*(d===0?1:-1);}
        else{const sign=d===2?1:-1;projected=[dx*Math.cos(pitch)+sign*dy*Math.sin(pitch),dy*Math.cos(pitch)-sign*dx*Math.sin(pitch)];}
        points.push(add(points[i],projected));depths.push(depths[i]+depth);
      }
      return {shoulder:points[0],elbow:points[1],hand:points[2],upper:dist(points[0],points[1]),lower:dist(points[1],points[2]),restUpper:dist(src[0],src[1]),restLower:dist(src[1],src[2]),depths,projected:d<2};
  }
  function forwardRaise(d,p){
    const pitch=(1-Math.cos(p*Math.PI*2))/2*data.raiseMotion.maxPitchDegrees*Math.PI/180;
    const arms=Object.fromEntries(['right','left'].map(side=>[side,projectedArm(d,side,pitch)]));
    return {frame:0,bob:0,arms,weaponAngle:0,pitch};
  }
  function pose(d, motion, p, options=settings()) {
    if(motion==='raise')return forwardRaise(d,p);
    const spec=data.directions[d], walk=motion==='walk', thrust=motion==='thrust';
    const frame=walk ? [0,1,0,2][Math.floor(p*4)%4] : 0;
    const bob=walk && frame!==0 ? -1:0;
    const push=thrust ? Math.pow(Math.max(0,Math.sin(p*Math.PI)),3):0;
    const holds=facingTargets('hold',d),main=holds.right,off=holds.left;
    if(walk){main[1]+=Math.sin(p*Math.PI*2)*.8;off[1]-=Math.sin(p*Math.PI*2)*.6;}
    if(thrust){main[0]+=[-2,2,5,-5][d]*push;main[1]+=[4,-4,-3,-3][d]*push;}
    const fit=fits[d];main[0]+=fit.mainX;main[1]+=fit.mainY+bob;off[0]+=fit.offX;off[1]+=fit.offY+bob;
    const arms={};
    for(const side of ['right','left']) {
      const source=spec.arms[side], shoulder=add(source[0],[0,bob]);
      if(walk&&!(side==='right'?options.spear:options.shield)){
        // Opposite arm/leg swing, projected in the sagittal plane. Reflection
        // changes the near anatomical side but never flips a temporal frame.
        const near=d===3?'left':'right';
        const pitch=Math.sin(p*Math.PI*2)*.28*(side===near?-1:1);
        arms[side]=projectedArm(d,side,pitch,bob);continue;
      }
      let target=side==='right'?main:off;
      const swing=(d===1?-1:1)*Math.sin(p*Math.PI*2)*2;
      if(motion!=='raise'&&side==='right'&&!options.spear)target=add(source[2],[walk?swing:0,bob]);
      if(motion!=='raise'&&side==='left'&&!options.shield)target=add(source[2],[walk?-swing:0,bob]);
      let bend=d===2?1:d===3?-1:(source[0][0]<32?1:-1);
      arms[side]=solve(shoulder,target,dist(source[0],source[1]),dist(source[1],source[2]),bend);
    }
    return {frame,bob,arms,weaponAngle:thrust?([-.25,.25,Math.PI/2,-Math.PI/2][d]*push):0};
  }
  function limb(ctx,image,sourceStart,sourceEnd,start,end,projected=false) {
    ctx.save();ctx.translate(Math.round(start[0]),Math.round(start[1]));
    if(projected){
      ctx.rotate(angle(start,end));
      ctx.scale(Math.max(.02,dist(start,end)/dist(sourceStart,sourceEnd)),1);
      ctx.rotate(-angle(sourceStart,sourceEnd));
    }else ctx.rotate(angle(start,end)-angle(sourceStart,sourceEnd));
    ctx.drawImage(images[image],-sourceStart[0],-sourceStart[1]);ctx.restore();
  }
  function drawHand(ctx,image,src,solved){
    ctx.save();ctx.translate(Math.round(solved.hand[0]),Math.round(solved.hand[1]));
    if(!solved.projected)ctx.rotate(angle(solved.elbow,solved.hand)-angle(src[1],src[2]));
    ctx.drawImage(images[image],-src[2][0],-src[2][1]);ctx.restore();
  }
  function item(ctx,asset,hand,rotation=0) {
    ctx.save();ctx.translate(Math.round(hand[0]),Math.round(hand[1]));ctx.rotate(rotation);
    ctx.drawImage(images[asset.image],-asset.grip[0],-asset.grip[1]);ctx.restore();
  }
  function fullPose(d,p,options=settings()){
    const spec=data.directions[d],body=spec.fullBody;
    const state=pose(d,'walk',p,options),bob=0;
    for(const arm of Object.values(state.arms))for(const key of ['shoulder','elbow','hand'])arm[key][1]+=bob-state.bob;
    state.bob=bob;state.frame=0;state.legs={};
    for(const side of ['right','left']){
      const src=body.legs[side],near=side===body.nearLeg;
      const cycle=p*Math.PI*2+(near?0:Math.PI),stride=Math.sin(cycle);
      const target=src[2].slice();
      if(d>=2)target[0]+=(d===2?1:-1)*stride*1.5;
      else target[1]+=(d===0?1:-1)*stride*.12;
      target[1]-=Math.max(0,Math.cos(cycle))*.25;
      const solved=solve(add(src[0],[0,bob]),target,dist(src[0],src[1]),dist(src[1],src[2]),d===2?-1:d===3?1:src[0][0]<32?1:-1);
      state.legs[side]={hip:solved.shoulder,knee:solved.elbow,ankle:solved.hand,upper:solved.upper,lower:solved.lower,footAngle:d<2?0:(d===2?1:-1)*Math.max(0,Math.cos(cycle))*.06};
    }
    state.headAngle=Math.sin(p*Math.PI*2)*.035;
    const anchors={pelvis:{position:add(body.waist,[0,bob]),rotation:0},torso:{position:add(body.waist,[0,bob]),rotation:0},head:{position:add(body.neck,[0,bob]),rotation:state.headAngle}};
    for(const side of ['right','left']){
      const a=state.arms[side],l=state.legs[side],arm=spec.arms[side],leg=body.legs[side];
      for(const [part,start,end,src] of [['UpperArm',a.shoulder,a.elbow,arm.slice(0,2)],['Forearm',a.elbow,a.hand,arm.slice(1)],['Thigh',l.hip,l.knee,leg.slice(0,2)],['Shin',l.knee,l.ankle,leg.slice(1)]]){
        anchors[side+part]={position:start,rotation:angle(start,end)-angle(...src),start,end,source:src,projected:(part==='UpperArm'||part==='Forearm')&&a.projected===true};
      }
      anchors[side+'Hand']={position:a.hand,rotation:a.projected?0:angle(a.elbow,a.hand)-angle(arm[1],arm[2])};
      anchors[side+'Foot']={position:l.ankle,rotation:l.footAngle};
    }
    state.attachments=Object.fromEntries(Object.entries(data.fullBody.slots).map(([slot,part])=>[slot,{part,...anchors[part]}]));
    return state;
  }
  function renderFullBody(ctx,d,p,options,selected='all'){
    const spec=data.directions[d],body=spec.fullBody,state=fullPose(d,p,options),parts=body.parts;
    const show=name=>selected==='all'||selected===name;
    const leg=side=>{
      const src=body.legs[side],a=state.legs[side];
      if(show(side+'Thigh'))limb(ctx,parts[side+'Thigh'],src[0],src[1],a.hip,a.knee);
      if(show(side+'Shin'))limb(ctx,parts[side+'Shin'],src[1],src[2],a.knee,a.ankle);
      if(show(side+'Foot'))item(ctx,{image:parts[side+'Foot'],grip:src[2]},a.ankle,a.footAngle);
    };
    const arm=side=>{
      const src=spec.arms[side],a=state.arms[side];
      if(show(side+'UpperArm'))limb(ctx,parts[side+'UpperArm'],src[0],src[1],a.shoulder,a.elbow,a.projected);
      if(show(side+'Forearm'))limb(ctx,parts[side+'Forearm'],src[1],src[2],a.elbow,a.hand,a.projected);
      if(selected==='all'&&side==='right'&&options.spear)item(ctx,data.spear,a.hand);
      if(show(side+'Hand'))drawHand(ctx,parts[side+'Hand'],src,a);
      if(selected==='all'&&side==='left'&&options.shield)item(ctx,spec.shield,a.hand);
    };
    const legOrder=d>=2?[body.nearLeg==='right'?'left':'right',body.nearLeg]:['right','left'].sort((a,b)=>state.legs[a].ankle[1]-state.legs[b].ankle[1]);
    legOrder.forEach(leg);
    if(d===2||d===1)arm('left');if(d===3||d===1)arm('right');
    if(show('torso'))ctx.drawImage(images[parts.torso],0,state.bob);
    if(show('pelvis'))ctx.drawImage(images[parts.pelvis],0,state.bob);
    if(selected==='all'&&options.chest)ctx.drawImage(images[spec.chest.image],spec.chest.origin[0]+fits[d].chestX,spec.chest.origin[1]+fits[d].chestY+state.bob);
    if(show('head'))item(ctx,{image:parts.head,grip:body.neck},add(body.neck,[0,state.bob]),state.headAngle);
    if(d!==3&&d!==1)arm('right');if(d!==2&&d!==1)arm('left');
    if(options.debug){
      ctx.lineWidth=.65;ctx.strokeStyle='#90e2a0';
      const chains=[...Object.values(state.arms).map(a=>[a.shoulder,a.elbow,a.hand]),...Object.values(state.legs).map(a=>[a.hip,a.knee,a.ankle])];
      for(const chain of chains){ctx.beginPath();ctx.moveTo(...chain[0]);chain.slice(1).forEach(pt=>ctx.lineTo(...pt));ctx.stroke();for(const pt of chain){ctx.fillStyle='#f6cd6f';ctx.fillRect(Math.round(pt[0])-1,Math.round(pt[1])-1,2,2);}}
      ctx.strokeStyle='#b3d9ff';ctx.beginPath();ctx.moveTo(...add(body.waist,[0,state.bob]));ctx.lineTo(...add(body.neck,[0,state.bob]));ctx.stroke();
    }
    return state;
  }
  function render(canvas,d,motion,p,options=settings()) {
    const ctx=canvas.getContext('2d');ctx.clearRect(0,0,canvas.width,canvas.height);ctx.imageSmoothingEnabled=false;
    ctx.save();ctx.translate(32,32);
    if(motion==='fullbody'){
      const state=renderFullBody(ctx,d,p,options,options.part||$('bodyPart').value);ctx.restore();return state;
    }
    const spec=data.directions[d], posed=pose(d,motion,p,options), {frame,bob,arms}=posed;
    const suffix=options.completed===false?'-rig':'-refined';
    if(motion==='original') {
      const f=[0,1,0,2][Math.floor(p*4)%4];ctx.drawImage(images['elf-original.png'],d*64,f*64,64,64,0,0,64,64);
      ctx.restore();return posed;
    }
    const drawArm=(side,lower=true)=>{
      const src=spec.arms[side], solved=arms[side];
      limb(ctx,spec.frames[0][side+'-upper'+suffix],src[0],src[1],solved.shoulder,solved.elbow,solved.projected);
      if(lower){
        limb(ctx,spec.frames[0][side+'-forearm'+suffix],src[1],src[2],solved.elbow,solved.hand,solved.projected);
        drawHand(ctx,spec.frames[0][side+'-hand'+suffix],src,solved);
      }
    };
    const drawMain=()=>{drawArm('right',false);const src=spec.arms.right;limb(ctx,spec.frames[0]['right-forearm'+suffix],src[1],src[2],arms.right.elbow,arms.right.hand,arms.right.projected);if(options.spear)item(ctx,data.spear,arms.right.hand,posed.weaponAngle);drawHand(ctx,spec.frames[0]['right-hand'+suffix],src,arms.right);};
    const drawOff=()=>{drawArm('left');if(options.shield)item(ctx,spec.shield,arms.left.hand);};
    // Direction-aware occlusion; the offhand is behind the right-facing torso.
    if(d===2||d===1)drawOff();if(d===3||d===1)drawMain();
    ctx.drawImage(images[spec.frames[frame][options.completed===false?'equipped-torso':'refined-torso']],0,0);
    if(options.chest)ctx.drawImage(images[spec.chest.image],spec.chest.origin[0]+fits[d].chestX,spec.chest.origin[1]+fits[d].chestY+bob);
    ctx.drawImage(images[spec.frames[frame][options.completed===false?'head':'render-head']],0,0);
    if(d!==3&&d!==1)drawMain();if(d!==2&&d!==1)drawOff();
    if(options.debug){
      ctx.lineWidth=.65;ctx.strokeStyle='#90e2a0';
      for(const side of ['right','left']){
        const arm=arms[side];ctx.beginPath();ctx.moveTo(...arm.shoulder);ctx.lineTo(...arm.elbow);ctx.lineTo(...arm.hand);ctx.stroke();
        for(const pt of [arm.shoulder,arm.elbow]){ctx.fillStyle='#90e2a0';ctx.fillRect(pt[0]-1,pt[1]-1,2,2);}
        ctx.strokeStyle=side==='right'?'#f6cd6f':'#ff8eb4';ctx.beginPath();ctx.arc(...arm.hand,2,0,Math.PI*2);ctx.stroke();ctx.strokeStyle='#90e2a0';
      }
      ctx.strokeStyle='#b3d9ff';ctx.strokeRect(spec.chest.origin[0]+fits[d].chestX,spec.chest.origin[1]+fits[d].chestY+bob,images[spec.chest.image].width,images[spec.chest.image].height);
    }
    ctx.restore();return posed;
  }
  function draw(){canvases.forEach((c,d)=>render(c,d,$('motion').value,phase));}
  function sync(){$('completed').disabled=$('motion').value==='fullbody';const fit=fits[+$('facing').value];keys.forEach(k=>{$(k).value=fit[k];$(k).disabled=$('motion').value==='raise'&&(k.startsWith('main')||k.startsWith('off'));});}
  function download(blob,name){const url=URL.createObjectURL(blob),link=document.createElement('a');link.href=url;link.download=name;link.click();setTimeout(()=>URL.revokeObjectURL(url),2000);}
  function png(canvas,name){canvas.toBlob(blob=>download(blob,name),'image/png');}
  function exportAtlas(motion=$('motion').value){
    const atlas=document.createElement('canvas');atlas.width=512;atlas.height=1024;const ctx=atlas.getContext('2d'),tile=document.createElement('canvas');tile.width=tile.height=128;
    for(let f=0;f<8;f++)for(let d=0;d<4;d++){render(tile,d,motion,f/8,{...settings(),debug:false});ctx.drawImage(tile,d*128,f*128);}
    return atlas;
  }
  function comparison(){
    const atlas=document.createElement('canvas');atlas.width=512;atlas.height=384;const ctx=atlas.getContext('2d'),tile=document.createElement('canvas');tile.width=tile.height=128;
    ['original','idle','thrust'].forEach((motion,row)=>{for(let d=0;d<4;d++){render(tile,d,motion,.5,{...settings(),debug:false});ctx.drawImage(tile,d*128,row*128);}});return atlas;
  }
  async function init(){
    await Promise.all(Object.entries(data.images).map(([key,url])=>new Promise((resolve,reject)=>{const im=new Image();im.onload=()=>{images[key]=im;resolve();};im.onerror=()=>reject(Error('Cannot decode '+key));im.src=url;})));
    data.directions.forEach((spec,d)=>{
      const panel=document.createElement('article');panel.className='view';panel.innerHTML='<h2>'+spec.name+'</h2><canvas width="128" height="128" aria-label="'+spec.name+' equipment preview"></canvas><p>Original Elf · '+(d===2?'shield behind torso':d===3?'spear behind torso':'independent hands')+'</p>';$('views').append(panel);const c=panel.querySelector('canvas');canvases.push(c);
      let drag=null;
      c.addEventListener('pointerdown',event=>{if(!$('debug').checked)return;if($('motion').value==='raise'){$('status').textContent='Forward raise uses shared anatomy. Choose Idle hold to adjust equipment grips.';return;}const rect=c.getBoundingClientRect(),pt=[(event.clientX-rect.left)*128/rect.width-32,(event.clientY-rect.top)*128/rect.height-32],state=$('motion').value==='fullbody'?fullPose(d,phase):pose(d,$('motion').value,phase);const side=dist(pt,state.arms.right.hand)<dist(pt,state.arms.left.hand)?'right':'left';if(dist(pt,state.arms[side].hand)>8)return;drag={pt,side,x:fits[d][side==='right'?'mainX':'offX'],y:fits[d][side==='right'?'mainY':'offY']};playing=false;$('play').textContent='Play';$('facing').value=d;sync();c.setPointerCapture(event.pointerId);});
      c.addEventListener('pointermove',event=>{if(!drag)return;const rect=c.getBoundingClientRect(),pt=[(event.clientX-rect.left)*128/rect.width-32,(event.clientY-rect.top)*128/rect.height-32],prefix=drag.side==='right'?'main':'off';fits[d][prefix+'X']=Math.max(-12,Math.min(12,Math.round(drag.x+pt[0]-drag.pt[0])));fits[d][prefix+'Y']=Math.max(-12,Math.min(12,Math.round(drag.y+pt[1]-drag.pt[1])));sync();draw();});
      c.addEventListener('pointerup',()=>drag=null);c.addEventListener('pointercancel',()=>drag=null);
    });
    $('play').onclick=()=>{playing=!playing;$('play').textContent=playing?'Pause':'Play';start=performance.now()-phase*1200;};
    $('phase').oninput=()=>{playing=false;$('play').textContent='Play';phase=+$('phase').value/8;draw();};
    ['motion','chest','spear','shield','debug','completed'].forEach(id=>$(id).onchange=draw);
    $('motion').onchange=()=>{sync();draw();};
    $('bodyPart').onchange=()=>{$('motion').value='fullbody';sync();draw();};
    $('facing').onchange=sync;keys.forEach(k=>$(k).oninput=()=>{fits[+$('facing').value][k]=Math.max(-12,Math.min(12,Number($(k).value)||0));draw();});
    $('zoom').onchange=()=>document.documentElement.style.setProperty('--sprite-scale',$('zoom').value);
    $('reset').onclick=()=>{fits=blankFits();sync();draw();$('status').textContent='Fit reset.';};
    $('saveFit').onclick=()=>download(new Blob([JSON.stringify({version:1,actor:'elf',directions:data.directions.map(d=>d.name),fits},null,2)],{type:'application/json'}),'elf-equipment-fit.json');
    $('loadFit').onclick=()=>$('fitFile').click();
    $('fitFile').onchange=async()=>{try{const file=$('fitFile').files[0];if(!file)return;const value=JSON.parse(await file.text());if(value.version!==1||value.actor!=='elf'||!Array.isArray(value.fits)||value.fits.length!==4||!value.fits.every(f=>keys.every(k=>Number.isFinite(f[k])&&Math.abs(f[k])<=12)))throw Error('Expected an Elf v1 fit with four directions and offsets from −12 to 12.');fits=value.fits.map(f=>Object.fromEntries(keys.map(k=>[k,f[k]])));sync();draw();$('status').textContent='Fit imported.';}catch(error){$('status').textContent='Could not import: '+error.message;}$('fitFile').value='';};
    $('export').onclick=()=>{png(exportAtlas(),'elf-'+$('motion').value+'-equipment-128px.png');$('status').textContent='Exported 4 directions × 8 frames, 128px cells.';};
    $('contact').onclick=()=>png(comparison(),'elf-original-idle-thrust-comparison.png');
    $('exportParts').onclick=()=>{
      const c=document.createElement('canvas');c.width=256;c.height=data.fullBody.parts.length*64;
      data.fullBody.parts.forEach((part,row)=>data.directions.forEach((spec,d)=>c.getContext('2d').drawImage(images[spec.fullBody.parts[part]],d*64,row*64)));
      png(c,'elf-full-body-components-64px.png');
    };
    window.equipmentRig={data,render,pose,fullPose,solve,exportAtlas,comparison,images,getFits:()=>structuredClone(fits),setPhase:p=>{playing=false;phase=p;$('play').textContent='Play';$('phase').value=Math.floor(p*8);draw();}};
    document.body.dataset.ready='true';sync();draw();
    function tick(now){if(playing){phase=((now-start)%1200)/1200;$('phase').value=Math.floor(phase*8);draw();}requestAnimationFrame(tick);}requestAnimationFrame(tick);
  }
  init().catch(error=>{$('status').textContent=error.message;console.error(error);});
})();
