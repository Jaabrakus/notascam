/* Preview the native redraws on actual 64px race bodies. Standing fits are drafts. */
(() => {
 const D=WORN_DATA,cv=(w,h)=>Object.assign(document.createElement('canvas'),{width:w,height:h}),pictures=new Map();
 const dirs=['South','North','East','West'];
 async function init(){await Promise.all(Object.entries(D.images).map(async([key,url])=>{const img=new Image();await new Promise((yes,no)=>{img.onload=yes;img.onerror=no;img.src=url;});pictures.set(key,img);}));}
 function partImage(set,part,view){return pictures.get(set.id+':'+part+':'+view);}
 function box(part,r,view,set){const h=r.height,w=r.width,x=r.chest[0],top=r.top,front=view<2,left=part.includes('left'),hand=left?r.shield:r.weapon,side=front?((left?1:-1)*(view===1?-1:1)):((left?1:-1)*(view===3?-1:1));
  if(part==='helmet'||part==='brow-piece'){
   const dragon=/dragonhide|dragonbone|kobold-dragon$/.test(set.id),dwarf=set.id.startsWith('dwarf');
   const hh=h*(dragon?.58:part==='brow-piece'?.23:dwarf?.46:.40),ww=r.headWidth*(dragon?1.35:1.09);
   return [r.head[0]-ww/2,top-(dragon?h*.13:part==='brow-piece'?1:1+h*(dwarf?.13:.07)),ww,hh];
  }
  if(part==='hood-mantle')return[r.head[0]-r.headWidth*.65,top-h*.12,r.headWidth*1.30,h*.66];
  if(part==='back-mantle'||part.startsWith('half-cape'))return[x-w*.48,top+h*.37,w*.96,h*.47];
  if(part.includes('chest')||part==='longcoat'){const long=/apron|longcoat/.test(part)||set.id==='elf-leather';const ww=w*(front?.80:.85),hh=h*(long?.45:.30);return[x-ww/2,r.chest[1]-h*.15,ww,hh];}
  if(part.includes('harness')||part.startsWith('strap-'))return[x-w*.45,top+h*.39,w*.90,h*.34];
  if(part==='shoulder-one'){const right=['dwarf-gold','orc-dragonbone','elf-wood'].includes(set.id),p=right?r.weapon:r.shield;return[p[0]-w*.17,top+h*.39,w*.34,h*.28];}
  if(part.startsWith('shoulder-'))return[hand[0]-w*.15,top+h*.39,w*.30,h*.23];
  if(part.includes('bracer')||part.includes('gauntlet')){const ww=w*(front?.23:.34),hh=h*(part.includes('gauntlet')?.23:.16);return[hand[0]-ww/2,hand[1]-hh*.95,ww,hh];}
  if(part==='belt')return[x-w*.43,top+h*.70,w*.86,h*.09];
  if(part.includes('hip-panels'))return[x-w*.44,top+h*.71,w*.88,h*.23];
  const footX=x+side*w*(front?.17:.055);
  if(part.startsWith('lower-leg'))return[footX-w*.15,61-h*.23,w*.30,h*.23];
  if(part.startsWith('greave-'))return[footX-w*.13,61-h*.24,w*.26,h*.17];
  if(part.startsWith('boot-'))return[footX-w*.17,61-h*.105,w*.34,h*.105];
  throw Error('Unknown fitted part '+part);
 }
 function semantic(set,part){if(['kobold-dragonhide','kobold-dragon'].includes(set.id)&&part==='shoulder-one')return'back-mantle';if(set.id==='dark-elf-spidersilk'){if(part==='helmet')return'brow-piece';if(part==='chest')return'longcoat';if(part==='shoulder-one')return'half-cape-left';}return part;}
 function render(bodyId,setId,{bare=false}={}){const b=D.bodies.find(b=>b.id===bodyId),set=D.catalog.sheets.find(s=>s.id===setId);if(!b||!set)throw Error('Unknown fit selection');const out=cv(512,128),c=out.getContext('2d'),layers={},placements=[];c.imageSmoothingEnabled=false;
  for(let view=0;view<4;view++){
   c.save();c.translate(view*128+32,32);const r=b.views[view].rig;
   const draw=part=>{const image=partImage(set,part,view);if(!image)return;let rect;
    if(set.registeredMaster){const sx=r.width/D.masterWidths[view],sy=r.height/56;rect=[32-32*sx,61-61*sy,64*sx,64*sy];}
    else rect=box(semantic(set,part),r,view,set);
    c.drawImage(image,...rect);placements.push({part,direction:dirs[view],rect});if(!layers[part])layers[part]=cv(512,128);const l=layers[part].getContext('2d');l.imageSmoothingEnabled=false;l.drawImage(image,rect[0]+view*128+32,rect[1]+32,rect[2],rect[3]);};
   const back=set.parts.filter(p=>semantic(set,p)==='back-mantle'||semantic(set,p).startsWith('half-cape'));
   if(!bare)back.forEach(draw);c.drawImage(pictures.get('body:'+bodyId+':'+view),0,0);
   if(!bare){const rank=p=>/lower-leg|boot|greave/.test(p)?0:/chest|longcoat/.test(p)?1:/hip-panels|belt/.test(p)?2:/harness|strap|shoulder/.test(p)?3:/bracer|gauntlet/.test(p)?4:5;set.parts.filter(p=>!back.includes(p)).sort((a,b)=>rank(a)-rank(b)).forEach(draw);
    // The generated open hood includes dark inner lining. The wearer's face is
    // a foreground body layer in its opening; source armor pixels stay intact.
    if(set.parts.includes('hood-mantle')&&view!==1){c.save();c.beginPath();c.ellipse(r.head[0]+(view===2?3:view===3?-3:0),topFace(r),r.headWidth*(view===0?.31:.25),r.height*.115,0,0,Math.PI*2);c.clip();c.drawImage(pictures.get('body:'+bodyId+':'+view),0,0);c.restore();}
    c.drawImage(pictures.get('features:'+bodyId+':'+view),0,0);}
   c.restore();
  }return{canvas:out,layers,placements};
 }
 const topFace=r=>r.top+r.height*.35;
 window.NativeWorn={init,render,box};
})();
