"""Transfer donor skin palettes and identity markings onto the six fixed bodies."""
from PIL import Image,ImageChops
from statistics import median
from heads import light,median_color


def is_mark(c,appearance,tone=None):
    r,g,b,a=c
    if a<160:return False
    name=appearance.lower()
    if name=='marked':return r>135 and g<r*.35 and b<r*.40
    if name=='ashen':return r>140 and 35<g<190 and b<110 and r>g*1.3 and r>b*2
    if name=='zombie':return r>75 and r>g*1.75 and r>b*1.4
    if name=='werewolf' and tone:
        return 18<light(c)<light(tone)*.45 and max(c[:3])-min(c[:3])>8
    return False


def palette(donor,record):
    tile=donor.crop((0,0,64,64));rig=record['rigs'][0][0]
    neck=round(rig['neck']);hip=round(rig['hip']);samples=[]
    def sample(x,y,weight=1):
        if not (0<=x<64 and 0<=y<64):return
        c=tile.getpixel((x,y))
        if c[3]<180 or light(c)<20 or is_mark(c,record['appearance']):return
        if record['appearance'].lower()=='ashen' and (max(c[:3])-min(c[:3])>32 or max(c[:3])>125):return
        samples.extend([c[:3]]*weight)
    # Bare hands and feet are reliable even with long hair and a charcoal top.
    for point in list(rig['hands'].values())+list(rig['feet'].values()):
        px,py=point
        for y in range(round(py)-3,round(py)+1):
            for x in range(round(px)-2,round(px)+3):sample(x,y,2)
    if record['sex']=='male':
        for y in range(neck+3,min(hip-2,60)):
            for x in range(27,38):sample(x,y,3)
    for y in range(neck+5,min(hip,60)):
        for x in list(range(18,24))+list(range(40,46)):sample(x,y)
    if not samples:return dict(mid=[176,139,102],method='fallback',sampleCount=0)
    return dict(mid=list(median_color(samples)),method='One stable body palette from donor torso, hands and feet; identity markings excluded.',sampleCount=len(samples))


def bones(rig):
    hip=rig['hip']
    result={'chest':([32,rig['neck']+2],[32,hip-1])}
    for side in ['right','left']:
        result['arm-'+side]=(rig['shoulders'][side],rig['hands'][side])
        fx,fy=rig['feet'][side]
        result['leg-'+side]=([32+(fx-32)*.4,hip],[fx,fy-2])
    return result


def coordinates(point,start,end):
    vx=end[0]-start[0];vy=end[1]-start[1];length=max(1,vx*vx+vy*vy)
    px=point[0]-start[0];py=point[1]-start[1]
    t=(px*vx+py*vy)/length;u=(-px*vy+py*vx)/length
    clamped=max(0,min(1,t))
    dist=(px-clamped*vx)**2+(py-clamped*vy)**2
    return t,u,dist


def markings(donor_tile,head,record,source_frame,view,target_rig,target_skin,tone):
    result=Image.new('RGBA',(64,64));name=record['appearance']
    if name.lower() not in ['marked','ashen','werewolf','zombie']:return result,0
    source_rig=record['rigs'][source_frame][view]
    src=bones(source_rig);dst=bones(target_rig);pixels={}
    for y in range(max(0,round(source_rig['neck'])),62):
        for x in range(3,61):
            c=donor_tile.getpixel((x,y))
            if head.getpixel((x,y))[3] or not is_mark(c,name,tone):continue
            if name.lower()=='werewolf' and not (26<=x<=37 and source_rig['neck']+4<=y<source_rig['hip']-3):continue
            pixels[x,y]=c
    # Keep each continuous scar/crack together; forward-scattering individual
    # pixels breaks small lines into freckles when body proportions differ.
    remaining=set(pixels);components=[]
    while remaining:
        first=remaining.pop();group=[first];stack=[first]
        while stack:
            px,py=stack.pop()
            for dx,dy in [(a,b) for a in [-1,0,1] for b in [-1,0,1] if a or b]:
                q=(px+dx,py+dy)
                if q in remaining:remaining.remove(q);stack.append(q);group.append(q)
        if len(group)>=2:components.append(group)
    for group in components:
        center=[sum(p[i] for p in group)/len(group) for i in [0,1]]
        key=min(src,key=lambda key:coordinates(center,*src[key])[2])
        a,b=src[key];c,d=dst[key]
        vx=b[0]-a[0];vy=b[1]-a[1];wx=d[0]-c[0];wy=d[1]-c[1];length=max(1,wx*wx+wy*wy)
        aa=(vx*wx+vy*wy)/length;ab=(vx*wy-vy*wx)/length
        ba=(vy*wx-vx*wy)/length;bb=(vy*wy+vx*wx)/length
        patch=Image.new('RGBA',(64,64))
        for point in group:patch.putpixel(point,pixels[point])
        patch=patch.transform((64,64),Image.Transform.AFFINE,(aa,ab,a[0]-aa*c[0]-ab*c[1],ba,bb,a[1]-ba*c[0]-bb*c[1]),resample=Image.Resampling.NEAREST)
        patch.putalpha(ImageChops.multiply(patch.getchannel('A'),target_skin.getchannel('A')))
        result.alpha_composite(patch)
    return result,sum(a>0 for a in result.getchannel('A').getdata())

