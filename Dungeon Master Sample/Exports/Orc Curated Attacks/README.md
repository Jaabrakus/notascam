# Orc Curated Attacks

Packaged with the corrected dark-reference-v1 skin colors.

**4 attacks × 4 directions × 4 phases = 64 frames.**

- Right punch, left punch, right kick, left kick.
- Directions, left to right: south/front, north/back, east/right, west/left.
- Phases, top to bottom: guard, windup or knee chamber, impact, recovery.
- Native frame size: 80 × 80 pixels with transparent padding.
- Body only. Weapons, shields and effects are separate from this set.

Open **index.html** for the offline animated preview. Pause and use Next frame to inspect poses. No server is required.

## Files

- `frames/`: 64 individual transparent PNGs, named action-direction-phase.
- `punch_right.png`, `punch_left.png`, `kick_right.png`, `kick_left.png`: four 320 × 320 action sheets.
- `orc-attacks.png`: 320 × 1280 combined atlas, action blocks in the order listed above.
- `contact-sheet.png`: labeled overview of all poses.
- `manifest.json`: frame rectangles, direction order, timing, pixel palette and source provenance.
- `source-drawings/`: selected source drawings, copied without modification.
- `references/`: original in-game Orc and the user's attack appearance reference.
- `SHA256SUMS.json`: hashes of the packaged files.

Use nearest-neighbor filtering and disable texture smoothing. Keep transparent padding when importing frames. Preview timing is illustrative; gameplay hit timing and integration are not included. These curated attack drawings are not pixel-identical replacements for the original idle/walk art.

The sprite PNGs are exact copies of the current curated exports. Packaging does not redraw or recolor them. Experimental thrusts, spear/shield tests, ki moves and special moves are not part of this four-attack package.
