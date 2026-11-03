"""Small-range Elf body articulation; all parts retain their native pixels."""
import math
import numpy as np
from PIL import Image


def point(transform,xy):
    return transform[:2,:2]@np.asarray(xy)+transform[:2,2]


def pivot(origin,target,degrees):
    a=math.radians(degrees);c,s=math.cos(a),math.sin(a)
    out=np.array([[c,-s,0.],[s,c,0.],[0.,0.,1.]])
    out[:2,2]=np.asarray(target)-out[:2,:2]@np.asarray(origin)
    return out


def pose(F,frame,profile,art,root,warp,matrix,solve):
    """Return posed body pieces and the parent matrix for shoulders/equipment.

    Ankle targets follow only the root, so knees absorb the pelvis shift.
    Side far-leg artwork is the existing inferred Elf component, not new art.
    """
    active=frame not in (0,7)
    sign=1 if F in 'SE' else -1
    lean=[0,-3,-6,-2,7,5,2,0][frame]*sign
    hip_dx=[0,-.5,-.5,0,.75,.5,0,0][frame]*sign
    crouch=[0,.5,1,.5,.5,.5,0,0][frame]
    delta=np.asarray(root,float)+[hip_dx,crouch]
    waist=np.asarray(profile['waist'],float)
    torso=pivot(waist,waist+delta,lean)
    pelvis=pivot(waist,waist+delta,0)
    neck=np.asarray(profile['neck'],float)
    head=pivot(neck,point(torso,neck),lean*.3)
    pieces={};legs={}
    for side,joints in profile['legs'].items():
        hip,knee,ankle=map(lambda p:np.asarray(p,float),joints)
        target_hip=hip+delta;target_ankle=ankle+root
        upper=float(np.linalg.norm(knee-hip));lower=float(np.linalg.norm(ankle-knee))
        a,b=ankle-hip,knee-hip
        cross=a[0]*b[1]-a[1]*b[0]
        bend=1 if cross>0 else -1
        solved_knee,solved_ankle=solve(target_hip,target_ankle,upper,lower,bend)
        transforms=[matrix(hip,knee,target_hip,solved_knee),matrix(knee,ankle,solved_knee,solved_ankle),pivot(ankle,solved_ankle,0)]
        for suffix,transform in zip(['Thigh','Shin','Foot'],transforms):
            key=side+suffix;pieces[key]=warp(art[key],transform)
        legs[side]={'hip':target_hip.tolist(),'knee':solved_knee.tolist(),'ankle':solved_ankle.tolist(),
                    'ankleTarget':target_ankle.tolist(),'upperLength':upper,'lowerLength':lower}
    pieces['pelvis']=warp(art['pelvis'],pelvis)
    pieces['torso']=warp(art['torso'],torso)
    pieces['head']=warp(art['head'],head)
    near=profile['nearLeg'];far='left' if near=='right' else 'right'
    order=[side+part for side in [far,near] for part in ['Thigh','Shin','Foot']]+['pelvis','torso','head']
    out=Image.new('RGBA',(128,128))
    for key in order:out.alpha_composite(pieces[key])
    meta={'active':active,'torsoAngle':math.radians(lean),'torsoMatrix':torso.tolist(),
          'waist':point(torso,waist).tolist(),'neck':point(torso,neck).tolist(),
          'pelvisOffset':delta.tolist(),'legs':legs,'partOrder':order}
    return out,torso,meta,pieces
