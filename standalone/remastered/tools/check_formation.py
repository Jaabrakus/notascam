#!/usr/bin/env python3
"""Run the Remastered formation and helping in a bounded arena.

tests/formation_test.dm (FORM| lines: slots, arrival, one unit, combat on the Company list, zoomed-out 3D), then
tests/formation_feel_test.dm (FF| lines, Formations.dm): six units of mixed races sent across open ground, into a
forest, beside a river, through a doorway, up stairs onto a mountain top; twelve and fifty on open ground; a
Shift-queued leg; attack-move; mixed speeds marching together and two on their own pace; a target against a wall;
a slot taken after the click; line, box and column. Each scenario is judged here: everyone arrives on a slot, nobody
swaps or takes a step after arriving, routes don't cross, arrival spread and detours stay small, the shapes are the
ones asked for, and an order for 50 units stays well under a server tick.
Writes tests/formation-checks.json (tests/<label>-checks.json with --label)."""
import json
import socket
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT.parent/'replica/runtime/macos-x64'   # shared engine, used read-only
EXPECTED = [
    'FORM|slots|distinct=5',
    'FORM|arrived|near=5|distinct_tiles=5|stuck=0',
    'FORM|single|exact=1',
    'FORM|combat|line=1|logged=1',
    'FORM|combat_end|cleared=1|won=1',
    'FORM|zoom|w=101|h=81|fast=1',
    'FORM|complete',
]


def kv(parts):
    out = {}
    for p in parts:
        if '=' in p:
            k, v = p.split('=', 1)
            out[k] = v
    return out


def xy(s):
    return tuple(int(v) for v in s.split(',')) if s and s not in ('none', '-') else None


def judge(text):
    """The FF| scenarios against what a StarCraft-like group move should do: list of (name, ok, detail)."""
    units, groups, facing, times, targets = {}, {}, {}, {}, {}
    for line in re.findall(r'FF\|[^\r\n]*|FFTIME\|[^\r\n]*', text):
        p = line.split('|')
        if p[0] == 'FFTIME':
            d = kv(p[1:])
            times[d.get('n') if p[1] != 'march' else 'march'] = d
        elif len(p) > 2 and p[2] == 'unit':
            d = kv(p[4:]); d['race'] = p[3]
            units.setdefault(p[1], []).append(d)
        elif len(p) > 2 and p[2] == 'group':
            groups[p[1]] = kv(p[3:])
        elif len(p) > 2 and p[2] == 'facing':
            f = p[3].split(','); facing[p[1]] = (float(f[0]), float(f[1])) if len(f) == 2 and f[0] != 'none' else None
            targets[p[1]] = xy(kv(p[4:]).get('target'))
    res = []
    def check(name, ok, detail):
        res.append((name, bool(ok), detail))
    def arrivals(name, key='arrive'):
        return [int(u[key]) for u in units.get(name, []) if u.get(key, '-') not in ('-', '')]
    def kept_shape(name):
        U = units.get(name, [])
        if not U: return False
        v = None
        for u in U:
            s, a = xy(u['start']), xy(u['at'])
            d = (a[0] - s[0], a[1] - s[1])
            if v is None: v = d
            elif d != v: return False
        return True
    scen = ['open', 'forest', 'river', 'doorway', 'mountain', 'open12', 'queued', 'attackmove', 'pace', 'ownpace', 'wall', 'taken', 'line', 'box', 'column', 'custom', 'roles', 'group2', 'facenorth', 'faceeast', 'fifty']
    for name in scen:
        G, U = groups.get(name), units.get(name, [])
        if not G or not U:
            check(f'{name}: ran', False, 'no result')
            continue
        on_final = sum(1 for u in U if xy(u['at']) == xy(u['final_slot']))
        check(f'{name}: everyone ends on a slot of their own', on_final == len(U) and len({u['at'] for u in U}) == len(U), {'on_slot': on_final, 'n': len(U)})
        check(f'{name}: no swaps, no steps after arriving', G['swaps'] == '0' and G['after'] == '0', {'swaps': G['swaps'], 'after': G['after']})
    # spread of arrival (ticks: 10 a second) and detours
    limits = {'open': 5, 'river': 5, 'wall': 5, 'open12': 6, 'attackmove': 5, 'pace': 5, 'taken': 10, 'forest': 20, 'doorway': 30, 'mountain': 30, 'box': 12, 'line': 20, 'fifty': 15}
    for name, lim in limits.items():
        A = arrivals(name, 'arrive') if name not in ('taken',) else None
        if name == 'taken':
            A = [int(u['arrive']) for u in units.get(name, []) if u['arrive'] != '-']
        if A:
            check(f'{name}: they arrive together (spread <= {lim / 10:g} s)', max(A) - min(A) <= lim, {'spread_ticks': max(A) - min(A)})
    for name in ['open', 'forest', 'river', 'doorway', 'open12', 'attackmove', 'pace', 'wall', 'taken', 'line', 'box', 'fifty']:
        G = groups.get(name)
        if G: check(f'{name}: no steps away from the slot (no circling)', int(G['away']) <= (2 if name == 'doorway' else 0), {'away': G['away']})
    for name in ['open', 'forest', 'river', 'doorway', 'open12', 'attackmove', 'wall', 'line', 'box', 'fifty']:
        G = groups.get(name)
        if G: check(f'{name}: no two routes cross', G['cross'] == '0', {'cross': G['cross']})
    for name in ['open', 'river', 'open12', 'attackmove', 'pace', 'fifty', 'doorway', 'wall']:
        check(f"{name}: 'keep' keeps the group's own shape", kept_shape(name), [(u['start'], u['at']) for u in units.get(name, [])][:6])
    # anchored on the click: someone stands on the clicked tile (keep: the one nearest the group's middle; line: the
    # front row's middle; column: its head; box: its middle; your own layout: its gold square), never a ring round it
    for name in scen:
        if name == 'queued' or name not in targets or not units.get(name): continue
        t = targets[name]
        check(f'{name}: a unit stands on the clicked tile', any(xy(u['at'])[:2] == t for u in units[name]), {'target': t, 'at': [u['at'] for u in units[name]][:8]})
    # river: nobody across the water (x >= 60)
    check('river: every slot on the near bank', all(xy(u['at'])[0] < 60 for u in units.get('river', [])), [u['at'] for u in units.get('river', [])])
    # wall: nobody beyond the wall (x >= 75)
    check('wall: the shape slides back from the wall', all(xy(u['at'])[0] < 75 for u in units.get('wall', [])), [u['at'] for u in units.get('wall', [])])
    # shapes: a line across the way they face, a column along it, a box
    def snap(f):
        fx, fy = f
        ax, ay = abs(fx), abs(fy)
        if ax > ay * 2.414: return (1 if fx >= 0 else -1, 0)
        if ay > ax * 2.414: return (0, 1 if fy >= 0 else -1)
        return (1 if fx >= 0 else -1, 1 if fy >= 0 else -1)
    for name, along in (('line', False), ('column', True)):
        U, f = units.get(name, []), facing.get(name)
        if U and f:
            s = snap(f); A = [xy(u['at']) for u in U]
            if along:   # one behind another: all on one line along the facing
                ok = all((a[0] - A[0][0]) * s[1] - (a[1] - A[0][1]) * s[0] == 0 for a in A)
            else:       # side by side: all on one line across it (the same distance along it)
                ok = len({a[0] * s[0] + a[1] * s[1] for a in A}) == 1
            check(f'{name}: {"one behind another" if along else "side by side across the way they go"}', ok, {'facing': f, 'at': A})
    U = units.get('box', [])
    if U:
        A = [xy(u['at']) for u in U]
        w = max(a[0] for a in A) - min(a[0] for a in A) + 1; h = max(a[1] for a in A) - min(a[1] for a in A) + 1
        check('box: a tight block (3 x 2)', sorted((w, h)) == [2, 3], {'w': w, 'h': h})
    # pace: Delays 3-6 arrive together; with the two fastest on their own pace, they get there well before the rest
    own = [int(u['arrive']) for u in units.get('ownpace', []) if u['own'] == '1' and u['arrive'] != '-']
    rest = [int(u['arrive']) for u in units.get('ownpace', []) if u['own'] == '0' and u['arrive'] != '-']
    check('own pace: those two get there before anyone of the group', own and rest and max(own) < min(rest), {'own': own, 'rest': rest})
    check('own pace: the rest still arrive together (within 2.5 s, letting the two past)', rest and max(rest) - min(rest) <= 25, {'rest': rest})
    pd = [int(u['delay']) for u in units.get('pace', [])]
    pa = arrivals('pace')
    check("pace: the group marches at the slowest one's pace", pa and max(pd) * 0.9 * min(int(u['dist']) for u in units['pace']) <= min(pa), {'delays': pd, 'arrive': pa})
    # the old speed (the user, 12:3x): on open ground a Delay-4 group takes about 5 ticks a step (2 tiles a second)
    od = [(int(u['arrive']) - int(u['first_step'] or 0)) / max(1, int(u['steps']) - 1) for u in units.get('open', []) if u['arrive'] != '-']
    check('speed: an ordered move walks at the old 2 tiles a second (about 5 ticks a step)', od and all(4.6 <= t <= 5.6 for t in od), {'ticks_per_step': [round(t, 2) for t in od]})
    # taken: the one whose slot got a crate took the nearest free tile, without circling
    T = units.get('taken', [])
    if T:
        u = T[0]
        s, f = xy(u['slot']), xy(u['final_slot'])
        check('taken: the unit whose slot was taken goes to the next nearest free tile', f and s != f and max(abs(f[0] - s[0]), abs(f[1] - s[1])) <= 2 and u['away'] == '0', u)
    # the player's own layout: the HUD commands keep it (a square out of reach dropped), and a V sent east lands as that
    # V turned to face east (the clicked tile at 0,0, forward up: dx,dy -> x + dy, y - dx)
    g = re.search(r'FF\|custom\|grid\|([^|]*)\|formation=(\w+)\|name=([^|\r\n]*)', text)
    check('custom: the HUD commands save the formation (a square out of reach dropped) and use it', g and g.group(1) == '0,0,any;-1,1,any;1,1,any;-2,2,any;2,2,any;0,-1,any' and g.group(2) == 'custom' and g.group(3) == 'V', g and g.groups())
    lay = [(0, 0), (-1, 1), (1, 1), (-2, 2), (2, 2), (0, -1)]
    want = {(120 + dy, 131 - dx) for dx, dy in lay}
    got = {xy(u['at'])[:2] for u in units.get('custom', [])}
    check('custom: they stand in the layout, turned to face the way they went', got == want, {'got': sorted(got), 'want': sorted(want)})
    # roles: swords to the front squares, bows to the ranged ones, the mage to the mage one (east: dx,dy -> x + dy, y - dx;
    # the layout shifted so its square nearest the clicked tile, front 0,1, is on it)
    lay = [(-1, 1, 'front'), (0, 1, 'front'), (1, 1, 'front'), (-1, -1, 'ranged'), (1, -1, 'ranged'), (0, -1, 'mage')]
    where = {(124 + (dy - 1), 110 - dx): r for dx, dy, r in lay}
    R = units.get('roles', [])
    check('roles: each stands on a square of its own role (swords front, bows back, the mage behind them)', R and all(where.get(xy(u['at'])[:2]) == u['role'] for u in R), {'layout': {f'{k[0]},{k[1]}': v for k, v in where.items()}, 'units': [(u['role'], u['at']) for u in R]})
    m = re.search(r'FF\|roles\|formations\|(\d+)\|mine=(\d+)', text); d = re.search(r'FF\|roles\|after_delete\|(\d+)\|mine=(\d+)\|name=([^\r\n]*)', text)
    check('formations: two saved, the second in use; deleting the first leaves the second, still in use', m and m.groups() == ('2', '2') and d and d.groups() == ('1', '1', 'Archers back'), [m and m.groups(), d and d.groups()])
    # attack box: every foe gets someone, the three archers on three different foes, Attack mode off; when a foe falls
    # nobody stays on it and all six go on to the others; when all fall, all stop
    o = re.search(r'FF\|attackbox\|ordered\|took=(\d+)\|foes_taken=(\d+)\|bow_foes=(\d+)\|mode=(\d+)\|notice=([^\r\n]*)', text)
    check('attack box: the group spreads over the foes, not all on one (all four taken, the three archers on three different ones)', o and o.group(1) == '6' and o.group(2) == '4' and o.group(3) == '3' and o.group(4) == '0' and 'in the box' in o.group(5), o and o.groups())
    f = re.search(r'FF\|attackbox\|after\|still_on_fallen=(\d+)\|retook=(\d+)\|still_attacking=(\d+)', text)
    check('attack box: a fallen foe is left for the next one, and all stop when the box is empty', f and f.groups() == ('0', '6', '0'), f and f.groups())
    r = re.search(r'FF\|rolecheck\|sword_caster=(\w+)\|bare_caster=(\w+)', text)
    check('roles: an enchanted blade (a caster with a sword) is still a fighter; a caster with no weapon is a mage', r and r.groups() == ('front', 'mage'), r and r.groups())
    al = re.search(r'FF\|alike\|targets=(\d+)\|on_archers=(\d+)\|mode=(\d+)\|notice=([^\r\n]*)', text)
    check('A then a click on an enemy archer: the three enemy archers are shared out, the swordsmen left alone', al and al.group(1) == '3' and al.group(2) == '6' and al.group(3) == '0' and 'archers' in al.group(4), al and al.groups())
    pc = re.search(r'FF\|alike\|plain_click_on_one=(\d+)', text)
    check('a plain click on a foe still sends everyone at that one', pc and pc.group(1) == '6', pc and pc.group(1))
    # archers and casters: their own first, then melee (the user: "exhaust all magic and throwable ammo, if none then use melee")
    kt = re.search(r'FF\|ranged\|kit\|v1=([^,]*),(\d+),(\w+)\|v2=([^,]*),(\d+)\|v3=([^,]*),(\w+),(\d+)', text)
    check('ranged kit: an archer (a bow, 2 arrows), one with a bow and no arrows, a staff holder counted a mage', kt and kt.groups() == ('Bow', '2', 'ranged', 'Bow', '0', 'Mace', 'mage', '20'), kt and kt.groups())
    v1 = kv(re.search(r'FF\|ranged\|v1\|([^\r\n]*)', text).group(1).split('|')) if re.search(r'FF\|ranged\|v1\|', text) else {}
    check('an archer shoots its arrows from afar (never beside its foe while it has some)', v1.get('shots') == '2' and v1.get('nearest_with_arrows', '0').isdigit() and int(v1['nearest_with_arrows']) >= 2, v1)
    check('out of arrows, it takes up the sword it carries and goes in to strike', v1.get('holds') == 'Sword' and v1.get('in_at', '-') != '-' and int(v1.get('blows', '0')) >= 1, v1)
    v2 = kv(re.search(r'FF\|ranged\|v2\|([^\r\n]*)', text).group(1).split('|')) if re.search(r'FF\|ranged\|v2\|', text) else {}
    check('a bow and no arrows, nothing else: puts the bow away and goes in with fists (it attacks at once)', v2.get('holds') in ('fists', '0') and v2.get('in_at', '-') != '-' and int(v2.get('blows', '0')) >= 1, v2)
    v3 = kv(re.search(r'FF\|ranged\|v3\|([^\r\n]*)', text).group(1).split('|')) if re.search(r'FF\|ranged\|v3\|', text) else {}
    check('a caster spends its mana from afar (two bone spears), then goes in to strike', v3.get('casts') == '2' and v3.get('nearest_with_mana', '0').isdigit() and int(v3['nearest_with_mana']) >= 2 and v3.get('in_at', '-') != '-' and int(v3.get('blows', '0')) >= 1, v3)
    bb = re.search(r'FF\|ranged\|bowback\|holds=(\w*)\|sword=([^|]*)\|arrows=(\d+)\|role=(\w+)', text)
    check('arrows again: when the fight is over it takes up its bow, the sword back in its pack', bb and bb.groups() == ('Bow', '(Carrying)', '3', 'ranged'), bb and bb.groups())
    cn = re.search(r'FF\|ranged\|corner\|in_sight_at_start=(\d)\|dist=(\d+)\|moved=(\d+)\|cast_at=([^|]*)\|status=([^\r\n]*)', text)
    check('a caster whose foe is in reach but round a wall walks round and casts (not stuck)', cn and cn.group(1) == '0' and int(cn.group(3)) >= 1 and cn.group(4) != '-', cn and cn.groups())
    br = re.search(r'FF\|ranged\|reach\|([0-9,]+)', text)
    check('bow reach: bone 5, wooden 6, metal 7, Dragonbone 7, Elf 7, each one more at Ranged 60', br and br.group(1) == '5,6,6,7,7,8,7,8,7,8', br and br.group(1))
    fg = kv(re.search(r'FF\|fog\|([^\r\n]*)', text).group(1).split('|')) if re.search(r'FF\|fog\|', text) else {}
    check('fog of war: A + a click takes only the foes of that kind you can see (two of three, the third in the fog)', fg.get('seen') == '1,1,0' and fg.get('pool') == '2', fg)
    check('fog of war: when a foe walks off into the fog, those on it go on to the next one they can see', fg.get('on_first', '0') != '0' and fg.get('then_on_second') == '3' and fg.get('stopped') == '0', fg)
    # groups from the Company list (the user: right-click a row, Group; Ctrl+G; Ctrl-click selects whole groups)
    gm = kv(re.search(r'FF\|groups\|make\|([^\r\n]*)', text).group(1).split('|')) if re.search(r'FF\|groups\|make\|', text) else {}
    check('Group: the six selected become group 1 (and are it, as recalled); again says they are already', gm.get('six') == '6' and gm.get('recalled') == '1' and gm.get('again') == '1', gm)
    check('Group with a row right-clicked: two selected and that one make group 2 and leave group 1 (a unit in one group)', gm.get('g1') == '3' and gm.get('g2') == '3' and gm.get('g2_has_third') == '1' and gm.get('apart') == '1', gm)
    gs = kv(re.search(r'FF\|groups\|select\|([^\r\n]*)', text).group(1).split('|')) if re.search(r'FF\|groups\|select\|', text) else {}
    check("a card's click selects its group (as that group); Ctrl-click on another adds it (both, not one group)", gs.get('one') == '3' and gs.get('group') == '1' and gs.get('both') == '6' and gs.get('both_group') == '0' and 'Groups 1 + 2' in gs.get('notice', ''), gs)
    check("the cards' data: each group's members, and the formation chosen while group 1 was selected is group 1's", gs.get('card1') == '3,line' and gs.get('card2') == '3,-', gs)
    ge = kv(re.search(r'FF\|groups\|end\|([^\r\n]*)', text).group(1).split('|')) if re.search(r'FF\|groups\|end\|', text) else {}
    check('take one out, ungroup (its formation goes too), Ctrl+G makes a group of the six (from group 2 too)', ge.get('g2_after_out') == '2' and ge.get('g1_after_ungroup') == '0' and ge.get('g1_formation_cleared') == '1' and ge.get('ctrl_g') == '6' and ge.get('g2_now') == '0', ge)
    gp = re.search(r'FF\|group\|own=(\w+)\|group2=(\w+),(\d+)\|five=(\w+),(\d+)', text)
    check('control group 2 keeps its own formation (a line) while your own stays keep; five of them are not the group', gp and gp.groups() == ('keep', 'line', '2', 'keep', '0'), gp and gp.groups())
    fg = facing.get('group2')
    check("control group 2's move uses its line", re.search(r'FF\|group2\|facing\|[^|]*\|shape=line', text) is not None, fg)
    FN = {xy(u['at'])[:2] for u in units.get('facenorth', [])}
    check('drag to face north, three abreast: a 3 x 2 block facing north, its front row on the clicked tile', FN == {(119, 118), (120, 118), (121, 118), (119, 117), (120, 117), (121, 117)}, sorted(FN))
    FE = {xy(u['at'])[:2] for u in units.get('faceeast', [])}
    check('drag to face east, six wide: a line across, north to south, on the clicked tile', len(FE) == 6 and {x for x, y in FE} == {130} and (130, 112) in FE, sorted(FE))
    # a higher middle on the mountain (block heights): everyone to a slot of its own on the rim, none up on the plateau
    pg = re.search(r'FF\|plateau\|group\|n=(\d+)\|arrived=(\d+)\|onslot=(\d+)', text)
    pp = re.search(r'FF\|plateau\|on_plateau=(\d+)', text)
    check('mountain with a higher middle: each gets to a slot of its own round it (none left "as close as it could")', pg and pg.group(2) == pg.group(1) and pg.group(3) == pg.group(1), pg and pg.groups())
    check('mountain with a higher middle: none up on the plateau (no ramp up it)', pp and pp.group(1) == '0', pp and pp.group(1))
    # mountain: up the stairs, everyone on top
    check('mountain: all up on the mountain top', all(xy(u['at'])[2] == 3 for u in units.get('mountain', [])), [u['at'] for u in units.get('mountain', [])])
    # cost
    t50 = times.get('50', {}); tw = times.get('50 round a wall', {}); tm = times.get('march', {})
    check('cost: one order for 50 units on open ground under 50 ms', t50 and float(t50['order_ms']) < 50, t50)
    check('cost: one order for 50 units round a wall under 60 ms', tw and float(tw['order_ms']) < 60, tw)
    check('cost: the order tick with 50 on the march under 20 ms', tm and float(tm['tick_ms']) < 20, tm)
    return res, {k: v for k, v in times.items()}


def free_port(kind):
    """A port nothing holds now (was a fixed 12185/25635: two runs at once failed, world-look 10-24)."""
    with socket.socket(socket.AF_INET, kind) as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def main():
    # --engine main [--dll D]: the server on the app's runtime (the main engine, its natives), that DLL in a copy of it;
    # --game G: test that game folder instead of game/; --label L: its arena, logs and report named L (default "formation":
    # tests/formation-arena, -compile.log, -server.log, -checks.json), so two runs at once can't share them
    import sys as _sys
    main_engine = '--engine' in _sys.argv and _sys.argv[_sys.argv.index('--engine') + 1] == 'main'
    dll = Path(_sys.argv[_sys.argv.index('--dll') + 1]) if '--dll' in _sys.argv else None
    game = Path(_sys.argv[_sys.argv.index('--game') + 1]) if '--game' in _sys.argv else ROOT/'game'   # --game G: a candidate copy
    label = _sys.argv[_sys.argv.index('--label') + 1] if '--label' in _sys.argv else 'formation'
    arena = ROOT/f'tests/{label}-arena'
    if arena.exists(): shutil.rmtree(arena)
    shutil.copytree(game, arena, ignore=shutil.ignore_patterns('Cave Crawlers.json', '*.dmm', 'ErrorLog.txt'))
    dme = (arena/'Cave Crawlers.dme').read_text(encoding='latin-1')
    dme = re.sub(r'^#include .*\.dmm"\s*$', '', dme, flags=re.M)
    (arena/'formation.dme').write_text(dme + '\n#include "formation_test.dm"\n#include "formation_feel_test.dm"\n', encoding='latin-1')
    world = arena/'Code/World.dm'
    text = world.read_text(encoding='latin-1')
    start = text.index('\tNew()'); end = text.index('\nvar/Season', start)
    world.write_text(text[:start] + '\tNew()\n\t\tspawn(0) FormationRun()\n' + text[end:], encoding='latin-1')
    shutil.copy2(ROOT/'tests/formation_test.dm', arena/'formation_test.dm')
    shutil.copy2(ROOT/'tests/formation_feel_test.dm', arena/'formation_feel_test.dm')
    env = dict(os.environ, DOTNET_ReadyToRun='0')
    dotnet = RUNTIME/'dotnet/dotnet'
    log = ROOT/f'tests/{label}-compile.log'
    with log.open('w') as out:
        subprocess.run([str(dotnet), str(RUNTIME/'compiler/DMCompiler.dll'), str(arena/'formation.dme')], env=env, stdout=out, stderr=subprocess.STDOUT, check=True)
    server_log = ROOT/f'tests/{label}-server.log'
    with tempfile.TemporaryDirectory(prefix='dm-formation-') as data, server_log.open('w') as out:
        srv = RUNTIME
        if main_engine:
            srv = Path(data)/'runtime'
            shutil.copytree(ROOT/'Banners of the Deep.app/Contents/Resources/game/runtime', srv, symlinks=True)
            if dll: shutil.copy2(dll, srv/'server/Resources/Assemblies/OpenDreamRuntime.dll')
        server = subprocess.Popen([str(srv/'dotnet/dotnet'), str(srv/'server/Robust.Server.dll'), '--data-dir', str(Path(data)/'data'),
            '--cvar', f'opendream.json_path={arena/"formation.json"}', '--cvar', f'opendream.topic_port={free_port(socket.SOCK_STREAM)}',
            '--cvar', f'log.path={ROOT/"tests/engine-logs"}', '--cvar', 'net.bindto=127.0.0.1', '--cvar', f'net.port={free_port(socket.SOCK_DGRAM)}', '--cvar', 'status.enabled=false',
            '--cvar', 'hub.advertise=false', '--cvar', 'auth.mode=0', '--cvar', 'game.auto_pause_empty=false'],
            env=env, stdout=out, stderr=subprocess.STDOUT, cwd=arena)
        deadline = time.monotonic() + 900
        while time.monotonic() < deadline and server.poll() is None:
            if 'FORM|complete' in server_log.read_text(errors='replace') or '[ERRO]' in server_log.read_text(errors='replace'): break
            time.sleep(.5)
        if server.poll() is None:
            server.terminate()
            try: server.wait(10)
            except subprocess.TimeoutExpired: server.kill()
    text = server_log.read_text(errors='replace')
    errorlog = arena/'ErrorLog.txt'
    elog = errorlog.read_text(errors='replace') if errorlog.exists() else ''
    actual = re.findall(r'FORM\|[^\r\n]*', text + elog)
    errors = re.findall(r'\[(?:ERRO|FATL)\][^\r\n]*', text) + re.findall(r'runtime error[^\r\n]*', elog + text)
    feel, times = judge(text)
    form_ok = actual == EXPECTED
    result = dict(passed=form_ok and not errors and all(ok for _, ok, _ in feel), expected=EXPECTED, actual=actual, errors=errors,
                  feel=[dict(name=n, ok=o, detail=d) for n, o, d in feel], times=times,
                  shapes=re.findall(r'FF\|[a-z0-9]+\|shape\|[^\r\n]*', text))
    (ROOT/f'tests/{label}-checks.json').write_text(json.dumps(result, indent=2) + '\n')
    for e, a in zip(EXPECTED + [''] * (len(actual) - len(EXPECTED)), actual + [''] * (len(EXPECTED) - len(actual))):
        print(('  ' if e == a else '!!'), a, '' if e == a else f'   (expected {e})')
    for n, o, d in feel:
        print(('  ' if o else '!!'), n, '' if o else '  ' + json.dumps(d)[:300])
    for k, v in times.items(): print('  time', k, v)
    if errors: print('\n'.join(errors[:5]))
    print('passed' if result['passed'] else 'FAILED')
    if not result['passed']: raise SystemExit(1)


if __name__ == '__main__':
    main()
