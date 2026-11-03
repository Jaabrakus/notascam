#!/usr/bin/env python3
"""The wearables catalogue: a name, a recipe and level requirements for every
weapon, armour piece and magic item that wearables64.py draws.

    python3 standalone/remastered/art/enhance/catalogue.py

Writes planning/WEARABLES.md (rules and tables to read) and
art/enhance/catalogue.json (every item, for wiring into the game later).

Built on the game's own systems (game/Code, read only):
  * workshops and skills: Forge = Smithing (MetalCraftingSkill), Leatherworks =
    Leatherwork, Bone crafting = Bone craft (bones, skulls, shell), Carpentry =
    Woodwork, Gem cutter = Gem cutting (JewlCraftingSkill);
  * materials: iron, silver, gold and adamantium ingots, wood, skin, bones, skull,
    shell, spider silk, cut diamond / ruby / emerald, demon head, poison gland;
  * levels are the Remastered RuneScape-style skill levels (1-99): crafting needs the
    workshop skill, using a thing needs its combat skill (Sword, Axe, Mace, Spear,
    Dagger, Shield, Armour) or magic school (Astral, Chaos, Destruction, Holy,
    Necromancy); quality still comes from the crafting skill as the Forge does it;
  * race rules the Forge already has: adamantium is dwarf work, goblins and kobolds
    do not work gold or silver, orcs do not forge straight swords, kobolds do not
    set diamonds; hell-forged gear backfires on anyone under its level who is not a
    demon (ForceEquipItem's existing rule).
"""

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
REMASTERED = os.path.dirname(os.path.dirname(HERE))

# tier -> name, workshop, crafting skill, craft level, use level, main material,
# extra per item, defence (a chestplate at Quality) and damage (a sword at Quality),
# who cannot make it
TIERS = {
    "wood": dict(name="Wooden", station="Carpentry", skill="Woodwork", craft=1, use=1, mat="wood", wt=0.5,
                 defence=6, damage=(8, 12), note="Training and village gear."),
    "leather": dict(name="Leather", station="Leatherworks", skill="Leatherwork", craft=1, use=1, mat="skin", wt=0.4,
                    defence=7, damage=None, note="Light; no penalty to sneaking."),
    "bone": dict(name="Bone", station="Bone crafting", skill="Bone craft", craft=5, use=5, mat="bones", wt=0.8,
                 defence=8, damage=(15, 25), note="Wild damage spread, as the game's bone weapons."),
    "iron": dict(name="Iron", station="Forge", skill="Smithing", craft=10, use=10, mat="iron ingot", wt=1.0,
                 defence=12, damage=(20, 24), note="The standard metal."),
    "chitin": dict(name="Chitin", station="Bone crafting", skill="Bone craft", craft=20, use=20, mat="shell", wt=0.7,
                   defence=13, damage=(20, 28), note="Spider and beetle shell: light for its strength."),
    "silver": dict(name="Silver", station="Forge", skill="Smithing", craft=25, use=30, mat="silver ingot", wt=1.0,
                   defence=12, damage=(18, 22), deny=["Goblin", "Kobold"],
                   note="Silver: extra damage to undead and vampires (the game's Silver flag)."),
    "gold": dict(name="Gold", station="Forge", skill="Smithing", craft=35, use=40, mat="gold ingot", wt=1.3,
                 defence=13, damage=(22, 26), deny=["Goblin", "Kobold"], note="Heavy; worn by chiefs and kings: +morale nearby."),
    "adamantium": dict(name="Adamantium", station="Forge", skill="Smithing", craft=50, use=50, mat="adamantium ingot", wt=0.8,
                       defence=18.5, damage=(30, 40), only=["Dwarf"], note="Dwarf-forged, always Legendary Quality."),
    "diamond": dict(name="Diamond", station="Forge, then Gem cutter", skill="Smithing", craft=60, use=60, mat="silver ingot",
                    extra=[("cut diamond", 1)], second=("Gem cutting", 40), defence=19, damage=(32, 40), wt=1.0,
                    deny=["Goblin", "Kobold"], note="Silver set with cut diamonds."),
    "hell": dict(name="Hellforged", station="Forge beside lava", skill="Smithing", craft=70, use=70, mat="adamantium ingot",
                 extra=[("demon head", 1)], second=("Magic", 30), defence=21, damage=(40, 55), wt=1.1,
                 note="Backfires on anyone under its level who is not a demon or half-demon."),
    # from great beasts (BeastParts.dm): what a dead dragon or great spider is butchered into
    "dragon": dict(name="Dragonscale", station="Forge", skill="Smithing", craft=45, use=55, mat="dragon scales", wt=0.7,
                   defence=20, damage=None, note="Dragon scales riveted on hide: light, and fire hardly takes the wearer."),
    "dragonfang": dict(name="Dragonfang", station="Bone crafting", skill="Bone craft", craft=45, use=50, mat="dragon fang", wt=0.6,
                       defence=0, damage=(36, 46), note="A dragon's teeth and claws: keen, and its cuts sometimes catch fire."),
    "spiderfang": dict(name="Spiderfang", station="Bone crafting", skill="Bone craft", craft=35, use=40, mat="spider fang", wt=0.5,
                       defence=0, damage=(30, 40), note="A great spider's fangs, barbed: their cuts carry its venom."),
    "dragonbone": dict(name="Dragonbone", station="Bone crafting", skill="Bone craft", craft=50, use=60, mat="dragon bones",
                       extra=[("dragon scales", 1)], wt=0.85, defence=21, damage=(40, 52),
                       note="A dragon's bones laid over its scales: as strong as hellforged, and fire hardly takes the wearer."),
    # the beasts' light versions, at the Leatherworks: no penalty to sneaking
    "dragonhide": dict(name="Dragonhide", station="Leatherworks", skill="Leatherwork", craft=35, use=40, mat="wing hide", wt=0.4,
                       defence=16, damage=None, note="A dragon's wing hide: light, and fire hardly takes the wearer."),
    "spidersilk": dict(name="Spidersilk", station="Leatherworks", skill="Leatherwork", craft=25, use=30, mat="spider silk",
                       extra=[("shell", 1)], wt=0.35, defence=14, damage=None, note="Woven spider silk set with chitin: light and quiet."),
    "bonehide": dict(name="Bonehide", station="Leatherworks", skill="Leatherwork", craft=40, use=45, mat="skin",
                     extra=[("dragon bones", 1)], wt=0.45, defence=18, damage=None, note="Hide studded with a dragon's bones."),
}

# style tables: (name, main material count, extras, level offset, stat factor, notes, weight at iron)
# Counts follow RuneScape's bar counts where there is one (platebody 5, chainbody 3,
# platelegs 3, full helm 2, med helm 1, kiteshield 3, sword 1, longsword 2, 2h 3).
HELMETS = {
    "kettle": ("Kettle Helm", 1, [], 0, 0.6, "The original Metal Helmet's shape.", 8),
    "nasal": ("Nasal Helm", 1, [], 0, 0.6, "", 8),
    "horned": ("Horned Helm", 2, [("bones", 1)], 2, 0.62, "Horns of bone on any metal.", 10),
    "winged": ("Winged Helm", 2, [("spider silk", 1)], 3, 0.62, "", 9),
    "great helm": ("Great Helm", 2, [], 5, 0.75, "Closed face: -1 sight range.", 12),
    "crested": ("Crested Helm", 2, [("skin", 1)], 3, 0.66, "A plume: +morale for units nearby.", 10),
}
CHESTS = {
    "plate": ("Breastplate", 5, [("skin", 1)], 5, 1.0, "", 35),
    "banded": ("Banded Mail", 5, [("skin", 1)], 5, 1.08, "Dwarven: only dwarves can make it.", 40),
    "mail": ("Chainmail", 3, [], 0, 0.85, "", 25),
    "scale": ("Scale Hauberk", 4, [("skin", 1)], 3, 0.92, "", 30),
    "lamellar": ("Lamellar Coat", 4, [("skin", 1)], 3, 0.9, "", 28),
    "brigandine": ("Brigandine", 3, [("spider silk", 2)], 2, 0.85, "", 22),
    "tabard": ("Mail and Tabard", 3, [("spider silk", 1)], 1, 0.87, "Shows the owner's colours.", 26),
    "leather": ("Jerkin", 3, [("iron ingot", 1)], 0, 0.5, "Leather only.", 10),
}
LEGS = {
    "plate": ("Greaves", 3, [("skin", 1)], 5, 0.8, "", 25),
    "mail": ("Chausses", 2, [("skin", 1)], 0, 0.68, "", 18),
    "scale": ("Scale Tassets", 3, [("skin", 1)], 3, 0.72, "", 20),
    "leather": ("Breeches", 2, [], 0, 0.4, "Leather only.", 6),
}
ARMS = {   # one item per arm, as the game's LeftArm / RightArm
    "plate": ("Vambrace", 1, [("skin", 1)], 3, 0.4, "", 6),
    "mail": ("Mail Sleeve", 1, [], 0, 0.32, "", 4),
    "leather": ("Bracer", 1, [], 0, 0.2, "Leather only.", 2),
}
SHIELDS = {
    "buckler": ("Buckler", 1, [], -3, 0.45, "Parries: suits daggers and swords.", 10),
    "round": ("Round Shield", 1, [("wood", 2)], 0, 0.7, "Planks with a rim and boss of the tier's metal.", 18),
    "heater": ("Heater Shield", 2, [("wood", 1)], 3, 0.78, "", 22),
    "kite": ("Kite Shield", 3, [("wood", 1)], 5, 0.8, "Covers the legs too.", 28),
    "tower": ("Tower Shield", 3, [("wood", 3)], 5, 0.95, "Slows the bearer; blocks arrows best.", 40),
}
# weapons: (name, count, extras, offset, damage factor, skill, hands, notes, weight at iron)
WEAPONS = {
    "dagger": ("Dagger", 1, [("skin", 1)], -3, 0.6, "Dagger", 1, "Fast; sneak attacks.", 10),
    "arming sword": ("Sword", 1, [("skin", 1)], 0, 1.0, "Sword", 1, "", 25),
    "longsword": ("Longsword", 2, [("skin", 1)], 5, 1.15, "Sword", 1, "Hand-and-a-half.", 30),
    "scimitar": ("Scimitar", 2, [("skin", 1)], 0, 0.95, "Sword", 1, "Cuts cause bleeding. Orcs and goblins favour it.", 25),
    "hand axe": ("Hand Axe", 1, [("wood", 1)], 0, 1.0, "Axe", 1, "Also fells trees.", 20),
    "battle axe": ("Battle Axe", 3, [("wood", 1)], 5, 1.3, "Axe", 2, "Two-handed: no shield.", 40),
    "warhammer": ("Warhammer", 3, [("wood", 1)], 5, 1.2, "Mace", 1, "Ignores part of the target's armour.", 35),
    "mace": ("Mace", 1, [("wood", 1)], 0, 1.05, "Mace", 1, "", 25),
    "morning star": ("Morning Star", 2, [("wood", 1)], 3, 1.12, "Mace", 1, "", 28),
    "spear": ("Spear", 1, [("wood", 2)], 0, 1.0, "Spear", 1, "Reach: strikes from behind a friend.", 20),
    "halberd": ("Halberd", 2, [("wood", 2)], 5, 1.35, "Spear", 2, "Two-handed: no shield. Reach.", 40),
    "pickaxe": ("Pickaxe", 2, [("wood", 1)], 0, 0.8, "Mining", 2, "A tool: its level is the Mining level it needs.", 30),
    "bow": ("Bow", 2, [("spider silk", 1)], 3, 1.0, "Bow", 2, "Shoots arrows from further off than the game's bows (7 tiles).", 15),
}

# which styles each tier can be made in
ALLOW = {
    "wood": dict(helmet=["kettle"], chest=["plate"], legs=["plate"], arms=["plate"], shield=["buckler", "round", "kite", "heater", "tower"],
                 weapon=["arming sword", "hand axe", "mace", "spear"]),
    "leather": dict(helmet=["kettle"], chest=["leather"], legs=["leather"], arms=["leather"], shield=["buckler", "round"], weapon=[]),
    "bone": dict(helmet=["kettle", "horned", "crested"], chest=["plate", "scale", "lamellar"], legs=["plate", "scale"], arms=["plate"],
                 shield=["buckler", "round", "kite"], weapon=["dagger", "arming sword", "scimitar", "hand axe", "mace", "spear", "halberd"]),
    "chitin": dict(helmet=["kettle", "horned", "crested", "great helm"], chest=["plate", "scale", "lamellar"], legs=["plate", "scale"],
                   arms=["plate"], shield=["buckler", "round", "kite", "heater"],
                   weapon=["dagger", "arming sword", "scimitar", "hand axe", "battle axe", "mace", "spear", "halberd"]),
}
ALLOW["dragon"] = dict(helmet=["kettle", "horned", "crested", "great helm"], chest=["scale", "lamellar", "plate"], legs=["scale", "plate"],
                       arms=["plate"], shield=["round", "kite", "heater"], weapon=[])
ALLOW["dragonbone"] = dict(helmet=["kettle", "horned", "great helm"], chest=["plate", "lamellar"], legs=["plate"], arms=["plate"],
                           shield=["round", "kite"], weapon=["longsword", "battle axe", "warhammer", "halberd", "bow"])
for t in ("dragonhide", "spidersilk", "bonehide"):
    ALLOW[t] = dict(helmet=["kettle"], chest=["leather"], legs=["leather"], arms=["leather"], shield=[], weapon=[])
ALLOW["dragonfang"] = dict(helmet=[], chest=[], legs=[], arms=[], shield=[],
                           weapon=["dagger", "arming sword", "longsword", "scimitar", "hand axe", "battle axe", "spear", "halberd"])
ALLOW["spiderfang"] = dict(helmet=[], chest=[], legs=[], arms=[], shield=[], weapon=["dagger", "arming sword", "scimitar", "spear"])
METAL = dict(helmet=list(HELMETS), chest=[c for c in CHESTS if c != "leather"], legs=[l for l in LEGS if l != "leather"],
             arms=[a for a in ARMS if a != "leather"], shield=list(SHIELDS), weapon=list(WEAPONS))
for t in ("iron", "silver", "gold", "adamantium", "diamond", "hell"):
    ALLOW[t] = METAL
ALLOW["diamond"] = dict(METAL, weapon=[w for w in WEAPONS if w != "pickaxe"])

# names that read better than tier + style
SPECIAL_NAMES = {("helmet", "kettle", "leather"): "Leather Cap", ("chest", "leather", "leather"): "Studded Leather Jerkin",
                 ("legs", "leather", "leather"): "Leather Breeches", ("arms", "leather", "leather"): "Leather Bracer",
                 ("chest", "plate", "wood"): "Wooden Chestplate", ("helmet", "kettle", "wood"): "Wooden Helmet",
                 ("helmet", "kettle", "bone"): "Skull Helm", ("weapon", "mace", "wood"): "Wooden Club",
                 ("weapon", "mace", "bone"): "Skull Mace",
                 ("chest", "scale", "dragon"): "Dragonscale Hauberk", ("legs", "scale", "dragon"): "Dragonscale Tassets",
                 ("chest", "lamellar", "dragon"): "Dragonscale Coat", ("helmet", "kettle", "dragon"): "Dragonscale Helm",
                 ("helmet", "horned", "dragon"): "Horned Dragon Helm", ("helmet", "great helm", "dragon"): "Dragon Great Helm",
                 ("helmet", "crested", "dragon"): "Crested Dragon Helm", ("weapon", "arming sword", "dragonfang"): "Dragonfang Sword",
                 ("weapon", "arming sword", "spiderfang"): "Spiderfang Sword",
                 ("helmet", "kettle", "dragonbone"): "Dragonbone Helm", ("helmet", "horned", "dragonbone"): "Horned Dragonbone Helm",
                 ("helmet", "great helm", "dragonbone"): "Dragon Skull Helm", ("chest", "plate", "dragonbone"): "Dragonbone Cuirass",
                 ("chest", "lamellar", "dragonbone"): "Dragonbone Lamellar", ("shield", "kite", "dragonbone"): "Dragon Skull Shield"}
for t, n in (("dragonhide", "Dragonhide"), ("spidersilk", "Spidersilk"), ("bonehide", "Bonehide")):
    SPECIAL_NAMES.update({("helmet", "kettle", t): f"{n} Cap", ("chest", "leather", t): f"{n} Jerkin",
                          ("legs", "leather", t): f"{n} Breeches", ("arms", "leather", t): f"{n} Bracer"})

# clothes and magic
# Plain robes are the game's own (black, red, white from spider silk; brown added).
# School robes: a cut stone or relic woven in, worn for +10% spell power in that school.
ROBES = {
    "black": ("Black Robe", [("spider silk", 3)], None, ""),
    "red": ("Red Robe", [("spider silk", 3)], None, ""),
    "white": ("White Robe", [("spider silk", 3)], None, ""),
    "brown": ("Plain Robe", [("spider silk", 2), ("skin", 1)], None, ""),
    "blue": ("Astral Robe", [("spider silk", 3), ("cut diamond", 1)], ("Astral", 10), "+10% Astral spell power."),
    "purple": ("Chaos Robe", [("spider silk", 3), ("toxic gland", 1)], ("Chaos", 10), "+10% Chaos spell power."),
    "crimson": ("Robe of Flames", [("spider silk", 3), ("cut ruby", 1)], ("Destruction", 10), "+10% Destruction spell power."),
    "gold": ("Priest's Robe", [("spider silk", 3), ("gold ingot", 1)], ("Holy", 10), "+10% Holy spell power."),
    "green": ("Druid's Robe", [("spider silk", 3), ("cut emerald", 1)], ("Holy", 10), "+10% healing; nature staffs."),
    "grey": ("Necromancer's Robe", [("spider silk", 3), ("skull", 1)], ("Necromancy", 10), "+10% Necromancy spell power."),
    # the great beasts' robes (BeastParts.dm)
    "dragonrobe": ("Dragonscale Robe", [("spider silk", 3), ("dragon scales", 2)], ("Destruction", 10),
                   "+10% Destruction spell power; scaled at the shoulders: fire hardly takes the wearer."),
    "spiderrobe": ("Spider Silk Robe", [("spider silk", 4), ("poison gland", 1)], ("Chaos", 10), "+10% Chaos spell power; a great spider's silk."),
    "bonerobe": ("Dragonbone Robe", [("spider silk", 3), ("dragon bones", 1)], ("Necromancy", 10), "+10% Necromancy spell power; a dragon's bones for a mantle."),
}
CLOTH = {
    "cloth": ("Padded Trousers", [("spider silk", 2), ("skin", 1)], "Leatherworks", "Leatherwork", 3, "", 6),
    "boots": ("Boots", [("skin", 1)], "Leatherworks", "Leatherwork", 1, "", 3),
}
STAFFS = {   # name, recipe, station, craft (skill, level), extra craft (skill, level), school and level, effect
    "crystal staff": ("Crystal Staff", [("wood", 2), ("silver ingot", 1), ("cut diamond", 1)], "Carpentry", ("Woodwork", 25), ("Gem cutting", 25),
                      ("Astral", 25), "A quarter of the mana its bearer spends comes back; the crystal lights the way at night."),
    "orb staff": ("Orb Staff", [("wood", 2), ("gold ingot", 1), ("cut ruby", 1)], "Carpentry", ("Woodwork", 35), ("Gem cutting", 30),
                  ("Chaos", 35), "Its bearer's race special now and then strikes twice."),
    "skull staff": ("Skull Staff", [("wood", 2), ("skull", 1), ("poison gland", 1)], "Carpentry", ("Woodwork", 15), None,
                    ("Necromancy", 15), "Raises skeletons, as the game's Necromancer's Staff."),
    "flame staff": ("Flame Staff", [("wood", 2), ("iron ingot", 1), ("cut ruby", 1)], "Carpentry", ("Woodwork", 25), ("Gem cutting", 25),
                    ("Destruction", 25), "Its bearer's fire always sets alight what it touches; its blows can too."),
    "nature staff": ("Nature Staff", [("wood", 3), ("cut emerald", 1)], "Carpentry", ("Woodwork", 10), ("Gem cutting", 15),
                     ("Holy", 10), "Its bearer's people close by heal faster, and crops near it ripen faster."),
    # the great beasts' staffs (BeastParts.dm): their blows carry the beast (Hits.dm RmWeaponEffect)
    "dragon staff": ("Dragon Skull Staff", [("wood", 2), ("dragon bones", 1), ("dragon scales", 1)], "Carpentry", ("Woodwork", 30), None,
                     ("Destruction", 30), "Its blows can set the target alight, and its bearer can't be set alight."),
    "spider staff": ("Spider Staff", [("wood", 2), ("spider fang", 2), ("spider silk", 2)], "Carpentry", ("Woodwork", 25), None,
                     ("Chaos", 25), "Its blows can bind the target in silk, held fast for 3 s."),
}
# enchanted weapons: base weapon (style, tier), reagents, mana, school and level, effect
ENCHANTED = {
    "rune sword": ("Runeblade", ("longsword", "iron"), [("cut diamond", 1)], 40, ("Astral", 25), "Each hit adds Astral damage."),
    "flame sword": ("Flametongue", ("arming sword", "iron"), [("cut ruby", 1)], 40, ("Destruction", 25), "Sets the target alight."),
    "frost axe": ("Frostbite Axe", ("battle axe", "silver"), [("cut diamond", 1)], 50, ("Astral", 35), "Hits slow the target."),
    "storm spear": ("Stormcaller Spear", ("spear", "silver"), [("cut emerald", 1)], 50, ("Destruction", 35), "Lightning jumps to a second enemy."),
    "void blade": ("Voidedge", ("scimitar", "adamantium"), [("demon head", 1)], 70, ("Chaos", 45), "Drinks the life it spills."),
    "holy mace": ("Dawnbringer", ("mace", "gold"), [("cut diamond", 1), ("skull", 1)], 60, ("Holy", 40), "Double damage to undead and demons."),
}

CHANGES = [
    "**Gentler levels.** Training slows by half every 10 levels (Skills.dm), so the top tiers sat almost out of reach "
    "(hellforged needed 85-95) and new units, who start every skill at 1, could not use iron (Sword 20). Now, to use: "
    "wood and leather 1, bone 5, iron 10, chitin 20, silver 30, gold 40, adamantium 50, diamond 60, hellforged 70.",
    "**Smaller style steps.** Heavy styles add at most +5 (they reached +10); light ones take off 3.",
    "**RuneScape bar counts.** A sword is 1 bar, a longsword 2, chainmail 3, platelegs 3, a breastplate 5, a kite shield 3, "
    "a nasal or kettle helm 1, a great helm 2.",
    "**Two-handed weapons take both hands.** Battle axes, halberds, pickaxes and staffs leave no hand for a shield; the "
    "kits drawn so far are changed to match (the orc and the frogman put their shields away).",
    "**Weights**, scaled from the game's own (an iron sword 25, a dagger 10): heavier styles and gold weigh more, "
    "chitin and adamantium less.",
    "**School robes.** The game's black, red and white silk robes stay as they are. New robes weave in a stone or relic and "
    "give +10% spell power in one school: Astral (diamond), Chaos (toxic gland), Flames (ruby), Priest's (gold), "
    "Druid's (emerald), Necromancer's (skull).",
    "**Wield checks use the Remastered combat levels** (Attack, Defence, Magic; Mining for pickaxes), as RuneScape does. "
    "The old magic schools (Astral, Chaos, Destruction, Holy) never train in the game, so they are flavour names only; "
    "staffs and enchanted weapons ask for Magic 5-30.",
    "**Names.** Studded Leather Jerkin, Leather Breeches, Leather Bracer, Skull Helm (bone, made with a skull as the game's "
    "bone helmet is), Wooden Club, Skull Mace, \"Diamond\" in place of \"Diamond-set\", Banded Mail without the race in the "
    "name. Wooden weapons are all wood.",
]

# Magic levels for staffs and enchanted weapons. The Remastered Magic level trains on race
# specials (CombatSkills.dm), so these stay within reach; the school names are flavour.
MAGIC_LEVEL = {"dragon staff": 20, "spider staff": 15, "nature staff": 5, "skull staff": 10, "crystal staff": 15, "flame staff": 15, "orb staff": 20,
               "rune sword": 15, "flame sword": 15, "frost axe": 20, "storm spear": 20, "holy mace": 25, "void blade": 30}

QUALITY = "Poor <=20, Average <=30, Quality <=40, Impressive <=50, Grand <=60, Masterful <=75, Epic <=90, Legendary 100+ (the Forge's own rule)"


def clamp(v):
    return max(1, min(99, v))


def recipe(tier, count, extras):
    T = TIERS[tier]
    mats = [(T["mat"], count)] + list(T.get("extra", [])) + list(extras)
    merged = {}
    for m, n in mats:
        merged[m] = merged.get(m, 0) + n
    return [{"material": m, "count": n} for m, n in merged.items()]


def who(tier, style=None):
    T = TIERS[tier]
    out = {}
    if T.get("only"):
        out["only"] = T["only"]
    if T.get("deny"):
        out["not"] = list(T["deny"])
    if style == "banded":
        out["only"] = ["Dwarf"]
    if style in ("arming sword", "longsword") and tier in ("iron", "silver", "gold", "adamantium", "diamond", "hell"):
        out["not"] = sorted(set(out.get("not", []) + ["Orc"]))
    if tier == "diamond":
        out["not"] = sorted(set(out.get("not", []) + ["Kobold"]))
    return out


def armour_items():
    items = []
    slots = (("helmet", HELMETS, "Helmet"), ("chest", CHESTS, "Chestplate"), ("legs", LEGS, "Leggings"),
             ("arms", ARMS, "LeftArm/RightArm"), ("shield", SHIELDS, "Shield"))
    for tier, T in TIERS.items():
        for slot, table, item_type in slots:
            for style in ALLOW[tier][slot]:
                name, count, extras, off, factor, note, wt = table[style]
                full = SPECIAL_NAMES.get((slot, style, tier), f"{T['name']} {name}")
                skill = "Defence"   # armour and shields: the Remastered Defence level
                if tier == "bone" and slot == "helmet":   # as the game's BoneHelmet: a skull for the crown
                    extras = list(extras) + [("skull", 1)]
                items.append(dict(id=f"{slot}.{style}.{tier}", name=full, slot=slot, item_type=item_type, style=style, tier=tier,
                                  station=T["station"], craft={"skill": T["skill"], "level": clamp(T["craft"] + off)},
                                  craft2=({"skill": T["second"][0], "level": T["second"][1]} if T.get("second") else None),
                                  recipe=recipe(tier, count, extras), use={"skill": skill, "level": clamp(T["use"] + off)},
                                  defence=round(T["defence"] * factor, 1), weight=round(wt * T["wt"]), who=who(tier, style),
                                  notes=" ".join(x for x in (note, T["note"] if tier in ("hell", "silver", "dragon", "dragonbone", "dragonhide", "spidersilk", "bonehide") else "") if x)))
    return items


def weapon_items():
    items = []
    for tier, T in TIERS.items():
        if not T["damage"]:
            continue
        for style in ALLOW[tier]["weapon"]:
            name, count, extras, off, factor, skill, hands, note, wt = WEAPONS[style]
            if tier == "wood":   # wooden weapons are all wood
                extras = [(m, n) for m, n in extras if m != "skin"]
            lo, hi = T["damage"]
            items.append(dict(id=f"weapon.{style}.{tier}", name=SPECIAL_NAMES.get(("weapon", style, tier), f"{T['name']} {name}"),
                              slot="weapon", item_type=skill if skill != "Mining" else "Pickaxe", weight=round(wt * T["wt"]),
                              style=style, tier=tier, station=T["station"], craft={"skill": T["skill"], "level": clamp(T["craft"] + off)},
                              craft2=({"skill": T["second"][0], "level": T["second"][1]} if T.get("second") else None),
                              recipe=recipe(tier, count, extras), use={"skill": "Mining" if skill == "Mining" else "Attack", "level": clamp(T["use"] + off)},
                              trains=skill, damage=[round(lo * factor), round(hi * factor)], hands=hands, who=who(tier, style),
                              notes=" ".join(x for x in (note, T["note"] if tier in ("hell", "silver", "bone", "dragonfang", "spiderfang", "dragonbone") else "") if x)))
    return items


def magic_items():
    items = []
    for c, (name, mats, school, note) in ROBES.items():
        items.append(dict(id=f"chest.robe.{c}", name=name, slot="chest", item_type="Chestplate", style="robe", tier=c,
                          station="Leatherworks", craft={"skill": "Leatherwork", "level": 5 if not school else 15},
                          recipe=[{"material": m, "count": n} for m, n in mats],
                          use={"skill": "Magic" if school else "Defence", "level": 5 if school else 1}, school=school[0] if school else None,
                          defence=1.5, weight=5, who={},
                          notes=note or "No defence to speak of; the game's own robe."))
    for key, (name, mats, station, skill, lvl, note, wt) in CLOTH.items():
        items.append(dict(id=f"legs.{key}", name=name, slot="legs", item_type="Leggings", style=key, tier="cloth", station=station,
                          craft={"skill": skill, "level": lvl}, recipe=[{"material": m, "count": n} for m, n in mats],
                          use={"skill": "Defence", "level": 1}, defence=1.0 if key == "cloth" else 0.5, weight=wt, who={}, notes=note))
    for key, (name, mats, station, craft, craft2, school, effect) in STAFFS.items():
        items.append(dict(id=f"magic.{key}", name=name, slot="weapon", item_type="Staff", style=key, tier="magic", station=station,
                          craft={"skill": craft[0], "level": craft[1]}, craft2=({"skill": craft2[0], "level": craft2[1]} if craft2 else None),
                          recipe=[{"material": m, "count": n} for m, n in mats], use={"skill": "Magic", "level": MAGIC_LEVEL[key]}, school=school[0],
                          damage=[10, 16], hands=2, weight=20, who={}, notes=effect + " Two-handed: no shield."))
    for key, (name, (bstyle, btier), reagents, mana, school, effect) in ENCHANTED.items():
        base = next(w for w in weapon_items() if w["id"] == f"weapon.{bstyle}.{btier}")
        items.append(dict(id=f"magic.{key}", name=name, slot="weapon", item_type=base["item_type"], style=key, tier="magic",
                          station="Gem cutter, beside a powered rune circuit", craft={"skill": "Magic", "level": MAGIC_LEVEL[key]}, school=school[0],
                          base=base["id"], base_name=base["name"], recipe=[{"material": base["name"], "count": 1}] +
                          [{"material": m, "count": n} for m, n in reagents] + [{"material": "mana", "count": mana}],
                          use={"skill": "Attack", "level": base["use"]["level"]}, use2={"skill": "Magic", "level": MAGIC_LEVEL[key]},
                          damage=[round(base["damage"][0] * 1.15), round(base["damage"][1] * 1.15)], hands=base["hands"], weight=base["weight"], who={},
                          notes=effect + f" Start from {'an' if base['name'][0] in 'AEIOU' else 'a'} {base['name']}" + (f" (made by: {', '.join(base['who'].get('only', []))})" if base["who"].get("only") else "") + "."))
    return items


# ---------------------------------------------------------------------------
# the document
# ---------------------------------------------------------------------------

def mats_text(rec):
    return ", ".join(f"{r['count']} {r['material']}" for r in rec)


def md(items):
    by = {}
    for it in items:
        by.setdefault(it["slot"], []).append(it)
    L = []
    w = L.append
    w("# Wearables: names, recipes and levels")
    w("")
    w("Generated by `art/enhance/catalogue.py` (edit the tables there and run it again); every item is also in "
      "`art/enhance/catalogue.json` for wiring into the game. Sprites: `art/enhance/wearables64.py`. Status: proposal, not in the game yet.")
    w("")
    w("## Changes in this revision")
    w("")
    for c in CHANGES:
        w(f"- {c}")
    w("")
    w("## How it works")
    w("")
    w("- **Made where the game already makes gear.** Forge (Smithing), Leatherworks (Leatherwork), Bone crafting (Bone craft), "
      "Carpentry (Woodwork), Gem cutter (Gem cutting). Enchanted weapons are finished on a powered rune circuit (Runes.dm), "
      "which pays the enchantment's mana from its crystals.")
    w("- **Two levels per item.** *Craft*: the workshop skill needed to make it. *Use*: the Remastered combat level needed to "
      "wield or wear it (CombatSkills.dm): Attack for weapons, Defence for armour and shields, Magic for staffs and school robes, "
      "Mining for pickaxes; enchanted weapons need Attack and Magic. The weapon still trains its own sub-skill (Sword, Axe...). "
      "Levels are the Remastered skill levels (1-99).")
    w(f"- **Quality** still comes from the crafter's skill, as the Forge does it now: {QUALITY}. "
      "Damage and defence below are at Quality; better crafters make better copies of the same item.")
    w("- **Recipe = the tier's material x the style's count, plus extras** (grips are skin, hafts and shield boards are wood). "
      "The original recipes take one material each; these cost more so that heavy gear means mining and smelting.")
    w("- **Two hands.** Battle axes, halberds, pickaxes and staffs take both hands: no shield while one is held.")
    w("- **Weight** counts against what a unit can carry, as the game's item weights do (an iron sword is 25, as now).")
    w("- **Race rules** are the Forge's own: adamantium is dwarf work, goblins and kobolds do not work silver or gold, "
      "orcs do not forge straight swords, kobolds do not set diamonds. Banded mail is dwarven. Hell-forged gear backfires "
      "on anyone under its level who is not a demon or half-demon (the game's existing rule). Race rules limit who can *make* "
      "an item; anyone with the level can use it.")
    w("")
    w("## Tiers")
    w("")
    w("| Tier | Name | Workshop | Material | Craft | Use | Chest defence | Sword damage | Notes |")
    w("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for t, T in TIERS.items():
        extra = "".join(f" + {n} {m}" for m, n in T.get("extra", []))
        craft = f"{T['skill']} {T['craft']}" + (f", {T['second'][0]} {T['second'][1]}" if T.get("second") else "")
        rules = ""
        if T.get("only"):
            rules = " Only " + ", ".join(T["only"]) + "."
        if T.get("deny"):
            rules = " Not " + ", ".join(T["deny"]) + "."
        dmg = f"{T['damage'][0]}-{T['damage'][1]}" if T["damage"] else "-"
        w(f"| {t} | {T['name']} | {T['station']} | {T['mat']}{extra} | {craft} | {T['use']} | {T['defence']} | {dmg} | {T['note']}{rules} |")
    w("")
    w("A style adds to the tier's levels and changes its stats:")
    w("")
    for title, table, kind in (("Helmets", HELMETS, "a"), ("Chest", CHESTS, "a"), ("Legs", LEGS, "a"), ("Arms (one per arm)", ARMS, "a"),
                               ("Shields", SHIELDS, "a"), ("Weapons", WEAPONS, "w")):
        w(f"### {title}")
        w("")
        if kind == "a":
            w("| Style | Name | Material x | Extras | Levels | Defence | Weight (iron) | Notes |")
            w("| --- | --- | --- | --- | --- | --- | --- | --- |")
            for st, (name, count, extras, off, factor, note, wt) in table.items():
                ex = ", ".join(f"{n} {m}" for m, n in extras) or "-"
                w(f"| {st} | {name} | {count} | {ex} | {off:+d} | x{factor} | {wt} | {note} |")
        else:
            w("| Style | Name | Material x | Extras | Levels | Damage | Skill | Hands | Weight (iron) | Notes |")
            w("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
            for st, (name, count, extras, off, factor, skill, hands, note, wt) in table.items():
                ex = ", ".join(f"{n} {m}" for m, n in extras) or "-"
                w(f"| {st} | {name} | {count} | {ex} | {off:+d} | x{factor} | {skill} | {hands} | {wt} | {note} |")
        w("")
    w("## Every item")
    w("")
    order = [("weapon", "Weapons"), ("helmet", "Helmets"), ("chest", "Chest"), ("legs", "Legs"), ("arms", "Arms"), ("shield", "Shields")]
    for slot, title in order:
        rows = [it for it in by.get(slot, []) if it["tier"] not in ("magic",) and not it["id"].startswith("chest.robe")
                and it["tier"] != "cloth"]
        w(f"### {title}")
        w("")
        w(f"| Item | Made at | Recipe | Craft | Use | {'Damage' if slot == 'weapon' else 'Defence'} | Weight | Made by |")
        w("| --- | --- | --- | --- | --- | --- | --- | --- |")
        for it in rows:
            craft = f"{it['craft']['skill']} {it['craft']['level']}" + (f", {it['craft2']['skill']} {it['craft2']['level']}" if it.get("craft2") else "")
            stat = f"{it['damage'][0]}-{it['damage'][1]}" + (" (2H)" if it.get("hands") == 2 else "") if slot == "weapon" else f"{it['defence']}"
            whotxt = "; ".join(("only " if k == "only" else "not ") + ", ".join(v) for k, v in it["who"].items()) or "anyone"
            w(f"| {it['name']} | {it['station']} | {mats_text(it['recipe'])} | {craft} | {it['use']['skill']} {it['use']['level']} | {stat} | {it['weight']} | {whotxt} |")
        w("")
    w("## Cloth and robes")
    w("")
    w("| Item | Made at | Recipe | Craft | Use | Notes |")
    w("| --- | --- | --- | --- | --- | --- |")
    for it in items:
        if it["id"].startswith("chest.robe") or it["tier"] == "cloth":
            w(f"| {it['name']} | {it['station']} | {mats_text(it['recipe'])} | {it['craft']['skill']} {it['craft']['level']} | "
              f"{it['use']['skill']} {it['use']['level']} | {it['notes']} |")
    w("")
    w("## Magic")
    w("")
    w("Staffs are made at the Carpentry; their head needs the Gem cutter's cut stone. They are wielded with Magic, "
      "not a weapon skill. Enchanted weapons start as an ordinary weapon and are finished at a Gem cutter that stands beside "
      "a powered rune circuit (Runes.dm): the enchanter needs the Magic level and the circuit's crystals pay the mana.")
    w("")
    w("| Item | Made at | Recipe | Craft | Use | Damage | Effect |")
    w("| --- | --- | --- | --- | --- | --- | --- |")
    for it in items:
        if it["tier"] == "magic":
            craft = f"{it['craft']['skill']} {it['craft']['level']}" + (f", {it['craft2']['skill']} {it['craft2']['level']}" if it.get("craft2") else "")
            use = f"{it['use']['skill']} {it['use']['level']}" + (f", {it['use2']['skill']} {it['use2']['level']}" if it.get("use2") else "")
            w(f"| {it['name']} | {it['station']} | {mats_text(it['recipe'])} | {craft} | {use} | {it['damage'][0]}-{it['damage'][1]} | {it['notes']} |")
    w("")
    return "\n".join(L)


def main():
    items = weapon_items() + armour_items() + magic_items()
    with open(os.path.join(HERE, "catalogue.json"), "w") as fh:
        json.dump({"tiers": TIERS, "quality": QUALITY, "items": items}, fh, indent=1)
    path = os.path.join(REMASTERED, "planning", "WEARABLES.md")
    with open(path, "w") as fh:
        fh.write(md(items))
    print(path, len(items), "items")


if __name__ == "__main__":
    main()
