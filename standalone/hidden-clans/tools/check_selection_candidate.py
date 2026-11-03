from pathlib import Path
from playwright.sync_api import sync_playwright
from urllib.parse import parse_qs,urlparse
import copy,hashlib,json
B=Path(__file__).resolve().parents[1];html=B/'game/Interface/remastered.html';human=json.loads((B/'tests/intent-human-model.json').read_text());orc=json.loads((B/'tests/intent-orc-model.json').read_text());source=html.read_text().replace('window.location.href=','window.testLastURL=');r={'scope':'Actual exported Human/Orc models and trusted browser presses; transport capture only. Receipt/delayed effects tested separately with original game.','html_sha256':hashlib.sha256(html.read_bytes()).hexdigest(),'checks':{},'cases':{},'errors':[]}
with sync_playwright()as pw:
 browser=pw.chromium.launch(executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless=True)
 def setup(area='dock'):
  p=browser.new_page(viewport={'width':390,'height':844});p.on('pageerror',lambda e:r['errors'].append(str(e)));p.set_content(source,wait_until='domcontentloaded');p.evaluate('m=>updateHUD(m)',human)
  if area=='controls':p.locator('#quickDock [data-ui=controls-open]').click()
  selector='#borderCatalog [data-control=stop] button'if area=='controls'else'#quickDock button[data-value=stop]';button=p.locator(selector);button.scroll_into_view_if_needed();p.evaluate("window.requests=[];Object.defineProperty(window,'testLastURL',{set:v=>requests.push(v),configurable:true})");return p,button
 def result(name,p,expected):
  requests=[{k:v[0]for k,v in parse_qs(urlparse(u).query).items()}for u in p.evaluate('requests')];r['checks'][name]=requests==expected;r['cases'][name]={'requests':requests,'expected':expected};p.close()
 def press(p,b):
  box=b.bounding_box();p.mouse.move(box['x']+box['width']/2,box['y']+box['height']/2);p.mouse.down()
 for area in ['dock','controls']:
  route='action'if area=='dock'else'borderaction';expected={'rm':route,'value':'stop','selection':human['controlGroups']['selection']}
  for gesture in ['pointer','Space']:
   p,b=setup(area)
   if gesture=='pointer':press(p,b)
   else:b.focus();p.keyboard.down('Space')
   p.evaluate('m=>updateHUD(m)',orc)
   if gesture=='pointer':p.mouse.up()
   else:p.keyboard.up('Space')
   result(area+'_'+gesture+'_selection_change_cancels',p,[])
  p,b=setup(area);press(p,b);m=copy.deepcopy(human);m['notice']='Updated';p.evaluate('m=>updateHUD(m)',m);p.mouse.up();result(area+'_unchanged_update_keeps_original_token',p,[expected])
  p,b=setup(area);press(p,b);p.evaluate('m=>updateHUD(m)',orc);p.evaluate('m=>updateHUD(m)',human);p.mouse.up();result(area+'_returning_old_selection_does_not_revive_press',p,[])
  p,b=setup(area);b.focus();p.keyboard.down('Enter');p.evaluate('m=>updateHUD(m)',orc);p.keyboard.down('Enter');p.keyboard.up('Enter');result(area+'_Enter_repeat_after_selection_change_keeps_first_request_only',p,[expected])
  p,b=setup(area);p.evaluate('m=>updateHUD(m)',orc);b.evaluate('e=>e.click()');result(area+'_programmatic_current_request_has_current_token',p,[dict(expected,selection=orc['controlGroups']['selection'])])
  p,b=setup(area);press(p,b);p.locator('#borderControls [data-ui=controls-close]'if area=='controls'else'#deselect').focus();b.focus();p.mouse.up();result(area+'_pointer_blur_does_not_revive_press',p,[])
  p,b=setup(area);b.focus();p.keyboard.down('Space');p.locator('#borderControls [data-ui=controls-close]'if area=='controls'else'#deselect').focus();b.focus();p.keyboard.up('Space');result(area+'_Space_blur_does_not_revive_press',p,[])
  p,b=setup(area);press(p,b);p.keyboard.press('Escape');p.mouse.up();result(area+'_Escape_cancels_held_action',p,[]if area=='controls'else[{'rm':'action','value':'clear'}])
 p,b=setup();p.locator('#deselect').evaluate('e=>e.click()');result('global_Deselect_has_no_selection_token',p,[{'rm':'action','value':'clear'}])
 r['checks']['real_models_mark_build_as_selection_bound']=all(any(c['id']=='build'and c['selectionBound']for c in rows)for rows in [human['commands'],human['border']['controls']])
 r['checks']['real_models_do_not_bind_global_camera_or_clear']=not next(c for c in human['commands']if c['id']=='coords')['selectionBound']and not next(c for c in human['commands']if c['id']=='clear')['selectionBound']
 browser.close()
r['passed']=all(r['checks'].values())and not r['errors'];(B/'tests/sixth-final-selection-browser.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'passed':r['passed'],'checks':len(r['checks']),'failures':[k for k,v in r['checks'].items()if not v],'errors':r['errors']},indent=2))

raise SystemExit(0 if r["passed"] else 1)
