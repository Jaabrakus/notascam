#!/usr/bin/env python3
"""Check the idle button against exported real-unit HUD models; transport only."""
import argparse,json,re,hashlib
from pathlib import Path
from urllib.parse import parse_qs,urlparse
from playwright.sync_api import sync_playwright
BASE=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--before',action='store_true');a=p.parse_args()
html_path=BASE/'remastered.before.html' if a.before else BASE/'game/Interface/remastered.html'
html=html_path.read_text().replace('window.location.href=','window.testLastURL=')
models={phase:json.loads((BASE/'tests'/f'idle-model-{phase}.json').read_text())for phase in ['available','first','second','none']}
r=dict(checks={},errors=[],html_sha256=hashlib.sha256(html_path.read_bytes()).hexdigest(),scope=__doc__);checks=r['checks']
with sync_playwright()as pw:
 browser=pw.chromium.launch(executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless=True)
 for width in (320,390,768):
  page=browser.new_page(viewport=dict(width=width,height=625),is_mobile=True,has_touch=True);page.on('pageerror',lambda e:r['errors'].append(str(e)));page.set_content(html,wait_until='domcontentloaded')
  def render(phase):page.evaluate('m=>updateHUD(m)',models[phase])
  def request():return {k:v[0]for k,v in parse_qs(urlparse(page.evaluate('window.testLastURL')).query).items()}
  render('available');idle=page.locator('#idle');idle.scroll_into_view_if_needed()
  checks[f'clear_single_unit_cycle_label_and_count_{width}']='Next idle' in idle.inner_text() and str(models['available']['idle'])in idle.inner_text() and 'next idle unit' in idle.get_attribute('aria-label')
  checks[f'idle_touch_target_fits_{width}']=idle.evaluate('e=>{const r=e.getBoundingClientRect();return r.width>=44&&r.height>=44&&r.left>=0&&r.right<=innerWidth&&document.documentElement.scrollWidth<=innerWidth}')
  idle.tap();checks[f'one_tap_sends_only_idle_request_{width}']=request()==dict(rm='idle')
  idle.focus();page.evaluate('window.savedIdle=document.activeElement');render('first')
  checks[f'first_server_selection_keeps_idle_control_and_focus_{width}']=page.evaluate('savedIdle===document.querySelector("#idle")&&document.activeElement===savedIdle') and page.locator('#units .unitpick[aria-pressed=true]').count()==1
  page.keyboard.press('Enter');render('second')
  selected=[u['ref']for u in models['second']['units']if u['selected']]
  checks[f'repeated_activation_keeps_transport_and_updates_single_selection_{width}']=request()==dict(rm='idle') and selected!=[u['ref']for u in models['first']['units']if u['selected']] and page.locator('#units .unitpick[aria-pressed=true]').count()==1
  render('none');page.evaluate("window.testLastURL='byond://?rm=unchanged'");idle.evaluate('e=>e.click()')
  checks[f'empty_idle_count_disables_with_clear_reason_and_no_request_{width}']=idle.is_disabled() and 'No idle units' in idle.get_attribute('aria-label') and request()==dict(rm='unchanged')
  if width==390 and not a.before:page.screenshot(path=str(BASE/'tests/idle-hud.png'))
  page.close()
 browser.close()
r['passed']=all(checks.values())and not r['errors'];dest=BASE/'tests'/('idle-browser-before.json'if a.before else'idle-browser-after.json');dest.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(passed=r['passed'],checks=len(checks),failures=[k for k,v in checks.items()if not v],errors=r['errors'],report=str(dest)),indent=2));raise SystemExit(0 if r['passed']else 1)
