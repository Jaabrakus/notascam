#!/usr/bin/env python3
"""Quest maker Q3's HUD (QuestTargets.dm; planning/QUEST_MAKER_PLAN_2026-10-31.md section 17) in the overlay page
(headless Chrome, ?overlay): the post form's goals (slay, hunt, clear, reach, work) and what they send; picking a
target (the page steps aside with a banner, Esc stops, the page comes back once picked); the world map's markers and
its click while picking; the card of a goal on a target (Where, no Hand in, To the marker); the tracker's distance and
direction; the 3D pins. Reads the console too (updateHUD catches its own errors).

    python3 tools/check_quest_targets_hud.py [--page game/Interface/remastered.html] [--shots DIR]"""
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
u['x'], u['y'], u['z'] = 40, 40, 1
m['x'], m['y'], m['z'] = 40, 40, 1
post = {'unit': u['ref'], 'unitName': 'Thorin', 'board': [40, 41, 1], 'carry': [], 'kinds': [['/obj/Items/Ingots/IronIngot', 'Iron Ingot']],
        'qualities': [], 'ranks': ['Camp', 'Hamlet'], 'days': [1, 3, 7], 'boards': 1,
        'hunt': [['Deer', 'deer'], ['Goblin', 'goblins']], 'plans': [['j4', 'Build 2', 12]], 'pick': None, 'picked': None,
        'circle': 10, 'placeMax': 12, 'huntMax': 50, 'workMax': 200}
page_q = {'taken': [], 'ours': [], 'renown': 0, 'coins': 120, 'open': 0, 'cap': 3, 'rank': 'Hamlet', 'cost': 2, 'logMax': 10, 'post': post}
mark = {'id': 'q7', 'title': 'Slay the Stone Golem', 'kind': 'slay', 'how': 'taken', 'x': 50, 'y': 50, 'z': 1, 'r': 0, 'now': 0,
        'ago': 'last seen 2 hours ago', 'ref': None, 'what': 'the Stone Golem'}
card = {'kind': 'quest', 'id': 'q7', 'title': 'Slay the Stone Golem', 'house': 'Ironbrow', 'mark': '?', 'state': 'open', 'goal': 'Slay the Stone Golem',
        'goalKind': 'slay', 'reward': '200 coins', 'got': 0, 'need': 1, 'own': 0, 'mine': 'taken', 'left': '2 days left', 'takers': 1,
        'x': 40, 'y': 41, 'z': 1, 'text': '', 'renown': 0, 'who': 'Anyone', 'why': 'You have taken it.', 'stats': {'taken': 1, 'done': 0},
        'unit': {'ref': u['ref'], 'name': 'Thorin', 'here': 1, 'carry': 3}, 'report': 1, 'target': 'At the marker, last seen 2 hours ago'}
errors = []
with tempfile.TemporaryDirectory(prefix='quest-targets-hud-') as tmp, sync_playwright() as pw:
    page_file = Path(tmp)/'remastered.html'
    page_file.write_text(html, encoding='utf-8')
    browser = pw.chromium.launch(executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless=True)
    page = browser.new_page(viewport=dict(width=1280, height=720))
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.on('console', lambda c: errors.append(c.text[:300]) if c.type == 'error' and 'Failed to load resource' not in c.text else None)
    page.add_init_script("window.testSent=[];Object.defineProperty(window,'testURL',{set(v){window.testSent.push(String(v))}})")
    page.goto(page_file.as_uri() + '?overlay', wait_until='domcontentloaded')
    if args.shots: args.shots.mkdir(parents=True, exist_ok=True)
    shot = lambda n: args.shots and page.screenshot(path=str(args.shots/f'quest-targets-hud-{n}.png'))
    feed = lambda mm: (page.evaluate('m=>updateHUD(m)', mm), page.wait_for_timeout(250))
    sent = lambda: [unquote(s) for s in page.evaluate('()=>window.testSent.splice(0)')]
    seen = {}
    for _ in range(2): feed(m)
    # the post form: a goal on a target
    m1 = copy.deepcopy(m); m1['tab'] = 'quests'; m1['quests'] = page_q
    feed(m1)
    page.evaluate("()=>document.body.classList.add('panel-open')")
    page.click('#page-quests [data-questview=ours]')
    feed(m1)
    page.select_option('#page-quests .qform [data-q=kind]', 'slay')
    feed(m1)
    shot('slay')
    seen['slay_form'] = page.evaluate("()=>[!!document.querySelector('#page-quests [data-qpick=thing]'),!document.querySelector('#page-quests [data-q=item]')]")
    sent()
    page.click('#page-quests [data-qpick=thing]')
    seen['pick_sends'] = sent()
    # picking: the page steps aside, a banner says what to click; Esc stops
    m2 = copy.deepcopy(m1); m2['questPick'] = 'thing'; m2['quests']['post'] = dict(post, pick='thing')
    feed(m2)
    seen['picking'] = page.evaluate("()=>{const b=document.querySelector('#build3d');return [document.body.classList.contains('panel-open'),!!b&&!b.hidden&&b.textContent]}")
    sent()
    page.keyboard.press('Escape')
    seen['esc_sends'] = sent()
    # picked: the page comes back with it
    m3 = copy.deepcopy(m1); m3['questPick'] = None; m3['quests']['post'] = dict(post, picked={'kind': 'thing', 'what': 'Stone Golem', 'x': 50, 'y': 50, 'z': 1})
    feed(m3)
    shot('picked')
    seen['back'] = page.evaluate("()=>[document.body.classList.contains('panel-open'),document.querySelector('#build3d').hidden,(document.querySelector('#page-quests .qpicked')||{}).textContent||'']")
    page.select_option('#page-quests .qform [data-q=exact]', 'circle')
    sent()
    page.click('#page-quests [data-qsubmit]')
    seen['slay_post'] = sent()
    # hunt and work
    page.select_option('#page-quests .qform [data-q=kind]', 'hunt')
    feed(m3)
    page.select_option('#page-quests .qform [data-q=race]', 'Goblin')
    page.fill('#page-quests .qform [data-q=hunt]', '7')
    sent()
    page.click('#page-quests [data-qsubmit]')
    seen['hunt_post'] = sent()
    page.select_option('#page-quests .qform [data-q=kind]', 'work')
    feed(m3)
    page.select_option('#page-quests .qform [data-q=row]', 'j4')
    sent()
    page.click('#page-quests [data-qsubmit]')
    seen['work_post'] = sent()
    # the card of a goal on a target, the tracker's way there
    page.evaluate("()=>document.body.classList.remove('panel-open')")
    m4 = copy.deepcopy(m); m4['questCard'] = card; m4['questMarks'] = [mark]
    m4['questTrack'] = [{'id': 'q7', 'title': 'Slay the Stone Golem', 'goal': 'Slay the Stone Golem', 'kind': 'slay', 'got': 0, 'need': 1, 'left': '2 days left',
                         'x': 50, 'y': 50, 'z': 1, 'r': 0, 'ago': 'last seen 2 hours ago'}]
    feed(m4)
    shot('card')
    seen['card'] = page.evaluate("()=>{const c=document.querySelector('#questcard');return [c.querySelector('h4').textContent,c.textContent.includes('Where'),c.textContent.includes('At the marker'),[...c.querySelectorAll('.qc-foot button')].map(b=>b.textContent)]}")
    seen['track'] = page.evaluate("()=>document.querySelector('#questtrack').textContent")
    # the 3D pins (the frame calls them; here once by hand)
    seen['pins'] = page.evaluate("()=>{try{questPins3D()}catch(e){return 'error '+e}const b=document.querySelector('#qpins3d');return b?b.children.length:0}")
    # the world map: the marker, and a click while picking
    W = {'z': 1, 'maxx': 200, 'maxy': 200, 'chunks': [[2, 2, ['#556b2f'] * 16]], 'units': [[40, 40]], 'stockpile': None, 'x': 40, 'y': 40,
         'quests': [dict(mark, r=10, how='read')], 'pick': 'place'}
    m5 = copy.deepcopy(m); m5['worldMap'] = W; m5['questPick'] = 'place'
    feed(m5)
    shot('worldmap')
    seen['worldmap_open'] = page.evaluate("()=>!document.querySelector('#worldmap').hidden")
    sent()
    # a click on the tile your people stand on (40,40) must pick that tile, whatever the HUD's zoom (hudKC)
    at = page.evaluate("""()=>{const W=model.worldMap,V=W.view,c=document.getElementById('wmCanvas'),r=c.getBoundingClientRect();
      const fx=(40.5-V.x0)/V.span,fy=1-(40.5-V.y0)/V.span;return [r.left+fx*r.width,r.top+fy*r.height,hudKC()]}""")
    page.mouse.click(at[0], at[1])
    seen['map_click'] = sent()
    seen['map_zoom'] = at[2]
    browser.close()


def posted(L):
    s = next((x for x in L if 'post|' in x), '')
    return json.loads(s.split('post|', 1)[1]) if s else {}


sp, hp, wp = posted(seen['slay_post']), posted(seen['hunt_post']), posted(seen['work_post'])
checks = {
    'slay_form_has_pick_no_item': seen['slay_form'] == [True, True],
    'pick_sends': any('rm=quest&value=pick|thing' in s for s in seen['pick_sends']),
    'picking_steps_aside_with_banner': seen['picking'][0] is False and 'Picking the creature' in str(seen['picking'][1]),
    'esc_stops': any('rm=quest&value=pick|' in s and s.endswith('pick|') for s in seen['esc_sends']),
    'picked_brings_the_page_back': seen['back'][0] is True and seen['back'][1] is True and 'Stone Golem' in seen['back'][2],
    'slay_posts_kind_and_exact': sp.get('kind') == 'slay' and sp.get('exact') == 'circle' and sp.get('item') is None,
    'hunt_posts_race_and_count': hp.get('kind') == 'hunt' and hp.get('race') == 'Goblin' and hp.get('need') == '7',
    'work_posts_the_plan': wp.get('kind') == 'work' and wp.get('row') == 'j4',
    'card_goal_not_bring': seen['card'][0] == 'Slay the Stone Golem',
    'card_where_line': seen['card'][1] and seen['card'][2],
    'card_no_hand_in_but_to_the_marker': not any(t.startswith('Hand in') for t in seen['card'][3]) and 'To the marker' in seen['card'][3],
    'tracker_way_there': '14 tiles NE' in seen['track'] and 'last seen 2 hours ago' in seen['track'],
    'pins_no_error': isinstance(seen['pins'], int),
    'worldmap_open': seen['worldmap_open'],
    'map_click_picks_not_moves': any('rm=quest&value=pickat|' in s for s in seen['map_click']) and not any('rm=camera' in s for s in seen['map_click']),
    'map_click_picks_the_tile_clicked': any(abs(int(s.split('pickat|')[1].split('|')[0]) - 40) <= 1 and abs(int(s.split('pickat|')[1].split('|')[1]) - 40) <= 1 for s in seen['map_click'] if 'pickat|' in s),
    'no_script_errors': not errors,
}
result = dict(passed=all(checks.values()), checks=checks, seen=seen, errors=errors[:5])
(BASE/'tests/quest-targets-hud-checks.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=1))
raise SystemExit(0 if result['passed'] else 1)
