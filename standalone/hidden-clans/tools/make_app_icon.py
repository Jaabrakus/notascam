from PIL import Image, ImageDraw, ImageFilter
import sys
N = 1024; K = 4; W = N * K           # drawn 4x and scaled down for smooth edges
GOLD, GOLD_D, INK = (242, 210, 122, 255), (176, 138, 62, 255), (14, 10, 6, 255)
CRIMSON, CRIMSON_D = (128, 24, 30, 255), (84, 14, 20, 255)
def s(v): return int(v * K)
img = Image.new('RGBA', (W, W), (0, 0, 0, 0))
# stone background: a vertical gradient in a rounded square, gold rim
bg = Image.new('RGBA', (W, W))
gd = ImageDraw.Draw(bg)
for y in range(W):
    t = y / W
    gd.line((0, y, W, y), fill=(int(44 - 22 * t), int(37 - 19 * t), int(28 - 15 * t), 255))
mask = Image.new('L', (W, W), 0)
ImageDraw.Draw(mask).rounded_rectangle((s(24), s(24), W - s(24), W - s(24)), radius=s(150), fill=255)
img.paste(bg, (0, 0), mask)
d = ImageDraw.Draw(img)
d.rounded_rectangle((s(24), s(24), W - s(24), W - s(24)), radius=s(150), outline=INK, width=s(14))
d.rounded_rectangle((s(62), s(62), W - s(62), W - s(62)), radius=s(116), outline=GOLD, width=s(16))
# the pole, with finials
d.rounded_rectangle((s(250), s(176), s(774), s(206)), radius=s(15), fill=GOLD, outline=INK, width=s(6))
for cx in (s(250), s(774)):
    d.ellipse((cx - s(30), s(161), cx + s(30), s(221)), fill=GOLD, outline=INK, width=s(6))
# the banner: swallowtail cloth with a gold border and a soft shadow
L, R, T, B, V = 300, 724, 200, 846, 724      # left, right, top, tail bottom, the V's inner point
cloth = [(s(L), s(T)), (s(R), s(T)), (s(R), s(B)), (s(512), s(V)), (s(L), s(B))]
shadow = Image.new('RGBA', (W, W), (0, 0, 0, 0))
ImageDraw.Draw(shadow).polygon([(x + s(14), y + s(18)) for x, y in cloth], fill=(0, 0, 0, 150))
img.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(s(14))))
d = ImageDraw.Draw(img)
d.polygon(cloth, fill=INK)
inset = [(s(L + 14), s(T + 6)), (s(R - 14), s(T + 6)), (s(R - 14), s(B - 26)), (s(512), s(V - 20)), (s(L + 14), s(B - 26))]
d.polygon(inset, fill=GOLD)
inner = [(s(L + 34), s(T + 18)), (s(R - 34), s(T + 18)), (s(R - 34), s(B - 62)), (s(512), s(V - 52)), (s(L + 34), s(B - 62))]
d.polygon(inner, fill=CRIMSON)
folds = Image.new('RGBA', (W, W), (0, 0, 0, 0)); fd = ImageDraw.Draw(folds)   # gentle folds, kept inside the cloth
for i in range(5):
    x = s(L + 96 + i * 66)
    fd.line((x, s(T + 24), x, s(B)), fill=CRIMSON_D, width=s(5))
fm = Image.new('L', (W, W), 0); ImageDraw.Draw(fm).polygon(inner, fill=255)
img.paste(folds, (0, 0), Image.composite(folds.split()[3], Image.new('L', (W, W), 0), fm))
d = ImageDraw.Draw(img)
# the emblem: a mountain with a cave mouth (the deep)
M = [(s(362), s(612)), (s(470), s(400)), (s(512), s(452)), (s(560), s(372)), (s(662), s(612))]
d.polygon(M, fill=INK)
d.polygon([(x, y - s(10)) if i not in (0, 4) else (x + (s(10) if i == 0 else -s(10)), y - s(6)) for i, (x, y) in enumerate(M)], fill=GOLD)
d.polygon([(s(560), s(372)), (s(592), s(428)), (s(560), s(414)), (s(538), s(436)), (s(530), s(410))], fill=(255, 240, 200, 255))   # snow cap
d.pieslice((s(466), s(520), s(558), s(640)), 180, 360, fill=INK)          # cave mouth
d.rectangle((s(466), s(580), s(558), s(602)), fill=INK)
d.line((s(352), s(612), s(672), s(612)), fill=INK, width=s(10))
out = img.resize((N, N), Image.LANCZOS)
out.save(sys.argv[1])
for n in (64, 32):
    out.resize((n, n), Image.LANCZOS).save(sys.argv[1].replace('.png', f'-{n}.png'))
