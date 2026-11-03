#!/usr/bin/env python3
"""Use exported real-unit states to verify which one-tap work control is offered."""
from pathlib import Path
from urllib.parse import parse_qs,urlparse
import argparse,hashlib,json
from playwright.sync_api import sync_playwright
B=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--label',required=True);p.add_argument('--models',type=Path,required=True);a=p.parse_args()
html=B/'game/Interface/remastered.html';source=html.read_text().replace('window.location.href=','window.testLastURL=');report={'scope':__doc__+' Chromium DOM/transport; no physical/native touch claim.','html_sha256':hashlib.sha256(html.read_bytes()).hexdigest(),'model_hashes':{},'checks':{},'errors':[]}
with sync_playwright() as pw:
 browser=pw.chromium.launch(executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless=True)
 for path in sorted(a.models.glob('projection-model-*.json')):
  report['model_hashes'][path.name]=hashlib.sha256(path.read_bytes()).hexdigest();model=json.loads(path.read_text());phase=path.stem.rsplit('-',1)[1];action='unitpause' if phase=='running' else 'unitresume';label='Pause' if phase=='running' else 'Resume';unit=model['units'][0]
  for tab,container in [('units','#units article.selected'),('orders','#orderunits article')]:
   page=browser.new_page(viewport={'width':390,'height':625},is_mobile=True,has_touch=True);page.on('pageerror',lambda e:report['errors'].append(str(e)));page.set_content(source,wait_until='domcontentloaded');model['tab']=tab;page.evaluate('m=>updateHUD(m)',model);key=path.stem+'-'+tab;b=page.locator(container+' .orderwork button[data-do='+action+']') if tab=='units' else page.locator(container+' button[data-do='+action+']')
   found=b.count()==1;report['checks'][key+'-correct-control']=found and b.inner_text()==label
   if found:
    b.scroll_into_view_if_needed();report['checks'][key+'-touch-sized']=b.evaluate('e=>{const r=e.getBoundingClientRect();return r.width>=44&&r.height>=44&&r.left>=0&&r.right<=innerWidth}')
    b.tap();request={k:v[0]for k,v in parse_qs(urlparse(page.evaluate('testLastURL')).query).items()};report['checks'][key+'-targets-original-unit']=request==dict(rm=action,value=unit['ref'])
   else:
    report['checks'][key+'-touch-sized']=False;report['checks'][key+'-targets-original-unit']=False
   report['checks'][key+'-no-horizontal-overflow']=page.evaluate('document.documentElement.scrollWidth<=innerWidth')
   if path.stem=='projection-model-Human-both-running' and tab=='orders':page.screenshot(path=str(B/'tests'/(a.label+'-running.png')))
   page.close()
 browser.close()
report['passed']=all(report['checks'].values())and not report['errors'];(B/'tests'/(a.label+'-browser.json')).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(passed=report['passed'],checks=len(report['checks']),failures=[k for k,v in report['checks'].items()if not v],errors=report['errors']),indent=2));raise SystemExit(0 if report['passed'] else 1)
