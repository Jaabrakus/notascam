// ===== Village > Log =====
/* a fight entry: the log's 'fight' kind, or a won fight (CombatLog.dm logs "<name>: Won against <foe>" as 'good'); other
   good news (milestones, tamed, joined, bought, treated) is 'good' too and is not a fight (polish-hud 10-26) */
function vlogIsFight(e){return !!e&&(e.kind==='fight'||(e.kind==='good'&&/: Won against /.test(String(e.text||''))))}
const VLOG_KINDS=[['all','Everything'],['msg','Messages'],['fight','Fights'],['morale','Morale'],['problem','Problems'],['work','Work'],['skill','Skills'],['birth','Family'],['death','Deaths']];let vlogFilter='all',vlogKey='';
function villageLogView(m){const L=arr(m.villageLog);const fb=$('vlogFilters');if(!fb.childElementCount)VLOG_KINDS.forEach(([k,l])=>{const b=document.createElement('button');b.dataset.k=k;b.innerHTML=esc(l)+'<b></b>';b.addEventListener('click',()=>{vlogFilter=k;vlogKey='';villageLogView(model)});fb.append(b)});
 fb.querySelectorAll('button').forEach(b=>{const k=b.dataset.k;text(b.querySelector('b'),k==='all'?L.length:k==='msg'?logHist.length:L.filter(e=>k==='fight'?vlogIsFight(e):e.kind===k).length+(k==='fight'?logHist.filter(e=>e.k==='fight').length:0));b.setAttribute('aria-pressed',String(k===vlogFilter))});
 if(vlogFilter==='msg'){hcMsgView();return}  // hud-craft: the Messages filter (hcMsgView, by the log history)
 const shown=L.filter(e=>vlogFilter==='all'||(vlogFilter==='fight'?vlogIsFight(e):e.kind===vlogFilter));
 const fl=vlogFilter==='fight'?logHist.filter(e=>e.k==='fight'):[];  // hud-craft: Fights also lists this session's fight lines (the old Log's Fights)
 const key=JSON.stringify([vlogFilter,shown.map(e=>e.id),fl.length,fl.length?fl[fl.length-1].t:'',Math.floor(Date.now()/10000)]);if(key===vlogKey)return;vlogKey=key;
 const ago=s=>(s<60?Math.max(0,Math.round(s))+'s':s<3600?Math.round(s/60)+'m':Math.round(s/3600)+'h')+' ago',now=Date.now();
 const rows=shown.map(e=>({at:now-(Number(e.ago)||0)*1000,h:'<button class="ventry k-'+esc(e.kind)+'"'+(e.z?' data-do="gotoplace" data-value="'+e.x+'|'+e.y+'|'+e.z+'"':' disabled')+'><span>'+esc(tidyLine(e.text))+'</span><small>'+ago(e.ago)+(e.z?' · '+e.x+', '+e.y+' · L'+e.z:'')+'</small></button>'}))
  .concat(fl.map(e=>({at:e.at,h:'<button class="ventry k-fight fl" disabled><span>'+esc(tidyLine(e.t))+'</span><small>'+ago((now-e.at)/1000)+' · fight line</small></button>'}))).sort((a,b)=>b.at-a.at);
 const box=$('vlogList');box.dataset.view='';text($('vlogHint'),vlogFilter==='fight'?'Fights in and around the village, and every fight line of this session, newest first. Click a village entry to go there.':vlogFilter==='all'?'Everything that happened in the village, newest first. Click an entry to go there.':'Showing '+((VLOG_KINDS.find(x=>x[0]===vlogFilter)||[0,'these'])[1])+' only, newest first. Click an entry to go there.');box.innerHTML=rows.length?rows.map(r=>r.h).join(''):'<p class="hint">'+(vlogFilter==='fight'?'No fighting yet.':'Nothing yet.')+'</p>'}
