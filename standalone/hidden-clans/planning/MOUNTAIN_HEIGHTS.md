# Mountain heights: tops on the surface, only the tallest reach the Sky

Plan only (ramps-gather, 2026-10-25). Nothing in `game/` has changed. Points that need the user's OK are marked **OK?**.

## The decision

The user, relayed by rts-feel: "there should be no more mountain top peak right now" and "maybe one or 10% a mountain
tiles climb that high allowing units to go to sky islands if we decide to build on those". So most mountains stop
below the Sky level, and only the tallest 1–10% reach it. Later those become the way up to sky islands
(the sky-ideas session, `local_571b17a1-b16b-4796-ae4e-1db20137b3c7`).

## How it works today

- **Rock columns.** Every rock tile on the ground (layer 1, about 626,000 `cavefloor` tiles of the 1000×1000 map) is a
  column of blocks 3–8 high. Its height comes from how far it is from open ground (`Breaking.dm RemasterBlocksAt`). It is
  worked out again each run and never saved.
- **Walkable tops.** A column's walkable top is a `MountainPeak` tile on the Sky layer (layer 3) right over it: 652,416
  of the Sky map's 1,000,000 tiles (65%). The rest is 342,344 open `Sky` tiles and about 3,000 built floors and walls
  from the map.
- **Every place above the ground is on layer 3, with a height** (`feet`, in blocks). That covers a column's top, a gap
  dug inside it, and a carved ramp (`Gather.dm RemasterSpotsAt`). Layer 1 is the ground and tunnels at ground level
  (feet 0).
- **Layer 3 also holds** wall walks on built walls (`WallWalks.dm`), upper floors and towers (`Construction.dm`,
  `Buildings.dm`, the original building code), lift landings (`Lifts.dm`) and, new from rts-feel, flyers on the Sky
  level.
- **Code that reads it:**
  - `Gather.dm` (21 references to the layer), `Plans.dm` (20), `WallWalks.dm` (16), `View3D.dm` (10).
  - `Mountains.dm` and `Orders.dm` (7 each), `Lifts.dm` and `Fog.dm` (6), `Peaks.dm` (5), `Formations.dm` and
    `Construction.dm` (4).
  - Original code: `Building.dm`, `Bump.dm`, `Stairs.dm`, `Admin.dm`.

So today "the Sky level" and "up on a mountain" are the same layer. That is why mountain tops show up in the sky.

## Two ways to do it

**A. Move mountain tops down to the surface layer.** Units up on a mountain would stand on layer 1 (on the rock tile
itself) with a height, and the 652,416 Peak tiles would become open sky.

- Every unit on a mountain would stand on a dense tile. The ground rule (`turf/grounds/Enter`), the original movement,
  `Bump.dm` and the stairs all treat a dense layer-1 tile as blocked.
- The whole model of places above the ground would be redone on layer 1, with the ground as place 0. That covers
  places, routes by height, work spots, ramps, hops and Plan mode's way up.
- The map, world saves (layer-3 tile records), unit saves (units on layer 3), and items and buildings up there would
  all need converting. That is a world and save format change.
- It is big and risky, and the player would see no difference from B.

**B. Keep the places where they are, and split the Sky level by height (recommended).**

- The Sky level becomes everything at or above a sky height, `RM_SKY_H`. The proposal is 10 blocks, above every
  ordinary mountain, whose tops are 8 at most.
- Below the sky height, layer 3 just means "up on the mountain / on the wall / upstairs". It belongs to the Surface
  level in everything the player sees and does.
- No map change and no save format change. `Peak` stays as an internal marker ("a walkable top here"). The game
  never shows or names it as sky.

**Recommendation: B.** The rest of this plan is B.

## 1. A mountain top below the Sky level

What the player gets:

- Units stand on the top block, or anywhere they have dug into the mountain, as now. They are drawn, picked and
  selected in the **Surface** view. The camera stays on Surface when it follows them up a mountain.
- The cutaway works at the unit's height, as now.
- Mining from above, carved ramps, workers cutting their own way up, and Plan mode all keep working unchanged.
  Plan mode's levels are the blocks 0 up to the sky height, in the Surface view.
- The yellow highlight on worked blocks (x, y, block) is unchanged.
- The sight bonus for being up high (+3, `Fog.dm`) goes by height (feet 2 and up) instead of by layer.
- Flyers on the Sky level fly over ordinary mountains, at the sky height and above.
- Hover and click wording says "mountain top", never "Peak" or "Sky".

What changes in code:

- One helper, `RmLevelOf(atom)`, returns "surface", "sky" or "caves" from the layer, the height and whether the unit
  is flying.
- It is used for:
  - the camera's and the view's level;
  - the level buttons;
  - Sky-view clicks, which only reach Sky-level places: sky peak summits, sky islands, and open sky for flyers;
  - fog;
  - the HUD's level label.
- Everything that works on heights already (mining, ramps, routes, Plan mode, formations' slots by height) needs
  nothing.

## 2. Which mountains reach the Sky

The rule is worked out from position alone, so it fits the chunked, procedural Daggerfall-scale world.

- **Score.** Each untouched natural rock tile gets a score from:
  - how deep inside its mountain it is (the depth `RemasterBlocksAt` works out already, 1–6 tiles);
  - a ridge noise (`1 - |2n - 1|` of a coarse value noise from `RemasterHash`, about 24 tiles across), so tall
    ground forms ridgelines rather than random spikes.
- **Tunable share.** The top `RM_SKY_PEAK_PCT` percent of rock tiles by score become sky peaks: default 0 (the user,
  2026-10-25: "0% for now"), tunable 1–10 later. The cut-off is calibrated per region from a fixed, seeded sample, so the share is the same in every region
  and every run.
- **Shape: a dome, not a pillar.** Heights rise 8 → 9 → 10–12 toward each core, so carved ramps and the workers' own
  way up can climb it a block at a time.
- **Cap.** A column has room for 16 blocks (the dug-gaps record is 16 bits wide), so sky peaks of 10–12 leave room to
  build on top. The build cap (`RM_BUILD_TOP`, 8 today) would rise so towers can reach the Sky level.
- **On today's map:** 5% of about 626,000 rock tiles is about 31,000 tiles; 1% is about 6,000.
- **Switch.** It stays off behind a switch until the user has seen it.

## 3. Existing worlds and saves

- **B changes no map file and no save format.** Nothing on a mountain top today moves. Units, buildings, items and
  wall walks stay where they are; they just count as the Surface level.
- **Heights need one fix first.** A column's height is worked out each run and never saved. That causes two problems:
  - A world dug before sky peaks arrive would get new heights on its tall columns. Its saved "blocks dug off the top"
    would then count from the wrong base.
  - This one exists today: digging a mountain open can change its neighbours' heights after a restart, because the
    height counts distance to open ground.
- **The fix:** save a column's height the first time it changes. That is one more saved tile value, written only for
  changed tiles. Old saves load as before, and an older build ignores it (`RemasterApplyVars` skips values it doesn't
  know). Columns already changed in a saved world keep their old heights. Only untouched rock can become a sky peak.
- **OK?** This is a small, compatible addition to world saves, but it does touch them, so the user should OK it.
  Restore point before landing: `game/` and a copy of the user's world save.
- **If A were ever chosen:** the map, world saves and unit saves would all convert. That needs the user's OK, a
  converter and a restore point.

## 4. The 3D view (world-look's answer, 2026-10-25, fitted to B)

- **Rock columns.** The Surface view already draws every rock column whole from the layer-1 chunks: each block's
  sides and the top block's top face (`v3rockStack`). Mountain tops need nothing new.
- **The "peaks in the sky" are a floor.** Layer 3 adds a floor at storey height over every mountain tile, with tufts
  and roofs, as its own chunk set (`V3.upper`). In a wide window (101×81) that is about 4,000 tiles and 14,500
  triangles.
- **Server change: send ordinary peaks as open sky.** Under B, the server sends a Peak tile whose column is below the
  sky height as open sky in the 3D terrain (`View3D.dm Remaster3DKind`). The data on layer 3 stays as it is. Those
  chunks then come out empty, leaving only tall peaks and built things. No chunk code changes, and pans and level
  changes get cheaper.
- **Side effects of that change.** `V3.upperTiles` also feeds the roofs, the cutaway of an upper storey near the
  camera, and a fallback height for units drawn in the air. Over ordinary mountains those simply stop applying, which
  is right: units up there already carry their height.
- **Surface view:** the ground with its full rock stacks, plus the upper layer (only tall peaks, and later sky
  islands). Units up on mountains already come as "air" things standing at their height (`v3feetY`). No change.
- **Sky view:** layer 3 (tall tops, islands, flyers) plus the whole surface below at minus one storey, every ordinary
  mountain included. world-look's staged level-switch fix (`patch_level_warm.py`) handles any ground content, and
  nothing in it assumes peaks.
- **Units on ordinary mountain tops in the Sky view.** Under B they are layer-3 things with a height. They show below,
  with the surface.
- **A separate Sky gap on the page, not the storey height.** The storey height (`STOREY`) is 2.3 blocks and is first a
  building storey: built walls, upper floors, stairs and ramps, and the cutaway read it 29 times. It must stay. Under
  B, layer 3 holds both at once: upper storeys and wall walks at storey height (2.3 up), and sky peaks and islands at
  the sky height (10+ up). So the page gets its own gap for the Sky level, `V3.SKYH = RM_SKY_H`:
  - The Sky view draws the surface under it at minus `SKYH`. Its layer-3 things below the sky height (units on
    ordinary mountains) stand at height minus `SKYH`: one rule.
  - Peak tiles that stay on layer 3 (the tall ones) carry their column's height in the layer-3 terrain (the kind's
    blocks, as ground rock does). The page draws their floor at that height, not at storey height. Building floors
    and wall walks on layer 3 stay at storey height.
  - Units on tall peaks and islands use their height as now (`v3feetY`, the top of their block in the stack).
  - world-look builds the page side once the format is fixed.
- **Only under A** would ground-layer units need to carry a height too (world-look's point 3: a stand-height field
  of the page's own, never `ly`, which many paths read as "on another level"). B doesn't need it.

## 5. Cost, risk, checks and order

| Step | What | Checks | Risk |
|---|---|---|---|
| 0 | Restore point. Save a column's height on its first change (`RemasterBlocksAt` and the procs that change blocks). Fixes the restart bug on its own. | Arena: dig, save, restart, same heights; dig/build/way-up arenas | low |
| 1 | `RM_SKY_H` and `RmLevelOf`; the camera, view level, clicks, fog and HUD label use them | Arena: units on tops stay Surface, flyers at sky height are Sky; headless page clicks; rts-feel's sky-click checks again | low |
| 2 | Ordinary peaks sent as open sky in the 3D terrain; tall peaks carry their column height; the page's own Sky gap `V3.SKYH = RM_SKY_H`, the Sky view standing layer-3 things below the sky height at height minus `SKYH` (world-look) | Headless and WKWebView stills of one spot, Surface vs Sky; triangle counts before and after | low–medium |
| 3 | Sky peaks (`RM_SKY_PEAK_PCT`, off by default) | An offline count on the real map (share and where); arena: a dome climbed by the way up and dug from the top; one real window: walk up a sky peak | medium |
| 4 | Sky islands meet the Sky level at the sky height (sky-ideas) | Theirs | — |

- **Every step:** arena first, headless where the page changes, one real window at the end, and an app build after
  each landing.
- **Cost:** heights are worked out once per tile, when first needed. The ridge noise adds a few hash calls to that.
  Calibration is a fixed sample per region (about 20,000 tiles, once).

## Questions for the user

1. The sky height: 10 blocks (just above the tallest ordinary mountain)?
2. The share of tall mountains: 5% to start, tunable 1–10?
3. OK to save a column's height the first time it changes (small and compatible, but it touches world saves)?
4. Should sky islands float over ordinary mountains too? Under B, a mountain top's tile can't also hold a floor at
   the sky height without a second place on that tile. That is a later step; sky-ideas decides.

## Decisions and notes since (2026-10-25)

- **The user, later the same evening: "0% for now".** No mountain changes height, and `RM_SKY_PEAK_PCT` defaults to
  0. Step 3's rule and its switch stay in the plan as a code path for later (sky islands), off by default. The
  user: "we shouldnt lower the mountains... we could have just raised the sky". That is plan B: the Sky line at 10,
  above every ordinary mountain (8 at most), with tops counting as Surface.
  - What that means on screen once step 2 is in: the Sky level is all open sky, plus building floors and wall walks.
    No mountain reaches it.

- **The user, through the coordinator:** "you got the best practices implement what is best".
  - Sky height `RM_SKY_H` = 10 blocks; `RM_SKY_PEAK_PCT` starts at 5, tunable 1–10.
  - OK to keep a column's height in world saves, with restore points, proof that an old save loads unchanged, and a
    new save round-tripping.
  - Sky islands over mountains: later, the sky-ideas session decides.
  - Build B in the plan's steps, step 0 first; each step goes through the arena and headless gates, then the
    coordinator's OK to land. It stays behind its switch until a real-window check passes.
- **sky-ideas** (`planning/SKY_CLOUDS_AIRSHIPS.md` 1c):
  - 10 blocks works for clouds, islands and airships.
  - Islands go over open ground and water only for now (the user's choice Q-C6), so no second place on a tile.
  - `RM_SKY_H` (server) and `V3.SKYH` (page) are the one source; clouds, island floors and airship heights read them
    and never keep a copy.
  - Sky peak positions must be findable from position alone, so islands can sit within a bridge's reach. Step 3 gives
    them one call for it, `RmSkyPeakAt(x, y)`.
  - Island and dock tiles are a turf state of their own, not Peak, so `Peaks.dm RemasterPeakUnheld` must never open
    them. That is for when islands land.
- **rts-feel** has adopted the rule in its staged sky work (`tools/rts_feel/sky/apply_sky2.py`, not in `game/`).
  - Earned Sky: `RmSkyUnit(M) = z3 && HP > 0 && (Flying || RemasterFeetOf(M) >= RM_SKY_H)`. A camera on layer 3 with
    nobody at Sky level goes back to Surface, unless it is locked on a unit.
  - `#ifndef RM_SKY_H / #define RM_SKY_H 10` sits in `Flying.dm` until step 1 defines it.
  - It switches to `RmLevelOf(M) == "sky"` when that lands. Sky-view clicks for walkers are step 1's.
  - For step 1: a flyer's height on layer 3 is `RM_SKY_H` plus its `RmFlyHeights` entry, wherever heights are drawn
    or worked out.
