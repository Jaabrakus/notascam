#!/usr/bin/env python3
"""Run a command while holding the shared app lock, so builds, app checks and real-client runs don't trip over
each other.

    python3 tools/runlock.py --who hud-craft -- python3 tools/build_app.py                 # a build: alone
    python3 tools/runlock.py --who qa -- python3 tools/check_app.py ...                     # real input: one at a time
    python3 tools/runlock.py --who world-look --kind run -- python3 tools/check_beasts_native.py   # up to 3 at once

Kinds (--kind; build_app.py is always "build" and check_app.py "input"):
  build  rebuilds the app or its runtime. Runs alone, and first waits until no other build_app.py / check_app.py /
         DungeonMasterRemastered process has run for --quiet seconds (a build under a running client stalls it, and
         sessions that don't use this lock still build).
  input  (the default) anything that moves the real pointer or sends keys, or brings a window to the front to drive
         it: check_app.py, real-input probes, tools/trailer/*, tools/click_audit/*. One at a time (two steal each
         other's clicks) and after quiet like a build, but beside the runs: those never touch the pointer. Needs
         INPUT_FREE_GB free. Holds nobody off.
  alone  a timing run that needs the Mac to itself (frame time, latency at speed 1 on a real client): runs alone like a
         build.
  run    a game client or server that never touches the real pointer or keyboard: arena servers, no-input 3D probes
         (tools/check_beasts_native.py style), headless checks that launch the runtime. Up to --slots of these at
         once, more while memory allows. They never wait for an input run, and wait for a build or alone run only
         in its priority windows (it has waited ALONE_PRIORITY_AFTER; windows of PRIORITY_WINDOW with gaps as long).
         The user, 2026-10-24: "tell everyone to not wait for anyone if your test is ready go".
         Pick ports that can't clash with another copy of the same check.
The holders and their commands are kept in .app.lock.who (alone) and .app.lock.who.<slot> (runs) while they run.
Exit status is the command's.
"""
import argparse
import fcntl
import os
import re
import subprocess
import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
LOCK = BASE/'.app.lock'            # alone kinds hold it exclusively, runs share it
WHO = BASE/'.app.lock.who'
WAITING = BASE/'.app.lock.waiting'  # touched every few seconds by an alone kind waiting its turn
WAITING_SINCE = BASE/'.app.lock.waiting.since'  # when the oldest alone kind still waiting began (epoch seconds)
BUILD_WAITING = BASE/'.app.lock.buildwait'  # touched every few seconds by a build waiting its turn: new runs hold off at once
ALONE_PRIORITY_AFTER = 10 * 60     # after this long an alone kind gets its drain even past a long run (no starving; builds are rare)
PRIORITY_WINDOW = 20 * 60          # ...in windows this long, with gaps as long between, so an hour-long run can't stall all runs
BUILD_HOLD_ALL_AFTER = 30 * 60     # ...but once it has waited this long, runs hold off without gaps until it's in
SLOTS = 4                          # always allowed (user, 2026-10-25 15:0x: "every test that is suppose to run run it it takes to long"; was 3)
MAX_SLOTS = 7                      # slots 5-7 only while enough memory is free (arena servers are 50-250 MB; a stress
MIN_FREE_GB = 3.0                  # world is GBs, so a fixed higher count could swap the Mac) (coordinator, 2026-10-24)
INPUT_LOCK = BASE/'.app.lock.input'  # one input run at a time
INPUT_QUEUE = BASE/'.app.lock.inputq'  # ...taken first come, first served (a ticket per waiting input run)
INPUT_FREE_GB = 4.0                # a real client and its world beside the runs
# A landing's gate runs while its lander holds the land lock (.land.lock), so every other landing waits on it: its runs
# get two slots of their own past MAX_SLOTS and skip the queue (owner, 2026-10-27: "these things have been stalling for
# hours... please find a better pipeline"; a gate's compile waited 32 min behind 32 queued runs)
LAND_WHO = BASE/'.land.lock'/'who'
PRIORITY_SLOTS = (8, 9)
PER_WHO = 3                        # runs one --who may hold at once (a fixer that queued 16 took every slot)
RUN_QUEUE = BASE/'.app.lock.runq'  # run waiters, first come first served (a ticket each)
# bracketed first letters so pgrep never matches its own command line
OTHERS = '[b]uild_app.py|[c]heck_app.py'
# the app itself, matched by process name: a shell or guard script that only names it in its text is not the game
APP_NAMES = ('BannersOfTheDeep', 'LandOfLords', 'LandsOfLords', 'DungeonMasterRemastered')


def ancestors():
    # this process and every process above it (caffeinate, the shell that started it...): never "another build"
    out, pid = set(), os.getpid()
    while pid > 1 and pid not in out:
        out.add(pid)
        r = subprocess.run(['ps', '-o', 'ppid=', '-p', str(pid)], capture_output=True, text=True).stdout.strip()
        pid = int(r) if r.isdigit() else 0
    return out


def others_running():
    out = subprocess.run(['pgrep', '-fl', OTHERS], capture_output=True, text=True).stdout
    # A command line with newlines in it (a shell heredoc) prints as several lines, only the first with the pid: join them.
    procs = []
    for l in out.splitlines():
        if l.split() and l.split()[0].isdigit(): procs.append([int(l.split()[0]), l])
        elif procs: procs[-1][1] += ' ' + l
    mine = ancestors()
    # a shell or runlock still waiting for this lock names its command too ("runlock.py ... build_app.py"): it is not
    # running yet, and waiting for it while holding the lock deadlocks both (audio, 23:20); nor is the shell that
    # started this runlock (it waited for itself, 00:30)
    # nor is a "sh -c ..." wrapper, such as a session's watcher whose text only names build_app.py (pgrep -f "build_app.py"
    # in an until-loop deadlocked the 12:0x build, 2026-10-25): a real build or check is its own python process, matched too
    procs = [p for p in procs if not re.match(r'\d+\s+(/bin/)?(zsh|bash|sh)\s+-c\b', p[1])]
    for name in APP_NAMES:
        for pid in subprocess.run(['pgrep', '-x', name], capture_output=True, text=True).stdout.split():
            procs.append([int(pid), f'{pid} {name} (the app)'])
    return [l[:200] for pid, l in procs if pid not in mine and 'runlock.py' not in l]


def holders():
    files = [WHO] + sorted(BASE.glob('.app.lock.who.*'))
    return '; '.join(f.read_text().strip() for f in files if f.exists()) or '?'


def note(text, waited):
    if waited % 60 == 0: print('runlock: ' + text, flush=True)


# windowless tests: with no --kind given they share a run slot. A mislabeled one queued as input held every other run
# off behind a long run (coordinator, 2026-10-24 18:40)
HEADLESS = ('check_arena.py', 'check_jobs.py', 'check_clip.py', 'check_obey.py', 'check_formation.py', 'check_breaking.py',
            'headless_slots.py', 'compile_check.py')


def kind_of(a, cmd):
    line = ' '.join(cmd)
    if 'build_app.py' in line: return 'build'
    if 'check_app.py' in line: return 'input'
    # a scratch engine build (build_runtime into a folder that isn't engine/server) shares: it touches neither the engine
    # nor the app; asked as build it idled eight runs (map-memory, 19:43)
    if a.kind == 'build' and 'build_runtime' in line and 'engine/server' not in line: return 'run'
    if a.kind: return a.kind
    if any(h in line for h in HEADLESS) and '--client real' not in line: return 'run'
    return 'input'


def waiting_since():
    try: return float(WAITING_SINCE.read_text().strip())
    except (OSError, ValueError): return None


def take_alone(fd, quiet, build=False):
    waited = 0
    s = waiting_since()
    if s is None or time.time() - s > 6 * 3600: WAITING_SINCE.write_text(str(time.time()))
    while True:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            break
        except BlockingIOError:
            WAITING.touch()          # runs hold off while an alone kind waits, so it isn't starved
            if build: BUILD_WAITING.touch()
            note(f'waiting for: {holders()}', waited)
            time.sleep(5)
            waited += 5
    quiet_since = time.time()
    while time.time() - quiet_since < quiet:
        busy = others_running()
        if busy:
            note('waiting for ' + '; '.join(busy)[:300], waited)
            quiet_since = time.time()
            if build: BUILD_WAITING.touch()
        time.sleep(5)
        waited += 5
    WAITING.unlink(missing_ok=True)
    WAITING_SINCE.unlink(missing_ok=True)
    if build: BUILD_WAITING.unlink(missing_ok=True)
    return WHO


def build_holding():
    # runs and input runs hold off for a build or alone run only in its priority windows (never for the user's own game:
    # the user, 2026-10-24: "dont pause the other test keep them active the question is how can we make the game run
    # good on a loaded computer")
    # a waiting app build: new runs hold off at once, the running ones finish (the user, 2026-10-25: "just go if it needs
    # to be built run it")
    try:
        if time.time() - BUILD_WAITING.stat().st_mtime < 20: return True
    except OSError:
        pass
    s = waiting_since()
    over = time.time() - s - ALONE_PRIORITY_AFTER if s is not None else -1
    # once it has waited BUILD_HOLD_ALL_AFTER, no more gaps: new runs wait until it's in (2026-10-25: a build the user was
    # waiting for sat 30+ min behind a chain, and the 11:58 gap let three new runs in ahead of it)
    return WAITING.exists() and time.time() - WAITING.stat().st_mtime < 20 and over > 0 and \
        (int(over // PRIORITY_WINDOW) % 2 == 0 or over + ALONE_PRIORITY_AFTER >= BUILD_HOLD_ALL_AFTER)


def input_turn(ticket):
    # first come, first served among input runs (2026-10-25: flock picks at random, and a run queued at 12:43 waited
    # 26+ min while later ones went in); a waiter whose process is gone doesn't count
    live = []
    for t in INPUT_QUEUE.glob('*'):
        try:
            os.kill(int(t.name.split('-')[1]), 0)
            live.append(t.name)
        except PermissionError:
            live.append(t.name)          # alive, someone else's
        except (ValueError, IndexError, ProcessLookupError):
            try: t.unlink()
            except OSError: pass
    return not live or min(live, key=lambda n: float(n.split('-')[0])) == ticket.name


def take_input(fd, quiet):
    ifd = os.open(INPUT_LOCK, os.O_CREAT | os.O_RDWR, 0o644)
    INPUT_QUEUE.mkdir(exist_ok=True)
    ticket = INPUT_QUEUE/f'{time.time():.3f}-{os.getpid()}'
    ticket.touch()
    waited = 0
    while True:
        if not input_turn(ticket):
            note('waiting for input runs queued earlier', waited)
            time.sleep(5)
            waited += 5
            continue
        try:
            fcntl.flock(ifd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            note(f'waiting for the other input run: {holders()}', waited)
        else:
            if build_holding():
                note('a build is in its priority window; letting it go first', waited)
            elif free_gb() < INPUT_FREE_GB:
                note(f'waiting for {INPUT_FREE_GB:.0f} GB free (free {free_gb():.1f} GB)', waited)
            else:
                try:
                    fcntl.flock(fd, fcntl.LOCK_SH | fcntl.LOCK_NB)
                    try: ticket.unlink()
                    except OSError: pass
                    break
                except BlockingIOError:
                    note(f'waiting for: {holders()}', waited)
            fcntl.flock(ifd, fcntl.LOCK_UN)
        time.sleep(5)
        waited += 5
    quiet_since = time.time()
    while time.time() - quiet_since < quiet:
        busy = others_running()
        if busy:
            note('waiting for ' + '; '.join(busy)[:300], waited)
            quiet_since = time.time()
        time.sleep(5)
        waited += 5
    return BASE/'.app.lock.who.input', ifd


def free_gb():
    # free + inactive + purgeable pages: what a new run can get without swapping
    try:
        out = subprocess.run(['vm_stat'], capture_output=True, text=True).stdout
    except OSError:
        return 0.0
    vals = {}
    for l in out.splitlines():
        if ':' in l:
            k, v = l.split(':', 1)
            vals[k.strip()] = v.strip().rstrip('.')
    page = 16384
    n = sum(int(vals.get(k, '0') or 0) for k in ('Pages free', 'Pages inactive', 'Pages purgeable'))
    return n * page / 1073741824


def slots_now(slots):
    # the fixed slots, plus extra ones up to MAX_SLOTS while memory allows
    if slots != SLOTS: return slots        # an explicit --slots wins
    return MAX_SLOTS if free_gb() >= MIN_FREE_GB else SLOTS


def landing_gate():
    # a run started (at any depth) by the process holding the land lock, or asked for with RUNLOCK_PRIORITY=1
    if os.environ.get('RUNLOCK_PRIORITY') == '1': return True
    try:
        m = re.search(r'\bpid (\d+)', LAND_WHO.read_text())
    except OSError:
        return False
    return bool(m) and int(m.group(1)) in ancestors()


def live_tickets(queue):
    live = []
    for t in queue.glob('*'):
        try:
            os.kill(int(t.name.split('-')[1]), 0)
            live.append(t.name)
        except PermissionError:
            live.append(t.name)
        except (ValueError, IndexError, ProcessLookupError):
            try: t.unlink()
            except OSError: pass
    return sorted(live, key=lambda n: float(n.split('-')[0]))


def held_counts():
    # --who -> run slots it holds now
    n = {}
    for f in BASE.glob('.app.lock.who.*'):
        try:
            w = f.read_text().split(' (', 1)[0]
        except OSError:
            continue
        n[w] = n.get(w, 0) + 1
    return n


def my_turn(ticket, n_slots):
    # first come, first served among run waiters, skipping those whose --who already holds PER_WHO slots (they would
    # only block the queue's head)
    held = held_counts()
    eligible = []
    for name in live_tickets(RUN_QUEUE):
        try:
            w = (RUN_QUEUE/name).read_text().strip()
        except OSError:
            continue
        if held.get(w, 0) < PER_WHO: eligible.append(name)
    return ticket.name in eligible[:n_slots]


def input_waiting():
    # a window check (input run) is queued; a dead waiter doesn't count
    for t in INPUT_QUEUE.glob('*'):
        try:
            os.kill(int(t.name.split('-')[1]), 0)
            return True
        except PermissionError:
            return True
        except (ValueError, IndexError, ProcessLookupError):
            pass
    return False


def take_slot(fd, slots, who='?'):
    waited = 0
    gate = landing_gate()
    ticket = None
    if not gate:
        RUN_QUEUE.mkdir(exist_ok=True)
        ticket = RUN_QUEUE/f'{time.time():.3f}-{os.getpid()}'
        ticket.write_text(who)
    while True:
        n_slots = slots_now(slots)
        order = list(range(1, n_slots + 1))
        if gate:
            order = list(PRIORITY_SLOTS) + order
        elif held_counts().get(who, 0) >= PER_WHO:
            note(f'{who} already holds {PER_WHO} run slots; waiting for one of them', waited)
            time.sleep(5)
            waited += 5
            continue
        elif input_waiting() and free_gb() < INPUT_FREE_GB + 1:
            # 2026-10-27 14:36: build 83's launch check waited 9+ min for 4 GB while new duel runs kept taking the memory
            note(f'a window check is waiting for {INPUT_FREE_GB:.0f} GB (free {free_gb():.1f} GB); letting it go first', waited)
            time.sleep(5)
            waited += 5
            continue
        elif not my_turn(ticket, n_slots):
            note(f'queued behind earlier runs (all {n_slots} run slots busy: {holders()})', waited)
            time.sleep(5)
            waited += 5
            continue
        if not build_holding():
            try:
                fcntl.flock(fd, fcntl.LOCK_SH | fcntl.LOCK_NB)
                for k in order:
                    sfd = os.open(BASE/f'.app.lock.slot{k}', os.O_CREAT | os.O_RDWR, 0o644)
                    try:
                        fcntl.flock(sfd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                        if ticket is not None:
                            try: ticket.unlink()
                            except OSError: pass
                        return BASE/f'.app.lock.who.{k}', sfd   # the slot's fd stays open while the command runs
                    except BlockingIOError:
                        os.close(sfd)
                fcntl.flock(fd, fcntl.LOCK_UN)
                note(f'all {n_slots} run slots busy (free {free_gb():.1f} GB): {holders()}', waited)
            except BlockingIOError:
                note(f'waiting for: {holders()}', waited)
        else:
            note('a build is in its priority window; letting it go first', waited)
        time.sleep(5)
        waited += 5


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--who', required=True, help='short name of the session holding the lock')
    ap.add_argument('--kind', choices=['build', 'input', 'alone', 'run'], default=None,
                    help='build / alone run alone; input (real pointer or keys, the default) one at a time beside the '
                         'runs; run (no real input) shares; known windowless tests (HEADLESS) default to run')
    ap.add_argument('--quiet', type=int, default=30, help='build/input: seconds with no other build/check/app process first')
    ap.add_argument('--slots', type=int, default=SLOTS, help='run: how many may run at once')
    ap.add_argument('cmd', nargs=argparse.REMAINDER)
    a = ap.parse_args()
    cmd = a.cmd[1:] if a.cmd[:1] == ['--'] else a.cmd
    if not cmd:
        ap.error('no command given')
    kind = kind_of(a, cmd)
    fd = os.open(LOCK, os.O_CREAT | os.O_RDWR, 0o644)
    sfd = None
    if kind == 'run':
        who, sfd = take_slot(fd, max(1, a.slots), a.who)
    elif kind == 'input':
        who, sfd = take_input(fd, a.quiet)
    elif kind == 'build' and 'build_runtime' not in ' '.join(cmd):
        # an app build (an engine build still waits, below: the runs use engine/server) doesn't wait for the arena runs to drain (they run on their own game copies and never read the
        # app), only for another build; the owner, 2026-10-27: "if we need to focus all cores on one thing then do it to
        # zip it faster" after a build sat behind a 30-minute village round
        bfd = os.open(BASE/'.app.lock.buildonly', os.O_CREAT | os.O_RDWR, 0o644)
        waited = 0
        while True:
            try:
                fcntl.flock(bfd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                note(f'waiting for the other build: {holders()}', waited)
                time.sleep(5)
                waited += 5
        who = WHO
    else:
        who = take_alone(fd, a.quiet, build=False)
    who.write_text(f'{a.who} ({kind}) pid {os.getpid()} since {time.strftime("%H:%M:%S")}: {" ".join(cmd)[:200]}\n')
    try:
        return subprocess.call(cmd)
    finally:
        who.unlink(missing_ok=True)
        if sfd is not None:
            fcntl.flock(sfd, fcntl.LOCK_UN)
            os.close(sfd)
        fcntl.flock(fd, fcntl.LOCK_UN)


if __name__ == '__main__':
    sys.exit(main())
