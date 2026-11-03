/* GOA's drawn bare-hand frames, posed on the Human's own 64 px parts. Coordinates: GOA's 32 px frames doubled.
   R/L, r/l = the right and left arm and leg. The jab is the right hand and the cross the left in every facing, as GOA
   draws them (owner 11-01). West is East mirrored onto the West parts, the same hands. */
const POSES={
 'Rest':[{S:{},N:{},E:{},W:{}}],
 // Jab: the right hand.
 'PunchA-1':[
  {S:{off:[2,0],chest:[0,0],R:{h:[11,26]},L:{h:[43,39]},r:{a:[24,58]},l:{a:[40,58]}},N:{off:[2,0],R:{h:[50,25]},L:{h:[23,38]},r:{a:[40,58]},l:{a:[24,58]}},
   E:{chest:[-1,0],R:{e:[21,37],h:[22,30]},L:{h:[44,40]},r:{a:[41,57]},l:{a:[27,58]}},W:'mirror'},
  {S:{chest:[1,1],R:{e:[19,34],h:[26,35]},L:{h:[46,40]},r:{a:[24,58]},l:{a:[40,58]}},N:{chest:[-1,-1],R:{e:[45,32],h:[40,28]},L:{h:[17,40]},r:{a:[40,58]},l:{a:[24,58]}},
   E:{off:[1,0],chest:[2,0],lean:.06,R:{h:[53,30]},r:{a:[41,57]},l:{a:[27,58]}},W:'mirror'}],
 // Cross: the left hand.
 'PunchA-2':[
  {S:{off:[-2,0],R:{h:[20,40]},L:{h:[53,26]},r:{a:[24,58]},l:{a:[40,58]}},N:{off:[-2,0],R:{h:[44,39]},L:{h:[14,26]},r:{a:[40,58]},l:{a:[24,58]}},
   E:{chest:[-1,0],R:{h:[40,30]},L:{h:[38,37]},r:{a:[40,57]},l:{a:[27,58]}},W:'mirror'},
  {S:{chest:[-1,1],L:{e:[45,34],h:[38,35]},R:{h:[18,40]},r:{a:[24,58]},l:{a:[40,58]}},N:{chest:[1,-1],L:{e:[19,32],h:[24,28]},R:{h:[47,40]},r:{a:[40,58]},l:{a:[24,58]}},
   E:{off:[1,0],chest:[3,0],lean:.1,L:{h:[56,27]},R:{h:[20,34]},r:{a:[40,57]},l:{a:[26,58]}},W:'mirror'}],
 'KickA-1':[
  {S:{off:[1,0],R:{h:[24,36]},L:{h:[40,36]},r:{a:[21,51]},l:{a:[38,58]}},N:{off:[-1,0],R:{h:[41,36]},L:{h:[24,36]},r:{a:[39,51]},l:{a:[25,58]}},
   E:{off:[0,1],front:'r',R:{h:[37,33]},L:{h:[39,35]},r:{a:[41,50]},l:{a:[29,58]}},W:'mirror'},
  {S:{off:[3,0],lean:.15,front:'r',R:{h:[22,36]},L:{h:[47,36]},r:{a:[10,40],s:1.3},l:{a:[38,58]}},N:{off:[-2,0],chest:[0,1],R:{h:[47,36]},L:{h:[17,36]},r:{a:[38,44]},l:{a:[26,58]}},
   E:{off:[-2,-1],chest:[-1,0],lean:-.3,front:'r',R:{h:[30,35]},L:{h:[14,40]},r:{a:[52,33],s:1.35},l:{a:[31,58]}},W:'mirror'}],
 'KickA-2':[
  {S:{off:[-1,0],R:{h:[24,36]},L:{h:[40,36]},l:{a:[43,51]},r:{a:[26,58]}},N:{off:[1,0],R:{h:[41,36]},L:{h:[24,36]},l:{a:[23,51]},r:{a:[39,58]}},
   E:{off:[0,1],front:'r',R:{h:[36,33]},L:{h:[34,36]},r:{a:[40,52]},l:{a:[28,58]}},W:'mirror'},
  {S:{off:[-3,0],lean:-.15,front:'l',R:{h:[17,36]},L:{h:[42,36]},l:{a:[54,40],s:1.3},r:{a:[26,58]}},N:{off:[2,0],chest:[0,1],R:{h:[47,36]},L:{h:[17,36]},l:{a:[26,44]},r:{a:[38,58]}},
   E:{off:[-3,-1],chest:[-1,0],lean:-.38,front:'r',R:{h:[28,36]},L:{h:[12,38]},r:{a:[54,28],s:1.4},l:{a:[29,58]}},W:'mirror'}],
 // Run: leaning in with the head tilted along (an upright head showed the collar under the chin), both arms trailing
 // straight back; GOA's frames 0 and 2 stride, 1 and 3 pass.
 'Run':[
  {S:{off:[0,1],chest:[0,1],R:{h:[9,36]},L:{h:[55,36]},r:{a:[25,58]},l:{a:[38,52]}},N:{off:[0,1],chest:[0,-1],R:{h:[54,38]},L:{h:[10,38]},r:{a:[38,58]},l:{a:[25,52]}},
   E:{off:[1,2],lean:.25,chest:[1,0],head:.18,R:{h:[16,41]},L:{h:[18,39]},r:{a:[40,57]},l:{a:[27,57]}},W:'mirror'},
  {S:{off:[0,2],chest:[0,1],R:{h:[10,35]},L:{h:[54,35]},r:{a:[23,58]},l:{a:[40,57]}},N:{off:[0,2],chest:[0,-1],R:{h:[53,37]},L:{h:[11,37]},r:{a:[40,57]},l:{a:[23,58]}},
   E:{off:[1,1],lean:.25,chest:[1,0],head:.18,R:{h:[16,41]},L:{h:[18,39]},r:{a:[35,58]},l:{a:[29,53]}},W:'mirror'},
  {S:{off:[0,1],chest:[0,1],R:{h:[9,36]},L:{h:[55,36]},l:{a:[38,58]},r:{a:[26,52]}},N:{off:[0,1],chest:[0,-1],R:{h:[54,38]},L:{h:[10,38]},l:{a:[25,58]},r:{a:[38,52]}},
   E:{off:[1,2],lean:.25,chest:[1,0],head:.18,R:{h:[16,41]},L:{h:[18,39]},l:{a:[41,56]},r:{a:[25,57]}},W:'mirror'},
  {S:{off:[0,2],chest:[0,1],R:{h:[10,35]},L:{h:[54,35]},r:{a:[23,58]},l:{a:[40,57]}},N:{off:[0,2],chest:[0,-1],R:{h:[53,37]},L:{h:[11,37]},r:{a:[40,57]},l:{a:[23,58]}},
   E:{off:[1,1],lean:.25,chest:[1,0],head:.18,R:{h:[16,41]},L:{h:[18,39]},l:{a:[34,58]},r:{a:[30,53]}},W:'mirror'}],
};
const REFNAME={Rest:'Walk'};
