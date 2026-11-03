# Fixes plan, 2026-10-27

You decide; this page plans. Each fix gives what happens today (with the measured number), the recommended fix, every number or rule it changes, what it does to saves, its size, how we prove it, one or two real alternatives, and the questions only you can answer. "Not measured" means nobody has measured it yet.

## Your two questions, answered

**"Mountain zones only clear the first row, right?"** Almost. A stone zone (or Gather zone) over a mountain digs the **bottom block of every tile in the zone**, not just the front row. It never takes anything above that. Every tile turns into a one-block crawl under the rock, and then the zone stops with most of the mountain standing. In the arena (an 8 x 15 zone, 676 blocks, mountain 3-8 blocks high), 556 of the 676 blocks were still standing at 4 minutes. The row then says "Nothing left in reach: N blocks overhead". The plan is in section 3.

**"Do we have Tend off in Gather?"** There is no Tend at all any more, on or off. Since the Tend redo (your call, 10-26), harvesting always takes everything: whole trees, whole blocks, whole veins (Yield.dm:48 and :136 both answer "never keep any"). What grows back is the zone's own work: its workers plant and look after saplings on the stumps. One stale message still talks about tending: the "found a living ore block" notice says "right-click it to tend it" (Yield.dm:194). It should be reworded in the polish pass.

## Already decided

- **First-house stall:** approved 10-27, options (a)+(b), being built.
- **Big-village stutter (2,000 workers, 1.3-1.5 s ticks):** being fixed without changing regrow numbers.

## Ranked list (biggest gain for a player first)

| # | Issue | What I recommend now | Size | Status |
|---|---|---|---|---|
| 1 | A new village's first house never finishes by itself | (a)+(b) | - | Approved, being built |
| 2 | Ore is never stored: iron, gold, gems rot on the ground | Default drop-off and quarry yards take ore and gems; smelter and gem cutter fetch the right things | S-M | Needs your yes |
| 3 | Mountain zones dig only the bottom block | Now: one stone number per natural block, then dig three blocks top-down. After the freeze: a real quarry | S-M now, L later | Needs your yes |
| 4 | Big villages stutter at 2,000 workers | - | - | Being fixed |
| 5 | In groups training beats gear; gear above iron barely shows | Measure properly first (same weapons both sides), then a gentle armour-led re-curve of silver, gold, chitin and diamond | S, then S | Needs your yes |
| 6 | A save taken while a unit is dying brings it back standing | Now: the autosave waits while someone is down. Full fix: save the seconds left | S now, M full | Needs your yes |

---

## 2. Ore is never stored

### What happens today

No automatic worker ever stores mined iron, silver, gold, adamantium, sand, uncut gems, rock salt or bones. They lie where they fall and rot after about 31.7 minutes. That includes stores painted with "Stockpile here", which are announced as "a store for anything".

Measured (30 game-minutes at speed 4, play_round.dm, tests/loops-*-server.log), pieces lying off the stores at the end:

| Round | Lying | Of which |
|---|---|---|
| 8 Humans | 39-40 | Iron 23, Gold 6, Silver 5, Diamond 2, salt 2, soul stone 1, bones 1 |
| 6 Orcs | 38 | - |
| 8 Dwarves | 54 | Iron 31, Gold 9, Silver 6, gems 5, salt 2, bones 1 |

Two miners on an outcrop for 10 minutes left 44 pieces where they fell (reports/polish-night-1026/loops/miners-leave-unstored/README.md). The only way ore reaches a smelter today is by hand: the player's own mine order, or buying it.

Why: one realm-wide test decides what any worker may lift or store, and it reads only the main drop-off's setting (Delivery.dm:18-24). The default setting, "Wood + stone", means exactly that (Delivery.dm:14). The only setting that takes ore, "Mining supplies", drops wood. A store's own setting can only narrow that test, never widen it (Jobs.dm:2762-2766, 2832), so a "takes anything" store gets no ore either. A quarry's own yard takes stone only, and refuses a whole bag if one iron is in it (Jobs.dm:872, 2762).

Two smaller faults sit next to it:
- The smelter's Make order asks for "any ore", and stone counts as ore in the code (StationCraft.dm:43). With stone in the stores it very likely fetches stone and makes nothing. Not measured.
- The gem cutter's Make order asks for "any gem", which includes cut gems and rings (StationCraft.dm:48). It can fetch back finished goods. Not measured.

### Recommended fix

Banished-style default: the main drop-off takes all raw materials, and a quarry's yard takes what a quarry gives.

1. **One shared list of raw materials**, used by every store and every worker, so a new raw good is added in one place.
2. **The default drop-off takes wood, stone, ore and uncut gems.** Ore means Iron, Silver, Gold, Adamantium and Sand. Uncut gems means uncut ruby, emerald and diamond (never cut gems or rings). Rock salt joins too. Bones stay in "Mining supplies" only: they are one piece in 40 and not part of the rot problem, and adding them would send haulers after fish and corpse bones.
3. **New label: "Wood, stone and minerals"** (not "Raw materials", since food, skins and seeds stay out). "Wood", "Stone" and "Mining supplies" stay as narrower choices, and a new "Wood + stone only" choice keeps the old meaning for anyone who wants it.
4. **A quarry's yard takes the mining set** (stone, ore, uncut gems, salt), so a miner's mixed bag unloads beside the quarry and haulers carry it in. Existing quarry yards in saves do this too, with nothing rewritten in the save.
5. **Vampires and werewolves never pick up silver.** Today they can't carry it (Orders.dm:734), so without this rule they would keep walking to the same silver piece.
6. **The smelter fetches only real ore** (Iron, Silver, Gold, Adamantium, Sand). **The gem cutter fetches only uncut gems.**
7. The "a store for anything" wording (Jobs.dm:1689, 1720) becomes "takes what your drop-off takes".

Nothing else changes: not the rot timer, yard places or sizes, haulers' order, or which store a carrier picks. Ore then flows miner -> quarry yard -> hauler -> main stockpile, and the smelter's Make order fetches it from the store nearest the smelter.

Items 1-6 are the core. Item 7, soul stones, and showing ore on the board can be approved separately (build-exactly-what-was-approved).

Strong colony games do this by default. A Banished stockpile takes every raw material. RimWorld's default stockpile takes nearly everything, and narrow filters are opt-in. In Dwarf Fortress and Songs of Syx ore is a normal hauled good, never litter.

### Every number or rule that changes

| What | Today | Proposed |
|---|---|---|
| Default drop-off takes | wood, stone | wood, stone, 5 ores, 3 uncut gems, rock salt |
| Its label | "Wood + stone" | "Wood, stone and minerals" |
| Choices on the drop-off | Wood / Stone / Wood + stone / Mining supplies | Wood / Stone / Wood + stone only / Wood, stone and minerals / Mining supplies |
| "Mining supplies" takes | stone, ores, uncut gems, bones | the same + rock salt |
| "Ore yard" zone setting (Zones.dm:24) | ores, gems, ingots, bones | the same + rock salt |
| A quarry's own yard takes | stone only, all-or-nothing bag | stone, ores, uncut gems, rock salt |
| Smelter Make order fetches | anything counted as ore, stone included | Iron, Silver, Gold, Adamantium, Sand |
| Gem cutter Make order fetches | any gem, cut gems and rings included | uncut ruby, emerald, diamond |
| Vampire / werewolf workers | sent to silver they can't lift | never sent to silver |

Unchanged: the rot delay (31.7 minutes off the stores; nothing on a store rots), wood-zone yards, Gather-zone yards, yard distance and crowding rules, food, seeds, skins and ingot routing, soul stones (your question 3).

Correction to an earlier claim: ore does not always weigh what stone weighs. Iron, Silver and Adamantium weigh 20 like stone; Gold and Sand weigh 30 (Turfs.dm:6039, 6067). A bag of mesa gold holds fewer pieces.

### Save impact

No new saved values. If you choose that the default keeps its internal name, saved villages on the default get the new set at once. A village whose player had deliberately picked "Wood + stone" cannot be told apart from one that never touched it, so it gets ore too; that player can pick "Wood + stone only" again. If you would rather old saves keep exactly what they had, the new default gets its own name and old saves stay on wood + stone until the player switches (your question 1b). Quarry yards need no save rewrite.

### Size and what it depends on

S-M, about 50-70 lines plus the HUD label (through art/hud/src and hud.py). Lands through the polish land lock, coordinated with the session that owns zone behaviour.

### How we prove it

1. Each round counts ore **dug, stored and lying**, so the pass mark is a share, not a guess: 8 Humans, 8 Dwarves and 6 Orcs, 30 minutes at speed 4. Pass: at least 90% of dug ore, gems and salt on a store by the end; ore left in bags 0; stone and wood stored within noise of today (stone 291-297, wood 203-217), compared at the same machine load.
2. Two miners on the outcrop, 10 minutes: "left where it fell" 44 -> about 0; stone stored not lower than 360.
3. A new arena check: a quarry yard takes iron with stone; a hauler moves the yard's iron in; a smelter order with stone and iron in the stores makes iron ingots; a gem cutter order never fetches a cut gem; a werewolf miner beside lying silver is never sent to it; a worker carrying salt behaves; with the drop-off on "Stone" or "Wood", ore still stays on the ground; "Mining supplies" unchanged; an old save with a stone yard loads and the yard takes ore.
4. Existing checks still pass: yards, store areas, gather zones 18/18, jobs, fish zones, lodges (not slower than 4.1 min), buildings 26/26, food 7/7, obey 32/32. Three checks name the old filter or its text and must be updated (plan_build_test.dm:27, buildings_test.dm:116 and 304, tests/defense-native-initial-checks.json:577-578).
5. Cost: tick time with 200 and 2,000 workers against the same-day baseline. Stone per worker-hour may dip by up to about 10% because bags carry ore too. Not measured.

### Alternatives

- **Every store has its own setting, the main drop-off included** (RimWorld / Songs of Syx). A bag unloads what each store takes and carries the rest on. The right long-term model for big villages and for handing areas to nobles, but size L (about 15 places in the code), a per-item cost to measure at 2,000 workers, and a new system under the freeze. Best after the freeze, with the warehouse.
- **Minerals stop rotting and just stay where they fall.** Tiny, no change to gathering pace. But the smelter still never gets ore without a player, which goes against "make a plan and workers carry it out", and in a lasting MMO world ore litter piles up for good. Could be added on top if you want minerals to keep (question 4).

### Your questions

1. Should the default drop-off take wood, stone, ore, uncut gems and rock salt ("Wood, stone and minerals")? Or should ore go only to a separate yard, never to the main stockpile?
   1b. Should old saves on the default get the new set at once (recommended), or keep wood + stone until the player switches?
2. Should a quarry's own yard take ore and gems too, so miners unload by the quarry? (The other way: miners walk ore to the main stockpile.)
3. Soul stones (about 1 in 150 rock tiles, never rot): stored by workers like ore, or left for the player to pick up?
4. Loose ore, gems and salt off the stores still vanish after 31.7 minutes. Keep that, or should minerals never rot?
5. After the freeze: show ore on the job board (for example "Stone 294 · ore 31", or keep-at-least rows for iron and gold)?

---

## 3. Mountain zones dig only the bottom block

### What happens today

A stone or Gather zone over a mountain treats each tile as one flat tile. It digs that tile's bottom block, which opens a crawl under the rock, then moves on to the tile behind (Jobs.dm:169-178, 1063-1067). When every tile is a crawl it stops: "Nothing left in reach: N blocks overhead (Plan mode digs a mountain from the top)" (Jobs.dm:1876). Workers standing on the mountain are refused as "on another level" (Jobs.dm:1049).

Measured (arena "mount" scene, 8 minutes at speed 4, reports/polish-night-1026/zones/*.out):

| Version | Workers | Stored | Lying at end | Note |
|---|---|---|---|---|
| Today | 1 | 240 | 2 | |
| Today | 5 | 325 | - | zone ran dry, 48% of the time off the zone |
| Today | 20 | 322 | - | |
| Three blocks top-down ("mountain-face") with the loops fix | 5 | 649 | 3 | never idle |
| Three blocks top-down, before the loops fix | 1 | 99 | 76 | 175 dug; most of the "loss" was pieces lying |
| Bottom two blocks ("mountain-two") | 5 | 609 | 82 | before the loops fix |

The two one-miner runs come from before the loops fix and have not been re-measured.

There is a second, hidden problem: **the same block of rock gives different stone depending on how it is dug.** The two bottom blocks of a tile give about 2.7 stone each. Every block above gives 0.7 and no ore, at plain speed whatever the pick. Five separate pieces of code each decide "a block came out", with their own stone, ore, tool-speed and cave-in rules. The 2.7 is read from the code for the first bottom block; for the second it is inferred, and the measured 6.0 stone per tile for mountain-face (625 stored + 94 lying over 120 tiles = 0.7 + 2.7 + 2.7) fits that reading.

Worse, a tile whose bottom block is dug after the block above it goes through the 2006 finds table (Bump.dm:284-420): stone 70%, iron 35%, gold 5%, silver 5%, gems about 3%, a Death Beetle, cave spider or mole 2% each, a tower cap 3%, and a **1% cave-in that refills nearby open floor with no check for units standing there**. Both staged patches dig in that order.

### Recommended fix

**Step 1, now (freeze-safe, small): one stone number for every natural block.**
- Every natural mountain block gives the same stone, about 2.7 on average, whichever side or order it is dug from. The work per block stays the same (50), so the grind per block does not change.
- **Built rock gives back at most what it cost: 1 stone.** Laying a block costs 1 stone and only 3 blows (Plans.dm:228-238, 239). Without this rule, a build plan and a dig plan on the same cells would print stone (+1.7 per cycle).
- Stone only. Ore, the 2006 finds, tool speed on upper blocks, and whether carving ramps gives stone are separate decisions (questions 2-4). Carved ramps stay "no material" (mountain-walking-rules).
- **Then land mountain-face as polish:** a zone digs each tile's three reachable blocks from the ground, top-down, like a click. Before it lands, the 1% cave-in and the critters must not run for zone digs, because this digging order sends every tile through that table. Re-measure the one-miner case first.

**Step 2, after the freeze: a real quarry.** You mark a mountain once; it is worked out layer by layer.
- It is a **dig plan made for you** from the zone: Plan mode already takes the highest block first, cuts its own way up with tunnels and one-tile ramps, and never digs a block someone stands on (Plans.dm:139, 621). The quarry reuses that instead of a second, separate picker, and runs it with the miners. No 600-block cap for it (Plans.dm:13); the arena zone alone is 676 blocks.
- **Opt-in:** a "Quarry" switch on the zone. Old zones are never turned into quarries on load, so no saved world starts flattening its mountains. Stone does not grow back.
- **A depth floor from day one,** shown on the zone, with a safe default (your question 6). Stonehearth and Dwarf Fortress both put a depth on the dig order.
- **Safe edges:** strictly the top block of a tile first, so no crawls and no cave-ins from a quarry. No step of 2 or more without a ramp, inside the zone **and at its rim**, so nobody outside falls in and nobody inside is trapped. The ramp lane nearest the yard is dug last, so a way down always stands.
- Workers on top of the mountain may work and must be able to unload: today the zone also refuses anyone not on the drop-off's level (Jobs.dm:1038). Hauling down the ramp lane has to be solved with it.
- Two zones over one mountain: forbidden, or the tile marker changes (a tile holds only one zone today, Jobs.dm:75).
- Row text: "Quarry: layer 5 of 7, 214 blocks left, +N/min".

### Every number or rule that changes

Step 1:

| What | Today | Proposed |
|---|---|---|
| Stone from a natural block above the bottom two | 0.7 | about 2.7 (2 from the work + a 70% chance of one more) |
| Stone from the two bottom blocks | about 2.7 | about 2.7 (unchanged) |
| Stone from a built block | 0.7-2.7, depending on height | at most 1 (what it cost) |
| Zone over a mountain digs | bottom block of each tile | each tile's three reachable blocks, top-down |
| 1% cave-in and critters on zone digs | runs on the upper-then-bottom order | off for zone digs |
| Work per block | 50 | 50 (unchanged) |

Step 2: a quarry's stone over its life is about 2.7 x its blocks: the arena zone 676 blocks -> about 1,825 stone, against about 325 today before it stops. Stone per worker-minute while working should stay about the same; trips down from the upper layers are longer. Not measured. New settings: the Quarry switch and the depth floor.

### Save impact

Step 1: none. Block cuts and vein numbers are already saved. Step 2: zones gain two optional saved values (quarry on/off, depth floor). Old zones read as "not a quarry". Old crawls under rock are dug from the top like any tile.

### Size and what it depends on

Step 1: S-M. Step 2: L (M only if it is built as a generated dig plan as above). Both depend on the ore fix (section 2): more mountain dug means more ore, and today it rots. Step 2 waits for the end of the freeze unless you call it polish.

### How we prove it

1. A new block-stone check: dig 200 blocks by each way (bottom first, top first, from the top, roof, plan), plain pick and gold pick. Pass: mean stone per natural block 2.7 +/- 0.2 on every way, and no block paid twice; built blocks give at most 1; 0 critters and 0 cave-ins on zone digs. Time per block is not expected to be equal across ways in step 1 (the blow pacing differs) and is reported, not passed.
2. Arena "mount" scene with 1, 5 and 20 workers, 8 and 30 minutes. Pass: stored at least today's at every count (the one-miner baseline re-measured on today's code first), lying 5 or fewer, nobody stuck. Stone compared only at the same tick cost.
3. Step 2 extra: sampled every 2 s, no step of 2 or more without a ramp under any standing worker, inside or at the rim; nobody stranded; 0 crawls made; 0 cave-ins; the row never says "Nothing left" while a way up can be cut. Compared against Plan mode digging the same volume. With 10 quarries and 2,000 workers, the worst tick no worse than today's.
4. Existing checks: yield, plan, plan access, plan build, gather zones, gather, mountain levels and heights, golem rise, wood, lodges, plus compile, combat, food, buildings, obey.
5. Last, one short real-client run: 3-5 Dwarves mark a mountain; the highlight sits on the exact block worked.

### Alternatives

- **Bottom two blocks per tile** (staged "mountain-two"): small, roughly doubles a zone's stone (325 -> 609 with 5 workers). But it leaves blocks 2 and up as a roof over the whole zone, never works the mountain out, and sends every tile through the 2006 table and its cave-in. Only with step 1.
- **Stop at three blocks for good** (mountain-face as the end state): workers end up under rock in 3-high halls on a mountain 3-8 high, and Plan mode does the rest by hand. Good as the freeze-time step, not as the goal.

### Your questions

1. One stone number for every natural block: about 2.7 (what the bottom blocks give today), or a different single number? And built blocks give back at most 1?
2. The old 2006 mining finds (iron 35%, gold 5%, silver 5%, rare gems): keep them as a roll when a tile is cleared, or should mountain ore come only from veins and biome rock? (The critters and the 1% cave-in go either way.)
3. Should good picks dig upper blocks faster too (today they speed only the bottom two)?
4. Should vein ore come out however a tile is dug (today it is lost when dug from the top)? This needs its own design: which block pays the ore.
5. Is a quarry, worked top-down to the ground with its own ramp lane, the end goal? Or should zones stop at a fixed height and leave the rest to Plan mode?
6. The quarry's depth floor default: to the ground, or leave a bench of N blocks?
7. During the freeze: land step 1 and mountain-face now as polish, and the quarry after? Or wait and do both together?

---

## 5. Training beats gear in groups; gear above iron barely shows

### What happens today

Measured (devlog/2026-10-26/combat-rules.md:9-70; logs in reports/polish-night-1026/combat-rules/runs/; the test is reports/polish-night-1026/combat-rules/tests/cr_fair.dm):

| Fight | Result |
|---|---|
| Duel: level 50 in the start kit vs level 30 in iron + longsword | L50 wins 13/30 |
| Duel: L50 start vs L30 Hellforged + longsword | L50 wins 14/30 |
| 5 vs 5: L50 start vs L30 iron + longsword | L50 wins 12/12 |
| 5 vs 5: L50 start vs L30 Hellforged | L50 wins 9/12 |
| Duel, same level 30: iron + longsword vs start kit | iron wins 24/30 |
| Duel, same level 30: iron + battle axe vs start kit | iron wins 18/30 |
| Duel, both level 50: Hellforged vs iron | 15/30 (no edge) |

So one on one, the trade-off is roughly what you asked for. In groups, 20 levels wins nearly every time.

Why:
- **Groups magnify any edge.** A duel is decided after only 2-5 landed blows a side, so luck evens it out. A 5 vs 5 has 12-26 landed blows a side and the winner of each small fight joins the next, so the same edge becomes near-certain.
- **Training works through about seven channels** (hit chance, dodge, damage, damage taken, limb and bleed guards, moves; Defence 50 also gives steady morale). Gear works through two (weapon damage, armour share).
- **One trained blow takes a fresh limb through iron.** A level-50 blow is about 170 before armour; limbs and the head have 100 HP (Vars.dm:511-515). Through iron greaves it is still about 108, so iron and better armour score the same. No vambrace stops it, not even Hellforged.
- **The tier ladder is flat:** silver is iron's numbers, gold barely above (chest 12 / 12 / 13; sword 20-24 / 18-22 / 22-26; art/enhance/catalogue.py:42-56).
- **Gear above your level works at half** (GearAny.dm:15), so Hellforged at level 30 is about iron.
- **The tables mixed weapon kinds.** The trained side always had an axe, which hits a second foe only in groups; the geared side mostly had a longsword, which parries in duels. That overstates gear in duels and understates it in groups.

Not the cause: morale (11/12 with it off), surround (12/12 with it off), the veteran rule.

Gaps in the evidence: there is no measured fight with high gear at its own level except the Hellforged-vs-iron row above. Adamantium was tested at "Quality", but every crafted adamantium piece is Legendary (x1.3, Gear.dm:166-167), so it was under-measured. A correction for the devlog: an iron breastplate takes 42% and a Hellforged one 56% at full strength, not 11% and 17%.

### Recommended fix

**Step 0: measure properly before choosing numbers** (no game change, S). The earlier draft's expected results came from a rough model that misses the limb overkill and moved a lot with small changes (one headline row went from 46% to 18% when the axe's second-foe hit was changed). So first:
- the same weapon kind on both sides, with sword-vs-sword and axe-vs-axe pairings;
- adamantium at Legendary, as crafted;
- the missing at-level rows: level 35 silver, level 45 gold and level 70-75 Hellforged against iron at the same level, with a start-kit control;
- 30 battles per 5 vs 5 cell, not 12, and steady measures alongside win counts: HP left, landed blows per kill, limbs lost per landed blow.

**Step 1: an armour-led re-curve of four tiers** (data only, S). Put armour on a straight line from iron to Hellforged, and raise weapon damage only about a third as much. More armour and modest damage makes fights longer, not shorter (slow-brutal-grind), and keeps more blows below the 100-HP limb line. The numbers below are proposals; the step 0 tables decide whether they hold.
- Melee weapons and armour only. Bows stay as they are in this step: gear level does not scale bows, so a raise would reach archers at full strength at any level.
- Only the gear data file is regenerated, never the sprite sheets (gear64-shading-pipeline).

**Step 2: "above-level gear counts more", as its own switch, off by default.** Today gear above your level works at the share level / item level, never below half. The option: half plus half of that share, so Hellforged at level 30 works at 70% instead of 50%. It changes the curve you approved on 10-26 ("scaled, half at least"), so it is a separate question with its own table.

**Step 3, only if steps 1-2 measured still leave level 30-35 geared units losing most 5 vs 5s:** gear on the hit roll (RuneScape-style accuracy and armour bonuses, M), or making one blow rarely take a fresh limb (L, a full re-test under the 10-25 bar: duels about 85 s, some knock-outs, limbs off in most fights).

### Every number or rule that changes

Step 1 (Quality rank; proposed, to be confirmed by the step 0 table):

| Tier (use level) | Chest Defence today -> proposed | Sword damage today -> proposed |
|---|---|---|
| Chitin (20) | 13 -> 13.5 | 20-28 -> about 21-29 |
| Silver (30) | 12 -> 15 | 18-22 -> about 21-26 |
| Gold (40) | 13 -> 16.5 | 22-26 -> about 25-31 |
| Diamond (60) | 19 -> 19.5 | 32-40 -> about 34-43 |
| Adamantium (50) | 18.5 -> your choice (question 3) | 30-40 -> your choice |

Unchanged: wood, leather, bone, iron, Hellforged (chest 21, sword 40-55), the beast tiers, all bows, all training numbers. Helms, greaves, vambraces, longswords and battle axes follow from the tier rows as today (helm x0.6, greaves x0.8, vambrace x0.4 of the chest).

Adamantium: crafted adamantium is always Legendary (x1.3), so today it is really chest 24 and about 45 sword damage, already above Hellforged (21, 47.5), which is made from adamantium ingots. To sit at or just under Hellforged as crafted, its chest base would go 18.5 -> 16 (crafted 20.8). The other way is to stop making every adamantium piece Legendary.

Beast tiers to check against the new line: dragonhide (use 40) chest 16 is about the new gold 16.5; spiderfang (use 40) 30-40 and dragonfang (use 50) 36-46 stay above the new gold and adamantium damage.

Step 2 (off by default), gear strength, today -> option (item use levels differ by piece; these are the earlier draft's worked cases): level 1 in iron 50% -> 53%; level 30 in Hellforged 50% -> 70%; level 30 in adamantium 55% -> 77%; level 50 in Hellforged 67% -> 83%; at 80% of the item's level 80% -> 90%; at the item's own level 100% -> 100%.

Not touched: NPC and raider kits use the old item types, which have no gear level, so neither step changes them (Restart.dm:131-148, CraftKits.dm:58+, Raids.dm:210). Players' new silver gets better; raiders' old silver stays as it is.

### Save impact

Step 2: none. Step 1: crafted gear stores its numbers when it is made (Gear.dm:177-183). Whether the save writer skips values equal to the default (then Quality-rank pieces would pick up the new numbers on load and other ranks would not) is not verified on our engine. Verify that first. Re-statting old gear on load is a staged after-freeze item.

### Size and what it depends on

Step 0: S, about 30 test cells, one big run at a time. Step 1: S (five data rows, a data-only export). Step 2: S (one switch). It depends on your yes under the freeze (balance data, no new feature) and your answers below.

### How we prove it

Before and after on a scratch copy with the same test, arena at speed 4. Duels 30 per cell, 5 vs 5 and 20 vs 20 at 30 battles per cell, every geared row at both weapon kinds. Proposed pass marks (yours to confirm):
- training alone (L50 start vs L30 start; L50 iron vs L30 iron): at least 24/30 duels and 25/30 at 5 vs 5;
- gear alone at the same level: at least 21/30 duels and 21/30 at 5 vs 5;
- "the geared unit can win" (L50 start vs L30 silver, L35 gold, L30 Hellforged): 5 vs 5 between 10 and 20 of 30 at both weapon kinds;
- tiers at the same level (adamantium, Hellforged vs iron): at least 20/30.
Guards: recruit duels stay 68-70 s; trained duels not shorter than today; knock-outs and limbs within noise; combat 32/32, stumps 23/23, the weapon-cap check.

### Alternatives

- **Gear on the hit roll** (RuneScape): weapons add accuracy, armour takes off the foe's hit chance. The strongest lever and the closest to RuneScape, but a new rule under the freeze, needs unit-card lines, and may push gold and up past "trained units are powerful". M.
- **Fix the overkill first:** one blow rarely takes a fresh limb, so armour adds up across blows. Goes at the deepest cause and would lengthen duels toward 70-90 s, but changes every combat table. L, with the full re-test under the 10-25 bar.

### Your questions

1. The target: at 5 vs 5, should a level 30-35 unit in the best gear for its level beat a level 50 in the start kit about half the time? Or should 20 levels still win most group fights?
2. Silver and gold: real steps above iron (silver chest 15, gold 16.5), or kept as side-grades with iron's use level?
3. Adamantium: lower its base so crafted pieces sit just under Hellforged (chest 18.5 -> 16), or stop making every piece Legendary?
4. Above-level gear: keep "level / item level, half at least" exactly as approved, or test the "half plus half" option as a separate switch?
5. Existing crafted gear: re-stat it to the new numbers after the freeze, or new crafts only?
6. Vambraces are 0.4 of the chest and never stop a trained blow, even Hellforged. Raise them to 0.6? (Not in the recommendation.)
7. Is a balance-data change acceptable under the freeze? From now on, should every combat table give both sides the same weapon kind?

---

## 6. A save taken while a unit is dying brings it back standing

### What happens today

A unit that is dying (the 60 s to save it) or knocked out, caught in a save, comes back from the reload standing at 1 HP, not dying, and stays alive. Measured: "Dying One" came back with no dying clock, standing, at 1 HP, and was still alive 70 s later; a knocked-out unit came back awake (reports/polish-night-1026/start/evidence/save-reload-dying.txt).

A correction to how the issue was put: **quitting itself does not save units.** Units are written by the autosave (about every 16 minutes, Saves.dm:9-15), by Save Now, and by an admin command. Logging out saves only kills and faction (Login.dm:19). Whether the Mac app saves on quit is not measured. The usual case is an autosave caught in the middle of a fall, then a reload much later.

Why: the dying and knock-out clocks are not saved (BleedOut.dm:11, Subdue.dm:20-21), and loading stands every unit up (Saves.dm:66-68). Two side effects follow from the code (not measured):
- A stump bleed-out restarts at a full 60 s after each reload.
- A reloaded dying unit works, eats and sleeps during the away catch-up.

On a running server, logging out never dodges death: the units stay in the world and keep bleeding (Login.dm:16-30).

### Recommended fix

**Now (freeze-safe, S): never take a save while someone is down.**
- The autosave waits while any of the player's units is dying or knocked out, checking again every 10 s, for at most about 3 minutes, then saves anyway, so a long battle cannot block saving for good.
- Save Now refuses while someone is down, with a line: "Can't save while X is down."
- No save-format change. It does not cover a crash or a server restart in the middle of a fall, and the max wait still lets a rare save through.

**Full fix (M), after the freeze or now if you prefer: save the seconds left and settle them by the live rules.**
1. Each unit saves two numbers: the seconds of dying left and the seconds of knock-out left (0 when standing).
2. On load, a downed unit lies down waiting. While waiting, nothing can restart its 60 s (one guard covers all six things that start bleeding out).
3. When the village starts running for the player:
   - Away under 5 minutes: the clock resumes with exactly the seconds left.
   - Away 5 minutes or more (the usual case after an autosave): the away catch-up gives the dying unit the normal care step first, the one that already treats stumps (friends near with a bandage or poultice, the Doctor, fire). Saved: it lives the rest of the away time normally. Not saved: it is dead on return ("X bled out while you were away", on the away card). A knocked-out unit simply wakes, since 30 s is far shorter than 5 minutes.
   - While down it never works, eats, sleeps or heals in the catch-up.
4. A fallback so no unit can stay stuck waiting: if the village has not started within 30 s of load, the clock starts anyway.

Accepted limit: other faints (a fresh stump, surgery, some wounds) still load awake. Knock-outs need this only for "no free stand-up"; captures already do not depend on it (Capture.dm:107-108).

Strong games: RimWorld and Dwarf Fortress save a bleeding pawn exactly as it was. RuneScape (about 10 s) and WoW (20 s) never let logging out end danger.

### Every number or rule that changes

No game number changes: 60 s to bleed out, 30 s knock-out, 5 minutes for away time, all unchanged.

| Rule | Today | Proposed |
|---|---|---|
| Autosave while a unit is down (now) | saves at once | waits, at most about 3 min |
| Save Now while a unit is down (now) | saves | refuses, with a line |
| Unit saved dying (full fix) | loads standing at 1 HP | loads dying with its seconds left |
| Unit saved knocked out (full fix) | loads awake | loads out cold with its seconds left |
| Stump bleed-out after a reload (full fix) | fresh 60 s | the seconds it had left |
| Away 5 min or more while dying (full fix) | stands up, works | saved by the normal care, or dead with an away-card line |
| Down during the catch-up (full fix) | works, eats, sleeps, heals | does none of it |

### Save impact

Interim: none. Full fix: two small numbers per unit (a few KB for 200 units against a 20 MB unit save; not measured). Old saves load as today. Loading a new save in an older build is not supported.

### Size and what it depends on

Interim: S. Full fix: M (a save hook, a load hook, a start hook, the guard, the away settlement and its card line, five test groups). Either needs your OK under the freeze, one batched rebuild, and the polish land lock.

### How we prove it

1. Interim: an autosave with a unit dying waits, then saves once it is saved or dead; Save Now shows the refusal; a 4-minute fight still gets its save at the cap.
2. Full fix, save round trip: a unit dying with 40 s left is saved and reloaded; it lies dying with about 40 s left once the village runs. With no helper it dies "Bleeding To Death" 40-42 s later; with a friend carrying a bandage within 3 tiles it is saved. Two reloads in a row: the time only goes down. Stump bleed-out keeps its seconds. Knocked out with 20 s left wakes about 20 s after.
3. Full fix, away: a dying unit with a 6-minute and a 16-minute gap. With a Doctor: alive. Without help: dead, with the card line. Either way no meals, sleep, HP change or work while down. "Nobody starved" checks still pass.
4. An old save loads with 0 errors. The bleed-out, falls, knock-out, treat, rescue and far-records checks still pass (rerun obey and parry A/B if they fail; they fail by chance).
5. One short real-client check at speed 1: press Save Now with a unit dying (interim: it refuses), then with the full fix reopen and see the dying pose and the seconds counting.

### Alternatives

- **A real-time deadline:** save the moment it will bleed out in real time; on load, if that moment has passed, it is dead. Simplest and impossible to game, but harsher than live play (no friend or Doctor gets a chance) and a crash with an autosave mid-fight kills units nobody could reach.
- **Kill on load:** anyone saved while down is dead. Harshest; punishes crashes and units a Doctor beside them would have saved.

(Rejected: "put any unit at 1 HP back to dying on load". Units already saved from bleeding stay at 1 HP, so they would be put back to dying on every reload.)

### Your questions

1. Ship the interim now (autosave waits, Save Now refuses) and the full fix after the freeze? Or the full fix now?
2. Full fix: after 5 minutes or more away, should a dying unit be settled by the normal away care (saved, or dead with a card line)? Or should its clock always freeze and resume with the seconds left?
3. Should knocked-out units also keep their seconds left (wake late instead of at once)?
4. After the freeze: NPC foes are not saved, so a reload in the middle of a fight makes them vanish. Do you want a "can't leave in combat" rule for the MMO later (RuneScape about 10 s, WoW 20 s)?
