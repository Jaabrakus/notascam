#!/usr/bin/env python3
"""Capture bounded original-engine full-world behavior, including original errors."""
import argparse,json,re,shutil,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ticks',type=int,default=600)
    args=parser.parse_args()
    arena=ROOT/'reference/world-soak-byond';arena.mkdir(exist_ok=True)
    for e in json.loads((ROOT/'reports/source-baseline.json').read_text()):
        p=Path(e['path'])
        if p.suffix.lower() in ('.sav','.log'):continue
        dest=arena/p;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/'source'/p,dest)
    p=arena/'Code/World.dm';s=p.read_text(encoding='latin1')
    p.write_text(s.replace('\t\tCallSave()','\t\tCallSave()\n\t\tspawn() ParitySoak()'),encoding='latin1')
    (arena/'world_soak.dme').write_text((arena/'Cave Crawlers.dme').read_text()+'\n#include "world_soak.dm"\n')
    (arena/'world_soak.dm').write_text(f'''proc/ParitySoak()
\tvar/start=world.time
\twhile(world.time-start<{args.ticks})
\t\tvar/mobs=0
\t\tfor(var/mob/M in world) mobs++
\t\tworld.log << "SOAK|tick=[world.time-start]|mobs=[mobs]|season=[Season]|date=[Date]"
\t\tsleep(100)
\tworld.log << "SOAK|complete|ticks=[world.time-start]"
\tshutdown()
''')
    errorlog=arena/'ErrorLog.txt';errorlog.write_text('')
    prefix=['docker','run','--rm','--network','none','--memory','3g','--ulimit','core=0','--mount',f'type=bind,src={arena},dst=/game']
    image='dungeon-master-reference:516.1655'
    with (ROOT/'reports/world-reference-compile.log').open('w') as log:
        subprocess.run(prefix+[image,'/opt/byond/bin/DreamMaker','/game/world_soak.dme'],stdout=log,stderr=subprocess.STDOUT,check=True)
    container='dm-world-reference'
    with (ROOT/'reports/world-reference-console.log').open('w') as log:
        process=subprocess.Popen(prefix+['--name',container,image,'/opt/byond/bin/DreamDaemon','/game/world_soak.dmb','0','-trusted','-invisible','-close'],stdout=log,stderr=subprocess.STDOUT)
        try:
            end=time.monotonic()+args.ticks*.1+180
            while process.poll() is None and time.monotonic()<end:
                if 'SOAK|complete' in errorlog.read_text(errors='replace'):break
                time.sleep(1)
        finally:
            subprocess.run(['docker','stop','-t','1',container],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            process.wait(timeout=10)
    output=errorlog.read_text(errors='replace');shutil.copy2(errorlog,ROOT/'reports/world-reference-world.log')
    result=dict(completed='SOAK|complete' in output,observations=re.findall(r'SOAK\|[^\r\n]*',output),runtime_errors=re.findall(r'runtime error: [^\r\n]*',output))
    (ROOT/'reports/world-reference-checks.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
