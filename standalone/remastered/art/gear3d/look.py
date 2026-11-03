# Contact sheet of the 3D gear pieces (python3 look.py OUT.png [tier]): a painter's-order software render of
# gear3d.json, two views each, coloured as the page colours them. For checking shapes; the real look is the page's.
import base64, json, os, sys
import numpy as np
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__))
D = json.load(open(os.path.join(HERE, 'gear3d.json')))
tier = sys.argv[2] if len(sys.argv) > 2 else 'iron'
T = D['tiers']
def col(m):
    r = T[tier]
    return {0: r[2], 1: r[3], 2: r[2] if tier not in ('wood', 'leather') else T['iron'][2], 3: T['wood'][2], 4: T['leather'][2], 5: (20, 18, 16),
            6: T['silk'][3], 7: T['red'][2], 8: T['blue'][2], 9: T['gold'][3], 10: T['horn'][2], 11: T['feather'][3], 12: T['plume'][2],
            13: T['wood'][0], 14: T['wood'][1], 15: r[1], 16: T['leather'][0], 17: r[3]}[m]
def unpack(p):
    P = np.frombuffer(base64.b64decode(p['pos']), '<i2').reshape(-1, 3) / D['q']
    N = np.frombuffer(base64.b64decode(p['nrm']), 'i1').reshape(-1, 3) / 127
    M = np.frombuffer(base64.b64decode(p['mat']), 'u1')
    return P, N, M
def rot(yaw, pitch):
    cy, sy, cp, sp = np.cos(yaw), np.sin(yaw), np.cos(pitch), np.sin(pitch)
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]]); Rx = np.array([[1, 0, 0], [0, cp, -sp], [0, sp, cp]])
    return Rx @ Ry
L = np.array([-0.5, 0.8, 0.6]); L /= np.linalg.norm(L)
def draw(img, P, N, M, R, cx, cy, sc):
    Q = P @ R.T; NN = N @ R.T
    d = ImageDraw.Draw(img)
    tris = Q.reshape(-1, 3, 3); nn = NN.reshape(-1, 3, 3); mm = M.reshape(-1, 3)[:, 0]
    order = np.argsort(tris[:, :, 2].mean(1))
    for i in order:
        n = nn[i].mean(0); n /= (np.linalg.norm(n) or 1)
        if n[2] < -0.05: continue
        lam = 0.45 + 0.55 * max(0, n @ L)
        h = n + np.array([0, 0, 1.0]); h /= np.linalg.norm(h)
        spec = max(0, (n @ (L + np.array([0, 0, 1])) / np.linalg.norm(L + np.array([0, 0, 1])))) ** 20 * (90 if mm[i] in (0, 1, 2, 9) else 10)
        c = tuple(int(min(255, v * lam + spec)) for v in col(mm[i]))
        pts = [(cx + p[0] * sc, cy - p[1] * sc) for p in tris[i]]
        d.polygon(pts, fill=c)
names = list(D['pieces'])
S = 220; img = Image.new('RGB', (S * 2 * 6, S * ((len(names) + 5) // 6)), (58, 62, 70))
for k, n in enumerate(names):
    P, N, M = unpack(D['pieces'][n])
    if n.startswith('weapon.'):
        # stand the weapon up: t (x) up, s (y) to the right, n (z) toward us
        A = np.array([[0, 1, 0], [1, 0, 0], [0, 0, 1]], float); P = P @ A.T; N = N @ A.T
        sc, oy = 3.4, 0.82
    elif n.startswith('shield.'):
        sc, oy = 5.5, 0.5
    else:
        sc, oy = 5.5, 0.55
    for j, (yaw, pitch) in enumerate(((0.5, 0.35), (2.0, 0.35))):
        x0, y0 = (k % 6) * 2 * S + j * S, (k // 6) * S
        draw(img, P, N, M, rot(yaw, pitch), x0 + S / 2, y0 + S * oy, sc)
    ImageDraw.Draw(img).text(((k % 6) * 2 * S + 4, (k // 6) * S + 4), n, fill=(255, 230, 120))
img.save(sys.argv[1]); print(sys.argv[1])
