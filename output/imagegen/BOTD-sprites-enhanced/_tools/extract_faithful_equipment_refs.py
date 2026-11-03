"""Explicit reviewed rectangles from existing reference sheets; no new art."""
import hashlib
import json
from pathlib import Path
from extract_existing_sprite import extract
from export_sprite_height import export_height

BASE=Path(__file__).resolve().parents[1]
OUT=BASE/'players-gear/faithful/equipment'
META=BASE/'_meta/faithful-equipment-batch.json'
PLAN={
 'bonehide': [('Gear/bonehide.png',0,[370,65,550,190]),('Gear/bonehide.png',1,[350,350,555,505]),('Gear/bonehide.png',2,[375,630,540,775]),('Gear/bonehide.png',3,[390,860,515,975])],
 'dragonhide': [('Gear/dragonhide.png',0,[370,65,550,190]),('Gear/dragonhide.png',1,[350,340,555,500]),('Gear/dragonhide.png',2,[375,630,540,775]),('Gear/dragonhide.png',3,[390,860,515,975])],
 'spidersilk': [('Gear/spidersilk.png',0,[390,70,535,205]),('Gear/spidersilk.png',1,[350,320,555,500]),('Gear/spidersilk.png',2,[380,630,540,770]),('Gear/spidersilk.png',3,[430,870,535,960])],
 'leather': [('Gear/leather.png',0,[325,50,465,170]),('Gear/leather.png',1,[320,280,465,415]),('Gear/leather.png',2,[320,510,465,635]),('Gear/leather.png',6,[320,1270,465,1415])],
 'spiderfang': [('Gear/spiderfang.png',0,[380,180,540,300]),('Gear/spiderfang.png',1,[380,395,545,560]),('Gear/spiderfang.png',2,[390,635,540,805]),('Gear/spiderfang.png',3,[380,805,535,1085])],
 'dragonfang': [('Gear/dragonfang.png',0,[305,115,400,215]),('Gear/dragonfang.png',1,[305,250,400,380]),('Gear/dragonfang.png',5,[275,935,410,1070]),('Gear/dragonfang.png',7,[285,1260,410,1495])],
 'cloth': [('Gear/cloth/page-01.png',1,[435,185,600,320]),('Gear/cloth/page-01.png',2,[435,325,600,455]),('Gear/cloth/page-01.png',4,[435,600,600,735]),('Gear/cloth/page-01.png',5,[435,740,600,875])],
 'magic': [('Gear/magic/page-01.png',0,[430,75,545,220]),('Gear/magic/page-01.png',2,[430,345,545,495]),('Gear/magic/page-02.png',7,[420,80,555,230]),('Gear/magic/page-02.png',11,[420,760,555,895])],
}
report=json.loads(META.read_text())
for family, selections in PLAN.items():
    results=[]
    catalog=report['families'][family]
    for sheet,stateindex,box in selections:
        native=catalog['states'][stateindex]
        slug=Path(native['output']).stem
        folder=OUT/family/'approved-sheet-art-v2';folder.mkdir(parents=True,exist_ok=True)
        cutout=folder/(slug+'-source-cutout.png')
        audit=extract(BASE/sheet,box,cutout)
        output=folder/(slug+'.png')
        method='nearest'
        try: exp=export_height(cutout,output,native_source=catalog['original_native'],cell_index=native['selected_cell'],method=method)
        except ValueError as error:
            if 'Resizing lost sparse' not in str(error):raise
            method='lanczos'
            exp=export_height(cutout,output,native_source=catalog['original_native'],cell_index=native['selected_cell'],method=method)
        e=json.loads(exp.read_text())
        results.append(dict(source='approvedsheetart',state_index=stateindex,state_name=native['state_name'],
            native_cell_index=native['selected_cell'],native_source=catalog['original_native'],native_sha256=catalog['original_native_sha256'],
            original_visible_height=native['original_visible_height'],output_visible_height=e['placement']['actual_visible_height'],
            sheet=str(BASE/sheet),sheet_sha256=audit['source_sha256'],crop_box=box,
            cutout=str(cutout),cutout_sha256=audit['output_sha256'],cutout_report=str(cutout.with_suffix('.cutout.json')),
            source_resolution_rgb_exact=audit['retained_rgb_exact'],hidden_rgb_exact=audit['all_rgb_exact_including_hidden'],
            extraction_warnings=audit['warnings'],enclosed_candidate_pixels_retained=audit['enclosed_candidate_pixels_retained'],
            output=str(output),output_sha256=e['output']['sha256'],export_report=str(exp),resample=method,
            generated=False,repainted=False,visual_review='pending',runtime_installed=False))
    report['approved_sheet_extractions'][family]=dict(status='four_existing_objects_exported_pending_visual_review',objects=results)
    META.write_text(json.dumps(report,indent=2)+'\n')
    print(family,[(v['state_name'],v['extraction_warnings']) for v in results],flush=True)
report['counts']['approved_sheet_families']=len(report['approved_sheet_extractions'])
report['counts']['approved_sheet_objects']=sum(len(v['objects']) for v in report['approved_sheet_extractions'].values())
META.write_text(json.dumps(report,indent=2)+'\n')
