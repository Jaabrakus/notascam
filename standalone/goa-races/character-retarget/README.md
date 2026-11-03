# Character retarget pipeline

Build review candidates from the approved Elf rig without changing it. This handles races and humanoid hybrids with the same 64px, four-direction layout. It does not promise perfect unseen anatomy or automatic art approval.

## Existing character profile

From the Dungeon-Master-master repository root:

```sh
python3 standalone/goa-races/character-retarget/retarget.py \
  --profile 'Dungeon Master Sample/GOA Reusable Animation Rig v1 - Human Male/profiles/human-male.json' \
  --assets 'Dungeon Master Sample/GOA Reusable Animation Rig v1 - Human Male/preview/assets' \
  --output 'Dungeon Master Sample/My New Human Review'
```

## Sprite sheet plus zones

Input folder must contain `sprites.png`, `fine.png`, `fine.json` and `<Race>.json`. The sheet is 256×192: columns South/North/East/West, rows idle/walk A/walk B, native 64px cells. The fine-zone PNG is indexed with the zone names in `fine.json`. Joint data follows the bundled `zone_cutter.py` schema.

```sh
python3 standalone/goa-races/character-retarget/retarget.py \
  --inputs '/absolute/path/to/inputs' --race Human --name 'Human male' \
  --output '/absolute/path/to/new-review-folder'
```

Existing-profile builds use Python 3.9+ and the standard library. Cutting from zones additionally requires Pillow and numpy. The included cutter is derived from the Human conversion tooling; it produces provisional parts and reports inferred geometry. Preserve and inspect those approximations.

## Batch races / hybrids

Pass `--batch jobs.json`, where the file is a JSON list. Each item uses the option names above (without `--`). Use absolute paths to avoid ambiguity. Each output must be a new folder. A failed job is reported separately; existing output folders are never overwritten.

```json
[
  {"inputs":"/path/Human","race":"Human","name":"Human male","output":"/path/out/Human"},
  {"inputs":"/path/HalfElf","race":"HalfElf","name":"Half elf female","output":"/path/out/HalfElf"}
]
```

## What is automated

- Validate joints, body-part names, PNG dimensions, references and direction order.
- Flag extreme left/right reach differences in front/back views rather than silently forcing symmetry.
- Fit guard offsets by calibrated reach and bow targets by neck position, shoulder span and torso height.
- Keep bow pose targets in the output profile for refinement. Preserve East mirroring the West master.
- Namespace character assets to avoid overwriting weapon images.
- Build a self-contained browser preview, editable source, profile, fit report and SHA-256 manifest.
- Preserve the Elf source. Do not copy its exports or pass reports and mislabel them as another character's results.

`--overrides file.json` overlays top-level profile fields before fitting. Use a complete replacement `views` list for manual joint corrections. Provide `poseTargets.bow` to override automatic bow mapping. Set `keepGrips: true` to retain manually calibrated grips. The output `rebuild.py` consumes the edited profile directly without rerunning the fitting guesses.

## What still needs review

The renderer retains some Elf-specific throw and body-motion corrections. This version adapts guard and bow targets; it does **not** fully parameterize every action or guarantee all races match automatically. Inspect the fit report and all key poses before export. Flat fillers, shorts/thigh seams, synthetic far limbs and big fists can need pixel cleanup. Wings, tails and non-humanoid anatomy are flagged and require additional layers; they must not be treated as finished output.

Open the generated `preview/index.html`, or serve its parent folder locally. Review native pixels, equipment contacts and complete recoveries. Bow samples: .32, .72, .90, 1.15, 1.40, 1.75s. Throw: .26, .38, .52, .75s. Export from the viewer only after review.

The current Human example is in `Dungeon Master Sample/GOA Retarget Review - Human Male`. The source Human package was being revised during development, so comparisons should use the generated manifest/profile snapshot rather than assuming its contents have remained unchanged.

## Human-specific repair guide

See `Dungeon Master Sample/GOA Retarget Review - Human Male/README-CLAUDE.md` for the current arm cuts, source-pivot rules, independent leg assignments and accepted North layer order. Use the refinement scripts only after inspecting the target body; they are not automatic rules for all races.

## The sprites are original art (owner, 2026-10-31)

Every race sheet in `Dungeon Master Sample/Sprites` and `Approved Sprites` is original GOA art made for this game,
even where an atlas still says "generated walk draft". Treat every body pixel as finished art:

- Cut it apart and put it back together; never redraw, repaint, recolour or patch body pixels with flat colour.
- Where a moving piece uncovers a surface the idle cell never shows, take it from another frame of the same facing
  (the walk frames), lined up by pixel match. If no frame shows it, leave it empty and report it.
- Cut each race by its own zones and proportions. Do not reuse another race's elbow, wrist or knee rows.

The Orc review (`Dungeon Master Sample/GOA Retarget Review - Orc Male`, `README-CLAUDE.md` and
`tools/recut_by_zones.py`) follows these rules.
