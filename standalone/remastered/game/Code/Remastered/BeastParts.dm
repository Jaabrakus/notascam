// What a dead great beast is butchered into (Remastered). TearMeat (Death.dm) cuts a body into
// its bones, meat, skull and glands; a dragon or a great spider gives more besides (pictures:
// art/enhance/beastparts32.py):
//   a dragon - scales in its own colour (the Dragonscale armour tier, at the Forge), its great bones (laid over
//   scales: the Dragonbone tier, at Bone crafting), teeth and
//   claws (the Dragonfang weapon tier, at Bone crafting), its heart (Dragon's Blood in a brew: the
//   Dragonheart Draught, Brewing.dm) and, grown, its wing hide (skin for any leatherwork);
//   a great spider - more chitin (the Chitin tier), its fangs (the Spiderfang tier) and a venom sac (a
//   poison gland: venom in a brew).
// Dragonscale keeps fire off - and Dragonbone, Dragonhide and the Dragonscale Robe, made of it: three pieces
// or more and the wearer can't be set alight, and each piece takes some of a fire's damage (Specials.dm
// RemasterBreathBurn).

obj/Items/Bones/DragonScales
	// its values: art/items/catalogue.json row bones.dragonscales (export_items.py writes ItemData.dm)

obj/Items/Bones/BeastFang   // teeth, claws and fangs: the Dragonfang and Spiderfang tiers' materials (Gear.dm)
	// its values: art/items/catalogue.json row bones.beastfang (export_items.py writes ItemData.dm)
	DragonTooth   // the Dragonfang tier's material ("dragon fang"): a tooth, or a claw
		// its values: art/items/catalogue.json row bones.beastfang.dragontooth (export_items.py writes ItemData.dm)
		DragonClaw
			// its values: art/items/catalogue.json row bones.beastfang.dragontooth.dragonclaw (export_items.py writes ItemData.dm)
	SpiderFang   // the Spiderfang tier's material ("spider fang")
		// its values: art/items/catalogue.json row bones.beastfang.spiderfang (export_items.py writes ItemData.dm)

obj/Items/Bones/Bones/DragonBones   // the Dragonbone tier's material; bones for anything else too
	// its values: art/items/catalogue.json row bones.bones.dragonbones (export_items.py writes ItemData.dm)

obj/Items/Bones/DragonHeart
	// its values: art/items/catalogue.json row bones.dragonheart (export_items.py writes ItemData.dm)

obj/Items/Skin/WingHide
	// its values: art/items/catalogue.json row skin.winghide (export_items.py writes ItemData.dm)

obj/Items/Glands/PoisonGland/VenomSac
	// its values: art/items/catalogue.json row glands.poisongland.venomsac (export_items.py writes ItemData.dm)

var/list/rm_dragon_colours = list("red"="Red", "red2"="Copper", "black"="Black", "ice"="White", "green"="Green",
	"sand"="Sand", "blue"="Blue", "zombie"="Rotting")

// Called from TearMeat as a body is cut up; the parts land where the body lay.
proc/RmButcherBeast(mob/Body/B)
	if(!B || !B.loc || (B.Race != "Dragon" && B.Race != "Spider")) return 0
	var/list/K = B.rm_beast
	var/size = (length(K) >= 3 && isnum(K[3])) ? K[3] : (B.Race == "Dragon" ? 2.4 : 1.4)
	var/grown = size >= 1.5
	var/atom/at = B.loc
	if(B.Race == "Dragon")
		var/v = (length(K) >= 2 && K[2]) ? K[2] : "red"
		for(var/i = 1, i <= 3 + round(size * 2), i++)
			var/obj/Items/Bones/DragonScales/S = new(at)
			S.icon_state = "scales-[v]"
			S.name = "[rm_dragon_colours[v] || "Dragon"] Dragon Scales"
		for(var/i = 1, i <= 1 + round(size), i++) new /obj/Items/Bones/BeastFang/DragonTooth(at)
		for(var/i = 1, i <= 1 + round(size * 1.3), i++) new /obj/Items/Bones/Bones/DragonBones(at)
		for(var/i = 1, i <= (grown ? 4 : 2), i++) new /obj/Items/Bones/BeastFang/DragonTooth/DragonClaw(at)
		if(grown)
			new /obj/Items/Bones/DragonHeart(at)
			for(var/i = 1, i <= 2, i++)
				var/obj/Items/Skin/WingHide/H = new(at)
				H.rm_colour = v
				H.name = "[rm_dragon_colours[v] || "Dragon"] Dragon Wing Hide"
	else
		for(var/i = 1, i <= round(size * 1.5), i++)
			var/obj/Items/Bones/Shell/C = new(at)
			C.name = "Spider Chitin"
		new /obj/Items/Bones/BeastFang/SpiderFang(at)
		new /obj/Items/Bones/BeastFang/SpiderFang(at)
		if(size >= 1.2) new /obj/Items/Glands/PoisonGland/VenomSac(at)
	return 1

// --- Beast weapons ------------------------------------------------------------------------
// What a great beast's weapon does when it hits (Hits.dm RemasterStrike): a Dragonfang blade or a Dragon
// Skull Staff now and then sets the target alight; a Spiderfang blade's venom gets into the wound; a
// Dragonbone weapon's weight can stagger; a Spider Staff can bind the target in silk for 3 s.
proc/RmHeldWeapon(mob/M)
	for(var/obj/Items/Equipment/Weapon/W in M) if(W.suffix == "(Equipped)") return W
	return null

mob/proc/RmWeaponEffect(mob/Monsters/M, d = 0)
	if(!istype(M) || M.HP <= 0 || M.GoingToDie) return
	var/obj/Items/Equipment/W = RmHeldWeapon(src)
	if(!W || !W.rm_gear) return
	if(copytext(W.rm_gear, 1, 7) == "magic.")
		if(istype(src, /mob/Monsters)) src:RmPassiveMoves(M, d)   // the staffs and enchanted weapons: their passives, from their mana (WeaponSkills.dm)
		return
	if(W.rm_group == "dragonfang")
		if(prob(15) && !RmFireproof(M) && !M.OnFire)
			M.Fire()
			RemasterHit(M, 0, "burn", src)
	else if(W.rm_group == "spiderfang")
		if(prob(50) && !M.ImmunePoison && !M.Undead)
			M.BloodContent -= 6
			M.rm_poison = min(40, M.rm_poison + 4)
			M.rm_poison_sick = 1
			M.rm_poison_kind = "spider venom"
			RemasterHit(M, 0, "venom", src)
	else if(W.rm_group == "dragonbone")
		if(prob(15) && !M.Stunned)
			M.Stunned = 1
			spawn(15) if(M) M.Stunned = 0
			RemasterHit(M, 0, "stagger", src)

// How far a bow shoots (Combat - Bows.dm BowTarget, Attack.dm, Defense.dm, Formations.dm). The user's last word
// (2026-10-23): "5 6 7 7 and if you have max or meet a ranged requirement then you unlock an extra tile or plus 1",
// "dragonbone is 7", "the Elf bow 7, the same as metal and Dragonbone": a bone bow 5, a wooden bow 6, metal, the forged
// tiers, Dragonbone and Elf bows 7; one tile more for an archer at Ranged level 60 (RM_BOW_REACH_RANGED), or with its
// Bow skill at the top level (120).
// The original's bows all shot 5.
#define RM_BOW_REACH_RANGED 60
proc/RmBowRange(mob/M)
	var/obj/Items/Equipment/W = RmHeldWeapon(M)
	. = 6                                              // no bow item in hand: as a wooden bow
	if(W)
		if(W.rm_group == "dragonbone" || W.rm_gear == "weapon.bow.dragonbone") . = 7   // a rare bone
		else if(istype(W, /obj/Items/Equipment/Weapon/Bows/BoneBow)) . = 5            // bone is easy to come by
		else if(istype(W, /obj/Items/Equipment/Weapon/Bows/ElfBow)) . = 7
		else if(istype(W, /obj/Items/Equipment/Weapon/Bows/WoodenBow)) . = 6
		else . = 7                                     // metal and the forged tiers
	if(RmBowReachBonus(M)) .++

// The extra tile: Ranged at RM_BOW_REACH_RANGED, or the Bow skill at the skills' top level (Skills.dm RM_SKILL_MAX_LEVEL).
proc/RmBowReachBonus(mob/M)
	return RemasterCombatLevel(M, "Ranged") >= RM_BOW_REACH_RANGED || RemasterCombatLevel(M, "Bow") >= 120

// --- Dragonscale and the Dragonheart Draught against fire ---------------------------------
mob/var/tmp/rm_fireproof_until = 0   // a Dragonheart Draught (Brewing.dm)

proc/RmDragonscaleWorn(mob/M)
	. = 0
	for(var/obj/Items/Equipment/E in M) if(E.suffix == "(Equipped)" && ((E.rm_group in list("dragon", "dragonbone", "dragonhide")) || E.rm_gear == "chest.robe.dragonrobe")) .++

// Can't be set alight (Verbs.dm Fire).
proc/RmFireproof(mob/M)
	if(!istype(M)) return 0
	var/obj/Items/Equipment/W = RmHeldWeapon(M)
	return M.rm_fireproof_until > world.time || RmDragonscaleWorn(M) >= 3 || (W && W.rm_gear == "magic.dragon staff")

// A fire's damage to M: each piece of dragonscale takes 15% of it (at most 75%); the draught half.
proc/RmFireDamage(mob/M, dmg)
	var/k = max(0.25, 1 - 0.15 * RmDragonscaleWorn(M))
	if(M.rm_fireproof_until > world.time) k *= 0.5
	return dmg * k

// --- Gear in its dragon's colour ------------------------------------------------------------
// Gear made from a dragon's scales or wing hide takes that dragon's colour (rm_colour, saved): its
// 3D picture is drawn red (art/enhance/wearables64.py) and RmGear64 swaps the reds for the dragon's.
obj/Items/var/rm_colour

// Each colour's scale ramp, darkest first (art/enhance/beastparts32.py SCALES).
var/list/rm_scale_ramps = list(
	"red2"=list(52,16,6, 120,40,14, 176,72,22, 218,116,40, 250,186,96),
	"black"=list(8,8,12, 28,26,36, 48,44,60, 76,70,94, 132,124,156),
	"ice"=list(40,64,92, 96,148,190, 148,200,232, 196,232,250, 250,255,255),
	"green"=list(10,30,12, 30,74,30, 52,112,46, 86,152,70, 156,206,120),
	"sand"=list(60,42,18, 132,100,54, 184,152,96, 220,194,138, 250,236,192),
	"blue"=list(10,18,46, 24,48,110, 40,80,160, 72,120,204, 140,182,240),
	"zombie"=list(30,36,26, 70,82,60, 108,122,92, 146,158,120, 196,204,164))

// The red ramps the pictures use, each with how dark it is beside the scales: dragonscale, dragon
// hide (wearables64.py "dragon", "dragonhide") and the Dragonscale Robe's cloth.
var/list/rm_red_ramps = list(
	list(1.0, "#220806", "#5c1610", "#902a1a", "#c0522a", "#f2a860"),
	list(0.78, "#1c0806", "#481610", "#70261a", "#963e28", "#c46848"),
	list(0.9, "#280608", "#641214", "#961e1e", "#bc362e", "#de6454"))

// The colour the parts a unit is about to use give what it makes: its scales', else its hide's.
proc/RmPartsColour(mob/M, list/R)
	if(R["dragon scales"]) for(var/obj/Items/Bones/DragonScales/S in RmGearCarried(M, /obj/Items/Bones/DragonScales))
		return copytext(S.icon_state, 8)
	if(R["wing hide"]) for(var/obj/Items/Skin/WingHide/H in RmGearCarried(M, /obj/Items/Skin/WingHide))
		return H.rm_colour
	return null

proc/RmGiveColour(obj/Items/I, colour)
	if(!colour || colour == "red" || !rm_scale_ramps[colour]) return
	I.rm_colour = colour
	I.name = "[rm_dragon_colours[colour]] [I.name]"

// A gear picture (list(file, state)) in a dragon colour: the whole sheet recoloured once and kept.
// Its third item keys it for the 3D view, its fourth is the sheet it came from (frame counts).
var/list/rm_tinted64 = list()
proc/RmDragonTint(list/P, colour)
	var/list/C = rm_scale_ramps[colour]
	if(!C) return P
	var/key = "[P[1]]#[colour]"
	var/icon/I = rm_tinted64[key]
	if(!I)
		I = icon(P[1])
		for(var/list/F in rm_red_ramps)
			var/k = F[1]
			for(var/j = 1, j <= 5, j++)
				var/b = (j - 1) * 3
				I.SwapColor(F[j + 1], rgb(round(C[b + 1] * k), round(C[b + 2] * k), round(C[b + 3] * k)))
		rm_tinted64[key] = I
	return list(I, P[2], key, P[1])
