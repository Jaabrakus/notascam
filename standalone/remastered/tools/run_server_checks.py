#!/usr/bin/env python3
"""Run every self-contained check (server only, no required arguments) one at a
time and write a pass/fail summary to tests/server-checks-<label>.json.

Checks that open a game window, or need a candidate/baseline build, are left
out; run those on their own."""
import argparse
from datetime import datetime, timezone
import json
import os
import signal
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT/'tools'
SKIP = {'check_app.py', 'check_recovery_save.py', 'check_starting_races.py', 'check_world_soak.py',
        'check_village_soak.py',    # a 30-minute soak; run it on its own
        'check_track_profile.py',   # a timing report, not a gate
        'check_real_save.py',       # reads the player's own saves (copies them); run it on its own
        'check_mining_filter.py',   # needs a candidate build folder
        'check_zlevel.py',          # a timing probe on a 1000x1000 world, 15+ minutes; run it on its own
        # phone-width tap tests of the old non-overlay page (the game always runs the overlay HUD, which
        # check_hud_watch.py covers); they fail since the October 22 HUD layout. Run by hand if that page returns.
        'check_easy_orders_hud.py', 'check_idle_hud.py'}


def runnable():
    out = []
    for path in sorted(TOOLS.glob('check_*.py')):
        text = path.read_text(errors='replace')
        if path.name in SKIP or 'Robust.Client' in text or 'required=True' in text:
            continue
        out.append(path)
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', default=datetime.now().strftime('%Y%m%d-%H%M'))
    parser.add_argument('--timeout', type=int, default=900, help='Seconds per check.')
    parser.add_argument('--only', help='Comma-separated check names to run.')
    args = parser.parse_args()
    checks = runnable()
    if args.only:
        wanted = {n if n.endswith('.py') else n + '.py' for n in args.only.split(',')}
        checks = [c for c in checks if c.name in wanted]
    report = ROOT/'tests'/f'server-checks-{args.label}.json'
    result = dict(started_utc=datetime.now(timezone.utc).isoformat(), checks=[])
    for path in checks:
        started = time.monotonic()
        try:
            command = [sys.executable, str(path)]
            # Checks that keep their evidence refuse to overwrite an existing label.
            if "'--label'" in path.read_text(errors='replace'): command += ['--label', 'qa' + re.sub(r'[^A-Za-z0-9]', '', args.label + path.stem[6:])]
            # Its own process group, so a timeout also stops the game server it started.
            proc = subprocess.Popen(command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, start_new_session=True)
            out, _ = proc.communicate(timeout=args.timeout)
            code = proc.returncode
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            out, _ = proc.communicate()
            code = 'timeout'
        tail = [line for line in out.splitlines() if line.strip()][-12:]
        verdict = 'pass' if code == 0 else 'fail'
        if code == 0 and any(re.fullmatch(r'\s*FAILED\s*', line) for line in tail[-3:]):
            verdict = 'fail'
        result['checks'].append(dict(check=path.name, verdict=verdict, exit=code, seconds=round(time.monotonic() - started, 1), tail=tail))
        print(f'{verdict:4} {path.name} ({round(time.monotonic() - started)}s)', flush=True)
        report.write_text(json.dumps(result, indent=2) + '\n')
    result['finished_utc'] = datetime.now(timezone.utc).isoformat()
    result['passed'] = sum(c['verdict'] == 'pass' for c in result['checks'])
    result['failed'] = [c['check'] for c in result['checks'] if c['verdict'] != 'pass']
    report.write_text(json.dumps(result, indent=2) + '\n')
    print(f"{result['passed']}/{len(result['checks'])} passed; failed: {', '.join(result['failed']) or 'none'}")


if __name__ == '__main__':
    main()
