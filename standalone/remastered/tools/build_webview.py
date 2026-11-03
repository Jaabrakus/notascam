#!/usr/bin/env python3
"""Build Remastered's own copy of the Mac client module (WebKit panels, keyboard
routing, drag-select box, test input) into remastered/engine/webview-webkit.

Inputs are the same as the replica's build_mac_webview.py: the pinned
RobustToolbox source, a .NET 10 SDK and the JetBrains annotations assembly. The
replica's client assemblies are only referenced; nothing in ../replica is written.
"""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
CLIENT = ROOT.parent/'replica/runtime/macos-x64/client/Space Station 14.app/Contents/Resources'
# The engine source is the pinned submodule checkout (af2a7d0) in ../opendream, the annotations assembly is the one
# shipped with the opendream-3d client, and the .NET 10 SDK is installed with Microsoft's dotnet-install script:
#   bash dotnet-install.sh --version 10.0.402 --install-dir /private/tmp/dm-runtime-audit/sdk
DEFAULTS = dict(robust_source=str(ROOT.parent/'opendream/RobustToolbox'),
                sdk='/private/tmp/dm-runtime-audit/sdk/dotnet',
                annotations=str(ROOT.parent/'opendream-3d/bin/Content.Client/JetBrains.Annotations.dll'),
                build_dir='/private/tmp/dm-runtime-audit/remastered-webview-build')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name, value in DEFAULTS.items():
        parser.add_argument('--' + name.replace('_', '-'), type=Path, default=Path(value))
    args = parser.parse_args()
    output = ROOT/'engine/webview-webkit'
    output.mkdir(parents=True, exist_ok=True)
    work = args.build_dir.resolve(); source = work/'src'
    if source.exists(): shutil.rmtree(source)
    source.mkdir(parents=True)
    for file in (args.robust_source/'Robust.Client.WebView').glob('*.cs'):
        if file.name in ('WebViewManager.cs', 'TestBrowseWindow.cs'): continue
        (source/file.name).write_text(file.read_text(encoding='utf-8-sig').replace('using Robust.Client.WebView.Cef;', ''))
    for file in (ROOT/'mac-webview').glob('*.cs'):
        shutil.copy2(file, source/file.name)
    project = ET.Element('Project', Sdk='Microsoft.NET.Sdk')
    properties = ET.SubElement(project, 'PropertyGroup')
    for key, value in {'TargetFramework': 'net10.0', 'AssemblyName': 'Robust.Client.WebView', 'Nullable': 'enable',
                       'EnableDefaultCompileItems': 'false', 'AllowUnsafeBlocks': 'true'}.items():
        ET.SubElement(properties, key).text = value
    items = ET.SubElement(project, 'ItemGroup')
    ET.SubElement(items, 'Compile', Include='src/**/*.cs')
    for path in list(CLIENT.glob('*.dll')) + [args.annotations]:
        ref = ET.SubElement(items, 'Reference', Include=path.stem)
        ET.SubElement(ref, 'HintPath').text = str(path)
        ET.SubElement(ref, 'Private').text = 'false'
    project_file = work/'WebView.csproj'
    ET.ElementTree(project).write(project_file, encoding='unicode')
    env = dict(os.environ, DOTNET_CLI_HOME=str(work/'sdk-home'), DOTNET_CLI_TELEMETRY_OPTOUT='1',
               DOTNET_SKIP_FIRST_TIME_EXPERIENCE='1', DOTNET_GENERATE_ASPNET_CERTIFICATE='false')
    with (ROOT/'webview-build.log').open('w') as log:
        subprocess.run([str(args.sdk), 'build', str(project_file), '-c', 'Release', '--ignore-failed-sources'],
                       env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
        subprocess.run(['swiftc', '-swift-version', '5', '-emit-library', '-O', '-target', 'x86_64-apple-macosx12.0',
                        '-module-cache-path', str(work/'swift-cache'), '-framework', 'AppKit', '-framework', 'WebKit',
                        str(ROOT/'mac-webview/WebKitBridge.swift'), '-o', str(output/'libdmwebkit.dylib')],
                       env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
        # the same bridge for the game window on Apple silicon's own .NET (load-asleep-1030; tools/build_app.py)
        (ROOT/'engine/webview-webkit-arm64').mkdir(exist_ok=True)
        subprocess.run(['swiftc', '-swift-version', '5', '-emit-library', '-O', '-target', 'arm64-apple-macosx12.0',
                        '-module-cache-path', str(work/'swift-cache'), '-framework', 'AppKit', '-framework', 'WebKit',
                        str(ROOT/'mac-webview/WebKitBridge.swift'), '-o', str(ROOT/'engine/webview-webkit-arm64/libdmwebkit.dylib')],
                       env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
    shutil.copy2(work/'bin/Release/net10.0/Robust.Client.WebView.dll', output/'Robust.Client.WebView.dll')
    print(f'Built Remastered client module: {output}')


if __name__ == '__main__':
    main()
