# The 3D pixel pieces baked into Gear64 sheets (python3 bake64.py OUT [sheet:slot=style:tier ...], style's spaces as _): the server
# lays a unit's worn and held pieces over its picture (View3D.dm Remaster3DLayers), so pieces drawn from the 3D
# models in the sheets it already reads cost the page nothing more than the drawn ones. Each piece is rendered at
# the four facings of the unit pictures (S seen from in front, N from behind, E from the wearer's right, W from its
# left), at that race's own fist, forearm and head in each walk frame (anchors.json), made pixel art as pixelgear.py
# makes it (the dragons' way), and cut by the body where the piece is on its far side. Weapons get the attack's
# wind-up and blow as frames 4 and 5, as the drawn ones have. Writes OUT/<sheet>/<tier>.dmi with the game's state
# names (weapon.<style>.<tier>, shield..., helmet...). Nothing in game/ is touched.
import json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'enhance'))
import pixelgear as pg          # noqa: E402
import meshes as ms             # noqa: E402
from game_export import read_dmi_full, write_sheet, walk_meta   # noqa: E402

ICONS = os.path.join(HERE, '..', '..', 'game', 'Icons', 'Remastered')
A = json.load(open(os.path.join(HERE, 'anchors.json')))
DIRS = 'SNEW'
FACING = {'S': 0, 'N': 8, 'E': 4, 'W': 12}   # the picture's facing as one of pixelgear's 16
_bodies = {}


def body_mask(sheet, d, f):
    if sheet not in _bodies:
        st = A[sheet]['state']
        _bodies[sheet] = next(c for n, m, c in read_dmi_full(os.path.join(ICONS, 'Races64', sheet + '.dmi')) if n == st)
    c = _bodies[sheet]
    k = f * 4 + DIRS.index(d)
    return (c[k] if k < len(c) else c[DIRS.index(d)])[..., 3] > 0


def cell(mesh_pts, at, scale, facing):
    """One 64 px cell: the placed piece (P, N, M in the wearer's frame, its origin the anchor) seen from facing,
    scaled, its origin on the picture's pixel `at`."""
    P, N, Mt = mesh_pts
    c, rc, u = pg.camera(facing)
    ax, ay = at
    box = (-ax, -ay, 64 - ax, 64 - ay)
    mat, nb = pg.raster(P * scale, N, Mt, c, rc, box)
    v, g = pg.shade(mat, nb, c, rc)
    best, vm, gm = pg.down(mat, v, g)
    return best, vm, gm


def bake(sheet, slot, style, tier):
    """[(state, meta, cells)] for one piece on one race sheet."""
    a = A[sheet]
    sc = a.get('scale', 1.0)
    if slot == 'w':
        mesh, name, poses = ms.weapon(style), 'weapon', ([0] if style == 'bow' else [0, 1, 3])
    elif slot == 's':
        mesh, name, poses = ms.shield(style), 'shield', [0]
    else:
        mesh, name, poses = ms.helmet(style), 'helmet', [0]
    placed = {}
    for pose in poses:
        if slot == 'w':
            B, off = pg.weapon_basis(style, pose)
        elif slot == 's':
            B, off = pg.shield_basis()
        else:
            B, off = pg.helmet_basis()
        P, N, Mt = pg.placed(mesh, B, off)
        if slot == 'h':
            hp, hn, hm = pg.placed(pg.head(), np.eye(3), np.zeros(3))
            P, N, Mt = np.concatenate([P, hp]), np.concatenate([N, hn]), np.concatenate([Mt, hm])
        placed[pose] = (P, N, Mt)
    # frames: the three walk frames at rest, then (weapons) the wind-up and the blow on the standing body
    frames = [(f, 0) for f in range(3)] + ([(0, 1), (0, 3)] if slot == 'w' and len(poses) > 1 else [])
    cells = []
    for f, pose in frames:
        for d in DIRS:
            v = a['views'][d][f]
            if slot == 'w':
                at, s = v['hand'], sc
            elif slot == 's':
                at, s = v['shield'], sc
            else:
                h = v['head']; sx = a['loc']['headw'] / 11.5
                at, s = ((h['l'] + h['r']) / 2, h['top'] + 10.5 * sx), sx * 0.5 + a['loc']['headd'] / 9.5 * 0.5
            best, vm, gm = cell(placed[pose], at, s, FACING[d])
            out = pg.colour(best, vm, gm, tier)
            far = (slot == 'w' and (d == 'W' or (d == 'N' and pose == 3))) or (slot == 's' and d in ('E', 'N'))   # from behind a shield is held out beyond the body
            if far:   # on the far side of the body: only what shows past it
                out[body_mask(sheet, d, f)] = 0
            cells.append(out)
    return [(f'{name}.{style}.{tier}', walk_meta(len(frames)), cells)]


def main(out, items):
    by = {}
    for it in items:   # Human:w=longsword:iron
        sheet, rest = it.split(':', 1)
        sheet = sheet.replace('_', ' ')   # Night_Elf
        slot, spec = rest.split('=')
        style, tier = spec.replace('_', ' ').split(':')   # names with spaces come with _ (battle_axe)
        by.setdefault((sheet, tier), []).extend(bake(sheet, slot, style, tier))
        print(it, flush=True)
    for (sheet, tier), states in by.items():
        os.makedirs(os.path.join(out, sheet), exist_ok=True)
        write_sheet(os.path.join(out, sheet, tier + '.dmi'), states, 64)
    print(out)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2:])
