#!/usr/bin/env python3
"""Inventory workshop menus and exercise original recipes with scripted prompts."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]

def dm_string(s):return json.dumps(s,ensure_ascii=False)

RACES=['Human','Elf','Orc','Goblin','Lizardman','Frogman','Kobold','Ratman']

def main():
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--races',action='store_true',help=f'write crafting_races: every recipe for {", ".join(RACES)} workers (the default suite uses a Dwarf)')
    args=parser.parse_args()
    name='crafting_races' if args.races else 'crafting'
    compiled=json.loads((ROOT/'opendream/Cave Crawlers.json').read_text())
    source_path='Code/Items/CraftingStations.dm'
    source=(ROOT/'source'/source_path).read_text(encoding='latin1')
    staged=(ROOT/'opendream'/source_path).read_text(encoding='latin1')
    assert source==staged, 'Review source line mapping before generating crafting fixtures'
    lines=source.splitlines();workshops=[]
    for proc in compiled['Procs']:
        owner=compiled['Types'][proc.get('OwningTypeId',0)]['Path']
        if not owner.startswith('/mob/WorkShops') or proc['Name']!='DblClick':continue
        locations=[x['Line'] for x in proc.get('SourceInfo',[]) if 'Line' in x]
        body='\n'.join(lines[min(locations)-1:max(locations)])
        choices=list(dict.fromkeys(re.findall(r'menu\w*\s*\+=\s*"([^"\n]+)"',body)))
        choices=[c for c in choices if c not in ('Craft','Destroy','Cancel')]
        inputs=list(dict.fromkeys(re.findall(r'for\(var(/obj/Items/[^\s,)]+)\s+in\s+M\)',body)))
        inputs=[p.rsplit('/',1)[0] for p in inputs]
        inputs=list(dict.fromkeys(inputs))
        all_types=[t['Path'] for t in compiled['Types']]
        expanded=[]
        for typ in inputs:
            children=[t for t in all_types if t.startswith(typ+'/')]
            leaves=[t for t in children if not any(c.startswith(t+'/') for c in children)]
            expanded.extend(leaves or [typ])
        inputs=list(dict.fromkeys(expanded))
        workshops.append(dict(type=owner,choices=choices,inputs=inputs,source=source_path,line=min(locations)))
    generated=['var/list/parity_workshops=list()','proc/PrepareCraftingCases()']
    for w in workshops:
        if w['type'] in ('/mob/WorkShops/CampFires/GoodAltar','/mob/WorkShops/CampFires/EvilAltar'):continue
        generated.append('\tparity_workshops+=list(list('+w['type']+',list('+','.join(dm_string(c) for c in w['choices'])+'),list('+','.join(w['inputs'])+')))')
    template=(ROOT/'reference/fixtures/crafting_template.dm').read_text()
    if args.races:
        # Same scenarios, repeated per worker race; each observation names its race.
        loop='\tfor(var/list/entry in parity_workshops)\n'
        assert template.count(loop)==1 and template.count('M.Race="Dwarf"')==1
        body=template[template.index(loop):template.index('\tworld.log << "PARITY|complete"')]
        races='list('+','.join(dm_string(r) for r in RACES)+')'
        nested='\tfor(var/worker in '+races+')\n'+''.join('\t'+line+'\n' if line else '\n' for line in body.rstrip('\n').split('\n'))
        template=template.replace(body,nested).replace('M.Race="Dwarf"','M.Race=worker')
        template=template.replace('world.log << "PARITY|craft|[station_type]','world.log << "PARITY|craft|[worker]|[station_type]')
        template=template.replace('world.log << "PARITY|craft_worker_deleted|[station_type]','world.log << "PARITY|craft_worker_deleted|[worker]|[station_type]')
        template=template.replace('world.log << "PARITY|smelter_contents|[mode]','world.log << "PARITY|smelter_contents|[worker]|[mode]')
    fixture=template+'\n'+'\n'.join(generated)+'\n'
    (ROOT/f'reference/fixtures/{name}.dm').write_text(fixture)
    subprocess.run([sys.executable,str(ROOT/'tools/prepare_gameplay_fixture.py'),'--fixture',name],check=True)
    substitutions=[]
    for engine in ('byond','opendream'):
        path=ROOT/f'reference/{name}-{engine}'/source_path
        text=path.read_text(encoding='latin1')
        pattern=r'input\("What Action Will You Choose\?", "Choose", null\) in (menu\w*)'
        changed,count=re.subn(pattern,r'ParityCraftChoice(\1)',text)
        path.write_text(changed,encoding='latin1')
        substitutions.append(dict(engine=engine,scripted_prompts=count))
    report=dict(workshops=workshops,workshop_count=len(workshops),menu_choices=sum(len(w['choices']) for w in workshops),
                substitutions=substitutions,fixture_sha256=hashlib.sha256(fixture.encode()).hexdigest(),
                exclusions=['Dwarf worker; unavailable race-specific menu entries are recorded, not claimed exercised.',
                            'Altar spells are inventoried but deferred to combat/magic tests.',
                            'Smelter failure dereferences a deleted item in the original; that known-original error is excluded from this recipe suite.',
                            'Scripted prompts retain original menu eligibility and recipe bodies.',
                            'Tests missing materials and high/zero skill; does not certify physical workshop UI or every race/skill combination.'])
    if args.races:
        report['worker_races']=RACES
        report['exclusions'][0]='Worker races '+', '.join(RACES)+' (Dwarf is the default suite); a Human mob carries each Race value.'
    (ROOT/('reports/crafting-races-inventory.json' if args.races else 'reports/crafting-inventory.json')).write_text(json.dumps(report,indent=2)+'\n')
    print('Crafting inventory:',len(workshops),'workshops,',report['menu_choices'],'menu choices')

if __name__=='__main__':main()
