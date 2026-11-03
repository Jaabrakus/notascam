# One sight grid: proposal (world-look, 2026-10-25)

A proposal for you to judge. Nothing in it is in the game. It is step B of `planning/WORLD_SIGHT_PLAN.md`, worked out
against today's code and measurements.

## In short
- Today **seven separate passes** each work out "who is near" or "who can see what" on their own: creature looks,
  attack-move looks, fog, awake land, the 3D scene, the 3D moves push, the explored map and the far view's figures.
  Together, at 200 units, they cost about 40 ms of server work a second.
- **Your theory, that they stack into hitches, is partly right.** Of 277 slow moments in today's 200-unit games, 19 (7%)
  had two or more of these working hard at once. Most hitches were one of them spiking alone: mostly the 3D ground,
  fixed today.
- **The proposal:** one unit grid, kept by the engine as units move, and one "who sees" answer, the fog's sides (already
  built once per side). Each pass reads those two instead of scanning the map itself. Awake land keeps its own wider
  circles, so nothing anyone can see ever sleeps.
- **The biggest win is a removal.** With fog on, the explored map is marked twice: by the fog circles, and again by a
  line-of-sight scan round every unit every 2 seconds. That second pass is 9 ms a second at 200 units and about 590 ms a
  second at 5,000. It can go without any grid.

## Today's passes

| Pass | Asks | How | How often | Cost, 200 units (one player) | At 5,000 |
|---|---|---|---|---|---|
| Creature looks (Monster AI.dm LocateTarget) | a foe near this creature? | engine pre-check `rm_foe_near` (~1 us), then `oview` only if yes | after each step / every guard look | 0.9 ms/s | 24 ms a tick near players (after the pre-check) |
| Attack-move looks (Attack.dm) | a foe in sight? | the same pre-check, then `oview(sight)` | attacking units' ticks | in "unit order" | grows with fighting units |
| Fog, side sight (Fog.dm) | what my side sees | circles round members' units in 16x16 cells, once per side | each 3D scene (2 a second) | 3.5 + 5.8 (the page's bits) | per side, not per player |
| Awake land (Awake.dm) | which land lives in full | squares round cameras (+24), units (32), workshops (16) | every second | small | grows with units |
| 3D scene, things (View3D.dm) | what's round my camera | `range(view)` (10 ms at the widest zoom) + a fog test per thing | each scene | 2.6, other layers 3.3 | 91 ms a scene at 5,000 in view |
| 3D moves push (View3D.dm) | where my visible units step | `range(25)` + a fog test per unit | **every tick** | 11 (one push of 84 ms) | 2.5 ms a tick for the scan alone |
| Explored map (Explore.dm) | what my units have seen | `view(5)` round every unit (line of sight) | every 2 s | 9 | **~590 ms/s** (235 us a unit) |
| Far view's figures (View3D.dm) | what my far-off units see | `view(7)` round each far unit (line of sight) | every 2 s | 3.1 | grows with far units |

Costs are from today's real-window profile (`reports/server-cost/t3d2-before`) and test-map timings
(`reports/world-look/sightgrid/sight_cost_check.dm`).

## Do they stack?
All six of today's 200-unit profiles, every tick over 100 ms (boot excluded):

| What was working hard (20 ms or more) in that tick | Ticks |
|---|---|
| Nothing named (the engine, memory paging, the hidden stat panel fixed today) | 125 |
| The 3D view alone (mostly new ground, fixed today) | 105 |
| Creature looks alone | 18 |
| Two or more together (3D + looks 10, 3D + HUD 7, HUD + looks 1, all three 1) | 19 |

Each system has its own budget (the track's 30 ms, the 3D's 10-30 ms, first steps 8 + 25 ms), and creature looks have
none. So stacking can still happen; it just isn't the main cause today. One grid makes every pass cheaper, which makes
stacking rarer. A whole-tick cap is the other half; it's in the systems map's Part 1.

## What it becomes

**1. One unit grid (engine).** For each 16x16 cell of each level, the units standing in it, with their owners. The engine
keeps it as units move, hooked where the change counters already are (every move, pick-up, drop, deletion), so it is
always exact and costs nothing between moves. A DM fallback answers from `range()` as today. It answers "the units in
this box", optionally of one owner or not of one owner. Building it from scratch in DM would cost 30 ms at 5,000 units,
which is why it must be the engine's.

**2. One "who sees" answer: the fog's sides.** Already built once per side (an alliance), already a cell lookup. Nothing
new is built; the passes below just ask it instead of working sight out again.

**3. Each pass reads them:**

| Pass | Becomes | Gives up | Saves (200 units) |
|---|---|---|---|
| 3D moves push | the grid's box round the camera; a fog test only for others' units | nothing (the same units, same order) | ~11 -> ~2 ms/s, and no 84 ms pushes |
| 3D things, other layers (units only) | the grid's box | nothing | ~3 -> ~1 |
| Explored map, with fog on | **dropped**: the fog circles (12 tiles) already mark more than `view(5)`, on every level (the fog takes all a side's units, underground ones too) | a blind unit's 5 tiles (by the fog it sees nothing) | ~9 -> ~0 ms/s; ~590 -> ~0 at 5,000 |
| Far view's figures | the grid's boxes round far units, kept to what the side sees | line of sight: it shows what the fog shows, as the detailed area already does | ~3 -> ~0.5 |
| Creature looks | unchanged: `rm_foe_near` is already exact and ~1 us | nothing | none |
| Awake land | its own squares, unchanged; may read the grid's occupied cells to build faster | nothing | small |
| Fog | unchanged | nothing | none |

At 200 units that's about 40 -> 20 ms of sight work a second for one player. At 5,000 the explored map's removal alone
is about half a core.

## Risks, and how each is kept
- **Nothing anyone can see may sleep.** Awake land never asks sight. It keeps 32 tiles round each unit, sight being 12
  (18 at most, flying and up high), and 24 beyond the camera's view. A check asserts it in every test run: every tile
  inside any side's circles is in awake land.
- **A raid marching in unseen must keep marching:** the same rule. Creatures with somewhere to go walk on in asleep land,
  as now.
- **The grid must never miss a move.** It's kept where the change counters are kept, which were proven on 911 random
  edits with units walking (0 missed). Shadow mode, like `RM_PATH_VERIFY`, works out both answers and logs any
  difference.
- **The explored map must lose nothing.** Fog circles (at least 9 tiles, at night) cover every tile of `view(5)`
  (corners at 7.1). The only loss is a blind unit, which sees nothing by the fog either. Checked by comparing both maps
  bit for bit over a session. With fog off, Explore.dm stays the only marker, as now.
- **The far view changes what it shows:** units within your side's sight instead of within 7 tiles' line of sight. That
  is your call (below).
- **Order:** the moves push keeps the scan's order, so the page and the "same as last time" check see no change.

## Proof, at each step
- Shadow mode: old and new answers built side by side and compared, counts logged, on real games.
- The moves push: identical `move3D` sends over a recorded 200-unit game.
- The explored map: identical bits with fog on; underground unchanged.
- The awake invariant check in the 200-unit and 5,000-unit runs; no creature wakes or sleeps differently.
- Real-window tick profiles before and after (200 units, a join and a pan), and the stress server at 5,000.

## Steps (each its own landing, with your OK)
1. **B1, the explored map's double marking (DM only, world-look).** Small, the biggest win at scale; needs no grid.
2. **B2, the engine's unit grid** (server-cost, with the next engine build), DM fallback, shadow mode.
3. **B3, the moves push and other layers read the grid** (world-look).
4. **B4, the far view reads the side's sight** (world-look), if you choose it.
5. **B5, Awake land reads the grid's occupied cells** (optional; server-cost, rts-feel).

## Found on the way (not part of the grid)
- **Underground, the explored map is marked through rock.** The fog builds its circles from all your side's units, also
  those underground, and marks them explored without line of sight. Underground the 3D view draws "seen before" dim, so
  cave shapes behind a rock wall within 12 tiles show dimly. Today Explore.dm's own `view(5)` marks underground by line
  of sight as well; the fog's circles mark more. Found by reading the code, not seen in a game yet.

## Your decisions (2026-10-25, through the coordinator)
1. **B1 first: yes.** With fog on, Explore.dm's `view(5)` per unit goes.
2. **Far view: what your side's fog sees**, not 7 tiles of line of sight (B4, after B2).
3. **The engine grid (B2): right after v11**, as its own engine (v12, server-cost), with a DM fallback and shadow mode;
   your install OK is asked again then.
4. **Underground: line of sight only.** The fog's circles must not mark underground tiles a unit can't see; a cave
   behind a wall stays unseen.

## For you to decide (answered above)
1. Go ahead with B1 first?
2. The far view: keep 7 tiles of line of sight round far units, or show what your side's fog sight shows?
3. The engine grid (B2): build it with the next engine (server-cost's), or wait?
4. Underground explored marks: keep the fog's circles there (cave shapes show dimly through rock), or mark underground
   by line of sight only?
