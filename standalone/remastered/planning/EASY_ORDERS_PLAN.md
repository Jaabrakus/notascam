# Easy clicks and independent unit work

Started October 16, 2026; controls and scope clarified October 17. Implementation is active in **Dungeon Master Remastered**, the current project at `standalone/remastered`. The parent folder name does not change the target: all new gameplay, HUD and sprite-pipeline work belongs to Remastered.

Finite unit queues, delivery detours, one filtered stockpile (wood, stone, mixed, or opt-in mining supplies), and bounded Woodcutter/Miner/Hauler roles are implemented. The recorded original-army two-tree check passes 22 assertions using the original starting three-Human army: one Human chops two natural trees while deselected, deposits seven logs and carries one, leaving four seeds and the other two Humans alone. Selection/movement has a separate 23-check original-army trace. Responsive HUD checks now pass 253 assertions at widths of 320, 390 and 768 pixels. Earlier simplified-unit fixtures remain useful isolated regressions, but the real-world checks establish the original-unit behavior. Native automation uses internal client hit-testing/callbacks and real WebKit dispatch; this does not certify physical phone/tablet input or a mobile export. Exact source/runtime and packaged-build status are in the overnight ledger.

This plan follows the [action inventory](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/ACTION_INTERACTION_INVENTORY.md>). The baseline sections below describe the earlier packaged version; the implementation checklist records current progress. Earlier regression evidence after the deselection and shared sprite-frame fix: [logic report](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/tests/easy-orders-facing-fix-checks.json>) and [tested source hashes](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/tests/easy-orders-facing-fix-sources.json>).

## Using the implemented controls

For the current app, accepted package, private candidates and rollback status, use [the morning handoff](MORNING_2026-10-17.md) and [the overnight ledger](OVERNIGHT_2026-10-17.md). This plan describes behavior and scoped evidence; a passing component test does not by itself mean a candidate is packaged.

**Select a worker → give a task → Deselect. The task belongs to the worker and continues.**

| Control | Current behavior |
| --- | --- |
| Select an owned unit or its card | Shows its work. Selecting another unit leaves existing work running and resets Add tasks. Add units / Shift+click adds or removes selection. |
| Tap/click a tree, mineable tile, loose resource or loose equipment | Assigns one eligible selected worker. It approaches and uses original work/pickup rules. Equipment is carried, not automatically equipped by pickup. |
| Tap/click clear ground | Moves the eligible selected group. Select one worker when you want precise control over its task list. |
| Do now | Replaces the receiving worker's finite tasks with the new task. |
| Add tasks / Shift+command | Appends targets in order, up to 32 pending tasks per worker. Use each pending task's Remove button to remove only that task. |
| Deselect / Space while the map has focus | Leaves assigned work running; resets Add units and Add tasks and cancels placement. It does not issue Stop. |
| Pause / Resume on a unit card | Retains tasks and suspends/restarts execution. Blocked work explains what must change before retrying. |
| Stop | Clears direct active/pending tasks and delivery, and pauses role/production execution. Retained crafting attempts can be cancelled separately in Work. It does not dump cargo. |
| Work → Stockpile | Sets the one current drop-off on open ground at the selected unit or view centre. Choose Wood, Stone, Wood + stone, or Mining supplies. |
| Drop off | Uses the assigned stockpile: Add tasks appends delivery; Do now replaces finite tasks. Selected workers must be on its level. This differs from original Drop commands, which drop items here. |
| Unload & resume / Auto unload | Unload & resume temporarily delivers accepted cargo, preserving interrupted tasks. Auto unload is a per-unit option for capacity and role delivery. Tools, finished equipment, food and seeds stay carried. |
| Woodcutter / Miner / Hauler | Assignment replaces selected workers' current direct tasks, enables Auto unload and captures a six-tile work area. Subsequent direct tasks take priority over a running role; Stop leaves that role paused until Resume. |
| Workshop, carried item or ability | Tap a workshop; use Skills, needs & inventory for carried items; use Interact/Controls for abilities. Some original ground-object menus still require double-click. Some direct actions pause work; check the card for Resume. |

Nearby help applies to covered attack routes, not every health loss; see [the defense route inventory](DEFENSE_REMAINING_SCOPE.md). Its source/candidate status is separate from package acceptance. Queue targets and temporary delivery/defense state reset on restart; [save scope](PERSISTENCE_SCOPE.md) distinguishes this from saved unit/configuration data.

These are current desktop-game controls with a responsive HUD. Physical phone/tablet input, touch map panning and a mobile build remain unverified.

## Baseline before implementation

| Capability | Packaged-source finding | What still needs work |
| --- | --- | --- |
| Work after deselection | Deselect removes the selection entry and marker; it does not clear the unit's destination. WalkTo continues independently of selection. | Verify the actual click → chop → deselect → finish flow in the packaged app. |
| Chop and mine | A unit repeatedly moves toward its target; collision performs tool/race-gated chopping or mining until the terrain changes. | Clear targeting feedback, tool errors and obstacle handling. |
| Multiple marked work targets | Existing autodig assigns markers to individual units and searches for their markers in local view. Markable terrain includes trees and mineable tiles. | This is not a general ordered task list or a shared team job pool. |
| Automatic continuation | Autodig clears completed target markers and can take another visible marker without selection. Guard/patrol also run independently. | Explicit priority between a direct order, autodig, guard and rest. |
| Collection | Individual and bulk pickup handlers already implement much of the inventory behavior. | An explicit sequence that approaches an item, collects it, then moves to the next task; capacity feedback. |
| General order queue | A draft Orders.dm exists in the working directory, with per-unit active/pending orders. | It is not verified packaged functionality and must be revised against the interaction inventory before integration. |
| Hauling / stockpile | Draft Settlement.dm stores one stockpile location per player, with wood/stone/food hauling roles and local item reservations. | It is not a full-inventory harvesting loop, multiple categorized stockpiles, or a verified unload-and-resume queue. |

Source anchors: [Deselect](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/dist/Dungeon Master Remastered/Source/game/Code/Mobs.dm:18>), [WalkTo](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/dist/Dungeon Master Remastered/Source/game/Code/Creatures/Mob Procs.dm:24>), [chop/mine](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/dist/Dungeon Master Remastered/Source/game/Code/Creatures/Bump.dm:94>), [autodig loop](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/dist/Dungeon Master Remastered/Source/game/Code/Vars.dm:349>), [marker assignment](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/dist/Dungeon Master Remastered/Source/game/Code/Building/Building.dm:268>), [draft orders](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Code/Remastered/Orders.dm:1>).

These are source findings, not a new live playtest. Existing normal clicks replace the current destination. Autodig chooses through view iteration, not the user's explicit click order; markers beyond local view are not automatically planned as a distant route. Chopping drops wood and seeds on the ground; it does not itself collect them into inventory.

The existing Stop command only clears the current destination/combat target; active autodig can assign its destination again on the next tick. Turning autodig off also clears its target and deletes that unit's markers. The proposed Stop/Pause controls need deliberate semantics rather than just relabeling these existing commands. See [StopAll](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/dist/Dungeon Master Remastered/Source/game/Code/Verbs.dm:254>) and [autodig toggle](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/dist/Dungeon Master Remastered/Source/game/Code/Login.dm:243>).

## Original design targets

The following design tables and example are the original plan, not an additional completion checklist. The implemented-control table above and checked milestones below are authoritative. Touch panning, a general object-choice panel, multiple drop-offs and a separate resume-role preference remain future work.

**Selection chooses who receives the next command. Orders belong to the unit after they are given.**

| Player input | Proposed result |
| --- | --- |
| Tap/click an owned unit | Select it; show current task and pending task count. Selecting another unit leaves the first unit working. |
| Tap a tree with an eligible worker selected | Start Chop & collect: approach, chop, collect the resulting wood within capacity. Show missing axe/race restriction immediately. |
| Tap mineable terrain | Start Dig & collect, using the existing mining effects and resource rules. |
| Tap a loose ordinary resource | Approach and collect that target. Special items retain their context choices. |
| Tap open ground | Move there. In normal mode this replaces that unit's task list and confirms the new destination visually. |
| Turn on Add tasks, then tap targets | Append tasks in tap order to the selected unit's list. On desktop, Shift+command is the shortcut. |
| Clear selection / select another unit | Work continues. Close the previous selection's Add tasks mode so it cannot accidentally apply to another unit. |
| Tap a task in the unit's list | Inspect/remove a pending task. Removing one task does not erase the rest. |
| Add tasks → Drop off | Insert a delivery stop at the currently assigned stockpile, then continue with the remaining tasks. Choosing between multiple stockpiles is future work. |
| Unload now | Temporarily deliver allowed cargo to the assigned stockpile, then resume the interrupted task and queue. Label this “Unload & resume.” |
| Pause work / Resume | Keep the list while temporarily stopping execution. |
| Stop | Stop active work and clear pending tasks. This must suppress guard/autodig immediately reissuing that work. |

Show the action at the target with a short label or icon and acknowledgement. Normal mode should say “Do now”; queue mode should say “Add tasks” and remain visibly active. Empty-ground taps issue movement when a unit is selected, so deselection needs its own clear control. Desired future touch behavior: dragging pans the camera, with selection-area painting and build painting in explicit modes. Touch map panning is not implemented or device-verified. Mouse box selection remains the desktop shortcut.

Owned units remain selection targets. The design goal is a clear choice panel where objects have several meaningful actions. Current workshop taps and carried-item Inventory routes expose original menus; doors, cages and other ground objects do not yet have a universal one-tap panel. Finite automation covers move/chop/dig/ordinary-pickup and eligible loose-equipment pickup; the latter carries equipment without equipping it.

## Example the first implementation must support

1. Select Worker A and tap Tree 1. It starts chopping.
2. Enable Add tasks, then tap Tree 2, a loose stone and two mineable tiles.
3. The unit strip reads “Chopping — 4 tasks queued,” with numbered target markers.
4. Select Worker B and give it another job. Worker A keeps executing its list.
5. Reselect Worker A to see its progress, remove a pending task, pause or stop.

Expected list:

**Chop Tree 1 + collect wood → Chop Tree 2 + collect wood → Drop off wood → Collect stone → Dig tile 1 + collect → Dig tile 2 + collect → Drop off stone.**

Collection after harvesting is an intentional convenience addition. Scope it to the harvest's outputs; do not sweep up every unrelated item, seed, weapon or corpse nearby. If seeds or byproducts are included, show that policy explicitly. Keep the original resource yields and carrying limits.

## Rules that make the queue predictable

- **One unit, one execution owner.** Direct orders must not fight with autodig, guard or future worker jobs over the same destination. Preserve their configuration, but only one controller issues movement at a time.
- **Commands capture their actor.** The queued unit remains the actor after the player changes selection. Legacy menus that use the current Selected list cannot simply be invoked later as if nothing changed.
- **Append versus replace is explicit.** Add tasks appends; Do now replaces; deselect changes neither. Return to Do now when changing selection, without touching previously assigned queues.
- **Recheck requirements when the job starts.** A unit can lose a tool, become injured, change owner or fill its inventory while a task waits. A queue-time check alone is insufficient.
- **Full inventory uses an explicit delivery policy.** With Auto unload enabled and an assigned compatible stockpile, temporarily unload and resume the unfinished collection/work task. Without a valid drop-off, pause with a reason. Keep the pending queue intact and never invent a destination or spill equipment to make room.
- **Unavailable targets have visible outcomes.** Already-collected item or already-cleared tile: mark skipped with a reason. Inaccessible route or missing tool: pause with a reason and keep pending work editable. No silent endless retries.
- **Sleep and injury are visible interruptions.** Keep pending tasks during ordinary rest; resume only when eligible. Death/ownership transfer must invalidate old owner's commands.
- **Completion is an effect, not a timer.** Chopping ends when the tree is cleared; digging when the target terrain is cleared; collection when ownership/location of the item changes; movement when the unit reaches the destination. Nearby-but-stuck does not count as progress.
- **Long-running jobs need an end condition.** Fishing/guard are not part of the first finite queue until a quantity, duration or “until stopped” rule is explicit.
- **Group work comes after single-unit reliability.** Then distribute finite work among eligible selected units rather than copying every pickup target to every unit. Keep shared reservations and per-unit feedback visible.
- **Save/load is a separate acceptance case.** Do not promise queued world targets survive restart until their identity can be safely restored. Current draft order fields are temporary.

## Resource delivery and simple unit roles

Interpret “mini agents” as game units with a role, a bounded work area, a task list, a cargo policy and a readable status. Use shared local game logic for decisions; each unit holds its own state. The player sees familiar roles rather than needing to configure a separate model for every unit.

### Delivery is a task, separate from Stop

Three delivery routes share the same deposit behavior:

1. **Queued Drop off:** walk to the chosen stockpile, unload matching cargo, then advance to the next queued task.
2. **Unload & resume:** remember the active task and remaining queue, deliver now, then return to unfinished work.
3. **Auto unload:** when the next allowed resource will not fit, run Unload & resume automatically if a stockpile is assigned. Also deliver a remaining partial load when an autonomous work batch finishes.

Stop cancels active/pending work and pauses the role. It does not throw items onto the ground or automatically start a delivery. Pause retains tasks. Deselect leaves all work running. Keep these separate in both labels and behavior.

Use a reachable ground stockpile first, with actual world items and existing pickup/drop rules. Container and wagon destinations can be added after their capacity and permission rules are handled. No teleporting resources, unlimited hidden inventory or resource-count-only deposit in place of real items.

### Stockpile categories

| Category | Accepts by default | Handling |
| --- | --- | --- |
| Wood | Logs/ordinary wood resources | Initial delivery category. |
| Stone | Ordinary loose stone | Initial delivery category; ores remain distinguishable. |
| Ores and metal | Raw ores and ingots, separately selectable | Future refinement; preserve their item/material identity. |
| Food | Eligible food cargo | Preserve the unit's configured dietary supply; food hauling is opt-in. |
| Craft materials | Seeds, skins, bones and similar resources, individually enabled | Never infer that every carried item is disposable cargo. |
| Mixed resources | Explicitly enabled resource categories | Convenient first drop zone with a visible accepted-items list. |

A stockpile has an owner, location/area and accepted categories. A worker has a primary drop-off and allowed cargo types; a compatible fallback must be deliberately configured. First implementation can use one marked ground tile accepting wood and stone. Multiple category zones are a later increment using the same interface.

Tools, weapons, armour, ammunition, quest/special items and reserved food stay with the unit unless explicitly included in a manual transfer. Protect carried spare tools too, not only equipped items. Deposited goods must be excluded from ordinary loose-resource gathering so a hauler does not repeatedly pick them back up.

### Roles

| Role | Repeating behavior within assigned work area | Initial scope |
| --- | --- | --- |
| Manual | Execute only the explicit task queue; optional auto unload | First pass |
| Woodcutter | Choose a designated tree → chop → collect wood → unload when needed → continue | First role increment |
| Miner | Choose a designated dig target → mine → collect allowed resources → unload → continue | First role increment |
| Hauler | Collect eligible loose resources → deliver to a compatible stockpile → repeat | First role increment |
| Builder / crafter | Fetch permitted materials → perform an assigned build/recipe → report missing requirements | Later; requires recipe/build contracts |
| Farmer | Tend designated farming tasks and move eligible harvests to food storage | Later; preserve growth and diet rules |
| Guard | Use configured guard/patrol behavior and report threats | Existing foundation; integrate with the same control rules |

The role is a reusable behavior preset. Race, tools, injuries, skills, ownership and capacity still decide what a particular unit can actually do. Assigning Miner must not grant mining abilities or tools. Work remains inside designated targets/area; a role should not independently harvest every tree on the map.

Shared worker states: **Idle → Find work → Travel → Work → Collect → Deliver → Resume**, with visible **Paused / Blocked** states. Not every role needs every state. Reserve a task/item before approaching it so two workers do not both claim the same resource; release reservations after completion, cancellation, death or ownership change.

Only one controller moves a unit at a time. Manual tasks temporarily take priority over an already-running role. A separate “Resume role after tasks” preference is still future work; the current card does not offer that switch. A capacity-triggered delivery is part of the active task, with a return point and remaining cargo recorded. Rest/injury interruptions preserve pending work; Stop prevents all automatic controllers from restarting it. Death and ownership transfer invalidate the previous owner's tasks and reservations.

### Minimal HUD

The default unit card can show **Role · Current task · Carry load · Queued count**. Keep ordinary target taps as the primary commands. An expandable Work panel contains **Drop-off**, **Auto unload**, **Add tasks** and **Pause/Stop**; advanced cargo filters and work-area settings stay behind details.

Example status: **Woodcutter · Delivering wood · Returning to Tree 3 afterward**. A blocked delivery should state the actual reason: “No drop-off assigned,” “Drop-off unreachable,” or “Stockpile does not accept stone.” A blocked/cancelled delivery must leave both cargo and queued work accounted for.

### Earlier draft hauling limitations

The earlier Settlement draft had loose-item wood/stone/food jobs around one stockpile, without harvesting roles or delivery detours. The current implementation reuses its checked inventory procedures. [Delivery.dm](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Code/Remastered/Delivery.dm>) now provides wood/stone and opt-in Mining supplies filters, retained-task delivery and the three bounded roles. Multiple storage zones remain open.

## Earlier draft issues addressed

The initial adapter needed these corrections. Current finite queues use explicit actors, original collision/inventory effects, captured harvest output and visible blocked states. Keep these findings as regression risks:

- The draft generic Use called DblClick despite important Click-only paths and handlers dependent on current selection. Finite queues now cover unambiguous resource/movement targets and eligible loose-equipment pickup; original context handlers remain available.
- The draft harvest completion swept up nearby items. Current collection captures only new eligible harvest output.
- The draft refreshed progress from proximity alone. Current harvesting checks changing target health and rechecks tools.
- Broad creature-to-Attack classification was removed from finite queues; original creature/context interactions keep their own rules.
- Tool checks, automatic controllers, sleeping behavior and transient queue persistence now have focused regressions.

Use the underlying movement, collision, inventory and resource procedures. Review the adapter that connects these procedures to input and task state; a new HUD alone does not make that adapter correct.

## First milestone checklist

- [x] Observe baseline chopping continuing after deselection and switching to another unit.
- [x] Make select → target → acknowledgement work with one click/tap, including useful blocked reasons.
- [x] Implement per-unit finite move/chop/dig/collect queues using explicit actor/target identity.
- [x] Add Do now / Add tasks, Clear selection, task count/list and distinct Stop behavior.
- [x] Keep a touch-sized Deselect button visible while scrolling; clear input modes without cancelling work. Space shares that behavior; Escape is supported inside the HUD, with editable controls excluded.
- [x] Verify three trees and two dig tiles finish in assigned order while the unit is deselected.
- [x] Verify switching between two units leaves their queues independent.
- [x] Verify normal order replacement, appending, removing one pending task, pause/resume and Stop.
- [x] Verify correct harvest yields and collection; no unrelated items taken and no carrying-limit bypass.
- [x] Verify missing/lost tools, full inventory, inaccessible routes, removed targets, sleep, death and ownership changes.
- [x] Verify existing autodig and guard cannot overwrite manual queued work or restart it after Stop.
- [x] Verify desktop AppKit clicks, embedded WebKit Add tasks and Space deselection in the earlier seven-check simplified-worker two-tree fixture (`tests/easy-orders-mouse-checks.json`). This is desktop input evidence on that snapshot, not production-unit appearance or physical phone input.
- [x] Verify single-click selection and the original selection marker on real Human units in the packaged full world.
- [x] Complete an uncontested full-world single-unit movement recording. October 17 private client callback/hit-test/network proof passes 23 checks with the original starting Human army; see [FULL_WORLD_SELECTION_CHECK.md](FULL_WORLD_SELECTION_CHECK.md). Physical OS/touch input remains a separate scope.
- [x] Verify touch DOM requests and responsive layout at 320/390/768 widths.
- [ ] Verify physical phone/tablet map input and touch panning in a mobile runtime.
- [x] Record save/load behavior and compare packaged game/HUD hashes with current source. Fresh full-game startup/save/reload retains three Human units with zero runtime errors; reports record the tested client version.

## Delivery and role increments

- [x] Add a ground stockpile with explicit wood/stone filters and a Drop off task inside the per-unit queue.
- [x] Verify chop → collect → drop off → next target while deselected; only allowed cargo moves.
- [x] Add Unload & resume with active-task identity, remaining output and pending queue preserved.
- [x] Add opt-in Auto unload when the next resource will not fit; return for the unfinished collection before advancing.
- [x] Verify partial deliveries, cleared/relocated/blocked drop-offs and resources too heavy even after unloading; retain cargo and work without an endless unload loop.
- [x] Keep wood/stone as the default delivery policy; add an explicit Mining supplies filter for stone, ores, sand, uncut gems and bones. Verify tools, finished gear, cut gems, food and seeds remain excluded.65 focused checks and24 native original-world mining checks pass.
- [x] Exclude stockpile contents from loose-item gathering; verify two haulers cannot duplicate or repeatedly shuttle the same item.
- [x] Add Woodcutter, Miner and Hauler presets with explicit work bounds and one active controller per unit.
- [x] Verify manual override, role continuation, Stop, sleep, actual death and ownership transfer suspend/release work and reservations. A separate optional “Resume role after tasks” preference remains open.
- [ ] Add multiple filtered stockpiles only after one destination works reliably; validate permissions and changed filters at delivery time.
- [x] Verify persistence of role/drop-off configuration separately from active queue/target persistence.

Implement in order: independent finite queues → queued delivery → automatic delivery/resume → role presets → group distribution and additional roles. Each increment has observable outcomes before expanding the automation.


## Current scope and remaining increments

- A worker's six-tile work area is captured when its role is assigned and can be recentered explicitly. Miners exclude built walls. Direct resource commands go to one selected worker; group work distribution is a later increment.
- One player-owned ground stockpile accepts Wood, Stone, Mixed (wood+stone), or opt-in Mining supplies. Mining supplies includes original ores, sand, uncut gems and bones as well as stone; cut gems, tools, weapons, food and seeds remain carried. No new material yields or carrying capacity are granted.
- Harvest collection includes only new eligible output from the original collision action. Woodcutters collect wood; miners also retain eligible ores/gems/bones. Seeds and unrelated nearby items are not swept up.
- Manual tasks temporarily take priority over a running role. Stop pauses the role as well as clearing finite tasks; Resume restarts it. A separate “Resume role after tasks” preference is still a future control.
- Active/pending targets and delivery detours are temporary. Role, work-area, auto-unload and stockpile/filter configuration are saved; restart never promises to restore a live world-target queue.
- Physical phone/tablet play, touch map panning, mobile packaging, multiple stockpiles, workshop/container transfers, additional roles and shared team task distribution remain separate increments.
- [Sprite pipeline](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/planning/SPRITE_PIPELINE.md>): original assets are exported to deterministic atlases with state/direction/timing/provenance metadata. The current renderer still consumes its original DMI resources.

Native testing exposed a player/worker identity mismatch in legacy terrain collision. Queued movement now runs terrain checks as its actual worker. The route search also avoids Chasm/Sky for grounded units and respects forbidden GoodGrass traits; five terrain regressions verify those cases.

Historical full-world input attempt: `tests/full-game-selection-checks.json` and its screenshots remain preserved. Its single-selection observation passed, but the overall run did not: movement was inconclusive and test-wrapper shutdown interrupted its save check. The later 23-check [original-army selection recording](FULL_WORLD_SELECTION_CHECK.md) supersedes it for selection/movement evidence; passing packaged lifecycle reports separately establish their scoped save/reload behavior. Automated foreground inputs must stop before handing the app to the player. Simplified queue fixtures cannot establish production-unit appearance.


## Border-control clarity increment

- [x] Catalog all 44 original buttons, the day/night indicator and decorative frame pieces in [BORDER_CONTROLS.md](BORDER_CONTROLS.md).
- [x] Add a touch-sized Controls drawer with original glyphs, labels, shortcuts, descriptions, availability reasons and separate Use buttons. Reading a label does not issue an order.
- [x] Add saved Hide/Show map border; keep original objects in client.screen so autodig marking and day/night updates continue. Build/magic palettes remain separate.
- [x] Route labeled commands through the original border handlers. Nearby pickup/plant harvest/equipment rules remain distinct from modern ground-resource commands; drop buttons unload here, while Drop off travels to the stockpile.
- [x] Export and package 47 exact original glyphs from the sprite atlas.
- [x] Verify the actual 45-row catalog and all 47 thumbnails in the responsive HUD test; 43 DOM/input checks pass at 320/390/768 widths.
- [x] Native-client checks confirm retained screen membership, hidden add/remove dig icon updates, unaffected build palettes and exact restoration. Seven diagnostics pass in `tests/right-click-checks.json`; that report separately leaves context-verb execution inconclusive.

The catalog is trusted local data, and requests accept only a catalog ID. Unknown IDs and read-only indicators cannot execute arbitrary HUD types. Physical phone map input remains a separate milestone.

## Input and idle-sprite fixes

- [x] Restore original right-click object menus (`map.right-click=false`); left/tap remains the primary order input. Native popup display and unchanged selection/task state are recorded in `tests/right-click-verified-observations.json`.
- [x] Preserve movement-only DMI metadata through generated icons and play those frames only during movement.
- [x] Verify real Human body/equipment animation through walking, idle, teleport and layer change; stationary Fire keeps animating. `tests/animation-lifecycle-checks.json`: 26 checks, 280 native samples, zero runtime errors.
- [x] Retain original sprite files and save data without migration. Shared renderer/runtime changes live in the Classic engine infrastructure; Classic gameplay source is untouched.
- [x] Verify SetTarget through the original context submenu, including click/release without hover, focus-loss cancellation and edge placement. The final private native context check passes 22 assertions; see CONTEXT_TOUCH_AUDIT.md.
- [ ] Verify the remaining original context-command matrix and physical long-press activation.
- [x] Resolve duplicate same-name idle/movement DMI variants (Deer / Hell Forged Sword). October 17 installed engine preserves both variants; 81 variant assertions and a 40-check real-client trace verify this increment. See `../replica/engine/MOVEMENT_ANIMATION.md` and the overnight report for exact hashes and remaining renderer limits.

Historical pre-overnight package milestone: the personal Remastered app was packaged and opened after backing up the then-existing three-Orc save. That installed-runtime snapshot passed 72 Easy Orders checks and 30 real-unit facing checks (`tests/animation-regression-hashes.json`). Its native normal startup reported no errors or missing browser resources and all 45 active border thumbnails loaded; its package hashes matched the tested client/runtime (`tests/border-animation-package.json`, `tests/border-animation-normal-launch.json`). The archived dist release remains unchanged.

## Overnight continuation and remaining priorities

Current package/build/private-candidate status lives in [MORNING_2026-10-17.md](MORNING_2026-10-17.md) and the versioned [OVERNIGHT_2026-10-17.md](OVERNIGHT_2026-10-17.md). They record exact source/runtime hashes, scoped acceptance, failed/interrupted attempts and rollback checkpoints. This plan does not duplicate a changing integration number.

Historical seventh milestone: private Orc startup/save/reload and read-only native HUD captures passed, with fresh acknowledgments and unchanged normal save. It included compact Controls, stable Work buttons, Mining supplies delivery, commit-only Carpentry/Masonry/Smelter/cooking/altar/Melter handoffs, retained quick-build queues, selected-action/direct Work intent guards, paused-production Resume and helper policy, original equipment/hair portraits, the magic chooser and larger native dialogs. Its combined gameplay acceptance passed 2,816 across 30 suites plus 144 recursive-combat checks; its exact HTML passed 253 broad HUD and 47 direct Work checks. Native Work 127 and Melter 170 were separate private-callback proofs. The earlier frozen third app passed all 13 ordinary starting races; two-player isolation/reload separately passed 97/102 on their recorded snapshots. These remain versioned evidence, not final-build or general multiplayer certification.

Prioritize the remaining work by its effect on play:

1. **Physical input and a mobile runtime.** Verify taps, panning without accidental orders, explicit selection/placement modes, cancellation, keyboard/dialog focus, orientation and screen edges on actual devices. Responsive DOM/native callbacks do not certify phone input. Native context rows retain their original dimensions; larger choice dialogs do not make every native control touch-sized. See [context-input scope](CONTEXT_TOUCH_AUDIT.md).
2. **Clear target-specific object choices.** Preserve original availability and ownership while making remaining ground-object actions discoverable. Doors/cages and older double-click menus need deliberate rules; right-click does not expose a universal interaction menu. Avoid changing default taps until original callbacks and stale-target rejection are verified.
3. **Remaining menu handoffs.** Follow [ACTION_HANDOFF_COVERAGE.md](ACTION_HANDOFF_COVERAGE.md) for installed, private and unmigrated families. Reproduce cancellation or changed-actor failures one family at a time, keeping original costs, ranges and effects. Do not infer full recipe coverage from focused tests.
4. **Settlement persistence.** Built structures, changed terrain and dropped stockpile cargo need a dedicated world-save design and two-launch verification. Existing unit-save checks do not cover them. Finite target queues intentionally reset; see [PERSISTENCE_SCOPE.md](PERSISTENCE_SCOPE.md).
5. **Broader automation after those boundaries are clear.** Multiple filtered stockpiles, shared team task allocation, additional roles and an explicit resume-role preference remain separate features. Current resource taps allocate one worker; ground movement commands the selected group. Keep this distinction visible rather than promising automatic team distribution.

Covered attack notifications have their own [remaining-route inventory](DEFENSE_REMAINING_SCOPE.md). It separates installed source, accepted private candidates and unverified paths; no new defense route is declared shipped by this plan. Visual polish can continue without obscuring these functional limits or changing original art.
