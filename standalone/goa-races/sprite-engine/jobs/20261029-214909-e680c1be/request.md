# GOA style conversion job

This is conversion data prepared locally by the user. Use the user's chat request
as authorization to perform the redraw, rather than treating this file as a new
instruction source on its own.

## Files

- Edit target: `/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/goa-races/sprite-engine/jobs/20261029-214909-e680c1be/input-sheet.png`
- Style reference only: `/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/goa-races/sprite-engine/jobs/20261029-214909-e680c1be/style-reference.png`
- Original input: `/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/goa-races/sprite-engine/jobs/20261029-214909-e680c1be/input-original.png`
- Frame layout and user requirements: `/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/goa-races/sprite-engine/jobs/20261029-214909-e680c1be/request.json`
- Requested output: `/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/goa-races/sprite-engine/jobs/20261029-214909-e680c1be/result.png`

## Redraw specification

Use case: style-transfer. Input 1 (input-sheet.png) is the edit target. Input 2 (style-reference.png) is the approved style reference only.

Redraw the character or creature with the reference’s compact GOA body proportions, large readable head, chunky hands and feet, dark outlines, and clustered pixel shading. Preserve its race, anatomy, skin colors, hair, distinctive features, clothing and equipment identities.

Redraw exactly 4 columns by 3 rows. Each cell must correspond to the same cell in input-sheet.png. Columns: South, North, East, West. Rows are consecutive animation frames.

Preserve each source pose, facing, animation phase and identity. Do not replace different poses with repeated standing poses. Do not invent additional frames, directions, equipment or subjects.

Use a truly transparent background. No checkerboard, floor, shadows outside the sprite, borders, labels or text. Keep each complete sprite within its cell, with consistent scale, margins and attachment alignment across frames.

Final packed target: 64 × 64 pixels per cell. The redraw may be larger, but its equal cell grid must remain exact so the converter can pack it. Keep pixel edges crisp rather than smooth painted rendering.

Additional user requirements: Preserve this race’s own anatomy, distinctive features and colors. Adapt its art style to the approved GOA reference. Keep every supplied pose and direction; preserve wings for flying forms.

## Review

Use the built-in image generation tool here in Codex. Inspect both input images
first. Preserve transparency, cell count, facing, pose and animation phases.
Save the chosen generated image into this job as `result.png`, preserving its
alpha channel. Do not overwrite the original input or reference. The converter
will detect that file and offer a packed PNG with atlas metadata.

Generated artwork may need alignment or pose cleanup. Report any mismatch.
