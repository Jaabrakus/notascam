// mob/Monsters/Move: one chain, in the order DM ran it when it was spread over 7 files (cleanup, from
// chains.py). The call runs Facing > TickProfile > Pace > Captives > Beasts > Subdue > Orders. Since step-cost (10-27) the
// 7 steps are this one proc, with no call and no args list between them (a step ran 8 calls more, each copying args):
// each step's start below in this order, the parent type's Move (..()) at the bottom of Orders, then the ends of the
// steps that have one, in the opposite order, as each step's own proc ran them after the next one down returned. A step
// that stops the move (its proc's return 0) clears go: the steps below it are skipped, the ends above it still run.
// Add a feature's part as a new step at its place in this order, never as another override elsewhere.
mob/Monsters/Move(NewLoc, Dir = 0, step_x = 0, step_y = 0)
	. = 0
	// step 1 of 7: Facing (was Code/Remastered/Facing.dm:87, RmChainMove_Facing), its start; its end is the last part
	// A step it makes faces it where it went; a blocked step (into a foe's tile, a wall) turns it only at a turn's pace.
	var/atom/was = loc
	var/f = rm_facing_on ? RmFacing() : 0   // read only by the Facing end, which runs only with facing on
	var/mob/u0 = usr   // steps 3 and 7 set usr for the steps below them; the ends see each step's own usr, as in its proc

	// step 2 of 7: TickProfile (was Code/Remastered/TickProfile.dm:466, RmChainMove_TickProfile), its start
	// --- Every creature, world-wide: steps (Orders.dm and Formations.dm Move), the walk loop's wait (Specials.dm), and
	// the wild ones' look round on each step (Monster AI.dm RandomWalk: FindGear, LocateTarget) -------------------------
	var/prof = rm_prof
	var/t0
	var/w0
	if(prof)
		t0 = RmProfIn()
		w0 = world.time

	// step 3 of 7: Pace (was Code/Remastered/Pace.dm:14, RmChainMove_Pace)
	if(ismob(destination) && destination:Owner != Owner) usr = src
	var/mob/u3 = usr

	// step 4 of 7: Captives (was Code/Remastered/Captives.dm:352, RmChainMove_Captives)
	// --- Bound: led or tied, never walking on their own, never fighting --------------------------------------
	var/go = !(rm_cap_state == "bound" && !rm_cap_leading)

	// step 5 of 7: Beasts (was Code/Remastered/Beasts.dm:292, RmChainMove_Beasts), its start
	// The ground rule (Building/TurfTypes.dm) only stops a unit moving under its own usr, so the
	// feet are checked here for anyone on foot. Walking into a foot is walking into the beast
	// (Creatures/Bump.dm): an enemy sent at it fights it, anyone else steps aside.
	if(go)
		if(rm_bound) go = 0   // chained down (Taming.dm)
		// a wild great beast closing on its prey stops at its jaws' reach and bites from there (Beasts.dm RmJawStrike)
		else if((Race == "Dragon" || Race == "Spider") && !rm_backing && !istype(Owner, /Player) && ismob(Target) && isturf(NewLoc) && get_dist(NewLoc, Target) < get_dist(src, Target) && RemasterHostile(src, Target) && RmJawStrike(Target)) go = 0
		else if(isturf(NewLoc) && !Flying)
			var/turf/T = NewLoc
			if(T.rm_feet_n)   // it looks only on a tile that counts a foot (Beasts.dm rm_feet_n, step-cost 10-27)
				for(var/obj/RmBeastFoot/F in T) if(F.owner != src && RmBeastFootStands(F))
					if(Dir) dir = Dir
					Bump(F.owner)
					go = 0
					break
			else if(rm_step_scan_check) RmStepScanFeet(T, src)
			if(go && (Race == "Dragon" || Race == "Spider" || Race == "Golem"))   // (RmBeastLegsMangled gives 0 for any other)
				// crippled (its legs are never cut off: Combats.dm / RmBeastLimbFloor): one mangled leg and it
				// limps, two and it can't walk until they mend
				var/lame = RmBeastLegsMangled(src)
				if(lame >= 2 || (lame == 1 && prob(35)))
					if(lame >= 2 && istype(Owner, /Player) && world.time >= rm_lame_said)
						rm_lame_said = world.time + 300
						Owner:RemasterNotice("[name] can't walk: [lame] of its legs are mangled.")
					go = 0
	var/beasts = go   // step 5 went on to the steps below: its end runs

	// step 6 of 7: Subdue (was Code/Remastered/Subdue.dm:31, RmChainMove_Subdue)
	// Out cold, a unit takes no step of its own. The original wander loop (Monster AI.dm RandomWalk) checks only InHole and
	// CanWalk, so a knocked-out raider kept walking off (user, 2026-10-23). Carrying one sets its loc, not Move.
	if(go && remaster_ko_until > world.time && !rm_cap_leading) go = 0   // dragged on a rope is the one way (Captives.dm)

	// step 7 of 7: Orders (was Code/Remastered/Orders.dm:53, RmChainMove_Orders)
	if(go)
		// WalkTo can inherit the logged-in player's usr from Login. Terrain uses
		// usr for collision exemptions and environmental effects, so queued work
		// must enter as its physical worker rather than the free-moving camera.
		if(RemasterHasOrder() || remaster_defense) usr = src
		// up on a mountain: a step to a place it can stand at, never up a block but by a ramp, nor down more than one (Gather.dm)
		var/list/step_to = (isturf(NewLoc) && isturf(loc) && loc:z == SKY_LAYER && NewLoc:z == SKY_LAYER) ? RemasterStepSpot(NewLoc) : null
		if(!(isturf(NewLoc) && isturf(loc) && loc:z == SKY_LAYER && NewLoc:z == SKY_LAYER && !step_to))
			// the bottom: the parent type's Move, as the first override's ..() reached; on a plain tile the engine's step
			// (Native.dm RmStepPlain, RmStep.cs: the same step without the standard Move's calls that do nothing)
			var/atom/was_at = loc   // the tile it leaves (rm_came_from below)
			var/sp = rm_step_native && !rm_step_verify ? RmStepPlain(NewLoc, Dir) : null
			if(isnull(sp))
				var/want = rm_step_verify ? RmStepDecide(NewLoc, Dir) : null   // the shadow mode: the engine's answer first
				. = ..()
				if(!isnull(want)) RmStepVerify(want, ., NewLoc)
			else . = sp
			if(. && step_to)
				remaster_feet = step_to[2] || null
				remaster_feet_on = loc
			if(.)
				// how long this step took, for the 3D glide (View3D.dm Remaster3DMovesPush): the time since the last step, or,
				// for a first step after standing, the unit's own step time
				var/gap = world.time - remaster_stepped_at
				remaster_stepped_at = world.time   // the step rhythm (Specials.dm RemasterStepDelay)
				rm_came_from = was_at   // never straight back on the battle field (Attack.dm RmGangUp)
				if(!rm_fs_far) remaster_step_gap = (gap > 0 && gap <= 3 * max(1, Delay)) ? gap : max(1, RemasterStepDelay())   // a far unit's (FarSteps.dm): nobody sees its glide
				if(remaster_active || remaster_attack || remaster_delivery) RemasterChainStep()   // straight on to its route's next tile (Formations.dm)
				if(remaster_push_step)   // the first step after an order goes to the 3D view this tick (View3D.dm)
					remaster_push_step = 0
					var/Player/P = Owner
					if(istype(P) && P.remaster_3d) P.Remaster3DMovesPushNow()

	// step 5 of 7: Beasts, its end
	if(beasts)
		usr = u3
		if(rm_feet || Race == "Dragon" || Race == "Spider") RmBeastFeetUpdate(src)

	// step 2 of 7: TickProfile, its end
	usr = u0
	if(prof) RmProf("creature move", t0, w0)

	// step 1 of 7: Facing, its end
	if(!rm_facing_on) return
	if(loc != was)
		rm_face = dir
		rm_turn_to = 0
		if(rm_fs_far) return   // a far unit (FarSteps.dm): no run counted (no foe within RM_FS_FOE to charge)
		if(world.time - rm_step_at > 10 && isturf(was))   // a run begins (a pause of a second ends one)
			rm_run_steps = 0
			rm_run_x = was.x
			rm_run_y = was.y
		rm_run_steps++
		rm_step_at = world.time
	else if(dir != f)
		var/want = dir
		dir = f
		RmTurnToward(want)
