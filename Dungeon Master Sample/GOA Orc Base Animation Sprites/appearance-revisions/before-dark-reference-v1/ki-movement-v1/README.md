# Orc ki and movement additions

The original curated punches and kicks remain unchanged. This additive pack separates body poses, effect sprites, and animation recipes so future abilities can reuse existing pixels.

## No-redraw sequences

- Right and left fist blasts reference the corresponding approved punch sheet directly.
- Alternating ki volley plays right then left punch, releasing a projectile on each impact.
- Held extended-arm blast holds the approved right-punch impact while the separate beam animates.
- Standing aura charge holds the approved guard while the aura animates.

These five recipes generate no new body images. Turning effects off shows the same approved body pixels.

## Newly drawn actions

Power charge, open-palm blast, two-hand energy wave, jump and landing each have four phases in four directions: 80 body frame cells. A complete jump-and-landing recipe reuses those sheets. Existing guard cells are copied exactly at the start of the ki actions and end of landing.

New drawings are reviews, not an assertion of pixel-identical continuity with every approved pose. The source drawings were generated with the built-in image tool; exact prompts are in `prompts/` and original images in `drawings/`. Rear-facing poses and anatomical hand placement should be reviewed with effects off.

## Separate energy layers

Aura, projectile and beam each have four effect frames. Body PNGs contain no energy. The preview rotates projectile/beam layers to demonstrate direction and draws north-facing attacks behind the body. These are preview composites, not finalized per-direction VFX art or gameplay hitboxes.

Open `index.html` through the existing local server. Use the group filter, pause/step and energy toggle to compare body poses independently. All assets are local; no external libraries or network resources are needed.

## Rebuild and integration

Run `python3 standalone/goa-races/character-retarget/build_orc_ki_movement.py` from the repository root. Rebuilds use saved art and require no generation calls or tokens. The 16-color body palette, binary alpha, nearest-neighbor sampling and 80px body cells match the curated exporter. Effects use their own five-color blue/cyan palette and separate cell sizes.

`manifest.json` records pose references, durations, effect types and illustrative vertical offsets; `catalog.js` exposes the same data to the local viewer without file-fetch permissions. The original 64 frame hashes are checked before and after export. New effect attachment coordinates and timing are provisional. Game collision, movement physics, resource costs, hit detection, input and damage are not integrated by this art pack.
