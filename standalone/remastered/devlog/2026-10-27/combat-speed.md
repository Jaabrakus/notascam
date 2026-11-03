# Second pass: combat speed (combat-speed, 10-27)

The rest of a big fight's server time is now mostly route searches. That is the engine's own work, and no exact
speedup of mine can reach it. What's left on my side is small: about a fifth of the morale tick. No landing this
pass. The findings, with numbers, are below, and two decisions are for the owner.

Status (08:40): nothing of mine running, no lock held, one work clone (`reports/polish-night-1026/combat-speed/work/`,
today's game). Battle timings wait while the 2,000-worker run (GsRun2000S) holds the Mac.

## Where a big fight's time goes now

Profile of last night's candidate (= today's combat code), 250 v 250, per game second, from
`tests/cs-b-pc250-foe-checks-tick-profile.log`:

| Part | ms per game s |
|---|---:|
| time no label covers ("other DM") | 494 |
| attack orders' tick (orders track) | 422 |
| of it: approaching the foe (route searches) | 338 |
| morale tick | 118 |
| walking and bumping | 90 |
| strike chain (all of it, after last night's fixes) | 50 |
| throw check (fixed last night) | 44 |

- **"Other DM" is first steps.** A slow tick comes every 5 ticks: 280-350 ms, of which the labels explain about
  120 ms. That is the battle test's order cadence. Units given an attack order take their first step in a batch one
  tick later (`RmFirstLater` → `RmFirstGo` → `RemasterAttackTick` → route search), and no top-level label covers that
  batch. So with the orders track, attack ticks and their route searches are roughly 800 of the ~1,100 ms a game
  second at 250 v 250.
- **The recurring ~450 ms worst tick** is that batch plus the morale ticks. In every slow tick the morale ticks are
  41-90 ms, because every fighter's tick falls on the same beat.
- **Garbage collection is small:** 4-14 ms a second of pauses (the engine's own log), at 110-150 MB a second
  allocated.

## The morale tick, measured

Micro-benchmark on today's game (`reports/polish-night-1026/combat-speed/tests/cs_micro.dm`, one fighter with 80 units
within 4 tiles, best of 7):

| Part | µs |
|---|---:|
| whole morale tick | 223 |
| its count of friends and foes: walking the list | 10 |
| + the alive / awake checks | +27 |
| + the knocked-out check (a proc call) | +23 |
| + the war/alliance check on each foe (`RemasterHostile`, about 40 foes) | +103 |
| the rally check (looking 6 tiles round for a royal) | 18 |

The exact savings left: inline the knocked-out check (about 20 µs), check `IsRoyal` first in the rally look (a few
µs), and inline the per-foe hostility checks (about 30 µs). The last one copies the hostility rules into Morale.dm, so
a later change to them could miss the morale count. Altogether about 20% of the morale tick: ~25 ms a second at
250 v 250, and 10-18 ms off each slow tick. I left it unlanded. It's small against the route searches, and the
copied rules are a trap. Say if you want it anyway.

Other helpers in a blow, measured: the call for help's own code is 5 µs (its cost in a fight is the helpers' route
searches); `range(8)` 62 µs; `RemasterArmourFactor` 7 µs; `RemasterBodyHealth` 9 µs.

## Needs the owner

- **Spread the morale ticks.** Every fighter's 1-second morale tick starts at first contact, so in a block melee they
  all land on one tick (41-90 ms of each slow tick at 250 v 250). Giving each unit its own offset within the second
  smooths that out. It changes when morale moves by up to a second, so it's a rule change.
- **Fewer route searches.** A unit chasing a foe searches a route again on its attack ticks. Reusing a route while
  the foe stays near its end would cut the biggest cost, but units would take slightly different paths. That's a
  behaviour change, and it's engine-side work.
- **Still open from last night:** the battle table's "fell into bleed-out after the fight" (0.5 → 1.2 a fight, no
  code path found). To settle it: today's game against today's game with combat-speed-1 and -2 undone, 60 fights
  each. That's a long battery, so it waits until the Mac is free. Want it run?
