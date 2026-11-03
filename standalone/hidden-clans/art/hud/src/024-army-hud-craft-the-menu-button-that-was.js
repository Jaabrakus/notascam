// ===== Army (hud-craft, the menu button that was Log): Formations and Captives =====
// Formations: the shape picker (the same `formation` command as the band card's Orders tab); the formations session's
// editor renders into #armyFormEditor through window.fmArmyEditor(el, model) while the tab is open.
// Captives: model.captives from capture-rope (see the board's Requests for the fields); empty state until then.
let armyView='formations',armyCapKey='';
const ARMY_SHAPES=[['keep','Keep','Each keeps its place around the group.',[[0,1],[2,0],[4,1],[1,3],[3,4],[5,3]]],['line','Line','Side by side.',[[0,2.5],[1,2.5],[2,2.5],[3,2.5],[4,2.5],[5,2.5]]],['column','Column','One behind another.',[[2.5,0],[2.5,1],[2.5,2],[2.5,3],[2.5,4],[2.5,5]]],['box','Box','A tight square.',[[1.5,2],[2.5,2],[3.5,2],[1.5,3],[2.5,3],[3.5,3]]]];
// diagrams in squares, like the slot markers in the world (the user chose squares over arrows); the bar along the top is the front
function armyShapeSvg(pts){return '<svg viewBox="0 0 48 48" aria-hidden="true"><rect class="as-dir" x="6" y="2" width="36" height="2" rx="1"/>'+pts.map(([c,r])=>'<rect x="'+(3.4+c*7.2).toFixed(1)+'" y="'+(7.4+r*6.8).toFixed(1)+'" width="5.2" height="5.2" rx=".8"/>').join('')+'</svg>'}
// "Your own": the formations session's layout (model.formationGrid = [[dx,dy],...], forward +dy, so +dy is drawn up), fitted to the box
function armyGridSvg(g){const top='<svg viewBox="0 0 48 48" aria-hidden="true"><rect class="as-dir" x="6" y="2" width="36" height="2" rx="1"/>';if(!g.length)return top+'<rect class="as-empty" x="9.5" y="11.5" width="29" height="29" rx="2"/></svg>';
 const xs=g.map(c=>+c[0]),ys=g.map(c=>-c[1]),x0=Math.min(...xs),y0=Math.min(...ys),w=Math.max(...xs)-x0+1,h=Math.max(...ys)-y0+1,s=Math.min(7.2,40/Math.max(w,h)),q=s*.72,ox=(48-w*s)/2,oy=7+(41-h*s)/2;
 return top+g.map((c,i)=>'<rect x="'+(ox+(xs[i]-x0)*s+(s-q)/2).toFixed(1)+'" y="'+(oy+(ys[i]-y0)*s+(s-q)/2).toFixed(1)+'" width="'+q.toFixed(1)+'" height="'+q.toFixed(1)+'" rx=".6"'+(/^(front|ranged|mage|any)$/.test(c[2])?' class="r-'+c[2]+'"':'')+'/>').join('')+'</svg>'}
// The server sends every selected unit's skills, stats and tool tiers only while the Units page shows (or one unit is
// selected: its card); otherwise each carries {style} for the band card (HUD.dm "unitspage", server-cost 10-24). Sent on
// change only; null at load, so a reloaded page says where it is once.
var hcUnitsPageSent=null;   // var, not let: queueRegions may call the hook before this line has run at load
function hcUnitsPage(){try{if(!model)return}catch(e){return}   // never before the first model: a command (a byond:// navigation) sent while the page still loads stops WebKit reading it, so send('ready','') never ran (coordinator, 15:3x); the server sends models only after ready
 const up=((!overlayHost||document.body.classList.contains('panel-open'))&&currentTab==='units')?'1':'0';if(up!==hcUnitsPageSent){hcUnitsPageSent=up;send('unitspage',up)}}
