"""Register and preview the reference-matched composite walk proof."""
from pathlib import Path
from PIL import Image
import numpy as np
import json,base64,hashlib
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
im=Image.open(HERE/'generated.png').convert('RGBA');rgba=np.asarray(im);a=rgba[:,:,3]>128

def runs(v):
 ids=np.flatnonzero(v)
 return [(int(q[0]),int(q[-1])+1) for q in np.split(ids,np.where(np.diff(ids)>1)[0]+1) if len(q)]

def head_center(mask,x0,y0,x1,y1):
 # Helmet and sword remain disconnected above the shoulders. Use the largest component.
 area=mask[y0:y0+max(2,round((y1-y0)*.27)),x0:x1];seen=np.zeros_like(area);best=[]
 for y,x in zip(*np.where(area)):
  if seen[y,x]:continue
  seen[y,x]=True;stack=[(y,x)];component=[]
  while stack:
   yy,xx=stack.pop();component.append(xx)
   for ny,nx in [(yy-1,xx),(yy+1,xx),(yy,xx-1),(yy,xx+1)]:
    if 0<=ny<area.shape[0] and 0<=nx<area.shape[1] and area[ny,nx] and not seen[ny,nx]:seen[ny,nx]=True;stack.append((ny,nx))
  if len(component)>len(best):best=component
 return x0+(min(best)+max(best))/2 if best else (x0+x1)/2

rows=runs(a.any(axis=1));assert len(rows)==4,('Expected4 complete pose rows',rows)
records=[]
for r,(y0,y1) in enumerate(rows):
 cols=runs(a[y0:y1].any(axis=0));assert len(cols)==4,(r,cols)
 for v,(x0,x1) in enumerate(cols):records.append(dict(row=r,direction=v,source=[x0,y0,x1,y1],headCenter=head_center(a,x0,y0,x1,y1)))
scale=min(56/max(q['source'][3]-q['source'][1] for q in records),28/max(q['headCenter']-q['source'][0] for q in records),28/max(q['source'][2]-q['headCenter'] for q in records))
out=Image.new('RGBA',(256,256));hashes=set()
for q in records:
 x0,y0,x1,y1=q['source'];piece=im.crop((x0,y0,x1,y1));piece=piece.resize((round(piece.width*scale),round(piece.height*scale)),Image.Resampling.NEAREST);dx=32-round((q['headCenter']-x0)*scale);dy=62-piece.height
 assert dx>=1 and dx+piece.width<=63 and dy>=1
 out.paste(piece,(q['direction']*64+dx,q['row']*64+dy));q['destination']=[dx,dy,piece.width,piece.height];hashes.add(hashlib.sha256(piece.tobytes()).hexdigest())
assert len(hashes)==16,'Repeated source poses'
out.save(HERE/'sprites-64.png')
frames=[]
for r in range(4):
 strip=out.crop((0,r*64,256,(r+1)*64)).resize((1024,256),Image.Resampling.NEAREST);bg=Image.new('RGB',strip.size,'#20343b');bg.paste(strip,mask=strip.getchannel('A'));frames.append(bg)
frames[0].save(HERE/'walk-loop.gif',save_all=True,append_images=frames[1:],duration=180,loop=0)
frames[0].save(HERE/'first-frame.png')
meta=dict(format='reference-walk-proof',directions=['South','North','East','West'],frameSize=[64,64],frames=4,sequence=[0,1,2,3],frameMs=180,scale=scale,registration=records,compositeArtwork=True,separatedEquipmentRig=False,status='Visual target walking proof; gait and production fitting remain subject to review.')
(HERE/'atlas.json').write_text(json.dumps(meta,indent=2))
ref='data:image/png;base64,'+base64.b64encode((HERE/'reference.png').read_bytes()).decode();sheet='data:image/png;base64,'+base64.b64encode((HERE/'sprites-64.png').read_bytes()).decode();gif='data:image/gif;base64,'+base64.b64encode((HERE/'walk-loop.gif').read_bytes()).decode()
html='''<!doctype html><html lang="en"><meta charset="utf-8"><title>Reference-matched armored walk proof</title><style>body{background:#14232a;color:#edf4f5;font:16px system-ui;padding:28px;margin:0}main{max-width:1100px;margin:auto}h1{font-size:26px}h2{font-size:19px}img{max-width:100%;image-rendering:pixelated}p{color:#bfd0d5;line-height:1.5}.dirs{display:grid;grid-template-columns:repeat(4,1fr);text-align:center}button,select{background:#29444d;color:white;padding:8px;border:1px solid #547781;border-radius:5px}.controls{display:flex;gap:16px;align-items:center;margin:18px 0}canvas{display:block;width:100%;image-rendering:pixelated;background:#20343b}details{margin:24px 0}</style><main><h1>Reference-matched armored walk</h1><p>A visual walking proof using the supplied guard as the appearance and holding-stance target.</p><h2>Your reference</h2><img alt="User reference guard in four directions" src="'''+ref+'''"> <h2>Walking proof</h2><div class="controls"><button id="play">Pause</button><button id="step">Next frame</button><label>Speed <select id="speed"><option value="180">Normal</option><option value="260">Slower</option><option value="120">Faster</option></select></label></div><canvas id="view" width="256" height="64"></canvas><div class="dirs"><span>South</span><span>North</span><span>East</span><span>West</span></div><p id="status"></p><details><summary>Registered64px sheet</summary><img src="'''+sheet+'''" alt="Four-frame four-direction sprite sheet"></details><p>This is a composite artwork proof. A separated body, armor and equipment rig still needs its own fitting; the reusable animation library remains separate.</p></main><script>const image=new Image();image.src='''+json.dumps(sheet)+''';const canvas=document.getElementById('view'),c=canvas.getContext('2d');let playing=true,row=0,last=performance.now();window.proofReady=false;function tick(now){if(image.complete&&image.naturalWidth){if(playing&&now-last>=+document.getElementById('speed').value){row=(row+1)%4;last=now;}c.imageSmoothingEnabled=false;c.clearRect(0,0,256,64);c.drawImage(image,0,row*64,256,64,0,0,256,64);document.getElementById('status').textContent='Frame '+(row+1)+' /4';window.proofReady=true;window.proofFrame=row;}requestAnimationFrame(tick);}document.getElementById('play').onclick=()=>{playing=!playing;document.getElementById('play').textContent=playing?'Pause':'Play';};document.getElementById('step').onclick=()=>{playing=false;document.getElementById('play').textContent='Play';row=(row+1)%4;};requestAnimationFrame(tick);</script></html>'''
(HERE/'index.html').write_text(html);(ROOT/'Dungeon Master Sample/GOA Reference Armored Walk.html').write_text(html)
(HERE/'README.md').write_text('Reference-matched composite walk proof. Source art generated with built-in image_gen; exact prompt and provenance are prompt.txt and generation.json. Packing only crops, uniformly scales and registers the existing alpha artwork, using the helmet center for stable horizontal registration. The64px atlas contains four poses in S/N/E/W order; playback is0,1,2,3 at180ms. The armor, body and weapons are baked together in this visual proof, so this is not yet a reusable separated equipment rig or live-game integration.\n')
print(json.dumps(dict(frames=4,directions=4,uniqueSprites=len(hashes),cellSize=64)))
