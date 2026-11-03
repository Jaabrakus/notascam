/* Poses the approved Human rig's own parts into GOA's drawn frames (one still per frame and facing).
   A pose gives joint positions in the 64 px frame, read off GOA's frames doubled: off (body shift), chest (torso, head and
   shoulders shifted over the hips: the chest goes into a blow), lean (torso turn, radians), head (extra head turn), hip (pelvis turn); R/L arms {h: hand, e: elbow, hr: wrist roll, bend}; r/l legs
   {a: ankle, k: knee, fr: foot roll, bend}; s on a limb stretches its bones (a kick on these short legs), front: 'r' or 'l'
   draws that leg over the body. Only a hand or ankle: the bone lengths are kept (IK). Elbow or knee too:
   placed as given and the part is stretched to fit. A facing given as 'mirror' is the other side's pose mirrored onto this side's own parts (same hands); 'flip' flips the other side's still. */
const D='SNEW';
// East to West: each hand and leg stays the same one (GOA: the jab is always the right hand, the cross the left).
// A limb's joints are mirrored about its own shoulder or hip, since the two facings' parts sit in different places.
function mirrorSpec(s,from,to){const o={};if(s.off)o.off=[-s.off[0],s.off[1]];if(s.chest)o.chest=[-s.chest[0],s.chest[1]];for(const k of ['lean','head','hip'])if(s[k])o[k]=-s[k];if(s.front)o.front=s.front;
 for(const [K,limb,side] of [['R','arms','right'],['L','arms','left'],['r','legs','right'],['l','legs','left']])if(s[K]){const j=s[K],a=from[limb][side][0],b=to[limb][side][0],m=p=>[b[0]-(p[0]-a[0]),b[1]+(p[1]-a[1])],n={};
  for(const k of ['h','e','a','k'])if(j[k])n[k]=m(j[k]);for(const k of ['hr','fr'])if(j[k])n[k]=-j[k];if(j.bend!=null)n.bend=-j.bend;if(j.s)n.s=j.s;o[K]=n;}return o;}
class PoseAnimator extends ElfAnimator{
 sample(id,time,d,eq){const clip=this.data.clips[id];return clip&&clip.pose?this.samplePose(clip,d):super.sample(id,time,d,eq);}
 samplePose(clip,d){
  const view=this.data.views[d],P=clip.pose,off=P.off||[0,0],lean=P.lean||0,ch=P.chest||[0,0],tp=p=>V.add(turn(p,view.waist,lean,off),ch),waist=V.add(view.waist,off),chest=V.add(waist,ch),neck=tp(view.neck);
  const result={bodyDirection:d,parts:{},arms:{},legs:{},root:[0,0],waist,neck,angle:lean,fall:0,squash:1,hidden:[],clip:clip.id,requestedClip:clip.id,time:0,d,equipment:clip.equipment,sourceFrame:0,drawnBody:false,weaponAngle:0};if(P.hide)result.hidden=P.hide;result.belt=P.belt??!!(lean||P.chest);
  const rigid=(name,sr,st,r,t)=>{const ps=view.partSource?.[name],srcRoot=ps?ps[0]:sr,srcTip=ps?ps[1]:st;
   result.parts[name]={srcRoot,srcTip,root:r,tip:t,foreshortened:ps?.[2]==='fit'||Math.abs(V.len(V.sub(t,r))-V.len(V.sub(srcTip,srcRoot)))>.75};};
  rigid('pelvis',view.waist,V.add(view.waist,[0,1]),waist,turn(V.add(view.waist,[0,1]),view.waist,P.hip||0,off));
  rigid('torso',view.waist,view.neck,chest,neck);
  rigid('head',view.neck,V.add(view.neck,[0,-10]),neck,turn(V.add(view.neck,[0,-10]),view.neck,lean*.3+(P.head||0),V.sub(neck,view.neck)));
  for(const [name,[h,k,a]] of Object.entries(view.legs)){const S=P[name==='right'?'r':'l']||{},A=V.len(V.sub(k,h))*(S.s||1),B=V.len(V.sub(a,k))*(S.s||1),hip=V.add(h,off),bend=S.bend??(d===2?-1:d===3?1:hip[0]<32?1:-1);
   const [knee,ankle]=S.k&&S.a?[S.k,S.a]:ik(hip,S.a||a,A,B,bend);
   rigid(name+'Thigh',h,k,hip,knee);rigid(name+'Shin',k,a,knee,ankle);rigid(name+'Foot',a,V.add(a,[0,1]),ankle,turn(V.add(a,[0,1]),a,S.fr||0,V.sub(ankle,a)));
   result.legs[name]={hip,knee,ankle,target:ankle,upperLength:A,lowerLength:B};}
  for(const [name,sd] of [['right','R'],['left','L']]){const [s,e,h]=view.arms[name],S=P[sd]||{},A=V.len(V.sub(e,s))*(S.s||1),B=V.len(V.sub(h,e))*(S.s||1),shoulder=tp(s),bend=S.bend??(d===2?1:d===3?-1:s[0]<32?1:-1);
   const [elbow,hand]=S.e&&S.h?[S.e,S.h]:S.h?ik(shoulder,S.h,A,B,bend):[tp(e),tp(h)];
   rigid(name+'UpperArm',s,e,shoulder,elbow);rigid(name+'Forearm',e,h,elbow,hand);
   const roll=Math.atan2(hand[1]-elbow[1],hand[0]-elbow[0])-Math.atan2(h[1]-e[1],h[0]-e[0])+(S.hr||0);
   rigid(name+'Hand',h,V.add(h,[0,1]),hand,turn(V.add(h,[0,1]),h,roll,V.sub(hand,h)));
   result.arms[name]={shoulder,elbow,hand,upperLength:A,lowerLength:B};}
  return result;}
 // A tilted or shifted torso shows its cut bottom over the shorts: draw the shorts again over it (belt: false keeps
 // the rig's order).
 part(ctx,name,p){super.part(ctx,name,p);if(name==='torso'&&p.belt)super.part(ctx,'pelvis',p);}
 render(ctx,id,time,d,options={}){const p=super.render(ctx,id,time,d,options),side=this.data.clips[id]?.pose?.front;
  if(side){const leg=side==='r'?'right':'left';ctx.save();ctx.imageSmoothingEnabled=false;ctx.translate(64,64);for(const s of ['Thigh','Shin','Foot'])this.part(ctx,leg+s,p);ctx.restore();}return p;}
}
const q=new URLSearchParams(location.search),images={},refs={},scratch=document.createElement('canvas');scratch.width=scratch.height=192;let animator;
function load(url){const im=new Image();im.src=url;return im.decode().then(()=>im);}
function still(state,f,d){const spec=POSES[state][f][D[d]];if(spec==null)return null;const c=document.createElement('canvas');c.width=c.height=64;const x=c.getContext('2d');
 if(spec==='flip'){const m=still(state,f,d===2?3:d===3?2:d);if(!m)return null;x.translate(64,0);x.scale(-1,1);x.drawImage(m,0,0);return c;}
 const id=state+'-'+D[d]+f;DATA.clips[id]={id,label:id,category:'GOA',pose:spec==='mirror'?mirrorSpec(POSES[state][f][D[d===3?2:d===2?3:d]],DATA.views[d===3?2:d===2?3:d],DATA.views[d]):spec,equipment:{weapon:'none',shield:false},duration:1,keys:[[0]],events:{},definition:{bare:true}};
 animator.render(scratch.getContext('2d'),id,0,d,{debug:q.has('debug')});x.drawImage(scratch,64,64,64,64,0,0,64,64);return c;}
function cell(z,draw,grid){const c=document.createElement('canvas');c.width=c.height=64*z;const x=c.getContext('2d');x.imageSmoothingEnabled=false;x.fillStyle='#464a54';x.fillRect(0,0,c.width,c.height);draw(x);
 if(grid){for(let k=0;k<=64;k+=4){x.fillStyle=k%16?'rgba(255,255,255,.10)':'rgba(255,230,120,.35)';x.fillRect(k*z,0,1,c.height);x.fillRect(0,k*z,c.width,1);}x.fillStyle='#ffe678';x.font='10px system-ui';for(let k=8;k<64;k+=8){x.fillText(k,k*z+1,10);x.fillText(k,1,k*z+10);}}return c;}
async function init(){
 await Promise.all(Object.entries(DATA.images).map(async([id,url])=>{images[id]=await load(url);}));animator=new PoseAnimator(DATA,images);
 const states=(q.get('states')||Object.keys(POSES).join(',')).split(','),dirs=(q.get('dirs')||'SNEW').split(''),z=+(q.get('zoom')||4);
 for(const s of states)for(let f=0;f<POSES[s].length;f++)for(const d of 'SNEW'){try{refs[s+'-'+d+f]=await load('ref/'+((typeof REFNAME!=='undefined'&&REFNAME[s])||s)+'-'+d+f+'.png');}catch(e){}}
 const rows=[];for(const s of states)for(let f=0;f<POSES[s].length;f++)rows.push([s,f]);
 const W=dirs.length*3*(64*z+6),H=rows.length*(64*z+18),sheet=document.createElement('canvas');sheet.width=W;sheet.height=H;const sx=sheet.getContext('2d');sx.fillStyle='#1e2026';sx.fillRect(0,0,W,H);sx.imageSmoothingEnabled=false;
 rows.forEach(([s,f],r)=>dirs.forEach((dn,j)=>{const d=D.indexOf(dn),ref=refs[s+'-'+dn+f],me=still(s,f,d),y=r*(64*z+18)+16,x0=j*3*(64*z+6);
  sx.fillStyle='#ddd';sx.font='12px system-ui';sx.fillText(s+' '+dn+f+'   GOA | Human 64 | overlay',x0,y-4);
  const cells=[cell(z,x=>{if(ref)x.drawImage(ref,0,0,64*z,64*z);},true),cell(z,x=>{if(me)x.drawImage(me,0,0,64*z,64*z);},true),cell(z,x=>{if(ref){x.globalAlpha=.45;x.drawImage(ref,0,0,64*z,64*z);}x.globalAlpha=.75;if(me)x.drawImage(me,0,0,64*z,64*z);},true)];
  cells.forEach((c,k)=>sx.drawImage(c,x0+k*(64*z+6),y));
  if(q.has('export')&&me&&j===dirs.indexOf(dn))fetch('/save/'+s+'-'+dn+f+'.png',{method:'POST',body:me.toDataURL('image/png')});}));
 document.getElementById('out').append(sheet);
 if(q.get('save'))await fetch('/save/'+q.get('save')+'.png',{method:'POST',body:sheet.toDataURL('image/png')});
 document.body.dataset.ready='1';document.getElementById('status').textContent='ready '+rows.length+' rows';}
init().catch(e=>{document.getElementById('status').textContent='error '+e;console.error(e);});
