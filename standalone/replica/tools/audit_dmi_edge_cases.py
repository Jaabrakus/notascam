#!/usr/bin/env python3
"""Read-only parity audit of real duplicate states and rewind artwork.

Runs the same isolated original-art icon fixture in BYOND 516.1655 and the
selected replacement server. A reflection probe invokes the actual client frame
selector with a controlled clock. Reports findings; never edits or installs
engine/game files or touches normal profiles. No invented sprites are used.
"""
import argparse
import collections
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
import zipfile

from PIL import Image
from check_generated_icons import read_states, pixel_hash

ROOT = Path(__file__).resolve().parents[1]
GAME = ROOT.parent/'remastered/game'
RUNTIME = ROOT/'runtime/macos-x64'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def metadata(path):
    states = read_states(path)
    with Image.open(path) as image:
        text = image.info.get('Description','')
    index = -1
    for line in text.splitlines():
        match = re.match(r'\s*(\w+)\s*=\s*(.*)',line)
        if not match: continue
        key,value=match.groups()
        if key=='state':
            index+=1
            states[index].update(loop=0,rewind=0)
        elif index>=0 and key in ('loop','rewind'):
            states[index][key]=int(value)
    return states


def cells(state):
    return state['dirs'],state['frames'],state['cells']


def run_byond(arena):
    base=['docker','run','--rm','--network','none','--memory','1g','--ulimit','core=0',
          '--mount',f'type=bind,src={arena},dst=/game']
    with (arena/'compile.log').open('w') as log:
        subprocess.run(base+['dungeon-master-reference:516.1655','/opt/byond/bin/DreamMaker','/game/audit.dme'],stdout=log,stderr=subprocess.STDOUT,timeout=60,check=True)
    container='dm-dmi-edge-audit-'+str(os.getpid())
    with (arena/'server.log').open('w') as log:
        process=subprocess.Popen(base+['--name',container,'dungeon-master-reference:516.1655','/opt/byond/bin/DreamDaemon','/game/audit.dmb','0','-trusted','-invisible','-close'],stdout=log,stderr=subprocess.STDOUT)
        try:
            end=time.monotonic()+45
            while process.poll() is None and time.monotonic()<end:
                if 'DMI_AUDIT|complete' in (arena/'server.log').read_text(): break
                time.sleep(.1)
        finally:
            subprocess.run(['docker','stop','--time','2',container],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=10)
            process.wait(timeout=10)
    if 'DMI_AUDIT|complete' not in (arena/'server.log').read_text(): raise RuntimeError('BYOND fixture did not complete')


def run_replacement(arena,server,port):
    env=dict(os.environ,DOTNET_ReadyToRun='0')
    dotnet=RUNTIME/'dotnet/dotnet'
    with (arena/'compile.log').open('w') as log:
        subprocess.run([str(dotnet),str(RUNTIME/'compiler/DMCompiler.dll'),str(arena/'audit.dme')],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=60,check=True)
    with (arena/'server.log').open('w') as log:
        process=subprocess.Popen([str(dotnet),str(server/'Robust.Server.dll'),'--data-dir',str(arena/'private-server-data'),
            '--cvar',f'opendream.json_path={arena/"audit.json"}','--cvar',f'net.port={port}',
            '--cvar',f'opendream.topic_port={port+13500}','--cvar','net.bindto=127.0.0.1',
            '--cvar','auth.mode=0','--cvar','status.enabled=false','--cvar','hub.advertise=false',
            '--cvar','game.auto_pause_empty=false'],cwd=arena,env=env,stdout=log,stderr=subprocess.STDOUT)
        try: process.wait(timeout=45)
        finally:
            if process.poll() is None: process.terminate();process.wait(timeout=10)
    if 'DMI_AUDIT|complete' not in (arena/'server.log').read_text(): raise RuntimeError('Replacement fixture did not complete')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--server',type=Path,default=Path('/tmp/dm-runtime-audit/dmi-variants-server'))
    parser.add_argument('--assemblies',type=Path,default=Path('/tmp/dm-runtime-audit/dmi-variants-client-build'))
    parser.add_argument('--sdk',type=Path,default=Path('/tmp/dm-runtime-audit/sdk/dotnet'))
    parser.add_argument('--work',type=Path,default=Path('/tmp/dm-runtime-audit/dmi-edge-probe'))
    parser.add_argument('--port',type=int,default=12185)
    parser.add_argument('--reuse-reference',action='store_true')
    args=parser.parse_args()
    arena=ROOT/'reference/dmi-edge-audit';arena.mkdir(exist_ok=True)
    reference=arena/'byond';replacement=arena/'replacement'
    reference.mkdir(exist_ok=True);replacement.mkdir(exist_ok=True)
    manifest=json.loads((ROOT.parent/'remastered/assets/sprites/manifest.json').read_text())
    duplicate_groups=[];rewind=[];finite=[]
    for asset in manifest['assets']:
        groups=collections.defaultdict(list)
        for state in asset.get('states',[]):
            groups[(state['name'],state['movement'])].append(state)
            if state['loop']: finite.append((asset['source'],state['name'],state['loop']))
            if state['rewind']: rewind.append(dict(source=asset['source'],state=state['name'],movement=state['movement'],frames=state['frames'],references=asset['references']))
        for (name,movement),states in groups.items():
            if len(states)>1:
                duplicate_groups.append(dict(source=asset['source'],state=name,movement=movement,
                    occurrences=len(states),indices=[s['source_index']for s in states],references=asset['references']))
    cases=[]
    for index,group in enumerate(duplicate_groups): cases.append(dict(name='duplicate-'+str(index),kind='duplicate',**group))
    for name,path,state in [('tapestry','Icons/Tapestries.dmi','Retribution'),('dragon-unused-state','Icons/dragons.dmi','sand2'),('naga-unused-asset','Icons/Naga.dmi','Normal')]:
        cases.append(dict(name=name,kind='rewind',source=path,state=state))
    paths={case['source']:GAME/case['source']for case in cases}
    paths.update(runtime=args.server/'Resources/Assemblies/OpenDreamRuntime.dll',shared=args.assemblies/'OpenDreamShared.dll',client=args.assemblies/'OpenDreamClient.dll',runner=Path(__file__),probe=ROOT/'engine/CheckDmiPlayback.cs')
    report=dict(scope=__doc__,inventory=dict(duplicate_groups=duplicate_groups,extra_duplicate_occurrences=sum(g['occurrences']-1 for g in duplicate_groups),rewind=rewind,finite_loop_states=finite),hashes_before={k:sha(p)for k,p in paths.items()},cases=[])
    lines=['world','\tNew()','\t\t..()']
    for index,case in enumerate(cases):
        literal='asset-'+str(index)+'.dmi';case['input']=literal
        for place in (reference,replacement):shutil.copy2(GAME/case['source'],place/literal)
        for mode in ('selected','copied-selected'):
            variable='I'+str(index)+mode.replace('-','_')
            source="'%s'"%literal
            if mode=='copied-selected':source='icon('+source+')'
            lines.extend([f'\t\tvar/icon/{variable} = icon({source},{json.dumps(case["state"])})',
                f'\t\tfcopy({variable},"{case["name"]}-{mode}.dmi")'])
    lines+=['\t\tworld.log << "DMI_AUDIT|complete"','\t\tshutdown()']
    text='\n'.join(lines)+'\n'
    for place in (reference,replacement):
        (place/'audit.dm').write_text(text);(place/'audit.dme').write_text('#include "audit.dm"\n')
    reference_inputs={'fixture':sha(reference/'audit.dm'),
                      'original_assets':{case['input']:sha(GAME/case['source'])for case in cases}}
    if args.reuse_reference:
        if not (reference/'inputs.json').exists() or json.loads((reference/'inputs.json').read_text()) != reference_inputs:
            raise ValueError('BYOND reference inputs changed; rerun without --reuse-reference')
    else:
        run_byond(reference)
        (reference/'inputs.json').write_text(json.dumps(reference_inputs,indent=2)+'\n')
    run_replacement(replacement,args.server,args.port)
    for case in cases:
        original=[s for s in metadata(GAME/case['source'])if s['name']==case['state']]
        result={**case,'source_unique_pixel_variants':len({json.dumps(cells(s),sort_keys=True)for s in original}),'modes':{}}
        for mode in ('selected','copied-selected'):
            outputs={engine:metadata(place/(case['name']+'-'+mode+'.dmi'))for engine,place in [('byond',reference),('replacement',replacement)]}
            data={}
            for engine,states in outputs.items():
                data[engine]=[dict(movement=s['movement'],frames=s['frames'],dirs=s['dirs'],loop=s['loop'],rewind=s['rewind'],
                    matching_original_occurrences=[i for i,o in enumerate(original)if cells(o)==cells(s)])for s in states]
            data['visible_pixels_match']=len(outputs['byond'])==len(outputs['replacement']) and all(cells(a)==cells(b)for a,b in zip(outputs['byond'],outputs['replacement']))
            data['rewind_metadata_matches']= [s['rewind']for s in outputs['byond']]==[s['rewind']for s in outputs['replacement']]
            result['modes'][mode]=data
        report['cases'].append(result)
    work=args.work;work.mkdir(parents=True,exist_ok=True)
    shutil.copy2(paths['probe'],work/'CheckDmiPlayback.cs')
    (work/'CheckDmiPlayback.csproj').write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net10.0</TargetFramework><EnableDefaultCompileItems>false</EnableDefaultCompileItems></PropertyGroup><ItemGroup><Compile Include="CheckDmiPlayback.cs"/></ItemGroup></Project>')
    refs=work/'refs';refs.mkdir(exist_ok=True)
    with zipfile.ZipFile(args.server/'Content.Client.zip')as archive:
        for name in archive.namelist():
            if name.endswith('.dll'):(refs/Path(name).name).write_bytes(archive.read(name))
    specs=[]
    for case in cases:
        if case['kind']!='rewind':continue
        specs.append(dict(name=case['name'],path=str(GAME/case['source']),state=case['state'],moving=case['name']=='naga-unused-asset',times_ms=list(range(50,10000,100))))
    (work/'cases.json').write_text(json.dumps(specs,indent=2)+'\n')
    env=dict(os.environ,DOTNET_ReadyToRun='0',DOTNET_CLI_HOME=str(work/'sdk-home'),DOTNET_CLI_TELEMETRY_OPTOUT='1',DOTNET_GENERATE_ASPNET_CERTIFICATE='false')
    with (work/'build.log').open('w') as log:subprocess.run([str(args.sdk),'build',str(work/'CheckDmiPlayback.csproj'),'-c','Release','--ignore-failed-sources'],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
    dirs=[args.assemblies,refs,RUNTIME/'client/Space Station 14.app/Contents/Resources',args.server/'Resources/Assemblies',args.server]
    with (arena/'playback.log').open('w')as log:subprocess.run([str(RUNTIME/'dotnet/dotnet'),str(work/'bin/Release/net10.0/CheckDmiPlayback.dll'),os.pathsep.join(map(str,dirs)),str(work/'cases.json'),str(arena/'playback.json')],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
    report['playback']=json.loads((arena/'playback.json').read_text())
    for sample,spec in zip(report['playback'],specs):
        with Image.open(spec['path'])as image:
            for row in sample['samples']:
                x,y=row['x'],row['y'];row['visible_rgba_sha256']=pixel_hash(image.crop((x,y,x+sample['width'],y+sample['height'])))
        indices=[s['index']for s in sample['samples']]
        sample['interior_reverse_steps']=sum(a-b==1 and a not in (0,sample['frame_count']-1)for a,b in zip(indices,indices[1:]))
        sample['last_to_first_wraps']=sum(a==sample['frame_count']-1 and b==0 for a,b in zip(indices,indices[1:]))
    report['hashes_after']={k:sha(p)for k,p in paths.items()}
    report['sources_and_private_runtime_unchanged']=report['hashes_before']==report['hashes_after']
    report['errors']={name:re.findall(r'(?im)^.*(?:\[(?:ERRO|FATL)\]|\bruntime error\b|\bexception\b).*$',(place/'server.log').read_text(errors='replace'))for name,place in [('byond',reference),('replacement',replacement)]}
    report['audit_completed']=report['sources_and_private_runtime_unchanged'] and not any(report['errors'].values())
    report['reference_fixture_sha256']=sha(reference/'audit.dm')
    report['reference_sources']=['https://www.byond.com/docs/ref/info.html#/icon/New','https://www.byond.com/docs/ref/info.html#/icon/proc/Insert']
    target=ROOT/'reports/dmi-edge-audit.json';target.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(report=str(target),audit_completed=report['audit_completed'],duplicates=duplicate_groups,finite=finite,
        results=[dict(name=c['name'],byond=c['modes']['selected']['byond'],replacement=c['modes']['selected']['replacement'])for c in report['cases']],
        playback=[{k:v for k,v in p.items()if k not in ('samples','exported')}for p in report['playback']]),indent=2))
    return 0 if report['audit_completed']else 1


if __name__=='__main__':raise SystemExit(main())
