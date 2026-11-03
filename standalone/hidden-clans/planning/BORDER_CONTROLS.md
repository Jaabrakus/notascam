# Permanent map-border controls

The current replacement layout is documented in [COMMAND_DOCK.md](COMMAND_DOCK.md).
The source inventory below remains the reference for every original command.

Source audit of the active Remastered game on 2026-10-16. This is a code-derived reference, not a live UI test. No game code or running app was changed for this audit.

There are **54 permanent `/obj/Hud` objects: 44 actionable controls, one day/night indicator, and nine decorative frame pieces**. Login creates 51 and Selection creates three. They use a fixed 19×19 screen grid: `(1,1)` is bottom-left; `(19,19)` is top-right. These are screen positions, not world coordinates. All use `HUD.dmi` except the three autodig painting buttons, which use `Selection.dmi`.

Current Remastered routing runs an actionable icon on one left click/tap and suppresses a repeated click burst; original handlers are named `DblClick`. Right clicks on these icons are consumed without running their action. Decorative icons have no action even though they use the same event routing. Keyboard bindings assume game/map focus; `—` means no dedicated binding in the current skin.

Construction: [Login.dm](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Code/Login.dm:638>), [Selection.dm](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Code/Selection.dm:121>). Click routing: [QoL.dm](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Code/Remastered/QoL.dm:111>), [Actions.dm](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Code/Remastered/Actions.dm:193>). Keys: [original bindings](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/skin.dmf:160>), [Remastered additions](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/skin.dmf:439>).

## Top edge, left to right

| Position | Label / `/obj/Hud` subtype | `icon_state` | Current effect | Key | Source |
|---|---|---|---|---|---|
| `1,19` | Autodig painting / `DigSel` | `autodig` | Toggle map painting between normal orders and `PlaceAutodig`. Selected workers must have their own autodig enabled to perform the marked work. | F5 | [23](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Code/Selection.dm:23>) |
| `2,19` | Add dig marks (+) / `DigAdd` | `addi → adda` | Switch from remove mode to add mode; the active icon is `adda`. Does nothing outside remove mode. | Tab toggles +/− | [2](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Code/Selection.dm:2>) |
| `3,19` | Remove dig marks (−) / `DigSub` | `subi → suba` | Switch from add mode to remove mode; the active icon is `suba`. Does nothing outside add mode. | Tab toggles +/− | [12](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Code/Selection.dm:12>) |
| `10,19` | Day/night indicator / `Day` | `Sun / Moon` | Indicator only: shows the global day/night state. No action. | — | [127](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Code/Login.dm:127>) |
| `18,19` | Worker autodig on/off / `DigOnUnit` | `DigOnUnit` | Toggle each selected worker independently. Off clears its destination, dig target, and owned dig marks. | — | [234](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Code/Login.dm:234>) |

The **+ and − change autodig mark painting; they do not zoom**. F5 enables/disables the painting mode; Tab toggles add/remove while it is active. The worker toggle at `(18,19)` is a separate setting. Mark assignment is per worker; this legacy mark list is separate from the finite task queue. Handlers: [Selection.dm](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Code/Selection.dm:42>); mark creation/removal: [Building.dm](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Code/Building/Building.dm:268>).

## Left edge, top to bottom

| Position | Label / `/obj/Hud` subtype | `icon_state` | Current effect | Key | Source |
|---|---|---|---|---|---|
| `1,16` | Toggle camera marker / `Pointer` | `Pointer` | Toggle the player/camera icon between `Player.dmi` and null. | — | [213](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Code/Login.dm:213>) |
| `1,15` | Find selected unit / `Find` | `Find` | Centre camera on selected units; with several selected, the final iterated unit wins. | Z | [610](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Code/Login.dm:610>) |
| `1,14` | Open information/HUD / `Updates` | `Updates` | Calls Updates → Intro; current Player.Intro opens the Remastered HUD. Original tooltip says updates. | T | [601](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Code/Login.dm:601>) |
| `1,13` | Stop selected units / `Stop` | `Stop` | Cancel selected owned units’ active/pending/delivery orders and targets; suppress role/autodig/guard restart. Original tooltip overstates “all”. | P | [619](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Code/Login.dm:619>) |
| `1,12` | Choose race / restart / `Restart` | `Restart` | Open the restart flow. Existing forces require confirmation; proceeding releases/deletes previous units and chooses a new race. | R | [591](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Code/Login.dm:591>) |
| `1,11` | Private message / `MSG` | `MSG` | Current override prompts for an online recipient and text; reports when nobody else is online. | W | [555](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Code/Login.dm:555>) |
| `1,10` | World chat / `Say` | `Say` | Invoke WorldSay; message, mute, ignore and cooldown rules remain in the verb. | S | [564](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Code/Login.dm:564>) |
| `1,9` | Camera waypoints / `Way` | `Way` | Set or jump to one of three saved camera waypoints. This is not a worker order queue. | Q | [573](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Code/Login.dm:573>) |
| `1,8` | Select all owned units / `All` | `All` | Add owned non-wagon units throughout the world to selection. | E | [225](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Code/Login.dm:225>) |
| `1,7` | Select nearby owned units / `Area` | `Area` | Add owned non-wagon units in `orange(usr)` around the camera to selection. | A | [203](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Code/Login.dm:203>) |
| `1,6` | Build menu / `Build` | `Build` | Toggle the original build palette (`Test`/`Building`); selected misted units block it. Options depend on units/materials. | B | [194](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Code/Login.dm:194>) |
| `1,5` | Online players / `Who` | `Who` | List currently connected players. | H | [582](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Code/Login.dm:582>) |
| `1,4` | Show coordinates / `Cords` | `Cords` | Print camera X,Y,Z coordinates. | C | [546](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Code/Login.dm:546>) |
| `1,3` | Go to coordinates / `Warp` | `Warp` | Current override prompts for X,Y,Z and moves the camera to clamped world coordinates. | G | [176](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Code/Login.dm:176>) |
| `1,2` | Interact nearby / `Interact` | `Interact` | Run the original nearby interaction menu for selected units. | I | [185](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Code/Login.dm:185>) |

Selected-only Stop override: [Orders.dm](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Code/Remastered/Orders.dm:418>); stop effects: [Orders.dm](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Code/Remastered/Orders.dm:72>). Camera/selection verbs: [Verbs.dm](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Code/Verbs.dm:1183>); waypoints: [Verbs.dm](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Code/Verbs.dm:1017>); restart consequences: [Restart.dm](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Code/Restart.dm:21>). Updates and T both call Intro: [World.dm](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Code/World.dm:325>); current Intro, message and warp overrides: [HUD.dm](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Code/Remastered/HUD.dm:327>).

## Bottom edge, left to right

These are immediate nearby pickup/processing actions, not queued travel. Unless stated otherwise, the border handler scans `oview(1, unit)` and calls `PickUpItem`; carrying capacity, flight/mist, item suffix and material restrictions still apply.

| Position | Label / `/obj/Hud` subtype | `icon_state` | Current effect | Key | Source |
|---|---|---|---|---|---|
| `4,1` | Pick up seeds / `Seeds` | `Seeds` | Try collecting nearby Seeds. | — | [406](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Code/Login.dm:406>) |
| `5,1` | Collect arrows into quiver / `Arrows` | `Arrows` | Requires an equipped LeatherQuiver and WearingBack. Moves arrows from `view(1)` directly into the quiver; see caveat below. | — | [534](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Code/Login.dm:534>) |
| `6,1` | Pick up ingots / `Ingots` | `Ingots` | Try collecting nearby Ingots. | — | [524](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Code/Login.dm:524>) |
| `7,1` | Pick up gems / `Gem` | `Gems` | Try collecting nearby gems. | — | [515](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Code/Login.dm:515>) |
| `8,1` | Pick up stone / `Stone` | `Stone` | Try collecting nearby ores/stone. | — | [506](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Code/Login.dm:506>) |
| `9,1` | Pick up wood / `Wood` | `Wood` | Try collecting nearby woods/wood. | — | [497](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Code/Login.dm:497>) |
| `10,1` | Pick up bones / `Bones` | `Bones` | Try collecting nearby Bones. | — | [487](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Code/Login.dm:487>) |
| `11,1` | Harvest/pick up food and bodies / `Edibles` | `Edibles` | Harvest one fruit from each nearby grape/tomato plant with Content≥2; then try collecting nearby Food and corpses. | — | [425](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Code/Login.dm:425>) |
| `12,1` | Pick up ores / `Ores` | `Ores` | Try collecting nearby ores excluding icon state `Stone`; skips Silver for vampires/werewolves. | — | [415](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Code/Login.dm:415>) |
| `13,1` | Pick up armour and a weapon / `Armor` | `Armor` | Try one successful pickup per category: chestplate, leggings, left arm, right arm, helmet, shield, weapon. | — | [380](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Code/Login.dm:380>) |
| `14,1` | Pick up skins / `Skin` | `Skin` | Try collecting nearby Skin. | — | [396](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Code/Login.dm:396>) |

Two implementation caveats matter when replacing these controls:

- The original arrow handler checks `Content<=250` before iterating arrows, then increments it for every arrow. It bypasses `PickUpItem`, does not check weight in this handler, and can overshoot the stated quiver threshold. This audit did not test that behavior live.
- Border Food and Armour handlers are not interchangeable with the current Actions/HUD `pickfood` and `pickarmour` dispatch. The latter intercepts most `pick*` actions and scans ground items generically within `range(1)`: it does not execute the border plant harvest/body pickup behavior or its one-per-equipment-slot limit. Preserve these distinctions in the catalog, or intentionally reconcile them with separate acceptance checks.

Pickup gates: [Item Procs.dm](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Code/Items/Item Procs.dm:44>). Modern dispatch: [Actions.dm](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Code/Remastered/Actions.dm:102>), [HUD.dm](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Code/Remastered/HUD.dm:154>).

## Right edge, top to bottom

The top-right corner belongs to this edge in the catalog. Every “drop” action below acts on the selected units’ carried items and unloads at each unit’s **current tile**. It does not walk to a stockpile, enqueue a stop, or resume a suspended collection task.

| Position | Label / `/obj/Hud` subtype | `icon_state` | Current effect | Key | Source |
|---|---|---|---|---|---|
| `19,19` | Equip equipment / `EquipArmor` | `ArmorE` | Attempt to equip every carried Equipment item, including weapons; ordinary equip restrictions apply. | — | [256](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Code/Login.dm:256>) |
| `19,18` | Unequip equipment / `RemoveArmor` | `ArmorUnE` | Attempt to unequip every Equipment item carried by selected units. | — | [265](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Code/Login.dm:265>) |
| `19,13` | Camera up / `ZUp` | `ZUp` | Move camera through Hell(4) → Underground(2) → Ground(1) → Sky(3). Does not move units. | `,` | [287](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Code/Login.dm:287>) |
| `19,12` | Camera down / `ZDown` | `ZDown` | Reverse that sequence: Sky(3) → Ground(1) → Underground(2) → Hell(4). | `.` | [274](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Code/Login.dm:274>) |
| `19,11` | Drop spare equipment here / `DropArmor` | `DropArmor` | Drop carried Equipment, including spare weapons; equipped items stay equipped (`DropItem(A,0)`). | — | [370](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Code/Login.dm:370>) |
| `19,10` | Drop all gems here / `DropGems` | `DropGems` | Drop all carried `/obj/Items/gems` from selected units. | — | [300](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Code/Login.dm:300>) |
| `19,9` | Drop all bones here / `DropBones` | `DropBones` | Drop all carried `/obj/Items/Bones`. | — | [309](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Code/Login.dm:309>) |
| `19,8` | Drop all wood here / `DropWood` | `DropWood` | Drop all carried `/obj/Items/woods/wood`. | — | [319](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Code/Login.dm:319>) |
| `19,7` | Drop all food/bodies here / `DropEdibles` | `DropEdibles` | Drop all Food items and carried Body mobs. | — | [328](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Code/Login.dm:328>) |
| `19,6` | Drop all ores here / `DropOres` | `DropOres` | Drop carried ores whose icon state is not `Stone`. | — | [340](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Code/Login.dm:340>) |
| `19,5` | Drop all stone here / `DropStone` | `Stone` | Drop all carried `/obj/Items/ores/stone`. Same icon state as the bottom pickup button. | — | [350](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Code/Login.dm:350>) |
| `19,4` | Drop all ingots here / `DropIngots` | `DropIngots` | Drop all carried `/obj/Items/Ingots`. | — | [360](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Code/Login.dm:360>) |
| `19,2` | Skin carried bodies / `TearSkin` | `TearSkin` | Try skinning carried corpses for eligible species/transforms, carnivores, or wielders of a Butcher Knife/Dagger. | — | [475](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Code/Login.dm:475>) |
| `19,1` | Butcher/devour carried bodies / `TearMeat` | `TearMeat` | Try tearing meat with species/tool gates. Devourers consume eligible non-critter corpses and gain egg content instead. | — | [459](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Code/Login.dm:459>) |

`DropItem` changes item location/weight using the normal inventory rules; equipment is only dropped when its suffix becomes `(Carrying)`. See [Item Procs.dm](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Code/Items/Item Procs.dm:61>). The separate Remastered **Drop off / Unload & resume** system travels to the chosen stockpile and accepts wood/stone according to its filter: [Delivery.dm](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Code/Remastered/Delivery.dm:38>).

## Decorative pieces and empty positions

These nine objects have an empty name and no `DblClick` handler. They draw the frame behind/around controls. The bottom corner icon-state names are reversed in the original source; retain the exact mapping if recreating the frame.

| Subtype | `icon_state` | `screen_loc` | Source |
|---|---|---|---|
| `Left` | `Left` | `1,2 to 1,18` | [95](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Code/Login.dm:95>) |
| `Right` | `Right` | `19,2 to 19,18` | [103](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Code/Login.dm:103>) |
| `Top` | `Top` | `2,19 to 18,19` | [111](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Code/Login.dm:111>) |
| `Top2` | `Top2` | `10,19` | [119](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Code/Login.dm:119>) |
| `Bottom` | `Bottom` | `2,1 to 18,1` | [136](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Code/Login.dm:136>) |
| `BottomLeft` | `BottomRight` | `1,1` | [144](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Code/Login.dm:144>) |
| `TopLeft` | `TopLeft` | `1,19` | [152](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Code/Login.dm:152>) |
| `TopRight` | `TopRight` | `19,19` | [160](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Code/Login.dm:160>) |
| `BottomRight` | `BottomLeft` | `19,1` | [168](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Code/Login.dm:168>) |

Unoccupied control positions are frame space: left rows 17–18; right rows 14–17 and 3; top columns 4–9 and 11–17; bottom columns 2–3 and 15–18. The bottom-left corner has only its decorative piece. Day is the sole non-action indicator; Top2 is decorative even though it shares Day’s position.

## Machine-readable catalog

[border-controls.json](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Interface/border-controls.json>) contains the 44 controls plus Day, excluding decorations. Rows are ordered top, left, bottom, right; the top-right Equip button belongs to the right edge. Each row supplies a stable ID, label, exact description, key, edge/position, DMI source/state, trusted HUD type, selected-unit requirement, and indicator flag. Source files are `Icons/HUD.dmi` and `Icons/Selection.dmi`.

IDs reuse existing action IDs where the HUD subtype matches, but catalog execution must call that retained border object's `DblClick` handler. Do not substitute the general Actions dispatcher for the food/equipment pickup cases described above. The current MSG/Warp overrides retain their safe input prompts. `needs_units` follows the existing action flags; camera/mode controls and Build are available before selection, even though useful building requires an eligible selected builder. The indicator has no runnable command.

## Optional hiding: proposed implementation, not yet implemented by this audit

The least disruptive approach is to keep the permanent `/obj/Hud` instances in `client.screen`, save each object's original `alpha` and `mouse_opacity`, then set `alpha=0` and `mouse_opacity=0` while hidden. Restore the saved values to show them. Restrict this to actual permanent border objects belonging to that client, not temporary synthetic HUD objects used by action dispatch.

Retaining the objects is important: the autodig mode handlers find DigAdd/DigSub by scanning `client.screen`, and day/night transitions find Day the same way. Removing them from that list would prevent those live icon-state updates while hidden; deleting/recreating them additionally resets mode visuals and requires reconstructing the client constructor chain. Keeping their identities and membership avoids that extra bookkeeping. `alpha=0` alone is not enough for the intended interaction: explicitly disable mouse hit-testing too, so an invisible border does not intercept map taps.

Do not blanket-hide or delete uppercase `/obj/HUD`, which contains transient construction/magic palettes. Do not invoke Stop, deselect, clear `Function`, reset `autodigging`/`adding`, or change task queues as a side effect of changing border visibility. The HTML control panel should retain a visible Show border toggle and an active-mode label/cancel action; shortcuts and catalog dispatch should continue to use the same procedures while the border is hidden. Apply a saved preference only after both Login and Selection border construction has completed, including reconnects.

Membership-dependent updates: [Selection.dm](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Code/Selection.dm:42>), [World.dm](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Code/World.dm:63>), [World.dm](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Code/World.dm:82>). Uppercase palette deletion: [Verbs.dm](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Code/Verbs.dm:286>), [QoL.dm](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Code/Remastered/QoL.dm:33>). Synthetic dispatch objects: [Actions.dm](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Code/Remastered/Actions.dm:109>).

Before shipping that option, check hide/show during active add/remove painting and a day/night change; confirm hidden cells accept map input, restored buttons show the current state, build palettes remain available, selection/queues remain identical, and reconnect reapplies the preference. Text-mode rendering should be checked separately if it is supported, since several icons also define fallback `text`. None of these UI checks were run during this read-only audit.


## Implemented labeled controls

The HUD now has a Controls drawer with all 44 actionable icons, the day/night indicator, original 32×32 artwork, descriptions and shortcuts. A separate Use button issues each command; reading labels does not send commands. Escape closes the drawer before affecting selection.

Hide/Show map border is saved with the player. It sets only the permanent `/obj/Hud` objects' alpha and mouse opacity, retaining them in `client.screen` so legacy dig and day/night updates still find them. Showing restores their exact original properties. Uppercase `/obj/HUD` build/magic palettes are unaffected.

The server resolves only trusted catalog IDs and invokes the existing border handler, preserving distinctions such as border Food's plant harvest and body pickup. There is no client-provided type/proc dispatch.

Verification: `tests/border-controls-checks.json` records 24 passing headless behavior assertions, including real Orc pickup/drop effects, saved visibility, membership, restored properties, camera levels and task/selection preservation. It explicitly excludes client-dependent dig callbacks. `tests/easy-orders-hud-checks.json` records 43 passing responsive/request checks, including all 45 catalog rows and all 47 generated PNGs. These focused checks do not certify every original gameplay effect or physical mobile input.

Native follow-up: all seven retained-border diagnostics pass in `tests/right-click-checks.json`, including original dig add/remove callbacks with a real client while hidden, an unaffected build palette and restoration. The report's overall result is inconclusive because the separate SetTarget submenu input was interrupted by native focus/position changes; that action is not claimed as verified.


## Command dock replacement

The current Remastered layout hides the permanent ring after the browser is
ready. Stop, Interact, Focus and Controls are in a labeled dock; all 44 commands
are grouped by purpose with search. The compact world status retains the
day/night indicator. Classic border Show/Hide remains saved and reversible.
See [COMMAND_DOCK.md](COMMAND_DOCK.md) for the migration and acceptance checklist.

Current focused verification supersedes the earlier drawer counts above:
33 headless game checks, 103 browser checks, and 16 connected native-client checks.
The native run was fully isolated and injected no keyboard or mouse input.
