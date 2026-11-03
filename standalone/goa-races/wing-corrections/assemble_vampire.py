"""Replace only the approved north tile; retain the other three RGBA tiles exactly."""
from pathlib import Path
from PIL import Image
import json,shutil
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent
source=ROOT/'hybrids/references/Vampire-approved-flight.png'
im=Image.open(source).convert('RGBA');size=im.height;assert im.width==size*4
north=Image.open(HERE/'Vampire-north-approved.png').convert('RGBA')
def bounds(img):return img.getchannel('A').point(lambda a:255 if a>128 else 0).getbbox()
old=im.crop((size,0,size*2,size));target=bounds(old);region=bounds(north)
tile=Image.new('RGBA',(size,size));tile.paste(north.crop(region).resize((target[2]-target[0],target[3]-target[1]),Image.Resampling.NEAREST),(target[0],target[1]))
out=im.copy();out.paste(tile,(size,0))
for d in [0,2,3]:assert out.crop((d*size,0,(d+1)*size,size)).tobytes()==im.crop((d*size,0,(d+1)*size,size)).tobytes()
output=HERE/'Vampire-flight-approved-north-fixed.png';out.save(output)
sample=ROOT.parents[1]/'Dungeon Master Sample';shutil.copyfile(output,sample/'GOA Vampire Flight - North Fixed.png')
(HERE/'vampire-verification.json').write_text(json.dumps(dict(changed_direction='North',unchanged_directions=['South','East','West'],unchanged_rgba_verified=True,source=str(source),corrected_north=str(HERE/'Vampire-north-approved.png'),frames_per_direction=1,note='Approved appearance row. Complete flying animation remains separate work.'),indent=2))
print(output)
