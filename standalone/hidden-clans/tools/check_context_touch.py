#!/usr/bin/env python3
"""Private native context-row UIClick check, without OS mouse/focus injection.

Real original Human/queue/SetTarget; mapless fixture provides stacked targets.
The private probe dispatches viewport right-click and normal UI focus/down/up
callbacks. Hover is invoked explicitly only for its separate regression/baseline
fallback. No press-and-hold, physical touch, or OS delivery claim is made.
"""
import argparse, hashlib, json, os, re, shutil, subprocess, tempfile, time, zipfile
from pathlib import Path
from check_mouse import ROOT, RUNTIME, stop, write_hints
from check_app import error_lines

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--label',required=True);p.add_argument('--port',type=int,default=12190)
 p.add_argument('--client',type=Path)
 p.add_argument('--webview-dir',type=Path,default=Path('/tmp/dm-runtime-audit/context-touch-stage/engine/webview-webkit'))
 a=p.parse_args();out=ROOT/'tests'
 if not re.fullmatch(r'[A-Za-z0-9_-]+',a.label) or not 1024<=a.port<=52035:p.error('invalid label/port')
 if (out/f'{a.label}-checks.json').exists():p.error('use a fresh label')
 report={'scope':__doc__,'checks':{},'actions':[]};checks=report['checks'];server=client=None
 sources={'fixture':out/'context_touch_probe.dm','webview':a.webview_dir/'Robust.Client.WebView.dll',
  'runtime':RUNTIME/'server/Resources/Assemblies/OpenDreamRuntime.dll','shared':RUNTIME/'server/Resources/Assemblies/OpenDreamShared.dll','client_zip':RUNTIME/'server/Content.Client.zip'}
 if a.client:sources['candidate_client']=a.client
 report['hashes_before']={k:sha(v) for k,v in sources.items()}
 with tempfile.TemporaryDirectory(prefix='dm-context-touch-') as temp:
  base=Path(temp);world=base/'world';probe=base/'probe';probe.mkdir()
  shutil.copytree(ROOT/'game',world,ignore=shutil.ignore_patterns('Cave Crawlers.json','*.dmm','*.sav','units','saves','ErrorLog.txt'))
  s=(world/'Code/World.dm').read_text(encoding='latin-1');start,end=s.index('\tNew()'),s.index('\nvar/Season')
  (world/'Code/World.dm').write_text(s[:start]+'\tNew()\n\t\tlog = file("ErrorLog.txt")\n'+s[end:],encoding='latin-1')
  dme=re.sub(r'^#include .*\.dmm"\s*$','',(world/'Cave Crawlers.dme').read_text(encoding='latin-1'),flags=re.M)
  shutil.copy2(sources['fixture'],world/'context_touch_probe.dm');fixture=world/'touch.dme'
  fixture.write_text(dme+'\n#include "context_touch_probe.dm"\n',encoding='latin-1')
  private=base/'server';shutil.copytree(RUNTIME/'server',private)
  package=private/'Content.Client.zip'
  if a.client:
   replacement=base/'client.zip'
   with zipfile.ZipFile(package) as old,zipfile.ZipFile(replacement,'w',compression=zipfile.ZIP_DEFLATED) as new:
    for item in old.infolist():new.writestr(item,a.client.read_bytes() if Path(item.filename).name=='OpenDreamClient.dll' else old.read(item))
   replacement.replace(package)
  with zipfile.ZipFile(package) as z:report['mounted_client_sha256']=hashlib.sha256(z.read(next(n for n in z.namelist() if n.endswith('/OpenDreamClient.dll')))).hexdigest()
  module=base/'webview';shutil.copytree(a.webview_dir,module)
  cd=base/'client';shutil.copytree(RUNTIME/'client/Space Station 14.app/Contents/Resources',cd,ignore=shutil.ignore_patterns('user_data','.DS_Store'))
  dotnet=RUNTIME/'dotnet/dotnet';env=dict(os.environ,DOTNET_ReadyToRun='0')
  slp,clp=out/f'{a.label}-server.log',out/f'{a.label}-client.log'
  def log():
   f=world/'ErrorLog.txt';return f.read_text(errors='replace') if f.exists() else ''
  def state():
   try:return json.loads((probe/'state.json').read_text())
   except (ValueError,FileNotFoundError):return {}
  def observed():
   rows=re.findall(r'TOUCHMENU\|state\|([^\r\n]+)',log());return json.loads(rows[-1]) if rows else {}
  def until(fn,seconds=10):
   end=time.monotonic()+seconds
   while not fn():
    if time.monotonic()>end:raise TimeoutError('Context fixture timed out')
    if client and client.poll() is not None:raise RuntimeError('Private client exited')
    time.sleep(.08)
  def window():return next((w for w in state()['windows'] if w.get('viewports')), None) or max(state()['windows'], key=lambda w: w['width'] * w['height'])
  def action(**values):
   data=dict(window=window()['id'],nonce=str(len(report['actions'])+1),kind=11,x=0,y=0,expected=None);data.update(values)
   report['actions'].append(data.copy());(probe/'action.pending').write_text(json.dumps(data));(probe/'action.pending').replace(probe/'action.json')
   name='map-click-result.json' if data['kind']==9 else 'menu-action-result.json'
   def done():
    try:return json.loads((probe/name).read_text())['nonce']==data['nonce']
    except (ValueError,FileNotFoundError):return False
   until(done,5);report['actions'][-1]['receipt']=json.loads((probe/name).read_text());time.sleep(.35)
  def rows():return window().get('contextItems',[])
  def popups():return window().get('popups',[])
  def verbs():return next((m for m in popups() if m['type']=='VerbMenuPopup'),None)
  def row(name):return next(r for r in rows() if r['text']==name)
  def click_row(name,release=None,**extra):
   r=row(name)['rect'];values=dict(kind=11,x=r['x']+r['width']/2,y=r['y']+r['height']/2,expected=name)
   if release:
    t=row(release)['rect'];values.update(x2=t['x']+t['width']/2,y2=t['y']+t['height']/2)
   values.update(extra);action(**values)
  def opening_unchanged():return observed()==report['before']
  def capture(name):
   f=f'{a.label}-{name}.png';(probe/'capture.txt').write_text(f)
   until(lambda:(probe/f).exists() and (probe/f).read_bytes().endswith(b'IEND\xaeB`\x82'),5)
   shutil.copy2(probe/f,out/f);report.setdefault('screenshots',{})[name]=str(out/f)
  try:
   with (out/f'{a.label}-compile.log').open('w') as compiler:
    subprocess.run([str(dotnet),str(RUNTIME/'compiler/DMCompiler.dll'),str(fixture)],stdout=compiler,stderr=subprocess.STDOUT,env=env,timeout=60,check=True)
   hints=base/'layout.json';write_hints(world/'skin.dmf',hints)
   env.update(RM_KEEP_2D='1', DM_SKIN_LAYOUT_HINTS=str(hints),DM_NATIVE_UI_PROBE=str(probe),DM_NATIVE_UI_TEST_TITLE='Remastered - Private Context Touch Check',ROBUST_MODULE_ROBUST_CLIENT_WEBVIEW=str(module))
   with slp.open('w') as sl,clp.open('w') as cl:
    server=subprocess.Popen([str(dotnet),str(private/'Robust.Server.dll'),'--data-dir',str(base/'server-data'),'--cvar',f'opendream.json_path={fixture.with_suffix(".json")}','--cvar','net.bindto=127.0.0.1','--cvar',f'net.port={a.port}','--cvar',f'opendream.topic_port={a.port+13500}','--cvar','auth.mode=0','--cvar','status.enabled=false','--cvar','hub.advertise=false','--cvar','game.auto_pause_empty=false'],cwd=world,env=env,stdout=sl,stderr=subprocess.STDOUT)
    until(lambda:' -> Ready' in slp.read_text(errors='replace'),30)
    client=subprocess.Popen([str(dotnet),str(cd/'Robust.Client.dll'),'--mount-zip',str(package),'--connect','--connect-address',f'udp://127.0.0.1:{a.port}','--username','ContextTouchCheck','--self-contained','--cvar','web.headless=false','--cvar','discord.enabled=false'],cwd=cd,env=env,stdout=cl,stderr=subprocess.STDOUT)
    until(lambda:'TOUCHMENU|ready' in log() and state().get('windows'),30);time.sleep(1)
    report['before']=observed()
    action(kind=9,x=.5,y=.5,right=True)
    until(lambda:any(r['text']=='Context Human A' for r in rows()))
    checks['stacked_original_targets_are_separate_rows']=all(any(r['text']==n for r in rows()) for n in ('Context Human A','Context Human B','Context Stone'))
    checks['opening_context_preserves_work_and_target']=opening_unchanged()
    checks['opening_context_needs_no_hover']=verbs() is None
    report['rows']=rows()
    click_row('Context Human A')
    checks['row_release_opens_submenu_without_hover']=verbs() is not None
    if verbs() is None:
     report['baseline_hover_fallback']=True;action(kind=13,text='Context Human A')
    until(lambda:verbs() is not None)
    checks['original_verb_filtering_retained']='Context Allowed' in verbs()['buttons'] and not any(n in verbs()['buttons'] for n in ('Context Hidden','Context No Popup')) and any(n.replace(' ','')=='SetTarget' for n in verbs()['buttons'])
    checks['opening_row_executes_nothing_and_preserves_work']=opening_unchanged()
    target_a=verbs()['target'];report['target_a']=target_a
    click_row('Context Human B')
    checks['tap_switches_stacked_target']=verbs() is not None and verbs()['target']!=target_a
    report['rows_after_nohover_taps']=rows()
    checks['nohover_taps_do_not_accumulate_row_highlights']=all(row(n).get('hasHoverOverride') is False for n in ('Context Human A','Context Human B'))
    if verbs() is None or verbs()['target']==target_a:action(kind=13,text='Context Human B')
    target_b=verbs()['target'];report['target_b']=target_b
    click_row('Context Stone')
    checks['no_verbs_row_keeps_parent_available']=any(m['type']=='ContextMenuPopup' for m in popups()) and (verbs() is None or len(verbs()['buttons'])==0) and len(rows())>=3
    if verbs() is not None and verbs()['buttons']:action(kind=13,text='Context Stone')
    click_row('Context Human A','Context Human B')
    checks['release_over_different_row_does_not_activate_it']=verbs() is None or verbs()['target'] not in (target_a,target_b)
    checks['canceled_row_press_executes_nothing']=opening_unchanged()
    click_row('Context Human A',cancelFocus=True)
    checks['focus_loss_before_release_cancels_activation']=verbs() is None or verbs()['target'] not in (target_a,target_b)
    action(kind=13,text='Context Stone')
    click_row('Context Human A',closeContext=True)
    checks['closed_popup_does_not_activate_pressed_row']=not any(m['type']=='ContextMenuPopup' for m in popups()) and verbs() is None
    action(kind=9,x=.5,y=.5,right=True)
    until(lambda:any(r['text']=='Context Human A' for r in rows()))
    click_row('Context Human A',releaseOnly=True)
    checks['unmatched_release_after_reopen_does_not_activate_row']=verbs() is None
    action(kind=13,text='Context Human A')
    checks['original_hover_still_opens_matching_submenu']=verbs() is not None and verbs()['target']==target_a
    action(kind=14)
    click_row('Context Human B')
    if verbs() is None or verbs()['target']!=target_b:action(kind=13,text='Context Human B')
    report['edge_popups']=popups();w=window()
    checks['edge_menus_stay_within_window']=all(m['rect']['x']>=0 and m['rect']['y']>=0 and m['rect']['x']+m['rect']['width']<=w['width']+1 and m['rect']['y']+m['rect']['height']<=w['height']+1 for m in popups())
    parent=next(m['rect'] for m in popups() if m['type']=='ContextMenuPopup');child=verbs()['rect']
    checks['edge_submenu_does_not_cover_parent_rows']=child['x']+child['width']<=parent['x']+1 or child['x']>=parent['x']+parent['width']-1
    capture('edge')
    checks['all_opening_and_cancel_steps_preserve_work']=opening_unchanged()
    b=next(b for b in window()['buttons'] if b['text'].replace(' ','')=='SetTarget')['rect']
    action(kind=12,x=b['x']+b['width']/2,y=b['y']+b['height']/2,expected='SetTarget')
    until(lambda:observed().get('targetB'))
    checks['separate_verb_click_executes_original_settarget']=observed()['targetB'] and not observed()['targetA']
    checks['verb_keeps_selection_and_exact_queue']=observed()['selected']==1 and observed()['activeSame'] and observed()['pendingSame'] and observed()['paused']
    report['after']=observed()
  except Exception as error:report['error']=repr(error);report['last_state']=state();report['last_observed']=observed()
  finally:
   stop(client);stop(server)
   (out/f'{a.label}-world.log').write_text(log())
   for n in ('state.json','map-clicks.jsonl','menu-actions.jsonl'):
    if (probe/n).exists():shutil.copy2(probe/n,out/f'{a.label}-{n}')
  logs={n:f.read_text(errors='replace') for n,f in [('server',slp),('client',clp),('world',out/f'{a.label}-world.log')] if f.exists()}
  report['errors']={k:error_lines(v) for k,v in logs.items()}
  report['native_input_events']=re.findall(r'native.ui.probe: (?:engine key|event)[^\r\n]*',logs.get('client',''))
  checks['no_os_input_events']=not report['native_input_events']
  checks['private_processes_stopped']=all(s is None or s.poll() is not None for s in (server,client))
 report['hashes_after']={k:sha(v) for k,v in sources.items()}
 expected=['stacked_original_targets_are_separate_rows','opening_context_preserves_work_and_target','opening_context_needs_no_hover','row_release_opens_submenu_without_hover','original_verb_filtering_retained','opening_row_executes_nothing_and_preserves_work','tap_switches_stacked_target','nohover_taps_do_not_accumulate_row_highlights','no_verbs_row_keeps_parent_available','release_over_different_row_does_not_activate_it','canceled_row_press_executes_nothing','focus_loss_before_release_cancels_activation','closed_popup_does_not_activate_pressed_row','unmatched_release_after_reopen_does_not_activate_row','original_hover_still_opens_matching_submenu','edge_menus_stay_within_window','edge_submenu_does_not_cover_parent_rows','all_opening_and_cancel_steps_preserve_work','separate_verb_click_executes_original_settarget','verb_keeps_selection_and_exact_queue','no_os_input_events','private_processes_stopped']
 report['expected_checks']=expected;report['missing_checks']=[key for key in expected if key not in checks]
 report['passed']=not report['missing_checks'] and all(checks.values()) and not report.get('error') and not any(report['errors'].values())
 (out/f'{a.label}-checks.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps({k:report[k] for k in ('passed','checks','errors')},indent=2))
 if report.get('error'):print(report['error'])
 return 0 if report['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
