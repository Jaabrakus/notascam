#!/usr/bin/env python3
"""Run the measured fidelity suite and write one honest coverage report."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference',action='store_true')
    parser.add_argument('--full',action='store_true',help='Also run browser, connected save/reload and full-world checks')
    parser.add_argument('--server-dir',type=Path,default=ROOT/'runtime/macos-x64/server')
    args=parser.parse_args()
    report_path=ROOT/'reports/fidelity-checks.json'
    started=datetime.now(timezone.utc).isoformat()
    report_path.write_text(json.dumps({'status':'running','started':started,'exact_replica_verified':False},indent=2)+'\n')
    def run(script,*options):
        try:
            subprocess.run([sys.executable,str(ROOT/'tools'/script),*[str(o) for o in options]],check=True)
        except subprocess.CalledProcessError as error:
            report_path.write_text(json.dumps({'status':'failed','started':started,'exact_replica_verified':False,
                'failed_check':script,'options':[str(o) for o in options],'exit_code':error.returncode},indent=2)+'\n')
            raise
    run('prepare_gameplay_fixture.py')
    run('prepare_gameplay_fixture.py','--fixture','systems')
    run('prepare_semantic_fixtures.py')
    run('prepare_crafting_fixture.py')
    run('prepare_crafting_fixture.py','--races')
    run('prepare_gameplay_fixture.py','--fixture','idle')
    run('prepare_gameplay_fixture.py','--fixture','turf_contents')
    run('prepare_gameplay_fixture.py','--fixture','pickup_crowd')
    names=('persistence','coordinates','movement','gameplay','systems','branching','repopulation','map_layout','text_io','reboot','randomness','output_targets','contents_order','icon_turn','bump_reentry','deleted_refs','self_call','random_step_blocked','wander_invariants','compiler_edges','crafting','crafting_races','idle','turf_contents','pickup_crowd','bump_target')
    for name in names:
        options=[name,'--server-dir',args.server_dir]
        if args.reference: options+=['--reference','--reference-timeout','1800']
        if name in ('gameplay','systems','branching','crafting','crafting_races','idle','turf_contents','pickup_crowd'):
            options+=['--fixture-dir',ROOT/f'reference/{name}-opendream',
                      '--reference-dir',ROOT/f'reference/{name}-byond']
        if name=='gameplay':options+=['--reload']
        if name=='reboot':options+=['--supervised']
        run('check_parity.py',*options)
    run('check_wandering.py','--server-dir',args.server_dir,*(['--reference'] if args.reference else []))
    run('check_icon_assets.py',*(['--reference'] if args.reference else []))
    run('check_maps.py')
    run('audit_coverage.py')
    if args.full:
        run('check_lifecycle.py','--server-dir',args.server_dir)
        run('check_client_gameplay.py','--server-dir',args.server_dir)
        run('check_browser.py','--legacy')
        run('check_native_ui.py','--server-dir',args.server_dir)
        run('check_client_crafting.py','--server-dir',args.server_dir)
        run('check_dblclick.py','--server-dir',args.server_dir)
        runtime=ROOT/'runtime/macos-x64'
        run('check_foundation.py','--dotnet',runtime/'dotnet/dotnet','--compiler',runtime/'compiler/DMCompiler.dll',
            '--server-dotnet',runtime/'dotnet/dotnet','--server',args.server_dir/'Robust.Server.dll')
    results={name:json.loads((ROOT/'reports'/f'{name}-parity.json').read_text())
             for name in (*names,'gameplay_reload')}
    report={'status':'passed','started':started,'finished':datetime.now(timezone.utc).isoformat(),
            'exact_replica_verified':False,'ordered_observations_match':all(r['matches'] for r in results.values()),
            'observations_excluding_completion_markers':sum(len(r['expected'])-1 for r in results.values()),
            'fixtures':{k:{'matches':v['matches'],'errors':v['errors']} for k,v in results.items()},
            'runtime_sha256':hashlib.sha256((args.server_dir/'Resources/Assemblies/OpenDreamRuntime.dll').read_bytes()).hexdigest(),
            'client_package_sha256':hashlib.sha256((args.server_dir/'Content.Client.zip').read_bytes()).hexdigest(),
            'webview_sha256':hashlib.sha256((ROOT/'runtime/macos-x64/webview-webkit/Robust.Client.WebView.dll').read_bytes()).hexdigest(),
            'full_checks_run':args.full,
            'coverage_and_limits':'PARITY.md',
            'icons':json.loads((ROOT/'reports/icon-assets-checks.json').read_text())['passed'],
            'wandering_open_terrain':json.loads((ROOT/'reports/wandering-checks.json').read_text())['passed'],
            'maps':json.loads((ROOT/'reports/map-geometry-checks.json').read_text())['passed']}
    if args.full:
        report['two_client_reboot']=json.loads((ROOT/'reports/lifecycle-checks.json').read_text())['passed']
        report['connected_save_reload']=json.loads((ROOT/'reports/client-gameplay-checks.json').read_text())['passed']
        report['full_world']=json.loads((ROOT/'reports/foundation-checks.json').read_text())
        report['browser']=json.loads((ROOT/'reports/browser-checks.json').read_text())
        report['native_ui']=json.loads((ROOT/'reports/native-ui-checks.json').read_text())['passed']
        report['client_crafting']=json.loads((ROOT/'reports/client-crafting-checks.json').read_text())['passed']
    (ROOT/'reports/fidelity-checks.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__': main()
