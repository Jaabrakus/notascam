import dmi
from PIL import Image
R='/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Icons/Remastered/'
_cache={}
WARP=None   # optional (picture, facing) -> picture remap applied to every layer (build3d9: races)
def unit(layers, f=0):
    out={}
    for d in 'SNEW':
        im=None
        for fn,st in layers:
            if fn not in _cache: _cache[fn]=dmi.load(R+fn)
            s=_cache[fn][st]; ff=min(f,s['frames']-1); c=dmi.frame(s,d,ff)
            if WARP is not None: c=WARP(c,d)
            if im is None: im=Image.new('RGBA',c.size,(0,0,0,0))
            im.alpha_composite(c)
        out[d]=im
    return out
H='Gear64/Human/'
KNIGHT=[('Races64/Human.dmi',''),(H+'iron.dmi','legs.plate.iron'),(H+'iron.dmi','chest.plate.iron'),(H+'old-Hair.dmi','HumanBrown'),
 (H+'iron.dmi','arms.plate.iron.L'),(H+'iron.dmi','arms.plate.iron.R'),(H+'iron.dmi','helmet.nasal.iron'),(H+'iron.dmi','shield.heater.iron'),(H+'iron.dmi','weapon.longsword.iron')]
PEASANT=[('Races64/Human.dmi',''),(H+'leather.dmi',None),(H+'old-Hair.dmi','HumanBrown')]
