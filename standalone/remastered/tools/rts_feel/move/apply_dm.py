#!/usr/bin/env python3
"""rts-feel 2026-10-23, smooth unit movement: the 3D moves push every tick, each row with the unit's real step gap (ms).
Exact-match edits, idempotent.  python3 tools/rts_feel/move/apply_dm.py GAME_DIR"""
import sys
from pathlib import Path
G = Path(sys.argv[1])
EDITS = [
 ('Code/Remastered/Orders.dm',
  """	if(.)
		remaster_stepped_at = world.time   // the step rhythm (Specials.dm RemasterStepDelay)
""",
  """	if(.)
		// how long this step took, for the 3D glide (View3D.dm Remaster3DMovesPush): the time since the last step, or,
		// for a first step after standing, the unit's own step time
		var/gap = world.time - remaster_stepped_at
		remaster_stepped_at = world.time   // the step rhythm (Specials.dm RemasterStepDelay)
		remaster_step_gap = (gap > 0 && gap <= 3 * max(1, Delay)) ? gap : max(1, RemasterStepDelay())
"""),
 ('Code/Remastered/Orders.dm',
  """mob/Monsters/var/tmp/remaster_stepped_at = -1000
""",
  """mob/Monsters/var/tmp/remaster_stepped_at = -1000
mob/Monsters/var/tmp/remaster_step_gap = 0   // ticks its last step took (the 3D glide's length)
"""),
 ('Code/Remastered/View3D.dm',
  """// Unit positions five times a second, so 3D movement glides like the map
// does (the full scene still comes with Remaster3DTick every half second).
#define REMASTER_3D_MOVES_EVERY 2
""",
  """// Unit positions every tick, so 3D movement glides like the map does (the full scene still comes with
// Remaster3DTick every half second). Every two ticks made a five-tick step look like four, then six: the page's
// glide waited at a tile, then rushed (rts-feel 2026-10-23, tools/rts_feel/move/).
#define REMASTER_3D_MOVES_EVERY 1
"""),
 ('Code/Remastered/View3D.dm',
  """		moves += list(list((M.Owner == src ? RemasterUIRef(M) : "\\ref[M]"), M.x, M.y, M.dir))
""",
  """		moves += list(list((M.Owner == src ? RemasterUIRef(M) : "\\ref[M]"), M.x, M.y, M.dir, round(M.remaster_step_gap * 100 / max(1, rm_speed))))   // 5th: its last step's length in ms, the page's glide
"""),
]
for rel, old, new in EDITS:
    p = G/rel; s = p.read_text(encoding='utf-8')
    if new in s: print('already', rel); continue
    n = s.count(old); assert n == 1, ('anchor found %d times' % n, rel, old[:70])
    p.write_text(s.replace(old, new), encoding='utf-8'); print('edited', rel)
