// Race specials: one aimed skill per race, on a cooldown. Select units and press F (or
// the special's button on the unit frame), then click where to aim it; right-click or
// Esc cancels. Every selected unit of that kind whose special is ready uses it. Specials
// only hurt units the caster may fight (enemies, raiders, a realm at war - never a realm
// at peace or your own people), and the 3D view previews the shape while aiming.
//   cone   - everything in a fan in front of the caster
//   line   - a shot along a line; "first" stops at the first unit it meets
//   throw  - lands within range and hits a small circle there
//   self   - a circle around the caster
//   dash / leap / blink - the caster moves (and may strike where it lands)

// race -> list(id, name, shape, range, arg (cone degrees / circle radius), cooldown seconds, description)
var/list/rm_specials = list(
	"Dragon"=list("breath", "Fire breath", "throw", 7, 2, 12, "Breathes a stream of fire at a spot: everything within 2 tiles of it burns and is set alight."),
	"Spider"=list("web", "Web shot", "first", 7, 0, 8, "Spits a web at the first enemy in line: stuck for 3 s, then slowed (10 silk)."),
	"Human"=list("charge", "Shield charge", "dash", 4, 0, 10, "Charges up to 4 tiles; the first enemy in the way is hit and stunned."),
	"Dwarf"=list("slam", "Ground slam", "self", 2, 2, 12, "Slams the ground: enemies within 2 tiles are hurt and staggered."),
	"Elf"=list("pierce", "Piercing arrow", "line", 9, 0, 10, "An arrow that goes through every enemy in a 9-tile line."),
	"Orc"=list("leap", "War leap", "leap", 4, 1, 12, "Leaps up to 4 tiles and crashes down on everyone around the landing."),
	"Goblin"=list("firepot", "Fire pot", "throw", 6, 1, 14, "Throws a pot of fire: a burst that sets enemies alight."),
	"Lizardman"=list("sweep", "Tail sweep", "self", 1, 1, 8, "Sweeps the tail around: enemies beside it are knocked back."),
	"Frogman"=list("tongue", "Tongue lash", "first", 6, 0, 9, "Lashes out and pulls the first enemy in line right up close."),
	"Kobold"=list("dart", "Poison dart", "first", 6, 0, 6, "A poisoned dart at the first enemy in line."),
	"Ratman"=list("plague", "Plague cloud", "throw", 6, 1, 14, "Throws a plague bag: a cloud of poison gas that slows and sickens."),
	"Svartalfar"=list("shadowstep", "Shadow step", "blink", 6, 0, 10, "Steps through the shadows to a spot within 6 tiles; the next blow lands hard."),
	"Devourer"=list("acid", "Acid spit", "first", 6, 0, 9, "Spits acid at the first enemy in line: it burns and eats their armour."),
	"Illithid"=list("mindblast", "Mind blast", "cone", 4, 60, 14, "A wave of psychic force: everyone in the cone is stunned and drained."))

// world/New: this file's part is step RmChainWorldNew_Specials in Code/Remastered/Chains/WorldNew.dm

mob/Monsters/var/tmp
	remaster_special_at = 0      // world.time it is ready again
	remaster_slow_until = 0
	remaster_root_until = 0
Player/var/tmp/list/remaster_aim  // units waiting for the aim click
var/list/rm_special_fx = list()   // list(id, special, sx, sy, tx, ty, z, time, element)
var/rm_special_fx_id = 0

// mob/Monsters/RemasterStepDelay: this file's part is step RmChainStepDelay_Specials in Code/Remastered/Chains/StepDelay.dm

mob/Monsters/proc/RemasterSpecial()
	return rm_specials[Race]

mob/Monsters/proc/RemasterSpecialName()
	var/list/S = RemasterSpecial()
	if(!S) return null
	if(S[1] == "breath")
		var/e = RemasterBreathLook()
		var/n = list("frost"="Frost breath", "poison"="Poison breath", "magma"="Magma spit", "sand"="Sand breath",
			"water"="Water spit", "plague"="Diseased breath", "holy"="Holy breath", "unholy"="Unholy breath")[e]
		if(n) return n
	return S[2]

mob/Monsters/proc/RemasterBreathElement()
	var/s = "[SubRace]"
	if(findtext(s, "Ice")) return "frost"
	if(findtext(s, "Poison")) return "poison"
	return "fire"

// What the breath looks like in 3D (the page's pixel particles, art/enhance/breath64.py): each
// kind of drake its own. What it does stays RemasterBreathElement's (the rest burn as fire).
mob/Monsters/proc/RemasterBreathLook()
	var/s = "[SubRace]"
	var/k = list("Magma"="magma", "Desert"="sand", "Sand"="sand", "Water"="water", "Zombie"="plague", "Holy"="holy", "Unholy"="unholy")[s]
	return k || RemasterBreathElement()

mob/Monsters/proc/RemasterSpecialData()
	var/list/S = RemasterSpecial()
	if(!S) return null
	return list("id"=S[1], "name"=RemasterSpecialName(), "shape"=S[3], "range"=S[4], "arg"=S[5],
		"wait"=max(0, round((remaster_special_at - world.time) / 10)), "desc"=S[7])

mob/Monsters/proc/RemasterSpecialAble()
	return RemasterSpecial() && HP > 0 && !GoingToDie && isturf(loc) && !Sleeping && !Fainted && !Stunned && !IsMist && !Meditating && !rm_bound   // not while chained down (Taming.dm)

// --- Aiming --------------------------------------------------------------------------
Player/proc/RemasterSpecialAim()
	var/list/ready = list()
	var/list/waiting = list()
	var/id
	for(var/mob/Monsters/M in Selected)
		if(M.Owner != src || !(M in UnitList) || !M.RemasterSpecialAble()) continue
		var/list/S = M.RemasterSpecial()
		if(id && S[1] != id) continue          // one kind of special per aim
		id = S[1]
		if(world.time < M.remaster_special_at) waiting += M
		else ready += M
	if(!length(ready))
		remaster_aim = null
		if(length(waiting))
			var/mob/Monsters/W = waiting[1]
			RemasterNotice("[W.RemasterSpecialName()] is ready in [round((W.remaster_special_at - world.time) / 10) + 1] s.")
		else RemasterNotice("Select a unit with a race special first (F).")
		return 0
	remaster_aim = ready
	var/mob/Monsters/F = ready[1]
	RemasterNotice("[F.RemasterSpecialName()]: click where to aim it. Right-click or Esc cancels.")
	return 1

Player/proc/RemasterSpecialCancel()
	if(remaster_aim) RemasterNotice("Special cancelled.")
	remaster_aim = null

Player/proc/RemasterAimData()
	if(!length(remaster_aim)) return null
	var/mob/Monsters/M = remaster_aim[1]
	if(!M || !M.loc) return null
	var/list/D = M.RemasterSpecialData()
	D["x"] = M.x
	D["y"] = M.y
	return D

// The aim click (client/Click, QoL.dm). Returns 1: the click is used up.
Player/proc/RemasterSpecialClick(atom/A)
	if(!length(remaster_aim)) return 0
	var/list/L = remaster_aim
	remaster_aim = null
	var/turf/T = RemasterTurf(A)
	if(!T) return 1
	var/n = 0
	var/was = remaster_notice
	remaster_notice = ""   // a caster that can't (a spider short of silk) says why itself: that stays
	for(var/mob/Monsters/M in L) if(M && M.z == T.z && M.RemasterSpecialAble() && world.time >= M.remaster_special_at)
		if(M.RemasterCastSpecial(T)) n++
	if(!length(remaster_notice))
		if(!n) RemasterNotice("Nothing happened: out of reach or blocked.")
		else remaster_notice = was
	return 1

// --- Shapes ------------------------------------------------------------------------------
proc/RemasterSpecialOpen(turf/T, mob/except)
	if(!T || T.density) return 0
	for(var/atom/movable/X in T) if(X.density && X != except) return 0
	return 1

// Tiles along a line from the caster toward T (up to range), stopping at walls.
mob/Monsters/proc/RemasterSpecialLine(turf/T, range)
	. = list()
	var/dx = T.x - x
	var/dy = T.y - y
	var/l = sqrt(dx * dx + dy * dy)
	if(!l) return
	var/ux = dx / l
	var/uy = dy / l
	var/turf/last = loc
	for(var/s = 0.5, s <= range + 0.01, s += 0.5)
		var/turf/X = locate(round(x + ux * s + 0.5), round(y + uy * s + 0.5), z)
		if(!X || X == last) continue
		if(X.density) break
		last = X
		. += X

mob/Monsters/proc/RemasterSpecialCone(turf/T, range, degrees)
	. = list()
	var/a0 = arctan(T.x - x, T.y - y)
	for(var/turf/X in range(range, src))
		if(X == loc || X.density) continue
		var/dx = X.x - x
		var/dy = X.y - y
		if(dx * dx + dy * dy > range * range + 0.5) continue
		var/d = arctan(dx, dy) - a0
		while(d > 180) d -= 360
		while(d < -180) d += 360
		if(abs(d) <= degrees / 2) . += X

// Where a throw or leap lands: T, pulled in to the range.
mob/Monsters/proc/RemasterSpecialReach(turf/T, range)
	var/dx = T.x - x
	var/dy = T.y - y
	var/l = sqrt(dx * dx + dy * dy)
	if(l <= range) return T
	return locate(round(x + dx / l * range + 0.5), round(y + dy / l * range + 0.5), z)

mob/Monsters/proc/RemasterSpecialFoes(list/tiles)
	. = list()
	for(var/turf/X in tiles) for(var/mob/Monsters/M in X)
		if(M != src && !RemasterIsSiege(M) && RemasterHostile(src, M, 1)) . += M

// --- Effects -----------------------------------------------------------------------------
mob/Monsters/proc/RemasterSpecialHurt(mob/Monsters/M, dmg, id)
	if(!M || M.HP <= 0) return
	var/before = RemasterBodyHealth(M)
	var/alive = !M.GoingToDie
	var/tx = M.x
	var/ty = M.y
	var/tz = M.z
	M.RemasterThreatenedBy(src)
	dmg = round(dmg * RemasterMagicScale(src))    // Magic skill (CombatSkills.dm)
	var/kind = dmg > 0 ? RemasterThrownWound(M, dmg, id) : "hit"
	if(!M || !M.loc)
		RemasterHitAt(tx, ty, tz, before, "kill", src, null)
		return
	if(alive && (M.HP <= 0 || M.GoingToDie)) kind = "kill"
	var/d = max(0, round(before - RemasterBodyHealth(M)))
	RemasterCombatXP("magic", d)
	RemasterHitAt(M.x, M.y, M.z, d, d > 0 || kind == "kill" ? kind : "miss", src, M.Owner)

mob/Monsters/proc/RemasterSpecialWord(mob/Monsters/M, word)
	if(M) RemasterHitAt(M.x, M.y, M.z, 0, word, src, M.Owner)

proc/RemasterStun(mob/Monsters/M, ticks)
	if(!M || M.Stunned) return
	M.Stunned = 1
	spawn(ticks) if(M) M.Stunned = 0

proc/RemasterSpecialFx(id, mob/Monsters/C, sx, sy, tx, ty, element)
	rm_special_fx += list(list(++rm_special_fx_id, id, sx, sy, tx, ty, C.z, world.time, element))
	if(length(rm_special_fx) > 60) rm_special_fx.Cut(1, length(rm_special_fx) - 59)

Player/proc/RemasterSpecialFxData()
	. = list()
	for(var/list/F in rm_special_fx)
		if(world.time - F[8] > 20 || F[7] != z || abs(F[3] - x) > 26 || abs(F[4] - y) > 26) continue
		. += list(list("id"=F[1], "sp"=F[2], "sx"=F[3], "sy"=F[4], "tx"=F[5], "ty"=F[6], "el"=F[9]))
	if(length(.)) RmSendFireFx()   // the pixel particles they are drawn with (Beasts.dm)

mob/Monsters/proc/RemasterLevelBonus()
	return ("Level" in vars) && isnum(vars["Level"]) ? vars["Level"] : 0

// Use the special toward T. Returns 1 if it went off.
mob/Monsters/proc/RemasterCastSpecial(turf/T)
	var/list/S = RemasterSpecial()
	if(!S || !T || T.z != z || T == loc) return 0
	var/id = S[1]
	var/range = S[4]
	var/sx = x
	var/sy = y
	dir = get_dir(src, T)
	switch(id)
		if("breath")
			// a stream from the jaws to a spot within reach; when it lands, everything within the
			// special's radius of the spot is caught in it
			var/turf/L = RemasterSpecialReach(T, range)
			if(!L) return 0
			var/el = RemasterBreathElement()
			RemasterSpecialFx(id, src, sx, sy, L.x, L.y, RemasterBreathLook())
			var/turf/at = L
			var/radius = S[5]
			spawn(3)
				if(!src || !at) return
				var/list/area = list()
				for(var/turf/X in range(radius, at)) if(!X.density) area += X
				RemasterBreathBurn(area, el, rand(12, 24) + RemasterLevelBonus() / 3, id)
		if("mindblast")
			var/list/tiles = RemasterSpecialCone(T, range, S[5])
			RemasterSpecialFx(id, src, sx, sy, T.x, T.y, "mind")
			for(var/mob/Monsters/M in RemasterSpecialFoes(tiles))
				RemasterStun(M, 25)
				M.Tiredness = max(0, M.Tiredness - 20)
				RemasterSpecialWord(M, "stun")
		if("web", "tongue", "dart", "acid")
			if(id == "web")
				if(WebContent < 10)
					if(istype(Owner, /Player)) Owner:RemasterNotice("[name] needs 10 silk for a web shot.")
					return 0
				WebContent -= 10
			var/list/line = RemasterSpecialLine(T, range)
			var/mob/Monsters/hit
			var/turf/end = length(line) ? line[length(line)] : T
			for(var/turf/X in line)
				var/list/F = RemasterSpecialFoes(list(X))
				if(length(F))
					hit = F[1]
					end = X
					break
			RemasterSpecialFx(id, src, sx, sy, end.x, end.y, hit ? "hit" : "miss")
			if(!hit) return RemasterSpecialDone(S)
			switch(id)
				if("web")
					hit.remaster_root_until = world.time + 30
					hit.remaster_slow_until = world.time + 90
					hit.destination = null
					RemasterSpecialWord(hit, "webbed")
					hit.RemasterThreatenedBy(src)
				if("tongue")
					// pulled to the tile right in front of the caster
					var/list/front = RemasterSpecialLine(hit.loc, 1)
					var/turf/next = length(front) ? front[1] : null
					if(next && next != hit.loc && RemasterSpecialOpen(next, hit)) hit.loc = next
					RemasterStun(hit, 10)
					RemasterSpecialHurt(hit, rand(3, 6), id)
				if("dart")
					RemasterSpecialHurt(hit, rand(4, 8), id)
					if(hit && hit.HP > 0 && !hit.ImmunePoison) hit.BloodContent -= 20
				if("acid")
					RemasterSpecialHurt(hit, rand(10, 18), id)
					if(hit && hit.HP > 0)
						hit.Defence -= 15
						var/mob/Monsters/H = hit
						spawn(150) if(H) H.Defence += 15
						RemasterSpecialWord(hit, "melt")
		if("pierce")
			var/list/line = RemasterSpecialLine(T, range)
			var/turf/end = length(line) ? line[length(line)] : T
			RemasterSpecialFx(id, src, sx, sy, end.x, end.y, null)
			for(var/mob/Monsters/M in RemasterSpecialFoes(line)) RemasterSpecialHurt(M, rand(10, 20) + BowSkill / 10, id)
		if("charge")
			var/list/line = RemasterSpecialLine(T, range)
			var/mob/Monsters/hit
			for(var/turf/X in line)
				var/list/F = RemasterSpecialFoes(list(X))
				if(length(F))
					hit = F[1]
					break
				if(!RemasterSpecialOpen(X, src)) break
				loc = X
			RemasterSpecialFx(id, src, sx, sy, x, y, null)
			if(hit)
				RemasterSpecialHurt(hit, rand(8, 14), id)
				RemasterStun(hit, 20)
		if("leap", "shadowstep")
			var/turf/L = RemasterSpecialReach(T, range)
			if(!RemasterSpecialOpen(L, src))
				for(var/turf/X in range(1, L)) if(RemasterSpecialOpen(X, src))
					L = X
					break
			if(!RemasterSpecialOpen(L, src)) return 0
			loc = L
			destination = null
			RemasterSpecialFx(id, src, sx, sy, L.x, L.y, null)
			if(id == "leap")
				for(var/mob/Monsters/M in RemasterSpecialFoes(range(1, L)))
					RemasterSpecialHurt(M, rand(14, 24), id)
					RemasterStun(M, 10)
			else remaster_opening = max(remaster_opening, 4)    // +12 on the next blow (Combats.dm)
		if("slam", "sweep")
			var/list/tiles = list()
			for(var/turf/X in range(S[5], src)) if(X != loc) tiles += X
			RemasterSpecialFx(id, src, sx, sy, sx, sy, null)
			for(var/mob/Monsters/M in RemasterSpecialFoes(tiles))
				if(id == "slam")
					RemasterSpecialHurt(M, rand(10, 18), id)
					RemasterStun(M, 15)
				else
					RemasterSpecialHurt(M, rand(6, 12), id)
					var/d = get_dir(src, M)
					for(var/k = 1, k <= 2, k++) if(M && RemasterSpecialOpen(get_step(M, d), M)) M.loc = get_step(M, d)
		if("firepot", "plague")
			var/turf/L = RemasterSpecialReach(T, range)
			if(!L) return 0
			RemasterSpecialFx(id, src, sx, sy, L.x, L.y, null)
			var/turf/at = L
			var/flight = 4 + round(get_dist(src, L) * 0.8)
			spawn(flight)
				if(!src || !at) return
				var/list/area = list()
				for(var/turf/X in range(S[5], at)) if(!X.density) area += X
				if(id == "plague")
					for(var/turf/X in area) RemasterGasAdd(X, "poison", 40)
				for(var/mob/Monsters/M in RemasterSpecialFoes(area))
					if(id == "firepot")
						RemasterSpecialHurt(M, rand(6, 12), id)
						if(M && M.HP > 0 && prob(50)) M.Fire()
					else
						M.remaster_slow_until = world.time + 80
						RemasterSpecialHurt(M, rand(3, 6), id)
	return RemasterSpecialDone(S)

// What a dragon's breath does to those it catches: fire burns and may set alight (and, heat
// set, heats the ground, which may catch), frost slows and chills, poison sickens.
mob/Monsters/proc/RemasterBreathBurn(list/area, el, dmg, id, heat = 1)
	if(el == "fire" && heat) for(var/turf/X in area) RemasterHeat(X, 220)
	for(var/mob/Monsters/M in RemasterSpecialFoes(area))
		RemasterSpecialHurt(M, el == "fire" ? RmFireDamage(M, dmg) : dmg, id)   // dragonscale takes some (BeastParts.dm)
		if(!M || M.HP <= 0) continue
		if(el == "fire" && prob(35)) M.Fire()
		else if(el == "frost")
			M.remaster_slow_until = world.time + 60
			M.Coldness = min(100, M.Coldness + 20)
		else if(el == "poison") M.BloodContent -= 15

mob/Monsters/proc/RemasterSpecialDone(list/S)
	remaster_special_at = world.time + S[6] * 10
	if(istype(Owner, /Player)) Owner:RemasterLog("[name] used [RemasterSpecialName()]", "fight", loc)
	return 1

// F (skin.dmf) and the unit frame's button.
Player/verb/RemasterSpecialVerb()
	set name = "Remaster-Special"
	set hidden = 1
	if(length(remaster_aim)) RemasterSpecialCancel()
	else RemasterSpecialAim()
