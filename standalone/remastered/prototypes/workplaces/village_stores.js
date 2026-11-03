/* PROTOTYPE (VillageStores.dm, Workplaces.dm): the Village stores bar and workplace painting and cards, put into the test arena's copy of remastered.html
   by watch_prototype.py. A strip under the top bar: each resource's total in your stores, what your people
   carry beside it, and a click that lists where it all is (a click on a place moves the camera there). */
(function(){
 const css=document.createElement('style');
 css.textContent='#vsbar{position:fixed;top:62px;left:320px;z-index:200;display:flex;gap:0;align-items:center;padding:2px 4px;background:linear-gradient(180deg,#221c12,#16120b);border:1px solid #6b5630;border-radius:3px;box-shadow:0 0 0 1px #000,0 4px 12px rgba(0,0,0,.5);font:12px Georgia,serif;color:#e8dcb8}'
 +'#vsbar .vsh{padding:0 8px 0 4px;color:#c9b27a;font-size:11px;letter-spacing:.04em;text-transform:uppercase}'
 +'#vsbar button{all:unset;cursor:pointer;display:inline-flex;align-items:baseline;gap:4px;padding:2px 8px;border-left:1px solid #3a3020}'
 +'#vsbar button:hover,#vsbar button.on{background:#3a2e18}'
 +'#vsbar b{color:#f2d27a;font-weight:600;font-size:13px;font-variant-numeric:tabular-nums}'
 +'#vsbar small{font-size:11px;color:#cdbf98}#vsbar em{font-style:normal;font-size:10px;color:#9fb08a}'
 +'#vspop{position:fixed;z-index:201;min-width:220px;max-width:320px;padding:8px 10px;background:#17130c;border:1px solid #6b5630;border-radius:3px;box-shadow:0 0 0 1px #000,0 8px 20px rgba(0,0,0,.6);font:12px Georgia,serif;color:#e8dcb8}'
 +'#vspop h4{margin:0 0 6px;font-size:13px;color:#f2d27a}#vspop .row{all:unset;display:flex;justify-content:space-between;gap:12px;width:100%;padding:3px 4px;cursor:pointer;box-sizing:border-box}'
 +'#vspop .row:hover{background:#2c2414}#vspop .row.carry{color:#b9c9a4}#vspop .row b{color:#f2d27a}#vspop p{margin:6px 0 0;font-size:10px;color:#a99a78}';
 document.head.appendChild(css);
 const bar=document.createElement('div');bar.id='vsbar';bar.setAttribute('role','group');bar.setAttribute('aria-label','Village stores');
 document.body.appendChild(bar);
 let open=null,last='';
 /* the page keeps its model in a top-level let (not on window) */
 const hudModel=()=>{try{return model}catch(e){return null}};
 const esc=s=>String(s==null?'':s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
 function popup(k,btn){
  const old=document.getElementById('vspop');if(old)old.remove();
  bar.querySelectorAll('button').forEach(b=>b.classList.toggle('on',b===btn&&open!==k));
  if(open===k){open=null;return}
  open=k;const S=hudModel()&&hudModel().stores,K=S&&S.kinds&&S.kinds[k];if(!K)return;
  const p=document.createElement('div');p.id='vspop';
  const rows=(K.where||[]).map(w=>'<button class="row'+(w[5]?' carry':'')+'" data-x="'+(w[2]==null?'':w[2])+'" data-y="'+(w[3]==null?'':w[3])+'"><span>'+esc(w[0])+'</span><b>'+w[1]+'</b></button>').join('');
  p.innerHTML='<h4>'+esc(K.label)+': '+K.stored+' in store'+(K.carried?' · '+K.carried+' carried':'')+'</h4>'+(rows||'<p>None anywhere.</p>')+'<p>Anyone in your house can use what is in store. What people carry is on its way in.</p>';
  const r=btn.getBoundingClientRect();p.style.left=Math.round(r.left)+'px';p.style.top=Math.round(r.bottom+4)+'px';
  p.addEventListener('click',e=>{const b=e.target.closest('.row');if(b&&b.dataset.x!=='')send('camera',b.dataset.x+','+b.dataset.y)});
  document.body.appendChild(p);
 }
 function render(){
  const S=hudModel()&&hudModel().stores;if(!S||!S.kinds)return;
  const key=JSON.stringify([S.kinds,arr2(hudModel().workplaces).length]);if(key===last)return;last=key;
  const keys=Object.keys(S.order||S.kinds).filter(k=>S.kinds[k]&&(S.kinds[k].stored||S.kinds[k].carried||['wood','stone','food'].includes(k)));
  const WPS=arr2(hudModel().workplaces);
  bar.innerHTML='<span class="vsh">Village stores</span>'+keys.map(k=>{const K=S.kinds[k];return '<button data-k="'+k+'" title="'+esc(K.label)+': '+K.stored+' in your stores'+(K.carried?', '+K.carried+' carried by your people':'')+'. Click: where it is."><b>'+K.stored+'</b><small>'+esc(K.label.toLowerCase())+'</small>'+(K.carried?'<em>+'+K.carried+'</em>':'')+'</button>'}).join('')
   +'<span class="vsh vsgap">Banners</span><button data-wp="choose" title="Place a banner: declare a lodge or a store where you click."><small>+ Banner</small></button><button data-wp="list" title="Your banners: lodges and stores"><b>'+WPS.length+'</b><small>placed</small></button>';
  bar.querySelectorAll('button[data-k]').forEach(b=>{if(b.dataset.k===open)b.classList.add('on');b.addEventListener('click',()=>{const k=b.dataset.k;if(open===k){popup(k,b);return}open=null;popup(k,b)})});
  bar.querySelectorAll('button[data-wp]').forEach(b=>b.addEventListener('click',()=>{const v=b.dataset.wp;if(v==='list'){wpList(b);return}if(v==='choose'){wpChoose(b);return}send('wppaint',v.split('|')[1])}));
  if(open){const b=bar.querySelector('button[data-k="'+open+'"]');const k=open;open=null;if(b)popup(k,b)}
 }
 const arr2=a=>Array.isArray(a)?a:[];
 /* the workplace card: workers and "stop at", what it is doing, look and remove */
 const card=document.createElement('div');card.id='wpcard';card.hidden=true;document.body.appendChild(card);
 let cardId=null,cardKey='',seenOpen=null;

 function wpCard(){
  const W=arr2(hudModel()&&hudModel().workplaces).find(w=>w.id===cardId);
  if(!W){card.hidden=true;cardId=null;return}
  const key=JSON.stringify(W);if(key===cardKey&&!card.hidden)return;cardKey=key;card.hidden=false;
  const y=W.yard,U=W.up||{},st=(k,label,what)=>{const u=U[k]||[0,0];return '<div class="wprow"><span>'+label+(u[0]?' · <b>'+u[0]+' built</b>':'')+(u[1]?' · '+u[1]+' planned':'')+'<br><small>'+what+'</small></span><button data-c="upgrade|'+k+'"'+((k!=='bench'&&(u[0]||u[1]))?' disabled':'')+'>Add</button></div>'};
  if(!W.lodge){card.innerHTML='<h4>'+esc(W.name)+'</h4><p class="sub">'+esc(W.what)+' · keeps '+esc(W.good)+(W.banner?'':' · banner not up yet')+'</p><p class="st">'+esc(W.status||'')+'</p><div class="wpbtns"><button data-c="look">Look</button><button data-c="remove" class="danger">Remove</button><button data-c="close">Close</button></div>';
   card.querySelectorAll('button[data-c]').forEach(b=>b.addEventListener('click',()=>{const c=b.dataset.c;if(c==='close'){card.hidden=true;cardId=null;return}send('wp',cardId+'|'+c)}));return}
  card.innerHTML='<h4>'+esc(W.name)+'</h4><p class="sub">Brings in '+esc(W.good)+' · its banner is its store'+(W.banner?'':' · banner not up yet')+'</p>'
   +'<div class="wprow"><span>Workers</span><b>'+esc(W.workers)+'</b></div>'
   +'<div class="wprow"><span>Stop at</span><span class="ctl"><button data-c="stop|-5">−5</button><b>'+W.stop+'</b><button data-c="stop|5">+5</button></span></div>'
   +'<div class="wprow"><span>In the stores</span><b>'+W.stock+' '+esc(W.good)+'</b></div>'
   +'<div class="wprow"><span>Brought in</span><b>'+W.total+'</b></div>'
   +(W.loose?'<div class="wprow"><span>Left lying in its zones</span><b>'+W.loose+'</b></div>':'')
   +'<h5>Zones to tend</h5><div class="wprow"><span>'+(arr2(W.zones).length?arr2(W.zones).map(z=>(z[2]-z[0]+1)+'×'+(z[3]-z[1]+1)).join(', '):'None yet')+'</span><span class="ctl"><button data-c="zone">Add a zone</button>'+(arr2(W.zones).length?'<button data-c="zonedrop">−</button>':'')+'</span></div>'
   +'<h5>Upgrades <small>(a builder puts them up round the banner, 1 wood each)</small></h5>'
   +st('bench','Bench','one worker each')+st('rack','Tool rack','its workers work a quarter faster')+st('cartstop','Cart stop','with track, a cart takes its store to the stockpile')
   +'<p class="st">'+esc(W.status||'')+(arr2(W.who).length?'<br><small>'+esc(W.who.join(', '))+'</small>':'')+'</p>'
   +'<div class="wpbtns"><button data-c="look">Look</button><button data-c="remove" class="danger">Remove</button><button data-c="close">Close</button></div>';
  card.querySelectorAll('button[data-c]').forEach(b=>b.addEventListener('click',()=>{if(b.disabled)return;const c=b.dataset.c;if(c==='close'){card.hidden=true;cardId=null;return}send('wp',cardId+'|'+c)}));
 }
 /* + Banner: what it declares */
 function wpChoose(btn){
  const old=document.getElementById('vspop');if(old){old.remove();if(open==='wpchoose'){open=null;return}}
  open='wpchoose';const p=document.createElement('div');p.id='vspop';
  const K=[['woodlot','Woodcutter\'s lodge','a workplace for the trees round it; its banner is its store'],['quarry','Quarry lodge','a workplace for the rock round it; its banner is its store'],['woodstore','Wood store','a place to keep wood'],['stonestore','Stone store','a place to keep stone']];
  p.innerHTML='<h4>Place a banner</h4>'+K.map(k=>'<button class="row" data-kind="'+k[0]+'"><span>'+esc(k[1])+'<br><small style="font-size:10px;color:#a99a78">'+esc(k[2])+'</small></span><b>›</b></button>').join('')+'<p>Then click where it goes. A builder puts it up (1 wood).</p>';
  const r=btn.getBoundingClientRect();p.style.left=Math.round(r.left)+'px';p.style.top=Math.round(r.bottom+4)+'px';
  p.addEventListener('click',e=>{const b=e.target.closest('.row');if(b){send('wppaint',b.dataset.kind);p.remove();open=null}});
  document.body.appendChild(p);
 }
 function wpList(btn){
  const old=document.getElementById('vspop');if(old){old.remove();if(open==='wplist'){open=null;return}}
  open='wplist';const p=document.createElement('div');p.id='vspop';const WPS=arr2(hudModel().workplaces);
  p.innerHTML='<h4>Banners</h4>'+(WPS.map(w=>'<button class="row" data-id="'+w.id+'"><span>'+esc(w.name)+' · '+esc(w.workers)+' working</span><b>'+w.stock+'/'+w.stop+'</b></button>').join('')||'<p>None yet. Use + Banner and click where it goes.</p>');
  const r=btn.getBoundingClientRect();p.style.left=Math.round(r.left)+'px';p.style.top=Math.round(r.bottom+4)+'px';
  p.addEventListener('click',e=>{const b=e.target.closest('.row');if(b){cardId=b.dataset.id;cardKey='';wpCard();p.remove();open=null}});
  document.body.appendChild(p);
 }
 const css2=document.createElement('style');
 css2.textContent='#vsbar .vsgap{padding-left:12px;border-left:1px solid #6b5630}'
  +'#wpcard{position:fixed;top:96px;left:320px;z-index:202;width:260px;padding:10px 12px;background:#17130c;border:1px solid #6b5630;border-radius:3px;box-shadow:0 0 0 1px #000,0 8px 20px rgba(0,0,0,.6);font:12px Georgia,serif;color:#e8dcb8}'
  +'#wpcard h4{margin:0;font-size:14px;color:#f2d27a}#wpcard .sub{margin:2px 0 8px;font-size:11px;color:#a99a78}'
  +'#wpcard .wprow{display:flex;justify-content:space-between;align-items:center;padding:3px 0;border-top:1px solid #2e2616}#wpcard .wprow b{color:#f2d27a}'
  +'#wpcard .ctl{display:inline-flex;align-items:center;gap:6px}#wpcard button{all:unset;cursor:pointer;padding:2px 8px;border:1px solid #6b5630;border-radius:2px;background:#2a2214;color:#e8dcb8;font-size:12px}'
  +'#wpcard button:hover{background:#3a2e18}#wpcard .danger{border-color:#8a3a2a}#wpcard .st{margin:8px 0;font-size:11px;color:#cdbf98}#wpcard .st small{color:#9fb08a;font-size:10px}'
  +'#wpcard .wpbtns{display:flex;gap:6px;justify-content:flex-end}#wpcard h5{margin:8px 0 2px;font-size:12px;color:#c9b27a}#wpcard h5 small{color:#a99a78;font-size:10px}#wpcard small{font-size:10px;color:#a99a78}#wpcard button[disabled]{opacity:.45;cursor:default}#wpcard{width:300px}';
 document.head.appendChild(css2);
 /* painting a workplace uses the game's own drag painting: green squares, and its own banner */
 const isWp=()=>typeof V3!=='undefined'&&V3.build&&String(V3.build.mode||'').startsWith('Piece:wp_');
 if(typeof v3ghostOk==='function'){const g0=v3ghostOk;window.v3ghostOk=function(t,kind){return isWp()?'ok':g0(t,kind)}}
 function banner(){if(!isWp())return;const bb=document.getElementById('build3d');if(bb){bb.hidden=false;const md=String(V3.build.mode),nm={woodlot:'woodcutter\'s lodge',quarry:'quarry lodge',woodstore:'wood store',stonestore:'stone store'}[md.slice(9)]||'banner';bb.textContent=md.includes('zone_')?'Drag a zone to tend, within 15 tiles of the banner (up to 13 by 13) · Esc to stop':'Click where the '+nm+'\'s banner goes · Esc to stop'}}
 const u0=window.updateHUD;
 if(typeof u0==='function')window.updateHUD=function(raw){u0(raw);try{render();const m=hudModel();if(m&&m.wpOpen&&m.wpOpen!==seenOpen){seenOpen=m.wpOpen;cardId=String(m.wpOpen).split(':')[0];cardKey=''}if(cardId)wpCard();banner()}catch(e){console.error(e)}};
 const d0=window.update3D;
 if(typeof d0==='function')window.update3D=function(raw){d0(raw);try{banner()}catch(e){console.error(e)}};
})();
