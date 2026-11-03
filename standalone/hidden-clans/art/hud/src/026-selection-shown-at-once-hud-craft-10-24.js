// ===== Selection shown at once (hud-craft, 10-24: "how can we make select plus 200 instant") =====
// Select all (its buttons, Ctrl+A) and the selections rts-feel draws ahead of the game (a box, the same kind: rfOptSelect)
// are shown at once: the page's own model with them selected goes through updateHUD (the cards, the counts, the band
// card's faces and, through rfSyncSel, the rings), without waiting for the server. Until a model says the same (the
// count, and for a box the very units) or 2.5 s pass, a send that came from before it gets the same selection put on it
// as it is merged (updateHUD), and the 3D view's sends have the rings put back after them, so nothing flickers back.
// The server's send then confirms it and fills in what only selected units carry (their packs, styles).
var hcSelPend=null,hcSelSelf=false,hcSel3dWrapped=false;
// The Units and Orders pages build a card for every unit, with each selected one's work, skills and sheet: selecting 200
// made one update take 4 s in WebKit (renderUnits 2.4 s, renderOrderUnits 1.5 s) though neither page was open. Their cards
// are now built only while the page shows, and at once when it opens (the panel, or its tab).
var hcCardsStale={units:true,orders:true};
// A selected card's heavy parts (its work rows, skills and sheet: ~20 ms a card in WebKit, so opening the Units page with
// 200 selected took 4.4 s) are built only for cards near the screen (an IntersectionObserver, 800 px either side); the
// rest wait, and are built from the current model as they come near (scrolling). Everything else on a card stays as it
// was (names, bars, status, pack).
var hcCardIO=null;
function hcCardHeavy(n,page){const ref=n.later&&n.later.ref;n.later=null;if(!ref)return;let u=null;try{u=arr(model&&model.units).find(x=>x.ref===ref)}catch(e){}if(!u||!u.selected)return;
 renderUnitWork(n.work,u);if(page==='units'){renderSkills(n.skillbox,u.skills,u);renderSheet(n.sheet,u.stats)}}
function hcCardDefer(n,u,page){
 if(!hcCardIO){if(typeof IntersectionObserver!=='function')return false;hcCardIO=new IntersectionObserver(es=>{for(const e of es){const n=e.target.__hcn;if(!n)continue;n.near=e.isIntersecting;if(n.near&&n.later)try{hcCardHeavy(n,e.target.__hcp)}catch(err){console.error(err)}}},{rootMargin:'800px 0px'})}
 if(!n.root.__hcn){n.root.__hcn=n;n.root.__hcp=page;hcCardIO.observe(n.root)}
 if(n.near){n.later=null;return false}
 n.later=u;return true}
function hcPageShown(tab){try{return (document.body.classList.contains('panel-open')||!overlayHost)&&currentTab===tab}catch(e){return true}}
function hcCards(m){
 if(hcPageShown('units')){const UL=hcListRows(m,'units');renderUnits(UL?UL.rows:arr(m.units),UL);hcCardsStale.units=false}else hcCardsStale.units=true;
 if(hcPageShown('orders')){renderOrderUnits(arr(m.units));hcCardsStale.orders=false}else hcCardsStale.orders=true}
function hcCardsNow(){try{if(!model)return}catch(e){return}if((hcCardsStale.units&&hcPageShown('units'))||(hcCardsStale.orders&&hcPageShown('orders')))try{hcCards(model)}catch(e){console.error(e)}
 if(hcCardsStale.delivery&&hcPageShown('orders'))try{renderDelivery(model)}catch(e){console.error(e)}
 if(hcCardsStale.work&&hcPageShown('work'))try{renderSettlement(model.settlement)}catch(e){console.error(e)}}
addEventListener('DOMContentLoaded',()=>{try{const mo=new MutationObserver(()=>hcCardsNow());mo.observe(document.body,{attributes:true,attributeFilter:['class']});
 for(const id of ['page-units','page-orders','page-work']){const pg=document.getElementById(id);if(pg)mo.observe(pg,{attributes:true,attributeFilter:['hidden']})}}catch(e){console.error(e)}});
function hcSelWant(P,u){return P.all?1:P.set.has(u.ref)?1:0}
// m's units with the pending selection put on, and its count
function hcSelPut(m,P){m.units=arr(m.units).map(u=>(u.selected?1:0)===hcSelWant(P,u)?u:Object.assign({},u,{selected:hcSelWant(P,u)}));m.selection=P.all?Math.max(m.selection|0,P.n):P.n}
// called as updateHUD merges a model: does it say the same yet?
function hcSelHold(m){const P=hcSelPend;if(!P)return;
 const agrees=P.all?(m.selection|0)>=hcUnitN(m):(m.selection|0)===P.n&&arr(m.units).every(u=>!!u.selected===P.set.has(u.ref));
 if(agrees||performance.now()-P.at>2500){hcSelPend=null;return}
 hcSelPut(m,P)}
function hcSelShow(P){
 try{if(!model)return}catch(e){return}
 hcSelPend=P;
 if(!hcSel3dWrapped&&typeof window.update3D==='function'){hcSel3dWrapped=true;const u3=window.update3D;window.update3D=function(raw){const r=u3(raw);try{if(hcSelPend&&typeof rfSyncSel==='function')rfSyncSel()}catch(e){}return r}}
 const m=Object.assign({},model);hcSelPut(m,P);
 hcSelSelf=true;try{window.updateHUD(m)}catch(e){console.error(e)}finally{hcSelSelf=false}}
function hcSelectAllNow(){try{if(!model)return}catch(e){return}hcSelShow({all:true,n:hcUnitN(model),at:performance.now()})}
addEventListener('click',e=>{const b=e.target&&e.target.closest&&e.target.closest('[data-do="action"][data-value="all"]');if(b&&!b.disabled)hcSelectAllNow()},true);
addEventListener('keydown',e=>{if(e.ctrlKey&&!e.metaKey&&!e.altKey&&e.key&&e.key.toLowerCase()==='a'&&!(e.target&&e.target.closest&&e.target.closest('input,select,textarea')))hcSelectAllNow()},true);
// rts-feel's selection ahead of the game (rings) also shows in the cards: only / add / flip, as rfApplyOpt does
function hcSelWrapOpt(){if(typeof rfOptSelect!=='function'||rfOptSelect.hcWrapped)return;const ro=rfOptSelect;rfOptSelect=function(refs,mode){ro(refs,mode);try{if(!model)return;const R=new Set(refs),set=new Set(arr(model.units).filter(u=>u.selected).map(u=>u.ref));
  if(mode==='only'){set.clear();for(const r of R)set.add(r)}else if(mode==='add'){for(const r of R)set.add(r)}else for(const r of R){if(set.has(r))set.delete(r);else set.add(r)}
  const own=new Set(arr(model.units).map(u=>u.ref));for(const r of [...set])if(!own.has(r))set.delete(r);
  hcSelShow({all:false,set,n:set.size,at:performance.now()})}catch(e){console.error(e)}};rfOptSelect.hcWrapped=true}
addEventListener('DOMContentLoaded',hcSelWrapOpt);setTimeout(hcSelWrapOpt,0);
