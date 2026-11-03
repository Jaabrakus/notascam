// ===== Village > Bulletin board =====
let boardKey='',boardRecipesKey='',boardStationsKey='';
function boardView(m){const B=m.board;if(!B)return;
 // recipes for craft orders (once)
 const rk=JSON.stringify(B.recipes||[]);if(rk!==boardRecipesKey){boardRecipesKey=rk;const sel=$('bpKind');sel.querySelectorAll('option[data-craft]').forEach(o=>o.remove());arr(B.recipes).forEach(r=>{const o=document.createElement('option');o.value='craft:'+r.id;o.dataset.craft='1';o.textContent='Craft: '+r.label+(r.uses?' — '+r.uses:'');sel.append(o)})}
 const sk=JSON.stringify(B.stations||[]);if(sk!==boardStationsKey){boardStationsKey=sk;const sel=$('bpKind');sel.querySelectorAll('optgroup[data-station]').forEach(o=>o.remove());arr(B.stations).forEach(st=>{const g=document.createElement('optgroup');g.label=st.label;g.dataset.station='1';arr(st.recipes).forEach(r=>{const o=document.createElement('option');o.value='station:'+r.id;o.textContent=r.label+(r.uses?' — uses '+r.uses:'')+(r.skill?' · '+r.skill:'');g.append(o)});sel.append(g)})}
 const key=JSON.stringify(B);if(key===boardKey)return;boardKey=key;
 const st={};arr(B.standing).forEach(s=>st[s.kind]=s);
 $('boardStats').innerHTML='<span>Board workers <b>'+esc(B.workers)+'</b>'+(B.workers?' · '+esc(B.waiting)+' waiting':'')+'</span>'+['wood','stone','food'].map(k=>'<span>'+k[0].toUpperCase()+k.slice(1)+' in stockpile <b>'+esc(st[k]?st[k].count:0)+'</b></span>').join('')+(B.stockpile?'':'<span class="bwarn">No stockpile yet: place one in the Work tab</span>')+(B.workers?'':'<span class="bwarn">Set some villagers to “Board worker” in the Roster</span>');
 // standing rows (keep typed values while focused)
 const sbox=$('boardStanding');if(!sbox.childElementCount)['wood','stone','food'].forEach(k=>{const r=document.createElement('div');r.className='srow';r.dataset.kind=k;r.innerHTML='<b>'+k[0].toUpperCase()+k.slice(1)+'</b><input type="number" min="0" max="500" aria-label="Keep at least this much '+k+'"><small></small><select aria-label="Priority for '+k+'"><option value="1">High</option><option value="2">Normal</option><option value="3">Low</option></select><input type="checkbox" aria-label="Standing order on">';sbox.append(r);
  const save=()=>{const keep=r.children[1].value||'0';send('standing',k+'|'+keep+'|'+r.children[3].value+'|'+(r.children[4].checked?'1':'0'))};r.children[4].addEventListener('change',save);r.children[1].addEventListener('change',save);r.children[3].addEventListener('change',save)});
 sbox.querySelectorAll('.srow').forEach(r=>{const s=st[r.dataset.kind]||{};const i=r.children[1];if(document.activeElement!==i)i.value=s.keep||'';text(r.children[2],'now '+(s.count||0));if(document.activeElement!==r.children[3])r.children[3].value=String(s.priority||2);r.children[4].checked=!!s.enabled});
 const head=(o,done)=>'<div class="ohead"><span><b>'+esc(o.label)+'</b>'+(o.standing?'<span class="tag">'+(String(o.standing).startsWith('build-')?'For building':'Standing · keep '+esc(st[o.standing]?st[o.standing].keep:''))+'</span>':'')+(o.area?'<span class="tag">At '+esc(o.area[0]+', '+o.area[1])+'</span>':'')+'</span>'+(done?'':'<span class="oact"><select data-boardprio="'+esc(o.id)+'" aria-label="Priority for '+esc(o.label)+'">'+[['1','High'],['2','Normal'],['3','Low']].map(([v,l])=>'<option value="'+v+'"'+(String(o.priority)===v?' selected':'')+'>'+l+'</option>').join('')+'</select><button data-do="boardcancel" data-value="'+esc(o.id)+'">Cancel</button></span>')+'</div>';
 const body=o=>{const pr=Math.max(0,Math.min(100,(o.progress||0)/(o.amount||1)*100));return '<div class="obar"><span style="width:'+pr+'%"></span></div><div class="omsg">'+esc(o.progress||0)+' / '+esc(o.amount)+(arr(o.claimers).length?' · Taken by <em>'+esc(arr(o.claimers).join(', '))+'</em>':'')+'</div><div class="omsg">'+esc(o.status||'')+'</div>'};
 // One node per order: the header (with its select and Cancel) only changes with the order itself;
 // progress and workers update in place, so clicks and open menus are never interrupted.
 const sync=(box,list,done)=>{const ids=list.map(o=>String(o.id));[...box.children].forEach(c=>{if(!ids.includes(c.dataset.id))c.remove()});
  list.forEach((o,i)=>{let c=[...box.children].find(x=>x.dataset.id===String(o.id));if(!c){c=document.createElement('div');c.dataset.id=String(o.id);c.innerHTML='<div class="oh"></div><div class="ob"></div>'}
   if(box.children[i]!==c)box.insertBefore(c,box.children[i]||null);c.className='ocard p'+o.priority;
   const h=head(o,done),b=body(o);if(c.dataset.h!==h&&!c.firstChild.contains(document.activeElement)){c.dataset.h=h;c.firstChild.innerHTML=h}if(c.dataset.b!==b){c.dataset.b=b;c.lastChild.innerHTML=b}})};
 const open=arr(B.orders).filter(o=>!o.done).sort((a,b)=>a.priority-b.priority);const done=arr(B.orders).filter(o=>o.done).reverse();
 sync($('boardOrders'),open,false);$('boardEmpty').hidden=open.length>0;
 sync($('boardDone'),done,true);$('boardDoneBox').hidden=!done.length}
$('bpPost').addEventListener('click',()=>{let kind=$('bpKind').value,recipe='';if(kind.startsWith('craft:')){recipe=kind.slice(6);kind='craft'}else if(kind.startsWith('station:')){recipe=kind.slice(8);kind='station'}
 send('boardpost',[kind,$('bpAmount').value||'1',$('bpPriority').value,$('bpWorkers').value,$('bpWhere').value,recipe].join('|'));boardKey=''});
document.addEventListener('change',e=>{const s=e.target.closest('select[data-boardprio]');if(s)send('boardpriority',s.dataset.boardprio+'|'+s.value)});

