# Original build and ability menus in the Remastered HUD

Updated 2026-10-17. This work belongs to `standalone/remastered`, the active game.
Classic game rules, sprites and recipes remain the reference.

## Playing

Select your unit, then use the original build or ability command. Building is
available through **Build & terrain** in the command dock, through **More
buildings & race abilities** in Work, and through the original B shortcut.
The HUD opens larger choices for the menu the game actually created.

For Illithid powers, use **Mental abilities** beside More buildings in Work,
or **Illithid mental abilities** in All commands. The original F6 shortcut also
remains available. Every selected unit must be a living Illithid you control,
outside mist form; the touch controls explain an ineligible selection. This
opens the original mental-powers menu and preserves its original spell checks.

- Each choice uses its original name and icon. One tap invokes that option.
- Submenus replace the choices in the same panel. Some options still open an
  original game choice dialog; others enter a placement mode on the map.
- **Close** closes the current menu and cancels placement. Assigned tasks remain
  intact. Escape while this HUD panel has focus does the same, before any
  deselection shortcut is considered.
- If the selected units or their race change, the old choices become unavailable
  and explain why. Close the panel and use the original command again for the
  current selection. Building and mental abilities keep their separate original
  commands; there is no synthetic combined race menu.
- To use the original map controls, close the panel and enable **Classic border**
  in Controls. Reopening a menu then retains its original map buttons too.

The panel has touch-sized buttons, internal scrolling, and a Close button that
stays visible. This is responsive desktop HUD work, not a mobile application or
a replacement for every native game dialog.

## How it stays faithful

`Code/Remastered/Palette.dm` enumerates the current named `/obj/HUD` objects in
the player's `client.screen`. Unpositioned racial options, decorative frames,
and letter sprites are not commands. Repeated copies of the same type/icon/state
produce one choice; the original callback still operates on the selection.

Requests contain an opaque menu token. The server resolves it against the
current screen and checks the captured actors, current ownership, unit-list
membership, living state, race, subrace, and mist state before calling that
object's original `DblClick()`. Tokens are assigned to each object's lifetime
within the server session; they are not persisted in saves or recycled atom
references. A deleted menu's button cannot become a new
submenu action when the engine reuses an atom reference. Repeated taps on the
same live option within five ticks are suppressed.

The adapter does not invent material costs or new recipes. It preserves original
menus, resource checks, placement handlers, racial options and game dialogs.
Opening, navigating, or closing a menu does not clear Easy Orders. Individual
original commands retain their original gameplay effects.

The original menu objects remain in `client.screen` while the modern replacement
is ready. Their alpha and mouse opacity are saved and temporarily disabled in
the clean layout, then restored for Classic border or an unready HUD. Keeping
the objects alive preserves original submenu and Close behavior. The HUD tick
restores the original menu before returning for an unready browser.

## Live unit controls delivered alongside the menu

- Task and inventory controls retain their DOM identity by their opaque token.
  Queue progress updates the pending task's ordinal without retargeting its
  Remove button to a neighboring task.
- If a focused task disappears, focus moves to descriptive task text. A removed
  inventory item returns focus to its unit's inventory summary. Unrelated
  updates preserve open details, focus, and scroll position.
- Paused status is not duplicated. Role names, empty queues, empty inventories,
  and empty selection explain their state.
- Delivery buttons explain a missing selection, missing stockpile, or different
  level. A mixed group can deliver when at least one selected unit is on the
  stockpile level; the text explains that only those units are eligible.
  The server still decides cargo and route validity.
- Auto unload explicitly describes ordinary wood and stone and the stockpile's
  filter. Food, tools and equipment are not silently deposited.
- Missing, loading or failed unit portraits show a fixed initials frame until a
  valid image loads. A portrait failure does not replace the unit card or alter
  selection controls.
- Carried potions, signs and tombstones now open their original Drink, Write,
  or Inscribe choices instead of falling through to their pickup/drop handler.
  Cancel and Inspect keep work running. A committed change pauses only that
  carrier while preserving its task objects; the other selected units continue.
  Ownership, selection, carrier, lifetime identity and item state are rechecked
  after each choice/text prompt. Equipment and food retain their original menus.
  Potion effects retain `usr` as the Player; two original client-context
  failure/death messages explicitly use the client display value.
- **Choose magic target** lists visible living creatures, including friendly
  and self targets. Choosing only assigns the original magic-target field;
  tasks, movement, attacks and spell resources stay untouched. A changed
  selection, camera, target identity or visibility requires a fresh choice.
  Original ability commands continue to perform their own casting checks.

## Verification and limits

`tools/check_easy_orders_hud.py` checks browser rendering and request contracts,
including token identity, submenu replacement, disabled choices, focus recovery,
Close/Escape, image failures and layouts at 320, 390 and 768 pixels. The final
complete pre-compact-layout run passed **144/144** checks in
`tests/hud-full-precompact-checks.json`,
with stable source files and no browser errors. This run includes portrait
loading/failure recovery and the mental-abilities touch opener, alongside the
original command-dock, queue, inventory, defense, and palette tests.

Earlier incremental reports remain in `tests/hud-palette-controls-checks.json`,
`tests/hud-portrait-checks.json`, and `tests/hud-mental-action-checks.json`.
The focused image or mental checks can be run with `--portraits-only` or
`--mental-only`. Browser tests capture requests; they do not simulate game effects.

`tools/check_palette_native.py` and `tests/palette_probe.dm` exercise original
Human, Orc, Spider, Devourer and Illithid constructors and callbacks in a private
connected client. They check current-screen tokens, racial menus, placement,
selection and exact task preservation, and native menu alpha/mouse-opacity.
They wait for the real embedded-browser ready handshake. They do not inject
mouse or keyboard input, and alpha/mouse-opacity assertions are not an OS
hit-test proof. The integration run passed 35 checks with stable source/runtime
hashes and no client, server, or world errors in
`tests/palette-native-checks.json`. It includes the lifetime-token migration,
the actual touch mental-action route, rejection of ineligible selections,
original Forcefield placement, and exact paused-task preservation. It created
no world save and observed no input events.

The complete browser run and this integration run use HTML SHA-256
`3f82c1e5f6a722dbac09475e7bb412b24fe2fb182c07f0cdffba682005c41c12`.
Earlier browser reports retain their own source hashes; their counts should not
be combined into a claim that every check ran on one build. App packaging and
verification of the final bundled runtime remain the lead developer's next step.

The later special-item routing fix passes **42/42** assertions in
`tests/ui-reference-audit-checks.json`, including the original 20 lifetime-token
checks and actual potion/sign/tombstone effects with scripted modal replies.
See [the touch access audit](TOUCH_ACCESS_AUDIT.md) for remaining command routes
and the distinction between a responsive HUD and native touch input.

Magic-target assignment is separately verified by **41/41** assertions in
`tests/magic-target-audit-checks.json`, with stable source/runtime/fixture hashes
and no errors. The actual HUD and native SetTarget routes preserve exact work
and target/resource state while rejecting stale actors, targets, sessions and
recycled references. This is a headless assignment test, not a cast or native
gesture test; its client-view-size observation is a documented test seam.
