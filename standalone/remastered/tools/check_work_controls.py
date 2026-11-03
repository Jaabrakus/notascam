#!/usr/bin/env python3
"""Real browser input while the Work model changes; transport only is captured."""
import argparse, copy, hashlib, json
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from playwright.sync_api import sync_playwright

parser=argparse.ArgumentParser()
parser.add_argument('--html',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
html=args.html.read_text().replace('window.location.href=','window.testLastURL=')
result=dict(scope='Browser pointer/keyboard continuity and request contracts; no native game effects.',html_sha256=hashlib.sha256(args.html.read_bytes()).hexdigest(),checks={},errors=[])
with sync_playwright() as pw:
    browser=pw.chromium.launch(executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless=True)
    for width,height in [(320,568),(390,625),(768,844)]:
        page=browser.new_page(viewport=dict(width=width,height=height),is_mobile=True,has_touch=True)
        page.on('pageerror',lambda e:result['errors'].append(str(e)))
        page.set_content(html,wait_until='domcontentloaded')
        page.evaluate("window.testRequests=[];const previousSend=send;send=(a,v)=>{testRequests.push([a,v]);previousSend(a,v)}")
        unit=dict(ref='worker-a:1',name='Human A',race='Human',level=1,role='Miner',skill=4,selected=True,portrait='',hp=100,maxhp=100,fullness=80,maxfullness=100,energy=80,cold=0,weight=25,capacity=110,warnings=[],order='Mining',queued=1,job='miner',x=20,y=20,z=1,items=[],tools='Uses tools',equipment='Can wear armour',paused=False,blocked='',autoUnload=True,pending=[])
        work=dict(ref=unit['ref'],name=unit['name'],job='miner',priority=2,status='Mining',paused=False,queue=[],area=dict(x=20,y=20,z=1,radius=6))
        model=dict(tab='work',notice='Ready',units=[unit],selection=1,multi=False,queue=False,season='Summer',day='Day',date=1,x=20,y=20,z=1,maxx=40,maxy=40,maxz=1,idle=0,alert=0,targets=[],mode='',tutorialHidden=True,milestones={},commands=[],settlement=dict(stockpile=dict(set=True,x=20,y=20,z=1,filter='mixed',accepts='wood and stone'),jobs=[dict(id=i,label=n) for i,n in [('manual','Manual'),('woodcutter','Woodcutter'),('miner','Miner'),('hauler','Hauler')]],recipes=[dict(id=i,label=n,cost='1 wood per attempt',available=True,reason='Wood and workshop required') for i,n in [('bucket','Wooden bucket'),('spade','Wooden spade'),('spike','Wooden spike')]],units=[work],message='Ready'))
        def render():page.evaluate('m=>updateHUD(m)',model)
        def reset():page.evaluate("window.testLastURL='byond://?rm=unchanged';testRequests.length=0")
        def req():return {k:v[0] for k,v in parse_qs(urlparse(page.evaluate('window.testLastURL')).query).items()}
        def check(name,value):result['checks'][f'{name}_{width}']=bool(value)
        def centre(selector):
            page.locator(selector).evaluate('e=>scrollTo(0,scrollY+e.getBoundingClientRect().top-innerHeight*.55)')
            b=page.locator(selector).bounding_box();return b['x']+b['width']/2,b['y']+b['height']/2
        render();reset()
        for selector,action,value in [('#jobs [data-value=hauler]','job','hauler'),('#recipes [data-value=bucket]','craft','bucket')]:
            x,y=centre(selector);page.mouse.move(x,y);page.mouse.down()
            page.evaluate('s=>window.held=document.querySelector(s)',selector)
            work['status']='Delivering';work['queue'].append('spade');model['settlement']['message']='Updated carrying state'
            render()
            check(action+'_status_update_retains_pressed_control',page.locator(selector).evaluate('e=>e===held&&e===document.activeElement'))
            page.mouse.up()
            check(action+'_release_after_status_update_sends_once',req()==dict(rm=action,value=value) and page.evaluate('testRequests.length')==1)
            reset()
        recipe=page.locator('#recipes [data-value=spade]');recipe.focus();page.evaluate('window.focusedRecipe=document.activeElement')
        model['settlement']['stockpile'].update(filter='stone',accepts='Stone');render()
        page.keyboard.press('Enter')
        check('stockpile_update_keeps_focused_recipe_and_keyboard_action',page.evaluate('focusedRecipe===document.activeElement') and req()==dict(rm='craft',value='spade'))
        reset();recipe.focus();model['settlement']['recipes'][1].update(available=False,reason='Queue is full (10 attempts)');render();page.keyboard.press('Enter')
        check('unavailable_recipe_cancels_focus_without_command',recipe.is_disabled() and req()==dict(rm='unchanged') and page.evaluate("document.activeElement.id==='productionHeading'"))
        model['settlement']['recipes'][1].update(available=True,reason='Wood and workshop required');render()
        for selector,action in [('#jobs [data-value=hauler]','job'),('#recipes [data-value=bucket]','craft')]:
            reset();x,y=centre(selector);page.mouse.move(x,y);page.mouse.down();page.evaluate('s=>window.oldActorButton=document.querySelector(s)',selector)
            suffix='b' if unit['ref'].startswith('worker-a') else 'a';unit['ref']='worker-'+suffix+':1';work['ref']=unit['ref'];unit['name']='Human '+suffix.upper();work['name']=unit['name'];render();page.mouse.up()
            check(action+'_changed_selection_cancels_held_tap',page.evaluate('!oldActorButton.isConnected') and req()==dict(rm='unchanged'))
        unit['selected']=False;model['selection']=0;model['settlement']['units']=[];render();reset()
        for button in page.locator('#jobs button').all():button.evaluate('e=>e.click()')
        check('empty_selection_disables_roles_with_reason',page.locator('#jobs button:disabled').count()==4 and req()==dict(rm='unchanged') and page.locator('#roleReason').count()>0 and 'Select' in page.locator('#roleReason').inner_text())
        unit['selected']=True;model['selection']=1;model['settlement']['units']=[work];render()
        check('role_buttons_show_current_role',page.locator('#jobs [data-value=miner]').get_attribute('aria-pressed')=='true' and page.locator('#jobs [aria-pressed=true]').count()==1)
        check('work_controls_fit_touch_targets',page.locator('#jobs button,#recipes button').evaluate_all('els=>els.length===7&&els.every(e=>{const r=e.getBoundingClientRect();return r.width>=44&&r.height>=44&&r.left>=0&&r.right<=innerWidth})') and page.evaluate('document.documentElement.scrollWidth<=innerWidth'))
        if width==390:
            centre('#jobs [data-value=miner]');page.screenshot(path=str(args.output.with_suffix('.png')))
        page.close()
    browser.close()
result['passed']=all(result['checks'].values()) and not result['errors']
args.output.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(passed=result['passed'],checks=len(result['checks']),failures=[k for k,v in result['checks'].items() if not v],errors=result['errors'])))
raise SystemExit(0 if result['passed'] else 1)
