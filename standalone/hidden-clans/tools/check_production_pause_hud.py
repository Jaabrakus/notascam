#!/usr/bin/env python3
"""Render exported real-unit models; verify paused crafting has one-tap Resume."""
import argparse,hashlib,json
from pathlib import Path
from urllib.parse import parse_qs,urlparse
from playwright.sync_api import sync_playwright
p=argparse.ArgumentParser();p.add_argument('--html',type=Path,required=True);p.add_argument('--models',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
html=a.html.read_text().replace('window.location.href=','window.testLastURL=')
out={'scope':'Responsive browser DOM and transport using exported original Human/Orc game models; no native client or physical touch claim.','html_sha256':hashlib.sha256(a.html.read_bytes()).hexdigest(),'checks':{},'errors':[],'model_hashes':{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in a.models.glob('*.json')}}
with sync_playwright() as pw:
    browser=pw.chromium.launch(executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless=True)
    for width,height in [(320,568),(390,625),(768,844)]:
        for race in ['Human','Orc']:
            page=browser.new_page(viewport={'width':width,'height':height},is_mobile=True,has_touch=True)
            page.on('pageerror',lambda e:out['errors'].append(str(e)))
            page.set_content(html,wait_until='domcontentloaded')
            def check(k,v):out['checks'][f'{race}_{width}_{k}']=bool(v)
            for phase in ['stopped','handoff']:
                model=json.loads((a.models/f'pause-model-{race}-{phase}.json').read_text())
                page.evaluate('m=>updateHUD(m)',model)
                expected=model['units'][0]['ref']
                card=page.locator('#units article.selected')
                button=card.locator('.orderwork button[data-do=unitresume]')
                exists=button.count()==1
                check(phase+'_resume_shown',exists and button.inner_text()=='Resume')
                text=card.locator('.taskempty').inner_text()
                check(phase+'_retained_crafting_explained','1 crafting attempt queued' in text and 'paused' in text and 'Work' in text)
                if exists:
                    button.click()
                    req={k:v[0] for k,v in parse_qs(urlparse(page.evaluate('testLastURL')).query).items()}
                    check(phase+'_one_click_addresses_original_actor',req=={'rm':'unitresume','value':expected})
                    check(phase+'_touch_sized',button.evaluate('e=>{const r=e.getBoundingClientRect();return r.width>=44&&r.height>=44&&r.left>=0&&r.right<=innerWidth}'))
                else:
                    check(phase+'_one_click_addresses_original_actor',False);check(phase+'_touch_sized',False)
            model=json.loads((a.models/f'pause-model-{race}-resumed.json').read_text())
            page.evaluate('m=>updateHUD(m)',model)
            check('resumed_has_pause_control',page.locator('#units article.selected .orderwork button[data-do=unitpause]').count()==1)
            check('no_horizontal_overflow',page.evaluate('document.documentElement.scrollWidth<=innerWidth'))
            if width==390 and race=='Human':page.screenshot(path=str(a.output.with_suffix('.png')))
            page.close()
    browser.close()
out['passed']=all(out['checks'].values()) and not out['errors'];a.output.write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({'passed':out['passed'],'checks':len(out['checks']),'failures':[k for k,v in out['checks'].items() if not v],'errors':out['errors']}));raise SystemExit(0 if out['passed'] else 1)
