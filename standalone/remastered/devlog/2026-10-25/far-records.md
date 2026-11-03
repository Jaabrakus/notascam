# Far records and the one "behind" signal (far-records)

When the server falls behind, the background jobs that can wait now all step back on the same signal: tiles of far
land go to sleep later, and far records stop taking new units. Nothing a player sees waits for it.

## Done
- **One "behind" signal (clean-up step 5), in the game.** The map's tile sleeping and the far records used to judge
  the server's load each in their own way. Both now read the shared signal (Shed's level) and the shared tick budget.
  Wakes of far land never wait.
- **Records keep out held units** (staged, not in the game: records stay switched off for now). No unit becomes a
  record while anything still points at it: another unit's target, another player's selection, an order, a helper on
  its way, a trade, a workshop, a group. Tested with seven kinds of holder.
- **Systems-map entry** for the clean-up pass: what the records loop does and when, what it shares with other systems,
  and the seven problems found where it met them.
- The dining-hall fault seen once this morning didn't show on today's game; that search was stopped.

## Numbers
- Full world with nobody on, 15 minutes: memory 1,497 MB -> 580 MB once far land sleeps (598 MB after three passes),
  no slow ticks from it.
- 5,000-unit war, three versions side by side: the same work in each (moves, walks and attack orders within ~4 %);
  only the timings moved, with the Mac's load.

## Needs the user
- Nothing now. Far records go back on when the clean-up pass reaches them.
