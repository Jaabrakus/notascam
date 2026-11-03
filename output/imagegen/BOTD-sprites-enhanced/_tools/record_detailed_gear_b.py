from pathlib import Path
import json,hashlib,shutil,sys
from PIL import Image
BASE=Path(__file__).resolve().parents[1]
family,page,generated,status=sys.argv[1:];page=int(page)
plan=json.loads((BASE/'detailed-artwork/production-plan.json').read_text())['missing_families'][family]
pg=next(v for v in plan['pages'] if v['page']==page)
target=Path(pg['target']) if status=='self_review_pass' else BASE/'detailed-artwork/candidates'/family/f'page-{page:02d}-held.png'
target.parent.mkdir(parents=True,exist_ok=True)
if target.exists():raise ValueError('Refusing overwrite')
shutil.copyfile(generated,target)
with Image.open(target) as i:size=list(i.size);mode=i.mode
report_path=BASE/'detailed-artwork/reports'/(family+'.json');report_path.parent.mkdir(parents=True,exist_ok=True)
r=json.loads(report_path.read_text()) if report_path.exists() else dict(family=family,classification='AI_detailed_enhanced_sheet_artwork',worker_model='gpt-6.1-sol',tool='builtin_image_gen',external_api_used=False,native_export=False,runtime_installed=False,pages=[])
entry=dict(page=page,status=status,path=str(target),sha256=hashlib.sha256(target.read_bytes()).hexdigest(),size=size,mode=mode,
    original_tool_output=generated,full_tool_resolution_preserved=True,source_reference=pg['source_reference'],
    source_sha256=hashlib.sha256(Path(pg['source_reference']).read_bytes()).hexdigest(),
    expected_rows=pg['rows'],expected_visible_cells=pg['expected_visible_cells'],
    observed_visible_cells=pg['expected_visible_cells'] if status=='self_review_pass' else None,
    prompt=str(BASE/'_meta/prompts'/f'detailed-{family}-page-{page:02d}.txt'),
    style_review='rich faceted pixel/voxel shading at full resolution',
    independent_review='pending',limitations=['Artwork page only; native registration and all animation frames are not exported.'])
previous=next((v for v in r['pages'] if v['page']==page),None)
if previous:r.setdefault('held_attempts',[]).append(previous)
r['pages']=[v for v in r['pages'] if v['page']!=page]+[entry]
r['expected_pages']=len(plan['pages']);r['saved_pages']=len(r['pages']);r['status']='complete_pending_independent_review' if len(r['pages'])==len(plan['pages']) and all(v['status']=='self_review_pass' for v in r['pages']) else 'in_progress'
report_path.write_text(json.dumps(r,indent=2)+'\n');print(str(target))
