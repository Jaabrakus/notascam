/* Original GOA authored cells. Only integer nearest-neighbor enlargement is used.
 * The world prototype supplies movement/elevation and ki effects independently.
 */
(function(global){
'use strict';
const DIRS='SNEW',clamp=(n,a,b)=>Math.max(a,Math.min(b,n));
const SOURCE='Original GOA base_m1.dmi';
const CLIPS=[
 {id:'idle',label:'GOA idle',duration:.8,loop:true,events:[],description:'Original standing frame; no skeletal re-posing.',sourceStates:[''],adapted:false},
 {id:'walk',label:'GOA walk',duration:.8,loop:true,events:[],description:'Original four-frame walk at its authored DMI timing.',sourceStates:[''],adapted:false},
 {id:'dash',label:'GOA run / dash',duration:.4,loop:false,events:[],description:'Original Run frames; world burst movement is the prototype’s rule.',sourceStates:['Run'],adapted:true},
 {id:'punch',label:'GOA punch A1',duration:.4,loop:false,events:[{time:.2,type:'hit',damage:8,range:70}],description:'PunchA-1: original preparation and strike, 200ms each.',sourceStates:['PunchA-1'],adapted:false},
 {id:'punch2',label:'GOA punch A2',duration:.4,loop:false,events:[{time:.2,type:'hit',damage:8,range:70}],description:'PunchA-2: the original alternate-arm punch, 200ms per frame.',sourceStates:['PunchA-2'],adapted:false},
 {id:'combo',label:'GOA four-hit chain',duration:1.6,loop:false,events:[{time:.2,type:'hit',damage:8,range:70},{time:.6,type:'hit',damage:8,range:70},{time:1,type:'hit',damage:13,range:100},{time:1.4,type:'hit',damage:13,range:100}],description:'Prototype chain of GOA PunchA-1, PunchA-2, KickA-1, KickA-2. GOA originally chooses among these attacks.',sourceStates:['PunchA-1','PunchA-2','KickA-1','KickA-2'],adapted:true},
 {id:'kick',label:'GOA kick A1',duration:.4,loop:false,events:[{time:.2,type:'hit',damage:13,range:100}],description:'KickA-1: original high straight kick and backward body lean.',sourceStates:['KickA-1'],adapted:false},
 {id:'kick2',label:'GOA kick A2',duration:.4,loop:false,events:[{time:.2,type:'hit',damage:13,range:100}],description:'KickA-2: original alternate-leg high kick.',sourceStates:['KickA-2'],adapted:false},
 {id:'charge',label:'Ki charge · GOA Chakra pose',duration:1,loop:true,events:[],description:'Original Chakra pose held while the world adds charge effects. Ki use is an adaptation.',sourceStates:['Chakra'],adapted:true},
 {id:'blast',label:'Ki blast · GOA throw poses',duration:.6,loop:false,events:[{time:.2,type:'projectile',damage:16}],description:'Original Throw1/Throw2 poses reused for a ki release; this timing and effect are new.',sourceStates:['Throw1','Throw2',''],adapted:true},
 {id:'beam',label:'Ki beam · GOA paired palms',duration:1.4,loop:false,events:[{time:.6,type:'beam',damage:35,duration:.5}],description:'Chakra to original Throw2 paired palms; beam timing/effect belongs to this prototype.',sourceStates:['Chakra','Throw2',''],adapted:true},
 {id:'hover',label:'World hover · GOA idle',duration:1.1,loop:true,events:[],description:'Original idle frame with separate world altitude. GOA has no dedicated hover state here.',sourceStates:[''],adapted:true},
 {id:'fly',label:'World flight · GOA run',duration:.4,loop:true,events:[],description:'Original Run cells with separate world altitude; placeholder until flight art is authored.',sourceStates:['Run'],adapted:true},
 {id:'hurt',label:'GOA hurt',duration:.4,loop:false,events:[],description:'Original hurt state held for this prototype’s hit reaction.',sourceStates:['hurt'],adapted:true},
 {id:'guard',label:'GOA guard / Seal',duration:.8,loop:true,events:[],description:'Original Seal pose, also used by GOA’s guard toggle.',sourceStates:['Seal'],adapted:false},
 {id:'fall',label:'GOA knockout',duration:.7,loop:false,events:[],description:'Original three-frame Knockout (200ms each), followed by Dead.',sourceStates:['Knockout','Dead'],adapted:false},
 {id:'recover',label:'Recovery · reversed GOA knockout',duration:.6,loop:false,events:[],description:'Reverse playback of original Knockout cells. Recovery sequence is a prototype adaptation.',sourceStates:['Knockout',''],adapted:true}
].map(c=>({...c,source:SOURCE,eventTiming:'Demo hit/release events; original DMI frame delays retained for attacks.'}));
// Effect sockets in ORIGINAL32px coordinates, measured against authored cells.
// These are approximate palms, not invented bones, and do not deform the image.
const IDLE=[[[10,20],[22,20]],[[21,20],[10,20]],[[13,20],[20,19]],[[11,19],[18,20]]];
const PAIRS={
 'Throw1':[[[10,16],[21,21]],[[22,16],[11,20]],[[25,14],[17,20]],[[6,14],[16,18]]],
 'Throw2':[[[12,18],[21,18]],[[21,18],[12,18]],[[24,17],[23,17]],[[8,17],[9,17]]],
 'Chakra':[[[14,18],[18,18]],[[18,18],[14,18]],[[20,17],[19,18]],[[11,17],[12,18]]],
 'Seal':[[[14,17],[18,17]],[[18,17],[14,17]],[[20,17],[19,17]],[[11,17],[12,17]]],
 'PunchA-1':[
  [[[8,13],[20,19]],[[23,13],[11,20]],[[12,14],[21,20]],[[19,14],[10,20]]],
  [[[12,16],[20,19]],[[20,16],[11,20]],[[25,14],[17,20]],[[6,14],[16,20]]]
 ],
 'PunchA-2':[
  [[[11,20],[22,13]],[[21,20],[9,13]],[[20,19],[15,15]],[[11,19],[16,15]]],
  [[[12,20],[20,16]],[[20,20],[12,16]],[[13,18],[27,14]],[[18,18],[4,14]]]
 ]
};
function socket(state,frame,view){let pair=PAIRS[state];if(state.startsWith('PunchA'))pair=pair?.[frame];pair=pair?.[view]||IDLE[view];return{right:{hand:pair[0].map(n=>n*2)},left:{hand:pair[1].map(n=>n*2)}};}
class GoaFrameAnimator{
 static clips=CLIPS;
 constructor(data,images){this.data=data;this.goa=data.goa;this.images=images;if(!this.goa?.states)throw Error('Original GOA sprite data is missing');this.image=images[this.goa.image];}
 timeline(id){
  const clip=CLIPS.find(c=>c.id===id)||CLIPS[0];
  const authored={punch:[200,200],punch2:[200,200],kick:[200,200],kick2:[200,200],
   walk:[200,200,200,200],dash:[100,100,100,100],fly:[100,100,100,100],
   combo:[200,200,200,200,200,200,200,200],fall:[200,200,200,100],
   recover:[200,200,200],blast:[200,280,120],beam:[600,550,250]};
  const durationsMs=(authored[clip.id]||[Math.round(clip.duration*1000)]).slice(),times=[];
  let elapsed=0;for(const duration of durationsMs){times.push(elapsed/1000);elapsed+=duration;}
  return{times,durationsMs};
 }
 select(action,t,complete){
  if(action==='punch')return['PunchA-1',t];if(action==='punch2')return['PunchA-2',t];
  if(action==='kick')return['KickA-1',t];if(action==='kick2')return['KickA-2',t];
  if(action==='combo'){const i=Math.min(3,Math.floor((t+1e-9)/.4));return[['PunchA-1','PunchA-2','KickA-1','KickA-2'][i],Math.min(.4,t-i*.4)];}
  if(action==='walk')return['',t];if(action==='dash'||action==='fly')return['Run',t];
  if(action==='charge')return['Chakra',0];if(action==='guard')return['Seal',0];
  if(action==='hurt')return['hurt',0];
  if(action==='blast')return t<.2?['Throw1',0]:t<.48?['Throw2',0]:['',0];
  if(action==='beam')return t<.6?['Chakra',0]:t<1.15?['Throw2',0]:['',0];
  if(action==='fall')return t<.6?['Knockout',t]:['Dead',0];
  if(action==='recover')return complete?['',0]:['Knockout',Math.max(0,.6-t-1e-9)];
  return['',0];
 }
 sample(action,time,facing='E'){
  const clip=CLIPS.find(c=>c.id===action)||CLIPS[0],raw=Number.isFinite(time)?Math.max(0,time):0;
  const complete=!clip.loop&&raw>=clip.duration,t=clip.loop?raw%clip.duration:Math.min(raw,clip.duration);
  const view=typeof facing==='number'?clamp(Math.floor(facing),0,3):Math.max(0,DIRS.indexOf(String(facing)[0]?.toUpperCase()));
  const [name,stateTime]=this.select(clip.id,t,complete),state=this.goa.states[name];if(!state)throw Error('Missing GOA state '+name);
  let frame=state.frames-1,remaining=stateTime*1000;
  for(let f=0;f<state.frames;f++){if(remaining<state.durationsMs[f]-1e-7){frame=f;break;}remaining-=state.durationsMs[f];}
  const index=state.offset+frame*state.dirs+Math.min(view,state.dirs-1),w=this.goa.frameSize;
  const rect=[(index%this.goa.columns)*w,Math.floor(index/this.goa.columns)*w,w,w];
  return{action:clip.id,time:t,duration:clip.duration,facing:DIRS[view],view,source:SOURCE,sourceState:name,sourceFrame:frame,sourceCell:index,sourceRect:rect,
   sourceFrameDurationMs:state.durationsMs[frame],sourceMovement:state.movement,arms:socket(name,frame,view),complete,events:clip.events,
   nativePixels:32,bodyPixels:64,root:[0,0],handSocketKind:'calibrated approximate original-frame anchors',adapted:clip.adapted};
 }
 render(ctx,action,time,facing='E',options={}){
  const state=this.sample(action,time,facing);if(!this.image)throw Error('Original GOA sprite image has not loaded');
  ctx.save();ctx.imageSmoothingEnabled=false;if(options.alpha!=null)ctx.globalAlpha*=options.alpha;
  ctx.drawImage(this.image,...state.sourceRect,0,0,64,64);
  if(options.debug){ctx.lineWidth=1;for(const [side,color]of [['right','#ffd36e'],['left','#ff91cb']]){const p=state.arms[side].hand;ctx.strokeStyle=color;ctx.beginPath();ctx.arc(p[0],p[1],2.5,0,Math.PI*2);ctx.stroke();}ctx.strokeStyle='#83dfe8';ctx.beginPath();ctx.moveTo(29,62.5);ctx.lineTo(35,62.5);ctx.stroke();}
  ctx.restore();return state;
 }
}
global.GoaFrameAnimator=GoaFrameAnimator;
})(typeof window==='undefined'?globalThis:window);
