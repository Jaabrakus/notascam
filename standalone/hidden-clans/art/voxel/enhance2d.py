# Frame-preserving 2D enhancement of the game's sprites (python3 enhance2d.py OUTROOT [folder/file.dmi ..]).
# Every frame of every .dmi is shaded in place: the sprite is read as a soft rounded shape (its
# height grows with the distance from its edge, as a balloon), lit from the top-left, and each pixel
# is stepped onto a 4-tone ramp of its own colour - so flat areas gain volume and a soft highlight,
# while the layout stays exact: same frames, same pixel positions, same transparency, same states,
# directions, timing and metadata. Outlines, eyes, mouths and other small features (dark or rare
# colours) are kept as drawn. Writes OUTROOT/_dmi/<path>.dmi (installable copy) and a 3x preview
# sheet OUTROOT/<path>.png; never touches the game's own files.
import os, sys, zlib
import numpy as np
from PIL import Image, PngImagePlugin

# read from the untouched originals: the game's own copies are the enhanced ones since 2026-10-24
# (enhancing them again would shade twice)
SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'restore-points', 'sprites-before-enhance-20261024')
FOLDERS = ['Races64', 'Gear64', 'Limbs64', 'Rope64', 'Gear', 'Items']
WORLD_SKIP = {'HUD.dmi', 'HUD2.dmi', 'Selection.dmi', 'txt.dmi', 'night_and_sun.dmi', 'Night.dmi', 'Sleep.dmi', 'Star.dmi',
              'File Send.dmi', 'Funny Icons.dmi', 'test.dmi', 'Temporary.dmi', 'fx.dmi', 'Fire.dmi', 'Mist.dmi', 'Gather.dmi',
              'ColoredEyes.dmi', 'RedEye.dmi', 'Stair.dmi'}
LIGHT = np.array([-0.55, -0.65, 0.52]); LIGHT /= np.linalg.norm(LIGHT)   # (x, y down, out of the picture)

def chamfer(mask, edge_inside=False):
    """Distance in pixels from each pixel in mask to the nearest pixel outside it. edge_inside:
    the cell's border is not an edge (a floor or wall tile runs on into the next tile)."""
    h, w = mask.shape; INF = 1e6
    d = np.where(mask, INF, 0.0)
    d = np.pad(d, 1, constant_values=INF if edge_inside else 0.0)
    for y in range(1, h + 1):
        row = d[y]; up = d[y - 1]
        for x in range(1, w + 1):
            if row[x]:
                row[x] = min(row[x], up[x] + 1, up[x - 1] + 1.414, up[x + 1] + 1.414, row[x - 1] + 1)
    for y in range(h, 0, -1):
        row = d[y]; dn = d[y + 1]
        for x in range(w, 0, -1):
            if row[x]:
                row[x] = min(row[x], dn[x] + 1, dn[x - 1] + 1.414, dn[x + 1] + 1.414, row[x + 1] + 1)
    return d[1:-1, 1:-1]

def blur(a, n=1):
    k = np.array([1, 2, 1], float) / 4
    for _ in range(n):
        a = np.apply_along_axis(lambda v: np.convolve(v, k, 'same'), 0, a)
        a = np.apply_along_axis(lambda v: np.convolve(v, k, 'same'), 1, a)
    return a

def gaps_of(a, dark):
    """Dark pixels joined to the outside through dark pixels: the outline and the black gaps
    between parts (arm and body, the legs). Dark pixels not joined - pupils, mouths, brows - are not."""
    h, w = a.shape
    g = np.zeros((h + 2, w + 2), bool); g[np.pad(~a, 1, constant_values=True)] = True
    dk = np.pad(dark & a, 1)
    while True:
        g2 = g | (dk & (np.roll(g, 1, 0) | np.roll(g, -1, 0) | np.roll(g, 1, 1) | np.roll(g, -1, 1)))
        if (g2 == g).all(): break
        g = g2
    return g[1:-1, 1:-1] & a

def enhance_cell2(c, strength=1.4, tones=8, soft_gaps=True, warm_outline=True):
    """Each part (the light areas parted by the sprite's dark lines) rounded as its own shape and
    shaded on a smooth ramp; the black gaps between parts softened to a deep shadow of the colour
    beside them; the outer outline a warm near-black. Same pixels, same alpha."""
    a = c[:, :, 3] > 0
    if a.sum() < 6: return c
    rgb = c[:, :, :3].astype(float); lum = rgb.sum(2)
    dark = lum < 110
    px = c[a][:, :3]; cols, cnt = np.unique(px, axis=0, return_counts=True)
    share = {tuple(k): v / len(px) for k, v in zip(cols.tolist(), cnt.tolist())}
    rare = np.zeros(a.shape, bool)
    ys, xs = np.nonzero(a)
    for y, x in zip(ys, xs):
        if share[tuple(c[y, x, :3].tolist())] < 0.012: rare[y, x] = True
    light = a & ~dark
    if light.sum() < 4: return c
    black = lum < 45                                                # the outline and gaps are near-black; the brown hair band is not
    gap = gaps_of(a, black)
    pa = np.pad(a, 1)
    outer = a & ~(pa[:-2, 1:-1] & pa[2:, 1:-1] & pa[1:-1, :-2] & pa[1:-1, 2:])
    # each part its own rounded shape: distance from the nearest dark line or edge (a tile drawn
    # to the cell's border runs on: its border is not an edge, so tiles stay seamless)
    d = chamfer(light, edge_inside=True)
    d = np.minimum(d, 12.0)
    hgt = blur(np.where(light, np.sqrt(np.clip(d, 0, None)) * 1.7, 0), 1)
    gy, gx = np.gradient(hgt)
    n = np.dstack([-gx, -gy, np.ones_like(hgt) * 0.85]); n /= np.linalg.norm(n, axis=2, keepdims=True)
    lit = n @ LIGHT
    t = np.clip((lit - 0.50) / 0.42, -1, 1)
    q = np.round((t + 1) / 2 * (tones - 1)) / (tones - 1)           # 0..1 in tone steps
    k = 1 + strength * (0.78 + 0.40 * q - 1.0)                    # 0.78 shadow .. 1.18 highlight
    warm = np.array([1.03, 1.0, 0.93]); cool = np.array([0.95, 0.97, 1.06])
    tint = warm[None, None] * q[:, :, None] + cool[None, None] * (1 - q[:, :, None])
    out = rgb.copy()
    mid = a & dark & ~black & ~rare
    if mid.any():
        dm = np.minimum(chamfer(a, edge_inside=True), 12.0); hm = blur(np.where(a, np.sqrt(np.clip(dm, 0, None)) * 1.7, 0), 1)
        gy2, gx2 = np.gradient(hm); n2 = np.dstack([-gx2, -gy2, np.ones_like(hm) * 0.85]); n2 /= np.linalg.norm(n2, axis=2, keepdims=True)
        k2 = 1 + strength * 0.35 * np.clip(((n2 @ LIGHT) - 0.5) / 0.42, -1, 1)
        out[mid] = np.clip(rgb[mid] * k2[mid][:, None], 0, 255)
    sh = light & ~rare
    out[sh] = np.clip(rgb[sh] * k[sh][:, None] * tint[sh], 0, 255)
    if soft_gaps:
        # gaps between parts (not the outer edge): a deep shadow of the colour beside them
        inner_gap = gap & ~outer
        if inner_gap.any():
            src = out.copy(); have = light.copy()
            for _ in range(4):
                need = inner_gap & ~have
                if not need.any(): break
                for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
                    nb = np.roll(np.roll(src, dy, 0), dx, 1); nh = np.roll(np.roll(have, dy, 0), dx, 1)
                    t2 = need & nh & ~have
                    src[t2] = nb[t2]; have |= t2
            ok = inner_gap & have
            out[ok] = src[ok] * np.array([0.34, 0.32, 0.36])       # a deep, slightly cool shadow, not mud
    if warm_outline:
        # the outer edge: a warm near-black of the colour inside it, not pure black
        e = outer & black
        if e.any():
            base = np.median(rgb[light], axis=0)
            out[e] = np.clip(base * 0.16 + np.array([10, 4, 2]), 0, 255)
    o = c.copy(); o[:, :, :3] = out.astype(np.uint8)
    return o

def enhance_cell(c, strength=1.0):
    """c: HxWx4 uint8 cell. Returns the enhanced cell (same alpha)."""
    a = c[:, :, 3] > 0
    if a.sum() < 6: return c
    rgb = c[:, :, :3].astype(float)
    lum = rgb.sum(2)
    # what not to touch: the outline and dark lines, and features (colours rare in this frame)
    px = c[a][:, :3]; cols, cnt = np.unique(px, axis=0, return_counts=True)
    share = {tuple(k): v / len(px) for k, v in zip(cols.tolist(), cnt.tolist())}
    rare = np.zeros(a.shape, bool)
    ys, xs = np.nonzero(a)
    for y, x in zip(ys, xs):
        if share[tuple(c[y, x, :3].tolist())] < 0.015: rare[y, x] = True
    keep = (lum < 110) | rare
    shade = a & ~keep
    if shade.sum() < 4: return c
    # the shape: a balloon over the whole figure (so arms, head, body round off), softened
    d = chamfer(a)
    hgt = np.sqrt(np.clip(d, 0, None)) * 1.6
    hgt = blur(np.where(a, hgt, 0), 2)
    gy, gx = np.gradient(hgt)
    n = np.dstack([-gx, -gy, np.ones_like(hgt) * 0.9]); n /= np.linalg.norm(n, axis=2, keepdims=True)
    lit = (n @ LIGHT)                                  # -1..1, about 0.5 on a flat front
    # a 4-step ramp of the pixel's own colour: shadow, base, light, highlight
    t = np.clip((lit - 0.52) / 0.38, -1, 1)
    steps = np.select([t < -0.45, t < 0.15, t < 0.6], [0.80, 0.95, 1.07], 1.17)
    k = 1 + (steps - 1) * strength
    out = rgb.copy()
    # highlights warm, shadows cool, as painted
    warm = np.array([1.02, 1.0, 0.95]); cool = np.array([0.96, 0.98, 1.05])
    tint = np.where((steps > 1)[:, :, None], warm, np.where((steps < 0.9)[:, :, None], cool, 1.0))
    out[shade] = np.clip(rgb[shade] * k[shade][:, None] * tint[shade], 0, 255)
    o = c.copy(); o[:, :, :3] = out.astype(np.uint8)
    return o

def read_dmi(path):
    im = Image.open(path); desc = im.info.get('Description', '')
    w = h = 32
    for line in desc.splitlines():
        s = line.strip()
        if s.startswith('width ='): w = int(s.split('=')[1])
        elif s.startswith('height ='): h = int(s.split('=')[1])
    return im, desc, w, h

def enhance_dmi(path, out_dmi, out_png=None, cell=None):
    im, desc, w, h = read_dmi(path)
    sheet = np.asarray(im.convert('RGBA')).copy()
    H, W = sheet.shape[:2]
    cell = cell or enhance_cell2
    for y in range(0, H - h + 1, h):
        for x in range(0, W - w + 1, w):
            sheet[y:y + h, x:x + w] = cell(sheet[y:y + h, x:x + w])
    os.makedirs(os.path.dirname(out_dmi), exist_ok=True)
    info = PngImagePlugin.PngInfo(); info.add_text('Description', desc, zip=True)
    Image.fromarray(sheet).save(out_dmi, 'PNG', pnginfo=info)
    return sheet

def _hsv(rgb):
    r, g, b = rgb[..., 0] / 255.0, rgb[..., 1] / 255.0, rgb[..., 2] / 255.0
    mx = np.maximum(np.maximum(r, g), b); mn = np.minimum(np.minimum(r, g), b); d = mx - mn
    h = np.zeros_like(mx)
    m = d > 1e-6
    rr = m & (mx == r); gg = m & (mx == g) & ~rr; bb = m & ~rr & ~gg
    h[rr] = ((g - b)[rr] / d[rr]) % 6; h[gg] = (b - r)[gg] / d[gg] + 2; h[bb] = (r - g)[bb] / d[bb] + 4
    h = h / 6.0
    s = np.where(mx > 0, d / np.maximum(mx, 1e-6), 0)
    return h, s, mx

METAL_TIERS = {'iron', 'silver', 'gold', 'adamantium', 'diamond', 'hell', 'magic', 'dragon', 'chitin', 'dragonfang', 'spiderfang'}

def enhance_gear_cell(c, contrast=1.25, rim=0.38, glint=0.5, matte=0.55, metal_all=False):
    """Armour and weapons: metal keeps the sprite's own drawn panels and gets crisper - more contrast,
    a bright rim on its top-left edges, a dark one on its bottom-right, and a glint where the light
    hits; wood, leather and cloth get the soft pass at a lower strength. Same pixels, same alpha."""
    a = c[:, :, 3] > 0
    if a.sum() < 4: return c
    rgb = c[:, :, :3].astype(float); lum = rgb.sum(2)
    h, s, v = _hsv(rgb)
    dark = lum < 110
    steel = a & ~dark & (s < 0.22) & (v > 0.30)
    gold = a & ~dark & (h > 0.08) & (h < 0.18) & (s > 0.35) & (v > 0.45)
    metal = steel | gold
    if metal_all:
        # a metal tier: every bright piece is its metal (adamantium's blue, hell's red), but not the
        # wood and leather of grips and hafts (brown, not bright)
        woodish = (h > 0.02) & (h < 0.12) & (s > 0.3) & (v < 0.62)
        metal = a & ~dark & ~woodish & (v > 0.28)
        steel = metal & ~gold
    # the rest: the soft pass, gentler
    soft = enhance_cell2(c, strength=matte).astype(float)
    out = np.where(metal[:, :, None], rgb, soft[:, :, :3])
    if metal.sum() >= 3:
        # contrast about each metal colour family's mean, so the drawn panels read sharper
        for m_ in (steel, gold):
            if m_.sum() < 3: continue
            mean = rgb[m_].mean(0)
            out[m_] = mean + (rgb[m_] - mean) * contrast
        # rims: lit on the edge facing the light (up/left), shaded on the far edge (down/right)
        pa = np.pad(a & ~dark, 1)
        up_open = ~pa[:-2, 1:-1]; left_open = ~pa[1:-1, :-2]; dn_open = ~pa[2:, 1:-1]; rt_open = ~pa[1:-1, 2:]
        lit_edge = metal & (up_open | left_open) & ~(dn_open & rt_open)
        far_edge = metal & (dn_open | rt_open) & ~(up_open | left_open)
        out[lit_edge] = out[lit_edge] + (255 - out[lit_edge]) * rim
        out[far_edge] = out[far_edge] * 0.82
        # a glint: the few metal pixels most turned to the light
        d = np.minimum(chamfer(metal), 6.0)
        hgt = blur(np.where(metal, np.sqrt(d) * 1.7, 0), 1)
        gy, gx = np.gradient(hgt)
        nrm = np.dstack([-gx, -gy, np.ones_like(hgt) * 0.85]); nrm /= np.linalg.norm(nrm, axis=2, keepdims=True)
        lit = nrm @ LIGHT
        vals = lit[metal]
        if len(vals) >= 6:
            th = np.percentile(vals, 93)
            g_ = metal & (lit >= th) & (lit > 0.62)
            tint = np.where(gold[:, :, None], np.array([255, 250, 210.0]), np.array([255, 255, 255.0]))
            out[g_] = out[g_] + (tint[g_] - out[g_]) * glint
        # the far side of a rounded piece a touch darker (form), not a flat plate
        sh = metal & (lit < np.percentile(vals, 20)) if len(vals) >= 6 else np.zeros_like(metal)
        out[sh] = out[sh] * 0.9
    o = c.copy(); o[:, :, :3] = np.clip(out, 0, 255).astype(np.uint8)
    return o


if __name__ == '__main__':
    outroot = sys.argv[1]
    targets = sys.argv[2:]
    cell_for = lambda rel: None
    if targets and targets[0] == '--gear':
        # armour and weapons with the metal-aware pass: the worn 64 px gear (Gear64), the 32 px item
        # pictures (Gear), and the original game's armour and weapon icons; from the untouched originals
        here = os.path.dirname(os.path.abspath(__file__))
        SRC = os.path.join(here, '..', '..', 'restore-points')
        targets = []
        for top in ('Gear64', 'Gear'):
            for root, _, files in os.walk(os.path.join(SRC, 'sprites-before-enhance-20261024', top)):
                for fn in sorted(files):
                    if fn.endswith('.dmi') and fn != 'fx.dmi':
                        targets.append(os.path.relpath(os.path.join(root, fn), SRC))
        OLD_GEAR = ['BoneItems', 'BoneSpear', 'Clan Armor', 'Crystal Sword of Fate', 'GemItems', 'GoblinBuckler', 'GoblinSword', 'GoldItems',
                    'Gremlin Equipment', 'HolyItems', 'HolyShield', 'HolySkornArmour', 'LeatherItems', 'LizardItems', 'MetalObjects', 'MetalObjects2',
                    'Quiver', 'Robe', 'RoyalItems', 'SN Leather items', 'Scale Armour', 'Shapeshifter_Armor', 'SilverItems', 'SkornArmour', 'Spear',
                    'StoneItems', 'Superbone', 'TrimmedMetal', 'UnholyShield', 'WoodItems', 'Jewelry']
        for n in OLD_GEAR:
            rel = os.path.join('world-icons-before-enhance-20261024', 'Icons', n + '.dmi')
            if os.path.exists(os.path.join(SRC, rel)): targets.append(rel)
        def cell_for(rel):
            tier = os.path.basename(rel)[:-4]
            all_metal = tier in METAL_TIERS or tier.startswith('old-Metal') or tier in ('MetalObjects', 'MetalObjects2', 'GoldItems', 'SilverItems', 'TrimmedMetal')
            return lambda c: enhance_gear_cell(c, metal_all=all_metal)
    if targets and targets[0] == '--world':
        # the 32 px world icons (floors, walls, items, buildings, furniture): every .dmi in game/
        # outside Icons/Remastered, read from the game itself (they have no enhanced copy installed)
        # (from their backup since they were installed, 2026-10-24: never shade them twice)
        SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'restore-points', 'world-icons-before-enhance-20261024')
        targets = []
        for root, _, files in os.walk(SRC):
            if os.path.join('Icons', 'Remastered') in root: continue
            for fn in sorted(files):
                # not the HUD, text, selection and effect icons: those are flat on purpose
                if fn in WORLD_SKIP: continue
                if fn.endswith('.dmi'): targets.append(os.path.relpath(os.path.join(root, fn), SRC))
    if not targets:
        for top in FOLDERS:
            for root, _, files in os.walk(os.path.join(SRC, top)):
                for fn in sorted(files):
                    if fn.endswith('.dmi'): targets.append(os.path.relpath(os.path.join(root, fn), SRC))
    import export_sprites_lib as ex
    for i, rel in enumerate(targets):
        orel = rel.split(os.sep, 1)[1] if rel.startswith(('sprites-before-enhance-', 'world-icons-before-enhance-')) else rel
        out_dmi = os.path.join(outroot, '_dmi', orel)
        if os.path.exists(out_dmi) and os.path.getmtime(out_dmi) > os.path.getmtime(__file__): continue   # resume
        try: enhance_dmi(os.path.join(SRC, rel), out_dmi, cell=cell_for(rel))
        except Exception as e:
            print('skip (not a readable icon):', rel, type(e).__name__, flush=True); continue
        ex.sheet(out_dmi, os.path.join(outroot, orel[:-4] + '.png'), orel)
        if i % 25 == 0: print(i, rel, flush=True)
    print('done', len(targets))
