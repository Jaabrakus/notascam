// ===== Order lines, StarCraft-style (the user, 10-25: "keep the movement lines, but StarCraft-style") =====
// A selected unit's line to its order point (and on through its queue) shows when the order is given (a model where its
// queue changed) and fades out by V3LINE_FADE; while Shift is held every selected unit's whole queue shows. Units given
// one order together (the same model) heading the same way, more than V3LINE_GROUP of them, get one line from their middle
// (the mean of where they are) through the means of their queue points instead of one each. A unit only just selected
// doesn't flash its standing orders (Shift shows them). The target squares fade with the lines (the user, 10-25: the
// placement grid, like the lines); pings and dig outlines are unchanged.
const V3LINE_HOLD=250,V3LINE_FADE=1500,V3LINE_GROUP=12;
var v3lineSeen=new Map(),v3lineBatch=0,v3lineShift=false;   // unit ref -> {sig, at, batch}
addEventListener('keydown',e=>{if(e.key==='Shift')v3lineShift=true},true);
addEventListener('keyup',e=>{if(e.key==='Shift')v3lineShift=false},true);
addEventListener('blur',()=>{v3lineShift=false});
function v3lineUpdate(m){const now=performance.now(),sel=new Set(),by=new Map();
 for(const u of arr(m&&m.units))if(u.selected)sel.add(u.ref);
 for(const t of arr(m&&m.targets)){const k=t.unit||'';if(!by.has(k))by.set(k,[]);by.get(k).push(t)}
 for(const r of [...v3lineSeen.keys()])if(!sel.has(r))v3lineSeen.delete(r);
 let batch=0,quiet=0;
 for(const r of sel){const L=(by.get(r)||[]).slice().sort((a,b)=>(a.index||0)-(b.index||0)),sig=L.map(t=>t.x+','+t.y+','+t.z).join(';'),rec=v3lineSeen.get(r);
  if(!rec){if(!quiet)quiet=++v3lineBatch;v3lineSeen.set(r,{sig,at:-1e9,batch:quiet});continue}   // just selected: no flash
  if(rec.sig!==sig){rec.sig=sig;if(sig){if(!batch)batch=++v3lineBatch;rec.at=now;rec.batch=batch}}}}
function v3lineGroups(Q,now){const alpha=new Map(),merged=new Set(),lines=[],groups=new Map();
 for(const q of Q){const r=v3lineSeen.get(q.unit);let a=q.unit==='patrol-draft'||v3lineShift?1:0;   // a patrol route being drawn always shows
  if(!a&&r&&r.at>0){const age=now-r.at;a=age<V3LINE_HOLD?1:Math.max(0,1-(age-V3LINE_HOLD)/(V3LINE_FADE-V3LINE_HOLD))}
  if(a<=0)continue;alpha.set(q.unit,a);if(!q.from||!q.list.length||q.unit==='patrol-draft')continue;
  const key=(r?r.batch:0)+'|'+q.list.length;if(!groups.has(key))groups.set(key,[]);groups.get(key).push(q)}
 // within one order, those heading to touching places are one group (a formation's slots touch; two far-apart points
 // don't): their last points in 4-tile cells, cells that touch joined
 const parts=[];for(const L of groups.values()){if(L.length<=V3LINE_GROUP){continue}const cell=new Map();
  for(const q of L){const t=q.list[q.list.length-1],k=Math.floor(t.x/4)+','+Math.floor(t.y/4);if(!cell.has(k))cell.set(k,[]);cell.get(k).push(q)}
  const seen=new Set();for(const k0 of cell.keys()){if(seen.has(k0))continue;const P=[],st=[k0];seen.add(k0);
   while(st.length){const k=st.pop();P.push(...cell.get(k));const [cx,cy]=k.split(',').map(Number);for(let dx=-1;dx<=1;dx++)for(let dy=-1;dy<=1;dy++){const k2=(cx+dx)+','+(cy+dy);if(cell.has(k2)&&!seen.has(k2)){seen.add(k2);st.push(k2)}}}
   parts.push(P)}}
 for(const L of parts){if(L.length<=V3LINE_GROUP)continue;const n=L.length,pts=[[0,0]];
  for(const q of L){merged.add(q.unit);pts[0][0]+=q.from[0]/n;pts[0][1]+=q.from[1]/n}
  for(let i=0;i<L[0].list.length;i++){let x=0,y=0;for(const q of L){x+=q.list[i].x/n;y+=q.list[i].y/n}pts.push([x,-y])}
  lines.push({pts,a:alpha.get(L[0].unit),c:L[0].list[0].color})}
 return {alpha,merged,lines}}
function armyOpen(view){if(view)armyView=view;send('tab','army');if(overlayHost){document.body.classList.add('panel-open');queueRegions()}}
window.hcOpenArmy=armyOpen;
function renderArmy(m){const pg=$('page-army');if(!pg)return;const C=Array.isArray(m.captives)?m.captives:[];{const n=$('armyCapN');const t=C.length?String(C.length):'';if(n.textContent!==t)n.textContent=t}
 if(pg.hidden)return;
 pg.querySelectorAll('[data-armyview]').forEach(b=>{const on=b.dataset.armyview===armyView;if(b.getAttribute('aria-selected')!==String(on))b.setAttribute('aria-selected',String(on))});
 const fv=$('armyFormations'),cv=$('armyCaptives');if(fv.hidden!==(armyView!=='formations'))fv.hidden=armyView!=='formations';if(cv.hidden!==(armyView!=='captives'))cv.hidden=armyView!=='captives';
 if(armyView==='formations'){const sh=$('armyShapes');if(!sh.childElementCount)sh.innerHTML=ARMY_SHAPES.map(([v,l,tip,pts])=>'<button class="armyshape" data-do="formation" data-value="'+v+'" title="'+esc(l+'\n'+tip)+'">'+armyShapeSvg(pts)+'<b>'+l+'</b><small>'+esc(tip)+'</small></button>').join('')+'<button class="armyshape mine" data-do="formation" data-value="custom"><svg></svg><b>Your own</b><small></small></button>';
  {const g=arr(m.formationGrid),F=arr(m.formations)[(Number(m.formationMine)||0)-1],nm=F&&F.name?String(F.name):'Your own',gk=JSON.stringify([g,nm]),b=sh.querySelector('[data-value=custom]');if(b&&b.dataset.g!==gk){b.dataset.g=gk;b.querySelector('svg').outerHTML=armyGridSvg(g);
   const by=['front','ranged','mage'].map(r=>[r,g.filter(c=>c[2]===r).length]).filter(x=>x[1]),t=!g.length?'Draw a layout below, then Use my layout.':by.length?by.map(([r,n])=>n+' '+r).join(' · ')+(g.length>by.reduce((a,x)=>a+x[1],0)?' · '+(g.length-by.reduce((a,x)=>a+x[1],0))+' any':'')+'.':'The layout you drew below: '+g.length+(g.length>1?' squares.':' square.');
   text(b.querySelector('b'),nm);text(b.querySelector('small'),t);b.title=nm+'\n'+t;b.disabled=!g.length}}
  sh.querySelectorAll('button').forEach(b=>{const on=String(b.dataset.value===m.formation);if(b.getAttribute('aria-pressed')!==on)b.setAttribute('aria-pressed',on)});
  const ed=$('armyFormEditor'),has=typeof window.fmArmyEditor==='function';if(ed.hidden===has)ed.hidden=!has;if(has){try{window.fmArmyEditor(ed,m)}catch(err){console.error(err)}}return}
 const key=JSON.stringify([C,m.ropes]);if(key===armyCapKey)return;armyCapKey=key;const box=$('armyCapList');
 if(!C.length){box.innerHTML='<p class="hint">No captives. Knock an enemy out and bind them with a rope.</p>'+armyRopes(m.ropes);return}
 const pct=v=>Math.max(0,Math.min(100,Math.round(Number(v)||0))),risk=v=>v>=67?'hi':v>=34?'mid':'lo';
 box.innerHTML=armyRopes(m.ropes)+C.map(c=>{const st=c.state==='slave'?'Slave'+(c.by?' · being won over by '+c.by:''):c.state==='winning'?'Being won over'+(c.by?' by '+c.by:''):c.state==='loose'?'Broke free':'Bound';const lo=pct(c.loyalty),rk=pct(c.risk),here=c.z?c.x+'|'+c.y+'|'+c.z:'';
  return '<div class="capt st-'+esc(c.state||'bound')+'"><div class="capt-h"><b>'+esc(tidyLine(c.name||'Captive'))+'</b><small>'+esc([c.race,st].filter(Boolean).join(' · '))+'</small>'+(here?'<button class="capt-go" data-do="gotoplace" data-value="'+esc(here)+'" title="Go there\nCentre the camera on them.">Go to</button>':'')+'</div>'
   +'<div class="capt-rope'+(c.rope?'':' none')+'"><b class="hcg hcg-chain">⛓</b> '+(c.rope?esc(c.rope)+(c.ropeq?' · '+esc(c.ropeq):''):'No rope')+'</div>'
   +'<div class="capt-bars"><span>Loyalty</span><i class="capt-bar loy"><em style="width:'+lo+'%"></em></i><b>'+lo+'%</b>'+(c.state==='slave'?'':'<span>Breaks free</span><i class="capt-bar risk '+risk(rk)+'"><em style="width:'+rk+'%"></em></i><b>'+rk+'%</b>')+'</div>'
   +(c.next!=null&&c.state!=='slave'?'<small class="capt-next">Next try to break free in '+esc(c.next)+' s</small>':'')
   +armyActs(c)+'</div>'}).join('')}
// a captive's actions in two short rows, so none wraps on its own: what becomes of them (win over, enslave, release),
// then handling them (move, tie here or lead); a command it doesn't know goes in the first row
function armyActs(c){const A=Array.isArray(c.acts)?c.acts:[];if(!A.length)return '';const hand=a=>/^(move|tie|lead)$/.test(a[0]);
 const btn=a=>'<button data-do="captive" data-value="'+esc(c.ref+'|'+a[0])+'"'+(a[2]?' disabled title="'+esc(a[1]+'\n'+a[2])+'"':' title="'+esc(a[1])+'"')+'>'+esc(a[1])+'</button>';
 const row=(L,k)=>L.length?'<div class="capt-acts'+k+'">'+L.map(btn).join('')+'</div>':'';return row(A.filter(a=>!hand(a)),'')+row(A.filter(hand),' hand')}
// ropes = {stock, carried} (capture-rope): what there is to bind a new captive with
function armyRopes(R){if(R==null)return '';const st=typeof R==='object'?Number(R.stock)||0:Number(R)||0,ca=typeof R==='object'?Number(R.carried)||0:0;return '<p class="armyropes">'+(st+ca?'Ropes: '+[st?st+' in the stockpile':'',ca?ca+' carried':''].filter(Boolean).join(' · '):'No rope yet: the Leatherworks and the Carpentry make it.')+'</p>'}
// Move only answers with a hint (click the ground): select the captive first, so that click leads them there
document.addEventListener('click',e=>{const b=e.target.closest('#armyCapList button[data-do=captive]');if(!b||b.disabled)return;const v=String(b.dataset.value),i=v.lastIndexOf('|');if(v.slice(i+1)==='move')send('select',v.slice(0,i))},true);
document.addEventListener('click',e=>{const b=e.target.closest('#page-army [data-armyview]');if(!b)return;armyView=b.dataset.armyview;armyCapKey='';if(model)renderArmy(model)});
function renderUseCard(m){const c=$('usecard');if(!c)return;const U=m.useCard;if(!U){if(!c.hidden){c.hidden=true;c.dataset.k='';queueRegions()}return}
 const key=JSON.stringify(U);if(c.dataset.k===key&&!c.hidden)return;c.dataset.k=key;
 const groups=new Map();arr(U.options).forEach((o,i)=>{const g=o.group||'';if(!groups.has(g))groups.set(g,[]);groups.get(g).push([o,i+1])});
 let h='<div class="ic-head"><span class="ic-kind k-station">⚒</span><div class="ic-name"><b>'+esc(typeof hcNiceName==='function'?hcNiceName(U.title):U.title)+'</b><small>'+(U.unit?esc(U.unit)+(U.near?' is beside it':' walks over first'):'Select a unit to use it')+' · '+arr(U.options).length+' to choose from</small></div><button class="ic-x" data-uc="close" title="Close (Esc)">×</button></div>';
 if(arr(U.options).length>10)h+='<input class="uc-q" type="search" placeholder="Find…" aria-label="Find">';
 h+='<div class="uc-body">';for(const [g,list] of groups){h+='<div class="uc-sec">'+(g?'<div class="uc-group">'+esc(icSpaced(g))+'</div>':'')+'<div class="uc-opts">'+list.map(([o,i])=>'<button data-uc="'+i+'" title="'+esc(o.label+(g?'\n'+g:'')+'\nClick: '+(U.unit?U.unit+(U.near?' makes it':' walks over and makes it'):'select a unit first'))+'">'+esc(icSpaced(o.label))+'</button>').join('')+'</div></div>'}
 c.innerHTML=h+'</div>';c.hidden=false;queueRegions();const q=c.querySelector('.uc-q');if(q)q.focus()}
document.addEventListener('input',e=>{const q=e.target.closest&&e.target.closest('#usecard .uc-q');if(!q)return;const t=q.value.trim().toLowerCase();
 $('usecard').querySelectorAll('.uc-sec').forEach(sec=>{const g=(sec.querySelector('.uc-group')||{}).textContent||'';let any=0;sec.querySelectorAll('button[data-uc]').forEach(b=>{const on=!t||b.textContent.toLowerCase().includes(t)||g.toLowerCase().includes(t);b.hidden=!on;if(on)any=1});sec.hidden=!any})});
document.addEventListener('click',e=>{const b=e.target.closest('#usecard [data-uc]');if(!b)return;const v=b.dataset.uc;if(v==='close')send('usecardclose','');else send('usecardrun',v);$('usecard').hidden=true;$('usecard').dataset.k='';queueRegions();gameFocus()});
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&$('usecard')&&!$('usecard').hidden){send('usecardclose','');$('usecard').hidden=true;$('usecard').dataset.k='';queueRegions()}});
function icSpaced(t){return String(t||'').replace(/([a-z])([A-Z])/g,'$1 $2')}
// A thing's name for the HUD (hud-craft): no owner tag; a run-together type name ("CarpentryCraftingStation", "ForgeLeft") loses
// its station/part suffix and gets its spaces back. Names that already have spaces are left as they are.
/* the race special's cooldown as the fraction still to wait: the game sends only the seconds left, so the most seen since
   it was last ready stands for the whole wait (hud-craft) */
/* workshops that all share the game's one brown workshop sprite get their own icon in the Build list (hud-craft) */
function hcShopIcon(id){return {carpentry:'saw',kitchen:'bowl',leather:'hide',bone:'bone',poison:'skull',potion:'flask',forge:'anvil',smelter:'furnace',masonry:'bricks',gem:'gem',melter:'crucible'}[id]||''}
/* a status line's leading ⚔ (fighting) or ☹ (unhappy) as an icon: at 11 px the glyphs read as a stray × and ⊗ */
function hcStatusHTML(t){t=String(t||'');const m=/^(⚔|☹) /.exec(t);return m?'<b class="hcg hcg-'+(m[1]==='⚔'?'sword':'frown')+'">'+m[1]+'</b> '+esc(t.slice(2)):esc(t)}
/* the rare creatures that are not people (playtest's lone-start list minus Svartalfar and Illithid): no craft role, no
   hands for stores or armour */
function hcBeast(u){return /^(Dragon|Spider|Devourer|SandKing|Sand King)$/.test(String(u&&u.race||''))}
/* a near-card use button says what it does ("Feed meat", "Treat with bandage", "Give ale to drink"), not just the item (hud-craft) */
function hcUseLabel(l){l=String(l||'');const m=/^(Treat|Feed|Give to drink): (.+)$/.exec(l);if(!m)return l;const it=m[2],low=it.toLowerCase();return m[1]==='Feed'?'Feed '+low:m[1]==='Treat'?'Treat with '+low:'Give '+low+' to drink'}
function hcSpCd(ref,w){const M=hcSpCd.m||(hcSpCd.m={});if(!(w>0)){delete M[ref];return '0'}M[ref]=Math.max(M[ref]||0,w);return (w/M[ref]).toFixed(3)}
function hcNiceName(n){n=String(n||'').replace(/^\{[^}]*\}\s*/,'');return /\s/.test(n)||!/[a-z][A-Z]/.test(n)?n:icSpaced(n.replace(/(CraftingStation|Station|Left|Right)$/,''))}
// The Interact card's icons and tips (by the action's words, then its command).
const IC_KIND={mine:'◉',player:'⚑',npc:'⚔',animal:'❦',item:'✋',station:'⚒',body:'✝',object:'▣'};
function icGlyph(label,a){const l=String(label);if(/^Treat/.test(l))return '<b class="hcg hcg-cross">✚</b>';if(/^(Feed|Eat)/.test(l))return '<b class="hcg hcg-bowl">❦</b>';if(/^(Give to drink|Drink)/.test(l))return '<b class="hcg hcg-flask">⚗</b>';if(/^Carry|^Put them down/.test(l))return '<b class="hcg hcg-carry">⇡</b>';if(/^(Hunt|Attack)/.test(l)||a==='attackpart')return '<b class="hcg hcg-sword">⚔</b>';if(a==='captureorder'||a==='chainorder')return '<b class="hcg hcg-chain">⛓</b>';if(a==='feedbeast')return '<b class="hcg hcg-bone">❧</b>';if(a==='breed')return '<b class="hcg hcg-heart">♥</b>';if(/^Select all/.test(l))return '<b class="hcg hcg-people">◎</b>';if(/^Add to sel/.test(l))return '<b class="hcg hcg-plus">＋</b>';if(/^Select/.test(l))return '<b class="hcg hcg-selected">◉</b>';if(/^(Favourite|Unfavourite)/.test(l))return '<b class="hcg hcg-star">\u2605</b>';if(/^(Pick up|Open its bag)/.test(l))return '<b class="hcg hcg-hand">✋</b>';if(/^(Use|Put on)/.test(l))return '<b class="hcg hcg-gear">⚙</b>';if(/^Sleep/.test(l))return '<b class="hcg hcg-moon">☾</b>';if(/^Fish/.test(l))return '<b class="hcg hcg-fish">≈</b>';if(/^Mine|^Dig down|block above/.test(l))return '<b class="hcg hcg-pick">⛏</b>';if(/ramp|steps|stairs|Go up|Man the wall/.test(l))return '<b class="hcg hcg-stairs">⇗</b>';if(a==='target3d')return '<b class="hcg hcg-spark">✦</b>';if(a==='unitability')return '<b class="hcg hcg-sparkle">✧</b>';return '<b class="hcg hcg-arrow">➜</b>'}
function icTip(label,a){const l=String(label);return /^Hunt/.test(l)?'The selected units hunt it.':/^Attack its/.test(l)?'The selected units strike that part.':/^Attack/.test(l)?'The selected units go and fight it.':/^Go to/.test(l)?'The selected units walk to it.':a==='captureorder'?(/Tame/.test(l)?'Knock it out (non-lethal), then tame it: it joins you at once.':'Knock them out (non-lethal) and tie them with a rope; then win them over or enslave them.'):a==='breed'?'They go off together for a while; a child may follow.':a==='chainorder'?'Bind the great beast with chains; then feed it while it is bound to tame it.':a==='feedbeast'?'Feed the bound beast raw meat: enough feeds and it trusts you.':/^Select all/.test(l)?'Every unit of yours like this one in view.':/^Add to sel/.test(l)?'Keeps the units already selected.':/^Select/.test(l)?'Select only this unit.':/^Pick up/.test(l)?'The selected unit walks over and takes it.':/^Use/.test(l)?(a==='usecard'?'Everything it can make or do, to choose from.':'Opens it, as a double-click does.'):/^Fish/.test(l)?'The selected units fish from here.':/^Dig down/.test(l)?'Takes the top block off this column; the mountain gets a block lower here.':/^Carve into a ramp/.test(l)?'Its top block becomes a slope, rising away from the one who carves it: units step up it, one block.':a==='target3d'?'Aim the waiting spell here.':/^Move|work here/.test(l)?'Walk here, or work on what is here.':''}
function v3menuClose(){const m=$('menu3d');if(m&&!m.hidden){m.hidden=true;V3.hoverPart=null;queueRegions()}}
function v3menuOpen(mx,my){const t=v3pickThing(mx,my),pt=t?{x:t.x,y:t.y}:v3pickTile(mx,my);if(!pt)return;const m=$('menu3d');
 // everything on that tile, not only the thing nearest the pointer
 const here=V3.things.filter(o=>o.x===pt.x&&o.y===pt.y&&!o.ly&&!o.nopick&&o.kind!=='effect'&&(o.kind!=='decal'||o.fishspot||o.mouth!=null||o.caveexit)&&v3visible(o));
 const units=here.filter(o=>['mine','player','npc','animal'].includes(o.kind)),order={mine:0,player:1,npc:2,animal:3};units.sort((a,b)=>order[a.kind]-order[b.kind]||(a===t?-1:b===t?1:0));
 const items=new Map();for(const o of here)if(o.kind==='item'){const k=o.name;if(!items.has(k))items.set(k,{t:o,n:0});items.get(k).n++}
 const others=here.filter(o=>!['mine','player','npc','animal','item'].includes(o.kind));
 const tv=o=>pt.x+'|'+pt.y+'|'+(o.ref||o.id||'');const tile=pt.x+'|'+pt.y+'|';const sel=arr(model&&model.units).some(u=>u.selected);
 const groups=[];const nm=o=>String(o.name||'').replace(/^\{[^}]*\}\s*/,'');
 /* one bound captive selected (not caged): anything solid right-clicked can take their rope (Captives.dm RmCapTieable) */
 const cs1=arr(model&&model.units).filter(u=>u.selected),capT=cs1.length===1&&cs1[0].captive&&cs1[0].captive.state==='bound'&&!cs1[0].captive.cage?cs1[0]:null;
 const tieAct=v=>capT?[['Tie '+nm(capT)+' to this','captive',capT.ref+'|tieto|'+v,'One of yours takes them beside it and ties them to it: they hold better tied to something.']]:[];
 for(const o of units){const acts=[];let grid=null;
  if(o.kind==='mine'){{const me=arr(model&&model.units).find(u=>u.ref&&u.ref===o.ref&&u.selected);if(me&&me.cave&&me.cave.plant)acts.push([me.cave.moves?'Move our lair here':'Make our lair here','cave',me.ref+'|plant','Your dragon digs its own lair into the rock here.'])}if(sel&&o.beast&&o.beast.bound===2)acts.push(['Feed it raw meat ('+(o.beast.trust||0)+'/'+(o.beast.feeds||3)+')','feedbeast',o.ref||o.id]);{const me1=arr(model&&model.units).filter(u=>u.selected);if(me1.length===1&&me1[0].ref&&me1[0].ref===o.ref){acts.push(['Open its bag','cardtab','overview','Its card\u2019s Overview: everything it carries, each with its own uses.']);acts.push(...arr(me1[0].selfuses).map(x=>[x[0],x[1],x[2],x[3]]))}}   /* its own card: bag, eat, drink, treat, put on, sleep (TargetActions.dm RemasterSelfUses; the owner, 10-28) */acts.push(['Select','click3d',tv(o)+'|0']);acts.push(['Add to selection','click3d',tv(o)+'|1']);acts.push(['Select all like this','dblclick3d',tv(o)]);capMenuActs(o,acts)}
  else{acts.push([sel?(o.kind==='animal'?'Hunt / attack':'Attack'):'Go to','click3d',tv(o)+'|0']);
   // a great beast (Beasts.dm): attack one of its parts - the nearest the pointer first; in the air, its wings
   if(sel&&o.beast&&o.id){const ps=arr(o.beast.parts).map(q=>{const [PX,,PZ]=v3world({dx:q[0],dy:q[1]}),sp=v3project([PX,v3groundAt(q[0],q[1])+0.5,PZ]);return {n:q[2],hp:q[3],d:sp?Math.hypot(sp[0]-mx,sp[1]-my):1e9}}).sort((p1,p2)=>p1.d-p2.d);
    if(!ps.length&&o.beast.fly)ps.push({n:'left wing',hp:o.beast.wings},{n:'right wing',hp:o.beast.wings});if(ps.length)grid={id:o.id,kind:o.beast.kind,fly:!!o.beast.fly,parts:ps,here:o.beast.fly?null:ps[0].n}}// a great beast is tamed by chains, not knocked out (Taming.dm): Chain it down, then feed it while it is bound
   if(sel&&o.id&&o.beast&&o.beast.bound===2)acts.push(['Feed it raw meat ('+(o.beast.trust||0)+'/'+(o.beast.feeds||3)+')','feedbeast',o.id]);
   else if(sel&&o.id&&o.beast&&!o.beast.bound&&!o.ally&&!o.peace&&(o.beast.kind==='dragon'||o.beast.kind==='spider'&&o.beast.size>=1.7))acts.push(['Chain it down','chainorder',o.id]);
   else if(sel&&!o.ally&&!o.peace&&o.id&&!o.beast)acts.push([o.kind==='animal'?(o.ko!=null?'Tame':'Tame (knock out first)'):(o.ko!=null?'Capture':'Capture (knock out first)'),'captureorder',o.id]);if(V3.magic)acts.push(['Set magic target','target3d',tv(o)])}
  // with one unit selected: have a child with a partner close by, and the original options for the creature beside it
  const one=arr(model&&model.units).filter(u=>u.selected);if(one.length===1){const u=one[0],nb=arr(u.nearby).find(n=>(o.ref&&n.ref===o.ref)||(o.id&&n.id===o.id));
   if(nb&&arr(nb.acts).includes('child'))acts.push(['Have a child','breed',u.ref+'|'+nb.ref]);
   if(nb&&arr(nb.uses).length)acts.splice(0,0,...arr(nb.uses).map(x=>[x[0],x[1],x[2],x[3]]));   // carry, treat, feed (TargetActions.dm)
   for(const [menu,name] of arr(u.abilities))if(menu==='Closest Creature'&&!/^Breed With/.test(name)&&String(name).replace(/\{[^}]*\}\s*/g,'').endsWith(nm(o)))acts.push([String(name).replace(/\{[^}]*\}\s*/g,''),'unitability',u.ref+'|'+menu+'|'+name])}
  groups.push({title:nm(o),sub:{mine:'yours',player:o.ally?'ally':o.war?'enemy realm':'another realm',npc:o.peace?'trader':'hostile',animal:'animal'}[o.kind],acts,grid,thing:o})}
 for(const [name,g] of items){const acts=[];{const s1=arr(model&&model.units).filter(u=>u.selected);if(s1.length===1&&s1[0].captive&&s1[0].captive.state==='bound'&&!s1[0].captive.cage&&/Cage/.test(name)&&g.t.id)acts.push(['Put '+String(s1[0].name||'').replace(/^\{[^}]*\}\s*/,'')+' in this cage','captive',s1[0].ref+'|cage|'+g.t.id,'One of yours takes them into it; the rope comes off them, back to that one. A cage with someone in it can\u2019t be carried.'])}   /* Captives.dm */if(g.t.id&&(g.t.m3||g.t.kind==='object'))acts.push(...tieAct(g.t.id));acts.push(sel?['Pick up','pickup3d',tv(g.t)+'|0']:['Pick up','nearact','pickup3d~'+tv(g.t)+'|0','Your nearest unit goes and picks it up.']);   /* a real pick-up, loose furniture too (View3D.dm Rm3DPickUp; the owner, 10-28) */acts.push(['Use / open','dblclick3d',tv(g.t)]);   /* none selected: the nearest unit does it (View3D.dm RmNearAct; the owner, 10-28) */groups.push({title:name+(g.n>1?' ×'+g.n:''),sub:'item on the ground',acts,thing:g.t})}
 for(const o of others){const one1=arr(model&&model.units).find(u=>u.selected);const acts=o.mouth!=null?(sel&&!o.mouthDone?[['Enter the cave','caveenter',tv(o),'The selected units walk to the mouth and go down together (up to 8). One visit per cave a day.']]:[]):o.caveexit?(one1?[['Climb out','cave',one1.ref+'|leave','Everyone of yours near the stairs climbs back up to the mouth.']]:[]):o.fishspot?[['Fish here','work3d',tv(o)+'|0']]:o.kind==='station'?[['Use / open','usecard',tv(o)]]:[['Use / open','dblclick3d',tv(o)]];
  if(o.id&&(o.kind==='object'||o.kind==='station'))acts.push(...tieAct(o.id));
  if(o.kind==='body'){const one=arr(model&&model.units).filter(u=>u.selected);if(one.length===1){const na=arr((arr(one[0].nearby).find(n=>n.id===o.id)||{}).acts);   /* Drag body / Let go: BodyDrag.dm */
   if(na.includes('carrybody'))acts.unshift(['Carry the body','carrybody',one[0].ref+'|'+o.id,'Walk over and take the body up: to the graveyard, or to the Operating table.']);
   else if(na.includes('dragbody'))acts.unshift(['Drag body','carrybody',one[0].ref+'|'+o.id,'Walk over, take hold and drag it along the ground behind (slower going): to the graveyard, a table or a workshop.']);
   else if(na.includes('letgo'))acts.unshift(['Let go','carrybody',one[0].ref+'|'+o.id+'|0','Leave the body where it lies.'])}
   if(!acts.some(x=>x[1]==='carrybody'))acts.unshift(['Drag body','nearact','carrybody~'+o.id,(sel?'The nearest of the selected':'Your nearest unit')+' walks over, takes hold and drags it along: to the graveyard, a table or a workshop.'])}   /* none near it selected, several, or none: the nearest one goes (View3D.dm RmNearAct) */
  {const go=o.hellgate?(o.hellgate==='up'?'Go up through the portal':'Go down through the portal'):'Go to';acts.push(sel?[go,'click3d',tv(o)+'|0']:[go,'nearact','click3d~'+tv(o)+'|0','Your nearest unit goes.'])}   /* a hellgate (View3D.dm "hellgate"): down to Hell or back up */groups.push({title:nm(o)||o.kind,sub:o.mouth!=null?((o.lair==='dragon'?"dragon's lair":o.lair==='spider'?"spider's nest":'cave mouth')+(o.mouthDone?' · explored today':sel?'':' · select units to send in')):o.caveexit?'the way back up':({station:'workshop',body:'body',object:'object'}[o.kind]||o.kind),acts,thing:o})}
 if(pt.lvl){const K=v3kindAt(pt.x,pt.y)||{};groups.push({tile:1,title:'Dug-out floor',sub:'inside the mountain, '+pt.lvl+' block'+(pt.lvl>1?'s':'')+' up',acts:[...(sel?[['Walk here','walk3d',tile+'|0|1|'+pt.lvl]]:[]),...(sel?[['Mine this block','work3d',tile+'|0|0|'+(pt.lvl-1)]]:[]),...(sel&&!K.slope?[['Carve into a ramp','carveramp',pt.x+'|'+pt.y+'|0|'+(pt.lvl-1),'The block under this floor becomes a slope: units step up it one block, to the next floor.']]:[])]})}
 else if(pt.up&&pt.peak){const onTop=sel&&arr(model&&model.units).some(u=>u.selected&&u.z===3);groups.push({tile:1,title:'Mountain top',sub:onTop?'dig it down a block at a time':'units go up by carved steps or stairs',acts:[[sel?(onTop?'Walk here':'Go up here'):'Look here',sel?'walk3d':'click3d',tile+'|0|1'],...(onTop?[['Dig down here','work3d',tile+'|0|1']]:[]),...(onTop&&!(v3kindAt(pt.x,pt.y)||{}).slope?[['Carve into a ramp','carveramp',pt.x+'|'+pt.y]]:[])]})}
 else if(pt.up)groups.push({tile:1,title:'Wall walk',sub:'on top of the wall',acts:[[sel?'Man the wall here':'Look here','click3d',tile+'|0|1']]});
 else{const near=V3.walkTiles&&[[0,1],[1,0],[0,-1],[-1,0]].some(([a1,b1])=>V3.walkTiles.has((pt.x+a1)+','+(pt.y+b1)));if(near&&sel)groups.push({tile:1,title:'Up onto the wall',sub:'a ramp (three tiles along the wall, 3 stone) or a single stairway',acts:[['Build a ramp from here','wallramp',pt.x+'|'+pt.y],['Build wall stairs here','wallstairs',pt.x+'|'+pt.y]]})}
 {const K=v3kindAt(pt.x,pt.y),YD=V3.yield&&V3.yield.get(pt.x+','+pt.y),xy=pt.x+'|'+pt.y;if(sel&&K&&K.kind==='wall'&&K.blocks&&!pt.up)groups.push({tile:1,title:'Mountain',sub:K.blocks+' layers of rock'+(K.vein?' · '+K.vein+' vein'+(YD&&YD[4]==='vein'?': '+YD[2]+' of '+YD[5]+' left':''):''),acts:[...tieAct(pt.x+','+pt.y),['Mine here','work3d',tile+'|0'],['Carve steps up from here','carve',pt.x+'|'+pt.y+'|0'],...(K.slope?[]:[['Carve into a ramp','carveramp',pt.x+'|'+pt.y]])]});
  if(sel&&K&&K.kind==='tree'&&!pt.up)groups.push({tile:1,title:'Tree',sub:(YD?YD[2]+' of '+YD[5]+' logs left':'a log every few swings'),acts:[...tieAct(pt.x+','+pt.y),['Chop it','work3d',tile+'|0'],['Add: chop it after','work3d',tile+'|1']]});
  if(capT&&K&&K.kind==='built'&&!pt.up)groups.push({tile:1,title:'Wall',sub:'built',acts:tieAct(pt.x+','+pt.y)});
  if(sel&&K&&K.roof&&K.kind!=='wall')groups.push({tile:1,title:'Dug out',sub:K.roof+' block'+(K.roof>1?'s':'')+' of rock overhead',acts:[['Mine the block above','mineroof',pt.x+'|'+pt.y+'|0'],['Add: mine the block above after','mineroof',pt.x+'|'+pt.y+'|1']]})}
 groups.push({tile:1,title:'This tile',sub:pt.x+', '+pt.y,acts:[]});   /* Hidden Clans: no Move here, your ninja walks with WASD (Drive.dm) */
 const things=groups.filter(g=>!g.tile),tiles=groups.filter(g=>g.tile);let cur=0;
 const draw=()=>{m.innerHTML='';const g=things[cur];
  const head=document.createElement('div');head.className='ic-head';
  if(g){const o=g.thing||{},hp=o.hp!=null?Math.max(0,Math.min(100,o.hp)):null,st=[g.sub,o.ko!=null?'knocked out':'',o.webbed?'held in a web':'',o.ill?String(o.ill):'',o.drunk?'drunk':''].filter(Boolean).join(' · ');
   head.innerHTML='<span class="ic-kind k-'+esc(o.kind||'tile')+'">'+(IC_KIND[o.kind]||'◆')+'</span><div class="ic-name"><b>'+esc(typeof hcNiceName==='function'?hcNiceName(g.title):g.title)+'</b><small>'+esc(st)+'</small>'+(hp!=null?'<i class="ic-hp"><span style="width:'+hp+'%"></span></i>':'')+'</div>'}
  else head.innerHTML='<span class="ic-kind k-tile">◆</span><div class="ic-name"><b>'+esc(tiles[0]?tiles[0].title:'Here')+'</b><small>'+esc(tiles[0]?tiles[0].sub||'':'')+'</small></div>';
  const x=document.createElement('button');x.className='ic-x';x.setAttribute('aria-label','Close');x.title='Close (Esc)';x.textContent='×';x.addEventListener('click',()=>{v3menuClose();gameFocus()});head.append(x);m.append(head);
  if(things.length>1){const ch=document.createElement('div');ch.className='ic-chips';things.forEach((t,k)=>{const b=document.createElement('button');b.textContent=t.title;b.setAttribute('aria-pressed',String(k===cur));b.title=t.title+'\n'+(t.sub||'')+'\nClick: what you can do with it';b.addEventListener('click',()=>{cur=k;draw();queueRegions()});ch.append(b)});m.append(ch)}
  const act=(label,a,val,cls,tp)=>{const b=document.createElement('button');b.setAttribute('role','menuitem');b.className='ic-act'+(cls?' '+cls:'');b.innerHTML='<i>'+icGlyph(label,a)+'</i><span>'+esc(label)+'</span>';const tip=tp||icTip(label,a);b.title=label+(tip?'\n'+tip:'');b.addEventListener('click',()=>{if(a==='cardtab'){const t=document.querySelector('#heroframe [data-hftab="'+val+'"]');if(t)t.click()}else send(a,val);v3menuClose();gameFocus()});return b};
  if(g){const body=document.createElement('div');body.className='ic-acts';const list=g.grid?g.acts.slice(0,1):g.acts;list.forEach(([l,a,v,tp],k)=>body.append(act(l,a,v,k===0?'primary':tp?'wide':'',tp)));m.append(body);
   if(g.grid){m.append(v3partGrid(g.grid));if(g.acts.length>1){const more=document.createElement('div');more.className='ic-acts';g.acts.slice(1).forEach(([l,a,v])=>more.append(act(l,a,v)));m.append(more)}}}
  const foot=tiles;if(foot.length){const f=document.createElement('div');f.className='ic-tile';for(const t of foot){const row=document.createElement('div');row.className='ic-tilerow';row.innerHTML='<small>'+esc(t.title)+(t.sub&&t.title!=='This tile'?' · '+esc(t.sub):'')+'</small>';t.acts.forEach(([l,a,v])=>row.append(act(l,a,v,g?'':'primary')));f.append(row)}m.append(f)}};
 draw();
 m.hidden=false;{const tip=$('partTip');if(tip)tip.hidden=true}   // the menu names the part: no tag over its title
 /* clamp in the HUD's own (zoomed) pixels: with a HUD scale above 1 the window's pixels let it run off the right and bottom edges (hud-craft) */
 {const place=()=>{const k=hudKC()||1,VW=innerWidth/k,VH=innerHeight/k,W=m.offsetWidth||320,H=Math.min(m.offsetHeight||m.scrollHeight,VH*0.7);m.style.left=Math.max(12,Math.min(mx+12,VW-W-12))+'px';m.style.top=Math.max(12,Math.min(my,VH-H-12))+'px'};place();requestAnimationFrame(()=>{if(!m.hidden)place()})/* again once lines added after opening (rts-feel's hint) are in */}queueRegions()}
document.addEventListener('keydown',e=>{if(e.key==='Escape')v3menuClose()});
// Your own units always show; others only on tiles in sight.
// Fog of war (Fog.dm): the server sends what you have explored for the 3D area (2 explored, 0 never seen) and the sight
// circles of your units, workshops and allies (x, y, r, and your unit's ref). The page draws the circles itself, each
// following its unit as it walks, soft at the edge (the user, 20:1x: "more like a circle, like the mist"), into a small
// texture (r in sight, g explored) that the shader turns into a drifting mist; the look eases as sight changes.
function v3fogData(f){if(!f||typeof f.s!=='string'){V3.fog=null;return}const O=V3.fog,n=f.w*f.h;
 let ex=O&&O.s===f.s&&O.x0===f.x0&&O.y0===f.y0&&O.w===f.w&&O.h===f.h?O.ex:null;
 if(!ex){ex=new Float32Array(n);for(let k=0;k<n;k++)ex[k]=f.s.charCodeAt(k)===50?1:0}
 let cur=null;if(O&&O.z===f.z){cur=new Float32Array(n*2);for(let j=0;j<f.h;j++)for(let i=0;i<f.w;i++){const oi=f.x0+i-O.x0,oj=f.y0+j-O.y0,k=(j*f.w+i)*2;if(oi>=0&&oj>=0&&oi<O.w&&oj<O.h){const q=(oj*O.w+oi)*2;cur[k]=O.cur[q];cur[k+1]=O.cur[q+1]}else cur[k+1]=ex[j*f.w+i]}}
 V3.fog={x0:f.x0,y0:f.y0,w:f.w,h:f.h,z:f.z,s:f.s,ex,circles:Array.isArray(f.c)?f.c:[],cur:cur||new Float32Array(n*2),tgt:new Float32Array(n*2),px:new Uint8Array(n*4),stampAt:0,ver:(O?O.ver:0)+1,tex:O&&O.tex,texW:O&&O.w===f.w&&O.h===f.h?O.texW:0,texH:O&&O.w===f.w&&O.h===f.h?O.texH:0,init:!cur,up:1}}
// The circles into the target: in sight 1 inside, fading out over the last two and a half tiles; explored where you
// have been or see now.
function v3fogStamp(F){const T=F.tgt,W=F.w,H=F.h,n=W*H;for(let k=0;k<n;k++){T[k*2]=0;T[k*2+1]=F.ex[k]}
 for(const c of F.circles){let x=c[0],y=c[1];const r=c[2]||0;if(c[3]){const d=V3.disp.get(c[3]);if(d&&d.dx!=null){x=d.dx;y=d.dy}}
  const R=r+1.5,i0=Math.max(0,Math.floor(x-R-F.x0)),i1=Math.min(W-1,Math.ceil(x+R-F.x0)),j0=Math.max(0,Math.floor(y-R-F.y0)),j1=Math.min(H-1,Math.ceil(y+R-F.y0));
  for(let j=j0;j<=j1;j++){const dy=F.y0+j-y;for(let i=i0;i<=i1;i++){const dx=F.x0+i-x,d=Math.sqrt(dx*dx+dy*dy);let v=(r+1-d)/2.5;if(v<=0)continue;if(v>1)v=1;v=v*v*(3-2*v);const k=(j*W+i)*2;if(v>T[k])T[k]=v;if(v>T[k+1])T[k+1]=v;if(v>0.5)F.ex[j*W+i]=1}}}}
function v3fogFrame(L,dt,under){const gl=V3.gl,F=V3.fog;V3.fogLive=false;if(!F||under||F.z!==V3.z){gl.uniform1f(L.fogon,0);return}V3.fogLive=true;
 const now=performance.now();if(now-F.stampAt>60){F.stampAt=now;v3fogStamp(F);if(F.init){F.cur.set(F.tgt);F.init=false}}
 let moved=!F.texW||F.up;const k=Math.min(1,dt*6);for(let q=0;q<F.cur.length;q++){const d=F.tgt[q]-F.cur[q];if(d>0.003||d<-0.003){F.cur[q]+=d*k;moved=true}else if(d){F.cur[q]=F.tgt[q];moved=true}}
 if(!F.tex)F.tex=V3.fogTex||(V3.fogTex=gl.createTexture());gl.activeTexture(gl.TEXTURE5);gl.bindTexture(gl.TEXTURE_2D,F.tex);
 if(moved){const P=F.px;for(let q=0,n=F.w*F.h;q<n;q++){P[q*4]=Math.round(F.cur[q*2]*255);P[q*4+1]=Math.round(F.cur[q*2+1]*255);P[q*4+2]=0;P[q*4+3]=255}
  if(F.texW!==F.w||F.texH!==F.h){gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,F.w,F.h,0,gl.RGBA,gl.UNSIGNED_BYTE,P);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.LINEAR);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.LINEAR);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);F.texW=F.w;F.texH=F.h}
  else gl.texSubImage2D(gl.TEXTURE_2D,0,0,0,F.w,F.h,gl.RGBA,gl.UNSIGNED_BYTE,P);F.ver++;F.up=0}
 gl.activeTexture(gl.TEXTURE0);gl.uniform1f(L.fogon,1);gl.uniform4f(L.fogr,F.x0,F.y0,F.w,F.h);gl.uniform2f(L.fogout,0,1);v3farFogBind(L)}
// The fog beyond its window (world-look 2026-10-25; the user: "the fog follow camera instead of only being viewable on
// units"). The fog's tiles come for the camera's window only, and land outside it was drawn as all explored, so the
// never-seen mist's edge was a box that moved with the camera. Outside the window the shader now reads this texture: the
// far view's explored marks (each tile's; each 4x4 cell's from an older server) and the sight circles of your units round
// the window and beyond it, 2 tiles a texel (r in sight, g explored, as the fog's own). Built when the far view, your far
// units or the circles change (each scene), not each frame; circles explore as they go until the next far view brings
// the server's marks. V3.farFogOff=1: drawn as before.
function v3farFogBuild(){const gl=V3.gl,D=V3.farData,F=V3.fog;
 if(V3.farFogOff||!gl||V3.z!==1&&V3.z!==3||!F||F.z!==V3.z||!Array.isArray(D)||!D.length)return null;
 let S=V3.farFog;if(!S||S.gl!==gl)S=V3.farFog={gl,tex:gl.createTexture(),tw:0,th:0,builds:0,ms:0};
 if(S.fd!==D){let cx0=1e9,cy0=1e9,cx1=-1e9,cy1=-1e9;for(const c of D){if(c[0]<cx0)cx0=c[0];if(c[1]<cy0)cy0=c[1];if(c[0]>cx1)cx1=c[0];if(c[1]>cy1)cy1=c[1]}
  const W=(cx1-cx0+1)*8,H=(cy1-cy0+1)*8,ex=new Uint8Array(W*H);   // explored: how many of a texel's 4 tiles
  for(const c of D){const R=c[4],bi=(c[0]-cx0)*8,bj=(c[1]-cy0)*8;
   if(Array.isArray(R)){for(let r=0;r<16;r++){const row=R[r]|0;if(!row)continue;const o=(bj+(r>>1))*W+bi;for(let b=0;b<16;b++)if(row&(1<<b))ex[o+(b>>1)]++}}
   else{const sm=typeof c[3]==='string'?c[3]:'';for(let q=0;q<16;q++)if(sm.charCodeAt(q)===49){const o=(bj+(q>>2)*2)*W+bi+(q&3)*2;ex[o]=ex[o+1]=ex[o+W]=ex[o+W+1]=4}}}
  S.fd=D;S.x0=cx0*16+1;S.y0=cy0*16+1;S.W=W;S.H=H;S.ex=ex;S.vis=new Float32Array(W*H);S.px=new Uint8Array(W*H*4);S.fu=S.fc=undefined}
 if(S.fu===V3.farUnits&&S.fc===F.circles)return S;
 const t0=performance.now(),W=S.W,H=S.H,ex=S.ex,vis=S.vis,P=S.px,C=new Map();S.fu=V3.farUnits;S.fc=F.circles;vis.fill(0);
 const add=(x,y,r)=>{if(!(r>0))return;const k=x*8192+y;if(!(C.get(k)>=r))C.set(k,r)};   // one circle a tile, the widest
 for(const c of F.circles)add(c[0],c[1],c[2]);
 for(const u of V3.farUnits||[])if(u[2]==='m')add(u[0],u[1],u[3]!=null?u[3]:V3.night?9:12);
 for(const [k,r] of C){const x=Math.floor(k/8192),y=k-x*8192,R=r+1.5,i0=Math.max(0,Math.floor((x-R-S.x0-0.5)/2)),i1=Math.min(W-1,Math.ceil((x+R-S.x0-0.5)/2)),j0=Math.max(0,Math.floor((y-R-S.y0-0.5)/2)),j1=Math.min(H-1,Math.ceil((y+R-S.y0-0.5)/2));
  for(let j=j0;j<=j1;j++){const dy=S.y0+j*2+0.5-y;for(let i=i0;i<=i1;i++){const dx=S.x0+i*2+0.5-x;let v=(r+1-Math.sqrt(dx*dx+dy*dy))/2.5;if(v<=0)continue;if(v>1)v=1;v=v*v*(3-2*v);const q=j*W+i;if(v>vis[q])vis[q]=v;if(v>0.5)ex[q]=4}}}
 for(let q=0,n=W*H;q<n;q++){const s=vis[q]*255;P[q*4]=Math.round(s);P[q*4+1]=Math.round(Math.max(s,ex[q]*63.75));P[q*4+2]=0;P[q*4+3]=255}
 gl.activeTexture(gl.TEXTURE6);gl.bindTexture(gl.TEXTURE_2D,S.tex);
 if(S.tw!==W||S.th!==H){gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,W,H,0,gl.RGBA,gl.UNSIGNED_BYTE,P);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.LINEAR);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.LINEAR);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);S.tw=W;S.th=H}
 else gl.texSubImage2D(gl.TEXTURE_2D,0,0,0,W,H,gl.RGBA,gl.UNSIGNED_BYTE,P);
 gl.activeTexture(gl.TEXTURE0);S.builds++;S.ms=performance.now()-t0;return S}
function v3farFogBind(L){const gl=V3.gl,S=v3farFogBuild();V3.farFogOn=!!S;gl.uniform1f(L.faron,S?1:0);if(!S)return;
 gl.activeTexture(gl.TEXTURE6);gl.bindTexture(gl.TEXTURE_2D,S.tex);gl.activeTexture(gl.TEXTURE0);gl.uniform4f(L.farr,S.x0,S.y0,S.W*2,S.H*2)}
// A tile's fog state for the minimap: 1 in sight, 2 explored, 0 never seen; 1 where there is no fog.
function v3fogAt(x,y){const F=V3.fog;if(!F||F.z!==V3.z)return '1';const i=x-F.x0,j=y-F.y0;if(i<0||j<0||i>=F.w||j>=F.h)return '2';const k=(j*F.w+i)*2;return F.cur[k]>0.5?'1':F.cur[k+1]>0.5?'2':'0'}
function v3visible(t){const S=V3.seen;if(!S||t.ly||t.kind==='mine')return true;const i=t.x-S.x0,j=t.y-S.y0;if(i<0||j<0||i>=S.w||j>=S.h)return true;return S.s[j*S.w+i]==='1'}
// Box select: your units whose drawn body is inside the box on screen (a turned camera
// makes the ground under the box a slanted shape, and units stand above their tile).
function v3boxRefs(x0,y0,x1,y1){const c=$('world3d'),r=c.getBoundingClientRect(),l=Math.min(x0,x1)-r.left,h=Math.max(x0,x1)-r.left,t=Math.min(y0,y1)-r.top,b=Math.max(y0,y1)-r.top;
 return V3.things.filter(u=>u.kind==='mine'&&u.ref&&u.dx!=null&&v3visible(u)).filter(u=>{const p=v3project([u.dx,0.55+v3groundAt(u.dx,u.dy),-u.dy]);return p&&p[0]>=l&&p[0]<=h&&p[1]>=t&&p[1]<=b}).map(u=>u.ref)}
function v3pickThing(mx,my){let best=null,bd=26,bs=null,bsd=42;for(const t of V3.things){if(t.dx==null||(t.ly&&(t.ly<0&&t.feet==null||t.fly||t.kind!=='mine'))||t.nopick||!v3visible(t))continue;const g=t.ly?t.ly:v3groundAt(t.dx,t.dy),ip=t.kind==='item',   /* one of yours up on the rock or a wall-walk (t.ly over 0) where it is drawn, at its feet's height: a click on it picks it (anyone else's up there: the click goes to the walk or the rock, as before) */s=v3project([t.dx+(ip?(t.px||0)+((t.iw||1)-1)/2:0),(ip?0.25:0.55)+g,-t.dy-(ip?(t.py||0):0)]);   /* an item where it is drawn (its pixel offsets) */if(!s)continue;let d=Math.hypot(s[0]-mx,s[1]-my);const pr=t.kind==='item'?6:0;
  // a flyer where it is drawn, up in the air (and still by its shadow); a great beast anywhere over the ground its legs,
  // head and wings stand on (Beasts.dm parts)
  const kd=t.key&&V3.disp.get(t.key),alt=kd&&kd.alt||0;if(alt>0.3){const sa=v3project([t.dx,g+alt+(t.beast?0.5*(t.beast.size||1):0.55),-t.dy]);if(sa)d=Math.min(d,Math.hypot(sa[0]-mx,sa[1]-my)*(t.beast?0.6:1))}
  if(t.beast&&!t.beast.dead)for(const q of arr(t.beast.parts)){const [PX,,PZ]=v3world({dx:q[0],dy:q[1]}),sp=v3project([PX,v3groundAt(q[0],q[1])+0.5,PZ]);if(sp)d=Math.min(d,Math.hypot(sp[0]-mx,sp[1]-my))}
  if(t.g3pc){const sp=v3project([t.g3pc[0],g+0.15,t.g3pc[1]]);if(sp)d=Math.min(d,Math.hypot(sp[0]-mx,sp[1]-my))}   /* a body where its death doll lies (gear3d.js g3poses) */
  if(d+pr<bd){bd=d+pr;best=t}if(t.kind==='station'&&d<bsd){bsd=d;bs=t}}
 // a workshop is bigger than a unit: when nothing else is under the pointer it takes clicks from further off (one half
 // hidden under a tree canopy was missed, and the click felled the tree instead)
 return best||bs}
// The floor of a ramp tile under world point (px, pz): a run carved up a mountain rises along its way as v3carveRock
// draws it; a ramp up a wall is taken at its middle height.
function v3rampFloor(K,tx,ty,px,pz){if(K.kind==='carve'&&K.carve){const [k,n,dir,top]=K.carve,Ht=top+0.4,h0=Ht*(k-1)/n,h1=Ht*k/n,ux=dir&4?1:dir&8?-1:0,uz=dir&1?-1:dir&2?1:0,u=Math.max(-0.5,Math.min(0.5,(px-tx)*ux+(pz+ty)*uz));return h0+(u+0.5)*(h1-h0)}return (V3.rampH&&V3.rampH.get(tx+','+ty))||0}
// With green blocks in reach (Gather on), rock that isn't one of them is marked far: a click there walks (rts-feel sends it
// as walk3d), on a mountain top along the top, on a dug-out floor to that floor.
function v3pickTile(mx,my){const r=v3pickTile0(mx,my);if(!r||r.ghost||!(model&&model.gather)||!(V3.reach&&V3.reach.size))return r;const K=v3kindAt(r.x,r.y);if(K&&(K.kind==='wall'&&K.blocks||r.roof&&K.roof)){r.far=true;if(r.lvl){r.up=true;r.peak=true}}return r}
function v3pickTile0(mx,my){if(!V3.inv)return null;const c=$('world3d');const nx=mx/c.clientWidth*2-1,ny=1-my/c.clientHeight*2;const un=(x,y,z)=>{const m=V3.inv;const X=x*m[0]+y*m[4]+z*m[8]+m[12],Y=x*m[1]+y*m[5]+z*m[9]+m[13],Z=x*m[2]+y*m[6]+z*m[10]+m[14],W=x*m[3]+y*m[7]+z*m[11]+m[15];return [X/W,Y/W,Z/W]};
 const a=un(nx,ny,-1),b=un(nx,ny,1);const dy=b[1]-a[1];if(Math.abs(dy)<1e-6)return null;const k=-a[1]/dy;if(k<0)return null;
 // Walk the ray toward the ground: the first wall, rock, tree or built tile it passes through is what was clicked
 // (clicking a cliff face digs that cliff, like clicking it on the map). Rock or a tree drawn faded at the pointer (over a
 // unit, the point looked at, or close to the eye: v3fadedAt) isn't clickable: the ray passes through it to what is behind.
 const T=V3.terrain;if(T&&Array.isArray(T.tiles)){const H={wall:1.2,block:1.2,built:V3.STOREY,tree:5.2};const stk=(K,tx,ty)=>T.z===1&&K.kind==='wall'&&K.blocks&&V3.rockGeo&&V3.rockGeo.get(tx+','+ty)&&V3.rockGeo.get(tx+','+ty).stack,top=(K,tx,ty)=>K.kind==='tree'?MD.treeTop(K,tx,ty):K.kind==='wall'?(stk(K,tx,ty)?v3peakTop(tx,ty)+0.06:Math.max(1.2,v3groundAt(tx,ty))):K.kind==='built'&&V3.walkTiles&&V3.walkTiles.has(tx+','+ty)?V3.STOREY+0.4:H[K.kind];const steps=Math.ceil(k*Math.hypot(b[0]-a[0],b[1]-a[1],b[2]-a[2])/0.08);
  let pk='',gk='';const gth=!!(model&&model.gather),gR=gth&&V3.reach&&V3.reach.size?V3.reach:null;
  // Gather on, with blocks in reach of your selected units (V3.reach, rts-feel's rfReach, outlined green): those are the
  // only rock a click mines (the user, 2026-10-24: "make the green blocks be the only ones selectable"). The first of them
  // along the ray is taken, solid, faded or cut away, through any other rock in front; other rock is a walk (v3pickTile).
  if(gR)for(let n=0;n<=steps;n++){const f=k*n/Math.max(1,steps),px=a[0]+(b[0]-a[0])*f,py=a[1]+(b[1]-a[1])*f,pz=a[2]+(b[2]-a[2])*f;if(py>10)continue;const tx=Math.round(px),ty=Math.round(-pz),i=tx-T.x0,j=ty-T.y0;if(i<0||j<0||i>=T.w||j>=T.h)continue;
   const c=T.tiles[j*T.w+i],K=c?T.kinds[c-1]:null,kk=Math.floor(py);if(!K||kk<0||!gR.has(tx+','+ty+','+kk)||!v3stackHas(K,kk)||K.kind==='wall'&&py>top(K,tx,ty))continue;return K.kind==='wall'?{x:tx,y:ty,blk:kk,ghost:true}:{x:tx,y:ty,blk:kk,ghost:true,roof:true}}
  for(let n=0;n<=steps;n++){const f=k*n/Math.max(1,steps);const px=a[0]+(b[0]-a[0])*f,py=a[1]+(b[1]-a[1])*f,pz=a[2]+(b[2]-a[2])*f;if(py>10)continue;const tx=Math.round(px),ty=Math.round(-pz);const i=tx-T.x0,j=ty-T.y0;if(i<0||j<0||i>=T.w||j>=T.h)continue;const c=T.tiles[j*T.w+i];const K=c?T.kinds[c-1]:null;const inCut=v3mcutTile(tx,ty);if(K&&(K.kind==='carve'||K.kind==='ramp')&&py<=v3rampFloor(K,tx,ty,px,pz)+0.03)return {x:tx,y:ty};   /* a ramp or steps: its slope, not the rock behind it (a click up a ramp mined it, 2026-10-24) */if(K&&K.roof&&K.kind!=='wall'&&!inCut){const c0=K.ceil||2;if(py>=c0&&py<=c0+K.roof+0.4&&(T.z!==1||v3stackHas(K,Math.min(Math.floor(py),c0+K.roof-1)))&&!v3fadedAt(mx,my,px,py,pz,'rock'))return {x:tx,y:ty,roof:true}}if(K&&H[K.kind]&&py<=(inCut?Math.min(top(K,tx,ty),v3mcutLim(tx,ty)):top(K,tx,ty))&&!(T.z===1&&K.kind==='wall'&&K.blocks&&!v3stackHas(K,Math.max(0,Math.min(Math.floor(py),K.blocks-1))))&&!((K.kind==='wall'||K.kind==='block')&&v3fadedAt(mx,my,px,py,pz,'rock')||K.kind==='tree'&&v3fadedAt(mx,my,px,py,pz,'tree'))){const peak=K.kind==='wall'&&!!K.blocks&&!(inCut&&top(K,tx,ty)>v3mcutLim(tx,ty)+0.05)&&(pk===tx+','+ty||stk(K,tx,ty)&&py>=top(K,tx,ty)-0.18)&&!!(V3.upperTiles&&V3.upperTiles.has(tx+','+ty));   /* a rock cut by the cutaway: its top there is the block cut through, not the mountain top */
   /* down through a block mined out onto the one under it: a dug-out floor inside the mountain (Gather.dm), walked to with Gather off, its block mined with it on */const lb=Math.floor(py),lvl=!peak&&stk(K,tx,ty)&&gk===tx+','+ty+','+(lb+1)&&!!(V3.upperTiles&&V3.upperTiles.has(tx+','+ty))?lb+1:0;if(lvl)return {x:tx,y:ty,up:!gth,peak:!gth,lvl};
   return {x:tx,y:ty,up:(K.kind==='built'&&!!(V3.walkTiles&&V3.walkTiles.has(tx+','+ty)))||peak,peak}}if(K&&stk(K,tx,ty)&&py<top(K,tx,ty)&&!v3stackHas(K,Math.floor(py)))gk=tx+','+ty+','+Math.floor(py);pk=tx+','+ty}}
 const X=a[0]+(b[0]-a[0])*k,Z=a[2]+(b[2]-a[2])*k,rx=Math.round(X),ry=Math.round(-Z);if(V3.z===3){const K=v3kindAt(rx,ry);if(!K||K.kind==='void')return {x:rx,y:ry,sky:true}}   /* open sky on the Sky level: flyers fly there, walkers can't (Flying.dm RmOpenSky; rts-feel) */return {x:rx,y:ry}}
// The tag by the pointer: what's under it, and with units selected, what a click would do. A plain move says
// nothing (only a move with something to warn about, or another order, shows).
function v3hover(){const m=V3.mouse,tag=$('tag3d');
 {const U=model&&model.useon;if(U&&m&&!V3.drag){const t=v3pickThing(m.x,m.y),g=t&&arr(U.targets).find(x=>x.id===(t.ref||t.id));   // an item held (UseOn.dm)
  if(t){tag.hidden=false;tag.classList.toggle('warn',!g);text(tag,g?g.label:String(t.name||'').replace(/^\{[^}]*\}\s*/,'')+': not for the '+U.item);tag.style.left=m.x+'px';tag.style.top=m.y+'px';return}}}if(!m||V3.drag||document.elementFromPoint(m.x*hudKC(),m.y*hudKC())!==$('world3d')){if(!tag.hidden)tag.hidden=true;return}const t=v3pickThing(m.x,m.y);let hv=model&&model.hover&&arr(model.units).some(u=>u.selected)?model.hover:null;if(hv&&!t&&V3.hoverTile&&V3.hoverTile.far)hv=null;   /* not a green block: a click walks there (v3pickTile) */if(hv&&hv.x!=null){const ht=t?{x:t.x,y:t.y}:V3.hoverTile;if(!ht||ht.x!==hv.x||ht.y!==hv.y||(hv.on==='thing')!==!!t)hv=null}   /* only the verdict for the spot under the pointer (HoverCheck.dm), never a stale one */if(hv&&hv.kind==='Move'&&hv.text==='Move'&&!hv.bad)hv=null;if(!hv&&typeof rfLocalVerb==='function'){const lv=rfLocalVerb(t);if(lv)hv={text:lv,kind:lv,bad:0}}   /* the verb at once, before (or without) the game's verdict (rts-feel) */if(!t&&!hv){if(!tag.hidden)tag.hidden=true;return}tag.hidden=false;tag.classList.toggle('warn',!!(hv&&hv.bad));text(tag,(t?hcNiceName(t.name)+(t.look?' · '+t.look:''):'')+(hv&&hv.text?(t?' — ':'')+String(hv.text).split(ownTag()||'\u0000').join(''):''));const L=m.x+'px',Tp=m.y+'px';if(tag.style.left!==L)tag.style.left=L;if(tag.style.top!==Tp)tag.style.top=Tp}
// Right-drag pans: the ground under the mouse follows it. Units per pixel at the
// camera target come from the 0.8 rad field of view; screen-vertical movement is
// stretched by the camera pitch because it runs along the ground.
// A camera lock (Lock camera on a unit) follows the unit: it centres it once, then moves with it, so the player can
// still pan, turn, tilt and zoom freely; the angle, height, zoom and the iso view stay as the player set them. Hero mode with Follow on: a low chase camera behind the hero. It turns to the
// hero's facing as they walk, unless the player turned the camera in the last 4 s.
function v3chase(dt){const P=model&&model.play;const lock=P&&P.lock,ref=P&&(lock||(P.mode==='hero'&&P.follow?P.hero:null));if(!ref){V3.chased=null;V3.lockOn=null;V3.lockT=null;return}
 const H=V3.things.find(t=>(t.ref||t.id)===ref);if(!H||H.dx==null)return;
 if(lock){V3.chased=null;V3.lockT=H;if(V3.lockOn!==lock){V3.lockOn=lock;V3.lockAt=[H.dx,H.dy];V3.tcx=V3.cx=H.dx;V3.tcy=V3.cy=H.dy;V3.panAt=performance.now();return}
  const ux=H.dx-V3.lockAt[0],uy=H.dy-V3.lockAt[1];V3.lockAt=[H.dx,H.dy];if(ux||uy){V3.tcx+=ux;V3.tcy+=uy;V3.cx+=ux;V3.cy+=uy;V3.panAt=performance.now()}return}
 if(V3.chased!==ref){V3.chased=ref;V3.pitch=0.2;V3.dist=Math.min(V3.dist,8);V3.userTurn=0}
 V3.tcx=V3.cx=H.dx;V3.tcy=V3.cy=H.dy;V3.panAt=performance.now();if(V3.drag||performance.now()-(V3.userTurn||0)<4000)return;
 const d=H.dir||2,fx=(d&4?1:0)-(d&8?1:0),fy=(d&1?1:0)-(d&2?1:0);if(!fx&&!fy)return;const want=Math.atan2(-fx,fy);let diff=want-V3.yaw;diff=Math.atan2(Math.sin(diff),Math.cos(diff));V3.yaw+=diff*Math.min(1,dt*2.5)}
// Plain unexplored ground out to the horizon (surface only), so the edge of the
// loaded world isn't open sky: a grid of 40-unit tiles around the camera, rebuilt
// when the camera has moved 80 units. The far view and the detailed area draw over it.
// The old one stays drawn while the next is built a few ms a frame (v3bgWork; at once it took 4-10 ms); with none yet, at once.
function v3horizon(x,z){const H=V3.hor,night=false;   /* lit by the shader like the near ground (darkening it here too made it twice as dark as the land in front at night) */if(H&&!H.stale&&Math.abs(H.x-x)<30&&Math.abs(H.z-z)<30&&H.night===night)return H;
 if(H&&V3.horJob)return H;const J=v3horJob(x,z,night);J.next();if(H){V3.horJob=J;return H}while(!J.next().done);return V3.hor}
function* v3horJob(x,z,night){const gl=V3.gl;
 // Painted like the near ground: smooth light/dark patches and a warm tint per
 // corner (MD.groundCorner's noise), grass tufts and pebbles out to ~44 tiles,
 // coarser cells beyond that out to the horizon.
 const G=V3.groundAvg||[0.3,0.45,0.26,1],nk=night?[0.35,0.38,0.42]:[1,1,1],T=V3.terrain,grass=V3.groundGrass,a=(V3.horV||(V3.horV=new VA())).reset();yield;   /* reused: a plain array grown to millions of numbers cost tens of ms */
 const memo=new Map(),col=(wx,wy)=>{const key=wx*100003+wy;let c=memo.get(key);if(c)return c;c=col0(wx,wy);memo.set(key,c);return c},col0=(wx,wy)=>{const v=0.86+MD.vn(wx,wy,7,3)*0.2+MD.h(Math.round(wx),Math.round(wy),11)*0.06,warm=(MD.vn(wx,wy,11,4)-0.5)*0.08;return [(G[0]*v+warm)*nk[0],(G[1]*v+warm*0.5)*nk[1],G[2]*v*nk[2],1]};
 const inNear=(tx,ty)=>T&&tx>=T.x0&&tx<T.x0+T.w&&ty>=T.y0&&ty<T.y0+T.h;
 const cx=Math.round(x),cz=Math.round(z);let Y=-0.16;
 const cell=(x0,z0,S,detail)=>{const x1=x0+S,z1=z0-S;quad4(a,[x0,Y,z0],[x1,Y,z0],[x1,Y,z1],[x0,Y,z1],[0,1,0],col(x0,-z0),col(x1,-z0),col(x1,-z1),col(x0,-z1));
  if(!detail)return;for(let q=0;q<S*S;q++){const tx=Math.round(x0+0.5+(q%S)),ty=Math.round(-(z0-0.5-Math.floor(q/S)));if(inNear(tx,ty))continue;const r=MD.h(tx,ty,12);
   if(grass&&r<0.14)MD.blob(a,tx+(MD.h(tx,ty,13)-0.5)*0.6,Y+0.05,-ty+(MD.h(tx,ty,14)-0.5)*0.6,0.12,0.07,0.12,MD.shade(col(tx,ty),1.15),tx*7+ty,0.35);
   else if(r>0.96)MD.blob(a,tx+(MD.h(tx,ty,15)-0.5)*0.6,Y+0.03,-ty+(MD.h(tx,ty,16)-0.5)*0.6,0.07,0.05,0.07,[0.5*nk[0],0.48*nk[1],0.45*nk[2],1],tx+ty*7,0.3)}};
 const IN=64;for(let j=-IN;j<IN;j+=2){yield;for(let i=-IN;i<IN;i+=2)cell(cx+i-0.5,cz-j+0.5,2,Math.abs(i)<44&&Math.abs(j)<44)}
 // coarse ring: skip only cells wholly inside the fine square, and sit a hair lower where they overlap it
 Y=-0.18;const S=20,OUT=560;for(let j=-OUT;j<OUT;j+=S){yield;for(let i=-OUT;i<OUT;i+=S){if(i>=-IN&&i+S<=IN&&j>=-IN&&j+S<=IN)continue;cell(cx+i-0.5,cz-j+0.5,S,false)}}
 if(V3.hor)gl.deleteBuffer(V3.hor.buf);const buf=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,buf);gl.bufferData(gl.ARRAY_BUFFER,a.f.subarray(0,a.length),gl.STATIC_DRAW);V3.hor={buf,count:a.length/12,x,z,night}}
// Work a few ms a frame: pictures to the GPU (v3tex; at least one a frame), then jobs drawn as they were until they
// are done: the far view (v3buildFar), the horizon (v3horizon).
function v3bgWork(ms){if(ms<0.5)return;const t0=performance.now(),Q=V3.texQ;for(let n=0;Q&&Q.length&&(!n||performance.now()-t0<ms);n++){const [img,e]=Q.shift();v3texUpload(img,e)}for(const k of ['farJob','horJob'])while(V3[k]&&performance.now()-t0<ms)if(V3[k].next().done)V3[k]=null}
// The detailed area follows the zoom, and grows when the camera looks toward the
// horizon (the eye then sits near its edge).
function v3sizeCheck(){if(!V3.on)return;const d=Math.round(Math.max(V3.dist,V3.pitch<0.35?26:0));if(d!==V3.sentDist){V3.sentDist=d;send('view3dsize',String(d))}}
function v3panDrag(d,dx,dy){if(!d.unfollow&&model&&model.play&&model.play.follow&&!model.play.lock){d.unfollow=1;send('follow','')}const H=$('world3d').clientHeight||innerHeight;const u=2*V3.dist*Math.tan(0.4)/H,v=u/Math.max(0.35,Math.sin(V3.pitch));
 const f=[-Math.sin(V3.yaw),Math.cos(V3.yaw)],r=[Math.cos(V3.yaw),Math.sin(V3.yaw)];
 V3.tcx=d.tcx-dx*u*r[0]+dy*v*f[0];V3.tcy=d.tcy-dx*u*r[1]+dy*v*f[1];V3.panAt=performance.now();v3panSend(false)}
function v3panSend(now){clearTimeout(V3.panT);const go=()=>{V3.panLast=performance.now();V3.camSeq=(V3.camSeq||0)+1;send('camera',Math.round(V3.tcx)+','+Math.round(V3.tcy)+','+V3.camSeq)};/* + its count: scenes say which they were begun after (hud-craft, 10-25) */if(now||performance.now()-(V3.panLast||0)>150)go();else V3.panT=setTimeout(go,150)}
// 2D map: the Mac app reports right-drags over the map (not over HUD panels) in
// window points; the game turns them into tiles of its own view.
let panAcc=null;window.remasterPanPx=function(dx,dy,w,h,done){if(V3.on)return;panAcc=panAcc||{x:0,y:0};panAcc.x+=dx;panAcc.y+=dy;const go=()=>{if(!panAcc)return;const a=panAcc;panAcc=null;clearTimeout(window.panT2);if(a.x||a.y)send('panpx',[a.x,a.y,w,h].map(n=>Math.round(n)).join('|'))};clearTimeout(window.panT2);if(done||performance.now()-(window.panLast2||0)>90){window.panLast2=performance.now();go()}else window.panT2=setTimeout(()=>{window.panLast2=performance.now();go()},90)};
// F9 locks the camera on the one selected unit (or frees it). The game has the same
// shortcut; this one covers the times the HUD has the keyboard.
addEventListener('keydown',e=>{if(e.key!=='F9'||e.metaKey||e.ctrlKey||e.altKey)return;e.preventDefault();send('chasecam','')});
// Isometric camera (the default): starts on a diagonal ~37 degrees down, through a long lens so the land
// looks nearly flat-projected. The camera still turns and tilts freely; Top, North and the chase camera leave it.
function v3isoOn(){return V3.iso&&!V3.chased&&!V3.cine&&!V3.top}
function v3iso(on,snap){V3.iso=!!on;try{localStorage.setItem('dm3dIso',on?'1':'0')}catch(e){}const b=$('camIso');if(b)b.setAttribute('aria-pressed',on?'true':'false');
 // Start from (or, with the button, return to) the iso angle: ~37 degrees down on the nearest diagonal. Turning
 // (right-drag, Q/E) and tilting stay free; the long lens stays while Iso is on.
 if(on&&(snap||!V3.isoSeen)){V3.isoSeen=true;const q=Math.PI/2;V3.turnTo=V3.isoSeen&&snap?Math.round((V3.yaw-q/2)/q)*q+q/2:null;if(!snap)V3.yaw=Math.PI/4;V3.pitch=V3.ISOPITCH}}
// Fires that light their surroundings: flames, campfires, forges, smelters, melters, lava vents and hellgates;
// the eight nearest the camera's target. Brighter at night and underground.
function v3fireLights(tgt,under){const L=V3.loc,gl=V3.gl,P=new Float32Array(32),C=new Float32Array(24),dark=V3.night||under,list=[];
 for(const t of V3.things){const m=t.m3||'';let r=0,c=null;if(t.flame){r=4.5;c=[1.0,0.55,0.2]}else if(t.beast&&t.beast.breath==='fire'&&/breathe/.test(t.beast.anim)){r=7;c=[1.0,0.5,0.15]}else if(m==='station:campfire'){r=5;c=[1.0,0.58,0.24]}else if(m==='station:altar'&&t.mat==='evil'){r=3;c=[0.9,0.16,0.08]}else if(/^station:(forge|smelter|melter)/.test(m)&&t.half!=='R'){r=4;c=[1.0,0.5,0.18]}else if(t.vent||t.hellgate){r=5;c=[1.0,0.32,0.12]}else if(t.glow){r=t.glow[0];c=[t.glow[1],t.glow[2],t.glow[3]]}else continue;
  const [X,,Z]=v3world(t);const d=Math.hypot(X-tgt[0],Z-tgt[2]);if(d<60)list.push([d,X,v3groundAt(t.x,t.y)+0.6,Z,r,c])}
 for(const p of V3.torchList||[]){const d=Math.hypot(p[0]-tgt[0],p[2]-tgt[2]);if(d<60)list.push([d,p[0],p[1],p[2],4,[1.0,0.56,0.2]])}
 for(const p of V3.hoardList||[]){const d=Math.hypot(p[0]-tgt[0],p[2]-tgt[2]);if(d<40)list.push([d+2,p[0],p[1],p[2],5,[0.5,0.4,0.2]])}   // a dragon's gold glows as if the sun were on it
 list.sort((a,b)=>a[0]-b[0]);const k=under?1.35:0.35+Math.min(1,V3.G?V3.G.nk:V3.night?1:0);   /* fires light more as the night deepens (no jump at dusk) */const tf=performance.now()/1000;const d9=list.length>8?list[8][0]:1e9;list.slice(0,8).forEach((e,i)=>{const sd=e[1]*1.7+e[3]*2.3,fl=0.9+0.1*Math.sin(tf*11+sd)*Math.sin(tf*6.3+sd*1.9),w=Math.min(1,(d9-e[0])/3);   /* firelight flickers a little; with more than 8 lights in reach, one about to give its place to a nearer one fades over its last 3 tiles (it went out at once as the camera moved) */
  P[i*4]=e[1];P[i*4+1]=e[2];P[i*4+2]=e[3];P[i*4+3]=e[4]*(0.97+0.03*fl);C[i*3]=e[5][0]*k*fl*w;C[i*3+1]=e[5][1]*k*fl*w;C[i*3+2]=e[5][2]*k*fl*w});
 gl.uniform4fv(L.lp,P);gl.uniform3fv(L.lc,C)}
// Two units on one wall-walk tile stand in two ranks across the wall: the wall's own direction comes
// from its neighbours on the ground layer; the first (by reference) takes the side towards -x/-y.
function v3ranks(){const by=new Map();for(const t of V3.things){if(!t.ly||!V3.walkTiles||!V3.walkTiles.has(t.x+','+t.y))continue;const k=t.x+','+t.y;if(!by.has(k))by.set(k,[]);by.get(k).push(t)}
 const T=V3.terrain,built=(x,y)=>{if(!T)return false;const i=x-T.x0,j=y-T.y0;if(i<0||j<0||i>=T.w||j>=T.h)return false;const c=T.tiles[j*T.w+i];const K=c?T.kinds[c-1]:null;return !!K&&K.kind==='built'};
 for(const [k,list] of by){if(list.length<2){list.forEach(t=>{t.px=0;t.py=0});continue}const t0=list[0];const ew=built(t0.x-1,t0.y)||built(t0.x+1,t0.y),ns=built(t0.x,t0.y-1)||built(t0.x,t0.y+1);const across=ew&&!ns?[0,1]:[1,0];
  list.sort((a,b)=>String(a.key)<String(b.key)?-1:1).forEach((t,n)=>{const o=n===0?-0.22:0.22;t.px=across[0]*o;t.py=across[1]*o})}}
// A gate between two fortress walls: the walk carried over it on an arched lintel, crenellated like the walls.
// A round tower over a 3x3 block of wall: battered footing, coursed body, a corbelled crown with arrow slits, an
// open crenellated platform at walk height (its nine walk tiles), and a banner in the middle.
// The tower a wall tile belongs to, as its offset from the tower's centre tile, or null.
function v3towerAt(kindAt,i,j){const bw=(p,q)=>{const k=kindAt(p,q);return !!k&&k.kind==='built'},full=(p,q)=>{for(let u=-1;u<=1;u++)for(let v=-1;v<=1;v++)if(!bw(p+u,q+v))return false;return true};
 const isTower=(p,q)=>full(p,q)&&!full(p+1,q)&&!full(p-1,q)&&!full(p,q+1)&&!full(p,q-1);for(let u=-1;u<=1;u++)for(let v=-1;v<=1;v++)if(isTower(i+u,j+v))return [u,v];return null}
function v3tower(a,X,Y,Z,tx,ty){const R=1.55,HW=V3.STOREY,N=28,sb=[0.6,0.57,0.52,0.99],st=k=>MD.shade(sb,k),seed=tx*31+ty*17;
 MD.prism(a,X,Z,Y,Y+0.55,R*1.08,R*1.01,N,st(0.76),seed);
 for(let r=0;r<4;r++){const y0=Y+0.55+r*(HW-0.85)/4;MD.prism(a,X,Z,y0,y0+(HW-0.85)/4,R*(1-r*0.004),R*(1-(r+1)*0.004),N,st(0.84+MD.h(tx,ty,r)*0.16),seed+r)}
 for(let k=0;k<N;k+=2){const an=(k+0.5)/N*6.2832,cx=X+Math.cos(an)*R*1.0,cz=Z+Math.sin(an)*R*1.0;boxr(a,cx-0.07,cx+0.07,cz-0.07,cz+0.07,Y+HW-0.42,Y+HW-0.3,st(0.8))}
 MD.prism(a,X,Z,Y+HW-0.3,Y+HW,R*1.08,R*1.09,N,st(0.95),seed+9);
 for(let k=0;k<N;k++){const t0=k/N*6.2832,t1=(k+1)/N*6.2832;tri(a,[X,Y+HW+0.004,Z],[X+Math.cos(t0)*R*1.08,Y+HW+0.004,Z+Math.sin(t0)*R*1.08],[X+Math.cos(t1)*R*1.08,Y+HW+0.004,Z+Math.sin(t1)*R*1.08],[0,1,0],st(0.8))}
 MD.prism(a,X,Z,Y+HW,Y+HW+0.26,R*1.09,R*1.09,N,st(0.9),seed+11);MD.prism(a,X,Z,Y+HW,Y+HW+0.26,R*0.99,R*0.99,N,st(0.72),seed+12);
 for(let m=0;m<10;m++){const an=m/10*6.2832,cx=X+Math.cos(an)*R*1.04,cz=Z+Math.sin(an)*R*1.04;boxr(a,cx-0.14,cx+0.14,cz-0.14,cz+0.14,Y+HW+0.26,Y+HW+0.56,st(0.92+MD.h(seed,m)*0.1));boxr(a,cx-0.155,cx+0.155,cz-0.155,cz+0.155,Y+HW+0.56,Y+HW+0.6,st(0.98))}
 for(let m=0;m<8;m++){const an=m/8*6.2832+0.39,cx=X+Math.cos(an)*(R+0.005),cz=Z+Math.sin(an)*(R+0.005);boxr(a,cx-0.04,cx+0.04,cz-0.04,cz+0.04,Y+0.9,Y+1.45,[0.08,0.07,0.07,1])}
 MD.prism(a,X,Z,Y+HW,Y+HW+1.6,0.035,0.03,6,[0.32,0.24,0.16,1],seed+20);const fy=Y+HW+1.55,fl=[0.62,0.12,0.1,1];quad(a,[X+0.03,fy,Z],[X+0.55,fy-0.05,Z],[X+0.55,fy-0.4,Z],[X+0.03,fy-0.35,Z],[0,0,0],fl);quad(a,[X+0.03,fy-0.35,Z],[X+0.55,fy-0.4,Z],[X+0.55,fy-0.05,Z],[X+0.03,fy,Z],[0,0,0],fl)}
// The way through a wall that carries a walk (a gate: a door in a one-tile gap between two walls). The walk is carried
// over it; the flanking walls decide its build. Local axes: u along the wall line, v across it (v>0 is +Z for a wall
// running east-west, +X for one running north-south); the outer face (walk faces from the server) gets the battlement
// or breastwork, the inner a lip or rail. The doors are the door object's (v3obj 'door', drawn as gate leaves here).
function v3gateGeom(kindAt,i,j,tx,ty){const b=(p,q)=>{const k=kindAt(p,q);return k&&k.kind==='built'?k:null};const ew=!!(b(i-1,j)&&b(i+1,j)),f=ew?b(i-1,j):b(i,j-1)||b(i,j+1),st=f&&f.state||'';
 const wood=!!f&&(!!f.wood||st.includes('wood')||st.includes('log')),face=V3.walkFace&&V3.walkFace.get(tx+','+ty)||0,bits=ew?[1,2]:[8,4];   // [v<0, v>0]
 const outerPos=face?!!(face&bits[1])&&!(face&bits[0])?1:!!(face&bits[0])&&!(face&bits[1])?-1:0:0;return {ew,wood,face,bits,outerPos}}
function v3gateArch(a,T,kindAt,i,j){const tx=T.x0+i,ty=T.y0+j,X=tx,Z=-ty,h=0.5,HW=V3.STOREY,G=v3gateGeom(kindAt,i,j,tx,ty),ew=G.ew;
 const bx=(u0,u1,v0,v1,y0,y1,c)=>{const U0=Math.min(u0,u1),U1=Math.max(u0,u1),V0=Math.min(v0,v1),V1=Math.max(v0,v1);if(ew)boxr(a,X+U0,X+U1,Z+V0,Z+V1,y0,y1,c);else boxr(a,X+V0,X+V1,Z+U0,Z+U1,y0,y1,c)};
 const P=(u,y,v)=>ew?[X+u,y,Z+v]:[X+v,y,Z+u],outer=s=>!G.face||!!(G.face&G.bits[s>0?1:0]);
 if(G.wood){
  // Timber gatehouse: four squared corner posts carry a lintel (knee-braced) over the way and a small shingled roof over
  // the fighting deck; boarded fill between lintel and deck; pointed logs on the outer side, a rail on the inner.
  const base=[0.47,0.33,0.21,1],dk=MD.shade(base,0.62),PT=HW+0.95;
  for(const su of [-1,1])for(const sv of [-1,1])bx(su*0.5,su*0.34,sv*0.46,sv*0.3,0,PT,MD.shade(dk,0.95+MD.h(tx+su,ty+sv,91)*0.1));
  for(const sv of [-1,1]){bx(-0.5,0.5,sv*0.47,sv*0.31,1.52,1.7,dk);for(const su of [-1,1])MD.rod(a,P(su*0.36,1.18,sv*0.39),P(su*0.18,1.6,sv*0.39),0.035,4,dk,tx+su+sv)}
  for(let q=0;q<4;q++){const y0=1.7+q*(HW-0.06-1.7)/4,c=MD.shade(base,0.72+MD.h(tx*5+q,ty,93)*0.14);bx(-0.34,0.34,-0.44,0.44,y0,y0+(HW-0.06-1.7)/4-0.01,c)}
  for(let q=0;q<5;q++){const u0=-h+q*0.2+0.004;bx(u0,u0+0.192,-h,h,HW-0.06,HW,MD.shade(base,0.92+MD.h(tx*3+q,ty,51)*0.16))}
  for(const sv of [-1,1]){const vo=sv*(h-0.075);
   if(outer(sv)){for(let q=1;q<5;q++){const u=-h+0.083+q*0.167,hh=HW+0.42+MD.h(tx*7+q,ty*3,sv+2)*0.12,c=MD.shade(base,0.78+MD.h(tx+q,ty,sv+9)*0.3),[x,,z]=P(u,0,vo);MD.prism(a,x,z,HW,HW+hh-HW,0.088,0.082,6,c,tx*31+ty*17+q);MD.cone(a,x,z,hh,hh+0.2,0.084,6,MD.shade(c,1.08),tx*13+ty+q)}}
   else MD.rod(a,P(-0.34,HW+0.42,sv*0.42),P(0.34,HW+0.42,sv*0.42),0.032,5,MD.shade(base,0.7),tx*3+ty)}
  // the roof: a gable along the wall line, eaves out past the posts, wooden shingles in courses; boarded gable ends
  const sh=[0.4,0.27,0.17,1],eave=PT,ridge=PT+0.5,ro=0.66,ul=0.6;
  for(const sv of [-1,1])for(let q=0;q<4;q++){const v0=sv*ro*(1-q/4),v1=sv*ro*(1-(q+1)/4),y0=eave+(ridge-eave)*q/4,y1=eave+(ridge-eave)*(q+1)/4,c=MD.shade(sh,0.85+(q%2)*0.1+MD.h(tx,ty,95+q)*0.06),n=ew?[0,ro,sv*(ridge-eave)]:[sv*(ridge-eave),ro,0];
   quad(a,P(-ul,y0,v0),P(ul,y0,v0),P(ul,y1,v1),P(-ul,y1,v1),n,c);quad(a,P(-ul,y0-0.06,v0),P(ul,y0-0.06,v0),P(ul,y0,v0),P(-ul,y0,v0),n,MD.shade(sh,0.6))}
  for(const su of [-1,1])tri(a,P(su*0.5,eave,-ro*0.9),P(su*0.5,eave,ro*0.9),P(su*0.5,ridge-0.03,0),ew?[su,0,0]:[0,0,su],MD.shade(base,0.7));
  MD.rod(a,P(-ul-0.04,ridge+0.02,0),P(ul+0.04,ridge+0.02,0),0.05,6,MD.shade(sh,0.7),tx+ty);
  // a torch on each outer post
  if(V3.torchList)for(const su of [-1,1]){const sv=G.outerPos||1,[x,,z]=P(su*0.42,0,sv*0.56);MD.prism(a,x,z,1.62,1.85,0.025,0.03,5,[0.2,0.15,0.1,1],tx+su);MD.blob(a,x,1.9,z,0.05,0.07,0.05,[1,0.62,0.22,1],tx*5+su,0.3);V3.torchList.push([x,1.95,z])}
  return}
 // Stone gate, in the walls' own courses: jamb piers, a round arch (its voussoirs and keystone proud of both faces), the
 // walls' corbelled ledge carried across, a parapet as the walls have it (outer: breastwork and one broad merlon with
 // coping; inner: a low lip), a raised portcullis showing its teeth under the arch, a torch sconce either side outside.
 const sb=[0.6,0.57,0.52,0.99],st=k=>MD.shade(sb,k*(0.92+MD.h(tx,ty,21)*0.16)),SP=1.3,R=0.4,soff=u=>SP+Math.sqrt(Math.max(0,R*R-u*u));
 for(const su of [-1,1])bx(su*0.5,su*R,-h,h,0,HW,st(0.86));
 for(let k=0;k<10;k++){const u0=-R+k*0.08,u1=u0+0.08;bx(u0,u1,-h,h,soff(Math.abs(u0+0.04)<0.001?0:(u0+u1)/2),HW,st(0.86))}
 for(const sv of [-1,1]){const v0=sv*h,v1=sv*(h+0.03);
  for(let k=0;k<=8;k++){const th=Math.PI*k/8,key=k===4,rm=R+0.08,cu=Math.cos(th)*rm,cy=SP+Math.sin(th)*rm,w=key?0.07:0.06,hh=key?0.11:0.07;bx(cu-w,cu+w,v0,v1,cy-hh,cy+hh,st(key?1.02:0.95))}
  bx(-h,h,v0,sv*(h+0.085),HW-0.15,HW-0.03,st(0.98));for(let m=0;m<4;m++){const u=-h+0.08+m*0.25;bx(u,u+0.09,v0,sv*(h+0.065),HW-0.27,HW-0.15,st(0.9))}
  const e0=sv*(h-0.13),e1=sv*h;
  if(outer(sv)){bx(-h,h,e0,e1,HW,HW+0.24,st(0.88));bx(-0.22,0.22,e0,e1,HW+0.24,HW+0.56,st(0.95));bx(-0.235,0.235,e0-sv*0.015,e1+sv*0.015,HW+0.56,HW+0.61,st(0.98));
   // portcullis teeth, raised, behind the outer arch (not where a real portcullis hangs: Gates.dm draws its own)
   if(!(V3.things||[]).some(t=>t.rune&&t.rune.id==='portcullis'&&t.x===tx&&t.y===ty))for(let q=0;q<7;q++){const u=-0.3+q*0.1;bx(u-0.012,u+0.012,sv*(h-0.16),sv*(h-0.13),soff(u)-0.2,soff(u),[0.2,0.2,0.22,1])}
   if(V3.torchList)for(const su of [-1,1]){const [x,,z]=P(su*0.62,0,sv*(h+0.08));MD.prism(a,x,z,1.35,1.55,0.025,0.03,5,[0.18,0.17,0.16,1],tx+su);MD.blob(a,x,1.6,z,0.05,0.07,0.05,[1,0.62,0.22,1],tx*5+su,0.3);V3.torchList.push([x,1.65,z])}}
  else bx(-h,h,e0,e1,HW,HW+0.13,st(0.88))}}
function v3wire(){const c=$('world3d');
 try{const v=localStorage.getItem('dm3dIso');if(v==='0')V3.iso=false}catch(e){}v3iso(V3.iso);$('camIso').addEventListener('click',()=>v3iso(V3.iso?false:true,true));
 c.addEventListener('contextmenu',e=>e.preventDefault());
 // After a click in 3D the keyboard goes back to the game, as a click on the map does,
 // so every original key works (arrows move the camera, Space pauses, Shift+Space deselects...).
 c.addEventListener('mouseup',()=>{if(V3.shop||V3.build)return;setTimeout(()=>{if($('menu3d').hidden)gameFocus()},0)});
 // Double-click: the map's double-click (workshops, stairs, items, corpses, "select all like this").
 c.addEventListener('dblclick',e=>{if(!V3.on||V3.build||V3.shop)return;{let rfh=false;try{rfh=typeof rfDbl==='function'&&rfDbl(e)}catch(err){console.error(err)}if(rfh)return}const v=v3target(mx(e),my(e));if(v)send('dblclick3d',v)});
 c.addEventListener('auxclick',e=>{if(e.button===1)e.preventDefault()});
 c.addEventListener('mousedown',e=>{if(e.button===1)e.preventDefault();v3menuClose();V3.drag={x:mx(e),y:my(e),b:e.button,moved:false,yaw:V3.yaw,pitch:V3.pitch,tcx:V3.tcx,tcy:V3.tcy,box:e.button===0&&!e.altKey&&!V3.build&&!V3.shop};if(V3.build&&e.button===0&&!e.altKey)V3.paint=v3pickTile(mx(e),my(e))});
 addEventListener('mousemove',e=>{V3.mouse={x:mx(e),y:my(e)};if(V3.on){V3.hoverTile=v3pickTile(mx(e),my(e));if(e.target===$('world3d'))v3hoverPart(mx(e),my(e));else if(V3.hoverPart&&$('menu3d').hidden)v3hoverPart(-1e4,-1e4);if(e.target===$('world3d')&&arr(model&&model.units).some(u=>u.selected)){clearTimeout(V3.hoverT);V3.hoverT=setTimeout(()=>{const v=V3.mouse&&v3target(V3.mouse.x,V3.mouse.y);if(v&&v!==V3.hoverSent){V3.hoverSent=v;send('hover3d',v)}},180)}}const d=V3.drag;if(!d)return;const dx=mx(e)-d.x,dy=my(e)-d.y;if((Math.abs(dx)+Math.abs(dy))*hudKC()>6)d.moved=true;   /* 6 screen pixels, whatever the HUD's zoom */if(d.box&&d.moved){const b=$('box3d');b.hidden=false;b.style.left=Math.min(d.x,mx(e))+'px';b.style.top=Math.min(d.y,my(e))+'px';b.style.width=Math.abs(dx)+'px';b.style.height=Math.abs(dy)+'px'}if(d.b===2&&d.moved)v3panDrag(d,dx,dy);if(d.b===1||(d.b===0&&e.altKey)){V3.yaw=d.yaw-dx*0.008;V3.pitch=Math.max(0.06,Math.min(1.52,d.pitch+dy*0.006));V3.userTurn=performance.now();if(V3.top&&Math.abs(dx)>8){V3.top=false;$('camTop').setAttribute('aria-pressed','false')}}});
 addEventListener('mouseup',e=>{const d=V3.drag;V3.drag=null;if(d&&d.b===2&&d.moved){v3panSend(true);return}
  if(model&&model.useon&&d&&!d.moved&&V3.on&&e.target===$('world3d')){if(d.b===2){send('useoncancel','');return}   // an item held (UseOn.dm)
   if(d.b===0){const t=v3pickThing(mx(e),my(e)),g=t&&arr(model.useon.targets).find(x=>x.id===(t.ref||t.id));if(g)send('useonat',g.id);else text($('notice'),'Click one of the ringed ones to use the '+model.useon.item+' on it, or right-click to let it go.');return}}if(model&&model.questPick&&d&&!d.moved&&V3.on&&e.target===$('world3d')){if(d.b===2){send('quest','pick|');return}if(d.b===0){const t=v3pickThing(mx(e),my(e)),tile=t?{x:t.x,y:t.y}:v3pickTile(mx(e),my(e));if(tile)send('quest','pick3d|'+tile.x+'|'+tile.y+'|'+(t?(t.ref||t.id||''):'')+'|0|'+(tile.up?'1':'0'));return}}   // picking a quest's target (QuestTargets.dm)
  if(V3.shop&&d&&d.b===0&&!d.moved&&V3.on){const t=v3pickTile(mx(e),my(e));if(t){send('placeworkshop',V3.shop.id+'|'+t.x+'|'+t.y);if(!V3.shop.multi)v3shopEnd()}return}if(V3.build&&V3.paint&&d&&d.b===0&&V3.on){const end=v3pickTile(mx(e),my(e))||V3.paint;send('paint3d',V3.paint.x+'|'+V3.paint.y+'|'+end.x+'|'+end.y);V3.paint=null;return}V3.paint=null;$('box3d').hidden=true;if(d&&d.box&&d.moved&&V3.on){const refs=v3boxRefs(d.x,d.y,mx(e),my(e));if(refs.length){try{if(typeof rfBoxFx==='function')rfBoxFx(refs,e.shiftKey)}catch(err){console.error(err)}send('boxrefs',refs.join(',')+'|'+(e.shiftKey?'1':'0'));return}{let rfh=false;try{rfh=typeof rfEmptyBox==='function'&&rfEmptyBox(e,d)}catch(err){console.error(err)}if(rfh)return}const a=v3pickTile(d.x,d.y),b=v3pickTile(mx(e),my(e));if(a&&b)send('box3d',a.x+'|'+a.y+'|'+b.x+'|'+b.y+'|'+(e.shiftKey?'1':'0'));return}if(d&&d.b===2&&!d.moved&&V3.on&&e.target===$('world3d')){if(V3.aim){send('specialcancel','');return}{let rfh=false;try{rfh=typeof rfRightClick==='function'&&rfRightClick(e)}catch(err){console.error(err)}if(rfh)return}v3menuOpen(mx(e),my(e));return}if(!d||d.moved||d.b!==0||!V3.on||e.target!==$('world3d'))return;const t=v3pickThing(mx(e),my(e));const tile=t?{x:t.x,y:t.y}:v3pickTile(mx(e),my(e));if(!tile)return;{let rfh=false;try{rfh=typeof rfClick==='function'&&rfClick(e,t,tile)}catch(err){console.error(err)}if(rfh)return}if(!t&&tile.roof&&arr(model&&model.units).some(u=>u.selected)&&!!(model&&model.gather)){send('mineroof',tile.x+'|'+tile.y+'|'+(e.shiftKey?'1':'0'));return}send('click3d',tile.x+'|'+tile.y+'|'+(t?(t.ref||t.id||''):'')+'|'+(e.shiftKey?'1':'0')+'|'+(tile.up?'1':'0'))});
 c.addEventListener('wheel',e=>{e.preventDefault();V3.dist=Math.max(6,Math.min(60,V3.dist*(1+Math.sign(e.deltaY)*0.1)));clearTimeout(V3.sizeT);V3.sizeT=setTimeout(v3sizeCheck,250)},{passive:false});
 /* Hidden Clans (Drive.dm): WASD walks your ninja the way the keys point on screen (the owner, 11-01: "change the movement
    based on the camera"): turned by the camera's facing as the arrows' pan is, snapped to the nearest of the 8 tile
    directions, a tile a step. It goes to the server only when it changes, again every 0.7 s while held (the server stops
    after 1.5 s without word), and as 0,0 when they are let go or the window loses focus. */
 const HCD={keys:new Set(),sent:'0,0',beat:0};
 function hcDriveVec(){let fx=0,fy=0;if(HCD.keys.has('w'))fy+=1;if(HCD.keys.has('s'))fy-=1;if(HCD.keys.has('d'))fx+=1;if(HCD.keys.has('a'))fx-=1;if(!fx&&!fy)return '0,0';
  const f=[-Math.sin(V3.yaw),Math.cos(V3.yaw)],r=[Math.cos(V3.yaw),Math.sin(V3.yaw)],wx=fx*r[0]+fy*f[0],wy=fx*r[1]+fy*f[1],o=Math.round(Math.atan2(wy,wx)/(Math.PI/4));
  const d=[[1,0],[1,1],[0,1],[-1,1],[-1,0],[-1,-1],[0,-1],[1,-1]][((o%8)+8)%8];return d[0]+','+d[1]}   /* the screen's way, to the nearest of 8 */
 function hcDriveSend(again){const v=hcDriveVec();if(v!==HCD.sent||again){HCD.sent=v;send('drive',v)}HCD.beat=performance.now()}
 setInterval(()=>{if(HCD.keys.size)hcDriveSend(performance.now()-HCD.beat>700)},120);
 addEventListener('blur',()=>{if(HCD.keys.size){HCD.keys.clear();hcDriveSend(true)}});
 addEventListener('keydown',e=>{if(V3.on&&e.ctrlKey&&!e.metaKey&&!e.altKey&&e.key.toLowerCase()==='a'&&!e.target.closest('input,select,textarea')){send('action','all');e.preventDefault();return}  // Ctrl+A selects every unit, not the page's text
  if(!V3.on||e.metaKey||e.ctrlKey||e.altKey||e.target.closest('input,select,textarea'))return;const k=e.key.toLowerCase();if(['q','e'].includes(k)){V3.keys.add(k);e.preventDefault();return}
  if(k==='n'){v3iso(false);V3.turnTo=null;V3.yaw=0;V3.pitch=0.9;toast('Camera faces north.');e.preventDefault();return}
  if(k==='g'&&!e.repeat){send('gather','');e.preventDefault();return}   // the Gather switch (Gather.dm)
  if(k==='escape'&&model&&model.useon){send('useoncancel','');e.preventDefault();return}   // let the held item go (UseOn.dm)
  if(k==='escape'&&V3.shop){v3shopEnd();e.preventDefault();return}
  if(k==='escape'&&V3.build){send('cancelmode','');e.preventDefault();return}
  if(k==='c'){const order=['stack','cut','flat'];V3.mode=order[(order.indexOf(V3.mode||'stack')+1)%3];send('stack3d',V3.mode==='flat'?'0':'1');toast({stack:'Diorama: the ground below is drawn as solid rock with its tunnels.',cut:'Cutaway: the near half is cut open so you can see into the layer below.',flat:'This layer only.'}[V3.mode]);e.preventDefault();return}
  if(k==='w'||k==='a'||k==='s'||k==='d'){if(!e.repeat){HCD.keys.add(k);hcDriveSend()}e.preventDefault();return}   /* WASD: your ninja (Hidden Clans; A was attack-move in Banners) */
  if(k==='r'){send('attackmode','');e.preventDefault();return}   /* R: attack-move (A in Banners) */
  if(k==='f'){send('specialaim','');e.preventDefault();return}
  if(k==='i'){if(!nearCardToggle())send('action','interact');e.preventDefault();return}   // I: the card for those beside the one selected (or the original Interact menu)
  if(k==='escape'&&V3.aim){send('specialcancel','');e.preventDefault();return}
  if(e.key===' '&&!e.shiftKey&&!e.metaKey&&!e.ctrlKey){send('pause','');e.preventDefault();return}
  if(e.key===' '&&e.shiftKey){send('action','clear');e.preventDefault();return}  // Shift+Space deselects, as on the map
  if(k==='x'){V3.xray=!V3.xray;send('xray3d',V3.xray?'1':'0');toast(V3.xray?'X-ray: showing the layer above as a ghost.':'X-ray off.');e.preventDefault();return}
  const mv={arrowup:[0,1],arrowdown:[0,-1],arrowleft:[-1,0],arrowright:[1,0]}[k];if(!mv)return;e.preventDefault();const now=performance.now();if(now-V3.lastPan<140)return;V3.lastPan=now;
  // move relative to the camera's facing
  const f=[-Math.sin(V3.yaw),Math.cos(V3.yaw)],r=[Math.cos(V3.yaw),Math.sin(V3.yaw)];const step=2;const dx=Math.round((mv[0]*r[0]+mv[1]*f[0])*step),dy=Math.round((mv[0]*r[1]+mv[1]*f[1])*step);V3.tcx+=dx;V3.tcy+=dy;V3.panAt=performance.now();send('camera',Math.round(V3.tcx)+','+Math.round(V3.tcy))});
 addEventListener('keyup',e=>{const k=e.key.toLowerCase();V3.keys.delete(k);if(HCD.keys.delete(k))hcDriveSend()})}
// Fast unit positions between full 3D updates: [key, x, y, dir].
// Q/E/N from the game's keyboard while in 3D (the game owns the keys after a click).
window.gather3d=function(v){if(!model)return;const on=String(v)==='1';model.gather=on;const gb=$('btnGather');if(gb){if(gb.getAttribute('aria-pressed')!==String(on)&&typeof V3!=='undefined')V3.hoverSent=null;gb.setAttribute('aria-pressed',String(on));const gw=gb.querySelector('span');if(gw)gw.textContent=on?'Gather on':'Gather off'}};   // the Gather switch at once (Gather.dm), so the cut and outlines follow G
window.nearKey=function(){if(!nearCardToggle())send('action','interact')};   // the I key (Abilities.dm RemasterInteractKey)
window.key3d=function(k){if(!V3.on)return;k=String(k);if(k==='n'){v3iso(false);V3.turnTo=null;V3.yaw=0;V3.pitch=Math.max(V3.pitch,0.9);toast('Camera faces north.');return}if(k==='q'||k==='e'){V3.turnTo=(V3.turnTo??V3.yaw)+(k==='q'?-0.5:0.5);V3.userTurn=performance.now()}};
// Things by ref (or id), made once a scene: a moves push finds its units without a pass over every unit.
function v3refIdx(){if(V3.refIdxOf!==V3.things){V3.refIdxOf=V3.things;const I=V3.refIdx=new Map();for(const t of V3.things){const k=t.ref||t.id,a=I.get(k);if(a)a.push(t);else I.set(k,[t])}}return V3.refIdx}
// The things of one sort (by fields the server sets), made once a scene, in the scene's order.
// A field of the page's own on a thing, left out of JSON (a thing stringified, as the object cache does, stays the server's).
function v3hid(t,k,v){Object.defineProperty(t,k,{value:v,writable:true,configurable:true,enumerable:false})}
function v3cat(name,pred){let C=V3.cats;if(!C||C.of!==V3.things)C=V3.cats={of:V3.things};return C[name]||(C[name]=V3.things.filter(pred))}
// The server's pace (server-pace; the owner, 10-29, watching a 1000 v 1000: "rubberbanding still happens", units stepping
// forward and back, snapping, surging and slowing): each move3D batch ends with ["@t", world.time, speed] (View3D.dm
// Remaster3DMovesPush). V3.rate is the game time that passed a real second at the chosen speed over the last 3 s: 1 when
// the server keeps up, ~0.55-0.8 in a 1000 v 1000 in the real app. The glide (023) walks each step in its length / V3.rate,
// so units walk steadily at the server's own pace instead of walking at full pace, standing, then hurrying to catch up.
function v3rateFrom(L){const T=L.length&&L[L.length-1];if(!Array.isArray(T)||T[0]!=='@t')return;const now=performance.now()/1000,st=T[1]/10/(T[2]||1),S=V3.rateS||(V3.rateS=[]);S.push([now,st]);while(S.length>2&&now-S[0][0]>3)S.shift();const a=S[0],dt=now-a[0];if(dt>=0.8)V3.rate=Math.max(0.25,Math.min(1.25,(st-a[1])/dt))}
// A scene's units where the moves have them (scene-moves; the owner, 10-29, watching a 1000 v 1000: "its rubbing banding bad
// now"): a 3D scene is put together over a few ticks (View3D.dm: entries kept, or built under a per-tick budget), so its
// units can be a tile behind the move batches sent since (move3D, every tick a unit moved). The page probe
// (reports/polish-night-1026/rubber-probe) counted 100-1,300 units in a 1000 v 1000 put back a tile by each scene and
// forward again by the next batch: the rubberbanding. A unit moved by a batch in the last 1.5 s keeps that batch's tile and
// facing when a scene comes; the rest take the scene's.
function v3keepMoves(m){const ML=V3.mvLast;if(!ML||!ML.size)return;const now=performance.now()/1000;for(const t of arr(m.things)){const k=t.ref||t.id;const r=k!=null&&ML.get(k);if(!r)continue;if(now-r[3]>1.5){ML.delete(k);continue}if(t.x!==r[0]||t.y!==r[1]){t.x=r[0];t.y=r[1];t.dir=r[2]}}if(now-(V3.mvPrune||0)>5){V3.mvPrune=now;for(const [k,r] of ML)if(now-r[3]>3)ML.delete(k)}}
// A move batch parsed once for move3D and the handlers wrapped round it (031's step lengths); packed ones ("~", View3D.dm Remaster3DMovesPush, u1-sends 10-30) unpacked as the scene's are, and a failure turns packing off.
function v3mvParse(raw){if(typeof raw!=='string')return JSON.parse(JSON.stringify(raw));if(raw===V3.mvRaw)return V3.mvL;let s=raw;if(s.charCodeAt(0)===126){try{s=window.rmHudUnpack(s)}catch(e){if(!V3.pkBad){V3.pkBad=1;setTimeout(()=>send('hudpack','0'),0)}throw e}}const L=JSON.parse(s);V3.mvRaw=raw;V3.mvL=L;return L}
// A scene's parts the server left out because they are what it sent last (View3D.dm Remaster3DSame, u1-sends 10-30): named in m.same, put back from the last scene's; a part neither sent nor named is none. Fog the page keeps by itself.
function v3same(m){const K=V3.keep3d||(V3.keep3d={});if(Array.isArray(m.same))for(const k of m.same)if(!(k in m))m[k]=K[k];for(const k of ['blueprints','plan','sites','pdoors'])K[k]=m[k]}
window.move3D=function(raw){try{const L=v3mvParse(raw);if(!Array.isArray(L))return;v3rateFrom(L);{const ML=V3.mvLast||(V3.mvLast=new Map()),ns=performance.now()/1000;for(const r of L)if(Array.isArray(r)&&r[0]!=='@t')ML.set(r[0],[r[1],r[2],r[3],ns])}const by=new Map(L.map(r=>[r[0],r])),I=v3refIdx(),D=V3.gDirty||(V3.gDirty=new Set());for(const [ref,r] of by)for(const t of I.get(ref)||[]){if(t.ly&&t.kind!=='mine')continue;t.x=r[1];t.y=r[2];t.dir=r[3];if(t.kind==='mine'&&r.length>5&&V3.z===1){if(r.length>6)t.feet=r[5]===3?r[6]:null;t.ly=r[5]===3?(t.fly&&V3.SKYH?Math.max(V3.SKYH,v3peakTop(t.x,t.y)):v3feetY(t.x,t.y,t.feet)||V3.STOREY+0.02):0}else if(t.kind==='mine'&&r.length>6&&V3.z===3&&r[5]===3){t.feet=r[6];t.ly=0;v3skyStand(t)}D.add(t)}   /* yours up on a mountain too, at their feet's height (its top, or a dug-out floor inside it); down off it, on the ground (Gather.dm) */}catch(e){console.error(e)}};
window.update3D=function(raw){try{if(typeof raw==='string'&&raw.charCodeAt(0)===126){/* packed like the HUD's sends (HudPack.dm, hudpack.js) */
  try{raw=window.rmHudUnpack(raw);V3.pkBad=0}catch(e){console.error(e);if(!V3.pkBad){V3.pkBad=1;setTimeout(()=>send('hudpack','0'),0);setTimeout(()=>send('3dfull',''),300)}return}}
 const m=typeof raw==='string'?JSON.parse(raw):raw;if(!V3.gl)return;if(!m.__up){v3same(m);v3unpack(m);m.__up=1;v3keepMoves(m)}if(typeof m.skyh==='number')V3.SKYH=m.skyh;if(v3levelHold(m))return;   /* a new level waits while its land is built (v3levelHold) */
 // the painted ground textures (View3D.dm Remaster3DSendTextures) reach the client just before the first 3D update:
 // asking for them earlier logged "Cache was ensured for a file that does not exist in cache"
 if(!V3.gtex){V3.gtex=v3repeatTex('r3t-ground-grass.png',1);V3.etex=v3repeatTex('r3t-ground-earth.png',2);V3.stex=v3repeatTex('r3t-ground-stone.png',3)}
 if(m.z!==V3.z){const SY={3:v3skyGap(),1:0,2:-5,4:-10};if(V3.z){V3.lift=(SY[m.z]??0)-(SY[V3.z]??0);V3.liftT=0;toast(v3layerNote(m))}V3.disp.clear();V3.z=m.z;V3.pendTerr=null;V3.lastLayers=null;V3.below=v3meshes(null,0,V3.below);if(V3.belowL)V3.belowL.G=null;V3.above=v3meshes(null,0,V3.above)}if(!V3.seen){V3.cx=m.cx;V3.cy=m.cy;V3.seen=true}if(!(V3.panAt&&performance.now()-V3.panAt<1000)&&!(model&&model.play&&model.play.lock)&&!(typeof m.jump==='number'&&m.jump<(V3.camSeq||0)&&performance.now()-(V3.panLast||0)<5000)&&(Math.abs(V3.tcx-m.cx)>0.5||Math.abs(V3.tcy-m.cy)>0.5)){V3.tcx=m.cx;V3.tcy=m.cy}   /* not the centre of a scene begun before our last camera send (for 5 s: a lost send or a reset count can't hold it off longer): built over ticks, it came after a jump (hud-craft, 10-25) */   /* a locked camera follows its unit itself (v3chase) */V3.night=!!m.night;V3.dayp=typeof m.dayp==='number'?m.dayp:null;V3.xray=!!m.xray;V3.magic=!!m.magic;if(!m.stack&&V3.mode!=='flat')V3.mode='flat';else if(m.stack&&V3.mode==='flat')V3.mode='stack';
 v3work(m);V3.yield=new Map(arr(m.yield).map(a=>[a[0]+','+a[1],a]));  /* wood and ore left, tending (Yield.dm) */
 if(m.far){V3.farData=m.far;if(!m.terrain)v3buildFar()}
 V3.farUnits=Array.isArray(m.farunits)?m.farunits:[];
 if('fog' in m)v3fogData(m.fog);   /* fog of war (Fog.dm): each tile never seen, explored or in sight */
 V3.planCells=arr(m.plan);   /* before the land: a wall still going up is told by it (021 v3shapes, construction-3d) */
 if(m.terrain){const sh=v3terrainShift(m);if(sh){if(sh==='warm')m.warmAt=V3.pendTerr&&V3.pendTerr.warmAt||performance.now();V3.pendTerr=m}else{V3.pendTerr=null;v3applyTerrain(m)}}   /* a newer land keeps the wait's start: never more than a quarter of a second */
 V3.blueprints=arr(m.blueprints);V3.planCells=arr(m.plan);V3.sites=arr(m.sites);V3.pdoors=arr(m.pdoors);const mb=m.build||null;const nb=mb&&mb.paint?mb:null;if(JSON.stringify(mb)!==JSON.stringify(V3.mode3)){V3.mode3=mb;V3.build=nb;const bb=$('build3d');if(nb){bb.hidden=false;text(bb,'Building: '+nb.label+' · click or drag on the ground to plan it · Esc to stop')}else if(mb){bb.hidden=false;text(bb,mb.label+': click where it goes · Shift+Space to stop')}else{if(!V3.shop)bb.hidden=true;V3.paint=null}}
 V3.hasSel=arr(m.things).some(t=>t.kind==='mine'&&t.selected);{const keep=new Set(arr(m.things).concat(arr(m.air).filter(t=>t.kind==='mine'&&t.ref),arr(m.ground).filter(t=>t.kind==='mine'&&t.ref)).map(t=>t.ref||t.id));   /* yours on the level above or below keep their figure: no ghost, no rebuild (Gather.dm) */for(const k of [...V3.disp.keys()])if(!keep.has(k)&&!k.startsWith('air')&&!k.startsWith('gnd')){v3ghost(V3.disp.get(k));V3.disp.delete(k)}}V3.things=arr(m.things).map(t=>(t.key=t.ref||t.id,v3skyStand(t),t)).concat(arr(m.air).map(t=>(t.key=(t.kind==='mine'&&t.ref?'':'air')+(t.ref||t.id),t.ly=t.fly&&V3.SKYH?Math.max(V3.SKYH,v3peakTop(t.x,t.y)):v3feetY(t.x,t.y,t.feet)||(V3.upperTiles&&V3.upperTiles.has(t.x+','+t.y)?V3.STOREY+0.02:3.2),t)),arr(m.ground).map(t=>(t.key=(t.kind==='mine'&&t.ref?'':'gnd')+(t.ref||t.id),t.ly=-v3skyGap(),t)));V3.gAll=1;if(window.g3rebind)g3rebind();if(typeof raw!=='string')V3.sceneGen=(V3.sceneGen||0)+1;   /* objects handed in (tests, the replay) may be the last scene's, changed in place: all checked again */v3ranks();v3roofsForDoors();if(m.terrain&&V3.on)bootCoverOff()}catch(e){console.error(e)}};
// The terrain as the server sent it, applied: the walk layer's sets, the line of sight, and the meshes.
// 3D sends only what changed (2026-10-24): the ground comes as 16x16 chunks (tc) the page keeps (dropped when the server
// says, tdrop), with each layer's window (tw: z, x0, y0, w, h) and the ground layer's sight (ts, "*" all in sight); the
// things as changes (td: c new or changed, d gone; to: the order; the whole list now and then). Each layer's window and
// the things list are put back here exactly as the server built them before (View3D.dm Remaster3DTerrain), so all the
// rest goes on as it did. A chunk that should be here and isn't asks for everything again (3dfull).
function v3unpack(m){const S=V3.pk||(V3.pk={chunks:new Map(),things:new Map(),order:[]});
 if(m.tdrop)for(const k of m.tdrop)S.chunks.delete(k);
 if(m.tc)for(const C of m.tc)S.chunks.set(C.z+'|'+Math.floor((C.x0-1)/16)+','+Math.floor((C.y0-1)/16),C);
 if(m.tw){let miss=false;for(const name in m.tw){const W=m.tw[name],T=v3assemble(S,W[0],W[1],W[2],W[3],W[4],name==='terrain'?m.ts:null);if(T.miss)miss=true;delete T.miss;m[name]=T}if(miss&&!V3.pkAsked){V3.pkAsked=1;send('3dfull','')}else if(!miss)V3.pkAsked=0}
 if(m.things){S.things=new Map();for(const t of m.things)S.things.set(t.ref||t.id,t);S.order=m.things.map(t=>t.ref||t.id)}
 else if(m.td){for(const t of m.td.c||[])S.things.set(t.ref||t.id,t);for(const k of m.td.d||[])S.things.delete(k);if(m.to)S.order=m.to;m.things=S.order.map(k=>S.things.get(k)).filter(Boolean)}}
// A layer's window from the chunks, as Remaster3DTerrain builds it: kinds numbered as they first appear, row by row.
function v3assemble(S,z,x0,y0,w,h,seen){const tiles=new Array(w*h),kinds=[],idx=new Map();let faces=null,miss=false;
 for(let j=0;j<h;j++){const y=y0+j,cy=Math.floor((y-1)/16);for(let i=0;i<w;i++){const x=x0+i,C=S.chunks.get(z+'|'+Math.floor((x-1)/16)+','+cy);
  if(!C||x<C.x0||y<C.y0||x>=C.x0+C.w||y>=C.y0+C.h){tiles[j*w+i]=0;miss=true;continue}const li=(y-C.y0)*C.w+(x-C.x0),c=C.tiles[li];let n=0;   /* a chunk's part under the window */
  if(c){const K=C.kinds[c-1];n=idx.get(K.k);if(!n){const k=Object.assign({},K);delete k.k;kinds.push(k);n=kinds.length;idx.set(K.k,n)}}tiles[j*w+i]=n;
  const f=C.face?C.face[li]:'0';if(f!=='0'){if(!faces)faces=new Array(w*h).fill('0');faces[j*w+i]=f}}}
 const T={x0,y0,w,h,z,tiles,kinds};if(faces)T.face=faces.join('');if(seen!=null)T.seen=seen==='*'?'1'.repeat(w*h):seen;if(miss)T.miss=true;return T}
// The walk layer's sets from the layer above (V3.upperTiles, V3.walkTiles, V3.walkFace, V3.walkKnown), as v3applyTerrain
// sets them; a new level's chunks are built with them before it is put in (v3levelWarm).
// Mountain heights, plan B (planning/MOUNTAIN_HEIGHTS.md; world-look 2026-10-25): the Sky level is what is at the sky
// height or above (the scene's "skyh", RM_SKY_H: 10 blocks); ordinary mountains stay under it. The gap between the
// surface and the Sky view's plane is that height (a storey before it was sent).
function v3skyGap(){return V3.SKYH||V3.STOREY}
// Where a layer-3 tile stands, for a layer drawn at yo: a tall peak ("peak", or a floor, with "blocks") at its column's height,
// anything else (upper storeys, wall walks, stairs) a storey over the surface; in the Sky view (yo 0) less the sky height.
function v3skyY(T,K,yo){if(T.z!==3||!V3.SKYH)return yo;const h=K&&(K.kind==='peak'||K.kind==='floor')&&K.blocks?K.blocks:V3.STOREY;return yo===0?h-V3.SKYH:yo===V3.STOREY?h:yo}
// In the Sky view, a unit of layer 3 over open sky (up on an ordinary mountain, whose peak is open sky to the view)
// stands at its feet less the sky height, on its mountain in the surface below; flyers keep their own height.
function v3skyStand(t){if(V3.z===3&&V3.SKYH&&t.feet!=null&&!t.fly&&t.feet<V3.SKYH&&!v3kindAt(t.x,t.y))t.ly=t.feet-V3.SKYH}
function v3walkSets(U){const up=new Set(),walk=new Set(),face=new Map(),known=!!(U&&Array.isArray(U.tiles));
 if(known)for(let j=0;j<U.h;j++)for(let i=0;i<U.w;i++){const c=U.tiles[j*U.w+i];const k=c?U.kinds[c-1]:null;if(k&&['bfloor','built','stairsdown','floor','walk'].includes(k.kind))up.add((U.x0+i)+','+(U.y0+j));if(k&&k.kind==='walk'){walk.add((U.x0+i)+','+(U.y0+j));const f=typeof U.face==='string'?parseInt(U.face[j*U.w+i],32)||0:0;if(f)face.set((U.x0+i)+','+(U.y0+j),f)}}
 return {up,walk,face,known}}
// A new level's land built before anything of it is put in (world-look 2026-10-25; the user: "going from caves sky to
// surface causes some lag spikes": building all of it in the update that changed the level was one frame of 66-91 ms).
// The update that changes the level, and any after it, wait in order (V3.lvHold) while its chunks, the ground's and its
// layers', are built 4 ms a frame (v3levelWarm); then they go in as they came (v3levelGo), its units with their ground.
// At most 0.7 s (8 ms a frame), by a timer too should frames stop; another level meanwhile lets what waits go in first. V3.lvOff=1: off.
function v3levelHold(m){if(m.__held||V3.lvGo)return false;const H=V3.lvHold;
 if(H){if(m.z!==H.z){v3levelGo();return v3levelHold(m)}m.__held=1;H.q.push(m);return true}
 if(V3.lvOff||!V3.z||m.z===V3.z||!m.terrain||!Array.isArray(m.terrain.tiles)||!Array.isArray(m.terrain.kinds)||!V3.models)return false;
 m.__held=1;const at=performance.now();V3.lvHold={z:m.z,m,q:[m],at,G:{}};setTimeout(()=>{if(V3.lvHold&&V3.lvHold.at===at)v3levelGo()},720);return true}
function v3levelWarm(ms){const H=V3.lvHold;if(!H)return;const t0=performance.now(),m=H.m,T=m.terrain,WS=H.ws||(H.ws=v3walkSets(m.upper||null));
 const keep=[V3.upperTiles,V3.walkTiles,V3.walkFace,V3.walkKnown];V3.upperTiles=WS.up;V3.walkTiles=WS.walk;V3.walkFace=WS.face;V3.walkKnown=WS.known;let done=false;
 try{const left=()=>Math.max(1,ms-(performance.now()-t0));done=v3layerWarm(T,0,ms,H.G,T.z+'|'+(WS.known?1:0))&&(T.z!==1||v3layerWarm(m.upper||null,V3.STOREY,left(),V3.upperL||(V3.upperL={})))&&(T.z!==3||v3layerWarm(m.below||null,-v3skyGap(),left(),V3.belowL||(V3.belowL={})))}
 finally{[V3.upperTiles,V3.walkTiles,V3.walkFace,V3.walkKnown]=keep}
 H.frames=(H.frames||0)+1;if(done||performance.now()-H.at>700)v3levelGo()}
function v3levelGo(){const H=V3.lvHold;if(!H)return;V3.lvHold=null;if(H.G.C){V3.tchunks=H.G.C;V3.tchunksZ=H.G.zk;V3.tchunkLive=null;V3.tchunkWarmed=1}
 V3.lvGo=true;try{for(const m of H.q)window.update3D(m)}finally{V3.lvGo=false}V3.lvLast={ms:Math.round(performance.now()-H.at),n:H.q.length,frames:H.frames||0}}
function v3applyTerrain(m){v3terrainFx(V3.terrain,m.terrain);V3.terrain=m.terrain;const U=m.upper;{const WS=v3walkSets(U);V3.upperTiles=WS.up;V3.walkTiles=WS.walk;V3.walkFace=WS.face;V3.walkKnown=WS.known}
  V3.seen=typeof m.terrain.seen==='string'?{x0:m.terrain.x0,y0:m.terrain.y0,w:m.terrain.w,h:m.terrain.h,s:m.terrain.seen}:null;
  // The server resends the terrain every few ticks even when nothing in it changed; rebuilding every mesh then cost
  // 10-30 ms (a stutter every few seconds), so the meshes are only rebuilt when what they are built from changed.
  const tkey=JSON.stringify([m.terrain,U||null,m.below||null,m.above||null,m.z,!!V3.models,V3.workVer||0,(V3.things||[]).filter(t=>t.rune&&t.rune.id==='portcullis').map(t=>t.x+','+t.y)]);
  if(tkey!==V3.terrKey){V3.terrKey=tkey;V3.terrGen=(V3.terrGen||0)+1;V3.upper=v3layerChunked(U||null,V3.STOREY,V3.upper,V3.upperL||(V3.upperL={}));v3buildTerrain(m.terrain);V3.below=m.z===3?v3layerChunked(m.below||null,-v3skyGap(),V3.below,V3.belowL||(V3.belowL={}),true):v3meshes(m.below||null,-5,V3.below,true);if(m.z!==3&&V3.belowL)V3.belowL.G=null;V3.above=v3meshes(m.above||null,2.4,V3.above)}
 V3.lastLayers={upper:m.upper||null,below:m.below||null,above:m.above||null}}
// While the camera pans, every step moves the server's window and resends the land (a full rebuild, 10-30 ms, so
// panning juddered). When the new window is only the same land shifted (every tile both share is unchanged) and the
// view is still well inside what is already built, it waits (V3.pendTerr) until the camera settles or nears the edge.
function v3overlapSame(A,B){if(!A||!B)return !A&&!B;if(!Array.isArray(A.tiles)||!Array.isArray(B.tiles)||!Array.isArray(A.kinds)||!Array.isArray(B.kinds))return false;const ka=A.kinds.map(k=>JSON.stringify(k)),kb=B.kinds.map(k=>JSON.stringify(k));
 const x0=Math.max(A.x0,B.x0),x1=Math.min(A.x0+A.w,B.x0+B.w),y0=Math.max(A.y0,B.y0),y1=Math.min(A.y0+A.h,B.y0+B.h),sa=typeof A.seen==='string'?A.seen:null,sb=typeof B.seen==='string'?B.seen:null,fa=typeof A.face==='string'?A.face:null,fb=typeof B.face==='string'?B.face:null;if(!!sa!==!!sb||!!fa!==!!fb)return false;
 for(let y=y0;y<y1;y++)for(let x=x0;x<x1;x++){const ia=(y-A.y0)*A.w+(x-A.x0),ib=(y-B.y0)*B.w+(x-B.x0),ca=A.tiles[ia],cb=B.tiles[ib];if((ca?ka[ca-1]:'')!==(cb?kb[cb-1]:''))return false;if(sa&&sa[ia]!==sb[ib])return false;if(fa&&fa[ia]!==fb[ib])return false}return true}
function v3inMargin(T){if(!T)return false;const mx=Math.min(T.w/2-1,V3.dist*0.85+3),my=Math.min(T.h/2-1,V3.dist*0.65+3),cx=V3.tcx,cy=V3.tcy;return cx-T.x0>=mx&&T.x0+T.w-1-cx>=mx&&cy-T.y0>=my&&T.y0+T.h-1-cy>=my}
function v3terrainShift(m){const A=V3.terrain,B=m.terrain,P=V3.lastLayers;if(!A||!B||!P||!V3.on||(A.x0===B.x0&&A.y0===B.y0&&A.w===B.w&&A.h===B.h))return false;
 // Zoomed right out the view is never well inside the window: a big window's land ('warm') waits only while its new
 // chunks are built a few ms a frame, a quarter of a second at most (world-look 2026-10-25: a pan step in one frame).
 const inside=v3inMargin(A);if(!inside&&!(A.w*A.h>=6000&&V3.models))return false;
 return v3overlapSame(A,B)&&v3overlapSame(P.upper,m.upper||null)&&v3overlapSame(P.below,m.below||null)&&v3overlapSame(P.above,m.above||null)?(inside||'warm'):false}
// The layer-change note; going down onto solid rock says why it's all rock (a new player saw a blank plain and no hint).
function v3layerNote(m){const base=({1:'Surface',2:'Down into the caves',3:'Up into the sky',4:'Down into the depths'})[m.z]||'Layer '+m.z,T=m.terrain;
 if((m.z!==2&&m.z!==4)||!T||!Array.isArray(T.tiles)||!Array.isArray(T.kinds))return base;let n=0,rock=0;
 for(let y=m.cy-4;y<=m.cy+4;y++)for(let x=m.cx-4;x<=m.cx+4;x++){const i=x-T.x0,j=y-T.y0;if(i<0||j<0||i>=T.w||j>=T.h)continue;const c=T.tiles[j*T.w+i],K=c?T.kinds[c-1]:null;n++;if(K&&(K.kind==='wall'||K.kind==='block'))rock++}
 return n&&rock===n?base+' · all rock here: dig stairs down to open the '+(m.z===4?'depths':'caves'):base}
// The loading cover: from the page's first moment until the first 3D frame with the land in it is drawn, so the
// native 2D map underneath is never seen while the game loads; a safety timeout lifts it anyway.
function bootCoverOff(){const c=$('bootcover');if(!c||c.classList.contains('off'))return;requestAnimationFrame(()=>requestAnimationFrame(()=>{c.classList.add('off');setTimeout(()=>c.remove(),900)}))}
setTimeout(bootCoverOff,30000);
function v3set(on){if(on&&!v3init())return false;if(!on){if(V3.shop)v3shopEnd();V3.paint=null;V3.drag=null;V3.keys.clear()}V3.on=on;document.body.classList.toggle('v3d',on);$('tag3d').hidden=true;queueRegions();return true}
addEventListener('blur',()=>V3.keys.clear());
function v3toggle(on){if(on&&!v3set(true))return;if(!on)v3set(false);V3.pending={on,at:performance.now()};send('view3d',on?'1':'0')}
$('btn3d').addEventListener('click',()=>v3toggle(!V3.on));

// --- Quests (Quests.dm; planning/QUEST_MAKER_PLAN_2026-10-31.md section 15, the owner's "Yes, all eight", 10-31) ------
// The Quests page (Taken, Ours and the post form), the card (a board's notices, or one notice with the box the game
// writes: goal, reward, who, time) and the tracker on the left. Every button is one send: data-do="quest".
let questView='taken',questKey='',questFormKey='',questCardKey='',questTrackKey='';
const questDraft={kind:'bring',item:'',need:'10',keep:'0',each:'3',quality:'',coins:'10',who:'anyone',rank:'1',days:'3',title:'',text:'',goods:new Set(),race:'',hunt:'5',exact:'exact',radius:'2',place:'',row:'',fortGoal:'chest',lethal:'1',captives:'0',fee:'0',after1:'',cond1:'done',after2:'',cond2:'done',afterMode:'all',gives:'',secret:'0'};
{const st=document.createElement('style');st.textContent=
 '#questcard{position:fixed;left:50%;top:46%;transform:translate(-50%,-50%);z-index:14;width:470px;max-width:calc(var(--sw,100vw) - 24px);max-height:calc(var(--sh,100vh)*.78);display:flex;flex-direction:column;padding:8px 10px 10px;background:linear-gradient(#2a241a,#18140e);border:1px solid #b08a3e;border-radius:4px;box-shadow:0 10px 30px rgba(0,0,0,.65);color:#efe3c2}#questcard[hidden]{display:none}'+
 '#questcard .qc-head{display:flex;gap:9px;align-items:flex-start;padding:2px 0 7px;border-bottom:1px solid rgba(176,138,62,.4)}#questcard .qc-t{flex:1;min-width:0}#questcard .qc-t b{display:block;font:17px HudText,Georgia,serif;letter-spacing:.03em;color:#f2d27a}#questcard .qc-t small{display:block;font-size:11px;color:#c9bd9e}'+
 '#questcard .qc-x{flex:none;min-height:24px!important;width:28px;padding:0!important}#questcard .qc-body{flex:0 1 auto;overflow-y:auto;padding:7px 1px 0}'+
 '#questcard .qc-says{position:relative;margin:0 0 16px;padding:7px 9px;background:#0f0d0a;border:1px solid #5d4a2a;font:italic 13px/1.45 HudText,Georgia,serif;color:#efe6cc}#questcard .qc-says i{position:absolute;left:8px;top:-8px;padding:0 5px;font:normal 10px HudText,Georgia,serif;color:#9e978a;background:#1d1a14}'+
 '#questcard .qc-list button{display:flex;width:100%;align-items:center;gap:8px;margin:0 0 3px;min-height:30px;text-align:left}#questcard .qc-list small{margin-left:auto;padding-left:8px;font-size:11px;color:#c9bd9e;white-space:nowrap;min-width:0;max-width:52%;overflow:hidden;text-overflow:ellipsis}'+
 '.qm{flex:none;display:inline-block;width:14px;font:bold 15px HudText,Georgia,serif;font-style:normal;text-align:center;color:#ffd75e}'+
 '#questcard .qc-game{position:relative;margin:4px 0 0;padding:9px 10px 7px;border:1px solid #b08a3e;background:rgba(0,0,0,.28)}#questcard .qc-game>i{position:absolute;right:8px;top:-8px;padding:0 6px;font:normal 10px HudText,Georgia,serif;letter-spacing:.04em;color:#cea654;background:#1d1a14}'+
 '#questcard .qc-game h4{margin:0 0 5px;font:15px HudText,Georgia,serif;color:#f1e7c8}#questcard dl{display:grid;grid-template-columns:92px minmax(0,1fr);gap:3px 10px;margin:0;font-size:12px}#questcard dt{color:#b9b2a2}#questcard dd{margin:0;color:#ebe3cf}'+
 '#questcard .qc-note{margin:7px 0 0;font-size:11.5px;color:#d9cdb0}#questcard .qc-note.no{color:#e7a48f}#questcard .qc-foot{display:flex;flex-wrap:wrap;gap:6px;margin-top:9px;padding-top:8px;border-top:1px solid rgba(176,138,62,.3)}#questcard .qc-foot .grow{flex:1}'+
 '#questcard .qc-journal{margin:8px 0 0;padding:0 0 0 16px;font-size:11px;color:#c9bd9e}'+
 '#questcard .qc-list .qdg{margin-left:auto;padding:0 5px;border:1px solid;border-radius:3px;font-size:10.5px;line-height:15px}#questcard .qc-list .qdg+small{margin-left:6px}.qdg-easy{color:#9fd08a;border-color:#5f8a4f}.qdg-even{color:#e8cf7a;border-color:#8a7a3c}.qdg-hard{color:#f0a868;border-color:#8a5a2f}.qdg-deadly{color:#f08a7a;border-color:#8a3a2f}#page-quests .qstand{margin:9px 0 0;padding:4px 0 0;border-top:1px solid rgba(176,138,62,.25)}#page-quests .qstand summary{cursor:pointer;font-size:12px;color:#d9cdb0}'+
 '#questcard .qk-head{align-items:center}#questcard .qk-face{flex:none;width:52px;height:52px;image-rendering:pixelated;border:1px solid #5d4a2a;background:#0f0d0a}#questcard .qk-head .qc-t small{display:block}#questcard .qk-name{text-transform:uppercase;letter-spacing:.09em}#questcard .qk-ask{display:flex;flex-wrap:wrap;gap:4px;margin-top:8px}#questcard .qk-ask[hidden]{display:none}'+
 '#heroframe .qk-tab label{display:block;margin:5px 0 2px;font-size:11px;color:#c9bd9e}#heroframe .qk-tab :is(input:not([type=checkbox]),select,textarea){box-sizing:border-box;width:100%;padding:3px 5px;font:12px HudText,Georgia,serif}#heroframe .qk-tab ::placeholder{color:#8f846c;font-style:italic}#heroframe .qk-offers label{display:flex;gap:6px;align-items:center;margin:2px 0;color:#ebe3cf;font-size:12px}#heroframe .qk-topic{display:grid;gap:2px;margin:0 0 4px}#heroframe .qk-acts{display:flex;flex-wrap:wrap;gap:4px;margin-top:6px}#heroframe .qk-tab .hfh span{margin-left:4px;font-size:10px;letter-spacing:0;text-transform:none;color:#9e978a}'+
 '#heroframe.keeper .hftabs button{grid-column:span 3}#heroframe:not(.keeper) .hftabs [data-hftab=keeper]{display:none}#heroframe[data-tab=keeper] [data-pane]:not([data-pane=keeper]){display:none!important}'+
 '#questtrack{position:fixed;left:6px;top:250px;z-index:3;width:214px;padding:5px 9px 6px;background:rgba(14,12,9,.84);border:1px solid rgba(176,138,62,.5);box-shadow:0 4px 14px rgba(0,0,0,.45);color:#efe3c2}#questtrack[hidden]{display:none}'+
 '#questtrack>span{display:block;font-size:9.5px;letter-spacing:.18em;text-transform:uppercase;color:#b08a3e}#questtrack button{display:block;width:100%;margin:4px 0 0;padding:0!important;min-height:0!important;text-align:left;background:none!important;border:0!important;border-image:none!important;box-shadow:none!important;color:inherit}'+
 '#questtrack b{display:block;font:13px HudText,Georgia,serif;color:#f1e7c8}#questtrack small{display:block;padding-left:9px;font-size:11.5px;line-height:1.35;color:#d6cfbd}#questtrack button:hover b{color:#ffe7a3}'+
 '#page-quests .qrow{padding:7px 0;border-bottom:1px solid rgba(176,138,62,.25)}#page-quests .qrow>b{display:block;font:14px HudText,Georgia,serif}#page-quests .qrow>small{display:block;font-size:11.5px;color:#c9bd9e}#page-quests .qrow .acts{display:flex;flex-wrap:wrap;gap:5px;margin-top:5px}'+
 '#page-quests .qform label{display:block;margin:7px 0 2px;font-size:11.5px;color:#b9b2a2}#page-quests .qform :is(input:not([type=checkbox]),select,textarea){box-sizing:border-box;width:100%;padding:4px 6px;background:#0f0d0a;border:1px solid #5d4a2a;color:#efe6cc;font:13px HudText,Georgia,serif}'+
 '#page-quests .qform .two{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:0 8px}#page-quests .qform .goods label{display:flex;gap:6px;align-items:center;margin:2px 0;color:#ebe3cf;font-size:12px}#page-quests .qform .goods input{width:auto}#page-quests .qform .acts{display:flex;gap:6px;margin-top:10px}'+
 '#food3d span.qmark{color:#ffd75e;font-weight:600}'+
 '#qpins3d{position:fixed;inset:0;pointer-events:none;z-index:0}#qpins3d span{position:absolute;left:0;top:0;padding:1px 8px 2px;border-radius:8px;background:rgba(30,22,12,.8);border:1px solid rgba(255,215,94,.5);color:#ffd75e;font:600 11px/15px HudText,Georgia,serif;white-space:nowrap;text-align:center;text-shadow:0 0 2px #000}'+
 '#qpins3d span.read{color:#efe3c2;border-color:rgba(239,227,194,.35)}#qpins3d span small{display:block;font-weight:400;font-size:10px;line-height:13px;color:#e6dcc4}#qpins3d span[hidden]{display:none}body:not(.v3d) #qpins3d,body.overlay.cine #qpins3d{display:none}'+
 '#page-quests .qform [data-qpick][aria-pressed=true]{color:#ffd75e}#page-quests .qpicked{color:#f2d27a}'+
 '#page-quests .qchain{margin:9px 0 0;padding:4px 0 0;border-top:1px solid rgba(176,138,62,.25)}#page-quests .qchain summary{cursor:pointer;font-size:12px;color:#d9cdb0}#page-quests .qchain label input[type=checkbox]{width:auto;margin-right:5px}'+
 'body.overlay[data-mat] #questcard .qc-t b{color:var(--macc)}body.overlay[data-mat] #questcard .qc-game{border-color:var(--macc)}body.overlay[data-mat] #questcard .qc-game>i,body.overlay[data-mat] #questcard .qc-says i{background:var(--mpane);color:var(--macc)}body.overlay[data-mat] #questtrack>span{color:color-mix(in srgb,var(--macc) 72%,transparent)}';
 document.head.append(st)}
function questMark(m){return '<i class="qm">'+(m==='!'?'!':m==='?'?'?':m==='...'?'…':'')+'</i>'}
// A keeper's talk (QuestKeepers.dm): who they are, what they say to you, their quests (a click: that quest's own card,
// with Back to them) and Ask about; a stall keeper's wares instead of quests. Their words are their maker's; the quest
// cards are always the game's.
// Q8 (QuestAdaptive.dm): the going rate on the post form (a hint only), a standing notice's fields, Ours' list of them.
function questRateText(P,item){const n=String(item||'').trim().toLowerCase();if(!n)return '';const k=arr(P.kinds).find(x=>String(x[1]).toLowerCase()===n);if(!k)return '';const r=(P.rates||{})[k[0]];
 return r?'Sold lately at market stalls: about '+r[0]+' coins each ('+r[1]+' sale'+(r[1]===1?'':'s')+'). A hint only: you set the reward.':'No sales of it at market stalls lately.'}
function questStandHtml(){return '<details class="qstand"'+(+questDraft.keep>0?' open':'')+'><summary>Keep it stocked: it goes up again whenever your stores run low</summary>'
 +'<div class="two"><div><label>Keep at least (0: just once)</label><input data-q="keep" type="number" min="0" max="200" value="'+esc(questDraft.keep)+'"></div><div><label>Pay each (coins)</label><input data-q="each" type="number" min="1" max="1000" value="'+esc(questDraft.each)+'"></div></div>'
 +'<p class="hint">With a number, it goes up by itself for what your stores lack (counted in your stores on this board’s level) and comes down once they are full again, while nobody has taken it. Its coins are taken as each notice goes up; How many, the coins and goods below are not used.</p></details>'}
function questStandingRows(D){const S=arr(D.standing);if(!S.length)return '';return '<p class="hint">Standing notices: they go up by themselves.</p>'+S.map(s=>'<div class="qrow"><b>'+esc('Keep '+s.keep+' '+s.itemName)+'</b><small>'+esc(s.have+' in your stores · '+s.each+' coins each · '+(s.note||''))+'</small><div class="acts">'+(s.quest?'<button data-do="quest" data-value="'+esc('open|'+s.quest)+'">Open</button>':'')+'<button data-do="quest" data-value="'+esc('standingstop|'+s.id)+'" title="Stop\nNo more notices go up for it. One up now stays until it ends or you take it down.">Stop</button></div></div>').join('')}
let questKeeperC=null;
function questKeeperHtml(C,btn){questKeeperC=C;const R=arr(C.rows),T=arr(C.topics),M=C.market,stall=C.job==='stall';
 let h='<div class="qc-head qk-head">'+(C.portrait?'<img class="qk-face" src="'+esc(C.portrait)+'" alt="">':'')+'<div class="qc-t"><b class="qk-name">'+esc(C.name)+'</b><small>'+esc((stall?'Stall keeper':'Quest giver')+' of House '+(C.house||'')+(stall?' · at their market stall':' · by their notice board'))+'</small><small>'+esc('A '+C.race+', Attack '+(C.attack||0)+'. A keeper: one of their own people.')+'</small></div>'+btn('close','×','Close','qc-x')+'</div><div class="qc-body">'
  +'<div class="qc-says" data-qk-says>“'+esc(C.line||'')+'”<i>'+(C.own?'their words, as others see them':'their words')+'</i></div>';
 if(!stall)h+='<div class="qc-list">'+(R.length?R.map(q=>'<button data-do="quest" data-value="'+esc('keeperq|'+q.id)+'">'+questMark(q.mark||(q.mine==='taken'?'...':''))+esc(q.title)+'<small>'+esc(q.tag||'')+'</small></button>').join(''):'<p class="hint">No quests from them for you right now.</p>')+'</div>';
 else if(M&&arr(M.wares).length)h+='<div class="qc-list">'+arr(M.wares).map(w=>'<button data-do="market" data-value="'+esc(C.uref+'|buy|'+w.ref)+'"'+(M.coins<w.price?' disabled title="Not enough coins"':'')+'>'+esc(w.name)+'<small>'+w.price+' coins</small></button>').join('')+'</div><p class="qc-note">'+esc('Your treasury: '+M.coins+' coins.')+'</p>';
 else h+='<p class="qc-note">'+esc(M?'Nothing for sale right now.':'Bring one of your people beside '+C.name+' to see what they sell.')+'</p>';
 if(T.length)h+='<div class="qk-ask" hidden>'+T.map((t,i)=>'<button type="button" data-qk-topic="'+i+'">'+esc(t[0])+'</button>').join('')+'</div>';
 if(!stall&&!C.unit&&!C.own)h+='<p class="qc-note">'+esc('Bring one of your people beside '+C.name+' to take or hand in their quests.')+'</p>';
 return h+'</div><div class="qc-foot">'+(T.length?'<button type="button" data-qk-ask>Ask about…</button>':'')+(C.own?'':'<button data-qrep="'+esc('unit|'+C.ref)+'" title="Report this keeper\nRude words: the admins look at it.">Report</button>')+'<span class="grow"></span>'+btn('close','Goodbye')+'</div>'}
document.addEventListener('click',e=>{const a=e.target.closest('#questcard [data-qk-ask]');if(a){const k=$('questcard').querySelector('.qk-ask');if(k)k.hidden=!k.hidden;return}
 const b=e.target.closest('#questcard [data-qk-topic]');if(!b||!questKeeperC)return;const t=arr(questKeeperC.topics)[+b.dataset.qkTopic],s=$('questcard').querySelector('[data-qk-says]');if(t&&s)s.innerHTML='“'+esc(t[1])+'”<i>'+esc(t[0])+'</i>'});
// The board or market box's "make a keeper" (a single own unit by its own board or stall).
function keeperMakeBtn(u,job){const M=u.keeperMake,stall=job==='stall';return '<button data-do="quest" data-value="'+esc('keepermake|'+u.ref+'|'+job)+'"'+(M.left>0?'':' disabled')+' title="'+esc((stall?'Make them your stall keeper':'Make them your quest giver')+'\n'+(stall?'They mind this stall and sell what they carry, in your own words.':'They stand by this board; other realms talk to them to take your quests.')+' A realm has at most '+M.max+' keepers ('+Math.max(0,M.left)+' left).')+'">'+(stall?'Make stall keeper':'Make quest giver')+'</button>'}
// A keeper's own tab on its unit card: job and where they stand, the quests they offer, their words (empty: their race's
// own, shown faded), up to 3 Ask about topics; Preview (their talk as others see it), Use default words, Save.
function keeperPaneHtml(u){const K=u.keeper,W=arr(K.words),D=arr(K.defaults),T=arr(K.topics),names=['Greeting','While you work','Thanks','Turn away'];
 const at=j=>arr(j==='stall'?K.stalls:K.boards).map(p=>'<option value="'+esc(p[0])+'"'+(p[0]===K.at?' selected':'')+'>'+esc(p[1])+'</option>').join('');
 let h='<div class="qk-tab" data-unit="'+esc(u.ref)+'"><div class="hfh">Keeper <span>'+K.count+' of '+K.max+' in your realm</span></div>'
  +'<label>Job</label><select data-k="job"><option value="quest"'+(K.job==='quest'?' selected':'')+'>Quest giver</option><option value="stall"'+(K.job==='stall'?' selected':'')+'>Stall keeper</option><option value="none">None: no keeper</option></select>'
  +'<label>Stands at</label><select data-k="at">'+at(K.job)+'</select>';
 if(K.job==='quest')h+='<label>Offers</label><div class="qk-offers">'+(arr(K.offers).length?arr(K.offers).map(o=>'<label><input type="checkbox" data-k="offer" value="'+esc(o[0])+'"'+(o[2]?' checked':'')+'>'+esc(o[1])+'</label>').join(''):'<p class="hint">No notices on that board yet: post one and they offer it.</p>')+'</div>';
 h+='<div class="hfh">Their words <span>empty: a '+esc(K.race)+'’s own, shown faded</span></div>'
  +names.map((n,i)=>'<label>'+n+'</label><input data-k="w'+i+'" maxlength="'+K.lines+'" placeholder="'+esc(D[i]||'')+'" value="'+esc(W[i]||'')+'">').join('')
  +'<label>Ask about (up to '+K.topicMax+')</label>'+Array.from({length:K.topicMax},(_,i)=>{const t=arr(T[i]);return '<div class="qk-topic"><input data-k="q'+i+'" maxlength="'+K.ask+'" placeholder="A question" value="'+esc(t[0]||'')+'"><textarea data-k="a'+i+'" rows="2" maxlength="'+K.answer+'" placeholder="Their answer">'+esc(t[1]||'')+'</textarea></div>'}).join('')
  +'<p class="hint">Fill-ins: {taker} {left} {reward} {house}. Words are filtered like chat and can be reported. Goals, rewards, rules and danger are always written by the game.</p>'
  +'<div class="qk-acts"><button type="button" data-qk="preview" title="Preview\nTheir talk, as other realms see it.">Preview</button><button type="button" data-qk="defaults" title="Use default words\nEmpties every line: they say a '+esc(K.race)+'’s own words. Save to keep it.">Use default words</button><button type="button" data-qk="save">Save</button></div></div>';
 return h}
document.addEventListener('change',e=>{const s=e.target.closest('#heroframe .qk-tab [data-k=job]');if(!s)return;const f=s.closest('.qk-tab'),a=f.querySelector('[data-k=at]'),K=heroPanes.u&&heroPanes.u.keeper;if(!a||!K||s.value==='none')return;
 a.innerHTML=arr(s.value==='stall'?K.stalls:K.boards).map(p=>'<option value="'+esc(p[0])+'">'+esc(p[1])+'</option>').join('')});
document.addEventListener('click',e=>{const b=e.target.closest('#heroframe [data-qk]');if(!b)return;const f=b.closest('.qk-tab');if(!f)return;const ref=f.dataset.unit,a=b.dataset.qk;
 if(a==='preview'){send('quest','keeperpreview|'+ref);return}
 if(a==='defaults'){f.querySelectorAll('[data-k^=w]').forEach(i=>i.value='');return}
 const v=k=>{const x=f.querySelector('[data-k='+k+']');return x?x.value:''},O=[...f.querySelectorAll('[data-k=offer]')],on=O.filter(o=>o.checked).map(o=>o.value);
 send('quest','keepersave|'+ref+'|'+JSON.stringify({job:v('job'),at:v('at'),all:on.length===O.length?1:0,offers:on,words:[0,1,2,3].map(i=>v('w'+i)),topics:[0,1,2].map(i=>[v('q'+i),v('a'+i)]).filter(t=>t[0]&&t[1])}))});
function questStateText(q){return q.state==='closing'?'Taken down: those who took it have until it ends':q.state==='done'?'Done':q.state==='ended'?'Ended':q.state==='gone'?'Gone':''}
function questGo(q){return q.x?'<button data-do="gotoplace" data-value="'+esc(q.x+'|'+q.y+'|'+q.z)+'" title="Go there\nCentre the camera on its notice board.">Go to</button>':''}
function renderQuests(m){const pg=$('page-quests');if(!pg)return;const D=m.quests,T=D?arr(D.taken):[],O=D?arr(D.ours):[];
 if(D){text($('questTakenN'),String(T.filter(q=>q.mine==='taken'&&(q.state==='open'||q.state==='closing')).length||''));text($('questOursN'),String(O.filter(q=>q.state==='open'||q.state==='closing').length||''))}
 if(pg.hidden||!D)return;
 pg.querySelectorAll('[data-questview]').forEach(b=>{const on=String(b.dataset.questview===questView);if(b.getAttribute('aria-selected')!==on)b.setAttribute('aria-selected',on)});
 text($('questRenown'),'Renown '+(D.renown||0));const body=$('questBody');
 if(questView==='ours'&&D.post){questFormRender(body,D);return}
 const key=JSON.stringify([questView,T,O,D.open,D.cap,D.coins,D.standing]);if(key===questKey)return;questKey=key;questFormKey='';
 if(questView==='taken'){body.innerHTML=T.length?T.map(q=>{const open=q.mine==='taken'&&(q.state==='open'||q.state==='closing');
   return '<div class="qrow"><b>'+questMark(q.mark)+esc(q.title)+'</b><small>'+esc([q.house,open&&q.need?questGoalText(q):q.mine==='done'?'Done':questStateText(q),open?q.left:''].filter(Boolean).join(' · '))+'</small>'
    +'<div class="acts">'+(q.state!=='gone'?'<button data-do="quest" data-value="'+esc('open|'+q.id)+'">Open</button>'+questGo(q):'')+(open?'<button data-do="quest" data-value="'+esc('giveup|'+q.id)+'" title="Give up\nWhat you handed in is put back by its notice board, yours.">Give up</button>':'<button data-do="quest" data-value="'+esc('giveup|'+q.id)+'">Remove</button>')+'</div></div>'}).join('')
  :'<p class="hint">No quests taken. Select one of your people standing by a notice board and read the notices.</p>';return}
 body.innerHTML='<p class="hint">Notices up: '+(D.open||0)+' of '+(D.cap||1)+' (a '+esc(D.rank||'Camp')+'). A notice costs '+(D.cost||2)+' coins; the reward is held until it is done. Treasury: '+(D.coins||0)+' coins.</p>'
  +'<button data-do="quest" data-value="postform|1" title="Post a notice\nOne of your people must stand by your notice board, carrying any goods you put up.">Post a notice</button>'+questStandingRows(D)
  +(O.length?O.map(q=>'<div class="qrow"><b>'+esc(q.title)+'</b><small>'+esc([questStateText(q)||q.left,q.goal,q.reward?'Reward: '+q.reward:'',q.takers?q.takers+' took it':''].filter(Boolean).join(' · '))+'</small><div class="acts"><button data-do="quest" data-value="'+esc('open|'+q.id)+'">Open</button>'+questGo(q)+(q.state==='open'?'<button data-do="quest" data-value="'+esc('cancel|'+q.id)+'" title="Take it down\nThe reward comes back to you. If someone took it, it stays up for them until it ends.">Take down</button>':'')+'</div></div>').join(''):'<p class="hint">You have no notices up.</p>')}
// the post form: drawn again only when what it offers changes, keeping what was typed (questDraft)
function questFormRender(body,D){const P=D.post||{},kinds=arr(P.kinds),seen={},names=kinds.map(k=>{const n=String(k[1]);seen[n]=(seen[n]||0)+1;return n});
 const label=kinds.map((k,i)=>seen[names[i]]>1?names[i]+' ('+String(k[0]).split('/').pop()+')':names[i]);
 const K=questDraft.kind||'bring',pk=P.picked||null;
 const key=JSON.stringify([P.unit,P.carry,kinds.length,P.boards,K,P.pick,pk,P.plans,arr(P.hunt).length,P.fortPicked,questDraft.fortGoal,P.chain]);if(key===questFormKey)return;questFormKey=key;questKey='';
 const opt=(v,l,cur)=>'<option value="'+esc(v)+'"'+(String(v)===String(cur)?' selected':'')+'>'+esc(l)+'</option>';
 const head=!P.unit?'<p class="hint">'+(P.boards?'Select one of your people standing by your notice board: they post it and carry any goods you put up.':'Build a Notice board first (Build › Workshops), then select one of your people beside it.')+'</p>':'<p class="hint">'+esc(P.unitName)+' posts it at your notice board.</p>';
 // goals on targets (QuestTargets.dm): the target is picked in the world or on the world map, and held by the game
 const pickBtn=(w,l)=>{const on=P.pick===w||P.pick===w+'2';return '<button type="button" data-qpick="'+w+'"'+(on?' aria-pressed="true"':'')+' title="'+esc(l+'\nThe page steps aside: click it in the world'+(w==='thing'||w==='fortchamp'?'':' or on the world map')+'. Right-click or Esc stops.')+'">'+esc(on?'Picking… (Esc stops)':l)+'</button>'};
 const picked=w=>pk&&pk.kind===w?'<p class="hint qpicked">Picked: '+esc(pk.what||'')+' ('+pk.x+', '+pk.y+')</p>':'<p class="hint">Nothing picked yet.</p>';
 const exact='<label>How exact its marker is</label><select data-q="exact">'+opt('exact','The spot',questDraft.exact)+opt('circle','A circle about it ('+(P.circle||10)+' tiles)',questDraft.exact)+opt('words','No marker: only my words',questDraft.exact)+'</select>';
 const wide='<label>How wide (tiles)</label><input data-q="radius" type="number" min="0" max="'+(P.placeMax||12)+'" value="'+esc(questDraft.radius)+'">';
 let goal;
 if(K==='slay')goal='<label>The creature</label>'+pickBtn('thing','Pick it in the world')+picked('thing')+exact+'<p class="hint">A wild creature or beast your people see now. While your people or a taker’s see it, its marker follows it; out of sight it shows where it was last seen, and how long ago.</p>';
 else if(K==='hunt')goal='<div class="two"><div><label>Kind</label><select data-q="race">'+opt('','Pick…',questDraft.race)+arr(P.hunt).map(h=>opt(h[0],h[1],questDraft.race)).join('')+'</select></div><div><label>How many</label><input data-q="hunt" type="number" min="1" max="'+(P.huntMax||50)+'" value="'+esc(questDraft.hunt)+'"></div></div>'
  +'<label>Where they are (a hint, optional)</label>'+pickBtn('place','Pick an area')+(pk&&pk.kind==='place'?picked('place')+wide+exact:'')+'<p class="hint">Wild ones killed by the taker’s people count, wherever they are.</p>';
 else if(K==='clear')goal='<label>The cave or lair</label>'+pickBtn('mouth','Pick it')+picked('mouth')+exact+'<p class="hint">A lair is cleared when its beast dies; a cave when everything in it does, while the taker’s people are down there.</p>';
 else if(K==='reach')goal='<label>The place</label>'+pickBtn('place','Pick it')+picked('place')+'<div class="two"><div><label>Its name (optional)</label><input data-q="place" maxlength="30" placeholder="the old hold" value="'+esc(questDraft.place)+'"></div><div>'+wide+'</div></div>'+exact;
 else if(K==='work')goal='<label>Your build plan</label><select data-q="row">'+opt('','Pick…',questDraft.row)+arr(P.plans).map(p=>opt(p[0],p[1]+' · '+p[2]+' blocks',questDraft.row)).join('')+'</select><p class="hint">'+(arr(P.plans).length?'':'Mark one in Plan mode first. ')+'The taker’s builders lay it with their own stone or logs, at most '+(P.workMax||200)+' blocks; the blocks are yours. Your own builders leave it while the notice is up.</p>';
 else if(K==='fort'){const F=P.fortPicked||{},a=F.area,pt=p=>'<p class="hint qpicked">Picked: ('+p[0]+', '+p[1]+')</p>';   // a fort challenge (QuestForts.dm)
  goal='<label>Your fort\u2019s area</label>'+pickBtn('fortarea','Pick its two corners')+(a?'<p class="hint qpicked">Picked: '+(a[2]-a[0]+1)+' by '+(a[3]-a[1]+1)+' tiles</p>':'<p class="hint">Nothing picked yet (at most '+(P.fortMax||48)+' tiles each way).</p>')
   +'<label>The way in</label>'+pickBtn('fortdoor','Pick it')+(F.door?pt(F.door):'')
   +'<div class="two"><div><label>Goal</label><select data-q="fortGoal">'+opt('chest','Take the chest',questDraft.fortGoal)+opt('champion','Defeat my champion',questDraft.fortGoal)+'</select></div><div><label>Entry fee (coins)</label><input data-q="fee" type="number" min="0" max="1000" value="'+esc(questDraft.fee)+'"></div></div>'
   +(questDraft.fortGoal==='champion'?pickBtn('fortchamp','Pick your champion')+(F.championName?'<p class="hint qpicked">Picked: '+esc(F.championName)+'</p>':''):pickBtn('fortgoal','Pick the chest\u2019s spot')+(F.goal?pt(F.goal):''))
   +'<div class="two"><div><label>Lethal</label><select data-q="lethal">'+opt('1','Lethal: the fallen die',questDraft.lethal)+opt('0','Non-lethal: blows knock out',questDraft.lethal)+'</select></div><div><label>Captives</label><select data-q="captives">'+opt('0','No captives',questDraft.captives)+opt('1','The fallen may be taken',questDraft.captives)+'</select></div></div>'
   +'<p class="hint">Your garrison: your people posted inside when you post it; select more later and press Garrison on the notice. A taker\u2019s party fights them only inside the area, 20 minutes a try. What fallen takers drop stays in your fort.</p>'}
 else goal='<datalist id="questKinds">'+label.map(l=>'<option value="'+esc(l)+'"></option>').join('')+arr((P.chain||{}).tokens).map(t=>'<option value="'+esc('Token: '+t[1]+' ('+t[2]+')')+'"></option>').join('')+'</datalist>'
  +'<label>Bring what</label><input data-q="item" list="questKinds" placeholder="Iron Ingot, Logs, a sword…" value="'+esc(questDraft.item)+'">'
  +'<div class="two"><div><label>How many</label><input data-q="need" type="number" min="1" max="200" value="'+esc(questDraft.need)+'"></div><div><label>Lowest quality (gear)</label><select data-q="quality">'+opt('','Any',questDraft.quality)+arr(P.qualities).map(q=>opt(q,q,questDraft.quality)).join('')+'</select></div></div>'+'<p class="hint" data-qrate>'+esc(questRateText(P,questDraft.item))+'</p>'+questStandHtml();
 body.innerHTML=head+'<div class="qform"><label>Goal</label><select data-q="kind">'+opt('bring','Bring goods',K)+opt('slay','Slay a creature',K)+opt('hunt','Hunt a kind of creature',K)+opt('clear','Clear a cave or lair',K)+opt('reach','Reach a place',K)+opt('work','Work on my build',K)+opt('fort','Storm my fort',K)+'</select>'
  +goal+questChainFields(P,K)
  +'<div class="two"><div><label>Reward: coins</label><input data-q="coins" type="number" min="0" value="'+esc(questDraft.coins)+'"></div><div><label>Stays up</label><select data-q="days">'+arr(P.days).map(d=>opt(d,d+(d===1?' day':' days'),questDraft.days)).join('')+'</select></div></div>'
  +'<label>Reward: goods '+esc(P.unitName||'')+' carries</label><div class="goods">'+(arr(P.carry).length?arr(P.carry).map(g=>'<label><input type="checkbox" data-qgood="'+esc(g.ref)+'"'+(questDraft.goods.has(g.ref)?' checked':'')+'>'+esc(g.name)+'</label>').join(''):'<p class="hint">Nothing carried.</p>')+'</div>'
  +'<div class="two"><div><label>Who may take it</label><select data-q="who">'+opt('anyone','Anyone',questDraft.who)+opt('others','Only other realms',questDraft.who)+opt('realm','Only my realm',questDraft.who)+'</select></div><div><label>Settlement at least</label><select data-q="rank">'+arr(P.ranks).map((r,i)=>opt(i+1,r,questDraft.rank)).join('')+'</select></div></div>'
  +'<label>Title (optional)</label><input data-q="title" maxlength="40" value="'+esc(questDraft.title)+'">'
  +'<label>Their words (optional)</label><textarea data-q="text" rows="3" maxlength="300">'+esc(questDraft.text)+'</textarea>'
  +'<div class="acts"><button data-qsubmit="1"'+(P.unit?'':' disabled')+'>Post it</button><button data-do="quest" data-value="postform|0">Cancel</button></div></div>';
 body.querySelector('.qform').dataset.kinds=JSON.stringify(kinds.map((k,i)=>[label[i],k[0]]).concat(arr((P.chain||{}).tokens).map(t=>['Token: '+t[1]+' ('+t[2]+')','token:'+t[0]])))}
document.addEventListener('input',e=>{const f=e.target.closest&&e.target.closest('#page-quests .qform');if(!f)return;const q=e.target.dataset.q;if(q)questDraft[q]=e.target.type==='checkbox'?(e.target.checked?'1':'0'):e.target.value;if(q==='kind'||q==='fortGoal'){questFormKey='';if(model)renderQuests(model);return}if(q==='item'){if(e.target.setCustomValidity)e.target.setCustomValidity('');const r=f.querySelector('[data-qrate]'),PD=model&&model.quests&&model.quests.post;if(r&&PD)r.textContent=questRateText(PD,e.target.value)}const g=e.target.dataset.qgood;if(g){if(e.target.checked)questDraft.goods.add(g);else questDraft.goods.delete(g)}});
document.addEventListener('change',e=>{const g=e.target.closest&&e.target.closest('#page-quests .qform input[data-qgood]');if(!g)return;if(g.checked)questDraft.goods.add(g.dataset.qgood);else questDraft.goods.delete(g.dataset.qgood)});
document.addEventListener('click',e=>{const b=e.target.closest('#page-quests [data-qsubmit]');if(!b||b.disabled)return;const f=b.closest('.qform'),K=questDraft.kind||'bring';let item=null,want='';
 if(K==='bring'){let map=[];try{map=JSON.parse(f.dataset.kinds||'[]')}catch(_){}
  const hit=map.find(k=>k[0].toLowerCase()===String(questDraft.item).trim().toLowerCase());if(!hit){const i=f.querySelector('[data-q=item]');i.focus();i.setCustomValidity&&i.setCustomValidity('Pick a kind from the list');i.reportValidity&&i.reportValidity();return}item=hit[1];if(String(item).startsWith('token:')){want=item.slice(6);item=null}}
 const D=model&&model.quests&&model.quests.post;send('quest','post|'+JSON.stringify({kind:K,unit:D&&D.unit,item,need:K==='hunt'?questDraft.hunt:questDraft.need,quality:questDraft.quality,coins:questDraft.coins,goods:[...questDraft.goods],who:questDraft.who,rank:questDraft.rank,days:questDraft.days,title:questDraft.title,text:questDraft.text,race:questDraft.race,exact:questDraft.exact,radius:questDraft.radius,place:questDraft.place,row:questDraft.row,fortGoal:questDraft.fortGoal,lethal:questDraft.lethal,captives:questDraft.captives,fee:questDraft.fee,token:want,after:[[questDraft.after1,questDraft.cond1],[questDraft.after2,questDraft.cond2]].filter(a=>a[0]),afterMode:questDraft.afterMode,gives:questDraft.gives,secret:questDraft.secret,keep:K==='bring'&&!want?questDraft.keep:'0',each:questDraft.each}));
 questDraft.goods.clear();questDraft.title='';questDraft.text='';questFormKey='';
 Object.assign(questDraft,{after1:'',cond1:'done',after2:'',cond2:'done',afterMode:'all',gives:'',secret:'0',keep:'0'})});
// Pick in the world (QuestTargets.dm RmQuestPickStart): the server holds what is picked; pressed again, it stops
document.addEventListener('click',e=>{const b=e.target.closest('#page-quests [data-qpick]');if(!b)return;const D=model&&model.quests&&model.quests.post;send('quest','pick|'+(D&&D.pick===b.dataset.qpick?'':b.dataset.qpick))});
addEventListener('keydown',e=>{if(e.key==='Escape'&&model&&model.questPick){send('quest','pick|');e.stopImmediatePropagation()}},true);
// While picking, the page steps aside and a banner says what to click; when the pick is made, the page comes back.
const QPICK={thing:'the creature: click it in the world',mouth:'the cave mouth or lair: click it in the world or on the world map',fortarea:'one corner of your fort\u2019s area: click it in the world or on the world map',fortarea2:'the opposite corner of your fort\u2019s area',fortdoor:'the way into your fort',fortgoal:'where the chest goes',fortchamp:'your champion: click one of your people inside the fort'};
let questPickWas=null;
function questPickWatch(m){const p=m.questPick||null;if(p===questPickWas)return;const was=questPickWas;questPickWas=p;const bb=$('build3d');
 if(p){if(overlayHost&&document.body.classList.contains('panel-open')){document.body.classList.remove('panel-open');queueRegions()}
  if(bb){bb.hidden=false;text(bb,'Picking '+(QPICK[p]||'the place: click it in the world or on the world map')+' · right-click or Esc stops')}}
 else{if(bb&&!V3.shop&&!V3.build)bb.hidden=true;
  if(was&&overlayHost){if(m.tab!=='quests')send('tab','quests');document.body.classList.add('panel-open');queueRegions()}}}
// The quest markers in 3D (QuestTargets.dm RmQuestMarksData): a pin over each, following a quarry while it is in sight.
function questPins3D(){const L=arr(model&&model.questMarks);let box=$('qpins3d');if(!box){if(!L.length)return;box=document.createElement('div');box.id='qpins3d';box.setAttribute('aria-hidden','true');const f=$('food3d');f.parentNode.insertBefore(box,f.nextSibling)}
 while(box.childElementCount<L.length)box.append(document.createElement('span'));const lv=z=>z===3?1:z;
 [...box.children].forEach((e,i)=>{const q=L[i];if(!q||lv(q.z)!==lv(V3.z)){e.hidden=true;return}
  const t=q.ref?V3.things.find(o=>o.id===q.ref):null;let P;if(t){const w=v3world(t);P=[w[0],v3groundAt(t.x,t.y)+2.4,w[2]]}else P=[q.x,v3groundAt(q.x,q.y)+0.9,-q.y];
  const s=v3project(P);if(!s){e.hidden=true;return}e.hidden=false;
  const sub=q.now?'':[q.ago,q.r>=8&&q.how!=='own'?'somewhere about here':''].filter(Boolean).join(' · '),k=q.how+'|'+q.title+'|'+sub;
  if(e.dataset.k!==k){e.dataset.k=k;e.className=q.how;e.innerHTML='<b>'+(q.how==='taken'?'⚑ ':q.how==='own'?'◆ ':'◇ ')+esc(q.title)+'</b>'+(sub?'<small>'+esc(sub)+'</small>':'')}
  e.style.transform='translate('+Math.round(s[0])+'px,'+Math.round(s[1])+'px) translate(-50%,-100%)'})}
// ...and on the world map: a pin and the place's circle; a vague one (a circle about it) only the circle.
function questMapMarks(g,PX,PY,k,W){for(const q of arr(W.quests)){const x=PX(q.x+0.5),y=PY(q.y+0.5),vague=q.r>=8&&q.how!=='own'&&!q.now;g.save();
  if(q.r>0){g.strokeStyle=q.how==='taken'?'rgba(255,215,94,.95)':'rgba(255,215,94,.6)';g.setLineDash(vague?[6,5]:[]);g.lineWidth=2;g.beginPath();g.arc(x,y,Math.max(4,q.r*k),0,Math.PI*2);g.stroke();g.setLineDash([])}
  if(!vague){g.fillStyle='#ffd75e';g.strokeStyle='#1a1408';g.lineWidth=2;g.beginPath();g.moveTo(x,y);g.lineTo(x-7,y-14);g.lineTo(x+7,y-14);g.closePath();g.fill();g.stroke()}
  const lab=q.title+(q.now?'':q.ago?' ('+q.ago.replace('last seen ','')+')':'');g.font='bold 17px HudText,Georgia,serif';g.textAlign='center';g.lineWidth=4;g.strokeStyle='#120e07';g.fillStyle='#ffe7a3';g.strokeText(lab,x,y-19);g.fillText(lab,x,y-19);g.restore()}}
document.addEventListener('click',e=>{const b=e.target.closest('#page-quests [data-questview]');if(!b)return;questView=b.dataset.questview;questKey='';questFormKey='';if(model)renderQuests(model)});
// "Post a notice" on the unit card: the Quests page, Ours, with the form (the second send waits a moment: two sends in
// one task lose the first)
function questOpenPost(){questView='ours';questKey='';questFormKey='';send('tab','quests');if(overlayHost){document.body.classList.add('panel-open');queueRegions()}setTimeout(()=>send('quest','postform|1'),120)}
document.addEventListener('click',e=>{const b=e.target.closest('[data-qpost]');if(b){e.preventDefault();questOpenPost()}});
// A fort challenge's terms on its card (QuestForts.dm): the fight, the entry, the garrison, the danger, the tries.
// Chains (QuestChains.dm): the post form's fields, and the card's lines.
function questChainFields(P,K){const C=P.chain||{},L=arr(C.links),opt=(v,l,cur)=>'<option value="'+esc(v)+'"'+(String(v)===String(cur)?' selected':'')+'>'+esc(l)+'</option>';
 const pick=n=>'<div class="two"><div><select data-q="after'+n+'" aria-label="Comes after">'+opt('','None',questDraft['after'+n])+L.map(q=>opt(q[0],q[1]+' \u00b7 '+q[2]+(q[3]!=='open'?' ('+q[3]+')':''),questDraft['after'+n])).join('')+'</select></div><div><select data-q="cond'+n+'" aria-label="Once">'+opt('done','once done',questDraft['cond'+n])+opt('failed','once failed',questDraft['cond'+n])+'</select></div></div>';
 return '<details class="qchain"'+(questDraft.after1||questDraft.gives?' open':'')+'><summary>Chain: what comes first, a token it gives</summary>'
  +'<label>Comes after (optional)</label>'+pick(1)+pick(2)
  +'<label>With two</label><select data-q="afterMode">'+opt('all','Both',questDraft.afterMode)+opt('any','Either one',questDraft.afterMode)+'</select>'
  +'<label>Gives a token (optional)</label><input data-q="gives" maxlength="30" placeholder="the hold\u2019s seal" value="'+esc(questDraft.gives)+'">'
  +(K!=='bring'?'<label><input type="checkbox" data-q="secret"'+(questDraft.secret==='1'?' checked':'')+'>Keep where it is secret until the step before is done</label>':'')
  +'<p class="hint">A token is a real item for whoever does it: it can be traded, stolen or lost, and any notice, yours or anyone\u2019s, may ask for it in a Bring goal.</p></details>'}
function questChainRows(H){let h='';
 if(arr(H.after).length)h+='<dt>Comes after</dt><dd>'+arr(H.after).map(a=>(a[3]?'\u2714 ':'\u25cb ')+esc((a[2]==='failed'?'failing ':'')+'\u201c'+a[0]+'\u201d ('+a[1]+')')).join(H.mode==='any'?' or ':', ')+'</dd>';
 if(H.wants)h+='<dt>Asks for</dt><dd>'+esc(H.wants)+' (a token)</dd>';
 if(H.token)h+='<dt>Gives</dt><dd>'+esc(H.token)+' (a token)</dd>';
 if(arr(H.next).length)h+='<dt>Leads to</dt><dd>'+esc(arr(H.next).map(t=>'\u201c'+t+'\u201d').join(', '))+'</dd>';return h}
function questFortRows(F){const dg=F.danger?F.danger+' (your '+F.party+' at the way in: '+F.partyPower+' against '+F.power+')':'Garrison strength '+F.power;
 return '<dt>Fight</dt><dd>'+(F.lethal?'Lethal: the fallen die':'Non-lethal: blows knock out')+' · '+(F.captives?'the fallen may be taken captive':'no captives')+'</dd>'
  +'<dt>Entry</dt><dd>'+(F.fee?F.fee+' coins, kept win or lose':'Free')+'</dd>'
  +'<dt>Garrison</dt><dd>'+F.garrison+' '+(F.garrison===1?'guard':'guards')+(F.champion?' · champion '+esc(F.champion):'')+'</dd>'
  +'<dt>Danger</dt><dd>'+esc(dg)+'</dd><dt>Tries</dt><dd>'+arr(F.tries).length+' recorded · '+(F.won||0)+' won</dd>'+(arr(F.report).length?'<dt>Report</dt><dd>'+arr(F.report).map(esc).join('<br>')+'</dd>':'')}
function questFortNotes(C,mine){const F=C.fort,T=F.try;let h='';
 if(T)h+='<p class="qc-note">'+esc((T.mine?'Your try':T.house+'\u2019s try')+' is on: '+T.left+' min left · '+T.in+' of '+T.went+' still in · '+T.standing+' of the garrison standing.')+'</p>';
 else if(mine&&F.why)h+='<p class="qc-note no">'+esc(F.why)+'</p>';
 if(arr(F.tries).length)h+='<ol class="qc-journal">'+arr(F.tries).slice(-3).map(t=>'<li>'+esc(t)+'</li>').join('')+'</ol>';return h}
function renderQuestCard(m){const c=$('questcard');if(!c)return;const C=m.questCard;if(!C){if(!c.hidden){c.hidden=true;questCardKey='';queueRegions()}return}
 const QM=C.id?arr(m.questMarks).find(q=>q.id===C.id):null,key=JSON.stringify([C,QM?[QM.x,QM.y,QM.z]:0]);if(key===questCardKey&&!c.hidden)return;questCardKey=key;
 const btn=(v,l,t,cls)=>'<button data-do="quest" data-value="'+esc(v)+'"'+(t?' title="'+esc(t)+'"':'')+(cls?' class="'+cls+'"':'')+'>'+esc(l)+'</button>';
 let h;if(C.kind==='board'){const R=arr(C.rows);
  h='<div class="qc-head"><div class="qc-t"><b>Notice board</b><small>'+esc(C.house||'')+(C.renown?' · renown '+C.renown:'')+'</small></div>'+btn('close','×','Close','qc-x')+'</div><div class="qc-body"><div class="qc-list">'
   +(R.length?R.map(q=>'<button data-do="quest" data-value="'+esc('open|'+q.id)+'">'+questMark(q.mark)+esc(q.title)+(q.danger?'<span class="qdg qdg-'+esc(q.danger.toLowerCase())+'" title="'+esc('For your people here: '+q.danger)+'">'+esc(q.danger)+'</span>':'')+'<small>'+esc(q.own?'yours':q.house)+' · '+esc(q.reward||'')+'</small></button>').join(''):'<p class="hint">No notices here.'+(C.own?' Post one from the Quests page.':'')+'</p>')
   +'</div></div><div class="qc-foot">'+(C.own?'<button data-qpost="1">Post a notice</button>':'')+(C.party?btn('sort|'+(C.sort==='manage'?'new':'manage'),C.sort==='manage'?'Newest first':'What we can manage',C.sort==='manage'?'Newest first\nThe board\u2019s own order.':'What we can manage\nRated for your people here against each garrison, creature or cave: the easiest first.'):'')+'<span class="grow"></span>'+btn('close','Close')+'</div>'}
 else if(C.kind==='keeper')h=questKeeperHtml(C,btn);   // a keeper's talk (QuestKeepers.dm)
 else{const U=C.unit,mine=C.mine==='taken'&&(C.state==='open'||C.state==='closing'),S=C.stats||{};
  const bring=(C.goalKind||'bring')==='bring',goal=mine&&C.need?questGoalText(C):(C.goal||'');
  const state=C.state==='done'?'Done by '+(C.winner||'someone'):C.state==='ended'?'Ended: '+(C.ended||''):C.state==='closing'?'Taken down: those who took it have until it ends':'';
  h='<div class="qc-head"><div class="qc-t"><b>'+esc(C.title)+'</b><small>'+esc((C.own?'Your notice':'By '+(C.house||''))+(C.renown?' · renown '+C.renown:''))+'</small></div>'+btn('close','×','Close','qc-x')+'</div><div class="qc-body">'
   +(C.keeper?'<div class="qc-says">“'+esc(C.keeper.line)+'”<i>'+esc(C.keeper.name)+'</i></div>':'')+(C.text?'<div class="qc-says">“'+esc(C.text)+'”<i>their words</i></div>':'')
   +'<div class="qc-game"><i>checked by the game</i><h4>'+esc(bring?'Bring '+(C.goal||''):(C.goal||''))+'</h4><dl>'
   +'<dt>Goal</dt><dd>'+questMark(C.mark)+' '+esc(goal)+'</dd><dt>'+(C.world?'Prize':'Reward')+'</dt><dd>'+esc(C.reward||'none')+(!C.world&&(C.state==='open'||C.state==='closing')?': held until it closes':'')+'</dd>'
   +'<dt>Who</dt><dd>'+esc(C.who||'Anyone')+'</dd><dt>Time</dt><dd>'+esc(state||C.left||'')+'</dd>'
   +'<dt>Taken</dt><dd>'+(S.taken||0)+' took it · '+(S.done||0)+' done'+(S.gaveup?' · '+S.gaveup+' gave up':'')+'</dd>'+(bring?'<dt>Hand in</dt><dd>'+(C.where?esc(C.where):'At its own notice board')+'</dd>':'<dt>Where</dt><dd>'+esc(C.target||'')+'</dd>'+(C.goalKind==='work'?'<dt>Bring</dt><dd>Your own '+(C.mat==='wood'?'logs':'stone')+'</dd>':''))+(C.fort?questFortRows(C.fort):'')+(C.chain?questChainRows(C.chain):'')+'</dl></div>'
   +(U?'<p class="qc-note">'+esc(U.name)+(U.here?' is at its notice board'+(C.need&&bring?'; your people here carry '+(U.carry||0)+' of them.':'.'):' is at a notice board that shows it.')+'</p>':'<p class="qc-note">Select one of your people by a notice board that shows it to take it'+(mine?', or by its own board to hand in.':'.')+'</p>')
   +(C.why&&!C.own&&!mine&&C.state==='open'?'<p class="qc-note no">'+esc(C.why)+'</p>':'')
   +(C.fort?questFortNotes(C,mine):'')
   +(arr(C.journal).length?'<ol class="qc-journal">'+arr(C.journal).slice(-8).map(j=>'<li>'+esc(arr(j)[0])+'</li>').join('')+'</ol>':'')
   +'</div><div class="qc-foot">'
   +(!C.why&&U&&C.state==='open'?btn('take|'+C.id+'|'+U.ref,'Take it','Take it\nIt goes in your quest log (Quests › Taken).'):'')
   +(bring&&mine&&U&&U.here&&U.carry?btn('handin|'+C.id+'|'+U.ref,'Hand in ('+Math.min(U.carry,(C.need||0)-(C.got||0))+')','Hand in\nEvery one of your people at the board hands in what they carry of it.'):'')
   +(C.fort&&C.own&&C.state==='open'&&C.fort.selected?btn('garrison|'+C.id,'Garrison ('+C.fort.selected+')','Garrison\nYour selected people take posts inside the fort and guard it, while you are away too.'):'')
   +(C.fort&&mine&&!C.fort.why&&!C.fort.try?btn('try|'+C.id,'Start a try','Start a try\nYour people at the way in go in; the entry fee goes to the fort\u2019s maker.'):'')
   +(mine?btn('giveup|'+C.id,'Give up','Give up\nWhat you handed in is put back by its notice board, yours.'):'')
   +(C.own&&C.state==='open'?btn('cancel|'+C.id,'Take down','Take it down\nThe reward comes back to you. If someone took it, it stays up for them until it ends.'):'')
   +(C.x?'<button data-do="gotoplace" data-value="'+esc(C.x+'|'+C.y+'|'+C.z)+'" title="Go to its notice board">Go to</button>':'')+(QM?'<button data-do="gotoplace" data-value="'+esc(QM.x+'|'+QM.y+'|'+QM.z)+'" title="Go to its marker">To the marker</button>':'')+(C.report?'<button data-qrep="'+esc('quest|'+C.id)+'" title="Report this notice\nRude words, a scam or a false notice: the admins look at it.">Report</button>':'')+(C.keeper?btn('keeperback','Back','Back\nTo '+C.keeper.name+'.'):'')+'<span class="grow"></span>'+btn('close','Close')+'</div>'}
 c.innerHTML=h;if(c.hidden){c.hidden=false;queueRegions()}}
// Goal lines: Bring counts what is in; the others say the goal, with a count when there is more than one to do.
function questGoalText(q){const bring=(q.goalKind||q.kind||'bring')==='bring';return bring?(q.got||0)+' of '+q.need+' '+String(q.goal||'').replace(/^\d+ /,''):String(q.goal||'')+(q.need>1?' ('+(q.got||0)+' of '+q.need+')':'')}
// Where to go, from the selected unit (else the camera): its marker (live from questMarks), or the board to hand in at.
function questFrom(m){const u=arr(m.units).find(u=>u.selected&&u.x!=null);return u?{x:u.x,y:u.y,z:u.z}:{x:m.x,y:m.y,z:m.z}}
function questWay(m,q){const M=arr(m.questMarks).find(k=>k.id===q.id),P=M||q;if(P.x==null)return '';const F=questFrom(m),dx=P.x-F.x,dy=P.y-F.y,d=Math.round(Math.hypot(dx,dy)),r=P.r||0;
 const ago=M&&M.ago&&!M.now?' · '+M.ago:'',lvl=P.z!==F.z&&!((P.z===1||P.z===3)&&(F.z===1||F.z===3))?' · on another level':'';
 if(d<=Math.max(1,r))return (M&&M.now?'Here, in sight':'Here')+ago+lvl;
 const D=['E','NE','N','NW','W','SW','S','SE'],A={E:'→',NE:'↗',N:'↑',NW:'↖',W:'←',SW:'↙',S:'↓',SE:'↘'},dir=D[((Math.round(Math.atan2(dy,dx)/(Math.PI/4))%8)+8)%8];
 return A[dir]+' '+d+' tiles '+dir+(r>=8&&!(M&&M.now)?', somewhere about there':'')+ago+lvl}
function renderQuestTrack(m){questPickWatch(m);const t=$('questtrack');if(!t)return;const L=arr(m.questTrack),W=L.map(q=>questWay(m,q)),key=JSON.stringify([L,W]);if(key===questTrackKey)return;questTrackKey=key;
 if(!L.length||!overlayHost){if(!t.hidden){t.hidden=true;queueRegions()}return}
 t.innerHTML='<span>Quests · '+L.length+'</span>'+L.map((q,i)=>'<button data-do="quest" data-value="'+esc('open|'+q.id)+'" title="'+esc(q.title+'\nClick: open it.')+'"><b>'+esc(q.title)+'</b><small>○ '+esc((q.kind||'bring')==='bring'?q.goal+' '+(q.got||0)+'/'+q.need:questGoalText(q))+'</small>'+(W[i]?'<small>'+esc(W[i])+'</small>':'')+'<small>'+esc(q.left||'')+'</small></button>').join('');
 if(t.hidden){t.hidden=false;queueRegions()}questTrackPlace()}
// under the goal and the Supplies card on the left, like the Supplies card is placed under the goal (033 fmSupplyPlace)
function questTrackPlace(){const el=$('questtrack');if(!el||el.hidden)return;const k=hudKC();let top=56;
 for(const id of ['topbar','goaltrack','fmSupplies']){const e=$(id);if(e&&e.getClientRects().length&&getComputedStyle(e).display!=='none'){const b=e.getBoundingClientRect();if(b.height>0&&b.left/k<240)top=Math.max(top,b.bottom/k+8)}}
 const v=Math.round(top)+'px';if(el.style.top!==v)el.style.top=v}
addEventListener('resize',()=>requestAnimationFrame(questTrackPlace));setInterval(questTrackPlace,1000);
// --- Admin (Moderation.dm; planning/ADMIN_PANEL_PLAN_2026-10-31.md, A1-A2): the Admin button and page for the staff
// (Quests, Players, Reports, Log; the top boxes: a search, and the reason or message that goes with an action), and the
// players' Report buttons (a notice's card, another realm's people in the near card). The server checks every action.
let adminKey='',adminFind='';
const REPORT_REASONS=[['rude','Rude words'],['scam','Scam or false notice'],['grief','Griefing'],['cheat','Cheating'],['other','Other']];
{const st=document.createElement('style');st.textContent=
 '#page-admin .adm-top{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:6px;margin:0 0 8px}#page-admin .adm-top input{box-sizing:border-box;width:100%;padding:4px 6px;background:#0f0d0a;border:1px solid #5d4a2a;color:#efe6cc;font:12.5px HudText,Georgia,serif}'+
 '#page-admin .qrow{padding:7px 0;border-bottom:1px solid rgba(176,138,62,.25)}#page-admin .qrow>b{display:block;font:14px HudText,Georgia,serif}#page-admin .qrow>small{display:block;font-size:11.5px;color:#c9bd9e}#page-admin .qrow .acts{display:flex;flex-wrap:wrap;gap:4px;margin-top:5px}#page-admin .qrow .acts button{min-height:26px;padding:0 6px;font-size:11.5px}'+
 '#page-admin .adm-word{display:flex;gap:6px;margin:0 0 8px}#page-admin .adm-word input{flex:1;min-width:0;box-sizing:border-box;padding:4px 6px;background:#0f0d0a;border:1px solid #5d4a2a;color:#efe6cc;font:12.5px HudText,Georgia,serif}'+
 '#page-admin .qrow.open>b{color:#ffd28a}#page-admin .on{color:#8fbf73}#page-admin .admlog{padding:3px 0;border-bottom:1px solid rgba(176,138,62,.15);font-size:11.5px;color:#d6cfbd;overflow-wrap:anywhere}'+
 '.qrep-row{display:flex;flex-wrap:wrap;align-items:center;gap:4px;margin-top:6px}.qrep-row>span{font-size:11.5px;color:#c9bd9e;margin-right:2px}.qrep-row button{min-height:24px;padding:0 6px;font-size:11.5px}'+
 '#page-admin .adm-restart{display:flex;flex-wrap:wrap;align-items:center;gap:6px;margin:0 0 8px;font-size:12px;color:#d6cfbd}#page-admin .adm-restart:empty{display:none}#page-admin .adm-restart b{color:#ffd28a;font-weight:normal}#page-admin .adm-restart select{padding:3px 4px;background:#0f0d0a;border:1px solid #5d4a2a;color:#efe6cc;font:12.5px HudText,Georgia,serif}#page-admin .adm-restart button{min-height:26px;padding:0 8px;font-size:11.5px}'+
 '#page-admin .bugtext{white-space:pre-wrap;overflow-wrap:anywhere;color:#efe6cc}#page-admin .bugdet{margin:5px 0;padding:5px 7px;background:rgba(0,0,0,.28);font-size:11px;color:#d6cfbd;overflow-wrap:anywhere}#page-admin .bugdet i{display:block;font-style:normal;color:#c9bd9e;margin-bottom:2px}'+
 '#bugform{position:fixed;left:50%;top:50%;transform:translate(-50%,-50%);z-index:9000;width:min(460px,calc(100vw - 32px));max-height:calc(100vh - 32px);overflow:auto;box-sizing:border-box;padding:14px 16px;background:#1d1a14;border:1px solid #b08a3e;color:#efe6cc;font:13px HudText,Georgia,serif;display:flex;flex-direction:column;gap:9px}'+
 '#bugform>b{font:16px HudCaps,Herculanum,HudHead,Georgia,serif;letter-spacing:.06em;color:#f2d27a}#bugform label{display:flex;flex-direction:column;gap:3px}#bugform label.bugchk{flex-direction:row;align-items:flex-start;gap:7px}'+
 '#bugform textarea,#bugform select{box-sizing:border-box;width:100%;padding:4px 6px;background:#0f0d0a;border:1px solid #5d4a2a;color:#efe6cc;font:12.5px HudText,Georgia,serif;resize:vertical}#bugform .hint{margin:0}#bugform .bugacts{display:flex;gap:8px;justify-content:flex-end}#bugform .bugacts button{min-height:28px;padding:0 14px}';
 document.head.append(st)}
function admRank(l){return l==='owner'?3:l==='admin'?2:l==='mod'?1:0}
// --- bug reports (Bugs.dm, the owner 11-01) ---------------------------------------------------------------------------
const BUG_KINDS=[['stuck','Units stuck'],['fight','Fighting'],['work','Building & work'],['screen','Screen & buttons'],['lag','Lag'],['other','Other']];
const BUG_KIND=Object.fromEntries(BUG_KINDS),BUG_STATE={new:'New',seen:'Seen',confirmed:'Confirmed',fixed:'Fixed',notbug:'Not a bug',dup:'Duplicate'};
// An opened row's details, all as text: what the server knows, then what the browser says (hints: it could be faked).
function bugDetails(d){const sec=(t,L)=>L&&L.length?'<div class="bugdet"><i>'+esc(t)+'</i>'+L.map(x=>'<div>'+esc(x)+'</div>').join('')+'</div>':'';
 const U=arr(d.units).map(u=>u.name+' ('+u.race+') '+u.hp+'/'+u.maxhp+' health · '+(u.job||'no job')+(u.doing?' · '+u.doing:'')+' · at '+u.x+','+u.y+','+u.z);
 const h=d.hints,H=h?[(h.screen?'screen '+h.screen:'')+(h.fps!=null?' · '+h.fps+' frames a second':'')+(h.lag!=null?' · lag '+h.lag+' ms':''),h.ua||''].filter(Boolean).concat(arr(h.errors)):[];
 return sec('Selected units',U)+sec('Their log, last lines',arr(d.log))+sec('Server errors just before',arr(d.server))+sec('The browser says (hints: it could be faked)',H)
  +(d.stack?sec('Stack',String(d.stack).split('\n').filter(Boolean)):'')+(d.playerList&&d.playerList.length?sec('Players it hit',d.playerList):'')}
// Settings > Report a bug: what went wrong, what they were doing and a kind; "Add what the game knows" (on by default)
// lets the server add the place, the selected units and the log, and the page its screen, frame rate and own errors.
function bugFormClose(){const d=$('bugform');if(d)d.remove();try{queueRegions()}catch(_){}}
function bugFormOpen(){if($('bugform'))return;const d=document.createElement('section');d.id='bugform';d.className='ovonly';d.setAttribute('role','dialog');d.setAttribute('aria-label','Report a bug');
 d.innerHTML='<b>Report a bug</b><label>What kind<select id="bugKind">'+BUG_KINDS.map(k=>'<option value="'+k[0]+'">'+esc(k[1])+'</option>').join('')+'</select></label>'
  +'<label>What went wrong?<textarea id="bugText" maxlength="1000" rows="4" placeholder="What happened, and what you expected to happen"></textarea></label>'
  +'<label>What were you doing? <span class="hint">(optional)</span><textarea id="bugDoing" maxlength="500" rows="2"></textarea></label>'
  +'<label class="bugchk"><input type="checkbox" id="bugDetails" checked><span>Add what the game knows: where you are, your selected units, your village log, your screen and frame rate</span></label>'
  +'<p class="hint">The admins read every report. Please leave out personal details.</p>'
  +'<div class="bugacts"><button type="button" id="bugCancel">Cancel</button><button type="button" id="bugSend">Send</button></div>';
 document.body.append(d);$('settings').hidden=true;try{queueRegions()}catch(_){}setTimeout(()=>{const t=$('bugText');if(t)t.focus()},0)}
document.addEventListener('click',e=>{if(e.target.closest('#setBug')){bugFormOpen();return}if(e.target.closest('#bugCancel')){bugFormClose();return}
 if(!e.target.closest('#bugSend'))return;const t=$('bugText'),v=t?t.value.trim():'';if(v.length<3){if(t)t.focus();return}
 const det=!!($('bugDetails')||{}).checked,hints=det?{screen:innerWidth+'x'+innerHeight+'@'+(window.devicePixelRatio||1),ua:String(navigator.userAgent||'').slice(0,200),fps:window.rmFpsNow,errors:(window.__rmErrs||[]).slice(-10)}:null;
 send('bugreport',JSON.stringify({kind:($('bugKind')||{}).value||'other',text:v.slice(0,1000),doing:(($('bugDoing')||{}).value||'').trim().slice(0,500),details:det?1:0,hints:hints}));bugFormClose()});
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&$('bugform')){e.preventDefault();e.stopPropagation();bugFormClose()}},true);
// The restart notice (Moderation.dm, the owner 11-01): Admins pick the minutes and send it, the reason box is its message;
// while it runs every staff page shows what is left, and Admins may call it off. Drawn again only when its words change.
let adminRestartKey='';
function renderAdminRestart(A){const el=$('adminRestart');if(!el)return;const me=admRank(A.level),R=A.restart;
 const left=R?(R.left>=90?Math.round(R.left/60)+' minutes':R.left>=60?'1 minute':Math.max(1,Math.round(R.left))+' seconds'):'';
 const key=R?'on|'+left+'|'+R.why+'|'+me:me>=2?'off':'';if(key===adminRestartKey)return;adminRestartKey=key;
 if(R){el.innerHTML='<span>Restart notice: <b>in '+esc(left)+'</b>'+(R.why?' · “'+esc(R.why)+'”':'')+' · by '+esc(R.by)+'</span>'+(me>=2?'<button data-adm="restart|0" title="Call it off\nEveryone is told the world goes on.">Call off</button>':'');return}
 el.innerHTML=me>=2?'<span>Warn everyone of a restart in</span><select id="adminRestartMins" aria-label="Minutes until the restart">'+[1,2,5,10,15,30].map(n=>'<option value="'+n+'"'+(n===5?' selected':'')+'>'+n+' min</option>').join('')+'</select><button data-admrestart="1" title="Send the restart notice\nEvery player online is told now and again as it nears; the reason box is its message. It only warns: restart the server yourself.">Send notice</button>':''}
document.addEventListener('click',e=>{const b=e.target.closest('#page-admin [data-admrestart]');if(!b)return;const s=$('adminRestartMins'),w=$('adminWhy');send('admin','restart|'+(s?s.value:'5')+'|'+(w?w.value.trim().replace(/\|/g,'/'):''))});
function renderAdmin(m){try{rmGuestBrowser(m)}catch(e){console.error(e)}const A=m.admin,nb=document.querySelector('nav [data-value=admin]');
 {const on=!!m.bugs,sb=$('setBug');window.rmBugsOn=on;if(sb&&sb.hidden===on)sb.hidden=!on}   // Settings > Report a bug, for everyone (Bugs.dm)
 if(nb){const show=!!A;if(nb.hidden===show)nb.hidden=!show;const n=A?(A.open||0)+(A.bugsNew||0):0,bd=n?(n>99?'99+':String(n)):'';if(nb.dataset.badge!==bd)nb.dataset.badge=bd}
 const pg=$('page-admin');if(!pg||!A)return;text($('adminOpenN'),A.open?String(A.open):'');text($('adminBugsN'),A.bugsNew?String(A.bugsNew):'');if(pg.hidden)return;
 pg.querySelectorAll('[data-admview]').forEach(b=>{const on=String(b.dataset.admview===A.view);if(b.getAttribute('aria-selected')!==on)b.setAttribute('aria-selected',on)});
 text($('adminLevel'),A.level==='owner'?'Owner':A.level==='admin'?'Admin':'Moderator');
 renderAdminRestart(A);
 const P=A.page,me=admRank(A.level),box=$('adminBody');const key=JSON.stringify([A.view,P,adminFind,me]);if(key===adminKey)return;adminKey=key;
 if(!P){box.innerHTML='<p class="hint">Loading…</p>';return}
 const f=s=>!adminFind||String(s).toLowerCase().includes(adminFind);
 const b=(v,l,t)=>'<button data-adm="'+esc(v)+'"'+(t?' title="'+esc(t)+'"':'')+'>'+esc(l)+'</button>';
 const go=r=>r.x?'<button data-do="gotoplace" data-value="'+esc(r.x+'|'+r.y+'|'+r.z)+'" title="Go to\nCentre the camera there.">Go to</button>':'';
 if(A.view==='quests'){const L=arr(P.quests).filter(q=>f([q.title,q.maker,q.house,q.text,q.goal].join(' ')));
  box.innerHTML=L.length?L.map(q=>{const live=q.state==='open'||q.state==='closing';
   return '<div class="qrow"><b>'+esc(q.title)+(q.hidden?' (words hidden)':'')+'</b><small>'+esc([q.maker+(q.house&&q.house!==q.maker?' ('+q.house+')':''),live?q.left:q.state,q.goal,'Reward: '+(q.reward||'none'),q.takers+' took it',q.reports?q.reports+' open report'+(q.reports>1?'s':'')+' on the maker':'',q.postban?'posting stopped, '+q.postban:''].filter(Boolean).join(' · '))+'</small>'+(q.text?'<small>“'+esc(q.text)+'”</small>':'')
    +'<div class="acts"><button data-do="quest" data-value="'+esc('open|'+q.id)+'">Open</button>'+go(q)
    +(live?b('qdown|'+q.id,'Take down','Take it down\nIts reward goes back to its maker, handed-in goods back to the takers. The reason box goes in the log.'):'')
    +b('qhide|'+q.id,q.hidden?'Show words':'Hide words',q.hidden?'Show its words again':'Hide the words\nIts maker’s title and words are blanked for everyone.')
    +(q.postban?b('postban|'+q.maker+'|0','Let post'):b('postban|'+q.maker+'|1','Stop posting 1 day')+b('postban|'+q.maker+'|7','7 days')+(me>=2?b('postban|'+q.maker+'|-1','Until lifted'):''))+'</div></div>'}).join('')
   :'<p class="hint">No notices'+(adminFind?' match':'')+'.</p>';return}
 if(A.view==='players'){const L=arr(P.players).filter(p=>f([p.key,p.house,p.race].join(' ')));
  box.innerHTML=L.length?L.map(p=>{const may=admRank(p.level)<me;
   return '<div class="qrow"><b>'+(p.online?'<span class="on">●</span> ':'')+esc(p.key)+(p.house&&p.house!==p.key?' ('+esc(p.house)+')':'')+'</b><small>'+esc([p.level?(p.level==='owner'?'Owner':p.level==='admin'?'Admin':'Moderator'):'',p.race,p.units!=null?p.units+' people':'',p.online?'online':'away',p.discord?'Discord':'',p.muted?'muted, '+p.muted:'',p.postban?'posting stopped, '+p.postban:'',p.banned?'banned, '+p.banned:'',p.reports?p.reports+' open report'+(p.reports>1?'s':''):''].filter(Boolean).join(' · '))+'</small>'
    +'<div class="acts">'+go(p)+(p.online?b('msg|'+p.key,'Message','Message\nSends what is in the reason box, to them only.'):'')
    +(may?(p.muted?b('mute|'+p.key+'|0','Unmute'):b('mute|'+p.key+'|1','Mute 1 hour','Mute\nNo chat and no notices.')+b('mute|'+p.key+'|24','1 day')+b('mute|'+p.key+'|168','7 days')+(me>=2?b('mute|'+p.key+'|-1','Until lifted'):''))
     +(p.online?b('kick|'+p.key,'Kick','Kick\nDisconnects them now; they can come back.'):'')
     +(p.banned?b('unban|'+p.key,'Unban','Unban\nThey may come back; their old people stay wanderers, so they start over.'):b('ban|'+p.key+'|1','Ban 1 day','Ban\nTheir people become wanderers on the map, and they can\u2019t come back until it ends. The reason box is shown to them.')+b('ban|'+p.key+'|7','7 days')+(me>=2?b('ban|'+p.key+'|-1','For good'):''))
     +(p.postban?b('postban|'+p.key+'|0','Let post'):b('postban|'+p.key+'|1','Stop posting 1 day')+b('postban|'+p.key+'|7','7 days'))
     +(me>=3?(p.level!=='mod'?b('level|'+p.key+'|mod','Make Moderator'):'')+(p.level!=='admin'?b('level|'+p.key+'|admin','Make Admin'):'')+(p.level==='mod'||p.level==='admin'?b('level|'+p.key+'|none','Remove from staff'):''):''):'')+'</div></div>'}).join('')
   :'<p class="hint">No players'+(adminFind?' match':'')+'.</p>';return}
 if(A.view==='reports'){const R=P.reasons||{},L=arr(P.reports).filter(r=>f([r.target,r.by,r.byHouse,r.note,JSON.stringify(r.copy||{})].join(' ')));
  box.innerHTML=L.length?L.map(r=>{const c=r.copy||{};const what=r.kind==='quest'?'Notice “'+(c.title||'')+'” by '+(c.house||r.target):'Player '+r.target+(c.house&&c.house!==r.target?' ('+c.house+')':'')+(c.unit?', by '+c.unit:'');
   return '<div class="qrow'+(r.state==='open'?' open':'')+'"><b>'+esc((R[r.reason]||r.reason)+': '+what)+'</b><small>'+esc(['From '+r.by+(r.byHouse&&r.byHouse!==r.by?' ('+r.byHouse+')':''),r.at,r.state==='open'?'open':'closed by '+r.closedBy+(r.closeNote?': '+r.closeNote:'')].join(' · '))+'</small>'
    +(r.note?'<small>Their note: “'+esc(r.note)+'”</small>':'')+(c.text?'<small>The notice said: “'+esc(c.text)+'”</small>':'')+(c.reward?'<small>Reward: '+esc(c.reward)+'</small>':'')
    +'<div class="acts">'+(r.state==='open'?b('rclose|'+r.id,'Close','Close it\nThe reason box goes in as a note.'):'')+'<button data-admlook="'+esc((r.kind==='quest'?'quests':'players')+'|'+r.target)+'" title="Look\nOpens '+(r.kind==='quest'?'Quests':'Players')+' searched for them.">Look</button>'+(c.x?go(c):'')+'</div></div>'}).join('')
   :'<p class="hint">No reports'+(adminFind?' match':'')+'.</p>';return}
 if(A.view==='bugs'){const L=arr(P.bugs).filter(g=>f([g.id,g.text,g.doing,g.by,g.house,g.where,BUG_KIND[g.kind]||''].join(' ')));   // Bugs.dm: reports and errors, newest first
  box.innerHTML='<p class="hint">Confirm only a real bug: it then goes to Claude’s file to be fixed, its players’ words marked untrusted. Fixed tells the player who reported it.</p>'
   +(L.length?L.map(g=>{const err=g.type==='error';
    const head=err?(g.src==='server'?'Server error':'Page error')+' ×'+g.count+(g.players?' · '+g.players+' player'+(g.players>1?'s':''):''):(BUG_KIND[g.kind]||'Bug')+' · '+g.by;
    const meta=[BUG_STATE[g.state]||g.state,g.back?'came back after a fix':'',err?g.where:[g.race,g.house&&g.house!==g.by?g.house:''].filter(Boolean).join(', '),g.build?'build '+g.build:'',err?(g.last?'last '+g.last:'first '+g.at):g.at,g.exported?'in Claude’s file':'',g.state!=='new'&&g.staff?'by '+g.staff:'',g.note?'note: '+g.note:''].filter(Boolean).join(' · ');
    return '<div class="qrow'+(g.state==='new'?' open':'')+'"><b>'+esc(head)+'</b><small>'+esc(meta)+'</small><small class="bugtext">'+esc(g.text)+'</small>'+(g.doing?'<small class="bugtext">Doing: '+esc(g.doing)+'</small>':'')+(g.details?bugDetails(g.details):'')
     +'<div class="acts">'+go(g)+b('bugopen|'+g.id,g.details?'Hide details':'Details')
     +(g.state==='new'?b('bugset|'+g.id+'|seen','Seen'):'')
     +(me>=2&&g.state!=='confirmed'&&g.state!=='fixed'?b('bugset|'+g.id+'|confirmed','Confirm','Confirm it\nA real bug: it goes to Claude’s file to be fixed (its players’ words marked untrusted). The reason box is its note.'):'')
     +(me>=2&&g.state!=='fixed'?b('bugset|'+g.id+'|fixed','Fixed','Mark it fixed\nThe player who reported it is told. An error row opens again if it comes back in a later build.'):'')
     +(g.state!=='notbug'?b('bugset|'+g.id+'|notbug','Not a bug'):'')+(g.state!=='dup'?b('bugset|'+g.id+'|dup','Duplicate'):'')
     +(g.state!=='new'?b('bugset|'+g.id+'|new','Reopen'):'')+'</div></div>'}).join('')
   :'<p class="hint">'+(adminFind?'No bugs match.':'No bugs reported.')+'</p>');return}
 if(A.view==='words'){const L=arr(P.words).slice().sort().filter(f);   // the word list (Moderation.dm, A4): Admins add and remove
  box.innerHTML='<p class="hint">Listed words come out as stars in chat, unit say, emotes, messages, notices, house names and unit names: a whole word in any case, or every word starting with it when it ends in *. '+arr(P.words).length+' of '+(P.max||300)+'.</p>'
   +(me>=2?'<div class="adm-word"><input id="adminWord" maxlength="31" placeholder="A word, or a start of words with *" aria-label="Word"><button data-admword="1">Add</button></div>':'<p class="hint">Only an Admin changes the list.</p>')
   +(L.length?L.map(w=>'<div class="qrow"><b>'+esc(w)+'</b>'+(me>=2?'<div class="acts">'+b('worddel|'+w,'Take off','Take it off the list\nThe reason box goes in the log.')+'</div>':'')+'</div>').join(''):'<p class="hint">'+(adminFind?'No words match.':'No words on the list.')+'</p>');return}
 box.innerHTML=arr(P.log).filter(f).map(l=>'<div class="admlog">'+esc(l)+'</div>').join('')||'<p class="hint">Nothing in the log yet.</p>'}
document.addEventListener('click',e=>{const b=e.target.closest('#page-admin [data-admword]');if(!b)return;const i=$('adminWord'),w=$('adminWhy'),v=i?i.value.trim().replace(/\|/g,''):'';if(!v)return;send('admin','wordadd|'+v+'|'+(w?w.value.trim().replace(/\|/g,'/'):''));i.value=''});document.addEventListener('keydown',e=>{if(e.key==='Enter'&&e.target.id==='adminWord'){e.preventDefault();const b=document.querySelector('#page-admin [data-admword]');if(b)b.click()}});
document.addEventListener('click',e=>{const b=e.target.closest('#page-admin [data-adm]');if(b){const w=$('adminWhy');send('admin',b.dataset.adm+'|'+(w?w.value.trim().replace(/\|/g,'/'):''));return}
 const v=e.target.closest('#page-admin [data-admview]');if(v){adminKey='';send('admin','view|'+v.dataset.admview);return}
 const l=e.target.closest('#page-admin [data-admlook]');if(l){const [view,who]=l.dataset.admlook.split('|');adminFind=String(who||'').toLowerCase();const i=$('adminFind');if(i)i.value=who||'';adminKey='';send('admin','view|'+view)}});
document.addEventListener('input',e=>{if(e.target&&e.target.id==='adminFind'){adminFind=e.target.value.trim().toLowerCase();adminKey='';if(model)renderAdmin(model)}});
// a Report button (data-qrep="quest|<id>" or "unit|<ref>") opens the reasons under it; each reason is one send
document.addEventListener('click',e=>{const b=e.target.closest('[data-qrep]');if(!b)return;const host=b.closest('.qc-foot,.hfnear')||b.parentElement;let row=host.nextElementSibling;
 if(row&&row.classList.contains('qrep-row')){row.remove();return}
 row=document.createElement('div');row.className='qrep-row';row.innerHTML='<span>Report for:</span>'+REPORT_REASONS.map(r=>'<button data-do="report" data-value="'+esc(b.dataset.qrep+'|'+r[0])+'">'+esc(r[1])+'</button>').join('');host.after(row)});
// a banned player's page (Moderation.dm RmModBanShow): the reason and until when, over everything, before they go
/* a guest's village kept by this browser (Guests.dm RmGuestBrowser; the owner, 11-01: "keep there stuff in guest mode save on browser", then "just do guest and play and save on browser"): a secret made once (32 hex) and kept in this browser's storage, sent once a page load when the model says this is a guest, '' with no storage (a guest as before); the server holds a guest's race picker for it a moment. Kept, the guest bar (029) says so. Run from renderAdmin, after the guest bar, each model. */
let rmGbSent=false;function rmGuestBrowser(m){const G=m&&m.guest;if(!G)return;if(!rmGbSent){rmGbSent=true;let c='';try{c=localStorage.getItem('rmGuestBrowser')||'';if(!/^[0-9a-f]{32}$/.test(c)){const r=new Uint8Array(16);crypto.getRandomValues(r);c=Array.from(r,x=>x.toString(16).padStart(2,'0')).join('');localStorage.setItem('rmGuestBrowser',c);if(localStorage.getItem('rmGuestBrowser')!==c)c=''}}catch(e){c=''}send('guestbrowser',c)}
 const gb=$('guestbar');if(!G.kept||!gb||gb.hidden)return;const sp=gb.querySelector('span'),t='Saved in this browser; clearing its data loses it. Sign in with Discord (optional) to play it on any device.';if(sp&&sp.textContent!==t)sp.textContent=t;const sb=gb.querySelector('.gsign');if(sb&&sb.textContent!=='Sign in (optional)')sb.textContent='Sign in (optional)'}
window.rmGuestGone=()=>{try{bootCoverOff()}catch(_){}const g=($('guestbar')||{})._g,d=document.createElement('div');d.id='rmguestgone';d.setAttribute('role','alertdialog');d.style.cssText='position:fixed;inset:0;z-index:100000;display:grid;place-items:center;background:rgba(12,10,8,.94);color:#efe6cc;font:17px HudText,Georgia,serif';const b='display:inline-block;margin:14px 6px 0;padding:7px 18px;border:1px solid #b08a3e;background:#2e271c;color:#f3e9d2;text-decoration:none;font:15px HudText,Georgia,serif';const su=g&&g.signin?g.signin+(g.signin.indexOf('?')>=0?'&':'?')+'return='+encodeURIComponent(location.origin+'/join'):'';d.innerHTML='<div style="max-width:560px;padding:22px 26px;border:1px solid #b08a3e;background:#1d1a14;text-align:center"><div style="font:22px HudCaps,Herculanum,HudHead,Georgia,serif;letter-spacing:.06em;color:#f2d27a;margin-bottom:10px">'+(g&&g.kept?'Your village is saved':'Your village is gone')+'</div><div>'+(g&&g.kept?'Your village is saved in this browser: come back from this browser to carry on. Clearing this browser\'s data loses it.':'Guests can\'t keep what they build: your people have turned to stone or died, and your village is gone. Sign in with Discord next time and your village stays.')+'</div><div><a href="/" style="'+b+'">Play again</a>'+(su?'<a href="'+esc(su)+'" style="'+b+'">Sign in with Discord'+(g&&g.kept?' (optional)':'')+'</a>':'')+'</div></div>';document.body.append(d)};   /* a guest who chose Leave (Guests.dm RmGuestLeaveAsk): a goodbye card over everything, the web link's disconnect bar too */ window.rmBanned=t=>{try{bootCoverOff()}catch(_){}const d=document.createElement('div');d.id='rmbanned';d.setAttribute('role','alertdialog');d.style.cssText='position:fixed;inset:0;z-index:99;display:grid;place-items:center;background:rgba(12,10,8,.92);color:#efe6cc;font:17px HudText,Georgia,serif';d.innerHTML='<div style="max-width:560px;padding:22px 26px;border:1px solid #b08a3e;background:#1d1a14;text-align:center"><div style="font:22px HudCaps,Herculanum,HudHead,Georgia,serif;letter-spacing:.06em;color:#f2d27a;margin-bottom:10px">Banned</div><div>'+esc(decodeURIComponent(String(t).replace(/\+/g,' ')))+'</div></div>';document.body.append(d)};
/* the player cap turned them away (Moderation.dm RmModFullGate): the same card, saying so, with a way back in */
window.rmFull=t=>{try{bootCoverOff()}catch(_){}const d=document.createElement('div');d.id='rmfull';d.setAttribute('role','alertdialog');d.style.cssText='position:fixed;inset:0;z-index:99;display:grid;place-items:center;background:rgba(12,10,8,.92);color:#efe6cc;font:17px HudText,Georgia,serif';d.innerHTML='<div style="max-width:560px;padding:22px 26px;border:1px solid #b08a3e;background:#1d1a14;text-align:center"><div style="font:22px HudCaps,Herculanum,HudHead,Georgia,serif;letter-spacing:.06em;color:#f2d27a;margin-bottom:10px">The world is full</div><div>'+esc(decodeURIComponent(String(t).replace(/\+/g,' ')))+'</div><div><a href="/" style="display:inline-block;margin:14px 6px 0;padding:7px 18px;border:1px solid #b08a3e;background:#2e271c;color:#f3e9d2;text-decoration:none;font:15px HudText,Georgia,serif">Try again</a></div></div>';document.body.append(d)};
document.addEventListener('click',e=>{const b=e.target.closest('.qrep-row [data-do=report]');if(b)setTimeout(()=>{const r=b.closest('.qrep-row');if(r)r.remove()},50)});

