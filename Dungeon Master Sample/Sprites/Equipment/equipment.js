/* Shared equipment renderer. Coordinates are 64px body space; art is immutable. */
(() => {
 'use strict';
 const clamp=(v,a,b)=>Math.max(a,Math.min(b,v)), cv=(w,h)=>Object.assign(document.createElement('canvas'),{width:w,height:h});
 const cache=new Map(),frames=new Map(),palettes=new Map();
 const SLOTS=['weapon','shield','head','chest','arms','legs','feet'];
 const facing=angle=>[0,2,1,3][Math.floor((((angle%360)+360+45)%360)/90)];
 const angles=[0,180,90,270];
 function bounds(image,threshold=110){const c=image.getContext('2d'),p=c.getImageData(0,0,image.width,image.height).data;let x0=image.width,y0=image.height,x1=-1,y1=-1;for(let y=0;y<image.height;y++)for(let x=0;x<image.width;x++)if(p[(y*image.width+x)*4+3]>=threshold){x0=Math.min(x0,x);y0=Math.min(y0,y);x1=Math.max(x1,x);y1=Math.max(y1,y);}return x1<0?null:[x0,y0,x1+1,y1+1];}
 function rgbaColor(index,material,tier){const rampName=(index.use[tier]||index.use.iron)[material],r=index.ramps[rampName]||index.ramps.iron,shade=index.sh[material]||0,metal=index.met.includes(material),mix=(a,b,t)=>a.map((v,i)=>v+(b[i]-v)*t),k=shade+(metal?0:5);let b=k===0?mix(r[1],r[2],.75):k===1?mix(r[2],r[3],.5):r[clamp(2+shade,0,4)];if(metal&&shade<0)b=mix(r[1],r[2],.35);return b;}
 class Renderer {
  constructor(data){this.data=data;this.items=new Map(data.catalog.items.map(i=>[i.id,i]));this.bodies=new Map(data.bodies.map(b=>[b.id,b]));this.images=new Map();this.featureCache=new WeakMap();}
  async initialize(){await Promise.all(Object.entries(this.data.images).map(async([key,src])=>{const image=new Image();await new Promise((resolve,reject)=>{image.onload=resolve;image.onerror=()=>reject(Error('Cannot load '+key));image.src=src;});this.images.set(key,image);}));}
  bodyFrame(id,view,frame){const body=this.bodies.get(id);if(!body)throw Error('Unknown body '+id);frame=((frame%body.sourceRects.length)+body.sourceRects.length)%body.sourceRects.length;const key=id+':'+view+':'+frame;if(cache.has(key))return cache.get(key);
   const rect=body.sourceRects[frame][view],box=body.frameBounds[frame][view],all=body.frameBounds.flat().filter(Boolean),maxHeight=Math.max(...all.map(b=>b[3]-b[1])),scale=body.targetHeight/maxHeight;
   const output=cv(64,64),c=output.getContext('2d');c.imageSmoothingEnabled=false;
   // Fixed scale across every frame. Remove arbitrary sheet padding, align planted feet.
   const width=(box[2]-box[0])*scale,height=(box[3]-box[1])*scale;
   c.drawImage(this.images.get(body.source),rect[0]+box[0],rect[1]+box[1],box[2]-box[0],box[3]-box[1],32-width/2,61-height,width,height);
   const result={image:output,body,width,height,scale,box:bounds(output)};cache.set(key,result);return result;
  }
  rig(bodyId,view,frame){const bf=this.bodyFrame(bodyId,view,frame),h=bf.body.targetHeight,top=61-h,p=bf.image.getContext('2d').getImageData(0,0,64,64).data;
   function span(y0,y1){let lo=64,hi=0;for(let y=Math.max(0,Math.floor(y0));y<Math.min(64,Math.ceil(y1));y++)for(let x=0;x<64;x++)if(p[(y*64+x)*4+3]>=140){lo=Math.min(lo,x);hi=Math.max(hi,x);}return lo<hi?[lo,hi]:[23,41];}
   const chestY=top+h*.57,hipsY=top+h*.78,handY=top+h*.74,headY=top+h*.25;
   const torso=span(chestY-1,chestY+2),head=span(top+h*.26,top+h*.34),width=torso[1]-torso[0]+1;
   // Long ears/horns should not turn a small helmet into an oversized cap.
   const short=bf.body.raceKey==='Dwarves',maxHeadWidth=h*(short?.60:.52);
   const headWidth=Math.min(head[1]-head[0]+1,maxHeadWidth),torsoX=(torso[0]+torso[1])/2;
   let right=[torso[0]+2,handY],left=[torso[1]-2,handY];
   if(view===1)[right,left]=[left,right];
   if(view===2){right=[32,handY];left=[35,handY-3];}if(view===3){right=[32,handY-2];left=[29,handY];}
   // Follow actual outer hand pixels through each supplied walking frame.
   function hand(point){let best=null;for(let y=Math.max(0,Math.floor(point[1]-5));y<=Math.min(63,Math.ceil(point[1]+4));y++)for(let x=Math.max(0,Math.floor(point[0]-3));x<=Math.min(63,Math.ceil(point[0]+3));x++){const i=(y*64+x)*4;if(p[i+3]<150)continue;const distance=Math.abs(x-point[0])*.9+Math.abs(y-point[1]);if(!best||distance<best[0])best=[distance,x,y];}return best?[best[1],best[2]]:point;}
   return {weapon:hand(right),shield:hand(left),head:[(head[0]+head[1])/2,headY],chest:[torsoX,chestY],arms:[torsoX,chestY+1],legs:[torsoX,hipsY],feet:[torsoX,58],height:h,width,headWidth,torso,top};
  }
  fit(state,body,view,frame,slot,rig){const store=state.fits||{},base=store[body.baseId]?.[view]||{},own=store[body.id]?.[view]||{};
   const value={...(base.all?.[slot]||{}),...(base[frame]?.[slot]||{}),...(own.all?.[slot]||{}),...(own[frame]?.[slot]||{})};
   return {anchor:rig[slot],x:value.x||0,y:value.y||0,scale:value.scale??1,stretch:value.stretch??1,rotation:value.rotation||0,depth:value.depth||'auto'};
  }
  gear(item,material,pose){pose=Math.min(pose,item.poses.length-1);const key=item.id+':'+material+':'+pose;if(palettes.has(key))return palettes.get(key);
   const img=this.images.get(item.strips[pose]),out=cv(img.width,img.height),c=out.getContext('2d');c.drawImage(img,0,0);const pixels=c.getImageData(0,0,out.width,out.height),p=pixels.data,index=this.data.gear.index,bases=Array.from({length:32},(_,i)=>rgbaColor(index,i,material));
   for(let i=0;i<p.length;i+=4){if(!p[i+3])continue;const m=p[i];if(m<32){const b=bases[m],light=p[i+1]/100;p[i]=Math.min(255,b[0]*light);p[i+1]=Math.min(255,b[1]*light);p[i+2]=Math.min(255,b[2]*light);}else{const b=bases[p[i+1]&31],light=p[i+2]/100*.3;p[i]=Math.min(40,b[0]*light);p[i+1]=Math.min(40,b[1]*light);p[i+2]=Math.min(40,b[2]*light);}}
   c.putImageData(pixels,0,0);const result={image:out,meta:item.poses[pose]};palettes.set(key,result);return result;
  }
  dmi(layer,view,frame,moving){const state=layer.state?layer.states.find(s=>s.name===layer.state):layer.states.find(s=>s.name===''&&s.movement===(moving?1:0))||layer.states.find(s=>s.name==='')||layer.states[0];if(!state)throw Error('No state in '+layer.source);
   const index=state.offset+frame%state.frames*state.dirs+view%state.dirs,key=layer.source+':'+index;if(frames.has(key))return frames.get(key);
   const out=cv(layer.width,layer.height),c=out.getContext('2d');c.drawImage(this.images.get(layer.source),index%layer.columns*layer.width,Math.floor(index/layer.columns)*layer.height,layer.width,layer.height,0,0,layer.width,layer.height);const result={image:out,box:bounds(out)};frames.set(key,result);return result;
  }
  drawGear(c,item,material,pose,angle,slot,rig,fit){const g=this.gear(item,material,pose),cell=Math.round(angle/22.5)%16,sw=g.image.width/16,m=g.meta;
   let scale=rig.height/56*.85;if(slot==='head')scale=rig.headWidth/25;if(slot==='shield')scale=rig.height/56*.8;
   const view=facing(angle),longHeld=slot==='weapon'&&pose===0&&!/dagger|bow|hammer$/.test(item.id),holdingAngle=longHeld?(view===2?25:view===3?-25:0):0;
   scale*=fit.scale;c.save();c.translate(fit.anchor[0]+fit.x,fit.anchor[1]+fit.y);c.rotate((fit.rotation+holdingAngle)*Math.PI/180);c.scale(fit.stretch,1);c.drawImage(g.image,cell*sw,0,sw,g.image.height,-m.ax*scale,-m.ay*scale,m.w*scale,m.h*scale);c.restore();
  }
  drawArmor(c,item,material,view,frame,slot,rig,fit,moving){const recipe=item.materialRecipes[material];if(!recipe)throw Error('Unsupported material '+material+' for '+item.id);
   for(const layer of recipe.layers){const piece=this.dmi(layer,view,frame,moving);if(!piece.box)continue;const [x0,y0,x1,y1]=piece.box,sw=x1-x0,sh=y1-y0;let w,h,anchor=[...fit.anchor];
    if(slot==='chest'){const robe=item.id==='chest.robe';h=rig.height*(robe?.58:.29);w=rig.width*(view<2?.78:.74);if(robe)anchor[1]+=h*.19;}
    else if(slot==='legs'){w=rig.width*.69;h=rig.height*.22;}
    else if(slot==='feet'){w=rig.width*.73;h=rig.height*.12;}
    else {const left=/\.L$/.test(layer.state||''),point=left?rig.shield:rig.weapon;anchor=[point[0],point[1]-rig.height*.105];w=rig.width*(view<2?.24:.36);h=rig.height*.25;}
    // Keep shoulders separate and fitted, sharing torso origin, for the native GOA recipe.
    if(item.id==='goa.chest'){h=rig.height*.33;w=rig.width*.90;if(layer.source.includes('sholders')){h=rig.height*.20;anchor[1]-=rig.height*.06;}}
    c.save();c.translate(anchor[0]+fit.x,anchor[1]+fit.y);c.rotate(fit.rotation*Math.PI/180);c.scale(fit.scale*fit.stretch,fit.scale);c.drawImage(piece.image,x0,y0,sw,sh,-w/2,-h/2,w,h);c.restore();
   }
  }
  drawGoa(c,item,view,frame,rig,fit,moving){const sourceView=view===1?0:view===3?2:view,mirror=view===1||view===3;
   // Complete held views are reflected around the measured native grip.
   for(const layer of item.materialRecipes.original.layers){const piece=this.dmi(layer,sourceView,0,false);if(!piece.box)continue;const scale=rig.height/56*fit.scale,holdingAngle=view===0?-25:view===2?25:view===3?-25:25;
    c.save();c.translate(fit.anchor[0]+fit.x,fit.anchor[1]+fit.y);c.rotate((fit.rotation+holdingAngle)*Math.PI/180);c.scale((mirror?-1:1)*fit.stretch,1);c.drawImage(piece.image,-21*scale,-43*scale,64*scale,64*scale);c.restore();}}
  headFeatures(bf,rig){if(this.featureCache.has(bf.image))return this.featureCache.get(bf.image);
   const out=cv(64,64),c=out.getContext('2d'),data=bf.image.getContext('2d').getImageData(0,0,64,64),p=data.data;
   const horned=/(Marked|Ashen|Hellblooded)/i.test(bf.body.variant)||bf.body.raceKey==='Demon'||bf.body.raceKey==='DemonFly';
   for(let y=0;y<64;y++)for(let x=0;x<64;x++){const side=Math.abs(x-rig.head[0])>rig.headWidth*.39;
    const ear=side&&y<rig.top+rig.height*.38;
    const horn=horned&&y<rig.top+rig.height*.17&&Math.abs(x-rig.head[0])>rig.headWidth*.20;
    if(!ear&&!horn)p[(y*64+x)*4+3]=0;
   }c.putImageData(data,0,0);this.featureCache.set(bf.image,out);return out;
  }
  render(c,state,{bodyId=state.bodyId,angle=state.angle,frame=state.frame||0,pose=0,anchors=false,bare=false}={}){const body=this.bodies.get(bodyId),view=facing(angle),realFrame=body.status==='standing_only'?0:frame%body.sourceRects.length,bf=this.bodyFrame(bodyId,view,realFrame),rig=this.rig(bodyId,view,realFrame),fits={};
   c.imageSmoothingEnabled=false;
   const drawSlot=slot=>{if(bare)return;const selection=state.loadout[slot],item=selection?.id?this.items.get(selection.id):null;if(!item)return;if(!item.materials.includes(selection.material))throw Error('Unsupported selection '+item.id+'/'+selection.material);
    const fit=this.fit(state,body,view,realFrame,slot,rig);fits[slot]=fit;
    if(item.renderer==='gear16')this.drawGear(c,item,selection.material,slot==='weapon'?pose:0,angle,slot,rig,fit);
    else if(item.renderer==='goaHeld')this.drawGoa(c,item,view,realFrame,rig,fit,state.motion==='walk');
    else this.drawArmor(c,item,selection.material,view,realFrame,slot,rig,fit,state.motion==='walk');};
   const isFar=slot=>{const fit=this.fit(state,body,view,realFrame,slot,rig);if(fit.depth==='back')return true;if(fit.depth==='front')return false;return slot==='weapon'?(view===1||view===3):(view===1||view===2);};
   if(isFar('weapon'))drawSlot('weapon');if(isFar('shield'))drawSlot('shield');
   c.drawImage(bf.image,0,0);for(const slot of ['legs','feet','chest','arms'])drawSlot(slot);
   if(!isFar('weapon'))drawSlot('weapon');if(!isFar('shield'))drawSlot('shield');drawSlot('head');
   if(!bare&&state.loadout.head?.id)c.drawImage(this.headFeatures(bf,rig),0,0);
   // Foreground hand pixels cover the grip rather than leaving a blade over the fingers.
   if(!bare&&state.loadout.weapon?.id&&!isFar('weapon')){const fit=this.fit(state,body,view,realFrame,'weapon',rig),[x,y]=fit.anchor;c.save();c.beginPath();c.arc(x,y,1.6,0,Math.PI*2);c.clip();c.drawImage(bf.image,0,0);c.restore();}
   if(anchors)for(const slot of SLOTS){const fit=this.fit(state,body,view,realFrame,slot,rig);c.fillStyle=slot===state.fitSlot?'#ffe08a':'#62e8c6';c.beginPath();c.arc(fit.anchor[0]+fit.x,fit.anchor[1]+fit.y,.65,0,Math.PI*2);c.fill();}
   return {bodyId,bodyStatus:body.status,bodyFrame:realFrame,bodyView:view,gearCell:Math.round(angle/22.5)%16,pose,loadout:state.loadout,fit:fits,rig};
  }
 }
 globalThis.EquipmentEngine={Renderer,SLOTS,facing,angles,canvas:cv,bounds};
})();
