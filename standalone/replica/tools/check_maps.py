#!/usr/bin/env python3
"""Independently compare frozen DMM geometry with replacement compiled maps."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]

def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def split_top(text, separator):
    result=[]; start=0; depth=0; quote=None; escaped=False
    for i,c in enumerate(text):
        if quote:
            if escaped: escaped=False
            elif c=='\\': escaped=True
            elif c==quote: quote=None
        elif c in ('"',"'"): quote=c
        elif c in '({[': depth+=1
        elif c in ')}]': depth-=1
        elif c==separator and depth==0:
            result.append(text[start:i].strip());start=i+1
    result.append(text[start:].strip());return result

def definition(text):
    objects=[]
    for item in split_top(text,','):
        m=re.fullmatch(r'(/[^{}]+?)(?:\{(.*)\})?',item.strip());assert m,item
        typ,props=m.groups();values={}
        if props:
            for prop in split_top(props,';'):
                if not prop: continue
                key,value=prop.split('=',1);value=value.strip()
                # Current map overrides are exclusively string/number literals.
                values[key.strip()]=json.loads(value)
        objects.append(dict(type=typ.rstrip('/') or '/',values=values))
    # A DMM cell can name successive turfs; only the last turf/area survives
    # initial map construction. Verified by the map_layout oracle fixture.
    return ([o for o in objects if not o['type'].startswith(('/turf','/area'))]
            + [next(o for o in reversed(objects) if o['type'].startswith('/turf'))]
            + [next(o for o in reversed(objects) if o['type'].startswith('/area'))])

def main():
    path=ROOT/'opendream/Cave Crawlers.json'; compiled=json.loads(path.read_text())
    maps=re.findall(r'^#include "([^"\n]+\.dmm)"', (ROOT/'source/Cave Crawlers.dme').read_text(),re.M)
    assert len(maps)==len(compiled['Maps'])
    results=[]; z_offset=0
    for filename,actual in zip(maps,compiled['Maps']):
        filename=filename.replace('\\','/');source=ROOT/'source'/filename
        text=source.read_text(encoding='latin1');definitions={}
        for key,contents in re.findall(r'^"([^"\n]+)"\s*=\s*\((.*)\)\s*$',text,re.M):
            definitions[key]=definition(contents)
        actual_defs={}
        for key,cell in actual['CellDefinitions'].items():
            ordered=[*cell.get('Objects',[]),cell['Turf'],cell['Area']]
            actual_defs[key]=[dict(type=compiled['Types'][o['Type']]['Path'],values=o.get('VarOverrides',{})) for o in ordered]
        errors=[]
        if definitions!=actual_defs:
            for k in set(definitions)|set(actual_defs):
                if definitions.get(k)!=actual_defs.get(k): errors.append('definition '+k)
        blocks=[];counts=Counter()
        for x,y,z,data in re.findall(r'\((\d+),(\d+),(\d+)\)\s*=\s*\{"(.*?)"\}',text,re.S):
            rows=[r for r in data.splitlines() if r];keylen=len(next(iter(definitions)))
            assert all(len(r)%keylen==0 for r in rows)
            width=len(rows[0])//keylen;assert all(len(r)==width*keylen for r in rows)
            cells=[r[i:i+keylen] for r in rows for i in range(0,len(r),keylen)]
            counts.update(cells)
            blocks.append(dict(X=int(x),Y=int(y),Z=int(z)+z_offset,Width=width,Height=len(rows),Cells=cells))
        if blocks!=actual['Blocks']:errors.append('cell coordinates/order')
        dimensions=dict(MaxX=max(b['X']+b['Width']-1 for b in blocks),
                        MaxY=max(b['Y']+b['Height']-1 for b in blocks),MaxZ=max(b['Z'] for b in blocks))
        for k,v in dimensions.items():
            if actual[k]!=v:errors.append(k)
        z_offset=max(z_offset+1, dimensions['MaxZ'])
        placements=sum(counts[k]*sum(not o['type'].startswith(('/turf','/area')) for o in defs) for k,defs in definitions.items())
        results.append(dict(path=filename,source_sha256=digest(source),matches=not errors,errors=errors,
                            dimensions=dimensions,cells=sum(counts.values()),definitions=len(definitions),object_placements=placements))
    report=dict(passed=all(r['matches'] for r in results),compiled_sha256=digest(path),maps=results,
                total_cells=sum(r['cells'] for r in results),
                total_object_placements=sum(r['object_placements'] for r in results),
                exclusions=['Compares complete compiled map geometry and overrides, not post-New random population or client rendering.'])
    (ROOT/'reports/map-geometry-checks.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    if not report['passed']:raise SystemExit(1)

if __name__=='__main__':main()
