"""Literal, reversible pixel partitions of canonical approved body sprites.

Only nearest-neighbor sampling and boolean pixel masks are used. Parts retain the
rendered original RGBA values, including partial alpha. No art is synthesized.
Mask geometry is a calibration draft: a flat image cannot reveal hidden limbs.
"""
from functools import lru_cache
from pathlib import Path
import json
import re
import numpy as np
from PIL import Image, ImageDraw

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
SOURCE=ROOT/'standalone/remastered/game/Icons/Remastered/Races64'
SLOTS=('LeftArm','RightArm','LeftLeg','RightLeg')
CALIBRATIONS={}

@lru_cache(maxsize=128)
def _image(path):
 return Image.open(path).convert('RGBA')


def render_body(body_descriptor):
 """Render fixed64px body space with the armory's scale/feet convention.

 Dest pixel centers select one unmodified sourceRGBA pixel. The same scale is
 used for every frame and facing, derived from the registry's maximum box height.
 """
 body=body_descriptor;source=np.asarray(_image(str(body['source'])))
 all_bounds=[b for row in body['frameBounds'] for b in row if b]
 scale=float(body['targetHeight'])/max(b[3]-b[1] for b in all_bounds)
 out=[]
 for frame,rects in enumerate(body['sourceRects']):
  row=[]
  for view,rect in enumerate(rects):
   box=body['frameBounds'][frame][view];w,h=box[2]-box[0],box[3]-box[1]
   dx=32-w*scale/2;dy=61-h*scale
   yy,xx=np.mgrid[:64,:64];sx=np.floor((xx+.5-dx)/scale).astype(int);sy=np.floor((yy+.5-dy)/scale).astype(int)
   inside=(sx>=0)&(sy>=0)&(sx<w)&(sy<h)
   pixels=np.zeros((64,64,4),np.uint8)
   pixels[inside]=source[rect[1]+box[1]+sy[inside],rect[0]+box[0]+sx[inside]]
   row.append(Image.fromarray(pixels,'RGBA'))
  out.append(row)
 return out


def _polygon(points):
 image=Image.new('L',(64,64));ImageDraw.Draw(image).polygon(points,fill=255)
 return np.asarray(image)>0


def _mask_points(body,frame,view):
 """Cell-space calibration override, keyed bodyid/frame/view/slot.

 A descriptor may carry pixelCutter.polygons[frame][view] or callers can populate
 module CALIBRATIONS[(bodyid,frame,view)] with absolute64px polygons. Supplied
 polygons are exact partition boundaries, not alpha or color replacements.
 """
 direct=CALIBRATIONS.get((body['id'],frame,view))
 if direct is not None:return direct
 config=body.get('pixelCutter',{}).get('polygons')
 if config:
  try:return config[frame][view]
  except (IndexError,KeyError,TypeError):pass
 return None


def split_frame(cell,body_descriptor,frame_index,view):
 """Return cell-aligned core and four disjoint original-pixel parts.

 Geometry will be calibrated per race/pose. A 0px occluded part stays empty;
 hidden art is never copied, mirrored, shifted or painted into existence.
 """
 if cell.size!=(64,64):raise ValueError('Expected canonical64x64 body cell')
 body=body_descriptor;rgba=np.asarray(cell.convert('RGBA'));alpha=rgba[...,3]>0
 supplied=_mask_points(body,frame_index,view)
 polygons=supplied if supplied is not None else _draft_polygons(rgba,body,frame_index,view)
 assigned=np.zeros((64,64),bool);parts={};masks={};flags=[]
 for slot in SLOTS:
  points=polygons.get(slot,[])
  mask=(_polygon(points) if len(points)>=3 else np.zeros((64,64),bool))&alpha&~assigned
  if slot.endswith('Arm'):
   hair=_protected_hair(rgba,body)
   if (mask&hair).any():flags.append('hair_pixels_retained_in_core_'+slot)
   mask &= ~hair
  assigned|=mask;part=np.zeros_like(rgba);part[mask]=rgba[mask]
  parts[slot]=Image.fromarray(part,'RGBA');masks[slot]=Image.fromarray(mask.astype(np.uint8)*255,'L')
  if not mask.any():flags.append('occluded_or_empty_'+slot)
 core=np.array(rgba,copy=True);core[assigned]=0
 return dict(core=Image.fromarray(core,'RGBA'),parts=parts,masks=masks,
  method='literal_rgba_polygon_partition_v1',qualityFlags=['geometry_calibration_draft','hidden_art_unavailable']+flags)


def _protected_hair(rgba,body):
 """Conservative race-specific hair exclusion, never repainting a pixel.

 Silver neutral pixels are distinguishable from blue DarkElf skin. Blond hair
 uses yellow hues, while peach Elf skin is more orange/red. Dark outline/hair
 boundary ambiguity remains part of the visible calibration draft.
 """
 rgb=rgba[...,:3].astype(float);r,g,b=rgb[...,0],rgb[...,1],rgb[...,2]
 maximum=rgb.max(2);minimum=rgb.min(2);delta=maximum-minimum
 race=body.get('raceKey','')
 if race=='Night Elf':
  selected=(maximum>=45)&(delta<=np.maximum(18,maximum*.18))
  return _include_hair_outline(selected,maximum)
 if race=='Elf':
  safe=np.maximum(delta,1);h=np.zeros(delta.shape,float)
  red=(maximum==r)&(delta>0);green=(maximum==g)&~red&(delta>0);blue=(delta>0)&~red&~green
  h[red]=((g[red]-b[red])/safe[red])%6
  h[green]=(b[green]-r[green])/safe[green]+2
  h[blue]=(r[blue]-g[blue])/safe[blue]+4
  h/=6
  saturation=delta/np.maximum(maximum,1)
  selected=((maximum>=60)&(delta>=20)&(h>=.105)&(h<=.20))|((maximum>=30)&(saturation>=.65)&(h>=.072)&(h<=.20))
  return _include_hair_outline(selected,maximum)
 return np.zeros(delta.shape,bool)


def _include_hair_outline(selected,maximum):
 # Keep dark1px boundaries attached to the hair rather than to a cut arm.
 padded=np.pad(selected,1);near=np.zeros_like(selected)
 for dy in range(3):
  for dx in range(3):near|=padded[dy:dy+64,dx:dx+64]
 return selected|(near&(maximum<50))

def _draft_polygons(rgba,body,frame,view):
 # Anatomical-left/right ownership, explicitly calibrated on approved Human f0.
 # Other templates scale these cell-space boundaries as a visible geometry draft.
 # No hidden arm is fabricated when a side-facing torso occludes it.
 front_right=[(20,33),(23,33),(24,36),(24,39),(23,43),(23,47),(14,47),(14,35)]
 front_left=[(64-x,y) for x,y in front_right]
 right_leg=[(15,52),(31,52),(32,63),(15,63)]
 left_leg=[(32,52),(49,52),(49,63),(32,63)]
 if view==0:
  result=dict(LeftArm=front_left,RightArm=front_right,LeftLeg=left_leg,RightLeg=right_leg)
 elif view==1:
  result=dict(LeftArm=front_right,RightArm=front_left,LeftLeg=right_leg,RightLeg=left_leg)
 elif view==2:
  result=dict(LeftArm=[],RightArm=[(22,34),(27,34),(28,38),(30,41),(30,46),(27,50),(20,50),(20,36)],
   LeftLeg=[(35,50),(43,50),(43,63),(35,63),(32,57)],
   RightLeg=[(21,50),(34,50),(39,63),(21,63)])
 else:
  result=dict(LeftArm=[(42,34),(37,34),(36,38),(34,41),(34,46),(37,50),(44,50),(44,36)],RightArm=[],
   LeftLeg=[(30,50),(43,50),(43,63),(25,63)],
   RightLeg=[(21,50),(29,50),(32,57),(29,63),(21,63)])
 height=float(body['targetHeight'])
 # Explicit template scaling preserves short-body builds without touching RGBA.
 # A variant with horns/tail/wings may need its own calibration; it is flagged.
 factor=height/56.0
 return {slot:[(32+(x-32)*factor,61+(y-61)*factor) for x,y in points]
         for slot,points in result.items()}


def reconstruction(split):
 """Recombine by disjoint ownership, avoiding alpha-over rounding."""
 output=np.array(split['core'],copy=True)
 for slot in SLOTS:
  mask=np.asarray(split['masks'][slot])>0;part=np.asarray(split['parts'][slot]);output[mask]=part[mask]
 return Image.fromarray(output,'RGBA')


def verify_partition(original,split):
 masks=np.stack([np.asarray(split['masks'][s])>0 for s in SLOTS])
 return dict(disjoint=bool((masks.sum(0)<=1).all()),
  exactReconstruction=bool(np.array_equal(np.asarray(original),np.asarray(reconstruction(split)))),
  originalRgbaPreserved=all(np.array_equal(np.asarray(split['parts'][s])[masks[i]],np.asarray(original)[masks[i]]) for i,s in enumerate(SLOTS)))
