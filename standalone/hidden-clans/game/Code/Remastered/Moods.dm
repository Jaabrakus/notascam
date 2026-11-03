// Moods. Every unit of a player has a mood (0 miserable .. 100 joyful) made of
// thoughts: needs that last while they last (hungry, starving, tired, cold, hurt,
// no bed) and memories that fade (a good meal, raw food, a proper room, a friend's
// or family member's death, the realm growing, a raid beaten). Mood drifts toward
// 50 + the thoughts. Unhappy units (below 30) work slower; miserable ones (below 12)
// snap: they sulk and refuse work, throw a tantrum and smash something they carry,
// or wander off for a while. Snapping lets off steam (+15).

// Moods are switched off for now (rm_moods_on = 0): no mood ticks, no slower work,
// no snapping, and the HUD hides the mood bar. Set it to 1 to bring them back.
var/rm_moods_on = 0

#define RM_MOOD_EVERY 50            // ticks between mood updates per player
#define RM_MOOD_SNAP 12
#define RM_MOOD_UNHAPPY 30
var/rm_mood_unhappy = RM_MOOD_UNHAPPY   // for Settlement.dm's fast path: it's included first, so it can't see the #define

mob/Monsters/var
	remaster_mood = 60              // saved
	list/remaster_memories          // saved: list(list(id, text, value, until world.time-ish day))
mob/Monsters/var/tmp
	list/remaster_thoughts          // what counts now: list(list(text, value))
	remaster_snap_until = 0
	remaster_snap_kind
	remaster_mourned = 0
	remaster_mood_said = 0
Player/var/tmp/remaster_mood_at = 0

// A memory: replaces an older one with the same id; lasts `days` game days.
mob/Monsters/proc/RemasterRemember(id, text, value, days = 1)
	if(!remaster_memories) remaster_memories = list()
	for(var/list/M in remaster_memories.Copy()) if(M[1] == id) remaster_memories -= list(M)
	var/Player/P = Owner
	var/today = istype(P) ? P.remaster_days : 0
	remaster_memories += list(list(id, text, value, today + days))

mob/Monsters/proc/RemasterMoodThoughts()
	var/list/T = list()
	var/full = MaxHunger ? Hunger / MaxHunger : 1
	if(full < 0.1) T += list(list("Starving", -30))
	else if(full < 0.25) T += list(list("Hungry", -14))
	if(Tiredness < 15) T += list(list("Exhausted", -16))
	else if(Tiredness < 30) T += list(list("Tired", -8))
	if(RemasterFeelsCold() && Coldness >= 40) T += list(list("Freezing", -12))
	if(MAXHP && HP < MAXHP * 0.5) T += list(list("Badly hurt", -12))
	if(islist(remaster_home) && length(remaster_home) == 3 && RemasterBedAt(remaster_home))
		T += list(list("Has a bed of their own", 6))
	else T += list(list("No bed", -6))
	T += RemasterRoomThoughts(Owner)       // bedrooms, a throne room (Rooms.dm)
	if(remaster_attacker && world.time - remaster_attacked_at < 300) T += list(list("Was attacked", -6))
	var/Player/P = Owner
	var/today = istype(P) ? P.remaster_days : 0
	if(remaster_memories) for(var/list/M in remaster_memories.Copy())
		if(M[4] < today) remaster_memories -= list(M)
		else T += list(list(M[2], M[3]))
	return T

mob/Monsters/proc/RemasterMoodName()
	if(remaster_snap_until > world.time) return "Snapped"
	if(remaster_mood >= 80) return "Joyful"
	if(remaster_mood >= 60) return "Content"
	if(remaster_mood >= RM_MOOD_UNHAPPY) return "Uneasy"
	if(remaster_mood >= RM_MOOD_SNAP) return "Unhappy"
	return "Miserable"

mob/Monsters/proc/RemasterMoodTick(Player/P)
	remaster_thoughts = RemasterMoodThoughts()
	var/target = 50
	for(var/list/T in remaster_thoughts) target += T[2]
	target = clamp(target, 0, 100)
	var/step = clamp(target - remaster_mood, -4, 3)
	remaster_mood = clamp(remaster_mood + step, 0, 100)
	if(remaster_snap_until && world.time > remaster_snap_until)
		remaster_snap_until = 0
		remaster_snap_kind = null
		remaster_role_paused = 0
		remaster_work_status = "Calmed down"
	if(!remaster_snap_until && remaster_mood < RM_MOOD_SNAP && prob(25)) RemasterSnap(P)
	else if(remaster_mood < RM_MOOD_UNHAPPY && world.time - remaster_mood_said > 3000)
		remaster_mood_said = world.time
		var/list/bad = list()
		for(var/list/T in remaster_thoughts) if(T[2] < 0) bad += lowertext(T[1])
		P.RemasterLog("[name] is unhappy[length(bad) ? ": [jointext(bad, ", ")]" : ""].", "problem", src)

// Snapping: sulk (refuse work), smash something carried, or wander off.
mob/Monsters/proc/RemasterSnap(Player/P)
	var/kind = pick(prob(50) ? "sulk" : "tantrum", "wander")
	remaster_snap_kind = kind
	remaster_snap_until = world.time + 900
	RemasterCancelOrders()
	destination = null
	switch(kind)
		if("sulk")
			remaster_role_paused = 1
			remaster_work_status = "Sulking: refuses to work"
			P.RemasterLog("[name] snapped and refuses to work!", "problem", src)
		if("tantrum")
			var/obj/Items/I
			for(var/obj/Items/X in src) if(X.suffix != "(Equipped)") I = X
			if(I)
				view(src) << "<b><font color=red>[src] throws a tantrum and smashes the [I]!</font></b>"
				weight -= I.weight
				del(I)
			else view(src) << "<b><font color=red>[src] throws a tantrum!</font></b>"
			remaster_role_paused = 1
			remaster_work_status = "Throwing a tantrum"
			P.RemasterLog("[name] threw a tantrum!", "problem", src)
		if("wander")
			var/turf/T = locate(clamp(x + rand(-14, 14), 2, world.maxx - 1), clamp(y + rand(-14, 14), 2, world.maxy - 1), z)
			if(T && !T.density) destination = T
			remaster_role_paused = 1
			remaster_work_status = "Wandered off to be alone"
			P.RemasterLog("[name] wandered off to be alone.", "problem", src)
	remaster_mood = min(100, remaster_mood + 15)
	P.RemasterNotice("[name] snapped ([RemasterMoodName()]). Better food, beds and rooms keep spirits up.")

// Unhappy units work slower: some of their work ticks are skipped (Settlement.dm).
mob/Monsters/proc/RemasterMoodSkipsWork()
	if(!rm_moods_on) return 0
	if(remaster_snap_until > world.time) return 1
	if(remaster_mood < RM_MOOD_UNHAPPY) return prob(round((RM_MOOD_UNHAPPY - remaster_mood) * 1.6))
	return 0

Player/proc/RemasterMoodsTick()
	if(!rm_moods_on) return
	if(world.time < remaster_mood_at) return
	remaster_mood_at = world.time + RM_MOOD_EVERY
	for(var/mob/Monsters/M in UnitList) if(M.Owner == src && M.HP > 0 && !M.GoingToDie) M.RemasterMoodTick(src)

// --- Memories from events ---------------------------------------------------------
mob/Monsters/proc/RemasterAteThought(obj/Items/I, healthy)
	if(!istype(Owner, /Player)) return
	RemasterRoomMeal()
	var/st = lowertext("[I.icon_state] [I.name]")
	if(!healthy || findtext(st, "raw")) RemasterRemember("meal", "Ate raw food", -4, 1)
	else if(findtext(st, "cooked") || findtext(st, "stew") || findtext(st, "bread") || findtext(st, "pie") || findtext(st, "cheese"))
		RemasterRemember("meal", "Had a good meal", 8, 1)
	else RemasterRemember("meal", "Ate", 2, 1)

// Called once when a unit dies: everyone of its player nearby mourns, family more.
proc/RemasterMourn(mob/Monsters/D)
	if(!rm_moods_on) return   // moods off: nothing reads these memories, which would only pile up in the saves (the owner, 10-29:
	                          // "Yes, skip it"; reports/polish-night-1026/stump-ticks: 2.4 ms a death in a 500 v 500)
	if(D.remaster_mourned || !istype(D.Owner, /Player)) return
	D.remaster_mourned = 1
	var/Player/P = D.Owner
	var/who = D.RemasterBareName()
	for(var/mob/Monsters/M in P.UnitList) if(M != D && M.Owner == P && M.HP > 0)
		var/family = (D.remaster_uid && (M.remaster_father == D.remaster_uid || M.remaster_mother == D.remaster_uid)) || (M.remaster_uid && (D.remaster_father == M.remaster_uid || D.remaster_mother == M.remaster_uid))
		if(family) M.RemasterRemember("death:[D.remaster_uid]", "Lost family: [who]", -28, 3)
		else if(M.z == D.z && get_dist(M, D) <= 12) M.RemasterRemember("death:[D.remaster_uid]", "Saw [who] die", -16, 2)
		else M.RemasterRemember("deathheard", "Heard of a death", -5, 1)

// Good news for everyone of the player.
Player/proc/RemasterCheer(id, text, value, days = 2)
	for(var/mob/Monsters/M in UnitList) if(M.Owner == src && M.HP > 0) M.RemasterRemember(id, text, value, days)

Player/proc/RemasterMoodAverage()
	if(!rm_moods_on) return null
	var/n = 0
	var/s = 0
	for(var/mob/Monsters/M in UnitList) if(M.Owner == src && M.HP > 0)
		n++
		s += M.remaster_mood
	return n ? round(s / n) : null
