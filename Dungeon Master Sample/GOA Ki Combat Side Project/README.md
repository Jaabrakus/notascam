# Ki World — DBZ motion study

A separate 2D/2.5D world prototype using the **approved blond Elf** and our existing 15-part animation maker. The melee attacks are newly authored DBZ-inspired choreography: snappy acceleration, torso coil, a guarded recovery, a rising kick and an airborne sweep. The Elf artwork is retained; GOA punch/kick states and the previous motion curves are no longer the source of the attacks.

Double-click `Start Side Project.command` to open the world, or open `index.html` directly. The launcher serves only this folder on localhost.

Move with WASD or arrows; point to aim independently. J alternates the jab and cross, K alternates rising and aerial kicks. Tap J during a punch to queue the rush sequence. L fires a ki blast, hold C to charge, H fires a beam, Q dashes, Space toggles flight, Shift guards, and R resets. Ground position, flight height and scene depth stay separate; attacks check direction, distance and altitude.

## Newly authored motion

| Move | Full duration | Contact | Choreography |
| --- | --- | --- | --- |
| Snap jab | 320 ms | 110 ms | Short coil, fast extension and return to guard |
| Driving cross | 460 ms | 160 ms | Hip and shoulder drive, forward weight transfer, follow-through |
| Rising kick | 520 ms | 220 ms | Knee chamber, rising extension, counterlean and retraction |
| Aerial sweep | 680 ms | 300 ms | Compression, body lift, sweeping leg, recoil and landing |
| Rush sequence | 1,180 ms | 100 / 280 / 550 / 860 ms | Independently authored linked strikes |

The animation maker supplies all joint movement. The lab offers four views, skeleton overlay, scrubbing and slow playback. PNG exports contain only the character with transparent padding; timing JSON retains precise contact samples. World motion trails and contact flashes can be toggled, and are separate from the animation exports.

The body source is `Dungeon Master Sample/Unique Body Equipment Rig/rig.json`, identified as `Approved GOA Elf · male`. Its head, torso, pelvis, upper arms, forearms, hands, thighs, shins and feet remain separate source images. `animator.js` owns poses and rendering; `sandbox.js` owns world movement, projection, depth, altitude and gameplay hits. The world uses only the approved Elf rig. The build also packages the original GOA sheet separately for the comparison page.

## Build and check

From the Dungeon Master repository root:

```sh
python3 standalone/goa-dbz-sideproject/build.py
node standalone/goa-dbz-sideproject/verify_poses.js
python3 standalone/goa-dbz-sideproject/verify_world.py
```

Output: `Dungeon Master Sample/GOA Ki Combat Side Project/`.

`build.py` records source asset hashes. Original Dungeon Master art and its animation viewer remain unchanged. This is one Elf appearance and practice targets; other bodies are not retargeted yet. Hidden joint surfaces in the source rig are inferred, so extreme poses may still expose art seams. The project is a motion prototype, not finished Dragon Ball character art or a complete game. Older review files may remain in the work folder; the active page loads the current Elf animation maker.


## Side-by-side GOA comparison

Open `compare.html` (or the **GOA comparison** link) to see the original GOA Punch A1/A2 and Kick A1/A2 next to the current Elf jab, cross, rising kick and aerial sweep in South, North, East and West.

**Contact aligned** synchronizes the strike point for pose review; it deliberately retimes playback. **Native timing** plays both from the same start at their actual durations and holds the shorter move at its end. GOA retains its two original frames at 200ms each. Both characters use a common baseline and 64px body coordinates, with the original 32px GOA cells enlarged exactly 2×. Speed controls affect both sides equally.

`reference-data.js` and `goa-animator.js` are loaded only by the comparison page. The world and exported Elf sheets continue to use the Elf animation maker. Original GOA source hashes are recorded separately in `comparison-source-manifest.json`.
