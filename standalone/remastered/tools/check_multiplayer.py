#!/usr/bin/env python3
"""Two real clients on one server: Alice founds a settlement, Bob joins it as
migrants through the realm prompt. Uses tests/mp_hook.dm (test-only build)."""
import json, os, re, shutil, subprocess, sys, tempfile, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
REPLICA = ROOT.parent/'replica'; RUNTIME = REPLICA/'runtime/macos-x64'
sys.path.insert(0, str(REPLICA/'tools'))
from check_browser import stop
from skin_layout import write_hints

def wait(cond, t):
    d = time.monotonic() + t
    while time.monotonic() < d:
        if cond(): return True
        time.sleep(.5)
    return False

def main():
    arena = ROOT/'tests/mp-arena'
    if arena.exists(): shutil.rmtree(arena)
    shutil.copytree(ROOT/'game', arena, ignore=shutil.ignore_patterns('Cave Crawlers.json', 'ErrorLog.txt', 'trailer-scene.txt'))
    dme = arena/'Cave Crawlers.dme'
    dme.write_text(dme.read_text(encoding='latin-1') + '\n#include "mp_hook.dm"\n', encoding='latin-1')
    shutil.copy2(ROOT/'tests/mp_hook.dm', arena/'mp_hook.dm')
    # --password: the world asks remote players for a password (as "Host for friends" sets up);
    # Bob joins over this Mac's network address with the right one, Eve with a wrong one.
    secured = '--password' in sys.argv
    lan = subprocess.run(['/usr/sbin/ipconfig', 'getifaddr', 'en0'], capture_output=True, text=True).stdout.strip() or '127.0.0.1'
    if secured:
        (arena/'join-password').write_text('test1234')
        (arena/'host-name').write_text('Alice')
        (arena/'host-addresses').write_text(lan + '\n')
    env = dict(os.environ, DOTNET_ReadyToRun='0')
    dotnet = RUNTIME/'dotnet/dotnet'
    subprocess.run([str(dotnet), str(RUNTIME/'compiler/DMCompiler.dll'), str(dme)], env=env, stdout=open(ROOT/'tests/mp-compile.log', 'w'), stderr=subprocess.STDOUT, check=True)
    hints = ROOT/'tests/mp-layout.json'; write_hints(arena/'skin.dmf', hints)
    cd = ROOT/'tests/client/Space Station 14.app/Contents/Resources'
    slp = ROOT/'tests/mp-server.log'
    procs = []
    probes = {}
    try:
        with tempfile.TemporaryDirectory(prefix='dm-mp-') as data:
            server = subprocess.Popen([str(dotnet), str(RUNTIME/'server/Robust.Server.dll'), '--data-dir', data,
                '--cvar', f'opendream.json_path={arena/"Cave Crawlers.json"}', '--cvar', 'opendream.topic_port=25683',
                '--cvar', f'log.path={ROOT/"tests/engine-logs"}', '--cvar', f'net.bindto={"0.0.0.0" if secured else "127.0.0.1"}', '--cvar', 'net.port=12233',
                '--cvar', 'auth.mode=0', '--cvar', 'status.enabled=false', '--cvar', 'hub.advertise=false', '--cvar', 'game.auto_pause_empty=false'],
                env=env, stdout=open(slp, 'w'), stderr=subprocess.STDOUT, cwd=arena)
            procs.append(server)
            wait(lambda: ' -> Ready' in slp.read_text(errors='replace'), 300)
            elog = arena/'ErrorLog.txt'
            log = lambda: (elog.read_text(errors='replace') if elog.exists() else '') + slp.read_text(errors='replace')
            def client(name, join, address='127.0.0.1', password=None):
                probe = ROOT/f'tests/mp-probe-{name}'
                if probe.exists(): shutil.rmtree(probe)
                probe.mkdir()
                probes[name] = probe
                cenv = dict(env, DM_SKIN_LAYOUT_HINTS=str(hints), DM_TEST_RACE='Orc', DM_TEST_JOIN='1' if join else '0',
                            DM_NATIVE_UI_PROBE=str(probe), DM_GAME_SNAPSHOT=str(probe/'game.png'), ROBUST_MODULE_ROBUST_CLIENT_WEBVIEW=str(ROOT/'engine/webview-webkit'))
                if password: cenv['DM_JOIN_PASSWORD'] = password
                p = subprocess.Popen([str(dotnet), str(cd/'Robust.Client.dll'), '--mount-zip', str(RUNTIME/'server/Content.Client.zip'), '--connect',
                    '--connect-address', f'udp://{address}:12233', '--username', name, '--self-contained', '--cvar', 'web.headless=false', '--cvar', 'discord.enabled=false'],
                    cwd=cd, env=cenv, stdout=open(ROOT/f'tests/mp-client-{name}.log', 'w'), stderr=subprocess.STDOUT)
                procs.append(p)
            client('Alice', False)
            print('alice open:', wait(lambda: 'MP|alice-open' in log(), 300))
            client('Bob', True, lan if secured else '127.0.0.1', 'test1234' if secured else None)
            got = wait(lambda: 'MP|request' in log(), 300)
            print('request:', got)
            if got:
                (probes['Alice']/'capture-web.txt').write_text('request')
                time.sleep(6)
            print('joined:', wait(lambda: 'MP|joined' in log(), 120))
            if secured:
                client('Eve', False, lan, 'nope')
                print('eve refused:', wait(lambda: 'Join refused' in log(), 240))
            if 'MP|joined' in log():
                time.sleep(4)
                (probes['Bob']/'capture-web.txt').write_text('bob')
                time.sleep(6)
    finally:
        for p in procs: stop(p)
    lines = re.findall(r'MP\|[^\r\n]*', log())
    print('\n'.join(dict.fromkeys(lines)))
    bob = open(ROOT/'tests/mp-client-Bob.log', errors='replace').read()
    print('bob prompt:', re.findall(r'answered the realm prompt[^\n]*', bob)[:1])
    m = re.search(r'MP\|joined\|people=(\d+)\|dist=(\d+)\|allied=(\d)\|pop=(\d+)', log())
    ok = bool(m) and int(m.group(1)) >= 3 and int(m.group(2)) <= 25 and m.group(3) == '1' and int(m.group(4)) >= 6
    if '--password' in sys.argv:
        bob_pw = 'answered the join password prompt' in bob
        refused = 'Join refused' in log()
        print('bob answered password:', bob_pw, '| eve refused:', refused)
        ok = ok and bob_pw and refused
    print('passed' if ok else 'FAILED')
    return 0 if ok else 1

if __name__ == '__main__':
    sys.exit(main())
