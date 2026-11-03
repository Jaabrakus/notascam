// Work on the sprite units (art/gear3d; the animation arena), with the real tool in hand (3D pieces like the weapons):
// mining (the pick swung down into the rock, chips and dust flying), chopping (the axe driven into the trunk, wood
// chips), smithing (the hammer on the anvil, sparks), building (knelt, hammering at the ground), fishing (the line
// cast out, the float bobbing, a bite, the fish reeled in on its line) and carrying (lifted from the ground in front,
// held before it in both hands, walked with, dropped if it is struck). Each job goes round till it is stopped (the
// skills' moves, skills.js, looped); its effects are the game's own pixels (rdPx) and chips (rdPart). Units in tiles.
const WK={props:[],lines:[],carry:new Map(),cards:[]};
// The sack is the game's own pixel sack (Icons/Remastered/Sack.dmi, the full one: g3sack.png, its size in pixels), a
// picture facing the eye; a barrel is a big one, half the unit's height.
const WKSACK={tex:'g3sack.png',w:10,h:14},WKBIG={barrel:2.1,log:1.15};
const wkR=(a,b)=>a+Math.random()*(b-a);
Object.assign(SK.defs,{
 mine:{keys:[[0],[0.35,{Ru:2.5,Rl:2.8,W:2.3,lean:-0.15,back:0.15,crouch:0.05}],[0.55,{Ru:-0.45,Rl:-0.7,W:-0.95,lean:0.35,crouch:0.22,lunge:0.15,step:0.35,back:0.15}],
  [0.8,{Ru:-0.55,Rl:-0.8,W:-1.0,lean:0.3,crouch:0.2,lunge:0.15,step:0.35,back:0.15}],[1.15]],hit:[0.55],two:true,work:'mine'},
 woodchop:{keys:[[0],[0.3,{Ru:1.2,Rl:1.8,W:2.6,lean:-0.12,back:0.15}],[0.5,{Ru:-0.1,Rl:0.1,W:0.05,lean:0.25,lunge:0.08,step:0.25,back:0.15,crouch:0.1}],
  [0.75,{Ru:-0.3,Rl:-0.2,W:-0.3,lean:0.2,crouch:0.1,step:0.25,back:0.15}],[1.05]],hit:[0.5],two:true,work:'chop'},
 smith:{keys:[[0,{Lu:-0.5,Ll:-0.1}],[0.25,{Ru:1.4,Rl:2.3,W:2.0,Lu:-0.5,Ll:-0.1,lean:-0.05}],[0.4,{Ru:-0.4,Rl:-0.5,W:-0.9,Lu:-0.5,Ll:-0.1,lean:0.12,crouch:0.05}],
  [0.6,{Ru:-0.3,Rl:-0.4,W:-0.8,Lu:-0.5,Ll:-0.1}],[0.7]],hit:[0.4],work:'smith'},
 build:{keys:[[0,{crouch:0.45,lean:0.3,Lu:-0.9,Ll:-0.9}],[0.2,{Ru:0.8,Rl:1.6,W:1.4,crouch:0.45,lean:0.3,Lu:-0.9,Ll:-0.9}],[0.35,{Ru:-0.9,Rl:-1.1,W:-1.4,crouch:0.48,lean:0.4,Lu:-0.9,Ll:-0.9}],
  [0.55,{Ru:-0.8,Rl:-1.0,W:-1.3,crouch:0.45,lean:0.35,Lu:-0.9,Ll:-0.9}],[0.65,{crouch:0.45,lean:0.3,Lu:-0.9,Ll:-0.9}]],hit:[0.35],work:'build'},
 // cast (0.4 back, 0.6 out), wait, a bite (2.6), the strike (2.8), reel in (3.1-3.6)
 fish:{keys:[[0],[0.4,{Ru:2.2,Rl:2.6,W:2.4,lean:-0.1,back:0.1}],[0.6,{Ru:0.4,Rl:0.3,W:0.5,lean:0.12,step:0.2,back:0.1}],[2.6,{Ru:0.3,Rl:0.2,W:0.45,lean:0.08,step:0.2,back:0.1}],
  [2.8,{Ru:0.25,Rl:0.15,W:0.35,lean:0.1,step:0.2,back:0.1}],[3.1,{Ru:1.3,Rl:1.8,W:1.6,lean:-0.12,back:0.1}],[3.6,{Ru:0.6,Rl:1.0,W:1.2,back:0.05}],[4.1]],release:0.6,work:'fish'},
 // spear fishing (the game's harpoon): raised, the point down, driven into the water ahead, held, then pulled up
 // with the fish on it
 spearfish:{keys:[[0],[0.4,{Ru:1.5,Rl:2.0,W:-1.3,lean:-0.05,back:0.1}],[0.58,{Ru:-0.75,Rl:-0.95,W:-1.3,lean:0.4,crouch:0.22,lunge:0.1,step:0.35,back:0.15}],
  [0.95,{Ru:-0.75,Rl:-0.95,W:-1.3,lean:0.38,crouch:0.22,lunge:0.1,step:0.35,back:0.15}],[1.35,{Ru:0.7,Rl:1.2,W:1.1,lean:-0.08,back:0.1}],[2.0,{Ru:0.7,Rl:1.2,W:1.1,back:0.1}],[2.3]],
  hit:[0.58],two:true,work:'spearfish'},
 // net fishing: the net swung back in both hands, thrown out to open over the water, left to sink, then hauled in
 // hand over hand
 netfish:{keys:[[0,{Rhx:-1,Rhy:-11,Lhx:-1,Lhy:-11}],[0.25,{Ru:-1.9,Rl:-1.6,Lu:-1.8,Ll:-1.5,lean:0.35,crouch:0.35,back:0.35}],[0.45,{Ru:2.3,Rl:2.6,Lu:2.2,Ll:2.5,lean:-0.3,crouch:0.15,back:0.3}],
  [0.62,{Ru:0.2,Rl:0.1,Lu:0.15,Ll:0.05,lean:0.45,crouch:0.25,lunge:0.25,step:0.55,back:0.2}],   /* the whole body into the throw: wound down low and back, up and over, lunging through */
  [2.3,{Ru:-0.3,Rl:-0.1,Lu:-0.35,Ll:-0.15,lean:0.15,step:0.3,back:0.15}],[2.6,{Ru:0.4,Rl:1.4,Lu:-0.4,Ll:-0.2,lean:-0.15,back:0.25,step:0.1}],[2.9,{Ru:-0.4,Rl:-0.2,Lu:0.4,Ll:1.4,lean:-0.18,back:0.25,step:0.1}],
  [3.2,{Ru:0.4,Rl:1.4,Lu:-0.4,Ll:-0.2,lean:-0.15,back:0.25,step:0.1}],[3.5,{Ru:-0.4,Rl:-0.2,Lu:0.4,Ll:1.4,lean:-0.15,back:0.2}],[3.9,{Rhx:-1,Rhy:-12,Lhx:-1,Lhy:-12}],[4.3]],release:0.62,bare:true,stowShield:true,work:'netfish'},
 // foraging (the game's wild herbs, Doctor.dm, and the farmer's steps, FoodRoles.dm): picking from a plant at chest
 // height, a hand in among the leaves, then to the bag at its hip; picking from the ground, knelt; tilling with the
 // spade (driven in with a foot, the earth levered up and thrown); planting seeds (knelt, a hole poked, a seed in, the
 // earth pressed down); harvesting (bent, a handful gathered and cut with the free hand's knife, then bundled)
 pick:{keys:[[0],[0.35,{Rfx:13,Rfy:-9,Lfx:5,Lfy:-12,lean:0.25,step:0.35,back:0.05,crouch:0.06}],[0.55,{Rfx:14,Rfy:-8,Lfx:5,Lfy:-12,lean:0.28,step:0.35,back:0.05,crouch:0.06}],[0.75,{Rfx:13,Rfy:-10,Lfx:5,Lfy:-12,lean:0.25,step:0.35,back:0.05,crouch:0.06}],
  [1.1,{Rfx:-2,Rfy:-16,lean:0.0,crouch:0.02}],[1.35]],hit:[0.6],bare:true,work:'pick'},
 gather:{keys:[[0],[0.45,{Rfx:9,Rfy:-27,Lfx:4,Lfy:-20,lean:0.6,crouch:0.55,step:0.3,back:0.25}],[0.7,{Rfx:10,Rfy:-28,Lfx:4,Lfy:-20,lean:0.6,crouch:0.55,step:0.3,back:0.25}],
  [0.95,{Rfx:9,Rfy:-26,Lfx:4,Lfy:-20,lean:0.6,crouch:0.55,step:0.3,back:0.25}],[1.3,{Rfx:-2,Rfy:-17,lean:0.15,crouch:0.2}],[1.6]],hit:[0.75],bare:true,stowShield:true,work:'gather'},
 till:{keys:[[0],[0.3,{Ru:-0.6,Rl:-0.9,W:-1.45,Lu:-0.2,Ll:0.4,lean:0.1,step:0.3,back:0.1,crouch:0.05}],[0.5,{Ru:-0.9,Rl:-1.0,W:-1.5,Lu:-0.5,Ll:0.1,lean:0.25,step:0.3,back:0.1,crouch:0.18}],
  [0.85,{Ru:-0.2,Rl:0.3,W:-0.9,Lu:0.1,Ll:0.8,lean:-0.15,step:0.3,back:0.15,crouch:0.1}],[1.05,{Ru:0.4,Rl:0.8,W:-0.4,Lu:0.4,Ll:1.0,lean:0.1,step:0.25,back:0.1}],[1.35]],hit:[0.5,0.95],two:true,work:'till'},
 plant:{keys:[[0],[0.4,{Rfx:8,Rfy:-27,Lfx:3,Lfy:-18,lean:0.55,crouch:0.6,step:0.3,back:0.25}],[0.6,{Rfx:8,Rfy:-29,Lfx:3,Lfy:-18,lean:0.6,crouch:0.6,step:0.3,back:0.25}],
  [0.85,{Rfx:8,Rfy:-27,Lfx:9,Lfy:-27,lean:0.6,crouch:0.6,step:0.3,back:0.25}],[1.05,{Rfx:8,Rfy:-29,Lfx:9,Lfy:-29,lean:0.6,crouch:0.6,step:0.3,back:0.25}],[1.4,{crouch:0.1}],[1.7]],hit:[0.6,1.05],bare:true,stowShield:true,work:'plant'},
 harvest:{keys:[[0],[0.35,{Rfx:11,Rfy:-14,Lfx:10,Lfy:-16,lean:0.45,crouch:0.35,step:0.35,back:0.2}],[0.55,{Rfx:11,Rfy:-15,Lfx:5,Lfy:-12,lean:0.48,crouch:0.37,step:0.35,back:0.2}],
  [0.75,{Rfx:11,Rfy:-14,Lfx:11,Lfy:-15,lean:0.45,crouch:0.35,step:0.35,back:0.2}],[1.1,{Rfx:3,Rfy:-10,Lfx:3,Lfy:-10,lean:0.05,crouch:0.05}],[1.4]],hit:[0.55],bare:true,stowShield:true,work:'harvest'},
 // climbing with the climbing gear (Mountains.dm): hand over hand up the face, the knees coming up in turn, on the
 // rope from a piton above; one cycle is one reach of each hand
 climb:{keys:[[0,{Rhx:1,Rhy:8,Lhx:2,Lhy:-4,crouch:0.16,step:0.22,back:-0.12}],[0.35,{Rhx:2,Rhy:-4,Lhx:1,Lhy:8,crouch:0.04,step:-0.08,back:0.16}],[0.7,{Rhx:1,Rhy:8,Lhx:2,Lhy:-4,crouch:0.16,step:0.22,back:-0.12}]],bare:true,stowShield:true,work:'climb'},
 // carrying: bent forward to lift it (the hands down to the ground in front), up, then held before it; the feet
 // stepping as it walks (wkCarry sets it going)
 lift:{keys:[[0],[0.3,{Rhx:1,Rhy:-22,Lhx:1,Lhy:-22,lean:0.6,crouch:0.45}],[0.55,{Rhx:0,Rhy:-20,Lhx:0,Lhy:-20,lean:0.55,crouch:0.45}],[0.9,{Rhx:-1,Rhy:-9,Lhx:-1,Lhy:-9,lean:0.05,crouch:0.05}],[1.0,{Rhx:-1,Rhy:-9,Lhx:-1,Lhy:-9}]]},
 carry:{keys:[[0,{Rhx:-1,Rhy:-9,Lhx:-1,Lhy:-9,step:0.25,back:0.1,crouch:0.04}],[0.3,{Rhx:-1,Rhy:-9.5,Lhx:-1,Lhy:-9.5,step:-0.1,back:-0.25,crouch:0.06}],
  [0.6,{Rhx:-1,Rhy:-9,Lhx:-1,Lhy:-9,step:0.25,back:0.1,crouch:0.04}]]},
 hold:{keys:[[0,{Rhx:-1,Rhy:-9,Lhx:-1,Lhy:-9,crouch:0.03}],[0.8,{Rhx:-1,Rhy:-9,Lhx:-1,Lhy:-9,crouch:0.03}]]},
});
SKWEAPON.woodchop=['hand axe','battle axe'];SKLEND.woodchop='hand axe:iron';SK.defs.carry.bare=SK.defs.lift.bare=SK.defs.hold.bare=true;SK.defs.carry.stowShield=SK.defs.lift.stowShield=SK.defs.hold.stowShield=true;   /* the tools set down to carry (Jobs.dm: heavy pieces) */

// A tool's head where it bites: its far end.
function wkTip(A){const d=A.doll,g=rdGearWorld(d,A.w),X=rdV.n(g.X);return rdV.add(g.o,rdV.mul(X,skLen(A.w.name)*A.w.s*0.92))}
// The tool bites: what flies off it.
function wkStrike(A){const w=A.D.work;if(['pick','gather','plant','harvest'].includes(w)){wkForage(A);return}if(!A.w)return;const P=wkTip(A),U=[0,1,0];
 if(w==='till'){const chips=(n,col,sp)=>{for(let i=0;i<n;i++)rdPart(P,[wkR(-sp,sp),wkR(0.4,1.2),wkR(-sp,sp)],wkR(0.4,0.7),0.014,0.012,[...col,1],[...col,1],6)};chips(10,[0.36,0.25,0.15],0.7);for(let i=0;i<3;i++)rdPx(P,[wkR(-0.2,0.2),wkR(0.05,0.2),wkR(-0.2,0.2)],0.7,0.05,0.09,'dust',0,1.5);return}
 if(w==='spearfish'){for(let i=0;i<12;i++)rdPx(P,[wkR(-0.4,0.4),wkR(0.5,1.1),wkR(-0.4,0.4)],0.55,0.04,0.03,'water',3);A.caught=A.opt.catch!=null?A.opt.catch:Math.random()<0.65;return}
 const chips=(n,col,sp)=>{for(let i=0;i<n;i++)rdPart(P,[wkR(-sp,sp),wkR(0.4,1.4),wkR(-sp,sp)],wkR(0.4,0.7),0.012,0.01,[...col,1],[...col,1],6)};
 if(w==='mine'){chips(9,[0.45,0.42,0.38],0.9);for(let i=0;i<3;i++)rdPx(P,[wkR(-0.2,0.2),wkR(0.1,0.3),wkR(-0.2,0.2)],0.7,0.05,0.09,'dust',0,1.5);if(Math.random()<0.4)rdSparks(P,5)}
 else if(w==='chop'){chips(7,[0.78,0.6,0.36],0.8);chips(3,[0.42,0.28,0.16],0.6);rdPx(P,[0,0.1,0],0.6,0.04,0.07,'dust',0,1.5)}
 else if(w==='smith'){rdSparks(P,12,[1,0.8,0.35]);for(let i=0;i<4;i++)rdPx(P,[wkR(-0.4,0.4),wkR(0.2,0.6),wkR(-0.4,0.4)],0.35,0.05,0.02,'spark',2)}
 else if(w==='build'){chips(5,[0.72,0.56,0.34],0.6);for(let i=0;i<3;i++)rdPx(P,[wkR(-0.2,0.2),wkR(0.05,0.2),wkR(-0.2,0.2)],0.7,0.05,0.09,'dust',0,1.5)}}

// The line goes out: the float flies from the rod's tip to the water ahead (opt.at, or two tiles on).
function wkCast(A){if(A.D.work==='netfish'){wkNetCast(A);return}const d=A.doll,tip=wkTip(A),F=rdV.n([...(A.opt.at?[A.opt.at[0]-d.O[0],0,A.opt.at[2]-d.O[2]]:[d.R[0]*A.sg,0,d.R[2]*A.sg])]);
 const P=A.opt.water||rdV.add([d.O[0],0,d.O[2]],rdV.mul(F,2.2));P[1]=rdGround(P[0],P[2])+0.02;A.float={P,from:tip,t0:performance.now()/1000}}
// Fishing as it goes: the line from the rod's tip to the float (or the fish), the float bobbing, the bite, the catch.
function wkFish(d,dt,b,emit,A){if(!A.w||!A.float)return;const tip=wkTip(A),F=A.float,now=performance.now()/1000;let at,fish=null;
 if(b<0.9){const u=Math.max(0,Math.min(1,(b-0.6)/0.3));at=rdV.add(rdV.add(F.from,rdV.mul(rdV.sub(F.P,F.from),u)),[0,Math.sin(Math.PI*u)*0.5,0])}   /* flying out */
 else if(b<2.6)at=rdV.add(F.P,[0,Math.sin(now*3.1)*0.012,0]);   /* waiting */
 else if(b<3.1){at=rdV.add(F.P,[0,-0.03-Math.abs(Math.sin(now*14))*0.03,0]);if(!F.bit){F.bit=true;for(let i=0;i<8;i++)rdPx(F.P,[wkR(-0.3,0.3),wkR(0.4,0.8),wkR(-0.3,0.3)],0.5,0.04,0.03,'water',3)}}   /* a bite */
 else if(b<3.6){const u=(b-3.1)/0.5;at=rdV.add(rdV.add(F.P,rdV.mul(rdV.sub(tip,F.P),u)),[0,Math.sin(Math.PI*u)*0.6,0]);fish=at}   /* reeled in */
 else{fish=rdV.add(tip,[0,-0.12,0]);at=fish}
 if(b>=0.6){WK.lines.push([tip,at]);if(!fish)WK.lines.push({float:at})}
 if(fish&&b<3.9){const q=rdQuat(...rdArrowBasis(rdV.n([Math.cos(now*18)*0.4,-1,Math.sin(now*18)*0.4])));emit('load.fish','iron',fish,q,d.k*1.5)}}

// Foraging: what comes away in the hand (a berry, a leaf, a seed going in, a stalk cut), as the game's pieces.
function wkForage(A){const d=A.doll,L=d.limbs,B=rdBasis(d),h=L.armRl?rdW(d,B,L.armRl.tip[0],L.armRl.tip[1],0.05):d.O,w=A.D.work;
 const bits=(n,col,sp,up)=>{for(let i=0;i<n;i++)rdPart(h,[wkR(-sp,sp),wkR(0,up),wkR(-sp,sp)],wkR(0.4,0.8),0.012,0.009,[...col,1],[...col,1],6)};
 if(w==='pick'){bits(4,[0.25,0.55,0.18],0.4,0.6);A.held={col:[0.75,0.1,0.15]}}
 else if(w==='gather'){bits(3,[0.3,0.25,0.15],0.3,0.4);for(let i=0;i<2;i++)rdPx(h,[0,0.1,0],0.6,0.04,0.07,'dust',0,1.5);A.held={col:[0.8,0.25,0.18]}}
 else if(w==='plant'){if(A.hits===0)bits(5,[0.36,0.25,0.15],0.3,0.5);else rdPx(h,[0,0.05,0],0.6,0.04,0.07,'dust',0,1.5)}
 else if(w==='harvest'){bits(6,[0.85,0.7,0.3],0.5,0.8);A.held={col:[0.85,0.7,0.3]}}}
// While foraging: the berry, mushroom or sheaf in its hand on the way to the bag.
function wkForageFx(d,dt,b,emit,A){if(!A.held)return;const D=A.D,last=D.keys[D.keys.length-1][0];if(b<D.hit[0]||b>last-0.2){if(b<D.hit[0])A.held=null;return}
 const L=d.limbs,B=rdBasis(d),h=L.armRl?rdW(d,B,L.armRl.tip[0],L.armRl.tip[1],0.06):d.O;const r=D.work==='harvest'?0.03:0.018;rdPart(h,[0,0,0],0.04,r,r,[...A.held.col,1],[...A.held.col,1])}   /* (a sheaf: bigger) */
// Spear fishing as it goes: the fish on the harpoon's point once pulled up (when it caught one).
function wkSpear(d,dt,b,emit,A){if(!A.w||!A.caught||b<1.0||b>2.15)return;const tip=wkTip(A),now=performance.now()/1000,g=rdGearWorld(d,A.w),X=rdV.n(g.X);
 const at=rdV.sub(tip,rdV.mul(X,4*A.w.s)),q=rdQuat(...rdArrowBasis(rdV.n(rdV.add(rdV.cross(X,[0,1,0]),[0,Math.sin(now*20)*0.4,0]))));emit('load.fish','iron',at,q,d.k*1.5)}
// The net: bundled in the hands, thrown out opening into a ring of cord over the water, sinking, then hauled back in,
// closing round what it caught.
const WKN=12,WKNR=0.34;
function wkNetCast(A){const d=A.doll,F=A.opt.at?rdV.n([A.opt.at[0]-d.O[0],0,A.opt.at[2]-d.O[2]]):[d.R[0]*A.sg,0,d.R[2]*A.sg],P=A.opt.water||rdV.add([d.O[0],0,d.O[2]],rdV.mul(F,0.95));   /* close in, a tile out */
 P[1]=rdGround(P[0],P[2])+0.01;A.net={P,F,caught:A.opt.catch!=null?A.opt.catch:Math.random()<0.7}}
function wkHands(d){const L=d.limbs,B=rdBasis(d),front=rdV.dot(B.Nn,rdV.sub(V3.eye||[0,10,10],d.O))>=0,n=(front?1:-1)*0.05,h=p=>L[p]?rdW(d,B,L[p].tip[0],L[p].tip[1],n):null,a=h('armRl'),c=h('armLl');
 return a&&c?rdV.mul(rdV.add(a,c),0.5):a||c||d.O}
function wkNet(d,dt,b,emit,A){const hands=wkHands(d),N=A.net;
 if(!N||b<0.62){emit('load.net','iron',rdV.add(hands,[0,-0.02,0]),[0,0,0,1],d.k);return}   /* bundled in its hands */
 let C,R,sink=0,closed=0;
 if(b<1.05){const u=(b-0.62)/0.43;C=rdV.add(rdV.add(hands,rdV.mul(rdV.sub(N.P,hands),u)),[0,Math.sin(Math.PI*u)*0.45,0]);R=0.06+WKNR*u}   /* flying out, opening */
 else if(b<2.4){C=N.P;R=WKNR;sink=Math.min(1,(b-1.05)/0.6);if(!N.splash){N.splash=true;for(let i=0;i<16;i++){const a=i/16*6.283;rdPx(rdV.add(N.P,[Math.cos(a)*WKNR,0,Math.sin(a)*WKNR]),[Math.cos(a)*0.2,wkR(0.3,0.6),Math.sin(a)*0.2],0.5,0.035,0.025,'water',3)}}}   /* on the water, sinking */
 else if(b<3.6){const u=(b-2.4)/1.2;C=rdV.add(N.P,rdV.mul(rdV.sub([hands[0],N.P[1],hands[2]],N.P),u*0.85));R=WKNR*(1-0.75*u);sink=1-u;closed=u}   /* hauled in, closing */
 else{const at=rdV.add([d.O[0],0,d.O[2]],rdV.mul(N.F,0.35));at[1]=rdGround(at[0],at[2]);emit('load.net','iron',rdV.add(at,[0,0.04,0]),[0,0,0,1],d.k);
  if(N.caught)for(let k=0;k<3;k++)emit('load.fish','iron',rdV.add(at,[Math.cos(k*2.1)*0.08,0.03,Math.sin(k*2.1)*0.08]),rdQ.axis([0,1,0],k*2.1),d.k*1.3);return}   /* on the ground at its feet, the catch on it */
 const y=C[1]-0.015*sink,pts=[];for(let i=0;i<WKN;i++){const a=i/WKN*6.283;pts.push([C[0]+Math.cos(a)*R,y+(closed?0.08*closed:0),C[2]+Math.sin(a)*R])}
 const mid=[C[0],y-0.02*sink+(closed?0.04*closed:0),C[2]];
 for(let i=0;i<WKN;i++){WK.lines.push([pts[i],pts[(i+1)%WKN]]);WK.lines.push([mid,pts[i]]);const q=rdV.mul(rdV.add(mid,pts[i]),0.5),r=rdV.mul(rdV.add(mid,pts[(i+1)%WKN]),0.5);WK.lines.push([q,r])}   /* its rim, spokes and a ring of mesh */
 if(b>=1.05)WK.lines.push([hands,pts[0]]);   /* the line back to its hands */
 if(N.caught&&b>2.4)for(let k=0;k<3;k++)emit('load.fish','iron',[mid[0]+Math.cos(b*9+k*2.1)*R*0.4,mid[1]+0.02,mid[2]+Math.sin(b*9+k*2.1)*R*0.4],rdQ.axis([0,1,0],b*6+k),d.k*1.3)}
// Climbing: t goes up (or down) the face of the rock at `at` (a cliff, height tiles high) in dur seconds, facing it,
// hand over hand, then over the lip onto the top (coming down: the same, backwards). In the game the climb's progress
// comes from the server (View3D.dm D["climb"]); here it runs on the clock. The rope hangs from a piton at the top of the
// face, pitons are driven in up it, and the coil is on its shoulder before and after. o (the game, game.js): base, the
// foot of the face; prog(), how far it has got (0-1, the server's); rope false for a race that climbs bare-handed;
// face, lip, top: how far from the foot toward the rock the face is, the top piton, and where it ends (a game block's).
function wkClimb(t,at,height,dur,up,o){o=o||{};const A=skAct(t,'climb',null,{loop:true,at,fx:(d,dt,b,emit,A2)=>{const C=A2.cl||(A2.cl={t0:performance.now()/1000,base:o.base?[...o.base]:[...A2.O0]});
   const u=o.prog?Math.max(0,Math.min(1,o.prog())):Math.min(1,(performance.now()/1000-C.t0)/dur),q=up?u:1-u,F=rdV.n([at[0]-C.base[0],0,at[2]-C.base[2]]),gy=rdGround(C.base[0],C.base[2]);
   const rise=Math.min(1,q/0.85),lip=Math.max(0,(q-0.85)/0.15),toFace=(o.face??0.82)*(1-lip)+(o.top??1.15)*lip;   /* up the face, then over the lip onto the top */
   A2.O0=[C.base[0]+F[0]*toFace,gy+height*rise+(lip>0?0.02:0),C.base[2]+F[2]*toFace];
   const top=[C.base[0]+F[0]*(o.lip??0.55),gy+height,C.base[2]+F[2]*(o.lip??0.55)],L=d.limbs,B=rdBasis(d),hn=p=>L[p]?rdW(d,B,L[p].tip[0],L[p].tip[1],0.02):A2.O0;
   if(o.rope!==false){WK.lines.push([top,hn('armRl')]);WK.lines.push([hn('armRl'),rdV.add(A2.O0,[0,-0.08,0])]);   /* the rope: from the piton to its hand, down past it */
    const X=rdV.mul(F,-1),Y=[0,1,0],q0=rdQuat(X,Y,rdV.cross(X,Y));emit('load.piton','iron',top,q0,d.k);
    for(let k=1;k<4;k++){const y=gy+height*k/4;if(y<A2.O0[1]+0.3)emit('load.piton','iron',[top[0],y,top[2]],q0,d.k)}}   /* driven in as it climbs */
   if(u>=1&&!A2.stop){A2.stop=true;A2.opt.then=(d2)=>{t.g3dir=0;if(up&&!o.prog){t.x=Math.round(at[0]);t.y=Math.round(-at[2]);t.dx=t.x;t.dy=t.y;t.ly=height}d2.done=true;rdBack(t)}}}});
 if(A){A.climbing=true;wkShowBack(t)}return A}
// A climber is always seen from behind: turned to the face if that is its back picture, else the way most away from
// the eye (v3face picks the picture from the unit's way and the camera).
function wkShowBack(t){if(typeof v3face!=='function'||v3face(t)===1){t.g3dir=t.dir;return}const sy=Math.sin(V3.yaw||0),cy=Math.cos(V3.yaw||0);let best=1,bv=-9;
 for(const d of [1,2,4,8,5,6,9,10]){const fx=(d&4?1:0)-(d&8?1:0),fz=(d&2?1:0)-(d&1?1:0),v=(fx*-sy+fz*-cy)/Math.hypot(fx,fz);if(v>bv){bv=v;best=d}}
 t.dir=t.g3dir=best;const kd=V3.disp.get(t.key);if(kd&&kd.rc)kd.rc.ep=null}   /* g3dir: kept over the game's updates (game.js g3adopt) */
// Carrying: what is held, between the hands, in front of it (behind it, hidden, from its back).
function wkCard(P,d,lift){const C=WKSACK,eye=V3.eye||[0,10,10],D=rdV.n([eye[0]-P[0],0,eye[2]-P[2]]),R=rdV.n(rdV.cross([0,1,0],D)),s=d.k*1.3,hw=C.w/2*s,h=C.h*s,y0=P[1]-(lift||0)*h;
 WK.cards.push([C.tex,rdV.add([P[0],y0,P[2]],rdV.add(rdV.mul(R,-hw),rdV.mul(D,0.02))),rdV.add([P[0],y0,P[2]],rdV.add(rdV.mul(R,hw),rdV.mul(D,0.02))),h])}
// (called by ragdoll.js once it has cleared its pictures this frame)
function wkCards(){for(const [tex,a,b,h] of WK.cards){let va=RD.va.get(tex);if(!va){va=new VA();RD.va.set(tex,va)}quad(va,a,b,rdV.add(b,[0,h,0]),rdV.add(a,[0,h,0]),QN0,[1,1,1,1],[0,1,1,1,1,0,0,0])}WK.cards.length=0}
function wkLoad(d,emit,kind){const L=d.limbs,B=rdBasis(d),front=rdV.dot(B.Nn,rdV.sub(V3.eye||[0,10,10],d.O))>=0,n=(d.fl==='N'?-1:1)*(front?1:-1)*0.06;
 const hand=p=>L[p]?rdW(d,B,L[p].tip[0],L[p].tip[1],n):null,a=hand('armRl'),c=hand('armLl');if(!a&&!c)return null;const m=a&&c?rdV.mul(rdV.add(a,c),0.5):a||c;
 const t=d.t,dir=t.dir||2,Fw=rdV.n([((dir&4)?1:0)-((dir&8)?1:0),0,((dir&2)?1:0)-((dir&1)?1:0)]),across=rdV.n(rdV.cross([0,1,0],Fw));
 const X=kind==='log'?across:kind==='barrel'?[0,1,0]:across,Y=kind==='barrel'?Fw:[0,1,0],Z=rdV.cross(X,Y);
 if(kind==='sack'){const at=rdV.add(m,[0,-0.02,0]);wkCard(at,d,0.45);return at}   /* the pixel sack, held by its middle */
 const at=rdV.add(m,[0,kind==='log'?0.02:kind==='barrel'?-0.02:0.03,0]);emit('load.'+kind,'iron',at,rdQuat(X,Y,Z),d.k*(WKBIG[kind]||1));return at}
// t lifts a load lying on the ground in front of it (a sack, a barrel, a log, a stone, ore), then holds it, walking
// steps tiles ahead if asked; struck while carrying, it drops it.
function wkCarry(t,kind,steps){const bare=d=>{if(!d.wkBare){d.wkBare=true;skStow(d,true)}};   /* both hands on the load: its weapon and shield on its back */
 const hold=(d)=>skAct(t,'hold',null,{loop:true,doll:d,fx:(d2,dt,b,emit,A2)=>{bare(d2);WK.carry.set(t,{A:A2,d:d2,kind,at:wkLoad(d2,emit,kind)})}});
 const lift=skAct(t,'lift',null,{fx:(d,dt,b,emit)=>{bare(d);const C=WK.carry.get(t);if(C)C.d=d;if(b>0.45){if(C)C.at=wkLoad(d,emit,kind)}else wkGround(d,emit,kind)},
  then:(d)=>{if(!steps){hold(d);return}const dir=t.dir||2,Fw=rdV.n([((dir&4)?1:0)-((dir&8)?1:0),0,((dir&2)?1:0)-((dir&1)?1:0)]),until=steps/1.1;
   skAct(t,'carry',null,{loop:true,doll:d,walk:{dir:Fw,speed:1.1,until},fx:(d2,dt,b,emit,A2)=>{bare(d2);WK.carry.set(t,{A:A2,d:d2,kind,at:wkLoad(d2,emit,kind)});
     if(A2.walked>=until&&!A2.stop){A2.stop=true;t.x=Math.round(d2.O[0]);t.y=Math.round(-d2.O[2]);t.dx=t.x;t.dy=t.y;A2.opt.then=hold}}})}});
 WK.carry.set(t,{A:lift,kind});return lift}
function wkGround(d,emit,kind){const t=d.t,dir=t.dir||2,Fw=rdV.n([((dir&4)?1:0)-((dir&8)?1:0),0,((dir&2)?1:0)-((dir&1)?1:0)]),P=rdV.add([d.O[0],0,d.O[2]],rdV.mul(Fw,0.32));
 P[1]=rdGround(P[0],P[2]);if(kind==='sack'){wkCard(P,d,0);return}const big=WKBIG[kind]||1;P[1]+=(kind==='barrel'?6:3)*d.k*big;
 const X=kind==='barrel'?[0,1,0]:rdV.n(rdV.cross([0,1,0],Fw)),Y=kind==='barrel'?Fw:[0,1,0];emit('load.'+kind,'iron',P,rdQuat(X,Y,rdV.cross(X,Y)),d.k*big)}
// Struck or killed while carrying: the load drops and rolls.
function wkInterrupt(t,from){const C=WK.carry.get(t);if(!C)return;WK.carry.delete(t);for(const A of SK.acts)if(A.t===t){A.stop=true;A.opt.loop=false;A.opt.then=null;if(A.doll)A.doll.done=true}
 SK.acts=SK.acts.filter(A=>A.t!==t);if(!C.at)return;
 if(C.kind==='sack'){const P=[C.at[0]+(from?from[0]*0.15:0),0,C.at[2]+(from?from[2]*0.15:0)];P[1]=rdGround(P[0],P[2]);WK.dropped=(WK.dropped||[]).concat([{P,d:C.d}]);return}
 RD.loose.push({name:'load.'+C.kind,tier:'iron',s:((C.d&&C.d.k)||0.0156)*(WKBIG[C.kind]||1),c:[0,0,0],r:0.06,X:[...C.at],V:rdV.add(rdV.mul(from||[0,0,1],0.6),[0,0.8,0]),q:[0,0,0,1],w:[wkR(-4,4),wkR(-4,4),wkR(-4,4)],rest:false,flat:2,bounce:0})}
// A job going round: the unit works at a spot (at, in the world) till wkStop.
function wkStart(t,job,at,opt){if(job==='chop')job='woodchop';   /* felling: not the axe's fighting chop (skills.js) */if(!SK.defs[job])return null;return skAct(t,job,null,Object.assign({loop:true,at,fx:job==='fish'?wkFish:job==='spearfish'?wkSpear:job==='netfish'?wkNet:['pick','gather','plant','harvest'].includes(job)?wkForageFx:null},opt||{}))}
function wkStop(t){const C=WK.carry.get(t);if(C){wkInterrupt(t,[0,0,0]);const b=RD.loose[RD.loose.length-1];if(b&&C.at){b.V=[0,0.2,0];b.w=[0,0,0]}rdBack(t);return}   /* set down where it stands */
 for(const A of SK.acts)if(A.t===t)A.stop=true}
// Something to work at, for the arena (in the game: the real rock, tree, anvil): name 'rock', 'trunk', 'anvil'.
function wkProp(name,X,Z,turn,scale){const y=rdGround(X,Z);WK.props.push({name:'prop.'+name,P:[X,y,Z],q:rdQ.axis([0,1,0],turn||0),s:0.0156*(scale||1)})}
// Each frame: the props, the fishing lines (gathered this frame, drawn with the trails), the floats.
function wkDraw(emit){for(const p of WK.props)emit(p.name,'iron',p.P,p.q,p.s);for(const s of WK.dropped||[])if(s.d)wkCard(s.P,s.d,0)}
function wkLinesDraw(va){const eye=V3.eye||[0,10,10];for(const l of WK.lines){if(l.float){const P=l.float,R=rdV.n(rdV.cross([0,1,0],rdV.sub(eye,P))),r=0.018;
   quad(va,rdV.sub(P,rdV.mul(R,r)),rdV.add(P,rdV.mul(R,r)),rdV.add(rdV.add(P,rdV.mul(R,r)),[0,r*1.6,0]),rdV.add(rdV.sub(P,rdV.mul(R,r)),[0,r*1.6,0]),QN0,[0.85,0.15,0.1,1]);continue}
  const [a,b]=l,D=rdV.n(rdV.sub(eye,a)),S=rdV.mul(rdV.n(rdV.cross(rdV.sub(b,a),D)),0.0025);quad(va,rdV.sub(a,S),rdV.add(a,S),rdV.add(b,S),rdV.sub(b,S),QN0,[0.92,0.92,0.88,0.85])}
 WK.lines.length=0}
