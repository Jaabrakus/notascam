#!/usr/bin/env python3
"""Quest maker Q8's HUD (QuestAdaptive.dm; planning/QUEST_MAKER_PLAN_2026-10-31.md section 8) in the overlay page
(headless Chrome, ?overlay): the post form's going-rate hint and standing fields (what they send, reset after), the Ours
list of standing notices (Stop, Open), a board's danger tags and its sort button, a world notice's card (its prize, not
held, no Report), and a fort's report for its maker.

    python3 tools/check_quest_adaptive_hud.py [--page game/Interface/remastered.html] [--shots DIR]"""
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
ING = '/obj/Items/Ingots/IronIngot'
post = {'unit': u['ref'], 'unitName': 'Thorin', 'board': [40, 41, 1], 'carry': [], 'kinds': [[ING, 'IronIngot'], ['/obj/Items/woods/wood', 'Logs']],
        'qualities': [], 'ranks': ['Camp', 'Hamlet'], 'days': [1, 3, 7], 'boards': 1, 'hunt': [], 'plans': [], 'pick': None, 'picked': None,
        'circle': 10, 'placeMax': 12, 'huntMax': 50, 'workMax': 200, 'fortPicked': None, 'fortMax': 48,
        'chain': {'links': [], 'tokens': [['tok-q1', "the hold's seal", 'Ironbrow']]}, 'rates': {ING: [12.5, 4]}}
standing = [{'id': 's1', 'itemName': 'IronIngot', 'keep': 50, 'each': 3, 'have': 41, 'note': 'A notice is up', 'quest': 'q7'}]
page_q = {'taken': [], 'ours': [], 'renown': 0, 'coins': 120, 'open': 0, 'cap': 3, 'rank': 'Hamlet', 'cost': 2, 'logMax': 10, 'post': post, 'standing': standing}
board = {'kind': 'board', 'house': 'Ironbrow', 'own': 0, 'renown': 0, 'unit': None, 'sort': 'new', 'party': 180,
         'rows': [{'id': 'q1', 'title': 'Bring 9 IronIngot', 'mark': '!', 'house': 'Ironbrow', 'reward': '27 coins'},
                  {'id': 'q2', 'title': 'Clear the Dragon’s lair', 'mark': '!', 'house': 'The world', 'reward': 'The lair’s hoard', 'danger': 'Deadly'},
                  {'id': 'q3', 'title': 'Slay the deer', 'mark': '!', 'house': 'The world', 'reward': 'Its antlers', 'danger': 'Easy'}]}
world = {'kind': 'quest', 'id': 'q2', 'title': 'Clear the Dragon’s lair', 'house': 'The world', 'mark': '!', 'state': 'open', 'goal': 'Clear the Dragon’s lair',
         'goalKind': 'clear', 'reward': 'The lair’s hoard (14 pieces of gold, silver and gems)', 'got': None, 'need': 1, 'own': 0, 'mine': None,
         'left': '7 days left', 'takers': 0, 'x': 45, 'y': 45, 'z': 1, 'text': 'A dragon sleeps on its hoard in this lair.', 'renown': 0, 'who': 'Anyone',
         'why': '', 'stats': {'taken': 0, 'done': 0}, 'unit': None, 'report': 0, 'world': 1, 'target': 'At the marker', 'chain': None}
fort = copy.deepcopy(world)
fort.update({'id': 'q9', 'title': 'Storm the east tower', 'house': 'Ironbrow', 'own': 1, 'world': 0, 'report': 0, 'goalKind': 'fort', 'reward': '200 coins',
             'fort': {'lethal': 1, 'captives': 0, 'fee': 0, 'garrison': 6, 'power': 300, 'danger': None, 'party': 0, 'tries': ['a', 'b'], 'won': 1,
                      'report': ['2 tries: 1 won, 1 not. Parties of about 3.5.', 'The way in lost someone in 2 of 2 tries.']}})
errors = []
with tempfile.TemporaryDirectory(prefix='quest-adaptive-hud-') as tmp, sync_playwright() as pw:
    page_file = Path(tmp)/'remastered.html'
    page_file.write_text(html, encoding='utf-8')
    browser = pw.chromium.launch(executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless=True)
    page = browser.new_page(viewport=dict(width=1280, height=800))
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.on('console', lambda c: errors.append(c.text[:300]) if c.type == 'error' and 'Failed to load resource' not in c.text else None)
    page.add_init_script("window.testSent=[];Object.defineProperty(window,'testURL',{set(v){window.testSent.push(String(v))}})")
    page.goto(page_file.as_uri() + '?overlay', wait_until='domcontentloaded')
    if args.shots: args.shots.mkdir(parents=True, exist_ok=True)
    shot = lambda n: args.shots and page.screenshot(path=str(args.shots/f'quest-adaptive-hud-{n}.png'))
    feed = lambda mm: (page.evaluate('m=>updateHUD(m)', mm), page.wait_for_timeout(250))
    sent = lambda: [unquote(s) for s in page.evaluate('()=>window.testSent.splice(0)')]
    seen = {}
    for _ in range(2): feed(m)
    page.evaluate("()=>{const b=document.getElementById('bootcover');if(b)b.remove()}")
    m1 = copy.deepcopy(m); m1['tab'] = 'quests'; m1['quests'] = page_q
    feed(m1)
    page.evaluate("()=>document.body.classList.add('panel-open')")
    page.click('#page-quests [data-questview=ours]')
    feed(m1)
    page.fill('#page-quests .qform [data-q=item]', 'IronIngot')
    seen['rate'] = page.evaluate("()=>document.querySelector('#page-quests [data-qrate]').textContent")
    page.fill('#page-quests .qform [data-q=item]', 'Logs')
    seen['rate_none'] = page.evaluate("()=>document.querySelector('#page-quests [data-qrate]').textContent")
    page.fill('#page-quests .qform [data-q=item]', 'IronIngot')
    page.evaluate("()=>document.querySelector('#page-quests .qstand').open=true")
    page.fill('#page-quests .qform [data-q=keep]', '50')
    page.fill('#page-quests .qform [data-q=each]', '3')
    shot('form')
    sent()
    page.click('#page-quests [data-qsubmit]')
    seen['post'] = sent()
    seen['keep_after'] = page.evaluate("()=>questDraft.keep")
    # a token asked for is never a standing notice
    page.fill('#page-quests .qform [data-q=keep]', '9')
    page.fill('#page-quests .qform [data-q=item]', "Token: the hold's seal (Ironbrow)")
    sent()
    page.click('#page-quests [data-qsubmit]')
    seen['token_post'] = sent()
    # Ours: the standing notices
    m2 = copy.deepcopy(m1); m2['quests']['post'] = None
    feed(m2)
    seen['ours'] = page.evaluate("()=>{const r=[...document.querySelectorAll('#page-quests .qrow')].find(x=>/Keep 50/.test(x.textContent));return r?[r.textContent,[...r.querySelectorAll('button')].map(b=>b.dataset.value)]:null}")
    shot('ours')
    sent()
    page.click('#page-quests [data-value="standingstop|s1"]')
    seen['stop'] = sent()
    page.evaluate("()=>document.body.classList.remove('panel-open')")
    # the board: danger tags, the sort button
    m3 = copy.deepcopy(m); m3['questCard'] = board
    feed(m3)
    shot('board')
    seen['ellipsis'] = page.evaluate("()=>{const s=document.querySelector('#questcard .qc-list small');return s?getComputedStyle(s).textOverflow:null}")
    seen['tags'] = page.evaluate("()=>[...document.querySelectorAll('#questcard .qc-list button')].map(b=>{const t=b.querySelector('.qdg');return t?[t.textContent,t.className]:null})")
    sent()
    page.click('#questcard [data-value="sort|manage"]')
    seen['sort'] = sent()
    m3b = copy.deepcopy(m3); m3b['questCard']['sort'] = 'manage'
    feed(m3b)
    seen['sort_back'] = page.evaluate("()=>!!document.querySelector('#questcard [data-value=\"sort|new\"]')")
    # a world notice's card
    m4 = copy.deepcopy(m); m4['questCard'] = world
    feed(m4)
    shot('world')
    seen['world'] = page.evaluate("()=>{const c=document.getElementById('questcard');return [c.querySelector('dl').textContent,!!c.querySelector('[data-qrep]'),c.querySelector('.qc-t small').textContent]}")
    # a fort's report for its maker
    m5 = copy.deepcopy(m); m5['questCard'] = fort
    feed(m5)
    seen['report'] = page.evaluate("()=>document.querySelector('#questcard dl').textContent")
    browser.close()


def posted(L):
    s = next((x for x in L if 'post|' in x), '')
    return json.loads(s.split('post|', 1)[1]) if s else {}


sp, tp = posted(seen['post']), posted(seen['token_post'])
checks = {
    'going_rate_hint': 'about 12.5 coins each (4 sales)' in seen['rate'] and 'No sales' in seen['rate_none'],
    'standing_sends_keep_and_each': sp.get('keep') == '50' and sp.get('each') == '3' and sp.get('item') == ING,
    'keep_resets_after_post': seen['keep_after'] == '0',
    'token_is_never_standing': tp.get('token') == 'tok-q1' and tp.get('keep') == '0',
    'ours_lists_standing': bool(seen['ours']) and '41 in your stores' in seen['ours'][0] and 'standingstop|s1' in seen['ours'][1] and 'open|q7' in seen['ours'][1],
    'stop_sends': any('standingstop|s1' in x for x in seen['stop']),
    'board_danger_tags': seen['tags'] == [None, ['Deadly', 'qdg qdg-deadly'], ['Easy', 'qdg qdg-easy']],
    'long_row_text_ends_in_an_ellipsis': seen['ellipsis'] == 'ellipsis',
    'board_sort_button': any('sort|manage' in x for x in seen['sort']) and seen['sort_back'],
    'world_card': 'Prize' in seen['world'][0] and 'held until' not in seen['world'][0] and not seen['world'][1] and 'The world' in seen['world'][2],
    'fort_report_for_maker': 'Report' in seen['report'] and 'The way in lost someone in 2 of 2 tries.' in seen['report'],
    'no_script_errors': not errors,
}
result = dict(passed=all(checks.values()), checks=checks, seen=seen, errors=errors[:5])
(BASE/'tests/quest-adaptive-hud-checks.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=1))
raise SystemExit(0 if result['passed'] else 1)
