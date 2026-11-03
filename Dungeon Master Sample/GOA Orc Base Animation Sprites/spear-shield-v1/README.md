# Equipped short spear jab — review v1

The user requested a small thrust and visible spear/shield to judge the pose. This is the current review target. Long empty-hand thrust, lunge and sweep drafts are archived under drawings; remaining weapon moves are pending this correction.

- 16 cells: south, north, east, west; ready, small pullback, short jab, recover.
- 96px cells give the spear room without shrinking the Orc. Fixed nearest-neighbor scale, binary alpha, original body palette plus wood and metal colors.
- Recovery copies ready pixels exactly. Prior 208 body cells are unchanged.
- Equipped sprites are flattened visual references, not separate body/equipment layers. No game integration or hitboxes yet.
- Built-in image generation supplied the drawings. Exact prompts: prompts/equipped-thrust.json.
- Rebuild from project root: python3 standalone/goa-races/character-retarget/build_orc_spear_preview.py

## Appearance correction — dark-reference-v1

Skin now uses the shared `../attack-appearance.json` shades sampled from the user-liked attack reference. Source shading is mapped before palette quantization, without smoothing. Poses, transparency and non-skin pixels are unchanged. Earlier appearance snapshots and hashes are archived under `../appearance-revisions/before-dark-reference-v1/`; active build hash baselines now track the corrected colors.
