#!/usr/bin/env python3
"""The rulership pieces of the HUD (Rulership.dm) in the overlay page (headless Chrome, ?overlay), fed a made-up
model: the unit card's Family tab for a ruler (title, regalia, health, what the stage needs), for an heir (the
heir's word and why) and for a unit holding another realm's heir's circlet; the Realm page's Rule box (rulers, a
pressed claim with Yield / Refuse, a claim of ours to press, the heir and the heir's item, the five laws with the
current one pressed); the succession banner when the seat is claimed. updateHUD catches its own throws and logs them,
so console errors count. Stills go to reports/polish-2026-10-22/rulership/.

    python3 tools/check_rulership_hud.py
"""
import copy
import json
from pathlib import Path
import tempfile
from playwright.sync_api import sync_playwright

BASE = Path(__file__).resolve().parents[1]
OUT = BASE/'reports/polish-2026-10-22/rulership'
html = (BASE/'game/Interface/remastered.html').read_text(encoding='utf-8').replace('window.location.href=', 'window.testLastURL=')
base = json.loads((BASE/'tests/idle-model-available.json').read_text())
for x in base['units']: x['selected'] = False

KIN = {'uid': 'u1', 'house': 'Ash', 'color': '#a33', 'generation': 1, 'ruler': 1, 'heir': 0, 'canHeir': 0,
       'parents': [], 'partners': [], 'children': [], 'siblings': []}
SEAT = {'title': 'Lord', 'regalia': 'Elder\'s Staff', 'health': 75, 'legacy': 0,
        'need': 'Your town needs a Lord or Lady: make a Silver Circlet (at a forge from 2 silver ingots and a cut emerald) for Hal to wear. Until then the seat stays a hamlet\'s, at +75 health.'}
LAWS = [{'id': i, 'name': n, 'tip': t} for i, n, t in [
    ('bloodline', 'Bloodline', 'The named heir, else the eldest child, then the eldest sibling, then the eldest of the house.'),
    ('chosen', 'Chosen heir', 'Whoever the ruler names; if no one, the eldest of the house.'),
    ('might', 'Might', 'The strongest grown member of the house (Attack, Strength and Defence).'),
    ('council', 'Council', 'The people choose: the grown unit they like best (mood, family, level).'),
    ('regalia', 'Regalia', 'Whoever holds the realm\'s regalia, the item its last ruler was crowned with: even an enemy.')]]
RULE = {'stage': 'Town', 'item': 'Silver Circlet', 'made': 'at a forge from 2 silver ingots and a cut emerald', 'health': 125,
        'rulers': [{'name': 'Hal', 'title': 'Lord', 'ref': 'r1', 'regalia': 'Elder\'s Staff', 'health': 75, 'legacy': 0, 'need': SEAT['need']}],
        'vacant': 0, 'law': 'bloodline', 'lawSet': 1, 'laws': LAWS, 'lawMood': -10,
        'heir': 'Edric', 'heirWord': 'Prince', 'heirWhy': 'holds the Heir\'s Circlet',
        'heirItem': {'name': 'Heir\'s Circlet', 'where': 'worn by Edric', 'ours': 1},
        'claimOn': None, 'claims': [{'key': 'carol', 'realm': 'Thorn\'s village', 'holder': 'Grak', 'item': 'Heir\'s Band', 'state': 'open', 'mins': 8}]}
CLAIMED = dict(RULE, rulers=[], vacant=1, heir='Edric', heirWhy='eldest child', heirItem={'name': 'Heir\'s Circlet', 'where': 'carried by House Thorn\'s Grak', 'ours': 0},
               claimOn={'by': 'bob', 'house': 'Thorn', 'holderName': 'Grak', 'item': 'Heir\'s Circlet', 'state': 'pressed', 'mins': None}, claims=[])


def model(unit_family=None, tab=None, rule=None, succession=None):
    m = copy.deepcopy(base)
    u = m['units'][0]
    u['selected'] = True
    u['royal'] = bool(unit_family and 'seat' in unit_family.get('rule', {}))
    if unit_family is not None: u['family'] = unit_family
    if tab: m['tab'] = tab
    if rule is not None: m['realm'] = dict(m.get('realm') or {}, rule=rule)
    if succession is not None: m['play'] = dict(m.get('play') or {}, succession=succession)
    return m


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    errors, seen = [], {}
    with tempfile.TemporaryDirectory(prefix='rulership-hud-') as tmp, sync_playwright() as pw:
        page_file = Path(tmp)/'remastered.html'
        page_file.write_text(html, encoding='utf-8')
        browser = pw.chromium.launch(executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless=True)
        page = browser.new_page(viewport=dict(width=1440, height=900))
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.on('console', lambda c: errors.append(c.text[:300]) if c.type == 'error' and 'Failed to load resource' not in c.text else None)
        page.goto(page_file.as_uri() + '?overlay', wait_until='domcontentloaded')

        page.evaluate('()=>{const c=document.getElementById("bootcover");if(c)c.remove()}')

        def feed(m):
            for _ in range(2):
                page.evaluate('m=>updateHUD(m)', m)
                page.wait_for_timeout(250)
            if m.get('tab') not in (None, 'units'):   # a page shows in its panel (as capture_hud.py opens one)
                page.evaluate('()=>document.body.classList.add("panel-open")')
                page.wait_for_timeout(200)

        def family_text():
            b = page.query_selector('#heroframe [data-hftab="family"]')
            if b: b.click()
            page.wait_for_timeout(250)
            return page.evaluate("()=>{const f=document.querySelector('#heroframe');return f?f.innerText:''}")

        # a ruler
        feed(model({'partners': [], 'kin': KIN, 'rule': {'seat': SEAT, 'held': []}}))
        t = family_text()
        seen['ruler_card'] = 'Lord · wears the Elder\'s Staff · +75 health' in t and 'Silver Circlet' in t
        page.screenshot(path=str(OUT/'family-ruler.png'))
        # an heir, holding another realm's circlet too
        kin = dict(KIN, ruler=0, heir=1, canHeir=0)
        feed(model({'partners': [], 'kin': kin, 'rule': {'heir': {'word': 'Prince', 'why': 'holds the Heir\'s Circlet'},
              'canRule': 'To be crowned, needs a Silver Circlet or better (made at a forge from 2 silver ingots and a cut emerald).',
              'held': [{'text': 'Holds House Thorn\'s Heir\'s Band: a claim on its seat if it falls empty.'}]}}))
        t = family_text()
        seen['heir_card'] = 'Prince · heir: holds the Heir\'s Circlet' in t and 'Named heir' not in t and 'House Thorn\'s Heir\'s Band' in t and 'To be crowned' in t
        page.screenshot(path=str(OUT/'family-heir.png'))
        # the Realm page: ruled, with a claim of ours to press
        feed(model(tab='realm', rule=RULE))
        t = page.evaluate("()=>{const b=document.querySelector('#realmBody');return b?b.innerText:''}")
        laws = page.evaluate("()=>[...document.querySelectorAll('#realmBody [data-value^=\"law|\"]')].map(b=>[b.textContent,b.getAttribute('aria-pressed')])")
        press = page.evaluate("()=>!!document.querySelector('#realmBody [data-value=\"claim|carol\"]')")
        seen['realm_rule'] = 'Rule' in t and 'Lord Hal' in t and 'Prince' in t and 'worn by Edric' in t and press
        seen['realm_laws'] = len(laws) == 5 and [l for l in laws if l[1] == 'true'] == [['Bloodline', 'true']]
        box = page.query_selector('#realmBody')
        if box: box.screenshot(path=str(OUT/'realm-rule.png'))
        # the Realm page: our seat claimed and pressed
        feed(model(tab='realm', rule=CLAIMED))
        t = page.evaluate("()=>{const b=document.querySelector('#realmBody');return b?b.innerText:''}")
        yr = page.evaluate("()=>[!!document.querySelector('#realmBody [data-value=\"yield|bob\"]'),!!document.querySelector('#realmBody [data-value=\"refuse|bob\"]')]")
        seen['realm_claimed'] = 'claims your seat' in t and 'The seat is empty' in t and yr == [True, True] and 'take it back' in t
        if box: page.query_selector('#realmBody').screenshot(path=str(OUT/'realm-claimed.png'))
        # the succession banner when the seat is claimed
        ev = {'dead': 'Hal', 'heir': 'r2', 'heirName': 'Edric', 'why': 'eldest child', 'house': 'Ash', 'royal': 1, 'title': 'Lord',
              'claim': 'Grak of House Thorn holds your Heir\'s Circlet and claims your seat.'}
        feed(model(succession=ev))
        b = page.evaluate("()=>{const s=document.querySelector('.succ');return s?[s.innerText,!!s.querySelector('[data-do=\"crownheir\"]'),!!s.querySelector('[data-value=\"realm\"]')]:null}")
        seen['banner_claim'] = bool(b) and 'claims your seat' in b[0] and not b[1] and b[2]
        ev2 = dict(ev, claim=None)
        feed(model(succession=ev2))
        b = page.evaluate("()=>{const s=document.querySelector('.succ');return s?[s.innerText,!!s.querySelector('[data-do=\"crownheir\"]')]:null}")
        seen['banner_crown'] = bool(b) and 'Crown as Lord' in b[0] and b[1]
        browser.close()
    checks = dict(seen, no_script_errors=not errors)
    result = dict(passed=all(checks.values()), checks=checks, errors=errors[:5])
    (BASE/'tests/rulership-hud-checks.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=1))
    raise SystemExit(0 if result['passed'] else 1)


if __name__ == '__main__':
    main()
