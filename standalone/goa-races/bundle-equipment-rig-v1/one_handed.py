"""Shared one-handed swing, with per-item art/grips/timing rather than new bodies."""
import math,json
from pathlib import Path
import numpy as np
from PIL import Image

# Read the actual Human animation's authored grips and blade directions.
REFERENCE=Path(__file__).resolve().parents[3]/'Dungeon Master Sample/Sprites/Combat/Human/Human-sword-actions.json'
HUMAN=json.loads(REFERENCE.read_text())
CLIP={'name':'one_handed_swing','reference':str(REFERENCE),
      'phases':['hold','hop_back','wind_up','hop_forward','strike','follow_through','recovery','hold'],
      'frameDurationsMs':[360,85,85,150,70,70,160,80],
      'events':[{'frame':4,'name':'strike'}],
      'scope':'Human one-hand sweep retargeted onto the approved Elf arm rig. Shared cutting/blunt motion; other weapon families use separate clips.'}

PROFILES=[
 ('sword','Arming sword','melee-weapons/weapon.arming_sword','Sword',30,14,8,1.),
 ('hand_axe','Hand axe','melee-weapons/weapon.hand_axe','Hand_Axe',25,17,10,1.15),
 ('mace','Mace','melee-weapons/weapon.mace','Mace',27,14,9,1.15),
 ('warhammer','Warhammer','melee-weapons/weapon.warhammer','Warhammer',25,20,11,1.25),
 ('scimitar','Scimitar','melee-weapons/weapon.scimitar','Scimitar',30,14,9,.95),
 ('dagger','Dagger','melee-weapons/weapon.dagger','Dagger',22,9,6,.75),
 ('goa_sword','GOA sword','melee-weapons/goa.sword','GOA_Sword',30,14,9,1.),
 ('rune_sword','Rune sword','enchanted-weapons/weapon.rune_sword','Rune_Sword',32,14,9,1.),
 ('flame_sword','Flame sword','enchanted-weapons/weapon.flame_sword','Flame_Sword',32,16,10,1.),
]

def load_weapons(root,save,sources):
    catalog={};art={}
    for ident,label,path,slug,height,front,side,speed in PROFILES:
        profile={'label':label,'slug':slug,'durationMultiplier':speed,'motion':'one_handed_swing','facings':{}}
        art[ident]={}
        for d,F in enumerate('SNEW'):
            source=root/path/(['South','North','East','West'][d]+'.png');sources.append(source)
            im=Image.open(source).convert('RGBA').resize((front if d<2 else side,height),Image.Resampling.NEAREST)
            if ident=='sword':grip=[im.width//2,24]
            else:
                # Handle cross-section at 82% of the image height. This also
                # handles the off-center axe shaft and angled scimitar grip.
                y=round((height-1)*.82);xs=[x for x in range(im.width) if im.getpixel((x,y))[3]>=128]
                assert xs,(ident,F,'handle row is empty');grip=[xs[len(xs)//2],y]
            filename=save(im,f'weapons/{ident}/{F}.png')
            art[ident][F]=(im,grip)
            profile['facings'][F]={'image':filename,'grip':grip,'size':list(im.size),'source':str(source)}
        catalog[ident]=profile
    return catalog,art

def root_offset(F,frame):
    """Pixel-snapped anticipation/advance from the Human clip, shared by all layers."""
    forward=[0,-.75,-1.5,0,1.5,1,.5,0][frame]
    lift=[0,2,0,2.2,0,0,.4,0][frame]
    projection=np.asarray(HUMAN['rootMotion']['forwardProjection']['SNEW'.index(F)])
    return np.rint(projection*forward-[0,lift]).astype(int)

def swing_pose(F,frame,shoulder,reach,hold):
    """Retarget Human grip keyposes in the shared native 64px coordinate space.

    IK in the builder preserves the Elf's actual limb lengths. Approved hold
    endpoints are kept; the intermediate sweep comes from the Human sheet.
    """
    if frame in [0,7]:return np.asarray(hold,float),0.
    d='SNEW'.index(F)
    poses=[np.asarray(HUMAN['grips'][r][d]['weapon'],float) for r in range(4)]
    # Undo the root movement here: caller adds it to the entire rig together.
    shift=root_offset(F,frame)
    neutral=np.asarray(hold,float)-shift
    targets=[neutral,neutral*.45+poses[1]*.55,poses[1],poses[1],
             poses[2],poses[2]*.65+poses[3]*.35,poses[3],neutral]
    angles=[math.atan2(v[d][0],-v[d][1]) for v in HUMAN['sweepVectors']]
    base=math.radians({'S':-10,'N':10,'E':14,'W':-14}[F])
    def blend(a,b,t):return a+math.atan2(math.sin(b-a),math.cos(b-a))*t
    orientation=[base,blend(base,angles[1],.55),angles[1],angles[1],angles[2],
                 blend(angles[2],angles[3],.35),angles[3],base][frame]
    return targets[frame]+shift,orientation-base

def weapon_orientation(F,pitch):
    base=math.radians({'S':-10,'N':10,'E':14,'W':-14}[F])
    # Human's front/back attack is a lateral diagonal sweep, not an end-on
    # shrinking blade. Preserve a readable full-length weapon in all facings.
    return base+pitch,1.
