# The big world: what was made today and what comes next (worldgen, 10-27)

The owner wants the world "as Daggerfall": huge, made by the computer, and kept as players change it. Today's step is
**pictures only**. Nothing in the game changed. The generator lives in `art/worldgen/`, and its pictures are in
`art/worldgen/out/` and `devlog/2026-10-27/img/worldgen-*.png`.

**The world is seed 1026** (owner, 10-27: "1026 is the best", over seed 2027). Every picture and the game use it.

## What exists now

- **One number makes the whole world.** The same seed gives the same world every run. Two runs were checked to give
  the same fingerprint (`world.json`).
- **Size.** 4,012 **hex regions** (owner, 10-27: "make it hexagon tiles"), each about 66,500 tiles, the same as a
  256 x 256 square. The world is 16,384 tiles across, about 268 of today's maps. About a third of it is land,
  roughly 1,660 hexes. Each hex has six equal neighbours. Inside a hex the game's tiles stay square, because the
  engine, routes, building, mining and 3D rock are all square: a tile belongs to the hex whose centre is nearest.
  A hex is loaded, saved and woken as one region (the tiles of its 320 x 320 box that belong to it).
- **Four layers in every region, tile for tile**, the same four as today:
  - **Ground**: height decides sea, beach, lowland, hills and mountain ranges. The climate comes from how far north
    a place is, how high it is and how wet it is. That gives snow, tundra with pines, grassland, woods, jungle,
    marsh, desert and red mesa, plus ash lands around a few volcanoes. These are today's biomes from `Biomes.dm`,
    now spread over the land and not dropped in as circles.
  - **Sky**: a peak above every ground mountain tile and open sky everywhere else. That's today's rule exactly:
    on today's map every one of 626,869 mountain tiles has a peak above it.
  - **Caves**: solid rock with winding tunnels and halls (more of them under mountains), underground lakes,
    flooded passages under the sea and rivers, lava near volcanoes, and mushroom caverns under woods and jungle.
    Every cave mouth on the ground opens into a hall right below it, with stairs up at the same tile, and a tunnel is
    dug from there to the nearest cave network.
  - **Depths**: wide halls of hell floor with rock walls, lava rivers and lakes, and patches of dead grass. Chasms in
    the caves drop to a landing at the same tile in the depths. A hellgate goes straight down.
- **Rivers** start in the hills and run downhill to the sea. They pass through lakes and widen as they gather water,
  from about 3 tiles at the source to about 30 at the mouth. They are worked out for the whole world at once, so they
  carry on across region edges with no seam.
- **Places**: about 2,060, and none of them has living people in it. The owner's rule (10-27) is no NPC towns: only
  players, beasts and monsters, plus a few kobold and goblin caves. The history in `planning/WORLD_LORE_2026-10-27.md`
  explains why the land is empty. The places are:
  - 18 fallen cities (one seat per old realm) and 150 abandoned holds, ruins the players can move into;
  - 314 old delvings to reopen, with the ore set by the land: gold and silver in the mesa, iron in the cold,
    adamantium by the volcanoes;
  - 420 beast lairs: wolves, giant spiders, death beetles, sand kings, ratmen, giant moles, demons in the ash;
  - about 700 caves, crypts, barrows, tombs, ice caves, mushroom hollows, deep halls, dragon peaks and hellgates;
  - 97 kobold warrens and goblin holes, the only folk left;
  - 460 ruins.
  **No names and no realms** (owner, 10-27): places are called what they are, every place has a line of its own
  history with no names in it, and the land is open for players to conquer and claim.
- **Old roads** join the fallen cities and holds, and old cart tracks join the delvings and some dungeons. Roads avoid mountains,
  share stretches with each other and cross rivers on bridges. **Old sea lanes** join the old harbours across open water, ready for ships later.
- **Climate (owner, 10-27)**: winter only in the far north and on the high peaks; a great swamp of reeds, black pools
  and drowned woods east of the heartland, and swamps wherever land is low, flat and wet.
- **Today's map can sit in the middle** as "The Old Heartland" (it covers parts of about 18 hexes), with all four of
  its layers kept exactly. The new land fits around it: its mountains, sea and water carry on outward, and its western
  water opens into a sea gulf. Round its edge is a mixed band (owner: "a hybrid setting"): its own snow, grass and sand
  spill outward in patches that thin out, so there is no hard line. The generator reads today's map fresh each run, so it follows
  hud-rework's changes (sea on the south and east since 17:41). A switch makes an all-new world without it.
  Both are in the pictures.

- **Dungeons** (owner, 10-27: "dungeons we can put around the map or dungeon instances"): every cave, crypt,
  barrow, tomb, ice cave, mushroom hollow, delving, dragon lair, kobold warren, goblin hole, hellgate and deep hall
  has its own layout, made from its own number, with 1 to 3 floors. Each has its way in, stairs, monster spots, a boss,
  treasure, tombs and eggs. **Both ways at once:** the first floor is carved into the caves layer right under its cave
  mouth, so it is part of the world; the deeper floors are instances, made fresh for one party in sealed rock, as
  `Instances.dm` does today. Its 40 x 40 slots would grow to fit (barrows 48, dragon lairs 120). The monsters are
  today's cave themes: goblin warren, kobold den, ratman burrow, undead crypt, orc stronghold, dragon's lair, spider's nest.
- **Caves and depths for the whole world**, lined up with the ground: the Underhalls, demon keeps, lava seas and the
  Wound (see the lore).
- **The Sky Isle and the Great Falls** (owner, 10-27): one great island (400 x 290 tiles) far out over the sea at the edge of the world, at the sky
  height, with a lake, its river, woods, a ruined temple and skystone. The river falls off the edge into the sea. There
  are also 12 small skyrocks. This follows the sky plan (`planning/SKY_CLOUDS_AIRSHIPS.md` (c)): a new
  "Cloudstone" tile that walkers stand on, the floor at the sky height. The great isle is over the sea, so it is by air
  (or ship and climb) only.

## Next steps (each one asks the owner before any game change)

1. **One region's real tiles in the game, windowless.** A small tool turns one region's four layers into game
   tiles. It would use the same turf types the hand-made maps use: grass, snow, desert, marsh, water, cave rock as
   `cavefloor`, caves as `cellarfloor` rock with dug floor, depths as `hellfloor`/`hellcliff`, sky as `Sky`/`MountainPeak`.
   The tool loads the region into the arena as extra layers (the engine can grow the map while running, proven
   10-22). Then it checks the region: units walk across it, mine it, go down a cave mouth to the stairs, and drop
   through a chasm. It also times the load. The generator stays outside the game and writes a small file per region,
   which the game reads; that's cheaper than making the land inside the game.
   **Open:** today's water is solid (no wading or swimming), so rivers would cut the land in pieces. The roads
   already have bridges, but wading through shallows is hud-rework's area. Agree with them first.
2. **Load and unload hex regions near players.** Build on the map memory work (`planning/MAP_MEMORY.md`: far tiles sleep in
   about 52 bytes each, and a region wakes before anyone sees it). A hex is loaded only while a player's units,
   buildings or camera are in it or in one of its six neighbours. Everything else is just the seed.
3. **Save only what players change.** An untouched region costs nothing on disk because the seed makes it again. A
   region's save holds only the tiles that differ from what the generator makes, plus the things on them (the same
   idea as today's world save, which keeps only tiles that differ from the map file).
4. **Fill the places.** The lairs get their beasts, and the dungeons get their monsters and treasure from today's cave
   themes (`Instances.dm`). The kobold warrens and goblin holes get their few folk. The fallen cities and abandoned
   holds are ruins players can claim and rebuild. No living NPC towns (owner, 10-27).
5. **Ships across seas.** The sea lanes become routes. First as travel on the world map that takes time (the away
   pace), later as real ships.
6. **The travel map.** The HUD's world map shows this map: hex regions, places found, roads and lanes, and who holds
   which hex.
8. **Kingdoms by hex** (owner, 10-27: "conquer and claim the land make kingdoms"). A hex is claimed the way land is
   claimed today (`Claims.dm`, keyed by hex). A kingdom is the hexes it holds, coloured on the hex map, named by its
   players, with its towns, borders and tolls (the feudal economy plan).
7. **The lore in the game.** Each place's history line shows when a player finds it.

## Questions for the owner

- Should today's map stay in the middle as the old heartland, or should the world be all new?
- Is about 4,000 hex regions (268 of today's maps) the right size to start? The generator can make it bigger or smaller.
- Is a hex of about 66,500 tiles (320 tiles corner to corner) the right size for one region?
