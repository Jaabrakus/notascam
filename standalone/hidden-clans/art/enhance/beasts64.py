#!/usr/bin/env python3
"""Huge animated beasts for the 3D view: dragons and spiders from 3D-rendered sprite packs,
made pixel art (drawn at half resolution: shading in flat bands, a small fixed palette per
variant, hard edges, a dark outline; then doubled), recoloured to the game's variants, in 8
facings and a few animations.

    python3 standalone/remastered/art/enhance/beasts64.py [--only dragon] [--variants red] [--preview DIR]

Reads the packs (read only; PACKS below) and writes, under game/:
  Icons/Remastered/Beasts/<beast>/<variant>/<anim>-<facing>.png   an atlas per animation and
                    facing: its frames left to right, ATLAS_COLS to a row, each cropped to the
                    animation's extent so every frame shares one ground point
  Code/Remastered/BeastData.dm    what the 3D view needs to cut and place them
Facings are the pack's angles: 000 seen from behind, 090 facing right, 180 facing the viewer.
"""

import argparse
import glob
import os
import sys

import numpy as np
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import remaster64 as rm  # noqa: E402

GAME = rm.GAME
OUT = os.path.join(GAME, "Icons", "Remastered", "Beasts")
OUT_DM = os.path.join(GAME, "Code", "Remastered", "BeastData.dm")
DOWNLOADS = os.path.expanduser("~/Downloads")
FACINGS = ("000", "045", "090", "135", "180", "225", "270", "315")
ATLAS_COLS = 8
PPT = 64   # atlas pixels per tile at a beast's size 1 (as the 64 px bodies)

# Dragon colours as dragons.dmi names them: a ramp from shadow to highlight, laid over the
# pack's pale skin by brightness (so its shading stays).
DRAGON_RAMPS = {
    "red": [(26, 4, 4), (84, 12, 10), (150, 26, 18), (204, 64, 26), (240, 150, 70)],
    "red2": [(24, 2, 12), (70, 8, 30), (128, 18, 48), (180, 46, 70), (230, 120, 130)],
    "black": [(8, 8, 12), (30, 30, 36), (58, 58, 68), (96, 96, 108), (150, 150, 162)],
    "ice": [(54, 84, 124), (112, 152, 196), (176, 212, 238), (222, 238, 250), (255, 255, 255)],
    "green": [(8, 28, 8), (26, 74, 22), (54, 124, 38), (104, 176, 58), (176, 220, 108)],
    "sand": [(64, 44, 18), (124, 94, 46), (176, 146, 86), (218, 192, 136), (246, 230, 190)],
    "blue": [(8, 14, 46), (22, 38, 104), (46, 76, 166), (96, 136, 218), (168, 198, 250)],
    "zombie": [(18, 28, 18), (40, 84, 44), (70, 150, 80), (120, 214, 120), (196, 250, 180)],
}
# Spider castes keep the original sprites' marking colours on the pack's glowing parts.
SPIDER_HUES = {"warrior": None, "worker": 52, "hunter": 110, "queen": 225}

# Animations added after the first atlases were drawn: left out of the palette, so the atlases
# drawn before keep matching.
LATER = {"death"}

BEASTS = {
    "dragon": dict(
        pack=os.path.join(DOWNLOADS, "Light_Skin_Uncompressed_Frames", "Frames_512x512"),
        cut=200,            # the pack's baked shadow is part-transparent: below this goes
        ground=(256, 310),  # where the dragon stands in its frames (its baked shadow's middle)
        art=0.5,            # drawn at half the pack's resolution, then doubled: pixel art
        bands=6,            # its shading in this many flat bands
        colours=16,
        # game animation: (pack animation, frames kept, frames a second)
        anims={"idle": ("Ground_Idle", 6, 6), "walk": ("Ground_Walk", 8, 10), "attack": ("Ground_Attack", 8, 10),
               "breathe": ("Ground_Breathe", 8, 8), "fly": ("Fly_Cycle", 8, 10),
               # played once as it rises or comes down (the page eases its height meanwhile)
               "takeoff": ("Fly_TakeOff", 8, 8), "land": ("Fly_Land", 8, 8),
               "flybreathe": ("Fly_Breathe", 10, 10),
               # played once as it dies, then held: how its body lies (Beasts.dm RmBeastCorpse3D)
               "death": ("Ground_Death", 10, 10)},
        variants=list(DRAGON_RAMPS)),
    "spider": dict(
        pack=os.path.join(DOWNLOADS, "256x256"),
        cut=128,
        ground=None,        # its own shadow frames say (Shadow/)
        art=0.5,
        bands=None,
        colours=16,
        anims={"idle": ("Idle", 8, 8), "walk": ("Walk", 10, 12), "attack": ("Attack1", 8, 10), "death": ("Death1", 10, 12)},
        variants=list(SPIDER_HUES)),
}


def frames_of(beast, anim, facing):
    """The pack frames an animation keeps for one facing, evenly spread."""
    b = BEASTS[beast]
    name, keep, _ = b["anims"][anim]
    files = sorted(glob.glob(os.path.join(b["pack"], name, "Body", facing, "*.png")))
    if not files:
        raise FileNotFoundError(os.path.join(b["pack"], name, "Body", facing))
    return [files[int(i * len(files) / keep)] for i in range(keep)]


def body(path, cut):
    a = np.asarray(Image.open(path).convert("RGBA")).copy()
    solid = a[..., 3] >= cut
    a[~solid] = 0
    a[solid, 3] = 255
    return a


def ramp(a, stops, bands=None):
    """Brightness laid over a colour ramp (in `bands` flat steps)."""
    out = a.copy()
    lum = np.clip(a[..., :3].astype(np.float32).mean(-1) / 225.0, 0, 1)
    if bands:
        lum = np.round(lum * (bands - 1)) / (bands - 1)
    s = np.array(stops, np.float32)
    t = lum * (len(s) - 1)
    i = np.clip(t.astype(int), 0, len(s) - 2)
    f = (t - i)[..., None]
    out[..., :3] = (s[i] * (1 - f) + s[i + 1] * f).astype(np.uint8)
    return out


def hue_to(a, hue):
    """The glowing warm parts turned to another hue (their light and depth kept)."""
    if hue is None:
        return a
    rgb = a[..., :3].astype(np.float32) / 255.0
    mx, mn = rgb.max(-1), rgb.min(-1)
    sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    warm = (sat > 0.35) & (r >= g) & (r >= b) & (mx > 0.25)
    # rebuild the colour at the new hue with the same value and saturation (HSV to RGB)
    k = (np.array([5, 3, 1]) + hue / 60.0) % 6
    chan = mx[..., None] - mx[..., None] * sat[..., None] * np.clip(np.minimum(k, 4 - k), 0, 1)[None, None, :]
    out = a.copy()
    out[warm, :3] = (np.clip(chan[warm], 0, 1) * 255).astype(np.uint8)
    return out


def variant(beast, a, v):
    return ramp(a, DRAGON_RAMPS[v], BEASTS[beast]["bands"]) if beast == "dragon" else hue_to(a, SPIDER_HUES[v])


def small(beast, a):
    """A frame at the art's resolution: smoothed of the render's fine noise, averaged down, hard-edged."""
    f = BEASTS[beast]["art"]
    h, w = a.shape[:2]
    out = np.asarray(Image.fromarray(a).filter(ImageFilter.MedianFilter(3)).resize((int(w * f), int(h * f)), Image.BOX)).copy()
    solid = out[..., 3] >= 128
    out[~solid] = 0
    out[solid, 3] = 255
    return out


def art(beast, path, v):
    """A pack frame as the variant's pixel art, at the art's resolution."""
    return small(beast, variant(beast, body(path, BEASTS[beast]["cut"]), v))


def ground_of(beast, anim):
    """Where the beast stands in its frames: given, or the middle of its own shadow frames."""
    b = BEASTS[beast]
    if b["ground"]:
        return b["ground"]
    pts = []
    for f in FACINGS:
        for p in sorted(glob.glob(os.path.join(b["pack"], b["anims"][anim][0], "Shadow", f, "*.png")))[::4]:
            al = np.asarray(Image.open(p).convert("RGBA"))[..., 3]
            ys, xs = np.nonzero(al > 20)
            if len(ys):
                pts.append((xs.mean(), ys.mean()))
    x, y = np.mean(pts, 0)
    return int(round(x)), int(round(y))


def extent(beast, anim):
    """The box every kept frame of an animation fits in (all facings), a pixel round it."""
    b = BEASTS[beast]
    x0 = y0 = 10 ** 6
    x1 = y1 = 0
    for f in FACINGS:
        for p in frames_of(beast, anim, f):
            al = np.asarray(Image.open(p).convert("RGBA"))[..., 3] >= b["cut"]
            ys, xs = np.nonzero(al)
            x0, x1, y0, y1 = min(x0, xs.min()), max(x1, xs.max()), min(y0, ys.min()), max(y1, ys.max())
    m = int(round(2 / b["art"]))   # room for the outline, a pixel of the art round it
    return x0 - m, y0 - m, x1 + m + 1, y1 + m + 1


def palette(beast, v):
    """One palette for a variant (from a spread of its frames), so colours hold still across frames."""
    b = BEASTS[beast]
    picks = []
    for anim in b["anims"]:
        if anim in LATER:   # drawn after the rest: keep the palette they were drawn with
            continue
        for f in FACINGS[::2]:
            fs = frames_of(beast, anim, f)
            picks.append(art(beast, fs[len(fs) // 2], v))
    px = np.concatenate([p[p[..., 3] > 0][:, :3] for p in picks])[::7]
    side = int(np.ceil(np.sqrt(len(px))))
    sample = np.zeros((side * side, 3), np.uint8)
    sample[:len(px)] = px
    sample[len(px):] = px[0]
    return Image.fromarray(sample.reshape(side, side, 3)).quantize(b["colours"], method=Image.Quantize.MEDIANCUT)


def pixelify(beast, a, pal, size):
    """Art-resolution frame -> the fixed palette (no dithering), a dark outline, doubled back
    up to the pack's size with hard pixels."""
    solid = a[..., 3] > 0
    q = np.asarray(Image.fromarray(a[..., :3]).quantize(palette=pal, dither=Image.Dither.NONE).convert("RGB"))
    out = np.zeros_like(a)
    out[solid, :3] = q[solid]
    out[solid, 3] = 255
    return np.asarray(Image.fromarray(rm.outline(out)).resize(size, Image.NEAREST))


def save_indexed(a, path):
    """An 8-bit palette PNG (a fifth of the size): exact when the atlas has 256 colours or
    fewer, as the fixed palette and its outline shades give."""
    flat = a.reshape(-1, 4)
    flat = np.where(flat[:, 3:4] > 0, flat, 0)
    cols, idx = np.unique(flat, axis=0, return_inverse=True)
    if len(cols) > 256:
        Image.fromarray(a).quantize(256, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE).save(path, optimize=True)
        return
    im = Image.fromarray(idx.reshape(a.shape[:2]).astype(np.uint8), "P")
    im.putpalette(cols[:, :3].astype(np.uint8).flatten().tolist())
    im.save(path, optimize=True, transparency=bytes(cols[:, 3].astype(np.uint8).tolist()))


def build(beast, variants, out_root, only_anims=None):
    b = BEASTS[beast]
    meta = {}
    for anim, (_, keep, fps) in b["anims"].items():
        x0, y0, x1, y1 = extent(beast, anim)
        gx, gy = ground_of(beast, anim)
        cols = min(keep, ATLAS_COLS)
        rows = -(-keep // cols)
        meta[anim] = dict(frames=keep, cols=cols, w=x1 - x0, h=y1 - y0, px=gx - x0, py=gy - y0, fps=fps, box=(x0, y0, x1, y1))
    for v in variants:
        pal = palette(beast, v)
        folder = os.path.join(out_root, beast, v)
        os.makedirs(folder, exist_ok=True)
        for anim, m in meta.items():
            if only_anims and anim not in only_anims:
                continue
            x0, y0, x1, y1 = m["box"]
            w, h, cols = m["w"], m["h"], m["cols"]
            rows = -(-m["frames"] // cols)
            for f in FACINGS:
                atlas = np.zeros((rows * h, cols * w, 4), np.uint8)
                for k, p in enumerate(frames_of(beast, anim, f)):
                    full = Image.open(p).size
                    a = pixelify(beast, art(beast, p, v), pal, full)[y0:y1, x0:x1]
                    r, c = divmod(k, cols)
                    atlas[r * h:(r + 1) * h, c * w:(c + 1) * w] = a
                save_indexed(atlas, os.path.join(folder, f"{anim}-{f}.png"))
        print(beast, v, "done", flush=True)
    return meta


# Where the jaws are, for the page to start a dragon's breath there: per animation, per facing.
MOUTH_ANIMS = {"dragon": ("breathe", "flybreathe", "attack")}


def mouth_points(beast, meta, out_root):
    """For each animation in MOUTH_ANIMS, each facing and each frame: the tip of the head (atlas
    pixels). The pack's camera looks down at the beast, so a facing of a degrees (0 away from the
    camera, 90 to its right) points up the picture at about half its depth. What stays solid
    through the whole animation is body, neck, head and tail (the wings flap, so they drop out):
    the tip of that, from the body's middle along the facing, is the head; in each frame the
    farthest solid pixel near it is where the jaws are then (the head dips and lunges)."""
    out = {}
    variant = BEASTS[beast]["variants"][0]
    for anim in MOUTH_ANIMS.get(beast, ()):
        m = meta[anim]
        n, w, h, cols, px, py = m["frames"], m["w"], m["h"], m["cols"], m["px"], m["py"]
        pts = []
        for f in FACINGS:
            a = np.asarray(Image.open(os.path.join(out_root, beast, variant, f"{anim}-{f}.png")).convert("RGBA"))
            frames = np.array([a[(k // cols) * h:(k // cols + 1) * h, (k % cols) * w:(k % cols + 1) * w, 3] > 0 for k in range(n)])
            th = np.radians(int(f))
            dx, dy = np.sin(th), -np.cos(th) * 0.55
            dx, dy = dx / np.hypot(dx, dy), dy / np.hypot(dx, dy)
            cx, cy = px, py * 0.75
            ys, xs = np.nonzero(frames.mean(0) >= 0.8)
            along, off = (xs - cx) * dx + (ys - cy) * dy, np.abs((ys - cy) * dx - (xs - cx) * dy)
            k = np.argmax(np.where(off <= 0.7 * np.maximum(along, 0) + 30, along, -1e9))   # in a cone ahead of the body
            head = (xs[k], ys[k])
            for fr in frames:
                ys, xs = np.nonzero(fr)
                near = np.hypot(xs - head[0], ys - head[1]) <= 30
                if not near.any():
                    pts += [int(head[0]), int(head[1])]
                    continue
                k = np.argmax(np.where(near, (xs - cx) * dx + (ys - cy) * dy, -1e9))
                pts += [int(xs[k]), int(ys[k])]
        out[anim] = pts
    return out


def meta_from_dm():
    """The atlases' cuts as BeastData.dm has them (for --mouths, which redoes only the jaws)."""
    import re
    text = open(OUT_DM).read()
    metas = {}
    for beast, body in re.findall(r'^\t"(\w+)"=list\("anims"=list\((.*?)\), "variants"', text, flags=re.M):
        metas[beast] = {a: dict(zip(("frames", "cols", "w", "h", "px", "py", "fps"), map(int, v.split(", "))))
                        for a, v in re.findall(r'"(\w+)"=list\(([\d, ]+)\)', body)}
    return text, metas


def dm_data(metas):
    lines = ["// Generated by art/enhance/beasts64.py (do not edit): how the 3D view cuts the beasts'",
             "// atlases (Icons/Remastered/Beasts/<beast>/<variant>/<anim>-<facing>.png). Per animation:",
             "// frames, atlas columns, frame width and height, the ground point (x, y) in a frame, frames a second.",
             f"#define RM_BEAST_PPT {PPT}",
             "var/list/rm_beast_facings = list(" + ", ".join(f'"{f}"' for f in FACINGS) + ")",
             "var/list/rm_beasts = list("]
    items = []
    for beast, (meta, variants) in metas.items():
        anims = ", ".join(f'"{a}"=list({m["frames"]}, {m["cols"]}, {m["w"]}, {m["h"]}, {m["px"]}, {m["py"]}, {m["fps"]})' for a, m in meta.items())
        vs = ", ".join(f'"{v}"' for v in variants)
        items.append(f'\t"{beast}"=list("anims"=list({anims}), "variants"=list({vs}))')
    lines.append(",\n".join(items))
    lines.append(")")
    lines.append(mouths_dm(metas))
    return "\n".join(lines) + "\n"


def mouths_dm(metas):
    mouths = []   # MOUTH_ANIMS: x, y of the jaws in each frame, for each facing in rm_beast_facings' order
    for beast, (meta, _) in metas.items():
        pts = mouth_points(beast, meta, OUT)
        if pts:
            mouths.append(f'\t"{beast}"=list(' + ", ".join(f'"{a}"=list({", ".join(map(str, v))})' for a, v in pts.items()) + ")")
    return "var/list/rm_beast_mouths = list(\n" + ",\n".join(mouths) + ")"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--only", default=None, help="beasts to build (comma separated)")
    ap.add_argument("--variants", default=None, help="only these variants (comma separated)")
    ap.add_argument("--preview", default=None, help="write the atlases under this folder (no game data)")
    ap.add_argument("--anims", default=None, help="draw only these animations (comma separated); the data still lists all")
    ap.add_argument("--mouths", action="store_true", help="only find the jaws again, in the atlases already made")
    a = ap.parse_args()
    if a.mouths:
        text, metas = meta_from_dm()
        start = text.index("var/list/rm_beast_mouths")
        with open(OUT_DM, "w") as fh:
            fh.write(text[:start] + mouths_dm({b: (m, None) for b, m in metas.items()}) + "\n")
        print(OUT_DM)
        return
    out_root = a.preview or OUT
    metas = {}
    for beast in BEASTS:
        if a.only and beast not in a.only.split(","):
            continue
        variants = [v for v in BEASTS[beast]["variants"] if not a.variants or v in a.variants.split(",")]
        metas[beast] = (build(beast, variants, out_root, a.anims and a.anims.split(",")), BEASTS[beast]["variants"])
    if not a.preview and not a.only and not a.variants:
        with open(OUT_DM, "w") as fh:
            fh.write(dm_data(metas))
        print(OUT_DM)
    for beast, (meta, _) in metas.items():
        print(beast, {k: (m["frames"], m["w"], m["h"], m["px"], m["py"]) for k, m in meta.items()})


if __name__ == "__main__":
    main()
