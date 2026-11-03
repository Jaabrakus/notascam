# The world's history (worldgen, 10-27, first draft for the owner)

New lore for the generated world, written for this game. Nothing here is taken from Daggerfall or from the 2006
game. The generator (`art/worldgen/lore.py`) gives every place on the map its own line of this history. The examples at
the end are copied from its output for seed 1026.

**The owner's rules (10-27):**
- No people live in the world now except the players. The rest is beasts, monsters and dungeons, plus a few kobold
  warrens and goblin caves. The history explains why.
- **No names** ("i kind of want no names i want people to conquer and claim the land make kingdoms"). The world, its
  old realms, cities, holds and caves have no names; they are forgotten. A place is called what it is ("a fallen city",
  "an abandoned hold"). Only four one-of-a-kind landmarks keep a plain title: the Old Heartland, the Sky Isle, the
  Great Falls and the Wound. Players name what they claim.

## Before memory: the Deep

Every people began underground. The caves under the world were the **Underhalls**, and every folk lived there: humans,
dwarves, night elves, orcs, goblins, kobolds, lizardmen and frogmen. Below the Underhalls lay **the Deep**, a sea of fire
and ash where something old slept. The peoples kept away from it.

One by one they climbed out into the light, each behind its own banner. That climb is where the game's name comes
from: they were the **Banners of the Deep**.

## The Age of Banners (about six hundred years)

On the surface the peoples raised **eighteen great realms**. Their names are forgotten. Each had a seat, a city that was the greatest its people
ever built. Around the cities stood about **one hundred and fifty holds**: walled towns on the roads, at the river
crossings and in the harbours. Stone roads joined them, and ships sailed the **sea lanes** between the ports. The
dwarves and the orcs dug **delvings** into the mountains for iron, silver and gold. The dead were laid in crypts,
barrows and desert tombs.

## The Delving

The best metal in the world, **adamantium**, grows only near the fire. In the last century of the Age of Banners
every realm wanted it, so every realm dug down again. They went past the Underhalls, lower each year, toward the
Deep.

## The Breaking: the Night of Open Gates

In one night the deepest shafts broke through. The old thing in the Deep woke, and **hellgates** tore open across
the land (twenty-one in this world). Mountains split and became volcanoes, and the land around them burned to the
ash fields. Demons climbed out of the gates. The dead got up in their crypts. Dragons came down from the high peaks
to the open treasuries. The great stone guardians the realms had built lay down and became hills.

**All eighteen realms fell within a generation.**

## The Long Quiet (three hundred years, up to now)

No kingdom stands. The holds are empty, their roofs fallen in. The cities are ruins with half their walls down,
and grass grows through the squares. The old roads are broken and overgrown. The world belongs to:

- **beasts**: wolves in the north and the woods, giant spiders and death beetles in the jungles and fens, sand kings
  under the deserts, ratmen and giant moles in the lowlands;
- **monsters**: demons at the gates and in the ash, the restless dead in the crypts, barrows and tombs, dragons asleep
  on stolen gold, and cave spiders and tower caps in the mushroom caverns;
- **the svartalfar and the mind-eaters**, who never came up from the Underhalls; their stairs are the deep halls;
- **kobolds and goblins**, the only folk still living in numbers. The kobolds hid deep in their warrens and outlasted
  everyone. Goblin bands hold caves by the old roads and raid whatever passes. They are the world's only NPCs, and
  there are few of them.

## Under the ground and in the sky

- **The Underhalls** (caves layer): the old homes the peoples left when they climbed out, 22 great round caverns
  under the mountains with rows of ruined halls and pillars. Empty now, and the cave folk use them. Every one is joined
  to the cave tunnels.
- **The Deep** (depths layer): halls of ash and fire. A **lava sea** lies under every volcano. Beside the shafts of the
  hellgates stand **11 demon keeps**: square walls and towers in a ring of lava, with one causeway in. Whoever holds a
  keep holds that gate from below.
- **The Wound**: the place the shafts first broke through, a black pit in a lake of fire under the greatest volcano. The
  old thing that woke sleeps under it. It is the bottom of the world, and the end of the story if there is one.
- **The Sky Isle** (sky layer): on the Night of Open Gates the Deep heaved and tore a hill out of the earth, lake and
  all, and threw it into the sky, where it stayed. Its lake pours off the
  edge as **the Great Falls**, straight down into the waves, and sailors see the mist for a day before they see the
  isle. It hangs far out over the open sea at the edge of the world, out of sight of any coast, waiting to be found
  (owner, 10-27). A ruined sky temple stands by the lake, and **skystone** grows in its white rim. A dozen smaller
  **skyrocks**, torn up the same night, float over sea and land.

## The Heartland

One vale was never touched: **the Old Heartland**, a wide valley ringed by mountains, where no gate opened. Today's
hand-made map is the Heartland. The last of every people fled there in the winter after the Breaking, and there they
stayed for three hundred years.

Now the players' companies ride out of the Heartland under their banners to retake the world: to move into the
abandoned holds and the fallen cities, reopen the delvings, clear the crypts, kill the dragons and close the gates,
and to **conquer and claim the land and make kingdoms**, fighting each other for it. The world is cut into hex regions;
a kingdom is the hexes it holds, and its players give it, and everything in it, their own names.

## How the map tells it

- **No realms or borders**: the land is open, in hex regions, for players to claim.
- **The great swamp** east of the Heartland: low, flat, wet land of reeds, black pools and drowned woods.
- **18 fallen cities**: each with a line saying which people raised it, how it fell (to a hellgate, to a dragon, to its
  own deep mines, to the dead) and what is there now.
- **150 abandoned holds**: each with what it lived on (a harbour, a delving's ore, the old road) and what became of
  its people.
- **314 old delvings**: each with its ore and why it was left (the shafts broke into fire, the galleries flooded,
  something came up the shafts).
- **420 beast lairs**, **~700 caves, crypts, barrows, tombs, ice caves, mushroom hollows, deep halls, dragon peaks
  and hellgates**, **97 kobold warrens and goblin holes**, and **460 ruins** (watchtowers, shrines, battlefields,
  standing stones, waystations and bridge forts).

## Examples from the generator (seed 1026)

Every place's line is in `art/worldgen/out/world.json`. A few, as the generator writes them:

- *A fallen city, the greatest the humans ever raised, seat of a realm whose name is forgotten. It fell when a hellgate
  burst open a day's march away. Its walls still stand in places, and wolves den in its halls.*
- *A fallen city, the greatest the lizardmen ever raised, seat of a realm whose name is forgotten. It fell when a
  dragon came down from the peaks for its treasury. Its treasury was never found.*
- *An abandoned lizardman hold, a harbour on the old sea lanes. Its people went down into the cellars to hide and did
  not come up again.*
- *An old delving, dug for silver and left when the lower galleries flooded. The ore is still there.*
- *A dragon took this peak after the Breaking and sleeps on the gold of a fallen city.*
- *One of the 21 gates that opened on the Night of Open Gates. Demons still climb out of it.*
- *Kobolds live here as they did before the Breaking: they hid deep and outlasted everyone.*

## Open for the owner

- Whether all eighteen realms fell, or one or two holdouts should survive as rare NPC strongholds (that would go
  against "no NPC towns", so today's answer is no).
- How many hellgates, and whether closing them is the long goal for the players.
