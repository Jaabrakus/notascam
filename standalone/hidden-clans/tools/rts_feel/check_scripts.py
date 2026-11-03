#!/usr/bin/env python3
"""node --check every <script> block of remastered.html (house rule after each edit)."""
import re, subprocess, sys, tempfile, os
from pathlib import Path
p = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parents[2]/'game/Interface/remastered.html')
bad = 0
for i, b in enumerate(re.findall(r'<script>(.*?)</script>', p.read_text(encoding='utf-8'), flags=re.S)):
    f = tempfile.NamedTemporaryFile('w', suffix='.js', delete=False); f.write(b); f.close()
    r = subprocess.run(['node', '--check', f.name], capture_output=True, text=True); os.unlink(f.name)
    print(i, len(b), 'ok' if r.returncode == 0 else r.stderr[:600]); bad += r.returncode != 0
sys.exit(1 if bad else 0)
