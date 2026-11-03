#!/usr/bin/env python3
"""Launch a relocated package twice with development paths denied to the game."""
import hashlib
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time

ROOT=Path(__file__).resolve().parents[1]
REPORTS=ROOT/'reports'


def saved_units(path):
    nodes=json.loads(path.read_text())['_nodes'];table=nodes['.opendream_graph']['Objects']
    refs=table[nodes['UnitList']['Id']]['Values'];result=[]
    for ref in refs:
        unit=table[ref['Id']];fields=unit['Fields']['_nodes']
        values={k:fields.get(k,{}).get('Value',{}).get('Value') for k in
            ('name','Race','HP','MAXHP','Level','savedx','savedy','savedz','HasLeftArm','HasRightArm','HasLeftLeg','HasRightLeg')}
        inventory=table[fields['contents']['Id']]['Values']
        values['inventory']=[dict(type=table[item['Id']]['Type'],
            equipped=table[item['Id']]['Fields']['_nodes'].get('suffix',{}).get('Value',{}).get('Value')) for item in inventory]
        result.append(values)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--race',choices=('Human','Orc'),default='Human')
    parser.add_argument('--app',type=Path,default=ROOT/'Dungeon Master.app')
    parser.add_argument('--shared',action='store_true',help='check a shareable build: no --username, so it names the player itself')
    args=parser.parse_args()
    prefix=('share-' if args.shared else '')+('package' if args.race=='Human' else 'package-orc')
    app=args.app
    runtime=app/'Contents/Resources/game/runtime/server/Resources/Assemblies/OpenDreamRuntime.dll'
    result=dict(status='running',runtime_sha256=hashlib.sha256(runtime.read_bytes()).hexdigest(),
        launcher_sha256=hashlib.sha256((app/'Contents/MacOS/DungeonMaster').read_bytes()).hexdigest(),
        launch_script_sha256=hashlib.sha256((app/'Contents/Resources/launch.zsh').read_bytes()).hexdigest(),exact_replica_verified=False)
    report=REPORTS/(('mac-app-share-' if args.shared else 'mac-app-')+('checks.json' if args.race=='Human' else 'orc-checks.json'));report.write_text(json.dumps(result,indent=2)+'\n')
    result['race']=args.race
    result['client_package_sha256']=hashlib.sha256((app/'Contents/Resources/game/runtime/server/Content.Client.zip').read_bytes()).hexdigest()
    with tempfile.TemporaryDirectory(prefix='dm-app-release-') as work:
        work=Path(work);relocated=work/app.name;shutil.copytree(app,relocated)
        data=work/'profile';exe=relocated/'Contents/MacOS/DungeonMaster'
        denied=[str(ROOT),'/private/tmp/dm-runtime-audit','/Applications/Xcode.app','/Library/Developer/CommandLineTools','/opt/homebrew','/usr/local/share/dotnet','/Users/kiwimango/.dotnet']
        profile='(version 1)(allow default)(deny file-write* (subpath '+json.dumps(str(relocated.resolve()))+'))'+''.join('(deny file-read* (subpath '+json.dumps(p)+'))' for p in denied)
        env=dict(os.environ,PATH='/usr/bin:/bin:/usr/sbin:/sbin',DM_STANDALONE_DATA_DIR=str(data))
        env.pop('DOTNET_ROOT',None);env.pop('DOTNET_HOST_PATH',None)
        phases={}
        for phase,duration in [('save',40),('reload',25)]:
            session=dict(env,DM_GAME_SNAPSHOT=str(work/(phase+'.png')))
            if phase=='save':session['DM_TEST_RACE']=args.race
            else:session.pop('DM_TEST_RACE',None)
            started=time.monotonic()
            with (REPORTS/f'{prefix}-{phase}-process.log').open('w') as log:
                proc=subprocess.Popen(['/usr/bin/sandbox-exec','-p',profile,str(exe),*([] if args.shared else ['--username','PackageVerification']),'--smoke-seconds',str(duration)],
                    cwd=work,env=session,stdout=log,stderr=subprocess.STDOUT)
                try:code=proc.wait(timeout=210)
                except subprocess.TimeoutExpired:
                    proc.terminate()
                    try:proc.wait(timeout=30)
                    except subprocess.TimeoutExpired:proc.kill();proc.wait()
                    raise RuntimeError('Packaged game did not shut down in time')
            logs={name:(data/'reports'/name).read_text(errors='replace') for name in ('launcher.log','server.log','client.log')}
            for name,contents in logs.items():(REPORTS/f'{prefix}-{phase}-{name}').write_text(contents)
            player=re.sub(r'[^A-Za-z0-9]','',os.environ.get('USER','')).lower() if args.shared else 'packageverification'
            save=data/f'world/units/localhost@{player}_save.sav'
            snapshot=work/(phase+'.png')
            if snapshot.exists():shutil.copy2(snapshot,REPORTS/f'{prefix}-{phase}.png')
            errors={name:re.findall(r'\[(?:ERRO|FATL)\][^\r\n]*',body) for name,body in logs.items()}
            phases[phase]=dict(exit_code=code,seconds=round(time.monotonic()-started,1),
                server_ready=' -> Ready' in logs['server.log'],client_in_game='Runlevel changed to: InGame' in logs['client.log'],
                browser_loaded='loaded panel=' in logs['client.log'],save_acknowledged=(data/'reports/save-status').read_text().strip()=='saved',
                units=saved_units(save) if save.exists() else [],errors=errors,snapshot=snapshot.exists())
            if save.exists():shutil.copy2(save,REPORTS/f'{prefix}-{phase}.sav')
            if code or not phases[phase]['save_acknowledged']:break
        passed=len(phases)==2 and all(p['exit_code']==0 and p['server_ready'] and p['client_in_game'] and p['browser_loaded'] and p['save_acknowledged'] and len(p['units'])==3 and all(u['Race']==args.race for u in p['units']) and not any(p['errors'].values()) for p in phases.values())
        position_fields=('savedx','savedy','savedz')
        def durable(units):return [{k:v for k,v in u.items() if k not in position_fields} for u in units]
        durable_match=len(phases)==2 and durable(phases['save']['units'])==durable(phases['reload']['units'])
        passed=passed and durable_match
        position_changes=[]
        if len(phases)==2:
            for index,(before,after) in enumerate(zip(phases['save']['units'],phases['reload']['units'])):
                if any(before[k]!=after[k] for k in position_fields):
                    position_changes.append(dict(unit=index,before=[before[k] for k in position_fields],after=[after[k] for k in position_fields]))
        result.update(status='passed' if passed else 'failed',passed=passed,phases=phases,
            package_relocated=True,package_writes_denied=True,system_only_path=env['PATH'],denied_read_paths=denied,
            durable_unit_fields_match=durable_match,position_changes=position_changes,
            exclusions=['Sandbox denies development paths; development tools were not uninstalled from this Mac.',
                        'Uses the original race prompt with test-only input automation; does not certify physical input or visual equality.',
                        f'Only the {args.race} startup/save/reload branch is exercised here.',
                        'Coordinates after 25 seconds of live simulation are recorded but excluded from equality. Exact immediate reload coordinates remain a separate comparison.'])
    report.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
    if not result['passed']:raise SystemExit(1)

if __name__=='__main__':main()
