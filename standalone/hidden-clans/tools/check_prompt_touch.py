#!/usr/bin/env python3
"""Audit real Rename, potion, Guard and Crown prompts in a private native client.

Only internal UI callbacks target the isolated client. No OS keyboard/mouse
events, normal profile, saves, installed runtime edits, or gameplay overrides.
Target sizing uses the actual focused TextEntered callback; legacy mode uses
a setter probe. Neither claims physical keyboard or mobile touch input.
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
import zipfile
from check_mouse import ROOT, RUNTIME, stop, write_hints


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--module',type=Path,required=True)
    p.add_argument('--client',type=Path)
    p.add_argument('--robust-client',type=Path)
    p.add_argument('--selection-contract',action='store_true')
    p.add_argument('--ui-scale',type=float,default=1.0)
    p.add_argument('--owner-logical-width',type=int,choices=[320])
    p.add_argument('--long-content',action='store_true')
    p.add_argument('--placement-checks',action='store_true')
    p.add_argument('--screen-bounds',type=Path)
    p.add_argument('--target-sizing',action='store_true',help='Measure 44px native targets and exercise focused text entry callbacks')
    p.add_argument('--label',default='prompt-touch-before')
    p.add_argument('--port',type=int,default=12197)
    a=p.parse_args()
    if a.placement_checks and not a.screen_bounds:p.error('Placement requires measured screen bounds')
    if a.placement_checks:a.long_content=True
    if a.long_content:a.target_sizing=True
    if a.target_sizing:a.selection_contract=True
    if a.ui_scale not in (1.0,1.5,2.0):p.error('bounded scales: 1, 1.5, or 2')
    if not re.fullmatch(r'[a-z0-9-]+',a.label):p.error('Use a simple label')
    out=ROOT/'tests';dest=out/(a.label+'-checks.json')
    if dest.exists():p.error('Use a fresh label')
    report=dict(scope=__doc__,checks={},actions=[],prompts=[],observations=[]);checks=report['checks']
    tracked={'fixture':out/('prompt_targets_probe.dm' if a.target_sizing else 'prompt_selection_probe.dm' if a.selection_contract else 'prompt_touch_probe.dm'),'module':a.module/'Robust.Client.WebView.dll'}
    if a.client:tracked['candidate_client']=a.client
    if a.robust_client:tracked['candidate_robust_client']=a.robust_client
    if a.long_content:tracked['Code/Restart.dm']=ROOT/'game/Code/Restart.dm'
    for name in ['Code/Verbs.dm','Code/Creatures/Monster AI.dm','Code/Items/Crowning.dm','Code/Remastered/InventoryActions.dm','Code/Remastered/SelectedActions.dm','Code/Remastered/Actions.dm']:
        tracked[name]=ROOT/'game'/name
    report['hashes_before']={k:sha(v)for k,v in tracked.items()}
    if a.screen_bounds:report['screens']=json.loads(a.screen_bounds.read_text())
    server=client=None
    with tempfile.TemporaryDirectory(prefix='dm-prompt-touch-')as temp:
        base=Path(temp);world=base/'world';probe=base/'probe';probe.mkdir()
        shutil.copytree(ROOT/'game',world,ignore=shutil.ignore_patterns('Cave Crawlers.json','*.dmm','*.sav','units','saves','ErrorLog.txt'))
        s=(world/'Code/World.dm').read_text(encoding='latin-1');start,end=s.index('\tNew()'),s.index('\nvar/Season')
        (world/'Code/World.dm').write_text(s[:start]+'\tNew()\n\t\tlog=file("ErrorLog.txt")\n'+s[end:],encoding='latin-1')
        dme=re.sub(r'^#include .*\.dmm"\s*$','',(world/'Cave Crawlers.dme').read_text(encoding='latin-1'),flags=re.M)
        shutil.copy2(tracked['fixture'],world/'prompt_touch_probe.dm');fixture=world/'prompt.dme'
        extra=''
        if a.long_content:
            restart=(world/'Code/Restart.dm').read_text(encoding='latin-1')
            intro=re.search(r'if\("Orc"\) alert\(src,("[^\n]+")\)',restart).group(1)
            report['long_message_original_source']='Code/Restart.dm original Orc introductory alert'
            long_dm='''Player/proc/PromptLongContent()
	sleep(3)
	world.log << "PROMPT_TOUCH|phase|long-original-alert"
	WorldName="\\[b\\]Literal & <world>\\[/b\\]"
	var/message=INTRO
	world.log << "PROMPT_TOUCH|long-message|[json_encode(message)]"
	var/response=alert(src,message,"Original Orc introduction","Yes","No","Cancel")
	world.log << "PROMPT_TOUCH|long-alert-response|[response]"
	PromptAuditState("long-original-alert-done")
	sleep(3)
	world.log << "PROMPT_TOUCH|phase|long-choice"
	var/list/choices=list("First","Diamond Encrusted Silver ChestPlate","Emerald Encrusted Silver ChestPlate","Melt All Weapons On Unit","Melt All Armours On Unit","Tear all Meat from Corpses","One","Two","Concentration Enhancing Hormonal Gland","Cancel")
	var/choice=input(src,"Choose.","Long original choices",choices[1]) as null|anything in choices
	world.log << "PROMPT_TOUCH|long-choice-response|[json_encode(choice)]"
	PromptAuditState("long-choice-done")
	sleep(3)
	world.log << "PROMPT_TOUCH|phase|wide-choice"
	var/wide="Concentration Enhancing Hormonal Gland / Diamond Encrusted Silver ChestPlate / Emerald Encrusted Silver ChestPlate"
	var/list/wide_choices=list("First",wide,"Cancel")
	var/wide_response=input(src,"Choose.","Very long choice",wide_choices[1]) as null|anything in wide_choices
	world.log << "PROMPT_TOUCH|wide-choice-response|[json_encode(wide_response)]"
	PromptAuditState("wide-choice-done")
'''.replace('INTRO',intro)
            (world/'prompt_long_content.dm').write_text(long_dm,encoding='latin-1')
            report['long_fixture_sha256']=sha(world/'prompt_long_content.dm')
            (out/(a.label+'-long-fixture.dm')).write_text(long_dm,encoding='latin-1')
            extra='#include "prompt_long_content.dm"\n'
        fixture.write_text(('#define PROMPT_TARGET_LONG\n' if a.long_content else '')+dme+'\n#include "prompt_touch_probe.dm"\n'+extra,encoding='latin-1')
        private=base/'server';shutil.copytree(RUNTIME/'server',private)
        if a.client:
            package=private/'Content.Client.zip';pending=private/'candidate.zip'
            with zipfile.ZipFile(package)as old,zipfile.ZipFile(pending,'w',compression=zipfile.ZIP_DEFLATED)as new:
                for info in old.infolist():new.writestr(info,a.client.read_bytes()if Path(info.filename).name=='OpenDreamClient.dll'else old.read(info))
            pending.replace(package)
        report['runtime_sha256']=sha(private/'Resources/Assemblies/OpenDreamRuntime.dll')
        report['client_zip_sha256']=sha(private/'Content.Client.zip')
        with zipfile.ZipFile(private/'Content.Client.zip')as package:
            report['mounted_client_sha256']=hashlib.sha256(package.read(next(n for n in package.namelist()if n.endswith('/OpenDreamClient.dll')))).hexdigest()
        cd=base/'client';shutil.copytree(RUNTIME/'client/Space Station 14.app/Contents/Resources',cd,ignore=shutil.ignore_patterns('user_data','.DS_Store'))
        if a.robust_client:shutil.copy2(a.robust_client,cd/'Robust.Client.dll')
        report['robust_client_sha256']=sha(cd/'Robust.Client.dll')
        module=base/'module';shutil.copytree(a.module,module)
        dotnet=RUNTIME/'dotnet/dotnet';env=dict(os.environ,DOTNET_ReadyToRun='0')
        slp,clp=out/(a.label+'-server.log'),out/(a.label+'-client.log')
        def log():
            f=world/'ErrorLog.txt';return f.read_text(errors='replace')if f.exists()else''
        def state():
            try:return json.loads((probe/'state.json').read_text())
            except(FileNotFoundError,ValueError):return{}
        def until(fn,seconds=15):
            end=time.monotonic()+seconds
            while True:
                result=fn()
                if result:return result
                if time.monotonic()>end:raise TimeoutError('Prompt fixture timed out')
                if client and client.poll()is not None:raise RuntimeError('Private client exited')
                time.sleep(.08)
        def prompt(title):return next((w for w in state().get('windows',[])if w.get('prompt') and w['title']==title),None)
        def ready(phase,title):
            until(lambda:'PROMPT_TOUCH|phase|'+phase in log());until(lambda:prompt(title),30 if phase=='rename-cancel' else 15);time.sleep(.4)
            w=prompt(title);report['prompts'].append(dict(phase=phase,window=w));return w
        def action(w,mode,**values):
            data=dict(kind=20,window=w['id'],title=w['title'],mode=mode,nonce=str(len(report['actions'])+1));data.update(values)
            report['actions'].append(data)
            (probe/'action.pending').write_text(json.dumps(data));(probe/'action.pending').replace(probe/'action.json')
            def received():
                try:return json.loads((probe/'prompt-action-result.json').read_text()).get('nonce')==data['nonce']
                except(FileNotFoundError,ValueError):return False
            until(received,5);report['actions'][-1]['receipt']=json.loads((probe/'prompt-action-result.json').read_text());time.sleep(.3)
        def button(w,text):
            b=next(b['rect']for b in w['buttons']if b['text']==text)
            action(w,'click',x=b['x']+b['width']/2,y=b['y']+b['height']/2)
        def item(w,text):
            original_window=w
            scrolled=False
            b=next(b['rect']for b in w['lists'][0]['items']if b['text']==text)
            box=w['lists'][0]['rect']
            if b is None or b['y']<box['y'] or b['y']+b['height']>box['y']+box['height']:
                scrolled=True
                action(w,'scroll-bottom')
                w=prompt(w['title'])
                b=next(b['rect']for b in w['lists'][0]['items']if b['text']==text)
            box=w['lists'][0]['rect']
            if a.target_sizing:
                report.setdefault('row_interactions',[]).append(dict(title=w['title'],window=w['id'],text=text,scrolled=scrolled,rect=b,list_rect=box))
                if b is None or b['y']<box['y']-.1 or b['y']+b['height']>box['y']+box['height']+.1:raise RuntimeError('Target row not fully visible after scrolling')
            action(w,'click',x=b['x']+b['width']/2,y=b['y']+b['height']/2)
        def observation(phase):
            def find():
                rows=[json.loads(s)for s in re.findall(r'PROMPT_TOUCH\|state\|([^\r\n]+)',log())]
                return next((r for r in rows if r['phase']==phase),None)
            row=until(find,45 if phase=='before' else 15);report['observations'].append(row);return row
        def preserved(row):return row['activeSame'] and row['pendingSame'] and row['paused'] and row['selected']==1
        try:
            with(out/(a.label+'-compile.log')).open('w')as compiler:
                subprocess.run([str(dotnet),str(RUNTIME/'compiler/DMCompiler.dll'),str(fixture)],env=env,stdout=compiler,stderr=subprocess.STDOUT,timeout=60,check=True)
            hints=base/'layout.json';write_hints(world/'skin.dmf',hints)
            env.update(DM_NATIVE_UI_PROBE=str(probe),DM_SKIN_LAYOUT_HINTS=str(hints),DM_NATIVE_UI_TEST_TITLE='Remastered - Private Prompt Audit',ROBUST_MODULE_ROBUST_CLIENT_WEBVIEW=str(module))
            with slp.open('w')as sl,clp.open('w')as cl:
                server=subprocess.Popen([str(dotnet),str(private/'Robust.Server.dll'),'--data-dir',str(base/'server-data'),'--cvar',f'opendream.json_path={fixture.with_suffix(".json")}','--cvar',f'net.port={a.port}','--cvar',f'opendream.topic_port={a.port+13500}','--cvar','net.bindto=127.0.0.1','--cvar','auth.mode=0','--cvar','status.enabled=false','--cvar','hub.advertise=false','--cvar','game.auto_pause_empty=false'],cwd=world,env=env,stdout=sl,stderr=subprocess.STDOUT)
                until(lambda:' -> Ready' in slp.read_text(errors='replace'),30)
                client=subprocess.Popen([str(dotnet),str(cd/'Robust.Client.dll'),'--mount-zip',str(private/'Content.Client.zip'),'--connect','--connect-address',f'udp://127.0.0.1:{a.port}','--username','PromptObserver','--self-contained','--cvar','web.headless=false','--cvar','discord.enabled=false','--cvar',f'display.uiScale={a.ui_scale}'],cwd=cd,env=env,stdout=cl,stderr=subprocess.STDOUT)
                before=observation('before')
                w=ready('rename-cancel','Rename')
                def normal_geometry():return [dict(id=v['id'],width=v['width'],height=v['height'],renderTarget=v.get('renderTarget'),viewports=v.get('viewports')) for v in state().get('windows',[]) if not v.get('prompt')]
                report['non_prompt_before']=normal_geometry()
                original_owner=w.get('ownerBounds')
                if a.owner_logical_width:
                    action(w,'owner-resize',width=round(a.owner_logical_width*w['scale']),height=original_owner['pixelHeight'])
                    until(lambda:prompt('Rename')['ownerBounds']['pixelWidth']==round(a.owner_logical_width*w['scale']))
                    report['narrow_owner']=prompt('Rename')['ownerBounds']
                checks['rename_default_selected_and_focused']=any(e['focused'] and e['selection']==0 and e['cursor']==len(e['text']) for e in w['lineEdits'])
                if a.target_sizing:
                    checks['initial_layout_callback_dimensions_consistent']=all(c['setWidth']=='NaN' or abs(float(c['setWidth'])-w['width']/w['scale'])<.01 for c in w['layout'] if c['type']=='TextPrompt')
                    resized_width=w['width']+round(64*w['scale']);resized_height=w['height']+round(36*w['scale'])
                    action(w,'resize',width=resized_width,height=resized_height)
                    until(lambda:prompt('Rename')['width']==resized_width and prompt('Rename')['renderTarget']['width']==resized_width)
                    time.sleep(.4);w=prompt('Rename');report['prompts'].append(dict(phase='rename-visible-resize',window=w))
                    checks['visible_resize_updates_geometry_and_original_callback']=w['height']==resized_height and all(c['setWidth']!='NaN' and abs(float(c['setWidth'])-resized_width/w['scale'])<.01 for c in w['layout'] if c['type']=='TextPrompt')
                if a.placement_checks:
                    moved_size=(w['width'],w['height'])
                    action(w,'position',x=120,y=100)
                    until(lambda:prompt('Rename')['nativeBounds']['x']==120 and prompt('Rename')['nativeBounds']['y']==100)
                    action(prompt('Rename'),'repeat-show');w=prompt('Rename')
                    checks['repeated_show_preserves_existing_position_and_size']=w['nativeBounds']['x']==120 and w['nativeBounds']['y']==100 and (w['width'],w['height'])==moved_size
                    action(w,'manual-create');until(lambda:prompt('Manual placement audit'));time.sleep(.4)
                    manual=prompt('Manual placement audit');report['manual_startup']=manual
                    checks['manual_startup_position_unchanged']=manual['nativeBounds']['x']==150 and manual['nativeBounds']['y']==170
                    button(manual,'Done');until(lambda:not prompt('Manual placement audit'))
                    action(prompt('Rename'),'stale-placement');time.sleep(.4)
                    checks['stale_destroyed_child_placement_ignored']=prompt('Rename')['nativeBounds']['x']==120 and prompt('Rename')['nativeBounds']['y']==100
                    usable=report['screens'][0]['visible'];owner=prompt('Rename')['ownerBounds']
                    edge_x=round(usable['x']+usable['width']-owner['width']/2);edge_y=round(usable['y']+usable['height']-owner['height']/2)
                    action(prompt('Rename'),'owner-position',x=edge_x,y=edge_y)
                    until(lambda:prompt('Rename')['ownerBounds']['x']==edge_x and prompt('Rename')['ownerBounds']['y']==edge_y)
                    report['edge_owner']=prompt('Rename')['ownerBounds']
                    w=prompt('Rename')
                action(w,'close')
                report['nullable_close_retained']=prompt('Rename')is not None
                if prompt('Rename'):button(prompt('Rename'),'Cancel')
                row=observation('rename-cancel-done');checks['rename_cancel_preserves_name_and_work']=row['name']==before['name'] and preserved(row)
                w=ready('rename-accept','Rename');action(w,'type' if a.target_sizing else 'text',text='Renamed Unit')
                if a.target_sizing:checks['native_text_input_replaces_selected_default']=prompt('Rename')['lineEdits'][0]['text']=='Renamed Unit'
                button(prompt('Rename'),'Ok')
                row=observation('rename-accept-done');checks['rename_confirm_reaches_real_handler']=row['name']=='{PromptOwner} Renamed Unit' and preserved(row)
                phases=[('potion-default','Drop'),('potion-inspect','Inspect'),('potion-cancel','Cancel'),('guard-default','Guard On'),('guard-off','Guard Off'),('guard-cancel','Cancel')]if a.selection_contract else [('potion-cancel','Drop'),('guard-cancel','Guard On')]
                for phase,first in phases:
                    w=ready(phase,'Choose')
                    default=phase.endswith('default')or not a.selection_contract
                    if default:checks[phase+'_first_choice_initially_selected']=w['lists'][0]['items'][0]['text']==first and w['lists'][0]['items'][0]['selected']
                    item(w,first);w=prompt('Choose');checks[phase+'_tapping_selected_row_keeps_selection']=any(i['selected']for i in w['lists'][0]['items'])
                    checks[phase+'_selection_does_not_auto_submit']=phase+'-done'not in log()
                    if a.selection_contract:
                        selected=[i['text']for i in w['lists'][0]['items']if i['selected']]
                        checks[phase+'_exact_single_choice_selected']=selected==[first]
                    if phase=='guard-off'and a.selection_contract:action(w,'submit')
                    else:button(w,'Ok')
                    remaining=prompt('Choose')
                    if remaining and remaining['id']!=w['id']:remaining=None
                    report.setdefault('after_default_row_tap',[]).append(dict(phase=phase,window=remaining,handler_completed=phase+'-done'in log()))
                    # If a broken selection stalls OK, advance with explicit
                    # Cancel. The contract branch intentionally requests Drop
                    # and Guard On above and checks their actual effects below.
                    if remaining:
                        item(remaining,'Cancel');button(prompt('Choose'),'Ok')
                    row=observation(phase+'-done')
                    if a.selection_contract and phase=='potion-default':
                        checks[phase+'_confirmed_drop_reaches_real_handler']=preserved(row)and not row['itemCarried']and row['itemFull']
                    elif a.selection_contract and phase=='guard-default':
                        checks[phase+'_confirmed_guard_reaches_real_handler']=preserved(row)and row['home']
                    else:checks[phase+'_cancel_or_inspect_preserves_work_and_item']=preserved(row)and row['itemCarried']and row['itemFull']and not row['home']
                w=ready('crown-no','Set Leader');button(w,'No')
                row=observation('crown-no-done');checks['crown_no_preserves_royalty_and_work']=not row['royal'] and preserved(row)
                if a.selection_contract:
                    w=ready('nullable-list','Nullable choice');button(w,'Cancel')
                    row=observation('nullable-list-done');checks['nullable_list_cancel_returns_null']='PROMPT_TOUCH|nullable-result|1'in log()and preserved(row)
                    w=ready('number-cancel','Number choice')
                    checks['number_default_selected_and_focused']=any(e['focused']and e['text']=='42'and e['selection']==0 and e['cursor']==2 for e in w['lineEdits'])
                    button(w,'Cancel');row=observation('number-cancel-done');checks['number_cancel_returns_null']='PROMPT_TOUCH|number-result|1'in log()and preserved(row)
                if a.target_sizing:
                    w=ready('number-accept','Number accept');action(w,'type',text='-12.5')
                    checks['native_number_input_replaces_selected_default']=prompt('Number accept')['lineEdits'][0]['text']=='-12.5'
                    button(prompt('Number accept'),'Ok');row=observation('number-accept-done')
                    checks['typed_decimal_reaches_original_number_prompt']='PROMPT_TOUCH|accepted-number|-12.5' in log() and preserved(row)
                    w=ready('crown-yes','Set Leader');button(w,'Yes');row=observation('crown-yes-done')
                    checks['crown_yes_preserves_work_and_applies_original_bonus']=bool(row['royal']) and row['strength']==before['strength']+10 and preserved(row)
                    checks['fixture_ordinary_grants_explicit']='PROMPT_TOUCH|fixture-grants|rename=1;guard=1;leader=1' in log()
                if a.long_content:
                    w=ready('long-original-alert','Original Orc introduction')
                    expected=json.loads(re.findall(r'PROMPT_TOUCH\|long-message\|([^\r\n]+)',log())[-1])
                    checks['long_original_message_preserved_as_literal']=len(w['messages'])==1 and w['messages'][0]['text']==expected and '[b]Literal & <world>[/b]' in expected
                    checks['three_button_alert_keeps_labels_order']= [b['text'] for b in w['buttons']]==['Yes','No','Cancel']
                    checks['long_message_container_stays_bounded']=all(not c['horizontal'] and c['rect']['height']/w['scale']<=360.1 and c['rect']['width']/w['scale']<=480.1 for c in w['scrolls'])
                    button(w,'Cancel');row=observation('long-original-alert-done')
                    checks['three_button_alert_exact_cancel_payload']='PROMPT_TOUCH|long-alert-response|Cancel' in log() and preserved(row)
                    w=ready('long-choice','Long original choices')
                    checks['long_original_choice_labels_fit']=all(i['textWidth']<=i['textAvailableWidth']+.1 for l in w['lists'] for i in l['items'])
                    item(w,'Concentration Enhancing Hormonal Gland');action(prompt(w['title']),'submit');row=observation('long-choice-done')
                    choices=re.findall(r'PROMPT_TOUCH\|long-choice-response\|([^\r\n]+)',log())
                    checks['long_choice_scroll_and_keyboard_submit_preserve_exact_payload']=bool(choices) and json.loads(choices[-1])=='Concentration Enhancing Hormonal Gland' and preserved(row)
                if a.long_content:
                    w=ready('wide-choice','Very long choice')
                    horizontal=next(c for c in w['scrolls'] if c['horizontal'])
                    checks['wide_choice_has_bounded_visible_horizontal_scroll']=horizontal['horizontalBarVisible'] and horizontal['rect']['width']/w['scale']<=480.1 and horizontal['rect']['x']>=0 and horizontal['rect']['x']+horizontal['rect']['width']<=w['width']
                    action(w,'scroll-right');w=prompt(w['title'])
                    checks['wide_choice_scroll_reaches_hidden_suffix']=next(c for c in w['scrolls'] if c['horizontal'])['horizontalScroll']>0
                    label='Concentration Enhancing Hormonal Gland / Diamond Encrusted Silver ChestPlate / Emerald Encrusted Silver ChestPlate'
                    rowitem=next(i for i in w['lists'][0]['items'] if i['text']==label)
                    rect=horizontal['rect'];action(w,'click',x=rect['x']+rect['width']/2,y=rowitem['rect']['y']+rowitem['rect']['height']/2)
                    if a.owner_logical_width:
                        action(w,'owner-resize',width=original_owner['pixelWidth'],height=original_owner['pixelHeight'])
                        until(lambda:prompt(w['title'])['ownerBounds']['pixelWidth']==original_owner['pixelWidth'])
                    if a.placement_checks:
                        action(w,'owner-position',x=original_owner['x'],y=original_owner['y'])
                        until(lambda:prompt(w['title'])['ownerBounds']['x']==original_owner['x'] and prompt(w['title'])['ownerBounds']['y']==original_owner['y'])
                        checks['private_owner_position_restored']=True
                    action(prompt(w['title']),'submit');row=observation('wide-choice-done')
                    returned=re.findall(r'PROMPT_TOUCH\|wide-choice-response\|([^\r\n]+)',log())
                    checks['wide_choice_scroll_preserves_exact_response']=bool(returned) and json.loads(returned[-1])==label and preserved(row)
                row=observation('empty-ally-done');checks['empty_list_returns_without_client_error']=preserved(row)
                until(lambda:'PROMPT_TOUCH|complete' in log());checks['fixture_completed']=True
                time.sleep(.5);report['non_prompt_after']=normal_geometry()
                checks['non_prompt_window_dimensions_unchanged']=report['non_prompt_before']==report['non_prompt_after']
                checks['repeated_prompts_closed_without_resize_loop']=not any(w.get('prompt') for w in state().get('windows',[]))
                for entry in report['prompts']:
                    w=entry['window']
                    checks[entry['phase']+'_buttons_inside_window']=all(b['rect']['x']>=0 and b['rect']['y']>=0 and b['rect']['x']+b['rect']['width']<=w['width']+1 and b['rect']['y']+b['rect']['height']<=w['height']+1 for b in w['buttons'])
                if a.placement_checks:
                    usable=report['screens'][0]['visible'];right=usable['x']+usable['width'];bottom=usable['y']+usable['height']
                    def on_screen(w):
                        n=w['nativeBounds']
                        return n['x']>=usable['x'] and n['y']>=usable['y'] and n['x']+n['width']<=right and n['y']+n['height']<=bottom
                    checks['all_initial_and_edge_prompts_inside_actual_usable_screen']=all(on_screen(e['window'])for e in report['prompts'])
                    checks['all_footer_controls_inside_actual_usable_screen']=all(w['nativeBounds']['x']+b['rect']['x']>=usable['x'] and w['nativeBounds']['y']+b['rect']['y']>=usable['y'] and w['nativeBounds']['x']+b['rect']['x']+b['rect']['width']<=right and w['nativeBounds']['y']+b['rect']['y']+b['rect']['height']<=bottom for e in report['prompts']for w in [e['window']]for b in w['buttons'])
                    first=report['prompts'][0]['window'];n=first['nativeBounds'];o=first['ownerBounds']
                    checks['initial_prompt_centered_on_owner']=abs(n['x']+n['width']/2-o['x']-o['width']/2)<=1 and abs(n['y']+n['height']/2-o['y']-o['height']/2)<=1
                if a.target_sizing:
                    windows=[entry['window'] for entry in report['prompts']]
                    checks['native_window_and_render_target_match']=all(w['renderTarget']['width']==w['width'] and w['renderTarget']['height']==w['height'] for w in windows)
                    if a.owner_logical_width:
                        checks['new_prompts_fit_320_logical_owner_width']=all(w['width']<=w['ownerBounds']['pixelWidth'] for e in report['prompts'] if e['phase'] not in ['rename-cancel','rename-visible-resize'] for w in [e['window']])
                    report['centering_offsets']=[dict(phase=e['phase'],dx=(w['nativeBounds']['x']+w['nativeBounds']['width']/2)-(w['ownerBounds']['x']+w['ownerBounds']['width']/2),dy=(w['nativeBounds']['y']+w['nativeBounds']['height']/2)-(w['ownerBounds']['y']+w['ownerBounds']['height']/2)) for e in report['prompts'] for w in [e['window']] if w.get('ownerBounds')]
                    checks['requested_ui_scale_used']=all(abs(w['scale']-a.ui_scale)<.01 for w in windows)
                    def inside(r,w):return r['x']>=-.1 and r['y']>=-.1 and r['x']+r['width']<=w['width']+.1 and r['y']+r['height']<=w['height']+.1
                    checks['all_prompt_buttons_minimum_72_by_44']=all(b['rect']['width']/w['scale']>=71.9 and b['rect']['height']/w['scale']>=43.9 and b['minWidth']>=72 and b['minHeight']>=44 for w in windows for b in w['buttons'])
                    checks['all_prompt_entries_minimum_44_and_inside']=all(e['rect']['height']/w['scale']>=43.9 and e['minHeight']>=44 and inside(e['rect'],w) for w in windows for e in w['lineEdits'])
                    checks['all_native_list_rows_minimum_44']=all(i['rect'] and i['rect']['height']/w['scale']>=43.9 for w in windows for rowlist in w['lists'] for i in rowlist['items'])
                    checks['list_viewports_bounded_inside_prompt']=all(inside(c['rect'],w) and w['height']/w['scale']<=400.1 for w in windows for c in w['scrolls'] if c['horizontal'])
                    checks['prompt_controls_do_not_overlap_footer']=all(e['rect']['y']+e['rect']['height']<=min(b['rect']['y'] for b in w['buttons'])+.1 for w in windows for e in w['lineEdits']+w['lists'])
                    checks['four_choice_potion_rows_fit_without_scroll']=all(i['rect']['y']>=l['rect']['y']-.1 and i['rect']['y']+i['rect']['height']<=l['rect']['y']+l['rect']['height']+.1 for entry in report['prompts'] if entry['phase'].startswith('potion') for l in entry['window']['lists'] for i in l['items'])
                    checks['long_guard_cancel_row_reached_by_scrolling']=any(row['text']=='Cancel' and row['scrolled'] for row in report.get('row_interactions',[]))
                checks['no_incidental_map_input']=all(r['incidentalInput']==0 for r in report['observations'])
        except Exception as error:report['error']=repr(error);report['last_state']=state()
        finally:
            stop(client);stop(server);(out/(a.label+'-world.log')).write_text(log())
            for path in probe.glob('prompt-*.png'):shutil.copy2(path,out/(a.label+'-'+path.name))
            for name in ('state.json','prompt-actions.jsonl'):
                if(probe/name).exists():shutil.copy2(probe/name,out/(a.label+'-'+name))
        logs={name:path.read_text(errors='replace')for name,path in [('server',slp),('client',clp),('world',out/(a.label+'-world.log'))]if path.exists()}
        report['errors']={k:re.findall(r'(?im)^.*(?:\[(?:ERRO|FATL)\]|\bruntime error\b|\bexception\b).*$',v)for k,v in logs.items()}
        report['native_events']=re.findall(r'native.ui.probe: (?:engine key|event)[^\r\n]*',logs.get('client',''))
        checks['no_os_input_events']=not report['native_events'];checks['no_save_created']=not list(world.rglob('*.sav'))
        checks['private_processes_stopped']=all(s is None or s.poll()is not None for s in (server,client))
    report['hashes_after']={k:sha(v)for k,v in tracked.items()};checks['sources_fixture_module_stable']=report['hashes_before']==report['hashes_after']
    report['passed']=bool(checks.get('fixture_completed')) and all(checks.values()) and not report.get('error') and not any(report['errors'].values())
    dest.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(report=str(dest),passed=report['passed'],checks=len(checks),failures=[k for k,v in checks.items()if not v],error=report.get('error'),errors=report['errors']),indent=2))
    return 0 if report['passed']else 1


if __name__=='__main__':raise SystemExit(main())
