// ===== Layered HUD over the map =====
const overlayHost=!!(window.webkit&&window.webkit.messageHandlers&&window.webkit.messageHandlers.dmOverlay)||/[?&]overlay\b/.test(location.search)||!!window.__dmWeb;if(!overlayHost)bootCoverOff();/* a browser (the engine's web link sets __dmWeb first) is always the HUD over the map, ?overlay or not: the public link has none (10-31) */
if(overlayHost){document.documentElement.classList.add('overlay');document.body.classList.add('overlay');const c=$('cameraOverview');if(c){c.open=true;/* the overlay hides the card's fold arrow, so a click on the date plate (or Space while it has focus) must not fold the minimap away for good */c.addEventListener('toggle',()=>{if(!c.open)c.open=true});const su=c.querySelector('summary');if(su){su.tabIndex=-1;su.addEventListener('mousedown',e=>e.preventDefault());su.addEventListener('click',e=>e.preventDefault())}}}
let lastRegions='';
function postRegions(){if(!overlayHost)return;const r=[];if(document.body.classList.contains('v3d'))r.push([0,0,innerWidth,innerHeight]);const kc=hudKC()/hudK(),add=el=>{if(!el)return;const b=el.getBoundingClientRect();if(b.width>0&&b.height>0&&getComputedStyle(el).display!=='none'&&getComputedStyle(el).visibility!=='hidden')r.push([Math.floor(b.left*kc),Math.floor(b.top*kc),Math.ceil(b.width*kc),Math.ceil(b.height*kc)])};
 if(document.querySelector('dialog[open]'))r.push([0,0,innerWidth,innerHeight]);
 ['header','nav','.world','.taskmode','#topbar','#roster','#heroframe','main','#attack','#attackx','#foodalert','#menu3d','#nearcard','#usecard','#askcard','#startcard','#goaltrack','#loghist','#worldmap','#daycard','#awaycard','#settings','#lockbar','#questcard','#questtrack','#bugform','#chatbox'].forEach(sel=>add(document.querySelector(sel)));
 const key=JSON.stringify(r);if(key===lastRegions)return;lastRegions=key;try{window.webkit.messageHandlers.dmOverlay.postMessage(r)}catch(e){}}
let regionQueued=false;function queueRegions(){if(typeof hcUnitsPage==='function')hcUnitsPage();if(regionQueued)return;regionQueued=true;requestAnimationFrame(()=>{regionQueued=false;postRegions()})}
if(overlayHost){new MutationObserver(queueRegions).observe(document.body,{subtree:true,childList:true,attributes:true,attributeFilter:['class','hidden','open','style']});addEventListener('resize',queueRegions);document.addEventListener('toggle',queueRegions,true);setInterval(postRegions,1000)}
document.addEventListener('click',e=>{if(!overlayHost)return;if(e.target.closest('#panelClose')){document.body.classList.remove('panel-open');queueRegions();return}
 const t=e.target.closest('button[data-do=tab]');if(t){if(document.body.classList.contains('panel-open')&&t.dataset.value===currentTab&&t.closest('nav'))document.body.classList.remove('panel-open');else document.body.classList.add('panel-open');queueRegions()}},true);
let lastToast='';
// "Fall · day 682", plus the time of day when it isn't plain day (the sun or moon icon shows that too).
function seasonLine(m){const p=String(m.border?.period||m.day||'');return m.season+(m.date==null?'':' · day '+m.date)+(p&&!/^day$/i.test(p)?' · '+p.toLowerCase():'')}
// Your own units' names carry your "{tag} " prefix; the HUD leaves it out (other players' and NPC tags stay).
function ownTag(){const n=String(arr(model&&model.units)[0]?.name||''),m=/^\{[^}]*\}\s*/.exec(n);return m?m[0]:''}
function ownName(n){const t=ownTag();n=String(n||'');return t&&n.startsWith(t)?n.slice(t.length):n}
let recentToasts=[];
// The tips box sits bottom right; in a narrow window the command bar reaches under it and hid its left half (11-01: a
// newcomer's first tip read "...people need Woodcutting 15 to"): then it goes just above the bar.
// The bar itself: .commandbar is display:contents (no box of its own). The chat box sits in the same corner.
function placeToasts(){const bar=document.querySelector('.commandbar .taskmode');if(!bar)return;const b=bar.getBoundingClientRect(),k=hudK();
 for(const [id,w] of [['toasts',268],['chatbox',340]]){const t=$(id);if(!t)continue;const left=innerWidth-6*k-(t.getBoundingClientRect().width||w*k);   // an empty box has no width: its usual one
  const want=b.width>0&&b.right>left&&b.top<innerHeight?Math.round((innerHeight-b.top)/k+6)+'px':'';if(t.style.bottom!==want)t.style.bottom=want}}
// --- The chat box (ChatBox.dm, the owner 11-01: "a world chat box where the log is like warcraft people can toggle
// between", then "we need local chat and world chat"): the corner's lines with tabs. All: everything; Chat: World,
// Local and Kingdom; Log: the game's news, tips and fights (logHist, the same history as Village > Log > Messages). Enter
// opens the line (World, Local or Kingdom; /w, /l or /s, /k switch), Enter sends, Escape closes. Left alone it fades to its last 20 s of lines, as the corner did.
let cbTab='all',cbChan='world',cbDirty=false,cbActiveAt=0;
const CB_CHAT=['world','local','kingdom'],CB_NAME={world:'World',local:'Local',kingdom:'Kingdom'},CB_OLD=20000,CB_IDLE=12000;
function cbShow(e){return cbTab==='all'||(cbTab==='chat'?CB_CHAT.includes(e.k):!CB_CHAT.includes(e.k))}
function cbRender(){cbDirty=false;const box=$('cbLines');if(!box||typeof logHist==='undefined')return;const atEnd=box.scrollHeight-box.scrollTop-box.clientHeight<24,now=Date.now();
 box.innerHTML=logHist.filter(cbShow).slice(-120).map(e=>{const ch=CB_CHAT.includes(e.k),pre=ch?'['+CB_NAME[e.k]+'] '+(e.who?e.who+': ':''):'';
  return '<div class="cbl k-'+esc(e.k)+(now-e.at>CB_OLD?' old':'')+'" data-at="'+e.at+'">'+(pre?'<b>'+esc(pre)+'</b>':'')+esc(e.t)+'</div>'}).join('');
 if(atEnd||$('chatbox').classList.contains('idle'))box.scrollTop=box.scrollHeight}
function cbQueue(){cbActiveAt=Date.now();cbIdle();if(cbDirty)return;cbDirty=true;requestAnimationFrame(cbRender)}
function cbIdle(){const c=$('chatbox');if(!c)return;const idle=!c.matches(':hover')&&document.activeElement!==$('cbText')&&Date.now()-cbActiveAt>CB_IDLE;if(c.classList.contains('idle')!==idle){c.classList.toggle('idle',idle);if(idle){const b=$('cbLines');if(b)b.scrollTop=b.scrollHeight}}
 const now=Date.now();c.querySelectorAll('.cbl:not(.old)').forEach(l=>{if(now-Number(l.dataset.at)>CB_OLD)l.classList.add('old')})}
setInterval(cbIdle,2000);
// A player's World or Kingdom line (ChatBox.dm RmChatSend): kept in the history as itself, never read as a fight line.
window.rmChatMsg=s=>{let d;try{d=JSON.parse(decodeURIComponent(String(s).replace(/\+/g,' ')))}catch(_){return}if(!d||!CB_CHAT.includes(d.ch)||typeof logHist==='undefined')return;
 logHist.push({t:String(d.text||''),k:d.ch,who:String(d.who||''),at:Date.now()});if(typeof logSerial!=='undefined')logSerial++;if(logHist.length>400)logHist.shift();hcMsgView()};
function cbSetChan(c){cbChan=c;const b=$('cbChan');if(b){b.textContent=CB_NAME[c];b.className=c}}
document.addEventListener('click',e=>{const t=e.target.closest('#chatbox [data-cbtab]');if(t){cbTab=t.dataset.cbtab;document.querySelectorAll('#chatbox [data-cbtab]').forEach(b=>b.setAttribute('aria-selected',String(b===t)));cbQueue();return}
 if(e.target.closest('#cbChan'))cbSetChan(CB_CHAT[(CB_CHAT.indexOf(cbChan)+1)%CB_CHAT.length])});
document.addEventListener('mouseover',e=>{if(e.target.closest&&e.target.closest('#chatbox'))cbQueue()});
document.addEventListener('keydown',e=>{const box=$('chatbox');if(!box||!overlayHost)return;const inp=$('cbText');
 if(e.target===inp){if(e.key==='Escape'){e.preventDefault();inp.value='';inp.blur();cbQueue();return}
  if(e.key!=='Enter'||e.isComposing)return;e.preventDefault();let v=inp.value.trim();const m=/^\/(w|world|l|local|s|say|k|kingdom)\b\s*/i.exec(v);if(m){cbSetChan(/^k/i.test(m[1])?'kingdom':/^[ls]/i.test(m[1])?'local':'world');v=v.slice(m[0].length)}
  if(v)send('chat',cbChan+'|'+v.slice(0,300));inp.value='';inp.blur();cbQueue();return}
 if(e.key!=='Enter'||e.altKey||e.ctrlKey||e.metaKey||e.isComposing)return;
 if(e.target.closest&&e.target.closest('input,textarea,select,button,[contenteditable]'))return;
 if(document.querySelector('#askcard:not([hidden]),#bugform,dialog[open]'))return;   // a card or form open: its own Enter
 e.preventDefault();cbQueue();inp.focus()});
addEventListener('resize',()=>{try{placeToasts()}catch(_){}});
function toast(msg){if(!overlayHost||!msg)return;requestAnimationFrame(()=>{try{placeToasts()}catch(_){}});msg=tidyLine(msg);if(!msg||msg===lastToast)return;// compare after stripping the player's tag: the notice comes with every HUD update, and with a tag it never matched, so it repeated every tick
if(/^(Started|Added): |: Arrived$/.test(String(msg)))return;// routine order news: the Company list already shows it
// the same news within half a minute is one line, with a count, not a column of repeats
{const now=Date.now();recentToasts=recentToasts.filter(r=>now-r.at<30000);const r=recentToasts.find(r=>r.msg===msg);if(r&&r.el&&r.el.isConnected){r.n++;r.at=now;text(r.el,msg+' ×'+r.n);r.el.classList.remove('fade');const e=logHist[logHist.length-1];if(e&&e.t.replace(/ ×\d+$/,'')===msg){e.t=msg+' ×'+r.n;hcMsgView()}return}}
lastToast=msg;logPush(msg,'note');const t=document.createElement('div');t.className='toast';text(t,msg);$('toasts').append(t);recentToasts.push({msg,n:1,at:Date.now(),el:t});while($('toasts').childElementCount>6)$('toasts').firstChild.remove();setTimeout(()=>t.classList.add('fade'),10000);setTimeout(()=>{t.remove();queueRegions()},10700)}
function heroBar(cls,label,v,max){return '<div class="bar '+cls+'"><em class="trl" style="width:'+pct(v,max)+'%"></em><span style="width:'+pct(v,max)+'%"></span><i>'+barLbl(label,v,max)+'</i></div>'}
// A bar's label in two parts, the name left and the numbers right (hud-rework 10-27, owner: "build them"); the text
// still reads "Health 212 / 350", and a live update only rewrites the numbers.
function barLbl(l,v,m){return '<b>'+esc(l)+'</b> <em>'+esc(v+' / '+m)+'</em>'}
function barSet(it,l,v,m){if(!it)return;const e=it.querySelector('em');if(e)text(e,v+' / '+m);else it.innerHTML=barLbl(l,v,m)}
function esc(v){return String(v==null?'':v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
let heroKey='';
// The Company list sits under the minimap panel; measured after layout, so it never slides under it.
// Click "Company" to fold the list to its header (remembered); the Village button's badge still shows idle units.
document.addEventListener('click',e=>{const h=e.target.closest('#roster>h4');if(!h)return;const r=$('roster'),on=!r.classList.contains('folded');r.classList.toggle('folded',on);try{localStorage.setItem('rm-rosterfold',on?'1':'')}catch(_){}queueRegions()});
try{if(localStorage.getItem('rm-rosterfold'))document.addEventListener('DOMContentLoaded',()=>$('roster')?.classList.add('folded'))}catch(_){}
function placeRoster(){const w=document.querySelector('.world'),r=$('roster');if(!w||!r)return;
 try{hcRosterWin()}catch(e){console.error(e)}   // the Company list's rows on screen (hud-craft)
 // the menu runs across the top right; the minimap panel sits just under it
 const nv=document.querySelector('nav');if(nv&&document.body.classList.contains('overlay')){const wt=Math.round(nv.getBoundingClientRect().bottom/hudK()+16)+'px';if(w.style.top!==wt){w.style.top=wt;queueRegions()}}
 // The top bar never runs under the menu (the owner, 11-01: "i liked the orignl look but it was overlapping that is all"):
 // its own size and place as before; only its widest stops 16 px short of the menu, which grows with its buttons (Admin,
 // badges) past the fixed room the style leaves it.
 {const tb=$('topbar');if(tb&&nv&&document.body.classList.contains('overlay')){const k=hudK(),n=nv.getBoundingClientRect(),t=tb.getBoundingClientRect();
  const ww='min(calc(var(--sw,100vw) - 534px),'+Math.max(200,Math.round((n.left-t.left)/k-16))+'px)';
  if(tb.dataset.mw!==ww){tb.dataset.mw=ww;tb.style.setProperty('max-width',ww,'important');queueRegions()}   // the browser rewrites the value as stored
  const g=$('goaltrack');
  // the arrival story's note sits under the goal tracker; every other card keeps its own place (centred)
  const ac=$('askcard');if(ac){const gb=g&&!g.hidden?g.getBoundingClientRect():tb.getBoundingClientRect(),st=ac.classList.contains('story')?Math.round(gb.bottom/k+16)+'px':'';if(ac.style.top!==st)ac.style.top=st}}}
 // 16: the frames reach 6 px past each box, so stacked panels keep a 4 px gap instead of overlapping (hud-craft)
 const t=Math.round(w.getBoundingClientRect().bottom/hudK()+16),top=t+'px';if(r.style.top!==top){r.style.top=top;queueRegions()}
 // it ends above the message log's corner (about 170 px) and scrolls when the company is long
 const mh=Math.max(60,innerHeight/(+document.documentElement.style.zoom||1)-t-144)+'px';if(r.style.maxHeight!==mh){r.style.maxHeight=mh;queueRegions()}}
addEventListener('resize',()=>requestAnimationFrame(placeRoster));
// HUD material follows the selected unit's race (or the first unit's).
const RACE_MATS={stone:['dwarf', 'gargoyle', 'stone', 'sand'],timber:['orc', 'goblin', 'kobold', 'ratman', 'gremlin'],bone:['skeleton', 'zombie', 'werewolf', 'devourer', 'fleshcrawler', 'unholy', 'lich'],kingdom:['human'],moon:['elf', 'svartalfar', 'illithid'],swamp:['lizard', 'frog', 'water', 'plant', 'towercap'],blood:['vampire', 'demon', 'blooded'],scale:['dragon'],chitin:['spider', 'queen', 'warrior', 'worker', 'egg']};
function matFor(race){const r=String(race||'').toLowerCase();for(const k in RACE_MATS)if(RACE_MATS[k].some(w=>r.includes(w)))return k;return 'kingdom'}
function hudIcons(m){const I=m.icons||{};const dn=document.querySelector('#topbar .datebox .ic');if(dn){dn.dataset.icon=/night/i.test(m.border?.period||m.day||'')?'daynight-moon':'daynight-sun';if(dn.parentElement.dataset.dn!==dn.dataset.icon)dn.parentElement.dataset.dn=dn.dataset.icon}document.querySelectorAll('img[data-icon]').forEach(e=>{const s=I[e.dataset.icon];if(s&&e.getAttribute('src')!==s)e.src=s})}
// Unit card tabs (one unit): Overview (bag, orders, work boxes), Health (body parts, blood, conditions), Family, Interact (the original Interact menu), Combat (lethal, style, stance, special, levels), Skills, Spells.
const HERO_TABS=[['overview','Overview','Bag, orders and the work at hand'],['health','Health','Body parts, blood and conditions'],['family','Family','House, parents, partners, children and siblings'],['interact','Interact','Its own abilities: fly, rest, breathe fire, turn to mist, gem spells and its weapon’s power. For the creature beside it, use Interact (I) on the action bar.'],['combat','Combat','Lethal or non-lethal, combat style, stance, special move and combat levels'],['skills','Skills','Gathering, crafting and support skills, and its own abilities'],['spells','Spells','Weapon moves and magic'],['keeper','Keeper','Their job as a keeper: where they stand, the quests they offer, their words']];
let heroTab='overview';try{const t=localStorage.getItem('rm-hftab');if(HERO_TABS.some(x=>x[0]===t))heroTab=t}catch(_){}
function heroTabsHtml(){return '<div class="hftabs" role="tablist" aria-label="Unit card">'+HERO_TABS.map(([v,l,tip])=>'<button type="button" role="tab" data-hftab="'+v+'" aria-selected="'+(heroTab===v)+'" title="'+esc(l+'\n'+tip)+'">'+l+'</button>').join('')+'</div>'}
document.addEventListener('click',e=>{const f=e.target.closest('#heroframe [data-focus]');if(f&&f.dataset.focus)send('lineagefocus',f.dataset.focus)},true);
// The band card (several units selected) has its own tabs: Band, Orders, Combat.
const GROUP_TABS=[['band','Band','Who is selected; click a face to take just that unit'],['orders','Orders','Formation, patrol route, unload and take'],['combat','Combat','Lethal or non-lethal, combat style and stance for the whole band']];
let groupTab='band';try{const t=localStorage.getItem('rm-gftab');if(GROUP_TABS.some(x=>x[0]===t))groupTab=t}catch(_){}
document.addEventListener('click',e=>{const b=e.target.closest('#heroframe [data-hftab],#heroframe [data-gftab]');if(!b)return;const g=!!b.dataset.gftab,t=g?b.dataset.gftab:b.dataset.hftab;
 if(g)groupTab=t;else heroTab=t;try{localStorage.setItem(g?'rm-gftab':'rm-hftab',t)}catch(_){}const hf=$('heroframe');hf.dataset.tab=t;
 hf.querySelectorAll(g?'[data-gftab]':'[data-hftab]').forEach(x=>x.setAttribute('aria-selected',String((g?x.dataset.gftab:x.dataset.hftab)===t)));
 if(!g&&heroPanes.u&&hf.dataset.unitref===heroPanes.u.ref){heroPanes(hf,heroPanes.u);const tb=hf.querySelector('.hftabs');if(tb&&hf.lastElementChild!==tb)hf.append(tb)}   // the opened tab's pane, built now
 queueRegions()});
// A captive's section of its card (Captives.dm, capture-rope): bound (led or tied) or a slave, the rope and how strong it
// is, loyalty, how likely they are to break free and why, and Win over / Enslave / Release / Move them / Tie or Lead.
function capCardHtml(u){const C=u.captive;if(!C)return '';const r=esc(u.ref),bound=C.state==='bound',lv=Math.max(0,['none','low','some','high','very high'].indexOf(C.risk));
 const b=(v,l,tip,off)=>'<button class="hfab" data-do="captive" data-value="'+r+'|'+v+'"'+(off?' disabled':'')+' title="'+esc(tip+(off?'\n'+off:''))+'">'+l+'</button>';
 let h='<div class="hfh">'+(bound?'Bound captive':'Slave')+'</div><div class="hfcap">';
 h+='<div class="caprow">'+(bound?(C.cage?'Shut in a <b>'+esc(String(C.cage).toLowerCase())+'</b>':C.inLine?'In a line, roped behind <b>'+esc(C.inLine)+'</b>':C.led?'Led on the rope by <b>'+esc(C.led)+'</b>':C.post?'Tied to a '+esc(C.postKind||'post'):'Tied up where they are'):'Hobbled · works for you, not of your house')+'</div>';
 if(bound&&C.behind)h+='<div class="caprow">'+C.behind+' roped behind them</div>';
 if(C.rope)h+='<div class="caprow" title="'+esc((bound?'Bound with ':'Hobbled with ')+C.rope+'\nStrength '+C.ropePower+' of 100: a stronger rope is harder to break.')+'">'+(bound?'Rope':'Hobble')+' <b>'+esc(C.rope)+'</b><em>'+esc(C.ropeWord)+'</em></div>';
 h+='<div class="bar caploy" title="'+esc('Loyalty '+C.loyalty+'%\n'+(bound?'Win them over: at 100% they join your house. The more loyal, the less they try the rope.':'Fed and unhurt, a slave grows loyal slowly. Win them over to free them into your house; armed, a loyal slave (60%) fights for you.'))+'"><span style="width:'+Math.max(0,Math.min(100,C.loyalty))+'%"></span><i>Loyalty '+C.loyalty+'%</i></div>';
 if(bound)h+='<div class="caprisk r'+lv+'" title="'+esc('May break free: '+C.risk+(C.odds?' ('+C.odds+'% a try, about every 30 s)':'')+'\n'+arr(C.why).join('\n')+'\nGuards close by, a better rope, a post and loyalty all hold them.')+'"><b class="hcg hcg-chain">⛓</b> May break free: <strong>'+esc(C.risk)+'</strong></div>';
 if(C.talker)h+='<p class="hfnote">'+esc(C.talker)+' is winning them over.</p>';
 if(!bound&&C.armed)h+='<p class="hfnote">'+(C.fights?'Armed and loyal: fights for you.':C.loyalty<40?'Armed and resentful: may turn on you.':'Armed, but won’t fight for you yet (loyalty 60%).')+'</p>';
 h+='<div class="hfspells">'+b('win','<b class="hcg hcg-heart">♥</b> Win over','Win over\nThe best talker of yours nearby sits with them: talk, and food when they are hungry (carry some). At 100% loyalty they join your house.',C.out?'Out cold: wait until they come to.':'')+
  (bound?b('enslave','Enslave','Enslave\nThey work for you (jobs, work orders) in a hobble, a bit slower, but never fight or defend and aren’t of your house. No more tries at the rope; many slaves with few guards may rise.'):'')+
  b('release','Release','Release\nThe rope comes off and they go home.')+
  (bound&&!C.cage?b('move','Move them','Move them\nWith them selected, click the ground: one of yours leads them there and ties them up.')+(C.led?b('tie','Tie here','Tie here\nTie them up where they are (beside a post or wall they hold better).'):b('lead','Lead','Lead\nThe nearest of yours takes the rope; they follow wherever that one goes.'))+
   b('line','Add to a line','Add to a line\nRope them behind the nearest other bound captive, one after the other. A leader holds two lines side by side; right-click a captive or one of yours to choose.',C.canLine?'':'No other bound captive within 8 tiles.')+
   b('post','Tie to something','Tie to something\nOne of yours takes them to the nearest thing to tie them to (a tree, a wall or rock, a post, furniture, a workshop, a stake) and ties them to it: they hold better there. Or right-click the thing itself: Tie \u2026 to this.',C.canPost?'':'Nothing to tie them to within 10 tiles: Stake here.')+
   b('stake','Stake here','Stake here\nOne of yours drives a stake into the ground beside them and ties them to it: they hold as well as at a tree. A stake carried is used, else one is cut from a log of wood.',C.canStake?'':'None of yours near them has a stake or a log of wood to cut one from.')+
   b('cage','Put in a cage','Put in a cage\nInto the nearest empty cage (one your people carry is set down first). The rope comes off them, back to the one who puts them in. Caged, they can\u2019t break free; a cage with someone in it can\u2019t be carried.',C.canCage?'':'No empty cage within 8 tiles: cages are made at a Carpentry, Bone crafting or a Forge.'):'')+
  (bound&&C.cage?b('uncage','Take out','Take out of the cage\nOne of yours with a rope lets them out and ties them up beside it.',C.canOut?'':'None of yours near the cage has a rope to tie them as they come out.'):'')+'</div>';
 if(C.from)h+='<p class="hfnote">Taken from '+esc(C.from)+'.</p>';
 return h+'</div>'}
// The right-click card's actions for one of your captives (Captives.dm).
function capMenuActs(o,acts){const cu=arr(model&&model.units).find(u=>u.ref&&u.ref===o.ref);if(!cu)return;
 /* one bound captive selected, another of yours right-clicked: on its rope (a captive: behind its line) */
 const sel1=arr(model&&model.units).filter(u=>u.selected);const sc=sel1.length===1&&sel1[0].captive&&sel1[0].captive.state==='bound'&&!sel1[0].captive.cage&&sel1[0].ref!==cu.ref?sel1[0]:null;
 if(sc&&!(cu.captive&&cu.captive.state!=='bound')){const nm2=String(sc.name||'').replace(/^\{[^}]*\}\s*/,'');acts.splice(0,0,[cu.captive?'Rope '+nm2+' behind them':'Hand them '+nm2+'\u2019s rope','captive',sc.ref+'|attach|'+cu.ref,cu.captive?'In a line, one after the other.':'They lead '+nm2+' on the rope (two lines side by side at most).'])}
 if(!cu.captive)return;const r=cu.ref,bound=cu.captive.state==='bound';
 if(!cu.captive.out)acts.push(['Win over','captive',r+'|win','The best talker of yours nearby sits with them; at 100% loyalty ('+cu.captive.loyalty+'% now) they join your house.']);   /* not while out cold */
 if(bound)acts.push(['Enslave','captive',r+'|enslave','They work for you in a hobble, never fight, and aren’t of your house.']);
 acts.push(['Release','captive',r+'|release','The rope comes off and they go home.']);
 if(bound)acts.push(cu.captive.led?['Tie them here','captive',r+'|tie','Tie them up where they are.']:['Lead them','captive',r+'|lead','The nearest of yours takes the rope.']);
 if(bound&&!cu.captive.cage){acts.push(['Tie to something','captive',r+'|post','One of yours takes them to the nearest tree, wall, post or other thing and ties them to it.']);acts.push(['Stake them here','captive',r+'|stake','One of yours drives a stake into the ground beside them and ties them to it (a stake carried, or one cut from a log of wood).'])}}
// Only the open tab's pane is built; another tab's is built when it is clicked (hud-craft, 10-25).
function heroPanes(hf,u){if(heroPanes.ref!==u.ref){heroPanes.ref=u.ref;heroHealthView='hurt'}heroPanes.u=u;hf.classList.toggle('keeper',!!u.keeper);if(heroTab==='keeper'&&!u.keeper){heroTab='overview';hf.querySelectorAll('[data-hftab]').forEach(x=>x.setAttribute('aria-selected',String(x.dataset.hftab==='overview')))}   /* the Keeper tab only on a keeper (QuestKeepers.dm) */const on=n=>heroTab===n,S=u.skills||{},T=arr(S.tiles),D=u.defense||{},ab=arr(u.abilities),sp=u.special,r=esc(u.ref);
 const pane=(name,k,make)=>{let p=hf.querySelector('.hfpane[data-pane='+name+']');if(!p){p=document.createElement('div');p.className='hfpane';p.dataset.pane=name;hf.append(p)}if(p.dataset.k!==k){p.dataset.k=k;p.innerHTML=make()}};
 on('keeper')&&u.keeper&&pane('keeper',JSON.stringify([u.ref,u.keeper]),()=>keeperPaneHtml(u));   // a keeper's own tab (027 keeperPaneHtml)
 // a weapon skill at its Attack level (t.cap, CombatSkills.dm) is held there: no weapon skill goes above Attack
 const tile=t=>'<div'+(t.cap!=null?' data-cap="'+esc(t.cap)+'"':'')+' title="'+esc(t.label+' level '+t.level+'\n'+(t.xp||0).toLocaleString()+' XP'+(t.cap!=null?(t.banked>0?' (+'+t.banked.toLocaleString()+' kept)':'')+'\nHeld at Attack level '+t.cap+': train Attack to raise it':t.next!=null?' · '+Math.max(0,t.next-t.xp).toLocaleString()+' to level '+(t.level+1):''))+'"><span>'+esc(t.label.replace(/ crafting$/,''))+'</span><b>'+esc(t.level)+'</b><em style="width:'+Math.max(0,Math.min(100,t.progress))+'%"></em></div>';
 const tiles=(list,c)=>list.length?'<div class="hflv"'+(c?' style="--c:'+c+'"':'')+'>'+list.map(tile).join('')+'</div>':'';
 const row=(label,h,n)=>'<div class="hfrow"><span>'+label+'</span>'+(n?'<div style="--n:'+n+'">'+h+'</div>':h)+'</div>';
 const pick=(act,v,on,l,tip)=>'<button data-do="'+act+'" data-value="'+r+'|'+v+'" aria-pressed="'+on+'" title="'+esc(tip)+'">'+l+'</button>';
 const nm=n=>esc(String(n).replace(/\{[^}]*\}\s*/g,''));
 const abBtn=([menu,name],cls)=>'<button class="hfab'+cls+'" data-do="unitability" data-value="'+esc(u.ref+'|'+menu+'|'+name)+'" title="'+nm(name)+'">'+nm(name)+'</button>';
 const lv=g=>T.filter(t=>t.group===g).map(t=>[t.id,t.level,t.progress]);
 // Weapon moves and spells (WeaponSkills.dm): what its weapon class and its item give it, by how its skills are built.
 const mv=arr(u.moves).map(m=>Object.assign({},m,{wait:Math.ceil(m.wait||0)})),classMv=mv.filter(m=>!m.item&&!m.ninja),itemMv=mv.filter(m=>m.item),ninjaMv=mv.filter(m=>m.ninja),ck=u.chakra,wm=u.wmana;
 const mvRow=(m,cls)=>{const lock=!!m.lack,act=m.kind!=='passive',tip=esc(m.name+'\n'+m.desc+(m.mana?'\nCosts '+m.mana+' of its weapon’s mana':'')+(m.chakra?'\nCosts '+m.chakra+' chakra':'')+(m.supply?'\nThrows one of its kunai':'')+(m.cool?'\nReady again '+m.cool+' s after':'')+(m.range>1?'\nReach: '+m.range+' tiles':''));
  const b=act&&!lock?'<button class="hfab'+cls+'" data-do="weaponmove" data-value="'+esc(u.ref+'|'+m.id)+'"'+(m.wait>0&&m.cool>0?' style="--cd:'+Math.min(1,m.wait/m.cool).toFixed(3)+'"':'')+' title="'+tip+'">'+esc(m.name)+(m.wait>0?' · '+m.wait+'s':'')+'</button>':'<span class="hfmv'+(lock?' lock':'')+'" title="'+tip+'">'+(lock?'<b class="hcg hcg-lock">🔒</b> ':'')+esc(m.name)+'</span>';
  const r=lock?'<em>needs '+esc(m.lack)+'</em>':act?'<button class="hfauto" data-do="weaponmoveauto" data-value="'+esc(u.ref+'|'+m.id)+'" aria-pressed="'+!!m.auto+'" title="'+esc(m.auto?'Auto: used by itself in fights when ready. Click: only when you use it':'Manual: only when you use it. Click: by itself in fights too')+'">'+(m.auto?'Auto':'Manual')+'</button>':'<em>passive'+(m.mana?' · '+m.mana+' mana':'')+'</em>';
  return '<div class="hfmove">'+b+r+'</div>'};
 const ckBar=()=>ck?'<div class="bar wmana chakra"><span style="width:'+Math.max(0,Math.min(100,Math.round(100*ck.chakra/Math.max(1,ck.max))))+'%"></span><i>'+ck.chakra+' / '+ck.max+' chakra · '+ck.kunai+' / '+ck.kunaiMax+' kunai</i></div>':'';   // a ninja's (Ninja.dm)
 const wmBar=()=>wm?'<div class="hfwm">'+esc(wm.name)+'</div><div class="bar wmana"><span style="width:'+Math.max(0,Math.min(100,Math.round(100*wm.mana/Math.max(1,wm.max))))+'%"></span><i>'+wm.mana+' / '+wm.max+' mana</i></div>':'';
 if(sp&&!on('combat'))hcSpCd(u.ref,sp.wait||0);   // the cooldown bar's full length, kept while the tab is shut
 on('combat')&&pane('combat',JSON.stringify([u.ref,u.weapon,u.nonlethal,S.style,D.mode,sp&&[sp.name,sp.wait],lv('Combat'),lv('Sub'),!!u.ownPace]),()=>
  (u.weapon?'<div class="hfweapon"><span>Weapon</span>'+esc(u.weapon)+'</div>':'')+(sp?'<button class="spbtn" data-do="specialaim" data-value=""'+(sp.wait?' disabled style="--cd:'+hcSpCd(u.ref,sp.wait)+'"':(hcSpCd(u.ref,0),''))+' title="'+esc(sp.name+'\n'+sp.desc+'\nClick: aim it (or press F)')+'"><b class="hcg hcg-spark">✦</b> '+esc(sp.name)+(sp.wait?' · '+sp.wait+'s':' (F)')+'</button>':'')+
  row('Fight',pick('unitlethal','lethal',!u.nonlethal,'Lethal <b class="hcg hcg-sword">⚔</b>','Lethal\nFights to kill.')+pick('unitlethal','nonlethal',!!u.nonlethal,'Non-lethal <b class="hcg hcg-fist">✋</b>','Non-lethal\nKnocks enemies and animals out instead of killing them, so you can capture or tame them. Doesn’t shoot or throw.'),2)+
  row('Style',[['accurate','Accurate','Attack'],['aggressive','Aggressive','Strength'],['defensive','Defensive','Defence'],['controlled','Controlled','Attack, Strength and Defence']].map(([v,l,tr])=>pick('combatstyle',v,S.style===v,l,l+'\nMelee trains '+tr+'.')).join(''),2)+
  row('Stance',[['assist','Help nearby','Joins a fight when a tribe member within 8 tiles is attacked.'],['self','Defend self','Fights back only when it is attacked itself.'],['off','No response','Never fights on its own.']].map(([v,l,tip])=>pick('defensemode',v,D.mode===v,l,l+'\n'+tip)).join(''),2)+
  row('March',pick('unitpace','group',!u.ownPace,'With the group','With the group\nSent with others, it marches at the slowest one’s pace so they arrive together.')+pick('unitpace','own',!!u.ownPace,'Own pace','Own pace\nIt walks at its own speed, even when sent with a group.'),2)+
  tiles(T.filter(t=>t.group==='Combat'&&t.id!=='Magic'),2)+'<div class="hfh">Weapons</div>'+tiles(T.filter(t=>t.group==='Sub'),4));
 const own=ab.filter(a=>a[0]!=='Closest Creature'&&a[0]!=='Magical Skills');
 on('skills')&&pane('skills',JSON.stringify([u.ref,S.total,lv('Gathering'),lv('Artisan'),lv('Support')]),()=>
  [['Gathering','Gathering',2],['Artisan','Crafting'],['Support','Support']].map(([g,h,c])=>{const l=T.filter(t=>t.group===g);return l.length?'<div class="hfh">'+h+'</div>'+tiles(l,c):''}).join('')+
  '<div class="hfrow"><span>Total</span><b>'+esc(S.total||0)+'</b><button data-do="tab" data-value="units" title="Skill guides\nWhat each level does, in the Character panel.">Guides</button></div>');
 on('health')&&pane('health',JSON.stringify([u.ref,u.health,heroHealthView]),()=>heroHealth(u.health));
 on('family')&&pane('family',JSON.stringify([u.ref,u.family,u.race]),()=>heroFamily(u));
 on('interact')&&pane('interact',JSON.stringify([u.ref,own,wm,itemMv.map(m=>[m.id,m.lack]),u.captive]),()=>capCardHtml(u)+
  '<div class="hfh">Its own abilities</div>'+(own.length?'<div class="hfspells">'+own.map(a=>abBtn(a,'')).join('')+'</div>':'<p class="hfnote">Nothing of its own to use right now.</p>')+
  (wm?'<div class="hfh">Its weapon</div>'+wmBar()+'<p class="hfnote">Its moves and spells are on the <b>Spells</b> tab.</p>':'')+
  '<p class="hfnote">With the creature beside it: <b>Interact (I)</b> in the middle bar.</p>');
 const magic=ab.filter(a=>a[0]==='Magical Skills'),mg=T.filter(t=>t.id==='Magic');   // its race's own magic (a Svartalfar's)
 on('spells')&&pane('spells',JSON.stringify([u.ref,u.aptitude,magic,mg.map(t=>[t.level,t.progress]),itemMv,wm,classMv,!!u.weapon,ninjaMv,ck]),()=>   // hud-craft: the weapon moves live here since 10-23 (the user: they belong with spells)
  (ninjaMv.length?'<div class="hfh">Techniques · keys 1-4 at the mouse</div>'+ckBar()+ninjaMv.map((m,i)=>mvRow(Object.assign({},m,{name:(i+1)+' · '+m.name}),' ninja')).join(''):'')+'<div class="hfh">Weapon moves</div>'+(classMv.length?classMv.map(m=>mvRow(m,'')).join(''):'<p class="hfnote">'+(u.weapon?'No moves for this weapon yet.':'Bare-handed: no weapon moves.')+'</p>')+
  (itemMv.length?'<div class="hfh">Its weapon’s spells</div>'+wmBar()+itemMv.map(m=>mvRow(m,' magic')).join(''):'')+
  (magic.length?'<div class="hfh">Its own magic</div><div class="hfspells">'+magic.map(a=>abBtn(a,' magic')).join('')+'</div>':itemMv.length?'':'<p class="hfnote">'+(u.aptitude?'Knows no spells yet.':'No magic of its own; spells come from enchanted weapons and scrolls.')+'</p>')+tiles(mg))}
// The middle bar's Interact (I) with one of yours selected: the creatures around it and what it can do with
// them - the original Interact menu's "Closest Creature" (feed from, breed with, rescue, bite), and have a
// child, capture or tame, attack, carry, treat. Its own abilities are on its card's Interact tab.
function nearCardHtml(u){const nm=n=>esc(String(n||'').replace(/^\{[^}]*\}\s*/,'')),nb=arr(u.nearby),near=arr(u.abilities).filter(a=>a[0]==='Closest Creature');
 const act=(c,a)=>a==='talk'?'<button data-do="quest" data-value="'+esc('keeper|'+c.id)+'" title="Talk\nTheir words, and the quests they give or the goods they sell.">Talk</button>':a==='select'?'<button data-do="select" data-value="'+esc(c.ref)+'" title="Select\nSelect '+nm(c.name)+' instead.">Select</button>':
  a==='child'?'<button data-do="breed" data-value="'+esc(u.ref+'|'+c.ref)+'" title="'+esc('Have a child\nThey go off together for a while.')+'"><b class="hcg hcg-heart">♥</b> Child</button>':
  a==='capture'?'<button data-do="captureorder" data-value="'+esc(c.id)+'" title="'+esc((c.critter?'Tame':'Capture')+'\n'+(c.ko?'Knocked out: walks over and takes them.':'Fights non-lethal until they are knocked out, then takes them.')+(c.critter?' An animal is tamed at once.':(c.rope==='carried'?' A person is tied with the rope your people carry,':c.rope==='stockpile'?' A person is tied with a rope fetched from the stockpile or nearby,':' A person needs a rope to be tied: none carried or lying near (make one at a Leatherworks or Carpentry),')+' then won over or enslaved.'))+'"><b class="hcg hcg-chain">⛓</b> '+(c.critter?'Tame':'Capture')+(c.rope===''?' · no rope':'')+'</button>':
  a==='winover'?'<button data-do="captive" data-value="'+esc(c.ref+'|win|'+u.ref)+'" title="'+esc('Win over\n'+nm(u.name)+' sits with them: talk, and food when they are hungry. At full loyalty they join your house.')+'"><b class="hcg hcg-heart">♥</b> Win over</button>':
  a==='attack'?'<button data-do="attackorder" data-value="'+esc(c.id)+'" title="'+esc((c.critter?'Hunt':'Attack')+'\nGoes to fight them'+(u.nonlethal?' (non-lethal: knocks them out)':'')+'.')+'"><b class="hcg hcg-sword">⚔</b> '+(c.critter?'Hunt':'Attack')+'</button>':
  a==='carrybody'?'<button data-do="carrybody" data-value="'+esc(u.ref+'|'+c.id)+'" title="Carry the body\nWalk over and take it up."><b class="hcg hcg-carry">⇡</b> Carry</button>':
  a==='dragbody'?'<button data-do="carrybody" data-value="'+esc(u.ref+'|'+c.id)+'" title="Drag the body\nWalk over, take hold and drag it along the ground behind (slower going): to the graveyard, a table or a workshop. Let go from here again."><b class="hcg hcg-carry">⇡</b> Drag</button>':
  a==='report'?'<button data-qrep="'+esc('unit|'+c.id)+'" title="Report this player\nRude words, griefing or cheating: the admins look at it.">Report</button>':
  a==='letgo'?'<button data-do="carrybody" data-value="'+esc(u.ref+'|'+c.id+'|0')+'" title="Let go\nLeave the body where it lies."><b class="hcg hcg-carry">⇣</b> Let go</button>':'';   /* Drag / Let go: BodyDrag.dm */
 const uses=c=>arr(c.uses).map(x=>'<button data-do="'+esc(x[1])+'" data-value="'+esc(x[2])+'" title="'+esc(x[0]+'\n'+(x[3]||''))+'">'+icGlyph(x[0],x[1])+' '+esc(hcUseLabel(x[0]))+'</button>').join('');
 let h='<div class="nchead"><b>'+nm(u.name)+' · with those near</b><button data-ui="nearcard-close" aria-label="Close">Close</button></div>';
 if(near.length)h+='<div class="hfh">Beside it</div><div class="hfspells">'+near.map(([m,n])=>'<button class="hfab" data-do="unitability" data-value="'+esc(u.ref+'|'+m+'|'+n)+'" title="'+nm(n)+'">'+nm(n)+'</button>').join('')+'</div>';
 if(nb.length)h+='<div class="hfh">Near it</div>'+nb.map(c=>'<div class="hfnear"><div><b>'+nm(c.name)+'</b><span>'+esc(c.kind+(c.critter||!c.race||c.race===String(c.name).split(' ')[0]?'':' · '+c.race)+' · '+c.dist+' tile'+(c.dist===1?'':'s')+(c.ko?' · knocked out':c.hp<100?' · '+c.hp+'% health':''))+'</span></div><div>'+uses(c)+arr(c.acts).map(a=>act(c,a)).join('')+'</div></div>').join('');
 if(!nb.length&&!near.length)h+='<p class="hfnote">No one within 5 tiles. Walk it up to someone to feed from them, have a child, rescue, capture or tame them, or fight them.</p>';
 return h}
function nearCardUnit(){const sel=arr(model&&model.units).filter(u=>u.selected);return sel.length===1&&sel[0].nearby!=null?sel[0]:null}
function nearCardSync(){const c=$('nearcard');if(!c||c.hidden)return;const u=nearCardUnit();if(!u){c.hidden=true;queueRegions();return}
 const k=JSON.stringify([u.ref,u.name,u.nearby,arr(u.abilities).filter(a=>a[0]==='Closest Creature')]);if(c.dataset.k!==k){c.dataset.k=k;c.innerHTML=nearCardHtml(u)}}
function nearCardToggle(show){let c=$('nearcard');if(!c){c=document.createElement('div');c.id='nearcard';c.hidden=true;c.setAttribute('role','dialog');c.setAttribute('aria-label','Interact with those near the selected unit');document.body.append(c)}
 const open=show==null?c.hidden:show;if(open&&!nearCardUnit())return false;c.hidden=!open;delete c.dataset.k;nearCardSync();queueRegions();return true}
document.addEventListener('click',e=>{if(e.target.closest('[data-ui="nearcard-close"]')){nearCardToggle(false);return}const b=e.target.closest('#nearcard button[data-do]');if(b&&!['select'].includes(b.dataset.do))setTimeout(()=>nearCardToggle(false),0)});
// Family tab: house, ruler or heir, and the relatives (click one to select it); "Have a child" with a partner close by.
function heroFamily(u){const F=u.family||{},K=F.kin,nm=n=>esc(String(n||'').replace(/^\{[^}]*\}\s*/,''));let h='';
 if(F.captive)h+='<div class="wrole"><b class="hcg hcg-chain">⛓</b> '+(F.captive==='slave'?'Slave':'Bound captive')+' · not of your house (its Interact tab)</div>';
 if(F.expecting)h+='<div class="wrole"><b class="hcg hcg-heart">♥</b> Expecting a child</div>';
 if(K){h+='<div class="hfhouse">'+(K.house?'<i style="background:'+esc(K.color||'#888')+'"></i><b>House '+esc(K.house)+'</b>'+(K.foreign?' <span>(another lord’s)</span>':''):'<b>No house</b>')+'<span>'+(K.generation?' · generation '+esc(K.generation):'')+(K.born?' · born '+esc(K.born):'')+'</span></div>';
  const RU=F.rule||{};if(K.ruler||(K.heir&&!RU.heir))h+='<div class="wrole">'+(K.ruler?'<b class="hcg hcg-crown">♛</b> Head of the house':'<b class="hcg hcg-crown">♛</b> Named heir')+'</div>';
  /* rulership (Rulership.dm): the seat and its regalia, the heir and why, what crowning needs, another realm's items held */
  if(RU.seat){const S=RU.seat;h+='<div class="wrole"><b class="hcg hcg-crown">♛</b> '+esc(S.title||'Ruler')+(S.regalia?' · wears the '+esc(S.regalia):' · no regalia worn')+(S.health?' · +'+esc(S.health)+' health':'')+'</div>'+(S.need?'<p class="hfnote">'+esc(S.need)+'</p>':'')}
  else if(RU.heir)h+='<div class="wrole"><b class="hcg hcg-crown">♛</b> '+esc(RU.heir.word||'Heir')+' · heir: '+esc(RU.heir.why||'')+'</div>';
  if(RU.canRule)h+='<p class="hfnote">'+esc(RU.canRule)+'</p>';arr(RU.held).forEach(x=>{h+='<p class="hfnote">'+esc(x.text)+'</p>'});
  const who=p=>p.ref?'<button data-do="select" data-value="'+esc(p.ref)+'" title="'+esc(p.role+': '+p.name+(p.age!=null?'\nAge '+p.age:'')+'\nClick: select')+'">'+nm(p.name)+'</button>':'<span class="'+(p.dead?'dead':'away')+'" title="'+esc(p.role+': '+p.name+(p.dead?'\nDied':'\nNot in your settlement'))+'">'+(p.dead?'✝ ':'')+nm(p.name)+'</span>';
  const row=(label,L)=>'<div class="hfkin"><span>'+label+'</span><div>'+(L.length?L.map(who).join(''):'<em>none</em>')+'</div></div>';
  h+=row('Parents',arr(K.parents))+row('Partners',arr(K.partners))+row('Children',arr(K.children))+row('Siblings',arr(K.siblings))}
 else h+='<p class="hfnote">Animals don’t keep a family tree.</p>';
 const ps=arr(F.partners).slice(0,4);if(ps.length)h+='<div class="hfkin hfbreed"><span>Have a child</span><div>'+ps.map(p=>'<button class="hfab" data-do="breed" data-value="'+esc(u.ref+'|'+p.ref)+'" title="'+esc('Have a child with '+nm(p.name)+'\nThey go off together for a while.')+'"><b class="hcg hcg-heart">♥</b> '+nm(p.name)+'</button>').join('')+'</div></div>';
 if(K)h+='<div class="hfrow"><button data-do="villageview" data-value="lineage" data-focus="'+esc(K.uid||'')+'" title="Family tree\nThe whole lineage in the Village panel, this unit at the centre.">Family tree</button>'+(K.canHeir?'<button data-do="designateheir" data-value="'+esc(K.uid||'')+'" title="Name as heir\nInherits when the head of the house dies.">Name as heir</button>':'')+'</div>';
 return h}
// Health tab: a body diagram coloured by the worst injury in each part of it, the conditions, and every body part.
// Severity 0 (fine) .. 5 (destroyed or missing), from the original's state word and the part's health.
const PART_SEV={'Good':0,'Slighty Damaged':1,'Slightly Damaged':1,'Cut':1,'Damaged':2,'Slashed':2,'Broken':3,'Smashed':3,'Crushed':3,'Mangled':4,'Destroyed':5};
function partSev(p){if(!p.has)return 5;const r=p.hp/p.max,h=p.hp<=0?5:r<0.25?4:r<0.45?3:r<0.7?2:r<0.95?1:0;return Math.max(h,PART_SEV[p.st]||0)}
function partWord(p,v){if(!p.has)return 'Missing';if(p.st&&p.st!=='Good')return p.st.replace('Slighty','Slightly');return ['Good','Hurt','Injured','Badly hurt','Failing','Destroyed'][v]}
// Which parts the list shows: 'hurt' (the default), 'all', or one area of the body diagram (click it; again for hurt).
let heroHealthView='hurt';
const BODY_AREA={head:'Head',torso:'Body',larm:'Left arm',rarm:'Right arm',lleg:'Left leg',rleg:'Right leg',wings:'Wings'};
document.addEventListener('click',e=>{const t=e.target.closest&&e.target.closest('#heroframe [data-hzone],#heroframe [data-hview]');if(!t||!heroPanes.u)return;
 const v=t.dataset.hzone||t.dataset.hview;heroHealthView=t.dataset.hzone&&heroHealthView===v?'hurt':v;heroPanes($('heroframe'),heroPanes.u);queueRegions()});
function heroHealth(H){if(!H)return '<p class="hfnote">No health data.</p>';
 const parts=arr(H.parts).filter(p=>!p.na),zone={};for(const p of parts){const v=partSev(p);p.v=v;if(zone[p.z]==null||v>zone[p.z])zone[p.z]=v}
 const view=heroHealthView==='all'||zone[heroHealthView]!=null?heroHealthView:'hurt',hurt=parts.filter(p=>p.v>0);
 const zt=z=>esc(BODY_AREA[z]+'\n'+parts.filter(p=>p.z===z).map(p=>p.n+': '+partWord(p,p.v)).join('\n')+'\nClick: '+(view===z?'back to hurt parts':'list these parts'));
 const shape=(z,el)=>zone[z]==null?'':el.replace('/>',' class="z s'+zone[z]+(view===z?' sel':'')+'" data-hzone="'+z+'" title="'+zt(z)+'"/>');
 const doll='<svg class="hfdoll" viewBox="0 0 60 104" role="img" aria-label="Body: click an area to list its parts">'+(zone.wings!=null?shape('wings','<path d="M20 28 L2 14 L6 46 Z M40 28 L58 14 L54 46 Z"/>'):'')+
  shape('head','<circle cx="30" cy="11" r="9"/>')+shape('torso','<rect x="20" y="22" width="20" height="34" rx="3"/>')+
  shape('rarm','<rect x="11" y="23" width="7" height="31" rx="3"/>')+shape('larm','<rect x="42" y="23" width="7" height="31" rx="3"/>')+
  shape('rleg','<rect x="20.5" y="58" width="8.5" height="42" rx="3"/>')+shape('lleg','<rect x="31" y="58" width="8.5" height="42" rx="3"/>')+'</svg>';
 const conds=arr(H.conds),bm=H.bloodmax||0;
 let side='';if(bm)side+='<div class="hfblood" title="'+esc('Blood '+H.blood+' / '+bm+'\nBelow a quarter the unit faints; at none it dies.')+'"><span style="width:'+pct(H.blood,bm)+'%"></span><i>'+barLbl('Blood',H.blood,bm)+'</i></div>';
 side+=conds.length?'<div class="hfconds">'+conds.map(([t,v])=>'<span class="s'+v+'">'+esc(t)+'</span>').join('')+'</div>':'<p class="hfnote">No conditions.</p>';
 /* stumps (Stumps.dm): each lost limb's wound, and a button for each thing that can be done for it right now */
 const stumps=arr(H.stumps);if(stumps.length){side+='<div class="hfh">'+esc(H.stumpHead||'Stumps')+'</div>'+stumps.map(s=>'<div class="hfstump st-'+esc(s.st)+'" title="'+esc(s.limb+' stump\n'+s.tip)+'"><b>'+esc(s.limb)+'</b> '+esc(s.text)+'</div>').join('');
  const acts=arr(H.stumpActs);if(acts.length)side+='<div class="hfspells">'+acts.map(([k,l,t])=>'<button class="hfab" data-do="stump" data-value="'+esc(H.ref+'|'+k)+'" title="'+esc(l+'\n'+t)+'">'+esc(l)+'</button>').join('')+'</div>';else if(H.stumpHint)side+='<p class="hfnote">'+esc(H.stumpHint)+'</p>'}
 if(H.age!=null)side+='<p class="hfnote">Age '+esc(H.age)+'</p>';
 const shown=view==='all'?parts:view==='hurt'?hurt:parts.filter(p=>p.z===view);
 const bar='<div class="hfrow hfview"><span>Parts</span><div style="--n:'+(BODY_AREA[view]?3:2)+'"><button data-hview="hurt" aria-pressed="'+(view==='hurt')+'" title="Hurt parts\nOnly the injured and missing ones.">Hurt '+hurt.length+'</button><button data-hview="all" aria-pressed="'+(view==='all')+'" title="All parts\nEvery body part the unit has.">All '+parts.length+'</button>'+(BODY_AREA[view]?'<button data-hzone="'+view+'" aria-pressed="true" title="'+esc(BODY_AREA[view]+'\nClick: back to hurt parts')+'">'+esc(BODY_AREA[view])+' ✕</button>':'')+'</div></div>';
 const list=shown.length?'<div class="hfparts">'+shown.map(p=>'<div class="s'+p.v+'" title="'+esc(p.n+': '+partWord(p,p.v)+(p.has?'\nHealth '+Math.max(0,p.hp)+' / '+p.max:''))+'"><span>'+esc(p.n)+'</span><b>'+esc(partWord(p,p.v))+'</b></div>').join('')+'</div>':'<p class="hfnote">No injuries. Click a body area, or All, to see its parts.</p>';
 return '<div class="hfbody">'+doll+'<div>'+side+'</div></div>'+bar+list}
document.addEventListener('click',e=>{const b=e.target.closest('#heroframe .hfmore');if(!b)return;const hf=$('heroframe');const on=hf.classList.toggle('more');b.setAttribute('aria-expanded',on);b.textContent=on?'Less':'More';try{localStorage.setItem('rm-hfmore',on?'1':'')}catch(_){}queueRegions()});
try{if(localStorage.getItem('rm-hfmore'))document.addEventListener('DOMContentLoaded',()=>$('heroframe')?.classList.add('more'))}catch(_){}
const PANEL_HEAD={realm:['Realm','equip'],army:['Army','equip'],units:['Units','area'],village:['Village','build'],orders:['Orders','waypoint'],work:['Work','autodig'],build:['Build','build'],guide:['Guide','updates'],quests:['Quests','msg'],admin:['Admin','who']};
function panelHead(m){const h=PANEL_HEAD[currentTab];if(!h)return;const pg=$('page-'+currentTab);const first=pg&&pg.querySelector('h2');const sub=first?first.textContent:'';text($('phTitle'),h[0]);text($('phSub'),sub===h[0]?'':sub);if(pg)pg.classList.add('headed');const im=document.querySelector('#panelhead .crest img'),src=(m.icons||{})[h[1]];if(src&&im.getAttribute('src')!==src)im.src=src}
// The game's own text output (combat blow by blow, limbs, deaths) arrives from the
// Mac client as plain lines and joins the chat box at the bottom right.
// The engine's own chat route (server-cost, a2): a kept line comes as output(line, "mapwindow.hud:remasterChatLine"), and
// in shadow mode to remasterChatShadow, which only records it (window.rmChatShadow). Inert until that route is on.
window.remasterChatLine=t=>window.remasterChat&&window.remasterChat([t]);
window.remasterChatShadow=t=>(window.rmChatShadow=window.rmChatShadow||[]).push(t);
// A big battle near the camera (the owner, 10-28: "keep big battles in the backgound logs and only highlight favorited
// units"): 25 or more blows landed in the last 3 s (v3hits). Its fight lines then go only to Village > Log > Messages,
// and the corner keeps those naming a favourite of yours (TargetActions.dm rm_fav), starred.
function rmBigBattle(){const n=performance.now(),H=window.rmHitAt||[];while(H.length&&n-H[0]>3000)H.shift();return H.length>=25}
window.remasterChat=function(lines){if(!overlayHost)return;const box=$('toasts');if(!box)return;
 const big=rmBigBattle(),favs=arr(model&&model.units).filter(u=>u.fav).map(u=>String(u.name||'').replace(/^\{[^}]*\}\s*/,'')).filter(n=>n.length>1);
 for(const raw of lines){const msg=tidyLine(raw);if(!msg)continue;
  const t=document.createElement('div');t.className='toast chat';
  if(/flies off|severed|torn off|rips off|cut off|falls off|ripped|decapitat|blood|gore|dies|died|killed|slain|destroyed/i.test(msg))t.classList.add('gore');
  else if(/hits|strikes|slashes|stabs|bites|punches|kicks|smashes|damag|wound|bruis|cuts|attacks|misses|dodges|blocks/i.test(msg))t.classList.add('hit');
  else if(/level|learned|improv|skill/i.test(msg))t.classList.add('good');
  const fight=/gore|hit/.test(t.className),fav=fight&&favs.some(n=>msg.includes(n));
  if(big&&fight&&!fav){logPush(msg,'fight');continue}   /* a big battle's line: the background log only */
  if(fav)t.classList.add('fav');
  text(t,(fav?'\u2605 ':'')+msg);logPush(msg,/gore|hit/.test(t.className)?'fight':'chat');box.append(t);
  setTimeout(()=>t.classList.add('fade'),15000);setTimeout(()=>{t.remove();queueRegions()},15700)}
 while(box.childElementCount>10)box.firstChild.remove()};
// Realm: settlement rank ladder, the next rank's checklist, metal age, milestones.
function renderRealm(P){if(!P)return;window.__realmP=P;{const hb=$('tbHost');if(hb){const on=!!window.__hosting;if(hb.hidden===on)hb.hidden=!on;if(on){const ad=arr(window.__hosting.addresses)[0]||'',tip='Hosting for friends\nThey join with '+(ad||'this Mac')+'\nClick: the address and who is here';/* the chip says "Hosting"; the address is in its tip and on the Realm page (with it the top bar overflowed at 1440x900) (hud-craft) */if(hb.textContent!=='Hosting')hb.textContent='Hosting';if(hb.dataset.tip!==tip){hb.dataset.tip=tip;hb.removeAttribute('title')}}}}const rb=$('tbRank');if(rb){const t=P.rank+(P.next?' · '+P.needs.filter(n=>n.done).length+'/'+P.needs.length:'');if(rb.textContent!==t)rb.textContent=t}
 const box=$('realmBody');if(!box)return;const key=JSON.stringify(P);if(box.dataset.k===key)return;box.dataset.k=key;
 const ladder='<div class="ladder">'+P.ranks.map((r,i)=>'<div class="rung'+(r.reached?' on':'')+(i+1===P.rankIndex?' here':'')+'" title="'+esc(r.unlock)+'"><b>'+esc(r.name)+'</b></div>').join('<i></i>')+'</div>';
 const now='<div class="realmnow"><div><small>Rank</small><b>'+esc(P.rank)+'</b></div><div><small>Metal</small><b>'+esc(P.age)+'</b>'+(P.nextAge?'<em>Next: '+esc(P.nextAge)+'</em>':'')+'</div><div><small>People</small><b>'+esc(P.stats.pop)+'</b>'+(P.mood!=null?'<em>Mood '+P.mood+(P.mood>=60?' · content':P.mood>=30?' · uneasy':' · unhappy')+'</em>':'')+'</div><div><small>Treasury</small><b>'+esc(P.coins||0)+'</b><em>coins</em></div></div>';
 const next=P.next?'<h3>Becoming a '+esc(P.next)+'</h3><p class="hint">'+esc(P.nextUnlock)+'</p><div class="needs">'+P.needs.map(n=>'<div class="need'+(n.done?' done':'')+'"><span>'+(n.done?'✓':'○')+' '+esc(n.label)+'</span><span>'+Math.min(n.have,n.need)+' / '+n.need+'</span><div class="meter"><span class="fill" style="width:'+Math.round(100*Math.min(1,n.have/n.need))+'%"></span></div></div>').join('')+'</div>':'<h3>A Kingdom</h3><p class="hint">The top of the ladder. Long may it last.</p>';
 const ms='<h3>Milestones</h3><div class="milestones">'+P.milestones.map(x=>'<div class="ms'+(x.day?' got':'')+'">'+(x.day?'★':'☆')+' '+esc(x.label)+(x.day?'<small>Day '+x.day+'</small>':'')+'</div>').join('')+'</div>';
 const T=window.__trade,trade=!T?'':'<div class="tradebox"><h3>Trade caravan</h3>'+(!T.here?'<p class="hint">Merchants are on their way to your stockpile.</p>':!T.stockpile?'<p class="hint">Set a stockpile first: trade goods come from and go to it.</p>':'<p class="hint">Treasury <b>'+T.credit+'</b> coins'+(T.leavesMin!=null?' · they leave in '+T.leavesMin+' min':'')+'</p><h4>Their wares</h4><div class="wares">'+T.wares.map(w=>'<button data-do="trade" data-value="buy|'+esc(w.id)+'" '+(w.left<=0||T.credit<w.price?'disabled':'')+'>'+esc(w.label)+'<small>'+w.price+' · '+w.left+' left</small></button>').join('')+'</div><h4>Your stockpile</h4><div class="wares">'+(T.goods.length?T.goods.map(g=>'<button data-do="trade" data-value="sell|'+esc(g.name)+'">Sell '+esc(g.name)+'<small>+'+g.value+' · '+g.count+' here</small></button>').join(''):'<p class="hint">Nothing they want on the stockpile.</p>')+'</div>')+'</div>';
const HS=window.__hosting,RM=window.__realm||{},realm='<div class="tradebox housebox"><b>Your house</b><p class="hint">'+(RM.named?'Your people are known as House '+esc(RM.house)+'.':'Name your house or clan: your people, banners and realm carry it.')+'</p><div class="wares"><input id="houseName" maxlength="24" placeholder="e.g. Blackhide" value="'+esc(RM.named?RM.house:'')+'" aria-label="House name"><button id="houseSet" type="button">'+(RM.named?'Rename':'Name the house')+'</button></div></div><h3>Realm & allies</h3>'+(HS?'<div class="tradebox"><b>Hosting for friends</b><p class="hint">Friends on the same network open the game, choose <b>Join a friend</b> and enter <b>'+esc(arr(HS.addresses)[0]||'this Mac')+'</b>'+(arr(HS.addresses).length>1?' (or '+arr(HS.addresses).slice(1).map(esc).join(', ')+')':'')+' with the password you chose. Players here: '+HS.players+'.</p></div>':'')+(RM.liege?'<p class="hint">You belong to <b>'+esc(RM.liege)+'</b>. Your people count toward its rank; you may work in its land.</p><div class="wares"><button data-do="realm" data-value="leave">Leave the realm</button></div>':'')+(RM.asked&&!RM.liege?'<p class="hint">Waiting for an answer from '+esc(RM.asked)+'.</p>':'')+(arr(RM.requests).length?'<h4>Requests</h4>'+RM.requests.map(r=>'<div class="need"><span>'+esc(r.name||r.key)+(r.kind==='join'?' asks to join as migrants':' offers fealty')+'</span><span><button data-do="realm" data-value="accept|'+esc(r.key)+'">Accept</button> <button data-do="realm" data-value="decline|'+esc(r.key)+'">Decline</button></span></div>').join(''):'')+(arr(RM.members).length?'<h4>Your realm</h4>'+RM.members.map(x=>'<div class="need"><span>'+esc(x.name)+(x.vassal?' · vassal':' · migrants')+'</span><span>'+x.people+' people</span></div>').join(''):'')+warSection(RM)+(P.open?'':'<p class="hint">At Hamlet rank, newcomers may ask to join you as migrants.</p>');
 const rooms='<h3>Rooms</h3>'+(arr(P.rooms).length?'<div class="milestones">'+P.rooms.map(r=>'<div class="ms got">'+esc(r.name)+'<small>'+esc(r.grade)+' · '+r.size+' tiles · '+r.x+', '+r.y+'</small></div>').join('')+'</div>':'<p class="hint">Wall in a space with a door. Beds make a bedroom, a table and chairs a dining hall, a throne a throne room. Built floors, pillars, statues, tapestries, light and gold make them finer.</p>');
 const land='<h3>Your land</h3><p class="hint">'+(P.banners?P.banners+' of '+P.rankIndex+' banner'+(P.rankIndex>1?'s':'')+' planted · each claims '+P.radius+' tiles around it. Others cannot dig, chop or build inside.':'Plant a Claim banner (Work › Place a workshop, 1 wood) to claim land as your realm. It claims '+P.radius+' tiles around it and grows with your rank.')+'</p>';
 const flags='<p class="hint">'+(P.open?'Other players may ask to join your settlement. ':'')+(P.trade?'Trade caravans visit. ':'')+'</p>';
 /* Rule (Rulership.dm): the seat, a claim on it or by us, the heir and the heir's item, the law of succession */
 const RU=RM.rule,CO=RU&&RU.claimOn,rule=!RU?'':'<div class="tradebox"><h3>Rule</h3>'+(arr(RU.rulers).length?RU.rulers.map(r=>'<div class="need"><span><b class="hcg hcg-crown">♛</b> '+esc(r.title)+' '+esc(r.name)+'</span><span>'+(r.regalia?esc(r.regalia)+(r.health?' · +'+esc(r.health)+' health':''):'no regalia worn')+'</span></div>'+(r.need?'<p class="hint">'+esc(r.need)+'</p>':'')).join(''):'<p class="hint">'+(RU.vacant?'The seat is empty. ':'No one rules yet. ')+'A '+esc(String(RU.stage).toLowerCase())+'’s ruler wears '+(/^[AEIOU]/.test(RU.item)?'an':'a')+' <b>'+esc(RU.item)+'</b> (made '+esc(RU.made)+'; Craft new gear › Regalia) for +'+esc(RU.health)+' health. Select someone holding one, then Declare Leader.</p>')
  +(CO?'<div class="need"><span class="atwar">'+esc(CO.holderName)+' of House '+esc(CO.house)+' holds your '+esc(CO.item)+' and claims your seat'+(CO.state==='open'?' (they have '+esc(CO.mins)+' min to press it)':CO.state==='refused'?': you refused, and it’s war':': they press it. Answer:')+'</span><span>'+(CO.state==='pressed'?'<button data-do="realm" data-value="yield|'+esc(CO.by)+'" title="Yield\nSwear fealty to their realm: yours becomes its vassal.">Yield</button> <button class="warbtn" data-do="realm" data-value="refuse|'+esc(CO.by)+'" title="Refuse\nWar at once. The claim stands while they hold the item; take it back, or hold out until peace.">Refuse</button>':CO.state==='refused'?'<button data-do="realm" data-value="yield|'+esc(CO.by)+'" title="Yield\nEnd the war: swear fealty to their realm.">Yield</button>':'')+'</span></div><p class="hint">No one can be crowned until the claim is settled.</p>':'')
  +arr(RU.claims).map(c=>'<div class="need"><span>'+esc(c.holder)+' holds '+esc(c.realm)+'’s '+esc(c.item)+(c.state==='open'?': a claim on its empty seat ('+esc(c.mins)+' min left)':c.state==='pressed'?': claim pressed, waiting for them':': they refused, and it’s war. Take their last banner and their realm is yours')+'</span><span>'+(c.state==='open'?'<button data-do="realm" data-value="claim|'+esc(c.key)+'" title="Press the claim\nThey yield and swear fealty to you, or refuse and it is war.">Press the claim</button>':'')+'</span></div>').join('')
  +'<h4>Heir</h4><p class="hint">'+(RU.heir?'<b>'+esc(RU.heir)+'</b>'+(RU.heirWord&&RU.heirWord!=='Heir'?' ('+esc(RU.heirWord)+')':'')+': '+esc(RU.heirWhy||'')+'. ':'No heir. ')+(RU.heirItem?'Your '+esc(RU.heirItem.name)+' is '+esc(RU.heirItem.where)+(RU.heirItem.ours?'.':': take it back!'):'No heir’s item yet: make an Heir’s Circlet (forge, 1 silver ingot) or an Heir’s Band (bone crafter) and have your heir wear it. Whoever of your realm holds it inherits first; a rival who takes it can claim your seat.')+'</p>'
  +'<h4>Law of succession</h4><div class="wares">'+arr(RU.laws).map(l=>'<button data-do="realm" data-value="law|'+esc(l.id)+'"'+(l.id===RU.law?' aria-pressed="true"':'')+' title="'+esc(l.name+'\n'+l.tip+(l.id!==RU.law&&RU.lawSet&&RU.lawMood?'\nChanging to it: mood '+RU.lawMood+' for a week.':''))+'">'+esc(l.name)+'</button>').join('')+'</div></div>';
 const html=trade+ladder+now+rule+next+realm+rooms+land+ms+flags;
 // only when it changed, and never under a press: a rebuilt button would swallow the click
 if(box._html===html)return;if(box.contains(document.activeElement)&&document.activeElement.matches('input,textarea,select')){box._pending=true;box.dataset.k='';if(!box._blurWired){box._blurWired=true;box.addEventListener('focusout',()=>setTimeout(()=>{if(box._pending){box._pending=false;renderRealm(window.__realmP)}},0))}return}if(box._pressed){box._pending=true;box.dataset.k='';return}box._html=html;box.innerHTML=html;
 if(!box._pressWired){box._pressWired=true;box.addEventListener('pointerdown',()=>{box._pressed=true});addEventListener('pointerup',()=>{if(!box._pressed)return;setTimeout(()=>{box._pressed=false;if(box._pending){box._pending=false;renderRealm(window.__realmP)}},0)},true)}}
// Damage numbers: rise and fade over the target for a second and a half.
function v3hits(list){if(!V3.floats)V3.floats=[];V3.hitSeen=V3.hitSeen||new Set();const box=$('dmgfloats');if(!box)return;
 for(const h of arr(list)){if(V3.hitSeen.has(h.id))continue;V3.hitSeen.add(h.id);if(h.k==='die'||h.k==='limb'||h.k==='drop'){if(window.g3hit)g3hit(h);continue}if(window.g3hit)g3hit(h);   /* a death the server tells (Gear3D.dm) shows no number; blows play as moves (gear3d.js game.js) */if(h.k==='miss'){V3.missAt=V3.missAt||{};const mk=h.x+','+h.y,now=performance.now();if(now-(V3.missAt[mk]||0)<700)continue;V3.missAt[mk]=now}if(V3.hitSeen.size>400)V3.hitSeen=new Set([...V3.hitSeen].slice(-200));
  if(typeof h.k==='string'&&h.k[0]==='+'){if(h.mine||h.mineby)V3.floats.push({cls:'dmg catchw',txt:h.k,x:h.x,y:h.y,key:v3floatOn(h.x,h.y),t:performance.now()+500,dx:0,life:1800});continue}
  const word={wall:'Wall',wreck:'Wreck',parry:'Parry',stagger:'Stagger!',ko:'Knocked out!',bleed:'Bleed',cleave:'Cleave',crit:'Critical!',save:'Armour save',flank:'Flanked!',rear:'From behind!',turned:'Turned to meet it!',m2:'Battle fury!',m1:'Emboldened!','m-1':'Shaken!','m-2':'Broken!',rout:'Routing!',cover:'Covered!',charge:'Charge!',reach:'Reach',double:'Double',crush:'Crush',block:'Blocked',burn:'Burn!',venom:'Venom',webbed:'Webbed',astral:'Astral',chill:'Chill',shock:'Shock',drain:'Drain',smite:'Smite',echo:'Again!',guard:'Riposte!',sub:'Substitution!',subready:'Substitution',flash:'Flash step',seal:'Hand seals'}[h.k];
  const cls='dmg '+(h.k==='kill'?'kill':h.k==='miss'?'miss':h.k==='block'?'parry':['parry','stagger','bleed','ko','burn','venom','webbed','chill','echo'].includes(h.k)?h.k:h.mine?'hurt':h.n>=30?'big':'hit');
  const txt=h.k==='kill'?'\u2620 '+(h.n||''):h.k==='miss'?'Miss':['parry','stagger','bleed','block','ko','burn','venom','webbed','chill','echo','crit','flank','rear','turned','m2','m1','m-1','m-2','rout','cover','charge'].includes(h.k)?word:(word&&h.k!=='crush'?word+' ':'')+h.n;
  const eng=h.w==='ram'||h.w==='catapult'||h.w==='ballista';if(eng){V3.siegeAnim=V3.siegeAnim||{};V3.siegeAnim[h.ax+','+h.ay]=performance.now()}
  let late=h.g3late||0;if(h.p&&!h.g3shot){const l=Math.hypot(h.x-h.ax,h.y-h.ay);late=(h.p==='arrow'?90+l*55:h.p==='bolt'?60+l*30:h.p==='boulder'?400+l*90:150+l*85);V3.fx=V3.fx||[];V3.fx.push({type:'proj',p:h.p,x:h.x,y:h.y,ax:h.ax,ay:h.ay,miss:h.k==='miss'||h.k==='block',t:performance.now(),dur:late,seed:h.id})}
  if(h.k==='wall'||(eng&&h.p==='boulder')){setTimeout(()=>{V3.fx=V3.fx||[];V3.fx.push({type:'rock',x:h.x,y:h.y,col:[0.6,0.56,0.5,1],t:performance.now()})},late)}
  if(eng);else if(h.k!=='miss'&&h.k!=='bleed'&&h.w&&h.w!=='bow'&&!h.g3swing){V3.fx=V3.fx||[];V3.fx.push({type:'swing',w:h.k==='parry'?'parry':h.w,x:h.x,y:h.y,ax:h.ax,ay:h.ay,t:performance.now()})}/* a number only where the player's own units are in it, hurt or striking (user, 2026-10-24); every blow still animates */if(h.mine||h.mineby)V3.floats.push({cls,txt:String(txt),x:h.x,y:h.y,key:v3floatOn(h.x,h.y),t:performance.now()+late,dx:(Math.random()-0.5)*0.5,life:h.k==='miss'?800:1500});
  // in a big fight the oldest numbers give way (at most 30 on screen): readable, and less page work each frame
  while(V3.floats.length>30)V3.floats.shift();
  // the moment it lands: the struck unit flashes and a short burst flies off it (v3impact)
  if(h.k!=='miss'&&h.k!=='bleed'&&!eng){const at=performance.now()+late;(V3.flash||(V3.flash=new Map())).set(h.x+','+h.y,at);V3.flashN=(V3.flashN||0)+1;{const W=window.rmHitAt||(window.rmHitAt=[]);W.push(performance.now());if(W.length>400)W.splice(0,W.length-400)}   /* blows landing near the camera: a big battle (rmBigBattle) */(V3.impacts||(V3.impacts=[])).push({x:h.x,y:h.y,ax:h.ax,ay:h.ay,t:at,k:h.k,w:h.w,n:h.n||0});if(h.k==='kill')(V3.kills||(V3.kills=new Map())).set(h.x+','+h.y,at)}}}
// Floating combat text, drawn on one 2D canvas over the 3D view (it was a DOM element per number, which cost WebKit
// ~8 ms a frame in a big fight). Each style's colour, size, weight and opacity are read once from the page's own .dmg
// CSS classes, so restyling them still applies; a dark rounded outline stands in for the text shadow.
function v3floatStyle(cls){const S=V3.fltS||(V3.fltS=new Map());let s=S.get(cls);if(s)return s;const box=$('dmgfloats');s={font:'bold 18px HudText,Georgia,serif',color:'#fff',op:1,px:18};
 if(box){const el=document.createElement('div');el.className=cls;el.textContent='0';el.style.visibility='hidden';box.append(el);const cs=getComputedStyle(el);s={font:(cs.fontStyle||'normal')+' '+(cs.fontWeight||'bold')+' '+(cs.fontSize||'18px')+' '+(cs.fontFamily||'HudText,Georgia,serif'),color:cs.color||'#fff',op:parseFloat(cs.opacity)||1,px:parseFloat(cs.fontSize)||18};el.remove()}
 S.set(cls,s);return s}
// The unit a number lands on: the one standing on the blow's tile (its key, so the number follows it as it moves).
function v3floatOn(x,y){const T=V3.things;if(!T)return null;for(const t of T)if(t.x===x&&t.y===y&&t.key&&V3UNITK.has(t.kind))return t.key;return null}
function v3floatsTick(){const F=V3.floats;let cv=V3.fltC;
 if(!F||!F.length){if(cv&&V3.fltDirty){cv.getContext('2d').clearRect(0,0,cv.width,cv.height);cv.style.display='none';V3.fltDirty=false}return}   /* hidden when empty: no full-window layer to composite */
 if(!cv){const box=$('dmgfloats');if(!box)return;cv=V3.fltC=document.createElement('canvas');cv.style.cssText='position:fixed;left:0;top:0;width:100vw;height:100vh;pointer-events:none;background:transparent;border:0;border-radius:0;box-shadow:none;margin:0;max-width:none;image-rendering:auto;cursor:default';box.append(cv)}   /* the page's plain canvas rule is for the minimap */
 if(cv.style.display==='none')cv.style.display='';const dpr=Math.min(2,window.devicePixelRatio||1),c3=$('world3d');
 // The page is scaled for the HUD (a CSS zoom on the whole document) and WebKit lays this full-window canvas out at the zoomed
 // size, so its buffer is sized from its own box and each number is mapped from the 3D view's box to this one, as both are
 // on screen. (A buffer the window's size was stretched: at HUD scale 0.8 the numbers sat 1.25x as far from the top left as
 // their units, so they were off them and slid whenever the camera moved or zoomed.) Measured again on a resize or rescale.
 const bk=innerWidth+'x'+innerHeight+'@'+document.documentElement.style.zoom;if(!V3.fltBox||V3.fltBox.key!==bk||performance.now()-V3.fltBox.t>1000){const rf=cv.getBoundingClientRect(),r3=c3.getBoundingClientRect();V3.fltBox={key:bk,t:performance.now(),rf,r3,cw:c3.clientWidth||1,ch:c3.clientHeight||1,bw:Math.max(1,Math.round(cv.clientWidth*dpr)),bh:Math.max(1,Math.round(cv.clientHeight*dpr))}}
 const B=V3.fltBox,w=B.bw,hh=B.bh;if(cv.width!==w||cv.height!==hh){cv.width=w;cv.height=hh}const kx=w/(B.rf.width||1),ky=hh/(B.rf.height||1),mxk=B.r3.width/B.cw*kx,myk=B.r3.height/B.ch*ky,ox=(B.r3.left-B.rf.left)*kx,oy=(B.r3.top-B.rf.top)*ky;
 const g=cv.getContext('2d'),now=performance.now();g.setTransform(1,0,0,1,0,0);g.clearRect(0,0,w,hh);V3.fltDirty=true;g.textAlign='center';g.textBaseline='middle';g.lineJoin='round';g.strokeStyle='rgba(0,0,0,0.9)';
 V3.floats=F.filter(f=>{const a=(now-f.t)/(f.life||1500);if(a>=1||!V3.on)return false;if(a<0)return true;
  // over the unit it landed on, where that unit is drawn now (it glides from tile to tile, a flyer is up in the air)
  const d=f.key&&V3.disp.get(f.key),ux=d?d.dx:f.x,uy=d?d.dy:f.y,air=d?(d.lift||0)+(d.alt||0):0;const [X,,Z]=v3world({dx:ux,dy:uy});const Y=(air>0.3?air:d&&d.gy!=null?d.gy:v3groundAt(ux,uy))+1.3;   /* over its feet as drawn (d.gy, the unit loop's): up on a wall-walk or the rock too, where the ground under it is the wall's foot */const p=v3project([X,Y,Z]),p1=p&&v3project([X,Y+1,Z]);if(!p)return true;
  // sized for the zoom it appears at: a tile's height on screen at the usual zoom (~72 px) or nearer is full size; further out
  // smaller, to 9 px. Its scatter to the side and its rise (most of a tile's height over its life) go with that size, so a
  // flurry looks the same at any zoom, only smaller (far out they piled into one blot). The size is kept for the number's
  // life: zooming while it is up, it stays put over the unit's head (sized every frame, it slid as the zoom changed)
  const s=v3floatStyle(f.cls);if(f.zk==null){const ppu=p1?Math.hypot(p1[0]-p[0],p1[1]-p[1]):72;f.zk=Math.max(9/s.px,Math.min(1,ppu/72))}const zk=f.zk,k=(a<0.12?0.6+a*3.3:1)*zk*kx;f.sx=p[0]+f.dx*72*zk;f.sy=p[1]-s.px*zk*0.5-a*65*zk;f.sk=zk;g.setTransform(k,0,0,k,ox+f.sx*mxk,oy+f.sy*myk);g.globalAlpha=s.op*(a<0.7?1:1-(a-0.7)/0.3);g.font=s.font;g.lineWidth=Math.max(2.5,s.px*0.17);g.strokeText(f.txt,0,0);g.fillStyle=s.color;g.fillText(f.txt,0,0);return true});
 g.globalAlpha=1;g.setTransform(1,0,0,1,0,0);
 // numbers never draw over the HUD's panels: their rectangles (measured at most every 0.4 s) are cut out afterwards
 const HR=v3hudRects();if(HR.length){g.globalCompositeOperation='destination-out';g.fillStyle='#000';for(const r of HR)g.fillRect((r[0]-B.rf.left)*kx,(r[1]-B.rf.top)*ky,r[2]*kx,r[3]*ky);g.globalCompositeOperation='source-over'}}
const V3HUDSEL=['nav','.world','.taskmode','#topbar','#roster','#heroframe','main','#attack','#foodalert','#menu3d','#nearcard','#usecard','#askcard','#startcard','#goaltrack','#loghist','#worldmap','#daycard','#awaycard','#settings','#lockbar','#questcard','#questtrack'];
function v3hudRects(){const now=performance.now();if(V3.hudR&&now-V3.hudRAt<400)return V3.hudR;const r=[];
 for(const s of V3HUDSEL){const el=document.querySelector(s);if(!el)continue;const b=el.getBoundingClientRect();if(b.width<=0||b.height<=0)continue;const cs=getComputedStyle(el);if(cs.display==='none'||cs.visibility==='hidden')continue;r.push([b.left-10,b.top-10,b.width+20,b.height+20])}   /* the race frames are drawn a few px outside the box */
 V3.hudR=r;V3.hudRAt=now;return r}
document.addEventListener('click',e=>{if(e.target.closest('#houseSet')){const i=$('houseName');if(i&&i.value.trim()){send('housename',i.value.trim());i.blur()}else if(i){i.focus();toast('Type a name for your house first.')}}});
document.addEventListener('keydown',e=>{if(e.key==='Enter'&&e.target&&e.target.id==='houseName'){e.preventDefault();e.stopPropagation();const v=e.target.value.trim();if(v){send('housename',v);e.target.blur()}else toast('Type a name for your house first.')}},true);
function warSection(RM){const WR=RM.war||{},wars=arr(WR.wars),ruler=!!WR.ruler,gr=WR.grievances||{},others=arr(RM.others).slice();let h='';
 for(const w of wars)if(!others.some(o=>o.key===w.key))others.push({key:w.key,name:w.name,rel:w.state});
 const rows=others.map(o=>{const w=wars.find(x=>x.key===o.key),rel=o.rel||'peace',k=esc(o.key);let st,btn='';
  if(rel==='war'){st='<b class="atwar">At war</b>'+(w?' · '+w.mine+' : '+w.theirs:'');if(ruler&&w)btn=w.peaceBy==='them'?'<button data-do="realm" data-value="acceptpeace|'+k+'">Accept peace</button> <button data-do="realm" data-value="declinepeace|'+k+'">Refuse</button>':w.peaceBy==='me'?'<i>peace offered</i>':'<button data-do="realm" data-value="peace|'+k+'">Offer peace</button>'}
  else if(rel==='warning'){st='<b class="atwar">War in '+(w?w.secs:'?')+' s</b>';if(ruler&&w)btn=w.peaceBy==='them'?'<button data-do="realm" data-value="acceptpeace|'+k+'">Accept peace</button> <button data-do="realm" data-value="declinepeace|'+k+'">Refuse</button>':w.peaceBy==='me'?'<i>peace offered</i>':'<button data-do="realm" data-value="peace|'+k+'">Offer peace</button>'}
  else if(rel==='truce'){st='Truce'+(w?' · '+Math.ceil(w.secs/60)+' min':'');}
  else{st=gr[o.key]?'<b class="atwar">Attacked your people</b>':'At peace';if(ruler&&o.ruler!==false)btn='<button class="warbtn" data-do="realm" data-value="war|'+k+'">'+(gr[o.key]?'Declare war now':'Declare war')+'</button>';if(!RM.liege&&o.ruler!==false)btn+=' <button data-do="realm" data-value="fealty|'+k+'">Swear fealty</button>'}
  return '<div class="need"><span>'+esc(o.name)+'<br><small>'+st+'</small></span><span>'+btn+'</span></div>'}).join('');
 if(rows)h+='<h4>Other realms</h4>'+rows+(ruler?'<p class="hint">War starts 60 s after you declare it (at once if they attacked you first). At war your people fight theirs on sight, may tear down their walls, and can take their banners: stand by one with nobody guarding it. Peace brings a 10 minute truce.</p>':'<p class="hint">Your ruler decides on war and peace.</p>');
 const sg=arr(WR.sieges);if(sg.length)h+='<h4>Sieges</h4>'+sg.map(x=>'<div class="need"><span>'+(x.ours?'Your banner':esc(x.name)+'\'s banner')+' at '+x.x+','+x.y+'</span><span class="siegebar"><i style="width:'+x.p+'%"></i></span></div>').join('');
 return h}
function warStrip(m){const el=$('warbar');if(!el)return;const WR=(m.realm&&m.realm.war)||{},w=arr(WR.wars).filter(x=>x.state==='war'||x.state==='warning'),sg=arr(WR.sieges).filter(x=>x.ours);
 document.body.classList.toggle('atwar',w.length>0);if(!w.length){if(!el.hidden)el.hidden=true;return}const t=w.map(x=>x.state==='war'?'\u2694 At war with '+x.name+' \u00b7 '+x.mine+' : '+x.theirs+(x.peaceBy==='them'?' \u00b7 they offer peace':''):'\u2694 War with '+x.name+' in '+x.secs+' s').join('   ')+(sg.length?'   \u00b7 a banner of yours is under siege!':'');{/* the crossed swords as the HUD's sword icon (at 14 px the glyph read as a stray ×) */const h=esc(t).replace(/\u2694 /g,'<b class="hcg hcg-sword">\u2694</b> ');if(el.dataset.h!==h){el.dataset.h=h;el.innerHTML=h}}el.hidden=false}

// Race specials (Specials.dm): what each looks like, its aim preview and its effect.
const SPC={breath:[1,0.55,0.15],frost:[0.6,0.85,1],poison:[0.45,0.85,0.3],mind:[0.78,0.5,1],web:[0.95,0.95,0.95],tongue:[0.92,0.45,0.55],dart:[0.55,0.8,0.3],acid:[0.6,0.95,0.25],pierce:[0.9,0.95,1],charge:[0.85,0.75,0.5],leap:[0.72,0.56,0.36],shadowstep:[0.45,0.25,0.65],slam:[0.62,0.52,0.42],sweep:[0.55,0.62,0.38],firepot:[1,0.5,0.12],plague:[0.5,0.78,0.3]};
const SPARG={breath:70,mindblast:60};
function v3specials(list){V3.spSeen=V3.spSeen||new Set();for(const f of arr(list)){if(V3.spSeen.has(f.id))continue;V3.spSeen.add(f.id);if(V3.spSeen.size>200)V3.spSeen=new Set([...V3.spSeen].slice(-100));V3.fx=V3.fx||[];V3.fx.push({type:'special',sp:f.sp,el:f.el,sx:f.sx,sy:f.sy,tx:f.tx,ty:f.ty,t:performance.now()})}}
function spTiles(A,hx,hy){const out=[],dx=hx-A.x,dy=hy-A.y,l=Math.hypot(dx,dy)||1,ux=dx/l,uy=dy/l,R=A.range;
 const clampTo=r=>l<=r?[hx,hy]:[Math.round(A.x+ux*r),Math.round(A.y+uy*r)];
 if(A.shape==='cone'){const a0=Math.atan2(dy,dx),half=(A.arg||60)*Math.PI/360;for(let y=-R;y<=R;y++)for(let x=-R;x<=R;x++){if((!x&&!y)||x*x+y*y>R*R+0.5)continue;let d=Math.atan2(y,x)-a0;while(d>Math.PI)d-=2*Math.PI;while(d<-Math.PI)d+=2*Math.PI;if(Math.abs(d)<=half)out.push([A.x+x,A.y+y])}}
 else if(A.shape==='line'||A.shape==='first'||A.shape==='dash'){const seen=new Set();for(let s=0.5;s<=R+0.01;s+=0.5){const x=Math.round(A.x+ux*s),y=Math.round(A.y+uy*s),k=x+','+y;if((x===A.x&&y===A.y)||seen.has(k))continue;seen.add(k);out.push([x,y])}}
 else if(A.shape==='self'){const r=A.arg||1;for(let y=-r;y<=r;y++)for(let x=-r;x<=r;x++)if(x||y)out.push([A.x+x,A.y+y])}
 else{const [cx,cy]=clampTo(R),r=A.shape==='blink'?0:(A.arg||1);for(let y=-r;y<=r;y++)for(let x=-r;x<=r;x++)out.push([cx+x,cy+y])}
 return out}
// The part of a great beast under the pointer while units are selected (Beasts.dm parts): a ring on its tile and its
// name by the pointer; a right-click lists it first ("Attack its left wing (here)").
function v3hoverPart(mx,my){let h=null;if(arr(model&&model.units).some(u=>u.selected)){const t=v3pickThing(mx,my);if(t&&t.beast&&t.kind!=='mine'&&arr(t.beast.parts).length){let bd=1e9;
  for(const q of t.beast.parts){const [PX,,PZ]=v3world({dx:q[0],dy:q[1]}),sp=v3project([PX,v3groundAt(q[0],q[1])+0.5,PZ]),d=sp?Math.hypot(sp[0]-mx,sp[1]-my):1e9;if(d<bd){bd=d;h={x:q[0],y:q[1],n:q[2],hp:q[3],id:t.id}}}}}
 V3.hoverPart=h;let el=$('partTip');if(!el){el=document.createElement('div');el.id='partTip';el.className='parttip';document.body.appendChild(el)}
 if(h){el.textContent='Its '+h.n+(h.hp!=null?' · '+h.hp+'%':'');el.style.left=(mx+16)+'px';el.style.top=(my+14)+'px';el.hidden=false}else el.hidden=true}
// A great beast chained down (Taming.dm): heavy chains from its neck and hind legs, pulled taut to iron-ringed stakes
// driven in well clear of it (one fewer for each it has snapped), and two iron links turning over its head.
function v3drawBonds(a){const now=performance.now()/1000,iron=[0.36,0.37,0.41,1],shine=[0.62,0.64,0.7,1],wood=[0.33,0.22,0.13,1];
 for(const t of v3cat('bound',t=>t.beast&&t.beast.bound)){const B=t.beast;if(!B||!B.bound||t.dx==null||!v3visible(t))continue;const X=t.dx,Z=-t.dy,g=v3groundAt(t.dx,t.dy),s=B.size||1;
  const P={};for(const q of arr(B.parts)){const [PX,,PZ]=v3world({dx:q[0],dy:q[1]});P[q[2]]=[PX,PZ]}
  const anchors=[];for(const n of ['head','left hind leg','right hind leg','left foreleg','right foreleg']){const q=P[n];if(!q)continue;anchors.push([q[0],q[1],n==='head'?0.55*s:0.22*s])}
  if(!anchors.length)for(let k=0;k<3;k++){const an=k/3*6.283+0.6;anchors.push([X+Math.cos(an)*0.5*s,Z+Math.sin(an)*0.5*s,0.3*s])}
  const n=Math.min(anchors.length,Math.max(1,B.chains||3));
  for(let k=0;k<n;k++){const [ax,az,ay]=anchors[k];let dx=ax-X,dz=az-Z;const dl=Math.hypot(dx,dz)||1;dx/=dl;dz/=dl;
   const A=[ax,g+ay,az],E=[ax+dx*(0.9+0.35*s),g+0.32,az+dz*(0.9+0.35*s)],L=12;
   const pt=u=>[A[0]+(E[0]-A[0])*u,A[1]+(E[1]-A[1])*u-Math.sin(u*Math.PI)*0.06,A[2]+(E[2]-A[2])*u];
   for(let i=0;i<L;i++){const p0=pt(i/L),p1=pt((i+1)/L);MD.rod(a,p0,p1,0.026,4,i%2?iron:shine,k*20+i);MD.blob(a,p0[0],p0[1],p0[2],0.04,0.04,0.04,i%2?shine:iron,k*20+i,0.05)}
   MD.rod(a,[E[0],g-0.02,E[2]],[E[0],g+0.36,E[2]],0.05,5,wood,k+90);MD.blob(a,E[0],g+0.33,E[2],0.07,0.035,0.07,iron,k+95,0.05)}
  const hy=g+1.35*s,sp=now*1.2;for(let r=0;r<2;r++){const cx=X+(r?0.07:-0.07),rr=0.11;for(let i=0;i<10;i++){const a0=i/10*6.283,a1=(i+1)/10*6.283,f=(u,an)=>r?[cx+Math.cos(an)*rr*Math.cos(sp),hy+Math.sin(an)*rr,Z+Math.cos(an)*rr*Math.sin(sp)]:[cx+Math.cos(an)*rr*Math.sin(sp),hy+Math.sin(an)*rr,Z-Math.cos(an)*rr*Math.cos(sp)];
   MD.rod(a,f(0,a0),f(0,a1),0.022,4,r?shine:iron,i+r*10)}}}}
// A unit held fast in a web (web shot, sticky web): silk wound round it and pinned to the ground.
// An egg carried off from a nest (View3D.dm "egg"): held in front of its carrier, in its mother's colour.
function v3drawCarriedEggs(a){const fx=Math.sin(V3.yaw)*0.16,fz=Math.cos(V3.yaw)*0.16;for(const t of v3cat('egg',t=>t.egg)){if(!t.egg||t.dx==null||!v3visible(t))continue;
 const kd=t.key&&V3.disp.get(t.key),X=t.dx+fx,Z=-t.dy+fz,g=v3groundAt(t.dx,t.dy)+(kd&&kd.alt||0)+0.4,sd=t.x*13+t.y*7;
 if(t.egg==='spider'){MD.blob(a,X,g,Z,0.12,0.1,0.12,[0.9,0.9,0.86,1],sd,0.12);continue}
 const C={red:[0.62,0.16,0.11],red2:[0.72,0.33,0.1],black:[0.2,0.19,0.25],ice:[0.68,0.84,0.94],green:[0.24,0.47,0.21],sand:[0.74,0.62,0.4],blue:[0.18,0.33,0.64],zombie:[0.45,0.5,0.38]}[t.egg]||[0.62,0.16,0.11];
 MD.blob(a,X,g,Z,0.1,0.13,0.1,[C[0],C[1],C[2],1],sd,0.04);
 for(let k=0;k<6;k++){const an=k*2.39+MD.h(k,sd,58),y=g-0.06+(k%3)*0.05;MD.blob(a,X+Math.cos(an)*0.09,y,Z+Math.sin(an)*0.09,0.022,0.016,0.022,[C[0]*0.55,C[1]*0.55,C[2]*0.55,1],k+3,0.05)}}}
function v3drawWebbed(a){const silk=[0.94,0.94,0.9,1];for(const t of v3cat('webbed',t=>t.webbed)){if(!t.webbed||t.dx==null||!v3visible(t))continue;const X=t.dx,Z=-t.dy,kd=t.key&&V3.disp.get(t.key),g=v3groundAt(t.dx,t.dy)+(kd&&kd.alt||0),s=t.beast?(t.beast.size||1)*0.8:1,R=0.27*s,H=0.95*s,sd=t.x*13+t.y*7;
  for(let k=0;k<24;k++){const a0=k*0.78+MD.h(k,sd,41)*0.3,a1=a0+0.78,y0=0.08+k/24*H,y1=y0+H/24*1.4;MD.rod(a,[X+Math.cos(a0)*R,g+y0,Z+Math.sin(a0)*R],[X+Math.cos(a1)*R,g+y1,Z+Math.sin(a1)*R],0.008,3,silk,k)}
  for(let k=0;k<5;k++){const an=k/5*6.283+MD.h(k,sd,42),y=0.2+MD.h(k,sd,43)*H*0.6;MD.rod(a,[X+Math.cos(an)*R,g+y,Z+Math.sin(an)*R],[X+Math.cos(an)*(R+0.35*s),g+0.01,Z+Math.sin(an)*(R+0.35*s)],0.005,3,silk,k+30)}}}
function v3drawPartRing(a){const h=V3.hoverPart;if(!h)return;const [X,,Z]=v3world({dx:h.x,dy:h.y}),Y=v3groundAt(h.x,h.y)+0.06,r=0.44+0.05*Math.sin(performance.now()/1000*6),n=20,c=[1,0.42,0.15,1];
 for(let k=0;k<n;k++){const a0=k/n*6.283,a1=(k+1)/n*6.283;quad(a,[X+Math.cos(a0)*r,Y,Z+Math.sin(a0)*r],[X+Math.cos(a1)*r,Y,Z+Math.sin(a1)*r],[X+Math.cos(a1)*(r-0.08),Y,Z+Math.sin(a1)*(r-0.08)],[X+Math.cos(a0)*(r-0.08),Y,Z+Math.sin(a0)*(r-0.08)],[0,1,0],c)}}
function v3drawAim(a){const A=V3.aim,h=V3.hoverTile;if(!A||!h)return;const c=SPC[A.id]||[1,0.8,0.3],col=[c[0],c[1],c[2],0.42],t=performance.now()/1000,pu=0.85+0.15*Math.sin(t*6);
 for(const [x,y] of spTiles(A,h.x,h.y)){const [X,,Z]=v3world({dx:x,dy:y}),Y=v3groundAt(x,y)+0.07,r=0.47*pu;quad(a,[X-r,Y,Z+r],[X+r,Y,Z+r],[X+r,Y,Z-r],[X-r,Y,Z-r],[0,1,0],col)}
 // a leap or a throw: the tile it lands on outlined and the arc it flies on, from the caster (the owner, 10-28: "war leap is a
 // skill or spell and it shows a tile highlight and efected tiles with a arc")
 if(A.shape==='leap'||A.shape==='throw'){const dx=h.x-A.x,dy=h.y-A.y,l=Math.hypot(dx,dy)||1,R=A.range,cx=l<=R?h.x:Math.round(A.x+dx/l*R),cy=l<=R?h.y:Math.round(A.y+dy/l*R),L=Math.hypot(cx-A.x,cy-A.y);
  const [SX,,SZ]=v3world({dx:A.x,dy:A.y}),[TX,,TZ]=v3world({dx:cx,dy:cy}),SY=v3groundAt(A.x,A.y),TY=v3groundAt(cx,cy),top=Math.min(2.2,0.5+L*0.4),ca=[c[0],c[1],c[2],0.9],n=Math.max(8,Math.round(L*6));
  for(let k=1;k<n;k++){const q=k/n,X=SX+(TX-SX)*q,Z=SZ+(TZ-SZ)*q,Y=SY+(TY-SY)*q+0.35+Math.sin(q*Math.PI)*top,s=0.055;quad(a,[X-s,Y,Z+s],[X+s,Y,Z+s],[X+s,Y,Z-s],[X-s,Y,Z-s],[0,1,0],ca)}
  const Y=TY+0.09,r=0.5,w=0.08,cl=[Math.min(1,c[0]*1.2),Math.min(1,c[1]*1.2),Math.min(1,c[2]*1.2),0.95];   /* the landing tile's outline */
  quad(a,[TX-r,Y,TZ+r],[TX+r,Y,TZ+r],[TX+r,Y,TZ+r-w],[TX-r,Y,TZ+r-w],[0,1,0],cl);quad(a,[TX-r,Y,TZ-r+w],[TX+r,Y,TZ-r+w],[TX+r,Y,TZ-r],[TX-r,Y,TZ-r],[0,1,0],cl);
  quad(a,[TX-r,Y,TZ+r],[TX-r+w,Y,TZ+r],[TX-r+w,Y,TZ-r],[TX-r,Y,TZ-r],[0,1,0],cl);quad(a,[TX+r-w,Y,TZ+r],[TX+r,Y,TZ+r],[TX+r,Y,TZ-r],[TX+r-w,Y,TZ-r],[0,1,0],cl)}}
// A soft smoke puff texture, made here once (4 puffs side by side): blobs of white fading to clear at the edge,
// a little darker below. White, so each cloud tints it; kept in V3.tex so a new 3D view makes it again.
function v3smokeTex(){let e=V3.tex.get('#smoke');if(e)return e;const gl=V3.gl,W=256,H=64,px=new Uint8Array(W*H*4);
 for(let f=0;f<4;f++){const B=[];for(let k=0;k<9;k++){const an=MD.h(f,k,1)*6.283,rr=MD.h(f,k,2)*9;B.push([32+Math.cos(an)*rr,32+Math.sin(an)*rr*0.8,8+MD.h(f,k,3)*11])}
  for(let y=0;y<H;y++)for(let x=0;x<64;x++){let sm=0;for(const b of B){const d=Math.hypot(x+0.5-b[0],y+0.5-b[1])/b[2];if(d<1)sm+=(1-d*d)*(1-d*d)}
   const ed=Math.max(0,1-Math.hypot(x+0.5-32,y+0.5-32)/31),al=Math.min(1,sm*0.45)*Math.min(1,ed*2.5)*(0.85+0.15*MD.h(f*64+x,y,5)),sh=0.78+0.22*(1-y/H),i=(y*W+f*64+x)*4;
   px[i]=px[i+1]=Math.round(255*sh);px[i+2]=Math.round(255*Math.min(1,sh+0.02));px[i+3]=Math.round(255*al)}}
 const t=gl.createTexture();gl.bindTexture(gl.TEXTURE_2D,t);gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL,false);gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,W,H,0,gl.RGBA,gl.UNSIGNED_BYTE,px);
 gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.LINEAR);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.LINEAR);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);
 e={t,ok:true};V3.tex.set('#smoke',e);return e}
// Dragon breath, as the magic weapons' particles (art/enhance/breath64.py: rows of fire, frost, poison, 4 frames),
// added as light. Fighting (v3drawBeast's V3.breaths): a stream from the jaws bursting over the foe and round it.
// The F special (Specials.dm "breath"): a stream from the jaws to the spot aimed at, bursting over the area it catches.
// The pixel particles' elements, in the atlas's order (art/enhance/breath64.py ELEMENTS: three rows each).
const V3_PARTICLES=['fire','frost','poison','magma','sand','water','plague','holy','unholy','mind','acid','dust','web','spark'];
function v3breathFx(fxg,right,nowS){const camps=(V3.things||[]).filter(t=>t.m3==='station:campfire'&&v3visible(t)&&Math.abs(t.x-V3.cx)<30&&Math.abs(t.y-V3.cy)<24);if(!(V3.breaths||[]).length&&!(V3.fx||[]).some(f=>f.type==='special')&&!(V3.flameTiles||[]).length&&!camps.length)return;const e=v3tex('rb-breath-dragon.png');if(!(e&&e.ok))return;const list=[],ROWS=V3_PARTICLES.length*3;
 const put=(x,y,z,r,el,k,fade)=>{if(fade<=0.02)return;const v=Math.max(0,V3_PARTICLES.indexOf(el))*3+k%3,f=Math.floor(nowS*9+k*1.7)%4,u0=f/4+0.002,u1=(f+1)/4-0.002,v0=v/ROWS+0.002,v1=(v+1)/ROWS-0.002,c=[fade,fade,fade,1],rx=right[0]*r,rz=right[2]*r;
  quad(list,[x-rx,y-r*0.3,z-rz],[x+rx,y-r*0.3,z+rz],[x+rx,y+r*1.7,z+rz],[x-rx,y+r*1.7,z-rz],[0,0,0],c,[u0,v1,u1,v1,u1,v0,u0,v0])};
 for(const b of V3.breaths||[]){for(let k=0;k<14;k++){const p=(nowS*1.6+k/14+MD.h(b.seed,k,31)*0.05)%1,sp=0.04+p*0.4,j=q=>(MD.h(b.seed,k,q)-0.5)*sp;
   put(b.m[0]+(b.t[0]-b.m[0])*p+j(32),b.m[1]+(b.t[1]-b.m[1])*p+j(33)*0.5,b.m[2]+(b.t[2]-b.m[2])*p+j(34),0.26+p*0.45,b.el,k,1)}
  const bx=b.t[0]-b.m[0],bz=b.t[2]-b.m[2],bl=Math.hypot(bx,bz)||1,cx=b.t[0]+bx/bl*0.35,cz=b.t[2]+bz/bl*0.35;   // round the foe and on past it, away from the jaws
  for(let k=0;k<10;k++){const ph=(nowS*1.2+k/10)%1,an=k*2.4+MD.h(b.seed,k,35)*6.28,rr=0.15+0.6*Math.sqrt(MD.h(b.seed,k,36));
   put(cx+Math.cos(an)*rr,b.t[1]-0.6+ph*0.7,cz+Math.sin(an)*rr,0.32+0.22*Math.sin(ph*Math.PI),b.el,k+5,Math.sin(ph*Math.PI))}}
 const now=performance.now();for(const f of V3.fx||[]){if(f.type!=='special')continue;if(f.sp!=='breath'){v3specialParticles(f,put,now);continue}const age=(now-f.t)/1000;if(age>1.4)continue;
  const el=V3_PARTICLES.includes(f.el)?f.el:'fire',C=(V3.things||[]).find(u=>u.beast&&!u.beast.dead&&u.x===f.sx&&u.y===f.sy),[SX,,SZ]=v3world(C||{dx:f.sx,dy:f.sy}),[TX,,TZ]=v3world({dx:f.tx,dy:f.ty}),SY=v3groundAt(f.sx,f.sy),TY=v3groundAt(f.tx,f.ty);
  const dx=TX-SX,dz=TZ-SZ,l=Math.hypot(dx,dz)||1,ux=dx/l,uz=dz/l,jaw=C?C.beast.jaw||0.4:0.4,kc=C&&V3.disp.get(C.key),m=kc&&kc.mouthPt&&nowS-kc.mouthAt<0.2?kc.mouthPt:[SX+ux*jaw,SY+(C?C.beast.mouth||0.85:0.85),SZ+uz*jaw],t=[TX,TY+0.6,TZ],flow=age<0.9?1:Math.max(0,1-(age-0.9)/0.4);
  for(let k=0;k<18;k++){const p=(age*1.8+k/18)%1;if(age<p*0.3)continue;const sp=0.05+p*0.5,j=q=>(MD.h(f.sx+k,f.sy,q)-0.5)*sp;   // the stream, out of the jaws
   put(m[0]+(t[0]-m[0])*p+j(32),m[1]+(t[1]-m[1])*p+j(33)*0.5,m[2]+(t[2]-m[2])*p+j(34),0.26+p*0.45,el,k,flow)}
  if(age>0.25){const b=Math.min(1,(age-0.25)/0.3),fade=age>1.0?Math.max(0,1-(age-1.0)/0.4):1;   // the burst over the area it lands on
   for(let k=0;k<24;k++){const an=k*2.399+MD.h(f.sx,k,41)*0.5,rr=1.9*Math.sqrt(MD.h(f.sy,k,42))*b,ph=(age*1.3+k/24)%1;
    put(TX+Math.cos(an)*rr,TY+0.05+ph*0.9,TZ+Math.sin(an)*rr,0.32+0.22*Math.sin(ph*Math.PI),el,k+3,fade*(0.15+0.85*Math.sin(ph*Math.PI)))}}}
 // burning ground: tongues of the same fire, rising and fading (in place of the old cones)
 for(const f of V3.flameTiles||[]){const [X,,Z]=v3world(f),Y=v3groundAt(f.x,f.y),sd=f.x*7+f.y*13;
  for(let k=0;k<9;k++){const ph=(nowS*(0.9+MD.h(sd,k,71)*0.5)+k/9)%1,ox=(MD.h(sd,k,72)-0.5)*0.6,oz=(MD.h(sd,k,73)-0.5)*0.6,sw=Math.sin(nowS*4+k+sd)*0.05;
   put(X+ox*(1-ph*0.5)+sw,Y+0.02+ph*0.85,Z+oz*(1-ph*0.5),0.16+0.2*Math.sin(ph*Math.PI)*(1-ph*0.3),'fire',k,Math.min(1,Math.sin(ph*Math.PI)*1.3))}}
 // campfires: a small tongue of the same pixel fire over the logs
 for(const c of camps){const [X,,Z]=v3world(c),Y=(c.ly||v3groundAt(c.x,c.y))+0.1,sd=c.x*7+c.y*13;
  for(let k=0;k<7;k++){const ph=(nowS*(1.1+MD.h(sd,k,71)*0.5)+k/7)%1,ox=(MD.h(sd,k,72)-0.5)*0.26,oz=(MD.h(sd,k,73)-0.5)*0.26,sw=Math.sin(nowS*5+k+sd)*0.03;
   put(X+ox*(1-ph*0.6)+sw,Y+ph*0.5,Z+oz*(1-ph*0.6),0.11+0.15*Math.sin(ph*Math.PI)*(1-ph*0.3),'fire',k,Math.min(1,Math.sin(ph*Math.PI)*1.4))}}
 if(list.length){let fa=fxg.get('rb-breath-dragon.png');if(!fa){fa=[];fxg.set('rb-breath-dragon.png',fa)}fa.push(...list)}}
// The race specials' bursts, rings, trails and clouds as pixel particles (art/enhance/breath64.py); what is thrown
// or shot (a pot, a dart, an arrow, a web, a tongue) stays a 3D shape (v3drawSpecial), which also sets how long each lasts.
function v3specialParticles(f,put,now){const age=(now-f.t)/1000,sp=f.sp,[SX,,SZ]=v3world({dx:f.sx,dy:f.sy}),[TX,,TZ]=v3world({dx:f.tx,dy:f.ty}),SY=v3groundAt(f.sx,f.sy),TY=v3groundAt(f.tx,f.ty),dx=TX-SX,dz=TZ-SZ,l=Math.hypot(dx,dz)||1,ux=dx/l,uz=dz/l,h=(k,q)=>MD.h(f.sx*7+f.tx+k,f.sy*5+f.ty,q);
 const burst=(X,Y,Z,el,n,R,b,fade,rise)=>{for(let k=0;k<n;k++){const an=k*2.399+h(k,41)*0.5,rr=R*Math.sqrt(h(k,42))*b,ph=(age*1.3+k/n)%1;put(X+Math.cos(an)*rr,Y+0.05+ph*rise,Z+Math.sin(an)*rr,0.26+0.2*Math.sin(ph*Math.PI),el,k,fade*(0.2+0.8*Math.sin(ph*Math.PI)))}};
 const ring=(X,Y,Z,el,n,R,fade)=>{for(let k=0;k<n;k++){const an=k/n*6.283+h(k,43)*0.3;put(X+Math.cos(an)*R,Y+0.08+h(k,44)*0.25,Z+Math.sin(an)*R,0.3,el,k,fade)}};
 const trail=(el,p,n)=>{for(let k=0;k<n;k++){const q=Math.max(0,p-k*0.05);put(SX+dx*q+(h(k,45)-0.5)*0.2,SY+0.8+(TY-SY)*q+(h(k,46)-0.5)*0.2,SZ+dz*q+(h(k,47)-0.5)*0.2,0.18+0.05*k,el,k,1-k/n)}};
 if(sp==='mindblast'){if(age>1)return;const half=Math.PI/6,a0=Math.atan2(uz,ux),fade=age>0.7?1-(age-0.7)/0.3:1;   // a 60 degree wave of rings
  for(let k=0;k<26;k++){const off=(h(k,31)-0.5)*2*half,st=h(k,32)*0.35,p=Math.max(0,Math.min(1,(age-st)/0.55));if(p<=0)continue;const d=0.4+p*4*(0.75+0.25*h(k,33));put(SX+Math.cos(a0+off)*d,SY+0.75+h(k,34)*0.4,SZ+Math.sin(a0+off)*d,0.25+p*0.35,'mind',k,fade)}return}
 if(['web','dart','acid','pierce'].includes(sp)){const dur=0.12+l*0.04,p=Math.min(1,age/dur),el=sp==='web'?'web':sp==='dart'?'poison':sp==='acid'?'acid':'spark',hold=sp==='web'?0.8:0.3;
  if(age<=dur)trail(el,p,sp==='pierce'?7:5);
  else if(age<=dur+hold&&(sp!=='web'||f.el==='hit')){const b=(age-dur)/hold;burst(TX,TY+0.5,TZ,el,sp==='web'?12:10,0.6,Math.min(1,b*3),1-b,0.6)}return}
 if(sp==='charge'||sp==='leap'||sp==='shadowstep'){if(age>0.8)return;const fade=1-age/0.8;
  if(sp==='shadowstep'){burst(SX,SY+0.3,SZ,'unholy',14,0.6,1,fade,1.2);burst(TX,TY+0.3,TZ,'unholy',14,0.6,Math.min(1,age*3),fade,1.2);return}
  for(let k=0;k<10;k++){const q=Math.min(1,age/0.45)*k/9,arc=sp==='leap'?Math.sin(q*Math.PI)*Math.min(2,l*0.35):0;put(SX+dx*q,SY+0.25+arc*0.3+(TY-SY)*q,SZ+dz*q,0.22+0.1*h(k,48),'dust',k,fade*(0.4+0.6*q))}
  if(sp==='leap'&&age>0.35)ring(TX,TY,TZ,'dust',16,0.3+(age-0.35)*2.4,fade);return}
 if(sp==='slam'||sp==='sweep'){if(age>0.6)return;const R=(sp==='slam'?2.5:1.5)*Math.min(1,age/0.4),fade=1-age/0.6;ring(SX,SY,SZ,'dust',sp==='slam'?26:18,R,fade);if(sp==='slam')burst(SX,SY,SZ,'dust',10,R*0.8,1,fade,1.0);return}
 if(sp==='firepot'||sp==='plague'){const fl=(400+80*Math.hypot(f.tx-f.sx,f.ty-f.sy))/1000;if(age<fl||age>fl+1.0)return;const b=age-fl;   // the burst where it lands
  burst(TX,TY,TZ,sp==='firepot'?'fire':'plague',sp==='firepot'?22:26,sp==='firepot'?1.4:1.8,Math.min(1,b*4),1-b,sp==='firepot'?1.1:0.5)}}
function v3drawSpecial(a,f,now){const age=(now-f.t)/1000,[SX,,SZ]=v3world({dx:f.sx,dy:f.sy}),[TX,,TZ]=v3world({dx:f.tx,dy:f.ty}),SY=v3groundAt(f.sx,f.sy),TY=v3groundAt(f.tx,f.ty);
 const sp=f.sp,key=sp==='breath'?(f.el==='frost'?'frost':f.el==='poison'?'poison':'breath'):sp==='mindblast'?'mind':sp,c=SPC[key]||[1,1,1],C=k=>[c[0]*k,c[1]*k,c[2]*k,1];
 const dx=TX-SX,dz=TZ-SZ,l=Math.hypot(dx,dz)||1,ux=dx/l,uz=dz/l;
 if(sp==='fish'){if(age>0.9)return false;const p=Math.min(1,age/0.35),R=[SX+ux*0.25,SY+1.0,SZ+uz*0.25],tip=[SX+dx*p,SY+1.0+(TY-0.1-SY-1.0)*p+Math.sin(p*Math.PI)*0.6,SZ+dz*p];const n=8;for(let k=0;k<=n;k++){const q=k/n;MD.blob(a,R[0]+(tip[0]-R[0])*q,R[1]+(tip[1]-R[1])*q+Math.sin(q*Math.PI)*0.15,R[2]+(tip[2]-R[2])*q,0.012,0.012,0.012,[0.9,0.9,0.85,1],k,0.02)}
  if(age>0.35){const b=(age-0.35)/0.55,r=0.1+b*0.35;for(let k=0;k<8;k++){const an=k/8*6.283;MD.blob(a,TX+Math.cos(an)*r,TY-0.08,TZ+Math.sin(an)*r,0.05*(1-b)+0.01,0.03,0.05*(1-b)+0.01,[0.85,0.95,1,1],k,0.1)}}return true}
 if(sp==='catch'){if(age>0.7)return false;const q=age/0.7;MD.blob(a,SX+dx*q,SY+0.1+(TY+0.6-SY)*q+Math.sin(q*Math.PI)*0.9,SZ+dz*q,0.14,0.07,0.06,[0.62,0.68,0.74,1],f.sx,0.1);return true}
 if(sp==='breath')return age<=1.5;   // drawn with the breath particles (v3breathFx)
 if(sp==='mindblast')return age<=1;   // drawn with the pixel particles (v3specialParticles)
 if(['web','tongue','dart','acid','pierce'].includes(sp)){const dur=0.12+l*0.04;if(age>dur+(sp==='web'?0.8:sp==='tongue'?dur:0.3))return false;
  const p=Math.min(1,age/dur),back=sp==='tongue'&&age>dur?1-(age-dur)/dur:p,px=SX+dx*back,pz=SZ+dz*back,py=SY+0.8+(TY-SY)*back;
  if(sp==='tongue'){const n=8;for(let k=0;k<=n;k++){const q=k/n*back;MD.blob(a,SX+dx*q,SY+0.8+(TY-SY)*q,SZ+dz*q,0.05,0.05,0.05,C(1),k,0.05)}}
  else if(sp==='pierce'){for(let k=0;k<5;k++){const q=Math.max(0,p-k*0.04);MD.blob(a,SX+dx*q,SY+0.85,SZ+dz*q,0.07-k*0.01,0.04,0.07-k*0.01,C(1-k*0.12),k,0.05)}}
  else MD.blob(a,px,py,pz,sp==='dart'?0.05:0.12,sp==='dart'?0.05:0.1,sp==='dart'?0.05:0.12,C(1),f.sx,0.3);
  return true}
 if(['charge','leap','shadowstep'].includes(sp))return age<=0.8;   // dust and shadow: the pixel particles
 if(sp==='slam'||sp==='sweep')return age<=0.6;   // the dust ring: the pixel particles
 if(sp==='firepot'||sp==='plague'){const fl=(400+80*Math.hypot(f.tx-f.sx,f.ty-f.sy))/1000;if(age>fl+1.0)return false;
  if(age<fl){const q=age/fl;MD.blob(a,SX+dx*q,SY+0.9+(TY-SY)*q+4*(0.25*l+0.4)*q*(1-q),SZ+dz*q,0.12,0.12,0.12,sp==='firepot'?[0.55,0.35,0.2,1]:[0.45,0.4,0.3,1],f.sx,0.3);return true}
  return true}   // its burst: the pixel particles
 return false}

// Furniture, workshops, chests, wagons, traps and resources as 3D models (View3D.dm
// tags them with "m3"), coloured by their material like the original sprites.
// A gate's doors (v3gateArch): two leaves filling the way under the lintel or arch, hung at its middle. Timber: planks
// with a Z-brace and iron hinge straps; stone gate: oak leaves with iron bands and studs, a boarded tympanum filling
// the arch above them. Open, the leaves swing in against the passage walls (towards the inner side).
function v3gateDoors(a,t,X,Y,Z){const T=V3.terrain,i=t.x-T.x0,j=t.y-T.y0,kindAt=(p,q)=>v3kindAt(T.x0+p,T.y0+q),G=v3gateGeom(kindAt,i,j,t.x,t.y),ew=G.ew;
 const bx=(u0,u1,v0,v1,y0,y1,c)=>{const U0=Math.min(u0,u1),U1=Math.max(u0,u1),V0=Math.min(v0,v1),V1=Math.max(v0,v1);if(ew)boxr(a,X+U0,X+U1,Z+V0,Z+V1,Y+y0,Y+y1,c);else boxr(a,X+V0,X+V1,Z+U0,Z+U1,Y+y0,Y+y1,c)};
 const oak=G.wood?[0.46,0.31,0.18,1]:[0.4,0.27,0.15,1],iron=[0.22,0.21,0.22,1],W=G.wood?0.34:0.4,H=G.wood?1.52:1.3,inner=-(G.outerPos||1);
 if(t.open){for(const su of [-1,1]){const u=su*(W-0.04);bx(u-0.035,u+0.035,0,inner*W,0.02,H,oak);bx(u-0.04,u+0.04,inner*0.06,inner*(W-0.06),H*0.25,H*0.25+0.05,iron);bx(u-0.04,u+0.04,inner*0.06,inner*(W-0.06),H*0.75,H*0.75+0.05,iron)}}
 else{for(let q=0;q<8;q++){const u0=-W+q*W/4+0.004,u1=u0+W/4-0.008;bx(u0,u1,-0.04,0.04,0.02,H,MD.shade(oak,0.9+MD.h(t.x*8+q,t.y,97)*0.18))}
  bx(-0.006,0.006,-0.045,0.045,0.02,H,MD.shade(oak,0.5));
  if(G.wood){for(const su of [-1,1]){for(const y of [0.25,H-0.3])bx(su*0.04,su*(W-0.02),-0.05,0.05,y,y+0.08,MD.shade(oak,0.75));MD.rod(a,ew?[X+su*0.06,Y+0.33,Z+0.05]:[X+0.05,Y+0.33,Z+su*0.06],ew?[X+su*(W-0.05),Y+H-0.3,Z+0.05]:[X+0.05,Y+H-0.3,Z+su*(W-0.05)],0.03,4,MD.shade(oak,0.75),t.x+su);for(const y of [0.3,H-0.25])bx(su*(W-0.2),su*(W-0.02),-0.052,0.052,y,y+0.035,iron)}}
  else{for(const y of [0.28,0.72,1.12])bx(-W,W,-0.05,0.05,y,y+0.045,iron);for(let q=0;q<6;q++)for(const y of [0.5,0.92]){const u=-W+0.07+q*(2*W-0.14)/5;bx(u-0.015,u+0.015,-0.055,0.055,y-0.015,y+0.015,iron)}
   for(const su of [-1,1])MD.blob(a,ew?X+su*0.1:X+0.06,Y+0.75,ew?Z+0.06:Z+su*0.1,0.035,0.035,0.012,iron,t.x+su,0.1);
   // the tympanum: boards filling the arch above the leaves
   for(let k=0;k<8;k++){const u0=-0.4+k*0.1,u1=u0+0.1,um=(u0+u1)/2,top=1.3+Math.sqrt(Math.max(0,0.16-um*um));bx(u0,u1,-0.03,0.03,H,top,MD.shade(oak,0.7+MD.h(t.x+k,t.y,98)*0.1))}}}}
const OMAT={wood:[0.52,0.35,0.19],bamboo:[0.66,0.72,0.36],darkwood:[0.36,0.24,0.13],metal:[0.55,0.57,0.6],iron:[0.5,0.47,0.45],gold:[0.88,0.7,0.26],silver:[0.8,0.82,0.86],adamantium:[0.42,0.75,0.7],bone:[0.88,0.85,0.74],stone:[0.56,0.55,0.51],obsidian:[0.2,0.18,0.25],leather:[0.5,0.33,0.2]};
function v3obj(a,t,X,Y,Z){const m=t.m3,M=OMAT[t.mat]||OMAT.wood,c4=(k=1,c=M)=>[Math.min(1,c[0]*k),Math.min(1,c[1]*k),Math.min(1,c[2]*k),1];const d=t.dir||2,rot=(d===4||d===8);
 const B=(u0,u1,v0,v1,y0,y1,c)=>{if(rot)boxr(a,X+v0,X+v1,Z+u0,Z+u1,Y+y0,Y+y1,c);else boxr(a,X+u0,X+u1,Z+v0,Z+v1,Y+y0,Y+y1,c)};
 const bl=(u,v,y,rx,ry,rz,c,sd=1,rr=0.2)=>{const x=rot?X+v:X+u,z=rot?Z+u:Z+v;MD.blob(a,x,Y+y,z,rx,ry,rz,c,sd+t.x*3+t.y,rr)};
 const wood=c4(1,OMAT.wood),dark=c4(1,OMAT.darkwood),iron=c4(1,OMAT.metal),stoneC=c4(1,OMAT.stone);
 if(m==='door'&&V3.walkTiles&&V3.walkTiles.has(t.x+','+t.y)&&V3.terrain){v3gateDoors(a,t,X,Y,Z);return}
 if(m==='door'&&V3.terrain){const w=(p,q)=>{const k=v3kindAt(p,q);return !!k&&(k.kind==='built'||k.kind==='wall')},alongZ=w(t.x,t.y-1)&&w(t.x,t.y+1)&&!(w(t.x-1,t.y)&&w(t.x+1,t.y));if(alongZ!==rot)return v3obj(a,Object.assign({},t,{dir:alongZ?4:2}),X,Y,Z)}
 if(m==='door'&&t.mat==='stone'&&window.g3stoneDoor&&g3stoneDoor(a,t,X,Y,Z,rot,B,stoneC))return;   /* the climbing stone's rock (gear3d.js) */
 if(m==='door'){if(t.open){B(-0.46,-0.36,-0.06,0.06,0,1.35,dark);B(-0.44,-0.36,0.06,0.86,0.04,1.3,c4(1));}else{B(-0.46,0.46,-0.07,0.07,0.04,1.32,c4(1));B(-0.46,0.46,-0.075,0.075,0.32,0.38,dark);B(-0.46,0.46,-0.075,0.075,0.98,1.04,dark);bl(0.3,0.09,0.68,0.04,0.04,0.04,c4(1.1,OMAT.metal))}B(-0.5,-0.44,-0.09,0.09,0,1.42,dark);B(0.44,0.5,-0.09,0.09,0,1.42,dark);B(-0.5,0.5,-0.09,0.09,1.36,1.44,dark);return}
 if(m==='bed'){B(-0.42,0.42,-0.3,0.3,0.06,0.24,c4(0.9));B(-0.4,0.4,-0.27,0.27,0.24,0.34,[0.92,0.9,0.86,1]);B(-0.05,0.4,-0.28,0.28,0.3,0.37,t.mat==='gold'?[0.75,0.15,0.15,1]:[0.55,0.2,0.18,1]);B(-0.38,-0.2,-0.2,0.2,0.33,0.41,[0.97,0.96,0.93,1]);B(-0.46,-0.4,-0.32,0.32,0.06,0.62,c4(0.85));for(const [u,v] of [[-0.42,-0.3],[-0.42,0.26],[0.38,-0.3],[0.38,0.26]])B(u,u+0.04,v,v+0.04,0,0.08,c4(0.75));return}
 if(m==='bedroll'){B(-0.38,0.38,-0.2,0.2,0.01,0.09,[0.45,0.33,0.2,1]);bl(-0.36,0,0.1,0.08,0.08,0.21,[0.5,0.38,0.24,1]);return}
 if(m==='table'){B(-0.44,0.44,-0.44,0.44,0.54,0.62,c4(1));for(const [u,v] of [[-0.4,-0.4],[-0.4,0.34],[0.34,-0.4],[0.34,0.34]])B(u,u+0.06,v,v+0.06,0,0.55,c4(0.8));return}
 if(m==='chair'||m==='throne'){const big=m==='throne'?1.25:1,cush=t.mat==='bone'?[0.45,0.1,0.1,1]:[0.62,0.14,0.14,1];
  B(-0.22*big,0.22*big,-0.22*big,0.22*big,0.32*big,0.38*big,c4(1));if(m==='throne')B(-0.2*big,0.2*big,-0.2*big,0.2*big,0.38*big,0.42*big,cush);
  B(-0.22*big,0.22*big,-0.24*big,-0.18*big,0.32*big,(m==='throne'?1.5:0.95)*big,c4(0.92));for(const [u,v] of [[-0.21,-0.21],[-0.21,0.17],[0.17,-0.21],[0.17,0.17]])B(u*big,(u+0.04)*big,v*big,(v+0.04)*big,0,0.33*big,c4(0.8));
  if(m==='throne'){B(-0.3,-0.24,-0.25,0.25,0.42,0.72,c4(1));B(0.24,0.3,-0.25,0.25,0.42,0.72,c4(1));for(let k=-1;k<=1;k++)bl(k*0.15,-0.22,1.92,0.05,0.07,0.05,c4(1.15),k)}return}
 if(m==='beam'){const K=v3kindAt(t.x,t.y),hh=Math.max(1.6,Math.min(K&&K.roof?(K.ceil||2):2,2.2))-0.04,w=[0.47,0.31,0.17,1],d=[0.38,0.25,0.14,1];B(-0.07,0.07,-0.07,0.07,0,hh,w);B(-0.5,0.5,-0.08,0.08,hh-0.16,hh,d);B(-0.3,-0.06,-0.04,0.04,hh-0.5,hh-0.16,d);B(0.06,0.3,-0.04,0.04,hh-0.5,hh-0.16,d);return}
  if(m==='pillar'){B(-0.3,0.3,-0.3,0.3,0,0.14,c4(0.9));B(-0.2,0.2,-0.2,0.2,0.14,1.62,c4(1));B(-0.26,-0.18,-0.26,0.26,0.14,1.62,c4(0.92));B(-0.3,0.3,-0.3,0.3,1.62,1.76,c4(0.9));return}
 if(m==='statue'){B(-0.3,0.3,-0.3,0.3,0,0.32,c4(0.85));bl(0,0,0.62,0.17,0.28,0.13,c4(1),1,0.25);bl(0,0,1.02,0.11,0.12,0.11,c4(1.05),2,0.2);bl(-0.2,0,0.7,0.06,0.18,0.06,c4(0.95),3);bl(0.2,0,0.7,0.06,0.18,0.06,c4(0.95),4);return}
 if(m==='fence'){B(-0.5,-0.4,-0.05,0.05,0,0.7,c4(0.85));B(0.4,0.5,-0.05,0.05,0,0.7,c4(0.85));B(-0.5,0.5,-0.035,0.035,0.2,0.28,c4(1));B(-0.5,0.5,-0.035,0.035,0.5,0.58,c4(1));return}
 if(m==='post'){B(-0.06,0.06,-0.06,0.06,0,1.25,c4(0.9));B(-0.36,0.36,-0.045,0.045,0.82,0.9,c4(1));bl(0,0,1.32,0.13,0.14,0.13,[0.78,0.68,0.4,1],1,0.35);bl(0,0,0.68,0.17,0.26,0.14,[0.75,0.64,0.38,1],2,0.35);return}
 // Lairs (Buildings.dm): a sticky web strung across the way, a cobweb in a corner, a cocoon, eggs, a dragon's hoard.
 if(m==='web'||m==='cobweb'){const sol=(x,y)=>{const K=v3kindAt(x,y);return !!K&&['wall','built','block','tree'].includes(K.kind)},silk=[0.93,0.93,0.9,1],sd=t.x*31+t.y*17;
  const alongZ=sol(t.x,t.y+1)&&sol(t.x,t.y-1)&&!(sol(t.x-1,t.y)&&sol(t.x+1,t.y));let P=(u,y)=>alongZ?[X,Y+y,Z+u]:[X+u,Y+y,Z],cu=0,cy=0.78,ru=0.49,ry=0.68,a0=0,span=6.2832,n=10;
  if(m==='cobweb'){const w=sol(t.x-1,t.y),e=sol(t.x+1,t.y),no=sol(t.x,t.y+1);const zz=!w&&!e&&no;P=zz?(u,y)=>[X+u,Y+y,Z-0.46]:(u,y)=>[X+(e&&!w?0.46:-0.46),Y+y,Z+u];cu=-0.46;cy=1.42;ru=0.62;ry=0.62;a0=-1.5708;span=1.5708;n=6}
  const pts=[];for(let k=0;k<n;k++){const an=a0+(m==='web'?(k+MD.h(k,sd,71)*0.35)/n*span:k/(n-1)*span),c=Math.cos(an),s=Math.sin(an);pts.push([c,s]);MD.rod(a,P(cu,cy),P(cu+c*ru,cy+s*ry),0.008,3,silk,k)}
  for(const f of [0.22,0.42,0.62,0.82]){for(let k=0;k<(m==='web'?n:n-1);k++){const p=pts[k],q=pts[(k+1)%n],sag=0.03*f;MD.rod(a,P(cu+p[0]*ru*f,cy+p[1]*ry*f-sag),P(cu+q[0]*ru*f,cy+q[1]*ry*f-sag),0.005,3,silk,k)}}
  if(m==='web')for(let k=0;k<7;k++){const p=pts[Math.floor(MD.h(k,sd,72)*n)],f=0.3+MD.h(k,sd,73)*0.5,q=P(cu+p[0]*ru*f,cy+p[1]*ry*f);MD.blob(a,q[0],q[1],q[2],0.016,0.016,0.016,[0.96,0.98,1,1],k,0.05)}
  return}
 if(m==='cocoon'){const silk=[0.9,0.88,0.8,1],band=[0.82,0.79,0.7,1],sd=t.x*13+t.y*7;bl(0,0,0.4,0.2,0.4,0.18,silk,1,0.18);bl(0.04,0,0.8,0.14,0.13,0.13,silk,2,0.18);
  for(let k=0;k<3;k++)bl(0.01*k,0,0.26+k*0.2,0.205,0.018,0.188,band,k+3,0.1);
  for(let k=0;k<3;k++){const an=k/3*6.283+MD.h(k,sd,81);MD.rod(a,[X+Math.cos(an)*0.14,Y+0.08,Z+Math.sin(an)*0.12],[X+Math.cos(an)*0.27,Y+0.01,Z+Math.sin(an)*0.27],0.004,3,silk,k)}return}
 // a stolen dragon's egg in its mother's colours, flecked with darker scales, and the nests they lie in (Taming.dm)
 if(m==='beastegg'){let hs=0;for(const ch of String(t.id||t.ref||''))hs=(hs*31+ch.charCodeAt(0))|0;const du=(MD.h(hs,1,56)-0.5)*0.36,dv=(MD.h(hs,2,57)-0.5)*0.36;
  const C={red:[0.62,0.16,0.11],red2:[0.72,0.33,0.1],black:[0.2,0.19,0.25],ice:[0.68,0.84,0.94],green:[0.24,0.47,0.21],sand:[0.74,0.62,0.4],blue:[0.18,0.33,0.64],zombie:[0.45,0.5,0.38]}[t.mat]||[0.62,0.16,0.11],c=[C[0],C[1],C[2],1],dk=[C[0]*0.55,C[1]*0.55,C[2]*0.55,1];
  bl(du,dv,0.15,0.135,0.15,0.135,c,1,0.03);bl(du,dv,0.27,0.105,0.13,0.105,c,2,0.03);
  for(let k=0;k<16;k++){const y=0.07+(k%8)*0.035,an=k*2.39+MD.h(k,hs,58),r=y<0.2?0.13*Math.sqrt(Math.max(0.1,1-((y-0.15)/0.16)**2)):0.1*Math.sqrt(Math.max(0.1,1-((y-0.27)/0.14)**2));bl(du+Math.cos(an)*r,dv+Math.sin(an)*r,y,0.024,0.018,0.024,dk,k+3,0.05)}return}
 if(m==='beastnest'){const sd=t.x*17+t.y*5;
  if(t.mat==='spider'){const silk=[0.9,0.9,0.88,1];bl(0,0,0.022,0.42,0.012,0.4,[0.8,0.8,0.78,1],1,0.02);bl(0,0,0.07,0.2,0.07,0.2,silk,2,0.15);
   for(let k=0;k<8;k++){const an=k/8*6.283+MD.h(k,sd,61)*0.4;MD.rod(a,[X+Math.cos(an)*0.12,Y+0.08,Z+Math.sin(an)*0.12],[X+Math.cos(an)*0.55,Y+0.01,Z+Math.sin(an)*0.55],0.005,3,silk,k)}return}
  bl(0,0,0.022,0.46,0.012,0.42,[0.15,0.11,0.08,1],1,0.02);
  for(let k=0;k<11;k++){const an=k/11*6.283,cx=Math.cos(an)*0.42,cz=Math.sin(an)*0.4;
   if(k===2||k===7){const d=0.1;MD.rod(a,[X+cx-Math.sin(an)*d,Y+0.03,Z+cz+Math.cos(an)*d],[X+cx+Math.sin(an)*d,Y+0.03,Z+cz-Math.cos(an)*d],0.022,4,[0.86,0.82,0.7,1],k);continue}
   bl(cx,cz,0.04,0.07,0.05,0.06,MD.shade([0.42,0.4,0.37,1],0.8+MD.h(k,sd,62)*0.35),k,0.35)}
  for(let k=0;k<6;k++)bl((MD.h(k,sd,63)-0.5)*0.5,(MD.h(k,sd,64)-0.5)*0.5,0.012,0.03,0.008,0.03,[0.3,0.28,0.26,1],k+20,0.1);return}
 if(m==='egg'){const k0=t.x*11+t.y*5,e=t.mat||'';
  if(e==='spider'){const silk=[0.9,0.89,0.84,1];bl(0,0,0.2,0.24,0.2,0.24,silk,1,0.1);for(let k=0;k<7;k++){const an=k/7*6.283+MD.h(k,k0,91),r=k<6?0.15:0;bl(Math.cos(an)*r,Math.sin(an)*r,k<6?0.33:0.4,0.07,0.065,0.07,[0.97,0.95,0.86,1],k+2,0.05)}
   for(let k=0;k<5;k++){const an=k/5*6.283;MD.rod(a,[X+Math.cos(an)*0.2,Y+0.1,Z+Math.sin(an)*0.2],[X+Math.cos(an)*0.32,Y+0.01,Z+Math.sin(an)*0.32],0.004,3,silk,k)}return}
  if(e==='dragon'){for(let k=0;k<7;k++){const an=k/7*6.283;bl(Math.cos(an)*0.28,Math.sin(an)*0.28,0.06,0.09,0.07,0.08,MD.shade([0.5,0.48,0.44,1],0.85+MD.h(k,k0,92)*0.3),k,0.35)}
   bl(0,0,0.34,0.19,0.3,0.19,[0.42,0.16,0.12,1],1,0.06);for(let k=0;k<9;k++){const an=MD.h(k,k0,93)*6.283,y=0.16+MD.h(k,k0,94)*0.36,r=0.19*Math.sqrt(Math.max(0.15,1-((y-0.34)/0.3)**2));bl(Math.cos(an)*r,Math.sin(an)*r,y,0.035,0.035,0.035,[0.85,0.55,0.2,1],k+3,0.1)}return}
  if(e.startsWith('devourer')){bl(0,0,0.18,0.26,0.18,0.24,[0.45,0.14,0.2,1],1,0.3);bl(0.06,0.04,0.32,0.15,0.12,0.14,[0.55,0.2,0.26,1],2,0.3);for(let k=0;k<5;k++){const an=k/5*6.283;MD.rod(a,[X,Y+0.3,Z],[X+Math.cos(an)*0.3,Y+0.06,Z+Math.sin(an)*0.28],0.012,3,[0.3,0.08,0.12,1],k)}return}
  for(let k=0;k<3;k++){const an=k/3*6.283;bl(Math.cos(an)*0.11,Math.sin(an)*0.11,0.1,0.08,0.1,0.08,e==='lizardman'?[0.62,0.7,0.5,1]:[0.92,0.9,0.8,1],k,0.05)}return}
 if(m.startsWith('hoard')){const n=+m.slice(5)||0,gold=[0.88,0.7,0.26,1],sd=t.x*29+t.y*13,g=k=>MD.shade(gold,0.85+MD.h(k,sd,101)*0.3);
  bl(0,0,0.04,0.44+0.03*n,0.1+0.05*n,0.4+0.03*n,gold,1,0.3);bl(0.04,-0.03,0.12+0.05*n,0.26+0.02*n,0.08+0.05*n,0.24+0.02*n,g(1),2,0.3);
  for(let k=0;k<16+6*n;k++){const an=MD.h(k,sd,102)*6.283,r=MD.h(k,sd,103)*(0.48+0.03*n),h=Math.max(0,(0.1+0.1*n)*(1-r/(0.5+0.03*n)));bl(Math.cos(an)*r,Math.sin(an)*r,0.03+h,0.052,0.014,0.052,MD.shade([1,0.86,0.42,1],0.92+MD.h(k,sd,106)*0.16),k,0.05)}
  const gems=[[0.75,0.12,0.14,1],[0.2,0.62,0.3,1],[0.25,0.4,0.85,1],[0.85,0.85,0.95,1]];for(let k=0;k<3+n;k++){const an=MD.h(k,sd,104)*6.283,r=0.08+MD.h(k,sd,105)*0.25;bl(Math.cos(an)*r,Math.sin(an)*r,0.1+0.06*n*(1-r),0.04,0.04,0.04,gems[k%4],k+40,0.05)}
  MD.prism(a,X+0.22,Z+0.12,Y+0.06+0.04*n,Y+0.13+0.04*n,0.03,0.015,5,g(60),sd+1);MD.prism(a,X+0.22,Z+0.12,Y+0.13+0.04*n,Y+0.22+0.04*n,0.04,0.07,6,g(61),sd+2);
  if(n>=1){const b0=[X-0.18,Y+0.08+0.05*n,Z+0.05],b1=[X-0.02,Y+0.55+0.05*n,Z-0.12];MD.rod(a,b0,b1,0.018,4,[0.8,0.82,0.86,1],sd);MD.rod(a,[b1[0]-0.07,b1[1]-0.02,b1[2]+0.02],[b1[0]+0.07,b1[1]+0.02,b1[2]-0.02],0.016,4,g(62),sd+3);MD.rod(a,b1,[b1[0]+0.02,b1[1]+0.09,b1[2]-0.03],0.014,4,[0.42,0.25,0.14,1],sd+4)}
  return}
 // A dwarven pillar (Moria): a plinth, an eight-sided fluted shaft with carved bands, a capital
 // flaring out to meet a tunnel's rock roof (or capped, under the sky). Cut stone (alpha 0.99).
 // Power (Power.dm). t.mat 'on' while the piece's drive train turns: the water wheel and the windmill's sails turn
 // (their angle from the clock; the frames stand still), the bellows pump, the dynamo's runes glow. The water wheel
 // hangs over the water beside its bank (t.dir: the way to it), its axle running back into a gear house on the bank;
 // axles join the pieces beside them (link bits N1 S2 E4 W8) at hub height.
 if(m==='waterwheel'||m==='windmill'||m==='bellows'||m==='dynamo'||m.startsWith('axle')||m.startsWith('lift')){const on=t.mat==='on',tt=performance.now()/1000,w=[0.46,0.32,0.18,1],dk=[0.33,0.22,0.12,1],ir=[0.32,0.32,0.35,1],hy=0.3,sd=t.x*7+t.y*3;
  const R=(p,q,r,c,n=3)=>MD.rod(a,p,q,r,n,c,sd),add=(p,v,k)=>[p[0]+v[0]*k,p[1]+v[1]*k,p[2]+v[2]*k];
  // Lifts (Lifts.dm): the tiles are the original stair pair (the terrain leaves them to these). The lower end of a
  // lift up a cliff is a timber tower to the rock top beside it (v3peakTop); of a shaft up from the tunnels, a frame
  // to the ceiling; the upper end of a shaft is a head frame over the hole with its sheave; the top of a cliff lift a
  // plank landing. While it runs ('on') the cage rides up and down and the sheave turns.
  if(m.startsWith('lift')){const tw=[0.44,0.3,0.17,1],dk2=[0.3,0.2,0.11,1],rope=[0.7,0.62,0.45,1],plank=[0.5,0.36,0.22,1],q=0.42,post=0.045;
   const posts=(H)=>{for(const [u,v] of [[-q,-q],[q,-q],[-q,q],[q,q]])boxr(a,X+u-post,X+u+post,Z+v-post,Z+v+post,Y,Y+H,tw)},
    rails=(y)=>{boxr(a,X-q,X+q,Z-q-0.03,Z-q+0.03,y,y+0.06,dk2);boxr(a,X-q,X+q,Z+q-0.03,Z+q+0.03,y,y+0.06,dk2);boxr(a,X-q-0.03,X-q+0.03,Z-q,Z+q,y,y+0.06,dk2);boxr(a,X+q-0.03,X+q+0.03,Z-q,Z+q,y,y+0.06,dk2)},
    deck=(y)=>{boxr(a,X-0.47,X+0.47,Z-0.47,Z+0.47,y,y+0.05,plank);for(let k=-2;k<=2;k++)boxr(a,X+k*0.19-0.006,X+k*0.19+0.006,Z-0.47,Z+0.47,y+0.05,y+0.053,dk2)},
    sheave=(y,ph)=>{const c=[X,Y+y,Z],r=0.2;for(let k=0;k<8;k++){const a0=ph+k/8*6.2832,a1=ph+(k+1)/8*6.2832;R([c[0]+Math.cos(a0)*r,c[1]+Math.sin(a0)*r,c[2]],[c[0]+Math.cos(a1)*r,c[1]+Math.sin(a1)*r,c[2]],0.02,ir)}
     R([c[0]+Math.cos(ph)*r,c[1]+Math.sin(ph)*r,c[2]],[c[0]-Math.cos(ph)*r,c[1]-Math.sin(ph)*r,c[2]],0.015,ir);R([c[0],c[1],c[2]-0.08],[c[0],c[1],c[2]+0.08],0.03,ir)},
    cage=(y)=>{boxr(a,X-0.36,X+0.36,Z-0.36,Z+0.36,Y+y,Y+y+0.06,plank);for(const [u,v] of [[-0.34,-0.34],[0.34,-0.34],[-0.34,0.34],[0.34,0.34]])boxr(a,X+u-0.02,X+u+0.02,Z+v-0.02,Z+v+0.02,Y+y,Y+y+0.55,dk2);boxr(a,X-0.36,X+0.36,Z-0.36,Z+0.36,Y+y+0.52,Y+y+0.56,dk2)};
   const ride=(H)=>on?(Math.sin(tt*0.7)*0.5+0.5)*H:0;
   if(m==='liftcliff'||m==='liftshaft'){const H=m==='liftcliff'?Math.max(V3.STOREY,...[[1,0],[-1,0],[0,1],[0,-1]].map(([a1,b1])=>v3peakTop(t.x+a1,t.y+b1))):2.0,top=H+0.25;deck(Y+0.01);posts(top);for(let y=0.9;y<top-0.2;y+=0.9)rails(Y+y);rails(Y+top-0.06);
    const cy=ride(H-0.02);cage(cy+0.06);for(const [u,v] of [[-0.3,0],[0.3,0]])R([X+u,Y+cy+0.62,Z+v],[X+u*0.2,Y+top-0.05,Z+v],0.01,rope,3);
    if(m==='liftcliff')deck(Y+H-0.04);sheave(top+0.15,on?tt*1.4:0);boxr(a,X-0.25,X-0.1,Z+0.3,Z+0.48,Y+0.05,Y+0.35,dk2);return}
   if(m==='liftheadframe'){quad(a,[X-0.36,Y+0.012,Z+0.36],[X+0.36,Y+0.012,Z+0.36],[X+0.36,Y+0.012,Z-0.36],[X-0.36,Y+0.012,Z-0.36],[0,1,0],[0.03,0.03,0.03,1]);
    for(const [x0,x1,z0,z1] of [[-0.48,0.48,-0.48,-0.36],[-0.48,0.48,0.36,0.48],[-0.48,-0.36,-0.36,0.36],[0.36,0.48,-0.36,0.36]])boxr(a,X+x0,X+x1,Z+z0,Z+z1,Y,Y+0.08,plank);
    for(const u of [-0.42,0.42]){R([X+u,Y+0.08,Z-0.42],[X+u*0.25,Y+1.55,Z],0.04,tw,4);R([X+u,Y+0.08,Z+0.42],[X+u*0.25,Y+1.55,Z],0.04,tw,4)}
    R([X-0.15,Y+1.55,Z],[X+0.15,Y+1.55,Z],0.04,dk2,4);sheave(1.62,on?tt*1.4:0);R([X+0.2,Y+1.62,Z],[X+0.2,Y-0.4,Z],0.012,rope,3);
    if(on){const cy=-0.5+Math.sin(tt*0.7)*0.4;boxr(a,X-0.3,X+0.3,Z-0.3,Z+0.3,Y+cy,Y+cy+0.05,plank)}return}
   // liftlanding: the plank landing at the cliff top, a rail round it but on the cliff side, the rope's top
   deck(Y-0.03);for(const [u,v] of [[-q,-q],[q,-q],[-q,q],[q,q]])boxr(a,X+u-0.03,X+u+0.03,Z+v-0.03,Z+v+0.03,Y,Y+0.55,tw);rails(Y+0.5);sheave(0.75,on?tt*1.4:0);return}
  if(m==='waterwheel'){const wx=d===4?1:d===8?-1:0,wz=d===2?1:d===1?-1:(wx?0:1),W=[wx,0,wz],Pp=[-wz,0,wx],U=[0,1,0],C=[X+wx*0.62,Y+0.34,Z+wz*0.62],r=0.46,ph=on?tt*0.9:0.3;
   const at=(s,th,rr)=>add(add(add(C,W,s),Pp,Math.cos(th)*rr),U,Math.sin(th)*rr);
   boxr(a,X-0.17,X+0.17,Z-0.17,Z+0.17,Y,Y+0.44,dk);boxr(a,X-0.2,X+0.2,Z-0.2,Z+0.2,Y+0.44,Y+0.5,w);R([X,Y+hy,Z],add(C,W,0.22),0.035,ir,6);
   {const b=add(C,W,0.26);boxr(a,b[0]-0.04,b[0]+0.04,b[2]-0.04,b[2]+0.04,Y-0.3,Y+0.4,dk)}
   for(const s2 of [-0.13,0.13]){for(let k=0;k<8;k++)R(at(s2,ph+k/8*6.2832,r),at(s2,ph+(k+1)/8*6.2832,r),0.022,w);R(at(s2,ph,r),at(s2,ph+Math.PI,r),0.018,dk);R(at(s2,ph+Math.PI/2,r),at(s2,ph+Math.PI*1.5,r),0.018,dk)}
   for(let k=0;k<8;k++){const th=ph+(k+0.5)/8*6.2832,n=add([0,0,0],add(add([0,0,0],Pp,-Math.sin(th)),U,Math.cos(th)),1),c=MD.shade(w,0.9+MD.h(sd,k)*0.2),p0=at(-0.17,th,0.3),p1=at(0.17,th,0.3),p2=at(0.17,th,0.52),p3=at(-0.17,th,0.52);
    quad(a,p0,p1,p2,p3,n,c);quad(a,p3,p2,p1,p0,n.map(v=>-v),c)}return}
  if(m==='windmill'){B(-0.3,0.3,-0.3,0.3,0,0.5,c4(0.95,w));B(-0.24,0.24,-0.24,0.24,0.5,1.3,c4(1,w));B(-0.18,0.18,-0.18,0.18,1.3,1.75,c4(1.05,w));
   B(-0.26,0.26,-0.26,0.26,1.75,1.83,dk);B(-0.17,0.17,-0.17,0.17,1.83,1.95,dk);B(-0.09,0.09,0.24,0.31,0,0.55,dk);
   const H=[X,Y+1.55,Z+0.3],ph=on?tt*1.1:0.4;R([X,Y+1.55,Z+0.1],H,0.04,ir,6);MD.blob(a,H[0],H[1],H[2]+0.02,0.07,0.07,0.05,dk,sd,0.05);
   for(let k=0;k<4;k++){const al=ph+k*Math.PI/2,e=[Math.cos(al),Math.sin(al),0],q=[-Math.sin(al)*0.17,Math.cos(al)*0.17,0],h=[H[0],H[1],H[2]+0.01];
    R(H,add(H,e,0.95),0.022,dk);const p0=add(h,e,0.28),p1=add(h,e,0.95),p2=add(p1,q,1),p3=add(p0,q,1),c=[0.88,0.84,0.74,1];quad(a,p0,p1,p2,p3,[0,0,1],c);quad(a,p3,p2,p1,p0,[0,0,-1],MD.shade(c,0.85))}return}
  if(m==='bellows'){const pu=on?Math.sin(tt*4)*0.05:0;B(-0.3,0.3,-0.2,0.2,0,0.08,dk);B(-0.28,0.22,-0.18,0.18,0.08,0.18+pu*0.5,[0.42,0.27,0.16,1]);B(-0.26,0.12,-0.16,0.16,0.18+pu*0.5,0.28+pu,[0.38,0.24,0.14,1]);
   B(-0.3,0.26,-0.2,0.2,0.28+pu,0.32+pu,c4(1,w));const n0=rot?[X,Y+0.13,Z+0.22]:[X+0.22,Y+0.13,Z],n1=rot?[X,Y+0.1,Z+0.46]:[X+0.46,Y+0.1,Z];R(n0,n1,0.035,ir,5);
   const l0=rot?[X,Y+0.32+pu,Z-0.2]:[X-0.2,Y+0.32+pu,Z];R(l0,[l0[0],Y+hy+0.12,l0[2]],0.022,dk);return}
  if(m==='dynamo'){const st=[0.56,0.55,0.51,0.99],gl=on?0.75+0.25*Math.sin(tt*3):0,rune=on?[0.4+0.2*gl,0.85+0.15*gl,1,1]:[0.24,0.32,0.36,1];B(-0.36,0.36,-0.36,0.36,0,0.12,MD.shade(st,0.9));
   for(let k=0;k<3;k++){const y0=0.12+k*0.24;B(-0.28,0.28,-0.28,0.28,y0,y0+0.21,MD.shade(st,0.95+k*0.04));B(-0.295,0.295,-0.295,0.295,y0+0.21,y0+0.24,rune)}
   R([X,Y+0.5,Z],[X,Y+1.0,Z],0.05,ir,6);MD.blob(a,X,Y+1.06,Z,0.09,0.12,0.09,rune,sd,0.15);return}
  const L=+(m.slice(4)||0);let n=0;for(const [bit,dx,dz] of [[1,0,-1],[2,0,1],[4,1,0],[8,-1,0]])if(L&bit){n++;R([X,Y+hy,Z],[X+dx*0.5,Y+hy,Z+dz*0.5],0.035,w,6)}
  if(!n)R([X-0.4,Y+hy,Z],[X+0.4,Y+hy,Z],0.035,w,6);const ew=(L&12)&&!(L&3);
  for(const s2 of [-1,1]){const px=ew?X:X+s2*0.12,pz=ew?Z+s2*0.12:Z;boxr(a,px-0.03,px+0.03,pz-0.03,pz+0.03,Y,Y+hy+0.05,dk)}
  boxr(a,X-0.05,X+0.05,Z-0.05,Z+0.05,Y+hy-0.06,Y+hy+0.06,ir);return}
 // Mine carts (Carts.dm): a wooden tub on four iron wheels, heaped with ore when loaded; a cart stop: a plank
 // platform with a post and a sign.
 if(m==='minecart'||m==='minecartfull'){const w=[0.5,0.34,0.2,1],ir=[0.3,0.3,0.33,1];B(-0.33,0.33,-0.23,0.23,0.16,0.5,c4(1,w));B(-0.35,0.35,-0.25,0.25,0.46,0.52,c4(0.8,w));
  for(const y of [0.24,0.4])B(-0.335,0.335,-0.235,0.235,y,y+0.03,ir);for(const [u,v] of [[-0.22,-0.25],[0.22,-0.25],[-0.22,0.25],[0.22,0.25]])bl(u,v,0.12,0.11,0.11,0.04,ir,u*7+v*3,0.05);
  if(m==='minecartfull'){bl(0,0,0.52,0.28,0.12,0.19,[0.45,0.43,0.4,1],5,0.35);for(let k=0;k<4;k++)bl((MD.h(k,t.x,191)-0.5)*0.4,(MD.h(k,t.y,192)-0.5)*0.25,0.58,0.05,0.05,0.05,[0.7,0.55,0.3,1],k+9,0.1)}return}
 if(m==='cartstop'){const w=[0.5,0.36,0.22,1];B(-0.45,0.45,0.28,0.5,0,0.12,c4(0.9,w));B(-0.04,0.04,0.38,0.46,0,1.15,c4(0.8,w));B(-0.24,0.24,0.37,0.47,0.82,1.08,c4(1.05,w));B(-0.2,0.2,0.36,0.48,0.86,1.04,[0.85,0.8,0.65,1]);return}
 if(m==='dwarfpillar'){const K=v3kindAt(t.x,t.y),top=K&&K.roof?(K.ceil||2):1.95,s=[0.56,0.55,0.51,0.99],sd=t.x*17+t.y*7,S=k=>MD.shade(s,k);
  MD.prism(a,X,Z,Y,Y+0.12,0.31,0.29,8,S(0.8),sd);MD.prism(a,X,Z,Y+0.12,Y+0.22,0.25,0.22,8,S(0.9),sd+1);
  MD.prism(a,X,Z,Y+0.22,Y+top-0.46,0.18,0.165,8,S(1),sd+2);
  for(const f of [0.36,0.66]){const y=Y+0.22+(top-0.68)*f;MD.prism(a,X,Z,y,y+0.06,0.2,0.2,8,S(1.08),sd+3)}
  MD.prism(a,X,Z,Y+top-0.46,Y+top-0.13,0.17,0.34,8,S(0.95),sd+4);boxr(a,X-0.38,X+0.38,Z-0.38,Z+0.38,Y+top-0.13,Y+top,S(0.88));return}
 if(m==='stake'){const w=c4(1),dk=c4(0.72),rp=[0.62,0.56,0.32,1];   /* a stake driven into the ground (Captives.dm): a squared post, its head split, rope round it */
  B(-0.045,0.045,-0.045,0.045,0,0.58,w);B(-0.05,0.05,-0.05,0.05,0.56,0.6,dk);B(-0.006,0.006,-0.052,0.052,0.57,0.61,c4(0.5));B(-0.06,0.06,-0.06,0.06,0.36,0.41,rp);B(-0.058,0.058,-0.058,0.058,0.27,0.31,rp);return}
 if(m==='cage'){const H=t.caged?1.24:1,W=t.caged?0.47:0.42,F=t.caged?0.04:0.08,st=(2*W-0.08)/4;   /* someone shut in it (Captives.dm): tall and wide enough for them, standing inside */
  B(-W,W,-W,W,0,F,c4(0.85));B(-W,W,-W,W,H-0.08,H,c4(0.85));for(let k=0;k<5;k++){const u=-W+0.04+k*st;B(u,u+0.04,-W+0.02,-W+0.06,F,H-0.08,c4(1));B(u,u+0.04,W-0.06,W-0.02,F,H-0.08,c4(1));B(-W+0.02,-W+0.06,u,u+0.04,F,H-0.08,c4(1));B(W-0.06,W-0.02,u,u+0.04,F,H-0.08,c4(1))}return}
 if(m==='pit'){quad(a,[X-0.4,Y+0.02,Z+0.4],[X+0.4,Y+0.02,Z+0.4],[X+0.4,Y+0.02,Z-0.4],[X-0.4,Y+0.02,Z-0.4],[0,1,0],[0.06,0.05,0.04,1]);for(let k=0;k<8;k++){const an=k/8*6.283;MD.blob(a,X+Math.cos(an)*0.42,Y+0.03,Z+Math.sin(an)*0.42,0.08,0.03,0.08,[0.4,0.32,0.22,1],k,0.3)}return}
 if(m==='spikes'||m==='trap'){if(m==='trap'){B(-0.3,0.3,-0.3,0.3,0,0.05,c4(0.9));return}for(let k=0;k<6;k++){const u=(MD.h(k,t.x,41)-0.5)*0.6,v=(MD.h(k,t.y,42)-0.5)*0.6;bl(u,v,0.18,0.035,0.2,0.035,c4(1.05),k,0.05)}return}
 if(m==='ribtrap'){for(let k=0;k<5;k++){const v=-0.3+k*0.15;for(const s of [-1,1])bl(s*0.22,v,0.25,0.03,0.24,0.03,c4(1),k*2+s,0.05)}bl(0,0,0.02,0.32,0.03,0.36,c4(0.8),9,0.1);return}
 if(m==='sign'){B(-0.04,0.04,-0.04,0.04,0,0.9,c4(0.8));B(-0.32,0.32,-0.04,0.04,0.6,0.95,c4(1));return}
 if(m==='log'){for(let k=0;k<2;k++){const v=k?0.12:-0.12,y=k?0.27:0.12;B(-0.36,0.36,v-0.11,v+0.11,y-0.11,y+0.11,dark);B(-0.37,-0.35,v-0.09,v+0.09,y-0.09,y+0.09,[0.75,0.6,0.4,1]);B(0.35,0.37,v-0.09,v+0.09,y-0.09,y+0.09,[0.75,0.6,0.4,1])}return}
 if(m==='stone'){bl(-0.1,0,0.12,0.18,0.13,0.16,stoneC,1,0.4);bl(0.14,0.1,0.09,0.12,0.09,0.11,c4(0.9,OMAT.stone),2,0.4);return}
 if(m==='ore'){bl(0,0,0.13,0.2,0.14,0.18,c4(0.85,OMAT.stone),1,0.4);for(let k=0;k<4;k++)bl((MD.h(k,1,51)-0.5)*0.3,(MD.h(k,2,52)-0.5)*0.3,0.18+MD.h(k,3,53)*0.06,0.05,0.05,0.05,c4(1.15),k+2,0.1);return}
 if(m==='gem'){const gc=t.color?[...hexrgb(t.color),1]:[0.4,0.8,0.9,1];bl(0,0,0.12,0.09,0.12,0.09,gc,1,0.05);return}
 if(m==='ingot'){B(-0.18,0.18,-0.09,0.09,0,0.08,c4(1));B(-0.14,0.14,-0.07,0.07,0.08,0.12,c4(1.1));return}
 if(m==='bones'){for(let k=0;k<3;k++)bl((k-1)*0.12,(MD.h(k,4,61)-0.5)*0.2,0.04,0.2,0.035,0.035,c4(1),k,0.05);bl(0.05,0.15,0.08,0.09,0.08,0.09,c4(1.05),9,0.1);return}
 if(m==='chest'){B(-0.34,0.34,-0.24,0.24,0,0.36,t.mat==='wood'?wood:c4(0.9));B(-0.36,0.36,-0.26,0.26,0.36,0.46,t.mat==='wood'?c4(1.1,OMAT.wood):c4(1));B(-0.36,0.36,-0.27,0.27,0.17,0.21,t.mat==='wood'?iron:dark);B(-0.05,0.05,0.24,0.28,0.25,0.36,c4(1.2,OMAT.gold));return}
 if(m==='wagon'){B(-0.45,0.45,-0.32,0.32,0.28,0.6,wood);B(-0.47,0.47,-0.34,0.34,0.24,0.3,dark);for(const [u,v] of [[-0.3,-0.36],[-0.3,0.36],[0.3,-0.36],[0.3,0.36]])bl(u,v,0.2,0.2,0.2,0.06,dark,u*9+v,0.04);B(0.45,0.85,-0.03,0.03,0.3,0.36,dark);return}
 if(m.startsWith('station:')){const k=m.slice(8),R=t.half==='R';
  if(k==='campfire'){for(let i=0;i<8;i++){const an=i/8*6.283;MD.blob(a,X+Math.cos(an)*0.3,Y+0.06,Z+Math.sin(an)*0.3,0.08,0.06,0.08,stoneC,i,0.3)}B(-0.25,0.25,-0.04,0.04,0.04,0.12,dark);B(-0.04,0.04,-0.25,0.25,0.06,0.14,dark);return}   /* its flames are the pixel fire (v3breathFx), like burning ground */
  if(k==='altar'){// holy stone with a gold cloth, darker with each sacrifice; an Evil Altar black with a bloody top and red flames (HalfDemons.dm)
  const ev=t.mat==='evil',dk=ev?3:t.mat==='holy2'?2:t.mat==='holy1'?1:0,st=[[0.8,0.78,0.72],[0.6,0.53,0.51],[0.4,0.31,0.3],[0.15,0.12,0.13]][dk];
  B(-0.4,0.4,-0.3,0.3,0,0.62,c4(1,st));B(-0.44,0.44,-0.34,0.34,0.62,0.7,c4(1.1,st));B(-0.3,0.3,-0.2,0.2,0.7,0.72,ev?[0.42,0.04,0.03,1]:dk?[0.62,0.5,0.36,1]:[0.88,0.7,0.26,1]);
  for(const u of [-0.3,0.3])bl(u,0,0.8,0.03,0.08,0.03,ev?[1,0.3,0.12,1]:[0.95,0.9,0.75,1],u*5,0.05);return}
  const top=t.mat==='stone'?stoneC:wood;
  if(k==='forge'||k==='smelter'||k==='melter'){if(!R){B(-0.45,0.45,-0.4,0.4,0,0.7,stoneC);B(-0.3,0.3,-0.25,0.25,0.7,0.76,[0.95,0.45,0.12,1]);B(-0.18,0.18,-0.3,0.06,0.76,1.7,c4(0.85,OMAT.stone));bl(0,0.12,0.8,0.12,0.06,0.12,[1,0.65,0.25,1],3,0.2)}else{B(-0.18,0.18,-0.18,0.18,0,0.42,dark);B(-0.3,0.3,-0.12,0.12,0.42,0.56,iron);B(0.3,0.42,-0.06,0.06,0.48,0.56,iron)}return}
  if(k==='kitchen'){if(!R){B(-0.45,0.45,-0.35,0.35,0,0.62,wood);bl(0,0,0.76,0.2,0.14,0.2,iron,2,0.1);bl(0,0,0.86,0.15,0.03,0.15,[0.55,0.4,0.25,1],3,0.1)}else{B(-0.2,0.2,-0.2,0.2,0,0.6,c4(0.8));B(-0.21,0.21,-0.21,0.21,0.18,0.22,iron);B(-0.21,0.21,-0.21,0.21,0.44,0.48,iron);bl(0.3,0.25,0.15,0.15,0.15,0.13,[0.8,0.72,0.5,1],5,0.4)}return}
  if(k==='leatherworks'){if(!R){B(-0.42,-0.36,-0.04,0.04,0,1.1,dark);B(0.36,0.42,-0.04,0.04,0,1.1,dark);B(-0.42,0.42,-0.04,0.04,1.04,1.1,dark);B(-0.34,0.34,-0.02,0.02,0.25,1.0,c4(1,OMAT.leather))}else{bl(0,0,0.22,0.32,0.22,0.32,c4(0.8,OMAT.wood),1,0.1);B(-0.26,0.26,-0.26,0.26,0.4,0.42,[0.42,0.3,0.15,1])}return}
  if(k==='masonary'){if(!R){B(-0.42,0.42,-0.35,0.35,0,0.55,stoneC);bl(0.1,0,0.7,0.16,0.14,0.15,c4(1.05,OMAT.stone),3,0.35)}else{for(let i=0;i<3;i++)bl((i-1)*0.22,(MD.h(i,7,81)-0.5)*0.3,0.12,0.14,0.11,0.13,stoneC,i,0.45)}return}
  if(k==='bonecraft'){B(-0.42,0.42,-0.35,0.35,0.5,0.58,c4(1,OMAT.bone));for(const [u,v] of [[-0.38,-0.31],[-0.38,0.27],[0.34,-0.31],[0.34,0.27]])B(u,u+0.05,v,v+0.05,0,0.5,c4(0.85,OMAT.bone));for(let i=0;i<3;i++)bl((i-1)*0.18,0,0.62,0.12,0.03,0.03,c4(1,OMAT.bone),i,0.05);if(R)bl(0,0,0.75,0.12,0.12,0.12,c4(1.05,OMAT.bone),9,0.1);return}
  if(k==='gemcutter'){B(-0.4,0.4,-0.32,0.32,0.5,0.58,wood);for(const [u,v] of [[-0.36,-0.28],[-0.36,0.24],[0.32,-0.28],[0.32,0.24]])B(u,u+0.05,v,v+0.05,0,0.5,c4(0.8));if(!R){B(-0.03,0.03,-0.2,0.2,0.58,0.95,iron);bl(0,0,0.95,0.06,0.2,0.2,stoneC,4,0.05)}else for(let i=0;i<3;i++)bl((i-1)*0.15,0,0.65,0.05,0.07,0.05,[[0.9,0.2,0.3,1],[0.3,0.8,0.4,1],[0.4,0.6,1,1]][i],i,0.05);return}
  if(k==='potionstation'||k==='poisonstation'){const fl=k==='poisonstation'?[0.45,0.85,0.3,1]:[0.4,0.6,1,1];B(-0.42,0.42,-0.33,0.33,0.52,0.6,wood);for(const [u,v] of [[-0.38,-0.29],[-0.38,0.25],[0.34,-0.29],[0.34,0.25]])B(u,u+0.05,v,v+0.05,0,0.52,c4(0.8));for(let i=0;i<(R?2:3);i++){const u=(i-1)*0.2;bl(u,0,0.7,0.07,0.1,0.07,fl,i,0.05);B(u-0.02,u+0.02,-0.02,0.02,0.78,0.86,[0.85,0.85,0.9,1])}return}
  // carpentry and any other bench
  if(!R){B(-0.45,0.45,-0.32,0.32,0.5,0.6,top);for(const [u,v] of [[-0.4,-0.28],[-0.4,0.23],[0.35,-0.28],[0.35,0.23]])B(u,u+0.06,v,v+0.06,0,0.5,c4(0.8));B(0.2,0.3,-0.3,-0.2,0.6,0.75,iron)}else{B(-0.3,-0.24,-0.25,0.25,0,0.45,dark);B(0.24,0.3,-0.25,0.25,0,0.45,dark);B(-0.36,0.36,-0.11,0.11,0.45,0.67,dark)}return}
}
// Everything else lying about: its own sprite as a chunky token on the ground.
function v3card(addTex,a,t,X,Y,Z,tk){const s=0.4,an=MD.h(t.x,t.y,91)*0.8-0.4,ca=Math.cos(an)*s,sa=Math.sin(an)*s,y=Y+0.05;
 // the item's own picture lying on the ground (turned a little), with a soft shadow under it
 const P=(u,v,yy)=>[X+u*ca-v*sa,yy,Z+u*sa+v*ca];const top=[];quad(top,P(-1,1,y),P(1,1,y),P(1,-1,y),P(-1,-1,y),[0,1,0],[1,1,1,1],[0,1,1,1,1,0,0,0]);addTex(tk,top);
 MD.blob(a,X+0.03,Y+0.012,Z+0.03,0.22,0.008,0.18,[0.12,0.14,0.08,1],t.x+t.y,0.05)}

// The moving surface of water and lava (their basins are part of the terrain mesh).
const V3_STILL=[0,0,0,0,0,0,0,0];
// A waterfall: [x0,z0,top,tx,ty,3,foot,x1,z1,nx,nz] from v3meshes, a mountain lake's water pouring over the lip of its
// stone face to the water below, in pale streaks running down it, whiter at the foot, where white water spreads over
// the pool. The sheet hugs the rock and runs a little past its ends, so where a step turns a corner the sheets meet
// and no stone shows through (the owner, 10-27: "i can still see thrugh it").
function v3fall(a,e,t,va){const x0=e[0],z0=e[1],yt=e[2],tx=e[3],ty=e[4],yb=e[6],x1=e[7],z1=e[8],nx=e[9],nz=e[10],H=yt-yb,R=8,Cn=8,sd=MD.h(tx,ty,5)*6.28;
 // drawn as water (vertex alpha 0.915: the water shading, lit like the lake, no ground texture laid on it)
 const P=(u,v)=>{const o=0.02+0.05*Math.sqrt(v),q=-0.09+u*1.18;return [x0+(x1-x0)*q+nx*o,yt-H*v,z0+(z1-z0)*q+nz*o]};
 const K=(u,v)=>{const f=0.5+0.5*Math.sin(u*21+sd),g=0.5+0.5*Math.sin(v*H*4.2-t*7.5+u*9+sd),w=Math.min(1,0.22+0.5*f*g+0.4*v*v);return [0.3+0.66*w,0.5+0.48*w,0.7+0.29*w,0.915]};
 for(let r=0;r<R;r++)for(let c=0;c<Cn;c++){const u0=c/Cn,u1=(c+1)/Cn,v0=r/R,v1=(r+1)/R,A=P(u0,v0),B=P(u1,v0),D=P(u1,v1),E=P(u0,v1),ca=K(u0,v0),cb=K(u1,v0),cd=K(u1,v1),ce=K(u0,v1);
  if(va){a.v(A[0],A[1],A[2],nx,0.3,nz,0,0,ca[0],ca[1],ca[2],0.915);a.v(B[0],B[1],B[2],nx,0.3,nz,0,0,cb[0],cb[1],cb[2],0.915);a.v(D[0],D[1],D[2],nx,0.3,nz,0,0,cd[0],cd[1],cd[2],0.915);a.v(A[0],A[1],A[2],nx,0.3,nz,0,0,ca[0],ca[1],ca[2],0.915);a.v(D[0],D[1],D[2],nx,0.3,nz,0,0,cd[0],cd[1],cd[2],0.915);a.v(E[0],E[1],E[2],nx,0.3,nz,0,0,ce[0],ce[1],ce[2],0.915)}
  else quad4(a,A,B,D,E,[nx,0.3,nz],ca,cb,cd,ce)}
 // the foot: white water spreading out over the pool and fading into it (no spray balls: the owner, 10-27)
 const fw=0.4+0.1*Math.sin(t*2.3+sd),fy=yb+0.012,F0=[0.86,0.92,0.97,0.915],F1=[0.2,0.4,0.56,0.915];
 for(let c=0;c<Cn;c++){const u0=c/Cn,u1=(c+1)/Cn,w0=fw*(0.8+0.4*MD.h(tx+c,ty,44)),w1=fw*(0.8+0.4*MD.h(tx+c+1,ty,44)),b0=0.04,
   A=[x0+(x1-x0)*u0+nx*b0,fy,z0+(z1-z0)*u0+nz*b0],B=[x0+(x1-x0)*u1+nx*b0,fy,z0+(z1-z0)*u1+nz*b0],D=[x0+(x1-x0)*u1+nx*(b0+w1),fy,z0+(z1-z0)*u1+nz*(b0+w1)],E=[x0+(x1-x0)*u0+nx*(b0+w0),fy,z0+(z1-z0)*u0+nz*(b0+w0)];
  quad4(a,A,B,D,E,[0,1,0],F0,F0,F1,F1)}
}
function v3drawLiquids(a){const L=V3.waterList;if(!L||!L.length)return;const t=performance.now()/1000,h=0.5,C=V3.liqC||(V3.liqC=new Float32Array(16)),va=a instanceof VA;
 // [X,Z,Y,tx,ty,type (0 water, 1 lava, 2 swamp),corners at the shore (bits as v3cornerMask),under a bank,a river's flow at
 // its four corners (x,z each, tiles a second; the shader carries the ripples on it)]; each corner's colour into C (no arrays per tile)
 const col=(o,x,z,s,lava)=>{const w=Math.sin(t*1.5+x*0.9+z*0.6)*0.5+Math.sin(t*2.3-x*0.4+z*1.1)*0.5;if(lava===1){const g=0.5+0.5*Math.sin(t*1.1+x*0.7-z*0.5);C[o]=0.85+0.15*g;C[o+1]=0.3+0.25*g*g;C[o+2]=0.06;C[o+3]=1;return}
  const k=s?1:0;if(lava===2){C[o]=0.13+0.14*k+w*0.02;C[o+1]=0.2+0.12*k+w*0.03;C[o+2]=0.12+0.07*k+w*0.035}else{C[o]=0.1+0.12*k+w*0.02;C[o+1]=0.27+0.18*k+w*0.03;C[o+2]=0.45+0.03*k+w*0.035}C[o+3]=0.915};
 for(let n=0;n<L.length;n++){if(L[n][5]===3){v3fall(a,L[n],t,va);continue}const e=L[n],X=e[0],Z=e[1],Y=e[2],tx=e[3],ty=e[4],lava=e[5],lm=e[6],bank=e[7],y=Y-(lava===1?0.05:0.12);
  col(0,X-h,Z+h,lm&1,lava);col(4,X+h,Z+h,lm&2,lava);col(8,X+h,Z-h,lm&4,lava);col(12,X-h,Z-h,lm&8,lava);
  if(va){const F=e[8]||V3_STILL;a.v(X-h,y,Z+h,0,1,0,F[0],F[1],C[0],C[1],C[2],C[3]);a.v(X+h,y,Z+h,0,1,0,F[2],F[3],C[4],C[5],C[6],C[7]);a.v(X+h,y,Z-h,0,1,0,F[4],F[5],C[8],C[9],C[10],C[11]);a.v(X-h,y,Z+h,0,1,0,F[0],F[1],C[0],C[1],C[2],C[3]);a.v(X+h,y,Z-h,0,1,0,F[4],F[5],C[8],C[9],C[10],C[11]);a.v(X-h,y,Z-h,0,1,0,F[6],F[7],C[12],C[13],C[14],C[15])}
  else quad4(a,[X-h,y,Z+h],[X+h,y,Z+h],[X+h,y,Z-h],[X-h,y,Z-h],[0,1,0],[C[0],C[1],C[2],C[3]],[C[4],C[5],C[6],C[7]],[C[8],C[9],C[10],C[11]],[C[12],C[13],C[14],C[15]]);if(bank)continue;
  const ph=(t*0.35+MD.h(tx,ty,97))%1;if(lava===1&&ph<0.12){const r=(lava===1?0.09:0.05)*(1-ph/0.12),u=(MD.h(tx,ty,98)-0.5)*0.7,v=(MD.h(tx,ty,99)-0.5)*0.7;MD.blob(a,X+u,y+0.015,Z+v,r*1.6,r*0.25,r,lava===1?[1,0.85,0.4,1]:[0.85,0.93,1,1],tx+ty,0.1)}}}
function renderOverlay(m){warStrip(m);hudIcons(m);{const sl=document.querySelector('.speedctl');if(sl&&sl.hidden!==!!m.speedLocked)sl.hidden=!!m.speedLocked}{const on=m.online,r=$('tbOnlineRes');if(r){if(r.hidden!==!on)r.hidden=!on;if(on){text($('tbOnline'),on.n);const tt='Players online in this world: '+on.n+(on.max?' (room for '+on.max+')':'');if(r.title!==tt)r.title=tt}}}{const sp=m.speed==null?1:m.speed;document.querySelectorAll('.speedctl button').forEach(b=>{const on=Number(b.dataset.value)===sp;b.classList.toggle('active',on);b.setAttribute('aria-pressed',String(on))});const pb=$('pausebanner');if(pb&&pb.hidden!==(sp!==0))pb.hidden=sp!==0}v3hits(m.hits);V3.claims=Array.isArray(m.claims)?m.claims:[];V3.siegeWalls=Array.isArray(m.siegeWalls)?m.siegeWalls:[];V3.aim=m.aim||null;document.body.classList.toggle('aiming',!!m.aim);v3specials(m.specialFx);V3.cine=m.cine||null;if(m.cine&&m.cine.panel&&!document.body.classList.contains('panel-open')){document.body.classList.add('panel-open');queueRegions()}document.body.classList.toggle('cine',!!(m.cine&&!m.cine.hud));if(!overlayHost)return;{const fg=$('setFog'),fr=$('setFogRow');if(fg&&typeof m.fog==='number'&&document.activeElement!==fg)fg.checked=!!m.fog;if(fr)fr.hidden=!m.fogHost;}   /* fog of war (Fog.dm): on by default, the host's switch */{const R=m.raids||{},sd=$('setDiff');if(sd&&R.difficulty&&document.activeElement!==sd&&sd.value!==R.difficulty)sd.value=R.difficulty;const h=$('setDiffHint');if(h)text(h,'World setting, saved with the world.'+(R.nextSeasonMin!=null?' Next season in about '+R.nextSeasonMin+' min'+(R.difficulty==='peaceful'?'.':' (and a raid on your settlement).'):'')+(R.raiders?' '+R.raiders+' raiders on the march.':''))}{const P=m.play||{},b=$('lockbar');const cb=$('camChase');if(cb)cb.setAttribute('aria-pressed',String(!!(P.lock||(P.mode==='hero'&&P.follow))));if(b.hidden!==!P.lock)b.hidden=!P.lock;if(P.lock){let bottom=0;for(const el of [$('topbar'),$('attack')]){if(el&&!el.hidden){const r=el.getBoundingClientRect();if(r.height>0)bottom=Math.max(bottom,r.bottom)}}const y=Math.round(bottom+12)+'px';if(b.style.top!==y)b.style.top=y}if(P.lock)text($('lockname'),'Camera follows '+String(P.lockName||'').replace(/^\{[^}]*\}\s*/,''))}const units=arr(m.units),play=m.play||{},heroU=play.mode==='hero'?units.find(u=>u.ref===play.hero):null,picked=units.filter(u=>u.selected),sel=picked.length?picked:heroU?[heroU]:[];
 $('pmHero').classList.toggle('on',play.mode==='hero');$('pmVillage').classList.toggle('on',play.mode!=='hero');
 text($('tbDate'),seasonLine(m));const nUnits=hcUnitN(m);text($('tbUnits'),nUnits);{const s=$('tbUnits').nextElementSibling;if(s)text(s,nUnits===1?'person':'people')}text($('tbIdle'),m.idle);{const vb=document.querySelector('nav [data-value=village]'),n=Number(m.idle)||0,bd=n>99?'99+':n>0?String(n):'';if(vb&&vb.dataset.badge!==bd){vb.dataset.badge=bd;vb.dataset.tip='Village\nPeople, land, board and log'+(n?'\n'+n+' idle: Next idle (bottom left) finds them':'');vb.removeAttribute('title')}}text($('tbSel'),m.selection);text($('tbPos'),m.x+', '+m.y+' · '+(['Surface','Caves','Sky','Depths'][m.z-1]||'L'+m.z));
 const CL=hcListRows(m,'company'),runits=CL?CL.rows:units;text($('rosterCount'),CL?nUnits:units.length);const list=$('rosterList');const want=runits.map(u=>u.ref).join('|');if(list.dataset.refs!==want){list.dataset.refs=want;list.replaceChildren();runits.forEach(u=>{const b=button('','select',u.ref);b.className='member';b.innerHTML='<img alt=""><div><div class="nm"></div><div class="st"></div><div class="hpbar"><em class="trl"></em><span></span></div></div>';list.append(b)})}
 hcRosterSync(list,runits,CL);   // only the rows on screen kept up to date (hud-craft, 10-25)
 {const s=units.find(u=>u.selected)||units[0],k=matFor(s&&s.race);if(document.body.dataset.mat!==k)document.body.dataset.mat=k}
 const hf=$('heroframe');let html,key;
 if(sel.length===1){const u=sel[0];key='h'+JSON.stringify([u.ref,u.name,u.level,u.race,u.kind,u.role,u.job,u.jobrow,u.weapon,u.portrait,play,picked.length]);
  html='<div class="hf"><div class="pw"><div class="ring">'+(u.portrait?'<img alt="" src="'+esc(u.portrait)+'">':'')+'</div><b class="lvb" title="Level">'+esc(u.level)+'</b></div><div><div class="hn" title="'+esc(ownName(u.name))+'">'+esc(String(u.name||'').replace(/^\{[^}]*\}\s*/,''))+'</div><div class="lv"'+(u.role&&u.role!=='Settler'?' title="'+esc('Best skill: '+u.role+' '+u.skill)+'"':'')+'>'+esc((u.kind?u.kind+' ':'')+(u.race||''))+(u.jobrow?' · '+esc(u.jobrow):u.job&&u.job!=='manual'?' · '+esc(roleLabel(u)):'')+'</div>'+heroBar('hp','Health',u.hp,u.maxhp)+heroBar('food','Food',u.fullness,u.maxfullness)+heroBar('rest','Rest',u.energy,100)+(u.mood!=null?heroBar('mood','Mood',u.mood,100):'')+'</div></div>'+heroTabsHtml()+'<div data-pane="overview"><div class="hb"><button data-do="tab" data-value="units">Character</button><button data-do="tab" data-value="orders">Orders</button><button data-do="tab" data-value="work">Work</button></div>'+(play.mode==='hero'?'<div class="hb">'+(u.ref===play.hero?'<button data-do="follow">'+(play.follow?'Stop following':'Follow')+'</button>'+(picked.length?'<button data-do="action" data-value="clear" title="Deselect; work continues (Shift+Space)">Deselect</button>':'<button data-do="select" data-value="'+esc(u.ref)+'">Select</button>'):'<button data-do="makehero" data-value="'+esc(u.ref)+'">Make my hero</button>')+'</div>':'')+'</div>'}
 else{const many=sel.length>1,refs=sel.map(u=>u.ref).join(','),same=f=>{const v=sel.map(f);return v.length&&v.every(x=>x===v[0])?v[0]:null};
  const BD=m.band,bx=(k,f,b)=>BD?(BD[k]==='#mixed'||BD[k]==null?null:(b?!!BD[k]:BD[k])):same(f);   // a selection over the server's cap: its summary (HudView.dm)
  const st=bx('style',u=>u.skills&&u.skills.style),dm=bx('mode',u=>u.defense&&u.defense.mode),nl=bx('nonlethal',u=>!!u.nonlethal,1),op=bx('ownPace',u=>!!u.ownPace,1),nm=n=>esc(String(n||'').replace(/^\{[^}]*\}\s*/,''));
  key='v'+JSON.stringify([nUnits,m.idle,m.selection,sel.map(u=>[u.ref,u.portrait]),m.formation,st,dm,nl,op,arr(m.formationGrid).length>0,m.formationGroup||0,m.selFly||0]);
  html='<div class="hn">'+(sel.length?'Your band':'Your settlement')+'</div><div class="facts">'+(sel.length?'<b>'+(m.selection||sel.length)+'</b> selected · ':'')+'<b>'+nUnits+'</b> in company · <b>'+esc(m.idle)+'</b> idle</div>';
  const hb='<div class="hb"><button data-do="action" data-value="all" title="Select all (Ctrl+A)\nEvery unit in your company.">Select all</button><button data-do="idle" title="Next idle (F1)\nSelects a unit with nothing to do and takes the camera to it.">Next idle</button><button data-do="tab" data-value="work" title="Settlement\nWork, zones and stockpiles.">Settlement</button></div>';
  if(!many)html+=hb;
  else{const row=(label,h,n)=>'<div class="hfrow"><span>'+label+'</span><div style="--n:'+n+'">'+h+'</div></div>';
   const bulk=(kind,v,on,l,tip)=>'<button data-do="villagebulk" data-value="'+esc(kind+'|'+v+'|'+refs)+'" aria-pressed="'+on+'" title="'+esc(tip)+'">'+l+'</button>';
   // Band: who is in it (click a face to take just that unit), and the usual ways to pick units
   html+='<div data-pane="band"><div class="group">'+sel.slice(0,24).map(u=>'<button class="gpick" data-do="select" data-value="'+esc(u.ref)+'" title="'+esc(nm(u.name)+'\n'+(u.role||'')+' · '+(u.hp!=null?u.hp+' / '+u.maxhp+' health':'')+'\nClick: select only them · double-click: the camera goes to them')+'">'+(u.portrait?'<img alt="" src="'+esc(u.portrait)+'">':esc(nm(u.name).slice(0,2)))+'<i class="ghp"><em></em></i></button>').join('')+(sel.length>24?'<span>+'+(sel.length-24)+'</span>':'')+'</div>'+hb+'</div>';
   // Orders: how they walk together (patrol and supplies join this tab below)
   html+='<div data-pane="orders">'+row('Formation',[['keep','Keep','Each keeps its place around the group.'],['line','Line','Side by side.'],['column','Column','One behind another.'],['box','Box','A tight square.']].map(([v,l,tip])=>'<button data-do="formation" data-value="'+v+'" aria-pressed="'+(m.formation===v)+'" title="'+esc(l+'\n'+tip)+'">'+l+'</button>').join(''),4)+
    row('Layout','<button data-do="formation" data-value="custom" aria-pressed="'+(m.formation==='custom')+'"'+(arr(m.formationGrid).length?'':' disabled')+' title="'+esc(arr(m.formationGrid).length?'Mine\nYour own formation from Army › Formations: the group lines up like that on the tile you click, each by what it holds (fighters front, archers and casters where you put them).':'Mine\nYour own formation: build one in Army › Formations first.')+'">Mine</button><button data-do="tab" data-value="army" title="'+esc('Edit\nArmy › Formations: build your own formations.')+'">Edit</button>',2)+
    (m.formationGroup?'<p class="hfnote">Control group '+esc(m.formationGroup)+' keeps its own formation.</p>':'')+
    row('March',[['group',false,'With the group','Sent together, they march at the slowest one’s pace and arrive as a group.'],['own',true,'Own pace','Each walks at its own speed.']].map(([v,on,l,tip])=>'<button data-do="unitpace" data-value="'+esc(refs+'|'+v)+'" aria-pressed="'+(op===on)+'" title="'+esc(l+'\n'+tip.replace(' (Formations.dm)',''))+'">'+l+'</button>').join(''),2)+
    // Fly (Flying.dm "flylevel"): the selected flyers a height up or down together, only while one of them is flying
    (Array.isArray(m.selFly)?row('Fly',[['up',0,'Higher','Fly higher\nThe selected flyers go up a height; from their highest, up to the Sky level.','None of them can fly higher.'],['down',1,'Lower','Fly lower\nThe selected flyers go down a height; from the Sky level, down to the surface.','None of them can fly lower.']].map(([v,i,l,tip,no])=>'<button data-do="flylevel" data-value="'+v+'"'+(m.selFly[i]>0?'':' disabled')+' title="'+esc(tip+(m.selFly[i]>0?'':'\n'+no))+'">'+l+'</button>').join(''),2):'')+'</div>';
   // Combat: the same choices as one unit's Combat tab, for the whole band (pressed when all agree)
   html+='<div data-pane="combat">'+row('Fight',bulk('lethal','lethal',nl===false,'Lethal <b class="hcg hcg-sword">⚔</b>','Lethal\nThey fight to kill.')+bulk('lethal','nonlethal',nl===true,'Non-lethal <b class="hcg hcg-fist">✋</b>','Non-lethal\nThey knock enemies and animals out instead of killing them, so you can capture or tame them. They don’t shoot or throw.'),2)+
    row('Style',[['accurate','Accurate','Attack'],['aggressive','Aggressive','Strength'],['defensive','Defensive','Defence'],['controlled','Controlled','Attack, Strength and Defence']].map(([v,l,tr])=>bulk('style',v,st===v,l,l+'\nMelee trains '+tr+'.')).join(''),2)+
    row('Stance',[['assist','Help nearby','Join a fight when a tribe member within 8 tiles is attacked.'],['self','Defend self','Fight back only when attacked.'],['off','No response','Never fight on their own.']].map(([v,l,tip])=>bulk('defense',v,dm===v,l,l+'\n'+tip)).join(''),2)+'</div>';
   html+='<div class="hftabs" role="tablist" aria-label="Band card">'+GROUP_TABS.map(([v,l,tip])=>'<button type="button" role="tab" data-gftab="'+v+'" aria-selected="'+(groupTab===v)+'" title="'+esc(l+'\n'+tip)+'">'+l+'</button>').join('')+'</div>'}}
 const ev=play.succession;if(ev){key+=JSON.stringify(ev);html='<div class="succ"><b>'+esc(ev.dead)+' has died.</b>'+(ev.heir?'<span>Long live '+esc(ev.heirName)+', '+esc(ev.why)+', now head of House '+esc(ev.house)+'.</span>'+(ev.claim?'<span class="atwar">'+esc(ev.claim)+' No one can be crowned until it’s settled.</span>':'')+'<div class="hb">'+(ev.claim?'<button data-do="tab" data-value="realm">Realm tab</button>':'<button data-do="crownheir">Crown as '+esc(ev.title)+'</button>')+'<button data-do="select" data-value="'+esc(ev.heir)+'">Select</button><button data-do="succession_ok">Close</button></div>':'<span>House '+esc(ev.house)+' has no one left to lead it.</span><div class="hb"><button data-do="succession_ok">Close</button></div>')+'</div>'+html}
 if(sel.length&&picked.length){const pd=m.patrol;key+='|p'+JSON.stringify(pd);html+=pd?'<div class="groupctl patrolctl"><span>Patrol</span><b>'+arr(pd.points).length+' point'+(arr(pd.points).length===1?'':'s')+' · click the ground</b><button data-do="patrolfinish">Finish</button><button data-do="patrolcancel">Cancel</button></div>':'<div class="groupctl"><span>Patrol</span><button data-do="patrolstart" title="Click points in order, then Finish: the selected units walk the loop">Set route</button>'+(picked.some(u=>u.patrolling)?'<button data-do="patrolclear">Stop patrol</button>':'')+'</div>'}
 const liveBars=()=>{if(sel.length!==1)return;const u=sel[0];const set=(cls,label,v,max)=>{const b=hf.querySelector('.bar.'+cls);if(!b)return;const w=pct(v,max)+'%',sp=b.querySelector('span'),it=b.querySelector('i'),tr=b.querySelector('.trl');if(sp&&sp.style.width!==w)sp.style.width=w;if(tr&&tr.style.width!==w)tr.style.width=w;if(cls==='hp')b.classList.toggle('low',max>0&&v>0&&v/max<0.25);barSet(it,label,v,max)};
  set('hp','Health',u.hp,u.maxhp);set('food','Food',u.fullness,u.maxfullness);set('rest','Rest',u.energy,100);
  const mb=hf.querySelector('.bar.mood');if(mb&&u.mood!=null){const sp=mb.querySelector('span'),it=mb.querySelector('i'),w=Math.max(0,Math.min(100,u.mood))+'%';if(sp.style.width!==w)sp.style.width=w;{const tr=mb.querySelector('.trl');if(tr&&tr.style.width!==w)tr.style.width=w}const t=(u.moodName||'Mood')+' '+u.mood;if(it.textContent!==t)it.textContent=t;
   mb.dataset.m=u.mood>=60?'good':u.mood>=30?'ok':'bad';const tip=arr(u.thoughts).map(x=>(x[1]>0?'+':'')+x[1]+'  '+x[0]).join('\n');if(mb.title!==tip)mb.title=tip||'No strong feelings'}};
 if(key!==heroKey){heroKey=key;hf.innerHTML='<button class="hfmore" type="button" title="More orders: formation, stance, patrol, unload" aria-expanded="'+hf.classList.contains('more')+'">More</button>'+html}
 liveBars();
 // a red pip on the Health tab while a body part is injured or worse, so a wound shows without opening it (hud-craft)
 {const ht=hf.querySelector('[data-hftab=health]');if(ht){const H=sel.length===1?sel[0].health:null,on=!!H&&arr(H.parts).some(p=>!p.na&&partSev(p)>=2);if(ht.classList.contains('hcpip')!==on)ht.classList.toggle('hcpip',on)}}
 // each band portrait's health strip, updated live like the Company list (hud-craft)
 {const byRef=new Map(sel.map(u=>[u.ref,u]));hf.querySelectorAll('.group .gpick').forEach(b=>{const u=byRef.get(b.dataset.value),e=b.querySelector('.ghp em');if(!u||!e)return;const p=u.maxhp>0?Math.max(0,Math.min(1,u.hp/u.maxhp)):1,w=Math.round(p*100)+'%';if(e.style.width!==w)e.style.width=w;b.classList.toggle('hurt',p<0.5);b.classList.toggle('low',p<0.25)})}
 hf.dataset.unitref=sel.length===1?sel[0].ref:'';
 // What anyone looking at the unit notices (Speech.dm): drunk, feverish, bandaged, a grafted Orc arm.
 {let lk=hf.querySelector('.hflook');const u=sel.length===1?sel[0]:null,t=u&&u.look?'Looks '+u.look+'.':'';
  if(!u){if(lk)lk.remove()}else{if(!lk){lk=document.createElement('div');lk.className='hflook';const h=hf.querySelector('.hf');if(h)h.after(lk);else hf.append(lk)}if(lk.textContent!==t)lk.textContent=t}}
  // The unit's warnings (Starving, Bleeding badly…) as a row of chips under its bars, on every tab, like debuffs on a
  // unit frame (hud-craft); before, they showed only on the Character page and the Village roster.
  {let wn=hf.querySelector('.hfwarn');const u=sel.length===1?sel[0]:null,W=u?arr(u.warnings):[],h=W.map(w=>'<span>'+esc(w)+'</span>').join('');
   if(!W.length){if(wn)wn.remove()}else{if(!wn){const col=hf.querySelector('.hf>div:last-child');if(col){wn=document.createElement('div');wn.className='hfwarn';col.append(wn)}}if(wn&&wn.dataset.h!==h){wn.dataset.h=h;wn.innerHTML=h}}}
 // Bag bar: the shown unit's carried items, always in reach (click = original choices, double-click = use, drag = give).
 {let bar=hf.querySelector('.bagbar');const u=sel.length===1?sel[0]:null;const items=u?arr(u.items):[];
  if(!bar&&u){bar=document.createElement('div');bar.className='bagbar';hf.append(bar)}
  // Same carried items share one slot with a count; equipped items stay single.
  const groups=[];const by=new Map();for(const i of items){const eq=/Equip/i.test(i.state||'');const k=eq?'eq:'+i.ref:(i.name+'|'+(i.icon||''));let g=by.get(k);if(!g){g={first:i,refs:[],eq};by.set(k,g);groups.push(g)}g.refs.push(...(i.refs&&i.refs.length?i.refs:[i.ref]))}   /* the server sends a kind once with its refs (HUD.dm) */
  if(bar){const bk=JSON.stringify(groups.map(g=>[g.refs,g.first.icon,g.first.state]));if(bar.dataset.k!==bk){bar.dataset.k=bk;bar.replaceChildren();groups.slice(0,16).forEach(g=>{const i=g.first;const b=bagButton(i.ref,g.refs);b.className='bagslot'+(g.eq?' eq':'');if(i.useon)b.dataset.useon='1';b.title=itemLabel(i.name)+(g.refs.length>1?' ×'+g.refs.length:'')+(i.state?' '+i.state:'')+(i.info?'\n'+i.info:'')+'\nClick: '+(i.useon?'hold it, then click what it is for · Right-click: choices':'choices')+' · Drag: give'+(g.refs.length>1?' all (Shift-drag: one)':'');if(i.icon){const im=document.createElement('img');im.alt='';im.src=i.icon;b.append(im)}else b.append(document.createTextNode((i.name||'?').slice(0,3)));if(g.refs.length>1){const c=document.createElement('i');c.className='bagcount';c.textContent=g.refs.length;b.append(c)}bar.append(b)});if(!items.length&&u)bar.innerHTML='<small>Empty bag</small>'}bagCombineMark()}}   /* outlined: what the held thing combines with (010-script.js) */
  {const sb=hf.querySelector('.skillbar');if(sb)sb.remove()}
  // Alchemy: the unit's brew, the ingredients it carries, and what it can do with them.
  {let ax=hf.querySelector('.alchemy');const u1=sel.length===1?sel[0]:null,A0=u1&&u1.alchemy,A=A0&&(A0.brew||A0.bottles)?A0:null;   /* only once it can brew (a bottle or a brew): ingredients alone just said "needs an Empty Bottle" on every new unit (hud-craft, from playtest) */
   if(!A){if(ax)ax.remove()}else{if(!ax){ax=document.createElement('div');ax.className='alchemy';(hf.querySelector('.skillbar')||hf.querySelector('.bagbar')||hf.lastChild).after(ax)}
    const k=JSON.stringify([u1.ref,A]);if(ax.dataset.k!==k){ax.dataset.k=k;const v=(a,arg)=>esc(u1.ref+'|'+a+'|'+(arg||''));
     let h='<div class="alchead"><b>Alchemy</b>'+(A.brew?' <span>'+esc(A.brew)+' · '+A.temp+'°</span>':A.bottles?' <span>'+A.bottles+' empty bottle'+(A.bottles>1?'s':'')+'</span>':' <span>needs an Empty Bottle</span>')+'</div>';
     if(A.contents&&A.contents.length)h+='<div class="alcmix">'+A.contents.map(c=>'<i style="background:'+esc(c.color)+'"></i>'+esc(c.units)+' '+esc(c.name)).join(' · ')+'</div>';
     if(A.ingredients.length&&(A.brew||A.bottles))h+='<div class="alcrow"><span>Add:</span>'+A.ingredients.map(g=>'<button data-do="brew" data-value="'+v('add',g.ref)+'" title="'+esc(g.name)+' → 5 '+esc(g.gives)+'">'+esc(g.gives)+'</button>').join('')+'</div>';
     h+='<div class="alcrow">';if(A.water&&(A.brew||A.bottles))h+='<button data-do="brew" data-value="'+v('water')+'">Draw water</button>';
     if(A.brew&&A.contents.length){h+='<button data-do="brew" data-value="'+v('heat')+'"'+(A.fire?'':' disabled title="Stand within 2 tiles of a campfire"')+'>'+(A.heating?'Heating…':'Heat')+'</button><button data-do="brew" data-value="'+v('drink')+'">Drink</button><button data-do="brew" data-value="'+v('throw')+'"'+(A.throwing?' aria-pressed="true"':'')+'>'+(A.throwing?'Click a tile…':'Throw')+'</button><button data-do="brew" data-value="'+v('empty')+'">Empty</button>'}
     h+='</div>';ax.innerHTML=h}}}
  // Cauldron: shown when the unit stands beside one.
  {let cx=hf.querySelector('.cauldronbox');const u1=sel.length===1?sel[0]:null,C=u1&&u1.cauldron;
   if(!C){if(cx)cx.remove()}else{if(!cx){cx=document.createElement('div');cx.className='alchemy cauldronbox';(hf.querySelector('.alchemy')||hf.querySelector('.skillbar')||hf.querySelector('.bagbar')||hf.lastChild).after(cx)}
    const k=JSON.stringify([u1.ref,C]);if(cx.dataset.k!==k){cx.dataset.k=k;const v=(a,arg)=>esc(u1.ref+'|'+a+'|'+(arg||''));
     let h='<div class="alchead"><b>Cauldron</b> <span>'+C.total+' / '+C.max+' · '+C.temp+'°'+(C.lit?' · burning ('+C.fuel+' min of wood)':C.fuel>0?' · fire out ('+C.fuel+' min of wood)':' · no fire')+'</span></div>';
     if(C.contents.length)h+='<div class="alcmix">'+C.contents.map(c=>'<i style="background:'+esc(c.color)+'"></i>'+esc(c.units)+' '+esc(c.name)).join(' · ')+'</div>';
     if(C.ingredients.length)h+='<div class="alcrow"><span>Add:</span>'+C.ingredients.map(g=>'<button data-do="cauldron" data-value="'+v('add',g.ref)+'" title="'+esc(g.name)+' → 5 '+esc(g.gives)+'">'+esc(g.gives)+'</button>'+(g.count>1?'<button data-do="cauldron" data-value="'+v('addall',g.ref)+'" title="All '+g.count+'">×'+g.count+'</button>':'')).join('')+'</div>';
     h+='<div class="alcrow"><button data-do="cauldron" data-value="'+v('water')+'">Pour water</button><button data-do="cauldron" data-value="'+v('fuel')+'"'+(C.wood?'':' disabled title="Carry wood"')+'>Add wood ('+C.wood+')</button>'+(C.fuel>0?'<button data-do="cauldron" data-value="'+v('light')+'">'+(C.lit?'Douse':'Light')+'</button>':'')+
       (C.contents.length?'<button data-do="cauldron" data-value="'+v('bottle')+'"'+(C.bottles?'':' disabled title="Carry Empty Bottles"')+'>Fill bottles ('+C.bottles+')</button><button data-do="cauldron" data-value="'+v('empty')+'">Empty</button>':'')+'</div>';
     cx.innerHTML=h}}}
  // Market stall beside the unit: buy from another realm's merchant, or set your own prices.
  {let mx=hf.querySelector('.marketbox');const u1=sel.length===1?sel[0]:null,K=u1&&u1.market;
   if(!K){if(mx)mx.remove()}else{if(!mx){mx=document.createElement('div');mx.className='alchemy marketbox';(hf.querySelector('.alchemy')||hf.querySelector('.skillbar')||hf.querySelector('.bagbar')||hf.lastChild).after(mx)}
    const k=JSON.stringify([u1.ref,K,u1.keeperMake]);if(mx.dataset.k!==k){mx.dataset.k=k;const v=(a,arg)=>esc(u1.ref+'|'+a+'|'+(arg||''));
     let h='<div class="alchead"><b>'+(K.own?'Your market':esc(K.seller)+"'s market")+'</b> <span>'+(K.merchant?esc(K.merchant):'no merchant here')+' · treasury '+K.coins+' coins</span></div>';
     if(K.own)h+='<div class="alcrow"><span>Prices '+K.markup+'%</span><button data-do="market" data-value="'+v('markup','-10')+'">−10%</button><button data-do="market" data-value="'+v('markup','10')+'">+10%</button></div><p class="hint">Give the merchant goods to sell: drag them onto it. Other realms buy here with their coins.</p>';
     else if(K.wares.length)h+='<div class="alcrow"><span>Buy:</span>'+K.wares.map(w=>'<button data-do="market" data-value="'+v('buy',w.ref)+'"'+(K.coins<w.price?' disabled title="Not enough coins"':'')+'>'+esc(w.name)+' · '+w.price+'</button>').join('')+'</div>';
     else h+='<p class="hint">Nothing for sale right now.</p>';
     if(K.own&&u1.keeperMake&&u1.keeperMake.stall)h+='<div class="alcrow">'+keeperMakeBtn(u1,'stall')+'</div>';   // QuestKeepers.dm
     mx.innerHTML=h}}}
  // Food pot or stall beside the unit (FoodSupply.dm): its food, the pot's fire, and what can be done.
  {let fx=hf.querySelector('.foodbox');const u1=sel.length===1?sel[0]:null,F=u1&&u1.food;
   if(!F){if(fx)fx.remove()}else{if(!fx){fx=document.createElement('div');fx.className='alchemy foodbox';(hf.querySelector('.alchemy')||hf.querySelector('.skillbar')||hf.querySelector('.bagbar')||hf.lastChild).after(fx)}
    const k=JSON.stringify([u1.ref,F]);if(fx.dataset.k!==k){fx.dataset.k=k;const v=(a,arg)=>esc(u1.ref+'|'+a+'|'+(arg||''));const fb=(a,label,arg,extra)=>'<button data-do="foodsupply" data-value="'+v(a,arg)+'"'+(extra||'')+'>'+label+'</button>';
     let h='<div class="alchead"><b>'+(F.own?esc(F.name):esc(F.owner||'Nobody')+'’s '+esc(String(F.name).toLowerCase()))+'</b> <span>'+F.n+' / '+F.max+(F.kind==='pot'?' · '+F.temp+'°'+(F.lit?' · burning ('+F.fuel+' min of wood)':F.fuel>0?' · fire out ('+F.fuel+' min of wood)':' · no fire'):'')+'</span></div>';
     if(F.suspect)h+='<div class="foodwarn">'+(F.suspect>1?'Poisoned: ':'Suspect: ')+esc(F.why||'')+'. Villagers won’t eat here until it is emptied'+(F.suspect>1?'':' or inspected clean')+'.</div>';
     h+=F.contents.length?'<div class="alcmix">'+F.contents.map(c=>esc(c.n)+' × '+esc(c.name)).join(' · ')+'</div>':'<p class="hint">'+(F.kind==='pot'?'Empty. Cooks fill it; over a wood fire raw meat stews without burning, and hot stew fills more.':'Bare. Farmers and cooks lay food out here; villagers eat here and take a piece along.')+'</p>';
     let row='';
     if(F.own){row+=fb('add','Put in food ('+F.add+')','',F.add?'':' disabled title="Carry food"');if(F.eat)row+=fb('eat','Eat');
      if(F.kind==='pot')row+=fb('fuel','Add wood ('+F.wood+')','',F.wood?'':' disabled title="Carry wood"')+(F.fuel>0?fb('light',F.lit?'Douse':'Light'):'');
      row+=fb('inspect','Inspect','',' title="Check the food for poison: cooking and poison skill help"')+(F.n||F.suspect?fb('empty',F.kind==='pot'?'Empty the pot':'Clear the stall','',' title="Throw the food out"'):'')}
     else{row+=fb('inspect','Inspect');if(F.war)row+=arr(F.poisons).map(q=>fb('poison','Slip in '+esc(q.kind)+' ('+q.dose+')',q.ref,' title="'+esc(q.name)+': poison this food in secret. Villagers nearby may see it done."')).join('')}
     h+='<div class="alcrow">'+row+'</div>';
     if(!F.own&&!F.war)h+='<p class="hint">Their food can only be poisoned while your realms are at war.</p>';else if(!F.own&&!arr(F.poisons).length)h+='<p class="hint">Carry a poison to slip it in: Toxic, Poison, a poison gland or root, or a poison brew.</p>';
     fx.innerHTML=h}}}
  // Doctor's stall beside the unit (Doctor.dm): herbs, remedies, and what this unit needs.
  {let dx=hf.querySelector('.clinicbox');const u1=sel.length===1?sel[0]:null,K=u1&&u1.clinic;
   if(!K){if(dx)dx.remove()}else{if(!dx){dx=document.createElement('div');dx.className='alchemy clinicbox';(hf.querySelector('.foodbox')||hf.querySelector('.alchemy')||hf.querySelector('.skillbar')||hf.querySelector('.bagbar')||hf.lastChild).after(dx)}
    const k=JSON.stringify([u1.ref,K]);if(dx.dataset.k!==k){dx.dataset.k=k;const v=(a,arg)=>esc(u1.ref+'|'+a+'|'+(arg||''));const cb=(a,label,arg,extra)=>'<button data-do="clinic" data-value="'+v(a,arg)+'"'+(extra||'')+'>'+label+'</button>';
     let h='<div class="alchead"><b>'+(K.own?'Doctor’s stall':esc(K.owner||'Nobody')+'’s Doctor’s stall')+'</b> <span>'+K.n+' / '+K.max+(K.doctor?' · a Doctor tends it':' · no Doctor (set a villager’s job to Doctor)')+'</span></div>';
     if(K.need)h+='<div class="foodwarn">'+esc(u1.name||'This unit')+' needs a '+esc((K.herbs.find(x=>x.rid===K.need)||{}).remedy||'remedy')+' ('+esc(K.needWhy)+').</div>';
     h+='<div class="alcmix">'+K.herbs.map(x=>esc(x.name)+' '+x.n+' · '+esc(x.remedy)+' '+x.rn).join('<br>')+'</div>';
     if(K.own){h+='<div class="alcrow">'+cb('put','Put in ('+K.carried+')','',K.carried?'':' disabled title="Carry herbs or remedies"')+K.herbs.map(x=>cb('make','Make '+esc(x.remedy.split(' ').pop()),x.id,x.n?' title="One '+esc(x.name)+': '+esc(x.treats)+'. Potion skill '+K.skill+'"':' disabled title="No '+esc(x.name)+' in the stall"')).join('')+'</div>';
      h+='<div class="alcrow">'+K.herbs.map(x=>cb('take','Take '+esc(x.remedy.split(' ').pop()),x.rid,x.rn?'':' disabled')).join('')+(K.need?cb('use','Use one now',K.need,(K.herbs.find(x=>x.rid===K.need)||{}).rn?'':' disabled title="None in the stall"'):'')+'</div>'}
     dx.innerHTML=h}}}
  // Operating table beside the unit (Surgery.dm): missing limbs and grafts, false limbs to make, a body's limbs to take.
  {let tx=hf.querySelector('.tablebox');const u1=sel.length===1?sel[0]:null,O=u1&&u1.table;
   if(!O){if(tx)tx.remove()}else{if(!tx){tx=document.createElement('div');tx.className='alchemy tablebox';(hf.querySelector('.clinicbox')||hf.querySelector('.foodbox')||hf.querySelector('.alchemy')||hf.querySelector('.skillbar')||hf.querySelector('.bagbar')||hf.lastChild).after(tx)}
    const k=JSON.stringify([u1.ref,O]);if(tx.dataset.k!==k){tx.dataset.k=k;const v=(a,arg)=>esc(u1.ref+'|'+a+'|'+(arg||''));const sb=(a,label,arg,extra)=>'<button data-do="surgery" data-value="'+v(a,arg)+'"'+(extra||'')+'>'+label+'</button>';const miss=arr(O.missing),grafts=arr(O.grafts);
     let h='<div class="alchead"><b>Operating table</b> <span>'+(O.doctor?'the Doctor operates here':'no Doctor (set a villager’s job to Doctor)')+'</span></div>';
     h+='<div class="alcmix">'+(miss.length?'Missing: '+esc(miss.join(', ').toLowerCase()):'No limbs missing')+(grafts.length?'<br>Has '+esc(grafts.join(', ')):'')+(arr(O.limbs).length?'<br>Carrying: '+esc(arr(O.limbs).join(', ')):'')+'</div>';
     if(O.own){h+='<div class="alcrow">'+arr(O.kinds).map(x=>['arm','leg'].filter(p=>x.id!=='wood'||p==='leg').map(p=>sb('make','Make '+esc(x.name.toLowerCase())+' '+p,x.id+':'+p,x.ok?' title="'+esc(x.what)+'"':' disabled title="Needs '+esc(x.what)+' carried"')).join('')).join('')+'</div>';
      if(O.body)h+='<div class="alcrow">'+sb('harvest','Take an arm from '+esc(O.body.replace(/'s Body$/,'')),'arm')+sb('harvest','Take a leg','leg')+'</div>';
      h+='<p class="hint">'+(miss.length?'Carry a limb or a false one and stand here: the Doctor grafts it. Any race’s limb takes.':'Grafted and false limbs show when the unit is looked at.')+'</p>'}
     tx.innerHTML=h}}}
  // Tavern beside the unit (Tavern.dm): its wine, pour or press more, have a drink.
  {let vx=hf.querySelector('.tavernbox');const u1=sel.length===1?sel[0]:null,T=u1&&u1.tavern;
   if(!T){if(vx)vx.remove()}else{if(!vx){vx=document.createElement('div');vx.className='alchemy tavernbox';(hf.querySelector('.tablebox')||hf.querySelector('.clinicbox')||hf.querySelector('.foodbox')||hf.querySelector('.alchemy')||hf.querySelector('.skillbar')||hf.querySelector('.bagbar')||hf.lastChild).after(vx)}
    const k=JSON.stringify([u1.ref,T]);if(vx.dataset.k!==k){vx.dataset.k=k;const v=a=>esc(u1.ref+'|'+a);const tb=(a,label,extra)=>'<button data-do="tavern" data-value="'+v(a)+'"'+(extra||'')+'>'+label+'</button>';
     let h='<div class="alchead"><b>Tavern</b> <span>'+T.drink+' / '+T.max+' cups of wine'+(T.drunk>=15?' · '+esc(u1.name||'this unit')+' is '+(T.drunk>=60?'very drunk':T.drunk>=35?'drunk':'merry'):'')+'</span></div>';
     if(T.own)h+='<div class="alcrow">'+tb('pour','Pour wine in ('+T.wine+')',T.wine?'':' disabled title="Carry a Wine brew"')+tb('press','Press wine',T.press?' title="2 fruit and a fungus: 3 cups"':' disabled title="Needs 2 fruit (grapes, tomatoes) and a fungus carried ('+T.fruit+' / '+T.fungus+')"')+tb('drink','Have a drink',T.drink?'':' disabled')+'</div><p class="hint">At night villagers come here for a few rounds. Very drunk ones may start a brawl: guards on patrol break it up.</p>';
     vx.innerHTML=h}}}
  // Notice board beside the unit (Quests.dm): read its notices; post one at your own.
  {let qx=hf.querySelector('.qboardbox');const u1=sel.length===1?sel[0]:null,Q=u1&&u1.qboard;
   if(!Q){if(qx)qx.remove()}else{if(!qx){qx=document.createElement('div');qx.className='alchemy qboardbox';(hf.querySelector('.tavernbox')||hf.querySelector('.tablebox')||hf.querySelector('.clinicbox')||hf.querySelector('.foodbox')||hf.querySelector('.alchemy')||hf.querySelector('.skillbar')||hf.querySelector('.bagbar')||hf.lastChild).after(qx)}
    const k=JSON.stringify([u1.ref,Q,u1.keeperMake]);if(qx.dataset.k!==k){qx.dataset.k=k;qx.innerHTML='<div class="alchead"><b>Notice board</b> <span>'+esc(Q.own?'Yours':(Q.house||''))+' \u00b7 '+(Q.n||0)+' notice'+(Q.n===1?'':'s')+(Q.mark==='!'?' \u00b7 one you can take':Q.mark==='?'?' \u00b7 hand in here':'')+'</span></div><div class="alcrow"><button data-do="quest" data-value="'+esc('board|'+u1.ref)+'">Read the notices</button>'+(Q.own?'<button data-qpost="1" title="Post a notice\nThis unit posts it and carries any goods you put up.">Post a notice</button>':'')+(Q.own&&u1.keeperMake&&u1.keeperMake.quest?keeperMakeBtn(u1,'quest'):'')+'</div>'}}}
  // Cave: a mouth beside the unit (enter), or inside one (foes, treasure, the way out).
  {let cv=hf.querySelector('.cavebox');const u1=sel.length===1?sel[0]:null,C=u1&&u1.cave;
   if(!C){if(cv)cv.remove()}else{if(!cv){cv=document.createElement('div');cv.className='alchemy cavebox';(hf.querySelector('.alchemy')||hf.querySelector('.skillbar')||hf.querySelector('.bagbar')||hf.lastChild).after(cv)}
    const k=JSON.stringify([u1.ref,C]);if(cv.dataset.k!==k){cv.dataset.k=k;const v=a=>esc(u1.ref+'|'+a);
     cv.innerHTML=C.inside?'<div class="alchead"><b>'+esc(C.name)+'</b> <span>'+C.foes+' foe'+(C.foes===1?'':'s')+' left · treasure: '+C.loot+' item'+(C.loot===1?'':'s')+(C.lootDist!=null?' ('+C.lootDist+' tiles)':'')+'</span></div>'+(C.exit?'<div class="alcrow"><button data-do="cave" data-value="'+v('leave')+'">Climb out</button></div>':'<p class="hint">The stairs up are where you came in.</p>')
      :C.plant?'<div class="alchead"><b>A lair for your dragon</b> <span>rock to dig into here</span></div><div class="alcrow"><button data-do="cave" data-value="'+v('plant')+'">'+(C.moves?'Move our lair here':'Make our lair here')+'</button></div><p class="hint">Your own cave: no visit limit. Treasure you leave inside stays, the floor fills with gold as the hoard grows, and your dragon heals faster asleep on it.</p>'
      :'<div class="alchead"><b>Cave mouth: '+esc(C.name)+'</b> <span>'+esc(C.dangerName)+'</span></div>'+(C.ready?'<div class="alcrow"><button data-do="cave" data-value="'+v('enter')+'">Enter with '+C.party+' (within 2 tiles)</button></div><p class="hint">Or send units walking into the mouth.</p>':'<p class="hint">Already explored today. Come back tomorrow.</p>')}}}
  // Runes: pieces beside the unit, and their circuit's mana.
  {let rx=hf.querySelector('.runebox');const u1=sel.length===1?sel[0]:null,R=u1&&u1.runes;
   if(!R){if(rx)rx.remove()}else{if(!rx){rx=document.createElement('div');rx.className='alchemy runebox';(hf.querySelector('.cauldronbox')||hf.querySelector('.alchemy')||hf.querySelector('.skillbar')||hf.querySelector('.bagbar')||hf.lastChild).after(rx)}
    const k=JSON.stringify([u1.ref,R]);if(rx.dataset.k!==k){rx.dataset.k=k;const v=(a,ref)=>esc(u1.ref+'|'+a+'|'+ref);
     let h='<div class="alchead"><b>Runes</b> <span>circuit: '+R.size+' piece'+(R.size===1?'':'s')+' · mana '+R.mana+' / '+R.max+(R.crystals?'':' · no crystal')+'</span></div>';
     h+=R.pieces.map(p=>'<div class="alcrow"><span>'+esc(p.name)+'</span>'+(p.id==='lever'?'<button data-do="rune" data-value="'+v('pull',p.ref)+'">Pull</button>':'')+(p.id==='runedoor'?'<button data-do="rune" data-value="'+v('door',p.ref)+'">'+(p.open?'Close':'Open')+'</button>':'')+
       (p.id==='plate'?'<button data-do="rune" data-value="'+v('anyone',p.ref)+'" title="Who sets it off">'+(p.anyone?'Anyone':'Enemies only')+'</button>':'')+(['lever','plate'].includes(p.id)?'<button data-do="rune" data-value="'+v('test',p.ref)+'">Test</button>':'')+
       '<button data-do="rune" data-value="'+v('scratch',p.ref)+'" title="Scratch it out: cuts the circuit here">Scratch out</button></div>').join('');
     rx.innerHTML=h}}}
  // Unload / Take / Best armour work for one unit or the whole selection.
  if(picked.length){let st=hf.querySelector('.bagstock');if(!st){st=document.createElement('div');st.className='bagstock';st.innerHTML='<button data-do="dropoff" title="Carry resources to the stockpile">Unload</button><span>Take:</span><button data-do="takestock" data-value="food">Food</button><button data-do="takestock" data-value="wood">Wood</button><button data-do="takestock" data-value="stone">Stone</button><button data-do="takestock" data-value="potions">Potions</button><button data-do="equipbest" title="Wear the best armour each selected unit carries">Best armour</button>';hf.append(st)}{/* a dragon or spider queen can't take food or wear armour: only Unload is offered (hud-craft) */const beasts=picked.every(hcBeast);st.querySelectorAll('[data-do=takestock],[data-do=equipbest],span').forEach(e=>{if(e.hidden!==beasts)e.hidden=beasts})}}
 if(sel.length===1){heroPanes(hf,sel[0]);for(const c of hf.children)if(!c.dataset.pane&&!c.matches('.hfmore,.hf,.hftabs,.succ'))c.dataset.pane='overview';hf.dataset.tab=heroTab;
  // tabs along the bottom: the card grows upward from the screen's edge, so they stay put whatever the pane's height
  const tb=hf.querySelector('.hftabs');if(tb&&hf.lastElementChild!==tb)hf.append(tb)}
 else if(sel.length>1){hf.querySelectorAll('.hfpane').forEach(p=>p.remove());for(const c of hf.children)if(!c.dataset.pane&&!c.matches('.hfmore,.hn,.facts,.hftabs,.succ'))c.dataset.pane=c.matches('.groupctl,.bagstock')?'orders':'band';hf.dataset.tab=groupTab;
  const tb=hf.querySelector('.hftabs');if(tb&&hf.lastElementChild!==tb)hf.append(tb)}
 else{hf.querySelectorAll('.hfpane').forEach(p=>p.remove());delete hf.dataset.tab}
 if(sel.length===1){const u=sel[0];[['hp','Health',u.hp,u.maxhp],['food','Food',u.fullness,u.maxfullness],['rest','Rest',u.energy,100]].forEach(([c,l,v,mx])=>{const b=hf.querySelector('.bar.'+c);if(!b)return;const w=pct(v,mx)+'%';if(b.firstChild.style.width!==w)b.firstChild.style.width=w;barSet(b.lastChild,l,v,mx)})}
 nearCardSync();if(!placeRoster.q){placeRoster.q=1;requestAnimationFrame(()=>{placeRoster.q=0;placeRoster()})}   // once, in the next frame (hud-craft, 10-25)
 toast(m.notice);queueRegions()}


