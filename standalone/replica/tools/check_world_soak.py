#!/usr/bin/env python3
"""Run the original full maps/event loops for a bounded number of game ticks."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time
from check_browser import stop

ROOT=Path(__file__).resolve().parents[1]
REPORTS=ROOT/'reports'
RUNTIME=ROOT/'runtime/macos-x64'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ticks',type=int,default=11000)
    parser.add_argument('--server-dir',type=Path,default=RUNTIME/'server')
    args=parser.parse_args()
    if args.ticks<1:parser.error('ticks must be positive')
    arena=ROOT/'reference/world-soak';arena.mkdir(exist_ok=True)
    for e in json.loads((REPORTS/'source-baseline.json').read_text()):
        p=Path(e['path'])
        if p.suffix.lower() in ('.sav','.log'):continue
        dest=arena/p;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/'opendream'/p,dest)
    world=arena/'Code/World.dm'
    text=world.read_text(encoding='latin1');assert text.count('\t\tCallSave()')==1
    world.write_text(text.replace('\t\tCallSave()','\t\tCallSave()\n\t\tspawn() ParitySoak()'),encoding='latin1')
    fixture=arena/'world_soak.dme'
    fixture.write_text((arena/'Cave Crawlers.dme').read_text()+'\n#include "world_soak.dm"\n')
    (arena/'world_soak.dm').write_text(f'''proc/ParitySoak()
\tvar/start=world.time
\twhile(world.time-start<{args.ticks})
\t\tvar/mobs=0
\t\tfor(var/mob/M in world) mobs++
\t\tworld.log << "SOAK|tick=[world.time-start]|mobs=[mobs]|season=[Season]|date=[Date]"
\t\tsleep(300)
\tworld.log << "SOAK|complete|ticks=[world.time-start]"
\tshutdown()
''')
    errorlog=arena/'ErrorLog.txt';errorlog.write_text('')
    env=dict(os.environ,DOTNET_ReadyToRun='0');dotnet=RUNTIME/'dotnet/dotnet'
    with (REPORTS/'world-soak-compile.log').open('w') as log:
        subprocess.run([str(dotnet),str(RUNTIME/'compiler/DMCompiler.dll'),str(fixture)],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
    runtime_hash=hashlib.sha256((args.server_dir/'Resources/Assemblies/OpenDreamRuntime.dll').read_bytes()).hexdigest()
    started=time.monotonic();samples=[];server=None
    (REPORTS/'world-soak-checks.json').write_text(json.dumps(dict(status='running',target_ticks=args.ticks,runtime_sha256=runtime_hash),indent=2)+'\n')
    with tempfile.TemporaryDirectory(prefix='dm-soak-') as data,(REPORTS/'world-soak-server.log').open('w') as log:
        try:
            server=subprocess.Popen([str(dotnet),str(args.server_dir/'Robust.Server.dll'),'--data-dir',data,
                '--cvar',f'opendream.json_path={fixture.with_suffix(".json")}','--cvar','opendream.topic_port=25578',
                '--cvar','net.bindto=127.0.0.1','--cvar','net.port=12128','--cvar','auth.mode=0',
                '--cvar','status.enabled=false','--cvar','hub.advertise=false','--cvar','game.auto_pause_empty=false'],
                env=env,stdout=log,stderr=subprocess.STDOUT)
            deadline=time.monotonic()+args.ticks*.1+240;next_sample=0
            while server.poll() is None and time.monotonic()<deadline:
                if time.monotonic()>=next_sample:
                    rss=subprocess.run(['ps','-o','rss=','-p',str(server.pid)],capture_output=True,text=True).stdout.strip()
                    samples.append(dict(seconds=round(time.monotonic()-started,1),rss_kib=int(rss) if rss else None))
                    next_sample=time.monotonic()+30
                time.sleep(1)
        finally:stop(server)
    output=errorlog.read_text(errors='replace');console=(REPORTS/'world-soak-server.log').read_text(errors='replace')
    observations=re.findall(r'SOAK\|[^\r\n]*',output)
    errors=re.findall(r'\[(?:ERRO|FATL)\][^\r\n]*',console)
    completed=any(s.startswith('SOAK|complete') for s in observations)
    # The game's world.log is a file, so also retain non-monitor error output.
    unexpected=[s for s in output.splitlines() if s.strip() and not s.startswith('SOAK|')]
    result=dict(status='passed' if completed and not errors and not unexpected else 'failed',
                passed=completed and not errors and not unexpected,target_ticks=args.ticks,
                seconds=round(time.monotonic()-started,1),runtime_sha256=runtime_hash,
                observations=observations,server_errors=errors,world_log_other_lines=unexpected,
                memory_samples=samples,exclusions=['No connected players; does not certify multiplayer or reference population equivalence.',
                                                 'Duration covers only the event transitions recorded, not every long-period cycle.'])
    shutil.copy2(errorlog,REPORTS/'world-soak-world.log')
    (REPORTS/'world-soak-checks.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
    if not result['passed']:raise SystemExit(1)

if __name__=='__main__':main()
