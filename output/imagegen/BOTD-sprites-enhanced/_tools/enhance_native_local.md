# Local native sprite enhancement engine

`enhance_native_local.py` applies a deterministic local pixel-art lighting pass.
These outputs are **local enhancements, not newly generated AI artwork**.
They remain review candidates; this tool does not install into the game.

## Usage

```sh
python3 output/imagegen/BOTD-sprites-enhanced/_tools/enhance_native_local.py \
  --source /absolute/source.dmi --output /absolute/candidate.dmi
```

For a batch, put this directory on `sys.path` and call
`enhance_file(sourcePath, outPath, settings=None)`. The optional settings dictionary
accepts only `strength`, default `1.0`, greater than zero and at most `1.5`.
Calls are independent and thread safe. A compact JSON-serializable report is
returned, and the same report is saved beside the output as `.dmi.local.json`.

## Appearance

The original per-pixel hues are relit using four broad steps derived from a
bounded distance field over each native cell's visible material. Dark lines
subdivide the form. Rare high-contrast detail colors are protected. Dark pixels
receive restrained shadow changes; bright colors use available highlight
headroom instead of channel clipping. No saturation change, random texture,
filtering of RGB, resizing, or movement of pixels is used. Nearly black and tiny
cells have a restrained one-channel-level tonal fallback so an unchanged
occupied cell is never silently marked enhanced. Completely transparent sheets
are explicitly classified `empty_preserved`, never as enhanced artwork.

## Preservation and audit

Only occupied, metadata-declared cells are processed, in their original order.
Duplicate state names and long animations are retained. Empty cells, unused
trailing cells, alpha at every coordinate, and RGB hidden under zero alpha stay
exact. Description text is stored verbatim in the resulting PNG container.
Original dimensions and occupied visible heights therefore stay exact.

The independent `validate_dmi.py` checker must pass before an output is finalized.
Original overwrite and output into the canonical game sprite tree are refused.
The source file hash is checked before and after processing. Cache identity
includes source hash, engine source hash, version and all settings; the cached
output file hash must still match. A modification to source, settings, script or
output invalidates the cached result.

Returned reports include file hashes, original dimensions, native frame size,
used/occupied/changed cell counts, changed visible RGB pixels, exact-alpha and
hidden-RGB counts, unchanged padding, verbatim Description and ordered-state
equality, and source-unchanged status. Structural checks establish preservation,
not artistic equivalence to any generated reference or runtime integration.

## Pilot

`../local-enhanced-pilot/pilot-report.json` records eight complete native sheets:
Night Elf, Skeleton, FrogMan, Demon, Goblins, Human, bone gear and adamantium
gear. Every occupied cell changes, with zero alpha/hidden-RGB/padding changes.
The six-material comparison PNG presents four first-direction cells from each
of the first six sheets: original at left, local candidate at right, displayed
at integer nearest-neighbor scale for inspection only. Native files are not
resized. Independent QA checked all six original pilot sheets and visually
reviewed 24 paired cells; findings were no blocking geometry or palette issues
and a subtle faceted effect, not an AI-redraw style.
