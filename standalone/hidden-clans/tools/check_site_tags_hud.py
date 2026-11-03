#!/usr/bin/env python3
"""A building site's 3D label (045 siteTags: "Timber house 0 / 20") sits under the HUD's cards and panels, as the food
tags and quest pins do, in the overlay page (headless Chrome, ?overlay): a label under the quest card or the open side
panel doesn't take their clicks; a label nothing covers still does (it opens the site's card in Build); a label stands
over its site under the browser's zoomed HUD (placed as the quest pins are, v3project).

    python3 tools/check_site_tags_hud.py [--page game/Interface/remastered.html] [--shots DIR]"""
import argparse
import copy
import json
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = Path(__file__).resolve().parents[1]
ap = argparse.ArgumentParser()
ap.add_argument('--page', type=Path, default=BASE/'game/Interface/remastered.html')
ap.add_argument('--shots', type=Path)
args = ap.parse_args()
html = args.page.read_text(encoding='utf-8').replace('window.location.href=', 'window.testURL=')
m = json.loads((BASE/'tests/idle-model-available.json').read_text())
card = {'kind': 'quest', 'id': 'q1', 'title': 'Iron for the gate', 'house': 'Ironbrow', 'mark': '', 'state': 'open', 'goal': '1 IronIngot',
        'goalKind': 'bring', 'reward': '30 coins', 'got': None, 'need': 1, 'own': 0, 'mine': None, 'left': '3 days left', 'takers': 0,
        'x': 40, 'y': 41, 'z': 1, 'text': '', 'renown': 0, 'who': 'Anyone', 'why': '', 'stats': {'taken': 0, 'done': 0}, 'unit': None,
        'report': 1, 'target': '', 'chain': None}
page_q = {'taken': [], 'ours': [], 'renown': 0, 'coins': 120, 'open': 0, 'cap': 3, 'rank': 'Hamlet', 'cost': 2, 'logMax': 10, 'post': None}
# One site; the view matrix puts it at (cx, cy) in the 3D view's clip space, whatever its spot. pmSite (the 3D view's
# per-frame site pass) draws the labels; all in one call, so no frame redraws the view in between.
PLACE = """([cx,cy])=>{V3.on=true;V3.z=1;V3.sites=[[0,0,1,0,20,20,10,10,12,12,'Timber house',1,'s',5]];
 V3.vp=[0,0,0,0, 0,0,0,0, 0,0,0,0, cx,cy,0,1];pmSite([]);const t=document.querySelector('#siteTags .sitetag');
 if(!t||t.hidden)return null;const r=t.getBoundingClientRect(),x=r.left+r.width/2,y=r.top+r.height/2,e=document.elementFromPoint(x,y);
 return {x,y,bottom:r.bottom,hit:e?(e.closest('#siteTags')?'label':e.closest('#questcard')?'card':e.closest('main')?'panel':(e.id||e.tagName)):null}}"""
errors = []
with tempfile.TemporaryDirectory(prefix='site-tags-hud-') as tmp, sync_playwright() as pw:
    page_file = Path(tmp)/'remastered.html'
    page_file.write_text(html, encoding='utf-8')
    browser = pw.chromium.launch(executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless=True)
    page = browser.new_page(viewport=dict(width=1280, height=720))
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.on('console', lambda c: errors.append(c.text[:300]) if c.type == 'error' and 'Failed to load resource' not in c.text else None)
    page.add_init_script("window.testSent=[];Object.defineProperty(window,'testURL',{set(v){window.testSent.push(String(v))}})")
    page.goto(page_file.as_uri() + '?overlay', wait_until='domcontentloaded')
    if args.shots: args.shots.mkdir(parents=True, exist_ok=True)
    shot = lambda n: args.shots and page.screenshot(path=str(args.shots/f'site-tags-hud-{n}.png'))
    feed = lambda mm: (page.evaluate('m=>updateHUD(m)', mm), page.wait_for_timeout(250))
    seen = {}
    for _ in range(2): feed(m)
    page.evaluate("()=>{const b=document.getElementById('bootcover');if(b)b.remove()}")   # the loading cover (gone once the world is in)
    seen['open'] = page.evaluate(PLACE, [0, 0])
    # the quest card over the label
    m2 = copy.deepcopy(m); m2['questCard'] = card
    feed(m2)
    seen['card'] = page.evaluate(PLACE, [0, 0])
    shot('card')
    feed(m)
    # the side panel over the label
    m3 = copy.deepcopy(m); m3['tab'] = 'quests'; m3['quests'] = page_q
    feed(m3)
    page.evaluate("()=>document.body.classList.add('panel-open')")
    box = page.evaluate("()=>{const r=document.querySelector('#page-quests').getBoundingClientRect();return [r.left,r.top,r.width,r.height]}")
    cx = ((box[0] + 60) / 1280) * 2 - 1   # its left part: labels near the window's right edge are hidden anyway
    seen['panel'] = page.evaluate(PLACE, [cx, 0])
    shot('panel')
    seen['layer'] = page.evaluate("()=>{const b=document.getElementById('siteTags');return [getComputedStyle(b).zIndex,"
                                  "!!(b.compareDocumentPosition(document.getElementById('questcard'))&Node.DOCUMENT_POSITION_FOLLOWING)]}")
    browser.close()

checks = {
    'label_clicked_when_uncovered': (seen['open'] or {}).get('hit') == 'label',
    'label_over_its_site': bool(seen['open']) and abs(seen['open']['x'] - 640) <= 2 and abs(seen['open']['bottom'] - 360) <= 2,
    'quest_card_over_the_label': (seen['card'] or {}).get('hit') == 'card',
    'side_panel_over_the_label': (seen['panel'] or {}).get('hit') == 'panel',
    'label_layer_under_the_hud': seen['layer'][0] == '0' and seen['layer'][1],
    'no_script_errors': not errors,
}
result = dict(passed=all(checks.values()), checks=checks, seen=seen, errors=errors[:5])
(BASE/'tests/site-tags-hud-checks.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=1))
raise SystemExit(0 if result['passed'] else 1)
