#!/usr/bin/env python3
"""The overnight-polish freeze (2026-10-23, qa-stability): check the frozen source, build the main app, check the app.

    python3 tools/qa_final_check.py --label final            # checks, then build + app check through the lock
    python3 tools/qa_final_check.py --label pre --no-build   # checks only

1. HUD watch (script syntax, compile, captured HUD/3D models in headless Chrome and a real WKWebView).
2. Key server checks (save round trip, safe start, progress, heirs, rooms, specials, unit save, village, multiplayer),
   and audio's checks (render, HUD hooks, mix, real WebKit).
3. tools/build_app.py and tools/check_app.py (with --native-panels), then audio's real-client check, each through
   tools/runlock.py.
Writes tests/qa-final-<label>.json and prints a short summary. Stops before building if a step fails, unless
--build-anyway is given."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
KEY_CHECKS = ['check_save_roundtrip', 'check_safe_start', 'check_progress', 'check_heirs', 'check_rooms',
              'check_specials', 'check_unit_save', 'check_village', 'check_multiplayer', 'check_fire_crowd', 'check_vapours']
LONG_CHECKS = ['check_construction', 'check_blueprints', 'check_buildings']   # with --full


def run(cmd, log, timeout):
    started = time.monotonic()
    with log.open('w') as out:
        try:
            code = subprocess.run(cmd, cwd=ROOT, stdout=out, stderr=subprocess.STDOUT, timeout=timeout).returncode
        except subprocess.TimeoutExpired:
            code = 'timeout'
    tail = [l for l in log.read_text(errors='replace').splitlines() if l.strip()][-8:]
    return dict(cmd=' '.join(cmd)[:200], exit=code, seconds=round(time.monotonic() - started), log=str(log), tail=tail)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', default=datetime.now().strftime('%H%M'))
    parser.add_argument('--no-build', action='store_true')
    parser.add_argument('--build-anyway', action='store_true')
    parser.add_argument('--full', action='store_true', help='also the long construction checks (~20 min more)')
    args = parser.parse_args()
    logs = ROOT/f'tests/qa-final-{args.label}'
    logs.mkdir(parents=True, exist_ok=True)
    py = sys.executable
    report = dict(label=args.label, started=datetime.now().isoformat(timespec='seconds'), steps={})
    out = ROOT/f'tests/qa-final-{args.label}.json'

    def step(name, cmd, timeout):
        r = run(cmd, logs/f'{name}.log', timeout)
        report['steps'][name] = r
        out.write_text(json.dumps(report, indent=2) + '\n')
        print(f"{'ok  ' if r['exit'] == 0 else 'FAIL'} {name} ({r['seconds']}s)", flush=True)
        return r['exit'] == 0

    ok = step('hud_watch', [py, 'tools/check_hud_watch.py', '--label', f'qa-final-{args.label}-hw'], 900)
    ok = step('server_checks', [py, 'tools/run_server_checks.py', '--label', f'qa-final-{args.label}', '--only', ','.join(KEY_CHECKS + (LONG_CHECKS if args.full else []))], 5400) and ok
    # audio's own checks (lock-free; the native one runs after the app check, through the lock)
    ok = step('audio_render', ['node', 'tools/render_audio.js'], 600) and ok
    ok = step('audio_hud', [py, 'tools/check_audio_hud.py'], 600) and ok
    ok = step('audio_mix', [py, 'tools/check_audio_mix.py'], 600) and ok
    step('audio_webkit', [py, 'tools/check_audio_webkit.py'], 600)   # reported, not a build gate
    sc = ROOT/f'tests/server-checks-qa-final-{args.label}.json'
    if sc.exists():
        report['server_checks_failed'] = json.loads(sc.read_text()).get('failed')
        ok = ok and not report['server_checks_failed']
    if not args.no_build and (ok or args.build_anyway):
        # keep the app being replaced (build_app.py removes it and builds anew)
        keep = ROOT/f'restore-points/before-final-build-{args.label}'
        if not keep.exists():
            step('keep_old_app', ['/usr/bin/ditto', str(ROOT/'Dungeon Master Remastered.app'), str(keep/'Dungeon Master Remastered.app')], 600)
        built = step('build_app', ['/usr/bin/caffeinate', '-d', '-i', py, 'tools/runlock.py', '--who', 'qa-stability', '--', py, 'tools/build_app.py'], 3600)
        if built:
            step('check_app', ['/usr/bin/caffeinate', '-d', '-i', py, 'tools/runlock.py', '--who', 'qa-stability', '--', py, 'tools/check_app.py',
                               '--race', 'Human', '--native-panels', '--label', f'qa-final-{args.label}-app'], 2400)
            step('audio_native', ['/usr/bin/caffeinate', '-d', py, 'tools/runlock.py', '--who', 'qa-stability', '--', py,
                                  'tools/check_audio_native.py'], 1200)
            app = ROOT/f'tests/qa-final-{args.label}-app-checks.json'
            if app.exists():
                a = json.loads(app.read_text())
                report['app'] = dict(passed=a.get('passed'), normal_saves_unchanged=a.get('normal_saves_unchanged'),
                                     matches_current_build=a.get('matches_current_build'),
                                     phases={k: {x: p.get(x) for x in ('exit_code', 'client_in_game', 'saved_units',
                                             'saved_units_alive', 'save_status', 'game_runtime_errors')} for k, p in a.get('phases', {}).items()})
    elif not args.no_build:
        print('not building: a check failed (use --build-anyway to build regardless)')
    report['finished'] = datetime.now().isoformat(timespec='seconds')
    out.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'steps'}, indent=1)[:3000])


if __name__ == '__main__':
    main()
