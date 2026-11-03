/* Standing equipment workshop. Approved Deepguard geometry stays immutable. */
(() => {
 const D=WORN_DATA,cv=(w,h)=>Object.assign(document.createElement('canvas'),{width:w,height:h});
 const pictures=new Map(),pixels=new Map(),eyeCache=new Map(),headCache=new Map(),smallCache=new Map();
 const dirs=['South','North','East','West'];
 async function init(){await Promise.all(Object.entries(D.images).map(async([key,url])=>{const img=new Image();await new Promise((yes,no)=>{img.onload=yes;img.onerror=no;img.src=url;});pictures.set(key,img);}));}
 function partImage(set,part,view){return pictures.get(set.id+':'+part+':'+view);}
 function imagePixels(img){if(pixels.has(img))return pixels.get(img);const out=cv(img.width,img.height),c=out.getContext('2d');c.drawImage(img,0,0);const p=c.getImageData(0,0,out.width,out.height).data;pixels.set(img,p);return p;}
 function eyes(bodyId,view,r){const key=bodyId+':'+view;if(eyeCache.has(key))return eyeCache.get(key);const out=[],p=imagePixels(pictures.get('body:'+key));
  if(view!==1)for(let y=Math.max(0,Math.floor(r.top+r.height*.17));y<Math.min(64,r.top+r.height*.38);y++)for(let x=Math.max(0,Math.floor(r.head[0]-r.headWidth*.4));x<Math.min(64,r.head[0]+r.headWidth*.4);x++){
   const i=(y*64+x)*4,[a,b,c,alpha]=p.slice(i,i+4);if(alpha<140)continue;
   const match=['orc','dark-elf'].includes(bodyId)?a>180&&b<90&&c<100:['goblin','kobold'].includes(bodyId)?a>185&&b>170&&c<130:Math.min(a,b,c)>225||(bodyId==='elf'&&c>180&&a<120&&b<210);
   if(match)out.push([x+.5,y+.5]);
  }eyeCache.set(key,out);return out;
 }
 function transform(rect,r,view){const sx=r.width/D.masterWidths[view],sy=r.height/56;return[32+(rect[0]-32)*sx,61+(rect[1]-61)*sy,rect[2]*sx,rect[3]*sy];}
 const limbSide=(part,view)=>part.includes('left')?(view===0?1:view===1?-1:0):(view===0?-1:view===1?1:0);
 function semantic(set,part){if(['kobold-dragonhide','kobold-dragon'].includes(set.id)&&part==='shoulder-one')return'back-mantle';if(set.id==='dark-elf-spidersilk'){if(part==='helmet')return'brow-piece';if(part==='chest')return'longcoat';if(part==='shoulder-one')return'half-cape-left';}if(set.id==='dwarf-leather'&&part==='belt')return'belt-hip-panels';return part;}
 function isHead(part){return ['helmet','brow-piece','hood-mantle'].includes(part);}
 function canonical(part,view,set){const front=view<2,right=part.includes('right'),s=limbSide(part,view);
  if(part==='helmet')return[20.5,-1,23,23];
  if(part==='brow-piece')return[20,7,24,16];
  if(part==='hood-mantle')return[14,-3,36,38];
  if(part==='back-mantle'||part.startsWith('half-cape'))return[19,27,26,23];
  if(part==='longcoat'||part==='chest-apron'||(set.id==='elf-leather'&&part==='chest-wrap'))return front?[22,27,20,23]:[25,27,15,23];
  if(part.startsWith('chest'))return front?[23,28,18,12]:view===2?[29,28,12,12]:[23,28,12,12];
  if(part.includes('harness')||part.startsWith('strap-'))return front?[21,27,22,15]:[24,27,16,15];
  if(part==='shoulder-one'){const rt=['dwarf-gold','orc-dragonbone','elf-wood'].includes(set.id);const cx=front?((view===0)===rt?21.5:42.5):32;return[cx-5.5,27,11,13];}
  if(part.startsWith('shoulder-')){const cx=front?32+s*10.5:(right?(view===2?28:34):(view===2?34:35));return[cx-4,28,8,9];}
  if(part.includes('bracer')||part.includes('gauntlet')){const cx=front?32+s*12:(right?(view===2?28:34):(view===2?34:36)),long=part.includes('gauntlet');return[cx-3,long?35:37,6,long?7:5];}
  if(part==='belt')return front?[23,39,18,3]:[25,39,14,4];
  if(part.includes('hip-panels'))return[22,part==='hip-panels'?42:39,21,part==='hip-panels'?8:11];
  const cx=front?32+s*5.5:(right?35:28);
  if(part.startsWith('lower-leg'))return[cx-4.5,50,9,11];
  if(part.startsWith('greave-'))return[cx-4.5,50,9,5];
  if(part.startsWith('boot-'))return[cx-5,55,10,6];
  throw Error('Unknown fitted part '+part);
 }
 function box(part,r,view,set){let rect=canonical(part,view,set);if(part==='helmet'&&/dragonhide|dragonbone|kobold-dragon$/.test(set.id))rect=[16,-7,32,34];return transform(rect,r,view);}
 function fitHead(image,rect,points,bodyId,view,key){if(!points.length)return rect;const cacheKey=key+':'+bodyId+':'+view;if(headCache.has(cacheKey))return headCache.get(cacheKey);const p=imagePixels(image);let best=rect,score=Infinity;
  for(let dy=-5;dy<=2;dy++)for(const dx of [-1,0,1]){const test=[rect[0]+dx,rect[1]+dy,rect[2],rect[3]];let occluded=0;for(const [x,y]of points){const u=Math.floor((x-test[0])/test[2]*image.width),v=Math.floor((y-test[1])/test[3]*image.height);if(u>=0&&v>=0&&u<image.width&&v<image.height)occluded+=p[(v*image.width+u)*4+3]/255;}const cost=occluded*20/points.length+dy*dy*.045+dx*dx*.12;if(cost<score){score=cost;best=test;}}
  headCache.set(cacheKey,best);return best;
 }
 function drawSmall(ctx,image,rect,raw=false){if(raw){ctx.drawImage(image,...rect);return;}const w=Math.max(1,Math.round(rect[2])),h=Math.max(1,Math.round(rect[3]));let sizes=smallCache.get(image);if(!sizes){sizes=new Map();smallCache.set(image,sizes);}const key=w+':'+h;let tile=sizes.get(key);
  if(!tile){tile=cv(w,h);const c=tile.getContext('2d');c.imageSmoothingEnabled=true;c.imageSmoothingQuality='high';c.drawImage(image,0,0,w,h);sizes.set(key,tile);}ctx.drawImage(tile,Math.round(rect[0]),Math.round(rect[1]));
 }
 function selection(value){if(!value||value==='none')return null;const [setId,part]=value.split('::');const set=D.catalog.sheets.find(s=>s.id===setId);return set?{set,part}:null;}
 function render(bodyId,setId,{bare=false,helmet='',chest='',weapon='',shield=''}={}){
  const b=D.bodies.find(b=>b.id===bodyId),set=D.catalog.sheets.find(s=>s.id===setId);if(!b||!set)throw Error('Unknown fit selection');
  const out=cv(512,128),c=out.getContext('2d'),layers={},placements=[];c.imageSmoothingEnabled=false;
  const headChoice=selection(helmet),torsoChoice=selection(chest),wp=selection(weapon),sh=selection(shield),robe=torsoChoice?.part.startsWith('robe.'),hoodedRobe=robe&&/\.(blue|green|dragonrobe)$/.test(torsoChoice.part);
  for(let view=0;view<4;view++){
   c.save();c.translate(view*128+32,32);const r=b.views[view].rig,eyePoints=eyes(bodyId,view,r);
   const draw=(owner,part,rect,raw=false,role='armor')=>{const image=partImage(owner,part,view);if(!image)return;if(!layers[part])layers[part]=cv(512,128);const l=layers[part].getContext('2d');l.imageSmoothingEnabled=false;l.save();l.translate(view*128+32,32);drawSmall(l,image,rect,raw);l.restore();drawSmall(c,image,rect,raw);placements.push({part,source:owner.id,direction:dirs[view],rect,role});};
   const drawPart=part=>{const image=partImage(set,part,view);if(!image)return;let rect=set.registeredMaster?transform([0,0,64,64],r,view):box(semantic(set,part),r,view,set);if(!set.registeredMaster&&isHead(part)&&!part.includes('hood'))rect=fitHead(image,rect,eyePoints,bodyId,view,set.id+':'+part);draw(set,part,rect,!!set.registeredMaster);};
   const held=(choice,slot)=>{if(!choice)return;const {set:owner,part}=choice,image=partImage(owner,part,view);if(!image)return;const anchor=r[slot];let pivot=[.5,.82],h=r.height*.74;
    if(slot==='shield'){h=r.height*({buckler:.3,round:.50,heater:.55,kite:.68,tower:.85}[part.split('.')[1]]||.5);pivot=[.5,.5];}
    else if(/staff|spear|harpoon|whisker/.test(part)){h=r.height*1.06;pivot=[.5,.74];}
    else if(/bow$/.test(part)){h=r.height*.76;pivot=[view===0?.72:view===1?.30:.5,.5];}
    else if(/dagger/.test(part))h=r.height*.43;
    else if(/hand axe|hammer$|mace$|morning star/.test(part))h=r.height*.56;
    else if(/longsword|battle axe|soul eater/.test(part))h=r.height*.90;
    else if(/spade/.test(part)){h=r.height*.85;pivot=[.5,.50];}
    else if(/fishing rod/.test(part)){h=r.height;pivot=[view===0?.25:view===1?.75:.5,.85];}
    h=Math.min(h,(62-anchor[1])/(1-pivot[1]));const w=h*image.width/image.height,rotation=slot==='weapon'?(view===0?-12:view===1?12:view===2?22:-22):0;
    c.save();c.translate(...anchor);c.rotate(rotation*Math.PI/180);drawSmall(c,image,[-w*pivot[0],-h*pivot[1],w,h]);c.restore();placements.push({part,source:owner.id,direction:dirs[view],role:slot,anchor,pivot,rotation,size:[w,h]});
   };
   const farWeapon=view===1||view===3,farShield=view===1||view===2;
   if(!bare&&farWeapon)held(wp,'weapon');if(!bare&&farShield)held(sh,'shield');
   const back=set.parts.filter(p=>['back-mantle','half-cape-left'].includes(semantic(set,p))),farArms=!set.registeredMaster?set.parts.filter(p=>(view===2&&p.includes('left')&&/shoulder|bracer|gauntlet/.test(p))||(view===3&&p.includes('right')&&/shoulder|bracer|gauntlet/.test(p))):[];
   if(!bare&&view!==1)back.forEach(drawPart);if(!bare&&!robe)farArms.forEach(drawPart);c.drawImage(pictures.get('body:'+bodyId+':'+view),0,0);
   if(!bare){const rank=p=>/lower-leg|boot|greave/.test(p)?0:/chest|longcoat/.test(p)?1:/hip-panels|belt|waist/.test(p)?2:/harness|strap|shoulder/.test(p)?3:/bracer|gauntlet/.test(p)?4:5;
    let visible=set.parts.filter(p=>!back.includes(p)&&!farArms.includes(p));if(helmet||hoodedRobe)visible=visible.filter(p=>!isHead(p));if(torsoChoice)visible=visible.filter(p=>!/chest|longcoat/.test(p));if(robe)visible=visible.filter(p=>!/hip-panels|belt|waist|harness|strap|shoulder|bracer|gauntlet/.test(p));visible.sort((a,b)=>rank(a)-rank(b)).forEach(drawPart);
    if(torsoChoice){const image=partImage(torsoChoice.set,torsoChoice.part,view);if(image){let rect=box(robe?'longcoat':'chest',r,view,torsoChoice.set);if(robe)rect=transform(hoodedRobe?[18,0,28,59]:[18,25,28,34],r,view);draw(torsoChoice.set,torsoChoice.part,rect);}}
    if(view===1)back.forEach(drawPart);
    if(headChoice){const image=partImage(headChoice.set,headChoice.part,view);if(image){let ref=[20,-1,24,24];if(/winged/.test(headChoice.part))ref=[10,-14,44,39];else if(/horned/.test(headChoice.part))ref=[12,-6,40,29];else if(/crested/.test(headChoice.part))ref=[19,-10,26,33];else if(/dragon/.test(headChoice.part))ref=[15,-9,34,36];let rect=transform(ref,r,view);if(!/great.helm/.test(headChoice.part))rect=fitHead(image,rect,eyePoints,bodyId,view,headChoice.set.id+':'+headChoice.part);draw(headChoice.set,headChoice.part,rect);}}
    if(!farWeapon)held(wp,'weapon');if(!farShield)held(sh,'shield');
    if(wp&&!farWeapon){c.save();c.beginPath();c.arc(...r.weapon,1.5,0,Math.PI*2);c.clip();c.drawImage(pictures.get('body:'+bodyId+':'+view),0,0);c.restore();}
    if(set.parts.includes('hood-mantle')&&!helmet&&view!==1){const xs=eyePoints.map(p=>p[0]),ys=eyePoints.map(p=>p[1]);if(xs.length){const x=(Math.min(...xs)+Math.max(...xs))/2,y=Math.min(...ys)+r.height*.06;c.save();c.beginPath();c.ellipse(x,y,Math.max(7,(Math.max(...xs)-Math.min(...xs))/2+3),r.height*.115,0,0,Math.PI*2);c.clip();c.drawImage(pictures.get('body:'+bodyId+':'+view),0,0);c.restore();}}
    c.drawImage(pictures.get('features:'+bodyId+':'+view),0,0);
   }c.restore();
  }return{canvas:out,layers,placements};
 }
 window.NativeWorn={init,render,box};
})();
