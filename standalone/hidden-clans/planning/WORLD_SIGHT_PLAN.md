# World sight: one sight system for the whole world

The user, 2026-10-24: "should we make the world a living player so we can ask the world have we seen this unit before?"
Then: "plan the shared world sight system with world-look: team sight computed once, a who-sees-what grid, seen-before
memory per team." Owners: world-look (fog: Fog.dm, the page's fog drawing), server-cost (the engine natives, timing).

## Why

Today sight (Fog.dm) is worked out by each player on their own, every 3D tick (about twice a second):

- `RmFogSources` gathers the player's units and workshops **and every ally's** (allies share sight), then `RmFogTick`
  builds the circles and buckets them into 16x16 cells. With 10 allied players, the whole alliance's sight is built
  10 times every half second, identically.
- "Can I see this tile" (`RmFogSees`) is asked per player, per thing in view, by the 3D list, attacks and clicks.
- What was seen is remembered per player: the explored map (`remaster_explored`, Explore.dm) and remembered buildings
  (`rm_fog_mem`). While allied, every member marks the same circles into their own copy.

At one player it costs about 10 ms a second at 200 units (after the 2026-10-24 savers: fewer string keys). It grows with
players times allies: the MMO case (kingdoms of many players) is where it hurts.

## What it becomes

A **side** is everyone who shares sight: players with the same alliance root (`RemasterRootKey`, Realms.dm), which is
exactly who `RemasterAllied` already says shares sight. A player alone is a side of one.

1. **Side sight, built once.** A world-level datum keeps, per side: its circles (x, y, z, r, the unit, its owner), its
   cell buckets, a version number, and the tick it was built. A player's `RmFogTick` asks for its side's sight; the first
   member to ask in a tick builds it from all members' sources, the rest reuse it. Circles carry their owner, so the
   page still gets the follow-ref only for the viewer's own units (`RmFogBits`), exactly as now.
2. **Who sees what.** A world grid of 16x16 cells -> the sides with a circle reaching that cell. "Does anyone see this
   tile?" is one cell lookup and an exact circle test only for the sides listed. Uses: creature AI (whether a player can
   see it), Awake.dm (areas no side is near can sleep), and later the stress server's per-side counts.
3. **Seen-before memory per side.** The explored map and remembered buildings kept once per side, marked once per circle
   that moved. Saved per side in the world save, keyed by the side's root; each member's own save keeps a copy, so a player
   who leaves an alliance keeps what they had seen. Loading merges members' maps (bitwise OR: no one loses anything).
4. **In the engine.** The circle bucketing, the "sees" test and the circle marking (rows of 16-bit chunk words) move into
   the engine (engine/native, like the route search), each with its DM fallback of the same name, bound only when the game
   declares it.

## Order, each step proven before the next

| Step | What | Proof | Who |
|---|---|---|---|
| A | Side sight built once per tick and shared by members (DM, no engine change) | old-vs-new: every member's `RmFogLook` answer and `RmFogBits` output identical, alone and in alliances of 2-10 (arena test) | world-look, server-cost reviews |
| B | Who-sees grid; Awake.dm and creature AI ask it | answers equal a brute-force check on random tiles; no creature wakes or sleeps differently | world-look + server-cost |
| C | Seen-before memory per side, with save migration | members' merged maps contain every bit each had; save/load round trip; leaving an alliance keeps a copy | world-look |
| D | Engine natives for B and A's hot parts | shadow mode: DM and engine answers identical on real games (like `RM_PATH_VERIFY`) | server-cost |

Measured at each step (tools/tick_profile.py `fog tick`, `3d/things`; the stress server's simulated players when it
exists): fog ms per second for 1, 5 and 20 allied players at 200 units each.

## Kept as they are

The circles' sizes and rules (`RmFogRadius`: 12 tiles, +3 high or flying, -3 at night unless the race sees in the dark),
the page's soft drawing of circles and explored bits, underground's own line of sight (View3D.dm), the host's fog switch,
and what other players' units you can see.

## Open questions

- Shared memory between allies: today an ally's explored map only holds what was seen while allied. With per-side memory,
  joining an alliance would merge what each member had seen before. Fine, or keep "only while allied"?
- War between former allies: does the copy each keeps include buildings remembered while allied? (Yes today.)

## world-look's review (2026-10-24)

The plan is right, and I'll take A and C. Changes, from reading Fog.dm, Realms.dm, QoL.dm and Awake.dm against it:

1. **Sides are well defined.** `RemasterRootKey` walks the liege chain (`rm_lieges`, up to 8 levels), so "same root" is
   a true grouping: if A shares with B and B with C, A shares with C. A root can change at any moment (a vassal swears
   or leaves), so a side is regrouped by root key at every build, never cached across builds.
2. **"Built once per tick" won't share anything.** Each player has its own `RemasterTrack` loop, with spread pauses.
   Members' 3D ticks almost never land on the same `world.time`. Rule instead: a side's sight is reused while it is
   younger than one track period (the 3D tick's own interval); the first member to ask after that rebuilds it. Other
   members see sight up to one period old, the same age a player's own sight already is between its own ticks. A's
   proof compares old and new built at the same moment, plus a check that a member never uses sight older than a period.
3. **What moves to the side, what stays with the player:**
   - side: the sources (members' units and workshops, and the workshop list `rm_fog_shops`), the circles, the cells,
     `rm_fog_near`, the answer cache `rm_fog_ask`, `rm_fog_marked` (each circle marks once per side) and `rm_fog_ver`;
   - player: `RmFogBits` and its cache key (they follow the viewer's camera window), and the follow-refs in `c`. Each
     circle keeps its owner player, so `RmFogBits` sends the ref only when owner == the viewer, as `C[5]` does now.
4. **B must not decide what sleeps.** Awake.dm keeps land awake 32 tiles round units, 16 round workshops and 24 beyond
   the camera, and sight is only 12. Putting land to sleep by sight would stop creatures that are near but unseen
   (a raid marching in just outside sight). Awake can read the side's source buckets to build its map faster, with its
   own radii unchanged. No code asks "does anyone see this tile" today, so B waits until something needs it (creature
   AI, the stress server's counts). Order: A, C, D, then B when it has a user.
5. **C needs no new save format.** `remaster_explored` and `rm_fog_mem` are already saved with each player (not tmp,
   so `Player.Write`). Simpler than per-side world-save entries keyed by root (which would need re-keying whenever roots
   change):
   - while allied, every member's `remaster_explored` / `rm_fog_mem` points at the side's one shared list, so marking
     happens once and everyone has it;
   - a side forming (or a member joining) OR-merges the members' lists into the shared one;
   - leaving or a war split deep-copies the shared list into the one who goes, before anyone marks again, so each
     keeps everything seen up to the split;
   - a save writes each member's copy as today; on load, the side forms again by OR-merging the copies.
   No migration, the world save stays as it is, and both of today's behaviours hold. Proof: merged maps hold every bit
   each member had; save/load round trip; leaving keeps a full copy; after a split, the two sides' marks never leak
   into each other.
6. **The open questions, with my lean (the user decides):**
   - joining merges what each had seen before: I'd say yes, since it falls out of the shared list and matches "allies
     share sight". "Only while allied" would need each member's own list plus a shared one, double the marking;
   - at war, each keeps everything up to the split, remembered buildings included: that is today's behaviour, and it's
     what copy-on-split gives.
7. **The page doesn't change.** The fog data (`s`, `c`) keeps its format, so the page's fog drawing (mine) needs nothing
   for A to C.
8. **Tests:** `tests/fog_test.dm` (15 checks; ally sight and the save round trip already in it) stays green at each step.
   A new arena test does old against new for sides of 1, 2, 5 and 10 players, members ticking at different times.

## Status (2026-10-24, world-look)

The user's answers: joining merges everything, and at war each keeps everything up to the split. **A and C are built**
(Fog.dm) and proven: `tests/fog_sides_check.dm` (old vs new, sides of 1 to 10, own clocks, a leave; 10 players with 200
units: 6 ms a round each building its own, 1 ms each side once) and `tests/fog_memory_check.dm` (7/7). check_fog 15/15.
Not in an app build yet. B waits for a user, D is server-cost's.

## Step B worked out (2026-10-25, world-look)
The proposal for the user: `planning/ONE_SIGHT_GRID.md`. One engine-kept unit grid plus the fog's sides as the one
"who sees" answer, read by the 3D moves push, the 3D scene's other layers and the far view. The explored map's double
marking (fog circles plus Explore.dm's `view(5)` per unit) goes first. Awake land keeps its own radii.
