"""Which engine a behaviour check runs on, and at what game speed (tools/check_care.py, check_doctor.py, check_food.py,
check_stumps.py, check_combat.py; the coordinator, 2026-10-24: "the engine players run is the one these checks should
prove", and the user: "when we run test turn it all on to speed 4").

    --engine app      (default) the app's runtime: Remastered's own engine, with the game clock (engine/server)
    --engine replica  the replica's runtime, the 1:1 reference, used read-only (no game clock: always speed 1)
    --speed N         world.game_state = N when the world starts (app engine only; default 4), so the game-time waits
                      take a quarter of the real time. Above 4 (up to 32) the server gets RM_MAX_SPEED=N (engine v5.1),
                      so the clock runs as fast as each tick leaves time for. Logged: the game seconds the check took, the real seconds from
                      the world's start, and how far behind real time the game fell (0 when the server kept up).

The compiler is the replica's either way (the app ships none); it is the same compiler the app's game is built with."""
from pathlib import Path
import os
import re
import time

ROOT = Path(__file__).resolve().parents[1]
# RM_CHECK_RUNTIME=DIR runs the checks on another runtime folder (a copy of the app's with a test engine in it)
APP_RUNTIME = Path(os.environ['RM_CHECK_RUNTIME']) if os.environ.get('RM_CHECK_RUNTIME') else ROOT/'Dungeon Master Remastered.app/Contents/Resources/game/runtime'
REPLICA_RUNTIME = ROOT.parent/'replica/runtime/macos-x64'
COMPILER = REPLICA_RUNTIME/'compiler/DMCompiler.dll'


def add_args(parser):
    parser.add_argument('--engine', choices=['app', 'replica'], default='app', help="the app's engine (default) or the replica's (the 1:1 reference)")
    parser.add_argument('--speed', type=int, default=4, help='game speed on the app engine (world.game_state; default 4, 1 for timing)')
    parser.add_argument('--label', help='names its arena, logs and results file (tests/<label>-...), so two runs at once never share them')


def free_port(kind='udp'):
    """A port nothing holds right now (net.port is UDP, opendream.topic_port TCP), so copies of a check never clash."""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM if kind == 'udp' else socket.SOCK_STREAM) as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def free_port_pair(offset=13500):
    """A UDP port P (net.port) with TCP P + offset free too (opendream.topic_port, as check_combat.run_world sets it)."""
    import random, socket
    for _ in range(500):
        p = random.randrange(20000, 50000)
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as a, socket.socket(socket.AF_INET, socket.SOCK_STREAM) as b:
                a.bind(('127.0.0.1', p)); b.bind(('127.0.0.1', p + offset))
            return p
        except OSError:
            continue
    raise RuntimeError('no free port pair')


def parse(doc=None):
    import argparse
    p = argparse.ArgumentParser(description=doc)
    add_args(p)
    return p.parse_args()


def engine(args):
    """The engine asked for; the app's when a caller has no arguments (a harness that imports run_world from check_combat)."""
    return getattr(args, 'engine', None) or 'app'


def runtime(args):
    speed(args)
    return APP_RUNTIME if engine(args) == 'app' else REPLICA_RUNTIME


def speed(args):
    """The game speed: --speed on the app engine; 1 on the replica's, or when a caller has no arguments (it sets none)."""
    if args is None or engine(args) != 'app': return 1
    s = min(32, max(1, getattr(args, 'speed', 1) or 1))
    if s > 4: os.environ['RM_MAX_SPEED'] = str(s)   # above play's 4 (engine v5.1); the servers the checks start inherit it
    return s


def world_new(entry, args):
    """World.dm's New() for a check: the speed, a game-time log every 5 game seconds, then the check's own proc. Put it in
    place of the original New() (up to the next top-level line): the logger proc ends the world block."""
    s = speed(args)
    return ('\tNew()\n' + (f'\t\tgame_state = {s}\n' if s != 1 else '') +
            f'\t\tspawn(0) RmCheckClock()\n\t\tspawn(0) {entry}()\n'
            'proc/RmCheckClock()   // tools/check_engine.py: the game time, for how far behind real time a sped-up check fell\n'
            '\twhile(1)\n\t\tworld.log << "CHECKCLOCK|[world.time]"\n\t\tsleep(50)\n')


def mark(log_path, t_world):
    """Called in a check's wait loop: the moment the world started (its first CHECKCLOCK line), once."""
    if t_world is None and 'CHECKCLOCK|' in Path(log_path).read_text(errors='replace'): return time.monotonic()
    return t_world


def report(log_text, args, t_world, t_end):
    """The game seconds, real seconds and seconds behind, as a dict for the check's JSON and a line to print."""
    ticks = [float(x) for x in re.findall(r'CHECKCLOCK\|([0-9.]+)', log_text)]
    game_s = (max(ticks) / 10) if ticks else 0.0
    real_s = (t_end - t_world) if t_world else 0.0
    s = speed(args)
    e = engine(args)
    if not ticks or not t_world:   # a world without the game-time log (a harness that doesn't use world_new): not measured
        return dict(engine=e, speed=s, game_seconds=None, real_seconds=None, seconds_behind=None), f'engine {e}, speed {s} (game time not logged)'
    behind = max(0.0, real_s - game_s / s)
    d = dict(engine=e, speed=s, game_seconds=round(game_s, 1), real_seconds=round(real_s, 1), seconds_behind=round(behind, 1))
    return d, f"engine {e}, speed {s}: {game_s:.0f} game s in {real_s:.0f} real s ({behind:.1f} s behind)"
