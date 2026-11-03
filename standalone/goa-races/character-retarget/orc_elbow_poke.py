"""Extract drawn elbow key poses and copy only the weapon-arm pixels."""
import json
import numpy as np
from PIL import Image, ImageDraw, ImageOps

HANDS = [
    [(27,53),(27,53),(25,55),(27,53)],
    [(54,53),(54,54),(54,50),(54,53)],
    [(43,54),(41,54),(49,53),(43,54)],
    [(30,54),(32,54),(24,53),(30,54)],
]

def drawn_frames(out):
    im=Image.open(out/'drawings/elbow-poke.png').convert('RGBA')
    a=np.asarray(im);rows=np.where((a[:,:,3]>200).sum(1)>15)[0]
    groups=np.split(rows,np.where(np.diff(rows)>8)[0]+1)
    bands=[(int(g[0]),int(g[-1])+1) for g in groups]
    assert len(bands)==4
    scale=43/(bands[0][1]-bands[0][0])
    old=np.asarray(Image.open(out/'revisions/before-elbow-poke/frames/body-east-0.png').convert('RGBA'))
    colors=np.unique(old[old[:,:,3]>0,:3],axis=0)
    ramp=json.loads((out.parent/'attack-appearance.json').read_text())['skinRamp']
    palette=np.unique(np.concatenate([colors,np.array(ramp)]),axis=0)
    result={}
    for phase,(top,bottom) in enumerate(bands):
        for d in range(4):
            tile=im.crop((d*im.width//4,top,(d+1)*im.width//4,bottom))
            a=np.array(tile);a[:,:,3]=np.where(a[:,:,3]>=200,255,0)
            tile=Image.fromarray(a);tile=tile.crop(tile.getbbox())
            w,h=[round(v*scale) for v in tile.size]
            a=np.array(tile.resize((w,h),Image.Resampling.NEAREST))
            near=((a[:,:,:3].astype(int)[:,:,None]-palette[None,None])**2).sum(3).argmin(2)
            a[:,:,:3]=palette[near];a[a[:,:,3]==0,:3]=0
            hx=np.where(np.asarray(tile)[:60,:,3]>0)[1]
            x=round(40-(hx.min()+hx.max())/2*scale)
            frame=Image.new('RGBA',(80,80));frame.paste(Image.fromarray(a),(x,68-h))
            result[phase,d]=frame
    return result

def east_arm(raw,phase):
    phase=0 if phase==3 else phase
    mask=Image.new('L',(80,80))
    points=([(29,44),(35,44),(39,48),(52,49),(59,49),(60,54),(56,57),(39,57),(31,54)]
        if phase==2 else [(29,44),(37,44),(37,50),(44,50),(47,52),(47,56),(32,57),(29,54)])
    ImageDraw.Draw(mask).polygon(points,fill=255)
    arm=Image.new('RGBA',(80,80));arm.paste(raw[phase,2],(0,0),mask)
    if phase==2:
        # The new strike drawing's straight forearm is six pixels too long.
        # Trim that excess once; ready/strike retain their distinct drawn elbows.
        shortened=Image.new('RGBA',(80,80))
        shortened.paste(arm.crop((0,0,42,80)),(0,0))
        shortened.paste(arm.crop((48,0,80,80)),(42,0))
        arm=shortened
    return arm

def build_bodies(out):
    raw=drawn_frames(out);result={}
    for d,name in enumerate(['south','north','east','west']):
        guard=Image.open(out/'revisions/before-elbow-poke/frames'/f'body-{name}-0.png').convert('RGBA').crop((24,24,104,104))
        for phase in range(4):
            im=guard.copy()
            if d==0:
                box=(18,46,36,58);patch=raw[min(phase,2),d].crop(box)
                if phase==2:
                    shifted=Image.new('RGBA',patch.size);shifted.paste(patch,(3,1));patch=shifted
                im.paste(patch,box[:2])
            elif d==1:
                box=(46,44,63,58);patch=raw[min(phase,2),d].crop(box)
                if phase==2:
                    shifted=Image.new('RGBA',patch.size);shifted.paste(patch,(0,-3));patch=shifted
                im.paste(patch,box[:2])
            elif d==2:
                im.paste((0,0,0,0),(20,43,51,58))
                torso=raw[0,0].crop((36,49,44,56))
                im.paste(torso.resize((17,12),Image.Resampling.NEAREST),(32,46))
                im.alpha_composite(east_arm(raw,phase))
                im.paste(guard.crop((39,43,53,46)),(39,43))
            else:
                # Right weapon arm is on the far side in west. The near left
                # guard arm is copied unchanged over the reflected weapon arm.
                im.paste((0,0,0,0),(18,46,34,58))
                reflected=ImageOps.mirror(east_arm(raw,phase))
                shifted=Image.new('RGBA',(80,80));shifted.paste(reflected,(-7,0))
                im.alpha_composite(shifted)
                im.paste(guard.crop((34,43,80,58)),(34,43))
            im.paste(guard.crop((0,0,80,43)),(0,0))
            im.paste(guard.crop((0,58,80,80)),(0,58))
            if phase==3:im=result[0,d].copy()
            result[phase,d]=im
    return result
