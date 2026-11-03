#!/usr/bin/env python3
"""The server's own CPU time per phase of an arena test, so other load on the Mac doesn't count (world.cpu is wall time):
watches the server log for CK|mark|<name>|start / CK|mark|<name>|end lines as they appear and reads the server process's
CPU time (ps) at each.

    python3 tools/rts_feel/wild/cpu_marks.py --port 25897 --log tests/wild-bench3-server.log --out marks.json

Run it beside tools/check_arena.py (same --port). Prints, per phase, CPU ms a second of wall time."""
import argparse
import json
import re
import subprocess
import time
from pathlib import Path


def cputime(pid):
    out = subprocess.run(['ps', '-o', 'time=', '-p', str(pid)], capture_output=True, text=True).stdout.strip()
    if not out: return None
    parts = out.split(':')   # [[dd-]hh:]mm:ss.cc
    secs = 0.0
    for p in parts:
        if '-' in p:
            d, p = p.split('-')
            secs += int(d) * 86400
        secs = secs * 60 + float(p)
    return secs


def server_pid(port):
    out = subprocess.run(['pgrep', '-f', f'net.port={port}'], capture_output=True, text=True).stdout.split()
    for pid in out:
        cmd = subprocess.run(['ps', '-o', 'command=', '-p', pid], capture_output=True, text=True).stdout
        if 'Robust.Server' in cmd: return int(pid)
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--port', type=int, required=True)
    ap.add_argument('--log', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--timeout', type=float, default=1800)
    a = ap.parse_args()
    log = Path(a.log)
    deadline = time.monotonic() + a.timeout
    pid = None
    seen = 0
    marks = []
    while time.monotonic() < deadline:
        if pid is None: pid = server_pid(a.port)
        if log.exists():
            text = log.read_text(errors='replace')
            if len(text) > seen:
                for m in re.finditer(r'CK\|mark\|([^|\r\n]+)\|(start|end)', text[seen:]):
                    c = cputime(pid) if pid else None
                    marks.append(dict(name=m.group(1), at=m.group(2), wall=time.monotonic(), cpu=c))
                seen = len(text)
            if 'CK|complete' in text: break
        if pid and cputime(pid) is None and marks: break
        time.sleep(0.05)
    Path(a.out).write_text(json.dumps(marks, indent=1))
    starts = {}
    for m in marks:
        if m['at'] == 'start': starts[m['name']] = m
        elif m['name'] in starts and m['cpu'] is not None and starts[m['name']]['cpu'] is not None:
            s = starts.pop(m['name'])
            wall = m['wall'] - s['wall']
            print(f"{m['name']:<40} {1000 * (m['cpu'] - s['cpu']) / wall:8.1f} CPU ms/s over {wall:5.1f} s")


if __name__ == '__main__':
    main()
