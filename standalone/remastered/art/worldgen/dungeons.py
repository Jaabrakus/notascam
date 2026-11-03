"""Dungeon layouts: one per dungeon place, made from the place's own number, the same every run.

A layout is one or more floors of square tiles plus marks (entrance, stairs, boss, hoard,
treasure, monsters...). The same layout can be used two ways (owner, 10-27):
  - in the world: its first floor is carved into the caves layer right under its cave mouth;
  - as an instance: every floor is made fresh in sealed rock for one party, as Instances.dm does
    today (its 40 x 40 slots would grow to fit).
Floor tiles use the world's kinds: K_CAVEFLOOR solid rock, K_TUNNEL open floor, K_WALL built wall,
K_WATER / K_LAVA / K_CHASM / K_MUSHROOM / K_ORE / K_SNOW as their names say.
"""
import numpy as np

from heartland import *  # noqa: F401,F403

# who lives there: today's cave themes in Instances.dm, and the creatures the game already has
THEMES = {
    "crypt": ("Undead crypt", "skeletons", "a skeleton lord"),
    "tomb": ("Undead crypt", "skeletons", "a vampire in the deepest tomb"),
    "barrow": ("Undead crypt", "zombies", "a barrow king"),
    "cave": ("Ratman burrow", "ratmen", "the ratman king"),
    "ice cave": ("Spider's nest", "cave spiders", "a frost spider queen"),
    "mushroom cavern": ("Spider's nest", "cave spiders and tower caps", "a spider queen"),
    "delving": ("Orc stronghold", "devourers and giant moles", "whatever came up the shafts"),
    "dragon lair": ("Dragon's lair", "dragon young", "a grown dragon on its hoard"),
    "kobold warren": ("Kobold den", "kobolds", "the kobold chieftain"),
    "goblin cave": ("Goblin warren", "goblins", "the goblin commander"),
    "hellgate": ("Hellgate", "demons", "a demon at the gate"),
    "deep hall": ("Deep hall", "svartalfar", "a mind-eater"),
}
FLOORS = {"crypt": 2, "tomb": 3, "barrow": 1, "cave": 2, "ice cave": 1, "mushroom cavern": 1, "delving": 3,
          "dragon lair": 1, "kobold warren": 2, "goblin cave": 1, "hellgate": 3, "deep hall": 2}
SIZE = {"crypt": 72, "tomb": 72, "barrow": 48, "cave": 80, "ice cave": 72, "mushroom cavern": 96, "delving": 80,
        "dragon lair": 120, "kobold warren": 64, "goblin cave": 80, "hellgate": 80, "deep hall": 96}


def _rng(pid, floor, seed):
    return np.random.default_rng((seed * 7919 + pid * 104729 + floor * 1299709) & 0xFFFFFFFF)


def _cellular(rng, n, fill=0.47, steps=5):
    """Natural caverns: random rock, smoothed a few times."""
    g = rng.random((n, n)) < fill
    g[0, :] = g[-1, :] = g[:, 0] = g[:, -1] = True
    for _ in range(steps):
        p = np.pad(g, 1, constant_values=True).astype(int)
        nb = sum(p[1 + dy:n + 1 + dy, 1 + dx:n + 1 + dx] for dy in (-1, 0, 1) for dx in (-1, 0, 1)) - g
        g = (nb >= 5) | ((nb >= 4) & g)
        g[0, :] = g[-1, :] = g[:, 0] = g[:, -1] = True
    return ~g   # True = open


def _keep_connected(open_, start):
    """Only the open ground that can be walked to from start; the rest is filled in."""
    n = open_.shape[0]
    seen = np.zeros_like(open_)
    stack = [start]
    seen[start] = open_[start]
    while stack:
        y, x = stack.pop()
        for yy, xx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
            if 0 <= yy < n and 0 <= xx < n and open_[yy, xx] and not seen[yy, xx]:
                seen[yy, xx] = True
                stack.append((yy, xx))
    return seen


def _carve(g, y0, x0, y1, x1, w=1, kind=K_TUNNEL, wiggle=None):
    """A passage from (y0, x0) to (y1, x1): along one axis, then the other, optionally wobbling."""
    n = g.shape[0]
    y, x = y0, x0
    path = []
    while (y, x) != (y1, x1):
        if wiggle is not None and wiggle.random() < 0.25:
            if wiggle.random() < 0.5 and y != y1:
                y += 1 if y1 > y else -1
            elif x != x1:
                x += 1 if x1 > x else -1
        elif x != x1 and (y == y1 or abs(x1 - x) > abs(y1 - y)):
            x += 1 if x1 > x else -1
        else:
            y += 1 if y1 > y else -1
        path.append((y, x))
    for (py, px) in path:
        sl = g[max(0, py - w + 1):min(n, py + w), max(0, px - w + 1):min(n, px + w)]
        sl[sl == K_CAVEFLOOR] = kind
    return path


def _rooms(rng, n, count, wmin, wmax, sym=False):
    rooms = []
    for _ in range(count * 30):
        w, h = int(rng.integers(wmin, wmax)), int(rng.integers(wmin, wmax))
        x, y = int(rng.integers(2, n - w - 2)), int(rng.integers(2, n - h - 2))
        if all(x + w + 2 < a or a + c + 2 < x or y + h + 2 < b or b + d + 2 < y for a, b, c, d in rooms):
            rooms.append((x, y, w, h))
            if sym and n - x - w > x + w + 2:
                rooms.append((n - x - w, y, w, h))
        if len(rooms) >= count:
            break
    return rooms


def _walled_room(g, x, y, w, h):
    g[y - 1:y + h + 1, x - 1:x + w + 1] = np.where(g[y - 1:y + h + 1, x - 1:x + w + 1] == K_CAVEFLOOR, K_WALL,
                                                   g[y - 1:y + h + 1, x - 1:x + w + 1])
    g[y:y + h, x:x + w] = K_TUNNEL


def _floor(kind, pid, f, nfloors, seed):
    """One floor: (grid, marks). Marks: list of (y, x, what)."""
    rng = _rng(pid, f, seed)
    n = SIZE[kind]
    g = np.full((n, n), K_CAVEFLOOR, np.uint8)
    marks = []
    last = f == nfloors - 1
    entry = (n - 4, n // 2)      # everyone comes in at the bottom middle
    if kind in ("crypt", "tomb", "barrow", "deep hall"):
        sym = kind in ("tomb", "deep hall")
        rooms = _rooms(rng, n, {"crypt": 9, "tomb": 8, "barrow": 4, "deep hall": 7}[kind],
                       5 if kind != "deep hall" else 8, 11 if kind != "deep hall" else 18, sym)
        rooms.sort(key=lambda r: -(r[1] + r[3] / 2))   # nearest the entrance first
        for (x, y, w, h) in rooms:
            _walled_room(g, x, y, w, h)
            if kind == "deep hall":   # pillars down the hall
                for px in range(x + 2, x + w - 1, 4):
                    for py in (y + 2, y + h - 3):
                        g[py, px] = K_WALL
        centres = [(y + h // 2, x + w // 2) for (x, y, w, h) in rooms]
        _carve(g, entry[0], entry[1], *centres[0], w=2 if kind == "deep hall" else 1)
        for a, b in zip(centres, centres[1:]):
            _carve(g, *a, *b, w=2 if kind == "deep hall" else 1)
        for (x, y, w, h) in rooms[1:-1]:
            marks.append((y + h // 2, x + w // 2, "monsters"))
            if kind != "deep hall" and rng.random() < 0.6:
                marks.append((y + 1, x + 1, "sarcophagus"))
            if rng.random() < 0.3:
                marks.append((y + h - 2, x + w - 2, "treasure"))
        far = centres[-1]
        marks.append((*far, "boss" if last else "stairs down"))
        if last:
            marks.append((far[0] - 1, far[1] + 2, "treasure"))
    elif kind in ("cave", "ice cave", "mushroom cavern", "goblin cave", "hellgate"):
        fill = {"cave": 0.47, "ice cave": 0.48, "mushroom cavern": 0.46, "goblin cave": 0.46, "hellgate": 0.47}[kind]
        op = _cellular(rng, n, fill)
        op[entry[0] - 3:entry[0] + 2, entry[1] - 3:entry[1] + 4] = True
        # make sure the far side is reachable: a winding way up the middle
        path = _carve(np.where(op, K_TUNNEL, K_CAVEFLOOR).astype(np.uint8), entry[0], entry[1], 6, n // 2 +
                      int(rng.integers(-n // 4, n // 4)), wiggle=rng)
        for (py, px) in path:
            op[max(0, py - 1):py + 2, max(0, px - 1):px + 2] = True
        op = _keep_connected(op, entry)
        g[op] = K_TUNNEL
        cells = np.argwhere(op)
        far = tuple(cells[np.argmin(cells[:, 0])])
        if kind in ("ice cave", "mushroom cavern"):   # patches: sheets of ice, or stands of giant mushrooms
            patch = _cellular(rng, n, 0.55, 4)
            g[op & patch] = K_SNOW if kind == "ice cave" else K_MUSHROOM
        if kind == "hellgate":
            hot = op & (rng.random(op.shape) < (0.02 + 0.1 * f))
            g[hot] = K_LAVA
        if kind == "goblin cave":   # stake walls across the wider chambers
            for _ in range(4):
                y, x = cells[int(rng.integers(len(cells)))]
                g[y, max(0, x - 3):x + 4][g[y, max(0, x - 3):x + 4] == K_TUNNEL] = K_WALL
                g[y, x] = K_TUNNEL
        for _ in range(5 + 2 * f):
            y, x = cells[int(rng.integers(len(cells)))]
            if abs(y - entry[0]) + abs(x - entry[1]) > 20:
                marks.append((y, x, "monsters"))
        marks.append((*far, "boss" if last else "stairs down"))
        if kind == "hellgate" and last:
            g[far[0] - 2:far[0] + 3, far[1] - 2:far[1] + 3] = K_CHASM
            marks.append((far[0] + 4, far[1], "gate down to the depths"))
    elif kind == "delving":
        # straight galleries on a grid, shafts between, ore along the walls
        step = 10
        rows = list(range(n - 8, 6, -step))
        g[rows[-1]:n - 4, n // 2 - 1:n // 2 + 2] = K_TUNNEL      # the main shaft
        for y in rows:
            a, b = int(rng.integers(4, n // 3)), int(rng.integers(2 * n // 3, n - 4))
            g[y - 1:y + 2, a:b] = K_TUNNEL
            for x in range(a, b, int(rng.integers(5, 9))):
                if rng.random() < 0.5:
                    g[max(0, y - step + 2):y, x] = K_TUNNEL       # side drifts
        walls = (g == K_CAVEFLOOR) & (np.roll(g, 1, 0) == K_TUNNEL)
        g[walls & (rng.random(g.shape) < 0.25)] = K_ORE
        if last:   # why it was left
            low = np.zeros_like(g, bool)
            low[:n // 3] = True
            g[low & (g == K_TUNNEL)] = K_WATER if pid % 2 else K_LAVA
            marks.append((rows[-1], n // 2, "boss"))
        else:
            marks.append((rows[-1], n // 2, "stairs down"))
        for y in rows[1:-1]:
            marks.append((y, int(rng.integers(n // 4, 3 * n // 4)), "monsters"))
    elif kind == "dragon lair":
        # a long winding tunnel up to one great round cave
        cy, cx = n // 4, n // 2 + int(rng.integers(-n // 6, n // 6))
        yy, xx = np.mgrid[0:n, 0:n]
        r = n * 0.2 * (1 + 0.15 * np.sin(np.arctan2(yy - cy, xx - cx) * 5 + pid))
        g[np.hypot(yy - cy, xx - cx) < r] = K_TUNNEL
        _carve(g, entry[0], entry[1], cy + int(n * 0.18), cx, w=2, wiggle=rng)
        hoard = (np.hypot(yy - cy, xx - cx) < n * 0.07)
        g[hoard] = K_ORE                                          # gold underfoot
        marks += [(cy, cx, "boss"), (cy - 3, cx + 5, "eggs"), (cy + 2, cx - 6, "hoard")]
        for _ in range(3):
            marks.append((int(cy + rng.integers(-15, 15)), int(cx + rng.integers(-15, 15)), "monsters"))
    elif kind == "kobold warren":
        # a maze of narrow tunnels with little chambers
        c = (n - 2) // 4
        seen = np.zeros((c, c), bool)
        stack = [(c - 1, c // 2)]
        seen[stack[0]] = True
        while stack:
            y, x = stack[-1]
            nbs = [(y + dy, x + dx) for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1))
                   if 0 <= y + dy < c and 0 <= x + dx < c and not seen[y + dy, x + dx]]
            if not nbs:
                stack.pop()
                continue
            ny, nx = nbs[int(rng.integers(len(nbs)))]
            seen[ny, nx] = True
            g[2 + min(y, ny) * 4:3 + max(y, ny) * 4, 2 + min(x, nx) * 4:3 + max(x, nx) * 4] = K_TUNNEL
            stack.append((ny, nx))
        for _ in range(8):
            y, x = int(rng.integers(1, c - 1)), int(rng.integers(1, c - 1))
            g[1 + y * 4:4 + y * 4, 1 + x * 4:4 + x * 4] = K_TUNNEL
            marks.append((2 + y * 4, 2 + x * 4, "monsters"))
        g[entry[0] - 2:n - 1, n // 2 - 1:n // 2 + 1] = K_TUNNEL
        marks.append((2, 2 + (c // 2) * 4, "boss" if last else "stairs down"))
    marks.insert(0, (*entry, "entrance" if f == 0 else "stairs up"))
    g[entry[0]:entry[0] + 2, entry[1] - 1:entry[1] + 2] = K_STAIRSUP
    return g, marks


def layout(place, seed):
    """All floors of a dungeon place (a dungeon or a delving)."""
    kind = place.get("type") or ("delving" if place["kind"] == "delving" else "cave")
    nf = FLOORS[kind]
    floors = [_floor(kind, place["id"], f, nf, seed) for f in range(nf)]
    th = THEMES[kind]
    return {"kind": kind, "floors": floors, "theme": th[0], "foes": th[1], "boss": th[2], "size": SIZE[kind]}
