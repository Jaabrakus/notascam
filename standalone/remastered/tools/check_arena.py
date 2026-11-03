"""Runs a test in the obey arena (a 120x100 map, light: not the 3 GB world) with its helpers (tests/obey_test.dm) and
prints its CK|name|ok|detail checks; every one must report 1, and it must end with CK|complete. --test is the test file,
--entry its proc; --game and --runtime-dll test a candidate. tools/check_clip.py is the same for tests/clip_check.dm.
Run it through tools/runlock.py --kind run."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
APP_RUNTIME = ROOT/'Dungeon Master Remastered.app/Contents/Resources/game/runtime'
COMPILER = ROOT.parent/'replica/runtime/macos-x64/compiler/DMCompiler.dll'   # shared, used read-only


def scrape_gc(port):
    import urllib.request
    try: text = urllib.request.urlopen(f'http://127.0.0.1:{port}/metrics', timeout=2).read().decode(errors='replace')
    except Exception as error: return {'error': repr(error)[:120]}
    out = {}
    for line in text.splitlines():
        if line.startswith(('dotnet_gc_pause_seconds_sum', 'dotnet_collection_count_total', 'dotnet_total_memory_bytes', 'process_cpu_seconds_total')):
            k, _, v = line.rpartition(' ')
            try: out[k] = float(v)
            except ValueError: pass
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--game', type=Path, default=ROOT/'game', help='game folder to test (default game/)')
    ap.add_argument('--runtime-dll', type=Path, help='OpenDreamRuntime.dll to run it on (default: the app\'s)')
    ap.add_argument('--port', type=int, default=12296)
    ap.add_argument('--test', type=Path, required=True, help='the test .dm file')
    ap.add_argument('--entry', required=True, help='its proc, started when the world starts')
    ap.add_argument('--report', help='results file name in tests/ (default: the test name + -checks.json)')
    ap.add_argument('--profile', action='store_true', help="the tick profiler on (RM_TICK_PROFILE=1); its log is kept as tests/<report>-tick-profile.log")
    ap.add_argument('--timeout', type=float, default=900, help='seconds to wait for CK|complete')
    ap.add_argument('--size', help='the arena\'s map as WIDTHxHEIGHT (default 120x100, obey_test.dm); set when it compiles: growing world.maxx at run time stalls the server for minutes')
    ap.add_argument('--maxz', type=int, help='the arena\'s layers (default 2, obey_test.dm; 3 for a mountain top on the sky layer)')
    ap.add_argument('--metrics', type=int, help="engine metrics port: GC counts and pauses every second into tests/<report>-metrics.json, each sample with how many CK|/STRESS| lines the test had logged (Robust's Prometheus server)")
    ap.add_argument('--max-speed', type=int, help='RM_MAX_SPEED for the server (engine v5.1: lets a test world run its clock above play\'s 4, up to 32); '
                    'default: the highest world.game_state the test sets, when that is above 4; 0 leaves it unset (as in play)')
    args = ap.parse_args()
    if not args.report: args.report = args.test.stem + '-checks.json'
    if args.max_speed is None:
        asked = [int(x) for x in re.findall(r'game_state\s*=\s*(\d+)', args.test.read_text(encoding='latin-1'))]
        args.max_speed = min(32, max(asked)) if asked and max(asked) > 4 else 0
    tests = ROOT/'tests'
    with tempfile.TemporaryDirectory(prefix='dm-clip-') as temp:
        arena = Path(temp)/'arena'
        shutil.copytree(args.game, arena, ignore=shutil.ignore_patterns('Cave Crawlers.json', '*.dmm', 'ErrorLog.txt', 'units', 'players', 'tick-profile.log'))
        (arena/'units').mkdir()
        dme = re.sub(r'^#include .*\.dmm"\s*$', '', (arena/'Cave Crawlers.dme').read_text(encoding='latin-1'), flags=re.M)
        (arena/'ck.dme').write_text(dme + f'\n#include "obey_test.dm"\n#include "{args.test.name}"\n', encoding='latin-1')
        world = arena/'Code/World.dm'
        text = world.read_text(encoding='latin-1')
        start = text.index('\tNew()'); end = text.index('\nvar/Season', start)
        world.write_text(text[:start] + f'\tNew()\n\t\tspawn(0) {args.entry}()\n' + text[end:], encoding='latin-1')
        shutil.copy2(tests/'obey_test.dm', arena/'obey_test.dm')
        if args.size:
            w, h = (int(x) for x in args.size.lower().split('x'))
            ob = (arena/'obey_test.dm').read_text(encoding='latin-1')
            if '\tmaxx = 120\n\tmaxy = 100\n' not in ob: raise SystemExit('obey_test.dm\'s world size changed; review --size')
            (arena/'obey_test.dm').write_text(ob.replace('\tmaxx = 120\n\tmaxy = 100\n', f'\tmaxx = {w}\n\tmaxy = {h}\n', 1), encoding='latin-1')
        if args.maxz:
            ob = (arena/'obey_test.dm').read_text(encoding='latin-1')
            if '\tmaxz = 2\n' not in ob: raise SystemExit('obey_test.dm\'s world layers changed; review --maxz')
            (arena/'obey_test.dm').write_text(ob.replace('\tmaxz = 2\n', f'\tmaxz = {args.maxz}\n', 1), encoding='latin-1')
        shutil.copy2(args.test, arena/args.test.name)
        # Behaviour runs at a faster clock (owner, 2026-10-27: "you can just put the game speeds to max speed and it would
        # cut down times by a lot"): with RM_TEST_SPEED or tools/.test_speed, a test's "world.game_state = 4" runs at that
        # speed instead; timing runs (--profile) and the speed-1 parts keep theirs.
        fast = os.environ.get('RM_TEST_SPEED') or ((ROOT/'tools/.test_speed').read_text().strip() if (ROOT/'tools/.test_speed').exists() else '')
        if fast.isdigit() and int(fast) > 4 and (not args.profile or os.environ.get('RM_PROFILE_FAST') == '1'):   # RM_PROFILE_FAST=1: base/fix timing A/B at speed too (owner 10-27)
            n = min(32, int(fast))
            src = (arena/args.test.name).read_text(encoding='latin-1')
            fixed = re.sub(r'(world\.game_state\s*=\s*)4\b', rf'\g<1>{n}', src)
            if fixed != src:
                (arena/args.test.name).write_text(fixed, encoding='latin-1')
                args.max_speed = max(args.max_speed or 0, n)
        runtime = APP_RUNTIME
        if args.runtime_dll:
            runtime = Path(temp)/'runtime'
            shutil.copytree(APP_RUNTIME, runtime, symlinks=True)
            shutil.copy2(args.runtime_dll, runtime/'server/Resources/Assemblies/OpenDreamRuntime.dll')
        dotnet = runtime/'dotnet/dotnet'
        env = dict(os.environ, DOTNET_ReadyToRun='0')
        if args.profile: env['RM_TICK_PROFILE'] = '1'
        if args.max_speed: env['RM_MAX_SPEED'] = str(args.max_speed)
        else: env.pop('RM_MAX_SPEED', None)
        stem = Path(args.report).stem   # logs named after the report, so two runs never share them
        with (tests/f'{stem}-compile.log').open('w') as out:
            subprocess.run([str(dotnet), str(COMPILER), str(arena/'ck.dme')], env=env, stdout=out, stderr=subprocess.STDOUT, check=True)
        log = tests/f'{stem}-server.log'
        with tempfile.TemporaryDirectory(prefix='dm-clip-data-') as data, log.open('w') as out:
            metrics_cvars = ['--cvar', 'metrics.enabled=true', '--cvar', 'metrics.host=127.0.0.1', '--cvar', f'metrics.port={args.metrics}',
                             '--cvar', 'metrics.runtime_gc=Informational'] if args.metrics else []
            server = subprocess.Popen([str(dotnet), str(runtime/'server/Robust.Server.dll'), '--data-dir', data,
                '--cvar', f'opendream.json_path={arena/"ck.json"}', '--cvar', f'opendream.topic_port={args.port + 13500}',
                '--cvar', 'net.bindto=127.0.0.1', '--cvar', f'net.port={args.port}', '--cvar', 'status.enabled=false',
                '--cvar', 'hub.advertise=false', '--cvar', 'auth.mode=0', '--cvar', 'game.auto_pause_empty=false'] + metrics_cvars,
                env=env, stdout=out, stderr=subprocess.STDOUT, cwd=arena)
            # Stopped or killed (a session's pkill, the user's Ctrl-C), the test server goes too: never left running alone.
            def stop_server(*_):
                if server.poll() is None:
                    server.terminate()
                    try: server.wait(10)
                    except subprocess.TimeoutExpired: server.kill()
                sys.exit(1)
            for sig in (signal.SIGTERM, signal.SIGHUP, signal.SIGINT): signal.signal(sig, stop_server)
            deadline = time.monotonic() + args.timeout
            samples = []   # --metrics: every second [unix time, the test's CK|/STRESS| lines so far, {GC/process metric: value}]
            next_mx = 0
            while time.monotonic() < deadline and server.poll() is None and 'CK|complete' not in (now := log.read_text(errors='replace')):
                if args.metrics and time.monotonic() >= next_mx:
                    next_mx = time.monotonic() + 1
                    samples.append([round(time.time(), 2), len(re.findall(r'(?:CK|STRESS)\|', now)), scrape_gc(args.metrics)])
                time.sleep(.5)
            if samples: (tests/f'{stem}-metrics.json').write_text(json.dumps(samples))
            if server.poll() is None:
                server.terminate()
                try: server.wait(10)
                except subprocess.TimeoutExpired: server.kill()
        if args.profile and (arena/'tick-profile.log').exists(): shutil.copy2(arena/'tick-profile.log', tests/f'{stem}-tick-profile.log')
        errorlog = arena/'ErrorLog.txt'
        text = log.read_text(errors='replace') + (errorlog.read_text(errors='replace') if errorlog.exists() else '')
    rows = re.findall(r'CK\|([^|\r\n]+)\|([01])\|([^\r\n]*)', text)
    notes = re.findall(r'CK\|(?:note|time)\|[^\r\n]*', text)
    pace = re.findall(r'clock speed=[^\r\n]*', text)   # the engine's own pace lines (RM_MAX_SPEED above 4)
    errors = re.findall(r'\[(?:ERRO|FATL)\][^\r\n]*|runtime error[^\r\n]*', text)
    result = dict(passed=bool(rows) and all(r[1] == '1' for r in rows) and 'CK|complete' in text and not errors,
                  game=str(args.game), runtime_dll=str(args.runtime_dll) if args.runtime_dll else None,
                  max_speed=args.max_speed or None, checks=[dict(name=r[0], ok=r[1] == '1', detail=r[2]) for r in rows], notes=notes, pace=pace, errors=errors[:10])
    (tests/args.report).write_text(json.dumps(result, indent=2) + '\n')
    for r in rows: print(('  ' if r[1] == '1' else '!!'), r[0], r[2])
    for n in notes: print('  ', n)
    for n in pace: print('  ', n)
    if errors: print('errors:', *errors[:5], sep='\n  ')
    print('passed' if result['passed'] else 'FAILED')
    if not result['passed']: raise SystemExit(1)


if __name__ == '__main__':
    main()
