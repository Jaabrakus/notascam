#!/usr/bin/env python3
"""The unit card's Health tab with a bleeding stump (Stumps.dm), headless: the Health data the stumps arena made
(tools/check_stumps.py writes tests/stumps-arena/stump-health*.json) in a unit of a real HUD model, in the overlay page.
  1. headless Chrome: the "Stumps" block (the stump's line, its buttons), no clipped button, a button sends the
     `stump` command with the unit's ref, the bandaged state after it; stills at 1280x720 and 1024x640;
  2. a real WKWebView (rts-feel's wkcheck, no window, no input): no script errors, the same block drawn, and the
     buttons still fit there (WebKit draws text under 9 px at 9 px, so it comes out larger than in Chrome; STYLE.md).
Stills in reports/polish-2026-10-22/stump-care/."""
import json
import subprocess
import tempfile
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = Path(__file__).resolve().parents[1]
OUT = BASE/'reports/polish-2026-10-22/stump-care'
ARENA = BASE/'tests/stumps-arena'
OUT.mkdir(parents=True, exist_ok=True)


def model(health_file):
    m = json.loads((BASE/'tests/idle-model-available.json').read_text())
    for x in m['units']: x['selected'] = False
    u = m['units'][0]
    u['selected'] = True
    u['health'] = json.loads((ARENA/health_file).read_text())
    u['warnings'] = ['Leg injury', 'Bleeding stump']
    return m, u


PROBE = """()=>{const hf=document.querySelector('#heroframe');const rows=[...hf.querySelectorAll('.hfstump')];
 const btns=[...hf.querySelectorAll('button[data-do=stump]')];
 const z=parseFloat(document.documentElement.style.zoom)||1;
 const px=el=>parseFloat(getComputedStyle(el).fontSize)*z;
 return {tab:hf.dataset.tab||'',rows:rows.map(r=>r.textContent),edge:rows.map(r=>getComputedStyle(r).borderLeftColor),
  buttons:btns.map(b=>b.textContent),values:btns.map(b=>b.dataset.value),clipped:btns.filter(b=>b.scrollWidth>b.clientWidth+1).map(b=>b.textContent),
  minpx:Math.min(99,...rows.map(px),...btns.map(px)),hint:(hf.querySelector('.hfpane .hfnote')||{}).textContent||''}}"""


def chrome(html):
    errors = []
    seen = {}
    with tempfile.TemporaryDirectory(prefix='stump-hud-') as tmp, sync_playwright() as pw:
        page_file = Path(tmp)/'remastered.html'
        page_file.write_text(html, encoding='utf-8')
        browser = pw.chromium.launch(executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless=True)
        for w, h in ((1280, 720), (1024, 640)):
            page = browser.new_page(viewport=dict(width=w, height=h))
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.on('console', lambda c: errors.append(c.text[:300]) if c.type == 'error' and 'Failed to load resource' not in c.text else None)
            page.goto(page_file.as_uri() + '?overlay', wait_until='domcontentloaded')
            m, u = model('stump-health.json')
            for _ in range(2):
                page.evaluate('m=>updateHUD(m)', m)
                page.wait_for_timeout(300)
            page.evaluate("()=>{const c=document.getElementById('bootcover');if(c)c.remove()}")   # stills only: the boot cover waits for the game
            page.evaluate("()=>document.querySelector('#heroframe [data-hftab=health]').click()")
            page.wait_for_timeout(300)
            s = page.evaluate(PROBE)
            frame = page.locator('#heroframe')
            frame.screenshot(path=str(OUT/f'health-tab-open-{w}.png'))
            if w == 1280:
                seen['open'] = s
                page.evaluate("()=>{window.testLastURL='';const b=[...document.querySelectorAll('#heroframe button[data-do=stump]')].find(b=>b.textContent==='Bandage it');if(b)b.click()}")
                seen['sent'] = page.evaluate('()=>decodeURIComponent(window.testLastURL||"")')
                m2, _ = model('stump-health-bandaged.json')
                for _ in range(2):
                    page.evaluate('m=>updateHUD(m)', m2)
                    page.wait_for_timeout(300)
                seen['bandaged'] = page.evaluate(PROBE)
                frame.screenshot(path=str(OUT/'health-tab-bandaged-1280.png'))
            else: seen['small'] = s
            page.close()
        browser.close()
    return seen, errors


def webkit(html):
    with tempfile.TemporaryDirectory(prefix='stump-wk-') as tmp:
        tmp = Path(tmp)
        subprocess.run(['swiftc', '-O', str(BASE/'tools/rts_feel/wkcheck.swift'), '-o', str(tmp/'wkcheck')], check=True, capture_output=True)
        m, _ = model('stump-health.json')
        drive = ("<script>window.SC_M=" + json.dumps(m) + ";setTimeout(()=>{try{updateHUD(SC_M);updateHUD(SC_M);"
                 "document.querySelector('#heroframe [data-hftab=health]').click();setTimeout(()=>{window.SC_OUT=JSON.stringify((" + PROBE + ")())},400)}"
                 "catch(e){window.SC_OUT='ERR '+e}},1500)</script>")
        k = "<script>\n// The browser requests its first model only after every script"
        assert html.count(k) == 1
        # wkcheck has no dmOverlay handler and drops ?overlay: the test copy is put in overlay mode as the game's is
        page = html.replace(k, drive + k).replace('const overlayHost=!!(', 'const overlayHost=true||!!(', 1)
        (tmp/'page.html').write_text(page, encoding='utf-8')
        r = subprocess.run([str(tmp/'wkcheck'), str(tmp/'page.html'),'window.SC_OUT||"no result"', '7'], capture_output=True, text=True, timeout=120)
        lines = r.stdout.splitlines()
        res = next((l[len('RESULT '):] for l in lines if l.startswith('RESULT ')), '')
        errs = [l for l in lines if l.startswith('ERROR') or l.startswith('console.error')]
        try: data = json.loads(res.strip())
        except Exception: data = {'raw': res[:300]}
        return data, errs


def main():
    html = (BASE/'game/Interface/remastered.html').read_text(encoding='utf-8').replace('window.location.href=', 'window.testLastURL=')
    seen, errors = chrome(html)
    wk, wk_errors = webkit(html)
    o, b, s = seen['open'], seen['bandaged'], seen['small']
    checks = {
        'health_tab': o['tab'] == 'health',
        'stump_line': o['rows'] == ['Right leg stump, bleeding: needs fire or a bandage'],
        'buttons_now': o['buttons'] == ['Sear with a torch', 'Bandage it'],
        'no_clipped_buttons': not o['clipped'] and not s['clipped'],
        'button_sends_stump': seen['sent'].endswith('|bandage') and 'stump' in seen['sent'],
        'bandaged_line': b['rows'] == ['Right leg stump, bandaged: still bleeding slowly'] and b['buttons'] == ['Sear with a torch'],
        'small_window': s['rows'] == o['rows'],
        'no_script_errors': not errors,
        'webkit_drawn': wk.get('rows') == o['rows'] and wk.get('buttons') == o['buttons'],
        'webkit_no_errors': not wk_errors,
        'webkit_not_clipped': wk.get('clipped') == [],   # WebKit draws sub-9 px text at 9 px (STYLE.md): it must still fit
    }
    result = dict(passed=all(checks.values()), checks=checks, chrome=seen, webkit=wk, errors=errors[:5], webkit_errors=wk_errors[:5])
    (BASE/'tests/stumps-hud-checks.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=1))
    raise SystemExit(0 if result['passed'] else 1)


if __name__ == '__main__':
    main()
