# Approved Elf sword and shield animations

The approved GOA Elf and its existing v7 rig are the animation template, as selected by the user. The former Orc experiment is kept separately in GOA Orc Sword and Shield Draft.

Idle hold and guarded walk, four facings, eight frames, 150ms per frame. Native 64px sheets are 256x512; padded 128px sheets are 512x1024. Columns South, North, East, West. Sword in anatomical right hand, shield in left. Shield front/back art and draw order follow facing; the sword sits beneath the gripping fist.

Uses the current Elf's completed upper arms, forearms, hands, original head, repaired torso and drawn walking legs. This does not replace them with Orc data or the experimental skeletal legs. The body preparation and original source files are not modified. Equipment is the existing arming sword and round shield, registered at the solved grips.

Source hashes, arm joints, grips, frame timing, draw order and separate PNG layers are in rig.json and assets/. The bundle's Scale2x helper is reused for pixel rotation; the skeletal profile is the Elf's.

Build: `python3 standalone/goa-races/bundle-equipment-rig-v1/build.py`

Version 3 retargets Human-sword-actions.json onto the Elf: raised windup, anticipation hop, cross-body sweep and recovery. Its authored per-facing grips and sweep vectors drive the weapon arm, with fixed Elf limb lengths. All body/equipment layers receive the same small pixel-snapped root movement. The shield follows the chest while keeping its approved guard target and North occlusion. Version 4 adds small-range articulated Elf torso/pelvis/head and two-bone legs. The ankles follow the root while the hips shift and knees flex. Shoulders and hand targets inherit the torso transform; the head counter-rotates. Hold endpoints retain the approved assembled body. The side far leg uses the existing inferred cutout, so this is an Elf body-motion preview, not finished rigging for all races. South attack order puts the weapon and gripping hand above the shield.

Frame durations are 360/85/85/150/70/70/160/80ms (1060ms total), splitting the Human reference phases across eight export frames. Strike is frame 4 (zero-based), after 680ms for the default sword. The same motion drives sword, hand axe, mace, warhammer, scimitar, dagger, GOA sword, rune sword and flame sword; each has its own measured grip and duration multiplier. Front/back use the Human lateral blade sweep at full length.

The approved North shield stays ahead of the character, occluded by the body. Attack sheets use padding where weapon tips leave the native body cell; rig.json exports provides the cell size and origin for each clip/item. No image is cropped to force it into 64px. Attack once returns to the held pose. The strike event is metadata for game integration, not live damage logic.

Scope: Elf one-handed swing, idle and guarded walk. Other races, thrusts, ranged/two-handed motion families and live-game replacement are not included.
