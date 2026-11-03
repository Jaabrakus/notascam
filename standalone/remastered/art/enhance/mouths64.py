#!/usr/bin/env python3
"""Mouths for the 64 px bodies (game_export.py body_sheet). The faces otherwise stay as the
originals drew them; doubled from 32 px, every race's mouth is the same black bar.

  small   a dwarf's: the bar the wider face stretched, cut back to a short line
  orc     an underbite with two ivory tusks rising from the jaw
  demon   a wide grin, a row of teeth and two fangs
  frog    a long thin grin turned up at the corners over a pale throat, two nostrils
          in place of the nose bar
  smirk   a dark elf's thin smirk
  goblin  a crooked grin with two snaggle teeth
  kobold  a muzzle's "w" and a little fang
  lizard  a long thin mouth turned down at the corners, a forked tongue
  zombie  a ragged open mouth with broken teeth
  vampire a thin closed mouth and two fangs
  gargoyle a stone snarl: open, the corners pulled down, fangs from both jaws

The old mouth is found as the dark bars across the middle of the face (front view) and
along the lower face (profile), so the new one sits where it was in every walk frame.
"""

import numpy as np

IVORY, IVORY_TIP, IVORY_BASE = (234, 224, 186), (250, 246, 222), (192, 178, 136)
TEETH = (244, 240, 226)
GULLET = (52, 6, 6)
# the shortest bar that is the old mouth, per style (the doubled originals' mouths are 4 to 16 wide)
LEAST = {"frog": 10, "orc": 8, "demon": 8, "small": 8, "goblin": 4, "kobold": 4, "smirk": 5, "vampire": 5, "gargoyle": 6}
STONE_FANG, STONE_MAW = (206, 202, 192), (28, 24, 24)


def dark(c64):
    return (c64[..., 3] > 0) & (c64[..., :3].astype(int).sum(-1) < 120)


def bars(c64, rows, least=6, centre=31.5, reach=5):
    """Dark runs at least `least` long across the middle of the face: [(y, x0, x1)], x1 past the end."""
    d = dark(c64)
    out = []
    for y in rows:
        if not 0 <= y < 64:
            continue
        x = 0
        while x < 64:
            if d[y, x]:
                x1 = x
                while x1 < 64 and d[y, x1]:
                    x1 += 1
                if x1 - x >= least and abs((x + x1 - 1) / 2.0 - centre) <= reach:
                    out.append((y, x, x1))
                x = x1
            else:
                x += 1
    return out


def top_of(c64):
    ys = np.flatnonzero((c64[..., 3] > 0).any(1))
    return ys.min() if len(ys) else None


def put(a, x, y, c):
    if 0 <= y < 64 and 0 <= x < 64:
        a[y, x, :3] = c
        a[y, x, 3] = 255


def shade(c, k):
    return tuple(int(max(0, min(255, v * k))) for v in c)


def mix(c, d, k):
    return tuple(int(round(u * (1 - k) + v * k)) for u, v in zip(c, d))


def paint_out(a, runs, above):
    """The old bar's pixels take the colour of the row above it (the skin, with its light)."""
    for y, x0, x1 in runs:
        a[y, x0:x1] = above[x0:x1]


def group(runs):
    """The first bar: its runs on consecutive rows."""
    runs = sorted(runs)
    if not runs:
        return []
    out = [runs[0]]
    for r in runs[1:]:
        if r[0] == out[-1][0] + 1:
            out.append(r)
        elif r[0] > out[-1][0] + 1:
            break
    return out


def front(c64, style, at, width=6, top=None):
    """The front view's mouth redrawn. at: the old mouth's row below the top of the sprite, or
    of `top` (measured on the standing frame; searched two rows either side)."""
    top = top_of(c64) if top is None else top
    if top is None:
        return c64
    runs = group(bars(c64, range(top + at - 2, top + at + 3), least=LEAST.get(style, 6)))
    if not runs:
        return c64
    runs = group(bars(c64, range(runs[0][0], runs[0][0] + 4), least=LEAST.get(style, 6)))   # all of the bar
    a = c64.copy()
    y0 = runs[0][0]
    x0, x1 = min(r[1] for r in runs), max(r[2] for r in runs) - 1
    cx = int(round((x0 + x1) / 2.0))
    skin = tuple(int(v) for v in c64[y0 - 1, cx, :3])
    paint_out(a, runs, c64[y0 - 1].copy())
    if style == "small":
        for x in range(cx - width // 2, cx - width // 2 + width):
            put(a, x, y0, tuple(int(v) for v in c64[y0, x0, :3]))
    elif style == "orc":
        line = (26, 40, 12)
        for x in range(cx - 5, cx + 6):                      # the mouth, low: an underbite
            put(a, x, y0 + 1, line)
            put(a, x, y0 + 2, shade(skin, 0.74))               # the jutting lower jaw
        for tx in (cx - 4, cx + 4):                          # tusks up from the jaw
            put(a, tx, y0 - 1, IVORY_TIP)
            put(a, tx, y0, IVORY)
            put(a, tx, y0 + 1, IVORY)
            put(a, tx + (1 if tx > cx else -1), y0 + 1, IVORY_BASE)
    elif style == "demon":
        lip = (34, 0, 0)
        for x in range(cx - 7, cx + 8):                      # a wide grin, open
            put(a, x, y0, lip)
            put(a, x, y0 + 1, GULLET)
        put(a, cx - 8, y0 - 1, lip)                          # the corners turned up
        put(a, cx + 8, y0 - 1, lip)
        for x in range(cx - 6, cx + 7, 2):                   # a row of teeth
            put(a, x, y0 + 1, TEETH)
        for fx in (cx - 4, cx + 4):                          # fangs over the lower lip
            put(a, fx, y0 + 1, TEETH)
            put(a, fx, y0 + 2, TEETH)
    elif style == "smirk":
        line = (12, 8, 30)
        for x in range(cx - 2, cx + 3):
            put(a, x, y0, line)
        put(a, cx + 3, y0 - 1, line)                         # one corner up
    elif style == "goblin":
        line = (26, 18, 0)
        put(a, cx - 4, y0 - 1, line)                         # a grin across the chin, corners up
        put(a, cx + 3, y0 - 1, line)
        for x in range(cx - 3, cx + 3):
            put(a, x, y0, line)
        put(a, cx - 1, y0 + 1, line)                         # open in the middle
        put(a, cx, y0 + 1, line)
        put(a, cx - 2, y0, TEETH)                            # two pointed teeth
        put(a, cx + 1, y0, TEETH)
    elif style == "kobold":
        line = (36, 24, 0)
        put(a, cx - 1, y0 - 2, line)                         # the nose at the end of the muzzle
        put(a, cx, y0 - 2, line)
        for x in (cx - 3, cx - 1, cx, cx + 2):               # a "w" under it
            put(a, x, y0, line)
        for x in (cx - 2, cx + 1):
            put(a, x, y0 + 1, line)
        put(a, cx + 2, y0 + 1, TEETH)                        # a little fang
    elif style == "lizard":
        line = (8, 40, 44)
        for x in range(cx - 6, cx + 6):                      # long and thin
            put(a, x, y0, line)
        put(a, cx - 7, y0 + 1, line)                         # turned down at the corners
        put(a, cx + 6, y0 + 1, line)
        tongue = (200, 40, 50)
        put(a, cx, y0 + 1, tongue)                           # a forked tongue
        put(a, cx - 1, y0 + 2, tongue)
        put(a, cx + 1, y0 + 2, tongue)
    elif style == "zombie":
        for x in range(cx - 4, cx + 4):                      # a ragged open mouth
            put(a, x, y0, GULLET)
            put(a, x, y0 + 1, GULLET)
        for x in (cx - 3, cx - 1, cx + 2):                   # its lower edge uneven
            put(a, x, y0 + 2, GULLET)
        put(a, cx - 4, y0 - 1, GULLET)
        put(a, cx - 2, y0, TEETH)                            # broken teeth
        put(a, cx + 1, y0, TEETH)
        put(a, cx + 1, y0 + 1, TEETH)
    elif style == "vampire":
        line = (60, 0, 8)
        for x in range(cx - 3, cx + 3):                      # a thin closed mouth
            put(a, x, y0, line)
        for fx in (cx - 2, cx + 1):                          # two fangs
            put(a, fx, y0 + 1, TEETH)
            put(a, fx, y0 + 2, TEETH)
    elif style == "gargoyle":
        for x in range(cx - 5, cx + 6):                      # a wide snarl, open
            put(a, x, y0, STONE_MAW)
            put(a, x, y0 + 1, STONE_MAW)
        put(a, cx - 6, y0 + 1, STONE_MAW)                    # the corners pulled down
        put(a, cx + 6, y0 + 1, STONE_MAW)
        for fx in (cx - 4, cx + 4):                          # fangs down from the upper jaw
            put(a, fx, y0, STONE_FANG)
        for fx in (cx - 2, cx + 2):                          # and up from the lower
            put(a, fx, y0 + 1, STONE_FANG)
    elif style == "frog":
        line = (24, 60, 10)
        for x in range(x0 - 1, x1 + 2):                      # a long thin grin
            put(a, x, y0, line)
            put(a, x, y0 + 1, mix(skin, (236, 240, 176), 0.55))   # the pale throat
        put(a, x0 - 2, y0 - 1, line)                         # turned up at the corners
        put(a, x1 + 2, y0 - 1, line)
        nose = group(bars(c64, range(y0 - 6, y0 - 1), least=6))
        if nose:                                             # two nostrils for the nose bar
            paint_out(a, nose, c64[nose[0][0] - 1].copy())
            ny = nose[0][0]
            put(a, cx - 2, ny, line)
            put(a, cx + 2, ny, line)
    return a


def side(c64, style, at, fwd, top=None):
    """A profile's mouth (fwd +1 facing east, -1 west): the frog's grin along the lower face
    with its throat, an orc's tusk or a demon's fang at the front of the jaw. top: as front()."""
    top = top_of(c64) if top is None else top
    if top is None or style == "small":
        return c64
    a = c64.copy()
    al = c64[..., 3] > 0
    if style == "frog":
        runs = [r for r in bars(c64, range(top + at - 2, top + at + 3), least=6, centre=31.5 + 6 * fwd, reach=8)]
        runs = group(runs)
        if not runs:
            return c64
        y0 = runs[0][0]
        x0, x1 = min(r[1] for r in runs), max(r[2] for r in runs) - 1
        skin = tuple(int(v) for v in c64[y0 - 1, (x0 + x1) // 2, :3])
        paint_out(a, runs, c64[y0 - 1].copy())
        line = (24, 60, 10)
        for x in range(x0, x1 + 1):
            put(a, x, y0, line)
            put(a, x, y0 + 1, mix(skin, (236, 240, 176), 0.55))
        back = x0 if fwd > 0 else x1
        put(a, back - fwd, y0 - 1, line)                     # the corner turned up
        return a
    y = top + at
    xs = np.flatnonzero(al[y])
    if not len(xs):
        return c64
    edge = xs.max() if fwd > 0 else xs.min()                  # the outline at the front of the jaw
    x = edge - 2 * fwd
    if style == "orc":
        put(a, x, y - 2, IVORY_TIP)
        put(a, x, y - 1, IVORY)
        put(a, x, y, IVORY)
        put(a, x - fwd, y, IVORY_BASE)
    elif style == "demon":
        put(a, x, y, TEETH)
        put(a, x, y + 1, TEETH)
        put(a, x - fwd, y, GULLET)
    elif style == "gargoyle":
        put(a, x, y, STONE_MAW)
        put(a, x - fwd, y, STONE_MAW)
        put(a, x, y + 1, STONE_FANG)
    return a
