# Memory with many players, 10-31 (afternoon)

## The server stopped hoarding

With ten players on one world, the server kept a little more in its pockets every second and never emptied them: about
twenty small lists a second for each player, a fresh pair every moment that player's camera checked who had moved. In
two minutes ten players piled up almost 22,000 of them. They held nothing anyone needed; the engine just never let go.

The same slip turned up in a dozen other places: marching routes, formation spots, the "who do I fight next" lists in
battles. All of them let go now. On the same ten players, the server's lists stay flat instead of climbing.

## Lighter creatures

Every creature on the map, every wolf and skeleton too, was born carrying about twenty empty pockets it would never
use: nine of them were the unit groups from the 2006 game, which only a player can set. Now those pockets are only made
when something actually puts a thing in them. Each creature is born with about three and a half instead of twenty.

At 30 players and a thousand units, the server's lists take 104 MB instead of 155 MB.

Next: what one unit costs on its own. Each keeps about 190 of its own numbers and names, about 6 KB. How small could a
soldier get?

## Every soldier carries a lighter notebook

Each unit keeps a little notebook of its own numbers: how much blood it has, which limbs it still has, what it is
chasing. A third of the pages only said what every unit starts with anyway ("has a head", "not fainted"). Once a minute
the server now tears those pages out; reading them gives the same answer, and a saved game is the same down to the byte.
The notebooks of the ground under everyone's feet also start thinner now.

With 100 players, those notebooks went from 83 MB to 55 MB. A soldier's own notebook is about 6 KB now. Getting it to
2 or 3 KB would mean rebinding every notebook in a new way. Worth it?
