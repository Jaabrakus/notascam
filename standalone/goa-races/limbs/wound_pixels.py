"""Tiny original-palette wound caps, separate from literal body/limb pixels.

The underlying approved source, pixel partitions, and pure detached parts remain
unchanged. A cap is a maximum4-pixel overlay at a visible part/core cut contact.
No image generation, reskinning, smoothing, dilation of anatomy or gore painting.
"""
import numpy as np
from PIL import Image

SLOTS=('LeftArm','RightArm','LeftLeg','RightLeg')
# Exact opaque colors measured from original Icons/Blood.dmi and Human wounds.
DARK_RIM=(50,4,2,255)   # #320402
DEEP_RED=(167,0,0,255)  # #a70000
MID_RED=(189,0,0,255)   # #bd0000
BRIGHT_RED=(211,0,0,255) # #d30000
PALETTE=(DARK_RIM,DEEP_RED,MID_RED,BRIGHT_RED)
MAX_PIXELS_PER_CAP=4
QUALITY_FLAGS=('wound_seam_geometry_draft','visible_cut_contact_only')


def _neighbors(mask):
 pad=np.pad(mask,1)
 return pad[:-2,1:-1]|pad[2:,1:-1]|pad[1:-1,:-2]|pad[1:-1,2:]


def _empty():
 return Image.new('RGBA',(64,64))


def _bloodless(body):
 race=str(body.get('raceKey',body.get('race',''))).lower().replace(' ','')
 material=str(body.get('material','')).lower()
 return race.startswith('gargoyle') or race=='skeleton' or material in ('stone','bone')


def _select_contact(removed,remaining):
 # Prefer a cut whose original body continues immediately above it: this is the
 # joint/upper end of the removed visible forearm or lower leg, not its fingertip.
 above=np.zeros_like(remaining);above[1:]=remaining[:-1]
 candidates=removed&above
 if not candidates.any():candidates=removed&_neighbors(remaining)
 if not candidates.any():return []
 ys,xs=np.nonzero(candidates);y=int(ys.min())
 row=sorted(int(x) for x in xs[ys==y])
 # At a narrow joint, disconnected outline ends may form separate contacts.
 # Keep one connected horizontal run; never bridge transparent space with red.
 runs=[];run=[]
 for x in row:
  if run and x>run[-1]+1:runs.append(run);run=[]
  run.append(x)
 if run:runs.append(run)
 center=float(np.nonzero(removed)[1].mean())
 run=max(runs,key=lambda r:(len(r),-abs(sum(r)/len(r)-center)))
 if len(run)>MAX_PIXELS_PER_CAP:
  start=max(0,min(len(run)-MAX_PIXELS_PER_CAP,round(center-run[0])-MAX_PIXELS_PER_CAP//2))
  run=run[start:start+MAX_PIXELS_PER_CAP]
 return [(x,y) for x in run]


def wound_overlays(original,split,body,frame,view):
 """Return four independent64pxRGBA wound overlays; never mutate inputs.

 Empty/occluded cuts stay empty. Gargoyles and skeletons have no red caps.
 Vampires retain static wound-red art (their no-drip gameplay rule is separate).
 The mask calibration determines seam anatomy; callers should retain
 QUALITY_FLAGS alongside their geometry review status.
 """
 if original.size!=(64,64):raise ValueError('Expected canonical64px original cell')
 result={slot:_empty() for slot in SLOTS}
 if _bloodless(body):return result
 rgba=np.asarray(original.convert('RGBA'));visible=rgba[...,3]>=128
 masks={slot:np.asarray(split['masks'][slot])>0 for slot in SLOTS}
 union=np.zeros((64,64),bool)
 for mask in masks.values():union|=mask
 # A cap must contact retained body pixels, not another detached limb.
 remaining=visible&~union
 for slot in SLOTS:
  removed=masks[slot]&visible
  if not removed.any():continue
  points=_select_contact(removed,remaining)
  if not points:continue
  pixels=np.zeros((64,64,4),np.uint8)
  # A deep-red seam with a bright red pixel and a small dark edge mirrors the
  # source's deliberately tiny hard-edged clusters. No smooth or oval caps.
  colors={1:[DEEP_RED],2:[DEEP_RED,BRIGHT_RED],
          3:[DARK_RIM,DEEP_RED,BRIGHT_RED],
          4:[DARK_RIM,DEEP_RED,MID_RED,BRIGHT_RED]}[len(points)]
  for (x,y),color in zip(points,colors):pixels[y,x]=color
  result[slot]=Image.fromarray(pixels,'RGBA')
 return result
