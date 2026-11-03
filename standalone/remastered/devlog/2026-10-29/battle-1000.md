# 1000 v 1000: the lag, and fighters led to the front

You watched 1,000 a side in the real game: it ran at about 30% of real time, and the first minute at about 10%. Nearly all of it was the server's game script, and most of that was fighters searching routes to foes deep in the enemy block. The battle field now reaches 40 steps instead of 16 (engine v20), and box and attack-move fighters use it at any distance. Build 128.

## Needs the user

- Watch a 1000 v 1000 in build 128. The test scene now runs orders at a real player's pace (it ran them 2.5x as often before).
- Big battles look a little different: the back ranks wait their turn behind the front instead of running round the crowd. Say if you'd rather they flank.

## Done

- Measured the real app (measurement engine, tick profiler, 3D page probe) and a windowless 1000 v 1000.
- Engine v20: the field's reach is 40 (RM_FIELD_REACH; 16 as before).
- Game: box and attack-move fighters take the field at any distance; a clicked foe is still chased.

## Numbers (windowless, same-time pairs)

| | 1000 v 1000 before | after | 500 v 500 before | after |
|---|---:|---:|---:|---:|
| Route searches when closing in, ms per game second | 383 | 42 | 77 | 1 |
| Attack ticks, ms per game second | 691 | 442 | 194 | 132 |
| Real seconds per game second | 2.27 | 1.97 | 1.08 | 1.08 |

Real app before (server ms per game second): attack ticks 2,067, walking and blows ~300, your HUD and 3D ~230, timers ~90, GC ~125.

Details: `reports/polish-night-1026/gang-far/README.md`.
