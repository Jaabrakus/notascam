/* Deterministic exports from the armory's actual source artwork and body fits. */
(() => {
 const A=Armory,E=A.engine,canvas=(w,h)=>Object.assign(document.createElement('canvas'),{width:w,height:h});
 const ANGLES=[0,180,90,270],SLOTS=EquipmentEngine.SLOTS;
 const empty=()=>Object.fromEntries(SLOTS.map(slot=>[slot,{id:'',material:''}]));
 function state(bodyId,loadout,motion='idle'){return {bodyId,loadout,motion,angle:0,frame:0,fits:{},fitSlot:'weapon'};}
 const occupied=c=>!!EquipmentEngine.bounds(c,1);
 function assertInterior(c){const b=EquipmentEngine.bounds(c,1);if(b&&(b[0]===0||b[1]===0||b[2]===c.width||b[3]===c.height))throw Error('Sprite touches export boundary');}
 function asset(id,material){const item=E.items.get(id);if(!item||!item.materials.includes(material))throw Error('Unsupported item/material');let images=[],frames=[],sourceFrameCount=1;
  if(item.renderer==='gear16'){
   const count=item.poses.length,meta=item.poses,left=Math.ceil(Math.max(...meta.map(p=>p.ax)))+4,up=Math.ceil(Math.max(...meta.map(p=>p.ay)))+4;
   const w=Math.ceil(Math.max(64,left+Math.max(...meta.map(p=>p.w-p.ax))+4)/16)*16,h=Math.ceil(Math.max(64,up+Math.max(...meta.map(p=>p.h-p.ay))+4)/16)*16;
   const out=canvas(w*16,h*count),c=out.getContext('2d');c.imageSmoothingEnabled=false;
   for(let pose=0;pose<count;pose++){const g=E.gear(item,material,pose),m=g.meta,sw=g.image.width/16;for(let facing=0;facing<16;facing++){
    const tile=canvas(w,h),tc=tile.getContext('2d');tc.imageSmoothingEnabled=false;tc.drawImage(g.image,facing*sw,0,sw,g.image.height,left-m.ax,up-m.ay,m.w,m.h);assertInterior(tile);c.drawImage(tile,facing*w,pose*h);
    frames.push({angle:facing*22.5,pose,rect:[facing*w,pose*h,w,h],pivot:[left,up],visible:occupied(tile)});
   }}images.push({name:'equipment.png',png:out.toDataURL()});sourceFrameCount=count;
  }else if(item.renderer==='dmi'){
   const recipe=item.materialRecipes[material],layers=[...recipe.layers,...(recipe.armedLayers||[])];
   for(let layerIndex=0;layerIndex<layers.length;layerIndex++){
    const layer=layers[layerIndex],selected=layer.state?layer.states.find(s=>s.name===layer.state):layer.states.find(s=>s.name===''&&s.movement===1)||layer.states.find(s=>s.name==='')||layer.states[0];
    const count=selected.frames,out=canvas(256,count*64),c=out.getContext('2d');c.imageSmoothingEnabled=false;
    for(let frame=0;frame<count;frame++)for(let view=0;view<4;view++){
     const piece=E.dmi(layer,view,frame,selected.movement===1);c.drawImage(piece.image,0,0,64,64,view*64,frame*64,64,64);
     frames.push({layer:layerIndex,state:selected.name,sourceMovement:selected.movement,direction:A.catalog.directionOrder[view],frame,rect:[view*64,frame*64,64,64],origin:[0,0],visible:!!piece.box,delays:selected.delays});
    }images.push({name:'layer-'+String(layerIndex).padStart(2,'0')+'.png',png:out.toDataURL(),role:layerIndex<recipe.layers.length?'normal':'armed-replacement',source:layer.source,state:selected.name});sourceFrameCount=Math.max(sourceFrameCount,count);
   }
  }else{
   const out=canvas(512,128),c=out.getContext('2d'),rig={height:56},fit={anchor:[64,96],x:0,y:0,scale:1,stretch:1,rotation:0};c.imageSmoothingEnabled=false;
   for(let view=0;view<4;view++){c.save();c.translate(view*128,0);E.drawGoa(c,item,view,0,rig,fit,false);c.restore();frames.push({direction:A.catalog.directionOrder[view],frame:0,rect:[view*128,0,128,128],pivot:[64,96],adaptation:item.fitAdaptation});}
   images.push({name:'equipment.png',png:out.toDataURL()});
  }
  if(!images.some(i=>i.png))throw Error('No image export for '+id);
  return {images,manifest:{format:'banners.shared-equipment',version:1,id,material,slot:item.slot,renderer:item.renderer,sourceFrameCount,frames,bodySpace:[64,64],artStatus:'source-art export; fit and style require visual review',source:item.renderer==='gear16'?item.strips:item.materialRecipes[material],fitAdaptation:item.fitAdaptation||null}};
 }
 function drawLayer(c,item,material,b,view,frame,pose){const rig=E.rig(b.id,view,frame),s=state(b.id,empty(),'walk'),fit=E.fit(s,b,view,frame,item.slot,rig);
  if(item.renderer==='gear16')E.drawGear(c,item,material,pose,ANGLES[view],item.slot,rig,fit);
  else if(item.renderer==='goaHeld')E.drawGoa(c,item,view,frame,rig,fit,true);
  else E.drawArmor(c,item,material,view,frame,item.slot,rig,fit,true);
 }
 function fitted(id,material,bodyId){const item=E.items.get(id),b=E.bodies.get(bodyId),count=b.sourceRects.length,size=192,padding=64,out=canvas(size*4,size*count),layers=canvas(size*4,size*count),rects=[];
  const loadout=empty();loadout[item.slot]={id,material};const s=state(bodyId,loadout,'walk');
  for(let f=0;f<count;f++)for(let v=0;v<4;v++){
   const c=out.getContext('2d'),l=layers.getContext('2d');l.imageSmoothingEnabled=false;c.save();c.translate(v*size+padding,f*size+padding);E.render(c,s,{frame:f,angle:ANGLES[v]});c.restore();
   l.save();l.translate(v*size+padding,f*size+padding);drawLayer(l,item,material,b,v,f,0);l.restore();
   rects.push({direction:A.catalog.directionOrder[v],frame:f,rect:[v*size,f*size,size,size],bodyOrigin:[padding,padding],socket:E.rig(bodyId,v,f)[item.slot]});
  }assertInterior(out);assertInterior(layers);
  return {png:out.toDataURL(),layer:layers.toDataURL(),manifest:{bodyId,bodyStatus:b.status,id,material,frames:rects,animation:b.animation,frameSize:[size,size],bodySpace:[64,64],notes:['Only existing body animation frames are used.','Layer-only output is drawn with the indicated near/far depth when composed.']}};
 }
 function setPreview(bodyId,loadout){const b=E.bodies.get(bodyId),size=192,padding=64,count=b.sourceRects.length,out=canvas(size*4,size*count),s=state(bodyId,loadout,'walk');
  for(let f=0;f<count;f++)for(let v=0;v<4;v++){const c=out.getContext('2d');c.save();c.translate(v*size+padding,f*size+padding);E.render(c,s,{frame:f,angle:ANGLES[v]});c.restore();}assertInterior(out);return out.toDataURL();
 }
 function bodyFits(){return A.bodies.map(b=>({id:b.id,label:b.label,status:b.status,baseId:b.baseId,raceKey:b.raceKey,frameCount:b.sourceRects.length,animation:b.animation,
   frames:b.sourceRects.map((_,f)=>ANGLES.map((_,v)=>({direction:A.catalog.directionOrder[v],frame:f,rig:E.rig(b.id,v,f)}))),
   missingStates:['complete armed-walk/body attack coverage','injury and limb-loss coverage'],notes:b.status==='standing_only'?['Standing only; no walk frames generated by this batch.']:['Uses authored/generated frames already present in the body registry.']}));}
 window.GearBatch={asset,fitted,setPreview,bodyFits,empty};
})();
