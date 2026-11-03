#!/usr/bin/env python3
"""Verify deterministic transparent sprite buffers using real-game audit outputs.

Checks two separately started MakeBody runs and a fresh private empty-icon
fixture. Original art, all installed artifacts, and normal profiles are untouched.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil

from PIL import Image
from audit_dmi_edge_cases import run_replacement
from check_generated_icons import pixel_hash

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT/'reference/icon-fallback-audit'


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def frame0(path, direction):
    with Image.open(path) as image:
        return image.convert('RGBA').crop((direction*32, 0, (direction+1)*32, 32))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--server',type=Path,required=True)
    parser.add_argument('--first',required=True)
    parser.add_argument('--repeat',required=True)
    parser.add_argument('--baseline',default='real-game')
    parser.add_argument('--label',required=True)
    parser.add_argument('--port',type=int,default=12191)
    args=parser.parse_args()
    for label in (args.first,args.repeat,args.baseline,args.label):
        if not re.fullmatch(r'[a-z0-9-]+',label):parser.error('Use simple labels')
    reports={key:json.loads((ROOT/'reports'/('icon-fallback-'+label+'.json')).read_text())
             for key,label in [('first',args.first),('repeat',args.repeat),('baseline',args.baseline)]}
    runtime=args.server/'Resources/Assemblies/OpenDreamRuntime.dll';before=sha(runtime)
    checks={key+'_audit_completed':r['audit_completed'] for key,r in reports.items()}
    checks['candidate_runtime_matches_both_audits']=before==reports['first']['runtime_sha256']==reports['repeat']['runtime_sha256']
    checks['constructor_inputs_match']=reports['first']['observations']==reports['repeat']['observations']==reports['baseline']['observations']
    checks['fixture_matches']=reports['first']['fixture_sha256']==reports['repeat']['fixture_sha256']==reports['baseline']['fixture_sha256']
    checks['original_art_unchanged']=reports['first']['art_sha256']==reports['repeat']['art_sha256']==reports['baseline']['art_sha256']
    for path in sorted((BASE/args.first/'replacement/outputs').glob('*-body.dmi')):
        for direction,name in enumerate(('south','north','east','west')):
            actual=frame0(path,direction)
            repeated=frame0(BASE/args.repeat/'replacement/outputs'/path.name,direction)
            ref=frame0(BASE/args.first/'byond/outputs'/path.name,direction)
            baseline=frame0(BASE/args.baseline/'replacement/outputs'/path.name,direction)
            key=path.stem+'_'+name
            checks[key+'_stable']=pixel_hash(actual)==pixel_hash(repeated)
            # The fix must not change a single intended opaque source pixel,
            # even in a composite with a separately documented Blend mismatch.
            checks[key+'_intended_pixels_preserved']=all(a==b for a,b,r in zip(actual.getdata(),baseline.getdata(),ref.getdata()) if r[3])
            checks[key+'_no_unexpected_visible_pixels']=all(not a[3] for a,r in zip(actual.getdata(),ref.getdata()) if not r[3])
            if path.stem=='human-male-body' or direction==0:
                checks[key+'_reference_exact']=pixel_hash(actual)==pixel_hash(ref)
    arena=ROOT/'reference/icon-buffer'/args.label;arena.mkdir(parents=True,exist_ok=False)
    original=ROOT.parent/'remastered/game/Icons/Human.dmi';shutil.copy2(original,arena/'Human.dmi')
    original_hash=sha(original)
    lines=['world','\tNew()','\t\t..()']
    for i in range(16):
        lines += [f'\t\tvar/icon/art{i}=icon(\'Human.dmi\',"",SOUTH,1)',
                  f'\t\tfcopy(art{i},"art-{i}.dmi")',
                  f'\t\tvar/icon/blank{i}=icon()',
                  f'\t\tfcopy(blank{i},"blank-{i}.dmi")']
    lines += ['\t\tworld.log << "DMI_AUDIT|complete"','\t\tshutdown()']
    (arena/'audit.dm').write_text('\n'.join(lines)+'\n');(arena/'audit.dme').write_text('#include "audit.dm"\n')
    run_replacement(arena,args.server,args.port)
    for path in sorted(arena.glob('blank-*.dmi')):
        with Image.open(path) as image:
            checks[path.stem+'_transparent_32px']=image.size==(32,32) and not image.convert('RGBA').getchannel('A').getbbox()
    checks['all_empty_resources_exported']=len(list(arena.glob('blank-*.dmi')))==16
    checks['source_and_runtime_stable']=sha(original)==original_hash and sha(runtime)==before
    errors={}
    for name in ('server.log','ErrorLog.txt'):
        path=arena/name
        errors[name]=re.findall(r'(?im)^.*(?:\[(?:ERRO|FATL)\]|\bruntime error\b|\bexception\b).*$',path.read_text(errors='replace')) if path.exists() else []
    checks['no_runtime_errors']=not any(errors.values())
    result=dict(scope=__doc__,passed=all(checks.values()),checks=checks,errors=errors,runtime_sha256=before,
                evidence={k:str(ROOT/'reports'/('icon-fallback-'+v+'.json')) for k,v in [('first',args.first),('repeat',args.repeat),('baseline',args.baseline)]},
                limitations='Does not fix constructor missing-state fallback, Blend frame expansion, or one-direction Blend replication.')
    target=ROOT/'reports'/('icon-buffer-'+args.label+'-checks.json');target.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(report=str(target),passed=result['passed'],checks=len(checks),failures=[k for k,v in checks.items()if not v]),indent=2))
    return 0 if result['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
