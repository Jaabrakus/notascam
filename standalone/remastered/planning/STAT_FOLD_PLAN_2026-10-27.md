# Fold the old stats into the skills (combat-rules, 10-27; step 2 of the owner's "Fold old stats into skills")

The owner, 10-27 ~21:55: "Fold old stats into skills" (after "what the fuck do we have two different stats happening
with the same name?"): old Strength -> Strength skill, old Agility -> Attack skill, old Intelligence -> Magic skill.
Step 1 (screens): a new company's roll sets the four skills and the Character tab stops showing the old three.
This is step 2: every place the game still reads the old stats.

## What's there today

- 87 reads in 23 files, and the old stats are written in about 120 more places: race and NPC presets (Mobs.dm,
  Turfs.dm, Mob/Monster/*), level-ups, bonuses, inheritance.
- Today a unit's old Strength is its race roll plus 1-1.25 per character level (Leveling.dm, capped near 120).
  Agility grows the same way; Intelligence gains only 0.01-0.02 a level. At level 50 Strength is about 55-65, close
  to a Strength skill of 50. So a one-for-one swap keeps a unit whose character level and skills grew together where
  it is today.
- Combat already counts the skills on their own (CombatSkills.dm): Strength skill adds damage, and the Attack and
  Defence skills move dodge. The old stats are a second channel next to them, which is why the names collide.

## The design

**One number, plus bonuses.** For a player's unit, every read of an old stat reads `skill + bonus`:
- Strength = Strength skill + bonus; Agility = Attack skill + bonus; Intelligence = Magic skill + bonus.
- The bonus is whatever was added to the old stat after the unit's own roll: werewolf form +20, vampire +8, a crown
  +10 a point of influence, tonics, surgery. Code: the old stat minus a base taken once (`rm_stat_base_*`, saved).
  Every existing +20/-20 then works unchanged.
- Level-ups stop adding Strength and Agility (+1-1.25 a level) to these units: the skills grow by use instead.
- NPCs, animals and great beasts keep their old stats in this step (see below), so raids and beasts fight as today.
- An already-saved unit's old Strength (roll plus its level gains) becomes its base, so it now fights with its
  Strength skill. A level-30 crafter with Strength skill 5 hits as a 5, not a 30: that is the fold's point.

**Each read** goes through `RmStr()`, `RmAgi()` and `RmInt()` (new file `Remastered/StatFold.dm`, behind
`rm_stats_folded`, 0 = today). Per use:

| Use (file) | Today reads | Folded reads | Scale |
|---|---|---|---|
| Melee damage, weapon moves, knock-out blows (Combats.dm 238/280/375, WeaponSkills.dm 244, Subdue.dm 51) | Strength / 2 | RmStr() / 2 | 1:1 |
| Dodge, block, melee hit (Combats.dm 341/348/363) | Agility | RmAgi() | 1:1 |
| Bow and throw aim (CombatSkills.dm 327/329), arrow damage (Combat - Bows.dm 53) | Agility | RmAgi() | 1:1 |
| Bites (Vampires.dm, Werewolves.dm), grapples (Interact.dm 713) | Agility / Strength, both sides | the same through the accessors | 1:1 |
| Heavy stone doors (StoneDoors.dm 63) | Strength >= 40 | RmStr() >= 40 | 1:1 (Strength skill 40) |
| A golem's grip (Golems.dm 249) | Strength + Defence | RmStr() + Defence | 1:1 |
| Captives: win-over and escape odds (Captives.dm 629/637/821) | Intelligence x 3 / x 0.12 / x 0.8, Strength x 0.3, Agility x 0.15 | the accessors, Intelligence capped at 20 | cap: today's Intelligence is under ~15, a Magic 60 mage would swamp every other term |
| Mind dominate (HUD Building.dm 182) | Intelligence x 3 - foe's x 4 | the same, both capped at 20 | cap, as above |
| Magic and paper thresholds (Turfs.dm 815-819, CraftingStations.dm 8331/8378) | Intelligence >= 10 / >= 1 | Magic skill >= 10 / >= 1 | 1:1 on the Magic scale |
| Building tiredness and blood (Building.dm 189/201/231), spell aim offsets (HUD Building.dm 1220-1224) | Intelligence / 50, / 25, / 10, +-Intelligence | capped at 20 | cap |
| Evil Altar offering (CraftingStations.dm 5896, HalfDemons.dm 159), a kill's XP (Death.dm 39) | Strength + Agility / 2 | the accessors | 1:1 |
| Breeding caps and inherited stats (Breeding.dm), soul stones (SoulStone.dm), body parts (Death.dm 194-196), golem making (CraftingStations.dm 6178) | the stats as stored | unchanged: they move the stored stat, i.e. the bonus | - |
| Level-up gains and caps (Leveling.dm 151-153, 197-198) | +STR/+AGL a level | skipped for folded units | - |

## Measuring it (the gate)

Base vs fold on one game (`rm_stats_folded` 0/1), 30 fights a row, `reports/polish-night-1026/combat-rules/tests/cr_fair.dm`:
- recruit duels in plate, the start kit and bare fists (every fist fight must still end);
- the level ladder (5 v 1, 10 v 1, 20 v 10, 50 v 50), with each unit's character level set to its skill level so
  "today" has its real level-up Strength and Agility;
- 5 v 5 in the start kit;
- ms a blow.
Plus the area checks that read these stats: capture, stone doors, golems, stumps, combat.

Expected: units whose level and skills match fight as today, within chance. Recruits hit a little softer (old roll
about 8, Strength skill 3-8 after step 1). High-level units with low combat skills get weaker.

## Not in this step

- NPCs. Their presets set Strength = 50 and the like on top of their role levels (NPCLevels.dm). Folding them would
  drop that preset and make every raid softer, so it's a balance call for the owner: measure it as its own option
  (squad and NPC cases) once this lands.
