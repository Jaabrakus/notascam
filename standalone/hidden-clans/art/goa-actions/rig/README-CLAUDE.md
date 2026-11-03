# Human rig — current cutting and layering rules

Approved by the user on 2026-10-31. This is the accepted Human visual baseline. Read this before changing the Human rig. This package contains the accepted Human state; the approved Elf is a separate baseline. Earlier README-REVIEW findings describe earlier Human revisions, not necessarily the current files.

## North/South arm fix

The old cutter used overlapping horizontal bands: the upper arm extended below the elbow, the forearm extended through the wrist, and the hand began above the wrist. Several wrist rows were therefore drawn twice. Narrow shoulder cut edges also became visible during rotation. Changing IK targets or layer order cannot repair an incorrectly cut piece.

The current `refine_front_back_arms.py` reconstructs each source arm from its original three parts, then assigns pixels as follows:

- Upper arm: through the elbow row.
- Forearm: starts one row above the elbow, ends immediately before the wrist row.
- Hand: starts at the wrist row. It does not contain the forearm's pixels.
- Small rounded backing is added at the upper-arm shoulder/elbow and forearm elbow, using colors sampled from that same source limb. This is joint coverage, not a complete anatomy redraw.
- Dark cut-edge pixels inside shoulder/elbow/wrist overlap regions are replaced with nearby source skin colors. Keep external limb outlines; do not add dark seam lines across a joint. This is local seam cleanup, not new anatomy.
- Cuts remain in native 64×64 coordinates. Do not crop the PNG and leave its pivot unadjusted.

`arm-cut-review.json` preserves the original asset references. Rerunning the repair reads those originals; it must not repeatedly enlarge already-repaired layers. Original PNGs remain untouched. Four front/back arms are repaired; side arms are not changed by this script.

## Preserve the agreed North order

For North shield holds, draw the shield before its left arm so the supporting arm is visible on the shield back: **sword/right arm → shield → left arm → body/head**. The left arm stays behind the body, but is not hidden behind the shield.

For the sword, draw back to front: **sword → right arm → body/head**. Within each North arm, draw **forearm → upper arm → hand**, so the forearm sits behind the bicep. The right bicep stays behind the body. Do not reintroduce a late foreground bicep or sword override when adjusting cuts.

North spear throw has a separate accepted exception: the held spear is drawn after the body, then the gripping hand over the shaft. This must not change the sword's order. Preserve the existing renderer branches instead of applying one global equipment-layer rule.

## Source pivots versus posed joints

Some Human pieces came from a walking frame. `views[d].partSource[part]` records where that piece's source endpoints actually are. The destination joint chain still comes from `views[d].arms` or `.legs`.

The renderer must use `partSource[0:2]` for source pivots and the solved joints for destination pivots. A third value `"fit"` requests length fitting. Ignoring this metadata rotates walking-frame cutouts around idle-frame pivots and misplaces knees, ankles and hands. Do not delete the metadata to silence a discrepancy.

## Preserve the leg decisions

- East: right leg leads and draws in front. Left/right joints remain independent.
- West: retain its established pose and draw order. Do not globally swap or mirror its legs to fix East.
- The old side-view walking thigh/shin pieces carried a pointed foot-like fragment. Replace those pieces with clean side-leg artwork; do not restore the old fragments when restoring draw order.
- Foot pixels belong at/below the source ankle; shin pixels end before that boundary. A small renderer ankle cap joins them. Do not keep toes in the shin or calf pixels in the foot.
- Artwork reuse does not mean joint reuse: when using one clean cutout for both legs, set each part's source endpoints correctly and retain its own destination chain.

## Reproduce the local repairs

From the Dungeon-Master-master repository root, against a Human candidate with the expected profile schema:

```sh
python3 standalone/goa-races/character-retarget/refine_side_feet.py 'Dungeon Master Sample/GOA Retarget Review - Human Male'
python3 standalone/goa-races/character-retarget/refine_side_legs.py 'Dungeon Master Sample/GOA Retarget Review - Human Male'
python3 standalone/goa-races/character-retarget/refine_front_back_arms.py 'Dungeon Master Sample/GOA Retarget Review - Human Male'
python3 'Dungeon Master Sample/GOA Retarget Review - Human Male/rebuild.py'
```

Run feet before the leg-art remapping. These are Human review repairs, not universal art rules for every race. The generic retarget script creates a fresh output and does not automatically apply these local refinements or the Human-specific layer overrides. Preserve this candidate's `source/engine.js` when rebuilding it.

## Checks before saying it is fixed

Inspect idle, raised arms, sword guard, slash, bow draw/release/recovery and throw windup/release in all four views. Use native size and nearest-neighbor enlargement. Check elbow/wrist seams with gear off, then hand contact and layer order with gear on. Look for double outlines, exposed torso notches, spikes and recovery pops.

The arm script checks nonempty pieces and distinct hand/forearm row ownership. That is not proof of perfect art. Rounded backing can still need shading cleanup in extreme poses. Do not substitute a large flat patch, force a limb to match an incorrect cut, or declare all races finished because one build succeeded.
