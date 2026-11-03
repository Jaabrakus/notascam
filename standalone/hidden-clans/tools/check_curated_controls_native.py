#!/usr/bin/env python3
"""Native WebKit curated Controls -> real Topic -> original prompts/effects.

Only a private copied HTML gains an observation function that clicks existing
DOM buttons. Native prompt responses use the isolated diagnostic UI callbacks;
text uses the real LineEdit setter, not physical typing. No OS input or saves.
"""
import argparse, hashlib, json, os, re, shutil, subprocess, tempfile, time, zipfile
from pathlib import Path
from check_mouse import ROOT, RUNTIME, stop, write_hints

EXTRA = ['guard','rename','unitsay','emote','leader','mental','magictarget','clear','jump','worldchat','clanchat','allyadd','allyremove','allylist','legends','music','help']
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--module',type=Path,default=Path('/tmp/dm-runtime-audit/prompt-touch-stage/module'))
    ap.add_argument('--label',default='curated-controls-native')
    ap.add_argument('--port',type=int,default=12195)
    a=ap.parse_args()
    if not re.fullmatch(r'[a-z0-9-]+',a.label): ap.error('Use a simple label')
    out=ROOT/'tests';report_path=out/(a.label+'-checks.json')
    if report_path.exists():ap.error('Use a fresh label')
    paths={'fixture':out/'curated_controls_native.dm','bridge':out/'curated_controls_native.js','module':a.module/'Robust.Client.WebView.dll','runtime':RUNTIME/'server/Resources/Assemblies/OpenDreamRuntime.dll','client_zip':RUNTIME/'server/Content.Client.zip','compiler':RUNTIME/'compiler/DMCompiler.dll'}
    for name in ['Cave Crawlers.dme','Interface/remastered.html','Code/Remastered/HUD.dm','Code/Remastered/Actions.dm','Code/Remastered/SelectedActions.dm','Code/Remastered/UIIdentity.dm','Code/Remastered/ControlGroups.dm','Code/Remastered/QoL.dm','Code/Verbs.dm','Code/Items/Crowning.dm']:
        paths[name]=ROOT/'game'/name
    report=dict(scope=__doc__,hashes_before={k:sha(v)for k,v in paths.items()},checks={},actions=[],prompts=[],screenshots=[])
    checks=report['checks'];server=client=None
    slp,clp=out/(a.label+'-server.log'),out/(a.label+'-client.log')
    with tempfile.TemporaryDirectory(prefix='dm-curated-native-')as temp:
        base=Path(temp);world=base/'world';probe=base/'probe';probe.mkdir()
        shutil.copytree(ROOT/'game',world,ignore=shutil.ignore_patterns('Cave Crawlers.json','*.dmm','*.sav','units','saves','ErrorLog.txt'))
        source=(world/'Code/World.dm').read_text(encoding='latin-1');start,end=source.index('\tNew()'),source.index('\nvar/Season')
        (world/'Code/World.dm').write_text(source[:start]+'\tNew()\n\t\tlog=file("ErrorLog.txt")\n'+source[end:],encoding='latin-1')
        html=world/'Interface/remastered.html';html_source=html.read_text();marker="// The browser requests its first model only after its functions exist."
        assert marker in html_source
        html.write_text(html_source.replace(marker,paths['bridge'].read_text()+'\n'+marker,1))
        dme=re.sub(r'^#include .*\.dmm"\s*$','',(world/'Cave Crawlers.dme').read_text(encoding='latin-1'),flags=re.M)
        shutil.copy2(paths['fixture'],world/'curated_controls_native.dm');fixture=world/'curated.dme'
        fixture.write_text(dme+'\n#include "curated_controls_native.dm"\n',encoding='latin-1')
        private=base/'server';shutil.copytree(RUNTIME/'server',private)
        cd=base/'client';shutil.copytree(RUNTIME/'client/Space Station 14.app/Contents/Resources',cd,ignore=shutil.ignore_patterns('user_data','.DS_Store'))
        module=base/'module';shutil.copytree(a.module,module)
        with zipfile.ZipFile(private/'Content.Client.zip')as z:
            report['mounted_client_sha256']=hashlib.sha256(z.read(next(n for n in z.namelist()if n.endswith('/OpenDreamClient.dll')))).hexdigest()
        dotnet=RUNTIME/'dotnet/dotnet';env=dict(os.environ,DOTNET_ReadyToRun='0')
        def log():
            f=world/'ErrorLog.txt';return f.read_text(errors='replace')if f.exists()else''
        def rows(kind):return[json.loads(s)for s in re.findall(r'CURATED_NATIVE\|'+kind+r'\|([^\r\n]+)',log())]
        def state():
            try:return json.loads((probe/'state.json').read_text())
            except(FileNotFoundError,ValueError):return{}
        def until(fn,seconds=15):
            end=time.monotonic()+seconds
            while True:
                result=fn()
                if result:return result
                if time.monotonic()>end:raise TimeoutError('Curated native phase timed out')
                if client and client.poll()is not None:raise RuntimeError('Private client exited')
                time.sleep(.06)
        def prompt(title):return next((w for w in state().get('windows',[])if w.get('prompt')and w['title']==title),None)
        def action(w,mode,**extra):
            data=dict(kind=20,window=w['id'],title=w['title'],mode=mode,nonce=str(len(report['actions'])+1));data.update(extra);report['actions'].append(data)
            (probe/'action.pending').write_text(json.dumps(data));(probe/'action.pending').replace(probe/'action.json')
            def receipt():
                try:return json.loads((probe/'prompt-action-result.json').read_text())
                except(FileNotFoundError,ValueError):return{}
            until(lambda:receipt().get('nonce')==data['nonce'],5);data['receipt']=receipt();time.sleep(.2)
        def button(w,text):
            b=next(b['rect']for b in w['buttons']if b['text']==text)
            action(w,'click',x=b['x']+b['width']/2,y=b['y']+b['height']/2)
        def observation(phase):return until(lambda:next((r for r in rows('state')if r['phase']==phase),None))
        def capture():
            prefix=a.label+'-catalog';(probe/'capture-web.txt').write_text(prefix)
            manifest=probe/(prefix+'-panels.json');until(manifest.exists,5)
            for entry in json.loads(manifest.read_text()):
                image=probe/entry['file'];until(lambda:image.exists()and image.read_bytes().endswith(b'IEND\xaeB`\x82'),5)
                shutil.copy2(image,out/image.name);report['screenshots'].append(str(out/image.name))
        try:
            with(out/(a.label+'-compile.log')).open('w')as compiler:
                subprocess.run([str(dotnet),str(RUNTIME/'compiler/DMCompiler.dll'),str(fixture)],env=env,stdout=compiler,stderr=subprocess.STDOUT,timeout=60,check=True)
            hints=base/'layout.json';write_hints(world/'skin.dmf',hints)
            env.update(DM_NATIVE_UI_PROBE=str(probe),DM_SKIN_LAYOUT_HINTS=str(hints),DM_NATIVE_UI_TEST_TITLE='Remastered - Private Controls Acceptance',ROBUST_MODULE_ROBUST_CLIENT_WEBVIEW=str(module))
            with slp.open('w')as sl,clp.open('w')as cl:
                server=subprocess.Popen([str(dotnet),str(private/'Robust.Server.dll'),'--data-dir',str(base/'server-data'),'--cvar',f'opendream.json_path={fixture.with_suffix(".json")}','--cvar',f'net.port={a.port}','--cvar',f'opendream.topic_port={a.port+13500}','--cvar','net.bindto=127.0.0.1','--cvar','auth.mode=0','--cvar','status.enabled=false','--cvar','hub.advertise=false','--cvar','game.auto_pause_empty=false'],cwd=world,env=env,stdout=sl,stderr=subprocess.STDOUT)
                until(lambda:' -> Ready'in slp.read_text(errors='replace'),30)
                client=subprocess.Popen([str(dotnet),str(cd/'Robust.Client.dll'),'--mount-zip',str(private/'Content.Client.zip'),'--connect','--connect-address',f'udp://127.0.0.1:{a.port}','--username','CuratedObserver','--self-contained','--cvar','web.headless=false','--cvar','discord.enabled=false'],cwd=cd,env=env,stdout=cl,stderr=subprocess.STDOUT)
                until(lambda:any(r['phase']=='owned'for r in rows('dom')),30);capture()
                for phase,title,reply,accept in [('rename-cancel','Rename',None,'Cancel'),('rename-accept','Rename','Renamed by Controls','Ok'),('speak-cancel','Speak through a unit',None,'Cancel'),('speak-accept','Speak through a unit','Native controls speech','Ok'),('emote-accept','Unit emote','checks the controls','Ok'),('leader-no','Set Leader',None,'No'),('leader-yes','Set Leader',None,'Yes')]:
                    until(lambda:'CURATED_NATIVE|phase|'+phase in log());w=until(lambda:prompt(title));time.sleep(.35);w=prompt(title)
                    report['prompts'].append(dict(phase=phase,window=w))
                    if reply is not None:action(w,'text',text=reply);w=prompt(title)
                    button(w,accept);observation(phase)
                until(lambda:'CURATED_NATIVE|complete'in log());checks['fixture_completed']=True
                report['dom']=rows('dom');report['models']=rows('model');report['topics']=rows('topic');report['observations']=rows('state')
                for phase in ['owned','empty','withdrawn']:
                    dom=next(r for r in report['dom']if r['phase']==phase);model=next(r for r in report['models']if r['phase']==phase)
                    byid={r['id']:r for r in dom['rows']};commands={r['id']:r for r in model['commands']}
                    checks[phase+'_all17_original_curated_routes_match_server_eligibility']=dom['open']and all(i in byid and byid[i]['route']=='action'and byid[i]['value']==i and byid[i]['reason']==commands[i]['reason']and byid[i]['disabled']==bool(commands[i]['reason'])for i in EXTRA)
                    checks[phase+'_all_original_and_curated_rows_retained_without_duplicates']=dom['count']==62 and dom['unique']==62 and len(dom['classic'])==44
                checks['withdrawn_rename_disabled_with_server_reason']=next(r for r in report['dom']if r['phase']=='withdrawn')['rows'][0]is not None and next(r for r in next(d for d in report['dom']if d['phase']=='withdrawn')['rows']if r['id']=='rename')['disabled']
                before=next(r for r in report['observations']if r['phase']=='before')
                for row in report['observations']:
                    phase=row['phase'];checks[phase+'_selected_work_preserved']=row['activeSame']and row['pendingSame']and row['paused']and row['role']=='woodcutter'and row['rolePaused']and not row['destination']and row['selected']==1
                    checks[phase+'_other_real_unit_unchanged']=row['neighborName']==before['neighborName']and row['neighborRoyal']==before['neighborRoyal']and row['neighborChat']==before['neighborChat']and row['neighborEmote']==before['neighborEmote']
                snapshots={r['phase']:r for r in report['observations']}
                checks['rename_cancel_preserves_original_name']=snapshots['rename-cancel']['name']==before['name']
                checks['rename_accept_changes_only_original_selected_unit']=snapshots['rename-accept']['name']=='{ControlsOwner} Renamed by Controls'
                checks['speech_cancel_preserves_log']=snapshots['speak-cancel']['chat']==before['chat']
                checks['speech_accept_uses_original_log_effect']='Native controls speech'in snapshots['speak-accept']['chat']
                checks['emote_accept_uses_original_log_effect']='checks the controls'in snapshots['emote-accept']['emote']
                checks['leader_no_preserves_royalty_and_stats']=not snapshots['leader-no']['royal']and snapshots['leader-no']['strength']==before['strength']
                checks['leader_yes_applies_original_royalty_stats']=bool(snapshots['leader-yes']['royal'])and snapshots['leader-yes']['strength']==before['strength']+10
                for phase,expected in [('rename-cancel','rename'),('rename-accept','rename'),('speak-cancel','unitsay'),('speak-accept','unitsay'),('emote-accept','emote'),('leader-no','leader'),('leader-yes','leader')]:
                    transport=[r for r in report['topics']if r['phase']==phase and r['action']=='action']
                    checks[phase+'_single_real_topic_from_dom']=len(transport)==1 and transport[0]['value']==expected
                checks['no_incidental_map_input']=all(r['incidentalInput']==0 for r in report['observations'])
        except Exception as error:
            report['error']=repr(error);report['last_state']=state()
            if client and client.poll() is None:
                try:capture()
                except Exception as capture_error:report['capture_error']=repr(capture_error)
        finally:
            stop(client);stop(server);(out/(a.label+'-world.log')).write_text(log())
            for image in probe.glob('prompt-*.png'):shutil.copy2(image,out/(a.label+'-'+image.name))
            for name in ['state.json','prompt-actions.jsonl']:
                if(probe/name).exists():shutil.copy2(probe/name,out/(a.label+'-'+name))
        logs={k:p.read_text(errors='replace')for k,p in [('server',slp),('client',clp),('world',out/(a.label+'-world.log'))]if p.exists()}
        report['errors']={k:re.findall(r'(?im)^.*(?:\[(?:ERRO|FATL)\]|\bruntime error\b|\bexception\b).*$',v)for k,v in logs.items()}
        report['native_events']=re.findall(r'native.ui.probe: (?:engine key|event)[^\r\n]*',logs.get('client',''))
        checks['no_os_input_events']=not report['native_events'];checks['no_save_created']=not list(world.rglob('*.sav'))
        checks['private_processes_stopped']=all(s is None or s.poll()is not None for s in(server,client))
        checks['no_fixture_failure']='CURATED_NATIVE|failure|'not in log()
    report['hashes_after']={k:sha(v)for k,v in paths.items()};checks['source_runtime_module_fixture_stable']=report['hashes_before']==report['hashes_after']
    report['passed']=bool(checks.get('fixture_completed'))and all(checks.values())and not report.get('error')and not any(report['errors'].values())
    report_path.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(report=str(report_path),passed=report['passed'],checks=len(checks),failures=[k for k,v in checks.items()if not v],error=report.get('error'),errors=report['errors']),indent=2))
    return 0 if report['passed']else 1
if __name__=='__main__':raise SystemExit(main())
