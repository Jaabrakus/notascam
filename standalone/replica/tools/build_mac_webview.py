#!/usr/bin/env python3
"""Build a WebKit implementation of Robust's existing browser interfaces."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('robust_source', 'sdk', 'annotations', 'build_dir'):
        parser.add_argument('--'+name.replace('_', '-'), required=True, type=Path)
    args = parser.parse_args()
    runtime = ROOT/'runtime/macos-x64'
    client = runtime/'client/Space Station 14.app/Contents/Resources'
    output = runtime/'webview-webkit'
    output.mkdir(exist_ok=True)
    work = args.build_dir.resolve()
    work.mkdir(parents=True, exist_ok=True)
    source = work/'src'
    source.mkdir(exist_ok=True)
    api = args.robust_source.resolve()/'Robust.Client.WebView'
    for file in api.glob('*.cs'):
        if file.name in ('WebViewManager.cs', 'TestBrowseWindow.cs'):
            continue
        text = file.read_text(encoding='utf-8-sig').replace('using Robust.Client.WebView.Cef;', '')
        (source/file.name).write_text(text)
    shutil.copy2(ROOT/'mac-webview/MacWebViewManager.cs', source/'MacWebViewManager.cs')
    shutil.copy2(ROOT/'mac-webview/NativeUiProbe.cs', source/'NativeUiProbe.cs')
    shutil.copy2(ROOT/'mac-webview/DreamSeekerKeys.cs', source/'DreamSeekerKeys.cs')
    project = ET.Element('Project', Sdk='Microsoft.NET.Sdk')
    properties = ET.SubElement(project, 'PropertyGroup')
    for key, value in {'TargetFramework': 'net10.0', 'AssemblyName': 'Robust.Client.WebView',
                       'Nullable': 'enable', 'EnableDefaultCompileItems': 'false',
                       'AllowUnsafeBlocks': 'true'}.items():
        ET.SubElement(properties, key).text = value
    items = ET.SubElement(project, 'ItemGroup')
    ET.SubElement(items, 'Compile', Include='src/**/*.cs')
    refs = list(client.glob('*.dll'))+[args.annotations.resolve()]
    for path in refs:
        ref = ET.SubElement(items, 'Reference', Include=path.stem)
        ET.SubElement(ref, 'HintPath').text = str(path)
        ET.SubElement(ref, 'Private').text = 'false'
    project_file = work/'WebView.csproj'
    ET.ElementTree(project).write(project_file, encoding='unicode')
    env = dict(os.environ, DOTNET_CLI_HOME=str(work/'sdk-home'), DOTNET_CLI_TELEMETRY_OPTOUT='1',
               DOTNET_SKIP_FIRST_TIME_EXPERIENCE='1', DOTNET_GENERATE_ASPNET_CERTIFICATE='false')
    with (ROOT/'reports/mac-webview-build.log').open('w') as log:
        subprocess.run([str(args.sdk.resolve()), 'build', str(project_file), '-c', 'Release',
                        *(['--no-restore'] if (work/'obj/project.assets.json').exists() else ['--ignore-failed-sources'])], env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
        subprocess.run(['swiftc', '-swift-version', '5', '-emit-library', '-O',
            '-target', 'x86_64-apple-macosx12.0', '-module-cache-path', str(work/'swift-cache'),
            '-framework', 'AppKit', '-framework', 'WebKit', str(ROOT/'mac-webview/WebKitBridge.swift'),
            '-o', str(output/'libdmwebkit.dylib')], env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
    shutil.copy2(work/'bin/Release/net10.0/Robust.Client.WebView.dll', output/'Robust.Client.WebView.dll')
    print(f'Built native WebKit browser module: {output}')


if __name__ == '__main__':
    main()
