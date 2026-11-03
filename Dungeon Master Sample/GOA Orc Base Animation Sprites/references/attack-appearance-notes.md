# User-liked attack appearance

Reference: user-liked-attack-appearance.png, supplied November 1, 2026.

The user likes this attack sheet and noticed color drift in the hand-to-hand sprites. Preserve its darker green skin, visible shading, short legs, large head, red eyes, dark shorts and outline as the appearance reference when refining attacks.

Inspection found that the current curated hand-to-hand exports and thrust foundation both predominantly use RGB (109, 152, 76), considerably brighter and flatter than the supplied reference. All 224 earlier frame hashes still match the snapshot taken before the thrust-foundation work: the newest build did not alter those files. The mismatch is present in the existing exported appearance as well as the new thrust.

This records the user's visual feedback only. No body or equipment frame has been recolored. A palette adjustment alone cannot restore the reference's shading in regions that are flat in the generated drawing. Do not claim the appearance is matched until visually verified.

## Correction applied

The earlier observation above is historical. The dark-reference-v1 export now applies shared reference shades to the source drawing pixels before quantization. See ../appearance-revisions/dark-reference-verification.json for checks confirming unchanged silhouettes and non-skin pixels.
