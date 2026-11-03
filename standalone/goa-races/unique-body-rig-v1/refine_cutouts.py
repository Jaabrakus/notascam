"""Clean rig cut edges using the existing AI-completed anatomy as backing art.

Original assets remain untouched. Render layers may replace cut-boundary pixels;
preserving those boundaries was leaving squared ends and scraps on moving limbs.
"""
from PIL import Image,ImageDraw
from complete_surfaces import TORSO_POLYGONS,BODY_BOXES,segment_distance

def clean_islands(image):
    out=image.copy();seen=set()
    for y in range(out.height):
        for x in range(out.width):
            if out.getpixel((x,y))[3]<128:out.putpixel((x,y),(0,0,0,0))
    for y in range(out.height):
        for x in range(out.width):
            if (x,y) in seen or not out.getpixel((x,y))[3]:continue
            todo=[(x,y)];seen.add((x,y));part=[]
            while todo:
                u,v=todo.pop();part.append((u,v))
                for nx,ny in [(u+i,v+j) for i,j in [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(1,1),(-1,1),(1,-1)]]:
                    if 0<=nx<out.width and 0<=ny<out.height and (nx,ny) not in seen and out.getpixel((nx,ny))[3]:
                        seen.add((nx,ny));todo.append((nx,ny))
            if len(part)<4:
                for u,v in part:out.putpixel((u,v),(0,0,0,0))
    return out

def repair_torso(image,d,completion):
    out=image.copy();mask=Image.new('L',(64,64));ImageDraw.Draw(mask).polygon(TORSO_POLYGONS[d],fill=255)
    gen=completion.cell(d,0);box=BODY_BOXES[d]
    # No arm-shaped leftovers or straight mask cuts can survive outside this
    # complete torso silhouette. Retain the source shorts/legs below the waist.
    for y in range(43):
        for x in range(64):
            if not mask.getpixel((x,y)):out.putpixel((x,y),(0,0,0,0));continue
            pixel=out.getpixel((x,y))
            shoulder_edge=(d<2 and y<=32 and (x<27 or x>36))
            if pixel[3]<128 or shoulder_edge:
                out.putpixel((x,y),completion.sample(gen,(x-box[0])*gen.width/(box[2]-box[0]),(y-box[1])*gen.height/(box[3]-box[1])))
    return clean_islands(out)

def repair_arm(image,d,side,part,joints,completion):
    gen=completion.cell(d,1 if side=='right' else 2)
    skin_rows={}
    for y in range(gen.height):
        row=[]
        for x in range(gen.width):
            r,g,b,a=gen.getpixel((x,y))
            if a>=128 and r>g*1.05 and g>b*1.05 and b>45:row.append((r,g,b))
        if row:skin_rows[y]=row
    assert skin_rows
    shoulder,elbow,hand=joints
    a,b=(shoulder,elbow) if part=='upper' else (elbow,hand)
    out=Image.new('RGBA',(64,64))
    radius=2.9 if part=='upper' else 2.8
    outline=completion.color((65,35,24))
    for y in range(64):
        for x in range(64):
            distance=segment_distance(x,y,a,b)
            if distance>radius:continue
            # Rounded, complete caps at both ends. No flat scanline split.
            cap=min((x-a[0])**2+(y-a[1])**2,(x-b[0])**2+(y-b[1])**2)<=10
            u,v=(shoulder,elbow) if y<elbow[1] else (elbow,hand)
            t=max(0,min(1,(y-u[1])/max(1,v[1]-u[1])))
            cx=u[0]+t*(v[0]-u[0])
            pixel=image.getpixel((x,y))
            red,green,blue,alpha=pixel
            if alpha>=128 and not cap and distance<radius-.8 and red>green*1.05 and green>blue*1.05 and blue>45:
                out.putpixel((x,y),pixel)
            else:
                # Sample the skin inside the completed limb, avoiding the old
                # cut's dark edge. The silhouette is the capsule boundary.
                sy=(y-(shoulder[1]-3))*gen.height/(hand[1]+4-(shoulder[1]-3))
                row=skin_rows[min(skin_rows,key=lambda v:abs(v-sy))]
                # Use the occupied skin span of this row, not the rectangular
                # component bounds (which include the old arm's silhouette).
                u=max(.08,min(.92,(x-cx+4)/8))
                out.putpixel((x,y),completion.color(row[round(u*(len(row)-1))]))
            # Keep the one-pixel outer contour; do not draw the old horizontal
            # cut outline across a shoulder or elbow connection.
            dx,dy=b[0]-a[0],b[1]-a[1]
            along=((x-a[0])*dx+(y-a[1])*dy)/max(1,dx*dx+dy*dy)
            exterior=(.18<along<.82) or (part=='lower' and along>=.82)
            if distance>radius-.65 and exterior:out.putpixel((x,y),outline)
    return clean_islands(out)

def source_arm(image,part,joints):
    """Retain approved arm/hand pixels; shorten the seven-row elbow overlap.

    Uses the registered completion layer (original artwork + hidden additions),
    not the synthetic capsule repaint from v4. Hands keep their real silhouette.
    """
    out=clean_islands(image)
    shoulder,elbow,hand=joints
    for y in range(64):
        for x in range(64):
            if (part=='upper' and y>elbow[1]+1) or (part=='lower' and y<elbow[1]-1):
                out.putpixel((x,y),(0,0,0,0))
    skin=set()
    for y in range(64):
        for x in range(64):
            red,green,blue,alpha=out.getpixel((x,y))
            if alpha>=128 and red>green*1.05 and green>blue*1.05 and blue>35:skin.add((x,y))
    # Retain a single-pixel source outline, not connected dark scraps from the
    # torso/shorts caught by the original broad arm selection.
    for y in range(64):
        for x in range(64):
            if out.getpixel((x,y))[3] and not any((x+dx,y+dy) in skin for dx in [-1,0,1] for dy in [-1,0,1]):
                out.putpixel((x,y),(0,0,0,0))
    return clean_islands(out)

def walk_body(upper_source,raw,d,frame):
    """Preserve the original walking pelvis/legs as one anatomical layer.

    The approved Elf's hands end above row 48. All pixels from row 48 down are
    copied exactly; the shorts above it are selected by material within the
    pelvis bounds, with occluded shorts backed from that same source row.
    """
    lower=Image.new('RGBA',(64,64));mask=Image.new('L',(64,64))
    waist=40 if frame==2 else 41
    for y in range(waist,48):
        # Keep arm outlines out of the shorts selection. These bounds describe
        # this Elf's pelvis, widening below its waistband, not the whole sprite.
        left,right=((25,39) if y<=41 else (23,40)) if d<2 else ((29,39) if y<=41 else (28,40))
        candidates=[]
        for x in range(left,right+1):
            r,g,b,a=raw.getpixel((x,y))
            if a>=128 and max(r,g,b)<110 and max(r,g,b)-min(r,g,b)<27:candidates.append(x)
        if len(candidates)<4:continue
        for x in range(min(candidates),max(candidates)+1):
            pixel=raw.getpixel((x,y));r,g,b,a=pixel
            if a<128 or max(r,g,b)>=110 or max(r,g,b)-min(r,g,b)>=27:
                pixel=raw.getpixel((min(candidates,key=lambda p:abs(p-x)),y))
            lower.putpixel((x,y),pixel);mask.putpixel((x,y),255)
    for y in range(48,64):
        for x in range(64):
            pixel=raw.getpixel((x,y));lower.putpixel((x,y),pixel)
            if pixel[3]:mask.putpixel((x,y),255)
    upper=upper_source.copy()
    for y in range(64):
        for x in range(64):
            r,g,b,a=upper.getpixel((x,y))
            if y>=43:upper.putpixel((x,y),(0,0,0,0))
    body=Image.new('RGBA',(64,64))
    body.alpha_composite(upper,(0,-1 if frame else 0))
    # Paste source pixels directly, preserving their alpha and foot placement.
    for y in range(64):
        for x in range(64):
            if mask.getpixel((x,y)):body.putpixel((x,y),lower.getpixel((x,y)))
    return body,lower,mask
