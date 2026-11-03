# Head against body at the game camera (python3 headratio.py 'Race,..'): the sprite's head area
# over its body area, and the 3D's at the 45-degree corner (head = parts 2, 3; body = the rest);
# an optional second argument passes inflate() settings, e.g. "dict(head_mode='r3')"
import sys
import inflate2, render3, numpy as np
def width(M, ids, yaw):
    keep = M.owner.copy()
    M.owner = np.where(np.isin(keep, ids), keep, 0)
    im = np.asarray(render3.render(M, yaw, 37, scale=2, size=200, stretch=1.2, foot=0.9, outline=(0, 0, 0), rim={}))
    M.owner = keep
    return (im[:, :, 3] > 0).sum() / 4.0                                 # area, in sprite pixels
kw = eval(sys.argv[2]) if len(sys.argv) > 2 else {}
for rc in sys.argv[1].split(','):
    M, S = inflate2.inflate(rc, **kw); L = inflate2.LAST
    a = S[:, :, 3] > 0
    hw = a[:L['neck_r'] + 1].sum(); bw = a[L['neck_r'] + 1:].sum()
    h3 = width(M, [2, 3], 45); b3 = width(M, [1, 4, 5], 45)
    print('%-15s sprite head/body %.2f   3D at 45: %.2f   (%.0f%%)' % (rc, hw / bw, h3 / b3, 100 * (h3 / b3) / (hw / bw)), flush=True)
