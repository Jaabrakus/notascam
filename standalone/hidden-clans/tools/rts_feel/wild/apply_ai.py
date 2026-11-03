#!/usr/bin/env python3
"""The wild creatures' AI loops: asleep in their own proc while their land is awake, on the shared clock while it isn't
(Remastered/WildClock.dm). Exact-match edits to a game folder's Monster AI.dm:

    python3 tools/rts_feel/wild/apply_ai.py GAME_DIR

Each loop's body is kept as it was; only its sleeps change. Where the old loop slept, the loop now sleeps in its proc if
its land is awake (RmAwake, Awake.dm) and otherwise books the clock for that tick and leaves the proc; the clock calls
the loop again at that tick (WildClock.dm), which goes on in a proc again once its land is awake. So the loops wake on
the old ticks either way. Idempotent: an edit already in place is skipped. (tools/rts_feel/wild/apply_ai_clock.py is the
all-clock version: measured dearer near players, reports/polish-2026-10-22/rts-feel/wild/.)"""
import sys
from pathlib import Path

EDITS = [
# the timing proof's trace points: nothing in the game; tests/wildclock_check.dm's build defines RM_WILD_TRACE first
("mob/var/tmp/list/Hostilities=new()\n",
 "#ifndef RM_WILD_TRACE\n#define RM_WILD_TRACE(T)\n#endif\n"
 "#define RM_WILD_AWAKE (world.time - rm_wild_seen < 10 ? rm_wild_was : RmWildLook())   // its land awake, asked at most every 10 ticks (Remastered/WildClock.dm)\n"
 "mob/var/tmp/list/Hostilities=new()\n"),
# StayLocal: spawn() while(CanBeSlaved) sleep(ReturnDelay); ReturningHome=2
("""mob/Monsters/proc/StayLocal()
	HomeLoc = loc
	spawn() while(CanBeSlaved)
		sleep(ReturnDelay)
		ReturningHome=2
""",
"""mob/Monsters/proc/StayLocal()
	HomeLoc = loc
	spawn() if(CanBeSlaved) StayLocalRun(RmWildKey(src, "StayLocal"), 1)   // asleep in its proc or on the clock (Remastered/WildClock.dm)
mob/Monsters/proc/StayLocalRun(key, wait)   // the loop: every ReturnDelay while it is wild (wait 0: the clock's run, its sleep over)
	while(1)
		if(wait)
			if(RM_WILD_AWAKE) sleep(ReturnDelay)
			else return RmWildBook(src, key, ReturnDelay)
		wait = 1
		RM_WILD_TRACE("s")
		ReturningHome=2
		if(!CanBeSlaved) break
	RmWildEnd(src, key)
"""),
# Guarding: two loops, the side one every 250 (50 more heading home), the main one every RATE, its first body at once
("""	spawn()
		spawn() while(HomeLoc)
			sleep(250)
			if(remaster_defense) continue
			if(ismob(destination))
				ReturningHome=1
				sleep(50)
				ReturningHome=0
		while(HomeLoc)
			if(remaster_defense)
				sleep(RATE)
				continue
			if(AUTO) if(ismob(Owner)) if(!Owner:client) break
			if(ReturningHome)
				if(loc!=HomeLoc) destination = HomeLoc
				else ReturningHome=0
			else
				if(!destination || prob(10))
					destination=LocateTarget(RANGE)
					if(!destination)
						destination=HomeLoc
						if(loc==PatrolPoint1) HomeLoc=PatrolPoint2
						if(loc==PatrolPoint2) HomeLoc=PatrolPoint1
			sleep(RATE)
		RunningProcs-="Guard"
""",
"""	spawn()   // both loops asleep in their procs or on the clock (Remastered/WildClock.dm)
		spawn() if(HomeLoc) GuardHomeRun(RmWildKey(src, "GuardHome"), 1)
		rm_guard_range = RANGE
		rm_guard_rate = RATE
		rm_guard_auto = AUTO
		GuardRun(RmWildKey(src, "Guard"), 0)   // the loop's first body comes before its first sleep
mob/Monsters/proc/GuardHomeRun(key, wait)   // the side loop: every 250 while it guards (HomeLoc); one after a creature heads home for 50
	while(1)
		if(wait)
			if(RM_WILD_AWAKE) sleep(250)
			else return RmWildBook(src, key, 250)
		wait = 1
		RM_WILD_TRACE(RmWildPhase(src, key) == "home" ? "H" : "h")
		if(RmWildPhase(src, key) == "home")   // the clock's run: its 50 over
			RmWildSetPhase(src, key, null)
			ReturningHome=0
		else if(!remaster_defense)
			if(ismob(destination))
				ReturningHome=1
				if(RM_WILD_AWAKE) sleep(50)
				else
					RmWildSetPhase(src, key, "home")
					return RmWildBook(src, key, 50)
				RM_WILD_TRACE("H")
				ReturningHome=0
		if(!HomeLoc) break
	RmWildEnd(src, key)
mob/Monsters/proc/GuardRun(key, wait)   // the main loop: every RATE while it guards (HomeLoc)
	var/RANGE = rm_guard_range
	var/RATE = rm_guard_rate
	var/AUTO = rm_guard_auto
	while(1)
		if(wait)
			if(RM_WILD_AWAKE) sleep(RATE)
			else return RmWildBook(src, key, RmWildIdle() ? max(RATE, rm_wild_far_think) : RATE)   // far and idle: a look every few seconds
		wait = 1
		if(!HomeLoc) break
		RM_WILD_TRACE("m")
		if(remaster_defense) continue
		if(AUTO) if(ismob(Owner)) if(!Owner:client) break
		if(ReturningHome)
			if(loc!=HomeLoc) destination = HomeLoc
			else ReturningHome=0
		else
			if(!destination || prob(10))
				destination=LocateTarget(RANGE)
				if(!destination)
					destination=HomeLoc
					if(loc==PatrolPoint1) HomeLoc=PatrolPoint2
					if(loc==PatrolPoint2) HomeLoc=PatrolPoint1
	RmWildEnd(src, key)
	RunningProcs-="Guard"
"""),
# RandomWalk: the side loop every 300, the main one every Delay+1 (a rest of rm_asleep_nap more in asleep land)
("""	spawn() while(CanBeSlaved)
		sleep(300)
		src.destination = null
		src.BowOn = 0
	while(CanBeSlaved)
		sleep(Delay+1)
		if(!destination && !RmAwake(src))   // nowhere to go and no player near: rest (Remastered Awake.dm)
			sleep(rm_asleep_nap)
			continue
		FindGear()
		if(!InHole && CanWalk)
			if(destination)
				if(ismob(destination) || destination == HomeLoc)
					if(destination in range(6,src)) step_towards(src,destination)
					else
						if(destination==HomeLoc) step_towards(src,destination)
						else destination = null
				if(destination == loc) destination=null
			if(!destination)
				if(HomeLoc&&ReturningHome==2)
					step_towards(src,HomeLoc)
					ReturningHome=0
				else
					step_rand(src)
					destination = LocateTarget()
	WalkTo(1)
""",
"""	spawn() if(CanBeSlaved) WanderClearRun(RmWildKey(src, "WanderClear"), 1)   // both loops asleep in their procs or on the clock (Remastered/WildClock.dm)
	if(CanBeSlaved) WanderRun(RmWildKey(src, "Wander"), 1)
	else WalkTo(1)
mob/Monsters/proc/WanderClearRun(key, wait)   // the side loop: every 300 while it is wild
	while(1)
		if(wait)
			if(RM_WILD_AWAKE) sleep(300)
			else return RmWildBook(src, key, 300)
		wait = 1
		RM_WILD_TRACE("c")
		src.destination = null
		src.BowOn = 0
		if(!CanBeSlaved) break
	RmWildEnd(src, key)
mob/Monsters/proc/WanderRun(key, wait)   // the main loop: Delay+1 after the last while it is wild
	while(1)
		if(wait)
			if(RM_WILD_AWAKE) sleep(Delay+1)
			else return RmWildBook(src, key, Delay+1)
		wait = 1
		RM_WILD_TRACE(rm_wander_rest ? "r" : "w")
		if(rm_wander_rest)   // the clock's run: its rest over, the loop goes round again
			rm_wander_rest = 0
		else if(!destination && !RmAwake(src))   // nowhere to go and no player near: rest (Remastered Awake.dm)
			rm_wander_rest = 1
			return RmWildBook(src, key, rm_asleep_nap)   // its land is asleep: the rest on the clock
		else
			FindGear()
			if(!InHole && CanWalk)
				if(destination)
					if(ismob(destination) || destination == HomeLoc)
						if(destination in range(6,src)) step_towards(src,destination)
						else
							if(destination==HomeLoc) step_towards(src,destination)
							else destination = null
					if(destination == loc) destination=null
				if(!destination)
					if(HomeLoc&&ReturningHome==2)
						step_towards(src,HomeLoc)
						ReturningHome=0
					else
						step_rand(src)
						destination = LocateTarget()
		if(!CanBeSlaved) break
	RmWildEnd(src, key)
	WalkTo(1)
"""),
# GuardWalk: the gear loop every 200 (its body first), the main one every Delay+1
("""mob/Monsters/proc/GuardWalk(LINKED=0) if(StopDouble("WalkTo") || LINKED) spawn()
	spawn() while(CanBeSlaved)
		FindGear()
		sleep(200)
	while(CanBeSlaved)
		sleep(Delay+1)
		if(!InHole && CanWalk)
			if(destination==HomeLoc) if(loc==HomeLoc) destination=null
			if(destination) step_towards(src,destination)
	WalkTo(1)
""",
"""mob/Monsters/proc/GuardWalk(LINKED=0) if(StopDouble("WalkTo") || LINKED) spawn()   // both loops asleep in their procs or on the clock (Remastered/WildClock.dm)
	spawn() GuardGearRun(RmWildKey(src, "GuardGear"), 0)   // the gear loop's first body comes before its first sleep
	if(CanBeSlaved) GuardWalkRun(RmWildKey(src, "GuardWalk"), 1)
	else WalkTo(1)
mob/Monsters/proc/GuardGearRun(key, wait)   // the gear loop: every 200 while it is wild
	while(1)
		if(wait)
			if(RM_WILD_AWAKE) sleep(200)
			else return RmWildBook(src, key, 200)
		wait = 1
		if(!CanBeSlaved) break
		RM_WILD_TRACE("f")
		FindGear()
	RmWildEnd(src, key)
mob/Monsters/proc/GuardWalkRun(key, wait)   // the main loop: Delay+1 after the last while it is wild
	while(1)
		if(wait)
			if(RM_WILD_AWAKE) sleep(Delay+1)
			else return RmWildBook(src, key, !destination && RmWildIdle() ? max(Delay+1, rm_wild_far_think) : Delay+1)   // far and idle: a look every few seconds
		wait = 1
		RM_WILD_TRACE("g")
		if(!InHole && CanWalk)
			if(destination==HomeLoc) if(loc==HomeLoc) destination=null
			if(destination) step_towards(src,destination)
		if(!CanBeSlaved) break
	RmWildEnd(src, key)
	WalkTo(1)
"""),
]


def main():
    game = Path(sys.argv[1])
    p = game/'Code/Creatures/Monster AI.dm'
    s = p.read_text(encoding='latin-1')
    for old, new in EDITS:
        if new in s: continue
        if s.count(old) != 1: sys.exit(f'{p}: no single match for:\n{old[:200]}')
        s = s.replace(old, new)
    b = s.encode('latin-1')
    tmp = p.with_suffix('.dm.tmp')
    tmp.write_bytes(b)
    tmp.replace(p)
    print('Monster AI.dm: wild loops asleep in their procs or on the clock')


if __name__ == '__main__':
    main()
