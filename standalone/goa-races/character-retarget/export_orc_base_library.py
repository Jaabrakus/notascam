#!/usr/bin/env python3
"""Export all existing Orc motion definitions as body-only, native-scale sheets.

Source rig and native Orc pixels are preserved. These are assembled pose drafts,
not newly AI-drawn anatomy or a claim that every pose is artistically approved.
"""
import base64
import hashlib
import json
from pathlib import Path
import tempfile

from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[3]
PACKAGE=ROOT/'Dungeon Master Sample/GOA Retarget Review - Orc Male'
SOURCE=ROOT/'Dungeon Master Sample/Sprites/Male/Orc/base/sprites.png'
OUT=ROOT/'Dungeon Master Sample/GOA Orc Base Animation Sprites/body-only-library-v1'
KI_SOURCE=ROOT/'standalone/goa-dbz-sideproject/animator.js'

KI_SETUP=r'''()=>{
 const {data,animator}=elfLibrary;
 const actor={directions:data.views.map(v=>({arms:v.arms,fullBody:{parts:v.parts,waist:v.waist,neck:v.neck,legs:v.legs,nearLeg:v.nearLeg}}))};
 const a=new DbzAnimator({actor},animator.images),sample=a.sample.bind(a);
 a.skin=d=>{const color=data.views[d].jointColors.rightElbow;return `rgb(${color[0]},${color[1]},${color[2]})`;};
 a.sample=(...args)=>{const p=sample(...args),view=data.views[p.view];
  for(const [name,b] of Object.entries(p.bones)){const ps=view.partSource?.[name];if(ps){b.sourceRoot=ps[0];b.sourceTip=ps[1];}}
  return p;};
 window.orcKi=a;
 const own=DbzAnimator.clips.map(c=>({...c,id:'ki_'+c.id,sourceId:c.id,sequence:[c.id],category:'Unarmed and ki poses'}));
 const combos=[['jab_cross','Jab - cross',['punch','punch2']],['double_jab','Double jab',['punch','punch']],
 ['jab_cross_kick','Jab - cross - rising kick',['punch','punch2','kick']],['kick_chain','Rising kick - aerial sweep',['kick','kick2']]];
 for(const [id,label,sequence] of combos){let duration=0,events=[];for(const id of sequence){const c=DbzAnimator.clips.find(c=>c.id===id);
 events.push(...c.events.map(e=>({...e,time:e.time+duration})));duration+=c.duration;}
 own.push({id:'ki_'+id,label,sequence,duration,events,category:'Unarmed and ki poses',loop:false});}
 window.orcKiClips=own;return own;
}'''

KI_EXPORT=r'''id=>{
 const clip=orcKiClips.find(c=>c.id===id),a=orcKi,segments=[];let offset=0;
 const times=[];for(const name of clip.sequence){const c=DbzAnimator.clips.find(c=>c.id===name),timeline=a.timeline(name);
 segments.push({id:name,start:offset,duration:c.duration});times.push(...timeline.times.map(t=>+(t+offset).toFixed(6)));offset+=c.duration;}
 times.push(+clip.duration.toFixed(6));
 const sheet=document.createElement('canvas');sheet.width=768;sheet.height=times.length*192;
 const cell=document.createElement('canvas');cell.width=cell.height=192;const c=cell.getContext('2d'),ctx=sheet.getContext('2d');
 const grips=[],bounds=[],issues=[];
 function finite(v){if(typeof v==='number'&&!Number.isFinite(v))throw Error('Nonfinite '+id);if(v&&typeof v==='object')for(const x of Object.values(v))finite(x);}
 times.forEach((time,row)=>{const segment=segments.find((s,i)=>time<s.start+s.duration-1e-6||i===segments.length-1),hands=[];
 for(let direction=0;direction<4;direction++){
 c.clearRect(0,0,192,192);c.save();c.translate(64,64);c.imageSmoothingEnabled=false;
 const pose=a.render(c,segment.id,Math.min(segment.duration,time-segment.start),direction);c.restore();finite(pose);
 const pixels=c.getImageData(0,0,192,192).data;let x0=192,y0=192,x1=-1,y1=-1;
 for(let y=0;y<192;y++)for(let x=0;x<192;x++)if(pixels[(y*192+x)*4+3]){x0=Math.min(x0,x);y0=Math.min(y0,y);x1=Math.max(x1,x);y1=Math.max(y1,y);}
 if(x1<0)throw Error('Empty '+id);if(x0<=0||y0<=0||x1>=191||y1>=191)issues.push({type:'cell_edge',row,direction});
 bounds.push([x0,y0,x1+1,y1+1]);hands.push({right:pose.arms.right.hand,left:pose.arms.left.hand});ctx.drawImage(cell,direction*192,row*192);
 }grips.push(hands);});
 for(const event of clip.events)if(!times.some(t=>Math.abs(t-event.time)<1e-5))throw Error('Missing ki event frame '+id);
 return {png:sheet.toDataURL(),metadata:{id,label:clip.label,category:clip.category,cellSize:192,bodyPixels:64,origin:[64,64],
 directions:['South','North','East','West'],times,duration:clip.duration,events:clip.events,grips,bounds,issues,
 frameDurationsMs:times.map((t,i)=>Math.round(((times[i+1]??clip.duration)-t)*1000)),equipmentDrawn:false,effectsDrawn:false,
 motionSource:'Existing ki-study choreography adapted to the original Orc parts',sequence:clip.sequence,
 status:'new_orc_motion_adaptation_needs_visual_review'}};
}'''

WEAPONS=r'''()=>Object.entries(elfLibrary.data.items).map(([id,item])=>{
 const images=item.views.map(v=>elfLibrary.animator.images[v.image]);
 const size=Math.max(64,...images.map(i=>Math.max(i.width,i.height))),c=document.createElement('canvas');c.width=size*4;c.height=size;
 const ctx=c.getContext('2d');ctx.imageSmoothingEnabled=false;
 images.forEach((image,d)=>ctx.drawImage(image,d*size,0));
 return {id,png:c.toDataURL(),metadata:{id,cellSize:size,directions:['South','North','East','West'],views:item.views,
 source:'Existing equipment artwork copied at native scale',separateFromBody:true}};
})'''

EXPORT=r'''id=>{
 const {animator:a,data}=elfLibrary,clip=data.clips[id],times=a.times(id),size=192;
 const sheet=document.createElement('canvas');sheet.width=4*size;sheet.height=times.length*size;
 const cell=document.createElement('canvas');cell.width=cell.height=size;
 const ctx=sheet.getContext('2d'),c=cell.getContext('2d',{willReadFrequently:true});
 const grips=[],bounds=[],issues=[];
 function finite(value){if(typeof value==='number'&&!Number.isFinite(value))throw Error('Nonfinite pose '+id);
 if(value&&typeof value==='object')for(const v of Object.values(value))finite(v);}
 for(let row=0;row<times.length;row++){
  const hands=[];
  for(let direction=0;direction<4;direction++){
   const pose=a.render(c,id,times[row],direction,{showEquipment:false});finite(pose);
   if(id==='idle'||id==='walk'){
    // Use the unmodified drawn source frames for original locomotion.
    const frame=id==='idle'?0:[0,1,0,2][Math.floor(times[row]/.2)%4];
    c.clearRect(0,0,size,size);c.imageSmoothingEnabled=false;
    c.drawImage(window.orcSource,direction*64,frame*64,64,64,64,64,64,64);
   }
   const pixels=c.getImageData(0,0,size,size).data;let x0=size,y0=size,x1=-1,y1=-1;
   for(let y=0;y<size;y++)for(let x=0;x<size;x++)if(pixels[(y*size+x)*4+3]){
    x0=Math.min(x0,x);y0=Math.min(y0,y);x1=Math.max(x1,x);y1=Math.max(y1,y);}
   if(x1<0)throw Error('Empty '+id+' '+row+' '+direction);
   if(x0<=0||y0<=0||x1>=size-1||y1>=size-1)issues.push({type:'cell_edge',row,direction});
   bounds.push([x0,y0,x1+1,y1+1]);hands.push({right:pose.arms.right.hand,left:pose.arms.left.hand});
   ctx.drawImage(cell,direction*size,row*size);
  }
  grips.push(hands);
 }
 for(const events of Object.values(clip.events||{}))for(const t of Array.isArray(events)?events:[events])
  if(!times.some(s=>Math.abs(s-t)<1e-5))throw Error('Missing event frame '+id+' '+t);
 return {png:sheet.toDataURL('image/png'),metadata:{id,label:clip.label,category:clip.category,
  cellSize:size,bodyPixels:64,origin:[64,64],directions:['South','North','East','West'],times,
  frameDurationsMs:times.map((t,i)=>Math.round(((times[i+1]??clip.duration)-t)*1000)),
  duration:clip.duration,events:clip.events,grips,bounds,issues,
  equipmentDrawn:false,effectsDrawn:false,equipmentPoseReference:clip.equipment,
  status:'assembled_pose_draft_needs_visual_review',originalPixelsUsedForLocomotion:['idle','walk'].includes(id)}};
}'''


def main():
    if OUT.exists():raise SystemExit('Output exists; retain it and choose a new version for changes.')
    sources=[SOURCE,PACKAGE/'preview/index.html',PACKAGE/'preview/engine.js',PACKAGE/'preview/app.js',KI_SOURCE]
    hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    errors=[];records=[];total=0
    OUT.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.orc-base-export-',dir=OUT.parent) as temp:
        stage=Path(temp)/'result';(stage/'sheets').mkdir(parents=True)
        with sync_playwright() as pw:
            browser=pw.chromium.launch(executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless=True)
            try:
                page=browser.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
                page.goto((PACKAGE/'preview/index.html').as_uri());page.wait_for_function('!!window.elfLibrary')
                page.evaluate('elfLibrary.setTime(0)')
                url='data:image/png;base64,'+base64.b64encode(SOURCE.read_bytes()).decode()
                page.evaluate('async url=>{window.orcSource=new Image();orcSource.src=url;await orcSource.decode();}',url)
                clips=page.evaluate('Object.keys(elfLibrary.data.clips)')
                for index,clip in enumerate(clips):
                    result=page.evaluate(EXPORT,clip);meta=result['metadata']
                    (stage/'sheets'/f'{clip}.png').write_bytes(base64.b64decode(result['png'].split(',',1)[1]))
                    (stage/'sheets'/f'{clip}.json').write_text(json.dumps(meta,indent=2)+'\n')
                    records.append({k:meta[k] for k in ['id','label','category','duration','times','issues','events']})
                    total+=len(meta['times'])*4
                    if (index+1)%10==0:print(json.dumps(dict(exported=index+1,total=len(clips))),flush=True)
                page.add_script_tag(content=KI_SOURCE.read_text())
                ki_clips=page.evaluate(KI_SETUP)
                for index,clip in enumerate(ki_clips):
                    result=page.evaluate(KI_EXPORT,clip['id']);meta=result['metadata']
                    (stage/'sheets'/f'{clip["id"]}.png').write_bytes(base64.b64decode(result['png'].split(',',1)[1]))
                    (stage/'sheets'/f'{clip["id"]}.json').write_text(json.dumps(meta,indent=2)+'\n')
                    records.append({k:meta[k] for k in ['id','label','category','duration','times','issues','events']})
                    total+=len(meta['times'])*4
                (stage/'weapons').mkdir()
                weapons=page.evaluate(WEAPONS)
                for item in weapons:
                    (stage/'weapons'/f'{item["id"]}.png').write_bytes(base64.b64decode(item['png'].split(',',1)[1]))
                    (stage/'weapons'/f'{item["id"]}.json').write_text(json.dumps(item['metadata'],indent=2)+'\n')
                (stage/'weapons/catalog.json').write_text(json.dumps([w['metadata'] for w in weapons],indent=2)+'\n')
                cards=''.join(f'<article><h2>{w["id"].replace("_"," ")}</h2><a href="{w["id"]}.png"><img src="{w["id"]}.png"></a><p><a href="{w["id"]}.json">Grip metadata</a></p></article>' for w in weapons)
                (stage/'weapons/index.html').write_text('<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Weapon and shield sprites</title><style>body{background:#272c35;color:white;font:16px system-ui;margin:20px}main{display:flex;flex-wrap:wrap;gap:16px}article{background:#444952;padding:16px}h2{font-size:18px}img{image-rendering:pixelated;max-width:90vw;width:512px}a{color:#bbd9ff}</style><h1>Weapon and shield sprites</h1><p>Separate native-scale artwork. Columns: South, North, East, West.</p><a href="../">Back to Orc animations</a><main>'+cards+'</main>')
                if errors:raise RuntimeError(errors)
                report=dict(status='exported_for_visual_review',clips=len(records),kiAndUnarmedClips=len(ki_clips),weaponSheets=len(weapons),directionFrames=total,
                            nativeBodyPixels=64,equipmentDrawn=False,effectsDrawn=False,browserErrors=errors,
                            cellEdgeIssues=sum(len(c['issues']) for c in records),sourceHashes=hashes,
                            limits=['Assembled from the existing Orc pixel parts and motion definitions.',
                                    'Extreme bends, inferred hidden anatomy and physics reactions still need visual review.',
                                    'Ki poses are new Orc adaptations of the existing motion study and need visual review.',
                                    'Live game assets are not replaced.'])
                (stage/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
                for record in records:
                    meta=json.loads((stage/'sheets'/f'{record["id"]}.json').read_text())
                    record['previewCrop']=128 if all(b[0]>=32 and b[1]>=32 and b[2]<=160 and b[3]<=160 for b in meta['bounds']) else 192
                (stage/'catalog.json').write_text(json.dumps(records,indent=2)+'\n')
                viewer=Path(__file__).with_name('orc_base_library_viewer.html').read_text()
                (stage/'index.html').write_text(viewer.replace('/*CATALOG*/',json.dumps(records).replace('<','\\u003c')))
                page.goto((stage/'index.html').as_uri());page.wait_for_function('document.body.dataset.ready === "true"')
                for clip in ['idle','walk','slash','block','bash','bow_shot','ki_punch','ki_kick','ki_beam']:
                    page.select_option('#action',clip)
                    page.wait_for_function('document.body.dataset.loaded === document.getElementById("action").value')
                page.select_option('#action','slash');page.wait_for_function('document.body.dataset.loaded === "slash"')
                page.locator('#play').click()
                page.screenshot(path=str(stage/'viewer-preview.png'),full_page=True)
                if errors:raise RuntimeError(errors)
            finally:browser.close()
        assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in hashes.items())
        (stage/'README.md').write_text('''# Orc base animation sheets

All 97 existing library actions plus 21 ki-study/unarmed actions and chains are
exported as transparent body-only sheets. Separate equipment sheets are in weapons/.
Open index.html to play, slow down, scrub and inspect each direction independently.
Original Orc artwork is the master. Idle/walk copy the original drawn cells; other
poses assemble its existing cut pixel parts using saved motion definitions.

Body space remains 64px. Each export cell is 192px with the original body's origin
at [64,64], preserving room for extended arms, kicks and falls without resizing.
Columns are South, North, East, West; rows are chronological samples. Timing JSON
includes action events and both hand sockets for equipment/effects added later.
Weapon/shield gripping poses remain; equipment and effects are not painted in.

These are assembled pose drafts for review. The rig's inferred hidden anatomy,
deep bends, nearest-neighbor rotations and simulated reaction poses can need
pixel cleanup. This is not a new AI redraw or blanket visual approval. No live
game files changed. Ki-study poses adapt existing choreography to the original Orc
parts; they are new review candidates, not approved finished art. verification.json
records actual coverage and source hashes.
''')
        stage.rename(OUT)
    print(json.dumps(report),flush=True)


if __name__=='__main__':main()
