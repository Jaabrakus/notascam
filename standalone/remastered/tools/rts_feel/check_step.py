#!/usr/bin/env python3
"""--test station: a click on a workshop walks the unit beside it, then opens the menu (tests/rts_station_test.dm).
Order → first step, and the steady step rhythm, in a private mapless arena (tests/rts_step_test.dm), at the game's
own 10 ticks a second (rts-feel, 2026-10-22). No client, no lock needed.
  python3 tools/rts_feel/check_step.py [--label rts-step] [--game PATH]"""
import argparse
import re
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'tools'))
from check_combat import run_world

ap = argparse.ArgumentParser()
ap.add_argument('--label', default='rts-step')
ap.add_argument('--game', type=Path, default=ROOT/'game')
ap.add_argument('--port', type=int, default=12421)
ap.add_argument('--test', default='step', choices=['step', 'station', 'idle'])
a = ap.parse_args()
with tempfile.TemporaryDirectory(prefix='rf-step-') as tmp:
    arena = Path(tmp)/'world'
    shutil.copytree(a.game, arena, ignore=shutil.ignore_patterns('Cave Crawlers.json', '*.dmm', '*.sav', 'ErrorLog.txt', 'units', 'saves', 'players'))
    dme = re.sub(r'^#include .*\.dmm"\s*$', '', (arena/'Cave Crawlers.dme').read_text(encoding='latin-1'), flags=re.M)
    world = arena/'Code/World.dm'
    src = world.read_text(encoding='latin-1')
    start = src.index('\tNew()'); end = src.index('\nvar/Season', start)
    world.write_text(src[:start] + '\tNew()\n\t\tspawn(0) %s()\n' % {'step': 'RfStepRun', 'station': 'RfStnRun', 'idle': 'RfIdleRun'}[a.test] + src[end:], encoding='latin-1')
    test = {'step': 'rts_step_test.dm', 'station': 'rts_station_test.dm', 'idle': 'rts_idle_cost_test.dm'}[a.test]
    shutil.copy2(ROOT/'tests'/test, arena/test)
    fixture = arena/'rts_step.dme'
    fixture.write_text(dme + '\n#include "%s"\n' % test, encoding='latin-1')
    ok = run_world(arena, fixture, a.label, 300, prefix={'step': 'RFSTEP', 'station': 'RFSTN', 'idle': 'RFIDLE'}[a.test], port=a.port)
import resource
ru = resource.getrusage(resource.RUSAGE_CHILDREN)
print('children cpu seconds', round(ru.ru_utime + ru.ru_stime, 1))
raise SystemExit(0 if ok else 1)
