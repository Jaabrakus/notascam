# Curated Orc attack set

Four attacks, four directions per attack, four phases per direction: 64 frame cells. Guard artwork is identical across all attacks for a given direction. Body only; equipment, shields and effects remain separate.

Open `index.html` directly for the animated comparison. No server or network connection is required. Pause and step through guard, preparation, impact and recovery. `contact-sheet.png` shows every frame. `orc-attacks.png` contains the combined transparent atlas; individual action PNGs and frame PNGs are also included.

## Selections

| Action | Selected artwork | Changes |
| --- | --- | --- |
| Right punch | New right punch v2 | Shared guard, alignment, common palette |
| Left punch | Left punch v2 South/East/West | North active frames reflect right punch North to correct the striking shoulder |
| Right kick | Right kick v2 | Retains the preferred foreshortened front kick; shared guard |
| Left kick | Right kick v2 counterpart | South/North reflected; East derived from reflected West and vice versa, swapping near/far striking legs |

These are existing newly drawn poses combined by pixel copying, not another generative redraw or the rejected rig library. Mirroring is explicitly recorded per frame in `manifest.json`. Unscaled selected pose crops are preserved in `selected-source-poses/`.

The user confirmed the original curated punch was correct. The proposed West right-punch correction is not applied. All 64 frame cells have been restored to the original curated set; the unused correction drawing is retained separately for reference.

## Export

- 80 × 80 transparent cells with a common ground baseline and room for extended limbs.
- One fixed scale for every pose, nearest-neighbor sampling, no smoothing or dithering.
- 16 RGB colors selected from the original in-game Orc source; alpha is 0 or 255.
- Atlas columns: South, North, East, West. Four rows per action: guard, preparation, impact, recovery. Action blocks: right punch, left punch, right kick, left kick.
- Preview timing is illustrative, not approved gameplay/hit timing.

Rebuild from the repository root with `python3 standalone/goa-races/character-retarget/curate_orc_attacks.py`. Inputs are local and hashed; no tokens, generation service, or network access are needed to rebuild. The script verifies shared guards, nonempty frames, bounds and binary transparency.

## Review limits

The user approved the front-kick motion reference, not every generated pose. Rear kicks and body movement between phases still need artistic review. These new drawings have different proportions from the original in-game Orc and are not a pixel-identical replacement for its idle/walk frames. The original master remains unchanged. This pack is a curated attack review, not the completed full animation library or an in-game integration.

## Appearance correction — dark-reference-v1

Skin now uses the shared `../attack-appearance.json` shades sampled from the user-liked attack reference. Source shading is mapped before palette quantization, without smoothing. Poses, transparency and non-skin pixels are unchanged. Earlier appearance snapshots and hashes are archived under `../appearance-revisions/before-dark-reference-v1/`; active build hash baselines now track the corrected colors.
