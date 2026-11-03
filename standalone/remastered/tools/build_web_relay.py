#!/usr/bin/env python3
"""Build the web relay module (web-relay/) into engine/webview-relay/Robust.Client.WebView.dll.

The module replaces the Mac WebKit view inside a headless Robust client and serves the HUD page
to a web browser (planning/WEB_CLIENT.md). It compiles against the replica's client runtime,
read-only, with the .NET 10 SDK (DM_DOTNET_SDK, /private/tmp/dm-runtime-audit/sdk, or `dotnet`).
"""
import os, shutil, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLIENT = ROOT.parent/'replica/runtime/macos-x64/client/Space Station 14.app/Contents/Resources'
OUT = ROOT/'engine/webview-relay'


def sdk():
    for candidate in (os.environ.get('DM_DOTNET_SDK'), '/private/tmp/dm-runtime-audit/sdk/dotnet', shutil.which('dotnet')):
        if candidate and Path(candidate).exists():
            return Path(candidate)
    sys.exit('No .NET SDK found: set DM_DOTNET_SDK to a dotnet executable with the SDK.')


def main():
    if not CLIENT.exists():
        sys.exit(f'Client runtime missing: {CLIENT}')
    references = sorted(p for p in CLIENT.glob('*.dll') if p.name != 'Robust.Client.WebView.dll')
    annotations = ROOT.parent/'opendream-3d/bin/Content.Client/JetBrains.Annotations.dll'
    if annotations.exists():
        references.append(annotations)
    build = Path(tempfile.mkdtemp(prefix='dm-web-relay-'))
    try:
        shutil.copytree(ROOT/'web-relay', build/'src')
        refs = ''.join(f'<Reference Include="{p.stem}"><HintPath>{p}</HintPath><Private>false</Private></Reference>' for p in references)
        (build/'WebRelay.csproj').write_text(
            '<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net10.0</TargetFramework>'
            '<AssemblyName>Robust.Client.WebView</AssemblyName><Nullable>enable</Nullable><EnableDefaultCompileItems>false</EnableDefaultCompileItems>'
            '<AllowUnsafeBlocks>true</AllowUnsafeBlocks><NoWarn>CS0618;CS1591</NoWarn></PropertyGroup>'
            f'<ItemGroup><Compile Include="src/**/*.cs" />{refs}</ItemGroup></Project>')
        env = dict(os.environ, DOTNET_CLI_HOME=str(build/'home'), DOTNET_NOLOGO='1', DOTNET_CLI_TELEMETRY_OPTOUT='1', DOTNET_SKIP_FIRST_TIME_EXPERIENCE='1')
        result = subprocess.run([str(sdk()), 'build', '-c', 'Release', '-nologo', '-v', 'q', str(build/'WebRelay.csproj')], cwd=build, env=env, text=True, capture_output=True)
        log = ROOT/'web-relay-build.log'
        log.write_text(result.stdout + result.stderr)
        errors = [line for line in (result.stdout + result.stderr).splitlines() if 'error' in line.lower()]
        if result.returncode != 0:
            print('\n'.join(errors[:30]) or result.stdout[-3000:])
            sys.exit(f'Build failed (see {log})')
        built = build/'bin/Release/net10.0/Robust.Client.WebView.dll'
        OUT.mkdir(parents=True, exist_ok=True)
        shutil.copy2(built, OUT/'Robust.Client.WebView.dll')
        warnings = [line for line in result.stdout.splitlines() if 'warning' in line.lower()]
        print(f'Built {OUT/"Robust.Client.WebView.dll"} ({(OUT/"Robust.Client.WebView.dll").stat().st_size} bytes, {len(warnings)} warnings)')
    finally:
        shutil.rmtree(build, ignore_errors=True)


if __name__ == '__main__':
    main()
