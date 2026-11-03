#!/usr/bin/env python3
"""Inventory the frozen game and map each entry to an explicit comparison scenario.

This is a coverage plan, not a passing gameplay report. Compiled metadata supplies
verb identities; recursive includes supply module membership independently.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'source'
REPORTS = ROOT/'reports'

SCENARIOS = {
    'runtime': ('R05', 'Compare initialization, inheritance, callbacks, lists and delayed actions used by this module.'),
    'world': ('W01,W02,W03,W04', 'Compare full-map startup, population, event transitions and timed state changes.'),
    'combat': ('G02,G03,G04,G05,G06', 'Exercise attack and recovery branches; compare damage, anatomy, effects and timing.'),
    'races': ('G01,G06', 'Create every declared race/form; compare spawning, attributes and transformation behavior.'),
    'ai': ('A01,A02,A03', 'Exercise each behavior family against visible, hidden, blocked and unreachable targets.'),
    'items': ('C01,C02,C03,C05', 'Exercise each item/recipe and valid/invalid interaction; compare inventory and resource changes.'),
    'building': ('C04,I06', 'Place/remove each structure and traverse resulting terrain; compare costs, state and collision.'),
    'input': ('I01,I02,I03,I04,I05,I07', 'Replay original physical key/mouse actions; compare commands, selection, camera and orders.'),
    'ownership': ('G07,M02', 'Exercise owner/ally/royal transitions and conflicts with two players; compare permissions and lists.'),
    'save': ('S01,S02,S03,S04', 'Save and reload each supported state, reconnect and compare graph, fields, placement and appearance.'),
    'admin': ('M05', 'Run each verb as an authorized and unauthorized player; compare visibility, permission and resulting state.'),
    'multiplayer': ('M01,M03,M04', 'Compare login, identity, messages, disconnect and recovery with two clients.'),
    'visual': ('V02,V03,V04', 'Compare every used state/direction/frame and composed appearance at equivalent game states.'),
    'map': ('V01,W01,I06', 'Compare dimensions, cells, types, overrides and initial object placements, then runtime traversal.'),
    'skin': ('V05,V06,I03', 'Compare control text, geometry, visibility, scrolling, links, focus and resizing.'),
    'macro': ('I01,I04', 'Press this binding with its modifiers and hold/release behavior; compare dispatched action and timing.'),
    'sound': ('V07', 'Trigger this sound in the original and replacement; compare asset, channel, volume and repetition.'),
    'resource': ('R01,F05', 'Identify every reference and compare resource resolution and presentation at its call sites.'),
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def category(path):
    p = path.lower()
    if any(x in p for x in ('admin', 'plugin', 'antispam')): return 'admin'
    if 'save' in p: return 'save'
    if 'ownership' in p: return 'ownership'
    if any(x in p for x in ('quickprocs', 'selection', 'click')): return 'input'
    if any(x in p for x in ('world', 'random events', 'history')): return 'world'
    if any(x in p for x in ('login', 'verbs')): return 'multiplayer'
    if 'building' in p or 'turf' in p: return 'building'
    if any(x in p for x in ('items', 'item making', 'workshop', 'container')): return 'items'
    if 'monster ai' in p or '/monster/' in p or 'critters' in p: return 'ai'
    if 'race' in p or 'restart' in p or 'breeding' in p: return 'races'
    if 'overlay' in p: return 'visual'
    if any(x in p for x in ('combat', 'health', 'death', 'damaged', 'leveling')): return 'combat'
    return 'runtime'


def mapped(kind, identity, **fields):
    checklist, steps = SCENARIOS[kind]
    return dict(id=identity, scenario=kind, checklist=checklist.split(','),
                comparison=steps, verification='unverified', **fields)


def main():
    compiled_path = ROOT/'opendream/Cave Crawlers.json'
    compiled = json.loads(compiled_path.read_text())
    baseline = json.loads((REPORTS/'source-baseline.json').read_text())
    assert all(sha(SOURCE/e['path']) == e['sha256'] for e in baseline)
    included, edges = set(), []
    def walk(path):
        if path in included: return
        included.add(path)
        if Path(path).suffix.lower() not in ('.dm', '.dme'): return
        for number, line in enumerate((SOURCE/path).read_text(encoding='latin1').splitlines(), 1):
            m = re.match(r'\s*#include\s+"([^"]+)"', line)
            if not m: continue
            child = (Path(path).parent/m[1].replace('\\', '/')).as_posix()
            assert (SOURCE/child).is_file(), child
            edges.append(dict(source=path, line=number, target=child))
            walk(child)
    walk('Cave Crawlers.dme')
    files=[]
    for e in baseline:
        p=e['path']; ext=Path(p).suffix.lower()
        kind=(category(p) if ext=='.dm' else 'map' if ext=='.dmm' else 'skin' if ext=='.dmf'
              else 'macro' if ext=='.dms' else 'visual' if ext in ('.dmi','.png','.bmp','.jpg','.gif')
              else 'sound' if ext in ('.wav','.ogg','.mp3','.mid','.midi') else 'resource')
        files.append(mapped(kind,'file:'+p, **e, included=p in included,
                            compiled_resource=p in compiled['Resources']))
    procs=[]
    for index,p in enumerate(compiled['Procs']):
        refs=[dict(path=compiled['Strings'][x['File']], line=x.get('Line'))
              for x in p.get('SourceInfo',[]) if 'File' in x]
        refs=[r for r in refs if r['path'] in included]
        if not refs: continue
        owner=compiled['Types'][p.get('OwningTypeId',0)]['Path']
        procs.append(mapped(category(refs[0]['path']),f'proc:{owner}/{p["Name"]}:{index}',
                            owner=owner, name=p['Name'], is_verb=p.get('IsVerb',False),
                            display_name=p.get('VerbName',p['Name']), sources=refs))
    controls=[]; group=None; element=None
    for number,line in enumerate((SOURCE/'skin.dmf').read_text(encoding='latin1').splitlines(),1):
        m=re.match(r'(window|macro|menu) "([^"]+)"',line)
        if m: group=(m[1],m[2]); element=None
        elif re.match(r'\s*elem\b',line):
            name=re.search(r'"([^"]*)"',line)
            element=mapped('macro' if group[0]=='macro' else 'skin', f'skin:{group[1]}:{number}',
                           group_kind=group[0],group=group[1],name=name[1] if name else '',line=number,properties={})
            controls.append(element)
        elif element is not None:
            m=re.match(r'\s*([\w-]+) = (.*)',line)
            if m: element['properties'][m[1]]=m[2]
    macros=[mapped('macro',f'dms:{n}',key=m[1],command=m[2],line=n)
            for n,line in enumerate((SOURCE/'BackGrounds.dms').read_text().splitlines(),1)
            if (m:=re.match(r'\s*(\S+)\s+return\s+"([^"]+)"',line))]
    warnings=[]
    for line in (REPORTS/'opendream-adapted-compile.log').read_text().splitlines():
        m=re.match(r'Warning (\w+) at (.*?):(\d+):(\d+): (.*)',line)
        if not m: continue
        code,path,ln,col,message=m.groups()
        status='open'; note='Requires comparison of reachable callers; not dismissed as cosmetic.'
        if 'DMS files are not supported' in message:
            status='adapted';note='Commands transferred into staged DMF; physical macro behavior remains I01.'
        elif 'Repop()' in message: note='Reachable from world.New and SeasonChange; population behavior gap.'
        elif 'Reboot()' in message: note='Reachable from reboot verb; lifecycle behavior gap.'
        warnings.append(dict(code=code,path=path,line=int(ln),column=int(col),message=message,status=status,note=note))
    report=dict(kind='coverage_plan',exact_replica_verified=False,
                source_baseline_sha256=sha(REPORTS/'source-baseline.json'),compiled_sha256=sha(compiled_path),
                runtime_sha256=sha(ROOT/'runtime/macos-x64/server/Resources/Assemblies/OpenDreamRuntime.dll'),
                scenarios=SCENARIOS,include_edges=edges,files=files,procedures=procs,
                controls=controls,legacy_macros=macros,
                counts=dict(files=len(files),included_dm=sum(p.endswith('.dm') for p in included),
                            included_maps=sum(p.endswith('.dmm') for p in included),procedures=len(procs),
                            verbs=sum(p['is_verb'] for p in procs),skin_elements=len(controls),legacy_macros=len(macros)),
                exclusions=['Inventory is not proof that any scenario passes.',
                            'Files outside the include graph are retained and identified, not assumed active.',
                            'Dynamic resources and permissions require caller-level verification.'])
    (REPORTS/'coverage-inventory.json').write_text(json.dumps(report,indent=2)+'\n')
    (REPORTS/'compiler-warning-audit.json').write_text(json.dumps(dict(
        compiled_sha256=sha(compiled_path),counts=dict(Counter(w['code'] for w in warnings)),
        warnings=warnings,all_behavior_differences_resolved=False),indent=2)+'\n')
    rows=['# Source-to-scenario coverage inventory','',
          'Generated by `tools/audit_coverage.py`. All entries are planned comparisons, not passing tests.','',
          'Detailed per-file, per-procedure, verb, skin and macro entries: `reports/coverage-inventory.json`.','',
          '| Category | Count |','| --- | --- |']
    rows += [f'| {k} | {v} |' for k,v in report['counts'].items()]
    rows += ['','| Scenario | Checklist | Comparison |','| --- | --- | --- |']
    rows += [f'| {k} | {v[0]} | {v[1]} |' for k,v in SCENARIOS.items()]
    rows += ['','| Included module | Scenario |','| --- | --- |']
    rows += [f'| `{p}` | {category(p)} |' for p in sorted(included) if p.endswith('.dm')]
    (ROOT/'COVERAGE.md').write_text('\n'.join(rows)+'\n')
    print(json.dumps(report['counts'],indent=2)); print('Warning groups:',dict(Counter(w['code'] for w in warnings)))

if __name__=='__main__': main()
