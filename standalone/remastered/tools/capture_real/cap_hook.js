// TEST HOOK (capture-rope real check, temporary copy only): on each "CKPROBE|serial|..." notice, report the right-click
// card's buttons, the unit card's Interact tab and captive buttons, the captive section's text and the boot cover.
const cpOrig=window.updateHUD;window.updateHUD=function(raw){cpOrig(raw);setTimeout(cpProbe,160)};
function cpProbe(){try{const n=String(model&&model.notice||'');if(!n.startsWith('CKPROBE|')||n===window.cpLast)return;window.cpLast=n;
 const shown=e=>e&&e.getClientRects().length&&getComputedStyle(e).display!=='none';
 const pos=e=>{if(!shown(e))return null;const b=e.getBoundingClientRect();return [Math.round(b.x+b.width/2),Math.round(b.y+b.height/2)]};
 const m3=$('menu3d'),menu={};if(m3)m3.querySelectorAll('button').forEach(b=>{const t=b.textContent.replace(/^\S\s*/,'').trim();if(!menu[t])menu[t]=pos(b)});
 const cap={},capOff=[];document.querySelectorAll('#heroframe .hfcap button[data-do=captive]').forEach(b=>{cap[b.dataset.value.split('|')[1]]=pos(b);if(b.disabled)capOff.push(b.dataset.value.split('|')[1])});
 const sec=document.querySelector('#heroframe .hfpane[data-pane=interact] .hfcap');
 send('cpprobe',JSON.stringify({serial:n.split('|')[1],w:innerWidth*ckZ(),h:innerHeight*ckZ(),menu:shown(m3),menuBtns:menu,tab:pos(document.querySelector('#heroframe [data-hftab=interact]')),
  heroTab:($('heroframe')||{}).dataset?.tab||null,cap,capOff,notice:String(model&&model.notice||'').slice(0,120),text:sec?sec.innerText.replace(/\s+/g,' ').trim():'',
  boot:!!(document.getElementById('bootcover')&&!document.getElementById('bootcover').classList.contains('off')),
  save:pos($('btnSave')),usecard:shown($('usecard')),
  rope:(()=>{const uc=$('usecard');const b=uc&&[...uc.querySelectorAll('button[data-uc]')].find(x=>/Leather Rope/.test(x.textContent));if(!b)return null;b.scrollIntoView({block:'center'});return pos(b)})(),
  ucOpts:(()=>{const uc=$('usecard');return uc?[...uc.querySelectorAll('button[data-uc]')].map(x=>x.textContent.trim()).filter(x=>/Rope/.test(x)):[]})(),
  selected:arr(model&&model.units).filter(u=>u.selected).map(u=>u.ref),
  things:(()=>{const o={};if(!V3.on||!V3.vp)return o;const c=$('world3d'),r=c.getBoundingClientRect();for(const x of arr(V3.things)){const k=x.kind==='mine'?x.ref:x.id;if(k&&x.dx!=null&&x.kind!=='mine'||x.kind==='mine'&&k&&x.dx!=null){const p=v3project([x.dx,v3groundAt(x.dx,x.dy)+0.3,-x.dy]);if(p)o[k]=[Math.round(r.left+p[0]),Math.round(r.top+p[1]),x.x,x.y,x.kind,x.m3||'',x.caged?1:0]}}return o})(),captives:arr(model&&model.units).filter(u=>u.captive).map(u=>[u.ref,u.captive.state])}))}catch(e){send('cpprobe',JSON.stringify({error:String(e)}))}}
