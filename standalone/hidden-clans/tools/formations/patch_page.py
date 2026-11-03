#!/usr/bin/env python3
"""Put the formations block (tools/formations/fm_module.js: slot markers for group moves) into remastered.html, or a
copy of it. Idempotent: the block between its marker and its </script> is replaced; a new one goes just before the
page's last script (the one that asks for the first model: WebKit stops reading the page there, so nothing after it
ever runs in the game), after rts-feel's block, whose rfClick and rfDraw it wraps.
  python3 tools/formations/patch_page.py [PAGE] [MODULE]"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
START = '<script>\n/* Formations (2026-10-23, formations)'
END_TAG = '</script>\n'
READY = '<script>\n// The browser requests its first model only after every script'
RF = '<script>\n/* RTS feel (overnight polish 2026-10-22, rts-feel)'


def patch(html, module):
    if START in html:
        i = html.index(START)
        j = html.index(END_TAG, i) + len(END_TAG)
        return html[:i] + module + html[j:]
    if html.count(READY) != 1:
        raise SystemExit('the ready script was not found once')
    if RF in html and html.index(RF) > html.index(READY):
        raise SystemExit("rts-feel's block is after the ready script")
    return html.replace(READY, module + READY)


if __name__ == '__main__':
    page = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT/'game/Interface/remastered.html'
    mod = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT/'tools/formations/fm_module.js'
    module = mod.read_text(encoding='utf-8')
    if not module.endswith('\n'):
        module += '\n'
    assert module.startswith(START), 'module must start with its marker'
    # never put a script that doesn't parse into the shared page
    import subprocess, tempfile
    with tempfile.NamedTemporaryFile('w', suffix='.js', delete=False) as f:
        f.write(module[len('<script>\n'):module.rindex('</script>')])
    r = subprocess.run(['node', '--check', f.name], capture_output=True, text=True)
    Path(f.name).unlink()
    if r.returncode:
        raise SystemExit('the module does not parse; the page is left as it was:\n' + r.stderr[-1500:])
    page.write_text(patch(page.read_text(encoding='utf-8'), module), encoding='utf-8')
    print('patched', page)
