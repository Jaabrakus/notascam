// ===== Onboarding (playtest) =====
// Game text arrives with the original's owner tags ("{NPC Undead} Skeleton Lord", "{Newcomer} Borim") and a few
// Title Case system lines; this tidies them for the toasts and the Log. Other players' units read "Bob’s Borim".
const LINE_FIX={'Day Rises':'Dawn breaks.','It Starts To Get Lighter':'The sky grows lighter.','It Starts To Get Darker':'Dusk is falling.','Night Falls':'Night falls.','Welcome to Dungeon Master!':'Welcome to Banners of the Deep.','Press R to choose a race to play.':'Click Choose your people to begin.','Autosaves happen every 15 minutes, if the server crashes you will be rolled back by at most 15 minutes.':'The world saves itself every 15 minutes.','Failed!':'The attempt failed and the material is used up. Crafting skill rises with every try.'};
// Item names come as the original's type names ("PickAxe - Quality", "WoodenAxe", "wood"): spaced and capitalised for tooltips.
function itemLabel(n){n=String(n||'').replace(/PickAxe/g,'Pickaxe').replace(/_/g,' ').replace(/([a-z])([A-Z])/g,'$1 $2');return n.charAt(0).toUpperCase()+n.slice(1)}
function tidyLine(s){s=String(s==null?'':s).replace(/\s+/g,' ').trim();const t=ownTag();if(t){s=s.split(t).join('');s=s.split('('+t.trim().slice(1,-1)+') ').join('')}
 s=s.replace(/[{(]NPC[^})]*[})]\s*/g,'').replace(/\{([^{}]{1,40})\}\s+(?=\S)/g,'$1’s ').replace(/!{2,}/g,'!');return LINE_FIX[s]||s}
// The race pick and the arrival story (Onboarding.dm) in the ask card.
const RARE_BLURB={Dragon:'One dragon, soon a mother. Flies and breathes fire.',Spider:'A spider queen who breeds her own swarm.',Devourer:'An ancient horror that grows on the dead.',Svartalfar:'One cursed dark elf, long-lived and powerful.',Illithid:'A mind flayer who bends weaker minds.','Sand King':'A sand king larva that grows its own bodies.'};
// A lone rare creature (Dragon, Spider queen…) doesn't build a camp: no settlement tracker, and its own first steps.
const SOLO_STORY=/^The (Dragon|Spider Queen|Devourer|Svartalfar|Illithid|Sand King)$/;function soloStart(m){const u=arr(m.units);return u.length>0&&u.every(x=>/^(Dragon|Spider|Devourer|Svartalfar|Illithid|SandKing)$/.test(String(x.race||'')))}
const RACE_BLURB={Human:'3 settlers with axes. Adaptable, and at home almost anywhere.',Dwarf:'3 miners with picks and axes. Masters of stone and deep halls.',Elf:'3 woodland guardians in wooden armour, sworn to the forests.',Orc:'3 warriors with axes and bucklers. Strong and fierce.',Goblin:'3 goblins with swords. Cunning diggers of dark dungeons.',Lizardman:'3 spear hunters, natives of the swamps.',Frogman:'3 spear carriers of the swamps, old rivals of the lizardmen.',Kobold:'5 small spear carriers. Many hands make light work.',Ratman:'5 ratfolk with spears. Strength in numbers.'};
function renderOnboardAsk(c,A){const opts=arr(A.options).map((l,i)=>[String(l),i+1]);let h,many=false;
 if(A.kind==='story'){const go=opts[0]||['Begin',1];
  h='<div class="ic-head"><span class="ic-kind"><b class="hcg hcg-spark">✦</b></span><div class="ic-name"><b>'+esc(A.title||'')+'</b><small>Your story begins</small></div></div><p class="story-text">'+esc(A.message||'')+'</p>'
   +'<p class="story-next"><b>First steps:</b> '+(SOLO_STORY.test(String(A.title||''))?'click your creature to see its needs, and right-click anything to see what it can do (its own powers are on its card\u2019s Interact tab). The Guide (F3) has the rest.':'the guide at the top left takes you through them one at a time, and lights up what to press. The Guide (F3) has the rest.')+'</p><button class="story-go" data-ask="'+go[1]+'">'+esc(go[0])+'</button>'}
 else{const cancel=opts.find(([l])=>l==='Cancel'),rest=opts.filter(([l])=>l!=='Cancel');many=rest.length>10;
  h='<div class="ic-head"><span class="ic-kind"><b class="hcg hcg-people">⚑</b></span><div class="ic-name"><b>'+esc(A.title||'Choose your people')+'</b><small>'+esc(A.message||'')+'</small></div></div><div class="uc-body"><div class="race-opts">'
   +rest.map(([l,i])=>{const rare=/ - Rare$/.test(l),n=l.replace(/ - Rare$/,'');return '<button data-ask="'+i+'"'+(rare?' class="rare"':'')+'><i class="rc-pic" data-r="'+esc(n)+'" aria-hidden="true"></i><b>'+esc(n)+(rare?' ★':'')+'</b><small>'+esc(rare?(RARE_BLURB[n]||'A rare people.')+' Drawn for you this time only.':(RACE_BLURB[n]||''))+'</small></button>'}).join('')+'</div></div>'
   +(cancel?'<div class="ask-foot"><button data-ask="'+cancel[1]+'" class="ask-cancel" title="Not now (Esc)">Not now</button></div>':'')}
 c.classList.toggle('many',many);c.innerHTML=h;c.hidden=false;queueRegions()}
// The first company (Company.dm, staged 10-27): after the race pick, one card per starting villager: their own sprite,
// a name to type over (Enter or leaving the box renames), sex and age, the four stats the race rolls (the best in the
// company in gold), a die to roll that one again and a switch to roll them as the other sex; Re-roll all and Begin below.
function companyKey(A,m){const refs=arr((A.extra||{}).units).map(r=>r.ref);return String(A.id)+'|'+JSON.stringify((A.extra||{}).units)+'|'+arr(m.units).filter(u=>refs.includes(u.ref)).map(u=>u.ref+u.name+u.portrait).join()}
function renderCompanyAsk(c,A,m){const X=A.extra||{},names=arr(X.names),rows=arr(X.units),units=arr(m.units),best=names.map((_,i)=>Math.max(...rows.map(r=>+arr(r.stats)[i]||0)));
 const card=r=>{const u=units.find(v=>v.ref===r.ref)||{},sex=u.gender==='Female'?'Female':'Male';return '<div class="co-card"><div class="co-pic">'+(/^r3u-[0-9a-f]+\.png$/.test(r.pic||'')?'<i class="co-pic3d" style="background-image:url('+r.pic+')"></i>':u.portrait?'<img alt="" src="'+esc(u.portrait)+'">':'')+'</div><input class="co-name" maxlength="25" aria-label="Name" data-ref="'+esc(r.ref)+'" value="'+esc(ownName(u.name||''))+'"><small class="co-who">'+esc(sex)+(u.age?' · age '+esc(u.age):'')+'</small><dl class="co-stats">'
  +names.map((n,i)=>{const v=+arr(r.stats)[i]||0;return '<div'+(v&&v===best[i]&&rows.length>1?' class="best"':'')+'><dt>'+esc(n)+'</dt><dd>'+v+'</dd></div>'}).join('')+'</dl><div class="co-acts"><button data-co="'+esc(r.ref)+'" title="Roll this one again">Re-roll</button><button data-co="'+esc(r.ref)+'|sex" title="Roll them again as '+(sex==='Male'?'a woman':'a man')+'">'+(sex==='Male'?'&#x2640;':'&#x2642;')+'</button></div></div>'};
 c.innerHTML='<div class="ic-head"><span class="ic-kind"><b class="hcg hcg-people">⚑</b></span><div class="ic-name"><b>'+esc(A.title||'Your company')+'</b><small>'+esc(A.message||'')+'</small></div></div><div class="co-row">'+rows.map(card).join('')+'</div><div class="ask-foot"><button class="co-back" data-ask="2" title="Pick another people">Back</button><button class="co-all" data-co="all">Re-roll all</button><button class="story-go" data-ask="1">Begin</button></div>';
 c.hidden=false;queueRegions()}
document.addEventListener('click',e=>{const b=e.target.closest('#askcard [data-co]');if(!b)return;send('companyroll',$('askcard').dataset.k.split('|')[0]+'|'+b.dataset.co)});
document.addEventListener('change',e=>{const i=e.target.closest('#askcard .co-name');if(!i)return;const v=i.value.trim();if(v)send('renameunit',i.dataset.ref+'|'+v);else toast('Type a name first.')});
// No people yet (a new player, or everyone lost): a start card instead of an empty map with no hint.
// After a defeat (people seen this session, now none) it says so instead of greeting a newcomer.
// Just after a choice is answered (the race picked) the army takes a moment to come: no card in between (the user,
// 10-25: it showed for a second after the race was chosen); held up to 6 s, or until the people are there.
// A brand-new player goes straight to the race picker (the owner 11-01: four start screens cut to two): the card's own
// button is pressed for them once, and the card shows only if no picker came within 5 s. A fallen company still gets it.
let hadPeople=false,startAuto=0;function startCard(m){const c=$('startcard');if(!c)return;const n=arr(m.units).length;if(n)hadPeople=true;const held=performance.now()-(window.rmAskAnsweredAt||-1e9)<6000;let show=!!overlayHost&&!n&&!m.ask&&!held;
 if(show&&!hadPeople&&!m.testRun){if(!startAuto){startAuto=performance.now();const b=c.querySelector('.sc-go');if(b)b.click()}if(performance.now()-startAuto<5000)show=false}
 if(show){const lost=hadPeople;if(c.dataset.lost!==String(lost)){c.dataset.lost=String(lost);text(c.querySelector('h2'),lost?'Begin again':'Banners of the Deep');text(c.querySelector('p'),lost?'Your company has fallen, but the land remains. Choose a people to lead and start a new story.':'A new land lies before you. Choose the people you will lead: each begins with its own tools and strengths, and the rest is up to you.')}}
 if(c.hidden!==!show){c.hidden=!show;queueRegions()}}
// F3 / Help (Actions.dm RemasterHelp) bumps model.help: open the Guide panel, not just its tab.
let helpSeen=null;function guideHotkey(m){const v=Number(m.help)||0;if(helpSeen!==null&&v!==helpSeen&&overlayHost){document.body.classList.add('panel-open');queueRegions()}helpSeen=v}
// The next unfinished goal, top left; a click opens the Guide.
// With every first goal met it points at the next rank instead (Realm tab), until the settlement reaches it.
function goalTrack(m,goals,done){const g=$('goaltrack');if(!g||guideOn(m))return;let next=goals.find(v=>!done(v[0])),tab='guide';const P=m.progress||{};   // the guide below holds it while first steps remain
 if(!next&&P.next&&(P.rankIndex||1)<=1){next=['rank','Grow to a '+P.next,arr(P.needs).filter(n=>!n.done).map(n=>n.have+'/'+n.need+' '+n.label).join(' · ')+'. The Realm tab shows what each rank brings.'];tab='realm'}
 const show=!!overlayHost&&!m.tutorialHidden&&!!next&&arr(m.units).length>0&&!soloStart(m);
 if(show){text(g.querySelector('b'),next[1]);text(g.querySelector('small'),next[2]);g.dataset.value=tab;g.title=tab==='realm'?'Your next rank. Click for the Realm tab.':'Your next goal. Click for the Guide (F3).'}if(g.hidden!==!show){g.hidden=!show;queueRegions()}}
function renderGoals(m){
 startCard(m);guideHotkey(m);const hasPeople=arr(m.units).length>0;
 const key=JSON.stringify([m.milestones,m.tutorialHidden,hasPeople,m.progress&&m.progress.rankIndex,m.progress&&m.progress.needs]);if(key===goalsKey)return;goalsKey=key;$('goals').hidden=!!m.tutorialHidden;$('goals').replaceChildren();
 const goals=[['people','Choose your people','Click Choose your people, then pick who you will lead.'],['select','Meet your company','Click one of your people to see their health, food and rest.'],['order','Give a direct order','With a unit selected, click a spot on the ground; with Gather on (G), a tree or a rock.'],['gather','Secure supplies','Collect wood, stone or food.'],['camp','Establish a camp','Select someone carrying wood, then Work › Build at the selected builder › Campfire (1 wood). No trees near? Lead your people to a wood first.'],['workshop','Make a workshop','Work › Place a workshop › Carpentry, then click open ground a few steps from the campfire (1 wood).'],['craft','Try your hand at crafting','With a unit carrying 1 wood selected, click your carpentry, choose Craft and pick something (a wooden bucket, say). Early attempts often fail; each one trains the skill.'],['defend','Prepare your defence','Select a unit, open Orders on its card and choose Hold or Guard.']];
 const doneOf=id=>id==='people'?hasPeople:!!(m.milestones||{})[id];goalTrack(m,goals,doneOf);
 goals.forEach(v=>{const done=doneOf(v[0]),d=document.createElement('div');d.className='task'+(done?' done':'');const small=document.createElement('small');text(d,(done?'✓ ':'○ ')+v[1]);text(small,v[2]);d.append(small);$('goals').append(d)});
}
// ===== The guide (the owner, 11-01: "we needa video or a tutorial of the game", then "Both, guide first") =====
// The first goals as a walkthrough in the goal tracker's place, top left: which step, what to do, the button to press
// ringed in gold (#guidering) and, on the map, a pin on what to click (#guidepin: one of your people, the nearest tree,
// your carpentry); out of view, the pin waits at the edge pointing the way, and a click takes the camera there. Steps
// tick off with the Guide (F3) list's milestones; Skip hides both (the Guide's own button brings them back). A lone rare
// creature has its own first steps.
const GUIDE=[['select','Meet your company'],['order','Give your first order'],['gather','Bring in supplies'],['camp','Light a campfire'],['workshop','Build a carpentry'],['craft','Craft something'],['defend','Set a guard']];
let guideShown=false,guideDoneSaid=false,guideKey='',guidePinData=null,guideScrolled=null,guideTreeMemo=null,guideRingAt='';
function guideOn(m){return !!overlayHost&&!!m&&!m.tutorialHidden&&arr(m.units).length>0&&!soloStart(m)&&GUIDE.some(([id])=>!(m.milestones||{})[id])}
function guideVis(e){return !!e&&e.getClientRects().length>0}
function guideFind(...a){for(const s of a){const e=typeof s==='string'?document.querySelector(s):s;if(guideVis(e))return e}return null}
function guideBtn(sel,re){return [...document.querySelectorAll(sel)].find(b=>guideVis(b)&&re.test(b.textContent.trim()))||null}
function guideOwn(){return typeof V3!=='undefined'&&V3.things?V3.things.filter(t=>t.kind==='mine'&&t.ref&&t.dx!=null):[]}
// The nearest tree to a unit (a terrain tile of kind "tree"), ring by ring out to 20 tiles; kept 2 s.
function guideTree(u){if(!u||typeof v3kindAt!=='function')return null;const now=performance.now(),k=u.x+','+u.y;if(guideTreeMemo&&guideTreeMemo.k===k&&now-guideTreeMemo.at<2000)return guideTreeMemo.t;let t=null;
 for(let r=1;r<=20&&!t;r++){let bd=1e9;for(let dy=-r;dy<=r;dy++)for(let dx=-r;dx<=r;dx++){if(Math.max(Math.abs(dx),Math.abs(dy))!==r)continue;const K=v3kindAt(u.x+dx,u.y+dy);if(K&&K.kind==='tree'&&!K.gone){const d=dx*dx+dy*dy;if(d<bd){bd=d;t={x:u.x+dx,y:u.y+dy}}}}}
 guideTreeMemo={k,at:now,t};return t}
// The nearest workshop of that name, on a tile none of your people stand on (a click there would pick them instead).
function guideStation(name,u){const own=guideOwn();let best=null,bd=1e9;for(const t of (typeof V3!=='undefined'&&V3.things)||[])if(t.kind==='station'&&t.name===name&&t.dx!=null){const d=(u?Math.hypot(t.x-u.x,t.y-u.y):0)+(own.some(o=>o.x===t.x&&o.y===t.y)?1000:0);if(d<bd){bd=d;best=t}}return best}
// What to say, which button to ring (scrolled to once) and what to pin, for a step as things stand now.
// Who is selected comes from the HUD's own rows (the 3D view's lag a frame); the pin rides the 3D unit when there is one.
function guideStep(id){const units=arr(model.units),sel=units.filter(u=>u.selected),u=sel[0]||units[0],own=guideOwn(),body=u&&own.find(t=>t.ref===u.ref),work={say:'Open Work in the menu at the top right.',ring:guideFind('nav [data-value=work]')};
 const pick={say:'Click one of your people, on the map or in the Company list on the right.',ring:guideFind('#rosterList > *'),pin:u?(body?{t:body,label:'Click me'}:{x:u.x,y:u.y,label:'Click me'}):null};
 if(id==='select')return {...pick,say:pick.say+' Their card shows health, food and rest.'};
 if(!sel.length&&id!=='gather')return {...pick,say:'First select one of your people. '+pick.say};
 if(id==='order'||id==='gather'){const g=$('btnGather'),busy=units.some(x=>/chop|mine|gather|fish|dig/i.test(String(x.order||'')));
  if(id==='gather'&&busy)return {say:'They chop it and carry the wood in their bags. This ticks off with the first wood. Meanwhile, select someone else and click another tree.'};
  if(!sel.length)return {...pick,say:'First select one of your people. '+pick.say};
  if(g&&g.getAttribute('aria-pressed')!=='true')return {say:'Turn Gather on: press G, or click Gather on the bar below. Then a click on a tree chops it, and on rock mines it.',ring:guideFind(g)};
  const t=guideTree(sel[0]);return {say:t?'Click a tree. Your people walk over and start chopping.':'Click a tree or a rock. None near? Click the ground to walk your people somewhere new.',pin:t?{...t,label:'Click this tree'}:null}}
 if(id==='camp'){const b=guideFind('#page-work [data-do=build][data-value=campfire]');
  return b?{say:'Press Campfire under Build at the selected builder. Whoever is selected builds it where they stand, with 1 wood from their bag.',ring:b,scroll:b}:{...work,say:work.say+' A campfire keeps your people warm and cooks their food.'}}
 if(id==='workshop'){if(typeof V3!=='undefined'&&V3.shop&&V3.shop.id==='carpentry')return {say:'Click open ground a few steps from the campfire. Your builder carries 1 wood over and builds it. Esc cancels.'};
  const b=guideBtn('#shopPicker button',/^Carpentry/);
  return b?{say:'Press Carpentry under Place a workshop, then click open ground a few steps from the campfire.',ring:b,scroll:b}:{...work,say:work.say+' A carpentry turns wood into tools, weapons and furniture.'}}
 if(id==='craft'){const it=guideBtn('#askcard button',/^Wooden Bucket$/);if(it)return {say:'Pick something to make. A Wooden Bucket takes 1 wood. Early tries often fail, but each one trains the skill.',ring:it,scroll:it};
  const cr=guideBtn('#askcard button',/^Craft$/);if(cr)return {say:'Press Craft.',ring:cr};
  const c=guideStation('Carpentry',u);return {say:'With someone carrying wood selected, click your carpentry. They walk over, and its menu opens there.',pin:c?{t:c,label:'Your carpentry'}:null}}
 const s=guideFind('[data-do=stance][data-value=guard]');if(s)return {say:'Press Guard: they stand watch and fight whatever comes near. Hold keeps them on the spot.',ring:s,scroll:s};
 return {say:'Press Orders on the selected person’s card.',ring:guideFind('#heroframe [data-do=tab][data-value=orders]','nav [data-value=orders]')}}
function guideTick(){const g=$('goaltrack'),m=typeof model!=='undefined'?model:null;if(!g)return;let ring=$('guidering');
 {const bc=$('bootcover');if(bc&&!bc.classList.contains('off')){guidePinData=null;if(ring&&!ring.hidden)ring.hidden=true;return}}   // nothing over the loading cover (bootCoverOff marks it off as it fades)
 {const ac=$('askcard');if(ac&&!ac.hidden&&ac.classList.contains('story')&&!g.hidden&&ac.getBoundingClientRect().top<g.getBoundingClientRect().bottom+8)placeRoster()}   // the arrival story's note goes under the card (it came before the roster was placed again)
 if(!guideOn(m)){guidePinData=null;if(ring&&!ring.hidden)ring.hidden=true;
  if(guideShown){guideShown=false;guideKey='';g.classList.remove('guide');g.innerHTML='<span>Next goal</span><b></b><small></small>';g.hidden=true;goalsKey='';   // the goal tracker takes over again (next rank)
   if(!guideDoneSaid&&m&&!m.tutorialHidden&&GUIDE.every(([id])=>(m.milestones||{})[id])){guideDoneSaid=true;toast('Guide done: you know the basics. Next, grow your camp: the Realm tab shows what each rank needs.')}}
  return}
 const M=m.milestones||{},i=GUIDE.findIndex(([id])=>!M[id]),S=guideStep(GUIDE[i][0]);guideShown=true;
 const key=i+'|'+S.say;if(key!==guideKey){guideKey=key;g.classList.add('guide');g.dataset.value='guide';g.title='Your first steps. Click for the Guide (F3).';
  g.innerHTML='<span>Guide · step '+(i+1)+' of '+GUIDE.length+'</span><b>'+esc(GUIDE[i][1])+'</b><small>'+esc(S.say)+'</small><em class="gt-bar">'+GUIDE.map((_,j)=>'<i'+(j<i?' class="on"':j===i?' class="now"':'')+'></i>').join('')+'</em><i class="gt-skip" data-do="tutorial" role="button" title="Hide the guide and goals. The Guide (F3) brings them back.">Skip guide</i>';
  if(g.hidden){g.hidden=false}queueRegions()}
 if(S.scroll&&S.scroll!==guideScrolled){guideScrolled=S.scroll;S.scroll.scrollIntoView({block:'center',behavior:'smooth'})}
 guidePinData=S.pin||null;
 // the ring: round the button, while it is on screen and not scrolled out of its panel
 let r=S.ring&&S.ring.getBoundingClientRect();const box=S.ring&&S.ring.closest('main');if(r&&box){const b=box.getBoundingClientRect();if(r.bottom<b.top+4||r.top>b.bottom-4)r=null}
 if(r&&(r.width<2||r.bottom<0||r.top>innerHeight))r=null;
 if(!ring){ring=document.createElement('div');ring.id='guidering';ring.setAttribute('aria-hidden','true');ring.hidden=true;document.body.append(ring)}
 if(!r){if(!ring.hidden)ring.hidden=true;return}
 const k=hudK(),at=[r.left/k-4,r.top/k-4,r.width/k+8,r.height/k+8].map(Math.round).join(',');if(at!==guideRingAt){guideRingAt=at;const [x,y,w,h]=at.split(',');Object.assign(ring.style,{left:x+'px',top:y+'px',width:w+'px',height:h+'px'})}
 if(ring.hidden)ring.hidden=false}
setInterval(()=>{try{guideTick()}catch(e){console.error(e)}},200);
// Skip sits inside the card (a button: it opens the Guide), so it is caught first: the Guide's own Show / hide goals.
document.addEventListener('click',e=>{if(!e.target.closest('#goaltrack .gt-skip'))return;e.preventDefault();e.stopImmediatePropagation();send('tutorial','')},true);   // before 012's tab listener on the same node
// The map pin, each 3D frame (with the quest pins): over what to click, or at the edge of the open view pointing to it.
function guidePin3D(){const P=guidePinData;let e=$('guidepin');if(!P){if(e&&!e.hidden)e.hidden=true;return}
 if(!e){const f=$('food3d');if(!f)return;e=document.createElement('div');e.id='guidepin';e.setAttribute('role','button');f.parentNode.insertBefore(e,f.nextSibling);
  e.addEventListener('click',()=>{const p=guidePinData;if(!p)return;V3.tcx=p.t?p.t.dx:p.x;V3.tcy=p.t?p.t.dy:p.y;V3.panAt=performance.now();v3panSend(true)})}   // a click looks there
 let W;if(P.t){const w=v3world(P.t);W=[w[0],v3groundAt(P.t.x,P.t.y)+(P.t.kind==='mine'?1.7:1.9),w[2]]}else W=[P.x,v3groundAt(P.x,P.y)+1.6,-P.y];   // just over a head or a workshop; a tree's trunk
 const s=v3project(W);if(!s){e.hidden=true;return}
 // in view: on screen with the map itself (not a panel) under it; out of view it waits inside the open middle, clear of
 // the side panels, the top bar and the command bar
 let inView=false;if(s[0]>=40&&s[0]<=innerWidth-40&&s[1]>=40&&s[1]<=innerHeight-40)for(const el of document.elementsFromPoint(s[0],s[1])){if(e.contains(el)||el.closest('#qpins3d'))continue;inView=el.id==='world3d';break}
 const L=Math.min(340,innerWidth*0.3),R=innerWidth-Math.min(300,innerWidth*0.25),T=110,B=innerHeight-150;
 let x=s[0],y=s[1];if(!inView){const cx=(L+R)/2,cy=(T+B)/2,dx=s[0]-cx,dy=s[1]-cy,f=Math.min(dx?(dx>0?R-cx:L-cx)/dx:1e9,dy?(dy>0?B-cy:T-cy)/dy:1e9,1);x=cx+dx*f;y=cy+dy*f}
 const label=inView?P.label:P.label+' · click to look',k=(inView?'':'off')+'|'+label;if(e.dataset.k!==k){e.dataset.k=k;e.className=inView?'':'off';e.innerHTML='<b>'+esc(label)+'</b><i></i>'}
 if(!inView)e.style.setProperty('--a',Math.atan2(s[1]-y,s[0]-x)+'rad');
 e.style.transform='translate('+Math.round(x)+'px,'+Math.round(y)+'px) translate(-50%,-100%)';if(e.hidden)e.hidden=false}


