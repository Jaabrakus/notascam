#!/usr/bin/env python3
"""Check generated rewind metadata and actual frame selectors against BYOND evidence.

No GUI, normal profiles or installed-runtime writes. Native reference capture is
separate and already retained beside the fixtures. Each label keeps its own
artifacts so the old failure evidence is not overwritten by the candidate.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import zipfile
from audit_dmi_edge_cases import metadata,cells,run_replacement

ROOT=Path(__file__).resolve().parents[1]
RUNTIME=ROOT/'runtime/macos-x64'
BASE=ROOT/'reference/dmi-rewind-audit'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--server',type=Path,required=True)
    parser.add_argument('--assemblies',type=Path,required=True)
    parser.add_argument('--label',required=True)
    parser.add_argument('--port',type=int,default=12186)
    parser.add_argument('--sdk',type=Path,default=Path('/tmp/dm-runtime-audit/sdk/dotnet'))
    args=parser.parse_args()
    if not re.fullmatch(r'[a-z0-9-]+',args.label):raise ValueError('Use a simple label')
    arena=BASE/args.label;arena.mkdir(exist_ok=True)
    work=Path('/tmp/dm-runtime-audit')/('rewind-check-'+args.label);work.mkdir(exist_ok=True)
    reference=BASE/'metadata-byond'
    tracked={str(p):p for p in [args.server/'Resources/Assemblies/OpenDreamRuntime.dll',args.server/'Resources/Assemblies/OpenDreamShared.dll',args.assemblies/'OpenDreamClient.dll',args.assemblies/'OpenDreamShared.dll',Path(__file__),ROOT/'engine/CheckDmiRewind.cs']}
    tracked.update({str(p):p for p in reference.glob('*.dmi')})
    hashes_before={k:sha(p)for k,p in tracked.items()}
    checks={}
    checks['matching_server_client_shared_assembly']=sha(args.server/'Resources/Assemblies/OpenDreamShared.dll')==sha(args.assemblies/'OpenDreamShared.dll')
    for name in ('audit.dm','audit.dme','tapestry.dmi','naga.dmi'):shutil.copy2(reference/name,arena/name)
    run_replacement(arena,args.server,args.port)
    for path in sorted(reference.glob('*.dmi')):
        if path.name in ('tapestry.dmi','naga.dmi'):continue
        expected=metadata(path);actual=metadata(arena/path.name)
        checks['metadata_and_pixels_'+path.stem]=len(expected)==len(actual)and all(
            cells(e)==cells(a)and(e['name'],e['movement'],e['rewind'])==(a['name'],a['movement'],a['rewind'])
            for e,a in zip(expected,actual))
    cases=json.loads((BASE/'playback-cases.json').read_text())
    for case in cases:
        if case['name']=='generated-tapestry':case['path']=str(arena/'selected.dmi')
    cases.append(dict(name='flick-forward-only',path=str(BASE/'native-byond/unequal-source.dmi'),state='',moving=False,flick=True,
        times_ms=[0,299,300,799,800,1599,1600,2099],expected=[0,0,1,1,2,2,-1,-1]))
    (arena/'cases.json').write_text(json.dumps(cases,indent=2)+'\n')
    shutil.copy2(ROOT/'engine/CheckDmiRewind.cs',work/'CheckDmiRewind.cs')
    project=work/'CheckDmiRewind.csproj'
    project.write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net10.0</TargetFramework><EnableDefaultCompileItems>false</EnableDefaultCompileItems></PropertyGroup><ItemGroup><Compile Include="CheckDmiRewind.cs"/></ItemGroup></Project>')
    refs=work/'refs';refs.mkdir(exist_ok=True)
    with zipfile.ZipFile(args.server/'Content.Client.zip')as archive:
        for name in archive.namelist():
            if name.endswith('.dll'):(refs/Path(name).name).write_bytes(archive.read(name))
    env=dict(os.environ,DOTNET_ReadyToRun='0',DOTNET_CLI_HOME=str(work/'sdk-home'),DOTNET_CLI_TELEMETRY_OPTOUT='1',DOTNET_GENERATE_ASPNET_CERTIFICATE='false')
    with (arena/'probe-build.log').open('w')as log:subprocess.run([str(args.sdk),'build',str(project),'-c','Release','--ignore-failed-sources'],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
    dirs=[args.assemblies,refs,RUNTIME/'client/Space Station 14.app/Contents/Resources',args.server/'Resources/Assemblies',args.server]
    with (arena/'probe.log').open('w')as log:subprocess.run([str(RUNTIME/'dotnet/dotnet'),str(work/'bin/Release/net10.0/CheckDmiRewind.dll'),os.pathsep.join(map(str,dirs)),str(arena/'cases.json'),str(arena/'playback.json')],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
    results=json.loads((arena/'playback.json').read_text())
    details=[]
    for case,result in zip(cases,results):
        indices=[s['index']for s in result['samples']]
        checks['actual_selector_'+case['name']]=indices==case['expected']
        details.append(dict(name=case['name'],expected=case['expected'],actual=indices))
    errors={}
    for name in ('server.log','probe.log','ErrorLog.txt'):
        path=arena/name
        errors[name]=re.findall(r'(?im)^.*(?:\[(?:ERRO|FATL)\]|\bruntime error\b|\bexception\b).*$',path.read_text(errors='replace'))if path.exists()else[]
    checks['no_world_server_or_probe_errors']=not any(errors.values())
    hashes_after={k:sha(p)for k,p in tracked.items()}
    checks['sources_reference_and_runtime_stable']=hashes_before==hashes_after
    report=dict(scope=__doc__,label=args.label,checks=checks,passed=all(checks.values()),errors=errors,
        hashes_before=hashes_before,hashes_after=hashes_after,playback=details,
        native_reference=str(BASE/'native-reference-checks.json'),
        limitation='Infinite-loop rewind only; no finite-loop count expansion. Flick remains forward-only, as measured in BYOND.')
    path=ROOT/'reports'/('dmi-rewind-'+args.label+'-checks.json');path.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(report=str(path),passed=report['passed'],checks=checks),indent=2));return 0 if report['passed']else 1


if __name__=='__main__':raise SystemExit(main())
