# Banners of the Deep: A Dungeon Master Tale

**Players see the game as _Banners of the Deep: A Dungeon Master Tale_** (short: BOTD; renamed October 24; before that _Land of Lords_ for a day and _Kin & Stone: The Deepholds_ for a day): the title screen, window title, Dock icon, loading screen, launcher and HUD use that name. The About section in the in-game Guide credits Dungeon Master, the BYOND game by Aaron Davey and contributors (GPL v2). The app is `Banners of the Deep.app` (the old names, `Dungeon Master Remastered.app` and `Land of Lords.app`, are hidden shortcuts to it), and the save folder keeps its old name so existing saves keep working. The title art, icons and the client's start-up texts come from `tools/make_client_brand.py`; to change the name, edit `NAME`, `LINE1`/`LINE2` and `MONOGRAM` there and run it. Then change the name in `game/skin.dmf` (the window title), in the header and About section of `game/Interface/remastered.html`, in `mac-app/Launcher.m` and `mac-app/launch.zsh`, and in `DISPLAY` in `tools/build_app.py`, and run `tools/build_app.py`.

The main game is **[Banners of the Deep.app](Banners%20of%20the%20Deep.app)** (`Land of Lords.app` and `Dungeon Master Remastered.app` are symlinks to it) directly inside this folder. It is built from the current Remastered source, including the latest 3D, village, realms, war, fishing and persistence work. No BYOND or Godot installation is needed.

## Open the current game

Double-click the main app and choose **Play**, **Host for friends**, or **Join a friend**. Both personal and shared builds now use your Mac login name, so updates open the same account. The previous personal-only `Kiwi` override has been removed; on this Mac the existing `kiwimango` save contains the current three-Dwarf army.

### Play in a web browser (October 22, first version)

Friends can play from a browser tab without installing anything; the hosting Mac runs one small
headless game client per web player. Host the world as usual (**Host for friends**), then
double-click **Host on the Web.command** in this folder: it builds the relay the first time
(`tools/build_web_relay.py`), runs the lobby (`tools/web_host.py`) and prints the address to give
out, `http://<this Mac>:8080/`. Friends' guide: [JOIN_IN_BROWSER.md](JOIN_IN_BROWSER.md).

Players open that address, enter a name and the world password, and play: the full layered HUD,
the 3D world, prompts (as cards), and the skin's keys all work in the browser. Each player uses a
port from 12200 up; for friends elsewhere, reach the Mac through Tailscale or a port forward, as
for native joining. `--private-world` starts a throw-away world for testing. Design, what headless
needed, cost (~300 MB and ~half a core per web player) and what is not done yet:
[planning/WEB_CLIENT.md](planning/WEB_CLIENT.md).

Saves remain in `~/Library/Application Support/Dungeon Master Remastered`. Updating the app preserves that directory. The app bundles no player saves by default. Classic import is an explicit legacy option for a new personal profile; it never replaces an existing unit-save directory.

`dist/Dungeon-Master-Remastered-mac.zip` is the shareable download (October 21). Its game, HUD, engine and client match the main app exactly; it has no saves, and its `Source` folder carries the game source plus the Remastered engine and Mac client sources. The previous October 20 share build is in `restore-points/before-share-20261021/`. Classic is in `../replica/`; the Godot experiment is in `../frontier/`.

## Playing

- Click a unit to select it. Shift+click adds/removes units; drag selects a group.
- Click destinations or any loose item to issue orders; with **Gather** on (G, off by default) a click on a tree, rock or fishing spot chops, mines or fishes it (off: right-click them). Units always carry them out: asleep, flying, blind, crippled, without a tool or with a full pack, they find a way ([report](reports/obey-2026-10-21/RESULTS.md)). **Add tasks** queues work; deselecting leaves work running.
- **Space** pauses/resumes time. **Shift+Space** deselects.
- **A**, then a click, attacks or attack-moves. **F**, then a click, aims a race special. **Ctrl+A** selects all.
- The game is always 3D: right-drag moves the camera, middle-drag turns it, the wheel zooms. **F3** opens the guide.
- Village, Work and Realm panels manage people, tasks, stockpiles, construction and diplomacy. The unit frame provides inventory and abilities.
- **HUD layout** ([report](reports/hud-2026-10-22/RESULTS.md)):
  - Bottom centre: one slim action bar. Stop, Attack (A), Lethal, Gather (G), Plan, Build (B), Interact (I), Focus (Z), Controls, then Do now / Add tasks and Deselect. The keys show in the buttons' corners; hover a button for what it does.
  - Right-hand column: the minimap panel, with layer buttons and a row of camera buttons (N, Top, Iso, Chase) plus Map and Guide; under it, the Company list, only as tall as your company.
  - Far right: a rail of buttons: Village, Work, Build, Realm, Map, Army, Guide and Settings. Units and Orders open from the unit card.
  - Messages: one dark panel at the bottom right, newest at the bottom, each line fading after 10 s.
  - Several units selected: the band card has three tabs. Band shows faces to click and Select all / Next idle. Orders has formation, patrol and Unload / Take. Combat sets Lethal / Non-lethal, style and stance for the whole band; a button shows as pressed when everyone agrees.
  - Minimap: unexplored land is a faint checker and explored land is drawn lighter. Your units are outlined dots, gold when selected. The camera is a gold frame, and N marks north.
  - Every HUD control explains itself on hover. The top bar reads "3 people · 1 idle · 2 selected".
  - The HUD follows the window (October 22): Settings → HUD size defaults to **Auto**, which scales the whole HUD from the window's size (laid out for 1440x900; 0.6x on small windows up to 1.6x on big screens) and re-fits when the window is resized. Small / Normal / Large / Extra large remain as fixed choices. At any size other than Normal the map now fills the window and clicks, box-select and right-click land on the cursor (the old sizes left the map short and the cursor off).
  - Questions with a list of answers (what to do with an item, a workshop's menus, the Interact menu) are asked in a HUD card, not the native "Choose" window. Esc cancels.
  - One log: Village › Log lists what happened in the village (click an entry to go there); its **Messages** filter keeps every message and fight line of the session, with the time. Army (top-right menu, where Log was) has two tabs: Formations (the shape a group keeps when you send it) and Captives (who you hold, their rope and loyalty).
  - With a unit selected, right-click another of yours: Carry them (if they are down), Treat with a remedy, Feed, or Give a potion to drink, from what the unit carries. A body: Carry the body. Dropping a bag item on a unit asks whether to use it on them or just give it.
  - Right-click in 3D: the Interact card, showing what you clicked and big buttons for what you can do with it. A workshop's Use / open lists everything it can make or do; pick one and the selected unit walks over and makes it.
- **Unit card tabs** (one unit selected): **Overview** (bag, orders, the work at hand), **Health** (a body diagram coloured by injury, blood, bleeding and other conditions, every body part's state), **Family** (house, parents, partners, children, siblings; click one to select them; have a child, family tree, name as heir), **Interact** (the Interact menu: what it can do itself and with the creature beside it, capture or tame), **Combat** (Lethal / Non-lethal, combat style, stance, race special, combat and weapon levels), **Skills** and **Spells**. The card remembers the last tab.
- **Lethal / Non-lethal** (command bar, or a unit's Combat tab): non-lethal units knock enemies and animals out instead of killing them; a knocked-out creature lies down with a "Zzz" for 30 s. **Capture / Tame** (right-click a creature, or click one that is knocked out): the selected units knock it out and take it. A person is tied with a rope (one of yours must carry one) and never joins on their own: win them over or enslave them from their card; an animal is tamed at once. Dragons and grown spiders are too big to knock out by hand ([report](reports/subdue-2026-10-22/RESULTS.md)).
- **Build** tab: pick a fortress piece (Helm's Deep wall with a walk on top, tower, gate, wall stairs, ramp), wall, floor, bridge, stairs, workshop or trap (only what your races can build) and click or drag it on the ground. Each plan is a construction task showing what it needs ("10 stone: 8 in stockpiles, 2 missing"). Assign selected units to it, or give villagers the **Builder** job: they fetch material from the stockpiles, build tile by tile with the original rules and take leftovers back. With no stock the task waits and posts a bulletin-board order.
- **Buildings and lairs** (Build tab): whole race buildings placed with one click (Rotate turns them): Dwarven forge-hall, Timber house, Elven lodge, Orc war lodge, Goblin warren, Kobold den, Rat warren, Tribal hut. Each is one construction task; workers lay the floor, bring beds, tables and chairs from a stockpile, build the workshop, raise the walls and hang the door. The rare races get lairs: a spider's brood lair (silk, cocoons, cobwebs, a sticky web at the way in; spiders spin web faster in it), a dragon's lair with its hoard (a sleeping dragon heals faster beside it, more with gold and gems), a Devourer flesh hive and the Svartalfar's hidden sanctum behind rock-looking walls. Underground, the rock inside a lair is dug out first. Eggs laid in a lair hatch sooner. Spiders also get their hunting kit: sticky webs that hold prey and call nearby spiders, web pits, cocoons, cobwebs and silk floor.
- **Into the mountains (Moria)**: dig a hall into a mountain and build in it. Halls (Build tab) are dragged to any size on open ground or into rock: walls round it (rock is the wall where it is cut into a mountain), lines of stone pillars or support beams, beds, a table or campfire and the race's workshop; the door goes where it meets a tunnel, and a tunnel is dug to it through up to ten tiles of rock. Rock is dug out by the hall's own workers (by hand if they have no pickaxe). Stone walls inside a mountain or underground are carved (pilasters, a carved band, torches that light the hall), stone floors are big carved flagstones, and dwarven pillars rise to the rock roof. Built walls underground or in a mountain hold the roof up like support beams. In 3D, when the camera is inside a mountain the rock round it is cut away down to the tunnel ceiling, so the halls show. A mountain top with no rock or tunnel roof left under it opens to the sky (no more brown tops floating over dug-out ground).
- **Mine carts** (Build tab, Rails): drag rail track (a wood a tile; it can't cross a cobbled road), put a cart stop on it beside the stockpile (unloading) and others out by the mines (loading), and a mine cart (3 wood) on the track. Miners and haulers drop what they carry at a loading stop when it is nearer than the stockpile; the cart waits there until it is full (or half a minute with something in it), rolls along the track, tips its load onto the stockpile and goes back to the busiest stop. In 3D: wooden sleepers and iron rails that join at bends and junctions, the carts heaped with ore when loaded. The same stops and carts are meant to carry rail trade between towns later.
- **Power** (Build tab, Power): a water wheel on a bank beside water (10 power) or a windmill under the open sky (6, 10 on a mountain top) turns a line of axles (a wood a tile, joined side by side). Machines on the line use it: bellows beside a forge, smelter or melter make the smith there work twice as fast (4 power); a rune dynamo touching a rune circuit charges its mana crystals (5). A line that can't feed all its machines runs none of them. In 3D the wheel and the sails turn and the bellows pump while the line runs; the dynamo's runes glow.
- **Lifts** (Build tab, Power): Lift up or Lift down, 6 wood, from where it is built to the level above or below: a shaft down to the tunnels (dug through rock if need be), up from the tunnels, or at the foot of a cliff or wall walk up onto the mountain top. Its winch takes 6 power from an axle beside it; while the line turns units ride it like stairs (move orders and builders take it by themselves), without power it stands still and routes go round it. In 3D a timber tower with a riding cage up the cliff, a head frame with its wheel over a shaft. `tools/check_lifts.py` checks it.
- **Gates worked by levers** (Build tab, Fortress): a portcullis (4 wood a tile) in a gap of up to three tiles between two walls or in a tunnel mouth, and a drawbridge (4 wood a tile) across a moat before a gate, up to five tiles wide and as wide as you like: paint it, and it is built out from the bank, each piece from the deck of the one before. Pieces of a gate touching side by side move as one, once a pull. Lay rune lines from a lever (or a pressure plate) to them: each pull drops or raises the portcullis and raises or lowers the drawbridge, for 3 mana from the circuit's crystals, or free while an axle turning beside the gate drives it. A dropped portcullis bars the way but can be seen and shot through; a raised drawbridge leaves open water no one crosses. No part of a gate closes while a unit stands in any of it. `tools/check_gates.py` checks them.

## Current systems

Remastered includes a layered HUD and 3D world, village jobs and standing orders, self-care and homes, families/heirs, construction, workshop automation, multiple stockpile zones, persistent skill experience, fishing, alchemy, rune circuits, realms and war, siege engines, race specials, hosting/joining, and pause/game speed. Moods are present but disabled.

World saving now records terrain changes, workshops, ground items, rune pieces, claims and siege engines as well as player/unit data. `tools/check_unit_save.py` checks save/restore across restarts ([October 21 save fixes](reports/save-fixes-2026-10-21/RESULTS.md)). Long play sessions and performance still need controlled verification; this is not a claim that every original interaction or save case is complete. Physical phone/tablet input and mobile exports remain future work.

## Source and builds

- `game/` is the canonical Remastered game source. `Code/Remastered/` contains the new systems.
- `game/Interface/remastered.html` contains the layered HUD and WebGL view.
- `art/` and `assets/` hold the art pipeline and generated sprite atlas.
- `engine/server/` contains Remastered's clock-enabled runtime; `engine/webview-webkit/` contains its native client module. Shared engine dependencies come from `../replica/runtime/` without changing Classic gameplay.
- `mac-app/` contains the launcher. `tools/` contains builders and verification scripts.

Run from this folder:

```sh
python3 tools/build_app.py                 # main app, existing Mac-login account
python3 tools/build_app.py --shareable     # separate dist app and ZIP, no saves
python3 tools/check_app.py --race Human --native-panels
```

A main build overwrites the existing main app; preserve a restore point before rebuilding. The October 21 promotion stages and tests its candidate before replacement. The previous app and save copies are in `restore-points/before-main-promotion-20261021/`.

## Evidence and remaining work

- [Main build promotion](reports/main-promotion-2026-10-21/PROMOTION.md): exact package, private lifecycle checks, account identity and save preservation.
- [October 20 verification](reports/verification-2026-10-20/REVIEW.md): source/package comparison, fresh focused checks and outstanding issues.
- [Development notes](../NOTES.md): chronological feature history; the newest dated entries supersede older descriptions.
- [Action inventory](ACTION_INTERACTION_INVENTORY.md), [Easy Orders plan](planning/EASY_ORDERS_PLAN.md) and [sprite pipeline](planning/SPRITE_PIPELINE.md): earlier design/coverage records, not current completion percentages.

The Hero-mode Deselect and Space/Shift+Space help issues were fixed on October 21 ([report](reports/deselect-fix-2026-10-21/RESULTS.md)). Obsolete test expectations are tracked in the verification review; save fixes are in the [October 21 save report](reports/save-fixes-2026-10-21/RESULTS.md). The October 17 regression counts and documentation describe an older snapshot.
