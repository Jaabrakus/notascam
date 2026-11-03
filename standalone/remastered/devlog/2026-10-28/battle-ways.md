# Battle ways: everyone finds a place to fight

In big battles, fighters now walk to the nearest free spot beside an enemy and gang up on whoever is there. Before, each one went the long way round the crowd to the one foe it had picked. The game's engine works out those ways for the whole battle at once, so this costs less than before, not more. Build 116.

## Needs the user

- Watch a big battle in build 116. Windowless tests say the fighting about doubles at the same server cost, but nobody has watched it in the game window yet.
- Next, if wanted: find what the server's unlabelled time in a big battle is, and the attack box's full look-over (about 9 ms a tick).

## Done

- The engine got the battle field (engine v13). For each side and each part of the map it keeps how many steps every tile is from a free spot beside a standing foe, and refreshes that twice a game second.
- Fighters with a foe they picked themselves (an attack-move, an attack box, Attack-then-click) follow that field. They fight the foe beside them that most of their friends are already on, then the weakest.
- A foe you click on its own is still chased. If it has no free side, your unit fights whoever is beside it meanwhile and goes back when that one falls.
- When a box's foe falls, the next pick is one beside it or near it, instead of a look over the whole box.

## Numbers (500 v 500, 90 game seconds, no window)

| | Before | After |
|---|---:|---:|
| Time spent closing in | 276 ms a second | 83 ms a second |
| Server time per tick | 113 ms | 99.5 ms |
| Blows a second | 465 | 821 |
| Fallen | 136 | 305 |

Details: `reports/polish-night-1026/battle-ways/README.md`.

## Later: morale in the engine (build 117)

The owner said "Yes, morale next". Every fighter's once-a-second look round for friends, foes and its ruler now happens in the engine, with exactly the same counts: 155,000 looks were compared and none differed. In a 500 v 500 that part fell from about 110 to about 33 ms a game second, roughly 7 to 8 ms off every 100 ms server tick.

## Later: where the time goes, game wide

We measured a 2,000-worker village and the big battle. Most of what looked like walking is work: a unit chops, mines and strikes by walking into a tree, a rock or a foe, and more than half of all step attempts are those. A plain step costs about 38 millionths of a second. One engine waste, empty calls on everything lying on a tile, was fixed and proven exact, but it saves only 0-2% in real play, so it waits. The next things worth timing are how each worker chooses its next job, and harvesting.

## Later: the attack box's next foe (build 118)

When a fighter in an attack box needed a new foe, it used to score every enemy in the box, up to 500 of them. The engine now ranks them first, and the game only looks at the few that could win. It picks the same foe: over 4,000 picks were checked and none differed. In a 500 v 500 that part fell from 91 to 17 ms a game second, and the worst orders hitch from 409 to 141 ms.

## Later: harvesting (build 119)

Timing inside a chop or a mine showed the cost wasn't where we guessed. The game keeps a list of the trees and rocks being worked, so the 3D view can show their cracks. Once 400 were being worked, every first blow on a new one tidied the whole list. With 2,000 workers that happened about 175 times a second. The engine does that tidy now, with exactly the same result: 53,200 checked, none differed. The harvest was the same too. A blow costs 40% less, and the whole village runs about 8% faster.

## Later: deliveries (build 120)

Starting a delivery took half a millisecond, mostly spent finding the best store tile. The engine does that search now, with the same answers: 8,400 checked. The biggest piece turned out to be a small one used everywhere. Asking for a zone's tiles, which happens about 24,000 times a second in a big village, built a piece of text each time just to check its memory. Now it compares the numbers directly. Along the way we found that every item lying on the ground keeps its own timer ticking once a second, forever if it's in a store. That cost grows as stores fill, so it's next on the list.

## Later: item timers (build 121)

Every item lying on the ground used to keep its own little timer, waking once a second to count towards rotting away, and on a stockpile it never stopped. A big store meant tens of thousands of timers. Now one timer in the engine counts for all of them, on exactly the same seconds, with the same rot rules: wood left out vanishes after 3 minutes, stored goods are kept, and arms go sooner. We ran both versions side by side for 210 seconds and their logs matched line for line. With 40,000 items lying around, the cost fell from about 9 ms to 1 ms of every tick.

## Next morning: no more freeze and hurry (build 122)

Units used to stop for a moment after an order, then hurry to catch up. We measured it in the real game. The server kept up fine, but the moves reached the screen unevenly, sometimes with a second or two between them. Now each unit walks its next tiles from a short queue at its own pace, still tile by tile. In the same test, units stopped mid-walk 71% less often and rushed 80% less.

## Next morning: going round mountains (build 123)

Click past a mountain and units used to walk to the rock and stand there. Their route search only looks so far, and the way round a long ridge is further. Now the game's engine spreads a map out from where you clicked and every unit going there reads its way down it. A group shares one map, so a hundred units cost about as much as a handful. With fog of war, the map only knows what your company has explored. Send units past rock nobody has seen and they'll walk up to it, see it, and then go round. In our test ridge, 0 of 100 units got round before; now 100 of 100 do. A big village costs the same as before.

## Later: carrying goods to the store (build 124)

We timed the next two pieces on the list from inside. Workers picking up pieces lying in their zone cost very little, so that one stays as it is. Carrying goods to a store was bigger, and the cost wasn't where the plan guessed. On every step of the walk, the carrier asked which store its target tile belongs to, and the game went through every store to find out. Now each tile remembers its store until the stores change. We checked 115,560 answers against the old way and none differed. Delivering now costs about half what it did.
