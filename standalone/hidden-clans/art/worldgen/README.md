# World generator (worldgen, 10-27)

Makes the Daggerfall-sized world as pictures. Offline only: it reads `game/Maps/*.dmm` and never writes game files.

- `python3 render.py [seed]`: every picture plus `out/world.json` (each place and its line of history). Takes about 3 minutes.
- `python3 quick.py [seed] [0|1]`: a fast rough map while tuning (1 = today's map in the middle).
- `worldgen.py`: the world. It has height, climate, rivers, places, roads, sea lanes, and one hex region's four layers (`World.hex_region`; regions are hexes, tiles inside stay square).
- `lore.py`: each place's line of history, with no names in it (owner, 10-27). The history is in `planning/WORLD_LORE_2026-10-27.md`.
- `heartland.py` reads today's four map layers. `noise.py` holds the seeded noise. `dungeons.py` makes every dungeon's floors.
- `export.py` + `arena_test.sh`: one hex region as game tiles, loaded into the test arena windowless (`tests/worldgen_region_test.dm`).

Plan for the next steps: `planning/WORLDGEN_PLAN_2026-10-27.md`. Devlog: `devlog/2026-10-27/worldgen.md`.
