// ===== The population overview (Jobs.dm RmPopTick): Village > Roster's top card, the whole realm at a glance =====
// Counts by work, need and doing from the last full sweep (counted a slice a pass, so its age is shown); a chip selects
// those units. Zero chips stay, dimmed, so the card doesn't jump as counts change.
const POP_GROUPS=[['Work',[[4,'Working a job'],[5,'Free on the job board'],[6,'Manual'],[7,'Idle']]],['Needs',[[8,'Hungry'],[9,'Need rest'],[10,'Low health'],[11,'Bleeding'],[12,'Cold'],[13,'Limb lost']]],['Doing',[[14,'Asleep'],[15,'Eating or resting'],[16,'Carrying in'],[17,'Fighting']]]];
function jbPopRender(){const m=jbModel(),box=$('popCard');if(!box||!m||currentTab!=='village')return;const P=m.pop,c=P&&Array.isArray(P.c)?P.c:null;
 const roles=P&&P.roles&&typeof P.roles==='object'?Object.entries(P.roles).filter(([,n])=>n>0).sort((a,b)=>b[1]-a[1]):[],jl=new Map(arr(m.settlement&&m.settlement.jobs).map(j=>[j.id,j.label]));
 const key=JSON.stringify([c,roles,P&&P.age]);if(box.dataset.k===key)return;box.dataset.k=key;box.hidden=false;
 if(!box.dataset.wired){box.dataset.wired='1';box.addEventListener('click',e=>{const b=e.target.closest('button[data-pop]');if(b&&!b.disabled)send('popselect',b.dataset.pop)})}
 if(!c){box.innerHTML='<div class="poph"><b>Population</b><small>counting…</small></div>';return}
 const n=v=>(+v||0).toLocaleString(),age=P.age>=0?(P.age<5?'just counted':'counted '+(P.age<120?P.age+' s':Math.round(P.age/60)+' min')+' ago'):'';
 const chip=(k,l,v,warn)=>'<button type="button" class="popc'+(v?'':' zero')+(warn&&v?' warn':'')+'" data-pop="'+esc(k)+'"'+(v?'':' disabled')+' title="'+esc(l)+'\nClick: select them (up to 500).">'+esc(l)+' <b>'+n(v)+'</b></button>';
 let h='<div class="poph"><b>Population</b><span><b>'+n(c[1])+'</b> people'+(c[2]?' · '+n(c[2])+' animals':'')+'</span><small>'+esc(age)+'</small></div>';
 for(const [g,L] of POP_GROUPS){h+='<div class="popg"><span class="popl">'+g+'</span>'+L.map(([k,l])=>chip(k,l,c[k-1],g==='Needs')).join('')+(g==='Work'?roles.map(([id,v])=>chip('role:'+id,jl.get(id)||id,v,false)).join(''):'')+'</div>'}
 box.innerHTML=h}
{const st=document.createElement('style');st.textContent=
 '#popCard{margin:0 0 10px;padding:8px 9px;border:1px solid var(--mband,#3a3020);border-radius:4px;background:rgba(0,0,0,.25)}#popCard[hidden]{display:none}'+
 '#popCard .poph{display:flex;align-items:baseline;gap:8px;flex-wrap:wrap;margin:0 0 6px}#popCard .poph>b{font:600 15px HudText,Georgia,serif;color:var(--macc,#f2d27a)}#popCard .poph span{font-size:12px;color:var(--mink,#e8dcc0)}#popCard .poph span b{font-variant-numeric:lining-nums tabular-nums}#popCard .poph small{margin-left:auto;font-size:11.25px;color:var(--muted)}'+
 '#popCard .popg{display:flex;flex-wrap:wrap;gap:4px;align-items:center;margin:3px 0}#popCard .popl{flex:0 0 46px;font-size:11.25px;color:var(--muted);text-transform:uppercase;letter-spacing:.06em}'+
 '#popCard .popc{min-height:24px!important;padding:1px 7px!important;font-size:11.25px;white-space:nowrap}#popCard .popc b{font-variant-numeric:lining-nums tabular-nums;color:var(--macc,#f2d27a)}#popCard .popc.zero{opacity:.5}#popCard .popc.warn b{color:#ffcf6e}body.cb #popCard .popc.warn b{color:#e6c229}';
 document.head.appendChild(st)}
// The Work button's badge: how many job board rows need the player (as the Village button counts the idle).
function jbBadge(){const m=jbModel(),wb=document.querySelector('nav [data-value=work]');if(!wb||!m||!m.jobs)return;const n=(+m.jobs.needs||0)+arr(m.chain&&m.chain.needs).reduce((a,v)=>a+(+v||0),0),bd=n>99?'99+':n>0?String(n):'';
 if(wb.dataset.tipBase==null)wb.dataset.tipBase=wb.dataset.tip||wb.getAttribute('title')||'Work';
 if(wb.dataset.badge!==bd){wb.dataset.badge=bd;wb.dataset.tip=wb.dataset.tipBase+(n?'\n'+n+(n===1?' thing needs':' things need')+' you: see Supply chain on Work':'');wb.removeAttribute('title')}}

// ===== The Realm overview (hud-rework 10-27, owner: "build them"): the Realm page's first tab, the realm at a glance =====
// Songs of Syx's three questions on one screen for a realm of thousands: are my people all right (the population
// counts, each a button that selects them), is my economy keeping up (the goods in store, their change per hour and how
// long a falling one lasts: RealmOverview.dm), where are my hands (every workplace's workers against wanted, output and
// what it is doing), and a short list of what needs the player. Drawn again only when its numbers change.
let realmView='overview';let realmOvSort='count';
const RO_BAND=[[0,'People'],[4,'Working'],[5,'Free'],[7,'Idle'],[8,'Hungry','w'],[10,'Low health','w'],[11,'Bleeding','bad'],[12,'Cold','w'],[17,'Fighting','bad']];
function roName(s){s=String(s||'');return s.charAt(0).toUpperCase()+s.slice(1)}
function roLasts(n,rate){if(rate==null||rate>=0||!n)return '';const h=n/-rate;return h<1?Math.max(1,Math.round(h*60))+' min':h<48?(Math.round(h*10)/10)+' h':Math.round(h/24)+' days'}
function renderRealmOverview(m){const body=document.body,ov=$('realmOverview'),rb=$('realmBody');if(!ov||!rb)return;
 if(currentTab!=='realm'){body.classList.remove('rwide');return}
 document.querySelectorAll('.rsubtabs button').forEach(b=>{const v=b.dataset.realmview===realmView?'true':'false';if(b.getAttribute('aria-selected')!==v)b.setAttribute('aria-selected',v)});
 rb.hidden=realmView!=='realm';ov.hidden=realmView!=='overview';{const on=realmView==='overview'&&!!overlayHost;if(body.classList.contains('rwide')!==on)body.classList.toggle('rwide',on)}
 if(realmView!=='overview')return;
 const P=m.pop,c=P&&Array.isArray(P.c)?P.c:null,O=m.overview||null,J=arr(m.jobs&&m.jobs.rows).filter(r=>r.kind!=='stock');
 const key=JSON.stringify([c,O,J.map(r=>[r.id,r.name,r.count,r.want,r.rate,r.paused,r.problem,r.status,r.amount,r.progress,jbLineText(r)[0]]),realmOvSort]);if(ov.dataset.k===key)return;ov.dataset.k=key;
 const n=v=>(+v||0).toLocaleString(),val=k=>c?(k===0?c[1]:c[k-1]):null;
 let h='<div class="roband" role="group" aria-label="Your people">'+RO_BAND.map(([k,l,cls])=>{const v=val(k);return '<button type="button" class="'+(k?'':'all ')+(cls&&v?cls:'')+(v?'':' zero')+'"'+(k&&v?' data-pop="'+k+'"':' disabled')+' title="'+esc(l+(k?'\nClick: select them (up to 500).':''))+'"><span>'+esc(l)+'</span><b>'+(c?n(v):'…')+'</b></button>'}).join('')+'</div>';
 // what needs the player: the worst numbers, one line each, a click to them
 const need=[];if(c){if(val(11))need.push(['bad',n(val(11))+' bleeding: they bleed until someone treats them','pop',11]);if(val(8))need.push(['w',n(val(8))+' hungry','pop',8]);if(val(10))need.push(['w',n(val(10))+' on low health','pop',10]);if(val(12))need.push(['w',n(val(12))+' cold','pop',12])}
 const short=J.filter(r=>!r.paused&&(+r.want||0)>(+r.count||0)).reduce((a,r)=>a+(+r.want-(+r.count||0)),0);if(c&&val(7)&&short)need.push(['w',n(val(7))+' idle while workplaces are short of '+n(short)+' hands','pop',7]);
 const G=arr(O&&O.goods);for(const g of G){const l=roLasts(g[1],g[2]);if(l&&g[1]/-g[2]<2)need.push([g[1]/-g[2]<0.5?'bad':'w',roName(g[0])+' runs out in about '+l,'',''])}
 for(const r of J)if(r.problem&&!r.paused)need.push(['w',r.name+': '+jbProb(r),'job',r.id]);
 h+='<h3>Needs you</h3>'+(need.length?'<ul class="roneeds">'+need.slice(0,7).map(([cls,t,k,v])=>'<li class="'+cls+'">'+(k?'<button type="button" data-ro="'+k+'" data-v="'+esc(v)+'">'+esc(t)+'</button>':'<span>'+esc(t)+'</span>')+'</li>').join('')+(need.length>7?'<li class="more"><span>and '+(need.length-7)+' more</span></li>':'')+'</ul>':'<p class="hint roquiet">Nothing needs you right now.</p>');
 // goods: biggest stock first, or by a column the player clicked
 const rows=G.slice();if(realmOvSort==='rate')rows.sort((a,b)=>(a[2]==null?1e9:a[2])-(b[2]==null?1e9:b[2]));else if(realmOvSort==='lasts')rows.sort((a,b)=>{const x=a[2]<0?a[1]/-a[2]:1e9,y=b[2]<0?b[1]/-b[2]:1e9;return x-y});else if(realmOvSort==='name')rows.sort((a,b)=>roName(a[0]).localeCompare(roName(b[0])));
 const th=(k,l)=>'<th data-rosort="'+k+'" tabindex="0"'+(realmOvSort===k?' aria-sort="ascending"':'')+' title="Sort by '+l.toLowerCase()+'">'+l+'</th>';
 const meas=O?(O.span>=60?'change measured over the last '+Math.round(O.span/60)+' min':'measuring the change (a minute)…'):'counting…';
 const goods='<table class="rotable"><thead><tr>'+th('name','Goods')+th('count','In store')+th('rate','Per hour')+th('lasts','Lasts')+'</tr></thead><tbody>'+(rows.length?rows.map(g=>{const r=g[2],l=roLasts(g[1],r),lh=r<0?g[1]/-r:1e9;return '<tr><td>'+esc(roName(g[0]))+'</td><td>'+n(g[1])+'</td><td class="'+(r>0?'up':r<0?'dn':'')+'">'+(r==null?'…':(r>0?'+':'')+n(r))+'</td><td class="'+(lh<0.5?'dn':lh<2?'warn':'')+'">'+(l||'—')+'</td></tr>'}).join(''):'<tr><td colspan="4" class="roempty">'+(O?'Nothing on your stores yet.':'Counting…')+'</td></tr>')+'</tbody></table><p class="rofoot">'+esc(meas)+(O&&O.more?' · '+O.more+' more kinds':'')+'</p>';
 // workplaces: the job board's rows, workers against wanted, output and what each is doing
 const work='<table class="rotable rowork"><thead><tr><th>Workplace</th><th>Workers</th><th>Per min</th><th>Doing</th></tr></thead><tbody>'+(J.length?J.map(r=>{const want=+r.want||0,cnt=+r.count||0,pct=want?Math.min(100,Math.round(cnt/want*100)):0,[st,cls]=jbLineText(r);return '<tr data-ro="job" data-v="'+esc(r.id)+'" tabindex="0" title="'+esc(r.name+'\nClick: open it on the Work page.')+'"><td>'+esc(r.name)+'</td><td><i class="romini"><i style="width:'+pct+'%"></i></i>'+cnt+'/'+want+'</td><td>'+(r.rate?'+'+n(r.rate):'—')+'</td><td class="'+(cls?'warn':'')+'" title="'+esc(st)+'">'+esc(st)+'</td></tr>'}).join(''):'<tr><td colspan="4" class="roempty">No workplaces yet: paint a zone on the Work page.</td></tr>')+'</tbody></table>';
 ov.innerHTML=h+'<div class="rocols"><section><h3>Goods</h3>'+goods+'</section><section><h3>Workplaces</h3>'+work+'</section></div>'}
document.querySelectorAll('.rsubtabs button').forEach(b=>b.addEventListener('click',()=>{realmView=b.dataset.realmview;if(model)renderRealmOverview(model)}));
{const ov=$('realmOverview');if(ov){const act=t=>{const p=t.closest('[data-pop]');if(p&&!p.disabled){send('popselect',p.dataset.pop);return}const s=t.closest('[data-rosort]');if(s){realmOvSort=s.dataset.rosort;if(model)renderRealmOverview(model);return}const r=t.closest('[data-ro]');if(!r)return;if(r.dataset.ro==='pop')send('popselect',r.dataset.v);else if(r.dataset.ro==='job'){JBG.open.add(String(r.dataset.v));send('tab','work')}};
 ov.addEventListener('click',e=>act(e.target));ov.addEventListener('keydown',e=>{if((e.key==='Enter'||e.key===' ')&&e.target.matches('[data-rosort],tr[data-ro]')){e.preventDefault();act(e.target)}})}}
