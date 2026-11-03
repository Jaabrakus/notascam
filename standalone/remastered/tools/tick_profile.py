#!/usr/bin/env python3
"""Server tick profile on a private copy of the player's world (TickProfile.dm, tests/tick_profile_probe.dm).

Copies game/ and the player's saves (~/Library/Application Support/Dungeon Master Remastered/world/units and players,
read only; their hashes are checked unchanged afterwards) into a temp folder, compiles it, and runs the app's own
packaged runtime (copied too, so a rebuild can't change it mid-run) with RM_TICK_PROFILE=1. With --client real the
app's WebKit client logs in as the player (their save loads), sends no input, and stays on the camera's spot; with
--client none only the world runs. --units N adds N Dwarves to the player's village, --orders S sends the whole army
8 tiles off and back every S seconds (the game's own RemasterOrder, everyone selected).

Writes reports/server-cost/<label>.json and .md: each system's ms per game second, calls, ms per call and the
slowest call; world.cpu (the DM part of each tick); how far the server fell behind real time; and how many
"MainLoop: Cannot keep up!" the server printed.

    python3 tools/runlock.py --who server-cost --kind run -- python3 tools/tick_profile.py --label base --minutes 3
"""
import argparse
import hashlib
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
REPLICA = ROOT.parent / 'replica/runtime/macos-x64'          # its compiler (the app build uses the same)
APP = ROOT / 'Banners of the Deep.app/Contents/Resources/game'
PLAYER_WORLD = Path.home() / 'Library/Application Support/Dungeon Master Remastered/world'
OUT = ROOT / 'reports/server-cost'


def hashes():
    out = {}
    for kind in ('units', 'players'):
        for p in sorted((PLAYER_WORLD / kind).glob('*')):
            if p.is_file(): out[f'{kind}/{p.name}'] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def stop(proc, sig=signal.SIGINT, grace=15):
    if not proc or proc.poll() is not None: return
    for s, g in ((sig, grace), (signal.SIGTERM, 10), (signal.SIGKILL, 5)):
        try: proc.send_signal(s)
        except ProcessLookupError: return
        try:
            proc.wait(g)
            return
        except subprocess.TimeoutExpired:
            pass


def footprint_mb(pid):
    # macOS physical footprint (resident + compressed + swapped), as Activity Monitor's "Memory"
    out = subprocess.run(['vmmap', '--summary', str(pid)], capture_output=True, text=True, timeout=120).stdout
    m = re.search(r'^Physical footprint:\s+([\d.]+)([KMG])', out, flags=re.M)
    return round(float(m.group(1)) * {'K': 1 / 1024, 'M': 1, 'G': 1024}[m.group(2)]) if m else None


def rss_mb(pid):
    # resident memory (ps): costs the server nothing, unlike vmmap
    out = subprocess.run(['ps', '-o', 'rss=', '-p', str(pid)], capture_output=True, text=True).stdout.split()
    return round(int(out[0]) / 1024) if out else None


def scrape(port):
    import urllib.request
    try:
        text = urllib.request.urlopen(f'http://127.0.0.1:{port}/metrics', timeout=2).read().decode(errors='replace')
    except Exception as error:
        return {'error': repr(error)[:120]}
    out = {}
    for line in text.splitlines():
        if line.startswith('#') or not line.strip(): continue
        name = line.split('{')[0].split(' ')[0]
        if ('gc' in name or 'collection' in name or name.startswith('process_') or 'memory' in name) and 'bucket' not in name:
            key, _, val = line.rpartition(' ')
            try: out[key] = float(val)
            except ValueError: pass
        elif name == 'dotnet_gc_pause_seconds_bucket' or name.endswith('gc_pause_seconds_bucket'):
            key, _, val = line.rpartition(' ')
            out[key] = float(val)
    return out


def parse(lines):
    rows = []
    for line in lines:
        if not line.startswith('RMPROF|'): continue
        head, _, body = line.rpartition('|')
        f = dict(kv.split('=', 1) for kv in head.split('|')[1:] if '=' in kv)
        systems = {}
        for part in body.split(';'):
            name, _, v = part.rpartition('=')
            ms, n, mx = (float(x) if x else 0.0 for x in v.split('/'))
            systems[name] = (ms, n, mx)
        cpu = [float(x) for x in f['cpu'].split('/')]
        st = [float(x) for x in f.get('stalls', '0/0/0').split('/')]
        al = [float(x) for x in f.get('alloc', '0/0').split('/')]   # MB the game thread / the process allocated that second (engine v6)
        kb = {}
        for item in filter(None, f.get('kb', '').split(',')):
            name, _, v = item.rpartition('~')
            kb[name] = float(v or 0)
        rows.append(dict(rt=int(f.get('rt', -1)), t=int(f['t']), ticks=int(f['ticks']), real=int(f['real']), cpu=cpu[0], cpu_max=cpu[1], over=int(cpu[2]),
                         stalls=int(st[0]), stall_max=st[1], stall_cpu=st[2], players=int(f['players']), mobs=int(f['mobs']), slept=int(f['slept']), systems=systems, alloc_game=al[0], alloc_proc=al[-1], kb=kb))
    return rows


def summary(rows):
    if not rows: return {}
    secs = len(rows)
    names = sorted({k for r in rows for k in r['systems']})
    table = {}
    for k in names:
        ms = sum(r['systems'].get(k, (0, 0, 0))[0] for r in rows)
        n = sum(r['systems'].get(k, (0, 0, 0))[1] for r in rows)
        mx = max(r['systems'].get(k, (0, 0, 0))[2] for r in rows)
        table[k] = dict(ms_per_s=round(ms / secs, 2), calls_per_s=round(n / secs, 2), ms_per_call=round(ms / n, 2) if n else 0, max_ms=mx,
                        kb_per_s=round(sum(r['kb'].get(k, 0) for r in rows) / secs, 1))
    ticks = sum(r['ticks'] for r in rows)
    real = sum(r['real'] for r in rows)
    return dict(seconds=secs, ticks=ticks, real_ds=real, behind_ds=real - ticks, slow_seconds=sum(1 for r in rows if r['real'] > r['ticks'] + 2),
                worst_second_ds=max(r['real'] for r in rows), cpu_avg=round(sum(r['cpu'] for r in rows) / secs, 1),
                cpu_max=max(r['cpu_max'] for r in rows), ticks_over_100=sum(r['over'] for r in rows),
                stalls=sum(r['stalls'] for r in rows), stall_max_ds=max(r['stall_max'] for r in rows),
                stalls_light=sum(1 for r in rows if r['stalls'] and r['stall_cpu'] < 50), mobs=max(r['mobs'] for r in rows),
                players=max(r['players'] for r in rows), slept=sum(r['slept'] for r in rows), systems=table,
                alloc_game_mb_s=round(sum(r['alloc_game'] for r in rows) / secs, 2), alloc_process_mb_s=round(sum(r['alloc_proc'] for r in rows) / secs, 2))


def markdown(label, args, s, extra):
    out = [f'# Tick profile: {label}', '', f'{args}', '',
           f"{s['seconds']} game seconds measured; {s['ticks']} ticks took {s['real_ds'] / 10:.1f} s of real time "
           f"(behind by {s['behind_ds'] / 10:.1f} s; {s['slow_seconds']} seconds slower than 1.2 s; worst {s['worst_second_ds'] / 10:.1f} s). "
           f"world.cpu (DM part of a tick, % of 100 ms): average {s['cpu_avg']}, worst tick {s['cpu_max']}, {s['ticks_over_100']} ticks over 100. "
           f"Gaps of 0.3 s or more between ticks: {s['stalls']} (longest {s['stall_max_ds'] / 10:.1f} s; seconds whose longest gap came "
           f"before a light tick, under 50 % DM, i.e. time spent outside the game's code: {s['stalls_light']}). "
           f"Creatures in the world: {s['mobs']}; players: {s['players']}. \"Cannot keep up\": {extra['cannot_keep_up']}.", '',
           '| system | ms per game second | calls per s | ms per call | slowest call ms |', '| --- | ---: | ---: | ---: | ---: |']
    order = sorted(s['systems'].items(), key=lambda kv: (kv[0] != 'other DM', kv[0].split('/')[0] not in ('track',), kv[0]))
    for k, v in order:
        out.append(f"| {k} | {v['ms_per_s']} | {v['calls_per_s']} | {v['ms_per_call']} | {v['max_ms']} |")
    out += ['', 'Extra: ' + json.dumps({k: v for k, v in extra.items() if k not in ('tp', 'proc', 'footprint', 'vmmap')}), '', 'Probe: ' + json.dumps(extra.get('tp', [])),
            '', 'Every 10 s [s, server MB, server %CPU, client MB, load, client %CPU]: ' + json.dumps(extra.get('proc', [])),
            '', 'Server memory, ps RSS before the warmup and after the end [s, MB]: ' + json.dumps(extra.get('footprint', []))]
    if extra.get('vmmap'): out += ['', 'Server physical footprint (vmmap, each one a ~2 s stall in the measure) [s, MB]: ' + json.dumps(extra['vmmap'])]
    return '\n'.join(out) + '\n'


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--label', required=True)
    ap.add_argument('--minutes', type=float, default=3)
    ap.add_argument('--warmup', type=float, default=30, help='seconds after the HUD is up before measuring')
    ap.add_argument('--client', choices=('real', 'none'), default='real')
    ap.add_argument('--units', type=int, default=0)
    ap.add_argument('--orders', type=int, default=0)
    ap.add_argument('--pan', type=float, default=0, help='camera pan, tiles a second (real client only)')
    ap.add_argument('--port', type=int, default=12493)
    ap.add_argument('--game', type=Path, default=ROOT / 'game', help='game folder to profile (default game/)')
    ap.add_argument('--username', default='kiwimango')
    ap.add_argument('--extra', action='append', default=[], type=Path, help='another DM file to include (a fixture)')
    ap.add_argument('--until', help='stop measuring as soon as tick-profile.log holds this text (a fixture says it is done)')
    ap.add_argument('--runtime-dll', type=Path, help='an OpenDreamRuntime.dll to run instead of the app\'s (a test build); only the temp copy changes')
    ap.add_argument('--no-game-guard', action='store_true', help="run even while a LandOfLords app is open (only when the user says so: e.g. it is another session's check, not their game)")
    ap.add_argument('--footprint-every', type=float, default=0, help='seconds between vmmap physical-footprint samples (each one suspends the server ~2 s, inside the measure; logged as TP|vmmap just before); default: none (the start and end readings are ps RSS)')
    ap.add_argument('--metrics', type=int, help="engine metrics port: scrape GC counts and pauses every second (Robust's Prometheus server)")
    ap.add_argument('--env', action='append', default=[], help='KEY=VALUE for the server (GC experiments)')
    ap.add_argument('--cvar', action='append', default=[], help='NAME=VALUE engine setting for the server (e.g. net.pvs_range=1: what each client is sent of the map)')
    ap.add_argument('--gc', choices=('workstation', 'server'), default='workstation', help="the app's launch.zsh uses workstation GC since 2026-10-23")
    args = ap.parse_args()
    if not args.no_game_guard and subprocess.run(['pgrep', '-x', 'BannersOfTheDeep|LandOfLords'], capture_output=True).stdout.strip():
        print("USER GAME OPEN: held, not run (the user's own game is running)")   # never run beside it
        return 3
    OUT.mkdir(parents=True, exist_ok=True)
    before = hashes()
    result = dict(label=args.label, args=vars(args) | {'game': str(args.game), 'extra': [str(x) for x in args.extra], 'runtime_dll': str(args.runtime_dll) if args.runtime_dll else None})
    server = client = caffeinate = None
    with tempfile.TemporaryDirectory(prefix='dm-tick-profile-') as temp:
        base = Path(temp)
        world = base / 'world'
        shutil.copytree(args.game, world, ignore=shutil.ignore_patterns('Cave Crawlers.json', '*.sav', '*.sav.bak*', 'ErrorLog.txt', 'units', 'saves', 'players', 'tick-profile.log'))
        for kind in ('units', 'players'):
            (world / kind).mkdir(exist_ok=True)
            for p in (PLAYER_WORLD / kind).glob('*'):
                if p.is_file(): shutil.copy2(p, world / kind / p.name)
        shutil.copy2(ROOT / 'tests/tick_profile_probe.dm', world / 'tick_profile_probe.dm')
        dme = (world / 'Cave Crawlers.dme').read_text(encoding='latin-1')
        assert 'TickProfile.dm' in dme, 'game/ has no TickProfile.dm include'
        for x in args.extra: shutil.copy2(x, world / x.name)
        (world / 'Cave Crawlers.dme').write_text(dme + '\n#include "tick_profile_probe.dm"\n' + ''.join(f'#include "{x.name}"\n' for x in args.extra), encoding='latin-1')
        runtime = base / 'runtime'
        shutil.copytree(APP / 'runtime', runtime, symlinks=True)
        if args.runtime_dll:
            shutil.copy2(args.runtime_dll, runtime / 'server/Resources/Assemblies/OpenDreamRuntime.dll')
            result['runtime_dll'] = hashlib.sha256(args.runtime_dll.read_bytes()).hexdigest()
        env = dict(os.environ, DOTNET_ReadyToRun='0', DOTNET_gcServer='0' if args.gc == 'workstation' else '1', RM_TICK_PROFILE='1', TP_UNITS=str(args.units), TP_ORDERS=str(args.orders), TP_PAN=str(args.pan))
        env.update(kv.split('=', 1) for kv in args.env)
        metrics_cvars = ['--cvar', 'metrics.enabled=true', '--cvar', 'metrics.host=127.0.0.1', '--cvar', f'metrics.port={args.metrics}',
                         '--cvar', 'metrics.runtime_gc=Informational', '--cvar', 'metrics.runtime_gc_histogram=1,5,10,25,50,100,250,500,1000,2000,5000'] if args.metrics else []
        with (base / 'compile.log').open('w') as out:
            subprocess.run([str(REPLICA / 'dotnet/dotnet'), str(REPLICA / 'compiler/DMCompiler.dll'), str(world / 'Cave Crawlers.dme')], env=env, stdout=out, stderr=subprocess.STDOUT, check=True, timeout=300)
        slog, clog, plog = OUT / f'{args.label}-server.log', OUT / f'{args.label}-client.log', world / 'tick-profile.log'
        mark = end_line = None   # the log lines the measure counted: [mark, end_line)
        try:
            with slog.open('w') as sl:
                server = subprocess.Popen([str(runtime / 'dotnet/dotnet'), str(runtime / 'server/Robust.Server.dll'), '--data-dir', str(base / 'data'),
                    '--cvar', f'opendream.json_path={world / "Cave Crawlers.json"}', '--cvar', 'net.bindto=127.0.0.1', '--cvar', f'net.port={args.port}',
                    '--cvar', f'opendream.topic_port={args.port + 13500}', '--cvar', f'log.path={base / "engine-logs"}', '--cvar', 'net.max_connections=16',
                    '--cvar', 'status.enabled=false', '--cvar', 'hub.advertise=false', '--cvar', 'auth.mode=0', '--cvar', 'game.auto_pause_empty=false'] + metrics_cvars + [x for kv in args.cvar for x in ('--cvar', kv)],
                    cwd=world, env=env, stdout=sl, stderr=subprocess.STDOUT)
            deadline = time.monotonic() + 240
            while ' -> Ready' not in slog.read_text(errors='replace'):
                if server.poll() is not None or time.monotonic() > deadline: raise RuntimeError('server did not start')
                time.sleep(1)
            result['server_ready_s'] = round(time.monotonic() - (deadline - 240), 1)
            caffeinate = subprocess.Popen(['caffeinate', '-d', '-i', '-w', str(server.pid)])
            if args.client == 'real':
                cdir = base / 'client'
                shutil.copytree(runtime / 'client', cdir, symlinks=True)
                cres = cdir / 'Space Station 14.app/Contents/Resources'
                cenv = dict(env, ROBUST_MODULE_ROBUST_CLIENT_WEBVIEW=str(runtime / 'webview-webkit'), DM_SKIN_LAYOUT_HINTS=str(APP / 'skin-layout-hints.json'))
                with clog.open('w') as cl:
                    client = subprocess.Popen([str(runtime / 'dotnet/dotnet'), str(cres / 'Robust.Client.dll'), '--mount-zip', str(runtime / 'server/Content.Client.zip'),
                        '--connect', '--connect-address', f'udp://127.0.0.1:{args.port}', '--username', args.username, '--self-contained',
                        '--cvar', 'web.headless=false', '--cvar', 'discord.enabled=false'], cwd=cres, env=cenv, stdout=cl, stderr=subprocess.STDOUT)
                deadline = time.monotonic() + 300
                while 'TP|' not in (plog.read_text(errors='replace') if plog.exists() else ''):
                    if client.poll() is not None or time.monotonic() > deadline: raise RuntimeError('the client never got its HUD up')
                    time.sleep(1)
            t_ready = time.monotonic()
            # No vmmap on a live server unless asked (--footprint-every): it suspends the whole server while it reads the
            # memory map (2.2-2.6 s on these runs), charged to whatever DM proc was open. The start and end samples were
            # the runs' worst stalls (map-memory, 2026-10-25: t3d-v10-after's 2.3 s "other DM" tick at join, t3d2-before's
            # 2.1 s "hud" tick; hud-craft: zoomout-200's 2.6 s "hud/data/units" tick ~3 s after the end). Both readings are
            # now the server's RSS (ps), which costs it nothing.
            t_fp = time.monotonic()
            start_footprint = [0, rss_mb(server.pid)]   # its time is set below: seconds before the measure, negative
            time.sleep(args.warmup)
            mark = len(plog.read_text(errors='replace').splitlines()) if plog.exists() else 0
            end = time.monotonic() + args.minutes * 60
            result['proc'] = []   # every 10 s: seconds in, server RSS MB, server %CPU, client RSS MB, load, client %CPU
            result['footprint'] = [start_footprint]   # seconds in, server RSS MB (ps): before the warmup and after the end
            result['vmmap'] = []   # seconds in, server physical footprint MB (vmmap): only every --footprint-every
            t_mark, next_ps, next_mx = time.monotonic(), 0, 0
            next_vm = t_mark + (args.footprint_every or 1e9)
            start_footprint[0] = round(t_fp - t_mark)
            result['metrics'] = []   # every second: [unix time, {metric line: value}] for the GC and process lines
            while time.monotonic() < end:
                if server.poll() is not None: raise RuntimeError('server stopped')
                if client and client.poll() is not None: raise RuntimeError('client stopped')
                if args.until and plog.exists() and args.until in plog.read_text(errors='replace'): break
                if not args.no_game_guard and subprocess.run(['pgrep', '-x', 'BannersOfTheDeep|LandOfLords'], capture_output=True).stdout.strip():
                    raise RuntimeError("the user's game opened: run stopped")   # never run beside the user's own game
                if time.monotonic() >= next_ps:
                    next_ps = time.monotonic() + 10
                    ps = lambda pid: subprocess.run(['ps', '-o', 'rss=,%cpu=', '-p', str(pid)], capture_output=True, text=True).stdout.split()
                    sv, cv = ps(server.pid), (ps(client.pid) if client else [])
                    result['proc'].append([round(time.monotonic() - t_mark), round(int(sv[0]) / 1024) if sv else None, float(sv[1]) if len(sv) > 1 else None,
                                           round(int(cv[0]) / 1024) if cv else None, round(os.getloadavg()[0], 1), float(cv[1]) if len(cv) > 1 else None])
                if args.metrics and time.monotonic() >= next_mx:
                    next_mx = time.monotonic() + 1
                    result['metrics'].append([round(time.time(), 2), scrape(args.metrics)])
                # vmmap suspends the whole server while it reads the memory map (~2 s on a 3 GB server): every sample is a
                # stall of its own, so only when asked (--footprint-every), and announced in the log just before.
                if args.footprint_every and time.monotonic() >= next_vm:
                    next_vm = time.monotonic() + args.footprint_every
                    s_in = round(time.monotonic() - t_mark)
                    with plog.open('a') as pl: pl.write(f'TP|vmmap|s={s_in}|tick_profile.py samples vmmap now: the server is suspended ~2 s\n')
                    result['vmmap'].append([s_in, footprint_mb(server.pid)])
                time.sleep(0.5 if args.metrics else 2)
            lines = plog.read_text(errors='replace').splitlines()
            end_line = len(lines)
            result['footprint'].append([round(time.monotonic() - t_mark), rss_mb(server.pid)])   # after the last line counted
            result['summary'] = summary(parse(lines[mark:]))
            result['tp'] = [l for l in lines if l.split('|')[0] in ('TP', 'WALLEQ', 'AWAKE', 'WALLPARTS', 'AWAKEDEST', 'PICS', 'SLOW', 'RMPATH', 'SHADOW')]
            result['rows'] = len(parse(lines))
        except Exception as error:
            result['error'] = repr(error)
        finally:
            stop(client)
            stop(server)
            if caffeinate: stop(caffeinate, signal.SIGTERM, 2)
            if plog.exists():   # kept even when the run is stopped
                # SLOWTICK and RMPROF lines from before the measure (loading, the join, the warmup) and after it (the
                # shutdown) are renamed SLOWTICK-WARMUP / RMPROF-AFTER etc., so a grep for SLOWTICK| finds measured ticks only
                kept = plog.read_text(errors='replace').splitlines()
                if mark is not None:
                    stop_at = end_line if end_line is not None else len(kept)
                    for i, l in enumerate(kept):
                        if (i < mark or i >= stop_at) and l.startswith(('SLOWTICK|', 'RMPROF|')):
                            head, rest = l.split('|', 1)
                            kept[i] = f"{head}-{'WARMUP' if i < mark else 'AFTER'}|{rest}"
                (OUT / f'{args.label}-tick-profile.log').write_text('\n'.join(kept) + '\n')
        text = slog.read_text(errors='replace')
        result['cannot_keep_up'] = text.count('Cannot keep up')
        el = world / 'ErrorLog.txt'
        errs = el.read_text(errors='replace') if el.exists() else ''
        result['runtime_errors'] = len(re.findall(r'runtime error', errs, flags=re.I))
        (OUT / f'{args.label}-errorlog.txt').write_text(errs[-200000:])
    result['player_saves_unchanged'] = hashes() == before
    if result.get('metrics'): (OUT / f'{args.label}-metrics.json').write_text(json.dumps(result.pop('metrics')))   # tools/gc_stalls.py lines them up
    result.pop('metrics', None)
    (OUT / f'{args.label}.json').write_text(json.dumps(result, indent=2) + '\n')
    if result.get('summary'):
        (OUT / f'{args.label}.md').write_text(markdown(args.label, ' '.join(sys.argv[1:]), result['summary'],
            dict(cannot_keep_up=result['cannot_keep_up'], runtime_errors=result['runtime_errors'], saves_unchanged=result['player_saves_unchanged'], tp=result['tp'], proc=result.get('proc', []), footprint=result.get('footprint', []), vmmap=result.get('vmmap', []))))
        print((OUT / f'{args.label}.md').read_text())
    print(json.dumps({k: v for k, v in result.items() if k not in ('summary', 'tp', 'proc', 'footprint', 'vmmap', 'metrics')}, indent=2))
    return 0 if result.get('summary') and result['player_saves_unchanged'] and not result.get('error') else 1


if __name__ == '__main__':
    sys.exit(main())
