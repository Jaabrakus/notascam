#!/usr/bin/env python3
"""The wild creatures' AI loops onto the shared clock: exact-match edits to a game folder's Monster AI.dm.

    python3 tools/rts_feel/wild/apply_ai.py GAME_DIR

Each loop's body is kept as it was (indented one level less where it leaves a while); only the loop's header and its
sleeps become clock bookings (Remastered/WildClock.dm). Idempotent: an edit already in place is skipped."""
import sys
from pathlib import Path

EDITS = [
# StayLocal: spawn() while(CanBeSlaved) sleep(ReturnDelay); ReturningHome=2
("""mob/Monsters/proc/StayLocal()
	HomeLoc = loc
	spawn() while(CanBeSlaved)
		sleep(ReturnDelay)
		ReturningHome=2
""",
"""mob/Monsters/proc/StayLocal()
	HomeLoc = loc
	spawn() if(CanBeSlaved) RmWildStart(src, "StayLocal", ReturnDelay)   // the shared clock runs its loop (Remastered/WildClock.dm)
mob/Monsters/proc/StayLocalTick(key)   // the loop's body, every ReturnDelay while it is wild
	ReturningHome=2
	if(CanBeSlaved) RmClockBook(src, key, ReturnDelay)
	else RmWildEnd(src, key)
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
"""	spawn()   // the shared clock runs both loops (Remastered/WildClock.dm)
		spawn() if(HomeLoc) RmWildStart(src, "GuardHome", 250)
		rm_guard_range = RANGE
		rm_guard_rate = RATE
		rm_guard_auto = AUTO
		GuardTick(RmWildKey(src, "Guard"))   // the loop's first body comes before its first sleep
mob/Monsters/proc/GuardHomeTick(key)   // the side loop's body, every 250 while it guards (HomeLoc); one after a creature heads home for 50
	if(RmWildPhase(src, key) == "home")
		RmWildSetPhase(src, key, null)
		ReturningHome=0
	else if(!remaster_defense)
		if(ismob(destination))
			ReturningHome=1
			RmWildSetPhase(src, key, "home")
			RmClockBook(src, key, 50)
			return
	if(HomeLoc) RmClockBook(src, key, 250)
	else RmWildEnd(src, key)
mob/Monsters/proc/GuardTick(key)   // the main loop's body, every RATE while it guards (HomeLoc)
	var/RANGE = rm_guard_range
	var/RATE = rm_guard_rate
	var/AUTO = rm_guard_auto
	if(!HomeLoc)
		RmWildEnd(src, key)
		RunningProcs-="Guard"
		return
	if(remaster_defense)
		RmWildBook(src, key, RATE)
		return
	if(AUTO) if(ismob(Owner)) if(!Owner:client)
		RmWildEnd(src, key)
		RunningProcs-="Guard"
		return
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
	RmWildBook(src, key, RmWildFarIdle() ? max(RATE, rm_wild_far_think) : RATE)   // far from every player and idle: a look every few seconds
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
"""	spawn() if(CanBeSlaved) RmWildStart(src, "WanderClear", 300)   // the shared clock runs both loops (Remastered/WildClock.dm)
	if(CanBeSlaved) RmWildStart(src, "Wander", Delay+1)
	else WalkTo(1)
mob/Monsters/proc/WanderClearTick(key)   // the side loop's body, every 300 while it is wild
	src.destination = null
	src.BowOn = 0
	if(CanBeSlaved) RmClockBook(src, key, 300)
	else RmWildEnd(src, key)
mob/Monsters/proc/WanderTick(key)   // the main loop's body, Delay+1 after the last while it is wild
	if(rm_wander_rest)   // its rest over: the loop goes round again
		rm_wander_rest = 0
	else if(!destination && !RmAwake(src))   // nowhere to go and no player near: rest (Remastered Awake.dm)
		rm_wander_rest = 1
		RmClockBook(src, key, rm_asleep_nap)
		return
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
	if(CanBeSlaved) RmClockBook(src, key, Delay+1)
	else   // no longer wild: the owned walk loop
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
"""mob/Monsters/proc/GuardWalk(LINKED=0) if(StopDouble("WalkTo") || LINKED) spawn()   // the shared clock runs both loops (Remastered/WildClock.dm)
	spawn() GuardGearTick(RmWildKey(src, "GuardGear"))   // the gear loop's first body comes before its first sleep
	if(CanBeSlaved) RmWildStart(src, "GuardWalk", Delay+1)
	else WalkTo(1)
mob/Monsters/proc/GuardGearTick(key)   // the gear loop's body, every 200 while it is wild
	if(!CanBeSlaved)
		RmWildEnd(src, key)
		return
	FindGear()
	RmWildBook(src, key, 200)
mob/Monsters/proc/GuardWalkTick(key)   // the main loop's body, Delay+1 after the last while it is wild
	if(!InHole && CanWalk)
		if(destination==HomeLoc) if(loc==HomeLoc) destination=null
		if(destination) step_towards(src,destination)
	if(CanBeSlaved) RmClockBook(src, key, !destination && RmWildFarIdle() ? max(Delay+1, rm_wild_far_think) : Delay+1)   // far and idle: a look every few seconds
	else
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
    print('Monster AI.dm: wild loops on the clock')


if __name__ == '__main__':
    main()
