# Unique bodies, modular armor, authored fits

The original race, hybrid and female bodies remain the source of truth. A shared skeleton vocabulary does not mean a shared silhouette. The consolidated-body experiment is preserved separately.

## Source art and anatomy

Work in the character's native 64px body space. Inspect both at 1× and an integer enlargement with nearest-neighbor sampling. A 64px canvas alone does not make downsampled artwork clean pixel art.

Record shoulders, elbows, wrists, chest, waist, hips, knees and feet for each facing. Keep original head shapes, ears, hair, horns and tails. Record what overlaps the armor and what belongs behind it. Different anatomy requires a different fitting profile even when bone names are shared.

Before animating cutout limbs, complete the hidden shoulder, armpit and torso surfaces. Give upper/lower limb pieces overlapping joint ends. Reconstructing a static source image exactly does not establish that it has enough artwork for rotation.

## Armor masters

Start with the approved Deepguard Iron design on the original Elf. Keep the body underneath for reference, and separate helmet, chest, left/right shoulder, bracers/gloves, waist, greaves and boots. Spear and shield use independent grip points.

Keep lighting consistent with the original base. Target a small palette per material: outline, shadow, midtone and highlight. Use discrete contact-shadow pixels rather than blurry shadows. Preserve recognizable Deepguard materials, trim and silhouette.

## Fit variants

For minor anatomical differences, cut and shift sections at anchors. For substantial size differences, nearest-neighbor resizing is only a draft: clean the silhouette, trim thickness and shading manually. For a different build, redraw the volume while retaining the equipment's design identity.

Reuse a fit only after the corresponding torso and limbs actually match. A hybrid can inherit a parent fit where anatomy is unchanged. Different proportions, female forms, wings, tails and horns can require local variants. Crafting traditions and wearable fit are separate data.

## Movement and export

The rig moves approved fitted layers. The chest follows the torso, shoulder armor follows its shoulder joint, bracers follow forearms and boots follow feet. Main-hand and off-hand equipment follow solved grip points. Each facing defines depth ordering and occlusion.

Check idle, both walk steps and the extreme attack pose at 1× and 4×. Inspect shoulder gaps, elbows, grip position, hair occlusion, feet registration and clipping. Bake approved results to transparent atlases with stable registration for game rendering. Additional facings require additional artwork; rotating a flat attachment does not create a new viewpoint.

## Current proof status

The Elf demo uses the approved GOA-style sprites intended for the finished game, as selected by the user. Version 2 adds AI-completed hidden torso and joint surfaces inside authored anatomy masks. New colors are remapped to exact source colors in CIELAB; existing visible layer pixels remain unchanged. Raised-arm inspection and a Completed surfaces toggle expose the result without equipment. The demo also has articulated arms, three equipment slots, four facings, original walk legs, exact-scale viewing and fit/PNG exports. It is still a first Elf proof, not a complete modular armor set or production-quality fits for every race. Do not label automated validation as visual approval.

Next visual work: review the completed Elf surfaces and refine the chest/arm fit, then fit one stocky and one small original body before expanding the catalog. Source lighting rotates with each rigid arm fragment; challenging poses can still require drawn replacement pieces.

Version 4 refinement: north/south arms now use complete rounded joint ends, cleaned internal seams and slim outer contours. Exposed torso silhouettes are repaired and detached scraps are removed from render layers. The north view draws the arms behind the body and hair. These render-layer repairs intentionally replace malformed cut-edge pixels; the original approved sheets and the earlier unmodified cutouts remain preserved. East/West retain their shared mirrored arm master. Use `North_South_Movement_Inspection.png` to review the full unarmored raise/walk cycles.

Version 5 supersedes the v4 arm repaint: retain the original arm and hand artwork, shorten elbow overlap to three rows, and trim dark scraps beyond a one-pixel skin outline. North/south hand targets follow shoulder-centered arcs during Raise arms, avoiding the deep elbow folds caused by straight-line target interpolation. West now shares the mirrored East torso, shorts and walking legs as well as its arm master; the approved West head stays separate. Default preview is idle. The original sheets are still untouched.

Version 7 adds the full fifteen-part Elf component profile, hip/knee/ankle chains, head pivot, per-part inspection and fifteen equipment anchors. Only chest/spear/shield have fitted equipment artwork. The full-body study uses gentle joint movement; the repaired drawn walk remains separate. Side-leg extraction now excludes the other foot, and shorts stay on the pelvis instead of rotating with the thigh. Female/race/hybrid profiles and pose-specific deep-bend art remain outstanding.
