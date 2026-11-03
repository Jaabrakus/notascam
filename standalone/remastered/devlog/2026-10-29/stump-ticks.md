# Stump ticks: the cost was dying

Bleeding stumps looked expensive in big battles, but the stump tick itself costs ~20 µs. The time was the deaths it causes: a unit that bleeds out calls Death(), about 6 ms each. A dying unit rebuilt its whole look once for every piece of gear it dropped, just before it was deleted. Now it rebuilds once. Build 126.

## Needs the user

- Nothing. You said "Yes, skip it": mourning is off while moods are off (build 127).
- Next, if wanted: the body's picture (~1.5 ms a death).

## Done

- Timed inside the stump tick, and stump loops on their own: cheap either way.
- Timed every part of Death in a 500 v 500: mourning, gear drops, the body's picture.
- Fix (death-look-once, build 126): one look rebuild after a dying unit's drops, instead of one per piece. Same items, stats and look (checked).
- Mourning off while moods are off (mourn-off, build 127): no memory for every unit at each death, as nothing reads them then.

## Numbers (500 v 500, two runs at once on the same load)

| | Before | After |
|---|---:|---:|
| A death | 6.35 ms | 4.99 ms, then 2.60 with mourning off |
| Dropping its gear | 1.93 ms | 0.15 ms |
| Mourning | 2.4 ms | 0.03 ms |
| All deaths, ms per game second | 23.8 | 18.0, then 9.7 |
| Look rebuilds, ms per game second | 12.1 | 4.8 |

Details: `reports/polish-night-1026/stump-ticks/README.md`.
