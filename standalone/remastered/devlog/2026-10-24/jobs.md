# jobs — 2026-10-24

Raw materials first, as you asked. A new scoreboard measures wood and stone at 20, 200 and 2,000 workers, and found why
big villages stored almost nothing: villagers carrying goods home couldn't walk through their own people, so they
stood in frozen lines. That fix is in the game (your rule: units pass each other, never rest on one tile), and so are
the gather fixes: at 200 workers the village now stores 8 times the stone. Lodges get built with no clicks, and doors
went in after midnight: a shut door now stops everyone who isn't yours, on every kind of walk, and your own villagers
open your own doors as soon as the engine update is installed.

## Done
- **The delivery jam, fixed (in the game).** At 200 workers about 100 carriers stood still for minutes next to the
  stockpile, and at 2,000 almost nothing was stored. Each one's next step was a tile with one of its own villagers on
  it: own units already walked through each other on orders, attacks, guard duty and building sites, but not with a
  full bag on the way home. Now every walk passes through its own side; two units still never stop on one tile.
  Checked before and after on the exact file: clip, walking speed, formations, obey, capture, combat, and a
  5,000-unit cost run (no change).
- **Raw-materials scoreboard** (arena, 5 minutes of game time; half of each wood already growing back, as a
  village's woods are). Per wood and stone: stored per worker-hour, where the time goes (working, walking, carrying,
  blocked, idle), blows per piece stored, blows wasted on regrowing trees, pieces dropped and how long until picked up,
  pieces still lying at the end, and what every carrier is doing halfway through.
- **Make and Serve tabs hidden** until Gather is tuned. The Work tab shows Gather only; Village › Bulletin board opens
  the board itself again. Checked in a real WebKit view; the rest of the page is pixel-identical.
- **Earlier today:** the Supply chain screen (Gather / Make / Serve, one pool of villagers for zones and board orders),
  big-village slices (30,000 units: the work pass 113–127 → 26 ms), work zones, unit labels as race plus real job.

## Numbers
Stored per worker-hour, 5 minutes of game time, arena, speed 4:

| Workers | Before: wood | Before: stone | After: wood | After: stone |
|---|---|---|---|---|
| 20 | 207 | 155 | 91* | 230* |
| 200 | 55 | 4.6 | 55.8 | 141 |
| 200, a store by each zone | 49.9 | 4.5 | 96.7 | 483 |
| 2,000 (one stockpile) | 0.1 | 0 | 1.7 | 3.5 |
| 2,000, a store by each zone | not run | not run | 58.8 | 367 |

\* stored in total at 20 workers (wood 91 and stone 230, against 88 and 192 before). At 20 there was no jam to fix.

At 200 workers, before → after:
- Deliveries in 5 minutes: 66 → 522 (with a store by each zone: 62 → 647, a trip 119 s → 5.5 s).
- Wood blows wasted on trees growing back: 41% → 0%. Blows per log stored: 14.6 → 3.6.
- Pieces dug or cut and left lying at the end: 117 (106 of them for over 2 minutes) → 51 (none over 2 minutes).
  With stores by the zones, a dropped piece is picked up in 8 s (was 125 s).
- Wood stays near 55 per worker-hour: a 25 × 25 wood holds 169 trees, each gives one log and then grows back for
  about 17 minutes, so a wood like that gives about 10 logs a minute however many work it. That's the game's pace,
  kept as it is; the scoreboard shows it per zone.
- 2,000 workers with one stockpile are still stuck: a single stockpile tile has eight tiles round it to put loads down
  from. With a store by each zone, 2,000 workers stored 2,446 wood and 10,466 stone in 5 minutes (a trip 7 s). Still to
  fix at that size: 635 pieces left lying at the end, mostly in the stone zones, and 23 of 170 carriers waiting for a
  way through.

Lodges, from felling the trees to the finished lodge, with no clicks:

| Lodge | Before | After |
|---|---|---|
| Elf lodge (29 walls, 2 beds, a table, a door) | never finished: nobody orders the furniture | built in 2.7 min, banner up 16 s later |
| Orc war lodge (31 walls, 8 beds, a fire, a door) | never finished | built in 4.1 min |

- **The gather fixes (in the game):** workers pick up pieces lying in their zone before cutting new ones; haulers
  sweep the work zones; woodcutters only cut grown trees; each worker goes for the nearest tree or rock; idle villagers
  don't wait beside a store (they held carriers off it); loads go to the nearest store that takes them. Every check
  passed on the exact file before it went in. It costs about half as much per piece stored as before, for 8 times the
  pieces; idle villagers cost the same as before at 200, 5,000 and 30,000 units.
- **Lodges build themselves (in the game):** buildings order their beds, tables and doors from the carpentry without
  over-ordering; a door (100) is too heavy to lift with an axe (25) in an Elf's or a Human's bag (120 / 110), so the
  worker puts the axe down on the stockpile, carries the door, and goes back for the axe.
- **Doors (in the game; your choice, (a)).** Live now: a shut door stops every unit on every kind of walk. Before, it
  only stopped a unit's own ordered steps, so wandering creatures, work walks and captives on a rope went through
  shut, locked and enemy doors. Until the engine update is installed, that includes your own villagers, because the
  engine's route planning treats the door as shut. A door you open by double-clicking lets everyone through as before.
  With the engine update (waiting on your OK): your villagers open your own unlocked doors as they step in, and the
  door shuts a second after the doorway is empty. A line keeps it open until the last one is through, and a captive
  on a rope goes through behind its captor. Locked doors still stop everyone. The 3D view shows the door open or shut.
- Checked on the exact files: all 16 door cases with the rule on, with it off, and in the live setting; route
  planning and the walking rule agree (0 differences). Walking speed, formations, clip, raids, siege, combat and
  capture are the same as before. Lodges with nobody opening the door by hand: Elf 2.7 min, Orc 3.2 min, banner up
  15 s later.

## In progress
- **Big villages, next:** at 2,000 workers, pieces left lying in the stone zones (635 at the end) and carriers waiting
  for a way through (23 of 170). Measured first, then fixed only where it doesn't raise the cost per piece stored.

## Needs the user
- (Done 10-25: you OK'd the engine update v7f, and your villagers open your own doors in the app. See
  devlog/2026-10-25/jobs.md.)
- A picture of zones in 3D needs a short game window. Say in the morning if that's OK; the pictures above are WebKit
  captures of the HUD, with no game window.
- "The banner flag on it": the Claim banner now goes up on a free floor tile inside the finished lodge. Say if you
  meant a flag flying on the lodge's roof in 3D.
- Make and Serve come back once Gather is tuned. Say if you want them sooner.
