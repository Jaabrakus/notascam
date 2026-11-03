# Human Male review — why this does not yet match the approved Elf

Reviewed 2026-10-30 against `../GOA Reusable Animation Rig v1`, the approved Elf baseline. This is a diagnosis and correction plan; the Human artwork and animation code have not been modified by this review.

## Main finding

The Human is an initial asset conversion, not a finished retarget. Its renderer is byte-identical to the packaged Elf renderer, but its anatomy, cutout boundaries and hand positions are different. Copying the renderer preserved our timing and special-case logic; it did not automatically preserve the final pose silhouettes.

The original package also has a limitation: several bow/throw targets are still Elf-specific coordinates inside `source/engine.js`. A profile swap alone is insufficient. The original package guide explicitly calls for tuning those targets. This is a limitation we need to address in the shared framework, not evidence that the Human creator changed the approved animation engine incorrectly.

## Evidence and priorities

### 1. Audit the joints before tuning animation

The profiles contain these native 64px-canvas measurements. Reach is upper-arm length plus forearm length, calculated from the shoulder, elbow and wrist points.

| Measurement | Elf | Human |
| --- | --- | --- |
| South right shoulder/elbow/wrist | [23,29], [21,37], [20,44] | [21,32], [20,36], [20,41] |
| South right reach | 15.32 px | 9.12 px |
| South left reach | 15.32 px | 15.25 px |
| South/North neck | [32,25] | [32,30] |
| South/North waist | [32,42] | [32,46] |
| East near-right reach | 15.06 px | 13.89 px |
| East far-left reach | 9.47 px | 13.89 px |

The South Human right-arm calibration is markedly shorter than its left. This is a red flag to inspect against the actual pixels, not a reason to force symmetry blindly. A bent or hidden arm can have a shorter *projected* appearance; that should not automatically become a shorter physical limb used by every pose.

The Human neck and waist sit 5px and 4px lower. Absolute Elf bow targets therefore land at different positions relative to the Human's face and chest. Reach clamping can prevent an invalid IK solve while still producing an unattractive pose.

**Fix:** open `inputs/sprites.png`, `inputs/Human.json` and `profiles/human-male.json` together. Check every joint at native resolution. Distinguish anatomical limb length from projection. Confirm the wrist is the hand attachment, not the elbow, fist center or a segmentation boundary that happens to be nearby.

### 2. Segmentation masks are not finished animation layers

`tools/cut_from_finezones.py` splits visible arm and leg pixels by nearest bone segment. It then adds capsule-shaped flat-color fillers. This identifies ownership, but does not recover the shaded shoulder, torso or limb surfaces hidden in the original sprite.

The Human README itself records a shoulder notch because the chest corner was assigned to the arm. `back_fill()` only processes rows that already contain an owning torso/hips zone; it cannot reconstruct missing anatomy on a row with no such pixels. `outline_added()` can also turn repair boundaries into dark contours that need visual cleanup.

The saved `review/zoom.png` shows broken-looking leg/shorts silhouettes in the attack poses and a crowded South bow pose. These observations are consistent with the incomplete layers and unretuned targets; the still images alone do not isolate every cause.

**Fix:** reconstruct complete torso and pelvis silhouettes underneath the movable limbs. Give upper/lower limbs overlapping joint ends with matching shading and outlines. Inspect `review/parts-*.png` and animated raised-arm/bent-knee poses, not only the original idle composite. Do not use larger flat caps as a substitute for missing anatomy.

### 3. The far-arm copy is an approximation, not the Elf's authored far arm

The cutter copies the near arm by `(7,1)` in East and `(-7,1)` in West, then darkens it by 18%. This preserves the near arm's length and shape. The Elf's far arm has different joint spacing: East far reach is 9.47px, versus the Human copied far arm's 13.89px.

The copied offset does not reproduce the Elf's complete calibration or artwork. Global darkening also creates colors rather than deliberately selecting the sprite's shadow palette.

**Fix:** calibrate the far shoulder and projected limb geometry for this body. Reconstruct a far limb using appropriate silhouette and shading. Check two-handed weapons and side views; do not simply transplant the Elf's shorter measurements either.

### 4. Guard offsets and action targets need separate fitting

`ELF_GRIP_OFFSETS` transfers Elf shoulder-relative guard offsets to Human shoulders and clamps them to reach. That produces reachable targets, not necessarily a correct grip or stance. Meanwhile, `bowPose()` still uses absolute Elf cheek/nock/bow coordinates. The special South/North throw elbow offsets also remain tuned for the Elf.

**Fix:** add per-character action calibration to the profile: guard grips, bow hand, nock, cheek, release follow-through, throw windup elbow/hand and recovery targets. Express these relative to appropriate anatomical anchors where possible. Keep source timing shared. Keep projected lengths and layer order explicit. Move the existing Elf values into the Elf profile without altering its rendered result, then calibrate Human separately.

The mirrored side bow uses the South body in the West master, with a West head; East mirrors that result. Inspect the Human South arm data when debugging side archery, not only its East/West source arms.

### 5. Verification and packaging are incomplete

The Human README says it was reviewed at selected still frames, and that it has no baked export sheets or verification reports. That does not establish clean transitions, recovery, mirrored poses or sustained hand contact. The Elf was refined across multiple key poses and playback passes.

`rebuild.py` also defaults to `profiles/elf-male.json`, which is absent in this Human folder. The documented explicit command works around this, but a bare `python3 rebuild.py` will fail. The viewer still has links intended for baked exports that this package has not supplied.

**Fix:** default to the Human profile, update presentation labels, and disable or supply missing export links. Run character-aware checks and bake exports only after the Human poses have been reviewed. Do not copy an Elf verification report and call it Human validation.

## Recommended correction order

1. Preserve the approved Elf package as the visual regression baseline.
2. Reassemble Human idle views from the cut parts without equipment; compare against the source sheet. Resolve misplaced joints and incomplete torso/pelvis first.
3. Review the South right arm's unusually short calibration and the synthetic far arms.
4. Repair shaded hidden surfaces and joint overlaps. Check shorts/thigh ownership when knees bend.
5. Establish Human empty-hand guard, raised-arm and straight-arm poses. Only then attach gear at actual palm sockets.
6. Fit one-handed attack and shield hold, then bow and spear. Preserve the approved motion phase and timing, while adapting anatomy-dependent targets.
7. Review all four directions at bow 0.32, 0.72, 0.90, 1.15, 1.40 and 1.75s; throw 0.26, 0.38, 0.52 and 0.75s. Inspect full playback, not only the release frame.
8. Compare native 1× and nearest-neighbor enlargement with joints on/off and gear on/off. Check gaps, double outlines, hand contact, elbow bends, foot sliding and recovery pops.
9. Validate source integrity, mirrored bow views, release events, grip continuity and unclipped exports. If the representation allows foreshortening, validate projected lengths separately from physical calibration.
10. Export and package the Human only when those comparisons are acceptable. Use it as the next tested profile before batch-converting races or hybrids.

## Instructions for the next AI

> Keep the approved Elf unchanged. The Human is not finished merely because its PNGs have the same part names. Read this review and the Human cutter. Audit the South right-arm joints, reconstruct hidden anatomy and shorts/leg overlaps, then move Elf-specific action targets into character calibration. Fit Human targets against its own body. Preserve the accepted animation timing, mirrored side bow, straightening bow recovery, North reverse-L throw and spear/hand layering. Demonstrate the Human at synchronized key poses and in playback before exporting. Report approximations instead of claiming that a successful build proves visual quality.
