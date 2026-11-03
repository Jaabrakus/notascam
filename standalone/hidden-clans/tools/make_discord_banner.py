#!/usr/bin/env python3
"""The Discord profile banner for Banners of the Deep (680x240, drawn at 2x): dark stone with a gold rim, the app
icon's banner emblem on the left, the title and subtitle in the brand's Luminari gold. Writes
art/brand/discord-banner-1360x480.png. The name comes from make_client_brand.py (LINE1, LINE2)."""
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from make_client_brand import LINE1, LINE2, TITLE_FONT, GOLD, CREAM, outlined  # noqa: E402
W, H = 1360, 480
img = Image.new('RGBA', (W, H))
d = ImageDraw.Draw(img)
for y in range(H):
    t = y / H
    d.line((0, y, W, y), fill=(int(46 - 24 * t), int(38 - 20 * t), int(28 - 16 * t), 255))
glow = Image.new('RGBA', (W, H), (0, 0, 0, 0))   # warm light behind the title
ImageDraw.Draw(glow).ellipse((380, 40, 1300, 440), fill=(150, 100, 40, 70))
img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(90)))
d = ImageDraw.Draw(img)
d.rectangle((10, 10, W - 11, H - 11), outline=(14, 10, 6, 255), width=8)
d.rectangle((26, 26, W - 27, H - 27), outline=GOLD, width=6)
# the emblem: the app icon's banner, without its square
icon = Image.open(ROOT/'art/brand/discord-app-icon-1024.png').convert('RGBA')
emblem = icon.crop((210, 150, 815, 870)).resize((300, 357), Image.LANCZOS)
img.alpha_composite(emblem, (90, 62))
x0 = 420
size = 104   # the largest title that fits between the emblem and the rim
while ImageFont.truetype(TITLE_FONT, size).getlength(LINE1) > W - x0 - 90: size -= 2
big, small = ImageFont.truetype(TITLE_FONT, size), ImageFont.truetype(TITLE_FONT, 48)
b1 = d.textbbox((0, 0), LINE1, font=big); b2 = d.textbbox((0, 0), LINE2, font=small)
cx = x0 + (W - 50 - x0) // 2
outlined(img, (cx - (b1[2] - b1[0]) // 2 - b1[0], 150 - b1[1]), LINE1, big, GOLD, outline=5)
y2 = 150 + (b1[3] - b1[1]) + 40
x2 = cx - (b2[2] - b2[0]) // 2 - b2[0]
outlined(img, (x2, y2 - b2[1]), LINE2, small, CREAM, outline=3)
d = ImageDraw.Draw(img)
ry = y2 + (b2[3] - b2[1]) // 2 + 2
for a, b in ((x2 - 120, x2 - 24), (x2 + (b2[2] - b2[0]) + 24, x2 + (b2[2] - b2[0]) + 120)):
    d.line((a, ry, b, ry), fill=(0, 0, 0, 200), width=6)
    d.line((a, ry, b, ry), fill=GOLD, width=3)
out = ROOT/'art/brand/discord-banner-1360x480.png'
img.convert('RGB').save(out, optimize=True)
print('wrote', out.relative_to(ROOT))
