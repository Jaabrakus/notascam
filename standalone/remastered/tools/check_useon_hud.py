#!/usr/bin/env python3
"""The unit card of a selected unit carrying items (one usable on something, UseOn.dm) beside an Operating table,
in the overlay HUD (headless Chrome, ?overlay). updateHUD catches its own exceptions and logs them, so a throw
leaves a stale card with no page error: this check reads the console too. Checks: the bag bar groups the items and
marks the usable one, the inventory rows carry the use-on flag, and the table box draws."""
import json
from pathlib import Path
import tempfile
from playwright.sync_api import sync_playwright

BASE = Path(__file__).resolve().parents[1]
html = (BASE/'game/Interface/remastered.html').read_text(encoding='utf-8').replace('window.location.href=', 'window.testLastURL=')
m = json.loads((BASE/'tests/idle-model-available.json').read_text())
for x in m['units']: x['selected'] = False
u = m['units'][0]
u['selected'] = True
u['items'] = [{'ref': 'it1', 'name': 'Iron Ingot', 'state': '(Carrying)', 'icon': '', 'info': '', 'useon': 0},
              {'ref': 'it2', 'name': 'Iron Ingot', 'state': '(Carrying)', 'icon': '', 'info': '', 'useon': 0},
              {'ref': 'it3', 'name': 'Soul stone', 'state': '(Carrying)', 'icon': '', 'info': 'A soul stone', 'useon': 1}]
u['table'] = {'own': 1, 'missing': ['leftleg'], 'grafts': [], 'limbs': [], 'body': None, 'doctor': 1,
              'kinds': [{'id': 'automail', 'name': 'Automail', 'ok': 1, 'what': '3 iron ingots, 1 silver ingot, metal crafting 15'}]}
errors = []
with tempfile.TemporaryDirectory(prefix='useon-hud-') as tmp, sync_playwright() as pw:
    page_file = Path(tmp)/'remastered.html'
    page_file.write_text(html, encoding='utf-8')
    browser = pw.chromium.launch(executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless=True)
    page = browser.new_page(viewport=dict(width=1280, height=720))
    page.on('pageerror', lambda e: errors.append(str(e)))
    # the model's portraits are not on disk here: only script errors count
    page.on('console', lambda c: errors.append(c.text[:300]) if c.type == 'error' and 'Failed to load resource' not in c.text else None)
    page.goto(page_file.as_uri() + '?overlay', wait_until='domcontentloaded')
    for _ in range(2):
        page.evaluate('m=>updateHUD(m)', m)
        page.wait_for_timeout(300)
    seen = page.evaluate("""()=>{const t=document.querySelector('#heroframe .tablebox');return {
      table_box:!!t&&t.textContent.includes('Operating table'),
      bag_slots:document.querySelectorAll('#heroframe .bagbar .bagslot').length,
      bag_useon:document.querySelectorAll('#heroframe .bagbar .bagslot[data-useon="1"]').length,
      rows_useon:[...document.querySelectorAll('#units [data-bag]')].filter(e=>e.dataset.useon==='1').length}}""")
    browser.close()
checks = {'table_box': seen['table_box'], 'bag_groups_items': seen['bag_slots'] == 2, 'bag_marks_usable': seen['bag_useon'] == 1,
          'inventory_rows_flag': seen['rows_useon'] == 1, 'no_script_errors': not errors}
result = dict(passed=all(checks.values()), checks=checks, seen=seen, errors=errors[:5])
(BASE/'tests/useon-hud-checks.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=1))
raise SystemExit(0 if result['passed'] else 1)
