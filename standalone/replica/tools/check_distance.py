#!/usr/bin/env python3
"""Compare get_dist tile/endpoint semantics to an isolated BYOND516.1655 oracle."""
import argparse, hashlib, json, os, re, shutil, subprocess, tempfile, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
RUNTIME=ROOT/'runtime/macos-x64'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(arena,engine,compiler,server,port):
    env=dict(os.environ,DOTNET_ReadyToRun='0')
    docker=['docker','run','--rm','--network','none','--memory','1g','--ulimit','core=0','--mount',f'type=bind,src={arena},dst=/game']
    if engine=='byond':command=docker+['dungeon-master-reference:516.1655','/opt/byond/bin/DreamMaker','/game/audit.dme']
    else:command=[str(RUNTIME/'dotnet/dotnet'),str(compiler/'DMCompiler.dll'),str(arena/'audit.dme')]
    with (arena/'compile.log').open('w') as log:subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=60)
    container='dm-distance-'+str(os.getpid())
    if engine=='byond':command=docker+['--name',container,'dungeon-master-reference:516.1655','/opt/byond/bin/DreamDaemon','/game/audit.dmb','0','-trusted','-invisible','-close']
    else:command=[str(RUNTIME/'dotnet/dotnet'),str(server/'Robust.Server.dll'),'--data-dir',str(arena/'private-data'),'--cvar',f'opendream.json_path={arena/"audit.json"}','--cvar',f'net.port={port}','--cvar',f'opendream.topic_port={port+13500}','--cvar','net.bindto=127.0.0.1','--cvar','auth.mode=0','--cvar','status.enabled=false','--cvar','hub.advertise=false','--cvar','game.auto_pause_empty=false']
    with (arena/'server.log').open('w') as log:
        process=subprocess.Popen(command,cwd=arena,env=env,stdout=log,stderr=subprocess.STDOUT)
        try:
            end=time.monotonic()+40
            while process.poll() is None and time.monotonic()<end:
                if 'DMI_AUDIT|complete' in (arena/'server.log').read_text():break
                time.sleep(.1)
        finally:
            if engine=='byond':subprocess.run(['docker','stop','--time','2',container],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=10)
            elif process.poll() is None:process.terminate()
            try:process.wait(timeout=10)
            except subprocess.TimeoutExpired:process.kill();process.wait()
    if 'DMI_AUDIT|complete' not in (arena/'server.log').read_text():raise RuntimeError(engine+' did not complete')
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--compiler',type=Path,default=RUNTIME/'compiler');p.add_argument('--server',type=Path,default=RUNTIME/'server');p.add_argument('--label',required=True);p.add_argument('--port',type=int,default=12198);p.add_argument('--reuse-reference',type=Path);a=p.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_-]+',a.label):p.error('simple unique label required')
    dest=ROOT/'reference/get-dist'/a.label;dest.mkdir(parents=True,exist_ok=False)
    tracked={'compiler':a.compiler/'DMCompiler.dll','standard':a.compiler/'DMStandard/_Standard.dm','runtime':a.server/'Resources/Assemblies/OpenDreamRuntime.dll','fixture':ROOT/'reference/fixtures/distance.dme','harness':Path(__file__)}
    report=dict(hashes_before={k:sha(v) for k,v in tracked.items()},scope=__doc__)
    for engine in ['byond','replacement']:
        arena=dest/engine;arena.mkdir()
        if engine=='byond' and a.reuse_reference:shutil.copytree(a.reuse_reference,arena,dirs_exist_ok=True)
        else:shutil.copy2(tracked['fixture'],arena/'audit.dme');run(arena,engine,a.compiler.resolve(),a.server.resolve(),a.port)
    rows={}
    for engine in ['byond','replacement']:
        rows[engine]={r['id']:r for r in [json.loads(line.split('DIST|')[1]) for line in (dest/engine/'server.log').read_text().splitlines() if 'DIST|' in line]}
    report['cases']={k:dict(reference=v,replacement=rows['replacement'].get(k),matches=v==rows['replacement'].get(k)) for k,v in rows['byond'].items()}
    report['errors']={engine:re.findall(r'(?im)^.*(?:\[(?:ERRO|FATL)\]|\bruntime error\b|\bexception\b).*$',(dest/engine/'server.log').read_text()) for engine in rows}
    report['hashes_after']={k:sha(v) for k,v in tracked.items()};report['stable']=report['hashes_before']==report['hashes_after'];report['known_placement_limits']={k:report['cases'][k] for k in ('inside-area','nested-inside-area')}
    report['placement_evidence']={engine:[line.split('POSITION|')[1] for line in (dest/engine/'server.log').read_text().splitlines() if 'POSITION|' in line] for engine in rows}
    report['required_cases']=[k for k in report['cases'] if k not in report['known_placement_limits']]
    report['full_parity']=all(v['matches'] for v in report['cases'].values())
    report['limitations']=['Direct object creation in an area places it on a turf in BYOND, but leaves it in the area in OpenDream. Those two calls start at different coordinates and are retained separately as a pre-existing constructor placement gap.']
    report['passed']=bool(report['cases']) and report['stable'] and all(report['cases'][k]['matches'] for k in report['required_cases']) and not any(report['errors'].values())
    path=ROOT/'reports'/('distance-'+a.label+'-checks.json');path.parent.mkdir(exist_ok=True);path.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(passed=report['passed'],cases=len(report['cases']),required_cases=len(report['required_cases']),failures=[k for k in report['required_cases'] if not report['cases'][k]['matches']],known_placement_limits=report['known_placement_limits'],errors=report['errors'],report=str(path)),indent=2));return 0 if report['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
