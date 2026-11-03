import sys,json,hashlib,shutil
from pathlib import Path
from PIL import Image
B=Path(__file__).resolve().parents[2]
f,num,generated=sys.argv[1:4];num=int(num);plan=json.load(open(B/'detailed-artwork/production-plan.json'));page=next(x for x in plan['missing_families'][f]['pages'] if x['page']==num);out=Path(page['target']);out.parent.mkdir(parents=True,exist_ok=True)
if out.exists():raise ValueError('refusing overwrite')
shutil.copy2(generated,out);prompt=B/'_meta/prompts'/f'detailed-{f}-page-{num:02}.txt'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
record={'page':num,'status':'generated_pending_visual_review','source_reference':page['source_reference'],'source_sha256':sha(page['source_reference']),'style_reference':str(B/'Gear/bonehide.png'),'style_sha256':sha(B/'Gear/bonehide.png'),'prompt':str(prompt),'prompt_sha256':sha(prompt),'output':str(out),'output_sha256':sha(out),'original_tool_output':generated,'dimensions':list(Image.open(out).size),'expected_visible_cells':page['expected_visible_cells'],'observed_visible_cells':None,'rows':page['rows'],'builtin_image_tool':True,'external_api':False,'native_height_export':False,'artwork_redrawn':True,'runtime_installed':False}
rp=B/'detailed-artwork/reports'/(f+'.json');r=json.load(open(rp));r['pages'].append(record);rp.write_text(json.dumps(r,indent=2)+'\n');print(str(out))
