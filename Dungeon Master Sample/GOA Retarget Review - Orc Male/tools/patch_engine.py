#!/usr/bin/env python3
"""Profile-gated additions to the approved Human renderer for the Orc package. Each change is a literal text
replacement on source/engine.js; the script stops if an anchor is not found exactly once, so the approved file
cannot drift. With both flags off the renderer behaves exactly as the approved Human's.

bowSideBody: the side-view bow clips use the body's own East/West drawing instead of the South body with a side
head on top. West draws the far (right) arm, which holds the bow, behind the torso and the near (left) arm, which
draws the string, in front; East stays the exact reflection of West. The drawing arm bends its elbow down in front
of the chest (on the South body it bent upward across the chest) and is not foreshortened toward the camera.

frontHeadOnTop: in the South view the head is drawn over an arm (and the gear it holds) whose hand is raised more than
4 px (or the given number) above the neck, so a weapon wound up overhead passes behind the head instead of over the
face; arms below that line, such as a slash crossing the body, are still drawn over the head (not in the bow).

armPose: a per-view entry {lift, spread, drop} in the profile adjusts the arm targets that come from the keyed arm
angles (the shared clip data): lift scales how far a posed hand rises above its shoulder, spread pushes a raised hand
outward in the front/back views (by that much per pixel of rise), drop lowers a posed hand by that many pixels. The
adjustment fades in and out with the pose, so rest, guard and walk are unchanged.

sideHeadOnTop: in the East/West views (not the bow, not the drawn idle/walk frames) the head is drawn after the near
arm, so an arm reaching forward at shoulder height passes under the jaw instead of over the face. The Orc's
shoulders sit level with its jaw and its snout reaches as far forward as its arm.

closePinholes: after each frame is drawn, a transparent pixel with body on both sides horizontally and vertically
(within two pixels) takes a neighbour's colour (the darkest when two or more neighbours are outline). Separately
rotated pieces leave such one-pixel seams where they meet; real gaps (an armpit slit, the space between the legs)
stay open because they are not enclosed both ways.

frontLegsSquash: wherever the front or back body is drawn (front/back views, and the East/West bow, which uses
the front body) a stepping or crouching leg keeps its knee on the hip-ankle line and
both leg pieces shorten along it (foreshortening, as a leg bending toward the camera looks), instead of the knee
buckling sideways. The Orc's shorts legs are 12-14 px wide and 8 px long; buckled sideways they tore apart.
"""
import sys

CHANGES = [
    # bowSideBody
    ("const bodyDirection=clip.mode==='bow'&&d>=2?(d===2?1:0):d,",
     "const bodyDirection=clip.mode==='bow'&&d>=2&&!this.data.bowSideBody?(d===2?1:0):d,"),
    ("if(p.d===3){const a=p.arms.left,reach=Math.min(a.lowerLength*.9,Math.max(2,(a.shoulder[0]-a.hand[0])*.55)),levelElbow=[a.hand[0]+reach,a.hand[1]];this.projectArm(p,'left',V.mix(a.elbow,levelElbow,raise),a.hand);}",
     "if(p.d===3&&!this.data.bowSideBody){const a=p.arms.left,reach=Math.min(a.lowerLength*.9,Math.max(2,(a.shoulder[0]-a.hand[0])*.55)),levelElbow=[a.hand[0]+reach,a.hand[1]];this.projectArm(p,'left',V.mix(a.elbow,levelElbow,raise),a.hand);}"),
    ("bend=side===drawSide&&p.d>=2?(p.d===2?-1:1):",
     "bend=side===drawSide&&p.d>=2?((p.d===2)!==!!this.data.bowSideBody?-1:1):"),
    ("p.d===3&&side===drawSide?1-raise+raise*Math.min(1,",
     "p.d===3&&side===drawSide&&!this.data.bowSideBody?1-raise+raise*Math.min(1,"),
    ("else if(p.bow&&d===3){arm('left');}",
     "else if(p.bow&&d===3){arm(this.data.bowSideBody?'right':'left');}"),
    ("if(p.bow&&d>=2){if(d===3){arm('left');arm('right');}}",
     "if(p.bow&&d>=2){if(d===3){arm('left');if(!this.data.bowSideBody)arm('right');}}"),
    # frontLegsSquash
    ("const bend=d===2?-1:d===3?1:hip[0]<32?1:-1,[knee,ankle]=ik(hip,target,A,B,bend);",
     "const bend=d===2?-1:d===3?1:hip[0]<32?1:-1,squash=!!this.data.frontLegsSquash&&bodyDirection<2,[knee,ankle]=squash?this.squashLeg(hip,target,A,B):ik(hip,target,A,B,bend);"),
    ("result.legs[name]={hip,knee,ankle,target,upperLength:A,lowerLength:B};",
     "result.legs[name]={hip,knee,ankle,target,upperLength:A,lowerLength:B};if(squash){result.parts[name+'Thigh'].foreshortened=true;result.parts[name+'Shin'].foreshortened=true;}"),
    # sideHeadOnTop
    ("this.part(ctx,'pelvis',p);this.part(ctx,'torso',p);this.part(ctx,'head',p);}",
     "this.part(ctx,'pelvis',p);this.part(ctx,'torso',p);if(!((this.data.sideHeadOnTop&&d>=2||this.data.frontHeadOnTop&&d===0)&&!p.bow))this.part(ctx,'head',p);}"),
    ("else if(d===2){arm('right');weapon();}else if(d===3){arm('left');shield();}",
     "else if(d===2){arm('right');weapon();}else if(d===3){arm('left');shield();}if(this.data.sideHeadOnTop&&d>=2&&!p.bow&&!p.drawnBody)this.part(ctx,'head',p);"),
    ("else if(d===0){arm('left');shield();arm('right');weapon();}",
     "else if(d===0){if(this.data.frontHeadOnTop&&!p.bow){const lift=+this.data.frontHeadOnTop===1?4:+this.data.frontHeadOnTop,up=k=>p.arms[k]&&p.arms[k].hand[1]<p.neck[1]-lift,"
     "L=()=>{arm('left');shield();},R=()=>{arm('right');weapon();};if(up('left'))L();if(up('right'))R();if(!p.drawnBody)this.part(ctx,'head',p);if(!up('left'))L();if(!up('right'))R();}"
     "else{arm('left');shield();arm('right');weapon();}}"),
    # armPose: per-view adjustment of arm targets from the keyed arm angles (lift scales the rise above the shoulder,
    # spread pushes a raised hand outward in front/back views, drop lowers the posed hand), faded in with the pose
    ("target=V.add(V.add(shoulder,q),V.sub(tp(base),V.add(shoulder,restQ)).map(x=>x*(1-weight)));",
     "target=V.add(V.add(shoulder,q),V.sub(tp(base),V.add(shoulder,restQ)).map(x=>x*(1-weight)));"
     "const pa=this.data.armPose&&this.data.armPose[d];if(pa){const up=Math.max(0,shoulder[1]-target[1]);"
     "target=[target[0]+(d<2?Math.sign(s[0]-32)*(pa.spread||0)*up:0),target[1]+up*(1-(pa.lift??1))+(pa.drop||0)*weight];}"),
    # closePinholes
    ("ctx.lineTo(...p.neck);ctx.stroke();}\n  ctx.restore();return p;\n }\n times(id){",
     "ctx.lineTo(...p.neck);ctx.stroke();}\n  ctx.restore();if(this.data.closePinholes)this.closeHoles(ctx);return p;\n }\n"
     " closeHoles(ctx){const W=ctx.canvas.width,H=ctx.canvas.height,img=ctx.getImageData(0,0,W,H),d=img.data,solid=i=>d[i+3]>=128,lum=i=>d[i]+d[i+1]+d[i+2],fill=[];"
     "for(let y=2;y<H-2;y++)for(let x=2;x<W-2;x++){const i=(y*W+x)*4;if(solid(i))continue;"
     "const h=(solid(i-4)||solid(i-8))&&(solid(i+4)||solid(i+8)),v=(solid(i-4*W)||solid(i-8*W))&&(solid(i+4*W)||solid(i+8*W));if(!h||!v)continue;"
     "const nb=[i-4,i+4,i-4*W,i+4*W].filter(solid);if(nb.length<2)continue;const dk=nb.filter(j=>lum(j)<150),lt=nb.filter(j=>lum(j)>=150);"
     "fill.push([i,dk.length>=2||!lt.length?dk.reduce((a,b)=>lum(a)<lum(b)?a:b,nb[0]):lt[0]]);}"
     "for(const [i,j] of fill){d[i]=d[j];d[i+1]=d[j+1];d[i+2]=d[j+2];d[i+3]=d[j+3];}if(fill.length)ctx.putImageData(img,0,0);}\n"
     " times(id){"),
    (" projectArm(p,side,elbow,hand){",
     " squashLeg(hip,target,A,B){const v=V.sub(target,hip),n=V.len(v),dist=Math.min(n,A+B-.001),u=n>1e-6?v.map(x=>x/n):[0,1];return [V.add(hip,u.map(x=>x*dist*A/(A+B))),V.add(hip,u.map(x=>x*dist))];}\n projectArm(p,side,elbow,hand){"),
]


def main(path):
    src = open(path).read()
    for old, new in CHANGES:
        if src.count(old) != 1:
            sys.exit('anchor not found exactly once in %s: %s' % (path, old[:70]))
        src = src.replace(old, new)
    src = src.replace('/* Runtime keyframes retargeted onto the approved Elf, preserving fixed bone lengths. */',
                      '/* Runtime keyframes retargeted onto the approved Elf, preserving fixed bone lengths. */\n'
                      '/* Orc package: + bowSideBody, sideHeadOnTop, frontHeadOnTop, armPose, frontLegsSquash, closePinholes (profile flags), see tools/patch_engine.py. */', 1)
    open(path, 'w').write(src)
    print('engine patched:', len(CHANGES), 'changes')


if __name__ == '__main__':
    main(sys.argv[1])
