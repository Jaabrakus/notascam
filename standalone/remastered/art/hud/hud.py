"""The HUD page from its sources, the way art/gear3d/install.py makes gear3d.js (cleanup step 2, staged 2026-10-26).

game/Interface/remastered.html stays one file: the app loads it, Gear3D.dm / Audio.dm / HudPack.dm fill its
<!--rm-gear3d--> / <!--rm-audio--> / <!--rm-hudpack--> markers when it is sent, and ~76 tools read it directly. Its
sources are here, in src/: the page cut at its own edges (each <style> and <script> block, the main script at its
"// =====" section headers, the boot cover, a style line over 8 KB) with the boot logo as a .png. Joining them gives the
page back byte for byte.

  python3 hud.py split  [--page PAGE] [--src SRC]   cut the page into SRC (refuses unless SRC joins back to PAGE)
  python3 hud.py build  [--check]                   join SRC into the page (--check: compare only, exit 1 if different)
  python3 hud.py adopt                              the page was patched in game/ (a land script): re-split it into src/,
                                                    when src/ holds no edits that were never built; refuses otherwise
  python3 hud.py status                             exit 0 when src/ joins to the page byte for byte

PAGE defaults to $HUD_GAME_DIR/Interface/remastered.html (HUD_GAME_DIR: a clone of game/ to test first) or game/'s.
SRC defaults to src/ beside this script. Edit the sources, then build; or patch the page, then adopt. Never both."""
import argparse
import base64
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]                       # standalone/remastered when this file is art/hud/hud.py
GAME = Path(os.environ.get('HUD_GAME_DIR') or ROOT/'game')
PAGE = GAME/'Interface'/'remastered.html'
SRC = HERE/'src'
STAMP = 'built.sha256'                       # in SRC: the page this src/ last built or was split from
ASSET = re.compile(rb'data:image/png;base64,([A-Za-z0-9+/=]{4096,})')
MARK = b'@@hud-asset:%s@@'
BIG_STYLE_LINE = 8000


def sha(b): return hashlib.sha256(b).hexdigest()


def slug(text):
    s = re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')
    return s[:40].rstrip('-') or 'part'


def cut(page):
    """[(name, bytes)]: the page in pieces whose concatenation is the page."""
    lines = page.splitlines(keepends=True)
    parts = []
    cur = {'kind': 'html', 'name': 'page', 'lines': []}

    def start(kind, name):
        nonlocal cur
        if cur['lines']: parts.append(cur)
        cur = {'kind': kind, 'name': name, 'lines': []}

    block = None   # b'script' or b'style' while inside one
    for line in lines:
        if block is None:
            m = re.match(rb'<(script|style)\b', line)
            if m:
                tag = m.group(1)
                closes = (b'</' + tag + b'>') in line
                if line.rstrip(b'\r\n') in (b'<script>', b'<style>'):       # the opener alone: it stays with the html
                    cur['lines'].append(line)
                    start('js' if tag == b'script' else 'css', 'script' if tag == b'script' else 'style')
                    block = tag
                elif closes:                                                 # a one-line block
                    start('html', 'inline-' + tag.decode())
                    cur['lines'].append(line)
                    start('html', 'page')
                else:                                                        # an opener with code after it
                    start('html', tag.decode() + '-open')
                    cur['lines'].append(line)
                    block = tag
                continue
            if line.startswith(b'<div id="bootcover"'):
                start('html', 'bootcover')
                cur['lines'].append(line)
                start('html', 'page')
                continue
            cur['lines'].append(line)
            continue
        if line.startswith(b'</' + block):
            start('html', 'page')
            cur['lines'].append(line)
            block = None
            continue
        if block == b'script' and line.startswith(b'// ====='):
            title = line.decode('utf-8', 'replace').strip('/ =\r\n')
            start('js', title)
            cur['lines'].append(line)
            continue
        if block == b'style' and len(line) > BIG_STYLE_LINE:
            start('css', 'style-big')
            cur['lines'].append(line)
            start('css', 'style')
            continue
        cur['lines'].append(line)
    if cur['lines']: parts.append(cur)
    out = []
    for i, p in enumerate(parts):
        ext = {'html': 'html', 'js': 'js', 'css': 'css'}[p['kind']]
        out.append((f'{i:03d}-{slug(p["name"])}.{ext}', b''.join(p['lines'])))
    return out


def split(page_path, src):
    page = page_path.read_bytes()
    pieces = cut(page)
    if b''.join(b for _, b in pieces) != page: raise SystemExit('refused: the cut pieces do not add up to the page')
    if re.search(rb'@@hud-asset:', page): raise SystemExit('refused: the page already holds an asset marker')
    tmp = Path(tempfile.mkdtemp(prefix='hud-src-'))
    (tmp/'assets').mkdir()
    manifest = {'page_sha256': sha(page), 'parts': [], 'assets': []}
    n = 0
    for name, body in pieces:
        def keep(m):
            nonlocal n
            b64 = m.group(1)
            raw = base64.b64decode(b64)
            if base64.b64encode(raw) != b64: return m.group(0)     # not canonical: left inline, so the join stays exact
            n += 1
            asset = f'assets/{Path(name).stem}-{n}.png'
            (tmp/asset).write_bytes(raw)
            manifest['assets'].append({'file': asset, 'sha256': sha(raw)})
            return b'data:image/png;base64,' + MARK % asset.encode()
        body2 = ASSET.sub(keep, body)
        (tmp/name).write_bytes(body2)
        manifest['parts'].append({'file': name, 'sha256': sha(body2)})
    (tmp/'manifest.json').write_text(json.dumps(manifest, indent=1) + '\n')
    (tmp/STAMP).write_text(sha(page) + '\n')
    if join(tmp) != page: raise SystemExit('refused: the sources do not join back to the page byte for byte')
    if src.exists():
        trash = Path.home()/'.Trash'/f'hud-src-{time.strftime("%Y%m%d-%H%M%S")}'
        shutil.move(str(src), str(trash))                             # the old sources to the Trash, never deleted
        print('old sources moved to', trash)
    shutil.move(str(tmp), str(src))
    print(f'split {page_path} ({len(page)} bytes) into {len(manifest["parts"])} parts and {len(manifest["assets"])} assets in {src}')


def join(src):
    m = json.loads((src/'manifest.json').read_text())
    out = []
    for p in m['parts']:
        body = (src/p['file']).read_bytes()
        body = re.sub(rb'@@hud-asset:([^@]+)@@', lambda a: base64.b64encode((src/a.group(1).decode()).read_bytes()), body)
        out.append(body)
    return b''.join(out)


def write(path, data):
    tmp = path.with_name(path.name + '.hud.tmp')
    tmp.write_bytes(data)
    if path.exists(): os.chmod(tmp, path.stat().st_mode & 0o777)
    os.replace(tmp, path)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('cmd', choices=['split', 'build', 'adopt', 'status'])
    ap.add_argument('--page', type=Path, default=PAGE)
    ap.add_argument('--src', type=Path, default=SRC)
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    if a.cmd == 'split':
        split(a.page, a.src)
        return
    joined = join(a.src)
    page = a.page.read_bytes()
    stamp = (a.src/STAMP).read_text().strip() if (a.src/STAMP).exists() else ''
    if a.cmd == 'status':
        if joined == page: print('ok: src joins to the page'); return
        src_moved, page_moved = sha(joined) != stamp, sha(page) != stamp
        why = ('src has edits not built (run: hud.py build)' if src_moved and not page_moved else
               'the page was patched in game/ (run: hud.py adopt)' if page_moved and not src_moved else
               'both src and the page changed since the last build: merge by hand')
        print('DIFFERENT:', why)
        sys.exit(1)
    if a.cmd == 'build':
        if joined == page: print('already built'); return
        if a.check: print('DIFFERENT: src does not join to the page'); sys.exit(1)
        if sha(page) != stamp: raise SystemExit('refused: the page was patched in game/ since the last build; adopt it first')
        write(a.page, joined)
        (a.src/STAMP).write_text(sha(joined) + '\n')
        print('built', a.page, len(joined), 'bytes')
        return
    if a.cmd == 'adopt':
        if joined == page: print('nothing to adopt: src already joins to the page'); return
        if sha(joined) != stamp: raise SystemExit('refused: src holds edits that were never built, and the page changed too: merge by hand')
        split(a.page, a.src)


if __name__ == '__main__':
    main()
