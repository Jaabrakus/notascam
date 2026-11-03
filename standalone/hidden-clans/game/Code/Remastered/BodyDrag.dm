// Bodies are dragged, not carried (user, 2026-10-25: "the body carry should be body drag?").
// "Drag body" (the body's right-click card, the Interact (I) card): the unit walks over and takes hold, and the body
// comes along on the ground a tile behind it, lying as it fell, a tile at a time as the dragger steps (no easing).
// The dragger goes slower: rm_drag_speed of its pace, rm_drag_speed_strong at Strength rm_drag_strong_at and up.
// "Let go" leaves it where it lies; the dragger dying, going down (Surgery.dm RemasterIsDown) or changing level lets
// go too. Bodies never lie stacked: a step goes only to open ground with no other body or unit on it.
// What used a body in the hands still does: the gravedigger drags the dead to the graveyard and buries them, and the
// old menus and jobs that want a body carried (the hunter's butchering, the workshops' Tear all Meat / Strip all
// Skin from Corpses) take a dragged body lying right beside the unit up into its hands first (RmHeldBodies); one
// that is not used up goes back to being dragged. The Operating table takes one dragged beside it (Surgery.dm).
// Cages hold the living only (pits, Captives.dm): no body goes in one. Small game the hunter kills is still carried.
// Bodies on the ground are not in the world save (WorldSave.dm keeps items and workshops), so no drag is saved; one
// taken up into the hands is saved as carried, as before.
// rm_body_drag = 0: "Carry the body" picks it up into the hands, as before (TargetActions.dm RemasterCarryBody).
// This file is included last: its overrides come after every other definition of the procs they wrap.

var/rm_body_drag = 1
var/rm_drag_speed = 0.6          // the dragger's pace while dragging (x its own)
var/rm_drag_speed_strong = 0.8   // ... at Strength rm_drag_strong_at and up
var/rm_drag_strong_at = 40

mob/Body/var/tmp/mob/Monsters/rm_dragged_by
mob/Monsters/var/tmp/mob/Body/rm_dragging
var/list/rm_drag_list = list()   // bodies being dragged, moved by RmDragLoop (which runs only while there are some)
var/rm_drag_looping = 0

// The body this unit drags (at any distance: it may lag a tile while the dragger steps), or null.
mob/Monsters/proc/RmDragged()
	var/mob/Body/B = rm_dragging
	if(!B) return null
	if(Rm3DGone(B) || B.rm_dragged_by != src)
		rm_dragging = null
		return null
	return B

// ... when it lies right beside the unit (or under it), on the same level.
mob/Monsters/proc/RmDraggedBeside()
	var/mob/Body/B = RmDragged()
	if(B && isturf(B.loc) && B.z == z && get_dist(B, src) <= 1) return B
	return null

mob/Monsters/proc/RmDragStart(mob/Body/B)
	if(!B || Rm3DGone(B) || !isturf(B.loc) || B.suffix || B.z != z || HP <= 0) return 0
	var/mob/Body/old = RmDragged()
	if(old) RmDragRelease(old, src)
	B.rm_dragged_by = src
	B.suffix = "(Dragged)"   // not picked up by anyone else (PickUpItem wants no suffix), not taken by a job
	rm_dragging = B
	rm_drag_list |= B
	if(!rm_drag_looping)
		rm_drag_looping = 1
		spawn(0) RmDragLoop()
	remaster_order_status = "Dragging [RemasterDeadName(B)]"
	return 1

// The body lies where it is; `why` tells the player (the dragger died, went down, changed level).
proc/RmDragRelease(mob/Body/B, mob/Monsters/M, why)
	rm_drag_list -= B
	if(B && !Rm3DGone(B))
		B.rm_dragged_by = null
		if(B.suffix == "(Dragged)") B.suffix = null
	if(!M || Rm3DGone(M) || M.rm_dragging != B) return
	M.rm_dragging = null
	if(findtext("[M.remaster_order_status]", "Dragging")) M.remaster_order_status = "Idle"
	var/Player/P = M.Owner
	if(why && istype(P)) P.RemasterNotice("[M.RemasterBareName()] lets go of [B && !Rm3DGone(B) ? RemasterDeadName(B) : "the body"]: [why].")

// For what wants a body in the hands: the dragged one beside the unit is taken up, and put back on the ground and
// dragged again a moment later if it was not used up (buried, butchered).
mob/Monsters/proc/RmDragTakeUp(mob/Body/B)
	RmDragRelease(B, src)
	ForcePickUpItem(B)
	spawn(10) RmDragBack(B)
	return B

mob/Monsters/proc/RmDragBack(mob/Body/B)
	if(!B || Rm3DGone(B) || B.loc != src || B.suffix != "(Carrying)" || !isturf(loc) || HP <= 0) return
	B.loc = loc
	B.suffix = null
	weight -= B.weight
	RmDragStart(B)

// The bodies in this unit's hands, a dragged one beside it taken up first (the old corpse menus and jobs loop over
// the bodies a unit carries).
mob/proc/RmHeldBodies()
	. = list()
	for(var/mob/Body/B in src) . += B

mob/Monsters/RmHeldBodies()
	var/mob/Body/D = RmDraggedBeside()
	if(D) RmDragTakeUp(D)
	return ..()

// Open ground a body can be dragged onto: no wall, tree or water, nothing solid, no other body, no unit.
proc/RmDragFree(turf/T, mob/Body/B)
	if(!T || T.density || T.vars["Tree"]) return 0
	for(var/atom/movable/O in T) if(O != B && (O.density || istype(O, /mob/Body) || istype(O, /mob/Monsters))) return 0
	return 1

// One step after the dragger: the tile behind it (where it stood), else the open tile beside it nearest the body.
mob/Body/proc/RmDragStep(mob/Monsters/M)
	var/turf/best
	var/turf/behind = get_step(M, turn(M.dir, 180))
	if(behind && get_dist(behind, M) == 1 && RmDragFree(behind, src)) best = behind
	else for(var/turf/T in orange(1, M)) if(RmDragFree(T, src) && (!best || get_dist(T, src) < get_dist(best, src))) best = T
	if(best)
		loc = best
		return 1
	if(get_dist(M, src) > 3) RmDragRelease(src, M, "no room to drag it through")
	return 0

// Every tick while anyone drags: the body steps after its dragger, and is let go when the dragger can't hold on.
proc/RmDragLoop()
	while(length(rm_drag_list))
		sleep(1)
		for(var/mob/Body/B in rm_drag_list.Copy())
			if(Rm3DGone(B))
				rm_drag_list -= B
				continue
			var/mob/Monsters/M = B.rm_dragged_by
			if(!M || Rm3DGone(M) || M.rm_dragging != B)
				RmDragRelease(B, null)
				continue
			if(M.HP <= 0 || M.GoingToDie)
				RmDragRelease(B, M, "killed")
				continue
			if(M.RemasterIsDown())
				RmDragRelease(B, M, "down")
				continue
			if(M.z != B.z || !isturf(M.loc) || !isturf(B.loc))
				RmDragRelease(B, M, "a level changed")
				continue
			if(get_dist(M, B) != 1) B.RmDragStep(M)
	rm_drag_looping = 0

// Slower going while dragging. A group's or a move order's pace comes from RemasterOwnStep (Formations.dm); a unit
// walking on its own takes RemasterStepDelay's: slowed in one of the two, never both.
mob/Monsters/proc/RmDragPace(d)
	var/s = RemasterCombatLevel(src, "Strength") >= rm_drag_strong_at ? rm_drag_speed_strong : rm_drag_speed
	return max(d + 1, round(d / max(0.1, s) + 0.5))

mob/Monsters/RemasterOwnStep()
	. = ..()
	if(rm_dragging && RmDragged()) . = RmDragPace(.)

// mob/Monsters/RemasterStepDelay: this file's part is step RmChainStepDelay_BodyDrag in Code/Remastered/Chains/StepDelay.dm

// "Drag body" / "Let go" ("carrier|body" / "carrier|body|0"; HUD.dm "carrybody").
Player/RemasterCarryBody(value)
	if(!rm_body_drag) return ..()
	var/list/p = splittext("[value]", "|")
	if(length(p) < 2) return 0
	var/mob/Monsters/M = RemasterUIUnit(p[1])
	var/mob/Body/B = locate(p[2])
	if(!istype(M) || M.Owner != src || !istype(B)) return 0
	if(length(p) >= 3 && p[3] == "0")
		if(B.rm_dragged_by != M) return 0
		RmDragRelease(B, M)
		RemasterNotice("[M.RemasterBareName()] lets go of [RemasterDeadName(B)].")
		return 1
	if(!isturf(B.loc) || B.suffix) return 0
	M.RemasterCancelOrders()
	M.remaster_patrol = null   // a direct order ends a patrol, or the patrol tick sends it back out on its route (Patrol.dm)
	var/mob/Body/old = M.RmDragged()
	if(old) RmDragRelease(old, M)
	M.destination = B
	M.remaster_order_status = "Going to drag [RemasterDeadName(B)]"
	spawn(0) M.RmDragGoTo(B, src)
	return 1

mob/Monsters/proc/RmDragGoTo(mob/Body/B, Player/P)
	for(var/t = 0, t < 120, t++)
		if(!src || HP <= 0 || Rm3DGone(B) || !isturf(B.loc) || B.suffix) return
		if(get_dist(src, B) <= 1 && z == B.z)
			destination = null
			if(RmDragStart(B) && P) P.RemasterNotice("[RemasterBareName()] takes hold of [RemasterDeadName(B)] and drags them along: slower going. Let go from the body's card.")
			return
		if(destination != B) return   // given another order on the way
		sleep(5)

// The Interact (I) card's list: a body on the ground offers "dragbody" (the page: Drag), the one this unit drags
// "letgo" (Let go).
mob/Monsters/RemasterNearbyData(Player/P)
	. = ..()
	if(!rm_body_drag) return
	for(var/list/E in .) if(E["kind"] == "body" && ("carrybody" in E["acts"])) E["acts"] = list("dragbody")
	var/mob/Body/B = RmDragged()
	if(B) . += list(list("id"="\ref[B]", "name"=RemasterDeadName(B), "kind"="body", "dist"=get_dist(src, B), "acts"=list("letgo")))

// The gravedigger (Graves.dm): the body it drags is the one it is taking to the graveyard, and burying takes it up.
mob/Monsters/RemasterCarriedBody()
	. = ..()
	if(!. && rm_body_drag) . = RmDragged()

mob/Monsters/RemasterBury(mob/Body/B)
	if(B && !Rm3DGone(B) && B.rm_dragged_by == src)
		if(!RmDraggedBeside()) return 0   // still a step behind: next time
		RmDragTakeUp(B)
	return ..()
