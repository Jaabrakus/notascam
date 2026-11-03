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
   - The queued blocks come back in the 3D update (V3.planCells, the 5th field 1 for a block to build, the 6th 1 for
     wood) and are drawn darker; the plans' rows in model.plans.
   - Build lays stone or wood (building rework L1, 10-27): Stone | Wood on the card, key M; a mark keeps its material
     (m), Queue it sends one build plan for each (planadd ...|build|stone, ...|build|wood), whole columns at most 600
     blocks a plan, more plans for a bigger queue. Stone is drawn blue-grey, wood amber.
   Patched in by tools/plan_mode/patch_page.py (before the last script, which asks for the game and stops the page). */
(function(){
if(window.PM)return;
const PM={on:false,level:0,cx:0,cy:0,tool:'dig',shape:'box',mat:'stone',drag:null,prio:2,marks:new Map(),undo:[],bad:false,sentAt:0};
window.PM=PM;
const SLAB=0.4,R=13,PLANMAX=600,SL=3,SPAN=3,RMTOP=8;   // PLANMAX: Plans.dm RM_PLAN_MAX; SL: levels a storey (two of room, then its floor over the one under: the layered builder, phase 3); SPAN: Sites.dm RM_SPAN; RMTOP: Plans.dm RM_BUILD_TOP
const key=(x,y,k)=>x+','+y+','+k;
const stB=l=>Math.floor(l/SL)*SL;   // the ground level of a level's storey
const COL={dig:[0.93,0.66,0.25,1],clear:[0.93,0.66,0.25,1],build:[0.42,0.68,0.96,1],erase:[0.9,0.42,0.36,1],door:[0.9,0.62,0.28,1],floor:[0.76,0.74,0.68,1],design:[0.42,0.68,0.96,1]},QCOL=[0.6,0.42,0.16,1],QBCOL=[0.26,0.44,0.7,1],BAD=[0.9,0.4,0.33,1],WCOL=[0.9,0.5,0.18,1],QWCOL=[0.66,0.34,0.1,1];
const bcol=()=>PM.mat==='wood'?WCOL:COL.build;
const lit=(c,k)=>[Math.min(1,c[0]*k),Math.min(1,c[1]*k),Math.min(1,c[2]*k),1];
const has=(x,y,k)=>{const K=typeof v3kindAt==='function'&&v3kindAt(x,y);return !!K&&k>=0&&v3stackHas(K,k)&&(K.kind==='wall'&&!!K.blocks||!!K.roof)};
const topOf=(x,y)=>{const K=v3kindAt(x,y);return K?v3stackTop(K):0};
const queued=(x,y,k)=>!!(PM.qset&&PM.qset.has(key(x,y,k)));
const qbuild=(x,y,k)=>!!(PM.qset&&PM.qset.get(key(x,y,k))>=1);   // 1 stone, 2 wood
const mbuild=(x,y,k)=>{const m=PM.marks.get(key(x,y,k));return !!(m&&m.b)};
// where a block can be laid: none there, and open ground under it (level 0), or a block, a build mark or a queued
// block to build under it, or open air held by the walls (the game checks it again: Plans.dm RmPlanBuildable)
const GROUND={floor:1,bfloor:1},D4=[[1,0],[-1,0],[0,1],[0,-1]];
const bAt=(x,y,k,more)=>has(x,y,k)||mbuild(x,y,k)||qbuild(x,y,k)||!!(more&&more.has(key(x,y,k)));
// a block over open air (the layered builder, phase 3: a storey's floor over a room): held when blocks at its level
// (laid, marked or queued) lead within 3 tiles to one on a whole column, a wall or a pillar (Sites.dm RmPlanHeld);
// any: through open air too (would it be held with the floor between laid: the label's hint)
function held(x,y,k,more,any){if(k<=0)return false;const st=(p,q)=>{for(let j=k-1;j>=0;j--)if(!bAt(p,q,j,more))return false;return true},seen=new Set([x+','+y]);let fr=[[x,y]];
 for(let d=1;d<=SPAN&&fr.length;d++){const nx=[];for(const [a,b] of fr)for(const [dx,dy] of D4){const p=a+dx,q=b+dy,s=p+','+q;if(seen.has(s))continue;seen.add(s);if(!bAt(p,q,k,more)){if(any)nx.push([p,q]);continue}if(st(p,q))return true;nx.push([p,q])}fr=nx}return false}
function canBuild(x,y,k,more){const K=typeof v3kindAt==='function'&&v3kindAt(x,y);if(!K||has(x,y,k))return false;
 if(k===0)return !!GROUND[K.kind];if(K.kind!=='wall'&&!GROUND[K.kind])return false;
 return bAt(x,y,k-1,more)||(!!K.roof&&has(x,y,k+1))||(K.kind!=='wall'&&held(x,y,k,more))}
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
const pk=()=>PM.tool==='door'?stB(PM.level):PM.tool==='floor'&&stB(PM.level)>0?stB(PM.level)-1:0;   // a piece's level: a door its storey's ground, a floor upstairs the blocks over the room below (phase 3)
const markable=(tool,x,y,k,more)=>tool==='erase'?PM.marks.has(key(x,y,k)):piece(tool)?pieceOK(tool,x,y,pk(),more):PM.marks.has(key(x,y,k))||queued(x,y,k)?false:tool==='build'?canBuild(x,y,k,more):has(x,y,k);
// a drag's cells, the lowest level first, so a build drag over several levels stacks on its own lower blocks
function dragCells(){const d=PM.drag,pc=piece(PM.tool),lp=pk(),lo=pc?lp:Math.min(d.k0,PM.level),hi=pc?lp:Math.max(d.k0,PM.level,PM.tool==='build'?lo+(PM.height||1)-1:0),more=new Set(),out=[];   /* Build: as high as the card's Height (play test, 10-30) */
 let rest=shapeCells(d.a,[PM.cx,PM.cy],lo,hi,PM.shape,PM.tool).sort((p,q)=>p[2]-q[2]);
 for(let go=true;go&&rest.length;){go=false;rest=rest.filter(c=>{if(!markable(PM.tool,c[0],c[1],c[2],more))return true;out.push(c);more.add(key(c[0],c[1],c[2]));go=true;return false});if(!(pc&&lp>0&&PM.tool==='floor'))break}return out}   /* a floor upstairs: again till none more, each held by those before it (phase 3) */
function apply(cells){const act={add:[],del:[]};let n=0;const more=new Set();for(const [x,y,k] of cells.slice().sort((p,q)=>p[2]-q[2])){const kk=key(x,y,k);if(PM.tool==='erase'){if(PM.marks.has(kk)){delMark(act,kk);n++}else{const k0=key(x,y,0),m0=PM.marks.get(k0);if(m0&&m0.t){delMark(act,k0);n++}}continue}
  if(piece(PM.tool)){const kp=pk(),k0=key(x,y,kp);if(more.has(k0)||!markable(PM.tool,x,y,kp,more))continue;if(PM.tool==='floor'&&kp>0){PM.marks.set(k0,{born:performance.now(),b:true,m:PM.mat});more.add(k0);act.add.push(k0);n++;continue}   /* upstairs: the floor is blocks over the room below, held by the walls (phase 3) */if(PM.tool==='door')for(const [kq,mq] of [...PM.marks])if(mq.b&&kq.startsWith(x+','+y+',')&&(+kq.split(',')[2]===kp||+kq.split(',')[2]===kp+1))delMark(act,kq);   /* its storey's two levels: a wall over it stays, held (phase 3) */PM.marks.set(k0,{born:performance.now(),b:false,t:PM.tool,k:kp,m:PM.tool==='floor'?PM.mat:null});more.add(k0);act.add.push(k0);n++;continue}
  if(!markable(PM.tool,x,y,k,more))continue;PM.marks.set(kk,{born:performance.now(),b:PM.tool==='build',m:PM.tool==='build'?PM.mat:null});more.add(kk);act.add.push(kk);n++}
 if(n)PM.undo.push(act);else shake();if(PM.undo.length>60)PM.undo.shift();card();tag();return n}
// an undo puts back what it took away as it was (a dig or a build mark)
function delMark(act,kk){act.del.push([kk,PM.marks.get(kk)]);PM.marks.delete(kk)}
function undo(){const a=PM.undo.pop();if(!a){shake();return}for(const kk of a.add)PM.marks.delete(kk);for(const [kk,m] of a.del)PM.marks.set(kk,Object.assign({b:false,m:null},m||{},{born:performance.now()}));card();tag()}
// one plan of each kind and material marked: the dig marks, the stone build marks, the wood build marks; whole columns
// at most PLANMAX blocks a plan (a block's support stays in its plan), more plans for a bigger queue, never cut
function queue(){if(!PM.marks.size){shake();return}const dig=[],st=[],wd=[],dr=[],fs=[],fw=[],sp=[];for(const [kk,m] of PM.marks){if(m.st)sp.push(kk+','+m.st);   /* a step of a building's stairs: x,y,k,the way it rises */const xy=kk.split(',').slice(0,2).join(',');if(m.t==='door'){dr.push(m.k?kk:xy);continue}   /* upstairs: x,y,k (an opening) */if(m.t==='floor'){(m.m==='wood'?fw:fs).push(xy);continue}(m.b?(m.m==='wood'?wd:st):dig).push(kk)}
 const go=(a,tail)=>{const col=new Map();for(const kk of a){const p=kk.split(','),c=p[0]+','+p[1];if(!col.has(c))col.set(c,[]);col.get(c).push(kk)}
  let cur=[];const out=[];for(const v of col.values()){if(cur.length&&cur.length+v.length>PLANMAX){out.push(cur);cur=[]}cur=cur.concat(v)}if(cur.length)out.push(cur);
  for(const c of out)send('planadd',PM.prio+'|'+c.join('/')+tail);return out.length};
 PM.queued=go(dig,'')+go(st,'|build|stone')+go(wd,'|build|wood');if(sp.length)send('planstep',sp.join('/'));if(dr.length)send('plandoor',dr.join('/'));if(fs.length)send('planfloor','stone|'+fs.join('/'));if(fw.length)send('planfloor','wood|'+fw.join('/'));PM.queued+=(dr.length?1:0)+(fs.length?1:0)+(fw.length?1:0);
 PM.sent=new Map([...dig.map(k=>[k,0]),...st.map(k=>[k,1]),...wd.map(k=>[k,2])]);PM.sentAt=performance.now();PM.marks.clear();PM.undo.length=0;card();tag()}
function shake(){PM.shakeAt=performance.now();const t=$('pmTag');if(t){t.classList.remove('pmshake');void t.offsetWidth;t.classList.add('pmshake')}}
function setLevel(l){PM.level=Math.max(0,Math.min(15,l));const e=$('pmLvl');if(e)e.textContent='Level '+PM.level+' · storey '+(Math.floor(PM.level/SL)+1);card();tag()}
function setTool(t){if(t!==PM.tool&&PM.on){if(t==='floor')setShape('box');else if(t==='door')setShape('single');else if(t==='building'&&!PM.hSet)PM.height=BKIND[PM.bk||'house'].h}PM.tool=t;   /* a floor fills, a door is one tile (play test) */document.querySelectorAll('#pmBar [data-pmtool]').forEach(b=>b.classList.toggle('on',b.dataset.pmtool===t));card();tag()}
function setMat(m){PM.mat=m==='wood'?'wood':'stone';card();tag()}
function setShape(s){PM.shape=s;document.querySelectorAll('#pmBar [data-pmshape]').forEach(b=>b.classList.toggle('on',b.dataset.pmshape===s));tag()}
function setOn(on){if(on&&V3.z!==1){if(typeof toast==='function')toast('Plan mode works on the surface view for now.');return}PM.on=on;PM.drag=null;V3.planCut=on?PM.level+SLAB:null;if(on&&!PM.designs){PM.designs=[];send('pmdesign','list')}   /* the saved designs, once */
 ['pmBar','pmCard','pmKeys','pmTag'].forEach(id=>{const e=$(id);if(e)e.hidden=!on});const b=$('btnPlan');if(b)b.setAttribute('aria-pressed',String(on));
 if(on){const s=V3.things&&V3.things.find(t=>t.kind==='mine'&&t.selected);if(s){PM.cx=s.x;PM.cy=s.y;setLevel(s.ly>0?(s.feet!=null?s.feet:Math.round(s.ly)):0)}else{PM.cx=Math.round(V3.cx);PM.cy=Math.round(V3.cy);setLevel(PM.level)}}
 card();tag()}
// The Place list's Structure and the card's list (build-menu-one): Plan mode on with this tool and material.
window.pmUse=function(tool,mat){if(!$('pmBar')){build();hookInput()}if(!PM.on)setOn(true);if(!PM.on)return;setTool(tool);if(mat)setMat(mat);if(tool==='build'){setShape('outline');if(!PM.hSet)PM.height=2;card()}};   /* a wall: an outline, two high (play test) */
function move(f,r){const F=fwd(),Rt=[F[1],-F[0]];PM.cx+=F[0]*f+Rt[0]*r;PM.cy+=F[1]*f+Rt[1]*r;if(PM.drag)PM.drag.moved=true;tag()}
// ---------- the HUD: the bar, the plan card (with the plans queued), the key strip, the tag over the cursor ----------
function build(){if($('pmBar'))return;const st=document.createElement('style');st.textContent=
 '.pmp{position:fixed;z-index:60;background:var(--mpane,#141d2b);border:1px solid var(--mband,#34465f);border-radius:6px;box-shadow:0 2px 10px #0008;color:var(--mink,#ece3cc);font-size:12px}'+
 '.pmp button{font:inherit;color:inherit;background:#ffffff0d;border:1px solid var(--mband,#34465f);border-radius:4px;padding:3px 8px;cursor:pointer}.pmp button:hover{filter:brightness(1.25)}.pmp button.on{border-color:var(--macc,#d9b45f);color:#fff;background:#ffffff1f}'+
 '.pmp .t{font-family:var(--mfont,HudText,Georgia,serif);color:var(--macc,#d9b45f);font-size:15px}.pmp .s{color:#ffffffa0;font-size:11px}.pmp kbd{font:600 10px HudText,Georgia,serif;border:1px solid var(--mband,#34465f);border-radius:3px;padding:0 3px;margin-left:4px;color:var(--macc,#d9b45f)}'+
 '#pmBar{top:46px;left:50%;transform:translateX(-50%);display:flex;gap:5px;align-items:center;padding:6px 8px}#pmBar i{width:1px;height:20px;background:var(--mband,#34465f);margin:0 3px}'+
 '#pmCard{left:8px;top:150px;width:236px;padding:9px 11px 0;max-height:calc(100vh - 245px);overflow-y:auto}#pmCard .r{display:flex;justify-content:space-between;padding:3px 0;border-top:1px solid #ffffff14}#pmCard .r span:first-child{color:#ffffffa0}#pmCard .a{display:flex;gap:6px;margin-top:8px;position:sticky;bottom:0;padding:6px 0 9px;background:var(--mpane,#141d2b)}#pmCard .a button{flex:1}'+
 '.sitetag{position:fixed;transform:translate(-50%,-100%);background:rgba(20,29,43,.9);border:1px solid var(--mband,#34465f);border-radius:5px;padding:2px 8px;font:11px var(--mfont,HudText,Georgia,serif);color:#ffffffc0;white-space:nowrap;box-shadow:0 2px 6px #0007}.sitetag b{color:var(--macc,#d9b45f);font-weight:600}.sitetag .need{color:#f0a090}.sitetag{pointer-events:auto;cursor:pointer}.sitetag .bar{display:block;height:3px;margin-top:2px;background:#0007;border-radius:2px;overflow:hidden}.sitetag .bar i{display:block;height:100%;background:var(--macc,#d9b45f)}.ocard.flash{outline:2px solid var(--macc,#d9b45f);outline-offset:1px}'+
 '#pmCard .wb{display:grid;grid-template-columns:1fr 1fr;gap:4px;margin:7px 0 5px}#pmCard .wb button{display:flex;flex-direction:column;align-items:flex-start;text-align:left;padding:3px 6px;line-height:1.2}#pmCard .wb small{color:#ffffffa0;font-size:10px}'+
 '#pmCard .dl{margin:4px 0 6px}#pmCard .dr{display:flex;gap:4px;align-items:stretch;margin:3px 0}#pmCard .dr button[data-pmdpick]{flex:1;display:flex;flex-direction:column;align-items:flex-start;text-align:left;line-height:1.2}#pmCard .dr small{color:#ffffffa0;font-size:10px}#pmCard .dr .s{align-self:center}'+
 '#pmCard .sv{display:flex;gap:4px;flex:0 0 100%}#pmCard .a{flex-wrap:wrap}#pmCard .sv button{flex:1}#pmCard .sv input{flex:1;min-width:0;font:inherit;color:inherit;background:#0006;border:1px solid var(--mband,#34465f);border-radius:4px;padding:3px 6px}#pmCard .sv input~button{flex:0 0 auto}'+
 '#pmCard .q{border-top:1px solid #ffffff14;padding:5px 0}#pmCard .q .bar{height:5px;background:#0006;border-radius:3px;margin:4px 0;overflow:hidden}#pmCard .q .bar b{display:block;height:100%;background:var(--macc,#d9b45f)}'+
 '#pmKeys{left:50%;bottom:92px;transform:translateX(-50%);padding:5px 10px;color:#ffffffa8;font-size:11px;white-space:nowrap}#pmKeys b{color:var(--mink,#ece3cc);font-weight:500}'+
 '#pmTag{position:fixed;z-index:61;pointer-events:none;transform:translate(-50%,-150%);padding:2px 8px;font-size:11px;white-space:nowrap}#pmTag.bad{border-color:#e2685a;color:#f6c8c0}#pmTag.pmshake{animation:pmshake .3s}'+
 '@keyframes pmshake{0%,100%{margin-left:0}25%{margin-left:-6px}50%{margin-left:5px}75%{margin-left:-3px}}#btnPlan{--ico:var(--hci-tasks)}';document.head.appendChild(st);
 const bar=document.createElement('div');bar.id='pmBar';bar.className='pmp';bar.hidden=true;
 bar.innerHTML='<button data-pmtool="building" title="Building: drag its size; a house, hall, tower or wall is laid out for you: its walls, a door facing your people, the floor (7)">Building</button><button data-pmtool="design" title="Designs: your saved buildings, placed again anywhere, turned (8)">Designs</button><button data-pmtool="dig" title="Dig: mark the blocks a shape covers on this level (1)">Dig</button><button data-pmtool="build" title="Build: blocks to lay where there are none, on open ground or on a block under it; one stone or one log each (Stone | Wood on the card, M) (2)">Build</button><button data-pmtool="clear" title="Clear: everything from this level up inside the shape, a clean floor here (3)">Clear</button><button data-pmtool="erase" title="Erase: take marks away (4)">Erase</button><button data-pmtool="door" title="Door: a doorway in a wall line, on the ground; its door is made at the carpentry and hung once the walls beside it are up (5)">Door</button><button data-pmtool="floor" title="Floor: floor tiles on the ground, in stone or wood (Stone | Wood on the card, M); the builders lay them (6)">Floor</button><i></i>'+
  '<button data-pmshape="single">Single</button><button data-pmshape="line">Line</button><button data-pmshape="box">Box</button><button data-pmshape="outline">Outline</button><i></i>'+
  '<button id="pmDn" title="Level down (PageDown)">&#9660;</button><span id="pmLvl" style="min-width:58px;text-align:center">Level 0</span><button id="pmUp" title="Level up (PageUp)">&#9650;</button><i></i><button id="pmDone" title="Leave Plan mode (Esc)">Done<kbd>Esc</kbd></button>';
 document.body.appendChild(bar);
 const cd=document.createElement('div');cd.id='pmCard';cd.className='pmp';cd.hidden=true;document.body.appendChild(cd);
 cd.addEventListener('keydown',e=>{if(e.target.id!=='pmName')return;e.stopPropagation();if(e.key==='Enter'){e.preventDefault();const b=$('pmSaveOk');if(b)dClick(b)}else if(e.key==='Escape'){e.preventDefault();PM.naming=null;card()}});   /* a design's name: its keys are the box's */
 const ks=document.createElement('div');ks.id='pmKeys';ks.className='pmp';ks.hidden=true;ks.innerHTML='<b>Click</b> / <b>drag</b>: mark · <b>Height</b> on the card (or the <b>wheel</b> while dragging) · <b>right-click</b>: unmark · <b>M</b>: stone / wood · <b>arrows</b>: move · <b>PageUp</b>/<b>PageDown</b>: level · <b>Esc</b>: done';document.body.appendChild(ks);
 const tg=document.createElement('div');tg.id='pmTag';tg.className='pmp';tg.hidden=true;document.body.appendChild(tg);
 bar.addEventListener('click',e=>{const t=e.target.closest('[data-pmtool]');if(t)return setTool(t.dataset.pmtool);const s=e.target.closest('[data-pmshape]');if(s)return setShape(s.dataset.pmshape);
  if(e.target.closest('#pmUp'))setLevel(PM.level+1);if(e.target.closest('#pmDn'))setLevel(PM.level-1);if(e.target.closest('#pmDone'))setOn(false)});
 cd.addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;if(dClick(b))return;if(b.id==='pmQueue')queue();else if(b.id==='pmClear'){const a={add:[],del:[...PM.marks.entries()]};if(a.del.length)PM.undo.push(a);PM.marks.clear();card();tag()}else if(b.id==='pmPrio'){PM.prio=PM.prio%3+1;card()}
  else if(b.dataset.pmmat)setMat(b.dataset.pmmat);else if(b.dataset.pmst!=null&&b.dataset.pmst!==''){setLevel(+b.dataset.pmst)}else if(b.dataset.pmbk){PM.bk=b.dataset.pmbk;if(!PM.hSet)PM.height=BKIND[PM.bk].h;card();tag()}else if(b.dataset.pmdoor){const o=['auto'].concat(BSIDE),i=o.indexOf(PM.door||'auto');PM.door=o[(i+1)%o.length];card()}else if(b.dataset.pmsy){PM.storeys=Math.max(1,Math.min(3,(PM.storeys||1)+(+b.dataset.pmsy)));card();tag()}else if(b.dataset.pmh){PM.height=Math.max(1,Math.min(8,(PM.height||1)+(+b.dataset.pmh)));PM.hSet=1;card();tag()}else if(b.dataset.pmuse){const [t0,m0]=b.dataset.pmuse.split('|');if(t0==='build'){pmUse(t0,m0);return}const [t,mt]=b.dataset.pmuse.split('|');setTool(t);if(mt)setMat(mt)}else if(b.dataset.pmrow)send('jobrow',b.dataset.pmrow)});
 // the dock button, beside Gather
 const g=$('btnGather');if(g&&!$('btnPlan')){const b=document.createElement('button');b.id='btnPlan';b.setAttribute('aria-pressed','false');b.title='Plan mode\nMark blocks to dig or build, level by level, and queue them: the job board\'s villagers dig and build them by themselves.';b.innerHTML='<b class="gear pick">&#9776;</b><span>Plan</span>';b.addEventListener('click',e=>{e.stopPropagation();setOn(!PM.on)});g.after(b)}
 setTool('dig');setShape('box')}
const PRIO=['','High','Normal','Low'];
const blocks=n=>n+' block'+(n>1?'s':'');
function card(){const cd=$('pmCard');if(!cd||!PM.on)return;if(PM.naming&&document.activeElement&&document.activeElement.id==='pmName')return;   /* not while a design's name is typed */const n=PM.marks.size;let nb=0,nw=0,np=0,nfs=0,nfw=0;for(const m of PM.marks.values()){if(m.t){np++;if(m.t==='floor'){if(m.m==='wood')nfw++;else nfs++}}else if(m.b){nb++;if(m.m==='wood')nw++}}const nd=n-nb-np,ndr=np-nfs-nfw,nfl=nfs+nfw,short=(v,h)=>h==null?String(v):v>h?'<span style="color:#f0a090" title="Your stores hold '+h+': the board gets an order for the rest when the builders run out">'+v+' (have '+h+')</span>':v+' (have '+h+')';
 const WB=[['building','','Building','house, hall, tower, wall'],['design','','Designs','your saved buildings'],['build','stone','Stone wall','1 stone a block'],['build','wood','Wooden wall','1 log a block'],['door','','Door','from the carpentry'],['floor','stone','Stone floor','1 stone a tile'],['floor','wood','Wooden floor','1 log a tile'],['dig','','Dig','gives stone']],ps=arr(model&&model.planStock);const wb='<div class="wb">'+WB.map(([t,mt,l,c])=>'<button data-pmuse="'+t+'|'+mt+'"'+(PM.tool===t&&(!mt||PM.mat===mt)?' class="on"':'')+'><b>'+l+'</b><small>'+c+'</small></button>').join('')+'</div>'+(ps.length?'<div class="s">In your stores: '+ps[0]+' stone · '+ps[1]+' logs</div>':'');
 const mb=(m,t)=>'<button data-pmmat="'+m+'"'+(PM.mat===m?' class="on"':'')+' title="'+t+' (M)">'+m[0].toUpperCase()+m.slice(1)+'</button>';
 const rows=[['To dig',nd?blocks(nd):'none'],['To build',nb?blocks(nb):'none'],...(ndr?[['Doors',ndr+' (from the carpentry)']]:[]),...(nfl?[['Floor',nfl+' tile'+(nfl>1?'s':'')]]:[]),['Stone needed',short(nb-nw+nfs,ps[0])],['Wood needed',short(nw+nfw,ps[1])],['Storey','<span style="display:flex;gap:3px">'+[1,2,3].map(s=>'<button data-pmst="'+(s-1)*SL+'"'+(Math.floor(PM.level/SL)+1===s?' class="on"':'')+' title="Storey '+s+': levels '+(s-1)*SL+' to '+((s-1)*SL+SL-1)+(s>1?', on its floor at level '+((s-1)*SL-1):'')+'">'+s+'</button>').join('')+'</span>'],['On it',(()=>{const b0=stB(PM.level);let mk=0,qd=0;for(const kk of PM.marks.keys()){const k=+kk.split(',')[2];if(k>=b0&&k<b0+SL)mk++}if(PM.qset)for(const kk of PM.qset.keys()){const k=+kk.split(',')[2];if(k>=b0&&k<b0+SL)qd++}return mk+' marked · '+qd+' queued'})()],...(PM.tool==='building'?[['Kind','<span style="display:flex;gap:3px;flex-wrap:wrap;justify-content:flex-end">'+Object.keys(BKIND).map(k=>'<button data-pmbk="'+k+'"'+((PM.bk||'house')===k?' class="on"':'')+'>'+BKIND[k].l+'</button>').join('')+'</span>'],['Door','<button data-pmdoor="1" title="The side its door is on: Auto faces your people">'+((PM.door||'auto')==='auto'?'Auto':(PM.door[0].toUpperCase()+PM.door.slice(1)))+' ↻</button>']]:[]),...(PM.tool==='building'&&BKIND[PM.bk||'house'].min?[['Storeys','<span style="display:flex;gap:4px;align-items:center"><button data-pmsy="-1" title="One storey less">−</button><b>'+(PM.storeys||1)+'</b><button data-pmsy="1" title="One storey more: a floor over the one under it, held by the walls, and stairs up">+</button></span>']]:[]),...(PM.tool==='build'||PM.tool==='building'?[['Height','<span style="display:flex;gap:4px;align-items:center"><button data-pmh="-1" title="Lower: one block less">−</button><b>'+(PM.height||1)+'</b><button data-pmh="1" title="Higher: one block more (a drag lays it this high)">+</button></span>']]:[]),['Build in','<span style="display:flex;gap:4px">'+mb('stone','Build in stone: one stone a block')+mb('wood','Build in wood: one log a block')+'</span>'],['Priority','<button id="pmPrio" title="Priority on the job board">'+PRIO[PM.prio]+'</button>']];
 if(PM.tool==='building'){const pri=['Kind','Storeys','Height','Door','Build in'];rows.sort((a,b)=>(pri.indexOf(a[0])+1||99)-(pri.indexOf(b[0])+1||99))}   /* the Building tool's own controls first: at 720 high the rest was out of sight (played in the browser, 10-30) */
 let h='<div class="t">'+(nd&&(nb||np)?'Dig and build plan':(nb||np)?'Build plan':nd?'Dig plan':'Plan')+'</div><div class="s">'+(n?'Not queued yet: Queue it puts it on the job board':PM.tool==='design'?(PM.dPick?'Move it where it goes and click: its blocks are marked there, to queue':'Your saved buildings: pick one to place it, on the storey you look at'):PM.tool==='building'?'Drag a '+BKIND[PM.bk||'house'].l.toLowerCase()+'\'s size: its walls, door'+((PM.storeys||1)>1&&BKIND[PM.bk||'house'].min?', floors and stairs are laid out for you, storey by storey':' and floor are laid out for you'):PM.tool==='door'?'Mark doors in wall lines, on the ground':PM.tool==='floor'?(stB(PM.level)?'Mark storey '+(stB(PM.level)/SL+1)+'\'s floor: '+PM.mat+' blocks over the room below, held by walls within 3 tiles':'Mark floor tiles on the ground ('+PM.mat+')'):'Mark blocks on level '+PM.level+' to '+({dig:'dig',build:'build',clear:'clear',erase:'unmark'})[PM.tool])+'</div>'+wb+dCard()+rows.map(([a,b])=>'<div class="r"><span>'+a+'</span><span>'+b+'</span></div>').join('')+
  '<div class="a">'+dSaveRow(nb)+'<button id="pmQueue"'+(n?'':' disabled')+'>Queue it</button><button id="pmClear"'+(n?'':' disabled')+'>Clear</button></div>';
 const P=arr(model&&model.plans);if(P.length)h+='<div class="t" style="font-size:13px;margin-top:9px">Plans</div>'+P.map(p=>'<div class="q"><div style="display:flex;justify-content:space-between"><span>'+p.name+'</span><span class="s">'+(p.total-p.left)+'/'+p.total+'</span></div><div class="bar"><b style="width:'+Math.round(100*(p.total-p.left)/Math.max(1,p.total))+'%"></b></div><div class="s">Level '+p.levels+' · '+PRIO[p.prio]+' · '+(p.count?p.count+' at work · ':'')+String(p.status||'').replace(/^(Dig|Build) \d+: /,'')+'</div>'+
  '<div style="display:flex;gap:4px;margin-top:3px"><button data-pmrow="'+p.id+'|pause">'+(p.paused?'Go on':'Pause')+'</button><button data-pmrow="'+p.id+'|prio|'+Math.max(1,p.prio-1)+'" title="Priority up">&#9650;</button><button data-pmrow="'+p.id+'|look" title="Go to it">Go to</button><button data-pmrow="'+p.id+'|remove" title="Remove the plan">&#10005;</button></div></div>').join('');
 if(cd.dataset.h!==h){cd.dataset.h=h;cd.innerHTML=h}}
function tag(){const t=$('pmTag');if(!t||!PM.on)return;const x=PM.cx,y=PM.cy,k=PM.level,kk=key(x,y,k);let txt,bad=false;
 if(PM.tool==='design'){const D=dCur();txt=D?D.name+' · '+D.w+' × '+D.h+' · '+blocks(D.nb)+' · click: place it here'+(PM.dNote?' ('+PM.dNote+')':''):'Designs: pick one on the card';bad=!D}else
 if(PM.drag&&PM.drag.moved&&PM.tool==='building'){txt=BKIND[PM.bk||'house'].l+' · '+bLayout(PM.drag.a,[x,y]).note}else if(PM.drag&&PM.drag.moved){const a=PM.drag.a,w=Math.abs(x-a[0])+1,h=Math.abs(y-a[1])+1,lv=Math.abs(k-PM.drag.k0)+1,n=dragCells().length;txt=(PM.tool==='clear'?'Clear '+w+' × '+h+' · level '+Math.min(k,PM.drag.k0)+' and up':PM.shape[0].toUpperCase()+PM.shape.slice(1)+' '+w+' × '+h+(lv>1?' × '+lv+' levels':''))+' · '+n+' block'+(n===1?'':'s');bad=!n}
 else{const what=has(x,y,k)?'a block':has(x,y,k-1)||k===0?'open floor':'open air';let act;if(PM.tool==='building')act='drag a '+BKIND[PM.bk||'house'].l.toLowerCase()+'\'s size (a click: one here)';else if(PM.marks.has(kk)&&!(piece(PM.tool)&&PM.marks.get(kk).b))act='marked (click: unmark)';else if(piece(PM.tool)&&k>=SL){if(PM.tool==='floor'){const fk=stB(k)-1;if(PM.marks.has(key(x,y,fk)))act='a floor block marked here';else if(pieceOK('floor',x,y,fk))act='click: a '+PM.mat+' floor here, a block at level '+fk+' over the room below';else{act=has(x,y,fk)?'a floor or a wall is there already':held(x,y,fk,null,true)?'drag from the wall: a floor up here is held by the walls within 3 tiles, through the floor laid between':'nothing holds a floor here: walls or a pillar within 3 tiles';bad=true}}else if(pieceOK('door',x,y,stB(k)))act='click: an opening in the wall here (a doorway upstairs, no door)';else{act='an opening goes in a wall still to be built';bad=true}}
  else if(piece(PM.tool)){const m0=PM.marks.get(key(x,y,0));if(m0&&m0.t)act=(m0.t==='door'?'a door':'floor')+' marked here';else if(has(x,y,0)){act='a block is there: a '+PM.tool+' goes on open ground';bad=true}else if(arr(V3.pdoors).some(d=>d[0]===x&&d[1]===y))act='a door is planned here';else if(PM.tool==='floor'&&queued(x,y,0)){act='a wall is planned here';bad=true}else act=PM.tool==='door'?'click: a door here (hung once the walls beside it are up)':'click: a '+PM.mat+' floor tile here'}else if(queued(x,y,k))act=qbuild(x,y,k)?'queued to build in '+(PM.qset.get(kk)===2?'wood':'stone'):'queued to dig';else if(PM.tool==='erase')act='nothing marked here';
  else if(PM.tool==='build'){if(canBuild(x,y,k))act='click: build a '+PM.mat+' block here';else{act=has(x,y,k)?'a block is there already':'nothing to build on here';bad=true}}
  else if(has(x,y,k))act='click: mark '+(PM.tool==='clear'?'this column from here up':'it');else{act='nothing to dig here';bad=true}
  txt='Level '+k+' · '+what+' · '+act}
 if(t.textContent!==txt)t.textContent=txt;t.classList.toggle('bad',bad);PM.bad=bad}
// ---------- input: the 3D view's mouse while Plan mode is on (the right button still pans), the game's keys ----------
function hookInput(){const c=$('world3d');if(!c||c.dataset.pm)return;c.dataset.pm='1';
 c.addEventListener('mousedown',e=>{if(!PM.on)return;if(e.button===0){e.stopImmediatePropagation();e.preventDefault();const p=pick(mx(e),my(e));if(p){PM.cx=p[0];PM.cy=p[1]}PM.drag={a:[PM.cx,PM.cy],k0:PM.level,moved:false};tag()}else if(e.button===2)PM.rdown={x:e.clientX,y:e.clientY}},true);
 addEventListener('mousemove',e=>{if(!PM.on||!(e.target===c||PM.drag))return;const p=pick(mx(e),my(e));if(p&&(p[0]!==PM.cx||p[1]!==PM.cy)){PM.cx=p[0];PM.cy=p[1];if(PM.drag)PM.drag.moved=true;tag()}},true);
 addEventListener('mouseup',e=>{if(!PM.on)return;
  if(e.button===0&&PM.drag&&PM.tool==='design'){e.stopImmediatePropagation();PM.drag=null;dPlace();return}
  if(e.button===0&&PM.drag&&PM.tool==='building'){e.stopImmediatePropagation();const d=PM.drag;PM.drag=null;bPlace(d.moved?bLayout(d.a,[PM.cx,PM.cy]):bLayout([PM.cx-2,PM.cy-2],[PM.cx+3,PM.cy+2]));return}
  if(e.button===0&&PM.drag){e.stopImmediatePropagation();const d=PM.drag,cells=d.moved?dragCells():null;PM.drag=null;if(cells)apply(cells);else{const kk=key(PM.cx,PM.cy,PM.level);if(PM.marks.has(kk)&&!(piece(PM.tool)&&PM.marks.get(kk).b)){const act={add:[],del:[]};delMark(act,kk);PM.undo.push(act);card();tag()}else apply(PM.tool==='clear'?shapeCells([PM.cx,PM.cy],null,PM.level,PM.level,'single','clear'):PM.tool==='build'?Array.from({length:PM.height||1},(_,i)=>[PM.cx,PM.cy,PM.level+i]):[[PM.cx,PM.cy,PM.level]])}return}
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
  else if(k==='r'||k==='pageup')setLevel(PM.level+1);else if(k==='f'||k==='pagedown')setLevel(PM.level-1);else if(k==='m')setMat(PM.mat==='wood'?'stone':'wood');else if(k==='1')setTool('dig');else if(k==='2')setTool('build');else if(k==='3')setTool('clear');else if(k==='4')setTool('erase');else if(k==='5')setTool('door');else if(k==='6')setTool('floor');else if(k==='7')setTool('building');else if(k==='8')setTool('design');
  else if(k===' '&&PM.tool==='design')dPlace();else if(k===' '&&PM.tool==='building')bPlace(bLayout([PM.cx-2,PM.cy-2],[PM.cx+3,PM.cy+2]));else if(k===' '){const kk=key(PM.cx,PM.cy,PM.level);if(PM.marks.has(kk)&&!(piece(PM.tool)&&PM.marks.get(kk).b)){const act={add:[],del:[]};delMark(act,kk);PM.undo.push(act);card();tag()}else apply([[PM.cx,PM.cy,PM.level]])}else if(k==='enter')queue();else if(k==='escape'){if(PM.drag){PM.drag=null;tag()}else setOn(false)}else done=false;
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
// ---------- construction sites (construction-3d, 10-30): a build plan as a construction site, as in Songs of Syx ----------
// Sites.dm: the stone or logs for a plan are carried to a pile beside it first, then the walls go up from there. Drawn
// here: the pile (cut stone stacked on a pallet, or logs in a stack, as much as lies there), stakes and string round the
// plan while its ground course goes in, scaffolding against the outer face of each column still going up (its deck
// where the next block goes, rising with the wall, gone from a column once its top block is in), and a block being laid
// rising with each blow (the worker's "lay" record, View3D.dm). The still parts are built once per change and kept.
const SITE={v:[]},SCOL={pole:[0.46,0.33,0.19,1],plank:[0.63,0.49,0.31,1],plank2:[0.56,0.42,0.26,1],rope:[0.88,0.82,0.64,1],stake:[0.5,0.36,0.2,1],pallet:[0.45,0.34,0.21,1],bark:[0.33,0.22,0.12,1],cut:[0.74,0.6,0.4,1]};
function sbox(a,x,y0,z,hx,hy,hz,c){const y1=y0+hy*2,x0=x-hx,x1=x+hx,z0=z-hz,z1=z+hz,s=lit(c,0.8),e=lit(c,0.9);   // a box: its top and four sides
 quad(a,[x0,y1,z1],[x1,y1,z1],[x1,y1,z0],[x0,y1,z0],[0,1,0],c);quad(a,[x0,y0,z1],[x1,y0,z1],[x1,y1,z1],[x0,y1,z1],[0,0,1],e);quad(a,[x1,y0,z0],[x0,y0,z0],[x0,y1,z0],[x1,y1,z0],[0,0,-1],e);
 quad(a,[x1,y0,z1],[x1,y0,z0],[x1,y1,z0],[x1,y1,z1],[1,0,0],s);quad(a,[x0,y0,z0],[x0,y0,z1],[x0,y1,z1],[x0,y1,z0],[-1,0,0],s)}
const sjit=(c,s)=>{const f=0.92+0.16*MD.h(s,3,17);return [Math.min(1,c[0]*f),Math.min(1,c[1]*f),Math.min(1,c[2]*f),1]};
// a log lying from p0 to p1: its bark and its two cut ends
function slog(a,p0,p1,r,s){MD.rod(a,p0,p1,r,6,sjit(SCOL.bark,s),s);const d=[p1[0]-p0[0],p1[2]-p0[2]],L=Math.hypot(d[0],d[1])||1,u=[d[0]/L,d[1]/L];
 for(const [p,sg] of [[p0,-1],[p1,1]]){const n=[u[0]*sg,0,u[1]*sg],px=-u[1]*r*0.92,pz=u[0]*r*0.92,o=[p[0]+n[0]*0.004,p[1],p[2]+n[2]*0.004];
  quad(a,[o[0]-px,o[1]-r*0.92,o[2]-pz],[o[0]+px,o[1]-r*0.92,o[2]+pz],[o[0]+px,o[1]+r*0.92,o[2]+pz],[o[0]-px,o[1]+r*0.92,o[2]-pz],n,sjit(SCOL.cut,s+sg));quad(a,[o[0]-px,o[1]+r*0.92,o[2]-pz],[o[0]+px,o[1]+r*0.92,o[2]+pz],[o[0]+px,o[1]-r*0.92,o[2]+pz],[o[0]-px,o[1]-r*0.92,o[2]-pz],n,sjit(SCOL.cut,s+sg))}}
// the pile: stone as cut blocks three by three on a pallet, layer on layer (54 at most shown); logs in a stack of rows,
// six at the bottom (21 at most shown)
function sitePile(a,S){const [px,py,wood,stock]=S;if(!(stock>0)||!(px||py))return;const G=v3groundAt(px,py),X=px,Z=-py;
 if(wood){const n=Math.min(stock,21);let i=0;for(let r=0;r<6&&i<n;r++)for(let c=0;c<6-r&&i<n;c++,i++){const z=Z+(c-(5-r)/2)*0.15,y=G+0.075+r*0.13,j=(MD.h(px+c,py+r,5)-0.5)*0.08;slog(a,[X-0.4+j,y,z],[X+0.4+j,y,z],0.072,px*7+py*3+i)}return}
 sbox(a,X,G,Z,0.46,0.025,0.46,SCOL.pallet);const n=Math.min(stock,54);
 for(let i=0;i<n;i++){const L=Math.floor(i/9),q=i%9,cx=(q%3-1)*0.29+(MD.h(i,px,7)-0.5)*0.03,cz=(Math.floor(q/3)-1)*0.29+(MD.h(i,py,9)-0.5)*0.03;sbox(a,X+cx,G+0.05+L*0.16,Z+cz,0.125,0.075,0.125,sjit(V3LAID.stone,px*13+py*5+i))}}
// stakes at the plan's corners and string between them, while its ground course is going in
function siteStakes(a,S){const x0=S[6]-0.5,y0=S[7]-0.5,x1=S[8]+0.5,y1=S[9]+0.5,c=[[x0,y0],[x1,y0],[x1,y1],[x0,y1]],top=[];
 for(const [x,y] of c){const G=v3groundAt(Math.round(x),Math.round(y));sbox(a,x,G,-y,0.028,0.21,0.028,SCOL.stake);top.push([x,G+0.33,-y])}
 for(let i=0;i<4;i++)v3beam4(a,top[i],top[(i+1)%4],0.007,SCOL.rope)}
// one bay of scaffolding against a column's outer face: two poles, the deck where the next block goes, a rail, a brace
function siteBay(a,x,y,dx,dy,deck){const G=v3groundAt(x+dx,y+dy),cx=x+dx*0.8,cy=y+dy*0.8,ax=dx?0:0.5,ay=dy?0:0.5,top=G+deck+1.0;
 const P=[[cx-ax,cy-ay],[cx+ax,cy+ay]];for(const [px,py] of P)sbox(a,px,G,-py,0.024,(top-G)/2,0.024,SCOL.pole);
 const hx=dx?0.13:0.5,hz=dy?0.13:0.5;sbox(a,cx,G+deck-0.04,-cy,hx,0.018,hz,SCOL.plank);sbox(a,cx+(dx?0.06:0),G+deck-0.036,-cy-(dy?0.06:0),dx?0.06:0.47,0.018,dy?0.06:0.47,SCOL.plank2);
 v3beam4(a,[P[0][0],top-0.1,-P[0][1]],[P[1][0],top-0.1,-P[1][1]],0.014,SCOL.pole);v3beam4(a,[P[0][0],G+0.1,-P[0][1]],[P[1][0],G+deck-0.05,-P[1][1]],0.012,SCOL.pole)}
function siteBuild(){const v=[],Q=arr(V3.planCells),S=arr(V3.sites),cols=new Map();
 for(const c of Q)if(c[4]===1){const kk=c[0]+','+c[1];const o=cols.get(kk);if(!o)cols.set(kk,{x:c[0],y:c[1],lo:c[2]});else if(c[2]<o.lo)o.lo=c[2]}
 for(const d of arr(V3.pdoors))try{siteDoor(v,d[0],d[1],d[2]===1,DOORCOL)}catch(e){}   /* doors waiting for their walls (PlanPieces.dm) */
 for(const s of S){try{sitePile(v,s);let ground=false;for(const o of cols.values())if(o.lo===0&&o.x>=s[6]&&o.x<=s[8]&&o.y>=s[7]&&o.y<=s[9]){ground=true;break}if(ground)siteStakes(v,s)}catch(e){}}
 for(const o of cols.values()){if(o.lo<1||!has(o.x,o.y,o.lo-1))continue;   // a column going up: its next block sits on a laid one
  const st=S.find(s=>o.x>=s[6]&&o.x<=s[8]&&o.y>=s[7]&&o.y<=s[9]),inn=(x,y)=>st&&x>st[6]&&x<st[8]&&y>st[7]&&y<st[9];
  for(const [dx,dy] of [[1,0],[-1,0],[0,1],[0,-1]]){const nx=o.x+dx,ny=o.y+dy;if(cols.has(nx+','+ny)||has(nx,ny,0)||inn(nx,ny))continue;try{siteBay(v,o.x,o.y,dx,dy,o.lo)}catch(e){}}}   /* the outer faces only: never inside its plan */
 return v}
// a block being laid: it rises with each blow (eased between them), stone in two courses, logs one by one
function siteLay(a,t,now){const L=t.lay;if(!Array.isArray(L)||L.length<6)return;const [x,y,k,b,need,wood]=L,key=L.join(',');if(t._layK!==key){t._layK=key;t._layAt=now}
 const f=Math.max(0.08,Math.min(1,(b+Math.min(1,(now-t._layAt)/650))/Math.max(1,need))),B=v3groundAt(x,y)+k,X=x,Z=-y;
 if(wood){for(let i=0;i<3;i++){const lo=i/3;if(f<=lo)break;const p=Math.min(1,(f-lo)*3),y0=B+0.165+i*0.333+(1-p)*0.25;slog(a,[X-0.47,y0,Z],[X+0.47,y0,Z],0.16,x*5+y*3+k*7+i)}return}
 sbox(a,X,B,Z,0.485,0.004,0.485,V3LAID.mortar);   // the mortar bed
 const courses=[[[-0.48,0],[0,0.48]],[[-0.48,-0.24],[-0.24,0.24],[0.24,0.48]]];   // two courses a block, in a running bond (as the laid look, 021)
 for(let c=0;c<2;c++){const lo=c/2;if(f<=lo)break;const h=Math.min(0.5,f-lo),y0=B+c*0.5+0.008;
  for(const [u0,u1] of courses[c])sbox(a,X+(u0+u1)/2,y0,Z,(u1-u0)/2-0.012,Math.max(0.01,h/2-0.006),0.47,sjit(V3LAID.stone,x*11+y*7+k*3+c*5+Math.round(u0*10)))}}
// A label over each site (construction-3d polish 2): its name, how far it is, what lies on its pile, what it waits for;
// one plate a site, placed over the plan's middle a little above its top, hidden off the view or under it.
// A site's label clicked: Build › Construction opens on that site's card, which lights up a moment (polish 5).
function bmGoSite(k){try{buildView='tasks'}catch(e){}if(typeof hbPanel==='function')hbPanel('build');else send('tab','build');let n=0;
 const look=()=>{const c=document.querySelector('#buildSites [data-id="'+CSS.escape(k)+'"]');if(c){c.scrollIntoView({block:'center'});c.classList.add('flash');setTimeout(()=>c.classList.remove('flash'),1600);return}if(++n<12)setTimeout(look,200)};setTimeout(look,150)}
function siteTags(){let box=$('siteTags');if(!box){box=document.createElement('div');box.id='siteTags';box.style.cssText='position:fixed;left:0;top:0;width:0;height:0;z-index:0;pointer-events:none';
  const f=$('food3d');if(f)f.parentNode.insertBefore(box,f.nextSibling);else document.body.appendChild(box)}   /* under every card and panel, as the food tags and quest pins: a card over a label gets its clicks */
 const S=V3.on&&V3.z===1?arr(V3.sites):[],cv=$('world3d'),seen=new Set();
 for(const s of S){const id='st'+s[6]+'_'+s[7];seen.add(id);let el=document.getElementById(id);if(!el){el=document.createElement('div');el.id=id;el.className='sitetag';box.appendChild(el)}
  const nm=s[10]||'Building',done=(s[5]||0)-(s[4]||0),wd=s[2]===1,w=wd?'logs':'stone',t='<b>'+esc(nm)+'</b> '+done+' / '+(s[5]||0)+(s[3]?' · '+s[3]+' '+w+' on its pile':'')+(s[11]?'<span class="need"> · needs '+(wd?'wood':'stone')+'</span>':'');
  const pct=Math.round(100*done/Math.max(1,s[5]||0)),tt=t+'<span class="bar"><i style="width:'+pct+'%"></i></span>';if(el.dataset.t!==tt){el.dataset.t=tt;el.innerHTML=tt;el.title='Click: its card in Construction'}el.dataset.k=s[12]==='s'?String(s[13]):'p:'+s[13];if(!el.onclick)el.onclick=()=>bmGoSite(el.dataset.k)
  let shown=false;const P=cv&&v3project([(s[6]+s[8])/2,3.2,-(s[7]+s[9])/2]);   /* in the HUD's own pixels, as the quest pins: over the site under a zoomed HUD in a browser too (the canvas rect is in window pixels there) */
  if(P&&P[1]>96&&P[1]<cv.clientHeight-100&&P[0]>120&&P[0]<cv.clientWidth-180){shown=true;   /* never under the HUD's bars */el.style.left=P[0]+'px';el.style.top=P[1]+'px'}
  if(el.hidden===shown)el.hidden=!shown}
 for(const el of [...box.children])if(!seen.has(el.id))el.remove()}
window.pmSite=function(a){if(typeof v3beam4!=='function'||typeof MD==='undefined'||!MD.rod)return;
 if(SITE.q!==V3.planCells||SITE.s!==V3.sites||SITE.d!==V3.pdoors||SITE.tg!==V3.terrGen||SITE.mg!==V3.tmeshGen||SITE.t!==V3.terrain){SITE.q=V3.planCells;SITE.s=V3.sites;SITE.d=V3.pdoors;SITE.tg=V3.terrGen;SITE.mg=V3.tmeshGen;SITE.t=V3.terrain;try{SITE.v=siteBuild()}catch(e){SITE.v=[]}}   /* built again when the plan, the sites or the terrain come anew */
 for(let i=0;i<SITE.v.length;i++)a.push(SITE.v[i]);try{siteTags()}catch(e){}
 const now=performance.now();for(const t of arr(V3.things))if(t&&t.lay)try{siteLay(a,t,now)}catch(e){}};
// ---------- doors and floors (plan-doors-floors, 10-30): Plan mode's Door and Floor tools, on the ground ----------
// A door: a frame (two posts and a lintel) across its tile, along the wall line it stands in; a floor tile: a tinted
// square on the ground in stone or wood. Waiting doors (PlanPieces.dm, V3.pdoors) are drawn the same with the sites.
const piece=t=>t==='door'||t==='floor',DOORCOL=[0.9,0.62,0.28,1];
const pieceOK=(tool,x,y,k,more)=>{if(k>0){if(tool==='floor')return !PM.marks.has(key(x,y,k))&&!queued(x,y,k)&&canBuild(x,y,k,more);if(tool!=='door')return false;   /* upstairs: a floor is a block over the room below (phase 3) */const mk=PM.marks.get(key(x,y,k)),mb=PM.marks.get(key(x,y,k-1));return !has(x,y,k)&&(!mk||mk.b)&&(has(x,y,k-1)||queued(x,y,k-1)||!!(mb&&mb.b))&&(!!(mk&&mk.b)||queued(x,y,k))}   /* upstairs: a door is an opening in a wall still to be built (phase 2); floors wait for phase 3 */
 const m0=PM.marks.get(key(x,y,0));return !has(x,y,0)&&(!m0||(tool==='door'&&m0.b))&&!(tool==='floor'&&queued(x,y,0))&&!arr(V3.pdoors).some(d=>d[0]===x&&d[1]===y)};
function siteDoor(a,x,y,ew,c,k){const G=v3groundAt(x,y)+(k||0),X=x,Z=-y,h=1.7,w=0.42,P=ew?[[X-w,Z],[X+w,Z]]:[[X,Z-w],[X,Z+w]];
 for(const [px,pz] of P)sbox(a,px,G,pz,0.04,h/2,0.04,c);v3beam4(a,[P[0][0],G+h,P[0][1]],[P[1][0],G+h,P[1][1]],0.05,c);v3beam4(a,[P[0][0],G+0.03,P[0][1]],[P[1][0],G+0.03,P[1][1]],0.03,lit(c,0.7))}
const doorEW=(x,y,k)=>{k=k||0;const s=(i,j)=>has(i,j,k)||queued(i,j,k)||(PM.marks.get(key(i,j,k))||{}).b;return s(x-1,y)||s(x+1,y)||!(s(x,y-1)||s(x,y+1))};
// a step of a building's stairs: a wedge rising the way it goes up, a block high (a ramp in the game: Gather.dm)
const STEPV={1:[0,1],2:[0,-1],4:[1,0],8:[-1,0]};
function stepBox(a,x,y,k,dir,c){const v=STEPV[dir]||[1,0],C=[[-1,-1],[1,-1],[1,1],[-1,1]].map(([i,j])=>[x+i*0.455,k+0.03+0.95*((i*v[0]+j*v[1])/2+0.5),-(y+j*0.455)]),B=C.map(p=>[p[0],k+0.01,p[2]]),sd=lit(c,0.8);
 quad(a,C[0],C[1],C[2],C[3],[-v[0]*0.6,0.8,v[1]*0.6],c);for(let i=0;i<4;i++){const j=(i+1)%4;quad(a,B[i],B[j],C[j],C[i],[[0,0,1],[1,0,0],[0,0,-1],[-1,0,0]][i],sd)}}
function pieceMark(a,x,y,m,f){if(m.t==='door'){siteDoor(a,x,y,doorEW(x,y,m.k),lit(DOORCOL,f||1),m.k);return}
 const c=lit(m.m==='wood'?[0.74,0.52,0.3,1]:[0.76,0.74,0.68,1],f||1);quad(a,[x-0.46,0.025,-y+0.46],[x+0.46,0.025,-y+0.46],[x+0.46,0.025,-y-0.46],[x-0.46,0.025,-y-0.46],[0,1,0],lit(c,0.78));rfSquare(a,x,0.03,-y,0.48,0.03,c)}
// ---------- the Building tool (the layered builder, phase 1, 10-30; the owner: "make it procedural to make it right") ----------
// Drag a footprint: the game lays out a whole building as marks. A house or a hall: walls round it, a doorway with its
// door on the side facing your people (or the side picked on the card), the floor inside, at least 4 (a hall 6) across
// and at most 40 tiles inside (a roof covers that much: the roof comes with the last block). A tower: a 3x3 ring four
// high (the round tower's shape), entered from a wall top. A wall: a straight run, its battlements by themselves. Seen
// whole while dragging, then ordinary marks: any tool changes them, Queue it sends them. On the ground, in stone or wood.
const BKIND={house:{h:2,l:'House',min:4},hall:{h:3,l:'Hall',min:6},tower:{h:4,l:'Tower'},wall:{h:3,l:'Wall'}},BSIDE=['north','east','south','west'],BDIR={north:1,south:2,east:4,west:8};
function bDoorSide(x0,y0,x1,y1){if(PM.door&&PM.door!=='auto')return PM.door;let sx=0,sy=0,n=0;for(const t of arr(V3.things))if(t&&t.kind==='mine'&&t.x!=null){sx+=t.x;sy+=t.y;n++}
 const dx=(n?sx/n:V3.cx)-(x0+x1)/2,dy=(n?sy/n:V3.cy-50)-(y0+y1)/2;return Math.abs(dx)>Math.abs(dy)?(dx>0?'east':'west'):(dy>0?'north':'south')}
// Storeys (the layered builder, phase 3, 10-30; the owner: "if someone does a 2 story or 3 story house in one drag plan
// does it also include the beams and etc?"): a house or hall of 2 or 3 storeys, three levels each (two of room, then the
// floor over it). Its walls go up through every storey, over the door too (held by the walls beside it); each upper
// storey's floor is blocks over the room below, held by the walls within 3 tiles (Sites.dm RmPlanHeld), with a pillar
// from the ground where a span is longer; a flight of three steps up each storey (blocks one, two and three high, each
// top made a ramp: PlanPieces.dm RmPlanSteps), its foot on open floor, against the wall away from the door, the next
// flight against the other wall going back; the roof over the top storey (020 v3roofs). At least 4 tiles inside one way.
// On the storey looked at (the owner: "like mine craft where they can build anything ... off set some buildings and
// rooms"): from storey 2 up, a building stands on its own floor, blocks over whatever is under it (a house's walls or
// floor, or open air held by them within 3 tiles, a pillar from the ground past that), so a room can sit on a house and
// stick out past it; its way in is an opening on the door side.
function bLayout(a,b,o){const k=PM.bk||'house',K=BKIND[k],B0=stB(PM.level),cap=(o&&o.cap)||40,out=[];let S=K.min?Math.max(1,Math.min(3,PM.storeys||1)):1;while(S>1&&RMTOP-B0-SL*(S-1)<2)S--;
 const h=Math.max(1,Math.min(PM.height||K.h,RMTOP-B0-SL*(S-1))),on2=B0?' on storey '+(B0/SL+1):'';let x0=Math.min(a[0],b[0]),x1=Math.max(a[0],b[0]),y0=Math.min(a[1],b[1]),y1=Math.max(a[1],b[1]);
 if(B0>=RMTOP-1)return {cells:[],storeys:S,pillars:0,note:'no room up here: blocks go up to level '+(RMTOP-1)};
 if(k==='wall'){if(x1-x0>=y1-y0)y0=y1=a[1];else x0=x1=a[0];for(let x=x0;x<=x1;x++)for(let y=y0;y<=y1;y++)for(let z=B0;z<B0+h;z++)out.push([x,y,z,'w']);return {cells:out,note:(x1-x0+y1-y0+1)+' long, '+h+' high'+on2}}
 if(k==='tower'){x0=b[0]>=a[0]?a[0]:a[0]-2;y0=b[1]>=a[1]?a[1]:a[1]-2;x1=x0+2;y1=y0+2;for(let x=x0;x<=x1;x++)for(let y=y0;y<=y1;y++)if(x!==x0+1||y!==y0+1)for(let z=B0;z<B0+h;z++)out.push([x,y,z,'w']);return {cells:out,note:'3 × 3, '+h+' high, entered from a wall top'}}
 const mn=S>1?Math.max(K.min,5):K.min;if(x1-x0+1<mn){if(b[0]<a[0])x0=x1-mn+1;else x1=x0+mn-1}if(y1-y0+1<mn){if(b[1]<a[1])y0=y1-mn+1;else y1=y0+mn-1}
 if(S>1&&x1-x0<5&&y1-y0<5){if(b[0]<a[0])x0=x1-5;else x1=x0+5}   // the stairs: a flight of three and its foot, 4 tiles inside
 while((x1-x0-1)*(y1-y0-1)>cap){if(x1-x0>=y1-y0){if(b[0]<a[0])x0++;else x1--}else{if(b[1]<a[1])y0++;else y1--}}
 const side=bDoorSide(x0,y0,x1,y1),mx=Math.round((x0+x1)/2),my=Math.round((y0+y1)/2),d=side==='north'?[mx,y1]:side==='south'?[mx,y0]:side==='east'?[x1,my]:[x0,my],top=SL*(S-1)+h;
 for(let x=x0;x<=x1;x++)for(let y=y0;y<=y1;y++){if(x!==x0&&x!==x1&&y!==y0&&y!==y1)continue;if(x===d[0]&&y===d[1]){if(!B0)out.push([x,y,0,'d']);for(let z=2;z<top&&S>1;z++)out.push([x,y,B0+z,z===2?'c':'w']);continue}for(let z=0;z<top;z++)out.push([x,y,B0+z,'w'])}   /* upstairs its way in is an opening (no door) */
 const ix0=x0+1,ix1=x1-1,iy0=y0+1,iy1=y1-1,fl=[],pil=[];
 if(B0)for(let x=x0;x<=x1;x++)for(let y=y0;y<=y1;y++)out.push([x,y,B0-1,'c']);   // upstairs: its floor, under its walls too (none where a block is already)
 if(S>1){const W=ix1-ix0+1,H=iy1-iy0+1,ax=W>=4&&(W>=H||H<4),Lu=ax?W:H,Lv=ax?H:W,P=(u,v)=>ax?[ix0+u,iy0+v]:[ix0+v,iy0+u];
  const dw=ax?(side==='south'?0:side==='north'?Lv-1:-1):(side==='west'?0:side==='east'?Lv-1:-1),vf=dw===Lv-1?0:Lv-1,vb=vf?0:Lv-1,up=ax?[BDIR.east,BDIR.west]:[BDIR.north,BDIR.south];   // vf: the row against the wall away from the door
  for(let f=0;f<S-1;f++){const v=f%2?vb:vf,us=f%2?[Lu-2,Lu-3,Lu-4]:[1,2,3],base=B0+SL*f;fl.push(us.map(u=>P(u,v)));us.forEach((u,i)=>{const [x,y]=P(u,v);for(let z=base;z<=base+i;z++)out.push(z===base+i?[x,y,z,'s',up[f%2]]:[x,y,z,'w'])})}
  for(let s=1;s<S;s++){const z=B0+SL*s-1,F=fl[s-1];for(let x=ix0;x<=ix1;x++)for(let y=iy0;y<=iy1;y++)if(!F.some(([p,q])=>p===x&&q===y))out.push([x,y,z,'c'])}}
 let up2=!B0;   // a room on storey 2: a flight of three steps from the ground under it up to its floor, where the ground under it is open (inside it, its foot on open ground there or under its wall)
 if(B0===SL){const open=(x,y,n)=>{for(let j=0;j<n;j++)if(bAt(x,y,j))return false;return true},inn=(x,y)=>x>=ix0&&x<=ix1&&y>=iy0&&y<=iy1;
  for(const pass of [0,1])for(const [dx,dy,dr] of [[1,0,BDIR.east],[0,1,BDIR.north],[-1,0,BDIR.west],[0,-1,BDIR.south]]){if(up2)break;
   for(let x=ix0;x<=ix1&&!up2;x++)for(let y=iy0;y<=iy1&&!up2;y++){const T=[0,1,2].map(i=>[x+dx*i,y+dy*i]),F=[x-dx,y-dy];
    if(!T.every(([p,q])=>inn(p,q)&&open(p,q,SL)&&!pil.includes(p+','+q))||!open(F[0],F[1],2)||F[0]<x0||F[0]>x1||F[1]<y0||F[1]>y1)continue;
    if(!pass&&T.slice(0,2).some(([p,q])=>(p===ix0||p===ix1)&&(q===iy0||q===iy1)))continue;   /* first a place with its two lowest steps off the room's inside corners: a corner by them had no place to be laid from but the house's wall top under the room (played in the browser, 10-30); the pillars below are laid out after it */
    const at=new Set(T.map(([p,q])=>p+','+q));for(let i=out.length-1;i>=0;i--){const c=out[i];if(c[2]===B0-1&&at.has(c[0]+','+c[1]))out.splice(i,1)}   // the stairwell: no floor over the first two, the third's top is the step
    T.forEach(([p,q],i)=>{for(let z=0;z<=i;z++)out.push(z===i?[p,q,z,'s',dr]:[p,q,z,'w'])});up2=true}}}
 // a span over 3 (a big hall, a room sticking out past what is under it): a pillar from the ground under the floor
 // where it is furthest from a wall or pillar (Sites.dm RmPlanHeld: a whole column holds a floor within 3 tiles)
 const bk=new Set(out.filter(c=>c[3]!=='d').map(c=>c[0]+','+c[1]+','+c[2])),on=(x,y,z)=>bk.has(x+','+y+','+z)||bAt(x,y,z),whole=(x,y,z)=>{for(let j=z-1;j>=0;j--)if(!on(x,y,j))return false;return true},fx=new Set(fl.flat().map(([p,q])=>p+','+q));
 const far=(x,y,z)=>{const seen=new Set([x+','+y]);let fr=[[x,y]];for(let dd=1;dd<=12&&fr.length;dd++){const nx=[];for(const [p0,q0] of fr)for(const [dx,dy] of D4){const p=p0+dx,q=q0+dy,s=p+','+q;if(seen.has(s))continue;seen.add(s);if(!on(p,q,z))continue;if(whole(p,q,z))return dd;nx.push([p,q])}fr=nx}return 99};
 for(const z of [...new Set(out.filter(c=>c[3]==='c').map(c=>c[2]))].sort((p,q)=>p-q))for(let g=0;g<20;g++){let wc=null,wd=SPAN;for(const c of out)if(c[2]===z&&c[3]==='c'&&!fx.has(c[0]+','+c[1])&&!(c[0]===d[0]&&c[1]===d[1])&&!bAt(c[0],c[1],z)){const dd=far(c[0],c[1],z);if(dd>wd){wd=dd;wc=c}}if(!wc)break;
  wc[3]='w';pil.push(wc[0]+','+wc[1]);for(let j=0;j<z;j++)if(!bk.has(wc[0]+','+wc[1]+','+j)&&!bAt(wc[0],wc[1],j)){out.push([wc[0],wc[1],j,'w']);bk.add(wc[0]+','+wc[1]+','+j)}}
 if(!B0)for(let x=ix0;x<=ix1;x++)for(let y=iy0;y<=iy1;y++)if(!(fl[0]||[]).some(([p,q])=>p===x&&q===y)&&!pil.includes(x+','+y))out.push([x,y,0,'f']);
 return {cells:out,storeys:S,pillars:pil.length,note:(x1-x0+1)+' × '+(y1-y0+1)+on2+(S>1?', '+S+' storeys, '+top+' high, stairs up':', '+h+' high')+', '+(x1-x0-1)*(y1-y0-1)+' tiles inside, '+(B0?'an opening':'door')+' to the '+side+(B0===SL?(up2?', stairs up from the ground under it':', no open ground under it for stairs: reach it from another building'):'')+(pil.length?', '+pil.length+' pillar'+(pil.length>1?'s':''):'')}}
// The layout as marks: each level from the ground up, its walls and steps first, then the floor blocks over open air
// (each held by the walls, or by the floor blocks placed before it), then the door and the ground floor's tiles.
function bPlace(Lb){const act={add:[],del:[]},more=new Set();let n=0;
 const put=(x,y,k,c,dir)=>{const kk=key(x,y,k),m0=PM.marks.get(kk);if(m0&&m0.t==='floor'&&!k&&!queued(x,y,k)&&canBuild(x,y,k,more)){act.del.push([kk,m0]);PM.marks.delete(kk)}   /* a block (a stair's) over a floor tile marked there: the block */if(PM.marks.has(kk)||queued(x,y,k)||!canBuild(x,y,k,more))return false;const m={born:performance.now(),b:true,m:PM.mat};if(c==='s')m.st=dir;PM.marks.set(kk,m);more.add(kk);act.add.push(kk);n++;return true};
 const byZ=new Map();for(const c of Lb.cells){if(!byZ.has(c[2]))byZ.set(c[2],[]);byZ.get(c[2]).push(c)}
 for(const z of [...byZ.keys()].sort((p,q)=>p-q)){const L=byZ.get(z);for(const c of L)if(c[3]==='w'||c[3]==='s')put(c[0],c[1],z,c[3],c[4]);
  let rest=L.filter(c=>c[3]==='c');for(let go=true;go&&rest.length;){go=false;rest=rest.filter(c=>{if(!put(c[0],c[1],z,'c'))return true;go=true;return false})}
  for(const [x,y,k,c] of L){if(c!=='d'&&c!=='f')continue;const t=c==='d'?'door':'floor';if(!pieceOK(t,x,y,0))continue;const k0=key(x,y,0);PM.marks.set(k0,{born:performance.now(),b:false,t,m:t==='floor'?PM.mat:null});act.add.push(k0);n++}}
 if(n){PM.undo.push(act);PM.bNote=Lb.note}else shake();card();tag();return n}
// ---------- saved designs (the layered builder, 10-30; the plan: "save what you made or generated, stamp it anywhere, turned") ----------
// The marks not yet queued, saved by name in the player's profile (PlanPieces.dm RmDesigns), placed again with the
// Designs tool: seen at the cursor on the storey looked at, turned a quarter at a time on the card, and a click puts them
// down as marks, each block where it can go (on the ground, on a block or mark under it, or held over open air), to
// queue like any others. Kept as "1.w,h.x,y,k,code/..." (never a ";": the engine's link params split on it) from the footprint's corner and its lowest storey's ground: sb /
// wb a stone or wooden block, sp1 / wp4 a step rising that way (BDIR), d a door, sf / wf a floor tile. Dig marks and
// doorways upstairs (the gap in the blocks) aren't kept.
window.pmDesigns=function(raw){let L=[];try{L=JSON.parse(typeof raw==='string'?raw:JSON.stringify(raw))}catch(e){}PM.designs=Array.isArray(L)?L:[];if(PM.dPick&&!PM.designs.some(d=>d[0]===PM.dPick))PM.dPick=null;PM.dDel=null;card();tag()};
function dEncode(){const L=[];for(const [kk,m] of PM.marks){const [x,y,k]=kk.split(',').map(Number),c=m.t==='door'?(k?null:'d'):m.t==='floor'?(m.m==='wood'?'wf':'sf'):m.b?(m.m==='wood'?'w':'s')+(m.st?'p'+m.st:'b'):null;if(c)L.push([x,y,k,c])}
 if(!L.some(c=>c[3][1]==='b'||c[3][1]==='p'))return null;let x0=1e9,y0=1e9,k0=1e9,x1=-1e9,y1=-1e9;for(const [x,y,k] of L){x0=Math.min(x0,x);y0=Math.min(y0,y);k0=Math.min(k0,k);x1=Math.max(x1,x);y1=Math.max(y1,y)}k0=stB(k0);
 return {w:x1-x0+1,h:y1-y0+1,t:'1.'+(x1-x0+1)+','+(y1-y0+1)+'.'+L.map(([x,y,k,c])=>(x-x0)+','+(y-y0)+','+(k-k0)+','+c).join('/')}}
function dDecode(t){const p=String(t||'').split('.');if(p[0]!=='1'||p.length<3)return null;const [w,h]=p[1].split(',').map(Number);return {w,h,cells:p[2].split('/').map(s=>{const q=s.split(',');return [+q[0],+q[1],+q[2],q[3]]}).filter(c=>c[3])}}
const DTURN={1:4,4:2,2:8,8:1},dBlock=c=>c[1]==='b'||c[1]==='p';   // a quarter turn clockwise: north to east
// the design picked, turned, the middle of its footprint on the cursor, on the storey looked at
function dCur(){const e=arr(PM.designs).find(d=>d[0]===PM.dPick),D=e&&dDecode(e[1]);if(!D)return null;let w=D.w,h=D.h,cells=D.cells;
 for(let i=0;i<(PM.dTurn||0);i++){const W=w;cells=cells.map(([x,y,k,c])=>[y,W-1-x,k,c[1]==='p'?c.slice(0,2)+(DTURN[+c.slice(2)]||1):c]);[w,h]=[h,w]}
 const ox=PM.cx-Math.floor(w/2),oy=PM.cy-Math.floor(h/2),B=stB(PM.level);return {name:e[0],w,h,nb:cells.filter(c=>dBlock(c[3])).length,cells:cells.map(([x,y,k,c])=>[ox+x,oy+y,B+k,c])}}
// the design put down as marks: each level from the ground up, its blocks again and again till no more go (a floor over
// open air held by those before it), then its doors and floor tiles; what can't go there is left out and counted
function dPlace(){const D=dCur();if(!D){shake();return 0}const act={add:[],del:[]},more=new Set();let n=0,skip=0;
 const put=(x,y,k,c)=>{const kk=key(x,y,k);if(PM.marks.has(kk)||queued(x,y,k)||!canBuild(x,y,k,more))return false;const m={born:performance.now(),b:true,m:c[0]==='w'?'wood':'stone'};if(c[1]==='p')m.st=+c.slice(2);PM.marks.set(kk,m);more.add(kk);act.add.push(kk);n++;return true};
 const byZ=new Map();for(const c of D.cells){if(!byZ.has(c[2]))byZ.set(c[2],[]);byZ.get(c[2]).push(c)}
 for(const z of [...byZ.keys()].sort((p,q)=>p-q)){const L=byZ.get(z);let rest=L.filter(c=>dBlock(c[3]));for(let go=true;go&&rest.length;){go=false;rest=rest.filter(c=>{if(!put(c[0],c[1],z,c[3]))return true;go=true;return false})}skip+=rest.length;
  for(const [x,y,k,c] of L){if(dBlock(c))continue;const t=c==='d'?'door':'floor';if(!pieceOK(t,x,y,k,more)){skip++;continue}const kk=key(x,y,k);PM.marks.set(kk,{born:performance.now(),b:false,t,k,m:t==='floor'?(c==='wf'?'wood':'stone'):null});act.add.push(kk);n++}}
 PM.dNote=skip?skip+' could not go there':'';if(n)PM.undo.push(act);else shake();card();tag();return n}
function dGhost(a,draw){const D=dCur();if(!D)return;for(const [x,y,k,c] of D.cells){if(dBlock(c)){const L=c[0]==='w'?V3LAID.wood:V3LAID.stone;if(c[1]==='p')stepBox(a,x,y,k,+c.slice(2),L);else sbox(a,x,k+0.01,-y,0.455,0.485,0.455,L);draw(x,y,k,true,lit(c[0]==='w'?WCOL:COL.build,1.15))}else pieceMark(a,x,y,c==='d'?{t:'door'}:{t:'floor',m:c==='wf'?'wood':'stone'},1.15)}}
// a name for what is marked: the Building tool's kind and its size, else "Design"; a number after it when it is taken
function dName(w,h){const base=(PM.bNote&&BKIND[PM.bk||'house']?BKIND[PM.bk||'house'].l:'Design')+' '+w+'x'+h;let s=base;for(let i=2;arr(PM.designs).some(d=>d[0]===s);i++)s=base+' '+i;return s}
// Save design, or its name box, on the card's foot with Queue it (always in sight: above it, a scrolled card hid it under
// the foot: played in the browser, 10-30)
function dSaveRow(nb){if(!nb)return '';return PM.naming?'<div class="sv"><input id="pmName" maxlength="32" value="'+esc(PM.naming.name)+'" title="Its name"><button id="pmSaveOk">Save</button><button id="pmSaveNo" title="Not now">&#10005;</button></div>':'<div class="sv"><button id="pmSave" title="Keep what is marked as a design of yours, to place again anywhere, turned (Designs)">Save design</button></div>'}
// the card's Designs list (the Designs tool) and its buttons
function dCard(){if(PM.tool!=='design')return '';const ds=arr(PM.designs);
 return '<div class="dl">'+(ds.length?ds.map(([nm,tx],i)=>{const D=dDecode(tx);return '<div class="dr"><button data-pmdpick="'+i+'"'+(PM.dPick===nm?' class="on"':'')+' title="Place it: it follows the cursor on the storey you look at; a click puts it down">'+esc(nm)+'<small>'+(D?D.w+' × '+D.h+' · '+blocks(D.cells.filter(c=>dBlock(c[3])).length):'')+'</small></button><button data-pmddel="'+i+'" title="Delete this design (click twice)">'+(PM.dDel===nm?'Delete?':'&#10005;')+'</button></div>'}).join(''):'<div class="s">No saved designs yet. Lay out a building or mark blocks, then Save design.</div>')+
  (PM.dPick?'<div class="dr"><button data-pmdturn="1" title="A quarter turn clockwise">Turn &#8635;</button><span class="s">'+['as saved','a quarter turned','half turned','three quarters turned'][PM.dTurn||0]+'</span></div>':'')+'</div>'}
function dClick(b){const ds=arr(PM.designs);
 if(b.dataset.pmdpick!=null){const d=ds[+b.dataset.pmdpick];if(d){PM.dPick=PM.dPick===d[0]?null:d[0];PM.dTurn=0;PM.dNote=''}card();tag();return true}
 if(b.dataset.pmddel!=null){const d=ds[+b.dataset.pmddel];if(d){if(PM.dDel===d[0]){send('pmdesign','del|'+d[0]);PM.dDel=null}else PM.dDel=d[0]}card();return true}
 if(b.dataset.pmdturn){PM.dTurn=((PM.dTurn||0)+1)%4;PM.dNote='';card();tag();return true}
 if(b.id==='pmSave'){const e=dEncode();if(!e){shake();return true}PM.naming={t:e.t,name:dName(e.w,e.h)};card();const i=$('pmName');if(i){i.focus();i.select()}return true}
 if(b.id==='pmSaveOk'){const i=$('pmName'),nm=(i?i.value:'').replace(/[^A-Za-z0-9 '()-]/g,'').trim().slice(0,32);if(!nm||!PM.naming){shake();return true}send('pmdesign','save|'+nm+'|'+PM.naming.t);PM.naming=null;if(i)i.blur();if(typeof toast==='function')toast('Saved "'+nm+'". Designs on the Plan card places it again.');card();return true}
 if(b.id==='pmSaveNo'){PM.naming=null;card();return true}
 return false}
window.pmBLayout=bLayout;   // for the play tests
// ---------- drawing: lit floors and the level's grid round the cursor, the marks, the queued blocks, the cursor ----------
let qsig='';
window.pmDraw=function(a){if(!$('pmBar')){build();hookInput()}
 pmWorked(a);
 if(PM.on&&V3.z!==1)setOn(false);
 const Q=arr(V3.planCells),sig=Q.length+':'+(Q[0]||'')+(Q[Q.length-1]||'');if(sig!==qsig){qsig=sig;PM.qset=new Map(Q.map(c=>[key(c[0],c[1],c[2]),c[4]===1?(c[5]===1?2:1):0]));card();tag()}
 try{pmSite(a)}catch(e){}   /* construction sites: piles, stakes, scaffolding, blocks being laid (construction-3d) */
 if(!PM.on){V3.planCut=null;   /* queued blocks to build shown outside Plan mode too, faintly (building rework L8: a house the game plans is seen going up) */
  if(Q.length){const t=performance.now(),Z0=[0,0,0],rt=[Math.cos(V3.yaw)*0.016,0,-Math.sin(V3.yaw)*0.016],cols=new Map();for(const c of Q){if(c[4]!==1||Math.abs(c[0]-V3.cx)>30||Math.abs(c[1]-V3.cy)>24)continue;const kk=c[0]+','+c[1],o=cols.get(kk);if(!o)cols.set(kk,{x:c[0],y:c[1],lo:c[2],hi:c[2],w:c[5]});else{o.lo=Math.min(o.lo,c[2]);o.hi=Math.max(o.hi,c[2])}}   /* one light outline a column: its top to be, and its footprint till begun (construction-3d) */
   for(const o of cols.values()){const x=o.x,y=o.y,col=lit(o.w===1?QWCOL:QBCOL,0.55+0.1*Math.sin(t/420-(x+y)*0.8));rfSquare(a,x,o.hi+1.016,-y,0.48,0.022,col);if(o.lo===0)rfSquare(a,x,0.02,-y,0.46,0.03,col)}}   /* the top it will reach; a footprint where nothing is laid yet */
  return}V3.planCut=PM.tool==='building'||PM.tool==='design'?null:PM.level+SLAB;V3.planR=26;
 if(PM.sent&&performance.now()-PM.sentAt>4000)PM.sent=null;
 const L=PM.level,LV=PM.tool==='building'||PM.tool==='design'?99:L,Z0=[0,0,0],t=performance.now();   /* LV: the highest mark drawn (the Building tool sees them all) */if(!(t%1000<17))card();
 // the level round the cursor: its floors lit, its blocks' tops outlined (the cut leaves them low slabs)
 for(let dy=-R;dy<=R;dy++)for(let dx=-R;dx<=R;dx++){const x=PM.cx+dx,y=PM.cy+dy;if(dx*dx+dy*dy>R*R)continue;
  if(has(x,y,L))rfSquare(a,x,L+SLAB+0.012,-y,0.5,0.018,[0.78,0.64,0.32,1]);
  else if(L>0&&has(x,y,L-1)){quad(a,[x-0.46,L+0.02,-y+0.46],[x+0.46,L+0.02,-y+0.46],[x+0.46,L+0.02,-y-0.46],[x-0.46,L+0.02,-y-0.46],Z0,[0.5,0.46,0.34,1]);rfSquare(a,x,L+0.025,-y,0.46,0.03,[0.96,0.88,0.6,1])}}
 // a mark: a tinted top over its block (a slab's on this level), its outline
 const mark=(x,y,k,c)=>{if(k>LV)return;const h=k===L&&LV===L?k+SLAB+0.016:k+1.016;quad(a,[x-0.47,h,-y+0.47],[x+0.47,h,-y+0.47],[x+0.47,h,-y-0.47],[x-0.47,h,-y-0.47],Z0,c);rfSquare(a,x,h+0.004,-y,0.5,0.045,lit(c,1.25))};
 // a block to build: a ghost of it, its top and its four upright edges (a slab's height on this level)
 const ghost=(x,y,k,c)=>{if(k>LV)return;const top=k===L&&LV===L?k+SLAB:k+1,lo=k+0.02;mark(x,y,k,c);const e=lit(c,1.3),rt=[Math.cos(V3.yaw)*0.03,0,-Math.sin(V3.yaw)*0.03];
  for(const [ox,oz] of [[-0.47,-0.47],[0.47,-0.47],[0.47,0.47],[-0.47,0.47]]){const px=x+ox,pz=-y+oz;quad(a,[px-rt[0],lo,pz-rt[2]],[px+rt[0],lo,pz+rt[2]],[px+rt[0],top,pz+rt[2]],[px-rt[0],top,pz-rt[2]],Z0,e)}};
 const draw=(x,y,k,b,c)=>b?ghost(x,y,k,c):mark(x,y,k,c);
 for(const c of Q)if(Math.abs(c[0]-PM.cx)<=R+6&&Math.abs(c[1]-PM.cy)<=R+6)draw(c[0],c[1],c[2],c[4]===1,lit(c[4]===1?(c[5]===1?QWCOL:QBCOL):QCOL,0.85+0.15*Math.sin(t/380-(c[0]+c[1])*0.8)));   // queued: a slow wave over them
 for(const [kk,m] of PM.marks){const [x,y,k]=kk.split(',').map(Number);if(m.t){pieceMark(a,x,y,m);continue}if(m.b&&k<=LV){if(m.st)stepBox(a,x,y,k,m.st,m.m==='wood'?V3LAID.wood:V3LAID.stone);else sbox(a,x,k+0.01,-y,0.455,((k===L&&LV===L?SLAB:1)-0.03)/2,0.455,m.m==='wood'?V3LAID.wood:V3LAID.stone)}draw(x,y,k,m.b,m.b?(m.m==='wood'?WCOL:COL.build):COL.dig)}   /* a block to build: its stone or wood, the size it will be (polish 5) */
 if(PM.sent)for(const [kk,b] of PM.sent){if(PM.qset&&PM.qset.has(kk))continue;const [x,y,k]=kk.split(',').map(Number);draw(x,y,k,b>=1,lit(b===2?QWCOL:b===1?QBCOL:QCOL,0.9))}   // sent, not back from the game yet
 if(PM.tool==='design')dGhost(a,draw);   // the design picked, at the cursor
 if(PM.drag&&PM.drag.moved&&PM.tool==='building'){for(const [x,y,k,c,dr] of bLayout(PM.drag.a,[PM.cx,PM.cy]).cells){if(c==='w'||c==='c'||c==='s'){if(c==='s')stepBox(a,x,y,k,dr,PM.mat==='wood'?V3LAID.wood:V3LAID.stone);else sbox(a,x,k+0.01,-y,0.455,0.485,0.455,PM.mat==='wood'?V3LAID.wood:V3LAID.stone);draw(x,y,k,true,lit(bcol(),1.15))}else pieceMark(a,x,y,c==='d'?{t:'door'}:{t:'floor',m:PM.mat},1.15)}}else
 if(PM.drag&&PM.drag.moved&&piece(PM.tool))for(const [x,y] of dragCells())pieceMark(a,x,y,{t:PM.tool,m:PM.mat},1.18);else
 if(PM.drag&&PM.drag.moved)for(const [x,y,k] of dragCells())draw(x,y,k,PM.tool==='build',lit(PM.tool==='build'?bcol():COL[PM.tool==='erase'?'erase':'dig'],1.18));
 // the cursor: the block's whole outline on this level, red where the tool can't do anything (a shake when refused)
 const sa=t-(PM.shakeAt||-1e9),sh=sa<300?Math.sin(sa/22)*0.08*(1-sa/300):0,c=PM.bad||sa<300?BAD:lit(PM.tool==='build'?bcol():COL[PM.tool],1.2),X=PM.cx+sh,Zc=-PM.cy;
 rfSquare(a,X,L+0.03,Zc,0.53,0.05,c);rfSquare(a,X,L+1.02,Zc,0.53,0.05,c);const rt=[Math.cos(V3.yaw)*0.035,0,-Math.sin(V3.yaw)*0.035];
 for(const [ox,oz] of [[-0.53,-0.53],[0.53,-0.53],[0.53,0.53],[-0.53,0.53]]){const px=X+ox,pz=Zc+oz;quad(a,[px-rt[0],L,pz-rt[2]],[px+rt[0],L,pz+rt[2]],[px+rt[0],L+1.02,pz+rt[2]],[px-rt[0],L+1.02,pz-rt[2]],Z0,c)}
 // the tag over it
 const tg=$('pmTag');if(tg&&V3.vp){const m=V3.vp,wx=PM.cx,wy=L+1.15,wz=-PM.cy,cw=m[3]*wx+m[7]*wy+m[11]*wz+m[15];if(cw>0){const cx=(m[0]*wx+m[4]*wy+m[8]*wz+m[12])/cw,cy=(m[1]*wx+m[5]*wy+m[9]*wz+m[13])/cw,cv=$('world3d'),r=cv.getBoundingClientRect();
   tg.style.left=(r.left+(cx+1)/2*r.width)+'px';tg.style.top=(r.top+(1-cy)/2*r.height)+'px'}}};
})();
