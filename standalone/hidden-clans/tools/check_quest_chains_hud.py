#!/usr/bin/env python3
"""Quest maker Q6's HUD (QuestChains.dm; planning/QUEST_MAKER_PLAN_2026-10-31.md section 7) in the overlay page (headless
Chrome, ?overlay): the post form's chain fields (comes after, once done or failed, both or either, gives a token, keep it
secret) and what they send; a token in the Bring list sends its id; the card's chain lines (comes after with ticks, asks
for, gives, leads to) and the reason a step isn't open yet.

    python3 tools/check_quest_chains_hud.py [--page game/Interface/remastered.html] [--shots DIR]"""
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
chain = {'links': [['q1', 'Iron for the gate', 'Ironbrow', 'done'], ['q4', 'Gave up?', 'Ironbrow', 'open']],
         'tokens': [['tok-q1', "the hold's seal", 'Ironbrow']]}
post = {'unit': u['ref'], 'unitName': 'Thorin', 'board': [40, 41, 1], 'carry': [{'ref': 'g1', 'name': 'Logs'}],'kinds': [['/obj/Items/Ingots/IronIngot', 'Iron Ingot']],
        'qualities': [], 'ranks': ['Camp', 'Hamlet'], 'days': [1, 3, 7], 'boards': 1, 'hunt': [], 'plans': [], 'pick': None,
        'picked': {'kind': 'place', 'what': 'a spot', 'x': 50, 'y': 20, 'z': 1}, 'circle': 10, 'placeMax': 12, 'huntMax': 50, 'workMax': 200,
        'fortPicked': None, 'fortMax': 48, 'chain': chain}
page_q = {'taken': [], 'ours': [], 'renown': 0, 'coins': 120, 'open': 0, 'cap': 3, 'rank': 'Hamlet', 'cost': 2, 'logMax': 10, 'post': post}
card = {'kind': 'quest', 'id': 'q2', 'title': 'Reach the old hold', 'house': 'Ironbrow', 'mark': '', 'state': 'open', 'goal': 'Reach the old hold',
        'goalKind': 'reach', 'reward': '5 coins', 'got': None, 'need': 1, 'own': 0, 'mine': None, 'left': '3 days left', 'takers': 0,
        'x': 40, 'y': 41, 'z': 1, 'text': '', 'renown': 0, 'who': 'Anyone', 'why': 'Only after doing "Iron for the gate" (Ironbrow).',
        'stats': {'taken': 0, 'done': 0}, 'unit': None, 'report': 1, 'target': 'Secret until the step before is done',
        'chain': {'after': [['Iron for the gate', 'Ironbrow', 'done', False]], 'mode': 'all', 'next': ['Into the keep'], 'token': None, 'wants': None, 'secret': 1}}
errors = []
with tempfile.TemporaryDirectory(prefix='quest-chains-hud-') as tmp, sync_playwright() as pw:
    page_file = Path(tmp)/'remastered.html'
    page_file.write_text(html, encoding='utf-8')
    browser = pw.chromium.launch(executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless=True)
    page = browser.new_page(viewport=dict(width=1280, height=720))
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.on('console', lambda c: errors.append(c.text[:300]) if c.type == 'error' and 'Failed to load resource' not in c.text else None)
    page.add_init_script("window.testSent=[];Object.defineProperty(window,'testURL',{set(v){window.testSent.push(String(v))}})")
    page.goto(page_file.as_uri() + '?overlay', wait_until='domcontentloaded')
    if args.shots: args.shots.mkdir(parents=True, exist_ok=True)
    shot = lambda n: args.shots and page.screenshot(path=str(args.shots/f'quest-chains-hud-{n}.png'))
    feed = lambda mm: (page.evaluate('m=>updateHUD(m)', mm), page.wait_for_timeout(250))
    sent = lambda: [unquote(s) for s in page.evaluate('()=>window.testSent.splice(0)')]
    seen = {}
    for _ in range(2): feed(m)
    m1 = copy.deepcopy(m); m1['tab'] = 'quests'; m1['quests'] = page_q
    feed(m1)
    page.evaluate("()=>document.body.classList.add('panel-open')")
    page.click('#page-quests [data-questview=ours]')
    feed(m1)
    page.select_option('#page-quests .qform [data-q=kind]', 'reach')
    feed(m1)
    page.evaluate("()=>document.querySelector('#page-quests .qchain').open=true")
    seen['fields'] = page.evaluate("()=>['after1','cond1','after2','cond2','afterMode','gives','secret'].map(q=>!!document.querySelector('#page-quests .qchain [data-q='+q+']'))")
    page.select_option('#page-quests .qform [data-q=after1]', 'q1')
    page.select_option('#page-quests .qform [data-q=after2]', 'q4')
    page.select_option('#page-quests .qform [data-q=cond2]', 'failed')
    page.select_option('#page-quests .qform [data-q=afterMode]', 'any')
    page.fill('#page-quests .qform [data-q=gives]', 'the inner key')
    page.check('#page-quests .qform [data-q=secret]')
    page.check('#page-quests .qform [data-qgood=g1]')
    # a ticked box shows its tick (the form's own input rule hid it, q6b)
    seen['ticks'] = page.evaluate("()=>['[data-q=secret]','[data-qgood=g1]'].map(s=>getComputedStyle(document.querySelector('#page-quests .qform '+s)).backgroundImage.includes('svg'))")
    shot('form')
    sent()
    page.click('#page-quests [data-qsubmit]')
    seen['post'] = sent()
    seen['cleared'] = page.evaluate("()=>[questDraft.after1,questDraft.after2,questDraft.gives,questDraft.secret,questDraft.afterMode]")
    # Bring a token: its label in the list, its id sent
    page.select_option('#page-quests .qform [data-q=kind]', 'bring')
    feed(m1)
    seen['token_option'] = page.evaluate("()=>[...document.querySelectorAll('#questKinds option')].map(o=>o.value).filter(v=>v.startsWith('Token:'))")
    page.fill('#page-quests .qform [data-q=item]', "Token: the hold's seal (Ironbrow)")
    sent()
    page.click('#page-quests [data-qsubmit]')
    seen['token_post'] = sent()
    # the card
    page.evaluate("()=>document.body.classList.remove('panel-open')")
    m2 = copy.deepcopy(m); m2['questCard'] = card
    feed(m2)
    shot('card')
    seen['card'] = page.evaluate("()=>{const c=document.querySelector('#questcard');return [c.querySelector('dl').textContent,(c.querySelector('.qc-note.no')||{}).textContent||'']}")
    browser.close()


def posted(L):
    s = next((x for x in L if 'post|' in x), '')
    return json.loads(s.split('post|', 1)[1]) if s else {}


sp, tp = posted(seen['post']), posted(seen['token_post'])
checks = {
    'chain_fields': all(seen['fields']),
    'post_sends_links': sp.get('after') == [['q1', 'done'], ['q4', 'failed']] and sp.get('afterMode') == 'any',
    'post_sends_token_and_secret': sp.get('gives') == 'the inner key' and sp.get('secret') == '1',
    'ticked_boxes_show_ticks': seen['ticks'] == [True, True],
    'chain_fields_cleared_after_post': seen['cleared'] == ['', '', '', '0', 'all'],
    'token_in_bring_list': seen['token_option'] == ["Token: the hold's seal (Ironbrow)"],
    'bring_token_sends_its_id': tp.get('token') == 'tok-q1' and tp.get('item') is None,
    'card_chain_lines': all(w in seen['card'][0] for w in ('Comes after', 'Iron for the gate', 'Leads to', 'Into the keep', 'Secret until')),
    'card_reason': 'Only after doing' in seen['card'][1],
    'no_script_errors': not errors,
}
result = dict(passed=all(checks.values()), checks=checks, seen=seen, errors=errors[:5])
(BASE/'tests/quest-chains-hud-checks.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=1))
raise SystemExit(0 if result['passed'] else 1)
