# Units: from ~100 KB each to ~10 KB live, ~300 B as a record

The user, 2026-10-24: "i want this game to be like 1 gb in memory", "how do we get 10kb per unit", "their must be a way to
compress it", "so how would we do this". Measured (tests/memory_report.dm in the arena, engine/native/RmMemory.cs): a
Dwarf costs ~100 KB of heap once the first ones' caches exist (200 more Dwarves: +20 MB); it holds ~134 values of its own
and ~22 lists. The world's goal (memory unit-scale-30k): 30,000 units a world, 1,000,000 player units in the MMO, real
units only where watched.

## Step 0: where the 100 KB goes (measure first)

The report also counts sleeping procs (the scheduler's delay queue) and engine entities, so per unit: values, lists,
sleeping procs, entity. Arena run, 200 and 400 Dwarves. Nothing changes in the game.

## Step 1: one shared loop per job, not eight loops per unit

`StartAllProcs` (Creatures/Mob Procs.dm) starts, per unit, `while(1)` loops that sleep and run a body: Hunger (400),
Tiredness, Bleeding, Heal, Bed, LevelUp, Regen for some races, WalkTo (the step loop). Each body sleeps only at its timer
(checked: one `sleep` each; Bed has two, to review), so each body can run from a shared clock.

- `Code/Remastered/UnitClock.dm`: per job a schedule of (unit, next due); one loop per tick runs the due bodies and books
  each unit's next one. A unit keeps its own phase (its first due time is when its loop would have woken), so every unit
  gets hungry, tired, bleeds and heals on the same ticks as today.
- The bodies stay where they are, split from their `while(1) sleep()` into a `...Tick()` proc. `StopDouble` keeps one
  entry per unit.
- WalkTo last: a step schedule by tick (units walk at their own `RemasterStepDelay`), the same steps on the same ticks.
- Also CPU: no proc wakes for a unit with nothing to do; dead and deleted units fall out of the schedule.
- Proof: a fixed group of units run for an in-game day old vs new: each body's runs per unit and their ticks equal (an
  event log), and hunger/tiredness/blood/HP trajectories within what the random rolls allow; the obey, care, doctor,
  stump-care and combat checks pass.
- Original code (Mob Procs.dm, Health.dm, Leveling.dm): the coordinator decides; one change, its own restore point.

## Step 2: values packed in the engine

A unit's own values are a `Dictionary<string, DreamValue>` (~40 bytes an entry). The engine gives each type's vars a slot
number and keeps an object's own values as a small array of (slot, value) pairs, and doesn't store a value equal to the
type's default (reading falls back to the default, as now). ~134 values: ~5 KB with overhead -> ~2.7 KB, and less where
New() sets defaults. Proof: every arena check and world run; a fuzz test of set/get/vars-list/savefile against the
dictionary.

## Step 3: lists made when first used (game code)

Per-unit lists made at birth (`var/list/x = list()` on mob/Monsters and in New) that most units never fill: null until
the first add. The biggest ones first, found by the report (list counts by owner var).

## Step 4: the engine entity

Every movable is also an engine entity (transform, sprite, network state) for the 2D map, which the 3D view hides. See
what it costs (Step 0); a lighter one, or none in 3D, would also cut what every client is sent. The riskiest step; only
if Step 0 shows it matters.

## Step 5: records for units nobody is near (the million)

- A unit far from every side's units and workshops (Awake.dm's chunks), out of combat, not on a caravan or raid, for some
  minutes becomes a **record**: its type, position, owner key, the values that differ from the type's, its items (as
  records), its job and orders. A few hundred bytes, kept per region.
- When anyone's units or camera come near the region, records become units again, with their loops booked (Step 1).
- Records still live: a region's records get batch catch-up every few minutes (eat, work, grow, age), as Away.dm already
  catches a village up on the time its player was away.
- Saves already store units as records; the record format is shared with the saves.
- Proof: round trip (unit -> record -> unit equal: values, items, lists, orders) for every race and job; a long world run
  with regions sleeping and waking; raids, caravans and towns behave the same.

## Expected

| | Today | After 1-3 | After 4-5 |
|---|---|---|---|
| A live unit | ~100 KB | ~10-15 KB | ~5-10 KB |
| A unit nobody is near | ~100 KB | ~10-15 KB | ~300 B (a record) |
| 30,000 units | ~3 GB | ~0.4 GB | ~0.1 GB |
| 1,000,000 player units | not possible | ~12 GB | ~0.5 GB (20k live + records) |
