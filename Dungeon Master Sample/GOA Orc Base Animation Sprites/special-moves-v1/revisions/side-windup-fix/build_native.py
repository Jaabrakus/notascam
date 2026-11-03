"""Export only the two revised overhead side windups, using original feet."""
from pathlib import Path
import importlib.util
import numpy as np
from PIL import Image, ImageDraw

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
spec=importlib.util.spec_from_file_location('curate',ROOT/'standalone/goa-races/character-retarget/curate_orc_attacks.py')
curate=importlib.util.module_from_spec(spec);spec.loader.exec_module(curate)
palette=curate.palette_from_original().astype(np.int32)
source=Image.open(HERE/'drawn-side-poses.png').convert('RGBA')

def eye(image):
 a=np.asarray(image).astype(int)
 y,x=np.where((a[:,:,0]>120)&(a[:,:,1]<45)&(a[:,:,3]>150))
 return np.array([x.mean(),y.mean()])

preview=Image.new('RGB',(960,268),'#444951');draw=ImageDraw.Draw(preview)
for i,direction in enumerate(['east','west']):
 raw=source.crop((i*source.width//2,0,(i+1)*source.width//2,source.height))
 a=np.asarray(raw);y,x=np.where(a[:,:,3]>200)
 raw=raw.crop((int(x.min()),int(y.min()),int(x.max())+1,int(y.max())+1))
 old=Image.open(HERE/f'original-{direction}-native.png').convert('RGBA')
 old_eye=eye(old);raw_eye=eye(raw)
 scale=(old.getbbox()[3]-old_eye[1])/(raw.height-raw_eye[1])
 raw=raw.resize((round(raw.width*scale),round(raw.height*scale)),Image.Resampling.NEAREST)
 a=np.asarray(raw).copy()
 nearest=((a[:,:,:3].astype(np.int32)[:,:,None]-palette[None,None])**2).sum(3).argmin(2)
 a[:,:,:3]=palette[nearest];a[:,:,3]=np.where(a[:,:,3]>200,255,0);a[a[:,:,3]==0,:3]=0
 raw=Image.fromarray(a);offset=np.rint(old_eye-eye(raw)).astype(int)
 frame=Image.new('RGBA',(80,80));frame.paste(raw,tuple(offset))
 frame.paste(old.crop((0,56,80,80)),(0,56))
 frame.save(HERE/f'{direction}-native.png')
 assert np.array_equal(np.asarray(frame)[56:],np.asarray(old)[56:])
 for j,image in enumerate([old,frame]):
  x=i*480+j*240;large=image.resize((240,240),Image.Resampling.NEAREST)
  preview.paste(large,(x,28),large)
  draw.text((x+10,8),direction+' '+('before' if j==0 else 'after'),fill='white')
preview.save(HERE/'comparison.png')
print('Built only east and west side-windup replacements.')
