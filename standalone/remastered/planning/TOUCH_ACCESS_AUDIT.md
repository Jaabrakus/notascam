# Touch access audit — 2026-10-17

Scope: current Remastered and shared native client. The fourth packaged app passed Human startup/save/reload. Its responsive HUD passes253 checks, and enlarged native dialogs pass92 checks at each of100%,150%,200% scale with screen-edge placement. This remains a route audit and desktop/browser verification, not a phone/tablet playtest. The historical144-check pre-layout result is superseded for layout but retained in the overnight evidence.

## Concrete remaining routes

| Priority | Gap | Existing behavior and minimal adaptation |
| --- | --- | --- |
| Fixed in source | Carried potion, sign, and tombstone choices | HUD inventory previously invoked `DblClick`, whose original implementation picks up/drops these objects. Drink, Write, and Inscribe now share their original `client/Click` behavior through `InventoryActions.dm`. Carrier, direct containment, selection, ownership, lifetime token, and item state are checked again after every prompt. Equipment/food retain their original `DblClick` route. |
| Fixed in source | Set a magic target | **Choose magic target** opens a list of visible living creatures using lifetime tokens. Friendly and self targets remain available for buffs. Opening, choosing and closing preserve work; only `MagicTarget` changes. The captured actor set, camera/view, target ownership/profile, containment and visibility are checked before assignment. The original native SetTarget uses the same validation. Original casts retain their own ranges and costs. |
| Fixed in source | Groups 1–9 | Separate Recall, Set and Add requests share a validated backend with the original Quick verb. Set/Add bind to immutable selected-unit tokens; recall filters current owned living membership. Work continues, Add tasks resets on recall, groups remain session-only, and the original repeat-to-center behavior is guarded against intervening selection changes. See [numbered groups](CONTROL_GROUPS.md). |
| Later | Clan tapestry mode | `PlaceTapestry` is mapped to `=` but absent from Actions and the border catalog. A labeled original-action wrapper can enter the same mode; map Click already performs original wall/range/clan checks. Keep Cancel accessible and avoid redirecting this mode into generic build painting. |
| Later | Player/social utilities | Ignore (`F`), Create a clan, clan members, shrines, and leader-only Invite/Boot lack modern Actions entries. The original native verb panel remains available through Details. Small wrappers should preserve existing availability and leader/verb-membership checks. |

The old bug-report/view shortcuts (`V`/`M`), file transfer (`F7`), configured
EVENT verb, and privileged GM/developer commands are also absent from the modern
catalog. They are not blockers for ordinary gathering/building, and should not
be promoted indiscriminately into player controls. Admin command access must
continue to depend on the original granted verbs/permissions.

The carried-item regression is recorded in `tests/inventory-routing-before-checks.json`:
all three original objects dropped on a tap, while the prior 20 identity checks
passed. The fixed `tests/ui-reference-audit-checks.json` passes **42/42** assertions
with stable source/runtime hashes and no errors. The tests use real Human,
LifePotion, Sign, and TombStone objects and the actual HUD dispatcher; only
modal choice/text replies are scripted. They verify original drink age/bottle
effects, Write/Inscribe, Drop weight/direction, exact queue preservation, and
changes to ownership, selection, carrier, item state, or item lifetime while
both prompts yield. Native dialog pointer input is outside that test's scope.
The extracted potion helper explicitly preserves the original client display
value in its two failure/death messages. This runtime centers no-argument
`view()` on `usr`, which remains the Player in both routes.

## Context menu and long press

The existing native client already populates a context popup from the objects
under a map point and filters the second menu through executable original verbs.
`MouseInputSystem.OnPress` opens it for `UIRightClick` when popup menus are enabled
and map `right-click=false`. This is why the restored right-click setting matters.

The original object row depended on hover to open its verb submenu. The October17
shared-client update adds matched press/release activation, with focus-loss and
cross-row cancellation, and fixes edge placement. Its final private native check
passes22 assertions; see [context audit](CONTEXT_TOUCH_AUDIT.md). No long-press
activation or physical touch test is implemented. Opening the menu on a phone
therefore remains a separate input task.

Two bounded options remain:

1. The explicit **Choose magic target** chooser now covers the immediate
   targeted-ability gap through the existing HUD request path. It does not
   require a native map-input change.
2. For general touch context access, add native press-and-hold activation
   using the existing popup and its now-tested object-row activation. Preserve
   original verb filtering/execution. Defer the ordinary left-click until a short release,
   cancel the hold on drag, and suppress the trailing click after opening the
   menu. Test placement, selection, queued work, stacked objects, and menu edge
   placement. Long-press activation requires a further engine input change and has not been implemented.

## Targeted-ability constraints

`Interact` already captures the selected actors and revalidates ownership after
choice prompts. Spells such as Damage Mind and Gargoyle projectiles look up the
actor's `MagicTarget` within their own ranges, while Dragon Breath uses that
same field. A target adapter must preserve those original range/resource checks.
Showing a target choice is not permission to execute a spell against a newly
selected actor or a replacement object after the original target disappears.
Reuse lifetime tokens and a captured actor set; reject changed selection/race,
ownership, containment, or target validity before committing a targeted choice.

Source locations: `Code/Remastered/HUD.dm`, `Code/Remastered/QoL.dm`,
`Code/Click.dm`, `Code/Turfs.dm`, `Code/Admin.dm`, `Code/Login.dm`,
`Code/1 - QuickProcs.dm`, `Code/Verbs.dm`, and `Code/Creatures/Interact.dm`.
Local engine source: `OpenDreamClient/Input/MouseInputSystem.cs` and
`OpenDreamClient/Input/ContextMenu/{ContextMenuItem,ContextMenuPopup,VerbMenuPopup}.xaml.cs`.

## Magic chooser validation

The chooser uses a temporary session token plus a target lifetime token. An old
close or pick cannot affect a newly opened chooser, and a deleted target cannot
be replaced by an engine-recycled object reference. It records the original
actor token strings: deleted mobs can leave null list slots, which ordinary
typed loops would skip. Every captured actor must still resolve to a living,
owned, listed and selected unit with the same race, subrace and mist state.

Only living creatures directly on visible turf are candidates. The observer
Player's `see_invisible` threshold is checked explicitly because this runtime's
`view()` includes hidden movables. Target ownership/race changes, containment,
leaving the view or level, and death all invalidate the old choice. Camera
movement or a changed view size require reopening. New arrivals are not added
to an already-open chooser. Opening cancels existing placement; opening a new
original build/ability menu closes the chooser. No chooser operation casts,
starts an attack, changes destination, spends mana or pauses task objects.

`tools/check_magic_target.py` uses real Human constructors and the actual HUD
request and native SetTarget paths in a private copied world. The camera-size
case substitutes only the size observation because a clientless world cannot
change `world.view` in this runtime. The other actor, visibility, ownership,
containment and reference-reuse changes occur on actual objects. Final report:
the41-check magic entry in `tests/installed-regressions-20261017.json`. No native gesture
or spell execution is simulated by this test.
