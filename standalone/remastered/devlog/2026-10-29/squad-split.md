# Big battles: what each fighter's thinking costs, and fighters waiting behind their front

You asked whether batching could save the server, then "Yes, split it", then "Shared chase first". Batch rendering helps only your computer's graphics card. The server's time in a big battle goes to each fighter's thinking (~half) and each soldier's steps and blows (~a quarter). The biggest single piece of the thinking was fighters chasing foes that had no free side: from ~40 s into a 1000 v 1000, up to 2,800 route searches a second. Landed as gang-wait: those fighters now close up a step or wait behind their own side.

## Needs the user

- Watch a 1000 v 1000 in the next build. Once the fronts are full, the back ranks stand right behind their front and step into gaps instead of circling the crowd. Fights get bloodier: about 30% more blows a second in those battles.
- Squads: your groups (or the units ordered together) as the division, small blocks inside it, everyone else grouped by where they stand. Not built: this was the first piece.

## Done

- Split each fighter's attack tick at 1000 v 1000 (timers on every piece, in a measurement copy only).
- gang-wait (Attack.dm): when the battle field has no room near, a box's or attack-move's fighter takes its step towards the foe if open, waits behind a unit of its side if one is there, and chases as before otherwise (water, rock, a foe). `RM_GANG_WAIT=0` turns it off.

## Numbers (windowless 1000 v 1000, base and fix side by side, from 40 s on)

| | seed 2 before | after | seed 3 before | after |
|---|---:|---:|---:|---:|
| Chasing route searches a second | 1,046 | 4 | 1,316 | 3 |
| Fighters' thinking, ms per game second | 900 | 437 | 968 | 394 |
| Real seconds per game second | 1.85 | 1.54 | 1.79 | 1.27 |

Seed 1 was a battle where the chasing never built up; nothing changed there.

What each fighter's thinking cost (ms per game second, before): the chase 482, the battle field's way 155, the box's next foe 34, and about ten small checks that cost little work but ~1.2 µs a call each (the first split put them at ~180; most of that was its own timers). Steps, bumps and blows ~456 more, which squads can't share.

Details: `reports/squad-split/README.md`, `reports/squad-split/gang-wait/README.md`.

## Later: the small checks ("Build them anyway")

- atk-guards landed 17:10: each fighter's small checks (throw, bow, capture, a beast's part, jaws, siege, down) are called only when they can apply, and the realms' answers (allied, at war) are worked out once a tick, kept until a war or liege changes.
- Exact: two shadow battles played as before and counted 0 differences in ~330,000 and ~155,000 checks a place; a same-tick check of war, truce and vassals passes (and fails without the war counter).
- Saves 36-55 ms of each game second at 1000 v 1000: each fighter's attack tick 8-14% cheaper, the battle 1-3.5% faster. Details: `reports/squad-split/atk-guards/README.md`.
