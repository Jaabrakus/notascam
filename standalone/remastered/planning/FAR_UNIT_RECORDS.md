# Far-away units as records

Written 2026-10-24 (far-records session). In game/ since 22:46, switched off (`rm_far_on = 0`) since ~23:10 for the
next app build; restore point `restore-points/before-far-records-20261024`. Code: `game/Code/Remastered/FarRecords.dm`. Proof: `tests/far_records_test.dm`
through `tools/check_arena.py`. This is step 5 of `planning/UNIT_MEMORY_PLAN.md` ("records for units nobody is near").

## Why

The world's goal is ~30,000 units a world and 1,000,000 across the realms, with real units only where someone is
watching (memory `unit-scale-30k`). Awake.dm already keeps only the 16-tile chunks near connected players fully alive,
but every unit elsewhere is still a whole DM mob: ~55 KB of heap since the shared unit clock, its clock jobs booked,
its walk loop sleeping and waking, an engine entity. Most of those units belong to players who are not connected.

## Who becomes a record

A unit becomes a record when all of these hold for `rm_far_quiet` (60 s):

- its owner is a player who **was connected in this server run and has left** (`rm_far_left`; a player who never
  connected, such as an arena test's, is never recorded), and is **not connected** now (Awake.dm marks the land round a connected player's camera, units and
  workshops, so their units are always awake anyway), and it stands in **asleep land** (`RmAwake()` is 0);
- nothing is going on with it: not bleeding, no stump still bleeding, festering or getting its blood back, not ill
  (poison, fever, food poisoning), not drunk, not burning; not captive, caged, in a hole; no orders, no fight, no
  destination or target, not looking after itself (Care.dm), not on a construction site or a board order; not asleep,
  out cold, stunned, meditating or flying; not royal, the hero or the heir; not an egg or a cart;
- it is not one of the races whose needs work differently (spiders, dragons, zombies, devourers, vampires);
- everything it links to can be kept: its own things, tiles, its owner, the owner's other units (by uid). A unit that
  holds anything else (a workshop, another player's unit, a datum) stays a full unit. So does a unit that an awake
  unit of the same owner holds.

Wild creatures and NPC towns are not records yet (their lairs and spawners hold them by reference). They already
rest in asleep land (Awake.dm).

## What a record keeps

A record is one DM list (`RMF_*` in FarRecords.dm):

| Field | What |
| --- | --- |
| x, y, z | where it stood |
| uid | `remaster_uid` (Lineage.dm; given one if it had none) |
| type, job | its type path; `remaster_job`, for a quick look |
| asleep since | `world.time`, `RemasterNow()` (real time) and the server run's id |
| vars | every **saved** var (`issaved()`, the same set a save writes) whose value differs from its type's, as name, value pairs |
| things | each thing it carries, depth first: type, what holds it, its saved vars |
| lists | each of its owner's lists it was in (UnitList, the quick groups `Group1`..`Group9`, any other), and its assoc value |
| links | uids of the owner's other units it holds |

Values: numbers, text, paths and null as they are; lists as `list("~L", key, value, ...)`; icon files as
`list("~F", path)`; tiles as `list("~T", x, y, z)`; its own things as `list("~I", place)`; its owner as
`list("~O")`; another of the owner's units as `list("~U", uid)`. Every empty list is one shared list. Tmp vars are not
kept (as in a save): a woken unit has no orders, no path and no target, which is why units with those stay awake.

After the record is made the unit's things and the unit are deleted, and it leaves the owner's lists.

## Waking

A record wakes into a full mob when:

- its **chunk wakes** (a connected player's camera or unit comes near: Awake.dm's map, looked at every 2 s);
- something **on its way** (a raider marching in, a creature chasing, a caravan: any unit or creature with a
  destination or a target, not of an offline player) comes **within one chunk** of it (looked at every 6 s);
- its **owner connects** (all their records, before the catch-up looks at the army);
- a unit it is linked to wakes (its links, both ways: they wake together, so links find each other).

The unit is made as a save load makes it: `new type(tile)` (with a stand-in `usr`, since races' `New()` add to usr's
stats), the gear its kind's `New()` hands out deleted, its things made inside it (and what their `New()` put in them
deleted), then every saved var set back from the record and every saved var the record doesn't hold set back to the
type's own (a race's random skin and stats). Then its owner, its places in the owner's lists, overlays. `New()` books
its clock jobs and walk loop again. A tile that can't hold it any more (a wall went up) puts it on the nearest open one.

## The time it slept

Nothing in asleep land can be seen, so a record does not run anything while it sleeps: its clock only counts. When it
wakes, it lives that time through at once (8 hours at most, as Away.dm) with the game's own procs, in this order:

1. **Work** (Away.dm's work procs, at the live pace): its job's budget is the time asleep less the time meals and sleep
   take (`RM_FAR_MEAL_SECS` a meal, `RM_FAR_SLEEP_SECS` a night), times `rm_far_rate[job]` (Away.dm's budget seconds a
   live second is worth, measured by FarHour below) and `rm_far_pace` (1).

   | Job | As a record |
   | --- | --- |
   | idle (no job, manual, and the jobs below not listed) | nothing; it eats and sleeps |
   | woodcutter, miner, board worker on wood or stone | `RemasterAwayHarvest`: the nearest tree or rock to its work area, chopped or dug with the race's own Bump code and its tool (taken from a store if it has none), the goods to the stores; tending marks kept |
   | hauler | `RemasterAwayHaul`: loose things in its work area onto the stores that take them |
   | farmer | `RemasterAwayFarm`: ripe fruit picked (plants kept growing live meanwhile, so only the growth they lost full is added), seeds planted on free farmland |
   | hunter, cook, builder, carpenter queue, merchant, doctor, gravedigger | wait (as merchants do in Away.dm); next to add |

2. **Needs**, as the clock jobs run them (one tick every 40 s, `HungerTick`/`TirednessTick` with a connected owner:
   1 a tick, half for lizardmen; gargoyles never hungry; elves and their kin rest awake). Each time hunger reaches the
   hungry mark (20) it eats a **real meal**: a food pot or stall's serving (`RemasterAwayMeal`), else the best food on
   the stores, eaten with `EatItem` (food value, raw or fungus halved, rot thrown away, poison tasted or eaten, moods,
   seeds dropped, Healing.dm's +20). Each time tiredness reaches the tired mark it sleeps as Care.dm sends it: its own
   bed or a free one within 30 tiles (claimed), `Sleep(300 - comfort)`, +10 every 10 s and fully rested; else rough,
   `Sleep(450)`, +5 every 10 s and rested to 70 only. The Heal tick that falls in the sleep mends limbs and organs.
   A bleeding stump is treated first, as in the first minutes live (its own bag or a friend's, a villager carrying
   something, the Doctor with a poultice or a torch or bandage from a store, a fire close by), then bleeds by the
   stump and the original bleeding ticks until treated or dead. After each meal or sleep it does what it would for
   itself: potions it drinks by itself (Bag.dm), a carried remedy, the Doctor's or the stall's remedy when ill or badly
   hurt (Doctor.dm), stone for a gargoyle's limbs (StoneLimbs.dm). Everyone woken together takes their meals in turn, one
   each, so a short larder is shared rather than eaten by the first. Nobody starves asleep: with no food left they
   wake hungry (Away.dm's rule; awake, a hungry unit loses health below 10).
3. **The clock jobs every unit runs**: the Heal tick's slow brain and lung mending (+0.05 a tick), a caster's mana
   (`HungerTick`), a regrowing race's `RegenTick` (replayed, every 60 s).

What it brought in goes on the owner's "While you were away" card: with the catch-up's own when the owner's first
connection of a run has one (Away.dm takes the records' tallies), else a card of its own (a relog in the same run:
the catch-up runs once a run).

Not lived through (as today for an offline player's awake units, which do nothing: the per-player track only runs
for connected players): moods drifting, skills from practice other than the work procs' own, ageing.

A working record doesn't wait for someone to come: every 10 minutes of game time (`RM_FAR_SETTLE`) it wakes, lives
those minutes through and goes back to sleep at the next sweep, because loose goods in its area rot in about half an
hour (`ItemDecay`) while a live worker would have carried them in. Waking is spread out: nearest a connected
player's camera first, 100 records at a time (each with its whole link group), the tick kept under 10 ms
(`rm_far_tick_use`), with pauses between units, between 1-minute work slices and between meal and sleep rounds. Meals
and beds come from lists made once per batch (the stores' food best first, beds by 16-tile chunk), not a search per meal.

Away.dm's catch-up (the first connection of a server run, for units that were never records) now lives its time
through the same way (`RmFarLiveThrough`): it no longer sets health to full or tiredness to rested.

## Interfaces with other work

- **Work zones (Jobs.dm)**: `P.RmJobUnitGone(M)` before a unit becomes a record, `P.RmJobUnitBack(M)` once it is back,
  and `P.RmJobAsleep(M)` gives a zone worker's job, zone centre and what the row still wants (all behind `hascall`).
- **Map regions on disk (map-memory)**: a global `rm_map_hook` with `Loaded(x, y, z)` and `Load(x, y, z)`. In an
  unloaded region a record only counts its time (no self-settle); a wake there loads the region first or waits.
- **What records will have brought in**: `P.RmFarExpected()` gives "wood", "stone", "things" and "food" so far
  (time asleep × `rm_far_per_hour`, cached 10 s), for the Village overview or the job board until the real result.

## Saves (WorldSave.dm, Saves.dm)

- The records are the owner's: `Player/var/rm_far` (a saved var), written by `SaveUnits()` with the army and read by
  `LoadUnits()`. A record is plain data (numbers, text, paths, lists), so the savefile keeps it exactly
  (FarRun: written and read back unchanged). Items inside a record are not on the ground, so `RemasterSaveWorld()`
  never writes them twice.
- Read back in a new server run (the owner logs in after a restart), a record's time asleep runs from the real time
  it fell asleep (`RemasterNow()`), so time the server was down counts too, capped at 8 hours; Away.dm's catch-up
  passes over units that were records (`rm_far_woke`), so no time is counted twice.
- Before a woken unit works, `RemasterTouchAround()` records its land's tiles as they were, so the world save sees
  the trees and rock its work removes as changes.
- Away.dm changes: the catch-up skips `rm_far_woke` units and starts its tally from the records' tallies.

## Split with the server-performance work

The server-performance session moves the busiest **live** job loops into native engine code. Records never run those
loops: a record is not a mob, and a woken unit gets its loops back through `New()` like a loaded one. FarRecords.dm only
calls Away.dm's work procs and the eating/sleeping procs on a just-woken unit, and reads the job vars
(`remaster_job`, `remaster_area_*`, `remaster_board_role`, pauses). If a job loop moves to native code, its Away.dm
twin is what records use; nothing in FarRecords.dm needs to follow.

## Proof

`tests/far_records_test.dm` through `tools/check_arena.py` (`--entry FrRun`, `FrHour`, `FrHeal`, `FrScale`, `FrLoad`),
run with `tools/runlock.py --kind run`. Timed runs at game speed 4 (they log the pace; the hour ran at 4.00-4.01x,
0 s behind); memory and CPU at speed 1.

- **Same unit back** (FrRun): a Human woodcutter (wounded, a broken arm, two logs, axe, pick), a Dwarf miner (an
  equipped pickaxe, a lost leg healed over) and an Elf farmer become records and wake: all 2,260 saved values of the
  three and their things are equal; the woodcutter's link to the miner points at the woken miner; quick group 1
  restored; clock jobs booked again. Waking the woodcutter alone wakes the miner it links to, not the farmer.
- **Who stays awake** (FrRun): a bleeding unit, a walking unit and one in watched land stay units; a quiet one sleeps.
- **Waking** (FrRun): nothing near, records stay; its land watched again, it wakes (the other record doesn't); a
  resting orc beside it doesn't wake it, the same orc marching to somewhere does.
- **Saves** (FrRun): records through a savefile and back unchanged; read back as from an earlier run, an hour on the
  real clock is lived through exactly as the clock jobs run it (hungry and tired at 80 ticks, a tomato from the stores,
  a rough sleep, 10 more ticks: Hunger, Tiredness and health as worked out by hand).
- **Work** (FrHour; a Human of its own skills, a stockpile each, the same patch live and asleep; the record's goods
  counted as they land):

  | Job | 5 min live | 5 min record | 1 h live | 1 h record |
  | --- | --- | --- | --- | --- |
  | woodcutter (open wood, tended) | 33 logs | 33 (0 %) | wood worked out: 33 trees → 0 | 33 → 0 |
  | miner (mountain face, 120 tiles) | 246 stone | 263 (6 %) | quarry worked out: 120 → 0 | 120 → 2 |
  | hauler (715 logs) | 67 | 66 (1 %) | 359 | 396 (10 %) |
  | farmer (6 tomato plants) | 36 | 36 (0 %) | 198 | 227 (14 %) |

  A 6-tile work area of wood or rock is worked out live within minutes. After that the live woodcutter keeps nibbling
  the tended trees as they creep back over half (almost no logs), and the live miner, which digs faster than it can
  carry, leaves stone to rot. Records copy neither, so over the hour the miner's goods differ (live 194, record 348) and
  are reported, not checked; the area is checked instead.
- **Health over time away** (FrHeal, Away.dm's real catch-up against a live unit with the connected-player clock jobs;
  a villager at 30 % health, or at full with a fresh arm stump): 5 minutes and 1 hour, all 20 cases within 15 %,
  18 exactly (none, food, bed, Doctor and their combinations; a stump with nothing for it bleeds to death both ways; a
  stump with a torch is seared both ways). The 6-hour leg was dropped at the user's word. With no food, the catch-up
  floors hunger at 20 and never starves (the user's rule, kept), where a live unit would starve.
- **The existing away checks** (`tools/check_away.py`'s test with these files): all pass (13 meals now where the old
  code counted 9, because meals now go through `EatItem`).
- **5,000 units** (FrScale, speed 1, the memory-report engine build): a live Dwarf is 71-72 KB of heap; a record
  (Dwarf, axe, two logs) 3.1-3.4 KB (5,000 copies on the heap). DM time a tick with 5,000 live idle units 29-34 ms,
  with them as records 0.02 ms. Putting all 5,000 to sleep took 8 s and waking them 23 s, both spread over ticks.
  The heap figure right after they sleep stays high (the .NET heap keeps the freed space); the working set falls from
  1,235 to 753 MB.
- **A region waking** (FrLoad, speed 1, 1,000 records each with 8 hours to live through: 100 woodcutters and 100
  miners on 40 work areas, 2,000 tomatoes on the stores, the rest idle; the machine shared with 7 other sessions' runs):
  all lived through in 308 s; mean 13 ms a tick, 125 of 3,082 ticks over 20 ms, 4 over 100 ms (worst 287 ms). Before
  the per-batch food and bed lists it didn't finish in an hour; before Away.dm's work loops shared the tick, the worst
  was 664 ms. The remaining spikes (likely .NET collections or one long work call) are a follow-up.

## Next

- Records for wild creatures and NPC towns (their lairs and spawners would hold uids instead of references).
- The waiting jobs (hunter, cook, builder, carpenter queue) through their Away.dm procs, measured like the others.
- Moods and practice while asleep, if they matter to players.
- An offline village someone else is watching stands still (no per-player track runs for it): give it a light
  track, or let a record stay a record while only another player's camera is near and nobody targets it.
- Per-region record stores for the MMO (planning/MMO_ARCHITECTURE.md): the record format is the region's.
