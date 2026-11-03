# Glide catch-up: units no longer teleport when they fall behind

In the 3D view, units sometimes jumped ahead several tiles. The page put a unit straight on its tile whenever it was drawn more than 3 tiles behind, and a late batch of moves (0.6-2 s late) passed that. Now a unit that falls behind walks to catch up, faster the further behind it is, and jumps only on a real jump: a leap, a shadowstep, or 15+ tiles. Build 125.

## Needs the user

- Watch units walk in build 125, especially big groups and fast units after an order. Not yet checked in the real app: you were playing build 124 while it was built, so reopen the game to get it.
- A unit that falls behind now hurries for a second or two (up to 2.5x) instead of jumping. Say if that looks wrong.
- The cause underneath is still there: moves reach the page late now and then, though the server sends them every tick. Finding why is the next step if wanted.

## Done

- Found why: the server sends each unit's latest tile, not the steps in between. The page's "more than 3 tiles behind: put it there" rule was older than build 122. Build 122's queue kept units drawn about 2 tiles behind instead of 1, so the rule fired more often. Slow walkers fired it even with no late moves.
- The glide now paces each unit by how many tiles behind it is drawn. A tile the server skipped takes its real length.
- A jump counts as real when it is farther than walking explains since the last moves came. Leaps and shadowsteps still land at once while anything in view is moving.

## Numbers (offline replay of the exact page code, one unit walking, 600 s x 5 runs)

| | Build 121 | Build 122-124 | Build 125 |
|---|---:|---:|---:|
| Teleports per 100 s, moves 1.2-2 s late | ~12 | ~12 | 0 |
| Teleports per 100 s, slow walkers, nothing late | 0 | 0.4 | 0 |
| Rushes per 100 s, nothing late (0.3 s steps) | 1,042 | 29 | 0 |
| Tiles drawn behind, mean (0.3 s steps) | 1.1 | 1.5 | 1.8 |
| War Leap while anything in view moves | instant | instant | instant |

Details: `reports/polish-night-1026/glide-catchup/README.md`, replay `glide_sim.js`, output `sim.out`.
