#!/usr/bin/env python3
"""Run the actual client frame selector headlessly against original DMI assets."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sdk', type=Path, required=True)
    parser.add_argument('--assemblies', type=Path, required=True)
    parser.add_argument('--build-dir', type=Path, required=True)
    parser.add_argument('--label', default='current')
    args = parser.parse_args()
    work = args.build_dir.resolve()
    work.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / 'engine/CheckMovement.cs', work / 'CheckMovement.cs')
    (work / 'CheckMovement.csproj').write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net10.0</TargetFramework><EnableDefaultCompileItems>false</EnableDefaultCompileItems></PropertyGroup><ItemGroup><Compile Include="CheckMovement.cs"/></ItemGroup></Project>')
    game = ROOT.parent / 'remastered/game'
    specs = []
    for name, path, state, movement in [
        ('human-default-fallback', 'Icons/Human.dmi', 'Normal', True),
        ('orc-normal', 'Icons/Orc.dmi', 'Normal', True),
        ('hair-overlay', 'Code/Creatures/Icons/Hair.dmi', 'HumanBrown', True),
        ('water-loop', 'Icons/water.dmi', 'water', False),
        ('fire-loop', 'Icons/Cave.dmi', 'Fire', False),
    ]:
        specs.append(dict(name=name, path=str(game / path), state=state, movement=movement, sha256=sha(game / path)))
    generated = ROOT / 'reference/generated-icons/movement-metadata'
    for name in ('real-human', 'real-chestplate'):
        asset = generated / (name + '-generated.dmi')
        if asset.exists():
            specs.append(dict(name='generated-' + name, path=str(asset), state='', movement=True, sha256=sha(asset)))
    (work / 'cases.json').write_text(json.dumps(specs, indent=2) + '\n')
    client = ROOT / 'runtime/macos-x64/client/Space Station 14.app/Contents/Resources'
    server = ROOT / 'runtime/macos-x64/server'
    dirs = [args.assemblies.resolve(), work / 'refs', client, server / 'Resources/Assemblies', server]
    # Published package dependencies include the matching Robust.Client.dll.
    import zipfile
    (work / 'refs').mkdir(exist_ok=True)
    with zipfile.ZipFile(server / 'Content.Client.zip') as archive:
        for entry in archive.namelist():
            if entry.endswith('.dll'):
                (work / 'refs' / Path(entry).name).write_bytes(archive.read(entry))
    env = dict(os.environ, DOTNET_CLI_HOME=str(work / 'sdk-home'), DOTNET_CLI_TELEMETRY_OPTOUT='1', DOTNET_GENERATE_ASPNET_CERTIFICATE='false', DOTNET_SKIP_FIRST_TIME_EXPERIENCE='1')
    with (work / 'build.log').open('w') as log:
        subprocess.run([str(args.sdk), 'build', str(work / 'CheckMovement.csproj'), '-c', 'Release', '--ignore-failed-sources'], env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
    result = subprocess.run([str(ROOT / 'runtime/macos-x64/dotnet/dotnet'), str(work / 'bin/Release/net10.0/CheckMovement.dll'), os.pathsep.join(map(str, dirs)), str(work / 'cases.json'), str(work / 'results.json')], env=env, text=True, capture_output=True)
    (work / 'probe.log').write_text(result.stdout + result.stderr)
    cases = json.loads((work / 'results.json').read_text()) if (work / 'results.json').exists() else []
    original_unchanged = all(sha(Path(s['path'])) == s['sha256'] for s in specs)
    report = dict(passed=result.returncode == 0 and original_unchanged, exit_code=result.returncode,
                  client_sha256=sha(args.assemblies / 'OpenDreamClient.dll'), shared_sha256=sha(args.assemblies / 'OpenDreamShared.dll'),
                  original_art_unchanged=original_unchanged, assets=specs, cases=cases,
                  known_limitations=['Full DMI loop-count and rewind parity is not covered. Duplicate idle/walking state pixels, texture selection and generated-icon preservation are covered separately by check_dmi_variants.py.'],
                  scope='Real client GetAnimationFrame and SetMovementActive methods with controlled game clock for movement-only bodies/equipment and ordinary scenery; no graphics or user input. Actual glide lifecycle is verified separately by the native lifecycle fixture.')
    target = ROOT / 'reports' / ('movement-animation-' + args.label + '-checks.json')
    target.write_text(json.dumps(report, indent=2) + '\n')
    print(result.stdout)
    if result.stderr: print(result.stderr)
    print(json.dumps(dict(passed=report['passed'], checks=len(cases), report=str(target)), indent=2))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
