# One animation, original bodies

All four directions must depict the same local action and timing. A forward raise is side-on in East/West, foreshortened toward the viewer in South, and foreshortened away from the viewer in North. It is not a lateral raise in the front view. Version 6 uses one lift angle and camera-aware projection; the hands are separate unscaled attachments. End-on silhouette and lighting are still approximations from cutouts, not fully redrawn view-dependent poses.

## Complete component layout

The intended base set is fifteen parts: head, torso, pelvis, and paired upper arms, forearms, hands, thighs, shins and feet. Hair can be separated into front/back layers; ears, tails, horns, wings and beards are optional anatomy attachments. Each cut part needs full hidden surfaces and joint overlap before it can articulate independently.

Version 7 separates all fifteen components for the male Elf and exposes a small-range full-body joint test, per-part inspection, a registered 64px component export and moving equipment-slot anchors. Walk mode still uses the repaired drawn frames; a finished skeletal walk is not implemented. The previously occluded side leg reuses the extracted near leg with independent registration. Tiny hidden joint caps extend neighboring source skin. These inferred surfaces need pose-specific artwork for larger movements. Hair/ears remain attached to the original head rather than being independently rigged.

## Reuse across races, females and hybrids

Share part identifiers, bone parent relationships, equipment slots, pose timing and the camera projection convention. Each source appearance retains its own body, head, limb lengths, pivots, masks, depth order and palette. Sex is an appearance/profile field, not a reason to change the skeleton names.

Hybrids can inherit the parent's rig only where anatomy is actually the same. Changed limb proportions, flight forms, tails, wings and unusual heads need profile or attachment overrides. Armor may reuse a parent fit only where its covered surfaces match; otherwise author a fitted variant while retaining the item design.

First finish and visually validate this Elf. Next validate the same component and motion format on the approved female Elf, an Orc and a small Goblin. Those reveal proportion and occlusion problems before batch preparation of the remaining appearances. Scripts can extract, register, palette-map, compose and export; hidden surface completion and visual fit still need review.

After poses are approved, bake equipment combinations to registered sprite atlases for crowd rendering. This proof has not replaced the game's live assets or converted all race sheets.
