// Land claims: a Claim banner (1 wood, built like a workshop) claims the land around
// it for its player's realm. The claim grows with the settlement's rank (Progress.dm):
// radius 8 at Camp up to 30 at Kingdom, and one banner per rank. Inside someone else's
// land your units may not dig, chop or build (orders, blueprints, workshops); the 3D
// view draws every realm's border and banner.

var/list/rm_claim_radius = list(8, 12, 16, 22, 30)
var/list/rm_banners = list()

obj/RemasterBanner
	name = "Claim banner"
	icon = 'Icons/Remastered/Runes.dmi'
	icon_state = "lamp_on"
	density = 0
	var/owner_key
	var/owner_name
	var/radius = 8
	var/colour = "#e0bb73"
	New()
		..()
		rm_banners += src
	Del()
		rm_banners -= src
		..()

proc/RemasterClaimColour(key)
	var/h = md5("[key]")
	var/list/C = list("#e0bb73", "#d9534f", "#5bc0de", "#9b59b6", "#5cb85c", "#f0ad4e", "#e67e22", "#1abc9c")
	return C[(text2num(copytext(h, 1, 3), 16) % length(C)) + 1]

// The banner whose land this is (nearest claim wins where two would overlap).
proc/RemasterClaimAt(turf/T)
	if(!T) return null
	var/obj/RemasterBanner/best
	var/bd = 1e9
	for(var/obj/RemasterBanner/B in rm_banners)
		if(!B.loc || B.z != T.z) continue
		var/d = max(abs(B.x - T.x), abs(B.y - T.y))
		if(d <= B.radius && d < bd)
			bd = d
			best = B
	return best

Player/proc/RemasterClaimRadius()
	return rm_claim_radius[clamp(remaster_rank, 1, length(rm_claim_radius))]

Player/proc/RemasterBanners()
	. = list()
	for(var/obj/RemasterBanner/B in rm_banners) if(B.owner_key == key) . += B

// May this player's units work (dig, chop, build) on T?
Player/proc/RemasterMayWork(turf/T, quiet = 0)
	var/obj/RemasterBanner/B = RemasterClaimAt(T)
	if(!B || RemasterAlliedKeys(B.owner_key, key)) return 1
	if(RemasterWarMayWork(src, B)) return 1      // at war: sieges may dig and tear down (War.dm)
	if(!quiet) RemasterNotice("That land belongs to [B.owner_name]'s realm.")
	return 0

Player/proc/RemasterClaimTick()
	if(remaster_liege && rm_lieges[key] != remaster_liege)
		rm_lieges[key] = remaster_liege
		rm_realm_ver++   // War.dm
	var/r = RemasterClaimRadius()
	for(var/obj/RemasterBanner/B in RemasterBanners())
		B.radius = r
		B.owner_name = RemasterHouse()

Player/proc/RemasterBuildBanner(mob/Monsters/M, turf/T)
	if(!T || T.density || M.loc != T) return 0
	var/list/mine = RemasterBanners()
	if(length(mine) >= remaster_rank)
		RemasterNotice("Your rank allows [remaster_rank] banner[remaster_rank > 1 ? "s" : ""]. Grow your settlement for more.")
		return 0
	var/obj/RemasterBanner/O = RemasterClaimAt(T)
	if(O && O.owner_key != key)
		RemasterNotice("That land already belongs to [O.owner_name]'s realm.")
		return 0
	var/obj/Items/used
	for(var/obj/Items/woods/wood/W in M) if(W.suffix != "(Equipped)")
		used = W
		break
	if(!used)
		RemasterNotice("[M.name] needs a piece of wood for the banner.")
		return 0
	if(!M.RemasterManualHandoff(src)) return 0
	var/obj/RemasterBanner/B = new(T)
	B.owner_key = key
	B.owner_name = RemasterHouse()
	B.radius = RemasterClaimRadius()
	B.colour = RemasterClaimColour(key)
	M.weight -= used.weight
	del(used)
	var/text = length(mine) ? "A new banner extends your realm." : "You have claimed this land as your realm."
	RemasterNotice(text)
	RemasterLog(text, "good", T)
	return 1

// For the 3D view: banners near the camera (and so their borders).
Player/proc/RemasterClaimData()
	. = list()
	for(var/obj/RemasterBanner/B in rm_banners) if(B.loc && B.z == z && get_dist(B, src) <= 70)
		. += list(list("x"=B.x, "y"=B.y, "r"=B.radius, "color"=B.colour, "mine"=(B.owner_key == key), "name"=B.owner_name))

// Saved with the world (WorldSave.dm): banners are neither items nor workshops,
// so without their own records every realm's claim was gone after a restart.
proc/RemasterBannerRecords()
	. = list()
	for(var/obj/RemasterBanner/B in rm_banners) if(isturf(B.loc))
		. += list(list(B.x, B.y, B.z, B.owner_key, B.owner_name, B.radius, B.colour))

proc/RemasterBannerRestore(list/L)
	. = 0
	for(var/list/R in L)
		if(length(R) < 7) continue
		var/turf/T = locate(R[1], R[2], R[3])
		if(!T || !R[4]) continue
		var/obj/RemasterBanner/B = new(T)
		B.owner_key = R[4]
		B.owner_name = R[5]
		if(isnum(R[6])) B.radius = R[6]
		if(R[7]) B.colour = R[7]
		.++
