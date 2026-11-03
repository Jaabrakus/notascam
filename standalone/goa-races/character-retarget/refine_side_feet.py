"""Review-oriented side-foot cleanup. Writes new assets, preserving source PNGs.
Usage: python3 refine_side_feet.py PACKAGE
"""
import json,sys
from pathlib import Path
from PIL import Image
root=Path(sys.argv[1]).resolve();path=root/'profiles/character.json';p=json.loads(path.read_text());assets=root/'preview/assets'
changes=[]
for d in [2,3]:
 v=p['views'][d];near=v['nearLeg'];far='left' if near=='right' else 'right'
 def source_ankle(side):return v.get('partSource',{}).get(side+'Foot',[v['legs'][side][2]])[0]
 src=Image.open(assets/v['parts'][near+'Foot']).convert('RGBA');a=source_ankle(near);b=source_ankle(far)
 # The foot owns pixels at/below the ankle; calf pixels belong to the shin.
 for y in range(max(0,round(a[1]))):
  for x in range(64):src.putpixel((x,y),(0,0,0,0))
 name=f'side-foot-clean-{d}-{near}.png';src.save(assets/name);v['parts'][near+'Foot']=name
 foot=Image.new('RGBA',(64,64));foot.paste(src,(round(b[0]-a[0]),round(b[1]-a[1])))
 name=f'side-foot-clean-{d}-{far}.png';foot.save(assets/name);v['parts'][far+'Foot']=name
 for side in ['left','right']:
  im=Image.open(assets/v['parts'][side+'Shin']).convert('RGBA');ankle=source_ankle(side)
  # A one-row overlap at the ankle is enough; toes belong exclusively to the foot.
  for y in range(max(0,round(ankle[1])-2),64):
   for x in range(64):
    if y>=round(ankle[1]) or abs(x-ankle[0])>2:im.putpixel((x,y),(0,0,0,0))
  name=f'side-shin-clean-{d}-{side}.png';im.save(assets/name);v['parts'][side+'Shin']=name
 changes.append({'view':v['name'],'footTemplate':near,'alignedFarFoot':far,'ankleOverlapRows':0,'jointBacking':'renderer ankle cap'})
path.write_text(json.dumps(p,indent=2));(root/'side-foot-review.json').write_text(json.dumps({'status':'needs_visual_review','changes':changes},indent=2));print(json.dumps(changes))
