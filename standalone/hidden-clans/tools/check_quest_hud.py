#!/usr/bin/env python3
"""The quest maker's HUD (Quests.dm; planning/QUEST_MAKER_PLAN_2026-10-31.md section 15) in the overlay page (headless
Chrome, ?overlay): the Quests button and page (Taken, Ours, the post form), the card (a board's notices, one notice with
the box the game writes), the tracker, the unit card's board box. updateHUD catches its own exceptions and logs them, so
this reads the console too, and checks what a click sends.

    python3 tools/check_quest_hud.py [--page game/Interface/remastered.html] [--shots DIR]"""
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
u['qboard'] = {'house': 'Ironbrow', 'own': 0, 'n': 2, 'mark': '!'}
row = lambda i, t, mark, **k: dict({'id': i, 'title': t, 'house': 'Ironbrow', 'mark': mark, 'state': 'open', 'goal': '20 Iron Ingot',
                                     'reward': '60 coins, Ruby', 'got': None, 'need': 20, 'own': 0, 'mine': None, 'left': '2 days left',
                                     'takers': 1, 'x': 40, 'y': 41, 'z': 1}, **k)
m['questTrack'] = [{'id': 'q2', 'title': 'Logs for the palisade', 'goal': 'Log', 'got': 12, 'need': 30, 'left': '5 hours left'}]
m['questCard'] = {'kind': 'board', 'house': 'Ironbrow', 'own': 0, 'renown': 3, 'unit': {'ref': u['ref'], 'name': 'Thorin'},
                  'rows': [row('q1', 'Iron for the forge', '!'), row('q2', 'Logs for the palisade', '?', mine='taken', got=12)]}
quest = dict(row('q1', 'Iron for the forge', '!'), kind='quest', text='The forge has gone cold. Bring me iron.', renown=3, who='Anyone',
             why='', stats={'taken': 1, 'done': 0, 'gaveup': 0}, unit={'ref': u['ref'], 'name': 'Thorin', 'here': 1, 'carry': 4})
taken = dict(quest, mine='taken', got=12, mark='?', why='You have taken it.')
page_q = {'taken': [row('q2', 'Logs for the palisade', '?', mine='taken', got=12, goal='30 Log', need=30)],
          'ours': [row('q9', 'Stone for the wall', '', own=1, state='open', takers=0)],
          'renown': 3, 'coins': 120, 'open': 1, 'cap': 3, 'rank': 'Hamlet', 'cost': 2, 'logMax': 10}
post = {'unit': u['ref'], 'unitName': 'Thorin', 'board': [40, 41, 1], 'carry': [{'ref': 'it9', 'name': 'Ruby'}],
        'kinds': [['/obj/Items/Ingots/IronIngot', 'Iron Ingot'], ['/obj/Items/woods/wood', 'Log'], ['/obj/Items/woods/wood/bamboo', 'Log']],
        'qualities': ['Poor Quality', 'Grand Quality'], 'ranks': ['Camp', 'Hamlet', 'Village', 'Town', 'Kingdom'], 'days': [1, 3, 7], 'boards': 1}
errors = []
with tempfile.TemporaryDirectory(prefix='quest-hud-') as tmp, sync_playwright() as pw:
    page_file = Path(tmp)/'remastered.html'
    page_file.write_text(html, encoding='utf-8')
    browser = pw.chromium.launch(executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless=True)
    page = browser.new_page(viewport=dict(width=1280, height=720))
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.on('console', lambda c: errors.append(c.text[:300]) if c.type == 'error' and 'Failed to load resource' not in c.text else None)
    page.add_init_script("window.testSent=[];Object.defineProperty(window,'testURL',{set(v){window.testSent.push(String(v))}})")
    page.goto(page_file.as_uri() + '?overlay', wait_until='domcontentloaded')
    shot = lambda n: args.shots and page.screenshot(path=str(args.shots/f'quest-hud-{n}.png'))
    if args.shots: args.shots.mkdir(parents=True, exist_ok=True)
    feed = lambda mm: (page.evaluate('m=>updateHUD(m)', mm), page.wait_for_timeout(250))
    sent = lambda: [unquote(s) for s in page.evaluate('()=>window.testSent.splice(0)')]
    seen = {}
    for _ in range(2): feed(m)
    shot('board')
    seen['nav_button'] = page.evaluate("()=>!!document.querySelector('nav button[data-value=quests]')")
    seen['board_card'] = page.evaluate("()=>{const c=document.querySelector('#questcard');return !!c&&!c.hidden&&c.textContent.includes('Notice board')&&c.querySelectorAll('.qc-list button').length}")
    seen['board_marks'] = page.evaluate("()=>[...document.querySelectorAll('#questcard .qc-list .qm')].map(e=>e.textContent).join('')")
    seen['tracker'] = page.evaluate("()=>{const t=document.querySelector('#questtrack');return !!t&&!t.hidden&&t.textContent.includes('12/30')}")
    seen['unit_box'] = page.evaluate("()=>{const b=document.querySelector('#heroframe .qboardbox');return !!b&&b.textContent.includes('Notice board')&&b.textContent.includes('one you can take')}")
    sent()
    page.click('#questcard .qc-list button >> nth=0')
    seen['open_sends'] = sent()
    m2 = copy.deepcopy(m); m2['questCard'] = quest
    feed(m2)
    shot('quest')
    seen['quest_card'] = page.evaluate("()=>{const c=document.querySelector('#questcard');return c.textContent.includes('checked by the game')&&c.textContent.includes('The forge has gone cold')}")
    page.click('#questcard .qc-foot button:has-text("Take it")')
    seen['take_sends'] = sent()
    m3 = copy.deepcopy(m); m3['questCard'] = taken
    feed(m3)
    seen['handin_button'] = page.evaluate("()=>[...document.querySelectorAll('#questcard .qc-foot button')].map(b=>b.textContent)")
    page.click('#questcard .qc-foot button:has-text("Hand in")')
    seen['handin_sends'] = sent()
    m4 = copy.deepcopy(m); m4['questCard'] = None; m4['tab'] = 'quests'; m4['quests'] = page_q
    feed(m4)
    page.evaluate("()=>document.body.classList.add('panel-open')")
    feed(m4)
    shot('taken')
    seen['page_taken'] = page.evaluate("()=>{const p=document.querySelector('#page-quests');return !!p&&!p.hidden&&p.textContent.includes('12 of 30')}")
    page.click('#page-quests [data-questview=ours]')
    feed(m4)
    seen['page_ours'] = page.evaluate("()=>document.querySelector('#questBody').textContent.includes('Stone for the wall')")
    m5 = copy.deepcopy(m4); m5['quests'] = dict(page_q, post=post)
    feed(m5)
    shot('post')
    seen['form'] = page.evaluate("()=>!!document.querySelector('#page-quests .qform [data-q=item]')&&document.querySelectorAll('#questKinds option').length")
    page.fill('#page-quests .qform [data-q=item]', 'Iron Ingot')
    page.fill('#page-quests .qform [data-q=need]', '20')
    page.check('#page-quests .qform input[data-qgood="it9"]')
    feed(m5)   # a send while typing must not wipe the form
    seen['form_kept'] = page.evaluate("()=>document.querySelector('#page-quests .qform [data-q=item]').value")
    sent()
    page.click('#page-quests [data-qsubmit]')
    seen['post_sends'] = sent()
    browser.close()

post_sent = next((s for s in seen['post_sends'] if 'post|' in s), '')
post_json = json.loads(post_sent.split('post|', 1)[1]) if post_sent else {}
checks = {
    'nav_button': seen['nav_button'],
    'board_card_lists_notices': seen['board_card'] == 2,
    'board_card_marks': seen['board_marks'] == '!?',
    'tracker_shows_progress': seen['tracker'],
    'unit_card_board_box': seen['unit_box'],
    'click_opens_notice': any('rm=quest' in s and 'open|q1' in s for s in seen['open_sends']),
    'quest_card_game_box': seen['quest_card'],
    'take_sends': any('take|q1|' in s for s in seen['take_sends']),
    'handin_button': any(t.startswith('Hand in') for t in seen['handin_button']),
    'handin_sends': any('handin|q1|' in s for s in seen['handin_sends']),
    'page_taken': seen['page_taken'],
    'page_ours': seen['page_ours'],
    'post_form': bool(seen['form']),
    'post_form_keeps_typing': seen['form_kept'] == 'Iron Ingot',
    'post_sends_json': post_json.get('item') == '/obj/Items/Ingots/IronIngot' and post_json.get('need') == '20' and post_json.get('goods') == ['it9'],
    'no_script_errors': not errors,
}
result = dict(passed=all(checks.values()), checks=checks, seen=seen, errors=errors[:5])
(BASE/'tests/quest-hud-checks.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=1))
raise SystemExit(0 if result['passed'] else 1)
