# Orc base animation sheets

All 97 existing library actions plus 21 ki-study/unarmed actions and chains are
exported as transparent body-only sheets. Separate equipment sheets are in weapons/.
Open index.html to play, slow down, scrub and inspect each direction independently.
Original Orc artwork is the master. Idle/walk copy the original drawn cells; other
poses assemble its existing cut pixel parts using saved motion definitions.

Body space remains 64px. Each export cell is 192px with the original body's origin
at [64,64], preserving room for extended arms, kicks and falls without resizing.
Columns are South, North, East, West; rows are chronological samples. Timing JSON
includes action events and both hand sockets for equipment/effects added later.
Weapon/shield gripping poses remain; equipment and effects are not painted in.

These are assembled pose drafts for review. The rig's inferred hidden anatomy,
deep bends, nearest-neighbor rotations and simulated reaction poses can need
pixel cleanup. This is not a new AI redraw or blanket visual approval. No live
game files changed. Ki-study poses adapt existing choreography to the original Orc
parts; they are new review candidates, not approved finished art. verification.json
records actual coverage and source hashes.
