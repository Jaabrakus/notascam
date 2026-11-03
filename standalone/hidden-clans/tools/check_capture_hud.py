#!/usr/bin/env python3
"""A captive's card in the overlay HUD (Captives.dm): headless Chrome (?overlay) and a real WKWebView
(tools/rts_feel/wkcheck.swift). One of your units selected as a bound captive, then as a slave; the Interact tab
must show the captive section (bound/led, the rope and how strong, loyalty bar, "May break free: <risk>" with the
reasons in its tip, and the buttons), the Family tab its line, and a click on Win over must send the "captive"
command. Then the Interact (I) card of one of yours beside a knocked-out enemy (no rope: says so) and beside a
captive of yours (Win over). Stills land in reports/polish-2026-10-22/capture-rope/.

    python3 tools/check_capture_hud.py [--no-webkit]
"""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from playwright.sync_api import sync_playwright

BASE = Path(__file__).resolve().parents[1]
OUT = BASE/'reports/polish-2026-10-22/capture-rope'
HTML = (BASE/'game/Interface/remastered.html').read_text(encoding='utf-8').replace('window.location.href=', 'window.testLastURL=')
CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'


def models():
    m = json.loads((BASE/'tests/idle-model-available.json').read_text())
    for x in m['units']: x['selected'] = False
    u = m['units'][0]
    u['selected'] = True
    u['name'] = 'Goblin Scout'
    u['race'] = 'Goblin'
    u['family'] = {'partners': [], 'expecting': 0, 'captive': 'bound', 'kin': None}
    u['captive'] = {'state': 'bound', 'rope': 'Silk Rope - Grand Quality', 'ropeWord': 'very strong', 'ropePower': 72, 'loyalty': 35,
                    'odds': 14, 'risk': 'high', 'why': ['silk rope - grand quality: very strong', 'left alone', 'half won over (35%)'],
                    'led': None, 'tied': 1, 'post': 1, 'postKind': 'stake', 'canStake': 1, 'talker': 'Grak', 'armed': 0, 'fights': 0, 'from': 'the Goblins'}
    bound = json.loads(json.dumps(m))
    out = json.loads(json.dumps(m)); out['units'][0]['captive']['out'] = 1
    caged = json.loads(json.dumps(m)); caged['units'][0]['captive'].update(cage='Wooden Cage', led=None, rope=None, ropeWord=None, ropePower=0, odds=0, risk='none', canOut=1)   # caged: the rope is off them
    u['name'] = 'Slave Goblin Scout'
    u['family']['captive'] = 'slave'
    u['captive'] = {'state': 'slave', 'rope': 'Plant Rope - Poor Quality', 'ropeWord': 'flimsy', 'ropePower': 16, 'loyalty': 22, 'odds': None,
                    'risk': None, 'why': [], 'led': None, 'tied': 0, 'post': 0, 'talker': None, 'armed': 1, 'fights': 0, 'from': 'the Goblins'}
    slave = json.loads(json.dumps(m))
    # the Interact (I) card: one of yours beside a knocked-out raider (no rope anywhere) and beside a captive of yours
    u['captive'] = None
    u['family'] = {'partners': [], 'expecting': 0, 'captive': None, 'kin': None}
    u['name'] = 'Grak'
    u['nearby'] = [{'ref': None, 'id': '[0x3000001]', 'name': 'Goblin Scout', 'race': 'Goblin', 'kind': 'hostile', 'dist': 1, 'hp': 30, 'ko': 1,
                    'critter': 0, 'acts': ['capture', 'attack'], 'uses': None, 'captive': None, 'rope': ''},
                   {'ref': 'ui-captive-1', 'id': '[0x3000002]', 'name': 'Orc Hunter', 'race': 'Orc', 'kind': 'yours', 'dist': 2, 'hp': 80, 'ko': 0,
                    'critter': 0, 'acts': ['select', 'winover'], 'uses': [], 'captive': 'bound', 'rope': None}]
    near = json.loads(json.dumps(m))
    return bound, slave, near, out, caged


READ = """()=>{const hf=document.querySelector('#heroframe'),cap=hf&&hf.querySelector('.hfpane[data-pane=interact] .hfcap'),fam=hf&&hf.querySelector('.hfpane[data-pane=family]');
 const btn=[...(cap?cap.querySelectorAll('button[data-do=captive]'):[])].map(b=>b.dataset.value.split('|')[1]);
 const risk=cap&&cap.querySelector('.caprisk'),bar=cap&&cap.querySelector('.bar.caploy span');
 const r=cap?cap.getBoundingClientRect():null;
 return {tab:hf&&hf.dataset.tab,text:cap?cap.innerText.replace(/\\s+/g,' ').trim():'',buttons:btn,risk:risk?risk.textContent.trim():'',riskTip:risk?risk.title:'',
  bar:bar?bar.style.width:'',family:fam?fam.innerText.replace(/\\s+/g,' ').trim().slice(0,200):'',
  clipped:cap?[...cap.querySelectorAll('button,b,strong,em')].filter(e=>e.scrollWidth>e.clientWidth+1).map(e=>e.textContent.trim()).slice(0,5):[],
  box:r?[Math.round(r.left),Math.round(r.top),Math.round(r.width),Math.round(r.height)]:null}}"""


def chrome(bound, slave, near, errors, out=None, caged=None):
    seen = {}
    with tempfile.TemporaryDirectory(prefix='capture-hud-') as tmp, sync_playwright() as pw:
        page_file = Path(tmp)/'remastered.html'
        page_file.write_text(HTML, encoding='utf-8')
        browser = pw.chromium.launch(executable_path=CHROME, headless=True)
        page = browser.new_page(viewport=dict(width=1280, height=720))
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.on('console', lambda c: errors.append(c.text[:300]) if c.type == 'error' and 'Failed to load resource' not in c.text else None)
        page.add_init_script("try{localStorage.setItem('rm-hftab','interact')}catch(_){}")
        page.add_init_script("addEventListener('DOMContentLoaded',()=>{const st=document.createElement('style');st.textContent='#bootcover{display:none!important}*,*::before,*::after{transition:none!important;animation:none!important}';document.head.append(st)})")
        page.goto(page_file.as_uri() + '?overlay', wait_until='domcontentloaded')
        for name, m in (('bound', bound), ('slave', slave)):
            for _ in range(2):
                page.evaluate('m=>updateHUD(m)', m)
                page.wait_for_timeout(250)
            seen[name] = page.evaluate(READ)
            hf = page.query_selector('#heroframe')
            if hf: hf.screenshot(path=str(OUT/f'card-{name}-chrome.png'))
        # out cold: Win over is greyed out and says why
        for _ in range(2):
            page.evaluate('m=>updateHUD(m)', out)
            page.wait_for_timeout(200)
        seen['outcold'] = page.evaluate("""()=>{const b=[...document.querySelectorAll('#heroframe .hfcap button[data-do=captive]')].find(x=>x.dataset.value.endsWith('|win'));return b?{disabled:b.disabled,tip:b.title}:null}""")
        for _ in range(2):
            page.evaluate('m=>updateHUD(m)', caged)
            page.wait_for_timeout(200)
        seen['caged'] = page.evaluate(READ)
        # nobody near the cage with a rope: Take out is greyed out and says why
        nr = json.loads(json.dumps(caged)); nr['units'][0]['captive']['canOut'] = 0
        for _ in range(2):
            page.evaluate('m=>updateHUD(m)', nr)
            page.wait_for_timeout(200)
        seen['caged_norope'] = page.evaluate("""()=>{const b=[...document.querySelectorAll('#heroframe .hfcap button[data-do=captive]')].find(x=>x.dataset.value.endsWith('|uncage'));return b?{disabled:b.disabled,tip:b.title}:null}""")
        # a click on Win over sends the command
        page.evaluate('m=>updateHUD(m)', bound)
        page.wait_for_timeout(200)
        page.evaluate("()=>{window.testLastURL=null;const b=document.querySelector('#heroframe .hfcap button[data-value$=\"|win\"]');if(b)b.click()}")
        page.wait_for_timeout(200)
        seen['sent'] = page.evaluate('()=>String(window.testLastURL||"")')
        # the Family tab's line
        page.evaluate("()=>{const t=document.querySelector('#heroframe [data-hftab=family]');if(t)t.click()}")
        page.wait_for_timeout(200)
        seen['family'] = page.evaluate("()=>{const p=document.querySelector('#heroframe .hfpane[data-pane=family]');return p?p.innerText.replace(/\\s+/g,' ').trim().slice(0,160):''}")
        page.evaluate("()=>{const t=document.querySelector('#heroframe [data-hftab=interact]');if(t)t.click()}")
        # the Interact (I) card
        for _ in range(2):
            page.evaluate('m=>updateHUD(m)', near)
            page.wait_for_timeout(250)
        page.evaluate("()=>nearCardToggle(true)")
        page.wait_for_timeout(250)
        seen['near'] = page.evaluate("""()=>{const c=document.querySelector('#nearcard');if(!c||c.hidden)return null;
          const cap=c.querySelector('button[data-do=captureorder]'),win=c.querySelector('button[data-do=captive]');
          return {capture:cap?cap.textContent.trim():'',captureTip:cap?cap.title:'',win:win?win.dataset.value:''}}""")
        nc = page.query_selector('#nearcard')
        if nc: nc.screenshot(path=str(OUT/'near-card-chrome.png'))
        browser.close()
    return seen


def webkit(bound, slave, errors):
    """A real WKWebView in the game's overlay mode (capwk.swift: hud-craft's wkshot with wkcheck's byond:// guard)."""
    from PIL import Image
    swift = OUT/'capwk.swift'
    exe = Path(tempfile.gettempdir())/'capwk-capture-rope'
    if not exe.exists() or exe.stat().st_mtime < swift.stat().st_mtime:
        subprocess.run(['swiftc', '-O', str(swift), '-o', str(exe)], check=True, capture_output=True)
    seen = {}
    with tempfile.TemporaryDirectory(prefix='capture-hud-wk-') as tmp:
        page = Path(tmp)/'remastered.html'
        page.write_text(HTML, encoding='utf-8')
        for name, m in (('bound', bound), ('slave', slave)):
            scene = Path(tmp)/f'{name}.js'
            scene.write_text('const w=t=>new Promise(r=>setTimeout(r,t));const c=document.getElementById("bootcover");if(c)c.remove();'
                             '{const st=document.createElement("style");st.textContent="*,*::before,*::after{transition:none!important;animation:none!important}";document.head.append(st)}'
                             "try{localStorage.setItem('rm-hftab','interact')}catch(_){}heroTab='interact';"
                             'const m=' + json.dumps(m) + ';updateHUD(m);await w(250);updateHUD(m);await w(400);'
                             'const hf=document.querySelector("#heroframe").getBoundingClientRect();'
                             'return JSON.stringify(Object.assign((' + READ + ')(),{hf:[hf.left,hf.top,hf.width,hf.height],W:innerWidth}))', encoding='utf-8')
            shot = Path(tmp)/f'{name}.png'
            r = subprocess.run([str(exe), str(page), '1280', '720', str(scene), str(shot), '2'], capture_output=True, text=True, timeout=90)
            lines = r.stdout.splitlines()
            errors += [f'wk {name}: {l}' for l in lines if (l.startswith('ERROR') or l.startswith('console.error') or l.startswith('SCRIPT-ERROR') or l.startswith('TIMEOUT')) and 'Failed to load resource' not in l]
            probe = next((l[6:] for l in lines if l.startswith('PROBE ')), '')
            try: seen[name] = json.loads(probe)
            except Exception: seen[name] = {'raw': lines[-4:]}
            if shot.exists() and 'hf' in seen[name]:
                im = Image.open(shot)
                k = im.width / 1280
                x, y, w_, h_ = seen[name]['hf']
                im.crop((int(x * k) - 8, int(y * k) - 8, int((x + w_) * k) + 8, int((y + h_) * k) + 8)).save(OUT/f'card-{name}-webkit.png')
    return seen


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    bound, slave, near, out, caged = models()
    errors = []
    seen = {'chrome': chrome(bound, slave, near, errors, out, caged)}
    if '--no-webkit' not in sys.argv: seen['webkit'] = webkit(bound, slave, errors)
    c = seen['chrome']
    checks = {
        'bound_section': 'Tied to a stake' in c['bound']['text'] and 'Silk Rope - Grand Quality' in c['bound']['text'],
        'bound_risk': c['bound']['risk'].endswith('May break free: high') and 'left alone' in c['bound']['riskTip'],
        'bound_loyalty': c['bound']['bar'] == '35%' and 'Grak is winning them over' in c['bound']['text'],
        'bound_buttons': c['bound']['buttons'] == ['win', 'enslave', 'release', 'move', 'lead', 'line', 'post', 'stake', 'cage'],
        'slave_section': 'Hobbled' in c['slave']['text'] and 'may turn on you' in c['slave']['text'] and not c['slave']['risk'],
        'slave_buttons': c['slave']['buttons'] == ['win', 'release'],
        'win_sends': 'captive' in c['sent'] and ('%7Cwin' in c['sent'] or '|win' in c['sent']),
        'family_line': 'Bound captive · not of your house' in c['family'],
        'near_no_rope': bool(c['near']) and c['near']['capture'].endswith('no rope') and 'needs a rope' in c['near']['captureTip'],
        'near_win_over': bool(c['near']) and c['near']['win'].endswith('|win|' + bound['units'][0]['ref']),
        'outcold_win_greyed': bool(c.get('outcold')) and c['outcold']['disabled'] and 'Out cold' in c['outcold']['tip'],
        'caged_card': 'Shut in a wooden cage' in c['caged']['text'] and 'Silk Rope' not in c['caged']['text'] and c['caged']['buttons'] == ['win', 'enslave', 'release', 'uncage'],
        'caged_takeout_needs_rope': bool(c.get('caged_norope')) and c['caged_norope']['disabled'] and 'rope' in c['caged_norope']['tip'],
        'nothing_clipped': not c['bound']['clipped'] and not c['slave']['clipped'],
        'no_script_errors': not errors,
    }
    if 'webkit' in seen:
        w = seen['webkit']
        checks['webkit_bound'] = w.get('bound', {}).get('buttons') == ['win', 'enslave', 'release', 'move', 'lead', 'line', 'post', 'stake', 'cage'] and 'May break free: high' in w['bound'].get('risk', '')
        checks['webkit_slave'] = w.get('slave', {}).get('buttons') == ['win', 'release']
        checks['webkit_nothing_clipped'] = not w.get('bound', {}).get('clipped') and not w.get('slave', {}).get('clipped')
    result = dict(passed=all(checks.values()), checks=checks, seen=seen, errors=errors[:8])
    (BASE/'tests/capture-hud-checks.json').write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps(dict(passed=result['passed'], checks=checks, errors=errors[:8]), indent=1, ensure_ascii=False))
    raise SystemExit(0 if result['passed'] else 1)


if __name__ == '__main__':
    main()
