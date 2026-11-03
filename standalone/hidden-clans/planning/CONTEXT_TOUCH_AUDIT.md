# Native context row click audit — 2026-10-17

Status: reviewed and installed in the shared client, including the fourth verified Remastered app. The22-check final native evidence below belongs to its recorded private snapshot; later dialog sizing changes have their own92-check evidence at three scales. Context rows retain their existing dimensions. Click/release without hover works, but physical touch and long-press map activation remain unverified.

## Existing behavior and reproduced failures

The native map's right-click path already opens a menu containing separate rows
for stacked visible objects and the turf. The object rows only open their verb
submenu on `MouseEntered`; a press/release without hover does nothing. The
existing submenu creates executable original verbs, filters hidden and
`popup_menu=0` verbs, and executes one only from its own separate button click.
At the bottom-right edge, the submenu clamps inside the screen over its parent
because `SetActiveItem` does not supply the already-supported alternate-left
origin.

Source evidence in the inspected engine checkout:

- [Row hover handler](/tmp/dm-runtime-audit/opendream-source/OpenDream-latest/OpenDreamClient/Input/ContextMenu/ContextMenuItem.xaml.cs:32).
- [Stacked object enumeration](/tmp/dm-runtime-audit/opendream-source/OpenDream-latest/OpenDreamClient/Input/ContextMenu/ContextMenuPopup.xaml.cs:51) and [submenu creation/placement](/tmp/dm-runtime-audit/opendream-source/OpenDream-latest/OpenDreamClient/Input/ContextMenu/ContextMenuPopup.xaml.cs:127).
- [Original filtering](/tmp/dm-runtime-audit/opendream-source/OpenDream-latest/OpenDreamClient/Input/ContextMenu/VerbMenuPopup.xaml.cs:31) and [separate verb execution](/tmp/dm-runtime-audit/opendream-source/OpenDream-latest/OpenDreamClient/Input/ContextMenu/VerbMenuPopup.xaml.cs:96).
- [Existing alternate-left placement](/tmp/dm-runtime-audit/robust-source/RobustToolbox-af2a7d0406b410c4d960f0f4b34513651c6dc742/Robust.Client/UserInterface/Controls/PopupContainer.cs:93).

## Private patch

`PatchContextClick.Apply(module)` is invoked exactly once after the retained
movement/variant/rewind client fixes. It adds a matching `UIClick` down/up pair
to the row. Activation requires release inside the same row, clears its pressed
flag, and calls the existing `SetActiveItem`. Focus loss clears the flag, matching
Robust's existing `BaseButton` cancellation behavior. Only the unchanged hover handlers set/clear `PanelOverride`; a no-hover tap
does not leave a simulated hover highlight on the row. Original verb
filtering/execution remain in use. The patch passes the row's
position as the alternate-left popup origin; existing bounds clamping remains
responsible for vertical placement.

`PanelContainer` inherits through `Container` directly to `Control` for
`KeyBindDown`, `KeyBindUp`, and `ControlFocusExited`. The private build asserts
that hierarchy before adding overrides, so a later base-handler change fails
the patch instead of being bypassed. The original UI manager also only delivers
a release to the control that received the matching down, and suppresses
releases to hidden controls. The first candidate nevertheless needed the explicit
focus-loss clear: a visible row can receive its recorded release after focus
cancellation.

Private integration sources:

- [PatchContextClick.cs](/tmp/dm-runtime-audit/context-touch-release/engine/PatchContextClick.cs)
- [PatchClient.cs call site](/tmp/dm-runtime-audit/context-touch-release/engine/PatchClient.cs)
- [Build integration](/tmp/dm-runtime-audit/context-touch-release/tools/build_client_compat.py)

No hold timer, normal-map click delay, input-origin guessing, recipe changes,
selection change, or task cancellation is added.

## Evidence and test boundary

The private fixture uses original Human constructors, two stacked target Humans,
an original stone without applicable verbs, a selected worker with an exact
paused active/pending FIFO, and the explicitly granted original `SetTarget` verb.
Additional fixture-only verbs verify hidden/no-popup filtering and detect
unintended execution. Only fixture startup and read-only observations are in DM;
menu actions run through the private client's actual UI manager down/up and
focus callbacks. Map context opening uses the real ControlMap/MouseInputSystem
callback and hit map. There is no OS mouse/focus injection or normal-app input.

The bottom-right case explicitly reopens the original popup at the window edge;
it is a placement check, not a physical pointer gesture. The hover regression
explicitly invokes the original `MouseEntered` callback. Physical input delivery,
long press, every viewport size, and device touch behavior remain untested.

- [Validated installed baseline](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/tests/context-touch-before-validated-checks.json): **15/18**, failing row release without hover, stacked-target switching, and parent overlap. The harness explicitly uses a labeled hover fallback after the failed tap to reach remaining original-verb checks.
- [First private candidate](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/tests/context-touch-candidate-checks.json): **18/18** for the initial scope.
- [Cancellation reproduction](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/tests/context-touch-cancel-before-checks.json): **20/21**; only focus loss before release incorrectly activates. Closing the popup and an unmatched release after reopening already pass.
- [Behavior candidate before styling refinement](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/tests/context-touch-final-checks.json): **21/21**, including focus-loss cancellation, popup-close/reopen cancellation, original verb effects and FIFO preservation. No client/server/world errors; recorded hashes unchanged; private processes stopped.
- [Styling reproduction](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/tests/context-touch-styling-before-checks.json): **21/22**; the original 21 behavior cases pass, but sequential no-hover taps leave both Human rows with a gray override. This is corrected by removing only the tap-time styling assignment.
- [Final styling candidate](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/tests/context-touch-styling-final-checks.json): **22/22**, with both no-hover-tapped rows showing no hover override. All original 21 cases still pass; no client/server/world errors; stable hashes on runtime `783f6ad20cb1f578d57429d2c015587187f6ac59e88e6c8bce609858fff5b6f4`; private processes stopped.
- [Private release manifest](/tmp/dm-runtime-audit/context-touch-release/release/manifest.json) includes the reproducible build, source patch, DLL/ZIP hashes and probe evidence.

The initial `context-touch-before-checks.json` is preserved but incomplete: its
fixture did not explicitly grant `SetTarget`. The validated baseline above fixes
that fixture omission; it is the usable before evidence.

## Why this does not yet provide long press

The inspected SDL3 bridge copies button/window/modifier fields, dropping the
SDL device-origin field before higher-level input sees it. `GUIBoundKeyEventArgs`
contains a function, state, pointer, and local coordinates without a touch-origin
field. No finger-event path was found in this inspected SDL dispatch. Native row
or map handlers therefore cannot reliably distinguish touch from mouse input.
A future hold gesture needs explicit backend origin/cancellation plumbing and
physical-device verification; adding a delay to every normal mouse click would
be a separate product behavior change.

Source: [SDL mouse-button translation](/tmp/dm-runtime-audit/robust-source/RobustToolbox-af2a7d0406b410c4d960f0f4b34513651c6dc742/Robust.Client/Graphics/Clyde/Windowing/Sdl3.RawEvent.cs:89),
[retained event fields](/tmp/dm-runtime-audit/robust-source/RobustToolbox-af2a7d0406b410c4d960f0f4b34513651c6dc742/Robust.Client/Graphics/Clyde/Windowing/Sdl3.RawEvent.cs:213),
and [UI input routing](/tmp/dm-runtime-audit/robust-source/RobustToolbox-af2a7d0406b410c4d960f0f4b34513651c6dc742/Robust.Client/UserInterface/UserInterfaceManager.Input.cs:122).
