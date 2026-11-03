"""Measured body features and independent attachment points for authored poses."""
import math
from copy import deepcopy
from PIL import Image
LABELS={'human':'Human','human-dark':'Human · dark skin','dwarf':'Dwarf','elf':'Elf','dark-elf':'Dark elf','orc':'Orc','goblin':'Goblin','kobold':'Kobold','vampire':'Vampire','demon':'Demon','gargoyle':'Gargoyle','frogman':'Frogman','lizardman':'Lizardman','devourer-zombie':'Devourer zombie','skeleton':'Skeleton'}


def fit_profile(body, templates):
    race=body['race']
    family='dwarf' if race=='dwarf' else 'goblin' if race in ['goblin','kobold'] else 'human'
    flight='-flying' in body['baseId']
    height=({'vampire':50,'demon':39,'gargoyle':39}.get(race,body['targetHeight']) if flight else body['targetHeight'])
    p=deepcopy(templates[family]);reference={'human':56,'dwarf':46,'goblin':43}[family]
    ratio=height/reference
    p['y']=[61+(y-61)*ratio for y in p['y']]
    p['armY']=[61+(y-61)*ratio for y in p['armY']]
    p['headY']=[[61+(y-61)*ratio for y in ys] for ys in p['headY']]
    if flight:
        for field in ['headWidth','torsoWidth','armWidth','lowerWidth']:p[field]*=height/56
    p['flight']=flight
    p['eyeColor']=({'demon':'yellow','vampire':'red','gargoyle':'white'}.get(race,'all') if flight else 'all')
    if race in ['orc','gargoyle','devourer-zombie','frogman']:
        p['torsoWidth']*=1.12;p['armWidth']*=1.08;p['armSpread']+=.5
    if race in ['elf','dark-elf','skeleton']:
        p['torsoWidth']*=.90;p['armWidth']*=.90
    if body['sex']=='female':
        p['torsoWidth']*=.90;p['armWidth']*=.90;p['headWidth']*=.92
        for index in [1,2,3]:p['y'][index]-=2
        p['y'][4]-=1
        p['armY']=[y-2 for y in p['armY']]
        p['headY']=[[a+1,b-2] for a,b in p['headY']]
    # Helmet crowns always retain a one-pixel canvas margin after the user's nudge.
    p['headY']=[[max(3,a),max(15,b)] for a,b in p['headY']]
    p['family']={'human':'standard','dwarf':'stocky','goblin':'small'}[family]
    return p


def eyes(tile,p,view):
    if view==1:return None
    predicted=p['headY'][view][0]+(16 if view==0 else 14)*(p['headY'][view][1]-p['headY'][view][0])/23
    rows=[]
    radius=14 if p.get('flight') else 6
    for y in range(max(2,round(predicted)-radius),min(53,round(predicted)+radius+1)):
        points=[]
        for x in range(21,44):
            r,g,b,a=tile.getpixel((x,y))
            if a<160:continue
            white=min(r,g,b)>195;yellow=r>140 and g>125 and b<85;red=r>185 and g<100 and b<135
            color=p.get('eyeColor','all')
            if (white if color=='white' else yellow if color=='yellow' else red if color=='red' else white or yellow or red):points.append(x)
        if 0<len(points)<=12:rows.append((abs(y-predicted)+abs(len(points)-5)*.10,y,points))
    if not rows:return None
    _,y,points=min(rows)
    return [sum(points)/len(points),float(y)]


def components(points):
    remaining=set(points);groups=[]
    while remaining:
        first=remaining.pop();stack=[first];group=[first]
        while stack:
            x,y=stack.pop()
            for dx,dy in [(0,1),(0,-1),(1,0),(-1,0),(1,1),(-1,1),(1,-1),(-1,-1)]:
                q=(x+dx,y+dy)
                if q in remaining:remaining.remove(q);stack.append(q);group.append(q)
        groups.append(group)
    return sorted(groups,key=len,reverse=True)


def skin(c):
    r,g,b,a=c
    return a>=160 and ((max(r,g,b)-min(r,g,b)>15 and max(r,g,b)>45) or min(r,g,b)>100)


def measure(tile,p,view,frame):
    alpha=tile.getchannel('A').point(lambda a:255 if a>=128 else 0)
    bounds=alpha.getbbox()
    eye=eyes(tile,p,view)
    expected=p['headY'][view][0]+(16 if view==0 else 14)*(p['headY'][view][1]-p['headY'][view][0])/23
    limit=16 if p.get('flight') else 5
    eye_delta=max(-limit,min(limit,eye[1]-expected)) if eye else 0
    neck=p['y'][1]+eye_delta*.5;hip=p['y'][3]+eye_delta*.15
    shoulders={};hands={}
    for side in ['right','left']:
        if view<2:
            screen=-1 if (side=='right')==(view==0) else 1
            sx=32+screen*(10*p['armWidth']+p['armSpread']);sy=neck+2
            hx=sx;hy=p['armY'][-1]+3
            xrange=(max(2,round(hx)-5),min(62,round(hx)+6))
        else:
            mirror=1 if view==2 else -1
            near=(side=='right')==(view==2)
            sx=32+mirror*(-5 if near else 2);sy=neck+2
            phase=(frame%3)
            hx=32+mirror*((-5 if phase!=2 else 7) if near else (7 if phase!=2 else -5))
            hy=p['armY'][-1]+(0 if phase else 2)
            xrange=(max(2,round(hx)-5),min(62,round(hx)+6))
        candidates=[(x,y) for y in range(max(3,round(hy)-6),min(61,round(hy)+5)) for x in range(*xrange) if skin(tile.getpixel((x,y)))]
        if candidates:
            low=max(y for x,y in candidates);tip=[q for q in candidates if q[1]>=low-2]
            hx=sum(x for x,y in tip)/len(tip);hy=low-1
        shoulders[side]=[sx,sy];hands[side]=[hx,hy]
    # Separate lower-leg silhouettes below the shorts; retain lifted feet.
    start=max(round(hip+2),round((hip+61)/2)-2)
    leg_range=range(22,42) if p.get('flight') else range(6,58)
    pts=[(x,y) for y in range(start,63) for x in leg_range if alpha.getpixel((x,y))]
    groups=[g for g in components(pts) if len(g)>=3]
    if len(groups)<2:
        groups=[[q for q in pts if q[0]<32],[q for q in pts if q[0]>=32]]
    groups=[g for g in groups if g]
    groups=sorted(sorted(groups,key=len,reverse=True)[:2],key=lambda g:sum(x for x,y in g)/len(g))
    feet={}
    for index,side in enumerate(['right','left']):
        if view==1:index=1-index
        elif view>=2:
            near=(side=='right')==(view==2)
            front=near if frame!=2 else not near
            index=(1 if front else 0) if view==2 else (0 if front else 1)
        g=groups[min(index,len(groups)-1)] if groups else [(27 if index==0 else 37,60)]
        bottom=max(y for x,y in g)+1
        tip=[(x,y) for x,y in g if y>=bottom-3]
        cx=(min(x for x,y in tip)+max(x for x,y in tip)+1)/2
        feet[side]=[cx,bottom]
    return dict(eye=eye,eyeDelta=eye_delta,neck=neck,hip=hip,shoulders=shoulders,hands=hands,feet=feet,bounds=list(bounds))


def delta(a,b):
    return [a[0]-b[0],a[1]-b[1]]


def angle(a,b):
    return math.degrees(math.atan2(b[0]-a[0],b[1]-a[1]))


def attachment(part,reference,current):
    dy=current['neck']-reference['neck'];dx=0;rotation=0;pivot=[32,reference['neck']+4]
    if part=='helmet':
        dy=current['eyeDelta'];pivot=[32,reference['neck']-9]
    elif part.startswith(('shoulder','bracer')):
        side=part.rsplit('-',1)[1];s0=reference['shoulders'][side];s=current['shoulders'][side];h0=reference['hands'][side];h=current['hands'][side]
        swing=max(-40,min(40,angle(s,h)-angle(s0,h0)))
        if part.startswith('bracer'):
            dx,dy=delta(h,h0);pivot=[h0[0],h0[1]-3];rotation=-swing
        else:
            dx,dy=delta(s,s0);pivot=s0;rotation=-swing*.20
    elif part.startswith(('boot','greave')):
        side=part.rsplit('-',1)[1];foot0=reference['feet'][side];foot=current['feet'][side]
        if part.startswith('boot'):
            dx,dy=delta(foot,foot0);pivot=[foot0[0],foot0[1]-3]
        else:
            dx=(foot[0]-foot0[0])*.65;dy=(foot[1]-foot0[1])*.65
            pivot=[foot0[0],foot0[1]-8]
            rotation=-max(-35,min(35,angle([32,current['hip']],foot)-angle([32,reference['hip']],foot0)))
    elif part in ['belt','waist-mail-cloth']:
        dy=current['hip']-reference['hip']
    return dx,dy,rotation,pivot


def transform(tile,dx,dy,degrees,pivot):
    if degrees:
        tile=tile.rotate(degrees,resample=Image.Resampling.NEAREST,center=tuple(pivot))
    result=Image.new('RGBA',(64,64));result.paste(tile,(round(dx),round(dy)))
    return result

