# The battle's "hidden half": it's about a tenth

The last report said half of a big battle's server time was under no label. A measurement engine that times every game loop shows the real figure is about 10%: ~56 of ~580 ms a game second. The rest was labelled work that the tick profiler failed to count, because its count of open timed calls gets stuck about 7 seconds into a battle. Nothing in the game changed.

## Needs the user

- Pick the next speed-up. The biggest single piece is still closing in on far foes (the chase, ~68 ms a game second). The cheapest-looking one is stump ticks (~15 ms, 1-3 ms each for a few lines of code).

## Done

- Built a measurement-only engine (the v19 engine plus a per-loop timer; never the game's engine) and a measurement copy of the game.
- Ran the 500 v 500 attack-box battle, seed 1, 90 game seconds, at speed 1.
- Found that spawn() code runs from the engine's timers, not its scheduler, and timed it too (~70 ms of the walk loops).
- Wrote corrections into the native plan and the attack-checks report.

## Numbers (500 v 500 battle, ms per game second, game seconds 10-90)

| | ms | Under a label |
|---|---:|---:|
| The orders pass | 245 | all |
| Units walking, bumping, striking | 251 | ~232 |
| The shared unit clock (morale, bleeding, hunger...) | 59 | ~42 |
| Stump ticks | 15 | none |
| Everything else | ~7 | none |
| **Server time (58% of each 100 ms tick)** | **580** | **~519** |

| "other DM" in the profiler | Before | Now known |
|---|---:|---:|
| First 6 s of the battle | 42-98 | — |
| After ~7 s | all of world.cpu (~560-690) | ~56 really unlabelled |

- The ticks over 100 ms (two a second) come from the test running both sides' orders pass in one tick. The real game spreads it over ticks.
- With no window attached, the map update and disk cost nothing. Garbage collection runs between ticks, not inside them.

Details: `reports/polish-night-1026/battle-other/README.md`.
