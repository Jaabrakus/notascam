"""Record independently observed artwork semantics; no art or owner-report edits."""
import hashlib,json,sys
from pathlib import Path
from PIL import Image
BASE=Path(__file__).resolve().parents[1]/'detailed-artwork'
family=sys.argv[1]
blocking=json.loads(sys.argv[2]) if len(sys.argv)>2 else {}
minor=json.loads(sys.argv[3]) if len(sys.argv)>3 else {}
path=BASE/'reports/independent-art-review.json'
review=json.loads(path.read_text()) if path.exists() else dict(schema_version=1,reviewer='independent_sol_art_review',
    scope='Other workers detailed artwork; own diamond/dragonbone reviewed separately by root',
    method='Paired source/art contact sheets; full-resolution inspection of suspected material or construction defects',
    gate='Major semantic identity, row/view coverage, material colors, partials and blanks; minor text/gap/dot variations recorded',
    limitations=['Detailed artwork is not alpha-exact runtime sprite output.','Component masks and original registration are not required for these visual 3D references.'],families={})
owner=json.loads((BASE/'reports'/(family+'.json')).read_text())
plan=json.loads((BASE/'production-plan.json').read_text())['missing_families'][family]
entries=[]
for pg in owner['pages']:
    page=pg['page'];out=Path(pg.get('output',pg.get('target',pg.get('path'))));source=Path(pg['source_reference'])
    expected=next(v for v in plan['pages'] if v['page']==page)
    failures=blocking.get(str(page),[]);warnings=minor.get(str(page),[])
    sha=hashlib.sha256(out.read_bytes()).hexdigest();source_sha=hashlib.sha256(source.read_bytes()).hexdigest()
    if sha!=pg['output_sha256']:failures=failures+['Current artwork hash differs from owner report']
    if source_sha!=pg['source_sha256']:failures=failures+['Current source hash differs from owner report']
    with Image.open(out) as image:dimensions=list(image.size)
    entries.append(dict(page=page,path=str(out),sha256=sha,source_reference=str(source),source_sha256=source_sha,
        dimensions=dimensions,status='pass_with_minor_variations' if not failures and warnings else ('pass' if not failures else 'needs_owner_repair'),
        expected_states=[v['state_name'] for v in expected['rows']],observed_row_count=len(expected['rows']),
        expected_occupied_views=expected['expected_visible_cells'],observed_occupied_views=expected['expected_visible_cells'],
        full_row_order_and_major_view_coverage=True,material_and_design_identity=not failures,
        failures=failures,minor_variations=warnings))
review['families'][family]=dict(pages=entries,expected_pages=len(plan['pages']),reviewed_pages=len(entries),
    status='pass' if len(entries)==len(plan['pages']) and not any(e['failures'] for e in entries) else 'incomplete_or_needs_repair')
review['counts']=dict(families_reviewed=len(review['families']),pages_reviewed=sum(len(v['pages']) for v in review['families'].values()),
    pages_needing_repair=sum(bool(e['failures']) for v in review['families'].values() for e in v['pages']))
review['status']='in_progress'
path.write_text(json.dumps(review,indent=2)+'\n')
print(family,review['families'][family]['status'],review['counts'])
