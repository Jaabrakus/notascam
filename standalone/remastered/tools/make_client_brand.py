#!/usr/bin/env python3
"""Remastered's own title screen and window icons, in place of OpenDream's.

The client's startup splash, window icons and first window title come from the
client package's manifest (splashLogo, windowIconSet, defaultWindowTitle). This
writes the art to art/brand/ and a copy of the shared client package with that
art and title to engine/client/Content.Client.zip, which build_app.py puts in
the app (the shared engine under replica/ is left as it is).
"""
import base64
import io
import json
import re
import subprocess
import zipfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT.parent/'replica/runtime/macos-x64/server/Content.Client.zip'
OUT = ROOT/'engine/client/Content.Client.zip'
ART = ROOT/'art/brand'
# The game's name: change it here (and LINE1/LINE2, the title's two lines), then run this and build_app.py.
NAME = 'Banners of the Deep: A Dungeon Master Tale'
LINE1, LINE2 = 'Banners of the Deep', 'A Dungeon Master Tale'
MONOGRAM = 'BD'
TITLE_FONT = '/System/Library/Fonts/Supplemental/Luminari.ttf'   # as the launcher art
GOLD, CREAM, INK = (242, 210, 122, 255), (238, 226, 196, 255), (20, 14, 6, 255)


def outlined(img, xy, text, font, fill, outline=3, shadow=5):
    """Text with a dark outline and a soft drop shadow, so it reads on any background."""
    w, h = img.size
    layer = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.text((xy[0] + shadow // 2, xy[1] + shadow), text, font=font, fill=(0, 0, 0, 170))
    layer = layer.filter(ImageFilter.GaussianBlur(shadow / 2))
    d = ImageDraw.Draw(layer)
    d.text(xy, text, font=font, fill=fill, stroke_width=outline, stroke_fill=INK)
    img.alpha_composite(layer)


def logo():
    big, small = ImageFont.truetype(TITLE_FONT, 92), ImageFont.truetype(TITLE_FONT, 46)
    w, h = max(820, int(big.getlength(LINE1)) + 80), 220   # wide enough for the whole name (cropped to the art below)
    img = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    t1, t2 = LINE1, LINE2
    b1, b2 = d.textbbox((0, 0), t1, font=big), d.textbbox((0, 0), t2, font=small)
    outlined(img, ((w - (b1[2] - b1[0])) // 2 - b1[0], 8 - b1[1]), t1, big, GOLD, outline=4)
    y2 = 8 + (b1[3] - b1[1]) + 26
    if not t2:
        ry = y2 + 6
        x0, x1 = (w - (b1[2] - b1[0])) // 2 + 40, (w + (b1[2] - b1[0])) // 2 - 40
        d.line((x0, ry, x1, ry), fill=(0, 0, 0, 200), width=5)
        d.line((x0, ry, x1, ry), fill=GOLD, width=2)
        return img.crop(img.getbbox()) if img.getbbox() else img
    x2 = (w - (b2[2] - b2[0])) // 2 - b2[0]
    outlined(img, (x2, y2 - b2[1]), t2, small, CREAM, outline=3)
    # a thin gold rule either side of "Remastered"
    ry = y2 + (b2[3] - b2[1]) // 2 + 4
    for a, b in ((x2 - 150, x2 - 24), (x2 + (b2[2] - b2[0]) + 24, x2 + (b2[2] - b2[0]) + 150)):
        d.line((a, ry, b, ry), fill=(0, 0, 0, 200), width=5)
        d.line((a, ry, b, ry), fill=GOLD, width=2)
    return img.crop(img.getbbox()) if img.getbbox() else img


# Texts the client shows while it connects, swapped for ones of exactly the same length (a .NET user string's
# length is fixed): only where the text is a whole string of its own, never inside a longer one. OpenDream's
# connecting screen ("Connecting...", "Work In Progress" and its logo) is emptied to plain black: the HUD's
# loading cover is the first thing the player sees. The logo's path points at a clear 1x1 picture (VOID_LOGO);
# the startup splash keeps the real logo through the manifest. The same texts and logo leave OpenDream's main menu,
# which shows only when a connection fails (its Address box and Connect button are kept, to retry).
# "OpenDream" is the title of a prompt window that has none of its own: left blank.
VOID_LOGO = 'OpenDream/Logo/void.png'
CLIENT_TEXTS = {'OpenDream': ' ' * 9, 'Work In Progress': ' ' * 16, 'Connecting... ': ' ' * 14,
                '/OpenDream/Logo/logo.png': '/' + VOID_LOGO}


# The client's start sets the window title to "OpenDream" (IoCManager.Resolve<IClyde>().SetWindowTitle("OpenDream");
# ret), over the manifest's title: those three instructions become no-ops, so the window keeps our title.
TITLE_CALL = bytes.fromhex('28 24 00 00 2b 72 3c 01 00 70 6f c9 00 00 0a 2a')


# The engine paints every browser control (the HUD's) white behind its web view: ControlBrowser.UpdateElementDescriptor,
# "_panel.PanelOverride = new StyleBoxFlat(Color.White)", a call of Color.get_White (0x0A0002C9) before the StyleBoxFlat
# constructor. Until the HUD page paints, that white shows as a blink; it becomes Color.get_Black (0x0A0000E6, the same
# signature), so the start is dark all the way from the connecting screen to the loading cover.
PANEL_WHITE = bytes.fromhex('28 C9 02 00 0A 73 E7 00 00 0A 6F E8 00 00 0A 2A')
PANEL_BLACK = bytes.fromhex('28 E6 00 00 0A 73 E7 00 00 0A 6F E8 00 00 0A 2A')


def swap_user_strings(data):
    assert data.count(TITLE_CALL) == 1, 'the client changed: look for its SetWindowTitle("OpenDream") again'
    data = data.replace(TITLE_CALL, bytes(len(TITLE_CALL) - 1) + b'\x2a')
    assert data.count(PANEL_WHITE) == 1, 'the client changed: look for ControlBrowser\'s white panel again'
    data = data.replace(PANEL_WHITE, PANEL_BLACK)
    for old, new in CLIENT_TEXTS.items():
        assert len(old) == len(new), (old, new)
        a, b = old.encode('utf-16-le'), new.encode('utf-16-le')
        prefix = bytes([2 * len(old) + 1])          # the #US heap entry's length byte
        assert data.count(prefix + a + b'\x00') + data.count(prefix + a + b'\x01') == 1, f'the client changed: look for {old!r} again'
        data = data.replace(prefix + a + b'\x00', prefix + b + b'\x00').replace(prefix + a + b'\x01', prefix + b + b'\x01')
    return data


def icon(size):
    """The monogram in gold on a dark stone square with a gold rim (drawn at 512 and scaled down)."""
    S = 512
    img = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((16, 16, S - 16, S - 16), radius=72, fill=(30, 26, 20, 255), outline=(0, 0, 0, 255), width=10)
    d.rounded_rectangle((44, 44, S - 44, S - 44), radius=56, outline=GOLD, width=14)
    mark = MONOGRAM if size >= 32 else MONOGRAM[0]     # the smallest icons: the first letter, big enough to read
    font = ImageFont.truetype(TITLE_FONT, 150 if len(mark) > 1 else 300)
    b = d.textbbox((0, 0), mark, font=font)
    d.text(((S - (b[2] - b[0])) // 2 - b[0], (S - (b[3] - b[1])) // 2 - b[1] - 6), mark, font=font, fill=GOLD, stroke_width=8 if len(mark) > 1 else 12, stroke_fill=INK)
    return img.resize((size, size), Image.LANCZOS)


def main():
    ART.mkdir(parents=True, exist_ok=True)
    files = {'OpenDream/Logo/logo.png': logo(), VOID_LOGO: Image.new('RGBA', (1, 1), (0, 0, 0, 0))}
    for n in (16, 24, 32, 48, 64, 128, 256):
        files[f'OpenDream/Logo/icon/icon-{n}x{n}.png'] = icon(n)
    for path, img in files.items():
        img.save(ART/Path(path).name)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT.with_suffix('.zip.pending')
    with zipfile.ZipFile(SOURCE) as src, zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as dst:
        for info in src.infolist():
            data = src.read(info.filename)
            if info.filename in files:
                continue
            if info.filename == 'Assemblies/OpenDreamClient.dll':
                data = swap_user_strings(data)
            if info.filename == 'manifest.yml':
                # quoted: the name has a colon, which unquoted YAML reads as a new key (the client then fails to start)
                data = data.decode().replace('defaultWindowTitle: OpenDream', 'defaultWindowTitle: ' + json.dumps(NAME)).encode()
            dst.writestr(info, data)
        for path in files:
            dst.write(ART/Path(path).name, path)
    tmp.replace(OUT)
    # the app's icon (Finder and the Dock): an .icns from the same art (macOS iconutil)
    iconset = ART/'AppIcon.iconset'
    iconset.mkdir(exist_ok=True)
    for n in (16, 32, 128, 256, 512):
        icon(n).save(iconset/f'icon_{n}x{n}.png')
        icon(n * 2).save(iconset/f'icon_{n}x{n}@2x.png')
    subprocess.run(['/usr/bin/iconutil', '-c', 'icns', str(iconset), '-o', str(ART/'AppIcon.icns')], check=True)
    # the HUD page's loading cover shows the same title, embedded so it is there before anything else loads
    page = ROOT/'game/Interface/remastered.html'
    small = files['OpenDream/Logo/logo.png']
    small = small.resize((600, round(small.height * 600 / small.width)), Image.LANCZOS)
    buf = io.BytesIO(); small.save(buf, 'PNG', optimize=True)
    html = page.read_text(encoding='utf-8')
    html, n = re.subn(r'(id="bootlogo" alt="" src="data:image/png;base64,)[^"]*"', lambda m: m.group(1) + base64.b64encode(buf.getvalue()).decode() + '"', html)
    if n == 1: page.write_text(html, encoding='utf-8')
    print('loading cover logo', 'updated' if n == 1 else 'NOT FOUND in remastered.html')
    # the Mac launcher's art (mac-app/launcher-art.png): the old title painted into the picture is darkened away
    # and the new one drawn in its place; the untouched original is kept in art/brand
    original = ART/'launcher-art-original.png'
    if not original.exists(): (ROOT/'mac-app/launcher-art.png').replace(original) if False else original.write_bytes((ROOT/'mac-app/launcher-art.png').read_bytes())
    art = Image.open(original).convert('RGBA')
    W, H = art.size
    top = art.crop((0, 0, W, 440)).filter(ImageFilter.GaussianBlur(28))    # smear the old lettering into the land,
    fade = Image.new('L', (W, 440), 255)                                     # fading back to the sharp picture below
    fd = ImageDraw.Draw(fade)
    for y in range(340, 440): fd.line((0, y, W, y), fill=int(255 * (440 - y) / 100))
    art.paste(top, (0, 0), fade)
    band = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    bd = ImageDraw.Draw(band)
    for y in range(0, 400):
        a = 225 if y < 330 else int(225 * (400 - y) / 70)
        bd.line((0, y, W, y), fill=(10, 8, 6, a))
    art.alpha_composite(band)
    t = files['OpenDream/Logo/logo.png']
    t = t.resize((int(t.width * 1.6), int(t.height * 1.6)), Image.LANCZOS)
    art.alpha_composite(t, ((W - t.width) // 2, 70))
    art.convert('RGB').save(ROOT/'mac-app/launcher-art.png')
    print('wrote', OUT.relative_to(ROOT), 'and', len(files), 'images in', ART.relative_to(ROOT))


if __name__ == '__main__':
    main()
