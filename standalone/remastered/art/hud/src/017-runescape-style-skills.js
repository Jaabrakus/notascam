// ===== RuneScape-style skills =====
const SKILL_ICON={Attack:'At',Strength:'Sr',Defence:'De',Ranged:'Ra',Magic:'Mg',Throwing:'Th',WoodCutting:'Wc',Mineing:'Mi',Fishing:'Fi',Butchery:'Bu',WoodCrafting:'Wd',MetalCrafting:'Me',StoneCrafting:'St',BoneCrafting:'Bo',LeatherCrafting:'Le',JewlCrafting:'Je',Cooking:'Co',Potion:'Po',Poison:'Px',Building:'Bd',Sneaking:'Sn',LockPicking:'Lp',Sword:'Sw',Axe:'Ax',Mace:'Ma',Spear:'Sp',Dagger:'Dg',Bow:'Bw',UnArmed:'Fi',Claw:'Cl',Shield:'Sh',Armour:'Ar'};
function renderSkills(box,S,u){if(!S||!S.tiles){box.hidden=true;return}   // {style} alone (several selected, Units page not open yet): nothing to drawbox.hidden=false;const open=openGuide.get(box)||'';const key=JSON.stringify([S,open,u&&u.toolTiers]);if(box.dataset.key===key)return;box.dataset.key=key;
 if(!box.dataset.wired){box.dataset.wired='1';box.addEventListener('keydown',e=>{const t=e.target.closest('.skill');if(t&&(e.key==='Enter'||e.key===' ')){e.preventDefault();t.click()}});box.addEventListener('click',e=>{const tile=e.target.closest('.skill');if(!tile)return;openGuide.set(box,openGuide.get(box)===tile.dataset.skill?'':tile.dataset.skill);box.dataset.key='';renderSkills(box,box._skills,box._unit)})}box._skills=S;box._unit=u;
 const groups=['Gathering','Artisan','Support','Combat'];let html='<h4>Skills <b>Total level '+esc(S.total)+'</b></h4><div class="skills">';
 groups.forEach(g=>arr(S.tiles).filter(t=>t.group===g).forEach(t=>{html+='<div role="button" tabindex="0" class="skill g-'+g+(open===t.id?' open':'')+'" data-skill="'+esc(t.id)+'" title="'+esc(t.label+' level '+t.level+' · '+(t.xp||0).toLocaleString()+' XP'+(t.next!=null?' · '+Math.max(0,t.next-t.xp).toLocaleString()+' to level '+(t.level+1):'')+' · click for the skill guide')+'"><i>'+esc(SKILL_ICON[t.id]||t.label.slice(0,2))+'</i><span>'+esc(t.label)+'</span><b>'+esc(t.level)+'</b><span class="bar" style="width:'+Math.max(0,Math.min(100,t.progress))+'%"></span></div>'}));
 html+='</div>';
  // Combat: which skill melee trains (RuneScape styles), and each main skill's sub-skills.
  const sub=arr(S.tiles).filter(t=>t.group==='Sub');
  if(sub.length){html+='<div class="cstyle"><span>Style</span>'+[['accurate','Accurate','Attack'],['aggressive','Aggressive','Strength'],['defensive','Defensive','Defence'],['controlled','Controlled','Attack, Strength and Defence']].map(([v,l,tr])=>'<button data-do="combatstyle" data-value="'+esc((u&&u.ref||'')+'|'+v)+'" aria-pressed="'+(S.style===v)+'" title="Melee trains '+tr+'">'+l+'</button>').join('')+'</div>';
   ['Attack','Ranged','Defence'].forEach(pn=>{const kids=sub.filter(t=>t.parent===pn);if(kids.length)html+='<div class="subsk"><b>'+pn+'</b>'+kids.map(t=>'<span role="button" tabindex="0" class="skill sub'+(open===t.id?' open':'')+'" data-skill="'+esc(t.id)+'"'+(t.cap!=null?' data-cap="'+esc(t.cap)+'"':'')+' title="'+esc(t.label+' level '+t.level+(t.cap!=null?' · held at Attack level '+t.cap:'')+' · click for the skill guide')+'">'+esc(t.label)+' <em>'+esc(t.level)+'</em></span>').join('')+'</div>'})}
  const ot=arr(S.tiles).find(t=>t.id===open);if(ot)html+=skillGuideHTML(ot,u||{});box.innerHTML=html}

// Skill guide: what each level does (verified against the game code).
const CRAFT=[[1,'Crafting succeeds 4% per level (failures use up the material)'],[21,'Items come out Average quality'],[25,'Crafting never fails'],[31,'Quality items'],[41,'Impressive quality'],[51,'Grand quality'],[61,'Masterful quality'],[76,'Epic quality'],[100,'Legendary quality (best weapons, armour and doors)']];
const WEAPON=s=>[[1,'+1 damage per 4 levels with this weapon'],...s,[150,'A Hell-Forged one can be used without losing an arm · normal skill cap (Humans 200, rulers +25)']];
const AXETIERS=[[1,'Wooden axe: basic speed'],[5,'Bone or Chitin axe: ×1.1 speed'],[15,'Metal axe: ×1.25 speed'],[25,'Silver axe: ×1.35 speed'],[35,'Gold axe: ×1.5 speed'],[50,'Adamantium axe: ×1.8 speed'],[75,'Hell-Forged axe: ×2.2 speed']];
const SKILL_GUIDE={
 Attack:[[1,'Enemies dodge you 1% less per 8 levels'],[1,'Melee in Accurate style trains it: 4 XP per point of damage'],[1,'Weapon skills (Sword, Axe, Mace, Spear, Dagger, Unarmed, Claws) are its sub-skills and keep their own tricks'],[1,'No weapon skill (those, Bow, Throwing, Shield or Armour) goes above Attack: one at Attack’s level is held there, and the XP it earns meanwhile counts as soon as Attack levels']],
 Strength:[[1,'+1 melee damage per 6 levels'],[1,'Melee in Aggressive style trains it: 4 XP per point of damage']],
 Defence:[[1,'Dodge 1% more per 12 levels and take 1 less damage per 8 levels'],[1,'Melee in Defensive style trains it'],[1,'Injuries still count: one leg halves dodging; no legs, or blind, no dodging at all'],[1,'Shield and Armour are its sub-skills']],
 Ranged:[[1,'+1 bow and throwing damage per 6 levels, +1% to hit per 8 levels'],[1,'Every bow or throwing hit trains it: 4 XP per point of damage'],[1,'Blind archers and throwers aim 40% worse'],[1,'Bow and Throwing are its sub-skills'],[1,'A bow reaches 5 tiles (bone), 6 (wooden) or 7 (metal, the forged ones, Dragonbone and Elf)'],[60,'Every bow reaches one tile further (or with Bow at 120)']],
 Magic:[[1,'Race specials (fire breath, webs, and the rest) hit 1% harder per level'],[1,'Every special hit trains it: 4 XP per point of damage']],
 Throwing:[[1,'Javelins, throwing axes and stones: every throw that hits trains it along with Ranged']],
 WoodCutting:[[1,'Chop power = level ÷ 4 per swing (level 20 ≈ 50 swings a tree, level 70 ≈ 15)'],...AXETIERS],
 Mineing:[[1,'Dig power = level ÷ 4 per swing; ore and gem finds are pure luck'],...AXETIERS.map(([l,t])=>[l,t.replace('axe','pickaxe')])],
 Fishing:[[1,'Catch chance = level ÷ 10 % per try'],[120,'Fishing stops improving']],
 Butchery:[[1,'With a butcher knife in a fight: rip meat off, chance level ÷ 60 %']],
 WoodCrafting:CRAFT,BoneCrafting:CRAFT,LeatherCrafting:CRAFT,
 MetalCrafting:[[1,'Smelting: iron 5% per level, silver 4%, gold 3%, adamantium 1%'],[1,'Dwarves: adamantium weapons succeed level %'],...CRAFT,[100,'Unlocks the Soul Blade (needs 5 Hell-Forged weapons)']],
 StoneCrafting:[[1,'Anti-portal stones succeed 3% per level'],...CRAFT,[100,'Form Gargoyle (uses up 100 levels)']],
 JewlCrafting:[[1,'Cut gems and silver rings: 4% per level'],[1,'Flawless gems: level ÷ 2 % chance'],[1,'Gold rings: level % (needs a flawless gem)'],[25,'Cutting never fails']],
 Cooking:[[1,'Cooking succeeds 4% per level (failures burn the meat)'],[25,'Cooking never fails']],
 Potion:[[1,'Potions succeed 4% per level'],[25,'Potions never fail']],
 Poison:[[1,'Extraction succeeds 4% per level'],[1,'Poison strength = level (toxic ×2, strong ×3)'],[25,'Extraction never fails']],
 Building:[[1,'Every wall you build gets +1 HP per level']],
 Sneaking:[[1,'Avoid traps: level % chance'],[1,'Escape pit traps: level ÷ 2 %']],
 LockPicking:[[1,'Pick locks: level % (Humans +5% and need no lockpick)']],
 Sword:WEAPON([[1,'Disarm the enemy: level ÷ 350 % per hit']]),
 Axe:WEAPON([[1,'Break the enemy shield: level ÷ 350 % per hit']]),
 Mace:WEAPON([[1,'Smash helmets: level ÷ 350 % per hit']]),
 Spear:WEAPON([[1,'With a shield worn: auto-block level ÷ 50 %']]),
 Dagger:WEAPON([[1,'Sleeping targets take +level damage'],[125,'Victims bleed silently']]),
 UnArmed:WEAPON([[1,'Steal the enemy weapon: level ÷ 350 % per hit']]),
 Claw:WEAPON([]),
 Bow:[[1,'Hit chance = level ÷ 4 + Agility ÷ 2 %'],[1,'+1 arrow damage per level'],[150,'A Hell-Forged bow can be used safely'],[200,'Skill cap']],
 Shield:[[1,'Block chance = level ÷ 2 − attacker Agility ÷ 4 (max 90%)'],[100,'Skill cap']],
 Armour:[[1,'Deflect chance = (Defence + level) ÷ 10 %'],[50,'Demonic armour costs no blood'],[101,'Armour stops improving']]};
const openGuide=new WeakMap();
function skillGuideHTML(t,u){const rows=SKILL_GUIDE[t.id]||[];let nextFound=false;
 const toNext=t.next!=null?Math.max(0,t.next-t.xp):null;let html='<div class="sguide"><h5>'+esc(t.label)+' · level '+esc(t.level)+'<small>'+esc((t.xp||0).toLocaleString())+' XP'+(toNext!=null?' · '+esc(toNext.toLocaleString())+' XP to level '+(t.level+1):'')+'</small></h5><p class="hint" style="margin:0 0 6px">A RuneScape-style grind: the effort per level doubles every 10 levels.</p>';
 rows.slice().sort((a,b)=>a[0]-b[0]).forEach(([l,txt])=>{const done=t.level>=l;let cls=done?'done':'';if(!done&&!nextFound){cls='next';nextFound=true}html+='<div class="row '+cls+'"><b>'+l+'</b><span>'+esc(txt)+'</span></div>'});
 const tool=arr(u.toolTiers).find(x=>x.skill===t.label);if(tool)html+='<div class="tool'+(tool.ok?'':' bad')+'">Holding: '+esc(tool.tier)+' '+esc(tool.kind.toLowerCase())+' · '+(tool.ok?'×'+esc(tool.speed)+' speed':'needs level '+esc(tool.needs)+', working at basic speed')+'</div>';
 return html+'</div>'}
const seenDrops=new Set();
function renderXPDrops(m){const box=$('xpdrops');if(!box)return;const sel=arr(m.units).filter(u=>u.selected);const one=sel.length===1?sel[0].ref:null;let stack=0;
 arr(m.xpDrops).forEach(d=>{if(seenDrops.has(d.id))return;seenDrops.add(d.id);if(seenDrops.size>200)seenDrops.delete(seenDrops.values().next().value);if(!window.rmXPDrops)return;
  const el=document.createElement('div');el.className='xpd'+(d.level?' lvl':'');el.style.bottom=stack+'px';stack+=d.level?36:22;/* a level-up box is taller than an XP line (hud-craft) */
  const who=one&&d.unit===one?'':d.name.replace(/^\{[^}]*\}\s*/,'')+': ';
  el.textContent=d.level?'★ '+who+d.skill+' level '+d.level+'!':'+'+d.xp+' '+who+d.skill+' XP';box.append(el);setTimeout(()=>el.remove(),d.level?4100:2700)})}

