'use strict';
/* The page's own errors (Bugs.dm, the owner 11-01: "Add auto errors too"): the last 20 kept for a bug report's hints,
   and each new one sent once a page load (10 at most), one every 3 s, once the server says bug reports are on
   (window.rmBugsOn, from the model: never before the page is ready). rmFpsNow: frames in the last second, for a report. */
window.__rmErrs=[];window.__rmErrSent={};window.__rmErrQ=[];window.rmFpsNow=null;
(function(){const base=s=>String(s||'').split(/[?#]/)[0].split('/').pop().slice(0,80);
 const add=(msg,file,line,stack)=>{try{msg=String(msg||'').slice(0,300);if(!msg)return;const where=base(file)+':'+(line||0),k=msg+'|'+where;
  window.__rmErrs.push(new Date().toISOString().slice(11,19)+' '+where+' '+msg);if(window.__rmErrs.length>20)window.__rmErrs.shift();
  if(window.__rmErrSent[k]||Object.keys(window.__rmErrSent).length>=10)return;window.__rmErrSent[k]=1;
  window.__rmErrQ.push(JSON.stringify({msg:msg,file:base(file),line:line||0,stack:String(stack||'').slice(0,1500)}))}catch(_){}};
 addEventListener('error',e=>{if(e&&e.message)add(e.message,e.filename,e.lineno,e.error&&e.error.stack)});
 addEventListener('unhandledrejection',e=>{const r=e&&e.reason;add('Unhandled: '+((r&&r.message)||r),'',0,r&&r.stack)});
 setInterval(()=>{try{if(window.__rmErrQ.length&&window.rmBugsOn&&typeof send==='function')send('bugauto',window.__rmErrQ.shift())}catch(_){}},3000);
 let frames=0;const tick=()=>{frames++;requestAnimationFrame(tick)};requestAnimationFrame(tick);setInterval(()=>{window.rmFpsNow=frames;frames=0},1000)})();
let model=null, terrain=[], currentTab='units', hudFullAsked=false;
const HUDHOT=['x','y','z','hp','fullness','energy','selected'];   // HUD.dm rm_hud_hot: the units' fast fields, sent as one array (updateHUD)   // hudFullAsked: a full HUD model asked for after a missed send (updateHUD)
const unitNodes=new Map(), commandNodes=new Map();
const $=id=>document.getElementById(id);
function renderWorld(d){const panel=$('worldPanel');if(!panel)return;statRows($('worldRows'),d.world)}
function text(el,value){value=String(value==null?'':value);if(el.textContent!==value)el.textContent=value}
function send(action,value){window.location.href='byond://?rm='+encodeURIComponent(action)+'&value='+encodeURIComponent(value==null?'':value)+(commandSelectionBound(action,value)?'&selection='+encodeURIComponent(currentSelectionToken()):'')}
// Pause/Resume can change label during a held press. Keep that one explicit
// action tied to the same selected unit; unrelated controls use normal clicks.
let pausePress=null,pauseKey=null;
function pauseControl(target){return target instanceof Element?target.closest('button[data-do="unitpause"],button[data-do="unitresume"]'):null}
function validPausePress(p){return p&&!p.cancelled&&p.button.isConnected&&!p.button.disabled&&p.button.dataset.value===p.unit&&arr(model&&model.units).some(u=>u.ref===p.unit&&u.selected)}
function cancelPausePress(){if(pausePress)pausePress.cancelled=true}
function capturePausePress(b,kind,id){pausePress={button:b,action:b.dataset.do,unit:b.dataset.value,kind,id,cancelled:false}}
document.addEventListener('pointerdown',e=>{
 if(!e.isPrimary||e.button!==0){cancelPausePress();return}
 const b=pauseControl(e.target);pausePress=null;
 if(b&&!b.disabled)capturePausePress(b,'pointer',e.pointerId);
},true);
document.addEventListener('pointerup',e=>{
 if(!pausePress||pausePress.kind!=='pointer'||pausePress.id!==e.pointerId)return;
 const hit=document.elementFromPoint(e.clientX,e.clientY);
 if(!hit||!pausePress.button.contains(hit))cancelPausePress();
},true);
document.addEventListener('pointercancel',e=>{if(pausePress&&pausePress.kind==='pointer'&&pausePress.id===e.pointerId)cancelPausePress()},true);
document.addEventListener('keydown',e=>{
 if(e.key==='Escape')cancelPausePress();
 const b=pauseControl(e.target);if(!b||b.disabled||![' ','Enter'].includes(e.key))return;
 if(e.repeat){e.preventDefault();return}
 pauseKey={button:b,key:e.key};capturePausePress(b,'key',e.key);
},true);
document.addEventListener('keyup',e=>{if(pauseKey&&pauseKey.key===e.key){if(e.target!==pauseKey.button)cancelPausePress();pauseKey=null;const released=pausePress;setTimeout(()=>{if(pausePress===released)pausePress=null},0)}},true);
document.addEventListener('focusout',e=>{if(pausePress&&e.target===pausePress.button)cancelPausePress()},true);
window.addEventListener('blur',()=>{cancelPausePress();pauseKey=null});
// A held selected-unit command cannot silently follow a new selection.
let selectionPress=null,selectionKey=null;
function commandSelectionBound(action,value){if(['build','stance','dropoff','unloadresume','job','craft','cancel','workarea','priority'].includes(action)||action==='stockpile'&&value==='unit')return true;const rows=action==='action'?arr(model&&model.commands):action==='borderaction'?arr(model&&model.border&&model.border.controls):[];return !!rows.find(c=>c.id===value)?.selectionBound}
function selectionCommand(target){const b=target instanceof Element?target.closest('button[data-do]'):null;return b&&commandSelectionBound(b.dataset.do,b.dataset.value)?b:null}
function currentSelectionToken(){return model&&model.controlGroups&&model.controlGroups.selection||''}
function validSelectionPress(p){return p&&!p.cancelled&&p.button.isConnected&&!p.button.disabled&&p.button.dataset.do===p.action&&p.button.dataset.value===p.value&&selectionCommand(p.button)&&p.token&&p.token===currentSelectionToken()}
function cancelSelectionPress(){if(selectionPress)selectionPress.cancelled=true}
function captureSelectionPress(b,kind,id){selectionPress={button:b,action:b.dataset.do,value:b.dataset.value,token:currentSelectionToken(),kind,id,cancelled:false}}
document.addEventListener('pointerdown',e=>{
 if(!e.isPrimary||e.button!==0){cancelSelectionPress();return}
 const b=selectionCommand(e.target);selectionPress=null;if(b&&!b.disabled)captureSelectionPress(b,'pointer',e.pointerId);
},true);
document.addEventListener('pointerup',e=>{if(selectionPress&&selectionPress.kind==='pointer'&&selectionPress.id===e.pointerId){const hit=document.elementFromPoint(e.clientX,e.clientY);if(!hit||!selectionPress.button.contains(hit))cancelSelectionPress()}},true);
document.addEventListener('pointercancel',e=>{if(selectionPress&&selectionPress.kind==='pointer'&&selectionPress.id===e.pointerId)cancelSelectionPress()},true);
document.addEventListener('keydown',e=>{
 if(e.key==='Escape')cancelSelectionPress();
 const b=selectionCommand(e.target);if(!b||b.disabled||![' ','Enter'].includes(e.key))return;
 if(e.repeat){e.preventDefault();return}selectionKey={button:b,key:e.key};captureSelectionPress(b,'key',e.key);
},true);
document.addEventListener('keyup',e=>{if(selectionKey&&selectionKey.key===e.key){if(e.target!==selectionKey.button)cancelSelectionPress();selectionKey=null;const released=selectionPress;setTimeout(()=>{if(selectionPress===released)selectionPress=null},0)}},true);
document.addEventListener('focusout',e=>{if(selectionPress&&e.target===selectionPress.button)cancelSelectionPress()},true);
window.addEventListener('blur',()=>{cancelSelectionPress();selectionKey=null});
document.addEventListener('click',e=>{
 const local=e.target.closest('button[data-ui]');
 if(local){
  if(local.disabled)return;
  if(local.dataset.ui==='controls-open')openControls(local.dataset.group||'all',local);
  else if(local.dataset.ui==='controls-close')closeControls();
  else if(local.dataset.ui==='controls-filter'){controlGroup=local.dataset.group;filterControls();$('borderControls').querySelector('.drawerbody').scrollTop=0}
  else if(local.dataset.ui==='controls-clear'){$('controlSearch').value='';filterControls();$('controlSearch').focus()}
  else if(local.dataset.ui==='controls-reset'){controlGroup='all';$('controlSearch').value='';filterControls();$('borderControls').querySelector('.drawerbody').scrollTop=0}
  else if(local.dataset.ui==='palette-close')closePalette(true);
  else if(local.dataset.ui==='magictarget-close')closeMagicTargets(true);
  else if(local.dataset.ui==='groups-open')openGroups(local);
  else if(local.dataset.ui==='groups-close')closeGroups();
  return;
 }
 const b=e.target.closest('button[data-do]');if(b&&!b.disabled){
  if(b.dataset.do==='action'&&b.dataset.value==='interact'&&nearCardUnit()){nearCardToggle();return}   // one unit: the Closest Creature card
  if(selectionCommand(b)&&e.isTrusted&&selectionPress&&!(selectionPress.kind==='pointer'&&e.detail===0)){const intent=selectionPress;selectionPress=null;if(b!==intent.button||!validSelectionPress(intent)){text($('notice'),'Selection changed; choose the command again. Assigned work continues.');return}}
  if(pauseControl(b)&&e.isTrusted&&pausePress&&!(pausePress.kind==='pointer'&&e.detail===0)){const intent=pausePress;pausePress=null;if(b===intent.button&&validPausePress(intent))send(intent.action,intent.unit);return}
  if(b.dataset.do==='action'&&b.dataset.value==='magictarget')magicTargetOpener=b;
  if((b.dataset.do==='action'||b.dataset.do==='borderaction')&&b.dataset.value==='build')paletteOpener=b;
  if(b.dataset.do==='action'&&b.closest('#borderCatalog'))closeControls();
  if(b.dataset.do==='borderaction'&&['build','digpaint','digadd','digremove','interact','goto','warp','waypoint','coords','msg','say','race','updates','zup','zdown','all','area'].includes(b.dataset.value))closeControls();
  send(b.dataset.do,b.dataset.value);
 }
});
document.addEventListener('change',e=>{
 const choice=e.target.closest('select[data-do=defensemode]');
 if(choice&&!choice.disabled)send('defensemode',choice.dataset.unit+'|'+choice.value);
});
document.addEventListener('keydown',e=>{
 if(e.key!=='Escape'||e.defaultPrevented||e.isComposing||e.altKey||e.ctrlKey||e.metaKey)return;
 if(typeof V3!=='undefined'&&V3.on&&(V3.shop||V3.build))return; // 3D placement handles its own Escape
 if($('unitGroups').open){e.preventDefault();closeGroups();return}
 if($('magicTargets').open){e.preventDefault();closeMagicTargets(true);return}
 if($('buildPalette').open){e.preventDefault();closePalette(true);return}
 if($('borderControls').open){e.preventDefault();closeControls();return}
 // an open card or menu, an item held or a special being aimed: Esc closes or cancels that (their own handlers), not the
 // selection too (rts-feel: with no command lost any more, this one used to arrive as well)
 if((typeof V3!=='undefined'&&V3.aim)||(model&&model.useon)||['askcard','usecard','menu3d','loghist','nearcard'].some(id=>$(id)&&!$(id).hidden))return;
 const target=e.target;if(target instanceof Element&&target.closest('input,textarea,select,[contenteditable]:not([contenteditable=false]),[role=dialog]'))return;
 if(model&&model.patrol){e.preventDefault();send('patrolcancel','');return}   // drawing a patrol route: Esc cancels the route, the selection stays (Patrol.dm)
 e.preventDefault();send(model&&model.mode?'cancelmode':'action',model&&model.mode?'':'clear');
});
function button(label,action,value){const b=document.createElement('button');text(b,label);b.dataset.do=action;b.dataset.value=value;return b}
function arr(v){return Array.isArray(v)?v:[]}
function focusWithoutScroll(el){if(el)el.focus({preventScroll:true})}
// Keep controls tied to their actual item/order references as the live model changes.
function syncRows(parent,nodes,items,create,update,fallback){
 const live=new Set(),focused=document.activeElement;let index=0;
 items.forEach(item=>{if(live.has(item.ref))return;live.add(item.ref);let n=nodes.get(item.ref);if(!n){n=create(item);nodes.set(item.ref,n)}update(n,item);if(parent.children[index]!==n.root)parent.insertBefore(n.root,parent.children[index]||null);index++});
 let removedFocus=false;for(const [ref,n]of nodes)if(!live.has(ref)){removedFocus=removedFocus||n.root.contains(focused);n.root.remove();nodes.delete(ref)}
 if(removedFocus)focusWithoutScroll(fallback);else if(focused&&focused.isConnected&&parent.contains(focused)&&(focused.matches(':disabled')||document.activeElement!==focused))focusWithoutScroll(focused.matches(':disabled')?fallback:focused);
}
function roleLabel(u){const job=arr(model&&model.settlement&&model.settlement.jobs).find(j=>j.id===u.job);return job?job.label:({manual:'Manual',woodcutter:'Woodcutter',miner:'Miner',hauler:'Hauler'}[u.job]||u.job||'Manual')}
function unitStatus(u){if(u.moodName&&u.moodName==='Snapped')return '☹ Snapped · '+(u.order||'');if(u.combat)return '⚔ '+u.combat;if(u.mood!=null&&u.mood<30)return '☹ '+u.moodName+' · '+(u.care||u.order||'Idle');if(u.care)return u.care;const order=u.order||'Idle';return (u.paused&&!/^paused\b/i.test(order)?'Paused · ':'')+order}
function stockpileAccepts(p){return Array.isArray(p.accepts)?p.accepts.join(' + '):(p.accepts||'wood + stone')}
const paletteNodes=new Map();let paletteOpener=null,paletteDismissedKey='',paletteKey='';
function closePalette(requestClose){
 const dialog=$('buildPalette');if(requestClose)paletteDismissedKey=paletteKey;
 if(dialog.open){dialog.close();const opener=[paletteOpener,document.querySelector('#commandCategories [data-group=build]'),document.querySelector('#quickDock [data-ui=controls-open]')].find(e=>e&&e.isConnected&&e.getClientRects().length);focusWithoutScroll(opener||$('deselect'))}
 if(requestClose)send('paletteclose','');
}
$('buildPalette').addEventListener('cancel',e=>{e.preventDefault();closePalette(true)});
function renderPalette(p){
 const entries=arr(p&&p.entries),open=!!(p&&p.open&&entries.length);paletteKey=entries.map(e=>e.ref).join('|');
 if(!open){closePalette(false);paletteDismissedKey='';syncRows($('paletteChoices'),paletteNodes,[],()=>{},()=>{},$('paletteTitle'));return}
 text($('paletteTitle'),p.title||'Build & abilities');
 const blocked=entries.some(e=>e.reason);$('paletteRecovery').hidden=!blocked;text($('paletteRecovery'),blocked?'Close this menu, then reopen the command for the selected units. Building commands are under Build & terrain.':'');
 syncRows($('paletteChoices'),paletteNodes,entries,e=>{
  const root=button('','palette',e.ref),icon=document.createElement('img'),copy=document.createElement('span'),label=document.createElement('span'),reason=document.createElement('small');icon.alt='';copy.className='palettecopy';copy.append(label,reason);root.append(icon,copy);
  icon.addEventListener('load',()=>icon.classList.add('loaded'));icon.addEventListener('error',()=>icon.classList.remove('loaded'));return {root,icon,label,reason};
 },(n,e)=>{text(n.label,e.label);text(n.reason,e.reason);n.reason.hidden=!e.reason;n.root.disabled=!!e.reason;n.root.title=e.reason||'';if(n.icon.getAttribute('src')!==(e.icon||'')){n.icon.classList.remove('loaded');if(e.icon)n.icon.src=e.icon;else n.icon.removeAttribute('src')}},$('paletteTitle'));
 if(paletteDismissedKey===paletteKey)return;
 if(!$('buildPalette').open){closeGroups();if($('borderControls').open){paletteOpener=controlsOpener;closeControls()}else if(!paletteOpener||!paletteOpener.isConnected)paletteOpener=document.activeElement;$('buildPalette').showModal();$('buildPalette').querySelector('.drawerbody').scrollTop=0;focusWithoutScroll($('paletteTitle'))}
}
const magicTargetNodes=new Map();let magicTargetOpener=null,magicTargetSession='',magicTargetDismissed='';
function closeMagicTargets(requestClose){
 const dialog=$('magicTargets');
 if(requestClose)magicTargetDismissed=magicTargetSession;
 if(dialog.open){dialog.close();const opener=[magicTargetOpener,$('magicTargetOpener'),document.querySelector('#quickDock [data-ui=controls-open]')].find(e=>e&&e.isConnected&&!e.disabled&&e.getClientRects().length);focusWithoutScroll(opener||$('deselect'))}
 if(requestClose&&magicTargetSession)send('magictargetclose',magicTargetSession);
}
$('magicTargets').addEventListener('cancel',e=>{e.preventDefault();closeMagicTargets(true)});
function renderMagicTargets(p){
 const session=String(p&&p.session||''),open=!!(p&&p.open&&session);
 magicTargetSession=session;
 if(!open){closeMagicTargets(false);magicTargetDismissed='';syncRows($('magicTargetChoices'),magicTargetNodes,[],()=>{},()=>{},$('magicTargetTitle'));return}
 text($('magicTargetActors'),'For: '+arr(p.actors).join(', '));
 const reason=p.reason||'';text($('magicTargetBlocked'),reason);$('magicTargetBlocked').hidden=!reason;
 const entries=arr(p.entries).map(e=>({...e,ref:session+'|'+e.ref}));$('magicTargetEmpty').hidden=entries.length>0||!!reason;
 syncRows($('magicTargetChoices'),magicTargetNodes,entries,e=>{
  const root=button('','magictarget',e.ref),copy=document.createElement('span'),label=document.createElement('span'),detail=document.createElement('small');copy.className='palettecopy';copy.append(label,detail);root.append(copy);return {root,label,detail};
 },(n,e)=>{text(n.label,e.label);text(n.detail,e.reason||[e.race,Number.isFinite(Number(e.x))&&Number.isFinite(Number(e.y))?'('+e.x+', '+e.y+')':''].filter(Boolean).join(' · '));n.root.disabled=!!(reason||e.reason);n.root.dataset.blocked=String(!!e.reason);n.root.title=reason||e.reason||''},$('magicTargetTitle'));
 if(magicTargetDismissed===session)return;
 if(!$('magicTargets').open){closeGroups();if($('borderControls').open){magicTargetOpener=controlsOpener;closeControls()}closePalette(false);if(!magicTargetOpener||!magicTargetOpener.isConnected)magicTargetOpener=document.activeElement;$('magicTargets').showModal();$('magicTargets').querySelector('.drawerbody').scrollTop=0;focusWithoutScroll($('magicTargetTitle'))}
}
const groupNodes=new Map();let groupsOpener=null;
function openGroups(opener){
 if(!model||!model.controlGroups)return;
 renderGroups(model.controlGroups,true);groupsOpener=opener;$('unitGroups').showModal();$('unitGroups').querySelector('.drawerbody').scrollTop=0;focusWithoutScroll($('groupsTitle'));
}
function closeGroups(){
 if(!$('unitGroups').open)return;$('unitGroups').close();const opener=[groupsOpener,$('groupsOpener'),document.querySelector('#quickDock [data-ui=controls-open]')].find(e=>e&&e.isConnected&&!e.disabled&&e.getClientRects().length);focusWithoutScroll(opener||$('deselect'));
}
$('unitGroups').addEventListener('cancel',e=>{e.preventDefault();closeGroups()});
function renderGroups(g,force){
 $('groupsOpener').disabled=!g;if(!g){closeGroups();return}
 if(!force&&!$('unitGroups').open)return;   // the rows only while the dialog is open; openGroups builds them (hud-craft)
 text($('groupsSelection'),(g.selectedCount||0)+' selected · Keyboard: 1–9 recall, Ctrl sets, Shift adds.');
 const reasons=[g.setReason,g.addReason].filter(Boolean);text($('groupsReason'),[...new Set(reasons)].join(' '));$('groupsReason').hidden=!reasons.length;
 const snapshot=String(g.selection||'');
 syncRows($('groupRows'),groupNodes,arr(g.groups).map(e=>({...e,ref:String(e.number)})),e=>{
  const root=document.createElement('section'),heading=document.createElement('div'),title=document.createElement('h3'),count=document.createElement('span'),members=document.createElement('p'),actions=document.createElement('div'),writes=document.createElement('span');root.className='unitgroup';heading.className='groupheading';title.tabIndex=-1;count.className='badge';members.className='groupmembers';actions.className='groupactions';writes.className='groupwrite';heading.append(title,count);
  const recall=button('Recall','controlgroup',e.number+'|Select|');recall.setAttribute('aria-label','Recall group '+e.number);actions.append(recall,writes);root.append(heading,members,actions);return {root,title,count,members,recall,writes,snapshot:null,set:null,add:null};
 },(n,e)=>{
  text(n.title,'Group '+e.number);text(n.count,(e.count||0)+' units');text(n.members,arr(e.names).length?arr(e.names).join(', '):'Empty group');n.recall.disabled=!e.count||!!e.reason;n.recall.title=e.reason||'Select this group; work continues.';
  // Replace writes when their selection changes: a held tap cannot silently
  // retarget the new selection. Ordinary world updates keep the same buttons.
  if(n.snapshot!==snapshot){const held=n.writes.contains(document.activeElement);n.set=button('Set','controlgroup',e.number+'|Set|'+snapshot);n.add=button('Add','controlgroup',e.number+'|Add|'+snapshot);n.set.setAttribute('aria-label','Set group '+e.number+' from selected units');n.add.setAttribute('aria-label','Add selected units to group '+e.number);n.writes.replaceChildren(n.set,n.add);n.snapshot=snapshot;if(held)focusWithoutScroll(n.title)}
  n.set.disabled=!snapshot||!!g.setReason;n.set.title=g.setReason||'Replace this group with selected units.';n.add.disabled=!snapshot||!!g.addReason;n.add.title=g.addReason||'Add selected units to this group.';
 },$('groupsTitle'));
}
function pct(n,max){return Math.max(0,Math.min(100,(Number(n)||0)/(Number(max)||1)*100))}
function vital(parent,label,kind){const el=document.createElement('div');el.className='vital';el.innerHTML='<div class="label"><span></span><span></span></div><div class="meter"><span class="fill '+kind+'"></span></div>';text(el.firstChild.firstChild,label);parent.append(el);return el}
// Morale while in combat (Morale.dm): a bar from -100 to +100 out of the middle, and its state.
function updateMorale(el,u){if(!el)return;if(u.morale==null){if(!el.hidden)el.hidden=true;return}el.hidden=false;const m=+u.morale||0;text(el.firstChild.lastChild,(m>0?'+':'')+m+' - '+(u.mstate||'Steady'));const f=el.lastChild.firstChild;f.style.marginLeft=(m>=0?50:50+m/2)+'%';f.style.width=Math.abs(m)/2+'%';const c=m>=30?'#d9822b':m<=-30?'#5b7fd1':'#9aa3ad';f.style.setProperty('--bc',c);f.style.background=c}
function updateVital(el,value,max){text(el.firstChild.lastChild,value+' / '+max);el.lastChild.firstChild.style.width=pct(value,max)+'%'}
let defenseControlId=0;
function createUnitDefense(){
 const root=document.createElement('div'),state=document.createElement('div'),options=document.createElement('div'),label=document.createElement('label'),select=document.createElement('select'),hint=document.createElement('p');
 root.className='unitdefense';state.className='defensestate';options.className='defenseoptions';hint.className='hint';select.dataset.do='defensemode';select.id='unit-defense-'+(++defenseControlId);label.htmlFor=select.id;hint.id=select.id+'-hint';select.setAttribute('aria-describedby',hint.id);text(label,'Automatic defense');
 [['assist','Help nearby'],['self','Defend self'],['off','No response']].forEach(([value,name])=>{const option=document.createElement('option');option.value=value;text(option,name);select.append(option)});
 options.append(label,select,hint);root.append(state,options);return {root,state,select,hint};
}
function renderUnitDefense(n,u){
 const d=u.defense;n.root.hidden=!d;if(!d)return;
 n.select.dataset.unit=u.ref;if(n.select.value!==d.mode)n.select.value=d.mode;
 const status=(d.state||'')+(d.responding&&d.target?' · '+d.target:'');text(n.state,status);n.state.hidden=!status;
 text(n.hint,d.mode==='assist'?'Hears attacks within '+d.radius+' tiles in every direction on the same level, including across walls. Still needs a route.':d.mode==='self'?'Defends itself and calls nearby helpers; does not answer their calls.':'No automatic response or calls for help. Direct combat orders still work.');
}
function unitNode(u){
 let n=unitNodes.get(u.ref);if(n)return n;
 const root=document.createElement('article');root.className='card';
 const pick=button('','select',u.ref);pick.className='unitpick';
 const portrait=document.createElement('span'),initials=document.createElement('span'),image=document.createElement('img');portrait.className='portrait';portrait.setAttribute('aria-hidden','true');initials.className='portraitfallback';image.className='portraitimage';image.alt='';portrait.append(initials,image);
 image.addEventListener('load',()=>{image.classList.toggle('loaded',image.naturalWidth>0);initials.hidden=image.naturalWidth>0});image.addEventListener('error',()=>{image.classList.remove('loaded');initials.hidden=false});
 const info=document.createElement('div'),name=document.createElement('div'),meta=document.createElement('div'),tick=document.createElement('span');
 name.className='unitname';meta.className='unitmeta';tick.className='tick';info.append(name,meta);pick.append(portrait,info,tick);
 const vitals=document.createElement('div');vitals.className='vitals';
 const hp=vital(vitals,'Health',''),food=vital(vitals,'Fullness','food'),rest=vital(vitals,'Rest','rest'),carry=vital(vitals,'Carry','carry'),morale=vital(vitals,'Morale','morale');morale.hidden=true;
 const status=document.createElement('div'),warnings=document.createElement('div');status.className='status';warnings.className='warnings';
 const work=document.createElement('div');work.className='orderwork';const defense=createUnitDefense();
 const details=document.createElement('details'),summary=document.createElement('summary'),traits=document.createElement('p'),inventory=document.createElement('div'),inventoryHint=document.createElement('p');
 text(summary,'Stats, skills & body');inventory.className='inventory bag';inventoryHint.className='inventoryhint hint';const sheet=document.createElement('div');sheet.className='sheet';const skillbox=document.createElement('div');skillbox.className='skillbox';details.append(summary,traits,skillbox,sheet);
 const plate=document.createElement('div');plate.className='levelplate';const bagWrap=document.createElement('div');bagWrap.className='bagwrap';const bagTitle=document.createElement('h4');bagTitle.className='consolehead';text(bagTitle,'Bag');bagWrap.append(bagTitle,inventory,inventoryHint);
 root.append(pick,plate,vitals,status,warnings,bagWrap,defense.root,work,details);$('units').append(root);
 n={root,pick,plate,skillbox,image,initials,name,meta,tick,hp,food,rest,carry,morale,status,warnings,traits,details,summary,inventory,inventoryHint,inventoryNodes:new Map(),sheet,work,defense};unitNodes.set(u.ref,n);return n;
}
function statRows(container,rows,badWhen){const want=arr(rows).map(r=>r[0]+'\u0000'+r[1]).join('\u0001');if(container.dataset.rows===want)return;container.dataset.rows=want;container.textContent='';arr(rows).forEach(r=>{const row=document.createElement('div');row.className='statrow'+(badWhen&&badWhen(r)?' bad':'');const k=document.createElement('span'),v=document.createElement('span');text(k,r[0]);text(v,r[1]);row.append(k,v);container.append(row)})}
function renderSheet(sheet,stats){if(!stats){sheet.hidden=true;return}sheet.hidden=false;if(!sheet.firstChild){[['attributes','Attributes'],['body','Body']].forEach(([id,label])=>{const h=document.createElement('h4');text(h,label);const rows=document.createElement('div');rows.className='statrows';rows.dataset.group=id;sheet.append(h,rows)})}
 sheet.querySelectorAll('.statrows').forEach(rows=>statRows(rows,stats[rows.dataset.group],rows.dataset.group==='body'?r=>/Missing|Yes|Bleed/.test(r[1])||(/^\d+$/.test(r[1])&&+r[1]<100&&!/Age|Blood/.test(r[0])):null))}
// Bag items: one click opens the item's original choices, a double-click uses it now,
// dragging it onto another unit (Company list, hero frame, roster, the unit in 3D) gives it.
let bagClickTimer=null,bagDrag=null;
// A bag item dropped on a unit: food, a potion or a remedy can be used on them (they eat it, drink it, are
// treated with it, as the carrier hands it over: Bag.dm) or just given; anything else is given.
function bagDropTo(refs,tref,x,y){const it=arr(model&&model.units).flatMap(u=>arr(u.items)).find(i=>i.ref===refs[0]),k=it&&it.use;
 if(!k){send('giveitem',refs.join(',')+'|'+tref);return}
 const who=arr(model&&model.units).find(u=>u.ref===tref),nm=who?ownName(who.name):'them',lab=k==='remedy'?'Treat '+nm:k==='food'?'Feed '+nm:'Give '+nm+' to drink';
 const m=$('menu3d');m.innerHTML='';const head=document.createElement('div');head.className='ic-head';head.innerHTML='<span class="ic-kind">'+(k==='remedy'?'<b class="hcg hcg-cross">✚</b>':k==='food'?'<b class="hcg hcg-bowl">❦</b>':'<b class="hcg hcg-flask">⚗</b>')+'</span><div class="ic-name"><b>'+esc(it.name)+'</b><small>'+esc((refs.length>1?refs.length+' of them · ':'')+'for '+nm)+'</small></div>';m.append(head);
 const row=document.createElement('div');row.className='ic-acts';
 const mk=(label,use,cls,tip)=>{const b=document.createElement('button');b.className='ic-act'+(cls?' '+cls:'');b.innerHTML='<i>'+(use?icGlyph(k==='remedy'?'Treat':k==='food'?'Feed':'Give to drink',''):'<b class="hcg hcg-arrow">➜</b>')+'</i><span>'+esc(label)+'</span>';b.title=label+'\n'+tip;b.addEventListener('click',()=>{send('giveitem',(use?refs[0]:refs.join(','))+'|'+tref+'|'+(use?'1':'0'));v3menuClose()});return b};
 row.append(mk(lab,1,'primary','The carrier walks over and '+(k==='remedy'?'treats them with it.':k==='food'?'feeds it to them.':'gives it to them to drink.')),mk('Just give it',0,'','The carrier walks over and hands it over; they keep it.'));m.append(row);
 m.hidden=false;{/* kept on screen in the HUD's own pixels, as the right-click menu (hud-craft) */const k=hudKC()||1,VW=innerWidth/k,VH=innerHeight/k,W=m.offsetWidth||320,H=m.offsetHeight||m.scrollHeight;m.style.left=Math.max(12,Math.min(x+12,VW-W-12))+'px';m.style.top=Math.max(12,Math.min(y,VH-H-12))+'px'}queueRegions()}
function bagButton(ref,refs){const b=document.createElement('button');b.type='button';b.dataset.bag=ref;b.draggable=false;b._refs=refs&&refs.length?refs:[ref];
 b.addEventListener('click',e=>{e.preventDefault();if(b.dataset.dragged){delete b.dataset.dragged;return}const c=bagCombineFor(b);if(c){send('combine',model.useon.ref+'|'+c.ref);return}send(b.dataset.useon==='1'?'useonpick':'inventory',ref)});   // a usable item is held (UseOn.dm), else its choices; no double-click (the owner, 10-28)
 b.addEventListener('contextmenu',e=>{e.preventDefault();clearTimeout(bagClickTimer);send('inventory',ref)});
 b.addEventListener('pointerdown',e=>{if(e.button!==0)return;bagDrag={ref,refs:refs&&refs.length>1&&!e.shiftKey?refs:[ref],b,x:mx(e),y:my(e),moving:false,ghost:null}});return b}
// The held thing combines with this bag slot (UseOn.dm RmCombineList): its rule row, or null. bagCombineMark outlines
// every slot that does (the owner, 10-28: "the one click highlight to combine with").
function bagCombineFor(b){const U=model&&model.useon;if(!U||!b._refs||b._refs.includes(U.ref))return null;return arr(U.combine).find(x=>b._refs.includes(x.ref))||null}
function bagCombineMark(){document.querySelectorAll('button[data-bag]').forEach(b=>{const c=bagCombineFor(b);b.classList.toggle('bagcombine',!!c);if(c)b.dataset.combine=c.label+'\n'+(c.tip||'');else delete b.dataset.combine})}
// What a bag item is, on hover (bag bar and inventory list; the unit panel's family and skill chips too): the game's
// webview shows no native tooltips, so the title shows in a panel by the pointer: the name, then the details, then help.
{let tip=null,on='';
 const hide=()=>{if(tip&&!tip.hidden)tip.hidden=true;on=''};
 const show=(el,x,y)=>{const t=el.getAttribute('title');if(t){el.dataset.tip=t;el.removeAttribute('title')}const s=el.dataset.tip||'';if(!s||document.body.classList.contains('bagdragging'))return hide();
  if(!tip){tip=document.createElement('div');tip.id='bagtip';tip.setAttribute('role','tooltip');document.body.append(tip)}
  if(on!==s){on=s;const lines=s.split('\n'),help=lines.filter(l=>/^Click:/.test(l)),rest=lines.filter(l=>!/^Click:/.test(l));const b=document.createElement('b');let first=rest.shift()||'';
   // a hotkey in the first line ("Attack (A)", "Pause (Space): give orders…") shows as a keycap beside the name (hud-craft)
   const km=/^(.+?)\s*\(((?:(?:Ctrl|Shift|Alt|Cmd)\+)*(?:[A-Z]|Esc|Space|Tab|Enter|Backspace|Delete|Del|F\d{1,2}|[←→↑↓]))\)(?::\s*(.*))?$/.exec(first);
   if(km){first=km[1];if(km[3])rest.unshift(km[3][0].toUpperCase()+km[3].slice(1))}else{/* "Name: details" ("Work: digging, building…") shows as a short title over its details, as a hotkey line does */const ci=first.indexOf(': ');if(ci>0&&ci<=40&&first.length-ci-2>=24){/* short pairs ("Father: Gorm", "Left arm: Broken") stay one line */rest.unshift(first[ci+2].toUpperCase()+first.slice(ci+3));first=first.slice(0,ci)}else if(first.length>44){/* "Woodcutting level 20 · 4,470 XP · …": the name over the rest */const di=first.indexOf(' · ');if(di>0&&di<=40){rest.unshift(first.slice(di+3));first=first.slice(0,di)}}}
   b.textContent=first;b.className=first.length>52?'long':'';{/* else the keycap the button itself shows (the action bar's data-key), so the tip and the button agree */const kk=km?km[2]:(el.dataset&&el.dataset.key)||'';if(kk){const k=document.createElement('kbd');k.textContent=kk;b.append(k)}}tip.replaceChildren(b);if(rest.length)tip.append(document.createTextNode(rest.join('\n')));if(help.length){const h=document.createElement('small');h.textContent=help.join('\n');tip.append(h)}}
  tip.hidden=false;{/* placed and kept on screen in the HUD's own (zoomed) pixels: with window pixels it ran off the right and bottom at HUD scales above 1 (hud-craft) */const k=hudKC()||1,VW=innerWidth/k,VH=innerHeight/k,w=tip.offsetWidth,h=tip.offsetHeight;tip.style.left=Math.max(6,Math.min(x+14,VW-w-6))+'px';tip.style.top=Math.max(6,y+18+h>VH-6?y-h-10:y+18)+'px'}};
 document.addEventListener('pointermove',e=>{const el=e.target&&e.target.closest?e.target.closest('[data-bag],:is(#topbar,.world,#roster,nav,.taskmode,#heroframe,#lockbar,#foodalert,#menu3d,#usecard,#askcard,#loghist,main,#settings,#nearcard,#daycard) :is([title],[data-tip])'):null;
  /* a disabled control gets no pointer events in WebKit: find it under the pointer so its tip still says why (hud-craft) */
  const dis=!el&&e.target&&e.target.closest&&e.target.closest('#topbar,.world,#roster,nav,.taskmode,#heroframe,main,#settings')?document.elementsFromPoint(e.clientX,e.clientY).find(x=>x.matches&&x.matches('button:disabled:is([title],[data-tip])')):null;
  if(el||dis)show(el||dis,mx(e),my(e));else hide()},{passive:true});
 document.addEventListener('pointerdown',hide,true);document.addEventListener('pointerleave',hide)}
function bagDropUnit(x,y){const hit=document.elementFromPoint(x*hudKC(),y*hudKC());if(!hit)return null;const el=hit.closest('[data-do="select"][data-value],[data-unitref]:not([data-unitref=""])');if(el)return {el,ref:el.dataset.unitref||el.dataset.value};
 if(hit===$('world3d')&&V3.on){const t=v3pickThing(x,y);if(t&&t.kind==='mine'&&t.ref)return {el:null,ref:t.ref}}return null}
// Ends a bag drag from any path (release, cancel, blur, Escape, a move with no button
// held) and sweeps every ghost and highlight, so nothing is ever left on screen.
function bagDragEnd(){document.querySelectorAll('.bagghost').forEach(x=>x.remove());document.body.classList.remove('bagdragging');document.querySelectorAll('.droptarget').forEach(x=>x.classList.remove('droptarget'));bagDrag=null}
addEventListener('pointermove',e=>{const d=bagDrag;if(!d)return;if(!(e.buttons&1)){if(d.moving)d.b.dataset.dragged='1';bagDragEnd();return}if(!d.moving){if(Math.hypot(mx(e)-d.x,my(e)-d.y)<6)return;d.moving=true;clearTimeout(bagClickTimer);document.body.classList.add('bagdragging');
  d.ghost=d.b.cloneNode(true);d.ghost.className='bagghost';d.ghost.removeAttribute('data-bag');d.ghost.setAttribute('aria-hidden','true');document.body.append(d.ghost)}
 d.ghost.style.transform='translate('+(mx(e)-15)+'px,'+(my(e)-15)+'px)';const t=bagDropUnit(mx(e),my(e));document.querySelectorAll('.droptarget').forEach(x=>{if(!t||x!==t.el)x.classList.remove('droptarget')});if(t&&t.el)t.el.classList.add('droptarget')},true);
addEventListener('pointerup',e=>{const d=bagDrag;if(!d)return;if(d.moving){d.b.dataset.dragged='1';const t=bagDropUnit(mx(e),my(e));if(t)bagDropTo(d.refs,t.ref,mx(e),my(e));else text($('notice'),'Drop the item on a unit (Company list, unit card, Roster or the unit in 3D) to give it.')}bagDragEnd()},true);
addEventListener('pointercancel',bagDragEnd,true);addEventListener('blur',bagDragEnd);addEventListener('keydown',e=>{if(e.key==='Escape'&&bagDrag)bagDragEnd()},true);document.addEventListener('visibilitychange',bagDragEnd);
document.addEventListener('change',e=>{const c=e.target.closest&&e.target.closest('input[data-autouse]');if(c)send('autouse',c.dataset.autouse+'|'+(c.checked?'1':'0'))});
function renderUnits(units,UL){
 const live=new Set();
 units.forEach(u=>{
  live.add(u.ref);const n=unitNode(u);if(!u.selected&&n.root.contains(document.activeElement)&&!n.pick.contains(document.activeElement))focusWithoutScroll(n.pick);n.root.classList.toggle('selected',!!u.selected);n.pick.setAttribute('aria-pressed',u.selected?'true':'false');
  text(n.name,ownName(u.name));text(n.meta,(u.kind?u.kind+' ':'')+u.race+' · Lv '+u.level+' · '+u.role+' skill '+u.skill);text(n.plate,'Level '+u.level+' '+((u.kind?u.kind+' ':'')+(u.race||'')).toLocaleUpperCase()+' · '+u.role);text(n.tick,u.selected?'Selected':'Select');
  text(n.initials,(ownName(u.name)||u.race||'?').trim().split(/\s+/).slice(0,2).map(word=>word[0]||'').join('').toLocaleUpperCase()||'?');
  const portrait=u.portrait||'';if(n.image.dataset.source!==portrait){n.image.dataset.source=portrait;n.image.classList.remove('loaded');n.initials.hidden=false;if(portrait)n.image.src=portrait;else n.image.removeAttribute('src')}
  updateVital(n.hp,u.hp,u.maxhp);updateVital(n.food,u.fullness,u.maxfullness);updateVital(n.rest,u.energy,100);updateVital(n.carry,u.weight,u.capacity);updateMorale(n.morale,u);
  text(n.status,unitStatus(u)+(u.queued?' · '+u.queued+' queued':'')+(u.job&&u.job!=='manual'?' · Role: '+roleLabel(u):''));
  renderUnitDefense(n.defense,u);
  if(u.selected&&!hcCardDefer(n,u,'units'))renderUnitWork(n.work,u);   // near the screen only (hud-craft)
  text(n.warnings,arr(u.warnings).join(' · '));text(n.traits,u.tools+' '+u.equipment+' Cold: '+u.cold+'.');
  syncRows(n.inventory,n.inventoryNodes,arr(u.items),i=>{const root=bagButton(i.ref,i.refs),img=document.createElement('img'),label=document.createElement('span'),state=document.createElement('small');img.alt='';img.className='bagicon';label.className='baglabel';state.className='bagstate';img.addEventListener('error',()=>{img.hidden=true;label.hidden=false});img.addEventListener('load',()=>{img.hidden=false;label.hidden=true});root.append(img,label,state);return {root,img,label,state}},(item,i)=>{const nm=(i.name||'').split(' - ')[0];text(item.label,nm.replace(/([a-z])([A-Z])/g,'$1 $2').split(/\s+/).slice(0,2).map(w=>w.slice(0,4)).join(' '));const st=/Equip/i.test(i.state)?'E':(i.n>1?'×'+i.n:'');text(item.state,st);item.state.hidden=!st;item.root.title=itemLabel(i.name)+(i.state?' '+i.state:'')+(i.info?'\n'+i.info:'');item.root.dataset.useon=i.useon?'1':'';item.root.setAttribute('aria-label',i.name+(i.state?' '+i.state:''));if(i.icon&&item.img.dataset.src!==i.icon){item.img.dataset.src=i.icon;item.img.src=i.icon}if(!i.icon){item.img.hidden=true;item.label.hidden=false}},u.selected?n.summary:n.pick);
  text(n.inventoryHint,arr(u.items).length?'Click an item to hold it, then click what it is for (it is ringed), or for its choices · right-click an item for all its choices (Use, Drop, Drop all, Inspect) · drag it onto another unit to give it. E = equipped, ×n = how many.':'No carried items.');
  if(u.selected){if(!n.rename){n.rename=document.createElement('div');n.rename.className='renamebox';n.rename.innerHTML='<input maxlength="25" aria-label="New name" placeholder="Rename"><button>Rename</button>';const inp=n.rename.querySelector('input');const go=()=>{const v=inp.value.trim();if(v){send('renameunit',n.rename.dataset.ref+'|'+v);inp.value=''}else{inp.focus();toast('Type the new name first.')}};n.rename.querySelector('button').addEventListener('click',go);inp.addEventListener('keydown',e=>{if(e.key==='Enter')go()});n.inventoryHint.after(n.rename)}n.rename.dataset.ref=u.ref;n.rename.hidden=false}else if(n.rename)n.rename.hidden=true;
  if(u.selected&&arr(u.autouse).length){if(!n.autouse){n.autouse=document.createElement('div');n.autouse.className='autouse';n.inventoryHint.after(n.autouse)}const ak=JSON.stringify(u.autouse);if(n.autouse.dataset.k!==ak){n.autouse.dataset.k=ak;n.autouse.innerHTML='<b>Uses by itself</b>'+arr(u.autouse).map(r=>'<label><input type="checkbox" data-autouse="'+esc(u.ref)+'|'+esc(r.id)+'"'+(r.on?' checked':'')+'> '+esc(r.label)+'</label>').join('')}n.autouse.hidden=false}else if(n.autouse)n.autouse.hidden=true;
  if(u.selected){if(!n.later){renderSkills(n.skillbox,u.skills,u);renderSheet(n.sheet,u.stats)}if(document.body.classList.contains('overlay')&&!n.details.open)n.details.open=true}
 });
 for(const [id,n]of unitNodes)if(!live.has(id)){if(n.root.contains(document.activeElement))focusWithoutScroll($('deselect'));n.root.remove();unitNodes.delete(id)}
 $('start').hidden=units.length>0;
 {const box=$('units');if(UL){units.forEach((u,i)=>{const n=unitNodes.get(u.ref);if(n&&box.children[i]!==n.root)box.insertBefore(n.root,box.children[i]||null)})}if(box)hcPad(box,UL,hcRowStep(box,'.card:not(.selected)')||60)}   // hud-craft: its window, in order
}
function orderLabel(o){if(!o)return 'No active task';return o.kind+' · '+o.name+(o.z?' ('+o.x+', '+o.y+')':'')}
const workNodes=new WeakMap();
function renderUnitWork(parent,u){
 let n=workNodes.get(parent);
 if(!n){
  const current=document.createElement('div'),returning=document.createElement('p'),reason=document.createElement('p'),list=document.createElement('ol'),empty=document.createElement('p'),controls=document.createElement('div'),autoHint=document.createElement('p');
  current.className='currenttask';current.tabIndex=-1;returning.className='hint';reason.className='warnings';list.className='tasklist';empty.className='taskempty hint';controls.className='workbuttons';autoHint.className='autohint hint';
  const pause=button('Pause','unitpause',u.ref),stop=button('Stop','unitstop',u.ref),auto=button('Auto unload: off','autounload',u.ref),lock=button('Lock camera','lockcam',u.ref);
  stop.className='danger';stop.title='Clear direct tasks and pause roles and production; crafting attempts stay in Work.';auto.className='wide';lock.title='The camera follows this unit as it moves; pan, turn, tilt and zoom it as you like. F9 or Unlock frees it.';controls.append(pause,stop,auto,lock);parent.append(current,returning,reason,list,empty,controls,autoHint);
  n={current,returning,reason,list,empty,pause,stop,auto,lock,autoHint,tasks:new Map()};workNodes.set(parent,n);
 }
 {const on=!!(model&&model.play&&model.play.lock===u.ref);text(n.lock,on?'Unlock camera':'Lock camera');n.lock.dataset.value=on?'':u.ref;n.lock.setAttribute('aria-pressed',on?'true':'false')}
 text(n.current,(u.defense&&u.defense.responding&&u.active?'Work to resume: ':'Current: ')+orderLabel(u.active));
 n.returning.hidden=!u.resume;text(n.returning,u.resume?'Then return to: '+orderLabel(u.resume):'');n.reason.hidden=!u.blocked;text(n.reason,u.blocked);
 syncRows(n.list,n.tasks,arr(u.pending),()=>{const root=document.createElement('li'),label=document.createElement('span'),remove=button('Remove','removeorder','');root.className='taskrow';root.append(label,remove);return {root,label,remove}},(row,o)=>{text(row.label,o.index+'. '+orderLabel(o));row.remove.dataset.value=u.ref+'|'+o.index+'|'+o.ref;row.remove.setAttribute('aria-label','Remove task '+o.index+': '+o.kind+' '+o.name)},n.current);
 n.empty.hidden=arr(u.pending).length>0;text(n.empty,u.active?'No pending tasks. Add tasks queues more work.':u.craftQueued?u.craftQueued+' crafting attempt'+(u.craftQueued===1?'':'s')+' queued'+(u.paused?' · paused. Resume or manage in Work.':'. Manage in Work.'):u.job&&u.job!=='manual'?'No direct tasks. '+roleLabel(u)+(u.paused?' is paused.':' works in its assigned area.'):'No tasks assigned. Click a destination or resource.');
 text(n.pause,u.paused?'Resume':'Pause');n.pause.dataset.do=u.paused?'unitresume':'unitpause';text(n.auto,'Auto unload: '+(u.autoUnload?'on':'off'));
 n.auto.setAttribute('aria-pressed',u.autoUnload?'true':'false');
 const p=model&&model.settlement&&model.settlement.stockpile||{};text(n.autoHint,'Auto unload delivers only accepted resources. '+(p.set?'Drop-off accepts '+stockpileAccepts(p)+'.':'Set a drop-off in Work to use it.'));
}
const orderNodes=new Map();
function renderOrderUnits(units){
 const selected=units.filter(u=>u.selected),live=new Set(selected.map(u=>u.ref));
 for(const [id,n]of orderNodes)if(!live.has(id)){if(n.root.contains(document.activeElement))focusWithoutScroll($('deselect'));n.root.remove();orderNodes.delete(id)}
 selected.forEach(u=>{let n=orderNodes.get(u.ref);if(!n){const root=document.createElement('article'),name=document.createElement('strong'),state=document.createElement('p'),work=document.createElement('div'),defense=createUnitDefense();root.className='card selected';state.className='hint';root.append(name,state,defense.root,work);$('orderunits').append(root);n={root,name,state,work,defense};orderNodes.set(u.ref,n)}text(n.name,ownName(u.name)+' · '+roleLabel(u));text(n.state,unitStatus(u)+' · '+u.weight+'/'+u.capacity+' carry');renderUnitDefense(n.defense,u);if(!hcCardDefer(n,u,'orders'))renderUnitWork(n.work,u)});
 $('ordersEmpty').hidden=selected.length>0;
}
function renderDelivery(m){
 if(!hcPageShown('orders')){hcCardsStale.delivery=true;return}hcCardsStale.delivery=false;   // only while the Orders page shows; built when it opens (hcCardsNow)
 const selected=arr(m.units).filter(u=>u.selected),p=m.settlement&&m.settlement.stockpile||{},eligible=selected.filter(u=>u.z===p.z);let reason='';
 if(!selected.length)reason='Select a unit to deliver. Deselecting does not stop its work.';
 else if(!p.set)reason='Set a drop-off in Work before sending supplies.';
 else if(!eligible.length)reason='The drop-off is on level '+p.z+'. Select a unit on that level or change the stockpile location in Work.';
 const enabled=!reason;['dropOff','unloadResume'].forEach(id=>{$(id).disabled=!enabled;$(id).title=reason});
 const partial=enabled&&eligible.length<selected.length?eligible.length+' of '+selected.length+' selected units are on the drop-off level; only those units will deliver. ':'';
 text($('deliveryReason'),reason||partial+'Accepts '+stockpileAccepts(p)+'. Tools, equipment, food and seeds stay carried.');$('deliverySetup').hidden=!selected.length||(p.set&&eligible.length>0);
}
function renderMap(){
 if(!model)return;const c=$('minimap'),g=c.getContext('2d'),scale=c.width/48;
 // Unexplored land is a faint checker (not black, which read as broken); explored land is drawn a little lighter
 // so it shows on the dark panel; your units are outlined dots (gold when selected); the camera is a gold frame.
 g.clearRect(0,0,c.width,c.height);const ex=typeof model.explored==='string'&&model.explored.length===2304?model.explored:null;
 {const T=renderMap.T||(renderMap.T=document.createElement('canvas'));if(renderMap.kt!==terrain||renderMap.ke!==ex||T.width!==c.width||T.height!==c.height){renderMap.kt=terrain;renderMap.ke=ex;T.width=c.width;T.height=c.height;const tg=T.getContext('2d');terrain.forEach((color,i)=>{const x=i%48,y=Math.floor(i/48);tg.fillStyle=ex&&ex[i]!=='1'?((x+y)%2?'#1d1a13':'#221e16'):mapLift(color);tg.fillRect(x*scale,y*scale,scale+1,scale+1)})}g.drawImage(T,0,0)}   // the land drawn once, until it or the explored part changes (hud-craft, 10-25)
 const px=x=>x/model.maxx*c.width,py=y=>(1-y/model.maxy)*c.height;
 g.strokeStyle='#000';g.lineWidth=4;g.strokeRect(px(model.x-12),py(model.y+9),25/model.maxx*c.width,19/model.maxy*c.height);g.strokeStyle='#f2d27a';g.lineWidth=2;g.strokeRect(px(model.x-12),py(model.y+9),25/model.maxx*c.width,19/model.maxy*c.height);
 if(typeof model.unitCells==='string'&&model.unitCells.length===2304){const C=model.unitCells,cw=c.width/48,chh=c.height/48;for(let i=0;i<2304;i++){const v=C.charCodeAt(i)-48;if(v>0){const cx=(i%48+0.5)*cw,cy=(Math.floor(i/48)+0.5)*chh;g.fillStyle='#000';g.fillRect(cx-3.5,cy-3.5,7,7);g.fillStyle=v===2?'#ffd34a':'#9ff0a8';g.fillRect(cx-2.5,cy-2.5,5,5)}}}   // hud-craft: the server's cells (HudView.dm) at any size of company
 else arr(model.units).filter(u=>u.z===model.z).forEach(u=>{g.fillStyle='#000';g.fillRect(px(u.x)-3.5,py(u.y)-3.5,7,7);g.fillStyle=u.selected?'#ffd34a':'#9ff0a8';g.fillRect(px(u.x)-2.5,py(u.y)-2.5,5,5)});
 g.font='12px Herculanum,HudHead,Georgia,serif';g.textAlign='center';g.lineWidth=3;g.strokeStyle='#000';g.strokeText('N',c.width/2,14);g.fillStyle='#f2d27a';g.fillText('N',c.width/2,14);g.textAlign='start';
 arr(model.targets).filter(t=>t.z===model.z).forEach(t=>{g.strokeStyle='#ffb27d';g.beginPath();g.arc(px(t.x),py(t.y),4,0,Math.PI*2);g.stroke();if(t.index){g.fillStyle='#ffe4b2';g.font='bold 11px HudText,Georgia,serif';g.fillText(t.index,px(t.x)+5,py(t.y)-3)}});
 g.fillStyle='#fff';g.fillRect(px(model.x)-1,py(model.y)-1,2,2);
 drawPings(g,px,py,model.z,1);
}
// A terrain colour 25% of the way to white, so explored land reads on the dark minimap (cached per colour).
const mapLiftCache=new Map();
function mapLift(c){let v=mapLiftCache.get(c);if(v)return v;const m=/^#?([0-9a-f]{6})$/i.exec(String(c));if(!m)return c;const n=parseInt(m[1],16),f=x=>Math.round(x+(255-x)*0.25);v='rgb('+f(n>>16&255)+','+f(n>>8&255)+','+f(n&255)+')';mapLiftCache.set(c,v);return v}
// Recent events as pulsing rings: red fights, grey deaths, purple births, amber problems, green wins.
const PING_COL={fight:'#ff5a45',death:'#c8c8c8',birth:'#d6a6ff',problem:'#ffb340',good:'#7fe36a'};
function drawPings(g,px,py,z,scale){const t=Date.now()/1000;for(const [x,y,pz,kind,ago] of arr(model&&model.pings)){if(pz!==z)continue;const f=(t*1.4+x*0.13)%1;g.strokeStyle=PING_COL[kind]||'#fff';g.globalAlpha=Math.max(0.15,1-ago/60)*(1-f);g.lineWidth=2;g.beginPath();g.arc(px(x),py(y),(3+f*9)*scale,0,Math.PI*2);g.stroke();g.globalAlpha=1;g.fillStyle=PING_COL[kind]||'#fff';g.fillRect(px(x)-1.5,py(y)-1.5,3,3)}}
setInterval(()=>{if(model&&arr(model.pings).length)renderMap()},120);
$('minimap').addEventListener('pointerup',e=>{if(!model)return;const r=e.currentTarget.getBoundingClientRect();send('camera',Math.round((mx(e)-r.left)/r.width*model.maxx)+','+Math.round((1-(my(e)-r.top)/r.height)*model.maxy))});
$('minimap').addEventListener('keydown',e=>{const dirs={ArrowUp:'n',ArrowDown:'s',ArrowLeft:'w',ArrowRight:'e'};if(dirs[e.key]){e.preventDefault();send('pan',dirs[e.key])}});
let settlementKey='',commandsKey='',goalsKey='';
const jobNodes=new Map(),recipeNodes=new Map(),settlementUnitNodes=new Map();
let zonesKey='';
function renderZones(m){const Z=m.zones;if(!Z)return;const key=JSON.stringify(Z);if(key===zonesKey)return;zonesKey=key;const F=Z.filters||{};
 const sel=$('zoneFilter');if(!sel.childElementCount)Object.entries(F).forEach(([k,l])=>{const o=document.createElement('option');o.value=k;o.textContent=l;sel.append(o)});
 const box=$('zoneList');box.innerHTML=arr(Z.zones).length?arr(Z.zones).map(z=>'<div class="zone"><span><b>'+esc(z.name)+'</b> <small>'+z.x+', '+z.y+' · L'+z.z+' · '+z.items+' item'+(z.items===1?'':'s')+'</small></span><select data-zone="'+esc(z.id)+'" aria-label="Zone filter">'+Object.entries(F).map(([k,l])=>'<option value="'+k+'"'+(k===z.filter?' selected':'')+'>'+esc(l)+'</option>').join('')+'</select><button data-do="gotoplace" data-value="'+z.x+'|'+z.y+'|'+z.z+'">Go</button><button data-do="zoneremove" data-value="'+esc(z.id)+'" aria-label="Remove '+esc(z.name)+'">×</button></div>').join(''):'<p class="hint">No zones yet.</p>'}
$('zoneAddUnit').addEventListener('click',()=>{send('zoneadd',$('zoneFilter').value+'|unit');zonesKey=''});
$('zoneAddCam').addEventListener('click',()=>{send('zoneadd',$('zoneFilter').value+'|camera');zonesKey=''});
document.addEventListener('change',e=>{const z=e.target.closest&&e.target.closest('select[data-zone]');if(z){send('zonefilter',z.dataset.zone+'|'+z.value);zonesKey=''}});
function renderSettlement(s){
 if(!hcPageShown('work')){hcCardsStale.work=true;return}hcCardsStale.work=false;   // only while the Work page shows; built when it opens (hcCardsNow)
 s=s||{};const key=JSON.stringify(s);if(key===settlementKey)return;settlementKey=key;
 const p=s.stockpile||{};text($('stockpile'),p.set?'Drop-off at '+p.x+', '+p.y+' · level '+p.z:'No drop-off assigned. Set one at a selected unit or the view centre.');text($('workNotice'),s.message||'');text($('stockAccepts'),'Accepts '+(Array.isArray(p.accepts)?p.accepts.join(' + '):(p.accepts||'wood + stone'))+'. Tools, equipment, food and seeds stay carried.');$('stockfilters').querySelectorAll('button').forEach(b=>b.setAttribute('aria-pressed',b.dataset.value===(p.filter||'mixed')?'true':'false'));
 const workers=arr(s.units).filter(u=>arr(model.units).some(x=>x.ref===u.ref&&x.selected));
 // Status changes retain an in-progress tap. Selection changes create new
 // controls so a held tap cannot be redirected to a different worker.
 const actors=JSON.stringify(workers.map(u=>u.ref).sort());
 syncRows($('jobs'),jobNodes,arr(s.jobs).map(j=>({...j,ref:actors+'|'+j.id})),j=>({root:button('','job',j.id)}),(n,j)=>{text(n.root,j.label);n.root.disabled=!workers.length;n.root.setAttribute('aria-pressed',String(!!workers.length&&workers.every(u=>u.job===j.id)));n.root.setAttribute('aria-describedby','roleReason')},$('roleHeading'));
 text($('roleReason'),workers.length?'Assigning a role replaces selected units’ current tasks.':'Select your own workers to assign a role.');
 const reasons=[];
 syncRows($('recipes'),recipeNodes,arr(s.recipes).map(r=>({...r,ref:actors+'|'+r.id})),r=>{const root=button('','craft',r.id),label=document.createElement('span'),small=document.createElement('small');root.append(label,small);return {root,label,small}},(n,r)=>{text(n.label,r.label);text(n.small,r.cost);n.root.disabled=!workers.length||!r.available;n.root.title=r.reason||r.requirement||'';if(r.reason&&!reasons.includes(r.reason))reasons.push(r.reason)},$('productionHeading'));
 text($('recipeReason'),reasons.join(' · ')||'Each click queues one item. Recipes use up materials, and crafting can fail: less often with skill.');
 syncRows($('workunits'),settlementUnitNodes,workers,u=>{const root=document.createElement('div'),strong=document.createElement('strong'),small=document.createElement('small');root.className='workunit';root.append(strong,small);return {root,strong,small}},(n,u)=>{text(n.strong,ownName(u.name)+' · '+u.job+' · '+({1:'high',2:'normal',3:'low'}[u.priority]||u.priority)+' priority');text(n.small,(u.paused?'Role paused · ':'')+u.status+' · Production: '+(arr(u.queue).join(', ')||'empty')+(u.area?' · Area '+u.area.x+', '+u.area.y+' / '+u.area.radius+' tiles':''))},$('roleHeading'));
}
function renderCommands(commands){
 const key=JSON.stringify(commands);if(key===commandsKey)return;commandsKey=key;
 const mental=commands.find(c=>c.id==='mental'),reason=mental?mental.reason:'Select an Illithid unit first.';$('mentalAbilities').disabled=!mental||!!reason;$('mentalAbilities').title=reason||'';text($('mentalReason'),reason||'Open the original Illithid powers menu. Some choices enter a placement mode.');
 const target=commands.find(c=>c.id==='magictarget'),targetReason=target?target.reason:'Select a unit first.';$('magicTargetOpener').disabled=!target||!!targetReason;$('magicTargetOpener').title=targetReason||'';text($('magicTargetReason'),targetReason||'Choose a visible unit, then cast its spell separately. Current work continues.');
 syncRows($('commands'),commandNodes,commands.map(c=>({...c,ref:c.id})),c=>{const root=button('','action',c.id),label=document.createElement('span'),key=document.createElement('kbd');root.append(label,key);return {root,label,key}},(n,c)=>{text(n.label,c.label);text(n.key,c.key||'Click');n.root.disabled=!!c.reason;n.root.title=c.reason||''},$('commands').parentElement.querySelector('summary'));
}
const borderNodes=new Map(),borderGroups=new Map();
const controlGroups=[{id:'units',label:'Units',short:'Units'},{id:'gather',label:'Gather & inventory',short:'Gather'},{id:'build',label:'Build & terrain',short:'Build'},{id:'camera',label:'Camera & world',short:'Camera'},{id:'people',label:'People & settings',short:'People'}];
const controlOrder={units:['interact','all','area','stop','equip','unequip'],gather:['pickwood','pickstone','pickfood','pickores','pickgems','pickseeds','pickingots','pickbones','pickskin','pickarmour','pickarrows','dropwood','dropstone','dropfood','dropores','dropgems','dropbones','dropingots','droparmour','tearskin','tearmeat'],build:['build','digpaint','digadd','digremove','autodig'],camera:['goto','zup','zdown','waypoint','warp','coords','pointer','daynight'],people:['say','msg','who','updates','race']};
// These are existing player actions, deliberately separate from border IDs.
const extraControls={
 guard:['units','Open the selected units’ guard choices.'],
 rename:['units','Give selected units a name while their work continues.'],
 unitsay:['units','Speak as the selected units to people nearby.'],
 emote:['units','Describe what the selected units are doing.'],
 leader:['units','Choose a king or queen, or ask a current leader to step down.'],
 mental:['units','Choose the selected Illithid units’ mental abilities.'],
 magictarget:['units','Choose who a later spell will target.'],
 clear:['units','Clear selection while units keep working.'],
 jump:['camera','Move the camera to the latest attack alert.'],
 worldchat:['people','Turn world chat on or off.'],
 clanchat:['people','Speak to your clan.'],
 allyadd:['people','Add a player to your allies.'],
 allyremove:['people','Remove a player from your allies.'],
 allylist:['people','See your current allies.'],
 legends:['people','Read the legends of this world.'],
 createclan:['people','Found a clan with its own name and members.'],
 clanmembers:['people','See who is in your clan.'],
 shrines:['people','List the shrines and who holds them.'],
 tapestry:['build','Hang or take down your clan tapestry on a wall next to a selected unit.'],
 event:['people','Join the current world event, when one is running.'],
 music:['people','Stop the current music.'],
 help:['people','Read the controls and actions guide.']
};
let controlGroup='all',controlsOpener=null;
function controlGroupFor(c){return controlGroups.some(g=>g.id===c.group)?c.group:controlGroups.find(g=>controlOrder[g.id].includes(c.id))?.id||'people'}
let borderLast=null;
function openControls(group,opener){
 if(borderLast)renderBorderControls(borderLast,true);   // the rows as they are now (they wait while the drawer is shut)
 controlsOpener=opener;controlGroup=controlGroups.some(g=>g.id===group)?group:'all';$('controlSearch').value='';filterControls();
 if(!$('borderControls').open)$('borderControls').showModal();$('borderControls').querySelector('.drawerbody').scrollTop=0;$('borderControls').querySelector('[data-ui=controls-close]').focus({preventScroll:true});
}
function closeControls(){if(!$('borderControls').open)return;$('borderControls').close();const opener=controlsOpener&&controlsOpener.isConnected&&controlsOpener.getClientRects().length?controlsOpener:document.querySelector('#quickDock [data-ui=controls-open]');focusWithoutScroll(opener)}
$('borderControls').addEventListener('cancel',e=>{e.preventDefault();closeControls()});
$('controlSearch').addEventListener('input',filterControls);
function initControlGroups(){
 if(borderGroups.size)return;
 $('borderCatalog').replaceChildren();
 const all=document.createElement('button');all.dataset.ui='controls-filter';all.dataset.group='all';text(all,'All');$('borderFilters').append(all);
 controlGroups.forEach(g=>{
  const section=document.createElement('section'),title=document.createElement('h3'),list=document.createElement('div'),filter=document.createElement('button'),opener=document.createElement('button');section.className='controlgroup';section.dataset.group=g.id;text(title,g.label);section.append(title,list);$('borderCatalog').append(section);
  filter.dataset.ui='controls-filter';filter.dataset.group=g.id;text(filter,g.short);filter.title=g.label;$('borderFilters').append(filter);
  opener.dataset.ui='controls-open';opener.dataset.group=g.id;text(opener,g.short);opener.title=g.label;opener.setAttribute('aria-label','Open '+g.label+' commands');opener.setAttribute('aria-haspopup','dialog');opener.setAttribute('aria-controls','borderControls');$('commandCategories').append(opener);
  borderGroups.set(g.id,{section,title,list,filter,opener});
 });
}
function filterControls(){
 const terms=$('controlSearch').value.trim().toLocaleLowerCase().split(/\s+/).filter(Boolean),used=new Set();let visible=0;
 for(const n of borderNodes.values()){
  const match=(controlGroup==='all'||controlGroup===n.group)&&terms.every(t=>n.search.includes(t));n.row.hidden=!match;if(match){visible++;used.add(n.group)}
 }
 for(const [id,g]of borderGroups)g.section.hidden=!used.has(id);
 $('borderFilters').querySelectorAll('button').forEach(b=>b.setAttribute('aria-pressed',b.dataset.group===controlGroup?'true':'false'));
 $('clearControlSearch').disabled=!$('controlSearch').value;
 text($('controlsCount'),visible===borderNodes.size?visible+' controls':visible+' of '+borderNodes.size+' controls');
 $('controlsEmpty').hidden=visible>0||!borderNodes.size;
 text($('controlsEmptyText'),terms.length?'No controls match “'+$('controlSearch').value.trim()+'”. Try another word or view all controls.':'No controls in this category.');
}
function renderBorderControls(border,force){
 initControlGroups();
 $('borderVisibility').hidden=!border;
 if(!border)return;
 borderLast=border;   // the drawer's rows are built from it when it opens (openControls)
 {const period=arr(border.controls).find(c=>c.id==='daynight');$('worldDayIcon').hidden=!period?.icon;if(period?.icon&&$('worldDayIcon').getAttribute('src')!==period.icon)$('worldDayIcon').src=period.icon}
 if(!force&&borderNodes.size&&!$('borderControls').open)return;   // the drawer shut: its ~100 rows wait for it to open (29-34 ms a HUD update in WebKit after a selection change, the chop hitch: rts-feel)
 const visible=!!border.visible;
 text($('borderVisibility'),visible?'Hide classic border':'Show classic border');$('borderVisibility').dataset.value=visible?'hide':'show';
 text($('borderVisibilityHint'),visible?'Classic icons are visible around the map. These labeled controls stay available.':'Classic border is off. Its commands and more player actions are available here.');
 arr(border.groups).forEach(g=>{const n=borderGroups.get(g.id);if(n){text(n.title,g.label);n.filter.title=g.label;n.opener.title=g.label;n.opener.setAttribute('aria-label','Open '+g.label+' commands')}});
 const period=arr(border.controls).find(c=>c.id==='daynight');$('worldDayIcon').hidden=!period?.icon;if(period?.icon&&$('worldDayIcon').getAttribute('src')!==period.icon)$('worldDayIcon').src=period.icon;
 const live=new Set();
 const known=new Set(arr(border.controls).map(c=>c.id));
 const extra=arr(model?.commands).filter(c=>Object.hasOwn(extraControls,c.id)&&!known.has(c.id)).map(c=>({...c,group:extraControls[c.id][0],description:extraControls[c.id][1],route:'action'}));
 const controls=arr(border.controls).concat(extra).sort((a,b)=>{const ga=controlGroupFor(a),gb=controlGroupFor(b);if(ga!==gb)return controlGroups.findIndex(g=>g.id===ga)-controlGroups.findIndex(g=>g.id===gb);const order=controlOrder[ga],ia=order.indexOf(a.id),ib=order.indexOf(b.id);return (ia<0?99:ia)-(ib<0?99:ib)});
 controls.forEach(c=>{
  const groupId=controlGroupFor(c),group=borderGroups.get(groupId);live.add(c.id);
  let n=borderNodes.get(c.id);
  if(!n){
   const row=document.createElement('article'),icon=document.createElement('img'),copy=document.createElement('div'),label=document.createElement('h4'),meta=document.createElement('div'),description=document.createElement('p'),action=document.createElement('div'),reason=document.createElement('p');
   row.className='bordercontrol';row.dataset.control=c.id;icon.alt='';meta.className='controlmeta';reason.className='reason';copy.append(label,meta,description,action,reason);row.append(icon,copy);group.list.append(row);n={row,icon,label,meta,description,action,reason,indicator:null};borderNodes.set(c.id,n);
  }
  if(n.row.parentNode!==group.list)group.list.append(n.row);n.group=groupId;n.search=[c.label,c.description,c.key,c.id,group.title.textContent].filter(Boolean).join(' ').toLocaleLowerCase();n.row.dataset.active=c.active?'true':'false';
  text(n.label,c.label);text(n.description,c.description);{const mt=[c.key?'Shortcut <kbd>'+esc(c.key)+'</kbd>':'',c.active?'Active':''].filter(Boolean).join(' · ');if(n.meta.dataset.k!==mt){n.meta.dataset.k=mt;n.meta.innerHTML=mt}n.meta.hidden=!mt}
  n.row.dataset.hasIcon=c.icon?'true':'false';n.icon.hidden=!c.icon;if(c.icon&&n.icon.getAttribute('src')!==c.icon)n.icon.src=c.icon;
  if(n.indicator!==!!c.indicator){
   n.indicator=!!c.indicator;n.action.replaceChildren();
   if(n.indicator){const info=document.createElement('span');info.className='controlindicator';text(info,'Status indicator · no action');n.action.append(info);n.run=null}
   else{n.run=button('',c.route||'borderaction',c.id);n.action.append(n.run)}
  }
  if(n.run){text(n.run,'Use '+c.label);n.run.disabled=!!c.reason;n.run.title=c.reason||''}
  text(n.reason,c.reason||'');n.reason.hidden=!c.reason;
 });
 for(const [id,n]of borderNodes)if(!live.has(id)){n.row.remove();borderNodes.delete(id)}
 filterControls();
}
