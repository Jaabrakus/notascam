// ===== HUD view at 30,000 units (hud-craft, 10-24): the server sends whole entries only for what the page shows (the
// selection, the units on screen, open group members and the rows in view); the lists ask for their rows ("hudview":
// their windows) and get them as refs in order (model.lists), the totals as model.unitCount / model.counts. Without
// model.lists (an older server) every list renders from model.units, as before.
var hcViewSent=null,hcViewT=0;
function hcUnitN(m){return m&&m.unitCount!=null?m.unitCount:arr(m&&m.units).length}
function hcListRows(m,k){const L=m&&m.lists&&m.lists[k];if(!L)return null;const by=new Map(arr(m.units).map(u=>[u.ref,u]));return {total:L.total|0,first:L.first|0,rows:arr(L.refs).map(r=>by.get(r)).filter(Boolean)}}
// the step from one row to the next (its height and the gap), in layout px (offsets) or, with rect, as the page draws it
function hcRowStep(list,sel,rect){const r=list?list.querySelectorAll(sel):[];if(r.length>1){const a=rect?r[0].getBoundingClientRect().top:r[0].offsetTop,b=rect?r[1].getBoundingClientRect().top:r[1].offsetTop;if(b>a)return b-a}return r.length?(rect?r[0].getBoundingClientRect().height:r[0].offsetHeight):0}
// the rows of a windowed list in view of its scroller: [first, count] (rows above the window are its top padding)
function hcWin(sc,list,sel,def,k){if(!sc||!list||!list.getClientRects().length)return null;const s=sc.getBoundingClientRect(),l=list.getBoundingClientRect(),ratio=l.height&&list.offsetHeight?l.height/list.offsetHeight:1,h=hcRowStep(list,sel,true)||def*ratio;   /* rects: zoomed px in Chrome, layout px in WebKit */if(!(h>0))return null;const a=Math.max(0,Math.floor((s.top-l.top)/h)),b=Math.max(a+1,Math.ceil((s.bottom-l.top)/h));return [Math.max(0,a-10),b-a+20]}
function hcViewState(){const o={c:[0,30],u:null,v:null,g:[]},k=hudKC()||1;
 const rs=$('roster'),rl=$('rosterList');if(rs&&rl&&!rs.classList.contains('folded')){const w=hcWin(rs,rl,'.member',34,k);if(w)o.c=w}
 const open=document.body.classList.contains('panel-open')||!overlayHost,main=document.querySelector('main');
 if(open&&currentTab==='units')o.u=hcWin(main,$('units'),'.card',60,k)||[0,30];
 if(open&&currentTab==='village'&&$('villageRoster')&&!$('villageRoster').hidden){const w=hcWin(main,$('villageRows'),'.vrow',48,k)||[0,40];o.v={f:villageFilter,q:($('villageSearch').value||'').trim(),s:$('villageSort').value,first:w[0],count:w[1]}}
 if(typeof FMG!=='undefined'&&FMG.open)o.g=[...FMG.open];return o}
// sent when it changes, never before the first model (a command while the page loads stops WebKit reading it)
function hcViewSoon(){if(hcViewSoon.q)return;hcViewSoon.q=1;requestAnimationFrame(()=>{hcViewSoon.q=0;try{hcViewSend()}catch(e){console.error(e)}})}   // the windows read in the next frame (hud-craft, 10-25)
function hcViewSend(){try{if(!model)return}catch(e){return}const st=JSON.stringify(hcViewState());if(st===hcViewSent)return;hcViewSent=st;send('hudview',st)}
function hcViewSoon(){clearTimeout(hcViewT);hcViewT=setTimeout(hcViewSend,120)}
addEventListener('scroll',e=>{const t=e.target;if(t&&t.nodeType===1&&(t.id==='roster'||t.tagName==='MAIN'))hcViewSoon()},true);
addEventListener('resize',()=>hcViewSoon());
// a windowed list's scroll bar is the whole list's: the rows above the window as padding on top, those below at the bottom
// The Company list's rows on screen (hud-craft, 10-25): with the whole company in the model (up to 1,000), only the rows
// in the list's visible window and ~12 either side are shown and kept up to date (hcRW: first, count, in shown rows);
// the others wait hidden (hc-off) and the list's padding stands in for them, so a change to every unit restyles ~40
// rows. The window is read after layout (placeRoster, each update and frame) and on scroll. Formations' grouped rows
// (fm-ing) take no room and are kept up to date as before. Above 1,000 the server's window (HudView.dm) is kept.
let hcRW=null,hcRosterH=0,hcRosterQ=0;
function hcRosterRow(b,u){b.classList.toggle('sel',!!u.selected);const img=b.querySelector('img');if(u.portrait&&img.dataset.src!==u.portrait){img.dataset.src=u.portrait;img.src=u.portrait}text(b.querySelector('.nm'),ownName(u.name));{const st=b.querySelector('.st'),h=hcStatusHTML(unitStatus(u));if(st.dataset.h!==h){st.dataset.h=h;st.innerHTML=h}}{const w=pct(u.hp,u.maxhp)+'%',sp=b.querySelector('.hpbar span'),tr=b.querySelector('.hpbar .trl');if(sp.style.width!==w)sp.style.width=w;if(tr&&tr.style.width!==w)tr.style.width=w}b.classList.toggle('fighting',!!u.combat);b.title=ownName(u.name)+' · '+u.race+' · Lv '+u.level+'\n'+unitStatus(u)+(arr(u.events).length?'\n\nRecent:\n'+arr(u.events).slice().reverse().map(e=>'· '+tidyLine(e.text)+' ('+(e.ago<60?e.ago+'s':Math.round(e.ago/60)+'m')+' ago)').join('\n'):'')}
function hcRosterSync(list,runits,CL){const R=list.children;
 if(CL){for(let i=0;i<R.length;i++){const b=R[i],u=runits[i];if(b.classList.contains('hc-off'))b.classList.remove('hc-off');if(u)hcRosterRow(b,u)}hcPad(list,CL,hcRowStep(list,'.member')||34);return}
 const W=hcRW,h=hcRosterH||34;let j=0,above=0,below=0;
 for(let i=0;i<R.length;i++){const b=R[i],u=runits[i];if(!u)continue;if(b.classList.contains('fm-ing')){hcRosterRow(b,u);continue}
  const on=!W||(j>=W[0]&&j<W[0]+W[1]);if(b.classList.contains('hc-off')===on)b.classList.toggle('hc-off',!on);
  if(on)hcRosterRow(b,u);else if(j<W[0])above++;else below++;j++}
 const pt=above?above*h+'px':'',pb=below?below*h+'px':'';if(list.style.paddingTop!==pt)list.style.paddingTop=pt;if(list.style.paddingBottom!==pb)list.style.paddingBottom=pb}
function hcRosterWin(){const rs=$('roster'),list=$('rosterList');let M=null;try{M=model}catch(e){}if(!rs||!list||!M||hcListRows(M,'company'))return;
 if(rs.classList.contains('folded')||!list.getClientRects().length)return;
 let p=null;for(const b of list.children){if(b.classList.contains('hc-off')||b.classList.contains('fm-ing'))continue;if(p){const d=b.offsetTop-p.offsetTop;if(d>0)hcRosterH=d;break}p=b}
 const s=rs.getBoundingClientRect(),l=list.getBoundingClientRect(),k=l.height&&list.offsetHeight?l.height/list.offsetHeight:1,h=(hcRosterH||34)*k;if(!(h>0))return;
 const a=Math.max(0,Math.floor((s.top-l.top)/h)),z=Math.max(a+1,Math.ceil((s.bottom-l.top)/h)),W=hcRW;
 if(W&&a-5>=W[0]&&z+5<=W[0]+W[1])return;   // still inside the shown rows, 5 to spare
 const f=Math.max(0,a-12);hcRW=[f,z+12-f];hcRosterSync(list,arr(M.units),null)}
{const rs=document.getElementById('roster');if(rs)rs.addEventListener('scroll',()=>{if(hcRosterQ)return;hcRosterQ=1;requestAnimationFrame(()=>{hcRosterQ=0;try{hcRosterWin()}catch(e){console.error(e)}})},{passive:true})}
function hcPad(list,L,h){const pt=(L?L.first*h:0)+'px',pb=(L?Math.max(0,L.total-L.first-L.rows.length)*h:0)+'px';if(list.style.paddingTop!==(L?pt:'')){list.style.paddingTop=L?pt:''}if(list.style.paddingBottom!==(L?pb:'')){list.style.paddingBottom=L?pb:''}}
