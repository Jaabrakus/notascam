"""Export every ordered Human equipment state, preserving decoded cell RGBA."""
import hashlib
import json
from pathlib import Path
import re
from PIL import Image
from validate_dmi import load_asset

BASE=Path(__file__).resolve().parents[1]
ROOT=BASE.parents[2]
OUT=BASE/'players-gear/faithful/equipment'
NATIVE=ROOT/'standalone/remastered/game/Icons/Remastered/Gear64/Human'
PROCESSED=BASE/'players-gear/processed/Gear64/Human'
META=BASE/'_meta/faithful-equipment-batch.json'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rgba_sha(im):return hashlib.sha256(im.tobytes()).hexdigest()
queue=json.loads((BASE/'_meta/players-gear-queue.json').read_text())
baselines={e['source_relative_path']:e['source_sha256'] for e in queue['files']}
families=sorted(Path(e['source_relative_path']).stem for e in queue['files'] if '/Gear64/Human/' in e['source_relative_path'])
if len(families)!=19:raise ValueError('Expected nineteen material families')
report=dict(schema_version=1,worker_model='gpt-6.1-sol',status='in_progress',
    scope='Every ordered equipment state: first occupied facing/frame, not every animation frame',
    primary_method='localenhancement',new_artwork_generated=False,runtime_installed=False,
    held_redesign_candidates_preserved=True,families={},approved_sheet_extractions={},
    limitations=['Processed native art is a local lighting enhancement, not an AI redraw.',
       'Each state supplies one facing/frame only; original complete animations remain in processed DMI.',
       'Existing sheet extractions, when available, are separate optional assets with retained RGB and native-height resize.'])
total=0;empty=0
for family in families:
    old_path=NATIVE/(family+'.dmi');new_path=PROCESSED/(family+'.dmi')
    old_sha=sha(old_path);new_sha=sha(new_path)
    if old_sha!=baselines[str(old_path.relative_to(ROOT))]:raise ValueError('Original changed '+family)
    old=load_asset(old_path.read_bytes());new=load_asset(new_path.read_bytes())
    if old.description!=new.description:raise ValueError('Metadata differs')
    if old.image.getchannel('A').tobytes()!=new.image.getchannel('A').tobytes():raise ValueError('Alpha differs')
    w,h=old.metadata.width,old.metadata.height;cols=old.image.width//w
    output_dir=OUT/family/'catalog';output_dir.mkdir(parents=True,exist_ok=True)
    states=[]
    for i,state in enumerate(old.metadata.states):
        used=state.directions*state.frames;cell=state.start_cell
        for offset in range(used):
            trial=state.start_cell+offset;x=(trial%cols)*w;y=(trial//cols)*h
            if old.image.getchannel('A').crop((x,y,x+w,y+h)).getbbox():cell=trial;break
        x=(cell%cols)*w;y=(cell//cols)*h;box=(x,y,x+w,y+h)
        original_cell=old.image.crop(box);processed_cell=new.image.crop(box)
        bbox=original_cell.getchannel('A').getbbox();new_bbox=processed_cell.getchannel('A').getbbox()
        name=json.loads(state.name);slug=re.sub(r'[^A-Za-z0-9._-]+','-',name).strip('-') or 'unnamed'
        output=output_dir/(f'{i:03d}-'+slug+'.png')
        if output.exists():raise ValueError('Refusing overwrite '+str(output))
        processed_cell.save(output)
        with Image.open(output) as check:decoded=check.convert('RGBA')
        exact=decoded.tobytes()==processed_cell.tobytes()
        height=(bbox[3]-bbox[1]) if bbox else 0
        if not exact or bbox!=new_bbox:raise ValueError('Pixel or height mismatch')
        states.append(dict(state_index=i,state_name=name,state_name_raw=state.name,state_fields=state.fields,
           state_start_cell=state.start_cell,directions=state.directions,frames=state.frames,
           selected_cell=cell,selected_cell_offset=cell-state.start_cell,
           selected_frame=(cell-state.start_cell)//state.directions,
           selected_direction_index=(cell-state.start_cell)%state.directions,
           selected_direction=('S','N','E','W','SE','SW','NE','NW')[(cell-state.start_cell)%state.directions],
           source_box=list(box),source='localenhancement',intentional_empty=bbox is None,
           native_alpha_bbox=list(bbox) if bbox else None,original_visible_height=height,
           processed_visible_height=height,output_visible_height=height,output_size=[w,h],
           output=str(output),output_sha256=sha(output),output_rgba_sha256=rgba_sha(decoded),
           processed_cell_rgba_sha256=rgba_sha(processed_cell),decoded_rgba_exact=True,
           alpha_exact=True,native_placement_exact=True))
        total+=1;empty+=int(bbox is None)
    family_report=dict(status='complete_all_ordered_states',source='localenhancement',
       original_native=str(old_path),original_native_sha256=old_sha,
       processed_source=str(new_path),processed_source_sha256=new_sha,
       exact_description=True,state_count=len(states),exported_count=len(states),
       state_indices_complete=[s['state_index'] for s in states]==list(range(len(old.metadata.states))),
       source_hashes_unchanged=sha(old_path)==old_sha and sha(new_path)==new_sha,
       all_rgba_exact=all(s['decoded_rgba_exact'] for s in states),states=states)
    report['families'][family]=family_report
    report['counts']=dict(complete_families=len(report['families']),exported_states=total,intentional_empty_states=empty)
    META.write_text(json.dumps(report,indent=2)+'\n')
    print(f'{family}: {len(states)} states exported',flush=True)
report['status']='all_19_local_catalogs_complete_existing_sheet_extractions_pending'
report['passed']=len(report['families'])==19 and all(f['state_indices_complete'] and f['source_hashes_unchanged'] and f['all_rgba_exact'] for f in report['families'].values())
META.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report['counts']))
