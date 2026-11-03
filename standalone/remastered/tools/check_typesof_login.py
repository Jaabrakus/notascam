#!/usr/bin/env python3
"""Private full-world Login and native targeting-menu acceptance.

Login and all grant conditions stay unchanged. A test-only observer reads them;
the existing race smoke driver answers the original Restart prompt internally.
No OS input or normal profile is used. The private module opens the real verb
submenu for inspection without selecting any action.
"""
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
from check_mouse import ROOT, RUNTIME, stop, write_hints


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


PROBE = '''var/typesof_incidental_input=0
var/typesof_observer_start=TypesofStartObserver()
proc/TypesofStartObserver()
    spawn(1) TypesofLoginObserver()
    return 1
proc/TypesofLoginObserver()
    while(1)
        for(var/Player/P in Players)
            if(!P.client || !length(P.UnitList)) continue
            var/admin_count=0
            var/clan_count=0
            var/list/native_targets=list()
            for(var/V in typesof(/Admin/verb)) if(V in P.verbs) admin_count++
            for(var/V in typesof(/Clan/verb)) if(V in P.verbs) clan_count++
            for(var/mob/Monsters/M in P.UnitList) native_targets+=!!M.MagicTarget
            var/list/data=list("targetGranted"=!!(/Targeting/verb/SetTarget in P.verbs),"adminCount"=admin_count,"clanCount"=clan_count,"GM"=P.GM,"DE"=P.DE,"clanLeader"=P.IsClanLeader,"adminExpected"=!!(P.client.address in adminlist),"targets"=native_targets,"units"=length(P.UnitList),"incidentalInput"=typesof_incidental_input)
            world.log << "TYPESOF_LOGIN|[json_encode(data)]"
        sleep(5)
client/Click(atom/A,location,control,params)
    typesof_incidental_input++
client/DblClick(atom/A,location,control,params)
    typesof_incidental_input++
client/MouseDrop(atom/A,atom/B,location,over_location,control,over_control,params)
    typesof_incidental_input++
'''


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--server',type=Path,required=True)
    p.add_argument('--module',type=Path,required=True)
    p.add_argument('--label',required=True)
    p.add_argument('--port',type=int,default=12194)
    a=p.parse_args()
    if not re.fullmatch(r'[a-z0-9-]+',a.label):p.error('Use a simple unique label')
    out=ROOT/'tests';dest=out/(a.label+'-checks.json')
    if dest.exists():p.error('Use a fresh report label')
    tracked={'runtime':a.server/'Resources/Assemblies/OpenDreamRuntime.dll','client_zip':a.server/'Content.Client.zip',
             'module':a.module/'Robust.Client.WebView.dll','Login':ROOT/'game/Code/Login.dm',
             'Admin':ROOT/'game/Code/Admin.dm','runner':Path(__file__)}
    report=dict(scope=__doc__,checks={},hashes_before={k:sha(v)for k,v in tracked.items()});checks=report['checks']
    server=client=None
    with tempfile.TemporaryDirectory(prefix='dm-typesof-login-')as temp:
        base=Path(temp);world=base/'world';probe=base/'probe';probe.mkdir()
        shutil.copytree(ROOT/'game',world,ignore=shutil.ignore_patterns('Cave Crawlers.json','*.sav','units','saves','ErrorLog.txt'))
        checks['original_login_and_admin_source_unchanged']=sha(world/'Code/Login.dm')==report['hashes_before']['Login'] and sha(world/'Code/Admin.dm')==report['hashes_before']['Admin']
        checks['all_four_original_maps']=len(list((world/'Maps').glob('*.dmm')))==4
        checks['original_world_startup_unchanged']=sha(world/'Code/World.dm')==sha(ROOT/'game/Code/World.dm')
        (world/'typesof_login_probe.dm').write_text(PROBE)
        dme=world/'Cave Crawlers.dme';dme.write_text(dme.read_text(encoding='latin-1')+'\n#include "typesof_login_probe.dm"\n',encoding='latin-1')
        private=base/'server';shutil.copytree(a.server,private)
        module=base/'module';shutil.copytree(a.module,module)
        cd=base/'client';shutil.copytree(RUNTIME/'client/Space Station 14.app/Contents/Resources',cd,ignore=shutil.ignore_patterns('user_data','.DS_Store'))
        slp,clp=out/(a.label+'-server.log'),out/(a.label+'-client.log')
        def worldlog():
            f=world/'ErrorLog.txt';return f.read_text(errors='replace')if f.exists()else''
        def read(path):
            try:return json.loads(path.read_text())
            except(FileNotFoundError,ValueError):return{}
        def until(fn,seconds):
            end=time.monotonic()+seconds
            while time.monotonic()<end:
                value=fn()
                if value:return value
                if client and client.poll()is not None:raise RuntimeError('Private client exited')
                if server and server.poll()is not None:raise RuntimeError('Private server exited')
                time.sleep(.1)
            raise TimeoutError('Private Login/menu timed out')
        dotnet=RUNTIME/'dotnet/dotnet';env=dict(os.environ,DOTNET_ReadyToRun='0')
        try:
            with(out/(a.label+'-compile.log')).open('w')as log:
                subprocess.run([str(dotnet),str(RUNTIME/'compiler/DMCompiler.dll'),str(dme)],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=180,check=True)
            hints=base/'layout.json';write_hints(world/'skin.dmf',hints)
            env.update(DM_NATIVE_UI_PROBE=str(probe),DM_TYPESOF_LOGIN_PROBE='1',DM_SKIN_LAYOUT_HINTS=str(hints),DM_TEST_RACE='Human',DM_GAME_SNAPSHOT=str(probe/'startup.png'),DM_NATIVE_UI_TEST_TITLE='Remastered - Private Login Verb Audit',ROBUST_MODULE_ROBUST_CLIENT_WEBVIEW=str(module))
            with slp.open('w')as sl,clp.open('w')as cl:
                server=subprocess.Popen([str(dotnet),str(private/'Robust.Server.dll'),'--data-dir',str(base/'server-data'),'--cvar',f'opendream.json_path={dme.with_suffix(".json")}','--cvar',f'net.port={a.port}','--cvar',f'opendream.topic_port={a.port+13500}','--cvar','net.bindto=127.0.0.1','--cvar','auth.mode=0','--cvar','status.enabled=false','--cvar','hub.advertise=false','--cvar','game.auto_pause_empty=false'],cwd=world,env=env,stdout=sl,stderr=subprocess.STDOUT)
                until(lambda:' -> Ready'in slp.read_text(errors='replace'),90)
                client=subprocess.Popen([str(dotnet),str(cd/'Robust.Client.dll'),'--mount-zip',str(private/'Content.Client.zip'),'--connect','--connect-address',f'udp://127.0.0.1:{a.port}','--username','TypesofLogin','--self-contained','--cvar','web.headless=false','--cvar','discord.enabled=false'],cwd=cd,env=env,stdout=cl,stderr=subprocess.STDOUT)
                menu=until(lambda:read(probe/'login-verbs.json'),120);time.sleep(1)
                rows=[json.loads(x)for x in re.findall(r'TYPESOF_LOGIN\|([^\r\n]+)',worldlog()+'\n'+slp.read_text(errors='replace'))]
                report.update(menu=menu,observations=rows)
                checks['original_login_grants_target']=bool(rows and rows[-1]['targetGranted'])
                checks['original_starting_army_created']=bool(rows and rows[-1]['units']==3)
                checks['native_executable_target_available']=any(v['name']=='SetTarget'for v in menu['executable'])
                checks['native_target_filter_includes_command']=any(v['name']=='SetTarget'for v in menu['targeted'])
                checks['original_native_submenu_has_target']=bool('SetTarget'in menu['menuButtons'])
                checks['menu_inspection_does_not_execute']=bool(rows and not any(rows[-1]['targets']))
                checks['admin_grant_condition_preserved']=bool(rows and all(bool(r['GM'])==bool(r['adminExpected']) and (r['adminExpected']or r['adminCount']==0)for r in rows))
                checks['clan_grant_condition_preserved']=bool(rows and all(r['clanLeader']or r['clanCount']==0 for r in rows))
                checks['no_incidental_map_input']=bool(rows and all(r['incidentalInput']==0 for r in rows))
                (probe/'capture.txt').write_text('native-target-menu.png')
                until(lambda:(probe/'native-target-menu.png').exists(),10)
                time.sleep(.3)
                shutil.copy2(probe/'native-target-menu.png',out/(a.label+'-menu.png'))
        except Exception as error:report['error']=repr(error)
        finally:
            # Stop the server first, so closing the test client cannot write a
            # private Logout save. Normal-profile files are never referenced.
            stop(server);stop(client)
            (out/(a.label+'-world.log')).write_text(worldlog())
            for name in ('state.json','login-verbs.json'):
                if(probe/name).exists():shutil.copy2(probe/name,out/(a.label+'-'+name))
            report['private_saves']=[str(x.relative_to(world))for x in world.rglob('*.sav')]
        report['errors']={k:re.findall(r'(?im)^.*(?:\[(?:ERRO|FATL)\]|\bruntime error\b|\bexception\b).*$',v.read_text(errors='replace'))for k,v in [('server',slp),('client',clp),('world',out/(a.label+'-world.log'))]if v.exists()}
        report['native_events']=re.findall(r'native.ui.probe: (?:engine key|event)[^\r\n]*',clp.read_text(errors='replace')if clp.exists()else'')
        checks['no_os_input_events']=not report['native_events']
        checks['private_processes_stopped']=all(x is None or x.poll()is not None for x in (server,client))
    report['hashes_after']={k:sha(v)for k,v in tracked.items()};checks['sources_and_runtime_unchanged']=report['hashes_before']==report['hashes_after']
    report['passed']=bool(checks.get('original_starting_army_created'))and all(checks.values())and not report.get('error')and not any(report['errors'].values())
    dest.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(report=str(dest),passed=report['passed'],checks=len(checks),failures=[k for k,v in checks.items()if not v],error=report.get('error'),errors=report['errors']),indent=2))
    return 0 if report['passed']else 1


if __name__=='__main__':raise SystemExit(main())
