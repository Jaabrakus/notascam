from pathlib import Path
from playwright.sync_api import sync_playwright
from urllib.parse import parse_qs,urlparse
import argparse,copy,hashlib,json
B=Path(__file__).resolve().parents[1];args=argparse.ArgumentParser();args.add_argument('--candidate',action='store_true');args.add_argument('--label',required=True);a=args.parse_args();html=B/'game'/'Interface/remastered.html';human=json.loads((B/'tests/work-human-model.json').read_text());orc=json.loads((B/'tests/work-orc-model.json').read_text());source=html.read_text().replace('window.location.href=','window.testLastURL=');r={'scope':'Real exported original Human/Orc models; trusted Chromium presses, transport only. Before/after original effects are separate headless checks.','html_sha256':hashlib.sha256(html.read_bytes()).hexdigest(),'checks':{},'cases':{},'errors':[]}
routes=[('priority','3'),('stance','hold'),('build','campfire'),('build','carpentry'),('job','woodcutter'),('craft','spade'),('cancel','all'),('workarea','unit'),('stockpile','unit'),('dropoff',''),('unloadresume','')]
with sync_playwright()as pw:
 browser=pw.chromium.launch(executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless=True)
 def setup(route,value):
  p=browser.new_page(viewport={'width':390,'height':844});p.on('pageerror',lambda e:r['errors'].append(str(e)));p.set_content(source,wait_until='domcontentloaded');m=copy.deepcopy(human);m['tab']='orders'if route in ['dropoff','unloadresume','stance']else'work';p.evaluate('m=>updateHUD(m)',m)
  selector=f'button[data-do="{route}"]'+(f'[data-value="{value}"]'if value else'');b=p.locator(selector).first;b.scroll_into_view_if_needed();p.evaluate("window.requests=[];Object.defineProperty(window,'testLastURL',{set:v=>requests.push(v),configurable:true})");return p,b,m
 def result(name,p,expected):
  requests=[{k:v[0]for k,v in parse_qs(urlparse(u).query,keep_blank_values=True).items()}for u in p.evaluate('requests')];r['checks'][name]=requests==expected;r['cases'][name]={'requests':requests,'expected':expected};p.close()
 def press(p,b):
  box=b.bounding_box();p.mouse.move(box['x']+box['width']/2,box['y']+box['height']/2);p.mouse.down()
 for route,value in routes:
  name=route+'-'+value;expected={'rm':route,'value':value,'selection':human['controlGroups']['selection']}
  for gesture in ['pointer','Space']:
   p,b,m=setup(route,value)
   if gesture=='pointer':press(p,b)
   else:b.focus();p.keyboard.down('Space')
   nextModel=copy.deepcopy(orc);nextModel['tab']=m['tab'];p.evaluate('m=>updateHUD(m)',nextModel)
   if gesture=='pointer':p.mouse.up()
   else:p.keyboard.up('Space')
   result(name+'_'+gesture+'_selection_change_cancels',p,[])
  p,b,m=setup(route,value);press(p,b);m['notice']='Status refresh';p.evaluate('m=>updateHUD(m)',m);p.mouse.up();result(name+'_stable_update_keeps_token',p,[expected])
  p,b,m=setup(route,value);b.evaluate('e=>e.click()');result(name+'_programmatic_current_token',p,[expected])
 for route,value in [('stockpile','camera'),('stockpile','clear'),('stockfilter','stone')]:
  p,b,m=setup(route,value);b.evaluate('e=>e.click()');result(route+'-'+value+'_global_no_token',p,[{'rm':route,'value':value}])
 browser.close()
r['passed']=all(r['checks'].values())and not r['errors'];(B/'tests'/(a.label+'-browser.json')).write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'passed':r['passed'],'checks':len(r['checks']),'failures':[k for k,v in r['checks'].items()if not v],'errors':r['errors']},indent=2))

raise SystemExit(0 if r['passed'] else 1)
