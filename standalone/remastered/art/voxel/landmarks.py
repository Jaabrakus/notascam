# Body landmarks of a race's bare sprite (front and side facings): rows of the head top, neck,
# crotch and sole; half-widths and depth centres of head, body and legs.
import numpy as np, dmi
from PIL import Image
R = '/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Icons/Remastered/Races64/'
P = 64

def body_state(race):
    d = dmi.load(R + race + '.dmi')
    return '' if '' in d else 'Normal'

def alpha(race, facing):
    d = dmi.load(R + race + '.dmi')[body_state(race)]
    return np.asarray(dmi.frame(d, facing).convert('RGBA'))[:, :, 3] > 0

def runs(row):
    out = []; i = 0; n = len(row)
    while i < n:
        if row[i]:
            j = i
            while j + 1 < n and row[j + 1]: j += 1
            out.append((i, j)); i = j + 1
        else: i += 1
    return out

def measure(race):
    S, E = alpha(race, 'S'), alpha(race, 'E')
    rows = np.nonzero(S.any(1))[0]; top, sole = int(rows.min()), int(rows.max())
    width = np.array([S[r].sum() for r in range(P)])
    H = sole - top
    # the neck: the narrowest row between a quarter and two thirds of the way down
    lo_, hi_ = top + int(0.2 * H), top + int(0.62 * H)
    neck = lo_ + int(np.argmin(width[lo_:hi_]))
    # the crotch: going up the middle column from the sole, the first drawn pixel
    mid = int(round(np.mean(np.nonzero(S[sole])[0]))) if S[sole].any() else 32
    crotch = sole
    for r in range(sole, neck, -1):
        if S[r, mid - 1:mid + 1].any(): crotch = r; break
    def span(img, r0, r1):
        ws, cs = [], []
        for r in range(r0, r1 + 1):
            if img[r].any():
                xs = np.nonzero(img[r])[0]; ws.append((xs.max() - xs.min() + 1) / 2); cs.append((xs.max() + xs.min() + 1) / 2)
        return (float(np.median(ws)), float(np.median(cs))) if ws else (1.0, 32.0)
    head_w, _ = span(S, top, neck - 1); head_d, head_c = span(E, top, neck - 1)
    body_w, _ = span(S, neck + 2, crotch - 1); body_d, body_c = span(E, neck + 2, crotch - 1)
    leg_d, leg_c = span(E, crotch + 1, sole)
    lr = runs(S[min(sole - 2, crotch + 3)])
    lr = sorted(lr, key=lambda t: -(t[1] - t[0]))[:2]
    if len(lr) == 2:
        cs_ = sorted([(a + b + 1) / 2 for a, b in lr]); leg_sp = (cs_[1] - cs_[0]) / 2
    else: leg_sp = 6.5
    # side pictures: column c is depth z = P - 1 - c, so the depth centre is P - 1 - centre
    return dict(top=top, neck=neck, crotch=crotch, sole=sole, head_w=head_w, head_d=head_d, head_z=P - head_c,
                body_w=body_w, body_d=body_d, body_z=P - body_c, leg_sp=leg_sp, leg_d=leg_d, leg_z=P - leg_c)

if __name__ == '__main__':
    for rc in ['Human', 'Dwarves', 'Night Elf', 'Orc', 'Goblins', 'Kobold', 'LizardMan', 'FrogMan', 'Skeleton', 'Vampire', 'Demon', 'Gargoyle', 'DevourerZombie']:
        m = measure(rc); print(rc.ljust(15), ' '.join('%s=%.1f' % (k, v) for k, v in m.items()))
