<script>
/* Plan mode (ramps-gather, 2026-10-25; tried out first in tools/plan_mode/arena.html). The player marks blocks of the
   mountain grid one level at a time and queues them as a dig plan (Plans.dm): a row on the job board that villagers on
   the Any role take up by themselves. The user: "we don't have to control individual workers, we make a plan and then
   they set it in motion".
   - One level at a time: the whole view is cut at the level looked at (the cutaway's V3.planCut), its blocks low slabs,
     its floors lit; a block cursor sits on that level only (the mouse moves it on the level's plane: nothing in front
     steals it), arrows move it turned to the camera, PageUp / PageDown change the level, Esc leaves.
   - Tools: Dig (the blocks a shape covers), Build (blocks to lay where there are none: on open ground or on a block or
     a mark under it, drawn as blue ghosts), Clear (everything from this level up inside the shape), Erase. Shapes:
     single, line, box, outline. A drag takes more levels with the wheel. Queue it sends the marks (planadd), a dig plan
     and a build plan (Plans.dm, stage 3) for what is marked of each.
   - The queued blocks come back in the 3D update (V3.planCells, the 5th field 1 for a block to build) and are drawn
     darker; the plans' rows in model.plans.
   Patched in by tools/plan_mode/patch_page.py (before the last script, which asks for the game and stops the page). */
(function(){
if(window.PM)return;
const PM={on:false,level:0,cx:0,cy:0,tool:'dig',shape:'box',drag:null,prio:2,marks:new Map(),undo:[],bad:false,sentAt:0};
window.PM=PM;
const SLAB=0.4,R=13;
const key=(x,y,k)=>x+','+y+','+k;
const COL={dig:[0.93,0.66,0.25,1],clear:[0.93,0.66,0.25,1],build:[0.42,0.68,0.96,1],erase:[0.9,0.42,0.36,1]},QCOL=[0.6,0.42,0.16,1],QBCOL=[0.26,0.44,0.7,1],BAD=[0.9,0.4,0.33,1];
const lit=(c,k)=>[Math.min(1,c[0]*k),Math.min(1,c[1]*k),Math.min(1,c[2]*k),1];
const has=(x,y,k)=>{const K=typeof v3kindAt==='function'&&v3kindAt(x,y);return !!K&&k>=0&&v3stackHas(K,k)&&(K.kind==='wall'&&!!K.blocks||!!K.roof)};
const topOf=(x,y)=>{const K=v3kindAt(x,y);return K?v3stackTop(K):0};
const queued=(x,y,k)=>!!(PM.qset&&PM.qset.has(key(x,y,k)));
const qbuild=(x,y,k)=>!!(PM.qset&&PM.qset.get(key(x,y,k))===1);
const mbuild=(x,y,k)=>{const m=PM.marks.get(key(x,y,k));return !!(m&&m.b)};
// where a block can be laid: none there, and open ground under it (level 0), or a block, a build mark or a queued
// block to build under it (the game checks it again: Plans.dm RmPlanBuildable)
const GROUND={floor:1,bfloor:1};
function canBuild(x,y,k,more){const K=typeof v3kindAt==='function'&&v3kindAt(x,y);if(!K||has(x,y,k))return false;
 if(k===0)return !!GROUND[K.kind];if(K.kind!=='wall'&&!GROUND[K.kind])return false;
 return has(x,y,k-1)||mbuild(x,y,k-1)||qbuild(x,y,k-1)||!!(more&&more.has(key(x,y,k-1)))||(!!K.roof&&has(x,y,k+1))}
// the way the camera looks, snapped to a side of the grid (tile x, tile y)
function fwd(){const f=[-Math.sin(V3.yaw),Math.cos(V3.yaw)];return Math.abs(f[0])>Math.abs(f[1])?[Math.sign(f[0]),0]:[0,Math.sign(f[1])]}
// the tile under the pointer on the level looked at: the top of its slabs first, where that is open the floor under it
function pick(sx,sy){if(!V3.inv)return null;const c=$('world3d'),nx=sx/c.clientWidth*2-1,ny=1-sy/c.clientHeight*2,m=V3.inv;
 const un=(x,y,z)=>{const X=x*m[0]+y*m[4]+z*m[8]+m[12],Y=x*m[1]+y*m[5]+z*m[9]+m[13],Z=x*m[2]+y*m[6]+z*m[10]+m[14],W=x*m[3]+y*m[7]+z*m[11]+m[15];return [X/W,Y/W,Z/W]};
 const a=un(nx,ny,-1),b=un(nx,ny,1),at=h=>{const d=b[1]-a[1];if(Math.abs(d)<1e-6)return null;const t=(h-a[1])/d;if(t<0)return null;return [Math.round(a[0]+(b[0]-a[0])*t),Math.round(-(a[2]+(b[2]-a[2])*t))]};
 const L=PM.level,p=at(L+SLAB);if(p&&has(p[0],p[1],L))return p;return at(L)}
function shapeCells(a,b,lo,hi,shape,tool){const out=[];b=b||a;const x0=Math.min(a[0],b[0]),x1=Math.max(a[0],b[0]),y0=Math.min(a[1],b[1]),y1=Math.max(a[1],b[1]);
 if(tool==='clear'){for(const [x,y] of shapeCells(a,b,lo,lo,shape,'dig')){const t=topOf(x,y);for(let k=lo;k<Math.max(t,lo+1);k++)if(has(x,y,k))out.push([x,y,k])}return out}   // the columns over the shape, from this level up
 if((x1-x0+1)*(y1-y0+1)>900)return out;
 for(let k=lo;k<=hi;k++){if(shape==='single'){out.push([b[0],b[1],k]);continue}
  if(shape==='line'){if(x1-x0>=y1-y0){for(let x=x0;x<=x1;x++)out.push([x,a[1],k])}else for(let y=y0;y<=y1;y++)out.push([a[0],y,k]);continue}
  for(let y=y0;y<=y1;y++)for(let x=x0;x<=x1;x++){if(shape==='outline'&&x>x0&&x<x1&&y>y0&&y<y1)continue;out.push([x,y,k])}}return out}
const markable=(tool,x,y,k,more)=>tool==='erase'?PM.marks.has(key(x,y,k)):PM.marks.has(key(x,y,k))||queued(x,y,k)?false:tool==='build'?canBuild(x,y,k,more):has(x,y,k);
// a drag's cells, the lowest level first, so a build drag over several levels stacks on its own lower blocks
function dragCells(){const d=PM.drag,lo=Math.min(d.k0,PM.level),hi=Math.max(d.k0,PM.level),more=new Set(),out=[];
 for(const c of shapeCells(d.a,[PM.cx,PM.cy],lo,hi,PM.shape,PM.tool).sort((p,q)=>p[2]-q[2]))if(markable(PM.tool,c[0],c[1],c[2],more)){out.push(c);more.add(key(c[0],c[1],c[2]))}return out}
function apply(cells){const act={add:[],del:[]};let n=0;const more=new Set();for(const [x,y,k] of cells.slice().sort((p,q)=>p[2]-q[2])){const kk=key(x,y,k);if(PM.tool==='erase'){if(PM.marks.has(kk)){delMark(act,kk);n++}continue}
  if(!markable(PM.tool,x,y,k,more))continue;PM.marks.set(kk,{born:performance.now(),b:PM.tool==='build'});more.add(kk);act.add.push(kk);n++}
 if(n)PM.undo.push(act);else shake();if(PM.undo.length>60)PM.undo.shift();card();tag();return n}
// an undo puts back what it took away as it was (a dig or a build mark)
function delMark(act,kk){act.del.push([kk,PM.marks.get(kk)]);PM.marks.delete(kk)}
function undo(){const a=PM.undo.pop();if(!a){shake();return}for(const kk of a.add)PM.marks.delete(kk);for(const [kk,m] of a.del)PM.marks.set(kk,{born:performance.now(),b:!!(m&&m.b)});card();tag()}
// one plan of each kind marked: the dig marks, then the build marks
function queue(){if(!PM.marks.size){shake();return}const dig=[],bld=[];for(const [kk,m] of PM.marks)(m.b?bld:dig).push(kk);
 if(dig.length)send('planadd',PM.prio+'|'+dig.join('/'));if(bld.length)send('planadd',PM.prio+'|'+bld.join('/')+'|build');
 PM.sent=new Map([...dig.map(k=>[k,0]),...bld.map(k=>[k,1])]);PM.sentAt=performance.now();PM.marks.clear();PM.undo.length=0;card();tag()}
function shake(){PM.shakeAt=performance.now();const t=$('pmTag');if(t){t.classList.remove('pmshake');void t.offsetWidth;t.classList.add('pmshake')}}
function setLevel(l){PM.level=Math.max(0,Math.min(15,l));const e=$('pmLvl');if(e)e.textContent='Level '+PM.level;card();tag()}
function setTool(t){PM.tool=t;document.querySelectorAll('#pmBar [data-pmtool]').forEach(b=>b.classList.toggle('on',b.dataset.pmtool===t));card();tag()}
function setShape(s){PM.shape=s;document.querySelectorAll('#pmBar [data-pmshape]').forEach(b=>b.classList.toggle('on',b.dataset.pmshape===s));tag()}
function setOn(on){if(on&&V3.z!==1){if(typeof toast==='function')toast('Plan mode works on the surface view for now.');return}PM.on=on;PM.drag=null;V3.planCut=on?PM.level+SLAB:null;
 ['pmBar','pmCard','pmKeys','pmTag'].forEach(id=>{const e=$(id);if(e)e.hidden=!on});const b=$('btnPlan');if(b)b.setAttribute('aria-pressed',String(on));
 if(on){const s=V3.things&&V3.things.find(t=>t.kind==='mine'&&t.selected);if(s){PM.cx=s.x;PM.cy=s.y;setLevel(s.ly>0?(s.feet!=null?s.feet:Math.round(s.ly)):0)}else{PM.cx=Math.round(V3.cx);PM.cy=Math.round(V3.cy);setLevel(PM.level)}}
 card();tag()}
function move(f,r){const F=fwd(),Rt=[F[1],-F[0]];PM.cx+=F[0]*f+Rt[0]*r;PM.cy+=F[1]*f+Rt[1]*r;if(PM.drag)PM.drag.moved=true;tag()}
// ---------- the HUD: the bar, the plan card (with the plans queued), the key strip, the tag over the cursor ----------
function build(){if($('pmBar'))return;const st=document.createElement('style');st.textContent=
 '.pmp{position:fixed;z-index:60;background:var(--mpane,#141d2b);border:1px solid var(--mband,#34465f);border-radius:6px;box-shadow:0 2px 10px #0008;color:var(--mink,#ece3cc);font-size:12px}'+
 '.pmp button{font:inherit;color:inherit;background:#ffffff0d;border:1px solid var(--mband,#34465f);border-radius:4px;padding:3px 8px;cursor:pointer}.pmp button:hover{filter:brightness(1.25)}.pmp button.on{border-color:var(--macc,#d9b45f);color:#fff;background:#ffffff1f}'+
 '.pmp .t{font-family:var(--mfont,Georgia,serif);color:var(--macc,#d9b45f);font-size:15px}.pmp .s{color:#ffffffa0;font-size:11px}.pmp kbd{font:10px Menlo,monospace;border:1px solid var(--mband,#34465f);border-radius:3px;padding:0 3px;margin-left:4px;color:var(--macc,#d9b45f)}'+
 '#pmBar{top:46px;left:50%;transform:translateX(-50%);display:flex;gap:5px;align-items:center;padding:6px 8px}#pmBar i{width:1px;height:20px;background:var(--mband,#34465f);margin:0 3px}'+
 '#pmCard{left:8px;top:150px;width:236px;padding:9px 11px}#pmCard .r{display:flex;justify-content:space-between;padding:3px 0;border-top:1px solid #ffffff14}#pmCard .r span:first-child{color:#ffffffa0}#pmCard .a{display:flex;gap:6px;margin-top:8px}#pmCard .a button{flex:1}'+
 '#pmCard .q{border-top:1px solid #ffffff14;padding:5px 0}#pmCard .q .bar{height:5px;background:#0006;border-radius:3px;margin:4px 0;overflow:hidden}#pmCard .q .bar b{display:block;height:100%;background:var(--macc,#d9b45f)}'+
 '#pmKeys{left:50%;bottom:92px;transform:translateX(-50%);padding:5px 10px;color:#ffffffa8;font-size:11px;white-space:nowrap}#pmKeys b{color:var(--mink,#ece3cc);font-weight:500}'+
 '#pmTag{position:fixed;z-index:61;pointer-events:none;transform:translate(-50%,-150%);padding:2px 8px;font-size:11px;white-space:nowrap}#pmTag.bad{border-color:#e2685a;color:#f6c8c0}#pmTag.pmshake{animation:pmshake .3s}'+
 '@keyframes pmshake{0%,100%{margin-left:0}25%{margin-left:-6px}50%{margin-left:5px}75%{margin-left:-3px}}#btnPlan{--ico:var(--hci-tasks)}';document.head.appendChild(st);
 const bar=document.createElement('div');bar.id='pmBar';bar.className='pmp';bar.hidden=true;
 bar.innerHTML='<button data-pmtool="dig" title="Dig: mark the blocks a shape covers on this level (1)">Dig</button><button data-pmtool="build" title="Build: blocks to lay where there are none, on open ground or on a block under it; one stone each (2)">Build</button><button data-pmtool="clear" title="Clear: everything from this level up inside the shape, a clean floor here (3)">Clear</button><button data-pmtool="erase" title="Erase: take marks away (4)">Erase</button><i></i>'+
  '<button data-pmshape="single">Single</button><button data-pmshape="line">Line</button><button data-pmshape="box">Box</button><button data-pmshape="outline">Outline</button><i></i>'+
  '<button id="pmDn" title="Level down (PageDown)">&#9660;</button><span id="pmLvl" style="min-width:58px;text-align:center">Level 0</span><button id="pmUp" title="Level up (PageUp)">&#9650;</button><i></i><button id="pmDone" title="Leave Plan mode (Esc)">Done<kbd>Esc</kbd></button>';
 document.body.appendChild(bar);
 const cd=document.createElement('div');cd.id='pmCard';cd.className='pmp';cd.hidden=true;document.body.appendChild(cd);
 const ks=document.createElement('div');ks.id='pmKeys';ks.className='pmp';ks.hidden=true;ks.innerHTML='<b>Click</b> / <b>drag</b>: mark · <b>wheel</b> while dragging: more levels · <b>right-click</b>: unmark · <b>arrows</b>: move · <b>PageUp</b>/<b>PageDown</b>: level · <b>Esc</b>: done';document.body.appendChild(ks);
 const tg=document.createElement('div');tg.id='pmTag';tg.className='pmp';tg.hidden=true;document.body.appendChild(tg);
 bar.addEventListener('click',e=>{const t=e.target.closest('[data-pmtool]');if(t)return setTool(t.dataset.pmtool);const s=e.target.closest('[data-pmshape]');if(s)return setShape(s.dataset.pmshape);
  if(e.target.closest('#pmUp'))setLevel(PM.level+1);if(e.target.closest('#pmDn'))setLevel(PM.level-1);if(e.target.closest('#pmDone'))setOn(false)});
 cd.addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;if(b.id==='pmQueue')queue();else if(b.id==='pmClear'){const a={add:[],del:[...PM.marks.entries()]};if(a.del.length)PM.undo.push(a);PM.marks.clear();card();tag()}else if(b.id==='pmPrio'){PM.prio=PM.prio%3+1;card()}
  else if(b.dataset.pmrow)send('jobrow',b.dataset.pmrow)});
 // the dock button, beside Gather
 const g=$('btnGather');if(g&&!$('btnPlan')){const b=document.createElement('button');b.id='btnPlan';b.setAttribute('aria-pressed','false');b.title='Plan mode\nMark blocks to dig or build, level by level, and queue them: the job board\'s villagers dig and build them by themselves.';b.innerHTML='<b class="gear pick">&#9776;</b><span>Plan</span>';b.addEventListener('click',e=>{e.stopPropagation();setOn(!PM.on)});g.after(b)}
 setTool('dig');setShape('box')}
const PRIO=['','High','Normal','Low'];
const blocks=n=>n+' block'+(n>1?'s':'');
function card(){const cd=$('pmCard');if(!cd||!PM.on)return;const n=PM.marks.size;let nb=0;for(const m of PM.marks.values())if(m.b)nb++;const nd=n-nb;
 const rows=[['To dig',nd?blocks(nd):'none'],['To build',nb?blocks(nb)+' · '+nb+' stone':'none'],['Priority','<button id="pmPrio" title="Priority on the job board">'+PRIO[PM.prio]+'</button>']];
 let h='<div class="t">'+(nd&&nb?'Dig and build plan':nb?'Build plan':nd?'Dig plan':'Plan')+'</div><div class="s">'+(n?'Not queued yet: Queue it puts it on the job board':'Mark blocks on level '+PM.level+' to '+({dig:'dig',build:'build',clear:'clear',erase:'unmark'})[PM.tool])+'</div>'+rows.map(([a,b])=>'<div class="r"><span>'+a+'</span><span>'+b+'</span></div>').join('')+
  '<div class="a"><button id="pmQueue"'+(n?'':' disabled')+'>Queue it</button><button id="pmClear"'+(n?'':' disabled')+'>Clear</button></div>';
 const P=arr(model&&model.plans);if(P.length)h+='<div class="t" style="font-size:13px;margin-top:9px">Plans</div>'+P.map(p=>'<div class="q"><div style="display:flex;justify-content:space-between"><span>'+p.name+'</span><span class="s">'+(p.total-p.left)+'/'+p.total+'</span></div><div class="bar"><b style="width:'+Math.round(100*(p.total-p.left)/Math.max(1,p.total))+'%"></b></div><div class="s">Level '+p.levels+' · '+PRIO[p.prio]+' · '+(p.count?p.count+' at work · ':'')+String(p.status||'').replace(/^(Dig|Build) \d+: /,'')+'</div>'+
  '<div style="display:flex;gap:4px;margin-top:3px"><button data-pmrow="'+p.id+'|pause">'+(p.paused?'Go on':'Pause')+'</button><button data-pmrow="'+p.id+'|prio|'+Math.max(1,p.prio-1)+'" title="Priority up">&#9650;</button><button data-pmrow="'+p.id+'|look" title="Go to it">Go to</button><button data-pmrow="'+p.id+'|remove" title="Remove the plan">&#10005;</button></div></div>').join('');
 if(cd.dataset.h!==h){cd.dataset.h=h;cd.innerHTML=h}}
function tag(){const t=$('pmTag');if(!t||!PM.on)return;const x=PM.cx,y=PM.cy,k=PM.level,kk=key(x,y,k);let txt,bad=false;
 if(PM.drag&&PM.drag.moved){const a=PM.drag.a,w=Math.abs(x-a[0])+1,h=Math.abs(y-a[1])+1,lv=Math.abs(k-PM.drag.k0)+1,n=dragCells().length;txt=(PM.tool==='clear'?'Clear '+w+' × '+h+' · level '+Math.min(k,PM.drag.k0)+' and up':PM.shape[0].toUpperCase()+PM.shape.slice(1)+' '+w+' × '+h+(lv>1?' × '+lv+' levels':''))+' · '+n+' block'+(n===1?'':'s');bad=!n}
 else{const what=has(x,y,k)?'a block':has(x,y,k-1)||k===0?'open floor':'open air';let act;if(PM.marks.has(kk))act='marked (click: unmark)';else if(queued(x,y,k))act=qbuild(x,y,k)?'queued to build':'queued to dig';else if(PM.tool==='erase')act='nothing marked here';
  else if(PM.tool==='build'){if(canBuild(x,y,k))act='click: build a block here';else{act=has(x,y,k)?'a block is there already':'nothing to build on here';bad=true}}
  else if(has(x,y,k))act='click: mark '+(PM.tool==='clear'?'this column from here up':'it');else{act='nothing to dig here';bad=true}
  txt='Level '+k+' · '+what+' · '+act}
 if(t.textContent!==txt)t.textContent=txt;t.classList.toggle('bad',bad);PM.bad=bad}
// ---------- input: the 3D view's mouse while Plan mode is on (the right button still pans), the game's keys ----------
function hookInput(){const c=$('world3d');if(!c||c.dataset.pm)return;c.dataset.pm='1';
 c.addEventListener('mousedown',e=>{if(!PM.on)return;if(e.button===0){e.stopImmediatePropagation();e.preventDefault();const p=pick(mx(e),my(e));if(p){PM.cx=p[0];PM.cy=p[1]}PM.drag={a:[PM.cx,PM.cy],k0:PM.level,moved:false};tag()}else if(e.button===2)PM.rdown={x:e.clientX,y:e.clientY}},true);
 addEventListener('mousemove',e=>{if(!PM.on||!(e.target===c||PM.drag))return;const p=pick(mx(e),my(e));if(p&&(p[0]!==PM.cx||p[1]!==PM.cy)){PM.cx=p[0];PM.cy=p[1];if(PM.drag)PM.drag.moved=true;tag()}},true);
 addEventListener('mouseup',e=>{if(!PM.on)return;
  if(e.button===0&&PM.drag){e.stopImmediatePropagation();const d=PM.drag,cells=d.moved?dragCells():null;PM.drag=null;if(cells)apply(cells);else{const kk=key(PM.cx,PM.cy,PM.level);if(PM.marks.has(kk)){const act={add:[],del:[]};delMark(act,kk);PM.undo.push(act);card();tag()}else apply(PM.tool==='clear'?shapeCells([PM.cx,PM.cy],null,PM.level,PM.level,'single','clear'):[[PM.cx,PM.cy,PM.level]])}return}
  if(e.button===2&&PM.rdown){const moved=Math.hypot(e.clientX-PM.rdown.x,e.clientY-PM.rdown.y)>6;PM.rdown=null;if(!moved&&e.target===c){e.stopImmediatePropagation();V3.drag=null;const p=pick(mx(e),my(e));if(p){PM.cx=p[0];PM.cy=p[1];const kk=key(p[0],p[1],PM.level);if(PM.marks.has(kk)){const act={add:[],del:[]};delMark(act,kk);PM.undo.push(act);card()}else shake();tag()}}}},true);
 c.addEventListener('contextmenu',e=>{if(PM.on){e.preventDefault();e.stopImmediatePropagation()}},true);
 c.addEventListener('wheel',e=>{if(!PM.on||!PM.drag)return;e.preventDefault();e.stopImmediatePropagation();const now=performance.now();if(now-(PM.wheelAt||0)<90)return;PM.wheelAt=now;setLevel(PM.level+(e.deltaY<0?1:-1))},{capture:true,passive:false});
 // the game's keys (the game window has them after a click): arrows move the cursor, PageUp / PageDown change level
 const k3=window.key3d;window.key3d=function(k){if(PM.on){k=String(k);const mv={north:[1,0],south:[-1,0],east:[0,1],west:[0,-1]}[k];if(mv){move(mv[0],mv[1]);return}
  if(k==='northeast'){setLevel(PM.level+1);return}if(k==='southeast'){setLevel(PM.level-1);return}if(k==='escape'){if(PM.drag){PM.drag=null;tag()}else setOn(false);return}}return k3?k3(k):undefined};
 // and the page's own keys, when it has them
 addEventListener('keydown',e=>{if(!PM.on||e.target.closest&&e.target.closest('input,select,textarea'))return;const k=e.key.toLowerCase();let done=true;
  if((e.metaKey||e.ctrlKey)&&k==='z')undo();else if(e.metaKey||e.ctrlKey||e.altKey)return;
  else if(k==='w'||k==='arrowup')move(1,0);else if(k==='s'||k==='arrowdown')move(-1,0);else if(k==='a'||k==='arrowleft')move(0,-1);else if(k==='d'||k==='arrowright')move(0,1);
  else if(k==='r'||k==='pageup')setLevel(PM.level+1);else if(k==='f'||k==='pagedown')setLevel(PM.level-1);else if(k==='1')setTool('dig');else if(k==='2')setTool('build');else if(k==='3')setTool('clear');else if(k==='4')setTool('erase');
  else if(k===' '){const kk=key(PM.cx,PM.cy,PM.level);if(PM.marks.has(kk)){const act={add:[],del:[]};delMark(act,kk);PM.undo.push(act);card();tag()}else apply([[PM.cx,PM.cy,PM.level]])}else if(k==='enter')queue();else if(k==='escape'){if(PM.drag){PM.drag=null;tag()}else setOn(false)}else done=false;
  if(done){e.preventDefault();e.stopImmediatePropagation()}},true)}
// ---------- the blocks being worked right now, Plan mode on or off ----------
// Each own unit's 3D record says which block it is mining (wk: x, y, block; -1 the face's next outside block, -2 the
// top: Plans.dm RmWorkedBlock3D), whoever gave the order. Drawn yellow on the rock's faces with a click's dig mark
// (rfMineMark), once per block however many work it, and not where a selected unit's order already outlines that rock
// (v3queues, in the orders' gold: two marks on one face would flicker); rebuilt only when the things, the orders, the
// ground or the camera's turn change (as the order queue's v3digCached), pushed as it is in between. V3.workCheck=1 builds it afresh each frame and
// counts any difference (V3.workCk).
const WKCOL=[1,0.86,0.28,1];
function pmWorkedBuild(keys){const v=[];for(const k of keys){const [x,y,b]=k.split(',').map(Number),blk=b===-2?'top':b===-1?null:b;let ok=false;
  try{ok=rfMineMark(v,x,y,WKCOL,0.055,blk)}catch(e){ok=false}if(!ok&&typeof rfSquare==='function'&&typeof rfY==='function')rfSquare(v,x,rfY(x,y),-y,0.49,0.045,WKCOL)}return v}
function pmWorked(a){if(typeof rfMineMark!=='function')return;const S=PM.wk||(PM.wk={things:null,targets:null,keys:[],v:[]}),TG=typeof model!=='undefined'&&model?model.targets:null;
 if(S.things!==V3.things||S.targets!==TG){S.things=V3.things;S.targets=TG;const outl=new Set();for(const q of arr(TG))if(q.z===V3.z&&/mine|dig/i.test(q.kind||''))outl.add(q.x+','+q.y);
  const set=new Set();for(const t of arr(V3.things))if(t.kind==='mine'&&t.wk&&!outl.has(t.wk[0]+','+t.wk[1]))set.add(t.wk.join(','));const keys=[...set].sort();
  if(keys.join(';')!==S.keys.join(';')){S.keys=keys;S.v=null}}
 if(!S.keys.length)return;
 if(!S.v||S.rock!==V3.rockGeo||S.terr!==V3.terrain||S.tg!==V3.terrGen||S.mg!==V3.tmeshGen||S.yaw!==V3.yaw){S.rock=V3.rockGeo;S.terr=V3.terrain;S.tg=V3.terrGen;S.mg=V3.tmeshGen;S.yaw=V3.yaw;S.v=pmWorkedBuild(S.keys)}
 for(let i=0;i<S.v.length;i++)a.push(S.v[i]);
 if(V3.workCheck){const b=pmWorkedBuild(S.keys),C=V3.workCk||(V3.workCk={checked:0,differ:0});C.checked++;if(b.length!==S.v.length||b.some((x,i)=>x!==S.v[i]))C.differ++}}
// ---------- drawing: lit floors and the level's grid round the cursor, the marks, the queued blocks, the cursor ----------
let qsig='';
window.pmDraw=function(a){if(!$('pmBar')){build();hookInput()}
 pmWorked(a);
 if(PM.on&&V3.z!==1)setOn(false);
 const Q=arr(V3.planCells),sig=Q.length+':'+(Q[0]||'')+(Q[Q.length-1]||'');if(sig!==qsig){qsig=sig;PM.qset=new Map(Q.map(c=>[key(c[0],c[1],c[2]),c[4]===1?1:0]));card();tag()}
 if(!PM.on){V3.planCut=null;return}V3.planCut=PM.level+SLAB;V3.planR=26;
 if(PM.sent&&performance.now()-PM.sentAt>4000)PM.sent=null;
 const L=PM.level,Z0=[0,0,0],t=performance.now();if(!(t%1000<17))card();
 // the level round the cursor: its floors lit, its blocks' tops outlined (the cut leaves them low slabs)
 for(let dy=-R;dy<=R;dy++)for(let dx=-R;dx<=R;dx++){const x=PM.cx+dx,y=PM.cy+dy;if(dx*dx+dy*dy>R*R)continue;
  if(has(x,y,L))rfSquare(a,x,L+SLAB+0.012,-y,0.5,0.018,[0.78,0.64,0.32,1]);
  else if(L>0&&has(x,y,L-1)){quad(a,[x-0.46,L+0.02,-y+0.46],[x+0.46,L+0.02,-y+0.46],[x+0.46,L+0.02,-y-0.46],[x-0.46,L+0.02,-y-0.46],Z0,[0.5,0.46,0.34,1]);rfSquare(a,x,L+0.025,-y,0.46,0.03,[0.96,0.88,0.6,1])}}
 // a mark: a tinted top over its block (a slab's on this level), its outline
 const mark=(x,y,k,c)=>{if(k>L)return;const h=k===L?k+SLAB+0.016:k+1.016;quad(a,[x-0.47,h,-y+0.47],[x+0.47,h,-y+0.47],[x+0.47,h,-y-0.47],[x-0.47,h,-y-0.47],Z0,c);rfSquare(a,x,h+0.004,-y,0.5,0.045,lit(c,1.25))};
 // a block to build: a ghost of it, its top and its four upright edges (a slab's height on this level)
 const ghost=(x,y,k,c)=>{if(k>L)return;const top=k===L?k+SLAB:k+1,lo=k+0.02;mark(x,y,k,c);const e=lit(c,1.3),rt=[Math.cos(V3.yaw)*0.03,0,-Math.sin(V3.yaw)*0.03];
  for(const [ox,oz] of [[-0.47,-0.47],[0.47,-0.47],[0.47,0.47],[-0.47,0.47]]){const px=x+ox,pz=-y+oz;quad(a,[px-rt[0],lo,pz-rt[2]],[px+rt[0],lo,pz+rt[2]],[px+rt[0],top,pz+rt[2]],[px-rt[0],top,pz-rt[2]],Z0,e)}};
 const draw=(x,y,k,b,c)=>b?ghost(x,y,k,c):mark(x,y,k,c);
 for(const c of Q)if(Math.abs(c[0]-PM.cx)<=R+6&&Math.abs(c[1]-PM.cy)<=R+6)draw(c[0],c[1],c[2],c[4]===1,lit(c[4]===1?QBCOL:QCOL,0.85+0.15*Math.sin(t/380-(c[0]+c[1])*0.8)));   // queued: a slow wave over them
 for(const [kk,m] of PM.marks){const [x,y,k]=kk.split(',').map(Number);draw(x,y,k,m.b,m.b?COL.build:COL.dig)}
 if(PM.sent)for(const [kk,b] of PM.sent){if(PM.qset&&PM.qset.has(kk))continue;const [x,y,k]=kk.split(',').map(Number);draw(x,y,k,b===1,lit(b===1?QBCOL:QCOL,0.9))}   // sent, not back from the game yet
 if(PM.drag&&PM.drag.moved)for(const [x,y,k] of dragCells())draw(x,y,k,PM.tool==='build',lit(COL[PM.tool==='erase'?'erase':PM.tool==='build'?'build':'dig'],1.18));
 // the cursor: the block's whole outline on this level, red where the tool can't do anything (a shake when refused)
 const sa=t-(PM.shakeAt||-1e9),sh=sa<300?Math.sin(sa/22)*0.08*(1-sa/300):0,c=PM.bad||sa<300?BAD:lit(COL[PM.tool],1.2),X=PM.cx+sh,Zc=-PM.cy;
 rfSquare(a,X,L+0.03,Zc,0.53,0.05,c);rfSquare(a,X,L+1.02,Zc,0.53,0.05,c);const rt=[Math.cos(V3.yaw)*0.035,0,-Math.sin(V3.yaw)*0.035];
 for(const [ox,oz] of [[-0.53,-0.53],[0.53,-0.53],[0.53,0.53],[-0.53,0.53]]){const px=X+ox,pz=Zc+oz;quad(a,[px-rt[0],L,pz-rt[2]],[px+rt[0],L,pz+rt[2]],[px+rt[0],L+1.02,pz+rt[2]],[px-rt[0],L+1.02,pz-rt[2]],Z0,c)}
 // the tag over it
 const tg=$('pmTag');if(tg&&V3.vp){const m=V3.vp,wx=PM.cx,wy=L+1.15,wz=-PM.cy,cw=m[3]*wx+m[7]*wy+m[11]*wz+m[15];if(cw>0){const cx=(m[0]*wx+m[4]*wy+m[8]*wz+m[12])/cw,cy=(m[1]*wx+m[5]*wy+m[9]*wz+m[13])/cw,cv=$('world3d'),r=cv.getBoundingClientRect();
   tg.style.left=(r.left+(cx+1)/2*r.width)+'px';tg.style.top=(r.top+(1-cy)/2*r.height)+'px'}}};
})();
</script>
