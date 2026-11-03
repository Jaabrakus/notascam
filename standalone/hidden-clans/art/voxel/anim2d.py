# 2D animation from the game's own sprites (python3 anim2d.py OUTDIR 'Race,..' [anim]).
# Method A ("posed"): each facing is cut into parts - head, torso, arms, legs - by the sprite's own
# rows and columns (the part map), and the parts are rotated about their joints and shifted frame
# by frame: every pixel in every frame is one of the sprite's own pixels, moved.
# Method B ("cleaned"): the posed frames, then repaired pixel by pixel - holes the moved parts left
# filled from the colours round them, stray single pixels dropped, the dark outline redrawn on the
# figure's new edge - as a pixel artist would touch up a posed frame.
import os, sys, math
import numpy as np
import dmi, landmarks, build3d10
from PIL import Image

P = 64
R = landmarks.R

def facings(race):
    st = dmi.load(R + race + '.dmi')[landmarks.body_state(race)]
    return {f: np.asarray(dmi.frame(st, f).convert('RGBA')).astype(np.int32) for f in 'SNEW'}

def masks(race, pics):
    """Per facing: {part: bool mask} and joints {name: (row, col)}."""
    Sp = build3d10.parts_of(race); neck, crotch, sole = Sp['neck'], Sp['crotch'], Sp['sole']
    out = {}
    rr, cc = np.mgrid[0:P, 0:P]
    # front / back: arms are the columns outside the torso's run where the arms hang free
    arm_r = [Sp['armR'][r] for r in Sp['armR']] or [(16, 21)]
    arm_l = [Sp['armL'][r] for r in Sp['armL']] or [(42, 47)]
    ar_in = int(np.median([b for a, b in arm_r])) + 1        # right arm (image left) ends at this column
    al_in = int(np.median([a for a, b in arm_l])) - 1
    arm_rows = sorted(set(Sp['armR']) | set(Sp['armL'])) or [neck + 8]
    sh_row = neck + 3; hand_row = max(arm_rows) + 2
    for f in 'SN':
        a = pics[f][:, :, 3] > 0
        m = {}
        m['head'] = a & (rr <= neck)
        m['armA'] = a & (rr > neck) & (rr <= hand_row) & (cc <= ar_in)     # image-left arm
        m['armB'] = a & (rr > neck) & (rr <= hand_row) & (cc >= al_in)     # image-right arm
        m['legA'] = a & (rr > crotch) & (cc < 32)
        m['legB'] = a & (rr > crotch) & (cc >= 32)
        m['torso'] = a & ~(m['head'] | m['armA'] | m['armB'] | m['legA'] | m['legB'])
        j = {'shA': (sh_row, ar_in - 1), 'shB': (sh_row, al_in + 1), 'hipA': (crotch, 27), 'hipB': (crotch, 37), 'neck': (neck, 32)}
        out[f] = (m, j)
    for f in 'EW':
        a = pics[f][:, :, 3] > 0
        cols = np.nonzero(a[crotch + 2:sole + 1].any(0))[0]
        mid = (cols.min() + cols.max() + 1) / 2 if len(cols) else 32
        tcols = np.nonzero(a[neck + 4:crotch].any(0))[0]
        tmid = (tcols.min() + tcols.max() + 1) / 2 if len(tcols) else 32
        m = {}
        m['head'] = a & (rr <= neck)
        m['legA'] = a & (rr > crotch) & (cc < mid)       # image-left leg
        m['legB'] = a & (rr > crotch) & (cc >= mid)
        # the arm in profile: the strip down the body's middle, shoulder to hand
        m['armA'] = a & (rr > neck + 2) & (rr <= hand_row) & (np.abs(cc + 0.5 - tmid) <= 3.5)
        m['armB'] = np.zeros_like(a)
        m['torso'] = a & ~(m['head'] | m['legA'] | m['legB'] | m['armA'])
        j = {'shA': (neck + 3, tmid), 'shB': (neck + 3, tmid), 'hipA': (crotch, mid), 'hipB': (crotch, mid), 'neck': (neck, tmid)}
        out[f] = (m, j)
    return out

def layer(pic, mask):
    L = np.zeros_like(pic); L[mask] = pic[mask]; return L

def rot(L, pivot, deg, dy=0, dx=0):
    """Nearest-neighbour rotation of a layer about pivot (row, col), then a shift."""
    if not deg and not dy and not dx: return L
    t = math.radians(deg); c, s = math.cos(t), math.sin(t)
    out = np.zeros_like(L)
    rr, cc = np.mgrid[0:P, 0:P]
    y = rr - dy - pivot[0]; x = cc - dx - pivot[1]
    sy = np.round(pivot[0] + c * y - s * x).astype(int); sx = np.round(pivot[1] + s * y + c * x).astype(int)
    ok = (sy >= 0) & (sy < P) & (sx >= 0) & (sx < P)
    out[ok] = L[sy[ok], sx[ok]]
    return out

def over(base, L):
    m = L[:, :, 3] > 0; base = base.copy(); base[m] = L[m]; return base

def fill_from(pic, holes, iters=4):
    out = pic.copy()
    for _ in range(iters):
        todo = holes & (out[:, :, 3] == 0)
        if not todo.any(): break
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            nb = np.roll(np.roll(out, dy, 0), dx, 1)
            t = todo & (nb[:, :, 3] > 0) & (out[:, :, 3] == 0)
            out[t] = nb[t]
    return out

# --- poses: per animation, a function of the phase t in [0, 1) giving part angles and shifts ---
def pose(anim, t, facing):
    s, c = math.sin(2 * math.pi * t), math.cos(2 * math.pi * t)
    side = facing in 'EW'; sg = 1 if facing == 'E' else -1
    p = dict(legA=(0, 0, 0), legB=(0, 0, 0), armA=(0, 0, 0), armB=(0, 0, 0), head=(0, 0, 0), body=(0, 0))
    if anim == 'walk':
        bob = -1 if abs(s) < 0.5 else 0
        p['body'] = (bob, 0)
        if side:
            p['legA'] = (sg * 20 * s, 0, 0); p['legB'] = (-sg * 20 * s, 0, 0)
            p['armA'] = (-sg * 16 * s, 0, 0)
        else:
            p['legA'] = (0, -round(max(0, s) * 2), 0); p['legB'] = (0, -round(max(0, -s) * 2), 0)
            p['armA'] = (0, round(-s), 0); p['armB'] = (0, round(s), 0)
    elif anim == 'idle':
        p['body'] = (1 if s > 0.3 else 0, 0)
        p['head'] = (0, 1 if s > 0.3 else 0, 0)
    elif anim == 'attack':
        # wind up (0-0.35), strike (0.35-0.55), recover - the weapon arm (armB front / armA side)
        k = np.interp(t, [0, 0.35, 0.55, 1.0], [0, -1, 1, 0])
        if side: p['armA'] = (sg * 70 * k, 0, 0); p['body'] = (0, sg * round(k))
        else: p['armB'] = (-40 * k, round(-2 * k), 0); p['body'] = (0, 0)
    elif anim == 'hit':
        k = np.interp(t, [0, 0.2, 1.0], [0, 1, 0])
        p['body'] = (0, -sg * round(2 * k) if side else 0)
        p['head'] = (-sg * 12 * k if side else 0, round(k), 0)
        p['armA'] = (sg * 20 * k if side else 0, 0, 0)
    elif anim == 'work':
        # an overhead swing (pick, axe): both arms up and down together
        k = np.interp(t, [0, 0.45, 0.6, 1.0], [0, -1, 0.6, 0])
        if side: p['armA'] = (sg * 110 * k, 0, 0)
        else: p['armA'] = (0, round(-3 * k), 0); p['armB'] = (0, round(-3 * k), 0)
        p['body'] = (round(abs(k)) if k > 0 else 0, 0)
    return p

def frame(pics, M, anim, t, facing, clean):
    pic = pics[facing]; m, j = M[facing]
    p = pose(anim, t, facing)
    by, bx = p['body']
    base = np.zeros_like(pic)
    order = ['legA', 'legB', 'torso', 'armA', 'armB', 'head'] if facing in 'SE' else ['armA', 'armB', 'legA', 'legB', 'torso', 'head']
    if facing in 'EW': order = ['armA', 'legA', 'legB', 'torso', 'head'] if anim in ('attack', 'work') and False else ['legA', 'legB', 'torso', 'armA', 'head']
    vacated = np.zeros((P, P), bool)
    for part in order:
        if not m[part].any(): continue
        L = layer(pic, m[part])
        if part.startswith('leg'):
            deg, dy, dx = p[part]; piv = j['hip' + part[-1]]
            L = rot(L, piv, deg, dy, dx)
            if deg or dy: vacated |= m[part]
        elif part.startswith('arm'):
            deg, dy, dx = p[part]; piv = j['sh' + part[-1]]
            L = rot(L, piv, deg, dy + by, dx + bx)
            vacated |= m[part]
        elif part == 'head':
            deg, dy, dx = p['head']; L = rot(L, j['neck'], deg, dy + by, dx + bx)
        else:
            # the body behind the arm: where the arm lay over the torso, the torso's own colours
            # carried in from beside it (a moved arm left a dark hole)
            under = m['armA'] | m['armB']
            if facing in 'EW': under = under & (np.arange(P)[:, None] < M[facing][1]['hipA'][0])
            L = fill_from(L, under & (pic[:, :, 3] > 0), 6)
            L = rot(L, (0, 0), 0, by, bx)
        base = over(base, L)
    if facing in 'EW' or not clean:
        pass
    if clean:
        # holes inside the figure where a part moved away: the colours round them
        a = base[:, :, 3] > 0
        pa = np.pad(a, 1)
        inside = ~a & (pa[:-2, 1:-1].astype(int) + pa[2:, 1:-1] + pa[1:-1, :-2] + pa[1:-1, 2:] >= 3)
        base = fill_from(base, inside, 1)
        # torso pixels the arm covered in the side view: the body's own colour, not empty
        tor = pic.copy(); tor[~m['torso'] & ~(vacated & (pic[:, :, 3] > 0))] = 0
        hole = (base[:, :, 3] == 0) & vacated & np.roll(m['torso'], by, 0)
        if hole.any():
            body_col = np.median(pic[m['torso']][:, :3], axis=0).astype(int) if m['torso'].any() else np.array([128, 128, 128])
            base[hole, :3] = body_col; base[hole, 3] = 255
        # stray pixels: a pixel with one neighbour or none
        a = base[:, :, 3] > 0; pa = np.pad(a, 1)
        nb = pa[:-2, 1:-1].astype(int) + pa[2:, 1:-1] + pa[1:-1, :-2] + pa[1:-1, 2:]
        base[a & (nb <= 1)] = 0
        # the outline on the new edge, in the sprite's outline colour
        a = base[:, :, 3] > 0; pa = np.pad(a, 1)
        edge = a & ~(pa[:-2, 1:-1] & pa[2:, 1:-1] & pa[1:-1, :-2] & pa[1:-1, 2:])
        o = pic[pic[:, :, 3] > 0][:, :3]; dark = o[o.sum(1) < 90]
        olc = np.median(dark, axis=0).astype(int) if len(dark) else np.array([20, 10, 5])
        light = base[:, :, :3].sum(2) > 150
        base[edge & light, :3] = olc
    return base

ANIMS = {'walk': 6, 'idle': 4, 'attack': 6, 'hit': 4, 'work': 6}

def run(outdir, races, anims=None):
    os.makedirs(outdir, exist_ok=True)
    anims = anims or list(ANIMS)
    for rc in races:
        pics = facings(rc); M = masks(rc, pics)
        for an in anims:
            n = ANIMS[an]
            for clean, tag in ((False, 'posed'), (True, 'cleaned')):
                frames = {f: [frame(pics, M, an, k / n, f, clean) for k in range(n)] for f in 'SNEW'}
                # strip: rows S, N, E, W; columns the frames
                strip = Image.new('RGBA', (P * n, P * 4))
                for i, f in enumerate('SNEW'):
                    for k, fr in enumerate(frames[f]): strip.alpha_composite(Image.fromarray(fr.astype(np.uint8)), (k * P, i * P))
                name = '%s-%s-%s' % (rc.replace(' ', ''), an, tag)
                strip.save(os.path.join(outdir, name + '.png'))
                # an animated GIF of all four facings, 4x
                gif = []
                for k in range(n):
                    g = Image.new('RGBA', (P * 4, P), (52, 56, 66, 255))
                    for i, f in enumerate('SNEW'): g.alpha_composite(Image.fromarray(frames[f][k].astype(np.uint8)), (i * P, 0))
                    gif.append(g.resize((P * 4 * 4, P * 4), Image.NEAREST).convert('P', palette=Image.ADAPTIVE))
                gif[0].save(os.path.join(outdir, name + '.gif'), save_all=True, append_images=gif[1:], duration=120 if an != 'idle' else 220, loop=0)
        print(rc, flush=True)

if __name__ == '__main__':
    run(sys.argv[1], sys.argv[2].split(','), sys.argv[3].split(',') if len(sys.argv) > 3 else None)
