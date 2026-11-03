/* Reference review only. The world continues to render the approved Elf rig. */
'use strict';
(async()=>{
 const $=id=>document.getElementById(id),IDS=['punch','punch2','kick','kick2'],DIRS='SNEW';
 const clamp=(n,a,b)=>Math.max(a,Math.min(b,n));
 try{
  if(!window.DBZ_DATA?.actor||!window.GOA_REFERENCE?.goa||!window.DbzAnimator||!window.GoaFrameAnimator)throw Error('Comparison assets are missing. Rebuild the side project and reload.');
  const decode=async sources=>Object.fromEntries(await Promise.all(Object.entries(sources).map(async([key,url])=>[key,await new Promise((resolve,reject)=>{const image=new Image();const timeout=setTimeout(()=>reject(Error('Image loading timed out: '+key)),15000);image.onload=()=>{clearTimeout(timeout);resolve(image);};image.onerror=()=>{clearTimeout(timeout);reject(Error('Cannot load '+key));};image.src=url;})])));
  const [elfImages,goaImages]=await Promise.all([decode(DBZ_DATA.images),decode(GOA_REFERENCE.images)]);
  const elfAnimator=new DbzAnimator(DBZ_DATA,elfImages),goaAnimator=new GoaFrameAnimator(GOA_REFERENCE,goaImages);
  const clips={elf:Object.fromEntries(DbzAnimator.clips.map(c=>[c.id,c])),goa:Object.fromEntries(GoaFrameAnimator.clips.map(c=>[c.id,c]))};
  const params=new URLSearchParams(location.search),state={move:IDS.includes(params.get('move'))?params.get('move'):'punch',mode:params.get('timing')==='native'?'native':'contact',progress:0,speed:.5,playing:true,skeleton:false};
  const views=[];
  for(const [i,name]of ['South','North','East','West'].entries()){
   const card=document.createElement('article');card.className='direction-card';card.dataset.facing=DIRS[i];
   card.innerHTML='<div class="card-head"><h2>'+name+'</h2><span>Same view · shared ground line</span></div><div class="pair"><figure><figcaption>Original GOA</figcaption><canvas width="128" height="96" aria-label="Original GOA '+name+'"></canvas><p class="frame-label"></p></figure><figure><figcaption>Our Elf</figcaption><canvas width="128" height="96" aria-label="Our Elf '+name+'"></canvas><p class="frame-label"></p></figure></div><div class="card-foot"><span>GOA <b class="source-name"></b></span><span>Elf <b class="elf-name"></b></span></div>';
   $('comparisonViews').append(card);views.push({facing:DIRS[i],card,canvases:[...card.querySelectorAll('canvas')],labels:[...card.querySelectorAll('.frame-label')]});
  }
  for(const id of IDS){const option=document.createElement('option');option.value=id;option.textContent=clips.goa[id].sourceStates[0]+' / '+clips.elf[id].label;$('moveSelect').append(option);}
  function getTimes(move=state.move,progress=state.progress,mode=state.mode){
   if(!IDS.includes(move))throw Error('Unknown comparison move: '+move);
   const source=clips.goa[move],elf=clips.elf[move],p=clamp(Number(progress)||0,0,1),goaImpact=source.events[0].time,elfImpact=elf.events[0].time,duration=Math.max(source.duration,elf.duration);
   const aligned=(length,impact)=>p<=.5?p*2*impact:impact+(p-.5)*2*(length-impact);
   const goa=mode==='native'?Math.min(p*duration,source.duration):aligned(source.duration,goaImpact);
   const own=mode==='native'?Math.min(p*duration,elf.duration):aligned(elf.duration,elfImpact);
   return{goa,source:goa,elf:own,duration,progress:p,goaImpact,elfImpact};
  }
  function stage(ctx,animator,move,time,facing,{x=0,y=0,skeleton=false}={}){
   ctx.save();ctx.imageSmoothingEnabled=false;ctx.translate(x,y);ctx.fillStyle='#20372b';ctx.fillRect(0,0,128,96);
   ctx.strokeStyle='#61876b66';ctx.lineWidth=1;ctx.setLineDash([2,3]);ctx.beginPath();ctx.moveTo(10,78.5);ctx.lineTo(118,78.5);ctx.stroke();ctx.setLineDash([]);
   ctx.fillStyle='#12271b';ctx.beginPath();ctx.ellipse(64,80,15,3,0,0,Math.PI*2);ctx.fill();
   ctx.translate(32,16);const pose=animator.render(ctx,move,time,facing,{debug:skeleton});ctx.restore();return pose;
  }
  function render(){
   const times=getTimes(),source=clips.goa[state.move],elf=clips.elf[state.move];
   for(const v of views){
    const sourcePose=stage(v.canvases[0].getContext('2d'),goaAnimator,state.move,times.goa,v.facing);
    stage(v.canvases[1].getContext('2d'),elfAnimator,state.move,times.elf,v.facing,{skeleton:state.skeleton});
    v.labels[0].textContent='Pose '+(sourcePose.sourceFrame+1)+' / 2 · '+Math.round(times.goa*1000)+' ms';
    v.labels[1].textContent=Math.round(times.elf*1000)+' ms · '+(times.elf<times.elfImpact?'Wind-up':times.elf<=times.elfImpact+.05?'Contact':'Recovery');
    v.card.querySelector('.source-name').textContent=source.sourceStates[0];v.card.querySelector('.elf-name').textContent=elf.label;
   }
   $('moveSelect').value=state.move;$('timingSelect').value=state.mode;$('speedSelect').value=String(state.speed).replace(/^0\./,'.');$('skeletonToggle').checked=state.skeleton;
   $('playToggle').textContent=state.playing?'Pause':'Play';$('scrubber').value=Math.round(state.progress*1000);$('progressLabel').value=Math.round(state.progress*100)+'%';
   $('goaSummary').textContent=source.sourceStates[0]+' · 2 original poses × 200 ms · 400 ms total';
   $('elfSummary').textContent=elf.label+' · '+Math.round(elf.duration*1000)+' ms total · contact '+Math.round(elf.events[0].time*1000)+' ms';
   $('contactFrame').title=state.mode==='contact'?'Jump to both contact poses':'Jump to the Elf contact time';
   $('timingNote').textContent=state.mode==='contact'?'Contact aligned: both attacks reach contact at the middle of the slider. Playback is retimed for pose comparison; GOA still uses its two untouched source poses.':'Original timing: both start together at their real durations. The shorter animation holds its last pose until the longer one finishes.';
  }
  function setMove(id){if(!IDS.includes(id))throw Error('Unknown comparison move: '+id);state.move=id;state.progress=0;render();}
  function setMode(mode){if(!['contact','native'].includes(mode))throw Error('Unknown timing mode: '+mode);state.mode=mode;state.progress=0;render();}
  function setProgress(progress){state.progress=clamp(Number(progress)||0,0,1);render();}
  function setPlaying(value){state.playing=Boolean(value);render();}
  function setSpeed(value){state.speed=[.25,.5,1].includes(Number(value))?Number(value):.5;render();}
  function step(seconds){if(state.playing){const delta=Math.max(0,Number(seconds)||0)*state.speed/getTimes().duration;state.progress=(state.progress+delta)%1;}render();return{...state};}
  function toProgress(time,length,impact){if(state.mode==='native')return time/getTimes().duration;return time<=impact?time/impact*.5:.5+(time-impact)/(length-impact)*.5;}
  function sampleProgresses(){const values=new Set([0,1]);for(const [engine,c]of [[goaAnimator,clips.goa[state.move]],[elfAnimator,clips.elf[state.move]]]){for(const t of engine.timeline(state.move).times)values.add(toProgress(t,c.duration,c.events[0].time));values.add(toProgress(c.duration,c.duration,c.events[0].time));}return[...values].sort((a,b)=>a-b);}
  function frameStep(sign){state.playing=false;const values=sampleProgresses(),eps=.00001;state.progress=sign>0?(values.find(p=>p>state.progress+eps)??1):([...values].reverse().find(p=>p<state.progress-eps)??0);render();}
  function jump(phase){state.playing=false;if(phase==='start')state.progress=0;else if(phase==='contact')state.progress=state.mode==='contact'?.5:clips.elf[state.move].events[0].time/getTimes().duration;else state.progress=.85;render();}
  function renderPair(move,facing,progress,{mode=state.mode,scale=1,skeleton=false}={}){
   const a=document.createElement('canvas');a.width=256*scale;a.height=128*scale;const c=a.getContext('2d'),t=getTimes(move,progress,mode);c.scale(scale,scale);c.imageSmoothingEnabled=false;c.fillStyle='#17291e';c.fillRect(0,0,256,128);
   c.font='10px system-ui';c.textAlign='center';c.fillStyle='#e3be79';c.fillText('Original GOA',64,12);c.fillStyle='#a8e6cb';c.fillText('Our Elf',192,12);
   stage(c,goaAnimator,move,t.goa,facing,{x:0,y:16});stage(c,elfAnimator,move,t.elf,facing,{x:128,y:16,skeleton});
   c.strokeStyle='#45634c';c.beginPath();c.moveTo(128.5,16);c.lineTo(128.5,112);c.stroke();c.font='9px system-ui';c.fillStyle='#9ab7a1';c.fillText(Math.round(t.goa*1000)+' ms',64,124);c.fillText(Math.round(t.elf*1000)+' ms',192,124);return a;
  }
  function renderReviewCanvas(progress,{mode=state.mode,scale=1}={}){
   const a=document.createElement('canvas');a.width=1024*scale;a.height=680*scale;const c=a.getContext('2d');c.scale(scale,scale);c.imageSmoothingEnabled=false;c.fillStyle='#102018';c.fillRect(0,0,1024,680);c.fillStyle='#dae9d9';c.font='16px system-ui';c.fillText('Original GOA / Our Elf · '+(mode==='contact'?'contact-aligned comparison':'original timing'),16,24);
   ['South','North','East','West'].forEach((name,i)=>{c.fillStyle='#a3c0a9';c.font='12px system-ui';c.fillText(name,i*256+14,48);});
   IDS.forEach((id,row)=>{const y=56+row*156;c.fillStyle='#1b3023';c.fillRect(0,y,1024,26);c.fillStyle='#c5d9c8';c.font='11px system-ui';c.fillText(clips.goa[id].sourceStates[0]+' / '+clips.elf[id].label,14,y+16);for(let d=0;d<4;d++)c.drawImage(renderPair(id,DIRS[d],progress,{mode,scale:1}),d*256,y+26);});return a;
  }
  $('moveSelect').onchange=e=>setMove(e.target.value);$('timingSelect').onchange=e=>setMode(e.target.value);$('playToggle').onclick=()=>setPlaying(!state.playing);$('speedSelect').onchange=e=>setSpeed(e.target.value);$('skeletonToggle').onchange=e=>{state.skeleton=e.target.checked;render();};$('scrubber').oninput=e=>{state.playing=false;setProgress(Number(e.target.value)/1000);};$('prevFrame').onclick=()=>frameStep(-1);$('nextFrame').onclick=()=>frameStep(1);$('startFrame').onclick=()=>jump('start');$('contactFrame').onclick=()=>jump('contact');$('recoveryFrame').onclick=()=>jump('recovery');
  window.motionCompare={state,setMove,setMode,setProgress,setPlaying,setSpeed,step,render,getTimes,renderPair,renderReviewCanvas,elfAnimator,goaAnimator,elfImages,goaImages,clips,views,sampleProgresses};
  render();document.body.dataset.ready='true';let last=performance.now();requestAnimationFrame(function tick(now){const dt=Math.min(.1,(now-last)/1000);last=now;if(state.playing&&!document.hidden)step(dt);requestAnimationFrame(tick);});
 }catch(error){$('error').hidden=false;$('error').textContent='Could not open comparison: '+error.message;$('timingNote').textContent='Reference loading failed.';console.error(error);}
})();
