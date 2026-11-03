"""Lossless visible-pixel decomposition of the approved Deepguard design.

Masks assign existing source pixels to slots. They never draw replacement pixels.
Full-resolution layers retain the original canvas and reconstruct its visible RGBA.
"""
from pathlib import Path
from io import BytesIO
import base64,json,zipfile
from PIL import Image,ImageDraw,ImageFont,ImageChops

HERE=Path(__file__).resolve().parent
SOURCE=HERE.parent/'deepguard-pixel-v2.png'
ROOT=HERE.parents[5]
PARTS=['body-reference','helmet','chest','shoulder-left','shoulder-right','bracer-left','bracer-right','belt','waist-mail-cloth','greave-left','greave-right','boot-left','boot-right']
DIRECTIONS=['South','North','East','West']

def body_polygons(view):
 if view<2:
  face=[(.24,.25),(.455,.25),(.455,.325),(.545,.325),(.545,.25),(.76,.25),(.77,.33),(.70,.365),(.60,.39),(.40,.39),(.30,.365),(.23,.33)] if view==0 else [(.30,.35),(.70,.35),(.65,.39),(.35,.39)]
  return [face,[(.40,.39),(.60,.39),(.62,.425),(.38,.425)],[(0,.636),(.23,.636),(.25,.72),(.23,.77),(0,.77)],[(1,.636),(.77,.636),(.75,.72),(.77,.77),(1,.77)],[(.04,.552),(.16,.552),(.18,.583),(.04,.583)],[(.84,.552),(.96,.552),(.96,.583),(.82,.583)]]
 polygons=[[(.53,.246),(.87,.246),(.87,.285),(.95,.29),(1,.32),(1,.35),(.90,.35),(.84,.385),(.65,.395),(.55,.365)],[(.60,.395),(.82,.395),(.82,.425),(.60,.425)],[(.09,.646),(.48,.646),(.56,.70),(.55,.765),(.14,.765),(.08,.72)],[(.12,.551),(.36,.551),(.38,.582),(.12,.582)]]
 return polygons if view==2 else [[(1-x,y) for x,y in p] for p in polygons]

def slot(u,v,view):
 # Anatomical left/right, not screen-relative left/right.
 if view<2:
  side='right' if (u<.5)==(view==0) else 'left'
  if v<.402:return 'helmet'
  if v<.572:return 'shoulder-'+side if u<.285 or u>.715 else 'chest'
  if v<.667:
   if u<.225 or u>.775:return 'bracer-'+side
   return 'belt' if v>=.602 else 'chest'
  if v<.81:return 'waist-mail-cloth'
  return ('greave-' if v<.892 else 'boot-')+side
 # East exposes the right side; West the left. Far-side pieces may be occluded.
 x=u if view==2 else 1-u
 near='right' if view==2 else 'left';far='left' if view==2 else 'right'
 if v<.402:return 'helmet'
 if v<.547:
  if x<.635:return 'shoulder-'+near
  return 'chest'
 if v<.665:
  if x<.49:return 'bracer-'+near if v>=.58 else 'shoulder-'+near
  return 'belt' if v>=.602 else 'chest'
 if v<.812:return 'waist-mail-cloth'
 return ('greave-' if v<.892 else 'boot-')+(near if x>=.49 else far)

def encoded(im):
 b=BytesIO();im.save(b,format='PNG');return 'data:image/png;base64,'+base64.b64encode(b.getvalue()).decode()

def main():
 im=Image.open(SOURCE).convert('RGBA');w,h=im.size;alpha=im.getchannel('A')
 boxes=[];cuts=[round(i*w/4) for i in range(5)]
 for d in range(4):
  b=alpha.crop((cuts[d],0,cuts[d+1],h)).point(lambda a:255 if a>=128 else 0).getbbox();boxes.append([b[0]+cuts[d],b[1],b[2]+cuts[d],b[3]])
 ownership=Image.new('L',im.size);pixels=ownership.load()
 for view,b in enumerate(boxes):
  for y in range(h):
   v=(y-b[1])/(b[3]-b[1])
   for x in range(cuts[view],cuts[view+1]):
    pixels[x,y]=PARTS.index(slot((x-b[0])/(b[2]-b[0]),v,view))
  mask=Image.new('1',im.size);draw=ImageDraw.Draw(mask)
  for poly in body_polygons(view):draw.polygon([(round(b[0]+x*(b[2]-b[0])),round(b[1]+y*(b[3]-b[1]))) for x,y in poly],fill=1)
  ownership.paste(0,(0,0),mask)
 full=HERE/'full-resolution';packed=HERE/'64px';full.mkdir(exist_ok=True);packed.mkdir(exist_ok=True)
 assembled=Image.new('RGBA',im.size);assembled64=Image.new('RGBA',(256,64));entries=[];images={}
 referenceHeight=max(b[3]-b[1] for b in boxes);scale=56/referenceHeight
 for index,name in enumerate(PARTS):
  mask=ownership.point(lambda v:255 if v==index else 0)
  layer=Image.new('RGBA',im.size);layer.paste(im,(0,0),mask);layer.save(full/(name+'.png'));assembled.alpha_composite(layer)
  atlas=Image.new('RGBA',(256,64))
  for view,b in enumerate(boxes):
   # Same nearest-neighbor transform for every layer; no independent resizing.
   center=(b[0]+b[2])/2;bottom=b[3]
   tile=layer.transform((64,64),Image.Transform.AFFINE,(1/scale,0,center-32/scale,0,1/scale,bottom-61/scale),resample=Image.Resampling.NEAREST)
   atlas.alpha_composite(tile,(view*64,0))
  atlas.save(packed/(name+'.png'));assembled64.alpha_composite(atlas)
  entries.append(dict(id=name,file64='64px/'+name+'.png',fileFull='full-resolution/'+name+'.png',coordinateSpace=64,frames=[dict(direction=DIRECTIONS[v],rect=[64*v,0,64,64],origin=[0,0]) for v in range(4)],type='visible body reference only' if index==0 else 'equipment layer',occludedViews=[DIRECTIONS[v] for v in range(4) if not atlas.crop((v*64,0,v*64+64,64)).getbbox()]))
  images[name]=encoded(atlas)
 assembled.save(HERE/'reassembled-full.png');assembled64.save(HERE/'reassembled-64px.png')
 # Compare every visible source pixel; transparent RGB payload is visually irrelevant.
 source=im.load();rebuilt=assembled.load();different=0
 for y in range(h):
  for x in range(w):
   if source[x,y][3]!=rebuilt[x,y][3] or (source[x,y][3] and source[x,y]!=rebuilt[x,y]):different+=1
 assert different==0,different
 manifest=dict(name='Deepguard iron',source=str(SOURCE),method='visible-pixel partition; no AI redraw or painted replacement pixels',sourceSize=list(im.size),sourceBodyBounds=boxes,bodySpace64=True,frameSize=[64,64],directionOrder=DIRECTIONS,feet=[32,61],referenceHeight=referenceHeight,sourceScale=scale,parts=entries,verification=dict(visiblePixelDifferences=different,sourcePreserved=True),limits=['Only visible surfaces can be extracted. Hidden surfaces need separate authored artwork before posing.','Standing four-view layers only; walking/attacks and race-specific fitting remain to be built.','Full-resolution layers retain original pixels. 64px versions use a shared nearest-neighbor transform.'])
 (HERE/'manifest.json').write_text(json.dumps(manifest,indent=2))
 data=dict(images=images,parts=PARTS,original=encoded(im),reassembled=encoded(assembled),manifest=manifest)
 html=(HERE/'viewer.template.html').read_text().replace('/*DATA*/null',json.dumps(data,separators=(',',':')))
 (HERE/'index.html').write_text(html)
 sample=ROOT/'Dungeon Master Sample'
 link=sample/'Deepguard Pixel Armor Pieces.html'
 if not link.exists():link.symlink_to(__import__('os').path.relpath(HERE/'index.html',sample))
 with zipfile.ZipFile(sample/'Deepguard Pixel Armor Pieces.zip','w',zipfile.ZIP_DEFLATED) as archive:
  archive.write(HERE/'manifest.json','manifest.json')
  for directory in [full,packed]:
   for path in directory.glob('*.png'):archive.write(path,path.relative_to(HERE))
 print(json.dumps(dict(equipmentPieces=len(PARTS)-1,views=4,visiblePixelDifferences=different,viewer=str(HERE/'index.html'))))
if __name__=='__main__':main()
