"""Native-pixel component preparation for the Elf full-body joint study.

This is an authored Elf profile, not an automatic anatomical recognizer. The
occluded side leg reuses the visible leg with its own registration; it remains
an inferred cutout requiring visual review, not recovered original artwork.
"""
from PIL import Image
from complete_surfaces import segment_distance

LEGS = [
    {'right': [[27,49],[27,54],[26,58]], 'left': [[36,49],[36,54],[37,58]]},
    {'right': [[36,49],[36,54],[37,58]], 'left': [[27,49],[27,54],[26,58]]},
    {'right': [[32,49],[32,53],[31,57]], 'left': [[36,49],[36,53],[35,57]]},
]
PARENTS = {'pelvis':None,'torso':'pelvis','head':'torso'}
for side in ['right','left']:
    PARENTS.update({side+'UpperArm':'torso',side+'Forearm':side+'UpperArm',side+'Hand':side+'Forearm',
                    side+'Thigh':'pelvis',side+'Shin':side+'Thigh',side+'Foot':side+'Shin'})
SLOTS={'helmet':'head','chest':'torso','waist':'pelvis','mainHand':'rightHand','offHand':'leftHand'}
for side in ['right','left']:
    for item,part in [('Shoulder','UpperArm'),('Bracer','Forearm'),('Glove','Hand'),('Greave','Shin'),('Boot','Foot')]:
        SLOTS[side+item]=side+part

def clip(image,predicate):
    out=image.copy()
    for y in range(64):
        for x in range(64):
            if not predicate(x,y):out.putpixel((x,y),(0,0,0,0))
    return out

def prepare(records,out,images,save):
    report=[]
    for d,record in enumerate(records):
        frame=record['frames'][0]
        get=lambda key:Image.open(out/'assets'/frame[key]).convert('RGBA')
        parts={'head':get('render-head')}
        body=get('refined-torso')
        parts['torso']=clip(body,lambda x,y:y<=43)
        parts['pelvis']=clip(get('walk-lower'),lambda x,y:y<=50)
        for side in ['right','left']:
            for part,source in [('UpperArm','upper'),('Forearm','forearm'),('Hand','hand')]:
                parts[side+part]=get(side+'-'+source+'-refined')
        if d<3:
            joints=LEGS[d]
            for side in ['right','left']:
                if d<2:
                    screen_left=(d==0 and side=='right') or (d==1 and side=='left')
                    leg=clip(body,lambda x,y:y>=47 and ((x<=31)==screen_left))
                else:
                    # Authored near-leg outline. The source side silhouette
                    # contains BOTH legs: copying the whole bottom gave each
                    # cutout a second ankle and foot, producing a black mesh.
                    bounds={48:(28,35),49:(28,35),50:(28,35),51:(28,35),52:(28,35),53:(28,34),54:(29,34),55:(29,33),56:(28,34),57:(27,36),58:(27,37),59:(27,38),60:(28,38)}
                    leg=clip(body,lambda x,y:y in bounds and bounds[y][0]<=x<=bounds[y][1])
                    if side=='left':
                        shifted=Image.new('RGBA',(64,64));shifted.alpha_composite(leg,(4,0));leg=shifted
                hip,knee,ankle=joints[side]
                skin=[(x,y,leg.getpixel((x,y))) for y in range(48,62) for x in range(64)
                      if (lambda c:c[3]>=128 and c[0]>c[1]*1.08 and c[1]>c[2]*1.08 and c[2]>40)(leg.getpixel((x,y)))]
                assert skin,(d,side)
                # Shorts belong to the pelvis, not the rotating thigh. Complete
                # the hidden thigh root with its adjacent skin under that hem.
                for y in range(48,51):
                    for x in range(64):
                        if segment_distance(x,y,hip,knee)<=2.5:
                            pixel=min(skin,key=lambda p:(p[0]-x)**2+(p[1]-y)**2)[2]
                            leg.putpixel((x,y),pixel)
                # Complete tiny hidden caps by extending adjacent source skin.
                # No broad rectangular crop edge is used as a joint surface.
                additions=0
                for joint in [hip,knee,ankle]:
                    for dx,dy in [(0,0),(-1,0),(1,0),(0,-1),(0,1)]:
                        x,y=joint[0]+dx,joint[1]+dy
                        if leg.getpixel((x,y))[3]<128:
                            pixel=min(skin,key=lambda p:(p[0]-x)**2+(p[1]-y)**2)[2]
                            leg.putpixel((x,y),pixel);additions+=1
                parts[side+'Thigh']=clip(leg,lambda x,y:y<=knee[1] and segment_distance(x,y,hip,knee)<=3.2)
                parts[side+'Shin']=clip(leg,lambda x,y:knee[1]-1<=y<=ankle[1]-1 and segment_distance(x,y,knee,ankle)<=2.8)
                parts[side+'Foot']=clip(leg,lambda x,y:y>=ankle[1]-1)
                report.append({'facing':record['name'],'side':side,'hiddenCapPixels':additions,'inferredFarLeg':d==2 and side=='left'})
        else:
            east=records[2]['fullBody'];joints={}
            for side,opposite in [('right','left'),('left','right')]:
                joints[side]=[[63-x,y] for x,y in east['legs'][opposite]]
                for part in ['Thigh','Shin','Foot']:
                    parts[side+part]=Image.open(out/'assets'/east['parts'][opposite+part]).transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        record['fullBody']={'parts':{key:save(im,f'{record["name"].lower()}/full-body/{key}.png',images) for key,im in parts.items()},
                            'legs':joints,'waist':[32 if d<2 else (35 if d==2 else 28),42],
                            'neck':[32 if d<2 else (34 if d==2 else 29),25],
                            'nearLeg':'left' if d==3 else 'right'}
        assert set(parts)==set(PARENTS)
    return {'parts':list(PARENTS),'parents':PARENTS,'slots':SLOTS,'preparation':report,
            'status':'Elf articulated component study; far side leg and tiny hidden joint caps are inferred from adjacent source artwork.',
            'profilePolicy':'Shared bone/slot names and motion; unique per-appearance art, proportions, pivots and masks. No automatic race or female body replacement.'}
