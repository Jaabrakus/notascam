# Sky level: clouds and airships (design, for the user's choices)

Written 2026-10-25 evening, design only. Nothing in `game/` or `engine/` is changed, and no runs were started. The
user asked whether the Sky level can have **clouds** and **flyable ships**. This file sets out the options, with data
from the code as it is today, the pros and cons, and rough costs. Every choice is the user's: they are collected at the
end (section 5) so they can be answered in one go.

Depends on two pieces in progress elsewhere:
- **rts-feel** is building the Sky level for flyers: Fly higher at the top height takes a flyer up to the Sky level,
  and open sky there is clickable for flyers (walkers stay on mountain tops). See the memory note sky-level-flying.
- **climbable-ramps** posted `planning/MOUNTAIN_HEIGHTS.md` at 17:09 (a plan, waiting on the user). The user said at
  17:03 that most mountains will stop below the Sky level, and only the tallest 1-10% of mountain tiles reach it ("the
  way up to sky islands later"). Today 65% of `Maps/3-Sky.dmm` is Peak tiles. The plan recommends **B**:
  - The **Sky level is everything at or above the sky height** `RM_SKY_H`, proposed at 10 blocks.
  - Layer 3 below that height counts as the Surface level: mountain tops, wall walks, upper floors.
  - One helper, `RmLevelOf`, says which level a place is on.
  - The page gets its own Sky gap, `V3.SKYH`. The building storey `STOREY` (2.3) stays.

  This file assumes B. It leaves sky islands to "the sky-ideas session", which is this one: section 1 (c) answers
  that plan's question 4.

## 0. What is there today (checked in the code)

| Fact | Where |
|---|---|
| The Sky level is z 3, 1000 x 1000 tiles: today 652,261 Peak (mountain tops), 342,344 open Sky, about 5,000 built floor and wall tiles from the original map. | `Maps/3-Sky.dmm`, `Building/Stairs.dm` (GROUND 1, UNDERGROUND 2, SKY 3, HELL 4) |
| A walker that steps onto open Sky falls to the surface; each leg has a 50% chance of being mangled (leg HP 10, 25 blood lost), unless it is a climber, an Illithid or a werewolf. A walker that falls down a chasm is deleted. | `Turfs.dm` ("Sky", "Chasm") |
| A peak with no rock under it opens to the sky, checked every 5 s round each player. Anything new that walkers stand on at z 3 over open ground (a dock top, an island) must be exempt from this. | `Peaks.dm` `RemasterPeakUnheld` |
| Flyers go over everything on the surface and the Sky level. Fly heights: dragons 3, 10, 20 or 30 tiles; others 2, 4 or 6. Landing needs open ground below. | `Flying.dm` |
| Route search on the Sky level is the DM one. The engine's native search is skipped there. | board, mountain walking; `Native.dm` |
| Fog of war: 12 tiles of sight a unit; +3 on the Sky level; +3 flying; -3 at night for most races. Circles are kept in 16 x 16 cells. "Can I see this tile" looks at the circles near it. There is no line of sight: the sky sees down onto the ground, and the ground sees up into the sky. | `Fog.dm` `RmFogRadius`, `RmFogLook` |
| A unit inside something (a cage, carried) is seen where that thing stands. Only units standing on a turf give sight. | `Fog.dm` `RmFogSeesMob`, `RmFogSources` |
| 3D sends: from the surface, things on the Sky level come as `D["air"]` with each scene, about every half second. The every-tick moves push covers creatures near the camera on the camera's own level, plus only *your own* units up on the Sky level. | `View3D.dm` `Remaster3DScene`, `Remaster3DMovesPush` |
| **Cloud shadows already exist** (world-look, 2026-10-22, round 6). They are drawn on the page only: two noise layers in the ground shader. They take away up to 32% of the sunlight, about 22-tile shapes drifting at about 0.24 tiles/s. They are off at night, underground, and in `V3.lite` / `V3.noClouds`. They are not synced between players, they follow the page's own clock (which wraps every 600 s, so there is a small jump every 10 minutes), and there are no clouds overhead to cast them. The sky dome has faint clouds in the background shader. | `remastered.html`: `clk` uniform; the sky program's `fbm` |
| Siege engines are crewed vehicles already. They are built at the Carpentry (ram 3 wood; catapult 4 wood, 1 stone; ballista 3 wood, 1 iron). They have HP 500 and move only with crew within 2 tiles. They can catch fire, burn and be wrecked, and are saved with the world. A ballista shoots 2-12 tiles and hits the part it aims at; at a flyer it hits mostly the wings, so a dragon comes down. | `Siege.dm` |
| The original game's wagon is a moving container: `mob/Monsters/Wagon`, weightmax 1000, Delay 4. | `Mob/Container/wagon.dm` |
| Mine carts run by themselves between loading and unloading stops, and they ride lifts between levels. | `Carts.dm`, `Lifts.dm` |
| Ropes: Leather Rope (skin) and Silk Rope (spider silk) at the Leatherworks; Plant Rope at the Carpentry; Iron Chains at the Forge. | `StationCosts.dm`, capture-needs-rope |
| Power: a water wheel gives 10; a windmill gives 6, or 10 on a mountain top. Rune dynamos charge crystals. | `Power.dm`, `Runes.dm` |
| A grown dragon is drawn about 13 tiles snout to tail (size 2.4) but takes one tile on the map. | `Beasts.dm` `RmBeastSize` |

Today's budgets (measured; the sources are in brackets):
- **Server tick:** 100 ms. The track slice is 30 ms for all players, and the 3D share is 10 ms of it (30 while new
  ground builds). The moves push runs every tick: 2.8 ms median at 200 units. (SYSTEMS_MAP.md)
- **Page at 200 units:** `v3frame` about 1.6-1.8 ms CPU, 60 fps. (board, 10-23)
- **Page at 30k on screen:** frame median 12 ms, p95 27 ms, 35 of 360 frames over 16.7 ms. (real WKWebView paced at
  60 Hz, board 10-24 22:0x)
- **The user's rule for gear:** about 0.1 ms or less, timed directly. The same bar is used below for anything drawn
  every frame.

## 1. Clouds: three options

### (a) Looks only: clouds drift at Sky height, with sun shadows that match them on the ground

What the player sees: soft clouds floating at the Sky level's height, drifting with the wind. Their shadows on the
land are the same shapes, offset by the sun's angle. Mountain tops that reach the Sky level poke up into them. At dawn
and dusk they take the sky's colour, and at night they are dark and thin.

The cloud band's height is the page's Sky gap (`V3.SKYH`, from MOUNTAIN_HEIGHTS B), not a number of its own. At play
zoom that is likely close to the camera's own height. The eye sits about 12 units up at the default distance of 15 and
pitch of 0.9; how blocks convert to units is still to check. So the fade below (Q-C3) is needed, not a nice-to-have.

**Server** (`View3D.dm`, small):
- One **cloud field** a world: a byte per 8 x 8-tile cell, 125 x 125 = 15,625 bytes for the 1000 x 1000 Sky level. It
  is made once from a saved seed and sent to the page once. A send of 1 KB or more goes deflated (`rm_pack`, as the 3D
  updates already do).
- In each scene, three numbers: `D["cloud"] = [ox, oy, cover]`. These are the wind's offset in tiles and the cover
  level, which controls how cloudy the sky is (weather). The offset moves one tile about every 4 s, and the page glides
  between offsets.
- That makes every player see the same clouds, and gives (b) the same field for free. Cost: nothing a tick. One list
  in memory (about 0.4 MB in OpenDream's lists; a text string of the same bytes would be smaller).

**Page** (`remastered.html`, world-look's area):
- The field becomes a 125 x 125 one-channel texture, uploaded once.
- **Shadows:** the existing `clk` term samples that texture at the ground point plus the sun's offset, instead of the
  two noise layers. That is one texture read in place of two noise calls, so no dearer per pixel. They then match the
  clouds overhead, are synced, and the 600 s jump goes away.
- **Clouds**, three ways to draw them (the look is a user choice, Q-C2):
  - **a1 puffs:** soft billboard puffs, like the vapour puffs the user already accepted (`v3smokeTex`). Built into one
    static buffer for the window and moved by a uniform, so the CPU does nothing a frame. The buffer is rebuilt only
    when the window pans, a few ms a frame (like the terrain warm).
  - **a2 slab shader:** one full-screen pass that steps through the cloud band, 8-12 texture reads a pixel. No
    geometry, but all of its cost is on the GPU.
  - **a3 faceted meshes:** low-poly lit cloud shapes that cast real shadows in the sun's shadow map. These match the
    faceted rock best, but cost the most to build.
- **Never hiding the view** (the memory note sun-not-camera-shadow: own units are never hidden): clouds between the
  eye and the ground thin out to a dither near the camera and over your units, the way trees and rock already do (the
  `fp` / `rp` fade slots). See Q-C3.

| Frame budget (estimates, to be measured) | 200 units | 30k on screen |
|---|---|---|
| CPU a frame | about 0.05-0.1 ms (uniforms, one draw) | the same: clouds don't grow with units |
| GPU a frame | a1 0.3-1.5 ms, a2 1-2 ms, a3 under 0.5 ms (blended overdraw at 1600 x 900 x 2 is the risk for a1/a2) | the same |
| Window pan | rebuilt a few ms a frame, never in one frame | the same |
| Shedding | off in `V3.lite` as today; at shed level 2, half-resolution or shadows only | the same: at 30k the p95 is already 27 ms, so clouds must cost the CPU nothing there |

Rough cost: **small**, about 1-2 days (world-look). Pros: cheap, everyone sees the same sky, fixes the unsynced
shadows, gives (b) its data. Cons: looks only, no gameplay; the fade near the camera needs tuning so a cloud never
blocks a click. The faded parts are not clickable, as rock and trees already work (`v3fadedAt`).

### (b) Clouds that play: they block sight and hide flyers inside them

The same field as (a). A tile on the Sky level whose cell is above the cover level is **in cloud**. The ideas:
- A flyer, airship or walker on a cloud-wrapped peak that is in cloud is hidden from anyone more than 2 tiles away.
- Anything in cloud sees only 3 tiles.
- (Option) Ground under a cloud is hidden from eyes on the Sky level, so an army can march under cloud cover unseen by
  dragons and airships above.

Checked against `Fog.dm`, each idea is a small hook in an existing pass:

| Rule | Hook | Cost |
|---|---|---|
| A source in cloud sees 3 tiles | `RmFogRadius`: `if(RmLevelOf(M) == "sky" && RmInCloud(M))` (MOUNTAIN_HEIGHTS' helper; under B, layer 3 below the sky height is not the Sky level) | one list read per Sky-level source a fog build; ground units and ordinary mountain tops skip it |
| A target in cloud is hidden past 2 tiles | `RmFogLook` for a place on the Sky level: a hit counts only if the circle is within 2 tiles | one list read per Sky-level tile asked, kept for the tick by `rm_fog_ask` |
| (Option) The sky can't see the ground under a cloud | `RmFogLook` for ground tiles: skip circles from `SKY_LAYER` when the tile is under a cloud | one list read per ground tile seen only from the sky |
| Hidden flyers don't reach the page | already: the 3D things and the moves push leave out what `RmFogSees` says is unseen | 0 |
| Unit looks (auto-target, archers, ballistas) don't fire into clouds | `rm_foe_near` is native and knows nothing of clouds; a DM filter on candidates on the Sky level, after its pre-check | Sky-level targets only |

Server cost (estimate): under 0.5 ms a scene at 200 units; at most about 2 ms for a 4,000-thing scene, and only for
the things on the Sky level. It falls inside the 3D share's safe points. The page needs nothing extra: it already has
the field and draws your own units in cloud as usual (the owner always sees their own). Frame budget: as (a).

Limits:
- It works only where fog of war is on. Worlds with fog off (the host setting) see everything, so clouds there are
  looks only (Q-C5).
- An 8-tile cell is coarse. The page draws soft edges but the rule is per cell, so near an edge a flyer can show up a
  moment before the cloud looks thin.

Rough cost: **small to medium**, about 1-2 days after (a) (world-look owns `Fog.dm`), plus an arena check like the fog
ones. Pros: ambushes from cloud, cover for airships, mist on the highest peaks, weather that matters. Cons: invisible
rules can feel unfair, so it needs a clear "in cloud" mark on the HUD and a soft mist around your own units in cloud.
It also adds one more sight rule to `SYSTEMS_MAP.md` Part 3, so it should be written there.

### (c) Cloud islands that walkers stand and build on

What the player sees: solid islands at the Sky level over open land. Walkers can stand, walk and build there.

**The way up** (the user, via the coordinator 10-25 17:1x): walkers reach the Sky level **only by the tall sky peaks**.
Those are the top 1-10% of rock, as 10-12-block domes (MOUNTAIN_HEIGHTS section 2), and they are the way up to the
islands. Flyers and, later, airships go up by air. A dock lift (section 2.3) would be a third way for walkers, so it is
an option for the user, not a given.

**Server:**
- A new Sky-level turf kind ("Cloudstone"). It must not be the "Peak" state, or `Peaks.dm` opens it to the sky (no rock
  under it). Walkers can stand on it like a peak.
- Building on it as on mountain tops (`Construction.dm`, `Buildings.dm` already handle the Sky level as an upper floor).
- Edges keep the existing rule: walkers can't step onto open sky. If the island under them is broken they fall (the
  `Turfs.dm` fall), so a broken edge is a weapon.
- Placed by the world generator (`Biomes.dm`) and saved as dirty turfs. The far view and the explored map treat them
  like peaks.
- What is there to want (the economy's "reasons to trade"): a sky resource, for example **skystone**, an ore that makes
  airships lighter (section 2.1, lift option ii), nests of flying beasts, rare herbs.

**Page:**
- Island tops and their hanging undersides go into the upper layer (`V3.upper`), which is already built in 8 x 8 chunks
  and warmed 4 ms a frame (world-look, 10-25). A cold chunk costs about 1-3 ms, like rock. Per frame it is static
  geometry, about 0 CPU at 200 units and at 30k.
- **Sends:** the Sky level's terrain chunks are already sent as the "upper" layer; islands are only more chunks there.

**Where islands can go** (MOUNTAIN_HEIGHTS' question 4: should sky islands float over ordinary mountains too?):
- Under B, a mountain tile's layer-3 tile already holds its top, the place units stand on at its height, below the sky
  height. An island over it would need a second place on the same tile. Nothing in the game has that today: `feet` is
  one height a tile.
- **Islands only over open ground and water** need no new model. That is today's 34% open Sky. An ordinary mountain
  sent as open sky in 3D still holds its top in the data, so it can't take an island.
- **Over mountains too** needs two places a tile (a second record per tile, read by walking, building, 3D and saves).
  That is a step bigger than the islands themselves.
- Suggestion: open ground and water only, for the first islands (Q-C6).

The island's floor sits at the sky height (`RM_SKY_H`, 10 blocks), level with the tall sky peaks. A sky peak beside an
island is then the way across, by a bridge or a step.

**Placing islands against the sky peaks** (world generation; the sky peaks come from position alone, so the generator
can find them):
- **Every island within a bridge's reach of a sky peak** (a few tiles): walkers can always get there on foot.
- **Some islands by air only:** far from any peak, so they are a prize for flyers and airship owners.
- Suggestion: most islands near a peak, a few by air only (Q-C6).

Rough cost: **large**, about 5-10 days. It touches walking rules (`Gather.dm` feet heights, `WallWalks.dm`,
`Orders.dm`), building rules, `Peaks.dm`, world generation, saves and the 3D upper layer. It should wait for
MOUNTAIN_HEIGHTS steps 1-3 (the sky height, `RmLevelOf`, sky peaks) to land.

Pros: a new frontier to claim (realms in the sky, sky forts), and a reason for airships. Cons: the most work by far,
many rule seams, and floating islands are not in the LOTR / Battle for Middle-earth look (Q-C6).

### Recommended order

1. **(a)** first: cheap, synced shadows, and it lays the field (b) needs.
2. **Airships phase 1** (section 2.9), once rts-feel's Sky level has landed.
3. **(b)**, once there are airships and flyers to hide.
4. **(c)** last, after `MOUNTAIN_HEIGHTS.md` and airships phase 3, if the user wants it at all.

## 2. Airships: the game's first vehicles that carry units

Siege engines are the base to build on. They are crewed, select and move like units, have HP, burn, are wrecked and
are saved with the world (`Siege.dm`). An airship is a new kind of the same thing that flies and carries people:
`mob/Monsters/RemasterAirship`, one tile on the map, drawn big (like a dragon).

### 2.1 What lifts it (flavour, weaknesses, economy)

| Option | How it works | Pros | Cons |
|---|---|---|---|
| **i. Hot-air** | A silk (or leather) envelope over a forge-made burner that burns wood or coal | Medieval-believable; uses materials the game has; fuel is a steady demand on the economy; a clear weakness: fire (fire arrows, Alchemist's Fire, dragon breath) | Not LOTR; fuel must be hauled; without automation that is micromanagement |
| **ii. Skystone / runes** | Lift stones of a new rare ore (tallest peaks, the depths, or islands from (c)), kept up by rune crystals charged by a rune dynamo | Ties into `Runes.dm` and power; scarce by region, so a reason to trade and fight; no fuel hauling | A new ore and mana balance to tune; "magic does it" |
| **iii. Beast-drawn** | A gondola pulled by tamed dragons or great eagles | The most LOTR-like (the Eagles); uses `Taming.dm` and beasts that already fly and fight | Needs tamed beasts (rare) and their food and rest; the gondola must follow the beast exactly (no-sliding rule) |

Suggestion: (i) for the first ship and (ii) later as an upgrade (lighter, more cargo, no fuel). The user decides (Q-A1).

### 2.2 Kinds, crafting and crew

| Kind (first guesses) | Carries | Where built | Materials (rough, to tune) | Moves (ticks a tile) |
|---|---|---|---|---|
| **Skiff** | 8 (a hero party of 3-8: towns-and-heroes) | Carpentry, like siege engines | 20 wood, 4 iron ingots, 4 rope, 6 spider silk, a burner (Forge, 2 iron) | 4 (a wagon's pace) |
| **War galleon** | 40 (a war band) | a new **Shipyard** | 80 wood, 20 iron, 20 rope, 30 silk, 2 burners (or skystone) | 6 |
| **Cargo barge** | 12 people + about 3,000 weight | Shipyard | 60 wood, 12 iron, 16 rope, 24 silk | 7 |

For comparison: siege engines are Delay 7-9 and a wagon is 4.

- **Where it's built:**
  - Skiffs at the Carpentry, the same as siege engines.
  - Big ships at a Shipyard: a large workshop with a slipway, put down as a blueprint. Builders bring materials and
    build it in stages (keel, hull, envelope, rigging), so the player plans and the workers do the rest
    (plan-dont-micromanage). The Carpentry's Woodwork skill sets the quality, and quality gives more HP and speed.
- **Crew:**
  - A ship moves only with a **pilot** aboard (the siege rule: someone of yours with it).
  - Hot-air ships also need a **burner tender**; without one the ship slowly loses height.
  - More crew means faster repairs in the air (crew with wood aboard).
  - Crew count against the places aboard.
- **A new skill?** "Airmanship" (raising speed and turning), or reuse Woodwork for building and plain Speed for
  flying (Q-A6).
- **Upkeep:** fuel by the minute of flight (option i) and food for people aboard, taken from the ship's own store.
  People aboard eat, sleep in hammocks (rough sleep, +5) and keep their needs on the unit clock as usual.

### 2.3 Boarding, getting off, carrying a war band

- **People ride inside the ship** (their `loc` is the ship, like a captive in a cage), not as units standing on deck
  tiles. The ship draws them on its deck in fixed places.
  - Their walk loops are parked, so they cost less than the same units walking.
  - Fog already sees them where the ship is (`RmFogSeesMob`), and the ship itself becomes the sight source.
  - The other ways (deck tiles that move with the ship, or units glued to it step by step) cost far more and break the
    clip and no-stacking rules.
- **Boarding:**
  - Select people, then right-click the ship: Board. Or click the ship with people selected. A Company group boards
    together and stays a group.
  - They walk to it, then step in one at a time (about 1 s each).
  - Possible when the ship is **landed** (open ground), **hovering beside a sky peak or island** on the Sky level (a
    gangplank to a free tile next to it, at the sky height), or **moored at a dock** (below). Ordinary mountain tops
    are below the sky height under MOUNTAIN_HEIGHTS B, so a ship reaches them only flying low.
- **Getting off:** in the ship's card, Unload all or one person. People are put on free tiles round the ship, never
  stacked, by the clip rules. That works on open ground, or on peak tiles next to it on the Sky level. If there is no
  room the order waits, with the red "can't" ping.
- **Rope ladder (option):** hovering low over the surface (2 tiles), people climb down a rope one at a time, about 3 s
  each, while they can be shot. This needs a rope aboard, which ties capture ropes into the system.
- **Docks (option):** a mooring mast built on the ground with a lift inside (`Lifts.dm`'s stair pair). Its top is a
  platform on the Sky level, like a tower top. A ship moors there; people and cargo go up and down by the lift. Walkers
  board at the Sky level without the ship ever landing, and carts can run to docks (`Carts.dm` stops). That makes a
  dock a way up for walkers besides the tall peaks, which is the user's call (Q-C6). A dock that stops below the sky
  height, where ships moor flying low, avoids it.
- **A war band:** one galleon carries one band (about 40). Bigger armies are several players' ships together, which
  fits warband-real-formations: battles are many players' bands. **Formations are on hold** (the user, 10-25 12:30): a
  band gets off round the ship as a group, and nothing more is built for formations until the user brings them back.

### 2.4 Moving on the Sky level, landing

- **Orders as for siege engines:** select the ship, click open sky (rts-feel's open-sky clicks for flyers) and it sails
  there. Fly higher and Fly lower work as for flyers: low over the surface (2-6 tiles), or up to the Sky level.
- **Routes:** the DM search on the Sky level, round tall peaks, islands and other ships. Ships are few (dozens), so the
  DM search is affordable. The ship's tick should be a unit-clock job, not a new world loop (`SYSTEMS_MAP.md` fold plan
  step 3).
- **Two heights matter for combat (Q-A7):**
  - **Low** over the surface: archers can hit it and its crew, ropes can drop, and dropped bombs land where aimed.
  - **On the Sky level:** out of bow reach (bows reach 5-7). Only ballistas (12), dragons, casters with long reach and
    other ships can hit it.
- **Landing rules (all user choices, Q-A8):**
  - Open flat ground with the ship's footprint free: a skiff 3 x 3, a galleon 5 x 3. That is `RmLandingBlocked` over
    the footprint: no dense ground, no dense things, no units.
  - Not on water, unless the user wants ships that float.
  - Not inside another realm's land unless at war or allied (`War.dm`, `Claims.dm`).
  - Never onto a mountain top. A ship hovers beside one instead.
- **No sliding** (the user's rule): the ship moves tile to tile in game logic. The page glides it at the step's length,
  as it does for units, and only turns it to face its way. People aboard are drawn as part of the ship, so they never
  drift off the deck. Take-off and landing ease up and down, as flyers already do.
- **Sends:** a ship on the Sky level is not in the moves push for players looking from the surface (today only your
  own units up there are). Others' ships would then glide only twice a second. **Needed:** add airships and flyers on
  the Sky level to `Remaster3DMovesPush` for surface viewers. The extra range() pass at the Sky level costs well under
  1 ms at airship numbers (estimate).

### 2.5 Damage, sinking, crashing

- **Parts:** hull, envelope (or lift stones), burner and rudder, aimed at like a beast's parts. A ballista already hits
  the part it was aimed at, and the right-click in 3D picks a part (`Beasts.dm`).
  - **Envelope** hits lose lift.
  - **Burner** hits stop the climb.
  - **Rudder** hits slow turns.
  - **Hull** hits take HP.
- **Fire:** as siege engines burn (`Siege.dm`: `Fire()` and `RemasterSiegeDamageTick`, 15 HP a second until the crew
  beats the flames out in 3 s). A burning envelope also loses lift fast. Crew aboard can put it out.
- **Sinking:** when lift falls below weight, the ship drops one height step every 10 s (estimate) until it lands where
  it can. Throwing cargo out, or setting people down, stops the drop. An overloaded ship can't take off.
- **Crashing:** HP 0 in the air. The ship falls straight down onto the tile below (game logic, no glide sideways) and
  leaves a wreck that can be salvaged for part of its wood, iron and silk.
  - People aboard get the original game's fall (`Turfs.dm`: legs mangled, blood lost), harder by height. From the Sky
    level there is also a chance of losing limbs or dying (Q-A9).
  - Over water it sinks: people swim if their race can, or drown.
  - Over a chasm it is lost.
  - On a mountain top the wreck lies there.

### 2.6 Fighting from a ship, sieges

- **From the deck (option):** archers and casters aboard shoot at what is in reach of the ship's tile, keeping the
  ranged-then-melee rule (aboard, only ranged).
- **Bombs (option):** drop fire brews or rocks onto the tile below, on the catapult's damage line.
- **A deck ballista (option):** a ballista built onto a galleon.
- **Ship to ship (option):** at war, side by side, the crews board and fight (a later phase).
- **Sieges:** ships go over walls, which undercuts walls and gates. Counter-play is needed and ships should not make
  walls pointless (Q-A11):
  - ballistas on towers and wall walks;
  - landing in enemy land only at war;
  - people getting off one by one while defenders shoot;
  - banner sieges still need units standing by the banner.

### 2.7 Capture, the economy, the MMO

- **Capture:**
  - Captives ride roped (their break-free rolls go on, and crew near them lower the odds as now) or in a cage carried
    as cargo. Today a cage with someone in it can't be picked up; ship cargo would be the one exception (Q-A12).
  - A captive who breaks free aboard fights the crew, or jumps and takes the fall.
  - Slaves could tend burners (labour only), keeping the "never fight" rule.
- **Economy** (player-run-feudal-economy):
  - **Sky haulage:** a cargo barge runs a standing route between docks, loaded and unloaded by haulers, as mine carts
    do between stops.
  - **Demand:** fuel (wood or coal), silk (spider farming), iron and skystone.
  - **Shipwright houses** build and sell ships at their stalls.
  - **Sky tolls:** a ruler law over the sky above their land, since road tolls don't reach the sky (Rulership's laws).
  - **Piracy:** raids on sky caravans by other ships and dragons.
  - The king sees only declared and observed ships and cargo, never a house's hidden plans.
- **Scale:** a ship is one mob, and its people inside are parked, so a full galleon is cheaper for the server than 40
  walking units.
  - An offline player's ship on a route over asleep land becomes a far record (`FarRecords.dm`): position, route,
    cargo, and its people as rows.
  - The page draws people on deck as instanced records, the same cost as the same units standing (gpu-unit-drawing:
    new per-unit visuals must write records).

### 2.8 The 3D model, in the project's pixel-art style

| Option | What | Pros | Cons |
|---|---|---|---|
| **M1. The dragons' way** | A mesh (`meshes.py`-style, or Blender) rendered from 16 facings, made pixel art (banded ramps, dark outline, 64 px a tile: `beasts64.py`, `pixelgear.py`), drawn as a billboard like a beast, with frames for sails, burner and damage | Looks exactly like the units and beasts; one pipeline | People on deck can't sit inside a flat picture. It needs two pictures per facing (the hull behind the deck, the rail in front) with the people drawn between them. Big atlases: 16 facings x frames x states, like the dragons. Its shadow is a sprite shadow. |
| **M2. A real 3D model on the page** | Built in JS like the siege engines and the cage (beams, planks, blobs), smooth-shaded like the world | People stand on a real deck at the right depth; real cast shadows in the sun's shadow map; turns smoothly; built once and cached | Not pixel art itself: it reads like a building, not a beast |
| **M3. Hybrid** (suggestion) | A real 3D hull and deck (M2), with envelope, sails, banners and figurehead as palette pixel-art pieces from the gear pipeline (`smoothgear --index`, coloured on the page in the realm's colour) | People stand on a real deck; the parts that carry the look are pixel art; banners in the claim colour; the gear pipeline already does indexed pieces at 16 facings | Two pipelines in one model; the joins between them need care |

Sizes against a grown dragon (about 13 tiles): skiff about 5 tiles, galleon about 10 (Q-A14). When shown, put a
person beside it for scale (huge-beasts-pixel-art).

Frame cost (estimate): M2/M3 ships are a few thousand triangles each, built once and kept while unchanged (like
`kd.rc`). For a handful on screen that is about 0.05 ms CPU a frame, under the gear bar. 40 people aboard are 40
records, the same as 40 units. M1 costs texture memory rather than CPU.

### 2.9 Phases and rough cost

| Phase | What | Rough cost | Needs first |
|---|---|---|---|
| 1 | Skiff at the Carpentry; board and get off when landed or beside a peak; fly low or up to the Sky level; landing rules; HP and wreck; the 3D model (one option); the moves push for Sky ships; arena check, headless, one real window | about 4-6 days | rts-feel's Sky level landed |
| 2 | Parts, fire, sinking, crash with falls, shooting from the deck, bombs | about 3-4 days | phase 1 |
| 3 | Shipyard, galleon and barge, docks with lifts, cargo routes, fuel and upkeep, far records, sky tolls | about 5-8 days | phase 2; the economy's stewards |

Who: a new airships session for the server (`Airships.dm`, beside `Siege.dm`); world-look for the page and fog parts;
the gear3d pipeline's owner for the model; rts-feel for the Sky level's clicks and moves. Each phase is its own landing
with a restore point, the coordinator's OK and an app build.

## 3. Risks

- **Sky level heights:** rts-feel picks the Sky level's flying heights, and `MOUNTAIN_HEIGHTS.md` the sky height
  (`RM_SKY_H` on the server, `V3.SKYH` on the page). The clouds' drawn height, the islands' floor and the ships'
  heights must use those numbers. Read them from there and don't copy them.
- **Clicks:** clouds and big ships sit between the camera and the ground. They must fade and never take a click meant
  for the ground (the `v3fadedAt` rule for rock and trees).
- **Walls:** airships change sieges more than anything since siege engines. Phase 1 should ship without bombs or
  shooting from the deck, so the user can feel them before they become a weapon.
- **30k frames:** the page is already at p95 27 ms with 30k on screen. Clouds and ships must cost the CPU nothing a
  frame there. Time them directly, paced at 60 Hz (frame-probes-pace-60hz).
- **The fold plan:** no new world loops. Ships tick on the unit clock, and their 3D work goes through the 3D share and
  entry reuse.

## 4. How to check (when built)

- Clouds: the page's frame cost, timed directly in a real WKWebView paced at 60 Hz, at 200 and 30k, with clouds on and
  off. No-input probes (arena-first-testing), then one real window.
- Clouds (b): an arena check in the style of the fog checks (`check_arena.py`). A flyer in a cloud is unseen past 2
  tiles, seen at 2, and always seen by its owner. Archers don't auto-target into a cloud.
- Airships: an arena check for board, get off, fly, land, crash and saves, at speed 4 (tests-at-speed-4); then one
  real window with real input for the feel.

## 5. The user's choices

Clouds:
- **Q-C1. Which, and in what order?** Suggested: (a), then airships phase 1, then (b), then maybe (c).
- **Q-C2. The clouds' look?**
  - a1, soft puffs like the vapours;
  - a2, a soft volume;
  - a3, faceted like the rock.
  - Also: banded "pixel" shading in two or three tones, or smooth? Suggested: a1 with soft banding.
- **Q-C3. On the surface, how do clouds overhead behave?**
  - They thin out near the camera and over your units (like trees and rock).
  - Or only their shadows show on the surface, and the clouds themselves show on the Sky level and when zoomed out.
  - Suggested: thin out.
- **Q-C4. Weather?**
  - Should cloud cover change (clear days, overcast) and differ by biome or season?
  - Should the wind's direction change?
  - Suggested: cover changes slowly, one wind for now.
- **Q-C5. For (b):**
  - Do clouds hide the ground under them from eyes in the sky?
  - On worlds with fog off, are clouds looks only?
  - Suggested: yes to both.
- **Q-C6. For (c), if wanted at all, what are the islands?**
  - Solid cloud.
  - Rock held up by skystone or runes.
  - No islands: the tallest peaks are the "sky islands".
  - Note that floating islands are not in the LOTR / Battle for Middle-earth look.
  - Where: over open ground and water only (suggested; no new model), or over mountains too (two places a tile, a
    bigger change). This answers MOUNTAIN_HEIGHTS' question 4.
  - Reach: every island near a sky peak, or some by air only (suggested: mostly near a peak, a few by air only).
  - May a dock lift take walkers up to the Sky level too, or are the tall peaks the only way up on foot?

Airships:
- **Q-A1. What lifts them?** Hot-air, skystone and runes, or beast-drawn. Suggested: hot-air first, skystone later.
- **Q-A2. Kinds and sizes:** skiff 8, galleon 40, barge 12 + cargo, or other numbers?
- **Q-A3. Where are they built?** Skiff at the Carpentry and big ships at a new Shipyard, or everything at one?
- **Q-A4. People inside the ship and drawn on deck** (suggested), or real units standing on deck tiles (far dearer)?
- **Q-A5. Ways on and off?**
  - landed;
  - beside a mountain top;
  - a rope ladder from low flight;
  - docks with a lift.
  - Which of these, and in which phase?
- **Q-A6. Crew:**
  - a pilot needed to move;
  - a burner tender needed to keep height;
  - a new Airmanship skill, or none.
- **Q-A7. Reach:** can bows reach a ship on the Sky level? Suggested: no; only ballistas, dragons, casters with long
  reach and other ships.
- **Q-A8. Landing rules:**
  - free footprint;
  - water allowed or not;
  - others' land only at war or allied.
- **Q-A9. A crash from the Sky level:** falls as the original game's (legs mangled), plus a chance of losing limbs or
  dying?
- **Q-A10. Fighting from ships:** shooting from the deck, bombs, deck ballistas, boarding between ships. In which phase
  (suggested: none in phase 1)?
- **Q-A11. Sieges:** how strong may landing behind walls be? Which counters: ballistas on towers, landing at war only,
  people getting off one by one?
- **Q-A12. Captives aboard:**
  - roped and in cages as cargo;
  - may a slave tend the burner?
- **Q-A13. Economy:** cargo routes between docks, fuel demand, sky tolls by law, shipwright houses. Which of these, and
  when?
- **Q-A14. The 3D model:**
  - M1, the dragons' way;
  - M2, a real 3D model;
  - M3, a hybrid.
  - And the sizes against a grown dragon (about 13 tiles)? Suggested: M3, skiff about 5, galleon about 10.
