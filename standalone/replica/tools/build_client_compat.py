#!/usr/bin/env python3
"""Apply retained, narrowly scoped fixes to the published game-client assembly."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import zipfile

ROOT=Path(__file__).resolve().parents[1]

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('sdk','cecil','build_dir','server_dir'):parser.add_argument('--'+key.replace('_','-'),type=Path,required=True)
    parser.add_argument('--stage-only',action='store_true',help='Build and validate DLLs without installing them')
    parser.add_argument('--internal-sizing-only',action='store_true',help=argparse.SUPPRESS)
    parser.add_argument('--base-content-zip',type=Path,help='Explicit retained clean content ZIP; otherwise use server Content.Client.zip.upstream')
    parser.add_argument('--native-client-dir',type=Path,default=ROOT/'runtime/macos-x64/client/Space Station 14.app/Contents/Resources')
    parser.add_argument('--robust-upstream',type=Path,help='Retained clean Robust.Client.dll, required for complete prompt build')
    parser.add_argument('--robust-upstream-sha256',help='Expected SHA256 of that clean bootstrap')
    args=parser.parse_args()
    for name in ('sdk','cecil','build_dir','server_dir','native_client_dir'):
        setattr(args,name,getattr(args,name).resolve())
    if args.base_content_zip:args.base_content_zip=args.base_content_zip.resolve()
    if args.robust_upstream:args.robust_upstream=args.robust_upstream.resolve()
    work=args.build_dir
    package=args.server_dir/'Content.Client.zip';backup=package.with_suffix('.zip.upstream')
    base=args.base_content_zip or backup
    if args.internal_sizing_only and not args.stage_only:
        parser.error('Internal sizing-only is never installable; it requires --stage-only')
    if not base.is_file():parser.error('Retained clean content ZIP required: --base-content-zip or existing Content.Client.zip.upstream')
    if not args.internal_sizing_only:
        required=[args.sdk,args.cecil,ROOT/'tools/build_prompt_target_candidates.py']+[ROOT/'engine'/name for name in ('PatchPromptTargets.cs','PatchPromptResize.cs','PatchPromptPlacement.cs','PromptPlacement.cs','PatchPromptLayout.cs','PromptLayout.cs')]+[args.native_client_dir/name for name in ('Robust.Shared.dll','Robust.Shared.Maths.dll','SpaceWizards.Sdl.dll','libSDL3.0.dylib')]
        missing=[str(path)for path in required if not path.is_file()]
        if missing:parser.error('Complete prompt build inputs missing: '+', '.join(missing))
        if not args.robust_upstream or not args.robust_upstream_sha256:
            parser.error('Complete prompt builds require --robust-upstream and --robust-upstream-sha256; no sizing-only fallback is installed')
        if not args.robust_upstream.is_file() or sha(args.robust_upstream)!=args.robust_upstream_sha256:
            parser.error('Clean Robust upstream hash does not match')
        if work.exists():parser.error('Complete builds require a fresh --build-dir to retain earlier artifacts')
        shared_target=args.server_dir/'Resources/Assemblies/OpenDreamShared.dll'
        bootstrap=args.native_client_dir/'Robust.Client.dll'
        bootstrap_upstream=bootstrap.with_suffix('.dll.upstream')
        if not args.stage_only:
            if not package.is_file() or not shared_target.is_file() or not bootstrap.is_file():
                parser.error('Complete installation requires an existing server package, shared assembly, and native bootstrap')
            if backup.exists() and sha(backup)!=sha(base):parser.error('Existing clean content backup differs from requested base')
            if bootstrap_upstream.exists() and sha(bootstrap_upstream)!=args.robust_upstream_sha256:
                parser.error('Existing clean bootstrap backup differs from requested clean input')
        command=['python3',str(ROOT/'tools/build_prompt_target_candidates.py'),'--sdk',str(args.sdk),'--cecil',str(args.cecil),'--base-content-zip',str(base),'--native-client-dir',str(args.native_client_dir),'--robust-upstream',str(args.robust_upstream),'--robust-upstream-sha256',args.robust_upstream_sha256,'--out',str(work)]
        subprocess.run(command,check=True,stdout=subprocess.DEVNULL)
        manifest=json.loads((work/'manifest.json').read_text())
        report=dict(complete_prompt_chain=True,stage_only=args.stage_only,manifest=str(work/'manifest.json'),artifacts=manifest['artifacts'])
        if args.stage_only:
            print(json.dumps(report,indent=2));return
        # Build/validate everything before mutation. Preserve clean rebuild inputs
        # and current installed files separately; a patched bootstrap is never
        # inferred to be the clean source on subsequent builds.
        retained=work/'installed-before';retained.mkdir()
        destinations={bootstrap:work/'Robust.Client.dll',package:work/'Content.Client.zip',shared_target:work/'OpenDreamShared.dll',ROOT/'engine/OpenDreamClient.dll':work/'OpenDreamClient.dll',ROOT/'engine/OpenDreamShared.dll':work/'OpenDreamShared.dll'}
        for i,(target,replacement)in enumerate(destinations.items()):
            if target.exists():shutil.copy2(target,retained/(str(i)+'-'+target.name))
        if not backup.exists():shutil.copy2(base,backup)
        if not bootstrap_upstream.exists():shutil.copy2(args.robust_upstream,bootstrap_upstream)
        for target,replacement in destinations.items():
            target.parent.mkdir(parents=True,exist_ok=True)
            pending=target.with_suffix(target.suffix+'.pending');shutil.copy2(replacement,pending);pending.replace(target)
        report.update(installed=True,clean_content_path=str(backup),clean_bootstrap_path=str(bootstrap_upstream),backup_directory=str(retained))
        (ROOT/'reports').mkdir(exist_ok=True)
        (ROOT/'reports/client-compat-build.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(report,indent=2));return
    work.mkdir(parents=True,exist_ok=True)
    shutil.copy2(ROOT/'engine/PatchClient.cs',work/'PatchClient.cs')
    shutil.copy2(ROOT/'engine/PatchMovement.cs',work/'PatchMovement.cs')
    shutil.copy2(ROOT/'engine/PatchDmiVariants.cs',work/'PatchDmiVariants.cs')
    shutil.copy2(ROOT/'engine/PatchRewind.cs',work/'PatchRewind.cs')
    shutil.copy2(ROOT/'engine/PatchContextClick.cs',work/'PatchContextClick.cs')
    shutil.copy2(ROOT/'engine/PatchPromptSelection.cs',work/'PatchPromptSelection.cs')
    shutil.copy2(ROOT/'engine/PatchPromptTargets.cs',work/'PatchPromptTargets.cs')
    shutil.copy2(args.cecil,work/'Mono.Cecil.dll')
    project=work/'PatchClient.csproj'
    project.write_text('''<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net10.0</TargetFramework><EnableDefaultCompileItems>false</EnableDefaultCompileItems></PropertyGroup><ItemGroup><Compile Include="PatchClient.cs"/><Compile Include="PatchMovement.cs"/><Compile Include="PatchDmiVariants.cs"/><Compile Include="PatchRewind.cs"/><Compile Include="PatchContextClick.cs"/><Compile Include="PatchPromptSelection.cs"/><Compile Include="PatchPromptTargets.cs"/><Reference Include="Mono.Cecil"><HintPath>Mono.Cecil.dll</HintPath></Reference></ItemGroup></Project>''')
    env=dict(os.environ,DOTNET_CLI_HOME=str(work/'sdk-home'),DOTNET_CLI_TELEMETRY_OPTOUT='1',DOTNET_GENERATE_ASPNET_CERTIFICATE='false')
    with zipfile.ZipFile(base) as z:
        entry=next(n for n in z.namelist() if n.endswith('/OpenDreamClient.dll'))
        (work/'OpenDreamClient.upstream.dll').write_bytes(z.read(entry))
        refs=work/'refs';refs.mkdir(exist_ok=True)
        for n in z.namelist():
            if n.endswith('.dll'):(refs/Path(n).name).write_bytes(z.read(n))
    with (work/'client-compat-build.log').open('w') as log:
        subprocess.run([str(args.sdk),'build',str(project),'-c','Release','--ignore-failed-sources'],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
        client=args.native_client_dir
        framework=sorted((args.sdk.parent/'shared/Microsoft.NETCore.App').glob('*'))[-1]
        subprocess.run([str(args.sdk),str(work/'bin/Release/net10.0/PatchClient.dll'),'--shared',str(refs/'OpenDreamShared.dll'),str(work/'OpenDreamShared.dll'),str(refs),str(client),str(framework)],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
        shutil.copy2(work/'OpenDreamShared.dll',refs/'OpenDreamShared.dll')
        subprocess.run([str(args.sdk),str(work/'bin/Release/net10.0/PatchClient.dll'),str(work/'OpenDreamClient.upstream.dll'),str(work/'OpenDreamClient.dll'),str(refs),str(client),str(framework)],
                       env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
    print(json.dumps(dict(internal_sizing_only=True,staged_client=str(work/'OpenDreamClient.dll'),staged_shared=str(work/'OpenDreamShared.dll'),client_sha256=sha(work/'OpenDreamClient.dll'),shared_sha256=sha(work/'OpenDreamShared.dll')),indent=2))

if __name__=='__main__':main()
