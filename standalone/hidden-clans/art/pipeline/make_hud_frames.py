"""Race-themed pixel-art HUD frames for the Remastered overlay HUD.

Each material gets a 24x24 nine-slice panel frame (8 px corners/edges), a 32x32
interior tile and two 12x12 button frames (normal, pressed), drawn at 1x and shown
at 2x with image-rendering:pixelated.  The CSS (data URIs) is written between the
RACE-FRAMES markers in game/Interface/remastered.html.

    python3 art/pipeline/make_hud_frames.py [--sheet]
"""
import base64, io, os, random, re, sys
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HTML = os.path.join(ROOT, 'game', 'Interface', 'remastered.html')

def sh(c, k):  # shade an rgb by k (-255..255)
    return tuple(max(0, min(255, v + k)) for v in c[:3]) + (255,)

# name: band, dark, accent(trim/gold), pane interior, ink, title font, races
MATS = {
 'stone':   dict(band=(112,108,116), pane=(34,33,38), acc=(206,166,84),  ink=(232,226,210), font='Herculanum',
                 races='dwarf gargoyle stone sand'),
 'timber':  dict(band=(122,80,42),   pane=(42,30,21), acc=(222,196,128), ink=(240,226,196), font='Luminari',
                 races='orc goblin kobold ratman gremlin'),
 'bone':    dict(band=(214,204,176), pane=(64,48,33), acc=(238,226,190), ink=(242,232,206), font='Herculanum',
                 races='skeleton zombie werewolf devourer fleshcrawler unholy lich'),
 'kingdom': dict(band=(128,134,146), pane=(24,30,48), acc=(224,184,90),  ink=(232,234,240), font='Luminari',
                 races='human'),
 'moon':    dict(band=(70,58,104),   pane=(22,18,38), acc=(188,206,236), ink=(226,224,246), font='Luminari',
                 races='elf svartalfar illithid'),
 'swamp':   dict(band=(104,128,58),  pane=(24,36,24), acc=(196,214,120), ink=(226,236,206), font='Luminari',
                 races='lizard frog water plant towercap'),
 'blood':   dict(band=(52,46,50),    pane=(36,12,16), acc=(214,48,48),   ink=(242,214,210), font='Luminari',
                 races='vampire demon blooded'),
 'scale':   dict(band=(158,52,36),   pane=(38,16,12), acc=(240,190,70),  ink=(248,226,196), font='Herculanum',
                 races='dragon'),
 'chitin':  dict(band=(54,40,62),    pane=(18,14,20), acc=(214,214,224), ink=(232,226,236), font='Herculanum',
                 races='spider queen warrior worker egg'),
}

def edge_pattern(m, name, R):
    """An 8-px-thick, 8-px-long strip (repeating) for the top edge; rotated for the others."""
    b = m['band']; s = Image.new('RGBA', (8, 8), (0,0,0,0)); d = ImageDraw.Draw(s)
    d.rectangle((0,0,7,7), fill=(0,0,0,0))
    if name == 'stone':
        d.rectangle((0,1,7,6), fill=sh(b,0)); d.line([0,1,7,1], fill=sh(b,30)); d.line([0,6,7,6], fill=sh(b,-40))
        d.line([7,1,7,6], fill=sh(b,-55)); d.point((2,3), fill=sh(b,-18)); d.point((5,4), fill=sh(b,12))
    elif name == 'timber':
        d.rectangle((0,1,7,6), fill=sh(b,0)); d.line([0,1,7,1], fill=sh(b,32)); d.line([0,6,7,6], fill=sh(b,-48))
        d.line([0,3,4,3], fill=sh(b,-30)); d.line([3,5,7,5], fill=sh(b,-22)); d.point((6,2), fill=sh(b,-30))
    elif name == 'bone':
        d.rectangle((0,2,7,5), fill=sh(b,0)); d.line([0,2,7,2], fill=sh(b,24)); d.line([0,5,7,5], fill=sh(b,-50))
        d.ellipse((5,1,8,6), fill=sh(b,20)); d.line([7,1,7,6], fill=sh(b,-70))   # knuckle joint
    elif name == 'kingdom':
        d.rectangle((0,1,7,6), fill=sh(b,0)); d.line([0,1,7,1], fill=sh(b,50)); d.line([0,6,7,6], fill=sh(b,-60))
        d.line([0,3,7,3], fill=m['acc']+(255,)); d.point((3,4), fill=sh(b,-30))
    elif name == 'moon':
        d.rectangle((0,1,7,6), fill=sh(b,0)); d.line([0,1,7,1], fill=sh(b,26)); d.line([0,6,7,6], fill=sh(b,-30))
        for x,y in ((0,4),(1,3),(2,3),(3,4),(4,5),(5,5),(6,4),(7,4)): d.point((x,y), fill=m['acc']+(255,))  # silver vine
        d.point((4,2), fill=sh(m['acc'],-40))
    elif name == 'swamp':
        for x in range(0,8,2): d.line([x,1,x,6], fill=sh(b,R.choice((-8,8,0)))); d.line([x+1,1,x+1,6], fill=sh(b,-34))
        d.line([0,1,7,1], fill=sh(b,30)); d.line([5,0,7,7], fill=(84,60,30,255))   # vine lashing
    elif name == 'blood':
        d.rectangle((0,1,7,6), fill=sh(b,0)); d.line([0,1,7,1], fill=sh(b,40)); d.line([0,6,7,6], fill=(10,6,8,255))
        d.polygon([(3,3),(4,2),(5,3),(4,4)], fill=sh(b,-22)); d.point((4,3), fill=(110,16,20,255))   # sigil
    elif name == 'scale':
        d.rectangle((0,1,7,6), fill=sh(b,-30))
        for cx in (0,4,8): d.ellipse((cx-3,0,cx+1,5), fill=sh(b,0), outline=sh(b,-60)); d.point((cx-2,1), fill=sh(b,40))
        d.line([0,6,7,6], fill=(30,10,6,255))
    elif name == 'chitin':
        d.rectangle((0,1,7,6), fill=sh(b,0)); d.line([0,1,7,1], fill=sh(b,40)); d.line([0,6,7,6], fill=(6,4,8,255))
        d.line([7,1,7,6], fill=(6,4,8,255)); d.line([1,2,5,2], fill=sh(b,70))   # glossy plate
    d.line([0,0,7,0], fill=(6,5,6,255)); d.line([0,7,7,7], fill=(6,5,6,255))
    return s

def corner(m, name):
    b, a = m['band'], m['acc']; c = Image.new('RGBA', (8, 8), (0,0,0,0)); d = ImageDraw.Draw(c)
    d.rectangle((0,0,7,7), fill=(6,5,6,255)); d.rectangle((1,1,6,6), fill=sh(b,-10))
    if name in ('stone', 'kingdom'):
        d.rectangle((1,1,6,6), fill=sh(a,-90)); d.rectangle((2,2,5,5), fill=a+(255,)); d.point((2,2), fill=sh(a,60)); d.point((5,5), fill=sh(a,-70))
    elif name == 'timber':
        for k in range(0,7,2): d.line([1+k,1,k,6], fill=(214,190,130,255)); d.line([2+k,1,1+k,6], fill=(140,116,72,255))
    elif name == 'bone':
        d.rectangle((0,0,7,7), fill=(0,0,0,0)); d.ellipse((0,0,7,7), fill=sh(b,24), outline=(30,22,14,255))
        d.point((2,4), fill=(30,22,14,255)); d.point((5,4), fill=(30,22,14,255)); d.line([3,6,4,6], fill=(30,22,14,255))
    elif name == 'moon':
        d.rectangle((1,1,6,6), fill=sh(b,-20)); d.ellipse((1,1,6,6), fill=a+(255,)); d.ellipse((3,1,7,5), fill=sh(b,-20))  # crescent
    elif name == 'swamp':
        d.ellipse((1,1,6,6), fill=(70,112,40,255)); d.point((3,2), fill=(150,200,90,255)); d.line([1,6,6,1], fill=(40,70,24,255))  # leaf
    elif name == 'blood':
        d.polygon([(4,1),(6,4),(4,6),(2,4)], fill=a+(255,)); d.point((4,2), fill=(255,170,170,255)); d.point((4,5), fill=(90,8,12,255))
    elif name == 'scale':
        d.polygon([(1,6),(6,1),(5,4),(3,6)], fill=(232,220,190,255)); d.point((6,1), fill=(255,255,240,255))  # horn
    elif name == 'chitin':
        d.rectangle((1,1,6,6), fill=sh(b,-20))
        for p in ((1,1,6,6),(1,6,6,1),(1,3,6,3),(3,1,3,6)): d.line(list(p), fill=(200,200,214,200))  # web
    return c

def frame(m, name, R):
    f = Image.new('RGBA', (24, 24), (0,0,0,0))
    e = edge_pattern(m, name, R); c = corner(m, name)
    for i in range(3):
        f.alpha_composite(e, (i*8, 0)); f.alpha_composite(e.rotate(180), (i*8, 16))
        f.alpha_composite(e.rotate(90, expand=True), (0, i*8)); f.alpha_composite(e.rotate(270, expand=True), (16, i*8))
    for x, y, r in ((0,0,0),(16,0,270),(16,16,180),(0,16,90)):
        f.alpha_composite(c.rotate(r) if name not in ('bone','moon','swamp','blood','scale') else c, (x, y))
    # inner shadow line under the band
    d = ImageDraw.Draw(f); d.rectangle((8,8,15,15), fill=(0,0,0,0))
    return f

def tile(m, name, R):
    t = Image.new('RGBA', (32, 32), m['pane']+(238,)); d = ImageDraw.Draw(t)
    for _ in range(90):
        x, y = R.randrange(32), R.randrange(32); d.point((x, y), fill=sh(m['pane'], R.choice((-6,-4,4,6,8)))[:3]+(238,))
    if name == 'timber':
        for y in (0, 11, 22): d.line([0,y,31,y], fill=sh(m['pane'],-14)[:3]+(238,))
    if name == 'stone':
        for y, off in ((0,0),(16,8)): d.line([0,y,31,y], fill=sh(m['pane'],-10)[:3]+(238,)); d.line([off,y,off,y+15], fill=sh(m['pane'],-10)[:3]+(238,)); d.line([off+16,y,off+16,y+15], fill=sh(m['pane'],-10)[:3]+(238,))
    if name == 'bone':  # hide: soft stitch rows
        for x in range(0, 32, 4): d.point((x, 1), fill=sh(m['pane'],40)[:3]+(238,))
    return t

def button(m, name, pressed):
    b = Image.new('RGBA', (12, 12), (0,0,0,0)); d = ImageDraw.Draw(b)
    face = sh(m['acc'], -60) if pressed else sh(m['pane'], 22)
    d.rectangle((0,0,11,11), fill=(6,5,6,255)); d.rectangle((1,1,10,10), fill=face)
    hi, lo = (sh(face,-30), sh(face,40)) if pressed else (sh(m['band'],10), (8,8,8,255))
    d.line([1,1,10,1], fill=hi); d.line([1,1,1,10], fill=hi); d.line([2,10,10,10], fill=lo); d.line([10,2,10,10], fill=lo)
    d.point((1,1), fill=sh(m['acc'], 0 if not pressed else 40))
    return b

def uri(im):
    buf = io.BytesIO(); im.save(buf, 'PNG', optimize=True)
    return 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode()

def hexc(c): return '#%02x%02x%02x' % c[:3]

def build():
    css = ['/* RACE-FRAMES-BEGIN (generated by art/pipeline/make_hud_frames.py; do not edit by hand) */']
    sheet = Image.new('RGBA', (len(MATS)*84, 40), (20,20,20,255))
    for i, (name, m) in enumerate(MATS.items()):
        R = random.Random(name)
        f, t, bn, bp = frame(m, name, R), tile(m, name, R), button(m, name, 0), button(m, name, 1)
        sheet.alpha_composite(t, (i*84, 4)); sheet.alpha_composite(f, (i*84+4, 8)); sheet.alpha_composite(bn, (i*84+36, 8)); sheet.alpha_composite(bp, (i*84+52, 8))
        css.append('body.overlay[data-mat=%s]{--mf:url(%s);--mt:url(%s);--mb:url(%s);--mbp:url(%s);--macc:%s;--mink:%s;--mband:%s;--mpane:%s;--mfont:%s}' % (
            name, uri(f), uri(t), uri(bn), uri(bp), hexc(m['acc']), hexc(m['ink']), hexc(m['band']), hexc(m['pane']), '"%s",Georgia,serif' % m['font']))
    races = {name: m['races'].split() for name, m in MATS.items()}
    css.append('/* race -> material: %s */' % '; '.join('%s=%s' % (k, ' '.join(v)) for k, v in races.items()))
    css.append('/* RACE-FRAMES-END */')
    js = 'const RACE_MATS=%s;' % ('{' + ','.join('%s:%r' % (k, v) for k, v in races.items()) + '}')
    return '\n'.join(css), js, sheet

if __name__ == '__main__':
    css, js, sheet = build()
    src = open(HTML, encoding='utf-8').read()
    src, n = re.subn(r'/\* RACE-FRAMES-BEGIN.*?RACE-FRAMES-END \*/', lambda _: css, src, flags=re.S)
    if not n: sys.exit('RACE-FRAMES markers missing in remastered.html')
    src, n = re.subn(r'const RACE_MATS=\{.*?\};', lambda _: js, src)
    if not n: sys.exit('const RACE_MATS missing in remastered.html')
    open(HTML, 'w', encoding='utf-8').write(src)
    if '--sheet' in sys.argv:
        out = os.path.join(ROOT, 'art', 'out', 'hud-frames.png'); sheet.resize((sheet.width*4, sheet.height*4), Image.NEAREST).save(out); print(out)
    print('wrote', len(css), 'bytes of frame CSS')
