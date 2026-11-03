# jobs — 2026-10-25

Your villagers now open your own doors in the current app, and big villages lose far less to stone left on the ground.
This afternoon: workers with nothing to do now wait for their zone to call them, so a 2,000-worker village runs about
6 times faster, and a freeze when villagers pile up is fixed. Both are in the game (build 27 takes them).

## Done
- **Doors open for your villagers (in the app).** With the new engine (v7f, installed this morning), your villagers
  open your own unlocked doors as they step in. The door shuts a second after the doorway is empty, and a line of
  villagers keeps it open until the last one is through. Locked doors, enemies, allies and wild creatures are stopped,
  and a captive on a rope goes through behind its captor. All 16 door checks pass live. Both lodges build themselves
  with nobody opening the door by hand (Elf 2.7 min, Orc 3.2 min), with the banner up 15 s later.
- **Big villages: stone no longer left lying (in the game).** At 2,000 workers every quarry was dug out within 5
  minutes, and a dug-out zone let all its workers go with the stone still on the ground: 789 pieces at the end.
  - A dug-out zone now keeps a few workers until the pieces are lifted, and they're the ones with room in their bags.
  - Farmers waiting for crops no longer stand by a store. At 2,000 workers they held 7 of the 8 tiles round the
    stockpile, and carriers had nowhere to put their loads down.
  - A villager let go next to a store steps away before it starts waiting. Waiting villagers were standing on the
    store rings for good.
- **The clean-up pass:** my part of the systems map is written (reports/jobs/systems-map-entry.md). The finding: the
  settlement pass (every villager's next piece of work) is the largest uncapped block in the tick at 2,000 workers,
  about 0.7 s for one call. At 200 (your game's size) it's about 18 ms. Moving it onto the unit clock is next after
  the stockpile change.

## Numbers
Same engine, arena, 5 minutes of game time, the game before → after:

| Workers | Stone stored | Wood stored | Pieces left lying at the end |
|---|---|---|---|
| 200, a store by each zone | 986 → 1,133-1,148 (+15%) | 208 → 208 | — |
| 2,000, a store by each zone | 10,279 → 11,047 (+7.5%) | 2,472 → 2,461 | 789 → 18 |

The cost per piece stored stayed about the same.

## Done this afternoon (in the game, 17:13)
- **Workers wait for their zone to call them** (your idea: "it should be the zones or the resources letting the
  worker im ready to be gathered"). Measured first, at 2,000 workers: nearly all the time spent on villagers' next
  work went to farmers with nothing to do. Each one, every second, searched every store for seeds, among 11,000 stored
  stones. Now:
  - a farmer, woodcutter or miner with nothing to do waits and costs nothing;
  - the farm calls a farmer when a crop ripens, seeds reach a store or the season turns;
  - the wood or quarry calls a worker when trees grow back, rock opens up, or a full bag leaves a piece on the ground;
  - anyone waiting a minute looks again anyway.

  | 2,000 workers, a store by each zone | Before | After |
  |---|---|---|
  | Real time for one game tick (should be under 100 ms) | 285 ms | 48 ms |
  | Villagers' next work, per second | 2,137 ms | 79 ms |
  | Stored in 5 minutes | wood 2,451, stone 11,028 | wood 2,486, stone 11,033 |

  The game runs about 6 times faster at that size. All the checks pass: farm and wood tests, food, jobs, lodges,
  doors, clip.
- **A freeze when villagers pile onto one tile.** Today's game can put 60 villagers on one tile in a crowd at a
  single stockpile. With that many, the "step off a friend's tile" check grew until the server froze. Fixed with a
  two-line change, and every check passes.

## Done this evening (in the game at 20:3x; the next app build takes it)
- **Bigger and more stockpiles** (your plan: "whole-area stockpiles, a yard by each wood and stone zone, then haulers
  to the main stockpile"). A painted stockpile was only ever one tile at its middle, however big you painted it.
  - A painted stockpile is now its whole area. Carriers spread over it, and idle villagers step off it.
  - Each wood and stone zone paints its own yard on the village side, with no click.
  - Haulers carry the yards' goods to the main stockpile, where the workshops are. Until you set the haulers row
    yourself, it asks for one hauler for each yard holding goods.
- **Fishing zones (+ Fish)**, next to + Wood and + Stone (your "lets add fishery lodges or workzones"):
  - one fisher to each fishing spot in the zone;
  - a missing rod, net or cage is fetched from a store;
  - the catch is cleaned into meat and brought to a food store;
  - a stretch of shore with no spots wants nobody.
- **Farmers with nothing to do wait at their farm**, not in the village. In a big village they made a wall round the
  stockpile.

| Stored in 5 minutes | Before | After |
|---|---|---|
| 2,000 workers, one stockpile | wood 105, stone 219 | wood 2,472, stone 11,024 |
| 200 workers, one stockpile, stone | 994 | 1,139-1,158 |
| 200 workers, a 9 x 9 stockpile painted, stone | 799 | 1,036 |
| The fishing test, 3 fishers | (no fishing zones) | 60 food in 2.5 minutes |

- All the checks pass. The one cost: a lodge now takes 4 minutes to build itself instead of 2.7, because its wood
  goes through the yard and a hauler. Next, workshops will take their materials from any store, which wins that back.
- Store clipping is parked, as you said. Its first try is what found the freeze above.
- Next to cut: what's left of the villagers' work pass spread over ticks, then (another session's code) walking units
  being checked on every step.
- Off-duty villagers (home, tavern) wait, as you said, until gathering is right.

## Needs the user
- **Sacks and barrels:** your idea of resources in sacks and barrels, carried in carts and dropped when struck, is on
  its own card ("Resource bundles: sacks and barrels on the ground"). That session writes the design for your OK
  first. My notes for it are in reports/jobs/bundles-notes.md: what every loose piece costs today, and where a bundle
  would plug in.
- From yesterday, still open: a short game window for a picture of zones in 3D, and whether "the banner flag on it"
  meant a flag on the lodge's roof.
