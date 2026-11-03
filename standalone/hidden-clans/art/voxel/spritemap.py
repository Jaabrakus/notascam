# Character map of a race sprite (front and side) to measure parts by hand.
import sys, dmi, landmarks, numpy as np
rc = sys.argv[1]; rows = range(int(sys.argv[2]), int(sys.argv[3]))
d = dmi.load(landmarks.R + rc + '.dmi')[landmarks.body_state(rc)]
pics = {f: np.asarray(dmi.frame(d, f).convert('RGBA')).astype(int) for f in 'SE'}
skin = None
for f in 'SE':
    a = pics[f]
    print(rc, f); print('     ' + ''.join(str(c // 10) for c in range(8, 58))); print('     ' + ''.join(str(c % 10) for c in range(8, 58)))
    for r in rows:
        row = ''
        for c in range(8, 58):
            p = a[r, c]
            if p[3] == 0: row += ' '; continue
            s = p[:3].sum()
            row += '#' if s < 40 else 'b' if (p[0] > p[1] + 15 and s < 150) else 'W' if s > 560 else 'Y' if (p[0] > 180 and p[1] > 180 and p[2] < 100) else 'R' if (p[0] > 150 and p[1] < 90) else '+' if s > 380 else 'o' if s > 260 else '.'
        print('%3d  ' % r + row)
