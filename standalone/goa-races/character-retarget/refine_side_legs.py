"""Use the clean idle-side leg artwork on independent left/right joints.
Human review correction; inspect on other bodies before adopting.
"""
import json,sys
from pathlib import Path
r=Path(sys.argv[1]);path=r/'profiles/character.json';p=json.loads(path.read_text())
for d,clean,lead in [(2,'left','right')]:
 v=p['views'][d];chain=v['legs'][clean];v['leadLeg']=lead;v['nearLeg']=lead
 for side in ['right','left']:
  for part,i in [('Thigh',0),('Shin',1),('Foot',2)]:
   v['parts'][side+part]=v['parts'][clean+part]
   a=chain[i];b=chain[i+1] if i<2 else [a[0],a[1]+1]
   v.setdefault('partSource',{})[side+part]=[a,b]+(['fit'] if i<2 else [])
# West keeps its original ordering; replace only the spiked far-leg artwork.
v=p['views'][3];chain=v['legs']['right']
for part,i in [('Thigh',0),('Shin',1)]:
 v['parts']['left'+part]=v['parts']['right'+part]
 v.setdefault('partSource',{})['left'+part]=[chain[i],chain[i+1],'fit']
path.write_text(json.dumps(p,indent=2))
