// ===== The job board and work zones (Jobs.dm) =====
// The Work tab's board: every zone and job row with workers wanted, priority, stop at and pause; villagers on Any work
// take the work by themselves. Zones are painted with the build drag ("Piece:jz_<kind>") and outlined on the ground in 3D.
const JB_KIND={wood:['Wood','#6fbf5a',[0.44,0.75,0.35,1]],stone:['Stone','#a8a8a0',[0.7,0.7,0.66,1]],farm:['Farm','#e0bb55',[0.88,0.73,0.33,1]],stock:['Stockpile','#c9a36b',[0.79,0.64,0.42,1]],builders:['Builders','',null],haulers:['Haulers','',null]};
const JB_SIDE={farm:21};
function jbModel(){try{return model}catch(e){return null}}
function jbMode(){const b=V3.build;const md=b&&String(b.mode||'');return md&&md.startsWith('Piece:jz_')?md.slice(9):''}
// A job's one line, always shown: name, a small bar of workers, what's happening, and what it gathered in the last
// minute. A click opens its controls under it (remembered); a job that needs the player says so in amber.
function jbLineText(r){if(r.paused)return ['Paused',''];if(r.problem)return [jbProb(r),'warn'];return [jbDoing(r)||r.status||'','']}
function jbRowLine(r){const id=esc(r.id),K=JB_KIND[r.kind]||[r.kind,'#999'],open=JBG.open.has(String(r.id)),[st,cls]=jbLineText(r);
 const want=+r.want||0,cnt=+r.count||0,pct=want?Math.min(100,Math.round(cnt/want*100)):0,rate=+r.rate||0,stock=r.kind==='stock';
 return '<div class="jbline" role="button" tabindex="0" data-jbtoggle="'+id+'" aria-expanded="'+open+'" title="'+esc(r.name+(st?'\n'+st:'')+'\nClick: '+(open?'close':'open')+' its controls.')+'">'+
  '<i class="jbchev"></i><b class="jbn">'+esc(r.name)+'</b>'+
  (stock?'<span class="jbst">Store · '+esc(Array.isArray(r.size)?r.size.join('×'):r.size||'')+'</span>':
   '<span class="jbmini" aria-hidden="true"><span style="width:'+pct+'%"></span></span><span class="jbct">'+cnt+'/'+want+'</span><span class="jbst'+(cls?' '+cls:'')+'">'+esc(st)+'</span>'+
   ((r.kind==='wood'||r.kind==='stone'||r.kind==='gather'||rate)?'<span class="jbrt'+(rate?'':' zero')+'" title="Gathered in the last minute">+'+rate+'/min</span>':''))+'</div>'}
// Opened: what it holds, its controls, and the workers' line.
function jbRowHead(r){const id=esc(r.id),K=JB_KIND[r.kind]||[r.kind,'#999'];let tags='';
 if(r.zone)tags+='<span class="tag"><i class="jbsw" style="background:'+K[1]+'"></i>'+esc(K[0])+' · '+esc(Array.isArray(r.size)?r.size.join('×'):r.size)+'</span>';
 if(r.left>=0&&(r.kind==='wood'||r.kind==='stone'||r.kind==='gather')){const rest=+r.resting||0;   // resting: saplings growing on the stumps (the zone's own regrowing; Yield.dm)
  tags+=rest?'<span class="tag" title="Growing\nSaplings planted on the stumps: the job works them again once they have grown.">'+esc(r.left)+' ready · '+esc(rest)+' growing</span>':'<span class="tag">'+esc(r.left)+' '+(r.kind==='wood'?(r.left===1?'tree':'trees'):r.kind==='gather'?(r.left===1?'tree or rock face':'trees and rock faces'):(r.left===1?'rock face':'rock faces'))+' to work</span>'}
 if(r.kind==='fish'&&r.left>=0)tags+='<span class="tag" title="Fishing spots\nOne fisher a spot, fished from the shore tile beside it. The spots drift along the shore every few minutes; the zone follows them while they stay inside it.">'+esc(r.left)+' fishing spot'+(+r.left===1?'':'s')+' · one fisher each</span>';
 if(+r.far)tags+='<span class="tag" title="Out of reach\nNo way to them from outside the zone (walled in, or across water), so nobody is sent to them. Open a way and the zone takes them up.">'+esc(r.far)+' out of reach</span>';
 let act='';
 if(r.kind!=='stock')act+='<select data-jbprio="'+id+'" aria-label="Priority for '+esc(r.name)+'" title="Priority\nHigh jobs get free villagers first, then Normal, then Low.">'+[['1','High'],['2','Normal'],['3','Low']].map(([v,l])=>'<option value="'+v+'"'+(String(r.prio)===v?' selected':'')+'>'+l+'</option>').join('')+'</select>'+
  '<button data-jb="'+id+'|pause" aria-pressed="'+!!r.paused+'" title="'+(r.paused?'Resume\nIt takes workers again.':'Pause\nIts workers go back to the free villagers.')+'">'+(r.paused?'Resume':'Pause')+'</button>'+
  '<button data-jb="'+id+'|select"'+(+r.count?'':' disabled')+' title="Select its workers\nCtrl+G then makes them a group.">Select</button>';
 if(r.zone)act+='<button data-jb="'+id+'|look" title="Go to\nCentre the camera on this zone.">Go to</button><button data-jbrename="'+id+'" title="Rename\nGive the zone its own name.">Rename</button><button data-jb="'+id+'|remove" title="Remove\nClick twice: the zone goes and its workers are free again.">Remove</button>';
 return (tags?'<div class="jbtags">'+tags+'</div>':'')+'<div class="oact jbact">'+act+'</div>'}
function jbRowBody(r){const id=esc(r.id);
 if(r.kind==='stock')return '<p class="omsg">A store for anything. Set what it takes under Stockpile zones.</p>';
 const want=+r.want||0,cnt=+r.count||0,fish=r.kind==='fish'&&r.left>=0,cap=fish?Math.min(+r.cap||0,+r.left):+r.cap||0;   // a fishing zone: one fisher a spot (Jobs.dm RM_JZ_FISH_PER_SPOT), not one a 4 tiles
 let h='<div class="jbw"><span>Workers <b>'+cnt+'</b> of <b><span class="jbwant" role="button" tabindex="0" data-jbwant="'+id+'" data-max="'+esc(r.cap||100000)+'" title="Workers wanted\nClick to type a number.">'+want+'</span></b> wanted</span><button data-jb="'+id+'|want|-1" aria-label="Fewer workers" title="Fewer workers\nShift-click: 10 fewer.">−</button><button data-jb="'+id+'|want|1" aria-label="More workers" title="More workers\nShift-click: 10 more.">+</button>'+
  (cap?'<button data-jb="'+id+'|want|='+esc(cap)+'" title="Fill it\nAs many as the zone has room for: '+(fish?'one fisher a fishing spot.':'one worker for every 4 tiles.')+'">Fill</button><span class="jbnow">room for '+esc(cap)+'</span>':'')+'</div>';
 if(r.good)h+='<div class="jbw"><span>Stop at <b>'+(r.stop?esc(r.stop)+' '+esc(r.good):'never')+'</b></span><button data-jb="'+id+'|stop|-10" aria-label="Stop sooner" title="Stop sooner\nThe job stands down when the stores hold this much. Shift-click: 100.">−</button><button data-jb="'+id+'|stop|10" aria-label="Stop later" title="Stop later\nShift-click: 100.">+</button><span class="jbnow">'+esc(r.stock)+' in the stores</span></div>';
 return h+(r.problem?'<p class="omsg jbprob">'+esc(jbProb(r))+'</p>':'<p class="omsg">'+esc(jbDoing(r)||r.status||'')+'</p>')}
// What a job needs from the player (Jobs.dm RmJzProblemOf), said with the fix.
const JB_PROB={1:()=>'No drop-off on this level: set a stockpile or a cart stop there',2:r=>'The drop-off doesn’t take '+(r.good||'this')+': change the stockpile’s filter',3:()=>'Its workers are on another level',4:()=>'No stockpile yet: haulers need one (Work › Stockpile)',5:()=>'Short of workers and nobody is free: give the job board more villagers, or lower another job’s workers'};
function jbProb(r){const f=JB_PROB[r.problem];return f?f(r):''}
// What a wood or stone job's workers are doing (Jobs.dm RmJzDoing: working, carrying in, eating or resting, waiting;
// counted from 60 of them at most, and then marked as about).
function jbDoing(r){const d=r.doing;if(!Array.isArray(d)||!r.count)return '';const w=[r.kind==='stone'?'mining':r.kind==='gather'?'gathering':'chopping','carrying in','eating or resting','waiting'];
 const parts=w.map((l,i)=>d[i]?d[i]+' '+l:'').filter(Boolean);return parts.length?(d[4]?'≈ ':'')+parts.join(' · '):''}
// One node per job: its line always; its controls only while open (and not redrawn under a field being typed in).
function jbSync(box,rows,R){R=R||JB_R;const ids=rows.map(r=>String(r.id));[...box.children].forEach(c=>{if(!ids.includes(c.dataset.id))c.remove()});
 rows.forEach((r,i)=>{let c=[...box.children].find(x=>x.dataset.id===String(r.id));if(!c){c=document.createElement('div');c.dataset.id=String(r.id);c.innerHTML='<div class="jl"></div><div class="jbdet"><div class="oh"></div><div class="ob"></div></div>'}
  if(box.children[i]!==c)box.insertBefore(c,box.children[i]||null);const open=JBG.open.has(String(r.id)),cls='ocard jbrow'+(open?' open':'')+(r.prio===1?' p1':r.prio===3?' p3':'')+(r.paused?' jbpaused':'')+(r.problem?' jbneed':'');if(c.className!==cls)c.className=cls;
  const ae=document.activeElement,typing=ae&&/^(INPUT|SELECT)$/.test(ae.tagName)?ae:null,L=c.firstChild,D=c.lastChild,l=R.line(r);
  if(L.dataset.l!==l&&!(typing&&L.contains(typing))){L.dataset.l=l;L.innerHTML=l}
  if(!open)return;const h=R.head(r),b=R.body(r);
  if(D.firstChild.dataset.h!==h&&!(typing&&D.firstChild.contains(typing))){D.firstChild.dataset.h=h;D.firstChild.innerHTML=h}if(D.lastChild.dataset.b!==b&&!(typing&&D.lastChild.contains(typing))){D.lastChild.dataset.b=b;D.lastChild.innerHTML=b}})}
const JB_R={line:r=>r.kind==='make'?chMakeLine(r):jbRowLine(r),head:r=>r.kind==='make'?chMakeHead(r):jbRowHead(r),body:r=>r.kind==='make'?chMakeBody(r):jbRowBody(r)};
function jbToggle(id){id=String(id);if(JBG.open.has(id))JBG.open.delete(id);else JBG.open.add(id);try{localStorage.setItem('rm-jbopen',JSON.stringify([...JBG.open]))}catch(_){}const b=$('jobBoard');if(b)b.dataset.k='';jbRender()}
// What the stores gain or lose a minute (Jobs.dm RmJzStoreRates), and who is working: the board's first line.
function jbOutLine(J){const o=Array.isArray(J.out)?J.out:null,f=v=>(v>0?'+'+v:v<0?'−'+(-v):'0'),c=v=>v<0?' class="neg"':'';
 const goods=o?[['Wood',o[0]],['Stone',o[1]],['Food',o[2]]].map(([l,v])=>'<span>'+l+' <b'+c(v)+'>'+f(v)+'</b></span>').join(''):'<span class="jbmeas">measuring…</span>';
 return '<span class="jbol" title="Stores a minute\nWhat the stores gained or lost over the last minute: gathered, made and brought in, less what was eaten, built with or used.">Stores a minute</span>'+goods+'<span class="jbwk">Working <b>'+(+J.working||0)+'</b> · free <b>'+(+J.free||0)+'</b></span>'}
// The first time: three steps, each ticked off from what the realm has done; "Got it" puts it away for good.
function jbGuide(J,rows){if(JBG.guideOff)return '';const zones=rows.filter(r=>r.zone&&r.kind!=='stock'),s1=zones.length>0,s2=(+J.working||0)+(+J.free||0)>0,s3=rows.some(r=>(+r.rate||0)>0);
 const step=(ok,t)=>'<li class="'+(ok?'done':'')+'"><span class="jbtick">'+(ok?'✓':'○')+'</span> '+t+'</li>';
 return '<div class="jbg-h"><b>'+(s1&&s2&&s3?'All set: the board runs itself now':'Getting started')+'</b><button type="button" data-jbguide="off" title="Hide this for good">Got it</button></div><ol>'+
  step(s1,'Paint a zone: <b>+ Wood</b>, then drag round some trees.')+step(s2,'Give villagers to the job board: <b>Idle → job board</b>.')+step(s3,'Watch the wood come in: the zone’s line shows <b>+N/min</b>.')+'</ol>'}
function jbRender(){const m=jbModel(),box=$('jobBoard');if(!box||!m||currentTab!=='work')return;const J=m.jobs;if(!J||!J.rows)return;
 if(!box.dataset.wired){box.dataset.wired='1';
  box.innerHTML='<div class="jbguide" hidden></div><div class="jbout"></div><div class="jbadd">'+[['wood','+ Wood','Wood zone\nDrag a rectangle round trees, up to 25 tiles a side. Villagers on the job board fell them and carry the logs in.'],['stone','+ Stone','Stone zone\nDrag a rectangle over rock, up to 25 tiles a side. Villagers on the job board mine the faces they can reach.'],['farm','+ Farm','Farm\nDrag a field, up to 21 tiles a side. Villagers on the job board till, plant and pick it.'],['fish','+ Fish','Fishing zone\nDrag a stretch of shore with fishing spots, up to 25 tiles a side. Villagers on the job board fish the spots, clean the catch and bring the fish in.'],['stock','+ Store','Stockpile zone\nDrag a store. Haulers and gatherers bring goods to it.']].map(([k,l,t])=>'<button type="button" data-jbzone="'+k+'" title="'+esc(t)+'">'+l+'</button>').join('')+'</div>'+
   '<p class="jbfree"></p><div class="jbstaff"></div><div class="jbneeds" hidden></div><div class="jbrows">'+['wood','stone','gather','farm','fish','stock'].map(k=>'<div class="jbgrp" data-kind="'+k+'" hidden><button type="button" class="jbgh" data-jbfold="'+k+'" aria-expanded="true"></button><div class="jbgrows"></div></div>').join('')+'</div><p class="jbempty" hidden>No zones yet. Paint one with + Wood, + Stone or + Farm: villagers on the job board take the work up by themselves.</p><div class="jbfixed"></div>';
  chWire(box);
  box.addEventListener('click',e=>{const z=e.target.closest('[data-jbzone]');if(z){send('jobzone',z.dataset.jbzone);document.body.classList.remove('panel-open');queueRegions();return}
   const gd=e.target.closest('[data-jbguide]');if(gd){JBG.guideOff=true;try{localStorage.setItem('rm-jbguide','off')}catch(_){}box.dataset.k='';jbRender();return}
   const tg=e.target.closest('[data-jbtoggle]');if(tg&&!e.target.closest('input')){jbToggle(tg.dataset.jbtoggle);return}
   const rn=e.target.closest('[data-jbrename]');if(rn){const c=rn.closest('.jbrow'),n=c&&c.querySelector('.jbn');if(n)jbRename(n,rn.dataset.jbrename);return}
   const a=e.target.closest('button[data-jbany]');if(a){if(!a.disabled)send('jobany',a.dataset.jbany);return}
   const b=e.target.closest('button[data-jb]');if(!b||b.disabled)return;const p=b.dataset.jb.split('|');if(p.length===3&&/^-?\d+$/.test(p[2])&&e.shiftKey)p[2]=String(+p[2]*10);
   if(p[1]==='remove'&&!b.dataset.armed){const t0=b.textContent;b.dataset.armed='1';b.textContent=b.dataset.arm||'Remove?';b.classList.add('jbarm');setTimeout(()=>{if(b.isConnected&&b.dataset.armed){delete b.dataset.armed;b.textContent=t0;b.classList.remove('jbarm')}},3000);return}   // a slip of the mouse can't lose a zone
   send('jobrow',p.join('|'))});
  box.addEventListener('keydown',e=>{const tg=e.target.closest&&e.target.closest('[data-jbtoggle]');if(tg&&e.target===tg&&(e.key==='Enter'||e.key===' ')){e.preventDefault();jbToggle(tg.dataset.jbtoggle)}});
  box.addEventListener('change',e=>{const s=e.target.closest('select[data-jbprio]');if(s)send('jobrow',s.dataset.jbprio+'|prio|'+s.value)});
  // the workers wanted: click the number, type, Enter (or click away) sets it, Esc doesn't (big jobs past Shift-click)
  const wantEdit=n=>{const inp=document.createElement('input');inp.type='number';inp.min='0';inp.max=n.dataset.max;inp.value=n.textContent;inp.className='jbwantin';inp.setAttribute('aria-label','Workers wanted');
   let over=false;const done=keep=>{if(over)return;over=true;const v=Math.round(+inp.value);if(keep&&inp.value!==''&&isFinite(v)&&String(Math.max(0,Math.min(+n.dataset.max,v)))!==n.textContent){const w=Math.max(0,Math.min(+n.dataset.max,v));n.textContent=String(w);send('jobrow',n.dataset.jbwant+'|want|='+w)}if(inp.isConnected)inp.replaceWith(n)};
   inp.addEventListener('keydown',ev=>{if(ev.key==='Enter'){ev.preventDefault();done(true)}else if(ev.key==='Escape'){ev.preventDefault();ev.stopPropagation();done(false)}});inp.addEventListener('blur',()=>done(true));
   n.replaceWith(inp);inp.focus();inp.select()};
  box.addEventListener('click',e=>{const n=e.target.closest('[data-jbwant]');if(n)wantEdit(n)});
  box.addEventListener('click',e=>{const g=e.target.closest('[data-jbgo]');if(g)jbOpenRow(g.dataset.jbgo)});
  box.addEventListener('click',e=>{const f=e.target.closest('[data-jbfold]');if(!f)return;const k=f.dataset.jbfold;JBG.fold[k]=!JBG.fold[k];try{localStorage.setItem('rm-jbfold',JSON.stringify(JBG.fold))}catch(_){}box.dataset.k='';jbRender()});
  box.addEventListener('keydown',e=>{const n=e.target.closest&&e.target.closest('[data-jbwant]');if(n&&(e.key==='Enter'||e.key===' ')){e.preventDefault();wantEdit(n)}});
  box.addEventListener('mouseover',e=>{const c=e.target.closest('.jbgrows .jbrow');JBG.hot=c?c.dataset.id:null});box.addEventListener('mouseleave',()=>{JBG.hot=null})}
 const sel=+m.selection||0,idle=+m.idle||0,rows=arr(J.rows),key=JSON.stringify([rows,J.free,J.working,J.out,sel,idle,JBG.guideOff,J.pace,m.chain,JBG.tab]);if(box.dataset.k===key){jbFocusRow();return}box.dataset.k=key;
 const zones=rows.filter(r=>r.zone),fixed=rows.filter(r=>!r.zone&&r.kind!=='make'),free=+J.free||0;
 {const g=box.querySelector('.jbguide'),t=jbGuide(J,rows);g.hidden=!t;if(g.dataset.t!==t){g.dataset.t=t;g.innerHTML=t}}
 {const o=box.querySelector('.jbout'),t=jbOutLine(J);if(o.dataset.t!==t){o.dataset.t=t;o.innerHTML=t}}
 const short=rows.some(r=>r.kind!=='stock'&&(+r.now||0)>(+r.count||0));
 box.querySelector('.jbfree').innerHTML=free?'<b>'+free+'</b> villager'+(free===1?'':'s')+' on the job board '+(free===1?'is':'are')+' free, waiting for a job'+(short?'':' · no job wants more: raise one with + or paint a zone'):'Nobody on the job board is free · give it villagers and it staffs the jobs itself';
 {const pace=+J.pace||1;if(pace>1)box.querySelector('.jbfree').innerHTML+='<br><span class="jbpace">Big village: a villager can take up to '+(pace/2)+' s to start a new job.</span>'}
 box.querySelector('.jbstaff').innerHTML='<button type="button" data-jbany="selected"'+(sel?'':' disabled')+' title="Selected → job board\nGives the selected units to the job board: it finds them work.">Selected → job board'+(sel?' ('+sel+')':'')+'</button>'+
  '<button type="button" data-jbany="idle"'+(idle?'':' disabled')+' title="Idle → job board\nGives idle villagers on Manual to the job board. Units kept in a control group (Ctrl+G) stay as they are.">Idle → job board'+(idle?' ('+idle+')':'')+'</button>';
 // the jobs that need the player, at the top: each a click from its line (it opens, and its kind unfolds)
 {const nb=box.querySelector('.jbneeds'),need=rows.filter(r=>r.problem&&r.kind!=='make');nb.hidden=!need.length;
  const t=need.length?'<span class="jbnl">Needs you</span>'+need.slice(0,4).map(r=>'<button type="button" data-jbgo="'+esc(r.id)+'" title="'+esc(r.name+'\n'+jbProb(r))+'"><b>'+esc(r.name)+'</b> · '+esc(jbProb(r))+'</button>').join('')+(need.length>4?'<span class="jbnmore">and '+(need.length-4)+' more below</span>':''):'';
  if(nb.dataset.t!==t){nb.dataset.t=t;nb.innerHTML=t}}
 // zones by kind, each kind under a header that folds (for a realm with dozens of zones): count, workers, output
 for(const k of ['wood','stone','gather','farm','fish','stock']){const g=box.querySelector('.jbgrp[data-kind="'+k+'"]'),L=zones.filter(r=>r.kind===k);g.hidden=!L.length;if(!L.length){jbSync(g.lastChild,[]);continue}
  const K=JB_KIND[k],fold=!!JBG.fold[k],cnt=L.reduce((a,r)=>a+(+r.count||0),0),want=L.reduce((a,r)=>a+(+r.want||0),0),rest=L.reduce((a,r)=>a+(+r.resting||0),0),rate=L.reduce((a,r)=>a+(+r.rate||0),0),h=g.firstChild;
  const t='<i class="jbchev"></i><i class="jbsw" style="background:'+K[1]+'"></i><b>'+esc(K[0])+'</b> · '+L.length+' zone'+(L.length===1?'':'s')+(k==='stock'?'':' · '+cnt+'/'+want+' workers')+(rest?' · '+rest+' growing':'')+(rate?'<span class="jbrt">+'+rate+'/min</span>':'');
  if(h.dataset.t!==t){h.dataset.t=t;h.innerHTML=t}h.setAttribute('aria-expanded',String(!fold));g.classList.toggle('folded',fold);if(fold)jbSync(g.lastChild,[]);else jbSync(g.lastChild,L)}
 box.querySelector('.jbempty').hidden=zones.length>0;jbSync(box.querySelector('.jbfixed'),fixed);chRender(box,m,rows);jbFocusRow()}
// A zone's name, from its Rename button: type, Enter (or click away) keeps it, Esc doesn't.
function jbRename(n,id){const inp=document.createElement('input');inp.type='text';inp.maxLength=24;inp.value=n.textContent;inp.className='jbnamein';inp.setAttribute('aria-label','Zone name');
 let over=false;const done=keep=>{if(over)return;over=true;const v=inp.value.replace(/[|\[\]<>"]/g,'').trim();if(keep&&v&&v!==n.textContent){n.textContent=v;send('jobrow',id+'|name|'+v)}if(inp.isConnected)inp.replaceWith(n)};
 inp.addEventListener('keydown',ev=>{ev.stopPropagation();if(ev.key==='Enter'){ev.preventDefault();done(true)}else if(ev.key==='Escape'){ev.preventDefault();done(false)}});inp.addEventListener('blur',()=>done(true));inp.addEventListener('click',ev=>ev.stopPropagation());
 n.replaceWith(inp);inp.focus();inp.select()}
// A zone's plate in 3D opens the Work tab at its row (once the tab's rows are drawn: up to 4 s).
function jbOpenRow(id){JBG.open.add(String(id));{const t=/^o/.test(String(id))?'make':'gather';if(JBG.tab!==t){JBG.tab=t;try{localStorage.setItem('rm-chtab',t)}catch(_){}const b=$('jobBoard');if(b)b.dataset.k=''}}try{localStorage.setItem('rm-jbopen',JSON.stringify([...JBG.open]))}catch(_){}{const m=jbModel(),z=m&&m.jobs&&arr(m.jobs.zones).find(z=>String(z[9])===String(id));if(z&&JBG.fold[z[5]]){JBG.fold[z[5]]=false;const b=$('jobBoard');if(b)b.dataset.k=''}}send('tab','work');if(overlayHost){document.body.classList.add('panel-open');queueRegions()}JBG.focus=String(id);JBG.focusAt=performance.now();jbFocusRow()}
function jbFocusRow(){const id=JBG.focus;if(!id)return;if(performance.now()-JBG.focusAt>4000){JBG.focus=null;return}const pg=$('page-work'),c=document.querySelector('#jobBoard .jbrow[data-id="'+CSS.escape(id)+'"]');if(!c||!pg||pg.hidden)return;
 JBG.focus=null;c.scrollIntoView({block:'center'});c.classList.add('jbflash');setTimeout(()=>c.classList.remove('jbflash'),1600)}
// 3D: each zone outlined on the ground in its colour with a post at each corner, drawn on the ghost path (into ga, which
// v3frame uploads to V3.dyn). The outline is built only when the zones or the ground change, and each edge is one strip
// per run of tiles at one ground height (one strip a side on flat land), so the per-frame upload stays small. The drag
// is drawn as the zone it will make (clamped as RmJzAdd clamps it).
const JBG={key:'',a:[],h:null,f:null,focus:null,focusAt:0,hot:null,open:(()=>{try{return new Set(JSON.parse(localStorage.getItem('rm-jbopen')||'[]').map(String))}catch(_){return new Set()}})(),guideOff:(()=>{try{return localStorage.getItem('rm-jbguide')==='off'}catch(_){return false}})(),fold:(()=>{try{return JSON.parse(localStorage.getItem('rm-jbfold')||'{}')||{}}catch(_){return {}}})()};
function jbOutline(a,x0,y0,x1,y1,c,post,w=0.14){const up=0.04;
 const flat=(X0,X1,Z0,Z1,g)=>quad(a,[X0,g,Z1],[X1,g,Z1],[X1,g,Z0],[X0,g,Z0],[0,1,0],c);
 const runs=(n,gAt,emit)=>{let s=0,g=gAt(0);for(let i=1;i<=n;i++){const gi=i<n?gAt(i):null;if(gi!==g){emit(s,i-1,g+up);s=i;g=gi}}};
 runs(x1-x0+1,i=>v3groundAt(x0+i,y0),(s,e,g)=>flat(x0+s-0.5,x0+e+0.5,-y0+0.5-w,-y0+0.5,g));
 runs(x1-x0+1,i=>v3groundAt(x0+i,y1),(s,e,g)=>flat(x0+s-0.5,x0+e+0.5,-y1-0.5,-y1-0.5+w,g));
 runs(y1-y0+1,i=>v3groundAt(x0,y0+i),(s,e,g)=>flat(x0-0.5,x0-0.5+w,-(y0+e)-0.5,-(y0+s)+0.5,g));
 runs(y1-y0+1,i=>v3groundAt(x1,y0+i),(s,e,g)=>flat(x1+0.5-w,x1+0.5,-(y0+e)-0.5,-(y0+s)+0.5,g));
 if(post)for(const [x,y,X,Z] of [[x0,y0,x0-0.5+w/2,-y0+0.5-w/2],[x1,y0,x1+0.5-w/2,-y0+0.5-w/2],[x0,y1,x0-0.5+w/2,-y1-0.5+w/2],[x1,y1,x1+0.5-w/2,-y1-0.5+w/2]]){const g=v3groundAt(x,y);boxr(a,X-0.07,X+0.07,Z-0.07,Z+0.07,g,g+0.85,c)}}
window.jbGhosts=function(ga){const m=jbModel(),Z=m&&m.jobs&&arr(m.jobs.zones).filter(z=>z[4]===V3.z);
 jbPlates(Z);
 if(Z&&Z.length){const key=JSON.stringify(Z.map(z=>z.slice(0,6)));if(key!==JBG.key||JBG.h!==V3.hgt||JBG.f!==V3.farH){JBG.key=key;JBG.h=V3.hgt;JBG.f=V3.farH;const a=[];
   for(const z of Z){const K=JB_KIND[z[5]];if(K&&K[2])jbOutline(a,z[0],z[1],z[2],z[3],K[2],true)}JBG.a=a}
  const a=JBG.a;for(let i=0;i<a.length;i++)ga.push(a[i]);
  const hz=JBG.hot&&Z.find(z=>String(z[9])===JBG.hot),HK=hz&&JB_KIND[hz[5]];   // the row under the mouse on the board: its zone stands out
  if(HK&&HK[2])jbOutline(ga,hz[0],hz[1],hz[2],hz[3],HK[2].map((v,i)=>i<3?Math.min(1,v*1.45+0.1):1),false,0.32)}else JBG.a=[]
 const k=jbMode(),bb=$('build3d');if(!k)return;const K=JB_KIND[k]||JB_KIND.wood,side=JB_SIDE[k]||25;let msg=K[0]+' zone: drag a rectangle on the ground, up to '+side+' tiles a side · Esc to stop';
 if(V3.paint&&V3.hoverTile){const a=V3.paint,b=V3.hoverTile,ax=Math.min(a.x,b.x),ay=Math.min(a.y,b.y),bx=Math.min(Math.max(a.x,b.x),ax+side-1),by=Math.min(Math.max(a.y,b.y),ay+side-1),w=bx-ax+1,h=by-ay+1;
  const over=k==='stock'?null:arr(m&&m.jobs&&m.jobs.zones).find(z=>z[5]!=='stock'&&z[4]===V3.z&&ax<=z[2]&&bx>=z[0]&&ay<=z[3]&&by>=z[1]);   // as RmJzAdd refuses it
  const cb=document.body.classList.contains('cb');   // colour-blind mode: vermilion against blue, not red against green
  const col=over?(cb?[0.84,0.37,0,1]:[0.95,0.3,0.25,1]):cb?[0.34,0.71,0.91,1]:K[2]?[Math.min(1,K[2][0]*1.3),Math.min(1,K[2][1]*1.3),Math.min(1,K[2][2]*1.3),1]:[0.35,0.9,0.45,1];
  jbOutline(ga,ax,ay,bx,by,col,false);
  let n=null;const T=V3.terrain;   // what's under the drag, while it lies in the detailed ground the page has
  if((k==='wood'||k==='stone')&&T&&ax>=T.x0&&ay>=T.y0&&bx<T.x0+T.w&&by<T.y0+T.h){n=0;const want=k==='wood'?'tree':'wall';for(let y=ay;y<=by;y++)for(let x=ax;x<=bx;x++){const q=v3kindAt(x,y);if(q&&q.kind===want)n++}}
  msg=over?K[0]+' zone: overlaps '+over[6]+' · work zones can’t share ground':K[0]+' zone: '+w+' × '+h+' tiles'+(n!=null?' · '+n+(k==='wood'?(n===1?' tree':' trees'):' rock'):'')+(k==='stock'?'':' · room for '+Math.max(1,Math.floor(w*h/4))+' workers')+' · let go to paint it'}
 if(bb){if(bb.hidden)bb.hidden=false;text(bb,msg)}};
// Each zone's name plate in 3D ("Wood 1 · 4/6"), like the food stalls' (v3foodTags): at the middle of the zone's edge
// highest on the screen that is on it (the far side, clear of the workers inside); a click opens its row on the Work tab.
function jbPlates(Z){let box=$('jb3d');const L=Z||[];if(!box){if(!L.length)return;box=document.createElement('div');box.id='jb3d';const f=$('food3d');(f&&f.parentNode||document.body).insertBefore(box,f?f.nextSibling:null);
  box.addEventListener('click',e=>{const s=e.target.closest('[data-jbid]');if(s)jbOpenRow(s.dataset.jbid)})}
 while(box.childElementCount<L.length){const e=document.createElement('span');e.title='Open on the job board';box.append(e)}const c=$('world3d'),W=c?c.clientWidth:0,H=c?c.clientHeight:0,far=V3.dist>45;   // an overview: the outlines say enough
 [...box.children].forEach((e,i)=>{const z=L[i];if(!z||far){e.hidden=true;return}let s=null;
  for(const [mx,my] of [[(z[0]+z[2])/2,z[3]+0.5],[(z[0]+z[2])/2,z[1]-0.5],[z[0]-0.5,(z[1]+z[3])/2],[z[2]+0.5,(z[1]+z[3])/2]]){
   const q=v3project([mx,v3groundAt(Math.round(mx),Math.round(my))+0.9,-my]);if(q&&q[0]>=30&&q[1]>=24&&q[0]<=W-30&&q[1]<=H-8&&(!s||q[1]<s[1]))s=q}
  if(!s){e.hidden=true;return}e.hidden=false;
  const t=z[6]+' · '+(z[8]<0?'paused':(z[7]||0)+'/'+(z[8]||0));if(e.textContent!==t)e.textContent=t;if(e.dataset.jbid!==String(z[9]))e.dataset.jbid=String(z[9]);
  const K=JB_KIND[z[5]];if(K&&e.dataset.c!==K[1]){e.dataset.c=K[1];e.style.borderLeftColor=K[1]}const hot=JBG.hot===String(z[9]);if(e.classList.contains('hot')!==hot)e.classList.toggle('hot',hot);e.style.transform='translate('+Math.round(s[0])+'px,'+Math.round(s[1])+'px) translate(-50%,-100%)'})}
// Zone modes are "floor" pieces to the game's own ghost: any tile is fine, and a drag is drawn by jbGhosts (the
// game's preview stops at 600 tiles; a 25 × 25 zone is 625).
{const ok0=v3ghostOk,pt0=v3paintTiles;v3ghostOk=function(t,kind){return jbMode()?'ok':ok0(t,kind)};v3paintTiles=function(a,b,kind){return jbMode()?[]:pt0(a,b,kind)}}
