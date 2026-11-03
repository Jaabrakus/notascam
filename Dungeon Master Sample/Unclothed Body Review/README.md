# Unclothed body review

Requested: male and female bases with underwear removed, so clothing can be equipped separately. Plain, undetailed mannequin anatomy is intentional.

Reference sources:
- Male: `../Approved Sprites/Male/Human/base/sprites.png`
- Female: `../Sprites/Female/Human/base/sprites.png` (current working sheet; not in the approved-male collection).

Status: image generation was blocked by the image tool's safety system. No edited image was produced and no source sprites were changed.

Proposed review layout: top three rows male, bottom three rows female. Columns: South, North, East, West. Each group has idle, walk A, walk B rows. Any future generated image must be treated as an art draft, not a rig-ready replacement.

Before integration, restore each frame to the original 64x64 canvas and check neck, shoulders, elbows, wrists, hips, knees, ankles and ground baseline against its source. Reconstruct complete body parts beneath clothing; simply deleting clothing creates holes. Retain the accepted rig's pivots, direction-specific depth order and animation timing. Review all four directions and both walk phases before exporting.

The approved sprites and animation packages remain untouched. Do not feed this full generated sheet directly into the existing rig cutter or claim its alignment is verified.
