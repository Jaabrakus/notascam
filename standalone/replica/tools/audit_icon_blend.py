#!/usr/bin/env python3
"""Original-art BYOND oracle for Blend direction selection, independently of frames.

No source artwork is generated or rewritten. Existing 32px sprites are selected
with native icon() filters, then blended/exported in private headless worlds.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil

from audit_dmi_edge_cases import run_byond, run_replacement
from check_generated_icons import read_states

ROOT=Path(__file__).resolve().parents[1]
GAME=ROOT.parent/'remastered/game'
ASSETS={'Human.dmi':'Icons/Human.dmi','Female.dmi':'Code/Creatures/Icons/Female.dmi',
        'BoneItems.dmi':'Icons/BoneItems.dmi','MetalObjects.dmi':'Icons/MetalObjects.dmi'}
DESTINATIONS={
    'one':"icon('Human.dmi',\"\",SOUTH,1,1)",
    'four':"icon('Human.dmi',\"\",null,1,1)",
    'eight':"icon('BoneItems.dmi',\"Arrow\",null,1,0)"}
SOURCES={
    'south':"icon('Female.dmi',\"Unders\",SOUTH,1,1)",
    'north':"icon('Female.dmi',\"Unders\",NORTH,1,1)",
    'east-frame2':"icon('Female.dmi',\"Unders\",EAST,2,1)",
    'four':"icon('Female.dmi',\"Unders\",null,1,1)",
    'eight':"icon('MetalObjects.dmi',\"Arrow\",null,1,0)"}
MODES=('OVERLAY','UNDERLAY','ADD','SUBTRACT','MULTIPLY','AND','OR')


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--server',type=Path,required=True)
    p.add_argument('--label',required=True)
    p.add_argument('--port',type=int,default=12193)
    p.add_argument('--reuse-reference',type=Path)
    a=p.parse_args()
    if not re.fullmatch(r'[a-z0-9-]+',a.label):p.error('Use a simple fresh label')
    out=ROOT/'reference/icon-blend'/a.label;out.mkdir(parents=True,exist_ok=False)
    cases=[]
    for destination,dexpr in DESTINATIONS.items():
        for source,sexpr in SOURCES.items():
            for mode in MODES:
                cases.append(dict(id=f'{destination}-{source}-{mode.lower()}',destination=dexpr,source=sexpr,mode=mode,scope='directions'))
    for mode in MODES:
        cases.append(dict(id='four-color-'+mode.lower(),destination=DESTINATIONS['four'],source='"#80402080"',mode=mode,scope='color-control'))
    # These expose frame repetition/expansion independently and are not bundled
    # into a direction-only implementation claim.
    cases.extend([
        dict(id='animated-body-still-source',destination="icon('Human.dmi',\"\",null,null,1)",source=SOURCES['south'],mode='OVERLAY',scope='frames-deferred'),
        dict(id='still-body-animated-source',destination=DESTINATIONS['four'],source="icon('Female.dmi',\"Unders\",null,null,1)",mode='OVERLAY',scope='frames-deferred')])
    lines=['world/New()','    ..()']
    for i,case in enumerate(cases):
        lines.extend([f'    var/icon/d{i}={case["destination"]}',f'    var/s{i}={case["source"]}',
                      f'    fcopy(d{i},"outputs/{case["id"]}-destination.dmi")'])
        if case['scope']!='color-control':lines.append(f'    fcopy(s{i},"outputs/{case["id"]}-source.dmi")')
        lines.extend([f'    d{i}.Blend(s{i},ICON_{case["mode"]})',f'    fcopy(d{i},"outputs/{case["id"]}.dmi")'])
    lines.extend(['    world.log << "DMI_AUDIT|complete"','    shutdown()'])
    fixture='\n'.join(lines)+'\n'
    runtime=a.server/'Resources/Assemblies/OpenDreamRuntime.dll'
    tracked={key:sha(GAME/value)for key,value in ASSETS.items()}
    report=dict(scope=__doc__,runtime_sha256=sha(runtime),original_art=tracked,cases=[],errors={})
    for engine in ('byond','replacement'):
        arena=out/engine;arena.mkdir()
        if engine=='byond'and a.reuse_reference:
            shutil.copytree(a.reuse_reference/'byond',arena,dirs_exist_ok=True)
            if (arena/'audit.dme').read_text()!=fixture:raise RuntimeError('Reference fixture differs')
            continue
        (arena/'outputs').mkdir()
        for name,path in ASSETS.items():shutil.copy2(GAME/path,arena/name)
        (arena/'audit.dme').write_text(fixture)
        if engine=='byond':run_byond(arena)
        else:run_replacement(arena,a.server.resolve(),a.port)
    for case in cases:
        ref=read_states(out/'byond/outputs'/(case['id']+'.dmi'))
        actual=read_states(out/'replacement/outputs'/(case['id']+'.dmi'))
        inputs={}
        for suffix in ('destination','source'):
            if suffix=='source'and case['scope']=='color-control':continue
            b=read_states(out/'byond/outputs'/(case['id']+'-'+suffix+'.dmi'))
            r=read_states(out/'replacement/outputs'/(case['id']+'-'+suffix+'.dmi'))
            inputs[suffix]=dict(reference=b,replacement=r,matches=b==r)
        cellmatches={}
        if ref and actual:
            r={(c['frame'],c['direction']):c['sha256']for c in actual[0]['cells']}
            cellmatches={f'{c["direction"]}-frame{c["frame"]}':r.get((c['frame'],c['direction']))==c['sha256']for c in ref[0]['cells']}
        report['cases'].append(dict(**case,inputs=inputs,reference=ref,replacement=actual,matches=ref==actual,cell_matches=cellmatches))
    for engine in ('byond','replacement'):
        logs='\n'.join(x.read_text(errors='replace')for x in (out/engine).glob('*.log')if x.name!='compile.log')
        report['errors'][engine]=re.findall(r'(?im)^.*(?:\[(?:ERRO|FATL)\]|\bruntime error\b|\bexception\b).*$',logs)
    report['sources_and_runtime_stable']=tracked=={key:sha(GAME/value)for key,value in ASSETS.items()}and report['runtime_sha256']==sha(runtime)
    report['audit_completed']=report['sources_and_runtime_stable']and not any(report['errors'].values())
    dest=ROOT/'reports'/('icon-blend-'+a.label+'.json');dest.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(report=str(dest),audit_completed=report['audit_completed'],cases=len(cases),matches=sum(c['matches']for c in report['cases']),
                         modes={m:dict(total=sum(c['mode']==m and c['scope']=='directions'for c in report['cases']),matches=sum(c['matches']and c['mode']==m and c['scope']=='directions'for c in report['cases']))for m in MODES}),indent=2))
    return 0 if report['audit_completed']else 1


if __name__=='__main__':raise SystemExit(main())
