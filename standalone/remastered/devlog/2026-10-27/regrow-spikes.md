# regrow-spikes: the once-a-run freeze in big villages

## What it was

After the regrow redo (build 67), a 2,000-worker village froze for 1.3-1.5 s about once a run, near the end, once the
woods were felled. The cause was not the regrowing. It was a list of "parked" workers (workers with nowhere to walk),
which the game looks over every 4 ticks. A worker went on the list each time it parked and never came off while it
stayed parked. Planting and tending saplings step by step makes workers park, set off and park again all the time, so
the list filled up with about 13 copies of every worker (up to 43,000 entries for 2,000 workers). Copying a list that
big every 4 ticks cost a few ms each time, and about once a run it cost a whole second.

## What changed

The look over the parked list now reads each worker once, and only the first copy is kept. Workers do exactly what
they did before: the same ones set off, in the same order, at the same moment. No regrow number or rule changed.

## Numbers

2,000 workers gathering, worst tick (ms, speed 4), before -> after, five pairs taken in turn:

| pair | 1 | 2 | 3 (Mac busy) | 4 | 5 |
|---|---|---|---|---|---|
| worst tick | 1465 -> 878 | 1479 -> 527 | 3760 -> 2148 | 2784 -> 694 | 1573 -> 591 |
| average ms/tick | 212 -> 187 | 195 -> 186 | 261 -> 416 | 228 -> 208 | 281 -> 193 |
| pieces stored | 21,364 / 21,319 | 21,289 / 21,327 | 21,310 / 21,322 | 21,391 / 21,271 | 21,330 / 21,310 |

The parked list now holds at most about 2,100 entries for about 2,000 workers. Each look takes 7 ms or less, where it
used to be 4-21 ms with one 967 ms look. At 200 workers nothing changes (average 17-20 ms/tick both ways).

Regrowing, before and after:

| | before | after |
|---|---|---|
| a sapling nobody tends grows in | 30.8 min | 30.8 min |
| a tended sapling grows in | 15.8-16.6 min | 16.0-16.3 min |
| 64-tree wood, 30 min, 5 workers: wood stored | 334, 339 | 334 |
| saplings planted / grown back | 64 / 64 | 64 / 64 |
| workers off the zone / pieces left lying | 0% / 0 | 0% / 0 |

Staged as `regrow-spread` (reports/polish-night-1026/regrow-spikes/fix/), not landed. Every regrow, jobs, yield,
gathering, lodge, obey, clip, combat, stumps and walk-latency check passes on the fixed copy.

Do you want big villages tested at 5,000 workers next, to see whether any other once-a-run freeze is left?
