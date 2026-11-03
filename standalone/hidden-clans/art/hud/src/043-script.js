/* The bottom bar's modes (hud-controls, 10-26; the owner: "the gather on should change the hud buttons to match ... then
   build mode can be build and seting blocks and etc"; picked from the stills). One bar, three sets: the main bar; the
   Gather bar while Gather is on (Gather zone in Plan's place, its options in a row above); the Build bar (B). The server's
   side is gathering's (selautounload, gatherzone, stockzone). */
const HB={build:false,takes:'all',mode:'main'};
/* the board's rows for the Gather zone's kinds (Jobs.dm rm_jz_kinds): their colour, ground outline and group */
if(!JB_KIND.gather)JB_KIND.gather=['Gather','#d9b45f',[0.85,0.71,0.37,1]];if(!JB_KIND.fish)JB_KIND.fish=['Fishing','#5aa9e6',[0.35,0.66,0.9,1]];
const HB_TAKES={all:'All',wood:'Wood',stone:'Stone',food:'Food'};
try{const v=localStorage.getItem('rm-hb-takes');if(HB_TAKES[v])HB.takes=v}catch(e){}
function hbBtn(id,label,title,key){let b=$(id);if(b)return b;b=document.createElement('button');b.id=id;b.type='button';b.className='hbx';
 b.innerHTML='<b class="gear"></b><span>'+label+'</span>';b.title=title;if(key)b.dataset.key=key;b.hidden=true;return b}
function hbMake(){const d=$('quickDock');if(!d||$('btnBuild'))return;const at=(el,ref)=>{if(ref&&ref.parentNode===d)d.insertBefore(el,ref.nextSibling);else d.appendChild(el)};
 const g=$('btnGather'),p=$('btnPlan');
 const B=hbBtn('btnBuild','Build','Build (B)\nThe Build bar: setting blocks, the Place list, workbenches and construction. B or Esc goes back.','B');at(B,p||g);
 at(hbBtn('btnGZone','Gather zone','Gather zone\nDrag a zone on the ground: the selected units gather what it takes (the row above), and so does the job board, as with Work\'s + Wood and + Stone.\nClick: Add tasks on, they finish their tasks first.'),p||g);
 let r=B;for(const [id,l,t] of [['btnBBlocks','Set blocks','Set blocks\nPlan mode\'s Build tool: walls, towers and houses, block by block; mark them level by level, then queue them; builders fetch the stone or logs and set them.'],
  ['btnBList','Place list','Place list\nEverything you can build: Structure first (stone and wooden walls block by block, doors, floors, digging: they open Plan mode), then furniture, workshops, traps, bridges, stairs and roads.'],
  ['btnBBench','Workbenches','Workbenches\nThe workshops you can build; click a built one to craft at it.'],
  ['btnBSites','Construction','Construction\nThe sites, who works them and what each waits for.']]){const b=hbBtn(id,l,t);at(b,r);r=b}
 const R=document.createElement('div');R.id='hbRow';R.hidden=true;R.setAttribute('role','group');R.setAttribute('aria-label','Gather options');
 for(const b of [hbBtn('btnGTakes','Takes: All','Takes: what a Gather zone gathers\nAll, Wood, Stone or Food (a fishing zone).\nClick: the next one.'),
  hbBtn('btnGUnload','Auto unload','Auto unload: for the selected units\nOn: they take what they carry to the stockpile by themselves when full.'),
  hbBtn('btnGStock','Stockpile here','Stockpile here\nA store round the selected unit (5 by 5), like Work\'s + Store: haulers and gatherers bring goods to it. With none on this level yet, it is the drop-off too.')]){b.classList.remove('hbx');R.appendChild(b)}
 (d.closest('.taskmode')||d).appendChild(R)}
function hbSet(){hbMake();const d=$('quickDock');if(!d)return;let m=null;try{m=model}catch(e){}
 HB.mode=HB.build?'build':(m&&m.gather)?'gather':'main';const md=HB.mode,show=(e,on)=>{if(typeof e==='string')e=$(e);if(e&&e.hidden!==!on)e.hidden=!on};
 show('btnLethal',md!=='build');show('btnPlan',md==='main');show('btnBuild',md!=='gather');
 for(const e of [$('btnAttack'),d.querySelector('[data-value=interact]'),$('btnGather')])show(e,md!=='build');
 show('btnGZone',md==='gather');show('hbRow',md==='gather');
 for(const id of ['btnBList','btnBBlocks','btnBBench','btnBSites'])show(id,md==='build');
 for(const id of ['btnGTakes','btnGUnload','btnGStock'])show(id,true);
 const B=$('btnBuild');if(B)B.setAttribute('aria-pressed',String(md==='build'));
 const sel=!!(m&&m.selection);for(const id of ['btnGZone','btnGUnload','btnGStock'])if($(id))$(id).disabled=!sel;
 {const v=m&&m.selAutoUnload,b=$('btnGUnload');if(b){b.querySelector('span').textContent=v==='mixed'?'Unload: mixed':'Auto unload';b.setAttribute('aria-pressed',String(v==='on'))}}
 const tk=$('btnGTakes');if(tk){tk.querySelector('span').textContent='Takes: '+HB_TAKES[HB.takes];tk.dataset.v=HB.takes}
 document.body.dataset.bar=md}
function hcBar(m){HB.build=m==='build';hbSet();queueRegions()}
function hbPanel(tab){send('tab',tab);if(overlayHost){document.body.classList.add('panel-open');queueRegions()}}
function hbBusy(){try{return !!(model&&model.mode)||!!V3.shop||!!(V3.build&&V3.build.mode)||!!($('btnPlan')&&$('btnPlan').getAttribute('aria-pressed')==='true')}catch(e){return false}}
function hbClick(id){let m=null;try{m=model}catch(e){}
 if(id==='btnBuild')hcBar(HB.build?'main':'build');
 else if(id==='btnGZone'){send('gatherzone',HB.takes+'|'+(m&&m.queue?1:0))}   /* the board's own drag starts; the selected join the row it makes */
 else if(id==='btnGTakes'){const k=Object.keys(HB_TAKES);HB.takes=k[(k.indexOf(HB.takes)+1)%k.length];try{localStorage.setItem('rm-hb-takes',HB.takes)}catch(e){}hbSet()}
 else if(id==='btnGUnload')send('selautounload',m&&m.selAutoUnload==='on'?'off':'on');
 else if(id==='btnGStock')send('stockzone','unit');   /* a whole-area store round the first selected unit (gathering) */
 else if(id==='btnBList'){buildView='catalog';hbPanel('build')}
 else if(id==='btnBBench'){buildView='catalog';buildCat='workshops';buildCatalogKey='';hbPanel('build')}
 else if(id==='btnBSites'){buildView='tasks';hbPanel('build')}
 else if(id==='btnBBlocks'){const p=$('btnPlan');if(p&&p.getAttribute('aria-pressed')!=='true')p.click();requestAnimationFrame(()=>requestAnimationFrame(()=>{const t=document.querySelector('#pmBar [data-pmtool=build]');if(t)t.click()}))}}
document.addEventListener('click',e=>{const b=e.target.closest('#quickDock .hbx,#hbRow button');if(b&&!b.disabled)hbClick(b.id)});
/* B: the Build bar; Esc leaves it when nothing else is under way */
function hbKey(k){if(k==='b'){hcBar(HB.build?'main':'build');return true}return false}
addEventListener('keydown',e=>{if(e.metaKey||e.ctrlKey||e.altKey||/^(INPUT|TEXTAREA|SELECT)$/.test((e.target&&e.target.tagName)||''))return;const k=(e.key||'').toLowerCase();
 if(k==='b'&&hbKey(k))e.preventDefault();else if(k==='escape'&&HB.build&&!hbBusy())hcBar('main')});
{const k0=window.key3d;if(typeof k0==='function')window.key3d=function(k){const s=String(k);if(s==='b'&&hbKey(s))return;if(s==='escape'&&HB.build&&!hbBusy()){hcBar('main');return}return k0(k)}}   /* from the game window (skin.dmf, Attack.dm) */
{const u0=window.updateHUD;if(typeof u0==='function')window.updateHUD=function(raw){u0(raw);try{hbSet()}catch(e){console.error(e)}}}
