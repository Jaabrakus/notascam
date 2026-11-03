#!/usr/bin/env python3
"""The admin panel's HUD (Moderation.dm; planning/ADMIN_PANEL_PLAN_2026-10-31.md A1-A2) in the overlay page (headless
Chrome, ?overlay): the Admin button only for the staff, with the open reports' count; its four tabs; an action sends the
reason box with it; the Report buttons on a notice's card and in the near card open the reasons, and a reason is one
send. Reads the console too (updateHUD catches its own errors).

    python3 tools/check_admin_hud.py [--page game/Interface/remastered.html] [--shots DIR]"""
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
u['nearby'] = [{'ref': None, 'id': '[0x3000123]', 'name': '{Ironbrow} Thorin', 'race': 'Dwarf', 'kind': 'another realm', 'dist': 2, 'hp': 100,
                'ko': 0, 'critter': 0, 'acts': ['capture', 'report'], 'uses': None, 'captive': None, 'rope': None}]
quests = [{'id': 'q3', 'title': 'Iron for the forge', 'maker': 'Ironbrow', 'house': 'Ironbrow', 'state': 'open', 'reward': '20 coins',
           'goal': '5 IronIngot', 'takers': 1, 'hidden': False, 'text': 'rude words', 'reports': 2, 'left': '2 days left', 'postban': '',
           'x': 40, 'y': 41, 'z': 1}]
players = [{'key': 'Ironbrow', 'house': 'Ironbrow', 'race': 'Dwarf', 'units': 12, 'online': 1, 'level': '', 'discord': False,
            'muted': None, 'postban': None, 'reports': 2, 'x': 40, 'y': 41, 'z': 1},
           {'key': 'discord-123', 'house': None, 'race': 'Elf', 'units': 3, 'online': 0, 'level': 'mod', 'discord': True,
            'muted': '5 hours left', 'postban': None, 'reports': 0, 'x': None, 'y': None, 'z': None},
           {'key': 'OtherOwner', 'house': None, 'race': 'Human', 'units': 5, 'online': 1, 'level': 'owner', 'discord': False,
            'muted': None, 'postban': None, 'reports': 0, 'x': 9, 'y': 9, 'z': 1}]
reports = [{'id': 'r1', 'at': '2026-10-31 12:00 UTC', 'by': 'Taker', 'byHouse': 'Taker', 'kind': 'quest', 'target': 'Ironbrow', 'reason': 'scam',
            'note': 'it lies', 'copy': {'title': 'Iron for the forge', 'text': 'rude words', 'reward': '20 coins', 'house': 'Ironbrow'}, 'state': 'open'}]
pages = {'quests': {'quests': quests}, 'players': {'players': players},
         'reports': {'reports': reports, 'reasons': {'scam': 'Scam or false notice'}}, 'log': {'log': ['2026-10-31 12:01 UTC | Boss (admin) | muted (1 hour) | Ironbrow | spam']}}
errors = []
with tempfile.TemporaryDirectory(prefix='admin-hud-') as tmp, sync_playwright() as pw:
    page_file = Path(tmp)/'remastered.html'
    page_file.write_text(html, encoding='utf-8')
    browser = pw.chromium.launch(executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless=True)
    page = browser.new_page(viewport=dict(width=1280, height=720))
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.on('console', lambda c: errors.append(c.text[:300]) if c.type == 'error' and 'Failed to load resource' not in c.text else None)
    page.add_init_script("window.testSent=[];Object.defineProperty(window,'testURL',{set(v){window.testSent.push(String(v))}})")
    page.goto(page_file.as_uri() + '?overlay', wait_until='domcontentloaded')
    if args.shots: args.shots.mkdir(parents=True, exist_ok=True)
    shot = lambda n: args.shots and page.screenshot(path=str(args.shots/f'admin-hud-{n}.png'))
    feed = lambda mm: (page.evaluate('m=>updateHUD(m)', mm), page.wait_for_timeout(250))
    sent = lambda: [unquote(s) for s in page.evaluate('()=>window.testSent.splice(0)')]
    seen = {}
    m0 = copy.deepcopy(m); m0['admin'] = None
    for _ in range(2): feed(m0)
    seen['hidden_for_players'] = page.evaluate("()=>document.querySelector('nav [data-value=admin]').hidden")
    m1 = copy.deepcopy(m); m1['tab'] = 'admin'; m1['admin'] = {'level': 'owner', 'open': 1, 'view': 'quests', 'page': pages['quests']}
    feed(m1)
    page.evaluate("()=>document.body.classList.add('panel-open')")
    feed(m1)
    shot('quests')
    seen['button_badge'] = page.evaluate("()=>{const b=document.querySelector('nav [data-value=admin]');return [!b.hidden,b.dataset.badge]}")
    seen['quests_rows'] = page.evaluate("()=>document.querySelectorAll('#adminBody .qrow').length")
    page.fill('#adminWhy', 'scam notice')
    sent()
    page.click('#adminBody button:has-text("Take down")')
    seen['qdown'] = sent()
    seen['views'] = {}
    for v in ('players', 'reports', 'log'):
        mv = copy.deepcopy(m1); mv['admin'] = dict(m1['admin'], view=v, page=pages[v])
        feed(mv)
        shot(v)
        seen['views'][v] = page.evaluate("()=>document.querySelector('#adminBody').textContent.slice(0,200)")
    mv = copy.deepcopy(m1); mv['admin'] = dict(m1['admin'], view='players', page=pages['players'])
    feed(mv)
    sent()
    page.click('#adminBody button:has-text("Mute 1 hour") >> nth=0')
    seen['mute'] = sent()
    sent()
    page.click('#adminBody button:has-text("Ban 1 day") >> nth=0')
    seen['ban'] = sent()
    seen['mod_row_actions'] = page.evaluate("()=>{const r=document.querySelectorAll('#adminBody .qrow')[1];return [...r.querySelectorAll('button')].map(b=>b.textContent)}")
    ma = copy.deepcopy(mv); ma['admin'] = dict(mv['admin'], level='admin')
    feed(ma)
    seen['admin_staff_buttons'] = page.evaluate("()=>[...document.querySelectorAll('#adminBody button')].some(b=>/Make|Remove from staff/.test(b.textContent))")
    feed(mv)
    seen['equal_row_actions'] = page.evaluate("()=>{const r=document.querySelectorAll('#adminBody .qrow')[2];return [...r.querySelectorAll('button')].map(b=>b.textContent)}")
    page.fill('#adminFind', 'discord')
    seen['search'] = page.evaluate("()=>document.querySelectorAll('#adminBody .qrow').length")
    # the Words view (A4): staff see the list; only an Admin adds and takes off
    page.fill('#adminFind', '')
    mw = copy.deepcopy(m1); mw['admin'] = dict(m1['admin'], level='mod', view='words', page={'words': ['heck*', 'darn'], 'max': 300})
    feed(mw)
    seen['words_mod'] = page.evaluate("()=>[document.querySelectorAll('#adminBody .qrow').length,!!document.querySelector('#adminWord'),[...document.querySelectorAll('#adminBody .qrow b')].map(b=>b.textContent)]")
    mw['admin'] = dict(mw['admin'], level='admin')
    feed(mw)
    shot('words')
    page.fill('#adminWhy', 'rude')
    page.fill('#adminWord', 'blast*')
    sent()
    page.click('#adminBody [data-admword]')
    seen['word_add'] = sent()
    page.click('#adminBody button:has-text("Take off") >> nth=0')
    seen['word_del'] = sent()
    # the Report button on a notice's card
    m2 = copy.deepcopy(m); m2['questCard'] = {'kind': 'quest', 'id': 'q3', 'title': 'Iron for the forge', 'house': 'Ironbrow', 'mark': '!', 'state': 'open',
                                             'goal': '5 IronIngot', 'reward': '20 coins', 'need': 5, 'own': 0, 'mine': None, 'left': '2 days left',
                                             'takers': 0, 'x': 40, 'y': 41, 'z': 1, 'text': '', 'renown': 0, 'who': 'Anyone', 'why': '',
                                             'stats': {'taken': 0, 'done': 0}, 'unit': None, 'report': 1}
    page.evaluate("()=>document.body.classList.remove('panel-open')")
    feed(m2)
    page.click('#questcard [data-qrep]')
    seen['card_reasons'] = page.evaluate("()=>[...document.querySelectorAll('#questcard .qrep-row button')].map(b=>b.textContent)")
    shot('report')
    sent()
    page.click('#questcard .qrep-row button:has-text("Scam")')
    seen['card_report'] = sent()
    # the near card's Report
    page.evaluate("()=>nearCardToggle(true)")
    page.wait_for_timeout(200)
    seen['near_report'] = page.evaluate("()=>!!document.querySelector('#nearcard [data-qrep]')")
    page.click('#nearcard [data-qrep]')
    sent()
    page.click('#nearcard .qrep-row button:has-text("Griefing")')
    seen['near_sends'] = sent()
    browser.close()

checks = {
    'admin_button_hidden_for_players': seen['hidden_for_players'] is True,
    'admin_button_and_badge_for_staff': seen['button_badge'] == [True, '1'],
    'quests_tab_rows': seen['quests_rows'] == 1,
    'action_sends_reason': any(s.endswith('rm=admin&value=qdown|q3|scam notice') for s in seen['qdown']),
    'players_tab': 'Ironbrow' in seen['views']['players'],
    'reports_tab': 'Scam or false notice' in seen['views']['reports'],
    'log_tab': 'muted (1 hour)' in seen['views']['log'],
    'ban_sends_with_reason': any('rm=admin&value=ban|Ironbrow|1|scam notice' in x for x in seen['ban']),
    'mute_sends': any('rm=admin&value=mute|Ironbrow|1|' in s for s in seen['mute']),
    'a_lower_rank_can_be_acted_on': 'Unmute' in seen['mod_row_actions'] and 'Remove from staff' in seen['mod_row_actions'],
    'only_the_owner_sees_staff_buttons': seen['admin_staff_buttons'] is False,
    'an_equal_rank_only_go_to_and_message': seen['equal_row_actions'] == ['Go to', 'Message'],
    'search_filters': seen['search'] == 1,
    'words_view_for_staff_sorted': seen['words_mod'][0] == 2 and seen['words_mod'][1] is False and seen['words_mod'][2] == ['darn', 'heck*'],
    'words_admin_adds': any('rm=admin&value=wordadd|blast*|rude' in s for s in seen['word_add']),
    'words_admin_takes_off': any('rm=admin&value=worddel|darn|rude' in s for s in seen['word_del']),
    'card_report_reasons': len(seen['card_reasons']) == 5,
    'card_report_sends': any('rm=report&value=quest|q3|scam' in s for s in seen['card_report']),
    'near_card_report': seen['near_report'] and any('rm=report&value=unit|[0x3000123]|grief' in s for s in seen['near_sends']),
    'no_script_errors': not errors,
}
result = dict(passed=all(checks.values()), checks=checks, seen=seen, errors=errors[:5])
(BASE/'tests/admin-hud-checks.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=1))
raise SystemExit(0 if result['passed'] else 1)
