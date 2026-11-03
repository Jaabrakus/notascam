// Deaths that aren't a blow (art/gear3d; the animation arena): each of the game's other causes of death (its
// DeathType names, RDCAUSE below) acted out on the unit's own sprite, then a fall of its own, with its own effects:
// bleeding out sways and sinks in its own blood; poison retches and drools green; starving sways and sinks; cold
// shivers hugging itself, frosts over and topples stiff; fever wipes its brow and sweats; burning flails in flames and
// falls charred and smoking; lightning throws its arms out rigid, sparking, and topples; the heart clutches its chest;
// choking (vapours, the lungs) holds its throat; goo and holy energy melt it into a puddle; a skeleton rattles and
// drops into a heap of bones; old age sits down and lies down. The acting is a move (skills.js: keys, hands on the
// body), the fall a doll kind (ragdoll.js rdKind), the effects particles (rdPart), and the body's colour a tint.
const DZ={};
// the moves (hand spots in picture pixels from the neck: x out to the hand's own side, - across the body; y up)
Object.assign(SK.defs,{
 d_sway:{keys:[[0],[0.5,{lean:0.12,crouch:0.1}],[1.0,{lean:-0.1,crouch:0.2}],[1.5,{lean:0.15,crouch:0.35}],[1.9,{lean:0.08,crouch:0.45}]]},
 d_retch:{keys:[[0],[0.3,{Rhx:-1,Rhy:-10,lean:0.3,crouch:0.12,shake:0.03}],[0.7,{Rhx:-1,Rhy:-10,Lhx:-2,Lhy:2,lean:0.45,crouch:0.2,shake:0.05}],[1.1,{Rhx:-1,Rhy:-11,Lhx:-1,Lhy:2,lean:0.5,crouch:0.3,shake:0.07}],[1.6,{Rhx:-1,Rhy:-11,lean:0.45,crouch:0.35,shake:0.08}]]},
 d_choke:{keys:[[0],[0.25,{Rhx:-1,Rhy:-1.5,Lhx:-1,Lhy:-1.5,lean:-0.12,shake:0.04}],[0.9,{Rhx:-0.5,Rhy:-1,Lhx:-0.5,Lhy:-1,lean:0.2,crouch:0.15,shake:0.07}],[1.5,{Rhx:-0.5,Rhy:-1.5,Lhx:-0.5,Lhy:-1.5,lean:0.3,crouch:0.3,shake:0.05}]]},
 d_clutch:{keys:[[0],[0.15,{Rhx:-2,Rhy:-6,lean:0.1,shake:0.05}],[0.5,{Rhx:-2,Rhy:-6,Lhx:6,Lhy:-6,lean:0.25,crouch:0.15,lunge:0.15,shake:0.02}],[1.0,{Rhx:-2,Rhy:-7,Lhx:3,Lhy:-12,lean:0.35,crouch:0.4,lunge:0.1}]]},
 d_shiver:{keys:[[0],[0.3,{Rhx:-3,Rhy:-6,Lhx:-3,Lhy:-6.5,crouch:0.1,shake:0.03}],[1.4,{Rhx:-3.5,Rhy:-6,Lhx:-3.5,Lhy:-6.5,crouch:0.18,shake:0.045}],[1.9,{Rhx:-3.5,Rhy:-6,Lhx:-3.5,Lhy:-6.5,crouch:0.18,shake:0.0}]]},
 d_fever:{keys:[[0],[0.3,{Rhx:-1,Rhy:7,lean:-0.05,crouch:0.05}],[0.9,{Rhx:-1,Rhy:7,lean:0.12,crouch:0.15}],[1.4,{Rhx:0,Rhy:4,lean:-0.12,crouch:0.3}],[1.8,{lean:0.1,crouch:0.4}]]},
 d_flail:{keys:[[0],[0.15,{Rhx:5,Rhy:8,Lhx:7,Lhy:-2,lean:-0.2,lunge:0.1,shake:0.04}],[0.3,{Rhx:7,Rhy:-2,Lhx:5,Lhy:8,lean:0.15,lunge:-0.08,shake:0.04}],[0.45,{Rhx:5,Rhy:8,Lhx:7,Lhy:-2,lean:-0.15,lunge:0.12,shake:0.04}],
  [0.6,{Rhx:7,Rhy:-2,Lhx:5,Lhy:8,lean:0.2,lunge:-0.05,shake:0.04}],[0.75,{Rhx:5,Rhy:8,Lhx:7,Lhy:-2,lean:-0.1,lunge:0.15,shake:0.04}],[0.9,{Rhx:7,Rhy:-2,Lhx:5,Lhy:8,lean:0.2,lunge:0.0,shake:0.04}],
  [1.05,{Rhx:5,Rhy:8,Lhx:7,Lhy:-2,lean:-0.15,lunge:0.12,shake:0.04}],[1.2,{Rhx:7,Rhy:-2,Lhx:5,Lhy:8,lean:0.25,lunge:0.05,crouch:0.15,shake:0.04}],[1.5,{Rhx:6,Rhy:2,Lhx:6,Lhy:2,lean:0.3,crouch:0.3,shake:0.06}]]},
 d_jolt:{keys:[[0],[0.05,{Rhx:8,Rhy:2,Lhx:8,Lhy:2,shake:0.12,lean:-0.12}],[0.55,{Rhx:8,Rhy:3,Lhx:8,Lhy:3,shake:0.12,lean:-0.12}],[0.7,{Rhx:7,Rhy:1,Lhx:7,Lhy:1,lean:-0.08}]]},
 d_twitch:{keys:[[0],[0.2,{shake:0.06,lean:0.05}],[0.7,{shake:0.09,crouch:0.15}],[1.0,{shake:0.04,crouch:0.25}]]},
 d_rattle:{keys:[[0],[0.2,{shake:0.08,crouch:0.05}],[0.8,{shake:0.1,crouch:0.1}]]},
 d_melt:{keys:[[0],[0.4,{Rhx:4,Rhy:-2,Lhx:4,Lhy:-2,shake:0.03,crouch:0.1}],[1.0,{Rhx:5,Rhy:0,Lhx:5,Lhy:0,shake:0.04,crouch:0.2}]]},
 d_sit:{keys:[[0],[0.8,{crouch:0.35,lean:0.1,Rhx:1,Rhy:-12,Lhx:1,Lhy:-12}],[1.6,{crouch:0.55,lean:0.15,Rhx:1,Rhy:-14,Lhx:1,Lhy:-14}]]},
 d_stone:{keys:[[0],[0.3,{shake:0.06,crouch:0.04}],[0.9,{shake:0.03,crouch:0.06,lean:0.04}],[1.4,{shake:0,crouch:0.06,lean:0.04}]]},
});
// the game's causes (its DeathType) to these deaths
const RDCAUSE={'Bleeding To Death':'bleed','Poison':'poison','Food Poisoning':'poison','eating it like a moron.':'poison','Starvation':'starve','Tiredness':'starve',
 'Coldness':'cold','Fever':'fever','Overheating':'fever','Burned To Death':'burn','Being Burned':'burn','lightning':'lightning','Heart Failure':'heart',
 'Massive Heart Attack':'heart','Punctured Heart':'heart','Lung Failure':'choke','Brain Damage':'brain','Melting Into Goo':'goo','being slowly melted by holy energy':'holy',
 'Crumbled into Bonemeal':'crumble','old age':'oldage','vapours':'choke','Turned To Stone':'stone'};

// A point on the doll, in picture pixels from its neck (x right in the picture, y up), lifted toward the eye by n.
function dzAt(d,dx,dy,n=0.02){const L=d.limbs.head,B=rdBasis(d),nk=L?rdRootNow(d,L):[d.pel[0],d.pel[1]+0.4];const front=rdV.dot(B.Nn,rdV.sub(V3.eye||[0,10,10],d.O))>=0?1:-1;
 return rdW(d,B,nk[0]+dx*d.k,nk[1]+dy*d.k,n*front)}
const dzR=(a,b)=>a+Math.random()*(b-a),dzBody=d=>dzAt(d,dzR(-5,5),dzR(-17,6),0.03);
// how many to start this frame at a rate a second, carried between frames
function dzN(d,key,rate,dt){d.dzAcc=d.dzAcc||{};const v=(d.dzAcc[key]||0)+rate*dt,n=Math.floor(v);d.dzAcc[key]=v-n;return n}
const dzLerp=(a,b,k)=>a.map((v,i)=>v+(b[i]-v)*k);
const GREEN=[0.45,0.75,0.2,0.9],GOO=[0.32,0.6,0.14];

// Each death: the move it acts out, the fall, the tint it ends in, its effects while acting (fx) and after (after).
const DZDEF={
 bleed:{act:'d_sway',fall:'crumple',tint:[0.92,0.86,0.86],fx(d,dt){for(let i=dzN(d,'b',5,dt);i>0;i--)rdBlood(dzBody(d),[0,-0.3,0],1,false)},
  after(d,dt,age){if(age<1.5&&dzN(d,'p',4,dt))rdPart(rdV.add(d.O,[dzR(-0.12,0.12),0.02,dzR(-0.12,0.12)]),[0,-1,0],0.5,0.03,0.03,[0.45,0.04,0.03,0.9],[0.45,0.04,0.03,0.9],6,0,[0.4,0.03,0.02])}},
 poison:{act:'d_retch',fall:'crumple',tint:[0.8,1.0,0.72],fx(d,dt,b){for(let i=dzN(d,'d',4,dt);i>0;i--)rdPart(dzAt(d,dzR(-1,1),2),[dzR(-0.05,0.05),-0.1,dzR(-0.05,0.05)],1.4,0.012,0.01,GREEN,GREEN,6,0,[0.3,0.5,0.12]);if(dzN(d,'pp',3,dt))rdPx(dzAt(d,dzR(-4,4),dzR(0,6)),[0,0.08,0],1.0,0.035,0.05,'poison',-0.05,1);
   if(b>1.05&&!d.dzSpew){d.dzSpew=true;const F=rdV.mul(d.R,d.fl==='W'?-1:1);for(let i=0;i<14;i++)rdPart(dzAt(d,0,2),rdV.add(rdV.mul(F,dzR(0.3,0.9)),[dzR(-0.3,0.3),dzR(0,0.5),dzR(-0.3,0.3)]),1.2,0.016,0.012,GREEN,GREEN,6,0,[0.3,0.5,0.12])}}},
 starve:{act:'d_sway',fall:'crumple',tint:[0.9,0.88,0.84]},
 cold:{act:'d_shiver',fall:'stiff',tint:[0.72,0.86,1.22],fx(d,dt){for(let i=dzN(d,'f',6,dt);i>0;i--){const P=rdV.add(dzBody(d),[dzR(-0.08,0.08),0,dzR(-0.08,0.08)]);rdPx(P,[0,-0.04,0],1.2,0.035,0.02,'frost',0.1,0.5)}
   if(dzN(d,'br',1.6,dt))rdPart(dzAt(d,0,3),[dzR(-0.05,0.05),0.08,dzR(-0.05,0.05)],1.0,0.015,0.05,[0.95,0.97,1,0.45],[0.95,0.97,1,0],-0.05,1)},
  after(d,dt,age){if(d.landed&&!d.dzIce){d.dzIce=true;rdSparks(d.O,14,[0.85,0.95,1])}if(age<3)for(let i=dzN(d,'f',3,dt);i>0;i--)rdPx(dzBody(d),[0,-0.03,0],1.2,0.035,0.02,'frost',0.1,0.5)}},
 fever:{act:'d_fever',fall:'crumple',tint:[1.1,0.84,0.8],fx(d,dt,b){d.tint=[1+0.12*Math.abs(Math.sin(b*5)),0.86,0.82];for(let i=dzN(d,'s',5,dt);i>0;i--)rdPart(dzAt(d,dzR(-4,4),dzR(5,9)),[dzR(-0.15,0.15),0.15,dzR(-0.15,0.15)],0.8,0.008,0.006,[0.75,0.88,1,0.9],[0.75,0.88,1,0.6],6)}},
 burn:{act:'d_flail',fall:'fall',tint:[0.3,0.25,0.22],fx(d,dt,b){dzFire(d,dt,45,8)},after(d,dt,age){if(age<2.5)dzFire(d,dt,30*(1-age/2.5),6);else if(age<6)dzSmoke(d,dt,4)}},
 lightning:{act:'d_jolt',fall:'stiff',tint:[0.36,0.33,0.33],fx(d,dt,b){if(!d.dzFlash){d.dzFlash=true;rdSparks(dzAt(d,0,10),30,[0.85,0.92,1]);rdPart(dzAt(d,0,-4),[0,0,0],0.18,0.25,0.4,[0.9,0.95,1,0.9],[0.8,0.9,1,0])}
   d.tint=b<0.12?[1.8,1.8,2]:null;if(dzN(d,'s',30,dt))rdSparks(dzBody(d),2,[0.8,0.9,1]);for(let i=dzN(d,'sp',14,dt);i>0;i--)rdPx(dzBody(d),[0,0,0],0.25,0.06,0.03,'spark')},after(d,dt,age){if(age<4)dzSmoke(d,dt,5)}},
 heart:{act:'d_clutch',fall:'fall'},
 choke:{act:'d_choke',fall:'crumple',tint:[0.86,0.86,0.94],fx(d,dt){if(dzN(d,'c',2.5,dt))for(let i=0;i<2;i++)rdPx(dzAt(d,dzR(-1,1),2),[dzR(-0.1,0.1),dzR(0.05,0.2),dzR(-0.1,0.1)],1.0,0.03,0.07,'plague',-0.1,1)}},
 brain:{act:'d_twitch',fall:'crumple'},
 goo:{act:'d_melt',fall:'melt',tint:[0.72,1.05,0.58],fx(d,dt){for(let i=dzN(d,'g',6,dt);i>0;i--)rdPart(dzBody(d),[0,-0.2,0],1,0.014,0.012,[0.4,0.7,0.18,0.95],[0.4,0.7,0.18,0.95],6,0,GOO)},after(d,dt,age){if(age<3){dzPuddle(d,dt,GOO,0.5);if(dzN(d,'ac',6,dt))rdPx(rdV.add(d.O,[dzR(-0.2,0.2),0.04,dzR(-0.2,0.2)]),[0,0.1,0],0.8,0.03,0.04,'acid',0,1)}}},
 holy:{act:'d_melt',fall:'melt',tint:[1.45,1.35,1.1],fx(d,dt,b){d.tint=dzLerp([1,1,1],[1.45,1.35,1.1],Math.min(1,b));for(let i=dzN(d,'h',8,dt);i>0;i--)rdPx(dzBody(d),[dzR(-0.03,0.03),dzR(0.2,0.35),dzR(-0.03,0.03)],1.2,0.04,0.025,'holy',-0.1,0.3)},
  after(d,dt,age){if(age<3){dzPuddle(d,dt,[0.85,0.82,0.7],0.45);for(let i=dzN(d,'h',5,dt);i>0;i--)rdPx(rdV.add(d.O,[dzR(-0.15,0.15),0.05,dzR(-0.15,0.15)]),[0,0.3,0],1.2,0.04,0.025,'holy',-0.1,0.3)}}},
 stone:{act:'d_stone',fall:'pose',tint:[0.62,0.6,0.58],fx(d,dt){for(let i=dzN(d,'st',7,dt);i>0;i--)rdPx(dzBody(d),[dzR(-0.03,0.03),dzR(0.05,0.15),dzR(-0.03,0.03)],0.9,0.035,0.06,'dust',0.05,0.6)},after(d,dt,age){if(age<0.1&&!d.dzDust){d.dzDust=true;rdDust(d.O,12)}}},   /* turned to stone (a guest who left, Guests.dm): it stiffens and greys where it stands, in a breath of stone dust, and stays standing */
 crumble:{act:'d_rattle',fall:'heap',tint:[0.95,0.93,0.86],after(d,dt,age){if(age<0.1&&!d.dzDust){d.dzDust=true;rdDust(d.O,10);for(let i=0;i<10;i++)rdPx(rdV.add(d.O,[dzR(-0.2,0.2),dzR(0.02,0.15),dzR(-0.2,0.2)]),[dzR(-0.2,0.2),dzR(0.1,0.3),dzR(-0.2,0.2)],1.0,0.05,0.08,'dust',0,1.5)}}},
 oldage:{act:'d_sit',fall:'liedown'},
};
function dzFire(d,dt,flames,smoke){for(let i=dzN(d,'fl',flames*0.45,dt);i>0;i--)rdPx(dzBody(d),[dzR(-0.06,0.06),dzR(0.35,0.6),dzR(-0.06,0.06)],dzR(0.45,0.7),0.07,0.045,'fire',-0.2,1.2);   /* the game's own fire pixels */
 for(let i=dzN(d,'em',flames*0.15,dt);i>0;i--)rdPart(dzBody(d),[dzR(-0.1,0.1),dzR(0.5,0.9),dzR(-0.1,0.1)],dzR(0.6,1.0),0.008,0.004,[1,0.75,0.3,1],[1,0.3,0.05,0],-0.1,0.5);dzSmoke(d,dt,smoke)}
function dzSmoke(d,dt,n){for(let i=dzN(d,'sm',n,dt);i>0;i--)rdPart(rdV.add(dzBody(d),[0,0.05,0]),[dzR(-0.08,0.08),0.35,dzR(-0.08,0.08)],1.6,0.03,0.12,[0.3,0.28,0.26,0.55],[0.35,0.34,0.33,0],-0.05,0.8)}
function dzPuddle(d,dt,col,r){for(let i=dzN(d,'pu',10,dt);i>0;i--){const a=Math.random()*6.283,q=Math.sqrt(Math.random())*r*Math.min(1,(d.age||0)+0.3);rdPart(rdV.add(d.O,[Math.cos(a)*q,0.01,Math.sin(a)*q]),[0,-1,0],0.3,0.035,0.035,[...col,0.9],[...col,0.9],8,0,col)}}

// The unit dies of cause (the game's DeathType, or one of DZDEF's names): it acts it out, then falls; from: the way it
// falls (away from that), else to a side.
function rdDie(t,cause,from){const key=DZDEF[cause]?cause:RDCAUSE[cause]||'starve',Z=DZDEF[key];if(!t||!t.g3last)return null;
 from=from||(()=>{const a=Math.random()*6.283;return [Math.cos(a),0,Math.sin(a)]})();
 const tint0=[1,1,1],A=skAct(t,Z.act,null,{death:true,fx(d,dt,b){if(Z.tint&&!['fever','lightning','holy'].includes(key))d.tint=dzLerp(tint0,Z.tint,Math.min(1,b/1.4));if(Z.fx)Z.fx(d,dt,b)},
  then(d){d.alive=false;rdKind(d,Z.fall,from);if(Z.tint)d.tint=Z.tint;d.onStep=Z.after||null;if(t.bleed)t.bleed.on=false;t.dead=true}});
 return A}
