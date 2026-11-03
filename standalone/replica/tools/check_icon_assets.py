#!/usr/bin/env python3
"""Compare legacy DMI conversion to BYOND's own export, not to our decoder."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
REPORTS=ROOT/'reports'

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def dmi(path):
    im=Image.open(path)
    description=im.info.get('Description','')
    width=height=32; states=[]; state=None
    for line in description.splitlines():
        m=re.match(r'\s*(\w+)\s*=\s*(.*)',line)
        if not m: continue
        k,v=m.groups()
        if k=='state':
            state=dict(name=json.loads(v),dirs=1,frames=1,delay=None,loop=0,rewind=0,movement=0)
            states.append(state)
        elif state is None:
            if k=='width': width=int(v)
            elif k=='height': height=int(v)
        elif k in ('dirs','frames','loop','rewind','movement'): state[k]=int(v)
        elif k=='delay': state[k]=[float(x) for x in v.split(',')]
        else: state[k]=v
    result=[]; offset=0; rgba=im.convert('RGBA'); cols=im.width//width
    for s in states:
        if s['delay'] is None: s['delay']=[1.0]*s['frames']
        hashes=[]
        for i in range(s['dirs']*s['frames']):
            n=offset+i
            cell=rgba.crop(((n%cols)*width,(n//cols)*height,(n%cols+1)*width,(n//cols+1)*height))
            # Invisible RGB does not affect the rendered result; retain alpha and all visible RGB.
            px=bytearray(cell.tobytes())
            for j in range(0,len(px),4):
                if px[j+3]==0: px[j:j+3]=b'\0\0\0'
            hashes.append(hashlib.sha256(px).hexdigest())
        offset+=len(hashes)
        result.append(dict(**s,pixels=hashes))
    return dict(width=width,height=height,states=result)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--reference',action='store_true');args=parser.parse_args()
    arena=ROOT/'reference/icon-assets';arena.mkdir(exist_ok=True)
    entries=json.loads((REPORTS/'source-baseline.json').read_text())
    assets=[e['path'] for e in entries if e['path'].lower().endswith('.dmi')]
    legacy=[p for p in assets if (ROOT/'source'/p).read_bytes().startswith(b'\x04DMI')]
    if args.reference:
        lines=['world','\tNew()','\t\t..()']
        for i,p in enumerate(legacy):
            shutil.copy2(ROOT/'source'/p,arena/f'original-{i}.dmi')
            # Force BYOND to decode/re-encode. Merely copying an untouched icon
            # preserves the legacy byte container. White multiplication leaves
            # visible RGBA unchanged while forcing a real image operation.
            lines += [f'\t\tvar/icon/I{i}=icon(\'original-{i}.dmi\')',
                      f'\t\tI{i}.Blend("#ffffff",ICON_MULTIPLY)',
                      f'\t\tfcopy(I{i},"oracle-{i}.dmi")']
        lines += ['\t\tworld.log << "PARITY|complete"']
        (arena/'icon_assets.dm').write_text('\n'.join(lines)+'\n')
        (arena/'icon_assets.dme').write_text('#include "icon_assets.dm"\n')
        subprocess.run([sys.executable,str(ROOT/'tools/check_parity.py'),'icon_assets','--reference-only',
                        '--fixture-dir',str(arena)],check=True)
    results=[]
    for p in assets:
        original=ROOT/'source'/p; staged=ROOT/'opendream'/p
        if p in legacy:
            expected=dmi(arena/f'oracle-{legacy.index(p)}.dmi');actual=dmi(staged)
            errors=[]
            if (expected['width'],expected['height'])!=(actual['width'],actual['height']):errors.append('cell dimensions')
            if len(expected['states'])!=len(actual['states']):errors.append('state count')
            for i,(a,b) in enumerate(zip(expected['states'],actual['states'])):
                for key in set(a)|set(b):
                    if a.get(key)!=b.get(key):errors.append(f'state {i} ({a["name"]!r}): {key}')
            results.append(dict(path=p,method='BYOND icon export versus converted PNG',matches=not errors,errors=errors,
                                states=len(expected['states']),frames=sum(len(s['pixels']) for s in expected['states']),
                                original_sha256=sha(original),staged_sha256=sha(staged),oracle_sha256=sha(arena/f'oracle-{legacy.index(p)}.dmi')))
        else:
            results.append(dict(path=p,method='unchanged original PNG-backed DMI',matches=sha(original)==sha(staged),
                                original_sha256=sha(original),staged_sha256=sha(staged)))
    report=dict(passed=all(r['matches'] for r in results),assets=len(assets),legacy_exports=len(legacy),
                source_baseline_sha256=sha(REPORTS/'source-baseline.json'),results=results,
                exclusions=['Client animation scheduling and composed overlays require separate runtime comparisons.'])
    (REPORTS/'icon-assets-checks.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='results'},indent=2))
    for r in results:
        if not r['matches']: print(r['path'],r.get('errors'))
    if not report['passed']: raise SystemExit(1)

if __name__=='__main__': main()
