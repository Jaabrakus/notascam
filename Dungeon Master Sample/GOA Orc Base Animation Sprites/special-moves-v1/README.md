# 2D Orc special moves

The user approved overhead cast, ground slam, dash strike and hit reaction/stagger, then explicitly chose to stay with 2D. This pack uses newly drawn 2D art, not the separate declined 3D prototype.

Four action sheets in four directions, with four phases each: 64 frame cells. Columns are South, North, East, West. Every starting guard and the stagger recovery guard are exact copies of the approved curated guard. The original 64 attack frames are checked by hash and remain unchanged.

`index.html` shows the animations with pause, step, speed and optional dash-travel controls. `orc-special-moves.png` combines all action sheets; `frames/` holds individual 80px cells. `front-contact-sheet.png` shows the front-view sequence for each move. The body images contain no weapon, shield, energy or impact-effect layers.

The built-in image tool generated the source drawings in `drawings/`. Exact prompts are saved in `prompts/`. Rebuild with `python3 standalone/goa-races/character-retarget/build_orc_special_moves.py` from the repository root. Rebuilds use saved images without further generation calls or tokens.

The export uses the existing 16-color palette, binary transparency and nearest-neighbor sampling. These new poses remain drawing reviews; palette/guard consistency is verified, but generated active poses are not pixel-identical redraws of the original character. Preview timings and dash displacement are illustrative. No game physics, input, damage or hit detection is integrated.

## Overhead cast selection

The original four-phase overhead cast is restored in full. The user rejected both the broad revision and the targeted east/west redraw. No native overrides are active. Revision drawings remain archived only; the original source `drawings/overhead_cast.png` supplies all four directions.

## Appearance correction — dark-reference-v1

Skin now uses the shared `../attack-appearance.json` shades sampled from the user-liked attack reference. Source shading is mapped before palette quantization, without smoothing. Poses, transparency and non-skin pixels are unchanged. Earlier appearance snapshots and hashes are archived under `../appearance-revisions/before-dark-reference-v1/`; active build hash baselines now track the corrected colors.
