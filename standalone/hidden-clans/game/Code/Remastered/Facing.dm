// Facing and flanking (the user, 2026-10-26: "okay start facing and flanking"; planning/COMBAT_STRATEGY_PLAN_2026-10-26.md
// system 2). A unit faces its world dir (8 ways; the 3D view draws its side from that and the camera). It faces where it
// last moved, at once; turning toward a foe it strikes or steps into takes rm_turn_ticks (0.5 s), so a second attacker
// at its side or back stays there until it turns. Struck from its side (90 degrees off its facing): no shield block (half
// from its shield's side, the left), half its dodge. From behind (135 degrees or straight back): no shield block, no dodge,
// and criticals on 18-20 (Combats.dm, CombatSkills.dm RmMeleeWhere). A blow that lands from the side or behind floats
// "Flanked!" or "From behind!" over it in 3D (no chat line) and counts in rm_flanks. Great beasts have no flanks.
// Awareness (the user, 2026-10-26: "Yes, as proposed", a skill check): a blow from the side or behind lets the defender
// roll a d20 to meet it, needing rm_aware_side (15) or rm_aware_rear (19), a point easier for every rm_aware_per (10) levels
// its Defence is above the attacker's Attack and harder below; a natural 20 always meets it, a 1 never. Met, the blow is as
// from the front and "Turned to meet it!" floats over it (its facing stays on its own foe). Turning toward a new foe is
// quicker with Defence: 0.5 s for a recruit, about 0.3 s at Defence 50.
var/rm_facing_on = 0      // 0: every blow as from the front, turns at once, as before (off since build 58, the charge with it: the user,
                          // 2026-10-26: "i honestly think we dont need the flanking and the flanking checks", "Drop it too")
var/rm_turn_ticks = 5     // ticks to turn toward a new foe (a recruit; less with Defence: RmTurnTicks)
var/rm_aware_on = 1
var/rm_aware_side = 15
var/rm_aware_rear = 19
var/rm_aware_per = 10
mob/Monsters/var/tmp/rm_turns = 0   // blows from a side or behind it turned to meet (reports)
mob/Monsters/var/tmp/rm_face = 0     // where it faces, as the fight sees it (0: its dir)
mob/Monsters/var/tmp/rm_turn_to = 0  // the way it is turning...
mob/Monsters/var/tmp/rm_turn_at = 0  // ...facing it from this world.time
mob/var/tmp/rm_arc = 0               // the arc of the blow it is striking: 0 front, 1 side, 2 behind
mob/var/tmp/rm_arc_left = 0          // that side blow comes from the target's left (its shield side)
mob/var/tmp/rm_flanks = 0            // blows it has landed from a side or behind (reports)
var/list/rm_dir_ring = list(NORTH, NORTHEAST, EAST, SOUTHEAST, SOUTH, SOUTHWEST, WEST, NORTHWEST)
// Rear surprise and charge (the user, 2026-10-26: "(a) + (b) together"). A unit doesn't notice a foe in its rear arc
// (RmNotices: to pick it as a target) until something strikes it or the foe is beside it at its side. One that ran
// rm_charge_steps tiles or more toward its foe in the last rm_charge_window ticks and strikes is charging: "Charge!", its
// first blow rm_charge_damage and +rm_charge_land to land, and its sides covered for rm_charge_cover ticks.
var/rm_rear_surprise_on = 1
var/rm_notice_after_hit = 100   // ticks after a blow it stays alert all round
var/rm_charge_on = 1
var/rm_charge_steps = 2
var/rm_charge_window = 20
var/rm_charge_cover = 10
var/rm_charge_damage = 1.25
var/rm_charge_land = 2
var/rm_charge_fresh = 30   // a charge is a first contact: no blow struck or taken for this long before
mob/Monsters/var/tmp/rm_hit_at = -1000      // its last blow taken
mob/Monsters/var/tmp/rm_run_x = 0           // where its run began...
mob/Monsters/var/tmp/rm_run_y = 0
mob/Monsters/var/tmp/rm_run_steps = 0       // ...the steps of it...
mob/Monsters/var/tmp/rm_step_at = -1000     // ...and its last step
mob/Monsters/var/tmp/rm_charge_until = 0    // its sides covered till then
mob/var/tmp/rm_charge_blow = 0              // this blow is a charge's first
mob/var/tmp/rm_charges = 0                  // charges it made (reports)

proc/RmNotices(mob/Monsters/U, mob/F)   // does U notice F (to go for it)?
	if(!rm_facing_on || !rm_rear_surprise_on || !istype(U) || !F || world.time - U.rm_hit_at < rm_notice_after_hit) return 1
	return RmArc(F, U) < 2

mob/Monsters/proc/RmFacing()
	return rm_face || dir

// Toward d at the turn's pace: called again and again while it means to (each blocked step, each blow), it faces d once
// rm_turn_ticks have passed since it first meant to.
mob/Monsters/proc/RmTurnToward(d)
	if(!d || !rm_facing_on)
		if(d) dir = d
		return
	var/f = RmFacing()
	if(d == f)
		rm_turn_to = 0
		return
	if(rm_turn_to != d)
		rm_turn_to = d
		rm_turn_at = world.time + RmTurnTicks()
	if(world.time >= rm_turn_at)
		rm_face = d
		rm_turn_to = 0
	dir = rm_face || f

mob/Monsters/proc/RmTurnTicks()
	return max(1, round(rm_turn_ticks - (RemasterCombatLevel(src, "Defence") - 1) / 25, 1))

// Awareness: does it meet a blow from arc (1 side, 2 behind) by A in time?
mob/Monsters/proc/RmAware(mob/A, arc)
	if(!rm_aware_on || Fainted || Stunned || RemasterKnockedOut() || rm_mstate == 2) return 0   // battle fury: tunnel vision (Morale.dm)
	var/roll = rand(1, 20)
	if(roll == 20) return 1
	if(roll == 1) return 0
	return roll >= (arc == 1 ? rm_aware_side : rm_aware_rear) - round((RemasterCombatLevel(src, "Defence") - RemasterCombatLevel(A, "Attack")) / rm_aware_per, 1) + RmMoraleAware()   // its morale (Morale.dm)

// mob/Monsters/Move: this file's part is step RmChainMove_Facing in Code/Remastered/Chains/Move.dm

// The arc a blows comes from: 0 its facing +-45 degrees, 1 +-90, 2 +-135 and straight back.
proc/RmArc(mob/A, mob/Monsters/D)
	if(!rm_facing_on || !istype(D) || !A || A.z != D.z || RmBeastKind(D)) return 0
	var/from = get_dir(D, A)
	if(!from) return 0
	var/a = rm_dir_ring.Find(from)
	var/b = rm_dir_ring.Find(D.RmFacing())
	if(!a || !b) return 0
	var/steps = abs(a - b)
	steps = min(steps, 8 - steps)
	if(steps <= 1) return 0
	if(steps == 2)
		if(D.rm_charge_until > world.time) return 0   // charging: its sides covered
		A.rm_arc_left = a == ((b + 5) % 8) + 1   // its facing turned 90 degrees to the left
		return 1
	return 2

// What of a shield block and a dodge the arc of this blow leaves (Combats.dm Attack).
mob/proc/RmArcShield()
	return rm_arc == 0 ? 1 : (rm_arc == 1 && rm_arc_left ? 0.5 : 0)
mob/proc/RmArcDodge()
	return rm_arc == 0 ? 1 : rm_arc == 1 ? 0.5 : 0

// mob/RemasterStrike: this file's part is step RmChainStrike_Facing in Code/Remastered/Chains/Strike.dm
