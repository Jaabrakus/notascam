#!/usr/bin/env python3
"""Compile a throw-away copy of game/ with the DM compiler, so a DM edit can be checked without touching the shared
game/Cave Crawlers.json (rts-feel, overnight polish 2026-10-22). Prints the error and warning lines; exit 1 on errors."""
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RT = ROOT.parent/'replica/runtime/macos-x64'
with tempfile.TemporaryDirectory(prefix='rf-compile-') as tmp:
    w = Path(tmp)/'world'
    shutil.copytree(ROOT/'game', w, ignore=shutil.ignore_patterns('Cave Crawlers.json', 'ErrorLog.txt', 'units', 'players', '*.log'))
    env = dict(os.environ, DOTNET_ReadyToRun='0')
    r = subprocess.run([str(RT/'dotnet/dotnet'), str(RT/'compiler/DMCompiler.dll'), str(w/'Cave Crawlers.dme')], env=env, capture_output=True, text=True)
    out = r.stdout + r.stderr
    errs = [l for l in out.splitlines() if re.search(r'\berror\b', l, re.I)]
    for l in errs[:40]:
        print(l)
    tail = [l for l in out.splitlines() if 'Compilation' in l or 'errors' in l.lower()]
    print('\n'.join(tail[-3:]) or out[-600:])
    ok = r.returncode == 0 and (w/'Cave Crawlers.json').exists()
    print('COMPILE OK' if ok else 'COMPILE FAILED')
    sys.exit(0 if ok else 1)
