#!/usr/bin/env python3
"""Bake one existing calibrated rig action into a reviewable sprite sheet.

Uses the package's actual browser renderer. Never edits source art or rigs.
Requires Python Playwright and local Google Chrome. Output must be a new folder.
"""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import tempfile

from playwright.sync_api import sync_playwright


RENDER = r'''({id, shield}) => {
 const {animator:a,data}=elfLibrary, clip=data.clips[id];
 if(!clip)throw Error('Unknown clip: '+id);
 elfLibrary.setTime(0);
 const times=a.times(id), size=192, sheet=document.createElement('canvas');
 sheet.width=size*4;sheet.height=size*times.length;
 const ctx=sheet.getContext('2d'),cell=document.createElement('canvas');
 cell.width=cell.height=size;const c=cell.getContext('2d',{willReadFrequently:true});
 const options={equipment:{weapon:'sword',shield},showEquipment:true};
 const bounds=[],grips=[],frames=[];
 const finite=(v,path='pose')=>{if(typeof v==='number'&&!Number.isFinite(v))throw Error('Nonfinite '+path);
  if(v&&typeof v==='object')for(const [k,x] of Object.entries(v))finite(x,path+'.'+k);};
 for(let f=0;f<times.length;f++){
  const row=[];
  for(let d=0;d<4;d++){
   const pose=a.render(c,id,times[f],d,options);finite(pose);
   const pixels=c.getImageData(0,0,size,size).data;let x0=size,y0=size,x1=-1,y1=-1;
   for(let y=0;y<size;y++)for(let x=0;x<size;x++)if(pixels[(y*size+x)*4+3]>0){
    x0=Math.min(x0,x);y0=Math.min(y0,y);x1=Math.max(x1,x);y1=Math.max(y1,y);}
   if(x1<0)throw Error('Empty frame '+f+'/'+d);
   if(x0===0||y0===0||x1===size-1||y1===size-1)throw Error('Clipped frame '+f+'/'+d);
   bounds.push([x0,y0,x1+1,y1+1]);
   row.push({right:pose.arms.right.hand,left:pose.arms.left.hand});
   ctx.drawImage(cell,d*size,f*size);
  }
  grips.push(row);frames.push({time:times[f],durationMs:Math.round(((times[f+1]??clip.duration)-times[f])*1000)});
 }
 for(const values of Object.values(clip.events||{}))for(const t of Array.isArray(values)?values:[values]){
  if(!times.some(s=>Math.abs(s-t)<1e-5))throw Error('Missing event frame '+t);
 }
 const inset=Math.min(...bounds.map(b=>Math.min(b[0],b[1],size-b[2],size-b[3])));
 const crop=inset>=32?128:192, offset=(192-crop)/2;
 const phases=[['Guard',0],['Windup',.16],['Strike',.30],['Follow-through',.42],['Recovered',.72]];
 const review=document.createElement('canvas'),scale=2,header=24,band=crop*scale+22;
 review.width=crop*scale*4;review.height=header+phases.length*band;
 const r=review.getContext('2d');r.fillStyle='#444952';r.fillRect(0,0,review.width,review.height);
 r.font='14px sans-serif';r.fillStyle='#ffffff';
 for(let d=0;d<4;d++)r.fillText(['South','North','East','West'][d],d*crop*scale+12,17);
 for(let f=0;f<phases.length;f++)for(let d=0;d<4;d++){
  a.render(c,id,Math.min(phases[f][1],clip.duration),d,options);
  r.fillStyle='#ffffff';r.fillText(phases[f][0],d*crop*scale+12,header+f*band+17);
  r.imageSmoothingEnabled=false;r.drawImage(cell,offset,offset,crop,crop,d*crop*scale,header+f*band+22,crop*scale,crop*scale);
 }
 return {png:sheet.toDataURL(),review:review.toDataURL(),metadata:{character:data.character||'Elf male',
  clip:id,cellSize:size,bodyPixels:64,origin:[64,64],directions:['South','North','East','West'],
  times,frames,duration:clip.duration,events:clip.events,equipment:options.equipment,
  grips,bounds,previewCrop:crop,validation:{finitePoses:true,nonemptyFrames:true,
   unclippedCells:true,eventFramesIncluded:true,directionFrames:times.length*4},
  status:'visual_review_candidate',method:'Existing calibrated rig rendered to sprite frames'}};
}'''

VIEWER = r'''<!doctype html><meta charset="utf-8"><title>Orc sword swing review</title>
<style>body{background:#272c35;color:#f0f2f7;font:16px system-ui;margin:24px}
h1{font-size:24px}.views{display:flex;flex-wrap:wrap;gap:16px}article{background:#444952;padding:12px}
canvas{image-rendering:pixelated;width:256px;height:256px}button,input{margin:12px 8px 12px 0}
a{color:#b8d7ff}p{max-width:850px;line-height:1.5}input{width:320px}</style>
<h1>Orc sword swing · review candidate</h1>
<p>The existing Orc artwork follows the shared slash animation. Sword only, with four facing directions.
This is a rig export for visual review.</p>
<button id="play">Pause</button><label>Speed <select id="speed"><option value=".25">¼×</option>
<option value=".5">½×</option><option value="1" selected>1×</option></select></label>
<input id="time" type="range" min="0" step=".001"><span id="clock"></span>
<div class="views" id="views"></div>
<p><a href="sword-swing.png">Transparent sprite sheet</a> · <a href="sword-swing.json">Timing and grip metadata</a>
 · <a href="pose-review.png">Pose comparison</a></p>
<p>Columns: South, North, East, West. Rows: chronological frames. Native body space is 64 pixels;
each export cell has padding for the sword. The final row is the recovery endpoint.</p>
<script>const META=__META__,IMAGE=__IMAGE__;
const image=new Image(),range=document.getElementById('time'),clock=document.getElementById('clock'),
button=document.getElementById('play'),speed=document.getElementById('speed');
let playing=true,time=0,last=performance.now();range.max=META.duration;
const canvases=META.directions.map(name=>{const article=document.createElement('article');
const title=document.createElement('h2');title.textContent=name;article.append(title);
const c=document.createElement('canvas');c.width=c.height=META.previewCrop;article.append(c);
document.getElementById('views').append(article);return c;});
function draw(){let frame=0;while(frame+1<META.times.length&&META.times[frame+1]<=time)frame++;
const crop=META.previewCrop,o=(META.cellSize-crop)/2;
canvases.forEach((c,d)=>{const x=c.getContext('2d');x.clearRect(0,0,c.width,c.height);x.imageSmoothingEnabled=false;
x.drawImage(image,d*META.cellSize+o,frame*META.cellSize+o,crop,crop,0,0,crop,crop);});
range.value=time;clock.textContent=time.toFixed(2)+' / '+META.duration.toFixed(2)+'s';}
button.onclick=()=>{playing=!playing;button.textContent=playing?'Pause':'Play';last=performance.now();};
range.oninput=()=>{playing=false;button.textContent='Play';time=+range.value;draw();};
image.onload=()=>{document.body.dataset.ready='true';draw();requestAnimationFrame(function tick(now){
if(playing){time=(time+(now-last)/1000*+speed.value)%META.duration;draw();}last=now;requestAnimationFrame(tick);});};
image.src=IMAGE;</script>'''


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--shield',action='store_true')
    args=parser.parse_args()
    package=args.package.resolve();out=args.output.resolve()
    if out.exists():
        parser.error('Output already exists; choose a new review folder.')
    sources=[package/'preview/index.html',package/'preview/engine.js',package/'preview/app.js']
    hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    errors=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless=True)
        try:
            page=browser.new_page()
            page.on('pageerror',lambda e:errors.append(str(e)))
            page.goto((package/'preview/index.html').as_uri())
            page.wait_for_function('!!window.elfLibrary')
            result=page.evaluate(RENDER,dict(id='slash',shield=args.shield))
            if errors:raise RuntimeError(errors)
            result['metadata']['sourceHashes']=hashes
            out.parent.mkdir(parents=True,exist_ok=True)
            with tempfile.TemporaryDirectory(prefix='.action-export-',dir=out.parent) as temp:
                stage=Path(temp)/'result';stage.mkdir()
                for key,name in [('png','sword-swing.png'),('review','pose-review.png')]:
                    (stage/name).write_bytes(base64.b64decode(result[key].split(',',1)[1]))
                (stage/'sword-swing.json').write_text(json.dumps(result['metadata'],indent=2)+'\n')
                viewer=VIEWER.replace('__META__',json.dumps(result['metadata'])).replace('__IMAGE__',json.dumps(result['png']))
                (stage/'index.html').write_text(viewer)
                page.goto((stage/'index.html').as_uri());page.wait_for_function('document.body.dataset.ready === "true"')
                page.click('#play');page.locator('#time').fill('0.3')
                page.locator('#time').dispatch_event('input')
                assert page.locator('canvas').count()==4
                assert '0.30' in page.locator('#clock').inner_text()
                if errors:raise RuntimeError(errors)
                assert all(hashlib.sha256(p.read_bytes()).hexdigest()==hashes[str(p)] for p in sources)
                stage.rename(out)
        finally:
            browser.close()
    print(json.dumps(dict(output=str(out),frames=len(result['metadata']['times']),
                         validation=result['metadata']['validation'],browserErrors=errors)))


if __name__=='__main__':
    main()
