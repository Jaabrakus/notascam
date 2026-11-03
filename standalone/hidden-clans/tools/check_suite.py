#!/usr/bin/env python3
"""The one test suite every landing passes (the clean-up pass, 2026-10-25, step 5).

    python3 tools/check_suite.py --who <you>          QUICK tier (arena and headless only, up to 3 at once)
    python3 tools/check_suite.py --tier full          QUICK, then one at a time: combat's full-world soak, check_app, launch
    python3 tools/check_suite.py --only clip,obey     just those (names from the table below)
    python3 tools/check_suite.py --jobs 1             one check at a time
    python3 tools/check_suite.py --set-baseline       also record this run as the baseline (tests/suite-baseline.json)

Each check runs through its OWN tools/runlock.py call (never a chain inside one hold): arena and headless checks as
--kind run, up to --jobs of them at once (the two long ones first; buildings alone after them, see SOLO), the
real-window ones as input, after them and one at a time. Every check gets its own free port and files named after the run (tests/suite-<label>-...), so two
copies of the suite, or checks side by side, never share one; the arenas it made are removed afterwards.
A check passes when it exits 0 with nothing failing, or when what fails is exactly what tools/check_suite_known.json
lists for it (each with its reason). Anything else is FAIL. Results: tests/suite-<label>.json and .md (check, tier,
result, detail, its baseline, time and time queued); logs in tests/suite-<label>/. It changes nothing in game/ or
engine/; checks that need a frozen copy take one themselves."""
import argparse
from concurrent.futures import ThreadPoolExecutor, FIRST_COMPLETED, wait
import json
from pathlib import Path
import random
import re
import shutil
import socket
import subprocess
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT/'tests'
KNOWN = ROOT/'tools/check_suite_known.json'
BASELINE = TESTS/'suite-baseline.json'
PY = sys.executable
LONG = ('formation', 'walk_latency')   # started first, side by side
# Run alone, with none of the suite's other checks beside it: buildings' dwarven hall is built by workers the settlement
# pass steps in slices timed in real ms (Jobs.dm), so beside two other arenas it gets fewer steps into its fixed 15,000
# ticks and the hall isn't done (33/39, 10-25 15:52; passes alone). Until jobs' J2 (the settlement pass on the unit clock).
SOLO = ('buildings',)

# name, tier, kind, command, results file in tests/ ('' = judge by exit code and output), timeout (s), needs.
# {R} is this run's file prefix (suite-<label>), {P} a free port (net.port; P + 13500 free too for the topic port).
CHECKS = [
    ('compile', 'quick', 'run', [PY, 'tools/rts_feel/compile_check.py'], '', 300, None),
    ('jscheck', 'quick', 'run', [PY, 'tools/rts_feel/check_scripts.py'], '', 120, None),
    ('hudjoin', 'quick', 'run', [PY, 'art/hud/hud.py', 'status'], '', 60, None),   # the HUD page == the join of art/hud/src
    ('make_chat', 'quick', 'run', [PY, 'reports/server-cost/staged/chat/make_chat.py', 'check', 'game', 'game/Code/Remastered/Chat.dm'], '', 120, None),
    ('settings', 'quick', 'run', [PY, 'reports/polish-2026-10-22/hud-craft/settings_persist_check.py'], '', 300, None),
    ('clip', 'quick', 'run', [PY, 'tools/check_clip.py', '--port', '{P}', '--report', '{R}-clip-checks.json'], '{R}-clip-checks.json', 900, None),
    ('obey', 'quick', 'run', [PY, 'tools/check_obey.py', '--report', '{R}-obey-checks.json'], '{R}-obey-checks.json', 1200, None),
    ('formation', 'quick', 'run', [PY, 'tools/check_formation.py', '--label', '{R}-formation'], '{R}-formation-checks.json', 1200, None),
    ('walk_latency', 'quick', 'run', [PY, 'tools/check_arena.py', '--test', 'tests/walk_latency_check.dm', '--entry', 'WlRun',
                                      '--report', '{R}-walk-latency-checks.json', '--port', '{P}', '--timeout', '900'], '{R}-walk-latency-checks.json', 1000, None),
    # 3D sends only what changed (world-look): the arena's scene steps, then the page puts its chunks back together and
    # must equal one whole build at every step (headless Chrome). Two calls: the page check reads the arena's server log.
    ('delta3d', 'quick', 'run', [PY, 'tools/check_arena.py', '--test', 'reports/world-look/rmver/fixtures/delta3d_check_current.dm', '--entry', 'DlRun',
                                 '--report', '{R}-delta3d.json', '--port', '{P}'], '{R}-delta3d.json', 900, None),
    ('delta3d_page', 'quick', 'run', [PY, 'reports/world-look/rmver/fixtures/check_delta3d.py', 'tests/{R}-delta3d-server.log',
                                      'game/Interface/remastered.html'], '', 600, 'delta3d'),
    ('buildings', 'quick', 'run', [PY, 'tools/check_buildings.py', '--label', '{R}-buildings'], '{R}-buildings-checks.json', 1200, None),
    ('food', 'quick', 'run', [PY, 'tools/check_food.py', '--label', '{R}-food'], '{R}-food-checks.json', 900, None),
    ('stumps', 'quick', 'run', [PY, 'tools/check_stumps.py', '--label', '{R}-stumps'], '{R}-stumps-checks.json', 900, None),
    # combat: the arena's lifetime checks (COMBAT|PASS lines); the full-world soak (the real map, ~3 GB) only in the full tier
    ('combat', 'quick', 'run', [PY, 'tools/check_combat.py', '--ticks', '0', '--label', '{R}-combat'], '{R}-combat-checks.json', 900, None),
    ('combat_soak', 'full', 'run', [PY, 'tools/check_combat.py', '--label', '{R}-combatsoak'], '{R}-combatsoak-soak-checks.json', 2400, None),
    ('app', 'full', 'input', [PY, 'tools/check_app.py', '--native-panels', '--label', '{R}-app'], '{R}-app-checks.json', 2400, None),
    ('launch', 'full', 'input', [PY, 'reports/coordinator/post_build_check.py'], '', 600, None),
]
ARENAS = {'formation': '{R}-formation-arena', 'buildings': '{R}-buildings-arena', 'food': '{R}-food-arena', 'stumps': '{R}-stumps-arena'}

PORTS = set()
PORT_LOCK = threading.Lock()


def free_port():
    """A UDP port P with TCP P + 13500 free too (net.port and opendream.topic_port), none handed out twice here."""
    def free(p, kind):
        with socket.socket(socket.AF_INET, kind) as s:
            try:
                s.bind(('127.0.0.1', p))
                return True
            except OSError:
                return False
    with PORT_LOCK:
        for _ in range(500):
            p = random.randrange(20000, 50000)
            if p not in PORTS and free(p, socket.SOCK_DGRAM) and free(p + 13500, socket.SOCK_STREAM):
                PORTS.add(p)
                return p
    raise RuntimeError('no free port')


def failures(name, rc, out, path, started):
    """(failing case names, how many cases) from a check's results file or output."""
    if name == 'jscheck':
        rows = re.findall(r'^\d+ \d+ (.*)$', out, flags=re.M)
        return [f'block {i}' for i, r in enumerate(rows) if r.strip() != 'ok'], len(rows)
    if name == 'settings':   # PASS / FAIL lines, then ALL PASS
        rows = re.findall(r'^(PASS|FAIL) (.*)$', out, flags=re.M)
        return [r[1][:60] for r in rows if r[0] == 'FAIL'] + ([f'exit {rc}'] if rc and not any(r[0] == 'FAIL' for r in rows) else []), len(rows)
    if name == 'delta3d_page':   # a row per step, then PASS / FAIL
        steps = len(re.findall(r'^.*\{"terrain"', out, flags=re.M))
        ok = rc == 0 and re.search(r'^PASS', out, flags=re.M) is not None
        diff = [l.split()[0] for l in out.splitlines() if 'DIFF' in l][:6]
        return ([] if ok else (diff or [f'exit {rc}'])), max(1, steps)
    if name == 'compile':
        m = re.search(r'Compilation succeeded with (\d+) warnings', out)
        return ([] if rc == 0 and m else [f'exit {rc}']), 1
    if name == 'launch':
        objs = re.findall(r'^\{.*?^\}', out, flags=re.M | re.S)
        try:
            res = json.loads(objs[-1])
        except (IndexError, ValueError):
            return [f'exit {rc}'] if rc else [], 0
        keys = ('client_reached_game', 'got_ready', 'got_3d', 'ready_first', 'hud_models')
        bad = [k for k in keys if not res.get(k)] + (['runtime_errors'] if res.get('runtime_errors') else []) + (['hudpack_failed'] if res.get('hudpack_failed') else [])
        if not res.get('passed') and not bad: bad = ['not passed']
        return bad, len(keys) + 2
    if path and path.exists() and path.stat().st_mtime >= started:
        d = json.loads(path.read_text())
        if name == 'app':
            phases = d.get('phases', {})
            bad = [f'{k}: {x}' for k, p in phases.items() for x in ('client_in_game', 'saved_units_alive') if not p.get(x)]
            bad += [f'{k}: runtime errors' for k, p in phases.items() if p.get('game_runtime_errors')]
            if not d.get('normal_saves_unchanged'): bad.append('normal saves changed')
            if not d.get('passed') and not bad: bad.append('not passed')
            return bad, 2 * len(phases) + 1
        obs = d.get('observations')
        if isinstance(obs, list) and any(re.match(r'COMBAT\|(PASS|FAIL)\|', o) for o in obs):   # check_combat's arena
            rows = [o for o in obs if re.match(r'COMBAT\|(PASS|FAIL)\|', o)]
            bad = [o.split('|')[2] for o in rows if o.startswith('COMBAT|FAIL|')] + ([] if d.get('passed') else ['not passed'] if not any(o.startswith('COMBAT|FAIL|') for o in rows) else [])
            return bad + [f"{len(d['errors'])} runtime errors"] * bool(d.get('errors')), len(rows)
        checks = d.get('checks')
        if isinstance(checks, list) and checks and isinstance(checks[0], dict):
            return [c.get('name', '?') for c in checks if not c.get('ok')], len(checks)
        if isinstance(checks, dict) and checks:
            return [k for k, v in checks.items() if not v], len(checks)
        if 'expected' in d and 'actual' in d:
            got = set(d['actual'])
            bad = ['|'.join(e.split('|')[:2]) for e in d['expected'] if e not in got]
            if d.get('errors'): bad.append(f"{len(d['errors'])} runtime errors")
            if d.get('timed_out'): bad.append('timed out')
            return bad, len(d['expected'])
        return ([] if d.get('passed') else ['not passed']), 1
    if path: return [f'exit {rc}' if rc else 'no results file'], 1
    return ([f'exit {rc}'] if rc else []), 1


def verdict(name, rc, bad, known):
    k = set(known.get(name, {}).get('failures', []))
    if rc == 'timeout': return 'FAIL', 'timed out'
    if not bad and rc == 0: return 'pass', ''
    if bad and set(bad) <= k and rc in (0, 1):
        fixed = k - set(bad)
        return 'pass', f'{len(bad)} known' + (f', {len(fixed)} known now passing: {", ".join(sorted(fixed))}' if fixed else '')
    new = [b for b in bad if b not in k]
    return 'FAIL', ('new: ' + ', '.join(new[:6])) if new else f'exit {rc}'


def run_check(c, tag, who, logs, known, base):
    name, tier, kind, cmd, res_file, timeout, _ = c
    port = free_port() if any('{P}' in a for a in cmd) else None
    cmd = [a.replace('{R}', tag).replace('{P}', str(port)) for a in cmd]
    log = logs/f'{name}.log'
    # the check itself, exec'd from a one-line shell that first marks when the lock let it start (still one command)
    lock = [PY, 'tools/runlock.py', '--who', who, '--kind', kind, '--', '/bin/zsh', '-c', 'print -r -- "SUITE_START $(date +%s)"; exec "$@"', 'suite'] + cmd
    print(f'{time.strftime("%H:%M:%S")} {name} queued', flush=True)
    t0 = time.time()
    with log.open('w') as f:
        try:
            rc = subprocess.run(lock, cwd=ROOT, stdout=f, stderr=subprocess.STDOUT, timeout=timeout + 3600).returncode   # + time in the queue
        except subprocess.TimeoutExpired:
            rc = 'timeout'
    t1 = time.time()
    out = log.read_text(errors='replace')
    m = re.search(r'^SUITE_START (\d+)$', out, flags=re.M)
    start = int(m.group(1)) if m else t0
    path = TESTS/res_file.replace('{R}', tag) if res_file else None
    bad, total = failures(name, rc, out, path, t0)
    result, note = verdict(name, rc, bad, known)
    detail = f'{total - len(bad)}/{total}' if total > 1 else ('ok' if not bad else ', '.join(bad[:4]))
    if note: detail += f' ({note})'
    if name in ARENAS: shutil.rmtree(TESTS/ARENAS[name].replace('{R}', tag), ignore_errors=True)
    b = base.get(name)
    seconds, waited = round(t1 - start), round(max(0, start - t0))
    print(f'{time.strftime("%H:%M:%S")} {name}: {result} {detail} ({seconds} s{f", queued {waited} s" if waited else ""})', flush=True)
    return dict(check=name, tier=tier, kind=kind, result=result, detail=detail, failing=bad, exit=rc, seconds=seconds, waited=waited,
                port=port, baseline=(f"{b['result']} {b['detail']}" if b else '-'), log=str(log.relative_to(ROOT)))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--tier', choices=('quick', 'full'), default='quick')
    ap.add_argument('--only', help='comma-separated check names')
    ap.add_argument('--label', default=time.strftime('%Y%m%d-%H%M%S'))
    ap.add_argument('--who', default='suite', help="runlock's holder name (your session's)")
    ap.add_argument('--jobs', type=int, default=3, help='QUICK checks at once (each its own runlock call)')
    ap.add_argument('--set-baseline', action='store_true')
    args = ap.parse_args()
    known = json.loads(KNOWN.read_text()) if KNOWN.exists() else {}
    base = json.loads(BASELINE.read_text()) if BASELINE.exists() else {}
    picked = [c for c in CHECKS if (args.tier == 'full' or c[1] == 'quick') and (not args.only or c[0] in args.only.split(','))]
    tag = f'suite-{args.label}'
    logs = TESTS/tag
    logs.mkdir(parents=True, exist_ok=True)
    report = dict(label=args.label, tier=args.tier, jobs=args.jobs, started=time.strftime('%Y-%m-%d %H:%M:%S'), rows=[])
    out_json, out_md = TESTS/f'{tag}.json', TESTS/f'{tag}.md'
    t_start = time.time()
    quick = sorted([c for c in picked if c[2] == 'run' and c[0] not in SOLO], key=lambda c: (c[0] not in LONG, LONG.index(c[0]) if c[0] in LONG else 0))
    done, rows = set(), {}
    with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
        running = {}
        while quick or running:
            for c in list(quick):
                if len(running) >= max(1, args.jobs): break
                if c[6] and c[6] not in done and any(x[0] == c[6] for x in picked): continue   # waits for the check it reads
                quick.remove(c)
                running[pool.submit(run_check, c, tag, args.who, logs, known, base)] = c[0]
            if not running: break
            finished, _ = wait(list(running), return_when=FIRST_COMPLETED)
            for f in finished:
                name = running.pop(f)
                rows[name] = f.result()
                done.add(name)
                report['rows'] = [rows[c[0]] for c in picked if c[0] in rows]
                out_json.write_text(json.dumps(report, indent=2) + '\n')
    for c in picked:   # the solo ones: after the parallel part, nothing else of the suite's beside them
        if c[0] in SOLO:
            rows[c[0]] = run_check(c, tag, args.who, logs, known, base)
            report['rows'] = [rows[x[0]] for x in picked if x[0] in rows]
            out_json.write_text(json.dumps(report, indent=2) + '\n')
    report['quick_seconds'] = round(time.time() - t_start)
    for c in picked:   # the full tier's: one at a time, after the rest (real windows as input; the full-world soak alone)
        if c[1] == 'full':
            rows[c[0]] = run_check(c, tag, args.who, logs, known, base)
            report['rows'] = [rows[x[0]] for x in picked if x[0] in rows]
            out_json.write_text(json.dumps(report, indent=2) + '\n')
    report['finished'] = time.strftime('%Y-%m-%d %H:%M:%S')
    report['seconds'] = round(time.time() - t_start)
    report['passed'] = all(r['result'] == 'pass' for r in report['rows'])
    out_json.write_text(json.dumps(report, indent=2) + '\n')
    q = report['quick_seconds']
    lines = [f"Suite {args.label} ({args.tier}, {args.jobs} at once), {report['started']} - {report['finished'][11:]}: {'PASS' if report['passed'] else 'FAIL'}",
             f"QUICK part: {q // 60}:{q % 60:02d} wall clock" + (f"; all: {report['seconds'] // 60}:{report['seconds'] % 60:02d}" if args.tier == 'full' else ''), '',
             '| check | tier | result | detail | baseline | time |', '|---|---|---|---|---|---|']
    for r in report['rows']:
        t = f"{r['seconds'] // 60}:{r['seconds'] % 60:02d}" + (f" (queued {r['waited']} s)" if r['waited'] else '')
        lines.append(f"| {r['check']} | {r['tier']} | {r['result']} | {r['detail']} | {r['baseline']} | {t} |")
    out_md.write_text('\n'.join(lines) + '\n')
    print('\n'.join(lines))
    if args.set_baseline:
        for r in report['rows']:
            base[r['check']] = dict(result=r['result'], detail=r['detail'], seconds=r['seconds'], label=args.label)
        BASELINE.write_text(json.dumps(base, indent=2) + '\n')
        print('baseline written:', BASELINE.relative_to(ROOT))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
