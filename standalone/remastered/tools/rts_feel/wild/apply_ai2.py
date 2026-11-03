#!/usr/bin/env python3
"""Wild creatures, second change (rts-feel, 2026-10-25), on a game folder that has the first (apply_ai.py + WildClock.dm):

    python3 tools/rts_feel/wild/apply_ai2.py GAME_DIR

1. LocateTarget asks rm_foe_near first (engine RmSight.cs; Native.dm's fallback answers yes): no other owner's unit within
   RANGE means the oview scan would find nobody, so it is skipped. The body is unchanged (one tab deeper).
2. A wander loop's rest is its own: the first wander keeps rm_wander_rest, a second one (RandomWalk(1) on a wanderer, as
   tests/capture_test.dm does) its phase in rm_wild_phase, as in the old game where each loop had its own.
3. The clock's dispatch: UnitClock.dm's switch hands the other jobs to RmWildRun (server-cost's OK), so WildClock.dm no
   longer overrides RmClockRun.
Exact-match edits; idempotent. WildClock.dm itself comes from tools/rts_feel/wild/WildClock.dm."""
import sys
from pathlib import Path

LOCATE_OLD_HEAD = "mob/Monsters/proc/LocateTarget(RANGE=5) for(var/mob/Monsters/M in oview(RANGE,src))\n"
LOCATE_NEW_HEAD = ("mob/Monsters/proc/LocateTarget(RANGE=5)\n"
                   "\tif(!rm_foe_near(src, RANGE, /mob/Monsters)) return   // nobody of another owner within RANGE: the scan would find no one (engine RmSight.cs; Native.dm's fallback: always scan)\n"
                   "\tfor(var/mob/Monsters/M in oview(RANGE,src))\n")
FALLBACK = ('\n\n// Whether a unit an attack-move\'s look could pick stands within dist of M: any /mob/Monsters but M within the square\n'
            '// oview(dist, M) looks over that isn\'t of M\'s own owner (engine RmSight.cs). Without the engine\'s: always yes, so\n'
            '// the look runs as before.\nproc/rm_foe_near(mob/Monsters/M, dist, monsters)\n\treturn 1\n')

AI_EDITS = [
("""#define RM_WILD_AWAKE (world.time - rm_wild_seen < 10 ? rm_wild_was : RmWildLook())   // its land awake, asked at most every 10 ticks (Remastered/WildClock.dm)
""",
"""#define RM_WILD_AWAKE (world.time - rm_wild_seen < 10 ? rm_wild_was : RmWildLook())   // its land awake, asked at most every 10 ticks (Remastered/WildClock.dm)
#define RM_WANDER_RESTING (key == "Wander" ? rm_wander_rest : RmWildPhase(src, key) == "rest")   // this wander loop is resting on the clock
"""),
("""		RM_WILD_TRACE(rm_wander_rest ? "r" : "w")
		if(rm_wander_rest)   // the clock's run: its rest over, the loop goes round again
			rm_wander_rest = 0
		else if(!destination && !RmAwake(src))   // nowhere to go and no player near: rest (Remastered Awake.dm)
			rm_wander_rest = 1
			return RmWildBook(src, key, rm_asleep_nap)   // its land is asleep: the rest on the clock
""",
"""		RM_WILD_TRACE(RM_WANDER_RESTING ? "r" : "w")
		if(RM_WANDER_RESTING)   // the clock's run: its rest over, the loop goes round again
			RmWanderRest(key, 0)
		else if(!destination && !RmAwake(src))   // nowhere to go and no player near: rest (Remastered Awake.dm)
			RmWanderRest(key, 1)
			return RmWildBook(src, key, rm_asleep_nap)   // its land is asleep: the rest on the clock
"""),
]

CLOCK_OLD = """		if("Bed") BedTick()
		if("Regen") RegenTick()
"""
CLOCK_NEW = """		if("Bed") BedTick()
		if("Regen") RegenTick()
		else RmWildRun(job)   // the wild creatures' loops (Remastered/WildClock.dm)
"""


def write(p, s):
    tmp = p.with_name(p.name + '.tmp')
    tmp.write_bytes(s.encode('latin-1'))
    tmp.replace(p)


def main():
    game = Path(sys.argv[1])
    p = game/'Code/Creatures/Monster AI.dm'
    s = p.read_text(encoding='latin-1')
    for old, new in AI_EDITS:
        if new in s: continue
        if s.count(old) != 1: sys.exit(f'{p}: no single match for:\n{old[:200]}')
        s = s.replace(old, new)
    if LOCATE_NEW_HEAD not in s:
        if s.count(LOCATE_OLD_HEAD) != 1: sys.exit('LocateTarget header not found once')
        a = s.index(LOCATE_OLD_HEAD)
        b = s.index('\nmob/proc/FindGear()', a)
        body = s[a + len(LOCATE_OLD_HEAD):b + 1]
        lines = body.split('\n')
        body = '\n'.join(('\t' + l) if l.strip() else l for l in lines)
        s = s[:a] + LOCATE_NEW_HEAD + body.rstrip('\t') + s[b + 1:]
    write(p, s)
    n = game/'Code/Remastered/Native.dm'
    t = n.read_text(encoding='latin-1')
    if 'proc/rm_foe_near' not in t: write(n, t.rstrip('\n') + FALLBACK)
    u = game/'Code/Remastered/UnitClock.dm'
    t = u.read_text(encoding='latin-1')
    if CLOCK_NEW not in t:
        if t.count(CLOCK_OLD) != 1: sys.exit('UnitClock.dm switch not found once')
        write(u, t.replace(CLOCK_OLD, CLOCK_NEW))
    print('wild change 2 applied to', game)


if __name__ == '__main__':
    main()
