"""Inventory all DMI states and stage lossless inputs for full-atlas redraws."""
from pathlib import Path
from PIL import Image
import json,re,shutil
HERE=Path(__file__).resolve().parent
SOURCE=HERE.parents[1]/'remastered/game/Icons/Remastered/Races64'
REF=HERE.parent/'goa-races-lotr-v1.png'

def inspect(path):
 im=Image.open(path); text=im.info['Description']; head=text.split('state =',1)[0]
 def n(block,key,default):
  m=re.search(r'^\s*'+key+r'\s*=\s*(\d+)',block,re.M);return int(m[1]) if m else default
 width,height=n(head,'width',32),n(head,'height',32);offset=0;states=[];seen={}
 for block in re.split(r'(?=^state\s*=)',text,flags=re.M)[1:]:
  name=re.search(r'^state\s*=\s*"(.*?)"',block,re.M)[1]
  dirs,frames=n(block,'dirs',1),n(block,'frames',1)
  delay=re.search(r'^\s*delay\s*=\s*([\d., ]+)',block,re.M)
  occurrence=seen.get(name,0);seen[name]=occurrence+1
  states.append(dict(name=name,occurrence=occurrence,offset=offset,dirs=dirs,frames=frames,
   delays=[float(x) for x in delay[1].split(',')] if delay else [1]*frames,
   movement=n(block,'movement',0),rewind=n(block,'rewind',0),loop=n(block,'loop',0)))
  offset+=dirs*frames
 return dict(name=path.stem,source=str(path),width=width,height=height,columns=im.width//width,rows=im.height//height,
  imageSize=list(im.size),cellCount=offset,states=states,description=text,duplicateStates=[s for s,c in seen.items() if c>1])

def main():
 records=[]
 for path in sorted(SOURCE.glob('*.dmi')):
  item=inspect(path);folder=HERE/'jobs'/path.stem;folder.mkdir(parents=True,exist_ok=True)
  shutil.copyfile(path,folder/'input.png')
  (folder/'source.json').write_text(json.dumps(item,indent=2))
  prompt=f'''Use case: style-transfer. Image 1 is the edit target: a complete {item['name']} game sprite atlas with {item['columns']} columns and {item['rows']} rows. Image 2 is ONLY the approved GOA style reference. Redraw every occupied cell while preserving the exact source grid, each sprite's facing, anatomy, skin colors, limb availability and pose. This includes limb loss: an arm or leg absent in a source cell MUST remain absent. Never restore missing limbs. Match the compact GOA body proportions, large readable head, strong black outlines and richly clustered pixel shading of the approved reference. Keep the same character identity, size and registration throughout all cells. The sheet has {item['cellCount']} occupied source cells; remaining trailing cells must stay transparent. Preserve all distinct walking, armed, sleep, sneaking, tail and flying poses present. Keep source horns, tails, wings and racial features; do not invent them when absent. Do not add poses, characters, text, borders, backgrounds, checkerboards or shadows. Every full sprite stays inside its original cell. Transparent background. Prefer a high-resolution image with the same aspect ratio and exact grid. Pixel-art game dolls, no graphic gore. This is one atlas, not a contact sheet of different character designs.'''
  (folder/'prompt.txt').write_text(prompt)
  item['folder']=str(folder);item['status']='pending_redraw';records.append(item)
 summary=dict(sheets=len(records),cells=sum(r['cellCount'] for r in records),states=sum(len(r['states']) for r in records),
  halfDemonSheets=sum(any(r['name'].endswith('-'+s) for s in ['Marked','Ashen','Hellblooded','Possessed1','Possessed2']) for r in records),
  notes=['Source metadata preserved verbatim, including duplicate state names; duplicate occurrences remain distinct.',
  'Pending means artwork is not converted. Existing walk-only redraws do not satisfy full-state coverage.'],sheetsData=records)
 (HERE/'coverage.json').write_text(json.dumps(summary,indent=2))
 print(json.dumps({k:v for k,v in summary.items() if k!='sheetsData'}))
if __name__=='__main__': main()
