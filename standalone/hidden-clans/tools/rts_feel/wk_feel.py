#!/usr/bin/env python3
"""The rts-feel functional check in a real WKWebView (the game's HUD engine), not headless Chrome: the page as the
server sends it (audio.js inserted at its marker), a lairs scene and HUD model (headless_feel.py --dump), synthetic
input from tools/rts_feel/wk_driver.js; prints script errors and the result. No game, no lock needed.
  python3 tools/rts_feel/wk_feel.py [--html PAGE]   (default: game/Interface/remastered.html)"""
import argparse, json, os, subprocess, tempfile
from pathlib import Path
BASE = Path(__file__).resolve().parents[2]; RFT = Path(__file__).resolve().parent
ap = argparse.ArgumentParser(); ap.add_argument('--html', type=Path, default=BASE/'game/Interface/remastered.html'); A = ap.parse_args()
with tempfile.TemporaryDirectory(prefix='rf-wk-') as tmp:
    tmp = Path(tmp)
    subprocess.run(['swiftc', '-O', str(RFT/'wkcheck.swift'), '-o', str(tmp/'wkcheck')], check=True, capture_output=True)
    subprocess.run(['python3', str(RFT/'headless_feel.py')], env=dict(os.environ, RF_DUMP=str(tmp/'rft_data.js')), check=True)
    h = A.html.read_text(encoding='utf-8')
    a = (BASE/'game/Interface/audio.js').read_text(encoding='utf-8') if (BASE/'game/Interface/audio.js').exists() else ''
    h = h.replace('<!--rm-audio-->', '<script>' + a + '</script>')
    # commands are recorded instead of navigating; the driver runs after every script, before the ready request
    h = h.replace('<head>', "<head><script>Object.defineProperty(window,'__nav',{set(v){(window.__navs=window.__navs||[]).push(v)}})</script>", 1)
    h = h.replace('window.location.href=', 'window.__nav=')
    k = "<script>\n// The browser requests its first model only after every script"
    assert h.count(k) == 1
    h = h.replace(k, '<script src="rft_data.js"></script><script>' + (RFT/'wk_driver.js').read_text() + '</script>' + k)
    (tmp/'page.html').write_text(h, encoding='utf-8')
    r = subprocess.run([str(tmp/'wkcheck'), str(tmp/'page.html'), 'window.RFT_OUT||"no result"', '9'], capture_output=True, text=True, env=dict(os.environ, WK_SHOW='1'), timeout=120)
    print(r.stdout[-4000:], r.stderr[-1000:])
