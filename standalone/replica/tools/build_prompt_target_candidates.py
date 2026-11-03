#!/usr/bin/env python3
"""Rebuild private native prompt candidates; never install or include diagnostics."""
import argparse, hashlib, json, os
from pathlib import Path
import shutil, subprocess, zipfile
from xml.sax.saxutils import escape
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for flag in ('sdk','cecil','base-content-zip','native-client-dir','robust-upstream','out'):p.add_argument('--'+flag,type=Path,required=True)
 p.add_argument('--robust-upstream-sha256',required=True)
 a=p.parse_args()
 for key in ('sdk','cecil','base_content_zip','native_client_dir','robust_upstream','out'):setattr(a,key,getattr(a,key).resolve())
 out=a.out
 if sha(a.robust_upstream)!=a.robust_upstream_sha256:p.error('Explicit clean Robust upstream hash does not match')
 if out.exists():p.error('Use a new output directory to retain prior evidence')
 out.mkdir(parents=True)
 env=dict(os.environ,DOTNET_CLI_HOME=str(out/'sdk-home'),DOTNET_CLI_TELEMETRY_OPTOUT='1')
 framework=sorted((a.sdk.parent/'shared/Microsoft.NETCore.App').glob('*'))[-1]
 bases={'content_zip':a.base_content_zip,'Robust.Client.dll':a.robust_upstream,'Robust.Shared.dll':a.native_client_dir/'Robust.Shared.dll','Robust.Shared.Maths.dll':a.native_client_dir/'Robust.Shared.Maths.dll','SpaceWizards.Sdl.dll':a.native_client_dir/'SpaceWizards.Sdl.dll','libSDL3.0.dylib':a.native_client_dir/'libSDL3.0.dylib'}
 before={k:sha(v)for k,v in bases.items()}
 server=out/'server';server.mkdir();shutil.copy2(a.base_content_zip,server/'Content.Client.zip');shutil.copy2(a.base_content_zip,server/'Content.Client.zip.upstream')
 log=(out/'build.log').open('w')
 def run(cmd):subprocess.run([str(v)for v in cmd],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
 run(['python3',ROOT/'tools/build_client_compat.py','--sdk',a.sdk,'--cecil',a.cecil,'--build-dir',out/'sizing','--server-dir',server,'--base-content-zip',a.base_content_zip,'--native-client-dir',a.native_client_dir,'--stage-only','--internal-sizing-only'])
 def build(name,sources,refs,executable):
  d=out/name;d.mkdir();project=d/(name+'.csproj')
  project.write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net10.0</TargetFramework><Nullable>enable</Nullable><EnableDefaultCompileItems>false</EnableDefaultCompileItems>'+('<OutputType>Exe</OutputType>'if executable else'')+'</PropertyGroup><ItemGroup>'+''.join('<Compile Include="'+escape(str(s))+'"/>'for s in sources)+''.join('<Reference Include="'+escape(r.stem)+'"><HintPath>'+escape(str(r))+'</HintPath></Reference>'for r in refs)+'</ItemGroup></Project>')
  run([a.sdk,'build',project,'-c','Release','--ignore-failed-sources'])
  return d/'bin/Release/net10.0'/ (name+'.dll')
 resize=build('PatchPromptResize',[ROOT/'engine/PatchPromptResize.cs'],[a.cecil],True)
 run([a.sdk,resize,bases['Robust.Client.dll'],out/'Robust.Client.resize-only.dll',a.native_client_dir,framework])
 placement_helper=build('PromptPlacement',[ROOT/'engine/PromptPlacement.cs'],[bases['SpaceWizards.Sdl.dll']],False)
 placement=build('PatchPromptPlacement',[ROOT/'engine/PatchPromptPlacement.cs'],[a.cecil],True)
 run([a.sdk,placement,out/'Robust.Client.resize-only.dll',out/'Robust.Client.dll',placement_helper,a.native_client_dir,framework])
 helper=build('PromptLayout',[ROOT/'engine/PromptLayout.cs'],[out/'Robust.Client.dll',bases['Robust.Shared.dll'],bases['Robust.Shared.Maths.dll']],False)
 importer=build('PatchPromptLayout',[ROOT/'engine/PatchPromptLayout.cs'],[a.cecil],True)
 run([a.sdk,importer,out/'sizing/OpenDreamClient.dll',out/'OpenDreamClient.dll',helper,out,out/'sizing/refs',a.native_client_dir,framework])
 shutil.copy2(out/'sizing/OpenDreamShared.dll',out/'OpenDreamShared.dll')
 replacements={'OpenDreamClient.dll':out/'OpenDreamClient.dll','OpenDreamShared.dll':out/'OpenDreamShared.dll'}
 entries={}
 with zipfile.ZipFile(a.base_content_zip)as old,zipfile.ZipFile(out/'Content.Client.zip','w')as new:
  for info in old.infolist():
   name=Path(info.filename).name
   if name in replacements:entries[name]=info.filename
   new.writestr(info,replacements[name].read_bytes()if name in replacements else old.read(info))
 if set(entries)!=set(replacements):raise RuntimeError('Missing exact OpenDream ZIP entries')
 if any(Path(n).name=='Robust.Client.dll'for n in zipfile.ZipFile(out/'Content.Client.zip').namelist()):raise RuntimeError('Unexpected native bootstrap in content package')
 after={k:sha(v)for k,v in bases.items()}
 if before!=after:raise RuntimeError('Build bases changed during reconstruction')
 sdk_version=subprocess.check_output([str(a.sdk),'--version'],env=env,text=True).strip()
 compiler_inputs=dict(sdk_version=sdk_version,csc_sha256=sha(a.sdk.parent/'sdk'/sdk_version/'Roslyn/bincore/csc.dll'),framework_directory=str(framework),system_runtime_sha256=sha(framework/'System.Runtime.dll'),helper_project_sha256=sha(helper.parent.parent.parent.parent/'PromptLayout.csproj'),placement_helper_project_sha256=sha(placement_helper.parent.parent.parent.parent/'PromptPlacement.csproj'),build_script_sha256=sha(Path(__file__)))
 manifest=dict(compiler_inputs=compiler_inputs,base_hashes=before,base_paths={k:str(v.resolve())for k,v in bases.items()},build_tools={str(a.sdk):sha(a.sdk),str(a.cecil):sha(a.cecil)},helper_project=str(helper.parent.parent.parent.parent/'PromptLayout.csproj'),artifacts={n:dict(path=str(out/n),sha256=sha(out/n))for n in ['OpenDreamClient.dll','OpenDreamShared.dll','Robust.Client.dll','Content.Client.zip']},content_zip_entries=entries,native_bootstrap_destination='client/Space Station 14.app/Contents/Resources/Robust.Client.dll',sources={str(f.relative_to(ROOT)):sha(f)for f in sorted((ROOT/'engine').glob('*.cs'))},tool_sources={str(f.relative_to(ROOT)):sha(f)for f in [ROOT/'tools/build_client_compat.py',Path(__file__)]},diagnostic_modules_included=False,installed=False)
 (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps(manifest,indent=2))
if __name__=='__main__':main()
