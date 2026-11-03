#!/usr/bin/env python3
"""Quest maker Q9's web test (planning/QUEST_MAKER_PLAN_2026-10-31.md phase Q9): 10 players in browsers on one world with
500 quests and 50 forts. A copy of game/ with tests/quest_scale_web_seed.dm (10 maker realms, 450 Bring notices, 50 forts
with 4 guards each) runs as a private web world (tools/web_host.py) with the tick profiler on (RM_TICK_PROFILE=1). Ten
headless Chrome players join as web1..web10 (a people, their company, Begin); the seed sets each one's people by a maker's
board; each opens the Quests page and that board's notices, and stays so while the server is measured.

Writes reports/quest-maker-1031/q9/web-test.json and .md: the server's tick (world.cpu each tick: average, worst, ticks
over 100 %), the HUD's and the quest data's ms per game second, the server's memory, and what each browser was sent.

    python3 tools/runlock.py --kind run --who quest-maker -- python3 tools/check_quest_scale_web.py [--players 10] [--seconds 180] [--port 8092]"""
import argparse
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from tick_profile import parse  # noqa: E402

RT = ROOT.parent/'replica/runtime/macos-x64'
OUT = ROOT/'reports/quest-maker-1031/q9'
CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'

ap = argparse.ArgumentParser()
ap.add_argument('--players', type=int, default=10)
ap.add_argument('--seconds', type=int, default=180)
ap.add_argument('--port', type=int, default=8092)
args = ap.parse_args()


def log(*a):
    print(time.strftime('%H:%M:%S'), *a, flush=True)


def wait(cond, secs, step=1.0):
    end = time.monotonic() + secs
    while time.monotonic() < end:
        v = cond()
        if v: return v
        time.sleep(step)
    return None


work = Path(tempfile.mkdtemp(prefix='quest-scale-web-'))
game = work/'game'
subprocess.run(['cp', '-c', '-R', str(ROOT/'game'), str(game)], check=True)
shutil.copy2(ROOT/'tests/quest_scale_web_seed.dm', game/'quest_scale_web_seed.dm')
dme = game/'Cave Crawlers.dme'
dme.write_text(dme.read_text(encoding='latin-1') + '\n#include "quest_scale_web_seed.dm"\n', encoding='latin-1')
log('compiling the test copy')
r = subprocess.run([str(RT/'dotnet/dotnet'), str(RT/'compiler/DMCompiler.dll'), str(dme)], env=dict(os.environ, DOTNET_ReadyToRun='0'), capture_output=True, text=True)
if r.returncode != 0 or not (game/'Cave Crawlers.json').exists():
    sys.exit('compile failed:\n' + '\n'.join(l for l in (r.stdout + r.stderr).splitlines() if 'error' in l.lower())[:3000])

before = set(Path(tempfile.gettempdir()).glob('dm-web-world-*'))
host_log = (OUT/'web-host.log').open('w')
host = subprocess.Popen([sys.executable, '-u', str(ROOT/'tools/web_host.py'), '--private-world', '--world', str(game), '--port', str(args.port)],
                        cwd=ROOT, env=dict(os.environ, RM_TICK_PROFILE='1'), stdout=host_log, stderr=subprocess.STDOUT)
server_log = None   # the world's own log (world.log), ErrorLog.txt in its folder, once the world is up
result = {'players': args.players, 'seconds': args.seconds}
try:
    if not wait(lambda: 'Friends open' in (OUT/'web-host.log').read_text(errors='replace'), 300):
        sys.exit('the world did not start; see ' + str(OUT/'web-host.log'))
    world = wait(lambda: next(iter(set(Path(tempfile.gettempdir()).glob('dm-web-world-*')) - before), None), 30)
    log('world up in', world)
    server_log = Path(world)/'ErrorLog.txt'
    seeded = wait(lambda: next((l for l in server_log.read_text(errors='replace').splitlines() if 'QZW|seeded|' in l), None), 600, 2)
    log('seeded:', seeded)
    result['seeded'] = seeded
    server_pid = subprocess.run(['/usr/sbin/lsof', '-nP', f'-iTCP:{args.port}', '-sTCP:LISTEN', '-t'], capture_output=True, text=True).stdout.split()
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=CHROME, headless=True, args=['--mute-audio'])
        pages = []
        sent = {}
        for i in range(1, args.players + 1):
            ctx = browser.new_context(viewport=dict(width=800, height=500))
            page = ctx.new_page()
            name = f'web{i}'
            sent[name] = 0

            def on_ws(ws, name=name):
                ws.on('framereceived', lambda payload, name=name: sent.__setitem__(name, sent[name] + len(payload)))
            page.on('websocket', on_ws)
            page.goto(f'http://127.0.0.1:{args.port}/?overlay', wait_until='domcontentloaded')
            page.fill('input', name)
            page.keyboard.press('Enter')
            pages.append((name, page))
            log('joined', name)
        for name, page in pages:   # a people, the company, Begin, the story card
            try:
                page.wait_for_selector('#startcard .sc-go', state='visible', timeout=120000)
                page.click('#startcard .sc-go')
                page.locator('#askcard button').filter(has_text='Human').first.click(timeout=30000)
                page.locator('#askcard button').filter(has_text='Begin').first.click(timeout=30000)
                page.wait_for_timeout(1500)
                b = page.locator('button').filter(has_text='Begin')
                if b.count(): b.first.click(timeout=5000)
            except Exception as e:
                log(name, 'start flow:', str(e)[:200])
        placed = wait(lambda: sum(1 for l in server_log.read_text(errors='replace').splitlines() if 'QZW|placed|web' in l) >= args.players or None, 120, 2)
        log('placed:', placed, sum(1 for l in server_log.read_text(errors='replace').splitlines() if 'QZW|placed|web' in l))
        for name, page in pages:   # the Quests page, and the board's notices for the first of their people
            page.wait_for_timeout(500)
            page.evaluate("()=>{send('tab','quests');const u=arr(model&&model.units)[0];if(u)send('quest','board|'+u.ref)}")
        time.sleep(10)
        opened = sum(1 for _, p in pages if p.evaluate("()=>!!(model&&model.questCard&&model.questCard.kind==='board'&&model.quests)"))
        log('boards and Quests pages open:', opened)
        result['open'] = opened
        start_rt = None
        prof = Path(world)/'tick-profile.log'
        n0 = len(prof.read_text(errors='replace').splitlines()) if prof.exists() else 0
        for k in sent: sent[k] = 0
        host_log_path = ROOT/f'reports/web-host/private-server-{args.port}.log'   # the engine's own count of what each player is sent
        h0 = len(host_log_path.read_text(errors='replace').splitlines())
        rss = []
        t_end = time.monotonic() + args.seconds
        while time.monotonic() < t_end:
            time.sleep(10)
            if server_pid:
                out = subprocess.run(['ps', '-o', 'rss=', '-p', server_pid[0]], capture_output=True, text=True).stdout.strip()
                if out: rss.append(int(out) // 1024)
        lines = prof.read_text(errors='replace').splitlines()[n0:] if prof.exists() else []
        (OUT/'web-tick-profile.log').write_text('\n'.join(lines) + '\n')   # kept: the world's folder goes with the world
        if (Path(world)/'hud-keys.log').exists(): shutil.copy2(Path(world)/'hud-keys.log', OUT/'web-hud-keys.log')   # what each HUD send encoded, by key
        result['slow_ticks'] = [l[:300] for l in lines if l.startswith('SLOWTICK|')][:10]
        rows = parse(lines)
        per = {}
        for l in host_log_path.read_text(errors='replace').splitlines()[h0:]:
            m = re.search(r'web: (web\d+) 10 s: .*?\(([\d.]+) KB/s;.*?on the wire \(([\d.]+) KB/s\)', l)
            if m: per.setdefault(m.group(1), []).append((float(m.group(2)), float(m.group(3))))
        result['sent_kb_s'] = {k: {'data': round(sum(x[0] for x in v) / len(v), 1), 'wire': round(sum(x[1] for x in v) / len(v), 1)} for k, v in sorted(per.items())}
        result['quests_left_open'] = sum(1 for _, p in pages if p.evaluate("()=>!!(model&&model.questCard&&model.quests)"))
        browser.close()
        if int(os.environ.get('QZW_AFTER', '0')) > 0:   # the world left empty a while (the tick GC's compaction waits for that)
            log('players gone; waiting', os.environ['QZW_AFTER'], 's')
            time.sleep(int(os.environ['QZW_AFTER']))
    secs = max(1, len(rows))
    cpu = [r['cpu'] for r in rows]
    sysms = {}
    for r in rows:
        for k, (ms, n, mx) in r['systems'].items():
            s = sysms.setdefault(k, [0.0, 0, 0.0])
            s[0] += ms
            s[1] += n
            s[2] = max(s[2], mx)
    result.update({
        'measured_seconds': len(rows),
        'tick_cpu_avg': round(sum(cpu) / secs, 1) if cpu else None,
        'tick_cpu_worst': max((r['cpu_max'] for r in rows), default=None),
        'ticks_over_100': sum(r['over'] for r in rows),
        'stalls': sum(r['stalls'] for r in rows),
        'players_seen': max((r['players'] for r in rows), default=0),
        'server_mb': {'min': min(rss) if rss else None, 'max': max(rss) if rss else None},
        'systems_ms_per_s': {k: {'ms_s': round(v[0] / secs, 3), 'calls_s': round(v[1] / secs, 1), 'slowest_ms': round(v[2], 2)}
                             for k, v in sorted(sysms.items(), key=lambda kv: -kv[1][0]) if k.startswith(('quests', 'hud', 'track', '3d')) or v[0] / secs > 5},
    })
finally:
    host.terminate()
    try: host.wait(20)
    except Exception: host.kill()
    host_log.close()
    subprocess.run(['mv', str(work), str(Path.home()/'.Trash'/work.name)])
(OUT/'web-test.json').write_text(json.dumps(result, indent=2) + '\n')
q = {k: v for k, v in result.get('systems_ms_per_s', {}).items() if k.startswith('quests')}
md = [f"# Q9 web test: {args.players} players, 500 quests, 50 forts ({result.get('measured_seconds')} s measured)", '',
      f"- Seeded: `{result.get('seeded')}`; boards and Quests pages open: {result.get('open')} of {args.players} (still open at the end: {result.get('quests_left_open')})",
      f"- Server tick (world.cpu): average {result.get('tick_cpu_avg')} %, worst {result.get('tick_cpu_worst')} %, ticks over 100 %: {result.get('ticks_over_100')}, stalls: {result.get('stalls')}",
      f"- Server memory: {result.get('server_mb')} MB",
      f"- Quest data the HUD built, ms a game second: " + ', '.join(f"{k} {v['ms_s']} ({v['calls_s']} calls/s, slowest {v['slowest_ms']} ms)" for k, v in q.items()),
      f"- Sent to each browser, KB/s (data / on the wire, the engine's own count): " + ', '.join(k + ' ' + str(v['data']) + ' / ' + str(v['wire']) for k, v in result.get('sent_kb_s', {}).items()), '',
      '| system | ms/s | calls/s | slowest ms |', '|---|---|---|---|']
md += [f"| {k} | {v['ms_s']} | {v['calls_s']} | {v['slowest_ms']} |" for k, v in result.get('systems_ms_per_s', {}).items()]
(OUT/'web-test.md').write_text('\n'.join(md) + '\n')
print('\n'.join(md))
