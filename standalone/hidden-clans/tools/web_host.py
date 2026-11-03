#!/usr/bin/env python3
"""Let friends play Banners of the Deep in a web browser (planning/WEB_CLIENT.md).

Since 2026-10-30 the world itself serves browsers (the engine's web link, U4: reports/u4-web-1030): the app's "Host
for friends" starts its world with the link on port 8080, and a friend opens http://<this Mac>:8080/, types a name and
answers the world's password. No client runs on this Mac for them.

    python3 tools/web_host.py                      # the hosted world's browser address(es), once the app hosts
    python3 tools/web_host.py --private-world      # a throw-away world with the link on (testing; the browser pane)
    python3 tools/web_host.py --relay [...]        # the old way: a headless relay client per player (planning/WEB_CLIENT.md)

Ports: the web link's (--port, 8080), or with --relay the lobby's and one per player from --player-ports
(12200-12299). Friends elsewhere reach them through Tailscale or a port forward, like native joining.
"""
import argparse, html, json, os, re, secrets, shutil, signal, socket, subprocess, sys, tempfile, threading, time, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT/'Hidden Clans.app'   # Hidden Clans (copied from Banners 11-01)
APP_RUNTIME = APP/'Contents/Resources/game/runtime'
APP_GAME = APP/'Contents/Resources/game/world'
REPLICA_RUNTIME = ROOT.parent/'replica/runtime/macos-x64'
RELAY = ROOT/'engine/webview-relay'
NAME_OK = re.compile(r'^[A-Za-z0-9_]{1,24}$')


def runtime():
    return APP_RUNTIME if (APP_RUNTIME/'dotnet/dotnet').exists() else REPLICA_RUNTIME


def client_zip():
    for candidate in (runtime()/'server/Content.Client.zip', ROOT/'engine/client/Content.Client.zip'):
        if candidate.exists():
            return candidate
    sys.exit('Content.Client.zip not found; build the app first (tools/build_app.py).')


def host_addresses():
    """This Mac's addresses friends can use: Wi-Fi/Ethernet first, then Tailscale (100.x), else localhost."""
    found = []
    for interface in ('en0', 'en1', 'en2', 'en3'):
        result = subprocess.run(['/usr/sbin/ipconfig', 'getifaddr', interface], capture_output=True, text=True)
        address = result.stdout.strip()
        if address and address not in found:
            found.append(address)
    ifconfig = subprocess.run(['/sbin/ifconfig'], capture_output=True, text=True).stdout
    for match in re.finditer(r'inet (100\.(?:6[4-9]|[7-9]\d|1[01]\d|12[0-7])\.\d+\.\d+)', ifconfig):
        if match.group(1) not in found:
            found.append(match.group(1) + '  (Tailscale)')
    return found or ['localhost']


def world_listening(port):
    """Whether a game server has the UDP port (the app's "Host for friends")."""
    result = subprocess.run(['/usr/sbin/lsof', '-nP', f'-iUDP:{port}'], capture_output=True, text=True)
    return f':{port}' in result.stdout


def free_port(candidates, taken):
    for port in candidates:
        if port in taken:
            continue
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                probe.bind(('0.0.0.0', port))
            except OSError:
                continue
        return port
    return None


class Player:
    def __init__(self, name, port, process, folder):
        self.name, self.port, self.process, self.folder = name, port, process, folder
        self.started = time.time()


class Host:
    def __init__(self, args):
        self.args = args
        self.players = {}
        self.lock = threading.Lock()
        self.rt = runtime()
        self.dotnet = self.rt/'dotnet/dotnet'
        self.logs = ROOT/'reports/web-host'
        self.logs.mkdir(parents=True, exist_ok=True)
        self.server = None
        self.world = None
        self.private_log = self.logs/f'private-server-{args.port}.log'   # by port: two private worlds never share one
        lo, hi = (int(x) for x in args.player_ports.split('-'))
        self.ports = range(lo, hi + 1)
        if args.relay:
            self.zip = client_zip()
            if not (RELAY/'Robust.Client.WebView.dll').exists():
                sys.exit('engine/webview-relay is missing; run tools/build_web_relay.py first.')

    # -- a private world for testing --------------------------------------------------
    def start_private_world(self):
        # The current source build when it has been compiled (tools/build_app.py), else the app's world.
        game = Path(self.args.world) if self.args.world else ROOT/'game' if (ROOT/'game/Cave Crawlers.json').exists() else APP_GAME   # --world: a test copy (a scene compiled in)
        self.world = Path(tempfile.mkdtemp(prefix='dm-web-world-'))
        for name in ('Cave Crawlers.json', 'skin.dmf', 'Interface', 'Icons', 'Sounds', 'Maps', 'Host Files'):
            source = game/name
            if source.is_dir():
                shutil.copytree(source, self.world/name)
            elif source.exists():
                shutil.copy2(source, self.world/name)
        # every other file the compiled game lists (icons kept under Code/, Tomb.bmp at the top): without them icon() of
        # one fails, "Value cannot be null (Parameter 'buffer')", hair, food and dead bodies among them (10-31)
        try:
            for rel in json.loads((game/'Cave Crawlers.json').read_text()).get('Resources', []):
                source, target = game/rel, self.world/rel
                if source.is_file() and not target.exists():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, target)
        except (OSError, ValueError) as error:
            print(f"The world's own files were not all copied: {error}", flush=True)
        if self.args.password:
            (self.world/'join-password').write_text(self.args.password)
            (self.world/'host-name').write_text('web-host')
        log = self.private_log.open('w')
        # the world's own web link (engine/web), as the app's "Host for friends" starts it (mac-app/launch.zsh)
        web = {} if self.args.relay else web_env(self.args)
        rt = self.private_runtime()
        # the server natively on Apple silicon when the app has it, as mac-app/launch.zsh does (load-asleep-1030, 10-31)
        arm = (os.uname().machine == 'arm64' and os.environ.get('RM_ARM64_SERVER', '1') != '0' and
               (rt/'dotnet-arm64/dotnet').exists() and (rt/'server-arm64/Robust.Server.dll').exists())
        dotnet, server_dir = (rt/'dotnet-arm64/dotnet', rt/'server-arm64') if arm else (rt/'dotnet/dotnet', rt/'server')
        self.server = subprocess.Popen([str(dotnet), str(server_dir/'Robust.Server.dll'), '--data-dir', str(self.world/'server-data'),
                                        '--cvar', f'opendream.json_path={self.world/"Cave Crawlers.json"}', '--cvar', 'net.bindto=127.0.0.1',
                                        '--cvar', f'net.port={self.args.game_port}', '--cvar', f'opendream.topic_port={self.args.game_port + 13500}',
                                        '--cvar', f'log.path={self.logs/"private-engine-logs"}', '--cvar', 'net.max_connections=16', '--cvar', 'status.enabled=false',
                                        '--cvar', 'hub.advertise=false', '--cvar', 'auth.mode=0', '--cvar', 'game.auto_pause_empty=false'],
                                       # the app's GC settings (mac-app/launch.zsh): workstation GC, compacting when the heap fills with free room
                                       cwd=self.world, env=dict(os.environ, DOTNET_ReadyToRun='1', DOTNET_TieredPGO='0', DOTNET_gcServer='0', DOTNET_GCConserveMemory='5',
                                                DOTNET_GCLOHThreshold='0x400000', DOTNET_SYSTEM_BUFFERS_SHAREDARRAYPOOL_MAXPARTITIONCOUNT='2',
                                                DOTNET_SYSTEM_BUFFERS_SHAREDARRAYPOOL_MAXARRAYSPERPARTITION='8', **web), stdout=log, stderr=subprocess.STDOUT)   # as launch.zsh (load-asleep-1030)
        for _ in range(180):
            if self.server.poll() is not None:
                sys.exit(f'The private world stopped; see {self.private_log}')
            if ' -> Ready' in self.private_log.read_text(errors='replace'):
                print(f'Private world ready on 127.0.0.1:{self.args.game_port}')
                return
            time.sleep(1)
        sys.exit('The private world did not start in time.')

    def private_runtime(self):
        """The app's runtime, with the installed engine (engine/server) in a copy when it differs from the app's build:
        the private world runs today's engine as it runs today's game/."""
        engine = Path(os.environ.get('RM_ENGINE_DLL') or ROOT/'engine/server/OpenDreamRuntime.dll')   # RM_ENGINE_DLL: a test build instead
        dll = self.rt/'server/Resources/Assemblies/OpenDreamRuntime.dll'
        if not engine.exists() or (dll.exists() and engine.read_bytes() == dll.read_bytes()):
            return self.rt
        copy = self.world/'runtime'
        shutil.copytree(self.rt, copy, symlinks=True, ignore=shutil.ignore_patterns('client'))
        shutil.copy2(engine, copy/'server/Resources/Assemblies/OpenDreamRuntime.dll')
        print("Private world on the installed engine (engine/server), which the app's build doesn't have yet")
        return copy

    # -- players ------------------------------------------------------------------------
    def join(self, name, password):
        with self.lock:
            self.reap()
            if name in self.players:
                return self.players[name].port, None
            port = free_port(self.ports, {p.port for p in self.players.values()})
            if port is None:
                return None, 'The world is full right now.'
            folder = Path(tempfile.mkdtemp(prefix=f'dm-web-{name}-'))
            shutil.copytree(self.rt/'client', folder/'client', ignore=shutil.ignore_patterns('user_data', '.DS_Store'))
            resources = folder/'client/Space Station 14.app/Contents/Resources'
            env = dict(os.environ, DOTNET_ReadyToRun='1', DOTNET_TieredPGO='0', ROBUST_MODULE_ROBUST_CLIENT_WEBVIEW=str(RELAY), DM_WEB_RELAY_PORT=str(port),
                       DM_WEB_RELAY_BIND=self.args.bind, DM_WEB_RELAY_IDLE=str(self.args.idle))
            if password:
                env['DM_JOIN_PASSWORD'] = password
            log = (self.logs/f'{name}.log').open('w')
            process = subprocess.Popen([str(self.dotnet), str(resources/'Robust.Client.dll'), '--headless', '--mount-zip', str(self.zip), '--connect',
                                        '--connect-address', f'udp://127.0.0.1:{self.args.game_port}', '--username', name, '--self-contained',
                                        '--cvar', 'discord.enabled=false', '--cvar', 'res.texturepreloadingenabled=false'],   # no GL to preload into
                                       cwd=resources, env=env, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT)
            self.players[name] = Player(name, port, process, folder)
            print(f'{name} joins on port {port} (pid {process.pid})')
            return port, None

    def wait_listening(self, name, port, seconds=90):
        """The browser is sent to the player's port only once the relay answers there."""
        deadline = time.time() + seconds
        while time.time() < deadline:
            with self.lock:
                player = self.players.get(name)
                if player is None or player.process.poll() is not None:
                    return False
            try:
                with socket.create_connection(('127.0.0.1', port), timeout=0.5):
                    return True
            except OSError:
                time.sleep(0.5)
        return False

    def reap(self):
        for name, player in list(self.players.items()):
            if player.process.poll() is not None:
                print(f'{name} left (exit {player.process.returncode})')
                shutil.rmtree(player.folder, ignore_errors=True)
                del self.players[name]

    def stop(self):
        with self.lock:
            for player in self.players.values():
                player.process.terminate()
            for player in self.players.values():
                try:
                    player.process.wait(10)
                except subprocess.TimeoutExpired:
                    player.process.kill()
                shutil.rmtree(player.folder, ignore_errors=True)
            self.players.clear()
        if self.server:
            self.server.send_signal(signal.SIGINT)
            try:
                self.server.wait(15)
            except subprocess.TimeoutExpired:
                self.server.kill()
        if self.world:
            shutil.rmtree(self.world, ignore_errors=True)


def web_env(args):
    """The world's web link settings (engine/web/RmWebServer.cs), as mac-app/launch.zsh sets them when hosting."""
    env = dict(RM_WEB_PORT=str(args.port), RM_WEB_PAGE='mapwindow.hud', RM_WEB_BIND=args.bind)
    if args.secret_file:
        env['RM_WEB_SECRET_FILE'] = str(Path(args.secret_file).resolve())   # sign-in links only (tools/web_token.py)
    elif args.bind not in ('127.0.0.1', 'localhost'):
        env['RM_WEB_OPEN'] = '1'   # a typed name, and the world's own password when it has one (as Host for friends)
    return env


def web_answers(port):
    """Whether a world's web link answers on this Mac."""
    try:
        with urllib.request.urlopen(f'http://127.0.0.1:{port}/health', timeout=2) as reply:
            return reply.read() == b'ok'
    except OSError:
        return False


def print_addresses(args, port, private):
    print()
    print('Hidden Clans — Host on the Web')
    print('=' * 60)
    if args.bind in ('127.0.0.1', 'localhost'):
        print(f'Open: http://127.0.0.1:{port}/?overlay   (this Mac only)')
    else:
        for address in host_addresses():
            print(f'Friends open:  http://{address.split()[0]}:{port}/?overlay' + ('  (Tailscale)' if 'Tailscale' in address else ''))
    if args.secret_file:
        print('Sign-in is on: give each friend a link from tools/web_token.py.')
    else:
        print('They type a name' + ('' if private and not args.password else ', then the world\'s password') + '. The same name brings them back to their people.')
    print('Keep this window open while friends play. Ctrl+C stops the world.' if private else
          'The world serves them while the app hosts it: this window can close.')
    print('=' * 60)


LOBBY = """<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Kin &amp; Stone</title>
<style>html,body{{height:100%;margin:0;background:#141210;color:#e8dcc0;font:16px/1.5 Georgia,serif}}
main{{min-height:100%;display:flex;align-items:center;justify-content:center;padding:16px;box-sizing:border-box}}
form{{background:#1d1a16;border:1px solid #6b5a3a;border-radius:10px;padding:24px 28px;width:100%;max-width:360px;box-shadow:0 10px 40px rgba(0,0,0,.6)}}
h1{{font-weight:normal;letter-spacing:.08em;margin:0 0 4px;font-size:26px}}p{{margin:0 0 18px;opacity:.75;font-size:14px}}
label{{display:block;font-size:13px;opacity:.8;margin:12px 0 4px}}input{{width:100%;box-sizing:border-box;background:#0f0d0b;color:#eee3c8;border:1px solid #6b5a3a;border-radius:5px;padding:9px 10px;font:inherit}}
button{{margin-top:20px;width:100%;background:#4a3a22;color:#f3e9d2;border:1px solid #8a7446;border-radius:5px;padding:10px;font:inherit;font-size:17px;cursor:pointer}}button:hover{{background:#5d4a2b}}
.err{{color:#f0a0a0;margin:12px 0 0;font-size:14px}}</style></head><body><main>
<form method="post" action="/join"><h1>Kin &amp; Stone</h1><p>The Deepholds &middot; play in your browser</p>
<label>Your name</label><input name="name" required maxlength="24" pattern="[A-Za-z0-9_]+" autocomplete="username" value="{name}">
<label>World password</label><input name="password" type="password" autocomplete="current-password">
{error}<button>Enter the world</button></form></main></body></html>"""


class Lobby(BaseHTTPRequestHandler):
    host: Host

    def log_message(self, fmt, *args):
        pass

    def page(self, status, body):
        data = body.encode()
        self.send_response(status)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = urlparse(self.path).path
        if path in ('/', '/index.html'):
            return self.page(200, LOBBY.format(name='', error=''))
        if path == '/health':
            with self.host.lock:
                self.host.reap()
                count = len(self.host.players)
            data = f'ok players={count}'.encode()
            self.send_response(200); self.send_header('Content-Type', 'text/plain'); self.send_header('Content-Length', str(len(data))); self.end_headers(); self.wfile.write(data)
            return
        self.page(404, LOBBY.format(name='', error='<p class="err">Not found.</p>'))

    def do_POST(self):
        if urlparse(self.path).path != '/join':
            return self.page(404, LOBBY.format(name='', error='<p class="err">Not found.</p>'))
        length = int(self.headers.get('Content-Length') or 0)
        form = parse_qs(self.rfile.read(min(length, 4096)).decode(errors='replace'))
        name = (form.get('name') or [''])[0].strip()
        password = (form.get('password') or [''])[0]
        if not NAME_OK.match(name):
            return self.page(400, LOBBY.format(name=html.escape(name), error='<p class="err">Names use letters, digits and _ only (up to 24).</p>'))
        port, error = self.host.join(name, password)
        if not error and not self.host.wait_listening(name, port):
            error = 'Your game client did not start. Ask the host to look at reports/web-host.'
        if error:
            return self.page(503, LOBBY.format(name=html.escape(name), error=f'<p class="err">{html.escape(error)}</p>'))
        here = (self.headers.get('Host') or 'localhost').rsplit(':', 1)[0]
        self.send_response(303)
        self.send_header('Location', f'http://{here}:{port}/')
        self.send_header('Content-Length', '0')
        self.end_headers()


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--port', type=int, default=8080, help="the world's web link port (default 8080, the app's), or with --relay the lobby page's")
    parser.add_argument('--bind', default='*', help='interfaces for the lobby and player ports: * (default, all) or 127.0.0.1')
    parser.add_argument('--game-port', type=int, default=12151, help="the hosted world's port (default 12151, the app's)")
    parser.add_argument('--player-ports', default='12200-12299', help='ports given to players (default 12200-12299)')
    parser.add_argument('--idle', type=int, default=90, help="seconds a player's client waits for a closed browser before quitting")
    parser.add_argument('--private-world', action='store_true', help='start a throw-away world here instead of joining the app\'s hosted one')
    parser.add_argument('--password', default='', help='with --private-world: the join password (empty = none)')
    parser.add_argument('--world', default='', help='with --private-world: the game folder to run (its Cave Crawlers.json, Interface...) instead of game/')
    parser.add_argument('--secret-file', default='', help='with --private-world: sign-in links only (the secret tools/web_token.py made)')
    parser.add_argument('--relay', action='store_true', help='the old way: a headless relay client per player (engine/webview-relay)')
    args = parser.parse_args()
    if not args.relay and not args.private_world:
        # the app's hosted world serves browsers itself (an app built after 2026-10-30 22:4x)
        if web_answers(args.port):
            print_addresses(args, args.port, private=False)
            return
        print(f'Nothing answers on port {args.port} for browsers.')
        print('In the app, choose "Host for friends" (an app built after 2026-10-30 has the browser link on) and run this again,')
        print('or use the old way for an older app: python3 tools/web_host.py --relay')
        sys.exit(1)
    host = Host(args)
    def on_term(*_):
        raise KeyboardInterrupt   # a plain kill still stops the players' clients and the private world
    signal.signal(signal.SIGTERM, on_term)
    if args.private_world:
        if args.game_port == 12151:
            args.game_port = 12161
        host.start_private_world()
        if not args.relay:
            if not web_answers(args.port):
                host.stop()
                sys.exit(f'The private world started, but its web link does not answer on port {args.port} (see {host.private_log}).')
            print_addresses(args, args.port, private=True)
            try:
                while host.server.poll() is None:
                    time.sleep(1)
            except KeyboardInterrupt:
                pass
            finally:
                print('Stopping…')
                host.stop()
            return
    Lobby.host = host
    bind = '' if args.bind == '*' else args.bind
    lobby = None
    for port in range(args.port, args.port + 10):
        try:
            lobby = ThreadingHTTPServer((bind, port), Lobby)
            break
        except OSError:
            print(f'Port {port} is busy, trying the next one.')
    if lobby is None:
        sys.exit(f'No free port from {args.port} to {args.port + 9}.')
    print()
    print('Kin & Stone — Host on the Web')
    print('=' * 60)
    if bind:
        print(f'Lobby: http://{args.bind}:{port}/')
    else:
        for address in host_addresses():
            print(f'Friends open:  http://{address}:{port}/')
    print(f'World: 127.0.0.1:{args.game_port}' + ('' if world_listening(args.game_port) else
          '   <- nothing is hosting there yet: in the app, choose "Host for friends"'))
    print('Keep this window open while friends play. Ctrl+C stops the lobby and their clients.')
    print('=' * 60)
    try:
        lobby.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        print('Stopping…')
        lobby.server_close()
        host.stop()


if __name__ == '__main__':
    main()
