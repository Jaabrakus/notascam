#!/usr/bin/env python3
"""Quest maker Q7's HUD (QuestKeepers.dm; planning/QUEST_MAKER_PLAN_2026-10-31.md section 15) in the overlay page
(headless Chrome, ?overlay): the unit card's Keeper tab (only on a keeper; job, where it stands, offers, words with its
race's own as placeholders, Ask about; Save, Use default words, Preview), the board and market boxes' "make a keeper",
Talk on the Interact (I) card, the talk card (words, quests with markers, Ask about, Report, Goodbye), the quest card
opened from a keeper (its words, Back), and a keeper's 3D label.

    python3 tools/check_quest_keepers_hud.py [--page game/Interface/remastered.html] [--shots DIR]"""
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
keeper = {'job': 'quest', 'at': '40,41,1', 'boards': [['40,41,1', 'Notice board at 40, 41'], ['60,61,1', 'Notice board at 60, 61']],
          'stalls': [['50,51,1', 'Market stall at 50, 51']], 'offers': [['q1', 'Iron for the gate', 1], ['q2', 'Logs for the palisade', 0]],
          'words': ['Well met, {taker}.', '', '', ''], 'defaults': ['Well met, {taker}. You look like work.', 'Still {left} to go.', 'Good work.', 'Not for your realm.'],
          'topics': [['The tower', 'My grandfather cut it from the hill.']], 'race': 'Dwarf', 'count': 1, 'max': 3, 'lines': 120, 'ask': 40, 'answer': 200, 'topicMax': 3}
talk = {'kind': 'keeper', 'ref': '[0x3000aa]', 'name': 'Thorgrimdrin', 'house': 'Ironbrow', 'job': 'quest', 'race': 'Dwarf', 'attack': 41, 'portrait': '',
        'line': 'Well met, Thorgrim. Bring your best.', 'lineKind': 'Greeting', 'own': 0, 'unit': 'Roven',
        'rows': [{'id': 'q1', 'title': 'Iron for the gate', 'mark': '!', 'tag': '1 iron bar', 'mine': None},
                 {'id': 'q3', 'title': 'Clear the hollow', 'mark': '', 'tag': 'you took this', 'mine': 'taken'}],
        'topics': [['The tower', 'My grandfather cut it from the hill.']]}
qcard = {'kind': 'quest', 'id': 'q1', 'title': 'Iron for the gate', 'house': 'Ironbrow', 'mark': '!', 'state': 'open', 'goal': '1 IronIngot',
         'goalKind': 'bring', 'reward': '30 coins', 'got': None, 'need': 1, 'own': 0, 'mine': None, 'left': '3 days left', 'takers': 0,
         'x': 40, 'y': 41, 'z': 1, 'text': '', 'renown': 0, 'who': 'Anyone', 'why': '', 'stats': {'taken': 0, 'done': 0},
         'unit': {'ref': 'ui-1', 'name': 'Roven', 'here': 1, 'carry': 0}, 'report': 1, 'target': '', 'chain': None,
         'keeper': {'name': 'Thorgrimdrin', 'line': 'Well met, Thorgrim. Bring your best.'}}
errors = []
with tempfile.TemporaryDirectory(prefix='quest-keepers-hud-') as tmp, sync_playwright() as pw:
    page_file = Path(tmp)/'remastered.html'
    page_file.write_text(html, encoding='utf-8')
    browser = pw.chromium.launch(executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless=True)
    page = browser.new_page(viewport=dict(width=1280, height=800))
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.on('console', lambda c: errors.append(c.text[:300]) if c.type == 'error' and 'Failed to load resource' not in c.text else None)
    page.add_init_script("window.testSent=[];Object.defineProperty(window,'testURL',{set(v){window.testSent.push(String(v))}})")
    page.goto(page_file.as_uri() + '?overlay', wait_until='domcontentloaded')
    if args.shots: args.shots.mkdir(parents=True, exist_ok=True)
    shot = lambda n: args.shots and page.screenshot(path=str(args.shots/f'quest-keepers-hud-{n}.png'))
    feed = lambda mm: (page.evaluate('m=>updateHUD(m)', mm), page.wait_for_timeout(250))
    sent = lambda: [unquote(s) for s in page.evaluate('()=>window.testSent.splice(0)')]
    seen = {}
    for _ in range(2): feed(m)
    page.evaluate("()=>{const b=document.getElementById('bootcover');if(b)b.remove()}")
    tab_shown = "()=>{const b=document.querySelector('#heroframe [data-hftab=keeper]');return !!b&&getComputedStyle(b).display!=='none'}"
    seen['tab_on_plain'] = page.evaluate(tab_shown)
    # the board and market boxes: make a keeper
    m1 = copy.deepcopy(m); u1 = m1['units'][0]
    u1['qboard'] = {'house': 'Ironbrow', 'own': 1, 'n': 2, 'mark': ''}
    u1['market'] = {'own': 1, 'seller': 'Ironbrow', 'merchant': None, 'wares': [], 'coins': 120, 'markup': 100}
    u1['keeperMake'] = {'quest': 1, 'stall': 1, 'left': 2, 'max': 3}
    feed(m1)
    page.evaluate("()=>{const b=document.querySelector('#heroframe [data-hftab=overview]');if(b)b.click()}")
    feed(m1)
    seen['make_buttons'] = page.evaluate("()=>[...document.querySelectorAll('#heroframe [data-value^=\"keepermake|\"]')].map(b=>b.dataset.value)")
    sent()
    page.click('#heroframe [data-value$="|quest"][data-value^="keepermake|"]')
    seen['make_sent'] = sent()
    # a keeper: its tab
    m2 = copy.deepcopy(m); m2['units'][0]['keeper'] = keeper
    feed(m2)
    seen['tab_on_keeper'] = page.evaluate(tab_shown)
    page.click('#heroframe [data-hftab=keeper]')
    feed(m2)
    seen['pane'] = page.evaluate("""()=>{const f=document.querySelector('#heroframe .qk-tab');if(!f)return null;const g=k=>f.querySelector('[data-k='+k+']');
      return {at:g('at').value,offers:[...f.querySelectorAll('[data-k=offer]')].map(o=>o.checked),w0:g('w0').value,w1:g('w1').value,w1ph:g('w1').placeholder,q0:g('q0').value,a0:g('a0').value,visible:getComputedStyle(f.closest('[data-pane]')).display!=='none'}}""")
    shot('tab')
    page.fill('#heroframe .qk-tab [data-k=w1]', 'Still {left}. The forge waits.')
    page.check('#heroframe .qk-tab [data-k=offer][value=q2]')
    page.fill('#heroframe .qk-tab [data-k=q1]', 'The gold')
    page.fill('#heroframe .qk-tab [data-k=a1]', 'Held in the chest until it closes.')
    sent()
    page.click('#heroframe [data-qk=save]')
    seen['save'] = sent()
    page.click('#heroframe [data-qk=defaults]')
    seen['defaults'] = page.evaluate("()=>[0,1,2,3].map(i=>document.querySelector('#heroframe .qk-tab [data-k=w'+i+']').value)")
    page.click('#heroframe [data-qk=preview]')
    seen['preview'] = sent()
    page.select_option('#heroframe .qk-tab [data-k=job]', 'stall')
    seen['stall_places'] = page.evaluate("()=>[...document.querySelectorAll('#heroframe .qk-tab [data-k=at] option')].map(o=>o.value)")
    # not a keeper any more: the tab goes, the card falls back to Overview
    feed(m)
    seen['after'] = page.evaluate("()=>[document.getElementById('heroframe').dataset.tab,("+tab_shown+")()]")
    # Talk on the Interact card
    m3 = copy.deepcopy(m); m3['units'][0]['nearby'] = [{'ref': None, 'id': '[0x3000aa]', 'name': 'Thorgrimdrin', 'race': 'Dwarf', 'kind': 'another realm', 'dist': 2, 'hp': 100, 'ko': 0, 'critter': False, 'acts': ['talk', 'report'], 'uses': None}]
    feed(m3)
    page.evaluate("()=>nearCardToggle(true)")
    feed(m3)
    sent()
    seen['talk_btn'] = page.evaluate("()=>{const b=document.querySelector('#nearcard [data-value^=\"keeper|\"]');if(b)b.click();return !!b}")
    seen['talk_sent'] = sent()
    page.evaluate("()=>nearCardToggle(false)")
    # the talk card
    m4 = copy.deepcopy(m); m4['questCard'] = talk
    feed(m4)
    shot('talk')
    seen['talk'] = page.evaluate("""()=>{const c=document.getElementById('questcard');return {name:c.querySelector('.qk-name').textContent,says:c.querySelector('[data-qk-says]').textContent,
      rows:[...c.querySelectorAll('.qc-list button')].map(b=>[b.querySelector('.qm').textContent,b.dataset.value]),report:!!c.querySelector('[data-qrep^="unit|"]'),bye:[...c.querySelectorAll('.qc-foot button')].some(b=>b.textContent==='Goodbye')}}""")
    page.click('#questcard [data-qk-ask]')
    page.click('#questcard [data-qk-topic="0"]')
    seen['answer'] = page.evaluate("()=>document.querySelector('#questcard [data-qk-says]').textContent")
    sent()
    page.click('#questcard [data-value="keeperq|q1"]')
    seen['row_sent'] = sent()
    # the quest card opened from it
    m5 = copy.deepcopy(m); m5['questCard'] = qcard
    feed(m5)
    shot('quest')
    seen['strip'] = page.evaluate("()=>[...document.querySelectorAll('#questcard .qc-says')].map(e=>e.textContent)")
    sent()
    page.click('#questcard [data-value="keeperback"]')
    seen['back_sent'] = sent()
    # its label in 3D
    seen['label'] = page.evaluate("""()=>{try{v3foodTags([{x:5,y:5,kind:'player',qkeeper:{m:'!',n:'Thorgrimdrin',j:'quest giver'}}])}catch(e){return 'error: '+e}
      const s=document.querySelector('#food3d span');return s?[s.textContent,s.className]:null}""")
    browser.close()


def save_json(L):
    s = next((x for x in L if 'keepersave|' in x), '')
    return json.loads(s.split('|', 2)[2]) if s.count('|') >= 2 else {}


sv = save_json(seen['save'])
checks = {
    'tab_hidden_on_a_plain_unit': seen['tab_on_plain'] is False,
    'make_buttons_by_own_board_and_stall': sorted(seen['make_buttons']) == sorted([f"keepermake|{u['ref']}|quest", f"keepermake|{u['ref']}|stall"]),
    'make_sends': any(f"keepermake|{u['ref']}|quest" in x for x in seen['make_sent']),
    'tab_shown_on_a_keeper': seen['tab_on_keeper'] is True,
    'pane_fields': bool(seen['pane']) and seen['pane']['visible'] and seen['pane']['at'] == '40,41,1' and seen['pane']['offers'] == [True, False]
                   and seen['pane']['w0'] == 'Well met, {taker}.' and seen['pane']['w1'] == '' and seen['pane']['w1ph'] == 'Still {left} to go.'
                   and seen['pane']['q0'] == 'The tower',
    'save_sends_words_offers_topics': sv.get('job') == 'quest' and sv.get('at') == '40,41,1' and sv.get('all') == 1 and sv.get('offers') == ['q1', 'q2']
                   and sv.get('words', [None, None])[1] == 'Still {left}. The forge waits.' and sv.get('topics') == [['The tower', 'My grandfather cut it from the hill.'], ['The gold', 'Held in the chest until it closes.']],
    'default_words_empty_the_lines': seen['defaults'] == ['', '', '', ''],
    'preview_sends': any(f"keeperpreview|{u['ref']}" in x for x in seen['preview']),
    'job_switch_lists_stalls': seen['stall_places'] == ['50,51,1'],
    'not_a_keeper_back_to_overview': seen['after'] == ['overview', False],
    'interact_card_talk': seen['talk_btn'] and any('keeper|[0x3000aa]' in x for x in seen['talk_sent']),
    'talk_card': seen['talk']['name'] == 'Thorgrimdrin' and 'Well met, Thorgrim' in seen['talk']['says'] and seen['talk']['rows'] == [['!', 'keeperq|q1'], ['…', 'keeperq|q3']]
                 and seen['talk']['report'] and seen['talk']['bye'],
    'ask_about_answers': 'grandfather' in seen['answer'],
    'row_opens_its_quest': any('keeperq|q1' in x for x in seen['row_sent']),
    'quest_card_keeper_strip_and_back': any('Bring your best' in s and 'Thorgrimdrin' in s for s in seen['strip']) and any('keeperback' in x for x in seen['back_sent']),
    'label_in_3d': isinstance(seen['label'], list) and seen['label'][0] == '! Thorgrimdrin · quest giver' and seen['label'][1] == 'qmark',
    'no_script_errors': not errors,
}
result = dict(passed=all(checks.values()), checks=checks, seen=seen, errors=errors[:5])
(BASE/'tests/quest-keepers-hud-checks.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=1))
raise SystemExit(0 if result['passed'] else 1)
