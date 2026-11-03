// ===== Village > Lineage & connections =====
let lineageKey='';
function lineageView(m){const L=m.lineage;const box=$('villageLineage');if(!L){return}
 const people=L.people||{};const houses=L.houses||{};
 if(box.contains(document.activeElement)&&document.activeElement.matches('input'))return;const key=JSON.stringify([L,arr(m.units).filter(u=>u.selected).map(u=>u.uid)]);if(key===lineageKey)return;lineageKey=key;
 const kids={};Object.values(people).forEach(p=>[p.father,p.mother].forEach(id=>{if(id){(kids[id]=kids[id]||[]).push(p.uid)}}));
 const sel=arr(m.units).find(u=>u.selected&&people[u.uid]);
 let focus=people[L.focus]?L.focus:sel?sel.uid:(Object.values(people).find(p=>p.alive&&p.royal)||Object.values(people).find(p=>p.alive)||{}).uid;
 const F=people[focus];
 const hc=id=>{const c=houses[id]&&houses[id].color;return /^#[0-9a-fA-F]{3,8}$/.test(c||'')?c:'#555'};const hn=id=>houses[id]?'House '+houses[id].name+(houses[id].foreign?' (another lord)':''):'No house';
 const SU=L.succession||{};const mark=uid=>uid===SU.ruler?'<span title="Head of the family">★ </span>':uid===SU.heir?'<span title="Heir">⚑ </span>':'';
 const card=(uid,cls,fallbackName)=>{const p=people[uid];
  if(!p)return '<button class="pcard unknown" disabled><span class="ghost">?</span><span><b>'+esc(fallbackName||'Unknown')+'</b><small>'+(fallbackName?'Not in your records':'Founder · parents unknown')+'</small></span></button>';
  const pic=p.alive&&p.portrait?'<img alt="" src="'+esc(p.portrait)+'">':'<span class="ghost">'+(p.alive?esc((p.race||'?')[0]):'†')+'</span>';
  const sub=p.alive?esc([p.race,p.gender,'age '+p.age,'Lv '+p.level].filter(Boolean).join(' · ')):'Died '+esc(p.died||'')+(p.killer?' · '+esc(p.killer):'');
  return '<button class="pcard '+(p.alive?'':'dead ')+(cls||'')+'" style="--hc:'+esc(hc(p.house))+'" data-do="lineagefocus" data-value="'+esc(uid)+'" title="'+esc(ownName(p.name)+' · '+hn(p.house)+(p.born?' · born '+p.born:''))+'">'+pic+'<span><b>'+(p.royal?'<b class="hcg hcg-crown">♛</b> ':'')+mark(uid)+esc(ownName(p.name))+'</b><small>'+sub+'</small><small>'+esc(hn(p.house))+' · gen '+esc(p.generation||1)+'</small></span></button>'};
 const row=(label,uids,empty)=>'<div class="lrow"><span>'+label+'</span><div class="lcards">'+(uids.length?uids.map(u=>card(u)).join(''):'<small class="hint">'+empty+'</small>')+'</div></div>';
 // houses column
 const counts={};Object.values(people).forEach(p=>{const c=counts[p.house]=counts[p.house]||{alive:0,dead:0,gen:0};p.alive?c.alive++:c.dead++;c.gen=Math.max(c.gen,p.generation||1)});
 let html='<div class="lin"><div class="houses"><h3>Houses</h3>'+Object.values(houses).map(h=>{const c=counts[h.id]||{alive:0,dead:0,gen:0};return '<div class="house" style="--hc:'+(/^#[0-9a-fA-F]{3,8}$/.test(h.color||'')?h.color:'#555')+'"><b>House '+esc(h.name)+'</b><small>Founded '+esc(h.founded||'')+(h.founder&&people[h.founder]?' by '+esc(ownName(people[h.founder].name)):'')+'</small><small>'+c.alive+' living · '+c.dead+' dead · '+c.gen+' generation'+(c.gen===1?'':'s')+'</small>'+(h.main?'<div class="rename"><input maxlength="32" aria-label="New house name" placeholder="Rename house" data-house="'+esc(h.id)+'"><button data-rename="'+esc(h.id)+'">Rename</button></div>':'')+'</div>'}).join('')+'</div><div class="tree">';
 if(!F){html+='<p class="hint">No villagers yet.</p></div></div>';box.innerHTML=html;return}
 const par=[F.father,F.mother].filter(Boolean);const pn=arr(F.parentNames);
 const grand=[];par.forEach(id=>{const p=people[id];if(p)[p.father,p.mother].forEach(g=>{if(g&&!grand.includes(g))grand.push(g)})});
 const siblings=[...new Set(par.flatMap(id=>kids[id]||[]))].filter(u=>u!==focus);
 const partners=arr(F.partners).filter(Boolean);const children=kids[focus]||[];const grandkids=children.flatMap(c=>kids[c]||[]);
 const desc=new Set();const walk=u=>(kids[u]||[]).forEach(c=>{if(!desc.has(c)){desc.add(c);walk(c)}});walk(focus);
 const livingDesc=[...desc].filter(u=>people[u]&&people[u].alive).length;
 html+='<p class="hint">'+(SU.ruler&&people[SU.ruler]?'★ Head of the family: <b>'+esc(ownName(people[SU.ruler].name))+'</b>':'')+(SU.heirName?' · ⚑ Heir: <b>'+esc(ownName(SU.heirName))+'</b> ('+esc(SU.heirWhy)+')':'')+'</p>';
 html+='<h3>Connections of '+esc(ownName(F.name))+'</h3><div class="conn"><div>House<b>'+esc(hn(F.house).replace('House ',''))+'</b></div><div>Generation<b>'+esc(F.generation||1)+'</b></div><div>Born<b>'+esc(F.born||'Founder')+'</b></div><div>Partners<b>'+partners.length+'</b></div><div>Children<b>'+children.length+'</b></div><div>Siblings<b>'+siblings.length+'</b></div><div>Descendants<b>'+desc.size+' ('+livingDesc+' living)</b></div>'+(F.alive?'':'<div>Died<b>'+esc(F.died||'')+'</b></div>')+'</div>';
 if(grand.length)html+=row('Grandparents',grand,'');
 html+='<div class="lrow"><span>Parents</span><div class="lcards">'+(F.father||pn[0]?card(F.father,'',pn[0]):'')+(F.mother||pn[1]?card(F.mother,'',pn[1]):'')+(!F.father&&!F.mother&&!pn[0]&&!pn[1]?card(null):'')+'</div></div>';
 html+='<div class="lrow"><span>'+(partners.length?'Partners · ':'')+esc(ownName(F.name))+(siblings.length?' · siblings':'')+'</span><div class="lcards focusline">'+partners.map(u=>card(u)).join('')+(partners.length?'<span class="sep">♥</span>':'')+card(focus,'focus')+(siblings.length?'<span class="sep">siblings</span>':'')+siblings.map(u=>card(u)).join('')+'</div></div>';
 html+=row('Children',children,'No children yet. Pair a male and female of age with Have a child (Family tab).');
 if(grandkids.length)html+=row('Grandchildren',grandkids,'');
 const members=Object.values(people).filter(p=>p.house===F.house&&p.uid!==focus).sort((a,b)=>(b.alive-a.alive)||((a.generation||1)-(b.generation||1))).map(p=>p.uid);
 if(members.length)html+=row('House members · click anyone to see their family',members,'');
 html+=(F.alive&&people[focus].ref?'<button data-do="select" data-value="'+esc(people[focus].ref)+'" style="margin-top:4px">Select '+esc(ownName(F.name))+' on the map</button>'+(focus!==SU.ruler&&focus!==SU.heir?' <button data-do="designateheir" data-value="'+esc(focus)+'" style="margin-top:4px">Name '+esc(ownName(F.name))+' as heir</button>':'')+(focus!==SU.ruler?' <button data-do="makehero" data-value="'+esc(people[focus].ref)+'" style="margin-top:4px">Make head of the family</button>':''):'')+'</div></div>';
 box.innerHTML=html}
document.addEventListener('click',e=>{const b=e.target.closest('button[data-rename]');if(!b)return;const input=b.parentElement.querySelector('input');const v=(input.value||'').trim();if(v){send('housename',b.dataset.rename+'|'+v);input.value='';lineageKey=''}else{input.focus();toast('Type the new house name first.')}});
/* Enter in the house name box renames, as the Rename button does (polish-hud 10-26) */
document.addEventListener('keydown',e=>{const i=e.key==='Enter'&&e.target&&e.target.closest&&e.target.closest('#villageLineage input[data-house]');if(!i)return;e.preventDefault();const b=i.parentElement.querySelector('button[data-rename]');if(b)b.click()});

