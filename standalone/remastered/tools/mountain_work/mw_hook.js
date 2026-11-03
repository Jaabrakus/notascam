// TEST HOOK (mountain work, temporary game copy only): on a "MWPROBE|serial|name:x,y,h;..." notice, report where those
// world points are on screen (h -1: the ground there, -2: the rock's top), your units, the Gather switch and its button,
// the right-click menu's buttons, the pointer's verdict and the last click's instant answer.
(function(){const orig=window.updateHUD;window.updateHUD=function(raw){orig(raw);setTimeout(mwProbe,120)}})();
function mwZ(){const w=document.documentElement.getBoundingClientRect().width;return w?w/innerWidth:1}
function mwFree(x,y){const e=document.elementFromPoint(x,y);return !!(e&&(e===$('world3d')||e.closest&&e.closest('#world3d')))}
function mwRect(e){const b=e.getBoundingClientRect();return b.width>2&&b.height>2?[Math.round(b.x+b.width/2),Math.round(b.y+b.height/2)]:null}
function mwProbe(){try{const n=String(model&&model.notice||'');if(!n.startsWith('MWPROBE|')||n===window.mwLast)return;window.mwLast=n;
 if(!window.mwCam&&V3.on){window.mwCam=1;if(typeof v3iso==='function')v3iso(false);V3.dist=15;V3.pitch=0.65;V3.yaw=0;V3.turnTo=null}
 const parts=n.split('|'),c=$('world3d'),r=c.getBoundingClientRect(),gb=$('btnGather'),m3=$('menu3d');
 const out={serial:parts[1],w:innerWidth*mwZ(),h:innerHeight*mwZ(),on:!!V3.on,z:V3.z,boot:!!($('bootcover')&&!$('bootcover').hidden),gather:!!(model&&model.gather),
  btn:gb?{at:mwRect(gb),pressed:gb.getAttribute('aria-pressed'),text:(gb.querySelector('span')||gb).textContent}:null,
  menu:m3&&!m3.hidden?[...m3.querySelectorAll('button')].map(b=>[b.textContent.trim().slice(0,60),mwRect(b)]).filter(x=>x[1]):null,
  hover:model&&model.hover||null,last:typeof RF!=='undefined'&&RF.last?{k:RF.last.k,x:RF.last.x,y:RF.last.y,drawn:!!RF.last.drawn}:null,pts:{},units:{},kinds:{},ghosts:(V3.ghosts||[]).filter(g=>performance.now()-g.t0<4000).length,mine:arr(V3.things).filter(t=>t.kind==='mine').length,plan:window.PM?{on:PM.on,level:PM.level,marks:PM.marks.size,btn:$('btnPlan')?mwRect($('btnPlan')):null,queue:$('pmQueue')?mwRect($('pmQueue')):null,build:document.querySelector('#pmBar [data-pmtool="build"]')?mwRect(document.querySelector('#pmBar [data-pmtool="build"]')):null,dig:document.querySelector('#pmBar [data-pmtool="dig"]')?mwRect(document.querySelector('#pmBar [data-pmtool="dig"]')):null,up:$('pmUp')?mwRect($('pmUp')):null,done:$('pmDone')?mwRect($('pmDone')):null,tool:PM.tool,rows:arr(model&&model.plans).map(p=>[p.name,p.total,p.left,p.status])}:null,cut:[+(V3.mcR||0).toFixed(2),+(V3.mcTop||0).toFixed(2)],vz:V3.z,skyh:V3.SKYH!=null?V3.SKYH:null,layers:$('layers')?[...$('layers').children].map(b=>[b.textContent,mwRect(b)]):[],upperTiles:V3.upperTiles&&V3.upperTiles.size!=null?V3.upperTiles.size:null,
  tris:{upper:Math.round((V3.upper||[]).reduce((n,m)=>n+(m.count||0),0)/3),ground:Math.round((V3.tmesh||[]).reduce((n,m)=>n+(m.count||0),0)/3),below:Math.round((V3.below||[]).reduce((n,m)=>n+(m.count||0),0)/3)},belowZk:V3.belowL&&V3.belowL.zk||null,lvLast:V3.lvLast||null,ys:{}};
 for(const t of arr(V3.things))if(t.kind==='mine'&&t.ref){const d=V3.disp&&V3.disp.get(t.key);out.ys[t.ref]=[t.ly!=null?+(+t.ly).toFixed(2):null,d&&d.base!=null?+(+d.base).toFixed(2):null,t.feet!=null?t.feet:null]}
 for(const s of (parts[2]||'').split(';').filter(Boolean)){const [k,v]=s.split(':'),[x,y,h]=v.split(',').map(Number),tx=Math.round(x),ty=Math.round(y);
  const Y=h===-1?v3groundAt(tx,ty)+0.05:h===-2?v3peakTop(tx,ty)+0.03:h;const p=v3project([x,Y,-y]);if(p){const X=Math.round(r.left+p[0]),Yp=Math.round(r.top+p[1]);out.pts[k]=[X,Yp,mwFree(X,Yp)]}
  const K=v3kindAt(tx,ty);out.kinds[k]=K?[K.kind,K.blocks||0,K.roof||0,K.ceil||0,K.carve?K.carve.join(','):'',K.dug||0,K.slope||0,K.gone||0]:null}
 for(const t of arr(V3.things))if(t.kind==='mine'&&t.ref&&t.dx!=null){const p=v3project([t.dx,(t.ly||0)+(t.ly?0:v3groundAt(t.dx,t.dy))+0.6,-t.dy]);if(p){const X=Math.round(r.left+p[0]),Y=Math.round(r.top+p[1]);out.units[t.ref]=[X,Y,t.x,t.y,!!t.selected,mwFree(X,Y)]}}
 send('mwprobe',JSON.stringify(out))}catch(e){send('mwprobe',JSON.stringify({error:String(e&&e.stack||e)}))}}
