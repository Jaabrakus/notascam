# A unit's picture cut into a 2D ragdoll's parts (python3 parts.py OUT): head, torso, two arms and two legs for each
# facing (S, N, E, W) of each preview lineup unit, from its standing picture as the game lays it (body and drawn
# armour, preview.strip, layer by layer). Each limb is told apart by the race's own pictures: the whole body minus its
# "NoRightArm" (and the other armless and legless pictures) is that limb (fists.py's way, on the pictures from before
# the 2026-10-24 reshade), and an arm also takes its own sleeve layer. Side on, an arm is drawn on the body (the
# armless picture lacks only its lines and paints a red stump at the shoulder), so there the arm is the whole area
# those span, and the body seen through the chest armour's gap for it. The head is what is above the chin; the torso
# is the rest, drawn as it is under the arms: the armless body (its stumps painted over) with the chest and leg armour,
# the chest's pattern carried into the gap the arm left. Every other pixel goes to the part it is joined to (a flood).
#
# Each arm is then split at its elbow into upper arm and forearm, and each leg at its knee into thigh and shin, so they
# bend.
#
# Writes OUT/g3r-<unit>-<facing>.png (ten 64 px cells side by side: head, torso, armRu, armRl, armLu, armLl, legRu,
# legRl, legLu, legLl, each holding only its own pixels where they are in the picture) and OUT/g3rig.json: per unit and
# facing, each part's box and its joints (neck, shoulders, elbows, hips, knees; hands and feet at the far ends), in
# picture pixels (x right, y down).
import json, os, sys
from collections import deque
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'enhance'))
import wearables64 as w          # noqa: E402
import game_export as ge         # noqa: E402
import remaster64 as rm          # noqa: E402
from game_export import read_dmi_full   # noqa: E402
import preview as pv             # noqa: E402
from fists import biggest        # noqa: E402

R64_SRC = os.path.join(HERE, '..', '..', 'restore-points', 'sprites-before-enhance-20261024', 'Races64')
R64 = os.path.join(HERE, '..', '..', 'game', 'Icons', 'Remastered', 'Races64')
DIRS = 'SNEW'
PARTS = ['head', 'torso', 'armR', 'armL', 'legR', 'legL']   # as cut
OUT_PARTS = ['head', 'torso', 'armRu', 'armRl', 'armLu', 'armLl', 'legRu', 'legRl', 'legLu', 'legLl']   # as written: arms split at the elbow, legs at the knee


def states(sheet):
    src = os.path.join(R64_SRC, sheet + '.dmi')
    return {n: c for n, m, c in read_dmi_full(src if os.path.exists(src) else os.path.join(R64, sheet + '.dmi'))}


def limb(body, other):
    """What the picture without the limb lacks, or shows in other colours."""
    B = body[..., 3] > 0
    changed = ~(other[..., 3] > 0) | (np.abs(body[..., :3].astype(int) - other[..., :3].astype(int)).sum(-1) > 24)
    return biggest(B & changed)


def flood(opaque, seeds):
    """Every opaque pixel to the part it is joined to: a breadth-first flood from each part's own pixels."""
    lab = np.full(opaque.shape, -1, int)
    q = deque()
    for k, m in enumerate(seeds):
        for y, x in zip(*np.nonzero(m & opaque & (lab < 0))):
            lab[y, x] = k; q.append((y, x))
    while q:
        y, x = q.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < 64 and 0 <= nx < 64 and opaque[ny, nx] and lab[ny, nx] < 0:
                lab[ny, nx] = lab[y, x]; q.append((ny, nx))
    # what nothing reaches (a loose speck) goes to the torso
    lab[opaque & (lab < 0)] = 1
    return lab


def ends(mask, top=True):
    """The middle of a mask's top (or bottom) three rows."""
    ys, xs = np.nonzero(mask)
    if not len(ys):
        return None
    sel = ys <= ys.min() + 2 if top else ys >= ys.max() - 2
    return [round(float(xs[sel].mean()) + 0.5, 2), round(float(ys[sel].mean()) + 0.5, 2)]


def box(mask):
    ys, xs = np.nonzero(mask)
    if not len(ys):
        return None
    return [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1]


def layers(sheet, state, armour, di, f=0):
    """The picture's layers as the game stacks them (preview.strip), frame f: body, legs, chest, the two sleeves."""
    body = pv.cells(pv.ICONS / 'Races64' / f'{sheet}.dmi', state) or pv.cells(pv.ICONS / 'Races64' / f'{sheet}.dmi', '')
    tier, chest, legs, arms = armour
    g = pv.ICONS / 'Gear64' / sheet / f'{tier}.dmi'
    sty = lambda s: s if tier != 'leather' else 'leather'
    out = [('body', pv.layer_cell(body, f, di))]
    if legs:
        out.append(('legs', pv.layer_cell(pv.cells(g, f'legs.{sty(legs)}.{tier}'), f, di)))
    if chest:
        out.append(('chest', pv.layer_cell(pv.cells(g, f'chest.{sty(chest)}.{tier}'), f, di)))
    if arms:
        for side in 'LR':
            out.append(('arm' + side, pv.layer_cell(pv.cells(g, f'arms.{sty(arms)}.{tier}.{side}'), f, di)))
    return [(n, np.asarray(c)[:, :64] if c is not None else np.zeros((64, 64, 4), np.uint8)) for n, c in out]


def compose(L):
    fr = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
    for _, c in L:
        fr.alpha_composite(Image.fromarray(np.ascontiguousarray(c)))
    return np.asarray(fr).copy()


def topmost(L):
    """Which layer is on top at each pixel (-1: none)."""
    t = np.full((64, 64), -1, int)
    for i, (_, c) in enumerate(L):
        t[c[..., 3] > 0] = i
    return t


def is_red(c):
    return (c[..., 3] > 0) & (c[..., 0] > 200) & (c[..., 1] < 70) & (c[..., 2] < 70)


def stump(other):
    """Where an armless picture's red stump is (the shoulder), if it has one."""
    if other is None:
        return None
    ys, xs = np.nonzero(is_red(np.asarray(other)[:, :64]))
    return [round(float(xs.mean()) + 0.5, 2), round(float(ys.mean()) + 0.5, 2)] if len(ys) else None


def bare(sheet, st, base, di):
    """The body with no arms (the race's NoArms picture as the game has it now), each red stump pixel given its
    nearest body colour. The stump is read off the pictures from before the reshade: what the armless picture paints
    reddish where the whole body differs (a red-skinned race's own skin is left alone)."""
    c = pv.cells(pv.ICONS / 'Races64' / f'{sheet}.dmi', 'NoArms')
    if c is None or 'NoArms' not in st:
        return np.zeros((64, 64, 4), np.uint8)
    im = np.asarray(pv.layer_cell(c, 0, di))[:, :64].copy()
    o, b = np.asarray(st['NoArms'][di])[:, :64].astype(int), np.asarray(base[di])[:, :64].astype(int)
    r, g, bl = o[..., 0], o[..., 1], o[..., 2]
    red = (o[..., 3] > 0) & (r > 70) & (g * 1.6 < r) & (bl * 1.6 < r)
    red &= (b[..., 3] == 0) | (np.abs(o[..., :3] - b[..., :3]).sum(-1) > 24)
    red &= im[..., 3] > 0
    ok = (im[..., 3] > 0) & ~red
    oy, ox = np.nonzero(ok)
    for y, x in zip(*np.nonzero(red)):
        if len(oy):
            j = np.argmin((oy - y) ** 2 * 2 + (ox - x) ** 2)
            im[y, x] = im[oy[j], ox[j]]
    return im


def hull(m):
    """A mask's convex hull, filled (the area an arm's drawn lines span)."""
    ys, xs = np.nonzero(m)
    pts = sorted(set(zip(xs.tolist(), ys.tolist())))
    if len(pts) < 3:
        return m.copy()
    pts = [(x + dx, y + dy) for x, y in pts for dx in (0, 1) for dy in (0, 1)]
    pts = sorted(set(pts))
    cross = lambda o, a, b: (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, hi = [], []
    for p in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(hi) >= 2 and cross(hi[-2], hi[-1], p) <= 0:
            hi.pop()
        hi.append(p)
    im = Image.new('L', (64, 64), 0)
    from PIL import ImageDraw
    ImageDraw.Draw(im).polygon(lo[:-1] + hi[:-1], fill=255)
    # a pixel is in when its middle is
    big = Image.new('L', (256, 256), 0)
    ImageDraw.Draw(big).polygon([(x * 4, y * 4) for x, y in lo[:-1] + hi[:-1]], fill=255)
    return (np.asarray(big)[2::4, 2::4] > 0) | m


def dilate(m, n):
    """A mask grown by n pixels every way (a square)."""
    out = m.copy()
    for _ in range(n):
        g = out.copy()
        g[1:] |= out[:-1]; g[:-1] |= out[1:]; g[:, 1:] |= out[:, :-1]; g[:, :-1] |= out[:, 1:]
        g[1:, 1:] |= out[:-1, :-1]; g[:-1, :-1] |= out[1:, 1:]; g[1:, :-1] |= out[:-1, 1:]; g[:-1, 1:] |= out[1:, :-1]
        out = g
    return out


def grow(m, free):
    """A mask grown over the free pixels joined to it (4-connected)."""
    out = m.copy()
    stack = list(zip(*np.nonzero(m)))
    while stack:
        y, x = stack.pop()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < 64 and 0 <= nx < 64 and free[ny, nx] and not out[ny, nx]:
                out[ny, nx] = True; stack.append((ny, nx))
    return out


def seg_dist(x, y, a, b):
    ax, ay = b[0] - a[0], b[1] - a[1]
    L2 = ax * ax + ay * ay or 1e-6
    t = np.clip(((x - a[0]) * ax + (y - a[1]) * ay) / L2, 0, 1)
    return np.hypot(x - a[0] - t * ax, y - a[1] - t * ay)


def mid_joint(m, S, H):
    """A limb's middle joint (an elbow, a knee): the middle of the limb half way between its two ends."""
    ys, xs = np.nonzero(m)
    px, py = xs + 0.5, ys + 0.5
    ax, ay = H[0] - S[0], H[1] - S[1]
    L2 = ax * ax + ay * ay or 1e-6
    t = ((px - S[0]) * ax + (py - S[1]) * ay) / L2
    mid = (t > 0.35) & (t < 0.65)
    if mid.any():
        return [round(float(px[mid].mean()), 2), round(float(py[mid].mean()), 2)]
    return [round((S[0] + H[0]) / 2, 2), round((S[1] + H[1]) / 2, 2)]


def shoulders(T, F, race, d):
    """Where the shoulders are in a facing, from the template body (wearables64.pauldrons' points: the chest's top
    row and the arm's top), moved onto the race's own figure: {'R': (x, y), 'L': (x, y)}; side on, the near one only."""
    r = T.ref[d]
    chest, arms = r['chest'], r['arm_L'] | r['arm_R']
    if d in ('S', 'N'):
        y = np.nonzero(chest)[0].min() + 6
        xs = np.flatnonzero((chest | arms)[y])
        left, right = (xs.min() + 3.6, y), (xs.max() + 1 - 3.6, y)
        # facing south the right arm is on the picture's left; facing north, on its right
        pts = {'R': left, 'L': right} if d == 'S' else {'R': right, 'L': left}
    else:
        ay = np.nonzero(arms)[0].min()
        xs = np.flatnonzero(arms[ay + 1])
        pts = {('R' if d == 'E' else 'L'): ((xs.min() + xs.max() + 1) / 2.0, ay + 1)}
    return {k: tuple(float(v) for v in F.map_point(race, d, x, y)) for k, (x, y) in pts.items()}


def find_arm(L, top, opaque, body, other, chin, hip_row, d, side, shoulder=None):
    """One arm's pixels in a picture (fists.py uses it too). L: the picture's layers, top: which is on top at each
    pixel, body: the race's whole body (before the reshade), other: its picture without this arm. What the armless
    picture lacks (in a side view only the arm's lines and its red stump, as the arm is drawn on the body there), from
    the chin down, with the sleeve's own armour layer; side on, the arm is the whole area those span where the body
    (not the chest's armour) is on top, and the body seen through the chest armour's gap for it."""
    names = [n for n, _ in L]
    B = np.asarray(body)[:, :64][..., 3] > 0
    if d in ('E', 'W') and side != ('R' if d == 'E' else 'L'):
        return np.zeros_like(B)   # side on, the far arm is behind the body (it borrows the near one's pixels)
    m = limb(np.asarray(body)[:, :64], np.asarray(other)[:, :64]) if other is not None else np.zeros_like(B)
    m[:max(0, int(chin) - 2, int(shoulder[1]) - 2 if shoulder else 0)] = False   # nothing above the shoulder (long hair)
    if shoulder and d in ('S', 'N'):   # face on, an arm is on its own side of the body
        if shoulder[0] < 32:
            m[:, int(round(shoulder[0])) + 6:] = False
        else:
            m[:, :max(0, int(round(shoulder[0])) - 6)] = False
    elif shoulder:   # side on, it hangs from the shoulder and reaches forward, not down the back (hair hangs there)
        sx = int(round(shoulder[0]))
        if d == 'E':
            m[:, :max(0, sx - 4)] = False
        else:
            m[:, sx + 5:] = False
    m = biggest(m)
    if 'arm' + side in names:
        sleeve = top == names.index('arm' + side)
        if d in ('E', 'W') and sleeve.any():
            m &= dilate(sleeve, 4)   # side on, near the sleeve (an elf's hair is not its arm)
        m |= sleeve
    if d in ('E', 'W') and m.any():
        own = (top == 0) | (top == (names.index('arm' + side) if 'arm' + side in names else -9))
        m = hull(m) & own
        if 'chest' in names:
            free = (top == 0) & opaque
            free[:int(round(chin)) + 1] = False
            free[hip_row:] = False
            m = grow(m, free & dilate(m, 3))   # near the arm only (not an elf's long hair)
    m &= opaque
    ys, xs = np.nonzero(m)
    if len(ys) < 6 or max(ys.max() - ys.min(), xs.max() - xs.min()) < 4:
        m = np.zeros_like(B)
    return m


def arm_joints(m, red, shoulder=None):
    """An arm's shoulder (its red stump when the race has one, else the figure's shoulder, else its top), its fist
    (the arm's far end from the shoulder) and its elbow (the middle of the arm half way between, so a bent arm bends
    there)."""
    ys, xs = np.nonzero(m)
    px, py = xs + 0.5, ys + 0.5
    near = lambda q: q is not None and np.min(np.hypot(px - q[0], py - q[1])) < (3 if q is red else 5)
    S = red if near(red) else list(shoulder) if near(shoulder) else ends(m, True)
    dist = np.hypot(px - S[0], py - S[1])
    far = dist >= dist.max() - 1.5
    H = [round(float(px[far].mean()), 2), round(float(py[far].mean()), 2)]
    ax, ay = H[0] - S[0], H[1] - S[1]
    L2 = ax * ax + ay * ay or 1e-6
    t = ((px - S[0]) * ax + (py - S[1]) * ay) / L2
    mid = (t > 0.35) & (t < 0.65)
    E = [round(float(px[mid].mean()), 2), round(float(py[mid].mean()), 2)] if mid.any() else [round((S[0] + H[0]) / 2, 2), round((S[1] + H[1]) / 2, 2)]
    return [round(S[0], 2), round(S[1], 2)], E, H


def cut_facing(sheet, state, armour, di, ctx):
    """One facing of one picture cut into its parts: (info, masks, cells, extra). ctx carries the race's pieces (A, T, F,
    race, st, base) and the hips' row, found from the front and used for the other facings."""
    d = DIRS[di]
    A, T, F, race, st, base = ctx['A'], ctx['T'], ctx['F'], ctx['race'], ctx['st'], ctx['base']
    hip_row = ctx.get('hip_row', 50)
    L = layers(sheet, state, armour, di)
    pic = compose(L)                                    # the standing picture, armour on (preview.strip)
    opaque = pic[..., 3] > 0
    top = topmost(L)
    names = [n for n, _ in L]
    b = base[di]
    B = b[..., 3] > 0
    seeds = {p: np.zeros_like(B) for p in PARTS}
    for p, name in (('legR', 'NoRightLeg'), ('legL', 'NoLeftLeg')):
        if name in st:
            seeds[p] = limb(b, st[name][di])
    if d == 'S':   # where the legs start, from the front (the hips' row)
        tops = [np.nonzero(seeds[p])[0].min() for p in ('legR', 'legL') if seeds[p].any()]
        hip_row = int(min(tops)) if tops else 50
        ctx['hip_row'] = hip_row
    chin = F.map_point(race, d, 32, rm.CHIN)[1]
    joints = {}   # the arms (find_arm), with their shoulders, elbows and fists
    sh = shoulders(T, F, race, d)
    for p, side, name in (('armR', 'R', 'NoRightArm'), ('armL', 'L', 'NoLeftArm')):
        other = st[name][di] if name in st else None
        m = find_arm(L, top, opaque, b, other, chin, hip_row, d, side, sh.get(side))
        seeds[p] = m
        if m.any():
            joints[p] = arm_joints(m, stump(other), sh.get(side))
    if d in ('E', 'W'):
        # side on, the legs overlap and the legless pictures barely differ: everything below the hips is the near
        # leg (the right one facing east, the left facing west); the far one is hidden and borrows it
        near, far = ('legR', 'legL') if d == 'E' else ('legL', 'legR')
        low = B.copy(); low[:hip_row] = False
        seeds[near] = low & ~seeds['armR'] & ~seeds['armL']
        seeds[far] = np.zeros_like(B)
    head = B.copy(); head[int(round(chin)):] = False
    for p in ('armR', 'armL'):
        head &= ~seeds[p]
    seeds['head'] = head
    torso = B & ~head
    for p in ('armR', 'armL', 'legR', 'legL'):
        torso &= ~seeds[p]
    seeds['torso'] = torso
    lab = flood(opaque, [seeds[p] for p in PARTS])
    info = {}
    masks = {}
    for k, p in enumerate(PARTS):
        masks[p] = lab == k
        info[p] = dict(box=box(masks[p]))
    # joints: the neck at the head's foot, each arm's shoulder (its stump), elbow and fist, each leg's hip at
    # its top and foot at its bottom; a hidden limb borrows the other side's, mirrored about the body
    hm = lab == 0
    info['head']['root'] = ends(hm, top=False) or [32, chin]
    for p in ('legR', 'legL'):
        m = lab == PARTS.index(p)
        info[p]['root'] = ends(m, top=True)
        info[p]['tip'] = ends(m, top=False)
        info[p]['knee'] = mid_joint(m, info[p]['root'], info[p]['tip']) if m.any() else None
    for p in ('armR', 'armL'):
        J = joints.get(p) if masks[p].any() else None
        info[p]['root'], info[p]['elbow'], info[p]['tip'] = J if J else (None, None, None)
    cx = (A[sheet]['views'][d][0]['head']['l'] + A[sheet]['views'][d][0]['head']['r']) / 2
    for a, b2 in (('armR', 'armL'), ('legR', 'legL')):
        for x, y in ((a, b2), (b2, a)):
            if info[x]['root'] is None and info[y]['root'] is not None:
                keys = ('root', 'elbow', 'tip') if a == 'armR' else ('root', 'knee', 'tip')
                for kk in keys:
                    v = info[y][kk]
                    # side on, the hidden limb is right behind the near one; front or back, across the body
                    info[x][kk] = list(v) if d in ('E', 'W') else [2 * cx - v[0], v[1]]
    tb = info['torso']['box'] or [24, 28, 40, 48]
    info['torso']['root'] = [round((tb[0] + tb[2]) / 2, 2), float(tb[3])]   # the pelvis: its foot, middle
    # the arms split at the elbow: each pixel to the upper arm or the forearm, the nearer of the two bones
    for a in ('armR', 'armL'):
        S, E, H, m = info[a]['root'], info[a]['elbow'], info[a]['tip'], masks[a]
        up, lo = np.zeros_like(m), np.zeros_like(m)
        if S and m.any():
            ys, xs = np.nonzero(m)
            near_up = seg_dist(xs + 0.5, ys + 0.5, S, E) <= seg_dist(xs + 0.5, ys + 0.5, E, H)
            up[ys[near_up], xs[near_up]] = True
            lo[ys[~near_up], xs[~near_up]] = True
        masks[a + 'u'], masks[a + 'l'] = up, lo
        info[a + 'u'] = dict(box=box(up), root=S, tip=E)
        info[a + 'l'] = dict(box=box(lo), root=E, tip=H)
        del info[a]
    # the legs split at the knee the same way: thigh and shin (with the foot)
    for a in ('legR', 'legL'):
        S, K, Ft, m = info[a]['root'], info[a].get('knee'), info[a]['tip'], masks[a]
        up, lo = np.zeros_like(m), np.zeros_like(m)
        if S and K and m.any():
            ys, xs = np.nonzero(m)
            near_up = seg_dist(xs + 0.5, ys + 0.5, S, K) <= seg_dist(xs + 0.5, ys + 0.5, K, Ft)
            up[ys[near_up], xs[near_up]] = True
            lo[ys[~near_up], xs[~near_up]] = True
        masks[a + 'u'], masks[a + 'l'] = up, lo
        info[a + 'u'] = dict(box=box(up), root=S, tip=K)
        info[a + 'l'] = dict(box=box(lo), root=K, tip=Ft)
        del info[a]
    # the body as it is under the arms: the armless picture (its red stumps painted over) with the chest and
    # leg armour, and where an arm lay in the chest armour's gap, that armour's own pattern carried across
    under = compose([(n, (bare(sheet, st, base, di) if n == 'body' else c)) for n, c in L if not n.startswith('arm')])
    chest = L[names.index('chest')][1][..., 3] > 0 if 'chest' in names else np.zeros_like(B)
    gap = (masks['armR'] | masks['armL']) & ~chest & (under[..., 3] > 0)
    if d in ('E', 'W') and chest.any():
        # side on the arm lay in the chest's gap: the chest's own pattern carried in (a pixel an even number along
        # its own row keeps a mail or banded pattern), inside the body's own outline, which is kept
        lum = under[..., :3].astype(int).sum(-1)
        edge = dilate(under[..., 3] == 0, 1)          # next to the outside: the body's own outline
        # the chest's dark rim round the gap goes too, so no seam is left where the arm lay
        rim = chest & (lum < 150) & dilate(gap, 1) & ~edge
        fill = (gap & ~((lum < 150) & edge)) | rim
        src = chest & ~rim & (lum >= 150)
        cy, cxs = np.nonzero(src)
        for y, x in zip(*np.nonzero(fill)):
            if not len(cy):
                break
            # from along its own row first, so the armour's bands run on unbroken
            d2 = (cxs - x) ** 2 + 60 * (cy - y) ** 2 + np.where(((cy - y) % 2 == 0) & ((cxs - x) % 2 == 0), 0, 1000)
            j = np.argmin(d2)
            under[y, x] = under[cy[j], cxs[j]]
    cells = np.zeros((64, 64 * len(OUT_PARTS), 4), np.uint8)
    for k, p in enumerate(OUT_PARTS):
        m = masks[p]
        cells[:, k * 64:(k + 1) * 64][m] = pic[m]
    k = OUT_PARTS.index('torso')
    tm = (masks['torso'] | masks['armR'] | masks['armL']) & (under[..., 3] > 0)
    cells[:, k * 64:(k + 1) * 64][tm] = under[tm]
    if d in ('E', 'W'):
        # side on, the far arm's own pixels (a hand or a sleeve peeking out past the body) go from the torso:
        # the far arm is drawn from the near one's pixels, so they would stay put as it moves
        far = 'L' if d == 'E' else 'R'
        fm = limb(b, st['NoLeftArm' if far == 'L' else 'NoRightArm'][di]) if ('NoLeftArm' if far == 'L' else 'NoRightArm') in st else np.zeros_like(B)
        if 'arm' + far in names:
            fm |= top == names.index('arm' + far)
        for part in ('torso', 'legRu', 'legRl', 'legLu', 'legLl'):   # the hips: the near leg took what hangs below them
            pm = fm & masks[part]
            if pm.any():
                kk = OUT_PARTS.index(part)
                cells[:, kk * 64:(kk + 1) * 64][pm] = np.where((under[pm][:, 3:4] > 0), under[pm], 0)
    extra = dict(pic=pic, under=under, far=(fm if d in ('E', 'W') else None), opaque=opaque)
    return info, masks, cells, extra


def main(out):
    os.makedirs(out, exist_ok=True)
    A = json.load(open(os.path.join(HERE, 'anchors.json')))
    T = w.Template(frame=0)
    specs = {s['sheet']: s for s in ge.SHEETS}
    races = list({s['race'] for s in specs.values() if s.get('gear', True)})
    F = w.Figures(T, races=races, frame=0)
    rig = {}
    for i, (sheet, state, armour, gear, act) in enumerate(pv.LINEUP):
        st = states(sheet)
        ctx = dict(A=A, T=T, F=F, race=specs[sheet]['race'], st=st, base=st[A[sheet]['state']])
        rig[i] = {}
        for di, d in enumerate(DIRS):
            info, masks, cells, _ = cut_facing(sheet, state, armour, di, ctx)
            Image.fromarray(cells).save(os.path.join(out, f'g3r-{i}-{d}.png'))
            rig[i][d] = info
        print(i, sheet, {p: rig[i]['S'][p]['box'] for p in OUT_PARTS}, flush=True)
    json.dump(rig, open(os.path.join(out, 'g3rig.json'), 'w'), separators=(',', ':'))
    print(os.path.join(out, 'g3rig.json'))


# The game's part maps (python3 parts.py --races OUT): in the game every unit wears its own armour, so instead of cutting
# pictures ahead, each race sheet the pieces are anchored on (anchors.json) gets, for each facing, a map of which part
# each pixel is, from the body cut bare and cut again in plate (so armour's pixels have their part too), its joints, and
# where the body under the arms shows when an arm moves. The page cuts each unit's own picture with it (game.js g3cut).
# Writes OUT/g3rig.json: {"sheets": {sheet: {facing: {"lab": ..., "labs": ..., "fill": ..., "j": {part: {box, root, tip}}}}}};
# "lab" (bare first), "labs" (in arm armour: the plate's first) and "fill" are run-length strings, row by row: A to J the parts in OUT_PARTS order, K the torso drawn from its own
# pixels (side on, a far arm peeking past the body), L nothing, . no part known; fill Y where the body under an arm shows.
RACE_ARMOUR = ('iron', 'plate', 'plate', 'plate')
CODES = 'ABCDEFGHIJ'


def rle(chars):
    out, prev, n = [], None, 0
    for c in chars:
        if c == prev:
            n += 1
        else:
            if prev is not None:
                out.append(f'{prev}{n}')
            prev, n = c, 1
    out.append(f'{prev}{n}')
    return ''.join(out)


def race_maps(sheet, A, T, F, specs):
    state = A[sheet]['state']
    st = states(sheet)
    ctx = dict(A=A, T=T, F=F, race=specs[sheet]['race'], st=st, base=st[state])
    R = {}
    for di, d in enumerate(DIRS):
        labs, ops = [], []
        fill = np.zeros((64, 64), bool)
        joints = None
        for v, armour in enumerate(((None, None, None, None), RACE_ARMOUR)):   # bare, then in plate
            info, masks, cells, ex = cut_facing(sheet, state, armour, di, ctx)
            if joints is None:
                joints = info
            op = ex['opaque']
            lab = np.full((64, 64), '.', dtype='<U1')
            for k, part in enumerate(OUT_PARTS):
                lab[masks[part] & op] = CODES[k]
            if ex['far'] is not None:
                fm = ex['far'] & op & (masks['torso'] | masks['legRu'] | masks['legRl'] | masks['legLu'] | masks['legLl'])
                lab[fm & (ex['under'][..., 3] > 0)] = 'K'
                lab[fm & (ex['under'][..., 3] == 0)] = 'L'
            labs.append(lab)
            ops.append(op)
            if v == 0:   # the body under the arms as it is bare: plate would widen every unit's chest
                fill |= (masks['armR'] | masks['armL']) & (ex['under'][..., 3] > 0)
        # bare first (the plate's parts only where the bare body has none: armour's own pixels), and, for a unit in arm
        # armour (its sleeves wider than the bare arm), the plate's first
        bare = np.where(ops[0], labs[0], labs[1])
        sleeved = np.where(ops[1], labs[1], labs[0])
        j = {}
        for part in OUT_PARTS:
            q = joints.get(part) or {}
            j[part] = {k: q.get(k) for k in ('box', 'root', 'tip') if q.get(k) is not None}
        R[d] = dict(lab=rle(bare.ravel()), labs=rle(sleeved.ravel()), fill=rle(np.where(fill, 'Y', 'N').ravel()), j=j)
    return R


def races(out):
    os.makedirs(out, exist_ok=True)
    A = json.load(open(os.path.join(HERE, 'anchors.json')))
    T = w.Template(frame=0)
    specs = {s['sheet']: s for s in ge.SHEETS}
    races_ = list({s['race'] for s in specs.values() if s.get('gear', True)})
    F = w.Figures(T, races=races_, frame=0)
    rig = {'sheets': {}}
    for sheet in sorted(A):
        if sheet not in specs:
            print('no spec', sheet)
            continue
        rig['sheets'][sheet] = race_maps(sheet, A, T, F, specs)
        print(sheet, {d: len(rig['sheets'][sheet][d]['lab']) for d in DIRS}, flush=True)
    json.dump(rig, open(os.path.join(out, 'g3rig.json'), 'w'), separators=(',', ':'))
    print(os.path.join(out, 'g3rig.json'), os.path.getsize(os.path.join(out, 'g3rig.json')))


if __name__ == '__main__':
    if sys.argv[1] == '--races':
        races(sys.argv[2])
    else:
        main(sys.argv[1])
