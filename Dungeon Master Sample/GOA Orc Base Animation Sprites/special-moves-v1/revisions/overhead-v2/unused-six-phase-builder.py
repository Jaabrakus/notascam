#!/usr/bin/env python3
"""Pack the four approved 2D special-move families without changing prior art."""
from pathlib import Path
import importlib.util
import hashlib
import json
import numpy as np
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'Dungeon Master Sample/GOA Orc Base Animation Sprites/special-moves-v1'
APPROVED=OUT.parent/'curated-attacks-v1'
spec=importlib.util.spec_from_file_location('curate',Path(__file__).with_name('curate_orc_attacks.py'))
curate=importlib.util.module_from_spec(spec);spec.loader.exec_module(curate)
ACTIONS={
 'overhead_cast':('Overhead cast',['Guard','Gather','Lift','Windup','Throw','Follow through'],[180,140,170,240,120,190]),
 'ground_slam':('Ground slam',['Guard','Raise fists','Slam','Recover'],[180,200,130,230]),
 'dash_strike':('Dash strike',['Guard','Windup','Strike','Recover'],[180,130,120,220]),
 'stagger':('Hit reaction / stagger',['Guard','Recoil','Stagger','Recover'],[150,120,220,250])}

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def extract_cast(path):
 image=Image.open(path).convert('RGBA');data=np.asarray(image).copy()
 data[:,:,3]=np.where(data[:,:,3]>200,255,0)
 image=Image.fromarray(data);rows=curate.bands(data[:,:,3]>0)
 assert len(rows)==6,rows
 frames={}
 for row,(top,bottom) in enumerate(rows):
  for direction in range(4):
   crop=image.crop((direction*image.width//4,top,(direction+1)*image.width//4,bottom))
   frames[row,direction]=crop.crop(crop.getbbox())
 return frames

def register_cast(raw,palette,guard,scale):
 width,height=[round(v*scale) for v in raw.size]
 a=np.asarray(raw.resize((width,height),Image.Resampling.NEAREST)).copy()
 nearest=((a[:,:,:3].astype(np.int32)[:,:,None]-palette.astype(np.int32)[None,None])**2).sum(3).argmin(2)
 a[:,:,:3]=palette[nearest];a[:,:,3]=np.where(a[:,:,3]>128,255,0);a[a[:,:,3]==0,:3]=0
 # Align the planted feet instead of treating raised hands as the head anchor.
 gy,gx=np.where(np.asarray(guard)[62:68,:,3]>128)
 y,x=np.where(a[-6:,:,3]>128)
 left=round((gx.min()+gx.max())/2-(x.min()+x.max())/2);top=68-height
 assert left>=0 and top>=0 and left+width<=80
 frame=Image.new('RGBA',(80,80));frame.paste(Image.fromarray(a),(left,top))
 # Stable shorts and feet use the actual approved pixels in every cast phase.
 frame.paste(guard.crop((0,56,80,80)),(0,56))
 return frame

def main():
 (OUT/'frames').mkdir(exist_ok=True)
 before=json.loads((OUT/'approved-frame-hashes.json').read_text())
 assert before=={p.name:digest(p) for p in (APPROVED/'frames').glob('*.png')}
 palette=curate.palette_from_original();records=[];recipes=[]
 combined=Image.new('RGBA',(320,sum(len(v[1]) for v in ACTIONS.values())*80));contact=Image.new('RGB',(1020,776),'#444951');draw=ImageDraw.Draw(contact)
 atlas_y=0
 for ai,(action,(title,labels,timings)) in enumerate(ACTIONS.items()):
  path=OUT/'drawings'/('overhead_cast-v3.png' if action=='overhead_cast' else f'{action}.png')
  source=extract_cast(path) if action=='overhead_cast' else curate.extract(path)
  curate.SCALE=.205*1448/Image.open(path).width
  count=len(labels);sheet=Image.new('RGBA',(320,count*80))
  cast_scale=float(np.median([Image.open(APPROVED/'frames'/f'punch_right-{d}-0.png').getbbox()[3]-Image.open(APPROVED/'frames'/f'punch_right-{d}-0.png').getbbox()[1] for d in curate.DIRECTIONS]))/float(np.median([source[0,d].height for d in range(4)])) if action=='overhead_cast' else None
  for row in range(count):
   for d,direction in enumerate(curate.DIRECTIONS):
    shared=row==0 or (action=='stagger' and row==3)
    guard=Image.open(APPROVED/'frames'/f'punch_right-{direction}-0.png').convert('RGBA')
    frame=(guard.copy() if shared else register_cast(source[row,d],palette,guard,cast_scale)
           if action=='overhead_cast' else curate.register(source[row,d],palette))
    frame.save(OUT/'frames'/f'{action}-{direction}-{row}.png');sheet.paste(frame,(d*80,row*80))
    a=np.asarray(frame);assert set(np.unique(a[:,:,3]))<={0,255}
    assert frame.getbbox()
    assert not(a[0,:,3].any() or a[-1,:,3].any() or a[:,0,3].any() or a[:,-1,3].any())
    records.append({'action':action,'direction':direction,'phase':row,'sharedGuard':shared,
                    'file':f'frames/{action}-{direction}-{row}.png','source':path.name,
                    'sharedLowerBody':action=='overhead_cast','atlasRect':[d*80,atlas_y+row*80,80,80]})
   frame=Image.open(OUT/'frames'/f'{action}-south-{row}.png').resize((160,160),Image.Resampling.NEAREST)
   contact.paste(frame,(row*170,ai*194+20),frame)
   draw.text((row*170+10,ai*194+180),labels[row],fill='#dce5d3')
  draw.text((10,ai*194+5),title,fill='white')
  sheet.save(OUT/f'{action}.png');combined.paste(sheet,(0,atlas_y));atlas_y+=count*80
  recipes.append({'id':action,'name':title,'sheet':action+'.png','labels':labels,'durations':timings,
                  'frameCount':count,'revision':'simple-hands-v3' if action=='overhead_cast' else 'v1',
                  'previewTravel':[0,0,7,3] if action=='dash_strike' else [0]*count})
 combined.save(OUT/'orc-special-moves.png');contact.save(OUT/'front-contact-sheet.png')
 manifest={'status':'2d_drawing_review_not_game_integrated','cellSize':80,'directions':curate.DIRECTIONS,
           'recipes':recipes,'frames':records,'palette':palette.tolist(),'bodyOnly':True,
           'approved64FramesUnchanged':True,'newFrameCells':len(records),
           'sources':{p.name:digest(p) for p in (OUT/'drawings').glob('*.png')},
           'note':'3D was declined. This pack uses only the newly drawn 2D sheets; timing and dash travel are preview values.'}
 (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 (OUT/'catalog.js').write_text('window.ORC_SPECIALS='+json.dumps(manifest)+';\n')
 assert before=={p.name:digest(p) for p in (APPROVED/'frames').glob('*.png')}
 print(f'Built four 2D move sheets / {len(records)} cells. Original 64 approved cells unchanged.')

if __name__=='__main__':main()
