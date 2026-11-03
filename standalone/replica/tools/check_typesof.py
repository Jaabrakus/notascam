#!/usr/bin/env python3
"""Compare direct proc/verb groups with BYOND in isolated headless worlds.

Original game sources and normal profiles are never changed. Global /proc
enumeration is recorded as a pre-existing limitation outside the login fix.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import tempfile

from audit_dmi_edge_cases import run_byond, run_replacement

ROOT = Path(__file__).resolve().parents[1]
GAME = ROOT.parent / 'remastered/game'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_rows(path):
    return {row['id']: row for row in
            (json.loads(line.split('TYPESOF|', 1)[1])
             for line in path.read_text(errors='replace').splitlines() if 'TYPESOF|' in line)}


def prepare_game(arena):
    shutil.copytree(GAME, arena, ignore=shutil.ignore_patterns(
        'Cave Crawlers.json', '*.dmm', '*.sav', 'units', 'saves', 'ErrorLog.txt'))
    world = arena / 'Code/World.dm'
    text = world.read_text(encoding='latin-1')
    start, end = text.index('\tNew()'), text.index('\nvar/Season')
    world.write_text(text[:start] + '\tNew()\n\t\tspawn(0) TypesofAudit()\n' + text[end:], encoding='latin-1')
    # The two existing StopAll definitions compile in the replacement engine;
    # BYOND rejects them. The unused old definition is renamed in both copies.
    verbs = arena / 'Code/Verbs.dm'
    verbs.write_text(verbs.read_text(encoding='latin-1').replace(
        'mob/verb/StopAll()', 'mob/verb/AuditUnusedLegacyStopAll()'), encoding='latin-1')
    fixture = '''var/parity_race
proc/TypesofObserve(ID,list/result,error=null)
    var/list/values=list()
    for(var/value in result)
        values+=list(list("text"="[value]","ispath"=!!ispath(value)))
    world.log << "TYPESOF|[json_encode(list("id"=ID,"values"=values,"error"=error))]"
proc/TypesofAudit()
'''
    for name, path in [('target', '/Targeting'), ('admin', '/Admin'), ('clan', '/Clan'),
                       ('terrain', '/TurfCreate'), ('spawn', '/mob/Spawn'),
                       ('misc', '/MiscCreate'), ('developer', '/mob/Developer')]:
        for mode, value in [('literal', path + '/verb'), ('string', '"' + path + '/verb"'),
                            ('trailing', '"' + path + '/verb/"')]:
            identifier = name + '-' + mode
            error_var = 'error_' + name + '_' + mode
            fixture += f'    try\n        TypesofObserve("{identifier}",typesof({value}))\n'
            fixture += f'    catch(var/{error_var})\n        TypesofObserve("{identifier}",list(),"[{error_var}]")\n'
    fixture += '''    var/Player/P=new
    var/initial_target=(/Targeting/verb/SetTarget in P.verbs)
    P.verbs+=typesof(/Targeting/verb/)
    world.log << "TYPESOF|[json_encode(list("id"="target-grant","values"=list(initial_target,!!(/Targeting/verb/SetTarget in P.verbs)),"error"=null))]"
    world.log << "DMI_AUDIT|complete"
    shutdown()
'''
    (arena / 'typesof_probe.dm').write_text(fixture)
    dme = re.sub(r'^#include .*\.dmm"\s*$', '',
                 (arena / 'Cave Crawlers.dme').read_text(encoding='latin-1'), flags=re.M)
    (arena / 'audit.dme').write_text(dme + '\n#include "typesof_probe.dm"\n', encoding='latin-1')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--server', type=Path, required=True)
    p.add_argument('--label', required=True)
    p.add_argument('--port', type=int, default=12193)
    p.add_argument('--reuse-reference', type=Path)
    a = p.parse_args()
    if not re.fullmatch(r'[a-z0-9-]+', a.label): p.error('Use a simple unique label')
    dest = ROOT / 'reference/typesof' / a.label
    dest.mkdir(exist_ok=False)
    tracked = {str(x.relative_to(GAME)): sha(x) for x in GAME.rglob('*.dm')}
    runtime = a.server / 'Resources/Assemblies/OpenDreamRuntime.dll'
    report = dict(scope=__doc__, runtime_sha256=sha(runtime), sources_before=tracked,
                  compiler_sha256=sha(ROOT / 'runtime/macos-x64/compiler/DMCompiler.dll'), cases={}, checks={}, errors={})
    for kind in ('core', 'game'):
        for engine in ('byond', 'replacement'):
            output = dest / kind / engine
            output.mkdir(parents=True)
            if engine == 'byond' and a.reuse_reference:
                shutil.copytree(a.reuse_reference / kind / engine, output, dirs_exist_ok=True)
                continue
            with tempfile.TemporaryDirectory(prefix='dm-typesof-') as temp:
                arena = Path(temp) / 'world'
                if kind == 'core':
                    arena.mkdir()
                    shutil.copy2(ROOT / 'reference/typesof/core.dme', arena / 'audit.dme')
                else:
                    prepare_game(arena)
                try:
                    if engine == 'byond': run_byond(arena)
                    else: run_replacement(arena, a.server.resolve(), a.port)
                finally:
                    for name in ('compile.log', 'server.log', 'ErrorLog.txt', 'audit.dme', 'typesof_probe.dm'):
                        if (arena / name).exists(): shutil.copy2(arena / name, output / name)
                report['checks'][kind + '-' + engine + '-no-save'] = not list(arena.rglob('*.sav'))
        before = read_rows(dest / kind / 'byond/server.log')
        after = read_rows(dest / kind / 'replacement/server.log')
        report['cases'][kind] = {key: dict(reference=value, replacement=after.get(key), matches=value == after.get(key))
                                 for key, value in before.items()}
        for key, value in report['cases'][kind].items():
            if key not in ('global-procs', 'global-procs-string'):
                report['checks'][kind + '-' + key] = value['matches']
        for engine in ('byond', 'replacement'):
            logs = '\n'.join(x.read_text(errors='replace') for x in (dest / kind / engine).glob('*.log') if x.name != 'compile.log')
            report['errors'][kind + '-' + engine] = re.findall(r'(?im)^.*(?:\[(?:ERRO|FATL)\]|\bruntime error\b|\bexception\b).*$', logs)
    report['checks']['source-unchanged'] = tracked == {str(x.relative_to(GAME)): sha(x) for x in GAME.rglob('*.dm')}
    report['checks']['runtime-unchanged'] = report['runtime_sha256'] == sha(runtime)
    report['passed'] = all(report['checks'].values()) and not any(report['errors'].values())
    path = ROOT / 'reports' / ('typesof-' + a.label + '-checks.json')
    path.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(dict(report=str(path), passed=report['passed'], checks=len(report['checks']),
                          failures=[k for k, v in report['checks'].items() if not v], errors=report['errors']), indent=2))
    return 0 if report['passed'] else 1


if __name__ == '__main__': raise SystemExit(main())
