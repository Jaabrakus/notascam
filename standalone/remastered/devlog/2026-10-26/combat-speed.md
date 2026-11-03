# Polish night: combat speed (combat-speed)

Big fights cost the server less, with every blow the same. Nine behaviour-identical changes landed in two patches
(combat-speed-1 at 00:13, combat-speed-2 at 01:42). A blow costs about a third less, a big melee's DM time per tick about
16-25% less, and under load a 250 v 250 now keeps real time where it fell to 0.63x. The worst tick of a quiet
250 v 250 (~450 ms, a recurring spike) is unchanged. No combat number, rule, timer or step order
changed.

## Status (10-27 02:08): DONE

- Landed: combat-speed-1 (00:13) and combat-speed-2 (01:42). Nothing of mine is running or in the land lock; the
  work clones are removed. Staged and not landed: nothing (the first help-scan was dropped; see Done).

## Done

- **combat-speed-1 landed** (23:57-00:13; gate compile, jscheck, hudjoin, combat 32/32, walk_latency 5/5, clip 11/11,
  obey 32/32, stumps 23/23; restore point `restore-points/before-polish-combat-speed-1-20261026-235704`). Seven parts
  (`reports/polish-night-1026/combat-speed/land-1/README.md`):
  - the strike chain skips measuring the foe on calls where the swing timer stops the blow (4 of 5 calls in a melee);
  - body health and limb ranks read a unit's fields, not 24 lookups by name;
  - a swing checks its weapon moves without building lists and words;
  - a blow works out armour only for the part struck;
  - a look round (morale tick, attack-move foe search, surround count) settles each realm's war and alliance once;
  - the bleed check finds dagger experts through the unit grid.
- **combat-speed-2 landed** (01:29-01:42, the same gate; restore point
  `restore-points/before-polish-combat-speed-2-20261027-012926`). Two parts (`land-2/README.md`):
  - the throw check looks in the pack before looking round for a clear line;
  - a call for help checks each friend's quick conditions before searching the realm's whole unit list.
- **One part dropped:** the first version of the help change took nearby friends from the unit grid. The units are the
  same, but they come in another order, and helpers answering in another order step to other tiles. The exact harness
  caught it, so the landed version keeps the old search and only reorders the checks.
- **The exact harness was not exact on today's game, and is now.** Three things outside the dice moved units:
  - the first-step budget, which is wall time;
  - the tick ledger, also wall time;
  - a step blocked by a unit side-steps with `step_rand` (Chains/Bump.dm), and that draws on the engine's own random
    numbers, which `rand_seed` doesn't set.

  So the same base gave 2-3 different logs. The harness now resets both budgets before every call, and has that one
  side-step take the first free tile in a fixed order, the same in every game it compares. Base run twice now gives
  one log.

## Numbers

**Results unchanged.** Exact harness (`reports/polish-night-1026/combat-speed/tests/cs_strikes.dm`): one proc, seeded,
60 pairs (8 weapon styles, 3 armour levels, levels 1-60, NPC orcs, non-lethal fighters, every morale state, surround,
cleave, throws, calls for help). Both units' full state is logged after every call. Today's game before both landings
vs all nine changes:

| Seed | Facing | Lines | Blows / blocked calls / throw checks (throws) | Result |
|---|---|---:|---|---|
| 5 | off | 9,375 | 3,374 / 3,372 / 2,334 (15) | identical |
| 9 | on | 8,902 | 3,146 / 3,144 / 2,317 (19) | identical |
| 13 | off | 8,510 | 2,966 / 2,964 / 2,285 (18) | identical |
| 17 | off | 8,950 | 3,176 / 3,173 / 2,307 (14) | identical |

Checks on all nine: the gate's combat 32/32, clip 11/11, obey 32/32, stumps 23/23 and walk_latency 5/5 (twice, at
landing). Throwing test: the expected 5 lines. Defence test: `failures=0`. Morale, facing, parry, kit armour,
surround, underdog, bleed-out and falls all pass (`runs/chainQ.log`).

**Battle table** (`tests/battle_morale_check.dm`, speed 4, head-on / flank / rear, 10 each; two runs of 30 a side,
pooled):

| Measure | Before (60 fights) | After (60 fights) | Welch t |
|---|---:|---:|---:|
| fight length, s | 161.1 ± 49.3 | 146.5 ± 36.7 | -1.84 |
| deaths | 26.1 ± 6.5 | 24.3 ± 5.6 | -1.67 |
| knock-outs | 0.9 ± 1.2 | 1.0 ± 1.1 | +0.55 |
| limbs lost | 71.4 ± 7.3 | 69.2 ± 5.7 | -1.85 |
| crushes | 17.5 ± 3.5 | 18.5 ± 4.7 | +1.35 |
| crits | 85.5 ± 9.8 | 84.2 ± 11.5 | -0.68 |
| fell into bleed-out after the fight | 0.5 ± 0.7 | 1.2 ± 1.1 | +4.02 |
| side A wins | 35 of 60 | 43 of 60 | |

Battles can't be replayed blow for blow (procs due on one tick wake in no fixed order), so this table checks the
spread, not the blows. Six rows are within noise. Two base runs differ from each other as much: fight length 155 vs
167 s. The last row is the exception: about 0.7 more units a fight fall into bleed-out in the 90 s after the batch's
last fight ends. I found no code path for it: every skipped step is a no-op on a blocked call in the old code too, and
the war memo gives the same answer as before. My guess: the server keeps up better, and the budgets that cap
steps per tick by wall time let units act sooner. But that's a guess, so it's under "Needs the owner".

**Faster.** Interleaved pairs at speed 1, base vs all nine. Server CPU comes from `ps` (load-proof); "DM per tick" is
`world.cpu`, the DM share of the 100 ms tick. Chain K: 3 pairs, load average ~10-50 from other sessions.

| Test | Measure | Before (3 runs) | After (3 runs) | Ratio |
|---|---|---|---|---:|
| 250 v 250, 120 game s | server CPU, s | 159.2 / 156.0 / 132.0 | 119.8 / 142.8 / 124.1 | 0.86 |
| | mean DM per tick | 88.7 / 92.6 / 72.1 % | 58.3 / 83.5 / 62.7 % | 0.81 |
| | p95 tick, ms | 409 / 410 / 358 | 245 / 383 / 267 | 0.75 |
| 100 v 100, 150 game s | server CPU, s | 107.0 / 83.7 / 96.4 | 82.0 / 110.2 / 76.2 | 0.94 |
| | mean DM per tick | 27.4 / 15.3 / 27.2 % | 13.1 / 24.7 / 11.9 % | 0.71 |
| | p95 tick, ms | 102 / 62 / 103 | 47 / 86 / 48 | 0.73 |
| | ticks over 100 ms (of 1,499) | 78 / 8 / 77 | 1 / 42 / 1 | |
| exact harness (chain L), best of 6 | µs a blow, with its blocked call | 613 / 403 / 369 | 281 / 234 / 260 | 0.63 |
| exact harness, quieter spell (round 1) | the same | 301 (301-321) | 204 (204-220) | 0.68 |

Chain O, 3 more pairs (load swung from ~5 to ~40; pair 1 ran in the worst of it). "Fight worst" counts from 1 s in:
the first sample is the tick that made the units, 2-7 s on both sides.

| Test | Measure | Before (3 runs) | After (3 runs) |
|---|---|---|---|
| 250 v 250 | server CPU, s | (missed) / 121.2 / 109.6 | 122.1 / 128.6 / 99.9 |
| | mean DM per tick | 151.9 / 72.0 / 62.4 % | 59.1 / 77.3 / 50.1 % |
| | fight worst tick, ms | 2,652 / 482 / 468 | 444 / 541 / 371 |
| | fight p99 tick, ms | 1,319 / 452 / 384 | 352 / 475 / 317 |
| 100 v 100 | server CPU, s | 114.8 / 80.1 / 67.1 | 105.8 / 69.7 / (missed) |
| | mean DM per tick | 44.1 / 18.3 / 14.9 % | 31.4 / 14.4 / 17.7 % |
| | fight worst tick, ms | 992 / 121 / 137 | 481 / 224 / 135 |
| | fight ticks over 100 ms | 156 / 14 / 8 | 106 / 14 / 2 |

All six pairs (K and O), median of the pair ratios after/before: mean DM per tick 0.84 at 250 v 250 and 0.75 at
100 v 100; server CPU 0.91 at 250 v 250. Under load (pair 1) the new code holds up far better: 250 v 250 kept real
time (1.00 real s per game s against 1.58), with a worst fight tick of 444 against 2,652 ms. On a quiet Mac the worst
tick at 250 v 250 hardly moves (~370-540 ms on both sides). The 5 worst ticks sit within a few ms of each other
(482, 481, 480, 476, 474), so a recurring spike sets it, not the blows. My reading is the morale ticks that all fall
on one tick (see "Needs the owner"), but I haven't measured that.

**Cost per blow and per fighting unit per tick** (for the MMO scale, from the means above):

| | Before | After |
|---|---:|---:|
| one blow, with its blocked call (harness, quiet best) | ~300 µs | ~200 µs |
| DM time per fighting unit per tick, 250 v 250 | 0.17 ms | 0.14 ms |
| DM time per fighting unit per tick, 100 v 100 | 0.12 ms | 0.08 ms |

At 0.14 ms a unit, a 100 ms tick holds about 700 fighting units with nothing else running. That is the ceiling for
one server process. The worst tick at 250 v 250 (~450 ms, recurring) is the next thing to cut for big battles.

Where the rest goes (profiles, 250 v 250, per game second): the attack-order tick 422 ms, of which the engine's route
search is 338 ms (not touched); the morale tick 118 ms; the strike chain about 50 ms; allocation 171 MB/s.

## Needs the owner

- **Bleed-outs after a battle**: in the battle table, about 0.7 more units a fight fell into bleed-out after the
  fight than before (1.2 vs 0.5, in both runs of the new code). Everything else matches. I found no code path for it.
  Should someone check it at speed 1, or with more fights, before the next build ships?
- A design question, not a speed fix: in a block melee every fighter's morale tick falls on the same tick (they all
  start at first contact), which makes 1-second spikes. Spreading them out would change when morale moves, so it's a
  rule change. Not touched.
- The engine's route search is now the biggest cost in a big melee (338 ms a game second at 250 v 250). It's the
  engine's own code, outside polish fixes.
