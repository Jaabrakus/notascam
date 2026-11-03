// Weapon skill animations on the sprite units (art/gear3d; the animation arena), one for each of the game's weapon
// skills (CombatSkills.dm): Sword (slash, thrust), Axe (chop), Mace (smash; a warhammer's blow can launch), Spear
// (thrust; a halberd chops), Dagger (two quick stabs), Bow (ragdoll.js rdShoot), Unarmed (jab and cross), Claw (a
// double rake), Shield (bash, block), Armour (blows glance off), Throwing (a spear, knife or axe thrown at the
// target), and Defence's parry and dodge. Each plays on the unit's own sprite as a standing doll (ragdoll.js): its
// arms, torso and weapon follow keyframes (a wind-up, the blow, the follow-through), the weapon's edge leaves a trail
// through the blow, and at the blow the target reacts: it flinches or, killed, falls as the blow decides; a defender
// blocks, parries (sparks) or dodges (a miss).
//
// Keyframe angles are in a unit's own terms: 0 straight at its target, +pi/2 up, -pi/2 down (a hanging arm), pi
// behind it. R is the weapon arm, L the other (the shield arm); u the upper arm, l the forearm; W the weapon's own
// angle (left out, it follows the forearm); lean leans the body toward the target. The rest are in the unit's own leg
// lengths, so a dwarf's stride is a dwarf's: lunge moves the body in, step puts the front foot down that far ahead of
// where it stood (left out, it goes with the lunge), back moves the back foot back, crouch sinks the hips. The feet
// stay planted: the hips sink as far as the stance needs for both knees to stay bent, and shift against the lean so
// the weight stays between the feet.
const SK={defs:{
 slash:{keys:[[0],[0.16,{Ru:2.0,Rl:2.5,W:2.5,Lu:-0.9,Ll:-0.3,lean:-0.1,back:0.15,crouch:0.08}],[0.3,{Ru:0.35,Rl:0.15,W:0.1,Lu:-1.1,Ll:-0.6,lean:0.18,lunge:0.35,step:0.6,back:0.1,crouch:0.2}],
  [0.42,{Ru:-0.25,Rl:-0.4,W:-0.35,lean:0.12,lunge:0.35,step:0.6,back:0.1,crouch:0.16}],[0.72]],   /* over the shoulder, level through the target, low and forward after */hit:[0.3],trail:[0.18,0.42],death:'fall',maim:'armcut'},
 thrust:{keys:[[0],[0.18,{Ru:-2.5,Rl:0.0,W:0.06,Lu:-0.6,Ll:-0.2,lean:-0.08,back:0.25,crouch:0.12}],[0.3,{Ru:-0.1,Rl:0.0,W:0.0,lean:0.15,lunge:0.5,step:0.85,back:0.2,crouch:0.26}],[0.46,{Ru:-0.55,Rl:-0.3,W:0.1,lean:0.08,lunge:0.4,step:0.85,back:0.2,crouch:0.2}],[0.74]],hit:[0.3],trail:[0.2,0.34],death:'fall'},
 chop:{keys:[[0],[0.26,{Ru:2.6,Rl:2.9,W:2.4,lean:-0.16,back:0.2,crouch:0.06}],[0.4,{Ru:-0.4,Rl:-0.7,W:-0.9,lean:0.3,lunge:0.35,step:0.6,back:0.15,crouch:0.32}],[0.62,{Ru:-0.5,Rl:-0.8,W:-1.0,lean:0.25,lunge:0.35,step:0.6,back:0.15,crouch:0.26}],[0.92]],hit:[0.4],trail:[0.28,0.44],two:true,death:'armoff',deaths:['armoff','armoff','fall'],maim:'armcut'},
 smash:{keys:[[0],[0.24,{Ru:2.4,Rl:2.7,W:2.0,lean:-0.14,back:0.2,crouch:0.06}],[0.38,{Ru:-0.3,Rl:-0.6,W:-1.2,lean:0.3,lunge:0.35,step:0.6,back:0.15,crouch:0.34}],[0.62,{Ru:-0.4,Rl:-0.7,W:-1.25,lean:0.24,lunge:0.35,step:0.6,back:0.15,crouch:0.28}],[0.9]],hit:[0.38],trail:[0.26,0.42],dust:true,death:'flying'},
 launch:{keys:[[0],[0.34,{Ru:2.7,Rl:3.0,W:2.5,lean:-0.22,back:0.3,crouch:0.18}],[0.5,{Ru:-0.2,Rl:-0.5,W:-1.15,lean:0.36,lunge:0.45,step:0.75,back:0.25,crouch:0.4}],[0.78,{Ru:-0.3,Rl:-0.6,W:-1.2,lean:0.3,lunge:0.45,step:0.75,back:0.25,crouch:0.34}],[1.1]],hit:[0.5],trail:[0.36,0.54],two:true,dust:true,death:'hammer',always:'hammer'},
 sweep:{keys:[[0],[0.24,{Ru:1.4,Rl:2.2,W:2.6,lean:-0.12,back:0.15,crouch:0.1}],[0.4,{Ru:-0.6,Rl:-0.4,W:-0.5,lean:0.24,lunge:0.3,step:0.55,back:0.15,crouch:0.28}],[0.6,{Ru:-0.9,Rl:-0.8,W:-0.9,lean:0.18,lunge:0.3,step:0.55,back:0.15,crouch:0.24}],[0.9]],hit:[0.4],trail:[0.26,0.44],two:true,death:'spin',deaths:['spin','legoff'],maim:'legcut'},
 stab:{keys:[[0],[0.07,{Ru:-2.4,Rl:0.1,W:0.0,back:0.1,crouch:0.1}],[0.14,{Ru:-0.2,Rl:0.0,W:0.0,lean:0.12,lunge:0.25,step:0.45,back:0.1,crouch:0.16}],[0.22,{Ru:-2.4,Rl:0.1,W:0.0,lunge:0.12,step:0.45,back:0.1,crouch:0.12}],[0.3,{Ru:-0.15,Rl:0.0,W:0.0,lean:0.14,lunge:0.3,step:0.5,back:0.1,crouch:0.18}],[0.5]],hit:[0.14,0.3],trail:[0.08,0.32],death:'crumple'},
 punch:{keys:[[0],[0.08,{Lu:-0.15,Ll:0.0,lean:0.08,lunge:0.2,step:0.4,back:0.1,crouch:0.12}],[0.16,{Lu:-1.2,Ll:-0.5,lunge:0.1,step:0.4,back:0.1,crouch:0.1}],[0.25,{Ru:-0.1,Rl:0.0,lean:0.16,lunge:0.35,step:0.5,back:0.1,crouch:0.16}],[0.37,{Ru:-1.2,Rl:-0.6,lunge:0.2,step:0.5,back:0.1,crouch:0.12}],[0.56]],hit:[0.08,0.25],bare:true,death:'fall'},
 claw:{keys:[[0],[0.15,{Ru:1.8,Rl:2.4,Lu:1.7,Ll:2.3,lean:-0.1,back:0.15,crouch:0.16}],[0.3,{Ru:-0.7,Rl:-1.1,Lu:-0.6,Ll:-1.0,lean:0.22,lunge:0.4,step:0.65,back:0.15,crouch:0.3}],[0.6]],hit:[0.3],bare:true,claw:true,death:'spin',maim:'armcut'},
 bash:{keys:[[0],[0.15,{Lu:-2.4,Ll:0.3,lean:-0.08,back:0.2,crouch:0.18}],[0.27,{Lu:0.0,Ll:0.0,lean:0.22,lunge:0.55,step:0.85,back:0.15,crouch:0.24}],[0.55]],hit:[0.27],shield:true,death:'flying',knock:true},
 throw:{keys:[[0],[0.26,{Ru:2.3,Rl:2.7,W:2.6,Lu:0.3,Ll:0.3,lean:-0.16,back:0.35,crouch:0.14}],[0.38,{Ru:0.5,Rl:0.3,W:0.3,Lu:-0.6,Ll:-0.4,lean:0.2,lunge:0.3,step:0.55,back:0.3,crouch:0.2}],[0.52,{Ru:-0.4,Rl:-0.6,lean:0.1,lunge:0.25,step:0.55,back:0.3,crouch:0.12}],[0.75]],release:0.38,ranged:true,death:'fall'},
 // a staff's spell (magicfx.js mfCast): raised back over the shoulder, then thrust at the target, the free hand thrown
 // forward; the staff's own pixel effect leaves its head at the thrust
 cast:{keys:[[0],[0.24,{Ru:1.9,Rl:2.4,W:1.65,Lu:0.8,Ll:1.3,lean:-0.12,back:0.2,crouch:0.06}],[0.42,{Ru:0.35,Rl:0.25,W:0.45,Lu:0.15,Ll:0.05,lean:0.15,lunge:0.2,step:0.4,back:0.15,crouch:0.12}],
  [0.62,{Ru:0.4,Rl:0.3,W:0.5,Lu:0.2,Ll:0.1,lean:0.1,lunge:0.18,step:0.4,back:0.15,crouch:0.1}],[0.95]],release:0.42,ranged:true,spell:true,death:'fall'},
 // the game's own weapon moves (WeaponSkills.dm, the user 2026-10-25: "lets do it"), played when the server says a blow
 // was one (Hits.dm "mv", game.js g3hit): each with the unit's own weapon. Their passives (a burning edge, frostbite...)
 // ride on the plain swings with their own pixel effects.
 lunge:{keys:[[0],[0.22,{Ru:-2.6,Rl:0.0,W:0.06,Lu:-0.4,Ll:-0.1,lean:-0.12,back:0.3,crouch:0.18}],[0.36,{Ru:-0.05,Rl:0.0,W:0.0,Lu:-1.3,Ll:-0.5,lean:0.3,lunge:1.0,step:1.35,back:0.25,crouch:0.4}],
  [0.6,{Ru:-0.3,Rl:-0.15,W:0.05,lean:0.22,lunge:0.9,step:1.35,back:0.25,crouch:0.34}],[0.95]],hit:[0.36],trail:[0.24,0.4],death:'fall'},   /* a long step in, the point driven home */
 heavyblow:{keys:[[0],[0.32,{Ru:2.8,Rl:3.0,W:2.7,Lu:2.6,Ll:2.9,lean:-0.2,back:0.25,crouch:0.1}],[0.46,{Ru:-0.35,Rl:-0.6,W:-0.8,Lu:-0.3,Ll:-0.5,lean:0.34,lunge:0.4,step:0.7,back:0.2,crouch:0.36}],
  [0.75,{Ru:-0.45,Rl:-0.7,W:-0.95,lean:0.28,lunge:0.4,step:0.7,back:0.2,crouch:0.3}],[1.05]],hit:[0.46],trail:[0.34,0.5],two:true,dust:true,death:'flying',maim:'armcut'},   /* both hands, high over the head and down */
 riposte:{keys:[[0],[0.1,{Ru:0.4,Rl:1.5,W:1.75,back:0.25,crouch:0.16}],[0.9,{Ru:0.5,Rl:1.6,W:1.8,lean:-0.04,back:0.28,crouch:0.2}],[1.15]],self:true},   /* its guard up and held: what strikes at it is parried and struck back */
 cleave:{keys:[[0],[0.28,{Ru:1.2,Rl:1.9,W:2.4,Lu:1.0,Ll:1.6,lean:-0.18,back:0.2,crouch:0.14}],[0.44,{Ru:-0.5,Rl:-0.3,W:-0.3,Lu:-0.6,Ll:-0.4,lean:0.3,lunge:0.35,step:0.6,back:0.15,crouch:0.32}],
  [0.66,{Ru:-1.1,Rl:-0.9,W:-1.0,Lu:-1.0,Ll:-0.8,lean:0.2,lunge:0.35,step:0.6,back:0.15,crouch:0.26}],[1.0]],hit:[0.44],trail:[0.3,0.66],two:true,death:'spin',deaths:['spin','armoff'],maim:'armcut'},   /* a wide two-handed sweep through all round the foe */
 skullcracker:{keys:[[0],[0.3,{Ru:2.9,Rl:3.1,W:2.6,Lu:1.2,Ll:1.6,lean:-0.24,back:0.3,crouch:0.3}],[0.44,{Ru:-0.2,Rl:-0.55,W:-1.3,Lu:-0.7,Ll:-0.4,lean:0.4,lunge:0.4,step:0.7,back:0.2,crouch:0.42}],
  [0.7,{Ru:-0.3,Rl:-0.65,W:-1.3,lean:0.32,lunge:0.4,step:0.7,back:0.2,crouch:0.36}],[1.0]],hit:[0.44],trail:[0.32,0.48],dust:true,death:'crumple'},   /* crouched, then up and over onto the head */
 skewer:{keys:[[0],[0.24,{Ru:-2.7,Rl:0.0,W:0.05,Lu:-1.6,Ll:-0.6,lean:-0.14,back:0.35,crouch:0.18}],[0.38,{Ru:-0.05,Rl:0.0,W:0.0,Lu:-0.5,Ll:-0.2,lean:0.28,lunge:0.8,step:1.1,back:0.3,crouch:0.34}],
  [0.62,{Ru:-0.15,Rl:0.0,W:0.02,lean:0.24,lunge:0.75,step:1.1,back:0.3,crouch:0.3}],[0.95]],hit:[0.38],trail:[0.26,0.42],two:true,death:'flying'},   /* driven through, into the one behind */
 flurry:{keys:[[0],[0.06,{Ru:-2.4,Rl:0.1,W:0.0,back:0.1,crouch:0.12}],[0.12,{Ru:-0.2,Rl:0.0,W:0.0,lean:0.14,lunge:0.25,step:0.45,back:0.1,crouch:0.18}],[0.18,{Ru:-2.3,Rl:0.1,W:0.0,lunge:0.15,step:0.45,back:0.1,crouch:0.14}],
  [0.24,{Ru:0.1,Rl:0.0,W:0.0,lean:0.16,lunge:0.3,step:0.5,back:0.1,crouch:0.2}],[0.3,{Ru:-2.4,Rl:0.1,W:0.0,lunge:0.18,step:0.5,back:0.1,crouch:0.15}],[0.36,{Ru:-0.35,Rl:0.0,W:0.0,lean:0.16,lunge:0.32,step:0.5,back:0.1,crouch:0.2}],
  [0.42,{Ru:-2.3,Rl:0.1,W:0.0,lunge:0.2,step:0.5,back:0.1,crouch:0.15}],[0.48,{Ru:-0.1,Rl:0.0,W:0.0,lean:0.18,lunge:0.35,step:0.5,back:0.1,crouch:0.22}],[0.7]],hit:[0.12,0.24,0.36,0.48],trail:[0.06,0.5],death:'crumple'},   /* four quick stabs */
 runebolt:{keys:[[0],[0.26,{Ru:1.6,Rl:2.2,W:2.2,Lu:0.6,Ll:1.0,lean:-0.1,back:0.2,crouch:0.08}],[0.44,{Ru:0.1,Rl:0.05,W:0.05,Lu:-0.4,Ll:-0.2,lean:0.14,lunge:0.25,step:0.45,back:0.15,crouch:0.14}],
  [0.7,{Ru:0.1,Rl:0.05,W:0.05,lean:0.1,lunge:0.2,step:0.45,back:0.15,crouch:0.12}],[1.0]],release:0.44,ranged:true,spell:true,death:'fall'},   /* the rune sword raised, then pointed: the bolt leaves its point */
 firewave:{keys:[[0],[0.26,{Ru:1.3,Rl:2.0,W:2.5,lean:-0.14,back:0.2,crouch:0.18}],[0.42,{Ru:-0.9,Rl:-0.6,W:-0.8,lean:0.3,lunge:0.3,step:0.6,back:0.2,crouch:0.42}],
  [0.66,{Ru:-1.2,Rl:-1.0,W:-1.1,lean:0.24,lunge:0.3,step:0.6,back:0.2,crouch:0.36}],[1.0]],hit:[0.42],trail:[0.28,0.66],death:'fall'},   /* a low wide sweep that throws the fire on */
 frozenhamstring:{keys:[[0],[0.26,{Ru:2.2,Rl:2.6,W:2.2,lean:-0.12,back:0.2,crouch:0.1}],[0.42,{Ru:-1.0,Rl:-1.2,W:-1.4,lean:0.4,lunge:0.35,step:0.65,back:0.18,crouch:0.48}],
  [0.68,{Ru:-1.1,Rl:-1.3,W:-1.5,lean:0.32,lunge:0.35,step:0.65,back:0.18,crouch:0.42}],[1.0]],hit:[0.42],trail:[0.3,0.5],two:true,death:'fall',deaths:['legoff','fall'],maim:'legcut'},   /* down low at the legs */
 calllightning:{keys:[[0],[0.3,{Ru:2.9,Rl:3.0,W:1.6,Lu:1.0,Ll:1.4,lean:-0.18,back:0.15,crouch:0.04}],[0.7,{Ru:3.0,Rl:3.05,W:1.6,Lu:1.1,Ll:1.5,lean:-0.2,back:0.15,crouch:0.04}],
  [0.86,{Ru:0.2,Rl:0.1,W:0.1,Lu:-0.4,Ll:-0.2,lean:0.16,lunge:0.25,step:0.45,back:0.15,crouch:0.14}],[1.2]],release:0.86,ranged:true,spell:true,death:'stiff'},   /* the storm spear held up to the sky, then down at the foe */
 bonespear:{keys:[[0],[0.28,{Ru:2.3,Rl:2.7,W:2.0,Lu:0.4,Ll:0.5,lean:-0.18,back:0.3,crouch:0.12}],[0.44,{Ru:0.4,Rl:0.2,W:0.4,Lu:-0.6,Ll:-0.4,lean:0.22,lunge:0.3,step:0.55,back:0.25,crouch:0.2}],
  [0.7,{Ru:0.3,Rl:0.2,W:0.35,lean:0.12,lunge:0.25,step:0.55,back:0.25,crouch:0.14}],[1.0]],release:0.44,ranged:true,spell:true,death:'fall'},   /* thrown from the staff like a spear */
 raiseskeleton:{keys:[[0],[0.4,{Ru:2.9,Rl:3.0,W:1.6,Lu:2.6,Ll:2.9,lean:-0.12,crouch:0.05}],[1.2,{Ru:2.95,Rl:3.05,W:1.6,Lu:2.7,Ll:3.0,lean:-0.14,crouch:0.05}],[1.6]],self:true,spell:true},   /* both hands raise the staff: the dead rise */
 // getting up from the ground (skGetUp): tilt is how far the body still lies (1 flat, 0 upright). It pushes up on one
 // hand with its knees drawn in, comes up to a kneel with one foot forward, then stands.
 getup:{keys:[[0,{tilt:1,crouch:0.1,Ru:-1.3,Rl:-1.3,Lu:-1.4,Ll:-1.4}],[0.35,{tilt:0.6,crouch:0.55,Ru:-2.1,Rl:-1.9,Lu:-0.8,Ll:-0.3,lean:0.3,back:0.1}],
  [0.8,{tilt:0.2,crouch:0.5,Ru:-1.7,Rl:-1.6,Lu:-0.6,Ll:-0.2,lean:0.15,step:0.35,back:0.1}],[1.25,{tilt:0,crouch:0.06,lean:0.02}],[1.5]],tilt:true},
 // the defender's side: started so the guard is up as the blow lands
 block:{keys:[[0],[0.12,{Lu:0.15,Ll:1.1,lean:-0.05,step:0,back:0.35,crouch:0.24}],[0.55,{Lu:0.15,Ll:1.1,lean:-0.08,step:0,back:0.35,crouch:0.24}],[0.8]],shield:true},
 parry:{keys:[[0],[0.12,{Ru:0.4,Rl:1.5,W:1.75,step:0,back:0.25,crouch:0.16}],[0.45,{Ru:0.5,Rl:1.6,W:1.8,step:0,back:0.25,crouch:0.16}],[0.7]]},
 dodge:{keys:[[0],[0.14,{lean:-0.4,lunge:-0.6,Ru:-1.0,Lu:-1.0,step:-0.15,back:0.9,crouch:0.2}],[0.42,{lean:-0.3,lunge:-0.55,step:-0.15,back:0.9,crouch:0.14}],[0.7]]},
},acts:[],shots:[],trails:[]};
// the weapons each skill is done with (the arena lends one when the unit holds none of them)
const SKWEAPON={slash:['arming sword','longsword','scimitar','rune sword','flame sword','void blade','soul eater'],thrust:['arming sword','longsword','scimitar','spear','rune sword','flame sword','storm spear','soul eater','bloodwhisker'],
 chop:['battle axe','hand axe','halberd','frost axe'],smash:['mace','morning star','warhammer','holy mace'],launch:['warhammer'],sweep:['halberd'],stab:['dagger'],throw:['spear','dagger','hand axe'],
 parry:['arming sword','longsword','scimitar','spear','halberd','rune sword','flame sword','void blade','storm spear','soul eater','bloodwhisker'],
 mine:['pickaxe'],chop:['hand axe','battle axe'],build:['hammer'],smith:['hammer'],fish:['fishing rod'],spearfish:['harpoon','spear'],till:['spade'],
 cast:['crystal staff','orb staff','skull staff','flame staff','nature staff','dragon staff','spider staff']};   /* the enchanted weapons (magicfx.js) do their base weapon's skills */
const SKLEND={till:'spade:wood',spearfish:'harpoon:iron',mine:'pickaxe:iron',chop:'hand axe:iron',build:'hammer:iron',smith:'hammer:iron',fish:'fishing rod:wood',cast:'crystal staff',slash:'arming sword:iron',thrust:'spear:iron',chop:'battle axe:iron',smash:'mace:iron',launch:'warhammer:iron',sweep:'halberd:iron',stab:'dagger:iron',throw:'spear:iron',parry:'arming sword:iron'};
const SKTWO=new Set(['spade','harpoon','battle axe','warhammer','halberd','spear','pickaxe','longsword','rune sword','frost axe','storm spear','bloodwhisker']);

// The unit's weapon for a skill: its own if it fits, else one lent for the skill (given back after).
function skGear(t,skill,want){const g=t.g3,need=want?[want.split(':')[0]]:SKWEAPON[skill],have=g.w?g.w.split(':')[0]:null;let lent=null;
 if(need&&!(have&&need.includes(have))){lent={w:g.w};t.g3={...g,w:want||SKLEND[skill]}}
 if((skill==='bash'||skill==='block')&&!g.s){lent=lent||{};lent.s=null;t.g3={...t.g3,s:'round:iron'}}
 if(lent){t.g3p=undefined;t.g3kk=undefined;const kd=V3.disp.get(t.key);if(kd&&kd.rc)kd.rc.ep=null}return lent}
function skFace(t,target){const dx=target.x-t.x,dy=target.y-t.y;t.dir=Math.abs(dx)>=Math.abs(dy)?(dx>=0?4:8):(dy>=0?1:2);const kd=V3.disp.get(t.key);if(kd&&kd.rc)kd.rc.ep=null}
// A melee blow needs the target in reach: the striker steps to the tile beside it, on its own side.
function skReach(t,target){if(typeof G3G!=='undefined'&&G3G.game)return;   /* in the game the server places it (a two-tile move reaches with its lunge) */const dx=target.x-t.x,dy=target.y-t.y;if(Math.max(Math.abs(dx),Math.abs(dy))<=1)return;
 if(Math.abs(dx)>=Math.abs(dy)){t.x=target.x-Math.sign(dx);t.y=target.y}else{t.x=target.x;t.y=target.y-Math.sign(dy)}t.dx=t.x;t.dy=t.y}

// Play a skill: t at target (for a defence, the striker it guards against). opt: {kill, guard: 'block'|'parry'|'dodge'|'armour'}
function skAct(t,skill,target,opt){opt=opt||{};const D=SK.defs[skill];if(!D||!t.g3last)return null;if(t.dead&&!opt.death)return null;   /* the dead act out only their death (deaths.js rdDie): a guard or swing timed before it fell (the setTimeouts below) took over the death act and stopped its fall, so it swayed till g3rebind felled it or stood (the owner, 10-28: "Death animation loop") */if(!RD.rig){rdLoad();return null}
 if(target&&target!==t){skFace(t,target);if(!D.ranged&&!['block','parry','dodge'].includes(skill))skReach(t,target)}
 if(opt.at){const dx=opt.at[0]-t.x,dy=-opt.at[2]-t.y;t.dir=Math.abs(dx)>=Math.abs(dy)?(dx>=0?4:8):(dy>=0?1:2);const kd=V3.disp.get(t.key);if(kd&&kd.rc)kd.rc.ep=null}   /* work at a spot: turned to it (work.js) */
 const lent=skGear(t,skill,opt.weapon),A={t,skill,D,target,opt,lent,t0:performance.now()/1000,doll:null,hits:0,released:false,trail:[]};
 // the defender's guard goes up so it meets the blow
 // a throw: a shield comes up as it leaves the hand
 if(target&&(opt.guard==='block'||opt.guard==='dodge')&&D.release!=null&&!D.spell){const gd=opt.guard;setTimeout(()=>{if(target.g3last&&V3.things.includes(target))skAct(target,gd,t,{})},Math.max(0,(0.12+D.release-0.3)*1000/(RD.slow||1)))}
 if(target&&opt.guard&&opt.guard!=='armour'&&D.hit){const g=opt.guard;setTimeout(()=>{if(target.g3last&&V3.things.includes(target))skAct(target,g,t,{})},Math.max(0,(0.12+D.hit[0]-0.18)*1000/(RD.slow||1)))}
 if(!opt.doll)for(const B of SK.acts.concat(SK.pending||[]))if(B.t===t&&B!==A&&!B.replaced){B.replaced=true;B.opt.loop=false;B.opt.then=null;if(B.doll&&B.doll.alive&&!B.doll.done)A.opt.doll=B.doll}   /* one move a unit: the new one takes over */
 (SK.stepping?SK.pending:SK.acts).push(A);return A}   /* started from inside a move's step (its then): joins after the step */

// The weapon slung on its back, slanting over the shoulder, the hilt up behind its head like a quiver's arrows (and,
// stowShield, the shield on its back too): riding on the body, behind it as seen from in front and side on, over it
// as seen from behind.
function skStow(d,shield){const L=d.limbs,nk=L.head?L.head.root0:[d.pel0[0],d.pel0[1]+0.4],up=nk[1]-d.pel0[1],back=d.fl==='N'?1:-1,side=d.fl==='W'?-1:1;
 for(const a of d.gear){if(a.stowed||!(a.slot==='w'||(shield&&a.slot==='s')))continue;a.stowed=true;a.part='torso';a.live=false;
  const sw=a.slot==='w',tilt=sw?side*0.65:0,ang=Math.PI/2+tilt;a.wrist=tilt;
  a.p=sw?[-side*0.18*up,up*0.55,back*0.035]:[0,up*0.42,back*0.03];a.X=[Math.cos(ang),Math.sin(ang),0];a.Y=[-Math.sin(ang),Math.cos(ang),0];a.Z=[0,0,1]}}
const skAbs=(a,sg)=>sg>0?a:Math.PI-a;
const SKZERO=new Set(['lean','lunge','crouch','step','back','shake']);   /* these ease in from and out to nothing */
function skKey(D,b,name){const K=D.keys;let i=0;while(i<K.length-1&&K[i+1][0]<=b)i++;const k0=K[i],k1=K[Math.min(i+1,K.length-1)];
 let v0=k0[1]&&k0[1][name],v1=k1[1]&&k1[1][name];if(SKZERO.has(name)){if(v0==null)v0=0;if(v1==null)v1=0}
 if(k1===k0||b>=k1[0])return v0==null?null:v0;
 const f=(b-k0[0])/Math.max(1e-6,k1[0]-k0[0]),e=f*f*(3-2*f);
 if(v0==null&&v1==null)return null;if(v1==null)return f<0.6?v0:null;   /* letting go: the muscle takes it back to rest */
 if(v0==null)return e>0.05?v1:null;
 return v0+(v1-v0)*e}

// The legs: each foot planted on the ground where the stance puts it, the hips low enough that both knees stay bent
// and shifted against the lean so the weight stays between the feet, each knee bent to fit between hip and foot (two
// bones, the law of cosines): side on, the way the unit faces; face on, out over its foot. The front leg is the one on
// the target's side (side on, the one drawn).
function skLegs(A,d,b,sg,lunge,dt){const L=d.limbs,Lg=A.Lg;
 if(!A.legs){const set=d.sets.f,legs=[['legRu','legRl'],['legLu','legLl']].filter(([u,l])=>L[u]&&L[l]);
  const x=([u])=>L[u].root0[0]*sg-(set[u]&&set[u].borrow?1e-3:0);legs.sort((p,q)=>x(q)-x(p));
  A.legs=legs.map(([u,l],i)=>({u,l,front:i===0,foot0:[...L[l].tip0],hip0:[L[u].root0[0]-d.pel0[0],L[u].root0[1]-d.pel0[1]]}));A.own=A.D.keys.some(k=>k[1]&&'step' in k[1])}
 const D=A.D,step=skKey(D,b,'step')*Lg,back=skKey(D,b,'back')*Lg,crouch=(skKey(D,b,'crouch')||0)*Lg,lean=skKey(D,b,'lean')||0,end=D.keys[D.keys.length-1][0]+0.25;
 const feet=A.legs.map(g=>{const go=g.front?(A.own?step:lunge):-back;return [g.foot0[0]+sg*(go-lunge),g.foot0[1]]});
 // how low the hips must go: each leg reaching at most most of its length (fully only as the move begins and ends)
 const on=Math.min(1,b/0.1,Math.max(0,(end-b)/0.15)),reach=1-0.07*on;let need=0;
 A.legs.forEach((g,i)=>{const U=L[g.u],W=L[g.l];if(!U||!W)return;const r=(U.len+W.len)*reach,hx=d.pel0[0]+g.hip0[0],dx=Math.min(Math.abs(feet[i][0]-hx),r*0.95);
  need=Math.max(need,d.pel0[1]+g.hip0[1]-(feet[i][1]+Math.sqrt(r*r-dx*dx)))});
 // the weight: as the body leans into the blow the hips go back, as it leans away they come forward
 const Ht=L.head?L.head.tip0[1]-d.pel0[1]:2.5*Lg,want=[d.pel0[0]-sg*0.3*Math.sin(lean)*Ht,d.pel0[1]-Math.max(crouch,need)],k=Math.min(1,dt*18);
 d.crouchTo=null;d.pel[0]+=(want[0]-d.pel[0])*k;d.pel[1]+=(want[1]-d.pel[1])*k;
 A.legs.forEach((g,i)=>{const U=L[g.u],W=L[g.l];if(!U||!W)return;const F=feet[i],H=rdRootNow(d,U),a=U.len,c=W.len;
  let vx=F[0]-H[0],vy=F[1]-H[1],dd=Math.hypot(vx,vy);const mx=(a+c)*0.999;if(dd<1e-4)return;if(dd>mx){vx*=mx/dd;vy*=mx/dd;dd=mx}
  const kn=d.fl==='E'?1:d.fl==='W'?-1:(H[0]>=d.pel[0]?1:-1);   /* side on the knee goes the way it faces; face on, out over the foot */
  const al=Math.acos(Math.max(-1,Math.min(1,(a*a+dd*dd-c*c)/(2*a*dd)))),th=Math.atan2(vy,vx)+kn*al,K=[H[0]+Math.cos(th)*a,H[1]+Math.sin(th)*a];
  U.pose=th;W.pose=Math.atan2(H[1]+vy-K[1],H[0]+vx-K[0])})}

// Where a living unit stands on the page, as its circle is drawn (game.js's downed doll follows it the same way); null for
// a dead one or one not placed yet. A move's doll keeps to it: one doll a unit is used move after move, and each started
// where the last left it, so in a fight (swing after swing while it stepped) the doll was left tiles from its circle
// (the owner, 10-31: "if a unit gets knocked back or dies it doesnt match the circle perfectly").
function skAt(t){return t&&!t.dead&&t.dx!=null?[t.dx+(t.px||0)+((t.iw||1)-1)/2,-t.dy-(t.py||0)]:null}
function skStep(dt,emit){const now=performance.now()/1000;SK.stepping=true;SK.pending=SK.pending||[];
 SK.acts=SK.acts.filter(A=>{if(A.replaced)return false;   /* another move or a fall took its doll */const t=A.t,b0=(now-A.t0)*(RD.slow||1)/(RD.slow||1);
  if(!A.doll){let d=A.opt.doll;   /* opt.doll: carry on in the doll it already has (lifting, then carrying) */
   if(d){d.kind='pose';d.alive=true;d.done=false;d.muscle=1}
   else{const cur=rdLive(t);if(!cur&&now-A.t0<0.12)return true;   /* a frame or two for its turned picture */
    d=rdTake(t);if(!d){const c=A.opt.death&&A.opt.then?rdLive(t):null;if(c)A.opt.then(c);return false}d.kind='pose';d.alive=true;d.muscle=1}   /* a death whose doll can't act (knocked flying, down): it falls as it is */   /* the doll it is already (one a unit), or a new one */
   const at0=A.opt.death||A.opt.walk||A.skill==='getup'?null:skAt(t);   /* a death, a carry (its own walk), getting up where it lay: as they were */
   if(at0)d.O=[at0[0],t.ly?d.O[1]:rdGround(at0[0],at0[1]),at0[1]];   /* a doll kept from its last move starts where the unit stands now */
   A.doll=d;A.a0=now;A.O0=[...d.O];A.at=at0;
   const tg=A.target&&A.target.g3last,at=tg?[tg.LX,0,tg.LZ]:A.opt.at;A.sg=at?(rdV.dot(rdV.sub([at[0],0,at[2]],[d.O[0],0,d.O[2]]),d.R)>=0?1:-1):1;
   if(A.D.bare)skStow(d,A.D.stowShield);   /* fists, claws, work with both hands: the weapon (and the shield) on its back */
   const w=d.gear.find(g=>g.slot==='w');A.w=w;A.two=(A.D.two||(w&&SKTWO.has(w.name.replace('weapon.',''))))&&!d.gear.some(g=>g.slot==='s');   /* with a shield on its arm, one hand only */
   const ln=p=>d.limbs[p]?d.limbs[p].len:0;A.Lg=Math.max(ln('legRu')+ln('legRl'),ln('legLu')+ln('legLl'))||0.17}   /* its leg's length: the stance's measure */
  const d=A.doll,D=A.D,b=now-A.a0,sg=A.sg,L=d.limbs;
  // the two hands: on a two-handed haft the other hand follows the weapon hand
  const arm={R:'R',L:'L'};
  for(const [key,p] of [['Ru','armRu'],['Rl','armRl'],['Lu','armLu'],['Ll','armLl']]){let v=skKey(D,b,key);if(A.two&&key[0]==='L'&&v==null){const r=skKey(D,b,'R'+key[1]);if(r!=null)v=r-0.12}if(L[p])L[p].pose=v==null?null:skAbs(v,sg)}
  // hands put on a spot of the body (deaths.js): Rhx, Rhy, Lhx, Lhy in picture pixels from the neck, x out to the
  // hand's own side (- across the body), y up; the arm bends to reach it
  // or Rfx, Rfy: forward toward what it works at (work.js), in picture pixels from the neck
  if(L.head)for(const sd of ['R','L']){const fx=skKey(D,b,sd+'fx');if(fx==null)continue;const fy=skKey(D,b,sd+'fy')||0,U=L['arm'+sd+'u'];if(!U)continue;
   const nk=rdRootNow(d,L.head),r=rdReach(d,'arm'+sd+'u','arm'+sd+'l',[nk[0]+sg*fx*d.k,nk[1]+fy*d.k]);if(r){U.pose=r[0];L['arm'+sd+'l'].pose=r[1]}}
  if(L.head)for(const sd of ['R','L']){const hx=skKey(D,b,sd+'hx');if(hx==null)continue;const hy=skKey(D,b,sd+'hy')||0,U=L['arm'+sd+'u'];if(!U)continue;
   const nk=rdRootNow(d,L.head),ss=Math.sign(U.root0[0]-L.head.root0[0])||1,r=rdReach(d,'arm'+sd+'u','arm'+sd+'l',[nk[0]+ss*hx*d.k,nk[1]+hy*d.k]);if(r){U.pose=r[0];L['arm'+sd+'l'].pose=r[1]}}
  // toward or away from the eye (its front or back picture, the target ahead in the view's depth): the move goes into
  // the depth, as the archer's does. The hands come in before its chest by how far they reach (drawn back, they stay
  // at the shoulder), the weapon points where its keys say but toward the target in 3D, and from its back the arms and
  // the blade are behind the body
  const tgw=A.target&&A.target.g3last?[A.target.g3last.LX,0,A.target.g3last.LZ]:A.opt.at?[A.opt.at[0],0,A.opt.at[2]]:null,Fw=tgw?rdV.n([tgw[0]-A.O0[0],0,tgw[2]-A.O0[2]]):rdV.mul(d.R,sg);
  const kx=d.fl==='E'||d.fl==='W'?1:Math.min(1,Math.abs(rdV.dot(Fw,d.R))*1.3),deep=1-kx;A.deep=deep;A.Fw=Fw;
  if(deep>0.05&&!['block','parry','dodge','lift','carry','hold'].includes(A.skill)&&!D.work&&L.head){const nk=L.head.root0;
   const shieldL=d.gear.some(g=>g.slot==='s');
   for(const sd of ['R','L']){if(sd==='L'&&shieldL&&!A.two&&!A.D.shield){if(deep>0.5){if(L.armLu)L.armLu.pose=null;if(L.armLl)L.armLl.pose=null}continue}   /* the shield arm keeps its shield up as it was */
    const U=L['arm'+sd+'u'],W=L['arm'+sd+'l'];if(!U||!W||U.pose==null||W.pose==null)continue;const S=rdRootNow(d,U),a=U.len,c=W.len;
    const E=[S[0]+Math.cos(U.pose)*a,S[1]+Math.sin(U.pose)*a],H=[E[0]+Math.cos(W.pose)*c,E[1]+Math.sin(W.pose)*c],ext=((H[0]-S[0])*sg)/(a+c),ss=Math.sign(S[0]-nk[0])||1;
    const P=[S[0]+(nk[0]-S[0])*Math.max(0,ext)*0.85+ss*Math.max(0,-ext)*0.25*(a+c),H[1]],r=rdReach(d,'arm'+sd+'u','arm'+sd+'l',P,d.fl==='N');
    if(r){U.pose=rdMixA(U.pose,r[0],deep);W.pose=rdMixA(W.pose,r[1],deep)}}
   d.armsBehind=d.fl==='N'&&deep>0.5}
  else d.armsBehind=false;
  const lean=(skKey(D,b,'lean')||0)+(skKey(D,b,'shake')||0)*(Math.sin(now*47)+0.5*Math.sin(now*31));let lunge=(skKey(D,b,'lunge')||0)*A.Lg;   /* shake: a shiver, a convulsion */if(D.tilt)d.phi+=(-sg*lean-d.phi)*Math.min(1,dt*8);else d.phi=-sg*lean;   /* getting up: from however it lay */
  if(D.tilt)d.tilt=skKey(D,b,'tilt')||0;   /* getting up: how far it still lies */
  if(d.jolt){const u=(now-d.jolt.t)/0.35;if(u<1){const k=d.jolt.k*Math.sin(Math.PI*Math.min(1,u*2))*(1-u);d.phi+=k;lunge-=Math.abs(k)*0.15*A.Lg}else d.jolt=null}   /* struck mid-move: a jolt, and it goes on */
  if(A.at){const a=skAt(t);if(a&&(a[0]!==A.at[0]||a[1]!==A.at[1])){const X=A.O0[0]+a[0]-A.at[0],Z=A.O0[2]+a[1]-A.at[1];A.O0=[X,t.ly?A.O0[1]:rdGround(X,Z),Z];A.at=a}}   /* the unit stepped (or was moved) mid-move: its doll goes with it */
  d.O=rdV.add(A.O0,rdV.mul(rdV.n(rdV.add(rdV.mul(d.R,sg*kx),rdV.mul(Fw,deep))),lunge));   /* the lunge toward the target, into the depth too */
  skLegs(A,d,b,sg,lunge*kx,dt);
  // the grip: the weapon slides into the fist as the move starts (the standing picture holds it a little apart) and
  // back as it ends, so the arm carries it from its hand
  if(A.w&&L[A.w.part]){const P=L[A.w.part];if(!A.g0)A.g0=[...A.w.p];const fist=[P.tip0[0]-P.root0[0],P.tip0[1]-P.root0[1],A.g0[2]],end0=D.keys[D.keys.length-1][0]+0.25;
   const f=A.looped?(A.stop?Math.min(1,Math.max(0,(end0-b)/0.15)):1):Math.min(1,b/0.12,Math.max(0,(end0-b)/0.15)),e=f*f*(3-2*f);   /* a job going round: kept in the fist */for(let i=0;i<3;i++)A.w.p[i]=A.g0[i]+(fist[i]-A.g0[i])*e}
  // the weapon's own angle
  if(A.w&&L[A.w.part]){const W=skKey(D,b,'W');if(W==null)A.w.wrist*=Math.max(0,1-dt*10);else{const f=rdPartFrame(d,A.w.part);let want=skAbs(W,sg)-(A.w.aw0+f.ang);while(want-A.w.wrist>Math.PI)want-=2*Math.PI;while(want-A.w.wrist<-Math.PI)want+=2*Math.PI;A.w.wrist+=(want-A.w.wrist)*Math.min(1,dt*30)}}
  // into the depth: the weapon's direction in 3D, its angle in the keys (forward and up) turned to point at the target
  if(A.w){if(deep>0.1){const W=skKey(D,b,'W');let ang;if(W!=null)ang=W;else{const f=rdPartFrame(d,A.w.part),fa=f.abs!=null?f.abs:0;ang=sg>0?fa:Math.PI-fa}
    const X3=rdV.n(rdV.add(rdV.mul(Fw,Math.cos(ang)),[0,Math.sin(ang),0]));A.w.aim3=X3;A.w.aimK=deep;A.w.aimOff=rdV.mul(Fw,0.05*deep);A.w.live=true}
   else if(A.w.aim3){A.w.aim3=null;A.w.live=false}}
  // the edge's trail through the blow
  if(A.w&&D.trail&&b>=D.trail[0]&&b<=D.trail[1]){const g=rdGearWorld(d,A.w),len=skLen(A.w.name)*A.w.s,X=rdV.n(g.X);A.trail.push({t:now,tip:rdV.add(g.o,rdV.mul(X,len)),mid:rdV.add(g.o,rdV.mul(X,len*0.45)),tier:A.w.tier,st:A.w.name.replace('weapon.','')});if(!SK.trails.includes(A.trail))SK.trails.push(A.trail)}
  // the blow lands
  if(D.hit)while(A.hits<D.hit.length&&b>=D.hit[A.hits]){if(D.work)wkStrike(A,emit);else skHit(A,A.hits===D.hit.length-1);A.hits++}   /* work: the tool bites (work.js) */
  // a thrown weapon leaves the hand
  if(D.release!=null&&!A.released&&b>=D.release&&D.work==='netfish'){A.released=true;wkCast(A,null)}   /* the net goes out (no tool in hand) */
  if(D.release!=null&&!A.released&&b>=D.release){A.released=true;if(A.w){const g=rdGearWorld(d,A.w);
   if(D.spell){if(typeof mfCast==='function')mfCast(A.w.name.replace('weapon.',''),g,A.w.s,A.target,A.opt.kill)}   /* the spell leaves the staff's head */
   else if(D.work)wkCast(A,g);   /* the line goes out (work.js) */
   else{d.gear.splice(d.gear.indexOf(A.w),1);skThrow(A,g)}}}
  const end=D.keys[D.keys.length-1][0]+0.25;
  if(A.opt.walk){const W=A.opt.walk;A.walked=(A.walked||0)+dt;if(A.walked<(W.until||1e9))A.O0=rdV.add(A.O0,rdV.mul(W.dir,W.speed*dt))}   /* walking as it goes (carrying) */
  if(A.opt.fx)A.opt.fx(d,dt,b,emit,A);   /* a death's or a job's own effects as it is acted out (deaths.js, work.js) */
  if(b>end&&A.opt.loop&&!A.stop){A.a0=now;A.hits=0;A.released=false;A.trail=[];A.looped=true;return true}   /* a job goes round till it is stopped */
  if(A.stop&&A.opt.then&&A.climbing){d.tilt=null;A.opt.then(d,A);return false}   /* a climb ends where it got to */
  if(b>end&&A.opt.then){d.tilt=null;A.opt.then(d,A);return false}   /* then something else from where it is (a fall) */
  if(b>end){d.done=true;d.tilt=null;if(A.opt.walk){t.x=Math.round(d.O[0]);t.y=Math.round(-d.O[2]);t.dx=t.x;t.dy=t.y}if(A.lent){if('w' in A.lent)t.g3={...t.g3,w:A.lent.w};if('s' in A.lent)t.g3={...t.g3,s:A.lent.s};if(!t.g3.w)delete t.g3.w;if(!t.g3.s)delete t.g3.s;t.g3p=undefined;t.g3kk=undefined}
   rdBack(t);return false}
  return true});
 SK.stepping=false;if(SK.pending.length){SK.acts.push(...SK.pending);SK.pending.length=0}
 // a living unit's standing doll that no move holds (its move taken over, a knock-back's flight cut short) stays where it
 // was left while the unit walks on, its circle with it (4 tiles apart in a fight arena): off its spot for 0.3 s it is let
 // go and the unit's own picture stands on its circle again (g3rebind does so only when its tile changes)
 {const held=new Set();for(const A of SK.acts)if(A.doll)held.add(A.doll);for(const A of SK.acts)held.add(A.t);
  for(const d of RD.dolls){const t=d.t;if(d.done||d.ghost||!d.alive||d.kind!=='pose'||!t||held.has(d)||held.has(t)||t.g3ko||t.g3cl||t.g3cy)continue;
   if(typeof WK!=='undefined'&&WK.carry.get(t))continue;const a=skAt(t);if(!a)continue;   /* dying (its fall to come), carried, carrying: theirs */
   if(Math.hypot(d.O[0]-a[0],d.O[2]-a[1])<0.05){d.loose=0;continue}d.loose=(d.loose||0)+dt;if(d.loose>0.3){d.done=true;rdShow(t)}}}
 SK.trails=SK.trails.filter(T=>{while(T.length&&now-T[0].t>0.2)T.shift();return T.length>0});
 SK.shots=SK.shots.filter(P=>skShotStep(P,dt,emit));
 if(typeof wkDraw==='function')wkDraw(emit)}

// The blow on the target: guarded (sparks or a miss), glancing off armour, or a hit: a flinch, or the skill's death.
function skHit(A,last){const T=A.target,d=A.doll;if(!T||!T.g3last)return;const tg=T.g3last,at=[tg.LX,tg.yA+tg.sh*0.5,tg.LZ];
 const from=rdV.n([tg.LX-A.O0[0],0,tg.LZ-A.O0[2]]),g=A.opt.guard;
 if(A.D.dust){const w=A.w&&rdGearWorld(d,A.w);rdDust(w?[w.o[0],rdGround(w.o[0],w.o[2]),w.o[2]]:at,9)}
 if(A.D.claw){for(let k=0;k<3;k++)SK.trails.push(skClawStreak(at,d,k,A.sg))}
 if(g==='dodge')return;   /* stepped out of it */
 if(g==='block'||g==='parry'){rdSparks(rdV.add(at,rdV.mul(from,-0.12)),12);return}
 if(g==='armour'){rdSparks(rdV.add(at,rdV.mul(from,-0.08)),9,[0.95,0.95,1]);rdStart(T,'flinch',from);return}
 if(!last&&!A.opt.kill){rdStart(T,'flinch',from);return}
 if(A.opt.maim&&A.D.maim){rdStart(T,A.D.maim,from);return}   /* a limb taken: it lives on without it, bleeding */
 if(A.D.always&&!A.opt.kill){rdStart(T,A.D.always,from,{live:true});return}   /* launched: it gets up where it lands */
 if(A.opt.kill){const ds=A.D.deaths,kind=(T.g3maim?(T.g3maim==='arm'?'armoff':'legoff'):null)||A.D.always||(ds?ds[Math.floor(Math.random()*ds.length)]:A.D.death)||'fall';   /* a limb the game took with the blow: off with it */const t2=rdStart(T,kind,from);if(t2&&!RDNOBLOOD.has(T.g3&&T.g3.sheet)&&!A.D.bare)rdBlood(at,rdV.mul(from,0.8),10,false);return}
 if(A.opt.knock){g3knockNow(T,A.opt.knock);return}   /* the game moved it: knocked there, alive (game.js) */
 if(A.D.knock){const t2=rdStart(T,'flinch',from);if(t2){t2.om*=1.6}return}
 rdStart(T,'flinch',from);if(!RDNOBLOOD.has(T.g3&&T.g3.sheet)&&!A.D.bare&&Math.random()<0.6)rdBlood(at,rdV.mul(from,0.5),5,false)}

// The weapon's length in pixels (the far end of its model along its haft or blade).
function skLen(name){let c=RD.cen.get('len:'+name);if(c!=null)return c;const P=G3.P[name];let mx=10;if(P)for(let i=0;i<P.v;i++)mx=Math.max(mx,P.pos[i*3]/G3.q);RD.cen.set('len:'+name,mx);return mx}

// A thrown weapon: on an arc to the target, a spear along its flight, a knife or an axe turning over; then it lands.
// It lands where the game says (Throwing.dm: a leg, an arm or the chest), is blocked by a shield, glances off armour
// or misses and comes down beyond (opt.guard 'block', 'armour', 'dodge'; opt.part a body part, else rolled).
function skThrow(A,g){const T=A.target;if(!T||!T.g3last)return;const gd=A.opt.guard,res=gd==='block'?'block':gd==='armour'?'deflect':gd==='dodge'?'miss':'hit';
 const aim=rdAim(T,A.opt.part||rdThrowPart());let P=aim.P;
 if(res==='miss'){const M=rdMissPoint(g.o,P),F=rdV.n([P[0]-g.o[0],0,P[2]-g.o[2]]);P=rdV.add(M,rdV.mul(F,0.9));P[1]=rdGround(P[0],P[2])+0.03}
 const D=rdV.sub(P,g.o),dist=Math.hypot(D[0],D[2])||0.01,time=Math.max(0.15,dist/11);
 const V=[D[0]/time,(D[1]+0.5*RDG*time*time)/time,D[2]/time],spear=A.w.name.includes('spear');
 SK.shots.push({name:A.w.name,tier:A.w.tier,s:A.w.s,X:[...g.o],V,t:0,T:time,target:T,kill:A.opt.kill&&res==='hit',res,at:P,spin:spear?0:(A.sg>0?-1:1)*18,ang:0,ax:rdV.n(rdV.cross(V,[0,1,0])),from:rdV.n([V[0],0,V[2]])})}
function skShotStep(P,dt,emit){P.t+=dt;P.V[1]-=RDG*dt;P.X=rdV.add(P.X,rdV.mul(P.V,dt));P.ang+=P.spin*dt;
 let [X,Y,Z]=rdArrowBasis(P.V);if(!P.spear){const q0=rdQuat(X,Y,Z),q=rdQ.mul(rdQ.axis(P.ax,P.ang),q0);emit(P.name,P.tier,P.X,q,P.s)}else emit(P.name,P.tier,rdV.sub(P.X,rdV.mul(X,skLen(P.name)*P.s*0.6)),rdQuat(X,Y,Z),P.s);
 if(P.t>=P.T){const T=P.target;let V=rdV.mul(P.V,-0.15);
  if(P.res==='block'||P.res==='deflect'){   /* off the shield or the armour: sparks, and it bounces back */
   const d=T&&RD.dolls.find(x=>x.t===T&&!x.done&&x.alive),sg=d&&d.gear.find(x=>x.slot==='s'),at=P.res==='block'&&sg?rdGearWorld(d,sg).o:P.X;
   rdSparks(at,10,P.res==='block'?undefined:[0.95,0.95,1]);V=rdV.add(rdV.mul(P.from,-1.4),[(Math.random()-0.5)*0.8,1.6,(Math.random()-0.5)*0.8]);if(T&&P.res==='deflect')rdStart(T,'flinch',P.from)}
  else if(P.res==='hit'&&T){rdStart(T,P.kill?'fall':'flinch',P.from);if(!RDNOBLOOD.has(T.g3&&T.g3.sheet))rdBlood(P.X,rdV.mul(P.from,0.6),P.kill?10:4,false)}
  // it drops where it struck (a miss: where it came down)
  RD.loose.push({name:P.name,tier:P.tier,s:P.s,c:[skLen(P.name)/2,0,0],r:0.02,X:[...P.X],V,q:rdQuat(X,Y,Z),w:[(Math.random()-0.5)*6,(Math.random()-0.5)*6,(Math.random()-0.5)*6],rest:false,flat:2,bounce:0});return false}
 return true}

// A claw's three streaks across the target, drawn as short trails.
function skClawStreak(at,d,k,sg){const now=performance.now()/1000,T=[],B=rdBasis(d);for(let i=0;i<5;i++){const f=i/4,x=(-0.12+f*0.24)*sg,y=0.16-f*0.26+(k-1)*0.05;
  const p=rdV.add(at,rdV.add(rdV.mul(B.Ux,x),rdV.mul(B.Uy,y)));T.push({t:now+i*0.01,tip:rdV.add(p,rdV.mul(B.Uy,0.012)),mid:rdV.sub(p,rdV.mul(B.Uy,0.012)),tier:'claw'})}return T}
// The trails as fading ribbons (ragdoll.js rdFxDraw adds them to its see-through pass).
function skTrailsDraw(va){if(typeof wkLinesDraw==='function')wkLinesDraw(va);   /* fishing lines (work.js) */
 skTrailsDraw0(va)}
function skTrailsDraw0(va){const now=performance.now()/1000;for(const T of SK.trails)for(let i=1;i<T.length;i++){const a=T[i-1],b=T[i],age=now-b.t,al=Math.max(0,0.5*(1-age/0.2));if(al<=0.01)continue;
  const m=SKTRAIL[b.st],c=m?[m[0],m[1],m[2],al*1.5]:b.tier==='hell'?[1,0.55,0.3,al]:b.tier==='gold'?[1,0.9,0.55,al]:b.tier==='claw'?[1,1,1,al*1.4]:[0.9,0.94,1,al];quad(va,a.mid,b.mid,b.tip,a.tip,QN0,c)}}
// an enchanted weapon's trail in its own colour (magicfx.js)
const SKTRAIL={'flame sword':[1,0.55,0.2],'frost axe':[0.7,0.9,1],'void blade':[0.55,0.3,0.85],'rune sword':[0.5,0.75,1],'storm spear':[0.8,0.9,1],'holy mace':[1,0.88,0.5]};

// Getting up from the ground, out cold or launched and living (ragdoll.js, when it is ready): its doll goes on as a
// move from where it lies; what it dropped comes back to its hand; a launched one is now on the tile it came down on.
function skGetUp(d){const t=d.t,now=performance.now()/1000;if(d.live){t.x=Math.round(d.O[0]);t.y=Math.round(-d.O[2]);t.dx=t.x;t.dy=t.y}
 for(const b of RD.loose)if(b.doll===d&&!b.pick)b.pick=1;
 d.tiltSign=Math.sign(d.th)||1;d.tilt=Math.min(1,Math.abs(d.th)/(Math.PI/2));d.kind='pose';d.live=false;d.crouchTo=null;d.om=0;d.landed=false;d.muscle=1;
 const ln=p=>d.limbs[p]?d.limbs[p].len:0;
 SK.acts.push({t,skill:'getup',D:SK.defs.getup,target:null,opt:{},lent:null,t0:now-1,doll:d,a0:now,O0:[...d.O],sg:d.fl==='W'?-1:1,hits:0,released:false,trail:[],w:null,two:false,
  Lg:Math.max(ln('legRu')+ln('legRl'),ln('legLu')+ln('legLl'))||0.17})}
