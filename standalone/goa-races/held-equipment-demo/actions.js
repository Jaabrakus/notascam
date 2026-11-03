/* Family-specific body poses. Coordinates are in 64px body space. */
function createActions(engine,data){
 const forward=[[0,1],[0,-1],[1,0],[-1,0]];
 const hands={
  spear:[
   [{weapon:[28,41],support:[36,38]},{weapon:[36,39],support:[29,35]},{weapon:[27,40],support:[47,35]},{weapon:[38,40],support:[18,35]}],
   [{weapon:[28,42],support:[35,38]},{weapon:[36,40],support:[29,35]},{weapon:[25,40],support:[38,38]},{weapon:[39,40],support:[26,38]}],
   [{weapon:[29,44],support:[34,47]},{weapon:[35,34],support:[31,29]},{weapon:[37,37],support:[53,35]},{weapon:[27,37],support:[12,35]}]],
  bow:[
   [{weapon:[39,36],support:[25,32]},{weapon:[30,34],support:[35,27]},{weapon:[48,34],support:[29,38]},{weapon:[16,34],support:[35,38]}],
   [{weapon:[38,35],support:[26,29]},{weapon:[30,31],support:[35,26]},{weapon:[51,32],support:[23,29]},{weapon:[13,32],support:[41,29]}],
   [{weapon:[38,35],support:[24,29]},{weapon:[30,31],support:[35,26]},{weapon:[51,32],support:[23,29]},{weapon:[13,32],support:[41,29]}]],
  staff:[
   [{weapon:[20,33],support:[44,42]},{weapon:[44,33],support:[21,42]},{weapon:[28,40],support:[47,42]},{weapon:[44,33],support:[21,41]}],
   [{weapon:[20,33],support:[43,36]},{weapon:[44,33],support:[21,36]},{weapon:[22,33],support:[48,35]},{weapon:[44,33],support:[19,36]}],
   [{weapon:[20,33],support:[45,35]},{weapon:[44,33],support:[18,34]},{weapon:[23,34],support:[51,33]},{weapon:[44,33],support:[14,33]}]]
 };
 hands['one-hand-sweep']=data.sweepProfile.grips;
 hands['spear-jab']=data.jabProfile.grips;
 const cache=new Map();
 function raster(id,material,cell=6){const key=id+':'+material+':'+cell;if(cache.has(key))return cache.get(key);const g=engine.gear(engine.items.get(id),material,0),m={...g.meta},w=g.image.width/16;
  // The live game's G3GRIP correction seats the longsword hilt three art pixels higher.
  if(id==='weapon.longsword'||id==='weapon.rune sword')m.ay+=3;
  const image=document.createElement('canvas');image.width=w;image.height=g.image.height;const c=image.getContext('2d');c.drawImage(g.image,cell*w,0,w,g.image.height,0,0,w,g.image.height);
  const pix=c.getImageData(0,0,w,image.height).data;let distance=0,tip=[m.ax,m.ay-1];
  for(let y=0;y<image.height;y++)for(let x=0;x<w;x++)if(pix[(y*w+x)*4+3]>128){const d=(x-m.ax)**2+(y-m.ay)**2;if(d>distance){distance=d;tip=[x,y];}}
  const result={image,m,axis:Math.atan2(tip[1]-m.ay,tip[0]-m.ax)};cache.set(key,result);return result;
 }
 function drawItem(c,r,anchor,vector,scale,widthRatio=1,lengthRatio=1){c.save();c.translate(...anchor);c.rotate(Math.atan2(vector[1],vector[0]));c.scale(scale*lengthRatio,scale*widthRatio);c.rotate(-r.axis);c.drawImage(r.image,-r.m.ax,-r.m.ay);c.restore();}
 function draw(c,family,view,row,enabled,anchors,shieldEnabled=false,weaponID='weapon.spear'){const h=hands[family][row][view],body=document.createElement('canvas');body.width=body.height=64;const bc=body.getContext('2d');bc.drawImage(engine.images.get(data.actionSources[family]),view*64,row*64,64,64,0,0,64,64);
  const gear=()=>{if(!enabled)return;
   if(family==='spear'){const v=view<2?forward[view]:[h.support[0]-h.weapon[0],h.support[1]-h.weapon[1]];drawItem(c,raster('weapon.spear','iron'),h.weapon,v,.78);}
   if(family==='spear-jab'){
    const v=data.jabProfile.vectors[view],scale=data.jabProfile.scales[view];
    drawItem(c,raster('weapon.spear','iron',view===1?14:6),h.weapon,v,scale,data.jabProfile.shaftWidthRatio,data.jabProfile.lengthProjection[view]);
   }
   if(family==='one-hand-sweep'){
    // Only the anatomical right fist grips the spear. Left arm stays in guard.
    let v=data.sweepProfile.vectors[row][view];
    // A short far-hand weapon needs a raised silhouette outside the west-facing torso.
    if(view===3&&row===0&&weaponID!=='weapon.spear')v=[.4,-1];
    const scale=weaponID==='weapon.spear'?.82:weaponID==='weapon.warhammer'?.85:.95;
    drawItem(c,raster(weaponID,'iron',view===1?14:6),h.weapon,v,scale,weaponID==='weapon.spear'?.65:1);
   }
   if(family==='staff')drawItem(c,raster('weapon.crystal staff','silver'),h.weapon,view===2?[-.35,-1]:[0,-1],.85);
   if(family==='bow'){
    // Bow limb axis crosses the line of aim. The arrow follows the facing.
    const bow=raster('weapon.bow','wood');drawItem(c,bow,h.weapon,view<2?[1,0]:[0,-1],.8);
    const v=forward[view],offset=row===2?16:-10,arrow=engine.images.get(data.arrowSource);
    c.save();c.translate(h.weapon[0]+v[0]*offset,h.weapon[1]+v[1]*offset);c.rotate(Math.atan2(v[1],v[0]));if(view<2)c.scale(.45,1);c.drawImage(arrow,-arrow.width/2,-arrow.height/2);c.restore();
   }
  };
  const far=['one-hand-sweep','spear-jab'].includes(family)?(view===1||view===3):family==='bow'?(view===1||view===2):(view===1||view===3);
  const shield=()=>{if(!['one-hand-sweep','spear-jab'].includes(family)||!shieldEnabled)return;engine.drawGear(c,engine.items.get('shield.round'),'iron',0,(EquipmentEngine.angles[view]+135)%360,'shield',{height:56},{anchor:h.shield,x:[-2,2,-2,2][view],y:0,scale:1,stretch:1,rotation:0});};
  const farShield=view===1||view===2;
  if(far)gear();if(farShield)shield();c.drawImage(body,0,0);if(!far)gear();if(!farShield)shield();
  // Keep the side-facing head readable when the upright pole passes behind it.
  if(enabled&&family==='spear-jab'&&view===2&&data.jabProfile.vectors[view][1]<-.8)c.drawImage(body,0,0,64,31,0,0,64,31);
  if(enabled&&!far&&family!=='bow'){c.save();c.beginPath();c.arc(...h.weapon,family==='spear-jab'?2.4:2,0,Math.PI*2);c.clip();c.drawImage(body,0,0);c.restore();}
  if(anchors)for(const [name,point] of Object.entries(h)){c.strokeStyle=name==='weapon'?'#ffcb65':'#63eaca';c.lineWidth=.6;c.beginPath();c.arc(...point,2,0,Math.PI*2);c.stroke();}
  return {family,view,row,hands:h,forward:forward[view],weaponVector:family==='spear-jab'?data.jabProfile.vectors[view]:null};
 }
 function drawFlinch(c,view,row,weaponID,shieldEnabled,anchors){
  const h=data.flinchProfile.grips[row][view],bow=weaponID==='weapon.bow',staff=weaponID==='weapon.crystal staff',point=bow?h.shield:h.weapon;
  const body=document.createElement('canvas');body.width=body.height=64;const bc=body.getContext('2d');bc.drawImage(engine.images.get(data.flinchSource),view*64,row*64,64,64,0,0,64,64);
  const weapon=()=>{if(!weaponID)return;
   if(weaponID==='weapon.spear'){drawItem(c,raster(weaponID,'iron',view===1?14:6),point,data.jabProfile.vectors[view],data.jabProfile.scales[view],data.jabProfile.shaftWidthRatio,data.jabProfile.lengthProjection[view]);return;}
   let vector=staff?(view===2?[-.35,-1]:[0,-1]):bow?(view<2?[1,0]:[0,-1]):data.sweepProfile.vectors[0][view];
   if(!bow&&!staff&&view===3)vector=[.4,-1];
   drawItem(c,raster(weaponID,bow?'wood':staff?'silver':'iron',view===1?14:6),point,vector,weaponID==='weapon.warhammer'?.85:.95);
  };
  const shield=()=>{if(!shieldEnabled)return;engine.drawGear(c,engine.items.get('shield.round'),'iron',0,(EquipmentEngine.angles[view]+135)%360,'shield',{height:56},{anchor:h.shield,x:[-2,2,-2,2][view],y:0,scale:1,stretch:1,rotation:0});};
  const far=bow?(view===1||view===2):(view===1||view===3),farShield=view===1||view===2;
  if(far)weapon();if(farShield)shield();c.drawImage(body,0,0);if(!far)weapon();if(!farShield)shield();
  if(weaponID==='weapon.spear'&&view===2&&data.jabProfile.vectors[view][1]<-.8)c.drawImage(body,0,0,64,31,0,0,64,31);
  if(weaponID&&!far){c.save();c.beginPath();c.arc(...point,2.4,0,Math.PI*2);c.clip();c.drawImage(body,0,0);c.restore();}
  if(anchors)for(const p of [point,h.shield]){c.strokeStyle='#ffcb65';c.lineWidth=.6;c.beginPath();c.arc(...p,2,0,Math.PI*2);c.stroke();}
  return {view,row,action:'flinch',weapon:weaponID,hand:bow?'left':'right',grip:point};
 }
 return {draw,drawFlinch,hands,forward};
}
