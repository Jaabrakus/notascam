/* Reusable sprite intake, DMI decoding, redraw specification and atlas export.
 * No image AI runs in this library. Codex performs the requested style redraw.
 */
(() => {
  'use strict';
  const DIRECTIONS = {1:['Single view'],4:['South','North','East','West'],
    8:['South','North','East','West','Southeast','Southwest','Northeast','Northwest'],
    16:Array.from({length:16},(_,i)=>`${i*22.5}°`)};
  const KINDS = {
    character: 'Redraw the character or creature with the reference’s compact GOA body proportions, large readable head, chunky hands and feet, dark outlines, and clustered pixel shading. Preserve its race, anatomy, skin colors, hair, distinctive features, clothing and equipment identities.',
    armor: 'Redraw only the armor or clothing shown in the input. Match the reference’s GOA body proportions, scale, dark outlines and clustered pixel shading. Keep the item as a separate wearable overlay; do not add a character underneath. Preserve openings, facing, coverage and material identity.',
    weapon: 'Redraw only the weapon or prop shown in the input. Match the reference’s chunky pixel scale, dark outlines, material shading and simplified readable detail. Preserve the item identity, facing, grip or attachment point, and silhouette.',
    spell: 'Redraw only the spell or effect shown in the input. Match the reference’s pixel cluster size and readable game-sprite finish, while preserving the spell’s colors, silhouette, phase, direction and empty space. Do not add a caster.',
  };
  const canvas = (w,h) => Object.assign(document.createElement('canvas'), {width:w,height:h});
  const integer = (v,min,max,label) => {
    if(!Number.isInteger(v)||v<min||v>max)throw new Error(`${label} must be an integer from ${min} to ${max}.`);
    return v;
  };
  async function loadImage(src) {
    const image=new Image();
    await new Promise((resolve,reject)=>{image.onload=resolve;image.onerror=()=>reject(new Error('Could not read this image.'));image.src=src;});
    return image;
  }
  async function dataURL(file) {
    return new Promise((resolve,reject)=>{const r=new FileReader();r.onload=()=>resolve(r.result);r.onerror=reject;r.readAsDataURL(file);});
  }
  function parseDescription(text) {
    const number=(block,key,def)=>{const m=block.match(new RegExp('^\\s*'+key+'\\s*=\\s*(\\d+)','m'));return m?+m[1]:def;};
    let offset=0;
    const states=text.split(/(?=^state\s*=)/m).slice(1).map(block=>{
      const match=block.match(/^state\s*=\s*"((?:[^"\\]|\\.)*)"/m);
      if(!match)throw new Error('Unreadable DMI state name.');
      const state={name:match[1],offset,dirs:number(block,'dirs',1),frames:number(block,'frames',1),movement:number(block,'movement',0)};
      const delay=block.match(/^\s*delay\s*=\s*([\d.,\s]+)/m);
      state.delays=delay?delay[1].trim().split(',').map(Number):Array(state.frames).fill(1);
      offset+=state.dirs*state.frames;
      return state;
    });
    return states.length?{width:number(text,'width',32),height:number(text,'height',32),states}:null;
  }
  async function dmiMetadata(buffer) {
    const bytes=new Uint8Array(buffer), decoder=new TextDecoder();
    if(bytes.length<8||bytes[0]!==137||decoder.decode(bytes.slice(1,4))!=='PNG')return null;
    const view=new DataView(buffer);
    for(let offset=8;offset+12<=bytes.length;) {
      const length=view.getUint32(offset),type=decoder.decode(bytes.slice(offset+4,offset+8));
      if(offset+12+length>bytes.length)throw new Error('Truncated PNG chunk.');
      if(type==='tEXt'||type==='zTXt') {
        const chunk=bytes.slice(offset+8,offset+8+length),zero=chunk.indexOf(0);
        if(zero>=0&&decoder.decode(chunk.slice(0,zero))==='Description') {
          let text;
          if(type==='tEXt')text=decoder.decode(chunk.slice(zero+1));
          else {
            if(chunk[zero+1]!==0)throw new Error('Unsupported DMI compression.');
            const stream=new Blob([chunk.slice(zero+2)]).stream().pipeThrough(new DecompressionStream('deflate'));
            const inflated=await new Response(stream).arrayBuffer();
            text=decoder.decode(inflated);
          }
          return parseDescription(text);
        }
      }
      offset+=length+12;
    }
    return null;
  }
  async function inspect(file) {
    if(file.size>32*1024*1024)throw new Error('Choose an image smaller than 32 MB.');
    const buffer=await file.arrayBuffer(), metadata=await dmiMetadata(buffer);
    // DMI files are PNG containers, regardless of their browser MIME type.
    let src=await dataURL(new Blob([buffer],{type:metadata||file.name.toLowerCase().endsWith('.dmi')?'image/png':file.type||'image/png'}));
    const image=await loadImage(src);
    if(image.width*image.height>32*1024*1024)throw new Error('This image is too large. Split it into smaller sheets first.');
    if(!new Uint8Array(buffer).slice(0,8).every((byte,i)=>byte===[137,80,78,71,13,10,26,10][i])) {
      const normalized=canvas(image.width,image.height);normalized.getContext('2d').drawImage(image,0,0);src=normalized.toDataURL();
    }
    return {image,src,metadata,name:file.name};
  }
  function prepare(input,config) {
    const width=integer(config.width,1,4096,'Frame width'),height=integer(config.height,1,4096,'Frame height');
    const dirs=integer(config.dirs,1,16,'Directions'),frames=integer(config.frames,1,64,'Animation frames');
    const offset=integer(config.offset,0,100000,'First cell');
    if(!DIRECTIONS[dirs])throw new Error('Choose 1, 4, 8 or 16 directions.');
    const columns=Math.floor(input.image.width/width),rows=Math.floor(input.image.height/height);
    if(!columns||!rows)throw new Error('The frame dimensions exceed the input image.');
    if(input.image.width%width||input.image.height%height)throw new Error('Frame dimensions must divide the source sheet exactly.');
    if(offset+dirs*frames>columns*rows)throw new Error('The selected frames run beyond the source sheet.');
    if(dirs*frames>128)throw new Error('Prepare at most 128 cells per redraw job.');
    const selected=canvas(dirs*width,frames*height),c=selected.getContext('2d');c.imageSmoothingEnabled=false;
    const cells=[];
    for(let frame=0;frame<frames;frame++)for(let direction=0;direction<dirs;direction++) {
      const index=offset+(config.order==='direction-major'?direction*frames+frame:frame*dirs+direction);
      const x=index%columns*width,y=Math.floor(index/columns)*height;
      c.drawImage(input.image,x,y,width,height,direction*width,frame*height,width,height);
      cells.push({column:direction,row:frame,direction:DIRECTIONS[dirs][direction],frame,sourceCell:index,sourceRect:[x,y,width,height]});
    }
    return {canvas:selected,cells,width,height,dirs,frames};
  }
  function specification(input,prepared,options) {
    const kind=Object.hasOwn(KINDS,options.kind)?options.kind:'character';
    const size=integer(options.outputSize,16,256,'Output frame size');
    const label=String(options.name||input.name).slice(0,120),notes=String(options.notes||'').slice(0,4000);
    return {format:'dungeon-master.sprite-redraw',version:1,name:label,kind,
      source:{filename:input.name,frameWidth:prepared.width,frameHeight:prepared.height,
        state:options.state??'custom',movement:options.movement||0,delays:options.delays||[],cells:prepared.cells},
      output:{columns:prepared.dirs,rows:prepared.frames,frameWidth:size,frameHeight:size,
        directionOrder:DIRECTIONS[prepared.dirs],transparent:true,preserveCellPlacement:true},
      style:{reference:'style-reference.png',name:'Approved GOA / LOTR race bodies'},notes,
      instructions:[
        'Use case: style-transfer. Input 1 (input-sheet.png) is the edit target. Input 2 (style-reference.png) is the approved style reference only.',
        KINDS[kind],
        `Redraw exactly ${prepared.dirs} columns by ${prepared.frames} rows. Each cell must correspond to the same cell in input-sheet.png. Columns: ${DIRECTIONS[prepared.dirs].join(', ')}. Rows are consecutive animation frames.`,
        'Preserve each source pose, facing, animation phase and identity. Do not replace different poses with repeated standing poses. Do not invent additional frames, directions, equipment or subjects.',
        'Use a truly transparent background. No checkerboard, floor, shadows outside the sprite, borders, labels or text. Keep each complete sprite within its cell, with consistent scale, margins and attachment alignment across frames.',
        `Final packed target: ${size} × ${size} pixels per cell. The redraw may be larger, but its equal cell grid must remain exact so the converter can pack it. Keep pixel edges crisp rather than smooth painted rendering.`,
        notes?`Additional user requirements: ${notes}`:'',
      ].filter(Boolean).join('\n\n')};
  }
  function requestText(spec,location='the attached conversion bundle') {
    return `Please redraw the sprites in ${location} to match its approved style-reference.png. Read request.json and inspect input-sheet.png and style-reference.png first. Use the built-in image generation tool here in Codex, preserve transparency, follow the specified cell layout and poses, and save the generated image as result.png beside request.json. Keep the input files unchanged. Inspect the result for correct frame count, directions, pose consistency and clipping; tell me about any mismatch. The local converter will detect result.png.`;
  }
  function pack(image,spec) {
    const {columns,rows,frameWidth,frameHeight}=spec.output;
    if(image.width<columns||image.height<rows)throw new Error('The redraw is smaller than the requested cell grid.');
    const output=canvas(columns*frameWidth,rows*frameHeight),c=output.getContext('2d');c.imageSmoothingEnabled=false;
    const sw=image.width/columns,sh=image.height/rows;
    for(let row=0;row<rows;row++)for(let col=0;col<columns;col++)c.drawImage(image,col*sw,row*sh,sw,sh,col*frameWidth,row*frameHeight,frameWidth,frameHeight);
    return output;
  }
  // Small dependency-free ZIP writer (stored entries, UTF-8 names).
  const crcTable=Array.from({length:256},(_,n)=>{for(let k=0;k<8;k++)n=n&1?0xedb88320^(n>>>1):n>>>1;return n>>>0;});
  const crc32=bytes=>{let crc=0xffffffff;for(const b of bytes)crc=crcTable[(crc^b)&255]^(crc>>>8);return (crc^0xffffffff)>>>0;};
  async function zip(entries) {
    const local=[],central=[];let offset=0,centralSize=0;
    for(const [name,value] of entries) {
      const filename=new TextEncoder().encode(name),bytes=typeof value==='string'?new TextEncoder().encode(value):new Uint8Array(await value.arrayBuffer()),crc=crc32(bytes);
      const header=new Uint8Array(30+filename.length),v=new DataView(header.buffer);
      v.setUint32(0,0x04034b50,true);v.setUint16(4,20,true);v.setUint16(6,0x800,true);v.setUint32(14,crc,true);v.setUint32(18,bytes.length,true);v.setUint32(22,bytes.length,true);v.setUint16(26,filename.length,true);header.set(filename,30);
      local.push(header,bytes);
      const directory=new Uint8Array(46+filename.length),d=new DataView(directory.buffer);
      d.setUint32(0,0x02014b50,true);d.setUint16(4,20,true);d.setUint16(6,20,true);d.setUint16(8,0x800,true);d.setUint32(16,crc,true);d.setUint32(20,bytes.length,true);d.setUint32(24,bytes.length,true);d.setUint16(28,filename.length,true);d.setUint32(42,offset,true);directory.set(filename,46);
      central.push(directory);centralSize+=directory.length;offset+=header.length+bytes.length;
    }
    const end=new Uint8Array(22),e=new DataView(end.buffer);e.setUint32(0,0x06054b50,true);e.setUint16(8,entries.length,true);e.setUint16(10,entries.length,true);e.setUint32(12,centralSize,true);e.setUint32(16,offset,true);
    return new Blob([...local,...central,end],{type:'application/zip'});
  }
  function manifest(spec) {
    return {format:'dungeon-master.sprite-atlas',version:1,image:'sprites.png',
      size:[spec.output.columns*spec.output.frameWidth,spec.output.rows*spec.output.frameHeight],
      frameSize:[spec.output.frameWidth,spec.output.frameHeight],state:spec.source.state,
      directionOrder:spec.output.directionOrder,delays:spec.source.delays,
      provenance:'AI style redraw; review animation and overlay registration before game integration',
      frames:spec.source.cells.map(cell=>({direction:cell.direction,frame:cell.frame,
        rect:[cell.column*spec.output.frameWidth,cell.row*spec.output.frameHeight,spec.output.frameWidth,spec.output.frameHeight]}))};
  }
  globalThis.SpriteEngine={DIRECTIONS,canvas,loadImage,dataURL,dmiMetadata,parseDescription,inspect,prepare,specification,requestText,pack,zip,manifest};
})();
