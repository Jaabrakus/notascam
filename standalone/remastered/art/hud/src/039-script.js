/* Build panel hints that go where they say (hud-controls, 10-26; launch audit polish 5): "No stockpile yet" opens Work at
   its Stockpile section, "Set the Builder job" opens Village > Roster at the job picker. The tab changes on the server's
   next update; the place is scrolled to and lit once its page shows (like the job board's jbFocusRow), for up to 4 s. */
const HCGO={stock:['work','#stockpile','#stockpile + .grid'],builder:['village','#villageBulk','#villageBulk']};let hcGoTo=null;
function hcGo(k){const g=HCGO[k];if(!g)return;if(k==='builder')send('villageview','roster');else send('tab',g[0]);if(overlayHost){document.body.classList.add('panel-open');queueRegions()}hcGoTo={k:k,at:performance.now()};hcGoShow()}
function hcGoShow(){if(!hcGoTo)return;if(performance.now()-hcGoTo.at>4000){hcGoTo=null;return}const g=HCGO[hcGoTo.k],pg=$('page-'+g[0]),el=document.querySelector(g[1]),lit=document.querySelector(g[2]);if(!pg||pg.hidden||currentTab!==g[0]||!el||el.closest('[hidden]'))return;
 hcGoTo=null;el.scrollIntoView({block:'center'});if(lit){lit.classList.add('hcgolit');setTimeout(()=>lit.classList.remove('hcgolit'),1600)}}
document.addEventListener('click',e=>{const b=e.target.closest('#buildStats [data-hcgo]');if(b)hcGo(b.dataset.hcgo)});
{const u0=window.updateHUD;if(typeof u0==='function')window.updateHUD=function(raw){u0(raw);try{hcGoShow()}catch(e){console.error(e)}}}
