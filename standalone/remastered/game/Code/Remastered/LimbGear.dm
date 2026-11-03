// Worn gear over a lost limb, in the 3D view. The original draws leggings and arm pieces over a missing
// leg or arm (OverlayBuilds.dm RebuildOverlays, kept as it is on the 2D map); in 3D the gear is cut where
// the limb was, so the stump shows (the user, 2026-10-23: "the armor does account for the missing limbs").
// The cut: where the body's whole picture has the limb and its missing-limb pose has nothing, the stump (pose
// pixels past the old body, or blood red on it), and RM_LIMB_MASK_GROW px beside the limb outside the pose's
// body; never the rest of the pose's body, so gear over what is left stays whole. Per body picture, pose, facing and frame, cached. A grafted or false limb is there
// (Has... = 1, Surgery.dm), so its gear stays. Capes, quivers, helmets and crowns are never cut.

#define RM_LIMB_MASK_GROW 2

var/list/rm_limb_masks = list()
var/list/rm_limb_uncut = list(/obj/Items/Equipment/Armour/Capes, /obj/Items/Equipment/Armour/Helmet,
	/obj/Items/Equipment/Armour/Crown, /obj/Items/Equipment/Armour/Quiver)

// What cuts M's gear: list(body picture, the pose for its truly missing limbs), or null when it has them all.
proc/RmLimbMaskFor(mob/M, body64)
	if(!istype(M, /mob/Monsters)) return null
	var/bits = "[M.HasLeftArm ? 0 : 1][M.HasRightArm ? 0 : 1][M.HasLeftLeg ? 0 : 1][M.HasRightLeg ? 0 : 1]"
	if(bits == "0000") return null
	var/state = rm_limb_states[bits]
	var/source = body64 || M.icon
	if(!source || !state || !(state in icon_states(source))) return null
	return list(source, state)

// A piece made for one arm (a vambrace, a gauntlet) is not drawn at all once that arm is gone: on a body whose
// hand hung over its hip, a cut alone would leave the gauntlet there. Nor is what that arm held: the pictures
// put a weapon in the right hand and a shield on the left arm, so without the arm it would float by the stump.
proc/RmLimbGearGone(mob/M, obj/Items/E)
	if(istype(E, /obj/Items/Equipment/Armour/LeftArm) || istype(E, /obj/Items/Equipment/Armour/Shield)) return !M.HasLeftArm
	if(istype(E, /obj/Items/Equipment/Armour/RightArm) || istype(E, /obj/Items/Equipment/Weapon)) return !M.HasRightArm
	return 0

// Off the unit too, not just out of the picture. The original's cut at 0 health drops that arm's armour (a broken arm
// its weapon or shield), but the newer cuts (Wounds.dm RmSever, a thrown weapon's in Throwing.dm) could take an arm with
// the sword still held, the shield or gauntlet still worn: gone in 3D, yet still striking, blocking and counted on the
// card (polish 10-26). Every path that takes a limb calls LimbLoss() (Stumps.dm); a moment after it (the original's own
// drops and lines go first) whatever is still worn or held on a missing arm is dropped where the unit stands, or put in
// its bag when its save is being read. Not for the races that keep their limbs.
mob/Monsters/LimbLoss()
	. = ..()
	if((HasLeftArm && HasRightArm) || CantLoseLimbs || (Race in list("Devourer", "Dragon", "Spider"))) return
	var/loading = rm_units_loading && world.time - rm_units_loading_at < 100
	spawn(0) if(!Rm3DGone(src)) RmLimbGearOff(loading)

mob/Monsters/proc/RmLimbGearOff(keep = 0)
	for(var/obj/Items/Equipment/E in src)
		if(E.suffix != "(Equipped)" || !RmLimbGearGone(src, E) || !UnEquipItem(E)) continue
		if(!keep && !E.NoDropOnDeath && isturf(loc)) DropItem(E)

// A gear layer to be cut: its picture, state, key and frame source as before, the cut fifth.
proc/RmLimbMasked(list/G, list/cut)
	if(!cut || !G) return G
	return list(G[1], G[2], length(G) >= 3 ? G[3] : G[1], length(G) >= 4 ? G[4] : G[1], cut)

proc/RmLimbMaskedAll(list/layers, list/cut)
	if(!cut) return layers
	. = list()
	for(var/list/X in layers) . += list(RmLimbMasked(X, cut))

// A white picture with holes where gear must not show, for ICON_MULTIPLY; null when the pose changes nothing.
proc/RmLimbMaskCell(list/cut, dir, frame)
	if(frame > 1 && Remaster3DFrames(cut[1], cut[2]) < frame) frame = 1   // a pose without walk frames stands still: so does its cut
	var/key = "[cut[1]]|[cut[2]]|[dir]|[frame]"
	if(key in rm_limb_masks) return rm_limb_masks[key]
	var/icon/N = Remaster3DCell(cut[1], "Normal", dir, frame)
	var/icon/P = Remaster3DCell(cut[1], cut[2], dir, frame)
	var/icon/K
	if(N && P && N.Width() == P.Width() && N.Height() == P.Height())
		var/w = N.Width()
		var/h = N.Height()
		var/list/gone = list()
		var/list/hole = new(w * h)
		var/list/body = new(w * h)   // the pose's own pixels: their gear stays, unless it is the stump
		for(var/x = 1, x <= w, x++)
			for(var/y = 1, y <= h, y++)
				var/a = N.GetPixel(x, y)   // "" when see-through (the sheets have no half-clear pixels)
				var/b = P.GetPixel(x, y)
				var/i = (y - 1) * w + x
				if(a && !b)
					gone += i   // the limb was here
					hole[i] = 1
				else if(b)
					body[i] = 1
					if(!a || (a != b && RmLimbRed(b) && !RmLimbRed(a))) hole[i] = 1   // the stump: drawn past the old body, or blood on it
		if(length(gone))
			for(var/i in gone)
				var/x0 = (i - 1) % w + 1
				var/y0 = round((i - 1) / w) + 1
				for(var/x = max(1, x0 - RM_LIMB_MASK_GROW), x <= min(w, x0 + RM_LIMB_MASK_GROW), x++)
					for(var/y = max(1, y0 - RM_LIMB_MASK_GROW), y <= min(h, y0 + RM_LIMB_MASK_GROW), y++)
						var/j = (y - 1) * w + x
						if(!body[j]) hole[j] = 1   // gear wider than the limb, beside it
			K = icon(N)
			K.DrawBox("#ffffff", 1, 1, w, h)
			for(var/j = 1, j <= w * h, j++) if(hole[j]) K.DrawBox(null, (j - 1) % w + 1, round((j - 1) / w) + 1)
	rm_limb_masks[key] = K
	return K

// Blood red: the colour of a stump.
proc/RmLimbRed(c)
	var/r = text2num(copytext(c, 2, 4), 16)
	return r >= 40 && r > 2 * text2num(copytext(c, 4, 6), 16) && r > 2 * text2num(copytext(c, 6, 8), 16)

// Cut one gear cell of a strip (Remaster3DStrip) where its unit's limb is gone.
proc/RmLimbCut(icon/C, list/cut, dir, frame)
	if(!C || !cut) return C
	var/icon/K = RmLimbMaskCell(cut, dir, frame)
	if(K && K.Width() == C.Width() && K.Height() == C.Height()) C.Blend(K, ICON_MULTIPLY)
	return C
