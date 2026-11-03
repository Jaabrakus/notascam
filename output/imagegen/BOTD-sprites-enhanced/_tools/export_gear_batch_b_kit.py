"""Mechanical kit split and original-height export. No artwork creation."""
import hashlib
import json
from pathlib import Path
import shutil
import sys
from PIL import Image
from export_sprite_height import export_height

BASE = Path(__file__).resolve().parents[1]
family, generated_path = sys.argv[1:]
meta = BASE / '_meta/players-gear-ai-batch-b.json'
report = json.loads(meta.read_text())
entry = report['families'][family]
source = BASE / 'players-gear/source-art/gear' / family
dest = BASE / 'players-gear/ai-designs/gear' / family
original = source / 'kit-original.png'
kit = dest / 'kit.png'
if original.exists() or kit.exists(): raise ValueError('Refusing to overwrite kit')
shutil.copyfile(generated_path, original);shutil.copyfile(generated_path, kit)
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
with Image.open(original) as im:
    image = im.convert('RGBA')
if image.getchannel('A').getextrema()[0] != 0: raise ValueError('No true transparent background')
w,h=image.size
if w%2 or h%2: raise ValueError('Uneven kit quadrant dimensions')
exports=[]
for ref in entry['selected']:
    i=ref['quadrant'];x=(i%2)*(w//2);y=(i//2)*(h//2)
    box=[x,y,x+w//2,y+h//2]
    crop=image.crop(box)
    # Explicit main-alpha rectangle may omit alpha=1 fringe specks only.
    # No retained pixel is altered, and the discarded range is audited below.
    main=crop.getchannel('A').point([0,0]+[255]*254).getbbox()
    full=crop.getchannel('A').getbbox()
    if main is None: raise ValueError('Empty kit quadrant')
    hist=crop.getchannel('A').histogram();kept=crop.crop(main).getchannel('A').histogram()
    discarded=[a-b for a,b in zip(hist,kept)]
    if sum(discarded[2:]): raise ValueError('Would discard substantive alpha')
    quadrant=source/(ref['slug']+'-quadrant.png')
    crop.save(quadrant)
    output=dest/(ref['slug']+'.png')
    export_report=export_height(quadrant,output,native_source=ref['path'],cell_index=ref['cell_index'],source_crop=main,method='lanczos')
    r=json.loads(export_report.read_text())
    if not r['output']['visible_height_matches_reference']: raise ValueError('Height failure')
    exports.append(dict(state_name=ref['state_name'],state_occurrence_index=ref['state_occurrence_index'],
        native_cell_index=ref['cell_index'],direction=ref['direction'],native_visible_height=ref['visible_height'],
        quadrant_box=box,quadrant_source=str(quadrant),source_crop=list(main),full_alpha_bbox=list(full),
        discarded_alpha1_pixels=sum(discarded[1:]),discarded_max_alpha=max((j for j,v in enumerate(discarded) if v and j),default=0),
        output=str(output),output_sha256=sha(output),report=str(export_report),
        actual_visible_height=r['placement']['actual_visible_height'],actual_canvas_size=r['output']['size'],
        native_source_sha256=r['native_reference']['sha256']))
entry.update(status='four_base_designs_exported_pending_independent_review',generated_tool_output=str(Path(generated_path).resolve()),
    highres_original=str(original),highres_kit=str(kit),highres_sha256=sha(original),highres_size=list(image.size),
    true_transparency=True,outputs=exports,image_generation_calls=1,
    self_review=dict(identity=True,four_distinct_objects=True,no_text=True,no_character_body=True,
       clear_gutters=True,original_visible_heights_exact=True,originals_unchanged=True,
       provisional=True,note='High-resolution and native-height visual inspection required after mechanical export.'))
report['status']='in_progress'
report['completed_kits']=sum(bool(v['outputs']) for v in report['families'].values())
report['completed_height_matched_items']=sum(len(v['outputs']) for v in report['families'].values())
meta.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'family':family,'completed_kits':report['completed_kits'],'exports':exports},indent=2))
