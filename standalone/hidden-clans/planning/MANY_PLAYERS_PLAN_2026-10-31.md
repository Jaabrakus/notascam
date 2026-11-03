# One Mac, 100-200 players: the plan (load-asleep-1030, 10-31)

The owner, 10-31: "i want my mac m1 to be the sole server for maybe 100-200 people? so we have to be legendary in that
aspect." Measured with a swarm of bot players (`reports/load-asleep-1030/swarm/`, numbers in
`reports/load-asleep-1030/README.md`, "Many players on one Mac"). Plan only, except what's marked done.

## Where it stands

Bots join the real world over the browser link as the page does, take a company, get 30 more units (~34 each, an
established player) and march their whole company about every 20 s. The native server, today's game.

| players | units | server memory (today's engine, J2) | one core's load a tick | ticks a second (10 = full speed) |
|---:|---:|---:|---:|---:|
| 50 | ~1,650 | 1.3 GB | ~55% | 9.7 |
| 100 | ~3,300 | ~1.6 GB (profiled run) | ~77% | 9.6 |
| 150 | ~4,900 | (3.5 GB before J2) | 176% | 7.9 |
| 200 | ~6,600 | (6.1 GB before J2; ~4 GB expected) | 341% | 4.9 |

- **Memory is solved for this size.** Each browser player's link kept the HUD page twice (~9.7 MB a player); engine
  J2 (installed 11:19) shares it: 50 players 2.36 -> 1.26 GB. 200 players should sit near 4 GB on a 16 GB Mac.
- **Bandwidth isn't a limit:** ~4 KB/s a busy player (U4's measure) is ~6-7 Mbit/s up for 200.
- **The wall is one CPU core.** The game's DM runs on one thread. Past ~100 players with 34 units each it can't finish
  a tick in its 100 ms, and at 200 the world runs at half speed. There are also hitches of seconds when many join at
  once (and some without).

## Where the core goes, 100 players (the engine's per-proc profiler, `prof100`)

| share | what | grows with |
|---:|---|---|
| 15% | each player's HUD panel (JSON for the page, unit rows, realm lists) | players x their units |
| 13% | each player's 3D scene (moves, terrain, far eyes) | players x what they see |
| 14% | unit movement and orders (groups, pace, steps, clocks) | units |
| 4% | realm and ally checks (~930,000 calls a second) | players x players |
| 3% | fog and explored land | players |
| 2% each | progress/guide measures; room scans; combat bodies | players / units |
| 37% | a long tail of smaller procs | |

(The profiler adds ~0.1 µs a call, so tiny, very frequent procs read high; the shares, not the totals, are the point.)

About 40% of the core is **per-player view work** that every new player adds whatever their units do.

## The plan, in order

**1. Per-player views, cheaper (~40% of the load today; days each).**
- Send a player's HUD and scene only when something they can see changed, and less often when it's calm (a quiet
  view needs no 10-a-second rows). Build the world-wide parts (date, season, realms, prices) once a tick, not once a
  player.
- Encode off the game thread: gathering stays on it, but turning the rows into JSON and compressing them (json_encode
  alone is 88 ms a second at 100 players) can run on the Mac's other cores.
- Progress measures and room scans: *done 13:17 ("engine-k2" + "scans-kept"): kept chunk by chunk with an engine counter of things on turfs, 102 -> 49 ms a second at 100 players, exact.*

**2. Realm and ally answers cached (~4%; a day).** *Done 11:37 ("side-groups") and 11:52 ("realm-panel-open"): ally and realm work 151 -> 26 ms a second at 100 players.* `RemasterAllied` / `RemasterAlliedKeys` / `RemasterRootKey` run
~930,000 times a second at 100 players. Each player's allied set, kept until an alliance changes.

**3. Units nobody watches, cheaper (14% and rising with units; a week or two).** Far-unit records exist
(`FarRecords.dm`, off since 10-25: `rm_far_on = 0`): units with no player near them as ~3 KB records that bank their
time. Turning them on safely, plus coarser steps for unwatched units (`planning/NATIVE_PLAN_2026-10-28.md`), is the
lever for thousands of units.

**4. The hitches.** A tick-gap recorder that names what ran in any tick over 250 ms; then fix each (joins in bursts,
company creation, saves).

**5. More than one core: the world as several server processes on one Mac (weeks; the owner's go first).** The M1's
other cores sit idle. The MMO plan's region shards (`planning/MMO_ARCHITECTURE.md`, section 11) run on one machine
first: e.g. 4 processes of ~50 players, a player's army handed over at a region edge, realms, chat and markets shared.
It's the only lever that multiplies instead of trimming, and the biggest job.

**Expected:** steps 1-2 should bring ~150 players to full speed on one core; step 3 more as companies grow; step 5 is
how 200 stays smooth while each player grows to hundreds of units.

## How to measure

`python3 tools/runlock.py --who X --kind run -- python3 -I reports/load-asleep-1030/swarm/swarm.py LABEL --world <a
compiled game copy with ZZSwarm.dm> --steps 1,10,25,50,100,150,200 --hold 120 --units 30` (headless, no window;
`--gcdump`, `--vmmap`, `--dll`, `--server-env`). Bots don't pan the camera or fight yet, so real players cost more:
adding both is the next harness step.

## Decisions for the owner

1. Start with 1-2 (views and ally caching), then measure again? (Recommended: days, no game changes players see.)
2. Turning far-unit records on (3) changes how far units live; it needs the owner's OK.
3. Multi-process (5) is an architecture change: plan it in full before any code.
