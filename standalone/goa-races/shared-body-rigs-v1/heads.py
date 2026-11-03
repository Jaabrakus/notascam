"""Extract unchanged head pixels; placement uses integer translation only."""
from PIL import Image
from statistics import median
import math


def light(c):
    return (c[0]*.2126+c[1]*.7152+c[2]*.0722)


def distance(a,b):
    return sum((a[i]-b[i])**2 for i in range(3))**.5


def median_color(colors,fallback=(176,139,102)):
    if not colors:return fallback
    return tuple(round(median(c[i] for c in colors)) for i in range(3))


def skin_color(tile,cut):
    # Bare lower legs/feet avoid blond or silver hair being mistaken for skin.
    foot_colors=[]
    for y in range(54,61):
        for x in range(15,49):
            r,g,b,a=tile.getpixel((x,y))
            if a>=160 and ((max(r,g,b)-min(r,g,b)>16 and max(r,g,b)>50) or min(r,g,b)>85):foot_colors.append((r,g,b))
    if len(foot_colors)>=5:return median_color(foot_colors)
    colors=[]
    for y in range(min(59,cut+3),min(60,cut+13)):
        for x in list(range(17,26))+list(range(38,47)):
            r,g,b,a=tile.getpixel((x,y))
            if a>=160 and max(r,g,b)>45 and (max(r,g,b)-min(r,g,b)>18 or min(r,g,b)>90):colors.append((r,g,b))
    if not colors:
        colors=[tile.getpixel((x,y))[:3] for y in range(max(1,cut-7),cut-1) for x in range(24,40) if tile.getpixel((x,y))[3]>160 and max(tile.getpixel((x,y))[:3])>65]
    return median_color(colors)


def extract(tile,record,f,v):
    rig=record['rigs'][f][v]
    cut=max(10,min(49,round(rig['neck']-1)))
    head=Image.new('RGBA',(64,64));extras=Image.new('RGBA',(64,64))
    for y in range(cut):
        for x in range(64):head.putpixel((x,y),tile.getpixel((x,y)))
    # Long hair is an identity feature, not part of the shared torso.
    has_hair=record['sex']=='female' or record['race'] in ['elf','dark-elf']
    tone=skin_color(tile,cut)
    if has_hair:
        alpha=tile.getchannel('A').point(lambda a:255 if a>=128 else 0)
        core=alpha.crop((20,0,44,cut)).getbbox()
        if core:
            top=core[1];crown=[]
            for y in range(top,min(cut,top+max(3,(cut-top)//4))):
                for x in range(20,44):
                    c=tile.getpixel((x,y))
                    if c[3]>=160 and max(c[:3])>20:crown.append(c[:3])
            hair=median_color(crown,(45,38,31))
            if distance(hair,tone)>40:
                for y in range(cut,min(61,cut+24)):
                    for x in range(12,52):
                        c=tile.getpixel((x,y))
                        outside_core=abs(x-32)>=6 or v==1
                        if outside_core and c[3] and distance(c[:3],hair)+12<distance(c[:3],tone):
                            head.putpixel((x,y),c)
    # Preserve flight wings behind the new body, and low profile tails separately.
    flying='-flying' in record['fitParent']
    for y in range(64):
        for x in range(64):
            wing=flying and (x<22 or x>=42)
            tail=record['race']=='lizardman' and v>=2 and y>=round(rig['hip']+3) and (x<24 or x>=40)
            if wing or tail:extras.putpixel((x,y),tile.getpixel((x,y)))
    points=[(x,y) for y in range(max(0,cut-3),cut) for x in range(23,41) if tile.getpixel((x,y))[3]>=128]
    cx=(min(x for x,y in points)+max(x for x,y in points)+1)/2 if points else 32
    original_center=round(cx)
    neck_skin=[(x,y) for x,y in points if distance(tile.getpixel((x,y))[:3],tone)<65]
    if neck_skin:
        lowest=max(y for x,y in neck_skin);lowest_row=[x for x,y in neck_skin if y==lowest]
        preferred=round(median(lowest_row))
        cx=max(original_center-2,min(original_center+2,preferred))
    return head,extras,dict(cutY=cut,neck=[round(cx),cut-1],extractionCenter=[original_center,cut-1],skin=list(tone),method='Source RGBA pixels copied without scaling or recoloring; integer attachment translation only.')


def tint(core,tone):
    out=core.copy();pix=out.load()
    for y in range(out.height):
        for x in range(out.width):
            r,g,b,a=pix[x,y]
            if not a:continue
            lum=light((r,g,b))
            # Generated core uses light neutral skin and dark charcoal underwear.
            if lum>=78 and max(r,g,b)-min(r,g,b)<45:
                factor=max(.46,min(1.40,lum/171))
                rgb=tuple(min(255,round(value*factor)) for value in tone)
                pix[x,y]=(*rgb,a)
    return out

