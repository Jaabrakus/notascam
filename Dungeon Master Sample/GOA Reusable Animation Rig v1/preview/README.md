# GOA reusable animation rig — v1

Snapshot: rig-package-16. Start with `preview/index.html`. This folder contains the current Elf rig, 97 animation clips, equipment artwork, baked PNG/JSON sheets, and editable renderer code. North spear has a longer rear shaft and thicker forward section, attached at the same grip.

## Reproduce the current result

Requires Python 3 only for rebuilding; the browser runs the preview.

```
python3 rebuild.py
python3 -m http.server 8880 --bind 127.0.0.1
```

Open http://127.0.0.1:8880/preview/. The default profile reproduces the packaged Elf. `preview/exports` contains all 97 baked sheets and timing/grip metadata. Body artwork uses native 64px coordinates; export cells are 192px with origin [64,64]. Columns are South, North, East, West.

## Adapt another character

1. Duplicate `profiles/elf-male.json` under a new name. Preserve the four-view order and the part names.
2. Add that character's transparent native-scale PNGs to `preview/assets` with unique filenames. Each view needs head, torso, pelvis, upper arms, forearms, hands, thighs, shins and feet. Complete hidden anatomy so moving a limb does not expose holes. Also supply the idle/walk images referenced by each view's `walk` rows.
3. Replace the profile's image references. Calibrate neck, waist, each shoulder/elbow/wrist, hip/knee/ankle, near-leg order, joint colors and both hand grips. Coordinates belong to the same 64px canvas as the PNGs; never measure from an enlarged screenshot.
4. Run `python3 rebuild.py profiles/your-character.json`. This rebuilds the preview, not the pre-baked exports. Existing baked sheets and verification reports still describe the original Elf until regenerated and rechecked.
5. Tune the character's action targets in `source/engine.js`. Bow/throw targets currently contain Elf-specific coordinates and corrections. Sharing the motion timing does not automatically fit every race, female or hybrid body. Calibrate one new character before expanding further.
6. Review every facing at windup, release, follow-through and recovery. Bow release is 0.90s; throw release is 0.38s. Check seams, hand contact, foot contact and layer order at native scale and slow playback. Export reviewed clips with the viewer buttons.

## Current rules worth preserving

- West is the master side bow pose. East mirrors its complete rendered animation.
- Both bow arms straighten toward relaxed rest after the shot; do not return the drawing hand to a raised shield grip.
- Front/back arrows are short end-on tips. North body occlusion is intentional.
- South throwing forearm is upright; North windup uses an outward elbow and upright forearm (reverse L).
- North held spear draws over the body, with the gripping hand on top. Shaft width/length are adjusted around the grip, so the weapon stays attached.
- Spear is vertical for North/South and horizontal for East/West. Axe/dagger use their own rotation.
- Projected limb lengths may be shorter than the physical calibration; tests must not force full side-view lengths onto foreshortened limbs.

## Contents and limits

`source` is the editable portable viewer/renderer. `profiles` supplies calibrated character anatomy. `preview` is runnable and includes assets, exports and reports. `original-pipeline` preserves extraction/build/test scripts for the original Dungeon Master repository; those scripts rely on its source paths and are not standalone commands for this package. `rebuild.py` is the standalone builder.

The archived technical verification covers all 97 clips. It does not mean every clip or deep bend is visually approved. Physics falls and projectile flight remain preview approximations; collision, damage and live game integration are separate. Only the approved Elf male is calibrated here. This package does not modify the live game.

`source/AI-HANDOFF.md` records earlier iterations; the rules above describe this final snapshot and supersede conflicting historical notes. `manifest.json` records packaged file hashes for reproducibility; regenerate it after intentional edits if you need a new snapshot.
