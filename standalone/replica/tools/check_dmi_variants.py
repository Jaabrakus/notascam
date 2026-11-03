#!/usr/bin/env python3
"""Audit real idle/walk variants through atlas, installed parser/client and icon().

The expected non-movement/movement extraction behavior is documented by BYOND
at https://www.byond.com/docs/ref/info.html#/icon/New. Existing movement-only
assets retain the established first-frame idle fallback. No art is synthesized.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time
import zipfile

from PIL import Image
from check_generated_icons import pixel_hash, read_states

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT/'runtime/macos-x64'
GAME = ROOT.parent/'remastered/game'
SPECS = [('deer','Icons/Animal.dmi',''),
         ('hell-forged-sword','Code/Items/Icons/DemonicItems.dmi','Sword'),
         ('human-fallback','Icons/Human.dmi','Normal'),
         ('fire-control','Icons/Cave.dmi','Fire'),
         ('water-control','Icons/water.dmi','water')]
DIRS = {2:'south',1:'north',4:'east',8:'west',6:'east',10:'west',5:'east',9:'west'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def selected_states(path,state):
    states = read_states(path)
    return [s for s in states if s['name']==state] or [s for s in states if s['name']=='']


def signature(state):
    return state['movement'],state['dirs'],state['frames'],state['cells']


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sdk',type=Path,default=Path('/tmp/dm-runtime-audit/sdk/dotnet'))
    parser.add_argument('--assemblies',type=Path,default=ROOT/'engine')
    parser.add_argument('--server-dir',type=Path,default=RUNTIME/'server')
    parser.add_argument('--build-dir',type=Path,default=Path('/tmp/dm-runtime-audit/dmi-variants-probe'))
    parser.add_argument('--label',default='baseline')
    parser.add_argument('--port',type=int,default=12181)
    parser.add_argument('--refresh-reference',action='store_true',help='Re-run the isolated fixture in the installed BYOND Docker reference image')
    args=parser.parse_args()
    if not re.fullmatch(r'[a-zA-Z0-9_-]+',args.label): parser.error('Invalid label')
    work=args.build_dir.resolve(); work.mkdir(parents=True,exist_ok=True)
    arena=ROOT/'reference/dmi-variants'/args.label; arena.mkdir(parents=True,exist_ok=True)
    report=dict(checks={},cases=[],source_references=[
        'https://www.byond.com/docs/ref/info.html#/icon/New',
        'https://www.byond.com/docs/ref/info.html#/icon/proc/Insert',
        'https://www.byond.com/docs/ref/info.html#/proc/icon_states'],
        scope='Actual installed parser/frame-selector + headless icon generation; no GUI, normal profiles, or runtime edits.')
    paths={'runtime':args.server_dir/'Resources/Assemblies/OpenDreamRuntime.dll',
           'server_shared':args.server_dir/'Resources/Assemblies/OpenDreamShared.dll',
           'shared':args.assemblies/'OpenDreamShared.dll','client':args.assemblies/'OpenDreamClient.dll',
           'probe':ROOT/'engine/CheckDmiVariants.cs','runner':Path(__file__)}
    specs=[]
    for name,path,state in SPECS:
        paths[name]=GAME/path
        with Image.open(GAME/path) as image:
            specs.append(dict(name=name,path=str(GAME/path),state=state,sheet_width=image.width,sheet_height=image.height))
    report['hashes_before']={k:sha(p) for k,p in paths.items()}
    manifest=json.loads((ROOT.parent/'remastered/assets/sprites/manifest.json').read_text())
    # Verify the exporter already retains source variants independently of the
    # engine: original paths, state metadata and exact saved atlas cell pixels.
    pages={}
    for name,path,state in SPECS[:2]:
        asset=next(a for a in manifest['assets'] if a['source']==path)
        variants=[s for s in asset['states'] if s['name']==state]
        report['checks'][name+'_atlas_preserves_both_variants']=len(variants)==2 and {s['movement'] for s in variants}=={0,1}
        exact=asset['source_sha256']==sha(GAME/path)
        with Image.open(GAME/path) as source:
            source=source.convert('RGBA')
            for variant in variants:
                for cell in variant['cells']:
                    if cell['page'] not in pages:
                        record=next(p for p in manifest['pages'] if p['id']==cell['page'])
                        pages[cell['page']]=Image.open(ROOT.parent/'remastered/assets/sprites'/record['file']).convert('RGBA')
                    x,y,w,h=cell['rect'];sx,sy,sw,sh=cell['source_rect']
                    original=source.crop((sx,sy,sx+sw,sy+sh)).tobytes()
                    atlas=pages[cell['page']].crop((x,y,x+w,y+h)).tobytes()
                    exact &= original==atlas and hashlib.sha256(atlas).hexdigest()==cell['rgba_sha256']
        report['checks'][name+'_both_atlas_variants_match_original_pixels']=exact
    shutil.copy2(paths['probe'],work/'CheckDmiVariants.cs')
    (work/'CheckDmiVariants.csproj').write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net10.0</TargetFramework><EnableDefaultCompileItems>false</EnableDefaultCompileItems></PropertyGroup><ItemGroup><Compile Include="CheckDmiVariants.cs"/></ItemGroup></Project>')
    (work/'cases.json').write_text(json.dumps(specs,indent=2)+'\n')
    refs=work/'refs';refs.mkdir(exist_ok=True)
    with zipfile.ZipFile(args.server_dir/'Content.Client.zip') as archive:
        for entry in archive.namelist():
            if entry.endswith('.dll'): (refs/Path(entry).name).write_bytes(archive.read(entry))
    env=dict(os.environ,DOTNET_ReadyToRun='0',DOTNET_CLI_HOME=str(work/'sdk-home'),DOTNET_CLI_TELEMETRY_OPTOUT='1',DOTNET_GENERATE_ASPNET_CERTIFICATE='false')
    with (work/'build.log').open('w') as log:
        subprocess.run([str(args.sdk),'build',str(work/'CheckDmiVariants.csproj'),'-c','Release','--ignore-failed-sources'],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
    dirs=[args.assemblies.resolve(),refs,RUNTIME/'client/Space Station 14.app/Contents/Resources',args.server_dir/'Resources/Assemblies',args.server_dir]
    with (arena/'client-probe.log').open('w') as log:
        subprocess.run([str(RUNTIME/'dotnet/dotnet'),str(work/'bin/Release/net10.0/CheckDmiVariants.dll'),os.pathsep.join(map(str,dirs)),str(work/'cases.json'),str(arena/'client-observations.json')],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
    observations=json.loads((arena/'client-observations.json').read_text())
    for spec,observed in zip(specs,observations):
        states=selected_states(Path(spec['path']),spec['state'])
        idle=next((s for s in states if not s['movement']),states[0])
        moving=next((s for s in states if s['movement']),idle)
        differences={}; phase_matches={phase:True for phase in ('idle','walking','stopped')}
        with Image.open(spec['path']) as image:
            for row in observed['observations']:
                expected=moving if row['phase']=='walking' else idle
                direction=DIRS[row['direction']] if expected['dirs']>=4 else 'south'
                expected_cells=[c for c in expected['cells'] if c['direction']==direction]
                cell=expected_cells[min(row['index'],len(expected_cells)-1)]
                x,y,w,h=row['x'],row['y'],observed['width'],observed['height']
                actual=pixel_hash(image.crop((x,y,x+w,y+h)))
                phase_matches[row['phase']] &= actual==cell['sha256']
                if row['phase']=='idle' and row['time']==50:
                    differences[str(row['direction'])]=actual!=cell['sha256']
        exported_names=re.findall(r'^state = (.+)$',observed['exported'],flags=re.M)
        expected_name=states[0]['name']
        kept=sum(json.loads(n)==expected_name for n in exported_names)
        report['checks'][spec['name']+'_parser_preserves_variant_count']=kept==len(states)
        for phase,passed in phase_matches.items(): report['checks'][spec['name']+'_'+phase+'_uses_correct_art']=passed
        report['checks'][spec['name']+'_texture_cache_and_frame_selector_agree']=all(r['textureX']==r['x'] and r['textureY']==r['y'] for r in observed['observations'])
        if spec['name'] in ('fire-control','water-control'):
            report['checks'][spec['name']+'_ordinary_idle_still_animates']=len({r['index'] for r in observed['observations'] if r['phase']=='idle'})>1
        if spec['name']=='human-fallback':
            report['checks']['movement_only_idle_fallback_freezes_and_walking_advances']=all(r['index']==0 for r in observed['observations'] if r['phase']!='walking') and any(r['index']>0 for r in observed['observations'] if r['phase']=='walking')
        report['cases'].append(dict(name=spec['name'],source_variants=[dict(name=s['name'],movement=s['movement'],dirs=s['dirs'],frames=s['frames']) for s in states],parsed_variants=kept,retained_movement=observed['selectedMovement'],wrong_idle_directions=differences))
    # Real /icon constructor filtering, copying, white color multiply, and
    # explicit Insert movement flags, all using unchanged source files.
    lines=['world','\tNew()','\t\t..()']
    generations=[]
    for number,(name,path,state) in enumerate(SPECS[:2]):
        filename=name+'.dmi';shutil.copy2(GAME/path,arena/filename)
        literal="'%s'"%filename
        for mode,selector in [('both',None),('idle',0),('moving',1)]:
            var=f'I{number}_{mode}'
            args_text=f'{literal},{json.dumps(state)}'
            if selector is not None: args_text+=f',null,null,{selector}'
            lines.append(f'\t\tvar/icon/{var} = icon({args_text})')
            output=f'{name}-{mode}-generated.dmi'
            lines.append(f'\t\tfcopy({var},"{output}")')
            generations.append(dict(name=name+'-'+mode,path=output,source=path,state=state,moving=selector,output_state=''))
        for mode in ('copy','blend'):
            var=f'I{number}_{mode}'
            lines.append(f'\t\tvar/icon/{var} = icon(I{number}_both)')
            if mode=='blend': lines.append(f'\t\t{var}.Blend("#ffffff",ICON_MULTIPLY)')
            output=f'{name}-{mode}-generated.dmi'
            lines.append(f'\t\tfcopy({var},"{output}")')
            generations.append(dict(name=name+'-'+mode,path=output,source=path,state=state,moving=None,output_state=''))
        lines += [f'\t\tvar/icon/J{number} = new/icon()',
                  f'\t\tJ{number}.Insert(I{number}_idle,"pair",moving=0)',
                  f'\t\tJ{number}.Insert(I{number}_moving,"pair",moving=1)',
                  f'\t\tfcopy(J{number},"{name}-insert-generated.dmi")',
                  f'\t\tworld.log << "VARIANTS|states|{name}|[json_encode(icon_states(J{number}))]"']
        generations.append(dict(name=name+'-insert',path=name+'-insert-generated.dmi',source=path,state=state,moving=None,output_state='pair'))
        for index,(mode,extra,output_state,movement) in enumerate([
            ('file-default','', '',0),('state-default',','+json.dumps(state),state,0),
            ('state-idle',','+json.dumps(state)+',moving=0',state,0),
            ('state-moving',','+json.dumps(state)+',moving=1',state,1),
            ('renamed',',"renamed",moving=1','renamed',1)]):
            var=f'R{number}_{index}'
            output=f'{name}-insert-{mode}-generated.dmi'
            lines += [f'\t\tvar/icon/{var} = new/icon()',f'\t\t{var}.Insert({literal}{extra})',f'\t\tfcopy({var},"{output}")']
            generations.append(dict(name=name+'-insert-'+mode,path=output,source=path,state=state,moving=movement,output_state=output_state,insert_first=True))
    lines += ['\t\tworld.log << "VARIANTS|complete"','\t\tshutdown()']
    dm=arena/'variants.dm';dm.write_text('\n'.join(lines)+'\n')
    dme=arena/'variants.dme';dme.write_text('#include "variants.dm"\n')
    reference=ROOT/'reference/dmi-variants/byond-reference'
    if args.refresh_reference:
        reference.mkdir(exist_ok=True)
        for path in [dm,dme,arena/'deer.dmi',arena/'hell-forged-sword.dmi']:shutil.copy2(path,reference/path.name)
        prefix=['docker','run','--rm','--network','none','--memory','1g','--ulimit','core=0','--mount',f'type=bind,src={reference},dst=/game']
        with (reference/'compile.log').open('w') as log:
            subprocess.run(prefix+['dungeon-master-reference:516.1655','/opt/byond/bin/DreamMaker','/game/variants.dme'],stdout=log,stderr=subprocess.STDOUT,timeout=60,check=True)
        container='dm-variant-reference-'+str(os.getpid())
        with (reference/'server.log').open('w') as log:
            proc=subprocess.Popen(prefix+['--name',container,'dungeon-master-reference:516.1655','/opt/byond/bin/DreamDaemon','/game/variants.dmb','0','-trusted','-invisible','-close'],stdout=log,stderr=subprocess.STDOUT)
            try:
                deadline=time.monotonic()+45
                while proc.poll() is None and time.monotonic()<deadline:
                    if 'VARIANTS|complete' in (reference/'server.log').read_text():break
                    time.sleep(.1)
            finally:
                subprocess.run(['docker','stop','-t','1',container],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=10)
                proc.wait(timeout=10)
        if 'VARIANTS|complete' not in (reference/'server.log').read_text():raise RuntimeError('BYOND reference did not finish')
    for old in arena.glob('*-generated.dmi'):old.unlink()
    with (arena/'compile.log').open('w') as log:
        subprocess.run([str(RUNTIME/'dotnet/dotnet'),str(RUNTIME/'compiler/DMCompiler.dll'),str(dme)],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=60,check=True)
    with tempfile.TemporaryDirectory(prefix='dm-dmi-variants-') as data,(arena/'server.log').open('w') as log:
        proc=subprocess.Popen([str(RUNTIME/'dotnet/dotnet'),str(args.server_dir/'Robust.Server.dll'),'--data-dir',data,'--cvar',f'opendream.json_path={dme.with_suffix(".json")}','--cvar',f'net.port={args.port}','--cvar',f'opendream.topic_port={args.port+13500}','--cvar','net.bindto=127.0.0.1','--cvar','status.enabled=false','--cvar','hub.advertise=false','--cvar','auth.mode=0','--cvar','game.auto_pause_empty=false'],cwd=arena,env=env,stdout=log,stderr=subprocess.STDOUT)
        try:proc.wait(timeout=45)
        except subprocess.TimeoutExpired:
            proc.terminate()
            try:proc.wait(timeout=5)
            except subprocess.TimeoutExpired:proc.kill();proc.wait()
    server_log=(arena/'server.log').read_text(errors='replace')
    report['errors']=re.findall(r'^.*(?:\[(?:ERRO|FATL)\]|runtime error|Exception occurred).*$',server_log,flags=re.M|re.I)
    report['checks']['headless_fixture_completes']='VARIANTS|complete' in server_log and not report['errors']
    report['generated']=[]
    for case in generations:
        expected=selected_states(GAME/case['source'],case['state'])
        if case.get('insert_first'):expected=[dict(read_states(GAME/case['source'])[0],movement=case['moving'])]
        elif case['moving'] is not None:expected=[dict(s,movement=0) for s in expected if s['movement']==case['moving']]
        actual=read_states(arena/case['path']) if (arena/case['path']).exists() else []
        matches=len(expected)==len(actual) and sorted(map(signature,expected),key=lambda s:s[0])==sorted(map(signature,actual),key=lambda s:s[0]) and all(s['name']==case['output_state'] for s in actual)
        report['checks'][case['name']+'_generated_exact_variants']=matches
        reference_path=reference/case['path']
        if reference_path.exists():
            report['checks'][case['name']+'_matches_byond_reference']=actual==read_states(reference_path)
        report['generated'].append(dict(name=case['name'],expected_variants=len(expected),actual_variants=len(actual),expected_movement=[s['movement'] for s in expected],actual_movement=[s['movement'] for s in actual],passed=matches))
    report['reference']=dict(version='BYOND 516.1655',fixture_matches=(reference/'variants.dm').exists() and sha(dm)==sha(reference/'variants.dm'),
        source_sha256={p.name:sha(p) for p in reference.glob('*.dmi') if p.name in ('deer.dmi','hell-forged-sword.dmi')},
        generated_sha256={p.name:sha(p) for p in reference.glob('*-generated.dmi')})
    report['checks']['independent_byond_reference_covers_full_fixture']=report['reference']['fixture_matches'] and all((reference/c['path']).exists() for c in generations)
    report['icon_states']={name:json.loads(value) for name,value in re.findall(r'VARIANTS\|states\|([^|]+)\|([^\r\n]+)',server_log)}
    report['checks']['icon_states_exposes_names_without_internal_variant_keys']=len(report['icon_states'])==2 and all(v==['pair'] for v in report['icon_states'].values())
    report['hashes_after']={k:sha(p) for k,p in paths.items()}
    report['checks']['sources_and_runtime_unchanged']=report['hashes_before']==report['hashes_after']
    report['checks']['server_and_client_share_same_parser']=report['hashes_before']['shared']==report['hashes_before']['server_shared']
    report['passed']=all(report['checks'].values())
    target=ROOT/'reports'/f'dmi-variants-{args.label}-checks.json';target.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(passed=report['passed'],checks=len(report['checks']),failed=[k for k,v in report['checks'].items() if not v],report=str(target)),indent=2))
    return 0 if report['passed'] else 1


if __name__=='__main__':
    raise SystemExit(main())
