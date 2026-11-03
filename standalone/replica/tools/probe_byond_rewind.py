#!/usr/bin/env python3
"""Run an isolated, scripted BYOND RenderIcon oracle without OS input.

Requires the existing BYOND reference container and private Wine installation.
The prefix must be a disposable test prefix, never the user's normal profile.
Only the named container and that prefix's wineserver are stopped on completion.
The fixture swallows input and reports its observed input count.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('fixture',type=Path)
    parser.add_argument('--prefix',type=Path,required=True)
    parser.add_argument('--wine-bin',type=Path,default=Path('/tmp/dm-runtime-audit/gui-reference/wine/Wine Devel.app/Contents/Resources/wine/bin'))
    parser.add_argument('--dreamseeker',type=Path,default=Path('/tmp/dm-runtime-audit/gui-reference/byond/byond/bin/dreamseeker.exe'))
    parser.add_argument('--port',type=int,default=12185)
    parser.add_argument('--timeout',type=int,default=90)
    args=parser.parse_args();base=args.fixture.resolve();prefix=args.prefix.resolve()
    if '/dm-runtime-audit/' not in str(prefix) or prefix.name!='prefix':
        raise ValueError('Use a disposable prefix beneath /tmp/dm-runtime-audit')
    fixture=base/'rewind.dm'
    source=fixture.read_text()
    if 'client.RenderIcon(O)' not in source or 'REWIND|input|' not in source:
        raise ValueError('Fixture must use scripted RenderIcon and report input')
    before={str(p):sha(p)for p in [fixture,base/'tapestry.dmi',args.dreamseeker]}
    name='dm-rewind-oracle-'+str(args.port)
    env=dict(os.environ,WINEPREFIX=str(prefix),WINEDEBUG='-all')
    compile_command=['docker','run','--rm','--network','none','--memory','1g','--ulimit','core=0','--mount',f'type=bind,src={base},dst=/game','dungeon-master-reference:516.1655','/opt/byond/bin/DreamMaker','/game/rewind.dme']
    with (base/'compile.log').open('w')as log:
        subprocess.run(compile_command,stdout=log,stderr=subprocess.STDOUT,timeout=60,check=True)
    server=None;client=None
    with (base/'server.log').open('w')as serverlog,(base/'client.log').open('w')as clientlog:
        try:
            server=subprocess.Popen(['docker','run','--rm','--name',name,'--memory','1g','--ulimit','core=0','-p',f'127.0.0.1:{args.port}:{args.port}','--mount',f'type=bind,src={base},dst=/game','dungeon-master-reference:516.1655','/opt/byond/bin/DreamDaemon','/game/rewind.dmb',str(args.port),'-trusted','-invisible'],stdout=serverlog,stderr=subprocess.STDOUT)
            time.sleep(2)
            client=subprocess.Popen([str(args.wine_bin/'wine'),str(args.dreamseeker),f'byond://127.0.0.1:{args.port}'],env=env,stdout=clientlog,stderr=subprocess.STDOUT)
            end=time.monotonic()+args.timeout
            while time.monotonic()<end and server.poll()is None:
                if 'REWIND|complete' in (base/'server.log').read_text(errors='replace'):break
                time.sleep(.2)
        finally:
            subprocess.run([str(args.wine_bin/'wineserver'),'-k'],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=10)
            subprocess.run(['docker','stop','--time','2',name],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=10)
            if server:server.wait(timeout=10)
            if client:client.wait(timeout=10)
    log=(base/'server.log').read_text(errors='replace')
    report=dict(scope=__doc__,fixture_sha256=before[str(fixture)],hashes_before=before,
        hashes_after={p:sha(Path(p))for p in before},completed='REWIND|complete' in log,
        observed_input=[int(v)for v in re.findall(r'REWIND\|input\|(\d+)',log)],
        samples=len(re.findall(r'REWIND\|sample\|',log)),
        errors={})
    for name in ('server.log','client.log','ErrorLog.txt'):
        path=base/name
        report['errors'][name]=re.findall(r'(?im)^.*(?:\bruntime error\b|\bexception\b|\bfatal\b).*$',path.read_text(errors='replace'))if path.exists()else[]
    report['passed']=report['completed'] and report['observed_input']==[0] and before==report['hashes_after'] and not any(report['errors'].values())
    (base/'run.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2));return 0 if report['passed']else 1


if __name__=='__main__':raise SystemExit(main())
