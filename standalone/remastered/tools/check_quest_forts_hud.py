#!/usr/bin/env python3
"""Quest maker Q5's HUD (QuestForts.dm; planning/QUEST_MAKER_PLAN_2026-10-31.md sections 4-5) in the overlay page
(headless Chrome, ?overlay): the post form's "Storm my fort" (pick the area's corners, the way in, the chest or a
champion; Lethal, captives, the fee) and what it sends; the banner while picking the second corner; the fort's card (the
fight's terms, the garrison, the danger, the tries; Garrison for its maker, Start a try for a taker; a try going on).

    python3 tools/check_quest_forts_hud.py [--page game/Interface/remastered.html] [--shots DIR]"""
import argparse
import copy
import json
import tempfile
from pathlib import Path
from urllib.parse import unquote

from playwright.sync_api import sync_playwright

BASE = Path(__file__).resolve().parents[1]
ap = argparse.ArgumentParser()
ap.add_argument('--page', type=Path, default=BASE/'game/Interface/remastered.html')
ap.add_argument('--shots', type=Path)
args = ap.parse_args()
html = args.page.read_text(encoding='utf-8').replace('window.location.href=', 'window.testURL=')
m = json.loads((BASE/'tests/idle-model-available.json').read_text())
for x in m['units']: x['selected'] = False
u = m['units'][0]
u['selected'] = True
post = {'unit': u['ref'], 'unitName': 'Thorin', 'board': [40, 41, 1], 'carry': [], 'kinds': [['/obj/Items/Ingots/IronIngot', 'Iron Ingot']],
        'qualities': [], 'ranks': ['Camp', 'Hamlet'], 'days': [1, 3, 7], 'boards': 1, 'hunt': [], 'plans': [], 'pick': None, 'picked': None,
        'circle': 10, 'placeMax': 12, 'huntMax': 50, 'workMax': 200, 'fortPicked': None, 'fortMax': 48}
page_q = {'taken': [], 'ours': [], 'renown': 0, 'coins': 120, 'open': 0, 'cap': 3, 'rank': 'Hamlet', 'cost': 2, 'logMax': 10, 'post': post}
fort = {'lethal': 0, 'captives': 0, 'fee': 10, 'garrison': 3, 'power': 210, 'party': 2, 'partyPower': 120, 'danger': 'Hard', 'why': '',
        'goalKind': 'chest', 'champion': None, 'won': 0, 'door': [40, 45, 1], 'site': [40, 40, 50, 50, 1],
        'tries': ['Ironbrow: 2 went in, 1 fell, 0 down, 0 left; the garrison lost 1 of 3 (4 min). Lost: the party is all down, fallen or out.']}
card = {'kind': 'quest', 'id': 'q9', 'title': 'Storm Thorgrim\'s fort', 'house': 'Thorgrim', 'mark': '', 'state': 'open', 'goal': 'Take the chest in Thorgrim\'s fort',
        'goalKind': 'fort', 'reward': '50 coins', 'got': 0, 'need': 1, 'own': 0, 'mine': 'taken', 'left': '2 days left', 'takers': 1,
        'x': 40, 'y': 41, 'z': 1, 'text': '', 'renown': 0, 'who': 'Anyone', 'why': 'You have taken it.', 'stats': {'taken': 1, 'done': 0},
        'unit': None, 'report': 1, 'target': 'At the marker', 'fort': fort}
errors = []
with tempfile.TemporaryDirectory(prefix='quest-forts-hud-') as tmp, sync_playwright() as pw:
    page_file = Path(tmp)/'remastered.html'
    page_file.write_text(html, encoding='utf-8')
    browser = pw.chromium.launch(executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless=True)
    page = browser.new_page(viewport=dict(width=1280, height=720))
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.on('console', lambda c: errors.append(c.text[:300]) if c.type == 'error' and 'Failed to load resource' not in c.text else None)
    page.add_init_script("window.testSent=[];Object.defineProperty(window,'testURL',{set(v){window.testSent.push(String(v))}})")
    page.goto(page_file.as_uri() + '?overlay', wait_until='domcontentloaded')
    if args.shots: args.shots.mkdir(parents=True, exist_ok=True)
    shot = lambda n: args.shots and page.screenshot(path=str(args.shots/f'quest-forts-hud-{n}.png'))
    feed = lambda mm: (page.evaluate('m=>updateHUD(m)', mm), page.wait_for_timeout(250))
    sent = lambda: [unquote(s) for s in page.evaluate('()=>window.testSent.splice(0)')]
    seen = {}
    for _ in range(2): feed(m)
    m1 = copy.deepcopy(m); m1['tab'] = 'quests'; m1['quests'] = page_q
    feed(m1)
    page.evaluate("()=>document.body.classList.add('panel-open')")
    page.click('#page-quests [data-questview=ours]')
    feed(m1)
    page.select_option('#page-quests .qform [data-q=kind]', 'fort')
    feed(m1)
    seen['picks'] = page.evaluate("()=>[...document.querySelectorAll('#page-quests [data-qpick]')].map(b=>b.dataset.qpick)")
    sent()
    page.click('#page-quests [data-qpick=fortarea]')
    seen['pick_area'] = sent()
    # the second corner: the button stays pressed, the banner says which corner
    m2 = copy.deepcopy(m1); m2['questPick'] = 'fortarea2'; m2['quests']['post'] = dict(post, pick='fortarea2')
    feed(m2)
    seen['area2'] = page.evaluate("()=>[document.querySelector('#page-quests [data-qpick=fortarea]').getAttribute('aria-pressed'),(document.querySelector('#build3d')||{}).textContent||'']")
    m3 = copy.deepcopy(m1); m3['questPick'] = None
    m3['quests']['post'] = dict(post, fortPicked={'area': [40, 40, 50, 50, 1], 'door': [40, 45, 1], 'goal': [49, 45, 1]})
    feed(m3)
    shot('form')
    seen['picked'] = page.evaluate("()=>[...document.querySelectorAll('#page-quests .qpicked')].map(e=>e.textContent)")
    page.select_option('#page-quests .qform [data-q=fortGoal]', 'champion')
    feed(m3)
    seen['champ_pick'] = page.evaluate("()=>!!document.querySelector('#page-quests [data-qpick=fortchamp]')&&!document.querySelector('#page-quests [data-qpick=fortgoal]')")
    page.select_option('#page-quests .qform [data-q=fortGoal]', 'chest')
    feed(m3)
    page.select_option('#page-quests .qform [data-q=lethal]', '0')
    page.fill('#page-quests .qform [data-q=fee]', '15')
    sent()
    page.click('#page-quests [data-qsubmit]')
    seen['post'] = sent()
    # the card: a taker with their party at the way in; the maker with people selected; a try going on
    page.evaluate("()=>document.body.classList.remove('panel-open')")
    m4 = copy.deepcopy(m); m4['questCard'] = card
    feed(m4)
    shot('card-taker')
    seen['card'] = page.evaluate("()=>{const c=document.querySelector('#questcard');return [c.querySelector('dl').textContent,[...c.querySelectorAll('.qc-foot button')].map(b=>b.textContent)]}")
    sent()
    page.click('#questcard .qc-foot button:has-text("Start a try")')
    seen['try_sends'] = sent()
    m5 = copy.deepcopy(m4); m5['questCard'] = dict(card, own=1, mine=None, fort=dict(fort, selected=3))
    feed(m5)
    sent()
    page.click('#questcard .qc-foot button:has-text("Garrison")')
    seen['garrison_sends'] = sent()
    m6 = copy.deepcopy(m4); m6['questCard'] = dict(card, fort=dict(fort, **{'try': {'house': 'Ironbrow', 'left': 12.5, 'in': 2, 'went': 3, 'standing': 2, 'mine': 1}}))
    feed(m6)
    shot('card-try')
    seen['try_note'] = page.evaluate("()=>document.querySelector('#questcard').textContent")
    browser.close()

sp = next((json.loads(s.split('post|', 1)[1]) for s in seen['post'] if 'post|' in s), {})
checks = {
    'fort_form_picks': seen['picks'] == ['fortarea', 'fortdoor', 'fortgoal'],
    'pick_area_sends': any('rm=quest&value=pick|fortarea' in s for s in seen['pick_area']),
    'second_corner_pressed_and_banner': seen['area2'][0] == 'true' and 'opposite corner' in seen['area2'][1],
    'picked_lines': len(seen['picked']) == 3 and '11 by 11' in seen['picked'][0],
    'champion_goal_swaps_pick': seen['champ_pick'],
    'post_sends_fort': sp.get('kind') == 'fort' and sp.get('fortGoal') == 'chest' and sp.get('lethal') == '0' and sp.get('fee') == '15',
    'card_terms': all(w in seen['card'][0] for w in ('Non-lethal', 'no captives', '10 coins, kept win or lose', '3 guards', 'Hard', '1 recorded')),
    'card_taker_start': 'Start a try' in seen['card'][1] and not any(t.startswith('Hand in') for t in seen['card'][1]),
    'try_sends': any('rm=quest&value=try|q9' in s for s in seen['try_sends']),
    'garrison_sends': any('rm=quest&value=garrison|q9' in s for s in seen['garrison_sends']),
    'try_note': 'Your try is on: 12.5 min left' in seen['try_note'] and '2 of the garrison standing' in seen['try_note'],
    'no_script_errors': not errors,
}
result = dict(passed=all(checks.values()), checks=checks, seen=seen, errors=errors[:5])
(BASE/'tests/quest-forts-hud-checks.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=1))
raise SystemExit(0 if result['passed'] else 1)
