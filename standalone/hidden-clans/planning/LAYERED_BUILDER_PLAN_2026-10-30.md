# A layered, procedural builder (plan, 10-30, for the owner's go-ahead)

The owner, 10-30: "we need layers in builder so i can put floors down and doors and etc, we may need to make it
procedural to make it right".

## Where it stands (app 146)

Plan mode builds in layers already: a level stepper (PageUp/PageDown, the arrows on the bar) and a cut view of the
level you're on. Walls go on any level. Doors and floors go on the ground only. A block must sit on a block under it,
so there are no upper floors spanning a room, only solid stacks. A house of 7x5 with a door and a stone floor takes
6 clicks and 2 drags (the HUD play test, reports/construction-3d/tests/play_hud.py: 10 of 10 steps easy).

## The idea

**One tool, Building:** drag a footprint, and the game lays out the whole building, layer by layer, as marks you can
see and change before you queue it.
- The card asks: what (house, hall, tower, wall), how many storeys (1 to 3), stone or wood, which side the door faces
  (it picks the side towards your village; click to change).
- The game writes the marks for each layer:
  - walls 2 blocks high a storey, as an outline;
  - the door's gap and its door on the ground storey;
  - the floor inside each storey;
  - stairs up in a corner when there is more than one storey;
  - the roof on top, which comes by itself when the last block is in.
- You see it finished before you queue it (the preview landed today), step through its layers with the level stepper
  to change any of them, then Queue it. After that it is the same plan the villagers already build: pile, scaffolding,
  idle villagers helping.
- Saved designs then come for free: save what you made or generated, stamp it anywhere, turned.

## Phases

1. **A one-storey building, generated.** LANDED 10-30 13:14, app 146 (reports/construction-3d/builder1; play test
   tests/play_builder.py 9/9: house, hall, tower, wall, the door turned, the 40-tile cap, Queue). Footprint, kind, material, door side; walls, door, floor, roof. Page only, on
   today's rules. About half a day with its play test.
2. **Layers you can work on.** LANDED 10-30 13:37, app 146 (reports/construction-3d/builder2; tests/play_storeys.py 6/6):
   Storey 1-4 on the card (two levels a storey) with what is marked and queued on it, the bar names the storey; a door
   belongs to its storey: the ground storey's as before, upstairs an opening in a wall still to be built (no door up
   there); the Floor tool upstairs says floors over a room come with phase 3. (Floors on wall tops: not done; the old
   rules hold a high tile only over stairs and wall walks.)
   Was: The level stepper becomes a storey picker showing what each storey holds; doors and
   floors on any storey you can reach (a floor on top of a wall run, a door in an upper wall's gap).
3. **Upper floors over a room.** A rule change: a block may be laid over open air when walls or a beam hold it within
   3 tiles. The world already draws columns with a gap under a block (tunnel ceilings), so the room below stays
   walkable and the storey above is stood on. This touches the block rules, the 3D terrain and how units stand up
   there, so it needs its own arena tests: walk in downstairs, climb the stairs, stand upstairs, dig one out.
   Approved 10-30 ("begin phase 3"). In parts:
   - 3a, the rule. LANDED 13:48: a block over open air is held within 3 tiles of a whole column; the room under it
     stays open, its top is stood on (tests/upper_floors.dm).
   - 3b, drawn. LANDED 13:55: a laid ceiling is drawn as the walls' blocks are, units on it at its height
     (tests/headless_upper.py).
   - 3c, storeys from the Building tool (the owner: "if someone does a 2 story or 3 story house in one drag plan does
     it also include the beams and etc?"). A storey is three levels: two of room and the floor over it. Storeys 1-3 on
     the card. One drag lays out:
     - walls through every storey, and over the door;
     - each upper floor as blocks held by the walls, with a pillar where a span is over 3;
     - a flight of three steps up each storey (made ramps as they are laid);
     - the roof over the top storey.
     The Floor tool upstairs marks floor blocks. A door cuts only its storey's two levels.
   - 3d, buildings on buildings (the owner, 10-30: "we want it like mine craft where they can build anything ... off
     set some buildings and rooms"). The Building tool works on the storey you are looking at. From storey 2 up, a
     building stands on its own floor: blocks laid over whatever is under it, an opening on its door side instead of a
     door. So a room can sit half on a house and stick out past it, up to 3 tiles, with pillars from the ground
     farther out. A plan may stand on blocks of another plan still going up.
     The owner, 10-30 evening: keep the 3-tile rule (a block over open air needs a wall or pillar within 3 tiles; not
     fully Minecraft).
     Storeys and rooms on houses LANDED 10-30 (3c 15:18, then 3d-3m from playing it by hand in the real game; the last,
     3m at 18:19: nobody stranded on a lower house's wall top, a room's corner by its stairs laid first;
     3n at 19:22: a stairs jam and the corner in the real game's layout; played by hand in the browser, a room on a house
     finished; reports/construction-3d/README.md).
4. **Saved designs.** LANDED 10-30 19:45 (reports/construction-3d/designs1): Save design on the Plan card keeps the marks
   by name in the player's profile; the Designs tool places one anywhere, turned a quarter at a time.
5. **Then:** furniture upstairs, windows, more building kinds.

## What it needs from you

- Go-ahead for phase 1 now.
- A yes or no on the support rule in phase 3 (blocks held by walls or beams within 3 tiles), which changes what can be
  built everywhere, not only in this tool.
