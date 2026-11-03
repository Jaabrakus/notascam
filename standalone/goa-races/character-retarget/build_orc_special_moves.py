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
 'overhead_cast':('Overhead cast',['Guard','Raise hands','Release','Follow through'],[180,250,140,180]),
 'ground_slam':('Ground slam',['Guard','Raise fists','Slam','Recover'],[180,200,130,230]),
 'dash_strike':('Dash strike',['Guard','Windup','Strike','Recover'],[180,130,120,220]),
 'stagger':('Hit reaction / stagger',['Guard','Recoil','Stagger','Recover'],[150,120,220,250])}
OVERRIDES={}

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
 (OUT/'frames').mkdir(exist_ok=True)
 before=json.loads((OUT/'approved-frame-hashes.json').read_text())
 assert before=={p.name:digest(p) for p in (APPROVED/'frames').glob('*.png')}
 palette=curate.palette_from_original();records=[];recipes=[]
 combined=Image.new('RGBA',(320,sum(len(v[1]) for v in ACTIONS.values())*80));contact=Image.new('RGB',(680,776),'#444951');draw=ImageDraw.Draw(contact)
 atlas_y=0
 for ai,(action,(title,labels,timings)) in enumerate(ACTIONS.items()):
  path=OUT/'drawings'/f'{action}.png'
  source=curate.extract(path)
  curate.SCALE=.205*1448/Image.open(path).width
  count=len(labels);sheet=Image.new('RGBA',(320,count*80))
  for row in range(count):
   for d,direction in enumerate(curate.DIRECTIONS):
    shared=row==0 or (action=='stagger' and row==3)
    guard=Image.open(APPROVED/'frames'/f'punch_right-{direction}-0.png').convert('RGBA')
    frame=guard.copy() if shared else curate.register(source[row,d],palette)
    override=OVERRIDES.get(f'{action}-{direction}-{row}')
    if override:
     frame=Image.open(OUT/override).convert('RGBA')
     assert frame.size==(80,80)
    frame.save(OUT/'frames'/f'{action}-{direction}-{row}.png');sheet.paste(frame,(d*80,row*80))
    a=np.asarray(frame);assert set(np.unique(a[:,:,3]))<={0,255}
    assert frame.getbbox()
    assert not(a[0,:,3].any() or a[-1,:,3].any() or a[:,0,3].any() or a[:,-1,3].any())
    records.append({'action':action,'direction':direction,'phase':row,'sharedGuard':shared,
                    'file':f'frames/{action}-{direction}-{row}.png','source':path.name,
                    'sharedLowerBody':bool(override),'nativeOverride':override,'atlasRect':[d*80,atlas_y+row*80,80,80]})
   frame=Image.open(OUT/'frames'/f'{action}-south-{row}.png').resize((160,160),Image.Resampling.NEAREST)
   contact.paste(frame,(row*170,ai*194+20),frame)
   draw.text((row*170+10,ai*194+180),labels[row],fill='#dce5d3')
  draw.text((10,ai*194+5),title,fill='white')
  sheet.save(OUT/f'{action}.png');combined.paste(sheet,(0,atlas_y));atlas_y+=count*80
  recipes.append({'id':action,'name':title,'sheet':action+'.png','labels':labels,'durations':timings,
                  'frameCount':count,'revision':'original-cast-restored-final' if action=='overhead_cast' else 'v1',
                  'previewTravel':[0,0,7,3] if action=='dash_strike' else [0]*count})
 combined.save(OUT/'orc-special-moves.png');contact.save(OUT/'front-contact-sheet.png')
 manifest={'status':'2d_drawing_review_not_game_integrated','cellSize':80,'directions':curate.DIRECTIONS,
           'recipes':recipes,'frames':records,'palette':palette.tolist(),'bodyOnly':True,
           'approved64FramesUnchanged':True,'newFrameCells':len(records),
           'sources':{p.name:digest(p) for p in (OUT/'drawings').glob('*.png')},
           'nativeOverrides':{name:{'path':path,'sha256':digest(OUT/path)} for name,path in OVERRIDES.items()},
           'note':'3D was declined. This pack uses only the newly drawn 2D sheets; timing and dash travel are preview values.'}
 curate.annotate_appearance(manifest)
 (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 (OUT/'catalog.js').write_text('window.ORC_SPECIALS='+json.dumps(manifest)+';\n')
 assert before=={p.name:digest(p) for p in (APPROVED/'frames').glob('*.png')}
 print(f'Built four 2D move sheets / {len(records)} cells. Original 64 approved cells unchanged.')

if __name__=='__main__':main()
