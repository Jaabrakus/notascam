"""Verify actual detailed-art cutout and native-height PNG deliverables."""
from pathlib import Path
import hashlib,json
from PIL import Image
import numpy as np
from validate_dmi import load_asset
from export_sprite_height import native_cell_reference,resize_and_place

BASE=Path(__file__).resolve().parents[1]
ROOT=BASE.parents[2]
ART=BASE/'detailed-artwork'
FAMILIES=['diamond','dragonbone','bonehide','dragonhide','spidersilk','leather','spiderfang','dragonfang','cloth','magic']
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def rgba(p):
    with Image.open(p) as i:return i.convert('RGBA')
manifest=json.loads((ART/'manifest.json').read_text())
plate_hashes={str((ART/v['path']).resolve()):v['sha256'] for v in manifest['gear_pages']}
native_hashes={str((ROOT/v['source_relative_path']).resolve()):v['source_sha256'] for v in json.loads((BASE/'_meta/players-gear-queue.json').read_text())['files']}
result=dict(schema_version=1,worker_model='gpt-6.1-sol',new_artwork_generated=False,runtime_installed=False,
  source='actual_detailed_enhanced_artwork_not_native_fallback',families={},failures=[])
cutouts=heights=nearest=lanczos=0
for f in FAMILIES:
    d=json.loads((ART/'exports/reports'/(f+'.json')).read_text())
    original=load_asset((ROOT/'standalone/remastered/game/Icons/Remastered/Gear'/(f+'.dmi')).read_bytes())
    errors=[]
    if [s['state_index'] for s in d['states']]!=list(range(len(original.metadata.states))):errors.append('Ordered inventory state coverage differs')
    for s in d['states']:
        if json.loads(original.metadata.states[s['state_index']].name)!=s['state_name']:errors.append('State identity differs')
        if sha(s['source_plate'])!=plate_hashes[s['source_plate']]:errors.append('Large detailed source plate changed')
        source=rgba(s['source_plate']).crop(s['crop_box']);cutout=rgba(s['source_cutout'])
        pad=s['extraction'].get('padded_source_offset',[4,4]);middle=np.asarray(cutout.crop((pad[0],pad[1],pad[0]+source.width,pad[1]+source.height)))
        old=np.asarray(source);keep=middle[:,:,3]>0
        if not np.array_equal(middle[:,:,:3],old[:,:,:3]):errors.append('Cutout source RGB differs including hidden pixels')
        for target in ['inventory','player']:
            e=s[target];ref=e['native_reference'];native=Path(ref['path'])
            if sha(native)!=native_hashes[str(native)]:errors.append('Native reference changed')
            actual=native_cell_reference(native,ref['cell_index'])
            if actual['state_name']!=s['state_name']:errors.append('Native state name mismatch')
            out=rgba(e['path']);bbox=out.getchannel('A').getbbox()
            if bbox[3]-bbox[1]!=actual['visible_height'] or bbox[3]!=actual['bottom_baseline_exclusive']:errors.append('Native height or bottom anchor differs')
            if out.height!=actual['frame_size'][1]:errors.append('Native canvas height differs')
            exp=json.loads(Path(e['report']).read_text())
            cropped=cutout.crop(exp['source']['effective_source_crop'])
            rebuilt,_=resize_and_place(cropped,actual['visible_height'],e['resample'],actual)
            if rebuilt.tobytes()!=out.tobytes() or sha(e['path'])!=e['sha256']:errors.append('Mechanical height export/hash differs')
            heights+=1;nearest+=int(e['resample']=='nearest');lanczos+=int(e['resample']=='lanczos')
        cutouts+=1
        if not s['visual_review'].startswith('pass'):errors.append('Visual review incomplete: '+s['state_name'])
    errors=list(dict.fromkeys(errors));result['families'][f]=dict(states=len(d['states']),passed=not errors,failures=errors)
    result['failures'] += [f+': '+x for x in errors]
result['counts']=dict(families=len(FAMILIES),source_cutouts=cutouts,height_exports=heights,nearest_exports=nearest,lanczos_sparse_edge_fallback_exports=lanczos)
result['passed']=not result['failures'] and cutouts==113 and heights==226
result['limitations']=['Alpha-only extraction uses reviewed segmentation; conservative edge residue can remain on some cloth.',
    'Cutouts retain all source RGB before resizing; resizing changes sampled pixels according to the recorded resampler.',
    'Height and bottom anchor match native references; width can vary, and these are not drop-in registered equipment overlays.']
path=ART/'exports/reports/assigned-ten-family-verification.json';path.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'passed':result['passed'],'counts':result['counts'],'failures':result['failures']},indent=2))
