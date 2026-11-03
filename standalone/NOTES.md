# Dungeon Master standalone: project notes

Updated 2026-10-22.


## Host-only create and edit links — October 22, 2026

`client/Topic` in `game/Code/plugin.dm` handled `?command=create;type=…` (spawn any object beside
the player) and `?command=edit;target=…` (change any variable of any object) with their admin checks
commented out, so any connected player, web players included, could use them. Both now go through
`client/proc/RemasterAdminTopic`: allowed for the host (`RemasterIsHost()`, i.e. the hosting Mac's
login name, or everyone in solo play), `world.host`, and GM/DE players; everyone else gets "Only the
host can use create" and a world.log line. Verified on a private world as a non-host web player.

## Skill pacing and the repeated level-up line — October 22, 2026

Two changes. (1) The HUD's toast de-duplication (`remastered.html`, `toast()`) compared the message
with the previous one *before* stripping the player's `{name}` tag, so with named units (every
multiplayer and web player, and any house with a name) nothing ever matched and every HUD tick
re-posted the current notice: "Woodcutting level 2!" ×8, "Gathered" ×40. The compare now happens
after the strip; verified on a private world: one line per level-up and per "Gathered".
(2) Skills levelled at the same XP an hour from 1 to 99 (a Dwarf reached Woodcutting 30 in
18 minutes). `Skills.dm` now scales training XP by level (`RemasterXPRate`: 0.15 + 0.0086×level,
capped at 1), so XP an hour grows with the level as in RuneScape: Woodcutting 10 in ~8 min, 30 in
~1 h, 50 in ~5 h, 99 in ~335 h of uninterrupted chopping (table and reasoning in
[remastered/planning/SKILLS_PACING.md](remastered/planning/SKILLS_PACING.md)). Measured: level 2
after ~45 s of chopping (was ~7 s). Work speed (blows per tree/rock) is unchanged. The unused
`RemasterSkillPace`/GRIND constants were removed. The game was recompiled; the app was not rebuilt.
Later the same evening: the level scaling now applies only to the per-blow skills (Woodcutting,
Mining); crafts, meals, walls, fish and combat keep their full per-item XP. Per-item work takes time
as in RuneScape: a cook spends 3 s on each meal (`RM_COOK_EVERY`, FoodRoles.dm) and a work-board
station craft takes 3 s (`RM_CRAFT_EVERY`, StationCraft.dm); before, both ran every half-second tick
(five meals in under 5 s). Measured: Mining 2 after 51-59 s of mining; Cooking 2 at 9 s (3 meals)
and 3 at 18 s (6 meals). The web relay learned to read prompt buttons (their text sits in a child
Label) so alert() Yes/No now show in the browser. Follow-up: `client/Topic` `?command=create` (plugin.dm)
has its admin check commented out, so any player, web players included, can spawn any object.

## Playing in a web browser — October 22, 2026

Remastered can now be played from a browser tab: `remastered/tools/web_host.py` runs a lobby on
the hosting Mac and starts one headless engine client per web player, with a new WebView module
(`remastered/web-relay/`, built to `remastered/engine/webview-relay/`) that serves the HUD page
over HTTP and relays the game's `output()` calls and the page's `byond://` commands over a
WebSocket. Native prompts show as cards; the skin's keys reach the engine. Verified on a private
test world: password prompt, race choice via the R macro, unit selection and a move order. Two
small game changes: `ready` resends the 3D scene, and a returning player's login resends the HUD
page. Not yet tried against the app's hosted world or from another computer. Details and cost:
[remastered/planning/WEB_CLIENT.md](remastered/planning/WEB_CLIENT.md).

## HUD follows the window — October 22, 2026

`game/Interface/remastered.html`: Settings → HUD size now has **Auto** (the default), which
zooms the page from the window's size (designed at 1440x900; clamped 0.6x–1.6x) and re-applies on
resize; the fixed sizes stay. Zoom needed three more things, which also fix the old Small/Large
settings: the 3D canvas and 34 stylesheet rules used viewport units (`100vw`/`vh`), which ignore
zoom, so the map only filled part of the window (now `--sw`/`--sh`, the window in zoomed pixels);
mouse positions are read through `mx(e)`/`my(e)` (`hudK()` is the factor between the engine's
unzoomed event/rect pixels and the zoomed layout, 1 where the engine already zooms them), so
clicks, box-select and right-click land where the cursor is; and `placeRoster` (minimap panel under
the menu, company list under the minimap) divides its measured rects by the same factor. Verified
at 0.76x in the Claude browser: click, box-drag and right-click all hit the dwarves. The app needs
a rebuild (`tools/build_app.py`) to carry it; web players get it as soon as the hosted world restarts.

## Main playable build — October 21, 2026

The main app is **[remastered/Dungeon Master Remastered.app](remastered/Dungeon%20Master%20Remastered.app)**. Claude's current Remastered source has been built and promoted there, including the four later claim-save, raider-cleanup and renderer-priority fixes. The source, 3D HUD and gameplay rules were preserved during promotion. `remastered/dist/` remains the older October 20 share package.

Both personal and shared apps use the Mac login account (`@login`). On this Mac that opens the existing `kiwimango` army of three Dwarves, rather than the empty legacy `Kiwi` roster. No normal save was restored, replaced or modified. Classic save bundling is now opt-in.

The promoted package passed private Human startup/save/reload and a separate load/save of copied current Dwarf/world saves. The original main app and save copies are retained in `remastered/restore-points/before-main-promotion-20261021/`. Details: [promotion receipt](remastered/reports/main-promotion-2026-10-21/PROMOTION.md). Earlier dated sections below are historical; the [current README](remastered/README.md) is the launch guide.

## Which game is which

| Folder | What it is | Status |
| --- | --- | --- |
| `remastered/` | **Dungeon Master Remastered**: the original game plus new controls. **This is the game we work on.** | Playable: `remastered/Dungeon Master Remastered.app` |
| `replica/` | **Dungeon Master (Classic)**: the original game source running with BYOND replaced. Reference only; don't change the game. | Playable: `replica/Dungeon Master.app` |
| `frontier/` | Old Godot experiment (maps and sprites only, no game rules). Not used. | Set aside |

Both playable games run on the same engine (OpenDream, no BYOND needed) and
keep separate save folders in `~/Library/Application Support/`.

The current editable project is **remastered/game/** and its current app is
**remastered/Dungeon Master Remastered.app**. Easy Orders and the sprite asset
pipeline are being integrated there. The older `remastered/dist/` release is
preserved as the previous share package; use the app directly inside
`remastered/` for the latest changes. Progress is recorded in
`remastered/planning/EASY_ORDERS_PLAN.md` and `remastered/planning/SPRITE_PIPELINE.md`.

## Rules

- New features and visual changes go in **Remastered** only.
- **Classic stays untouched.** It is the reference for how the real game behaves.
- Engine bugs (like the arrow keys, sounds and inventory list fixed today) are
  fixed once in the shared engine files in `replica/` (tools and runtime, never
  the game code); Remastered picks them up on its next rebuild.
- Test changes by actually playing them. Earlier automated checks missed real
  keyboard and mouse problems.

## Done so far in Remastered

- Click a unit to select it; Shift+click to add or remove; double-click to
  select all of that race on screen.
- Drag a box to select (green box shows while dragging).
- Left-click/tap to move, attack, gather or open supported workshops. Right-click
  lists commands exposed by the original object; it is not a universal interaction
  menu. Carried items use the unit inventory card; some older ground menus use double-click.
- Control groups on 1-9, Ctrl+1-9 and Shift+1-9.
- Health bars over your units; "under attack" alerts with Backspace to jump there.
- Controls contains the original commands and shortcuts; F3 opens the full guide.
- HUD icons and build-menu buttons work with one click.
- The map now defaults to a clean view. A labeled command dock replaces the
  ring of tiny icons: Stop, Interact, Focus, and Controls. All 44 commands remain
  available in searchable purpose groups, with original glyphs and descriptions.
  Controls can restore the Classic border; the choice is saved. The camera and
  minimap collapse to leave more room for units. See `remastered/planning/COMMAND_DOCK.md`.
- Pick-up and drop actions say what happened (including the carry-weight limit).
- F3 opens the Controls & Actions guide. Full list: `remastered/ACTIONS.md`.
- Easy Orders: per-unit tasks continue after deselection, with queues, pause/resume,
  filtered drop-off (including opt-in Mining supplies) and bounded worker roles. The gold Deselect button stays
  visible while scrolling; Space clears selection and modes without stopping work.
- Automatic defense is implemented in Remastered: each unit can Help nearby,
  Defend self, or choose No response. For covered attacks, helpers hear threats within 8 tiles on the
  same level, including across walls, and still need a route. Cards show Responding
  or Returning while retaining prior work. All 103 real-game defense checks and
  56 HUD checks pass; the rebuilt app passed private startup/save/reload with the normal save unchanged.
  Details: `remastered/planning/DEFENSE.md`; remaining attack families are listed in `remastered/planning/DEFENSE_REMAINING_SCOPE.md`.
- Fixed generated sprite frame/direction ordering in the shared engine so composed
  clothing/equipment layers keep the unit's facing. Original sprite files and
  Classic game rules are unchanged.
- Fixed movement-only animation playback in the shared engine: idle body,
  hair and equipment hold still; walking animates them, and animated scenery
  continues normally. Real-unit native start/stop/teleport/layer tests pass.

## Layered HUD (2026-10-17)

The map now fills the window, and the HUD floats over it (a mix of Crusader Kings and WoW):
- **Layout:**
  - Top-left: realm block with Units / Village / Orders / Work / Guide.
  - Top: resource and date bar.
  - Top-right: round minimap.
  - Right edge: company outliner.
  - Bottom-left: hero frame (one unit selected) or settlement frame.
  - Bottom centre: action bar.
  - Bottom-right: event toasts.
  - Left: slide-in panel for the character sheet, orders and work.
- **Village tab:** a wide roster of everyone with filters (idle, hurt, hungry, tired, workers, rulers), search, sort, per-villager Job / Priority / Defense and Go, plus tick boxes for bulk changes and "Select on map".
- **Engine:** the HUD is `mapwindow.hud`. Remastered's own web module (`remastered/mac-webview`) lets a page post its clickable regions to `dmOverlay`. The page then turns see-through, clicks elsewhere reach the map, and OpenDream's white browser backing panel is cleared.
- **Log and Classic info:** these open as a strip under the map from the top bar.
- **Families and houses** (`Code/Remastered/Lineage.dm`, check: `tools/check_family.py`):
  - Births, eggs and deaths are recorded with saved ids, parents, partners, house and generation.
  - Shown under Village › Lineage & connections.
- **Self-care and homes** (`Code/Remastered/Care.dm`, check: `tools/check_care.py`):
  - Villagers claim a home bed and sleep rough if there's none.
  - They walk to a campfire when cold, and to the stockpile when hungry with no food.
  - Orders and jobs are kept and resume afterwards.
- **Bulletin board** (`Code/Remastered/Board.dm`, check: `tools/check_board.py`):
  - Village › Bulletin board: post work orders (chop wood, mine stone, collect food, craft) with amount, priority, worker count and place.
  - Villagers with the job "Board worker" claim them, using the existing woodcutter, miner, food-haul and carpentry engines.
  - Standing orders ("keep at least N") post work by themselves when the stockpile is low.
  - Progress counts stockpile gains. Orders and standing orders are saved.
- **RuneScape-style skills** (`Code/Remastered/Skills.dm`, `Tools.dm`, check: `tools/check_skills.py`):
  - Each skill's existing number is its level, with progress to the next.
  - XP drops ("+15 Woodcutting XP") and level-up banners.
  - A skill grid with total level in the character sheet.
  - A clickable skill guide built from the verified game formulas.
- **RuneScape grind** (gameplay change, `Skills.dm`):
  - Training gains are scaled by level, so the effort per level doubles every 10 levels, with a floor of 0.1% pace from level 100.
  - Chopping 1→99 is about 89k swings (about 25 hours).
  - XP is shown on RuneScape's table (99 = 13,034,431).
  - One-off boosts over 5 points in a second (crowning, inheritance) aren't scaled.
  - All game formulas still read the raw skill value.
- **Tool tiers** (gameplay change): axe and pickaxe material speeds chopping and digging (Wooden ×1 → Hell-Forged ×2.2) once the villager reaches the tier's level (5/15/25/35/50/75); below that they work at basic speed.
- **3D view, route 2 proof** (`Code/Remastered/View3D.dm` plus the WebGL renderer in `Interface/remastered.html`):
  - The game keeps every rule. The server sends the tiles and things within about 20×15 tiles of the camera.
  - The HUD page draws them in 3D:
    - ground and walls textured with the game's own tile art;
    - tree models;
    - lower water;
    - units, workshops and items as camera-facing sprites, with rings and health bars.
  - Controls: the 3D button or F8; right-drag or Q/E to turn, wheel to zoom, WASD to move.
  - Clicks go through `client/Click`, the same code path as the 2D map.
  - Not done yet: real 3D models and animation, wall art per side, a bigger view radius, and keyboard shortcuts while the 3D page has focus.
  - **Layers:**
    - Sky, Surface, Caves and Depths stack in 3D.
    - "," and "." dive and rise with a camera animation.
    - Flyers on the Sky layer hover over the surface, and the surface shows far below the Sky.
    - X toggles an x-ray ghost of the layer above.
  - **Views (C cycles):**
    - Diorama: the layer below is drawn as solid rock with its tunnels.
    - Cutaway: the near half is cut open to show the layer below.
    - This layer only.
  - **Terrain:**
    - Surface rock rises into terraced mountains by depth.
    - Units show the sprite side they face relative to the camera, with gear.
    - Your units hidden behind walls show a green silhouette.
  - **Building kit** (`Code/Remastered/Blueprints.dm`, check: `tools/check_blueprints.py`):
    - Player-built walls (`IsWall`) are drawn as connected wall pieces in their material, and built floors are raised.
    - Rooms of built floor walled in (one or two doorways allowed) get a stepped hip roof that hides when zoomed in, when a selected unit is inside, or in cutaway.
    - With a build mode active, a green/yellow/red ghost follows the mouse. Drag outlines walls or fills floors. Esc stops.
    - Painted tiles become blueprints. The selected builders walk next to each one and build it with the original build code.
    - **Construction sites:** a builder without the material fetches it from loose piles within 15 tiles or the stockpile. If there's none, the site posts a "Chop wood / Mine stone for building" order on the bulletin board and waits.
    - **Workshops** (Work tab › Place a workshop): two-tile ghost in 3D. The builder fetches the material (1 wood or 1 stone), stands on the spot and builds it with the original `Create…()` proc. The workshop is owned by the player.
- **World saving** (`Code/Remastered/WorldSave.dm`, check: `tools/check_world.py`):
  - Runs inside `SaveUnits()`, so it saves on autosave and on quit. Saved to `units/remaster_world.sav`; restored right after the map loads.
  - Saves tiles that differ from the map in 16×16 areas player units visited: walls, floors, bridges, dug tunnels, felled trees.
  - Saves items made or dropped on the ground and workshops, as records (type, simple settings, owner key, contents), never as whole objects (OpenDream's saver recursed forever on item graphs).
  - Also saves the calendar and land history.
  - Blueprints and builder flags are saved with the player. A save attempted during startup is refused.
  - Restored items and workshops are handed back to their player on login.
  - Not covered: map loot picked up and dropped elsewhere respawns at its map spot (original behaviour). Real-map two-launch check: save and load run cleanly, but a built change hasn't been restarted in real play yet.
- **Art direction:** a separate art-lead session is building a Blender pipeline and prototype in `remastered/art/` and `planning/ART_DIRECTION.md`. Not wired into the game yet.
- **Real-map scenario** (`tools/check_scenario.py` plus `tests/scenario_test.dm`):
  - Two launches of the full 1000×1000 map. Launch 1 settles six Orcs by a real forest, plans a room plus a carpentry with no wood, lets the real RemasterTrack run (board workers chop, builders fetch and build) and breeds a couple. Launch 2 verifies everything was restored.
  - Passed 2026-10-17 (12/12 walls, 4/4 floors, carpentry, child, house, standing order, owner key; 0 runtime errors).
  - It found two real-map bugs, now fixed: board workers stalled when nearby trees ran out (they now move to the nearest uncut trees), and builders walled rooms shut before laying floors (floors now go first).
  - Note: this game writes `world.log` to `ErrorLog.txt`.
- **Two-storey houses in 3D:** Sky-layer floors and walls above the surface draw one storey up, stairs are drawn as steps, and roofs sit on the top floor. The upper storey lifts away when zoomed in or in cutaway.
- **Food chain roles** (`Code/Remastered/FoodRoles.dm`, check: `tools/check_food.py`): Farmer (tills with a spade, plants seeds, harvests), Hunter (hunts critters, butchers, fishes) and Cook (campfire or kitchen) repeat the original actions and store food on the stockpile. Items lying on a stockpile no longer expire.
- **Village crafting at every workshop** (`Code/Remastered/StationCraft.dm`, check: `tools/check_station.py`): the board can post "Make N <recipe> at the <workshop>" for the forge, smelter, carpentry, bone, leather, masonry, gem cutter, kitchen, potion and poison stations. Recipes are read from the real station menus (per race), and a board worker fetches materials from the stockpile, runs the original menu with the answers filled in, and stores what it makes. Orders it can't make say "missing materials or skill". The Melter and Wooden Arrows (which asks for an amount) are left out.
- **Hero / Village mode** (`Code/Remastered/PlayMode.dm`): a Hero | Village switch in the top bar. Hero mode pins your hero in the hero frame when nothing is selected, opens the Units tab and can make the camera follow them; Village mode opens the Village tab. "Make my hero" / "Make head of the family" picks the hero.
- **Heirs and succession** (`Code/Remastered/Succession.dm`, check: `tools/check_heirs.py`): the hero is the head of the family. Heir rule: named heir, eldest child, eldest sibling, eldest of the house, then the eldest of anyone. When the head dies the heir takes the hero frame at once and a banner offers "Crown as King/Queen", which runs the original Declare Leader (its one-hour wait still applies). Lineage shows ★ head and ⚑ heir, with "Name as heir".
- **Neighbours help:** a hungry villager with no food anywhere gets a neighbour (within 20 tiles, with food to spare) to walk over; the original eating rule then takes the food. The Village roster has a "Village needs" line.
- **3D works like the map** (2026-10-18): 3D opens facing north (N in the page resets). Clicks hand the keyboard back to the game, so every original shortcut works in 3D; arrows move the camera, right-drag turns, wheel zooms. Double-click, right-click menu (Select / Move / Attack, Use, Set magic target) and drag-box selection. Line of sight: tiles the map blacks out are dark in 3D and things on them hidden. Units glide (positions 5×/s, steady per-step speed). Corpses, dig marks, blood, fire and smoke are drawn; workshop signs are baked into the station picture; pixel offsets and big icons are placed like the map. Clicking a cliff or tree face picks that tile. The ground is checked every tick, so felled trees and dug rock vanish at once. Order targets of the selected units are outlined tiles with queue numbers, and lines run from each unit through its queue. The old map border/palette hide in 3D. Attack alert hides 30 s after the last hit or with ×.
- **3D round 2** (2026-10-18): 3D fills the window (a minimap style had clipped it to an oval). Zooming out widens the area sent (41x31 up close, up to 101x81; the far ground refreshes about every 3 s, close ground every tick). No white flash: units keep their last picture until a new one loads, ground shows its kind colour. Group moves form up (each unit its own open tile near the target, keeping the group's shape; check: `tools/check_formation.py`). The Company list shows fights ("Fighting X", "Fighting back against X", "Helping Y against X", "Attacked by X!") and a hover log of recent events (`Code/Remastered/CombatLog.dm`). Original `mob/Logout` gets `usr` when the engine leaves it empty (window close).
- **QoL round 2** (2026-10-18, check: `tools/check_qol2.py`):
  - Explored-map memory (`Explore.dm`): tiles your units and view have seen are remembered (saved with the player). 3D draws seen-before tiles dim and never-seen tiles dark; the minimap shows explored land only; the top bar's **Map** opens a world map fitted to what you've explored (layers, click to move the camera).
  - Village > **Log** (`VillageLog.dm`): births, deaths, fights, finished board orders, blocked orders and "couldn't reach" in one list with filters; click an entry to go there.
  - Hover warnings (`HoverCheck.dm`): with units selected, hovering a target says the order and who can't do it (other level, needs an axe/pickaxe, can't reach). 3D: on the hover tag; 2D: a bar under the top bar.
  - Recipe costs: `tools/gen_station_costs.py` reads what each workshop recipe uses and trains from the station code into `StationCosts.dm`; the board's workshop list shows them.
  - Auto-equip: chop/mine (orders and jobs) use the best carried tool the unit has the level for, else fetch the best one from the stockpile or a zone.
  - Stockpile zones (`Zones.dm`, Work tab): up to 8 extra stores (Food store, Ore yard, Armoury, Wood pile, Stone yard, Seed store, Anything). Idle board workers carry matching items there from the main stockpile; counts, eating, cooking, seeds and tools use every store; nothing expires on a store.
  - 3D: units bob while walking, new things grow in, top-bar **N** (face north) and **Top** (straight down) buttons in 3D.
  - Polish: world save also watches areas around every creature and any replaced tile; lineage view cached; captured units show their own house (marked "another lord").
  - **Not done:** game speed / pause. The engine runs game time at real time whatever the tick rate, so this needs a patched engine copy for Remastered (Classic shares the current one).
- **Bag system** (2026-10-18, `Code/Remastered/Bag.dm`, check: `tools/check_bag.py`): a bag bar on the hero frame shows the selected unit's items. Click = the item's original choices, double-click = use now (eat, drink, equip/unequip), drag onto another unit (Company list, hero frame, roster, the unit in 3D) = the carrier walks over and hands it across; potions and food are used on arrival. Friends within 3 tiles share their bags for needed potions. Per-unit "uses by itself" rules: Restoration when a limb is lost, Internal Restoration when badly hurt inside, Vampirism Cure after a bite. Drag is a pointer drag (the browser's drag-and-drop doesn't start in the overlay). Probe actions 10 (double-click) and 11 (scroll) are test-only.
- **QoL round 3** (2026-10-18, check: `tools/check_qol3.py`, plus `check_bag.py`):
  - Real names per race (`Names.dm`), keeping the original "{Owner} " prefix and King/Queen title; rename from the unit panel (25 characters).
  - Bag bar stacks identical items ("×5"); drag gives the stack, Shift-drag one. Unload, Take (food/wood/stone/potions from the nearest store) and Best armour buttons, for one unit or a group.
  - Item tooltips (damage, defence, tool tier and level needed, food, weight).
  - Minimap and world-map pings for the last minute's fights, deaths, births and problems.
  - Group view: formation Keep / Line / Column / Box (faces the direction of travel), stance for everyone, Patrol → Set route (click points, Finish; loops as Move orders, `Patrol.dm`).
  - Daily report each morning (`DailySummary.dm`): resources gained, born, died, attacks, stuck. A "day" is one night-to-morning change (the game's Date is a random year, not a day count).
  - Undo (Ctrl+Z skin macro or top bar): the last plan or order (`Comfort.dm`). Save button with "saved ... ago"; world save keeps three backups (.bak, .bak2, .bak3).
  - Settings (⚙): HUD size and colour-blind friendly colours, kept per computer. Guide tab has a "New in Remastered" section.
- **3D models, first pass** (2026-10-18): the 3D world is drawn with low-poly, flat-shaded, painted-colour models built in `remastered.html` (`MD` library), RuneScape-style, instead of stretched 32 px sprites. Leafy trees, pines (snow-capped on snow), cactus, bamboo, dead trees; mountains as one faceted mass with shared corner heights; painted ground blended at tile corners with soft patches, grass tufts and pebbles; water and lava; wooden plank walls with posts, stone block walls, plank and flagstone floors. Every model is seeded by its tile, so it looks the same each time. ⚙ → "3D: original flat sprites" switches back. Still sprites: units, items, workshops; roofs are the old flat steps. The preview test scene is `scratchpad/hudview/scene.js` (not shipped).
- **3D unit models** (2026-10-18): `art/pipeline/export_units.py` (run inside Blender) builds Orc, Human, Dwarf, Elf, Goblin, Kobold, Lizardman, Frogman, Skeleton, Zombie and Vampire from primitives (the orc from `blender_models.py`, the rest from one parametric humanoid), poses the rig for idle, walk, work (axe swing) and attack, and bakes every frame to low-poly coloured triangles in `game/Interface/models/<race>.json` (490-820 triangles, 22 frames, 250-430 KB). The server sends a race's file the first time it appears (`browse_rsc` "model-<race>.json") plus each unit's action; the 3D view blends frames and turns units to face where they go. Other creatures stay sprites. Rebuild: `/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python standalone/remastered/art/pipeline/export_units.py`.
- **Equipment on unit models** (2026-10-18): the Blender export also writes, per frame, the hand, forearm and head joints, a body-part tag per triangle, and nine gear pieces in joint space (axe, sword, spear, mace, dagger, pickaxe, bow, buckler, horned helm). The server sends each modelled unit's equipped items (`Remaster3DGear`: weapon kind + tier, shield, helmet, chest, legs, gauntlets; tier from the item's name: wood, bone, leather, iron, silver, gold, adamantium, diamond, chitin, hell). The 3D view attaches held and worn pieces to their joints and recolours chest, legs and arms with the armour's tier colour.
- **Polish round 1** (2026-10-17): three code reviews plus a 200-unit stress test; all verified findings fixed. Details, open items and the play-test checklist: `remastered/planning/POLISH.md`. Scale plan: `remastered/planning/SCALING.md`.
- **Known test limits:**
  - The packaged app check (`tools/check_app.py`) can't connect while the Mac's screen is locked.
  - Real-window HUD clicks are swallowed while another app is in front. Map clicks still work.
  - When either happens, rerun later or use the arena checks and the preview browser.
- **Plans:**
  - `remastered/planning/VILLAGE_LIFE.md`: bulletin board, helping each other, kingdoms.
  - `remastered/planning/GAME_GAPS.md`: what's still missing.
  - `remastered/planning/FAMILY_HOUSES.md`: heirs and succession.

## Next: visual polish (keep the layout, make it look better)

1. Dark fantasy colour theme for panels, tabs, buttons and chat; better fonts.
2. Continue polishing command icons and contextual build/magic palettes.
3. Map: smoother unit movement, crisper zoom, nicer health bars and selection marker.
4. Tidier layout for the Unit Stats and Inventory tabs.

Ideas for later: Warcraft-style bottom console (minimap, portrait, command
card), more explicit world-object choices, and additional worker-role controls.

## Sharing

`remastered/dist/Dungeon-Master-Remastered-mac.zip` (no saves; includes "How to
open.txt" for the one-time macOS security step, the action list and GPL source).


## October17 overnight working build

The current personal app is `remastered/Dungeon Master Remastered.app`. The cumulative twelfth build passed private Frogman startup/save/reload at 05:23 Eastern, with unchanged normal save and visually reviewed native panels. Its complete app/source restore point is `remastered/restore-points/overnight-twelfth-integrated-app-20261017-052529/`; earlier accepted builds remain available. It includes carried Food/Equipment menu validation, finite loose-equipment pickup, correct Pause/Resume status, committed Forge/Poison/Gem/Potion/Bone/Leather menus, expanded spell/dragon/Vampire/Werewolf defense notifications, and the reviewed shared-engine inventory insertion order. Final cumulative source passes9,550 across56 gameplay suites; browser/native evidence remains separately scoped. A complete app/source restore point is preserved. The sixth and frozen-final long worlds and final current-build race matrix remain incomplete; whole-world persistence and physical mobile input remain open. See `remastered/planning/MORNING_2026-10-17.md` (in-progress handoff) and `remastered/planning/OVERNIGHT_2026-10-17.md` for exact coverage and restore points. The shareable ZIP above remains the unchanged archived release.

## Axe facing (2026-10-18)
- `build_axe` turns the head 30° about the haft (inner `axe_head_*` pivot) so the blade sits outward and forward instead of flat to the side; shared by the 2D sprite render and the 3D export.
- New honed-edge strip (`AXE_EDGE`, material `<tier>_edge`, one ramp band brighter). The 3D export tags it as gear material 4; the client draws it as the tier colour lightened 45%.
- Sprites, DMIs, 3D models, orc poll image and app rebuilt.

## Camera controls (2026-10-18)
- 2D: right-drag moves the map. OpenDream sends the game no live drag events, so the Mac bridge (`mac-webview/WebKitBridge.swift`, `installPanDrag`) watches right-drags over the map (not HUD panels) and passes window-point deltas to the HUD page (`remasterPanPx`), which sends `panpx`; `Player/RemasterPanPixels` (QoL.dm) turns them into tiles of `client.view`. A plain right-click is unchanged; the engine's end-of-pan right click/drop is ignored for 1 s (`client.remaster_pan_time`).
- 3D: middle-drag (or Alt+left, Q/E) turns, right-drag pans (ground follows the mouse), plain right-click opens the menu. Arrow keys still work.
- Probe kind 12: real AppKit right (button 1) / middle (button 2) drag. Checked in the real window: 2D pan direction and size match the drag; no menu after a pan.

## Race sprites (2026-10-18)
- `art/pipeline/race_models.py`: the parametric humanoid and the 10 race definitions, shared by `export_units.py` (3D) and `render_sprites.py` (2D). Shoulders now sit on the torso (arms were floating), limbs 1.35x thicker, nose/brows/mouth, limb parts and stumps for limb-loss states. Elf is a Night Elf (dark blue, silver hair, red eyes) and the kobold olive, like the original sheets.
- `render_sprites.py` copies each race's original state list (names, dirs, frames, delays, order) straight from `game/Icons/*.dmi`: walk, limb loss, legless (sits on its stumps), Sleep (on its back, eyes shut; vampire in a coffin), Kobold "Sneak" (crouched), Lizardman "Tail" overlay (body as holdout). Dwarves get their own `Dwarves.dmi` (the original dwarf uses `Human.dmi`).
- Output: `art/out/dmi32` and `dmi64` (Orc + 10 races), comparison `art/out/races.png` (`make_race_sheet.py`). Not wired into the game yet: 32 px is a drop-in replacement; 64 px needs the engine supersampling change (planning/ART_DIRECTION.md section 6).

## 3D camera and distance (2026-10-18)
- Tilt: middle-drag now goes down to 0.06 rad (almost level). Low views aim at chest height, the eye stays 0.7 above the ground under it (`v3heights`/`v3groundAt`), and the fog moves out to ~250 tiles toward the horizon.
- Mountains: rock height counts depth up to 30 tiles (1.2 + 0.8 per tile, ~24 units), near and far alike.
- Far view: `Player/Remaster3DFar` (View3D.dm) sends the explored world-map chunks within 160 tiles of the camera (surface only) when the camera enters another 16x16 chunk or every ~10 s while exploring. `v3buildFar` draws them as 4x4-tile cells: rock rising with depth (snow above 11), water, lava, forest pines; cells under the detailed area sink beneath it. Unexplored land stays out.
- Hero chase: Hero mode + Follow gives a low camera behind the hero that turns to their facing (`v3chase`); turning it by hand holds for 4 s, right-drag panning turns Follow off.

## Camera lock and mountains out of sight (2026-10-18)
- Lock camera on any one unit: unit panel "Lock camera", or F9 (game macro `Remaster-Lock-Camera`, and the HUD page handles F9 when it has the keyboard). `Player/remaster_lock` holds the unit's UI ref; `RemasterPlayModeTick` keeps the camera on it in 2D, and in 3D `v3chase` rides behind it. A bar under the top bar (and attack alert) names the unit with Unlock; right-drag panning, F9 or Unlock frees it; it frees itself if the unit dies. L stays World Chat.
- 3D: surface rock keeps its colour when out of sight (only ground, units and items stay dark), so whole ranges show instead of a black silhouette. Far view: unknown cells walled in by rock count as rock, since a range's middle is never explored. Checked in the real window (2D lock, bar, follow) and in the preview (rock out of sight).

## XP log, chase button, 3D keys, horizon (2026-10-18)
- XP pop-ups over the map are off by default (Settings: "Show XP pop-ups"). XP is summed per unit and skill and written to Village > Log once a minute ("Gorukgura: +245 Axe XP"); level-ups go to the log at once and still show a notice. New "Skills" log filter; the log keeps 150 lines.
- Chase button in the 3D top bar (and F9): locks on the one selected unit, else the hero/leader; again frees it (`chasecam`).
- Q/E/N: in 3D the game's own keys now turn the camera / face north (`Remaster-3D-Key` -> `key3d`); on the 2D map they stay WayPoint / Every / Rename.
- 3D clicks use real heights (mountains from the height map, trees ~3), so clicking a cliff face or tall tree orders mine/chop for every selected unit.
- Mountains: one height curve `MH(d)` = 1.2 + 1.3 x sqrt(depth - 1), max ~8 (was up to 24).
- Horizon: plain ground (the loaded land's average colour, dimmer) out to ~560 units in a 40-unit grid (`v3horizon`); fog start/end kept in order (zoomed far out, start passed end and turned everything haze-blue).
- Horizon ground is painted like the near ground (2026-10-19): corner noise patches and warm tint (`MD.groundCorner`'s), grass tufts and pebbles out to ~44 tiles, 2-unit cells to 64, 20-unit cells to 560; base colour is the most common loaded ground (not the mean). Explored far land gets the same patchiness. Rebuilt after 30 units of camera travel, ~20-30 ms.
- Far view shows the real land (2026-10-19): `Remaster3DFar` sends every chunk within 160 tiles (cells cached for everyone in `remaster_far_cells`, 5 min) with the player's explored mask; unexplored cells are drawn 30% hazier. World-map colours map to the 3D ground palette (`FARC`). Forests: six trees per 4x4 cell, pines and round leafy crowns, none within 26 tiles of the camera target (the detailed area covers that). The page asks for a larger detailed area when the camera tilts low (`v3sizeCheck`).
- Far-off figures (2026-10-19): `Remaster3DFarUnits` sends your units beyond the detailed area (out to 160 tiles) every tick, plus what they can see within 7 tiles (refreshed every 2 s, max 150): kinds m/p/a/n. The page draws a small body and head on the ground height there, and a gold marker over your own that keeps its size on screen. Nothing no unit of yours can see is sent. Checked in the preview; live run showed no errors but the units were out of frame.

## Raids and difficulty (2026-10-19)
- The original season timer (`World.dm`: `SeasonChange` every 10000 ticks, ~17 min) calls `Army()`, which lands 25-66 NPCs at a random spot on the 1000x1000 map, so it almost never meets anyone. `Seasons()` now asks `RemasterSeasonChanged()` (Raids.dm) first.
- Settlement raids: each season change (not the one at boot) sends one raid per player settlement (stockpile, or the middle of its surface units), mustered 35-45 tiles out with a warning naming the direction (notice, chat line, village log with location). Normal: 3 + 1.5 per living unit (max 25), none before the third morning. Brutal: 8 + 3 per unit (max 45), from day one, plus a second raid halfway through the season. Early days: kobolds, goblins, ratmen; later: undead, orcs, crusaders, goblins; a leader with 10+.
- Raiders march using the NPC "home" walking (HomeLoc/destination set to the target every 5 s unless they are fighting; stuck ones side-step); after 10 min survivors roam where they are.
- Difficulty (Settings > Difficulty) is a world setting saved with the world: Peaceful stops every army including the original random one. Settings shows the minutes to the next season and raiders on the march.
- Check: `tools/check_raids.py` (grace, peaceful, size, muster distance, warning, march arrival, brutal size, setting) passes; `check_world.py` passes.
- 3D speed fix (2026-10-19): the far view no longer rebuilds on every terrain update, only for new far data or when the detailed area has moved 8+ tiles; the server resends it when the camera moves 2 chunks (32 tiles) or every ~20 s while exploring, reads at most 60 new chunks per send (the rest follow every 2 s), and refreshes at most 12 stale chunks per send. The user's game logged constant "MainLoop: Cannot keep up!" zoomed out; a zoomed-out pan test now logs 4 (start-up).
- 3D look setting (2026-10-19): Settings > 3D look: "3D world, 2D sprites for units" (default, HD-2D style), "3D world and 3D unit models", "Original flat sprites". `V3.unitModels` gates the unit models separately from the world models.

## Skill bar, bigger dragons and spiders, bag drag fix (2026-10-19)
- Skill bar (`Abilities.dm`): one selected unit's special abilities as buttons under its bag. Found by opening the original Interact menu with preset answers in record mode ("This Creature", and "Magical Skills" for casters), cached 10 s per unit; everyday options (Run, Dig, Give, Suicide, Pull Out Arrow) are left out. A button runs Interact with the two answers; later questions are asked normally (`remaster_preset_then_ask`). `tools/check_abilities.py` passes (dragon: Dragon Breath, Rest; spider queen: Rest, Lay Egg; human: none; Rest really sleeps; refused when missing).
- 3D size: dragons 2.4x, spiders 1.0/1.3/1.6 by Young/Older/Mature (queens x1.2, warriors x1.1); every other race one tile.
- Bag drag: ends on release, cancel, blur, Escape, hidden page or a move with no button held, and sweeps every ghost and highlight (ghosts were left on screen when the release was missed).
- XP no longer goes to the village log; level-ups still do (and show a notice).
- 64 px race bodies for 3D sprites: code in place (`Remaster3DBody64`, `Icons/Remastered/Races64`) but off (`remaster_3d_use64 = 0`) while the art direction is decided (faithful redraws vs automatic enhancement; sample in `art/enhance/sample.png`).

## Alchemy: vapours, fire, brewing (2026-10-19)
- `Vapours.dm`: tile gases (smoke, poison, sleeping mist, rot, mana vapour, firedamp, steam, healing mist). Only tiles holding gas are processed (cap 4000); each second they archive, then share with open cardinal neighbours (archived difference x 0.2; a pair shares once per cycle); arriving gas brings its temperature, plus conduction; each gas decays at its own rate; empty, cool tiles drop out. Walls, rock and closed doors block gas. Effects on creatures standing in it: poison and rot hurt (not undead), sleeping mist sends to sleep, healing mist heals, mana vapour restores mana, thick smoke and hot air hurt.
- Fire: a tile with fuel (firedamp, wood on it, a tree, a wooden wall) catches at 150 degrees and goes out below 110 or without fuel; it eats firedamp for heat and smoke, lights wood and creatures with the original `atom/Fire()` (dragons, gargoyles, half-demons immune), radiates heat to neighbours with fuel, and logs "Fire at x, y!" to nearby players. Corpses give off rot.
- Look: one `obj/RemasterCloud` per tile in the main gas's colour and thickness, `obj/RemasterFlame` while burning; both are 3D effects (clouds tinted by gas).
- `Brewing.dm`: brews in an Empty Bottle (30 units). Ingredients give 5 units: fruit -> juice, glands -> venom, poison roots -> root sap, bones/skulls/shells -> bone dust, bloody limbs -> blood, meat, fungus, gems -> ruby/emerald/diamond dust; water from a lake or river (10). Recipes by ratio and minimum heat: Healing Draught (2 water + 1 juice, 60), Lifebloom (2 juice + 1 emerald, 60), Sleeping Draught (1 juice + 1 root sap), Venom Draught (2 venom + 1 water, 60), Alchemist's Fire (ruby + bone + water, 90), Mana Elixir (1 diamond + 2 water, 90), Smoke Powder (2 bone + 1 fungus), Strength Tonic (2 meat + 1 blood, 60). Batches = smallest amount / ratio. Heating at a campfire or fire within 2 tiles for 15 s. Drink (also double-click in the bag) or throw up to 7 tiles: the brew bursts into its gas (Alchemist's Fire bursts burning).
- HUD: Alchemy box on the hero frame (one unit selected): contents and temperature, Add per ingredient, Draw water, Heat, Drink, Throw (then click a tile; works in 3D), Empty.
- Checks: `tools/check_vapours.py`, `tools/check_brewing.py` pass; vapours, abilities, raids, bag, qol, world suites pass (the raid march check is timing-sensitive and can need a rerun).
- 3D look for alchemy (2026-10-19): vapours are see-through, unlit, drifting puffs in the gas's colour (thicker where there's more gas); fire is layered flickering cones (orange, amber, yellow) over an ember glow. Gas spreads at half tg's share per second; decay rates halved; thrown brews make clouds 3x bigger; a spark on fuel ignites at once. Fixed: the gas loop (and the raid loop) could start several copies before its first tick, which ran the gas ~50x too fast.

## Cauldron (2026-10-19)
- `Cauldron.dm`: `mob/WorkShops/RemasterCauldron`, built like other workshops (Build list / 3D ghost "Cauldron", 1 stone, one tile). Holds 150 units; its own fire: wood from a unit's bag burns 1 minute per piece, heating toward 160 degrees, cooling when out; reactions run every second. Units beside it: Add (or Add all of a kind), Pour water (water within 6 tiles), Add wood, Light/Douse, Fill bottles (each Empty Bottle takes up to 30 units of the mix), Empty. Its menu is the HUD Cauldron box (hero frame, one unit selected beside it).
- Advanced recipes (cauldron only, fifth recipe entry): Elixir of Life (2 healing + emerald + diamond, 140: full heal, blood restored), Dragonfire (2 Alchemist's Fire + ruby, 150: burns the drinker; thrown, a 3x3 firestorm), Stoneskin (tonic + 2 bone + water, 120: +armour skill for 3 min), Plague (poison + blood + fungus, 100: sickness; thrown, a rot cloud), Archmage's Draught (2 mana + diamond, 140: full mana). Recipes compete for shared ingredients.
- Look: 2D sprite `Icons/Remastered/Cauldron.dmi` (cold, lit; drawn by `art/pipeline/make_cauldron.py`); 3D model in the page: iron pot on three legs with a rim, brew surface in its colour, bubbles when hot, flames under it while lit.
- `tools/check_cauldron.py` passes; brewing and vapours still pass.
- Guide (2026-10-19): Guide tab > "Alchemy & the Cauldron" (collapsible): the five Cauldron steps, bottle brewing without a Cauldron, where every ingredient comes from in the original game (all obtainable: farming grapes/tomatoes; butchering for meat, bones, skulls, shells, glands; severed limbs for blood; poison spore plants for roots; Tower Caps for fungus; gems from digging; Empty Bottles from smelting sand at a Smelter or Glass Forge, or left by drinking a potion), the recipe table with heats and effects, and the fire warning.

## Rune circuits (2026-10-19)
- `Runes.dm`: one rune piece per tile, built like workshops ("Workshop:<id>", builder stands on the tile): Rune line (free), Mana crystal (1 gem), Rune door / Fire jet / Spike trap / Pressure plate / Rune lamp / Alarm bell (1 stone), Lever (1 wood). Pieces touching side by side form a circuit (flood fill, rebuilt when a piece is added or removed); its crystals hold the mana (100 each, +0.15/s, mana vapour on a crystal soaks in fast). Plates (enemies and animals, or anyone) and levers signal the circuit: every device acts if the circuit can pay (door 2, spikes 3 = 25 damage, fire jet 6 = burning firedamp, bell 1 = notice + log). Lamps glow (and give light) while the circuit has mana. Doors never close on someone.
- HUD Runes box (one unit beside pieces): circuit size and mana, Pull, Open/Close, Test, plate Enemies only/Anyone, Scratch out. 3D ghost: rune pieces stay in place mode (lay lines tile by tile) and skip the workshop spacing rule.
- Look: 2D `Icons/Remastered/Runes.dmi` (`art/pipeline/make_runes.py`); 3D: glowing violet linked lines (pulsing when powered, dull when not), floating spinning crystal, stone door with a sigil that sinks when open, spikes that shoot up, plate with glowing edge, flipping lever, glowing lamp orb, bell in a frame, fire vent. Guide: "Rune circuits: doors, traps and alarms".
- `tools/check_runes.py` passes.

## HUD overhaul; Classic retired (2026-10-19)
- Classic's panels and where they live now: Units -> Company list and Village roster; Unit Stats and Unit Information (attributes, every skill, elemental affinities, magic, every body part) and Your Information -> Character view; Inventory -> bag bar; Actions -> Controls. The commands only Classic's verb tabs reached are now in Controls: Create a clan, Check clan members, Check shrines, Place/remove tapestries, Join the current event (`Actions.dm` table, `RemasterCuratedVerb`). WayPoint, Go to coordinates, Get coordinates and World say were already there.
- Classic button (top bar) and "Classic info tabs" (footer) removed; the old "details" command now only keeps the info pane closed; the "classic border" toggle is hidden. The game starts in 3D (F8 still shows the 2D map). The chat log (Log) stays.
- Theme layer at the end of the page's styles: leather-and-iron panels with gold double trim and gilt corner studs, small-caps serif titles with a gold rule, embossed iron buttons (gold on hover, gilded when active), rounded glossy bars, a gilt portrait frame, Company cards that lift, parchment-edged notices, a bronze ring round the minimap; the Alchemy/Cauldron/Runes boxes match.
- Checked in a real window (starts in 3D, no Classic, new look); qol, qol2, qol3, bag, world, abilities, runes, cauldron suites pass.

## Race-themed HUD frames (2026-10-19)
- The overlay HUD's gradient/stud theme is replaced by pixel-art frames, buttons, bars and slots drawn at 1x and shown at 2x (pixelated).
- The material follows the selected unit's race (or the first unit's): stone (Dwarf, Gargoyle), timber (Orc, Goblin, Kobold, Ratman, Gremlin), bone (Skeleton, Zombie, Werewolf, ...), kingdom (Human, the default), moonsilver (Elf, Svartalfar, Illithid), swamp reed (Lizardman, Frogman, Plant), blood iron (Vampire, Demon), dragon scale (Dragon), chitin (Spider and its castes).
- Frames come from `art/pipeline/make_hud_frames.py`, which writes data-URI CSS between the RACE-FRAMES markers in `game/Interface/remastered.html` and the `RACE_MATS` table; `--sheet` writes `art/out/hud-frames.png`.

## CK3 / WoW HUD pass (2026-10-19)
- Tabs are an icon side bar down the right edge (Units, Village, Orders, Work, Map, Log, Guide, Settings) using the original HUD.dmi icons (`RemasterHudIcons` in HUD.dm sends them).
- Panels open full height beside the bar with a crest header (tab icon on a shield, title, subtitle, close); the minimap and Company list step aside while one is open.
- Village sub-tabs are icon buttons; roster rows and unit cards are plates with round portraits.
- Unit frame: round portrait with a level badge; minimap is round with the date plate above and layer tabs below; band orders (formation, stance, patrol, unload) sit behind More.
- Action bar uses icon slots; top bar is one row of counts with icons; routine "Started/Added/Arrived" notices are dropped, others show as chat-style text.

## Attack orders, combat chat, unit bars (2026-10-19)
- RTS attack (`Code/Remastered/Attack.dm`): clicking an enemy with units selected sends them at it (melee walks in and the original Bump/Combats code fights; bows use BowTarget). The Attack button on the action bar (or A) arms attack mode: click an enemy, or the ground to attack-move (march and fight any hostile within 6 tiles, then carry on). Wild animals are only attacked when clicked in attack mode. Any new order or Stop ends an attack; defense never hijacks one. Select-all moved from A to Ctrl+A. Arena check: `tools/check_attack.py`.
- Combat chat: the Mac client module relays every new line of the game's own output (blow by blow, body parts, limbs flying off, deaths) into the HUD's bottom-right chat (`mac-webview/RemasterChatRelay.cs` → `window.remasterChat`). Gore lines red, hits amber, level-ups gold.
- 3D unit bars: a short framed nameplate bar just above the head; layers are offset toward the camera so they no longer z-fight (flash). Company list bars fixed (the fill had no height).

## Trailer (2026-10-19)
- `remastered/marketing/trailer-party-to-kingdom.mp4` (58 s, 1080p): three orcs set out, make camp, raise a family, build a walled village, beat a goblin raid with attack-move, become a kingdom with a crowned King. Staged with the game's own code and recorded in the real game.
- Re-record: put `tools/trailer/ZZTrailer.dm` back in the .dme, compile, build the Swift tools (`winrec`, `cut`, `still`, `frame`), run `trailer_run.py` from `remastered/`, then `cut spec.json out.mp4`. `winrec` records only the game window (ScreenCaptureKit), never the rest of the screen; `DM_RECORDING=1` keeps the 3D view drawing while the window is covered.

## Tiers, trade, claims, markets, farming in 3D (2026-10-19)
- Ranks (`Progress.dm`): Camp → Hamlet (5 people, 2 workshops, 4 farmland) → Village (10, 5 workshops, 30 walls, Iron Age) → Town (20, 3 births, a raid beaten, Silver Age) → Kingdom (35, 120 walls, a crowned ruler, Gold Age). Unlocks: Hamlet lets other players ask to join, Village brings trade caravans, Town makes the ruler Lord/Lady, Kingdom makes them King/Queen. Metal ages Stone → Iron → Silver → Gold → Adamantium. Twelve milestones. Realm tab (♛) shows the ladder, the next rank's checklist, land, treasury and milestones; the top bar shows the rank. Check: `tools/check_progress.py`.
- Trade caravans (`Trade.dm`): from Village rank, every 2 days three merchants walk to the stockpile and stay 6 minutes; sell stockpile goods for coins, buy their wares (seeds, spade, ores, gems, bottles, cheese). Never attack-move targets. Check: `tools/check_trade.py`.
- Land claims (`Claims.dm`): Claim banner (1 wood) claims radius 8/12/16/22/30 by rank, one banner per rank; others can't dig, chop, paint or build inside. 3D draws borders and waving banners in the realm's colour. Check: `tools/check_claims.py`.
- Coins and markets (`Market.dm`): realm treasury; Market stall (1 wood, 3D model with awning); Merchant job tends it and sells what it carries at value × markup (50–300%); other realms' units beside it buy with their coins. Check: `tools/check_market.py`.
- Farming in 3D: farmland is furrowed soil; tomato bushes and grape vines grow through five stages and show fruit when ripe.

## Players as migrants; realms into kingdoms (2026-10-19)
- `Realms.dm`: a new player choosing a race is asked to found their own land or join an open realm (Hamlet rank or higher, online) as migrants; their units arrive about 18 tiles from that realm's stockpile and its ruler accepts or declines in the Realm tab. A settlement can swear fealty to a realm of its rank or higher. Members and vassals are allies: they may work inside each other's claims, attack orders never target them, and their people count toward the realm's rank. Anyone can leave a realm. Links are saved with the world (`Lieges`). Names shown are login names.
- Checks: `tools/check_realms.py` (arena, three realms) and `tools/check_multiplayer.py` (one server, two real clients: Alice founds, Bob joins through the prompt; uses the test-only `tests/mp_hook.dm`). The test probe answers the realm prompt with `DM_TEST_JOIN=1`.

## Host/Join launcher, join password, gear sprites, damage numbers, openings (2026-10-19)
- Launcher (`mac-app/Launcher.m`): opening the app asks Play / Host for friends (password, at least 4 characters) / Join a friend (address + password; the address is remembered). Passwords travel in `DM_JOIN_PASSWORD`, never on the command line. Started with options (package checks) it skips the chooser.
- Hosting writes `join-password`, `host-addresses` and `host-name` to the world folder (`launch.zsh`); `Joining.dm` asks everyone except the host for the password (two tries, then disconnect). The joining Mac's client fills the prompt from the launcher (`MacWebViewManager.AnswerJoinPassword`). The Realm tab and a top-bar badge show the host's address. Check: `tools/check_multiplayer.py --password` (Bob joins with the right password, Eve is refused).
- Gear in 3D: equipped weapons and armour were missing from 3D sprites (icon() overlays lose their picture in this engine). `Remaster3DLayers` now builds the sprite from the equipped items in RebuildOverlays order, and the cache keys on the gear.
- Damage numbers (`Hits.dm`): every melee strike's real damage (body health before/after Attack) floats over the target in 3D; gold for big hits, red when your unit is hurt, small grey "Miss" (throttled), skull for a kill.
- Openings: each strike in a row that does no damage adds +3 to the next (`Combats.dm`), so armour can't stall a fight forever. Measured with `tools/check_duel.py`: orc vs goblin raider went from 2+ minutes undecided to 15–45 s.
- Realm borders in 3D were not drawing (wrong coordinate fields); fixed with the damage-number fix.

## Names, allies, launcher, cave instances, rock and tree animations (2026-10-19)
- Each player takes their login name and their units' "{Player}" prefix follows it (`RemasterTakeName`, Joining.dm). Allied units have teal rings in 3D, caravan merchants gold.
- Launcher window (`mac-app/Launcher.m`, art `mac-app/launcher-art.png`): game art with the title, Play / Host for friends / Join a friend, Saves & logs, Quit.
- Cave instances (`Instances.dm`): 38 cave mouths at the foot of natural mountains (28 surface, 10 in the caves; same places every boot), each with a theme (goblin warren, kobold den, ratman burrow, undead crypt, orc stronghold) and danger. A unit walking onto a mouth (or Enter in its unit frame) takes up to 8 nearby units into a private cave carved fresh in sealed rock in a corner of the Depths (12 slots): foes, a boss from danger 2, treasure at the far end, stairs up at the start. Climb out at the stairs; empty caves are wiped after 30 s; one visit per mouth per day. 3D: mouth = ramp under a rock arch with a danger flag. Check: `tools/check_caves.py`.
- Animations: when a rock tile opens it bursts into tumbling chunks and dust; a felled tree tips over on its base, crashes and sheds leaves (`v3terrainFx` / `v3drawFx`, from terrain changes).

## Moods (2026-10-19)
- `Moods.dm`: every unit has a mood (0–100) drifting toward 50 + its thoughts. Needs while they last: starving −30, hungry −14, exhausted −16, tired −8, freezing −12, badly hurt −12, was attacked −6, no bed −6, own bed +6, bed in a proper (built) room +6. Memories that fade by game days: good meal +8 / ate raw −4 (EatItem hook), saw a death −16, lost family −28, heard of a death −5 (Death hook), the settlement ranked up +10, a raid beaten +10.
- Below 30 units work slower (skipped work ticks); below 12 they may snap for 90 s: sulk and refuse work, throw a tantrum and smash a carried item, or wander off; snapping gives +15. Unhappy units say so in the log; the Company list marks them.
- HUD: Mood bar in the unit frame (green/yellow/red; hover for the thoughts), average mood in the Realm tab. The unit frame's bars now refresh live (they used to stay at their first values).
- Check: `tools/check_moods.py`.

## Pause and game speed (2026-10-19)
- Remastered now ships its own engine build: the Classic engine fixes plus a game clock (`engine/clock/RemasterClock.cs`). `tools/build_runtime.py` runs a staged copy of the Classic build script with the clock patch, writing only `engine/server/OpenDreamRuntime.dll` (nothing in ../replica). `tools/build_app.py` puts it into the app's server.
- The clock: sleep/spawn delays and world.time follow a virtual tick. Paused, it stands still while player commands still run (orders can be planned); at 2× and 3× it advances that many ticks per engine tick. DM sets it through `world.game_state` (a hub-only setting this engine never uses): `Speed.dm`.
- Controls: ⏸ ▶ ▶▶ ▶▶▶ on the top bar, Space pauses/resumes (deselect-all moved to Shift+Space), a "Paused" banner. In a shared world only the host (or a lone player) changes the speed.
- Check: `tools/check_speed.py` (measured exactly 1.00×/2.00×/3.00×; paused time stands still; a command while paused resumes it). Arena tests still use the Classic server, where the setting does nothing.

## Biomes (2026-10-19)
- `Biomes.dm`: 22 regions laid over the original map at boot, the same every boot, before the world save is restored (so biome tiles never count as player changes). `RemasterBiomeAt(T)` answers for any tile.
  - Jungle (grassland near water): about a quarter of its grass becomes trees; wild ripe grapes and tomatoes.
  - Mesa (desert under mountains): red layered rock and orange sand; gold and silver nuggets; mining its rock turns up extra gold/silver (35%).
  - Tundra (snowfields): pale ground, scattered pines, wolves, iron; out there units get colder unless by a fire.
  - Ashlands (the Depths): ash fields, ember vents that flare (fire), adamantium lying about and in the rock (18% when mined).
  - Mushroom caves (the Caves): winding caverns carved in the solid rock, giant glowing mushrooms (chop for wood), fungus to eat, TowerCaps and cave spiders, mana drifting in the air.
- Resources regrow a little every morning. The 3D view colours biome ground and rock (mesa bands, ash, frost, violet cave rock) and draws jungle trees (tall, wide canopy, vines) and giant mushrooms in their own style; ember vents glow.
- Check: `tools/check_biomes.py`; real-game captures of all five.

## Rooms that matter (2026-10-19)
- `Rooms.dm`: an enclosed floor area (walls and doors around it, at most 160 tiles) is a room, typed by its furniture: one or two beds = bedroom, three or more = dormitory, a table and two chairs = dining hall, a throne = throne room. Grade Plain / Decent / Fine / Grand from built floors, a sensible size, decoration (pillars, statues, tapestries, lamps, fires) and gold furniture. Found again every 5 s near the settlement, so walls built or broken change them at once.
- Moods: sleeping in a bedroom +3/+6/+9/+12 by grade (dormitory +1..+6), eating in a dining hall +3..+10 (remembered for a day), "Our ruler holds court" +4 while there is a throne room and a crowned ruler.
- Rank: Town now needs a dining hall, Kingdom a throne room; new milestones for the first bedroom, dining hall and throne room. The Realm tab lists every room with its grade, size and place.
- Check: `tools/check_rooms.py` (and `check_progress.py` updated).

## Weapon classes (2026-10-19)
- `Hits.dm` (`RemasterStrike` replaces the plain Attack call in Combats.dm). Each weapon type has its own role:
  - Sword (duelist): can parry a blow before it lands (up to 30%, more with sword skill).
  - Axe (cleaver): 60% chance to cleave a second foe standing beside the wielder or the target.
  - Mace (crusher): ignores a quarter of the target's defence; 12% chance to stagger.
  - Dagger (quick): 35% double strike; hits make the target bleed.
  - Spear (reach): strikes from two tiles away (attack orders and defenders keep their distance).
- Openings: a staggered or bleeding foe takes +3 damage per opening.
- 3D: a swing effect per class at the strike, and floating words (Parry, Cleave, Crush, Bleed, Miss) next to the damage numbers. The unit frame shows the weapon role under the name.
- Check: `tools/check_weapons.py` (all five traits); duels between armed units end within about a minute; real-game capture of a staged raid with sword, axe and mace orcs.

## Throwing weapons and visible shots (2026-10-19)
- `Throwing.dm`: two new items, Javelin and Throwing Axe; any carried stone also works as a rock.
  - Javelin: range 6, heavy, pierces armour, uses spear skill.
  - Throwing axe: range 4, can take a limb off, uses axe skill.
  - Rock: range 5, light damage, 18% chance to stagger.
- Units carrying them throw on their own in attack orders and when defending, from 2+ tiles every 2.5 s, best item first, then close in to melee once they run out. A shield can block a throw. Thrown things land by the target and can be picked up again. The chat log says where each one hit ("hit in the left leg by ...'s javelin", "left arm is torn off by the throwing axe").
- Crafting: Carpentry > Javelins (1 wood makes 3), Forge > Throwing Axes (1 iron ingot makes 3). The unit frame's weapon line lists what a unit carries to throw.
- Bows: every arrow fired is now measured and sent to the 3D view like a melee hit.
- 3D: arrows, javelins, spinning axes and rocks fly from the shooter to the target along an arc. The damage number appears when it lands. Misses fall beside the target, and missed arrows and javelins stay stuck in the ground for a moment. New "Blocked" word.
- Check: `tools/check_throwing.py` (all four shot kinds, thrown items land, crafting, unit summary).

## War between realms (2026-10-20)
- `War.dm`. Realms are at peace by default. Attack orders and attack-move leave another realm's people alone ("You are at peace with ... Declare war in the Realm tab first"). Anyone attacked may still fight back.
- Only a realm's ruler decides on war and peace (in the Realm tab, under Other realms):
  - Declare war: both realms are told. Fighting starts after 60 s, or at once if the other realm's people attacked yours while at peace.
  - Offer peace: the other ruler accepts or refuses. Peace brings a 10 minute truce in which neither side can declare war.
- At war:
  - The two realms' people fight on sight.
  - Each side may dig and tear down inside the other's land.
  - Enemy units show red rings in 3D, and a red strip at the top shows the war and its score.
- Sieges:
  - Units within 2 tiles of an enemy banner, with no defender within 5, raise the siege (2% a second per unit, up to 5 units). Defenders bring it down.
  - At 100% the banner and its land change hands, with a quarter of the loser's coins as plunder.
  - A realm that loses its last banner sues for peace.
  - In 3D a besieged banner shows a red ring and a progress bar; the Realm tab lists sieges.
- Score: 1 per enemy killed, 5 per banner taken. Moods: going to war -3 or -5, taking land +5, losing land -6, peace +6.
- Wars and their clock are saved with the world ("Wars", "WarClock"). The war clock counts seconds itself, because `world.realtime` restarts near zero on this engine.
- Check: `tools/check_war.py`. `tests/realms_test.dm` now expects strangers at peace not to be attack targets.

## Two-player war test (2026-10-20)
- Real two-client test on one Mac (`tests/war_mp_hook.dm` sets the two settlements side by side; test-only). Alice hosted with a join password; Bob joined over the network address.
- Done by real clicks in the game windows:
  - Alice declared war (both saw the 60 s countdown).
  - Alice's people attack-moved on Bob's banner: Select all, A, then a map click.
  - The fight ended 3 kills to 2.
  - Alice took Bob's first banner by siege (25 coins plunder), then his second. Bob's realm fell and sued for peace: truce, final score 13 : 2.
  - After the truce, Bob declared war; Alice clicked Offer peace and Bob clicked Accept peace, giving a truce.
- No runtime errors.
- Fixed from the test:
  - Realm panel buttons missed clicks: the panel was rebuilt on every update, so a button could be replaced under the mouse. It now rebuilds only when it changes, and never while the mouse is held in it.
  - The "Hosting" label and "Hosting for friends" box showed for players who joined. They now show only for the host (`RemasterIsHost`).
  - Ctrl+A did nothing when the HUD had keyboard focus; it now selects all units.
- Noted: a realm with no people left is not listed under Other realms, so it can't be targeted by a declaration.

## Siege weapons; moods off (2026-10-20)
- Moods are switched off for now: `rm_moods_on = 0` in `Moods.dm`.
  - No mood ticks, no slower work, no snapping.
  - The HUD hides the Mood bar and the realm's mood.
  - Set it to 1 to bring moods back; `tests/moods_test.dm` turns it on to keep the system tested.
- `Siege.dm`: two siege engines, built at the Carpentry.
  - Battering Ram: 3 wood. It rolls up to a wall or door and pounds it every 2.5 s: 300 per blow, +100 for each extra crew member, up to +200.
  - Catapult: 4 wood and 1 stone. It throws a boulder every 6 s at 3 to 10 tiles. A boulder does 500 to a wall and wounds everyone within a tile of where it lands; 25% land a tile off.
- Crew: an engine moves and fires only with one of its owner's people within 2 tiles. Otherwise it reads "Needs crew".
- Orders:
  - Click an engine to select it (shift adds; box-select takes it too).
  - Click a wall or door, or use Attack and click one, to attack it.
  - Use Attack and click an enemy to shell them (catapult only).
  - Use Attack and click the ground to attack-move, smashing walls of realms at war on the way.
  - Click the ground to roll there.
- What can be hit: built walls have 1000 (wood) to 4500 (obsidian) HP, doors 10. A broken wall opens the way digging does (60% leave stone rubble), and the wall's realm is told. Walls inside another realm's land can only be attacked at war; your own and your allies' never.
- 3D:
  - The ram is a capped log slung under a roof on wheels and swings at each blow.
  - The catapult's arm flings forward when it fires, and the boulder arcs to the target.
  - Dust bursts on impact, "Wall 400"-style numbers appear, and damaged walls show a health bar.
- Engines are not people: they don't count toward population, eat or take jobs. Enemies can't attack them (like wagons).
- Check: `tools/check_siege.py`. Real-game capture: `marketing/siege-engines-frames.png`.

## Siege engines: saving, wrecking, burning (2026-10-20)
- Saved with the world: `S["siege"]` holds type, position, owner key, HP and whether it's burning. Engines are restored at boot and handed back to their owner at login (`RemasterClaimWorld`).
- Wrecking: an engine with no crew within 2 tiles can be hacked apart by anyone beside it who is at war with its owner, and by raiders.
  - 25 HP a second each, up to 4 wreckers. Each second there's a 15% chance they set it alight.
  - A crewed engine can't be wrecked; its crew are called to fight the wreckers.
  - Attack orders and attack-move target enemy engines at war, attack-move only uncrewed ones. Units wreck from beside the engine and never use spear reach, throws or cleave on it.
- Burning: fire from anywhere (fire brews, burning ground) sets an engine alight, costing 15 HP a second. One of the owner's people beside it beats the flames out in 3 seconds.
- Destroyed: at 0 HP it falls apart into 2 wood, the owner is told, and at war the wreckers' side scores 2.
- 3D: damaged engines show a health bar, burning ones flames, and wrecking shows "Wreck" numbers.
- Checks: `tools/check_siege.py` (wreck, guard, score, burn, douse) and `tools/check_siege_save.py` (saves, restarts the server, restores both engines with HP, burning and owner).

## Race specials, house names, families and captives, 3D assets, water (2026-10-20)
- **Race specials** (`Specials.dm`): one aimed skill per race, on a cooldown. Press F, or the ✦ button on the unit frame, then click to aim; right-click or Esc cancels. While aiming, the 3D view previews the shape.
  - Dragon: Fire breath, a cone that burns and sets alight. Ice dragons get Frost breath (slows) instead, poison dragons Poison breath.
  - Spider: Web shot (roots for 3 s, then slows; costs 10 silk).
  - Human: Shield charge. Dwarf: Ground slam. Elf: Piercing arrow (goes through the whole line). Orc: War leap. Goblin: Fire pot. Lizardman: Tail sweep (knockback).
  - Frogman: Tongue lash (pulls the target in). Kobold: Poison dart. Ratman: Plague cloud (poison gas). Svartalfar: Shadow step (blink, next blow +12). Devourer: Acid spit (−15 armour). Illithid: Mind blast (stun).
  - Specials only hurt units the caster may fight: never a realm at peace, never your own.
  - F was "Ignore" (an old chat command); R stays Restart.
- **Dragons fly twice as fast** (`RemasterStepDelay`). Slowing and rooting from the specials go through the same step delay.
- **Right-click menu** lists everything on the tile: units (Select / Attack / Capture), grouped items (Pick up / Use), workshops and bodies, and the tile itself.
- **House names:** the Realm tab has "Your house": name it, and units ("{Blackhide} Grak"), banners, the realm name and war notices all follow.
  - Names are unique and 2–24 letters. The login name still decides who the host is.
  - The Realm panel no longer redraws while you type in it.
- **Families:** the unit frame lists partners nearby ("Have a child with …"). The pair walk together and the original breeding runs; the frame then shows "Expecting".
- **Captives:**
  - Subdue an enemy you may fight (fainted, stunned, webbed or rooted, in a pit, or below 35% health). Then "Capture" from the frame or the right-click list.
  - Captives are held for a minute, then join your house. Animals are tamed at once. Rulers can't be captured; at war a capture scores 1.
- **Old Interact menu as buttons:** the skill bar now also lists the "Closest Creature" options (Breed With, Rescue, Feed From, Bite) for each creature beside the unit. The menu waits for the right creature ("sticky" preset answers in `StationCraft.dm`).
- **Felled trees disappear in 3D:** a chopped tile keeps its tree type but isn't dense, so it now draws as ground. Tree2/Tree3 draw as trees instead of rock.
- **3D models instead of flat sprites** (`Remaster3DObjModel` in View3D.dm, `v3obj` in the HUD), coloured by material:
  - Furniture: doors (open and closed), beds, bedrolls, tables, chairs, thrones, pillars, statues, fences, training posts, signs.
  - Every workshop, each half modelled: forge and smelter with chimney and glowing coals plus anvil, carpentry bench and sawhorse, kitchen, masonry, leatherworks, bone craft, gem cutter, potion and poison stations, melter, campfire with live flames, altar.
  - Chests, wagons, cages, traps (pit, spikes, rib trap).
  - Resources: logs, stone, ores, gems, ingots, bones.
  - Other items lie flat on the ground with a shadow.
- **Water:** a real basin (dark bed, earth banks) and a moving surface with glints. Lava gets a glowing surface. The underground "diorama" rock and the far-view land dip under water so they don't poke through.
- Checks:
  - New: `tools/check_specials.py` (all 14 races, cone front and back, peace, cooldown, aim, flight) and `tools/check_capture.py` (partners, child, Closest Creature skill, subdue, capture, peace, ruler, tame, joins the house).
  - `tools/check_realms.py` now also covers house names.
  - Real-game captures: `marketing/3d-assets-yard.png`, `marketing/race-special-fire-breath.png`.

## Fair start and rare races (2026-10-20)
- `Rarity.dm`. Common races (Human, Dwarf, Elf, Orc, Goblin, Lizardman, Frogman, Kobold, Ratman) start with every skill at level 1. The rare races keep their own gifts.
- Softened low levels:
  - Every craft roll (446 of them, originally `prob(skill*4)`) now goes through `RemasterCraftOdds`: 45% at level 1, 72% at 10, certain from 19. Higher levels keep the original rate.
  - Chopping and mining (58 lines) use `RemasterWorkSkill`: at least as strong as level 12.
  - Throwing-weapon crafting uses the same odds.
- Rare races: Dragon, Spider, Devourer, Svartalfar and Illithid show in the race list only when drawn.
  - Each is rolled separately every time you choose a race: 4% plus 3% for every achievement (milestone) you have ever reached, up to 49% with all 15.
  - Achievements are kept across games in `units/remaster_profile_<ckey>.sav`.
  - The draw holds while you choose (Cancel doesn't re-roll) and is used up once you pick. A line in chat says what was drawn, or the current odds.
- Check: `tools/check_rarity.py`. The two-client check (`check_multiplayer.py`) goes through the new race menu in real clients, and `check_skills.py` still passes.

## Gentler first raids (2026-10-20)
- `Raids.dm`, Normal difficulty only; Brutal is unchanged and Peaceful still has no raids.
- Size: a young settlement (Camp or Hamlet with fewer than 2 raids beaten) gets at most 1 + rank + half its people. A new camp of 3 now faces 3 raiders instead of 7.
- Strength: `RemasterRaidStrength` scales raiders' skills, armour and weapon damage down.
  - Formula: 35% + 15% per rank above Camp + 10% per raid beaten + the people's average best combat skill / 60, capped at 100%.
  - A band under 70% strength is announced as "a ragged band".
- Checks: `tools/check_rarity.py` (young versus grown raids), `tools/check_raids.py` updated for the new size.

## Fishing, RuneScape style (2026-10-20)
- `Fishing.dm`. Fishing spots sit on shore tiles. The kind comes from how much water lies within 6 tiles: shallow (ponds), river, deep (big lakes), plus swamp and cave pools.
  - 160 spots across the world at boot. Each settlement is kept at 3 or more within 30 tiles. Spots drift along the shore every 5–10 minutes.
- Tools and fish (level needed):
  - Shallow, net: Shrimp 1, Anchovy 15. Shallow, rod: Sardine 5, Herring 10.
  - River, rod: Trout 20, Pike 25, Salmon 30.
  - Deep, lobster cage: Lobster 40. Deep, harpoon: Tuna 35, Swordfish 50, Shark 76.
  - Swamp, net: Tropical fish 12, Blowfish 22.
  - Cave, rod: Cave fish 18, Cave eel 38.
  - Bare hands work in shallow water and swamps at half the odds.
- Catching: a try every 3 s, best fish first. Odds are 30% + 2% per level above the fish's requirement, between 15% and 85%. Experience is 0.15 + level/100 per catch.
  - Catches are fish (heavier for bigger fish, so more meat) dropped at the fisher's feet. They keep for 5 minutes.
- Tools: Fishing Rod, Fishing Net and Lobster Cage (2 wood) at the Carpentry; Harpoon (iron ingot) at the Forge.
- Use: select units and click a spot (or right-click → "Fish here"). Fisher workers go to spots on their own. The status line says which tool or level is missing.
- 3D: ripple rings and fish breaking the surface on spots, the cast line and splash, the catch leaping to the fisher, and "+Salmon" floats.
- The old bump fishing (73 places) now has at least a 4% chance, instead of 0.1% at level 1.
- Check: `tools/check_fishing.py`. Real-game capture: `marketing/fishing-spots.png`.

## RuneScape skills, rot fix, Guide (2026-10-20)
- Skills now level exactly like RuneScape (`Skills.dm`).
  - Each unit keeps real experience per skill, saved in `remaster_xp`. Existing units convert at their current level.
  - The game's own gains become a fixed XP per action (`rm_xp_per_point`): 4 XP a swing of the axe or pick, 15–30 a craft, 30 a cooked meal, about 4 a combat hit.
  - Fish give RuneScape's XP: Shrimp 10, Trout 50, Lobster 90, Shark 110.
  - The level comes from RuneScape's official table, written out because 32-bit floats drift: 83 XP for level 2, 101,333 for 50, 6,517,253 for 92, 13,034,431 for 99. Levels continue to 120 (RuneScape 3 elite), so content gated at 100 stays reachable.
  - The old "grind pace" scaling is gone; the RuneScape curve does that job. One-off boosts keep their level. The skills check is updated.
- The cloud in the fishing capture was rot: every body, including a fresh catch, gave off miasma from the start. Bodies now start to rot after 2 minutes and fish after 5 (uncollected fish are gone by then). Covered by `check_fishing.py`.
- Guide tab: new sections for race specials (table), war, sieges and peace, siege engines, families, captives and your house, fishing (table), and skills and levels (RuneScape table, fair start, rare races, gentler raids). The shortcuts line now has F for specials and Ctrl+A (A is Attack).

## Soak and performance test (2026-10-20)
- About 60 units, every workshop, 131 furniture, ponds, a rival realm at war, siege engines, raids. Real client, 3D on, about 15 minutes per run, three runs plus a reload repro. ErrorLog: no runtime errors.
- 3D: 58-60 fps at normal speed, 53 at fast, 46 at faster (p95 31-34 ms). JS takes 3-7 ms per frame. About 4 MB of furniture, workshop and water geometry is re-uploaded every frame.
- Server: normal speed holds 10 ticks/s. Fast and faster both reach only about 14 ticks/s (70% and 48%). The per-player 3D builder (`Remaster3DTick`: terrain about 40 ms, things about 11 ms per call) and the HUD are about 15-20% of it, and they run per game tick, so they double at speed 2. A save freezes the game for 1.6-2.4 s.
- Fixed:
  - Claim banners are now saved with the world (`Claims.dm`, `WorldSave.dm`). Before, every realm's claim was gone after a restart. `check_siege_save.py` covers it.
  - Dead raiders are now removed from `remaster_raiders` (`Raids.dm`). A typed loop never visited the null keys they left.
  - The 3D view fills its 600-thing cap with workshops, furniture, banners, siege engines and fishing spots before loose items, so loot no longer hides buildings (`View3D.dm`).
- Open at the time; resolved 2026-10-21 (`remastered/reports/save-fixes-2026-10-21/RESULTS.md`): the 27 units with no location were a test artifact (the harness replayed a scene after restart); the campfire and the lost ground items were real and fixed (items and workshops are now saved unless they came with the map); ground items growing during fights was not reproduced.
- As first written:
  - After one long war run, 27 of 46 units came back from a reload with no location. A short clean run reloaded exactly. Cause not found yet.
  - One workshop kind and about 40% of ground items don't survive a reload.
  - Ground items keep growing during fights.
  - Details, numbers and ranked fixes: the soak report in the session notes.

## Hero Deselect and Shift+Space help (2026-10-21)
- The hero frame's Deselect button sent `select|<hero>`, which just selected the hero again. It now sends the same `action|clear` (Zip) as the main Deselect button (`remastered.html`).
- Help said Space deselects; Space pauses. Fixed in the F3 guide, the Deselect tooltip, the Controls command list (`Actions.dm`) and the 3D placement hint ("Shift+Space to stop").
- In 3D, Shift+Space now also deselects while the HUD has the keyboard, like it does on the map.
- Tested in the packaged app (private profile, Humans): Hero → Select → Deselect, Space pause/resume, Shift+Space from the HUD and the map. Report: `remastered/reports/deselect-fix-2026-10-21/RESULTS.md`.
- Test note: the probe's AppKit key route (kind 4) never sends a Shift key-down, so Shift combos need the SDL key route (kind 1, modifiers=1).

## Save fixes (2026-10-21)
- The "27 units with no location" after the soak reload was the soak harness, not the game: it replayed its kingdom scene after the restart and spawned 26 orcs and a builder at a null site.
- Fixed (`WorldSave.dm`): things that override `New()` without `..()` were never marked "made during play" and were dropped from the world save. That covered wood, ores and stone, food, seeds, gems, ingots, glands, bodies and the campfire (the missing workshop kind). Now everything present when the world loads counts as map content, and anything else on the ground is saved. The first-visit item marking is gone.
- Fixed (`Runes.dm`): rune pieces (line, crystal, door, jet, spikes, plate, lever, lamp, bell) are saved with their settings. Before, they vanished on every restart.
- Fixed: empty `UnitList` slots left by deleted units are dropped before saving.
- Fights don't pile up ground items. An arena raid left only severed limbs and bodies; the soak's growth came from its workers.
- New check: `tools/check_unit_save.py` (three boots: build, save, log in, save, log in; nothing lost or doubled). Fails on the old code, passes now.
- Stockpiles no longer rot (`Zones.dm` overrides the original `ItemDecay()`): goods on or beside a main stockpile or zone are kept; loose goods still rot after about 32 minutes. Check: `tools/check_stockpile_rot.py`.
- Open, design: severed limbs never rot.
- Report: `remastered/reports/save-fixes-2026-10-21/RESULTS.md`.

## TikTok cut (2026-10-21)
- `remastered/marketing/tiktok-2d-to-3d.mp4`: 20 s, 1080x1920, silent (add a sound in TikTok). Hook: the classic 2D map ("this game died years ago"), then a cut at the switch to the 3D town ("so I rebuilt it"); then raid, catapult hitting a wall, fire dragon, fishing/farm/family, and a pull-back from the King to the walled town ("free on Mac · link in bio").
- Recorded in the real game (packaged engine and client, portrait 640x1138 window) from a temporary game copy with `tools/trailer/ZZTrailer.dm` plus `tools/trailer/tiktok/ZZTikTok.dm` (2D/3D flip, framed siege and dragon, king pull-back). The recording copy hides notices, chat and the war bar in cinematic shots and lets a shot set the camera's facing. Game source is unchanged.
- Re-make: build `winrec`/`frame` from `tools/trailer/*.swift` and `tiktok_cut.swift` into the runner's folder, run `tiktok_run.py`, `captions.py caps`, then `tiktok_cut spec.json out.mp4` (`spec.json` paths are relative to that folder).

## Shareable download (2026-10-21)
- `remastered/dist/Dungeon-Master-Remastered-mac.zip` (76 MB) rebuilt from the current source: compiled game `1c939ff1…`, the same as the main app; game, HUD, engine and client files identical to it. No saves, no personal data (checked after unzipping).
- `build_app.py --shareable` now puts Remastered's own engine and Mac client sources (`RemasterClock.cs`, `RemasterChatRelay.cs`, `RemasterDragBox.cs`, newer `MacWebViewManager.cs`, `NativeUiProbe.cs`, `WebKitBridge.swift`) in `Source/engine-changes`; before, it shipped the Classic copies.
- The unzipped app passed `check_app.py` (new army, save, restart, reload: 3 living units, no errors). Report: `remastered/tests/share-20261021-checks.json`. Previous share build: `remastered/restore-points/before-share-20261021/`.

## 3D hellgates (2026-10-21)
- The original hellgates (two permanent ones on the surface at 666,666 and 472,600, one in Hell at 666,666 back up, plus any an admin opens) were drawn in 3D as a flat ground decal. Now (`View3D.dm` sends `hellgate` = down/up; `v3hellgates` in `remastered.html`): a ring of black obsidian spikes on scorched ground around a floating fire rift that always faces the camera (near-black rim, crimson, orange, white-hot core; jagged rings turning), embers rising, an additive halo and ground glow. The fire draws unlit at full brightness, so it blazes at night. The gate in Hell burns pale gold. About 1.5 tiles across, so it reads from the default camera.
- Real-game test (packaged engine and client, full map, temporary copy with `tools/trailer/hellgate/ZZGate.dm`): day, night, cinematic and normal HUD views. A unit ordered onto the surface gate arrives in Hell at 666,665,4; in one run it came through blind (the original 15% roll). No game errors. Clip: `remastered/marketing/hellgate-3d.mp4`.
- The ground around the surface gate is the original map's hell floor and hell cliffs (red in 3D).

## Click audit, regression run, combat skills (2026-10-21)
- Click audit (`tools/click_audit/`): real AppKit clicks and keys in the real 3D client for about 30 interactions. Fixed: box select with a turned camera (now screen-space, `boxrefs`), unit picking on raised ground (picked at ground height), 6 px click tolerance. Open: an intermittent extra F8 press; shift+click is not testable with the probe.
- `tools/run_server_checks.py`: all 74 self-contained checks. No game regressions; outdated tests: duel, gear_dump, easy_orders_hud, portraits.
- RuneScape combat skills (`CombatSkills.dm`): Attack, Strength, Defence, Ranged, Magic over the weapon sub-skills (new Throwing under Ranged). Combat style per unit (Accurate, Aggressive, Defensive, Controlled) picks which skill melee trains; 4 XP per damage. Injuries: one lost leg halves dodging, both or blind and no dodging; parry needs an arm and sight. HUD: style picker and sub-skill rows in the skills panel. Check: `tools/check_combat_skills.py`.
- Original quirk, left as is: a melee miss or shield block doesn't stop the blow; only a dodge does.
- Report: `remastered/reports/qol-2026-10-21/RESULTS.md`.

## Always 3D, always Village (2026-10-21)
- At the user's request the 2D/3D toggle and Hero mode are gone: F8 is unbound, the top-bar 3D button and Hero/Village switch are hidden, `view3d` and `Toggle-3D-View` can only turn 3D on, `playmode` only accepts village, `makehero` does nothing, and saves from Hero mode load as Village.
- Verified in the packaged app (start, save, reload; HUD snapshot shows no 3D or Hero/Village buttons).

## Orders always go through (2026-10-21)
- Every way a unit could ignore or refuse an order was mapped and tested (`remastered/tools/check_obey.py`, 32 situations): the old code failed 22, now 32/32. Sleeping units can be selected and wake when ordered; flyers land; blind units go; legless units crawl; with no axe or pickaxe units fetch one or work by hand (about a quarter of the speed); a full pack unloads at the stockpile or puts resources down to make room; a group on one tree all chop it; any loose item can be picked up (placed beds, furniture, signs and traps are walked to instead); walls, water and occupied tiles mean "go beside it"; stairs are taken, also for work on another level; blocked routes keep retrying instead of waiting for Resume and unreachable goals end "as close as it could"; a direct order ends a patrol; a move given while fighting is a retreat that auto-defense won't turn back; the enemy you clicked is chased until it's reachable; 3D clicks reach as far as the view.
- Still refused on purpose: claims, peace treaties, dead units, eggs, pits, knock-outs and stuns (carry on after), silver for vampires/werewolves, items too heavy to lift, fishing gear and levels.
- `Player/RemasterMapOrder` (QoL.dm) is the one click → order decision for map and 3D clicks. Real-input check: `CK_SET=obey tools/click_audit/click_audit.py`.
- Checks: 22/22 order-related server checks and the order integration suite pass, except the seven jobs already failing on October 20 and a random-roll cooking test. Tests that asserted the old refusals were updated to the new rules. The app is rebuilt and passes `check_app.py`.
- Report: `remastered/reports/obey-2026-10-21/RESULTS.md`. Restore point: `remastered/restore-points/before-obey-20261021/`.

## Mining layers, felling, ore lumps, bamboo (2026-10-21)
- Rock is mined layer by layer inside the natural faceted mountains. Cracks spread over the band being dug, then the bottom layer bursts out (a recess with the rock still above), then the next layer, opening a two-high tunnel whose roof stays and is saved (`remaster_roof`).
- Layers are 3 at a mountain's edge and 7–8 inside (2 underground), fixed by distance to open ground, so heights hold as you dig. Mining a tile still takes the same HP. Mining roofs away isn't in yet.
- The user tried and rejected stacked Minecraft cubes in favour of the faceted look.
- Metal veins (iron, silver, gold, adamantium) are fixed by place and biome (about 7% of surface rock, 12% underground) and show as lumps of metal sticking out of the rock. A vein tile always gives its metal.
- Trees shake and drop leaves at each blow, fall away from the feller, bounce and break into logs. Bamboo canes topple one by one and split. Felled bamboo gives `Bamboo` wood (a kind of wood).
- Code: `Code/Remastered/Breaking.dm`, the `Bump` hook in `Orders.dm`, `work`, `vein`, `blocks` and `roof` in the 3D terrain data (`View3D.dm`), and `v3cutRock`, `v3veinMarks`, `v3work`, `v3drawWork` and `v3breakFx` in `remastered.html`.
- Checks: `tools/check_breaking.py`; real client `tools/trailer/breaking/break_run.py`. Report: `remastered/reports/breaking-2026-10-21/RESULTS.md`.

## Mountains: one block an order, roofs, steps, ramps (2026-10-21)
- Mining natural rock is now one block per order. The first order takes the bottom block and leaves a notch; the tile stays solid, because units are two blocks tall. The second order takes the block above, opening a two-high tunnel. Each "Mine the block above" order (3D right-click on a dug tile, or a left click on the rock over it) takes the next block up, until the tile is open to the sky. Shift queues more. State is kept in `remaster_dug`, `remaster_roof` and `remaster_ceil`, all saved.
- Up a mountain (the peaks on the sky layer): right-click rock at a mountain's edge, then "Carve steps up from here" (straight in, up to two layers a tile) or "Carve a ramp up from here" (along the face, a layer a tile). Each tile of the run is dug like rock, the peak over the cut opens, and the head becomes the original stair pair onto the peak, so move orders onto a mountain top climb it. A click on a mountain's top in 3D means its peak, and units up there stand on the rock.
- Cave-ins (original rule: 5% per dig, open tunnel floor within 3 tiles refills at 50%, any pillar within 4 tiles holds it) also apply to roof mining. Mine hovers warn when no pillar is near, and 3D shows rock crashing down with dust. The Build-menu session added a "Support beam" (`/obj/Items/Furniture/Pillars/WoodenBeam`, 1 wood, planned every 9 tiles along a tunnel; a unit carrying one sets it down in unbraced tunnel); 3D draws it as a post and crossbeam.
- A 1-wide cut can be blocked by creatures the original mining spawns (beetles, moles, tower caps).
- Code: `Code/Remastered/Mountains.dm`, `Breaking.dm`, hooks in `Orders.dm`, `View3D.dm`, `HUD.dm`, `WallWalks.dm` and `HoverCheck.dm`; in `remastered.html`, `v3carveRock`, `v3peakTop` and the cut, notch, menu and picker code. Checks: `tools/check_breaking.py` (19 checks); real client `tools/trailer/breaking/mount_run.py`.

## Climbing gear and the tree redesign (2026-10-21)
- Climbing gear (`/obj/Items/RemasterTools/ClimbingGear`, made at a forge from 1 iron ingot) lets a unit carrying it climb a cliff face onto a mountain top, and back down, where no carved steps lead. It needs no equipping. Kobolds, Vampires and spiders (`CliffClimber`) climb without it in half the time; flyers just fly up. Time is 2 s plus 1 s per rock layer. A move order onto a peak picks the nearest foot of the face; without gear the order is refused with a hint about the forge. Code: `RemasterCanClimb`, `RemasterClimbTime`, `RemasterClimbSpot`, `RemasterScaleOrder` in `Mountains.dm`, and the "Scale" order in `Orders.dm`.
- 3D: a climber is drawn against the face, rising with the climb, then steps over the lip. Units on a peak stand on the rock as drawn (`v3peakTop` reads the drawn corners), so they are no longer sunk into it.
- Trees are modelled at full height (a unit is about 1 high): oaks about 4.5 with a big round crown and the sprite's red-brown flecks (apples on a good tree); pines about 6 in drooping tiers (snow on cold ground); birches with a pale banded trunk; dead trees; bare winter trees like the original snow-tree sprite; and jungle giants with buttress roots and vines. Size, turn and lean vary per tile. Bamboo, cactus and giant mushrooms keep the old stretched model, so `v3cane` still matches. About 300 triangles a tree.
- Trees thin out to a dither over your units (selected ones first, up to 8) and right in front of the camera, so nothing hides under a canopy. Tree vertices carry colour alpha 0.97 as the marker; the shader takes `fp[8]` (screen position, radius, depth) and `fnear`. Clicks on a crown pick its tile (`MD.treeTop`), felled trees land their crowns further out and break into more logs, and the far view's trees match the new heights.
- Code: `MD.tallTree`, `MD.treeKind`, `MD.bigTree`, `MD.limb`, `MD.skirt`, `MD.clump`, `MD.gem` in `remastered.html`. Real-client checks: `tools/trailer/breaking/mount_run.py` (`MT_ONLY=gear`) and `trees_run.py`.
- No more "camera shadow": 3D used to black out every tile the camera's own spot couldn't see past trees, and hid any unit there, so dark patches moved with the camera and swallowed your units. On the surface and the sky layer everything in the 3D area now counts as in sight (caves keep line of sight through rock), and your own units always show.
- Sun and sky: a 2048 shadow map from the sun (packed depth, so any WebGL1 works) gives cast shadows from trees, rock and buildings, soft-edged; shade keeps a quarter of the sunlight. The sun follows the day (`dayp`, how far through the day or night, from `RemasterDayProgress` in View3D.dm; `Night()` switches every 5500 ticks): it rises in the east, stands about 58 degrees up in the south at noon and sets in the west, so shadows sweep round. Sky light fills in while it's low. The sky is a gradient to blue with the sun's disc and glow (warmer when low) and slow clouds; at night it's dark with the moon and stars, and there are no sun shadows. Units (billboards) aren't shaded, so they stay clear in shade. Code: `v3sunDir`, `v3drawShadow`, `V3.sh`, `V3.skyp`, `sunlit()` in the fragment shader.

## Unit panel tidy, bag hover, no "Move" tag (2026-10-22)
- Hovering an item in the bag (the panel's bag bar or the inventory list) shows a small panel by the pointer: the item's name, count, state and details, then the click/drag help. The game's webview shows no native tooltips, so slot titles go into `#bagtip`. The panel's family and skill chips use the same hover panel.
- Unit panel (`#heroframe`): the name drops the `{owner}` tag and no longer runs under "More" (the grid column can shrink). "Have a child with X" buttons became one full-width row, "Child ♥ X ♥ Y". The skill bar puts the unit's own skills first and "Nearby" creature actions on their own line, as single-line chips that cut long names short. A stray `.skill{display:grid}` rule made them wrap before.
- Nearby actions (`RemasterAbilities` in Abilities.dm): "Rescue X" is only listed when X is caught in a pit trap (the only time it does anything), and "Breed With X" is left out for partners, who already have "Child" chips.
- The 3D hover tag no longer says just "Move" for a plain move. A move with something to warn about (stairs, climbing, no way through) and every other order still show.
- Double mining fixed: with several units selected, one click on rock gave each of them a Mine order, so the first cut the notch and the next took the block above. Each Mine and "Mine roof" order now records the rock's state when it starts (`dug0`, `roof0`), and if another unit has already taken that block it ends with "That block is already out; mine again for the next", without a blow. When the notch is cut, the tile's HP is set to exactly half, so the block above is a whole block. Check: "two units, one click: one block" in `tools/check_breaking.py`.

## While you were away (2026-10-22)
- Villages keep working while you're away. A village only works while its player is connected (`RemasterTrack`), so `Player.remaster_seen` (saved) records when the game last ran for you, and the first tick after you come back (`Loaded`, world ready) catches up if it's been 5 minutes or more. It counts up to 8 hours at half the live pace, with at most 60 jobs a villager.
- Woodcutters, miners, haulers, farmers, cooks, carpenters and board workers on wood or stone orders replay their real work in their areas: each race's `Bump` chop and dig with tools or by hand, plants regrowing every 2 minutes and picked, seeds planted, the original cooking chance, the carpentry recipe. Goods go to `RemasterStoreFor`. Everyone eats down the original hunger (1 per 40 s) from the stores, then sleeps and heals; nobody starves while away. Miners skip rock beside water or lava, and spawned creatures are removed. Merchants and workshop orders wait for you.
- A "While you were away" card (`#awaycard`, HUD data `awayReport`, closed with `awayclose`) shows the work, goods, stockpile change, meals and events. It also goes into the village log.
- Engine bug: this OpenDream's `world.realtime` is always 0–9 (it uses `.Milliseconds` of the time since 2000). Use `RemasterNow()` / `RemasterSince()` (Away.dm), which take the UTC date from `time2text(0, "YYYY-MM-DD", 0)` and the time from `world.timeofday`. The Save button's "saved N s ago" now uses it too.
- Code: `Code/Remastered/Away.dm`; hooks in `QoL.dm` (`RemasterTrack`), `HUD.dm`, `Comfort.dm`, `WorldSave.dm`; the card in `remastered.html`. Checks: `tools/check_away.py` (13 checks); real client `tools/trailer/breaking/away_run.py`. Report: `remastered/reports/away-2026-10-22/RESULTS.md`.
- Hunters and builders also work while you're away. Builders run the construction tasks' own steps (`RemasterSiteFor`, `RemasterSiteFetch`, `RemasterSiteBuild`) without the walking. Jobs go in passes: gathering and building, then cooks, then carpenters. Server log: "Remastered: <key> was away …; catching up" / "caught up in N s".
- Hunters (live, `RemasterHunterTick`, and away): a bow with arrows in an equipped quiver first (`BowTarget(1)` every 5 s within 5 tiles), else javelins, throwing axes or stones (`RemasterTryThrow`/`RemasterThrowAt`) from 2+ tiles, else melee. They pick shots and throws back up (`RemasterHunterRearm`, `RemasterHunterQuiverUp`) or take them from a store, switch to a knife to butcher (`RemasterHunterWield`), and butcher a kill too heavy to carry where it lies. Away throws and shots are removed from `rm_hits` so no damage numbers pop up afterwards.

## Food pots, food stalls and poisoned food (2026-10-22)
- Villagers now get their meals from **Food pots** and **Food stalls** instead of off the stockpile, so a village's food supply can be poisoned the SS13 way. Both are in the Build tab (workshops) and the 3D ghost's workshop buttons: Food pot 1 stone, Food stall 1 wood, one tile each like the Cauldron.
- Both are food stores like a stockpile: food in them never rots and counts in the village food stock (`RemasterStockCount("food")`, so board orders and the away card see it). Cooks put cooked food in, farmers put crops out, and idle cooks restock them from the stockpile (cooked meat, fruit, cheese; raw meat waits for cooking). Hungry villagers walk to the nearest one with food for them (`RemasterFoodPlace`, Care.dm) and eat one serving with the original `EatItem()`, so food values, unhealthy raw meat, seeds and moods are the original ones. With none, the stockpile is the fallback as before.
- The Food pot is a cauldron for food: wood under it burns a minute a piece (Add wood / Light / Douse), heat rises to 120°. At 80° it stews one raw serving every 20 s (raw meat becomes cooked, fungus a stew anyone can eat) with no burn chance, so a cook with a pot and wood takes the stockpile's raw meat there instead of to a campfire. A pot at 60°+ serves "Hot stew": a quarter more filling and a good meal for moods. The Food stall holds 30; a villager who eats there takes a piece along, so fewer trips are made.
- Poisoning (only another realm's food, only at war, `RemasterMayPoison`): a unit beside it with a poison gets "Slip in …" buttons in the food box. Doses: extracted Toxic (PoisonContent, 10–45), Poison (8–40), Strong poison (15–65), a raw poison gland or root (15), a brew's Venom Draught/venom/Plague, or a Sleeping Draught (eaters fall asleep). A pot's poison is stirred through the stew: every bowl takes its share, food added later too, until it is emptied. A stall's goes onto the food lying there. Owner's villagers awake within 6 tiles may see it (50% each, less with sneaking skill); then the food is marked poisoned and the owner gets the alert.
- In the body (`rm_poison`, saved) poison sets in after 15 s, then a quarter of what's left acts every care step (~3 s): 6 blood (`BloodContent`, `BloodLoss()`, so the original bleeding rolls apply) and 6 HP per unit, halved by `ImmunePoison`. Death is DeathType "Poison"; at war the poisoner's realm scores. Undead, Gargoyles, Skeletons, SandKings, Zombies and Devourers are immune. When sickness sets in, and now and then after (30% a step), the villager throws up green vomit (`obj/RemasterVomit`, gone after 2 minutes; 3D draws a puddle of bile and, while fresh, the splash): 15% of the poison comes up with it, and 10 hunger.
- Noticing: tasting before eating (chance = dose × the poison's taste × 2.5 + CookingSkill/5, at most 90%; Toxic and alchemists' draughts taste least, raw glands most, a skilled poisoner hides it) spits the food out with a fifth of the dose; falling sick names where it was eaten; Inspect in the food box (30 + 2×cooking + 3×poison skill, made harder by a skilled poisoner); cooks check what they fill and throw out food under suspicion unless they find it clean. Food someone fell sick from or tasted wrong is avoided until it is emptied or inspected clean.
- Dealing with it: Empty the pot / Clear the stall; the new **Antidote** brew (bone dust 1 + water 2 heated to 100°, Brewing.dm; removes 3 poison per unit) drunk by hand or by the new "Drink an Antidote when poisoned" bag rule (also from a friend's bag within 3 tiles); an Elixir of Life clears it; the original Potion of Poison Immunity halves it.
- HUD: a food box beside a pot or stall like the Cauldron's (food in it, the fire, Put in food, Eat, Add wood, Light, Inspect, Empty / poison buttons for an enemy's), a green "Food alert" banner (click goes there, × dismisses), village log entries and minimap pings, and labels over each pot and stall in 3D ("Food pot 7/20", "· suspect"/"· poisoned" for the owner).
- 3D: the pot is an iron pot on three legs in a ring of hearth stones, a fire under it when lit, the stew level rising with what it holds (coloured by what's in it, sickly green when under suspicion) and steam when hot. The stall is a counter under a green-and-cream awning with a realm-coloured trim, the food laid out on it and crates in front.
- Offline catch-up: meals come from the pots and stalls first (with tasting and poison, which runs its course at once; whoever survives has rested it off), cooks restock them, and the card reports meals from the pots and poisoned meals.
- Save: the food in a pot or stall is kept in its saved text var `rm_food` (workshops save simple vars only), so no `WorldSave.dm` change.
- Code: `Code/Remastered/FoodSupply.dm` (new); hooks in `Items/Food.dm` (`EatItem`: taste before, poison after, like `RemasterAteThought`), `Care.dm`, `FoodRoles.dm` (cook, farmer), `Blueprints.dm`, `Construction.dm`, `Brewing.dm`, `Bag.dm`, `Away.dm`, `Board.dm`, `HUD.dm`, `View3D.dm`, `remastered.html`. Arena check: `tools/check_food_supply.py` (`tests/foodsupply_test.dm`, 26 checks). Real client: `tools/trailer/food/food_run.py` (real AppKit clicks on the food box and alert; 13/14, the miss was the runner probing before the box arrived, since fixed). The 3D food labels sit under the HUD panels (`#food3d` right after the canvas, z-index 0). The app was rebuilt and `tools/check_app.py` passed. Report: `remastered/reports/foodsupply-2026-10-22/RESULTS.md`.

## Herbs, the Doctor, drink, rotten food and the fever (2026-10-22)
- **Herbs** (`Code/Remastered/Doctor.dm`). Three herbs: Athelas (kingsfoil), Feverfew and Milk thistle. They grow as perennial plants (`obj/Items/Plants/RemasterHerbPlant/*`) that are picked down and grow back a leaf every two minutes, up to three. Nine wild ones are placed once around each village (three of each, 6–25 tiles from the stockpile, `RemasterPlaceWildHerbs`). Caravans sell them too. In 3D they are drawn in the crop pass: athelas has broad dark leaves and white flowers, feverfew has daisies, milk thistle is spiny with purple heads.
- **Remedies** are made at the **Doctor's stall** (1 wood, Build tab and 3D ghost; `mob/WorkShops/RemasterClinic`, its stock in simple vars, so it saves). Each takes one herb and succeeds 50% + 3% per point of the original Potion skill; a failure wastes the herb.
  - Athelas poultice: +80 health, stops bleeding.
  - Feverfew tonic: cures the fever and gives immunity.
  - Thistle purge: −30 poison, ends food poisoning, −50 drunk. Poured into a poisoned pot or stall, it neutralises 30 of its poison, so the food is kept.
  - A remedy in the bag is used like a potion. The bag rule "Use a carried Doctor's remedy when ill or hurt" (on by default) applies it by itself.
- **The Doctor job.** Each step, the Doctor:
  1. Treats the villager in most need within 40 tiles: bleeding badly, then poisoned, fever, food poisoning, badly hurt, very drunk.
  2. Checks food under suspicion and neutralises poisoned food with purges, instead of the cook throwing it out.
  3. Keeps two of each remedy in the stall.
  - To get a remedy, the Doctor tries in turn: its own bag, then the stall, then making one from an herb in the stall. With no herb it posts a **Board order** "Gather <herb>": priority High for a patient or poisoned food, Low to restock. It also picks the herb itself if one grows within 25 tiles. Board workers on that order pick herbs within 30 tiles of the stockpile and bring them to the stall. Herbs in stalls count toward the order. So the chain runs by itself: poisoned food → no remedy → order → gathered → made → used.
  - Without a Doctor, a sick or badly hurt villager walks to a stall that has the right remedy and takes it (care "remedy", Care.dm).
- **Drunk** (`Code/Remastered/Ailments.dm`, `rm_drunk`). Wine is a new brew: fruit juice 2 + fungus 1, cold (Brewing.dm). Drinking it adds 2 per unit and the mood "Merry with wine".
  - From 35: staggers a step the wrong way while walking, and hiccups.
  - From 60: may throw up.
  - From 85: passes out (`Sleep`).
  - It wears off by 1 a care step. Unhappy villagers carrying wine have a drink (bag rule "wine"). In 3D, a drunk villager's sprite sways.
- **Rotten food.** Every piece of food ages a minute at a time (`rm_age`, saved; `RemasterFoodRotStep`). At 60 minutes it becomes "Rotten …". At 120 it rots away even on a stockpile. Food pots and stalls keep food fresh (entries have a rotten flag), and a hot pot boils rotten food clean. Villagers smell rot and throw it away (70% + half the cooking skill) unless starving. Eaten, rotten food gives food poisoning (`rm_foodsick`, about a minute): retching and green vomit, hunger lost, a "Sickness" alert, and a 15% chance of the fever. The catch-up ages stored food over the time away.
- **Salt keeps food** (Ailments.dm).
  - Rock salt (`obj/Items/RemasterSalt`) comes out of mined rock: 6% per tile opened, 20% in the mesa (`RemasterBiomeMined`, Biomes.dm). Caravans sell it too.
  - Double-click it in a unit's bag (`RemasterUseFor`) to salt up to 4 pieces of the food that unit carries, meat first. They become "Salted …" (`rm_salted`) and age an eighth as fast: about 8 hours to rot.
  - Cooks with nothing to cook salt meat that has waited 20+ minutes on a store with salt (`RemasterCookSaltTick`).
  - Salt needs no combining to keep food. Salt lying on a stockpile or zone makes all food there age a quarter as fast, and so does salt in a unit's bag for the food in that bag. A lump keeps 10 pieces for 60 minutes and is then used up, leaving the bag when it's gone (`RemasterSaltedStoreFood`, `RemasterUseSalt`; the catch-up uses the store part).
- **The fever** (`rm_fever`, stages 1 coughing, 2 fever, 3 very ill, like SS13's virus stages).
  - Caught from rotten food, from miasma (rotting bodies, Vapours.dm), from Plague (food or brew), and from the sick. A sick villager spreads it to anyone within 1 tile and to sleepers within 2 (3%/step, 6% at stage 3), including other realms' people. A sick eater leaves germs in a pot or stall, and a hot pot kills them.
  - It starts coughing a minute after it is caught, and worsens every two minutes unless it breaks (2/1.5/1% a step, three times likelier asleep or in bed). Stage 3 drains 3 HP a step and can kill (DeathType "Fever").
  - A Feverfew tonic cures it, and then the villager is immune for 600 steps.
- **Shared plumbing:**
  - Alerts are now kinded ("Food alert", "Sickness") on the same green banner.
  - The ailments show in the unit's warnings (HUD.dm) and in the Health tab's conditions (`RemasterAilmentConds`, one line in Health.dm).
  - 3D sends `drunk`, `ill` and `cough` for units; a pale cough cloud shows now and then.
  - The original `EatItem()` now has one hook before the meal (`RemasterBeforeEat`: rot smelt, poison tasted) and one after (`RemasterAfterEat`: poison, rot, germs), in place of the two poison lines.
  - The catch-up sobers everyone, ends food poisoning, and cures a fever with a tonic from a stall or rests it off.
- Checks: `tools/check_doctor.py` (`tests/doctor_test.dm`, 16 checks).
- Real client: `tools/trailer/doctor/doctor_run.py`, with real AppKit clicks on the stall box and the Village › Board view.
  - Run 2 passed 12/12. It showed the whole chain: the poisoned pot, the Board order, the herb gathered, the purge made, the patient treated and the pot neutralised.
  - Run 3 added the cough cloud and passed 11/12. The miss was the Board click landing on the next button while the Village panel slid in; the runner now waits and retries.
- `tests/settlement_test.dm`'s `hud_data_json` check fails because it expects 3 recipes; the build-menu session added the beam.
- Report: `remastered/reports/doctor-2026-10-22/RESULTS.md`.

## Gravedigger, forensics, examine and speech, surgery, the tavern (2026-10-22)
SS13-style village trades, all in `Code/Remastered/`. Each new workshop is one tile, built from the Build tab (Workshops) or the 3D ghost, and keeps its stock in simple vars so it saves.
- **Gravedigger** (`Graves.dm`, job "gravedigger"; Graveyard: 1 stone, a stone cross).
  - People's bodies lying within 30 tiles of the stockpile are carried to the graveyard. Animal carcasses are left for the hunters. The body is buried with the original Bury effect: a Grave with the body inside, which then gives off no miasma or fever. A spade is needed, as in the original menu.
  - Graves go on free tiles within 4 of a graveyard. With no graveyard, they go on free ground 8–14 tiles from the stockpile. When a villager of your own is buried, everyone remembers "Our dead were laid to rest".
  - With nobody to bury, the gravedigger cleans up blood, green vomit and rotten food lying off the stores within 20 tiles. The catch-up buries the dead and clears the mess.
- **Forensics** (`Forensics.dm`).
  - A poisoner leaves 1–3 footprints (`obj/RemasterTrace`: race, realm, who; they fade over 15 minutes in 3D) and a clue on the food (`rm_clue`, saved; cleared by Empty).
  - Any Inspect of your food may read the clue: 20% + cooking + 2× poison + potion skill. A villager walking past strangers' footprints may notice them, with sneaking skill counting double.
  - A find goes into the log and raises a "Clue" alert. One roll in three also names the poisoner.
  - If the realm is at peace, this counts as a grievance, so war can be declared at once (as after an attack at peace). If it was someone of your own realm, the alert reads "Traitor!".
- **Examine and speech** (`Speech.dm`).
  - `RemasterLook()` says what anyone sees, for example: knocked out, pale and sweating, coughing or feverish, green around the gills, merry, reeking of wine or staggering drunk, bleeding or bandaged, badly hurt, grafted and false limbs, missing limbs.
  - It shows on the 3D hover tag and as a line under the selected unit's name.
  - `RemasterSay()` puts a speech bubble over a unit in 3D for 4 seconds, at most one every 5 seconds per unit unless forced. Units speak on poison onset, vomiting, hiccups, coughs, fever, hunger, hurts ("Ow!"), burials, surgery, brawls and the tavern.
- **Rescue and surgery** (`Surgery.dm`; Operating table: 1 wood, the nearest within 40 tiles of the Doctor).
  - First duty: the Doctor carries a downed villager (knocked out, fainted, can't walk, under 25% health) to the table.
  - Then, for a villager missing a limb, it uses a limb that is carried by the Doctor, carried by a villager at the table (the patient's own arm, the smith's false leg), lying within 15 tiles, or on a store.
  - Success is 40% + 2× potion + half the butchery skill, with 20% more for false limbs, at most 95%. A failure ruins flesh, hurts the patient and is logged. A patient operated on awake may go into shock; a Sleeping Draught the Doctor carries is given first.
  - Grafts: any race's arm or leg takes. A foreign limb brings some of that race's strength, agility and defence (an Orc arm gives +3 strength). Foreign flesh is rejected 15% of the time: it drops off within 1–4 minutes, with a "Surgery" alert.
  - False limbs, made from the table box:
    - iron (2 iron ingots): tough but slow
    - wooden peg leg (1 wood)
    - bone (3 bones)
    - glimmering (a cut gem): quick, +20 mana, and sparkles in 3D
    - **automail** (3 iron ingots and 1 silver ingot; needs metal crafting 15): +3 strength, +1 agility, +2 defence
  - A body beside the table gives up two arms and two legs ("Take an arm/leg").
  - Each limb is remembered (`rm_limbs`, saved: kind, label, stats, donor race) and shows when the unit is examined. When the limb is lost again, its effect goes with it.
  - **How it looks in 3D** (`RemasterLimbLayers`):
    - The body is drawn as the original's "No…" picture for the replaced slots, and each limb is laid on it from `Icons/Remastered/Limbs64/<sheet>.dmi` (made by `art/enhance/limbs64.py` from the Races64 sheets).
    - The limb always keeps the wearer's own shape, so it fits from the front, the back and the side. A first try transplanted the donor's own pixels, but other races hold their arms differently from the side, and they didn't line up.
    - From the side, the original draws only the near arm and leg. A replaced far limb is drawn as the near limb's shape moved back, arms up to 5 px and legs 3, where it peeks out past the body (`side_peek`).
    - A graft takes the donor race's skin (the three commonest colours of its arms) and its look: bone gaps, scales, spots, stone. A row of stitches marks the seam.
    - A false limb is drawn in iron, wood, bone, gem or automail (steel with joint seams and a brass bolt).
  - **Demon flesh** does what the hell portal does (Vars.dm `Portal()`, same odds): 15% go mad and tear their eyes out; of the rest, 25% are possessed and turn half-demon, then Demon, by the original `RaceChange(SUBRACE="HalfDemon")`.
  - Lizardmen, Vampires and Werewolves regrow lost limbs anyway (the original `Regen()`). Frogmen and Demons don't.
  - The Doctor:
    - It takes a limb from a villager carrying one at the table, so the patient can bring their own arm.
    - It takes a limb itself from a body laid beside the table, and the gravedigger leaves those bodies alone.
    - A remedy waiting on a Board order no longer stops it from rescuing, operating or keeping the stall. `RemasterDoctorGet` returns -1 for "waiting on the Board".
  - Hook in the original `LimbFling` (Combats.dm): severed limbs remember their race.
- **Tavern and brawls** (`Tavern.dm`; Tavern: 1 wood, up to 40 cups).
  - Wine gets in three ways: poured from bottles (3 units of a Wine brew = 1 cup), pressed at the counter (2 fruit + 1 fungus = 3 cups), or pressed by idle cooks from the stockpile when it runs low.
  - Moods are off in this build, so villagers go for a drink at night, at most every 5 minutes. With moods on, they go whenever their mood is under 50. Guards on patrol stay sober.
  - A visit is a round every 5 seconds: alone, until merry (30); with friends, up to 55, which is brawl level. A visit gives the memories "Had a drink at the tavern" or "Drank with friends".
  - Brawls: anyone at 50+ drunk may pick a fight with someone beside them (4% a care step). They trade the non-lethal blows of Subdue.dm until one is knocked out, 20 seconds pass, or a sober guard on patrol within 6 tiles breaks it up, sobering both by 10. Brawlers get the memory "Got into a fight".
  - In 3D a brawl shows a dust cloud and stars; the tavern shows its mugs, barrels and sign.
- **HUD:**
  - Boxes for the Operating table (missing slots, grafts, make limbs, take limbs from a body) and the Tavern (pour, press, drink).
  - Labels and models: tavern label; 3D models for the table, tavern, graveyard, graves and footprints.
  - Speech bubbles go in `#say3d`, under the HUD.
- Fixes found by playing it:
  - The gravedigger counted its own tile as taken, so it never buried anyone.
  - In the same Inspect click, the poisoned-food alert replaced the Clue alert.
  - With moods off, villagers never went to the tavern, and one cup could never reach brawl level.
- Checks: `tools/check_village.py` (`tests/village_test.dm`, 17 lines).
- Real client: `tools/trailer/village/village_run.py`, with real AppKit clicks on the Build tab, the food, table and tavern boxes, and the units. Report: `remastered/reports/village-2026-10-22/RESULTS.md`.

## Vampirism from Unholy Blood, soul stones, zombie and werewolf looks, pixel particles (2026-10-22)
- **Vampirism** (`HalfDemons.dm`). The Alchemy station no longer makes the Potion of Vampirism: its menu line is commented, and `StationCosts.dm` and `tests/potion_effects_test.dm` are updated to match. Drinking Unholy Blood (a Flask of Blood blessed at an Evil Altar) turns `rm_unholy_vampire`% of drinkers (25) into Vampires through the original `RaceChange("Vampire")`; the rest are Marked as before. Potions already made still work.
- **Soul stones** (`SoulStone.dm`).
  - A rare stone from surface rock: 0.7% per tile mined on level 1, the mountains (`Biomes.dm`).
  - A body remembers who it was: `MakeBody` stores `RemasterSoulOf()` on `mob/Body.rm_soul` (the name, race, gender, level, stats and every skill).
  - Double-clicked by a body, the stone takes the soul and the body crumbles. Double-clicked by a gargoyle of yours that has no soul, the gargoyle takes the name, level, stats where higher, and every skill. It remembers being that person, and its examine text says "a soul in stone".
- **Zombies for every race** (`art/enhance/zombie64.py` writes `Races64/<sheet>-Zombie.dmi`; `Undead.dm` `RmZombieSheet`, used by `Remaster3DBody64`). A plague zombie keeps its victim's icon, and in 3D it is now that race rotted: grey-green flesh tinted by the race, decay, bare bone, torn clothes, dead eyes and blood at the mouth.
- **Werewolves for every race** (`art/enhance/werewolf64.py` writes `<sheet>-Werewolf.dmi`; `Undead.dm` `RmWerewolfSheet`). A werewolf changed at night (`Werepowers`; its race comes from `SavedIcon`) is now its own race's wolf: fur tinted by the race, wolf ears, red eyes, fangs and claws. By day it is itself again.
- **Pixel particles** (`art/enhance/breath64.py` writes `Fx/breath.png`, 14 elements; the page has `V3_PARTICLES`, `v3breathFx` and `v3specialParticles`).
  - Dragon breath shows by kind through `RemasterBreathLook()`: fire, frost, poison, magma, sand, water, plague (zombie drakes), holy and unholy. What the breath does is unchanged (`RemasterBreathElement`), and it is named by kind: Magma spit, Diseased breath and so on.
  - Every race special's bursts, rings, trails and clouds are drawn with the same particles: mind rings, web strands, poison, acid and spark trails, dust for slams, leaps and charges, unholy smoke for the shadow step, fire-pot flames, a plague cloud. The thrown and shot objects stay 3D shapes, and `v3drawSpecial` still sets how long each effect lasts.
  - The server sends the atlas whenever specials are in view (`RemasterSpecialFxData`).
- Checks: `VG|demonflesh`, `VG|soulstone`, `VG|undead` in `tools/check_village.py`, and `unholy_vampire` in `tools/check_halfdemons.py`.

## Building in the Guide: walls, gates, roads, halls, carts, power, lifts (2026-10-22)
- **Guide.** New "Building" section in the in-game Guide (`remastered.html`, `details#guideBuilding`, after "Looking after your people"). It covers how construction tasks and builders work, wall-walks, getting up, gates, houses and forts, roofs, roads and bridges, halls in mountains, mine carts, power and lifts.
- **Walls** (`WallWalks.dm`, 3D in `remastered.html`). Every non-house wall gets a walk on the sky layer: two units a tile in front and back ranks, Climb orders via stairs and ramps, and the walk falls on a breach. Outer faces are crenellated (one broad merlon, coping) and inner faces get a lip. A free-standing wall is crenellated only on the side away from the nearest claim banner (`RemasterWallOuter`, `RemasterWallFree`). Wooden walls with a walk are timber ramparts.
- **Gates** (`v3gateGeom`, `v3gateArch`, `v3gateDoors`). A timber gatehouse between wooden walls, a stone round arch between stone walls, big double doors and outer torches. A portcullis (`Gates.dm`) also carries the walk (`RemasterGateLeaf`). Ordinary doors now face along their wall.
- **Houses and huts.** A walled space of 4 to 40 tiles with a door or open doorway is a house whatever its floor (`RemasterHutFill`, `RemasterDoorway`, `RemasterJamb`; water is no doorway jamb). It gets a roof through the hut pass in `v3roofs` (`v3roofsForDoors` rebuilds roofs when doors change).
- **Roofs.** Gable on rectangles, hipped otherwise, thatch over timber and slate over stone. Every roof on screen is see-through at play zoom and solid when zoomed far out. There are no roofs underground or over halls in rock.
- **Roads** (`Roads.dm`). A cobbled road (1 stone a tile, 0.7&times; step time) and a dirt track (free, 0.85&times;). Rails share `turf/remaster_road` ("rail", no walking bonus). Bridges now draw in 3D (kind "bridge" with `under`).
- **Stairs built in play** now reach 3D as stairs (`Remaster3DIsStairs`), so wall ramps rise to their head stairs.
- **From the Build menu chat:** halls in mountains with the Ceiling setting, the mountain cut-away, mine carts and rails, power (water wheel, windmill, axles, bellows, rune dynamo), lifts, portcullises and drawbridges.
- Checks: `tools/check_wallwalks.py` (15 lines: huts, moat bank, portcullis gate, built stairs in 3D) and `tools/check_roads.py` (7 lines).

## MMO architecture plan (2026-10-22)
- The user's goal: Kin & Stone as an RTS MMO (one persistent world, many players, accounts) with a world the scale of Daggerfall's (a vast generated land of regions). The plan is `remastered/planning/MMO_ARCHITECTURE.md`: what exists today (`Joining.dm` password gate, `auth.mode=0`, `net.max_connections=16`, `WorldSave.dm` chunk diffs, `Away.dm` catch-up, the web relay), the engine's tick budget from the 2026-10-20 soak (about 1 ms per unit and 12 ms per connected player per tick, estimated; about 80 units at 10 ticks/s today), server topology (a dedicated Linux server, the Mac app as client, relay hosts for the web), persistence (chunked write-behind saves, SQLite, the reload bugs as blockers), accounts (signed tokens at the gate, the account id as the player key), authority (HUD commands are owner-checked; the original verbs are not), sleeping realms woken on contact, hosting costs, a four-phase roadmap (10, 50, 200+ players), honest positioning (not "the first": Shattered Galaxy, 2001), and the region design for a Daggerfall-scale world (regions from a seed, loaded on demand, diffed saves, a travel map, shards by region).
- Engine check for the plan's regions and extra storeys: `remastered/tests/maxz_test.dm` (run with `tools/check_breaking.py --entry MzRun --extra tests/maxz_test.dm`) shows OpenDream grows the map while running: one new z-level in 5 ms (120x100 arena), four more in 56 ms, 50 more columns in 109 ms; new levels take turfs, items and moving units; old tiles untouched. Section 12 of the plan adds the user's framing: each player is a town and a travelling hero party, with Daggerfall-style template quests from NPC towns and the Bulletin board.

## Use on: hold an item, click what it is for (2026-10-22)
- **One mode for every item that works on something else** (`Code/Remastered/UseOn.dm`; page: `bagButton`, `v3useOnBanner`, `v3hover`, the 3D mouse-up and Escape handlers, rings in the effects pass).
  - Click such an item in the unit's bag, in the bag bar or the inventory list, and it is held: its slot is outlined green.
  - A banner (`#useon3d`) says what to click, for example "Soul stone: click the body of the dead to take their soul · right-click or Esc to let it go".
  - Every valid target within 15 tiles gets a breathing green ring in 3D. Hovering one says what will happen ("Take the soul of Brunhild"); hovering anything else says it is not for this item.
  - Click a ringed target and the unit walks to a free tile beside it (`RemasterUseOnSpot`) and does it.
  - Right-click or Esc lets the item go.
  - Right-click on the item in the bag opens its original choices, and a double-click still uses it at once.
- **Chains:** after the soul is taken, the soul stone is held again and the banner moves on: "Brunhild's soul is in it: click a gargoyle of yours to wake it".
- **Items and targets:**
  - soul stone: a person's body, then a soulless gargoyle of yours
  - remedy, potion or brew, food: a villager (treat, give to drink, feed)
  - food: your food pot or stall (put it in)
  - poison: a pot or stall of a realm at war (slip it in)
  - wine brew: your tavern (pour it in)
  - herb or remedy: your Doctor's stall (put it in)
  - severed or false limb: a villager missing that limb (they take it to the Operating table for the Doctor)
  - weapon or armour: a villager (handed over and put on)
- **Server:** commands `useonpick`, `useonat` and `useoncancel` (HUD.dm). The model's `useon` carries the item, its ref, the banner hint and the targets (id, x, y, label); ids are UI refs for your units and `\ref` for everything else. Bag items carry `useon`=1 (`RemasterUseOnAble`, cheap).
- **Adding an item:** a branch in `RemasterUseOnTargets` (what, and the hint) and one in `RemasterUseOnDo` (doing it).
- Checks: `tools/check_useon.py` (`tests/useon_test.dm`) for the server; `tools/check_useon_hud.py` for the page (headless Chrome, `?overlay`): the bag bar, the inventory flag and the table box for a unit carrying items, with no script error in the console.
- **Page errors stay quiet:** `updateHUD` catches its own exceptions, so a throw only logs to the console and the unit card stops updating. Run 10 and run 11 lost every unit card for units carrying items that way: a `root` that should have been `item.root` in `renderUnits`. Fixed.
- **Real-client probes:** the HUD is zoomed (it fits 0.8 at 1280x720). Probes must report window pixels: the 3D projection times `hudKC()`, element rects times `hudKC()/hudK()` (`tools/trailer/*/hook.js`). They also record a throw inside `updateHUD` in `jsErrors`.

## Flyers over mountains, and the camera lock that follows (2026-10-22)
- **Clicking rock with flyers:** `Player/RemasterClickKind` (Flying.dm) is the order a click gives. Rock (`Mine`) becomes `Move` when every selected unit is flying, so they fly onto it. `RemasterOrder` uses it, and so does the hover hint (`RemasterHoverVerdict`: "Fly on top"). Flyer-only groups sent onto rock skip the formation, which would put them on open ground beside it. Walkers, and mixed groups, still mine. An "up" click on a peak top already climbs flyers up (`RemasterCanClimb`).
- **Drawn above the rock:** the page adds the rock height under a flyer (`v3groundAt`, eased as `kd.lift`) to its base. It used to be drawn at its flying height over the open ground, inside the mountain. Picking always aimed at ground plus height.
- **Camera and rock:** over a mountain the aim is 0.6 of the rock height, inside it. The pull-in that brings the eye in front of rock now ignores the rock round the aim: only rock the view meets after clearing it counts. The eye is clamped above the ground under it after the pull-in, and the iso near plane (0.2 of the eye distance) shrinks with the pull-in. Before, the eye went to 15% of its distance, inside the rock, with the near plane past the target.
- **Camera lock = free camera that follows:** Chase, F9 or Lock camera centres the unit once (`V3.lockOn`). After that the page moves the camera as far as the unit moves (`V3.lockAt`). Pan, turn, tilt and zoom stay free; a right-drag pans and no longer unlocks. While locked the page ignores the server's view centre. The server moves its own view by the unit's movement too (`remaster_lock_at`, PlayMode.dm). Locked on a flyer, the camera aims at the flyer's height (`V3.lockT`).
- Checks: `tools/check_flying.py` (two new: `flyer_click_on_rock_flies_on_top`, `walkers_still_mine_rock`). The real client runs `tools/trailer/village/village_run.py` with `VC_ONLY=soul` (soul stone, lock) or `VC_ONLY=fly` (flyer over a scene-made mountain).

## Soak "units at no place after a reload" was the trailer fixture (2026-10-27)
- The soak run3 reload showed 27 orcs at 0,0,0 (full HP, in the roster). They were not saved units: the soak arena's `trailer-scene.txt` still said `kingdom`, and after the restart `ZZTrailer.dm` (test-only) forgot the scene and staged it again with no site (`tr_site` is not saved). `TrNear(null)` made 26 orcs plus the builder at a null turf. The smoke run's +27 was the same replay.
- The unit save is fine: in this engine x/y/z of a unit inside an object (any cage, not only `rm_cap_cage`) are the object's tile, so `savedx/y/z` are right.
- Fix (tests/soak-arena only): a scene file left from before a restart is logged as `TR|stale|` and not staged; scenes that need the site skip with `TR|nosite|` when there is none.
- Check: `tools/check_unit_place_save.py` (`tests/unit_place_save_test.dm`) - a unit on open ground and one in an old Capture cage keep their tiles through `SaveUnits`, and a stale `kingdom` scene is not replayed. It fails on the old trailer.
