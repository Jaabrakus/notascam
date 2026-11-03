# Remastered command dock

Replace the permanent ring of tiny map icons with labeled controls that can be
used by touch. This changes the active Remastered game only.

## Layout

- The map defaults to a clean view without the yellow frame or permanent border
  buttons. Original construction and magic palettes remain available.
- Stop, Interact, Focus, and Controls form the quick command dock.
- All 44 commands remain in Controls, grouped as Units, Gather & inventory,
  Build & terrain, Camera & world, and People & settings.
- Search filters labels, descriptions and shortcuts. Opening groups and reading
  descriptions never executes a command.
- The day/night indicator stays visible in the compact world status. Camera and
  minimap tools collapse so unit cards are easier to reach.
- Classic border can be shown again from Controls. That preference is saved.
- Existing Do now, Add tasks, Deselect, work queues and defense settings remain.

October 17 compact follow-up: on screens at most 740 pixels high, the redundant
category strip and repeated selection hint collapse. **Controls** still opens
every category. World status is the camera/minimap disclosure, Idle joins the
unit-selection row, and an active attack alert appears in the sticky command
bar. A closed camera no longer reserves space for inactive alert controls.
The original 320×568 and 390×625 layouts hid even the first unit name below the
fold; the revised layout shows its name/portrait without scrolling while
retaining touch-sized Stop, Interact, Focus, Controls, and Deselect.

## Integration

`Interface/border-controls.json` remains the trusted list of original command
IDs and handlers; each row now has a purpose group. Every old command retains
its original effect, including the distinctions between pickup/harvest,
items dropped here, and stockpile delivery.

`remaster_border_layout_version` migrates previous profiles once to the new
clean layout. Later explicit Show/Hide choices survive loading. The original
border remains usable until the browser reports ready. Hidden objects stay in
`client.screen`, with alpha and mouse opacity zero, so legacy dig/day updates
still work. Showing restores the exact original properties.

## Verification

The compact follow-up passes 162 final browser checks, including 18 short-screen
visibility/access checks, with no browser errors. `tests/hud-compact-before-checks.json`
retains the two before-fix failures; `tests/hud-compact-checks.json` records the
focused pass. `tests/hud-compact.png` uses a synthetic data fixture, not a live
world capture. Native WebKit palette captures are available separately under
`tests/palette-web-*`; a final compact native capture follows integration.

The results below describe the earlier command-dock build, before this follow-up:

- [x] All 45 catalog rows have a valid group; original action IDs remain intact.
- [x] New and old profiles start clean; explicit Classic border choice persists.
- [x] Actual pickup/drop effects and unit task identities are preserved.
- [x] Mobile layouts, search, group navigation, disabled commands and focus pass.
- [x] Native hidden controls are noninteractive; dig and build palettes still work.
- [x] Rebuilt canonical app opens the existing player save successfully.

Desktop responsive and touch-event checks are preparation for mobile use;
they do not establish that the native desktop app is a mobile build.

Verification results: **33 headless game checks**, **103 browser checks**, and
**16 connected native-client checks** passed with no runtime or browser errors.
Every one of the 44 commands was tapped at 320, 390 and 768-pixel widths, with
its exact catalog ID verified. Search, empty results, disabled commands, focus,
Escape and Classic border restoration were exercised, along with the existing
queue and automatic-defense controls.

The native fixture used real game units and original callbacks in an isolated
profile with no injected input or saves. It verified all 54 permanent border
objects' alpha/mouse-opacity state, readiness fallback, retained screen identity,
and hidden autodig callbacks. This is not a physical pointer hit-test. The
engine framebuffer captures the map but excludes the native WebKit overlay;
browser images separately show the actual HTML layout.

Evidence: `tests/border-controls-checks.json`,
`tests/easy-orders-hud-checks.json`, `tests/command-dock-native-checks.json`.

The canonical app was rebuilt and reopened with the existing Kiwi save. Its
client reached InGame with the updated HUD and 45 active icon resources, no
missing browser resources, and no client/server errors. The normal launch
snapshot confirms the yellow frame and permanent ring are gone. The current
save was acknowledged and backed up before rebuilding; no older roster was
restored. Engine binaries and original sprite files are unchanged.

Package/startup evidence: `tests/command-dock-package.json`,
`tests/command-dock-normal-launch.json`, and
`tests/command-dock-prebuild-save.json`.
