# Native DMI preservation validation

`validate_dmi.py` reads an original native `.dmi` and a candidate native `.dmi`,
then writes a JSON report. It never saves, enhances, or modifies an image.
It requires Python 3 and Pillow, already present in this workspace.

Run from the project root, substituting an existing candidate file:

```sh
python3 output/imagegen/BOTD-sprites-enhanced/_tools/validate_dmi.py \
  standalone/remastered/game/Icons/Remastered/Races64/Human.dmi \
  output/imagegen/BOTD-sprites-enhanced/native/Races64/Human.dmi \
  --report output/imagegen/BOTD-sprites-enhanced/_meta/validation/Human.json \
  --require-enhanced
```

The candidate path above is an example, not a claim that this asset exists.
Exit status is zero on pass, one on failed checks, and two on CLI usage errors.

The validator checks:

- PNG chunk integrity via Pillow `verify()`, and rejection of animated PNG containers.
- Supported metadata versions (3.0 and 4.0), valid quoted state names, direction
  counts (1, 4, or 8), positive frame counts/delays, valid movement/rewind/loop values,
  and three-integer hotspots referring to an existing state cell. These rules match
  the established parser in `standalone/remastered/tools/export_sprite_assets.py`.
  Extra positive delays are retained with a warning; repeated hotspots are allowed.
  Duplicate header or non-hotspot state keys are rejected. Unknown fields are
  retained without interpretation and reported as warnings.
- Exact decoded `Description` text, including comments, whitespace, unknown keys,
  direction/frame counts, delay, movement, loop, rewind, and hotspot metadata.
- Ordered state records, retaining duplicate names as separate indexed records.
  Existing duplicates are reported and permitted; dropping or reordering them fails.
- Sheet and DMI frame dimensions, sufficient sheet capacity, and frame divisibility.
- Exact alpha values at every coordinate, including partially transparent pixels.
- RGB values at fully transparent source coordinates, strictly preserved by default.
  `--allow-transparent-rgb-changes` permits these invisible changes with a warning.
- RGB in unused trailing DMI cells, which must remain unchanged even with that flag.
- With `--require-enhanced`, at least one visible RGB change. Copies, re-encoded
  originals, and changes confined to transparent pixels fail this requirement.

Visible RGB changes are measured and reported, not rejected. Each used cell has its
state occurrence index, offset inside that state, sheet coordinates, alpha bounding
boxes, and difference counts. This indexing avoids collapsing duplicate names or
pretending to infer runtime direction labels. The report also includes full parsed
metadata, file and decoded-pixel hashes, and aggregate difference counts.

Preserving dimensions, ordered metadata, and every alpha coordinate preserves the
recorded frame positions and silhouettes. It does **not** prove that faces, limb
details, material colors, or equipment look right. A one-pixel RGB change can pass
`--require-enhanced`; the flag prevents unchanged copies being counted, but is not
an art quality score. Swapping RGB artwork between states with identical alpha can
also pass: this validator does not verify sprite identity. Visual review, animation playback, equipment checks, and
runtime integration remain separate requirements. PNG compression and chunk
ordering may change; the decoded Description string must remain exact.

## Verification performed

```sh
cd output/imagegen/BOTD-sprites-enhanced/_tools
python3 -m unittest -v test_validate_dmi.py
```

All 23 tests passed. Tests construct tiny fixtures in memory and do not write
images. They cover duplicated/dropped/reordered states, exact-alpha drift,
coordinate shifts, transparent RGB policy, unchanged copies, valid visible RGB
differences, exact metadata including additional fields, and dimension/capacity errors.
They also reject missing/invalid versions, malformed names, invalid direction/timing/
hotspot values, duplicate keys, corrupt IDAT checksums, and APNGs. Valid extra delays
and repeated hotspots remain accepted. A four-direction, two-frame state followed
by a duplicate state verifies cell ownership and sheet-row wrapping. An explicit
same-alpha RGB-swap test documents the sprite-identity limit.

Seven original-versus-itself baselines passed across Races64, Gear, Gear64, Items,
Limbs64, and Rope64, including both native Demon files with duplicate state names.
Reports are in `../_meta/validation/baseline/`, with a `summary.json` index.
These baselines validate 2,285 existing frame cells. They are **not enhanced assets**
and do not count toward completing the sprite batch.

The full manifest baseline also passed: **669 of 669 native sources**, covering
**146,255 frame cells**, with no validation failures. Its compact per-file results
are in `../_meta/validation/all-native-baseline.json`. Four existing Gargoyle race
variants contain 12 delays for a two-frame state; these remain preserved with
warnings, consistent with the established exporter. No checks were weakened for
the full pack. All comparisons were against each original itself, with
`--require-enhanced` disabled; no enhanced candidates or images were produced.
