#!/usr/bin/env python3
"""Drag body / Let go on the page (BodyDrag.dm; capture-rope, 2026-10-25), headless Chrome (?overlay): one unit selected
beside a body it can drag (act "dragbody"), one it drags ("letgo") and, the switch off, one to carry ("carrybody").
The Interact (I) card must show Drag / Let go / Carry with the "carrybody" command (ref|body, ref|body|0, ref|body), and
the body's right-click card (v3menuOpen, the 3D pick stubbed to the body) "Drag body" / "Let go" / "Carry the body".

    python3 tools/check_body_drag_hud.py [page]   (default game/Interface/remastered.html)"""
import json
from pathlib import Path
import sys
import tempfile
from playwright.sync_api import sync_playwright

BASE = Path(__file__).resolve().parents[1]
PAGE = Path(sys.argv[1]) if len(sys.argv) > 1 else BASE/'game/Interface/remastered.html'
CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
BODIES = [('[0x3000101]', 'Maric', 'dragbody'), ('[0x3000102]', 'Edda', 'letgo'), ('[0x3000103]', 'Osric', 'carrybody')]


def model():
    m = json.loads((BASE/'tests/idle-model-available.json').read_text())
    for x in m['units']: x['selected'] = False
    u = m['units'][0]
    u['selected'] = True
    u['nearby'] = [{'id': i, 'name': n, 'kind': 'body', 'dist': 1, 'acts': [a]} for i, n, a in BODIES]
    return m, u['ref']


def main():
    m, ref = model()
    errors = []
    html = PAGE.read_text(encoding='utf-8').replace('window.location.href=', 'window.testLastURL=')
    with tempfile.TemporaryDirectory(prefix='bodydrag-hud-') as tmp, sync_playwright() as pw:
        f = Path(tmp)/'remastered.html'
        f.write_text(html, encoding='utf-8')
        browser = pw.chromium.launch(executable_path=CHROME, headless=True)
        page = browser.new_page(viewport=dict(width=1280, height=720))
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.on('console', lambda c: errors.append(c.text[:300]) if c.type == 'error' and 'Failed to load resource' not in c.text else None)
        page.add_init_script("addEventListener('DOMContentLoaded',()=>{const st=document.createElement('style');st.textContent='#bootcover{display:none!important}*{transition:none!important;animation:none!important}';document.head.append(st)})")
        page.goto(f.as_uri() + '?overlay', wait_until='domcontentloaded')
        for _ in range(2):
            page.evaluate('m=>updateHUD(m)', m)
            page.wait_for_timeout(250)
        page.evaluate("()=>nearCardToggle(true)")
        page.wait_for_timeout(250)
        near = page.evaluate("""()=>[...document.querySelectorAll('#nearcard button[data-do=carrybody]')].map(b=>[b.textContent.trim(),b.dataset.value,b.title])""")
        menus = {}
        for i, n, a in BODIES:
            menus[a] = page.evaluate("""([i,n])=>{try{const T={kind:'body',x:10,y:10,dx:10,dy:10,id:i,name:n+"'s Body"};
              window.v3pickThing=()=>T;window.v3pickTile=()=>({x:10,y:10});window.v3visible=()=>true;window.v3kindAt=()=>null;
              V3.things=[T];v3menuOpen(300,300);const m=document.getElementById('menu3d');
              const r=m?[...m.querySelectorAll('button')].map(b=>b.textContent.replace(/^\\S\\s*/,'').trim()).filter(Boolean):[];v3menuClose();return r}catch(e){return ['ERROR '+e]}}""", [i, n])
        browser.close()
    want_near = [['⇡ Drag', f'{ref}|[0x3000101]', 'Drag the body'], ['⇣ Let go', f'{ref}|[0x3000102]|0', 'Let go'], ['⇡ Carry', f'{ref}|[0x3000103]', 'Carry the body']]
    checks = {
        'near_buttons': [[x[0], x[1]] for x in near] == [[w[0], w[1]] for w in want_near],
        'near_tips': len(near) == 3 and all(x[2].startswith(w[2]) for x, w in zip(near, want_near)),
        'menu_drag': 'Drag body' in menus['dragbody'] and 'Carry the body' not in menus['dragbody'],
        'menu_letgo': 'Let go' in menus['letgo'] and 'Drag body' not in menus['letgo'],
        'menu_carry_off': 'Carry the body' in menus['carrybody'],
        'no_script_errors': not errors,
    }
    print(json.dumps(dict(passed=all(checks.values()), checks=checks, near=near, menus=menus, errors=errors[:5]), indent=1, ensure_ascii=False))
    if not all(checks.values()): sys.exit(1)


if __name__ == '__main__':
    main()
